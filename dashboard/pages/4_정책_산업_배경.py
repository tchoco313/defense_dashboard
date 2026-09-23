"""⓪ 국외조달 예산 추이 · 정책·산업 배경 — 팀원 디자인 데모(K-Defense) 「정책 · 산업 배경」 화면 배치에 RDS 실측값을 채웠다.

① 수출입 현황의 배경 화면이다(수입액을 설명하지 않는다). 데모의 샘플 값(국외조달 예산 BUDGET · 방위력개선비 대비 · 분야별 예산
FIELD_BUDGET · 시·도 지도)은 DB 근거가 없어 쓰지 않고, 같은 자리에 실제 자료로 바꿨다:
- 예산 추이: v_overseas_plan_yearly(A7 국외조달 계획, 원화 계획액) · 방위력개선비 대비 → v_budget_rnd_yearly 국방기술개발 비중(같은 자료 안 비율).
- 분야별 예산 히트맵 → 집행유형 × 계획연도 계획 예산(v_overseas_plan_yearly).
- 국외조달 절차 건수 = clean_dapa_overseas_plan · _bid_result · _contract 행 수(기간 · 단위가 달라 전환율로 읽지 않음).
- 가동률(clean_kosis_utilization) · 세부사업 예산(v_budget_rnd_yearly, 정부안 배지) · 계획 집행유형(v_overseas_plan_yearly) ·
  방산업체 지정(v_defense_company_sector) · 광공업생산지수(clean_kosis_production_index, 잠정치 음영).
- 국방반도체 발전전략: RDS ref_semi_* 7표(원본 data/reference/semi_*.csv 수작업 참조표 → load_db.py --ref, 2026-09-23).
원화 예산 · 계획액은 관세청 수입액(달러 실적)과 합산 · 비율 · 같은 축 비교를 하지 않는다(CLAUDE.md · idea-review §3-15).
모든 plotly 차트 아래 PNG 내려받기(ui.png_button), 표는 CSV(ui.csv_header 머리줄).
"""
from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import data_stamp, query, try_query
from ui import (ACCENT, ETC, MUTED, SERIES, TEXT, chart_source, chart_title, csv_header, dark_geo, globe_loading, hero, kpi,
                png_button, rules_card, style_fig, zone)

HIGHLIGHT = "통신전자"   # 방산 분야 중 전자부품과 가장 가까운 분야 — 강조색
GREY = "#cdd6e4"
# 국방반도체 참조표(RDS ref_semi_*, alter_2026-09-23_semi_ref.sql) — 키 → SELECT. date 열은 DB 에서 event_date
SEMI_SQL = {
    "chip_type": "SELECT type_no, name_ko, summary, material_process, example_devices, related_hs6, hs_basis, source "
                 "FROM ref_semi_chip_type ORDER BY type_no",
    "strategy_task": "SELECT task_no, direction_no, direction_key, direction_name, sub_no, task_name, source "
                     "FROM ref_semi_strategy_task ORDER BY task_no",
    "public_fab": "SELECT fab_no, name_ko, abbr, parent_org, ministry, field, field_group, city, lat, lon, coord_basis, source "
                  "FROM ref_semi_public_fab ORDER BY fab_no",
    "market_share": "SELECT country, segment, share_pct, source, caveat FROM ref_semi_market_share",
    "policy_timeline": "SELECT event_date AS date, category, event, detail, source_title, source_url, verify_level "
                       "FROM ref_semi_policy_timeline ORDER BY row_no",
    "domestic_case": "SELECT case_no, type_no, org, title, event_date AS date, target_system, stage, source_title, source_url, "
                     "verify_level, note, dapa_2025_task FROM ref_semi_domestic_case ORDER BY case_no",
    "stat": "SELECT stat_key, label, value_num, unit_txt, note, source FROM ref_semi_stat",
}
STRATEGY_DAY = pd.Timestamp("2024-11-19")
E8 = 1e8   # 억 원 = 원 ÷ 1e8


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> dict:
    budget = query("SELECT * FROM v_budget_rnd_yearly ORDER BY fiscal_year")
    plan = query("SELECT plan_year, exec_type, plan_count, budget_krw, elec_candidate_count FROM v_overseas_plan_yearly ORDER BY plan_year")
    util = query("SELECT sector_name, year, value_text FROM clean_kosis_utilization")
    comp = query("SELECT sector, company_count FROM v_defense_company_sector")
    prod = query("""SELECT industry_code, stat_month, is_provisional, index_value FROM clean_kosis_production_index
                    WHERE region_name LIKE :r AND item_code = :i""", {"r": "00%", "i": "T20"})
    proc = query("""SELECT (SELECT COUNT(*) FROM clean_dapa_overseas_plan) AS plan_n,
                           (SELECT MIN(plan_year) FROM v_overseas_plan_yearly) AS plan_y0,
                           (SELECT MAX(plan_year) FROM v_overseas_plan_yearly) AS plan_y1,
                           (SELECT COUNT(*) FROM clean_dapa_overseas_bid_result) AS bid_n,
                           (SELECT MIN(opening_ym) FROM clean_dapa_overseas_bid_result) AS bid_y0,
                           (SELECT MAX(opening_ym) FROM clean_dapa_overseas_bid_result) AS bid_y1,
                           (SELECT COUNT(*) FROM clean_dapa_overseas_contract) AS ctr_n,
                           (SELECT MIN(contract_year) FROM clean_dapa_overseas_contract) AS ctr_y0,
                           (SELECT MAX(contract_year) FROM clean_dapa_overseas_contract) AS ctr_y1""")
    return dict(budget=budget, plan=plan, util=util, comp=comp, prod=prod, proc=proc)


def load_semi() -> tuple[dict | None, str | None]:
    """RDS ref_semi_* 7표 → {키: DataFrame(전 열 문자열, NULL = "")}. 실패하면 (None, 오류 클래스명), 한 표라도 비면 (None, "미적재").
    값을 문자열로 맞춘 것은 예전 CSV 직독과 같은 모양을 유지하려는 것(숫자 열은 쓰는 곳에서 float 로 바꾼다)."""
    out = {}
    for key, sql in SEMI_SQL.items():
        df, err = try_query(sql)
        if err:
            return None, err
        if df.empty:
            return None, "미적재"
        out[key] = df.astype(object).where(df.notna(), "").astype(str).apply(no_dep)
    return out, None


