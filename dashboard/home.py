"""홈 — 팀원 디자인 데모(K-Defense) 「HOME」 화면 배치를 그대로 옮기고 값만 RDS 로 바꿨다.

구역: 원천 확인 한 줄(live.py — 관세청 API 로 공개 최신 월을 직접 확인) → 핵심 KPI 5장 → 부품별 공급망 현황(품목군 표 + 스파크라인 · 핵심 지표) → 어디서 들어오나(지구본 · 1위 공급국 점유율 막대).
명세 app/specs/10_home.md. 데이터 판정: docs/report/data/data-usage-decision-2026-09-18.md §4.
- 분석 대상 = ref_hs_whitelist 중 priority IN (1, 2) — 13개(2026-09-21 회의 M5). 수입액은 국가 전체 수입(민수 포함).
- 기간 기준(기준 연도 / 최근 5년 / 전체)은 수입액 · 점유율 · HHI · 지구본 · 막대에 적용. 부분연도(예: 2026.01~08)는 빼고 센다.
  점유율·HHI 계산은 metrics.concentration(③·조회 와 같은 산식: 선택 연도 합산 → 국가 점유율, 수입 실적>0 국가만).
  화면 라벨은 「기간 합계 HHI」(M6 — ①의 연도별 HHI와 다른 값).
- 표의 추이(스파크라인)·변화율 = 적재된 마지막 달까지 최근 12개월 vs 그 전 12개월 월별 수입액(fact_customs_monthly, 부분연도 포함 월 단위).
- 국외 조달계획 KPI 는 clean_dapa_overseas_plan_api 의 is_elec=1(FSG 58·59·60, M4 확정) 행 수, 국산화개발 KPI 는 B2 정제본
  (is_electronic_group=1) 스냅샷. 둘 다 기간 기준과 무관. 캐시 밖 try_query 로 「조회 실패 / 적재 0건 / n」을 구분한다.
- 데모에서 뺀 것: 샘플 월별 추이(실측으로 대체), 「공급 국가」 지구본의 가짜 국가(실측 1위 공급국만).
"""
from __future__ import annotations

import re
from html import escape

import pandas as pd
import streamlit as st

import live
from db import data_stamp, query, try_query
from metrics import concentration, count_state
from kdesign import supply_globe
from ui import (source_pop, ETC, SHORT, chart_source, chart_title, core_kpis, country_colors, csv_header, globe_loading, hero, kpi,
                period_control, png_button, supply_table, zone)

E6 = 1e6   # 백만 달러 = USD ÷ 1e6 (표시 전용 변환)
# 화면 · CSV 출처는 「기관 · 데이터명(포털 ID) · 자료 기간」만 — DB 표 · 뷰 이름과 적재일은 쓰지 않는다(보안, 2026-09-24 사용자)
SOURCE_LINE = ("출처: 관세청 품목별 국가별 수출입실적 OpenAPI(15100475) · 방위사업청 국외 조달계획 OpenAPI(15158418) · "
               "방위사업청 국산화개발품목(15119899) · 분석 대상 품목군 기준표(팀 작성)")


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> dict:
    wl = query("SELECT hs6, name_ko FROM ref_hs_whitelist WHERE priority IN (1, 2)")
    imp = query("""
        SELECT hs6, year, stat_cd, imp_dlr, is_partial_year
        FROM v_import_hs6_year WHERE hs6 IN :hs AND imp_dlr > 0
    """, {"hs": wl["hs6"].tolist()})
    ctry = query("SELECT stat_cd, name_ko, lat, lon FROM ref_country")
    # 최근 24개월 월별 수입액(품목군별) — 적재된 마지막 달 기준
    last = query("SELECT MAX(yyyymm) AS ym FROM fact_customs_monthly")["ym"].iloc[0]
    ym0 = (pd.Period(f"{last[:4]}-{last[4:]}", "M") - 23).strftime("%Y%m")
    mon = query("""
        SELECT hs6, yyyymm, SUM(imp_dlr) AS imp_dlr FROM fact_customs_monthly
        WHERE hs6 IN :hs AND yyyymm BETWEEN :a AND :b GROUP BY hs6, yyyymm
    """, {"hs": wl["hs6"].tolist(), "a": ym0, "b": last})
    return dict(wl=wl, imp=imp, ctry=ctry, mon=mon, last=last, ym0=ym0)


