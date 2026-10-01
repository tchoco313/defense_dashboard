"""① 1-2 수출입 현황 — 연도 · 국가별로 어떻게 바뀌었나(명세 11_cat_parts.md §3, 차트 세부 20_trade.md). 수입/수출은 토글로 같은 모양.

값: 관세청 연도 × 국가 수입 · 수출(rds.trade) — 연도 차트는 완결 연도만, 국가 구성 · 지도는 기준 연도(최근 완결 연도).
국가별 규모는 지구본(kdesign.supply_globe — demo/KDD_v2 「국가별 수입 규모」와 같은 블록)으로, 토글한 흐름 하나만 보인다.
"""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R
from kdesign import hover_donut, supply_globe
from ui import EXP, IMP

SEE = "고른 품목군의 연도별 수입(또는 수출)액과 국가 구성"
FLOW = {"수입": "imp", "수출": "exp"}
TOP_N = 7
GLOBE_N = 20     # 지구본에 올릴 나라 수(금액 큰 순) — 다 올리면 원 · 화살표가 겹쳐 읽히지 않는다

it = R.items()
by = R.base_year()
ys = R.full_years()
names = {"전체 13개": None} | {f"{r.short} ({r.hs6})": r.hs6 for r in it.itertuples()}
q = st.query_params.get("hs")
default = next((k for k, v in names.items() if v == q), "전체 13개")
c1, c2 = st.columns([1, 2.4], vertical_alignment="bottom")   # 선택창은 내용이 다 보일 만큼만 · 수입/수출 단추는 바로 그 옆
pick = c1.selectbox("품목군", list(names), index=list(names).index(default), key="p12_hs")
st.session_state.setdefault("p12_flow", "수입")     # 아래 지구본 카드의 단추(p12_flow_map)가 이 값을 바꾼다 — default 대신 세션 값으로 시작
flow_lb = c2.segmented_control("수입 / 수출", list(FLOW), key="p12_flow", label_visibility="collapsed") or "수입"
flow = FLOW[flow_lb]
hs = [names[pick]] if names[pick] else it["hs6"].tolist()
label = "분석 대상 13개 합계" if names[pick] is None else pick

yr = R.yearly(hs)
cur = yr[flow]
sh_imp, sh_exp = R.shares(hs, by, "imp"), R.shares(hs, by, "exp")
sh = sh_imp if flow == "imp" else sh_exp
col = R.colors(sh["stat_cd"].head(TOP_N).tolist())
source = f"관세청 · 품목별 국가별 수출입실적 · {R.customs_period()}"
v0, v1 = float(cur.iloc[0]), float(cur.iloc[-1])

P.lead(f'{escape(label)}의 {flow_lb}액은 {ys[0]}년 {v0:,.1f}억 달러에서 '
       f'<span class="key">{ys[-1]}년 {v1:,.1f}억 달러</span>로 {"늘었다" if v1 >= v0 else "줄었다"}',
       f"억 달러 · {ys[0]}~{ys[-1]} 완결 연도 · 국가 전체 {flow_lb}(민수 포함) · 국가 = 선적국(수입) · 도착국(수출)")


def top_txt(s) -> tuple[str, str]:
    return (s.iloc[0]["country"], f'{s.iloc[0]["share"]:.1f}% · {by}년') if not s.empty else ("—", f"{by}년 실적 없음")


ti, te = top_txt(sh_imp), top_txt(sh_exp)
P.kpis([P.kpi("수입액", f"{yr['imp'].iloc[-1]:,.1f}", "억 달러", f"{by}년 · 민수 포함"),
        P.kpi("수출액", f"{yr['exp'].iloc[-1]:,.1f}", "억 달러", f"{by}년 · 민수 포함"),
        P.kpi("1위 수입국", ti[0], "", ti[1]),
        P.kpi("1위 수출국", te[0], "", te[1])])

a, b = st.columns([1.5, 1], gap="medium")
with a, P.card("line"):
    P.title(f'연도별 {flow_lb}액 — {ys[-1]}년 <span class="key">{v1:,.1f}억 달러</span>', "억 달러 · 연도별 합계 · 완결 연도")
    fig = go.Figure(go.Scatter(x=list(yr.index), y=cur.round(2).tolist(), mode="lines+markers",
                               line=dict(color=IMP if flow == "imp" else EXP, width=3), marker=dict(size=7),
                               hovertemplate="%{x}년 %{y:,.1f}억 달러<extra></extra>"))
    fig.update_layout(height=330, showlegend=False)
    fig.update_xaxes(dtick=1)
    P.chart(fig, "p12_line")
with b, P.card("donut"):
    if sh.empty:
        P.title(f"{by}년 {flow_lb} 국가 구성")
        st.info(f"{by}년 {flow_lb} 실적이 없습니다(실제 0).")
    else:
        P.title(f"{flow_lb}국 비중", f"조각에 커서를 올려 보세요 · {by}년 · 상위 {TOP_N}개국 + 기타 · 단위: 억 달러")
        head, rest = sh.head(TOP_N), sh.iloc[TOP_N:]
        rows = [(r.country, round(float(r.value), 2), col.get(r.stat_cd, "#c3cede")) for r in head.itertuples()]
        if not rest.empty:
            rows.append((f"기타 {len(rest)}개국", round(float(rest["value"].sum()), 2), "#c3cede"))
        hover_donut(rows, f"{sum(v for _, v, _ in rows):,.1f}", "억 달러", value_unit="억 달러", height=330)
P.see(SEE, source)

def _flow_from_map() -> None:
    """지구본 카드의 수입/수출 단추를 누르면 위(품목군 옆) 단추도 같은 값으로."""
    st.session_state["p12_flow"] = st.session_state.get("p12_flow_map") or "수입"


with P.card("map"):
    st.session_state["p12_flow_map"] = flow_lb       # 위 단추를 눌렀을 때도 이 단추가 따라온다
    with st.container(key="map_flow"):               # 카드 오른쪽 위 ⓘ 왼쪽(자리 = see.css .st-key-map_flow)
        st.segmented_control("수입 / 수출", list(FLOW), key="p12_flow_map", label_visibility="collapsed", on_change=_flow_from_map)
    way = "대한민국으로 들어오는" if flow == "imp" else "대한민국에서 나가는"
    P.title(f"국가별 {flow_lb} 규모",
            f"억 달러 · {by}년 · 국기 원 크기 = {flow_lb}액 · 화살표 = {way} 방향 · 상위 {GLOBE_N}개국 · 지구본 ↔ 지도 전환")
    pts = [{"name": r.country, "lat": float(r.lat), "lon": float(r.lon), "value": round(float(r.value), 2),
            "color": col.get(r.stat_cd, "#8fb0ea"), "note": f"{flow_lb} 비중 {r.share:.1f}%", "code": r.stat_cd}
           for r in sh.head(GLOBE_N).itertuples() if r.lat == r.lat and r.lat is not None]
    if pts:
        supply_globe(pts, height=560, unit="억 달러", outbound=flow == "exp")
    else:
        st.info(f"{by}년 {flow_lb} 실적이 없습니다(실제 0).")
    st.html('<div class="caption">국가 좌표는 나라 대표 위치 · 수입 = 선적국, 수출 = 도착국(원산지 아님) · 원 위에 커서를 올리면 금액과 비중</div>')
