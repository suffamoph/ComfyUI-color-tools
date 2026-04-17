# ComfyUI-color-tools 项目分析

## 项目结构

```
ComfyUI-color-tools/
├── __init__.py               # 入口，注册所有节点（分组 try/except，单组失败不影响其余）
├── install.py                # 自动安装依赖脚本
├── requirements.txt          / pyproject.toml / setup.py
├── generate_ocio_defs.py     # 从 ocio/config.ocio 动态生成 ocio_defs.py
├── ocio/config.ocio          # 内置 OCIO 配置文件
├── frame-matching-method.md  # 技术文档
└── nodes/
    ├── color_profile_reader.py          # ICC 色彩描述文件读取
    ├── color_profile_convert.py         # 色彩描述文件转换（完整版）
    ├── color_profile_convert_simple.py  # 色彩描述文件转换（简化版）
    ├── color_converter_advanced.py      # 高级颜色转换器
    ├── littlecms_converter.py           # 基于 LittleCMS 的转换
    ├── quick_color_fix.py               # 快速色彩空间修正
    ├── color_conversion.py              # 色彩空间互转 + 色温
    ├── rgb_hex_adjust.py                # HEX/RGB 互转 + HSV 微调
    ├── color_grading.py                 # 调色（色平衡/亮度对比/饱和度等）
    ├── color_analysis.py                # 主色提取、直方图、调色板等分析
    ├── natural_background_color.py      # 和谐配色生成
    ├── rgb_array_resolve.py             # 从颜色数组中取单个颜色
    ├── color_space_inspector.py         # 单色多空间转换预览
    ├── dominant_color_filter.py         # 主色过滤器
    ├── hue_distance.py                  # 色相距离计算
    ├── hue_matcher.py                   # 色相匹配
    ├── vector_scope.py                  # 矢量示波器
    ├── ocio_tools.py                    # OCIO 色彩空间转换（需 PyOpenColorIO）
    ├── ocio_advanced.py                 # 高级 OCIO 变换
    ├── ocio_defs.py                     # 自动生成的 OCIO 空间定义
    ├── color_utils.py                   # 公共工具函数（双输入模式等）
    └── advanced_tools.py                # 高级处理节点（量化/色盲模拟/色域映射）
```

---

## 节点分类总览

节点在 ComfyUI 中以 `Color Tools/` 前缀分类，共 6 个子分类。

### 1. Color Tools/Profile — 色彩描述文件

| 节点 | 说明 |
|------|------|
| Read Image Color Profile | 从图片文件读取 ICC 描述文件、PNG 色彩元数据，输出 JSON |
| Compare Image Gamma Values | 对比两张图的 gamma 值，给出不一致时的修正建议 |
| Convert Image Color Space | 用 ICC 描述文件将图片转换到 sRGB 或线性 sRGB |
| Advanced Color Converter | 高级色彩转换器，支持更多格式选项 |
| LittleCMS Color Profile Converter | 基于 LittleCMS 库的精确 ICC 描述文件转换 |
| Quick Color Space Fix | 快速修正常见色彩空间问题 |

### 2. Color Tools/Conversion — 色彩空间转换

| 节点 | 说明 |
|------|------|
| Color Space Converter | RGB / HSV / HSL / LAB / XYZ / CMYK 互转，支持 gamma 矫正 |
| Color Temperature | 调整图片的色温（冷暖）和色调偏移 |
| Color Space Analyzer | 分析图片色彩空间属性，输出统计与建议 |
| RGB/HEX Convert + Adjust | HEX ↔ RGB 互转，并通过 HSV 做色相/饱和度/明度微调 |

### 3. Color Tools/Grading — 调色

| 节点 | 说明 |
|------|------|
| Color Balance | 分别调整暗部/中间调/高光的 RGB 分量（类 Premiere 三路色轮） |
| Brightness/Contrast | 亮度 & 对比度调整 |
| Saturation | 饱和度调整，可选是否保持亮度 |
| Hue Shift | 全局色相旋转（-180° ~ 180°） |
| Gamma Correction | Gamma 校正 |

### 4. Color Tools/Analysis — 颜色分析

