"""v2 메뉴 레지스트리 — 홈 + 대분류 4개 · 소분류(한 소분류 = 한 화면). 메뉴 순서 · 이름 · 주소는 이 파일 한 곳에서 고친다.

명세: 공동작업 저장소 app/specs/10_home.md · 11~14_cat_*.md · 00_common.md §4-1(2026-09-30 교수 피드백).
주소 = /{대분류 키}-{소분류 키}. 화면 파일 = dashboard/screens/{대분류 키}_{소분류 키}.py
"""
from __future__ import annotations

from typing import NamedTuple


class Sub(NamedTuple):
    key: str        # 소분류 키 — 주소 · 파일 이름에 쓴다
    name: str       # 왼쪽 메뉴 · 펼침 메뉴 이름
    question: str   # 이 화면이 답하는 질문(명세 §3 소분류 표)


class Cat(NamedTuple):
    key: str        # 대분류 키
    no: str         # 화면 번호 ①~④
    name: str       # 대분류 이름
    question: str   # 이 대분류가 답하는 질문(명세 §1 첫 줄) — 서브 배너 부제 · 홈 이야기 카드
    who: str        # 주로 찾는 분(타겟 3그룹, 순위 없음)
    icon: str       # Material Symbols 이름
    subs: tuple[Sub, ...]


CATS: tuple[Cat, ...] = (
    Cat("parts", "①", "부품 현황", "13개 품목군을 어디서 얼마나 들여오고 내보내나", "정책·예산 · 연구·분석", "inventory_2", (
        Sub("code", "HS코드란", "HS(류 · 호 · 소호)는 무엇이고 13개 품목군은 그 안의 어디인가"),
        Sub("summary", "종합 현황표", "13개 품목군을 한 표로 보면 어떤가"),
        Sub("trade", "수출입 현황", "연도 · 국가별로 어떻게 바뀌었나"),
        Sub("conc", "공급국 집중도 변화", "수입 쏠림은 어떻게 바뀌었나"),
        Sub("detail", "상세 조회", "조건을 골라 직접 보고 내려받기"),
    )),
    Cat("fsc", "②", "군급 분류와 조달", "군수품 분류(군급)로 보면 전자부품을 해외에서 무엇을 조달하려 하나",
        "방산 중소·벤처 · 정책·예산", "category", (
        Sub("code", "군급코드란", "군(FSG) · 군급(FSC)은 무엇이고 어떤 관계인가"),
        Sub("plan", "군급별 국외 조달계획", "전자 군급별로 몇 건을 해외에서 조달하려 하나"),
        Sub("army", "소요군별", "어느 소요군이, 어느 해에 요구하나"),
        Sub("detail", "상세 조회", "조건을 골라 직접 보고 내려받기"),
    )),
    Cat("loc", "③", "국산화 현황", "그중 무엇을 국산화했나", "방산 중소·벤처 · 정책·예산", "build", (
        Sub("done", "국산화 완료 부품", "어느 군급에서 몇 개를 국산화했나"),
        Sub("pair", "조달계획과 나란히", "해외 조달계획이 많은 군급과 국산화한 군급은 어떻게 다른가"),
        Sub("detail", "상세 조회", "조건을 골라 직접 보고 내려받기"),
    )),
    Cat("bg", "④", "배경과 자료", "왜 보고, 무엇으로 만들었나", "연구·분석 · 정책·예산", "account_balance", (
        Sub("policy", "정책 · 예산 배경", "정책은 어떻게 흘러왔고 예산은 어떻게 바뀌었나"),
        Sub("industry", "국내 생산 기반", "국내 생산 기반은 어떤가"),
        Sub("domestic", "국내 조달(부록)", "국내 조달은 어떤 방식으로 이뤄지나"),
        Sub("source", "데이터 출처 · 검증", "숫자는 어디서 왔고 무엇을 뜻하지 않는가"),
    )),
)
CAT_BY_KEY = {c.key: c for c in CATS}


def page_key(cat: str, sub: str) -> str:
    """페이지 키 = 주소 = 「대분류-소분류」(예 parts-summary). 홈은 "home"."""
    return f"{cat}-{sub}"


def split(key: str) -> tuple[Cat | None, Sub | None]:
    """페이지 키 → (대분류, 소분류). 홈이면 (None, None)."""
    if key == "home":
        return None, None
    c, s = key.split("-", 1)
    cat = CAT_BY_KEY[c]
    return cat, next(x for x in cat.subs if x.key == s)


# 이야기 연결 — 상세 조회 앞 마지막 소분류 아래에 「다음 →」(00_common.md §4-1). ④는 홈으로 돌아간다
NEXT = {"parts-conc": "fsc-code", "fsc-army": "loc-done", "loc-pair": "bg-policy", "bg-source": "home"}
