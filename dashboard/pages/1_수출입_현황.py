"""핵심 ① 수출입 현황 — 품목군(HS6) × 국가 × 연도. 수입·수출 동등 배치.

읽는 뷰: v_import_hs6_year(수입·수출 연도×국가), v_hhi_hs6_year·v_hhi_export_hs6_year(집중도),
fact_customs_monthly(월별·HS10 세부), ref_hs_whitelist·ref_country·raw_hs_unit_name(라벨).
라벨 고정: 「국가 전체 수입·수출(민수 포함)」 — 군수 수요 비중이 아니다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_ready, query  # noqa: E402
from ui import (BG, ETC, EXP, EXP_DIM, IMP, IMP_DIM, PANEL2, SHORT, TEXT, country_colors,  # noqa: E402
                dark_geo, kpi, style_fig, zone)

# 색·레이아웃은 ui.py(다크 테마 · 목업 common.css). 국가 색은 홈과 같은 country_colors — 같은 나라 = 같은 색
SCOPE_LABEL = "국가 전체 수입·수출(민수 포함) · 관세청 품목별 국가별 수출입실적 · USD"
ALL = "__all__"
# 지도 라벨 위치 — 홈(home.py)과 같은 값. ui.py 에 두지 않는 이유: Streamlit Cloud 가 재배포 때 이미 올린 ui 모듈을
# 다시 읽지 않아 ui 에 새 이름을 추가하면 재부팅 전까지 ImportError 가 난다(2026-09-20 확인)
LABEL_POS = {"TW": "middle right", "MY": "middle left", "US": "top center", "CN": "top left", "SG": "bottom center", "VN": "middle left",
             "JP": "top right", "KR": "top right"}


# ── 데이터 ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_base() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(HS6 × 연도 × 국가 수입·수출, 화이트리스트) — 페이지가 쓰는 기본 표 두 개."""
    trade = query("""
        SELECT v.hs6, v.year, v.stat_cd, c.name_ko AS country, c.lat, c.lon,
               v.imp_dlr, v.exp_dlr, v.month_count, v.is_partial_year
        FROM v_import_hs6_year v
        LEFT JOIN ref_country c ON c.stat_cd = v.stat_cd
    """)
    trade["country"] = trade["country"].fillna(trade["stat_cd"])
    wl = query("""
        SELECT hs6, category, name_ko, priority, axis, evidence_basis, evidence, civil_mix, defense_use_ko
        FROM ref_hs_whitelist ORDER BY priority, hs6
    """)
    return trade, wl


@st.cache_data(ttl=3600, show_spinner=False)
def load_hhi(year: int) -> pd.DataFrame:
    imp = query("SELECT hs6, hhi AS hhi_imp, top1_stat_cd AS top1_imp, top1_share AS top1_share_imp, "
                "country_count AS n_imp FROM v_hhi_hs6_year WHERE year = :y", {"y": year})
    exp = query("SELECT hs6, hhi_export AS hhi_exp, top1_stat_cd AS top1_exp, top1_share AS top1_share_exp, "
                "country_count AS n_exp FROM v_hhi_export_hs6_year WHERE year = :y", {"y": year})
    return imp.merge(exp, on="hs6", how="outer")


@st.cache_data(ttl=3600, show_spinner=False)
def load_monthly(hs6_list: tuple[str, ...]) -> pd.DataFrame:
    return query("""
        SELECT yyyymm, SUM(imp_dlr) AS imp_dlr, SUM(exp_dlr) AS exp_dlr, MAX(is_partial_year) AS is_partial_year
        FROM fact_customs_monthly WHERE hs6 IN :hs GROUP BY yyyymm ORDER BY yyyymm
    """, {"hs": list(hs6_list)})


@st.cache_data(ttl=3600, show_spinner=False)
def load_hs10(hs6: str, year: int) -> pd.DataFrame:
    df = query("""
        SELECT f.hs10, SUM(f.imp_dlr) AS imp_dlr, SUM(f.exp_dlr) AS exp_dlr, COUNT(DISTINCT f.stat_cd) AS countries
        FROM fact_customs_monthly f WHERE f.hs6 = :hs6 AND f.year = :y GROUP BY f.hs10
    """, {"hs6": hs6, "y": year})
    names = query("SELECT hs_code AS hs10, name_ko FROM raw_hs_unit_name WHERE hs_unit = '10' AND hs_code LIKE :p",
                  {"p": f"{hs6}%"}).drop_duplicates("hs10")
    return df.merge(names, on="hs10", how="left").sort_values("imp_dlr", ascending=False)


