"""「데이터 시각화」 상세 조회 도구 — 조건을 골라 차트 · 지도 · 표로 보는 선택형 시각화(값은 RDS).

「상세 조회」 3곳(screens/parts.py 의 detail)이 runpy.run_path 로 매 실행 새로 돌린다(페이지 파일처럼 —
import 하면 모듈이 프로세스에 한 번만 실행돼 화면이 그려지지 않는다). init_globals={"FIXED_TYPE": 유형}으로 유형을 하나로 고정한다(query_panel).

맨 위 「데이터 유형」 — 수출입 HS · 군수품 FSG/FSC · 국산화개발. 유형마다 조건 · 지표 · 차트 · 결과 탭이 바뀐다
(session_state 키 앞머리 qs_ · qf_ · ql_).
- 수출입 HS: 분석영역 · HS6/HS10 · 품목코드 · 국가 · 기간 · 지표 · 차트 15종 · 빠른 설정 → 지표 카드 · 차트 / 국가별 분포 지도 / 결과 표.
  읽는 표: fact_customs_monthly(월별 HS10 × 국가) · ref_hs_whitelist(분석 대상 13개) · ref_country · ref_hs_code_master(HS10 품명).
- 군수품 FSG/FSC: 국외 조달계획 OpenAPI 품목(clean_dapa_overseas_plan_api, 전자 계열 FSG 58·59·60) — 건수만 센다(금액은 통화 미검증).
- 국산화개발: 국산화개발품목(clean_dapa_localized_item, 전자 계열) — 스냅샷이라 건수 · 개수만(국산화율 · 추세 없음).
  「관련 업체」는 원자료의 계약업체(개발 주체 아님).
관세청 HS 와 FSC 는 어떤 수준에서도 엮지 않는다 — 유형끼리 값을 합치거나 잇지 않는다.
차트 유형 설명 칸은 KOSIS 「데이터 시각화 체험하기」 차트 목록을 따른다.
자유 입력은 품목명 · 기능명 · NSN · 부품관리번호 부분검색뿐이고 DB 에서 이미 읽은 표 안에서 거른다(SQL 에 넣지 않는다).
SQL 은 바인딩 파라미터만 쓴다.
단위: 금액 백만 USD(USD ÷ 10⁶), 중량 톤(kg ÷ 10³, 참고값). 무역수지 = 수출액 − 수입액. 국가는 선적국(원산지 아님).
"""
from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from db import data_stamp, query, safe_query
from kdesign import _FONT_LINK, ACCENT, ETC, SERIES, TEXT, _svg_img
from ui import (EXP, EXP_DIM, IMP, IMP_DIM, SHORT, source_pop, chart_source, chart_title, country_colors, country_map, csv_header, globe_loading, hover_donut, kpi, png_button,
                style_fig)

