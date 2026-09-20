"""홈 — 한눈에 보는 KPI · 어디서 들어오나(지도 · 1위 공급국 점유율) · 안내와 한계.

디자인: docs/report/mockup-2026-09-18/main.html. 데이터 판정: docs/report/data-usage-decision-2026-09-18.md §4.
- 분석 대상 = ref_hs_whitelist 중 evidence_basis='rule'(19개). 수입액은 국가 전체 수입(민수 포함).
- 기간 기준(기준 연도 / 최근 5년 / 전체)은 KPI 1~3과 지도·막대에만 적용. 부분연도(예: 2026.01~08)는 빼고 센다.
- KPI 4(국외 조달계획)는 정제 전 raw 에서 NSN 13자리 · FSG 58·59 행만 센 잠정값. KPI 5는 B2 정제본 스냅샷.
  둘 다 기간 기준과 무관하며, 테이블이 없으면 「—」로 비운다.
"""
from __future__ import annotations

import sys
from html import escape
from math import sqrt
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import db_ready, query, safe_query  # noqa: E402
from ui import BG, MUTED, SHORT, TEXT, country_colors, kpi, period_control, zone  # noqa: E402

# 지도 라벨 위치(목업과 같게 — 동아시아 원이 겹치지 않도록). 없으면 아래 가운데
LABEL_POS = {"TW": "middle right", "MY": "middle left", "US": "top center", "CN": "top left", "SG": "bottom center", "VN": "middle left",
             "JP": "top right", "KR": "top right"}

if not db_ready():
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> dict:
    wl = query("SELECT hs6, name_ko FROM ref_hs_whitelist WHERE evidence_basis = 'rule'")
    imp = query("""
        SELECT hs6, year, stat_cd, imp_dlr, is_partial_year
        FROM v_import_hs6_year WHERE hs6 IN :hs AND imp_dlr > 0
    """, {"hs": wl["hs6"].tolist()})
    ctry = query("SELECT stat_cd, name_ko, lat, lon FROM ref_country")
    rule = safe_query("SELECT COUNT(*) AS n FROM ref_hs_rule_flag")
    plan = safe_query(r"""
        SELECT COUNT(*) AS n,
               COUNT(DISTINCT CASE WHEN equipment_name <> '' AND equipment_name NOT LIKE '%*%' THEN equipment_name END) AS eq,
               MIN(demand_year_req) AS y0, MAX(demand_year_req) AS y1
        FROM raw_dapa_overseas_plan_api
        WHERE stock_no REGEXP '^[0-9]{13}$' AND LEFT(stock_no, 2) IN ('58', '59')
    """)
    b2 = safe_query("""
        SELECT COUNT(DISTINCT part_mgmt_no) AS n, COUNT(DISTINCT project_name) AS p,
               (SELECT COUNT(DISTINCT project_name) FROM clean_dapa_localized_item) AS p_all
        FROM clean_dapa_localized_item WHERE is_electronic_group = 1
    """)
    return dict(wl=wl, imp=imp, ctry=ctry, rule=rule, plan=plan, b2=b2)


def first_val(df: pd.DataFrame | None, col: str):
    """safe_query 결과의 첫 값. 테이블 없음·0건이면 None."""
    if df is None or df.empty or pd.isna(df.iloc[0][col]) or df.iloc[0][col] == 0:
        return None
    return df.iloc[0][col]


with st.spinner("팀 DB 조회 중…"):
    d = load()
wl, imp, ctry = d["wl"], d["imp"], d["ctry"]
names = {r.hs6: SHORT.get(r.hs6, r.name_ko) for r in wl.itertuples()}
cname = dict(zip(ctry["stat_cd"], ctry["name_ko"]))

