# -*- coding: utf-8 -*-
"""意象分享卡片渲染（服务端 SVG）+ QR 码"""
import base64
import io
import re
from functools import lru_cache
from pathlib import Path

import qrcode
import qrcode.image.svg

try:
    from PIL import Image
except ImportError:  # 无 Pillow 时 Logo 回退为文字印章
    Image = None

from ..utils.taxonomy import emotion_main_of

FONT_SANS = "PingFang SC,Microsoft YaHei,sans-serif"
FONT_KAI = "Kaiti SC,STKaiti,KaiTi,SimSun,serif"
FONT_SONG = "Noto Serif SC,Songti SC,STSong,SimSun,serif"

# 一级情感大类配色（镜像前端 utils/emotionColors.js，全站统一）
EMOTION_MAIN_COLORS = {
    "情感心绪类": "#6E4A7E", "交往离别类": "#9B4423", "人生感悟类": "#8A6D3B",
    "自然山水类": "#5B7C5F", "历史文化类": "#2B4C7E", "志向抱负类": "#9B2C1F",
    "超脱境界类": "#3A7A7C",
}

LOGO_PATH = Path(__file__).resolve().parents[1] / "static" / "logo.png"


def _mix(c1: str, c2: str, r: float) -> str:
    """线性插值混合两色：r 为 c1 占比（0~1），返回 hex。用于替代 SVG 不支持的 color-mix。"""
    a = [int(c1.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    m = [round(a[i] * r + b[i] * (1 - r)) for i in range(3)]
    return "#" + "".join(f"{v:02x}" for v in m)


def _text_width(s: str, size: float) -> float:
    """粗略估算文本宽度：CJK 按 1 字宽、半角/标点按 0.55 字宽。"""
    return sum(size if ord(ch) > 0x2E80 else size * 0.55 for ch in (s or ""))


@lru_cache(maxsize=1)
def _logo_data_uri(size: int = 64) -> str:
    """读取品牌 Logo，缩放为 size×size 后 base64 内嵌（SVG 自包含，PNG 导出不跨域）。

    文件缺失或 Pillow 不可用时返回空串，调用方回退为文字印章「诗象」。
    """
    if Image is None or not LOGO_PATH.exists():
        return ""
    try:
        with Image.open(LOGO_PATH) as im:
            im = im.convert("RGBA").resize((size, size), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def _tag_row(items, cx: float, y: float, max_w: float, font: int = 13,
             pad_x: int = 10, h: int = 26, gap: int = 8, line_gap: int = 8) -> tuple[str, float]:
    """居中渲染一行（可自动换行）低饱和标签。

    items: [(label, text_hex, border_hex, stroke_op, fill_op)]，返回 (svg, 占用高度)。
    """
    rows, cur, cur_w = [], [], 0
    for it in items:
        w = _text_width(it[0], font) + pad_x * 2 + gap
        if cur and cur_w + w > max_w:
            rows.append(cur)
            cur, cur_w = [it], w
        else:
            cur.append(it)
            cur_w += w
    if cur:
        rows.append(cur)

    svg = ""
    for ri, row in enumerate(rows):
        total = sum(_text_width(it[0], font) + pad_x * 2 for it in row) + gap * (len(row) - 1)
        x = cx - total / 2
        ry = y + ri * (h + line_gap)
        for label, tc, bc, so, fo in row:
            tw = _text_width(label, font) + pad_x * 2
            svg += (
                '<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{bc}" fill-opacity="{fo}" '
                'stroke="{bc}" stroke-opacity="{so}" stroke-width="1"/>'
                '<text x="{tx}" y="{ty}" font-size="{fs}" fill="{tc}" font-family="{f}">{t}</text>'
            ).format(x=x, y=ry, w=tw, h=h, bc=bc, fo=fo, so=so, tx=x + pad_x, ty=ry + h - 8,
                     fs=font, tc=tc, f=FONT_SONG, t=_esc(label))
            x += tw + gap
    height = len(rows) * (h + line_gap) - line_gap
    return svg, height


def _make_qrcode_svg(url: str, size: int = 80) -> str:
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=10, border=1)
    buf = io.BytesIO()
    img.save(buf)
    raw = buf.getvalue().decode("utf-8")
    raw = re.sub(r'<\?xml[^?]*\?>', '', raw)
    raw = re.sub(r'</svg>', '', raw)
    raw = re.sub(r'<svg[^>]*>', f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">', raw, count=1)
    return raw


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """按 max_chars 宽度折行"""
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    if text:
        lines.append(text)
    return lines


def _wrap_verse_lines(verse: str, per_line: int = 10) -> list[str]:
    """按标点优先、其次固定宽度，把诗句折成若干行（完整展示，不截断）"""
    if not verse:
        return []
    pieces = re.split(r'([，。！？；、：,.!?;:\n])', verse)
    sentences = []
    buf = ""
    for p in pieces:
        if not p:
            continue
        if p == "\n":
            if buf:
                sentences.append(buf)
                buf = ""
            continue
        buf += p
        if p in "，。！？；、：,.!?;:":
            sentences.append(buf)
            buf = ""
    if buf:
        sentences.append(buf)

    lines = []
    cur = ""
    for s in sentences:
        if len(cur) + len(s) <= per_line:
            cur += s
        else:
            if cur:
                lines.append(cur)
            while len(s) > per_line:
                lines.append(s[:per_line])
                s = s[per_line:]
            cur = s
    if cur:
        lines.append(cur)
    return [ln for ln in lines if ln]


def render_share_card(concept, clause: str, poetry, poetry_count: int = 0, artwork_count: int = 0, qr_svg_inline: str = "") -> str:
    color = concept.theme_color or "#2B4C7E"
    name = concept.name or "?"
    ink = "#2C2C2C"
    warm = "#7A7468"          # 柔和灰褐（出处 / 统计标签）
    faint = "#9A9A9A"

    W = 720
    H = 480                    # 3:2 横版（明信片）
    M = 56                     # 左右安全边距
    Lx = (M + W / 2) / 2       # 左栏中心（意象名 + 分类）
    Rx = (W / 2 + (W - M)) / 2  # 右栏中心（名句 + 出处 + 统计）
    panel_w = W / 2 - M        # 单栏可用宽度

    name_len = len(name)
    name_size = 84 if name_len <= 2 else 70 if name_len == 3 else 58 if name_len == 4 else 48
    name_ls = max(4, round(name_size * 0.05))

    # ── 左栏：① 意象名（第一视觉焦点）② 分类 ──
    name_svg = (
        '<text x="{cx}" y="{ny}" font-size="{fs}" fill="{ink}" font-family="{f}" text-anchor="middle" '
        'letter-spacing="{ls}">{n}</text>'
    ).format(cx=Lx, ny=180, fs=name_size, ink=ink, f=FONT_SONG, ls=name_ls, n=_esc(name))
    uw = min(name_size * 1.7, 170)
    underline = ('<rect x="{x}" y="{y}" width="{w}" height="1" fill="{c}" opacity="0.4"/>'
                 ).format(x=Lx - uw / 2, y=222, w=uw, c=color)

    cat_items = []
    cat_parts = [p for p in [concept.category_main, concept.category_sub] if p]
    if cat_parts:
        cat_items = [(" · ".join(cat_parts), _mix(color, ink, 0.74), color, 0.30, 0.06)]
    cat_svg, cat_h = _tag_row(cat_items, Lx, 264, panel_w)

    raw_tags = [t.strip() for t in (concept.emotion_tags or "").split(",") if t.strip()]
    seen, mains = set(), []
    for t in raw_tags:
        m = emotion_main_of(t)
        if m and m not in seen:
            seen.add(m)
            mains.append(m)
    mains = mains[:4]
    if mains:
        emo_items = [(m, _mix(EMOTION_MAIN_COLORS.get(m, "#8A6D3B"), warm, 0.62),
                      EMOTION_MAIN_COLORS.get(m, "#8A6D3B"), 0.22, 0.05) for m in mains]
    else:
        emo_items = [(t, _mix(color, ink, 0.74), color, 0.30, 0.06) for t in raw_tags[:3]]
    emo_svg, emo_h = _tag_row(emo_items, Lx, 306, panel_w)

    # ── 右栏：③ 经典诗句（第二视觉重点）④ 出处 ⑤ 统计 ──
    verse_lines = _wrap_verse_lines(clause, 8)[:2]
    verse_font, verse_lh = 32, 50
    verse_rows = ""
    for i, ln in enumerate(verse_lines):
        verse_rows += (
            '<text x="{cx}" y="{vy}" text-anchor="middle" font-size="{fs}" fill="{ink}" '
            'font-family="{f}" letter-spacing="3">{t}</text>'
        ).format(cx=Rx, vy=150 + i * verse_lh, fs=verse_font, ink=ink, f=FONT_KAI, t=_esc(ln))

    author_text = ""
    if poetry:
        author_text = f'{poetry.dynasty} · {poetry.author} 《{poetry.title}》'
        if _text_width(author_text, 13) > panel_w:
            ts = poetry.title[:8] + "…" if len(poetry.title) > 8 else poetry.title
            author_text = f'{poetry.dynasty} · {poetry.author} 《{ts}》'
    author_svg = ('<text x="{cx}" y="{ay}" text-anchor="middle" font-size="13" fill="{warm}" font-family="{f}">{t}</text>'
                  ).format(cx=Rx, ay=262, warm=warm, f=FONT_SONG, t=_esc(author_text)) if author_text else ""

    num_color = _mix(color, ink, 0.12)
    stat_svg = (
        '<text x="{x1}" y="{sy}" text-anchor="middle" font-size="13" fill="{warm}" font-family="{f}">'
        '收录诗词 <tspan fill="{nc}">{n1}</tspan> 首</text>'
        '<line x1="{cx}" y1="{ly1}" x2="{cx}" y2="{ly2}" stroke="{ink}" stroke-opacity="0.15" stroke-width="1"/>'
        '<text x="{x2}" y="{sy}" text-anchor="middle" font-size="13" fill="{warm}" font-family="{f}">'
        '关联古画 <tspan fill="{nc}">{n2}</tspan> 幅</text>'
    ).format(x1=Rx - 64, x2=Rx + 64, sy=308, warm=warm, f=FONT_SONG, nc=num_color,
             n1=poetry_count or 0, n2=artwork_count or 0, cx=Rx, ly1=296, ly2=320, ink=ink)

    # ── ⑥ 底部品牌落款 + Logo（缩小降重，作品牌落款而非视觉主体）──
    logo_size = 44
    logo_x = W - M - logo_size
    logo_y = H - 38 - logo_size
    brand_y = logo_y + logo_size / 2 + 4
    brand_svg = ('<text x="{x}" y="{y}" font-size="11" fill="{faint}" font-family="{f}">{t}</text>'
                 ).format(x=M, y=brand_y, faint=faint, f=FONT_SONG, t=_esc("诗象万千 · 游心万象，一眼千年"))

    logo_uri = _logo_data_uri(logo_size)
    if logo_uri:
        seal_svg = ('<image x="{x}" y="{y}" width="{s}" height="{s}" href="{u}" '
                    'preserveAspectRatio="xMidYMid meet"/>'
                    ).format(x=logo_x, y=logo_y, s=logo_size, u=logo_uri)
    else:
        s = 30
        sx, sy = W - M - s, H - 40 - s
        seal_svg = (
            '<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="3" fill="#9B2C1F" opacity="0.9"/>'
            '<text x="{cx}" y="{ty}" font-size="13" fill="#F5F1E8" text-anchor="middle" font-family="{fk}">诗象</text>'
        ).format(x=sx, y=sy, s=s, cx=sx + s / 2, ty=sy + s - 9, fk=FONT_KAI)

    qr_block = f'<g transform="translate(586, 300) scale(0.85)">{qr_svg_inline}</g>' if qr_svg_inline else ""

    return f'''<!-- share_card_v6 --><svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="#F5F1E8"/>
  <rect width="{W}" height="{H}" fill="url(#wash)" opacity="0.5"/>
  <defs>
    <radialGradient id="wash" cx="50%" cy="10%" r="95%">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect x="14" y="14" width="{W - 28}" height="{H - 28}" fill="none" stroke="{ink}" stroke-opacity="0.08" stroke-width="1"/>
  <rect x="24" y="24" width="{W - 48}" height="{H - 48}" fill="none" stroke="{ink}" stroke-opacity="0.05" stroke-width="1"/>
  {name_svg}
  {underline}
  {cat_svg}
  {emo_svg}
  {verse_rows}
  {author_svg}
  {stat_svg}
  {brand_svg}
  {seal_svg}
  {qr_block}
</svg>'''


def render_exploration_card(explored: list, report: str = "", theme_count: int = 0) -> str:
    count = len(explored)
    names = " · ".join(item.get("name", "?") for item in explored[:12])
    if len(explored) > 12:
        names += f" …等{count}个"

    report_text = (report or "").replace("**", "").replace("###", "").replace("##", "").replace("__", "")[:200]
    color = "#2B4C7E"

    report_lines = _wrap_verse_lines(report_text, 26)[:6]
    report_rows = ""
    for i, ln in enumerate(report_lines):
        report_rows += '<tspan x="56" dy="{dy}">{t}</tspan>'.format(dy=0 if i == 0 else 24, t=_esc(ln))

    # 右下角平台 logo（缺失/无 Pillow 时回退为「诗象」文字印章）
    logo_size = 44
    logo_x = 720 - 56 - logo_size
    logo_y = 380
    logo_uri = _logo_data_uri(logo_size)
    if logo_uri:
        seal_svg = ('<image x="{x}" y="{y}" width="{s}" height="{s}" href="{u}" '
                    'preserveAspectRatio="xMidYMid meet"/>'
                    ).format(x=logo_x, y=logo_y, s=logo_size, u=logo_uri)
    else:
        seal_svg = (
            '<rect x="590" y="380" width="44" height="44" rx="4" fill="#9B2C1F" opacity="0.9"/>'
            '<text x="612" y="410" font-size="20" fill="#F5F1E8" text-anchor="middle" font-family="{fk}">诗象</text>'
        ).format(fk=FONT_KAI)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="440" viewBox="0 0 720 440">
  <rect width="720" height="440" fill="#F5F1E8"/>
  <defs>
    <radialGradient id="wash" cx="18%" cy="16%" r="80%">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="720" height="440" fill="url(#wash)" opacity="0.7"/>
  <rect x="12" y="12" width="696" height="416" fill="none" stroke="{color}" stroke-width="2" opacity="0.4"/>
  <rect x="18" y="18" width="684" height="404" fill="none" stroke="{color}" stroke-width="0.75" opacity="0.25"/>

  <text x="360" y="70" font-size="36" fill="{color}" text-anchor="middle" font-family="{FONT_KAI}">我的意象地图</text>

  <text x="360" y="120" font-size="20" fill="#2C2C2C" text-anchor="middle" font-family="{FONT_SANS}">
   已探索 <tspan fill="{color}" font-weight="bold">{count}</tspan> 个意象
   · 跨越 <tspan fill="{color}" font-weight="bold">{theme_count}</tspan> 个主题族
  </text>

  <line x1="160" y1="140" x2="560" y2="140" stroke="{color}" stroke-width="0.75" opacity="0.25"/>

  <text x="56" y="178" font-size="15" fill="#6B6B6B" font-family="{FONT_SONG}">
    <tspan x="56" dy="0">{_esc(names)}</tspan>
  </text>

  <text x="56" y="240" font-size="14" fill="#4A4A4A" font-family="{FONT_SONG}">
    <tspan x="56" dy="0" font-weight="bold" fill="{color}">AI 探索报告</tspan>
  </text>
  <line x1="56" y1="248" x2="156" y2="248" stroke="{color}" stroke-width="3" opacity="0.55"/>
  <text x="56" y="264" font-size="13" fill="#2C2C2C" font-family="{FONT_SONG}">
    {report_rows}
  </text>

  <text x="56" y="410" font-size="12" fill="#9A9A9A" font-family="{FONT_SONG}">诗象万千 · 游心万象，一眼千年</text>

  {seal_svg}
</svg>'''
