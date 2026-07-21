# -*- coding: utf-8 -*-
"""意象分享卡片渲染（服务端 SVG，零依赖）"""


def render_share_card(concept, clause: str, poetry) -> str:
    color = concept.theme_color
    tags = concept.emotion_tags.replace(",", " · ")
    author_line = f"{poetry.dynasty} · {poetry.author} 《{poetry.title}》" if poetry else ""
    # 名句竖排：按句读（逗号/句号）分列，从右向左，每列一句
    import re
    parts = [p for p in re.split(r"[，。！？；、：]", clause) if p][:3]
    col_text = ""
    for i, part in enumerate(parts):
        x = 440 - i * 58
        tspans = "".join(
            f'<tspan x="{x}" dy="{0 if j == 0 else 46}">{ch}</tspan>' for j, ch in enumerate(part[:9])
        )
        col_text += f'<text y="118" font-size="38" fill="#2C2C2C" font-family="\'Kaiti SC\',\'STKaiti\',\'KaiTi\',\'SimSun\',serif">{tspans}</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400">
  <rect width="640" height="400" fill="#F5F1E8"/>
  <rect x="10" y="10" width="620" height="380" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.5"/>
  <rect x="16" y="16" width="608" height="368" fill="none" stroke="{color}" stroke-width="0.75" opacity="0.35"/>
  <text x="56" y="150" font-size="92" fill="{color}" font-family="'Kaiti SC','STKaiti','KaiTi','SimSun',serif">{concept.name}</text>
  <text x="58" y="196" font-size="17" fill="#6B6B6B" font-family="'PingFang SC','Microsoft YaHei',sans-serif">{tags}</text>
  <line x1="56" y1="216" x2="220" y2="216" stroke="{color}" stroke-width="1" opacity="0.6"/>
  {col_text}
  <text x="56" y="330" font-size="15" fill="#6B6B6B" font-family="'PingFang SC','Microsoft YaHei',sans-serif">{author_line}</text>
  <text x="56" y="360" font-size="13" fill="#9A9A9A" font-family="'PingFang SC','Microsoft YaHei',sans-serif">诗象志 · 一字藏万象，一诗见千年</text>
  <rect x="560" y="316" width="44" height="44" rx="4" fill="#9B2C1F" opacity="0.9"/>
  <text x="582" y="346" font-size="18" fill="#F5F1E8" text-anchor="middle" font-family="'Kaiti SC','STKaiti','KaiTi',serif">诗象</text>
</svg>'''
