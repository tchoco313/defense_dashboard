"""① 1-1 종합 현황표 — 13개 품목군을 한 표로(명세 11_cat_parts.md §3 · §4, 차트 세부 22_category_table.md).

값: 관세청 연도 × 국가 수입(rds.trade)을 고른 기간만큼 합산한 뒤 점유율 · HHI(metrics.concentration — 한 해면 DB 뷰와 같은 값),
추이 = 최근 12개월 월별 수입액(rds.monthly12), 선정 근거 = 관세청 HS부호 규칙 판정(rds.items r1 · r2).
"""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R
from kdesign import LV_BG, LV_FG, hhi_level, sparkline

LEAD = '{n}개 품목군 중 <span class="key">{k}개는 1위 공급국 점유율이 50% 이상</span>이다'
LEAD_SUB = "{period} 합계 · 국가 전체 수입(민수 포함) · 우선순위를 정한 목록은 아닙니다"
SEE = "13개 품목군의 수입이 몇 나라에 몰렸는지(1위 공급국 점유율 · HHI)와 품목이 무엇인지"

ys = R.full_years()
by = ys[-1]
r5 = [y for y in ys if y >= by - 4]
PERIODS = {f"{by} 기준 연도": [by], f"최근 5년({r5[0]}~{by})": r5, f"전체({ys[0]}~{by})": ys}
period = st.segmented_control("기간 기준", list(PERIODS), default=list(PERIODS)[0], key="p11_period") or list(PERIODS)[0]
c = R.conc(tuple(PERIODS[period])).sort_values("hhi", ascending=False).reset_index(drop=True)
names = R.country_names()
col = R.colors(c["top1_stat_cd"].dropna().tolist())
k50 = int((c["top1_share"] >= 0.5).sum())
k25 = int((c["hhi"] >= 2500).sum())
total = c["total"].sum() / R.E8
cats = c["category"].value_counts()
cat_txt = " · ".join(f"{k} {int(cats[k])}" for k in ("반도체", "전자부품", "소재장비") if k in cats)
wide, m0, m1 = R.monthly12()
source = f"관세청 · 품목별 국가별 수출입실적 · {R.customs_period()} / 품목 선정: 관세청 HS부호 마스터"

P.lead(LEAD.format(n=len(c), k=k50), LEAD_SUB.format(period=period))
P.kpis([P.kpi("분석 대상 품목군", f"{len(c)}", "개", cat_txt),
        P.kpi("수입액", f"{total:,.1f}", "억 달러", f"{period} 합계 · 국가 전체 수입(민수 포함)"),
        P.kpi("1위 공급국 50% 이상", str(k50), "개", "1위 공급국 점유율 기준"),
        P.kpi("HHI 2,500 이상", str(k25), "개", "기간 합계 HHI · 공급 집중 「높음」")])

head = ("<tr><th>No.</th><th>품목군</th><th>관세청 품명</th><th>1위 공급국</th><th>1위 점유율</th><th>최근 12개월 추이</th>"
        "<th>HHI</th><th>공급 집중</th><th>수입국</th><th>선정 근거</th></tr>")
body = ""
for i, r in enumerate(c.to_dict("records"), 1):
    lvl, _ = hhi_level(r["hhi"])
    color = col.get(r["top1_stat_cd"], "#94a7c8")
    spark = wide.loc[r["hs6"]].tolist() if r["hs6"] in wide.index else [0.0] * 12
    badges = "".join(f'<span class="bdg rule">{x}</span>' for x in R.rules(r))
    body += (f'<tr><td>{i}</td><td class="l nm"><b>{escape(r["short"])}</b><em>HS {r["hs6"]}</em> '
             f'<span class="bdg fam">{escape(str(r["family"]))}</span></td>'
             f'<td class="l" style="max-width:220px">{escape(r["name_ko"])}</td>'
             f'<td><span class="cdot" style="background:{color}"></span>{escape(names.get(r["top1_stat_cd"], r["top1_stat_cd"]))}</td>'
             f'<td>{P.share_bar(r["top1_share"] * 100, color)}</td>'
             f'<td>{sparkline(spark, color)}</td><td>{r["hhi"]:,.0f}</td>'
             f'<td><span class="lvb" style="background:{LV_BG[lvl]};color:{LV_FG[lvl]}">{lvl}</span></td>'
             f'<td>{int(r["country_count"])}</td><td class="l">{badges}</td></tr>')
