# -*- coding: utf-8 -*-
"""意象分享卡片渲染（服务端 SVG）+ QR 码"""
import io
import re

import qrcode
import qrcode.image.svg

FONT_SANS = "PingFang SC,Microsoft YaHei,sans-serif"
FONT_KAI = "Kaiti SC,STKaiti,KaiTi,SimSun,serif"


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
    name_len = len(name)

    name_size = 72 if name_len <= 2 else 56 if name_len <= 3 else 42
    name_x = 64
    name_y = 130

    # 情感标签芯片
    tag_items = [t.strip() for t in (concept.emotion_tags or "").split(",") if t.strip()]
    tag_chips = ""
    tx = name_x
    for t in tag_items[:5]:
        tw = len(t) * 17 + 24
        tag_chips += (
            '<rect x="{x}" y="{y}" width="{w}" height="30" rx="15" fill="{c}" opacity="0.08"/>'
            '<text x="{cx}" y="{cy}" font-size="15" fill="{c}" text-anchor="middle" font-family="{fs}">{t}</text>'
        ).format(x=tx, y=name_y + 26, w=tw, c=color, cx=tx + tw / 2, cy=name_y + 46, fs=FONT_SANS, t=_esc(t))
        tx += tw + 10

    divider_y = name_y + 108

    # 诗句（完整折行展示）
    verse_lines = _wrap_verse_lines(clause, 10)[:6]
    verse_start_y = divider_y + 66
    verse_rows = ""
    for i, ln in enumerate(verse_lines):
        verse_rows += (
            '<text x="360" y="{y}" text-anchor="middle" font-size="38" fill="#2C2C2C" '
            'font-family="{fk}" letter-spacing="3">{t}</text>'
        ).format(y=verse_start_y + i * 52, fk=FONT_KAI, t=_esc(ln))

    # 出处
    author_text = ""
    if poetry:
        author_text = f'{poetry.dynasty} · {poetry.author} 《{poetry.title}》'
        if len(author_text) > 44:
            ts = poetry.title[:12] + "…" if len(poetry.title) > 12 else poetry.title
            author_text = f'{poetry.dynasty} · {poetry.author} 《{ts}》'
    verse_end_y = verse_start_y + max(0, len(verse_lines) - 1) * 52
    author_y = verse_end_y + 46

    # 统计
    stats_y = author_y + 44
    stat1 = f'收录 {poetry_count or 0} 首诗词'
    stat2 = f'关联 {artwork_count or 0} 幅古画'
    stat_chips = ""
    sw1 = len(stat1) * 15 + 28
    stat_chips += (
        '<rect x="64" y="{y}" width="{w}" height="34" rx="8" fill="none" stroke="{c}" stroke-opacity="0.35"/>'
        '<text x="{cx}" y="{ty}" font-size="14" fill="#6B6B6B" text-anchor="middle" font-family="{fs}">{t}</text>'
    ).format(y=stats_y, w=sw1, c=color, cx=64 + sw1 / 2, ty=stats_y + 23, fs=FONT_SANS, t=stat1)
    sw2 = len(stat2) * 15 + 28
    stat_chips += (
        '<rect x="{x}" y="{y}" width="{w}" height="34" rx="8" fill="none" stroke="{c}" stroke-opacity="0.35"/>'
        '<text x="{cx}" y="{ty}" font-size="14" fill="#6B6B6B" text-anchor="middle" font-family="{fs}">{t}</text>'
    ).format(x=64 + sw1 + 14, y=stats_y, w=sw2, c=color, cx=64 + sw1 + 14 + sw2 / 2, ty=stats_y + 23, fs=FONT_SANS, t=stat2)

    # 底部
    card_h = stats_y + 92
    brand_y = card_h - 28
    brand = (
        '<text x="64" y="{y}" font-size="12" fill="#9A9A9A" font-family="{fs}">诗象志 · 一字藏万象，一诗见千年</text>'
    ).format(y=brand_y, fs=FONT_SANS)
    seal_y = card_h - 74
    seal = (
        '<rect x="608" y="{y}" width="46" height="46" rx="5" fill="#9B2C1F" opacity="0.92"/>'
        '<text x="631" y="{ty}" font-size="20" fill="#F5F1E8" text-anchor="middle" font-family="{fk}">诗象</text>'
    ).format(y=seal_y, ty=seal_y + 31, fk=FONT_KAI)
    qr_block = '<g id="qr-placeholder" transform="translate(586, 300) scale(0.85)"></g>' if not qr_svg_inline else qr_svg_inline

    return f'''<!-- share_card_v3 --><svg xmlns="http://www.w3.org/2000/svg" width="720" height="{card_h}" viewBox="0 0 720 {card_h}">
  <rect width="720" height="{card_h}" fill="#F5F1E8"/>
  <rect width="720" height="{card_h}" fill="url(#wash)" opacity="0.7"/>
  <defs>
    <radialGradient id="wash" cx="18%" cy="16%" r="80%">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.14"/>
      <stop offset="60%" stop-color="{color}" stop-opacity="0.03"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect x="12" y="12" width="696" height="{card_h - 24}" fill="none" stroke="{color}" stroke-width="2" opacity="0.42"/>
  <rect x="18" y="18" width="684" height="{card_h - 36}" fill="none" stroke="{color}" stroke-width="0.75" opacity="0.22"/>

  <rect x="40" y="{name_y - 66}" width="6" height="58" fill="{color}" rx="3"/>
  <text x="{name_x}" y="{name_y}" font-size="{name_size}" fill="{color}" font-weight="bold" font-family="{FONT_KAI}">{_esc(name)}</text>
  <text x="{name_x + name_size * name_len + 26}" y="{name_y - 8}" font-size="14" fill="#6B6B6B" font-family="{FONT_SANS}">意象 · {_esc(concept.category_main or '')}</text>
  {tag_chips}
  <line x1="64" y1="{divider_y}" x2="656" y2="{divider_y}" stroke="{color}" stroke-width="1.2" opacity="0.28"/>
  {verse_rows}
  <text x="360" y="{author_y}" font-size="15" fill="#6B6B6B" text-anchor="middle" font-family="{FONT_SANS}">— {_esc(author_text)} —</text>
  {stat_chips}
  {brand}
  {seal}
  {qr_block}
</svg>'''


