"""K-Defense 대시보드 — 진입점(온라인 배포 화면, https://defense-trade.streamlit.app). 숫자는 운영 DB(AWS RDS).

메뉴: 홈 → 소개 → 전자부품 현황 → 군급 분류와 조달 → 국산화 현황 → 배경과 자료.
- 홈 · 소개: 첫 화면과 소개 글(선정 규칙 · 13개 품목 · 무기체계 분류 · 공개 사례 — weapon_context.py).
- 나머지 소분류: dashboard/screens/*.py 를 그 자리에서 실행한다(값은 dashboard/screens/rds.py → dashboard/db.py, 캐시 1시간).
  대분류마다 소분류를 한 페이지에 이어 그리므로, 화면 파일끼리 위젯 key 가 겹치면 안 된다(2026-09-30 확인 — 겹침 없음).
- 상세 조회: dashboard/datacenter_viz.py(실데이터)를 자료 유형 하나로 고정(screens/parts.py 의 detail).

화면 틀: 국방과학연구소 누리집(add.re.kr/kps) 방식 · 흰색 + 파랑(동현님 새 디자인, dashboard/demo/K-Defense_brandnew.py).
  - 사이드바 대신 흰 머리글 + 상단 메뉴. 메뉴에 커서를 올리면 모든 페이지의 소분류 목록이 파란 띠로 펼쳐진다
  - 서브 배너 → 왼쪽 메뉴(이 페이지의 소분류) + 본문. 소분류는 주소의 ?sec= 로 고른다

실행:  streamlit run dashboard/main.py
배포본: 공동작업 저장소(kimhh080888-blip/Defense_Dashboard)의 app/KDD_v2.py 와 같은 코드다(경로만 app/ ↔ dashboard/).
  2026-10-01 양쪽에서 KDD_v1 에서 복사돼 남아 있던 샘플 화면 · 샘플 데이터 코드를 걷어냈다. 파일 대응은 dashboard/README.md.
설계도판(숫자 없는 목업): dashboard/demo/KDD_v2.py · 기록 docs/report/app/kdd-v2-mockup-2026-09-30.md
"""
from __future__ import annotations

