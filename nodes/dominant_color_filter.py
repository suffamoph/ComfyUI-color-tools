"""
Dominant Color Filter

Receives dominant_colors / color_percentages JSON from DominantColors* nodes,
filters out near-achromatic colors using OKLCH chroma (C), outputs the remaining
colors in unified standard HSV, and computes WCAG-based brightness.
"""

import json
import math
import colorsys
import torch
import numpy as np
from typing import List, Tuple

_LUMINANCE_OPTIONS = [
    "0.350  (perceptual)",
    "0.200  (conservative)",
    "0.179  (WCAG precise)",
]


class DominantColorFilter:

    DESCRIPTION = (
        "接收 DominantColors* 节点输出的颜色 JSON，过滤低彩度颜色，\n"
        "将剩余颜色统一转为标准 HSV（H:0-360, S:0-1, V:0-1），\n"
        "并用 WCAG 加权亮度判断 bright / dark。\n\n"
        "【color_format】与上游 DominantColors 节点保持一致\n"
        "  • RGB：[[r,g,b], ...]，值域 0~1\n"
        "  • HSV：[[h,s,v], ...]，OpenCV 编码（H:0-179, S:0-255, V:0-255）\n"
        "  • HEX：[\"#rrggbb\", ...]\n\n"
        "【chroma_threshold】OKLCH C（彩度）低于此值的颜色视为无彩色，排除出色相匹配\n"
        "  OKLCH C 范围约 0~0.4，感知均匀；推荐起点 0.04（演出照片等低饱和场景可适当降低）\n"
        "  全部低于阈值时 is_desaturated=True\n\n"
        "【luminance_threshold】WCAG 加权亮度阈值，用于 bright/dark 判断\n\n"
        "【输出】\n"
        "  • filtered_hsv：过滤后颜色 JSON，标准 HSV + hex + weight\n"
        "    [{\"h\":210.5,\"s\":0.82,\"v\":0.91,\"hex\":\"#1a80e6\",\"weight\":0.56}, ...]\n"
        "  • representative_hex：OKLCH 彩度最高颜色的 HEX\n"
        "  • brightness：bright / dark\n"
        "  • is_desaturated：True = 全部低彩度，跳过色相匹配\n"
        "  • preview_image：色条，通过过滤的色块白框，彩度最高者加三角标记"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dominant_colors":     ("STRING", {"forceInput": True}),
                "color_percentages":   ("STRING", {"forceInput": True}),
                "color_in_format":     (["RGB", "HSV", "HEX"], {"default": "RGB"}),
                "color_out_format":    (["HSV", "RGB", "HEX"], {"default": "HSV"}),
                "chroma_threshold":    ("FLOAT", {"default": 0.04, "min": 0.0, "max": 0.4, "step": 0.005}),
                "luminance_threshold": (_LUMINANCE_OPTIONS, {"default": _LUMINANCE_OPTIONS[0]}),
            }
        }

    RETURN_TYPES  = ("STRING",         "STRING",             "STRING",    "BOOLEAN",        "IMAGE")
    RETURN_NAMES  = ("filtered_color", "representative_hex", "brightness","is_desaturated", "preview_image")
    FUNCTION      = "filter_colors"
    CATEGORY      = "Color Tools/Analysis"

    # ------------------------------------------------------------------

    def filter_colors(
        self,
        dominant_colors: str,
        color_percentages: str,
        color_in_format: str,
        color_out_format: str,
        chroma_threshold: float,
        luminance_threshold: str,
    ):
        colors_raw  = json.loads(dominant_colors)
        percentages = json.loads(color_percentages)

        total = sum(percentages) or 1.0
        percentages = [p / total for p in percentages]

        entries = [self._to_unified(c, color_in_format) for c in colors_raw]

        # ── Chroma filter (OKLCH C) ──────────────────────────────────
        best_idx       = max(range(len(entries)), key=lambda i: entries[i]["oklch_c"])
        best           = entries[best_idx]
        is_desaturated = best["oklch_c"] < chroma_threshold
        representative_hex = self._rgb_to_hex(best["r"], best["g"], best["b"])

        kept = [
            (e, p) for e, p in zip(entries, percentages)
            if e["oklch_c"] >= chroma_threshold
        ]

        kept_total = sum(p for _, p in kept) or 1.0
        filtered_color = json.dumps([
            self._format_entry(e, p / kept_total, color_out_format)
            for e, p in kept
        ], ensure_ascii=False)

        # ── WCAG weighted luminance ──────────────────────────────────
        weighted_lum = sum(
            self._wcag_luminance(e["r"], e["g"], e["b"]) * p
            for e, p in zip(entries, percentages)
        )
        lum_threshold = float(luminance_threshold.split()[0])
        brightness    = "bright" if weighted_lum > lum_threshold else "dark"

        preview = self._make_preview(entries, percentages, best_idx, is_desaturated, chroma_threshold)

        return (filtered_color, representative_hex, brightness, is_desaturated, preview)

    # ------------------------------------------------------------------
    # Color parsing / conversion
    # ------------------------------------------------------------------

    def _format_entry(self, e: dict, weight: float, fmt: str) -> dict:
        """Serialize a unified entry to the requested output format."""
        hex_val = self._rgb_to_hex(e["r"], e["g"], e["b"])
        w = round(weight, 4)
        if fmt == "RGB":
            return {"r": round(e["r"], 4), "g": round(e["g"], 4), "b": round(e["b"], 4),
                    "hex": hex_val, "weight": w}
        elif fmt == "HEX":
            return {"hex": hex_val, "weight": w}
        else:  # HSV (default)
            return {"h": round(e["h"] * 360.0, 2), "s": round(e["s"], 4), "v": round(e["v"], 4),
                    "hex": hex_val, "weight": w}

    def _to_unified(self, raw, fmt: str) -> dict:
        if fmt == "HEX":
            r, g, b = self._parse_hex(raw)
        elif fmt == "HSV":
            r, g, b = colorsys.hsv_to_rgb(
                raw[0] / 179.0, raw[1] / 255.0, raw[2] / 255.0
            )
        else:  # RGB 0-1
            r, g, b = float(raw[0]), float(raw[1]), float(raw[2])

        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        oklch_c = self._rgb_to_oklch_c(r, g, b)
        return {"r": r, "g": g, "b": b, "h": h, "s": s, "v": v, "oklch_c": oklch_c}

    def _parse_hex(self, hex_str: str) -> Tuple[float, float, float]:
        h = str(hex_str).strip().lstrip("#")
        return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0

    def _rgb_to_hex(self, r: float, g: float, b: float) -> str:
        return "#{:02x}{:02x}{:02x}".format(
            max(0, min(255, round(r * 255))),
            max(0, min(255, round(g * 255))),
            max(0, min(255, round(b * 255))),
        )

    # ------------------------------------------------------------------
    # OKLCH chroma
    # ------------------------------------------------------------------

    @staticmethod
    def _rgb_to_oklch_c(r: float, g: float, b: float) -> float:
        """Return OKLCH chroma C for an sRGB color (0~1 each). Range ~0~0.4."""
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

        return math.sqrt(ok_a ** 2 + ok_b ** 2)

    # ------------------------------------------------------------------
    # WCAG luminance
    # ------------------------------------------------------------------

    @staticmethod
    def _linearize(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    def _wcag_luminance(self, r: float, g: float, b: float) -> float:
        return (
            0.2126 * self._linearize(r)
            + 0.7152 * self._linearize(g)
            + 0.0722 * self._linearize(b)
        )

    # ------------------------------------------------------------------
    # Preview image
    # ------------------------------------------------------------------

    def _make_preview(
        self,
        entries: List[dict],
        percentages: List[float],
        best_idx: int,
        is_desaturated: bool,
        chroma_threshold: float,
    ) -> torch.Tensor:
        from PIL import Image, ImageDraw

        W, H    = 512, 96
        STRIP_Y = 36

        img  = Image.new("RGB", (W, H), (24, 24, 24))
        draw = ImageDraw.Draw(img)

        x = 0
        segs = []
        for entry, pct in zip(entries, percentages):
            w = max(1, round(pct * W))
            if x + w > W:
                w = W - x
            r8 = max(0, min(255, round(entry["r"] * 255)))
            g8 = max(0, min(255, round(entry["g"] * 255)))
            b8 = max(0, min(255, round(entry["b"] * 255)))
            draw.rectangle([x, STRIP_Y, x + w - 1, H - 1], fill=(r8, g8, b8))
            segs.append((x, x + w, entry, entry["oklch_c"] < chroma_threshold))
            x += w

        if x < W and entries:
            last = entries[-1]
            draw.rectangle([x, STRIP_Y, W - 1, H - 1], fill=(
                max(0, min(255, round(last["r"] * 255))),
                max(0, min(255, round(last["g"] * 255))),
                max(0, min(255, round(last["b"] * 255))),
            ))

        # White border on kept colors
        for x0, x1, _, filtered_out in segs:
            if not filtered_out:
                draw.rectangle([x0, STRIP_Y, x1 - 1, H - 1], outline=(255, 255, 255), width=2)

        # Triangle above highest-chroma kept color
        if not is_desaturated and best_idx < len(segs):
            x0, x1, _, _ = segs[best_idx]
            cx = (x0 + x1) // 2
            tri = [(cx, STRIP_Y - 2), (cx - 7, 8), (cx + 7, 8)]
            draw.polygon(tri, fill=(255, 255, 255))

        arr = np.array(img, dtype=np.float32) / 255.0
        return torch.from_numpy(arr).unsqueeze(0)
