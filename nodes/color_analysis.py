"""
Color Analysis Nodes

This module contains nodes for analyzing colors in images, extracting
dominant colors, generating palettes, and performing color similarity analysis.
"""

import torch
import numpy as np
import cv2
from sklearn.cluster import KMeans
from collections import Counter
import json
from typing import Tuple, Dict, Any, List, Optional

class DominantColors:
    """
    Extract dominant colors from an image using K-means clustering.
    Works with both file paths and image tensors.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_mode": (["file", "tensor"], {"default": "tensor"}),
                "num_colors": ("INT", {"default": 5, "min": 1, "max": 20, "step": 1}),
                "color_format": (["RGB", "HSV", "HEX"], {"default": "RGB"}),
            },
            "optional": {
                "image": ("IMAGE",),
                "image_path": ("STRING", {"default": "", "multiline": False}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("dominant_colors", "color_percentages")
    FUNCTION = "extract_dominant_colors"
    CATEGORY = "Color Tools/Analysis"
    
    def extract_dominant_colors(self, input_mode: str, num_colors: int, color_format: str, 
                               image: torch.Tensor = None, image_path: str = "") -> Tuple[str, str]:
        """
        Extract dominant colors from the image.
        Supports both file paths and image tensors.
        """
        if input_mode == "file":
            return self._extract_from_file(image_path, num_colors, color_format)
        else:
            return self._extract_from_tensor(image, num_colors, color_format)
    
    def _extract_from_file(self, image_path: str, num_colors: int, color_format: str) -> Tuple[str, str]:
        """Extract colors from file"""
        if not image_path.strip():
            raise ValueError("Image path required when input_mode is 'file'")
        
        # Load image from file
        img_array = self._load_image_from_path(image_path)
        return self._extract_colors(img_array, num_colors, color_format)
    
    def _extract_from_tensor(self, image: torch.Tensor, num_colors: int, color_format: str) -> Tuple[str, str]:
        """Extract colors from tensor"""
        if image is None:
            raise ValueError("Image tensor required when input_mode is 'tensor'")
        
        # Convert tensor to numpy
        img_array = self._tensor_to_array(image)
        return self._extract_colors(img_array, num_colors, color_format)
    
    def _load_image_from_path(self, image_path: str) -> np.ndarray:
        """Load image from file path"""
        from PIL import Image
        pil_image = Image.open(image_path)
        img_array = np.array(pil_image) / 255.0
        return img_array
    
    def _tensor_to_array(self, tensor: torch.Tensor) -> np.ndarray:
        """Convert ComfyUI tensor to numpy array"""
        if len(tensor.shape) == 4:
            return tensor[0].cpu().numpy()
        else:
            return tensor.cpu().numpy()
    
    def _extract_colors(self, img_array: np.ndarray, num_colors: int, color_format: str) -> Tuple[str, str]:
        """Core color extraction logic"""
        # Ensure image is in [0, 1] range
        if img_array.max() > 1.0:
            img_array = img_array / 255.0
        
        # Extract dominant colors
        colors, percentages = self._extract_colors_internal(img_array, num_colors, color_format)
        
        return colors, percentages
    
    def _extract_colors_internal(self, img: np.ndarray, num_colors: int, color_format: str) -> Tuple[str, str]:
        """Extract dominant colors using K-means clustering."""
        # Reshape image to list of pixels
        pixels = img.reshape(-1, 3)
        
        # Apply K-means clustering
        kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get cluster centers and labels
        colors = np.clip(kmeans.cluster_centers_, 0.0, 1.0)
        labels = kmeans.labels_
        
        # Calculate percentages per cluster index, then sort by percentage (high -> low).
        total_pixels = len(labels)
        counts = np.bincount(labels, minlength=num_colors)
        percentages = counts.astype(np.float64) / float(total_pixels)
        sorted_indices = np.argsort(-percentages)

        colors = colors[sorted_indices]
        percentages = percentages[sorted_indices]
        
        # Convert colors to desired format
        if color_format == "RGB":
            colors_str = json.dumps(colors.tolist())
        elif color_format == "HSV":
            hsv_colors = []
            for color in colors:
                hsv = cv2.cvtColor(np.uint8([[color * 255]]), cv2.COLOR_RGB2HSV)[0][0]
                hsv_colors.append(hsv.tolist())
            colors_str = json.dumps(hsv_colors)
        elif color_format == "HEX":
            hex_colors = []
            for color in colors:
                r, g, b = (color * 255).astype(int)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                hex_colors.append(hex_color)
            colors_str = json.dumps(hex_colors)
        
        percentages_str = json.dumps(percentages.tolist())
        
        return colors_str, percentages_str


class DominantColorsAdvanced:
    """
    Extended version of DominantColors with sample_mode and edge_ratio.
    - full:   all pixels (edge_ratio ignored)
    - edge:   outer band pixels only
    - center: inner rectangle pixels only
    """

    DESCRIPTION = (
        "DominantColors 的增强版，新增 sample_mode 参数控制像素采样范围。\n\n"
        "【input_mode 说明】\n"
        "• tensor：直接接收 ComfyUI IMAGE 输入\n"
        "• file：通过 image_path 字符串读取本地文件\n\n"
        "【sample_mode 说明】\n"
        "• full：对整张图所有像素做 K-means，edge_ratio 不起作用\n"
        "• edge：只采样四条边的像素带（外圈），采样面积 = 1-(1-2r)²\n"
        "• center：只采样几何中心矩形（内框），采样面积 = (1-2r)²\n\n"
        "【edge_ratio 说明】\n"
        "• 单边占图像边长的比例，范围 0.01~0.5\n"
        "• edge/center 模式下有效，full 模式下忽略\n\n"
        "【输出】\n"
        "• dominant_colors：主色列表（JSON），按占比从高到低排序\n"
        "• color_percentages：每个主色的像素占比（JSON 浮点数列表）"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_mode": (["file", "tensor"], {"default": "tensor"}),
                "num_colors": ("INT", {"default": 5, "min": 1, "max": 20, "step": 1}),
                "color_format": (["RGB", "HSV", "HEX"], {"default": "RGB"}),
                "sample_mode": (["full", "edge", "center"], {"default": "full"}),
                "edge_ratio": ("FLOAT", {"default": 0.05, "min": 0.01, "max": 0.5, "step": 0.01}),
            },
            "optional": {
                "image": ("IMAGE",),
                "image_path": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("dominant_colors", "color_percentages", "sample_area_preview", "dom_clr_preview")
    FUNCTION = "extract"
    CATEGORY = "Color Tools/Analysis"

    def extract(self, input_mode: str, num_colors: int, color_format: str,
                sample_mode: str, edge_ratio: float,
                image: torch.Tensor = None, image_path: str = "") -> Tuple[str, str, torch.Tensor, torch.Tensor]:
        if input_mode == "file":
            if not image_path.strip():
                raise ValueError("image_path is required when input_mode is 'file'")
            from PIL import Image as PILImage
            img = np.array(PILImage.open(image_path)) / 255.0
        else:
            if image is None:
                raise ValueError("image is required when input_mode is 'tensor'")
            img = image[0].cpu().numpy()
            if img.max() > 1.0:
                img = img / 255.0

        if sample_mode == "edge":
            pixels = self._edge_pixels(img, edge_ratio)
        elif sample_mode == "center":
            pixels = self._center_pixels(img, edge_ratio)
        else:
            pixels = img.reshape(-1, 3)

        colors_str, percentages_str = self._kmeans_colors(pixels, num_colors, color_format)
        area_preview = self._make_preview(img, sample_mode, edge_ratio)
        clr_preview = self._make_color_preview(colors_str, percentages_str)
        return colors_str, percentages_str, area_preview, clr_preview

    def _edge_pixels(self, img: np.ndarray, edge_ratio: float) -> np.ndarray:
        H, W, _ = img.shape
        bh = max(1, int(H * edge_ratio))
        bw = max(1, int(W * edge_ratio))
        top    = img[:bh, :, :].reshape(-1, 3)
        bottom = img[H - bh:, :, :].reshape(-1, 3)
        left   = img[bh:H - bh, :bw, :].reshape(-1, 3)
        right  = img[bh:H - bh, W - bw:, :].reshape(-1, 3)
        return np.concatenate([top, bottom, left, right], axis=0)

    def _center_pixels(self, img: np.ndarray, edge_ratio: float) -> np.ndarray:
        H, W, _ = img.shape
        bh = max(1, int(H * edge_ratio))
        bw = max(1, int(W * edge_ratio))
        y0, y1 = bh, max(bh + 1, H - bh)
        x0, x1 = bw, max(bw + 1, W - bw)
        return img[y0:y1, x0:x1, :].reshape(-1, 3)

    def _make_preview(self, img: np.ndarray, sample_mode: str, edge_ratio: float) -> torch.Tensor:
        GREEN = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        OPACITY = 0.8
        img = np.ascontiguousarray(img)
        H, W, _ = img.shape
        green_overlay = OPACITY * GREEN + (1 - OPACITY) * img
        if sample_mode == "full":
            preview = img.copy()
        elif sample_mode == "edge":
            preview = green_overlay.copy()
            bh = max(1, int(H * edge_ratio))
            bw = max(1, int(W * edge_ratio))
            preview[:bh, :] = img[:bh, :]
            preview[H - bh:, :] = img[H - bh:, :]
            preview[bh:H - bh, :bw] = img[bh:H - bh, :bw]
            preview[bh:H - bh, W - bw:] = img[bh:H - bh, W - bw:]
        elif sample_mode == "center":
            preview = green_overlay.copy()
            bh = max(1, int(H * edge_ratio))
            bw = max(1, int(W * edge_ratio))
            y0, y1 = bh, max(bh + 1, H - bh)
            x0, x1 = bw, max(bw + 1, W - bw)
            preview[y0:y1, x0:x1] = img[y0:y1, x0:x1]
        preview = np.clip(preview, 0.0, 1.0)
        return torch.from_numpy(preview).unsqueeze(0).float()

    def _make_color_preview(self, colors_str: str, percentages_str: str) -> torch.Tensor:
        colors = json.loads(colors_str)
        percentages = json.loads(percentages_str)
        W, H = 512, 64
        canvas = np.zeros((H, W, 3), dtype=np.float32)
        x = 0
        for color, pct in zip(colors, percentages):
            w = int(round(pct * W))
            if w == 0:
                continue
            if isinstance(color, str):
                h = color.lstrip("#")
                rgb = [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
            elif max(color) <= 1.0:
                rgb = list(color[:3])
            else:
                rgb = [c / 255.0 for c in color[:3]]
            canvas[:, x:x + w, :] = np.array(rgb, dtype=np.float32)
            x += w
        if x < W and colors:
            canvas[:, x:, :] = canvas[:, x - 1:x, :]
        return torch.from_numpy(canvas).unsqueeze(0).float()

    def _kmeans_colors(self, pixels: np.ndarray, num_colors: int, color_format: str) -> Tuple[str, str]:
        n_clusters = min(num_colors, len(pixels))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(pixels)

        colors = np.clip(kmeans.cluster_centers_, 0.0, 1.0)
        labels = kmeans.labels_
        counts = np.bincount(labels, minlength=n_clusters)
        percentages = counts.astype(np.float64) / float(len(labels))
        order = np.argsort(-percentages)
        colors = colors[order]
        percentages = percentages[order]

        if color_format == "RGB":
            colors_str = json.dumps(colors.tolist())
        elif color_format == "HSV":
            hsv_list = []
            for c in colors:
                hsv = cv2.cvtColor(np.uint8([[c * 255]]), cv2.COLOR_RGB2HSV)[0][0]
                hsv_list.append(hsv.tolist())
            colors_str = json.dumps(hsv_list)
        elif color_format == "HEX":
            hex_list = []
            for c in colors:
                r, g, b = (c * 255).astype(int)
                hex_list.append(f"#{r:02x}{g:02x}{b:02x}")
            colors_str = json.dumps(hex_list)

        return colors_str, json.dumps(percentages.tolist())


class DominantColorsAdvancedMultiple:
    """
    Batch/List-aware version of DominantColorsAdvanced.
    Accepts IMAGE batch tensor or IMAGE list (different sizes supported).
    Iterates over all images, samples pixels per sample_mode,
    merges into one pool, runs K-means once.
    """

    INPUT_IS_LIST = True

    DESCRIPTION = (
        "DominantColorsAdvanced 的多图版本，同时支持 IMAGE batch 和 IMAGE list 输入。\n\n"
        "【输入说明】\n"
        "• IMAGE batch（如 Load Image Batch）：所有图被上游 resize 到同一尺寸后输入\n"
        "• IMAGE list（如 Load Images From Dir List）：每张图保持原始尺寸，比例不受影响\n"
        "  推荐使用 list 模式以保留各图原始比例，确保 edge/center 采样区域准确\n\n"
        "【sample_mode 说明】\n"
        "• full：每张图取全部像素，edge_ratio 不起作用\n"
        "• edge：每张图取四条边的像素带，采样面积 = 1-(1-2r)²\n"
        "• center：每张图取几何中心矩形，采样面积 = (1-2r)²\n\n"
        "【edge_ratio 说明】\n"
        "• 单边占图像边长的比例，edge/center 模式下有效，范围 0.01~0.5\n\n"
        "【输出】\n"
        "• dominant_colors：主色列表（JSON），按占比从高到低排序\n"
        "• color_percentages：各主色在合并像素池中的占比（JSON 浮点数列表）\n"
        "• sample_preview：每张图的采样区域预览，统一 resize 到第一张图的尺寸"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "num_colors": ("INT", {"default": 5, "min": 1, "max": 20, "step": 1}),
                "color_format": (["RGB", "HSV", "HEX"], {"default": "RGB"}),
                "sample_mode": (["full", "edge", "center"], {"default": "full"}),
                "edge_ratio": ("FLOAT", {"default": 0.05, "min": 0.01, "max": 0.5, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("dominant_colors", "color_percentages", "sample_area_preview", "dom_clr_preview")
    OUTPUT_IS_LIST = (False, False, False, False)
    FUNCTION = "extract"
    CATEGORY = "Color Tools/Analysis"

    def extract(self, images: list, num_colors: list, color_format: list,
                sample_mode: list, edge_ratio: list) -> Tuple[str, str, torch.Tensor, torch.Tensor]:
        # INPUT_IS_LIST=True 时所有参数都是 list，取第一个值
        image = images
        num_colors = num_colors[0]
        color_format = color_format[0]
        sample_mode = sample_mode[0]
        edge_ratio = edge_ratio[0]

        # 展开所有图：batch tensor (B,H,W,3) 或 list of (1,H,W,3)
        imgs = []
        for item in image:
            for i in range(item.shape[0]):
                img = np.ascontiguousarray(item[i].cpu().numpy())
                if img.max() > 1.0:
                    img = img / 255.0
                imgs.append(img)

        all_pixels = []
        previews = []
        target_h, target_w = imgs[0].shape[0], imgs[0].shape[1]

        for img in imgs:
            if sample_mode == "edge":
                all_pixels.append(self._edge_pixels(img, edge_ratio))
            elif sample_mode == "center":
                all_pixels.append(self._center_pixels(img, edge_ratio))
            else:
                all_pixels.append(img.reshape(-1, 3))

            preview = self._make_preview(img, sample_mode, edge_ratio)
            if img.shape[0] != target_h or img.shape[1] != target_w:
                preview_np = cv2.resize(preview[0].numpy(), (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                preview = torch.from_numpy(preview_np).unsqueeze(0).float()
            previews.append(preview)

        pixels = np.concatenate(all_pixels, axis=0)
        colors_str, percentages_str = self._kmeans_colors(pixels, num_colors, color_format)
        preview_batch = torch.cat(previews, dim=0)
        clr_preview = self._make_color_preview(colors_str, percentages_str)
        return colors_str, percentages_str, preview_batch, clr_preview

    def _edge_pixels(self, img: np.ndarray, edge_ratio: float) -> np.ndarray:
        H, W, _ = img.shape
        bh = max(1, int(H * edge_ratio))
        bw = max(1, int(W * edge_ratio))
        top    = img[:bh, :, :].reshape(-1, 3)
        bottom = img[H - bh:, :, :].reshape(-1, 3)
        left   = img[bh:H - bh, :bw, :].reshape(-1, 3)
        right  = img[bh:H - bh, W - bw:, :].reshape(-1, 3)
        return np.concatenate([top, bottom, left, right], axis=0)

    def _center_pixels(self, img: np.ndarray, edge_ratio: float) -> np.ndarray:
        H, W, _ = img.shape
        bh = max(1, int(H * edge_ratio))
        bw = max(1, int(W * edge_ratio))
        y0, y1 = bh, max(bh + 1, H - bh)
        x0, x1 = bw, max(bw + 1, W - bw)
        return img[y0:y1, x0:x1, :].reshape(-1, 3)

    def _make_preview(self, img: np.ndarray, sample_mode: str, edge_ratio: float) -> torch.Tensor:
        GREEN = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        OPACITY = 0.8
        img = np.ascontiguousarray(img)
        H, W, _ = img.shape
        green_overlay = OPACITY * GREEN + (1 - OPACITY) * img
        if sample_mode == "full":
            preview = img.copy()
        elif sample_mode == "edge":
            preview = green_overlay.copy()
            bh = max(1, int(H * edge_ratio))
            bw = max(1, int(W * edge_ratio))
            preview[:bh, :] = img[:bh, :]
            preview[H - bh:, :] = img[H - bh:, :]
            preview[bh:H - bh, :bw] = img[bh:H - bh, :bw]
            preview[bh:H - bh, W - bw:] = img[bh:H - bh, W - bw:]
        elif sample_mode == "center":
            preview = green_overlay.copy()
            bh = max(1, int(H * edge_ratio))
            bw = max(1, int(W * edge_ratio))
            y0, y1 = bh, max(bh + 1, H - bh)
            x0, x1 = bw, max(bw + 1, W - bw)
            preview[y0:y1, x0:x1] = img[y0:y1, x0:x1]
        preview = np.clip(preview, 0.0, 1.0)
        return torch.from_numpy(preview).unsqueeze(0).float()

    def _make_color_preview(self, colors_str: str, percentages_str: str) -> torch.Tensor:
        colors = json.loads(colors_str)
        percentages = json.loads(percentages_str)
        W, H = 512, 64
        canvas = np.zeros((H, W, 3), dtype=np.float32)
        x = 0
        for color, pct in zip(colors, percentages):
            w = int(round(pct * W))
            if w == 0:
                continue
            if isinstance(color, str):
                h = color.lstrip("#")
                rgb = [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
            elif max(color) <= 1.0:
                rgb = list(color[:3])
            else:
                rgb = [c / 255.0 for c in color[:3]]
            canvas[:, x:x + w, :] = np.array(rgb, dtype=np.float32)
            x += w
        if x < W and colors:
            canvas[:, x:, :] = canvas[:, x - 1:x, :]
        return torch.from_numpy(canvas).unsqueeze(0).float()

    def _kmeans_colors(self, pixels: np.ndarray, num_colors: int, color_format: str) -> Tuple[str, str]:
        n_clusters = min(num_colors, len(pixels))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(pixels)

        colors = np.clip(kmeans.cluster_centers_, 0.0, 1.0)
        labels = kmeans.labels_
        counts = np.bincount(labels, minlength=n_clusters)
        percentages = counts.astype(np.float64) / float(len(labels))
        order = np.argsort(-percentages)
        colors = colors[order]
        percentages = percentages[order]

        if color_format == "RGB":
            colors_str = json.dumps(colors.tolist())
        elif color_format == "HSV":
            hsv_list = []
            for c in colors:
                hsv = cv2.cvtColor(np.uint8([[c * 255]]), cv2.COLOR_RGB2HSV)[0][0]
                hsv_list.append(hsv.tolist())
            colors_str = json.dumps(hsv_list)
        elif color_format == "HEX":
            hex_list = []
            for c in colors:
                r, g, b = (c * 255).astype(int)
                hex_list.append(f"#{r:02x}{g:02x}{b:02x}")
            colors_str = json.dumps(hex_list)

        return colors_str, json.dumps(percentages.tolist())


class ColorHistogram:
    """
    Generate color histograms for analysis.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "bins": ("INT", {"default": 256, "min": 32, "max": 512, "step": 32}),
                "histogram_type": (["RGB", "HSV", "LAB"], {"default": "RGB"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("histogram_data", "statistics")
    FUNCTION = "generate_histogram"
    CATEGORY = "Color Tools/Analysis"
    
    def generate_histogram(self, image: torch.Tensor, bins: int, histogram_type: str) -> Tuple[str, str]:
        """
        Generate color histogram data.
        """
        # Convert tensor to numpy
        if len(image.shape) == 4:
            img_np = image[0].numpy()
        else:
            img_np = image.numpy()
        
        # Ensure image is in [0, 1] range
        if img_np.max() > 1.0:
            img_np = img_np / 255.0
        
        # Generate histogram
        histogram_data, statistics = self._generate_histogram(img_np, bins, histogram_type)
        
        return histogram_data, statistics
    
    def _generate_histogram(self, img: np.ndarray, bins: int, hist_type: str) -> Tuple[str, str]:
        """Generate color histogram."""
        # Convert to appropriate color space
        if hist_type == "RGB":
            channels = [img[:, :, 0], img[:, :, 1], img[:, :, 2]]
            channel_names = ["Red", "Green", "Blue"]
        elif hist_type == "HSV":
            hsv = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
            channels = [hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]]
            channel_names = ["Hue", "Saturation", "Value"]
        elif hist_type == "LAB":
            lab = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)
            channels = [lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]]
            channel_names = ["L", "A", "B"]
        
        # Calculate histograms
        histograms = []
        statistics = {}
        
        for i, (channel, name) in enumerate(zip(channels, channel_names)):
            if hist_type == "RGB":
                hist, _ = np.histogram(channel, bins=bins, range=(0, 1))
            else:
                hist, _ = np.histogram(channel, bins=bins, range=(0, 255))
            
            histograms.append(hist.tolist())
            
            # Calculate statistics
            statistics[name] = {
                "mean": float(np.mean(channel)),
                "std": float(np.std(channel)),
                "min": float(np.min(channel)),
                "max": float(np.max(channel)),
                "median": float(np.median(channel))
            }
        
        histogram_data = json.dumps({
            "channels": channel_names,
            "histograms": histograms,
            "bins": bins
        })
        
        statistics_str = json.dumps(statistics)
        
        return histogram_data, statistics_str


