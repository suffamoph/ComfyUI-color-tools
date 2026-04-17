"""
Hue Distance

Computes the perceptually-uniform hue distance between two HEX colors
by converting to OKLCH and measuring the angular difference on the hue wheel.
"""

import math


def _hex_to_rgb(hex_str: str):
    h = str(hex_str).strip().lstrip("#")
    return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0


def _rgb_to_oklch_h(r: float, g: float, b: float) -> float:
    """Return OKLCH hue angle (0~360°) for an sRGB color (0~1 each)."""
    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    rl, gl, bl = linearize(r), linearize(g), linearize(b)

    l = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    m = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    s = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl

    l_ = max(l, 0.0) ** (1.0 / 3.0)
    m_ = max(m, 0.0) ** (1.0 / 3.0)
    s_ = max(s, 0.0) ** (1.0 / 3.0)

    ok_a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    ok_b = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    return math.degrees(math.atan2(ok_b, ok_a)) % 360.0


def oklch_hue_distance(hex_a: str, hex_b: str) -> float:
    """Circular hue distance in OKLCH space, 0~180°."""
    h_a = _rgb_to_oklch_h(*_hex_to_rgb(hex_a))
    h_b = _rgb_to_oklch_h(*_hex_to_rgb(hex_b))
    d = abs(h_a - h_b) % 360.0
    return min(d, 360.0 - d)


class HueDistance:

    DESCRIPTION = (
        "计算两个颜色在 OKLCH 色相空间中的环形距离（感知均匀）。\n\n"
        "输入为 HEX 颜色字符串（#rrggbb），内部转换到 OKLCH 后取色相角做环形差。\n"
        "相比 HSV 色相，OKLCH 色相空间感知均匀：\n"
        "黄绿区 30° 与蓝区 30° 的视觉差距一致。\n\n"
        "【输出】\n"
        "  • distance：OKLCH 色相环形距离，0~180°\n"
        "  • similarity：1.0 - distance/180，0~1\n"
        "  • is_match：distance ≤ threshold"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "color_a":   ("STRING", {"default": "#ff0000", "multiline": False}),
                "color_b":   ("STRING", {"default": "#0000ff", "multiline": False}),
                "threshold": ("FLOAT",  {"default": 30.0, "min": 0.0, "max": 180.0, "step": 0.5}),
            }
        }

    RETURN_TYPES  = ("FLOAT",    "FLOAT",      "BOOLEAN")
    RETURN_NAMES  = ("distance", "similarity", "is_match")
    FUNCTION      = "compute"
    CATEGORY      = "Color Tools/Analysis"

    def compute(self, color_a: str, color_b: str, threshold: float):
        distance   = oklch_hue_distance(color_a, color_b)
        similarity = round(1.0 - distance / 180.0, 6)
        is_match   = distance <= threshold
        return (round(distance, 4), similarity, is_match)
