"""② 조달·국산화 근거 — 팀원 디자인 데모(K-Defense) 「부품 → 무기체계」 + 「국내 조달」 화면 틀을 그대로 옮기고 값만 RDS 로 바꿨다.

위: 전자 군급(FSG 58·59·60)의 방위사업청 국외 조달계획과 국산화 완료 이력을 같은 군급(FSC) 축에 나란히 놓는다(연결·비율 아님).
아래(부록, 2026-09-21 M2): 방위사업청 국내 조달 계약 방법 · 수의계약 사유 · 경쟁입찰 결과 · 공고 상태(건수만, 금액 미사용).

데이터 판정: docs/report/data/data-usage-decision-2026-09-18.md §1 핵심(국외 조달계획 API · 군급 기준표 · B2), 부록은 app/specs/34_domestic_procurement.md.
- 조달계획: clean_dapa_overseas_plan_api 중 is_elec = 1 행(FSG 58·59·60, 2026-09-21 M4). 금액 열은 통화 미검증이라 쓰지 않고 건수(행 = 조달요구번호 × 품목순번)만 센다.
- 국산화 이력: clean_dapa_localized_item(B2, 지상 사업의 완료 부품 목록, is_electronic_group = 1). 부품 수 = part_mgmt_no 고유. 국산화율 아님.
- 국내 조달: clean_dapa_contract(계약 단위 = is_latest_seq = 1) · v_contract_private_reason(계약번호당 1행) · clean_dapa_bid_result
  (고유 키 = is_key_representative = 1) · clean_dapa_bid_notice. 공고 예산 ≠ 낙찰금액 ≠ 계약금액이라 금액은 쓰지 않는다.
- HS 품목군과 군급·조달 자료는 연결하지 않는다(카테고리 맵 2026-09-21 폐기, CLAUDE.md). 관세청 수입액과 합산·비교하지 않는다.
- 특정 무기체계의 취약 부품을 지목하지 않도록 적용장비는 이름 없이 종류 수만 보인다(docs/idea-review.md §3-10) —
  데모의 「적용장비 TOP 품목」 자리는 「국산화 완료 부품 상위 군급」으로 바꿨다.
"""
from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import data_stamp, query
from kdesign import ETC, SERIES, TEXT
from ui import (chart_source, chart_title, csv_header, hero, hover_donut, kpi, png_button, rank_card, rules_card, style_fig,
                zone)

PLAN_C, B2_C = SERIES[0], SERIES[2]          # 국외 조달계획 · 국산화 완료(두 자료 구분색)
ARMY_C = {"육군": SERIES[0], "해군": SERIES[1], "공군": SERIES[2], "해병대": SERIES[3], "국직": SERIES[4], "미확인": ETC}
FSGS = ["58", "59", "60"]                    # clean.is_elec = fsg2 IN (58, 59, 60) — 2026-09-21 M4 확정
FSG_C = {"58": SERIES[0], "59": SERIES[1], "60": SERIES[2]}
SOURCE_LINE = ("방위사업청 국외 조달계획 OpenAPI(15158418) → clean_dapa_overseas_plan_api(is_elec=1 · FSG 58·59·60) · "
               "국방전자조달시스템 국산화개발품목(15119899) → clean_dapa_localized_item · 군급분류집 → ref_fsc · ref_fsg")
DOM_SOURCE = ("방위사업청 국내조달 계약정보(15050920) → clean_dapa_contract · 입찰공고 → clean_dapa_bid_notice · "
              "입찰결과 → clean_dapa_bid_result · 국외조달 계약정보 → clean_dapa_overseas_contract")
