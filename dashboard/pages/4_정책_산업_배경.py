"""④ 정책·산업 배경 — 예산 · 국외조달 계획 · 국내 생산 기반. 수출입 현황 화면(①·③)의 배경 축.

데이터 판정: docs/report/data/data-usage-decision-2026-09-18.md §1 보조 · §3 국내 생산 기반.
- 예산: v_budget_rnd_yearly(열린재정 세부사업, 방위사업청 일반회계, 억 원). 2027은 정부안 — 확정액과 구분해 표시.
- 국외조달 계획: v_overseas_plan_yearly(A7 파일판 정제본, 원화 계획액). 계획 ≠ 계약. 관세청 수입액(달러 실적)과
  합산 · 비율 · 같은 축 비교를 하지 않는다(docs/idea-review.md §3-15).
- 국내 생산 기반: KOSIS 방산 분야별 가동률(raw_kosis_utilization) · 방산업체 지정(v_defense_company_sector) ·
  KOSIS 광공업생산지수 C26·C261·C262·C264(raw_kosis_production_index, 2020=100). 생산지수 stat_ym 의 「p)」는 잠정치 표시라
  떼어 내고 잠정 구간으로 음영 처리한다. 가동률 · 지정 업체 수는 생산 능력이 아니며 수입 증감과 인과로 쓰지 않는다.
- 국방반도체 발전전략: data/reference/semi_*.csv 6개(방위사업청 2024-11-19 일반본 PDF와 후속 보도를 손으로 옮긴 참조표, DB 미적재).
  근거 · 열 설명: docs/report/data/policy-pdf-analysis-2026-09-19.md §11 · §12. 7대 유형의 관련 HS6 은 문서에 없는 팀 판단이라
  범례로만 보여 주고 수입액과 잇거나 합산하지 않는다. 공공 팹 좌표는 근사값, 국내 사례는 언론 보도 기준(기업 발표 포함).
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import query
from ui import ACCENT, BG, ETC, MUTED, PANEL2, TEXT, dark_geo, kpi, style_fig, zone

SERIES = ["#5b9bff", "#f2b33d", "#2ec4b6", "#b07cff", "#ff8fab"]
HIGHLIGHT = "통신전자"   # 방산 분야 중 전자부품과 가장 가까운 분야 — 강조색, 나머지는 회색
DIM = "#3a4560"
REF = Path(__file__).resolve().parents[2] / "data" / "reference"   # 수작업 참조표(semi_*.csv)
SEMI_FILES = ("chip_type", "strategy_task", "public_fab", "market_share", "policy_timeline", "domestic_case")


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> dict:
    budget = query("SELECT * FROM v_budget_rnd_yearly ORDER BY fiscal_year")
    plan = query("""
        SELECT plan_year, exec_type, plan_count, budget_krw, elec_candidate_count
        FROM v_overseas_plan_yearly ORDER BY plan_year
    """)
    util = query("SELECT sector_name, year, value_text FROM raw_kosis_utilization")
    comp = query("SELECT sector, company_count FROM v_defense_company_sector")
    prod = query("""
        SELECT industry_name, stat_ym, value_text FROM raw_kosis_production_index
        WHERE region_name LIKE :r AND item_name LIKE :i
    """, {"r": "00%", "i": "T20%"})   # 전국 · 계절조정
    return dict(budget=budget, plan=plan, util=util, comp=comp, prod=prod)


@st.cache_data(ttl=3600, show_spinner=False)
def load_semi() -> dict | None:
    """국방반도체 발전전략 참조표. 파일이 하나라도 없으면 None — 구역만 비우고 나머지 화면은 그린다."""
    try:
        return {n: pd.read_csv(REF / f"semi_{n}.csv", dtype=str).fillna("") for n in SEMI_FILES}
    except FileNotFoundError:
        return None


d = load()
st.html('<div class="page-h">④ 정책 · 산업 배경</div>'
        '<div class="note">수출입 현황의 배경 — 정부 예산, 방위사업청 국외조달 계획, 국내 생산 기반. '
        '각 자료는 단위 · 기준이 달라 서로 합하거나 관세청 수입액과 직접 비교하지 않습니다.</div>')

# ── 1. 예산 ─────────────────────────────────────────────────────────────────
b = d["budget"].copy()
b["year"] = b["fiscal_year"].astype(int)
fixed = b[b["amount_basis"] == "확정"]
first, last = fixed.iloc[0], fixed.iloc[-1]
loc_years = b.loc[b["localization_gov_100m"] > 0, "year"]
semi = b[b["semiconductor_gov_100m"] > 0]
with zone("p4_budget", "국방 R&D · 부품국산화 예산"):
    st.html('<div class="kpis k4">'
            + kpi(f"{last.year} 국방기술개발 예산", f"{last.tech_dev_gov_100m / 1e4:,.2f}", "조 원",
                  f"{first.year}년 {first.tech_dev_gov_100m / 1e4:,.2f}조 → {last.tech_dev_gov_100m / first.tech_dev_gov_100m:.1f}배")
            + kpi(f"{last.year} 부품국산화 예산", f"{last.localization_gov_100m:,.0f}", "억 원",
                  f"{loc_years.min()}년부터 세부사업으로 편성" if not loc_years.empty else "편성 없음")
            + (kpi("국방반도체 예산", f"{semi.iloc[0].semiconductor_gov_100m:,.0f}", "억 원",
                   f"{semi.iloc[0].year}년 {semi.iloc[0].amount_basis}에 처음 편성",
                   "정부안" if semi.iloc[0].amount_basis != "확정" else "")
               if not semi.empty else kpi("국방반도체 예산", "—", "", "편성 없음"))
            + kpi(f"{last.year} 방위사업청 일반회계", f"{last.total_gov_100m / 1e4:,.1f}", "조 원", "세부사업 합계 · 비교 기준선")
            + "</div>")
    c1, c2 = st.columns([1.6, 1], gap="medium")
    fig = go.Figure()
    for col, name, color in (("tech_dev_gov_100m", "국방기술개발", SERIES[0]), ("localization_gov_100m", "부품국산화", SERIES[1]),
                             ("semiconductor_gov_100m", "국방반도체", SERIES[2]), ("supply_chain_gov_100m", "공급망", SERIES[3])):
        s = b[b[col] > 0]
        if s.empty:
            continue
        fig.add_trace(go.Bar(x=s["year"], y=s[col], name=name, marker=dict(
            color=color, opacity=[0.45 if basis != "확정" else 1 for basis in s["amount_basis"]], line=dict(color=BG, width=1)),
            hovertemplate=f"{name} %{{x}}년<br>%{{y:,.0f}}억 원<extra></extra>"))
    fig.update_layout(barmode="group", title="세부사업 예산(억 원) · 흐린 막대 = 정부안", xaxis=dict(dtick=1),
                      yaxis=dict(title="억 원"), legend=dict(orientation="h", y=-0.15, title=None), margin=dict(t=50, b=30))
    c1.plotly_chart(style_fig(fig, 380), width="stretch", theme=None)
    share = b.assign(pct=b["tech_dev_gov_100m"] / b["total_gov_100m"] * 100)
    fig2 = go.Figure(go.Scatter(x=share["year"], y=share["pct"], mode="lines+markers", line=dict(color=ACCENT, width=2),
                                hovertemplate="%{x}년 %{y:.1f}%<extra></extra>"))
    fig2.update_layout(title="일반회계 중 국방기술개발 비중(%)", xaxis=dict(dtick=2), yaxis=dict(rangemode="tozero"),
                       margin=dict(t=50, b=30), showlegend=False)
    c2.plotly_chart(style_fig(fig2, 380), width="stretch", theme=None)
    st.html('<div class="note">출처: 열린재정 세부사업 예산편성현황(방위사업청 · 일반회계). 억 원 · 정부 예산 기준. '
            f'{b.iloc[-1].year}년은 {b.iloc[-1].amount_basis} — 확정 전 값입니다.</div>')

# ── 2. 국외조달 계획 ─────────────────────────────────────────────────────────
p = d["plan"].copy()
with zone("p4_plan", "방위사업청 국외조달 계획"):
    yearly = p.groupby("plan_year", as_index=False).agg(n=("plan_count", "sum"), krw=("budget_krw", "sum"),
                                                        elec=("elec_candidate_count", "sum"))
    c1, c2 = st.columns(2, gap="medium")
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=yearly["plan_year"], y=yearly["krw"] / 1e8, name="계획 예산(억 원)", marker_color="#35507f",
                          hovertemplate="%{x}년 %{y:,.0f}억 원<extra></extra>"))
    fig3.add_trace(go.Scatter(x=yearly["plan_year"], y=yearly["n"], name="계획 건수", yaxis="y2", mode="lines+markers",
                              line=dict(color=SERIES[1], width=2), hovertemplate="%{x}년 %{y:,.0f}건<extra></extra>"))
    fig3.update_layout(title="연도별 국외조달 계획 — 예산(막대) · 건수(선)", yaxis=dict(title="억 원"),
                       yaxis2=dict(title="건", overlaying="y", side="right", showgrid=False, rangemode="tozero"),
                       legend=dict(orientation="h", y=-0.15, title=None), margin=dict(t=50, b=30))
    c1.plotly_chart(style_fig(fig3, 360), width="stretch", theme=None)
    keep = p.groupby("exec_type")["plan_count"].sum().sort_values(ascending=False).index[:5].tolist()
    mix = (p.assign(grp=p["exec_type"].where(p["exec_type"].isin(keep), "기타"))
           .groupby(["plan_year", "grp"])["plan_count"].sum().unstack(fill_value=0))
    fig4 = go.Figure()
    for g, color in zip(keep + ["기타"], SERIES + [ETC]):
        if g in mix.columns:
            fig4.add_trace(go.Bar(x=mix.index, y=mix[g], name=g, marker=dict(color=color, line=dict(color=BG, width=1)),
                                  hovertemplate=f"%{{x}}년 {g} %{{y}}건<extra></extra>"))
    fig4.update_layout(barmode="stack", title="집행유형별 계획 건수", legend=dict(orientation="h", y=-0.15, title=None),
                       margin=dict(t=50, b=30))
    c2.plotly_chart(style_fig(fig4, 360), width="stretch", theme=None)
    st.html('<div class="note">· 원화 <b>계획</b> 예산(집행 예정액)이며 계약 · 집행 실적이 아닙니다. 관세청 수입액(달러 실적)과 합산 · 비교하지 않습니다<br>'
            f'· 대표품명 키워드로 뽑은 전자 관련 후보는 {int(yearly.elec.sum()):,}건(잠정 — 검수 전)<br>'
            '· 출처: 방위사업청 국외조달 조달계획(파일 데이터) → 팀 정제본</div>')

# ── 3. 국내 생산 기반 ────────────────────────────────────────────────────────
with zone("p4_base", "국내 생산 기반"):
    u = d["util"].assign(v=lambda x: pd.to_numeric(x["value_text"], errors="coerce")).dropna(subset=["v"])
    c1, c2 = st.columns([1.3, 1], gap="medium")
    fig5 = go.Figure()
    for sector, g in u.groupby("sector_name"):
        hi, avg = sector == HIGHLIGHT, sector == "평균"
        fig5.add_trace(go.Scatter(
            x=g["year"], y=g["v"], name=sector, mode="lines+markers" if hi or avg else "lines", showlegend=hi or avg,
            line=dict(color=SERIES[0] if hi else (TEXT if avg else DIM), width=3 if hi else (2 if avg else 1),
                      dash="dot" if avg else "solid"),
            hovertemplate=f"{sector} %{{x}}년 %{{y:.1f}}%<extra></extra>"))
    fig5.update_layout(title=f"방산 분야별 가동률(%) — {HIGHLIGHT} 강조 · 점선 = 평균 · 회색 = 다른 분야", yaxis=dict(title="%"),
                       legend=dict(orientation="h", y=-0.15, title=None), margin=dict(t=50, b=30))
    c1.plotly_chart(style_fig(fig5, 360), width="stretch", theme=None)
    comp = d["comp"][d["comp"]["sector"] != "미기재"].sort_values("company_count")
    fig6 = go.Figure(go.Bar(x=comp["company_count"], y=comp["sector"], orientation="h",
                            marker_color=[SERIES[0] if s == HIGHLIGHT else DIM for s in comp["sector"]],
                            text=comp["company_count"], textposition="outside", textfont=dict(color=MUTED), cliponaxis=False,
                            hovertemplate="%{y} %{x}개사<extra></extra>"))
    fig6.update_layout(title=f"분야별 방산업체 지정 수(총 {int(d['comp']['company_count'].sum())}개사)",
                       margin=dict(t=50, b=30, r=30), showlegend=False)
    c2.plotly_chart(style_fig(fig6, 360), width="stretch", theme=None)

    pr = d["prod"].copy()
    pr["prelim"] = pr["stat_ym"].str.contains("p", case=False)
    pr["ym"] = pd.to_datetime(pr["stat_ym"].str.extract(r"(\d{4}\.\d{2})")[0], format="%Y.%m")
    pr["v"] = pd.to_numeric(pr["value_text"], errors="coerce")
    pr["code"] = pr["industry_name"].str.split().str[0]
    labels = {"C26": "C26 전자부품·컴퓨터·통신 전체", "C261": "C261 반도체", "C262": "C262 전자부품", "C264": "C264 통신·방송장비"}
    fig7 = go.Figure()
    for code, color in zip(labels, SERIES):
        g = pr[pr["code"] == code].sort_values("ym")
        if not g.empty:
            fig7.add_trace(go.Scatter(x=g["ym"], y=g["v"], name=labels[code], mode="lines",
                                      line=dict(color=color, width=2.5 if code == "C262" else 1.5),
                                      hovertemplate=f"{labels[code]} %{{x|%Y-%m}}<br>%{{y:.1f}}<extra></extra>"))
    fig7.add_hline(y=100, line=dict(color=MUTED, dash="dot", width=1))
    p0 = pr.loc[pr["prelim"], "ym"].min()
    if pd.notna(p0):
        fig7.add_vrect(x0=p0, x1=pr["ym"].max(), fillcolor=PANEL2, opacity=0.9, line_width=0, layer="below",
                       annotation_text="잠정치(p)", annotation_position="top left", annotation_font=dict(color=MUTED, size=11))
    fig7.update_layout(title="광공업생산지수(계절조정, 2020=100) — 전국", yaxis=dict(title="지수"),
                       legend=dict(orientation="h", y=-0.15, title=None), hovermode="x unified", margin=dict(t=50, b=30))
    st.plotly_chart(style_fig(fig7, 380), width="stretch", theme=None)
    st.html('<div class="note">· 가동률 · 지정 업체 수는 조사 · 지정 기준 값이며 생산 능력이나 국산화 수준을 뜻하지 않습니다. 수입 증감과 인과로 읽지 않습니다<br>'
            '· 생산지수는 방산에 한정되지 않은 민수 포함 산업 지표입니다. 수입액과 비교할 때는 지수끼리만 봅니다(이중 축 금지)<br>'
            '· 출처: KOSIS 방산업체 경영분석(409) 분야별 평균가동률 · 방위사업청 방산업체 지정현황 · '
            'KOSIS 광업제조업동향조사(101) 시도/산업별 광공업생산지수</div>')

# ── 4. 국방반도체 발전전략 ───────────────────────────────────────────────────
sm = load_semi()
with zone("p4_semi", "국방반도체 발전전략 · 국내 기반"):
    if sm is None:
        st.html('<div class="note">참조표(data/reference/semi_*.csv)를 찾지 못해 이 구역을 비웠습니다.</div>')
    else:
        fab = sm["public_fab"].astype({"lat": float, "lon": float})
        case, ctype = sm["domestic_case"], sm["chip_type"]
        comp_fab = fab[fab["field_group"] == "화합물"]
        st.html('<div class="kpis k4">'
                + kpi("무기체계 적용 반도체 해외 도입", "98.9", "%", "54개 무기체계 조사(2023.12) · 산출 기준(종류·수량·금액) 미공개", "인용")
                + kpi("그중 미국 비중", "85", "% 이상", "설계(미국) → 생산(대만) 구조 · 발전전략 원문 인용", "인용")
                + kpi("국방반도체 핵심기술 과제", f"{int((case['dapa_2025_task'] == '1').sum())}", "건",
                      "2025.5 최초 선정 · 「100대 국방반도체」는 2026년 말 수립 예정")
                + kpi("공공 나노팹 중 화합물반도체 표기", f"{len(comp_fab)}", f"/ {len(fab)}곳",
                      " · ".join(f"{r.name_ko}({r.city})" for r in comp_fab.itertuples()) + " — 그림 표기 기준")
                + "</div>")

        # 4-1. 타임라인 | 4방향 12과제
        c1, c2 = st.columns([1.5, 1], gap="medium")
        tl = sm["policy_timeline"].copy()
        tl["when"] = pd.to_datetime(tl["date"].where(tl["date"].str.len() > 4, tl["date"] + "-01"), format="mixed")   # 「2027」→ 2027-01
        cats = list(dict.fromkeys(tl["category"]))
        palette = dict(zip(cats, SERIES + [ETC, MUTED, TEXT]))
        fig8 = go.Figure()
        for cat, g in tl.groupby("category", sort=False):
            fig8.add_trace(go.Scatter(
                x=g["when"], y=[cat] * len(g), mode="markers", name=cat, marker=dict(size=13, color=palette[cat], line=dict(color=BG, width=1)),
                customdata=g[["date", "event", "detail", "source_title"]],
                hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]}<br><i>%{customdata[3]}</i><extra></extra>"))
        fig8.add_vline(x=pd.Timestamp("2024-11-19"), line=dict(color=ACCENT, dash="dot", width=1))
        fig8.add_annotation(x=pd.Timestamp("2024-11-19"), y=1.06, yref="paper", text="발전전략 발표", showarrow=False,
                            font=dict(color=ACCENT, size=11))
        fig8.update_layout(title="논의 → 전략 → 과제 → 법 → 예산 (점에 마우스를 올리면 내용)", showlegend=False,
                           xaxis=dict(tickformat="%Y.%m"), yaxis=dict(categoryorder="array", categoryarray=cats[::-1]), margin=dict(t=60, b=30))
        c1.plotly_chart(style_fig(fig8, 360), width="stretch", theme=None)
        task = sm["strategy_task"]
        rows = "".join(
            f'<div style="margin-bottom:9px"><b style="color:{color}">{escape(k)}</b> '
            f'<span style="color:{MUTED}">{escape(g["direction_name"].iloc[0])}</span><br>'
            + " · ".join(escape(t) for t in g["task_name"]) + "</div>"
            for (k, g), color in zip(task.groupby("direction_key", sort=False), SERIES))
        c2.html('<div class="card"><div class="h">비전 「2030 첨단반도체 강군 육성을 위한 생태계 구축」'
                '<span class="sub">4방향 · 12과제</span></div>'
                f'<div class="note" style="font-size:12px;line-height:1.7">{rows}</div></div>')

        # 4-2. 7대 유형 × 국내 개발 사례
        n_case = case.groupby("type_no").size()
        tv = pd.DataFrame({
            "유형": ctype["type_no"] + ". " + ctype["name_ko"], "개요": ctype["summary"], "대표 소자": ctype["example_devices"],
            "관련 HS6(팀 판단)": ctype["related_hs6"].str.replace(";", " · ").replace("", "—"),
            "국내 사례(건)": ctype["type_no"].map(n_case).fillna(0).astype(int)})
        st.html('<div class="h" style="margin-top:14px">방위사업청 7대 유형 × 국내 개발 사례'
                '<span class="sub">유형 · 개요는 발전전략 참고9 · 사례는 언론 보도 기준</span></div>')
        st.dataframe(tv, hide_index=True, width="stretch", height=38 + 35 * len(tv), column_config={
            "개요": st.column_config.TextColumn(width="large"),
            "관련 HS6(팀 판단)": st.column_config.TextColumn(help="발전전략 문서에 없는 팀 판단. 유형 ↔ HS6 은 다대다이고 민수를 포함하므로 "
                                                                "수입액과 잇거나 합산하지 않습니다. 센서 · 우주 유형은 현재 품목군에 대응 코드가 없습니다"),
            "국내 사례(건)": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=int(max(n_case.max(), 1)))})
        pick = st.segmented_control("유형", ["전체"] + list(ctype["type_no"] + ". " + ctype["name_ko"]), default="전체",
                                    key="semi_type", label_visibility="collapsed") or "전체"
        cv = case if pick == "전체" else case[case["type_no"] == pick.split(".")[0]]
        cv = cv.merge(ctype[["type_no", "name_ko"]], on="type_no").rename(columns={
            "name_ko": "유형", "org": "주체", "title": "내용", "date": "시점", "target_system": "적용 대상", "stage": "단계",
            "source_url": "출처", "verify_level": "확인 수준", "note": "비고"})
        # 높이는 행 수만큼 다 편다(표 안 세로 스크롤이 페이지 휠을 가로챈다). 확인 수준 · 출처가 잘리지 않게 폭을 정하고 남는 폭은 비고가 받는다
        st.dataframe(cv[["유형", "주체", "내용", "시점", "적용 대상", "단계", "확인 수준", "출처", "비고"]], hide_index=True, width="stretch",
                     height=40 + 35 * len(cv), column_config={
                         "유형": st.column_config.TextColumn(width=150),
                         "주체": st.column_config.TextColumn(width=150),
                         "내용": st.column_config.TextColumn(width=330),
                         "시점": st.column_config.TextColumn(width=90),
                         "적용 대상": st.column_config.TextColumn(width=180),
                         "단계": st.column_config.TextColumn(width=100),
                         "출처": st.column_config.LinkColumn(display_text="기사", width=55),
                         "비고": st.column_config.TextColumn(width=135),
                         "확인 수준": st.column_config.TextColumn(width=100, help="기사 원문 = 원문을 열어 확인 · 검색 요약 = 검색 결과 요약만 확인")})

        # 4-3. 공공 팹 지도 | 국가별 시장점유율
        c1, c2 = st.columns([1, 1.15], gap="medium")
        LABEL_LEFT = {"1", "3", "5", "10"}   # 같은 도시에 둘씩 있는 곳(대전 · 서울 · 전주 · 대구)은 한쪽 라벨을 왼쪽으로
        fig9 = go.Figure()
        for (ministry, color) in (("과기부", SERIES[2]), ("산업부", SERIES[1])):
            g = fab[fab["ministry"] == ministry]
            hi = g["field_group"] == "화합물"
            fig9.add_trace(go.Scattergeo(
                lat=g["lat"], lon=g["lon"], mode="markers+text", name=ministry,
                text=g["abbr"].where(g["abbr"] != "", g["parent_org"]), textfont=dict(color=MUTED, size=10),
                textposition=["middle left" if n in LABEL_LEFT else "middle right" for n in g["fab_no"]],
                marker=dict(size=[16 if h else 10 for h in hi], color=color, opacity=0.9,
                            line=dict(color=[TEXT if h else BG for h in hi], width=[2 if h else 1 for h in hi])),
                customdata=g[["name_ko", "parent_org", "field", "city"]],
                hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]}<extra>" + ministry + "</extra>"))
        dark_geo(fig9)
        fig9.update_geos(projection_type="mercator", lonaxis_range=[124.8, 130.6], lataxis_range=[33.0, 38.9], resolution=50)
        fig9.update_layout(title=f"파운드리 구축 협력 후보 — 공공 나노팹 {len(fab)}곳(흰 테두리 = 화합물반도체)",
                           legend=dict(orientation="h", y=-0.05, title=None), margin=dict(t=50, b=10, l=0, r=0))
        c1.plotly_chart(style_fig(fig9, 430), width="stretch", theme=None)
        ms = sm["market_share"].astype({"share_pct": float})
        fig10 = go.Figure()
        for country, color in (("미국", DIM), ("대만", "#55617f"), ("중국", "#2f384f"), ("한국", ACCENT)):
            g = ms[ms["country"] == country]
            fig10.add_trace(go.Bar(x=g["segment"], y=g["share_pct"], name=country, marker=dict(color=color, line=dict(color=BG, width=1)),
                                   text=g["share_pct"].map(lambda v: f"{v:g}"), textposition="outside",
                                   textfont=dict(color=TEXT if country == "한국" else MUTED, size=10), cliponaxis=False,
                                   hovertemplate=f"{country} %{{x}} %{{y:g}}%<extra></extra>"))
        fig10.update_layout(barmode="group", title="국가별 반도체 분야 시장점유율(%) — 한국 강조", yaxis=dict(title="%", range=[0, 78]),
                            legend=dict(orientation="h", y=-0.12, title=None), margin=dict(t=50, b=30))
        c2.plotly_chart(style_fig(fig10, 430), width="stretch", theme=None)
        st.html('<div class="note">· 98.9% · 85%는 방위사업청 「국방반도체 발전전략」(2024-11-19, 일반본) 본문 인용이며 팀이 계산한 값이 아닙니다. '
                '조사 대상 54개 무기체계의 목록과 산출 기준은 공개되지 않았습니다<br>'
                '· 공공 나노팹은 방위사업청이 파운드리 구축을 <b>협력하겠다고 꼽은 후보</b>(연구 · 시제 규모)이며 현재 국방 협력 기관이라는 뜻이 아닙니다. '
                '좌표는 근사값이고, 수입 통계의 신고 지역과 관계가 없습니다<br>'
                '· 시장점유율은 발전전략 참고3 그래프에서 읽은 값으로 원출처 · 기준연도가 표기돼 있지 않습니다<br>'
                '· 국내 사례는 언론 보도 기준(기업 발표 포함)이며 전수 목록이 아닙니다. 사례 건수는 개발 수준이나 국산화율을 뜻하지 않습니다<br>'
                '· 출처: 방위사업청 「국방반도체 발전전략」 참고3 · 9 · 10, 본문 17-1 · 17-3 · 방위사업청 보도자료(2025-05-19) · 각 기사(표의 출처 열)</div>')

