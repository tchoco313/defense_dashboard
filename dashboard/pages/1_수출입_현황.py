"""핵심 ① 수출입 현황 — 팀원 디자인 데모(K-Defense) 「수출입 현황」 화면을 그대로 옮기고 값만 RDS 로 바꿨다. 수입·수출 동등 배치.

구역(데모 순서): 안내 줄 → 핵심 지표(KPI 6장) → 연도별 · 국가별(추이 선 · 국가 비중 도넛) → 공급국 집중도(주요 국가 TOP 7 ·
품목군별 HHI 산점) → 공급국 순위 변화(범프 — 품목 · 비교 연도를 고르면 이 구역만 다시 조회) → 품목군별 공급 집중도(탭 · 공급 국가 비중) → 세계 지도 → 과천시 소재 수입자 비중(추정, 히트맵) → 표 · 내려받기.
읽는 뷰: v_import_hs6_year(수입·수출 연도×국가), v_hhi_hs6_year·v_hhi_export_hs6_year(연도별 집중도), v_import_share_hs6_year(연도별 수입 순위), v_customs_region_gwacheon_year(과천 비중),
fact_customs_monthly(HS10 세부), ref_hs_whitelist·ref_country·ref_hs_code_master(HS10 품명 라벨).
데모에만 있고 DB 에 없는 칸(HSK 통제코드·민군겸용/항공/전자 후보 건수의 전년 대비)은 넣지 않았다.
라벨 고정: 「국가 전체 수입·수출(민수 포함)」 — 군수 수요 규모가 아니다. 국가는 선적국·도착국(원산지 아님).
"""
from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import live
from db import data_stamp, query
from kdesign import ETC, MUTED, TEXT, point_labels
from ui import (EXP, EXP_DIM, IMP, IMP_DIM, SHORT, source_pop, chart_source, chart_title, country_colors, country_map, csv_header, hero, hover_donut, kpi,
                png_button, rank_card, style_fig, zone)