# 건수 KPI — 캐시 밖(try_query): 실패는 「조회 실패(클래스)」, 0행은 「적재 0건」, 그 외 n.
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
    """count_state 결과 → (값, 단위, 설명). 실패 · 미적재 · 실제 0 · 값을 구분한다."""
    if state == "failed":
        return "—", "", f"조회 실패({err}) — 아래 「다시 조회」"
    if state == "unloaded":
        return "—", "", "미적재(표에 0행)"
    if state == "zero":
        return "0", unit, sub_zero
    return f"{n:,}", unit, sub_ok


def ym_txt(ym: str) -> str:
    return f"{ym[:4]}.{ym[4:]}"


s_customs = data_stamp("customs_all", "fact_customs_monthly")


def src_customs() -> str:
    """관세청 출처 한 줄 — 「기관 · 데이터명(포털 ID) · 자료 기간」(DB 표 이름 · 적재일은 쓰지 않는다)."""
    return (f"관세청 품목별 국가별 수출입실적(15100475) · 자료 기간 "
            f"{s_customs['period'] if s_customs['has_period'] else '—'}")


hero("주요 방산 전자부품 수출입 및 국산화 현황",
     "분석 대상 품목군의 수입 규모와 공급국 집중도, 조달 · 국산화 현황을 요약합니다",
     stamps=[("관세청 수출입", s_customs)])

with globe_loading("관세청·방위사업청 집계를 읽는 중"):
    d = load()
    rule_df, rule_err = try_query("SELECT COUNT(*) AS n FROM ref_hs_rule_flag")
    plan_df, plan_err = try_query(PLAN_SQL)
    b2_df, b2_err = try_query(B2_SQL)
wl, imp, ctry, mon = d["wl"], d["imp"], d["ctry"], d["mon"]
names = {r.hs6: SHORT.get(r.hs6, r.name_ko) for r in wl.itertuples()}
cname = dict(zip(ctry["stat_cd"], ctry["name_ko"]))

# ── 관세청 원천 최신 월 확인 — 페이지를 볼 때 관세청 API 에 직접 묻는다(6시간 캐시 · DB 값은 바꾸지 않음) ─────────
chk = live.source_check(str(d["last"]), wl["hs6"].tolist())
live_html = f'<b>원천 확인</b> · {escape(live.line_text(chk))}'
if chk["state"] == "newer" and chk["new"] is not None and not chk["new"].empty:
    nm = chk["new"][chk["new"]["yyyymm"] == chk["src_latest"]]
    live_html += (f' — <span class="key">{live.ym_dot(chk["src_latest"])} 분석 대상 {len(wl)}개 수입 '
                  f'{nm["imp"].sum() / E6:,.0f} · 수출 {nm["exp"].sum() / E6:,.0f} 백만 USD</span>'
                  '<span class="caption"> (관세청 직접 조회 · 화면 표 · 차트에는 아직 없음)</span>')
st.html(f'<div class="lede"><div class="note">{live_html}</div></div>')

# 기간 기준(부분연도 제외) — 데모 홈에는 없지만 수입액·집중도의 기준 기간을 밝혀야 해서 둔다
with st.container(key="filters_home"):
    years, y_label = period_control(imp, "기간 기준을 바꾸면 수입액 · 점유율 · HHI · 지구본 · 점유율 막대가 같은 기준으로 다시 계산됩니다",
                                    key="period_home")
if not years:
    st.stop()

sel = imp[imp["year"].isin(years)]
conc = concentration(sel, "imp_dlr")                 # hs6 별 합계·1위국·점유율·HHI·수입국 수
top1 = conc.rename(columns={"top1_stat_cd": "stat_cd", "top1_share": "share"})
total = float(conc["total"].sum())
by_year = imp[imp["is_partial_year"] == 0].groupby("year")["imp_dlr"].sum()
ly = years[-1]
yoy = (by_year.get(ly, 0) - by_year.get(ly - 1, 0)) / E6 if ly - 1 in by_year.index else None

# ── 한눈에 보는 KPI ─────────────────────────────────────────────────────────
n_wl_all = int(query("SELECT COUNT(*) AS n FROM ref_hs_whitelist").iloc[0]["n"])   # 수집 범위 HS6 수
st_rule, n_rule = count_state(rule_df, rule_err, "n")
st_plan, plan_n = count_state(plan_df, plan_err, "n", total_col="n_all")
st_b2, b2_n = count_state(b2_df, b2_err, "n", total_col="n_all")
plan_sub = b2_sub = ""
if st_plan == "ok":
    r = plan_df.iloc[0]
    yr_txt = f"{int(r['y0'])}~{int(r['y1'])}" if pd.notna(r["y0"]) and pd.notna(r["y1"]) else "—"
    plan_sub = f"적용장비 {int(r['eq']):,}종 · FSG 58·59·60 · 요구연도 {yr_txt}"
