"""
Get Accent Color from Images

For each input image (batch or list), resizes to 512 long edge (only shrinks),
runs K-means on the sampled region, picks the cluster center with the highest
OKLCH chroma as the accent color, then computes WCAG luminance and
desaturation status.
"""

import json
import math
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.cluster import KMeans


# ---------------------------------------------------------------------------
# Module-level color math helpers
# ---------------------------------------------------------------------------

def _linearize(c: float) -> float:
    """sRGB component (0-1) → linear light (IEC 61966-2-1)."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgb_to_oklch(r: float, g: float, b: float):
    """
    sRGB (0-1) → OKLCH.
    Returns (L, C, h_degrees).
    Negative LMS values (float rounding) are handled with copysign before cbrt.
    """
    rl, gl, bl = _linearize(r), _linearize(g), _linearize(b)

    # linear RGB → LMS  (Björn Ottosson 2020)
    l = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    m = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    s = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl

    # cube root (guard against tiny negatives from float error)
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
    """sRGB (0-1) → WCAG relative luminance (0-1)."""
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _hex_to_rgb_float(hex_color: str):
    """'#rrggbb' → (r, g, b) floats in [0, 1]."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class GetAccentColorFromImages:
    """
    逐张分析图片，提取 accent color（OKLCH 彩度 C 最高的 K-means 聚类中心），
    并计算 WCAG 感知亮度和去饱和判断，按输入顺序输出 JSON 数组与预览。
    """

    DESCRIPTION = (
        "逐张分析图片，提取 accent color（OKLCH 彩度 C 最高的 K-means 聚类中心），\n"
        "并计算 WCAG 感知亮度和去饱和判断。\n\n"
        "【输入】\n"
        "• image：支持 batch tensor (B,H,W,3) 或 list（不同尺寸图片均可）\n\n"
        "【处理流程】\n"
        "1. 长边 > 512 时等比缩小，小图保持原尺寸\n"
        "2. 按 sample_mode 采样像素（full / edge / center）\n"
        "3. K-means(kmeans_k) 聚类\n"
        "4. 各聚类中心转 OKLCH，C 最大者为 accent color\n"
        "5. accent color → WCAG 亮度 → bright / dark\n"
        "6. accent color 的 OKLCH C < saturation_threshold → is_desaturated\n\n"
        "【输出】\n"
        "• result_json：每张图的分析结果数组（按输入顺序）\n"
        "• accent_color_preview：512×64 色条，每张图等宽一格，白色分隔线\n"
        "• sample_area_preview：采样区域预览 batch，绿色覆盖非采样区域\n\n"
        "【JSON 结构】\n"
        '[{"index":0,"accent_color":"#c45a1f","oklch_c":0.142,\n'
        '  "wcag_luminance":0.089,"brightness":"dark","is_desaturated":false}, ...]'
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "kmeans_k": ("INT", {
                    "default": 5, "min": 1, "max": 20, "step": 1,
                    "tooltip": "K-means 聚类数（k 值）",
                }),
                "sample_mode": (["full", "edge", "center"], {
                    "default": "full",
                    "tooltip": "full=全图  edge=外边缘带  center=中心区域",
                }),
                "edge_ratio": ("FLOAT", {
                    "default": 0.15, "min": 0.01, "max": 0.5, "step": 0.01,
                    "tooltip": "edge/center 模式下采样带宽占图像边长的比例（full 模式下忽略）",
                }),
                "luminance_threshold": (
                    [
                        "0.350  (perceptual)",
                        "0.200  (conservative)",
                        "0.179  (WCAG precise)",
                    ],
                    {"default": "0.350  (perceptual)"},
                ),
                "saturation_threshold": ("FLOAT", {
                    "default": 0.04, "min": 0.0, "max": 0.2, "step": 0.005,
                    "tooltip": "accent color 的 OKLCH C 低于此值时判定为去饱和（is_desaturated=true）",
                }),
            }
        }

    RETURN_TYPES = ("STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("result_json", "accent_color_preview", "sample_area_preview")
    FUNCTION = "analyze"
    CATEGORY = "Color Tools/Analysis"

    # Separator between color-strip bands
    _SEP_W = 2
    _SEP_COLOR = (1.0, 1.0, 1.0)  # white

    # Sample-area preview: green tint over non-sampled region
    _GREEN = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    _TINT_OPACITY = 0.8  # opacity of green tint on non-sampled area

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def analyze(
        self,
        image,
        kmeans_k: int,
        sample_mode: str,
        edge_ratio: float,
        luminance_threshold: str,
        saturation_threshold: float,
    ):
        lum_thresh = float(luminance_threshold.split()[0])
        frames = self._unpack(image)

        results = []
        accent_hex_list = []
        preview_frames = []   # (H, W, 3) numpy arrays, one per image

        for idx, frame in enumerate(frames):
            entry, preview_np = self._analyze_frame(
                frame, idx,
                kmeans_k, sample_mode, edge_ratio,
                lum_thresh, saturation_threshold,
            )
            results.append(entry)
            accent_hex_list.append(entry["accent_color"])
            preview_frames.append(preview_np)

        accent_strip   = self._make_color_strip(accent_hex_list)
        sample_preview = self._stack_previews(preview_frames)

        return (json.dumps(results, ensure_ascii=False), accent_strip, sample_preview)

    # ------------------------------------------------------------------
    # Unpack batch tensor or list → list of (H, W, 3) float32 numpy arrays
    # ------------------------------------------------------------------

    def _unpack(self, image) -> list:
        """
        Accepts:
          - torch.Tensor of shape (B, H, W, 3)  — standard ComfyUI batch
          - list/tuple of tensors, each (1, H, W, 3) or (H, W, 3)  — variable-size list
        Returns a list of (H, W, 3) float32 numpy arrays in [0, 1].
        """
        if isinstance(image, (list, tuple)):
            frames = []
            for item in image:
                t = item if isinstance(item, torch.Tensor) else torch.as_tensor(item)
                t = t.cpu().float()
                if t.ndim == 4:
                    for i in range(t.shape[0]):
                        frames.append(t[i].numpy())
                else:
                    frames.append(t.numpy())
            return frames

        # Single batch tensor (B, H, W, 3)
        t = image.cpu().float()
        return [t[i].numpy() for i in range(t.shape[0])]

    # ------------------------------------------------------------------
    # Per-frame analysis  →  (result_dict, preview_np)
    # ------------------------------------------------------------------

    def _analyze_frame(
        self,
        img: np.ndarray,
        idx: int,
        kmeans_k: int,
        sample_mode: str,
        edge_ratio: float,
        lum_thresh: float,
        sat_thresh: float,
    ):
        # 1. Ensure [0, 1] range
        if img.max() > 1.0:
            img = img / 255.0

        # 2. Resize (only shrink, long edge → 512)
        img = self._resize_512(img)

        # 3. Build sample-area preview (on the resized image, before K-means)
        preview_np = self._make_sample_preview(img, sample_mode, edge_ratio)

        # 4. Sample pixels
        pixels = self._sample_pixels(img, sample_mode, edge_ratio)  # (N, 3)

        # 5. K-means
        n_clusters = min(kmeans_k, len(pixels))
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        km.fit(pixels)
        centers = np.clip(km.cluster_centers_, 0.0, 1.0)  # (k, 3)

        # 6. Pick accent color: cluster center with highest OKLCH C
        best_idx = 0
        best_c = -1.0
        for i, center in enumerate(centers):
            _, C, _ = _rgb_to_oklch(float(center[0]), float(center[1]), float(center[2]))
            if C > best_c:
                best_c = C
                best_idx = i

        accent = centers[best_idx]
        r, g, b = float(accent[0]), float(accent[1]), float(accent[2])

        # 7. WCAG luminance → brightness
        lum = _wcag_luminance(r, g, b)
        brightness = "bright" if lum > lum_thresh else "dark"

        # 8. is_desaturated
        is_desat = bool(best_c < sat_thresh)

        # 9. HEX string
        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(round(r * 255)),
            int(round(g * 255)),
            int(round(b * 255)),
        )

        entry = {
            "index": idx,
            "accent_color": hex_color,
            "oklch_c": round(best_c, 4),
            "wcag_luminance": round(lum, 4),
            "brightness": brightness,
            "is_desaturated": is_desat,
        }
        return entry, preview_np

    # ------------------------------------------------------------------
    # Sample-area preview
    # Convention (matches DominantColorsAdvanced):
    #   sampled region   → original colors
    #   non-sampled area → green tint (TINT_OPACITY * green + (1-TINT_OPACITY) * original)
    # ------------------------------------------------------------------

    def _make_sample_preview(self, img: np.ndarray, sample_mode: str, edge_ratio: float) -> np.ndarray:
        """Returns (H, W, 3) float32 numpy array."""
        img = np.ascontiguousarray(img)
        H, W = img.shape[:2]
        tinted = self._TINT_OPACITY * self._GREEN + (1 - self._TINT_OPACITY) * img

        if sample_mode == "full":
            return img.copy()

        bh = max(1, int(H * edge_ratio))
        bw = max(1, int(W * edge_ratio))

        if sample_mode == "edge":
            # Non-sampled = center → apply tint there; edges stay original
            preview = tinted.copy()
            preview[:bh, :]          = img[:bh, :]
            preview[H - bh:, :]      = img[H - bh:, :]
            preview[bh:H-bh, :bw]    = img[bh:H-bh, :bw]
            preview[bh:H-bh, W-bw:]  = img[bh:H-bh, W-bw:]
        else:  # center
            # Non-sampled = edges → apply tint there; center stays original
            preview = tinted.copy()
            y0, y1 = bh, max(bh + 1, H - bh)
            x0, x1 = bw, max(bw + 1, W - bw)
            preview[y0:y1, x0:x1] = img[y0:y1, x0:x1]

        return np.clip(preview, 0.0, 1.0)

    # ------------------------------------------------------------------
    # Stack per-frame previews into a batch tensor
    # All frames are resized to the first frame's dimensions.
    # ------------------------------------------------------------------

    def _stack_previews(self, previews: list) -> torch.Tensor:
        if not previews:
            return torch.zeros(1, 64, 64, 3)

        target_H, target_W = previews[0].shape[:2]
        tensors = []

        for p in previews:
            if p.shape[:2] != (target_H, target_W):
                t = torch.from_numpy(p).permute(2, 0, 1).unsqueeze(0).float()
                t = F.interpolate(t, size=(target_H, target_W), mode="bilinear", align_corners=False)
                p = t.squeeze(0).permute(1, 2, 0).numpy()
            tensors.append(torch.from_numpy(p).float())

        return torch.stack(tensors, dim=0)  # (B, H, W, 3)

    # ------------------------------------------------------------------
    # Color strip preview: 512×64, one equal-width band per image
    # ------------------------------------------------------------------

    def _make_color_strip(self, hex_colors: list) -> torch.Tensor:
        """
        Build a 512×64 horizontal color strip.
        Each image gets an equal-width color band, separated by white lines.
        Returns a (1, 64, 512, 3) float32 tensor.
        """
        W, H = 512, 64
        n = len(hex_colors)
        canvas = np.zeros((H, W, 3), dtype=np.float32)

        if n == 0:
            return torch.from_numpy(canvas).unsqueeze(0)

        total_sep = self._SEP_W * (n - 1)
        usable_w = W - total_sep
        band_w = usable_w / n

        for i, hex_color in enumerate(hex_colors):
            offset = i * self._SEP_W
            x0 = offset + int(round(i * band_w))
            x1 = offset + int(round((i + 1) * band_w))
            x1 = max(x1, x0 + 1)
            x1 = min(x1, W)
            r, g, b = _hex_to_rgb_float(hex_color)
            canvas[:, x0:x1, 0] = r
            canvas[:, x0:x1, 1] = g
            canvas[:, x0:x1, 2] = b

            # Draw separator after this band (except after the last one)
            if i < n - 1:
                sx0 = x1
                sx1 = min(sx0 + self._SEP_W, W)
                canvas[:, sx0:sx1, 0] = self._SEP_COLOR[0]
                canvas[:, sx0:sx1, 1] = self._SEP_COLOR[1]
                canvas[:, sx0:sx1, 2] = self._SEP_COLOR[2]

        return torch.from_numpy(canvas).unsqueeze(0).float()

    # ------------------------------------------------------------------
    # Resize: shrink only, long edge → 512
    # ------------------------------------------------------------------

    def _resize_512(self, img: np.ndarray) -> np.ndarray:
        H, W = img.shape[:2]
        if max(H, W) <= 512:
            return img
        scale = 512.0 / max(H, W)
        new_H = max(1, int(round(H * scale)))
        new_W = max(1, int(round(W * scale)))
        t = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).float()
        t = F.interpolate(t, size=(new_H, new_W), mode="bilinear", align_corners=False)
        return t.squeeze(0).permute(1, 2, 0).numpy()

    # ------------------------------------------------------------------
    # Pixel sampling
    # ------------------------------------------------------------------

    def _sample_pixels(self, img: np.ndarray, sample_mode: str, edge_ratio: float) -> np.ndarray:
        if sample_mode == "full":
            return img.reshape(-1, 3)

        H, W = img.shape[:2]
        bh = max(1, int(H * edge_ratio))
        bw = max(1, int(W * edge_ratio))

        if sample_mode == "edge":
            top    = img[:bh,       :,        :].reshape(-1, 3)
            bottom = img[H - bh:,   :,        :].reshape(-1, 3)
            left   = img[bh:H - bh, :bw,      :].reshape(-1, 3)
            right  = img[bh:H - bh, W - bw:,  :].reshape(-1, 3)
            return np.concatenate([top, bottom, left, right], axis=0)

        # center
        y0, y1 = bh, max(bh + 1, H - bh)
        x0, x1 = bw, max(bw + 1, W - bw)
        return img[y0:y1, x0:x1, :].reshape(-1, 3)