SCOPE_LABEL = "국가 전체 수입·수출(민수 포함) · 관세청 품목별 국가별 수출입실적 · USD"
# 화면 · CSV 출처는 「기관 · 데이터명(포털 ID) · 자료 기간」만 — DB 표 · 뷰 이름과 적재일은 쓰지 않는다(보안, 2026-09-24 사용자)
SOURCE = "관세청 품목별 국가별 수출입실적 OpenAPI(15100475)"
ALL = "__all__"
E6 = 1e6   # 백만 달러 = USD ÷ 1e6 (데모 단위: 백만 USD)
PLOT_CFG = {"displaylogo": False, "modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "autoScale2d"]}


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
def load_hs10(hs6: str, year: int) -> pd.DataFrame:
    df = query("""
        SELECT f.hs10, SUM(f.imp_dlr) AS imp_dlr, SUM(f.exp_dlr) AS exp_dlr,
               COUNT(DISTINCT CASE WHEN f.imp_dlr > 0 THEN f.stat_cd END) AS imp_countries,
               COUNT(DISTINCT CASE WHEN f.exp_dlr > 0 THEN f.stat_cd END) AS exp_countries
        FROM fact_customs_monthly f WHERE f.hs6 = :hs6 AND f.year = :y GROUP BY f.hs10
    """, {"hs6": hs6, "y": year})
    names = query("SELECT hs10, name_ko FROM ref_hs_code_master WHERE hs10 LIKE :p",
                  {"p": f"{hs6}%"}).drop_duplicates("hs10")
    return df.merge(names, on="hs10", how="left").sort_values("imp_dlr", ascending=False)


@st.cache_data(ttl=3600, show_spinner=False)
def load_rank(hs6: str, years: tuple[int, ...]) -> pd.DataFrame:
    """고른 품목 · 연도의 수입 상위 3개국(EDA A2 — db/query_eda2_2026-09-23.sql [A2]와 같은 뷰 · 조건, 품목 · 연도만 파라미터)."""
    return query("""
        SELECT s.year, s.rnk, s.stat_cd, s.share
        FROM v_import_share_hs6_year s
        WHERE s.hs6 = :h AND s.year IN :ys AND s.rnk <= 3 AND s.is_partial_year = 0
        ORDER BY s.year, s.rnk, s.stat_cd
    """, {"h": hs6, "ys": list(years)})


@st.cache_data(ttl=3600, show_spinner=False)
def load_gwacheon(hs: tuple[str, ...]) -> pd.DataFrame:
    """품목군 × 연도 과천시 소재 수입자 비중(분모 = 전국 수입액, 천 달러 — 관세청 시군구별 실적)."""
    return query("SELECT hs6, year, gwacheon_share, imp_kusd_gwacheon, imp_kusd_total, is_partial_year "
                 "FROM v_customs_region_gwacheon_year WHERE hs6 IN :hs", {"hs": list(hs)})


def m6(v: float) -> float:
    return float(v) / E6


def share_card(f: dict) -> str:
    """데모 share_card 와 같은 모양 — 캡션만 실측 기준으로(데모 쪽은 「샘플」 문구)."""
    sh = f["shares"]
    rest = sum(s for _, s in sh[5:])
    cmap = f.get("colors", {})
    rows = [(n, s, cmap.get(n, "#94a7c8")) for n, s in sh[:5]] + ([("기타", rest, ETC)] if rest > 0.05 else [])
    body = "".join(f'<div class="row" title="{escape(n)} {s:.1f}%"><div class="nm">{escape(n)}</div><div class="track">'
                   f'<div class="fill" style="width:{s:.1f}%;background:{c}"></div><div class="ref"></div></div>'
                   f'<div class="pct">{s:.1f}%</div></div>' for n, s, c in rows)
    top_n, top_s = (sh[0][0], sh[0][1]) if sh else ("—", 0.0)
    if not sh:
        title = f'{escape(f["name"])} {f["axis"]} 국가 비중'
    elif f["axis"] == "수입":
        title = f'{escape(f["name"])} 수입액의 <span class="key">{top_s:.1f}%는 {escape(top_n)}</span>에서 들어왔다'
    else:
        title = f'{escape(f["name"])} 수출액의 <span class="key">{top_s:.1f}%는 {escape(ro(top_n))}</span> 나갔다'
    return (f'<div class="card"><div class="h"><span>{title}</span><span class="sub">HS {f["hs"]} · {f["year"]}년 · '
            f'{f["axis"]}국 {f["n"]}개 중 상위 5개국 · 점선 = 50% · 연도 HHI {f["hhi"]:,.0f}</span></div>'
            f'<div class="bars big">{body}</div></div>')


def ro(w: str) -> str:
    """조사 (으)로 — 받침이 있으면 「으로」(ㄹ 받침은 「로」)."""
    c = str(w)[-1:] or " "
    if "가" <= c <= "힣":
        j = (ord(c) - 0xAC00) % 28
        return f"{w}{'으로' if j not in (0, 8) else '로'}"
    return f"{w}로"


def change_txt(a: float, b: float) -> str:
    """a → b 변화를 중립 문장으로(늘었다 · 줄었다 · 같다). a 가 0 이면 비율 없이."""
    if not a:
        return "늘었다" if b > 0 else "같다"
    r = (b / a - 1) * 100
    return f"{abs(r):.1f}% 늘었다" if r > 0.05 else (f"{abs(r):.1f}% 줄었다" if r < -0.05 else "같다")


def trend_word(v: float) -> str:
    return f'<span class="up">▲ {v:+.1f}%</span>' if v >= 0 else f'<span class="dn">▼ {v:.1f}%</span>'


# ── 데이터 읽기 ───────────────────────────────────────────────────────────────
stamp = data_stamp("customs_all", "fact_customs_monthly")
STAMP_TXT = f"자료 기간 {stamp['period'] if stamp['has_period'] else '—'}"
SRC_TRADE = f"관세청 · 품목별 국가별 수출입실적(15100475) · {STAMP_TXT}"
SRC_HHI = f"관세청 · 품목별 국가별 수출입실적(15100475) · 연도별 집중도(HHI) · {STAMP_TXT}"
with st.spinner("관세청 집계를 읽는 중"):
    trade, wl = load_base()
if trade.empty:
    hero("① 수출입 현황", "분석 대상 품목군을 어느 나라에서 얼마나 수입하고, 어느 나라로 얼마나 수출하는지 봅니다",
         stamps=[("관세청 수출입", stamp)])
    st.warning("관세청 수출입 집계가 아직 적재되지 않았습니다(미적재). 관리자에게 적재 상태를 확인해 주세요.")
    st.stop()
# 「자료 기준」 버튼 안에 관세청 원천 최신 월 확인 한 줄(live.py — 홈과 같은 캐시를 쓴다)
_last_ym = query("SELECT MAX(yyyymm) AS ym FROM fact_customs_monthly")["ym"].iloc[0]
hero("① 수출입 현황", "분석 대상 품목군을 어느 나라에서 얼마나 수입하고, 어느 나라로 얼마나 수출하는지 봅니다",
     stamps=[("관세청 수출입", stamp), ("원천 확인", live.as_stamp(live.source_check(str(_last_ym), wl.loc[wl["priority"] <= 2, "hs6"].tolist())))])

years = sorted(int(y) for y in trade["year"].unique())
partial_years = {int(y) for y in trade.loc[trade["is_partial_year"] == 1, "year"].unique()}
last_full_year = max(y for y in years if y not in partial_years)
analysis_hs = wl.loc[wl["priority"] <= 2, "hs6"].tolist()   # 분석 대상 13개(진입 R1 OR R2, 2026-09-21 M5)
name_of_hs = {r.hs6: SHORT.get(r.hs6, r.name_ko) for r in wl.itertuples()}
label_of = {r.hs6: f"{r.hs6} · {r.name_ko} ({r.category}{', 분석 제외' if r.priority == 3 else ''})" for r in wl.itertuples()}
code_of = dict(zip(trade["country"], trade["stat_cd"]))

st.html('<div class="lede"><div class="note">HS/HSK 기반 방산 연관 품목군의 수입 · 수출 구조 · 공급국 집중도 · 품목군 동향. '
        '군수 수요 비중이 아니라 <b>국가 전체 교역 규모</b>(민수 포함)입니다. 국가는 선적국 · 도착국이며 원산지가 아닙니다.</div></div>')

# ── 조건(품목군 · 기준 연도) ──────────────────────────────────────────────────
with st.container(key="filters_p1"):
    f1, f2 = st.columns([3, 1], vertical_alignment="bottom")
    imp_rank = (trade[(trade["year"] == last_full_year) & trade["hs6"].isin(analysis_hs)]
                .groupby("hs6")["imp_dlr"].sum().sort_values(ascending=False))
    options = [ALL] + imp_rank.index.tolist() + [h for h in wl["hs6"] if h not in imp_rank.index]
    sel = f1.selectbox("품목군(HS6)", options, key="p1_hs6",
                       format_func=lambda h: f"분석 대상 {len(analysis_hs)}개 합계 (수집 {len(wl)}개 중 군용 전용 · 전문 용도 세분류 해당)" if h == ALL else label_of[h])
    year = f2.selectbox("기준 연도", sorted(years, reverse=True), index=sorted(years, reverse=True).index(last_full_year),
                        key="p1_year", format_func=lambda y: f"{y} (부분연도)" if y in partial_years else str(y))

hs_list = tuple(analysis_hs) if sel == ALL else (sel,)
scope = f"분석 대상 {len(analysis_hs)}개 합계" if sel == ALL else f"{name_of_hs[sel]} {sel}"
d = trade[trade["hs6"].isin(hs_list)]
if d.empty or d.loc[d["year"] == year].empty:
    first_year = int(d["year"].min()) if not d.empty else None
    st.warning(f"선택한 품목군에 {year}년 관세청 집계가 없습니다(실제 0 또는 코드 신설 전)." +
               (f" 이 HS6는 {first_year}년부터 있습니다." if first_year and first_year > year else ""))
    st.stop()
mc = int(d.loc[d["year"] == year, "month_count"].max())
if year in partial_years:
    st.warning(f"{year}년은 **1~{mc}월 부분연도** 집계입니다. 연간 실적과 직접 비교하지 마세요(전년 대비는 내지 않습니다).")

yr = d.groupby("year")[["imp_dlr", "exp_dlr"]].sum()
cur = yr.loc[year]
prev = yr.loc[year - 1] if (year - 1) in yr.index and year not in partial_years else None
by_c = d[d["year"] == year].groupby("country")[["imp_dlr", "exp_dlr"]].sum()
n_imp, n_exp = int((by_c["imp_dlr"] > 0).sum()), int((by_c["exp_dlr"] > 0).sum())
imp_top, exp_top = by_c["imp_dlr"].idxmax(), by_c["exp_dlr"].idxmax()
ptag = f" (1~{mc}월)" if year in partial_years else ""


def yoy_sub(col: str) -> str:
    if prev is None or not prev[col]:
        return "전년 대비 없음(부분연도 · 첫 해)"
    return f"{trend_word((cur[col] / prev[col] - 1) * 100)} 전년 대비 · {year - 1}년 {m6(prev[col]):,.0f}"


# ── 핵심 지표(KPI 6장) ────────────────────────────────────────────────────────
with zone("kpi2", "핵심 지표"):
    st.html('<div class="kpis k6">'
            + kpi("분석 대상 HS6", f"{len(analysis_hs)}", "개", f"수집 {len(wl)}개 중 군용 전용 · 전문 용도 세분류 해당")
            + kpi(f"{year}년 수입액{ptag}", f"{m6(cur.imp_dlr):,.0f}", "백만 USD", yoy_sub("imp_dlr"))
            + kpi(f"{year}년 수출액{ptag}", f"{m6(cur.exp_dlr):,.0f}", "백만 USD", yoy_sub("exp_dlr"))
            + kpi("1위 수입국(선적국)", escape(imp_top), "", f"점유율 {by_c.loc[imp_top, 'imp_dlr'] / cur.imp_dlr * 100:.1f}% · 수입국 {n_imp}개")
            + kpi("1위 수출국(도착국)", escape(exp_top), "", f"점유율 {by_c.loc[exp_top, 'exp_dlr'] / cur.exp_dlr * 100:.1f}% · 수출국 {n_exp}개")
            + kpi("분석 기간", f"{years[0]}–{years[-1]}", "", f"총 {len(years)}년" + (f" · {max(partial_years)}년은 부분연도" if partial_years else ""))
            + "</div>")
    chart_source(f"{SRC_TRADE} · {escape(scope)} · {year}년 · 전년 대비는 완결 연도끼리만")

# ── 연도별 · 국가별 ───────────────────────────────────────────────────────────
with zone("trend", "연도별 · 국가별"):
    c1, c2 = st.columns([1.3, 1], gap="medium")
    with c1.container(border=True, key="card_trend"):
        full_years = [y for y in yr.index if y not in partial_years]
        if len(full_years) >= 2:
            ya, yb = full_years[0], full_years[-1]
            ia, ib, ea, eb = yr.loc[ya, "imp_dlr"], yr.loc[yb, "imp_dlr"], yr.loc[ya, "exp_dlr"], yr.loc[yb, "exp_dlr"]
            ri = (ib / ia - 1) * 100 if ia else 0.0
            re_ = (eb / ea - 1) * 100 if ea else 0.0
            imp_ph, exp_ph = f"수입액은 {change_txt(ia, ib)}", f"수출액은 {change_txt(ea, eb)}"
            if abs(ri) >= abs(re_):          # 변화가 더 큰 쪽을 강조 구절로
                imp_ph = f'<span class="key">{imp_ph}</span>'
            else:
                exp_ph = f'<span class="key">{exp_ph}</span>'
            trend_title = (f"{ya}년 대비 {yb}년 {imp_ph}({m6(ia):,.0f} → {m6(ib):,.0f}백만 USD), "
                           f"{exp_ph}({m6(ea):,.0f} → {m6(eb):,.0f}백만 USD)")
        else:
            trend_title = f"{escape(scope)} 연도별 수입액 · 수출액"
        trend_sub = (f"{escape(scope)} · 단위: 백만 USD · {years[0]}~{years[-1]}"
                     + (f" · {max(partial_years)}년은 부분연도(점선, 비교에서 뺌)" if partial_years else ""))
        chart_title(trend_title, trend_sub)
        yr_r = yr.reset_index()
        full = yr_r[~yr_r["year"].isin(partial_years)]
        part = yr_r[yr_r["year"].isin(partial_years)]
        fig = go.Figure()
        for col, name, color, light in (("imp_dlr", "수입", IMP, IMP_DIM), ("exp_dlr", "수출", EXP, EXP_DIM)):
            fig.add_trace(go.Scatter(x=full["year"], y=full[col] / E6, name=name, mode="lines+markers",
                                     line=dict(color=color, width=2.5), marker=dict(size=7, color="#fff", line=dict(color=color, width=2)),
                                     hovertemplate=f"{name} %{{x}}년<br>%{{y:,.0f}} 백만 USD<extra></extra>"))
            if not part.empty:
                tail = pd.concat([full.tail(1), part])
                fig.add_trace(go.Scatter(x=tail["year"], y=tail[col] / E6, name=f"{name}(부분연도)", mode="lines+markers",
                                         line=dict(color=light, width=2.5, dash="dot"),
                                         marker=dict(size=7, color="#fff", line=dict(color=light, width=2)),
                                         hovertemplate=f"{name} %{{x}}년(부분연도)<br>%{{y:,.0f}} 백만 USD<extra></extra>"))
        fig.update_layout(legend=dict(orientation="h", y=1.12))
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(tickformat=",.0f")
        st.plotly_chart(style_fig(fig, 430), width="stretch", theme=None, config=PLOT_CFG)
        chart_source(SRC_TRADE)
        png_button(fig, f"수출입_연도별추이_{'all' if sel == ALL else sel}", align="flex-start",
                   title=trend_title, source="출처: " + SRC_TRADE)
    with c2.container(border=True, key="card_share"):
        axis = st.segmented_control("비중 기준", ["수입", "수출"], default="수입", key="p1_donut_axis",
                                    label_visibility="collapsed") or "수입"
        col = "imp_dlr" if axis == "수입" else "exp_dlr"
        s = by_c[col][by_c[col] > 0].sort_values(ascending=False)
        top7 = s.head(7)
        cc = country_colors([code_of.get(n, n) for n in top7.index])
        rows = [(n, m6(v), cc[code_of.get(n, n)]) for n, v in top7.items()]
        if s.iloc[7:].sum() > 0:
            rows.append(("기타", m6(s.iloc[7:].sum()), ETC))
        if s.empty:
            donut_title = f"{year}년{ptag} {axis} 국가 비중"
        else:
            top_nm = str(s.index[0])
            donut_title = (f'{year}년{ptag} {axis}액의 <span class="key">{s.iloc[0] / s.sum() * 100:.1f}%는 '
                           + (f'{escape(top_nm)}</span>에서 들어왔다' if axis == "수입" else f'{escape(ro(top_nm))}</span> 나갔다'))
        chart_title(donut_title, f"{escape(scope)} · 단위: 백만 USD · 상위 7개국 + 기타 · 조각에 커서를 올리면 값")
        hover_donut(rows, f"{m6(s.sum()):,.0f}", f"{axis}액 합계 · 백만 USD", value_unit="백만 USD", height=440)
        pie = go.Figure(go.Pie(labels=[r[0] for r in rows], values=[r[1] for r in rows], hole=.55, sort=False,
                               marker=dict(colors=[r[2] for r in rows], line=dict(color="#fff", width=1.5)), textinfo="label+percent"))
        pie.update_layout(height=420, annotations=[dict(text=f"{m6(s.sum()):,.0f}<br>백만 USD", showarrow=False, font=dict(size=17))])
        chart_source(SRC_TRADE + (" · 국가는 선적국" if axis == "수입" else " · 국가는 도착국"))
        png_button(style_fig(pie), f"수출입_{axis}국비중_{year}", align="flex-start",
                   title=donut_title, source="출처: " + SRC_TRADE)

# ── 공급국 집중도 ─────────────────────────────────────────────────────────────
hhi = load_hhi(year).merge(wl[["hs6", "name_ko"]], on="hs6")
hhi = hhi[hhi["hs6"].isin(hs_list)]
name_of_cd = dict(zip(trade["stat_cd"], trade["country"]))
with zone("conc", "공급국 집중도"):
    c1, c2 = st.columns([1, 1.25], gap="medium")
    with c1:
        t_i, t_e = st.tabs(["주요 수입국", "주요 수출국"])
        for tab, col, nm, basis in ((t_i, "imp_dlr", "수입", "선적국"), (t_e, "exp_dlr", "수출", "도착국")):
            s = by_c[col][by_c[col] > 0].sort_values(ascending=False)
            top = s.head(7)
            cc = country_colors([code_of.get(n, n) for n in top.index])
            rank_title = (f'상위 7개 {nm}국이 {year}년{ptag} {nm}액의 <span class="key">{top.sum() / s.sum() * 100:.1f}%</span>를 차지한다'
                          if not s.empty else f"주요 {nm}국 TOP 7")
            tab.html(rank_card(rank_title, f"{basis} · {nm}국 {len(s)}개 중 상위 7개",
                               [(escape(str(n)), m6(v), cc[code_of.get(n, n)]) for n, v in top.items()], "백만 USD"))
            chart_source(SRC_TRADE, where=tab)
    with c2.container(border=True, key="card_hhi"):
        ax2 = st.segmented_control("집중도 기준", ["수입", "수출"], default="수입", key="p1_hhi_axis",
                                   label_visibility="collapsed") or "수입"
        hcol, scol, tcol = ("hhi_imp", "top1_share_imp", "top1_imp") if ax2 == "수입" else ("hhi_exp", "top1_share_exp", "top1_exp")
        h = hhi.dropna(subset=[hcol])
        k_hi2 = int((h[hcol] >= 2500).sum())
        if h.empty:
            hhi_title = f"{year}년 품목군별 {ax2} 집중도(HHI)"
        elif k_hi2:
            hhi_title = f'{year}년 {ax2} 기준 {len(h)}개 품목군 중 <span class="key">{k_hi2}개</span>가 HHI 2,500 이상(높은 집중)이다'
        else:
            hhi_title = f'{year}년 {ax2} 기준 {len(h)}개 품목군 <span class="key">모두 HHI 2,500 미만</span>이다'
        chart_title(hhi_title, f"{year}년 연도별 값 · 가로 = 1위 국가 점유율(%) · 세로 = HHI(0~10,000) · 색 = 1위 국가")
        if h.empty:
            st.info(f"{year}년 {ax2} 집중도 행이 없습니다.")
        else:
            cc = country_colors(h[tcol].tolist())
            xs, ys = (h[scol] * 100).tolist(), h[hcol].tolist()
            names = [name_of_hs.get(x, x) for x in h["hs6"]]
            xr = [max(0.0, min(xs) - 8), min(100.0, max(xs) + 8)]
            yr = [max(0.0, min(ys) - 700), max(ys) + 900]
            shown, pos = point_labels(xs, ys, names, xr, yr)     # 겹치는 이름은 옮기거나 비운다(커서를 올리면 보임)
            fig = go.Figure(go.Scatter(
                x=xs, y=ys, mode="markers+text", text=shown, textposition=pos, textfont=dict(size=13, color=MUTED),
                customdata=list(zip(names, [name_of_cd.get(c, c) for c in h[tcol]])),
                marker=dict(size=14, color=[cc.get(c, ETC) for c in h[tcol]], line=dict(color="#fff", width=1.5)),
                hovertemplate="%{customdata[0]}<br>1위 %{customdata[1]} %{x:.1f}%<br>HHI %{y:,.0f}<extra></extra>"))
            fig.add_hline(y=2500, line=dict(color="#94a7c8", dash="dash", width=1),
                          annotation_text="HHI 2,500", annotation_font=dict(color=MUTED, size=13))
            fig.update_xaxes(title="1위 국가 점유율(%)", range=xr)
            fig.update_yaxes(title="HHI", range=yr)
            st.plotly_chart(style_fig(fig, 360), width="stretch", theme=None, config=PLOT_CFG)
            chart_source(SRC_HHI)
            png_button(fig, f"수출입_{ax2}HHI_{year}", align="flex-start", title=hhi_title, source="출처: " + SRC_HHI)


# ── 공급국 순위 변화(범프 차트) — 품목 · 비교 연도를 바꾸면 이 구역만 다시 조회한다 ─────────────
@st.fragment
def rank_change() -> None:
    full_years = [y for y in years if y not in partial_years]
    r_opts = imp_rank.index.tolist() + [h for h in analysis_hs if h not in imp_rank.index]   # 기준 연도 수입액 순
    r_default = sel if sel in r_opts else r_opts[0]
    c1, c2 = st.columns([1.2, 2], vertical_alignment="bottom")
    r_hs = c1.selectbox("품목군", r_opts, index=r_opts.index(r_default), key=f"p1_rank_hs_{r_default}",
                        format_func=lambda h: f"{name_of_hs[h]} · {h}")
    base = list(dict.fromkeys(y for y in (2016, 2021, last_full_year) if y in full_years))
    r_years = c2.multiselect("비교 연도(최대 3개 · 완결 연도만)", full_years, default=base, max_selections=3, key="p1_rank_years")
    if not r_years:
        st.info("비교 연도를 하나 이상 고르세요.")
        return
    r_years = sorted(r_years)
    rk = load_rank(r_hs, tuple(r_years))
    first_year = int(trade.loc[trade["hs6"] == r_hs, "year"].min())
    empty_years = [y for y in r_years if y not in set(rk["year"])]
    nm = name_of_hs[r_hs]
    if rk.empty:
        st.info(f"{nm}은(는) 고른 연도에 수입 실적이 없습니다" + (f"(이 코드는 {first_year}년부터 있습니다)." if first_year > r_years[0] else "."))
        return
    top1 = rk[rk["rnk"] == 1].drop_duplicates("year").set_index("year")
    y0, y1 = int(top1.index.min()), int(top1.index.max())
    c0, c_last = name_of_cd.get(top1.loc[y0, "stat_cd"], top1.loc[y0, "stat_cd"]), name_of_cd.get(top1.loc[y1, "stat_cd"], top1.loc[y1, "stat_cd"])
    s0, s1 = top1.loc[y0, "share"] * 100, top1.loc[y1, "share"] * 100
    if y0 == y1:
        r_title = f'{escape(nm)} {y1}년 수입 1위는 <span class="key">{escape(str(c_last))}({s1:.1f}%)</span>'
    elif c0 == c_last:
        r_title = (f'{escape(nm)} 수입 1위는 {y0}년부터 {y1}년까지 <span class="key">{escape(str(c_last))}</span>'
                   f'({s0:.1f}% → {s1:.1f}%)')
    else:
        r_title = (f'{escape(nm)} 수입 1위가 {y0}년 {escape(str(c0))}({s0:.1f}%)에서 '
                   f'<span class="key">{y1}년 {escape(ro(str(c_last)))}</span> 바뀌었다({s1:.1f}%)')
    chart_title(r_title, f"HS {r_hs} · 연도별 수입 상위 3개국 · 점 옆 = 그해 수입 점유율(%) · 마지막 연도에 3위 밖이면 회색")
    last_set = set(rk.loc[rk["year"] == r_years[-1], "stat_cd"]) if r_years[-1] in set(rk["year"]) else set()
    cc = country_colors([c for c in rk.sort_values(["year", "rnk"], ascending=[False, True])["stat_cd"] if c in last_set])
    xs = [str(y) for y in r_years]
    fig = go.Figure()
    for cd in dict.fromkeys(rk["stat_cd"]):
        g = rk[rk["stat_cd"] == cd].set_index("year")
        cname = str(name_of_cd.get(cd, cd))
        col = cc.get(cd, MUTED) if cd in last_set else "#b8c2cf"
        ys = [float(g.loc[y, "rnk"]) if y in g.index else None for y in r_years]
        txt = [f"{cname} {g.loc[y, 'share'] * 100:.1f}%" if y in g.index else "" for y in r_years]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers+text", name=cname, text=txt, textposition="top center",
            textfont=dict(size=12.5, color=TEXT if cd in last_set else MUTED), connectgaps=False,
            line=dict(color=col, width=3 if cd in last_set else 2), marker=dict(size=13, color=col, line=dict(color="#fff", width=1.5)),
            hovertemplate=f"{cname}<br>%{{x}}년 %{{y:.0f}}위<extra></extra>"))
    fig.update_yaxes(range=[3.6, 0.4], tickvals=[1, 2, 3], ticktext=["1위", "2위", "3위"], title=None)
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=xs, title=None)
    fig.update_layout(showlegend=False)
    st.plotly_chart(style_fig(fig, 330), width="stretch", theme=None, config=PLOT_CFG)
    notes = []
    if empty_years:
        notes.append(", ".join(map(str, empty_years)) + "년은 수입 실적 없음" + (f"(이 코드는 {first_year}년부터)" if first_year > min(empty_years) else ""))
    src = SRC_TRADE + " · 연도별 국가 수입 점유율 순위(동률은 같은 순위)"
    if notes:
        st.html(f'<div class="caption">{escape(" · ".join(notes))}</div>')
    chart_source(src)
    png_button(fig, f"수출입_공급국순위_{r_hs}_{'-'.join(xs)}", align="flex-start", title=r_title, source="출처: " + src)


