"""홈 — 한눈에 보는 KPI · 어디서 들어오나(지도 · 1위 공급국 점유율) · 안내와 한계.

디자인: docs/report/app/mockup-2026-09-18/main.html. 데이터 판정: docs/report/data/data-usage-decision-2026-09-18.md §4.
- 분석 대상 = ref_hs_whitelist 중 priority IN (1, 2) — 13개(2026-09-21 회의 M5: 진입식 R1 OR R2, R4 제외). 수입액은 국가 전체 수입(민수 포함).
  선정 근거는 공식 분류표·통제 목록의 규칙 R1·R2(군용전용·항공/항행 세분류). 회의 결정 반영표는 app/specs/00_common.md §8.
- 기간 기준(기준 연도 / 최근 5년 / 전체)은 KPI 1~3과 지도·막대에만 적용. 부분연도(예: 2026.01~08)는 빼고 센다.
  점유율·HHI 계산은 metrics.concentration(③·🔎 KPI 와 같은 산식: 선택 연도 합산 → 국가 점유율, 수입 실적>0 국가만).
- KPI 4(국외 조달계획)는 clean_dapa_overseas_plan_api 의 is_elec=1(FSG 58·59·60, 영숫자 NSN 포함 — 2026-09-21 M4 확정) 행 수.
  KPI 5는 B2 정제본(is_electronic_group=1) 스냅샷. 둘 다 기간 기준과 무관.
- KPI 4·5·규칙 건수는 캐시 밖에서 try_query 로 읽어 「조회 실패 / 적재 0건 / n」을 구분한다(실패값이 캐시에 남지 않게).
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
from db import db_ready, query, try_query  # noqa: E402
from metrics import concentration, count_state  # noqa: E402
from ui import BG, MUTED, PANEL2, SHORT, TEXT, country_colors, kpi, period_control, zone  # noqa: E402

# 지도 라벨 위치(목업과 같게 — 동아시아 원이 겹치지 않도록). 없으면 아래 가운데
LABEL_POS = {"TW": "middle right", "MY": "middle left", "US": "top center", "CN": "top left", "SG": "bottom center", "VN": "middle left",
             "JP": "top right", "KR": "top right"}

if not db_ready():
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> dict:
    wl = query("SELECT hs6, name_ko FROM ref_hs_whitelist WHERE priority IN (1, 2)")
    imp = query("""
        SELECT hs6, year, stat_cd, imp_dlr, is_partial_year
        FROM v_import_hs6_year WHERE hs6 IN :hs AND imp_dlr > 0
    """, {"hs": wl["hs6"].tolist()})
    ctry = query("SELECT stat_cd, name_ko, lat, lon FROM ref_country")
    return dict(wl=wl, imp=imp, ctry=ctry)


# 건수 KPI 3개 — 캐시 밖(try_query): 실패는 「조회 실패(클래스)」, 0행은 「적재 0건」, 그 외 n. 기대값은 문서(data-cleaning-rules §2-6)에만 둔다.
PLAN_SQL = """
    SELECT SUM(is_elec = 1) AS n, COUNT(*) AS n_all,
           COUNT(DISTINCT CASE WHEN is_elec = 1 AND is_equipment_missing = 0 THEN equipment_name END) AS eq,
           MIN(CASE WHEN is_elec = 1 THEN demand_year END) AS y0, MAX(CASE WHEN is_elec = 1 THEN demand_year END) AS y1
    FROM clean_dapa_overseas_plan_api
"""
B2_SQL = """
    SELECT COUNT(DISTINCT CASE WHEN is_electronic_group = 1 THEN part_mgmt_no END) AS n, COUNT(*) AS n_all,
           COUNT(DISTINCT CASE WHEN is_electronic_group = 1 THEN project_name END) AS p,
           COUNT(DISTINCT project_name) AS p_all
    FROM clean_dapa_localized_item
