"""
Color Space Inspector Node

Input a single color in any common color space, convert it to all supported spaces,
and generate a 512x512 preview image with an info bar.
"""

import json
import math
import numpy as np
import torch


class ColorSpaceInspector:
    """
    输入单色（RGB / HEX / HSV / HSL / LAB / CMYK），
    自动转换到所有常用颜色空间，并生成 512×512 预览图。
    """

    DESCRIPTION = (
        "输入单色（RGB/HEX/HSV/HSL/LAB/CMYK），转换到所有常用颜色空间，\n"
        "并生成 512×512 预览图（色块 + 信息条）。\n\n"
        "【输入模式】\n"
        "• rgb：R/G/B 各 0~255\n"
        "• hex：十六进制字符串，如 #ff3a2b 或 ff3a2b\n"
        "• hsv：H 0~360°，S/V 0~1\n"
        "• hsl：H 0~360°，S/L 0~1\n"
        "• lab：L 0~100，a/b -128~127\n"
        "• cmyk：C/M/Y/K 0~1\n\n"
        "【输出】\n"
        "• preview_image：512×512 色块预览\n"
        "• hex_out：十六进制颜色字符串\n"
        "• r / g / b：RGB 各通道值（0~255）\n"
        "• out_json：包含所有颜色空间转换结果的 JSON"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_mode": (["rgb", "hex", "hsv", "hsl", "lab", "cmyk"], {"default": "hex"}),
                "luminance_threshold": (
                    [
                        "0.350  (perceptual)",
                        "0.200  (conservative)",
                        "0.179  (WCAG precise)",
                    ],
                    {"default": "0.350  (perceptual)"},
                ),
            },
            "optional": {
                # RGB
                "r":      ("INT",   {"default": 255,  "min": 0,    "max": 255,   "step": 1}),
                "g":      ("INT",   {"default": 100,  "min": 0,    "max": 255,   "step": 1}),
                "b":      ("INT",   {"default": 50,   "min": 0,    "max": 255,   "step": 1}),
                # HEX
                "hex_color": ("STRING", {"default": "#ff6432"}),
                # HSV
                "hsv_h":  ("FLOAT", {"default": 0.0,  "min": 0.0,  "max": 360.0, "step": 0.1}),
                "hsv_s":  ("FLOAT", {"default": 1.0,  "min": 0.0,  "max": 1.0,   "step": 0.01}),
                "hsv_v":  ("FLOAT", {"default": 1.0,  "min": 0.0,  "max": 1.0,   "step": 0.01}),
                # HSL
                "hsl_h":  ("FLOAT", {"default": 0.0,  "min": 0.0,  "max": 360.0, "step": 0.1}),
                "hsl_s":  ("FLOAT", {"default": 1.0,  "min": 0.0,  "max": 1.0,   "step": 0.01}),
                "hsl_l":  ("FLOAT", {"default": 0.5,  "min": 0.0,  "max": 1.0,   "step": 0.01}),
                # LAB
                "lab_L":  ("FLOAT", {"default": 50.0, "min": 0.0,  "max": 100.0, "step": 0.1}),
                "lab_a":  ("FLOAT", {"default": 0.0,  "min": -128.0, "max": 127.0, "step": 0.1}),
                "lab_b":  ("FLOAT", {"default": 0.0,  "min": -128.0, "max": 127.0, "step": 0.1}),
                # CMYK
                "cmyk_c": ("FLOAT", {"default": 0.0,  "min": 0.0,  "max": 1.0,   "step": 0.01}),
                "cmyk_m": ("FLOAT", {"default": 0.0,  "min": 0.0,  "max": 1.0,   "step": 0.01}),
                "cmyk_y": ("FLOAT", {"default": 0.0,  "min": 0.0,  "max": 1.0,   "step": 0.01}),
                "cmyk_k": ("FLOAT", {"default": 0.0,  "min": 0.0,  "max": 1.0,   "step": 0.01}),
            }
        }

    RETURN_TYPES  = ("IMAGE", "STRING", "FLOAT", "FLOAT", "FLOAT", "STRING", "STRING")
    RETURN_NAMES  = ("preview_image", "hex_out", "r", "g", "b", "luminance_theme", "out_json")
    FUNCTION      = "inspect"
    CATEGORY      = "Color Tools/Analysis"

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

    def inspect(
        self,
        input_mode: str,
        luminance_threshold: str = "0.350  (perceptual)",
        r: int = 255, g: int = 100, b: int = 50,
        hex_color: str = "#ff6432",
        hsv_h: float = 0.0, hsv_s: float = 1.0, hsv_v: float = 1.0,
        hsl_h: float = 0.0, hsl_s: float = 1.0, hsl_l: float = 0.5,
        lab_L: float = 50.0, lab_a: float = 0.0, lab_b: float = 0.0,
        cmyk_c: float = 0.0, cmyk_m: float = 0.0, cmyk_y: float = 0.0, cmyk_k: float = 0.0,
    ):
        # 1. Parse input → RGB (0-255 ints)
        r_out, g_out, b_out = self._parse_input(
            input_mode,
            r, g, b,
            hex_color,
            hsv_h, hsv_s, hsv_v,
            hsl_h, hsl_s, hsl_l,
            lab_L, lab_a, lab_b,
            cmyk_c, cmyk_m, cmyk_y, cmyk_k,
        )

        # 2. HEX output
        hex_out = "#{:02x}{:02x}{:02x}".format(r_out, g_out, b_out)

        # 3. Convert to all spaces
        all_spaces = self._convert_all(r_out, g_out, b_out)

        # 4. WCAG luminance + theme
        rf, gf, bf = r_out / 255.0, g_out / 255.0, b_out / 255.0
        def _linearize(c):
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        wcag_luminance = 0.2126 * _linearize(rf) + 0.7152 * _linearize(gf) + 0.0722 * _linearize(bf)
        threshold = float(luminance_threshold.split()[0])
        luminance_theme = "light" if wcag_luminance > threshold else "dark"

        # 5. Build JSON (rgb + hex + luminance included)
        out_json = json.dumps(
            {
                "hex": hex_out,
                "rgb": {"r": r_out, "g": g_out, "b": b_out},
                "wcag_luminance": round(wcag_luminance, 6),
                **all_spaces,
            },
            ensure_ascii=False,
        )

        # 6. Generate 512×512 preview
        preview = self._make_preview(r_out, g_out, b_out, hex_out, all_spaces)

        return (preview, hex_out, float(r_out), float(g_out), float(b_out), luminance_theme, out_json)

    # ------------------------------------------------------------------
    # Input parsing
    # ------------------------------------------------------------------

    def _parse_input(
        self, mode,
        r, g, b,
        hex_color,
        hsv_h, hsv_s, hsv_v,
        hsl_h, hsl_s, hsl_l,
        lab_L, lab_a, lab_b,
        cmyk_c, cmyk_m, cmyk_y, cmyk_k,
    ):
        if mode == "rgb":
            return (int(r), int(g), int(b))
        elif mode == "hex":
            return self._hex_to_rgb(hex_color)
        elif mode == "hsv":
            return self._hsv_to_rgb(hsv_h, hsv_s, hsv_v)
        elif mode == "hsl":
            return self._hsl_to_rgb(hsl_h, hsl_s, hsl_l)
        elif mode == "lab":
            return self._lab_to_rgb(lab_L, lab_a, lab_b)
        elif mode == "cmyk":
            return self._cmyk_to_rgb(cmyk_c, cmyk_m, cmyk_y, cmyk_k)
        return (255, 255, 255)

    def _hex_to_rgb(self, hex_color: str):
        h = hex_color.strip().lstrip("#")
        if len(h) != 6:
            return (255, 255, 255)
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except ValueError:
            return (255, 255, 255)

    def _hsv_to_rgb(self, h, s, v):
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h / 360.0, s, v)
        return (self._clamp8(r * 255), self._clamp8(g * 255), self._clamp8(b * 255))

    def _hsl_to_rgb(self, h, s, l):
        import colorsys
        # colorsys uses HLS order
        r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
        return (self._clamp8(r * 255), self._clamp8(g * 255), self._clamp8(b * 255))

    def _lab_to_rgb(self, L, a, b_val):
        # LAB → XYZ (D65)
        fy = (L + 16.0) / 116.0
        fx = a / 500.0 + fy
        fz = fy - b_val / 200.0

        def f_inv(t):
            return t ** 3 if t > 0.206897 else (t - 16.0 / 116.0) / 7.787

        x = f_inv(fx) * 0.95047
        y = f_inv(fy) * 1.00000
        z = f_inv(fz) * 1.08883

        # XYZ → linear sRGB
        r_lin =  3.2406 * x - 1.5372 * y - 0.4986 * z
        g_lin = -0.9689 * x + 1.8758 * y + 0.0415 * z
        b_lin =  0.0557 * x - 0.2040 * y + 1.0570 * z

        def gamma(c):
            c = max(0.0, min(1.0, c))
            return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055

        return (
            self._clamp8(gamma(r_lin) * 255),
            self._clamp8(gamma(g_lin) * 255),
            self._clamp8(gamma(b_lin) * 255),
        )

    def _cmyk_to_rgb(self, c, m, y, k):
        r = 255 * (1 - c) * (1 - k)
        g = 255 * (1 - m) * (1 - k)
        b = 255 * (1 - y) * (1 - k)
        return (self._clamp8(r), self._clamp8(g), self._clamp8(b))

    def _clamp8(self, v):
        return max(0, min(255, round(v)))

    # ------------------------------------------------------------------
    # Conversions from RGB
    # ------------------------------------------------------------------

    def _convert_all(self, r: int, g: int, b: int) -> dict:
        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
        return {
            "hsv":   self._rgb_to_hsv(rf, gf, bf),
            "hsl":   self._rgb_to_hsl(rf, gf, bf),
            "lab":   self._rgb_to_lab(rf, gf, bf),
            "oklch": self._rgb_to_oklch(rf, gf, bf),
            "cmyk":  self._rgb_to_cmyk(rf, gf, bf),
        }

    def _rgb_to_hsv(self, r, g, b):
        import colorsys
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return {"h": round(h * 360, 2), "s": round(s, 4), "v": round(v, 4)}

    def _rgb_to_hsl(self, r, g, b):
        import colorsys
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return {"h": round(h * 360, 2), "s": round(s, 4), "l": round(l, 4)}

    def _rgb_to_lab(self, r, g, b):
        # sRGB → linear
        def linearize(c):
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        rl, gl, bl = linearize(r), linearize(g), linearize(b)

        # linear RGB → XYZ (D65)
        x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl
        y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
        z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl

        # XYZ → LAB
        xn, yn, zn = 0.95047, 1.00000, 1.08883

        def f(t):
            return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0

        fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
        L = 116.0 * fy - 16.0
        a = 500.0 * (fx - fy)
        b_out = 200.0 * (fy - fz)
        return {"L": round(L, 3), "a": round(a, 3), "b": round(b_out, 3)}

    def _rgb_to_oklch(self, r, g, b):
        # sRGB → linear
        def linearize(c):
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        rl, gl, bl = linearize(r), linearize(g), linearize(b)

        # linear RGB → LMS (Björn Ottosson 2020)
        l = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
        m = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
        s = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl

        l_ = l ** (1.0 / 3.0)
        m_ = m ** (1.0 / 3.0)
        s_ = s ** (1.0 / 3.0)

        ok_L =  0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
        ok_a =  1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
        ok_b =  0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

        C = math.sqrt(ok_a ** 2 + ok_b ** 2)
        H = math.degrees(math.atan2(ok_b, ok_a)) % 360.0

        return {"L": round(ok_L, 4), "c": round(C, 4), "h": round(H, 2)}

    def _rgb_to_cmyk(self, r, g, b):
        if r == 0.0 and g == 0.0 and b == 0.0:
            return {"c": 0.0, "m": 0.0, "y": 0.0, "k": 1.0}
        k = 1.0 - max(r, g, b)
        denom = 1.0 - k
        c = (1.0 - r - k) / denom
        m = (1.0 - g - k) / denom
        y = (1.0 - b - k) / denom
        return {
            "c": round(c, 4),
            "m": round(m, 4),
            "y": round(y, 4),
            "k": round(k, 4),
        }

    # ------------------------------------------------------------------
    # Preview image
    # ------------------------------------------------------------------

    def _make_preview(self, r: int, g: int, b: int, hex_out: str, all_spaces: dict):
        from PIL import Image, ImageDraw

        W, H = 512, 512

        rf, gf, bf = r / 255.0, g / 255.0, b / 255.0

        # WCAG perceptual luminance → choose text color (fixed threshold 0.35)
        lum = 0.2126 * rf + 0.7152 * gf + 0.0722 * bf
        use_dark_text = lum > 0.35
        text_rgb = (20, 20, 20)   if use_dark_text else (235, 235, 235)
        dim_rgb  = (80, 80, 80)   if use_dark_text else (180, 180, 180)

        # Solid color canvas
        img  = Image.new("RGB", (W, H), color=(r, g, b))
        draw = ImageDraw.Draw(img)

        font_title = self._load_font(26)
        font_body  = self._load_font(22)

        hsv   = all_spaces["hsv"]
        hsl   = all_spaces["hsl"]
        lab   = all_spaces["lab"]
        oklch = all_spaces["oklch"]
        cmyk  = all_spaces["cmyk"]

        lines = [
            # (label, value, font)
            (f"{hex_out.upper()}  ", f"RGB({r}, {g}, {b})", font_title),
            (f"HSV   ", f"h:{hsv['h']}°  s:{hsv['s']}  v:{hsv['v']}",           font_body),
            (f"HSL   ", f"h:{hsl['h']}°  s:{hsl['s']}  l:{hsl['l']}",           font_body),
            (f"LAB   ", f"L:{lab['L']}  a:{lab['a']}  b:{lab['b']}",             font_body),
            (f"OKLCH ", f"L:{oklch['L']}  c:{oklch['c']}  h:{oklch['h']}°",      font_body),
            (f"CMYK  ", f"c:{cmyk['c']}  m:{cmyk['m']}  y:{cmyk['y']}  k:{cmyk['k']}", font_body),
        ]

        x_pad  = 14
        y_pad  = 14
        line_h = 32

        for i, (label, value, font) in enumerate(lines):
            y = y_pad + i * line_h
            draw.text((x_pad, y), label, fill=text_rgb, font=font)
            try:
                lw = draw.textlength(label, font=font)
            except AttributeError:
                lw = len(label) * 8
            draw.text((x_pad + lw, y), value, fill=dim_rgb, font=font)

        arr = np.array(img, dtype=np.float32) / 255.0
        return torch.from_numpy(arr).unsqueeze(0)

    def _load_font(self, size: int):
        from PIL import ImageFont
        candidates = [
            # Windows
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()
