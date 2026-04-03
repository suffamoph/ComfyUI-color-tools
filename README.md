# ComfyUI Color Profile Reader

A ComfyUI custom node for reading color profiles and color space information from image files. This node extracts ICC profiles, PNG color space chunks, and other color metadata to help you understand the color characteristics of your images.

## 🎨 Features

### **Color Profile Detection**
- **ICC Profile Extraction**: Reads embedded ICC color profiles from images
- **PNG Color Space Support**: Extracts sRGB, gamma, and chromaticity data from PNG files
- **Multi-format Support**: Works with JPEG, PNG, TIFF, WEBP, and other formats supported by Pillow
- **Profile Analysis**: Provides detailed information about color profiles and color spaces

### **Gamma Comparison**
- **Gamma Analysis**: Compares gamma values between two images
- **Standard Gamma Detection**: Identifies common gamma values (sRGB, Rec. 709, Rec. 2020, etc.)
- **Tolerance-based Comparison**: Configurable tolerance for gamma difference detection
- **Detailed Recommendations**: Provides workflow and technical recommendations for gamma mismatches

### **Output Information**
- **Profile JSON**: Complete color profile metadata in JSON format
- **ICC Base64**: Raw ICC profile data encoded in Base64
- **Primaries JSON**: Color primaries and white point information
- **Notes JSON**: Any warnings or additional information about the image

## 🚀 Installation

### Method 1: ComfyUI Manager (Recommended)

1. Open ComfyUI
2. Go to Manager → Install
3. Search for "ComfyUI Color Profile Reader"
4. Click Install

### Method 2: Manual Installation