"""


def kpi_num(state: str, n: int | None, unit: str, sub_ok: str, err: str | None, sub_zero: str) -> tuple[str, str, str]:
    """count_state 결과 → (값, 단위, 설명).
    failed 「—」/조회 실패(<클래스>) · unloaded 「—」/미적재(0행) · zero 「0」/<sub_zero>(실제 0) · ok n/<sub_ok>."""
    if state == "failed":
        return "—", "", f"조회 실패({err}) — 아래 「다시 조회」"
    if state == "unloaded":
        return "—", "", "미적재(표에 0행)"
    if state == "zero":
        return "0", unit, sub_zero
    return f"{n:,}", unit, sub_ok


with st.spinner("팀 DB 조회 중…"):
    d = load()
    rule_df, rule_err = try_query("SELECT COUNT(*) AS n FROM ref_hs_rule_flag")
    plan_df, plan_err = try_query(PLAN_SQL)
    b2_df, b2_err = try_query(B2_SQL)
wl, imp, ctry = d["wl"], d["imp"], d["ctry"]
names = {r.hs6: SHORT.get(r.hs6, r.name_ko) for r in wl.itertuples()}
cname = dict(zip(ctry["stat_cd"], ctry["name_ko"]))

# ── KPI ─────────────────────────────────────────────────────────────────────
with zone("kpi", "한눈에 보는 KPI"):
    years, y_label = period_control(imp, "기간 기준을 바꾸면 KPI 1~3 · 지도 · 점유율 막대가 같은 기준으로 다시 계산됩니다",
                                    key="period_home")
    if not years:
        st.stop()

    sel = imp[imp["year"].isin(years)]
    conc = concentration(sel, "imp_dlr")                 # hs6 별 합계·1위국·점유율·HHI·수입국 수(③·🔎 와 같은 산식)
    top1 = conc.rename(columns={"top1_stat_cd": "stat_cd", "top1_share": "share"})
    total = float(conc["total"].sum())

    st_rule, n_rule = count_state(rule_df, rule_err, "n")
    st_plan, plan_n = count_state(plan_df, plan_err, "n", total_col="n_all")
    st_b2, b2_n = count_state(b2_df, b2_err, "n", total_col="n_all")
    rule_sub = (f"HS6 {n_rule:,}개에 " if st_rule == "ok" else "") + f"공식 분류·통제표 규칙 R1·R2 적용 · 수집 24개 중 {len(wl)}개"
    plan_sub = b2_sub = ""
    if st_plan == "ok":
        r = plan_df.iloc[0]
        yr_txt = f"{int(r['y0'])}~{int(r['y1'])}" if pd.notna(r["y0"]) and pd.notna(r["y1"]) else "—"
        plan_sub = f"적용장비 {int(r['eq']):,}종 · FSG 58·59·60 · 요구연도 {yr_txt}"
    if st_b2 == "ok":
        r = b2_df.iloc[0]
        b2_sub = f"전자 군급(is_electronic_group) · 지상 {int(r['p_all'])}개 사업 중 {int(r['p'])}개 · 국산화율 아님"

    st.html('<div class="kpis">'
            + kpi("분석 대상 품목군", f"{len(wl)}", "개", rule_sub)
            + kpi(f"{y_label} 수입액 ({len(wl)}개 합)", f"{total / 1e8:,.0f}", "억 달러", "국가 전체 수입 · 민수 포함 · 기간 합계")
            + kpi("특정국 50% 이상 품목군", f"{int((top1['share'] >= 0.5).sum())}", "개", f"1위 공급국 점유율 · {y_label} 합계 기준")
            + kpi("전자 군급 국외 조달계획", *kpi_num(st_plan, plan_n, "건", plan_sub, plan_err, "전자 군급(FSG 58·59·60) 행 0건"))
            + kpi("국산화개발 전자 부품", *kpi_num(st_b2, b2_n, "개", b2_sub, b2_err, "전자 군급 부품 0개"))
            + "</div>")
    if "failed" in (st_rule, st_plan, st_b2):
        if st.button("다시 조회", key="kpi_retry"):   # try_query 는 캐시되지 않으므로 rerun 이 곧 재시도. 캐시된 조회도 함께 비운다
            query.clear()
            st.rerun()

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
TABS = [("pages/1_수출입_현황.py", "①", "품목군별 수입·수출 국가 구성 · 집중도 추이 · 지도"),
        ("pages/2_부품_무기체계.py", "②", "전자 군급별 국외 조달계획 · 국산화 이력"),
        ("pages/3_품목군_현황표.py", "③", f"{len(wl)}개 품목군 한 표 비교 · CSV 내려받기"),
        ("pages/4_정책_산업_배경.py", "④", "예산 · 국외조달 · 국내 생산 기반"),
        ("pages/6_조회.py", "🔎", "조건을 골라 표·차트로 조회 · PNG/엑셀 저장")]

with zone("guide", "안내와 한계"):
    st.html(f"""<style>
.st-key-card_tabs [data-testid="stPageLink"] a{{padding:1px 6px;margin-left:-6px;border-radius:6px;background:transparent}}
.st-key-card_tabs [data-testid="stPageLink"] a:hover{{background:{PANEL2}}}
.st-key-card_tabs [data-testid="stPageLink"] a p{{font-size:12px;color:{MUTED}}}
.st-key-card_tabs [data-testid="stPageLink"] a p strong{{color:{TEXT};font-weight:600;margin-right:4px}}
.st-key-card_tabs [data-testid="stVerticalBlock"]{{gap:2px}}</style>""")
    c_tabs, c_read, c_src = st.columns([1.2, 1, 1], gap="small")
    with c_tabs.container(border=True, key="card_tabs", height="stretch"):
        st.html('<div class="h">탭 안내 <span class="sub">누르면 그 화면으로 갑니다</span></div>')
        for path, no, text in TABS:
            st.page_link(path, label=f"**{no}** {text}", width="stretch")
    with c_read.container(border=True, key="card_read", height="stretch"):
        st.html("""<div class="h">읽는 법</div><div class="note">
  · 「수입 집중도」 = 품목군 수입액 중 특정국 비중(1위 점유율·HHI)<br>
  · 국가 전체 수입으로 <b>민수가 포함</b>됩니다<br>
  · 군수 몫은 관세 통계로 나뉘지 않습니다 — 과천시 소재 수입자 비중은 <b>추정</b>(⑤ 참고)<br>
  · 조달계획 ≠ 계약, 국산화개발 부품 수 ≠ 국산화율</div>""")
    with c_src.container(border=True, key="card_src", height="stretch"):
        st.html("""<div class="h">출처</div><div class="note">
  관세청 품목별 국가별 수출입실적 · 시군구별 수출입실적<br>
  방위사업청 국외 조달계획 · 국산화개발품목 · 군급분류집<br>
  열린재정 예산 · KOSIS 방산 가동률 · 광공업생산지수<br>
  <span style="color:#6f7890">모든 수치에 기준일·산식 표시 · 상세는 ⑤ DATA INFO</span></div>""")

st.html('<div class="caption">수입액은 관세청 품목별 국가별 수출입실적(USD) 합계이며 군수 수요 비중이 아닙니다. '
        '품목군은 공식 분류·통제표의 규칙 R1·R2(군용전용 · 항공/항행 세분류)로 골랐습니다.</div>')
