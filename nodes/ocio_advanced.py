"""
Advanced OCIO Color Tools Node

This module contains the AdvancedOcioColorTransform node, giving granular control
over OCIO color conversions with a staged pipeline.
"""

import torch
import numpy as np
from typing import Tuple, List
import os

try:
    import PyOpenColorIO as ocio
    from .ocio_defs import OCIO_SPACES
    print(f"[Color Tools] ✅ OCIO_SPACES loaded: {len(OCIO_SPACES)} spaces")
except ImportError as e:
    print(f"[Color Tools] ❌ Failed to import OCIO dependencies: {e}")
    print("[Color Tools] ❌ Advanced OCIO node will not be available.")
    ocio = None
    OCIO_SPACES = ["sRGB", "Linear", "raw"]

# Mapping from display spaces to their linear equivalents
DISPLAY_TO_LINEAR_MAP = {
    "sRGB": "Linear",
    "Rec.709": "Linear Rec.709",
    "Rec.2020": "Linear Rec.2020",
    "Display P3": "Linear P3-D65",
    "Adobe RGB": "Linear P3-D65",
    "raw": "raw",
    "Linear": "Linear",
    "Linear Rec.709": "Linear Rec.709",
    "Linear Rec.2020": "Linear Rec.2020",
    "Linear P3-D65": "Linear P3-D65",
    "Log2": "Linear",
    "XYZ": "Linear",
}


def get_linear_equivalent(space_name: str) -> str:
    """Finds the linear version of a display space, or returns it if already linear."""
    return DISPLAY_TO_LINEAR_MAP.get(space_name, space_name)


def _apply_gamut_compress(img: np.ndarray, threshold: float, power: float, scale: float) -> np.ndarray:
    """
    Parametric gamut compression using a smooth power curve.

    Compresses per-channel values that exceed `threshold` toward 1.0.
    ocio.GamutCompressTransform does not exist in released PyOpenColorIO builds,
    so this is a pure-numpy replacement.

    Args:
        img:       float32 array (H, W, 3), values typically 0-1 but may exceed range
        threshold: value above which compression begins (e.g. 0.85)
        power:     curve sharpness — higher = harder knee (e.g. 1.15)
        scale:     controls how far beyond 1.0 maps to the ceiling (e.g. 0.9)
    """
    result = img.copy()
    mask = result > threshold
    if np.any(mask):
        headroom = 1.0 - threshold
        span = headroom / max(scale, 1e-6)
        # Normalised excess in [0, inf)
        t = np.where(mask, (result - threshold) / span, 0.0)
        # Soft-knee: t / (1 + t^power)^(1/power)  →  asymptotically approaches 1.0
        t_compressed = t / np.power(1.0 + np.power(t, power), 1.0 / max(power, 1e-4))
        result = np.where(mask, threshold + t_compressed * span, result)
    return result


