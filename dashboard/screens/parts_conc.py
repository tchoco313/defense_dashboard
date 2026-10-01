"""① 1-3 공급국 집중도 변화 — 수입 쏠림은 어떻게 바뀌었나.

값: 연도별 HHI · 순위 = 관세청 연도별 집중도 · 점유율 뷰(rds.hhi_years · rds.ranks, 완결 연도), 기준 연도 국가 구성 · 산점 = rds.shares · rds.conc.
「연도별 HHI」(그해 값)와 1-1의 기간 합계 HHI는 다른 지표다.
"""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R

SEE = "품목군별 연도별 HHI와 1위 공급국 순위가 해마다 바뀌었는지"
FLOW = {"수입": "imp", "수출": "exp"}

by = R.base_year()
base = R.conc((by,))
top5 = base.sort_values("total", ascending=False).head(5)
c1, c2 = st.columns([1.15, 1], vertical_alignment="bottom")   # 수입/수출 단추를 품목군 단추 바로 옆에
pick = c1.pills(f"품목군({by}년 수입액 상위 5)", top5["short"].tolist(), default=top5.iloc[0]["short"], key="p13_hs") \
    or top5.iloc[0]["short"]
flow_lb = c2.segmented_control("수입 / 수출", list(FLOW), default="수입", key="p13_flow", label_visibility="collapsed") or "수입"
flow = FLOW[flow_lb]
hs = top5.loc[top5["short"] == pick, "hs6"].iloc[0]
names = R.country_names()
hy = R.hhi_years(hs, flow)
source = f"관세청 · 품목별 국가별 수출입실적 · {R.customs_period()}"

if hy.empty:
    P.lead(f"{escape(pick)}의 {flow_lb} 연도별 HHI를 계산할 실적이 없습니다", "완결 연도 기준")
else:
    h0, h1 = hy.iloc[0], hy.iloc[-1]
    gap = round(h1["hhi"]) - round(h0["hhi"])      # 첫 해와의 차이 — 문장에는 차이를 적는다(「2016년보다 907 높다」)
    word = f"보다 {abs(gap):,} 높다" if gap > 0 else f"보다 {abs(gap):,} 낮다" if gap < 0 else "와 같다"
    P.lead(f'{escape(pick)}의 {flow_lb} HHI는 <span class="key">{int(h1["year"])}년 {h1["hhi"]:,.0f}</span>이다 — '
           f'{int(h0["year"])}년{word}',
           f"연도별 HHI(그해 값 — 1-1 기간 합계 HHI와 다름) · {flow_lb} 기준 · 국가 = {'선적국' if flow == 'imp' else '도착국'}")

a, b = st.columns(2, gap="medium")
with a, P.card("bar7"):
    sh = R.shares([hs], by, flow).head(7)
    if sh.empty:
        P.title(f"{by}년 {flow_lb} 상위 7개국")
        st.info(f"{by}년 {flow_lb} 실적이 없습니다(실제 0).")
    else:
        col = R.colors(sh["stat_cd"].tolist())
        P.title(f'{by}년 {flow_lb} 상위 7개국 — 1위 <span class="key">{escape(sh.iloc[0]["country"])} {sh.iloc[0]["share"]:.1f}%</span>',
                f"% · {by}년 · 점선 = 50%")
        fig = P.hbar([(r.country, round(r.share, 1), col[r.stat_cd]) for r in sh.itertuples()], "%", 320)
        fig.add_vline(x=50, line_dash="dot", line_color="#94a3b8")
        P.chart(fig, "p13_bar")
with b, P.card("scatter"):
    sc = base if flow == "imp" else R.conc((by,), "exp")
    sc = sc.dropna(subset=["hhi"])
    hi = int((sc["hhi"] >= 2500).sum())
    col13 = R.colors(sc["top1_stat_cd"].tolist())
    P.title(f'13개 품목군 중 <span class="key">{hi}개가 {flow_lb} HHI 2,500 이상</span>이다',
            f"{by}년 · 가로 = 1위 {'공급국' if flow == 'imp' else '수출국'} 점유율(%) · 세로 = HHI · 색 = 1위 국가")
    fig = go.Figure(go.Scatter(x=(sc["top1_share"] * 100).round(1), y=sc["hhi"].round(0), mode="markers+text",
                               text=[s if h == hs else "" for s, h in zip(sc["short"], sc["hs6"])], textposition="top center",
                               marker=dict(size=[16 if h == hs else 11 for h in sc["hs6"]],
                                           color=[col13.get(c, "#94a7c8") for c in sc["top1_stat_cd"]], line=dict(color="#fff", width=1.5)),
                               customdata=[f"{s} · 1위 {names.get(c, c)}" for s, c in zip(sc["short"], sc["top1_stat_cd"])],
                               hovertemplate="%{customdata}<br>1위 %{x:.1f}% · HHI %{y:,}<extra></extra>"))
    fig.add_hline(y=2500, line_dash="dash", line_color="#94a3b8")
    fig.update_layout(height=320, showlegend=False, xaxis_title=f"1위 국가 점유율(%)", yaxis_title="HHI")
    P.chart(fig, "p13_scatter")
P.see(SEE, source)

a, b = st.columns(2, gap="medium")
with a, P.card("hhi"):
    P.title(f"{escape(pick)} — 연도별 {flow_lb} HHI", "그해 HHI · 점선 = 2,500(높음) · 완결 연도")
    fig = go.Figure(go.Scatter(x=hy["year"], y=hy["hhi"].round(0), mode="lines+markers", line=dict(color="#1d4ed8", width=3),
                               marker=dict(size=8), hovertemplate="%{x}년 HHI %{y:,}<extra></extra>"))
    fig.add_hline(y=2500, line_dash="dash", line_color="#94a3b8")
    fig.update_layout(height=280, showlegend=False)
    fig.update_xaxes(dtick=1)
    P.chart(fig, "p13_hhi")
with b, P.card("rank"):
    top3 = R.shares([hs], by, flow).head(3)
    P.title(f"{escape(pick)} — {by}년 상위 3개국의 순위 변화", f"순위(1 = 가장 큼) · 연도별 · {flow_lb}")
    rk = R.ranks(hs, flow, tuple(top3["stat_cd"])) if not top3.empty else None
    if rk is None or rk.empty:
        st.info("순위를 그릴 실적이 없습니다.")
    else:
        colr = R.colors(top3["stat_cd"].tolist())
        fig = go.Figure()
        for code in top3["stat_cd"]:
            d = rk[rk["stat_cd"] == code]
            fig.add_trace(go.Scatter(x=d["year"], y=d["rnk"], mode="lines+markers", name=names.get(code, code),
                                     line=dict(color=colr[code], width=3), marker=dict(size=9),
                                     hovertemplate=f"{names.get(code, code)} · %{{x}}년 %{{y}}위<extra></extra>"))
        fig.update_layout(height=280)
        fig.update_yaxes(autorange="reversed", dtick=1)
        fig.update_xaxes(dtick=1)
        P.chart(fig, "p13_rank")

P.next_link("parts-conc")
