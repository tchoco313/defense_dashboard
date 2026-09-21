"""주요 방산 전자부품 수출입 및 국산화 현황 대시보드 — 진입점(라우터). 제목·페이지 라벨은 2026-09-21 회의 M1(app/specs/00_common.md §1·§8).

실행: streamlit run app/main.py
메뉴는 목업(docs/report/app/mockup-2026-09-18/main.html) 순서: 홈 · ① · ② · ③ · ④ · 🔎 조회 · ⑤ DATA INFO.
아직 만들지 않은 화면은 메뉴에 회색(준비 중)으로만 둔다. 화면 본문은 home.py · pages/*.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
from db import data_stamp  # noqa: E402
from ui import inject_css, top_bar  # noqa: E402

st.set_page_config(page_title="방산 전자부품 수출입 및 국산화 현황", page_icon="🛰️", layout="wide")
inject_css()

home = st.Page(APP / "home.py", title="홈", default=True)
p1 = st.Page(APP / "pages" / "1_수출입_현황.py", title="① 수출입 현황", url_path="import")
p2 = st.Page(APP / "pages" / "2_부품_무기체계.py", title="② 부품→무기체계", url_path="parts")
p3 = st.Page(APP / "pages" / "3_품목군_현황표.py", title="③ 품목군 현황표", url_path="table")
p4 = st.Page(APP / "pages" / "4_정책_산업_배경.py", title="④ 정책·산업 배경", url_path="background")
p5 = st.Page(APP / "pages" / "5_DATA_INFO.py", title="⑤ DATA INFO", url_path="info")
p6 = st.Page(APP / "pages" / "6_조회.py", title="🔎 조회", url_path="search")
pg = st.navigation([home, p1, p2, p3, p4, p5, p6], position="hidden")


def stamp() -> str:
    """상단바 — 관세청 자료 기간과 fact 표 적재일(db.data_stamp, 비캐시: 실패 문구가 1시간 고정되지 않게). CSV 머리줄도 같은 값."""
    s = data_stamp("customs_all", "fact_customs_monthly")
    if not s["has_period"]:
        return "관세청 자료 —<br>DB 적재 —"
    return f"관세청 자료 {s['period']}<br>DB 적재 {s['loaded'] or '—'}"


top_bar([(home, "홈"), (p1, "① 수출입 현황"), (p2, "② 부품→무기체계"), (p3, "③ 품목군 현황표"),
         (p4, "④ 정책·산업 배경"), (p6, "🔎 조회"), (p5, "⑤ DATA INFO")], pg, stamp())
pg.run()