class AdvancedOcioColorTransform:
    """
    An advanced OCIO node for fine-grained control over color space conversions.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "source_space": (OCIO_SPACES, {"default": "sRGB"}),
                "dest_space": (OCIO_SPACES, {"default": "sRGB"}),
                "fix_transfer": ("BOOLEAN", {"default": True}),
                "fix_gamut": ("BOOLEAN", {"default": True}),
                "gamut_compress": ("BOOLEAN", {"default": False}),
                "gc_threshold": ("FLOAT", {"default": 0.85, "min": 0.0, "max": 1.0, "step": 0.01}),
                "gc_power": ("FLOAT", {"default": 1.15, "min": 0.01, "max": 5.0, "step": 0.01}),
                "gc_scale": ("FLOAT", {"default": 0.9, "min": 0.01, "max": 2.0, "step": 0.01}),
                "alpha_mode": (["passthrough", "premultiply"], {"default": "passthrough"}),
                "clip_after": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "ocio_config_path": ("STRING", {"default": "default", "multiline": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "transform_info")
    FUNCTION = "transform_image"
    CATEGORY = "Color Tools/OCIO"

    def transform_image(self, image: torch.Tensor, source_space: str, dest_space: str,
                        fix_transfer: bool, fix_gamut: bool, gamut_compress: bool,
                        gc_threshold: float, gc_power: float, gc_scale: float,
                        alpha_mode: str, clip_after: bool,
                        ocio_config_path: str = "default") -> Tuple[torch.Tensor, str]:

        if ocio is None:
            raise ImportError("PyOpenColorIO is required for this node to work.")

        # Load OCIO configuration
        try:
            if ocio_config_path != "default" and os.path.exists(ocio_config_path):
                config = ocio.Config.CreateFromFile(ocio_config_path)
            else:
                bundled_config_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "ocio", "config.ocio"
                )
                config = ocio.Config.CreateFromFile(bundled_config_path)
        except Exception as e:
            return image, f"Failed to load OCIO config: {str(e)}"

        # Prepare image
        h, w, c = image.shape[-3], image.shape[-2], image.shape[-1]
        img_np = image[0].cpu().numpy() if len(image.shape) == 4 else image.cpu().numpy()

        alpha = img_np[:, :, 3:4].copy() if c == 4 else None
        img_rgb = img_np[:, :, :3].copy().astype(np.float32)

        if alpha_mode == "premultiply" and alpha is not None:
            img_rgb *= alpha

        # Build the OCIO transform pipeline
        transforms = []
        current_space = source_space

        source_linear = get_linear_equivalent(source_space)
        dest_linear = get_linear_equivalent(dest_space)

        # Stage A: Decode transfer (non-linear → linear)
        if fix_transfer and current_space != source_linear:
            transforms.append(ocio.ColorSpaceTransform(src=current_space, dst=source_linear))
            current_space = source_linear

        # Stage B: Change primaries (gamut)
        if fix_gamut and source_linear != dest_linear:
            transforms.append(ocio.ColorSpaceTransform(src=current_space, dst=dest_linear))
            current_space = dest_linear

        # Stage C: Encode transfer (linear → target non-linear)
        if fix_transfer and current_space != dest_space:
            transforms.append(ocio.ColorSpaceTransform(src=current_space, dst=dest_space))
            current_space = dest_space

        if not transforms:
            if not gamut_compress:
                return image, "No conversion needed. All toggles were off or spaces matched."
        else:
            # Apply OCIO transforms using PackedImageDesc (fast bulk operation)
            try:
                group_transform = ocio.GroupTransform(transforms)
                processor = config.getProcessor(group_transform)
                cpu_processor = processor.getDefaultCPUProcessor()

                img_f32 = np.ascontiguousarray(img_rgb, dtype=np.float32)
                image_desc = ocio.PackedImageDesc(img_f32, w, h, 3)
                cpu_processor.apply(image_desc)
                img_rgb = img_f32
            except Exception as e:
                return image, f"Failed to apply OCIO transform: {str(e)}"

        # Gamut compression (numpy — ocio.GamutCompressTransform is not in released OCIO builds)
        if gamut_compress:
            img_rgb = _apply_gamut_compress(img_rgb, gc_threshold, gc_power, gc_scale)

        if clip_after:
            img_rgb = np.clip(img_rgb, 0.0, 1.0)

        # Re-handle alpha
        if alpha is not None:
            if alpha_mode == "premultiply":
                img_rgb = img_rgb / np.maximum(alpha, 1e-8)
            final_img = np.concatenate([img_rgb, alpha], axis=2)
        else:
            final_img = img_rgb

        result_tensor = torch.from_numpy(final_img).float().unsqueeze(0)

        info = {
            "source": source_space,
            "destination": dest_space,
            "final_space": current_space,
            "stages": [t.__class__.__name__ for t in transforms],
            "gamut_compression": "on" if gamut_compress else "off",
        }

        return result_tensor, str(info)