with zone("rank", "공급국 순위 변화"):
    with st.container(border=True, key="card_rank"):
        rank_change()

# ── 품목군별 공급 집중도(탭) ──────────────────────────────────────────────────
with zone("focus", "품목군별 공급 집중도"):
    st.html('<div class="note" style="margin-bottom:4px">탭을 누르면 품목군이 바뀝니다 — 품목군별 공급 국가 비중입니다'
            f'({year}년 수입액 상위 5개 품목군 · 수입 기준, 오른쪽 탭은 수출 기준).</div>')
    focus = [sel] if sel != ALL else imp_rank.index[:5].tolist()
    dy = trade[(trade["year"] == year) & trade["hs6"].isin(focus)]
    hhi_all = load_hhi(year).set_index("hs6")
    labels = [f"{name_of_hs[h]} · 수입" for h in focus] + [f"{name_of_hs[h]} · 수출" for h in focus]
    for tab, (h, col, ax) in zip(st.tabs(labels), [(h, "imp_dlr", "수입") for h in focus] + [(h, "exp_dlr", "수출") for h in focus]):
        g = dy[dy["hs6"] == h].groupby("country")[col].sum()
        g = g[g > 0].sort_values(ascending=False)
        if g.empty:
            tab.info(f"{year}년 {ax} 실적이 없습니다(실제 0).")
            continue
        shares = [(n, v / g.sum() * 100) for n, v in g.items()]
        cc = country_colors([code_of.get(n, n) for n in g.index[:5]])
        hv = hhi_all.loc[h, "hhi_imp" if ax == "수입" else "hhi_exp"] if h in hhi_all.index else float("nan")
        tab.html(share_card({"name": name_of_hs[h], "hs": h, "shares": shares, "n": len(g), "axis": ax, "year": year,
                             "hhi": float(hv) if pd.notna(hv) else 0.0,
                             "colors": {n: cc[code_of.get(n, n)] for n in g.index[:5]}}))
        chart_source(SRC_TRADE + " · 집중도(HHI)는 연도별 값", where=tab)

