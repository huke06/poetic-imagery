# -*- coding: utf-8 -*-
"""分类体系工具：一级情感标签映射 · 朝代九大段归并 · 艺术品朝代识别"""
import re

# ═══════════════ 一级情感标签（七大类） ═══════════════
EMOTION_MAIN_LABELS = ["情感心绪类", "交往离别类", "人生感悟类", "自然山水类",
                       "历史文化类", "志向抱负类", "超脱境界类"]

# 二级情感标签 → 一级情感标签
EMOTION_MAIN_MAP = {
    # ── 情感心绪类 ──
    "怀人": "情感心绪类", "孤寂": "情感心绪类", "落寞": "情感心绪类",
    "相思": "情感心绪类", "思念": "情感心绪类", "愁苦": "情感心绪类",
    "身世愁苦": "情感心绪类", "悼亡": "情感心绪类", "闺怨": "情感心绪类",
    "孤独": "情感心绪类", "忧愁": "情感心绪类", "哀怨": "情感心绪类",
    # ── 交往离别类 ──
    "离别": "交往离别类", "离愁": "交往离别类", "思乡": "交往离别类",
    "赠别勉励": "交往离别类", "友谊": "交往离别类", "人际交往": "交往离别类",
    "宴饮欢乐": "交往离别类", "爱情": "交往离别类", "送别": "交往离别类",
    "羁旅": "交往离别类",
    # ── 人生感悟类 ──
    "时光流逝": "人生感悟类", "时空永恒": "人生感悟类", "哲理": "人生感悟类",
    "人生隐喻": "人生感悟类", "永恒": "人生感悟类", "惜春": "人生感悟类",
    "生命感悟": "人生感悟类",
    # ── 自然山水类 ──
    "山水": "自然山水类", "闲适": "自然山水类", "山水闲适": "自然山水类",
    "自然赞美": "自然山水类", "季节感怀": "自然山水类", "田园": "自然山水类",
    # ── 历史文化类 ──
    "怀古": "历史文化类", "怀古咏史": "历史文化类", "咏物": "历史文化类",
    "咏物言志": "历史文化类", "边塞苍凉": "历史文化类", "苍凉": "历史文化类",
    "战争苦难": "历史文化类", "厌战": "历史文化类", "民生疾苦": "历史文化类",
    # ── 志向抱负类 ──
    "豪迈": "志向抱负类", "壮烈": "志向抱负类", "悲壮": "志向抱负类",
    "怀才不遇": "志向抱负类", "忧国忧民": "志向抱负类", "家国情怀": "志向抱负类",
    "建功立业": "志向抱负类",
    # ── 超脱境界类 ──
    "禅意": "超脱境界类", "仙道": "超脱境界类", "隐逸": "超脱境界类",
    "超脱": "超脱境界类",
}


def emotion_main_of(emotion: str) -> str:
    """二级情感标签 → 一级情感标签（未知时返回空串）

    优先级：运行时从统计数据学习到的映射（LEARNED_MAP）→ 静态映射表。
    """
    if not emotion:
        return ""
    e = emotion.strip()
    if e in LEARNED_MAP:
        return LEARNED_MAP[e]
    if e in EMOTION_MAIN_MAP:
        return EMOTION_MAIN_MAP[e]
    if e in EMOTION_MAIN_LABELS:
        return e
    # 模糊兜底：标签包含已知关键词
    for k, v in EMOTION_MAIN_MAP.items():
        if k in e or e in k:
            return v
    return ""


# 运行时学习的映射（由情感统计 CSV 导入时更新，优先于静态表）
LEARNED_MAP: dict[str, str] = {}


def update_learned_map(mapping: dict[str, str]):
    LEARNED_MAP.update(mapping)


def rebuild_learned_map_from_db(db):
    """启动/导入后调用：从 emotion_stat 表按多数表决重建学习映射"""
    from collections import Counter, defaultdict
    from ..models import EmotionStat
    stat = defaultdict(Counter)
    for row in db.query(EmotionStat.word, EmotionStat.emotion, EmotionStat.category).all():
        if row.emotion and row.category:
            stat[row.emotion][row.category] += 1
    mapping = {e: cnt.most_common(1)[0][0] for e, cnt in stat.items()}
    LEARNED_MAP.clear()
    LEARNED_MAP.update(mapping)
    return mapping


# ═══════════════ 朝代九大段归并 ═══════════════
DYNASTY_GROUPS = ["先秦", "秦汉", "魏晋南北朝", "隋唐", "五代十国", "宋", "元", "明", "清"]

# 艺术品朝代组：九大段之外，近现代/当代单独成组
ARTWORK_DYNASTY_GROUPS = DYNASTY_GROUPS + ["近现代", "当代"]