SRC_PLAN = "방위사업청 국외 조달계획 OpenAPI(15158418) → clean_dapa_overseas_plan_api(is_elec=1 · FSG 58·59·60) · 군급분류집 → ref_fsc · ref_fsg"
SRC_B2 = "국방전자조달시스템 국산화개발품목(15119899) → clean_dapa_localized_item(is_electronic_group=1) · 군급분류집 → ref_fsc · ref_fsg"
PLOT_CFG = {"displaylogo": False, "modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "autoScale2d"]}


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> dict:
    plan = query("""
        SELECT fsc4, fsg2 AS fsg, army_std AS army_name, demand_year AS year,
               CASE WHEN is_equipment_missing = 0 THEN equipment_name END AS equipment
        FROM clean_dapa_overseas_plan_api WHERE is_elec = 1
    """)
    plan["year"] = plan["year"].astype("int64")
    b2 = query("""
        SELECT fsc4, fsc2 AS fsg, COUNT(DISTINCT part_mgmt_no) AS parts, COUNT(DISTINCT project_name) AS projects
        FROM clean_dapa_localized_item WHERE is_electronic_group = 1 GROUP BY fsc4, fsc2
    """)
    all_projects = int(query("SELECT COUNT(DISTINCT project_name) AS n FROM clean_dapa_localized_item").iloc[0]["n"])
    fsc = query("SELECT fsc4, name_ko FROM ref_fsc")
    fsg = query("SELECT fsg_code, name_ko FROM ref_fsg WHERE fsg_code IN :g", {"g": FSGS})
    gap = query("SELECT COUNT(*) AS n, SUM(demand_year = 2018) AS y18, SUM(demand_year = 2019) AS y19, "
                "SUM(demand_year = 2020) AS y20 FROM clean_dapa_overseas_plan_api").iloc[0]   # 원자료 빈 구간 캡션용
    return dict(plan=plan, b2=b2, all_projects=all_projects, fsc=fsc, fsg=fsg, gap={k: int(gap[k] or 0) for k in gap.index})


@st.cache_data(ttl=3600, show_spinner=False)
def b2_scope(fsgs: tuple[str, ...]) -> tuple[int, int]:
    """고른 FSG 의 국산화 완료 부품 고유 수 · 사업 수(FSC4 합이 아니라 전체 고유 — 한 부품이 두 FSC 에 걸쳐도 한 번)."""
    r = query("SELECT COUNT(DISTINCT part_mgmt_no) AS parts, COUNT(DISTINCT project_name) AS projects "
              "FROM clean_dapa_localized_item WHERE is_electronic_group = 1 AND fsc2 IN :g", {"g": list(fsgs)}).iloc[0]
    return int(r["parts"]), int(r["projects"])


@st.cache_data(ttl=3600, show_spinner=False)
def load_domestic() -> dict:
    method = query("SELECT contract_method_name AS m, COUNT(*) AS n FROM clean_dapa_contract "
                   "WHERE is_latest_seq = 1 GROUP BY contract_method_name ORDER BY n DESC")
    reason = query("SELECT reason_group AS g, SUM(contract_count) AS n FROM v_contract_private_reason "
                   "GROUP BY reason_group ORDER BY n DESC")
    bid = query("SELECT opening_result AS r, COUNT(*) AS rows_n, SUM(is_key_representative) AS keys_n "
                "FROM clean_dapa_bid_result GROUP BY opening_result")
    notice = query("SELECT bid_notice_status AS s, COUNT(*) AS n FROM clean_dapa_bid_notice GROUP BY bid_notice_status ORDER BY n DESC")
    one = query("""SELECT (SELECT COUNT(*) FROM clean_dapa_contract) AS rows_all,
                          (SELECT COUNT(DISTINCT winner_biz_reg_no) FROM clean_dapa_bid_result WHERE winner_biz_reg_no IS NOT NULL) AS winners,
                          (SELECT COUNT(*) FROM clean_dapa_overseas_contract) AS ov_n,
                          (SELECT COUNT(*) FROM clean_dapa_overseas_contract WHERE contract_method_name LIKE '%수의%') AS ov_priv,
                          (SELECT COUNT(*) FROM clean_dapa_bid_notice WHERE YEAR(bid_notice_date) = 2024) AS n24,
                          (SELECT COUNT(*) FROM clean_dapa_bid_notice WHERE YEAR(bid_notice_date) = 2025) AS n25""").iloc[0]
    return dict(method=method, reason=reason, bid=bid, notice=notice, one={k: int(v) for k, v in one.items()})


def hbar(rows: list[tuple[str, int, str]], height: int = 300, unit: str = "") -> go.Figure:
    """데모 hbar(가로 막대 · 값 라벨 · 긴 라벨 자리 확보) 그대로."""
    rows = list(reversed(rows))
    fig = go.Figure(go.Bar(x=[r[1] for r in rows], y=[r[0] for r in rows], orientation="h",
                           marker=dict(color=[r[2] for r in rows], line=dict(color="#fff", width=1)),
                           text=[f"{r[1]:,}" for r in rows], textposition="outside",
                           textfont=dict(size=12.5, color=TEXT), cliponaxis=False,
                           hovertemplate="%{y}<br>%{x:,}" + f" {unit}<extra></extra>"))
    label_w = max(len(str(r[0])) for r in rows) * 11 + 14
    fig.update_layout(height=height, showlegend=False, margin=dict(l=min(label_w, 230), r=48, t=10, b=8))
    return fig


def pie_fig(rows: list[tuple[str, float, str]], center: str) -> go.Figure:
    """hover_donut(HTML) 과 같은 값 · 색의 plotly 도넛 — PNG 내려받기용."""
    fig = go.Figure(go.Pie(labels=[r[0] for r in rows], values=[r[1] for r in rows], hole=.55, sort=False,
                           marker=dict(colors=[r[2] for r in rows], line=dict(color="#fff", width=1.5)), textinfo="label+percent"))
    fig.update_layout(height=420, annotations=[dict(text=center, showarrow=False, font=dict(size=17))])
    return style_fig(fig)


def pct_rows(rows: list[tuple[str, float, str]]) -> str:
    """이름 · 막대 · % 한 줄씩(점선 = 50%) — 데모 pct_rows 그대로."""
    return '<div class="bars big">' + "".join(
        f'<div class="row" title="{n} {v:.1f}%"><div class="nm">{n}</div><div class="track">'
        f'<div class="fill" style="width:{v:.1f}%;background:{c}"></div><div class="ref"></div></div>'
        f'<div class="pct">{v:.1f}%</div></div>' for n, v, c in rows) + "</div>"


def chart(fig: go.Figure, fname: str, key: str, title: str | None = None, source: str | None = None) -> None:
    """plotly 차트 + 보이는 그림 그대로 PNG(결론형 제목 · 출처 한 줄은 PNG 에도 얹는다)."""
    st.plotly_chart(style_fig(fig), width="stretch", theme=None, key=key, config=PLOT_CFG)
    png_button(fig, fname, align="flex-start", title=title, source=source)


def pct(n: float, d: float) -> float:
    return n / d * 100 if d else 0.0


def stamp_txt(s: dict) -> str:
    return "—(조회 실패)" if s.get("error") and not s.get("loaded") else (s.get("loaded") or "—")


s_plan = data_stamp("dapa_overseas_plan_api", "clean_dapa_overseas_plan_api")
s_b2 = data_stamp("dapa_localized_item", "clean_dapa_localized_item")
s_con = data_stamp("dapa_contract", "clean_dapa_contract")
hero("② 조달·국산화 근거", "전자 군급별 국외 조달계획과 국산화를 마친 부품, 국내 조달이 이뤄지는 방식을 봅니다",
     stamps=[("국외 조달계획", s_plan), ("국산화개발품목", s_b2), ("국내 계약", s_con)])

with st.spinner("팀 DB에서 방위사업청 조달계획·국산화 목록을 읽는 중"):
    d = load()
fsc_name = dict(zip(d["fsc"]["fsc4"], d["fsc"]["name_ko"]))
fsg_name = dict(zip(d["fsg"]["fsg_code"], d["fsg"]["name_ko"]))

st.html('<div class="lede"><div class="note">전자 군급(FSG 58 통신·탐지 · 59 전기·전자 구성품 · 60 광섬유)을 기준으로, '
        '국외 조달계획과 국산화 개발 부품을 군급(FSC)별로 나란히 봅니다. '
        'HS 품목군과는 <b>연결하지 않습니다</b>(공식 대응표 없음). 두 자료는 합산·비율로 보지 않습니다.</div></div>')

# ── 조건(클릭) — FSG · 소요군 ──────────────────────────────────────────────────
with st.container(key="filters_p2"):
    c1, c2 = st.columns([1.2, 1], vertical_alignment="bottom")
    g_pick = c1.pills("군급 그룹(FSG)", FSGS, selection_mode="multi", default=FSGS, key="p2_fsg",
                      format_func=lambda g: f"{g} {fsg_name.get(g, '')}") or FSGS
    armies = [a for a in ARMY_C if a in set(d["plan"]["army_name"])]
    a_pick = c2.pills("소요군(조달계획에만 적용)", armies, selection_mode="multi", default=armies, key="p2_army") or armies

plan = d["plan"][d["plan"]["fsg"].isin(g_pick) & d["plan"]["army_name"].isin(a_pick)]
b2 = d["b2"][d["b2"]["fsg"].isin(g_pick)]
years = [int(y) for y in sorted(plan["year"].dropna().unique())]
yr_txt = f"{years[0]}~{years[-1]}" if years else "—"
by_fsc = (plan.groupby("fsc4").agg(plan_n=("fsc4", "size"), eq_n=("equipment", "nunique")).reset_index()
          .merge(b2[["fsc4", "parts", "projects"]], on="fsc4", how="outer")
          .fillna({"plan_n": 0, "eq_n": 0, "parts": 0, "projects": 0}))
by_fsc["name"] = by_fsc["fsc4"].map(lambda f: fsc_name.get(f, "—"))
n_parts, n_proj = b2_scope(tuple(g_pick))
tag = "_".join(g_pick)

if by_fsc.empty:
    st.info("고른 군급 그룹 · 소요군 조합에는 국외 조달계획 행도 국산화 완료 부품도 없습니다. 조건을 바꿔 보세요.")
else:
    # ── 전자 군급 현황(KPI 5) ─────────────────────────────────────────────────
    with zone("kpi3", "전자 군급 현황"):
        st.html('<div class="kpis">'
                + kpi("국외 조달계획 품목", f"{len(plan):,}", "건", f"요구연도 {yr_txt} · 조달요구번호 × 품목순번 행")
                + kpi("해당 군급(FSC)", f"{plan['fsc4'].nunique()}", "개", "조달계획에 나온 FSC4 수")
                + kpi("국산화 완료 부품", f"{n_parts:,}", "개", "part_mgmt_no 고유 · 국산화율 아님")
                + kpi("국산화 사업", f"{n_proj}", "개", f"B2 지상 {d['all_projects']}개 사업 중")
                + kpi("적용장비", f"{plan['equipment'].nunique():,}", "종", "고유 수(결측 제외) · 이름은 싣지 않음")
                + "</div>")
        st.html('<div class="caption">두 자료는 합산 · 비교하지 않음 · 금액 미사용(통화 미검증)</div>')
        chart_source(f"{SOURCE_LINE} · 조달계획 DB 적재 {stamp_txt(s_plan)} · 국산화개발품목 DB 적재 {stamp_txt(s_b2)}")

    # ── 군급 분포 ──────────────────────────────────────────────────────────────
    with zone("fsg", "군급 분포"):
        c1, c2 = st.columns(2, gap="medium")
        by_fsg = plan.groupby("fsg").size()
        fsg_rows = [(f"FSG {g} ({fsg_name.get(g, '')})", int(by_fsg.get(g, 0)), FSG_C[g]) for g in FSGS if g in g_pick]
        with c1.container(border=True, key="card_fsg"):
            f_tot = sum(v for _, v, _ in fsg_rows)
            f_top = max(fsg_rows, key=lambda r: r[1]) if fsg_rows else None
            t_fsg = (f"국외 조달계획 {f_tot:,}건 중 가장 많은 군급 그룹은 "
                     f'<span class="key">{escape(f_top[0])} {pct(f_top[1], f_tot):.0f}%</span>') if f_top and f_tot else "FSG 58·59·60 분포"
            chart_title(t_fsg, f"건 · 요구연도 {yr_txt} · 국외 조달계획")
            chart(hbar(fsg_rows, 300, "건"), f"조달계획_FSG분포_{tag}", "p2_fsg_bar", title=t_fsg, source=SRC_PLAN)
            chart_source(f"{SRC_PLAN} · DB 적재 {stamp_txt(s_plan)}")
        top_fsc = by_fsc[by_fsc["plan_n"] > 0].nlargest(8, "plan_n")
        fsc_rows = [(f"{f} {n}"[:24], int(v), SERIES[i % len(SERIES)]) for i, (f, n, v) in
                    enumerate(zip(top_fsc["fsc4"], top_fsc["name"], top_fsc["plan_n"]))]
        with c2.container(border=True, key="card_fsc"):
            if fsc_rows:
                r0 = top_fsc.iloc[0]
                t_fsc = (f"국외 조달계획이 가장 많은 군급(FSC)은 "
                         f'<span class="key">{escape(str(r0.fsc4))} {escape(str(r0["name"]))}({int(r0.plan_n):,}건)</span>')
                chart_title(t_fsc, f"건 · 요구연도 {yr_txt} · 상위 8")
                chart(hbar(fsc_rows, 300, "건"), f"조달계획_FSC상위_{tag}", "p2_fsc_bar", title=t_fsc, source=SRC_PLAN)
                chart_source(f"{SRC_PLAN} · DB 적재 {stamp_txt(s_plan)}")
            else:
                chart_title("FSC 상위 군급", "건 · 상위 8")
                st.info("이 조건에는 국외 조달계획 행이 없습니다(0건).")

    # ── 국산화 상태 ────────────────────────────────────────────────────────────
    with zone("loc", "국산화 상태"):
        c1, c2 = st.columns([1.5, 1], gap="medium")
        b2_fsg = b2.groupby("fsg")["parts"].sum()
        loc_rows = [(f"FSG {g} {fsg_name.get(g, '')}", float(b2_fsg.get(g, 0)), FSG_C[g]) for g in FSGS if g in g_pick]
        with c1.container(border=True, key="card_loc"):
            tot_loc = sum(v for _, v, _ in loc_rows)
            l_top = max(loc_rows, key=lambda r: r[1]) if loc_rows else None
            t_loc = (f"국산화 완료 부품이 가장 많은 군급 그룹은 "
                     f'<span class="key">{escape(l_top[0])} {pct(l_top[1], tot_loc):.0f}%</span>') if l_top and tot_loc else "전자 군급 국산화 완료 부품 — 군급 그룹별"
            chart_title(t_loc, "부품 수(FSC4 합) · 조각에 커서를 올려 보세요")
            hover_donut(loc_rows, f"{tot_loc:,.0f}", "국산화 완료 부품(FSC4 합)", value_unit="개", height=430)
            if tot_loc:
                png_button(pie_fig([r for r in loc_rows if r[1] > 0], f"{tot_loc:,.0f}<br>국산화 완료 부품"),
                           f"국산화완료부품_FSG_{tag}", align="flex-start", title=t_loc, source=SRC_B2)
            chart_source(f"{SRC_B2} · DB 적재 {stamp_txt(s_b2)}")
        c2.html(rules_card("읽는 법", [
            ("국산화율이 아닙니다", f"지상 {d['all_projects']}개 사업에서 국산화개발을 마친 부품 수이며 비율 지표가 아닙니다."),
            ("조각 크기 = 부품 수", "금액이 아니라 부품(part_mgmt_no) 개수 기준입니다. FSC4별로 센 뒤 더해 고유 수와 조금 다를 수 있습니다."),
            ("조달계획과 연결하지 않습니다", "같은 군급 축에 나란히 놓을 뿐, 한쪽이 많다고 「국산화가 부족하다」는 뜻이 아닙니다."),
        ]))

    # ── 국산화 상위 군급 · 군별 ────────────────────────────────────────────────
    with zone("eq", "국산화 상위 군급 · 군별"):
        c1, c2 = st.columns([1, 1.3], gap="medium")
        top_b2 = by_fsc[by_fsc["parts"] > 0].nlargest(5, "parts")
        if not top_b2.empty:
            b0 = top_b2.iloc[0]
            c1.html(rank_card(f"국산화 완료 부품이 가장 많은 군급은 "
                              f'<span class="key">{escape(str(b0.fsc4))} {escape(str(b0["name"]))}({int(b0.parts):,}개)</span>',
                              "국산화개발품목(B2) · 상위 5 군급 · 적용장비 이름은 싣지 않습니다",
                              [(f"{f} {n}", float(v), SERIES[i % len(SERIES)]) for i, (f, n, v) in
                               enumerate(zip(top_b2["fsc4"], top_b2["name"], top_b2["parts"]))], "부품 수"))
            chart_source(f"{SRC_B2} · DB 적재 {stamp_txt(s_b2)}", where=c1)
        else:
            c1.info("이 조건에는 국산화 완료 부품이 없습니다(0개).")
        with c2.container(border=True, key="card_army"):
            yr = plan.groupby(["year", "army_name"]).size().unstack(fill_value=0)
            a_tot = int(yr.to_numpy().sum())
            if a_tot:
                a_sum = yr.sum().sort_values(ascending=False)
                t_army = (f"{yr_txt} 국외 조달계획 {a_tot:,}건 중 {escape(str(a_sum.index[0]))} 몫이 "
                          f'<span class="key">{pct(a_sum.iloc[0], a_tot):.0f}%</span>로 가장 크다')
            else:
                t_army = "연도별 군별 조달계획"
            chart_title(t_army, f"건 · 요구연도 {yr_txt} · 소요군별")
            fig = go.Figure()
            for a in [a for a in ARMY_C if a in yr.columns]:
                fig.add_trace(go.Bar(x=yr.index.astype(str), y=yr[a], name=a,
                                     marker=dict(color=ARMY_C[a], line=dict(color="#fff", width=1)),
                                     hovertemplate=f"%{{x}}년 {a} %{{y:,}}건<extra></extra>"))
            fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.14), height=330, xaxis=dict(type="category"))
            chart(fig, f"조달계획_연도군별_{tag}", "p2_army_bar", title=t_army, source=SRC_PLAN)
            g = d["gap"]
            st.html(f'<div class="caption">원자료가 2018~2020년에 비어 있는 구간(전체 {g["n"]:,}행 중 2018 {g["y18"]:,} · '
                    f'2019 {g["y19"]:,} · 2020 {g["y20"]:,}건)이라 「조달 없음 · 감소」로 읽지 않습니다.</div>')
            chart_source(f"{SRC_PLAN} · DB 적재 {stamp_txt(s_plan)}")

    # ── 군급별 나란히(대칭 막대) · 표 · CSV ─────────────────────────────────────
    with zone("pair", "군급별 국외 조달계획 · 국산화 완료"):
        top = by_fsc.assign(key=by_fsc["plan_n"] + by_fsc["parts"]).nlargest(15, "key").sort_values("plan_n")
        labels = [f"{f} {n}" for f, n in zip(top["fsc4"], top["name"])]
        lim = float(max(top["plan_n"].max(), top["parts"].max())) * 1.25 or 1
        with st.container(border=True, key="card_pair"):
            pp, pb = top.loc[top["plan_n"].idxmax()], top.loc[top["parts"].idxmax()]
            t_pair = (f"상위 {len(top)} 군급 중 조달계획이 가장 많은 군급은 {escape(str(pp.fsc4))} {escape(str(pp['name']))}, "
                      f'국산화 완료 부품이 가장 많은 군급은 <span class="key">{escape(str(pb.fsc4))} {escape(str(pb["name"]))}</span>')
            chart_title(t_pair, "왼쪽 국외 조달계획(건) · 오른쪽 국산화 완료 부품(개) · 같은 축에 나란히 둘 뿐 연결 · 비율 아님")
            fig = go.Figure()
            fig.add_trace(go.Bar(y=labels, x=-top["plan_n"], orientation="h", name="국외 조달계획(건)", marker_color=PLAN_C,
                                 customdata=top["plan_n"], text=top["plan_n"].astype(int), textposition="outside", cliponaxis=False,
                                 hovertemplate="%{y}<br>국외 조달계획 %{customdata:,}건<extra></extra>"))
            fig.add_trace(go.Bar(y=labels, x=top["parts"], orientation="h", name="국산화 완료 부품(개)", marker_color=B2_C,
                                 text=top["parts"].astype(int), textposition="outside", cliponaxis=False,
                                 hovertemplate="%{y}<br>국산화 완료 부품 %{x:,}개<extra></extra>"))
            fig.update_layout(barmode="overlay", bargap=0.3, height=30 * len(top) + 160,
                              xaxis=dict(range=[-lim, lim], tickvals=[-lim * 0.7, 0, lim * 0.7],
                                         ticktext=[f"{lim * 0.7:,.0f}건", "0", f"{lim * 0.7:,.0f}개"]),
                              legend=dict(orientation="h", y=1.08), margin=dict(l=280, r=40, t=30, b=8))
            chart(fig, f"군급별_조달계획_국산화_{tag}", "p2_pair_bar", title=t_pair, source=f"{SRC_PLAN} · {SRC_B2}")
            chart_source(f"{SOURCE_LINE} · 조달계획 DB 적재 {stamp_txt(s_plan)} · 국산화개발품목 DB 적재 {stamp_txt(s_b2)}")
        tbl = by_fsc.sort_values(["plan_n", "parts"], ascending=False)
        view = pd.DataFrame({"FSC": tbl["fsc4"], "군급 명칭": tbl["name"], "국외 조달계획(건)": tbl["plan_n"].astype(int),
                             "적용장비(종)": tbl["eq_n"].astype(int), "국산화 완료 부품(개)": tbl["parts"].astype(int),
                             "국산화 사업 수": tbl["projects"].astype(int)})
        with st.container(border=True, key="card_ptbl"):
            n_both = int(((view["국외 조달계획(건)"] > 0) & (view["국산화 완료 부품(개)"] > 0)).sum())
            chart_title(f'전자 군급 {len(view)}개 중 두 자료에 모두 나오는 군급은 <span class="key">{n_both}개</span>',
                        "건 · 개 · 조달계획 건수 내림차순 · 0 = 「이 자료에 없음」")
            st.dataframe(view, hide_index=True, width="stretch", height=min(38 + 35 * len(view), 420))
            head = csv_header(
                f"FSG {','.join(g_pick)} · 소요군 {','.join(a_pick)}(조달계획에만 적용)",
                "방위사업청 국외 조달계획 OpenAPI(15158418) → clean_dapa_overseas_plan_api(is_elec=1) · "
                "국방전자조달 국산화개발품목(15119899) → clean_dapa_localized_item(is_electronic_group=1)",
                [("국외 조달계획", s_plan, f"요구연도 {yr_txt}(원자료 2018~2020 공백)" if years else None), ("국산화개발품목", s_b2, None)],
                extra="건수 = 조달계획 행 수(조달요구번호 × 품목순번) · 부품 수 = part_mgmt_no 고유 · 두 자료는 합산·비교하지 않음")
            st.download_button("군급 표 CSV 내려받기", (head + view.to_csv(index=False)).encode("utf-8-sig"),
                               file_name=f"fsc_plan_localized_FSG{'-'.join(g_pick)}.csv", mime="text/csv", key="p2_csv",
                               icon=":material/download:", type="primary")
            chart_source(f"{SOURCE_LINE} · 조달계획 DB 적재 {stamp_txt(s_plan)} · 국산화개발품목 DB 적재 {stamp_txt(s_b2)}")

