"""페이지 레지스트리 — 파일·제목·URL·사이드바 순서를 한 곳에서 정한다(main.py 라우터와 home.py 탭 안내가 같이 읽음).

- 키는 app/specs/00_common.md §9 페이지 키와 맞춘다. 파일명 숫자는 식별자일 뿐 순서가 아니다.
- 표시 순서는 NAV_ORDER 한 줄. 페이지 이름·순서는 담당자 Figma 결과(M3)로 바뀔 수 있어 여기만 고치면 된다.
- st.Page 객체는 pages()가 한 번 만들어 재사용한다(ui.sidebar 는 `page is current` 로 현재 페이지를 판정).
- 새 페이지: PAGE_SPECS 에 한 줄 추가 + NAV_ORDER 에 키 삽입. 
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import streamlit as st

APP = Path(__file__).resolve().parent


class PageSpec(NamedTuple):
    key: str        # specs 키(00_common.md §9)
    file: str       # app/ 기준 상대 경로
    title: str      # 브라우저 탭·st.Page title
    url_path: str   # URL 슬러그("" = 기본 페이지 /)
    label: str      # 사이드바 라벨
    icon: str       # 사이드바 아이콘 — 단색 Material Symbols 이름(이모지 쓰지 않음)


PAGE_SPECS: tuple[PageSpec, ...] = (
    PageSpec("home", "home.py", "홈", "", "HOME", "home"),
    PageSpec("trade", "pages/1_수출입_현황.py", "① 수출입 현황", "import", "① 수출입 현황", "bar_chart"),
    PageSpec("parts", "pages/2_부품_무기체계.py", "② 조달·국산화 근거", "parts", "② 조달·국산화 근거", "inventory_2"),
    PageSpec("table", "pages/3_품목군_현황표.py", "③ 검토 목록", "table", "③ 검토 목록", "table_rows"),
    PageSpec("background", "pages/4_정책_산업_배경.py", "⓪ 국외조달 예산 · 배경", "background", "⓪ 국외조달 예산 · 배경", "account_balance"),
    PageSpec("info", "pages/5_DATA_INFO.py", "⑤ 데이터 정보", "info", "DATA INFO", "info"),
    PageSpec("search", "pages/6_조회.py", "조회", "search", "조회", "search"),
)
SPEC_BY_KEY: dict[str, PageSpec] = {s.key: s for s in PAGE_SPECS}

# 사이드바 표시 순서(CLAUDE.md 핵심 설계 제약, 09-17 교수 피드백): 홈 · ① 수출입 현황 · ⓪ 국외조달 예산(배경) · ② 근거 · ③ 검토 목록 · 조회 · ⑤ 데이터 정보
NAV_ORDER: tuple[str, ...] = ("home", "trade", "background", "parts", "table", "search", "info")


@lru_cache(maxsize=1)
def pages() -> dict[str, st.Page]:
    """키 → st.Page. 프로세스당 한 번 만들어 rerun 사이에 같은 객체를 쓴다."""
    out: dict[str, st.Page] = {}
    for s in PAGE_SPECS:
        if s.url_path:
            out[s.key] = st.Page(APP / s.file, title=s.title, url_path=s.url_path)
        else:
            out[s.key] = st.Page(APP / s.file, title=s.title, default=True)
    return out


def page(key: str) -> st.Page:
    return pages()[key]


def nav_items() -> list[tuple[st.Page, str, str]]:
    """ui.sidebar 인자 — NAV_ORDER 순서의 (st.Page, 라벨, 아이콘)."""
    return [(page(k), SPEC_BY_KEY[k].label, SPEC_BY_KEY[k].icon) for k in NAV_ORDER]
