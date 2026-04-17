"""
Color Tools Nodes Package

This package contains all the color manipulation and analysis nodes for ComfyUI.
Nodes are organized by functionality:
- color_profile_reader: Color profile reading and analysis nodes
- color_profile_convert: Color profile conversion nodes
- color_conversion: Color space conversion nodes
- color_grading: Color correction and grading nodes
- color_analysis: Color analysis and extraction nodes
- advanced_tools: Advanced color processing nodes
"""

# Import only the core nodes that have minimal dependencies
from .color_profile_reader import (
    ColorProfileReader,
    GammaCompare,
)

from .color_profile_convert_simple import (
    ColorProfileConvert,
)

from .color_converter_advanced import (
    ColorConverterAdvanced,
)

# Import dual input nodes
from .color_conversion import (
    ColorSpaceConverter,
    ColorTemperature,
    ColorSpaceAnalyzer,
)

from .color_grading import (
    ColorBalance,
    BrightnessContrast,
    Saturation,
    HueShift,
    GammaCorrection,
)

from .color_analysis import (
    DominantColors,
    DominantColorsAdvanced,
    DominantColorsAdvancedMultiple,
    ColorHistogram,
    ColorPalette,
    ColorSimilarity,
    ColorHarmony,
    LuminanceCalculator,
    CollageBackgroundColor,
)

from .vector_scope import (
    VectorScope,
)

from .color_space_inspector import (
    ColorSpaceInspector,
)

from .dominant_color_filter import (
    DominantColorFilter,
)

# Import utility functions
from .color_utils import (
    ColorInputHandler,
    create_dual_input_types,
    create_file_only_input_types,
    validate_dual_input,
    get_standard_dual_input_params,
)

__all__ = [
    # Color Profile Reader (File-only)
    "ColorProfileReader",
    "GammaCompare",
    
    # Color Profile Convert
    "ColorProfileConvert",
    
    # Advanced Color Converter
    "ColorConverterAdvanced",
    
    # Dual Input Conversion Nodes
    "ColorSpaceConverter",
    "ColorTemperature",
    "ColorSpaceAnalyzer",
    
    # Dual Input Grading Nodes
    "ColorBalance",
    "BrightnessContrast",
    "Saturation",
    "HueShift",
    "GammaCorrection",
    
    # Dual Input Analysis Nodes
    "DominantColors",
    "DominantColorsAdvanced",
    "DominantColorsAdvancedMultiple",
    "ColorHistogram",
    "ColorPalette",
    "ColorSimilarity",
    "ColorHarmony",
    "LuminanceCalculator",
    "CollageBackgroundColor",

    # Vector Scope Node
    "VectorScope",

    # Color Space Inspector
    "ColorSpaceInspector",

    # Dominant Color Filter
    "DominantColorFilter",
    
    # Utility Functions
    "ColorInputHandler",
    "create_dual_input_types",
    "create_file_only_input_types",
    "validate_dual_input",
    "get_standard_dual_input_params",
]
