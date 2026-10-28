# -*- coding: utf-8 -*-
"""
多规格连续序列帧自适应切割器：
原生支持【3x3 九宫格 (9帧)】与【4x4 十六宫格 (16帧)】以及任意高分辨率 (1024 / 2048 / 4096 4K)！
动态计算单元格中心与裁切范围，完美规避分割线，零白边、零抖动。
"""

import os
from typing import List, Tuple, Union, Optional
from PIL import Image

from .matting import remove_background


def slice_grid(
    image_input: Union[str, Image.Image],
    output_dir: Optional[str] = None,
    grid_layout: Union[str, Tuple[int, int]] = (3, 3),
    crop_size: Optional[int] = None,
    export_size: Optional[int] = None,
    transparent: bool = False,
) -> List[Image.Image]:
    """
    自适应切割九宫格 (3x3) 或十六宫格 (4x4)。
    
    参数：
      image_input: 图片文件路径或 PIL.Image 对象
      output_dir: 若传入路径，则保存切片
      grid_layout: 网格布局规格，支持 (3, 3)、(4, 4) 或字符串 "3x3"、"4x4"、"9"、"16"
      crop_size: 每帧裁切尺寸，None 时自适应保留单元格的 93.75% 画面
      export_size: 最终导出单帧尺寸 (如 320, 240, 或 None 保持原生超清)
      transparent: 是否自动去除纯色背景 (生成 Alpha 通道)
    """
    if isinstance(image_input, str):
        im = Image.open(image_input).convert("RGB")
    else:
        im = image_input.convert("RGB")

    width, height = im.size

    # 解析行列数
    if isinstance(grid_layout, str):
        gl = grid_layout.lower().strip()
        if "4" in gl or gl == "16":
            rows, cols = 4, 4
        else:
            rows, cols = 3, 3
    else:
        rows, cols = grid_layout

    step_x = width / float(cols)
    step_y = height / float(rows)

    cell_centers_x = [step_x * (c + 0.5) for c in range(cols)]
    cell_centers_y = [step_y * (r + 0.5) for r in range(rows)]

    # 动态安全裁切尺寸（避开分割线）
    if crop_size is None or crop_size <= 0:
        crop_size = int(round(min(step_x, step_y) * 0.9375))

    crop_half = crop_size // 2
    frames = []

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    frame_idx = 1
    for r in range(rows):
        for c in range(cols):
            cx = cell_centers_x[c]
            cy = cell_centers_y[r]

            x0 = int(cx - crop_half)
            y0 = int(cy - crop_half)
            x0 = max(0, min(width - crop_size, x0))
            y0 = max(0, min(height - crop_size, y0))
            x1 = x0 + crop_size
            y1 = y0 + crop_size

            frame = im.crop((x0, y0, x1, y1))

            if transparent:
                frame = remove_background(frame)

            if export_size and export_size > 0 and (frame.width != export_size or frame.height != export_size):
                frame = frame.resize((export_size, export_size), Image.Resampling.LANCZOS)

            frames.append(frame)

            if output_dir:
                save_path = os.path.join(output_dir, f"frame_{frame_idx:02d}.png")
                frame.save(save_path)

            frame_idx += 1

    return frames