def no_dep(col: pd.Series) -> pd.Series:
    """화면 표현 경계 — 인용 원문의 「의존율 · 의존도 · 의존」을 「도입 비중 · 도입」으로 바꿔 보인다(DB 값은 그대로)."""
    return (col.str.replace("의존율", "도입 비중", regex=False).str.replace("의존도", "도입 비중", regex=False)
            .str.replace("의존", "도입", regex=False))


def hbar(rows: list[tuple[str, int, str]], height: int = 300, unit: str = "") -> go.Figure:
    """데모 hbar — 가로 막대 순위(위 = 첫 행)."""
    rows = list(reversed(rows))
    fig = go.Figure(go.Bar(x=[r[1] for r in rows], y=[r[0] for r in rows], orientation="h",
                           marker=dict(color=[r[2] for r in rows], line=dict(color="#fff", width=1)),
                           text=[f"{r[1]:,}" for r in rows], textposition="outside",
                           textfont=dict(size=12.5, color=TEXT), cliponaxis=False,
                           hovertemplate="%{y}<br>%{x:,}" + f" {unit}<extra></extra>"))
    label_w = max(len(str(r[0])) for r in rows) * 11 + 14
    fig.update_layout(height=height, showlegend=False, margin=dict(l=min(label_w, 230), r=48, t=10, b=8))
    return fig


def chart(fig, name: str, cfg: dict | None = None, title: str | None = None, source: str | None = None) -> None:
    """plotly 차트 + 보이는 그림 그대로 PNG 내려받기(결론형 제목 · 출처 한 줄은 PNG 에도 얹는다)."""
    st.plotly_chart(fig, width="stretch", theme=None, config=cfg or {"displaylogo": False})
    png_button(fig, f"배경_{name}", title=title, source=source)


def trend(a: float, b: float, up: str = "늘었다", down: str = "줄었다", same: str = "같다") -> str:
    return up if b > a else down if b < a else same


def caption(text: str) -> None:
    st.html(f'<div class="caption">{text}</div>')


def stamp_txt(name: str, s: dict) -> str:
    failed = s.get("error") and not s.get("has_period") and not s.get("loaded")
    return f'{name} {"—(조회 실패)" if failed else s["period"]} · DB 적재 {s.get("loaded") or "—"}'


def yoy_badge(cur: float, prev: float | None, unit: str = "%") -> str:
    """데모 전년비 표기(▲/▼). unit="%p" 이면 차이, "%" 이면 증감률."""
    if prev is None or pd.isna(prev) or pd.isna(cur) or (unit == "%" and not prev):
        return "전년 값 없음"
    d = cur - prev if unit == "%p" else (cur / prev - 1) * 100
    return f'<span class="{"up" if d >= 0 else "dn"}">{"▲" if d >= 0 else "▼"} {d:+.1f}{unit}</span> 전년 대비'


with globe_loading("팀 DB 에서 배경 자료를 읽는 중"):
    d = load()
s_plan = data_stamp("dapa_overseas_plan", "clean_dapa_overseas_plan")
s_bud = data_stamp("openfiscal_program_budget", "clean_openfiscal_program_budget")
s_util = data_stamp("kosis_utilization", "clean_kosis_utilization")
s_comp = data_stamp("dapa_defense_company", "clean_dapa_defense_company")
s_prod = data_stamp("kosis_production_index", "clean_kosis_production_index")

hero("⓪ 국외조달 예산 · 배경", "국외조달 계획의 예산과 건수, 그 배경인 국방 R&amp;D 예산 · 국내 생산 기반 · 국방반도체 정책을 봅니다",
     stamps=[("국외조달 계획", s_plan), ("열린재정 예산", s_bud), ("KOSIS 가동률", s_util), ("KOSIS 생산지수", s_prod)])
st.html('<div class="lede"><div class="note">수입 현황의 배경 — 정부 예산, 방위사업청 국외조달 계획, 국내 생산 기반. '
        '각 자료는 단위·기준이 달라 서로 합하거나 관세청 수입액과 <b>직접 비교하지 않습니다</b>.</div></div>')

# ── 공통 계산 ────────────────────────────────────────────────────────────────
p = d["plan"].copy()
yearly = (p.groupby("plan_year", as_index=False).agg(n=("plan_count", "sum"), krw=("budget_krw", "sum"),
                                                    elec=("elec_candidate_count", "sum"))
          if not p.empty else pd.DataFrame(columns=["plan_year", "n", "krw", "elec"]))
yearly["year"] = yearly["plan_year"].astype(int)
b = d["budget"].copy()
b["year"] = b["fiscal_year"].astype(int)
b["pct"] = b["tech_dev_gov_100m"] / b["total_gov_100m"] * 100
u = d["util"].assign(v=lambda x: pd.to_numeric(x["value_text"], errors="coerce")).dropna(subset=["v"])
pr = d["prod"].copy()
pr["prelim"] = pr["is_provisional"].astype(int).astype(bool)
pr["ym"] = pd.to_datetime(pr["stat_month"])
pr["v"] = pd.to_numeric(pr["index_value"], errors="coerce")

# ── 1. KPI — 예산 · 조달 ─────────────────────────────────────────────────────
with zone("bkpi", "예산 · 조달"):
    cards = []
    if not yearly.empty:
        r1 = yearly.iloc[-1]
        r0 = yearly.iloc[-2] if len(yearly) > 1 else None
        cards.append(kpi(f"{r1.year} 국외조달 계획 예산", f"{r1.krw / E8:,.0f}", "억 원",
                         yoy_badge(r1.krw, r0.krw if r0 is not None else None) + " · 원화 계획(집행 예정액)"))
        cards.append(kpi(f"{r1.year} 국외조달 계획 건수", f"{int(r1.n):,}", "건",
                         yoy_badge(r1.n, r0.n if r0 is not None else None) + " · 계획 ≠ 계약"))
    else:
        cards.append(kpi("국외조달 계획 예산", "—", "", "자료 없음(미적재)"))
    avg = u[u["sector_name"] == "평균"].sort_values("year")
    if not avg.empty:
        a1, a0 = avg.iloc[-1], (avg.iloc[-2] if len(avg) > 1 else None)
        cards.append(kpi(f"{int(a1.year)} 국내 방산 가동률", f"{a1.v:.1f}", "%",
                         yoy_badge(a1.v, a0.v if a0 is not None else None, "%p") + " · KOSIS 전 분야 평균"))
    g262 = pr[pr["industry_code"] == "C262"].dropna(subset=["v"]).sort_values("ym")
    if not g262.empty:
        e2 = g262.iloc[-1]
        cards.append(kpi("전자부품 생산지수(C262)", f"{e2.v:.1f}", "", f"{e2.ym:%Y.%m} · 2020 = 100 · 계절조정 · 민수 포함",
                         "잠정" if e2.prelim else ""))
    st.html('<div class="kpis k4">' + "".join(cards) + "</div>")
    chart_source(f"방위사업청 국외조달 계획 → clean_dapa_overseas_plan · {stamp_txt('국외조달 계획', s_plan)} · "
                 f"KOSIS 방산업체 가동률 → clean_kosis_utilization · {stamp_txt('KOSIS 가동률', s_util)} · "
                 f"KOSIS 광공업생산지수 → clean_kosis_production_index · {stamp_txt('KOSIS 생산지수', s_prod)}")