ALL = "__all__"
STATIC_DIR = Path(__file__).resolve().parent / "static"     # 결과 카드의 HTML · JS 조각(넓은 차트 · 지도 PNG)
# 분포 차트(막대) — 막대가 WIDE_MIN 개를 넘으면 실제 폭을 막대 수에 비례해 넓히고 가로 스크롤(wide_chart).
# 폭 = 막대 수 / WIDE_MIN × WIDE_BASE px(10개 = 결과 카드 폭 정도). WIDE_MIN 이하는 카드 폭에 맞춘다
WIDE_MIN, WIDE_BASE = 10, 700
# 화면 · CSV 출처는 「기관 · 데이터명(포털 ID) · 자료 기간」만 — DB 표 · 뷰 이름과 적재일은 쓰지 않는다(보안)
SOURCE = "관세청 품목별 국가별 수출입실적(15100475) · 국가 전체 교역(민수 포함) · 국가는 선적국"
PLOT_CFG = {"displaylogo": False, "modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "autoScale2d"]}
TARGET = "SELECT hs6 FROM ref_hs_whitelist WHERE priority IN (1, 2)"   # 분석 대상 13개


@st.cache_data(ttl=3600, show_spinner=False)
def load_ref() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wl = query("SELECT hs6, name_ko FROM ref_hs_whitelist WHERE priority IN (1, 2) ORDER BY priority, hs6")
    ctry = query(f"""SELECT c.stat_cd, c.name_ko, c.lat, c.lon, SUM(f.imp_dlr) + SUM(f.exp_dlr) AS tot
                     FROM fact_customs_monthly f JOIN ref_country c USING (stat_cd)
                     WHERE f.hs6 IN ({TARGET})
                     GROUP BY c.stat_cd, c.name_ko, c.lat, c.lon HAVING tot > 0 ORDER BY tot DESC""")
    yrs = query("SELECT year, MAX(is_partial_year) AS p, MIN(month) AS m0, MAX(month) AS m1 "
                "FROM fact_customs_monthly GROUP BY year ORDER BY year")
    return wl, ctry, yrs


@st.cache_data(ttl=3600, show_spinner=False)
def load_hs10_all() -> pd.DataFrame:
    """분석 대상 13개 아래에서 실적이 있는 HS10 전부(hs6 · hs10 · 품명). 품명이 없는 코드는 코드만 쓴다."""
    df = query(f"SELECT DISTINCT hs6, hs10 FROM fact_customs_monthly WHERE hs6 IN ({TARGET}) ORDER BY hs10")
    names = safe_query("SELECT hs10, name_ko FROM ref_hs_code_master")
    if names is None:
        return df.assign(name_ko=None)
    return df.merge(names.drop_duplicates("hs10"), on="hs10", how="left")


@st.cache_data(ttl=3600, show_spinner=False)
def load_trade(unit: str, items: tuple[str, ...] | None, y0: int, y1: int) -> pd.DataFrame:
    """연도 × 국가 수출입 금액·중량 합(USD · kg). items = 고른 품목코드(unit 단위), None = 분석 대상 13개 전체."""
    params: dict = {"y0": y0, "y1": y1}
    if items is None:
        cond = f"hs6 IN ({TARGET})"
    else:
        cond = f"{'hs10' if unit == 'HS10' else 'hs6'} IN :items"
        params["items"] = list(items)
    return query(f"""SELECT year, stat_cd, SUM(exp_dlr) AS exp_dlr, SUM(imp_dlr) AS imp_dlr,
                            SUM(COALESCE(exp_wgt, 0)) AS exp_wgt, SUM(COALESCE(imp_wgt, 0)) AS imp_wgt
                     FROM fact_customs_monthly WHERE {cond} AND year BETWEEN :y0 AND :y1
                     GROUP BY year, stat_cd""", params)


@st.cache_data(ttl=3600, show_spinner=False)
def load_fsg_ref() -> tuple[dict[str, str], dict[str, str]]:
    """전자 계열 FSG(58·59·60) · 그 아래 FSC 이름(군급분류집 표기)."""
    g = query("SELECT fsg_code, name_ko FROM ref_fsg WHERE is_electronic_group = 1 ORDER BY fsg_code")
    c = query("SELECT fsc4, name_ko FROM ref_fsc WHERE is_electronic_group = 1 ORDER BY fsc4")
    return dict(zip(g["fsg_code"], g["name_ko"])), {k: (v or "").strip() for k, v in zip(c["fsc4"], c["name_ko"])}


@st.cache_data(ttl=3600, show_spinner=False)
def load_fsg_items() -> pd.DataFrame:
    """군수품 — 국외 조달계획 OpenAPI 품목 중 전자 계열(is_elec = 1) 전부(약 2.3천 행). 금액 열은 읽지 않는다(통화 미검증).
    적용장비는 공란 · * 이 아닌 원문(②화면과 같은 기준)."""
    d = query("""SELECT nsn, item_name, fsg2, fsc4, function_name, item_kind_name, army_std, demand_year,
                        CASE WHEN is_equipment_missing = 0 THEN equipment_name END AS equipment,
                        kdsis_link_status = '연결' AS kdsis
                 FROM clean_dapa_overseas_plan_api WHERE is_elec = 1""")
    return pd.DataFrame({"NSN": d["nsn"].fillna(""), "품목명": d["item_name"].fillna(""), "FSG": d["fsg2"],
                         "FSC": d["fsc4"], "기능명": d["function_name"].fillna("미기재"),
                         "품목종류": d["item_kind_name"].fillna("미기재"), "군종": d["army_std"],
                         "요구연도": d["demand_year"].astype(int), "적용장비": d["equipment"],
                         "KDSIS 연결": d["kdsis"].astype(bool)})


@st.cache_data(ttl=3600, show_spinner=False)
def load_localized() -> pd.DataFrame:
    """국산화개발 — 국산화개발품목(사업 × 부품) 중 전자 계열 전부(약 2.7천 행). 스냅샷 — 연도 축 없음."""
    d = query("""SELECT project_name, part_mgmt_no, nsn, fsc2, fsc4, item_name, contractor_name
                 FROM clean_dapa_localized_item WHERE is_electronic_group = 1""")
    return pd.DataFrame({"부품관리번호": d["part_mgmt_no"], "NSN": d["nsn"].fillna(""), "품목명": d["item_name"].fillna(""),
                         "FSG": d["fsc2"], "FSC": d["fsc4"], "사업명": d["project_name"],
                         "관련 업체": d["contractor_name"].fillna("미기재")})


def trade_frame(names: list[str], y0: int, y1: int, unit: str, items: list[str] | None) -> pd.DataFrame:
    """국가 × 연도 표(수출액 · 수입액 · 무역수지 · 수출중량 · 수입중량) — 값은 RDS.
    고른 국가에서 실적이 없는 연도는 0 으로 채운다(실제 0). 전부 0 이면 빈 표."""
    raw = load_trade(unit, None if items is None else tuple(items), y0, y1)
    codes = [CODE[n] for n in names]
    raw = raw[raw["stat_cd"].isin(codes)]
    grid = pd.MultiIndex.from_product([codes, [y for y in Q_YEARS if y0 <= y <= y1]], names=["stat_cd", "year"])
    g = (raw.set_index(["stat_cd", "year"])[["exp_dlr", "imp_dlr", "exp_wgt", "imp_wgt"]]
         .reindex(grid, fill_value=0).reset_index())
    if g[["exp_dlr", "imp_dlr"]].to_numpy().sum() == 0:
        return pd.DataFrame()
    return pd.DataFrame({"국가": g["stat_cd"].map(NAME), "연도": g["year"].astype(int),
                         "수출액": (g["exp_dlr"] / 1e6).round(1), "수입액": (g["imp_dlr"] / 1e6).round(1),
                         "무역수지": ((g["exp_dlr"] - g["imp_dlr"]) / 1e6).round(1),
                         "수출중량": (g["exp_wgt"] / 1e3).round(1), "수입중량": (g["imp_wgt"] / 1e3).round(1)})


STAMP = data_stamp("customs_all", "fact_customs_monthly")
S_PLAN = data_stamp("dapa_overseas_plan_api", "clean_dapa_overseas_plan_api")
S_B2 = data_stamp("dapa_localized_item", "clean_dapa_localized_item")
# DB 접속 확인은 부르는 쪽이 먼저 한다

with globe_loading("기준표를 읽는 중"):
    WL, CTRY, YRS = load_ref()
HS_NAME = {h: SHORT.get(h, n) for h, n in zip(WL["hs6"], WL["name_ko"])}
CTRY = CTRY[CTRY["stat_cd"] != "ZZ"]                       # 기타국(ZZ)은 한 나라가 아니라 국가 목록에서 뺀다
NAME = dict(zip(CTRY["stat_cd"], CTRY["name_ko"]))
CODE = {n: c for c, n in NAME.items()}
WHERE = {n: (float(la) if pd.notna(la) else None, float(lo) if pd.notna(lo) else None)
         for n, la, lo in zip(CTRY["name_ko"], CTRY["lat"], CTRY["lon"])}
Q_YEARS = YRS["year"].astype(int).tolist()
_part = YRS[YRS["p"] == 1]
PARTIAL_YEAR = int(_part["year"].iloc[0]) if not _part.empty else 9999
PARTIAL_TXT = f"{int(_part['m0'].iloc[0])}~{int(_part['m1'].iloc[0])}월" if not _part.empty else ""
LAST_FULL = max(y for y in Q_YEARS if y != PARTIAL_YEAR)
Q_COUNTRIES = CTRY["name_ko"].tolist()                   # 교역액(수입 + 수출) 큰 순
# 품목코드 — HS6 = 분석 대상 13개(기준표 순서), HS10 = 그 아래 실적이 있는 코드(품명은 ref_hs_code_master, 없으면 코드만)
HS6_OPTS = {h: HS_NAME[h] for h in WL["hs6"]}
_h10 = load_hs10_all()
HS10_OPTS = {r.hs10: (r.name_ko.strip() if isinstance(r.name_ko, str) else "") for r in _h10.itertuples()}


def period_txt(s: dict) -> str:
    """출처 줄의 자료 기간 — 기간이 없는 목록형 자료는 「기준일 미표기」, 조회 실패는 그대로 알린다(DB 적재일은 쓰지 않는다)."""
    if s.get("error") and not s.get("has_period"):
        return "—(조회 실패)"
    return s["period"] if s.get("has_period") else "기준일 미표기"


# 군수품 FSG/FSC · 국산화개발 — 전자 계열 행을 한 번 읽어 두고 조건은 pandas 로 거른다(각 2~3천 행)
FSG_NAME, FSC_NAME = load_fsg_ref()
QF_ITEMS = load_fsg_items()
QL_ITEMS = load_localized()
SRC_PLAN = f"방위사업청 · 군수품조달정보 국외 조달계획 OpenAPI(15158418) · 요구연도 {period_txt(S_PLAN)}"
SRC_B2 = f"방위사업청 · 국방전자조달시스템 국산화개발품목(15119899) · 스냅샷({period_txt(S_B2)})"


def _groups(df: pd.DataFrame) -> tuple[dict[str, str], dict[str, list[str]]]:
    """그 자료에 실제로 있는 FSG(이름) · FSG별 FSC 목록 — 없는 분류는 선택지에서 뺀다(국산화개발은 FSG 60 행이 없다)."""
    fsg = {g: FSG_NAME.get(g, "") for g in sorted(df["FSG"].dropna().unique())}
    return fsg, {g: sorted(df.loc[df["FSG"] == g, "FSC"].dropna().unique()) for g in fsg}


QF_FSG, QF_FSC = _groups(QF_ITEMS)
QL_FSG, QL_FSC = _groups(QL_ITEMS)
QF_BRANCHES = [b for b in ("육군", "해군", "공군", "해병대", "국직", "미확인") if b in set(QF_ITEMS["군종"])]
QF_YEARS = sorted(QF_ITEMS["요구연도"].unique().tolist())
QF_YEAR_GAP = {2018, 2019, 2020}            # 원자료 공백 구간(2018 1건 · 2020 11건 — 전자 계열은 2018 1건뿐) — 연도 흐름 차트에서 뺀다
QF_KINDS = ["전체"] + sorted(QF_ITEMS["품목종류"].unique().tolist(), key=lambda k: (k == "미기재", k))
QL_PROJECTS = QL_ITEMS["사업명"].value_counts().index.tolist()          # 기록이 많은 사업부터
QL_COMPANIES = QL_ITEMS["관련 업체"].value_counts().index.tolist()

Q_AREAS = ["수출입", "수출", "수입"]
# 지표 이름, 단위, 아이콘, 쓸 수 있는 분석영역 — 3개씩 두 줄
Q_METRICS = [("수출액", "백만 USD", "", {"수출입", "수출"}), ("수입액", "백만 USD", "", {"수출입", "수입"}),
             ("무역수지", "백만 USD", "", {"수출입"}), ("수출중량", "톤", "", {"수출입", "수출"}),
             ("수입중량", "톤", "", {"수출입", "수입"})]
# 거래건수는 DB 에 없는 지표라 두지 않는다 — fact_customs_monthly 는 HS10 × 국가 × 월 합계 행이다
Q_UNIT = {m: u for m, u, _, _ in Q_METRICS}
Q_MONEY = ("수출액", "수입액", "무역수지")
# 차트 유형 — KOSIS 「데이터 시각화 체험하기」 차트 목록 15종. 고른 차트로 결과를 그리고, 같은 모양으로 CSV 를 내려준다
Q_CHART_ICON = {"꺾은선 그래프": ":material/show_chart:", "막대 그래프": ":material/bar_chart:",
                "누적 막대 그래프": ":material/stacked_bar_chart:", "피라미드 그래프": ":material/align_horizontal_center:",
                "면적 그래프": ":material/area_chart:", "원형 그래프": ":material/pie_chart:", "도넛 그래프": ":material/donut_large:",
                "버블 차트": ":material/bubble_chart:", "복합 차트": ":material/finance:", "레이더 차트": ":material/radar:",
                "맵 차트": ":material/map:", "히트맵 차트": ":material/grid_on:", "트리맵 차트": ":material/dashboard:",
                "산점도 차트": ":material/scatter_plot:", "덤벨 차트": ":material/linear_scale:"}
Q_CHARTS = list(Q_CHART_ICON)
Q_CHART_COLS = 5                                              # 차트 유형 버튼 한 줄에 5개
Q_METRIC_COLOR = {"수출액": EXP, "수입액": IMP, "무역수지": SERIES[3], "수출중량": EXP_DIM,
                  "수입중량": IMP_DIM}   # 수입 파랑 · 수출 청록(①·지도와 같은 짝), 중량은 같은 색의 옅은 톤
Q_PALETTE = SERIES   # 팔레트 8색 고정 순서 — 9번째부터는 기타(ETC), 색을 돌려 쓰지 않는다


def ctry_colors(names) -> dict[str, str]:
    """국가 이름 → 색. 다른 페이지와 같은 나라 = 같은 색(ui.country_colors — 미국 파랑 · 중국 주황 · 대만 청록).
    순서대로 팔레트를 돌려 쓰면 중국이 파랑이 되는 등 페이지마다 색이 달라진다. 「기타 …」는 회색."""
    cc = country_colors([CODE.get(str(n), str(n)) for n in names if not str(n).startswith("기타")])
    return {n: (ETC if str(n).startswith("기타") else cc[CODE.get(str(n), str(n))]) for n in names}
Q_CHART_TOP = len(SERIES)   # 그림에 따로 그리는 국가 수 — 넘으면 기간 합계 상위만 두고 나머지는 「기타 N개국」 한 줄(카드 · 표 · CSV 는 전체)

# 데이터 유형 — 고르면 조회조건 · 지표 · 차트 · 결과 탭이 통째로 바뀐다. 유형마다 session_state 키 앞머리가 다르다
Q_TYPES = ["수출입 HS", "군수품 FSG/FSC", "국산화개발"]

Q_DEFAULT = {"qs_area": "수출입", "qs_hs": "HS6", "qs_ctry": ["중국", "대만", "미국"], "qs_all": False,
             "qs_item": [], "qs_item_all": True,          # 품목코드 — 기본은 분석 대상 전체
             "qs_y0": Q_YEARS[0], "qs_y1": Q_YEARS[-1], "qs_chart": "막대 그래프",
             **{f"qs_m_{m}": m in Q_MONEY for m, *_ in Q_METRICS}}

# 군수품 FSG/FSC — 지표(이름, 단위, 아이콘) · 차트. HS 지표는 이 유형에서 그리지 않는다
QF_BRANCH_ROWS = {"qf_branch_a": QF_BRANCHES[:3], "qf_branch_b": QF_BRANCHES[3:]}   # 군종 버튼 두 줄(3 + 나머지)
QF_METRICS = [("품목 건수", "건", "inventory_2"), ("FSC 수", "개", "category"),
              ("적용장비 수", "종", "precision_manufacturing"), ("KDSIS 연결 건수", "건", "link")]
QF_CHARTS = ["막대 그래프", "누적 막대 그래프", "도넛 그래프", "트리맵 차트", "꺾은선 그래프"]
QF_DEFAULT = {"qf_fsg": list(QF_FSG), "qf_fsg_all": True, "qf_fsc": [],
              **{k: list(v) for k, v in QF_BRANCH_ROWS.items()}, "qf_y0": QF_YEARS[0], "qf_y1": QF_YEARS[-1],
              "qf_name": "", "qf_func": "", "qf_kind": "전체", "qf_nsn": "", "qf_chart": "막대 그래프",
              **{f"qf_m_{m}": m in ("품목 건수", "FSC 수") for m, *_ in QF_METRICS}}
# 국산화개발 — 스냅샷 자료라 건수 · 개수만 센다(국산화율 · 성공률 · BOM 대비 비율 · 연도별 추이는 만들지 않는다)
QL_METRICS = [("국산화개발 기록 수", "건", "library_books"), ("고유 부품 수", "개", "extension"),
              ("사업 수", "개", "inventory"), ("관련 업체 수", "개", "factory")]
QL_CHARTS = ["막대 그래프", "도넛 그래프", "트리맵 차트"]
QL_DEFAULT = {"ql_proj": [], "ql_proj_all": True, "ql_fsg": list(QL_FSG), "ql_fsg_all": True, "ql_fsc": [],
              "ql_name": "", "ql_comp": [], "ql_comp_all": True, "ql_part": "", "ql_nsn": "", "ql_chart": "막대 그래프",
              **{f"ql_m_{m}": m in ("국산화개발 기록 수", "고유 부품 수") for m, *_ in QL_METRICS}}
Q_TYPE_DEFAULT = {"수출입 HS": Q_DEFAULT, "군수품 FSG/FSC": QF_DEFAULT, "국산화개발": QL_DEFAULT}
# 지표 체크박스에 쓰는 짧은 이름 — 두 칸 폭에서 「국산화개발 기…」로 잘리던 것. 지표 키 · 카드 제목은 원래 이름
Q_METRIC_SHORT = {"국산화개발 기록 수": "기록 수"}
# 빠른 설정 — 고르면 아래 조건이 한꺼번에 바뀐다(적지 않은 값은 기본값)
Q_QUICK = {
    "빠른 설정 불러오기": None,
    "수입 상위 공급국 (중국·대만·미국·일본)": {"qs_area": "수입", "qs_ctry": ["중국", "대만", "미국", "일본"],
                                     "qs_chart": "누적 막대 그래프", "qs_m_수입액": True},
    "대미 교역 점검 (미국 수출입)": {"qs_ctry": ["미국"], "qs_chart": "꺾은선 그래프", "qs_y0": LAST_FULL - 4, "qs_y1": LAST_FULL},
    "동남아 수출 (베트남·싱가포르·말레이시아·필리핀)": {"qs_area": "수출", "qs_ctry": ["베트남", "싱가포르", "말레이시아", "필리핀"],
                                          "qs_chart": "도넛 그래프", "qs_m_수출액": True},
    "기본값으로 되돌리기": {},
}


def _q_quick() -> None:
    preset = Q_QUICK.get(st.session_state.get("qs_quick"))
    if preset is None:
        return
    _q_apply(Q_DEFAULT, force=True)
    if any(k.startswith("qs_m_") for k in preset):           # 지표를 정한 설정이면 그 지표만 켠다
        st.session_state.update({f"qs_m_{m}": False for m, *_ in Q_METRICS})
    st.session_state.update(preset)
    st.session_state["qs_quick"] = "빠른 설정 불러오기"       # 고른 뒤에는 다시 안내 문구로


def _q_short(nm: str) -> str:
    """버튼에는 「그래프」 · 「차트」를 떼고 이름만 — 설명 칸 · CSV 파일명에는 전체 이름을 쓴다."""
    return nm.removesuffix(" 그래프").removesuffix(" 차트")


def _q_pick(nm: str, key: str = "qs_chart") -> None:
    st.session_state[key] = nm


def _q_label(icon: str, text: str) -> None:
    st.markdown(f"{icon}&nbsp; **{text}**")


def _q_drop(key: str, n: str) -> None:
    """칩의 ✕ — 다중선택(key)에서 n 을 뺀다. 국가 · 품목코드 · FSG · FSC · 사업명 · 업체 칩이 함께 쓴다."""
    st.session_state[key] = [c for c in st.session_state[key] if c != n]


def _q_apply(defaults: dict, force: bool = False) -> None:
    """기본값 채우기(force=True 면 덮어쓰기). 목록 값은 복사해 넣어 기본값 dict 가 같이 바뀌지 않게 한다."""
    ss = st.session_state
    for k, v in defaults.items():
        if force or k not in ss:
            ss[k] = list(v) if isinstance(v, list) else v


def _q_type_change() -> None:
    """데이터 유형 전환 — 새 유형의 키(qs_ · qf_ · ql_ 중 하나)를 기본값으로 덮어써 새로 시작한다.
    다른 유형 키는 지우지 않는다 — 같은 rerun 에서 뒤이어 도는 그 유형 위젯의 on_change(예: _q_hs_unit)가
    지워진 키를 읽다 KeyError 가 난다. 그리지 않은 위젯 키는 Streamlit 이 치운다."""
    _q_apply(Q_TYPE_DEFAULT[st.session_state["qd_type"]], force=True)


def _q_reset() -> None:
    """초기화 버튼 — 지금 데이터 유형의 분석 조건을 처음 상태로 되돌린다. 데이터 유형은 그대로 둔다."""
    ss = st.session_state
    _q_apply(Q_TYPE_DEFAULT[ss["qd_type"]], force=True)
    if ss["qd_type"] == "수출입 HS":
        ss["qs_quick"] = "빠른 설정 불러오기"
    ss["q_reset_n"] = ss.get("q_reset_n", 0) + 1                # 누를 때마다 아이콘 회전 애니메이션을 다시 건다


def _q_hs_unit() -> None:
    """HS6 ↔ HS10 전환 — 고른 품목코드를 새 단위로 옮긴다(HS6 → 그 아래 HS10 전부, HS10 → 위 HS6)."""
    ss = st.session_state
    heads = {x[:6] for x in ss.get("qs_item", [])}
    if ss.get("qs_hs", "HS6") == "HS10":
        ss["qs_item"] = [c for c in HS10_OPTS if c[:6] in heads]
    else:
        ss["qs_item"] = [c for c in HS6_OPTS if c in heads]


def _q_keep(key: str, options: list) -> list:
    """위젯을 그리기 전에 선택값을 지금 목록(options)에 있는 것만 남긴다 — 상위 조건(FSG · HS 단위)이 바뀌어
    목록에서 사라진 값이 남아 있으면 multiselect 가 오류를 낸다."""
    ss = st.session_state
    ss[key] = [v for v in ss.get(key, []) if v in options]
    return ss[key]


# 왼쪽 글씨 칸 높이 = 오른쪽 첫 입력칸 높이(px). 위로 붙여 놓고 그 높이 안에서 가운데 → 글씨와 입력칸이 같은 가로선
Q_ROW_H = {"dtype": 32, "area": 32, "hs": 32, "item": 40, "ctry": 40, "period": 40, "metric": 40,
           "fsg": 40, "fsc": 40, "branch": 32, "year": 40, "name": 40, "proj": 40, "comp": 40}
Q_CHIP_COLS = 3                                               # 고른 값을 입력칸 밑에 한 줄 3개씩
Q_CHIP_SCROLL = 10                                            # 이만큼 이상 고르면 칩 칸을 스크롤로
Q_CHIP_ROWS = 3                                               # 스크롤 칸에 한 번에 보이는 칩 줄 수(칩 30px · 줄 간격 6px)
# 칩 다중선택 — 선택창 key → 칩 묶음 key. 국가 칩 묶음은 qs_chips
Q_CHIP_KEY = {"qs_ctry": "qs_chips", "qs_item": "qs_item_chips", "qf_fsg": "qf_fsg_chips", "qf_fsc": "qf_fsc_chips",
              "ql_proj": "ql_proj_chips", "ql_fsg": "ql_fsg_chips", "ql_fsc": "ql_fsc_chips", "ql_comp": "ql_comp_chips"}
# 파란 선택창 — 데이터 유형 드롭다운 · 기간 · 요구연도
Q_YEAR_KEYS = ["qd_type", "qs_y0", "qs_y1", "qf_y0", "qf_y1"]


def _q_form_css(hints: dict[str, str]) -> str:
    """분석 조건 카드 CSS. hints = {칩 다중선택(multiselect) key: 입력칸 안 안내 문구} — 그 화면에 그린 선택창만 넘긴다.
    칩 모양 · 말풍선 규칙은 칩 묶음 key 전부(Q_CHIP_KEY)에 건다(체크박스 드롭다운 칩 포함)."""
    rows = "".join(f".st-key-card_form .st-key-qlab_{k}{{height:{h}px !important;flex:0 0 auto !important;justify-content:center !important}}"
                   for k, h in Q_ROW_H.items())
    ms = list(hints)
    chips = list(Q_CHIP_KEY.values())
    sel = lambda keys, tail: ",".join(f".st-key-{k} {tail}" for k in keys)
    hint_css = "".join(
        f'.st-key-{k} [data-testid="stMultiSelectTagsContainer"]::before{{content:"{h}"}}' for k, h in hints.items())
    ms_css = "" if not ms else f"""
{sel(ms, '[data-testid="stMultiSelect"] > div:last-child > div')}{{background:rgba(43,110,246,.1) !important;
  border:1px solid var(--accent) !important}}
{sel(ms, '[data-testid="stMultiSelect"] > div:last-child svg')}{{color:var(--accent)}}
/* 고른 값은 입력칸 안이 아니라 밑에 칩으로 쌓는다 */
{sel(ms, '[data-testid="stMultiSelectTagsContainer"] > span')}{{display:none}}
{sel(ms, '[data-testid="stMultiSelectTagsContainer"]::before')}{{color:#5a7fc9;font-size:15.5px;
  padding-left:4px;white-space:nowrap;align-self:center}}
{hint_css}
{sel(ms, '[data-testid="stMultiSelectTagsContainer"]:has(input:focus)::before')}{{content:none}}
{sel(ms, 'input:disabled::placeholder')}{{color:transparent}}   /* 전체 선택으로 잠기면 안내 문구만(관련 업체 칸에서 겹쳤다) */"""
    return f"""<style>{rows}
/* Streamlit 기본 margin-bottom:-16px 이 글씨 칸을 3px 로 눌러 글씨가 아래로 삐져나왔다(약 8px 낮아 보이던 원인) */
.st-key-card_form div[class*="st-key-qlab_"] [data-testid="stMarkdownContainer"],
.st-key-card_form [data-testid="stMarkdownContainer"]:has(h3){{margin-bottom:0 !important}}
.st-key-card_form div[class*="st-key-qlab_"] [data-testid="stMarkdownContainer"] p{{line-height:1.2}}
/* 데이터 유형 · 기간 · 요구연도 선택창 — 분석영역에서 고른 칸과 같은 색 */
{sel(Q_YEAR_KEYS, '[data-testid="stSelectbox"] > div:last-child > div')}{{background:rgba(43,110,246,.1) !important;
  border:1px solid var(--accent) !important}}
{sel(Q_YEAR_KEYS, '[data-testid="stSelectbox"] > div:last-child svg')}{{color:var(--accent)}}
/* 연도 숫자는 검은색 */
{sel(Q_YEAR_KEYS, '[data-testid="stSelectbox"] > div:last-child div')},
{sel(Q_YEAR_KEYS, '[data-testid="stSelectbox"] input')}{{color:#111;font-weight:600}}
{ms_css}
/* 칩 — 남색, 한 줄 · 말줄임 */
{sel(chips, '')}{{gap:6px}}
{sel(chips, '[data-testid="stHorizontalBlock"]')}{{gap:6px;margin-bottom:0 !important}}
{sel(chips, 'button')}{{min-height:0;height:30px;padding:0 8px 0 12px;border-radius:6px;border:0;background:#1f3a6e;color:#fff;
  justify-content:space-between}}
{sel(chips, 'button:hover')}{{background:#142850;color:#fff}}
{sel(chips, 'button > div')},{sel(chips, 'button > div > span')}{{width:100%;justify-content:space-between}}
{sel(chips, 'button p')}{{font-size:14.5px;font-weight:600;text-align:left;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}}
{sel(chips, 'button [data-testid="stMarkdownContainer"]')}{{min-width:0;flex:1 1 auto;overflow:hidden;text-align:left}}   /* wrap=True 라도 한 줄 · … */
{sel(chips, 'button [data-testid="stIconMaterial"]')}{{color:#fff !important;font-size:17px}}
/* 군종 두 줄 — 칸마다 폭을 한 줄 3칸 기준(1/3)으로 고정해 윗줄 · 아랫줄 칸 넓이를 맞춘다.
   다중선택 segmented_control 은 고른 칸에 aria-checked 없이 data-selected 만 붙어 전역 파랑 규칙이 안 걸렸다 → 여기서 같은 색 */
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"]{{flex:0 0 calc(100% / 3) !important;
  max-width:calc(100% / 3);min-width:0}}
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"][data-selected]{{
  background:rgba(43,110,246,.1);border-color:var(--accent);color:var(--accent)}}
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"][data-selected] p{{font-weight:700}}   /* 고른 군종은 굵게 */
div[class*="st-key-qf_branch_"] [data-testid="stButtonGroup"] > div{{justify-content:flex-start}}
/* 커서를 올렸을 때 — Streamlit 기본 강조색(빨강)이 테두리에 들던 것을 테마 파랑으로 */
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"]:hover,
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"]:focus-visible{{
  border-color:var(--accent) !important;color:var(--accent) !important;background:rgba(43,110,246,.05) !important;
  box-shadow:none !important}}
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"][data-selected]:hover{{
  background:rgba(43,110,246,.16) !important}}
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"]:hover *{{color:var(--accent) !important}}
/* 두 줄이 맞닿는 모서리는 직각 — 윗줄 아래 모서리 · 아랫줄 위 모서리(윗줄 끝 칸 아래 오른쪽은 밑에 칸이 없어 둥근 채로) */
.st-key-qf_branch_a button[data-variant="segmented_control"]{{border-bottom-left-radius:0 !important}}
.st-key-qf_branch_a button[data-variant="segmented_control"]:not(:last-of-type){{border-bottom-right-radius:0 !important}}
.st-key-qf_branch_b button[data-variant="segmented_control"]{{border-top-left-radius:0 !important;border-top-right-radius:0 !important}}
.st-key-qf_branch_box{{gap:0 !important}}
.st-key-qf_branch_box [data-testid="stElementContainer"]:has(.st-key-qf_branch_b),.st-key-qf_branch_b{{margin-top:-1px}}
/* 체크박스 드롭다운(품목코드 · 국가 · FSC) — 펼친 목록이 아래 줄을 덮도록 위로 올린다 */
.st-key-qs_item_box,.st-key-qs_ctry_box,.st-key-qf_fsc_box,.st-key-ql_fsc_box{{position:relative;z-index:40;overflow:visible}}
/* 상세검색 접이 칸 — 카드 안에서 얇게 */
.st-key-card_form [data-testid="stExpander"] summary p{{font-size:15px;font-weight:700;color:#16233f}}
/* 도움말 말풍선 글씨 — 기본보다 2pt 작게 */
[data-testid="stTooltipContent"],[data-testid="stTooltipContent"] p{{font-size:calc(14px - 2pt)}}
/* 칩 말풍선 — 안 잘린 칩에 커서가 있을 때(_CHIP_FIT_JS)는 숨긴다 */
.st-key-chipfit_js,[data-testid="stLayoutWrapper"]:has(> .st-key-chipfit_js){{display:none!important}}
html[data-chipfit] [role="tooltip"]:has([data-testid="stTooltipContent"]),
html[data-chipfit] [data-testid="stTooltipContent"]{{display:none!important}}
</style>"""


def _q_row(icon: str, text: str, key: str):
    """분석 조건 한 줄 — 왼쪽 글씨 칸(높이 Q_ROW_H[key]) · 오른쪽 입력 칸을 돌려준다."""
    a, b = st.columns([1, 2.55], vertical_alignment="top")
    with a.container(key=f"qlab_{key}"):
        _q_label(icon, text)
    return b


def _q_chip_select(key: str, options: list, fmt, placeholder: str, all_key: str | None = None,
                   all_label: str = "") -> list:
    """칩 다중선택 — 검색 가능한 선택창 + 고른 값은 밑에 칩(✕ 로 빼기) + (있으면) 전체 선택 체크.
    all_key 가 켜져 있으면 options 전부를 돌려준다. 선택창 안내 문구는 _q_hint 로 CSS 에 넣는다."""
    ss = st.session_state
    all_on = bool(all_key and ss[all_key])
    _q_keep(key, options)
    picked = st.multiselect(key, options, key=key, format_func=fmt, label_visibility="collapsed",
                            placeholder=placeholder, disabled=all_on)
    if not all_on:
        _q_chips(key, picked, fmt, scroll=True)
    if all_key:
        st.checkbox(all_label, key=all_key)
    return list(options) if all_on else picked


# 칩 말풍선 — 글씨가 칩 안에서 … 로 잘린 칩에만 보인다. 잘렸는지는 화면 폭에 따라 달라 서버에서 알 수 없으므로
# 모든 칩에 help 를 달고, 브라우저에서 커서를 올린 순간 글씨 폭(scrollWidth > clientWidth)을 재서
# 안 잘린 칩이면 <html data-chipfit> 를 켜 말풍선 층을 숨긴다
_CHIP_FIT_JS = """
export default function () {
  if (window.__kdChipFit) return
  window.__kdChipFit = true
  const root = document.documentElement
  document.addEventListener("pointerover", e => {
    // 말풍선을 여는 곳(도움말 대상)에 들어갈 때만 판단을 바꾼다. 빈 곳 · 말풍선 위로 옮길 때는 그대로 둔다 —
    // 말풍선은 커서가 떠난 뒤에도 잠깐 열려 있어, 칩을 벗어나자마자 표시를 끄면 숨겼던 말풍선이 그 사이에 드러났다
    const tgt = e.target.closest && e.target.closest('[data-testid="stTooltipHoverTarget"]')
    if (!tgt) return
    const btn = tgt.closest('[class*="st-key-"][class*="chips"]') && tgt.querySelector("button")
    const p = btn && btn.querySelector("p")
    if (p && p.scrollWidth <= p.clientWidth + 1) root.setAttribute("data-chipfit", "")
    else root.removeAttribute("data-chipfit")
  }, true)
}
"""
_CHIP_FIT = st.components.v2.component("kd_chip_fit", html="<span></span>", js=_CHIP_FIT_JS)


def _q_chips(key: str, picked: list, fmt, scroll: bool = False) -> None:
    """고른 값을 선택창 밑에 칩(✕ 로 빼기)으로 한 줄 Q_CHIP_COLS 개씩 쌓는다.
    scroll=True 이고 Q_CHIP_SCROLL 개 이상이면 칩 칸 높이를 Q_CHIP_ROWS 줄로 묶고 나머지는 스크롤로 본다(조건 카드가 길어지지 않게)."""
    if not picked:
        return
    ck = Q_CHIP_KEY[key]
    if scroll and len(picked) >= Q_CHIP_SCROLL:
        h = Q_CHIP_ROWS * 30 + (Q_CHIP_ROWS - 1) * 6
        st.html(f"""<style>
.st-key-{ck}{{max-height:{h}px;overflow-y:auto;overflow-x:hidden;padding-right:6px;scrollbar-width:thin;
  scrollbar-color:#b7c4da transparent}}
.st-key-{ck} > *{{flex-shrink:0}}
</style>""")
    with st.container(key=ck):
        for r in range(0, len(picked), Q_CHIP_COLS):
            for c, n in zip(st.columns(Q_CHIP_COLS, gap="small"), picked[r:r + Q_CHIP_COLS]):
                label = fmt(n)
                # 말풍선 = 전체 이름(안 잘린 칩은 _CHIP_FIT_JS 가 숨긴다). wrap=True — 끄면 브라우저 기본 말풍선(title)까지 둘 뜬다
                c.button(label, icon=":material/close:", icon_position="right",
                         key=f"qs_chip_{n}" if key == "qs_ctry" else f"{key}_chip_{n}",
                         on_click=_q_drop, args=(key, n), width="stretch", wrap=True, help=label)


# 체크박스 드롭다운(CCv2) — 품목코드 · 국가 · FSC 선택용. 목록 앞 체크박스로 여러 개를 고르는 동안에는 반영하지 않고,
# 드롭다운 밖으로 포커스가 나가면(바깥 클릭 · Tab · Esc) 고른 것을 한 번에 넘긴다(commit 트리거 → rerun 1번).
# 기본 multiselect 는 하나 고를 때마다 rerun 해서 조회 결과(DB 조회)가 매번 다시 그려졌다
_CHECK_DD_HTML = """
<div class="dd">
  <button class="field" type="button"><span class="txt"></span><span class="arr">▾</span></button>
  <div class="panel" tabindex="-1" hidden>
    <input class="q" type="text" autocomplete="off" />
    <div class="tools"><button type="button" class="all">전체 선택</button><button type="button" class="none">선택 해제</button>
      <span class="cnt"></span></div>
    <div class="list"></div>
  </div>
</div>
"""
_CHECK_DD_CSS = """
.dd{position:relative;font:15.5px Pretendard,'Malgun Gothic',system-ui,sans-serif}
.field{width:100%;height:40px;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:0 12px;
  border-radius:8px;border:1px solid #2b6ef6;background:rgba(43,110,246,.1);color:#5a7fc9;font:inherit;cursor:pointer;text-align:left}
.dd.off .field{opacity:.55;cursor:not-allowed}
.field .txt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.field .arr{color:#2b6ef6;font-size:12px;transition:transform .15s}
.dd.open .field .arr{transform:rotate(180deg)}
.panel{position:absolute;left:0;right:0;top:44px;z-index:1000;background:#fff;border:1px solid #c9d3e6;border-radius:10px;
  box-shadow:0 12px 30px rgba(20,40,80,.18);padding:8px;outline:none}
.q{width:100%;box-sizing:border-box;height:34px;border:1px solid #d6dbe6;border-radius:6px;padding:0 10px;font:inherit;color:#111}
.q:focus{outline:none;border-color:#2b6ef6}
.tools{display:flex;align-items:center;gap:6px;margin:6px 2px}
.tools button{border:0;background:none;color:#2b6ef6;font:600 13.5px inherit;cursor:pointer;padding:2px 4px}
.tools .cnt{margin-left:auto;color:#6b7a99;font-size:13px}
.list{max-height:240px;overflow-y:auto}
.list label{display:flex;align-items:center;gap:8px;padding:6px 6px;border-radius:6px;cursor:pointer;color:#16233f;font-size:14.5px}
.list label:hover{background:rgba(43,110,246,.07)}
.list input{width:16px;height:16px;margin:0;accent-color:#2b6ef6;cursor:pointer;flex:0 0 auto}
.empty{padding:10px 6px;color:#6b7a99;font-size:14px}
"""
_CHECK_DD_JS = """
const S = new WeakMap()
export default function (component) {
  const { data, parentElement, setTriggerValue } = component
  const root = parentElement.querySelector(".dd")
  if (!root) return
  const field = root.querySelector(".field"), txt = root.querySelector(".txt"), panel = root.querySelector(".panel")
  const q = root.querySelector(".q"), list = root.querySelector(".list"), cnt = root.querySelector(".cnt")
  const opts = data.options || [], committed = data.selected || []
  let s = S.get(parentElement)
  if (!s) { s = { open: false, draft: new Set() }; S.set(parentElement, s) }
  if (!s.open) s.draft = new Set(committed)          // 닫혀 있을 때는 Python 값이 기준
  q.placeholder = data.search || "검색"
  field.disabled = !!data.disabled
  root.classList.toggle("off", !!data.disabled)
  if (data.disabled && s.open) { s.open = false; root.classList.remove("open") }

  const label = () => {
    const n = s.open ? s.draft.size : committed.length
    if (data.disabled) { txt.textContent = data.all_text || ""; return }
    txt.textContent = n ? `${data.noun} ${n}개 선택` + (s.open ? " · 닫으면 반영" : "") : (data.placeholder || "")
    cnt.textContent = `${s.draft.size} / ${opts.length}`
  }
  const draw = () => {
    const f = q.value.trim().toLowerCase()
    const shown = opts.filter(o => !f || o.l.toLowerCase().includes(f))
    list.innerHTML = shown.length ? "" : '<div class="empty">검색 결과가 없습니다.</div>'
    for (const o of shown) {
      const lab = document.createElement("label"), cb = document.createElement("input")
      cb.type = "checkbox"; cb.checked = s.draft.has(o.v)
      cb.onchange = () => { cb.checked ? s.draft.add(o.v) : s.draft.delete(o.v); label() }
      lab.append(cb, document.createTextNode(o.l)); list.append(lab)
    }
    label()
  }
  const open = () => { s.open = true; root.classList.add("open"); panel.hidden = false; q.value = ""; draw(); q.focus() }
  const close = () => {
    if (!s.open) return
    s.open = false; root.classList.remove("open"); panel.hidden = true
    const next = opts.map(o => o.v).filter(v => s.draft.has(v))
    label()
    if (next.length !== committed.length || next.some((v, i) => v !== committed[i])) setTriggerValue("commit", next)
  }
  field.onclick = () => (s.open ? close() : open())
  q.oninput = draw
  root.querySelector(".all").onclick = () => { opts.forEach(o => s.draft.add(o.v)); draw() }
  root.querySelector(".none").onclick = () => { s.draft.clear(); draw() }
  root.onkeydown = e => { if (e.key === "Escape") { close(); field.focus() } }
  // 드롭다운 밖으로 포커스가 나가면 닫으면서 한 번에 반영(패널 여백 클릭은 panel 이 포커스를 받아 안 닫힌다)
  root.onfocusout = e => { if (s.open && !root.contains(e.relatedTarget)) close() }
  panel.hidden = !s.open
  if (s.open) draw(); else label()
}
"""
_CHECK_DD = st.components.v2.component("kd_check_dropdown", html=_CHECK_DD_HTML, css=_CHECK_DD_CSS, js=_CHECK_DD_JS)


def _q_check_commit(key: str) -> None:
    v = st.session_state[f"{key}_dd"].commit
    if v is not None:
        st.session_state[key] = list(v)


def _q_check_select(key: str, options: list, fmt, noun: str, placeholder: str, search: str = "",
                    all_key: str | None = None, all_label: str = "", all_text: str = "") -> list:
    """체크박스 드롭다운 + 칩(+ 있으면 전체 선택 체크). 고른 값은 session_state[key](목록)에 두고,
    드롭다운을 닫을 때 한 번에 바뀐다. all_key 가 켜져 있으면 드롭다운을 잠그고 options 전부를 돌려준다."""
    all_on = bool(all_key and st.session_state[all_key])
    picked = _q_keep(key, options)
    with st.container(key=f"{key}_box"):
        _CHECK_DD(key=f"{key}_dd", data={"options": [{"v": o, "l": fmt(o)} for o in options], "selected": picked,
                                         "noun": noun, "placeholder": placeholder, "disabled": all_on,
                                         "all_text": all_text, "search": search or f"{noun} 코드 · 이름 검색"},
                  on_commit_change=lambda: _q_check_commit(key))
    if not all_on:
        _q_chips(key, picked, fmt, scroll=True)
    if all_key:
        st.checkbox(all_label, key=all_key)
    return list(options) if all_on else picked


def _q_hint(key: str, all_key: str | None, noun: str, all_text: str) -> str:
    """선택창 안내 문구 — 전체 선택 중 · n개 선택 · (비었으면) 빈칸."""
    ss = st.session_state
    if all_key and ss.get(all_key):
        return all_text
    n = len(ss.get(key, []))
    return f"{noun} 검색 · {n}개 선택" if n else ""


def _q_chart_grid(charts: list[str], state_key: str, subject: str = "국가", shapes: dict | None = None) -> str:
    """차트 유형 버튼 묶음 — charts 에 든 것만 그린다(안 되는 차트는 아예 빼고 잠그지 않는다). 고른 차트 이름을 돌려준다."""
    ss = st.session_state
    if ss.get(state_key) not in charts:
        ss[state_key] = charts[0]
    chart = ss[state_key]
    st.html(_csv_css())
    # 버튼에 커서를 올리면 그 차트 설명(차트 목록 설명 칸)이 버튼 묶음 위로 떠서 조건 칸을 덮는다
    with st.container(key="qs_ct_grid"):
        for r in range(0, len(charts), Q_CHART_COLS):
            cols = st.columns(Q_CHART_COLS, gap="small")
            for i, (c, nm) in enumerate(zip(cols, charts[r:r + Q_CHART_COLS]), start=r):
                c.button(_q_short(nm), icon=Q_CHART_ICON[nm], key=f"qs_ct_{i}", width="stretch", on_click=_q_pick,
                         args=(nm, state_key), type="primary" if chart == nm else "secondary")
                with c.container(key=f"qs_pop_{i}"):
                    st.html(csv_info(nm, subject, (shapes or {}).get(nm)))
    return chart


def query_panel() -> dict:
    """분석 조건 설정 카드. 맨 위 데이터 유형에 따라 HS · FSG/FSC · 국산화개발 조건을 그리고,
    고른 조건을 dict 로 돌려준다(q["type"] = 데이터 유형).
    FIXED_TYPE — 부르는 쪽이 runpy init_globals 로 넘기면 그 유형으로 고정하고 「데이터 유형」 칸을 숨긴다(상세 조회 3곳).
    다른 유형 키는 그리지 않으면 Streamlit 이 치우므로, 돌아오면 아래 _q_apply 가 기본값을 다시 채운다."""
    fixed = globals().get("FIXED_TYPE")
    if fixed in Q_TYPES:
        st.session_state["qd_type"] = fixed
    st.session_state.setdefault("qd_type", Q_TYPES[0])
    dtype = st.session_state["qd_type"]
    _q_apply(Q_TYPE_DEFAULT[dtype])
    with st.container(border=True, key="card_form"):
        h1, h2 = st.columns([1.25, 1], vertical_alignment="center")
        h1.html('<div class="h" style="font-size:17px">분석 조건 설정</div>')   # 「조회 결과」 제목과 같은 모양(파란 막대) — 글씨는 조금 크게
        if dtype == "수출입 HS":                                   # 빠른 설정은 HS 조건 묶음이라 HS 에서만
            h2.selectbox("빠른 설정", list(Q_QUICK), key="qs_quick", on_change=_q_quick, label_visibility="collapsed")
        # filter_mode=None — 클릭하면 목록만 열리고 글자 입력(검색)은 받지 않는다
        if fixed not in Q_TYPES:
            _q_row(":material/database:", "데이터 유형", "dtype").selectbox(
                "데이터 유형", Q_TYPES, key="qd_type", on_change=_q_type_change, label_visibility="collapsed",
                filter_mode=None)
        panel = {"수출입 HS": query_panel_hs, "군수품 FSG/FSC": query_panel_fsg, "국산화개발": query_panel_localized}[dtype]
        q = panel()
        _q_reset_button()
        with st.container(key="chipfit_js"):
            _CHIP_FIT(key="chipfit")
    return q | {"type": dtype}


def _q_reset_button() -> None:
    """차트 유형 밑 초기화 버튼. 누르면 화살표 아이콘이 한 바퀴 돌고 조건이 처음 상태로 돌아간다.
    누를 때마다 애니메이션 이름을 바꿔(q_spin0 ↔ q_spin1) 같은 아이콘에서도 회전이 다시 시작되게 한다."""
    n = st.session_state.get("q_reset_n", 0)
    spin = f"animation:q_spin{n % 2} .7s ease-in-out;" if n else ""
    st.html(f"""<style>
@keyframes q_spin0{{from{{transform:rotate(0)}}to{{transform:rotate(360deg)}}}}
@keyframes q_spin1{{from{{transform:rotate(0)}}to{{transform:rotate(360deg)}}}}
.st-key-q_reset{{margin-top:6px}}
.st-key-q_reset button{{height:38px;border-radius:8px;border:1px solid var(--line);background:#fff;color:#4b5a78}}
.st-key-q_reset button:hover{{border-color:var(--accent);color:var(--accent)}}
.st-key-q_reset button [data-testid="stIconMaterial"]{{font-size:19px;color:inherit !important;{spin}}}
</style>""")
    st.button("조건 초기화", icon=":material/sync:", key="q_reset", on_click=_q_reset, width="stretch")


def _hs_label(unit: str, items: list[str] | None) -> str:
    """결과 · CSV 머리에 쓰는 품목 표기 — 전체 · 한 개(이름) · 여러 개(개수)."""
    if items is None:
        return f"분석 대상 {len(WL)}개 합계"
    if len(items) == 1:
        c = items[0]
        nm = HS6_OPTS.get(c) if unit == "HS6" else HS10_OPTS.get(c)
        return f"{nm} {c}" if nm else c
    return f"{unit} {len(items)}개"


def query_panel_hs() -> dict:
    """수출입 HS 조건 — 분석영역 · HS 단위 · 품목코드 · 국가/지역 · 기간 · 지표 · 차트."""
    ss = st.session_state
    st.html(_q_form_css({}))
    area = _q_row(":material/travel_explore:", "분석영역", "area").segmented_control(
        "분석영역", Q_AREAS, key="qs_area", required=True, label_visibility="collapsed", width="stretch")
    hs = _q_row(":material/qr_code_2:", "HS6/HS10", "hs").segmented_control(
        "HS 단위", ["HS6", "HS10"], key="qs_hs", required=True, on_change=_q_hs_unit, label_visibility="collapsed")
    codes = HS6_OPTS if hs == "HS6" else HS10_OPTS
    with _q_row(":material/barcode:", "품목코드", "item"):
        items = _q_check_select("qs_item", list(codes), lambda c: f"{c} - {codes[c]}" if codes[c] else c, "품목코드",
                                f"{hs} 품목코드를 고르세요.", f"{hs} 코드 · 품목명 검색", "qs_item_all",
                                f"전체 품목 선택 ({hs} {len(codes)}개)", f"전체 {hs} 품목 선택 중")
    with _q_row(":material/public:", "국가/지역", "ctry"):
        names = _q_check_select("qs_ctry", Q_COUNTRIES, str, "국가", "국가를 고르세요.", "국가명 검색",
                                "qs_all", f"전체 국가 선택 ({len(Q_COUNTRIES)}개국)", "전체 국가 선택 중")
    with _q_row(":material/calendar_month:", "기간", "period"):
        # 두 칸에서 연도를 고른다 — 시작 칸은 끝 연도까지만, 끝 칸은 시작 연도부터만 보여 앞뒤가 뒤집히지 않는다
        c0, mid, c1 = st.columns([1, .16, 1], vertical_alignment="center", gap="small")
        y0 = c0.selectbox("시작 연도", [y for y in Q_YEARS if y <= ss["qs_y1"]], key="qs_y0", label_visibility="collapsed")
        mid.html('<div style="text-align:center;font-size:18px;font-weight:700;color:#6b7a99">~</div>')
        y1 = c1.selectbox("끝 연도", [y for y in Q_YEARS if y >= y0], key="qs_y1", label_visibility="collapsed")
    with _q_row(":material/leaderboard:", "지표 선택", "metric"):
        # 분석영역에 맞는 지표만 그린다(맞지 않는 지표는 잠그지 않고 아예 뺀다)
        shown = [m for m, _, _, areas in Q_METRICS if area in areas]
        cols = st.columns(3)
        metrics = [m for i, m in enumerate(shown) if cols[i % 3].checkbox(m, key=f"qs_m_{m}")]
    _q_label(":material/donut_large:", "차트 유형")
    chart = _q_chart_grid(Q_CHARTS, "qs_chart")
    names = [n for n in Q_COUNTRIES if n in names]
    sel = None if ss["qs_item_all"] else items
    return {"area": area, "unit": hs, "items": sel, "n_items": len(items), "hs": _hs_label(hs, sel), "names": names,
            "period": f"{y0} ~ {y1}", "years": (y0, y1), "metrics": metrics, "chart": chart}


def _q_fsg_fsc(pre: str, fsc_ph: str, groups: dict[str, str],
               fsc_of: dict[str, list[str]]) -> tuple[list[str], list[str], list[str]]:
    """FSG(칩 다중선택 + 전체) → FSC(고른 FSG 안의 것만, 체크박스 드롭다운). FSC 를 비우면 고른 FSG 의 FSC 전부.
    군수품 · 국산화개발 두 화면이 같이 쓴다(pre = qf_ / ql_). groups · fsc_of = 그 자료에 실제로 있는 분류만.
    (FSG, 사용자가 고른 FSC(비었으면 []), 조회에 쓸 FSC) — 군수품은 둘째 값이 비었는지로 집계 단위(FSG · FSC)를 정한다."""
    with _q_row(":material/category:", "FSG", "fsg"):
        fsg = _q_chip_select(f"{pre}fsg", list(groups), lambda g: f"{g} - {groups[g]}", "FSG 를 검색하세요.",
                             f"{pre}fsg_all", f"전체 FSG 선택 ({len(groups)}개)")
    opts = [c for g in fsg for c in fsc_of[g]]
    with _q_row(":material/account_tree:", "FSC", "fsc"):
        fsc = _q_check_select(f"{pre}fsc", opts, lambda c: f"{c} - {FSC_NAME.get(c, '')}", "FSC", fsc_ph)
    return fsg, fsc, fsc or opts


def _q_metric_row(pre: str, metrics: list[tuple]) -> list[str]:
    with _q_row(":material/leaderboard:", "지표 선택", "metric"):
        cols = st.columns(2)
        return [m for i, (m, *_) in enumerate(metrics)
                if cols[i % 2].checkbox(Q_METRIC_SHORT.get(m, m), key=f"{pre}m_{m}")]


# 차트 설명 칸의 「CSV 데이터 모양」 — 군수품 · 국산화개발용(분류 = FSG 또는 FSC)
QF_SHAPES = {"막대 그래프": "행 = 분류 · 열 = 지표", "누적 막대 그래프": "행 = 요구연도 · 열 = 분류 + 합계",
             "도넛 그래프": "행 = 분류 · 값 · 비중(%)", "트리맵 차트": "행 = 분류 · 값 · 비중(%)",
             "꺾은선 그래프": "행 = 요구연도 · 열 = 분류"}
QL_SHAPES = {"막대 그래프": "행 = FSC · 열 = 지표", "도넛 그래프": "행 = FSC · 값 · 비중(%)",
             "트리맵 차트": "행 = FSC · 값 · 비중(%)"}


def query_panel_fsg() -> dict:
    """군수품 FSG/FSC 조건 — 분류 단위 · FSG · FSC · 군종 · 요구연도 · 품목명 · 상세검색 · 지표 · 차트."""
    ss = st.session_state
    st.html(_q_form_css({"qf_fsg": _q_hint("qf_fsg", "qf_fsg_all", "FSG", "전체 FSG 선택 중")}))
    # 집계 단위는 따로 고르지 않는다 — FSC 를 비우면(= 고른 FSG 아래 전체) FSG 단위, 하나라도 고르면 FSC 단위.
    # FSG 가 FSC 의 상위 분류라 「분류 단위 FSG/FSC」 토글은 두 분류체계 중 하나를 고르는 것처럼 보여 두지 않는다
    fsg, picked_fsc, fsc = _q_fsg_fsc("qf_", "FSC 를 고르세요 · 비우면 FSG 단위로 집계", QF_FSG, QF_FSC)
    unit = "FSC" if picked_fsc else "FSG"
    with _q_row(":material/military_tech:", "군종", "branch"), st.container(key="qf_branch_box", gap=None):
        # 한 줄에 다 두면 카드 폭이 좁아 가려져 두 줄(3 + 나머지)로 나눈다. 고른 값은 두 줄을 합친다
        branch = [b for k, opts in QF_BRANCH_ROWS.items() if opts
                  for b in (st.segmented_control(f"군종 {k[-1]}", opts, key=k, selection_mode="multi",
                                                 label_visibility="collapsed", width="stretch") or [])]
    with _q_row(":material/calendar_month:", "요구연도", "year"):
        c0, mid, c1 = st.columns([1, .16, 1], vertical_alignment="center", gap="small")
        y0 = c0.selectbox("시작 연도", [y for y in QF_YEARS if y <= ss["qf_y1"]], key="qf_y0", label_visibility="collapsed")
        mid.html('<div style="text-align:center;font-size:18px;font-weight:700;color:#6b7a99">~</div>')
        y1 = c1.selectbox("끝 연도", [y for y in QF_YEARS if y >= y0], key="qf_y1", label_visibility="collapsed")
    name = _q_row(":material/search:", "품목명", "name").text_input(
        "품목명", key="qf_name", placeholder="품목명(영문)을 입력하세요.", label_visibility="collapsed")
    with st.expander("상세검색 — 기능명 · 품목종류 · NSN", icon=":material/tune:"):
        d1, d2, d3 = st.columns(3)
        func = d1.text_input("기능명", key="qf_func", placeholder="예: 함정")
        kind = d2.selectbox("품목종류", QF_KINDS, key="qf_kind")
        nsn = d3.text_input("NSN", key="qf_nsn", placeholder="예: 5962")
    metrics = _q_metric_row("qf_", QF_METRICS)
    _q_label(":material/donut_large:", "차트 유형")
    chart = _q_chart_grid(QF_CHARTS, "qf_chart", "분류", QF_SHAPES)
    return {"unit": unit, "fsg": fsg, "fsc": fsc, "branch": branch, "years": (y0, y1), "name": name.strip(),
            "func": func.strip(), "kind": kind, "nsn": nsn.strip(), "metrics": metrics, "chart": chart}


def query_panel_localized() -> dict:
    """국산화개발 조건 — 사업명 · FSG · FSC · 품목명 · 관련 업체 · 상세검색 · 지표 · 차트. 기간 조건은 없다(스냅샷)."""
    st.html(_q_form_css({"ql_proj": _q_hint("ql_proj", "ql_proj_all", "사업명", "전체 사업 선택 중"),
                         "ql_fsg": _q_hint("ql_fsg", "ql_fsg_all", "FSG", "전체 FSG 선택 중"),
                         "ql_comp": _q_hint("ql_comp", "ql_comp_all", "관련 업체", "전체 관련 업체 선택 중")}))
    with _q_row(":material/inventory:", "사업명", "proj"):
        proj = _q_chip_select("ql_proj", QL_PROJECTS, str, "사업명을 검색하세요.",
                              "ql_proj_all", f"전체 사업 선택 ({len(QL_PROJECTS)}개)")
    fsg, _, fsc = _q_fsg_fsc("ql_", "FSC 를 고르세요 · 비우면 고른 FSG 전체", QL_FSG, QL_FSC)
    name = _q_row(":material/search:", "품목명", "name").text_input(
        "품목명", key="ql_name", placeholder="국산화개발 품목명을 입력하세요.", label_visibility="collapsed")
    with _q_row(":material/factory:", "관련 업체", "comp"):
        comp = _q_chip_select("ql_comp", QL_COMPANIES, str, "관련 업체를 검색하세요.",
                              "ql_comp_all", f"전체 관련 업체 선택 ({len(QL_COMPANIES)}개)")
    with st.expander("상세검색 — 부품관리번호 · NSN", icon=":material/tune:"):
        d1, d2 = st.columns(2)
        part = d1.text_input("부품관리번호", key="ql_part", placeholder="예: M00002105")
        nsn = d2.text_input("NSN", key="ql_nsn", placeholder="예: 3750")
    metrics = _q_metric_row("ql_", QL_METRICS)
    _q_label(":material/donut_large:", "차트 유형")
    chart = _q_chart_grid(QL_CHARTS, "ql_chart", "FSC", QL_SHAPES)
    return {"proj": proj, "fsg": fsg, "fsc": fsc, "name": name.strip(), "comp": comp, "part": part.strip(),
            "nsn": nsn.strip(), "metrics": metrics, "chart": chart}


def _chart_frame(df: pd.DataFrame, names: list[str], primary: str) -> tuple[pd.DataFrame, list[str], int]:
    """그림용 국가 줄이기 — 고른 국가가 Q_CHART_TOP 보다 많으면(예: 전체 국가 선택) 기간 합계 상위 국가만 두고
    나머지는 연도별로 더해 「기타 N개국」 한 줄로 만든다. 무역수지는 절댓값 순. 돌려주는 값: (그림용 표, 국가 순서, 합친 국가 수)."""
    if len(names) <= Q_CHART_TOP:
        return df, names, 0
    tot = df.groupby("국가")[primary].sum()
    key = tot.abs() if primary == "무역수지" else tot
    top = key.sort_values(ascending=False, kind="stable").index[:Q_CHART_TOP].tolist()
    rest = [n for n in names if n not in top]
    etc = f"기타 {len(rest)}개국"
    other = df[df["국가"].isin(rest)].groupby("연도", as_index=False)[list(Q_UNIT)].sum().assign(국가=etc)
    return pd.concat([df[df["국가"].isin(top)], other[df.columns]], ignore_index=True), top + [etc], len(rest)


def query_chart(df: pd.DataFrame, q: dict) -> tuple[go.Figure, str]:
    """차트 유형에 맞춰 그린다. 금액 지표(수출액·수입액·무역수지)끼리만 한 축에 두고,
    중량·건수는 금액이 하나도 없을 때만 그린다(단위가 달라 한 축에 섞지 않는다).
    돌려주는 값: (PNG 로 내려받을 그림, 그래프 기준 문구 — 출처 줄에 붙인다)."""
    names, chart = q["names"], q["chart"]
    plot_ms = [m for m in q["metrics"] if m in Q_MONEY] or q["metrics"][:1]
    primary = plot_ms[0]
    unit = Q_UNIT[primary]
    n_all = len(names)
    if chart != "맵 차트":                                   # 지도는 전체 국가를 그대로 칠한다
        df, names, n_rest = _chart_frame(df, names, primary)
        q = {**q, "names": names}
    else:
        n_rest = 0
    trim = (f"그래프는 {primary} 기간 합계 상위 {Q_CHART_TOP}개국 + 나머지 {n_rest}개국 합계(「기타」) — "
            f"지표 카드 · 결과 표 · CSV 는 {n_all}개국 전체" if n_rest else "")
    by_c = df.groupby("국가", sort=False)[list(Q_UNIT)].sum()
    color = ctry_colors(names)
    note = ""
    fig = go.Figure()
    png_fig = None
    if chart not in ("도넛 그래프", "막대 그래프", "꺾은선 그래프", "누적 막대 그래프", "면적 그래프"):
        # 나머지 차트는 CSV 와 같은 모양의 표로 그린다(내려받는 CSV 와 그림이 어긋나지 않게)
        out, note = csv_shape(chart, df, q)
        fig = csv_preview(chart, out)
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CFG)
        if trim:
            st.html(f'<div class="caption">{escape(trim)}</div>')
        return fig, f"그래프 기준: {note} · {escape(q['hs'])} 기준" + (f". {trim}" if trim else "")
    if chart == "도넛 그래프":
        pm = primary if primary != "무역수지" else ("수출액" if q["area"] != "수입" else "수입액")
        if pm != primary:
            note = "무역수지는 음수가 있어 원형으로 나눌 수 없어 수출액으로 그렸습니다."
        rows = sorted(((n, float(by_c.loc[n, pm]), color[n]) for n in names), key=lambda r: -r[1])
        rows = rows[:7] + ([("기타", sum(r[1] for r in rows[7:]), ETC)] if len(rows) > 7 else [])
        hover_donut(rows, f"{sum(r[1] for r in rows):,.0f}", f"{pm} 합계 · {Q_UNIT[pm]}", value_unit=Q_UNIT[pm], height=420)
        # PNG 내려받기용 — 화면 도넛(HTML)과 같은 값 · 같은 색의 plotly 도넛
        png_fig = go.Figure(go.Pie(labels=[r[0] for r in rows], values=[r[1] for r in rows], hole=.55, sort=False,
                                   marker=dict(colors=[r[2] for r in rows], line=dict(color="#fff", width=1.5)),
                                   textinfo="label+percent"))
        png_fig.update_layout(height=420, annotations=[dict(text=f"{sum(r[1] for r in rows):,.0f}<br>{pm} · {Q_UNIT[pm]}",
                                                            showarrow=False, font=dict(size=17))])
        fig = None
    elif chart == "막대 그래프":
        order = by_c.loc[names].sort_values(primary, ascending=False).index.tolist()
        for m in plot_ms:
            fig.add_trace(go.Bar(x=order, y=by_c.loc[order, m], name=m,
                                 marker=dict(color=Q_METRIC_COLOR[m], line=dict(color="#fff", width=1)),
                                 text=[f"{v:,.0f}" for v in by_c.loc[order, m]] if len(plot_ms) == 1 else None,
                                 textposition="outside", textfont=dict(size=12.5, color=TEXT), cliponaxis=False,
                                 hovertemplate="%{x} · " + m + "<br>%{y:,.1f} " + Q_UNIT[m] + "<extra></extra>"))
        fig.update_layout(barmode="group", bargap=.28)
        if len(order) > 8:
            fig.update_xaxes(tickangle=-35)
    else:
        years = sorted(df["연도"].unique())
        by_multi = len(names) == 1 and len(plot_ms) > 1      # 한 나라만 골랐으면 지표끼리 비교
        series = ([(m, df.groupby("연도")[m].sum(), Q_METRIC_COLOR[m]) for m in plot_ms] if by_multi else
                  [(n, df[df["국가"] == n].set_index("연도")[primary], color[n]) for n in names])
        for i, (nm, s, c) in enumerate(series):
            s = s.reindex(years)
            u = Q_UNIT[nm] if by_multi else unit
            tip = f"{nm} · %{{x}}년<br>%{{y:,.1f}} {u}<extra></extra>"
            if chart == "누적 막대 그래프":
                fig.add_trace(go.Bar(x=years, y=s, name=nm, marker=dict(color=c, line=dict(color="#fff", width=1)),
                                     hovertemplate=tip))
            elif chart == "면적 그래프":
                stack = primary != "무역수지" and not by_multi
                fig.add_trace(go.Scatter(x=years, y=s, name=nm, mode="lines", line=dict(color=c, width=2),
                                         stackgroup="one" if stack else None, fill=None if stack else "tozeroy",
                                         hovertemplate=tip))
            else:
                fig.add_trace(go.Scatter(x=years, y=s, name=nm, mode="lines+markers", line=dict(color=c, width=2.5),
                                         marker=dict(size=6, color="#fff", line=dict(color=c, width=2)),
                                         hovertemplate=tip))
        fig.update_layout(barmode="relative", bargap=.3)
        fig.update_xaxes(dtick=1)
        if PARTIAL_YEAR in years:
            note = f"{PARTIAL_YEAR}년은 {PARTIAL_TXT} 부분연도입니다."
    if fig is not None:
        fig.update_layout(legend=dict(orientation="h", y=1.12), height=400, margin=dict(l=58, r=10, t=30, b=8))
        fig.update_yaxes(tickformat=",.0f")
        st.plotly_chart(style_fig(fig), width="stretch", theme=None, config=PLOT_CFG)
    if trim:
        st.html(f'<div class="caption">{escape(trim)}</div>')
    dropped = [m for m in q["metrics"] if m not in plot_ms and chart != "도넛 그래프"]
    msg = " ".join(x for x in (note, f"{'·'.join(dropped)}은(는) 단위가 달라 그래프에서 빼고 위 지표 카드와 표에만 둡니다."
                               if dropped else "", f"{trim}." if trim else "") if x)
    basis = f"그래프 기준: {'·'.join(plot_ms)} ({unit}) · {escape(q['hs'])} 기준" + (f". {msg}" if msg else "")
    return (style_fig(png_fig) if fig is None else fig), basis