def render_exploration_card(explored: list, report: str = "", theme_count: int = 0) -> str:
    count = len(explored)
    names = " · ".join(item.get("name", "?") for item in explored[:12])
    if len(explored) > 12:
        names += f" …等{count}个"

    report_text = (report or "").replace("**", "").replace("###", "").replace("##", "").replace("__", "")[:200]
    color = "#B5352C"

    report_lines = _wrap_verse_lines(report_text, 26)[:6]
    report_rows = ""
    for i, ln in enumerate(report_lines):
        report_rows += '<tspan x="56" dy="{dy}">{t}</tspan>'.format(dy=0 if i == 0 else 24, t=_esc(ln))

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

  <line x1="160" y1="140" x2="560" y2="140" stroke="{color}" stroke-width="1" opacity="0.4"/>

  <text x="56" y="178" font-size="15" fill="#6B6B6B" font-family="{FONT_SANS}">
    <tspan x="56" dy="0">{_esc(names)}</tspan>
  </text>

  <text x="56" y="240" font-size="14" fill="#4A4A4A" font-family="{FONT_SANS}">
    <tspan x="56" dy="0" font-weight="bold" fill="{color}">AI 探索报告</tspan>
  </text>
  <text x="56" y="260" font-size="13" fill="#2C2C2C" font-family="{FONT_SANS}">
    {report_rows}
  </text>

  <text x="56" y="410" font-size="12" fill="#9A9A9A" font-family="{FONT_SANS}">诗象志 · 一字藏万象，一诗见千年</text>

  <rect x="590" y="380" width="44" height="44" rx="4" fill="#9B2C1F" opacity="0.9"/>
  <text x="612" y="410" font-size="20" fill="#F5F1E8" text-anchor="middle" font-family="{FONT_KAI}">诗象</text>
</svg>'''
