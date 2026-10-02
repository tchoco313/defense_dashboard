"""① 1-3 공급국 집중도 변화 — 수입 쏠림은 어떻게 바뀌었나.

값: 연도별 HHI · 순위 = 관세청 연도별 집중도 · 점유율 뷰(rds.hhi_years · rds.ranks, 완결 연도), 기준 연도 국가 구성 · 산점 = rds.shares · rds.conc.
품목군 = 전체(13개 합계) · 상위 5개 합계 · 13개 각각. 여러 품목군은 국가별 금액을 합친 뒤 점유율 · HHI(rds.hhi_years_set · rds.ranks_set).
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
order = base.sort_values("total", ascending=False)                # 13개 — 기준 연도 수입액 순
ALL, TOP5 = "전체 (13개 품목군 합계)", f"상위 5개 품목군 합계 ({by}년 수입액)"
GROUPS = {ALL: order["hs6"].tolist(), TOP5: order["hs6"].head(5).tolist()}
c1, c2 = st.columns([1.15, 1], vertical_alignment="bottom")   # 수입/수출 단추를 품목군 칸 바로 옆에
# 전체 · 상위 5 · 13개 각각(수입액 순) — 15개라 단추 대신 선택 상자(글자 입력 없이 목록만). 처음은 상위 5개 합계
pick = c1.selectbox(f"품목군 (13개는 {by}년 수입액 순)", [ALL, TOP5] + order["short"].tolist(), index=1, key="p13_pick",
                    filter_mode=None)
flow_lb = c2.segmented_control("수입 / 수출", list(FLOW), default="수입", key="p13_flow", label_visibility="collapsed") or "수입"
flow = FLOW[flow_lb]
hs_set = GROUPS.get(pick) or order.loc[order["short"] == pick, "hs6"].tolist()
group = pick in GROUPS
name = ("13개 품목군 합계" if pick == ALL else "상위 5개 품목군 합계") if group else pick
tname = name.replace("품목군", "전자부품 품목군")   # 차트 제목용(「13개 전자부품 품목군 합계」) — 결론 문장은 name
names = R.country_names()
hy = R.hhi_years_set(hs_set, flow) if group else R.hhi_years(hs_set[0], flow)
source = f"관세청 · 품목별 국가별 수출입실적 · {R.customs_period()}"

if hy.empty:
    P.lead(f"{escape(name)}의 {flow_lb} 연도별 HHI를 계산할 실적이 없습니다", "완결 연도 기준")
else:
    h0, h1 = hy.iloc[0], hy.iloc[-1]
    gap = round(h1["hhi"]) - round(h0["hhi"])      # 첫 해와의 차이 — 문장에는 차이를 적는다(「2016년보다 907 높다」)
    word = f"보다 {abs(gap):,} 높다" if gap > 0 else f"보다 {abs(gap):,} 낮다" if gap < 0 else "와 같다"
    P.lead(f'{escape(name)}의 {flow_lb} HHI는 <span class="key">{int(h1["year"])}년 {h1["hhi"]:,.0f}</span>이다 — '
           f'{int(h0["year"])}년{word}',
           f"연도별 HHI(그해 값 — 1-1 기간 합계 HHI와 다름) · {flow_lb} 기준 · 국가 = {'선적국' if flow == 'imp' else '도착국'}"
           + (" · 여러 품목군은 국가별 금액을 합친 뒤 계산" if group else ""))

a, b = st.columns(2, gap="medium")
with a, P.card("bar7"):
    sh = R.shares(hs_set, by, flow).head(7)
    if sh.empty:
        P.title(f"{flow_lb} 상위국 점유율", f"% · {by}년")
        st.info(f"{by}년 {flow_lb} 실적이 없습니다(실제 0).")
    else:
        col = R.colors(sh["stat_cd"].tolist())
        P.title(f"{flow_lb} 상위국 점유율", f"% · {by}년 · 점선 = 50%")
        fig = P.hbar([(r.country, round(r.share, 1), col[r.stat_cd]) for r in sh.itertuples()], "%", 320)
        fig.add_vline(x=50, line_dash="dot", line_color="#94a3b8")
        P.chart(fig, "p13_bar")
        P.caption(f'{by}년 {flow_lb} 상위 7개국 — 1위 <span class="key">{escape(sh.iloc[0]["country"])} {sh.iloc[0]["share"]:.1f}%</span>')
with b, P.card("scatter"):
    sc = base if flow == "imp" else R.conc((by,), "exp")
    sc = sc.dropna(subset=["hhi"])
    hi = int((sc["hhi"] >= 2500).sum())
    col13 = R.colors(sc["top1_stat_cd"].tolist())
    P.title("전자부품 품목군별 점유율 분포",
            f"{by}년 · 가로 = 1위 {'공급국' if flow == 'imp' else '수출국'} 점유율(%) · 세로 = HHI · 색 = 1위 국가")
    # 고른 품목군을 크게 · 이름 표시(전체면 모두 같은 크기 · 이름 없음, 상위 5면 다섯 개)
    big = set(hs_set) if pick != ALL else set()
    fig = go.Figure(go.Scatter(x=(sc["top1_share"] * 100).round(1), y=sc["hhi"].round(0), mode="markers+text",
                               text=[s if h in big else "" for s, h in zip(sc["short"], sc["hs6"])], textposition="top center",
                               marker=dict(size=[16 if h in big else 11 for h in sc["hs6"]],
                                           color=[col13.get(c, "#94a7c8") for c in sc["top1_stat_cd"]], line=dict(color="#fff", width=1.5)),
                               customdata=[f"{s} · 1위 {names.get(c, c)}" for s, c in zip(sc["short"], sc["top1_stat_cd"])],
                               hovertemplate="%{customdata}<br>1위 %{x:.1f}% · HHI %{y:,}<extra></extra>"))
    fig.add_hline(y=2500, line_dash="dash", line_color="#94a3b8")
    fig.update_layout(height=320, showlegend=False, xaxis_title=f"1위 국가 점유율(%)", yaxis_title="HHI")
    P.chart(fig, "p13_scatter")
    P.caption(f'13개 품목군 중 <span class="key">{hi}개가 {flow_lb} HHI 2,500 이상</span>이다')
P.see(SEE, source)

a, b = st.columns(2, gap="medium")
with a, P.card("hhi"):
    P.title(f"{escape(tname)} — 연도별 {flow_lb} HHI", "그해 HHI · 점선 = 2,500(높음) · 완결 연도")
    fig = go.Figure(go.Scatter(x=hy["year"], y=hy["hhi"].round(0), mode="lines+markers", line=dict(color="#1d4ed8", width=3),
                               marker=dict(size=8), hovertemplate="%{x}년 HHI %{y:,}<extra></extra>"))
    fig.add_hline(y=2500, line_dash="dash", line_color="#94a3b8")
    fig.update_layout(height=280, showlegend=False)
    fig.update_xaxes(dtick=1)
    P.chart(fig, "p13_hhi")
with b, P.card("rank"):
    top3 = R.shares(hs_set, by, flow).head(3)
    P.title(f"{escape(tname)} — {by}년 상위 3개국의 순위 변화", f"순위(1 = 가장 큼) · 연도별 · {flow_lb}")
    rank_of = R.ranks_set if group else (lambda h, f, c: R.ranks(h[0], f, c))
    rk = rank_of(hs_set, flow, tuple(top3["stat_cd"])) if not top3.empty else None
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