# ══ 국내 조달(부록) ══════════════════════════════════════════════════════════
dm = load_domestic()
o = dm["one"]
m = dm["method"]
n_con = int(m["n"].sum())
priv = int(m.loc[m["m"].str.contains("수의", na=False), "n"].sum())
bid = dm["bid"].set_index("r")
keys_tot = int(bid["keys_n"].sum())
fail_keys = int(bid["keys_n"].get("유찰", 0))
nt = dm["notice"].set_index("s")["n"]
n_notice = int(nt.sum())

st.html('<div class="lede" style="margin-top:18px"><div class="note">부록 — 방위사업청 <b>국내조달</b> 계약정보 · 입찰공고 · 입찰결과를 '
        '<b>건수</b>로만 봅니다. 금액은 쓰지 않습니다 — 공고 예산 ≠ 낙찰금액 ≠ 계약금액. '
        'HS 품목군·관세청 수입액과는 연결하지 않고, 위 전자 군급 자료의 근거도 아닙니다(조달 방식의 배경).</div></div>')
with zone("dkpi", "국내 조달 핵심 지표"):
    st.html('<div class="kpis">'
            + kpi("국내 계약", f"{n_con:,}", "건", f"계약 단위(최종 차수) · 정제 행 {o['rows_all']:,}")
            + kpi("수의계약 비중", f"{priv / n_con * 100:.1f}", "%",
                  f"{priv:,} / {n_con:,}계약 · 국외조달은 {o['ov_priv'] / o['ov_n'] * 100:.1f}%")
            + kpi("입찰공고", f"{n_notice:,}", "건", f"2024 {o['n24']:,} · 2025 {o['n25']:,}")
            + kpi("경쟁입찰 유찰률", f"{fail_keys / keys_tot * 100:.1f}", "%", f"유찰 {fail_keys:,} / 공고 키 {keys_tot:,}")
            + kpi("낙찰업체", f"{o['winners']:,}", "개", "사업자번호 기준(입찰결과)")
            + "</div>")
    chart_source(f'{DOM_SOURCE} · 계약 {s_con["period"]} · DB 적재 {stamp_txt(s_con)}')