import base64
import contextlib
import json
import math
import time
from html import escape
from string import Template

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# dashboard/ (db · kdesign · ui · datacenter_viz · weapon_context) · dashboard/screens (rds · parts · menu · 소분류 화면)
import runpy
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent
SCREENS_DIR = APP_DIR / "screens"
for _p in (str(APP_DIR), str(SCREENS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from weapon_context import CASES, SYSTEMS  # noqa: E402  소개 「어디에 쓰이나」 — 무기체계 분류 · 공개 사례

# CSS · JS · 인트로 HTML 은 static/ 파일에 둔다. CSS 안의 ${이름} 자리는 불러올 때 파이썬 값(색 · 폭 등)으로 채운다
STATIC_DIR = APP_DIR / "static"


def static(name: str) -> str:
    """static/ 파일(CSS · JS · HTML)을 그대로 읽는다."""
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def css(name: str, **vals) -> str:
    """static/*.css 를 <style> 로 감싼다. ${이름} 자리는 vals 로 채운다."""
    text = static(name)
    return "<style>" + (Template(text).substitute(vals) if vals else text) + "</style>"


def script(name: str) -> str:
    """static/*.js 를 <script> 로 감싼다(보이지 않는 components.html 안에서 바깥 화면을 다루는 조각)."""
    return "<script>" + static(name) + "</script>"

# 브라우저 탭 아이콘 — 머리글 로고와 같은 방패(Material Symbols Rounded 의 shield 원본 도형 · 흰색) + 가운데 태극.
# 태극 위치 · 크기 · 회전은 머리글과 같은 비율: 방패 글자칸(38px) 기준 가로 50%(+0.3px) · 세로 46% · 지름 15px · 시계방향 40도
_FAV_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960">'
    '<path fill="#ffffff" d="M467-85q-6-1-12-3-135-45-215-166.5T160-516v-189q0-25 14.5-45t37.5-29l240-90q14-5 28-5t28 5l240 90'
    'q23 9 37.5 29t14.5 45v189q0 140-80 261.5T505-88q-6 2-12 3t-13 1q-7 0-13-1Zm13-79q104-33 172-132t68-220v-189l-240-90-240 90'
    'v189q0 121 68 220t172 132Zm0-316Z"/>'
    '<g transform="translate(487.6 -518.4) rotate(40) scale(17.22)">'
    '<circle r="10" fill="#0047A0"/>'
    '<path d="M-10 0A10 10 0 0 1 10 0A5 5 0 0 0 0 0A5 5 0 0 1-10 0Z" fill="#CD2E3A"/>'
    '<circle r="10" fill="none" stroke="#fff" stroke-width="1.6"/></g></svg>')
FAVICON = "data:image/svg+xml;base64," + base64.b64encode(_FAV_SVG.encode()).decode()

st.set_page_config(page_title="K-Defense 대시보드 — 훈수안이조", page_icon=FAVICON, layout="wide",
                   initial_sidebar_state="collapsed")

# ════════════════════════════════════════════════════════════════════════════
# 1. 색 토큰 · CSS
# ════════════════════════════════════════════════════════════════════════════
BG, PANEL, PANEL2, LINE = "#eef3fb", "#ffffff", "#eef2f9", "#dde5f2"
TEXT, MUTED, ACCENT = "#16233f", "#6b7a99", "#2b6ef6"
NAVY, NAVY2 = "#003899", "#003899"   # 메뉴 사이드바 바탕 — 선명한 파랑(단색)
UP, DOWN = "#12b76a", "#f04438"

# ── 글꼴 ────────────────────────────────────────────────────────────────────
# 본문 · 사이드바 모두 Pretendard(각진 고딕)를 쓴다.
SIDE_STACK = "Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif"

# @import 는 다른 규칙보다 반드시 앞에 와야 브라우저가 읽는다(뒤에 두면 통째로 무시된다).
_PRETENDARD = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
_FONTS = f"@import url('{_PRETENDARD}');\n"


# 화면 배율 — 누가 열든(브라우저 100% 기준) 전체를 이만큼 키워 보인다. 크롬 확대와 같은 방식이라 비율은 그대로다.
APP_ZOOM = 1.1

# Plotly 차트 · 표(st.dataframe)는 화면 배율 아래에서 마우스 위치를 잘못 읽는다(오른쪽 막대일수록 옆 막대가 잡힘).
# 그래서 이 둘 안쪽만 배율을 되돌린다. 칸 크기는 바깥(배율 적용)에서 정해져 차지하는 자리는 똑같이 커진다.
CSS = css("base.css", FONTS=_FONTS, APP_ZOOM=APP_ZOOM, BG=BG, PANEL=PANEL, PANEL2=PANEL2, LINE=LINE, TEXT=TEXT,
          MUTED=MUTED, ACCENT=ACCENT, NAVY=NAVY, NAVY2=NAVY2, UP=UP, DOWN=DOWN)

st.html(CSS)

# ── 라이트 테마 고정(위젯) ───────────────────────────────────────────────────
# 저장소의 .streamlit/config.toml(운영 앱용 다크 테마) 아래에서 열거나, 테마 설정 없이 OS 다크모드에서 열면
# 버튼 · 분석영역/HS 선택 · 체크박스 · 선택창이 어두운 바탕 · 흰 글씨 · 다크 강조색으로 그려졌다(조원 PC 에서 본 증상).
# 이 파일만 받아 실행해도 같은 화면이 나오게 테마가 칠하는 색을 여기서 직접 정한다.
# 아래 규칙보다 뒤에 오는 칸별 규칙(.st-key-… — 국가 칩 · 차트 유형 버튼 · ⓘ 단추)이 명시도가 같거나 높아 그대로 이긴다.
st.html(css("light_theme.css"))

# ── 막대·선 그래프 등장 연출(plotly) ─────────────────────────────────────────
# 막대는 왼쪽 것부터 차례로 바닥에서 자라고(가로 막대는 왼쪽에서 뻗고), 선은 왼쪽에서 오른쪽으로 그려진다.
# 옅은 그림자로 입체감을 준다. 차트가 새로 그려질 때(페이지 이동·창 크기 변경)마다 다시 재생된다.
_STAGGER = "\n".join(
    f".js-plotly-plot .barlayer .point:nth-child({i}) path{{animation-delay:{0.05 + i * 0.07:.2f}s}}\n"
    f".js-plotly-plot .barlayer .point:nth-child({i}) text{{animation-delay:{0.45 + i * 0.07:.2f}s}}"
    for i in range(1, 16))
CHART_ANIM = css("chart_anim.css", STAGGER=_STAGGER)
st.html(CHART_ANIM)

# ── 공급망 현황 표 · 핵심 지표 · HHI 게이지 · 탭 ─────────────────────────────
st.html(css("components.css"))


# ════════════════════════════════════════════════════════════════════════════
# 2. 공용 요소
# ════════════════════════════════════════════════════════════════════════════


# 라우터(맨 아래)가 페이지를 돌리기 전에 정한다 — landing: Home 의 Main(첫 화면)만 그리는 중인지
_SEC = {"sel": None, "shown": False, "landing": False}


def zone(key: str, tag: str):
    """페이지 안 블록 하나. 한 페이지의 블록을 위에서부터 차례로 모두 그리고, 블록마다 제목을 단다.
    Home 의 Main 은 첫 화면 전용이라 Main 을 볼 때는 Main 만, 다른 블록을 볼 때는 Main 만 뺀다.
    `for _ in zone("kpi", "한눈에 보는 KPI"):` 로 쓴다 — 그릴 블록이면 한 번, 아니면 0번 돈다."""
    if (key == "main") != _SEC["landing"]:
        return
    _SEC["shown"] = True
    with st.container(key=f"zone_{key}"):
        if key != "main":
            st.html(f'<div class="sec-h"><h2>{tag}</h2></div>')
        yield


# ════════════════════════════════════════════════════════════════════════════
# 3-2. 인트로 — 깨끗한 지구본(국가 표시·화살표 없음) 한 장
#      접속 직후 화면 전체를 덮었다가 스스로 사라지고, 그 밑에서 대시보드가 드러난다.
#      세션당 한 번만 뜬다(필터를 바꿔 다시 그려질 때는 뜨지 않는다). 새로고침하면 다시 본다.
# ════════════════════════════════════════════════════════════════════════════
_INTRO = static("intro.html")

INTRO_SEC = 0.5          # 지구본이 머무는 시간(초). 이 뒤 0.4초 동안 사라져 전체 약 1초


def intro_screen() -> None:
    """세션당 한 번, 화면 전체를 덮는 인트로. CSS 애니메이션으로 스스로 사라지므로
    서버를 멈추거나(time.sleep) 다시 그리지(st.rerun) 않는다 — 그 사이 밑에서 대시보드가 다 그려진다."""
    if st.session_state.get("intro_done"):
        return
    st.session_state["intro_done"] = True
    with st.container(key="intro"):
        components.html(_INTRO.replace("__H__", "680").replace("__SEC__", str(INTRO_SEC)),
                        height=680, scrolling=False)
    st.html(css("intro_fade.css", FADE_AT=INTRO_SEC + .1))

# ── 분석 대상 품목(HS) — 선정 근거 · 계열 · 방산 용도 ─────────────────────────────
# 분석 대상 13개(진입 = R1 군용전용 또는 R2 항공·항행, 2026-09-21 확정). 나머지 11개는 배경 자료
TARGET_HS = {"841191", "852610", "852691", "852910", "852990", "854231", "854233", "854239",
             "880730", "901410", "901420", "901480", "901490"}

HS_BASIS = [
    ("854231", "프로세서·컨트롤러(IC)", "반도체", "HSK-군용;HSK-항공/항행;전략물자-DU;B2-FSC"),
    ("854233", "증폭기(IC)", "반도체", "HSK-군용;HSK-항공/항행;전략물자-DU;B2-FSC"),
    ("854239", "기타 집적회로", "반도체", "HSK-군용;HSK-항공/항행;전략물자-DU;B2-FSC"),
    ("854110", "다이오드", "반도체", "전략물자-DU;B2-FSC"),
    ("854121", "트랜지스터(1W 미만)", "반도체", "전략물자-DU;B2-FSC"),
    ("854129", "트랜지스터(1W 이상)", "반도체", "전략물자-DU;B2-FSC"),
    ("854159", "기타 반도체 디바이스", "반도체", "A6;B2-FSC"),
    ("854142", "광전지(모듈 미조립)", "반도체", "팀판단"),
    ("852691", "무선항행용 무선기기", "전자부품", "HSK-항공/항행;전략물자-DU;B2-FSC"),
    ("852610", "레이더 기기", "전자부품", "HSK-항공/항행;전략물자-DU;B2-FSC"),
    ("852990", "통신·레이더 기기 부분품", "전자부품", "HSK-항공/항행;전략물자-DU;B2-FSC"),
    ("901380", "기타 광학기기", "전자부품", "전략물자-DU;B2-FSC"),
    ("901420", "항공·우주용 항행기기", "전자부품", "HSK-항공/항행;전략물자-DU"),
    ("848620", "반도체 제조용 기계", "소재장비", "팀판단"),
    ("847180", "자동자료처리기계 단위기기", "전자부품", "팀판단"),
    ("841191", "터보제트·터보프롭 부분품", "소재장비", "HSK-항공/항행"),
    ("880730", "항공기·헬리콥터 부분품", "소재장비", "HSK-항공/항행;전략물자-DU"),
    ("852692", "무선원격조종기기", "전자부품", "전략물자-DU;B2-FSC"),
    ("852560", "송수신 겸용 무선기기", "전자부품", "전략물자-DU;B2-FSC"),
    ("851762", "음성·영상·데이터 송수신기기", "전자부품", "팀판단"),
    ("901480", "기타 항행용 기기", "전자부품", "HSK-항공/항행;전략물자-DU;B2-FSC"),
    ("852910", "안테나와 그 부분품", "전자부품", "HSK-항공/항행;전략물자-DU"),
    ("901410", "방향탐지용 컴퍼스", "전자부품", "HSK-항공/항행;전략물자-DU"),
    ("901490", "항행용 기기 부분품", "전자부품", "HSK-항공/항행;전략물자-DU"),
]

# 분석 대상 13개(TARGET_HS)의 계열 · 방산 용도(한 줄 설명). 키 집합은 TARGET_HS 와 같아야 한다(아래 assert)
SYSTEM_FAMILY = {
    "841191": "소재장비", "880730": "소재장비",
    "852610": "레이더",
    "901420": "항공전자",
    "852691": "항법", "901410": "항법", "901480": "항법", "901490": "항법",
    "852910": "통신·레이더 부분품", "852990": "통신·레이더 부분품",
    "854231": "반도체", "854233": "반도체", "854239": "반도체",
}

DEFENSE_USE_KO = {
    "841191": "항공기 엔진 핵심 수입부품",   # 원래 defense_use_ko는 "배경 자료(분석 대상 아님)"이라 모순돼서 짧은 태그로 대체(팀 결정)
    "880730": "항공기 부품(HS2022 신설, 구 8803.30)",  # 위와 같은 이유로 대체
    "852610": "탐지·추적·사격통제 레이더 완제품·모듈(대포병·조기경보·함정 레이더 등 A7 조달계획 대표품명에 반복 등장)",
    "852691": "GPS/INS 항법 수신기·항법 보조장비",
    "852910": "레이더·전술통신·데이터링크의 안테나·반사기·급전 부분품(팀 판단)",
    "852990": "안테나·T/R 모듈·송수신 부분품(레이더·통신 공통)",
    "854231": "레이더 신호처리·사격통제·항전 컴퓨터의 프로세서·FPGA·MCU. 무기체계 첨단 반도체 98.9% 해외 의존(A6)",
    "854233": "레이더 송수신(T/R)·전술통신의 RF/전력 증폭 IC",
    "854239": "ADC/DAC·믹스드시그널·특수목적 IC(전자전·신호처리)",
    "901410": "항공기·함정·차량 항법용 자기·자이로 컴퍼스(팀 판단)",
    "901420": "항공기·유도무기 항행 계기(에비오닉스)",
    "901480": "선박·지상 항법기기(함정 음탐·항법 계열, A7 조달계획 대표품명)",
    "901490": "항법 기기(9014 계열)의 부분품(팀 판단)",
}

assert set(SYSTEM_FAMILY) == TARGET_HS, f"SYSTEM_FAMILY 키 ≠ TARGET_HS: {set(SYSTEM_FAMILY) ^ TARGET_HS}"
assert set(DEFENSE_USE_KO) == TARGET_HS, f"DEFENSE_USE_KO 키 ≠ TARGET_HS: {set(DEFENSE_USE_KO) ^ TARGET_HS}"


# ════════════════════════════════════════════════════════════════════════════
# 5. 화면
# ════════════════════════════════════════════════════════════════════════════


# ── Main(첫 화면) — 국방과학연구소 첫 화면처럼 큰 사진 + 글씨 ──────────────────────
# 사진은 Unsplash 무료 사진(상업적 사용 가능 · 출처 표기 선택)을 주소로 불러온다 — 인터넷이 없으면 사진 자리는 파란 바탕만 보인다
def _ph(pid: str, w: int = 1600) -> str:
    return f"https://images.unsplash.com/photo-{pid}?auto=format&fit=crop&w={w}&q=70"


MAIN_SLIDES = [_ph("1551796880-ddd03f861ae7", 2000),    # 푸른 하늘의 전투기
               _ph("1685178362030-9b574eb9ae7c", 2000),  # 항공모함
               _ph("1610457642191-05328cdf34ff", 2000)]  # 밤하늘 레이더
MAIN_CARDS = [  # (url, 소분류, 사진, 분류, 제목, 설명) — 이야기 순서. 소개는 첫 화면 단추 · 상단 메뉴로만(09-30 사용자)
    ("parts", "summary", _ph("1592659762303-90081d34b277", 900), "PARTS", "전자부품 현황",
     "분석 대상 13개 품목군을 어느 나라에서 얼마나 들여오고 내보내는지, 공급국 집중도와 함께 봅니다."),
    ("fsc", "code", _ph("1578575437130-527eed3abbec", 900), "CLASSIFICATION", "군급 분류와 조달",
     "군수품 분류(군 FSG · 군급 FSC)로 전자 군급의 국외 조달계획과 국내 계약 · 입찰을 봅니다."),
    ("local", "done", _ph("1587293852726-70cdb56c2866", 900), "LOCALIZATION", "국산화 현황",
     "군(FSG) 58 · 59 · 60에 속한 전자 군급 부품 중 국산화개발을 마친 부품을 군급별로 봅니다."),
    ("background", "policy", _ph("1676090438227-141cac59c405", 900), "BACKGROUND", "배경과 자료",
     "정책 흐름과 예산, 국내 생산 기반, 그리고 이 숫자들이 어디서 왔는지 봅니다."),
]

MAIN_CSS = css("landing.css")


# 큰 사진 넘기기 — st.html 은 스크립트를 돌리지 않아, 보이지 않는 components.html 안에서 바깥 화면(window.parent)을 다룬다.
# 6초마다 다음 장, ‹ › 를 누르면 바로 이전 · 다음 장으로 가고 6초를 처음부터 다시 센다. 보던 장 번호는 다시 그려져도 이어진다
MV_JS = script("landing_slider.js")


def main_landing() -> None:
    """Main — 큰 사진(자동 전환) · 소개와 바로가기 · 주요 분석 사진 카드 · 숫자 띠 · 데이터 갱신 목록."""
    home = page_of["home"][0]
    pad = f"max(32px, calc((100% - {WRAP}px) / 2 + 32px))"
    # <style> 만 있는 st.html 은 「이벤트 칸」으로 가서 대화상자(데이터 정보 등)를 열 때 지워진다 — 빈 표식을 붙여 본문 칸에 남긴다
    with st.container(key="main_css"):
        st.html(MAIN_CSS.replace("__PAD__", pad) + '<i class="main-css-mark"></i>')

    # 1) 큰 사진 + 글씨
    slides = "".join(f'<div class="mv-sl{" on" if i == 0 else ""}" style="background-image:url(\'{u}\')"></div>'
                     for i, u in enumerate(MAIN_SLIDES))
    arrow = '<button class="mv-arr {0}" type="button" aria-label="{1}"></button>'   # 화살표 모양은 CSS(::before)로 — st.html 이 svg 를 지운다
    st.html(f'<div class="mv">{slides}<div class="mv-txt"><small>K-DEFENSE DATA PLATFORM</small>'
            '<h1>데이터로 알아보는<br>국방 전자부품</h1><div class="en">Data-Driven Defense Electronics</div>'
            '<p>방산 전자부품의 수입 집중도 · 국산화 · 조달 현황을<br>하나의 화면에서 확인하고, 더 나은 결정을 돕습니다.</p></div>'
            '<div class="mv-bar">' + arrow.format("prev", "이전 사진") + '<div class="tr run"></div>'
            + arrow.format("next", "다음 사진") + '</div></div>')
    with st.container(key="mvjs"):
        components.html(MV_JS, height=0)
    with st.container(key="mv_cta", horizontal=True, vertical_alignment="center"):
        st.page_link(page_of["intro"][0], label="이야기 시작하기", icon=":material/play_arrow:", query_params={"sec": "elec"})
        st.page_link(page_of["parts"][0], label="직접 조회하기", icon=":material/search:", query_params={"sec": "detail"})

    # 2) 왜 전자부품인가 — 이유(본문) + 그 이유를 확인하는 화면 네 곳(아이콘). 아이콘은 이야기 순서 ① → ① → ③ → ④
    #    98.9% 는 인용(국방반도체 발전전략 본문 · 2023-12 조사) — 본문에는 각주 표시(*)만, 출처 · 한계는 아래 각주 줄에.
    #    * · 98.9% 에 마우스를 올리면 아래 각주 줄이 파란 글씨로 커진다(.mi-hit — CSS :has)
    #    「의존도」 · 「공급망」은 쓰지 않는다
    #    「13개 중 5개」는 RDS(screens/rds.py conc — 전자부품 현황 종합 현황표와 같은 계산)에서. 조회 실패면 숫자 없는 문장
    import rds as R                                  # dashboard/screens/rds.py
    from db import DBConfigError
    from sqlalchemy.exc import SQLAlchemyError
    try:
        _y = R.full_years()[-1]
        _c = R.conc((_y,))
        why_top1 = (f'분석 대상 {len(_c)}개 품목군 중 <b>{int((_c["top1_share"] >= 0.5).sum())}개</b>는 '
                    f'{_y}년 수입액의 절반 이상을 한 나라에서 들여왔습니다(민수 포함). ')
    except (DBConfigError, SQLAlchemyError, pd.errors.DatabaseError):
        why_top1 = '분석 대상 품목군 여럿은 수입액의 절반 이상을 한 나라에서 들여왔습니다(민수 포함). '
    with st.container(key="mi", horizontal=True):
        st.html('<div class="mi-txt"><div class="k">WHY ELECTRONICS</div>'
                '<h2>왜 <em>전자부품</em>인가?</h2>'
                '<p>탐지 · 통신 · 항법 · 제어 같은 무기체계의 핵심 기능은 반도체와 전자부품이 맡습니다. '
                '그런데 무기체계에 들어가는 반도체의 <span class="mi-hit"><sup class="mi-ref">*</sup><b>98.9%</b></span>는 해외에서 들여오고, '
                + why_top1 +
                '우리 정부도 2024년 국방반도체 발전전략, 2026년 국방반도체법으로 반도체와 부품국산화 사업으로 전자부품 전반의 국산화를 추진하고 있습니다.</p>'
                '<p>이 대시보드는 공개 데이터로 <b>소개 → 전자부품 현황 → 군급 분류와 조달 → 국산화 현황 → 배경과 자료</b>를 차례로 보여 줍니다.</p>'
                '<small class="mi-src">* 무기체계 적용 반도체의 해외 도입 비중 — 국방반도체 발전전략(2024-11)이 인용한 2023-12 조사 값입니다. '
                '팀이 계산한 값이 아니며 분모 기준은 확인하지 못했습니다.</small></div>')
        with st.container(key="mi_links", horizontal=True):
            for u, sec, label, icon in [("intro", "items", "13개 품목군은 무엇인가", "memory"),
                                        ("parts", "trade", "어느 나라에서 들여오나", "public"),
                                        ("local", "done", "무엇을 국산화했나", "build"),
                                        ("intro", "use", "어떤 무기체계에 쓰이나", "rocket_launch")]:
                st.page_link(page_of[u][0], label=label, icon=f":material/{icon}:", query_params={"sec": sec})

    # 3) 주요 분석 사진 카드
    st.html('<div class="mc-head"><h2><small>STORY</small>이야기 순서대로 보기</h2>'
            '<span>전자부품 현황부터 배경과 자료까지 차례로 이어집니다</span></div>')
    with st.container(key="mcards", horizontal=True):
        for i, (u, sec, img, cat, title, desc) in enumerate(MAIN_CARDS):
            with st.container(key=f"mc_{i}"):
                st.html(f'<div class="mc-img"><b>{cat}</b><div style="background-image:url(\'{img}\')"></div></div>'
                        f'<div class="mc-body"><h3>{title}</h3><p>{desc}</p></div>')
                st.page_link(page_of[u][0], label="자세히 보기", icon=":material/arrow_forward:", query_params={"sec": sec})


# 왼쪽 메뉴(스크롤형) — 소분류 링크(a.lnb-a)를 누르면 페이지를 다시 열지 않고 그 소분류 칸(.st-key-sub_*)으로 부드럽게
# 스크롤한다. 스크롤하면 지금 보이는 소분류를 ✓(.on) 로 · 위쪽 경로(.crumb b)도 그 이름으로 바꾼다.
# data.go = [소분류, 번호] — 다른 페이지 · 위쪽 메뉴에서 ?sec= 로 들어왔을 때 열린 뒤 한 번만 그 소분류로 간다
_LNB_JS = static("lnb_scroll.js")
_LNB = st.components.v2.component("kd_lnb_scroll", html="<span></span>", js=_LNB_JS)


# ════════════════════════════════════════════════════════════════════════════
# 페이지 본문 — 대분류 한 페이지에 소분류를 위에서 아래로 이어 그린다(왼쪽 메뉴는 그 소분류로 스크롤).
# ════════════════════════════════════════════════════════════════════════════
def _run_sub(subs: dict) -> None:
    """소분류 화면 함수를 순서대로 모두 불러 위에서 아래로 이어 그린다(스크롤형).
    소분류마다 sub_{키} 칸으로 감싸 왼쪽 메뉴가 그 칸으로 스크롤해 간다(_LNB_JS)."""
    for k, fn in subs.items():
        with st.container(key=f"sub_{k}"):
            fn()


def page_home() -> None:
    for _ in zone("main", "Main"):
        main_landing()


# ════════════════════════════════════════════════════════════════════════════
# 소개 — 소분류마다 「질문 → 이 화면이 말하려는 것 → 설명 재료 → 읽을 때 주의」(선정 규칙 · 품목 설명 · 무기체계 분류 · 공개 사례).
# ════════════════════════════════════════════════════════════════════════════
STORY_CSS = css("story.css")

def _mk_css() -> None:
    # <style> 만 있는 st.html 은 이벤트 칸으로 빠지므로 빈 표식을 붙여 본문 칸에 남긴다(main_landing 과 같은 방법)
    with st.container(key=f"mk_css_{url}"):
        st.html(STORY_CSS + '<i class="mk-mark"></i>')


def story_screen(key: str, title: str, question: str, message: str, notes: tuple = (), extra: str = "") -> None:
    """소분류 한 화면 — 질문 · 이 화면이 말하려는 것 · (설명 재료 extra) · 읽을 때 주의."""
    for _ in zone(key, title):
        st.html(f'<div class="mk-q"><b>Q.</b>{question}</div>'
                f'<div class="mk-msg"><small>이 화면이 말하려는 것</small><b>{message}</b></div>')
        if extra:
            st.html(extra)
        if notes:
            st.html('<div class="mk-note"><b>읽을 때 주의</b><ul>' + "".join(f"<li>{n}</li>" for n in notes) + '</ul></div>')


# ── ① 왜 이 부품인가 ────────────────────────────────────────────────────────
_FUNCS = [("radar", "탐지", "레이더 · 전자광학으로 표적을 찾고 쫓습니다", "레이더 기기 · 증폭 IC"),
          ("cell_tower", "통신", "부대와 체계가 정보를 주고받습니다", "안테나 · 송수신 부분품"),
          ("explore", "항법", "위치와 자세를 알아 길을 찾습니다", "GPS/INS 수신기 · 항행 계기"),
          ("memory", "제어", "신호를 처리해 사격과 비행을 제어합니다", "프로세서 · FPGA · 특수목적 IC")]


def _why_elec() -> None:
    cards = "".join(f'<div class="mk-card"><span class="ms">{ic}</span><h4>{n}</h4><p>{d}</p>'
                    f'<p style="margin-top:6px"><small>맡는 부품</small>{p}</p></div>' for ic, n, d, p in _FUNCS)
    story_screen(
        "elec", "왜 전자부품인가",
        "무기체계에서 전자부품은 무슨 일을 하나",
        "무기체계의 눈 · 귀 · 두뇌(탐지 · 통신 · 항법 · 제어)는 전자부품이 맡는다. 그런데 무기체계에 들어가는 반도체의 대부분을 해외에서 들여온다.",
        extra=f'<div class="mk-cards">{cards}</div>',
        notes=("「반도체 98.9% 해외 도입」은 국방반도체 발전전략(2024-11)이 인용한 2023-12 조사 값 — 팀 계산값 아님 · 분모 기준 미확인",))


def _why_select() -> None:
    # 한 줄 깔때기는 1,003 → 52 → 13 만. 수집 24 는 진입 52 의 부분집합이 아니라서 층으로 넣지 않고 아래 한 줄로 따로 적는다
    # (plan-revision-2026-09-23.md §2-1 · KDD_v1 HS_SELECT 와 같은 값)
    funnel = ('<div class="mk-funnel">'
              '<div style="width:92%">HS 6단위 전체 1,003개<small>84 · 85 · 88 · 90류</small></div><i>▼</i>'
              '<div style="width:64%">진입 기준 충족 52개<small>군용 전용 세분류 또는 세분류 이름에 전문 용도 명시</small></div><i>▼</i>'
              '<div style="width:38%;background:#0f2f73"><b>분석 대상 13개 품목군</b><small>전자 계열만 — 「항공기용」 세분류로 걸린 기계 · 전장 계열 39개 제외</small></div>'
              '</div>'
              '<div class="mk-q" style="text-align:center">수집은 24개 = 분석 대상 13개 + 배경 자료 11개 (배경 11개는 진입 52개 밖에서 따로 모았다)</div>')
    story_screen(
        "select", "어떻게 골랐나",
        "1,003개 품목 중 왜 이 13개인가",
        "무역 통계의 공식 분류(HS)에서 군용 · 항공 · 항행 전용으로 나뉜 품목만 골랐다 — 팀이 임의로 고른 것이 아니다.",
        extra=funnel,
        notes=("HS 품목과 군급(FSC)을 잇는 공식 연계표가 없어 R4(국산화개발품목 FSC 대응)는 규칙에서 뺐다(09-21 결정)",
               "무역 값은 국가 전체 수입 · 수출(민수 포함)이다 — 「방산 수입」이 아니다"))


def _why_items() -> None:
    name = {hs: n for hs, n, *_ in HS_BASIS}
    groups = [("반도체", "두뇌 — 신호 처리 · 증폭", ["854231", "854233", "854239"]),
              ("전자부품", "눈 · 귀 · 길잡이 — 레이더 · 통신 · 항법",
               ["852610", "852910", "852990", "852691", "901410", "901420", "901480", "901490"]),
              ("소재장비", "전자부품은 아님 — 항공기 · 엔진 부품", ["841191", "880730"])]
    html = ""
    for g, sub, hss in groups:
        warn = " warn" if g == "소재장비" else ""
        html += (f'<div class="mk-grp">{g} {len(hss)}개<span>{sub}</span></div><div class="mk-cards">'
                 + "".join(f'<div class="mk-card{warn}"><small>HS {hs} · {SYSTEM_FAMILY[hs]}</small><h4>{name[hs]}</h4>'
                           f'<p>{escape(DEFENSE_USE_KO[hs])}</p></div>' for hs in hss) + '</div>')
    story_screen(
        "items", "13개 품목군",
        "13개는 각각 어떤 부품인가",
        "13개는 반도체 3 · 전자부품 8 · 소재장비 2로 나뉜다. 이야기의 중심은 반도체와 전자부품 11개다.",
        extra=html,
        notes=("소재장비 2개(841191 · 880730)를 분석 대상에 계속 둘지는 미결 — 11개로 줄이면 이 화면과 ① 깔때기만 고치면 된다",))


# ── ⑤ 어디에 쓰이나 ─────────────────────────────────────────────────────────
_ROLE = [("memory", "반도체 3개", "신호 처리 · 사격통제 · 항전 컴퓨터", "화력 · 항공 · 감시정찰"),
         ("radar", "레이더 · 통신 부분품 3개", "표적 탐지 · 추적, 전술통신 · 데이터링크", "감시정찰 · 지휘통제통신"),
         ("explore", "항법 · 항공전자 5개", "위치 · 자세 측정, 항행 계기", "항공 · 함정 · 유도무기")]


def _use_role() -> None:
    cards = "".join(f'<div class="mk-card"><span class="ms">{ic}</span><h4>{n}</h4><p>{d}</p>'
                    f'<p style="margin-top:6px"><small>주로 쓰이는 무기체계 분야</small>{s}</p></div>' for ic, n, d, s in _ROLE)
    story_screen(
        "role", "부품이 하는 일",
        "13개 품목군은 무기체계의 어떤 기능을 맡나",
        "반도체는 두뇌, 레이더 · 통신 부분품은 눈과 귀, 항법 기기는 길잡이 — 모두 무기체계의 핵심 기능이다.",
        extra=f'<div class="mk-cards" style="grid-template-columns:repeat(3,minmax(0,1fr))">{cards}</div>',
        notes=("부품 종류의 일반적인 쓰임이다 — 특정 무기체계의 부품 목록(BOM)이나 수입 품목의 실제 사용처가 아니다",))


def _use_sys() -> None:
    cards = "".join(f'<div class="mk-card"><small>{c}</small><h4>{n}</h4><p>{d}</p>'
                    f'<p style="margin-top:6px;font-size:12px">{ex}</p></div>' for c, n, d, ex in SYSTEMS)
    story_screen(
        "sys", "무기체계 분류",
        "우리나라는 무기체계를 어떻게 나누나",
        "방위사업청 분류체계는 무기체계를 10개 대분류로 나눈다. 전자부품은 거의 모든 분류에 들어간다.",
        extra=f'<div class="mk-cards" style="grid-template-columns:repeat(5,minmax(0,1fr))">{cards}</div>',
        notes=("출처: 방위사업청 무기체계 분류체계(별표3)",))


def _use_cases() -> None:
    cards = "".join(f'<div class="mk-card"><small>{f} · {co}</small><h4>{sysn}</h4><p>{stt} · {when}<br>{desc}</p>'
                    f'<a href="{link}" target="_blank" rel="noopener">공식 발표 보기 ↗</a></div>'
                    for f, co, sysn, stt, when, desc, link in CASES)
    story_screen(
        "cases", "공개 사례",
        "국산 전자부품 · 무기체계는 실제로 어디까지 왔나",
        "KF-21 레이다, 항재밍 수신기처럼 국산 전자부품이 양산 · 수출까지 이어진 사례가 나오고 있다.",
        extra=f'<div class="mk-cards">{cards}</div>',
        notes=("각 사례는 기업 · 기관의 공개 발표다 — 분석 대상 13개 품목의 수입 · 조달 자료와 연결하지 않는다",))


def _intro_use() -> None:
    # 「어디에 쓰이나」 = 부품이 하는 일 · 무기체계 분류 · 공개 사례를 한 소분류에 차례로(KDD_v1 과 같음)
    _use_role()
    _use_sys()
    _use_cases()


def pg_intro() -> None:
    _mk_css()
    _run_sub({"elec": _why_elec, "select": _why_select, "items": _why_items, "use": _intro_use})


# 실데이터 화면 — dashboard/screens/{screen}.py 를 소분류 자리에서 실행(runpy — 매 실행 새로 그린다)
SCREENS = {
    "parts": {"summary": "parts_summary", "trade": "parts_trade", "conc": "parts_conc", "detail": "parts_detail"},
    "fsc": {"code": "fsc_code", "plan": "fsc_plan", "army": "fsc_army", "domestic": "bg_domestic", "detail": "fsc_detail"},
    "local": {"done": "loc_done", "pair": "loc_pair", "detail": "loc_detail"},
    "background": {"policy": "bg_policy", "industry": "bg_industry", "source": "bg_source"},
}
# 화면 끝 「다음 대분류로」(screens/menu.py NEXT) → v2 주소 · 소분류
_NEXT_V2 = {"parts-conc": ("fsc", "code"), "fsc-army": ("local", "done"), "loc-pair": ("background", "policy"),
            "bg-source": ("home", "main")}


def _next_link_v2(cur: str) -> None:
    t = _NEXT_V2.get(cur)
    if not t:
        return
    u, sec = t
    label = "처음으로: 홈" if u == "home" else f"다음: {page_of[u][1]} — {page_of[u][4]}"
    with st.container(key="next"):
        st.page_link(page_of[u][0], label=label, icon=":material/arrow_forward:", query_params={"sec": sec},
                     width="stretch")


# 소분류 맨 위 파란 상자의 질문 — 설계도판 v2 의 「Q.」. 「이 화면에서 보는 것」 설명 대신 쓴다(09-30 사용자).
# 상세 조회는 질문 없이 출처만
V2_Q = {
    ("parts", "summary"): "13개 품목군을 한 표로 보면 어떤가",
    ("parts", "trade"): "어느 나라에서 얼마나 들여오고 내보내나",
    ("parts", "conc"): "한 나라에 쏠린 정도는 나아지고 있나",
    ("fsc", "code"): "군은 전자부품을 어떤 분류로 관리하나",
    ("fsc", "plan"): "군은 전자 군급 중 무엇을 해외에서 사려 하나",
    ("fsc", "army"): "어느 군이, 어느 해에 해외 조달을 요구하나",
    ("fsc", "domestic"): "국내에서는 어떤 방식으로 사나",
    ("local", "done"): "그중 무엇을 국산화했나",
    ("local", "pair"): "해외 조달계획이 많은 군급과 국산화한 군급은 어떻게 다른가",
    ("background", "policy"): "정부는 어떤 정책과 예산으로 전자부품 국산화를 밀고 있나",
    ("background", "industry"): "국내 방산 생산 기반은 어떤가",
    ("background", "source"): "숫자는 어디서 왔고, 무엇을 뜻하지 않나",
}
# 파란 상자 글씨 — 설계도판 .mk-q 와 같은 15px(Q. = 굵은 파랑 · 질문 = 회청색). 상자 · 출처 모양은 screens/parts.py 의 .see 그대로
V2_SEE_CSS = css("see.css")
# 화면 파일은 끝에서 P.see(설명, 출처)를 부른다 — 소분류 제목 바로 아래에 자리(st.empty)를 먼저 만들어 두고 거기에 채운다
_SEE = {"slot": None, "q": None}


def _see_v2(what: str, source: str) -> None:
    q = _SEE["q"]
    body = (f'<div class="see q"><b>Q.</b><span>{escape(q)}</span><span class="src">출처: {source}</span></div>' if q
            else f'<div class="see"><span class="src">출처: {source}</span></div>')
    (_SEE["slot"] or st).html(body)


def _detail_v2(kind: str, sub: str) -> None:
    """상세 조회 — 「조건을 골라 … 내려받습니다」 설명 줄 없이 도구만(09-30 사용자)."""
    import parts as screen_parts
    runpy.run_path(str(screen_parts.VIZ), init_globals={"FIXED_TYPE": kind}, run_name="datacenter_viz")


def _live_page(u: str) -> None:
    """대분류 한 페이지 — DB 접속을 확인하고, 소분류마다 제목 줄 + 실데이터 화면을 이어 그린다."""
    import parts as screen_parts           # dashboard/screens/parts.py — 화면 파일이 쓰는 카드 · KPI · 차트 조각
    from db import db_ready
    screen_parts.next_link = _next_link_v2  # 소분류 화면의 옛 페이지 링크 대신 이 메뉴로 잇는다
    screen_parts.see = _see_v2              # 「이 화면에서 보는 것」 → 맨 위 「Q. 질문」
    screen_parts.detail = _detail_v2        # 상세 조회 설명 줄 빼기
    screen_parts.inject()
    st.html(V2_SEE_CSS)
    if not db_ready():                     # 접속 실패 — 안내 + 「다시 연결」만(UI/UX 9원칙)
        return
    titles = dict(SECTIONS[u])

    def run(k: str, screen: str):
        def _f():
            for _ in zone(k, titles[k]):
                _SEE["slot"], _SEE["q"] = st.empty(), V2_Q.get((u, k))
                runpy.run_path(str(SCREENS_DIR / f"{screen}.py"), run_name="__main__")
        return _f
    _run_sub({k: run(k, sc) for k, sc in SCREENS[u].items()})


def pg_parts() -> None:
    _live_page("parts")


def pg_fsc() -> None:
    _live_page("fsc")


def pg_local() -> None:
    _live_page("local")


def pg_background() -> None:
    _live_page("background")


# ════════════════════════════════════════════════════════════════════════════
# 6. 라우터 · 사이드바
# ════════════════════════════════════════════════════════════════════════════
# 사이드바 메뉴 — (페이지, 메뉴 이름, 아이콘, 배너 제목, 배너 부제).
# 아이콘은 차트 유형 버튼과 같은 Material Symbols(Rounded) 이름 — 이모티콘은 글꼴마다 색 · 모양이 달라 통일감이 없었다
PAGES = [
    (st.Page(page_home, title="K-Defense 홈", url_path="home", default=True), "홈", "home",
     "K-Defense 데이터 대시보드", "방산 전자부품 13개 품목군의 수출입과 국산화 현황"),
    (st.Page(pg_intro, title="소개", url_path="intro"), "소개", "info",
     "소개", "무기체계의 핵심 기능을 맡는 전자부품 — 왜 이 13개를 골랐고, 어디에 쓰이나"),
    (st.Page(pg_parts, title="전자부품 현황", url_path="parts"), "전자부품 현황", "memory",
     "전자부품 현황", "분석 대상 13개 품목군(HS)을 어디서 얼마나 들여오고 내보내나"),
    (st.Page(pg_fsc, title="군급 분류와 조달", url_path="fsc"), "군급 분류와 조달", "category",
     "군급 분류와 조달", "군수품 분류(군 FSG · 군급 FSC)로 보면 전자부품을 무엇을, 어떻게 조달하나"),
    (st.Page(pg_local, title="국산화 현황", url_path="local"), "국산화 현황", "build",
     "국산화 현황", "군(FSG) 58 · 59 · 60에 속한 전자 군급 부품 중 무엇을 국산화했나"),
    (st.Page(pg_background, title="배경과 자료", url_path="background"), "배경과 자료", "account_balance",
     "배경과 자료", "정책·예산, 국내 생산 현황과 데이터 출처를 확인합니다"),
]

pg = st.navigation([p[0] for p in PAGES], position="hidden")

# ── 데이터 정보(ⓘ) — 사이드바 왼쪽 아래 단추 → 대화상자(데이터.png 참고) ─────────────
st.html(css("dialogs.css"))


# 용어 설명 — 바닥글 「용어 설명」을 누르면 뜨는 대화상자. 모양은 데이터 정보 대화상자(di-*)와 같다
GLOSSARY = [
    ("inventory_2", "수출입 · 공급 집중도", [
        ("HS6 / HS10", "국제 공통 6자리 품목 분류 / 한국 세분류 10자리(HSK)"),
        ("품목군", "분석 대상 HS 품목을 묶은 단위 — 13개"),
        ("1위 점유율", "품목군 수입액 중 가장 큰 공급국의 비중"),
        ("HHI", "국가별 점유율(%) 제곱 합 · 2,500 이상 높음 · 4,000 이상 매우 높음"),
        ("부분연도", "한 해가 다 차지 않은 연도(2026년) — 추세 비교에서 뺌"),
    ]),
    ("category", "군수품 분류", [
        ("FSG", "군급 — 군수품 대분류(58 통신·탐지 · 59 전기·전자 구성품 · 60 광섬유)"),
        ("FSC", "군별 — FSG 아래 4자리 세분류"),
        ("NSN", "국가재고번호 — 군수품 한 품목에 붙는 13자리 번호"),
        ("적용장비", "부품이 들어가는 무기체계 · 장비"),
        ("국산화개발", "해외 조달 부품을 국내 개발로 대체하는 사업(품목 수 ≠ 국산화율)"),
    ]),
    ("receipt_long", "조달", [
        ("국외 조달계획", "방위사업청이 해외에서 사들일 계획인 품목 · 건수"),
        ("경쟁입찰", "여러 업체가 입찰해 낙찰자를 정하는 계약 방법"),
        ("수의계약", "경쟁 없이 특정 업체와 맺는 계약 — 사유를 따로 기록"),
        ("유찰", "입찰자가 없거나 조건 미달로 낙찰자가 정해지지 않은 공고"),
        ("낙찰업체", "입찰에서 계약 상대로 정해진 업체(사업자번호 기준)"),
    ]),
    ("account_balance", "예산 · 산업", [
        ("방위력개선비", "무기체계 구매 · 개발에 쓰는 국방 예산"),
        ("국외조달 예산", "방위사업청 예산 중 해외 구매에 배정된 금액"),
        ("방산 가동률", "방산 업체 생산설비를 실제로 돌린 비율(KOSIS)"),
        ("생산지수", "2020년 = 100 으로 둔 생산량 지수"),
        ("잠정", "이후 확정치로 바뀔 수 있는 값"),
    ]),
    ("rule", "이 대시보드 규칙", [
        ("R1 / R2", "분석 대상 진입 규칙 — 군용전용 / 항공 · 항행 세분류"),
    ]),
]


@st.dialog("용어 설명", width="medium")
def glossary_dialog() -> None:
    """바닥글 「용어 설명」 — 화면에 나오는 용어를 분야별 카드로 정리한다."""
    st.html('<div class="di-lead">대시보드 화면에 나오는 용어를 분야별로 정리했습니다.</div>' + "".join(
        f'<div class="di-card"><div class="di-ic"><span class="ms">{ic}</span></div><div><div class="di-t">{title}</div>'
        '<table class="di-tbl gl">' + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows) + '</table></div></div>'
        for ic, title, rows in GLOSSARY))


