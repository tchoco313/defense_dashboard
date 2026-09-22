"""🔎 조회 — 정해진 조건을 골라 관세청 수입 실적을 표·차트로 보고 내려받는다(자유 입력·임의 SQL 없음).

디자인: docs/report/app/mockup-2026-09-18/search.html (왼쪽 조건 · 상단 요약 4 · 중앙 차트 · 하단 표와 내려받기).
- 지금 되는 조건: 품목군(HS6) · 세부코드(HS10) · 국가 · 기간 · 차트 형태. 원천은 fact_customs_monthly(월별 HS10 × 국가).
- 연결 군급(FSC) 조건은 두지 않는다(카테고리 맵 폐기, 2026-09-21). 적용장비 조건은 자리만 회색으로 둔다.
- 그래프 PNG는 plotly 도구 막대의 카메라 버튼(브라우저에서 바로 저장, 추가 설치 없음). 표는 CSV(조건·출처·기준일 머리줄 포함).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import data_stamp, query, safe_query
from metrics import concentration, period_years
from ui import BG, ETC, IMP, MUTED, SHORT, country_colors, csv_header, kpi, style_fig, zone

ALL = "__all__"
SOURCE = "관세청 품목별 국가별 수출입실적(15100475) · 국가 전체 수입(민수 포함) · USD"
CHARTS = ["국가 구성 100% 누적막대", "수입액 추이(선)", "1위국 점유율 · HHI 추이"]
KEYS = ("q_hs6", "q_hs10", "q_period", "q_ctry", "q_chart")


@st.cache_data(ttl=3600, show_spinner=False)
def load_ref() -> tuple[pd.DataFrame, pd.DataFrame]:
    wl = query("SELECT hs6, name_ko FROM ref_hs_whitelist WHERE priority IN (1, 2) ORDER BY priority, hs6")   # 분석 대상 13개(2026-09-21 M5)
    ctry = query("SELECT stat_cd, name_ko FROM ref_country")
    return wl, ctry


@st.cache_data(ttl=3600, show_spinner=False)
def load_hs10(hs6: str) -> pd.DataFrame:
    df = query("SELECT DISTINCT hs10 FROM fact_customs_monthly WHERE hs6 = :h ORDER BY hs10", {"h": hs6})
    names = safe_query("SELECT hs_code AS hs10, name_ko FROM raw_hs_unit_name WHERE hs_unit = '10' AND hs_code LIKE :p",
                       {"p": f"{hs6}%"})  # 품명은 라벨일 뿐 — 표가 없으면 코드만 보여 준다
    if names is None:
        return df.assign(name_ko=None)
    return df.merge(names.drop_duplicates("hs10"), on="hs10", how="left")


@st.cache_data(ttl=3600, show_spinner=False)
def load_trade(hs6_list: tuple[str, ...], hs10: str | None) -> pd.DataFrame:
    """연도 × 국가 수입·수출(HS10 조건이 있으면 그 코드만)."""
    sql = """
        SELECT year, stat_cd, SUM(imp_dlr) AS imp_dlr, SUM(exp_dlr) AS exp_dlr, MAX(is_partial_year) AS is_partial_year
        FROM fact_customs_monthly WHERE hs6 IN :hs {cond} GROUP BY year, stat_cd
    """
    if hs10:
        return query(sql.format(cond="AND hs10 = :h10"), {"hs": list(hs6_list), "h10": hs10})
    return query(sql.format(cond=""), {"hs": list(hs6_list)})


wl, ctry = load_ref()
cname = dict(zip(ctry["stat_cd"], ctry["name_ko"]))
names = {h: SHORT.get(h, n) for h, n in zip(wl["hs6"], wl["name_ko"])}

st.html('<div class="page-h">🔎 조회</div>'
        '<div class="note">자유 입력 대신 정해진 조건을 골라 조회합니다(오타 · 임의 SQL 방지). 결과 표와 그래프를 내려받을 수 있습니다.</div>')

left, right = st.columns([1, 3.2], gap="medium")

# ── 왼쪽 · 조회 조건 ─────────────────────────────────────────────────────────
with left, zone("p6_cond", "조회 조건"):
    hs6 = st.selectbox("품목군 (HS6)", [ALL] + wl["hs6"].tolist(), key="q_hs6",
                       format_func=lambda h: f"분석 대상 {len(wl)}개 합계" if h == ALL else f"{names[h]} · {h}")
    hs10 = None
    if hs6 == ALL:
        st.selectbox("세부코드 (HS10)", ["품목군을 하나 고르면 선택"], disabled=True)
    else:
        h10 = load_hs10(hs6)
        label10 = {r.hs10: f"{r.hs10} {r.name_ko}" if isinstance(r.name_ko, str) else r.hs10 for r in h10.itertuples()}
        pick10 = st.selectbox("세부코드 (HS10)", [ALL] + h10["hs10"].tolist(), key="q_hs10",
                              format_func=lambda h: "전체 세부코드" if h == ALL else label10.get(h, h))
        hs10 = None if pick10 == ALL else pick10
    raw = load_trade(tuple(wl["hs6"]) if hs6 == ALL else (hs6,), hs10)
    p = period_years(raw.loc[raw["is_partial_year"] == 0, "year"].unique())   # 홈·③ 과 같은 연도 목록 규칙(완결 연도만)
    if not p:
        st.info("이 조건에는 완결 연도 실적이 없습니다.")
        st.stop()
    periods = {str(p["base"][0]): p["base"], "최근 5년": p["recent5"], "전체": p["all"]}
    pick = st.pills("기간 기준", list(periods), default="최근 5년", key="q_period") or "최근 5년"
    years = periods[pick]
    ranked = raw[raw["year"] == p["base"][0]].groupby("stat_cd")["imp_dlr"].sum().sort_values(ascending=False).index.tolist()
    country = st.selectbox("국가", [ALL] + ranked, key="q_ctry",
                           format_func=lambda c: "전체 국가" if c == ALL else cname.get(c, c))
    chart = st.selectbox("차트 형태", CHARTS, key="q_chart")
    st.selectbox("적용장비", ["② 국외 조달계획 정제 후"], disabled=True)
    if st.button("초기화", width="stretch"):
        for k in KEYS:
            st.session_state.pop(k, None)
        st.rerun()

# ── 계산(기간 합계) ──────────────────────────────────────────────────────────
y_label = f"{years[0]}" if len(years) == 1 else f"{years[0]}~{years[-1]}"
scope = f"{len(wl)}개 합계" if hs6 == ALL else f"{names[hs6]} {hs6}" + (f" · {hs10}" if hs10 else "")
yr = raw[raw["year"].isin(years) & (raw["imp_dlr"] > 0)]
by_c = yr.groupby("stat_cd")["imp_dlr"].sum().sort_values(ascending=False)   # 표·상위 5개국용(기간 합계, 내림차순)
conc = concentration(yr.assign(hs6="_"), "imp_dlr")                            # 합계·1위국·HHI·수입국 수 — 홈·③ 과 같은 산식
total = float(conc["total"].iloc[0]) if not conc.empty else 0.0
share = by_c / total * 100 if total else by_c
hhi = float(conc["hhi"].iloc[0]) if not conc.empty else 0.0
top1_cd = str(conc["top1_stat_cd"].iloc[0]) if not conc.empty else None
n_ctry = int(conc["country_count"].iloc[0]) if not conc.empty else 0
cur = raw[(raw["year"] == years[-1]) & (raw["imp_dlr"] > 0)].groupby("stat_cd")["imp_dlr"].sum()
prev = raw[(raw["year"] == years[-1] - 1) & (raw["imp_dlr"] > 0)].groupby("stat_cd")["imp_dlr"].sum()
d_share = (cur / cur.sum() * 100).subtract(prev / prev.sum() * 100, fill_value=0) if not prev.empty else None
ctry_label = "전체 국가" if country == ALL else cname.get(country, country)
fname = f"조회_{hs6 if hs6 != ALL else f'all{len(wl)}'}_{y_label.replace('~', '-')}"

with right:
    # ── 상단 · 요약 ─────────────────────────────────────────────────────────
    with zone("p6_sum", "조회 결과 요약"):
        st.html('<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">'
                + "".join(f'<span style="font-size:11.5px;background:#2b3550;border-radius:14px;padding:4px 10px;color:#c9d4ec">{c}</span>'
                          for c in (scope, y_label, ctry_label)) + "</div>")
        if total == 0:
            st.info("이 조건에는 수입 실적이 없습니다. 기간이나 세부코드를 바꿔 보세요.")
            st.stop()
        if country == ALL:
            cards = [kpi(f"{y_label} 수입액", f"{total / 1e8:,.1f}", "억 달러", "국가 전체 수입 · 민수 포함"),
                     kpi("1위 공급국", cname.get(top1_cd, top1_cd), "", f"점유율 {float(share.get(top1_cd, 0)):.1f}%"),
                     kpi("HHI", f"{hhi:,.0f}", "", ("2,500 이상 = 높은 집중 · " if hhi >= 2500 else "") + "기간 합계 점유율 기준"),
                     kpi("수입국 수", f"{n_ctry}", "개국", f"{y_label} 수입 실적(>0)이 있는 국가")]
        else:
            v = float(by_c.get(country, 0))
            rank = by_c.index.get_loc(country) + 1 if country in by_c.index else None
            cards = [kpi(f"{ctry_label} 수입액", f"{v / 1e8:,.2f}", "억 달러", y_label),
                     kpi("점유율", f"{v / total * 100:.1f}", "%", f"{scope} 수입 중"),
                     kpi("순위", f"{rank}" if rank else "—", "위" if rank else "", f"{n_ctry}개 수입국 중"),
                     kpi("품목군 HHI", f"{hhi:,.0f}", "", "기간 합계 점유율 기준")]
        st.html('<div class="kpis k4">' + "".join(cards) + "</div>")

    # ── 중앙 · 선택한 차트 ──────────────────────────────────────────────────
    with zone("p6_chart", "선택한 차트"):
        top5 = by_c.index[:5].tolist() if country == ALL else [country]
        colors = country_colors(top5)
        fig = go.Figure()
        if chart == CHARTS[0]:
            g = yr.assign(grp=yr["stat_cd"].where(yr["stat_cd"].isin(top5), "기타")).groupby(["year", "grp"])["imp_dlr"].sum()
            pct = (g / g.groupby(level="year").transform("sum") * 100).unstack(fill_value=0)
            for cd in [c for c in top5 + ["기타"] if c in pct.columns]:
                fig.add_trace(go.Bar(x=pct.index.astype(str), y=pct[cd], name=cname.get(cd, cd),
                                     marker=dict(color=colors.get(cd, ETC), line=dict(color=BG, width=1)),
                                     hovertemplate="%{x} %{fullData.name}<br>%{y:.1f}%<extra></extra>"))
            fig.add_hline(y=50, line=dict(color="#e7eaf0", dash="dot", width=1))
            fig.update_layout(barmode="stack", yaxis=dict(range=[0, 100], title="점유율(%)"),
                              title=f"연도별 국가 구성 — {scope} · 점선 = 50%")
        elif chart == CHARTS[1]:
            s = (yr if country == ALL else yr[yr["stat_cd"] == country]).groupby("year")["imp_dlr"].sum()
            fig.add_trace(go.Scatter(x=s.index.astype(str), y=s / 1e6, name="수입액" if country == ALL else ctry_label,
                                     mode="lines+markers", line=dict(color=IMP if country == ALL else colors[country], width=2),
                                     hovertemplate="%{x}년 %{y:,.1f}백만$<extra></extra>"))
            fig.update_layout(yaxis=dict(title="수입액(백만$)", rangemode="tozero"), title=f"연도별 수입액 — {scope} · {ctry_label}")
        else:
            g = yr.groupby(["year", "stat_cd"])["imp_dlr"].sum()
            sh = g / g.groupby(level="year").transform("sum") * 100
            by_year = pd.DataFrame({"top1": sh.groupby(level="year").max(), "hhi": (sh ** 2).groupby(level="year").sum()})
            fig.add_trace(go.Bar(x=by_year.index.astype(str), y=by_year["hhi"], name="HHI", marker_color="#35507f",
                                 hovertemplate="%{x} HHI %{y:,.0f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=by_year.index.astype(str), y=by_year["top1"], name="1위국 점유율(%)", yaxis="y2",
                                     mode="lines+markers", line=dict(color="#f2b33d", width=2),
                                     hovertemplate="%{x} 1위국 %{y:.1f}%<extra></extra>"))
            fig.add_hline(y=2500, line=dict(color=MUTED, dash="dash", width=1))
            fig.update_layout(title=f"연도별 1위국 점유율 · HHI — {scope} · 점선 = HHI 2,500 (요약 카드의 기간 합계 HHI 와 다른 값)",
                              yaxis=dict(title="HHI", rangemode="tozero"),
                              yaxis2=dict(title="1위국 점유율(%)", overlaying="y", side="right", range=[0, 100], showgrid=False))
        fig.update_layout(margin=dict(t=60, b=30), legend=dict(orientation="h", y=-0.15, title=None), bargap=0.3)
        st.plotly_chart(style_fig(fig, 420), width="stretch", theme=None, config={
            "displaylogo": False, "modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "autoScale2d"],
            "toImageButtonOptions": {"format": "png", "filename": fname, "scale": 2}})
        st.html('<div class="note">그래프 PNG 저장: 그래프 위에 마우스를 올리면 오른쪽 위에 나오는 📷 버튼</div>')

    # ── 하단 · 결과 표와 내려받기 ───────────────────────────────────────────
    with zone("p6_table", "결과 표와 내려받기"):
        tbl = pd.DataFrame({"순위": range(1, len(by_c) + 1), "국가": [cname.get(c, c) for c in by_c.index],
                            f"수입액(백만$, {y_label})": (by_c.values / 1e6).round(1), "점유율(%)": share.values.round(1)})
        if d_share is not None:
            tbl[f"점유율 변화(%p, {years[-1] - 1}→{years[-1]})"] = [round(d_share.get(c, float("nan")), 1) for c in by_c.index]
        if country != ALL:
            tbl = tbl[tbl["국가"] == ctry_label]
        st.dataframe(tbl, hide_index=True, width="stretch", height=min(38 + 35 * len(tbl), 420), column_config={
            f"수입액(백만$, {y_label})": st.column_config.NumberColumn(format="localized"),
            "점유율(%)": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)})
        stamp = data_stamp("customs_all", "fact_customs_monthly")
        head = csv_header(f"{scope} · 기간 {y_label} · {ctry_label}", SOURCE, [("관세청 수출입", stamp, None)],
                          extra="점유율 = 국가별 수입액 ÷ 품목군 수입액(기간 합계) · HHI = 기간 합계 점유율 기준")
        st.download_button("⬇ 표 CSV 내려받기(엑셀)", (head + tbl.to_csv(index=False)).encode("utf-8-sig"),
                           file_name=f"{fname}.csv", mime="text/csv")
        st.html(f'<div class="note">출처 {SOURCE} · 자료 기간 {stamp["period"]} · DB 적재 {stamp["loaded"] or "—"} · '
                f'내려받은 날 {stamp["today"]} — 내려받은 파일 맨 위에도 조건 · 출처 · 자료 기간 · 적재일이 적힙니다</div>')