# ── 조회 — 결론형 차트 제목(Datawrapper) ─────────────────────────────────────
# 고른 차트 유형 · 지표 · 국가 · 기간에 맞춰 조회 결과(RDS)에서 문장을 만든다. 부분연도는 변화 비교에서 뺀다.
TIME_CHARTS = ("꺾은선 그래프", "면적 그래프", "누적 막대 그래프", "복합 차트", "히트맵 차트", "덤벨 차트")
SHARE_CHARTS = ("도넛 그래프", "원형 그래프", "트리맵 차트", "맵 차트")


def _bat(word: str) -> bool:
    """마지막 글자에 받침이 있으면 True(한글이 아니면 숫자 · 영문 읽기와 무관하게 받침 없음으로 본다)."""
    c = str(word)[-1:] or " "
    return "가" <= c <= "힣" and (ord(c) - 0xAC00) % 28 != 0


def eun(w: str) -> str:
    return f"{w}{'은' if _bat(w) else '는'}"


def iga(w: str) -> str:
    return f"{w}{'이' if _bat(w) else '가'}"


def query_title(df: pd.DataFrame, q: dict) -> tuple[str, str]:
    """(결론형 제목 HTML, 부제). 제목의 강조 구절은 하나만 <span class="key">."""
    names, chart = q["names"], q["chart"]
    plot_ms = [m for m in q["metrics"] if m in Q_MONEY] or q["metrics"][:1]
    pm = plot_ms[0]
    unit = Q_UNIT[pm]
    y0, y1 = q["years"]
    k = len(names)
    who = escape(names[0]) if k == 1 else f"고른 {k}개국"
    has_part = PARTIAL_YEAR in set(df["연도"])
    sub = (f"{q['area']} · {escape(q['hs'])} · {k}개국 · {y0}~{y1} · 단위 {unit}"
           + (f" · {PARTIAL_YEAR}년은 {PARTIAL_TXT} 부분연도" if has_part else ""))
    by_c = df.groupby("국가")[list(Q_UNIT)].sum()

    def fmt(v: float, m: str = pm) -> str:
        return f"{v:+,.0f}" if m == "무역수지" else f"{v:,.0f}"

    def key(t: str) -> str:
        return f'<span class="key">{t}</span>'

    if chart in SHARE_CHARTS:
        vm = pm if pm != "무역수지" else ("수출액" if q["area"] != "수입" else "수입액")
        sv = by_c[vm][by_c[vm] > 0].sort_values(ascending=False)
        if sv.empty:
            return f"{who} {vm} 비중", sub
        if k == 1:
            return f"{who} {y0}~{y1} {vm} 합계는 {key(f'{sv.iloc[0]:,.0f} {Q_UNIT[vm]}')}", sub
        top = escape(str(sv.index[0]))
        return f"{who}의 {vm} 합계에서 {key(f'{iga(top)} {sv.iloc[0] / sv.sum() * 100:.1f}%')}로 가장 크다", sub
    if chart == "피라미드 그래프":
        e, i = by_c["수출액"].sum(), by_c["수입액"].sum()
        return (f"{who} 합계 수출액 {e:,.0f} · 수입액 {i:,.0f}백만 USD — {key(f'무역수지 {e - i:+,.0f}백만 USD')}"), sub
    if chart in ("버블 차트", "산점도 차트"):
        if k == 1:
            e_txt = f"수출액 {by_c['수출액'].sum():,.0f}백만 USD"
            return f"{who} 수입액 {by_c['수입액'].sum():,.0f} · {key(e_txt)}", sub
        ti, te = escape(str(by_c["수입액"].idxmax())), escape(str(by_c["수출액"].idxmax()))
        return f"수입액이 가장 큰 나라는 {key(ti)}, 수출액이 가장 큰 나라는 {te}", sub
    if chart == "레이더 차트":
        top = escape(str(by_c[pm].idxmax()))
        return f"{pm} 기준으로는 {key(iga(top))} 가장 크다 — 지표마다 가장 큰 나라 = 100", sub
    if chart in TIME_CHARTS:
        full = sorted(int(y) for y in df["연도"].unique() if y != PARTIAL_YEAR)
        tot = df.groupby("연도")[pm].sum()
        if chart == "히트맵 차트":
            cells = df.groupby(["국가", "연도"])[pm].sum()
            (n, y), v = cells.idxmax(), cells.max()
            ytxt = f"{y}년" + (f"({PARTIAL_TXT})" if y == PARTIAL_YEAR else "")
            return f"{iga(pm)} 가장 큰 칸은 {key(f'{escape(str(n))} {ytxt} {fmt(v)} {unit}')}", sub
        if chart == "덤벨 차트" and k > 1 and len(full) >= 2:
            a, b = full[0], full[-1]
            chg = (df[df["연도"] == b].groupby("국가")[pm].sum() - df[df["연도"] == a].groupby("국가")[pm].sum()).dropna()
            if not chg.empty:
                n = chg.abs().idxmax()
                return f"{a}→{b}년 {pm} 변화가 가장 큰 나라는 {key(f'{escape(str(n))} {chg[n]:+,.0f} {unit}')}", sub
        if len(full) >= 2:
            a, b = full[0], full[-1]
            va, vb = tot.get(a, 0.0), tot.get(b, 0.0)
            if pm == "무역수지":
                word = "로 바뀌었다"
            else:
                word = "로 늘었다" if vb > va else ("로 줄었다" if vb < va else "로 같다")
            return f"{who} {pm} 합계는 {a}년 {fmt(va)}에서 {b}년 {key(f'{fmt(vb)} {unit}')}{word}", sub
        if full:
            return f"{who} {full[0]}년 {pm} 합계는 {key(f'{fmt(tot.get(full[0], 0.0))} {unit}')}", sub
        return f"{who} {PARTIAL_YEAR}년({PARTIAL_TXT}) {pm} 합계는 {key(f'{fmt(tot.get(PARTIAL_YEAR, 0.0))} {unit}')}", sub
    # 막대 그래프(국가별 기간 합계)
    if k == 1:
        return f"{who} {y0}~{y1} {pm} 합계는 {key(f'{fmt(by_c[pm].sum())} {unit}')}", sub
    top = by_c[pm].idxmax()
    return f"{who} 중 {eun(pm)} {key(f'{escape(str(top))} {fmt(by_c.loc[top, pm])} {unit}')}로 가장 크다", sub


