"""
Accent Color Matcher

Matches a reference color (HEX) against a list of accent colors from
GetAccentColorFromImages result_json, ranking by hue or hue+brightness.
"""

import json
import math
import numpy as np
import torch


# ---------------------------------------------------------------------------
# Color math helpers (module-level, no external deps)
# ---------------------------------------------------------------------------

def _linearize(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgb_to_oklch(r: float, g: float, b: float):
    """sRGB (0-1) → (L, C, h_degrees)."""
    rl, gl, bl = _linearize(r), _linearize(g), _linearize(b)

    l = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    m = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    s = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl

    l_ = math.copysign(abs(l) ** (1.0 / 3.0), l)
    m_ = math.copysign(abs(m) ** (1.0 / 3.0), m)
    s_ = math.copysign(abs(s) ** (1.0 / 3.0), s)

    ok_L =  0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    ok_a =  1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    ok_b =  0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    C = math.sqrt(ok_a ** 2 + ok_b ** 2)
    h = math.degrees(math.atan2(ok_b, ok_a)) % 360.0
    return ok_L, C, h


def _wcag_luminance(r: float, g: float, b: float) -> float:
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _hex_to_rgb(hex_color: str):
    h = hex_color.strip().lstrip("#")
    return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0


def _hue_dist(h1: float, h2: float) -> float:
    """Circular angular distance between two hue angles (0-360), result in [0, 180]."""
    d = abs(h1 - h2) % 360.0
    return min(d, 360.0 - d)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class AccentColorMatcher:
    """
    将参考色（HEX）与 GetAccentColorFromImages 输出的颜色列表匹配，
    按匹配程度从高到低输出排名结果。
    """

    DESCRIPTION = (
        "将参考色与 GetAccentColorFromImages result_json 中的颜色进行匹配，\n"
        "按匹配程度从高到低输出排名。\n\n"
        "【match_method】\n"
        "• hue_only：\n"
        "  仅按 OKLCH 色相角距离排名，忽略亮度与去饱和状态\n"
        "• hue_and_brightness：\n"
        "  - ref 非去饱和：取色相最近前两名，再按 brightness 匹配唯一最佳；\n"
        "    若两者 brightness 相同或均不匹配，则按 WCAG 亮度接近度决胜\n"
        "  - ref 去饱和：改为按 WCAG 亮度接近度排名\n\n"
        "【desaturated_fallback】\n"
        "  ref_color 是否被判定为去饱和，供下游逻辑决定是否走 fallback 分支，\n"
        "  与 match_method 无关，始终输出"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ref_color_hex": ("STRING", {
                    "forceInput": True,
                    "tooltip": "参考色，HEX 格式 #rrggbb，外部输入",
                }),
                "compare_color_json": ("STRING", {
                    "forceInput": True,
                    "tooltip": "接 GetAccentColorFromImages 的 result_json 输出",
                }),
                "match_method": (
                    ["hue_only", "hue_and_brightness"],
                    {"default": "hue_and_brightness"},
                ),
                "saturation_threshold": ("FLOAT", {
                    "default": 0.04, "min": 0.0, "max": 0.2, "step": 0.005,
                    "tooltip": "ref_color 的 OKLCH C 低于此值时视为去饱和",
                }),
                "luminance_threshold": (
                    [
                        "0.350  (perceptual)",
                        "0.200  (conservative)",
                        "0.179  (WCAG precise)",
                    ],
                    {"default": "0.350  (perceptual)"},
                ),
            }
        }

    RETURN_TYPES  = ("INT",        "STRING",             "IMAGE",          "BOOLEAN")
    RETURN_NAMES  = ("best_index", "ranked_result_json", "ranked_preview", "ref_color_desaturated")
    FUNCTION      = "match"
    CATEGORY      = "Color Tools/Analysis"

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def match(
        self,
        ref_color_hex: str,
        compare_color_json: str,
        match_method: str,
        saturation_threshold: float,
        luminance_threshold: str,
    ):
        lum_thresh = float(luminance_threshold.split()[0])

        # ── Analyze ref_color ──────────────────────────────────────────
        ref_r, ref_g, ref_b = _hex_to_rgb(ref_color_hex)
        _, ref_C, ref_h     = _rgb_to_oklch(ref_r, ref_g, ref_b)
        ref_lum             = _wcag_luminance(ref_r, ref_g, ref_b)
        ref_brightness      = "bright" if ref_lum > lum_thresh else "dark"
        ref_desaturated     = ref_C < saturation_threshold

        # ── Parse & enrich compare entries ────────────────────────────
        entries = json.loads(compare_color_json)
        if not entries:
            empty_preview = torch.zeros(1, 64, 512, 3)
            return (-1, "[]", empty_preview, ref_desaturated)

        for e in entries:
            er, eg, eb   = _hex_to_rgb(e["accent_color"])
            _, _, e_h    = _rgb_to_oklch(er, eg, eb)
            e["_h"]      = e_h
            e["_hd"]     = _hue_dist(ref_h, e_h)
            e["_ld"]     = abs(ref_lum - e["wcag_luminance"])

        # ── Rank ───────────────────────────────────────────────────────
        ranked = self._rank(entries, match_method, ref_desaturated, ref_brightness)

        # ── Build outputs ─────────────────────────────────────────────
        best_index = ranked[0]["index"]

        ranked_result = [
            {
                "rank":          i + 1,
                "index":         e["index"],
                "accent_color":  e["accent_color"],
                "oklch_c":       e["oklch_c"],
                "wcag_luminance":e["wcag_luminance"],
                "brightness":    e["brightness"],
                "is_desaturated":e["is_desaturated"],
                "hue_dist":      round(e["_hd"], 2),
                "lum_diff":      round(e["_ld"], 4),
            }
            for i, e in enumerate(ranked)
        ]

        preview = self._make_preview(
            ref_color_hex,
            [e["accent_color"] for e in ranked],
        )

        return (
            best_index,
            json.dumps(ranked_result, ensure_ascii=False),
            preview,
            ref_desaturated,
        )

    # ------------------------------------------------------------------
    # Ranking logic
    # ------------------------------------------------------------------

    def _rank(self, entries: list, method: str, ref_desat: bool, ref_brightness: str) -> list:

        if method == "hue_only":
            return sorted(entries, key=lambda e: e["_hd"])

        # hue_and_brightness ──────────────────────────────────────────
        if ref_desat:
            # ref is achromatic: rank purely by luminance proximity
            return sorted(entries, key=lambda e: e["_ld"])

        # ref has color:
        # split into chromatic vs desaturated — hue of desaturated entries
        # is OKLCH noise and meaningless for hue comparison
        chromatic   = [e for e in entries if not e["is_desaturated"]]
        desaturated = [e for e in entries if     e["is_desaturated"]]

        # rank chromatic group: top-2 by hue → brightness tie-break
        if chromatic:
            hue_sorted = sorted(chromatic, key=lambda e: e["_hd"])
            top2       = hue_sorted[:2]
            rest       = hue_sorted[2:]
            winner     = self._pick_winner(top2, ref_brightness)
            others     = [e for e in top2 if e is not winner]
            ranked_chromatic = [winner] + others + rest
        else:
            ranked_chromatic = []

        # rank desaturated group: by luminance proximity (hue is meaningless)
        ranked_desat = sorted(desaturated, key=lambda e: e["_ld"])

        return ranked_chromatic + ranked_desat

    def _pick_winner(self, candidates: list, ref_brightness: str):
        """
        From at most 2 candidates (already top-2 by hue distance):
        - prefer the one whose brightness matches ref
        - if both match or neither matches: prefer closer WCAG luminance
        """
        if len(candidates) == 1:
            return candidates[0]

        a, b = candidates[0], candidates[1]
        a_match = a["brightness"] == ref_brightness
        b_match = b["brightness"] == ref_brightness

        if a_match and not b_match:
            return a
        if b_match and not a_match:
            return b
        # both match or neither: decide by luminance proximity
        return a if a["_ld"] <= b["_ld"] else b

    # ------------------------------------------------------------------
    # Preview: ref swatch | separator | ranked swatches
    # ------------------------------------------------------------------

    _REF_W    = 80   # width of ref color block
    _SEP_W    = 4    # width of main separator between ref and ranked list
    _BAND_SEP = 2    # width of separator between ranked bands
    _BORDER   = 2    # white border thickness on top and bottom

    def _make_preview(self, ref_hex: str, ranked_hex: list) -> torch.Tensor:
        """
        Layout (total 512×64):
          top border (BORDER px white)
          [ref_block: REF_W, labeled 'ref_color'] [sep: SEP_W] [ranked bands]
          bottom border (BORDER px white)
        Text color on ref block auto-selected by WCAG luminance.
        """
        from PIL import Image, ImageDraw, ImageFont

        W, H = 512, 64
        canvas = np.zeros((H, W, 3), dtype=np.float32)

        # top / bottom white borders
        canvas[:self._BORDER, :, :] = 1.0
        canvas[H - self._BORDER:, :, :] = 1.0

        # drawable row range (inside borders)
        y0, y1 = self._BORDER, H - self._BORDER

        # ref block
        rr, rg, rb = _hex_to_rgb(ref_hex)
        canvas[y0:y1, :self._REF_W, 0] = rr
        canvas[y0:y1, :self._REF_W, 1] = rg
        canvas[y0:y1, :self._REF_W, 2] = rb

        # main separator (full height for clean look)
        sep_end = self._REF_W + self._SEP_W
        canvas[:, self._REF_W:sep_end, :] = 1.0

        # ranked bands
        n = len(ranked_hex)
        if n > 0:
            avail      = W - sep_end
            total_gaps = self._BAND_SEP * (n - 1)
            band_w     = (avail - total_gaps) / n

            for i, hex_color in enumerate(ranked_hex):
                offset = sep_end + i * self._BAND_SEP
                x0 = offset + int(round(i * band_w))
                x1 = offset + int(round((i + 1) * band_w))
                x1 = max(x1, x0 + 1)
                x1 = min(x1, W)
                cr, cg, cb = _hex_to_rgb(hex_color)
                canvas[y0:y1, x0:x1, 0] = cr
                canvas[y0:y1, x0:x1, 1] = cg
                canvas[y0:y1, x0:x1, 2] = cb
                if i < n - 1:
                    gx0 = x1
                    gx1 = min(gx0 + self._BAND_SEP, W)
                    canvas[:, gx0:gx1, :] = 1.0

        # ── Draw "ref_color" label on ref block ───────────────────────
        # Convert canvas to PIL, draw text, convert back
        img_uint8 = (np.clip(canvas, 0, 1) * 255).astype(np.uint8)
        pil_img   = Image.fromarray(img_uint8, mode="RGB")
        draw      = ImageDraw.Draw(pil_img)

        # Auto text color: white on dark bg, black on light bg
        ref_lum    = _wcag_luminance(rr, rg, rb)
        text_color = (0, 0, 0) if ref_lum > 0.35 else (255, 255, 255)

        label = "ref_color"
        try:
            font = ImageFont.load_default(size=10)
        except TypeError:
            font = ImageFont.load_default()

        # Center text in the ref block
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (self._REF_W - tw) // 2
        ty = y0 + ((y1 - y0) - th) // 2
        draw.text((tx, ty), label, fill=text_color, font=font)

        canvas = np.array(pil_img, dtype=np.float32) / 255.0
        return torch.from_numpy(canvas).unsqueeze(0).float()