1. Clone this repository to your ComfyUI `custom_nodes` directory:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/yourusername/ComfyUI-color-tools.git
   ```

2. Install dependencies:
   ```bash
   cd ComfyUI-color-tools
   pip install -r requirements.txt
   ```

3. Restart ComfyUI to load the new node

## 📖 Usage

### Basic Color Profile Reading

1. Add a "Color Profile Reader" node from the "Image/Color" category
2. Connect an image path (string) to the `image_path` input
3. The node will output:
   - `profile_json`: Complete profile information
   - `icc_base64`: Raw ICC profile data
   - `primaries_json`: Color primaries information
   - `notes_json`: Any additional notes or warnings

### OCIO Configuration Usage

The OCIO nodes work with both built-in configurations and custom files:

#### **Official OCIO Configurations**
1. Download OCIO configurations from the Academy Software Foundation ACES config repo:
   - Main repository: https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/tree/main
   - Download releases: https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/releases
   - Extract the `.ocio` file to your desired location (e.g., within your project folder or system config directory)

2. For the ACES config, recommended locations:
   - `C:\ProgramData\OpenColorIO\config.ocio` (Windows)
   - `/usr/local/share/OpenColorIO/config.ocio` (Linux/Mac)
   - Or any path you can easily reference for your project

3. In the OCIO Color Space Converter node, enter the full path to your `.ocio` file in the `ocio_config_path` input

#### **Example Usage**
```
OCIO Config Path: C:\ProgramData\OpenColorIO\config.ocio
Source Color Space: sRGB
Target Color Space: ACEScg
```

If no config path is specified, the nodes use OCIO's default built-in configuration.

#### **Getting OCIO Config Info**
Use the OCIO Config Info node to see what color spaces are available in your configuration and understand the structure.

### Workflow Integration

The node outputs JSON strings that can be:
- Displayed in Text nodes for inspection
- Used with Conditional nodes for branching logic
- Processed by other nodes that accept string inputs
- Saved to files for further analysis

## 🛠️ Node Details

### **📊 Color Profile Nodes**

#### **Color Profile Reader**
**What it does:** Extracts color profile and color space information from image files. Reads ICC profiles, PNG color space chunks, and other color metadata to understand the color characteristics of your images.

**Inputs:**
- `image_path` (STRING): Path to the image file (absolute or relative to ComfyUI)

**Outputs:**
- `profile_json` (STRING): Complete color profile metadata
- `icc_base64` (STRING): Raw ICC profile data in Base64 encoding
- `primaries_json` (STRING): Color primaries and white point data
- `notes_json` (STRING): Additional information and warnings

#### **Gamma Compare**
**What it does:** Compares gamma values between two images and provides detailed analysis. Detects gamma mismatches that could affect color accuracy and provides recommendations for color management.

**Inputs:**
- `image_path_1` (STRING): Path to the first image file
- `image_path_2` (STRING): Path to the second image file
- `tolerance` (FLOAT): Tolerance for gamma difference detection (0.001-0.1)

**Outputs:**
- `comparison_json` (STRING): Detailed comparison data between the two images
- `gamma_analysis` (STRING): In-depth gamma analysis and interpretation
- `recommendations` (STRING): Workflow and technical recommendations

#### **Color Profile → sRGB / Linear**
**What it does:** Converts images to sRGB or linear sRGB using ICC profiles, PNG color space data, or chromaticity matrices. Provides professional-grade color space conversion with fallback handling.

**Inputs:**
- `image` (IMAGE): Input image tensor
- `target_space` (COMBO): "sRGB" or "sRGB_linear"
- `icc_profile_base64` (STRING): ICC profile data from ColorProfileReader
- `png_srgb_intent` (INT): PNG sRGB rendering intent (-1 to 3)
- `png_gamma` (FLOAT): PNG gamma value
- `png_chromaticity_json` (STRING): PNG chromaticity data from ColorProfileReader

**Outputs:**
- `image` (IMAGE): Converted image in target color space

### **🔄 Color Conversion Nodes**

#### **Color Space Converter**
**What it does:** Converts images between different color spaces including RGB, HSV, HSL, LAB, XYZ, and CMYK. Supports gamma correction and preserves alpha channels.

**Inputs:**
- `image` (IMAGE): Input image
- `source_space` (COMBO): Source color space
- `target_space` (COMBO): Target color space
- `preserve_alpha` (BOOLEAN): Whether to preserve alpha channel
- `gamma_correction` (FLOAT): Gamma correction value

**Outputs:**
- `image` (IMAGE): Converted image
- `conversion_info` (STRING): Conversion details

#### **Color Temperature**
**What it does:** Adjusts color temperature and tint of images. Simulates warm/cool lighting conditions and provides fine control over color balance.

**Inputs:**
- `image` (IMAGE): Input image
- `temperature` (FLOAT): Temperature adjustment (-100 to 100)
- `tint` (FLOAT): Tint adjustment (-100 to 100)

**Outputs:**
- `image` (IMAGE): Temperature-adjusted image

#### **Color Space Analyzer**
**What it does:** Analyzes color space properties and provides detailed information about image characteristics. Generates recommendations for color management.

**Inputs:**
- `image` (IMAGE): Input image

**Outputs:**
- `color_space_info` (STRING): Color space information
- `color_stats` (STRING): Color statistics
- `recommendations` (STRING): Color management recommendations

### **🎨 Color Grading Nodes**

#### **Color Balance**
**What it does:** Adjusts color balance for shadows, midtones, and highlights separately. Provides professional color correction capabilities similar to video editing software.

**Inputs:**
- `image` (IMAGE): Input image
- `shadow_red/green/blue` (FLOAT): Shadow color adjustments
- `midtone_red/green/blue` (FLOAT): Midtone color adjustments
- `highlight_red/green/blue` (FLOAT): Highlight color adjustments

**Outputs:**
- `image` (IMAGE): Color-balanced image

#### **Brightness/Contrast**
**What it does:** Adjusts brightness and contrast of images. Provides precise control over exposure and contrast levels.

**Inputs:**
- `image` (IMAGE): Input image
- `brightness` (FLOAT): Brightness adjustment (-1.0 to 1.0)
- `contrast` (FLOAT): Contrast adjustment (0.0 to 3.0)

**Outputs:**
- `image` (IMAGE): Adjusted image

#### **Saturation**
**What it does:** Adjusts color saturation while optionally preserving luminance. Can boost or reduce color intensity.

**Inputs:**
- `image` (IMAGE): Input image
- `saturation` (FLOAT): Saturation multiplier (0.0 to 3.0)
- `preserve_luminance` (BOOLEAN): Whether to preserve luminance

**Outputs:**
- `image` (IMAGE): Saturation-adjusted image

#### **Hue Shift**
**What it does:** Shifts hue values of images. Useful for color correction and creative color effects.

**Inputs:**
- `image` (IMAGE): Input image
- `hue_shift` (FLOAT): Hue shift in degrees (-180 to 180)

**Outputs:**
- `image` (IMAGE): Hue-shifted image

#### **Gamma Correction**
**What it does:** Applies gamma correction to images. Essential for proper color management and display calibration.

**Inputs:**
- `image` (IMAGE): Input image
- `gamma` (FLOAT): Gamma value (0.1 to 5.0)

**Outputs:**
- `image` (IMAGE): Gamma-corrected image

### **📈 Color Analysis Nodes**

#### **Dominant Colors**
**What it does:** Extracts dominant colors from images using K-means clustering. Useful for color palette generation and color scheme analysis.

**Inputs:**
- `image` (IMAGE): Input image
- `num_colors` (INT): Number of colors to extract (1-20)
- `color_format` (COMBO): Output format (RGB, HSV, HEX)

**Outputs:**
- `dominant_colors` (STRING): Extracted colors as JSON
- `color_percentages` (STRING): Color percentages as JSON

#### **Color Histogram**
**What it does:** Generates color histograms for analysis. Provides detailed color distribution information across different color spaces.

**Inputs:**
- `image` (IMAGE): Input image
- `bins` (INT): Number of histogram bins (32-512)
- `histogram_type` (COMBO): Color space for histogram (RGB, HSV, LAB)

**Outputs:**
- `histogram_data` (STRING): Histogram data as JSON
- `statistics` (STRING): Color statistics as JSON

#### **Color Palette**
**What it does:** Generates comprehensive color palettes from images using various quantization methods. Creates color schemes for design workflows.

**Inputs:**
- `image` (IMAGE): Input image
- `palette_size` (INT): Number of colors in palette (3-32)
- `palette_type` (COMBO): Quantization method (K-means, Median Cut, Octree)

**Outputs:**
- `palette` (STRING): Color palette as JSON
- `palette_info` (STRING): Palette information as JSON

#### **Color Similarity**
**What it does:** Finds colors similar to a target color based on color distance. Useful for color matching and replacement workflows.

**Inputs:**
- `image` (IMAGE): Input image
- `target_color` (STRING): Target color (hex or RGB)
- `similarity_threshold` (FLOAT): Similarity threshold (0.0-1.0)
- `color_space` (COMBO): Color space for comparison (RGB, HSV, LAB)

**Outputs:**
- `mask` (IMAGE): Similarity mask
- `similarity_info` (STRING): Similarity analysis as JSON

#### **Color Harmony**
**What it does:** Analyzes color harmony and relationships in images. Evaluates complementary, triadic, analogous, and other color harmony types.

**Inputs:**
- `image` (IMAGE): Input image
- `harmony_type` (COMBO): Type of harmony to analyze

**Outputs:**
- `harmony_analysis` (STRING): Harmony analysis as JSON
- `color_relationships` (STRING): Color relationships as JSON

### **🔧 Advanced Tools Nodes**

#### **Color Matcher**
**What it does:** Matches and replaces colors in images. Supports exact, similar, and hue-only matching modes for color correction workflows.

**Inputs:**
- `image` (IMAGE): Input image
- `source_color` (STRING): Color to match
- `target_color` (STRING): Replacement color
- `tolerance` (FLOAT): Matching tolerance (0.0-1.0)
- `replace_mode` (COMBO): Replacement mode (Exact, Similar, Hue Only)

**Outputs:**
- `image` (IMAGE): Color-matched image
- `replacement_info` (STRING): Replacement statistics as JSON

#### **Color Quantizer**
**What it does:** Reduces the number of colors in images using various quantization methods. Useful for creating indexed color images and artistic effects.

**Inputs:**
- `image` (IMAGE): Input image
- `num_colors` (INT): Target number of colors (2-256)
- `quantization_method` (COMBO): Quantization method (K-means, Median Cut, Octree, Uniform)
- `dithering` (BOOLEAN): Whether to apply dithering

**Outputs:**
- `image` (IMAGE): Quantized image
- `quantization_info` (STRING): Quantization statistics as JSON

#### **Gamut Mapper**
**What it does:** Maps colors between different color gamuts. Essential for color management when working with different display technologies.

**Inputs:**
- `image` (IMAGE): Input image
- `source_gamut` (COMBO): Source color gamut
- `target_gamut` (COMBO): Target color gamut
- `mapping_method` (COMBO): Gamut mapping method (Perceptual, Relative, Saturation, Absolute)

**Outputs:**
- `image` (IMAGE): Gamut-mapped image
- `mapping_info` (STRING): Mapping information as JSON

#### **Color Blind Simulator**
**What it does:** Simulates different types of color blindness. Useful for accessibility testing and understanding how color-blind users perceive images.

**Inputs:**
- `image` (IMAGE): Input image
- `color_blindness_type` (COMBO): Type of color blindness to simulate
- `severity` (FLOAT): Simulation severity (0.0-1.0)

**Outputs:**
- `image` (IMAGE): Simulated image
- `simulation_info` (STRING): Simulation details as JSON

### **☹️ OCIO Nodes**

#### **OCIO Color Space Converter**
**What it does:** Professional color space conversions using OpenColorIO configurations. Supports industry-standard color pipelines and professional color management.

**Inputs:**
- `image` (IMAGE): Input image tensor
- `ocio_config_path` (STRING): Path to .ocio configuration file (optional)
- `source_colorspace` (STRING): Source color space name
- `target_colorspace` (STRING): Target color space name

**Outputs:**
- `image` (IMAGE): Converted image in target color space
- `conversion_info` (STRING): Conversion details and metadata

#### **OCIO Config Info**
**What it does:** Displays information about OCIO configurations, including available color spaces, displays, and viewing transforms.

**Inputs:**
- `ocio_config_path` (STRING): Path to .ocio configuration file (optional)

**Outputs:**
- `config_info` (STRING): Detailed configuration information

#### **Test Pattern Generator**
**What it does:** Generates test patterns for color space validation and calibration. Creates color bars, tone ramps, SMPTE color bars, and ColorChecker-like patterns essential for testing OCIO transforms.

**Inputs:**
- `pattern_type` (COMBO): Type of test pattern (Color Bars, Tone Ramp, Gray Ramp, SMPTE Color Bars, ColorChecker)
- `width` (INT): Pattern width in pixels
- `height` (INT): Pattern height in pixels

**Outputs:**
- `test_pattern` (IMAGE): Generated test pattern image
- `pattern_info` (STRING): Description of the generated pattern

Recommended workflow: Generate test patterns, convert them through OCIO color spaces, and visually compare results to validate color accuracy.

### **Profile JSON Structure**

```json
{
  "container": "PNG",
  "pillow_mode": "RGB",
  "icc_present": true,
  "icc_profile_name": "sRGB IEC61966-2.1",
  "icc_summary": {
    "profile_class": "mntr",
    "pcs": "XYZ ",
    "acsp_sanity": true
  },
  "srgb_chunk_intent": 0,
  "gamma": 0.45455,
  "chromaticity": {
    "wx": 0.3127,
    "wy": 0.3290,
    "rx": 0.64,
    "ry": 0.33,
    "gx": 0.30,
    "gy": 0.60,
    "bx": 0.15,
    "by": 0.06
  }
}
```

## 📊 Use Cases

### **Color Management Workflows**
- Verify color profiles in source images
- Ensure proper color space handling in processing pipelines
- Detect color profile mismatches that could affect output quality
- Compare gamma values between images for consistency

### **Image Analysis**
- Analyze color characteristics of reference images
- Extract color space information for documentation
- Validate color profile compliance
- Detect gamma mismatches that could cause color shifts

### **Quality Control**
- Check for missing or incorrect color profiles
- Verify color space consistency across image sets
- Monitor color profile usage in production workflows
- Ensure gamma consistency in multi-image projects

### **Gamma Comparison Workflows**
- Compare gamma values between source and output images
- Detect gamma mismatches in color pipelines
- Analyze gamma characteristics for color space identification
- Generate recommendations for gamma correction

## 🔧 Dependencies

- `Pillow>=8.0.0`: Image processing and ICC profile support
- `opencolorio>=2.0.0`: Professional color management (OCIO nodes)

## 📁 Project Structure

```
ComfyUI-color-tools/
├── README.md
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── __init__.py
├── nodes/
│   ├── __init__.py
│   ├── advanced_tools.py
│   ├── color_analysis.py
│   ├── color_conversion.py
│   ├── color_converter_advanced.py
│   ├── color_grading.py
│   ├── color_profile_convert.py
│   ├── color_profile_convert_simple.py
│   ├── color_profile_reader.py
│   └── ocio_tools.py  (OpenColorIO integration)
└── examples/
    └── color_profile_workflow.json
