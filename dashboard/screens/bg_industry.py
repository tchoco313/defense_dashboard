"""④ 4-2 국내 생산 기반 — 국내 생산 기반은 어떤가.

값: 방산업체 분야별 평균가동률(KOSIS, rds.utilization) · 전자 · 반도체 광공업생산지수 연평균(KOSIS 원지수, rds.prod_index) ·
분야별 방산업체 지정 수(방위사업청, rds.companies). 가동률 · 생산지수는 생산 능력이나 국산화 수준을 뜻하지 않는다.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R
from kdesign import SERIES

SEE = "방산 분야별 가동률과 전자 · 반도체 광공업생산지수 추이"
SOURCE = "KOSIS · 방산업체 평균가동률 · 광공업생산지수 / 방위사업청 · 방산업체 지정 현황"
HIGHLIGHT = "통신전자"
GRAY = ["#c3cede", "#9fb0c8", "#b8c4d6", "#aab7cb", "#cfd8e6", "#b1bdd0", "#a3b1c7"]

u = R.utilization()
hl = u[(u["sector"] == HIGHLIGHT) & (u["is_avg"] == 0)]
avg = u[u["is_avg"] == 1]
last = hl.iloc[-1] if not hl.empty else None
if last is not None:
    a_last = avg.loc[avg["year"] == last["year"], "pct"]
    P.lead(f'방산 통신전자 분야 가동률은 <span class="key">{int(last["year"])}년 {last["pct"]:.1f}%</span>다'
           + (f" (분야 평균 {float(a_last.iloc[0]):.1f}%)" if not a_last.empty else ""),
           "% · 가동률 · 생산지수는 생산 능력이나 국산화 수준을 뜻하지 않습니다")

a, b = st.columns(2, gap="medium")
with a, P.card("util"):
    P.title("분야별 방산 가동률 — 통신전자 강조", f"% · 연도별 {int(u['year'].min())}~{int(u['year'].max())} · 굵은 선 = 통신전자 · 점선 = 분야 평균")
    fig = go.Figure()
    others = [s for s in u.loc[u["is_avg"] == 0, "sector"].unique() if s != HIGHLIGHT]
    for i, s in enumerate(others):
        d = u[u["sector"] == s]
        fig.add_trace(go.Scatter(x=d["year"], y=d["pct"], name=s, mode="lines", line=dict(width=1.6, color=GRAY[i % len(GRAY)]),
                                 hovertemplate=f"{s} · %{{x}}년 %{{y:.1f}}%<extra></extra>"))
    if not avg.empty:
        fig.add_trace(go.Scatter(x=avg["year"], y=avg["pct"], name="분야 평균", mode="lines", line=dict(width=2, color="#64748b", dash="dot"),
                                 hovertemplate="분야 평균 · %{x}년 %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=hl["year"], y=hl["pct"], name=HIGHLIGHT, mode="lines+markers", line=dict(width=4, color="#2b6ef6"),
                             marker=dict(size=7), hovertemplate=f"{HIGHLIGHT} · %{{x}}년 %{{y:.1f}}%<extra></extra>"))
    fig.update_layout(height=320)
    fig.update_xaxes(dtick=1)
    P.chart(fig, "p42_util")
with b, P.card("prod"):
    pi = R.prod_index()
    P.title("전자 · 반도체 광공업생산지수", f"2020 = 100 · 연평균(원지수) · {int(pi['year'].min())}~{int(pi['year'].max())} · 12개월이 다 있는 해만")
    fig = go.Figure()
    for (code, name), color in zip(R.PROD_NAME.items(), (SERIES[3], SERIES[2], SERIES[5])):
        d = pi[pi["code"] == code]
        fig.add_trace(go.Scatter(x=d["year"], y=d["v"].round(1), name=f"{name}({code})", mode="lines+markers",
                                 line=dict(width=3, color=color), hovertemplate=f"{name} · %{{x}}년 %{{y:.1f}}<extra></extra>"))
    fig.add_hline(y=100, line_dash="dot", line_color="#94a3b8")
    fig.update_layout(height=320)
    fig.update_xaxes(dtick=1)
    P.chart(fig, "p42_prod")
P.see(SEE, SOURCE)

with P.more("분야별 방산업체 지정 수"):
    cp = R.companies()
    P.chart(P.hbar([(r.sector, int(r.n), "#2b6ef6" if r.sector == HIGHLIGHT else "#c3cede") for r in cp.itertuples()], "개", 320),
            "p42_comp")
    st.html(f'<div class="caption">개 · 방산업체 지정 현황 {int(cp["n"].sum())}개 업체 · 업체 주소는 생산시설 위치가 아닙니다</div>')
with P.more("해석할 때 주의"):
    st.markdown("- 가동률 = 가동 시간 기준이지 생산 능력 · 국산화 수준이 아닙니다\n- 생산지수의 최근 값은 잠정치일 수 있습니다\n"
                "- 업체 주소는 생산시설 위치가 아닙니다")
