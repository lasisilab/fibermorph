"""Lasisi Lab design system for the fibermorph Streamlit GUI.

One place for the visual identity: the injected CSS (fonts, tokens, sidebar,
buttons, cards, table, inputs) plus small HTML-builder helpers for the sidebar
brand lockup, per-view headers, and at-a-glance metric cards.

Colors, type and spacing follow the design handoff tokens exactly. Assets
(logo + dendritic "branch" mask) live in gui/assets/ and are embedded as base64
data URIs so the app stays self-contained (no static-file server needed).
"""

from __future__ import annotations

import base64
import html as _html
from functools import lru_cache
from pathlib import Path

_ASSETS = Path(__file__).resolve().parent / "assets"

# --- Palette (design tokens) -------------------------------------------------
TEAL_900 = "#023943"   # identity / headlines / hero
TEAL_800 = "#034D54"
TEAL_700 = "#05686D"   # links / functional / click
TEAL_500 = "#2D8489"
TEAL_400 = "#4FB5B5"
TEAL_200 = "#A4D2CD"
TEAL_50 = "#DCEDEB"
PINK_600 = "#A82F88"   # accent CTA
PINK_800 = "#6E1A56"   # accent hover
PINK_100 = "#F7E1ED"
INDIGO_700 = "#3A2E78"
INDIGO_50 = "#F1EDF8"
INK_700 = "#3F4251"
INK_500 = "#6B6F7E"

# Brand teals for the matplotlib histograms (replaces the default #4C72B0).
CHART_COLORS = [TEAL_500, TEAL_400, TEAL_700, INDIGO_700]


@lru_cache(maxsize=8)
def _data_uri(name: str) -> str:
    """Return a base64 data URI for an asset PNG (cached)."""
    data = (_ASSETS / name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


# Simple stroke-outline nav glyphs (from the design): an ellipse for the
# cross-section, an arc for curvature, a laptop for local, a server for remote.
# Used as CSS masks so the icon colour follows the nav item's text colour.
_NAV_ICONS = {
    "section": ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                'fill="none" stroke="#000" stroke-width="2">'
                '<ellipse cx="12" cy="12" rx="9" ry="6"/></svg>'),
    "curvature": ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                  'fill="none" stroke="#000" stroke-width="2" stroke-linecap="round">'
                  '<path d="M3 16 A 10 8 0 0 1 21 16"/></svg>'),
    "local": ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
              'fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" '
              'stroke-linejoin="round"><rect x="4" y="5" width="16" height="11" rx="1.5"/>'
              '<path d="M2 20h20"/></svg>'),
    "remote": ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
               'fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" '
               'stroke-linejoin="round"><rect x="4" y="4" width="16" height="7" rx="1.5"/>'
               '<rect x="4" y="13" width="16" height="7" rx="1.5"/>'
               '<path d="M7.5 7.5h.01M7.5 16.5h.01"/></svg>'),
}


def _svg_uri(svg: str) -> str:
    """Base64 data URI for an inline SVG (avoids URL-escaping issues in CSS)."""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


@lru_cache(maxsize=1)
def css() -> str:
    """The full <style> block to inject once at app start."""
    branch = _data_uri("pattern-branches-mask.png")
    nav_icons = "\n".join(
        f'[data-testid="stSidebar"] .st-key-nav_{k} button::before {{'
        f"-webkit-mask-image:url('{_svg_uri(svg)}'); mask-image:url('{_svg_uri(svg)}'); }}"
        for k, svg in _NAV_ICONS.items()
    )
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600&family=Mulish:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Open+Sans:wght@400;500;600;700&family=Source+Code+Pro:wght@400;500;600&display=swap');

:root {{
  --teal-900:{TEAL_900}; --teal-700:{TEAL_700}; --teal-400:{TEAL_400};
  --teal-50:{TEAL_50}; --pink-600:{PINK_600}; --indigo-700:{INDIGO_700};
  --ink-700:{INK_700}; --ink-500:{INK_500};
}}