# ── 조회 — 차트 유형 15종 설명 · CSV 를 차트 모양대로(KOSIS 「데이터 시각화 체험하기」 차트 목록 참고) ──────────
# 분석 조건 설정의 차트 유형 버튼 → 커서를 올리면 그 차트 설명(그림 · 설명 · 용도)이 뜨고, 오른쪽 아래 버튼으로 그 차트 모양의 CSV 를 내려받는다
_CB, _CT, _CP, _CG, _CY, _CO, _CA = "#2b6ef6", "#17c8b5", "#ff9f43", "#dbe4ef", "#ffc36b", "#ffb877", "#9aa5b8"   # 차트 유형 설명 칸의 장식 그림(KOSIS 차트 목록 모양) — 데이터 색(SERIES 고정 순서)과 무관
_AX = f'<path d="M22 12V72H104" fill="none" stroke="{_CA}" stroke-width="1.2"/>'


def _svg(body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 84">{body}</svg>'


# 설명 칸 그림 — KOSIS 차트 목록처럼 파랑 · 청록 · 분홍 · 연회색 네 색으로 모양만 보여 준다
CSV_ICON = {
    "꺾은선 그래프": _AX + f'<polyline points="30,58 50,40 70,55 94,24" fill="none" stroke="{_CB}" stroke-width="3"/>'
                  + "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="{_CB}"/>' for x, y in ((30, 58), (50, 40), (70, 55), (94, 24))),
    "막대 그래프": _AX + f'<rect x="34" y="46" width="12" height="26" fill="{_CP}"/><rect x="56" y="34" width="12" height="38" fill="{_CT}"/>'
                f'<rect x="78" y="20" width="12" height="52" fill="{_CB}"/>',
    "누적 막대 그래프": f'<rect x="30" y="40" width="26" height="34" fill="{_CB}"/><rect x="30" y="20" width="26" height="20" fill="{_CT}"/>'
                  f'<rect x="30" y="12" width="26" height="8" fill="{_CP}"/><rect x="64" y="46" width="26" height="28" fill="{_CB}"/>'
                  f'<rect x="64" y="18" width="26" height="28" fill="{_CT}"/><rect x="64" y="12" width="26" height="6" fill="{_CP}"/>',
    "피라미드 그래프": f'<line x1="60" y1="8" x2="60" y2="78" stroke="{_CA}" stroke-width="1.2"/>'
                 + "".join(f'<rect x="{60 - a}" y="{y}" width="{a}" height="9" fill="{_CB}"/><rect x="60" y="{y}" width="{b}" height="9" fill="{_CT}"/>'
                           for y, a, b in ((14, 12, 18), (28, 30, 34), (42, 24, 26), (56, 20, 18))),
    "면적 그래프": _AX + f'<path d="M23 44L38 30L50 46L66 22L80 34L94 20L104 36V72H23Z" fill="{_CT}"/>'
                f'<path d="M23 56L38 50L50 58L66 44L80 52L94 46L104 54V72H23Z" fill="{_CB}"/>',
    "원형 그래프": f'<circle cx="60" cy="44" r="30" fill="{_CG}"/><path d="M60 44L60 14A30 30 0 0 1 89.6 39Z" fill="{_CT}"/>'
                f'<path d="M60 44L37 25A30 30 0 0 1 60 14Z" fill="{_CP}"/>',
    "도넛 그래프": f'<circle cx="60" cy="42" r="26" fill="none" stroke="{_CG}" stroke-width="10"/>'
                f'<circle cx="60" cy="42" r="26" fill="none" stroke="{_CT}" stroke-width="10" stroke-dasharray="60 200" transform="rotate(-90 60 42)"/>'
                f'<circle cx="60" cy="42" r="26" fill="none" stroke="{_CP}" stroke-width="10" stroke-dasharray="30 200" stroke-dashoffset="-110" transform="rotate(-90 60 42)"/>'
                f'<circle cx="60" cy="42" r="26" fill="none" stroke="{_CB}" stroke-width="10" stroke-dasharray="26 200" stroke-dashoffset="-140" transform="rotate(-90 60 42)"/>',
    "버블 차트": f'<path d="M26 10H100V78H26ZM50.7 10V78M75.3 10V78M26 32.7H100M26 55.3H100" fill="none" stroke="{_CA}" stroke-width="1"/>'
              f'<circle cx="50" cy="31" r="15" fill="{_CP}"/><circle cx="88" cy="22" r="6" fill="{_CG}"/>'
              f'<circle cx="80" cy="60" r="10" fill="{_CB}"/><circle cx="37" cy="66" r="6" fill="{_CT}"/>',
    "복합 차트": _AX + f'<rect x="32" y="48" width="12" height="24" fill="{_CP}"/><rect x="54" y="52" width="12" height="20" fill="{_CT}"/>'
              f'<rect x="76" y="38" width="12" height="34" fill="{_CG}"/>'
              f'<polyline points="38,32 60,20 82,26" fill="none" stroke="{_CB}" stroke-width="2.4"/>'
              + "".join(f'<circle cx="{x}" cy="{y}" r="3.4" fill="{_CB}"/>' for x, y in ((38, 32), (60, 20), (82, 26))),
    "레이더 차트": "".join(f'<polygon points="{" ".join(f"{60 + r * math.sin(a * 2 * math.pi / 5):.1f},{44 - r * math.cos(a * 2 * math.pi / 5):.1f}" for a in range(5))}" '
                        f'fill="none" stroke="{_CA}" stroke-width="1"/>' for r in (34, 24, 14, 6))
                + f'<polygon points="60,18 88,36 76,66 46,64 38,38" fill="{_CB}" fill-opacity=".18" stroke="{_CB}" stroke-width="2"/>',
    "맵 차트": f'<circle cx="60" cy="44" r="32" fill="#eef2f8" stroke="{_CA}" stroke-width="1.2"/>'
            f'<ellipse cx="60" cy="44" rx="14" ry="32" fill="none" stroke="{_CA}" stroke-width=".8"/>'
            f'<path d="M28 44H92M32 28H88M32 60H88" stroke="{_CA}" stroke-width=".8"/>'
            f'<path d="M38 22Q48 16 54 24T50 40Q44 44 40 36Z" fill="{_CT}"/><path d="M62 30Q76 24 84 34T76 50Q66 52 64 42Z" fill="{_CB}"/>'
            f'<path d="M48 52Q58 50 60 60T52 72Q44 66 48 52Z" fill="{_CP}"/>',
    "히트맵 차트": "".join(f'<rect x="{30 + c * 12.4}" y="{12 + r * 12.4}" width="11.4" height="11.4" '
                        f'fill="{(_CY, _CO, "#ff5b6e", _CO, _CY)[(r * 3 + c * 2) % 5]}"/>' for r in range(5) for c in range(5)),
    "트리맵 차트": f'<rect x="22" y="12" width="44" height="62" fill="{_CB}"/><rect x="68" y="12" width="32" height="30" fill="{_CT}"/>'
                f'<rect x="68" y="44" width="18" height="30" fill="{_CP}"/><rect x="88" y="44" width="12" height="30" fill="{_CG}"/>',
    "산점도 차트": _AX + "".join(f'<circle cx="{x}" cy="{y}" r="3.4" fill="{c}"/>' for x, y, c in (
        (32, 62, _CB), (38, 56, _CT), (46, 58, _CB), (50, 48, _CP), (58, 44, _CB), (62, 50, _CT), (70, 36, _CB),
        (76, 40, _CP), (82, 28, _CT), (90, 26, _CB), (96, 18, _CB), (42, 40, _CG), (86, 52, _CG))),
    "덤벨 차트": "".join(f'<line x1="{a}" y1="{y}" x2="{b}" y2="{y}" stroke="{_CG}" stroke-width="4"/>'
                      f'<circle cx="{a}" cy="{y}" r="5" fill="{_CT}"/><circle cx="{b}" cy="{y}" r="5" fill="{_CB}"/>'
                      for y, a, b in ((18, 34, 70), (34, 46, 96), (50, 30, 58), (66, 54, 88))),
}

# 차트 이름: (설명, 용도, 중요 포인트, 데이터 모양)
CSV_CHARTS = {
    "꺾은선 그래프": ("시간에 따라 값이 어떻게 바뀌는지 점을 선으로 이어 보여 줍니다.",
                 ["연도별 증감 추세 파악", "여러 국가의 흐름 비교", "변곡점 · 급변 시점 확인"],
                 ["시간 흐름 강조", "추세 비교 용이", "변화 폭 한눈에"], "행 = 연도 · 열 = 국가"),
    "막대 그래프": ("항목끼리의 크기를 막대 길이로 비교합니다.",
                ["국가별 규모 비교", "여러 지표를 나란히 비교", "순위 확인"],
                ["크기 비교 직관적", "항목 수가 많아도 읽기 쉬움", "지표를 묶어 비교"], "행 = 국가 · 열 = 지표(기간 합계)"),
    "누적 막대 그래프": ("막대 하나에 여러 항목을 쌓아 전체와 부분을 함께 보여 줍니다.",
                  ["연도별 전체 규모와 국가별 몫", "구성의 변화 추적", "합계 추이 확인"],
                  ["전체 · 부분 동시 표현", "구성비 변화 파악", "합계 비교"], "행 = 연도 · 열 = 국가 + 합계"),
    "피라미드 그래프": ("두 집단의 값을 가운데 축을 기준으로 좌우에 마주 놓고 비교합니다.",
                  ["수출과 수입을 마주 비교", "국가별 교역 균형 확인", "대칭 · 비대칭 파악"],
                  ["두 값 대칭 비교", "불균형 한눈에", "항목별 방향 확인"], "행 = 국가 · 왼쪽 = 수출액 · 오른쪽 = 수입액"),
    "면적 그래프": ("꺾은선 아래를 색으로 채워 양의 흐름과 누적 규모를 강조합니다.",
                ["누적 규모 변화 표현", "국가별 기여 흐름", "기간 전체의 양 강조"],
                ["양의 크기 강조", "누적 흐름 표현", "추세 · 규모 동시 파악"], "행 = 연도 · 열 = 국가"),
    "원형 그래프": ("전체를 100%로 두고 각 항목이 차지하는 비중을 부채꼴로 나눕니다.",
                ["국가별 점유율 표현", "상위 국가 집중도 확인", "구성비 비교"],
                ["비중 직관적 표현", "전체 대비 부분", "항목 5~7개가 적당"], "행 = 국가 · 값 · 비중(%)"),
    "도넛 그래프": ("가운데를 비운 원형 그래프로, 가운데에 합계를 적을 수 있습니다.",
                ["점유율 + 합계 함께 표현", "구성비 비교", "대시보드 요약 카드"],
                ["비중과 합계 동시 표현", "공간 효율적", "구성비 비교 용이"], "행 = 국가 · 값 · 비중(%)"),
    "버블 차트": ("X축과 Y축으로 2개 변수, 버블의 크기로 제3변수를 표현하는 3차원적 그래프입니다.",
              ["세 변수 간 관계 분석", "데이터 분포 및 집중도 표현 용이", "3차원 데이터 시각화 가능"],
              ["세 변수 한눈에 표현 가능", "데이터 간 상대적 비교 용이", "패턴과 분포 시각화"],
              "행 = 국가 · X = 수입액 · Y = 수출액 · 크기 = 수입중량"),
    "복합 차트": ("막대와 선을 한 그림에 겹쳐 성격이 다른 두 값을 함께 보여 줍니다.",
              ["규모(막대)와 차이(선) 동시 표현", "수출입과 무역수지 비교", "두 지표 관계 파악"],
              ["서로 다른 지표 결합", "정보 밀도 높음", "관계 · 추세 동시 파악"], "행 = 연도 · 막대 = 수출액·수입액 · 선 = 무역수지"),
    "레이더 차트": ("여러 지표를 방사형 축에 놓고 이어 만든 모양으로 대상을 비교합니다.",
                ["국가별 교역 특성 비교", "강점 · 약점 지표 확인", "다차원 프로필 표현"],
                ["여러 지표 동시 비교", "모양으로 특성 파악", "지표마다 100 기준 환산"], "행 = 국가 · 열 = 지표(지표별 최대 = 100)"),
    "맵 차트": ("지도 위 위치에 값을 표시해 지역별 분포를 보여 줍니다.",
             ["국가별 분포를 지도로 표현", "지역 쏠림 확인", "지리적 패턴 파악"],
             ["위치 정보 직관적", "지역 간 비교", "분포 패턴 확인"], "행 = 국가 · 국가코드 · 위도 · 경도 · 값"),
    "히트맵 차트": ("두 분류가 만나는 칸의 크기를 색의 진하기로 표현합니다.",
                ["국가 × 연도 값 비교", "집중 시기 · 국가 파악", "이상값 확인"],
                ["많은 값을 한 판에", "패턴 · 집중도 강조", "색으로 크기 비교"], "행 = 국가 · 열 = 연도"),
    "트리맵 차트": ("사각형의 넓이로 전체에서 각 항목이 차지하는 비중을 나눠 보여 줍니다.",
                ["국가별 비중 표현", "항목이 많을 때의 구성비", "상위 집중도 확인"],
                ["공간 효율적", "많은 항목도 표현", "비중 직관적"], "행 = 국가 · 값 · 비중(%)"),
    "산점도 차트": ("두 변수의 값을 점으로 찍어 둘 사이의 관계를 봅니다.",
                ["두 변수 상관관계 확인", "군집 · 이상값 파악", "분포 확인"],
                ["관계 · 상관 파악", "이상값 발견", "점 하나 = 국가 × 연도"], "행 = 국가 × 연도 · X = 수입액 · Y = 수출액"),
    "덤벨 차트": ("시작과 끝 두 시점의 값을 선으로 이어 변화 폭을 보여 줍니다.",
              ["기간 전후 비교", "국가별 변화 폭 순위", "증가 · 감소 방향 확인"],
              ["두 시점 차이 강조", "변화 방향 명확", "항목 간 비교 용이"], "행 = 국가 · 시작 연도 값 · 끝 연도 값 · 변화"),
}
def _csv_css() -> str:
    return """<style>
/* 차트 유형 버튼 15개 — 아이콘 위 · 이름 아래로 쌓아 가운데 정렬(이름 길이가 달라도 줄이 맞는다), 고른 것은 파란 테두리 */
.st-key-qs_ct_grid{position:relative;gap:6px}
.st-key-qs_ct_grid [data-testid="stHorizontalBlock"]{gap:6px;margin-bottom:0 !important}
.st-key-qs_ct_grid [data-testid="stColumn"]{position:static}
.st-key-qs_ct_grid button{height:66px;padding:6px 4px;border-radius:8px;border:1px solid var(--line);background:#fff;color:var(--muted)}
.st-key-qs_ct_grid button > div,.st-key-qs_ct_grid button > div > span{width:100%;justify-content:center}
.st-key-qs_ct_grid button > div > span{flex-direction:column;align-items:center;gap:5px}
.st-key-qs_ct_grid button > div > span > span:first-child{margin:0 !important}
/* 아이콘 · 이름은 평소 회색(잠긴 것처럼 보이지 않게 대비 4.5:1 이상), 커서를 올리거나 고른 버튼만 파란색 */
.st-key-qs_ct_grid button [data-testid="stIconMaterial"]{font-size:24.5px;width:22px;height:22px;color:inherit !important}
.st-key-qs_ct_grid button [data-testid="stMarkdownContainer"]{text-align:center}
.st-key-qs_ct_grid button p{font-size:14px;line-height:1.2;white-space:nowrap;color:inherit}
.st-key-qs_ct_grid button:hover{border-color:var(--accent);color:var(--accent) !important}
.st-key-qs_ct_grid button[data-testid="stBaseButton-primary"]{background:rgba(43,110,246,.08);border:1.5px solid var(--accent);color:var(--accent) !important}
.st-key-qs_ct_grid button[data-testid="stBaseButton-primary"] p{font-weight:700}
/* 커서를 올린 버튼의 설명 칸 — 버튼 묶음 바로 위로 떠서 조건 칸을 덮는다. 커서를 받지 않아 깜빡이지 않는다 */
.st-key-qs_ct_grid [data-testid="stLayoutWrapper"]:has(> div[class*="st-key-qs_pop_"]){position:absolute;inset:0;pointer-events:none}
.st-key-qs_ct_grid div[class*="st-key-qs_pop_"]{position:absolute;left:0;bottom:calc(100% + 10px);width:100% !important;
  max-width:none !important;z-index:60;pointer-events:none;opacity:0;visibility:hidden;transform:translateY(6px);
  transition:opacity .16s,transform .16s,visibility .16s}
.st-key-qs_ct_grid [data-testid="stColumn"]:has(button:hover) div[class*="st-key-qs_pop_"]{opacity:1;visibility:visible;transform:none}
.csv-pop{background:#fff;border:1px solid #c9d7ea;border-radius:10px;padding:14px 18px 18px;box-shadow:0 4px 14px rgba(15,31,58,.10)}
.csv-h{font-size:19px;font-weight:700;color:#1d4ed8}
.csv-crumb{font-size:13.5px;color:#4b515d}.csv-crumb b{color:#1d2a44}
.csv-top{display:grid;grid-template-columns:150px 1fr;gap:14px}
.csv-fig{border:1.5px solid #6b7280;border-radius:12px;background:#fff;display:flex;align-items:center;justify-content:center;min-height:150px}
.csv-desc{background:#f2f2f3;border-radius:12px;padding:16px 20px;font-size:14.5px;color:#30343c;line-height:1.65}
.csv-desc hr{border:0;border-top:1px solid #c8cbd2;margin:12px 0}
.csv-desc h5{font-size:17px;font-weight:800;margin:0 0 6px;color:#1d2330}
.csv-desc .shape{display:inline-block;margin-top:10px;padding:3px 12px;border-radius:14px;background:#fff;border:1px solid #d6dbe6;
  font-weight:700;color:#3d4a6b;font-size:13.5px}
</style>"""


def csv_shape(chart: str, df: pd.DataFrame, q: dict) -> tuple[pd.DataFrame, str]:
    """고른 차트가 바로 읽을 수 있는 모양으로 조회 결과를 다시 짠다. (표, 값 설명)"""
    names = q["names"]
    pm = ([m for m in q["metrics"] if m in Q_MONEY] or q["metrics"][:1])[0]
    by_c = df.groupby("국가", sort=False)[list(Q_UNIT)].sum().reindex(names)
    wide = df.pivot_table(index="연도", columns="국가", values=pm, aggfunc="sum").reindex(columns=names)
    col = lambda m: f"{m}({Q_UNIT[m]})"
    note = f"값 = {col(pm)}"
    if chart in ("꺾은선 그래프", "면적 그래프"):
        out = wide.reset_index()
    elif chart == "막대 그래프":
        out = by_c[q["metrics"]].rename(columns=col).reset_index()
        note = f"값 = {q['years'][0]}~{q['years'][1]} 합계"
    elif chart == "누적 막대 그래프":
        out = wide.assign(합계=wide.sum(axis=1)).reset_index()
    elif chart == "피라미드 그래프":
        out = by_c[["수출액", "수입액"]].rename(columns=col).reset_index()
        note = "단위: 백만 USD · 기간 합계"
    elif chart in ("원형 그래프", "도넛 그래프", "트리맵 차트", "맵 차트"):
        vm = pm if pm != "무역수지" else ("수출액" if q["area"] != "수입" else "수입액")   # 음수는 비중으로 나눌 수 없다
        s = by_c[vm]
        out = pd.DataFrame({"국가": s.index, col(vm): s.values})
        if chart == "맵 차트":
            out.insert(1, "국가코드(ISO2)", [CODE.get(n, "") for n in s.index])
            out.insert(2, "위도", [WHERE.get(n, (None, None))[0] for n in s.index])
            out.insert(3, "경도", [WHERE.get(n, (None, None))[1] for n in s.index])
        else:
            out["비중(%)"] = (s / s.sum() * 100).round(1).values
        note = f"값 = {col(vm)}" + (" · 무역수지는 음수가 있어 대신 씁니다" if vm != pm else "")
    elif chart == "버블 차트":
        out = by_c[["수입액", "수출액", "수입중량"]].reset_index().rename(
            columns={"수입액": "X_수입액(백만 USD)", "수출액": "Y_수출액(백만 USD)", "수입중량": "크기_수입중량(톤)"})
        note = f"X · Y · 크기 세 열 · {q['years'][0]}~{q['years'][1]} 합계"
    elif chart == "복합 차트":
        out = df.groupby("연도")[["수출액", "수입액", "무역수지"]].sum().reset_index().rename(
            columns={"수출액": "막대_수출액(백만 USD)", "수입액": "막대_수입액(백만 USD)", "무역수지": "선_무역수지(백만 USD)"})
        note = "선택 국가 합계"
    elif chart == "레이더 차트":
        rm = [m for m in Q_UNIT if m != "무역수지"]             # 음수가 있는 무역수지는 방사형 축에 올리지 않는다
        out = (by_c[rm] / by_c[rm].max().replace(0, 1) * 100).round(1).reset_index()
        note = "지표마다 가장 큰 국가 = 100 으로 환산(단위가 달라서)"
    elif chart == "히트맵 차트":
        out = wide.T.rename_axis("국가").reset_index()
        out.columns = [str(c) for c in out.columns]
    elif chart == "산점도 차트":
        out = df[["국가", "연도", "수입액", "수출액"]].rename(
            columns={"수입액": "X_수입액(백만 USD)", "수출액": "Y_수출액(백만 USD)"})
        note = "점 하나 = 국가 × 연도"
    else:                                   # 덤벨 차트
        ys = sorted(df["연도"].unique())
        a, b = wide.loc[ys[0]], wide.loc[ys[-1]]
        out = pd.DataFrame({"국가": names, f"{ys[0]}년": a.values, f"{ys[-1]}년": b.values,
                            "변화": (b - a).values, "변화율(%)": ((b - a) / a.abs().replace(0, float("nan")) * 100).round(1).values})
        note = f"값 = {col(pm)} · 시작 {ys[0]}년 → 끝 {ys[-1]}년"
    if PARTIAL_YEAR in set(df["연도"]) and chart not in ("피라미드 그래프", "막대 그래프"):
        note += f" · {PARTIAL_YEAR}년은 {PARTIAL_TXT} 부분연도"
    return out.round(1), note


def csv_preview(chart: str, out: pd.DataFrame) -> go.Figure:
    """CSV 모양(out) 만 가지고 그 차트를 그린다 — 조회 결과 차트와 내려받는 CSV 가 같은 표에서 나온다."""
    fig = go.Figure()
    first = out.columns[0]
    pal = lambda i: (Q_PALETTE[i] if i < len(Q_PALETTE) else ETC)
    rows_c = [str(n) for n in out[first]]
    is_ctry = lambda ns: bool(ns) and all(n in CODE or n.startswith("기타") for n in ns)
    cmap = ctry_colors(rows_c) if is_ctry(rows_c) else {}                   # 행 = 국가(원형 · 도넛 · 트리맵 · 버블)
    if chart in ("꺾은선 그래프", "면적 그래프", "누적 막대 그래프"):
        series = [c for c in out.columns[1:] if c != "합계"]
        stack = chart == "면적 그래프" and bool((out[series] >= 0).all().all())
        scol = ctry_colors(series) if is_ctry(series) else {}                 # 열 = 국가면 국가 색
        pal_s = lambda i: scol.get(series[i]) or pal(i)
        for i, c in enumerate(series):
            if chart == "누적 막대 그래프":
                fig.add_trace(go.Bar(x=out[first], y=out[c], name=c, marker_color=pal_s(i)))
            else:
                fig.add_trace(go.Scatter(x=out[first], y=out[c], name=c, line=dict(color=pal_s(i), width=2.2),
                                         mode="lines" if chart == "면적 그래프" else "lines+markers",
                                         stackgroup="a" if stack else None,
                                         fill=None if stack or chart == "꺾은선 그래프" else "tozeroy"))
        fig.update_layout(barmode="stack")
        fig.update_xaxes(dtick=1)
    elif chart == "막대 그래프":
        for i, c in enumerate(out.columns[1:]):
            fig.add_trace(go.Bar(x=out[first], y=out[c], name=c, marker_color=Q_METRIC_COLOR.get(c.split("(")[0], pal(i))))
    elif chart == "피라미드 그래프":
        l, r = out.columns[1:3]
        fig.add_trace(go.Bar(y=out[first], x=-out[l], name=l, orientation="h", marker_color=_CB,
                             customdata=out[l], hovertemplate="%{y}<br>%{customdata:,.1f}<extra>" + l + "</extra>"))
        fig.add_trace(go.Bar(y=out[first], x=out[r], name=r, orientation="h", marker_color=_CT))
        fig.update_layout(barmode="relative", bargap=.25)
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(tickformat=",.0f")
    elif chart in ("원형 그래프", "도넛 그래프"):
        fig.add_trace(go.Pie(labels=out[first], values=out.iloc[:, 1], hole=.55 if chart == "도넛 그래프" else 0, sort=False,
                             marker=dict(colors=[cmap.get(n) or pal(i) for i, n in enumerate(rows_c)], line=dict(color="#fff", width=1.5)),
                             textinfo="percent", textposition="inside", texttemplate="%{percent:.1%}"))   # 소수 1자리로 통일(33% · 9.91% 섞임)
    elif chart == "트리맵 차트":
        fig.add_trace(go.Treemap(labels=out[first], parents=[""] * len(out), values=out.iloc[:, 1],
                                 marker=dict(colors=[cmap.get(n) or pal(i) for i, n in enumerate(rows_c)]), textinfo="label+percent root"))
    elif chart == "맵 차트":
        v = out.iloc[:, 4]
        fig.add_trace(go.Scattergeo(lat=out["위도"], lon=out["경도"], text=out[first], mode="markers",
                                    marker=dict(size=v, sizemode="area", sizeref=2 * max(v.max(), 1) / 40 ** 2, sizemin=4,
                                                color=_CB, opacity=.7, line=dict(color="#fff", width=1)),
                                    hovertemplate="%{text}<br>%{marker.size:,.1f}<extra></extra>"))
        fig.update_geos(showcountries=True, countrycolor="#c9d3e6", landcolor="#eef2f8", showocean=False,
                        projection_type="natural earth", showframe=False, bgcolor="rgba(0,0,0,0)")
    elif chart == "버블 차트":
        x, y, s = out.columns[1:4]
        fig.add_trace(go.Scatter(x=out[x], y=out[y], text=out[first], mode="markers",
                                 marker=dict(size=out[s], sizemode="area", sizeref=2 * max(out[s].max(), 1) / 46 ** 2, sizemin=5,
                                             color=[cmap.get(n) or pal(i) for i, n in enumerate(rows_c)], opacity=.8, line=dict(color="#fff", width=1.2)),
                                 hovertemplate="%{text}<br>X %{x:,.1f} · Y %{y:,.1f}<extra></extra>"))
        pad = lambda v: [float(v.min()) - (float(v.max() - v.min()) or 1) * .15, float(v.max()) + (float(v.max() - v.min()) or 1) * .18]
        fig.update_xaxes(title=x, range=pad(out[x]))          # 가장자리 버블이 잘리지 않게 축을 넉넉히
        fig.update_yaxes(title=y, range=pad(out[y]))
    elif chart == "복합 차트":
        for i, c in enumerate(out.columns[1:3]):
            fig.add_trace(go.Bar(x=out[first], y=out[c], name=c, marker_color=(_CT, _CB)[i]))
        c = out.columns[3]
        fig.add_trace(go.Scatter(x=out[first], y=out[c], name=c, mode="lines+markers", line=dict(color=_CP, width=2.5)))
        fig.update_xaxes(dtick=1)
    elif chart == "레이더 차트":
        axes = list(out.columns[1:])
        for i, (_, r) in enumerate(out.head(6).iterrows()):
            fig.add_trace(go.Scatterpolar(r=[*r[axes], r[axes[0]]], theta=[*axes, axes[0]], name=r[first], fill="toself",
                                          line=dict(color=pal(i), width=1.8), opacity=.55))
        fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], gridcolor="#e2e8f2", tickfont=dict(size=10)),
                                     angularaxis=dict(gridcolor="#e2e8f2")))
    elif chart == "히트맵 차트":
        fig.add_trace(go.Heatmap(z=out.iloc[:, 1:].values, x=list(out.columns[1:]), y=out[first],
                                 colorscale=[[0, "#eff6ff"], [.5, "#60a5fa"], [1, "#1e3a8a"]], xgap=2, ygap=2))
        fig.update_yaxes(autorange="reversed")
    elif chart == "산점도 차트":
        x, y = out.columns[2:4]
        for i, (n, g) in enumerate(out.groupby(first, sort=False)):
            fig.add_trace(go.Scatter(x=g[x], y=g[y], name=n, mode="markers", marker=dict(size=8, color=pal(i), opacity=.8)))
        fig.update_xaxes(title=x)
        fig.update_yaxes(title=y)
    else:                                   # 덤벨 차트
        a, b = out.columns[1:3]
        for _, r in out.iterrows():
            fig.add_trace(go.Scatter(x=[r[a], r[b]], y=[r[first]] * 2, mode="lines", line=dict(color=_CG, width=5),
                                     showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=out[a], y=out[first], name=a, mode="markers", marker=dict(size=12, color=_CT)))
        fig.add_trace(go.Scatter(x=out[b], y=out[first], name=b, mode="markers", marker=dict(size=12, color=_CB)))
        fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.14, font=dict(size=11)))
    style_fig(fig)
    fig.update_xaxes(automargin=True, tickformat=",.0f" if chart not in ("꺾은선 그래프", "면적 그래프", "누적 막대 그래프",
                                                                          "복합 차트", "히트맵 차트", "막대 그래프") else None)
    return fig


