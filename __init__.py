"""
ComfyUI Color Tools

A comprehensive collection of color manipulation and analysis nodes for ComfyUI workflows.
"""

import os
import subprocess
import sys
import importlib.util

# Run the installation script before trying to import any nodes
install_script_path = os.path.join(os.path.dirname(__file__), "install.py")
try:
    print("[ComfyUI Color Tools]  initiator: Running installation script...")
    subprocess.check_call([sys.executable, install_script_path])
except (subprocess.CalledProcessError, FileNotFoundError) as e:
    print(f"[ComfyUI Color Tools] ⚠️  Initiator: Failed to run install script: {e}")

# Regenerate ocio_defs.py from the bundled config whenever PyOpenColorIO is available.
try:
    import PyOpenColorIO as _ocio_check  # noqa: F401
    _gen_script = os.path.join(os.path.dirname(__file__), "generate_ocio_defs.py")
    _ocio_config = os.path.join(os.path.dirname(__file__), "ocio", "config.ocio")
    _ocio_defs = os.path.join(os.path.dirname(__file__), "nodes", "ocio_defs.py")
    if os.path.exists(_gen_script) and os.path.exists(_ocio_config):
        _spec = importlib.util.spec_from_file_location("generate_ocio_defs", _gen_script)
        _gen_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_gen_mod)
        _gen_mod.generate_defs(_ocio_config, _ocio_defs)
        print("[ComfyUI Color Tools] ✅ ocio_defs.py regenerated from bundled config")
except Exception as _e:
    print(f"[ComfyUI Color Tools] ℹ️ Skipping ocio_defs regeneration: {_e}")

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# ── Each group has its own try/except so one bad import doesn't wipe everything ──

try:
    from .nodes.color_profile_reader import ColorProfileReader, GammaCompare
    from .nodes.color_profile_convert_simple import ColorProfileConvert
    from .nodes.color_converter_advanced import ColorConverterAdvanced
    NODE_CLASS_MAPPINGS.update({
        "ColorProfileReader": ColorProfileReader,
        "GammaCompare": GammaCompare,
        "ColorProfileConvert": ColorProfileConvert,
        "ColorConverterAdvanced": ColorConverterAdvanced,
    })
except Exception as e:
    print(f"[ComfyUI Color Tools] ⚠️ Profile reader nodes unavailable: {e}")

try:
    from .nodes.littlecms_converter import LittleCMSColorProfileConverter
    from .nodes.quick_color_fix import QuickColorSpaceFix
    NODE_CLASS_MAPPINGS.update({
        "LittleCMSColorProfileConverter": LittleCMSColorProfileConverter,
        "QuickColorSpaceFix": QuickColorSpaceFix,
    })
except Exception as e:
    print(f"[ComfyUI Color Tools] ⚠️ LittleCMS nodes unavailable: {e}")

try:
    from .nodes.color_conversion import ColorSpaceConverter, ColorTemperature, ColorSpaceAnalyzer
    from .nodes.rgb_hex_adjust import RGBHexAdjust
    NODE_CLASS_MAPPINGS.update({
        "ColorSpaceConverter": ColorSpaceConverter,
        "ColorTemperature": ColorTemperature,
        "ColorSpaceAnalyzer": ColorSpaceAnalyzer,
        "RGBHexAdjust": RGBHexAdjust,
    })
except Exception as e:
    print(f"[ComfyUI Color Tools] ⚠️ Color conversion nodes unavailable: {e}")

try:
    from .nodes.color_grading import ColorBalance, BrightnessContrast, Saturation, HueShift, GammaCorrection
    NODE_CLASS_MAPPINGS.update({
        "ColorBalance": ColorBalance,
        "BrightnessContrast": BrightnessContrast,
        "Saturation": Saturation,
        "HueShift": HueShift,
        "GammaCorrection": GammaCorrection,
    })
except Exception as e:
    print(f"[ComfyUI Color Tools] ⚠️ Color grading nodes unavailable: {e}")

try:
    from .nodes.color_analysis import (
        DominantColors, DominantColorsAdvanced, DominantColorsAdvancedMultiple,
        ColorHistogram, ColorPalette, ColorSimilarity, ColorHarmony,
        LuminanceCalculator, CollageBackgroundColor,
    )
    from .nodes.natural_background_color import NaturalBackgroundColor
    from .nodes.rgb_array_resolve import RGBArrayResolve
    NODE_CLASS_MAPPINGS.update({
        "DominantColors": DominantColors,
        "DominantColorsAdvanced": DominantColorsAdvanced,
        "DominantColorsAdvancedMultiple": DominantColorsAdvancedMultiple,
        "ColorHistogram": ColorHistogram,
        "ColorPalette": ColorPalette,
        "ColorSimilarity": ColorSimilarity,
        "ColorHarmony": ColorHarmony,
        "LuminanceCalculator": LuminanceCalculator,
        "CollageBackgroundColor": CollageBackgroundColor,
        "NaturalBackgroundColor": NaturalBackgroundColor,
        "RGBArrayResolve": RGBArrayResolve,
    })