# ── 세계 지도 ────────────────────────────────────────────────────────────────
with zone("map", "세계 지도"):
    with st.container(border=True, key="card_choro"):
        geo = d[d["year"] == year].groupby("country")[["imp_dlr", "exp_dlr"]].sum()
        chart_title(f'{year}년{ptag} 1위 국가는 <span class="key">수입 {escape(str(imp_top))} · 수출 {escape(str(exp_top))}</span>'
                    f'(수입의 {by_c.loc[imp_top, "imp_dlr"] / cur.imp_dlr * 100:.1f}% · 수출의 {by_c.loc[exp_top, "exp_dlr"] / cur.exp_dlr * 100:.1f}%)',
                    "색 = 합계 대비 비중 · 상위 6개국 라벨 · 오른쪽 위에서 수출로 전환")
        where = {n: (float(la), float(lo)) for n, la, lo in
                 d[["country", "lat", "lon"]].drop_duplicates("country").itertuples(index=False) if pd.notna(la)}
        country_map({n: m6(v) for n, v in geo["imp_dlr"].items() if v > 0},
                    {n: m6(v) for n, v in geo["exp_dlr"].items() if v > 0}, height=520, where=where)
        chart_source(SRC_TRADE + " · 국가 좌표는 나라 대표 위치 · 수입 = 선적국, 수출 = 도착국")

