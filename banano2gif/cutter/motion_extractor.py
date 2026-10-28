# -*- coding: utf-8 -*-
"""
动作连续帧网格提取器 (Motion Grid Extractor)
从任意输入动图 (.gif, .webp) 或视频 (.mp4, .mov, etc.) 中智能均匀抽取关键帧，
拼接为 3x3 (9帧) 或 4x4 (16帧) 动作参考图，用于引导大模型进行动作生成迁移。
"""

import os
from typing import List, Tuple, Optional, Union
from PIL import Image, ImageSequence

try:
    import imageio.v3 as iio
    IMAGEIO_AVAILABLE = True
except ImportError:
    IMAGEIO_AVAILABLE = False


def extract_frames_from_media(media_path: str, target_frame_count: int = 9) -> List[Image.Image]:
    """从 GIF/WebP 或视频文件中抽取指定数量的关键帧"""
    if not os.path.isfile(media_path):
        raise FileNotFoundError(f"未找到输入媒体文件: {media_path}")

    ext = os.path.splitext(media_path)[1].lower()
    raw_frames: List[Image.Image] = []

    if ext in (".gif", ".webp"):
        im = Image.open(media_path)
        for frame in ImageSequence.Iterator(im):
            raw_frames.append(frame.convert("RGB"))
    else:
        if not IMAGEIO_AVAILABLE:
            raise RuntimeError("处理视频需安装 imageio：pip install imageio imageio-ffmpeg")
        for frame_arr in iio.imiter(media_path):
            raw_frames.append(Image.fromarray(frame_arr).convert("RGB"))

    if not raw_frames:
        raise ValueError(f"未能从 {media_path} 中解析到有效帧")

    total_frames = len(raw_frames)

    if total_frames <= target_frame_count:
        indices = [int(i * (total_frames - 1) / (target_frame_count - 1)) if target_frame_count > 1 else 0 for i in range(target_frame_count)]
    else:
        step = (total_frames - 1) / float(target_frame_count - 1) if target_frame_count > 1 else 0
        indices = [int(round(i * step)) for i in range(target_frame_count)]

    sampled_frames = [raw_frames[min(idx, total_frames - 1)] for idx in indices]
    return sampled_frames


def create_motion_guide_grid(
    media_path: str,
    output_grid_path: str = "motion_guide_grid.jpg",
    grid_layout: Union[str, Tuple[int, int]] = (3, 3),
    grid_size: int = 1024,
) -> str:
    """
    抽取关键帧并拼贴成 3x3 或 4x4 动作参考图。
    """
    if isinstance(grid_layout, str):
        gl = grid_layout.lower().strip()
        rows, cols = (4, 4) if ("4" in gl or gl == "16") else (3, 3)
    else:
        rows, cols = grid_layout

    target_count = rows * cols
    frames = extract_frames_from_media(media_path, target_frame_count=target_count)

    cell_size = grid_size // cols
    margin = 4 if grid_size >= 2048 else 2
    grid_img = Image.new("RGB", (grid_size, grid_size), color=(255, 255, 255))

    for idx, frame in enumerate(frames):
        row = idx // cols
        col = idx % cols

        w, h = frame.size
        min_side = min(w, h)
        left = (w - min_side) // 2
        top = (h - min_side) // 2
        square_frame = frame.crop((left, top, left + min_side, top + min_side))
        target_cell_w = cell_size - margin * 2
        square_frame = square_frame.resize((target_cell_w, target_cell_w), Image.Resampling.LANCZOS)

        x_pos = col * cell_size + margin
        y_pos = row * cell_size + margin
        grid_img.paste(square_frame, (x_pos, y_pos))

    os.makedirs(os.path.dirname(os.path.abspath(output_grid_path)), exist_ok=True)
    grid_img.save(output_grid_path, quality=95)
    return output_grid_path