if st_b2 == "ok":
    r = b2_df.iloc[0]
    b2_sub = f"전자 군급 · 지상 {int(r['p_all'])}개 사업 중 {int(r['p'])}개 · 국산화율 아님"
k50 = int((top1["share"] >= 0.5).sum())
p_val, p_unit, p_sub = kpi_num(st_plan, plan_n, "건", plan_sub, plan_err, "전자 군급(FSG 58·59·60) 행 0건")
b_val, b_unit, b_sub = kpi_num(st_b2, b2_n, "개", b2_sub, b2_err, "전자 군급 부품 0개")
yoy_txt = (f'<span class="{"up" if yoy >= 0 else "dn"}">{"▲" if yoy >= 0 else "▼"} {yoy:+,.0f}</span> {ly}년 전년 대비 · '
           if yoy is not None else "")

with zone("kpi", "한눈에 보는 KPI"):
    st.html('<div class="kpis">'
            + kpi("분석 대상 품목군", f"{len(wl)}", "개",
                  (f"HS6 후보 {n_rule:,}개에 " if st_rule == "ok" else "") + f"진입 규칙(군용 전용 · 전문 용도 세분류) 적용 · 수집 {n_wl_all}개 중")
            + kpi(f"{y_label} 수입액", f"{total / E6:,.0f}", "백만 USD", yoy_txt + "국가 전체 수입 · 민수 포함")
            + kpi("특정국 50% 이상 품목군", f"{k50}", "개", f"1위 공급국 점유율 기준 · {y_label} 합계")
            + kpi("전자 군급 국외 조달계획", p_val, p_unit, p_sub or "건수만 · 계획 ≠ 계약")
            + kpi("국산화개발 전자 부품", b_val, b_unit, b_sub or "국산화율 아님")
            + "</div>")
    chart_source(f"{SOURCE_LINE.removeprefix('출처: ')} · 관세청 자료 기간 "
                 f"{s_customs['period'] if s_customs['has_period'] else '—'} · "
                 "관세청 달러 금액과 방위사업청 건수·부품 수는 합산하거나 비율을 내지 않습니다(직접 비교 불가)")
    if "failed" in (st_rule, st_plan, st_b2):
        if st.button("다시 조회", key="kpi_retry"):   # try_query 실패는 캐시되지 않으므로 rerun 이 곧 재시도(전역 캐시는 비우지 않는다)
            st.rerun()

# ── 부품별 공급망 현황 — 품목군 표(스파크라인) · 핵심 지표 ─────────────────────────
piv = (mon.assign(v=mon["imp_dlr"] / E6).pivot_table(index="hs6", columns="yyyymm", values="v", aggfunc="sum")
       .reindex(columns=sorted(mon["yyyymm"].unique())).fillna(0))
colors = country_colors(top1["stat_cd"].tolist())   # 1위 공급국 국가 색 — 표 · 지도 · 점유율 막대에서 같은 나라 = 같은 색
rows = []
for r in top1.sort_values("hhi", ascending=False).itertuples():
    m = piv.loc[r.hs6].tolist() if r.hs6 in piv.index else [0.0] * 24
    m = ([0.0] * 24 + m)[-24:]
    prev, rec = sum(m[:12]), sum(m[12:])
    rows.append({"name": names[r.hs6], "hs": r.hs6, "top": cname.get(r.stat_cd, r.stat_cd),
                 "color": colors.get(r.stat_cd, ETC), "m": m[12:] if any(m[12:]) else [0, 0],
                 "yoy": (rec / prev * 100 - 100) if prev else 0.0, "n": int(r.country_count), "hhi": int(round(r.hhi)),
                 "s1": r.share * 100})
n_ctry = int(sel.groupby("stat_cd")["imp_dlr"].sum().gt(0).sum())
avg_hhi = float(top1["hhi"].mean()) if not top1.empty else 0.0
n_hi = int((top1["hhi"] >= 2500).sum())