def fmt_usd(v: float) -> str:
    """억 달러 단위 짧은 표기(원칙 5: 짧고 명확하게)."""
    if pd.isna(v):
        return "—"
    return f"{v / 1e8:,.1f}억$" if abs(v) >= 1e8 else f"{v / 1e6:,.1f}백만$"


def pct(part: float, total: float) -> str:
    return f"점유율 {part / total * 100:.1f}%" if total else "점유율 —"


def yoy(cur: float, prev: float) -> str | None:
    if not prev or pd.isna(prev) or pd.isna(cur):
        return None
    return f"{(cur / prev - 1) * 100:+.1f}% vs 전년"


# ── 접속 확인 ───────────────────────────────────────────────────────────────
if not db_ready():
    st.stop()

with st.spinner("팀 DB에서 관세청 집계를 읽는 중…"):
    trade, wl = load_base()

if trade.empty:
    st.warning("관세청 집계 뷰(`v_import_hs6_year`)에 데이터가 없습니다. `scripts/load_db.py --clean` 적재 여부를 확인하세요.")
    st.stop()

years = sorted(trade["year"].unique())
partial_years = set(trade.loc[trade["is_partial_year"] == 1, "year"].unique())
last_full_year = max(y for y in years if y not in partial_years)
analysis_hs = wl.loc[wl["priority"] <= 2, "hs6"].tolist()  # 분석 대상 13개(진입 R1 OR R2, 2026-09-21 M5). priority 3 = 분석 제외
label_of = {r.hs6: f"{r.hs6} · {r.name_ko} ({r.category}{', 분석 제외' if r.priority == 3 else ''})"
            for r in wl.itertuples()}

# ── 제목 ─────────────────────────────────────────────────────────────────────
st.html('<div class="page-h">① 수출입 현황 — 품목군별 · 국가별 · 연도별</div>'
        f'<div class="note">{SCOPE_LABEL} · 군수 수요 비중이 아니라 국가 전체 교역 규모입니다.</div>')

# ── 필터 한 줄(원칙 2·6: 상단, 기본값은 최근 완결 연도·수입액 1위 품목군) ──────
z_top = zone("p1_top", "조건과 요약")
f1, f2, f3 = z_top.columns([3, 1, 1])
imp_rank = (trade[(trade["year"] == last_full_year) & trade["hs6"].isin(analysis_hs)]
            .groupby("hs6")["imp_dlr"].sum().sort_values(ascending=False))
options = [ALL] + imp_rank.index.tolist() + [h for h in wl["hs6"] if h not in imp_rank.index]
sel = f1.selectbox("품목군(HS6)", options,
                   format_func=lambda h: f"분석 대상 {len(analysis_hs)}개 합계 (수집 24개 중 규칙 R1·R2 진입)" if h == ALL else label_of[h])
year = f2.selectbox("기준 연도", sorted(years, reverse=True), index=sorted(years, reverse=True).index(last_full_year),
                    format_func=lambda y: f"{y} (부분연도)" if y in partial_years else str(y))
top_n = f3.slider("상위 국가 수", 5, 15, 10)
ZONES = ["연도별 추이", "국가", "지도 · 집중도", "월별 · 표"]
zones_on = z_top.pills("표시 구역", ZONES, selection_mode="multi", default=ZONES, key="p1_zones",
                       help="보고 싶은 구역만 남깁니다. 조건과 요약(KPI)은 항상 보입니다") or ZONES

hs_list = tuple(analysis_hs) if sel == ALL else (sel,)
scope_title = f"분석 대상 {len(analysis_hs)}개 합계" if sel == ALL else f"{sel} {wl.set_index('hs6').loc[sel, 'name_ko']}"
d = trade[trade["hs6"].isin(hs_list)]
if d.empty or d.loc[d["year"] == year].empty:
    first_year = int(d["year"].min()) if not d.empty else None
    st.warning(f"선택한 품목군에 {year}년 관세청 집계가 없습니다." +
               (f" 이 HS6는 {first_year}년부터 있습니다(HS 2022 신설 코드)." if first_year and first_year > year else ""))
    st.stop()

if sel != ALL:
    info = wl.set_index("hs6").loc[sel]
    z_top.markdown(f"**{scope_title}** — 국방 용도: {info.defense_use_ko or '미기재'} · 근거 키 `{info.evidence or '—'}` "
                f"({info.evidence_basis}) · 민수 혼합 {info.civil_mix or '판단불가'}")