```

---

## ✨ Added in `color-tools-advanced` branch

The following nodes were added on top of the original package.

---

### **🎯 Dominant Colors Advanced**
**Category:** Color Tools/Analysis

An upgraded version of Dominant Colors with sampling zone control.

**Inputs:**
- `input_mode` (COMBO): `tensor` (IMAGE socket) or `file` (image_path string)
- `num_colors` (INT): Number of dominant colors to extract (1–20)
- `color_format` (COMBO): Output format — `RGB`, `HSV`, or `HEX`
- `sample_mode` (COMBO): `full` (whole image), `edge` (outer border strip), `center` (inner rectangle)
- `edge_ratio` (FLOAT): Border thickness as a fraction of image size (0.01–0.5); only applies to `edge` / `center` modes
- `image` (IMAGE, optional): Input tensor
- `image_path` (STRING, optional): File path when using `file` mode

**Outputs:**
- `dominant_colors` (STRING): JSON list of colors, sorted by prevalence
- `color_percentages` (STRING): JSON list of pixel proportions per color
- `sample_area_preview` (IMAGE): Original image with the sampled region highlighted in green (80% opacity)
- `dom_clr_preview` (IMAGE): 512×64 horizontal color strip — each color band is proportional to its percentage

---

### **🎯 Dominant Colors Advanced (Multiple)**
**Category:** Color Tools/Analysis

Batch / list-aware version of Dominant Colors Advanced. Accepts both IMAGE batch tensors and IMAGE lists (different sizes supported). Pixels from all images are merged into one pool before K-means, producing a single shared color result.

**Inputs:**
- `images` (IMAGE): Batch tensor (e.g. Load Image Batch) or image list (e.g. Load Images From Dir — preserves individual aspect ratios)
- `num_colors`, `color_format`, `sample_mode`, `edge_ratio`: Same as above

**Outputs:**
- `dominant_colors` (STRING): Merged dominant colors as JSON
- `color_percentages` (STRING): Proportions across the merged pixel pool
- `sample_area_preview` (IMAGE): Per-image previews stacked into a batch (all resized to the first image's dimensions)
- `dom_clr_preview` (IMAGE): 512×64 color strip for the merged result

> Tip: Use an image list loader (not batch) to preserve each image's original aspect ratio for accurate edge/center sampling.

---

### **💡 Luminance Calculator**
**Category:** Color Tools/Analysis

Calculates perceptual luminance from a color using the W3C WCAG relative luminance formula (sRGB IEC 61966-2-1 gamma correction). Useful for deciding whether to display light or dark UI text on a given background color.

**Inputs:**
- `input_mode` (COMBO): `RGB` or `HEX`
- `red`, `green`, `blue` (FLOAT): Normalized 0–1 values (used in RGB mode)
- `hex_color` (STRING): `#RRGGBB` hex string (used in HEX mode)