if rows:
    t_chain = (f'{len(rows)}개 품목군 중 <span class="key">{n_hi}개가 기간 합계 HHI 2,500 이상</span>이고, 가장 높은 것은 '
               f'{escape(rows[0]["name"])}(HHI {rows[0]["hhi"]:,} · 1위 {escape(str(rows[0]["top"]))} {rows[0]["s1"]:.1f}%)')
else:
    t_chain = f"{y_label} 수입 실적이 있는 품목군이 없다"
chain_head = (f'<div class="h"><span>{t_chain}</span><span class="sub">{y_label} 합계 · 추이 = 최근 12개월 월별 · '
              'HHI 2,500 이상 높음</span></div>')

with zone("chain", "부품별 공급망 현황"):
    c1, c2 = st.columns([2.6, 1], gap="medium")   # 공급망 표가 1280 폭에서도 잘리지 않게 표 쪽을 넓게
    c1.html(re.sub(r'<div class="h">.*?</div>', lambda _m: chain_head, supply_table(rows), count=1))
    chart_source(src_customs()
                 + f" · 집중도·1위 점유율·수입국 = {y_label} 합계(완결 연도) · 추이·변화율 = 최근 12개월("
                 f"{ym_txt(str(piv.columns[-12]))}~{ym_txt(d['last'])}) vs 그 전 12개월 월별 수입액 · HHI 순 · 국가는 선적국", where=c1)
    c2.html(core_kpis([
        ("", "", "비교 품목군", f"{len(top1)}", "개", f"분석 대상 {len(wl)}개 중 {y_label} 실적 있음", ""),
        ("", "", "고집중 품목군", f"{n_hi}", "개", "기간 합계 HHI 2,500 이상", ""),
        ("", "", "평균 집중도", f"{avg_hhi:,.0f}", "HHI", f"{len(top1)}개 품목군 단순 평균", ""),
        ("", "", "공급 국가", f"{n_ctry}", "개국", f"{y_label} 수입 실적 > 0 선적국", ""),
    ], f"{y_label} 합산"))
    tbl = pd.DataFrame([{"HS6": x["hs"], "품목군": x["name"], "1위 공급국": x["top"], "1위 점유율(%)": round(x["s1"], 1),
                         "기간 합계 HHI": x["hhi"], "수입국 수": x["n"], "최근 12개월 변화율(%)": round(x["yoy"], 1)} for x in rows])
    head = csv_header(f"분석 대상 {len(wl)}개 품목군 · 기간 {y_label} 합계(완결 연도) · 변화율 = 최근 12개월 vs 그 전 12개월",
                      SOURCE_LINE.removeprefix("출처: "), [("관세청 수출입", s_customs, None)])
    c1.download_button("표 CSV 내려받기", (head + tbl.to_csv(index=False)).encode("utf-8-sig"),
                       f"홈_공급망현황_{y_label.replace('~', '-')}.csv", "text/csv", icon=":material/download:", key="home_csv")

# ── 어디서 들어오나 — 지구본 · 품목군별 1위 공급국 점유율 ─────────────────────────
leaders = top1.groupby("stat_cd")["hs6"].apply(list)
pts = (sel[sel["stat_cd"].isin(leaders.index)].groupby("stat_cd", as_index=False)["imp_dlr"].sum()
       .merge(ctry, on="stat_cd", how="left").dropna(subset=["lat", "lon"]).sort_values("imp_dlr", ascending=False))
globe_pts = [{"name": cname.get(c, c), "lat": float(la), "lon": float(lo), "value": round(v / E6, 1), "color": colors.get(c, ETC),
              "note": "1위 품목군: " + ", ".join(names[h] for h in leaders[c])}
             for c, la, lo, v in zip(pts["stat_cd"], pts["lat"], pts["lon"], pts["imp_dlr"])]

