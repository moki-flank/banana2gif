# -*- coding: utf-8 -*-
"""
视频转动图模块 (Video-to-GIF / Video-to-WebP)
支持各类常见视频格式（MP4, MOV, WebM, AVI, MKV, FLV 等）直接高效转为轻量、平滑循环的表情包动图。
"""

import os
from typing import Optional, List, Tuple
from PIL import Image

try:
    import imageio.v3 as iio
    IMAGEIO_AVAILABLE = True
except ImportError:
    IMAGEIO_AVAILABLE = False


def convert_video_to_gif(
    video_path: str,
    output_gif_path: str,
    fps: int = 10,
    max_duration_sec: float = 4.0,
    target_size: Optional[Tuple[int, int]] = (320, 320),
    loop: int = 0,
) -> str:
    """
    将视频文件转换为 GIF 动图。
    video_path: 视频文件路径
    output_gif_path: 输出动图路径 (.gif 或 .webp)
    fps: 采样帧率 (推荐 8~12 FPS 适合表情包)
    max_duration_sec: 最大采样时长(秒)，避免视频过长导致动图过大
    target_size: 缩放尺寸，如 (320, 320)，None 则保持原比例
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"未找到输入视频文件: {video_path}")

    if not IMAGEIO_AVAILABLE:
        raise RuntimeError("处理视频需要安装 imageio 与 imageio-ffmpeg：pip install imageio imageio-ffmpeg")

    os.makedirs(os.path.dirname(os.path.abspath(output_gif_path)), exist_ok=True)

    frames: List[Image.Image] = []
    max_frames = int(fps * max_duration_sec)

    try:
        # 读取视频帧
        frame_idx = 0
        for frame_arr in iio.imiter(video_path, plugin="pyav" if hasattr(iio, "pyav") else None):
            frame = Image.fromarray(frame_arr).convert("RGB")
            
            if target_size:
                # 保持中心正方形裁切并缩放
                w, h = frame.size
                min_dim = min(w, h)
                left = (w - min_dim) // 2
                top = (h - min_dim) // 2
                frame = frame.crop((left, top, left + min_dim, top + min_dim))
                frame = frame.resize(target_size, Image.Resampling.LANCZOS)

            frames.append(frame)
            frame_idx += 1
            if frame_idx >= max_frames:
                break
    except Exception as e:
        # 兼容传统 imageio 模式
        import imageio
        reader = imageio.get_reader(video_path)
        for i, frame_arr in enumerate(reader):
            if i >= max_frames:
                break
            frame = Image.fromarray(frame_arr).convert("RGB")
            if target_size:
                w, h = frame.size
                min_dim = min(w, h)
                left = (w - min_dim) // 2
                top = (h - min_dim) // 2
                frame = frame.crop((left, top, left + min_dim, top + min_dim))
                frame = frame.resize(target_size, Image.Resampling.LANCZOS)
            frames.append(frame)

    if not frames:
        raise ValueError("未能从视频中提取有效画面帧")

    duration_ms = int(1000.0 / fps)
    
    # 支持根据后缀自动选择 GIF 或 WebP
    is_webp = output_gif_path.lower().endswith(".webp")
    
    frames[0].save(
        output_gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=loop,
        optimize=True,
        format="WEBP" if is_webp else "GIF",
    )
    return output_gif_path