/* ---- Base type + canvas ---- */
html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, span, div, label {{
  font-family:'Open Sans', sans-serif;
}}
[data-testid="stAppViewContainer"] {{ background:#FBFCFD; }}
[data-testid="stMain"] .block-container {{ max-width:1180px; padding-top:3.75rem; padding-bottom:4rem; }}
h1, h2, h3, h4 {{ font-family:'Mulish', sans-serif; font-weight:700; color:{TEAL_900}; }}

/* ---- Sidebar shell: teal→indigo gradient, branch motif, accent rail ---- */
[data-testid="stSidebar"] {{
  background:linear-gradient(160deg,{TEAL_900} 0%,{INDIGO_700} 118%);
  border-right:0;
}}
[data-testid="stSidebar"] > div:first-child {{ padding-top:2.6rem; position:relative; }}
[data-testid="stSidebar"]::before {{
  content:""; position:absolute; top:-2%; right:-14%; width:78%; aspect-ratio:1/1;
  -webkit-mask:url('{branch}') no-repeat top right/contain;
  mask:url('{branch}') no-repeat top right/contain;
  background-color:#fff; opacity:0.09; pointer-events:none; z-index:0;
}}
[data-testid="stSidebar"]::after {{
  content:""; position:absolute; top:0; bottom:0; right:0; width:3px;
  background:linear-gradient(180deg,{PINK_600},#DA94BC 55%,{TEAL_400}); opacity:0.85;
}}
[data-testid="stSidebar"] * {{ color:#fff; }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{ position:relative; z-index:1; }}

/* ---- Sidebar nav (buttons; active = primary, inactive = secondary) ---- */
[data-testid="stSidebar"] .stButton > button {{
  width:100%; text-align:left; justify-content:flex-start;
  font-family:'Plus Jakarta Sans', sans-serif; font-weight:600; font-size:14px;
  border:0; border-radius:10px; padding:9px 13px; margin:2px 0;
  transition:background 160ms ease;
}}
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
  background:transparent; color:rgba(255,255,255,0.66); box-shadow:none;
}}
[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {{
  background:rgba(255,255,255,0.07); color:#fff;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background:rgba(255,255,255,0.12); color:#fff; box-shadow:none;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{ background:rgba(255,255,255,0.16); }}
/* Nav glyphs: stroke SVG as a mask, tinted to the item's text colour. */
[data-testid="stSidebar"] .stButton > button::before {{
  content:""; display:inline-block; width:17px; height:17px; margin-right:11px; flex:none;
  background-color:currentColor; vertical-align:middle;
  -webkit-mask-repeat:no-repeat; mask-repeat:no-repeat;
  -webkit-mask-position:center; mask-position:center;
  -webkit-mask-size:contain; mask-size:contain;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"]::before {{ background-color:{TEAL_400}; }}
{nav_icons}
[data-testid="stSidebar"] .nav-eyebrow {{
  font-family:'Plus Jakarta Sans', sans-serif; font-size:10.5px; font-weight:600;
  letter-spacing:0.2em; text-transform:uppercase; color:rgba(255,255,255,0.45);
  padding:0 6px; margin:14px 0 8px;
}}

/* ---- Sidebar brand lockup ---- */
.fm-brand {{ display:flex; align-items:center; gap:12px; margin-bottom:8px; position:relative; z-index:1; }}
.fm-brand__badge {{ width:44px; height:44px; flex:none; background:#fff; border-radius:12px;
  display:grid; place-items:center; box-shadow:0 4px 12px rgba(0,0,0,0.2); }}
.fm-brand__badge img {{ width:30px; height:30px; object-fit:contain; }}
.fm-brand__name {{ font-family:'Mulish', sans-serif; font-weight:800; font-size:19px; line-height:1; color:#fff; }}
.fm-brand__lab {{ font-family:'Plus Jakarta Sans', sans-serif; font-size:10px; font-weight:600;
  letter-spacing:0.18em; text-transform:uppercase; color:{TEAL_200}; margin-top:5px; }}
.fm-foot {{ margin-top:18px; position:relative; z-index:1; }}
.fm-foot__status {{ font-family:'Plus Jakarta Sans', sans-serif; font-size:12px; font-weight:600; color:rgba(255,255,255,0.85); }}
.fm-foot__dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; background:{TEAL_400};
  box-shadow:0 0 0 3px rgba(79,181,181,0.25); margin-right:8px; vertical-align:middle; }}
.fm-foot__ver {{ font-family:'Source Code Pro', monospace; font-size:10.5px; color:rgba(255,255,255,0.4); margin-top:6px; }}

/* ---- Per-view header ---- */
.fm-eyebrow {{ font-family:'Plus Jakarta Sans', sans-serif; font-size:11px; font-weight:600;
  letter-spacing:0.22em; text-transform:uppercase; color:{PINK_600}; margin-bottom:8px; }}
.fm-h2 {{ font-family:'Mulish', sans-serif; font-weight:700; font-size:26px; color:{TEAL_900}; margin:0 0 6px; }}
.fm-sub {{ font-size:13.5px; line-height:1.6; color:{INK_500}; margin:0 0 6px; max-width:620px; }}
.fm-rule {{ border:0; border-top:1px solid #ECEDF1; margin:18px 0 22px; }}

/* ---- Metric cards ---- */
.fm-metrics {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:6px 0 8px; }}
.fm-card {{ background:#fff; border:1px solid #E4E7EC; border-radius:14px; padding:16px 18px; }}
.fm-card__label {{ font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:{INK_500}; }}
.fm-card__num {{ font-family:'Mulish', sans-serif; font-weight:800; font-size:30px; color:{TEAL_900}; margin-top:4px; line-height:1.1; }}
.fm-card__unit {{ font-size:14px; font-weight:600; color:#8A93A0; }}
.fm-card--hero {{ background:{TEAL_900}; color:#fff; position:relative; overflow:hidden; }}
.fm-card--hero .fm-card__label {{ color:{TEAL_200}; }}
.fm-card--hero .fm-card__num {{ color:#fff; }}
.fm-card--hero::after {{ content:""; position:absolute; top:-30%; right:-20%; width:70%; aspect-ratio:1;
  -webkit-mask:url('{branch}') no-repeat top right/contain; mask:url('{branch}') no-repeat top right/contain;
  background:#fff; opacity:0.1; }}
.fm-pill {{ font-family:'Plus Jakarta Sans', sans-serif; font-size:11px; font-weight:600;
  padding:5px 9px; border-radius:999px; display:inline-block; margin-right:6px; }}
.fm-pill--teal {{ background:{TEAL_50}; color:{TEAL_700}; }}
.fm-pill--indigo {{ background:{INDIGO_50}; color:{INDIGO_700}; }}
.fm-pill--amber {{ background:#FDF3E0; color:#C98A14; }}

/* ---- Primary / accent buttons in the main area ---- */
[data-testid="stMain"] .stButton > button[kind="primary"] {{
  background:{TEAL_900}; color:#fff; border:0; border-radius:9px; font-family:'Plus Jakarta Sans', sans-serif;
  font-weight:600; box-shadow:0 1px 2px rgba(31,35,44,0.06);
}}
[data-testid="stMain"] .stButton > button[kind="primary"]:hover {{ background:{TEAL_700}; color:#fff; }}
[data-testid="stMain"] .stDownloadButton > button {{
  background:{TEAL_50}; color:{TEAL_700}; border:0; border-radius:8px;
  font-family:'Plus Jakarta Sans', sans-serif; font-weight:600;
}}
[data-testid="stMain"] .stDownloadButton > button:hover {{ background:#CDE7E4; color:{TEAL_700}; }}

/* ---- Expander (Settings) as a card ---- */
[data-testid="stExpander"] {{ border:1px solid #E4E7EC; border-radius:14px; background:#fff; box-shadow:0 1px 2px rgba(31,35,44,0.05); }}
[data-testid="stExpander"] summary {{ font-family:'Plus Jakarta Sans', sans-serif; font-weight:600; color:{INK_700}; }}

/* ---- Dataframe header ---- */
[data-testid="stDataFrame"] thead tr th {{ background:#FAFBFC !important; color:#8A93A0 !important;
  font-family:'Plus Jakarta Sans', sans-serif; font-weight:600; text-transform:uppercase; font-size:11px; letter-spacing:0.04em; }}

/* ---- Alerts: soften info to brand mint (keep warning/error distinct) ---- */
[data-testid="stAlert"] {{ border-radius:12px; }}
[data-testid="stAlertContainer"] {{ border-radius:12px; }}
/* st.info renders with a light-blue ground; re-tint to mint teal. */
[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) {{
  background:{TEAL_50}; color:{TEAL_800};
}}
</style>
"""


def brand_html() -> str:
    """Sidebar brand lockup: logo badge + fibermorph / LASISI LAB."""
    logo = _data_uri("logo-icon.png")
    return (
        f'<div class="fm-brand"><div class="fm-brand__badge">'
        f'<img src="{logo}" alt="Lasisi Lab"></div><div>'
        f'<div class="fm-brand__name">fibermorph</div>'
        f'<div class="fm-brand__lab">Lasisi Lab</div></div></div>'
    )


def footer_html(status: str, version: str) -> str:
    """Sidebar footer: status dot + line, and a mono version line."""
    return (
        f'<div class="fm-foot"><div class="fm-foot__status">'
        f'<span class="fm-foot__dot"></span>{_html.escape(status)}</div>'
        f'<div class="fm-foot__ver">{_html.escape(version)}</div></div>'
    )


def view_header(eyebrow: str, title: str, subtitle: str) -> str:
    """Per-view header: pink eyebrow, Mulish h2, sub-copy, hairline rule."""
    return (
        f'<div class="fm-eyebrow">{_html.escape(eyebrow)}</div>'
        f'<div class="fm-h2">{_html.escape(title)}</div>'
        f'<p class="fm-sub">{_html.escape(subtitle)}</p><hr class="fm-rule">'
    )


def metric_cards(cards) -> str:
    """Render a 4-up grid of metric cards.

    Each card is a dict: {"label": str, "value": str, "unit": str|None,
    "hero": bool, "pills": [(text, kind), ...]}. `value`/`unit` are shown as a
    big number; if `pills` is given it replaces the number with pills.
    """
    cells = []
    for c in cards:
        cls = "fm-card fm-card--hero" if c.get("hero") else "fm-card"
        label = f'<div class="fm-card__label">{_html.escape(c["label"])}</div>'
        if c.get("pills"):
            pills = "".join(
                f'<span class="fm-pill fm-pill--{k}">{_html.escape(t)}</span>'
                for t, k in c["pills"]
            )
            body = f'<div style="margin-top:12px;">{pills}</div>'
        else:
            unit = (f'<span class="fm-card__unit"> {_html.escape(c["unit"])}</span>'
                    if c.get("unit") else "")
            body = f'<div class="fm-card__num">{_html.escape(str(c["value"]))}{unit}</div>'
        cells.append(f'<div class="{cls}">{label}{body}</div>')
    return f'<div class="fm-metrics">{"".join(cells)}</div>'