| 节点 | 说明 |
|------|------|
| Dominant Colors | K-means 提取图片主色（1-20 色），输出 JSON + 占比 |
| Dominant Colors Advanced | 升级版，支持**全图/边缘/中心**三种采样区域，输出色带预览 |
| Dominant Colors Advanced (Multiple) | 多图合并像素池后统一聚类，支持 batch 和 list 输入 |
| Color Histogram | 生成 RGB/HSV/LAB 色彩直方图 |
| Color Palette | 多种量化算法（K-means / Median Cut / Octree）生成调色板 |
| Color Similarity | 在图片中找近似于目标颜色的区域，输出蒙版 |
| Color Harmony | 分析图片的配色和谐性（互补/三角/类似色等） |
| Luminance Calculator | W3C WCAG 亮度公式计算，判断用深色还是浅色文字 |
| Collage Background Color | 从多图边缘提取主色，K-means 聚类后去饱和，输出拼版底色 |
| Color Harmonizer | 从图片主色推导和谐配色（互补/类似/三角/分裂互补等） |
| RGB Array Resolve | 按索引从主色数组取出单色，输出 R/G/B + HEX + 预览块 |
| Color Space Inspector | 输入任意色彩空间的颜色值，同时输出所有空间的转换结果 + 512×512 预览图 |
| Dominant Color Filter | 对主色结果做过滤筛选 |
| Hue Distance | 计算两个颜色之间的色相角度距离 |
| Hue Matcher | 根据色相距离做颜色匹配 |
| Vector Scope | 矢量示波器，用于专业色彩校正监看 |

### 5. Color Tools/Advanced — 高级工具

| 节点 | 说明 |
|------|------|
| Color Matcher | 精确/相似/色相替换模式的颜色替换 |
| Color Quantizer | 减少图片颜色数量（2–256 色），可加抖动 |
| Gamut Mapper | 不同色域之间的映射（感知/相对/饱和/绝对） |
| Color Blind Simulator | 模拟各类色盲视觉（用于无障碍可访问性测试） |

### 6. Color Tools/OCIO — 专业色彩管道（需 PyOpenColorIO）

| 节点 | 说明 |
|------|------|
| OCIO Color Space Converter | 基于 OpenColorIO 配置文件做专业色彩空间转换（支持 ACES 等） |
| OCIO Config Info | 查看 OCIO 配置中可用的色彩空间、Display 和 View Transform |
| Test Pattern Generator | 生成测试图案（色条/色阶/SMPTE/ColorChecker）用于验证 OCIO 变换 |
| Advanced OCIO Color Transform | 高级 OCIO 变换，支持更复杂的色彩管线配置 |

---

## 能解决的场景需求

### 场景一：拼版 / 封面底色选取

> 批量加载图片 → Dominant Colors Advanced (Multiple)（边缘采样）→ Collage Background Color（去饱和）→ 得到与多张主图协调的中性底色

### 场景二：UI / 文字颜色决策

> 获取背景色（HEX/RGB）→ Luminance Calculator（WCAG 亮度计算）→ 根据阈值自动选深色文字或浅色文字

### 场景三：颜色格式转换与精细调整

> RGB/HEX Convert + Adjust（色相偏移 / 饱和度缩放 / 明度偏移）→ RGB Array Resolve（拆出单色）→ 接入下游节点（如 ControlNet 颜色控制）

### 场景四：图片色彩空间管理（专业制作流程）

> Read Image Color Profile → Compare Gamma → Convert Image Color Space / LittleCMS Converter，确保 AI 生图前后色彩一致，避免 sRGB / Linear 混用导致的偏色

### 场景五：基于 ACES/OCIO 的专业电影级色彩管道

> OCIO Config Info（查看可用色彩空间）→ Test Pattern Generator（生成标准测试图）→ OCIO Color Space Converter（ACEScg ↔ sRGB 等）

### 场景六：颜色分析与设计辅助

> Color Space Inspector（输入任意颜色查看全空间数值）/ Color Harmony（分析图片配色关系）/ Color Harmonizer（为图片生成和谐配色方案）→ 辅助设计决策

### 场景七：无障碍可访问性测试

> Color Blind Simulator（模拟色盲视觉）→ 检查 AI 生成图像在不同色觉用户下的可读性

### 场景八：色彩调色与后期处理

> Color Balance + Saturation + Hue Shift + Gamma Correction → 对 AI 输出图做精细色彩后处理，替代外部图像编辑软件

---

## 版本说明

当前安装的是 `color-tools-advanced` 分支，基于 [APZmedia/ComfyUI-color-tools](https://github.com/APZmedia/ComfyUI-color-tools) 原版扩展。在原版基础上新增了面向**拼版/UI 配色/多图处理**场景的节点组，是对原版功能较为完整的超集。

新增节点主要包括：Dominant Colors Advanced、Dominant Colors Advanced (Multiple)、Luminance Calculator、Collage Background Color、RGB/HEX Convert + Adjust、RGB Array Resolve、Color Harmonizer、Color Space Inspector。
