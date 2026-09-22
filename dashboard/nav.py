"""페이지 레지스트리 — 파일·제목·URL·상단바 순서를 한 곳에서 정한다(main.py 라우터와 home.py 탭 안내가 같이 읽음).

- 키는 app/specs/00_common.md §9 페이지 키와 맞춘다. 파일명 숫자는 식별자일 뿐 순서가 아니다.
- 표시 순서는 NAV_ORDER 한 줄. 페이지 이름·순서는 담당자 Figma 결과(M3)로 바뀔 수 있어 여기만 고치면 된다.
- st.Page 객체는 pages()가 한 번 만들어 재사용한다(ui.top_bar 는 `page is current` 로 현재 페이지를 판정).
- 새 페이지: PAGE_SPECS 에 한 줄 추가 + NAV_ORDER 에 키 삽입. 준비 중 화면은 top_bar 에 (None, 라벨)로 넘긴다.
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
    label: str      # 상단바 라벨


PAGE_SPECS: tuple[PageSpec, ...] = (
    PageSpec("home", "home.py", "홈", "", "홈"),
    PageSpec("trade", "pages/1_수출입_현황.py", "① 수출입 현황", "import", "① 수출입 현황"),
    PageSpec("parts", "pages/2_부품_무기체계.py", "② 부품→무기체계", "parts", "② 부품→무기체계"),
    PageSpec("table", "pages/3_품목군_현황표.py", "③ 품목군 현황표", "table", "③ 품목군 현황표"),
    PageSpec("background", "pages/4_정책_산업_배경.py", "④ 정책·산업 배경", "background", "④ 정책·산업 배경"),
    PageSpec("info", "pages/5_DATA_INFO.py", "⑤ DATA INFO", "info", "⑤ DATA INFO"),
    PageSpec("search", "pages/6_조회.py", "🔎 조회", "search", "🔎 조회"),
)
SPEC_BY_KEY: dict[str, PageSpec] = {s.key: s for s in PAGE_SPECS}

# 상단바 표시 순서(목업 main.html): 홈 · ① · ② · ③ · ④ · 🔎 조회 · ⑤ DATA INFO
NAV_ORDER: tuple[str, ...] = ("home", "trade", "parts", "table", "background", "search", "info")


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


def nav_items() -> list[tuple[st.Page, str]]:
    """ui.top_bar 인자 — NAV_ORDER 순서의 (st.Page, 라벨)."""
    return [(page(k), SPEC_BY_KEY[k].label) for k in NAV_ORDER]
