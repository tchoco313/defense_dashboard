"""③ 품목군 현황표 — 분석 대상 품목군(evidence_basis='rule')을 한 표로(선정 근거 · 수입 집중 지표 · 수출/수입 비율 · 관련 군급 후보).

기획서 v6 §수행 방향 ③: 선정 근거 · 수입액 · 1위국 · 점유율 · HHI · 수출/수입 비율 · 관련 군급, 정렬·필터, 수입액 × HHI 산점도, CSV.
트리맵(분류 › 품목군 수입액 구성)은 2026-09-20 벤치마킹(SIPRI) 반영.
- 지표는 기간 기준(홈과 같은 3개 선택지) 합계로 다시 계산한다(metrics.concentration — 홈·🔎 KPI 와 같은 산식). 여러 해를 고르면
  기간 합계의 국가 점유율로 HHI를 낸다(연도별 HHI의 평균이 아니다). 부분연도는 선택지에 넣지 않는다.
- 수입국 수 = 기간 합계 수입액 > 0 인 국가 수(수출만 있는 국가는 빼며, DB 뷰 v_hhi_hs6_year.country_count 와 다른 정의).
- 선정 근거는 ref_hs_whitelist.evidence(규칙 스냅샷 키)를 R1~R4로 읽는다. R4(B2 대응)는 잠정(대응표 미확정, 2026-09-18) —
  R3∧R4 로만 진입한 품목군은 metrics.r4_provisional 로 표시한다.
- 관련 군급은 related_fsc 후보값 — HS6↔FSC4 공식 연계표가 없어 확정하지 않는다(CLAUDE.md 핵심 설계 제약).
- 과천시 소재 수입자 비중(추정) 열은 두지 않는다 — 시군구별 수입 미적재이고 채택 여부는 팀 결정(⑤ 참고).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import data_stamp, db_ready, query  # noqa: E402
from metrics import concentration, r4_provisional  # noqa: E402
from ui import (ACCENT, BG, MUTED, PANEL, PANEL2, SHORT, TEXT, country_colors, csv_header,  # noqa: E402
                period_control, style_fig, zone)

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
    years, y_label = period_control(trade, "기간 기준을 바꾸면 표 · 산점도 · 내려받는 CSV가 같은 기준으로 다시 계산됩니다",
                                    key="period_p3")
    if not years:
        st.stop()
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    cats = sorted(wl["category"].unique())
    pick = c1.multiselect("분류", cats, default=cats, placeholder="분류를 고르세요")
    only50 = c2.toggle("1위 공급국 50% 이상만", value=False)

# ── 계산(기간 합계) — 국가별로 선택 연도를 먼저 합산한 뒤 점유율·HHI·수입국 수(홈·🔎 와 같은 metrics.concentration) ──────
sel = trade[trade["year"].isin(years)]
conc = concentration(sel, "imp_dlr").set_index("hs6")          # 수입 실적(>0) 없는 hs6 는 여기 없다 → join 뒤 NaN = 자료 없음
exp_sum = sel.groupby("hs6")["exp_dlr"].sum()                     # 수출/수입 비율의 분자(수입 0 국가의 수출도 포함)
first_year = trade.groupby("hs6")["year"].min()
full = trade[trade["is_partial_year"] == 0].groupby(["hs6", "year"])["imp_dlr"].sum() / 1e6
trend = full.groupby(level="hs6").apply(list)

t = wl.set_index("hs6").join([conc[["total", "hhi", "country_count"]].rename(columns={"total": "imp_dlr", "country_count": "n_ctry"}),
                              exp_sum.rename("exp_dlr")], how="left")
t["top1_cd"] = conc["top1_stat_cd"]
t["top1"] = t["top1_cd"].map(lambda c: cname.get(c, c) if isinstance(c, str) else "—")
t["top1_share"] = conc["top1_share"] * 100
t["ratio"] = t["exp_dlr"] / t["imp_dlr"]
t["rules"] = t["evidence"].map(rule_text)
t["r4_only"] = t["evidence"].map(r4_provisional)
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
            "1위 공급국": t["top1"], "1위 점유율(%)": t["top1_share"], "HHI": t["hhi"].round(0),
            "수입국 수": t["n_ctry"].astype("Int64"),
            "수출/수입": t["ratio"], "관련 군급(후보)": t["related_fsc"].fillna("—").str.replace(";", " · "),
            "수입 추이(백만$)": t["trend"],
        }).reset_index(drop=True)
        st.dataframe(view, hide_index=True, width="stretch", height=min(38 + 35 * len(view), 720), column_config={
            f"수입액(백만$, {y_label})": st.column_config.NumberColumn(format="localized"),
            "1위 점유율(%)": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
            "HHI": st.column_config.NumberColumn(format="localized", help="Σ(국가 점유율 %)². 2,500 이상 = 높은 집중(미 법무부 기준)"),
            "수입국 수": st.column_config.NumberColumn(format="localized", help="기간 합계 수입액이 0보다 큰 국가 수(수출만 있는 국가 제외)"),
            "수출/수입": st.column_config.NumberColumn(format="%.2f", help="1보다 크면 수출이 수입보다 많음. HS6 합계라 민수 반도체가 대부분"),
            "관련 군급(후보)": st.column_config.TextColumn(help="HS6↔FSC4 공식 연계표가 없어 확정하지 않은 후보값"),
            "수입 추이(백만$)": st.column_config.LineChartColumn(help="완결 연도(부분연도 제외) 연간 수입액"),
        })
        r4_list = ", ".join(f"{h} {s}" for h, s in zip(t.index[t["r4_only"]], t.loc[t["r4_only"], "short"]))
        notes = ["표 머리를 누르면 정렬됩니다. 기본 정렬은 HHI 내림차순",
                 "R1~R3 = 관세청 분류표·전략물자 고시 등 공식 자료에 팀 규칙을 적용한 것, *R4 = B2 국산화개발품목 대응(잠정 — 대응표 미확정)",
                 (f"R3∧R4 로만 진입해 R4 잠정 근거에 기대는 품목군 {int(t['r4_only'].sum())}개: {r4_list}" if r4_list
                  else "이 표에는 R3∧R4 로만 진입한 품목군이 없습니다"),
                 "여러 해를 고르면 기간 합계 점유율로 HHI 계산(연도별 HHI 평균 아님) · 수입국 수 = 수입 실적(>0) 있는 국가 수"]
        if t["late"].any():
            notes.append(f"HS6 * = {years[0]}년 이후 일부 연도만 집계(HS 개정)")
        notes.append("과천시 소재 수입자 비중(추정) 열은 두지 않습니다 — 시군구별 수입 미적재, 채택 여부 팀 결정(⑤ DATA INFO)")
        if not missing.empty:
            notes.append(f"{y_label} 관세청 수입 실적(>0)이 없어 표에서 뺀 품목군: "
                         + ", ".join(f"{h} {n}" for h, n in zip(missing.index, missing["short"])))
        st.html('<div class="note">' + "<br>".join("· " + n for n in notes) + "</div>")

        cond = f"기간 {y_label} · 분류 {', '.join(pick)}" + (" · 1위 공급국 50% 이상만" if only50 else "")
        head = csv_header(cond, SOURCE, [("관세청 수출입", data_stamp("customs_all", "fact_customs_monthly"), None)],
                          extra="HHI = 기간 합계 점유율 기준 · 수입국 수 = 수입 실적(>0) 국가 수")
        csv = head + view.drop(columns=["수입 추이(백만$)"]).to_csv(index=False)
        st.download_button("⬇ 표 CSV 내려받기(엑셀)", csv.encode("utf-8-sig"), mime="text/csv",
                           file_name=f"품목군_현황표_{y_label.replace('~', '-')}.csv")

# ── 트리맵: 분류 > 품목군 수입액 구성(색 = 1위 공급국 점유율) ────────────────────
tree = t[(t["imp_dlr"] > 0) & t["top1_share"].notna()].copy()
if not tree.empty:
    with zone("p3_tree", "수입액 구성"):
        tree["mil"] = tree["imp_dlr"] / 1e6
        tree["label"] = [f"{s}<br>{c} {p:.0f}%" for s, c, p in zip(tree["short"], tree["top1"], tree["top1_share"])]
        fig_t = px.treemap(tree, path=[px.Constant(f"{len(tree)}개 품목군"), "category", "label"], values="mil",
                           color="top1_share", color_continuous_scale=[PANEL2, ACCENT], range_color=[0, 100],
                           title=f"분류 › 품목군 수입액 구성 — {y_label} · 면적 = 수입액 · 색 = 1위 공급국 점유율")
        fig_t.update_traces(marker=dict(line=dict(color=BG, width=2)), textfont=dict(color=TEXT, size=12), root_color=PANEL,
                            hovertemplate="%{label}<br>수입 %{value:,.0f}백만$<br>1위 공급국 점유율 %{color:.1f}%<extra></extra>")
        fig_t.update_layout(margin=dict(t=50, b=10, l=0, r=0),
                            coloraxis_colorbar=dict(title="1위 점유율(%)", thickness=12, tickfont=dict(color=MUTED)))
        st.plotly_chart(style_fig(fig_t, 460), width="stretch", theme=None)
        st.html('<div class="note">칸을 누르면 그 분류만 크게 봅니다(위쪽 경로를 누르면 돌아옵니다). 분류 칸의 색은 속한 품목군의 수입액 가중평균입니다. '
                '국가 전체 수입(민수 포함) 기준이며 군수 수요 비중이 아닙니다.</div>')

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