**Outputs:**
- `luminance` (FLOAT): Relative luminance value in [0, 1]; values above ~0.179 are considered "light"
- `result_json` (STRING): Full calculation details as JSON

---

### **🖼️ Collage Background Color**
**Category:** Color Tools/Analysis

Samples edge pixels from all images in a batch, runs K-means to find the most representative background color, then desaturates it slightly for a neutral collage background.

**Inputs:**
- `image` (IMAGE): Batch of images
- `num_colors` (INT): K-means clusters (1–10)
- `edge_ratio` (FLOAT): Border thickness as fraction of image size
- `desaturation` (FLOAT): How much to reduce saturation (0 = no change, 1 = fully grey)

**Outputs:**
- `hex_color` (STRING): Output color as `#RRGGBB`
- `red`, `green`, `blue` (FLOAT): Normalized RGB components

---

### **🎨 RGB/HEX Convert + Adjust**
**Category:** Color Tools/Conversion

Converts between HEX and RGB and applies HSV-based adjustments (hue shift, saturation scale, value scale/offset).

**Inputs:**
- `input_mode` (COMBO): `HEX` or `RGB`
- `hex_color` (STRING): Input color as `#RRGGBB`
- `red`, `green`, `blue` (FLOAT): Input color as normalized RGB (used when mode is RGB)
- `hue_shift` (FLOAT): Hue rotation in degrees (−180 to 180)
- `saturation_scale` (FLOAT): Multiply saturation (0–3)
- `value_scale` (FLOAT): Multiply brightness (0–3)
- `value_offset` (FLOAT): Add/subtract brightness (−1 to 1)

