"""③ 3-2 조달계획과 나란히 — 해외 조달계획이 많은 군급과 국산화한 군급은 어떻게 다른가.

값: 같은 군급(FSC) 축에 국외 조달계획 건수(rds.plan)와 국산화 완료 부품 수(rds.loc)를 나란히 놓는다.
두 자료는 연결하거나 비율로 계산하지 않는다(한쪽이 많다고 「국산화가 부족하다」는 뜻이 아니다).
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R

SEE = "같은 군급 축에 놓은 국외 조달계획 건수(왼쪽)와 국산화 완료 부품 수(오른쪽)"
SOURCE = "방위사업청 · 국외 조달계획(품목) · 국산화개발품목 · 군급분류집"
TOP = 15

fsc_name = R.fsc_names()
plan_rows = R.plan()
year_start, year_end = int(plan_rows["year"].min()), int(plan_rows["year"].max())
plan_period = str(year_start) if year_start == year_end else f"{year_start}~{year_end}"
plan = plan_rows.groupby("fsc4").size().to_dict()
loc = R.loc().set_index("fsc4")["parts"].astype(int).to_dict()
both = sorted(set(plan) | set(loc), key=lambda c: -(plan.get(c, 0) + loc.get(c, 0)))
codes = both[:TOP]
p_top = max(plan, key=plan.get)
l_top = max(loc, key=loc.get)
P.lead(f'국외 조달계획 건이 가장 많은 군급코드는 <span class="key">{p_top}</span>, '
       f'국산화 완료 부품 개수가 가장 많은 군급코드는 <span class="key">{l_top}</span>이다',
       "두 자료는 같은 군급 축에 나란히 놓았을 뿐 연결하거나 비율로 계산하지 않습니다")

with P.card("pair"):
    P.title(f"{plan_period}년 군급별 국외 조달계획 · 국산화 완료",
            f"왼쪽 = 국외 조달계획(건, 요구연도 {plan_period}) · 오른쪽 = 국산화 완료 부품(개, 스냅샷) · 두 값의 합이 큰 군급 {len(codes)}개(전체 {len(both)}개)")
    ys = [f"{c} {fsc_name.get(c, '')}"[:24] for c in codes]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=ys, x=[-plan.get(c, 0) for c in codes], orientation="h", name="국외 조달계획(건)",
                         marker_color="#2b6ef6", customdata=[plan.get(c, 0) for c in codes],
                         hovertemplate="%{y}<br>국외 조달계획 %{customdata:,}건<extra></extra>"))
    fig.add_trace(go.Bar(y=ys, x=[loc.get(c, 0) for c in codes], orientation="h", name="국산화 완료 부품(개)",
                         marker_color="#17c8b5", hovertemplate="%{y}<br>국산화 완료 부품 %{x:,}개<extra></extra>"))
    m = max(max(plan.get(c, 0) for c in codes), max(loc.get(c, 0) for c in codes))
    step = 100 if m <= 400 else 200 if m <= 800 else 500
    ticks = list(range(0, m + step, step))
    fig.update_layout(barmode="overlay", height=480, bargap=.25)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickvals=[-t for t in ticks[:0:-1]] + ticks, ticktext=[f"{t:,}" for t in ticks[:0:-1]] + [f"{t:,}" for t in ticks])
    fig.add_vline(x=0, line_color="#16233f", line_width=2)
    P.chart(fig, "p32_pair")
P.see(SEE, SOURCE)

P.next_link("loc-pair")