if year in partial_years:
    mc = int(d.loc[d["year"] == year, "month_count"].max())
    z_top.warning(f"{year}년은 **{mc}월까지의 부분연도** 집계입니다. 연간 실적과 직접 비교하지 마세요.", icon="⚠️")

# ── KPI 4장(원칙 2: 상단) ───────────────────────────────────────────────────
yr = d.groupby("year", as_index=False)[["imp_dlr", "exp_dlr"]].sum().set_index("year")
cur, prev = yr.loc[year], (yr.loc[year - 1] if (year - 1) in yr.index else None)
prev_ok = prev is not None and year not in partial_years  # 부분연도는 전년비를 내지 않는다
by_c = d[d["year"] == year].groupby("country")[["imp_dlr", "exp_dlr"]].sum()
imp_top, exp_top = by_c["imp_dlr"].idxmax(), by_c["exp_dlr"].idxmax()


def yoy_html(cur_v: float, prev_v: float | None) -> str:
    """전년비를 색으로(증가 초록·감소 빨강). 부분연도·전년 없음이면 안내 문구."""
    t = yoy(cur_v, prev_v) if prev_ok else None
    if not t:
        return "전년비 없음(부분연도·첫 해)"
    return f'<span class="{"up" if t.startswith("+") else "dn"}">{t}</span>'


def money(v: float) -> tuple[str, str]:
    s = fmt_usd(v)
    return (s[:-2], s[-2:]) if s.endswith("억$") else (s[:-3], s[-3:]) if s.endswith("백만$") else (s, "")


z_top.html('<div class="kpis k4">'
           + kpi(f"{year}년 수입액", *money(cur.imp_dlr), yoy_html(cur.imp_dlr, prev.imp_dlr if prev is not None else None))
           + kpi(f"{year}년 수출액", *money(cur.exp_dlr), yoy_html(cur.exp_dlr, prev.exp_dlr if prev is not None else None))
           + kpi("1위 수입국", imp_top, "", pct(by_c.loc[imp_top, "imp_dlr"], cur.imp_dlr))
           + kpi("1위 수출국", exp_top, "", pct(by_c.loc[exp_top, "exp_dlr"], cur.exp_dlr))
           + "</div>")

# ── 1행: 연도별 수입·수출 추이(선 2개, 한 축) ─────────────────────────────────
if "연도별 추이" in zones_on:
    yr_r = yr.reset_index()
    fig = go.Figure()
    for col, name, color, light in (("imp_dlr", "수입", IMP, IMP_DIM), ("exp_dlr", "수출", EXP, EXP_DIM)):
        full = yr_r[~yr_r["year"].isin(partial_years)]
        fig.add_trace(go.Scatter(x=full["year"], y=full[col], name=name, mode="lines+markers",
                                 line=dict(color=color, width=2), marker=dict(size=8),
                                 hovertemplate=f"{name} %{{x}}년<br>$%{{y:,.0f}}<extra></extra>"))
        part = yr_r[yr_r["year"].isin(partial_years)]
        if not part.empty:  # 부분연도는 연한 색·빈 마커·점선으로 이어 붙인다
            tail = pd.concat([full.tail(1), part])
            fig.add_trace(go.Scatter(x=tail["year"], y=tail[col], name=f"{name}(부분연도)", mode="lines+markers",
                                     line=dict(color=light, width=2, dash="dot"),
                                     marker=dict(size=8, color=BG, line=dict(color=color, width=2)),
                                     hovertemplate=f"{name} %{{x}}년(부분연도)<br>$%{{y:,.0f}}<extra></extra>"))
    fig.update_layout(title=f"연도별 수입액·수출액 — {scope_title}", xaxis=dict(dtick=1, title=None),
                      yaxis=dict(title="USD", zeroline=False),
                      legend=dict(orientation="h", y=1.12, title=None), hovermode="x unified", margin=dict(t=70, b=30))
    z_trend = zone("p1_trend", "연도별 추이")
    z_trend.plotly_chart(style_fig(fig), width="stretch", theme=None)