@st.fragment
def glossary_button(key: str) -> None:
    """바닥글 「용어 설명」 글씨 단추 — fragment 라 눌러도 본문은 다시 그리지 않는다."""
    if st.button("용어 설명", key=key, type="tertiary"):
        glossary_dialog()


# ════════════════════════════════════════════════════════════════════════════
# 7. 화면 틀 — 국방과학연구소(add.re.kr/kps) 방식
#    흰 머리글 + 상단 메뉴(마우스를 올리면 블록 목록이 펼쳐짐) → 서브 배너(왼쪽 제목 칸 · 블록 제목)
#    → 왼쪽 메뉴(이 페이지의 블록) + 오른쪽 본문(경로 표시 · 고른 블록 하나) → 짙은 바닥글
# ════════════════════════════════════════════════════════════════════════════
# 페이지별 블록 — 왼쪽 메뉴 · 상단 펼침 메뉴 · 전체 메뉴에 쓴다. 각 페이지 함수의 zone(키, 이름)과 같아야 한다
SECTIONS = {   # KDD_v1 과 같은 키 · 이름 · 순서
    "home": [("main", "Main")],
    "intro": [("elec", "왜 전자부품인가"), ("select", "어떻게 골랐나"), ("items", "13개 품목군"), ("use", "어디에 쓰이나")],
    "parts": [("summary", "종합 현황표"), ("trade", "수출입 현황"),
              ("conc", "공급국 집중도 변화"), ("detail", "상세 조회")],
    "fsc": [("code", "군급코드란"), ("plan", "군급별 국외 조달계획"), ("army", "소요군별"),
            ("domestic", "국내 계약 · 입찰"), ("detail", "상세 조회")],
    "local": [("done", "국산화 완료 부품"), ("pair", "군급 국산화 현황"), ("detail", "상세 조회")],
    "background": [("policy", "정책과 예산"), ("industry", "국내 생산 현황"),
                   ("source", "데이터 출처와 검증")],
}
# 왼쪽 메뉴 아래 파란 칸 — KDD_v1 과 같은 팁. (머리말, 내용)
LNB_TIPS = {
    "intro": [("흐름", "기능 → 선정 규칙 → 13개 → 쓰임"), ("주의", "쓰임은 일반적 용도 · 특정 체계 부품 목록(BOM) 아님")],
    "parts": [("공급국 집중", "HHI 2,500 이상 · 1위 공급국 점유율 50% 이상"),
              ("금액", "국가 전체 수입(민수 포함) — 군 수요만이 아님")],
    "fsc": [("기준", "전자 군급 = 군(FSG) 58 · 59 · 60에 속한 군급, 건수만"),
            ("비교", "전자부품 현황의 HS 품목군과 코드로 잇지 않음")],
    "local": [("주의", "완료 부품 수 ≠ 국산화율(분모 없음)"),
              ("비교", "조달계획과 막대만 나란히 — 비율로 계산하지 않음")],
    "background": [("단위", "예산 · 가동률 · 생산지수는 기준이 서로 다름"),
                   ("비교", "관세청 수입액과 합산 · 직접 비교하지 않음")],
}
URLS = ["home", "intro", "parts", "fsc", "local", "background"]   # PAGES 와 같은 순서
GNB = ["intro", "parts", "fsc", "local", "background"]              # 상단 메뉴 — 홈(첫 화면)은 로고를 누르면 간다
# 태극 — 위 빨강(#CD2E3A) · 아래 파랑(#0047A0), 왼쪽은 빨강이 · 오른쪽은 파랑이 반원만큼 파고든다. 흰 테두리로 방패 선과 떼어 놓는다
# st.html 은 <svg> 를 지우므로 그림(data URI)으로 넣는다
_TG_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-11 -11 22 22">'
           '<circle r="10" fill="#0047A0"/>'
           '<path d="M-10 0A10 10 0 0 1 10 0A5 5 0 0 0 0 0A5 5 0 0 1-10 0Z" fill="#CD2E3A"/>'
           '<circle r="10" fill="none" stroke="#fff" stroke-width="1.6"/></svg>')