# ── 과천시 소재 수입자 비중(추정) — 품목군 × 연도 히트맵(dashboard/specs/24_gwacheon_share.md, M7) ─────────────
s_region = data_stamp("customs_region", "clean_customs_region")
SRC_GC = ("관세청 시군구별 품목별 수출입실적(15134343) · 수입 = 납세의무자 주소지 기준 · 분모 = 전국 수입액 · "
          f"자료 기간 {s_region['period'] if s_region['has_period'] else '—'}")
with zone("gwacheon", "과천시 소재 수입자 비중(추정)"):
    with st.container(border=True, key="card_gc"):
        try:
            gc = load_gwacheon(tuple(analysis_hs))
        except Exception as e:   # noqa: BLE001 — 클래스명만(접속 정보 노출 금지)
            gc = None
            st.error(f"조회 실패({type(e).__name__}) — 페이지를 새로 고쳐 다시 조회해 주세요.")
        if gc is not None and gc.empty:
            st.info("관세청 시군구별 집계가 아직 적재되지 않았습니다(미적재).")
        elif gc is not None:
            gc = gc.assign(pct=gc["gwacheon_share"].astype(float) * 100)
            gc_years = sorted(int(y) for y in gc["year"].unique())
            gc_partial = {int(y) for y in gc.loc[gc["is_partial_year"] == 1, "year"].unique()}
            gc_last = max(y for y in gc_years if y not in gc_partial)
            last = gc[gc["year"] == gc_last].set_index("hs6")["pct"]
            order = last.sort_values(ascending=True).index.tolist()           # 히트맵은 아래에서 위로 그려진다 → 위가 가장 높다
            order += [h for h in analysis_hs if h not in order]
            piv = gc.pivot_table(index="hs6", columns="year", values="pct", aggfunc="sum").reindex(index=order, columns=gc_years)
            top_h = last.idxmax()
            gc_title = (f'{gc_last}년 과천시 소재 수입자 비중(추정)은 '
                        f'<span class="key">{escape(name_of_hs.get(top_h, top_h))} {last.max():.1f}%</span>가 가장 높다')
            chart_title(gc_title, "관세청 수입액 중 수입자 주소지가 경기 과천시인 몫 · 셀 = % · "
                        + (f"{', '.join(map(str, sorted(gc_partial)))}년은 부분연도 · " if gc_partial else "") + "하한 · 상한 아님")
            xs = [f"{y}(부분)" if y in gc_partial else str(y) for y in gc_years]
            ys = [f"{name_of_hs.get(h, h)} {h}" for h in piv.index]
            z = piv.to_numpy()
            fig = go.Figure(go.Heatmap(
                z=z, x=xs, y=ys, zmin=0, zmax=max(35.0, float(pd.Series(z.ravel()).max())),
                colorscale=[[0, "#f4f8fe"], [1, IMP]], xgap=2, ygap=2,
                text=[[("" if pd.isna(v) else f"{v:.1f}") for v in row] for row in z], texttemplate="%{text}",
                textfont=dict(size=12), colorbar=dict(title="%", thickness=10, len=0.8),
                hovertemplate="%{y}<br>%{x}년 과천 비중 %{z:.1f}%<extra></extra>"))
            fig.update_layout(height=30 * len(ys) + 110, margin=dict(l=190, r=20, t=10, b=30))
            fig.update_xaxes(type="category", side="bottom")
            st.plotly_chart(style_fig(fig), width="stretch", theme=None, config=PLOT_CFG, key="p1_gc_heat")
            st.html('<div class="caption">「과천시 소재 수입자 비중(방위사업청 소재지), 추정」 — 관측값은 납세의무자 주소지 기준 신고액이고, '
                    '그 신고자가 방위사업청인지는 공개 자료로 확인되지 않았습니다(가설). 과천 소재 민간 수입자가 섞이거나 위탁 업체 명의 수입이 '
                    '빠질 수 있어 군 몫의 하한도 상한도 아닙니다.</div>')
            chart_source(SRC_GC)
            png_button(fig, "수출입_과천소재수입자비중_추정", align="flex-start", title=gc_title, source="출처: " + SRC_GC)

