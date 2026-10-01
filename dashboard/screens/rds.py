"""소분류 화면의 조회 — 운영 DB(AWS RDS)에서 읽어 화면이 쓰는 모양으로 바꾼다.

화면 파일(screens/*.py)은 이 모듈만 부른다. 조회는 dashboard/db.py 의 query(바인딩 파라미터 · 캐시 1시간)이다.
- 관세청: v_import_hs6_year · v_hhi_hs6_year · v_hhi_export_hs6_year · v_import_share_hs6_year · v_export_share_hs6_year ·
  fact_customs_monthly(최근 12개월) · ref_hs_whitelist(분석 대상 13 = priority 1 · 2) · ref_hs_rule_flag(선정 깔때기) · ref_country
- 방위사업청: clean_dapa_overseas_plan_api(전자 군급 = is_elec, 건수만 — 금액은 통화 미검증) · clean_dapa_localized_item ·
  ref_fsg · ref_fsc · clean_dapa_contract · v_contract_private_reason · clean_dapa_bid_result · clean_dapa_bid_notice · v_overseas_plan_yearly
- 그 밖: v_budget_rnd_yearly · clean_kosis_utilization · clean_kosis_production_index · v_defense_company_sector ·
  ref_semi_policy_timeline · ref_semi_stat · meta_dataset
HS 품목군과 군급(FSG · FSC)은 어떤 수준에서도 잇지 않는다. 단위: 관세청 억 달러(USD ÷ 1e8), 예산 억 원(원 ÷ 1e8).
화면에는 DB 표 · 뷰 · 열 이름을 쓰지 않는다 — 출처는 기관 · 데이터명 · 자료 기간만.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import live
from db import data_stamp, query
from kdesign import ETC, SERIES
from metrics import concentration
from ui import SHORT, country_colors

E8 = 1e8
TTL = 3600
TARGET = "SELECT hs6 FROM ref_hs_whitelist WHERE priority IN (1, 2)"   # 분석 대상 13개
FAMILY_ORDER = ["반도체", "레이더", "통신·레이더 부분품", "항법", "항공전자", "소재장비"]
RULE_BADGE = (("r1", "군용 전용 세분류"), ("r2", "전문 용도 명시"))
FSGS = ["58", "59", "60"]                    # 전자 관련 군 — clean.is_elec = fsg2 IN (58, 59, 60)
FSG_COLOR = {"58": SERIES[0], "59": SERIES[1], "60": SERIES[2]}
ARMY_COLOR = {"육군": SERIES[0], "해군": SERIES[1], "공군": SERIES[2], "해병대": SERIES[3], "국직": SERIES[4], "미확인": ETC}
PROD_NAME = {"C261": "반도체", "C262": "전자 부품", "C264": "통신 · 방송장비"}   # 광공업생산지수 산업(KSIC) — 짧은 이름
# 출처 표에 싣는 자료 — 키 → 쓰인 곳(메뉴). 1만 건 요건 2종은 관세청 · 국산화개발품목
SOURCE_USE = {
    "customs_all": "① 부품 현황 · 1만 건 요건", "customs_hs_code_master": "① 품목 선정",
    "dapa_overseas_plan_api": "② 군급 분류와 조달 · ③", "dapa_fsc_catalog": "② · ③ 군급 이름",
    "dapa_localized_item": "③ 국산화 현황 · 1만 건 요건", "dapa_overseas_plan": "④ 정책 · 예산 배경",
    "openfiscal_program_budget": "④ 정책 · 예산 배경", "semi_strategy": "④ 정책 흐름 · 인용 수치",
    "kosis_utilization": "④ 국내 생산 기반", "kosis_production_index": "④ 국내 생산 기반",
    "dapa_defense_company": "④ 국내 생산 기반", "dapa_contract": "④ 국내 조달(부록)",
    "dapa_bid_notice": "④ 국내 조달(부록)", "dapa_bid_result": "④ 국내 조달(부록)",
}
# 대분류별 「자료 기준」 줄 — (이름, 데이터셋 키, 표)
STAMPS = {
    "parts": [("관세청 수출입", "customs_all", "fact_customs_monthly")],
    "fsc": [("국외 조달계획", "dapa_overseas_plan_api", "clean_dapa_overseas_plan_api"),
            ("군급분류집", "dapa_fsc_catalog", "ref_fsc")],
    "loc": [("국산화개발품목", "dapa_localized_item", "clean_dapa_localized_item"),
            ("국외 조달계획", "dapa_overseas_plan_api", "clean_dapa_overseas_plan_api")],
    "bg": [("국외조달 계획", "dapa_overseas_plan", "clean_dapa_overseas_plan"),
           ("열린재정 예산", "openfiscal_program_budget", "clean_openfiscal_program_budget"),
           ("KOSIS 가동률", "kosis_utilization", "clean_kosis_utilization"),
           ("KOSIS 생산지수", "kosis_production_index", "clean_kosis_production_index"),
           ("국내 계약", "dapa_contract", "clean_dapa_contract")],
}


def stamps(cat: str) -> list[tuple[str, dict]]:
    return [(n, data_stamp(k, t)) for n, k, t in STAMPS.get(cat, [])]


def no_dep(s: str) -> str:
    """화면 표현 경계 — 인용 원문의 「의존율 · 의존도 · 의존」을 「도입 비중 · 도입」으로(DB 값은 그대로)."""
    return str(s).replace("의존율", "도입 비중").replace("의존도", "도입 비중").replace("의존", "도입")


# ── 관세청 ────────────────────────────────────────────────────────────────────
def customs_period() -> str:
    """관세청 자료 기간(적재된 월 범위, 예 2016.01~2026.08)."""
    s = data_stamp("customs_all", "fact_customs_monthly")
    return s["period"] if s["has_period"] else "—"


@st.cache_data(ttl=TTL, show_spinner=False)
def items() -> pd.DataFrame:
    """분석 대상 13개 — hs6 · short(화면 짧은 이름) · name_ko(관세청 품명) · family(묶음) · category · r1 · r2(선정 규칙)."""
    df = query("""
        SELECT w.hs6, w.name_ko, w.category, w.system_family AS family,
               COALESCE(f.r1_mil, 0) AS r1, COALESCE(f.r2_aero_nav, 0) AS r2
        FROM ref_hs_whitelist w LEFT JOIN ref_hs_rule_flag f ON f.hs6 = w.hs6
        WHERE w.priority IN (1, 2) ORDER BY w.hs6
    """)
    df["short"] = df["hs6"].map(SHORT).fillna(df["name_ko"])
    return df


def rules(r) -> list[str]:
    """선정 근거 배지 이름(규칙 충족한 것만)."""
    return [name for col, name in RULE_BADGE if int(r[col] or 0)]


@st.cache_data(ttl=TTL, show_spinner=False)
def trade() -> pd.DataFrame:
    """분석 대상 13개 HS6 × 연도 × 국가 수입 · 수출(USD) + 국가 이름 · 좌표. 국가 = 선적국 · 도착국(원산지 아님)."""
    df = query(f"""
        SELECT v.hs6, v.year, v.stat_cd, c.name_ko AS country, c.lat, c.lon, v.imp_dlr, v.exp_dlr, v.is_partial_year
        FROM v_import_hs6_year v LEFT JOIN ref_country c ON c.stat_cd = v.stat_cd
        WHERE v.hs6 IN ({TARGET})
    """)
    df["country"] = df["country"].fillna(df["stat_cd"])
    df["year"] = df["year"].astype(int)
    return df


def full_years() -> list[int]:
    """완결 연도(부분연도 제외) — 연도별 차트 · 기간 합계의 기준."""
    t = trade()
    part = set(t.loc[t["is_partial_year"] == 1, "year"])
    return sorted(int(y) for y in t["year"].unique() if y not in part)


def base_year() -> int:
    return full_years()[-1]


def country_names() -> dict[str, str]:
    t = trade()
    return dict(zip(t["stat_cd"], t["country"]))


def colors(codes: list[str]) -> dict[str, str]:
    """국가 색 — ui.country_colors 규칙(주요 7개국 고정, 그 밖은 1색 뒤 기타)."""
    return country_colors(list(codes))


def conc(years: tuple[int, ...], flow: str = "imp") -> pd.DataFrame:
    """분석 대상 13개의 집중도(고른 연도를 합산한 뒤 점유율) — items 열 + total · top1_stat_cd · top1_share(0~1) · top3_share · hhi · country_count.
    한 해만 넣으면 DB 뷰(v_hhi_hs6_year)와 같은 값이다(metrics.concentration 머리 주석)."""
    t = trade()
    c = concentration(t[t["year"].isin(years)], "imp_dlr" if flow == "imp" else "exp_dlr")
    return items().merge(c, on="hs6", how="left")


@st.cache_data(ttl=TTL, show_spinner=False)
def monthly12() -> tuple[pd.DataFrame, str, str]:
    """최근 12개월 품목군별 월 수입액(USD) — (hs6 × 월 표, 시작 월, 끝 월). 빈 달은 0으로 채운다."""
    last = str(query("SELECT MAX(yyyymm) AS ym FROM fact_customs_monthly")["ym"].iloc[0])
    start = live.ym_add(last, -11)
    df = query(f"""SELECT hs6, yyyymm, SUM(imp_dlr) AS imp FROM fact_customs_monthly
                   WHERE hs6 IN ({TARGET}) AND yyyymm >= :s GROUP BY hs6, yyyymm""", {"s": start})
    months = [live.ym_add(start, i) for i in range(12)]
    wide = df.pivot_table(index="hs6", columns="yyyymm", values="imp", aggfunc="sum").reindex(columns=months).fillna(0)
    return wide, start, last


def yearly(hs: list[str]) -> pd.DataFrame:
    """고른 품목군 합계의 연도별 수입 · 수출(억 달러, 완결 연도만) — index = 연도, 열 imp · exp."""
    t, ys = trade(), full_years()
    d = t[t["hs6"].isin(hs) & t["year"].isin(ys)].groupby("year")[["imp_dlr", "exp_dlr"]].sum() / E8
    return d.reindex(ys, fill_value=0).rename(columns={"imp_dlr": "imp", "exp_dlr": "exp"})


def shares(hs: list[str], year: int, flow: str) -> pd.DataFrame:
    """고른 품목군 합계의 국가 구성 — stat_cd · country · value(억 달러) · share(%) · lat · lon, 큰 순, 실적 > 0 만."""
    t = trade()
    col = "imp_dlr" if flow == "imp" else "exp_dlr"
    d = (t[t["hs6"].isin(hs) & (t["year"] == year)].groupby(["stat_cd", "country"], as_index=False)
         .agg(value=(col, "sum"), lat=("lat", "first"), lon=("lon", "first")))
    d = d[d["value"] > 0].sort_values(["value", "stat_cd"], ascending=[False, False])
    d["share"] = d["value"] / d["value"].sum() * 100 if not d.empty else 0.0
    d["value"] = d["value"] / E8
    return d.reset_index(drop=True)


@st.cache_data(ttl=TTL, show_spinner=False)
def hhi_years(hs: str, flow: str) -> pd.DataFrame:
    """품목군 하나의 연도별 HHI · 1위국(완결 연도) — year · hhi · top1_stat_cd · top1_share(0~1)."""
    if flow == "imp":
        sql = ("SELECT year, hhi, top1_stat_cd, top1_share FROM v_hhi_hs6_year "
               "WHERE hs6 = :h AND is_partial_year = 0 ORDER BY year")
    else:
        sql = ("SELECT year, hhi_export AS hhi, top1_stat_cd, top1_share FROM v_hhi_export_hs6_year "
               "WHERE hs6 = :h AND is_partial_year = 0 ORDER BY year")
    df = query(sql, {"h": hs})
    df["year"] = df["year"].astype(int)
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def ranks(hs: str, flow: str, codes: tuple[str, ...]) -> pd.DataFrame:
    """고른 국가들의 연도별 순위(1 = 가장 큼, 완결 연도) — year · stat_cd · rnk · share."""
    view = "v_import_share_hs6_year" if flow == "imp" else "v_export_share_hs6_year"   # 고정 두 이름 중 하나(입력값 아님)
    df = query(f"SELECT year, stat_cd, rnk, share FROM {view} "
               "WHERE hs6 = :h AND is_partial_year = 0 AND stat_cd IN :c ORDER BY year", {"h": hs, "c": list(codes)})
    df["year"] = df["year"].astype(int)
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def hs_funnel() -> list[tuple[str, str, int]]:
    """품목 선정 깔때기 — (이름, 설명, 개수). 관세청 HS6(84 · 85 · 88 · 90류) → 규칙 충족 → 분석 대상."""
    r = query("SELECT COUNT(*) AS n, SUM(r1_mil = 1 OR r2_aero_nav = 1) AS hit FROM ref_hs_rule_flag").iloc[0]
    n, hit, target = int(r["n"]), int(r["hit"] or 0), len(items())
    return [("관세청 HS6", "84 · 85 · 88 · 90류", n),
            ("규칙 충족", "군용 전용 세분류 또는 전문 용도(항공기용 · 항행 · 레이더 · 무인기) 명시", hit),
            ("분석 대상", f"「항공기용」 세분류로 걸린 기계 · 전장 계열 {hit - target}개 제외", target)]


# ── 방위사업청 — 군(FSG) · 군급(FSC) · 국외 조달계획 · 국산화 ─────────────────────────────
@st.cache_data(ttl=TTL, show_spinner=False)
def fsg_names() -> dict[str, str]:
    df = query("SELECT fsg_code, name_ko FROM ref_fsg WHERE fsg_code IN :g", {"g": FSGS})
    return {g: dict(zip(df["fsg_code"], df["name_ko"])).get(g, "") for g in FSGS}


@st.cache_data(ttl=TTL, show_spinner=False)
def fsc_ref() -> pd.DataFrame:
    """전자 관련 군(58 · 59 · 60) 아래 군급 — fsc4 · fsg · name · closed(폐지 = status C)."""
    df = query("SELECT fsc4, fsc2 AS fsg, name_ko AS name, status FROM ref_fsc WHERE fsc2 IN :g ORDER BY fsc4", {"g": FSGS})
    df["closed"] = df["status"].eq("C")
    return df


def fsc_names() -> dict[str, str]:
    f = fsc_ref()
    return dict(zip(f["fsc4"], f["name"]))


@st.cache_data(ttl=TTL, show_spinner=False)
def plan() -> pd.DataFrame:
    """전자 군급 국외 조달계획 품목 행(조달요구번호 × 품목순번) — fsc4 · fsg · army · year · equipment(결측이면 None). 금액은 쓰지 않는다."""
    df = query("""
        SELECT fsc4, fsg2 AS fsg, army_std AS army, demand_year AS year,
               CASE WHEN is_equipment_missing = 0 THEN equipment_name END AS equipment
        FROM clean_dapa_overseas_plan_api WHERE is_elec = 1
    """)
    df["year"] = df["year"].astype("int64")
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def plan_funnel() -> list[tuple[str, int]]:
    """국외 조달계획 분류 깔때기(행)."""
    r = query("""SELECT COUNT(*) AS n_all, SUM(nsn IS NOT NULL) AS n_nsn,
                        SUM(nsn IS NOT NULL AND fsc4 <> '9999') AS n_pop, SUM(is_elec) AS n_elec
                 FROM clean_dapa_overseas_plan_api""").iloc[0]
    return [("국외 조달계획 품목", int(r["n_all"])), ("NSN 있음", int(r["n_nsn"] or 0)),
            ("군급 「9999」 제외(분석 모집단)", int(r["n_pop"] or 0)), ("전자 군급(군 58 · 59 · 60)", int(r["n_elec"] or 0))]


@st.cache_data(ttl=TTL, show_spinner=False)
def plan_years() -> list[int]:
    return [int(y) for y in query("SELECT DISTINCT demand_year AS y FROM clean_dapa_overseas_plan_api "
                                  "WHERE demand_year IS NOT NULL ORDER BY y")["y"]]


@st.cache_data(ttl=TTL, show_spinner=False)
def army_share(y0: int, y1: int) -> pd.DataFrame:
    """소요군별 전자 군급 비중 — army · n_valid · n_elec · pct.
    분모 = 군급 판별 가능 행(군급 있음 · 「9999」 기타 품목 제외, 전자 외 군급 포함)."""
    df = query("""
        SELECT army_std AS army,
               SUM(fsg2 IS NOT NULL AND fsc4 <> '9999') AS n_valid,
               SUM(fsg2 IN ('58', '59', '60') AND fsc4 <> '9999') AS n_elec
        FROM clean_dapa_overseas_plan_api
        WHERE demand_year BETWEEN :y0 AND :y1
        GROUP BY army_std
    """, {"y0": y0, "y1": y1})
    df = df[df["n_valid"] > 0].copy()
    df["pct"] = df["n_elec"] / df["n_valid"] * 100
    return df.sort_values("pct", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=TTL, show_spinner=False)
def loc() -> pd.DataFrame:
    """전자 군급 국산화 완료 부품 — fsc4 · fsg · parts(부품관리번호 고유 수) · projects."""
    return query("""
        SELECT fsc4, fsc2 AS fsg, COUNT(DISTINCT part_mgmt_no) AS parts, COUNT(DISTINCT project_name) AS projects
        FROM clean_dapa_localized_item WHERE is_electronic_group = 1 GROUP BY fsc4, fsc2
    """)


@st.cache_data(ttl=TTL, show_spinner=False)
def loc_scope() -> dict[str, int]:
    """국산화개발품목 전체 · 전자 군급의 고유 부품 수 · 사업 수(군급 합이 아니라 전체 고유 — 한 부품이 두 군급에 걸쳐도 한 번)."""
    r = query("""SELECT COUNT(DISTINCT part_mgmt_no) AS parts_all, COUNT(DISTINCT project_name) AS proj_all,
                        COUNT(DISTINCT CASE WHEN is_electronic_group = 1 THEN part_mgmt_no END) AS parts,
                        COUNT(DISTINCT CASE WHEN is_electronic_group = 1 THEN project_name END) AS proj
                 FROM clean_dapa_localized_item""").iloc[0]
    return {k: int(r[k] or 0) for k in r.index}


# ── 배경 ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=TTL, show_spinner=False)
def policy() -> pd.DataFrame:
    """국방반도체 정책 연표 전체 — row_no · date · category · event · source_title(발전전략 참조표)."""
    df = query("SELECT row_no, event_date AS date, category, event, source_title FROM ref_semi_policy_timeline ORDER BY row_no")
    for c in ("event", "source_title"):
        df[c] = df[c].fillna("").map(no_dep)
    df["date"] = df["date"].astype(str)
    return df


def policy_key() -> pd.DataFrame:
    """대표 5점 — 조사 · 전략 · 과제 · 법 · 예산 분류마다 첫 행."""
    p = policy()
    return (p[p["category"].isin(["조사", "전략", "과제", "법", "예산"])].drop_duplicates("category")
            .sort_values("row_no").reset_index(drop=True))


@st.cache_data(ttl=TTL, show_spinner=False)
def quotes() -> list[tuple[str, str, str, str]]:
    """발전전략 본문 인용 수치 — (이름, 값, 단위, 출처). 팀 계산값이 아니다."""
    df = query("SELECT stat_key, label, value_num, unit_txt, source FROM ref_semi_stat ORDER BY stat_key = 'overseas_share' DESC")
    return [(no_dep(r.label), f"{float(r.value_num):g}", r.unit_txt or "", r.source or "") for r in df.itertuples()]


@st.cache_data(ttl=TTL, show_spinner=False)
def overseas_budget() -> pd.DataFrame:
    """국외조달 계획 예산(원화 계획액) — plan_year · exec_type · eok(억 원) · n(계획 건수)."""
    df = query("SELECT plan_year, exec_type, plan_count AS n, budget_krw FROM v_overseas_plan_yearly ORDER BY plan_year")
    df["plan_year"] = df["plan_year"].astype(int)
    df["eok"] = df["budget_krw"].astype(float) / E8
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def rnd_budget() -> pd.DataFrame:
    """국방 R&D 세부사업 예산(억 원, 정부 예산) — year · basis(확정 · 정부안) · 부품국산화 · 국방반도체 · 국방기술개발 · 전체."""
    df = query("""SELECT fiscal_year AS year, amount_basis AS basis, localization_gov_100m AS loc,
                         semiconductor_gov_100m AS semi, tech_dev_gov_100m AS tech, total_gov_100m AS total
                  FROM v_budget_rnd_yearly ORDER BY fiscal_year""")
    df["year"] = df["year"].astype(int)
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def utilization() -> pd.DataFrame:
    """방산업체 분야별 평균가동률(%) — sector · year · pct · is_avg."""
    df = query("SELECT sector_name AS sector, year, is_avg_row AS is_avg, value_text FROM clean_kosis_utilization")
    df["pct"] = pd.to_numeric(df["value_text"], errors="coerce")
    df["year"] = df["year"].astype(int)
    return df.dropna(subset=["pct"]).sort_values(["sector", "year"])


@st.cache_data(ttl=TTL, show_spinner=False)
def prod_index() -> pd.DataFrame:
    """전자 · 반도체 광공업생산지수(원지수, 2020 = 100) 연평균 — code · name · year · v. 12개월이 다 있는 해만."""
    df = query("""SELECT industry_code AS code, YEAR(stat_month) AS year, AVG(index_value) AS v, COUNT(*) AS m
                  FROM clean_kosis_production_index
                  WHERE region_name LIKE :r AND item_code = :i AND industry_code IN :c
                  GROUP BY industry_code, YEAR(stat_month) ORDER BY code, year""",
               {"r": "00%", "i": "T10", "c": list(PROD_NAME)})
    df = df[df["m"] == 12].copy()
    df["year"] = df["year"].astype(int)
    df["name"] = df["code"].map(PROD_NAME)
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def companies() -> pd.DataFrame:
    """분야별 방산업체 지정 수 — sector · n(큰 순)."""
    return query("SELECT sector, company_count AS n FROM v_defense_company_sector ORDER BY company_count DESC, sector")


@st.cache_data(ttl=TTL, show_spinner=False)
def domestic() -> dict:
    """국내 조달(부록) — 계약 방법 · 수의계약 사유 · 입찰 결과 · 공고 수(건수만)."""
    method = query("SELECT contract_method_name AS m, COUNT(*) AS n FROM clean_dapa_contract "
                   "WHERE is_latest_seq = 1 GROUP BY contract_method_name ORDER BY n DESC")
    reason = query("SELECT reason_group AS g, SUM(contract_count) AS n FROM v_contract_private_reason "
                   "GROUP BY reason_group ORDER BY n DESC")
    bid = query("SELECT opening_result AS r, SUM(is_key_representative) AS keys_n FROM clean_dapa_bid_result GROUP BY opening_result")
    notice = int(query("SELECT COUNT(*) AS n FROM clean_dapa_bid_notice").iloc[0]["n"])
    return dict(method=method, reason=reason, bid=bid, notice=notice)


@st.cache_data(ttl=TTL, show_spinner=False)
def sources() -> pd.DataFrame:
    """출처 표 — 이 화면들이 쓰는 자료만(SOURCE_USE), 기관 · 데이터명 · 데이터 ID · 원본 건수 · 자료 기간 · 쓰인 곳."""
    df = query("""SELECT dataset_key, tier, provider, dataset_id, title, period_start, period_end, is_partial_period, raw_row_count
                  FROM meta_dataset WHERE dataset_key IN :k""", {"k": list(SOURCE_USE)})
    order = {k: i for i, k in enumerate(SOURCE_USE)}
    df = df.sort_values("dataset_key", key=lambda s: s.map(order)).reset_index(drop=True)
    df["use"] = df["dataset_key"].map(SOURCE_USE)
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def bid_match() -> dict[str, int]:
    """입찰 공고 ↔ 결과 연결(행) — 공고번호 + 차수 대조."""
    r = query("""SELECT (SELECT COUNT(*) FROM clean_dapa_bid_notice) AS n_notice,
                        (SELECT COUNT(*) FROM clean_dapa_bid_result) AS n_result,
                        (SELECT COUNT(*) FROM clean_dapa_bid_result WHERE notice_link_status <> '미연결') AS n_linked,
                        (SELECT COUNT(*) FROM clean_dapa_bid_result WHERE notice_link_status = '1:1') AS n_one""").iloc[0]
    return {k: int(r[k] or 0) for k in r.index}


@st.cache_data(ttl=TTL, show_spinner=False)
def procedure() -> dict:
    """국외조달 절차 단계별 자료 건수 · 기간. 단계마다 자료 · 기간이 달라 전환율로 읽지 않는다."""
    r = query("""SELECT (SELECT COUNT(*) FROM clean_dapa_overseas_plan) AS plan_n,
                        (SELECT MIN(plan_year) FROM v_overseas_plan_yearly) AS plan_y0,
                        (SELECT MAX(plan_year) FROM v_overseas_plan_yearly) AS plan_y1,
                        (SELECT COUNT(*) FROM clean_dapa_overseas_bid_result) AS bid_n,
                        (SELECT MIN(opening_ym) FROM clean_dapa_overseas_bid_result) AS bid_y0,
                        (SELECT MAX(opening_ym) FROM clean_dapa_overseas_bid_result) AS bid_y1,
                        (SELECT COUNT(*) FROM clean_dapa_overseas_contract) AS ctr_n,
                        (SELECT MIN(contract_year) FROM clean_dapa_overseas_contract) AS ctr_y0,
                        (SELECT MAX(contract_year) FROM clean_dapa_overseas_contract) AS ctr_y1""").iloc[0]
    return {k: r[k] for k in r.index}


@st.cache_data(ttl=TTL, show_spinner=False)
def strategy_tasks() -> pd.DataFrame:
    """국방반도체 발전전략 4방향 12과제(참조표) — direction_no · direction_name · task_no · task_name."""
    df = query("SELECT direction_no, direction_name, task_no, task_name FROM ref_semi_strategy_task ORDER BY task_no")
    for c in ("direction_name", "task_name"):
        df[c] = df[c].fillna("").map(no_dep)
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def chip_types() -> pd.DataFrame:
    """정부가 밝힌 국방반도체 수요 7대 유형(참조표) — type_no · name_ko · summary."""
    df = query("SELECT type_no, name_ko, summary FROM ref_semi_chip_type ORDER BY type_no")
    for c in ("name_ko", "summary"):
        df[c] = df[c].fillna("").map(no_dep)
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def whitelist_n() -> int:
    """수집한 HS6 수(기준표 전체 — 분석 대상 13 + 배경)."""
    return int(query("SELECT COUNT(*) AS n FROM ref_hs_whitelist").iloc[0]["n"])
