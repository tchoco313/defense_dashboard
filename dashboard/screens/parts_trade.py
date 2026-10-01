"""① 1-2 수출입 현황 — 연도 · 국가별로 어떻게 바뀌었나(명세 11_cat_parts.md §3, 차트 세부 20_trade.md). 수입/수출은 토글로 같은 모양.

값: 관세청 연도 × 국가 수입 · 수출(rds.trade) — 연도 차트는 완결 연도만, 국가 구성 · 지도는 기준 연도(최근 완결 연도).
지도는 운영 앱 ① 세계 지도(kdesign.country_map)를 그대로 쓰고 토글한 흐름 하나만 보인다.
"""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R
from ui import EXP, IMP, country_map

SEE = "고른 품목군의 연도별 수입(또는 수출)액과 국가 구성"
FLOW = {"수입": "imp", "수출": "exp"}
TOP_N = 7

it = R.items()
by = R.base_year()
ys = R.full_years()
names = {"전체 13개": None} | {f"{r.short} ({r.hs6})": r.hs6 for r in it.itertuples()}
q = st.query_params.get("hs")
default = next((k for k, v in names.items() if v == q), "전체 13개")
c1, c2 = st.columns([2.2, 1], vertical_alignment="bottom")
pick = c1.selectbox("품목군", list(names), index=list(names).index(default), key="p12_hs")
flow_lb = c2.segmented_control("수입 / 수출", list(FLOW), default="수입", key="p12_flow") or "수입"
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
        P.title(f'{flow_lb}의 1위 국가는 <span class="key">{escape(sh.iloc[0]["country"])} {sh.iloc[0]["share"]:.1f}%</span>',
                f"% · {by}년 · 상위 {TOP_N}개국 + 기타")
        head, rest = sh.head(TOP_N), sh.iloc[TOP_N:]
        rows = [(r.country, round(r.share, 1), col.get(r.stat_cd, "#c3cede")) for r in head.itertuples()]
        if not rest.empty:
            rows.append((f"기타 {len(rest)}개국", round(float(rest["share"].sum()), 1), "#c3cede"))
        P.chart(P.donut(rows, f"{flow_lb}<br>국가 구성", 330), "p12_donut")
P.see(SEE, source)

with P.card("map"):
    P.title(f"국가별 {flow_lb} 비중 지도", f"억 달러 · {by}년 · 색 = 합계 대비 비중 · 상위 6개국 라벨 · 수입/수출은 위 토글")
    vals = {r.country: float(r.value) for r in sh.itertuples()}
    where = {r.country: (float(r.lat), float(r.lon)) for r in sh.itertuples() if r.lat == r.lat and r.lat is not None}
    country_map(vals if flow == "imp" else {}, vals if flow == "exp" else {}, modes=(flow,), height=440,
                unit="억 달러", where=where)
    st.html('<div class="caption">국가 좌표는 나라 대표 위치 · 수입 = 선적국, 수출 = 도착국(원산지 아님)</div>')