# ── 표 · 내려받기 ─────────────────────────────────────────────────────────────
tbl = by_c.sort_values("imp_dlr", ascending=False).reset_index()
tbl["수입 점유율(%)"] = (tbl["imp_dlr"] / tbl["imp_dlr"].sum() * 100).round(2)
tbl["수출 점유율(%)"] = (tbl["exp_dlr"] / tbl["exp_dlr"].sum() * 100).round(2)
tbl = tbl.rename(columns={"country": "국가", "imp_dlr": "수입액(USD)", "exp_dlr": "수출액(USD)"})
csv_head = csv_header(f"{scope} · {year}년{ptag} · {SCOPE_LABEL}", SOURCE, [("관세청", stamp, None)],
                      "국가는 선적국·도착국(관세청 통계 기준, 원산지 아님). 금액 USD")
with zone("tbl", "집중도 · 표 · 내려받기"):
    with st.container(border=True, key="card_tbl"):
        top5_share = tbl["수입 점유율(%)"].head(5).sum()
        chart_title(f'{year}년{ptag} 수입국은 {n_imp}개, 수출국은 {n_exp}개 — 수입 상위 5개국이 '
                    f'<span class="key">{top5_share:.1f}%</span>를 차지한다',
                    "수입액 내림차순 · 금액 USD · 점유율 %")
        st.dataframe(tbl, hide_index=True, width="stretch", height=320,
                     column_config={"수입액(USD)": st.column_config.NumberColumn(format="localized"),
                                    "수출액(USD)": st.column_config.NumberColumn(format="localized")})
        st.download_button("국가별 표 CSV 내려받기", (csv_head + tbl.to_csv(index=False)).encode("utf-8-sig"),
                           file_name=f"trade_{'all13' if sel == ALL else sel}_{year}.csv", mime="text/csv",
                           key="p1_csv", icon=":material/download:", type="primary")
        chart_source(SRC_TRADE + " · 국가는 선적국 · 도착국(원산지 아님)")
    if not hhi.empty:
        with st.container(border=True, key="card_hhi_tbl"):
            show = hhi.sort_values("hhi_imp", ascending=False)[["hs6", "name_ko", "hhi_imp", "top1_imp", "top1_share_imp", "n_imp",
                                                                  "hhi_exp", "top1_exp", "top1_share_exp", "n_exp"]].copy()
            for c in ("top1_imp", "top1_exp"):
                show[c] = show[c].map(lambda x: name_of_cd.get(x, x))
            show["top1_share_imp"] = (show["top1_share_imp"] * 100).round(1)
            show["top1_share_exp"] = (show["top1_share_exp"] * 100).round(1)
            show = show.rename(columns={"hs6": "HS6", "name_ko": "품목군", "hhi_imp": "수입 HHI", "top1_imp": "1위 수입국",
                                        "top1_share_imp": "1위 수입 점유율(%)", "n_imp": "수입국 수", "hhi_exp": "수출 HHI",
                                        "top1_exp": "1위 수출국", "top1_share_exp": "1위 수출 점유율(%)", "n_exp": "수출국 수"})
            k_hi = int((show["수입 HHI"] >= 2500).sum())
            chart_title(f'{year}년 {len(show)}개 품목군 중 <span class="key">{k_hi}개</span>가 수입 HHI 2,500 이상(높은 집중)이다',
                        "연도별 값 · HHI 0~10,000 · 수입 HHI 내림차순")
            st.dataframe(show, hide_index=True, width="stretch", height=min(480, 40 + 36 * len(show)),
                         column_config={"수입 HHI": st.column_config.NumberColumn(format="localized"),
                                        "수출 HHI": st.column_config.NumberColumn(format="localized")})
            st.download_button("집중도 표 CSV 내려받기", (csv_header(f"{scope} · {year}년 · 연도별 HHI", SOURCE, [("관세청", stamp, None)],
                               "HHI = Σ(국가 점유율 × 100)², 0~10,000 · 국가 전체 교역 기준") + show.to_csv(index=False)).encode("utf-8-sig"),
                               file_name=f"hhi_{'all13' if sel == ALL else sel}_{year}.csv", mime="text/csv", key="p1_csv_hhi",
                               icon=":material/download:")
            chart_source(SRC_HHI)
    if sel != ALL:
        with st.expander(f"{year}년 HS10 세부 품목 표 — {sel}"):
            h10 = load_hs10(sel, year)
            if h10.empty:
                st.info("해당 연도에 HS10 세부 행이 없습니다.")
            else:
                h10["수입 비중(%)"] = (h10["imp_dlr"] / h10["imp_dlr"].sum() * 100).round(1) if h10["imp_dlr"].sum() else 0.0
                h10 = h10.rename(columns={"hs10": "HS10", "name_ko": "품명(관세청 HS부호 단위별 품목명)", "imp_dlr": "수입액(USD)",
                                          "exp_dlr": "수출액(USD)", "imp_countries": "수입국 수", "exp_countries": "수출국 수"})   # 실적 > 0 국가만(00_common §4)
                if h10["수입액(USD)"].sum() > 0:
                    t10 = h10.iloc[0]
                    chart_title(f'HS10 {len(h10)}개 중 <span class="key">{t10["HS10"]}</span>이 수입액의 {t10["수입 비중(%)"]:.1f}%를 차지한다',
                                f"{sel} · {year}년 · 수입액 내림차순 · 금액 USD")
                st.dataframe(h10, hide_index=True, width="stretch")
                st.download_button("HS10 표 CSV 내려받기", (csv_header(f"{sel} · {year}년 HS10", SOURCE + " · 관세청 HS부호 단위별 품목명(15130660)",
                                   [("관세청", stamp, None)]) + h10.to_csv(index=False)).encode("utf-8-sig"),
                                   file_name=f"hs10_{sel}_{year}.csv", mime="text/csv", key="p1_csv_h10")
                chart_source(f"관세청 · 품목별 국가별 수출입실적(15100475) · HS10 품명은 관세청 HS부호 단위별 품목명(15130660) · {STAMP_TXT}")
    with st.expander("산식 · 출처 · 표현 범위"):
        st.markdown("**수입액·수출액** = 관세청 수입·수출 금액(USD) 합(HS10→HS6 합산, 총계 행 제외). 백만 USD = USD ÷ 10⁶.  \n"
                    "**전년 대비** = (당해 ÷ 전년 − 1) × 100. 완결 연도끼리만 계산.  \n"
                    "**점유율** = 국가 금액 ÷ 해당 연도 합계 × 100.  \n"
                    "**HHI** = Σ(국가 점유율 × 100)², 0~10,000. 이 화면은 **연도별** 값. 홈·검토 목록의 「기간 합계 HHI」와 다른 지표.  \n"
                    "**국가** = 관세청 통계의 선적국·도착국. 원산지가 아닙니다.  \n\n"
                    "**표현 범위** — 국가 전체(민수 포함) 교역액이며 군수 수요 규모나 국방 부품의 해외 조달 비중을 뜻하지 않습니다. "
                    "FSC·NSN·조달 예산과 연결하지 않으며 특정 기업을 지목하지 않습니다.  \n\n"
                    f"**출처** — {SOURCE}. 자료 기간 {stamp['period']}.")

st.html('<div class="caption" style="margin-top:16px">수입액·수출액은 국가 전체(민수 포함) 교역액이며 군수 수요 규모를 뜻하지 않습니다.</div>'
        + source_pop(f'{SOURCE} · 자료 기간 {stamp["period"]}'))