TAEGEUK = ('<img class="tg" alt="" src="data:image/svg+xml;base64,'
           + base64.b64encode(_TG_SVG.encode()).decode() + '">')
# 배너 사진(Unsplash · 무료) — 항공모함 · K9 자주포
SV_SHIP = "https://images.unsplash.com/photo-1685178362030-9b574eb9ae7c?auto=format&fit=crop&w=1400&q=80"
# K9 자주포 — 자주포사진1.jpg(흙먼지 속을 달리는 K9, 1920×1080)를 840×473 흑백으로 줄였다(luminosity 로 겹치니 밝기만 쓴다).
# 왼쪽 뒤에 있던 두 번째 자주포는 지우고 주변 흙먼지로 번지게 메웠다. 파일은 assets/k9_banner.jpg — data URI 로 넣는다
SV_K9 = "data:image/jpeg;base64," + base64.b64encode((APP_DIR / "assets" / "k9_banner.jpg").read_bytes()).decode()
WRAP = 1400                    # 본문 최대 폭(px) — 머리글 · 배너 · 바닥글 배경은 화면 끝까지, 내용은 이 폭 안에
LNB_W = 230                    # 왼쪽 메뉴 폭 = 서브 배너의 제목 칸 폭
GNB_W = 200                    # 상단 메뉴 한 칸 폭(예전 7칸 때와 같은 폭) — 4칸을 가운데에 모은다. 파란 펼침 띠도 같은 폭
BLUE, BLUE_D, LINE_B = "#1d4ed8", "#003899", "#1d4ed8"   # 강조 파랑 · 짙은 파랑(제목 칸 · 펼침 메뉴)
_SUB_N = max(len(v) for v in SECTIONS.values())
_DROP_H = _SUB_N * 46 + 34     # 펼침 메뉴 높이 — 블록이 가장 많은 페이지 기준(한 줄 약 46px)

