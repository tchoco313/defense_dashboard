"""주요 방산 전자부품 수입 의존도 · 국산화 현황 대시보드 — 진입점(라우터).

실행: streamlit run app/main.py
메뉴는 목업(docs/report/mockup-2026-09-18/main.html) 순서: 홈 · ① · ② · ③ · ④ · 🔎 조회 · ⑤ DATA INFO.
아직 만들지 않은 화면은 메뉴에 회색(준비 중)으로만 둔다. 화면 본문은 home.py · pages/*.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
from db import safe_query  # noqa: E402
from ui import inject_css, top_bar  # noqa: E402

st.set_page_config(page_title="방산 전자부품 수입 의존도 · 국산화 현황", page_icon="🛰️", layout="wide")
inject_css()

home = st.Page(APP / "home.py", title="홈", default=True)
p1 = st.Page(APP / "pages" / "1_수출입_현황.py", title="① 수입 의존도", url_path="import")
p2 = st.Page(APP / "pages" / "2_부품_무기체계.py", title="② 부품→무기체계", url_path="parts")
p3 = st.Page(APP / "pages" / "3_품목군_현황표.py", title="③ 품목군 현황표", url_path="table")
p4 = st.Page(APP / "pages" / "4_정책_산업_배경.py", title="④ 정책·산업 배경", url_path="background")
p5 = st.Page(APP / "pages" / "5_DATA_INFO.py", title="⑤ DATA INFO", url_path="info")
p6 = st.Page(APP / "pages" / "6_조회.py", title="🔎 조회", url_path="search")
pg = st.navigation([home, p1, p2, p3, p4, p5, p6], position="hidden")


@st.cache_data(ttl=3600, show_spinner=False)
def stamp() -> str:
    cov = safe_query("SELECT MIN(yyyymm) AS s, MAX(yyyymm) AS e FROM fact_customs_monthly")
    if cov is None or cov.empty or cov.iloc[0]["e"] is None:
        return "데이터 기준일 —"
    s, e = cov.iloc[0]["s"], cov.iloc[0]["e"]
    loaded = safe_query("SELECT DATE(MAX(measured_at)) AS d FROM meta_load_log")
    d = loaded.iloc[0]["d"] if loaded is not None and not loaded.empty else None
    return f"데이터 기준일 {d or '—'}<br>관세청 {s[:4]}.{s[4:]}~{e[:4]}.{e[4:]}"


top_bar([(home, "홈"), (p1, "① 수입 의존도"), (p2, "② 부품→무기체계"), (p3, "③ 품목군 현황표"),
         (p4, "④ 정책·산업 배경"), (p6, "🔎 조회"), (p5, "⑤ DATA INFO")], pg, stamp())
pg.run()
