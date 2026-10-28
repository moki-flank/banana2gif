# -*- coding: utf-8 -*-
"""
banano2gif 核心流水线引擎
全面支持：
  1. 文生动图 (Text-to-GIF)
  2. 图生动图 (Image-to-GIF / 参考图生图)
  3. 动作迁移 (Motion-Transfer / 从GIF、WebP、视频中提取动作迁移到新人设图)
  4. 视频直转动图 (Video-to-GIF)
  5. 智能透明背景化 (Alpha Channel Matting)
  6. 4K 超高清规格 (4K 4096x4096 UHD)
  7. 【多规格网格控制精度】：支持 3x3 九宫格 (9帧) 与 4x4 十六宫格 (16帧超丝滑)
"""

import os
import urllib.request
from typing import Optional, Dict, Any, List, Union, Tuple
from PIL import Image

from .sdk.client import HrioClient, DEFAULT_BASE_URL, OFFICIAL_WEBSITE
from .prompts.engine import build_prompt, build_motion_transfer_prompt, ACTION_PRESETS
from .cutter.slicer import slice_grid
from .cutter.gif_builder import build_gif
from .cutter.video_to_gif import convert_video_to_gif
from .cutter.matting import remove_background
from .cutter.motion_extractor import create_motion_guide_grid

DEFAULT_MODEL = "gemini-nano-banana-2.1"


