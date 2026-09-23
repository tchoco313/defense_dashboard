"""조회 — 선택형 시각화(팀원 디자인 데모 「조회」 화면을 그대로 옮기고 값만 RDS 로 바꿨다).

왼쪽 「분석 조건 설정」(분석영역 · 품목군 · 세부코드 · 국가 · 기간 · 지표 · 차트 유형 15종 · 빠른 설정)
→ 오른쪽 「조회 결과」(지표 카드 · 차트 / 국가별 분포 지도 / 결과 표 탭 · 차트 모양대로 CSV · 보이는 차트 PNG).
차트 유형 15종과 설명 칸은 KOSIS 「데이터 시각화 체험하기」 차트 목록(디자인 입력 B2)을 따른다.
읽는 표: fact_customs_monthly(월별 HS10 × 국가) · ref_hs_whitelist(분석 대상 13개) · ref_country · ref_hs_code_master(HS10 품명).
자유 입력·임의 SQL 없음 — 조건은 모두 고르는 값이고 SQL 은 바인딩 파라미터만 쓴다.
단위: 금액 백만 USD(USD ÷ 10⁶), 중량 톤(kg ÷ 10³, 참고값). 무역수지 = 수출액 − 수입액. 국가는 선적국(원산지 아님).
"""
from __future__ import annotations

import math
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import data_stamp, query, safe_query
from kdesign import ACCENT, ETC, SERIES, TEXT, _svg_img
from ui import (SHORT, source_pop, chart_source, chart_title, country_map, csv_header, globe_loading, hero, hover_donut, kpi, png_button,
                style_fig, zone)

