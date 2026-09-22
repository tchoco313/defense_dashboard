"""주요 방산 전자부품 수출입 및 국산화 현황 대시보드 — 진입점(라우터). 제목·페이지 라벨은 2026-09-21 회의 M1(app/specs/00_common.md §1·§8).

실행: streamlit run app/main.py
페이지 파일·제목·URL·메뉴 순서는 nav.py(PAGE_SPECS·NAV_ORDER) 한 곳에서 정한다. 화면 본문은 home.py · pages/*.py.
DB 접속 확인(db_ready)은 여기서 한 번만 — 페이지 파일은 검사하지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
from db import data_stamp, db_ready  # noqa: E402
from nav import NAV_ORDER, nav_items, page  # noqa: E402
from ui import inject_css, top_bar  # noqa: E402

st.set_page_config(page_title="방산 전자부품 수출입 및 국산화 현황", page_icon="🛰️", layout="wide")
inject_css()

pg = st.navigation([page(k) for k in NAV_ORDER], position="hidden")


def stamp() -> str:
    """상단바 — 관세청 자료 기간과 fact 표 적재일(db.data_stamp, 비캐시: 실패 문구가 1시간 고정되지 않게). CSV 머리줄도 같은 값."""
    s = data_stamp("customs_all", "fact_customs_monthly")
    if not s["has_period"]:
        return "관세청 자료 —<br>DB 적재 —"
    return f"관세청 자료 {s['period']}<br>DB 적재 {s['loaded'] or '—'}"


top_bar(nav_items(), pg, stamp())
if not db_ready():      # 접속 실패면 오류·「다시 연결」만 보이고 페이지 본문은 실행하지 않는다
    st.stop()
pg.run()