# ── 2행: 상위 수입국 / 상위 수출국(나란히, 단일 색조) ─────────────────────────
if "국가" in zones_on:
    z_ctry = zone("p1_ctry", "어느 나라와 · 얼마나")
    left, right = z_ctry.columns(2)
    for col_ui, col, name, color in ((left, "imp_dlr", "수입", IMP), (right, "exp_dlr", "수출", EXP)):
        total = by_c[col].sum()
        top = by_c[col].sort_values(ascending=False).head(top_n).reset_index()
        top["share"] = top[col] / total * 100
        fig2 = px.bar(top.sort_values(col), x=col, y="country", orientation="h", custom_data=["share"],
                      color_discrete_sequence=[color], labels={col: "USD", "country": ""},
                      title=f"{year}년 상위 {top_n}개 {name}국 (합계 {fmt_usd(total)})")
        fig2.update_traces(hovertemplate="%{y}<br>$%{x:,.0f} (%{customdata[0]:.1f}%)<extra></extra>",
                           text=[f"{s:.1f}%" if i >= len(top) - 3 else "" for i, s in enumerate(top.sort_values(col)["share"])],
                           textposition="outside", cliponaxis=False)
        fig2.update_layout(bargap=0.35, margin=dict(t=50, b=30))
        col_ui.plotly_chart(style_fig(fig2), width="stretch", theme=None)

    # ── 3행: 연도별 국가 구성 100% 누적막대(수입·수출 나란히, 같은 국가 = 같은 색) ──
    def composition(col: str, k: int = 5) -> pd.DataFrame:
        g = d.groupby(["year", "country"])[col].sum().reset_index()
        tot = g.groupby("year")[col].transform("sum")
        g["share"] = g[col] / tot * 100
        keep = (g[g["year"] == year].sort_values(col, ascending=False).head(k)["country"].tolist())
        g["group"] = g["country"].where(g["country"].isin(keep), "기타")
        return g.groupby(["year", "group"], as_index=False)["share"].sum(), keep


    comp_imp, keep_imp = composition("imp_dlr")
    comp_exp, keep_exp = composition("exp_dlr")
    union = list(dict.fromkeys(keep_imp + [c for c in keep_exp if c not in keep_imp]))
    code_of = dict(zip(trade["country"], trade["stat_cd"]))
    by_code = country_colors([code_of.get(c, c) for c in union])
    cmap = {c: by_code[code_of.get(c, c)] for c in union} | {"기타": ETC}
    left, right = z_ctry.columns(2)
    for col_ui, comp, keep, name in ((left, comp_imp, keep_imp, "수입"), (right, comp_exp, keep_exp, "수출")):
        order = [c for c in union if c in keep] + ["기타"]
        comp = comp[comp["group"].isin(order)]
        fig3 = px.bar(comp, x="year", y="share", color="group", category_orders={"group": order},
                      color_discrete_map=cmap, labels={"share": "점유율(%)", "year": "", "group": ""},
                      title=f"연도별 {name}국 구성 (기준 연도 상위 5개국 + 기타)")
        fig3.update_traces(hovertemplate="%{x}년 %{fullData.name}<br>%{y:.1f}%<extra></extra>", marker_line=dict(color=BG, width=1))
        fig3.update_layout(barmode="stack", bargap=0.3, xaxis=dict(dtick=1),
                           yaxis=dict(range=[0, 100]), legend=dict(orientation="h", y=-0.18, title=None),
                           margin=dict(t=50, b=30))
        col_ui.plotly_chart(style_fig(fig3), width="stretch", theme=None)