# ── KPI ─────────────────────────────────────────────────────────────────────
with zone("kpi", "한눈에 보는 KPI"):
    years, y_label = period_control(imp, "기간 기준을 바꾸면 KPI 1~3 · 지도 · 점유율 막대가 같은 기준으로 다시 계산됩니다")

    sel = imp[imp["year"].isin(years)]
    by_c = sel.groupby(["hs6", "stat_cd"], as_index=False)["imp_dlr"].sum()
    by_c["share"] = by_c["imp_dlr"] / by_c.groupby("hs6")["imp_dlr"].transform("sum")
    top1 = by_c.sort_values("share", ascending=False).drop_duplicates("hs6")
    total = float(sel["imp_dlr"].sum())

    n_rule = first_val(d["rule"], "n")
    plan_n, plan_eq = first_val(d["plan"], "n"), first_val(d["plan"], "eq")
    b2_n, b2_p = first_val(d["b2"], "n"), first_val(d["b2"], "p")
    plan_sub = (f"적용장비 {plan_eq or 0:,}종 · NSN 기준 FSG 58·59 · {d['plan'].iloc[0]['y0']}~{d['plan'].iloc[0]['y1']}"
                if plan_n else "조달계획 API 적재 후 표시")

    st.html('<div class="kpis">'
            + kpi("분석 대상 품목군", f"{len(wl)}", "개",
                  f"HS6 {n_rule:,}개 → 규칙 2단계 선정" if n_rule else "법령·분류코드 규칙으로 선정")
            + kpi(f"{y_label} 수입액 ({len(wl)}개 합)", f"{total / 1e8:,.0f}", "억 달러", "국가 전체 수입 · 민수 포함")
            + kpi("특정국 50% 이상 품목군", f"{int((top1['share'] >= 0.5).sum())}", "개", f"1위 공급국 점유율 기준 · {y_label}")
            + kpi("전자 군급 국외 조달계획", f"{plan_n:,}" if plan_n else "—", "건" if plan_n else "", plan_sub, "잠정")
            + kpi("국산화개발 전자 부품", f"{b2_n:,}" if b2_n else "—", "개" if b2_n else "",
                  f"FSG 58·59 · 지상 {first_val(d['b2'], 'p_all')}개 사업 중 {b2_p}개" if b2_n else "B2 정제본 적재 후 표시")
            + "</div>")

# ── 어디서 들어오나 ─────────────────────────────────────────────────────────
first_year = imp.groupby("hs6")["year"].min()
late = sorted(set(first_year[first_year > years[0]].index) & set(top1["hs6"]))  # 기간 중간부터 집계(HS 개정)
colors = country_colors(top1["stat_cd"].tolist())

