"""
RGB Array Resolve Node

Resolve one RGB triplet from an RGB array by index and output byte RGB ints.
"""

import ast
import json
from typing import Any, List, Sequence, Tuple

import torch


class RGBArrayResolve:
    """
    Input: RGB array (socket input) + index
    Output: r, g, b in selected mode (normalized or byte)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "rgb_array": ("STRING", {"default": "[]", "multiline": False, "forceInput": True}),
                "color_index": ("INT", {"default": 0, "min": 0, "max": 999, "step": 1}),
                "clamp_index": ("BOOLEAN", {"default": True}),
                "rgb_output_mode": (["normalized", "byte"], {"default": "byte"}),
                "preview_width": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 1}),
                "preview_height": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 1}),
            }
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "FLOAT", "STRING", "IMAGE")
    RETURN_NAMES = ("red", "green", "blue", "hex_color", "preview")
    FUNCTION = "resolve"
    CATEGORY = "Color Tools/Analysis"

    def resolve(
        self,
        rgb_array: Any,
        color_index: int,
        clamp_index: bool,
        rgb_output_mode: str,
        preview_width: int,
        preview_height: int,
    ):
        data = self._parse_array(rgb_array)
        if not data:
            raise ValueError("rgb_array is empty")

        if clamp_index:
            idx = min(max(color_index, 0), len(data) - 1)
        else:
            if color_index < 0 or color_index >= len(data):
                raise ValueError(f"color_index {color_index} out of range for length {len(data)}")
            idx = color_index

        item = data[idx]
        r_byte, g_byte, b_byte = self._to_rgb_bytes_auto(item)
        hex_color = f"#{r_byte:02x}{g_byte:02x}{b_byte:02x}"

        if rgb_output_mode == "normalized":
            out_r = r_byte / 255.0
            out_g = g_byte / 255.0
            out_b = b_byte / 255.0
        else:
            out_r = float(r_byte)
            out_g = float(g_byte)
            out_b = float(b_byte)

        preview = torch.zeros((1, preview_height, preview_width, 3), dtype=torch.float32)
        preview[..., 0] = r_byte / 255.0
        preview[..., 1] = g_byte / 255.0
        preview[..., 2] = b_byte / 255.0
        return (float(out_r), float(out_g), float(out_b), hex_color, preview)

    def _parse_array(self, value: Any) -> List[Any]:
        if isinstance(value, list):
            return value

        text = str(value).strip()
        if not text:
            return []

        try:
            obj = json.loads(text)
        except Exception:
            obj = ast.literal_eval(text)

        if not isinstance(obj, list):
            raise ValueError("rgb_array must be a list-like value")
        return obj

    def _to_rgb_bytes_auto(self, item: Any) -> Tuple[int, int, int]:
        if not (isinstance(item, Sequence) and not isinstance(item, str) and len(item) >= 3):
            raise ValueError("selected item is not an RGB triplet")

        try:
            r = float(item[0])
            g = float(item[1])
            b = float(item[2])
        except Exception as e:
            raise ValueError(f"failed to parse RGB values: {e}")

        # Auto-detect normalized (0..1) vs byte (0..255) input.
        if max(r, g, b) <= 1.0:
            r *= 255.0
            g *= 255.0
            b *= 255.0

        rr = int(round(max(0.0, min(255.0, r))))
        gg = int(round(max(0.0, min(255.0, g))))
        bb = int(round(max(0.0, min(255.0, b))))
        return (rr, gg, bb)
