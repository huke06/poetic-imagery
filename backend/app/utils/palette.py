"""意象配色体系：按「分类色相族 + 名称哈希」确定性分配中国传统色

设计目标：50+ 意象时配色依然和谐、可预期、有传统韵味
- 每个分类绑定一个传统色族（如 植物→青绿族、天象→青蓝族）
- 同族内按意象名的确定性哈希选取具体色号，保证同族近似、异族有别
- 完全确定性：同名同分类无论何时计算结果一致，便于前后端复现
"""
import hashlib

# 中国传统色卡（名称, 色号）——按色相族组织
COLOR_FAMILIES: dict[str, list[tuple[str, str]]] = {
    # 天象：青蓝紫族（夜空与光影）
    "天象": [
        ("石青", "#2B4C7E"), ("黛蓝", "#3B5069"), ("靛青", "#3F4E8C"), ("绀青", "#2E3A59"),
        ("远山黛", "#4A5D7E"), ("天水碧", "#4F7C8A"), ("月白", "#6E8CA0"), ("烟青", "#5A6B7A"),
        ("昙蓝", "#4B5B8A"), ("苍蓝", "#46617C"),
    ],
    # 植物：青绿族（草木葱茏）
    "植物": [
        ("竹青", "#5B7C5F"), ("艾绿", "#6B8E6F"), ("松石绿", "#4E7C74"), ("豆绿", "#7A9A6D"),
        ("苍绿", "#4F6B54"), ("柳黄绿", "#8A9A5B"), ("檀栾", "#5E7A5E"), ("茵陈", "#6F8560"),
        ("翠微", "#4C7A63"), ("菉竹", "#698B69"),
    ],
    # 动物：赭黄族（走兽飞羽）
    "动物": [
        ("赭石", "#9B4423"), ("秋香", "#A8823C"), ("藤黄", "#B08A3E"), ("檀色", "#8C5B3F"),
        ("驼褐", "#8A6D4B"), ("鸾色", "#96754A"), ("鹿褐", "#7C6248"), ("鸭头绿", "#6B7C4A"),
        ("雁灰", "#7A7568"), ("莺黄", "#B59A4A"),
    ],
    # 器物：沉雅族（钟鼎器皿）
    "器物": [
        ("青铜", "#5F7361"), ("古铜", "#7C6A4F"), ("沉香", "#6B5B4E"), ("墨黛", "#4A4A52"),
        ("松烟", "#55524E"), ("窑变", "#7E5A50"), ("紫砂", "#7A4E42"), ("铜绿", "#5A7A68"),
        ("铁灰", "#5C5C60"), ("陶土", "#8A6248"),
    ],
    # 地理：山水族（河山烟霞）
    "地理": [
        ("岱赭", "#8A5A3B"), ("溪蓝", "#4A6B7A"), ("涧石", "#6A7A72"), ("沧浪", "#4E7A8A"),
        ("沙白", "#A89A7E"), ("岩青", "#5B6B60"), ("川黛", "#3E5A6B"), ("汀绿", "#6B8A72"),
        ("峡紫", "#6B5B7A"), ("塬黄", "#A08A5B"),
    ],
    # 人事/情感（备用分类）：绛红族
    "人事": [
        ("绛紫", "#7A4A5E"), ("胭脂", "#9B3B4E"), ("朱砂", "#9B2C1F"), ("绛纱", "#8C4653"),
        ("藕荷", "#8A6B7C"), ("茜色", "#A84A4A"), ("妃色", "#B0717A"), ("檀心", "#96525E"),
        ("杏绛", "#A06B5E"), ("绛红", "#8E3B3B"),
    ],
}

DEFAULT_FAMILY = [("玄青", "#3A4A5A"), ("黛色", "#4A4A56"), ("苍灰", "#6B6B66"), ("缥色", "#7A8A92")]

ALL_COLORS = [(name, hex_, fam) for fam, colors in COLOR_FAMILIES.items() for name, hex_ in colors]


def _hash_index(key: str, modulo: int) -> int:
    return int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % modulo


def assign_color(concept_name: str, category: str = "") -> dict:
    """为意象确定性分配传统色，返回 {color, color_name, family}"""
    family = COLOR_FAMILIES.get(category, DEFAULT_FAMILY)
    idx = _hash_index(concept_name, len(family))
    color_name, hex_ = family[idx]
    return {"color": hex_, "color_name": color_name, "family": category or "通用"}


def palette_for_category(category: str = "") -> list[dict]:
    """返回某分类（或全部）的候选色卡，供后台选色"""
    colors = COLOR_FAMILIES.get(category, DEFAULT_FAMILY)
    return [{"color": h, "color_name": n} for n, h in colors]
