"""소분류 화면 공통 조각 — 한 소분류 = 한 화면.

화면 순서: 결론 한 문장(lead) → KPI 최대 4개(kpis) → 주 차트 + 보조 차트(card · chart) → 「이 화면에서 보는 것」 + 출처(see)
→ 아래 「자세히 보기」(more) → 다음 대분류 링크(next_link). 화면 파일은 이 함수들만 불러 쓰고, 문구는 파일 맨 위 상수에 둔다.
"""
from __future__ import annotations

import runpy
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from kdesign import TEXT, hbar_key, kpi, style_fig  # noqa: F401  (kpi 는 화면 파일이 여기서 가져다 쓴다)
from menu import NEXT, split

VIZ = Path(__file__).resolve().parents[1] / "datacenter_viz.py"   # 상세 조회 도구(dashboard/datacenter_viz.py)
PLOT_CFG = {"displaylogo": False, "modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "autoScale2d"]}

CSS = """<style>
/* 결론 한 문장(두괄식) — 화면 맨 위, 가장 크게 */
.pg-lead{margin:2px 0 4px;padding:18px 22px;background:#f5f8fe;border-left:5px solid #1d4ed8;border-radius:0 10px 10px 0}
.pg-lead p{margin:0;font-size:22px;font-weight:800;letter-spacing:-.6px;line-height:1.45;color:#0b1f4d}
.pg-lead p .key{display:inline;font-size:inherit;font-weight:inherit;color:#1d4ed8}
.pg-lead > span{display:block;margin-top:6px;font-size:13.5px;color:#5b6b88}
/* 소분류 제목 줄 — 아래 검은 줄 없음 */
.sub-h{display:flex;align-items:baseline;gap:14px;padding-bottom:4px;margin-bottom:6px}
.sub-h h2{margin:0;padding:0;font-size:27px;font-weight:800;letter-spacing:-.7px;color:#101a33}
.sub-h p{margin:0;font-size:15px;color:#5b6b88}
/* KPI 칸 수를 화면마다 — --n 칸 */
.kpis.pk{grid-template-columns:repeat(var(--n),minmax(0,1fr))} .kpis.pk > .kpi{grid-column:auto!important}
/* 카드가 적은 화면 — 카드 폭을 --w 칸짜리 화면과 같게 하고 가운데로 모은다 */
.kpis.pk.fit{grid-template-columns:repeat(var(--n),calc((100% - (var(--w) - 1)*20px)/var(--w)));justify-content:center}
@container (max-width:620px){.kpis.pk,.kpis.pk.fit{grid-template-columns:repeat(2,minmax(0,1fr))}}
/* 이 화면에서 보는 것 + 출처(한 줄) */
.see{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;padding:11px 16px;border:1px solid #dde5f2;border-radius:10px;
  background:#fff;font-size:14px;color:#33415c}
.see b{font-size:13px;font-weight:800;color:#1d4ed8;letter-spacing:.2px}
.see .src{margin-left:auto;font-size:12.5px;color:#7a879e}
/* 한 줄 「읽는 법」 */
.read1{font-size:13.5px;color:#44567a;padding:2px 2px 0}
.read1::before{content:"읽는 법 · ";font-weight:800;color:#1d4ed8}
/* 배지 */
.bdg{display:inline-block;font-size:11.5px;font-weight:700;padding:2px 8px;border-radius:20px;margin:1px 3px 1px 0;white-space:nowrap}
.bdg.fam{background:#eaf1ff;color:#1d4ed8} .bdg.rule{background:#effaf5;color:#0f7a55} .bdg.warn{background:#fff4e5;color:#9a5b00}
.bdg.appx{background:#fff4e5;color:#9a5b00;font-size:13px;padding:4px 12px}
/* 표 */
.pt{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
.pt th{font-size:12.5px;font-weight:700;color:#5a6b8c;background:#f3f6fc;padding:9px 8px;text-align:center;border-bottom:1px solid #dde5f2;white-space:nowrap}
/* 접이식 칸(자세히 보기) 안의 표 · 데이터 출처 표 · 전자부품 품목군 현황표 — 머리 줄은 남색 바탕 · 흰 글씨(상세 조회 표와 같은 색) */
[data-testid="stExpander"] .pt th,.st-key-card_src .pt th,.st-key-card_tbl .pt th{background:#1b2f66;color:#fff;border-bottom-color:#33488a}
.pt td{padding:9px 8px;border-bottom:1px solid #eef2f9;color:#16233f;text-align:center;white-space:nowrap}
.pt td.l{text-align:left;white-space:normal}
.pt td.nm b{display:block;font-weight:800} .pt td.nm em{font-style:normal;font-size:12px;color:#7a879e}
.pt tr:hover td{background:#f7faff}
.pt .cdot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:0}
.pt .lvb{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12.5px;font-weight:600;white-space:nowrap}
/* 점유율 막대(점선 = 50%) */
.sbar{display:flex;align-items:center;gap:8px;min-width:130px}
.sbar i{position:relative;flex:1;height:8px;background:#eef2f9;border-radius:4px}
.sbar i b{position:absolute;left:0;top:0;bottom:0;border-radius:4px}
.sbar i::after{content:"";position:absolute;left:50%;top:-3px;bottom:-3px;border-left:1.5px dashed #94a3b8}
.sbar span{font-variant-numeric:tabular-nums;font-weight:700;min-width:46px;text-align:right}
/* 다음 대분류 링크 */
.st-key-next [data-testid="stPageLink"] a{justify-content:flex-end;background:#f3f6fb;border-radius:10px;padding:14px 18px}
.st-key-next [data-testid="stPageLink"] a p{font-size:16px!important;font-weight:800;color:#1d4ed8!important}
</style>"""


def inject() -> None:
    st.html(CSS)


def lead(text: str, sub: str = "") -> None:
    """결론 한 문장 — 강조 구절은 <span class="key">…</span>."""
    st.html(f'<div class="pg-lead"><p>{text}</p>' + (f"<span>{sub}</span>" if sub else "") + "</div>")


def kpis(cards: list[str], width_of: int | None = None) -> None:
    """KPI 카드 한 줄. width_of = 카드 폭을 그 칸 수짜리 화면과 같게(카드가 적어 가로로 너무 길어질 때) — 가운데로 모은다."""
    fit = width_of and width_of > len(cards)
    st.html(f'<div class="kpis pk{" fit" if fit else ""}" style="--n:{len(cards)}' + (f";--w:{width_of}" if fit else "") + '">'
            + "".join(cards) + "</div>")


def card(key: str):
    return st.container(border=True, key=f"card_{key}")


def title(text: str, sub: str = "") -> None:
    """카드 제목(결론형) + 부제(단위 · 기간 · 기준 · 색의 뜻 — 무엇을 보여 주는지)."""
    st.html(f'<div class="h"><span>{text}</span>' + (f'<span class="sub">{sub}</span>' if sub else "") + "</div>")


def caption(text: str) -> None:
    """차트 아래 작은 글씨 설명 — 제목 자리에 있던 결론 문장을 옮겨 둔다(static/base.css .caption)."""
    st.html(f'<div class="caption">{text}</div>')


def chart(fig: go.Figure, key: str, height: int | None = None) -> None:
    hb = hbar_key(fig, key)                       # 가로 막대는 표식 칸으로 감싼다 — 등장 연출이 왼쪽에서 오른쪽으로
    if hb:
        with st.container(key=hb):
            st.plotly_chart(style_fig(fig, height), width="stretch", theme=None, key=key, config=PLOT_CFG)
    else:
        st.plotly_chart(style_fig(fig, height), width="stretch", theme=None, key=key, config=PLOT_CFG)


def read1(text: str) -> None:
    st.html(f'<div class="read1">{text}</div>')


def see(what: str, source: str) -> None:
    st.html(f'<div class="see"><b>이 화면에서 보는 것</b><span>{what}</span><span class="src">출처: {source}</span></div>')


RING_CSS = """<style>
/* 고리 차트 — 칸마다 누를 수 있다(커서 = 손 모양 · 올리면 색이 진해진다). 오른쪽 위 안내 딱지가 까딱인다 */
.st-key-CARD{position:relative}
.st-key-CARD .sunburstlayer g.slice{cursor:pointer}
.st-key-CARD .sunburstlayer g.slice path{transition:filter .15s}
.st-key-CARD .sunburstlayer g.slice:hover path{filter:brightness(1.06) saturate(1.25)}
.st-key-CARD [data-testid="stElementContainer"]:has(.ring-hint){position:absolute;right:16px;top:68px;width:auto!important;z-index:2;pointer-events:none}
.ring-hint{display:inline-flex;align-items:center;gap:5px;padding:5px 11px 5px 8px;border-radius:999px;background:#eef4ff;border:1px solid #c9d9f8;
  font-size:12.5px;font-weight:700;color:#1d4ed8;animation:ringNudge 1.8s ease-in-out infinite}
.ring-hint .ms{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;font-size:17px;line-height:1;
  animation:ringTap 1.8s ease-in-out infinite}
@keyframes ringNudge{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
@keyframes ringTap{0%,55%,100%{transform:scale(1)}70%{transform:scale(.8)}85%{transform:scale(1.08)}}
.st-key-CARD_ringjs,[data-testid="stLayoutWrapper"]:has(> .st-key-CARD_ringjs){display:none!important}
@media (prefers-reduced-motion:reduce){.ring-hint,.ring-hint .ms{animation:none!important}}
</style>"""
RING_JS = Path(__file__).resolve().parents[1] / "static" / "ring_click.js"


def ring_hint(card: str, text: str = "칸을 눌러 펼쳐 보세요") -> None:
    """고리 차트 카드(card = card_○○ 키) 안에서 부른다 — 바깥 칸도 눌리게 하고(static/ring_click.js),
    오른쪽 위 안내 딱지로 누르도록 이끈다."""
    st.html(RING_CSS.replace("CARD", card) + f'<div class="ring-hint"><span class="ms">touch_app</span>{text}</div>')
    with st.container(key=f"{card}_ringjs"):
        components.html("<script>" + RING_JS.read_text(encoding="utf-8").replace("__CARD__", card) + "</script>", height=0)


def share_bar(pct: float, color: str = "#2b6ef6") -> str:
    """표 안 점유율 막대(%) — 점선 = 50%."""
    return f'<div class="sbar"><i><b style="width:{min(pct, 100):.1f}%;background:{color}"></b></i><span>{pct:.1f}%</span></div>'


def more(label: str = "자세히 보기"):
    return st.expander(label)


def next_link(cur: str) -> None:
    """이야기 연결 — 상세 조회 앞 마지막 소분류 아래에 다음 대분류로(menu.NEXT)."""
    target = NEXT.get(cur)
    if not target:
        return
    if target == "home":
        label = "처음으로: 홈 결론 보기"
    else:
        cat, _ = split(target)
        label = f"다음: {cat.no} {cat.name} — {cat.question}"
    with st.container(key="next"):
        st.page_link(pages()[target], label=label, icon=":material/arrow_forward:", width="stretch")


def hbar(rows: list[tuple[str, float, str]], unit: str = "", height: int = 300) -> go.Figure:
    """가로 막대(값 라벨) — rows = [(이름, 값, 색)] 위에서부터."""
    rows = list(reversed(rows))
    fig = go.Figure(go.Bar(x=[r[1] for r in rows], y=[r[0] for r in rows], orientation="h",
                           marker=dict(color=[r[2] for r in rows]), text=[f"{r[1]:,}" for r in rows],
                           textposition="outside", cliponaxis=False, textfont=dict(color=TEXT),
                           hovertemplate="%{y}<br>%{x:,}" + f" {unit}<extra></extra>"))
    fig.update_layout(height=height, showlegend=False, margin=dict(l=10, r=48, t=10, b=8))
    return fig


def donut(rows: list[tuple[str, float, str]], center: str, height: int = 320) -> go.Figure:
    fig = go.Figure(go.Pie(labels=[r[0] for r in rows], values=[r[1] for r in rows], hole=.58, sort=False,
                           marker=dict(colors=[r[2] for r in rows], line=dict(color="#fff", width=2)),
                           textinfo="percent", hovertemplate="%{label}<br>%{value:,} (%{percent})<extra></extra>"))
    fig.update_layout(height=height, showlegend=True, legend=dict(orientation="v", x=1, y=.5),
                      annotations=[dict(text=center, showarrow=False, font=dict(size=17, color=TEXT))],
                      margin=dict(l=8, r=8, t=8, b=8))
    return fig


def detail(kind: str, sub: str) -> None:
    """상세 조회 — 「데이터 시각화」 도구(dashboard/datacenter_viz.py)를 자료 유형 하나로 고정해 그린다.
    runpy 로 매 실행 새로 돌린다(import 하면 프로세스에 한 번만 실행돼 화면이 그려지지 않는다)."""
    lead(f'조건을 골라 <span class="key">{kind}</span> 자료를 직접 보고 내려받습니다', sub)
    runpy.run_path(str(VIZ), init_globals={"FIXED_TYPE": kind}, run_name="datacenter_viz")
