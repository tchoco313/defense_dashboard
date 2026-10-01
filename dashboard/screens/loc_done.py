"""③ 3-1 국산화 완료 부품 — 어느 군급에서 몇 개를 국산화했나(명세 13_cat_localization.md §3, 차트 세부 21_parts_fsc.md loc · eq 왼쪽).

값: 방위사업청 국산화개발품목 중 전자 군급(군 58 · 59 · 60) 부품(rds.loc · rds.loc_scope) — 부품 수 = 부품관리번호 고유 수.
국산화율이 아니다(필요 부품 전체 수 = 분모가 공개되지 않음). 사업 · 적용장비 이름은 싣지 않는다(idea-review §3-10).
"""
from __future__ import annotations

from html import escape

import streamlit as st

import parts as P
import rds as R
from kdesign import rank_card

SEE = "군(58 · 59 · 60)별 국산화 완료 부품 수와 상위 군급"
SOURCE = "방위사업청 · 국산화개발품목(시점 미상) · 군급분류집"

fsg_name, fsc_name = R.fsg_names(), R.fsc_names()
lc = R.loc()
sc = R.loc_scope()
by_g = {g: int(lc.loc[lc["fsg"] == g, "parts"].sum()) for g in R.FSGS}
top_g = max(by_g, key=by_g.get)
g_sum = sum(by_g.values())
P.lead(f'전자 군급 국산화 완료 부품 {sc["parts"]:,}개 중 <span class="key">군 {top_g}({escape(fsg_name[top_g])})가 '
       f'{by_g[top_g]:,}개</span>다', "부품 고유 수(부품관리번호) · 시점 미상 · 국산화율 아님")
P.kpis([P.kpi("국산화 완료 부품", f"{sc['parts']:,}", "개", f"전자 군급 · 전체 {sc['parts_all']:,}개 중"),
        P.kpi("해당 군급", f"{lc['fsc4'].nunique()}", "개", "완료 부품이 있는 군급(FSC)"),
        P.kpi("국산화 사업", f"{sc['proj']}", "개", f"전체 {sc['proj_all']}개 사업 중 · 이름은 싣지 않음")])

a, b = st.columns([1.2, 1], gap="medium")
with a, P.card("donut"):
    none = [g for g, v in by_g.items() if not v]
    P.title(f'완료 부품이 가장 많은 군은 <span class="key">군 {top_g} {by_g[top_g] / g_sum * 100:.0f}%</span>',
            "개 · 군(FSG)별 군급 합" + (f" · 군 {'·'.join(none)}은 이 자료에 없음" if none else ""))
    rows = [(f"군 {g} {fsg_name[g]}", v, R.FSG_COLOR[g]) for g, v in by_g.items() if v]
    P.chart(P.donut(rows, f"{g_sum:,}개<br>완료 부품", 340), "p31_donut")
with b:
    top5 = lc.sort_values("parts", ascending=False).head(5)
    t0 = top5.iloc[0]
    st.html(rank_card(f'가장 많은 군급은 <span class="key">{t0["fsc4"]} {escape(fsc_name.get(t0["fsc4"], ""))}</span>',
                      "국산화개발품목 · 상위 5 군급 · 적용장비 이름은 싣지 않습니다",
                      [(f"{r.fsc4} {escape(fsc_name.get(r.fsc4, ''))}", int(r.parts), R.FSG_COLOR.get(r.fsg, "#94a7c8"))
                       for r in top5.itertuples()], "개"))
P.read1("완료 부품 수는 국산화율이 아닙니다 — 전체 필요 부품 수(분모)가 공개되지 않았습니다 · "
        "군별 합은 군급마다 센 뒤 더해 고유 부품 수와 조금 다를 수 있습니다")
P.see(SEE, SOURCE)