with zone("dmethod", "계약 방법"):
    c1, c2 = st.columns([1.4, 1], gap="medium")
    src_con = f'방위사업청 국내조달 계약정보(15050920) → clean_dapa_contract(is_latest_seq=1) · 계약 {s_con["period"]} · DB 적재 {stamp_txt(s_con)}'
    with c1.container(border=True, key="card_dmethod"):
        t_meth = (f"국내 계약 {n_con:,}건 중 가장 많은 계약 방법은 "
                  f'<span class="key">{escape(str(m.iloc[0].m))}({pct(m.iloc[0].n, n_con):.1f}%)</span>') if not m.empty else "계약 체결 방법별 건수"
        chart_title(t_meth, "계약 · 계약 단위(최종 차수)")
        chart(hbar([(r.m, int(r.n), SERIES[i % len(SERIES)]) for i, r in enumerate(m.itertuples())], 300, "계약"),
              "국내조달_계약방법", "p2_dmethod", title=t_meth, source=src_con)
        chart_source(src_con)
    with c2.container(border=True, key="card_dpriv"):
        chart_title(f'수의계약 비중은 국내 <span class="key">{pct(priv, n_con):.1f}%</span> · 국외 {pct(o["ov_priv"], o["ov_n"]):.1f}%',
                    "% · 계약 수 기준 · 점선 = 50%")
        st.html(pct_rows([("국내조달", pct(priv, n_con), SERIES[2]), ("국외조달", pct(o["ov_priv"], o["ov_n"]), SERIES[0])])
                + f'<div class="caption">국내 {priv:,} / {n_con:,}계약 · 국외 {o["ov_priv"]:,} / {o["ov_n"]:,}계약. '
                  '국내는 소액·소기업 사유가 대부분이라 비중 차이를 곧 진입 장벽으로 읽지 않습니다.</div>')
        chart_source(f"{src_con} · 국외조달 계약정보 → clean_dapa_overseas_contract")

