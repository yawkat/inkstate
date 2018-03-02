from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


def draw_text_relative(draw: ImageDraw.ImageDraw, anchor: Tuple[float, float], text: str, font: ImageFont.ImageFont,
                       xa: float = 0, ya: float = 0, clamp_image: Image.Image = None):
    x, y = anchor
    w, h = font.getsize(text)
    x -= w * xa
    y -= h * ya
    if clamp_image is not None:
        x = max((0, min((clamp_image.width - w, x))))
        y = max((0, min((clamp_image.height - h, y))))
    draw.text((x, y), text, font=font)