class Banano2Gif:
    """
    banano2gif 多模态动图生成引擎
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ):
        self.client = HrioClient(api_key=api_key, base_url=base_url)
        self.model = model

    def text_to_gif(
        self,
        prompt: str,
        preset: Optional[str] = None,
        grid: str = "3x3",
        style: str = "High-end 3D animation render, soft ambient lighting, clean solid white background, Pop Mart collectible figurine style",
        output_dir: str = "output",
        gif_filename: str = "animation.gif",
        duration_ms: Optional[int] = None,
        crop_size: Optional[int] = None,
        export_size: Optional[int] = None,
        transparent: bool = False,
        is_4k: bool = False,
    ) -> Dict[str, Any]:
        """【文生动图】支持 3x3 (9帧) 与 4x4 (16帧)。"""
        return self._generate_from_prompt(
            prompt=prompt,
            images=None,
            preset=preset,
            grid=grid,
            style=style,
            output_dir=output_dir,
            gif_filename=gif_filename,
            duration_ms=duration_ms,
            crop_size=crop_size,
            export_size=export_size,
            transparent=transparent,
            is_4k=is_4k,
            mode="text_to_gif",
        )

    def image_to_gif(
        self,
        image_path: str,
        prompt: str = "gently waving and smiling happily",
        preset: Optional[str] = None,
        grid: str = "3x3",
        style: str = "Preserve original character art style, high quality render, clean solid white background",
        output_dir: str = "output",
        gif_filename: str = "image_animation.gif",
        duration_ms: Optional[int] = None,
        crop_size: Optional[int] = None,
        export_size: Optional[int] = None,
        transparent: bool = False,
        is_4k: bool = False,
    ) -> Dict[str, Any]:
        """【图生动图 / 参考图生图】支持 3x3 与 4x4 规格。"""
        if not os.path.isfile(image_path) and not image_path.startswith(("http://", "https://")):
            raise FileNotFoundError(f"未找到参考图片文件: {image_path}")

        return self._generate_from_prompt(
            prompt=prompt,
            images=[image_path],
            preset=preset,
            grid=grid,
            style=style,
            output_dir=output_dir,
            gif_filename=gif_filename,
            duration_ms=duration_ms,
            crop_size=crop_size,
            export_size=export_size,
            transparent=transparent,
            is_4k=is_4k,
            mode="image_to_gif",
        )

    def transfer_motion(
        self,
        source_media: str,
        target_image: str,
        action_hint: str = "transfer the exact motion and poses from the motion guide to the target character",
        grid: str = "3x3",
        style: str = "Preserve target character art style, high quality render, clean solid white background",
        output_dir: str = "output",
        gif_filename: str = "motion_transfer.gif",
        duration_ms: Optional[int] = None,
        crop_size: Optional[int] = None,
        export_size: Optional[int] = None,
        transparent: bool = False,
        is_4k: bool = False,
    ) -> Dict[str, Any]:
        """【动作生成迁移】支持 3x3 与 4x4 动作指南。"""
        os.makedirs(output_dir, exist_ok=True)
        if not os.path.isfile(source_media):
            raise FileNotFoundError(f"未找到源动作媒体文件: {source_media}")
        if not os.path.isfile(target_image):
            raise FileNotFoundError(f"未找到目标角色人设图片: {target_image}")

        is_16 = "4" in str(grid) or str(grid) == "16"
        grid_dim = 4096 if is_4k else 1024
        guide_grid_path = os.path.join(output_dir, "motion_guide_grid.jpg")
        print(f"[banano2gif] 1. 正在从源媒体抽取关键动作 ({'4x4 16帧' if is_16 else '3x3 9帧'}): {source_media}...")
        create_motion_guide_grid(source_media, output_grid_path=guide_grid_path, grid_layout=grid, grid_size=grid_dim)

        full_prompt = build_motion_transfer_prompt(action_hint=action_hint, grid=grid, style=style, is_4k=is_4k)
        grid_save_path = os.path.join(output_dir, "transferred_grid.jpg")
        frames_dir = os.path.join(output_dir, "transferred_frames")
        gif_save_path = os.path.join(output_dir, gif_filename)

        req_size = "4096x4096" if is_4k else "1024x1024"
        print(f"[banano2gif] 2. 发起跨角色动作迁移生图 (规格: {req_size}, 模型: {self.model})...")

        resp = self.client.generate_image(
            self.model,
            full_prompt,
            images=[target_image, guide_grid_path],
            parameters={"size": req_size},
        )
        img_url, img_bytes = self.client.extract_image_bytes_or_url(resp)

        if img_bytes:
            with open(grid_save_path, "wb") as f:
                f.write(img_bytes)
        elif img_url:
            req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as s, open(grid_save_path, "wb") as f:
                f.write(s.read())
        else:
            raise RuntimeError(f"未能从模型返回中提取有效图片数据: {resp}")

        print(f"[banano2gif] 3. 正在切帧 (网格: {grid}, 透明去底: {transparent})...")
        frames = slice_grid(
            grid_save_path,
            output_dir=frames_dir,
            grid_layout=grid,
            crop_size=crop_size,
            export_size=export_size,
            transparent=transparent,
        )

        eff_duration = duration_ms or (100 if is_16 else 180)
        print(f"[banano2gif] 4. 正在合成动图 ({eff_duration}ms/帧, 共 {len(frames)} 帧)...")
        gif_path = build_gif(frames, output_path=gif_save_path, duration_ms=eff_duration)
        webp_save_path = os.path.splitext(gif_save_path)[0] + ".webp"
        build_gif(frames, output_path=webp_save_path, duration_ms=eff_duration)

        return {
            "ok": True,
            "mode": "motion_transfer",
            "grid": "4x4" if is_16 else "3x3",
            "is_4k": is_4k,
            "source_media": source_media,
            "target_image": target_image,
            "motion_guide": guide_grid_path,
            "grid_image": grid_save_path,
            "frames_dir": frames_dir,
            "total_frames": len(frames),
            "gif_path": gif_path,
            "webp_path": webp_save_path,
            "official_website": OFFICIAL_WEBSITE,
        }

    def video_to_gif(
        self,
        video_path: str,
        output_path: str = "output/video_animation.gif",
        fps: int = 10,
        max_duration_sec: float = 4.0,
        target_size: Optional[Tuple[int, int]] = (320, 320),
    ) -> Dict[str, Any]:
        """【视频生 / 视频转动图】将任意格式视频转换为表情包 GIF 或 WebP。"""
        print(f"[banano2gif] 正在转换视频: {video_path} -> {output_path}...")
        res_path = convert_video_to_gif(
            video_path=video_path,
            output_gif_path=output_path,
            fps=fps,
            max_duration_sec=max_duration_sec,
            target_size=target_size,
        )
        return {
            "ok": True,
            "mode": "video_to_gif",
            "gif_path": res_path,
            "video_input": video_path,
        }

    def _generate_from_prompt(
        self,
        prompt: str,
        images: Optional[List[str]],
        preset: Optional[str],
        grid: str,
        style: str,
        output_dir: str,
        gif_filename: str,
        duration_ms: Optional[int],
        crop_size: Optional[int],
        export_size: Optional[int],
        transparent: bool,
        is_4k: bool,
        mode: str,
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        grid_save_path = os.path.join(output_dir, "grid.jpg")
        frames_dir = os.path.join(output_dir, "frames")
        gif_save_path = os.path.join(output_dir, gif_filename)

        is_16 = "4" in str(grid) or str(grid) == "16"
        grid_label = "4x4 (16帧)" if is_16 else "3x3 (9帧)"

        full_prompt = build_prompt(
            subject_and_action=prompt,
            preset=preset,
            grid=grid,
            style=style,
            has_reference_image=bool(images),
            is_4k=is_4k,
        )

        req_size = "4096x4096" if is_4k else "1024x1024"
        print(f"[banano2gif] 模式: {mode} | 网格: {grid_label} (规格: {req_size}, 透明去底: {'开启' if transparent else '关闭'})")
        print(f"[banano2gif] 1. 请求大模型生图 (模型: {self.model})...")

        resp = self.client.generate_image(
            self.model,
            full_prompt,
            images=images,
            parameters={"size": req_size},
        )
        img_url, img_bytes = self.client.extract_image_bytes_or_url(resp)

        if img_bytes:
            with open(grid_save_path, "wb") as f:
                f.write(img_bytes)
        elif img_url:
            req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as s, open(grid_save_path, "wb") as f:
                f.write(s.read())
        else:
            raise RuntimeError(f"未能从模型返回中提取有效图片数据: {resp}")

        print(f"[banano2gif] 2. 正在进行高精度自适应切帧 (网格: {grid_label}, 透明化: {transparent})...")
        frames = slice_grid(
            grid_save_path,
            output_dir=frames_dir,
            grid_layout=grid,
            crop_size=crop_size,
            export_size=export_size,
            transparent=transparent,
        )

        eff_duration = duration_ms or (100 if is_16 else 180)
        print(f"[banano2gif] 3. 正在合成动图 ({eff_duration}ms/帧, 共 {len(frames)} 帧, 单帧: {frames[0].width}x{frames[0].height})...")
        gif_path = build_gif(frames, output_path=gif_save_path, duration_ms=eff_duration)

        webp_save_path = os.path.splitext(gif_save_path)[0] + ".webp"
        build_gif(frames, output_path=webp_save_path, duration_ms=eff_duration)

        return {
            "ok": True,
            "mode": mode,
            "grid": "4x4" if is_16 else "3x3",
            "is_4k": is_4k,
            "transparent": transparent,
            "gif_path": gif_path,
            "webp_path": webp_save_path,
            "grid_image": grid_save_path,
            "frames_dir": frames_dir,
            "frame_resolution": (frames[0].width, frames[0].height),
            "total_frames": len(frames),
            "prompt": full_prompt,
            "official_website": OFFICIAL_WEBSITE,
        }


def banano2gif(
    prompt: Optional[str] = None,
    image_path: Optional[str] = None,
    video_path: Optional[str] = None,
    motion_source: Optional[str] = None,
    preset: Optional[str] = None,
    grid: str = "3x3",
    transparent: bool = False,
    is_4k: bool = False,
    export_size: Optional[int] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    style: str = "High-end 3D animation render, soft ambient lighting, clean solid white background, Pop Mart collectible figurine style",
    output_dir: str = "output",
    duration_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """
    智能统一接口：自动根据传入参数分流执行：
      - 动作迁移 (motion_source + image_path)
      - 视频转动图 (video_path)
      - 图生动图 (image_path)
      - 文生动图 (prompt)
    支持 grid="4x4" 开启 16 宫格高帧率模式。
    """
    app = Banano2Gif(api_key=api_key, base_url=base_url, model=model)

    if motion_source and image_path:
        return app.transfer_motion(
            source_media=motion_source,
            target_image=image_path,
            action_hint=prompt or "transfer the exact motion and poses from the motion guide to the target character",
            grid=grid,
            style=style,
            output_dir=output_dir,
            duration_ms=duration_ms,
            transparent=transparent,
            is_4k=is_4k,
            export_size=export_size,
        )

    if video_path:
        out_gif = os.path.join(output_dir, "video_animation.gif")
        return app.video_to_gif(video_path=video_path, output_path=out_gif)

    if image_path:
        act_prompt = prompt or "gently waving and smiling happily"
        return app.image_to_gif(
            image_path=image_path,
            prompt=act_prompt,
            preset=preset,
            grid=grid,
            style=style,
            output_dir=output_dir,
            duration_ms=duration_ms,
            transparent=transparent,
            is_4k=is_4k,
            export_size=export_size,
        )

    act_prompt = prompt or "A cute 3D character smiling warmly"
    return app.text_to_gif(
        prompt=act_prompt,
        preset=preset,
        grid=grid,
        style=style,
        output_dir=output_dir,
        duration_ms=duration_ms,
        transparent=transparent,
        is_4k=is_4k,
        export_size=export_size,
    )