with zone("dreason", "수의계약 사유"):
    c1, c2 = st.columns([1.4, 1], gap="medium")
    rs = dm["reason"][dm["reason"]["g"] != "해당 없음(경쟁계약)"].reset_index(drop=True)
    rsn = {r.g: int(r.n) for r in rs.itertuples()}
    rows = [(r.g, int(r.n), ETC if r.g in ("기타", "사유 미기재") else SERIES[i % len(SERIES)]) for i, r in enumerate(rs.itertuples())]
    with c1.container(border=True, key="card_dreason"):
        r_tot = sum(rsn.values())
        t_rsn = (f"수의계약 {r_tot:,}계약 중 가장 많은 사유는 "
                 f'<span class="key">{escape(str(rs.iloc[0].g))}({pct(rs.iloc[0].n, r_tot):.0f}%)</span>') if not rs.empty and r_tot else "수의계약 사유 그룹"
        chart_title(t_rsn, "계약 · 계약번호당 1행")
        src_rsn = f"{src_con} · 사유 그룹 = v_contract_private_reason"
        chart(hbar(rows, 340, "계약"), "국내조달_수의계약사유", "p2_dreason", title=t_rsn, source=src_rsn)
        chart_source(src_rsn)
    c2.html(rules_card("사유를 읽는 법", [
        (f"경쟁 실패 후 수의 {rsn.get('경쟁실패 후 수의', 0):,}계약", "재공고·1인 입찰·공고 후 수의 — 조달 지연의 간접 신호."),
        (f"단일공급·호환성·특허 {rsn.get('단일공급·호환성·특허', 0):,}계약", "공급자가 한정된 경우. 진입 장벽 신호는 여기까지로 한정합니다."),
        (f"소액·소기업 {rsn.get('소액·소기업', 0):,}계약", "추정가격 기준 소액·소기업 사유 — 진입 장벽 신호가 아닙니다."),
    ]))