# ── 4행: 세계지도(수입/수출 전환) + 집중도 ─────────────────────────────────────
if "지도 · 집중도" in zones_on:
    z_map = zone("p1_map", "지도와 집중도")
    left, right = z_map.columns([3, 2])
    axis = left.radio("지도 기준", ["수입", "수출"], horizontal=True, label_visibility="collapsed")
    mcol, mcolor = ("imp_dlr", IMP) if axis == "수입" else ("exp_dlr", EXP)
    geo = (d[d["year"] == year].groupby(["stat_cd", "country", "lat", "lon"], as_index=False)[mcol].sum())
    geo = geo[(geo[mcol] > 0) & geo["lat"].notna()].sort_values(mcol, ascending=False).reset_index(drop=True)
    geo["share"] = geo[mcol] / geo[mcol].sum() * 100
    geo["label"] = [f"{c} {s:.1f}%" if i < 5 else "" for i, (c, s) in enumerate(zip(geo["country"], geo["share"]))]  # 상위 5개국만 상시 표시
    fig4 = px.scatter_geo(geo, lat="lat", lon="lon", size=mcol, size_max=45, hover_name="country", custom_data=["share"], text="label",
                          color_discrete_sequence=[mcolor], title=f"{year}년 국가별 {axis}액 — {scope_title}")
    fig4.update_traces(marker=dict(opacity=0.8, line=dict(color=BG, width=1)), textfont=dict(color=TEXT, size=11),
                       textposition=[LABEL_POS.get(c, "bottom center") for c in geo["stat_cd"]],
                       hovertemplate="%{hovertext}<br>$%{marker.size:,.0f} (%{customdata[0]:.1f}%)<extra></extra>")
    fig4.update_layout(margin=dict(t=50, b=0, l=0, r=0), height=420)
    picked = left.plotly_chart(dark_geo(style_fig(fig4)), width="stretch", theme=None, key=f"p1_map_{axis}_{year}_{sel}",
                               on_select="rerun", selection_mode="points")

    hhi = load_hhi(year).merge(wl[["hs6", "name_ko", "evidence_basis"]], on="hs6")
    hhi = hhi[hhi["hs6"].isin(hs_list)]
    with right:
        st.markdown(f"**{year}년 집중도(HHI, 0~10,000)** — 2,500 이상 「높은 집중」")
        if sel == ALL:
            show = hhi.sort_values("hhi_imp", ascending=False)[["hs6", "name_ko", "hhi_imp", "top1_imp", "top1_share_imp", "hhi_exp", "top1_exp"]]
            show["top1_share_imp"] = show["top1_share_imp"] * 100  # 뷰 값은 0~1 비율 → % 표시
            show = show.rename(columns={"name_ko": "품목군", "hhi_imp": "수입 HHI", "top1_imp": "1위 수입국", "top1_share_imp": "1위 점유율",
                                        "hhi_exp": "수출 HHI", "top1_exp": "1위 수출국"})
            st.dataframe(show, hide_index=True, width="stretch", height=380,
                         column_config={"수입 HHI": st.column_config.NumberColumn(format="%.0f"),
                                        "수출 HHI": st.column_config.NumberColumn(format="%.0f"),
                                        "1위 점유율": st.column_config.NumberColumn(format="%.1f%%")})
        elif hhi.empty:
            st.info("해당 연도의 집중도 행이 없습니다.")
        else:
            r = hhi.iloc[0]
            c1, c2 = st.columns(2)
            c1.metric("수입 HHI", f"{r.hhi_imp:,.0f}", delta=f"1위 {r.top1_imp} {r.top1_share_imp * 100:.1f}% · {int(r.n_imp)}개국", delta_color="off")
            c2.metric("수출 HHI", f"{r.hhi_exp:,.0f}", delta=f"1위 {r.top1_exp} {r.top1_share_exp * 100:.1f}% · {int(r.n_exp)}개국", delta_color="off")
            st.caption("HHI = Σ(국가 점유율)². 국가 전체 수입·수출 기준이며 군수 의존도가 아닙니다. 검토 목록(③)의 관문·정렬은 수입 HHI만 씁니다.")
        st.caption("지도 좌표: `ref_country`(238개국). 좌표 없는 국가는 표시되지 않습니다.")

    # 지도에서 고른 나라 → 분석 대상 합계면 그 나라의 품목군 구성, 품목군 하나면 그 나라의 연도별 추이
    pts = picked.selection.points
    if not pts:
        z_map.caption("지도의 원을 누르면 그 나라의 세부 내역이 아래에 나옵니다. 지도 빈 곳을 두 번 누르면 풀립니다.")
    else:
        cd = geo.iloc[pts[0]["point_index"]]
        one = d[d["stat_cd"] == cd.stat_cd]
        if sel == ALL:
            g = one[one["year"] == year].groupby("hs6", as_index=False)[mcol].sum()
            g = g[g[mcol] > 0].sort_values(mcol).tail(10)
            g["name"] = [f"{SHORT.get(h, h)} ({h})" for h in g["hs6"]]
            fig6 = px.bar(g, x=mcol, y="name", orientation="h", color_discrete_sequence=[mcolor], labels={mcol: "USD", "name": ""},
                          title=f"{cd.country} — {year}년 품목군별 {axis}액 (상위 10개 · 전체의 {cd.share:.1f}%)")
            fig6.update_traces(hovertemplate="%{y}<br>$%{x:,.0f}<extra></extra>")
        else:
            g = one[~one["year"].isin(partial_years)].groupby("year", as_index=False)[mcol].sum()
            fig6 = px.bar(g, x="year", y=mcol, color_discrete_sequence=[mcolor], labels={mcol: "USD", "year": ""},
                          title=f"{cd.country} — 연도별 {axis}액 · {scope_title} (부분연도 제외)")
            fig6.update_traces(hovertemplate="%{x}년<br>$%{y:,.0f}<extra></extra>")
            fig6.update_xaxes(dtick=1)
        fig6.update_layout(bargap=0.35, margin=dict(t=50, b=30, l=190 if sel == ALL else 80))  # 품목군 이름이 길다
        z_map.plotly_chart(style_fig(fig6, 340), width="stretch", theme=None)