with zone("where", "어디서 들어오나"):
    c_map, c_bar = st.columns([1.35, 1], gap="medium")

    with c_map.container(border=True, key="card_map"):
        st.html(f'<div class="h">국가별 수입 규모 <span class="sub">품목군별 1위 공급국 · 원 크기 = '
                f'{len(wl)}개 품목군 수입액 합 · {y_label}</span></div>')
        leaders = top1.groupby("stat_cd")["hs6"].apply(list)
        pts = (sel[sel["stat_cd"].isin(leaders.index)].groupby("stat_cd", as_index=False)["imp_dlr"].sum()
               .merge(ctry, on="stat_cd", how="left").dropna(subset=["lat", "lon"]))
        pts["eok"] = pts["imp_dlr"] / 1e8
        label = [f"{cname.get(c, c)} {v:,.1f}억$" for c, v in zip(pts["stat_cd"], pts["eok"])]
        hover = [f"{t}<br>1위 품목군: " + ", ".join(names[h] for h in leaders[c]) for t, c in zip(label, pts["stat_cd"])]
        fig = go.Figure(go.Scattergeo(
            lat=pts["lat"], lon=pts["lon"], mode="markers+text", text=label,
            textposition=[LABEL_POS.get(c, "bottom center") for c in pts["stat_cd"]],
            textfont=dict(color=TEXT, size=12), hovertext=hover, hoverinfo="text",
            # 원 크기는 기간마다 최대값 기준(면적 ∝ 금액) — 10년 합에서도 원이 겹쳐 덮지 않도록
            marker=dict(size=[12 + 56 * sqrt(v / pts["eok"].max()) for v in pts["eok"]], color=[colors[c] for c in pts["stat_cd"]],
                        opacity=.85, line=dict(color=BG, width=1))))
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                          geo=dict(projection_type="natural earth", showland=True, landcolor="#232c40", showocean=True,
                                   oceancolor="#121827", showcountries=True, countrycolor="#33405c", coastlinecolor="#33405c",
                                   bgcolor="rgba(0,0,0,0)", showframe=False, lataxis_range=[-50, 75], lonaxis_range=[-130, 180]))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})

    rows = "".join(
        f'<div class="row" title="{escape(cname.get(r.stat_cd, r.stat_cd))} {r.share * 100:.1f}%">'
        f'<div class="nm">{escape(names[r.hs6])}<em>{r.hs6}{"*" if r.hs6 in late else ""}</em></div>'
        f'<div class="track"><div class="fill" style="width:{r.share * 100:.1f}%;background:{colors[r.stat_cd]}"></div>'
        f'<div class="ref"></div></div><div class="pct">{r.share * 100:.1f}%</div></div>'
        for r in top1.itertuples())
    legend = "".join(f'<span><i style="background:{col}"></i>{escape(cname.get(c, c))}</span>' for c, col in colors.items())
    foot = (f'<div class="note" style="margin-top:6px">* {", ".join(late)}: {years[0]}년 이후 일부 연도만 집계(HS 개정)</div>'
            if late else "")
    c_bar.html(f"""
<style>
.bars .row{{display:grid;grid-template-columns:128px 1fr 52px;align-items:center;gap:8px;height:21px;font-size:11.5px}}
.bars .nm{{color:{TEXT};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bars .nm em{{color:{MUTED};font-style:normal;font-size:10px;margin-left:3px}}
.bars .track{{position:relative;height:12px;border-radius:3px}}
.bars .fill{{position:absolute;left:0;top:0;bottom:0;border-radius:3px}}
.bars .ref{{position:absolute;top:-4px;bottom:-4px;left:50%;border-left:1px dashed #c9d2e6aa}}
.bars .pct{{text-align:right;color:{MUTED}}}
</style>
<div class="card"><div class="h">품목군별 1위 공급국 점유율 <span class="sub">{y_label} · 점선 = 50%</span></div>
<div class="bars">{rows}</div><div class="legend" style="margin-top:10px">{legend}</div>{foot}</div>""")

# ── 안내와 한계 ─────────────────────────────────────────────────────────────
with zone("guide", "안내와 한계"):
    st.html(f"""
<style>.tabs li{{list-style:none;font-size:12px;color:{MUTED};line-height:1.9}}
.tabs li b{{color:{TEXT};font-weight:600;margin-right:6px}}</style>
<div style="display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:12px">
 <div class="card"><div class="h">탭 안내</div><ul class="tabs" style="padding:0;margin:0">
  <li><b>①</b>품목군별 국가 구성·집중도 추이, 수입자 지역(군 직접 하한)</li>
  <li><b>②</b>전자 군급별 국외 조달계획 · 국산화 이력</li>
  <li><b>③</b>{len(wl)}개 품목군 한 표 비교 · CSV 내려받기</li>
  <li><b>④</b>예산 · 국외조달 · 국내 생산 기반</li>
  <li><b>🔎</b>조건을 골라 표·차트로 조회 · PNG/엑셀 저장</li></ul></div>
 <div class="card"><div class="h">읽는 법</div><div class="note">
  · 「수입 의존도」 = 품목군 수입액 중 특정국 비중(점유율·HHI)<br>
  · 국가 전체 수입으로 <b>민수가 포함</b>됩니다<br>
  · 군 직접 수입(과천)은 수입자 소재지 기반 <b>추정 하한</b><br>
  · 조달계획 ≠ 계약, 국산화개발 부품 수 ≠ 국산화율</div></div>
 <div class="card"><div class="h">출처</div><div class="note">
  관세청 품목별 국가별 수출입실적 · 시군구별 수출입실적<br>
  방위사업청 국외 조달계획 · 국산화개발품목 · 군급분류집<br>
  열린재정 예산 · KOSIS 방산 가동률 · 광공업생산지수<br>
  <span style="color:#6f7890">모든 수치에 기준일·산식 표시 · 상세는 ⑤ DATA INFO</span></div></div>
</div>""")

st.html('<div class="caption">「잠정」 = 정제·산출식 확정 전 값. 수입액은 관세청 품목별 국가별 수출입실적(USD) 합계이며 군수 수요 비중이 아닙니다.</div>')