with zone("dbid", "입찰 결과"):
    c1, c2 = st.columns([1.2, 1], gap="medium")
    bid_c = {"개찰완료": SERIES[0], "유찰": SERIES[3], "순위확정": SERIES[1]}   # 파랑 · 옅은 파랑 · 하늘(조각끼리 구분)
    bid_rows = [(r, float(bid.at[r, "rows_n"]), bid_c[r]) for r in ("개찰완료", "유찰", "순위확정") if r in bid.index]
    src_bid = f'방위사업청 국내 입찰결과(파일데이터) → clean_dapa_bid_result · DB 적재 {stamp_txt(data_stamp("dapa_bid_result", "clean_dapa_bid_result"))}'
    with c1.container(border=True, key="card_dbid"):
        tot_bid = sum(v for _, v, _ in bid_rows)
        b_top = max(bid_rows, key=lambda r: r[1]) if bid_rows else None
        t_bid = (f"국내 경쟁입찰 개찰 결과 {tot_bid:,.0f}행 중 가장 많은 결과는 "
                 f'<span class="key">{escape(b_top[0])}({pct(b_top[1], tot_bid):.0f}%)</span>') if b_top and tot_bid else "국내 경쟁입찰 개찰 결과"
        chart_title(t_bid, "결과 행 · 조각에 커서를 올려 보세요")
        hover_donut(bid_rows, f"{tot_bid:,.0f}", "개찰 결과 행", value_unit="행", height=430)
        png_button(pie_fig(bid_rows, f"{tot_bid:,.0f}<br>개찰 결과 행"), "국내조달_개찰결과", align="flex-start",
                   title=t_bid, source=src_bid)
        chart_source(src_bid)
    urgent = int(nt.get("긴급", 0))
    with c2.container(border=True, key="card_dref"):
        chart_title(f'국내 공고 중 긴급 공고는 {pct(urgent, n_notice):.1f}%, 경쟁입찰 유찰은 공고 키의 '
                    f'<span class="key">{pct(fail_keys, keys_tot):.1f}%</span>', "% · 서로 단위가 달라 한 줄로 비교하지 않습니다")
        st.html(pct_rows([("긴급 공고(국내)", pct(urgent, n_notice), SERIES[3]), ("유찰(국내, 공고 키)", pct(fail_keys, keys_tot), SERIES[0])])
                + f'<div class="caption" style="margin-top:10px">긴급 공고 {urgent:,} / {n_notice:,} · 유찰 {fail_keys:,} / {keys_tot:,} 공고 키 · '
                  f'재공고 {int(nt.get("재공고", 0)):,} · 취소 {int(nt.get("취소", 0)):,}.<br>'
                  '국외조달 입찰결과는 부분연도라 연간 유찰률로 쓰지 않고 국내와 나란히 두지 않습니다. 낙찰금액 ≠ 계약금액.</div>')
        chart_source("방위사업청 국내 입찰공고 → clean_dapa_bid_notice · 입찰결과 → clean_dapa_bid_result")
    agg = pd.concat([
        pd.DataFrame({"구분": "계약 방법(계약)", "항목": m["m"], "건수": m["n"].astype(int)}),
        pd.DataFrame({"구분": "수의계약 사유 그룹(계약)", "항목": dm["reason"]["g"], "건수": dm["reason"]["n"].astype(int)}),
        pd.DataFrame({"구분": "개찰 결과(행)", "항목": bid.index, "건수": bid["rows_n"].astype(int).values}),
        pd.DataFrame({"구분": "개찰 결과(공고 키)", "항목": bid.index, "건수": bid["keys_n"].astype(int).values}),
        pd.DataFrame({"구분": "공고 상태(공고)", "항목": nt.index, "건수": nt.astype(int).values})])
    head = csv_header(f'국내 조달 전체({s_con["period"]}) · 건수만(금액 미사용)', DOM_SOURCE,
                      [("국내 계약", s_con, None), ("입찰공고", data_stamp("dapa_bid_notice", "clean_dapa_bid_notice"), None)],
                      extra="계약 = clean_dapa_contract is_latest_seq=1 · 사유 = v_contract_private_reason · 유찰률 = 유찰 공고 키 ÷ 공고 키")
    st.download_button("국내 조달 집계 CSV 내려받기", (head + agg.to_csv(index=False)).encode("utf-8-sig"),
                       file_name="domestic_procurement_counts.csv", mime="text/csv", key="p2_dom_csv",
                       icon=":material/download:", type="primary")

chart_source(f"{SOURCE_LINE} · {DOM_SOURCE}")