def csv_info(nm: str, subject: str = "국가", shape: str | None = None) -> str:
    """차트 설명 칸 — 차트 목록 > 이름 · 그림 · 설명 · 용도 · CSV 모양. 차트 유형 버튼에 커서를 올리면 뜬다.
    군수품 · 국산화개발 화면은 용도 문구의 「국가」를 subject(분류 · FSC)로 바꾸고, CSV 모양은 shape 로 바꿔 쓴다."""
    desc, uses, _, shape_txt = CSV_CHARTS[nm]
    uses = [u.replace("국가", subject) for u in uses]
    shape_txt = shape or shape_txt
    return (f'<div class="csv-pop"><div class="csv-crumb">차트 목록 &gt; <b>{nm}</b></div>'
            f'<div class="csv-h" style="border:0;margin:8px 0 10px;padding:0">{nm}</div>'
            f'<div class="csv-top"><div class="csv-fig">{_svg_img(_svg(CSV_ICON[nm]), 150, 105)}</div>'
            f'<div class="csv-desc">{desc}<hr><h5>용도</h5>{"<br>".join(f"- {u}" for u in uses)}'
            f'<br><span class="shape">CSV 데이터 모양 · {shape_txt}</span></div></div></div>')


# ── 조회 — 결과 표: 연도별 통계표(KOSIS 통계표 모양 · 행 = 국가, 열 = 시점(연도) 아래 항목(지표)) ──────────
STAT_CSS = """<style>
/* 남색 머리(흰 글씨) · 옅은 줄무늬 · 국가 열 고정 · 가로/세로 스크롤 */
.st-tbl{border-collapse:collapse;font-size:14px;min-width:100%}
.st-scroll{max-height:405px;overflow:auto;border:1px solid #e1e9f3;border-radius:8px;background:#fff}
.st-tbl th{position:sticky;top:0;z-index:2;background:#1b2f66;color:#fff;font-weight:600;padding:6px 10px;text-align:center;
  border-right:1px solid #33488a;border-bottom:1px solid #33488a;white-space:nowrap}
.st-tbl th small{font-weight:500;opacity:.85}
.st-tbl thead tr:nth-child(2) th{top:31px;background:#2a4285;font-weight:500;font-size:13px}
.st-tbl td{padding:6px 10px;border-bottom:1px solid #edf2f8;border-right:1px solid #f2f6fb;text-align:right;color:#0f1f3a;white-space:nowrap;font-variant-numeric:tabular-nums}
.st-tbl td:first-child,.st-tbl th:first-child{position:sticky;left:0;z-index:1;text-align:left}
.st-tbl th:first-child{z-index:3}
.st-tbl td:first-child{background:#fff;font-weight:700}
.st-tbl tr:nth-child(even) td{background:#fafcff}
.st-tbl td.neg{color:#0f1f3a}
.st-tbl .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px;vertical-align:-1px}
.st-note{font-size:13px;color:#6b7a99;margin-top:6px}
</style>"""


