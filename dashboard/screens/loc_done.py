"""③ 3-1 국산화 완료 부품 — 어느 군급에서 몇 개를 국산화했나.

값: 방위사업청 국산화개발품목 중 전자 군급(군 58 · 59 · 60) 부품(rds.loc · rds.loc_scope) — 부품 수 = 부품관리번호 고유 수.
국산화율이 아니다(필요 부품 전체 수 = 분모가 공개되지 않음). 사업 · 적용장비 이름은 싣지 않는다.
"""
from __future__ import annotations

from html import escape

import streamlit as st

import parts as P
import rds as R

SEE = "군(58 · 59 · 60)별 국산화 완료 부품 수와 상위 군급"
SOURCE = "방위사업청 · 국산화개발품목(시점 미상) · 군급분류집"
DONUT_COLOR = {"58": "#17c8b5", "59": "#2b6ef6"}   # 이 도넛에서만 — 군 58 녹색(아래 「군급별 국외 조달계획 · 국산화 완료」의 국산화 완료 막대 색) · 군 59 파랑
TOP_COLORS = ["#7c6cf0", "#38bdf8", "#ff6b9a", "#84cc16", "#1e3a8a"]   # 상위 군급 막대 — 순위마다 다른 색(왼쪽 도넛의 군 색 파랑 · 주황 · 청록과 겹치지 않게)

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
        P.kpi("국산화 사업", f"{sc['proj']}", "개", f"전체 {sc['proj_all']}개 사업 중 · 이름은 싣지 않음")], width_of=4)

a, b = st.columns([1.2, 1], gap="medium")
with a, P.card("donut"):
    none = [g for g, v in by_g.items() if not v]
    P.title("군(FSG)별 국산화 완료 비중",
            "개 · 군(FSG)별 군급 합" + (f" · 군 {'·'.join(none)}은 이 자료에 없음" if none else ""))
    rows = [(f"군 {g} {fsg_name[g]}", v, DONUT_COLOR.get(g, R.FSG_COLOR[g])) for g, v in by_g.items() if v]
    fig = P.donut(rows, f"<b>{g_sum:,}개<br>완료 부품</b>", 340)
    fig.update_traces(hole=.4)                                   # 고리를 두껍게(기본 .58)
    fig.update_annotations(font_size=19)                          # 가운데 합계 글씨(기본 17)
    fig.update_layout(legend=dict(orientation="h", x=.5, xanchor="center", y=-.04, yanchor="top"),   # 범례(군 이름)는 도넛 아래에
                      margin=dict(l=8, r=8, t=8, b=8))
    P.chart(fig, "p31_donut")
    P.caption(f'완료 부품이 가장 많은 군은 <span class="key">군 {top_g} {by_g[top_g] / g_sum * 100:.0f}%</span>')
with b, P.card("top5"):
    top5 = lc.sort_values("parts", ascending=False).head(5)
    t0 = top5.iloc[0]
    P.title("상위 군급 국산화 현황", "개 · 국산화개발품목 · 상위 5 군급 · 막대에 커서를 올리면 군급 이름 · 적용장비 이름은 싣지 않습니다")

    def short(code: str) -> str:      # 세로축 이름 — 길면 줄인다(전체 이름은 커서를 올리면 보인다)
        name = fsc_name.get(code, "")
        return f"{code} {name[:11]}…" if len(name) > 12 else f"{code} {name}"

    fig = P.hbar([(short(r.fsc4), int(r.parts), c) for r, c in zip(top5.itertuples(), TOP_COLORS)], "개", 340)
    fig.update_traces(customdata=[fsc_name.get(c, "") for c in reversed(list(top5["fsc4"]))], width=.62,
                      hovertemplate="%{customdata}<br>%{x:,} 개<extra></extra>")
    fig.update_layout(margin=dict(l=10, r=48, t=34, b=8))       # 막대를 살짝 아래로 — 왼쪽 도넛과 높이 중심을 맞춘다
    P.chart(fig, "p31_top5")
    P.caption(f'가장 많은 군급은 <span class="key">{t0["fsc4"]} {escape(fsc_name.get(t0["fsc4"], ""))}</span>')
P.read1("완료 부품 수는 국산화율이 아닙니다 — 전체 필요 부품 수(분모)가 공개되지 않았습니다 · "
        "군별 합은 군급마다 센 뒤 더해 고유 부품 수와 조금 다를 수 있습니다")
P.see(SEE, SOURCE)