t = c.iloc[0]
with P.card("tbl"):
    P.title(f'HHI가 가장 높은 품목군은 <span class="key">{escape(t["short"])}(HHI {t["hhi"]:,.0f} · '
            f'1위 {escape(names.get(t["top1_stat_cd"], t["top1_stat_cd"]))} {t["top1_share"] * 100:.1f}%)</span>',
            f"{period} 합계 · HHI 내림차순 · 추이 = 최근 12개월({m0[:4]}.{m0[4:]}~{m1[:4]}.{m1[4:]}) 월별 수입액 · HHI 2,500 이상 = 높음")
    st.html(f'<div style="overflow-x:auto"><table class="pt"><thead>{head}</thead><tbody>{body}</tbody></table></div>')
P.see(SEE, source)

c1, c2 = st.columns([1.4, 1], gap="medium")
with c1, P.card("tree"):
    lo = c.iloc[-1]
    P.title(f'{period} 합계 HHI는 <span class="key">{escape(t["short"])} {t["hhi"]:,.0f}</span>로 가장 높고 '
            f'{escape(lo["short"])} {lo["hhi"]:,.0f}로 가장 낮다',
            "칸 크기 = HHI(0~10,000, 클수록 수입이 소수 국가에 몰림) · 색 = 1위 공급국")
    fig = go.Figure(go.Treemap(labels=c["short"].tolist(), parents=[""] * len(c), values=c["hhi"].round(0).tolist(),
                               marker=dict(colors=[col.get(x, "#94a7c8") for x in c["top1_stat_cd"]], line=dict(color="#fff", width=2)),
                               customdata=[names.get(x, x) for x in c["top1_stat_cd"]],
                               texttemplate="<b>%{label}</b><br>HHI %{value:,}",
                               hovertemplate="%{label}<br>HHI %{value:,} · 1위 %{customdata}<extra></extra>"))
    fig.update_layout(height=360, margin=dict(l=0, r=0, t=0, b=0))
    P.chart(fig, "p11_tree")
with c2, P.card("nctry"):
    top_n = c.loc[c["country_count"].idxmax()]
    P.title(f'수입국 수는 <span class="key">{escape(top_n["short"])} {int(top_n["country_count"])}개국</span>이 가장 많다',
            f"개국 · {period} · 수입 실적 > 0인 선적국 · 색 = 1위 공급국")
    rows = [(r["short"], int(r["country_count"]), col.get(r["top1_stat_cd"], "#94a7c8"))
            for r in c.sort_values("country_count", ascending=False).to_dict("records")]
    P.chart(P.hbar(rows, "개국", 360), "p11_nctry")
P.read1("HHI 2,500 이상 = 「높음」(미 법무부 · 연방거래위원회 2010 합병 지침의 고집중 기준) · 집중 수준 구간일 뿐 위험 예측이 아닙니다")

with P.more("자세히 보기 — 산식 · 선정 규칙"):
    st.markdown("- **1위 공급국 점유율** = 품목군 수입액 중 가장 큰 선적국의 비중(고른 기간 합계)\n"
                "- **HHI** = 국가별 점유율(%)의 제곱 합(0~10,000) — 수입 실적이 있는 선적국만\n"
                "- **선정 근거**: 군용 전용 세분류(관세청 HS부호 마스터의 「제9301호 · 제9306호 물품 전용」) · "
                "전문 용도 명시(세분류 · 품명에 항공기용 · 항행 · 레이더 · 무인기)\n"
                "- 수입액은 국가 전체 수입(민수 포함)이며 군수 몫은 관세 통계로 나뉘지 않습니다")