except Exception as e:
    print(f"[ComfyUI Color Tools] ⚠️ Color analysis nodes unavailable: {e}")

try:
    from .nodes.color_space_inspector import ColorSpaceInspector
    NODE_CLASS_MAPPINGS["ColorSpaceInspector"] = ColorSpaceInspector
except Exception as e:
    print(f"[ComfyUI Color Tools] ⚠️ ColorSpaceInspector unavailable: {e}")

try:
    from .nodes.vector_scope import VectorScopeNode
    NODE_CLASS_MAPPINGS["VectorScope"] = VectorScopeNode
except Exception as e:
    print(f"[ComfyUI Color Tools] ⚠️ Vector scope node unavailable: {e}")

# ── OCIO nodes (require PyOpenColorIO) ────────────────────────────────────────
try:
    from .nodes.ocio_tools import OCIOColorSpaceConverter, OCIOConfigInfo, TestPatternGenerator
    from .nodes.ocio_advanced import AdvancedOcioColorTransform
    NODE_CLASS_MAPPINGS.update({
        "OCIOColorSpaceConverter": OCIOColorSpaceConverter,
        "OCIOConfigInfo": OCIOConfigInfo,
        "TestPatternGenerator": TestPatternGenerator,
        "AdvancedOcioColorTransform": AdvancedOcioColorTransform,
    })
    print("[ComfyUI Color Tools] ✅ OCIO nodes registered")
except Exception as e:
    print(f"[ComfyUI Color Tools] ⚠️ OCIO nodes unavailable (install PyOpenColorIO to enable): {e}")

# ── Display names for all registered nodes ────────────────────────────────────
_ALL_DISPLAY_NAMES = {
    "ColorProfileReader": "Read Image Color Profile",
    "GammaCompare": "Compare Image Gamma Values",
    "ColorProfileConvert": "Convert Image Color Space",
    "ColorConverterAdvanced": "Advanced Color Converter",
    "LittleCMSColorProfileConverter": "LittleCMS Color Profile Converter",
    "QuickColorSpaceFix": "Quick Color Space Fix",
    "ColorSpaceConverter": "Color Space Converter",
    "ColorTemperature": "Color Temperature",
    "ColorSpaceAnalyzer": "Color Space Analyzer",
    "RGBHexAdjust": "RGB/HEX Convert + Adjust",
    "ColorBalance": "Color Balance",
    "BrightnessContrast": "Brightness/Contrast",
    "Saturation": "Saturation",
    "HueShift": "Hue Shift",
    "GammaCorrection": "Gamma Correction",
    "DominantColors": "Dominant Colors",
    "DominantColorsAdvanced": "Dominant Colors Advanced",
    "DominantColorsAdvancedMultiple": "Dominant Colors Advanced (Multiple)",
    "ColorHistogram": "Color Histogram",
    "ColorPalette": "Color Palette",
    "ColorSimilarity": "Color Similarity",
    "ColorHarmony": "Color Harmony",
    "LuminanceCalculator": "Luminance Calculator",
    "CollageBackgroundColor": "Collage Background Color",
    "NaturalBackgroundColor": "Color Harmonizer",
    "RGBArrayResolve": "RGB Array Resolve",
    "ColorSpaceInspector": "Color Space Inspector",
    "VectorScope": "Vector Scope",
    "OCIOColorSpaceConverter": "OCIO Color Space Converter",
    "OCIOConfigInfo": "OCIO Config Info",
    "TestPatternGenerator": "Test Pattern Generator",
    "AdvancedOcioColorTransform": "Advanced OCIO Color Transform",
}

# Only expose display names for nodes that actually loaded
NODE_DISPLAY_NAME_MAPPINGS = {
    k: v for k, v in _ALL_DISPLAY_NAMES.items() if k in NODE_CLASS_MAPPINGS
}

print(f"[ComfyUI Color Tools] --- Registration ---")
print(f"[ComfyUI Color Tools] ✅ Registered {len(NODE_CLASS_MAPPINGS)} nodes.")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