_GROUP_KEYWORDS = [
    # (组, 关键词) —— 顺序敏感：先匹配的生效
    ("先秦", ["先秦", "上古", "夏", "商", "西周", "东周", "春秋", "战国"]),
    ("秦汉", ["秦", "汉", "新朝", "新莽"]),
    ("魏晋南北朝", ["魏晋", "三国", "曹魏", "蜀汉", "孙吴", "东吴", "晋", "十六国",
                    "南北朝", "南朝", "北朝", "南梁", "南齐", "南汉", "北魏", "北齐",
                    "北周", "东魏", "西魏", "前凉", "前秦", "西凉", "西梁", "刘宋"]),
    ("隋唐", ["隋", "唐", "武周", "盛唐", "中唐", "晚唐", "初唐"]),
    ("五代十国", ["五代", "十国", "后梁", "后唐", "后晋", "后汉", "后周",
                   "前蜀", "后蜀", "南唐", "吴越", "闽国", "南汉", "南平", "北汉"]),
    ("宋", ["宋", "北宋", "南宋", "辽", "金", "西夏"]),
    ("元", ["元", "蒙古"]),
    ("明", ["明", "南明"]),
    ("清", ["清"]),
]

# 近现代/当代细分（艺术品朝代用；诗文九大段时间轴仍归入清）
_POETRY_MODERN = ["民国", "近现代", "近代", "现代", "当代", "现当代"]
_ARTWORK_MODERN = [
    ("当代", ["当代", "现当代"]),
    ("近现代", ["近现代", "现代", "近代", "民国"]),
]


def _match_group(period: str) -> str:
    """按关键词出现的最早位置匹配九大朝代段（不含近现代细分）"""
    best_group, best_pos = "", 10 ** 9
    for group, keywords in _GROUP_KEYWORDS:
        for kw in keywords:
            pos = period.find(kw)
            if pos >= 0 and pos < best_pos:
                best_group, best_pos = group, pos
    return best_group


def dynasty_group_of(period: str) -> str:
    """细粒度朝代/时期 → 九大朝代段（诗文时间轴用；近现代归入清；未知返回空串）"""
    if not period:
        return ""
    p = period.strip()
    if p in DYNASTY_GROUPS:
        return p
    # 诗文时间轴无现当代段，近现代/当代并入清
    if any(kw in p for kw in _POETRY_MODERN):
        return "清"
    return _match_group(p)


def artwork_dynasty_group(period: str) -> str:
    """艺术品朝代归类：九大段之外，近现代/当代单独成组（不硬套古诗朝代）

    例：'清代·清雍正' → '清'；'当代' → '当代'；'近现代' → '近现代'
    """
    if not period:
        return ""
    p = period.strip()
    # 现当代细分优先（避免被"清"误吞）
    for group, keywords in _ARTWORK_MODERN:
        if any(kw in p for kw in keywords):
            return group
    if p in DYNASTY_GROUPS:
        return p
    return _match_group(p)


def normalize_artwork_dynasty(dynasty_period: str, dynasty: str) -> str:
    """从「朝代·时期」与旧朝代字段中识别艺术品主朝代（用于统计与检索）

    例：'清代·清雍正' → '清'；'当代' → '当代'；'近现代' → '近现代'
    """
    raw = (dynasty_period or dynasty or "").strip()
    if not raw:
        return ""
    group = artwork_dynasty_group(raw)
    if group:
        return group
    # 去掉修饰词后直接取朝代字
    cleaned = re.sub(r"(代|代·|·|时期|晚期|早期|中期|初期|末期)", "", raw)
    return cleaned[:2] if cleaned else ""


# ═══════════════ 艺术品主题拆分 ═══════════════
def split_subjects(raw: str) -> list[str]:
    """拆分艺术品主题：兼容中英文分号、顿号、逗号（去重保序）

    例：'中国绘画；山水、人物' → ['中国绘画', '山水', '人物']
    """
    seen, out = set(), []
    for part in re.split(r"[;；、,，]+", raw or ""):
        p = part.strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def normalize_subjects(raw: str) -> str:
    """主题归一化为英文分号分隔（入库前统一格式）"""
    return ";".join(split_subjects(raw))


# ═══════════════ 共现类型 ═══════════════
COOCCURRENCE_TYPES = ["句内", "跨句", "全诗"]


def dominant_cooccurrence_type(same_sentence: int, adjacent_sentence: int, same_poem: int) -> str:
    """由三级共现次数推断主导共现类型"""
    counts = {"句内": same_sentence, "跨句": adjacent_sentence, "全诗": same_poem}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else "全诗"
