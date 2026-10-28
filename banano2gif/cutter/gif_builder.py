# -*- coding: utf-8 -*-
"""
动图合成器 (GIF / WebP Builder)
完整支持：
  1. 常规不透明动图合成
  2. 【8-bit Alpha 完整半透明通道】Animated WebP 动图合成
  3. 【透明调色板与防残影 disposal=2】Animated GIF 动图合成
"""

import os
from typing import List, Union
from PIL import Image


def build_gif(
    frames: List[Union[str, Image.Image]],
    output_path: str = "output.gif",
    duration_ms: int = 180,
    loop: int = 0,
) -> str:
    """
    合成 GIF 或 WebP 动图。
    支持自动检测 RGBA 透明通道并保留透明背景。
    """
    if not frames:
        raise ValueError("帧列表为空，无法合成动图")

    loaded_images: List[Image.Image] = []
    has_alpha = False

    for f in frames:
        if isinstance(f, str):
            im = Image.open(f)
        else:
            im = f

        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            has_alpha = True
            loaded_images.append(im.convert("RGBA"))
        else:
            loaded_images.append(im.convert("RGB"))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    is_webp = output_path.lower().endswith(".webp")

    if is_webp:
        # WebP 原生支持 8 位 Alpha 平滑抗锯齿半透明通道
        loaded_images[0].save(
            output_path,
            format="WEBP",
            save_all=True,
            append_images=loaded_images[1:],
            duration=duration_ms,
            loop=loop,
            lossless=True,
        )
        return output_path

    # GIF 动图处理
    if has_alpha:
        gif_frames = []
        for img in loaded_images:
            alpha = img.split()[-1]
            # 自适应 255 色调色板，留出 1 个槽位给透明通道
            p_img = img.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
            # 蒙版：Alpha < 128 映射为全透色号 255
            mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
            p_img.paste(255, mask)
            p_img.info["transparency"] = 255
            gif_frames.append(p_img)

        gif_frames[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=gif_frames[1:],
            duration=duration_ms,
            loop=loop,
            disposal=2,  # 强制每帧清空背景，避免透明动图产生层叠残影
            transparency=255,
            optimize=False,
        )
    else:
        loaded_images[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=loaded_images[1:],
            duration=duration_ms,
            loop=loop,
            optimize=True,
        )

    return output_path