# ── 5행: 월별 추이(2026년은 부분연도) ─────────────────────────────────────────
if "월별 · 표" in zones_on:
    m = load_monthly(hs_list)
    m["ym"] = pd.to_datetime(m["yyyymm"], format="%Y%m")
    fig5 = go.Figure()
    for col, name, color in (("imp_dlr", "수입", IMP), ("exp_dlr", "수출", EXP)):
        fig5.add_trace(go.Scatter(x=m["ym"], y=m[col], name=name, mode="lines", line=dict(color=color, width=2),
                                  hovertemplate=f"{name} %{{x|%Y-%m}}<br>$%{{y:,.0f}}<extra></extra>"))
    for py in sorted(partial_years):
        x_end = (m["ym"].max() + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
        fig5.add_vrect(x0=f"{py}-01-01", x1=x_end, fillcolor=PANEL2, opacity=0.8, line_width=0, layer="below",
                       annotation_text=f"{py} 부분연도", annotation_position="top left")
    fig5.update_layout(title=f"월별 수입액·수출액 — {scope_title}", hovermode="x unified",
                       yaxis=dict(title="USD", zeroline=False), xaxis=dict(title=None),
                       legend=dict(orientation="h", y=1.12, title=None), margin=dict(t=70, b=30))
    z_month = zone("p1_month", "월별 추이와 표")
    z_month.plotly_chart(style_fig(fig5), width="stretch", theme=None)

    # ── 하단 표(원칙 2·8: 조회용 표, CSV) ────────────────────────────────────────
    with z_month.expander(f"{year}년 국가별 수입·수출 표 (전체 국가)"):
        tbl = by_c.sort_values("imp_dlr", ascending=False).reset_index()
        tbl["수입 점유율(%)"] = tbl["imp_dlr"] / tbl["imp_dlr"].sum() * 100
        tbl["수출 점유율(%)"] = tbl["exp_dlr"] / tbl["exp_dlr"].sum() * 100
        tbl = tbl.rename(columns={"country": "국가", "imp_dlr": "수입액(USD)", "exp_dlr": "수출액(USD)"})
        st.dataframe(tbl, hide_index=True, width="stretch",
                     column_config={"수입액(USD)": st.column_config.NumberColumn(format="%d"), "수출액(USD)": st.column_config.NumberColumn(format="%d"),
                                    "수입 점유율(%)": st.column_config.NumberColumn(format="%.2f"), "수출 점유율(%)": st.column_config.NumberColumn(format="%.2f")})
        st.download_button("CSV 내려받기", tbl.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"trade_{'all19' if sel == ALL else sel}_{year}.csv", mime="text/csv")

    if sel != ALL:
        with z_month.expander(f"{year}년 HS10 세부 품목 표 — {sel}"):
            h10 = load_hs10(sel, year)
            if h10.empty:
                st.info("해당 연도에 HS10 세부 행이 없습니다.")
            else:
                h10["수입 비중(%)"] = h10["imp_dlr"] / h10["imp_dlr"].sum() * 100 if h10["imp_dlr"].sum() else 0.0
                h10 = h10.rename(columns={"hs10": "HS10", "name_ko": "품명(관세청 HS부호 단위별 품목명)", "imp_dlr": "수입액(USD)",
                                          "exp_dlr": "수출액(USD)", "countries": "교역국 수"})
                st.dataframe(h10, hide_index=True, width="stretch",
                             column_config={"수입액(USD)": st.column_config.NumberColumn(format="%d"), "수출액(USD)": st.column_config.NumberColumn(format="%d"),
                                            "수입 비중(%)": st.column_config.NumberColumn(format="%.1f")})
                st.caption("HS10 품명은 관세청 `HS부호 단위별 품목명`(15130660) 기준. 품명이 없으면 2026 신설·폐지 코드일 수 있습니다.")

st.html('<div class="caption">출처: 관세청 품목별 국가별 수출입실적 OpenAPI(15100475, 2016-01~2026-08, 2026-09-14 수집) → 팀 DB fact_customs_monthly. '
        "총계 행 제외, HS10→HS6 합산. 수입액·수출액은 국가 전체(민수 포함) 교역액이며 군수 수요·해외 의존도를 뜻하지 않습니다.</div>")