page_of = {u: p for u, p in zip(URLS, PAGES)}   # url → (페이지, 메뉴 이름, 아이콘, 제목, 부제)
url = next(u for u, p in page_of.items() if p[0] is pg)
# 처음 열 때(새 창 · 새로 고침 · 앱 재시작)는 주소에 남은 페이지 · 블록(?sec=)과 상관없이 늘 첫 화면(Main — 로고를 누르면 나오는 화면)으로.
# 앱 안에서 메뉴를 눌러 옮겨 다니는 것은 같은 세션이라 그대로 동작한다
if "_kd_opened" not in st.session_state:
    st.session_state["_kd_opened"] = True
    if url != "home" or st.query_params.get("sec") not in (None, "main"):
        st.query_params.clear()
        st.switch_page(page_of["home"][0])
_, cur_label, _, cur_title, cur_sub = page_of[url]
secs = SECTIONS[url]
_q = st.query_params.get("sec")
_SEC["sel"] = _q if _q in dict(secs) else secs[0][0]
# 홈은 첫 화면(Main)뿐 — 서브 배너 · 왼쪽 메뉴 없이 전체 폭
_SEC["landing"] = url == "home"
# 소분류는 한 페이지에 모두 이어 그린다(_run_sub). 다른 페이지 · 위쪽 메뉴 · 첫 화면 바로가기에서 ?sec= 로 들어오면
# 열린 뒤 그 소분류로 한 번만 스크롤한다(_LNB_JS). 주소의 sec 는 지운다 — 남겨 두면 버튼 · 전환으로 화면을 다시 그릴
# 때마다 그 자리로 되돌아간다. 번호(n)는 같은 소분류로 다시 들어와도 또 스크롤하게 바꿔 준다
if not _SEC["landing"] and _q in dict(secs):
    st.session_state["_lnb_go"] = [_q, st.session_state.get("_lnb_go", [None, 0])[1] + 1]
    del st.query_params["sec"]
