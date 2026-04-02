"""
RGB/HEX Convert and Adjust Node

Converts between HEX and RGB and applies HSV-based adjustments.
"""

import colorsys
import json
from typing import Tuple

import torch


class RGBHexAdjust:
    """
    Convert RGB/HEX and apply hue, saturation, value adjustments.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_mode": (["HEX", "RGB"], {"default": "HEX"}),
                "red": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "green": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "blue": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "hex_color": ("STRING", {"default": "#808080", "multiline": False}),
                "hue_shift": ("FLOAT", {"default": 0.0, "min": -180.0, "max": 180.0, "step": 1.0}),
                "saturation_scale": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.01}),
                "value_scale": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.01}),
                "value_offset": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "FLOAT", "FLOAT", "STRING", "IMAGE")
    RETURN_NAMES = (
        "rgb_array",
        "hex_color",
        "hue",
        "saturation",
        "value",
        "info_json",
        "preview",
    )
    FUNCTION = "convert_and_adjust"
    CATEGORY = "Color Tools/Conversion"

    def convert_and_adjust(
        self,
        input_mode: str,
        red: float,
        green: float,
        blue: float,
        hex_color: str,
        hue_shift: float,
        saturation_scale: float,
        value_scale: float,
        value_offset: float,
    ) -> Tuple[str, float, float, float, float, float, float, str, torch.Tensor]:
        # Resolve source color from selected mode.
        if input_mode == "HEX":
            r, g, b = self._hex_to_rgb01(hex_color)
        else:
            r = self._clamp01(red)
            g = self._clamp01(green)
            b = self._clamp01(blue)

        # RGB -> HSV
        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        # Apply adjustments
        h = (h + (hue_shift / 360.0)) % 1.0
        s = self._clamp01(s * saturation_scale)
        v = self._clamp01(v * value_scale + value_offset)

        # HSV -> RGB
        out_r, out_g, out_b = colorsys.hsv_to_rgb(h, s, v)
        out_hex = self._rgb01_to_hex(out_r, out_g, out_b)

        preview = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
        preview[..., 0] = out_r
        preview[..., 1] = out_g
        preview[..., 2] = out_b

        info = {
            "input_mode": input_mode,
            "input_hex": hex_color,
            "input_rgb": [float(r), float(g), float(b)],
            "hue_shift": float(hue_shift),
            "saturation_scale": float(saturation_scale),
            "value_scale": float(value_scale),
            "value_offset": float(value_offset),
            "preview_width": 512,
            "preview_height": 512,
            "output_hex": out_hex,
            "output_rgb": [float(out_r), float(out_g), float(out_b)],
            "output_hsv": [float(h), float(s), float(v)],
        }

        rgb_array = json.dumps([[float(out_r), float(out_g), float(out_b)]])

        return (
            rgb_array,
            out_hex,
            float(h),
            float(s),
            float(v),
            json.dumps(info, ensure_ascii=False),
            preview,
        )

    def _hex_to_rgb01(self, hex_color: str) -> Tuple[float, float, float]:
        text = (hex_color or "").strip().lstrip("#")
        if len(text) != 6:
            raise ValueError("hex_color must be in #RRGGBB format")
        r = int(text[0:2], 16) / 255.0
        g = int(text[2:4], 16) / 255.0
        b = int(text[4:6], 16) / 255.0
        return (r, g, b)

    def _rgb01_to_hex(self, r: float, g: float, b: float) -> str:
        rr = int(self._clamp01(r) * 255)
        gg = int(self._clamp01(g) * 255)
        bb = int(self._clamp01(b) * 255)
        return f"#{rr:02x}{gg:02x}{bb:02x}"

    def _clamp01(self, v: float) -> float:
        return max(0.0, min(1.0, float(v)))