class ColorPalette:
    """
    Generate comprehensive color palettes from images.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "palette_size": ("INT", {"default": 8, "min": 3, "max": 32, "step": 1}),
                "palette_type": (["K-means", "Median Cut", "Octree"], {"default": "K-means"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("palette", "palette_info")
    FUNCTION = "generate_palette"
    CATEGORY = "Color Tools/Analysis"
    
    def generate_palette(self, image: torch.Tensor, palette_size: int, palette_type: str) -> Tuple[str, str]:
        """
        Generate color palette from image.
        """
        # Convert tensor to numpy
        if len(image.shape) == 4:
            img_np = image[0].numpy()
        else:
            img_np = image.numpy()
        
        # Ensure image is in [0, 1] range
        if img_np.max() > 1.0:
            img_np = img_np / 255.0
        
        # Generate palette
        palette, palette_info = self._generate_palette(img_np, palette_size, palette_type)
        
        return palette, palette_info
    
    def _generate_palette(self, img: np.ndarray, palette_size: int, palette_type: str) -> Tuple[str, str]:
        """Generate color palette using specified method."""
        # Reshape image to list of pixels
        pixels = img.reshape(-1, 3)
        
        if palette_type == "K-means":
            palette_colors = self._kmeans_palette(pixels, palette_size)
        elif palette_type == "Median Cut":
            palette_colors = self._median_cut_palette(pixels, palette_size)
        elif palette_type == "Octree":
            palette_colors = self._octree_palette(pixels, palette_size)
        else:
            palette_colors = self._kmeans_palette(pixels, palette_size)
        
        # Create palette data
        palette_data = {
            "colors": palette_colors.tolist(),
            "size": palette_size,
            "method": palette_type,
            "hex_colors": [f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}" 
                          for r, g, b in palette_colors]
        }
        
        # Create palette info
        info = {
            "total_colors": len(palette_colors),
            "method": palette_type,
            "color_diversity": float(np.std(palette_colors)),
            "brightness_range": [float(np.min(palette_colors)), float(np.max(palette_colors))]
        }
        
        return json.dumps(palette_data), json.dumps(info)
    
    def _kmeans_palette(self, pixels: np.ndarray, n_colors: int) -> np.ndarray:
        """Generate palette using K-means clustering."""
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        return kmeans.cluster_centers_
    
    def _median_cut_palette(self, pixels: np.ndarray, n_colors: int) -> np.ndarray:
        """Generate palette using median cut algorithm."""
        # Simplified median cut implementation
        def median_cut(pixels, depth):
            if depth == 0 or len(pixels) == 0:
                return [np.mean(pixels, axis=0)]
            
            # Find the channel with the greatest range
            ranges = np.max(pixels, axis=0) - np.min(pixels, axis=0)
            channel = np.argmax(ranges)
            
            # Sort by the channel with greatest range
            pixels_sorted = pixels[np.argsort(pixels[:, channel])]
            
            # Split at median
            median = len(pixels_sorted) // 2
            
            # Recursively process both halves
            left = median_cut(pixels_sorted[:median], depth - 1)
            right = median_cut(pixels_sorted[median:], depth - 1)
            
            return left + right
        
        # Calculate depth needed
        depth = int(np.log2(n_colors))
        colors = median_cut(pixels, depth)
        
        # Limit to requested number of colors
        return np.array(colors[:n_colors])
    
    def _octree_palette(self, pixels: np.ndarray, n_colors: int) -> np.ndarray:
        """Generate palette using octree quantization."""
        # Simplified octree implementation
        # For now, fall back to K-means
        return self._kmeans_palette(pixels, n_colors)


class ColorSimilarity:
    """
    Find similar colors in an image based on color distance.
    Works with both file paths and image tensors.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_mode": (["file", "tensor"], {"default": "tensor"}),
                "target_color": ("STRING", {"default": "#FF0000"}),
                "similarity_threshold": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01}),
                "color_space": (["RGB", "HSV", "LAB"], {"default": "LAB"}),
            },
            "optional": {
                "image": ("IMAGE",),
                "image_path": ("STRING", {"default": "", "multiline": False}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("mask", "similarity_info")
    FUNCTION = "find_similar_colors"
    CATEGORY = "Color Tools/Analysis"
    
    def find_similar_colors(self, input_mode: str, target_color: str, 
                           similarity_threshold: float, color_space: str, 
                           image: torch.Tensor = None, image_path: str = "") -> Tuple[torch.Tensor, str]:
        """
        Find colors similar to the target color.
        Supports both file paths and image tensors.
        """
        if input_mode == "file":
            return self._find_from_file(image_path, target_color, similarity_threshold, color_space)
        else:
            return self._find_from_tensor(image, target_color, similarity_threshold, color_space)
    
    def _find_from_file(self, image_path: str, target_color: str, 
                       similarity_threshold: float, color_space: str) -> Tuple[torch.Tensor, str]:
        """Find similar colors from file"""
        if not image_path.strip():
            raise ValueError("Image path required when input_mode is 'file'")
        
        # Load image from file
        img_array = self._load_image_from_path(image_path)
        mask, info = self._find_similar_colors(img_array, target_color, similarity_threshold, color_space)
        
        # Convert mask back to tensor
        return self._array_to_tensor(mask), info
    
    def _find_from_tensor(self, image: torch.Tensor, target_color: str, 
                         similarity_threshold: float, color_space: str) -> Tuple[torch.Tensor, str]:
        """Find similar colors from tensor"""
        if image is None:
            raise ValueError("Image tensor required when input_mode is 'tensor'")
        
        # Convert tensor to numpy
        img_array = self._tensor_to_array(image)
        mask, info = self._find_similar_colors(img_array, target_color, similarity_threshold, color_space)
        
        # Convert mask back to tensor
        return self._array_to_tensor(mask), info
    
    def _load_image_from_path(self, image_path: str) -> np.ndarray:
        """Load image from file path"""
        from PIL import Image
        pil_image = Image.open(image_path)
        img_array = np.array(pil_image) / 255.0
        return img_array
    
    def _tensor_to_array(self, tensor: torch.Tensor) -> np.ndarray:
        """Convert ComfyUI tensor to numpy array"""
        if len(tensor.shape) == 4:
            return tensor[0].cpu().numpy()
        else:
            return tensor.cpu().numpy()
    
    def _array_to_tensor(self, array: np.ndarray) -> torch.Tensor:
        """Convert numpy array to ComfyUI tensor"""
        if len(array.shape) == 3:
            array = array[np.newaxis, ...]
        return torch.from_numpy(array).float()
    
    def _find_similar_colors(self, img_array: np.ndarray, target_color: str, 
                           similarity_threshold: float, color_space: str) -> Tuple[np.ndarray, str]:
        """Core similarity finding logic"""
        # Ensure image is in [0, 1] range
        if img_array.max() > 1.0:
            img_array = img_array / 255.0
        
        # Parse target color
        target_rgb = self._parse_color(target_color)
        
        # Find similar colors
        mask, info = self._find_similar_colors_internal(img_array, target_rgb, similarity_threshold, color_space)
        
        return mask, info
    
    def _parse_color(self, color_str: str) -> np.ndarray:
        """Parse color string to RGB values."""
        if color_str.startswith("#"):
            # Hex color
            hex_color = color_str[1:]
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return np.array([r, g, b])
        else:
            # Assume RGB tuple
            try:
                rgb = eval(color_str)
                return np.array(rgb) / 255.0
            except:
                return np.array([1.0, 0.0, 0.0])  # Default to red
    
    def _find_similar_colors(self, img: np.ndarray, target_rgb: np.ndarray, 
                           threshold: float, color_space: str) -> Tuple[np.ndarray, str]:
        """Find similar colors in the image."""
        # Convert to target color space
        if color_space == "RGB":
            img_space = img
            target_space = target_rgb
        elif color_space == "HSV":
            img_space = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2HSV) / 255.0
            target_space = cv2.cvtColor((target_rgb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV) / 255.0
        elif color_space == "LAB":
            img_space = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2LAB) / 255.0
            target_space = cv2.cvtColor((target_rgb * 255).astype(np.uint8), cv2.COLOR_RGB2LAB) / 255.0
        
        # Calculate color distances
        distances = np.sqrt(np.sum((img_space - target_space) ** 2, axis=2))
        
        # Create similarity mask
        similarity_mask = distances <= threshold
        
        # Calculate statistics
        total_pixels = img.shape[0] * img.shape[1]
        similar_pixels = np.sum(similarity_mask)
        similarity_percentage = (similar_pixels / total_pixels) * 100
        
        info = {
            "target_color": target_rgb.tolist(),
            "color_space": color_space,
            "threshold": threshold,
            "similar_pixels": int(similar_pixels),
            "total_pixels": int(total_pixels),
            "similarity_percentage": float(similarity_percentage)
        }
        
        return similarity_mask.astype(np.float32), json.dumps(info)


class ColorHarmony:
    """
    Analyze color harmony and relationships in images.
    Works with both file paths and image tensors.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_mode": (["file", "tensor"], {"default": "tensor"}),
                "harmony_type": (["Complementary", "Triadic", "Analogous", "Split-Complementary"], 
                               {"default": "Complementary"}),
            },
            "optional": {
                "image": ("IMAGE",),
                "image_path": ("STRING", {"default": "", "multiline": False}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("harmony_analysis", "color_relationships")
    FUNCTION = "analyze_color_harmony"
    CATEGORY = "Color Tools/Analysis"
    DESCRIPTION = (
        "分析图像的色彩和谐性，输出和谐得分（0~1，越高越和谐）及主色相分布（JSON格式）。\n\n"
        "【和谐类型说明】\n"
        "• Complementary（互补）：色轮上相差180°的两色组合，对比强烈，视觉冲击力强。\n"
        "• Triadic（三角）：色轮上均匀分布的三色（间隔120°），色彩丰富且平衡。\n"
        "• Analogous（类似）：色轮上相邻的颜色（差值＜30°），色调统一，画面柔和协调。\n"
        "• Split-Complementary（分裂互补）：一个主色 + 其互补色两侧的颜色，比互补色更柔和。\n\n"
        "【输出说明】\n"
        "• harmony_analysis：包含类型、得分和描述的 JSON。\n"
        "• color_relationships：包含主导色相列表、色相直方图及详细分析的 JSON。"
    )
    
    def analyze_color_harmony(self, input_mode: str, harmony_type: str, 
                            image: torch.Tensor = None, image_path: str = "") -> Tuple[str, str]:
        """
        Analyze color harmony in the image.
        Supports both file paths and image tensors.
        """
        if input_mode == "file":
            return self._analyze_from_file(image_path, harmony_type)
        else:
            return self._analyze_from_tensor(image, harmony_type)
    
    def _analyze_from_file(self, image_path: str, harmony_type: str) -> Tuple[str, str]:
        """Analyze harmony from file"""
        if not image_path.strip():
            raise ValueError("Image path required when input_mode is 'file'")
        
        # Load image from file
        img_array = self._load_image_from_path(image_path)
        return self._analyze_harmony(img_array, harmony_type)
    
    def _analyze_from_tensor(self, image: torch.Tensor, harmony_type: str) -> Tuple[str, str]:
        """Analyze harmony from tensor"""
        if image is None:
            raise ValueError("Image tensor required when input_mode is 'tensor'")
        
        # Convert tensor to numpy
        img_array = self._tensor_to_array(image)
        return self._analyze_harmony(img_array, harmony_type)
    
    def _load_image_from_path(self, image_path: str) -> np.ndarray:
        """Load image from file path"""
        from PIL import Image
        pil_image = Image.open(image_path)
        img_array = np.array(pil_image) / 255.0
        return img_array
    
    def _tensor_to_array(self, tensor: torch.Tensor) -> np.ndarray:
        """Convert ComfyUI tensor to numpy array"""
        if len(tensor.shape) == 4:
            return tensor[0].cpu().numpy()
        else:
            return tensor.cpu().numpy()
    
    def _analyze_harmony(self, img_array: np.ndarray, harmony_type: str) -> Tuple[str, str]:
        """Core harmony analysis logic"""
        # Ensure image is in [0, 1] range
        if img_array.max() > 1.0:
            img_array = img_array / 255.0
        
        # Analyze color harmony
        harmony_analysis, color_relationships = self._analyze_harmony_internal(img_array, harmony_type)
        
        return harmony_analysis, color_relationships
    
    def _analyze_harmony_internal(self, img: np.ndarray, harmony_type: str) -> Tuple[str, str]:
        """Analyze color harmony."""
        # Convert to HSV for hue analysis
        hsv = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
        hues = hsv[:, :, 0]
        
        # Calculate hue distribution
        hue_hist, _ = np.histogram(hues, bins=36, range=(0, 180))
        
        # Find dominant hues
        dominant_hues = np.argsort(hue_hist)[-3:][::-1] * 5  # Convert to actual hue values
        
        # Analyze harmony based on type
        if harmony_type == "Complementary":
            analysis = self._analyze_complementary(dominant_hues)
        elif harmony_type == "Triadic":
            analysis = self._analyze_triadic(dominant_hues)
        elif harmony_type == "Analogous":
            analysis = self._analyze_analogous(dominant_hues)
        elif harmony_type == "Split-Complementary":
            analysis = self._analyze_split_complementary(dominant_hues)
        else:
            analysis = {"type": "Unknown", "score": 0.0}
        
        # Create color relationships
        relationships = {
            "dominant_hues": dominant_hues.tolist(),
            "hue_distribution": hue_hist.tolist(),
            "harmony_type": harmony_type,
            "analysis": analysis
        }
        
        return json.dumps(analysis), json.dumps(relationships)
    
    def _analyze_complementary(self, hues: np.ndarray) -> Dict[str, Any]:
        """Analyze complementary color harmony."""
        if len(hues) < 2:
            return {"type": "Complementary", "score": 0.0, "description": "Insufficient color data"}
        
        # Check for complementary colors (180 degrees apart)
        hue_diff = abs(hues[0] - hues[1])
        if hue_diff > 90:
            hue_diff = 180 - hue_diff
        
        score = 1.0 - (hue_diff / 90.0)
        
        return {
            "type": "Complementary",
            "score": float(score),
            "description": f"Complementary harmony score: {score:.2f}"
        }
    
    def _analyze_triadic(self, hues: np.ndarray) -> Dict[str, Any]:
        """Analyze triadic color harmony."""
        if len(hues) < 3:
            return {"type": "Triadic", "score": 0.0, "description": "Insufficient color data"}
        
        # Check for triadic colors (120 degrees apart)
        hue_diffs = []
        for i in range(len(hues)):
            for j in range(i + 1, len(hues)):
                diff = abs(hues[i] - hues[j])
                if diff > 60:
                    diff = 120 - diff
                hue_diffs.append(diff)
        
        avg_diff = np.mean(hue_diffs)
        score = 1.0 - (avg_diff / 60.0)
        
        return {
            "type": "Triadic",
            "score": float(score),
            "description": f"Triadic harmony score: {score:.2f}"
        }
    
    def _analyze_analogous(self, hues: np.ndarray) -> Dict[str, Any]:
        """Analyze analogous color harmony."""
        if len(hues) < 2:
            return {"type": "Analogous", "score": 0.0, "description": "Insufficient color data"}
        
        # Check for analogous colors (close together on color wheel)
        hue_diffs = []
        for i in range(len(hues)):
            for j in range(i + 1, len(hues)):
                diff = abs(hues[i] - hues[j])
                if diff > 90:
                    diff = 180 - diff
                hue_diffs.append(diff)
        
        avg_diff = np.mean(hue_diffs)
        score = 1.0 - (avg_diff / 30.0)  # Analogous colors should be within 30 degrees
        
        return {
            "type": "Analogous",
            "score": float(score),
            "description": f"Analogous harmony score: {score:.2f}"
        }
    
    def _analyze_split_complementary(self, hues: np.ndarray) -> Dict[str, Any]:
        """Analyze split-complementary color harmony."""
        if len(hues) < 3:
            return {"type": "Split-Complementary", "score": 0.0, "description": "Insufficient color data"}
        
        # Check for split-complementary (one color and two colors adjacent to its complement)
        # This is a simplified analysis
        score = 0.5  # Placeholder for more complex analysis
        
        return {
            "type": "Split-Complementary",
            "score": float(score),
            "description": f"Split-complementary harmony score: {score:.2f}"
        }


class LuminanceCalculator:
    """
    Calculate perceptual luminance from an RGB or HEX color value.
    Uses the W3C WCAG relative luminance formula with gamma correction.
    Outputs a float luminance value and a JSON summary including a UI theme suggestion.
    """

    DESCRIPTION = (
        "根据 RGB 或 HEX 颜色值计算感知亮度（W3C WCAG 标准），用于判断 UI 应展示深色还是浅色主题。\n\n"
        "【输入模式】\n"
        "• rgb：输入 R / G / B 三个通道（0~255）\n"
        "• hex：输入十六进制颜色字符串，如 #ff3a2b 或 ff3a2b\n\n"
        "【亮度阈值】\n"
        "• 0.179（WCAG precise）：白字/黑字对比度相等的数学精确点\n"
        "• 0.200（conservative）：略保守，更早切换到深色字\n"
        "• 0.350（perceptual）：贴近人眼感知，视觉体验优先\n\n"
        "【输出】\n"
        "• luminance（FLOAT）：感知亮度，范围 0（纯黑）~ 1（纯白）\n"
        "• result_json（STRING）：JSON，包含输入颜色、亮度值、推荐 UI 主题（dark / light）"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_mode": (["rgb", "hex"], {"default": "hex"}),
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
                "hex_color": ("STRING", {"default": "#ffffff", "multiline": False}),
                "r": ("INT", {"default": 255, "min": 0, "max": 255, "step": 1}),
                "g": ("INT", {"default": 255, "min": 0, "max": 255, "step": 1}),
                "b": ("INT", {"default": 255, "min": 0, "max": 255, "step": 1}),
            }
        }

    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("luminance", "result_json")
    FUNCTION = "calculate"
    CATEGORY = "Color Tools/Analysis"

    def calculate(self, input_mode: str, luminance_threshold: str = "0.350  (perceptual)",
                  hex_color: str = "#ffffff", r: int = 255, g: int = 255, b: int = 255):
        if input_mode == "hex":
            r, g, b = self._hex_to_rgb(hex_color)
        hex_out = "#{:02x}{:02x}{:02x}".format(r, g, b)
        luminance = self._relative_luminance(r, g, b)
        threshold = float(luminance_threshold.split()[0])
        ui_theme = "dark" if luminance > threshold else "light"
        result = {
            "input": {"hex": hex_out, "r": r, "g": g, "b": b},
            "luminance": round(luminance, 6),
            "ui_theme": ui_theme,
            "description": (
                "Background is bright — use dark text/UI"
                if ui_theme == "dark"
                else "Background is dark — use light text/UI"
            ),
        }
        return (float(luminance), json.dumps(result, ensure_ascii=False))

    # ------------------------------------------------------------------
    def _hex_to_rgb(self, hex_color: str):
        h = hex_color.strip().lstrip("#")
        if len(h) != 6:
            raise ValueError(f"Invalid HEX color: '{hex_color}'. Expected format: #RRGGBB")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def _linearize(self, c: float) -> float:
        """Apply inverse sRGB gamma (IEC 61966-2-1)."""
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    def _relative_luminance(self, r: int, g: int, b: int) -> float:
        """W3C WCAG 2.x relative luminance, range [0, 1]."""
        R = self._linearize(r / 255)
        G = self._linearize(g / 255)
        B = self._linearize(b / 255)
        return 0.2126 * R + 0.7152 * G + 0.0722 * B


class CollageBackgroundColor:
    """
    Suggest a harmonious background color for a photo collage.
    Samples border pixels from each input image, clusters them,
    and returns the dominant border color after desaturation.
    """

    DESCRIPTION = (
        "为照片拼版自动推荐和谐底色。\n\n"
        "【多图 Batch 支持】\n"
        "输入的 IMAGE 可以是一个 batch（多张图），节点会遍历 batch 中的每一张图，"
        "分别采样各自的边缘像素，然后将所有图的边缘像素合并在一起统一聚类。"
        "这样得到的底色对 batch 内所有照片都具有代表性，适合多张照片的拼版场景。\n"
        "若只输入单张图，则退化为对该图边缘的分析。\n\n"
        "【原理】\n"
        "采样每张图四条边的像素带（宽度由 border_ratio 控制），"
        "合并后用 K-means 聚类找到最具代表性的边缘色，再压低饱和度，"
        "确保底色不与照片抢色。\n\n"
        "【参数】\n"
        "• border_ratio：单边采样宽度占图像边长的比例，采样面积 = 1-(1-2r)²（默认 0.05 = 5%）\n"
        "• saturation_scale：饱和度保留比例，0 = 全灰，1 = 保持原色（默认 0.3）\n\n"
        "【输出】\n"
        "• hex_color：推荐底色的十六进制字符串，如 #3a3a2b\n"
        "• r / g / b：对应的 RGB 整数值（0~255）"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "border_ratio": ("FLOAT", {"default": 0.05, "min": 0.01, "max": 0.25, "step": 0.01}),
                "saturation_scale": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "INT")
    RETURN_NAMES = ("hex_color", "r", "g", "b")
    FUNCTION = "pick_background"
    CATEGORY = "Color Tools/Analysis"

    def pick_background(self, image: torch.Tensor, border_ratio: float, saturation_scale: float):
        # image: (B, H, W, 3), values in [0, 1]
        all_pixels = []
        for i in range(image.shape[0]):
            img = image[i].cpu().numpy()  # (H, W, 3)
            all_pixels.append(self._border_pixels(img, border_ratio))

        all_pixels = np.concatenate(all_pixels, axis=0)

        # K-means to find dominant border color
        from sklearn.cluster import KMeans
        n = min(3, len(all_pixels))
        kmeans = KMeans(n_clusters=n, random_state=42, n_init=10)
        kmeans.fit(all_pixels)
        counts = np.bincount(kmeans.labels_)
        dominant = kmeans.cluster_centers_[counts.argmax()]  # (3,)

        # Desaturate
        result = self._desaturate(dominant, saturation_scale)

        r, g, b = (np.clip(result * 255, 0, 255)).astype(int).tolist()
        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        return (hex_color, r, g, b)

    def _border_pixels(self, img: np.ndarray, border_ratio: float) -> np.ndarray:
        H, W, _ = img.shape
        bh = max(1, int(H * border_ratio))
        bw = max(1, int(W * border_ratio))
        top    = img[:bh, :, :].reshape(-1, 3)
        bottom = img[H - bh:, :, :].reshape(-1, 3)
        left   = img[bh:H - bh, :bw, :].reshape(-1, 3)
        right  = img[bh:H - bh, W - bw:, :].reshape(-1, 3)
        return np.concatenate([top, bottom, left, right], axis=0)

    def _desaturate(self, rgb: np.ndarray, saturation_scale: float) -> np.ndarray:
        pixel = (np.clip(rgb, 0, 1) * 255).astype(np.uint8).reshape(1, 1, 3)
        hsv = cv2.cvtColor(pixel, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[0, 0, 1] *= saturation_scale
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        return result[0, 0] / 255.0
