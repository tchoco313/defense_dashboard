"""② 부품 → 무기체계 — 전자 군급(FSG 58·59)의 방위사업청 국외 조달계획과 국산화 완료 이력을 군급(FSC) 축으로 나란히 본다.

데이터 판정: docs/report/data-usage-decision-2026-09-18.md §1 핵심(국외 조달계획 API · 군급 기준표 · B2).
- 조달계획: raw_dapa_overseas_plan_api 중 재고번호(NSN) 13자리 · 앞 2자리 58·59 행. **정제본(clean) 전 원본 기준 = 잠정**
  (정제 담당 P3). 금액 열은 통화 미검증이라 쓰지 않고 건수만 센다. 적용장비명 '*'는 자리표시라 뺀다.
- 국산화 이력: clean_dapa_localized_item(B2, 지상 28개 사업의 완료 부품 목록). 부품 수 = part_mgmt_no 고유. 국산화율 아님.
- HS 품목군과 군급은 연결하지 않는다(대응표 미확정, CLAUDE.md). 표의 「관련 품목군」은 ref_hs_whitelist.related_fsc 후보값.
- 특정 무기체계의 취약 부품을 지목하지 않도록 적용장비는 이름 없이 종류 수만 보인다(docs/idea-review.md §3-10).
- FSG 60(광섬유)은 전자 플래그 수정 전이라 넣지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_ready, query  # noqa: E402
from ui import ACCENT, BG, SHORT, kpi, style_fig, zone  # noqa: E402

PLAN_C, B2_C = ACCENT, "#2ec4b6"            # 국외 조달계획 파랑 · 국산화 완료 청록
ARMY_C = {"육군": "#5b9bff", "해군": "#2ec4b6", "공군": "#f2b33d", "해병": "#b07cff"}

if not db_ready():
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> dict:
    plan = query(r"""
        SELECT LEFT(stock_no, 4) AS fsc4, LEFT(stock_no, 2) AS fsg, army_name, demand_year_req AS year,
               NULLIF(NULLIF(equipment_name, ''), '*') AS equipment
        FROM raw_dapa_overseas_plan_api
        WHERE stock_no REGEXP '^[0-9]{13}$' AND LEFT(stock_no, 2) IN ('58', '59')
    """)
    b2 = query("""
        SELECT fsc4, fsc2 AS fsg, COUNT(DISTINCT part_mgmt_no) AS parts, COUNT(DISTINCT project_name) AS projects
        FROM clean_dapa_localized_item WHERE fsc2 IN ('58', '59') GROUP BY fsc4, fsc2
    """)
    all_projects = int(query("SELECT COUNT(DISTINCT project_name) AS n FROM clean_dapa_localized_item").iloc[0]["n"])
    fsc = query("SELECT fsc4, name_ko FROM ref_fsc")
    fsg = query("SELECT fsg_code, name_ko FROM ref_fsg WHERE fsg_code IN ('58', '59')")
    wl = query("SELECT hs6, name_ko, related_fsc FROM ref_hs_whitelist WHERE evidence_basis = 'rule' AND related_fsc IS NOT NULL")
    return dict(plan=plan, b2=b2, all_projects=all_projects, fsc=fsc, fsg=fsg, wl=wl)


@st.cache_data(ttl=3600, show_spinner=False)
def b2_projects(fsgs: tuple[str, ...]) -> int:
    return int(query("SELECT COUNT(DISTINCT project_name) AS n FROM clean_dapa_localized_item WHERE fsc2 IN :g",
                     {"g": list(fsgs)}).iloc[0]["n"])


d = load()
fsc_name = dict(zip(d["fsc"]["fsc4"], d["fsc"]["name_ko"]))
fsg_name = dict(zip(d["fsg"]["fsg_code"], d["fsg"]["name_ko"]))
hs_of_fsc: dict[str, list[str]] = {}
for r in d["wl"].itertuples():
    for f in str(r.related_fsc).split(";"):
        hs_of_fsc.setdefault(f.strip(), []).append(SHORT.get(r.hs6, r.name_ko))

st.html('<div class="page-h">② 부품 → 무기체계</div>'
        '<div class="note">전자 군급(FSG 58 통신·탐지 · 59 전기·전자 구성품)을 기준으로, 방위사업청이 해외에서 조달하려는 품목과 '
        '국산화 개발을 마친 부품을 군급(FSC)별로 나란히 봅니다.</div>')

# ── 조건 ────────────────────────────────────────────────────────────────────
with zone("p2_top", "조건"):
    c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    g_pick = c1.pills("군급 그룹(FSG)", ["58", "59"], selection_mode="multi", default=["58", "59"], key="p2_fsg",
                      format_func=lambda g: f"{g} {fsg_name.get(g, '')}") or ["58", "59"]
    armies = [a for a in ARMY_C if a in set(d["plan"]["army_name"])]
    a_pick = c2.pills("소요군", armies, selection_mode="multi", default=armies, key="p2_army") or armies
    top_n = int(c3.number_input("표시할 군급 수", 5, 30, 15, step=5))

plan = d["plan"][d["plan"]["fsg"].isin(g_pick) & d["plan"]["army_name"].isin(a_pick)]
b2 = d["b2"][d["b2"]["fsg"].isin(g_pick)]
years = sorted(plan["year"].dropna().unique())

by_fsc = (plan.groupby("fsc4").agg(plan_n=("fsc4", "size"), eq_n=("equipment", "nunique")).reset_index()
          .merge(b2[["fsc4", "parts", "projects"]], on="fsc4", how="outer")
          .fillna({"plan_n": 0, "eq_n": 0, "parts": 0, "projects": 0}))
by_fsc["name"] = by_fsc["fsc4"].map(lambda f: fsc_name.get(f, "—"))
by_fsc["hs"] = by_fsc["fsc4"].map(lambda f: " · ".join(hs_of_fsc.get(f, [])) or "—")

# ── 요약 ────────────────────────────────────────────────────────────────────
with zone("p2_sum", "요약"):
    st.html('<div class="kpis k4">'
            + kpi("국외 조달계획 품목", f"{len(plan):,}", "건", f"NSN 기준 · 요구연도 {years[0]}~{years[-1]}" if years else "—", "잠정")
            + kpi("적용장비", f"{plan['equipment'].nunique():,}", "종", "조달계획에 적힌 적용장비명 고유 수")
            + kpi("해당 군급(FSC)", f"{plan['fsc4'].nunique()}", "개", f"FSG {' · '.join(g_pick)} · 조달계획 기준")
            + kpi("국산화 완료 부품", f"{int(b2['parts'].sum()):,}", "개",
                  f"B2 지상 {d['all_projects']}개 사업 중 {b2_projects(tuple(g_pick))}개 사업 · 국산화율 아님")
            + "</div>")

# ── 대칭 막대: 군급별 국외 조달계획 vs 국산화 완료 ───────────────────────────
with zone("p2_pair", "군급별 국외 조달계획 · 국산화 완료"):
    top = by_fsc.assign(key=by_fsc["plan_n"] + by_fsc["parts"]).nlargest(top_n, "key").sort_values("plan_n")
    labels = [f"{f} {n}" for f, n in zip(top["fsc4"], top["name"])]
    lim = float(max(top["plan_n"].max(), top["parts"].max())) * 1.25
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=-top["plan_n"], orientation="h", name="국외 조달계획(건)", marker_color=PLAN_C,
                         customdata=top["plan_n"], text=top["plan_n"].astype(int), textposition="outside", cliponaxis=False,
                         hovertemplate="%{y}<br>국외 조달계획 %{customdata:,}건<extra></extra>"))
    fig.add_trace(go.Bar(y=labels, x=top["parts"], orientation="h", name="국산화 완료 부품(개)", marker_color=B2_C,
                         text=top["parts"].astype(int), textposition="outside", cliponaxis=False,
                         hovertemplate="%{y}<br>국산화 완료 부품 %{x:,}개<extra></extra>"))
    fig.update_layout(barmode="overlay", bargap=0.3,
                      title="왼쪽 = 해외 조달 계획 품목(건) · 오른쪽 = 국산화 완료 부품(개)",
                      xaxis=dict(range=[-lim, lim], tickvals=[-lim * 0.7, 0, lim * 0.7],
                                 ticktext=[f"{lim * 0.7:,.0f}건", "0", f"{lim * 0.7:,.0f}개"]),
                      yaxis=dict(automargin=True), legend=dict(orientation="h", y=-0.06, title=None),
                      margin=dict(t=50, b=30, l=240))
    st.plotly_chart(style_fig(fig, 30 * len(top) + 160), width="stretch", theme=None)
    st.html(f'<div class="note">· 두 막대는 서로 다른 자료입니다. 한쪽이 길다고 「국산화가 부족하다」는 뜻이 아닙니다 — '
            f'조달계획은 품목 행 수, 국산화 목록은 지상 {d["all_projects"]}개 사업의 완료 부품만 담고 있습니다<br>'
            '· 0은 「없음」이 아니라 「이 자료에 없음」입니다</div>')

# ── 연도 · 소요군 ────────────────────────────────────────────────────────────
with zone("p2_year", "요구연도 · 소요군별 조달계획"):
    c1, c2 = st.columns([1.6, 1], gap="medium")
    yr = plan.groupby(["year", "army_name"]).size().unstack(fill_value=0)
    fig2 = go.Figure()
    for a in [a for a in ARMY_C if a in yr.columns]:
        fig2.add_trace(go.Bar(x=yr.index, y=yr[a], name=a, marker=dict(color=ARMY_C[a], line=dict(color=BG, width=1)),
                              hovertemplate=f"%{{x}}년 {a} %{{y}}건<extra></extra>"))
    fig2.update_layout(barmode="stack", title="요구연도별 계획 품목(건)", xaxis=dict(type="category"),
                       legend=dict(orientation="h", y=-0.15, title=None), margin=dict(t=50, b=30))
    c1.plotly_chart(style_fig(fig2, 340), width="stretch", theme=None)
    ar = plan.groupby("army_name").agg(n=("army_name", "size"), eq=("equipment", "nunique"))
    ar = ar.reindex([a for a in ARMY_C if a in ar.index])
    fig3 = go.Figure(go.Bar(x=ar.index, y=ar["n"], marker_color=[ARMY_C[a] for a in ar.index], text=ar["n"].astype(int),
                            textposition="outside", customdata=ar["eq"], cliponaxis=False,
                            hovertemplate="%{x} %{y:,}건 · 적용장비 %{customdata:,}종<extra></extra>"))
    fig3.update_layout(title="소요군별 계획 품목(건)", showlegend=False, margin=dict(t=50, b=30))
    c2.plotly_chart(style_fig(fig3, 340), width="stretch", theme=None)
    missing = [str(y) for y in range(int(years[0]), int(years[-1]) + 1) if str(y) not in yr.index] if years else []
    thin = [y for y in yr.index if yr.loc[y].sum() < 10]
    st.html('<div class="note">· 요구연도 = API 호출 기준 연도(demandYear). '
            + (f"{', '.join(missing)}년은 전자 군급 행이 없고 " if missing else "")
            + (f"{', '.join(thin)}년은 10건 미만입니다 — 수집 공백일 수 있어 「조달 없음 · 감소」로 읽지 않습니다" if thin or missing else "")
            + '<br>· 금액 열은 통화가 검증되지 않아 쓰지 않고 건수만 셉니다</div>')

# ── 군급 표 ─────────────────────────────────────────────────────────────────
with zone("p2_table", "군급(FSC) 표"):
    tbl = by_fsc.sort_values(["plan_n", "parts"], ascending=False)
    view = pd.DataFrame({"FSC": tbl["fsc4"], "군급 명칭": tbl["name"], "국외 조달계획(건)": tbl["plan_n"].astype(int),
                         "적용장비(종)": tbl["eq_n"].astype(int), "국산화 완료 부품(개)": tbl["parts"].astype(int),
                         "국산화 사업 수": tbl["projects"].astype(int), "관련 품목군(후보)": tbl["hs"]})
    st.dataframe(view, hide_index=True, width="stretch", height=min(38 + 35 * len(view), 520), column_config={
        "관련 품목군(후보)": st.column_config.TextColumn(help="HS6↔FSC4 공식 연계표가 없어 확정하지 않은 후보값(③ 표와 같은 값)")})
    st.download_button("⬇ 표 CSV 내려받기(엑셀)",
                       ("# 조건: FSG " + ",".join(g_pick) + " · 소요군 " + ",".join(a_pick) + "\n"
                        "# 출처: 방위사업청 국외 조달계획 OpenAPI(15158418, 원본 · 잠정) · 국방전자조달 국산화개발품목(15119899)\n"
                        + view.to_csv(index=False)).encode("utf-8-sig"),
                       file_name="부품_무기체계_군급표.csv", mime="text/csv")

st.html('<div class="caption">출처: 방위사업청 국외 조달계획 OpenAPI(15158418) 원본 → raw_dapa_overseas_plan_api (정제 전 · 잠정) · '
        '국방전자조달시스템 국산화개발품목(15119899) → clean_dapa_localized_item · 군급분류집 → ref_fsc · ref_fsg</div>')
