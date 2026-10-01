"""② 2-2 군급별 국외 조달계획 — 전자 군급별로 몇 건을 해외에서 조달하려 하나.

값: 방위사업청 국외 조달계획 OpenAPI 품목 중 전자 군급(군 58 · 59 · 60) 행(rds.plan) — 건수만 센다(금액은 통화 미검증).
적용장비는 이름 없이 종류 수만 보인다.
"""
from __future__ import annotations

from html import escape

import streamlit as st

import parts as P
import rds as R

SEE = "전자 관련 군(58 · 59 · 60)과 군급별 국외 조달계획 건수"
SOURCE = "방위사업청 · 국외 조달계획(품목) · 군급분류집"

fsg_name, fsc_name = R.fsg_names(), R.fsc_names()
allp = R.plan()
armies = [a for a in R.ARMY_COLOR if a in set(allp["army"])]
c1, c2 = st.columns([2.6, 1], vertical_alignment="bottom")   # 군 이름이 길어 왼쪽을 넓게(1.6 일 때 셋째 단추가 잘렸다)
g_pick = c1.pills("군(FSG)", R.FSGS, selection_mode="multi", default=R.FSGS, key="p22_fsg",
                  format_func=lambda g: f"{g} {fsg_name[g]}") or R.FSGS
a_pick = c2.pills("소요군", armies, selection_mode="multi", default=armies, key="p22_army") or armies
p = allp[allp["fsg"].isin(g_pick) & allp["army"].isin(a_pick)]
by_fsc = p.groupby("fsc4").size().sort_values(ascending=False)
by_g = {g: int((p["fsg"] == g).sum()) for g in g_pick}
total = len(p)
years = sorted(p["year"].unique())
yr_txt = f"{years[0]}–{years[-1]}" if years else "—"
gap = [y for y in (2018, 2019, 2020) if (allp["year"] == y).sum() < 20]

if not total:   # st.stop() 은 바닥글까지 멈추므로 쓰지 않는다
    P.lead("고른 군 · 소요군 조합에는 국외 조달계획 행이 없습니다", "조건을 바꿔 보세요")
else:
    top_g = max(by_g, key=by_g.get)
    P.lead(f'전자 군급 국외 조달계획 {total:,}건 중 <span class="key">군 {top_g}({escape(fsg_name[top_g])})가 '
           f'{by_g[top_g] / total * 100:.0f}%</span>다', "건 · 품목 단위(조달요구번호 × 품목순번) · 금액은 쓰지 않음(통화 미확인)")
    P.kpis([P.kpi("국외 조달계획", f"{total:,}", "건", f"전자 군급 · 요구연도 {yr_txt}"),
            P.kpi("해당 군급", f"{p['fsc4'].nunique()}", "개", "조달계획이 있는 군급(FSC)"),
            P.kpi("적용장비", f"{p['equipment'].nunique():,}", "종", "종류 수만(결측 제외) · 이름은 싣지 않음"),
            P.kpi("요구연도", yr_txt, "", f"{'·'.join(map(str, gap))}은 원자료가 적음" if gap else "요구연도 기준")])

    a, b = st.columns(2, gap="medium")
    with a, P.card("fsg"):
        P.title(f'가장 많은 군은 <span class="key">군 {top_g}</span>', f"건 · 군(FSG)별 · 요구연도 {yr_txt}")
        P.chart(P.hbar([(f"군 {g} {fsg_name[g]}", v, R.FSG_COLOR[g]) for g, v in by_g.items()], "건", 300), "p22_fsg_bar")
    with b, P.card("fsc8"):
        top8 = by_fsc.head(8)
        c0 = top8.index[0]
        P.title(f'가장 많은 군급은 <span class="key">{c0} {escape(fsc_name.get(c0, ""))}({int(top8.iloc[0]):,}건)</span>',
                "건 · 군급(FSC) 상위 8")
        P.chart(P.hbar([(f"{c} {fsc_name.get(c, '')}"[:26], int(v), R.FSG_COLOR[c[:2]]) for c, v in top8.items()], "건", 300), "p22_fsc")
    P.see(SEE, SOURCE)

    # 45행 전부 그리되 10행 높이 칸 안에서 세로 스크롤(칸 높이 · 행 수 = static/components.css 의 .st-key-p22_fsc_all --rows)
    with P.more(f"군급 표 전체({len(by_fsc)}개)"), st.container(key="p22_fsc_all"):
        rows = "".join(f"<tr><td>{c}</td><td class='l'>{escape(fsc_name.get(c, '—'))}</td><td>군 {c[:2]}</td><td>{int(v):,}</td></tr>"
                       for c, v in by_fsc.items())
        st.html(f'<table class="pt"><thead><tr><th>군급</th><th>이름</th><th>군</th><th>국외 조달계획(건)</th></tr></thead><tbody>{rows}</tbody></table>')
