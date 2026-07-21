# -*- coding: utf-8 -*-
"""古画占位图生成器：为每幅古画生成国风水墨风格 SVG

设计思路：
- 宣纸底色 + 淡墨远山 + 月/日主题意象 + 竖排画题 + 朱红印章
- 保证在无外网环境下古画展厅依然完整美观；后续可用真实图片替换 image_url
"""
import re
from pathlib import Path

# 按意象定制的配色：月=石青夜色，夕阳=赭石墨色，青绿=山水通用（新增意象古画的默认主题）
THEMES = {
    "月": {
        "sky_top": "#1D3450", "sky_bottom": "#3D5A80",
        "body": "#F2ECCF", "body_glow": "#FBF6DF",
        "mountain_back": "#2B4C7E", "mountain_front": "#16283F",
        "ink": "#0F1E33", "accent": "#8FA6C4",
    },
    "夕阳": {
        "sky_top": "#7A3B2E", "sky_bottom": "#D9A05B",
        "body": "#E8873A", "body_glow": "#F5C396",
        "mountain_back": "#6E4A3A", "mountain_front": "#3A2A24",
        "ink": "#2E1F1A", "accent": "#C97C4A",
    },
    "青绿": {
        "sky_top": "#DCE8DC", "sky_bottom": "#A8C4B0",
        "body": "#F5F1E8", "body_glow": "#F5F1E8",
        "mountain_back": "#5B7C5F", "mountain_front": "#33503A",
        "ink": "#22332A", "accent": "#7FA085",
    },
}


def _detect_theme(name: str, description: str, explicit: str = "") -> str:
    if explicit in THEMES:
        return explicit
    text = name + description
    if re.search(r"夕|落|霞|暮|残阳|斜", text):
        return "夕阳"
    if re.search(r"月|夜|霜|蟾|桂魄|冰轮", text):
        return "月"
    return "青绿"


def make_svg(theme_name: str, title: str, artist: str, dynasty: str) -> str:
    t = THEMES[theme_name]
    # 天体位置与光芒（青绿山水主题不画天体）
    cx, cy, r = 190, 118, 42
    rays = ""
    if theme_name == "夕阳":
        import math
        for i in range(12):
            ang = math.pi * 2 * i / 12
            x1 = cx + (r + 8) * math.cos(ang); y1 = cy + (r + 8) * math.sin(ang)
            x2 = cx + (r + 20) * math.cos(ang); y2 = cy + (r + 20) * math.sin(ang)
            rays += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t["body_glow"]}" stroke-width="2.5" opacity="0.55" stroke-linecap="round"/>'
    # 月面环形山纹理
    craters = ""
    if theme_name == "月":
        acc = t["accent"]
        craters = (
            f'<circle cx="178" cy="106" r="7" fill="{acc}" opacity="0.25"/>'
            f'<circle cx="202" cy="130" r="5" fill="{acc}" opacity="0.2"/>'
        )
    # 天体（月/日）
    body = ""
    if theme_name in ("月", "夕阳"):
        body = (
            f'<circle cx="{cx}" cy="{cy}" r="{r * 2.4}" fill="url(#glow)"/>'
            + rays
            + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{t["body"]}"/>'
            + craters
        )
    # 竖排画题（右起）：逐字换行
    title_chars = "".join(f'<tspan x="332" dy="{0 if i == 0 else 30}">{ch}</tspan>' for i, ch in enumerate(title[:8]))
    meta = f"{dynasty}·{artist}"
    text_fill = "#2C2C2C" if theme_name == "青绿" else "#F5F1E8"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t["sky_top"]}"/><stop offset="1" stop-color="{t["sky_bottom"]}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{t["body_glow"]}" stop-opacity="0.9"/><stop offset="1" stop-color="{t["body_glow"]}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="400" height="300" fill="url(#sky)"/>
  <rect width="400" height="300" fill="{t["ink"]}" opacity="0.06"/>
  {body}
  <path d="M0 218 Q70 168 150 206 T310 196 Q360 184 400 202 L400 300 L0 300 Z" fill="{t["mountain_back"]}" opacity="0.75"/>
  <path d="M0 252 Q90 212 190 244 T400 236 L400 300 L0 300 Z" fill="{t["mountain_front"]}" opacity="0.9"/>
  <path d="M0 284 Q120 268 230 282 T400 276 L400 300 L0 300 Z" fill="{t["ink"]}" opacity="0.85"/>
  <text font-family="'Kaiti SC','STKaiti','KaiTi','SimSun',serif" font-size="24" fill="{text_fill}" opacity="0.92">
    {title_chars}
  </text>
  <text x="332" y="{34 + len(title[:8]) * 30 + 8}" font-family="'Kaiti SC','STKaiti','KaiTi',serif" font-size="11" fill="{text_fill}" opacity="0.7" text-anchor="middle">{meta}</text>
  <rect x="308" y="236" width="34" height="34" rx="3" fill="#9B2C1F" opacity="0.88"/>
  <text x="325" y="259" font-family="'Kaiti SC','STKaiti','KaiTi',serif" font-size="15" fill="#F5F1E8" text-anchor="middle">诗象</text>
</svg>'''


def _next_index(out_dir: Path) -> int:
    """扫描目录中已有的 artwork_XX.svg，返回下一个可用编号"""
    max_i = 0
    for f in out_dir.glob("artwork_*.svg"):
        m = re.match(r"artwork_(\d+)\.svg", f.name)
        if m:
            max_i = max(max_i, int(m.group(1)))
    return max_i + 1


def ensure_artwork_svgs(artworks: list[dict], out_dir: Path) -> list[str]:
    """为每幅古画生成 SVG（编号在已有文件后续接），返回文件名列表（与入参顺序一致）"""
    out_dir.mkdir(parents=True, exist_ok=True)
    start = _next_index(out_dir)
    files = []
    for i, a in enumerate(artworks):
        theme = _detect_theme(a["name"], a.get("description", ""), a.get("svg_theme", ""))
        fname = f"artwork_{start + i:02d}.svg"
        (out_dir / fname).write_text(make_svg(theme, a["name"], a.get("artist", "佚名"), a.get("dynasty", "")), encoding="utf-8")
        files.append(fname)
    return files