**Outputs:**
- `rgb_array` (STRING): JSON `[[r, g, b]]` — compatible with RGB Array Resolve
- `hex_color` (STRING): Adjusted color as `#RRGGBB`
- `hue`, `saturation`, `value` (FLOAT): HSV components of the output color
- `info_json` (STRING): Full input/output details as JSON
- `preview` (IMAGE): 512×512 solid color swatch

---

### **🔢 RGB Array Resolve**
**Category:** Color Tools/Analysis

Picks one color from an RGB array (e.g. output of Dominant Colors or RGB/HEX Convert + Adjust) by index and outputs it as individual R/G/B values and a HEX string.

**Inputs:**
- `rgb_array` (STRING): JSON array of RGB triplets — accepts normalized (0–1) or byte (0–255) values, auto-detected
- `color_index` (INT): Which color to pick (0-based)
- `clamp_index` (BOOLEAN): If true, clamps out-of-range indices instead of erroring
- `rgb_output_mode` (COMBO): `byte` (0–255) or `normalized` (0–1)
- `preview_width`, `preview_height` (INT): Size of the output swatch

**Outputs:**
- `red`, `green`, `blue` (FLOAT): Color components in selected mode
- `hex_color` (STRING): Color as `#RRGGBB`
- `preview` (IMAGE): Solid color swatch