with zone("where", "어디서 들어오나"):
    c_map, c_bar = st.columns([1.35, 1], gap="medium")
    with c_map.container(border=True, key="card_map"):
        if globe_pts:
            g0 = globe_pts[0]
            t_map = (f'1위 공급국 {len(globe_pts)}개국 중 분석 대상 수입액은 <span class="key">{escape(str(g0["name"]))} '
                     f'{g0["value"]:,.0f}백만 USD</span>가 가장 크다')
        else:
            t_map = f"{y_label} 1위 공급국 수입 실적이 없다"
        chart_title(t_map, f"백만 USD · {y_label} 합계 · 1위 공급국만 · 지구본 · 지도 전환 · 끌어서 돌리기 · 원에 올리면 상세")
        fig_map = supply_globe(globe_pts, height=430, unit="백만 USD")
        # 지도 읽는 법 — 네 줄이 좁은 칸에서 두 줄씩 어긋나게 꺾이지 않도록 2열 격자로
        st.html('<div style="display:grid;grid-template-columns:repeat(2,max-content);gap:3px 18px;font-size:13px;color:var(--muted);'
                'background:#fff;border:1px solid var(--line);border-radius:8px;padding:7px 12px">'
                '<span>원 크기 = 분석 대상 수입액 합</span>'
                '<span>화살표 = 대한민국으로 들어오는 방향</span><span>원 색 = 국가(표 · 막대와 같은 색)</span>'
                '<span>국가는 선적국(원산지 아님)</span></div>')
        src_map = src_customs() + " · 국가 좌표는 나라 대표 위치 · 국가는 선적국"
        chart_source(src_map)
        png_button(fig_map, f"홈_1위공급국_지도_{y_label.replace('~', '-')}", title=t_map, source=src_map)
    bars = top1.sort_values("share", ascending=False)
    body = "".join(
        f'<div class="row" title="{escape(names[r.hs6])} — 1위 {escape(cname.get(r.stat_cd, r.stat_cd))} {r.share * 100:.1f}%">'
        f'<div class="nm">{escape(names[r.hs6])}<em>{r.hs6}</em></div>'
        f'<div class="track"><div class="fill" style="width:{r.share * 100:.1f}%;background:{colors.get(r.stat_cd, ETC)}"></div>'
        f'<div class="ref"></div></div><div class="pct">{r.share * 100:.1f}%</div></div>'
        for r in bars.itertuples())
    legend = "".join(f'<span><i style="background:{col}"></i>{escape(cname.get(c, c))}</span>' for c, col in colors.items())
    t_bar = (f'{len(top1)}개 품목군 중 <span class="key">{k50}개는 1위 공급국 점유율이 50% 이상</span>이다'
             if len(top1) else f"{y_label} 수입 실적이 있는 품목군이 없다")
    c_bar.html(f'<div class="card"><div class="h"><span>{t_bar}</span>'
               f'<span class="sub">% · {y_label} 합계 · 점선 = 50%</span></div>'
               f'<div class="bars">{body}</div><div class="legend" style="margin-top:10px">{legend}</div>'
               + source_pop(f'{src_customs()} · 수입 실적 &gt; 0 국가만 · '
                            '1위 동률은 국가 코드 내림차순 · 국가는 선적국') + '</div>')

with st.expander("산식 · 출처 · 표현 범위"):
    st.markdown(f"**수입액** = 관세청 수입금액(USD) 합 — 분석 대상 {len(wl)}개 품목군, 선택 기간의 완결 연도 합계. 백만 USD = USD ÷ 10⁶.  \n"
                "**1위 공급국 점유율** = 품목군별 1위 국가 수입액 ÷ 품목군 수입액 합 × 100(수입 실적 > 0 국가만).  \n"
                "**기간 합계 HHI** = Σ(국가 점유율 × 100)², 0~10,000. 선택 기간을 합산한 점유율로 계산(①의 연도별 HHI와 다른 지표). "
                "2,500 이상 「높음」(미 법무부 · 연방거래위원회 2010 합병 지침의 고집중 기준) · 그 밖 「보통」은 집중 수준 구간일 뿐 위험 예측이 아닙니다.  \n"
                "**추이 · 변화율** = 관세청 월별 수입액, 최근 12개월 합 ÷ 그 전 12개월 합 − 1.  \n"
                "**전자 군급 국외 조달계획** = 방위사업청 국외 조달계획 중 전자 군급(FSG 58 · 59 · 60) 품목 수(건수만).  \n"
                "**국산화개발 전자 부품** = 국산화개발품목 중 전자 군급 부품의 부품관리번호 고유 수(국산화율 아님).  \n\n"
                "**표현 범위** — 수입액은 국가 전체(민수 포함) 교역액이며 군수 수요 규모를 뜻하지 않습니다. "
                "관세청 달러 금액과 방위사업청 건수·부품 수는 합산하거나 비율을 내지 않습니다. HS 품목군을 FSC·NSN과 연결하지 않습니다.  \n\n"
                f"**출처** — {SOURCE_LINE.removeprefix('출처: ')}.")