def _stat_cell(v: float, m: str) -> str:
    txt = f"{v:,.0f}" if Q_UNIT[m] == "건" else f"{v:,.1f}"          # 건수는 소수점 없이
    return f'<td class="neg">{txt}</td>' if v < 0 else f"<td>{txt}</td>"


def stat_table(df: pd.DataFrame, q: dict) -> None:
    """분석 조건 그대로 — 고른 국가(행) × 기간 안의 연도(시점) × 고른 지표(항목). 국가 색은 차트와 같다."""
    names, ms = q["names"], q["metrics"]
    years = sorted(df["연도"].unique())
    color = ctry_colors(names)
    piv = df.pivot_table(index="국가", columns="연도", values=ms, aggfunc="sum").reindex(names)
    yl = lambda y: f"{y}<small> ({PARTIAL_TXT})</small>" if y == PARTIAL_YEAR else str(y)
    head1 = "".join(f'<th colspan="{len(ms)}">{yl(y)}</th>' for y in years)
    head2 = "".join(f"<th>{m}<br><small>{Q_UNIT[m]}</small></th>" for _ in years for m in ms)
    body = "".join(f'<tr><td><span class="dot" style="background:{color[n]}"></span>{escape(str(n))}</td>'
                   + "".join(_stat_cell(float(piv.loc[n, (m, y)]), m) for y in years for m in ms) + "</tr>"
                   for n in names)
    st.html(STAT_CSS + f'<div class="st-scroll"><table class="st-tbl"><thead><tr><th rowspan="2">국가</th>{head1}</tr>'
            f'<tr>{head2}</tr></thead><tbody>{body}</tbody></table></div>'
            f'<div class="st-note">통계표 · 국가 {len(names)}개 × 시점 {len(years)}개({years[0]}~{years[-1]}) × 항목 {len(ms)}개 · '
            f'{q["area"]} · {escape(str(q["hs"]))} · 가로로 넘겨 보세요'
            + (f" · {PARTIAL_YEAR}년은 {PARTIAL_TXT} 부분연도" if PARTIAL_YEAR in years else "") + "</div>")



