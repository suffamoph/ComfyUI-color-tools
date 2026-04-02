"""
Natural Background Color Node

Automatically picks a harmonized single background color from 1-4
Dominant Colors outputs.
"""

import ast
import json
import math
from typing import Any, List, Optional, Sequence, Tuple

import colorsys
import torch


class NaturalBackgroundColor:
    """
    Build a safe, natural-looking solid background color for collages.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "style_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.5, "step": 0.01}),
                "colors_1": ("STRING", {"default": "[]", "multiline": False, "forceInput": True}),
            },
            "optional": {
                "percentages_1": ("STRING", {"default": "", "multiline": False, "forceInput": True}),
                "colors_2": ("STRING", {"default": "", "multiline": False, "forceInput": True}),
                "percentages_2": ("STRING", {"default": "", "multiline": False, "forceInput": True}),
                "colors_3": ("STRING", {"default": "", "multiline": False, "forceInput": True}),
                "percentages_3": ("STRING", {"default": "", "multiline": False, "forceInput": True}),
                "colors_4": ("STRING", {"default": "", "multiline": False, "forceInput": True}),
                "percentages_4": ("STRING", {"default": "", "multiline": False, "forceInput": True}),
            },
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "FLOAT", "FLOAT", "FLOAT", "FLOAT", "STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("red", "green", "blue", "hue", "saturation", "value", "hex_color", "analysis_json", "preview")
    FUNCTION = "compute_background"
    CATEGORY = "Color Tools/Analysis"

    def compute_background(
        self,
        style_strength: float,
        colors_1: str,
        percentages_1: str = "",
        colors_2: str = "",
        percentages_2: str = "",
        colors_3: str = "",
        percentages_3: str = "",
        colors_4: str = "",
        percentages_4: str = "",
        **kwargs,
    ):
        # Compatibility path for old workflow nodes that still carry deprecated
        # sockets/values (dominant_colors_* and old width/height shifted values).
        if not (colors_1 or "").strip():
            colors_1 = kwargs.get("dominant_colors_1", colors_1)
        if not (colors_2 or "").strip():
            colors_2 = kwargs.get("dominant_colors_2", colors_2)
        if not (colors_3 or "").strip():
            colors_3 = kwargs.get("dominant_colors_3", colors_3)
        if not (colors_4 or "").strip():
            colors_4 = kwargs.get("dominant_colors_4", colors_4)

        style_strength = self._normalize_style_strength(style_strength)

        color_blocks = [colors_1, colors_2, colors_3, colors_4]
        pct_blocks = [percentages_1, percentages_2, percentages_3, percentages_4]

        samples = []
        for i in range(4):
            c_block = (color_blocks[i] or "").strip()
            if not c_block:
                continue

            colors = self._parse_list(c_block)
            if not colors:
                continue

            rgb = self._to_rgb01(colors[0])

            weight = 1.0
            p_block = (pct_blocks[i] or "").strip()
            if p_block:
                p_list = self._parse_list(p_block)
                if p_list and isinstance(p_list[0], (int, float)):
                    weight = float(max(0.0, p_list[0]))

            samples.append((rgb, weight))

        if not samples:
            raise ValueError("No valid color inputs were provided.")

        hue = self._weighted_circular_mean_hue(samples)
        sat_mean, val_mean = self._weighted_mean_sv(samples)

        # Natural style mapping: reduce saturation, keep clean medium-high value.
        sat_target = self._clamp(0.08 + 0.35 * sat_mean * style_strength, 0.08, 0.22)
        val_target = self._clamp(0.76 + 0.20 * (val_mean - 0.5), 0.72, 0.88)

        red, green, blue = colorsys.hsv_to_rgb(hue, sat_target, val_target)
        hex_color = self._to_hex(red, green, blue)

        preview = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
        preview[..., 0] = red
        preview[..., 1] = green
        preview[..., 2] = blue

        analysis = {
            "mode": "natural_background_auto",
            "preview_width": 512,
            "preview_height": 512,
            "style_strength": style_strength,
            "input_count": len(samples),
            "hue": hue,
            "sat_mean": sat_mean,
            "val_mean": val_mean,
            "sat_target": sat_target,
            "val_target": val_target,
            "rgb": [red, green, blue],
            "hex": hex_color,
        }

        return (
            float(red),
            float(green),
            float(blue),
            float(hue),
            float(sat_target),
            float(val_target),
            hex_color,
            json.dumps(analysis, ensure_ascii=False),
            preview,
        )

    def _parse_list(self, text: str) -> List[Any]:
        try:
            obj = json.loads(text)
        except Exception:
            obj = ast.literal_eval(text)
        if not isinstance(obj, list):
            raise ValueError("Expected list-like JSON content.")
        return obj

    def _to_rgb01(self, color: Any) -> Tuple[float, float, float]:
        if isinstance(color, str):
            c = color.strip().lstrip("#")
            if len(c) != 6:
                raise ValueError("HEX color must be #RRGGBB.")
            r = int(c[0:2], 16) / 255.0
            g = int(c[2:4], 16) / 255.0
            b = int(c[4:6], 16) / 255.0
            return (r, g, b)

        if isinstance(color, Sequence) and len(color) >= 3:
            r = float(color[0])
            g = float(color[1])
            b = float(color[2])
            if max(r, g, b) > 1.0:
                r /= 255.0
                g /= 255.0
                b /= 255.0
            return (self._clamp(r, 0.0, 1.0), self._clamp(g, 0.0, 1.0), self._clamp(b, 0.0, 1.0))

        raise ValueError("Unsupported color format.")

    def _weighted_circular_mean_hue(self, samples: List[Tuple[Tuple[float, float, float], float]]) -> float:
        x = 0.0
        y = 0.0
        w_sum = 0.0
        for rgb, w in samples:
            h, s, v = colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])
            # Desaturated colors contribute less to hue decision.
            effective_w = max(1e-6, w * (0.35 + 0.65 * s))
            angle = 2.0 * math.pi * h
            x += math.cos(angle) * effective_w
            y += math.sin(angle) * effective_w
            w_sum += effective_w

        if w_sum <= 0:
            return 0.0

        angle = math.atan2(y, x)
        if angle < 0:
            angle += 2.0 * math.pi
        return angle / (2.0 * math.pi)

    def _weighted_mean_sv(self, samples: List[Tuple[Tuple[float, float, float], float]]) -> Tuple[float, float]:
        s_sum = 0.0
        v_sum = 0.0
        w_sum = 0.0
        for rgb, w in samples:
            h, s, v = colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])
            ww = max(1e-6, w)
            s_sum += s * ww
            v_sum += v * ww
            w_sum += ww
        return (s_sum / w_sum, v_sum / w_sum)

    def _to_hex(self, r: float, g: float, b: float) -> str:
        rr = int(self._clamp(r, 0.0, 1.0) * 255)
        gg = int(self._clamp(g, 0.0, 1.0) * 255)
        bb = int(self._clamp(b, 0.0, 1.0) * 255)
        return f"#{rr:02x}{gg:02x}{bb:02x}"

    def _clamp(self, v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def _normalize_style_strength(self, value: Any) -> float:
        """
        Protect against stale widget value shifting (e.g. 1536.0 from old width).
        """
        try:
            f = float(value)
        except Exception:
            return 1.0
        if not math.isfinite(f):
            return 1.0
        if f > 3.0:
            return 1.0
        return float(self._clamp(f, 0.0, 1.5))