# ── 2. 예산 추이 ─────────────────────────────────────────────────────────────
with zone("bud", "예산 추이"):
    c1, c2 = st.columns(2, gap="medium")
    src_plan = f"방위사업청 국외조달 조달계획(파일데이터) → clean_dapa_overseas_plan · v_overseas_plan_yearly · {stamp_txt('국외조달 계획', s_plan)}"
    with c1.container(border=True, key="card_bud"):
        if yearly.empty:
            chart_title("연도별 국외조달 계획 예산", "억 원 · 원화 계획(집행 예정액)")
            st.info("국외조달 계획 자료가 없습니다(미적재).")
        else:
            ys = yearly["krw"] / E8
            by0, by1, bv0, bv1 = int(yearly["year"].iloc[0]), int(yearly["year"].iloc[-1]), float(ys.iloc[0]), float(ys.iloc[-1])
            t_bud = (f"국외조달 계획 예산은 {by0}년 {bv0:,.0f}억 원에서 {by1}년 "
                     f'<span class="key">{bv1:,.0f}억 원</span>으로 {trend(bv0, bv1)}')
            chart_title(t_bud, f"억 원 · 계획연도 {by0}~{by1} · 원화 계획(집행 예정액)")
            fig = go.Figure(go.Bar(x=yearly["year"], y=ys, marker=dict(color="#9dbdf9", line=dict(color="#fff", width=1)),
                                   text=[f"{v:,.0f}" for v in ys], textposition="outside",
                                   textfont=dict(size=12, color=TEXT), cliponaxis=False,
                                   hovertemplate="%{x}년<br>%{y:,.0f}억 원<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(tickformat=",.0f", range=[0, ys.max() * 1.15])
            fig.update_layout(showlegend=False, bargap=.35, margin=dict(l=50, r=8, t=20, b=8))
            chart(style_fig(fig, 330), "국외조달계획예산", title=t_bud, source=src_plan)
            caption("계획연도 합 · 계약 · 집행 실적이 아님 · 관세청 수입액(USD)과 비교하지 않음")
            chart_source(src_plan)
    src_bud = f"열린재정 세부사업 예산 → clean_openfiscal_program_budget · v_budget_rnd_yearly · {stamp_txt('열린재정', s_bud)}"
    with c2.container(border=True, key="card_ratio"):
        sf, sd = b[b["amount_basis"] == "확정"], b[b["amount_basis"] != "확정"]
        if sf.empty:
            chart_title("국방기술개발 비중(방위사업청 일반회계 대비)", "%")
            st.info("세부사업 예산 자료(확정 연도)가 없습니다(미적재).")
        else:
            ry0, ry1, rp0, rp1 = int(sf["year"].iloc[0]), int(sf["year"].iloc[-1]), float(sf["pct"].iloc[0]), float(sf["pct"].iloc[-1])
            t_ratio = (f"방위사업청 일반회계 중 국방기술개발 비중(확정)은 {ry0}년 {rp0:.1f}%에서 {ry1}년 "
                       f'<span class="key">{rp1:.1f}%</span>로 {trend(rp0, rp1, "높아졌다", "낮아졌다")}')
            chart_title(t_ratio, f"% · {ry0}~{ry1} 확정" + (" · 점선 = 정부안" if not sd.empty else ""))
            fig = go.Figure(go.Scatter(x=sf["year"], y=sf["pct"], mode="lines+markers", name="확정",
                                       line=dict(color=ACCENT, width=2.5),
                                       marker=dict(size=7, color="#fff", line=dict(color=ACCENT, width=2)),
                                       fill="tozeroy", fillcolor="rgba(29,78,216,.08)",
                                       hovertemplate="%{x}년<br>%{y:.1f}%<extra></extra>"))
            if not sd.empty:
                tail = pd.concat([sf.tail(1), sd])
                fig.add_trace(go.Scatter(x=tail["year"], y=tail["pct"], mode="lines+markers", name="정부안",
                                         line=dict(color=ACCENT, width=2, dash="dot"),
                                         marker=dict(size=7, color="#fff", line=dict(color=ACCENT, width=2)),
                                         hovertemplate="%{x}년(정부안)<br>%{y:.1f}%<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(range=[0, b["pct"].max() * 1.2], ticksuffix="%")
            fig.update_layout(showlegend=not sd.empty, legend=dict(orientation="h", y=1.12))
            chart(style_fig(fig, 330), "국방기술개발비중", title=t_ratio, source=src_bud)
            caption("국방기술개발 ÷ 방위사업청 일반회계 세부사업 합계(같은 자료 안의 비율)"
                    + (f" · {'·'.join(str(y) for y in sd['year'])}년은 정부안(확정 전)" if not sd.empty else ""))
            chart_source(src_bud)

# ── 3. 국외조달 절차 · 집행유형별 예산 ─────────────────────────────────────────
with zone("proc", "국외조달 절차 · 집행유형별 예산"):
    c1, c2 = st.columns([1, 1.35], gap="medium")
    pc = d["proc"].iloc[0]
    fmt_ym = lambda v: f"{str(v)[:4]}.{str(v)[4:6]}" if v and len(str(v)) >= 6 else str(v)
    steps_src = [("계획", "", "조달 필요 확인<br>구매계획 수립", int(pc.plan_n), "#1d4ed8"),
                 ("입찰", "", "국외 공고 및 입찰<br>업체 평가 · 선정", int(pc.bid_n), "#0369a1"),
                 ("계약", "", "계약 체결<br>납품 및 이행 관리", int(pc.ctr_n), "#1e3a8a")]
    steps = '<div class="ar">→</div>'.join(
        f'<div class="st"><div class="ci" style="background:{bg}"><span>{ic}</span><b>{nm}</b></div>'
        f'<div class="ds">{ds}</div><div class="n">{n:,}<small>건</small></div></div>'
        for nm, ic, ds, n, bg in steps_src)
    with c1.container(border=True, key="card_proc"):
        chart_title(f"국외조달 기록은 계획 {int(pc.plan_n):,}건 · 입찰 결과 {int(pc.bid_n):,}건 · 계약 "
                    f'<span class="key">{int(pc.ctr_n):,}건</span> — 기간이 달라 전환율로 읽지 않는다', "건 · 단계별 행 수(실측)")
        st.html(f'<div class="proc">{steps}</div>')
        caption("조달계획 ≠ 계약 · 단계마다 기간 · 단위가 달라 앞 단계 대비 비율로 보지 않습니다")
        chart_source(f"방위사업청 국외조달 계획 · 입찰결과 · 계약(파일데이터) → clean_dapa_overseas_plan({pc.plan_y0}~{pc.plan_y1}) · "
                     f"clean_dapa_overseas_bid_result({fmt_ym(pc.bid_y0)}~{fmt_ym(pc.bid_y1)}, 결과 행) · "
                     f"clean_dapa_overseas_contract({pc.ctr_y0}~{pc.ctr_y1}) · DB 적재 {s_plan.get('loaded') or '—'}")
    with c2.container(border=True, key="card_heat"):
        if p.empty:
            chart_title("집행유형별 국외조달 계획 예산", "억 원")
            st.info("국외조달 계획 자료가 없습니다(미적재).")
        else:
            hm = (p.assign(y=p["plan_year"].astype(int)).groupby(["exec_type", "y"])["budget_krw"].sum() / E8).unstack(fill_value=0)
            hm = hm.loc[hm.sum(axis=1).sort_values(ascending=False).index]
            vals = hm.to_numpy()
            h_share = float(hm.iloc[0].sum() / (vals.sum() or 1) * 100)
            t_heat = (f"{int(hm.columns.min())}~{int(hm.columns.max())} 국외조달 계획 예산의 "
                      f'<span class="key">{h_share:.0f}%</span>는 {escape(str(hm.index[0]))} 유형이다')
            chart_title(t_heat, "억 원 · 색 = 유형 안에서의 상대 크기 · 칸에 올리면 금액")
            rel = [[(v - row.min()) / ((row.max() - row.min()) or 1) for v in row] for row in vals]
            fig = go.Figure(go.Heatmap(
                z=rel, x=list(hm.columns), y=list(hm.index), xgap=2, ygap=2, zmin=0, zmax=1, customdata=vals.round(0),
                colorscale=[[0, "#eff6ff"], [.5, "#60a5fa"], [1, "#1e3a8a"]],
                colorbar=dict(thickness=10, len=.9, outlinewidth=0, tickvals=[0, 1], ticktext=["낮음", "높음"],
                              tickfont=dict(color=MUTED, size=12.5)),
                hovertemplate="%{y} · %{x}년<br>%{customdata:,.0f}억 원<extra></extra>"))
            fig.update_xaxes(dtick=1, showgrid=False, tickfont=dict(size=12))
            fig.update_yaxes(autorange="reversed", showgrid=False)
            fig = style_fig(fig, 330)
            fig.update_layout(margin=dict(l=90, r=8, t=10, b=30))
            chart(fig, "집행유형별예산히트맵", title=t_heat, source=src_plan)
            caption("집행유형 × 계획연도 계획 예산 합(원화 계획) · 계약 · 집행 실적이 아님")
            chart_source(src_plan)

# ── 4. 운영 DB 실측 — 가동률 · 국산화 예산 · 계획 · 방산업체 ─────────────────────
with zone("facts", "운영 DB 실측 — 가동률 · 국산화 예산 · 국외조달 계획"):
    c1, c2 = st.columns(2, gap="medium")
    src_util = f"통계청 KOSIS 방산업체 경영분석(가동률) → clean_kosis_utilization · {stamp_txt('KOSIS 가동률', s_util)}"
    with c1.container(border=True, key="card_util"):
        if u.empty:
            chart_title("방산 분야별 가동률", "%")
            st.info("방산 분야 가동률 자료가 없습니다(미적재).")
        else:
            n_sec = u.loc[u["sector_name"] != "평균", "sector_name"].nunique()
            hi_l = u[u["sector_name"] == HIGHLIGHT].sort_values("year")
            av_l = u[u["sector_name"] == "평균"].set_index("year")["v"]
            if not hi_l.empty and hi_l["year"].iloc[-1] in av_l.index:
                uy, uh = int(hi_l["year"].iloc[-1]), float(hi_l["v"].iloc[-1])
                ua = float(av_l.loc[hi_l["year"].iloc[-1]])
                t_util = (f'{uy}년 {HIGHLIGHT} 분야 가동률은 <span class="key">{uh:.1f}%</span>로 '
                          f"{n_sec}개 분야 평균({ua:.1f}%)보다 {'높다' if uh > ua else '낮다' if uh < ua else '같다'}")
            else:
                t_util = "방산 분야별 가동률"
            chart_title(t_util, f"% · {int(u['year'].min())}~{int(u['year'].max())} · {HIGHLIGHT} 강조 · 점선 = 분야 평균")
            fig = go.Figure()
            for name, g in u.groupby("sector_name"):
                if name in (HIGHLIGHT, "평균"):
                    continue
                fig.add_trace(go.Scatter(x=g["year"], y=g["v"], name=name, mode="lines", showlegend=False,
                                         line=dict(color=GREY, width=1.4), hovertemplate=name + " %{x}년 %{y:.1f}%<extra></extra>"))
            n_sector = u.loc[u["sector_name"] != "평균", "sector_name"].nunique()
            for name, dash, color, w in (("평균", "dash", SERIES[3], 2), (HIGHLIGHT, None, SERIES[1], 3)):
                g = u[u["sector_name"] == name].sort_values("year")
                if g.empty:
                    continue
                fig.add_trace(go.Scatter(x=g["year"], y=g["v"], name=f"{n_sector}개 분야 평균" if name == "평균" else name,
                                         mode="lines" if dash else "lines+markers", line=dict(color=color, width=w, dash=dash),
                                         marker=dict(size=7, color="#fff", line=dict(color=color, width=2)),
                                         hovertemplate=name + " %{x}년 %{y:.1f}%<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(range=[max(0, u["v"].min() - 5), min(100, u["v"].max() + 5)], ticksuffix="%")
            fig.update_layout(legend=dict(orientation="h", y=1.14))
            chart(style_fig(fig, 330), "방산가동률", title=t_util, source=src_util)
            hi = u[u["sector_name"] == HIGHLIGHT].sort_values("year")
            if not hi.empty:
                caption(f"{HIGHLIGHT}은 {int(hi['year'].min())}~{int(hi['year'].max())}년 {hi['v'].min():.1f}~{hi['v'].max():.1f}% "
                        f"(최고 {int(hi.loc[hi['v'].idxmax(), 'year'])}년). 조사 기반 값이라 생산 능력·국산화 수준이 아니며, "
                        "수입 증감과 인과로 읽지 않습니다")
            chart_source(src_util)
    with c2.container(border=True, key="card_rnd"):
        lf = b[(b["localization_gov_100m"] > 0) & (b["amount_basis"] == "확정")].sort_values("year")
        if len(lf) >= 2:
            ly0, ly1 = int(lf["year"].iloc[0]), int(lf["year"].iloc[-1])
            lv0, lv1 = float(lf["localization_gov_100m"].iloc[0]), float(lf["localization_gov_100m"].iloc[-1])
            t_rnd = (f"부품국산화 예산(확정)은 {ly0}년 {lv0:,.0f}억 원에서 {ly1}년 "
                     f'<span class="key">{lv1:,.0f}억 원</span>으로 {trend(lv0, lv1)}')
        else:
            t_rnd = "부품국산화 · 공급망 · 국방반도체 예산"
        chart_title(t_rnd, "억 원 · 세부사업별 · 흐린 막대 = 정부안")
        fig = go.Figure()
        for col, name, color in (("localization_gov_100m", "부품국산화", SERIES[0]), ("supply_chain_gov_100m", "공급망", SERIES[1]),
                                 ("semiconductor_gov_100m", "국방반도체", SERIES[2])):
            s = b[b[col] > 0]
            if s.empty:
                continue
            fig.add_trace(go.Bar(x=s["year"], y=s[col], name=name,
                                 marker=dict(color=color, opacity=[.45 if a != "확정" else 1 for a in s["amount_basis"]],
                                             line=dict(color="#fff", width=1)),
                                 text=[f"{v:,.0f}" if v >= 100 else f"{v:,.1f}" for v in s[col]],
                                 textposition="outside", textfont=dict(size=12, color=TEXT), cliponaxis=False,
                                 customdata=s["amount_basis"],
                                 hovertemplate=name + " %{x}년 %{y:,.1f}억 원 (%{customdata})<extra></extra>"))
        top = b[["localization_gov_100m", "supply_chain_gov_100m", "semiconductor_gov_100m"]].max().max()
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(range=[0, top * 1.18])
        fig.update_layout(barmode="group", legend=dict(orientation="h", y=1.14), bargap=.25)
        chart(style_fig(fig, 330), "국산화예산", title=t_rnd, source=src_bud)
        draft = b[b["amount_basis"] != "확정"]
        last_fixed = b[b["amount_basis"] == "확정"].iloc[-1] if (b["amount_basis"] == "확정").any() else None
        badge = "".join(f'<span class="ex">정부안</span> {int(y)}년 ' for y in draft["year"])
        caption((f"{badge}은 확정 전 값입니다. " if badge else "")
                + (f"같은 자료의 국방기술개발은 {int(last_fixed.year)}년 {last_fixed.tech_dev_gov_100m / 1e4:,.2f}조 원 — 규모 차이가 커 이 그림에는 넣지 않았습니다. "
                   if last_fixed is not None else "")
                + "세부사업 계열끼리 합산하지 않고, 관세청 수입액과 합산하지 않습니다")
        chart_source(src_bud)

    c1, c2 = st.columns([1.35, 1], gap="medium")
    with c1.container(border=True, key="card_ovplan"):
        if p.empty:
            st.info("국외조달 계획 자료가 없습니다(미적재).")
        else:
            keep = p.groupby("exec_type")["plan_count"].sum().sort_values(ascending=False).index[:5].tolist()
            mix = (p.assign(grp=p["exec_type"].where(p["exec_type"].isin(keep), "기타"), y=p["plan_year"].astype(int))
                   .groupby(["y", "grp"])["plan_count"].sum().unstack(fill_value=0))
            total = int(mix.to_numpy().sum())
            y0, y1 = int(mix.index.min()), int(mix.index.max())
            k_share = float(mix[keep[0]].sum() / (total or 1) * 100) if keep and keep[0] in mix.columns else 0.0
            t_mix = (f"{y0}~{y1} 국외조달 계획 {total:,}건 중 가장 많은 유형은 "
                     f'<span class="key">{escape(str(keep[0]))}({k_share:.0f}%)</span>') if keep else "국외조달 계획 — 집행유형별 건수"
            chart_title(t_mix, f"건 · 계획연도 {y0}~{y1} · 상위 5개 유형 + 기타")
            fig = go.Figure()
            for i, g in enumerate(keep + ["기타"]):
                if g in mix.columns:
                    fig.add_trace(go.Bar(x=mix.index, y=mix[g], name=g,
                                         marker=dict(color=(SERIES[:5] + [ETC])[i], line=dict(color="#fff", width=1)),
                                         hovertemplate=g + " %{x}년 %{y}건<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.16), bargap=.3)
            chart(style_fig(fig, 330), "국외조달계획_집행유형", title=t_mix, source=src_plan)
            caption(f"계획(원화 집행 예정액 기준)이며 계약·집행 실적이 아닙니다 · 전체 건수 상위 5개 유형 + 기타 · "
                    f"대표품명 키워드 전자 관련 후보 {int(yearly['elec'].sum()):,}건(잠정, 검수 전) · 국가 정보가 없어 수입국과 연결하지 않습니다")
            chart_source(src_plan)
            tbl = mix.copy()
            tbl["합계"] = tbl.sum(axis=1)
            tbl = tbl.reset_index().rename(columns={"y": "계획연도"})
            tbl["계획 예산(억 원)"] = tbl["계획연도"].map(dict(zip(yearly["year"], (yearly["krw"] / E8).round(1))))
            head = csv_header(f"국외조달 계획 · {y0}~{y1} 계획연도 · 집행유형 상위 5 + 기타 · 단위 건 / 억 원(원화 계획액)",
                              "방위사업청 국외조달 조달계획(파일 데이터) → clean_dapa_overseas_plan → v_overseas_plan_yearly",
                              [("국외조달 계획", s_plan, None)], extra="계획 ≠ 계약 · 관세청 수입액과 합산·비교하지 않음")
            st.download_button("표 CSV 내려받기", (head + tbl.to_csv(index=False)).encode("utf-8-sig"),
                               f"배경_국외조달계획_{y0}-{y1}.csv", "text/csv", icon=":material/download:", key="p4_csv_plan")
    with c2.container(border=True, key="card_defco"):
        comp_all = d["comp"]
        comp = comp_all[comp_all["sector"] != "미기재"].sort_values("company_count", ascending=False)
        total_c = int(comp_all["company_count"].sum())
        n_missing = int(comp_all.loc[comp_all["sector"] == "미기재", "company_count"].sum())
        src_comp = f"방위사업청 방산업체 지정현황 → clean_dapa_defense_company · v_defense_company_sector · {stamp_txt('방산업체 지정현황', s_comp)}"
        if comp.empty:
            chart_title("분야별 방산업체 지정 수", "개사")
            st.info("방산업체 지정 자료가 없습니다(미적재).")
        else:
            c_top = comp.iloc[0]
            c_hl = comp.loc[comp["sector"] == HIGHLIGHT, "company_count"]
            if c_top.sector == HIGHLIGHT or c_hl.empty:
                t_comp = (f"지정 방산업체 {total_c}개사 중 가장 많은 분야는 "
                          f'<span class="key">{escape(str(c_top.sector))}({int(c_top.company_count)}개사)</span>')
            else:
                t_comp = (f"지정 방산업체 {total_c}개사 중 가장 많은 분야는 {escape(str(c_top.sector))}({int(c_top.company_count)}개사), "
                          f'{HIGHLIGHT} 분야는 <span class="key">{int(c_hl.iloc[0])}개사</span>')
            chart_title(t_comp, f"개사 · 「미기재」 {n_missing}개사는 막대에서 빼고 합계에 포함")
            rows = [(r.sector, int(r.company_count), SERIES[1] if r.sector == HIGHLIGHT else "#9dbdf9") for r in comp.itertuples()]
            chart(style_fig(hbar(rows, 330, "개사")), "방산업체지정", title=t_comp, source=src_comp)
            caption("지정 기준 값이며 생산 능력이나 국산화 수준을 뜻하지 않습니다")
            chart_source(src_comp)

# ── 5. 국내 생산 기반 — 생산지수 · 해석 주의 ───────────────────────────────────
with zone("geo", "국내 생산 기반"):
    c1, c2 = st.columns([1.3, 1], gap="medium")
    src_prod = f"통계청 KOSIS 광공업생산지수 → clean_kosis_production_index · {stamp_txt('KOSIS 생산지수', s_prod)}"
    with c1.container(border=True, key="card_prod"):
        if pr.empty:
            chart_title("광공업생산지수 — 전자부품 · 반도체 · 통신장비", "2020 = 100")
            st.info("광공업생산지수 자료가 없습니다(미적재).")
        else:
            if not g262.empty:
                pe = g262.iloc[-1]
                t_prod = (f'전자부품(C262) 생산지수는 {pe.ym:%Y.%m} 기준 <span class="key">{pe.v:.1f}</span>'
                          + ("(잠정)" if pe.prelim else "")
                          + f" — 2020년 수준(100)보다 {'높다' if pe.v > 100 else '낮다' if pe.v < 100 else '같다'}")
            else:
                t_prod = "광공업생산지수 — 전자부품 · 반도체 · 통신장비"
            chart_title(t_prod, "2020 = 100 · 전국 · 계절조정 · 음영 = 잠정치(p)")
            labels = {"C26": "C26 전자부품·컴퓨터·통신 전체", "C261": "C261 반도체", "C262": "C262 전자부품", "C264": "C264 통신·방송장비"}
            style = {"C26": ("#94a7c8", 1.5), "C261": (SERIES[2], 1.8), "C264": (SERIES[3], 1.8), "C262": (SERIES[0], 3)}
            fig = go.Figure()
            for code in ("C26", "C261", "C264", "C262"):
                g = pr[pr["industry_code"] == code].sort_values("ym")
                if g.empty:
                    continue
                color, w = style[code]
                fig.add_trace(go.Scatter(x=g["ym"], y=g["v"], name=labels[code], mode="lines", line=dict(color=color, width=w),
                                         hovertemplate=labels[code] + " %{x|%Y-%m}<br>%{y:.1f}<extra></extra>"))
            fig.add_hline(y=100, line=dict(color=MUTED, dash="dot", width=1))
            p0 = pr.loc[pr["prelim"], "ym"].min()
            if pd.notna(p0):
                fig.add_vrect(x0=p0, x1=pr["ym"].max() + pd.offsets.MonthEnd(0), fillcolor="#eef2f9", opacity=0.9, line_width=0,
                              layer="below", annotation_text="잠정치(p)", annotation_position="top left",
                              annotation_font=dict(color=MUTED, size=12.5))
            fig.update_layout(legend=dict(orientation="h", y=1.16), hovermode="x unified")
            chart(style_fig(fig, 400), "광공업생산지수", title=t_prod, source=src_prod)
            caption("민수 포함 산업 지표(방산 한정 아님) · 잠정치는 확정치 갱신본에서 바뀔 수 있음")
            chart_source(src_prod)
    c2.html(rules_card("해석할 때 주의", [
        ("예산은 배경 자료", "원화 예산·계획액은 관세청 수입액(USD)과 합산·비교하지 않습니다."),
        ("조달계획 ≠ 계약", "계획 건수·예산은 실제 계약·집행 실적이 아닙니다."),
        ("정부안은 확정 전 값", "정부안 연도는 흐린 막대·점선·「정부안」 배지로 구분합니다."),
        ("가동률·지정 수 ≠ 생산 능력", "조사·지정 기준 값이며 국산화 수준을 뜻하지 않습니다."),
        ("생산지수는 민수 포함", "방산에 한정되지 않은 산업 지표입니다."),
    ]))

# ── 6. 국방반도체 발전전략 ───────────────────────────────────────────────────
sm, sm_err = load_semi()
with zone("semi", "국방반도체 발전전략 · 국내 기반"):
    if sm is None and sm_err == "미적재":
        st.warning("국방반도체 참조표(ref_semi_*)가 비어 있습니다(미적재). `python scripts/load_db.py --ref` 로 적재하세요.")
    elif sm is None:
        st.error(f"국방반도체 참조표(ref_semi_*)를 조회하지 못했습니다({sm_err}). 잠시 뒤 다시 열어 주세요.")
    else:
        stat = sm["stat"].set_index("stat_key")
        s_ov, s_us = stat.loc["overseas_share"], stat.loc["us_share_min"]
        fab = sm["public_fab"].astype({"lat": float, "lon": float})
        case, ctype, task = sm["domestic_case"], sm["chip_type"], sm["strategy_task"]
        comp_fab = fab[fab["field_group"] == "화합물"]
        tl = sm["policy_timeline"].copy()
        tl["when"] = pd.to_datetime(tl["date"].where(tl["date"].str.len() > 4, tl["date"] + "-01"), format="mixed")
        strat = tl[tl["category"] == "전략"]
        strat_day = strat["when"].min() if not strat.empty else STRATEGY_DAY
        SRC_SEMI = "방위사업청 「국방반도체 발전전략」(2024-11-19)"
        st.html('<div class="kpis k4">'
                + kpi(escape(s_ov["label"]), f"{float(s_ov['value_num']):g}", escape(s_ov["unit_txt"]),
                      escape(s_ov["note"]) + " · " + escape(s_ov["source"]), "인용")
                + kpi(escape(s_us["label"]), f"{float(s_us['value_num']):g}", escape(s_us["unit_txt"]),
                      escape(s_us["note"]) + " · " + escape(s_us["source"]), "인용")
                + kpi("국방반도체 핵심기술 과제", f"{int((case['dapa_2025_task'] == '1').sum())}", "건",
                      "2025.5 최초 선정 · 방위사업청 보도자료(2025-05-19)")
                + kpi("공공 나노팹 중 화합물반도체", f"{len(comp_fab)}", f"/ {len(fab)}곳",
                      escape(" · ".join(f"{r.name_ko}({r.city})" for r in comp_fab.itertuples())) + " · 발전전략 참고10")
                + "</div>")
        c1, c2 = st.columns([1.5, 1], gap="medium")
        with c1.container(border=True, key="card_tl"):
            t_tl = (f"국방반도체 정책 사건 {len(tl)}건({tl['when'].min():%Y}~{tl['when'].max():%Y}) 중 전환점은 "
                    f'<span class="key">{escape(strat.iloc[0]["date"])} {escape(strat.iloc[0]["event"])}</span>'
                    if not strat.empty else f"국방반도체 정책 사건 {len(tl)}건")
            chart_title(t_tl, "건 · 점에 올리면 내용 · 점선 = 발전전략 발표")
            cats = list(dict.fromkeys(tl["category"]))
            fig = go.Figure()
            for i, (cat, g) in enumerate(tl.groupby("category", sort=False)):
                fig.add_trace(go.Scatter(x=g["when"], y=[cat] * len(g), mode="markers", name=cat,
                                         marker=dict(size=13, color=(SERIES + [ETC] * 9)[i], line=dict(color="#fff", width=1)),
                                         customdata=g[["date", "event", "detail", "source_title"]],
                                         hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]}<br><i>%{customdata[3]}</i><extra></extra>"))
            fig.add_vline(x=strat_day, line=dict(color=ACCENT, dash="dot", width=1))
            fig.update_layout(showlegend=False, xaxis=dict(tickformat="%Y.%m"),
                              yaxis=dict(categoryorder="array", categoryarray=cats[::-1]))
            src_tl = f"{SRC_SEMI} 추진 경과 · 보도자료 · 언론 보도(점마다 출처 제목) → ref_semi_policy_timeline"
            chart(style_fig(fig, 340), "국방반도체_타임라인", title=t_tl, source=src_tl)
            y_only = [d_ for d_ in tl["date"] if len(d_) == 4]
            if y_only:
                caption(f"「{' · '.join(y_only)}」은 연 단위 자료라 1월 위치에 찍었습니다")
            chart_source(src_tl)
        rows = "".join(
            f'<div style="margin-bottom:9px"><b style="color:{color}">{escape(k)}</b> '
            f'<span style="color:{MUTED}">{escape(g["direction_name"].iloc[0])}</span><br>'
            + " · ".join(escape(t) for t in g["task_name"]) + "</div>"
            for (k, g), color in zip(task.groupby("direction_key", sort=False), SERIES))
        with c2.container(border=True, key="card_task"):
            chart_title(f'발전전략은 {task["direction_key"].nunique()}개 방향 · <span class="key">{len(task)}개 과제</span>로 짜여 있다',
                        "방향별 과제")
            st.html(f'<div class="note" style="font-size:13.5px;line-height:1.7">{rows}</div>')
            chart_source(f"{SRC_SEMI} 본문 17-3 → ref_semi_strategy_task")

        c1, c2 = st.columns([1, 1.15], gap="medium")
        with c1.container(border=True, key="card_fab"):
            t_fab = (f'공공 나노팹 {len(fab)}곳 중 화합물반도체 팹은 <span class="key">{len(comp_fab)}곳</span>'
                     + (f"({escape(', '.join(comp_fab['name_ko']))})" if not comp_fab.empty else ""))
            chart_title(t_fab, "곳 · 부처별 색 · 큰 점 = 화합물반도체 · 좌표는 도시 단위 근사값")
            fig = go.Figure()
            for ministry, color in (("과기부", SERIES[0]), ("산업부", SERIES[1])):
                g = fab[fab["ministry"] == ministry]
                hi = g["field_group"] == "화합물"
                fig.add_trace(go.Scattergeo(lat=g["lat"], lon=g["lon"], mode="markers+text", name=ministry,
                                            text=g["abbr"].where(g["abbr"] != "", g["parent_org"]),
                                            textfont=dict(color=MUTED, size=11), textposition="middle right",
                                            marker=dict(size=[16 if h else 10 for h in hi], color=color, opacity=.9,
                                                        line=dict(color=[TEXT if h else "#fff" for h in hi], width=[2 if h else 1 for h in hi])),
                                            customdata=g[["name_ko", "parent_org", "field", "city"]],
                                            hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]}<extra>" + ministry + "</extra>"))
            dark_geo(fig)
            fig.update_geos(projection_type="mercator", lonaxis_range=[124.8, 130.6], lataxis_range=[33.0, 38.9], resolution=50)
            fig.update_layout(legend=dict(orientation="h", y=-0.05), margin=dict(t=10, b=10, l=0, r=0))
            src_fab = f"{SRC_SEMI} 참고10 → ref_semi_public_fab"
            chart(style_fig(fig, 420), "공공나노팹", title=t_fab, source=src_fab)
            caption("파운드리 구축 협력 후보(연구 · 시제 규모) · 수입 통계의 신고 지역과 무관")
            chart_source(src_fab)
        with c2.container(border=True, key="card_ms"):
            ms = sm["market_share"].astype({"share_pct": float})
            kr = ms[ms["country"] == "한국"]
            if not kr.empty:
                k_hi, k_lo = kr.loc[kr["share_pct"].idxmax()], kr.loc[kr["share_pct"].idxmin()]
                t_ms = (f'한국은 {escape(k_hi.segment)} 점유율이 <span class="key">{k_hi.share_pct:g}%</span>로 가장 높고, '
                        f"가장 낮은 분야는 {escape(k_lo.segment)}({k_lo.share_pct:g}%)")
            else:
                t_ms = "국가별 반도체 분야 시장점유율"
            chart_title(t_ms, "% · 발전전략 참고3 그래프 판독값(인용) · 원출처 · 기준연도 미표기")
            fig = go.Figure()
            for country, color in {"미국": "#94a7c8", "대만": GREY, "중국": "#e1e7f0", "한국": ACCENT}.items():
                g = ms[ms["country"] == country]
                fig.add_trace(go.Bar(x=g["segment"], y=g["share_pct"], name=country, marker=dict(color=color, line=dict(color="#fff", width=1)),
                                     text=g["share_pct"].map(lambda v: f"{v:g}"), textposition="outside",
                                     textfont=dict(color=TEXT if country == "한국" else MUTED, size=11), cliponaxis=False,
                                     hovertemplate=country + " %{x} %{y:g}%<extra></extra>"))
            fig.update_layout(barmode="group", yaxis=dict(range=[0, 78], ticksuffix="%"), legend=dict(orientation="h", y=1.12))
            src_ms = f"{SRC_SEMI} 참고3(인용 · 그래프 판독값) → ref_semi_market_share"
            chart(style_fig(fig, 420), "반도체시장점유율", title=t_ms, source=src_ms)
            chart_source(src_ms)

        n_case = case.groupby("type_no").size()
        tv = pd.DataFrame({"유형": ctype["type_no"] + ". " + ctype["name_ko"], "개요": ctype["summary"],
                           "대표 소자": ctype["example_devices"],
                           "관련 HS6(팀 판단)": ctype["related_hs6"].str.replace(";", " · ").replace("", "—"),
                           "국내 사례(건)": ctype["type_no"].map(n_case).fillna(0).astype(int)})
        with st.container(border=True, key="card_types"):
            n_max = int(tv["국내 사례(건)"].max()) if not tv.empty else 0
            tops = [escape(v) for v in tv.loc[tv["국내 사례(건)"] == n_max, "유형"]] if n_max else []
            t_types = (f"{len(ctype)}대 유형 중 국내 사례가 가장 많은 유형은 "
                       f'<span class="key">{" · ".join(tops)}({n_max}건)</span>') if tops else f"{len(ctype)}대 유형 × 국내 개발 사례"
            chart_title(t_types, "건 · 사례 = 언론 보도 기준(전수 아님) · 관련 HS6 은 팀 판단이라 수입액과 잇거나 합산하지 않음")
            st.dataframe(tv, hide_index=True, width="stretch", height=38 + 35 * len(tv), column_config={
                "개요": st.column_config.TextColumn(width="large"),
                "국내 사례(건)": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=int(max(n_case.max(), 1)))})
            head = csv_header("국방반도체 7대 유형 × 국내 개발 사례 건수", "방위사업청 「국방반도체 발전전략」(2024-11-19) 참고9 · 언론 보도 → RDS ref_semi_chip_type · ref_semi_domestic_case",
                              [], extra="RDS 참조표(수작업 입력) · 관련 HS6 은 팀 판단")
            st.download_button("표 CSV 내려받기", (head + tv.to_csv(index=False)).encode("utf-8-sig"),
                               "배경_국방반도체_유형별사례.csv", "text/csv", icon=":material/download:", key="p4_csv_semi")
            chart_source(f"{SRC_SEMI} 참고9 · 언론 보도 → ref_semi_chip_type · ref_semi_domestic_case")

with st.expander("산식 · 출처 · 표현 범위"):
    st.markdown(
        "**국외조달 계획 예산** = v_overseas_plan_yearly 의 budget_krw 계획연도 합(원화, 집행 예정액). 억 원 = 원 ÷ 10⁸. "
        "**전년 대비** = (당해 ÷ 전년 − 1) × 100(가동률은 %p 차).  \n"
        "**국외조달 절차 건수** = clean_dapa_overseas_plan · clean_dapa_overseas_bid_result · clean_dapa_overseas_contract 행 수(기간이 서로 달라 전환율 아님).  \n"
        "**국방기술개발 비중** = 국방기술개발 ÷ 방위사업청 일반회계 세부사업 합계 × 100(같은 자료 안의 비율). 정부안 연도는 확정 전 값.  \n"
        "**가동률** = KOSIS 방산 분야별 평균가동률(%). **지정 업체 수** = 방산업체 지정현황(「미기재」는 막대에서 빼고 합계에 포함). "
        "**광공업생산지수** = 전국 · 계절조정(T20) · 2020=100, 잠정치(p) 음영.  \n"
        "**국방반도체** = RDS ref_semi_* 7표(원본은 data/reference/semi_*.csv 수작업 참조표). 해외 도입 비중 · 미국 비중은 ref_semi_stat 의 발전전략 본문 인용값(팀 계산값 아님).  \n\n"
        "**표현 범위** — 계획 ≠ 계약 ≠ 집행. 원화 예산 · 계획액은 관세청 수입액(달러 실적)과 합산 · 비율 · 같은 축 비교를 하지 않습니다. "
        "세부사업 계열끼리도 합산하지 않습니다. 가동률 · 지정 업체 수 · 생산지수는 생산 능력이나 국산화 수준을 뜻하지 않습니다.")