def _dl_area(slots: list, map_file: str = "") -> None:
    """결과 카드 맨 아래 내려받기 줄 — 탭 하나당 칸 하나(dl_t0 · dl_t1 · dl_t2). slots[i] = i 번째 탭의
    (출처 문구 또는 None, 단추를 그리는 함수). 출처가 있으면 「? 출처」 원은 왼쪽 · 단추는 오른쪽(「?  ···  내려받기」).
    단추 이름 = 「탭 이름 + 형식」(차트 · 지도 = PNG 이미지, 표 = CSV) — 고른 차트 유형은 파일 이름에만 넣는다.
    지금 고른 탭(aria-selected)의 칸만 보인다(static/components.css). 탭 칸 바깥 · 카드 안의 평범한 줄이라 내용을 덮지 않는다."""
    with st.container(key="res_dl"):
        for i, (src, draw) in enumerate(slots):
            with st.container(key=f"dl_t{i}", horizontal=True, vertical_alignment="center",
                              horizontal_alignment="distribute" if src else "right"):
                if src:
                    chart_source(src)
                draw()
    with st.container(key="imgdl_js"):                     # PNG 단추(dlbtn_png · dlbtn_map) 클릭 처리(static/img_dl.js)
        components.html(f"<script>window.parent.__kdMapFile = {json.dumps(map_file + '.png')};</script>"
                        "<script>" + (STATIC_DIR / "img_dl.js").read_text(encoding="utf-8") + "</script>", height=0)


def _png_dl(label: str, **png) -> None:
    """차트 PNG — CSV 단추와 똑같은 Streamlit primary 단추(다운로드 아이콘). 누르면 페이지를 다시 돌리지 않고
    숨겨 둔 그림 칸(png_button trigger)이 넓힌 폭 그대로 PNG 를 만든다(static/img_dl.js 가 클릭을 가로챈다)."""
    st.button(label, icon=":material/download:", type="primary", key="dlbtn_png")
    with st.container(key="png_js"):
        png_button(**png, trigger="dlbtn_png")


def _map_png_button() -> None:
    """지도 탭 PNG — CSV 단추와 같은 Streamlit primary 단추. 지도는 iframe 그림이라 지금 보이는 지도 칸을 그대로 찍는다
    (파일 이름은 _dl_area(map_file=…), 클릭 처리는 static/img_dl.js)."""
    st.button("지도 PNG 이미지 내려받기", icon=":material/download:", type="primary", key="dlbtn_map")


def _png_width(fig) -> int:
    """PNG 그림 폭 — 넓힌 막대 차트(wide_chart)면 그 폭 그대로(막대 · x축 라벨이 잘리지 않게), 아니면 1100."""
    return max(1100, int(fig.layout.width or 0))


def wide_chart(fig, n_bars: int, height: int = 400) -> int:
    """막대가 WIDE_MIN 개를 넘는 분포 차트 — 그림 폭을 막대 수에 비례해 넓혀 iframe 안에 그리고 가로로 스크롤한다
    (static/wide_chart.html). st.plotly_chart 는 칸 폭을 넘지 못해 막대가 다시 찌그러지기 때문. 넓힌 폭을 돌려준다."""
    width = int(max(WIDE_BASE, n_bars / WIDE_MIN * WIDE_BASE))
    fig.update_layout(width=width, height=height)
    html = ((STATIC_DIR / "wide_chart.html").read_text(encoding="utf-8")
            .replace("__FONTLINK__", _FONT_LINK).replace("__FIG__", fig.to_json())
            .replace("__W__", str(width)).replace("__H__", str(height)))
    components.html(html, height=height + 18, scrolling=False)   # + 가로 스크롤바 자리
    return width


def query_result(q: dict, y0: int, y1: int) -> None:
    """조회 결과 카드 안 — 지표 카드 · 차트/지도/표 탭 · 탭별 내려받기 단추(차트 · 지도 = PNG, 결과 표 = CSV)."""
    # 조건을 바꾸면 여기가 다시 계산된다 — 그동안 작은 지구본이 돈다.
    # 로딩 지구본은 실제 DB 조회 시간 동안만 보인다.
    with globe_loading("조회 결과를 계산하는 중"):
        df = trade_frame(q["names"], y0, y1, q["unit"], q["items"])
    if df.empty:
        st.info("이 조건에는 수출입 실적이 없습니다(실제 0). 기간 · 품목군 · 국가를 바꿔 보세요.")
        return
    tot = df[list(Q_UNIT)].sum()
    icon = {m: ic for m, _, ic, _ in Q_METRICS}
    cards = "".join(
        kpi(m, f"{tot[m]:+,.0f}" if m == "무역수지" else f"{tot[m]:,.0f}", Q_UNIT[m],
            f"{len(q['names'])}개국 · {y0}~{y1} 합계" + (f" ({PARTIAL_YEAR}년은 {PARTIAL_TXT})" if y1 >= PARTIAL_YEAR else ""),
            tag="참고값" if "중량" in m else "", icon=icon[m]) for m in q["metrics"])
    st.html(f'<div class="kpis q" style="grid-template-columns:repeat({min(len(q["metrics"]), 3)},minmax(0,1fr))">{cards}</div>')

    src_q = f"관세청 · 품목별 국가별 수출입실적(15100475) · 자료 기간 {STAMP['period']}"
    t_chart, t_map, t_tbl = st.tabs(["차트", "국가별 분포 지도", "결과 표"])
    with t_chart:
        title, sub = query_title(df, q)
        chart_title(title, sub)
        fig, basis = query_chart(df, q)
        src_chart = f"{src_q} · {basis}"
        png_args = dict(fig=fig, filename=f"조회_{q['chart'].replace(' ', '')}_{q['area']}_{y0}_{y1}",
                        label="차트 PNG 이미지 내려받기", title=title, source=f"출처: {src_q} · {basis}")
    with t_map:
        by_c = df.groupby("국가")[["수입액", "수출액"]].sum()
        modes = {"수출입": ("imp", "exp"), "수출": ("exp",), "수입": ("imp",)}[q["area"]]
        tops = []
        if "imp" in modes and by_c["수입액"].max() > 0:
            tops.append(f"수입 {escape(str(by_c['수입액'].idxmax()))}")
        if "exp" in modes and by_c["수출액"].max() > 0:
            tops.append(f"수출 {escape(str(by_c['수출액'].idxmax()))}")
        chart_title((f'고른 {len(q["names"])}개국 중 1위는 <span class="key">{" · ".join(tops)}</span>' if tops and len(q["names"]) > 1
                     else f"{escape(q['names'][0]) if len(q['names']) == 1 else '고른 국가'} {q['area']} 분포"),
                    f"색 = 선택 국가 합계 대비 비중 · 상위 6개국 라벨 · {y0}~{y1} 합계 · 백만 USD")
        country_map({n: float(v) for n, v in by_c["수입액"].items() if v > 0},
                    {n: float(v) for n, v in by_c["수출액"].items() if v > 0},
                    modes=modes, height=400, note="선택 국가 기준", where=WHERE)
        src_map = f"{src_q} · 국가 좌표는 나라 대표 위치 · 수입 = 선적국, 수출 = 도착국"
    with t_tbl:
        tm = ([m for m in q["metrics"] if m in Q_MONEY] or q["metrics"][:1])[0]
        tsum = df.groupby("국가")[tm].sum()
        if len(q["names"]) > 1 and not tsum.empty:
            tt = tsum.idxmax()
            v = f"{tsum[tt]:+,.0f}" if tm == "무역수지" else f"{tsum[tt]:,.0f}"
            chart_title(f'{y0}~{y1} {tm} 합계가 가장 큰 나라는 <span class="key">{escape(str(tt))}</span>({v} {Q_UNIT[tm]})',
                        f"행 = 국가 · 열 = 연도 × 지표 · {y0}~{y1}")
        else:
            chart_title(f"{escape(q['names'][0]) if q['names'] else '선택 국가'} 연도별 통계표", f"행 = 국가 · 열 = 연도 × 지표 · {y0}~{y1}")
        stat_table(df, q)
        src_tbl = f"{src_q} · CSV 는 오른쪽 버튼으로, 고른 차트 유형 모양대로 내려받습니다"
    # CSV — 고른 차트 모양대로(조회 결과와 같은 표를 다시 짠다). 탭 칸 아래 오른쪽(어느 탭이든 같은 자리).
    out, note = csv_shape(q["chart"], df, q)
    head = csv_header(f"분석영역 {q['area']} · 품목군 {q['hs']} · 국가 {len(q['names'])}개({', '.join(q['names'][:10])}"
                      f"{' 외' if len(q['names']) > 10 else ''}) · 기간 {y0}~{y1} · 차트 {q['chart']} · 단위 백만 USD(중량 톤)",
                      SOURCE, [("관세청 수출입", STAMP, None)], extra=note)
    _dl_area([
        (src_chart, lambda: _png_dl(png_args.pop("label"), **png_args, width=_png_width(png_args["fig"]))),   # 차트 탭
        (src_map, _map_png_button),                                                                   # 국가별 분포 지도 탭
        (src_tbl, lambda: st.download_button("결과 표 CSV 내려받기", (head + out.to_csv(index=False)).encode("utf-8-sig"),
                                   f"조회결과_{q['chart'].replace(' ', '')}_{q['area']}_{y0}_{y1}.csv",
                                   "text/csv", icon=":material/download:", type="primary")),      # 결과 표 탭
    ], map_file=f"조회_국가별분포지도_{q['area']}_{y0}_{y1}")



# ── 조회 결과 — 군수품 FSG/FSC · 국산화개발(전자 계열 행을 조건으로 걸러 센다) ──────────────────────────────
QF_AGG = {"품목 건수": ("NSN", "size"), "FSC 수": ("FSC", "nunique"), "적용장비 수": ("적용장비", "nunique"),
          "KDSIS 연결 건수": ("KDSIS 연결", "sum")}
QL_AGG = {"국산화개발 기록 수": ("부품관리번호", "size"), "고유 부품 수": ("부품관리번호", "nunique"),
          "사업 수": ("사업명", "nunique"), "관련 업체 수": ("관련 업체", "nunique")}
_has = lambda col, txt: col.str.contains(txt, case=False, regex=False)   # 부분검색(대소문자 무시, 정규식 아님)


def result_fsg(q: dict) -> pd.DataFrame:
    """군수품 품목(전자 계열)을 조건으로 거른다. 빈 검색칸은 조건에서 뺀다."""
    d = QF_ITEMS
    d = d[d["FSC"].isin(q["fsc"]) & d["군종"].isin(q["branch"]) & d["요구연도"].between(*q["years"])]
    for col, txt in (("품목명", q["name"]), ("기능명", q["func"]), ("NSN", q["nsn"])):
        if txt:
            d = d[_has(d[col], txt)]
    if q["kind"] != "전체":
        d = d[d["품목종류"] == q["kind"]]
    return d


def result_localized(q: dict) -> pd.DataFrame:
    """국산화개발 기록(전자 계열)을 조건으로 거른다."""
    d = QL_ITEMS
    d = d[d["사업명"].isin(q["proj"]) & d["FSC"].isin(q["fsc"]) & d["관련 업체"].isin(q["comp"])]
    for col, txt in (("품목명", q["name"]), ("부품관리번호", q["part"]), ("NSN", q["nsn"])):
        if txt:
            d = d[_has(d[col], txt)]
    return d


def _cat_label(col: str, v: str) -> str:
    return f"FSG {v} {FSG_NAME.get(v, '')}".rstrip() if col == "FSG" else f"{v} {FSC_NAME.get(v, '')}".rstrip()


