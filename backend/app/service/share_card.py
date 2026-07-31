# -*- coding: utf-8 -*-
"""意象分享卡片渲染（服务端 SVG）+ QR 码"""
import io
import re
import qrcode
import qrcode.image.svg


def _make_qrcode_svg(url: str, size: int = 80) -> str:
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=10, border=1)
    buf = io.BytesIO()
    img.save(buf)
    raw = buf.getvalue().decode("utf-8")
    # Strip <?xml?> declaration and </svg> closing tag
    raw = re.sub(r'<\?xml[^?]*\?>', '', raw)
    raw = re.sub(r'</svg>', '', raw)
    raw = re.sub(r'<svg[^>]*>', f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">', raw, count=1)
    return raw


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """按 max_chars 宽度折行"""
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    if text:
        lines.append(text)
    return lines


def render_share_card(concept, clause: str, poetry, poetry_count: int = 0, artwork_count: int = 0, qr_svg_inline: str = "") -> str:
    color = concept.theme_color or "#2B4C7E"
    tags = (concept.emotion_tags or "").replace(",", " · ")
    name = concept.name or "?"
    name_len = len(name)

    name_size = 80 if name_len <= 2 else 60 if name_len <= 3 else 48
    name_y = 120 if name_len <= 3 else 110
    tag_lines = _wrap_text(tags, 28)

    parts = [p for p in re.split(r"[，。！？；、：]", clause) if p][:3]
    parts = [p[:5] for p in parts]
    col_text = ""
    for i, part in enumerate(parts):
        x = 480 - i * 52
        tspans = "".join(f'<tspan x="{x}" dy="{0 if j == 0 else 40}">{ch}</tspan>' for j, ch in enumerate(part))
        col_text += f'<text y="158" font-size="32" fill="#2C2C2C" font-family="\'Kaiti SC\',\'STKaiti\',\'KaiTi\',\'SimSun\',serif">{tspans}</text>'

    info_base_y = 390
    author_line = ""
    if poetry:
        author_text = f'{poetry.dynasty} · {poetry.author} 《{poetry.title}》'
        if len(author_text) > 40:
            ts = poetry.title[:12] + "…" if len(poetry.title) > 12 else poetry.title
            author_text = f'{poetry.dynasty} · {poetry.author} 《{ts}》'
        author_line = f'<text x="56" y="{info_base_y}" font-size="15" fill="#6B6B6B" font-family="\'PingFang SC\',\'Microsoft YaHei\',sans-serif">{author_text}</text>'

    count_line = f'<text x="56" y="{info_base_y + 28}" font-size="13" fill="#9A9A9A" font-family="\'PingFang SC\',\'Microsoft YaHei\',sans-serif">收录 {poetry_count or 0} 首诗词 · 关联 {artwork_count or 0} 幅古画</text>'

    brand_y = info_base_y + 58
    brand = f'<text x="56" y="{brand_y}" font-size="12" fill="#9A9A9A" font-family="\'PingFang SC\',\'Microsoft YaHei\',sans-serif">诗象志 · 一字藏万象，一诗见千年</text>'
    card_h = brand_y + 50

    seal_y = brand_y - 30
    seal = f'<rect x="600" y="{seal_y}" width="44" height="44" rx="4" fill="#9B2C1F" opacity="0.9"/><text x="622" y="{seal_y + 30}" font-size="20" fill="#F5F1E8" text-anchor="middle" font-family="\'Kaiti SC\',\'STKaiti\',\'KaiTi\',serif">诗象</text>'

    # QR placeholder: replaced by frontend with clean QR code
    qr_block = '<g id="qr-placeholder" transform="translate(56, 370) scale(0.85)"></g>'

    tag_rows = ""
    for i, line in enumerate(tag_lines):
        tag_rows += f'<text x="58" y="{180 + i * 22}" font-size="16" fill="#6B6B6B" font-family="\'PingFang SC\',\'Microsoft YaHei\',sans-serif">{line}</text>'
    divider_y = 198 + (len(tag_lines) - 1) * 22

    return f'''<!-- share_card_v2 --><svg xmlns="http://www.w3.org/2000/svg" width="720" height="{card_h}" viewBox="0 0 720 {card_h}">
  <rect width="720" height="{card_h}" fill="#F5F1E8"/>
  <rect x="12" y="12" width="696" height="{card_h - 24}" fill="none" stroke="{color}" stroke-width="2" opacity="0.4"/>
  <rect x="18" y="18" width="684" height="{card_h - 36}" fill="none" stroke="{color}" stroke-width="0.75" opacity="0.25"/>

  <text x="56" y="{name_y}" font-size="{name_size}" fill="{color}" font-family="'Kaiti SC','STKaiti','KaiTi','SimSun',serif">{name}</text>
  {tag_rows}
  <line x1="56" y1="{divider_y}" x2="240" y2="{divider_y}" stroke="{color}" stroke-width="1.2" opacity="0.5"/>
  {col_text}
  {author_line}
  {count_line}
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

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="440" viewBox="0 0 720 440">
  <rect width="720" height="440" fill="#F5F1E8"/>
  <rect x="12" y="12" width="696" height="416" fill="none" stroke="{color}" stroke-width="2" opacity="0.4"/>
  <rect x="18" y="18" width="684" height="404" fill="none" stroke="{color}" stroke-width="0.75" opacity="0.25"/>

  <text x="360" y="70" font-size="36" fill="{color}" text-anchor="middle"
   font-family="'Kaiti SC','STKaiti','KaiTi','SimSun',serif">我的意象地图</text>

  <text x="360" y="120" font-size="20" fill="#2C2C2C" text-anchor="middle"
   font-family="'PingFang SC','Microsoft YaHei',sans-serif">
   已探索 <tspan fill="{color}" font-weight="bold">{count}</tspan> 个意象
   · 跨越 <tspan fill="{color}" font-weight="bold">{theme_count}</tspan> 个主题族
  </text>

  <line x1="160" y1="140" x2="560" y2="140" stroke="{color}" stroke-width="1" opacity="0.4"/>

  <text x="56" y="180" font-size="15" fill="#6B6B6B"
   font-family="'PingFang SC','Microsoft YaHei',sans-serif">
    <tspan x="56" dy="0">{names}</tspan>
  </text>

  <text x="56" y="240" font-size="14" fill="#4A4A4A"
   font-family="'PingFang SC','Microsoft YaHei',sans-serif">
    <tspan x="56" dy="0" font-weight="bold" fill="{color}">AI 探索报告</tspan>
  </text>
  <foreignObject x="56" y="260" width="608" height="120">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;font-size:13px;color:#2C2C2C;line-height:1.7;width:608px;overflow:hidden;">
      {report_text}
    </div>
  </foreignObject>

  <text x="56" y="410" font-size="12" fill="#9A9A9A"
   font-family="'PingFang SC','Microsoft YaHei',sans-serif">诗象志 · 一字藏万象，一诗见千年</text>

  <rect x="590" y="380" width="44" height="44" rx="4" fill="#9B2C1F" opacity="0.9"/>
  <text x="612" y="410" font-size="20" fill="#F5F1E8" text-anchor="middle"
   font-family="'Kaiti SC','STKaiti','KaiTi',serif">诗象</text>
</svg>'''
