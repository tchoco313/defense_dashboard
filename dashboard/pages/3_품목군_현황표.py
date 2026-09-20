"""③ 품목군 현황표 — 분석 대상 19개 품목군을 한 표로(선정 근거 · 수입 의존 지표 · 수출/수입 비율 · 관련 군급 후보).

기획서 v6 §수행 방향 ③: 선정 근거 · 수입액 · 1위국 · 점유율 · HHI · 수출/수입 비율 · 군 직접(하한) · 관련 군급, 정렬·필터,
수입액 × HHI 산점도, CSV.
- 지표는 기간 기준(홈과 같은 3개 선택지) 합계로 다시 계산한다. 여러 해를 고르면 기간 합계의 국가 점유율로 HHI를 낸다
  (연도별 HHI의 평균이 아니다). 부분연도는 넣지 않는다.
- 선정 근거는 ref_hs_whitelist.evidence(규칙 스냅샷 키)를 R1~R4로 읽는다. R4(B2 대응)는 잠정(대응표 미확정, 2026-09-18).
- 관련 군급은 related_fsc 후보값 — HS6↔FSC4 공식 연계표가 없어 확정하지 않는다(CLAUDE.md 핵심 설계 제약).
- 군 직접(하한, 과천) 열은 시군구별 수입 RDS 적재 뒤 붙인다. 지금은 열을 두지 않고 안내만 한다.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_ready, query  # noqa: E402
from ui import BG, MUTED, SHORT, TEXT, country_colors, period_control, style_fig, zone  # noqa: E402

# evidence 키 → 규칙(docs/reference/hs-whitelist-definition.md §8-2)
RULES = [("HSK-군용", "R1 군용전용"), ("HSK-항공/항행", "R2 항공·항행"), ("전략물자-DU", "R3 이중용도"), ("B2-FSC", "R4 국산화 대응*")]
SOURCE = "관세청 품목별 국가별 수출입실적(15100475) · 국가 전체 수입·수출(민수 포함) · USD"

if not db_ready():
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wl = query("""
        SELECT hs6, category, name_ko, evidence, related_fsc
        FROM ref_hs_whitelist WHERE evidence_basis = 'rule'
    """)
    trade = query("""
        SELECT hs6, year, stat_cd, imp_dlr, exp_dlr, is_partial_year
        FROM v_import_hs6_year WHERE hs6 IN :hs
    """, {"hs": wl["hs6"].tolist()})
    ctry = query("SELECT stat_cd, name_ko FROM ref_country")
    return wl, trade, ctry


def rule_text(evidence: str | None) -> str:
    keys = set((evidence or "").split(";"))
    hit = [label for key, label in RULES if key in keys]
    return " · ".join(hit) if hit else "—"


with st.spinner("팀 DB 조회 중…"):
    wl, trade, ctry = load()
cname = dict(zip(ctry["stat_cd"], ctry["name_ko"]))

st.html('<div class="page-h">③ 품목군 현황표</div>'
        f'<div class="note">분석 대상 {len(wl)}개 품목군을 한 표로 비교합니다 · {SOURCE}</div>')

# ── 조건 ────────────────────────────────────────────────────────────────────
with zone("p3_top", "조건"):
    years, y_label = period_control(trade, "기간 기준을 바꾸면 표 · 산점도 · 내려받는 CSV가 같은 기준으로 다시 계산됩니다")
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    cats = sorted(wl["category"].unique())
    pick = c1.multiselect("분류", cats, default=cats, placeholder="분류를 고르세요")
    only50 = c2.toggle("1위 공급국 50% 이상만", value=False)

# ── 계산(기간 합계) ──────────────────────────────────────────────────────────
sel = trade[trade["year"].isin(years)]
by_c = sel.groupby(["hs6", "stat_cd"], as_index=False)[["imp_dlr", "exp_dlr"]].sum()
imp_c = by_c[by_c["imp_dlr"] > 0].copy()
imp_c["share"] = imp_c["imp_dlr"] / imp_c.groupby("hs6")["imp_dlr"].transform("sum")
top1 = imp_c.sort_values("share", ascending=False).drop_duplicates("hs6").set_index("hs6")
agg = by_c.groupby("hs6")[["imp_dlr", "exp_dlr"]].sum()
hhi = imp_c.assign(sq=(imp_c["share"] * 100) ** 2).groupby("hs6")["sq"].sum()
n_ctry = imp_c.groupby("hs6")["stat_cd"].nunique()
first_year = trade.groupby("hs6")["year"].min()
full = trade[trade["is_partial_year"] == 0].groupby(["hs6", "year"])["imp_dlr"].sum() / 1e6
trend = full.groupby(level="hs6").apply(list)

t = wl.set_index("hs6").join([agg, hhi.rename("hhi"), n_ctry.rename("n_ctry")], how="left")
t["top1_cd"] = top1["stat_cd"]
t["top1"] = t["top1_cd"].map(lambda c: cname.get(c, c) if isinstance(c, str) else "—")
t["top1_share"] = top1["share"] * 100
t["ratio"] = t["exp_dlr"] / t["imp_dlr"]
t["rules"] = t["evidence"].map(rule_text)
t["short"] = [SHORT.get(h, n) for h, n in zip(t.index, t["name_ko"])]
t["trend"] = trend.reindex(t.index)
t["late"] = first_year.reindex(t.index) > years[0]
t = t[t["category"].isin(pick)]
missing = t[t["imp_dlr"].isna()]   # 관세청 수집 전 품목군(2026-09-16 추가 3개 등) — 빈 숫자 행 대신 안내로
t = t[t["imp_dlr"].notna()]
if only50:
    t = t[t["top1_share"] >= 50]
t = t.sort_values("hhi", ascending=False)  # 검토 정렬 = 수입 HHI 내림차순(CLAUDE.md)

# ── 표 ──────────────────────────────────────────────────────────────────────
with zone("p3_table", f"{len(t)}개 품목군 한 표"):
    if t.empty:
        st.info("조건에 맞는 품목군이 없습니다. 분류나 50% 필터를 바꿔 보세요.")
    else:
        view = pd.DataFrame({
            "HS6": [h + ("*" if late else "") for h, late in zip(t.index, t["late"])],
            "품목군": t["short"], "분류": t["category"], "선정 근거": t["rules"],
            f"수입액(백만$, {y_label})": (t["imp_dlr"] / 1e6).round(0),
            "1위 공급국": t["top1"], "1위 점유율(%)": t["top1_share"], "HHI": t["hhi"].round(0), "교역국 수": t["n_ctry"],
            "수출/수입": t["ratio"], "관련 군급(후보)": t["related_fsc"].fillna("—").str.replace(";", " · "),
            "수입 추이(백만$)": t["trend"],
        }).reset_index(drop=True)
        st.dataframe(view, hide_index=True, width="stretch", height=min(38 + 35 * len(view), 720), column_config={
            f"수입액(백만$, {y_label})": st.column_config.NumberColumn(format="localized"),
            "1위 점유율(%)": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
            "HHI": st.column_config.NumberColumn(format="localized", help="Σ(국가 점유율 %)². 2,500 이상 = 높은 집중(미 법무부 기준)"),
            "수출/수입": st.column_config.NumberColumn(format="%.2f", help="1보다 크면 수출이 수입보다 많음. HS6 합계라 민수 반도체가 대부분"),
            "관련 군급(후보)": st.column_config.TextColumn(help="HS6↔FSC4 공식 연계표가 없어 확정하지 않은 후보값"),
            "수입 추이(백만$)": st.column_config.LineChartColumn(help="완결 연도(부분연도 제외) 연간 수입액"),
        })
        notes = ["표 머리를 누르면 정렬됩니다. 기본 정렬은 HHI 내림차순",
                 "R1~R3 = 관세청 분류표·전략물자 고시에서 도출한 팀 규칙, *R4 = B2 국산화개발품목 대응(잠정 — 대응표 미확정)",
                 "여러 해를 고르면 기간 합계 점유율로 HHI 계산(연도별 HHI 평균 아님)"]
        if t["late"].any():
            notes.append(f"HS6 * = {years[0]}년 이후 일부 연도만 집계(HS 개정)")
        notes.append("군 직접 수입(과천, 하한) 열은 시군구별 수입 적재 뒤 추가됩니다")
        if not missing.empty:
            notes.append(f"{y_label} 관세청 수입 자료가 없어 표에서 뺀 품목군: "
                         + ", ".join(f"{h} {n}" for h, n in zip(missing.index, missing["short"])))
        st.html('<div class="note">' + "<br>".join("· " + n for n in notes) + "</div>")

        cond = f"기간 {y_label} · 분류 {', '.join(pick)}" + (" · 1위 공급국 50% 이상만" if only50 else "")
        head = f"# 조건: {cond}\n# 출처: {SOURCE}\n# 기준일: {date.today():%Y-%m-%d} · HHI = 기간 합계 점유율 기준\n"
        csv = head + view.drop(columns=["수입 추이(백만$)"]).to_csv(index=False)
        st.download_button("⬇ 표 CSV 내려받기(엑셀)", csv.encode("utf-8-sig"), mime="text/csv",
                           file_name=f"품목군_현황표_{y_label.replace('~', '-')}.csv")

# ── 산점도: 수입액 × HHI ─────────────────────────────────────────────────────
if not t.empty:
    with zone("p3_scatter", "수입 규모 × 집중도"):
        colors = country_colors(t["top1_cd"].dropna().tolist())
        fig = go.Figure()
        for cd, g in t.dropna(subset=["top1_cd"]).groupby("top1_cd", sort=False):
            fig.add_trace(go.Scatter(
                x=g["imp_dlr"] / 1e6, y=g["hhi"], mode="markers+text", name=cname.get(cd, cd),
                text=g["short"], textposition="top center", textfont=dict(size=11, color=TEXT),
                marker=dict(size=13, color=colors[cd], line=dict(color=BG, width=1)),
                customdata=g[["top1_share"]].values,
                hovertemplate="%{text}<br>수입 %{x:,.0f}백만$ · HHI %{y:,.0f}<br>1위 점유율 %{customdata[0]:.1f}%<extra></extra>"))
        fig.add_hline(y=2500, line=dict(color=MUTED, dash="dash", width=1),
                      annotation_text="HHI 2,500 높은 집중", annotation_font=dict(color=MUTED, size=11))
        fig.update_layout(title=f"수입액(로그) × HHI — {y_label} · 색 = 1위 공급국", margin=dict(t=60, b=40),
                          xaxis=dict(type="log", title="수입액(백만$, 로그 축)"), yaxis=dict(title="HHI", rangemode="tozero"),
                          legend=dict(orientation="h", y=-0.2, title=None))
        st.plotly_chart(style_fig(fig, 520), width="stretch", theme=None)
        st.html('<div class="note">오른쪽 위일수록 수입 규모가 크고 특정국에 몰려 있습니다. '
                '국가 전체 수입(민수 포함) 기준이며 군수 의존도가 아닙니다.</div>')

st.html(f'<div class="caption">출처: {SOURCE} → 팀 DB v_import_hs6_year · 선정 근거: ref_hs_whitelist.evidence '
        '(docs/reference/hs-whitelist-definition.md §8-2)</div>')