ALL = "__all__"
SOURCE = "관세청 품목별 국가별 수출입실적(15100475) → fact_customs_monthly · 국가 전체 교역(민수 포함) · 국가는 선적국"
PLOT_CFG = {"displaylogo": False, "modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "autoScale2d"]}
TARGET = "SELECT hs6 FROM ref_hs_whitelist WHERE priority IN (1, 2)"   # 분석 대상 13개(2026-09-21 M5)


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
def load_hs10(hs6: str) -> pd.DataFrame:
    df = query("SELECT DISTINCT hs10 FROM fact_customs_monthly WHERE hs6 = :h ORDER BY hs10", {"h": hs6})
    names = safe_query("SELECT hs10, name_ko FROM ref_hs_code_master WHERE hs10 LIKE :p", {"p": f"{hs6}%"})
    if names is None:
        return df.assign(name_ko=None)
    return df.merge(names.drop_duplicates("hs10"), on="hs10", how="left")


@st.cache_data(ttl=3600, show_spinner=False)
def load_trade(hs6: str, hs10: str | None, y0: int, y1: int) -> pd.DataFrame:
    """연도 × 국가 수출입 금액·중량 합(USD · kg)."""
    cond = f"hs6 IN ({TARGET})" if hs6 == ALL else "hs6 = :h"
    params: dict = {"y0": y0, "y1": y1}
    if hs6 != ALL:
        params["h"] = hs6
    if hs10:
        cond += " AND hs10 = :h10"
        params["h10"] = hs10
    return query(f"""SELECT year, stat_cd, SUM(exp_dlr) AS exp_dlr, SUM(imp_dlr) AS imp_dlr,
                            SUM(COALESCE(exp_wgt, 0)) AS exp_wgt, SUM(COALESCE(imp_wgt, 0)) AS imp_wgt
                     FROM fact_customs_monthly WHERE {cond} AND year BETWEEN :y0 AND :y1
                     GROUP BY year, stat_cd""", params)


def trade_frame(names: list[str], y0: int, y1: int, hs6: str, hs10: str | None) -> pd.DataFrame:
    """데모 trade_frame 과 같은 모양(국가 × 연도 · 수출액 · 수입액 · 무역수지 · 수출중량 · 수입중량) — 값은 RDS.
    고른 국가에서 실적이 없는 연도는 0 으로 채운다(실제 0). 전부 0 이면 빈 표."""
    raw = load_trade(hs6, hs10, y0, y1)
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
hero("조회", "조건을 골라 원하는 차트를 만들고, 표와 그림으로 내려받습니다 — 조건은 고르는 값만 씁니다(자유 입력 없음)",
     stamps=[("관세청 수출입", STAMP)])
if not STAMP["has_period"]:
    if STAMP["error"]:
        st.error(f"관세청 월별 표(fact_customs_monthly)를 조회하지 못했습니다({STAMP['error']}). 잠시 뒤 다시 열어 주세요.")
    else:
        st.warning("관세청 월별 표(fact_customs_monthly)에 적재된 행이 없습니다(미적재).")
    st.stop()

with globe_loading("팀 DB 에서 기준표를 읽는 중"):
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

Q_AREAS = ["수출입", "수출", "수입"]
# 지표 이름, 단위, 아이콘, 쓸 수 있는 분석영역 — 목업처럼 3개씩 두 줄
Q_METRICS = [("수출액", "백만 USD", "", {"수출입", "수출"}), ("수입액", "백만 USD", "", {"수출입", "수입"}),
             ("무역수지", "백만 USD", "", {"수출입"}), ("수출중량", "톤", "", {"수출입", "수출"}),
             ("수입중량", "톤", "", {"수출입", "수입"})]
# 거래건수(데모)는 DB 에 없는 지표라 뺐다 — fact_customs_monthly 는 HS10 × 국가 × 월 합계 행이다
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
Q_METRIC_COLOR = {"수출액": SERIES[1], "수입액": SERIES[0], "무역수지": SERIES[6], "수출중량": "#f5b597",
                  "수입중량": "#9fc1ec"}   # 수입 파랑 · 수출 주황(①·지도와 같은 짝), 중량은 같은 색의 옅은 톤
Q_PALETTE = SERIES   # 검증 팔레트 8색 고정 순서 — 9번째부터는 기타(ETC), 색을 돌려 쓰지 않는다

Q_DEFAULT = {"qs_area": "수출입", "qs_hs6": ALL, "qs_hs10": ALL, "qs_ctry": ["중국", "대만", "미국"], "qs_all": False,
             "qs_y0": Q_YEARS[0], "qs_y1": Q_YEARS[-1], "qs_chart": "막대 그래프",
             **{f"qs_m_{m}": m in Q_MONEY for m, *_ in Q_METRICS}}
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
    st.session_state.update(Q_DEFAULT)
    if any(k.startswith("qs_m_") for k in preset):           # 지표를 정한 설정이면 그 지표만 켠다
        st.session_state.update({f"qs_m_{m}": False for m, *_ in Q_METRICS})
    st.session_state.update(preset)
    st.session_state["qs_quick"] = "빠른 설정 불러오기"       # 고른 뒤에는 다시 안내 문구로


def _q_short(nm: str) -> str:
    """버튼에는 「그래프」 · 「차트」를 떼고 이름만 — 설명 칸 · CSV 파일명에는 전체 이름을 쓴다."""
    return nm.removesuffix(" 그래프").removesuffix(" 차트")


def _q_pick(nm: str) -> None:
    st.session_state["qs_chart"] = nm




def _q_label(icon: str, text: str) -> None:
    st.markdown(f"{icon}&nbsp; **{text}**")


def _q_drop(n: str) -> None:
    st.session_state["qs_ctry"] = [c for c in st.session_state["qs_ctry"] if c != n]


# 왼쪽 글씨 칸 높이 = 오른쪽 첫 입력칸 높이(px). 위로 붙여 놓고 그 높이 안에서 가운데 → 글씨와 입력칸이 같은 가로선
Q_ROW_H = {"area": 32, "hs6": 40, "hs10": 40, "ctry": 40, "period": 40, "metric": 40}
Q_CHIP_COLS = 3                                               # 고른 국가를 입력칸 밑에 한 줄 3개씩


def _q_form_css(n_picked: int, all_c: bool) -> str:
    rows = "".join(f".st-key-card_form .st-key-qlab_{k}{{height:{h}px !important;flex:0 0 auto !important;justify-content:center !important}}"
                   for k, h in Q_ROW_H.items())
    hint = "전체 국가 선택 중" if all_c else (f"국가명을 검색하세요 · {n_picked}개 선택" if n_picked else "")
    return f"""<style>{rows}
/* Streamlit 기본 margin-bottom:-16px 이 글씨 칸을 3px 로 눌러 글씨가 아래로 삐져나왔다(약 8px 낮아 보이던 원인) */
.st-key-card_form div[class*="st-key-qlab_"] [data-testid="stMarkdownContainer"],
.st-key-card_form [data-testid="stMarkdownContainer"]:has(h3){{margin-bottom:0 !important}}
.st-key-card_form div[class*="st-key-qlab_"] [data-testid="stMarkdownContainer"] p{{line-height:1.2}}
/* 국가/지역 · 기간 선택창 — 분석영역에서 고른 칸과 같은 색(연한 파랑 바탕 · 파란 테두리 · 파란 글씨) */
.st-key-qs_ctry [data-testid="stMultiSelect"] > div:last-child > div,
.st-key-qs_y0 [data-testid="stSelectbox"] > div:last-child > div,
.st-key-qs_y1 [data-testid="stSelectbox"] > div:last-child > div{{background:rgba(43,110,246,.1) !important;
  border:1px solid var(--accent) !important}}
.st-key-qs_y0 [data-testid="stSelectbox"] > div:last-child svg,.st-key-qs_y1 [data-testid="stSelectbox"] > div:last-child svg,
.st-key-qs_ctry [data-testid="stMultiSelect"] > div:last-child svg{{color:var(--accent)}}
/* 기간 연도 숫자는 검은색 */
.st-key-qs_y0 [data-testid="stSelectbox"] > div:last-child div,.st-key-qs_y1 [data-testid="stSelectbox"] > div:last-child div,
.st-key-qs_y0 [data-testid="stSelectbox"] input,.st-key-qs_y1 [data-testid="stSelectbox"] input{{color:#111;font-weight:600}}
/* 국가/지역 — 고른 국가는 입력칸 안이 아니라 밑에 칩으로 쌓는다 */
.st-key-qs_ctry [data-testid="stMultiSelectTagsContainer"] > span{{display:none}}
.st-key-qs_ctry [data-testid="stMultiSelectTagsContainer"]::before{{content:"{hint}";color:#5a7fc9;font-size:15.5px;
  padding-left:4px;white-space:nowrap;align-self:center}}
.st-key-qs_ctry [data-testid="stMultiSelectTagsContainer"]:has(input:focus)::before{{content:none}}
.st-key-qs_chips{{gap:6px}}
.st-key-qs_chips [data-testid="stHorizontalBlock"]{{gap:6px;margin-bottom:0 !important}}
.st-key-qs_chips button{{min-height:0;height:30px;padding:0 8px 0 12px;border-radius:6px;border:0;background:#1f3a6e;color:#fff;
  justify-content:space-between}}
.st-key-qs_chips button:hover{{background:#142850;color:#fff}}   /* 국가 칩 — 남색 */
.st-key-qs_chips button > div,.st-key-qs_chips button > div > span{{width:100%;justify-content:space-between}}
.st-key-qs_chips button p{{font-size:14.5px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.st-key-qs_chips button [data-testid="stIconMaterial"]{{color:#fff !important;font-size:17px}}
</style>"""


def query_panel() -> dict:
    """분석 조건 설정 카드(목업 「분석 조건 설정」). 고른 조건을 dict 로 돌려준다."""
    for k, v in Q_DEFAULT.items():
        st.session_state.setdefault(k, v)
    with st.container(border=True, key="card_form"):
        h1, h2 = st.columns([1.25, 1], vertical_alignment="center")
        h1.markdown("### :material/settings: 분석 조건 설정")
        h2.selectbox("빠른 설정", list(Q_QUICK), key="qs_quick", on_change=_q_quick, label_visibility="collapsed")

        all_c = st.session_state["qs_all"]
        st.html(_q_form_css(len(st.session_state["qs_ctry"]), all_c))

        def row(icon: str, text: str, key: str):
            a, b = st.columns([1, 2.55], vertical_alignment="top")
            with a.container(key=f"qlab_{key}"):
                _q_label(icon, text)
            return b

        area = row(":material/travel_explore:", "분석영역", "area").segmented_control(
            "분석영역", Q_AREAS, key="qs_area", required=True, label_visibility="collapsed", width="stretch")
        # 데모의 HS6/HS10 단위 버튼 자리 — 실제 데이터는 품목군(HS6)과 그 안의 세부코드(HS10)를 고른다
        hs6 = row(":material/qr_code_2:", "품목군(HS6)", "hs6").selectbox(
            "품목군", [ALL] + WL["hs6"].tolist(), key="qs_hs6", label_visibility="collapsed",
            format_func=lambda h: f"분석 대상 {len(WL)}개 합계" if h == ALL else f"{HS_NAME[h]} · {h}")
        h10 = load_hs10(hs6) if hs6 != ALL else pd.DataFrame(columns=["hs10", "name_ko"])
        lab10 = {r.hs10: f"{r.hs10} {r.name_ko}" if isinstance(r.name_ko, str) else r.hs10 for r in h10.itertuples()}
        if st.session_state.get("qs_hs10") not in [ALL] + list(lab10):
            st.session_state["qs_hs10"] = ALL
        hs10 = row(":material/qr_code_2:", "세부코드(HS10)", "hs10").selectbox(
            "세부코드", [ALL] + list(lab10), key="qs_hs10", label_visibility="collapsed", disabled=hs6 == ALL,
            format_func=lambda h: ("품목군을 고르면 선택" if hs6 == ALL else "전체 세부코드") if h == ALL else lab10.get(h, h))
        hs = (f"분석 대상 {len(WL)}개 합계" if hs6 == ALL else f"{HS_NAME[hs6]} {hs6}") + ("" if hs10 == ALL else f" · {hs10}")

        with row(":material/public:", "국가/지역", "ctry"):
            picked = st.multiselect("국가/지역", Q_COUNTRIES, key="qs_ctry", label_visibility="collapsed",
                                    placeholder="국가명을 검색하세요.", disabled=all_c)
            if picked and not all_c:
                with st.container(key="qs_chips"):
                    for r in range(0, len(picked), Q_CHIP_COLS):
                        for c, n in zip(st.columns(Q_CHIP_COLS, gap="small"), picked[r:r + Q_CHIP_COLS]):
                            c.button(n, icon=":material/close:", icon_position="right", key=f"qs_chip_{n}",
                                     on_click=_q_drop, args=(n,), width="stretch", help=f"{n} 빼기")
            st.checkbox(f"전체 국가 선택 ({len(Q_COUNTRIES)}개국)", key="qs_all")
        with row(":material/calendar_month:", "기간", "period"):
            # 두 칸에서 연도를 고른다 — 시작 칸은 끝 연도까지만, 끝 칸은 시작 연도부터만 보여 앞뒤가 뒤집히지 않는다
            ss = st.session_state
            c0, mid, c1 = st.columns([1, .16, 1], vertical_alignment="center", gap="small")
            y0 = c0.selectbox("시작 연도", [y for y in Q_YEARS if y <= ss["qs_y1"]], key="qs_y0", label_visibility="collapsed")
            mid.html('<div style="text-align:center;font-size:18px;font-weight:700;color:#6b7a99">~</div>')
            y1 = c1.selectbox("끝 연도", [y for y in Q_YEARS if y >= y0], key="qs_y1", label_visibility="collapsed")

        with row(":material/leaderboard:", "지표 선택", "metric"):
            cols = st.columns(3)
            metrics = []
            for i, (m, _, _, areas) in enumerate(Q_METRICS):
                ok = area in areas
                if cols[i % 3].checkbox(m, key=f"qs_m_{m}", disabled=not ok) and ok:
                    metrics.append(m)

        _q_label(":material/donut_large:", "차트 유형")
        if st.session_state["qs_chart"] not in Q_CHARTS:
            st.session_state["qs_chart"] = Q_DEFAULT["qs_chart"]
        chart = st.session_state["qs_chart"]
        st.html(_csv_css())
        # 버튼에 커서를 올리면 그 차트 설명(차트 목록 설명 칸)이 버튼 묶음 위로 떠서 조건 칸을 덮는다
        with st.container(key="qs_ct_grid"):
            for r in range(0, len(Q_CHARTS), Q_CHART_COLS):
                cols = st.columns(Q_CHART_COLS, gap="small")
                for i, (c, nm) in enumerate(zip(cols, Q_CHARTS[r:r + Q_CHART_COLS]), start=r):
                    c.button(_q_short(nm), icon=Q_CHART_ICON[nm], key=f"qs_ct_{i}", width="stretch", on_click=_q_pick, args=(nm,),
                             type="primary" if chart == nm else "secondary")
                    with c.container(key=f"qs_pop_{i}"):
                        st.html(csv_info(nm))

        names = Q_COUNTRIES if all_c else [n for n in Q_COUNTRIES if n in picked]
        q = {"area": area, "hs": hs, "hs6": hs6, "hs10": None if hs10 == ALL else hs10, "names": names, "period": f"{y0} ~ {y1}", "years": (y0, y1),
             "metrics": metrics, "chart": chart}
    return q


def query_chart(df: pd.DataFrame, q: dict) -> tuple[go.Figure, str]:
    """차트 유형에 맞춰 그린다. 금액 지표(수출액·수입액·무역수지)끼리만 한 축에 두고,
    중량·건수는 금액이 하나도 없을 때만 그린다(단위가 달라 한 축에 섞지 않는다).
    돌려주는 값: (PNG 로 내려받을 그림, 그래프 기준 문구 — 출처 줄에 붙인다)."""
    names, chart = q["names"], q["chart"]
    plot_ms = [m for m in q["metrics"] if m in Q_MONEY] or q["metrics"][:1]
    primary = plot_ms[0]
    unit = Q_UNIT[primary]
    by_c = df.groupby("국가", sort=False)[list(Q_UNIT)].sum()
    color = {n: (Q_PALETTE[i] if i < len(Q_PALETTE) else ETC) for i, n in enumerate(names)}
    note = ""
    fig = go.Figure()
    png_fig = None
    if chart not in ("도넛 그래프", "막대 그래프", "꺾은선 그래프", "누적 막대 그래프", "면적 그래프"):
        # 나머지 차트는 CSV 와 같은 모양의 표로 그린다(내려받는 CSV 와 그림이 어긋나지 않게)
        out, note = csv_shape(chart, df, q)
        fig = csv_preview(chart, out)
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CFG)
        return fig, f"그래프 기준: {note} · {escape(q['hs'])} 기준"
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
    dropped = [m for m in q["metrics"] if m not in plot_ms and chart != "도넛 그래프"]
    msg = " ".join(x for x in (note, f"{'·'.join(dropped)}은(는) 단위가 달라 그래프에서 빼고 위 지표 카드와 표에만 둡니다."
                               if dropped else "") if x)
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
_CB, _CT, _CP, _CG, _CY, _CO, _CA = "#2a78d6", "#1baf7a", "#eb6834", "#dbe4ef", "#eda100", "#f39a70", "#9aa5b8"   # 차트 유형 설명 칸의 장식 그림(KOSIS 차트 목록 모양) — 데이터 색(SERIES 고정 순서)과 무관
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
.st-key-qs_ct_grid button{height:66px;padding:6px 4px;border-radius:8px;border:1px solid var(--line);background:#fff;color:#aab4c5}
.st-key-qs_ct_grid button > div,.st-key-qs_ct_grid button > div > span{width:100%;justify-content:center}
.st-key-qs_ct_grid button > div > span{flex-direction:column;align-items:center;gap:5px}
.st-key-qs_ct_grid button > div > span > span:first-child{margin:0 !important}
/* 아이콘 · 이름은 평소 밝은 회색, 커서를 올리거나 고른 버튼만 파란색(버튼 글자색을 그대로 따른다) */
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
    if chart in ("꺾은선 그래프", "면적 그래프", "누적 막대 그래프"):
        series = [c for c in out.columns[1:] if c != "합계"]
        stack = chart == "면적 그래프" and bool((out[series] >= 0).all().all())
        for i, c in enumerate(series):
            if chart == "누적 막대 그래프":
                fig.add_trace(go.Bar(x=out[first], y=out[c], name=c, marker_color=pal(i)))
            else:
                fig.add_trace(go.Scatter(x=out[first], y=out[c], name=c, line=dict(color=pal(i), width=2.2),
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
                             marker=dict(colors=[pal(i) for i in range(len(out))], line=dict(color="#fff", width=1.5)),
                             textinfo="percent", textposition="inside"))
    elif chart == "트리맵 차트":
        fig.add_trace(go.Treemap(labels=out[first], parents=[""] * len(out), values=out.iloc[:, 1],
                                 marker=dict(colors=[pal(i) for i in range(len(out))]), textinfo="label+percent root"))
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
                                             color=[pal(i) for i in range(len(out))], opacity=.8, line=dict(color="#fff", width=1.2)),
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


