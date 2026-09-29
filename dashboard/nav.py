"""페이지 레지스트리 — 파일·제목·URL·메뉴 순서·배너 문구를 한 곳에서 정한다(main.py 라우터 · frame.py 가 읽음).

- 키는 dashboard/specs/00_common.md §9 페이지 키와 맞춘다. 파일명 숫자는 식별자일 뿐 순서가 아니다.
- 표시 순서는 NAV_ORDER 한 줄. 상단 메뉴(GNB)는 조회를 뺀 순서 — 조회는 돋보기 단추로 따로 둔다.
- 블록(왼쪽 메뉴 · 상단 펼침 메뉴)은 페이지 파일의 zone("키", "이름") 호출을 읽어 만든다 — 목록을 따로 적지 않는다.
- st.Page 객체는 실행(rerun)마다 새로 만든다. 프로세스 단위로 캐시해 공유하면 겹친 재실행에서 st.navigation 의
  「한 번만 run」 플래그가 엇갈려 StreamlitAPIException 이 난다(2026-09-28 조회 Escape 재현). 현재 페이지는 url_path 로 판정.
- 새 페이지: PAGE_SPECS 에 한 줄 추가 + NAV_ORDER 에 키 삽입.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import streamlit as st

APP = Path(__file__).resolve().parent


class PageSpec(NamedTuple):
    key: str        # specs 키(00_common.md §9)
    file: str       # dashboard/ 기준 상대 경로
    title: str      # 브라우저 탭·st.Page title
    url_path: str   # URL 슬러그("" = 기본 페이지 /)
    label: str      # 상단 메뉴 · 왼쪽 메뉴 제목 칸 · 경로 표시
    icon: str       # 단색 Material Symbols 이름(이모지 쓰지 않음)
    heading: str    # 서브 배너 제목
    lead: str       # 서브 배너 부제 — 이 화면에서 보는 것 한 문장


PAGE_SPECS: tuple[PageSpec, ...] = (
    PageSpec("home", "home.py", "홈", "", "HOME", "home",
             "주요 방산 전자부품 수출입 및 국산화 현황",
             "분석 대상 품목군의 수입 규모와 공급국 집중도, 조달 · 국산화 현황을 요약합니다"),
    PageSpec("trade", "pages/1_수출입_현황.py", "① 수출입 현황", "import", "① 수출입 현황", "bar_chart",
             "① 수출입 현황",
             "분석 대상 품목군을 어느 나라에서 얼마나 수입하고, 어느 나라로 얼마나 수출하는지 봅니다"),
    PageSpec("parts", "pages/3_조달_국산화_근거.py", "③ 조달·국산화 근거", "parts", "③ 조달·국산화 근거", "inventory_2",
             "③ 조달·국산화 근거",
             "전자 군급별 국외 조달계획과 국산화를 마친 부품, 국내 조달이 이뤄지는 방식을 봅니다"),
    PageSpec("table", "pages/4_검토_목록.py", "④ 검토 목록", "table", "④ 검토 목록", "table_rows",
             "④ 검토 목록",
             "분석 대상 품목군을 수입 집중도(HHI)가 높은 순으로 한 표에서 비교합니다 — 우선순위를 정한 목록은 아닙니다"),
    PageSpec("background", "pages/2_국외조달_예산_배경.py", "② 국외조달 예산 · 배경", "background", "② 국외조달 예산 · 배경",
             "account_balance", "② 국외조달 예산 · 배경",
             "국외조달 계획의 예산과 건수, 그 배경인 국방 R&amp;D 예산 · 국내 생산 기반 · 국방반도체 정책을 봅니다"),
    PageSpec("info", "pages/5_데이터_정보.py", "⑤ 데이터 정보", "info", "DATA INFO", "folder_open",
             "⑤ 데이터 정보",
             "화면의 숫자가 어디서 왔고 어떻게 계산했으며, 무엇을 뜻하지 않는지 적었습니다"),
    PageSpec("search", "pages/6_조회.py", "조회", "search", "조회", "search",
             "조회",
             "조건을 골라 원하는 차트를 만들고, 표와 그림으로 내려받습니다 — 조건은 고르는 값만 씁니다(자유 입력 없음)"),
)
SPEC_BY_KEY: dict[str, PageSpec] = {s.key: s for s in PAGE_SPECS}

# 표시 순서(CLAUDE.md 핵심 설계 제약, 09-17 교수 피드백): 홈 · ① 수출입 현황 · ② 국외조달 예산(배경) · ③ 근거 · ④ 검토 목록 · 조회 · ⑤ 데이터 정보
# 화면 번호 = 표시 순번(2026-09-24 사용자). 문서의 페이지 키(핵심 ① · 배경 ⓪ · 핵심 ② · 핵심 ③)와 다르다 — 대응표 dashboard/specs/00_common.md §1
NAV_ORDER: tuple[str, ...] = ("home", "trade", "background", "parts", "table", "search", "info")
GNB_ORDER: tuple[str, ...] = tuple(k for k in NAV_ORDER if k != "search")

_ZONE = re.compile(r'zone\(\s*"([a-z0-9_]+)"\s*,\s*"([^"]+)"\s*\)')


@lru_cache(maxsize=None)
def sections(key: str) -> tuple[tuple[str, str], ...]:
    """페이지의 블록 (키, 이름) — 파일에 적힌 zone("키", "이름") 순서. 홈은 맨 앞에 첫 화면(Main)을 붙인다."""
    found = tuple(dict.fromkeys(_ZONE.findall((APP / SPEC_BY_KEY[key].file).read_text(encoding="utf-8"))))
    return ((("main", "Main"),) if key == "home" else ()) + found


def pages() -> dict[str, st.Page]:
    """키 → st.Page. 부를 때마다 새로 만든다 — main.py 는 한 실행에서 한 번 만든 dict 를 navigation · 메뉴에 같이 넘긴다."""
    out: dict[str, st.Page] = {}
    for s in PAGE_SPECS:
        if s.url_path:
            out[s.key] = st.Page(APP / s.file, title=s.title, url_path=s.url_path)
        else:
            out[s.key] = st.Page(APP / s.file, title=s.title, default=True)
    return out


def current_key(pg: st.Page) -> str:
    """st.navigation 이 고른 페이지 → 키(url_path 로 판정 — st.Page 는 실행마다 새로 만든다)."""
    return next(s.key for s in PAGE_SPECS if s.url_path == pg.url_path)