def cat_table(df: pd.DataFrame, note: str) -> None:
    """결과 표(목록형) — HS 결과 표와 같은 통계표 모양(STAT_CSS). 글자 열은 왼쪽, 숫자 열은 오른쪽 정렬.
    행이 많으면 앞 500행만 그리고(브라우저 부담) CSV 는 전체를 내려받는다."""
    flag = {c for c in df.columns if df[c].dtype == bool}
    num = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in flag and c != "요구연도"}
    shown = df.head(500)

    def cell(c, v):
        if c in num:
            return f"<td>{v:,.0f}</td>"
        v = ("연결" if v else "—") if c in flag else ("—" if v is None or (isinstance(v, float) and pd.isna(v)) else escape(str(v)))
        return f'<td style="text-align:left">{v}</td>'
    head = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(cell(c, r[c]) for c in df.columns) + "</tr>" for _, r in shown.iterrows())
    more = f" · 화면에는 앞 {len(shown):,}행만(CSV 는 {len(df):,}행 전체)" if len(df) > len(shown) else ""
    st.html(STAT_CSS + f'<div class="st-scroll"><table class="st-tbl"><thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div><div class="st-note">{escape(note)}{more}</div>')


def _muted(hex_color: str, k: float = .55, base: str = "#eef2f8") -> str:
    """채도를 낮춘 색 — 팔레트 색을 옅은 바탕색(base) 쪽으로 k 만큼 섞는다(색 계열은 그대로, 진하기만 낮춤)."""
    a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(a, b))


def cat_chart(by: pd.DataFrame, q: dict, units: dict, yearly: pd.DataFrame | None = None,
              muted_rest: bool = False) -> tuple[go.Figure, str]:
    """분류(FSG · FSC)별 차트 — by: 행 = 분류 이름, 열 = 지표. 막대 · 트리맵 · 누적 막대 · 꺾은선은 csv_preview 를,
    도넛은 hover_donut 을 쓴다. yearly = 요구연도 × 분류 표(누적 막대 · 꺾은선용). (PNG 용 그림, 그래프 기준 문구)."""
    chart, ms = q["chart"], q["metrics"]
    pm = ms[0]
    # 색은 값이 큰 순서(1위~8위)대로 8색, 9위부터 기타(ETC) — 표 줄 순서(FSC 코드 순)로 주면 도넛 상위 7개 · 트리맵 큰 칸이 회색이 됐다
    color = {n: (Q_PALETTE[i] if i < len(Q_PALETTE) else ETC) for i, n in enumerate(by[pm].sort_values(ascending=False).index)}
    note = f"값 = {pm}({units[pm]})"
    if chart == "도넛 그래프":
        rows = sorted(((n, float(v), color[n]) for n, v in by[pm].items() if v > 0), key=lambda r: -r[1])
        rows = rows[:7] + ([("기타", sum(r[1] for r in rows[7:]), ETC)] if len(rows) > 7 else [])
        hover_donut(rows, f"{sum(r[1] for r in rows):,.0f}", f"{pm} 합계 · {units[pm]}", value_unit=units[pm], height=420)
        fig = go.Figure(go.Pie(labels=[r[0] for r in rows], values=[r[1] for r in rows], hole=.55, sort=False,
                               marker=dict(colors=[r[2] for r in rows], line=dict(color="#fff", width=1.5)),
                               textinfo="label+percent"))
        fig.update_layout(height=420, annotations=[dict(text=f"{sum(r[1] for r in rows):,.0f}<br>{pm} · {units[pm]}",
                                                        showarrow=False, font=dict(size=17))])
        return style_fig(fig), note
    if chart == "막대 그래프":
        out = by[ms].rename(columns=lambda m: f"{m}({units[m]})").rename_axis("분류").reset_index()
        note = "값 = 조건에 맞는 건수 · 개수" + (" · 지표마다 단위가 달라 크기만 비교" if len(ms) > 1 else "")
    elif chart == "트리맵 차트":
        s = by[pm][by[pm] > 0].sort_values(ascending=False)   # 큰 칸부터 — csv_preview 가 앞에서부터 8색을 준다
        out = pd.DataFrame({"분류": s.index, f"{pm}({units[pm]})": s.values, "비중(%)": (s / s.sum() * 100).round(1).values})
    else:                                   # 누적 막대 · 꺾은선 — 요구연도 흐름(원자료 공백 연도 제외)
        out = (yearly.assign(합계=yearly.sum(axis=1)) if chart == "누적 막대 그래프" else yearly).reset_index()
        gap = sorted(QF_YEAR_GAP & set(range(q["years"][0], q["years"][1] + 1)))
        note += " · 요구연도별" + (f" · {gap[0]}~{gap[-1]}년은 원자료 공백 구간이라 뺐습니다" if gap else "")
    fig = csv_preview(chart, out)
    fig.update_layout(height=400)
    if chart == "트리맵 차트" and muted_rest:
        # 9위부터 회색(ETC) 대신 팔레트 8색을 차례로 돌려 채도만 낮춘 색 — 상위 8칸(진한 색)이 먼저 보이고 나머지도 구분된다
        n = len(Q_PALETTE)
        fig.data[0].marker.colors = [Q_PALETTE[i] if i < n else _muted(Q_PALETTE[i % n]) for i in range(len(out))]
    if chart == "막대 그래프" and len(out) > 8:
        fig.update_xaxes(tickangle=-35)
    if chart == "막대 그래프" and len(out) > WIDE_MIN:   # 막대가 많으면 실제 폭을 넓혀 가로 스크롤(PNG 도 같은 폭 — _png_width)
        wide_chart(fig, len(out))
    else:
        st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CFG)
    return fig, note


def _cat_kpis(tot: dict, ms: list[str], units: dict, icons: dict, sub: str) -> None:
    cards = "".join(kpi(m, f"{tot[m]:,.0f}", units[m], sub, icon=icons[m]) for m in ms)
    st.html(f'<div class="kpis q" style="grid-template-columns:repeat({min(len(ms), 4)},minmax(0,1fr))">{cards}</div>')


def _cat_csv(base: str, cond: str, src: str, stamp_name: str, stamp: dict, label: str, df: pd.DataFrame) -> None:
    """표 하나의 CSV 단추(머리에 조회 조건 · 출처 · 자료 기간) — 그 표 탭의 내려받기 칸(_dl_area)에 놓인다."""
    head = csv_header(f"{cond} · 표 {label}", src, [(stamp_name, stamp, None)])
    st.download_button(f"{label} CSV 내려받기", (head + df.to_csv(index=False)).encode("utf-8-sig"),
                       f"{base}_{label.replace('·', '').replace(' ', '')}.csv", "text/csv",
                       icon=":material/download:", type="primary", key=f"dl_{label}")


def query_result_fsg(q: dict) -> None:
    """군수품 FSG/FSC 조회 결과 — 지표 카드 · [차트] [분류 상세] [결과 표]. 국가 지도는 없다(HS 와 엮지 않는다)."""
    unit, ms = q["unit"], q["metrics"]
    y0, y1 = q["years"]
    # 집계 기준 — unit 은 사용자가 고른 값이 아니라 FSC 를 골랐는지로 정해진다(query_panel_fsg)
    if unit == "FSC":
        basis = f'FSC {q["fsc"][0]} 기준' if len(q["fsc"]) == 1 else f'FSC {q["fsc"][0]} 등 {len(q["fsc"])}개 기준'
    else:
        basis = f'FSG {len(q["fsg"])}개 기준 · FSC 전체 {len(q["fsc"])}개'
    st.html(f'<div class="h" style="font-size:17px">조회 결과 <span class="sub">군수품 · {basis} · '
            f'{"·".join(q["branch"]) or "군종 없음"} · 요구연도 {y0}~{y1} · {q["chart"]}</span></div>')
    if not q["fsg"]:
        return st.info("FSG 를 하나 이상 고르거나 「전체 FSG 선택」을 켜 주세요.")
    if not q["branch"]:
        return st.info("군종을 하나 이상 고르세요.")
    if not ms:
        return st.info("지표를 하나 이상 고르세요.")
    d = result_fsg(q)
    if d.empty:
        return st.info("조건에 맞는 품목이 없습니다. 품목명 · 상세검색 조건을 줄여 보세요.")
    units, icons = {m: u for m, u, _ in QF_METRICS}, {m: ic for m, _, ic in QF_METRICS}
    tot = {m: float(d.agg({c: f})[c]) for m, (c, f) in QF_AGG.items()}
    _cat_kpis(tot, ms, units, icons, f"요구연도 {y0}~{y1} · 전자 계열 · 건수만")

    by = d.groupby(unit).agg(**QF_AGG).rename(index=lambda v: _cat_label(unit, v))
    ys = [y for y in QF_YEARS if y0 <= y <= y1 and y not in QF_YEAR_GAP]
    yearly = (d.assign(분류=d[unit].map(lambda v: _cat_label(unit, v))).groupby(["요구연도", "분류"])
              .agg(v=QF_AGG[ms[0]]).reset_index().pivot(index="요구연도", columns="분류", values="v")
              .reindex(columns=by.index).reindex(ys).fillna(0))
    detail = (d.groupby(["FSG", "FSC"]).agg(**QF_AGG).reset_index()
              .assign(FSG=lambda x: x["FSG"].map(lambda g: f"{g} {FSG_NAME.get(g, '')}"),
                      FSC명=lambda x: x["FSC"].map(lambda c: FSC_NAME.get(c, "")))
              [["FSG", "FSC", "FSC명", *QF_AGG]])
    items = d.assign(FSC=d["FSC"].map(lambda c: _cat_label("FSC", c)))[
        ["NSN", "품목명", "FSC", "기능명", "품목종류", "군종", "요구연도", "적용장비", "KDSIS 연결"]].sort_values(["FSC", "NSN"])

    src = f"{SRC_PLAN} · 전자 계열(FSG 58·59·60) 품목 · 건수만(금액은 통화 미검증이라 쓰지 않음)"
    t_chart, t_det, t_tbl = st.tabs(["차트", "분류 상세", "결과 표"])
    with t_chart:
        top = by[ms[0]].idxmax()
        chart_title(f'{ms[0]}가 가장 많은 {"FSG" if unit == "FSG" else "FSC"}는 <span class="key">{escape(str(top))}</span>'
                    f'({by.loc[top, ms[0]]:,.0f}{units[ms[0]]})',
                    f"군수품 · {unit} 단위 · 요구연도 {y0}~{y1} · {len(d):,}건")
        fig, note = cat_chart(by, q, units, yearly)
        src_chart = f"{src} · 그래프 기준: {note}"
    with t_det:
        cat_table(detail, f"분류 상세 · FSG {detail['FSG'].nunique()}개 → FSC {len(detail)}개")
    with t_tbl:
        cat_table(items, f"결과 표 · 품목 {len(items):,}건 · 품목명은 원자료(영문) 그대로 · 적용장비는 원문(공란 · * 제외)")
    cond = (f"군수품 FSG/FSC · {unit} 단위 · FSG {','.join(q['fsg'])} · FSC {len(q['fsc'])}개 · 군종 {','.join(q['branch'])}"
            f" · 요구연도 {y0}~{y1}" + "".join(f" · {k} '{v}'" for k, v in (("품목명", q["name"]), ("기능명", q["func"]),
                                                                           ("NSN", q["nsn"])) if v)
            + ("" if q["kind"] == "전체" else f" · 품목종류 {q['kind']}"))
    base = f"조회결과_군수품_{unit}_{y0}_{y1}"
    _dl_area([
        (src_chart, lambda: _png_dl("차트 PNG 이미지 내려받기", fig=fig,
                                    filename=f"조회_군수품_{unit}_{q['chart'].replace(' ', '')}_{y0}_{y1}",
                                    width=_png_width(fig), source=f"출처: {src}")),                     # 차트 탭
        (None, lambda: _cat_csv(base, cond, src, "국외 조달계획", S_PLAN, "분류 상세", detail)),       # 분류 상세 탭
        (None, lambda: _cat_csv(base, cond, src, "국외 조달계획", S_PLAN, "결과 표", items)),         # 결과 표 탭
    ])


def query_result_localized(q: dict) -> None:
    """국산화개발 조회 결과 — 지표 카드 · [차트] [사업·업체] [품목 상세]. 비율 · 추세 지표는 두지 않는다(스냅샷)."""
    ms = q["metrics"]
    st.html(f'<div class="h" style="font-size:17px">조회 결과 <span class="sub">국산화개발 · 사업 {len(q["proj"])}개 · FSG {len(q["fsg"])}개 · '
            f'FSC {len(q["fsc"])}개 · 관련 업체 {len(q["comp"])}개 · {q["chart"]}</span></div>')
    for ok, msg in ((q["proj"], "사업명을 하나 이상 고르거나 「전체 사업 선택」을 켜 주세요."),
                    (q["fsg"], "FSG 를 하나 이상 고르거나 「전체 FSG 선택」을 켜 주세요."),
                    (q["comp"], "관련 업체를 하나 이상 고르거나 「전체 관련 업체 선택」을 켜 주세요."),
                    (ms, "지표를 하나 이상 고르세요.")):
        if not ok:
            return st.info(msg)
    d = result_localized(q)
    if d.empty:
        return st.info("조건에 맞는 기록이 없습니다. 품목명 · 상세검색 조건을 줄여 보세요.")
    units, icons = {m: u for m, u, _ in QL_METRICS}, {m: ic for m, _, ic in QL_METRICS}
    tot = {m: float(d.agg({c: f})[c]) for m, (c, f) in QL_AGG.items()}
    _cat_kpis(tot, ms, units, icons, "스냅샷 · 전자 계열 · 국산화율 아님")

    by = d.groupby("FSC").agg(**QL_AGG).rename(index=lambda v: _cat_label("FSC", v))
    pc = pd.crosstab(d["사업명"], d["관련 업체"])
    pc = pc[pc.sum().sort_values(ascending=False).index]            # 기록이 많은 업체부터
    pc = pc.assign(합계=pc.sum(axis=1)).sort_values("합계", ascending=False).reset_index().rename(columns={"사업명": "사업명 \\ 관련 업체"})
    items = d.assign(FSC=d["FSC"].map(lambda c: _cat_label("FSC", c)))[
        ["부품관리번호", "NSN", "품목명", "FSC", "사업명", "관련 업체"]].sort_values(["부품관리번호", "사업명"])

    src = f"{SRC_B2} · 전자 계열(FSC 58·59xx) · 건수 · 개수만(국산화율 · 추세 아님) · 관련 업체 = 원자료 계약업체(개발 주체 아님)"
    t_chart, t_pc, t_tbl = st.tabs(["차트", "사업·업체", "품목 상세"])
    with t_chart:
        top = by[ms[0]].idxmax()
        chart_title(f'{ms[0]}가 가장 많은 FSC는 <span class="key">{escape(str(top))}</span>({by.loc[top, ms[0]]:,.0f}{units[ms[0]]})',
                    f"국산화개발 · 사업 {d['사업명'].nunique()}개 · 기록 {len(d):,}건 · 스냅샷")
        fig, note = cat_chart(by, q, units, muted_rest=True)     # 트리맵 9위부터 낮은 채도 색(국산화개발만)
        src_chart = f"{src} · 그래프 기준: {note}"
    with t_pc:
        cat_table(pc, "사업 × 관련 업체 · 칸 = 국산화개발 기록 수(건) · 관련 업체 = 계약업체")
    with t_tbl:
        cat_table(items, f"품목 상세 · 기록 {len(items):,}건")
    cond = (f"국산화개발 · 사업 {len(q['proj'])}개 · FSG {','.join(q['fsg'])} · FSC {len(q['fsc'])}개 · 관련 업체 {len(q['comp'])}개"
            + "".join(f" · {k} '{v}'" for k, v in (("품목명", q["name"]), ("부품관리번호", q["part"]), ("NSN", q["nsn"])) if v))
    base = "조회결과_국산화개발"
    _dl_area([
        (src_chart, lambda: _png_dl("차트 PNG 이미지 내려받기", fig=fig,
                                    filename=f"조회_국산화개발_{q['chart'].replace(' ', '')}",
                                    width=_png_width(fig), source=f"출처: {src}")),                     # 차트 탭
        (None, lambda: _cat_csv(base, cond, src, "국산화개발품목", S_B2, "사업·업체", pc)),            # 사업·업체 탭
        (None, lambda: _cat_csv(base, cond, src, "국산화개발품목", S_B2, "품목 상세", items)),         # 품목 상세 탭
    ])


def render() -> None:
    """조건 카드 | 결과 카드 + 캡션 · 출처. 구역(소분류 제목)은 부르는 쪽이 연다."""
    c_form, c_res = st.columns([1.15, 1.45], gap="medium")   # 1280 폭에서 차트 유형 · 지표 이름이 잘리지 않게 조건 칸을 넓게
    with c_form:
        q = query_panel()
    with c_res.container(border=True, key="card_res"):
        if q["type"] == "군수품 FSG/FSC":
            query_result_fsg(q)
        elif q["type"] == "국산화개발":
            query_result_localized(q)
        else:
            y0, y1 = q["years"]
            st.html(f'<div class="h" style="font-size:17px">조회 결과 <span class="sub">{q["area"]} · {escape(str(q["hs"]))} · {len(q["names"])}개국 · '
                    f'{y0}~{y1} · {q["chart"]}</span></div>')
            if not q["names"]:
                st.info("국가를 하나 이상 고르거나 「전체 국가 선택」을 켜 주세요.")
            elif not q["n_items"]:
                st.info("품목코드를 하나 이상 고르거나 「전체 품목 선택」을 켜 주세요.")
            elif not q["metrics"]:
                st.info("지표를 하나 이상 고르세요. 분석영역에 맞는 지표만 목록에 나옵니다.")
            else:
                query_result(q, y0, y1)
    # 카드 아래 한 줄 설명 · 맨 아래 「? 출처」 원은 두지 않는다(출처는 결과 카드 안 「?」 · PNG · CSV 에 있다)


render()
