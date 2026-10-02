"""② 2-3 소요군별 — 어느 소요군이, 어느 해에 요구하나.

값: 소요군별 전자 군급 비중 = 전자 군급 행 ÷ 군급 판별 가능 행(군급 있음 · 「9999」 제외, rds.army_share),
요구연도 × 소요군 = 전자 군급 국외 조달계획 건수(rds.plan).
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R

SEE = "소요군별 국외 조달계획 중 전자 군급 비중과 요구연도별 건수"
SOURCE = "방위사업청 · 국외 조달계획(품목) · 군급분류집"

ys = R.plan_years()
YEARS = list(range(ys[0], ys[-1] + 1))
ss = st.session_state
ss.setdefault("p23_y0", YEARS[0])
ss.setdefault("p23_y1", YEARS[-1])
# 요구연도 — 상세 조회 「분석 조건 설정」과 같은 꼴(시작 ~ 끝 선택창). 시작은 끝보다 늦을 수 없고 끝은 시작보다 이를 수 없다
c0, mid, c1, _ = st.columns([.58, .13, .58, 4.31], vertical_alignment="bottom", gap="small")   # 연도 칸은 네 자리 숫자 + 화살표가 들어갈 만큼만
y0 = c0.selectbox("요구연도", [y for y in YEARS if y <= ss["p23_y1"]], key="p23_y0")
mid.html('<div class="kd-yr-tilde">~</div>')
y1 = c1.selectbox("끝 연도", [y for y in YEARS if y >= y0], key="p23_y1", label_visibility="collapsed")
sh = R.army_share(y0, y1)
if sh.empty:
    P.lead(f"요구연도 {y0}~{y1}에는 군급을 판별할 수 있는 국외 조달계획 행이 없습니다", "연도 범위를 넓혀 보세요")
else:
    top = sh.iloc[0]
    span = str(y0) if y0 == y1 else f"{y0}~{y1}"
    P.lead(f'{span}년 국외 조달계획 중 전자 군급 비중은 <span class="key">{top["army"]} {top["pct"]:.1f}%</span>로 가장 크다',
           f"요구연도 {y0}~{y1}")
    with P.card("army"):
        P.title("소요군별 전자 군급 비중", "% · 가로 100% = 그 소요군의 국외 조달계획 · 색 막대 = 전자 군급(군 58 · 59 · 60, 색 = 소요군) · 괄호 = 분모 건수")
        ylab = [f"{r.army} ({int(r.n_valid):,}건)" for r in sh.itertuples()]
        fig = go.Figure()
        fig.add_trace(go.Bar(y=ylab, x=sh["pct"].round(1), orientation="h", name="전자 군급", showlegend=False,
                             marker_color=[R.ARMY_COLOR.get(a, "#2b6ef6") for a in sh["army"]],     # 소요군마다 다른 색(아래 연도 차트와 같은 색)
                             text=[f"{v:.1f}%" for v in sh["pct"]], textposition="inside",
                             customdata=sh["n_elec"].astype(int), hovertemplate="%{y}<br>전자 군급 %{x:.1f}% (%{customdata:,}건)<extra></extra>"))
        fig.add_trace(go.Bar(y=ylab, x=(100 - sh["pct"]).round(1), orientation="h", name="그 밖의 군급", marker_color="#dae0e9",
                             hovertemplate="%{y}<br>그 밖의 군급 %{x:.1f}%<extra></extra>"))
        fig.update_layout(barmode="stack", height=60 + 44 * len(sh))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(range=[0, 100], ticksuffix="%")
        P.chart(fig, "p23_army")
P.see(SEE, SOURCE)

with P.card("year"):
    p = R.plan()
    p = p[p["year"].between(y0, y1)]
    ya = p.groupby(["year", "army"]).size().unstack(fill_value=0).reindex(range(y0, y1 + 1), fill_value=0)
    P.title(f"요구연도 × 소요군 — 전자 군급 국외 조달계획 {len(p):,}건", "건 · 요구연도별 · 색 = 소요군")
    fig = go.Figure()
    for a in [a for a in R.ARMY_COLOR if a in ya.columns]:
        fig.add_trace(go.Bar(x=list(ya.index), y=ya[a].tolist(), name=a, marker_color=R.ARMY_COLOR[a],
                             hovertemplate=f"{a} · %{{x}}년 %{{y:,}}건<extra></extra>"))
    for y in ya.index[ya.sum(axis=1) == 0]:        # 건수가 없는 해 — 빈 자리로 두지 않고 「정보 없음」이라고 적는다
        fig.add_annotation(x=int(y), y=0, text="정보 없음", showarrow=False, yanchor="bottom", yshift=6,
                           font=dict(size=12, color="#8a96ab"))
    fig.update_layout(barmode="stack", height=300)
    fig.update_xaxes(dtick=1)
    P.chart(fig, "p23_year")
    gap = {y: int((R.plan()["year"] == y).sum()) for y in (2018, 2019, 2020)}
    st.html('<div class="caption">원자료가 2018~2020년에 적게 들어 있는 구간(전자 군급 '
            + " · ".join(f"{y}년 {n}건" for y, n in gap.items()) + ')이라 「조달 없음 · 감소」로 읽지 않습니다.</div>')

P.next_link("fsc-army")