nav_secs = [(k, t) for k, t in secs if k != "main"]      # 왼쪽 메뉴의 소분류 — 누르면 그 소분류로 스크롤한다
cur_sub = dict(nav_secs).get(_SEC["sel"], "")

# 머리글 · 배너 · 본문 줄 안쪽 여백 — 배경은 화면 끝까지, 내용은 가운데 WRAP 폭 안에 들어온다
_PAD = f"max(32px, calc((100% - {WRAP}px) / 2 + 32px))"
st.html(css("frame.css", PAD=_PAD, WRAP=WRAP, BLUE=BLUE, BLUE_D=BLUE_D, GNB_W=GNB_W, LNB_W=LNB_W,
            GNB_TOTAL=len(GNB) * GNB_W, GNB_HALF=len(GNB) * GNB_W // 2, DROP_H=_DROP_H, DROP_TOP=66 + _DROP_H))

intro_screen()

# ── 머리글 ──────────────────────────────────────────────────────────────
with st.container(key="hdr_top", horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
    st.html(f'<div class="brand"><span class="mark"><span class="ms">shield</span>{TAEGEUK}</span><div><b>K-Defense Electronics</b>'
            '<small>방산 전자부품 수입 집중도 · 국산화 · 조달 데이터 대시보드</small></div></div>')
    # 오른쪽 위(훈수안이조 배지 · 로그인 · 공지사항 · 데이터 정보)는 09-30 비움 — 데이터 출처는 바닥글 · 배경과 자료에
    # 로고(방패 · K-Defense · 부제) 위에 투명한 링크를 덮어, 누르면 홈(Main 첫 화면)으로 간다
    with st.container(key="brand_link"):
        st.page_link(page_of["home"][0], label="K-Defense 홈", query_params={"sec": "main"})

# ≡ 단추 — 누르면 파란 펼침 띠가 커서를 떼도 계속 펼쳐져 있고, 다시 누르면 닫힌다(열려 있을 때는 × 모양).
# st.html 은 스크립트를 돌리지 않아, 보이지 않는 components.html 안에서 바깥 화면(window.parent)을 다룬다
GNB_JS = script("gnb_toggle.js")

with st.container(key="gnb", horizontal=True, vertical_alignment="center"):
    for u in GNB:
        page, label = page_of[u][0], page_of[u][1]
        with st.container(key=f"gi_{u}", width="stretch"):
            if page is pg:
                st.html(f'<div class="gnb-on">{label}</div>')
            else:      # 대분류를 누르면 첫 소분류 화면으로
                st.page_link(page, label=label)
            with st.container(key=f"gs_{u}"):
                for k, t in SECTIONS[u]:
                    st.page_link(page, label=t, query_params={"sec": k})
    with st.container(key="gnb_all", width="content"):
        st.html('<button class="gnb-all" type="button" aria-label="전체 메뉴 열기 · 닫기"><span class="ms">menu</span></button>')
with st.container(key="gnbjs"):
    components.html(GNB_JS, height=0)

# ── Main(첫 화면)은 서브 배너 · 왼쪽 메뉴 없이 화면 전체 폭으로 ──────────────────────
LANDING = _SEC["landing"]
if LANDING:
    with st.container(key="landing"):
        pg.run()

# ── 서브 배너 ───────────────────────────────────────────────────────────
if not LANDING:
    # ── 서브 배너 ──
    st.html(f'<div class="sv"><div class="sv-ph"><i class="ship" style="background-image:url({SV_SHIP})"></i>'
            f'<i class="k9" style="background-image:url({SV_K9})"></i></div>'
            f'<div class="sv-in"><div class="sv-sp"></div>'
            f'<div class="sv-title"><h1>{cur_title}</h1><p>{cur_sub}</p></div></div></div>')

    # ── 본문 줄: 왼쪽 메뉴 + 본문 ────────────────────────────────────────────
    with st.container(key="body", horizontal=True):
        with st.container(key="lnb", width=LNB_W):
            # 제목 칸(K-DEFENSE · 페이지 이름) — 배너 아래쪽에 걸쳐 놓이고, 왼쪽 메뉴와 한 묶음으로 스크롤을 따라온다
            st.html(f'<div class="sv-box lnb-box"><small>K-DEFENSE</small><b>{cur_label}</b></div>')
            # 소분류 — 한 페이지에 모두 이어져 있다. 누르면 페이지를 다시 열지 않고 그 소분류로 스크롤한다(_LNB_JS).
            # 보이는 소분류는 스크롤 위치에 따라 ✓ 로 바뀐다. href 는 스크립트가 없을 때를 위한 예비(예전처럼 그 소분류로 연다)
            st.html('<nav class="lnb-nav">' + "".join(
                f'<a class="lnb-a{" on" if k == _SEC["sel"] else ""}" href="?sec={k}" data-sub="{k}">{t}</a>'
                for k, t in nav_secs) + '</nav>')
            with st.container(key="lnbjs"):
                _LNB(key="lnb_scroll", data={"go": st.session_state.get("_lnb_go"),
                                              "labels": dict(nav_secs)})
            st.html('<div class="lnb-help"><b>이렇게 보세요</b><ul>' + "".join(f"<li><em>{h}</em>{t}</li>" for h, t in LNB_TIPS[url])
                    + '</ul></div>')
        with st.container(key="main"):
            # 홈 아이콘은 링크 — 누르면 Main(첫 화면)으로 간다(로고 링크와 같은 곳)
            with st.container(key="crumb", horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
                st.page_link(page_of["home"][0], label="홈", icon=":material/home:", query_params={"sec": "main"})
                st.html(f'<div class="crumb"><i>›</i><span>{cur_label}</span><i>›</i><b>{cur_sub}</b></div>')
            pg.run()

# SECTIONS 와 페이지 함수의 zone 키가 어긋나면 본문이 비므로 바로 알린다(개발용)
if not _SEC["shown"]:
    st.error("이 페이지에서 그릴 블록을 찾지 못했습니다 — SECTIONS 와 zone 키를 맞춰 주세요.")

# ── 바닥글 ──────────────────────────────────────────────────────────────
# 바닥글 — K-Defense(로고) → Main · 데이터 출처 → ④ 데이터 출처 · 검증 · 용어 설명 → 대화상자 · 훈수안이조 → 팀 GitHub
TEAM_URL = "https://github.com/dashboard"
with st.container(key="ft", horizontal=True):
    with st.container(key="ft_brand", width="content"):
        st.html('<div class="brand"><span class="mark"><span class="ms">shield</span>' + TAEGEUK + '</span><div><b>K-Defense</b>'
                '<small>데이터로 만드는 더 강한 대한민국</small></div></div>')
        st.page_link(page_of["home"][0], label="K-Defense 홈", query_params={"sec": "main"})   # 로고 위를 덮는 투명 링크
    with st.container(key="ft_mid"):
        with st.container(key="ft_links", horizontal=True, vertical_alignment="center"):
            st.html('<span class="ftl">데이터 이용 안내</span>', width="content")
            st.page_link(page_of["background"][0], label="데이터 출처", query_params={"sec": "source"})
            glossary_button("ft_terms")
            st.html('<span class="ftl">주의사항</span>', width="content")
        st.html('<div class="ft-mid">자료: 관세청 수출입무역통계 · 방위사업청 국내 · 국외 조달 · KOSIS 방산 가동률 · 열린재정 세부사업 예산<br>'
                f'<a class="ft-team" href="{TEAM_URL}" target="_blank" rel="noopener">훈수안이조</a>'
                ' — 숫자는 공개 데이터를 적재한 운영 DB 에서 읽습니다 · © 2026 K-Defense 팀 프로젝트</div>')
    st.html('<details class="ft-rel"><summary>관련 사이트 바로가기</summary>'
            '<a href="https://unipass.customs.go.kr/ets/" target="_blank">관세청 수출입무역통계</a>'
            '<a href="https://www.dapa.go.kr" target="_blank">방위사업청</a>'
            '<a href="https://kosis.kr" target="_blank">KOSIS 국가통계포털</a>'
            '<a href="https://www.openfiscaldata.go.kr" target="_blank">열린재정</a>'
            '<a href="https://www.data.go.kr" target="_blank">공공데이터포털</a></details>', width="content")

# ── 화면이 바뀌면 맨 위로 ──────────────────────────────────────────────────
# st.html 은 스크립트를 돌리지 않아, 보이지 않는 components.html 안에서 바깥 화면(window.parent)을 다룬다.
# __NAV__ 에 대분류 · 소분류를 넣어 화면이 바뀔 때만 새로 붙는다(같은 화면에서 위젯을 만질 때는 스크롤 그대로)
_TOP_JS = script("scroll_top.js")
with st.container(key="kdjs"):
    components.html(_TOP_JS.replace("__NAV__", f"{url}|{_SEC['sel']}"), height=0)