---

### **🌈 Color Harmonizer** *(NaturalBackgroundColor)*
**Category:** Color Tools/Analysis

Analyzes the dominant hue of an image and generates a harmonious background color using standard color theory relationships (complementary, analogous, triadic, etc.). Saturation and value are adjustable.

**Inputs:**
- `image` (IMAGE): Input image
- `harmony_type` (COMBO): Harmony relationship — `complementary`, `analogous`, `triadic`, `split-complementary`, `tetradic`, `monochromatic`
- `saturation` (FLOAT): Saturation of the output color (0–1)
- `value` (FLOAT): Brightness of the output color (0–1)

**Outputs:**
- `hex_color` (STRING): Harmonious background color as `#RRGGBB`
- `red`, `green`, `blue` (FLOAT): Normalized RGB
- `harmony_info` (STRING): JSON with source hue, harmony type, and output color details

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

## 🆘 Support

For issues, feature requests, or questions:
- Open an issue on GitHub
- Check the documentation
- Review example workflows

## 🔄 Version History

- **v1.0.0**: Initial release with color profile reading functionality

## 🙏 Acknowledgments

- ComfyUI community for the excellent framework
- Pillow team for image processing capabilities
- ICC profile specification contributors

---

**Author**: Pablo Apiolazza  
**Repository**: [ComfyUI-color-tools](https://github.com/APZmedia/ComfyUI-color-tools)  
**Category**: Image/Color
