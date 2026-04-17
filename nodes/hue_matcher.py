"""
Hue Matcher

Compares a reference color against up to 8 candidate colors using
perceptually-uniform OKLCH hue distance, and ranks candidates closest-first.
"""

import json
from .hue_distance import oklch_hue_distance

_EMPTY = ("", "none", "null", "-")


def _is_provided(hex_str) -> bool:
    return isinstance(hex_str, str) and hex_str.strip().lstrip("#") not in _EMPTY and len(hex_str.strip().lstrip("#")) == 6


class HueMatcher:

    DESCRIPTION = (
        "将参考颜色与最多 8 个候选颜色在 OKLCH 色相空间中做感知距离排序。\n\n"
        "【ref_color】参考颜色 HEX，通常来自 DominantColorFilter 的 representative_hex\n"
        "【color_1 ~ color_8】候选颜色 HEX，未接入的槽位留空即可\n\n"
        "【输出】\n"
        "  • best_index：距离最近的候选序号（1~8）\n"
        "  • best_hex：距离最近的候选颜色 HEX\n"
        "  • ranked_indices：所有已接入候选按距离升序排列的序号，JSON 数组\n"
        "  • distances_json：与 ranked_indices 平行的 OKLCH 色相距离（0~180°），JSON 数组"
    )

    @classmethod
    def INPUT_TYPES(cls):
        hex_slot = lambda default: ("STRING", {"default": default, "multiline": False})
        return {
            "required": {
                "ref_color": ("STRING", {"default": "#ffffff", "multiline": False}),
            },
            "optional": {
                "color_1": hex_slot(""),
                "color_2": hex_slot(""),
                "color_3": hex_slot(""),
                "color_4": hex_slot(""),
                "color_5": hex_slot(""),
                "color_6": hex_slot(""),
                "color_7": hex_slot(""),
                "color_8": hex_slot(""),
            }
        }

    RETURN_TYPES  = ("INT",        "STRING",     "STRING",          "STRING")
    RETURN_NAMES  = ("best_index", "best_hex",   "ranked_indices",  "distances_json")
    FUNCTION      = "match"
    CATEGORY      = "Color Tools/Analysis"

    def match(
        self,
        ref_color: str,
        color_1: str = "", color_2: str = "", color_3: str = "",
        color_4: str = "", color_5: str = "", color_6: str = "",
        color_7: str = "", color_8: str = "",
    ):
        candidates = [color_1, color_2, color_3, color_4,
                      color_5, color_6, color_7, color_8]

        # Compute distance for each provided slot
        results = []  # (1-based index, distance)
        for i, color in enumerate(candidates, start=1):
            if _is_provided(color):
                dist = oklch_hue_distance(ref_color, color)
                results.append((i, round(dist, 4)))

        if not results:
            return (0, "", "[]", "[]")

        # Sort by distance ascending; ties broken by original index (stable)
        results.sort(key=lambda x: (x[1], x[0]))

        best_index     = results[0][0]
        best_hex       = candidates[best_index - 1]
        ranked_indices = json.dumps([r[0] for r in results])
        distances_json = json.dumps([r[1] for r in results])

        return (best_index, best_hex, ranked_indices, distances_json)