def csv_info(nm: str) -> str:
    """차트 설명 칸 — 차트 목록 > 이름 · 그림 · 설명 · 용도 · CSV 모양. 차트 유형 버튼에 커서를 올리면 뜬다."""
    desc, uses, _, shape_txt = CSV_CHARTS[nm]
    return (f'<div class="csv-pop"><div class="csv-crumb">차트 목록 &gt; <b>{nm}</b></div>'
            f'<div class="csv-h" style="border:0;margin:8px 0 10px;padding:0">{nm}</div>'
            f'<div class="csv-top"><div class="csv-fig">{_svg_img(_svg(CSV_ICON[nm]), 150, 105)}</div>'
            f'<div class="csv-desc">{desc}<hr><h5>용도</h5>{"<br>".join(f"- {u}" for u in uses)}'
            f'<br><span class="shape">CSV 데이터 모양 · {shape_txt}</span></div></div></div>')


# ── 조회 — 결과 표: 연도별 통계표(KOSIS 통계표 모양 · 행 = 국가, 열 = 시점(연도) 아래 항목(지표)) ──────────
STAT_CSS = """<style>
/* 슬레이트 머리 · 베이지 줄무늬 · 국가 열 고정 · 가로/세로 스크롤 */
.st-tbl{border-collapse:collapse;font-size:14px;min-width:100%}
.st-scroll{max-height:405px;overflow:auto;border:1px solid #e1e9f3;border-radius:8px;background:#fff}
.st-tbl th{position:sticky;top:0;z-index:2;background:#eaf3fd;color:#0f2a5c;font-weight:600;padding:6px 10px;text-align:center;
  border-right:1px solid #d6e5f5;border-bottom:1px solid #d6e5f5;white-space:nowrap}
.st-tbl th small{font-weight:500;opacity:.85}
.st-tbl thead tr:nth-child(2) th{top:31px;background:#f4f9fe;font-weight:500;font-size:13px}
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
    color = {n: (Q_PALETTE[i] if i < len(Q_PALETTE) else ETC) for i, n in enumerate(names)}
    piv = df.pivot_table(index="국가", columns="연도", values=ms, aggfunc="sum").reindex(names)
    yl = lambda y: f"{y}<small> ({PARTIAL_TXT})</small>" if y == PARTIAL_YEAR else str(y)
    head1 = "".join(f'<th colspan="{len(ms)}">{yl(y)}</th>' for y in years)
    head2 = "".join(f"<th>{m}<br><small>{Q_UNIT[m]}</small></th>" for _ in years for m in ms)
    body = "".join(f'<tr><td><span class="dot" style="background:{color[n]}"></span>{n}</td>'
                   + "".join(_stat_cell(float(piv.loc[n, (m, y)]), m) for y in years for m in ms) + "</tr>"
                   for n in names)
    st.html(STAT_CSS + f'<div class="st-scroll"><table class="st-tbl"><thead><tr><th rowspan="2">국가</th>{head1}</tr>'
            f'<tr>{head2}</tr></thead><tbody>{body}</tbody></table></div>'
            f'<div class="st-note">통계표 · 국가 {len(names)}개 × 시점 {len(years)}개({years[0]}~{years[-1]}) × 항목 {len(ms)}개 · '
            f'{q["area"]} · {q["hs"]} · 가로로 넘겨 보세요'
            + (f" · {PARTIAL_YEAR}년은 {PARTIAL_TXT} 부분연도" if PARTIAL_YEAR in years else "") + "</div>")



def query_result(q: dict, y0: int, y1: int) -> None:
    """조회 결과 카드 안 — 지표 카드 · 차트/지도/표 탭."""
    # 조건을 바꾸면 여기가 다시 계산된다 — 그동안 작은 지구본이 돈다.
    # 로딩 지구본은 실제 DB 조회 시간 동안만 보인다(데모의 인위적 대기 없음).
    with globe_loading("조회 결과를 계산하는 중"):
        df = trade_frame(q["names"], y0, y1, q["hs6"], q["hs10"])
    if df.empty:
        st.info("이 조건에는 수출입 실적이 없습니다(실제 0). 기간 · 품목군 · 국가를 바꿔 보세요.")
        return
    tot = df[list(Q_UNIT)].sum()
    icon = {m: ic for m, _, ic, _ in Q_METRICS}
    cards = "".join(
        kpi(m, f"{tot[m]:+,.0f}" if m == "무역수지" else f"{tot[m]:,.0f}", Q_UNIT[m],
            f"{len(q['names'])}개국 · {y0}~{y1} 합계" + (f" ({PARTIAL_YEAR}년은 {PARTIAL_TXT})" if y1 >= PARTIAL_YEAR else ""),
            tag="참고값" if "중량" in m else "", icon=icon[m]) for m in q["metrics"])
    st.html(f'<div class="kpis q" style="grid-template-columns:repeat({min(len(q["metrics"]), 3)},1fr)">{cards}</div>')

    src_q = (f"관세청 · 품목별 국가별 수출입실적(15100475) → fact_customs_monthly · 자료 기간 {STAMP['period']} · "
             f"DB 적재 {STAMP.get('loaded') or '—'}")
    t_chart, t_map, t_tbl = st.tabs(["차트", "국가별 분포 지도", "결과 표"])
    with t_chart:
        title, sub = query_title(df, q)
        chart_title(title, sub)
        fig, basis = query_chart(df, q)
        chart_source(f"{src_q} · {basis}")
        png_button(fig, f"조회_{q['chart'].replace(' ', '')}_{q['area']}_{y0}_{y1}", label=f"「{q['chart']}」 PNG 이미지 내려받기",
                   align="flex-start", title=title, source=f"출처: {src_q} · {basis}")
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
        chart_source(f"{src_q} · 국가 좌표 ref_country · 수입 = 선적국, 수출 = 도착국")
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
        chart_source(f"{src_q} · CSV 는 오른쪽 아래 버튼으로, 고른 차트 유형 모양대로 내려받습니다")
    # CSV — 고른 차트 모양대로(조회 결과와 같은 표를 다시 짠다). 탭 칸 오른쪽 아래에 겹쳐 둔다(어느 탭이든 같은 자리).
    out, note = csv_shape(q["chart"], df, q)
    head = csv_header(f"분석영역 {q['area']} · 품목군 {q['hs']} · 국가 {len(q['names'])}개({', '.join(q['names'][:10])}"
                      f"{' 외' if len(q['names']) > 10 else ''}) · 기간 {y0}~{y1} · 차트 {q['chart']} · 단위 백만 USD(중량 톤)",
                      SOURCE, [("관세청 수출입", STAMP, None)], extra=note)
    with st.container(key="res_dl", horizontal=True, horizontal_alignment="right"):
        st.download_button(f"「{q['chart']}」 모양으로 CSV 내려받기", (head + out.to_csv(index=False)).encode("utf-8-sig"),
                           f"조회결과_{q['chart'].replace(' ', '')}_{q['area']}_{y0}_{y1}.csv",
                           "text/csv", icon=":material/download:", type="primary")



def page_search() -> None:
    with zone("sel", "분석 조건 설정"):
        c_form, c_res = st.columns([1, 1.55], gap="medium")
        with c_form:
            q = query_panel()
        with c_res.container(border=True, key="card_res"):
            y0, y1 = q["years"]
            st.html(f'<div class="h">조회 결과 <span class="sub">{q["area"]} · {q["hs"]} · {len(q["names"])}개국 · '
                    f'{y0}~{y1} · {q["chart"]}</span></div>')
            if not q["names"]:
                st.info("국가를 하나 이상 고르거나 「전체 국가 선택」을 켜 주세요.")
            elif not q["metrics"]:
                st.info("지표를 하나 이상 고르세요. 분석영역에 맞지 않는 지표는 흐리게 잠깁니다.")
            else:
                query_result(q, y0, y1)
    st.html('<div class="caption">수출입액은 국가 전체(민수 포함) 교역액이며 군수 수요 규모를 뜻하지 않습니다. 중량은 참고값(반올림 오차).</div>'
            + source_pop(f'{SOURCE} · 자료 기간 {STAMP["period"]} · DB 적재 {STAMP.get("loaded") or "—"}'))


page_search()
