"""平仄标注工具：基于拼音声调近似推定

说明：中古音平仄以《平水韵》为准，此处用现代普通话声调近似（一、二声为平，三、四声为仄），
并内置常见入声字表修正，供格律参考，不作为学术依据。
"""
from pypinyin import Style, lazy_pinyin

# 常见入声字（普通话已派入平声者），标注时判为仄
ENTERING_TONE_CHARS = set(
    "一七八十百月日不白得德读书出说客色北黑笔力立历石食识即席息惜敌笛"
    "客隔格革国郭获或惑活合鹤核竭节结洁杰捷截绝觉爵角脚乐落洛络骆绿"
    "律率略袜灭蔑篾末莫寞漠墨默木目牧穆纳虐疟诺匹迫朴泣契恰切窃怯"
    "却鹊雀阙缺热入若弱色涩瑟杀刹霎舌设涉摄摄失湿十什石时实食拾识"
    "室释饰适叔淑梳疏孰熟塾束述术戍刷率蟀说朔硕烁铄速宿肃粟谡缩索"
    "踏榻蹋塔獭挞特惕倜帖贴铁听突秃托脱拓斡握沃呜屋无勿务物雾夕"
    "汐矽穸昔惜晰晰膝习席袭檄峡狭匣狎辖黠吓夏屑亵燮血泄绁卸屑"
    "雪血穴学谑勋压押鸭轧挹悒邑易益翼翊忆忆臆阴音喑欲玉育郁狱浴"
    "域越月岳悦钥杂砸则泽择贼窄宅寨翟折哲辙浙这织直值植殖执侄职"
    "只汁织之知卮跖掷踯质炙秩栉窒捉桌涿啄酌浊濯着足卒族作昨琢撮"
)


def char_tone(ch: str) -> str:
    """返回单字平仄：'平' / '仄' / ''（非汉字）"""
    if not ("一" <= ch <= "鿿"):
        return ""
    if ch in ENTERING_TONE_CHARS:
        return "仄"
    py = lazy_pinyin(ch, style=Style.TONE3, neutral_tone_with_five=True)
    if not py or not py[0]:
        return ""
    tone = "".join(c for c in py[0] if c.isdigit())
    if tone in ("1", "2"):
        return "平"
    if tone in ("3", "4", "5"):
        return "仄"
    return ""


def verse_tones(verse: str) -> str:
    """返回一句诗的平仄串，如 '平平仄仄平'；非汉字跳过"""
    return "".join(char_tone(ch) for ch in verse if char_tone(ch))


def poem_tones(clauses: list[str]) -> list[dict]:
    """整首标注：按句读（逗/句/顿）拆为诗行后逐行标注平仄"""
    import re
    result = []
    for clause in clauses:
        for line in re.split(r"[，。！？；、：\s]+", clause):
            if not line:
                continue
            chars = [{"char": ch, "tone": char_tone(ch)} for ch in line if "一" <= ch <= "鿿"]
            if chars:
                result.append({"clause": line, "tone_string": "".join(c["tone"] for c in chars), "chars": chars})
    return result
