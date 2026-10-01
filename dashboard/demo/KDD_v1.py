"""K-Defense 대시보드 — 새 디자인(brandnew). dashboard/demo/design_demo.py 를 바탕으로 화면 틀만 바꾼 판.

화면 틀: 국방과학연구소 누리집(add.re.kr/kps) 방식 · 흰색 + 파랑.
  - 사이드바 대신 흰 머리글 + 상단 메뉴. 메뉴에 커서를 올리면 모든 페이지의 블록 목록이 파란 띠로 펼쳐진다
  - 서브 배너(왼쪽 아래 페이지 제목 칸) → 왼쪽 메뉴(이 페이지의 블록) + 본문(경로 표시 · 고른 블록 하나)
  - 블록은 주소의 ?sec= 로 고른다(예: /import?sec=trend). 고르지 않은 블록은 실행하지 않는다
  - 오른쪽 빠른 메뉴 · 짙은 바닥글

실행:  streamlit run "dashboard/demo/K-Defense_brandnew.py" --theme.base light
       저장소 루트의 `.streamlit/config.toml` 은 운영 앱용 **다크** 테마라, 저장소에서 플래그 없이 실행하면
       테마가 다크로 잡힌다. OS 다크모드이거나 테마 설정이 없을 때도 마찬가지다. 그래도 버튼 · 선택창 · 체크박스는
       아래 「라이트 테마 고정(위젯)」 CSS 로 라이트로 보인다. 표는 모두 HTML 표(cat_table · stat_table)라
       다크 테마에서도 흰 표로 보인다. 그래도 위처럼 `--theme.base light` 를 붙여 실행하는 편이 안전하다.

이 파일 하나만 있으면 돌아간다. DB·`.env`·프로젝트 폴더가 전혀 필요 없다(다른 PC로 복사해도 같다).
필요한 것은 streamlit·pandas·plotly 뿐이고, 지구본의 세계지도 데이터만 인터넷(CDN)에서 받는다
(못 받으면 경위선만 그리고 화면에 알린다).

★ 화면의 모든 숫자는 **화면 배치·색·움직임을 보여 주기 위한 샘플**이다. 실제 DB 값이 아니며,
  어떤 보고·발표 자료에도 그대로 쓰면 안 된다. 실제 값은 운영 앱(dashboard/main.py)이 AWS RDS 에서 읽는다.

디자인 기준: 목업 PNG 6장(K-Defense) — 짙은 남색 사이드바 + 밝은 본문 + 흰 카드.
"""
from __future__ import annotations

import base64
import contextlib
import json
import math
import time
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# 소개 — 무기체계 분류 · 공개 사례 설명 상수(dashboard/weapon_context.py, KDD_v2 와 같은 방법)
import sys
from pathlib import Path
_DASHBOARD_DIR = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_DIR))
from weapon_context import CASES, SYSTEMS  # noqa: E402

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
SERIES = [ACCENT, "#17c8b5", "#7c6cf0", "#ff9f43", "#ff6b9a", "#38bdf8"]
ETC = "#c3cede"

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
CSS = f"""<style>
{_FONTS}html{{zoom:{APP_ZOOM}}}
[data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{{zoom:calc(1 / {APP_ZOOM})}}
/* 선택창 목록(selectbox · multiselect)은 버튼 위치를 재서 그 좌표에 뜨는데, 배율이 좌표까지 키워 버튼 밑이 아닌
   오른쪽 아래 엉뚱한 곳에 떴다 — 목록 틀은 배율을 되돌려 제자리에, 안의 글씨·칸은 다시 배율만큼 키운다. 도움말 말풍선(help=)도 같다 */
[data-rac][data-trigger],[data-rac][role="tooltip"]{{zoom:calc(1 / {APP_ZOOM})}}
[data-rac][data-trigger] > *,[data-rac][role="tooltip"] > *{{zoom:{APP_ZOOM}}}
/* 배율이 스크롤 영역 높이(100vh)까지 키워 페이지 맨 아래가 창 밖으로 잘린다 — 높이만 창 크기로 되돌린다 */
[data-testid="stMain"]{{height:calc(100dvh / {APP_ZOOM})!important;max-height:calc(100dvh / {APP_ZOOM})!important}}
:root{{
  --bg:{BG}; --panel:{PANEL}; --panel2:{PANEL2}; --line:{LINE};
  --text:{TEXT}; --muted:{MUTED}; --accent:{ACCENT}; --navy:{NAVY}; --navy2:{NAVY2};
  --up:{UP}; --down:{DOWN};
  --shadow:0 1px 2px rgba(19,42,84,.06), 0 6px 18px rgba(19,42,84,.06);
  --shadow-h:0 2px 4px rgba(19,42,84,.08), 0 14px 32px rgba(19,42,84,.12);
}}

html, body, [class*="st-"]{{font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif}}
/* 위 규칙이 아이콘 span 까지 덮으면 아이콘 이름(keyboard_double_arrow_left 등)이 글씨로 찍힌다 — 아이콘 글꼴 복원 */
[data-testid="stIconMaterial"],[data-testid="stExpanderIcon"]{{font-family:'Material Symbols Rounded'!important}}
/* 헤더를 통째로 숨기면 그 안의 '사이드바 열기' 버튼까지 사라진다 — 헤더는 투명하게 두고 메뉴·툴바만 숨긴다 */
[data-testid="stHeader"]{{background:transparent;height:0;pointer-events:none}}
[data-testid="stToolbar"] > *:not(:has([data-testid="stExpandSidebarButton"])),
[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="stMainMenu"],
[data-testid="stToolbarActions"],[data-testid="stAppDeployButton"]{{display:none!important}}
/* 차트·표에 마우스를 올리면 뜨는 요소 툴바(전체화면 확대 버튼 등)를 숨긴다 */
[data-testid="stElementToolbar"],[data-testid="StyledFullScreenButton"]{{display:none!important}}
/* 사이드바 열기(») / 닫기(«) — 둘 다 왼쪽 위 같은 자리(left 10px · top 20px · 40px 칸)에 놓는다 */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] button{{width:40px;height:40px;min-height:0;padding:0;border:none;border-radius:10px;
  display:grid;place-items:center;background:rgba(255,255,255,.06);transition:background .16s}}
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stSidebarCollapseButton"] button:hover{{background:rgba(255,255,255,.14)}}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]{{font-size:0}}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::after,
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::after{{font-family:Pretendard,system-ui,sans-serif;
  font-size:22px;font-weight:700;line-height:1;color:#b9cdea}}
[data-testid="stExpandSidebarButton"]:hover [data-testid="stIconMaterial"]::after,
[data-testid="stSidebarCollapseButton"] button:hover [data-testid="stIconMaterial"]::after{{color:#fff}}
[data-testid="stExpandSidebarButton"]{{position:fixed!important;left:10px;top:20px;margin:0;z-index:999991;pointer-events:auto}}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::after{{content:"»"}}
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button{{visibility:visible!important}}   /* 기본값은 사이드바에 커서를 올려야만 보인다 */
[data-testid="stSidebarCollapseButton"]{{display:block!important;position:absolute;left:10px;top:20px;margin:0;z-index:2}}
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::after{{content:"«"}}
[data-testid="stAppViewContainer"]{{background:var(--bg)}}
.block-container{{padding:0 34px 40px;max-width:1500px}}

/* ── 사이드바 ─────────────────────────────────────────────────────────── */
[data-testid="stSidebar"]{{background:linear-gradient(175deg,var(--navy) 0%,var(--navy2) 100%);border-right:none;width:248px!important}}
[data-testid="stSidebar"] > div{{padding-top:0}}
[data-testid="stSidebarContent"]{{padding:0}}
[data-testid="stSidebarNav"]{{display:none}}
/* ── 미니 사이드바 — 사이드바가 닫혔을 때만 왼쪽에 아이콘만 세로로 ─────────── */
.st-key-minirail{{display:none!important}}
.stApp:has([data-testid="stSidebar"][aria-expanded="false"]) .st-key-minirail{{display:flex!important}}
.stApp:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stMain"]{{margin-left:60px}}
/* 위 60px 만큼 본문 폭은 줄지 않아 오른쪽이 창 밖으로 나가고 구역들이 오른쪽으로 쏠린다 —
   구역들만 30px 왼쪽으로, 맨 위 배너(hero)는 제자리 */
.stApp:has([data-testid="stSidebar"][aria-expanded="false"]) .block-container{{position:relative;left:-30px}}
.stApp:has([data-testid="stSidebar"][aria-expanded="false"]) .st-key-hero{{position:relative;left:30px}}
.st-key-minirail{{position:fixed;left:0;top:0;bottom:0;width:60px;z-index:999980;   /* 헤더(999990, » 버튼이 들어 있음)보다 아래 */
flex-direction:column;align-items:center;
  justify-content:center;gap:12px;padding:72px 0;overflow:visible;
  background:linear-gradient(175deg,var(--navy) 0%,var(--navy2) 100%);box-shadow:2px 0 14px rgba(7,28,64,.18)}}
.st-key-minirail > div{{width:auto!important;overflow:visible}}
/* 미니 사이드바를 본문 맨 앞에 두므로, 그 바깥 감싸개를 흐름에서 빼 본문 위쪽에 빈 간격이 생기지 않게 한다 */
[data-testid="stLayoutWrapper"]:has(> .st-key-minirail){{position:fixed;left:0;top:0;width:0;height:0;margin:0;z-index:999980}}
/* 평소엔 아이콘만 보이는 40px 칸 — 커서를 올리면 오른쪽으로 펼쳐지며 아이콘+글씨가 커진다 */
.st-key-minirail [data-testid="stPageLink"] a,
.mr-on{{display:flex;align-items:center;box-sizing:border-box;width:max-content;height:40px;max-width:40px;padding:0 10px;margin:0;
  overflow:hidden;white-space:nowrap;border-radius:10px;background:transparent;transform-origin:left center;
  transition:max-width .22s ease,transform .18s ease,background .16s,box-shadow .16s}}
.st-key-minirail [data-testid="stPageLink"] a p,
.mr-on{{font-family:{SIDE_STACK};font-size:16px;font-weight:700;letter-spacing:-.2px;color:#fff;white-space:nowrap}}
.mr-on{{background:#fff;color:#1d4ed8;box-shadow:0 4px 14px rgba(7,28,64,.22);
  height:38px;max-width:38px;padding-left:9px}}   /* 지금 페이지 파란 칸 — 다른 칸(40px)보다 2px 작게.
     칸이 좁아져 가운데로 1px 들어온 만큼 왼쪽 여백을 1px 줄여, 누르기 전후로 이모티콘 자리가 그대로이게 한다 */
.st-key-minirail [data-testid="stPageLink"] a:hover,
.mr-on:hover{{max-width:240px;padding-right:16px;transform:scale(1.12);position:relative;z-index:2;
  background:linear-gradient(95deg,#2b6ef6,#3fa9f5);box-shadow:0 8px 22px rgba(13,42,92,.38)}}
.mr-on:hover{{background:#fff}}   /* 지금 페이지 칸 — 흰 바탕 · 파란 글씨(펼쳐져도 그대로) */
.st-key-sidebrand{{padding:14px 20px 18px;   /* 위쪽은 닫기 버튼(«)이 놓이는 사이드바 헤더(60px) 바로 아래 */
border-bottom:1px solid rgba(255,255,255,.08)}}
.sb-brand{{display:flex;align-items:center;gap:11px}}
/* 로고 — 메뉴와 같은 Material Symbols 방패 아이콘 · 흰색 · 배경 칸 없음. 브라우저 탭 아이콘도 같은 방패 */
.sb-mark{{width:38px;height:38px;flex:0 0 38px;display:grid;place-items:center}}
.sb-mark .nav-ic{{margin:0;font-size:32px;width:32px;flex:0 0 32px;color:#fff}}
.sb-brand b{{display:block;font-size:19.5px;font-weight:800;letter-spacing:-.3px;color:#fff;line-height:1.2}}
.sb-brand small{{display:block;font-size:11.5px;color:#93b0dd;line-height:1.55;margin-top:4px}}
.st-key-sidenav{{padding:14px 12px 0}}
.st-key-sidenav [data-testid="stVerticalBlock"]{{gap:3px}}
.st-key-sidenav [data-testid="stPageLink"] a{{padding:10px 14px;border-radius:10px;background:transparent;transition:background .16s,transform .16s}}
.st-key-sidenav [data-testid="stPageLink"] a:hover{{background:rgba(255,255,255,.08);transform:translateX(2px)}}
.st-key-sidenav [data-testid="stPageLink"] a p{{font-size:14.5px;font-weight:600;color:#b9cdea;white-space:nowrap}}
.nav-on{{display:flex;align-items:center;padding:10px 14px;margin:0;font-size:14.5px;font-weight:700;color:#1d4ed8;
  border-radius:10px;background:#fff;box-shadow:0 4px 14px rgba(7,28,64,.22)}}   /* 지금 페이지 — 흰 바탕 · 파란 글씨 */
/* 메뉴 아이콘 — 차트 유형 버튼과 같은 Material Symbols(Rounded) 한 벌 · 한 색(글씨색을 그대로 따른다) · 20px */
.nav-ic{{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;font-size:20px;line-height:1;
  width:20px;flex:0 0 20px;margin-right:10px;letter-spacing:0;font-feature-settings:'liga';-webkit-font-smoothing:antialiased}}
.st-key-sidenav [data-testid="stPageLink"] a [data-testid="stIconMaterial"],
.st-key-minirail [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{{font-size:20px;width:20px;flex:0 0 20px;margin:0 10px 0 0!important}}
/* page_link 의 아이콘 감싸개는 너비가 16px 로 고정되고 가운데 정렬이라, 아이콘(20px)+간격(10px)이 양옆으로 7px 씩 삐져나와
   고른 메뉴(파란 칸)보다 아이콘이 7px 왼쪽에 놓였다 — 감싸개 너비를 내용대로 두고 왼쪽 정렬. 기본 간격(8px)도 없애 글씨 위치까지 맞춘다 */
.st-key-sidenav [data-testid="stPageLink"] a,.st-key-minirail [data-testid="stPageLink"] a{{gap:0!important}}
.st-key-sidenav [data-testid="stPageLink"] a > span:first-child,
.st-key-minirail [data-testid="stPageLink"] a > span:first-child{{width:auto!important;flex:0 0 auto!important;justify-content:flex-start!important}}
.st-key-sidenav [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{{color:#b9cdea}}
.st-key-minirail [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{{color:#fff}}
.st-key-sidenav [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"],
.st-key-sidenav [data-testid="stPageLink"] a:hover p{{color:#fff}}
.st-key-sidefoot{{padding:26px 20px 20px;margin-top:8px}}
.sb-tag{{font-size:11.5px;font-weight:800;letter-spacing:2.2px;line-height:1.85;color:#5e8bd0}}
.sb-note{{margin-top:16px;font-size:12.5px;color:#9fb8de;line-height:1.6}}
.sb-ver{{margin-top:18px;padding-top:14px;border-top:1px solid rgba(255,255,255,.08);font-size:10.5px;color:#587298}}

/* ── 히어로 ───────────────────────────────────────────────────────────── */
.st-key-hero{{margin:0 -34px 8px;padding:0}}
.hero{{position:relative;overflow:hidden;min-height:112px;padding:24px 700px 26px 34px;
  background:linear-gradient(105deg,#e8f1ff 0%,#dbeafe 42%,#cfe4fb 70%,#bfdcf7 100%)}}
.hero::after{{content:"";position:absolute;right:-60px;top:-40px;width:420px;height:230px;border-radius:50%;
  background:radial-gradient(circle at 40% 40%,rgba(255,255,255,.75),rgba(255,255,255,0) 68%)}}
.hero h1,.hero .slogan b{{font-family:{SIDE_STACK};font-weight:800;font-style:normal}}   /* 표어도 제목과 같은 글꼴 */
.hero h1{{margin:0;font-size:27px;letter-spacing:-.6px;color:#0f2c5e;line-height:1.25}}
.hero p{{margin:7px 0 0;font-size:13px;color:#3d5b8c;line-height:1.55}}
.hero .slogan{{position:absolute;right:34px;top:50%;transform:translateY(-50%);width:200px;text-align:right;z-index:1}}
.hero h1,.hero p{{position:relative;z-index:1}}   /* 제목 · 부제는 그림 위에 */
.hero .slogan b{{display:block;font-size:18px;color:#1c4ea3;letter-spacing:-.5px;line-height:1.35}}
/* 제목과 표어 사이 — 목업의 구축함 · 전투기 그림(HERO_IMG). 배너 높이에 맞추고 좌우 끝은 마스크로 배경에 녹인다.
   폭이 좁으면 그림을 빼고 제목 자리를 넓힌다 */
.hero .hero-art{{position:absolute;right:25px;top:0;height:100%;width:auto;z-index:0;pointer-events:none;display:block;opacity:.3;
  -webkit-mask-image:linear-gradient(90deg,transparent 0,#000 16%,#000 86%,transparent 100%);
  mask-image:linear-gradient(90deg,transparent 0,#000 16%,#000 86%,transparent 100%)}}
@media (max-width:1250px){{.hero .hero-art{{display:none}} .hero{{padding-right:300px}}}}

/* ── 샘플 데이터 경고 띠 ──────────────────────────────────────────────── */
.demo-bar{{display:flex;align-items:center;gap:10px;margin:0 0 14px;padding:10px 16px;border-radius:10px;
  background:#fff7e6;border:1px solid #fcd9a0;border-left:4px solid #f59e0b}}
.demo-bar b{{font-size:12.5px;font-weight:800;color:#92400e}}
.demo-bar span{{font-size:11.5px;color:#a16207;line-height:1.5}}

/* ── 구역 ─────────────────────────────────────────────────────────────── */
div[class*="st-key-zone_"]{{position:relative;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.55);
  padding:32px 16px 18px;margin:14px 0 18px}}
div[class*="st-key-zone_"]::before{{position:absolute;top:-12px;left:18px;z-index:1;
  background:#2b6ef6;color:#fff;font-size:12px;font-weight:700;letter-spacing:-.2px;
  padding:4px 13px;border-radius:20px;box-shadow:0 4px 12px rgba(43,110,246,.3)}}

/* ── 카드 ─────────────────────────────────────────────────────────────── */
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:15px 17px;height:100%;
  box-shadow:var(--shadow);transition:box-shadow .2s ease,transform .2s ease}}
.card:hover{{box-shadow:var(--shadow-h);transform:translateY(-2px)}}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [class*="st-key-card_"]),
div[class*="st-key-card_"]{{background:var(--panel);border:1px solid var(--line)!important;border-radius:14px;box-shadow:var(--shadow)}}

/* ── KPI ──────────────────────────────────────────────────────────────── */
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:13px}}
.kpis.k4{{grid-template-columns:repeat(4,1fr)}}
.kpis.k6{{grid-template-columns:repeat(6,1fr)}}
.kpi{{animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both}}
.kpis .kpi:nth-child(1){{animation-delay:.02s}} .kpis .kpi:nth-child(2){{animation-delay:.07s}}
.kpis .kpi:nth-child(3){{animation-delay:.12s}} .kpis .kpi:nth-child(4){{animation-delay:.17s}}
.kpis .kpi:nth-child(5){{animation-delay:.22s}} .kpis .kpi:nth-child(6){{animation-delay:.27s}}
@keyframes rise{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
.kpi .kt{{display:flex;align-items:center;gap:9px;min-height:30px}}
.kpi .ico{{width:30px;height:30px;flex:0 0 30px;border-radius:9px;display:grid;place-items:center;font-size:15px;
  background:#e8f0ff;transition:transform .2s ease}}
.kpi:hover .ico{{transform:scale(1.08) rotate(-4deg)}}
.kpis .kpi:nth-child(2) .ico{{background:#e4fbf6}} .kpis .kpi:nth-child(3) .ico{{background:#f0ecff}}
.kpis .kpi:nth-child(4) .ico{{background:#fff2e3}} .kpis .kpi:nth-child(5) .ico{{background:#ffe9f1}}
.kpis .kpi:nth-child(6) .ico{{background:#eaf4ff}}
/* KPI 아이콘 — 이모티콘 대신 메뉴와 같은 Material Symbols(Rounded). 배경 칸 색은 그대로 두고 아이콘은 같은 계열의 진한 색 */
.kpi .ico .ms{{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;font-size:19px;line-height:1;
  letter-spacing:0;font-feature-settings:'liga';-webkit-font-smoothing:antialiased}}
.kpis .kpi .ico{{color:#2b6ef6}}
.kpis .kpi:nth-child(2) .ico{{color:#0f9f85}} .kpis .kpi:nth-child(3) .ico{{color:#7a5af8}}
.kpis .kpi:nth-child(4) .ico{{color:#e0851a}} .kpis .kpi:nth-child(5) .ico{{color:#e0457b}}
.kpis .kpi:nth-child(6) .ico{{color:#2f8fdc}}
.kpi .l{{font-size:12px;font-weight:600;color:#5a6b8c;line-height:1.35}}
.kpi .v{{font-size:29px;font-weight:800;margin-top:9px;letter-spacing:-1px;color:#12234a;line-height:1.1}}
.kpi .v small{{font-size:13px;color:var(--muted);font-weight:600;margin-left:4px;letter-spacing:0}}
.kpi .s{{font-size:11px;color:var(--muted);margin-top:6px;line-height:1.5}}
/* ⓘ 단추 — 카드 오른쪽 위. 커서를 올리면 세부 설명 말풍선(SGIS 대시보드 방식). 제목 줄(.h · .kt)의 오른쪽 끝에 붙는다 */
.ib{{position:relative;margin-left:auto;flex:0 0 auto;align-self:flex-start;display:inline-grid;place-items:center;
  width:20px;height:20px;cursor:help;color:#9aabc8;transition:color .15s}}
.ib:hover{{color:var(--accent)}}
.ib .ms{{font-family:'Material Symbols Rounded'!important;font-size:18px;line-height:1;font-weight:400;font-style:normal;
  font-feature-settings:'liga'}}
.ib .tip{{position:absolute;top:calc(100% + 6px);right:-6px;width:max-content;max-width:290px;padding:10px 12px;
  background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 10px 28px rgba(19,42,84,.16);
  font-size:11.5px;font-weight:500;line-height:1.65;color:#44567a;letter-spacing:-.1px;text-align:left;white-space:normal;
  opacity:0;visibility:hidden;transform:translateY(-4px);transition:opacity .15s,transform .15s,visibility .15s;
  z-index:80;pointer-events:none}}
.ib:hover .tip{{opacity:1;visibility:visible;transform:none}}
/* 다른 페이지 — 카드 제목 옆 설명(.h .sub)도 같은 ⓘ 말풍선으로 보인다.
   설명 글자는 평소 숨긴 말풍선 안에 있고, ⓘ 은 그 말풍선의 ::before(혼자 보이게 둠)라 ⓘ 에 커서를 올리면 말풍선이 켜진다 */
.h{{position:relative}}
.h .sub{{position:absolute;right:-6px;top:calc(100% + 6px);width:max-content;max-width:290px;margin:0;padding:10px 12px;
  background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 10px 28px rgba(19,42,84,.16);
  font-size:11.5px;font-weight:500;line-height:1.65;color:#44567a;letter-spacing:-.1px;text-align:left;white-space:normal;
  visibility:hidden;z-index:80}}
.h .sub::before{{content:"info";position:absolute;top:-29px;right:6px;width:20px;height:20px;display:grid;place-items:center;
  visibility:visible;cursor:help;color:#9aabc8;transition:color .15s;font-family:'Material Symbols Rounded';font-size:18px;
  line-height:1;font-weight:400;font-style:normal;letter-spacing:0;font-feature-settings:'liga'}}
.h .sub:hover{{visibility:visible}}
.h .sub:hover::before{{color:var(--accent)}}
/* KPI(조회 결과 작은 카드 제외) — 숫자를 키워(29 → 35px) 가운데에 두고, 설명 줄(.s)은 숫자 아래에 왼쪽 정렬 · 회색 글씨로 붙인다.
   가로로 너무 길어 보이지 않게 세로를 늘리고(142 → 180px), 숫자 + 설명 묶음을 제목 줄 아래 남은 칸의 세로 가운데에 둔다 */
.kpis:not(.q) .kpi{{min-height:180px;display:flex;flex-direction:column;min-width:0}}
/* 블록 위쪽 파란 선 — defense-trade.streamlit.app KPI 카드와 같은 #1d4ed8 · 두께 4px */
.kpis:not(.q) .kpi{{border-top:4px solid #1d4ed8}}
/* 블록 가로 — 칸 사이를 넓혀(13 → 26px) 블록 폭을 줄이고, minmax(0,1fr)로 글 길이와 상관없이 모든 칸 폭을 같게 */
.kpis:not(.q){{gap:26px;grid-template-columns:repeat(5,minmax(0,1fr))}}
.kpis.k4:not(.q){{grid-template-columns:repeat(4,minmax(0,1fr))}}
.kpis.k6:not(.q){{grid-template-columns:repeat(6,minmax(0,1fr))}}
.kpis:not(.q) .kpi .v{{margin:auto 0 0;padding:0 0 2px;text-align:center;font-size:35px;letter-spacing:-1.2px}}
.kpis:not(.q) .kpi .v small{{font-size:14px}}
.kpis:not(.q) .kpi .s{{margin:12px 0 auto;color:var(--muted);font-size:11.5px}}
/* 제목(분석 대상 품목군 등)은 크게 · 진하게 */
.kpis:not(.q) .kpi .l{{font-size:17px;font-weight:700;color:#12234a;letter-spacing:-.3px}}
.kpis:not(.q) .kpi .kt{{min-height:34px}}
.kpis:not(.q) .kpi .ico{{width:34px;height:34px;flex:0 0 34px;font-size:17px}}
/* 글씨 비율 — 칸이 좁은 6칸 줄은 제목 · 숫자를 한 단계 줄이고, 긴 제목 · 긴 숫자는 한 줄에 들어가게 더 줄인다(4칸 줄은 칸이 넓어 그대로) */
.kpis.k6:not(.q) .kpi .l{{font-size:15.5px}}
.kpis.k6:not(.q) .kpi .v{{font-size:31px}}
.kpis:not(.q):not(.k4) .kpi .l.long{{font-size:15.5px;letter-spacing:-.5px}}
.kpis:not(.q) .kpi .v.long{{font-size:26px;letter-spacing:-.8px;white-space:nowrap}}
/* 차트(plotly)에 커서를 올리면 오른쪽 위에 뜨는 도구 막대(내려받기 · 확대 · 이동 · 되돌리기 등) — 모든 차트에서 숨긴다 */
.modebar-container{{display:none!important}}
/* 카드 제목이 없는 곳(조회 차트 아래 등)의 ⓘ 줄 — 오른쪽 끝에 두고 말풍선은 위로 연다 */
.info-line{{display:flex;justify-content:flex-end;margin:2px 0 0}}
.info-line .ib .tip{{top:auto;bottom:calc(100% + 6px)}}
/* 조회 결과 카드(차트 · 결과 표 탭) — ⓘ 은 탭 칸 오른쪽 위에 띄우고 말풍선은 아래로 연다(오른쪽 아래는 내려받기 단추 자리) */
.st-key-card_res [role="tabpanel"]{{position:relative}}
.st-key-card_res [role="tabpanel"] [data-testid="stElementContainer"]:has(.info-line){{position:absolute!important;top:8px;right:10px;
  width:auto!important;margin:0!important;z-index:6}}
.st-key-card_res [role="tabpanel"] [data-testid="stElementContainer"]:has(.info-line .ib:hover){{z-index:90}}
.st-key-card_res .info-line{{margin:0}}
.st-key-card_res .st-scroll{{margin-top:22px}}   /* 결과 표는 ⓘ 아래에서 시작(표 모서리와 겹치지 않게) */
/* 말풍선은 ⓘ 위로 연다 — 아래로 열면 차트를 가렸다. 탭 칸(높이 고정 · overflow-y:auto)이 위로 나간 말풍선을 자르므로
   ⓘ 에 커서가 있는 동안만 탭 칸 · 결과 카드의 넘침을 보이게 한다(탭 칸 내용은 500px 안이라 평소 스크롤바가 없어 폭이 안 바뀐다) */
.st-key-card_res .info-line .ib .tip{{top:auto;bottom:calc(100% + 6px);right:-6px;left:auto;transform:translateY(4px)}}
.st-key-card_res .info-line .ib:hover .tip{{transform:none}}
.st-key-card_res:has(.info-line .ib:hover),
.st-key-card_res [role="tabpanel"]:has(.info-line .ib:hover){{overflow:visible!important}}
/* 말풍선이 옆 · 아래 카드에 가리지 않게 — 커서가 올라간 카드와 그 감싸개를 맨 앞으로 */
.card:has(.ib:hover,.sub:hover),[data-testid="stElementContainer"]:has(.ib:hover,.sub:hover),
[data-testid="stVerticalBlock"]:has(.ib:hover,.sub:hover),[data-testid="stLayoutWrapper"]:has(.ib:hover,.sub:hover),
[data-testid="stColumn"]:has(.ib:hover,.sub:hover){{position:relative;z-index:90}}
/* 단, 조회 결과 탭 칸 안의 감싸개는 제외 — ⓘ 은 탭 칸 기준 absolute 인데, 커서를 올리는 순간 위 규칙이 안쪽 감싸개
   (차트 자리 container 등)를 relative 로 바꿔 기준이 바뀌면 ⓘ 이 왼쪽 아래로 밀려 커서를 벗어나고, 다시 제자리로
   돌아오며 깜빡였다. 앞으로 올리기는 ⓘ 칸 자신(z-index:90)과 탭 칸(relative)으로 충분하다 */
.st-key-card_res [role="tabpanel"] [data-testid="stVerticalBlock"]:has(.info-line .ib:hover),
.st-key-card_res [role="tabpanel"] [data-testid="stLayoutWrapper"]:has(.info-line .ib:hover){{position:static!important;z-index:auto!important}}
.kpi .s .up{{color:var(--up);font-weight:700}} .kpi .s .dn{{color:var(--down);font-weight:700}}
.ex{{display:inline-block;font-size:10px;font-weight:700;color:#b45309;background:#fef3c7;border:1px solid #fde68a;
  border-radius:5px;padding:0 5px;margin-left:5px;vertical-align:middle}}

/* ── 글 ───────────────────────────────────────────────────────────────── */
.h{{font-size:14.5px;font-weight:700;margin-bottom:11px;display:flex;align-items:center;gap:8px;color:var(--text);letter-spacing:-.3px}}
.h::before{{content:"";width:4px;height:15px;border-radius:3px;background:#2b6ef6;flex:0 0 4px}}
.h .sub{{font-size:11px;color:var(--muted);font-weight:500;letter-spacing:0}}
.note{{font-size:11.5px;color:#5d6d8c;line-height:1.7}}
.note b{{color:var(--text);font-weight:700}}
.legend{{display:flex;gap:12px;flex-wrap:wrap;font-size:11px;color:var(--muted)}}
.legend i{{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:4px;vertical-align:middle}}
.caption{{font-size:11px;color:#8494ae;line-height:1.7;margin-top:6px}}
.lede{{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;
  padding:11px 15px;box-shadow:var(--shadow);margin-bottom:4px}}

/* 원칙 목록(목업 「분석 원칙」 카드) */
.rule{{display:flex;gap:10px;margin-bottom:12px}}
.rule .ck{{width:20px;height:20px;flex:0 0 20px;border-radius:50%;display:grid;place-items:center;font-size:11px;
  background:#dcfce7;color:#15803d;font-weight:800}}
.rule b{{display:block;font-size:12.5px;font-weight:700;color:var(--text);letter-spacing:-.2px}}
.rule span{{display:block;font-size:11px;color:var(--muted);margin-top:2px;line-height:1.5}}
/* 분류체계 결합 원칙 — 두 체계 사이 「✕ 공식 직접 매핑 없음」 */
.nomap{{display:flex;align-items:center;gap:8px;margin:2px 0 14px}}
.nomap .sys{{flex:1;border:1px solid var(--line);border-radius:10px;padding:8px 10px;text-align:center;
  font-size:12.5px;font-weight:700;color:var(--text);background:#f6f9ff}}
.nomap .sys small{{display:block;font-size:10.5px;font-weight:500;color:var(--muted);margin-top:1px}}
.nomap .x{{flex:0 0 auto;text-align:center;color:#d64545;font-size:16px;font-weight:800;line-height:1}}
.nomap .x small{{display:block;font-size:10px;font-weight:600;margin-top:3px;white-space:nowrap}}

/* 순위 목록(목업 「주요 수입국」 카드) */
.rank{{display:grid;grid-template-columns:22px 92px 1fr 66px;align-items:center;gap:9px;height:29px;font-size:12px}}
.rank .no{{width:20px;height:20px;border-radius:50%;background:#eef2f9;color:#5a6b8c;font-size:10.5px;font-weight:800;
  display:grid;place-items:center}}
.rank .nm{{font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rank .tr{{position:relative;height:11px;border-radius:4px;background:#eef2f9}}
.rank .fl{{position:absolute;left:0;top:0;bottom:0;border-radius:4px;animation:grow .7s cubic-bezier(.18,.89,.32,1.1) both}}
@keyframes grow{{from{{transform:scaleX(0);transform-origin:left}}to{{transform:none}}}}
.rank .vl{{text-align:right;font-weight:700;color:var(--text);font-size:11.5px}}

/* 점유율 막대(홈 오른쪽) */
.bars .row{{display:grid;grid-template-columns:128px 1fr 52px;align-items:center;gap:8px;height:21px;font-size:11.5px}}
.bars .nm{{color:{TEXT};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bars .nm em{{color:{MUTED};font-style:normal;font-size:10px;margin-left:3px}}
.bars .track{{position:relative;height:12px;border-radius:4px;background:{PANEL2}}}
.bars .fill{{position:absolute;left:0;top:0;bottom:0;border-radius:4px;animation:grow .7s cubic-bezier(.18,.89,.32,1.1) both}}
.bars .ref{{position:absolute;top:-4px;bottom:-4px;left:50%;border-left:1px dashed #94a7c8}}
.bars .pct{{text-align:right;color:{MUTED}}}

/* 국외조달 절차(정책·산업 배경) — 원 → 화살표 → 원 */
.proc{{display:grid;grid-template-columns:1fr 30px 1fr 30px 1fr;align-items:start;padding:6px 0 2px}}
.proc .st{{text-align:center;animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both}}
.proc .st:nth-child(3){{animation-delay:.12s}} .proc .st:nth-child(5){{animation-delay:.24s}}
.proc .ci{{width:88px;height:88px;margin:0 auto;border-radius:50%;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:3px;color:#fff;box-shadow:0 6px 18px rgba(43,110,246,.26)}}
.proc .ci span{{font-size:23px;line-height:1}}
.proc .ci b{{font-size:15.5px;font-weight:800;letter-spacing:-.3px}}
.proc .ar{{margin-top:30px;text-align:center;font-size:21px;color:#8fb3f4}}
.proc .ds{{margin-top:12px;font-size:12px;color:#44567a;line-height:1.55}}
.proc .n{{margin-top:8px;font-size:22px;font-weight:800;color:#1c4ea3;letter-spacing:-.5px}}
.proc .n small{{font-size:12px;color:var(--muted);font-weight:600;margin-left:3px}}

/* 입찰 공고 ↔ 결과 매칭 깔때기(DATA CENTER) — 층마다 사다리꼴 하나 */
.funnel .fr{{display:grid;grid-template-columns:1.3fr 1fr;align-items:center;gap:10px;height:52px;margin-bottom:6px}}
.funnel .tz{{height:100%;display:grid;place-items:center;color:#fff;font-size:19px;font-weight:800;letter-spacing:-.3px;
  animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both}}
.funnel .lb{{display:flex;align-items:center;gap:8px;font-size:12.5px;font-weight:600;color:var(--text)}}
.funnel .lb::before{{content:"";flex:0 0 34px;border-top:2px dotted #b7c7e2}}
.funnel .lb small{{display:block;font-size:11px;color:var(--muted);font-weight:500;margin-top:2px}}

/* ── 위젯 ─────────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div{{background:#fff;border-color:var(--line);border-radius:10px}}
[data-testid="stSegmentedControl"] button{{border-radius:9px}}
[data-testid="stDataFrame"]{{border-radius:12px;overflow:hidden;border:1px solid var(--line)}}
[data-testid="stExpander"]{{background:#fff;border:1px solid var(--line)!important;border-radius:12px;box-shadow:var(--shadow)}}
.stButton button,.stDownloadButton button{{border-radius:10px;font-weight:600}}
</style>"""

st.html(CSS)

# ── 라이트 테마 고정(위젯) ───────────────────────────────────────────────────
# 저장소의 .streamlit/config.toml(운영 앱용 다크 테마) 아래에서 열거나, 테마 설정 없이 OS 다크모드에서 열면
# 버튼 · 분석영역/HS 선택 · 체크박스 · 선택창이 어두운 바탕 · 흰 글씨 · 다크 강조색으로 그려졌다(조원 PC 에서 본 증상).
# 이 파일만 받아 실행해도 같은 화면이 나오게 테마가 칠하는 색을 여기서 직접 정한다.
# 아래 규칙보다 뒤에 오는 칸별 규칙(.st-key-… — 국가 칩 · 차트 유형 버튼 · ⓘ 단추)이 명시도가 같거나 높아 그대로 이긴다.
st.html("""<style>
:root{color-scheme:light}
[data-testid="stMain"],div[role="dialog"]{color:var(--text)}
div[role="dialog"]{background:#fff}
/* 버튼 — 기본(흰 바탕) · 강조(파랑) */
button[data-testid="stBaseButton-secondary"]{background:#fff;border-color:var(--line);color:var(--text)}
button[data-testid="stBaseButton-secondary"]:hover{border-color:var(--accent);color:var(--accent)}
button[data-testid="stBaseButton-primary"]{background:var(--accent);border-color:var(--accent);color:#fff}
button[data-testid="stBaseButton-primary"]:hover{background:#1f5fe0;border-color:#1f5fe0;color:#fff}
/* 분석영역 · HS 단위(segmented_control) — 고른 칸은 연한 파랑 바탕 · 파란 테두리 · 파란 글씨 */
button[data-variant="segmented_control"]{background:var(--bg);border-color:var(--line);color:var(--text)}
button[data-variant="segmented_control"]:hover{color:var(--accent)}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"][aria-checked="true"][data-selected]{
  background:rgba(43,110,246,.1);border-color:var(--accent);color:var(--accent)}
/* 체크박스 — 네모 칸 */
[data-testid="stCheckbox"] label > div:not([data-testid]){background:#fff;border-color:#b7c4da}
[data-testid="stCheckbox"] label:has(input:checked) > div:not([data-testid]){background:var(--accent);border-color:var(--accent)}
[data-testid="stCheckbox"] label:has(input:disabled){opacity:.45}
/* 선택창(selectbox · multiselect)과 펼친 목록 */
[data-testid="stSelectbox"] div[role="group"],[data-testid="stMultiSelect"] div[role="group"]{background:#fff;border-color:var(--line);color:var(--text)}
[data-testid="stSelectbox"] div[role="group"]:focus-within,[data-testid="stMultiSelect"] div[role="group"]:focus-within{border-color:var(--accent)}
[data-testid="stSelectbox"] input,[data-testid="stMultiSelect"] input{color:var(--text)}
[data-testid="stSelectbox"] input::placeholder,[data-testid="stMultiSelect"] input::placeholder{color:var(--muted)}
[data-testid="stSelectbox"] div[role="group"] button,[data-testid="stMultiSelect"] div[role="group"] button{color:var(--muted)}
[data-rac][data-trigger="ComboBox"]{background:#fff;border-color:var(--line);color:var(--text)}
[data-rac][data-trigger="ComboBox"] [role="option"] *{color:var(--text)}
/* 도움말 말풍선(help=) · 안내 상자(st.info) */
[data-testid="stTooltipContent"]{background:#fff;color:var(--text)}
/* 도움말 말풍선 글씨 — 기본(14px)보다 2pt 작게 */
[data-testid="stTooltipContent"],[data-testid="stTooltipContent"] p{font-size:calc(14px - 2pt)}
[data-testid="stAlertContainer"]{background:#eaf1ff;color:#1c4ea3}
</style>""")

# ── 막대·선 그래프 등장 연출(plotly) ─────────────────────────────────────────
# 막대는 왼쪽 것부터 차례로 바닥에서 자라고(가로 막대는 왼쪽에서 뻗고), 선은 왼쪽에서 오른쪽으로 그려진다.
# 옅은 그림자로 입체감을 준다. 차트가 새로 그려질 때(페이지 이동·창 크기 변경)마다 다시 재생된다.
_STAGGER = "\n".join(
    f".js-plotly-plot .barlayer .point:nth-child({i}) path{{animation-delay:{0.05 + i * 0.07:.2f}s}}\n"
    f".js-plotly-plot .barlayer .point:nth-child({i}) text{{animation-delay:{0.45 + i * 0.07:.2f}s}}"
    for i in range(1, 16))
CHART_ANIM = f"""<style>
.js-plotly-plot .barlayer .point path{{transform-box:fill-box;transform-origin:50% 100%;
  animation:barY .75s cubic-bezier(.6,0,.25,1) both;filter:drop-shadow(0 3px 4px rgba(19,42,84,.18))}}
.st-key-card_fsg .barlayer .point path,.st-key-card_fsc .barlayer .point path{{transform-origin:0 50%;animation-name:barX}}
.js-plotly-plot .barlayer .point text{{animation:barTxt .4s ease both}}
@keyframes barY{{from{{transform:scaleY(0)}}to{{transform:none}}}}
@keyframes barX{{from{{transform:scaleX(0)}}to{{transform:none}}}}
@keyframes barTxt{{from{{opacity:0}}to{{opacity:1}}}}
.js-plotly-plot .scatterlayer .trace:has(.js-line){{animation:lineIn 1.5s cubic-bezier(.65,0,.35,1) both}}
.js-plotly-plot .scatterlayer .trace:nth-child(2):has(.js-line){{animation-delay:.18s}}
.js-plotly-plot .scatterlayer .trace:nth-child(3):has(.js-line){{animation-delay:.36s}}
.js-plotly-plot .scatterlayer .js-line{{filter:drop-shadow(0 5px 5px rgba(43,110,246,.28))}}
@keyframes lineIn{{from{{clip-path:inset(-20px 100% -20px -20px)}}to{{clip-path:inset(-20px -20px -20px -20px)}}}}
/* 마리메코는 칸마다 자라면 비율을 읽기 어려워 뺀다 */
.st-key-card_mekko .barlayer .point path,.st-key-card_mekko .barlayer .point text{{animation:none;filter:none}}
{_STAGGER}
</style>"""
st.html(CHART_ANIM)

# ── 공급망 현황 표 · 핵심 지표 · HHI 게이지 · 탭 ─────────────────────────────
st.html(r"""<style>
.sc{width:100%;border-collapse:collapse;font-size:12.5px}
.sc th{font-size:11px;font-weight:700;color:#5a6b8c;background:#f3f6fc;padding:9px 6px;text-align:center;
  border-bottom:1px solid #dde5f2;line-height:1.35;white-space:nowrap}
.sc th small{display:block;font-weight:500;color:#6b7a99;font-size:10px}
.sc td{padding:9px 6px;text-align:center;border-bottom:1px solid #eef2f9;color:#16233f;white-space:nowrap}
.sc td.no{color:#6b7a99;font-weight:700}
.sc td.nm{text-align:left;font-weight:700}
.sc td.nm em{display:block;font-style:normal;font-weight:500;font-size:10.5px;color:#6b7a99}
.sc tbody tr{animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both;transition:background .15s}
.sc tbody tr:nth-child(2){animation-delay:.06s} .sc tbody tr:nth-child(3){animation-delay:.12s}
.sc tbody tr:nth-child(4){animation-delay:.18s} .sc tbody tr:nth-child(5){animation-delay:.24s}
.sc tbody tr:hover{background:#f5f9ff}
.sc td.up{color:#e5484d;font-weight:700} .sc td.dn{color:#2b6ef6;font-weight:700}
.sc td.lv{font-weight:700} .sc td.lv i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
.demo-bar.real{background:#ecfdf3;border-color:#abefc6;border-left-color:#12b76a}
.demo-bar.real b{color:#067647} .demo-bar.real span{color:#085d3a}
.basis{width:100%;border-collapse:collapse;font-size:12px}
.basis th{font-size:10.5px;font-weight:700;color:#5a6b8c;background:#f3f6fc;padding:7px 4px;border-bottom:1px solid #dde5f2;line-height:1.3}
.basis td{padding:5px 4px;border-bottom:1px solid #eef2f9;text-align:center;white-space:nowrap}
.basis td.nm{text-align:left;font-weight:600;color:#16233f}
.basis td.nm em{font-style:normal;color:#6b7a99;font-size:10.5px;margin-right:6px}
.basis td.cat{color:#6b7a99;font-size:11px}
.basis i{display:inline-block;width:12px;height:12px;border-radius:50%;animation:rise .4s ease both}
.basis tbody tr:hover{background:#f5f9ff}
.basis.asof td{white-space:normal;line-height:1.35}   /* 자료별 기준일 — 기준 설명은 줄바꿈 허용 */
.basis.asof td.nm{white-space:nowrap}
.spark{display:block;margin:0 auto;animation:revealX 1.3s cubic-bezier(.65,0,.35,1) .2s both}   /* 왼쪽부터 그려지듯 드러난다 */
.sc tbody tr:nth-child(2) .spark{animation-delay:.3s} .sc tbody tr:nth-child(3) .spark{animation-delay:.4s}
.sc tbody tr:nth-child(4) .spark{animation-delay:.5s} .sc tbody tr:nth-child(5) .spark{animation-delay:.6s}
@keyframes revealX{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}

.kgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}   /* 좁으면 1열, 넓으면 2열 */
.kc{display:flex;gap:12px;align-items:center;padding:14px 12px;border:1px solid #dde5f2;border-radius:12px;background:#fff;
  animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both}
.kc:nth-child(2){animation-delay:.07s} .kc:nth-child(3){animation-delay:.14s} .kc:nth-child(4){animation-delay:.21s}
.kc .ic{width:44px;height:44px;flex:0 0 44px;border-radius:50%;display:grid;place-items:center;font-size:20px}
.kc .ic .ms{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;font-size:22px;line-height:1;
  letter-spacing:0;font-feature-settings:'liga';-webkit-font-smoothing:antialiased}
.kc .l{font-size:12px;font-weight:700;color:#44567a}
.kc .v{font-size:26px;font-weight:800;color:#12234a;letter-spacing:-.8px;line-height:1.2;margin-top:3px}
.kc .v small{font-size:12px;color:#6b7a99;font-weight:600;margin-left:3px;letter-spacing:0}
.kc .s{font-size:10.5px;color:#6b7a99;margin-top:3px;line-height:1.4}

.bars.big{display:flex;flex-direction:column;gap:5px;margin-top:4px}
.bars.big .row{height:30px;font-size:12.5px}
.bars.big .track{height:16px;border-radius:5px}
.bars.big .fill{border-radius:5px}

/* 탭 메뉴 — 북마크(폴더) 탭: 고른 탭이 아래 패널과 한 장으로 이어진다 */
[data-testid="stTabs"] [role="tablist"]{gap:4px;flex-wrap:wrap;align-items:flex-end;border-bottom:none;box-shadow:none;
  padding:6px 0 0 14px;margin:0;overflow:visible;position:relative;z-index:1}
[data-testid="stTabs"] [role="tablist"]::after,[data-testid="stTabs"] [role="tablist"]::before{display:none}
[data-testid="stTabs"] [data-testid="stTab"]{height:auto;padding:8px 18px 9px;margin:0 0 -1px;border:1px solid var(--line);
  border-bottom:none;border-radius:12px 12px 0 0;background:#e4ebf6;box-shadow:none;
  transition:background .15s,padding .15s}
[data-testid="stTabs"] [data-testid="stTab"]:hover{background:#edf2fa;padding-top:10px}
[data-testid="stTabs"] [data-testid="stTab"] p{font-size:12.5px;font-weight:700;color:#5b6f94;line-height:20px!important}   /* 이모지(📈 · 🗺️ · 📋)마다 줄 높이가 달라 탭 높이가 들쭉날쭉하지 않게 */
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"]{background:#f8fafe;padding-top:12px;
  border-top:3px solid var(--accent);box-shadow:0 -4px 10px rgba(19,42,84,.06)}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] p{color:var(--accent);font-weight:800}
[data-testid="stTabs"] [data-testid="stTab"] > div:not([data-testid]){display:none}   /* 기본 밑줄 */
[data-testid="stTabs"] [role="tabpanel"]{background:#f8fafe;border:1px solid var(--line);border-radius:0 14px 14px 14px;
  padding:18px 16px 16px;box-shadow:var(--shadow)}
/* 조회 — 분석 조건 설정 카드(목업) */
.st-key-card_form{padding:18px 18px 14px}
.st-key-card_form h3{font-size:21px;font-weight:800;color:#12234a;letter-spacing:-.5px;padding:0;margin:0}
.st-key-card_form [data-testid="stIconMaterial"]{color:var(--accent)}
.st-key-card_form [data-testid="stMarkdownContainer"] p{margin:0}
.st-key-card_form [data-testid="stMarkdownContainer"] strong{font-size:14.5px;font-weight:800;color:#16233f;letter-spacing:-.3px}
.st-key-card_form [data-testid="stMarkdownContainer"] p [data-testid="stIconMaterial"]{font-size:21px;vertical-align:-5px}
.st-key-card_form [data-testid="stCheckbox"] label p{font-size:13px}
.st-key-card_form [data-testid="stHorizontalBlock"]{margin-bottom:4px}
/* 조회 결과 — 탭(차트 · 지도 · 표)을 바꿔도 창 크기가 그대로이게 탭 칸 높이를 고정(차트 탭 기준) */
.st-key-card_res [data-testid="stTabs"] [role="tabpanel"]{height:500px;box-sizing:border-box;overflow-y:auto}
/* 내려받기(차트 · 지도 = 그림, 결과 표 = CSV) — 탭 칸 오른쪽 아래, 차트 캡션(그래프 기준 …)과 같은 줄로 끌어올린다 */
.st-key-res_dl{margin-top:-78px;padding-right:22px;position:relative;z-index:2;pointer-events:none}
/* 분석 조건 설정 · 조회 결과 — 두 카드 세로 길이를 긴 쪽에 맞춘다(국가 칩이 늘어도 같이) */
[data-testid="stLayoutWrapper"]:has(> .st-key-card_form),[data-testid="stLayoutWrapper"]:has(> .st-key-card_res),
.st-key-card_form,.st-key-card_res{flex:1 1 auto}
.st-key-res_dl button{pointer-events:auto}
/* 탭마다 내려받기 단추가 다르다 — 지금 고른 탭(aria-selected)의 단추만 보인다.
   단추 칸을 감싼 바깥 칸(stLayoutWrapper)까지 숨겨야 숨은 칸이 자리 · 간격을 차지하지 않아, 어느 탭이든 같은 자리(오른쪽 끝)에 온다 */
.st-key-dl_chart,.st-key-dl_map,.st-key-dl_tbl,
[data-testid="stLayoutWrapper"]:has(> .st-key-dl_chart),[data-testid="stLayoutWrapper"]:has(> .st-key-dl_map),
[data-testid="stLayoutWrapper"]:has(> .st-key-dl_tbl){display:none!important}
.st-key-card_res:has([role="tab"]:nth-of-type(1)[aria-selected="true"]) .st-key-dl_chart,
.st-key-card_res:has([role="tab"]:nth-of-type(2)[aria-selected="true"]) .st-key-dl_map,
.st-key-card_res:has([role="tab"]:nth-of-type(3)[aria-selected="true"]) .st-key-dl_tbl{display:flex!important}
.st-key-card_res:has([role="tab"]:nth-of-type(1)[aria-selected="true"]) [data-testid="stLayoutWrapper"]:has(> .st-key-dl_chart),
.st-key-card_res:has([role="tab"]:nth-of-type(2)[aria-selected="true"]) [data-testid="stLayoutWrapper"]:has(> .st-key-dl_map),
.st-key-card_res:has([role="tab"]:nth-of-type(3)[aria-selected="true"]) [data-testid="stLayoutWrapper"]:has(> .st-key-dl_tbl){display:flex!important}
.st-key-imgdl_js,[data-testid="stLayoutWrapper"]:has(> .st-key-imgdl_js){display:none!important}
.st-key-chipfit_js,[data-testid="stLayoutWrapper"]:has(> .st-key-chipfit_js){display:none!important}
/* 안 잘린 칩에 커서가 있을 때(_CHIP_FIT_JS) — 말풍선 층을 숨긴다 */
html[data-chipfit] [role="tooltip"]:has([data-testid="stTooltipContent"]),
html[data-chipfit] [data-testid="stTooltipContent"]{display:none!important}
.img-dl{display:inline-flex;align-items:center;gap:6px;height:40px;padding:0 16px;border-radius:8px;border:1px solid #2b6ef6;
  background:#2b6ef6;color:#fff;font:600 14px Pretendard,'Malgun Gothic',system-ui,sans-serif;cursor:pointer;white-space:nowrap;
  transition:background .15s}
.img-dl:hover{background:#1f5fe0;border-color:#1f5fe0}
.img-dl:disabled{opacity:.7;cursor:progress}
.img-dl .ms{font-family:'Material Symbols Rounded'!important;font-size:19px;line-height:1;font-weight:400;font-feature-settings:'liga'}
.kpis.q{gap:10px;margin-bottom:6px}
.kpis.q .kpi .v{font-size:23px}
</style>""")


# ════════════════════════════════════════════════════════════════════════════
# 2. 공용 요소
# ════════════════════════════════════════════════════════════════════════════
def info_btn(text: str) -> str:
    """카드 오른쪽 위 ⓘ — 커서를 올리면 text(HTML) 말풍선이 뜬다. 제목 줄(.h · .kt) 끝에 넣는다."""
    return f'<span class="ib"><span class="ms">info</span><span class="tip">{text}</span></span>'


def info_line(text: str) -> str:
    """카드 제목이 없는 자리(차트 아래 등)에 두는 오른쪽 끝 ⓘ 한 줄 — 말풍선은 위로 연다."""
    return f'<div class="info-line">{info_btn(text)}</div>'


def kpi(label: str, value: str, unit: str, sub: str, tag: str = "", icon: str = "bar_chart", info: str = "") -> str:
    t = f'<span class="ex">{tag}</span>' if tag else ""
    # 긴 제목(공백 빼고 10자 이상) · 긴 숫자(8자 이상, 예: 2016–2026)는 글씨를 줄여 한 줄에 맞춘다
    lc = " long" if len(label.replace(" ", "")) >= 10 else ""
    vc = " long" if len(value) >= 8 else ""
    return (f'<div class="card kpi"><div class="kt"><span class="ico"><span class="ms">{icon}</span></span>'
            f'<div class="l{lc}">{label}{t}</div>{info_btn(info) if info else ""}</div>'
            f'<div class="v{vc}">{value}<small>{unit}</small></div>'
            + (f'<div class="s">{sub}</div>' if sub else "") + '</div>')


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


# 히어로 그림 — 목업(그림 참고.png)의 구축함 · 전투기 부분(가로 830~1250 · 세로 0~87px)을 그대로 잘라 넣었다.
# 원본이 작아(87px) 브라우저가 늘리면 흐려지므로, 미리 6배로 늘리고(LANCZOS 2단계) 단계마다 윤곽을 선명하게
# (언샤프 마스크) 한 WebP. 파일 하나로 돌아가게 이미지 파일 대신 base64 문자열로 둔다(약 96KB).
# 좌우 끝은 CSS 마스크로 배경에 녹이고, 불투명도 30%
HERO_IMG = ("data:image/webp;base64,"
    "UklGRlh3AQBXRUJQVlA4IEx3AQAwGAidASrYCQoCPjEYikOiIaOqp/MJuVAGCWVulq7l7zC8erT4JOCnW9J+p63iZ+hs/ULPisdPfbeB96n/q/"
    "PE9WTEJ+L9Fr/LeoTnf0kf/N6W1Ij/r79G69N8aSXy+l5V3LPhX8//Gf6b/uf5b59/7n7Y+LXy//a/bP07/X/6z/0f6T82/lf/1P/j/v/978SP"
    "5v/n//f/p/3//6P2KfrD/0/8B/ofgf/7/3f+EX98/8/q9/sX/J/c73cf/f+7nwo/uHqU/0v/if/3/m+/l61P/V9Ujzdf/j+6//X+Zf+of879sf"
    "+n8Iv+Y/+f+w9wD//+330C/g3/w9DXxX+8/6Xi/+Rfc/8f/IfvL8O2W/3zwS/m361zFd0v4z/fehH+P/1D/o/4b1p/8PQ/4X/3ejj9I/yf/95O"
    "9Vf1x/2ezP/QP+fz8/9HoOv+jz//j/oSf4ISzOi2lpdIrxwclUFMMKR+yEs0d4d5KAD3ejtHSW0nbI2Y+T5tdKMx7ha+i6GUZQoly0Gl/lYAbh"
    "f3MvvhmUDjjMlqOkUYcpLuq5asPUxOXFyX8i28C6MmYDEIUuq5SbIjuM82qcDZpLisJYNfuraC9KA1MUAlxiuLYiB/rl6FiXWxkWEwEMM6Ew7Z"
    "rEw7Kuz9zETDRE+4Zba6I9HekSZo9ag0bk9HQXy9cjKsqXwmN30NsJHf5C8p9j2VW/raWjrRzxspyy0OiulWakHpjv6s4HlADIH2EMuGINvafX"
    "3y1Yc+PBCNJf/6oltw/j8subBhLC80mGlbeLmpPKVIwKLqTydqprwIR/SbZl9ZqKhTrbIkva4PNJlsXp9eev///iQH3GR8VVkPL72btyXGUNmD"
    "kuEMDmvOT6U3NNAs88UpuCDRKgIkXNH5U2IcpX0y2am2mzEfOI50yYpArGA+QFn0uLRknMz0GY/W+dppTu5FHXyFEM7Rau5Op/cdaO5B1rfKAU"
    "GmOTJSybEHqMt2M7qS2q4OBKw++tA0ZGWtcI1TbP1iA+lQFh1K+uLLLb5X48kf++1yO5dUe1qatyZf9oSdLG7h22fnd67SohnGARI8dYzYF+SF"
    "cFBJRyIfX4Td6sJ9NGKASK4kaLvvT4UYHz5yYBpCTWDupoowchlsyDsrPmFvRViRYsgNetYEexiv6f48geAZYroWWr7aTKJbUjLvD5YW9FPtyM"
    "OkTjecT1JzwjN8hw7LSarTIL86Ap1oWVhz/qGS9twSmOiN1aBxFePCf68hnh9g20qY0FTb5DAHGsB9mVMbA1vAzZ3M0NbVxhEIlm4ANoziUYm+"
    "Y0qFENsckIr7LazIf/5FmgMOA85fTd3//R2K04LddNxTf+rd06t1JNtW6T89pKKS6DgYBgeCylzKkQnUnUrzvxNq6Nzj+86Et1rOpFB00NNLVy"
    "H5p4pgGQ7/2SUe3n+r7rOx/S3jVULe3bQCTQuAXODEQuKPa1bS8/+Nm75XLr8gsJxanWfkJZ1jOH2NGqKsZyDjccYMlNim/YjRJHGJ+jZ/EKqw"
    "hiEEbSGsvZvx3u8HjnsELKR9Od6evrS7lcopTPJYv1ivtJ9T3EfzDVb9KZCQDrCCvVkR+mew3Fuo3QSs452gjFGGYkTEgpfjZ/Uw+yoW171Z1t"
    "AG5LOeZGKL1s0gkEjnyw66pCwXvr56L//8BspqTIy7NERaVdj9Spt6BQIcLH//0vxWyg1kGU6Ezh3kr+f/5+4eizGVHiawHWBhX6ia2Ag1UZIm"
    "R43/BdXF+uRghKQuvADbrjADX2zkIZLyw/+Iauaacg2B+EJzokSp1VUF28T0aeaCr5HHX7f+NybFyN9rAxXmefDqdvKR4UcOfQ4f6eQImb0VjE"
    "L6r01KB51GCgpwa97x8Eb4IiYq/wI4Y+x/WtmvNxiy2BIBz6PsAcuEtZ9hedhiktg1h4ZxIhSf6TINn6Z7omX13ifeYPqA3v5zNkjWpyJFRRkk"
    "QyIUboSVumDaQx7g45VUW7TfcKXsmI6QgqowSto0IrC0G6BeWBSfellh2k6do5Gf5WNlXn6jcEPQMNNePNSp5pFWsbsLAjhyiqsL402X5nWTyw"
    "EQUKETa06ElCGbraMoeC/9GizqbjVYNk8m2I1VD76BmVMTI2iQ3+RaMJ7tmz6Ny3KjCpbsu+OvoRI6xAE2EM8leSBExWSpmOZWPCpdp8ZrBhXP"
    "ZYFI9/vCI4FJekqwppygbcBhZIPdvzanDhTzpUJFfbM+2LLtXvw4K/bZIoFwk0x0dZlqeT+mdmZR//57qJlvfNp9aNBG2X75vchLCOh0SC5TE+"
    "E+mjzulNvl9mromgGFKhWRPBkvlyRqqULA3+ZlVgzUg60ng9ZXbGwhFaJvmswFgfkSQhGb735B5036V8OaapxGX//88hodnoF2S7CY4osFttkv"
    "ZGm/l94Es/jpACMh2d67w8xqNHqNxucT9KmmSV5joj/ly2oL92hLzYlSGrcvSHr4GalxD3wzF/Hpei/6bIzt1bxGAo+ECmTUJCh31smp1DF0vA"
    "YlHNQCdq68oHLTO7Dco4AQWHV6iRpJDeBqrsZ+4S3MimRXraz2HiCvrDIrlzwommnW1gqpD3YOent81OWYMV+X9R4miyJEn3HPJtfR5/6OKx+u"
    "SV66qo2E+ecYyP/rKkUUa6nFyKcMrcQpNEheKNj+Dy9WiG8At1baPi3MpdnV6n+mj8euTLvZacylRqPDmJhrlsiQjt8TfQv7htILOrLcj4/DnD"
    "s+aqZi4gp1tnJNPA/89KR5cmt414VICJZ9BjLyelNYrnVHJNj4KQAOPR7lKDB2QzEoE8fHt88/T/152F0pAplHiTQiRZSSGBJ7n1scFwbqaxvP"
    "vXyDHSEwg3mZSzIMgQ0QShesnYCObv0MAwqaDmBTuiWot1YA+LJAf5N3Vhs0fFvRmLQZjk58adrp68ssPFuFFkDpm3vOwnYQoeP+Sr7Hv9jlUg"
    "iRubUh+HYT+RVNPCPZPjFWUkOHof3bnAUDHKIWfExWCacheAxIVeGNAS2jzhAKOnzbmIsCrLeNYo8ckqLGLszn9HrAJNJ3O+qPp+JdLk9gFDAF"
    "g/AP+ZHy/DOSHk4f7wwLApCwwG5SQAeHWm8oayfz3CFsx8ltewiO5uahNdJC2509vq+ysY8LCmkPWZmWAHdS8Jt7d5HMscHztT6mnHd6jy9Mt/"
    "l8OKagQCLxyjK26IOW66Dd8FLgqnP5Suf6vMdZd28RO5xnsU5YHhhY/XKwsTRug2jOpjIM8osERSdOo77YFMuFeAAaPi3LroLqYVwNvaXPaIrH"
    "8FukuW21GC4T370VpSMBs46B/wqinfefNcMF0FV1CGe497I6RqGlCYM/76qfq4JhHhzMi2yDLpvNZPxvvOebVns0SxhAE/y3Z8Q94xVZLe2PBN"
    "2H3JVQBocXrMjGctg67EihI7NZZLNEYjixW5Gf3wNV6Wv4ivHxlX8pGI/KgbfpYT8hmCLGk2Zeq8DNf/671WyHmWs61wgBsl8mJiu4yNaicEKM"
    "p3qVMCmbiiS2LKX3e0OE0BPxTd3z5JumC45DMb7bH0WwlZT57wKWHVsC/ks84N9q691DFRGjZ8Q7Ls6h7wmuhfeur8n4f1Y5hozrZvH82oqcV+"
    "LXdIavt88bUiaGR0Ko3kPeGq+bto8FuYNQAumkjQ+LYOTGiovRBv3hlmsiZdjcr31BiL2w+LKGyqXa3Lk6XIGT4oQMB3+8ucVcDHGdy28JP5H+"
    "OO98LNKiD/lgHKO135dgxIwkT42GdKfY/H5ToHjCm6V3L/wzqrUakSrRhftNUsqFVdRINjx4PEbShGyDkOhCWSvUReLFsNWU1FNF/4FLIitoTr"
    "IBxNIqalLOHaMPQXiUj7zNIcdr8isatINRui1Xj/URkdwPP8fkcPpOylx0zsb4lvbXQZKUQPU9i1B6RkyoSUbms1qqmP9wbXFNfdObgZwkFUXA"
    "6TQJz5uw7BuVYWiESQMIm0rqNBbwWIiNICR24yw9KsgafB8NADLUbWlPf+tlAMlCyR76RhvuwlKviuOjuEFm4pmeNKgoFhV/Zhqnwr43I0e1/+"
    "c9vmpX5pIvRop7eXoQZZrRzV/R1zgutQuNfC3zM8F3/YzV1/V289XaOo4B+V4n3czmb36q8HL3AKmlhZsMnhQyepMztm8tWk5KlvyoWV/ndMAM"
    "niG2FAXtmbFXo061kdnxix1WEOav2JBoO9TjdPYXFFgU6lAKUZxnCAw+V/2iVIAnlgozRUxcOQej+BQ6Pb3X2HueJvLu40cpIokv00n5CgnGCV"
    "uueuf5+Zcc5k10/27xeHqvhrQn5dDJR4Pk2Wh8Pge9uwQ6SVU6hd3tEqGKBLOjjVOd0oQ7AT+2wEdtEh7t3U4YSR+zZf9fQ3GRZNXNiaVc3bcj"
    "voPctIxYAsA2K1QvqsB7cZAS7RdayR16liFobUWYFO+7O9CnczJLue2YqlOH6XqKIj+6CMHDNwtBMe5oyw5M/PWvLq5cgVO5LX1WFvbf/uX3pZ"
    "00CifXiAvjBKxpy8iI+jbTCiB4XRESukwBOaR1EqERIMabrnlJIEhpykjOmqGzRk42ixXI5yHFjIieWDhSef0mUQn0sZe7S194RjyzRhnBVUeF"
    "SMMaLRPI6zOpQwKWEY5CWO7daXVs9S39vyzMQ5vs7bLuz9TSESA+mUHdR8T5/3gw7oELW/nRpJ3RP3mWBOIjXDSsbIgpWN6hU5OgEfQuA8lLcY"
    "Cktzrv0D/MFFIKcDOEa8xlXsa0LcZ3tfJ+IsKHEHCOE/u7YT/TJo0KOAJjHsuTUktO12pDOkqAO+lHDO/tlq6Ptj/DtqRiGgMRTZM53rrb5J0k"
    "ZSc+btHGsCgnD2bECRfjPpB2TOHy8utUdOrQMmOHW8MQCGbU4vLNIxO7y3j+CkDyy7iJQmZF3lTovIWqYkLmiJoovApqQ5P0rDtt2BcDC504Vm"
    "CIswlp9TE6rgW/KOQWLXAtlTRloromolzt8bji0GhPdvW1oXdPjTDAUM12ZklLOUCRq5DwBL6j+0dzFAD//EZnBvj1HFtvczhiD0RvBeDaIjIh"
    "7OCVpHxKMa1pVJjItV/LUUSXJLivm2zpoIGPp/keFnfpx8yu1mQUA7EB3c5xb9A+1QOnJWr4t5dm8zYN3s8fCz22GOUGedvAjGD1fMDdqrlgn8"
    "jb03bvR8GNC/JTdJOC1dhxFbZeUdY8/1W49ayfsSPBfUzTTrg7wb41tSEigLJMpIT45yqZ/v8ZI8kMH6zV22eq6XoVpleG3BpOQiIyxr1gNU7k"
    "/IEos/dAxllZjsahRyXM2yudo3t+d99CdMqHh/75N0DpOS2/PLBHuQQEgWep5hvdYTRcw4vP7vjPrVYX43BtGy7TbFz2Mv6QMDiZQH2J2wgSPS"
    "VlGKGTGettPDyVz+MfUPiAnvmaMpIR4yXUBhCGaeXQ/i0VdodNt3buF60wTTnFwcu7aUw/OtZOzEpOtxkxy49mhP/GW4otUWgsQf/66/Tm/mpZ"
    "gIWssy9YU3gvU/TzUpnYKp/pixjxG5P5hFpP0GBVh1gdHfFnV6WHotMbYa08wOLCynREPhPfcn9oiwkIUl0genFy21HHZfNikiAFU+Q70YFhfO"
    "wOr3h6gOm3q0ZLQV70bPk319wUCA48ZzJ63uRI9F8fwjWnUUaqsEEcH9d0zwh2U5KiS4EFoOoRKZZD+hLvjT0d6bjS5Z0TdUOm6BKhPXiiLycB"
    "aLucOkrwhqxo8769C1CWlg+63gGjXkUFrKpP59BHeKq/DqmPhNw5lkfCmgK/8DvrxWofyT7H6yGON8mHtXyRckhGNLuPflNxBwwtLj81RUytSG"
    "YyM4vy9OqShl8KaA2MhJHY8zrW67gxmrjKnQM0xXU824cIZgkI+Wubw9kPOVTP9dqMhvaIyrO+vKZt5x8as1gAJLu/SLB4Jaf1BmJSsnCzBJjj"
    "KYdrWreXVqlLsl1qTDz7zuYP2qgwtJpB7W+O8Y7zNPUrjC/cr5yZQXTXADtQtFe3a0LX/Zl3sQsHZY9YVQ4hHvHRX8ayaS/6SwftEiNvDLf/mV"
    "s7XpZ7/1C4VIXlqygbuL1oy5nLS0g5YsIe40X9BJO+GtYaV3Wpz3azy4zM5ptP2gfLRg+AcVLc1+SjXs6c/Gza3DyGDvgsGUkjC7Suw3yl0jod"
    "Z/3lnVpZgMce5B7/flc8Y2iHJKjAX7SRk5TtxDs+EnDwvz9MO859O6xskL4CCr37vlq18625urfxpILsrokp7etxN3ucjO1Sjp/g+glYPvOcwU"
    "YqnEU9QNY4oIoJH87Mg6uxxH6GuwgrFW76RHmNDt99hJs+uGIhIahXmUoyrfwWeDfwqEQqrrBcCVxBWIfyXAjsVxY1QtzQzGg2ciENvVUGWqFy"
    "VV4GzqB2RH2pteyBaYX9+1v2K6mx8Acl0AF1tvDC2O29Cpgq5fkgYoEiKcAYvmH8dX5aERCNU3Wiwc9sgh1l3dIsXtC1aEW1SRzHnp8YwfNH8s"
    "NUelOBXuF1rbeXV0wl2N3kHBSes2Bh6hHF1MgB1LfdtCMwjt818SOsLAJpC9eArj0xIuS0mbgvjAqoy9oYbE0RIDOo95GiwtgXXaHah2RvLzLP"
    "ttg0b6U/ZCHnHymDxc1daRClPQ35BasRIGm/9RZc99ux7EJ/OH3baNOzfppI44K7/PUlxE1zvA3xrcjFr8gXNktJTO4LDixDd/bxXzbu4CE9DH"
    "9AL0v+RqxS6uTo9RirZQ40+MT3FmKvqhhxkQym/i1Pc/gz9hGz5wmLXpp5uiTihWNXvm5404ZBSzuOIO0P7mx9X9I8QVyUmZTZCJacfxO6uXsx"
    "MKv4ce1h41VxJXCOZqrqnK+vUF8WrY05Y3Y+GMAddaSklZFqpFZb5nqFG/JlFOC20TQr9PBMdU6N80OoxVWiYl2bh3cpxbpxcqtN8s8rvgRjXP"
    "sXuTA2LG7anyooNNLZl2yfJLWBqhNwSdNFNI4+onE0bVWmmdJZgxBZtJ1+k4YkZ/PO/rWn7SIKvDJagBe/I3rEpV2JnrxhahLeDtCmfW6/Msux"
    "8GFid8yTtKmlX4Gnfiw97hobS0m9zu6+AJiAdtb3fRzfhnQqMv4fxp5Fpztm+TKpFz9nks+TdSWiYunEW1R7J3IBfl67/SUeq0MY8GmmtBL2fd"
    "0+XvPSfPuW4EMIGkTD26mNYX/rSDHk49VFxQwsiInmbjGcIxgBq8J/r91JEIpPLUjBseAOtzNzPO5QsevxdM6ndxFAN5BN6EEmlzJeVA4kxVhO"
    "v1UU8/YbtNApGkYlYfl+UVMT2U1XV0QCdMZQ6kXsqfcpQrz05W5BeEzDP5DJOTMGfomkN2B7vbPGbTkQiLFH/h8VuFX+Ln24hABG5sa+F2wuwB"
    "8V6UQNl0iPtoEJMjIG47mkSW8cEhh+V62io3xf88DlzqxWBHZlBACMMpcTN05zCzgUbHLpCIJMWyIcRhXjtpkwf9DZJKL9JiVuIkktlaLtkR7D"
    "ggK+JS3VfPWITj6BfHrjYn1DZFub6Ft059/GT8aoy+h8tkTBKv9jhOCoYfCe8O5jqB4IwBKpm63s6Pu1S7i6VPc0KjSBwRMX9EcFA2IQ8mfZ0/"
    "ScYqUo8SFlygldI4sk8VV6m6HYe7oouMtBftKIlEUtcJx6lj8Tfr2jV6QdmFxqkHrc+f8CB7vfgbmc4t8JEbRoHN1qzo5BXr0vHPQ6CXTOIWud"
    "3lemcqiA1wMJYFKD5ZLCXbLH2GfE0acVHQU4ji2duw2s03D+xfNXnlj9i8CmyocGjowUJbbNJCfvOfm88ob48J33kwdCIOClzfuq8wkyvdl5oK"
    "UXycRfUN3MnnSfPPmJe+1StJLpe4CMsnL6r3UyEszxsosuczHOgoZ/GxVqPCWjjlHGetYOY6iAnr0T6TdSUx2Kta1XmL2A7kPbTo/vWHg+yEjt"
    "eM177SZi1sjz934ObTAzdwAf9NteNQjCtvQtxSHn2LUmegwBoz0BPsm3tpmm5c7nOzalxrJk3gld6IGGrCYVwzTRUeuwUi0cZO3PMDWsDZtT9G"
    "JidgBt5TDpNEocwnmeF9lIw5HrMVtz7NgPc0QUbWiiplREG4GIArLpuRY8a2v2G3WO4tt36V8fNKMg4De5O7+HCAz5Eu1KyJTQ4sgxLpC7mkSi"
    "BqEWTIOuz3EpOt/hBXsKkAjpSO8JYTs678D1yyPW+iL4us/RUdOmA/2REdot2IzG6VMCukPJY4h/GxYDoItedcEPgdHXzNb89e9JmzCrGdgGBq"
    "FykpPqEpqvGm76d1b1SrDYXMRL6DPe11+msiWPDpauR0VA6d/zmbGkqZNSityzjG05rOO0YuxXcSBvKHdek2vAUR4uy1rM0KkAt0IWFxbZFRyz"
    "TDcnwX/G7+a0dDjrnO/bb3liYCx7endgBh5J0rmXIOZytPMpfP2oBKl0UAKFBdug/nH9aIEj0hxkQHKj7SgdRo7dRBvyw6wCqEImcTPsmhZ35G"
    "PK4ddyrHuNmXUmMFHWpyco+Z45jP4PYbQTti7Beq3G1gaF4rREU6YHq+H71S7hvnbYRWdXShY3/bO912LBcB3KAlV/yFa00sj4rk8uA1A1VW3h"
    "Tmfoox2kOiw+yYdbyql1Q3X8dqInYXy+iQjANeLO2ttXRG1Iabu7lWUwZrq7MD19enOLJclrTMSA7Mt3+EYDkqRMDTdrSXZq1vEQFe13eMOPJ5"
    "5qAoJpsYK6Gz3odg2svGdc0dXJgB23vjlEW8OczT2tpqp39pSI+OlCLgt7uytYCg2anyOYa3atRkv6mJ1uYFZpQVXswVbZm2lK88/qNMGd1hCw"
    "PBOGsHpRVrSYueshW0ROlR2bCNMuW28g4uPELL99Uo502uPFzUZV0HBPjlrQrW1Pnv/hU4Byk0315RFL6OexdFWVU3ZbUc9HU9DHhz1ZyKHUBo"
    "aulZvLExLbhw5hgHQSeH/enBugaopvsjLs3kbCQqQsVcIpnoO09fzvi3puh/O8reBbQfNT35e4xm+Iogy6kxcwGJaf0J8vfPZ+g3CWumiU0wnx"
    "Tzhj3xJjMn7XgWQBwSDAkuKJgPdOLeQzxDsFNgOj/eUCAI0KFSKQ/+6dRi/xcLO/Az1zHzY27+yqJSZDY9omAgaSQfyKRrqFO/KwA5YnufDd4O"
    "44Lujo0pQTOF71dIHSvCAndnDDxmeutJw5LVD7tMgL6E/yT46OUG4koKFuIZN/o8lQuK4hSmfFyREOIv5mbWLohiyhXbtZTtTbSn5DchFathW3"
    "KHf0Zd7aI84ZxTyVGJo2pA/fIMOJtsNI+kpOOllDdrNMFw2QBlgeCKNAIe6pR2eUgcrdJdSdU5tMzdbIKqUV808oYPKEB3Mh9xhVpbEapYoXlj"
    "6fpB0v4taLEEF7B79e5LkyNYh2nAlVqy2EkZy4C0eRMnrXInhI4d1zzX3bZlfkIGFgR60leMED4h3gH3eXX6nsR78MvEz9UCFkn9o5xb+l6swe"
    "dSXq+i3JZJbccDmpbZT4P/KGh6v5U1FKISwT1OeX1YLWXMO/obqetI6rhzwM07RlgdRS3N8U5JiG4YkHp1H6+oHanSah48aE4JEipSwuI8eamL"
    "0e+wB8FbLG9/NrBh0RSdoXMYkQvIiXJ1y5wswIANmHLUROaqIBR4dQGp4CrwGYtM6IwFokk0KqfZ7zRM9RzShpB3gGdCcAfKcRCPSEDotq7vTQ"
    "TJdReIoEelGElYgspSsg+fFVI0Scr3ZzUhoBHkJ6GWbgzmfFoQC6+YO/5EvudDUkBx2vUwYkbbsOv562Wo+ebFkhgtASTJagupI7frGwV00nlQ"
    "CuXxkUYrDu8Ln/exWJ1vVpmrSzkazEMph5walHw/6ijyFhlb/IyBsnM/tz3az7x1CcSiPvc9Y4SMlhT630Sg4xyLxDhDaQVx/72COpJg170cmK"
    "rAk/9Y+zGv/6LWHJkzqhwh2cxfr0jOiv2ORSS0meJp+mWwlRcmFOCHeuCauQZfcFelm903Ps/kWDCJJ3y3JSsfxqOVQQcdj5sNbpCRsqYFv/gN"
    "UCEXeIICZ/jHLG/JxVV6liGVLx7cBYO3cVI8mfcT+DP6nmJWaX9+IdnYkeQBL5T2Qyqshv2qniBq/NLfiz5sNPj1TG5M3wHUCD2d1sixfH/Vl1"
    "aL+7R8B8+wYh2J0P+syLY3jb9LnvGMxAuyfCJns2D0LTpE0cXcKXh2SSNZ+B5Tun5MQUskmllrZUOSl9r72nhqyadkcEPzev8P1/IvFfv4873y"
    "V7fxCkLhnEl32Wczj/XqRNooOKH0i6WkXhmSbR5BG28oWMlZQERs1sfNMkW60b9gs44pb/j2q6uAWy20pTBvgDEAauk6O5wOWEE6FTp5cPUA2x"
    "o08y6wjxWsVeGSnOEi0eLyCwNlB3j+jXM1+SR4DzPH15etHzdXlkfnwpPFOcDimDF9IiyIjWbrrJ/SlU/TrcmBn/F4gq70JE2tsOtBrdMFDjvX"
    "vtolqDYiBXDCWyHFRp4Un+DM1QRZnohLAHR14O+rIyeLu20WYSg74S4zUmmikiwy66Eb8qBQectagm/2QcGhYxAkL2yLNarGC528soijP7Oes/"
    "BEPIFSJisYvRGc8D9+sGjqBQcBMj7zNvRMEedzcb9Ues2aRh55m5Zv0KO3QVZa+yJYoUl2EO7WgCzeJbQJewlPejBvkTisSdrm1lk/mAMeWjxd"
    "8XtBgHNTx80oTr0NWzDW9xwQwIoJRkuX5hg88CNrG9ZpY/JtsxxQ4ArH1JUCjFiH/jVwFZnhwOHksi8dqHeMeVYDEgvTj4OPpxjBBr3CO21Yeb"
    "NUM+4WvillJcTJYCjIu2GJVaNMIJ4xM9DTVXLqAzeSwgc0eMOcCBGavxJt6+KLoPlKHWHP5lUcvS7wIPrsSJ2efioTLTgQttWpDcKTC9VIPWRa"
    "DaAkfKx5tHzj/zA6sKWiSZggV/z2l7JWv1a6+U6vd2AoYPCxWwrxBqYzjxxYrWkw5j38/4P3osQEOcz0HTKBrC/jgCEp2Bory1bSonJ2NSBPXY"
    "KRv8aXhHjc3dWUTuMBqyXj9wV0gq/5F43vevlG7e5DROJtuT5UzJijw96Voia/ftD/HfZEnrCXHj0i7BvONwhsCksjZmX3io1+KIU9gWRdklHp"
    "AZpM2LZ2mLkZeE4deNoilO1h9sAww7mdpWlBwPGGo8rZhCpirzbFnppTtVXJJovyr4E5jGbYN2T3AQsHEGZEQSwpZ8gUcrgiHPvxq7t+siTwIS"
    "Kx/nE0s5ut6VH6kj7ZqdHyMLl6YHHAG/V/6g6IRzEhen/G73lpn9UEIY32uW8EGKkPEZon+GqalXPLFMPmv3/Ri6D+rDm1HBKdWQqV3L7+z7aE"
    "JqpAcjmmwqPrWgTBpkMKpBzdkEKqdfiPoLnzwOQM8LTkANJIJDp09byUIcFcdc7rvg/bkDDQ0FdXMENQQHaQH1/7pppXdshB5ccvIC3Xiuo+0F"
    "+UHI8S9AoVEVXJ3bAUrbgDnPHSlkPFn0hkXgyBFXhzapQE19TGQZFOYjkKz9uV2qZC9XrMu9PMoogmZeMvh6zo0KkEWtUuSU0G419XsWD7qHHb"
    "C3eyg9qabvaP1Z4Vff4+R11Dv6lFIodx+4rLLVHjy31HyQgRQED35FVWTeOWDP43/GMjwHzRWOVjbsgld+fvvEx5UXz7d0btZiy2qH8CVwFiSA"
    "UL1elvGtZC6BQt+afkSSKqwb7G9AmlY/h7UjN4vyBmC4YGz1UGPK3IKIKs0hYGB2G1xWXkKtnDhm8yUC8+5005YeP2xQzrjPljIKJIuY+db25M"
    "/CtvZ/oNmhk2m95o5DTKgOeiKr3yOfkxpWkmrzCd5pnJLu6/RCgfAU0l8iNpKl9p007LSyHttLHnBDSby44FOMMliT8TIQ7zqPiuXbFJD5sFKH"
    "ffbcrcA92WZIBEvFxT9spOGFJ9iAZd6ioJzjqOMmmym2qaxZHOSVPV8EDEL4J64W2Merobm/VASHvuCFx3zvKolUrQX6WYf74Bh5UZCleM/AmD"
    "zevcWLYfWOcZaiouOf9DWaPWiJb7W1v3qofNpjDk8YkmqyUjpOdFgt1CGNhJTzUoUEMDJPMzk5MoI5jA//lk1HxKrpbAXzSJuYDQU0VEsSI21g"
    "36MABYgVGIkQY3TvstGdpgHLqfmzjArZBZfZuYJrk3O6w3TmPebbdMpQ1kYsdBIvTPOZ4Rj8i/USHPbTIEE9KD8rhAqGVoQGcOeK3xHXlnJXAY"
    "vnMzwRC5IXVFBsFgRGihZmwFJ9M3vn7Iip2ZfhR9gilOew0uDq0vHgdRqAXYLFdX6Efova7Ss0A50pjvZH5kRQVzPvyo6583ug7obzrzr2HrRm"
    "OKrOdJeC0buuPirRSbLE9wReANoodumny5e1eKM7LSDgfMXSkw1ph4DriAJzzjU9Xg3KzUUmbP83+tnrL9LCH2L/yGIIuzNtcjttLMAwhFrstm"
    "/dNNp6tj5GrQHjSeFwmldVs3iEemQvXHCtS33uMzCMKzXYusOtLXWkA8XpRdeovalQwl3FPgKHNqcxe0MO7eHetkQrFtg6YuZml11TqgY75Vgn"
    "BbQbZBHgMYMKkr9YkqfcCveXhfoceYcnmjkFEKtHtN0YxNGXu++NrvYB6EOW42AfYyk6Npjap+cUhBWNGzcMTuC0FVG1/akkq0OjztAqRBx2sS"
    "n50Z9To7FsocmxQLMUr1XG1T939QHGjquKOF75uKaT/AxdVodFZ+ybZEHYx1VUPxEiW9HsgXTU2uUFFRZbMT9akxx6/iUe/e77isZzZpgYdoee"
    "PRW0th8jd55gRLSVVMKmYRnLslJveB1KScapDoucZZgPsxT84UiMkzhrV0PK1nCA5xAcdcZdEh+wcU2xHD31rMbm5XnfgirUY9uCpX+zlfTIVi"
    "i1VA4F/BU+P3A+2qUE739CqLp0V9kZFLRsxdLp+N/S/3PVFjAfsEL5agnB80N5Dt/tKXIDTuqIJ+ydvpRJcogDfc9E4uyNo7NLb/hdTkFJl8S7"
    "ciJ0GRNtdxTXhOGKA3+u59kv50abax35flskKX0CVEqQSmGOxa6ebtT3Xg3XLIVUnSoxMbSOKrXrt5jPueto0dRWSuRNYuv0jS60sfQ8eCFPPl"
    "eNz2jS8HqPMG4O2bgai+Uoy9unFEodp/Aj/iZ4Lv4HGmXiLJlLqOwf66/tUdxbw1S6Kg6DOaYWQOGBCSqKHfwjGpbQP64RkuHXTEvvGdmm2xdi"
    "1A3Sp/Ov5V2Ckd92QSj9lyEUCEun08Iq9TaOz3SpB4uY6+SvEFq28A6H3Bj8y2WNKD6Ag4zai1DDetnrz4jKkjIGMzugCAcb4Mclt9yXrnwER0"
    "UidTmBN1aumOZReGXlxqKu2frVRQBLPzJAQJbQJZMUdd+aeJTwA0v8JGvUJ1qrZAO19TEvYTNcZwpuvsXKKMzCAz3MOeTl9MrsgtjvDWFBpbB8"
    "yb15Ww07zOCpt/ADin/rfQCgJMJLfKtRCzplYxSqnlpKBWzNHwaaYf3iwgJ1hxKscafrh8t64zdz/FcsYxj62m3zYXLpVVyLk38l+zhGC4mQrV"
    "yiOxLuRdvzI/5lxuass6nzHf/FiucyG8N3wHAdiLaz9D9ZP9Qjq/wrIQS7NaXbwmkn7qWFJe3djrPOnM6pO7e2eoGZeAd8aVmAStkGBaMOO7I1"
    "il59b1EWhgZT+RUgDHWdyirnGSracA3m7G8A3DkJHy6U3+zi0kormVEqNyk1f739l1JkhUU2MQQlq9T16VeGtmkIgADNzR01Qv3e5QIj5svhnO"
    "KISRgiTpIDNxkWTXhphgOTJzmCEjjA9iUKWUQ2WiCagE4V4/pne5b6cg1dACXPMsfOZiYEryVofM/agL5Lb9vo/3LwFdFiYgYIejBO3tH+IbBM"
    "BPJ9Eco4Y9z9fIio7+UN8SnejKIolZc27XcsxtXROJN6+yY4qjJ1w0lKrr4Pb9yGYu+7xoiImI8J80awSAUmWbKuwitCdZ48uiW1W0zRvHUWXL"
    "4fOyZ9reUrzAoDvfThPNDoKlMz4KmNyHPR9v04k131yVX0G6aCicNiBWeiA4VfFiDeTRAgKMrIKvy7ESvoUwmDfZBYFTAosy1JBOWeY5YmMeP0"
    "0hHV0p22HsVyOkCDIgqbLo22uPVromRCx6YbR7Q2T6Ow3wFvlEyZvVywzBnjpoWrfS8d3QLxop0rCWldshlI50ay7oFW9MkXdeameyyQg8+DYd"
    "3vE4KAYSBH+UqtHVgMgRyjpsX2Mgsum3GMLtoGc0ATG3MiMsgKGw1vg8DtR9gMsYK2OogYVs96jieAafx9Es3+VJcBZuroAIjZBgQTS6re5eEU"
    "Q6zgIlQvwp1n1awfHfpUtyfA71lryvVWexcVe2/jGBQ/YuM1eEY1E1SYRZH3siLgdndHOd3+yC2GFLN7zYzOdobLAPh3zBHxLy0RYTVB0MmnTk"
    "HCMrnMoVKB/F3RlKsaCNi3ITdcMPWXPvCCUnH0x3Rc6mMkSNSQ4w8leJgRDYnubiXVwEKbZogMTozl8W/5qoNBp5beCv8vLKizP4kWrw5uKEqQ"
    "urGIBpBqgZxhh7SuQ0PY+dREhBqsFJC4SHxQVxFyog/L+p5xdB2t3V9NkKADWbbKDm6fy1Si/zzgTza4UowTCok6s+Yl8uazwhW/60zva7PQfQ"
    "4T0pkit5iZYKzAKgKq9ytImExOyRYlzGbfoBOB8Qd4rdDh6RfEmpymXEziwXWHSOQ2DGaZGPCoDMNMz/yALMKmUu7gutTifwBn66/v7smD6cQR"
    "LL2QHIe0fVUPiHWrtoKwox53+SZrVVOiV8MvFJ7Sm32sW3KxRgrEf0F3AMijUbdcPaJNKHqopd5cy2xJj0IkQAFBkGlTdpKuzPO7NAa6wq72j0"
    "cXBzl3IW0BX0uhtE+nIl1pfRnH3yqhUnJiBuh8qHjPhFDXk+niPImuUBXjSt98xepCcHXkOnoHpMIOOTsC69FxUetM8H3ywnpx8kS32N9tHddW"
    "ZTG17JvTHlxYPnBsdtlgx2mKMHq29K5x5A/I0wLQQQRj8BOrzF5GTqSWVoJ6WP6l2WI7nmzk0omkp+1mqouN3T3JVKRUprrWx6m+4l+o9urtaP"
    "HcuBWVjAjK3zB3Zj5VFDs1Zk8XI3Kk0RzfYEhWP06S+NIIr4qDtHfSuaT0XXMequEUqG8syibsgkLlnRzDaUMG7FfXjmnbmbA2ZndnHflsh+wa"
    "NTN6WjqL2wmSNWqRE03UAkT4uZ13AAps3caiCsjGIbaxvoqd1RTnrgq59IFat6JeKBaZoQcSpuZjVRkFL65g+dtpK06I/uN7mumpJhNKkBWMG3"
    "yFe4qKTXfNQNfordQEArLdxSuJfoUT0ey5mBgm6mLe1hxvcQJf/nBzPXL7I6oqwUNnZO9JAn19Y9GR7/f9ZL03z7bJzpXJifeJnf8vd1yWIGaA"
    "y2/23Snm0ZQkyYKvlFgej/eX6abPRiBPKYjIDk6I+7afCC6q9x6FG35WNnKBBpy4IPLAs8twVxehEqGrdHy/NwZX2hb8ZGLE3jMIvcYf8AhfHh"
    "rbcpPNU5yo44YRw3iSlxpIIClOpID3dkdqnKtYlXeEjH8TlMFIB2d6F4ziw/viLHJpND3AAI4mfLhXSJGoHhH/rV2HmfTMEbHgGHaAsLI74cxR"
    "+OW3uTC/nzI23GSF4H2LmaAWM1n8nWTxZBnDcAQ3hRJO8I4+KpmNQ+TVMC8mrJ/rsf5YWHnYOyPQdvnHeOGgc+tJXIh5GTIkYkzhq8gzuf0JAg"
    "22uAGVMB+HbH61/LPgLZ7i7+8n46x6X0zgiODFyL5EToBgeQ4gmEGFJ8vNErVbwntcuFZ9daxOu4m4UG9Y2qac2xhsoG3PvfEZJG6xkc1Z/2N7"
    "18tc+gNTXAJXdRHwvbAb33vU/IwWxuOari5VAsn4CkbOZjW7in5LWvicv8QB1QR0tf4LGod6Nna8YZ5h1MnFP/nTAAJ6GCgUIkoeUdMdbVHFlP"
    "u9T3ukzf74oYQZcMiZFVwF/7sP1+8RFH6f09GMVYvtpvN7sAeHfx2lad4Ut8lrp2hFGLqGuIKv1zj21Dj8dfiVvj8UmsSS2qfFoVmQ+BvTnZYa"
    "RMQpRhaGRKU8fMtd8CAOXGpzuDxpS1Jta2Y0JKOdbhATd3LLC7XMCawxyj0/Zp/xK2GFFmqegOvdcrWzLx7SCyqrjG+R5tFxWVCOr9dgSh7RuJ"
    "0GkFaewHDZxCep/VWm3vs1hmhAY+2Djn+pQNET/m78LDjyTw2AuPIGYpJu9NdyBFhJTFa59GKwYpfmNtEoeZIUWzZRgvu/tXakSHSa5GjrKCcI"
    "0bwA/jPaKf/7fcyc7DC2aq2qDPPaUAQDfFfn2ja+kbfDST5P7FoOLW0099Vyr+c3RfArrscy/vmUsC6lTZd+iuTF2+uXLTaseIEUtb0q++IGg1"
    "SM94Vn3XrsLj5XblQsPoSto87elTduXaQRgYY6eXrxprkiYUhhXoSpqaV7JYopKXdSobZqqMGUb/9XYJi59c1NHQ9YsvyJmOB1aCg47qEyEB87"
    "MKV24buOYbJe6IBbZ49va6r6XMr64MOWjFPJL1MEWH1U7hdjraey0106H1Dl5QBuaT+Ma3F54iz1nVeYXtyi4CxtK0MI2o0MJjE7RiMpWq5AUa"
    "8Ofdb8oR1SuDCnpVpwqGQf0Z3h6FsVncsv0R/qG4j7+TBWZ5lM3K1aX2Rr10l+b7zdHEXAoA7OaDHap1pZnEaUD+QUqNpJ0kpk85iHlz8xnf5i"
    "38CyIy0EYkEVEby+HieSaZMFSIeq2JLHG1pHz/QLAA6Un+/k7ibYsuYE7H0geVkbRqMeUVdoATPTavyge2ey8qhIelubLXO5PwTtGDeHKi91kZ"
    "xFkkNnxVS101Iw6xQ8QopaLAFXAZsQUxXZxZ8ln25h3DHFzPABGLT13tZ+bUv1L+zORXtpnkI7c7/BW0t1gj0ToKKrGl2Bc5RAjOMZ2aBTwMbd"
    "1/MtiWPTJoj41kO9PH6tZzsyUVBfgAzl0pNCnuWVZuufN66oNzmCbCMf5ZhFhpoemyG3YDYV+dBQl/7eRfn9OZm3AyUEo93hoQqsW0tLJiP62/"
    "pt4iz+gr/RZbAMlF8Iwi7peSC09t4219YcNyJHxfT3tLjRhveCFXKWilzgt8/ODOi5Lmb+zOPF+thzB3SK3uraLlj5THpvTQRKES2ot/LKXksX"
    "5euLverfnjEnybKOjOLq2riFACwKncsQt9FjrtD3j+d5ZC+GWArn1k4Jtngy5tQeoH4t/XTFz+H9ONEwwO8VDGOTXCWiG3aLSS+7gjZmZBHqiG"
    "Lj29821hDszCZRj5Bwwd4M0M6yQg9E8U1o6Wk3K8aN0ZWSsHO9HNYlckRRLkb0JEf37WZz78VqBAO/RiruuajY5AUSoRSNhXcIdUs0BmXhyZbH"
    "QCEDzX2AVIyKlEsG/LcOh6YlQ5rMEmpDiWLNJh/LOBo4tYAhPtYMWuPZ8xE1565pTM0Pgb9YW2mrQeeDKLwWDnnNg4/KJI9Rc2WRbgclCyZMlG"
    "NYgPKOZnRU58Ju3s6Difuev1lUeFqPVFEZzs9EKbpDlB+FmslQblFZ9oMpTwL3rGCEGIEzsG2j8IxsrtajqmKMhhaWvKANdoXzMqm/qdsXj74A"
    "QjBnFJot3aso7yc9KNhOgwcS0xDUyfvP5DqIOGyj+uFV9Y9VmPPGWAGwju2fydtwyx2VukMOk7l0zsEdEozZGUaooKAZJFNWfOsy5I04wkWysD"
    "wzg9g8TIgMbG4egjqBkgDiBklIEBgalHquT0O120txr5uURvHWo0ZQPBCA6WtG4hZRBRAm/vVNnwXExAzV0EaTIpCTwHmxA+dKn4fZwbQ4Bm3Z"
    "cmaBSxwNxhWzjcdBrLoG3amWkx6vdaCyADikHrQmRLt4WJFdcOh4YzTLm0mailsagXVQHnzLjo1FeKl6qlUTjVgLapawdtABhecnWlE/3v2sYg"
    "1+4TAe7hwckHVZkuu1y2dVu2JO4dlXAWNJYTq3tJfO+FIn1j+cgYAyykOQiAMSO58pKYv8eOjYN251OMP8NLKdfyvQoqOl0ZUevVWQQA1odvqJ"
    "3KU4bys+S5ydej1YOPqzOzRrEdGMOJlVYJpcg3aVNvzS9czwo0PAKeOjP+oKQuuktGe34gq47xNoICjIjwW5kULFxpJpfIBLXMnqk/RlFDigaz"
    "q6ZRbtxVKGtkubtog7ixffpD7norQ2ypHfvqFPgxGbkXuUCjB1eRfW9/rbGUCcyyv02mshC/+n1oehi9SjoNjgDqRzSmiPvZRakgWmdfrTbnjH"
    "4A9AdNbTkrOpjsGA0pK4X5GjfU1FKqwUL+w5gq2FXD8qYsdgqMa7ehjKKDw2MQpF6RfhHUz9xxFWfoCy61oLnkDG5NehrCA+fT0jTEk4/1XNEI"
    "xHjECqgBgHrLsUyd82ez7wgO74K+tWF/bm0emzCTWlm4JUb/1lOp02lyl+AJdHdd7dsh5sbefjHfftRdLns1LrNHJNWrwEqSWAmWD1DnqkgScg"
    "HWdrjt+A95z5LehnXdjo0HP/62Zk0OHB//dIzLw99fCp2ktaqeFUQvbUsMrdA9C0Nwiwqj4WZUpzekvvRb9fgV4VokSimoJVLN87wUs3BKjXhk"
    "5v4I9faHGuGKCJ5gdhERNHcDyRxrJ5iUNamKcrpJKXgNpjSqUOwI7AvfSFzRK0pnBcY074zQ6cyGDZ3kshHRQdth/lbLund+KVDOL0QtzMsbWC"
    "JE8aq/hy3OuKP9U/YWI3IC/npaE+jDnrCjaS6pNxB7SfVOqA9/TRONkPn8S5cxeefAgxW3A++8sxGYaOcIzCAT/5mFktbG2bmCPV/6xnZQ2VcF"
    "xvUJJrZcSbst/Io9qVSWyMtuqMqAt8h6Fp6x9DFb8yIMpVHiDD+4ajOfit6m23Z2UZgNlKBrFvQEXKCLQ97wfV8acJoZ+jkYXWltwOqLbW58p1"
    "CgthMH11OtjTCYBPFVhKaMfnaXEd22iPjk92D+oI/NriBgOaVfYLuN3+gQAOKcDtvwBakg9LSVD2P5CPDcXexsIbiIQKym+alrqHhuazFCegoL"
    "DbYnxP1djPNuo5ZyObD29sGyS7AIG0gzBx6wO+rrrDfjAurvcPtb5KYjn2rm2pqrdb2DyOrsmsM8cdB40x/jFa3mXsKazOTKIrSFAqISyNil74"
    "Z6C6C5ABfOPsnfpmw76b5qwmnOwLNRoPO0+dHGeAmD+mH1JoJZHwPGnmKNOmt/MmG44LngtyMyKM+ZPXzKtEUIaeReZy7Kfs0K7vJUE/tYZdHn"
    "kQS6DRTW4yMRnBhr3KQyHE1FVHdwrwMSHLmu3j5018lkNruyx/D+XjKqbNgzkuaL9kHgghYo+phycYszkBbTk0Kf8/JhZv8qCkRtJIwAaD+vsR"
    "Pr3MSg3Jld1GKVfUODtqXB4D9l49hYUKGia9TrH2Lz+x9xnPJI7rMXZ48vUFKnS9xZ++Nm+E3lO+Wen7oVrBV0ThP3LmOON8N9it1T1wGJnWO6"
    "Ljecus6ZmS2qy3T96JTLSvaNh8pkVaQUf02CQNFtU8cQJ2hlzumDByQ48aBkfHJIsvSBj67N0hwwE00oiaofA8LUbt93HN9c3671ziIEXlNPzy"
    "NekpRKSGpVD45a8WTPo577nwtH13a/hD3z+aQ9JrF2WWgr1fOxdb40R7kijC+svNPvxyCqzH9b/FwPaL8ZJrIo4fGw4e5jIpW8jHKknmwX+QI8"
    "nUfQ02t0QEYVVcONzTTcD7PHTpGNW6USS0GEYjo27TLzf0Rz1KSUibYvUpakHAYjzVwqKhN3PU9xRl79F0DBNo79a0TnG4uVn2zFKJ+PA4EcAO"
    "di5S8+oaabPS85DTG3dF7c6AU5xxEyC35EqOzD9YXQTqV4P8DC24caEzllXDfB+tr47k0Mo/fuKqZiD3LFsfE/747PY+iJySccindrMx3XCzZ6"
    "dfoVB2g8AOX8WqOeuj5hTDK/ukwCKsakd96Z/fTbJE1tyVdkFEZ2AWLKuVp8zZaNDnQgSrLKYlX1PDJtaJdOAVAPtR1PQ2b8Fp6akAS4Re/tO8"
    "66w9evfbo+egDonB0+PEPhO6Wc7P2hvLL5WzwN+rRkc7Qlvy1Zrq49nCtMoHoHM6LvVi9f6DVggaXXxNuh59nQJ/yyvZbXij0w9yaP0XuKCEWu"
    "Xx8sz41Q9hz6H+qJwKHCO8ip1+CJW/x9qlUDVWh4sHWvswAO8ATSv9lGf0IXMPSD6Is8LmylUaxUUak9K9Yz1SbQddS8ozHqzi6evrM1xhKzyQ"
    "CRQhWnsxikdG5Yk16DPVrtCb14cl3AsKoNTmEtY6ayNb3wGJZCSVqNkhcwfHLBK2h0w06c6YWLEPnnVNsljf+J3XjalYKAZb7nkd5anHUXKvmV"
    "qIqA02AgS4gunlDdCmtAeGWjSReFLtfjlz2nB4CuJZDdmD2DZ5qkWCxyKzIFkwHarTPrPxCEuRUPEYS5fY3K3DZy4iYKgKxAXBcnPdm87e7VaD"
    "326AgRLkrr9YuMDSEKL9r/OzLWVQo5zTyjeyETmkhUaa3+k3+zeynfPpobHTDoitbEnOk/RHivjPJXoMcu5qfxI5/oMrs/PteA8+PZE6cAfSqN"
    "p7nU238g+13GzfqsPt9vgNXGu+Wwx5ykeLOt7+7PiSqRY0Cmc41rFgju3LHQT+KHfXvnyxdZFk6lj4SSNKcndbEKahwlk1kI7GdhWd1Ok5eAkc"
    "ZFtMv5hBnd8U2XFhrsVs8J1KZeKpJakKVTTP5uIxg2A6U+07mrL5HrAUSxaY3ZXeMEUn+QEqr8jFLlcmzl7UWHRwaBskFz+Hodh051bqQYGxPv"
    "63RBJzDkA3HLpSXcUpYleAeuPDv3gTJbVnbQhHnOWLtI0PjhvNzMZFpa16ZPBKXd88wIS30vUOkRAE8o7yY4HcUBOtkRox2XG4wXXI9jcU2q9R"
    "6mGnjcbo1oIos+Awn8NbTCROm968Ym73Jy6AqOSbMYWzaesjeoek+roN+IpcAku8QuDk0rfmWZ/mPM/3Bix8TPtl/9voxMQyZXrVETqU3mN9Wq"
    "ljhMr5Dtn53khp7rPp78kBYe2GwJePTDWCZXQ1f5NOK+4GBew8V9aKOHqRcsER6rhr/bgdcEtMFDBCggWIMAEXQwSwtfplGpgmXrpLSnq0iufD"
    "uJ7clmqcemUmCBrOPfPX5zEMVWGIzvsBuIy0W8ozSXaN8ujcLeI7Gu563W/a70nadJAduU6+kzI42SjATGreRfUBgpcEDusUQVnIT42oZvTtly"
    "1nffYdhC4wMiNMS0kAMHElx8m0XuqvPD2MSzmhJbgq6UgYYEG1V8cvDbMJfTTOIqjR6UMhuwUs6YuuDocVxMoqyFMSVtfFpOJih82xSrZJ5Qzj"
    "t5y8ITYL3dqKOBnYp33zVLUvPLlAr6bzGmdYAascjvotB9oCqs8seqW9029sM+EoJsPqoDfim4TzxItuPj6hZCFiBsI7uwhn4hlCSQtaU4D9eH"
    "O8phT3bFUD7Kn1qPWAwqomNdrtOpH8GqxOyzOAzBazfwjMic8zBafUrj8WFiSxetnHDiYMhP2xawC4qAb7IihmCVv6fj65yCoDMqwYzJjjmEvX"
    "z1lHhZ1xKaiYs9LyHT/ljVdesA14Zgoe3W3EoQ9C8rJVLKbglgaYoIiThvQaIDUpDhG+zvQMmD4cBBkcZdWcrvyogE1N6ClfYVYNQD0oQFRY0i"
    "G6nSX8m0W08pRTsgei5k1GYQe0iqiSQC6hUyu9UfWcOj+gLJeBQgmC92mRTBGliBAEoBi6nJ8cEvTgnKnZGRRxC08K61hoFCgCqQ8CDKTD32cH"
    "VlvvfO5fF5K/kfhIBPQAoy1ebkzzUpgNQE65inlr3AvNGTFUkC3OhcBLUajQJYZmCdH71ENwyANT1ZQnxRe5xTYYasSnhbd6WBUxpz+diNdtva"
    "MBVIkCemNH6BvuCl9Hyr5bTiHi4io2nwI8YBj1ZYKLNGP6vmix7HFZIbZMs0pI29DYdpOsiprxZw91w4OzDShfKoe4tk00uWgADjXQUAX7obmY"
    "6//bPcGK8f9yg9TJatsojeO2JdceAOlKRRPhWBp7M2suZ1yiGO4N7McWpx5cXA8g/8dJaMKHEN+CAtYmQEUrtarAnBDgT66pJyITMhy0SrhBcs"
    "uOWerMc2B5+bewh7xC1ieoJJn+BIAEAAD+tdbl/oN9t35wmL//wf/+Sj+6CthPK9MH+LwwS1Q32vd9O8/gRSw0vbMrG0eaGSMV6QYTOADIRcnf"
    "dk2QeZuZMRfHmU1cZF6EPtfGp2Dftcbz6qUY2R0sAEU8S4I5yeSUP9RXeQDKjuTzyytOohvpGv6Itb2s1eQUDXHZvPh2z6ZG4pusjqiy287bq2"
    "LYa36Q6WJHloqiebas6yOf0LooTb4qqgAov+QFFzLOlehpDZYMNMqD0V9wpffWqxHgIPeYFKbsO8r3V95lDrcW7u0+5JYJG8kgMD0fAZAb2oQs"
    "vfir/aEn94XdZzj4zpSvj0v0pBzuBbSg6rHnvrSmYqTakP0CZnngzgEY6VwQChC1RlXHhKhqce+Ta6sZXg3Mge28IWLjV+sITFc79p5YqvWBh3"
    "ow1sidynEthHOhoqSmLjOnAFFS0YJ71TyGsDFxtz9Rja3QBiaUXX5xtsPdqD4EVSaffruNP/8ID8g5grktUN+Lz6sHowJDKerO8jAplRun0hOT"
    "ABUazDmrFiSFaR3fK93PzF/3P51i3VPvn6boMv97P3VPZ9qKsLmN4+2k8D4hXqltk7hjUPsMFhYwc2embvoGYlteZa5KGd2P7xD7jpxjFOgLBz"
    "k+bZVy3t7bZRwcumCbv6IKKCqN0Ujm/qI/qL7B0xx1hD/MLAl58vtAZOvbHDvk9bLICywcPnMag+alC3hy1hoLxlajm+8cn74po2ZbTFMleKfG"
    "TS+mVuOjvudqipGWz3Z6M1qCGTKWvoMBWT5/BgJKI8n0biX62GySnzFcQPlxhjfrMqfeQ5JIwmwyXhEF3YUcziufKZWdXbTx/gXSu8P/GZb5Xt"
    "sPYP9gXZCEUBATptmmJRExM7/oDkOBZfBLjriyPvoExfmQHScXrUUxsvyEdANnmRvkyz6DbmmgI4vivVHyWiP4kECDFnB98VS3uIIFR70BDaDh"
    "tERL5zqYYxGETNi9E97cZut5RhJZoUzQmuyn191PFL8DtHFTEzezZTvZIwgxauxcm4AccUxkeibov7y0mL24E+HrvNpDCcMfJMtOrXxOZWFSlt"
    "vXh5jkdIUDBcDgVLPQKGQIxfX3Px43AxnDdAdCD5tIcygxBTpvV4ldqksrJbB1Tl4isV99DBN+LhltbfJt3QihkV8g2o4KDngpy14unk3Hiela"
    "Dhm9+HdZW8C7MJtSdvZmWZF2Epwnu1NMjEHtzUAnb1batnpbZhRpV9dAZzqpyiLgpiemzUsDvwZjgKIKuBdMMUW3UftBWuDuFvBsLz2jmVNGPX"
    "8sjm2q09Y4vjUhp7HXXlJTsGuz45ZXUa4Uem0k//AOjqX/uWk0IFmsHIZGwkuVQOTHHYEAcBZmFnHJjMYD53eXNmar7rtl36zbndVLQ+LnAjwL"
    "qxdaB5+Hf2G2tlVi6bl9Bzl0HeLvgAQ5ULJWOUTh2Q36O2fZeqT/k97zbi4o5FZeNFGb1TtDQkpChQsmcc3IEB1Z7yqXQFtF1ANBrIdsE8unMc"
    "0naPcYgttt3JNGCz2Lp/ur1nczIR4/7zQA6y0BFuAXAj6HLGBIGcpS9+hKEgUihwgeRGvPwJ8zaewjBg3kO9yweICkxyJluJzWogCIyMwvzEk9"
    "eXrVpVlt7nohoTb7kYZI+ehr9wms1/RyCgD0sOC1ueMWyb3z8CBvB/Rd589D7IByvzXVtYtUJeyYtZSq9ts15YviTWfX9YWVHBsYPamWIFExYc"
    "fZKoP1+6njs1zuZALOlOUu7Zp/WZSHHvK4oh6z0eiQOXqlbyR3wiDkel+gf1+03ULTDknfVsvzL+Yf0fFnDJ+HLodMukey8/0hFVvo6Y+r9Jew"
    "xpSLpQ77HPeaekf7bFeIIfcgfN9G69kQ4ouAfidt3y/Xu2bdGIUJov5n6sWHBoiPArkrTlrxMuXlRcR5N24eV1GQ3q2/ZXQ2DyMsbqFascn081"
    "BACR4Pdzv+xYxWEX54WyJOu0OGH48t8Xnlq9VfukcXq95yE9G+U/z2iiKGd2tWeTsL7+lbW+LInePt/pQY1l/xyLUYY29DwAwbnHjIqkj9lFh0"
    "kO8HVdjl6GXW0ub22kgrse9hjkCcyluikuLg/pIGaFpVWTPDARH4btJEjth0YRhrASRW/umZ7NMLnhtloo8b3XwcFQCgxSSKZqc5+iHBDshcaw"
    "EGJqUz2iEvum/UjH6w/o4nrl+/bM6hozD7zmrsLo7ojx4Prq1GngnnVmbRf08g/qp9c6B4NATc62e1bAgK6BC9yIv/d/xahpW2M7703mjD9BeS"
    "8coVrVHayxEs5DYwq3bQGsB6uS1mJrI8eK4KW8O6EBLi4A4ZNwzAIePLrxFcnR7LgBDScUPRviVTWCQoNjRFjDWLMLqSpFM/VNb/GLDQl7wTYv"
    "rFUnpKzyxEyYLvhRQ0mYt7Q0OsOeC/MNwfZQVMEprV8+W2D0EntdKqrugTX9KFC7Mxi6IQKo4GNbWGsomCV7J//g3WILUUNFHLfNg3zMytRBj5"
    "W8rSkQ6fKRXuR2mIB0L9aQMWb8qaYhaUY+NZlxlUuQ3+9g+K7aSny2r378mu+2NeDc3wFGfY0FoFdjPTWY5Ts2NY2Wyk2ruyEhs9opsNvdG0AX"
    "DPLtYpN+hbPwAOcLVlY0LhnZ+cKvgD0QfeJdaQYU7ES8t2QAIaUxU8jPLSqcoeqb89phoLHFJ2JMH706BgNORvhgdYDYULmMVrk4Bv8XzRfWuu"
    "QVxvI4sC3hLsQgkBhwsh//zRtHOUCOEq0VwezWHyEU09TkwlAQSzKHNgFoT4MDdAa28IRKw4do6onw7EZiBVbSd1pwFBTFQkCKG0Pcztc3EGsg"
    "8rEhuOJzyetLtPnyqOBEA2C6je/BexIqHPAx0wxUWgm00HpQfGGsPRFtoz2YKKaIegO55S81IAEEzKIAbLWBTEQA50v47+ULFqXDbibqHEolg9"
    "pLLdEYZP0kIe98c3YWBlYpcLU6UHlOJTTpI+pXRLxGWsRXB9KujsguTpAFLyvgee+D9UZJ+fUjDVnplroesgnWz5zdD8VgJpvu3Rse1Bi/lIWd"
    "mvKyPDpaw7L7LWIfdvPGeku7mj1gReaDifirTtw0OCUwHp7JjkdQ2lBrxOp9TI/jA/N5tlWDGJflgF1TPyKFcq2uW3pM1V3NZQ73/0U7dnSO2J"
    "LwFcUQL1moKJpS04UVUPrivhTPfYwZib+1zTkv+HGdv/fASezn0huXjKC0VdTg8JgEjesJh0QNJzELHml/eqH/s+sWOhGdSKS4c8WWctiDdAjX"
    "6s6iakAWb9sXfOe0LAIgvmBME8ZqQu+n8EItGQ8n0WNYZMVwQlQgbkpJAqjaPhJbYu3yiIaeJ6/63SJiyHgQqDuIi359gNJFRO8OUxiSI64IwT"
    "HEeVii23W9Kgob1UjYbYKaOvkLPgSFoHHlHvqtjixZEaGk/DnjLs6eU1w7cExILQRk++LNt2RJFr5eVRMy+KrvnOAuuaEDLTsogEys7OZPuWCr"
    "JzJh8HGov6MN1gp1mJZmb8QzgIZ0rB1yNvt/Jg5rey1QRBuPi5Dq1ZFyUbzinWptEcHKlvmQ6C7GG64ROw9vLW89H19hp11fuldo49/q154JF3"
    "I31rqTHO39ovvobVUlmQtQOYT+eC8hkcz9dY1S0PaQWqr6e3u+4vLQ95Zr7l/DTfk2i8yElKAUvoNrXwEyCjMJTCZsNYGNue/QGx0eSZBtB53r"
    "BbNd6NHFc/43Fr2kT+dIhdwxN0Ftuwzl/4ph9AukBfKgrrUS8p5Kf0+NIrr2J88/3E/lEuQ5YZNXFKBaDPgg7AzCOLipfR2wH3X00yoy0x0qWg"
    "FrZAUN6TC/aCeN/X43YgFvdQrKlzGMbTM6OV8ocAFWObXEp6rDaNW/YDs5n1TGrT4LcuU+1dpg8FmFBBKfSwuOqM0FJikHyCd4bRz9qrFk9kdx"
    "RM04scQoYCiybnTBGkyMqCMBwvIPreaPwBVQANAGvgGl6JsxTgE1pR7ePiKfMAGmFUWQJwAOWP3DlB+bsGc0DGNK9JR3S26H+1cA8Dbu7u3pQl"
    "T4tYT12J4xLwQWkKK5WiywuYk0SbGflb/Fwh/NeKQHGpfJ/YOUfo8ufYIxheSyI5GF+ewWafFyABKszi/ZkcuUmUAB7e1IiwpFiIGAhK9RJDCX"
    "K7YCUt5HB5ETqzTiOigmopkJ6xKeYMRmMxaBjBt6TFB95LOIBGlVg0/NYdPkJtT9KWvt8fmuALQsYgxgGwJ2dytVdEOTfxru0WIMqMRTxjwBXf"
    "COTXdNu4SNsMxwcm4gf1VwU7SgpKj5WiYv2J/3I0t5Inb1FtAgZsmZwmizmj46+vEstX/ZhLxG2XibcO4RQ5Y2Gp2ZToFVCo5oaesIy4E80le1"
    "qyoT0zUosAZBterOFIPhBWKGFB36xz47uil/alxGykcD3YOO4iEi4Zi/IGvSnVXsXSzP3ylqgl2JDGpEHTPgCVf8zuWQCb1F0UvQepK7zqcetz"
    "iDiOu6kpy1R/yLq2bDWx3mrbkcbcqFP7/OmV8Y6+nZn9ijioivY4K26QYfGwQg3V39+tIKOQQnGKBLqk87EWllaHIAKv2PG3SgqxSclSxG5tm/"
    "A3jAlPl2s6/6XlyCJwkULm3Une79bOIthb52GHj3IPfquXy6CHS33n3UALE1GYU1TQk2TYhZ8RiPKEIMEOjJff1r9nAtWjAMLOc+7xFHo58MPg"
    "0Ynbnzj4fp1by7DJeZLDv8I+8kHDrnNYZ6tEIwFoW9ABKtbzjI+H4A25C+B1ZYkXb4/FAVP6oyRoBeocR9D9jZgkT/bbscypidxwNiqoBLYOed"
    "BhrS8wu0xUK0QKH/yEVOs9vnMTXHFZA+4+tq4dafLulttljDX05SYT7ZA+0/we0TwnXU6621XO9FEITilmouUH6XAQy+OlNjWzRM3byToUsiQ9"
    "jKwn5agdsZiaOGbj15kU8kCPI65DxlX2hV8zrK5C2k95dqxCreGnxjSwAPQqrj03CoMR2h3cZiZHCyyYwrYdMJEVeEC7GPE/OAcWZi0yqnGeHO"
    "al4EWb7IvbuEmCmzQPBkVVUWlDqKQjpqk1ziBCACMtA+KhfXUX3h7PMXAsJG0ebk561AE6zi3Cd10EUtdTIzKrwjRYgnP2+UO6H+hUFxanAKQH"
    "H58jgRhg169jpTUBNMD4r35SNy9YO6yiKYY4kA0tDbGEcIaF3u2NZqfgPM30+tV8Spw0zLq+vsWgnb/JuiNT1hOAkRSCLOS4MO76Jx0l5oQk9F"
    "EqOvo6fRY9yqQLevx9GnDUqdMbRVghrtchsF+o4z+TeWFo1D0m8f65ItOiBuP3EtkLYqX/xAD1V+hCJDjQuAgm8E87kyt8R+FGmos5QkmRa+AC"
    "kwCbQ/D8T7SI6I51dxaOp4K4HkfvRYNoZvm5k3BMXCvRfxyXxtlrfNzC0s2tN5VowFND1eWBX7DuR2OD2IxQr45mv4JZgbYZ03uw8NwRiG074k"
    "gs9o5XS3l87y1YIllZeD1wb16Jcm8Kb5KUVKNjeTNSgZ14ZN1XzVjfnV8cbhLt4xe0VKdCGCcr2EX8Jk0l2v7H/7yBmppUg1mmXo0nTz/T1wGs"
    "nWdimpzz7o48BcY01a7TPXvNkyUYqHf2b8LRfIEuGn1kVheUYQIBBqrhlPjusGXxk6RTjnDBrqS6HPXVqO048PfmKD5sHuTg7VoIqJ0Oc38mvU"
    "Dea2/QxDXfVcQiCu7dNWYmJOJuOOX9jVvHk9UGX8VATeOx5hcjOxAScx9YY9alZjWE6b5IobPsiujY6xEtLgbspJR6l6balNNiJrTpsy/KOEsf"
    "DpW0P+IHiOPvakE7AhGNpx6dFRUkxtr+5DV38/HIbmhp6NdespOhEZRguTeOuYxS6wODS6ZU5cRBZV3SQfho3U0rnoOcTYISqRU8AxXxb8lcEQ"
    "rpSA2UVBs7wnNLey+OD4UHSKwgIolbZQe6buYNIWIa+zZT43ftjKdqPvMsH467AJ78JRBAwXHNIOJ2+aDHUGMpVBtsjjq1VrIqk8kZeVnWPcPE"
    "SftLE8RO9GbnI1GPpb41R9e/SRQ2wYxtuKFQH8mtDNN6EPAyIY4/zUbP4KDpFRoZjz1OprBUeEjgMg4d0hyQB7vT42NnwuJrQJ+11b32XaoqBY"
    "nCrY8+830+XIdGusTLEZyoakdUSWdw7l8YCnACUbGSDJhCA2h5za/uP8/0amgU6eQaVpHyZJ1jvJjwrVeeZ3Ihg2c+t9wFAP0zNG8ZlwIDhU83"
    "jD4/KF92sD0UDE8ukwcGVVV3rd2zEtuozbz1sbOBPzU3/tA7KfehQVnNvr8P3rOJcMF42vDamHelqM5DpNKn8W4rOfU6gIjKFS0f4ONu+QXvap"
    "iahcqGlQXrjohRevqSkGuEQUtGM9yFRDu8XyKcT6q5RxSjTxE96Z6+nhL3lHGaVMMWI2bjPuNid6NvN3ys8y981hJIx6MggTCI8Z8WApZs7r/t"
    "4398b7SlN5YYHmjafSkKORF7Gn6cPRCYpHg0BKLde3/ZWZbKTDWAbthzGJKVU3Viyt+tA0J4vLKwcWra4P45QZ2bg0O+VKOh4MUasJLU1TEyKB"
    "P4eO/Uktb6MN/32dr0DAgFtR98KJtGW673reHQxYN7pWa+EN6CpcUjJdvHC4IeGAr/Z2e2yXznkae28LHVgjZEC3dKq4J46BwZk7TJith/TKBq"
    "FpbykqO+HkPpXVf8GCp0LVxMeGDxuNzfCMBgRuHGtIWVw0tXWJJ0DkQUSg3RUXHmJA+VIjU243lIDfpjhRuC7X6Ygi296miSJbB4Ip+u4rayy9"
    "NmoZmKtITJxcrvXxfaHijE6Fa+f6cSxWEwKgfF0iDbsKlNq2ha3VjkE6X8i+WDbkwkM1tVIQV8vGqTbv87PIedTHZDci+3KncmV9dpJVPrupzC"
    "QLI01caXRcRdpPF7caha5+7qSw1ZMIDzhWDxo6b0OxCipeYbdsHCgsZU74xPs/ezrpnXYzHhr0CNmiH5fPtc2AujLhyCaTQxdt8yis2Fz7UnrV"
    "HRM0mMuMmOgYLUqo2khxi4TrjH1QAr6t/rrLoPIirTRhmPi2hwqnaAXcRoT8NAOC5r1MAAbEHUU5aIhPiQ6sAR+qMfTDV2aGyQfl2Jw+n06911"
    "Ewvj2OWQEMW0pWFt0/wvrR9QH06/zc1j7knFG9vCsdT3HH9HwNqUIydTkRDWg8jOYxnobwUptG8/lNOZMXkI+PtWEgmDWBmWGcfOQuv5ieN33d"
    "HGu7cZZia5uP6wi2Y5UO0Wfk63lEcmdrtMfnFmTo9Ldmh5Xsto+pXWsLorS9DbmciOlWQWGFcWi2bXFN1EoWi9FlmRhSqWzjm3DLCp55hnxAUD"
    "gL0L/c8OjBz5CTUPlzzkgeGKJl6xlV4Pd3TpiDdEH8fPreo3aSTkNggx8IVhqAuoMhUP4fxNyw1TTWWpNLRSRNBOiZNyNCqy8y+3shjEMch14h"
    "UUF8o6hcwYZNqyBZJQ+mhFuxY9hpqS/FLis9d0Fhe6ZbgRQ9n3DbgPuBstAEAEAJg5883fkb0H7i+ZTtfToOMIimhNlsry7L7CIQI9ONUvXUSt"
    "H/8f9MHcZ84bzijCG9KD8VYIoD/zw1M3uP/lLJbz3hN+BRqCjnqMPB3Aa2AtABDbU+rQnMg17mvOJDjWR3IAPi3vBRrSvcNHnPZznr/6wkBsa9"
    "vA0TMmb4TTau+h40xFfVkSxm7o/7YEP/CSHeK4gA6dY6kj4D9J0KAxOVrmKNuSfM0/aHujZJbVfrezB/vzVPtTP7vFAiTkLCy1nVpoDi3khZYQ"
    "p2hfKQVD7RYCiQprv8lzZucbI9zBfEYQ2rUekdStuqwBNQc4wnF9K+1HM5sL5cV9n0RI2NU5DIO7EAp1iAjvgEwRnkyaY1RufasHN3bFWdDpZe"
    "m5ljAUnSwqLuFNJXxif0kdwqrbizGT3Sp/xrzxNQLtP2WcnlobmXBaAD6cGkosv9zYAXfKSYbpS4AIgS0wGXChjtCXUaJK4LRURPVHU+CFc1MY"
    "A8L5Z3rY88xKCqBkKimmWPSYyF2QsF1TwdUitsmfMrV2012NjQNNZkrc0WQ0R0qlZvVdPZ6pKwFD++CKLI3pWMkQvB6kbwnmHwRzo4KoMlkxQB"
    "cl1S/8ZJ9dKaYz4+vPerAf5G6hsLDlmykFT7VzBdntHjd0zA/c9r1bFCW5XBUqzT2MImu6rypeZwLOPLRoWzniar+qzMgiNk46qgBWObRMdoqn"
    "DCvInRSx5FWAkhn4c+0o4tlVmDPk6n8x6/4wg5tFoGTwoHVg1PsObHOAyYIdm1XPMht4/+VFIhBWAJk1uKjwUlB2+hpbJyNHzzrsTMA1WPHned"
    "e5HQ2yEP4AHA7wO/3NQjbzq7WDccLpSZ60wcI0rhWA1RgcTdfFvb/Bv9oJ5BNT/N/8yb9L2conNftSH7t8LRaBIQ/+VlMcxOakptWJoJRxovts"
    "h+ynQlEuQYBlIBlUuJFANkROuJEP3nhmnsaxYPeYmVZeY6EAYN4fXvnLD0xFcqSXD+i5Pl09l3uaN0AjhyBEMftViDDg9BI+/tiTYEEk88vkqD"
    "yr9OD3ekFdPI0jGUSHpK/HfWkZF/eYU/ftxIXR5xLPGiofz/JItanbXNAkOB3IophbgzwVairH1eb1hXtPFYGyEdGKRYxA7s4SMcLb0A7TWibU"
    "2HembaPqUATAelRThr82TlUO+jPGGKuJ5gYXJmlq3K73EcZUiXj5IMwKHO14YfHt4Y5UKaNgJdRpLQ+5FnZ9AkcFuCf7FOBaRko2470C++W5co"
    "Kv3FEc4cMUX1wOl3Ib3WFX5JLKRC7UQ7p1xIihz91iYy4G7OfGvJy6AsVdSCtqzrHUyoyXKMpyduvdOMibVaho8jhnxcJ8n/1FEhQpCwiwipWP"
    "gVefuyMWGcCpUUKjL5L80NRQ1gGpZWlyCJ2MbnsLlr2gLhwijVFH7yJoJ3LBwKB70SXbHIJ0nqchrehf+C9XuzGS22kdoLrTAAUbDRUCHZ9oVu"
    "fTqqReqPIaoyG2wynEp0r/5lFD6O19psbrC80KgzoR/oqXjeywrMKiQteR/jxnVDqgBASxrKpAms3g2RjJXlzFezf/idCU56yHaa57zjyu7mZr"
    "vIN9cMliSUMpk8CmrrmghI+WoJQJCAvbsNPSkwfXYifLKBXqwCmnwKZqtdS2mz6cRo4dTj72SvX+rCKd5LgCNOtlzG7LPKBOVuGIeeYBh4tbnV"
    "vr9nwaYGIdhkSzcQ8wPV9X+zXncG/RZh3zKr2sbXgwUx5TB2bFMaSGZOt7pzwmVDQtLCPHGMOHH8BiXtzBKRxVq/zsKgEsGmzpE3Nz8RDlMaxu"
    "2IBzOvrM07AhPX+J2nvcBOwEG7dD0qiFeHXEsO5y7xC38LKcfsQPpc8UqVg9sohYcCZwkU+8WdFa4Gxez6O/ghP8DUShs1JEjES1tICmY9hwSt"
    "2KSQlg09ym7SsGeZtbYcBRIMSSUS9dQS9FQ3Ag5d2ckPqf/T/zRvQO+TGe+u2cOK4Nt2jCPrqFK6t5srauPR+QogX/j5VfWCbJ0qfq2toasRQd"
    "s3jyhZnK/XSw3+vXGRbR2pRGJ6zJoH0dBWHMm1r8MnG6uoSyg7gUkw+wy2R8+EDmORHb+e9mUxsqYRBlBL4SXhKBEKC+x5ykSTameJ3NnjeJxB"
    "TNHgDOq7El/o3oR3EbwuJh/PumExQNOG4uARIEpLIm+lwAN6zwOAo4olM8Tsy2e6P90KZ8oKAh2qi4ieMf9XeE5fpVOXlwFFl7lhty+iQF9zix"
    "WT9H6fOAWNgZgccZKIS+3Wz/F9PcFlrUjGUl6cK/bybB9SBZKfCwCBaqbd8o4ciVubfXpMlGg/WeI19UuzWcGMppDbFXotz2AY8buB5wpVXV+J"
    "SHn+Q7Aem8WmWWPn7QADZkESdhTDPtcR/5lENbM0RXsn7Zox36jTnaJviZXRo78Fs9VkB5Fh7xJAJeHsccx4vHt3A1aDHira9WGipGAiCaR/FP"
    "jY+3LGaxRyM/6euYWEqhVcCYoUTjZwwYUPRM/MsbtqXNqZlD5bUzFmZ5w17poQ1g9nYak33xOpn9frcVxfy6y3hsrkNAN6C1e2KG0TJg19H3QP"
    "lqn7WRZ2KugLSdJIvHtSVc59tmbcNnzGny2mJnm4vQSil7SpM3TpWHk/mrCRmcze16U6Ig8b+ZWAFy+rtyvx9OEz+gYV3s6NB62AAHv92i49Tz"
    "vIKRGKH47gFW/iBe2kqbsnMQ5ii6edxblKAT2RDQPVdU5QEQ/W37y6E5tP7rg3WYKGNbmt+2KBpDqKdW2E4KptxZ7Q4VwpQT9+TSwOvmH2oBom"
    "2boFeXzuGexM6FkB76K1nAouPY4QYs4aZkxJ2XZko+ytQPY5Z2NYB4aH3Wk9JppJk+WMyf09rbe8ew+BXA9P2zEM9I9xWGfUBe5ldQPY8IHloW"
    "ctM13Kvmr5IbUcHtEo9Iu9+vUWnz5XyaOBJY+tmY23xO6gd3dBc74UUdlYG/zNSDhQKYihypIQLtc6/eSZI6P7J8Sf3+dMcHoVJHPRksQ8/8LS"
    "C/uXt/uHCnOPdmkNkq6Dyn1Pg2ooBnI6Oc42HAcA1JC2/SqnjN6U7yU/C9OSFMBmoZfZdmXjvkTHeKup+lQMrHI+gazTMgokKSNubO1snThkLe"
    "KJaWbdYS8Wy/ogaoBShbdjpPrrf7BsrPlyvf7ieSJ5pKoM3jw68Giz40WCYnmSsWExUatcLLbgCuhsZl4ebjt+Cm00tmx1CuRJxwgGKidhvPdS"
    "AkzZD8UsG6QrW3it6A46NQY537DNNEBRVHc9HGc5WPRsVZhz5gambM5eUFPaqwypCCwOnOTHyQ56YGsxmy5g6xjo0lDsCf+xWfFSOYcI+9a6Ok"
    "CDNxWEyICs1ve4zyo3DI391Uh8LXSxh4GGfbDas3zyHZBLBSg2rkC06wSr4TbyMVPUCltVwr+eOyiQwHEmz4JEiFiR01dgsPrt891BlyUXVRPe"
    "aB9jQXk5Jh/06Ud8rOHjc7il+Zkis9vk35s6sbp5eas4L+aPB9NJTUj0XFYuRLzuaCyX0GQnGvFx+RD60AeuQjHhx0mN1zTAfZGbwrt3M5dl2R"
    "Y2yz/v4EJn5zIM6e8jlul2uhoQShy/B/7415NS7MqFvtRbbv8x79t0DpOEv6uPmvK9dtazNHGABFpnAnA7VMRTG5Cgl8BCdbSALew0EZWWOVi2"
    "iXxq7hh3rotgPpH0+x6X1o2e57t83wZmiejQznjMDQXWEOHkrbSpYxe8WUS09QKqArbpsDtJrKcLlyjyEutRCPne4Kf0OjVTPzy4zmPXjrUgk5"
    "wSo7TburNdvlJ7rwYDtsy8M6V7ofFGg9LKzrlPa4bgVtjoDrLRi/AzDVTytikSH7prlyKG/YT4GbDINeqpVKno+PIW0nd+swNzScwV+BccDL72"
    "bcc3PRN8Nh/VyoIfrdyf81X/Dfih8lTxCPMIK96mgUBDuIGaKCSB7r6eloQdfrI5xdo+7qrs17jvVklOrS990J0fYyQ9KNitCGfyZjNlzQ+EAm"
    "VMEiZRGXpm2HlC3bwkJtNIJS3WWfIP9YeOiimadihSK2gFoQfGCF2B3oZeIJMvWVfTIWHRzAWTNpOxIsVCHtlEklfbJyR+YZCRiZyvfbrD88gG"
    "SDsGA3GcQg3WpY8hBn7pulQOWocvAkZAHFM/KGDYy6VtuNuFThYnCcXNfRg4ArivKleJHT3uKGKytsSixkSjQDoEKZBGktlk9Y5AzLC657S0nC"
    "G8d+bBuWK5fOA/UxFYmSANegSkdlOKTvU7+eKZIInoxhfCfKDMtCwzVEshDddS7ptoPSnKfbEowLGxYDEmANRMYA1jYzmPeRjIAJ4YOVPx8+sy"
    "VrAwb8U3mzptakMT1eLPzuR/ULyByUjmynWOA+ejytyacOAWIloywH5I1wYALLqNMNCFIKpcZDUwPUFMG2pkhVXXypE9qZIA2elVSVgFR7/iaB"
    "iaKdjXe+LT9wILYjvn0jdpqhSc16Yp5/VO6TKc/9zRImje2sJg6z+Bc5oy6nphO5XABjVT9thekYZ89ysyiUSAjCe4Ab0h18Al639Xe/DDaCnm"
    "D3s7B1hUky54/lb0oybXrIt5pWAKQSuMchtf/kNE+CapnSyokL0g7vzrvgu2n+kuV3bOda5FwP+fe1/1y69EEkG9xxXP15Con2gKsVtc+p5qs6"
    "bF3P7uknre2s/eAyA5GoRX5mKq8ab5Wuo8beIccigYvGzMVmv+5LXICQ+55Be1cuRIoF1bmtmuUQcbjT9xgwE/h7LefDTm1/W8bYKg6mo7LciC"
    "Ja7Qi8QNuPk/+U2AKL83RdRt8eJCH3bwyR27T7NY0xmWP+rIz6U6IRXN9h9uMEuBkqHTBIUMpsr1BQNew4r7lwEWj9pJF8V1WkWp4zbWo4usU+"
    "qu6mBhz7SDMClcnoS+gC4IOp87/XHT8Fu3ErlD0HffwOcijvKVIK2dilfXaZdm1IgsbLsdzf0Qz8GMKTOgYre7v6C9l/bS7i0IAaeVAvAx7eJO"
    "+hrImSjs7dGsDGzNj9Ey81KPghUqlq9VCtOUdeZwe4TOwSkSv6uTopbx1/R3NxJoHVyd/eSJKcE8rDU3Pn7/bdmjyrkz0n7g/h7s3smADk57hK"
    "4G/kKvkBKeVIFQvgO53zpAOGLdPmkS81phS+nBIqTgHwgyYZjt6OWAJsFL1x8sq1pHNbEbrDLYX/0lQCA/DvtPAcPb27Srr0pROzhlDNt62ru4"
    "7J2zywElhAq1C7ADTXGSMy6AGJPKb2cJvXQXeSV2MLX5rsZmeHJ9OGcdmEWkZ/PV3OCjvCRceGxw4Xk3bDabAePP6UfFdCU0FJ2pBjCAo4B/QB"
    "zfAAAAOvkdcFPmIvYvL4BdBtbJfU2AQ7wtSb/7d3OREp4ree1u5Lg4O8UAqAKuE8/KTb4acje60vNUS6C474Sag2Wq9nFK8d6aNsDXD0++SoeS"
    "ARKXuGBBxSGt7+49ctZZqABocFv7XkDVI+wUrSVBuS1GSnZTmuV0RmcI5kbSiI48bFyvA/8MoS7ngZzt0Mga2MS+4GpeE0AyNsCEOcpsSae/R8"
    "+UpKRrJflT8OJ8750tWoFsVo43MTBzTyKU4h8Li693vjkV6zp+nDiYhJq0yEhY1LcPB8BLJW8tduDk4AYNOtuDZqNByXz5TpnuR9c0+aYhu7zX"
    "Dd9VCqqQ6sjHWiNmgIAm4KS0lR0DG494mhKKfwBg8b0G/gVxj6Idbh4//iFKjxBpkVBFlhw+I8/EqA+iSFMjShMGst1f0SeMebPc8jpFOX3YxM"
    "tAruXaLDqPUa7JhPKTkTXjhbmAibwkKYw30C813tL58QjWHb+buqRZaoB8uZVfq1Vwic22zNx/f34Vo8RhNJuzdEIMNuGQnJAdWoW6lau8SNtS"
    "/+7R5ZRkhdazRTg5CFmYgXMGEE10Kmr3BRGcPHfaqbWR5X4rTqSo82/StVfhpKb91E14Xb4qZi1CCqflsnMnFmQ7v5LE822TCgiOdto7MU68eT"
    "0bdLnPXk+68f2c/Vm5OnEBZJl3ZEa4DMEPsJxG2V29FNPePU6yx6Vu736bYu3aN9gnRJESTa5xTuVyU6mBcrgjtgTVoVAbyd0h+gQ+WJcbNyrZ"
    "48nxivDYWcxjHKeIkZnOfBE1zNIRk7xlUEDQ4dsj1peK+s69LKpQ5hwtOdoJHUg+gQDWiPY8sMUe3540M0toDq9hFFivPlnnKgChaFnhpuUW9W"
    "F91bODB/thL/F4mEQI21oTZwACRBAVvJuCMoLzEITNJHbq3nSZoAp/CvJv87bVXE0rNY0eTMdZwlr0D0tMASOay25fVkWwtuzmuqH3co3G9bHx"
    "6eGwvI8vTnfgGXKGdjOjoLm9Ozogc+Wywx1ySXTHGL3wG9y9wrI28kY10evKvs8D/c3wfiaKg71tkylm86UoULzbNUzFXi433ctjJMakhrUDsm"
    "M1kuj3JnAD1YI2QUTNTlXqMAq0Q0yQl3aVcgUV5kAYrCb6307Ix6YW6s0XKVY1e409EjqbPkRcho4XRfM3+k6y+y0kLh91ZTuoeKS0eM+Q5m1X"
    "M2mJtWo7Pc2mBpZlliawV5b31JUTI2a4KZJdI5BxSsecBKt8BruG6/zaSFRRh+isWhSzfrFKirwDjm4v6qg7H2TFnjFCkTdUv/yXLajdOQ84zU"
    "pyht3NTtkzL3AT74tZrPbZoGQeZHZOyn0ROUCL5TsK3jyyrgBPTCUUiCdrL2I+Av4LdibQdvSFyUIX+0US0fPoJZrjVd0zMxgRRcjGTeZtbTj6"
    "9/+cVjVdlOXHvIaXefBnrfznxaezCLnMouU2bk5lbdgRP9NIF7/uVctfcIpC2ykHQJbFKe7oTdl2nowbYJ/fs+XqN1OvPI1zOaXDezqnDM3h1L"
    "pj1ULEn7itSmUXoAMbvuiAmDv4XjFnDHHTewQoFDB6xZCWVK4MttXJTXnPSDnt5TDOzUOZLSCJ3Gdd4MBlBpxw77vKOd8OCy9xkcTuz9MWkam3"
    "tnbvgSqBoioe5BhSPbGT4mwS5PNF9SS4jNHNvl0WooiVY47fXPdv7mRMrsmaikW0yaB1FZ/BO3nfk9BU6wTJA5Z+kinn6GvmSTUyDuHw1lZrYo"
    "sIgXMLUgLIkUTJQEHH+UHMjnDFFQZMbKdf3NBn2DleYvj60t7DCnh/BfRzlXojkJXVCkiPpfqD0c8QfmgC2Ztq/B6SMd4krcDb3LO9aludLBsa"
    "KQz50/9SMVSfpJg0RTvUafVkE0S9Ih/j3ymlHmWSNzNeDgYzIhsHQkap4H3Q2e7D4CVkZIZVXe9YR2sTsp17S8lqKXr55DXjdtTkd6numfjb6i"
    "5Arc+TsR3r0MCJ+BOiVX2y7U5Y/0vg0XETOCXNS+FDBwqj3wgsp4AEQHwxkjeUqfFPTgaGKPxaGSXoMR41Zp1MtLMPyJrfMWsgGC5MilWZ16uX"
    "Tje6rdpRsiPLuRZYUmiVhicq55GtIANrQrQvagwf4/wa09UlGkwPMynCGks0WAQShHelWvNkSzNxjwgkB6pFdITq5Wl5c+QtpsGcPRgtugvHVi"
    "Iqe4w8+3rZ1gAsNireQAJAM6zEz0tMly+Q+r4hOUt6z1t86C70o4oy3KmMI0lGCNc5CXuRr4r4Xka4s5ZklvnODuSAtToX3d29DcwukyoboduC"
    "KcEHOX2JmCCZkErx3WaU0YemusTRjuioNwn/kAeOTzfa4wwrCUqQ2Njx8CBLWOgUy7wfHmAXZI9rPyzsvia2uyM8ZliFGH1EevtZvD54OcCsUC"
    "fGuKfbHkJbLEru4nlj+MHH5+o3pw6GReppWEwZ9mIr2V6k+mERJZ1+pngA12L7V1c5azfOO9mp2fskRNamsqCvNngyoopJVikv9UiCkefnG63s"
    "UiHGc5PAhryFjfOUbllEgH0NuvQHZVYJBcoap5lul5v1CgqD0d8UcvF0f1XfUPnb1Cz97rHBs6Q5PKUUuvGufkKCYgsvPEgmkmokhoKIB0NQCS"
    "N5SI0apLIveR1MCK9o1V9LeblOQOwhhjcrsdBkySGZYyDYO5GusJRkSSXxVBBxnEYN/5TkH4PcVgwkWQhe8zOZ0yA8xfey8n97DOnTD0bffapF"
    "i/DVaGvl/w71iKqjdRfKw5g3HT61vflGPegjRK26CiycTBBhc+69lCLX7SRaiCRGpAzFCKeebYGu5ynz4EnKHii7Gc1i2Dsi9aWHGK85hh3nB/"
    "BVgFRU5ihLWGR0IrMwhB6hpkacPNKfLLZC/AindNbpV3dW4Sys8P57DUNFsm14OsMxfuM4ynNSn5MSROV/dfGDhNq+Ztov7/0WTHIWTFN9q70W"
    "3tDaG+VJ9RlckNM5Ct1Nm02yOnNCm34HYA4KpSS52etU09+YvZM7uq+oFJH2pbyzD4oHAO0FQVREVI/4YwfjPeT7BlSM/dfeXhNGEtlMzMGgiH"
    "zCo4GSATpTazdKMrvIQ6p+dtJ1inVYnPapqY/7RCExXeGDEa2JaMpN1PfRGPJjFiC0v2ARMv0WUZyRt7tUXAlLt+54i0YlJR/kmLoaTABdi1kC"
    "4rTX0qIfGmsA5x+CbS6rGQSa4OAKFbQKGmQCB1QtIeojdCLCfaQBLQRrAfASwsvPB2OtNIS0OUVVlHaRkHH5XOP5oN1hGmj3rOnuozt4WclKm6"
    "WeSUidQleN5usTBe/ZNrKPJyTOAA3jsiWs5R0jAAH3PZzPAwwCDIOODkMxR3Uacwn0n+NNWxKH6fgkYspiQnQqjSlh5jv9xQb4RIxpbAragVaK"
    "AyCdTSinLAFxByKUwM1YNyiBZNAXXZYkoLbrG37YVXCS3NFZeX7R+nU4AISZA/QvwvTEFYbK1f7AAxeiDVlyhb6gBg5x6c5/ioyJwhheAZMizx"
    "OYxXb3RiI1/AvMiKOKPhZ/UkJf8JaBbPWAM/svY0xr9NMMaeD6FMne1mYlESb6j1WfwDUz4MbxHdZyxA/PIQtZV4aHifC6URW7u48iTsCoNLVo"
    "PDXtdoqzu840W9UnGW0ELO8NSSFsJLPdbzUs5dXv+OsOUoi1FmewOLnD/ntVQpI2G9pnVjw/AG6fCZooMOLvBYCeL083srcu1HcmoMMTckaREb"
    "/ay/yWnCAijri04Vc+twIwFCj7YPnV6734OPng8bBhQiPNgcYiAo/8joXyK8me5RiVouRHVEcxd3Hzqv+UMo8OpDbFAnDrDjE0QnazVx6eZVxH"
    "o9A8QK9R0q46Wwe1qzVB5Pv0+1W1exYF2YGCIgR1OA8wZsOkJrq5Ce8g0SjULk2bq9S2064s2og+i2Rhx3OE0ayZoeps+jASOkvTCed3ykpWOH"
    "FgjrUMCcD876eYvlo8AEXtBPJduCcxwsdabGpC4fCS9D13l1miWthsLXhbr1j5/JAR4WBeBZpP2QYuivVadpwf6dadlTp8FeGJdIYhj0wLtKyN"
    "TyXhhp2OtoWlXgYU402cjyXcqqtxeVTc1+MoH/1NUR837Q9ZjSsCx014hFxkjD+hePc7QGA4qIGtO1OOrPiQNdc4728AV6fclgmmaijJWxwNKj"
    "SSjAGYqfnJOTGv32Ddeq/PdAbm/KQRhzBl87A0feawS7fSzsDED0B2TwF0ynzj7meyCb/l2NmSX15aC+RYKXblOdRDlwZIHidE99tEqcky6rvR"
    "u5LlWDc4G07V2KnergD+E0QmgKhQGMHxqF4ZxfR6WTn3BFul443370I6zBJsWYoz70Ucxyaz6DfVInoIBh83b6MTzrmaIHu6xgl4DYt0Gm2Teu"
    "viqifOS6sAAIvSBG8rqL3LST5Iytvf/P8DJ5f5Knhwg3AsOJ7JTwFtdgkztqvI434amBgIsL0I9M1BXBvlG4Vmtnj2hO2IUR2B0jtzO+F0jH8o"
    "UikOyhYIdnuMEC9PgY0xPpOAlsi339WQ3bRZ2GDCco85fDauCAHyWpu8NaZsOHlqIpDrnj+FsHdAP+otmwAAGSfI/odXBqNYKJXWFf73f/FcFl"
    "iV2XeINFbhj3uCPexQD+NtS72MyHTWDY4avJ9oRd4exLaPpO96KH3DWGv2jtI81ym5btEqJVlubTf+otKpx2IGKhfD0SeAB+0JeidxTuOpEKfJ"
    "26Oo6C1Foif8UHQpUl2CzwWrklbKnQ24p8R9Bqdex9OMWL/Ixg5pcCRJDoK7NReYkqbtY/beQ3lQ1aJqyUnvc6+qqMSECAaZ0qVGB5LUP2Tcgg"
    "px+fDZsHXU5t7QHolhf0D4mlR1JL91mD1AJ76GLHgv73biDaAciSV4HYRt6CxXaDmh6sAWIUv5dKKIoGBK+Jf17clBMNNgKfzVcL5lXfc0605Q"
    "vR700OXDUh6ahyrU5cUWk73p5++Sj+IE/zLdWgz8NKj95t77kaHq17S783eaeb68fzyHcCc8dLClSAmGKVyukCR2bBKJ4tu/W/31x/kQ9m5geJ"
    "lGn9PMT3ZlLSB72hqBrNZRLMlevl6CUf7vtl7L37LORhXXaRHP0WR6TiQjfk+e1HXTmvOB3XZVC+VL3+UfSGv3tYF4O5MecGu10wg39fseiL24"
    "gJyPXPqLHmz5YQc3LAjPY78vLY8M8yc5RtnaHa4DERjDWMlMBqcuKsk1gQLwEpDHa52X6JhaPI0Bre59uePjE9menc34cOkPwC8wZGYGVdNvng"
    "cCJd9sP+8hrq1ZGjz/v4Yw0o/IOlicShrUHm99OD/Cpso8qXkXTgXZtttPaJdF0EGewLE3uAhMWmFcTkf+CadEv2/cZlfnURRniRtvKvboe+zl"
    "eZ3llib6HsSjzVtqmulU4f/w3sJ/EByyREE7fNzAC2K17hMglxSFgBbmb27CK3FZAtax71G3Hv5g7G+stmizYclQruo6AtCPhGp/EK+LpwLH6S"
    "BthRiqd9igadKgzdEYn1zIIeoDh7zlqgfTv5XAWmPQ/Br2nS40D+DP3TwxNbZlPwft5frrtcb/mqbQG2NVUEiwXdaD4ivce9L9RIWFg97ZeFH4"
    "220JweJkM7fHwemlfcU+gAvt3p7UaAVDtbwyqM5m3IJ/6jyrXKsbf9uhe1KjJCRBbCSVvg0+69mj5HKqtszXk9XCFSiIoyxLhRbUyeodxEj8Be"
    "rupPZKm0gapi8TDw8vDSsY4n/6r6Gihub3qSa7yTQFXVh6rNtBLXGTjksFp8GmhpkYMuT3gsNbL/CFh9Mz6nCdlSb5t6gPuMPanH+8L5+jLEWz"
    "jvYmd6FLnG89KZovAEjAjddKAsrh3tk5PlIu80Vj1dZAA3BZVz46gK4GQiK5zB6IPKKiOfaa3YxEy0puWwFli91DZLBe6+H6W41F9+ZpapXS6c"
    "1aBEfG3l82Nz+7zzgOd0Rq7uvv3VZpnjrridl4zAaPDKo46L9cL5yNYiMpxmOUASHnizWgF3AARf5Tv+Y1pwHPCcAAFwJPAWWN3UhcC64FYhxY"
    "hwVc7y8srfZuVywWFggzVTzrJhQ5XMgYn4FyAw5JcGoECEIIiGyJcj2J8SJxUoNDsqDZhV9CxHEWtom8ZWHDDJY9eU0j1OJcq1IbTIGAacNtYj"
    "c36nTeOeniN8uy/jvI8HhkYmu6p8KmR/85c1Jdcp4kpB663tj+6T7JnKIdOY7/JLoQ6OY0MLJJsfjpBYZfBoOoGKy20rqm3kBJwGozWdStKjBu"
    "PVQ86/0rH5GR6eztE1Z94IyzOcAFpW0H0mrSe92F1Mp7b96ZnBMES2+g4ymof6+Cqb5FXz1Eu4dS9JzC0dPn04FZrMZDV2yXdlLmptFjp7pu15"
    "tAL9cSIUoZhYMgfPnOtdm2K5oJfWJdblMnoKTkHo0jPtRZ8nHTCBhvL9IVmNDG5hnlKUq0NLt+bE9H20qUQk1cx3LbbaQT20Y+yQ/14sCNWv2s"
    "FDFEHTOur0WVT0/jOYIXyDk8VXMGnhL6srH1WClXrxACKarQ9NG7jtbVmq+qbGho3Bx7y5YAV0l29cMAEAc6Qqa+/G66IrSCdY63jYlyDVLvqn"
    "yjt7z9lDCUTZR/fy99z8V8UA/OtzTe7WRkS/vf2z4yndBsjGOG+ZGVav3KbSKGXNCuTlMYBudKvWEc9RrrBPqT9Yw+9D2jArS7doqqs2bMNlBj"
    "GdwaW7af9adBLLMbt9ro5Qy1BT7GLf3YnfNVWGS0dySabryv37IMqq9WWPYhnxzrOpB7R0kG4HjnC5BC0kGaZgYXcYrUzaghEEoyK3JDzL0rrb"
    "PUUPqAd/DpPWM5+UfkiC6y1pYUij9QUNecHnTdGQBn+W+pPMWVACdO2YIOVYIIWqlQ9NdPfpJhXKNy++ZKeOaVhlTqCP5MxA8XAxFzyfpJVgXN"
    "1alFVywCMFL/MUq/6kCg9EU9bjSxmorBERvfGgP6kE6xSveR1NOhsiUpLPl1ShgqJWbhB6wQcHLKdzqQrp8dGTwIEB+szHcav9DnmNIPUFFAJ1"
    "/jfhSmfGNFrew/Yacivm3DGp9gK1b94Vv9HhPpPvdxReHQfC+JlSN6Z9fqLUjvh+CrEsaKYrOuXWHtgAFJobC9NNt+AIGgGtjygEZ2R3wXaBT7"
    "x40qU+oWeJ+fDw3h6l5x8oV4fFgdXQCXLfWR/a+8MJIwDDpxzbT3lvfM1+9rQvmm0Y1WzsFCKONvk2N4oRzDREuJpQndc48guW+y0CZdg68wZE"
    "HSenfQDidZI0nS61Bk88hb7S0spnUj0j8+UvFya7fJfOtSNnt+PsErbcXj/dvK3Evg2Sm/slD6aItDOhHV9Z5ajDlGFcAbOEbqzXI2PbD4HOhX"
    "3h5xjQXkSSmC2UMdwaiEJ2L1C742iSygH+Tl1buZhRLCP3dI/aqAw14p81mripG/mnCIS/Rn27W6iTK9L75ixAEmXwzYQEmwKfEhw1PCqlDR3x"
    "U0XVENj20uWQMF6SjDFe072h9j300UZi/ZeZ5eYF19/gdiYBBqG5UVyaRpU/hJSw6ai+MGr62l6+X/2TYKn0TQFUm0gc+KQ5Kr+4p5slfKnnzj"
    "yEO0Jq6lKII9Cg0hvR5Tlu6OXJ/vsunEHAKhPVWKm4VbZqDgeHnhWIfZdUOFghFX5/L8HvdfvLiRy6WwBhM842KNFJG3WXW16NFR2+l5znq6PG"
    "httOM9qvbaWNTplLZU23LOU8p2yVkqpPoowP1yKx0BJODcchVBlYBrP2MBd/Pe9TbJD4xfj7ZjajrgCAqpTDn9CJp09afBpAMAVjpzvMh8fNql"
    "s+vmGbprOtC0xht4EgJXQk+pV9KV1JeIP5rlttu8Q6baIfxosiXeyChFmuIe1jOSBOcOd4kNbbHdG178Od0LE9Bn3R44pCXkRGi4e89baZ4V9A"
    "MTBUldO+/M+HFt1KIf4Y/wRlOiDrjEjYeSe9Mi809zoBFnlfkGYk/2+bEkKM4SQHaGifIx15fH0Zv+0Mi5n0wvAiKktxxMjUcnZ9NCt9PZKrme"
    "dvOcftsRO1oFjifujx59eGbOxbZ/yTEHsioFQgKT8qwxLUsvYLt78iDAiuquBz6qZHrgdLbzJhr3ybcye1xQLLhkGKE90S2AQMut+IPTSyGx0X"
    "6qtAfXnSc4lRrMgllzbj8Ufv1io/AC+Sps62igORy73NEYaghzGjQvKEGUP1YLkujv+Cksno556Z9lppF/R9j443AwGxnUYN+rDhtgWi8uoKEf"
    "MBQYe18fm0IC8lGas24UPxODGDnzAeZVwuEZ6QXYtZ9vpwtozTmoL+TMZXPoQj4DpjYr9mIDKdUGJEFr2KEvEtIjjje/LNZPRkes59Mc1n6FTQ"
    "n/6UZbeL7yqWtF+MDcNC1wrTOBSBD4h/suU21Y7aMSI8FzE0ZNjL93v5yDZTnqs4JRNtabMcdIUJgekEMiWqnJBxcGMN4nmUOkfnaKH26RLJZV"
    "lu4EaYWZd1xU9tHGpBLIoNgRPhZ6txTyhvAHsa1Hv8dgvNTp2c6cy/KLjBC8Zm/7hvWc7um0EcWUUxA6iJt8ptVihL80pZdeMKRmD3Pjx8zDWL"
    "smlhnLmnALQjEOkmdRWrcY47dRY9hBhhnzzxJt/b9W4H1MP1O9q/zCNWaQTQ56oulXUrEWnuYDmyXEyjX+09j9EHngmQcKSHJQeecqTV4PJkBR"
    "3Lh734N0m4+ffr3HeIQ/P0I8A2lj4aeDu8wZFPpFouUIX+6qSNJaoH9wJPofMoC+SMnWvXogV4sLf0i0nLshOX7TmjMaJLj0lAD0UDhvVKm2Y8"
    "q/QB5PBGF5ZNBfQgc7yMgtdHLp/MXNa1rWZuRyi7JWJqj+VlAhNVnIrQJCjQbU73+TFB0u36t99i9ZXsdV99YsRABhUQ65mNgplX/FcYLiFrKO"
    "2j/m87XdEyaeWQDHNeeOlfs6XYnapXJ1N9LvhHC2L2gSMSrmcdXCazdjEM8ACGJE1fX9EA1/mu3C3mODrqWItWlg8jTq4bAFfgoAICbC6TcMEH"
    "CkTQHzSdrTyZsHJypWXOcsijncX02phCDsYgmm3HRY4iZ0xYCIgjQTyW3UftxCZuhalu1Ze/emT9PO66CaukFatDUM/t1mXXD4qS3ipbu7nG9f"
    "eu0b9B7Fwznju71jHWGfJ2dzE4blVFu5qZDc1nSUSlHX4Z6zHAik3r/rdEKknlWW60FmlctM7zJRc29SDf4JqeCDF0vRSoRsXeIx8+XYFgBOgB"
    "3KiMGn1DKHYh3rpLt+pQWbAIYC1csTPhPyIIF+iA9dDwdKYPEor916PCRpj2qep0gog+jn6SSYH10GJsuOL7KUE1382wWJxGS9qTpfUbg4P+jV"
    "1JNYwlgbCZcuYb9bCJ/x6GiYelZCn9kDkzHSJG/edh7BoiL1WzmlD4VqGhfdF2OAaVs7XiKDkBtM26cYwoSxq645JThqCI7u+xxk/P1FpQvP9a"
    "dBrG8J1MHo26sfHWs3A4DeTDkPF4GAcp+2/k6dVlPefLdatkBHOB9hN3nT+wCBRdbmsnD5scmeJn81hb+SsBrxxETbwirDw04wdbcUXLF3JNus"
    "5sx7lzj3ZdRB8CkDFTdmB0MyMi7M23SCWdJWE52LPAVIJ35e9WdFYgr+6WwynuowLgJLe68kY861A0M2uhyCjZk9hmh8bg/pa6lnJi0P5QOQ1W"
    "3EDc49rTL8r1lHAHxDluWFHxVgis6r0lhid2u+XphY5DxcMMJEGedjMEQXXYJ9V6nTNs7v5NIZBIA0lDlU/o5gVlb1yGrNOP3G5AN8hJQceuVB"
    "9UbePz5e03kQmE/090zbyWz1rBadbkaufYgH+56pbuOT1+Stg6RHHsPStGw+0j4FZDQc7JUfYbB9IJhzZzV1wfI03KMMSwbEEteWdZs1l/ut7g"
    "IxhUW8rIQkswXLYyqaTzEjhkZQS3ehdIueqk3u+5Lf77YLfH8lEknOogwoAn0hPK1US5XNAc5RTEVhKcxdYSKfaiFadzA6bfYaBrcOZlP8MXCM"
    "AkIIYjkAWFpIg3zb5LCL4YQ5Ga1tgX+fHL4G3mVB+FCDLpY3P04AuSdHbjcog8CB1OYfaAIEZ05UNBuKIgsfSQPlTKSqn/mJcCiN65A7f5l0PL"
    "6jToV8yhDcmcdfc34oHwMG3jRfMIb70jEY6mkAIP4ZSd8hQD1UYFEjewP3iSoirOMs4Vu+1WIVeY5DvaXzFOjn8CjlgfnhtXG92pQyeK5RMreQ"
    "izCRfDL3CdbZvfupbGuaJSMef3bI+ZD8Ga4Vs51+jMX8b+Sdy0t6YTaRkkr1yyJWxYPxjPFc6KNqeD+aIPs9qR6ZQbBQ0g7yZqNqvDBJeSMKDj"
    "wVNT0WXTG7z7o2JbWga/mLFzZO/IwhC4m9/V3+seK7M+yh1d7z3skuB8/va2sd4z4uIjXeqzpxrDU404Iv6DghRKTmsR6VjSbnNDslMZWoF3iw"
    "AsDMh8D6JlBrzTIehwSYFFAfkTNDNr5wXY++ilbaP0w3BBYsFV3Q6XjwV9DAhgmM2M/agMDzU6hjiRyH2+QZ1v32ZPSZPCpAJ7c6y8srBsDMxx"
    "Me/JoZM1oho2PN6qZqvH2gr+pmjA2I1yA9kIKsEWm6ipO5VNNpDMzimdNBYbcwOVIkl1JHut2TQMuehyMVzuGu5h1FFpZnERTditsfmnrz7SFh"
    "N6wy5RmqqRhYAcZCa9MTBGeEJaq6V7hYX9U1PkiwvUPdm+ncI0D0dM613XckwfrQm01COFEVVTki9HnLBnabTdxRiT7uifaADQirtK7i4cOW/2"
    "A6ehUNBUDvQWW45KPG63V1F9i9VJBu4pzjnpTUUpOwVf2v0812g0RU6Q3tXf7vCYkNMQFXmg9TRgYFmxnDhCi/mQaNHeu+xbZi964DQ+xL3KOJ"
    "dImNkEMTMZqaQySLWFJxS3mxWyQUqyZwRkFxDQfFPTsLqmQDtut4hXxG4g8w5DrS0LwNA/Xkqht8YMIn1r4r7MOqcNNL4zkbW2W709cdbHABBJ"
    "5L8VWH6W1pqdv+bw1smug3CXjiniWlUc+m9b9PIGE3eyEjqAeZ6ocKebYu85I/d8LSidFXIJVqRRBFUgSx7eo2usu9hA7X3Xzdid1Wockk9pbl"
    "6YbpzwzKiWwLfh4nnCPyIfDOmZiHvCLVyPYf6hv+eewDT6qxS9vzeeEQjAXGP4c2EzNy/BkfaKPc/VQIdQWhmrsbziJcvR9Yxt0WXCWmNgXrMa"
    "oSYAVtXYCVC82YDsABcHNFPFPpEQleiff1lg5UD8t/wm5HLHHv1eTwvfVUMOd92QEYlifaYc3qc9J+S02SiDhbySOk2io/lJdkjFS8AylbuJs4"
    "OS0vBQKazAPvaw1GeQf/+hIW1lpkUHig8QMHknpBPFVK/Jk+ElY+44BNyl43SCpkhaXF/AxBegoD4HL/hM3spDnNvuh94hB/tQx2zT1KmWm/J+"
    "xjg6l+250BG669y47J3LkHktpdIYyiWlrA/y5tlj/HZvqtJo/cRjB04c5YGXdmz6qUabNXVTcse5pK2iUQBdn/SQ/nHnXxJFjJyHgT4h4RlTO+"
    "38p73b2Di1ikIWJ/RH3P7btbhS2KpNkssIb+HgE18ISL6p402iIDrUlMP7+BPzo4vjxdpAB5Nyma2jv9d+et2cP2gVIBUmvsrTEBozrSZrMFQ9"
    "5ljn+mD0CBoU7YXD4R18moYq/Os+7DUuewJ7IZGCHd9tRa2oh3hRNnvxKZLsnTYkAkYojX7Ly9DvXkT5hyntSBxRuNx91BbRYRSLTBbbMtmdX+"
    "cfoVCWjvQrSHDvgvBuWuiqaVVgsv3nx+oQQatVJl/NE95F8OQyTBY5u38yVWoS/S5UAtgali8CJ+PC5ZPe4i3hmbqIQcLM89tPIwB1Pj8Jz5LB"
    "ZNM5XElHsjCyVYaGfGaevTOZWwHFXlYoaWGUL7NGuR1eqtZKNQr5iMLD5GVnnVIu0PFe8+I243qleAczHqrqZLzB4RV6AJstZbd1P0hSH1hrwH"
    "Wb8qUaA5Jq2lpe4qj1WKREseTtn1dLpDoSmN7hUSNaUJJ3w6rdqwwKMXSyuPPWaDwGyFshISTgxWPaZOTA5GbTscN3ZQ527y03Imy4QhqnNzj8"
    "T7HjnMOGYMCoh9L/3c8/l86HQr3mlC+lkwmG12OVUjyZ3Xo5M6VmZFR+NJi9IyqFsVNqptztpxnXa7xwtkBkdJoh3oxdgVnLcsQWZDXI55Ltaj"
    "Ks2l+bUBfeMQo34i7B5AWWf/fAMChU/7BX0fpJHkFYi0z9e5RHGP8ML63fx9xq4pb9LtPgSmueBDJrTu43CtVMS0Sad+GtPkeB0OpWLuJKBLxD"
    "bPfZPhCw/hFgWSb9ZAace3N5HTyvmKZ7BC6ntGdYtmFg6rUjfHZ1ZnQ1h+mSNcWkYSbQUMX+qVMhPcNBBJ8OTZ2mwZXAKFkcnHXT1k1B3HEB7F"
    "Ae4VCPH2s7oDVwiRMN6IidlDtQyBoAl3yeO3saCtgUcoMh+EGc0hEIQF/kU/ttmr/zVG0COyl+8pSCzBY07BCWouyQR/YkZvCAYjSLFH+eb71J"
    "ioRw2GKkERELMm1K1mCIcWe1n170zyplWEoawBdgZlOlAOYL/k4xT1qJHYNS+Xn9mHPzRGB5SJ549i1w80EpQJ5o4UP14EE5d5zUNBu5VN2oOP"
    "5M24CYNr8QXoyUrBdCgvqRZRnKs3s5u+UHRkMsHwZjRo4Oz8pn34MDQqR0OJIXteYAks21Teylz4JRKL71iUJ3Yl8DuV/5dS1pHpO+OKv4l/JL"
    "9H/ZY7bz5LJ/jFche3tYLHvopKRPKwjyiNWxzJj8DJ0a+fArX/T0087vVJJzr6kOfWyASs6vETCk+EeLJOHHpoDtXJcwZDzefojPhvTfu6msDz"
    "KmrJ8OM7wXBHRMQ+PNcru8MuC3snLHi8YFGDw9186emyDZnliuRLlDrokf3nlfQywtakcLyRoWX9YFl4wv3/VPqHwyvXSMpbOJ4TQ6327EGH+e"
    "OLqAst9qCvFZyq4TfsgNQDh6VieSLICH5+KDDCe5s5BHGFBNmVfltv64PTec9q+Yqsc2GkzeGYd5X2IUTTEGoxcmmzYQQEvvbSO4yujwg5dX5k"
    "92dcPaFXka98uyAfkc715B1YFV+QZgn33tQs41ii2skfBj39FFXIJ5wddP3y4ElFBElavm0OibOos22TyDcz8x29COb7xL86Y3ym1bE2VofKfJ"
    "3eo/hXeeHl76EnvXxaOvzwyyz4pZNUm7aJpZ6YERgBmjlxZcPXNE+cP5IiFockMr+cu726tRVDARpic13h/Sqe0GiqlBLbzF1sgfDe+vqnmF5g"
    "5skixaPWbFxtf7Za3ix97PA1hm5XOjsFRhbNYuj5cuBdizlM2h6xQANauIFEEa/eqSSNAxlVa14CzPSXQRKFa2NzepDKLwinBCw76MDhaUUH8F"
    "d+Lr9B5ADqm4jLH+oAjQHXJBGABm/lmrd5S93lakQBKM78zQjyly77WboMpzcQ7ya6e4Fcz8YmAw1mHZArNUcnxQAXJT0fADl5KIQTKnWZq8rf"
    "H1OGbAT/z8lgLXYy8uN4GA3OCYMGZSZN8LG3lpWYla8Gs9gcTt0litUKGgcKgzujVLPi+OMx+qybPPKAWuXKf0w+oPBfxlNSVoAD3H2RmY+7Dk"
    "4ZtlXS7XgOTbX67cr5oWaCQbeaur2xnWj/JZH0Ry0XIqBCSjPtcjvsDJTsD0bdp8i5tmumGnr1OLG1xIIZXu38sSgWgALFmLyCvh1wVM4D/dvQ"
    "97z5iQRmUIXhWjqOvxaIEo/fkO07yU6ilCjnDTOtJBWOTpVR5N4dgKfGRsBDnGsVhcBOY4K+EqH2rffLOx1h/jrSnKeEgltJaIqlgHHTur/z8U"
    "saKRE103p5xEUHB00j6oHvPpO3t7i0CaGIcVPaV95GYOgJkmEcXCKM+1AAoba/CJxPQOPdMKFjFOG4Wy/U/yGpk3JvHUw2nVTmdU0Ngunyv/MZ"
    "UOGDALVclCX66JAjot6dO2XqIe6Nd5+jPbHZgyA4D4SaYqlRR7FshFLfyPJnJpshpFRiDTFcuphXL12mJYQWKY6tWUcSFq/7LpDOacPp2dYbXX"
    "e0rGyQLmfHO/gIhMp2oBh1BN8nCaEV6UiAvgTfWu4f5PwrQcUnJmOR7oObZUT8lH0fvf2LXQvgmEYG3BMsWaxUXXOtONZywmmkZ0O6+QNKrkvV"
    "mpPUUje7B3GP+wBd+Hbchm19ZGD2RZsWJQ1YrzCdy6byTXaAB3CNDcS2ErvpLbb84/W8W7tPs0+PtlZvhbl4EXOhi5jMEZnxHeLTEN+ZGO5Wfu"
    "ABOH9+rVsVq+6Fwbx7pDIiZTwW+5M1U2ftDL0yCqCyfGboudje+c3nqvPkHk+jHS3pn46c3FYEM73eQ+9XfdbU0+qGxfqNGcoLl1r++oWYY6WO"
    "DcNSDRk/q6VDaGdCda1Sq/nn18fJ4+AlT5jhnjrx7bJ66pFtiJ0jlJhin6Inee+Ia4w4Ny3GZu1ZveRi0EPeNPJFhonzahHhHBBqbn6AF8KTxn"
    "Zc19FSEaKIMgPuCeRDOZlCXDnN7R3xgY4R8Ur0IwrmyLNNBMGBOs8a6XYwtnPz2zKQs+TXucRdf4bU8WDrsXGmGJtS8MVHxa9ck1v/e/uF3nP7"
    "idk9GycavPnRQXI5eg/d9hRqRNwzdp9d18oRAXI4odDaFNi6dc2lHrpVOwL/Tug59vJp4xMfXhdHcA3+/M0T0sy2arWNLSoWjCyEQl1ZCR3akj"
    "SRS9UkKNeBrjKnjl05W0+A7kKVkRWlGG7/xgBRnPHTCIpGDbTOoikqt1PBQ6S6tR5R5CBNaKDw8cNqgZ1j9JfumVKW2vwZhL7klCJeFwM9Jwb5"
    "cH4pv1ukyuKfT6+xBJALt465Xj7f2Dock1JiZaG3gkW9mTvLRqWZxmnfbrNpn+9FDNNk0GNEzdBk46wXokvR+sVZbrHMyWfBKH1qmQyxu9Ql96"
    "CGZjHtYHKYGp2wqwiq5+YvzZv9e3NTFhPexhKD9UAuOJpF32DgizkYDP6lDgcfZqnu7VW5Ncz30DSBBfAgWTMJOc50wf1e0iyLfkuEqTc15HVN"
    "KjFKzJ6ytFoz22F358vUBgy5sI+TeXr0AEt5i/YelSEw3jvlcp/7+LertL5dzgVXZ4+eK+4tBes0ZI14dIWoZg4F5abDPnkEwp0ARGCnZwGaeT"
    "/HHm1JmVeTDfONQESfd9QUuM4eKs6Gpd0Ocn3qHYZ/ysIp+QNiv18c5TyZugdPmFNHYsTz0zsuzI56K0u0K9JGDi28CuJXQPq4SqEvcfXRhUVM"
    "oVTWYevruqkB5ImPx+cuRagF2EJ34IPUULjQ4kNbAQ9YM4HxbhOAr49y1mNUoFS6tU37Da/9MwWLN61o5dNIqBfLAOZOBQ3gOKxHKsfZTi7rIJ"
    "VDe+HqZNVFOrfrh+isXXwCjAB78uIlHExCZVgFrCJlyXkpqR3x54tOum/tDWajtnNXy4a02ZeNkwG1NTGNwLTe43u3FjkzFr8B5E6TIbZWn9Lw"
    "ZJnQaOlyXOAU8+QBljOuyJPUiHf8Ktl1kpLvn6qQv6LB8/fdEvjDXJwXW+tU/5aiOIsF9ALCSmr+Vs4vTHZNbzSD/KlenODPjI6n7ey4mBHg4K"
    "7Hr1mls9Og918D10EpZKlOYbnILECQ/DEY8qknpNWT1UpIrxuFfdXecp4/ueMIgJP10wKonSoatRDPhtGniDSwmMNzayxz9Eb4jVgOILgMW02L"
    "iRIIXOfMYmmF3snH2F7XKdmHrvidU0yI3fRRlgyJnFmhSsn15APnosvy5IwYprrXHFGn1nhV4RaZO+jHn10W6Ibe6KR53yGTIkW1VYePBrZ0zA"
    "3Fh1qbnhENIqeI5QfvnC1+2g4nTsPTQvGGQgq8Qs56l948GeBf7zyeaQdIaLN0okTtmBYp1EN5lIXQPuBa0HNvcmG0ae9LSBHFcPs/m+/Y+TiS"
    "XnDtE75xi6thRFKIScSQj2lkVQEgc8FV8BX5qyg150iEqgGpwG1iONqX0ld4GJRkz7D5x4LgktB1iEUuR1T7NBroEN/Vvq+dV5G7k1tm0fntDL"
    "tbnDSXYBFyGYMgQBAp8W+WY0RKuynzD/rmuFantdu4Ai5nE49691+LlDUqcoKhUpHNNCycN1fokFgX0bi5IfIbyhW0zPVz2RGCtKOXFYbm+Yy2"
    "V5i5kJQZ8zRZTF06WmiracO0XaPmlZXVWjjSvUokLx1rhFPKoV0whzqdnTSJ1RWwVuG1na3mVxlRvwJYja6X08ac2JYKC/kKxhvcJWfHzf2w62"
    "YXCSGpCeLuvXvA8622J+EalU9w36QwxeHmN6teqo0QKV6hChh2U/TyozW2qtyUlWFP2V3MsJNW3cQqCU1Oo/p9OAfwwkWgOX5eFFFeZ/Cy5XA2"
    "It5bH/S8RGm9Bzm27LXE3k91E9tU1dlOF7SdE7nMPC6Tql9nWNzuF18JX+tiigo2dzxmMsTK0S80LNmP+y6ox+UyRfRoYEvuvsMXKE5CV26fJU"
    "3cgq8kKYfIXwdv8aryMClZ51nM0JxarPcQ0jgkCU+y40jnrqOv3JoOh+sdXAHaTYQP4R899igeH2HcwGQgFvs6zPNQ+m5W9z7t3tcu5jZ73+Xk"
    "8++0R5Qlufob8V79RwYeuZFeD6rrwiTBHGzcis15OlTeIeYoTClJULmsNUW1sFeMecUAvHLMRMVNVsMTePxKWJYw6NE3ULsM3pPyTuCbsPxrBz"
    "uA26dY/bxU/0EyzrsnGl5CR60qxRj8A73xQ5lEN9iXPIX6nHpUg9xlUxU27Af2HQAlJvIeGJrf5II/ICLsrijtVZYgwhxdvgqZEd36oNRk0R7N"
    "Nu44e2kRezKCLLSfy71DfoXaOfqkK6O7bmnrkAnTYfQgh2QnyDwjClevC/Fm8q+KtRNBxyK9qKkV4MyA5FAHgabnDMDBP15UuMLA/onBQQYPbZ"
    "Vio0nd9tBf1e0tr8gfXo6L6ZiwLGKGXjD4xRQJQiOU6LGJAYOxBQkIjE1jc5oiiY9PCoDVM2rU5OF9gTR0qDHAwrnDH3Ri8fRc189FY/8iGJIk"
    "+gxIL1HMOfV3iIYcaF11/t+b+9ajvXkbTo12YBpSSGguAf6S4cPxgyENtpYF5FvOZAyQBt1vk8jdKwW7BHQFA+tknsXj+ydsKaRKMaC05aLuzL"
    "ZD2QpCXxBIWqncopsCSrcO3LQZ1s30ULR0YnmoZFXNn0HSjLQXI+Iv2L28c8A1FQTfGrfSiw3TRazYeuH1JPu16MAq0iLcKneuVIxZ959IMgyc"
    "Up7/SeII+vDKCeIqAbuIHohQlK5KD5Nzq8mc60QMFEZDK6qvaRe1TdCaQGUL/9k8IUmi6ElxBCTUudZhCNlgKKe2yF9Z399sWrWq31w/uyTuEp"
    "NBt0flLwNQV+4zKmvEzCklyDwl2oDuYjG8tPLCuOl0G/ghW6eFnQ8eyfEvXGRZXNS6TpaeD+ICJUZ8FXmWdtcb3zasM+4gT9FhlXKpKGNk/K/U"
    "4IsFTvFeDA6NSq4g43ooYcHr88nJCu+s7T0RzLCEwuiMeXDIoOA6YCo/wcRALXUlPCP5Xcc8bU7Nho6tTEMIuGStj0Pl4aA/DIDNoEMCcOqpHU"
    "3B2AyQ6G0MGNFaX2QTzeVWNyVMO4ET/A8jQ7jMoWWeDG8qvJrghTu/RtkQk0PQRjywF1//c3FJ0LOdkTgRJz0ocXIlkE/d/bvEO++Z06CZwHTD"
    "EVGKnzPLI4oopK5DRS4yp66GYNEP1xASVOfSvQmOqVQ2Vu4r5gBjuOg/hDFA6uQ40DofXBn20dc3Mxpk6jsaF2ej+teRfuEfN1pJkzUuwwMMZG"
    "Vn4N7iCPVrWuzLX2yaycciNPQ7+lqbbbNm+uq6TxLBcb2tlHIzrES3FQD7XYcNr/sTPWEOOYniYxTkrd1zauv3YTaE15H4aTXHJSmLkCzvO+hV"
    "eZooXFgz+Bs6hempbjAMx5h4yiHaYJaXH0XeBsg/2fsMSTizyASfhCUXiWtX50zM9ta3YzzU5DWp3GMs6WLIvgffJnWr9OiSn1I06Sl497Tlrx"
    "CKHg9yJzQG9lsDjU4+eaUwl4LV1dCavLaqXXUTiaZmz0vV6uu3viD1TZeOIDDiFJsN+uWrxuZJaIWoyMLxm7/ud3UQruDdJG5HhmAb8Vb+qzID"
    "96Y+uoub3TyV9nShopnfD1ARlzi2Pjb0Mrb1DBKUfiL29j2UEoMQhXLG3g81XKJC5QYIUUqIb7s6o0qeqYnAeXhNABP33CUa3RIt526vHUXk9k"
    "PslGNfYFoqvkAXBR7+IdBURjwUwkJhe7bSOPz85naf/ACSh9JkSyA7HmDB9x245z1vio5RLv6o8O0OXAzPMQ30tTifb4hIH9g7pNCdXp3cVE2M"
    "Y29bBk2+YnxLbGpDv/wuifvsG3yC7JrzkxWfLjHDMJO5EmIYUIPYu7d1aLZQSNtA/n2urQimaTxby93GFMy9EcbRYv1ON7HkWc1U5VNIHVoMgG"
    "BrJZvkc+peDs6P/c05tOSlBYvrvs+LlFEhYoPL46mN36B/wpuBmdRZtHbB86LxV/Hho7sC61Dc1pH1kQONKPbpeY5QPhfhtyfVe+OYyN3D+75N"
    "a+8n3A5voAGy/kRvWb6vtYaK0Zi52aqgpitAT+AQwF/CW19ZPpa+d8UgH4ACiOvIHpMtPYrPbXSLNTrdAeDAkkiDxI9L9DzLjn7xa2JJspDvdf"
    "D6QPQlbLSySi2svC9408gumioRs4sv/NUy191mEwYAni9U9PRgPXFLPhYN9ZZ8LSCy63SBMpbZFsYWz63H897ZxoY6XoxPqASPNZyROlcmrB47"
    "Rf7LW5iMEwVSaCIYmgbkYr1N7SLglUwP8NkhPoxOczcPEDIGfitgsdX1kkQLM9rWeR9NHVv3PFYyQALSxk8rvRSRJlUPzIlJexbOMSNehxOmfV"
    "VY5akjpNceqMWn6CB+mtNeh4KwLdQ7XJNXHFaXhpA0bYfd9MyT3KiqU71t0seuG3Q9cbjLSE+sQvygKTQyMjs0mVMDdvj6CfKrSKXH842lTpuS"
    "T7jNRL1LoXxtjZc6OtTBrKUjmvQ9h8qaKX3/XHKrK7s62GnBRKRnUtgBbSKEP3BPBij1aOl97LfuzBYzlKpuUoDLAG+DOlr8lf62yt+2h7cagF"
    "kZwDU88Kpa1USn/MlRs7ch6PPd9JV7xnhB9Eje6DYIqo9YMB8pzoWJ8+6ZhzPFIVJgyUS7IEItAQAnI5SrMANPqO+8wp2gvFCo1kR3GH9qf3cN"
    "0MpFYzrwGZDNidxjwgMVMJj2S+Nl1/SMLVDBZ/nBhHR9yGbLaMpOeAqE32w4lY0pBAsYZQu9fa4OocuQAXmf7TScXmXsR22kYyRE+9I97GXqlE"
    "bex0IdJUBdCvk9Wo4CwOm046p1eX9JdjVPbwzlp3NAlXE+eZiumImIeRZXK2NY3gxsbgc24c/CmDzB/ezMKCQ6/za3jzz5NNAhZBsZHtt0VF1R"
    "gqJeSIh0vW2X/bt6gLTYWBLtgouvMDIIVS6dBTRFd6vqGza+rcpIU0Tiyu8nEuqiz8QeXLWBZEKLy62RCR+6xAqk7jQR5Iekv2x+VnVdaO9hRp"
    "MBPW787Ug6sgjjxt+mHl3/HGXelkF3VilcTrtVmik0ObYsRhXZvH4gx9HBFCoqK0DF3mSOObv+pjlfBo9V4T3TUDpAiPXLGDXaoakUJLiEZVxK"
    "soR4/nqVnJLc1gTgmCocjaC4ZbWlP7zRbP6NxZ0A6te1WiXslaN3gqP6pHlylr1r+7ab+JEehNp96/84fFNOpM6x8FddieuAoI5rsrBCWDEtHW"
    "Zye1DENJo1E20ox1TePIMHOuy56clnX2tMhAfgIgYCga8Fr8Tz/UBSeR92PAo/tAJSmJB4EwAsfL0yi+oc4HB4upIj2Z4X3BAkFLg3c69CmEGd"
    "8nnLtVMtq3KMtLQbxarCvpE42g5I3G231d4ck39+oVkpwwtuXr7xavcvtx9NHnyYUCd/OFR/i7s6SdQtxUVtiM3BtTOnwt3/ktyAMBvvtxnUUX"
    "bghEhqhxF8ppjpz1hlRfEmFeumzkIrFLfBPM8L2KZN7zGMi0dN5wxUm2O5tgiz2p6q9ux5vGkc3YiZ81OJey9lwSMPvXPOo90Fyubau4+6kogt"
    "OwSlixhobJ3zqzNOhMx2cGlDSU6ex4HqLuO6f0/rfp1D4lRoW+rIje/zulMT4M3q8RCgMsspn4vzyQQfINg+vcQuYS4TjCkF+nzmrIBcMOk+09"
    "qoPhSa3qF+amxWmTCpE5Qq/lrc1/75ieGkYVRVqxYGJl3Vvkb4nS1klB92oY3+N6PPaCCupvrtU6+yBJfV2qcKjTXMJIu0mzB5jplve6/dz6UC"
    "wqicsqVYeqOWwX9b+FWELNrcpycGVQiu9fs6/C8+U+beVGcKJjz+yfoeeYroxPn5w7csK+9iOOnmKrEfJ/gxsXHTFKCZkqiI6BcjQyMCbyOldN"
    "y7w6JO/NPIkm09Tca5ZJHDxA/ruEjjVy0juNS+9TxxtLlYh12zhWVVaHp8qiscP0Y0hPHdh8xUeoQjheJm3U/diyEovcFS255scIl+FbmRXho4"
    "4rRCk+pqp43VU9x7MAKYx/YbfHnBT7ft/H6yVbf50d3XrclJPFE7fUA2FwEc6jQQ+xKVoINZ1IPLWnnIDn5bnGlLftzo3fMl40tWpfhWmFUIXB"
    "ZYB06JKNrKrRHq1AMHOFbo9Dwes4l0SCVoA32k4gLprpjpKGoIJ4iSJGVIH4hHMXY5gw35MZbDvrm73k0Ec+4hDiEqbzBYUIdzuw1GyJMunSvW"
    "vQx6dFu9T7EcI/N/FgAxoihy6G53SpI+9QqCREtBqVy5QaS/g4vzF3AML2LsQBiJ02VtwEUA/fJcpTajynCPsJdC3fc4KsqUaJOrUWlYZJOZxH"
    "S//pvMUy1OhG9VmcG5S1ZKyFIy5SqxMssONEXTxWJs/FG71B31AamjS+KvAqGKwEVEVkO6xEhlrHSxhwb+NcZIw4k1mev/6d7Iog3w0ljsZx21"
    "7cglTQXgcfmnJllLjNlmN5cGfK33ZT8CYxH3P8xlOwiZkf4mthuB1A68Om+i6mBou4qHYbnZqo8EVpu2UQf7n95IXzsVU0Oz8VPJ6U/O+o9+r1"
    "DLcIGK7J27ECndpqI0vP5R/MGN+5wK5W11YmcELPvmdtRDlf0lIJpxD/SOhBZC//5QbPCVBJ310ELoFAgFPLHmtURjVcA0kEGeumgGAIvidxTr"
    "MdK5SFQWcS4BSgUS2HBThUHdgjH0ie2OdODsdqlmZtS/11d7oYR2QWicAz6J6rdIvd4TBTXStMFObZ0l6QtHgrvsSOcunLVdoWcKfS53OGMSVB"
    "IJ7qQ/4CkhjRprPnSttcljcG/RvMxyxr1CKKGZ1ARyVz1d69PD6EH2BN2bqqct+SrUywIZK1rNjxlnEguwH7k+bGK5tpnA9ODhzCOSmd0EmlKv"
    "yXyA38d9Dli6YwupZNPb1ffXNzoRqwlGrrOtoZLMeYthdPO+PB8OZT4BKWhawNPbgYG7++Wj8uMb+2Rntkp4RED3d5GhO6S53EtDzOMqfjlVRt"
    "xUKDYDYf3YEN33t++OGZKdOceQK9WXuJLwxh7t3i5cPvV6wKd5ZtoVVykmi9liCUoFNVaw85Dt205FbzXBOBgA1TBaxD2Ssem28GLwMpchJEJd"
    "UwfbTUDgkWVMQWIekKmsFbYJ3d2v565cxJZWVz0nfmkkr7jogEJ/KVdz856umMa9hBPz1TlhIQaNvKBkxJGq5mNzyUnla12n3CkvPEH+sgTyDN"
    "aH+2iFQfeWInWReMAwcO7AsZcDj1EEhOKYa6pZAT6K1l6PMgejKLrLR9eYcvSJhI+U9NBZn49Ax7W9nxM1hq2YQ9w518BJkY1MjScy4GkbtNa3"
    "cuqKBE3Z1gOXANBT/A0f93ZRXa3KYnNNmN57/jHKA723kiW5KvZACWEt5PNFGhEMOFfUQUzZMK8zFr4W/n+gDwjuRk0IEOon4cXopummczyVaW"
    "RseU0vBQ2/qUGgGrWgWTkpoM0R0v1BTTaMncq5m0GjCY76jlX2ltjf0KRv9YAy7PiHUH9k7i9LFgP/K8m4T+KsHVMWlhYEw3OUSEgFBo2quwmM"
    "mA5vjvtXJhNr9Ii127a57K2EFVoAaX9pQgD8bG8c0R8ADK5J1S+ES5CbAwGL5hfBtgjC/3lm/MAn6jqBlAJX1oahPYpK0FhfqIC2eEYjI//lPO"
    "1exqc07XeBN1LkyJsb+voiAe6M9jLHQ0oPLSjGtnDMy2h628AdkPajceqfqkrM2ylgw+cW9ZNL3bcIjHb0LOLo8iad+Y1UF+d17qCDvBrBxBjz"
    "MeWWCXaW/x8E8+WvpKrs8Jf2R6r3WpSOBLoBbqlsH04dDgK3Qf53psFqRbyUbIQFpv1VwIpNT8nTtuTT4Ujj8ERKZ0I2XFK5wyo+ozRH0Hvq5e"
    "ur/FgZeA1vAD/6Or/w4o0sIkW+08cziiWAFXnf3SXVEFXKWVfahFhbTAQedySO6+hMBtNN6WnODfi/8DCByzb2385FM17ya5uHpeTM7iQxMY/O"
    "uUktMDVwCMe16UHTXr7slrWp6l+zmtDjF1Y9Z1FB/QVhOBgRwQBkSSPUkDemK9PVfqvmjNB1f45e4zOX/Y8IKEfrD5BY/7MYiFJFS+6llCCA/k"
    "CfTHWM776fzybDqlPYKpqFJl4AmpDc5NyeA4ysWf/xbsGOf3pXAuLi5pT0VUkyYdcunjWg67NBmoSZV9spChAM+Q9KqZVnK4REyoHyimTV3twN"
    "Cedpmew6JB/fsb6GAhOXvNsGENLpMT7dpe7KfdP771qrvcERWY8IK+jignQJUXlwZxPJKQtU6vU3ZpWInlwuKkBcRSDHVspPhJWRClhyTFDBKa"
    "R5XIdS85zefRJHWLQhxamd/bSoyvxFJCi0clbIcoQMhskla7IR/M6XizAypB6fvlTcSnLqylnSvh2lsyqliYqPoPucvji/xvIfD9bem19+80kk"
    "gBBRVokepEGMVlZ6ak54t/u4UYGiJgh1cH+GKe4T0g8Fy2tXFaECAMpeJoRs7EgT5aIozLD3WnNYvEqEJ+6oMN/VXKcuJbROwv2EU1Z24hIKrq"
    "D+m0+saaEehXS9ObhHbnN3K6LNEpKIL2Rz1GVJGASovyLGYCIumJiN04AR8iZOnllVc1PcFD/eb22O+qNg0KYaDgEJs2QLK584cXNaGrk1LG08"
    "KcL5T2p+OBdotP38NRM/krKKhUdF/MYG+otfi0H3mTcVM9VE9MIjo4g28bQHSIqMNQIcrY7Fkr8rCmvne13VNxwcnUQJw1Qj9UsHlznJtulR+Q"
    "d6iHRnTTw9d22Qnhc4C2YDlXJQ/8b9HTLxT1YK6UBfa7eVJPOwhVVNFjqquNNBjdPCXsTjKOZ5n7nKIDoLBaZUAvTHJlDmLFD4442N+Fqpn/HP"
    "VV8DEKXuxCuGZQq9bR3TPHj+U9wUOeNvOCW8QjmOQphyDOMgka/fkBFUBXA8W9wgFe2+HqnjuMlkbf6U8AlNrdEG4ExwiN6udQtlKBhJn4nUFu"
    "q/oJQPzflb6hiAlYGE0/cvHBCgmObrjmyIVvoKSaL7GpcG/53LljHxB8EYn8soq415VLk6fVp/i7RIaGwRw1cv8aRNDJPFH4nnM/t2PmW6dSE+"
    "kWtKSimqsq3CUhZddIeGlM4gqqet2A/HkmsoLPbciz1HpfVt6ANENmwOvmh9YlM8tI8tMaK5ZpEVHiawjFH0fYsfc2o0WPBAT+oZTzlcm0WzTS"
    "2Ay2ncV8B2pvHtOTjDn8KPsIFskEr16bVPf1/D+m7G/uaumbpDqMuWZq8jfMGnWnnbUYuLuMsMlI4trEidkEDdMIsvijL6GxToGzzvEzyreSiT"
    "GhiqU9SgllpGfz/8ff30nfo3hDuBm5yHxEq0TbfYM4Es3wLBLusGWqYz+4svQBrp/jrj2t/+Ee8gKyNwIVkAk8aZUSkEAoXzAtdnGPx5YjWTZ4"
    "fn5YC6N91fPTf1yckflxHjje3qIEFtwKUmWNiB7Iz20sftw6ad5Acme9jOciQiKivuJt8XPxZ4sEe2aFH4Y+cVb49YZ8GxbvRG+blck+VkYCcp"
    "NykztobeynGdNzKsH5q1ps6RaT0OyGrar1/nw1w09M2A3yudXtb3spYGRpGJrcdAFO8+JLAsAV7VAjwbVaXKkDxS0VglInR+yfsO9SR4lQJjNE"
    "U19nGIKxHGyw3VwLcPSUm+XHvbn8fz7cajiYAHGl2TZI3ZEmXQ9rRQpawZPNjlG0hweIseE4nl/5eGFbAoflCquTooFga06F5utYmZ6pR2fsBQ"
    "/0tB1+/tBZP3vg4yt0hw6fuL+Gp1OfnVg7+3KCd5akoC7/KIpHYB7noCHOLSAwbm4Wmu8zzIORdTNz5OySvSavTR7NEQjN+ST3JcDNHlkG5QUm"
    "FArIuL3BvPBD7eRrZyNqdwpWEoxgEIGH7ik6MXG3i60AbN+h9VIj5ucjOnsnwCkkZAI9/IBOyOQVt2DKMgEtr9Xca+skwuQK20TIsiRZeiBeN7"
    "dDhahQs/B2hOc5xfWJtB/SM0M6cLrVGeDVqyr0VJ7nuB2CbdN6wsbj1L66EzJ32leZ8RUfU1QyoJVMbgaK0rY/q1nTbGOwPJvxgq6gggvtPeW0"
    "bWfN6rIgOLI3EcND6aMZAEz2IhC9XcsyxKm5NIcyW8DCsWWYOgUoofQ/h0vU5IiptTzdgxmpW/f2xVVOSAdMgGoDVbqSbmUJ53NXu7644UX/C1"
    "/p+ztOD3dlQG6uEqoixpC5RAol70aFIAxhAFd9QDWt39VvzND5PFMRepV+u5ORIvUvGzEkVcifBR52QTH90N5cxtRCr46EM5T+/YyQ69rcPn29"
    "H9nbPEdPC3brZUL3LvqIeTc5FvdbTrHKg748hE+noXVr90Rz2yFYO4WLVDy6hIoIyrQISOcePvBIvYy90sPEwudj1fNE0TXgoFAbJIRWYo2PYk"
    "LvE6SQSZanaiFXNs8L1jmFMmMPXwzmUbIl3sGUIQb3Q9LNvYOGGBOoL2jmsVw3S0OtABj5nfE81bninWIkFhyXv2p7NQ2WdY1r2oOF2m4wcjRU"
    "eI3fmlNzkodDZrZgl/Y+hr0AGsswn+MlQJ/gtoFbFBndVuLvOweKvLJjNjmdAU2LBf9UExK/xFeq5JrHDkHi8RE0m0gRb+bVVMhbICBzJgeeFu"
    "xsMvtDSxovCYo++zROfqNXwjudXtDBD8rUZ1x9NZUJJsmYvKFw837b/PARsvfQCtaNsXLtxR3ztoy+nFTmvm39IoGK5NKs/dPgjhgjNAZzIUyt"
    "gmruTps0aJJmbQdGs2sGsqpAiagpKKslqcw9i6Ho6w1YkAlPK6kqiw2A2QpbXYO6RA2SpwTvlWKQlNrAQw6V8bx163hde097qLEE/QRlQ910sx"
    "bp6Q+LurdDqqsLGbvy5eEe+E8UEAC/fnuQ4h5a4qUpNDR6ZWGCNguqy/6eUQ5SyBQ1RNRggm7b0EALprJOqmRn2tktR8miAA79OAlmiBamPaeM"
    "vS7Rjyi4Nhkf1yWEeqOjRPB//Pq9KSdFn78HJGeCkFyhZ856cDTeFUY26HdwkpEWzZI7rwDloGq3ZJ/SXWTMWJ9Bkbd3RqAluz3WpgDU3uXHU7"
    "i3CP/3hx9I/ba/d6gFbUDbibaon+6/bCALfWGG0KR9axo2lTzhuFqihK9TQSuzkvXVyJPLkCXDW8LSUoiTC7Q5guKUu6gU5cir6pIYHAd+hkmy"
    "6S7vDZn0epwHbCB2OaXaEFL+/VEgD9Nqk2lVc3OQYevgFRCt05BKy9MmZ2Exv0XBP1ZB1kWJuu15I4WFdq6tq5bC5DUEPH1Xyh6mAVVXXqXuo0"
    "CwbHY0hMpLpOQMc1fXkT2SqdMWgYuCBXbZP9LJ2nBgpnu4v/LoA67LP/zp1yl0Eo3jyEPfsnkhY85rqUpW7ZV/lDgbWBmvFN4rak9KwH0TLPUk"
    "L/9MP8UOTWtbBcpo5QTjpKqNhpDoGxGDB0ORkXdVZslz8nTl2QVcK06feWPA6LtTIOLIo7Ku1T6w4m5ViGJujFvfaVz8TqzIm8PXEFU2El2zvy"
    "sgM1J2Wzixl51p6IYWZTPktRUW8aVv43mVKUqYWVL+Kg+dD428sTh7lnwGAWNJyzjNNhYZAyssh/56TuwCK3rjIPyV2uw3FNp3TJzgq/xheZ83"
    "K82JwMIvO7juq9vazACFh/nTfS2qlyLHajEfzxjbGjD60/ewTKWTCHDox9TBNsf74R32LAAnFAgprNlWwoZ4WkD229FtDmeZLAhrzNTaqi2gMa"
    "mgIb7cpqtEXaaATkl5YDMXvTRG/MM20pyVhfev10BvJAmYWkGn8yBUtYe1VaQEjX4FrekODGuCdwrgG9GCvceR0Pt/7KUyMVSZkU7BxJLDnQTF"
    "gNS2PexKUEerOAO1VMtIiiAMmqgdEAsE5B/gTfKTx42+OB3Jtcyp188302VM32LaVzfxvMFzl7SDCIjHjtvuHrJsN73bSQv0Lc3khTeSLcimAF"
    "JMUUerUouLtCrEQ/2gdh6IYbmjt16Wr+uqlxz9cVv79IIPRi7qbe5fdAqLOc85FIlK/o3r0BAUxGnLjgvTQjdexo4s9EsWBzrKGS5zw3yE/9nE"
    "+LTHWPEkKfoMZzr/ZMrpqwFnwPtceQH6LzwYyNEvkxyGiSCLnmqMs0CNAvCxYdJyoGQLuuscz/AMXs4pnyBYLkL8GT6UMdRfhcasRsIbMOOlo5"
    "uRTkcx5mwRHKR2YHAHzyAbEVlAv70MfLqpjrIJF4sdUR3A02aYuN2sYj7UY9TDnI3AmRWf03aGTaeGUXzwvl7V+ZFqw9u8zPqKfXnDRwCcw1HD"
    "yrMf55Q3oQmpjr7o/BfDJ+w+xn7lfUyMYHBwZI9ODB27aG0LCajpMiex54uuVoPcPFnADLzxVpoSFrXSqWtln6XBKUu1KDz+p+6xUNwXTqTtZL"
    "VoID82OtJUCYwJqIyw7FYuspiGaPQe0jW1p71YL98yQMihwb2c98YAUjs0NH64vSWooJvDY39RnE0luNjm4kTdPCB0l8Vh5Fe4XPhRTMczJEII"
    "0o8gBRpSPfMEWr/smaqM9Ftxenn72h/0V9qClNzqy14AStWrOotKIe6wCnx+G1TlOrleZ6KdLpxa4ajXIMb6CbYeyhxCt5QWYkB45mFVkMH2oq"
    "Wy+azT/cMxTCBaucm1zE/3P9Wf8RXKqiq0z7Ju64ystHEp0IPwE6coHBc5yNCVFNgkngVEgwzfbImLf0fyj1ZRpX7JY77l7j/DjhiCDLrHWGGS"
    "CSa3cBIPigLiFudXjroooL1pDuaHZ/6s8WRJW/GQwT0VsNq5fEplFnkKdDxeTKCOLCWtV+X6gbJqC0EOVhISIBreF/LCdAdzWz73IltjH8nHld"
    "yNsKK1lcjWC/ZqTJU7bIuqeKxXQ4olNyD6+Mflyh4Ux0Fc4bhQKRLP7BtZXx+l9hZwS5a5t0xEqpavH4pY0lyH8VamBqgcadhBSwBep0znzDej"
    "T4uoHBBQsEGoEEtxNwDndzj7rdaouv2tED3tI6O1lmatqmmdU9VS7Wkn5+3OtEmWECC+5yr1sBPf+3biVNJXBW+MbRouD3dnGa8nshCaClmvMV"
    "LxRZaLXf+ZWBB9piBMWkzfzNAyGPV4xNOICxrIWfy2dOX0iDHBNhQBdJKKVNBgWyczttU2/m+f/MjkXfKFKR4AgrMMVCeJFUwjVKZSCihp7SyW"
    "sAUGQb3VUZUa2Vez8H11nvk4ddMxVhXfhibH9vEKNWJE53Fip9XqnfDrBCWyh0nXz+MiDCeh6T4qxWC4zbBKhuj3Ixi7dwLxK7GHed0eD1DmJS"
    "JbAUxLqRRzbNNWl9Hi+c6SYXY2/n2NMKSCR4wtjs797/G2bfMFPjrCKxDAjf5WvoRyt4/bHsT0NxOnR82cbqGpdzNeWJcCTfyQHthhNMD2JMhJ"
    "62Awmk/GHlpJ2klJVAuJlhdbR1mnbBGmQcRofs2HfamduG/WWkPc28CZlOY8OMSqUV2hrVOmbTpnt5LDJVHHmxczvRiuHR3ZoJMfXVnti52ntB"
    "vD85TExyYQxw+6BraGy98HBoWVMOZNUNbVVmsb4IT2bc3f5Ri4NxBfpVZz6nhvxUUjAGbXZ7M7TzZIuwSsPKf0l8Y2IT5J3As3eN3KNRwLXHAr"
    "j596jNLEz9pxgm7BR6chK6vdn0sYrBGpaN3lN1wM/+vM3g0tJTmKU/O/OMYCu+4kERgCDDqJTlfkNf2B2bFbQB2/sfm7lELJAGmDle0ha+c1Eg"
    "hT5gPK5hkKU1Lb6AJrHK2H0cx/t71Uf+DLJpl02C8N3DiqwFflo/J+I2UVfSEMizQbjNJtkPV7jhg1yNnJpXbgbRKc4nhLfX7gTkyQBVvbEOw/"
    "Alqsn4Tk6Sou+EHh0TFWhfmPvykyvDdUuXxXZTQxJpwwCg8+IsQndPBZ9fCRjelYyKUV2doXsQp4wpWnV6EnSoUxnvfFRn4Q0nJdJ/jBKrr9yI"
    "dhyrYx6ENS7gIOVGi9bKQvpwLRCsUg6UPve+L5tfbEHN37RYKgqNFpno+CdHAxSX8ziC11rKXSfwa4Rv4lKee2Lv+pWTbGCHL4JPVzhV1LJWCK"
    "S/0LBNPyBM6gxkq0UOfMOsNEKQwCFhvwd7Prsb1aaV+CNxuTaqum8zBJQvfASmaqVzJ/CH/42qBV2Kh4eOx8M9Olc2XpdrolsZjYCe0Lw843Y2"
    "hFftjo4IXTaDCzrQRpV0tpcRoYHDbSgVg9YoQuFtxgRuxojKrztsFI0M/7Ya0ttfgf9Vs3HEDnwNidnFWQDf9mloCmI6lvfQKiExRvxNbcv1c3"
    "VznMq0wYXk+a/A1YkgdV/cn75PXdeTz0Pq1e9V0jk3IdpMo/rvunuCPPP2f3X88Yr1+IxrkiI2+YBReYQugAG2akBuS4BbS/gJ9QCB6HzUdbfj"
    "MruVkMHt5Sk5gLDdw06THMtv93AMmg1KjthLsizHt9/SiummyCo89AAt5npGTZeh/h3KNFvCaNIF/5XMmu8+aXapfXyviuMSevnxyxkKAWGfos"
    "xx4Jb75APV6epWSaocUVTikHJuLDIZUoWU7fkFU+DUCCrCpSyTzymfZ7fVz4j52pQIo5Yjc+/kwKgKsqpK769uuBvVXW1jRF30kRR34RHWt4tZ"
    "OM3rphJ1EnVKlAY12yiWEcCcyAi7ve59cTlh0gOarS9B1vIF1fsr3q+mZteYIS81VeDLREpbriG5upMs0sIqPplprSXt35/1e5W7VPdi/avnri"
    "BxDxqRuCPyJmrGPoY2+z/PT0NeTmNzDdxa/pj7Yd3gYap95KrSoUN7GZrvb1mhSJTvonAHfXf1gMBCDNUczDCMpewbG0mfQyeNIiRBtIwdr2T9"
    "fViebYGiwN3qXhgcaQhlYTaOV6FPEmqrYeJp3D1usGyaOgLNPtdiFlCIAb62WNpCzcsAYVwoiu/UAmcgEJDN6LoT0ov7xjjJpdod4GJp1b7edm"
    "a3QhWrsV9swfsrUOlRZcHJmQLkIz2tRgjd2t94wfG1IAYVPrMyKmcWNe5Y+F+oazQGekbcZ34qSAW70IfPHqFNhWt1ib0fCBlfzgjhuSCzY6wS"
    "2ar4aW6xZLFboJrIhmz2pkDC0ZTKrbLGh0PWy8/QqiH/b/dK6dcZ0HhHBuFQNu7+iyz3FI1jRQsNXTmMlAZZLCdlNBvln1Zg54jtWKkYD/PEm+"
    "+YiMfkKuYRxSi06MXGLYULTJ9I+F5mlmO56aira0ahjHzcd0V7HmBvJGOVa4XkTAsUKF8g9duE9QDhvjTHS68zI4BaR/SZLUG/jkAYO4CaVM6F"
    "UiA8/BrE22n7Suq3fJsd+2ffcXtX5lfoRD3rVWyQ81ZJJE/bbQN6rRBOKmbD8abbK3UoP+feoWPuZ1g/GFEFDNW7TJKKmApIYQJsb+cyhqmviY"
    "QzwtZJXmNi0DLWnGwYuJYkGhL4VitaJsACpiOE70duqdDA7UG+Zg8xH/N0EnIe6E2efMDdJ0ERAuY2IcOwFOt6OExueQhWkpNyON8X+ct9zf1+"
    "BRR0jQgxK5hkSNS2540kJUjhbPqc9L1OC4fp1yIkPYHvOucBvOpVLL5rapnYDz1x+i9EqXEM/ikXIApwXkHUxG3TsUTW+UTrX6Fi95wLo7eaLs"
    "ngFR9FUEV5r58yAjcf1oel+LYOE1ZZMSwE8TxonA/J7iTbcCf/Q2i9cAYdxlY5ZKU+KXtPQeOwgd0kvDZZ87IRSQ3kvYDk4pc4lkis2FZzN73N"
    "VyDZ/4ay4FvDqEFtyhRirW+d4GKFSWajA6atHfxBG8Cjr5ptOJAeCjH1cXQe1DOmtpC8nnfqWWWwUDLTSNg1xMtWLhmHTjzEZUuFgBSK/DoH9f"
    "m7sqoy72mK84MVFWZPo766aUZVuiV1tXPYzZKEU0VHE+pUCQUTHxLciRKRPEnJ2lhd5lq523uTts0TXKU0tbU5yrhLPD5IP7LOSKjRvU3/7e1p"
    "c2I0LmkaEGW5IfxBXfOhTGof+GpaaJ4MYqPyOkJB8FvBIybyi9KA1fg1XkzHS//3zSLR5eDyjnrAAxmAGYRu6huhXfFBS0Dp16CpM9+zvZo6JM"
    "gKUaBfDdDuHNslTS4DCOMwMzi+TR6waBYOw7S0vY1p3Pj+79fa/8xjiCAf/Cc9jzu3ItmqSqiIN93nEROFd2V+W6v2kZ3BnrpKWtT7FC9SROfR"
    "49MLnhGjj3/rekfdULFsOyoEmtil3Wi/YxuoET0TssPpR46XNA6lwTpZo5pC4+2pNH4SesyF7qf2j/lIVN9LSocLI5ElBgrF8tMZFGbo2BXkQF"
    "2m94w5rgPwTcb/GId5kgeZZ6tZevJxQ4RZJ1QikXuJxigqgiCCraNmqJFHtBNt3vgf/OPYbN0brfeLYPJmOSDuSsZuscA3IuBMGtsvLQFI6bLQ"
    "EaEk27U1HOFo5sSBC6Wigl3/Bey5LXqnrRJWZOCSQRzxzpjsEGyZ/4UdpoFLJKVEmI48n3R8gG77EgEvIa48yHSpdEQ8ls1nTshbxgqUQjpZh6"
    "Ca+3urpzKmJSl/WCZHw83gByVl4p2pVzRUX0+wMJ9LtMGrHY4GNYJAocxkdMYJIMF99K64ObENDjlAyR4hfcMJD6A/Ba6DUzrKwTCWWGlgrWT+"
    "l3rgu9zsJtcF9nIIWbyE2mcD+Kas+Ou+05EAGilbrXqGKJLdm649ZA8K7l1w90+DED7mXmoiSGWfsZqO7d2SdSDc4UrXdHcz/PQBU0eWwJkDOW"
    "eYV6Si3S2A2HeTJzJjMnKOaS8YNnWEa9qJ0taswjMW8hVHoGLa+bQ5tV4ALaKUsRESMtvU9RCN2zchaK7huO5aUu/pg099Bk38JWtMvRV0kOBE"
    "OQ+gztQrai0ZGgzp3T0ngTY/7Kcpo3YzSumtmnMcW2VabFdnXt7jY+EMX1IWJRSIutRxNIq6+fPYE9eoQ0qld0gDKoKo0xFlt6QShiDSdLUFIU"
    "oDCQe4Xzix+QGiKALM+QJUYSIWmnM27uC6Lvduvjwj/m6oTimQacp/eV8GJnJrY1nxgIMra4QoLm2l6ZV3LuwFFz8rUXtUzuxdbBHQjsoeQ/st"
    "gsRd1G0NolPsei0H/x/MEsybiYOIhd4zuRf9yh4mqaxrhX8jGFmbntP2nYHuBmFdmZAnNupFJaItE7juYu+2mdd40byRDl36MDs0Hvn8JjspKx"
    "TlScPLTBUKQ2ZII9REMEDFZmg+OPdzfEHZs5Bg8OgcuwiEXv3gGBOAA6fMTDrHgoQOAWshHLSWfGw6kL8FOyC9DKyXdHqTMqI1UihXEggOLLXd"
    "ylncqqFxFn20HQpkEOX5dKaYUAQQ9taw+FOy+5OJY8UyPy8pT+Toc7sLc4ERxESDBJrN1tGmwOkskyz2EZwpeMhjrDiKNWdegG3uVqPu00Sdjl"
    "Vp40wCzJqvT/fnOGc4VyahAoBU+na8y0WdMeKxRNzjfdx4jkFCmSdFVEfCsb1jz3wP/q6QMbCisg7I0ky5nooXii3G26XdBtXk/AK3mNTvGhxO"
    "UXuCLN0hDUOiIPz2Oo6leawEi7rYozO/XEfYFQRJKTHGivCf1HsIF5yljGwWcg4tPUIIS8qL3iTVi9AkfJBdCT3beBak0G62qSLxl4fDqHHIwv"
    "7ZFztzn8e9mJ/RfrNBP0px6SknoPd6vOfgxqPJmTeUi5FSK0YEAyO9AvkAU1cme+6Y/1zlRdHjuuWeTFsa4s7U2f1n5pPhA6HssVzKtuqMukux"
    "cp1dpZ3acyRzhgTleDxKGgBuggj1385ndceCHCjPDQD5DUdOarBun5nsINmdFvBK4nbI/Qu5GqXdxZjVBccDv4cZnYCebZ826dEK1qw7/SAEbW"
    "WZX6cjJi+CLpT7cT5vBvxunkM8BFrd9TioNepIPVauoj62Pj0a4oI39i8+aWTTAP/y28EMpMjAy23kW4yrZ+t3MeomSZBdwJfikfoazEw328Lt"
    "kA2hetan0HkXt/LV3iRhScF48wLZ4RQrx2UW9hv/n2a1JCytAkyPcxF9ofjU2Wmq7QPpwZHm3Mr+4Ak1SsiJIXHEMoZLu8fMVsgC1oYw6o1cuG"
    "GKB2KKS1oH28uWnz3W1zYUQ6Z0TzF3iZ3ZW4xhaTxPYltjH1PHOHsEbxGZkk8bXyxtifbhzKx0VqDt3MAf4g4J98kqdGU+DO8JOJJMNJmYnBWG"
    "pN4bhGtkHMWZsroFlb42RFoUkRi0D5JuwnXVUldRcgWwsZ+rhXLor64C9KqnMEh+t1Bzq12gTdp24q2Jebs/PhjGRbmq4WYdQpEEWo4IFxsitY"
    "r694vwcsF6mMUlzU66cOrmf0RkqQAT7nyehneft3ykWhNbmJNwYy6+zbZjtuFEtUydIpgiyhZ9ktif4bbDkriW0o6I7jRKzmzQprw22W9ny3yK"
    "jOpAYrVMG51NSmAXyty37oaxdQv7vw6Cf12nl6WgkZ+ilWQdxxnfFNrEe4rPR+e0MI/4UldiV4KXkwT6Lzv+UUlfsP7tCylVsss80THqGJsQAy"
    "HTGUZyVErahawpbDLlj/FQHS8gYPirdqTLv42PquL38koisZ3bWa0AkuYSKHp9R5ipmbKfutzYs9YpcCvHn/YNZB2wSUSCek9DuXAPBRibmmgw"
    "BY06OUScF5t8KKupQWEVgeh9G6M079/fUjiN/WWYg5CkgJf1pzNnSUIFn+CiuGhIDIieHomrIDhDpiKK6FhT7DTdfMnnBYG0AUMDeJ+Q/R25Rl"
    "Jb+XPAGEzIpIoVyMKt9ptEMapcYzLTsonMgMai0xAftXQpf9ENnppXrAN9wGnlzb6BvADiV4a8lq0qtSlpyHi6ek1sLynevY79xSN/AOl1jIrM"
    "WP6BbHKEY5XnusaNY/nGAiNN9NcghsEPt/s8zmH6IcSkT1uieHEMQaEducsjZ4mkKC6Jfe2QCaWzlDIRKaSvppSIIci4FJp1AJleHuRJUfcKp5"
    "6Siyhtxn4ZxGMI3kVSJMvZKIesyhkekvQ2vM2CBgfvnppNfq4y1wqVSE5/yUApQX2ZTFu5T32E2BVOD9h/DEY9JNl9WC+nufzhK9TWCYp/+wNb"
    "+3aEYi3LgNXNoFvbjscA4BrggYiujI2VYnbMsgJModTfLYW9ALGoZzCtBMgQmHUZpkdhDb2wYQ1Qabu3na3o4AgmbG+z2xyPpG8lF2AC3DK0cl"
    "XIHyCYBWAzUjj2ZSlSJkUvDoqKoKdygVZ7ei1Da//H6w0vXaThzv2P1dEdPcoi+AnLPH95Oaza6fTB3rMnqyC4KyN3eKD7xFG1DRXlD0PONCzc"
    "qkeEukEXO8u0Ef2MTQwaTCIb8dkCEBJamyaB+5zbvRgWJpnBMKJ5lIIQ1VKGbSSC3lXtHS5+jpcPS+UdujMRoPzYm1bRfZ7TasDONO2lxP833L"
    "+/9vFfck8JaWBg3NVn0r1vgM5IiP+RTsh1CCqNEcdqcqYlRfJgVtRUCu5fwVvDPl2EWwgy3TfuyumwQtJlzs1XUQvtw2LyNHWEsp7+O+2rZOnP"
    "Kjt7byFJ4g1q6m1RMyPUsGvAIynHOdqWGqwiX/cVT1dVetJ7JZrp4qt7m3Tndtt8debUEYp3yNhhoal4MZNcvpVM5YUo73hKmAve1oovpGFxS5"
    "JAHWNsBqli6rE4qkmMlcjpAF5qUQZVquEM4yvdIS79aStrPX/zO3Stwk7t5oEc8QTFvJ1/r8gTx3DMLr0ZrJJYR1EEARxzJwxWfGQWkhAAf2TI"
    "S3gTaZbSdBTCyd8MYpK7hJ5+Y618QvxcxsBu+gzcikJW5bm65HM4Fx0CXUYFlHj2EJon/H+m4Tj08ZSh2eyobPmCRuPPmwCWeE2knKpeZep+8u"
    "aItAsyqbVD725FYyw4akVaje4fsnwPnqpIfAF19LYu+m0QHS134Y0cAhaoJ/VTKzLrPin1WygR6b3Nb3K0QMi4uuWw+PPD2ZIq7DXDPVbpULVY"
    "MOXEJlrZ3mJMJOXeRuSsY96sunMg+39bQtR86N2nCLPUWwWhs9BsLcPnhux9XEgLCn/IaQR5m0B3qNqCROq8+WFOQFuOLdLSCHzIjcqshqyU/P"
    "Vkw93KXBpUwPhw9aN6RJuN6xyJQ4DchLVrqI94EsUsNPryrsD7wC4NXsInFttXjbU9JKsOvZYLL2RhMlJVZQIHTmcO6znZpVTquw4xJMjcG73/"
    "7l9dctDoswajMiYnLcMqRzYkZUnTpg66E5LTIzqvZ/YX/MttveNyDzCeiiNe/xThvwjQLcmDQjKqyfiL5eAuxsl8+6giF5oeLLwxSxX9UDbJLG"
    "rzJPQV/+jpBbLvcA0leDvEowU12198R8guKCxu+9xvntfxjHJhqy88n9quWhwf2sr72eA4kpRAhDWwCaAj6rCFCg/bKV9WHnHoiBW5aQ9Vm29k"
    "b5LYtItqRS5XqHCoG9as3c5TBh41bwihfserzzgAIPQtBgOqTuIRU1gosaz7TO8Yu1tyJL/huYbXg64H+wUJ1Db57rllYg3hAQCDkvABVq6jVE"
    "Zzy9u7goiPGlIp9XkZ/83w0HH+2hY9CbMchd1Vthew47+XCsGRU++7SlEJ3rC6WR39U9hF24z8AniuPlG8/A/FIiMCOYuzZGdsY3YZx8Ma6kgn"
    "0ViX2nY4ulRUvNmOBfcuJRrJSB2VTQyCQxztEV0Hxa9RRDNjOhL7GqrKpYdKIu5xpBbHduYr8fubRjYXAwLpYvhxNvPZ/AefvAeFcz5F5LcpSo"
    "oc0L1t83XbuCwi3gI9ltg/p5uCfGuwjCpJV1eIjgcOvaKxMfuODQ94/tN90fnI29ldoU7v7DofGWnpp3M3NRO2jaXc37v9Flc2acmdsKFtYLDi"
    "7nKbaT8/JdEMubbiEBhuzYB0X1KAbHijz7uIGbVH0Cr2hwqiAYru2gpZ9KQnihbZzqATnvFkHvcgoHYz4Xiaq7oh1LII4sd4zSd3jXjhCyc4bt"
    "HSmnIK0/pz34/5tNHU4aX3uIezpqhQ5NnSFFQGm8awwxPh/RTLHx/U3ojd8K0FzERNdhXwQ1gNUJhlNTFXvGegRM/cRmFE1wQ1JCYkROt2hbKM"
    "JBzATmCnBi+iUoJtJVFZwEPDB+9SRgXoV4RwkfZNqTedHpp6Y+c7VaJ2gwUKEWG3q2Hyc2VukZ2Ks53cauLj+oaL2pn5IPQbO7VDzkxgjUL/DR"
    "4Qat+4CayuO6XsVMjF46Smn1JfoZ/XWb8bPDQc78i7xfg3pqw/e7OTsXrI76yQdsHUxMSPQzs8VrsQyJIhFalCnSdwaOieH5CDBymCOLdN9lrg"
    "6JWt+eUIJLemXnArn3EMfeiKGtkh8hdIUoZGQrtvIOVLb7ER4RmICSFLBnzcmIST9xTVS9wFHA29f2XIXwMxfSYl5z7l4s+bqR3jSSzjPigG/n"
    "PofZi37kRODP2fiYTyV9KDoMHlWIwjJnqTjDb/AuPUv8Vt+n0Dj0sy0roKkmz002MChheTvsKcTx/jb6mBaMCISl4Ao4/6H/lFtti6NRLbqO3I"
    "ClkDbWOOeP62H56O/dEgoeFfWBY9emQlPrOQcoUtivGV1dzjYq1NhDaZmMOpJPac4sJ3vdvt9ESVc3iktzf1rZ+/3ep0pLIe3pgD+s07XpNEXL"
    "P4DFWjUd0+lK+wUMeJarFunrBvw2NJS1IQ8A17+zcr4BYJWg4vTgslo/tZHziRk1K9Crxqnb3L5/W3DNwYEE3I6i72Bb9JREHWl8EvPqkMJ2ep"
    "iavbpBiCHuZXRBzL1uxuuIrel8gxwVGZbj3od+95bu9z+TZvhfA8IOwWOd51loXTSXXpbPS+3K+S33K1euwPnCKSHbD5gxNIz8rKcSQMDO5tDA"
    "4vbKysgBAv/uFdBcV5uK64I29NIO/rZkKASChbUaXXqlUNYq0SNayVeYg1xfmHPgMrzzQPDPEls+8Z/sHc6X57TzfxCfFw+E/a7BFXz827InmK"
    "wbgYs8nlm/iDQbzNwCq4nY7bT9T3YPENhTgZ7S9oCSXvcVEHPbAL+9kHEysU0dPqPhOMEZ6yVf+07qwBROWiyAhcF3qIBQFKNQBkps9zl8QHRH"
    "QSMtnJ/isMlfL+FTh5BtrRZas72P134REtgNiRm4A9w8mqcGQEYG1+AFdGIPUaSZjIqWfGCCZS75Dqmmd9g8EpJmGFzg/sFzzn99d3vvj4OUEn"
    "UMqn/CmPLW4ekQ6zvXgAET0a5WTqNB/sPoqpBcXXvnb89w+FUziv0BS/+wBak+JoR+osDe2M+d9UHDBZoy1GmnWzvGa96Ck7JEauhB8UqO0oue"
    "xZNgVFk9wuBjnd0tjzVG6Khy1IV+5EOof1HCj4tgtLjrKI2qVrC6CB/Srl/kpTqmkocdGH5eOJd1qEn26lX5rP33ybrKbNzlD9dUmFLosLgRgs"
    "Mjq/tz9Kb2ScDw06IO61FL9EaHse8R+nYUKj1/dwpFJgNTXtI0DvPc3ursocGFaLjFZflImH5WYVwe2d11tm7c3ujZSwEHDpCTZarjbnXhUGwz"
    "/8x/3Y2QFgCKPv7T0swMgPgs/la+CdTd1JOk9jZbEKbOk4CPOEQWp7S6g79DSHb0kgEMXXzzMk4786vKH2utWu9pS2JdbdDa0+O0uX8icAwAhl"
    "SuTu71rz2rf0T2rJ5M2g9m0j372VzWXX7SZUgUZzcXmXropmxvIxFVmWNaOHehmMaHlF6qkfYBuI1QFxgXatogih1zccerc8QXg21U5Vfq49dJ"
    "C5BpWlcPxlHhA61hrZmPW/l9M5pbmPOV+74HuujGNDTnVw9yi7DSIjIq3N5mMX5QQWhg/8duqI7uorWYuPrdNm1W3UO4AdP4JmciaTnVtZzkeq"
    "+bZb9J/ex3et825o8DnvWHIoA1KHgVpchDFsRUIy96tsOAV/2huAwPAd+lfLDSvxf3mKxotcDia624cVLbSKmrLv4SQJSJD7ewXKg2l0ckMbiI"
    "dGHA3WRPr3bNfsPabbShGgdATPn3p9FgpH5StElmDF0QnF6zKoP1HH8g+gZ8ABv1lVT/3kq67cKWl5TqJ3imSPJc1qeWuG+72EWYepB9RwApW9"
    "1JKRWJmvoNOek45tfPmlqPS0IyFiYEHUrRQReqJz5jE32vr3jtv8sWLsRxEhQzADEPcYDaEH5NehTtzWhqGiu3SglQ75bE+aPwHXV6kZW7NCgP"
    "KHJIJaiVLqRu3SF6hxLAQyD3n+xpjp1s7p8lTDo92UtxuOrUm9tov8flCjgGVr0kiidJfJb38xV9gN/dVeVF37WZnIjIpxJuIi+Wbwct230BXc"
    "T8CGmyhBy4q2F6qzfZRsaiCx7klOW1xihyVfmeQu97utmwHkNaSqySAktXu4wOMx3+ZxiqIdqn7dCkXZ/pTL88nQrStmY/Hb0VFgokd/htyVKd"
    "vIoyxICLW8nudJCEd9xD6aIfSdjKOa6Wlt4U8lnidKnS7P0u5N0sBRq9iQHvlLYBVNqCQaDajjntnE2ufAJ3UqfjAxVdqqYroki3phsZBBSXUg"
    "rFx49au+pTHtZY+KTh2yz5N3ufRKSK9xWgD6WJv26y1dGU3bFr5fYzprqn7GYeizwmIQRrPm65S1dNXizD07YG8k8To0JR3RJpjELwYXmfjAGD"
    "vRXsrTjQs3UEqD6sFBpg3e1Hlx+MENQ5baoGdxjsFRU5H9o4WY+o4SXF9ppIwWDcBnTMNSRK3goBgdnBMU80mpFx52EM40tzQW1K+DqNeIwbcq"
    "vrHG3h4HAt5D1cEh7oen2+JnFL2xxdKWTDdMK49BsAhA08Gp5L0vSN0RSliwHW2Up5M53OBpMpOvPDq3cG0I5wskO+wj5g6Qckq61KoRR5gdvE"
    "jE6P+jwKW1uV3sDZsvhfsNj/Sit3zkx4qsIYfOj1w7yuqbJFpiw/YR4tL0aYpgDB5OTGqpMHq6iszB/LXEv51TH0KUTWeKq6teCWALLcmui0xX"
    "nNogjY697FejRrZtP8I8b2u7IyTuhfzgrqKs6udl4mfN26iIbx5EqhODU5sW5CakwGH6gZzb0LCEpWYaKKyuYryrENHbO9tfKw6DzxLXUItmHy"
    "Qj8bUU0dfK+cu2hU6BYwDrDwR4TUQKBOywKEl4PHsUu8Pg6O2XUa/RyBE064qlYMQiADG2+U1f26vqjbXJeSlbqEa/s854SZMY+VvzHxQtYkI0"
    "FYsAtcYJWtQ9LbaKgU3y4WQtgFvDdx7p7/37u6iklfJgF70n8LNvVfkNX45XCaFpi98JagVrYeoA0/aGijAybHspOMeJdkHd8a7j4I7phEn5zM"
    "o0WzvNdcMvMs0/+PPftp0Olv137/1ktPgbDXDbIKeViVKiAgoyUzKZeaoGoRuPaFLWTvHIQXNcYqNMMZIFJfed+oozvHmlv6Vkdra1rBe8jqPq"
    "FTvmika875PMbt8mjX9Fq1kJlXg8uIopDTSn9c8cnwi45Szvi64sGtZNcOWgZWl/hkbCRfI+ogFrlll6+TX2W6mRVmqmIet41cTJfYyr3O+Y53"
    "TedO/3F3FRWcKTaNftcVw0uHWG4UD4BRZeKzbaKKbZQUd7E8CfiNDJQ4N0e2y8R74D6wPb2jRkMP/J7HEeEdsx7Lfk6H8w62W2ZiIyrc+1pExf"
    "ADG2ZrVCeD7VCWj3AHxht7qXOmRiNxjrF/LwVDy7nY9CB7xci/Fmvnz6MXpgYzZbDW2cQnD7xPBBQKke0qtULGs6Fv6EqKMTxnS7nGi5aZdVl1"
    "eUGzRg5UmcmlxbDXWQyyOXkPleaYTR9N9ROTpcAEnpp8YWVvYCiS0JmNVPV/MOVHqyHT2QHREA0BpXTCsym7wdekl/eEBV/MWGxBW3UvmWboHO"
    "JdeBjEXIU+2xZtVixQK0Hc6M5WvjxF7NvFGDCjETbSnBWEgeQMjeOsXlYC1/M9HeVXkC6nXsr6BLZuaKRtWRUweCoJUhuotQZjw0QqTnxm2QhM"
    "MHcE3BsD+fp0ybncb6jg0Y6vPWG7kIs0YtLHd8Xzf1DlAYK+1W5x//QI72d+lApxyNxP++4LAgkmIRUSxUaBUiw+56Eh62bjrTiPOcdNgCLl4b"
    "E+jI1OzTFcgAK0nr9+/V8fInX+msDdKJFFvT2tHvvx/Xsh5dI/mldmHxZYIjt9oy1A1oXQe7j7bvdG3mxkqohj/NgJEqjPxNsLKtxRvm/I+uwM"
    "9+zqf+J17eQVkQu+NU7qEY9mMy9TTGtFq/d6IRWwaVDwKEoBXQdNal4Iwc8vKBM6uMpl+KZ1CUGcsjxGa/1RhcorIKTWa7ObffgtWHwySyOHdT"
    "3yW4nyGxoU3IWBkx3WUELy++Lssyeb45pZX5TcZZAM38/23OT7/vUCXCRU5QKq1q5lWcfHdei6yYhoCOpPCO1rSWbbVHlKRxnCQ/MQmLRAQfTb"
    "nCzgw2tZapr9xSWrYdPVHcGBnKk6W94lhq6nrUC90Bb6LtMiTvW66AyS9eQ2xK8rlV9/DfkCpmGSqMi4zxTJJYvioNTHn+2/I98CW8WhBaJ6+j"
    "9KhyQtSrtlltszq/J3oWgSayc0nfq0OH5p8pB7szvfZ4VZQQXsJ874HgJSIgDInR9IGwWNHLXq/QrNGvWOq+QFtH4iXGbQ8EJic0Ece0UmVwRR"
    "LY1xMCmhBeURXTDfnkU9oU332QrJhBt0Kp2krCXvplBAt5zTap5CXTBfB+YMWSBY6VGkX++Lpq85U89JByaAnN4QCQksu7cMAa5gMsU+6yHiLN"
    "zkU4s1YYaGD79gREdG11aoOlG0WgJ+YrxLUeRxzRcKchE/WmdNYTsjKrzsYCCHqhDRH0g3ikbwgJo3+c+xlWsKKyNKXydjrfjo/b//rfSJckdy"
    "JntdElhRDyr70LO/jPb+kUXU+yjZC7FzRSCvhIWFyq2CcOFiSl5L9+HLoX+o+iI77ti1QRDZUfnWBy8z5QFtBUQrSWy36krJTO/gme0RphXg5B"
    "ceR6EW+Q+04YvKymZCBp1D4upi+D8NqQbVbvxWW/ChmSVponxC/dkM+7o3Ic+7tHeJf39YF3Hd/TDu9REbl4jcexvuuJ4jhvzb6ok+4j4oNjcH"
    "sfYGKIQXj3QSTtrJ49v+n2wFa3fDznsHNPAPGwVk2mYUnYVLU97iT0nzjxwsPf5NeAlVvfc+08Qx5qCKAMfVT5r43Bjgc2yjaiy8X9mHUZbgdu"
    "SHiMz6ejvJjsvVGDYYccdEAqQBJtHEsDT5bNSfKcTSsOMFzA+QAcVU2d0XPKRBd3WcCBedZ0ALOforpJbJ5qfTBW/dMDCMY7O7+6jiNSUzAshi"
    "mgRz3QN7+fvfcFUoDLkb/RXO1LctU/YYQdRiHuBbdo8h2d34adNme0TOFmeM8CTbV+fEtRLdqZ7im57+64Mvwz8FfkEXEaFLVZfYmfdVlLfN3C"
    "xV91oJp/SIa9cYRfg8Rb3qP4Un+H5CV5e769AzNq8aZUkz0ynG6HALpTyyzpPdofNKeomw1AJbuYf9xf5elI/kP1P+D6UR2laM4wdEUCn8oDCz"
    "tqvkdoHRCpyhXPMtsdOIWjhMaetcPQcfcxNWX4w7VavBBnhpfV4pZFjs56KnQPC8I7v87jZtuFo5aXqKRoCew8WqId7UPGpNG6bfuRjUxUV/aO"
    "AoC6AaUV/8xFa0r0qp9xy1fxbgEBQpSrlPoQtIlF+buuzeeHnAv43r3Ala9UxXpIImVdjPIVDVLV1F5UudsUQGUSfbjzNH0iORqXlUjhFso7qZ"
    "xiOuQ59mDvf6Pl/D0zybD9wCdu3OZoR+3VdXhoyfwRxjddfhBB4qEqw75CVt58tvQ5ZSHEbEC/fKAV8Opo+ghUlEcHxktcOyHsK4mk1JPdbVEk"
    "u466S1/wxTK7zj1u0miAj4uFYymDpZUz3eJEwm34fNC01CKYKDhSDNWethBpfypjKr2TrQ6uH5SuIoXHZyCU//95niK8JEoo40jiIrq8Ct4wee"
    "cztFCtMsAyVatE0YW18DgRrGUDoQF8AgvI5Qn/uzIQ3B6XD4dg4KP/ztQRXV6mhLeKDOg7/5zZ/VsMjstVj0ot5bTmpMMb8N6bGdN+BKPhRR0h"
    "VIAT4QveFQdgCCAUk15maFhtNw/F7aBORBXSr0eAWR1mK2nOubBXFWxjvCzqV03+4I84L8gZzk/d/Jk+HP7ddfZ/fyGUrR+1XoEjwlXSbWz4Al"
    "Qk7SD4/Bwt0AxysZMDRsZZ3lttM3IjTz9qMYR9XFnwlbSGRmNdw08DK3IpzL7pvr9YLADQ0AMKT7J9pyHl7KiwG0MGhTgyQ48CGRZJ638iEed7"
    "Apm6GvdSvZfzMabUh2gc1SYQqYeheDrZEERhzr0V3awk5efsJCl+oz7HHVlPPmXZz+si4+mZAL1SfIjmRpIbhF/u+We9FjJeSBJvp3s1rhQ0Kw"
    "WKAEYpm5EJLBgdSgCLmPr+B9eAFZh+iB/KdWkbsnXbZbxUFEY+c57qQ7wWGnTRPrh9wOzagGsr3WL3S1AtyDR1ipwlKrZp6QxD8pNEk9Zy2jqd"
    "8ZXrpcPUZR8peBl+EJ0lc8zegMXi39H2h0ZlCRvRJH99rfjI6q06tdTf8+f+tTiR49rML6k3b5v10ptDysHlyA+Yj+R+8W44nNy0WUwYimyUOE"
    "kqlqJ5NogIleQWn9fU3K7uF8MWmoLwZdouai0TigfKHUMtMssWIkPVf1cVsQhW6XzLDAXEq0WGM7p+1GOKUfzgX+TAsVL/3Hi0LcvDVrm+JcTY"
    "O81Aqqchc7i2vxzy6UIWPO6H4oSogq1BLBullAZgetMuDgJri5NRd9OXWzDhkojYuSV1QM69pTe4+2AZ+6SPbwJD9ziNj0fhTOq5ges4rWB3UM"
    "SZ0tkTDgfddL4lx7WoEIvyeBMfr4/q/FgCYcjNGrAUvRBn9qd7DOM44afEIm86f3Q8Loki5vBOn+0+KY9Lvjx6wq9Rovv/2ZRYeS4Qa3TQgja8"
    "GgQIdPuaW/vVhcNOLKqotZywpavFR0p7AglKWNRVhs5WuRSkEHeuD7DA6XQpJjWVJ6eMDHeHTmBfYuXUpPB+p+gs+fYh5j7aw31MerheuaNbo0"
    "LN5KM4sTmJRTL0mcDR+WXItSKbxiVlsLxhq7JvC/lwcsRIJediDsjoe49f7FYaLAi+cQeppsZXqhFxMvKbXrBmiBIgU/vpRt6mURRmMUH1cyIQ"
    "SW628cEz+VjPvbN+XgSv/dPx/8JfIx7P/RfacpLlPQQB8dSdZEDeIXC83yuIBDPC1fPB64R57+i+VUbVWLfGzdolOahMdg2Savoq5rg9PMv//c"
    "6rVpJfUxkhK9HK9Xc8NKeQzcbfOYMkNiBhEZdL15n0tR0Lt8qfcszz5tTMm41iI+7P8uWZnb/9bkEtX8EvbeR32OvjybDhMaQLweGKTydnQiML"
    "Gtxbj1hmuL1be+WupSkH6fuX7kmSOVlGb27PHm9sc/8/1E9BUkaH1Ul1bJiQ6wcbm7ly609n3Yu0AOfNf8MuJb9uOUgAIjM9yRXFocQggHJYv3"
    "1OAnffAB4xlgyhEK8cgh5ubNhVSGGQolMB2lCFT4wjfETrAq+JXplsUydTaFdww+k/lQC0ZJfL34nq0ommetSdHbt39MKWNtGwqWFTcQJPDhrH"
    "dCPtR6QXrxVnliCAWBIPLUDDVH2Yne9fR8qtfQzkQ5DiqqxKf2W+T4CbzeButKz7+1uA1CgRxRtn2ovRY2Yj7GuyD2clF4ThUS5oEAonrbXF00"
    "UYb5VzAqMRyMRCwWS+5L1v4z8U4TZdLeNNhrXXZEPTFwKEDk8o0CKrmqTAJzLPk6dZ9+QgplZzAnf5qj+TeMyCkfmE7ozJ0XWnIla+3LsDTPu+"
    "cD6+q6YqFh0S0bSFYQ7+oOXezuO71wPv7m16XT6/YL5FKXg++mNzk+FtdEX5vJAkacvlLp/iKZWbYRfm35BJ/121tZ/YlM59QjMrukjEltmC+E"
    "oHDTYTaq49QUOQEdX27jREIxYoFI99ONJFkqwpNlJqeoz4Z785j+GHol5yAKUJHEDVqgGQMlbCTZl1UNxxRg7iUnmxrMUUposGuqTQUCJRroQe"
    "D4NN+YEdCiLXpte2yOYVLVqKMkQG2jt9tPIuGRZze7Q+e682FyOXcGEF9eBRtZItrRqJiqA+Rn+Gdlxe1OEAT4q2wx3By6njWKp0dZVIWrUJgN"
    "v+fq4CmIyOklMemIBHZBVFeeRJBfHEeHBFzCDdVVyCGk4blwoY7vpz+IG3sEgTyaKwbHesV4vdI9vuRsAOJ5VtXtGLU5gYv7/qABeJiv/UKMR3"
    "xtU/qQQP2aPx2erf8/yBHT7mMnytv0rw9iepjbAcG/XOLsZGZbkw0jF6I1nc6sWJnY1IPQl2zpfa4622PqNRW/sNaclktC7gY3nN/gX1p/f9FT"
    "kmh8J+aHWvgmtN/mjpWT0MKHuBmH97b06T6WCK6RW3GmI/0PKq/XopzdNFtD7NKY2XtIaxPOWz12z2ElEmDwa8xhaFkqqOCTFhwaXebsrPmWJD"
    "X194nNYMC/VfMM8gdnCYtSEc21HRRvSYZG1Aou5WSTgkjimetY3hEabvookp7EDK+mEw/3KW1EJYt1eoMEmZvOe0tTFLTJ4l41RfpB54kl2hWH"
    "h5ohfBb3Dh94h8vPRO+MFSb5M1B9BV3iX6jTdPA+Q+vo9tU/lmvCVWTYa64WUp4rcdmcCaXLYWJgc3UqMPpW7vYoNcUoE8Lb/hNmdsMicj/B46"
    "dsnwPzwbD6BFXe29t4gJmp1U9AODt0wgOuv951KFDqpYf3CgIKg0thaJCdXMoe4+IlfwcQ3G1k24L3/C9X2ZWmVLFPpAnMN9f4qLIztSAZxvIm"
    "DzAAqz3Afu/yC4A0Vkla0Bfw6wCUUWNxypL/Q0NaRTbDsk+m2tzzQMNNplFIGQFTfZDiXFEU+ya9pWge0nazVHYBexz/bgtdLwVLnWiJGzqMph"
    "uUYA/dzD5g2JSHdHrFYsiMgdYHLQMNPvokty7l2wJ5b5B3C83zS4Vip2yuLip1zyqJp1LrRbQ4hoEy/ESddPxC9mCoAUAscfN9FmldEhL7Mh+n"
    "jHNRfZxLOXLoDTbrO2Gm5FiCDPikIGnFguwX3cbUQxPB8CDKJlGvGijug1BxOcRblTDptRGVyf0YBnE9N6UGazInPjh+iYeGganBMElRZehqPv"
    "9nwCLqaOhcpwZLmdSNoE24OAnXcW0/gjcdfQHu569I79renhwKOzHOqm6wR/m7muGQJB0YDHxcRoY6GzLxAuS3Kc6cXhj/zbQrk9WDT/4iBHBi"
    "iEyinB+gUjoWd3gcdQuz7y0q94c4JRuFerMlbi1nCOvx0NmZvS7Ud5xFvesdvaih2EujSdwuQjl6pHammxmZgPy2mKJZcEQXNFVpTyGKcAfLOt"
    "K5IN0Kq1zJ3BgYsLnrp6rbulXmT5kbUhI1iCB0CHJTKtfJg+yPKKOR5uJgh6SOAKIWtqxk6HhnBGhWGmIncrskM6rlt+xmR90fjogpF8oFGsdZ"
    "2PM/L+XScya3RQWIf+Jhdt+edBe5CnaIKTzadncuNW14QQA5cAWEEfVe8FA53nTp0lERoUpssXARKnolEUUH+nPFx33rJmioROyaL4XRVt9R7a"
    "1qGTLiR8APwEs7YNRfRRT91pFuPkLRph0+o7cp0YTceR4Ik6xihrHR69RhhpzD9a4PqSEF2m7U+hu17Xhr/2Fq1pkhubAyGUGBsbVTGem5aIhh"
    "/AU33A+hBSK4j9Zj7G/UEDxuMpYFJwMjrB4feLFiTY5RD4xYIGuGzPNKO97isAyGa7TV2rANiTtcgwCl2Vwl2nQljKcv/wUPM6cKlWY5HcFgRa"
    "D5Ao991U3HScI2hbcxUsQxsq+ZH35oi13VFrQXMHFp98V/L+9S4fZ7Gp4SY8ufgEnHPlbvR18Ebpu/p9t5ji/5xc5QX66Gj5FOYEE45O44/gO+"
    "0wccc13lmZ+zSuy92R3LccOsJN5QADJoqZSBt7ZQ5vVBkpRP/hWSHY3NGojvlk7Zl0nUBMEDdzF/fI/aOwH8+07BIlMuyZUkwKUrojJDsJE4gg"
    "ZBNvd4uRzxqF7HYvgsRpVVBu0ejNrY5Viubx6Nx+EZxZLswgnw3Wi0L7pH+D09JOiRHcfVloMwGFYkbYwF26HnfObeXuM61oV78X+9/9H9ZPHR"
    "FpczxvauXBeh6RgzW777T7w5+KBaZDu/wwW+XnN09UcEL2QlPpel/6dsIDuKAyYjnIKNGlVCRIflDifpDEfkZ/vIvx3JU9uo0E3sVDTU5wYabo"
    "2xMY3FFut9hOlTh6yjj9bvqllfOaaUHkGinrL2m4AN9Xpr8w9uXwV2xN3Uv7tFAOKqHukqr3tboup0EeavnuUMTWubI8niDnGs3Z+Hn87Hm+3T"
    "b/m8rgf+9kX8+HKn4Nz0OI9inGahyvp/z3j1/DQFFJTmlRiAHq3ycyXOplGye55uOBJrl3Dv14h2pIeOsQZjUgPpgKy9O1dBD2VIDmWKHOuLRT"
    "SRQcLXvSRjEwaG5KyzvSBXYJy4U3m07CiJ08uvOqxDh7ZrJS/3HlNnwK5zZWAEHAizdbI3VKenD705BX26m56Afm3K1whF2gYRxObWzyjWHzYt"
    "w7+kXhl3hr5NCD2vrkuIZE8sAbSA/s0m/x0P5/mWxywdJ36vHtkDqA2UixlP4gB4wZB3o1tUZ51FgHGHPGBEqlkcvGtIBGZsP2bfEx03r+IniH"
    "45dS9GyEYGTdLUNifJ9lEa0oMXNp/UM/OHWSQE+W7W+5TquakuTYBpF3JxrGpy7UOa7DcjTkUkWllbxtcCWSGiF//KKGdW+y9y4+A7AJi1jo5z"
    "HA21fs0JK99d0HwNKZce9loKQlqbpOJjascee6j9TBeSNd6DS+WQDC87mhlrgx6PcRlXKZN0jEV7JcNKJMALuGlmEOqjDv1bcIvZx6ey0C559c"
    "UsdTzfueTHBukWhqaJ9lfveEgh9j+YLsaUWVv9N/2jPOJntf4Mxosne0JWXeE+9mk4no2G3PRMFeEK4frd8ROlxdflZG4s1xwfCpUOaFGqW9q2"
    "LNe5xoEU4e75FG8X5xuaHTOUfIMlOTMqf8RNyAgWTLzG+U2pa6c0vwGgt0wRGCAoHTGZDPy/NCKRoyOmGL39qYR3HEf4Ji8ZjskM7rjFGbTcMd"
    "RzGlvBUEFxtTiXvxtgTARExR6BRh/1xRChwkHK2rDMCkCPRHl/NdUZqrU3frnGg4K8/zyViIgyprsJv24SeEgRdULPAmb3F3k+FOZhTeGHjxol"
    "I9rDZ8lw0CqgGLKKKRxBUE+ggU5EWRN+4eDEdBFDcNRdZRNaGpGwV9bipJfoN/5PE5G2z0fW/1gZCnn4ROOaRmAwLaERCl/zoPegaurljs5h5R"
    "TZI3KVlQvBzkTS8EP7OmdSzbkLxnfqrybFtwbPdjIVK0fko0Bt9M6AIo0Vou/bmjYqaO7p1r/Lv4AKYCTNVtxWkYAK41i6cnBk/RMGsrdYMBgQ"
    "FFcE5TtnVxc3Vuj2zLYkyMN2NpgFEEgik98IjsHD56ydFrfHtmTw6swlcinE5tx3t0efKfb4gllvR9go6gxo5mwJovT2DiBHr8Ksk1S+IM40eB"
    "0eBopkEz2clEGnQGIXPu/J8Pz2uIUWxFpX6plCxcMgQW/pGeSOoOOYY92m9b/elOj14EpQSfMkzPE8hPh8jCMwt6OSPwpBc0OORgEdoyrZ1t/u"
    "IcywoO0KzdKcvPOqV0tlMWh/jWKSh8iNJsx+qRhisljF9uSmh4Im76d7ts5AYkb/ZXfWJrmZWTTWie+SxlD19kAnt8xOkKoqEOhnuVUL/Yh6M4"
    "IQeb3+8n5526pb/xTDB2bBwRS5vIbJAfRTBcO+j744DgrjDyEKqDfa27JYEahqALpKD5R4iV43qp6mYW5z3B2m4QxVzrSb4WPhs+w9FPuz7Ux4"
    "Gv6Rs8wW0RfwKXrzyp3DyHVfXCyngW9cuNZqF6XK8TfEarsfp7ZOu1YvX2tltDPuNSZ91cFLUe8QSpB+ZVWb58xQbLT2Olvv2v8tlD5w4S/Hsb"
    "fAQvAH/YYGw5yFP1Xxj0gfqq2Bdw3xmHX8NiRForTjkQwFyq0ovcf+PRgxQ/lOlPZ79/Y+koSWHwSS8v58dV1IQOBabuc2G7T+HelyjiY8Kzw/"
    "e++j2d9lhT/xac/SIYLb1C+FzMO9uMrU1Wj8L8CXf6PsnlU/YcCTjKNt4EoZp0/ol+1pSX478I1F1lFRJ4SxVw0CwjCIOzvTI1nHThy1NEBICm"
    "L4aOGNGybiA4f/y9ARdP0GZlDGkTC/CFRjLYQrjLd1wN1QxsNVb9efVRhnTquoD+W2LMmJFeGuDeRHEKsCAZDbiGOCbwOMSnHmQMKtsBnV9CVV"
    "nD3+0R8oTlZXgWlRkCT0zuuXYulzT/9XKOX3lL+qrwCr7jDvGGYRyYh5QaUS8ZvLxgXPnxoqA0Iwy0mwRb98jrDA8cRGfJiv0UMF51Q7y2qc+M"
    "iBgF2N07MGEnv4kFIwf9+20EJhTbHfw7OUO6vGUEN7fYOIag35H5dXUr4B5EHACml6+msHy26t9dn+Ui71164zF8k1Yt9K054/TBMNhNiVw9Vn"
    "O2PHWNrTRFIc5f6GsBDOGqaav16iTw50ZFqq2IX2ytrWhAk0L+T7opuuEP/Fet58Y4hqkBMSe9WiduntvhOeAZpFVpbYIBylBkg0kxtWesJshP"
    "ErJks95GaUm+QGy+0uNdgKLkFCMASB7aZl1Z9wV0Rfhfs8NJGzUPRx3DfycOTORkDoi0DcEPFESzcvFP3L94EGuuHUUnb2GNclHLtKm2/8Ri3T"
    "n/Ycu+UmwLozwQkUGMoC1NubVGXQh/CRPBBVrPHjxMJpAmxEgYf6tbji4WdjdVA4CAhzSl3LHnyQQMFfoQHKW+S2Fika/X8HlIKhL8g0ezKMMY"
    "j3PcYsHUhFQGs4xIS8Nz5mP4LNRCaL6J041+iKYY0BGpo++amhqduYQVFliFUBohiG9pwiD25ZOdBJwfDEEmiLi0cO6hj+bbiVLeemuW7OwU8v"
    "3qBtun4DFXjrq4xxQrpy+soe1ORyKH/QRSNaLhZFTX6x5GYiXkwA++gFxjzbTPj3y5de9oXQ5Fr77zoCfF9Pi/gQ7+7H++Ty2vxlP4izKzVYxz"
    "XcXaxNWY1fsHxKJgfoi0W8bd0ziSW7zwk2JPn4DlCNETmu5b2vrLHJdzzT31SdUyc1AtllhMJ/KV6yZqsOkMgdtsbECcO5uxPCjwXO23hkfU8L"
    "t5MOwzcKBFA2fQtHy83q3rQvAc4OSK0pJOFuzIwCeVuWWcVGPSzniJn9HGH2jIsXKh60mZKJSTRkXTtqmse00oHO6q83CWKSLlzW7GnzcgcudW"
    "pMSElZGkt8ldJDLb5VeFSHx3wiNAWvfC1cSlUFdLrq+o1lJCnIzLHXTFuaZab1fXwFEp5YmXZtxfZLFLiCG7f93pRr/nDn296D9KKQBX1Eu7DN"
    "HfAsabCP7GaEuOQQNvzdjEzM+B40gjhNPFcTa6WJSuk+4DIsobvVjzhdKren3u9KlrcEvqMkLxdRCLLclw1YcMoE/2Z4H6GKVOTEwNl1bLIUF6"
    "ql8jBGJxPKGA9tbHIZmwxGFwv56vor/tXHQf+xLcxnZJHc9wKRpe2WecfUKPGSDnpfRygEywZC1mAup9YC6RF2beVAZWt75ctOjelZdUKuDaPi"
    "GhN0jkNusevqdNGC2o0qGlvAr4nxqX9SxeH69uZrbPzwhWZxfIoV6As5qr5i57WeptZ0il3Wf1C+TMz/hySLUvQ1WqJPX1HFvSqqzQb7DxuseF"
    "UFaQsw6lU4QyMPROJuUOE7uO5bTT17Sxv3YMHmPSVrsb/wKj006WJIbfAVlHqKO1K7ed8aLmhhlE++Kk43x6lVQSRQLJqIigBMs4AY2OfU4FqA"
    "Pj741CjI++CHqpWyoIXCH6KI9dZl4fq0rzht49ZzXQh3xKwMWR5Q55cxkvHX8f8abkFFPrxUrqzcGrU/nT+tpwW+ouTRTH7Dn0ZmwNIDRL/W1i"
    "/axKfm7cEvexs95P5MDKOY8oxL0v/MAv26fARfIAzv4FC8+Sk+c+rxyitQLgN7NrXzVdi5lKF9ooXNhlJHs1kl0w2X0/fAQPkSoUwVWw3ecRWX"
    "iXHILc+dCDdEtDshSvxFNsl7Ermt1z7N5Y/N5glDzAdLUMKRe+uLqzl3nZw4VXj7FyH+C/kzAfy70Vegg4+Q7C1lpJg0ytyFQwbHV7lEXgGh9l"
    "AbEscHS0lBYBcJEnDbizy8N/78i6Rm9J5jLv2uwLR25KZJk6Rf3glplpDmUGPnKF4WJz3JS4+JltCChfMgRw1I2BjHOjtKs3RwiN9vN9umUktL"
    "sW3tnKd49GdJ80fT/HE9WFw91y6pi3cxo5KrcQNipNfhdlgEDdOaRrG/ErJfL5YvXahn7mfUHaXZfR52G2KTE9dq1PRokuaRxWfc5gVuN7LnuE"
    "/o3qE6d50psl2aVaMJxC9YyMpBCIbb45ixYe6efC4GFt3zbDyzNC3el9cS4PDfu/Y11htanxDODPNNMWd2X6k6oU2SoUegua+TBGebS0eWUNh3"
    "A0UUmbWitgSwrLGI252jZlWOw/qdvJH2o28ziFYA5WZLIn4cIH0aSTpGmnpSMLE16AhIfEKAjVUtNowsp302u+56qGsPM922AzUoqJviHwY0f1"
    "5FXOM54Gt+rqArlxh5xgAj55pAiB+iG84PSXpXb2Ll75vr0TmTEEWebshrviGHml7NJnjrEgHCVm+K4l5aWf+7jOjW3iMv/4fiHdGzyxZ0Cye1"
    "La/DgtRS5dzwWP/4nBzb6ItTfLhdJuJwAvNZWrHBhy3XRqT0VYF+uHAMH2fVrmJK0yeABZlqyu3ZW72lNIdmWEJ+LTyhwIA/vpnTeIU89NS8mT"
    "sNT8uRAFD9brj9cG8U3gMBYGlyuC/htFLi3oYdbKyI9XLfU/byj4kadQAnAnDf5ZhmZNZlFCA6azGWxrhIP57iV7gUw55piIH8+QrmFckLHSQM"
    "2F+pz2oz3FGx6W1hDDoOd8s5VbuhTgBPoL3yKFFd4Gn0Sqq6FrQxOmXR/XD+VFM9LeP/UUGxZqcoGOw+SvH3BYFZJEQetBjKVkLJWzudUF7NFX"
    "HD0DlGgaS3hsHSo98N5XhUQSYrZWNsyf1qdTZJ0IOvSM51xXRMIwktWhCa0pHW5QJXVXaFZ378Ts9T6WdEdrKqwwBRq6kFnGtyBfiviYB5H4jo"
    "+vapQ/vyH0CvfMi/+Fhg1BzqT62N9kJ7+ZXrVRWDjbtMX4vRndGNYNoWcNlyjsacNA4YyDJhWq3+L0Sv4xFn8qZcuFIsyNei5EizCjplTGtJTu"
    "kPdWDoxiu2LzlXLdAZEefau+yhPJNQjtd5kor+URupYOYu7mty4Xl4G73L7bLZYgNlFBcVgBVaP/mC7ulO9s28jOg/8FBdSS8/3taDqThWKDnh"
    "q6R8Kk+KMrt7o6VTJNeEOb5oU0dU04iVkMsOef5+HajO6HotMJHNunrWZTPK/Uc6Acim+b+hKcmLPJNy2+MtCbt+amTjyqp8zBYgGKuS4Z2vCz"
    "xubMcVwyFD8UWuoutH+CVdvyvCqWvvoc5eN7+SgHxbsPGX6MEh/cwssuc/NoAAYPvtwNbVX4tXexaCPCjoVw3XxFsP02WPb1IL4dh2sUQzhmCT"
    "j+EY8grs/Mmq0//oVroS5d4SDjwWh5lZnLJ6Wn4SlnNfarZTqT9mQ3vuPsAmI26k9RowYmJ8yWHsqycEaNTr1ZA/oHvWpDB/y0fOUTfomKrau5"
    "V89y272BCP5k885YLdR8NAIpOJhalqNVl+VUt8lLVm/k0b5comDq7m7tf4xPTBt90bpuYVVJMVG0nuyyTxmbCnV91Jo/tteDd+PRTALwQcvJfz"
    "9KpWhBVn/c2RrMjoeSLX4GHQndah16mD6htRNmUl73kiWGtAE7rGiiiu14otaAF0oQC8CVRLe4fFcphoPXy4wFPeDZ7WQhFm23ZycC3TGieP45"
    "xQl+mx9LAeLa0IY5voIGY8hQunCavTmazsilBYSpgdu/YdCXnW9fH8A84/XyBt2U24LiDGB5dwzgHbh+ViKGitX71bfc5QcgnBT437cr8wEfPt"
    "TSQrzKRjlr19jHzwU9uyF3oJUJpHucOgE3keIEzY1aaHDdQJyy+VodjKJiLzaApbqa5IQCoW41SbTb9hygnaJVt1QzcmpKTVtxE2iCJhhh5Nhi"
    "6vwd0t8NJ2d5cK21p0PspfEJ5Ma2bnwhINVz230SAitSO+y0W+lKTJ+UFcnYdLjFtp/1SPgBecYtc0eXZ54lDXKefYJwXbxD3yiFmo1ZvlCJT7"
    "tVVvShFR4m4XqfiO/wZQKFIPmTNphC8gkCOoQS9oobxj0NxCbTe9teINhd51cO4ZtwhvfG2tAFkqyQECF2AjUv2h1+CQIPYQDQUTPzM4cBJ3Eb"
    "HxouExxEIBZgsJlKIdVH6CW63hHRdFRES89i4buBPvj/tiZScD+4PklvAF1g5gkcud0PDUwS8tTK+3Klxg2papwgT1EbFakfxmfsXBckndw/Fg"
    "v7OQPg5IymGCtjDNguZcHSlVw1DHRZy9+4abZGKelwCL+6dQsNnWSnI3jBgOY0jreYOdEYv6hVidNty3MefWu9NamHTIT3Kg2H1HPqSXjNMgnD"
    "7ENLT74muST8VAKHav5GdQiIo5hqu7Cs2ASmZe7GqEfgTRoKMbV/JtEXJr5gIxxtz2+OT5XhMYJdoHBg2p058n7ZSEo/AuL0A1uCgpmX1358U/"
    "Ckpsthsm0JqyscqYW6qAVcee9g5j7vESXXW+cy/cpIHs4a+mCCo7eqqpUqeBVxqNSLAOVTBdMGNaL4tT1vzOBbyb/M/Sm86HQ1yGQYxrE6Tjhk"
    "2wTkvk0+tC5249fsX//T1GCQsqOb/3tRi9YJ+vJzZBA13cHWideS6VDXWnas9OWrMK4jkT+wKfcsKcVmGN4yVbfzhh6LKv7VeE00I9b5jn8Utb"
    "rHJytagtnc++le+RaeSzbVWZJ4G7jax0cUmcC+glYnxQZicSZZThPFJBckw+JsTQQ+3xq5RNgAMZvME7+uma0IRu8JUwfthrueYiKmff+3rFY3"
    "cp50bNcS30eztAymnQfff8f3VEWaYOAsF3ZlwU+meAXLfuW6GBb0euOva3K3DYqfa+W4H5htv76wXrhTP4WxAP1d2InENSjY5DMb89qqcLEZC3"
    "FUdz/DLuCxvx2dWWRXbvqMfe/jF68NcqhjyDSlqTbKmHBlK0g5Fv240pR6lpz3HrKyRD7vsxFf8VN0KFsXpCajPu6ex6cRo0pQbStF+ZJ7HMrA"
    "l6nLTkZYwh0QNhwyCSjDKbFrxNlugSZMJNE4d0rulKdjUhMAhnzFkT7mgQUaKiHLymz/JdDRUd9ElV/LY+o3leqdpYuqNtdKTgKDl+nto+Urky"
    "5MBo3AKXi5hUFQaulOwll3b3vKaw2DsaqrVLaIC9BTwZdd5Q77c4npS8iPWgf4MZXVW1Xt11zf+3VCL9jqvSQMVBwwKfnEoG4G0CUtyF3dWMnK"
    "ykdXXOTldkYLWwz7VP3tyNsx/HiqAnGZGv8G7idK8rRtf6OX0c8dz3i7E5V1mRu3ZvyP0nzs6Ra07kBfDia+fPvLvvaGDluVQHhRNpVLp2HiwQ"
    "P23s3ecflxLf7zuNxLG/7S+XMfCkulLNGZxAohq0B+1ALnFFJGi6aFW7gVXx0vQuS7CRSMXlDGGBds/YlRUlgGlsjVNlVSQZG0qWvKks2KONyo"
    "bkg4a0WLltuKvdmWBhC3dkJcofwvjSTgu8Jzu57ZWJ/wt11J/GZpXUpkKNY+qfaWOGfTqBULg5/wntZ7QaWwSHs5383l0CYqsmyzk2Hb8ilspO"
    "fyt+Oa5J2bdcebSMAXW3aIO+BGBkeuADlUKPmpOo93+L1M2ow34g7HNPwquv+8KZCCtPbaZcM/S3LlyHNu012WC6AMr9OpBNC922ywo9XdCUDF"
    "flapHdeXjM2TY28fkoFxCVyxm22rS5Eo/MBkdRFkxQbY352qli5CeLCo/y6Vde5leJLUyn6njfAO3428Q0Q/FpcgYreHS3m1Kr8X1JPqHDurRK"
    "3e0CHIDtgTpb9YNSv+pxWiLFkRRzoPO+ilq1pD5pTuwGS/CtETFRyj2aCzmsK9YThU+mjlNccEOX1E9+BI0hmMTwRQmXCKNXx8DEPuYgXNAdoZ"
    "eUAQixkUjKXEBSUb/tblzP22TmSRjfjg/1H9GX1atUnf4ghpP6EwcQxKds/PlHso98JbDLG5JHRrn8BikT1SpIzEf6Mi6LJeI6sPDzPIlFGoPn"
    "QOnxdzJEQhSavRO5aHoB8OfcLWtMN7wjCU+ip3Qtr1iLyt2M1XJPYRu8aVk8AyoPVdXBWhAoCd+z4cgrtKi8OoTZOhx3SO+cab9s+nY8N/o9rK"
    "h0M1L1iyHkWPvJf39fIPPrWFdBfrX40/KF91F1E3blADz0yNzBRtLf1edSgur0n05iTuFTx13wkNf2/6zBFbspkafR4MsEkMzQqtolUWEsd/IM"
    "F334odRLWA5jHRaRQRXzb1uYr4oS8yMVYTo9LDlVCjTsu4gGaMxiNYNOicfJCzgGxcXY3t9gTZD3SucgFRTL6XX7ZNrepl5tgevt2xtBCqEEoy"
    "mFmYrPp0eXbmvDM/SlW2CmKzkCJ5WBet2f00WcUN22iYzSnPqpOG5fXgS780cRaxIKQuILeY2gKcprIg3aVAm1MZO9bV7UTdvQH31VzXS30e5I"
    "scXc+7VcVSdI82UBYz5WYFffLCWXLypVOcJTuqAqBPiAt0/5I16cYi7W4cGEQv6KfoHanTL9TWVHVKs6KxR37z5sjdH9+fBkhPSOttaoKMRAJo"
    "pOLMdu4nm7o/R7LYBzCcsb7fAK8Zeyo17UD0bj8FSRuRUJxl/IN3K4T0RPqeLiFuMpt3BPKduqPnAJL7A4t2vWYfSMP5yfPfQ7OVxzMvAwQWEX"
    "9l6LdNh0TstH8lgelqS+lXufIUBoDerLFqlK+st632HH4A2F2s1Ae6Pkp+P8c24LmlqurbP54m49ATfT6TtqJbwvqbRulBuyWbJGOxmy2FFIC7"
    "TKDRlcWXc+jtKNrKvEfDJ4vkkx6vv/8GSypPwnVYFdsauVammkBh3XiJY+Qc9B+OCaVOC+NRPsqJoRmF3aBH0MeBfodM3jQwe9puG1AKkYLyMW"
    "ZZEV9cnPs1TfNAZ8tv+7cklDqo3ANJoH+snxvaaG7mrdMWksRK5S9Q9sa6yeEPp/XvvnMAP7jwiJb1hszkhpGPffbt0Hwf5D8uK64N/Icz9ZyA"
    "PFXx7NejEbWCZy3KQXJNCiw9ivFvigKWEDNlKDpbFthPXbdvLYIQRObx2RaWNdRGHO17kg+IHZQ3i9K/SQ4EHbu/Uxf/c+mZBe52a+YejlQt8b"
    "ZgnMwjRhFcs/F6AxJWtuOnqaRJbqrQnRJgfO5G/RtmoOkyJ/5PWV7gOMXSeXJQ5vdIzticVd4noyH4gtf3Thy1Zs50Z2g+zIL4RLxN2D8U4nJ/"
    "NdRn9QYqdJR0XVjHaOL/9vNRlXwgPlF7mqUExLT7g5WvQv4kRlG+Xta0m34qUNdJLk1vCHz7enQskXbDv/ZmHqRD1v/3nQCO9A17Rv91opieZd"
    "rxgMPpsk2v9BqseqfO2Jh/Zw98yhAj05wmClHS9qilnEUJh1GcwneDMhi0+VSoLEm82yTGnOt2ZDgkmhRcbIXOuHpQ0vYZNkV1SHkvuY45DLdo"
    "x6ArYELxvUuaO3HWES0zNC6qAVjwqZW3OB3p+d9NyZTh7TSwKKBmgFrehcBVu9Ca6pZPQxO6RZSYB7EQGXEBwY/DdipXffaEZ0I7phQZfaRblR"
    "Y0NSJa+T6SVMxs/7DmXe/hN2xds2nmj5Kun35JhYwKHM25462jY9ecfI2NOz+3bBXpR2JY6W6VcLn0bb4NztgqYm0n/zMbTj9/9Zx6lZ7//XVJ"
    "njr4hWZwePQhour+uEneqVYqIJdL7J3TwygjCIQafUmZna7ALYaXJr1I8los0bnT/5LL03h/a8JR6Ojcg8NDUvRpc83azd67scwEQOM5A3nj26"
    "iz9l8ENaAZDaUDUmO7ci3aDA6nPGSfIPY/hGVVblseOLwyBNvb6NqzASxMD8ffIyRwEEDC/W2LFKniNPUD81pGRNiv4SklNs6BulVqPPDDNHXV"
    "AvEosG1NIKO/yZxEaV7rOUKGF1Rk2OVaWTsidorYTrnZnp3HLwXTuTVT7V21mivxHryYtcTBX1aDZK3g4MSWtFMQuwXG8JOVlc07lRvnMBRwvW"
    "6iu8yk6H1Xv81D9HZ7ky576kf08uj7F2npHiP0myqp0ru++p1PFlbCbZn7TYbMtrb25jD5QOBnBpg6aDEB6X7B321dK08m9bZU1EfZofIBRBSO"
    "MBzk+7524VPHFZWYTxoXdFedsNebtl5h4vlZV6vAIGuZoI4AeBop1RYc5nKbRMhaJy6Dcumi2roE/H9oJxqFYR5318pVLhgItFhVYcjdQgi7vN"
    "NKBAzYEpVigji/zNmHvDQ1cdQ6fRPxopOwJjPmvHPZAfT+cbY6gQienBxzlpz8O0LvC+MOmVi5LxvQWG6XiXL2Li+2AjQP3mM2drFCs5QaVN4Z"
    "+Kc2jkn+GFR50yM0L0H4Kni8Vpiraxak5oYS4TKBLlGhtVFBJS2XTHJmdmrhVCd8deYUFucJfjejjfM5PSIcZmskt2WtLJaSXe9r0xjbiQ2sqm"
    "GoLvHZVTljkNxN3/ZqVI8PN/Ym5N3ctIUAabzjUEgU6Jarf1e/wF5LGjrl9sGh22KZVBOleaRpro/eb74qFD+Bfibr5srUIFPsX3MFj2MpM8R1"
    "oqnt6USDWfIeIgm1Cn9f/wDSQc3NPPaoeUmHY42aTlfrXWvgF4/9xH89shzONGx0/3egYKA93U9EFd+taJKXeeWhcJWiP9cUyDue5zHrmV2gBI"
    "iJIE4DlLXMTFdLeLpWt8QESja3rnDcK3yNpLQ52IBu7aRrTUxnNYbXF4oj3gSDehS1lG4mbkil89ft2IZ6H1bneT8BTnF7r2CUZwQ8WyZM5Qef"
    "6ZybGGfdmYQIhh8elBZ3toDBhD/l8T4bevyQaGAN5FlfHkZAwLYTX21LdwIToNXQ21npr0cbfNZ/FsyA3zuF146S7dBDnY1whDPGDhXsFMD92o"
    "5M5LsY/H3P8le7HjIw6xkOBfCP2NdXhuDdjl8zOAe+s/m7XeYpw1l8L2fCpdM7yQpS7jhZXHcCaMIsglYE7QmG4czZH7d8HvP7jkBoDKFUXC5k"
    "kqMwHv8oN6OBQEswkq1yfWnMjLdQcmMPt5yiLyU7nE2EE7/YWxsiGO8px2XG2kKqgYUeUAVTcA5F0w4sgK+rEza0u/caRe3g+udtZHmeE5MYJp"
    "5u5K+5KXFhSD8FjBK4voTgizPevvF8QMrrURTB11m2DU533db/FUfUxlZ9dqFthEhmuJnc+crVniYqS+2YzdNBht5I5tJw0ETj4+tP6i7h+OW8"
    "QvX8uBbAOe6BdgEsW28TJyRsCUAa2grLjhWFmvCDtZlGwEsYRs1M/KJ2KwzMoRATfEbhZ3l53JKJiygL4vu5MVrGaRf0eB8J2TIdj10DHMyb4X"
    "nD9yazacXEvSb9TQzRGWPR3RBz3IwNNMJMMyFg2ICzM+u3vi1bE3Bbm37zaAm/+o6+zI4l1RaEetGY4GzKp+gzgfKltb+BtuNQT9vDxvJxOXp2"
    "RXYPBn3PW7Q4XTAli3DeQ14Y+XELa5gWUyXYvpbmPr2mLHraodaHA+/k0RHguJcqgfw9X9zEagzHE82CImxaZ6obSTfdFpBCYZltN/4f17dvNi"
    "4OlOKW+qJ5ksmCwOEZLFjjEnaxjC/WKfrJ/N1w+VoLVTWib5Z4tuMrxvVtQl5LqOO3mWeroOKuzQ/+K79j+deNLZvjKHJDLPJMAZCGDMuyF4E3"
    "QB2s6GLIMVlrqsGE5kdu4Y9+Ex6NFG2dVxkj6K9d7hVc5zL0vjgiDx+nMwohzm4ECZ5SwLrpQObdmlpU44qiWlwq2R5gj+LATFBDlHO8OBmuy/"
    "nG2SsYx2lh+1HmotId8F7sp853JO8aKYFMJkdkvyBOxhR5Thkm+RYxSkhwQQKZXwF1vMnJ0cu4F/uV7u8atK1eaZ/8PQOv+oxvRm3L2jv9EY6w"
    "cl1fqHH2Hs3ADq/pD7Ploy1YowZ5Onl75/U5MPMI2xS5lCHR0Q8tRfCwAOknknPnE5UkzRLVm6XxWNoyG/c/11KoOLdo+s/H8yVoQe3vHOByh+"
    "teti4+JbZL0sc6fK756vpfEvXHIOVleJiemlRnShB96dlymTkmTclp1w/jgPx8XBcZisasxrdczCXp/n3CggbIIO/yUBIGReS9IQ0JOmHdVbZJ"
    "2pnM1gyqchVCnbbAA0t924vxE65hbClMgL6c4LNNB24kXs18L92zmSt+ma7oyQQCh85dcXuAlGC5f5OhAocrJei/c1hwN59h5MoRDGCpMuTULN"
    "GZDX8vSEhbBXO2YxcmOi5m6EWK9do2jggV8MDwpX+9hqrz88MjZoMPkgWj4kMfAd+Fmr6YcgzdkZmBZKMDYTkVPEz+UULU3w0szadc3P0HJHc7"
    "nzY7gS1XbLDB9aq0wm4X3XoZpXzcJrU3Tc0xrSh3pkBwCRSKuLZcOUFs6AlkGVQDXjFWb7aetS7dUchUsZ0AC8zhKpGnEHCcGbnlRnv/iZ0uSk"
    "1cmwXfe5Oy9OZZ6mAQgzWiIKIxYzqJczEI6DxNbPEpCHQAbuGNXCivoPRv+ji8SK1Ks4TXAPfuTJJypp6LhLx+b5h9es4zxxrKk6/wHTu5erRe"
    "U2XJl4jiVvyZCs4jAhDDzCKHaSdzf0TXbFKJZxjWuSFZBqnNOfNDY00ft0s9L3jsQdvsAUCApm9Lc388lYmDbDVkuS/h8/pxzqMymd1xU2UBEn"
    "2fpMwu3quhf+GOorBPcaHfdSr3H+Fq7fviMwIFLre8f020Ps6en9ThQp8BIlNURYsjAM2SOUXdB/KAm+t5GXlVaHT73tSa4Xeievfftd2hcyJw"
    "J6xmSpVregQe2E6gN1s8K3eOPsNmwbgCT2aJad3Xj32w5GbWVoxTj8bZSaLiVOT2kaC2lfGji2rg9mRyB65KO+vY8uQ/M3gFCNvpKu8a3GAoQy"
    "1vaFUcrzU/m3wqRdPMbXMF4TJZLR/UOvAVOQJcQRMHfofb34DX1tb3Q/6/SDsErSCeXmQcpfY8w0mzqgZk3QQBNUUS6OJ4H6+zqMa2uKvOVOZK"
    "xV0qsIbnVTJi3IE6YQ6P5kRbDb+4Vemi/YcWIWXjXAUMtn12oRnCarZd9O2TrIJe3+gdAY54A6Mq0nFoF0WljIztU1MURiqYrSIAlJFRjIDYL5"
    "0BnfJ7z+ovA5iQALLIqXJo10LIs4PO/cgBqgQ8n7T3mf+f5og2aTYWKenAoXcIp0yYVyDDGFIAsg5QtwaLJy4BG3VUPoWefcSmRph47DPBq8db"
    "wfTsDi/6LX5a6UwkA8P1lNKWBlIytngopDl3VHrzM2OoN/oA6wpMVDRps20QkiHRxX/9jw+Pqf2e2gdth7p79wNdNBTSV40xFM+f7ms5Bvqjh0"
    "kzrCvecWRHYCkn8G0+WPYScXfrVnJtIqhTFbmvsQzmt5OvhLv1v3Z+LMEzmFV0jv9/zPWood+75N7luhNuj9L0xRfopPOeyBe5FWQFRyL0qMjs"
    "i7ascWYbQ9GKyTZp+q2oaYLBvWOzOw7qpz8MCV8lkPdWFutOgLu/6/g5LYZGU2tl6WZi1AxxJ+JApo+rmeY0NR1nXhYo4ZmDmEMO4WMuV1VUOW"
    "KXRXI/F3Wy4j4s0jOW1n1dbpJ9g+pBQF8F08pf79fkG5JxmCjR2F5dcuoxE0Ghex9DSKCYSvbpqvYNkDgqopU6MI+S9rFG8ieJ/la2xB0nv9uz"
    "6n2hwoQ9UjJA48riGPuNeO4JoMv9g51TvSrRgm+91XPbLBBVyYKATK+fdDilANWH0F4eZVX4mSY4Or5sJklqb8+hh7FhLkOnk89XfxyJ6QFGwl"
    "31nchwOb/Pi7KwP7LqT+QIP0dS5LfEaf5mXj5RjtXfLQwpg4Tc+3xlrdVAiTdtuffWKVBwkuRfI1huaWgoLmnxezqYVz2s9Jen7Zrzqijj6T29"
    "0XpBHuGaVZlA8lZKdLvfdcj72ELglyYjRoO8uHAaRCmtHTQGDNN/xc11DlOP0+hF173ClocugCD3XDh/lFJKA0ZHSk5Zva9uREVwMoZIiq0IEV"
    "t5eMCJrNKkuC/N/gjxUPOPmPTknoXtxtEKX0vfvELTDtqKUWUAz6qTFqHJba6aTRJgkvtjGT5CUEpkoLbeKYo7xtIJw8NvkqkprBga2BJmehck"
    "y5MnyUR2vqcZjHamcuEhgh+A7IajqK23ZR8QjK7jDDEzz/yYqNx7tWzP9LS7bKF0NmC96gGo8uwAYmxBKQXPfiQ3I/RMTo7FMOao3EpjVMrfcw"
    "1IgMNjDHWF3V86Ds+BTFP4VK5t4oyPwMQCpD3hRWZufYXdxYzfhn36ngfh/JMzZI/bTqZk6IVLrfpUduJEr8SKL5VL9HLUJt+AqLfqQ56jb9OF"
    "W7TQhTKHTKd7aiB36cDdZmTQO5S6TUP1qECaskm51k8n7olmo+3NgGFXfGoiK9FkA0nnHPWJytsfv+PWrQaoqFG2MrpqRIE4iNeNzFuUKs6fvb"
    "K8pABJ5GUyEx4t0eSFAbHA4sK9a5jPeqC6vMI4I6kkZOQ2eI8FirjKCeGKWwRrg2DlRpTz0W2klthDOSfJ4oq/HHWVT/9za96nTJIsHhd8K805"
    "Vm0Mr54AqbcEzdHQff8vV9FD0tnxF5lkNeT8AK57R4gjhIA8fKsHFHdy2KEiQskmNYl6h1AG6evE20AcAo5QK+bNvFrqMY5RqopKtVFYInVBP7"
    "1ZIHyAt/7etcT9qKQK1LK68dm8Z6yiUfrmtGqcRBzNVoqOD2CGVpjaLK7CTQDjHke0dXvfvnuPgiU267H10THWUGy5DhgbETIZh/D7MDjiBaQp"
    "R9APInaKY+u7e9WXQGa1jP9BvF1IvPCpNfbXKIJqknUW3wZcatScELUdFcouiJM6K+qc1F2qjhaoIJNDFBFWs8M7WGnoA9KQMqAs65Cn7WY9Zs"
    "jSTGbD5RaAnz92Qky5wQxb5rw7E9FDY9wwDllqj5OUzBlK6JMyV+iCDIJfNPqeM7y4DKTm6FXa+QdWECV9n1+MYJeLeXEtqpbEwKvD9bPn7ynU"
    "+m5YXwSKMV7tZznwIvqtGTRgMcfXtmGk2WzZ/XldSlOGCYHHKWvIAhmEN4naEyoCySnMTkV0CEyCnkLrpY8JgvJCVxtZ6Xpbq1te29VFVjx5zT"
    "ImYpMHW/S5QUOs4mGEQQ+UR2ACrRYNPwVuuvYc1xp1km6Q7SdplaHFlDW3140SGEZrP6sSeScPz2L+0rPEiV3zFwKtqsrDeRKWLxthUQbdcrmG"
    "tM9WcKDgkl/l04kNYVp95eOg9lMI11i8InMcqMgDsRu/0Zbe6eQn2cp/caQLQVYc1+POqLfexbz03GMXiCrpwkJhxhQPJnKykpw8tIXVj32lLo"
    "rxjkypxIp5cJi1HfWziX5kPKrj+hZBkeiXDGmIt52n83vAfksrveTG/rnuDF4ES476ECvSQ5zlprVoUIuPCt5j4czrI+U7TvI84Sc8Jd9clMSx"
    "EcuIEuAv1cDd2xn7raD4oj4kLoCclAiK6GNHg2nO8h4IYd+5t7HUXHh3byRfoLzzlPOOvA7ha5k9OXiMvFHbny/Mx7TxXN7hIj5foBHdxSCsua"
    "8Ei1o+VkDUlKI9K/t/AAdJSMa8FO1IAnIuu8hcHxd6zKpJ6VeH4h8nx6FU/WAvDS2yowIyu6OWkXTqVELA40DX4xVldV2eMnS3A+hdOUx2lLMq"
    "xG0PiykV41mRZaaq4nSxb3puFu/MJrGaTXWANaqZSYPGJLc3ZwK69uTcB46+5YzlHPAgD0CrqUoYs6ki/zLd5hogOW3F6WT9cw10U/+a49ec7w"
    "u+0u9QjdRcaMZOHFCvbofT3KCHgPyenVFe94F0LKFxcpaGzSkxZu8SFtth/GFlp/55DMOKgurhK5EznDfWQ71ymdJkz/P52RcQyCw1UbTh+kCI"
    "fWkKblFWaia8R07SHYXygW2PJPcKh5NUFhY2AWoYgpya0T7oDtVryV/M8p0XCKWQBdI2E6nCJT7U9VKbf0aIVFWt38e73sQ4NyAgSlYQoY0jM6"
    "ACpkY5cYxtJmKQy2McUJkgkarZpGFufml9FbWl2pTWi6kdSM+45RncChLyuioGwivtlRneYjk9hHRd0ZVVni+GnPeuHLxkH2bRWTtTOylebBiX"
    "HAtGtdrl6q5m6U0Xtm6G0+r4pQhCqcmKCd1hXgOeBcobGNex0oCrIo9wKodhqLCOrdwEQz/KWSadB7rT7CSYBwuxXkgsXj9HNywMOFWToMl2PV"
    "7ln46RKoHZp6nENNWDKPqDhlI8K+KO9skC9VkVGusoNdWCTv04aXzVT++ZobF5gzOmqTd5fPfeWDs10xmXkRFPf/d3OjroxdvmuKCBTcqGL3dN"
    "GAdfDYwUnZkJZPhpVl8uNVMX2zZ4mEBXSQRQvGisxi+8R0kf0wfuK524QWzD03K9kD2kyBdaa6CKfhagDSIJDxjWhU/KKZLoxd1Ppd0g9Dvr+q"
    "LNusd2zB/zdMfdxjekbuUY1/BxMRVnr3lV8Sk8il3lmkjpQfE4P47OYxUUL8GAbPMJBWD6mlPpblKeIlVNgk3rf1ltYqqar8IYL3UaRSBKa4dF"
    "ZY7MeCaYtAWm0e2io2kZX6MfS3tEh/CATQvUA56IsOBl2/fg4iBFIuQfslNfb+Nq0pke6Z68x2Z72GNMHkdfT19TNT6/w3SBBkSIOjpLGYbn8Q"
    "0iYKQ/fd2PXnF2d5sbmEP0OkXqMpzQzZH6oAfS2rd+vUVLK+C7PSjMqXioAJZRnER7/JrAXnL1nY4Q9VSYPzpYhMsbvwhRnhxin8fwgl7g8t9P"
    "CTkp83+yNa07+I1jmUY0V77PekmSTUrIuYDQynTUs4n/9Fk6kx6Na+YfXubGsF5sT34oBSlw4egoF7o+ZNVjkcXFQuchdvk9jcZbuzcZkUDDp6"
    "igONaltB9JucZvN7EjUbq/A8kAT9dd5ZPcLmsad8T9BfgqESEFEB33HWcym/9sAPmDLDeVQusJ2uR9nQ4595Q2bAyqTregHswtsUpnvnsMro39"
    "1wQmj3fVrDEENYH3NCkY4pRYehYmPkQYazAQMjB+rSLcMKcnfEVyBBxKG2FoW25Lqz26U3xaqlz8/TPR09tI2StVtGqFeKgMayWkX/cB86XDEY"
    "mtRs1lNJyffXuii/s5i2gUdcygvp4N0lsa5a1jPBg8c552BgywT0bNUBX+y9X0wPDzB6pyw//9HcsGXABGItVMEVi6kTDv/VEX4sqLHPRMVXBh"
    "XrGtekCbk1WlaTxNYxU2AXxZJP7t4QXMf6B34eQ+V4BdhjgPCZBx6We7OlgGdZx8Tv474/5GxDZ8UcAN0ddn7NL+3LsEpdqMFaw0E4DvPmOJmp"
    "C8bofPdTjhRKQxPhtkwk/3hm9qUDNPMEFYTJDF3ht1nY09kkWweAvQg7tnWZU5lCrC96swVk5L0pLpX6X+chnHfVvT+HSdn+BIb1t2c/euc4YB"
    "fWBDBaY1m0yDjYfN+g7VJh4OZZpx4Cj3OWWByTQp0RrGrtfDh/Wdb+q827+Jzh3IzTzLk+3JIrJ4cynawODKa3Pqwxh9HSy9VO6O0l7pfsDpIe"
    "Rh4ny6HsETFORArRyY5KKEUNTAxHKSezBwU8I6kgzSC+TKdImgMlnyqne8VjxnW5WIs8QWJIaJkA2jQIoxBf3NGfZCaKfeSDulEBhoWzk8pEc5"
    "TQzUJfgswuPePR+tM6gvhh/aNM9L+zNPef0YOnnCKPYPmulW6uLNFtQGCqkvl6K4EtxGTdzVvx868XM9itthPgRruzVhDKI79L5aUOxob5nBvg"
    "m9wugYJ0nsErO7tNJ7lBFKD5g8f7UYpJKUbZCxOl77vDYcwOkhSjKWLc/prrQdp1UHEFO6YZXSEv2wqGf1UYT0R6iJ9V8qeq3XsMnlvye+LHEt"
    "wOCDCc0UpwzrnjtrJXKvK9jYfYG+BHhiuDkkZBhzkicRNQYBxvlvXP8q2KsGA2flfsOS0h/VXmLlulRB6oBqesW+CFJxsou6GCxH2lBo9b5oRa"
    "Fe2oUiOmhzC8nlLv5csfyDGCf7ZFAbq85OXJrH/SYnHJhQvUaHXNmgzYCR7XY+b/gMIoLf2Pg7BcuLXfHLZzTcp7Lb9R9rucFEMwgh1S5ekCG9"
    "oAatXLhzT5RndaHUWcbv8u9OFyw0g70J9JHbpXjnT7sis02GIKloOpz2TfNkZLW1sCEY5dazsGP/fagY/LOKjidVkw//bmBUbKnNQmC/xy9R8C"
    "RFa0uL5nEOYO0gXKnLqHst0ceNORd1SSV+Rxx6mS0GL9rljMwY/vBm2h0XLn1rnogYlBLj57Bhngdp7f7NlplyXkTFcKowB3xTxMvWZ7Df531i"
    "eveybBvtyCR81cfx617bB8ijvGINSky0qgDymOVFo2u7sGFXcId7h7H6f5S/FOmQsVXyhtEYKXg3807etaLRrDf3P0laCcHk4w7UvZvO3Xi1e2"
    "3Cmkcxy7PEt78v/pRAY533amk6/5KFiq41rT0U6O/+qSJkNfqtrBPFZ6GpmuTg29bgclo+EE9GawO5zIMd7I0es+QNOFgDDzlZi63Fi0kpQ4nm"
    "y8QerG4vA2aQcMmvspx+ZGTNKPoR49rD10YFp9Z35wnjAvNQD51mghJve1lUlYj8ej7teTGcq+2dzHnbTfaMO7/FhWrbxgoVwWJYv4fZMpsnDS"
    "+ZlCwIaVtIgQWLcsDqsAqwNIeZX0aZkdQNnP5x9zQGMUQ3RG2nrqgNLROnTAM7lgVH/z0DLtenx8sGe8TYanFf0xcCm8aa1yRlYOD9H4rLAUyB"
    "3vkBHjrGsza1gS+b72zCTMfGaRgaUbQHb5tEYkA8iCtjD0sdU0Qoa5OVxRFKCen9HpdO9yEMcGsdOHLkL6dVvOB7Zb1TVc+scB1nEK+HHVwfk9"
    "XxVjRVdKxnAmX5wttpa6ke1G0MSMf2yh2bIShMBsY16LXuTHn5EQtBSOAaJPKhQKF3qQbM0uDsfH5oOS2AgpMOTYsUuyhe0U94ZbJA/MDsCGSn"
    "tmJCTx60c8MgzGBzOAArVQ+sshet6WmE3/zUSH7k/j7LciBde1zS13YeMBzymqrqcAFhJDToFxS+U9QKa1aWR/ILzPexjlu2O6AJVtPQntAHtu"
    "F/WQqIa99fH53dTFUc1QK8/oGXmgCMY3u6OEVaz7dshBaC53auHhlzh0kZcN1VyPPA4wV5tSI9QVqMMCJUsgaRPDHgYDQEyjsqjnE7x1N19WZW"
    "xokTEYVgvx0XFNdegE76+/akyamh7Lclmy4pSQe7k4bkgLSkVaYFpnxRUEDehDk04l0W0exdnC2n1/j9wmo15VxNtNjwSuhQOyA8lmaYR1vYxs"
    "FHDh3Nw/iY7XEqPcNr5NljuR8HNYCmDL5qraKYYguQ3QxYZKarkyhiTFhNtD/r5Tk0cRI01GT9G3aomRgag5NjN+r/Dl72onkKVAlZJHhXlh9u"
    "Go0ajaBQamkRHwd1/zEVMcFrX5gUw5/sf9Df0aK+zM4u3wEkpN4edU6YP4AD+uLfeEUvMS7u9U8mbQxolzxfnc6NTThhMTYbLsccSHlH070TKf"
    "l4RLWE9a2iF0YFao7gd3NAKz/qlEyBd30Dg06eqRiZIzEeJtyPc9NueN9qZYQ1ewHDYqkMCToZWLS/8bKAbBGluJNaATuPV1egYt956RyBU90B"
    "W0C2zB8JhnJ/OqUAQliOarQYPjVGZhIt533iLzHO/wSNqoCH3FcL2/XQntTfxWW60wTOcD3lf3QRS45A8fFYbI9FzgvTaiUtpzv+OIxNB/CGs4"
    "k+iVUAmRsI9L49PBLjfgkTGQ1xR0Lc8xqRIT/i8CSst9xq/09dvxTt++niRhJKtHCNqgYpG5UpcXe8FGSYnOMS3b4VbDVO+0dxpe1nYNmrFasC"
    "JMH0uNpqda6upRSfzPyKu4wSc+k0rSE9o1fhqJp+r3CKJY8nMTaD3T7FnrrMAqZEsDDv88oGZUMWNWwr6z2kcAO+hZg+l5ZOTTXpC6I52lNzu9"
    "/whnqyKRXzGwzAdZiRDRjz7yNPZOtSEjJdyIJuX3lkg6hD/MD/gym6ZKfDvXjQxXDuBVYq+9rfZNX7BWC03+QPCVonaOsgf2LEqwDjnrqNWPkA"
    "fJSImcat64N+Nk4ukbamZA44eYTjUA48UevkU3BLx32e1CPyM9qZzNc2DHu7u19P2GYwHTePRDgVULH9Dq5/GBmpX0b/1AAt+cEJ3RUm61Hkua"
    "5g4BzxOZXGW7olQ2M9TJzfMYcnCxYB8y6pmPTyZZ1sa8VT5omKlLh0ULXlFqIn0sLznRUWNIHVIk1xLk99yRIJRP8d3Q2Jz38VJ823j2SbeEu4"
    "+feDMpdswTp58a0psJ4p4e7g5qiPTwArbXIXp1KtRBCLSg7Wf9QEOqnMgqvbIXiExEHiSATrY1dxmN90R512t/oQ+hv6bdErX6kCRORe/PitIH"
    "pw8Z/pne90g/Wnsy9hoQqHNlTfbjbb5nAd40X6EeUmAng8wB1/adG23Soxmkgf5Jg3XVB78+EGx9psgkV70Lv+bdDFt+LwYgKzFGqSGh9oL9vS"
    "pvQBS5QuWJIlziGn4dF8r+tsib4DmKdYQjmcIUZray99U25kVpImY3ApJvxJ5RI/vVmeRqPgRXYLcJGNCh220FpNbqfOIoL7xe7vSqUBxV6Nhv"
    "YC+DdRg9AFtNPWL8mziKRCp1SqbAP+2jf1pCQRfdN6l5UIRR9mXL2Q8nx4imDHAUoOTl4+c6nsdnW1oGa4EYecM4rOuNP5w/61HSvPNeFgou5x"
    "6JyYEfnzKmxHjObNc4iPv2Il5rh9dtEnhxyUtulHaSoinVk0mTOlV21Icyq0McYCov4vCiJOQIVvnfWoyiZMFu8cf/KewFlqed5LAl6KyMJWAM"
    "kKaadPGtUKkJVR/I115DjJfJzLo/kYqrExxQElE2cr75ZCZKaL8DhDj76bWOJtW2zoQNja1jxyROItGAU3x8aQIwhiK/lkfR3+jshH2vqoRqnz"
    "2ug1sfLo56qNE2LWYyKBIPjl11nEkZ92T3fFxLDqh7saP+OJbc4d7aMfHzDzBxk//NjtRViSQh0g00ygTAiswfPw9oZF0CETR/VxGVZlSXXF9K"
    "jFwchMt7i+PGBU33wU8IsV8t57f3BXTWeH1pCgjGH5yOSiACwwEQDl4JLI4qTQU8RDAFI8k86+1jl81J8M907JKY4QOIOc+maC5NfDEgHRyKuZ"
    "3tt6ed2K+qY5xnqBjxgGFtWHqLIPDgxLe1qbVIVOg8GRDSY1bsG6ENmiuDXNr73O5ThfQdul7bKdPKrwN3HzEu3v7b3TXNTCAUryGeE7Mg7Y9t"
    "F8RCjcgQLMsnAAKQ0UR7yf+vJJLxleV1DgXJRk+3bBRkjClyH+3YYan8wonaKY2kfzDKT7TSoNBZQ5tSGnmBHEpXd9th583b4QJJPU4ve1UbbR"
    "EYGge5rlz6TdqnVpDPu+OJ/o0RG1v4vvbUsgX2TPfsloZ/qspr6veyEEShMxTYPZ5HMDC105xLrF7PS4dhWjjvv670/Tnl7J/QHsoojLz+y0DD"
    "+VIiozgI3BdECh/PMsiGocqHftVwy8+x/U7OstJsimthQe9kSsIPgH/bexUl+6s58eXMMAqWc3vwdvk3L/PTr3ixL92SYhsxLyVgynkwrJipUj"
    "cP1jxYirrYyRfLCiWgNSlSUhoNQVOpRB6u9vT15eD1FfoAu39p1QqecUxRnromgHFRPH1WFm7RkvzRodk2e6nAddNgJWWQGeCTb35NMgpHYFK+"
    "NnbVo67X4ziv9Zc/UuSfBu/e2Pz9EnaGcepTnAJ4nSfKMifm1bbX9J/lMcbv2H8WAU+jCZxupxAno8GEwkS9+OFE14gJE2Sp4UwP/dixjl6mm8"
    "u35hvX7NgcjtrCJEcz+e7VfsX3x1jj6kXqIXqa0EwPsCd0ORHhigxxfGMPv/weLOaYhG7QRvIcyo5j2P76SpTRjP3FMVPY263SsbF6NfGUNQJX"
    "QCgoxOmhJkykg0IfCbhxyMdu1zrmqMgaZHA7RcgxokNKhVTJ72UsaaYjjQ2m8LujtKK12XhUzwjtAsA0X3Z2hwBp7H7AIb5WG5470+J6qZHZ8e"
    "xCmzxFtslDPBldg88DEpL5kqYCjTarQ5txzvj3tSu3Da3Tl/XQuSAv2ZGRkc7dLtOwjllXlTRSzvq1SO57y42IPuoS0WeMOEKGJCGLmduxvR+t"
    "WZfoOCfNZJXuV86eUpnIW8kdxpaihP1UZlOdhibHy/kSxhrjzaNBz+63FjTQ/cdLYpWTHxswvFGW4oSNAyQjHvgZEsU5JMyfB6fach+4frG2Oh"
    "pog19cl62Md1stk1Z1ppk8aR4JNX+fk4TlfG7JioN3IEjgVSNk5kmyEBt+3w2GhA8wdHRIMf1vJ9k9S8ZG6eupdr7j9vH5h9HA+Das/Kqzv7Oc"
    "bD9EBwr/+ix78uEf41gHkPGpn3etLrCsiwNnM82rh+e5zpb9MRp52XMt2oFUfUPAwJinDEeTblAWW5lCGzU7Tp91+GOZcaNTgI4Iwn67+21rNR"
    "cSKZZkVEqXdiYR75OMqQbnFu1Ow5QomxcKpk9W/RzQKK3XU7lOe7ads/U+rBHUc04Q1BglA+UQ/lCxfT+eZmQ6IXvGYUcxyQrL6iw+eg1mhG7L"
    "W67OUx+cA/AkZfV671jL/qjm1WGAjWl2hzJBQu+lLQMeHigIC5WOfDk9/sJDfmprT20BYqjyckYXutdKM0w5VxhRWn+IyLUg206Tkwr7Rt2b9d"
    "8xskvQn+yPmgTWjyIrvsSQjXTwqF1jJAL1j0iiCQMZ9aIpA0jvaZZl+bfnnCVMhLwnBPyQO1yVmNyuE6G8hLx/q0AvqB/OqXolQ1u+dkq+GCT3"
    "uVI5GPrB583XxgyweouUScVd6MsHnrQdGIVOzrKGMzLQlFV47k00I20VtRaSuOLH0IoGL2pU4+kPP0NO+xVikHHsPoSr6dSMBMpjsfWrJcxADn"
    "i8viyc7opVhq8IEwQ+xGZL6JejpJvyXi1/kHJHxunIQhUMl6RRvEWtp1N75wqG9dTx1zx0EJHOBYmFd5E/Dpo5jaPduEtkN/l3Iy85dXvnY1il"
    "7aOP91nq8/QvnY3xYK+p+UTo8Zu/01EKhJlCiq4LOAoEoLVeoazLmSTHPrPGsNPBTxD/mwhxiA9FHctiwtlBhk8FRjQo6pTGpgFya7h8Cmds/r"
    "RukS+P5P7Uk64YWRPpcohkpNwU921yRtZDx7uciSB9OxP80ulSafZP1RKcFjSTCM+vtVu81scEn3lioKJNM6xcEF5vqCXr0StefXodMhjdog5R"
    "FjcfMzPVeiGKMFKGL6aSk88QhEnpCuTf8qNxJdK3v+1LZkQtHA3Dpvv4SnNqPq3fnWHg/r8HDwWRS5lI7WfKg9VFuy1RU4frICX2HeJqtEId7R"
    "0R8HvufdaPUCLv0GbjrBLiQM9XTGbHzSQZ1rvS66RNlWtJVSObYt54FvgFfNwx2r/PhM+YrKeY0laPJF32V8l2v6I6Dpwqt7S4sO1Xmz/1JJ2Q"
    "1uii5stwEhViOOcXvmDpcFqIJxe02i866XSt9F7KmVqhCeXLDeYde+xnnEpgQuPKtoVM3Lc2XD1hYKUhoKsE9lpJndWUY3N6Ipt0heHAPi5iUq"
    "VrI2fo6s8JMUr4zv5cLi/C2XHPa8PYQV2f656UDnvVmlzugyjgq+vH2hxTBFgrJnm3ANx0AegDPH2RBwj8TyNHJFQo+xfmEHEcaV7+VoXul4BO"
    "6b6SeBt1oCsAzKXHKLD5pHv5eq4RJ0H1H1ZiFWD1cqJEqMb47AVn3QTquzMAtdkiQt2Vpnsx2vCwgSufDrlHCQlwAaw80bKL0Ii2onm68pY7IY"
    "FOtsdVvLL0ts+bY9c9uc2AS0dUKWLc5TgySdaC7ZArG9m8dPqN+0Yh4wdJUq87GU3WgAM5kAXjPLvd5dUad4t8slX0kPMkwH8Bu84fDFxVBuol"
    "IjRKuBX1ysieosUyB3Ne6wdSr9lldvr2t9EcfwUdBHzkcYr4EaaUwzPq3lAYiua0m9/gcFyQNLI/EIpDsJaZQolge2Scwt0PgieJ/EQ8+YsaPS"
    "KMk8PpyiwIDs9z/2i24Add0u59zZ5qYVYGOMN9uCn97r+KauTJ3JWe8aYhl47H29gLSpry8faZL4003wSR/KvxH5G+E/pU6fTbKFy8aVvusxpD"
    "ourWmcZp+lXJO54O57f3plXDxpN6Or6Oe8WgLEw5mj/axqf5eoVmP/Yhc5B3OOTAhURK9MMdMfodhNyCyHCdURTpi0pDsAdRgp6uMbUevSPp1h"
    "DDIvGUFLRYS0bJkvqKFkTbkSTYkJkOxnb6oci2cA5evAQx8gY3cOZhwE89KwX+912aOPFHDOmhcVxA1NxTq3i6ISXRHgdPC7gT7GA2XPJ8sIGH"
    "XBnv5InZooEe6WdQ99Yh0Cyzjg/2LXlKET4YTRAuXZhfYrntfHfEVpZTGeoLiSKwMPyAEKQMMUrcGv/bhuVnq24oSbHUlC3rTDJpYJM9FaN31b"
    "bzQLGHVdiUUQitrVciITgBrzvmOuP04ALtr8hO0b99ASoJUhcVkKCgpX/afjOji6C6I2NXUrJDXV9nQGtdAv0K/hF4hRf40aWmVcwHQtbKErVW"
    "yoXlADVxPE7oY4LtJiGBwsPxkB+HIG63JRc+mSzyYrXQxfWQF2LEar2B9DaLf9E3s2vXdHpsvzT6xQG9wNLe5sfUWWhVRHnOs4XoaHkmybEETl"
    "cGGfZMvfV+b0p05FhepcDLeAA5KyORu0nWFDaWeQ43Nb5/7TRFvJ/9Dlvdm5vIaPlj0fPim6/COanowUSDgQaNHDLXDZl9vbmWhPZbfqrWFNVV"
    "WQVT+6AS+WaNzvA4868987RgY+OBVc3/WRy50P8jrGdUOZY72IDPcXs1Qsc3X/DCVtiSWn0j7yMIVoFecaUWQ2tJ/ziHUD6MT851/POYZIcjC5"
    "uCK9OcQA7a2+CE/gFVHopwl1T5vURCgJuAC+qtOeUa8Ic8z9wuMITNd/EUvmZdfSM5+r59wqfYV5JWfWQgQ22V1uPrbQ9aOzKBWqGg2GMnV9up"
    "FPkJzmY77MKqPPR9QG5R4fBa3xkvERdUt9ekJ2js80Flctc7hXONX2OKJekCnii1x531H24o+dLVogNgj9exlnzbR9ZPD/8maXOCm6kvHpoP1c"
    "wYqxopfZMq2TD6zlTeTZv236m+EeIIOBqtRa3GDBn2UJbGvK4xR9dapYoYKq5wOYbwCAqrShLUhMGd8kRNIprHL+srDj84EJgyvCQtatdqa4qs"
    "rs1D7vyc6jux9fM72Sep9EC51sQ5zh57y/1L7vMyRmUChdla8U1Tw0/UdEkQvee6aZ6vGHsUuBLccJR4Qo03gqbsA0hHIqP19/inkcr663vINe"
    "rSwZKbZxSB1QrvOR8Ct1g/PWMSu2VvVFflpnUDxeV+zOK00ZNKbk6e/hU2IG2vFnxlHlzCQI5g8Rq24wvRsJGG3OUCyCccciJSZlDC0DW/OhXP"
    "E3LI8D859HD7sn0SFGHsOKgzFiCJRT+FGxsIcl6UztvtJVlXmKF8IJ7GSU42ojBZnb32XayRiKSJzl5sYUqishdZXBz9KkCemOQh4SvZVkP75H"
    "ByLSbnTqaxL2lNL1nDCD8c+jKauQk4cXgTAy2D3kU2PONGMgt3P2zqSu8IKx0R/Is/Johafxb77f9IYc09m4NA+oHRM+62Wc9XsZU5K3Vz7UR/"
    "h005LDLiMwBaZQWF7cL2gjSZSOVvpTerDgIJK+YkU/Z0n6qxVq7zIW0h7p1WdIZdfrhW71jawLkb1ORPivP+eJKTPsFpD+sdIrYpR0dZplsj1N"
    "GpRmgxu7tFG3ocukAPzrdDmvluZ3h82Q4FAZa8HAiTvmdAxdWtDxM0M4MNIhmYPRvVWXPkRYFAkKuU9qYFvL76L8Z2q68Ez9mTPIKD2S4uYxY7"
    "ck2+II4yfBGCocJzw84jA8xpmqV4xl/VvSXMy7yDh5fPU9ScfaRZxrdgN6ktuzsyKZQyCzQEe7WwSHw2vXZV25Duv29V5PAvwO0zzfZtPhMzNU"
    "D+8+GKNCADs8IUcvxl7QE4mOj7MhxU4xpDEwmg4haXHjzfFYMorXvEIJaf3t4iJBTTovKK7VpKEBJfWcL4StscbonDB6/ZJFyCtZuGoxMMYXEV"
    "LHBNspMqcefocLmiuMyxKeRnRpUIp0eIceF2WoRliDdt8Nlgi5L733bbvmOmR9m+Jrl5gv8VW78mi5J81Gc5h6ZUqakOyGty6drx+YGeAsg1gP"
    "8uYUUOK9Rmi9kRxwDTEusDqrRU57/3sAv+AAlHsoaOg3uZYbzSA40nR5QlprUdHDoJuOjLhAPR3u6jGRMD1EKyMi4YLtF875mEUVYJGg0WVR9n"
    "k9mDhN9DI3UsvudyuMmbK8qZKj76h8l6DbtLo8hTepOQ6FW87D618XNkGAB8k0gVhq0yo8q/Be0jqrAD1JBZLeRiN/kympL57P4/Bp8+UC6M34"
    "n1KudH189xuYOX9sahUKrf3SoL1XQLPwI3y3Tsr1JhMnM8fy6Xt6aU5zmWqlIpxNbjP4yxdXDwnLfjLX2uRapNKSe+VE9MDkO76H+Q/YsAN/+S"
    "CQcf+ckmC3CiAQmvGZMO6KKEx6XrkZ2t64jRUFhMm5BW51eghG+mL+W1vUdPtrF9s6xGz1zsvn9e+n2x3seLPzCWEcwCYprgkNPghqP33fBbO+"
    "ICQg5bvbzzt/wG1qSbWzR8tzJfErMa3WwAouB+OQNrJ08f8DIZsXt0CddM4HZG03CNqJjf/oXnDNEx8VooTdRQgdmB5GzJIjDVUPReQW902ooo"
    "2pemkgqzGAyDLBtaTJ/3GT70O5cqbpNg3ZGExwDG5un7Wl+3YqH7ITqIE4SD3r84LWTRhf5rwNIce72lwop+9uQ8c3JY/vaw/hzjmuoUJwkKQM"
    "YcPcsbqUU8jAxR39jp03eyiz2P34KyqA8xpitEZ4wGNlK2F1X74aYO+Lqu4K0FlylOU1WNDCcuQ7vP8ktWJd+CYTyUUmdCwL7Z00vK9iNQKhM6"
    "cRbpxwo+k0HI6Yg5X4OXkiqfsRZl5Ga4T83AoKQwc1hevkLALREtaEo2RmVyaCWKhAncDA+3P0mP3/Qf+tOmp6lZWehPymZ80nxjEndcr01VC2"
    "DbZHKibV795MD6mTcWatx1q+OzZdPta957Tgh+2pKAlYwhSKANb4Mo/u6YyXyE0PDYtIkLUxJyjB0ZYar8R0K7sHzo3OmO96WllDumT0c7Fpuq"
    "HbNb8pgetNePcfuR2ZutseRtfYs2ud05kAQS+ycuc2iukCNHQIk1Z+nBJ7LxTv6+ReeAoiHQ8XVR82JGonbs01Mn9gpeec2MtiGVgqEF1qZG4x"
    "xmKBMiTSgCy2oJkV0XPtUaWLkuiB9Wq/XFdb7A0Dgv9gUHjdpuf/GYy2U0meFwKxYoKN4tlRzYcq6gTPgzcETfPNQMLBEcwfCWPE5GKIJUMrYq"
    "QfkuPZMas9WodgKTxAFhtSAIx5/9A5joySjPFTyivS4fSMOsVeGJDQgqgs1DVPQ2Qrm+6z/Qjwbudi2/EPnd89AW3GbEOovIlybH8dxfeAXchU"
    "y+UYVGtH2qk2mZyvJu0eGPG/4/pU+XhIiKvelaAYHgl/CljFOlTCpBNHI6jm9u+PZ6At+msA3iTfsChZ6JbV0K93wc1Hh8Peg7xsvB67q/k43T"
    "AdU3iE8QqXxp0a59y3OuSTmYlih6ssYFZ8yILaUwe2lDNuNtM+V3tYzYqSHdPoTdOksREXT7y+kjeViC8LLyfpD74bELOfuQ7hQF3qyBqlXOYT"
    "/HyURChypscp7cEKqi210nByPfCUFJdP0UaDD8aCLnZlZEH5qKCxtz3RLy5G7RUGK0YDwgf0iIJQs7yfDbD3w6qUIeseHqIOP9Bp0euuD0sdbL"
    "kOsjsoFNbHObUUzHRhxfBgdyfoRBF1BxsxfQSwlCwaX9kfnIEv4eBM7EnGVBlpgL6eMdMXFCOcO65jNsOT+/Qd7QZOa2RdMs3Bfuly+3Rha/BX"
    "0xDBxTDOHkEEYp7aO+EDNp4dH8f1CLbqc/Bn8ITdGk5ZMUCQxKIODbUnuTKoESZ7wh8YmzbWKKOvXll4XN2fW1lu5r9ByAk+KxBmQ2XWteCAvR"
    "ANq9DkicCeVxRJGQZmTTsos0KRcZu6GC1GH6hXbVK5ghGepdJdTAeLs7peMu1h29Wr1Q/WGWr30rTd7YbJfFCNDHnCYAZsDu/8xgaufxcZyF7H"
    "R1TxWehhjXmbcmFdYwRXMB9sAMGn/Seny8+f9iY5WfbPhvTsPxDAWNSbrX225HZePeLcuYFqeGD/5ie+nMfSodyFbBHqhqnB9+DD8MnIQJFeiq"
    "XreDcYS6yCYFkUssTv/0refA7krFXR2m61jPOUY+VOgQvpmRnhm+rnEXgq+s6tPWHRmYznpiR+2wdR9uaPsZGx7BmVGd5vTS7Tqm8BEFP1F8ys"
    "3QkO/jNQvt6jTcRfEBszasxo/A3H2DUXcjrIJH24Qkckn1A0blQ8ohYiWdjZx5N/Pimji+c5gmGiaQbHTKK2RBxk6BfcM+xlEr6FW/V/yzEwmD"
    "fuOpu2UfGJDIElHZSJmXpWYvcogfw5f8dLoNk0jZ8Jb6VV1Tm1n4HyNMj5b9i4szJOEBt6IBII2pLiHKKtWoYrrXjCchJqPGfT+FL9ZCGdEZgM"
    "xej2TYGTEdnPyGeRKf8TmrtYvP8cQ56O3EZLeSySQaK1Bu7YzKLdOHeM8ketYd44IBpbQ57M2kGb3G5ButEdg/N0kT/NgfBGg1pHh7j04h8GLA"
    "WOQLKNp3+ehPiJbVqgerx7a8eR5JMpJ1XArE5lI/gZFBYq0hMWo5k5518l6By1tsbbgokSHQTlNOk9IcqrbZIIvzdbLb6n/Av+n8yK8QyJdKX+"
    "mjb8xZJxYOZU7NQG1GmCCHX53HF4xHD8PUku4qjwvRRKHn2rAL8XvPoakQcDyZPKR4b5GxX6nMTfL1gTk7ceKfmzV0W0w1R8WTieFjGkCV4hvW"
    "cYRGQpjVPc4vMhja5UgZ8bPI+Po5sd5MFv1Fe0BRY3HxSFJRXD62KUtlcp5nxo2Whbp4BbVXv7jyR/XoImUhuZhGraY85WGY00PhgjE9yv6TTT"
    "FI/QR4WmIYrW5lnWs0Yp3wlRR9DJnZbE/qENELYeS7nr0GG/eAqinmdnqYRjE6Rj+MKAN9bpsS9oGXKEB1eqAqpJ2NmkbY1Ddd8LJp9rho9SbX"
    "/9xdbHDaB/vx4ajiAQE4+DJ1tgb0B5nMJEGMWKwJT1Tq88nQeQ3lRkzI5k6KRNCEqalYjyg3q1AJ77fcG9HNfq3tXPAmKoujRas3Rb1WNivb+8"
    "vdMhE3NKOR/uD6Jb5mPBIsrFqXn3t+9VKSqdIY6OqygJSdml2+lTcs8CryiFNpW5K3b/xgy19Qbis5DHacIqGeq3mfdKWNcEdZ0JrqFOlQ1DZI"
    "Gm64L6oNG4QxCX0vkiRc1PAE6EGZyG0Z37c0B6kqYd+J9ksHK3ZLR7PQDNvuA6GQGRkd7YH0/w8GftTunV80l8ynEZEptzHFtgBU9j6uGLX2Gh"
    "hG80uAx09De6cKw9hVrnMeNvm8AuyaJ/+NUNX2blJjXsP4QaG6Ieh8eAzk53OMn50XbdnV/kRAiGEkLj6Vb+uz+u7mHN9nSvMFevzj/AIk13xg"
    "AeM5Kkttyriz9VkVLMQpWvgZ8PnaIcfxZJswmlpl6q77tptWZrXsW+ilRMYgz1QDzQ0WVyI3iJRF8IH2EGKOQukLpd2czUsD0cDOUYxs4+Zlln"
    "uUjTbNwc75fu8jumROiYogGYH4CT66bk95pZALZju7kx6mKjV/XrP9Hg+JGV70MMF1TMN+dxp8LzIaMY+ZO3w35jMIqCRpO+FGsgJbjBAmb75v"
    "0t9FGMUTMTJZtwhTsASxwzvqHYe4fIAs7Hos0kH5+DhZQsg7zNRKx06IR98boOrbGsTZ8CC7Vcpmj73Y2wlAgEQl+CPM7NWGEzeh1d7fFLJn82"
    "hL+eDwOp+34FZd/1PfLGYHiUinmZNooSXuvoXLhXvKn5nyErhy2BlUCEl0fg91TID9ao0Wsbs0rOSr6jnN0NxhDZVA1RN5mea5OCTGHWr28Ycf"
    "m1LMqVFURXjj/y+3rT/e322KfL0+Kd6J3MeIHXN26GdcmsF7d2kEE++bM6Dt41l+59gavQ5Sbx+FAbho+tKCyesi5GAt6ur2KNHeWl4qbvEiDF"
    "G5IreNWYBJtHvdwRohyqF1XTUTb2bckfhVababbGr2iGN+NT2tuQ7ZrENn4Gfm5bcnVEyEADdC/q65aPXbcC70vUt0y4kHj6Hkst3AiBPGuQdD"
    "hfa/244oSN1pPiJa/bFtH6s4nmhvev+JMeY1SKnd/EmH4BvaGJWa6PyoN82Chyd5KZhiBzjBoRoujQX/UF3Mx6INhugo9o3PFbv3Fu1c6v7sb8"
    "3p7MVzgFEr2uOSVcJrfIKwyTyuKnKveEzldSt39yIFQPju+R3t2JnU4HQn6eCIWi7h/BqLdpai1e7CnFzhqRkJRaJdZW9pf8zSiW8MAhYVVJq0"
    "IK0Tra5WsWGrZXG/znG+y6QwB/tSIapxzp1eNTFSJLlB0GOrraAPBV6+g4j8Q0avPc1uFzE34f4quZf5sejWqu/AQdA4smXlL42vUftDnXKviB"
    "+8u8N1RxximRX2qNytC5jKYgGRRWOfnSgPgp7sP1DjZsoz8MFJusIugn4cs8wVGkvh/Hbm1TMzn7zdkixHuq4e2mjrcLz7Qcq8jdgQL5kRK88H"
    "KYDlVtDqR0i3STEkpEGSxmp64O0btd+NVDk5+kIsucDndjbIFM/eKuurwJiLVdCxbinidrgnd7PE5Zbyr0tkqCbmoL2qYu44mrZYFA69gluSJf"
    "sP3ZlEACcZyNhnsSPdAMN6qWFsI+YqM5GadhyiXk/+erypbuwkpVcVoxX8d4Wi1HLpQCWf+wEAsRPewY20CDZ8gNQZzH4qRm12y7gwfI0p0JgW"
    "oZkpWb8TRgsCiYblHQ+3/YC9OAbZed1RgSP6dyEVDvksxBpVB3jrB9t3wJqrD10HmBG0iE7mNXg5s+JWH9p6MopzerzZ9g3qdLBpeIHtap5u6V"
    "7FJtKhCIFA/Eh26+M8/a5ksRjYCE2PE586OJ68TPUrc68f29pesRiB4zqRd2Ndh4cdw1CZ7eyKLuOA+q18O1hgFN3OYuqTvu+FPYveDcxuR7kZ"
    "bGd4C1at4qrN1/BJEwCUB2W/1ygNpwQcU/TudZeK+64B5ijXkHVdAdcft/le6PTJ+/36zPr9pgApWWromRr+4pkPCE02HHziSBHAD1jYW/KWIV"
    "C2NlLDzIhga5U9BPV1EORy6KFAfMgILlkpuPvbiwL2TbqDHEJMKvOjhFiDLP/6aLyONIzXzKYjCsOFq/AcNaBjsk7Zk4bbkzllLO2dZ0Zl/5/c"
    "DTgHMD7wetuhsvp1opLpWb7oRDvzgtIUj/Cq6bvlCuCH8lX7LM7RP+Ta+vArGV9iprVIhLgsgy6ufYDHg8TSDX2CD4FruuinzZWmUxYx/+6HxL"
    "DOGL1/vSfu90GCScCUGrGWSLeVX4yrKO0/ZIqW4LDScaCr2aRCBSWRxtVzd0ALpTGJR4MyMF8TRGC4bnpnr5kleh8wuIlaAfMyzKcGLs0L+9Yj"
    "WDEzf5ivA9qz3GL7sDLQSsqVRFUYMONXNz11SJ1AK+ZTlxkQpg3ThhVmDJBrp7D5nw+v8php1UaW9i+WpsOVUng6nTOYVWqqi4zqxkqw+3+h2T"
    "MQadFV6bFPDAXeFKlgoXXEuC1p91Mo0RASVk0BhpWgZACISzHutZEKCO+U+9kklV61jpsyoGSh1UftsZnSr0LzDZAyOW1MLulxskClOfQt8JzO"
    "pbSyCQXLXieUrhEaiNQ/pxtx5BWQ9f04l/SKsm2zbLFHO/3ti0nhZep42cQw0RuaR18UKB9t+Ei/ZTQtRnpA2oIALCA6yH/I2pSebmZzIlQHG1"
    "itb5BfCD0UtbUC8noAKf2/+w2ww7MrZY3GMOz8AKMfTpQUSTfZViZWgJAd2za7zRmFhfFaAzm2ZA8oFMelc4xIAF37WbZ9UEzjA9u7aYm3qTSK"
    "7sG94CeVUt52F7v9HUCWYIT9nub/Uwvh4qPAFlAxNFOpZOfxoW4UG5QKGhOR4RAJdCxiR36r1IHYqGdCNpKm6NXoJ+KRZWUVUFdFhX/A4FcxzT"
    "e2UQdqefS+ebjGTLoWCftNBDi5XLHV+9O9YdlJlAham021XT60AyUTMycmhcBgLCvGM/RvB44E6LYaGflnIc6Z2AkqNQfaCIrQDza59UxDrX29"
    "QhYuiXCuWmN+46BfT/w/Y8pUKM+C+sZK7wSyjcuA1WzAVm60Ge+Ie0W36gGw+rUJKIBnwRCRXhVf8/BouuUM49JD/snuTre3xxpiOLvTqBGSnn"
    "S8nhqipQBW8m9xw4pAscGXuFguMiwm7uyfCAy2YpJbcCJM+CDM1vyQOoij8C8OJNzgCWn+IayTI+sXAZ8kZT7lPSwwqzyu8RHEBXfphC4wxKur"
    "3djrGNVaRIyFSISzXG1FMplwcJ8NGymh5F+8nin5j/8QRqJfYL2D3GfFn6kSswNfhMqRqtdIE+SeOKEmHuBrdYQb0gSbVq3v/cD8WeVpR0l0Hn"
    "kpOUhVyqcojZkxw/T2JLjZZPG+FsDZZZdGkHB391bw6k70zVUn5S/PABTKCh9hPwxe0WhLqPnitg1kUaMhF6twC0LAIClKFLMdlfNN7GS/gAhQ"
    "sibQBgjlhugAsg1QESr3VLt+F3HqWimB8PcHUMTsvC3ESF+oTGz4BSzI5qHkLy+/fNdqZlbHIsXaFOccPGLZIHqiMvGCj9pyC83mc64yCm+076"
    "q48L8HS3xt+JmRsRVvYJW30JcrU/tn8aTKhIoEtUK7Q5VG9gFeULFJK+vuoJ7K35Z6O8WDdwlS/D2RahmFKQTSFvVA992rEEJ7SiqUHAJpDNHO"
    "A8f+hbKif0N5vGfQuHJTmzG4uclG4rmI5bGF2ybBiAuDrGCn5VXKxEm16FOmDynpB1axdkMzjCmUBtVvsRECLQlhUEA2HP2UZlqARfHaFmEquA"
    "q69etEmoKSLtWPClwSOxgP1HlouKiifCQSzPC9PblMDH8+39n8Ts5rzG4kettZGxCUtwY1yTs8IKfzPid4DD9efyw7eLCrVFICwgAGRxOw6OG0"
    "WLHagxcZftHVSmYDIgv42R/EbFefGIcjTCPgSD9t4J2KW/uRwn9ctltWFSIsye2r/2hK28RbknqIaq+VTs2gkD766o8COMKVpP72isybWRDCMY"
    "VeA1MAl3Fg56BYR89h57KlER0UtVB2XMT9Ka2Trmx9cmDGVWcydUs85f22zVrRdpvYSez67WTbjfHgdJi16eUDBEobA8YkqfPoVPPlksJNWKfH"
    "sb9w59rkA6WFE4aHQaSxtJS+2exRL2q6xBjZ0/JC3pKBPRLf7P+fO384bGNL8fqqS8bOPWBavOVcK8f4qbdllgvU9e1Fe/MasjWJIeQGujZZo7"
    "1n6m7jvL12otH9HYmFP+E5WstARH2BDGzserkZYCdDbCcZ6TOU8OZRSJzIL4sjdSCDPSY1M1bjsRYftdGvEoTrWkspkyPJpcqGOiMqXXrVFvTZ"
    "kIkDeqc7g98tLEigb/cK+3pIB9pJPkj8iiZzsS6ZfJp5J8OZzedVflOEtQe5gdY2SuShI4fakJVi+ZSzR6lSMH9IOSa96QXjfirM4VcnIgunbv"
    "UFKKLyoE0ZnQFIA4ijLeRIqVMb4VDi6Oc72+2roKxQONYJ10M6nt06yVSaNSZwzmqRVpILKsiyAslIwVcbJwqUAAU4q7ARmStrT9jW/u0FKEJm"
    "D9iHjdJkQ4hXhbD8H4p/PdN93msiD2qA7e+RzqNwau31k3oUd2b5ixk/t+Z3eOVneOoDRzyA936+3KDrTTvelr6fbwtO9lYibuFasouHZBc5Ml"
    "Bt6z6PJXmue+cNHkFnNDdoztMQx8zGuFV/OXFuZnSBIrI6h9ifZUR/9Po6dbbxZbiNXLF+4U89g9umHeJc6LEFpq9diMMUv47GTB8BC2viHQ1q"
    "AsTt06JblL/69//qRlT9oEPn07fBygcui6MkGV/5NU+AFeJPFaLee3ZLWPhEsfJKmCicvt6uCrxtM2jk6/VCI7ZwxJTvXxTRcGUlMyCa1j0Dh8"
    "pjPrzT2D7/GkMZRa9ATOW3FDKK24KqEBAD/ef5o1imMUqTTGiDbiYWBqYPaSOpc5rtLd61xLaVNsKH9bk6kZ+rh7K3xTaY/ltEVxHFj5ypt/vA"
    "rpWEYuYxowZ+yEn2Nxh+XQqKl6zd6fZqH5MjkvGGz7gbmuC71YcVv0F8Yoc2NnGysyB7tHejipElEnLdesRfEKOtopbto11WS26qxTMzI9Irwf"
    "4Sndp4OML7N7h5u+4Hpu3K3+42ZKJnwsBE4lX3F6yF0eTCjmtBTZp2Ci9hSj1Rw3Q37EXGSi7R39/CbOr46xeGAkLrSWN13Re33/jXrmaq43uI"
    "ryi86oJSMuLRj0Fm4iih/gI/vyzhCUyNXDD31Bq3ZoyTJByeAlznBsFHb0ImZC1Oi1E4t8EAa/h1HmLnPt9MFTUWaXcI0OYSzdQrGjkWCoXjOF"
    "wC3hX0S9u32oYqE6EZaIeE+fPtPq/qefMqpC03hCED+lN6QFe74FOkIDOGyl8XeZ/mB0WwZdUPaGrqlpN8WwVB3N8RNtRk1ZTDR7hyuxID8+Ud"
    "XAa0eX9VcppMz5FN8Vm/guwI5jCUEsVEOGH7hJf0DgD4FV/seMbyVbMApQyIW8MmVSXo+3tXmypIsJd16dI+TdQomFm1RgZwO7ciK0Hstvu4Ya"
    "x0Jfyz81IePfuS27tHpyVP5Aj7dVt9iRdJv08uDHXfeApeiaFotXzKjSeFvIXIFNkYP4NpEysvUPQqNTW1tSBBEarX12/k9xTbsGlsdpH+CTiT"
    "cFBNtmkof9J+oJpmS1h6HrH/sPzxDWM+dqI8hihjfUKgIF1Em0WcIweSfDmvAhSl5IUHLOo+KMSt3iplYwnI8OlI9RQCoZZImFXVzdlw5/CntI"
    "0nLVl/IhKSN0OmvLrAz4pK90MkH8X/aW1I0/VbFqtsO7KJaigiWjQpIN0L7wcGUmWY/3cJDbvGqtt0voV1zPZI7YDaOOWeG7xMReutP83P8jfC"
    "btInJAfg9FlGiGkcVEpYC2ZdwAo0S6DHyySYaExb3q1Wc+7ps+sJpRqSQif4OO+wDmp6e9M5DFGsLwRev9hwK08o9nUrc57YPlKasvEnbBjWV5"
    "tMrvD3xfkyPu5/Kc5QtdknQXS0t7Id8qqb5B4IlgnEi68V0LR4PxB+vi8YPmomaoQCE3KWvoTZnhLHBPLA7wPEnFmZoRd4kSDhiAO6cwV+ChZR"
    "Iwi54SfuqOMYPi4bizyNFXh6yHAjp38oQZNX3pB7eXf065IowBzjUTYvJA4gHqxdxIKLxftDkNNLG6+sUtr5o8sGVk4ojY/FxGjbOlJoYEK53W"
    "xB3eNkQnoMs0utG8fVPPtdu45Zgz4fWsBF/vBHM0K1BkynxM18aPA6LesAwx0T7zTACBzHjAkRH27khllhWYlj6jTABnfjAQLY0zyGyPDQhMj5"
    "fDxSASeHVvXtqhGzk8S4xICC3owsSyd7sRZfXqVoQLtbaMruhus/D/m/09E+Vwar2Lld7cpKwdojNK9rRvMqC0M+DfmxGeDAlNrMmvrQiCqgGB"
    "ybhe7XU7obJpD4TOcOXkkMoyHuHabC0tkmAPw16xOXWv0cHfy0tYKAlJw3sYrD3CdOPYUvpnMh6mwkc6FZBSSq1qYqwIXr82fhp2E5DY3vunzL"
    "+jBgzR4sSfwF8FD167qseqqtkiff+FZBXyI0nTosmdFuUI4kO/udUfa2fW0soNMBeS+L241s3fqGilV8rirwuIWBqAKrqbucnOrfMMdn1BAz6T"
    "rH/T50xQ8c4QZm/piG2RHdEgDbkKjGkM8EuQRBF4XVn+GjuOzS4YP4+xOovIWYBr4UWX9J6ehF+IPo6YKJoKwurgZ8vB6Ez9RurmNDC54V8gJE"
    "tE9RZjRGV92mtw/Xb93syVotHGEVE9YRog8A+8Vnpr9YhXZNXeZOJJ9UdTSyfet2+J2j0LWkmy5357DhcUe4Lu1h0UnR9DGygURVj4CZG32acO"
    "qEFxFyqp1jdtQIb+yx1Ou6ErZSM8ZAda+nCbfK0Q2X5g/WV2E+qbw8VSfWhgiBYtmC9A79x1+pGVUP+OeD2/IBI4OVpK4crwbuXQj2Ueg/ErAs"
    "fVEET58F9FGO/Xlj6nFuX99H7AJP8Hc4FycFtPwTrNc4K6W4n1h3Q/ldgQ2RSAH17iQHFJbOEEyC9MR73DcaMk1NCYjF4UN0x4FXqQosYLbivq"
    "1kInoTL5ru/MCNev4laMi/+iEHC9QfrLHfZOLXGXvOFvKQ10L7cwlQUUsS7G2nnUqFc4lZ4tEqiSBhTWi/9nddCrcW19789yRdMk7wAenqxg5u"
    "bBmsdpzq52XR0ZNBFhv3GqTFsc2s53UOO8/RE27xvGM7Pp9W3cGQiKIBezRmM3aYw+L6fVl30FfOyG+fUlmXhFFpluGFo+KghdHckH26n+oHu3"
    "OkJD8x2ImU7tojructT8vjk47zTFIf1Ry8McnaTngnDhSFgrRsbFY3uJGZuH1OcmzH6ZtJ274dFqa1Jwg2mHEu0eNCmjvzR0wZXimmoEfwIfeh"
    "RjIz9Lt7AOg/mRxzbPpOdVkMtwaRbKsLu41XNakM5KyDJjmbP1vG1iYLWH8vtoUuL5kJICyFhGOrQNUYOJAT6UadhJ5dsyCqrYQ5nM/HAi7q3R"
    "IRydHSe7Gfucs220033MAXwskKoDuYXyDK9ZhH+9p7XL8rzxgia+zCo1kTGTEut/WOpR4b8u06C2pOLn8XGSoxqK9IB/O8E9bVekV+0cYMp3s+"
    "r5hEHG2Mhy2THD5WAl6yGWremBftQJXVDOQ41WYKXnvePA2FE3MdtglQItK2jgwx19y3b/HmpafIZ+LnJMUe7NEZlgVZzG3wTgx0lql6Ih+I3h"
    "SQXzvsGXG3HFvmqc0oBxSZnFuJR/I8Ue8GHHw1Wkh46WU0k0dsOknUmRR4r2MbAssOkaMyI0REu7S++hIG2qRO8Mv6I8o2M6h/lanAWHTJf2fR"
    "pSNDwlbIp7RbQEoMfD+oh6DkO7Ldg91nK2PJTokL1lq7R5IUBmbjZXsoNXA4VtWlGs2+x4wh60ke/DddxCEASpwUjsU/5KbVbrV5c76Lo47h5h"
    "wmcXdT5rnWuWip7JbySr2NGA8sir6xuyX5niwkMcortyhrPHR+8bZ4cbG/o7L3JiSug7MJ3/xyr1scF7rpXugzmT61CEByqRMJHI/fS4lZgDaj"
    "ESRashjIcmrUwZj23Dr4FgsXSDqMV0qyXTbjZAfjzpK4bMHU4yaT+RQtuGjBXk68CgGNsvSUvCquMbFVxccM3sjUwDTxK0zhXzblWB+ZcjbL0R"
    "c2W4kALurpzHGGR1Q2lB52zwuVM5S7wxCTlC+XOVSPp3IQ3F6EUWVVLV6xkRApSxKKR/FTC05iLAEI0tTlj4oDUE0MdqHklxzR4eafyj0y82Wp"
    "l9MUNTbE7yil/PwAxvuPhw73rpLM/KwPKmwFQRj6QTcqnxKpHNc5j0Z0k3/ff5MA4KUcCREKffKfGquLqVAFIA5J/imLrNgtFhuFRzJv83RprM"
    "AKWUYjDqp+R6j7Igw54I/SxafSPzkJN5IdwFdjlsNNXqpAR1rfGDio6yAolQnSZ3nVGvrPKyk7QIcya3uJCHqCw4Nf5dI65b70zkAUQ91ofizZ"
    "BIcvqjFGrKw7xdIUDzeEYCLny+YRmHb2m7vckwk92JwWtdM59i74xLIoFf5coZBCxR5ELUR+SEMvkMCyiELki7aIGwr7U27y4plh4aVy6S/n2U"
    "muSUHHCrA/xot+LZm0IKw7duskRlmOodPVCVc4o5Eb1IVQtecr9aojhvM78YO5Kdwuuoc7vN0Ui8Uva7Pz0iRgEB14wqKf7ejZGZJ7Tbb1TBBF"
    "KgL8CDkgTEwOchqkr8WmtBnvBL6LmCgCd1ol8P5qi22L91D68zJ89d2AY2GZJAngCf6XVlS161urwSsUQOwGG9/EexYfbgET6uAMA3S8Erh1V/"
    "CQLkIkzbaAbkGJgXYrpD6Tpq40SPPnGVPA/QcjHLD3DwQt7/W9nVj1EK/dNOvANqeKzGzBwv/G9FLATNOEjwjX5gibqdgj8qklMrLFsWoRodDS"
    "oARCtctqxQ0bLt1yAIDHogT2PYr8Vlql+rUTkG73fybkTwMV0Ehq6kQmlhmkxc1VsZ8ovBrBqd3Xfr2qYEEIbP5zCJuBR4SqE45BiiuQzV9dxR"
    "p1aftuxM4vTQn8AQ9dhcEJjxzzHtuirXcvh4NCOD2hqY49SFpM96niQJdUxmm+ecqB61qrvQECNKXBkNZp/Kc3+wpezM9+3yn1W4OVofruKN3W"
    "Nlo19ygCCK3ZuB0MZSkjESzouZRhoqUzgBOAnH4c16grcb9DdV+ZRbFXWk96FUs7imFMpvbucln/RySYzgW4D9w5jrMu2kRLzijrUzns/yhPC5"
    "kfTbKLuufMyf3MjIs4wYaOM1oEU4ywg9UKz2iSqoM3W1IPOLnZvCc+yAmBns8EsPORzpX5TzTmKk0T7XLpgFo8FU8ldWsGWE5T8EJekstpqTnq"
    "Xkre1hjYDQ/P3ZoohqDaJQgolJudEX84iYoLn1dMgLdNlTSbh5dLkhiHLo6xAc3dYVBCBKkkdLKdqMauMZA23scoFjrI2FW6AcJVi++8Rds0On"
    "b1pAHsT1EO8rxRgU4m9eiCg+cyqioR3gurBUT+A6pkG/l2U26RlK3j86tsnKaxbkG4DE/+vEMCgeu/2sPklZN0P1now5NxXbGY3nnaI9nqqIq+"
    "3rVKAKnPA5yCJBiN/fMaJ7P9QPdmbCkgnfsGSA+gI+kPCvqWbpWkWp/uxngTaa/wGwEHNyIrp9Cn39d0rttsdnyv28yfBzGpjt814EWxxB4DQ+"
    "K+Ea9zBf6hq8E9gd3mEw4XEM/OQtc+k6QN8oEaSkWkGyP+yQqLW5UJUUZKg4+87KkN7lCoUW23pl6NHj+Q/ZI5O6vzjB/xSg68Jk0ZKqWUugv7"
    "iyhk2brzk0+jTNaQLRqeCBoWFyR5gVCfxgQZiHlFgH1M+Oqh0klv2TT+af4AL8pNA/MTg9yO6m3AbaQboQZOh6P2AwH2KHBZU4J0Z9yDr5zcWi"
    "29JWFY/oJEsaCvaXWm3YFQOhunHzUFl7ld8V405jMiaNbp/YCUKR6f2y0lrR7fOKwVhZ89G/fGhWUGeDXv3+JSLofJ5ePAE95tQABhXj63NrXt"
    "VU5Z/UF8pKRR3m6ag0IrpprNthwaAIXuXNu/DpHtow2QBYA+izbHRSkYT1+QZfIUkwiWaGZ06F5zFXsMSOktuBySmhRDGBghMMc9r17o9nI5kh"
    "tjssaj8XM3r15RjbayiDQDicB5dUALypjZO2+bIWFdB+nQ9xGWoXl/NzGCd4bk5LJwBNTsGL80O8JIdQNT4k19mzv2yzjer9ApL4HlgcS88AhU"
    "05W19aJ+7uqNjm+7Eoecigc2Eq5QGcIpnWqkBplUcW6YttpD4Kqzatp4/NOG1BjLYyLnHZziZRZeemahVYxwWSbNpEYa+5FFovci1p3iPTvkhN"
    "vfPRZ9y2OJtmNu5b5EdpYe2Zn6eOVkPv8lX+hk6SRxl5OsKGnnkVP0q8DmVfzr0g+fcH8EuhOHbXwQjG0zssYpAsFYnUebQtcSJiDBzSO9e//i"
    "m5DHpu+9xaQ4hC9ZFhgc+BMstNmn+O5ljDws7S6ZZEeSonw/4N8OGWbxgIXHr2wS9syFQvn5m1+wsidAdMJEeGxjEt9nwCZLuNykZGzwo+ml9+"
    "ApFSrzzf9DF6irsmlJN0mFL+cnAS1Z9RbsygmsRNhlwOCKaRorIHL2PK9ZykRFnniQRLxKJ587owaTZhWgK1teKe4sJ750y+mVI141W3A3JXBh"
    "KU61a4UYUEeQXcxxz2+aVDpZFV7PnVZrpbafL3tNl9y82FBSoD+ocMnZjLiR4GCuJKRxLfU2RVKrPVbB8VfL40oSDafycss5WOCe0OA1BYDx+s"
    "9M4K/XgnUIxFnAb9R6OkhCvZQUqshENVtP9Zr+7wd86EtI/GLu38Mv2keWk2G5LSBqY2/gWw5RK/91qeT7Kq92G5zqzE5+NyuPSsNkUiSt656n"
    "Q/l1yBrZCMcvZuhfuif/dSsgq2REP3NxFHIkMdUTQ1XrV+908tJF4JchpU62cb0+AJEB3nIBL64iFdt1k2mlRUcDZ/tc+ybCbCi6sLMWYbBhql"
    "DxSAJ+o5ybxQzctBt18TYh5W65SsQVqK4Gsl7KOwA1yrY7Rpkg/tROT8IutftzvIj317SY/2SNT++3N0223QFU4GoGF5EaxVP6M+pXCurCQR+u"
    "fNBsTzpFxJ6S/NOhVJuMNR70fonKS5Vva8Sbee/9e/yGO5X1E9mGM3tAtSC3APfVQl9CmxNcPWQLfIq8Pq+pKgnQN1+yw1tbOehfaq5wejxgPa"
    "XcIu+qNMX2YBnAtF/eRbK94heKNlSAIzVUdR33TQWE8sGhaJiqLNyuFD3kUrrEFy4R+Uvv0WdeWvZDo3pb4uAnUJ87+c4jSJeg44ImZ/Wd567W"
    "EScJaEP02Tbr/pZt36ALZKwMIXfHJPsYca97J+QikqEeU0p8AYnrfOmiHleaiw5t4i0IcMWeWaakf6zLIz1XeYulfRKIDtZ6rjm2/DpMMb0sWo"
    "bVwwKjTUlV92uwk75+c1acw3S37+MPKDyhPz5D98cyKg4N1jio+23hpGjCzS4DqGWCJcplJq2HF9FfKd8ZXHeMa14IrLZb9bN2o66mBPFcqz9T"
    "MXdBMlxbcUWlwwaQ8GaWgzdBbi5IbBd2/4P3tww8LXpsIeAiP3SCPnvHCRWxCmKt2KDBjCqS6PeaRLH8NM/OeBWVsfveoWmCFTdiFxGsSFgQf2"
    "C0ZxderLnH/oUA45B976d+VmfMZd56g0sA32fOtyZ7UO61Lyg+l7EoSRkzNVlejHxSn9ddKOcyH7xmiMOAAlK7CxwiSb8quqbLv+5utgx3CzhT"
    "epC5cKbWtabzDCsCkZ/bcfaSJEZO/6bNGLUvIpBINuQAYZtwAl63ZbUlnTxnSk0LKo8IFXAtZEoO0OU5EuWS232nwm8GZi/9f1xHBVtTckmfHw"
    "olPnne8qMWgIesq1EI/g1WKcVtSGvr1sT3wkm374yyY7f8b7hriKJD0fkV0iURTqUbyFO2iGz0BCMDOmqa79m6kuiDa8mr6gLF4RABUUasPpP6"
    "9XIkfUgRffnpd7o+0vfl3Lp3WCIT4HeQ6O1pThlXCfNc22LKyg9hQc3W5wCd6wN7lA6xCVZh2VU6N7swjS+TJbQclJWBfyA0nM8dEd7UjhOhif"
    "j4uaOnX190C5Amor8jf8/skd3ZH9I0VyRNwYYz9uFBK7k6C78WhpseZlDiecK0qvymbuuShKHAP5dCP/t4M2oYOADF4IhIvHoVTr775Ji+pi1U"
    "nlbEXtQvtEePJPoFafdOI0KyiTSZHUoOlK01FhDK5EPobHBv8Ba1rATrjSXOnYt7paW+vS4a2GLB1GQUhgoebsohUjGjBKWXnjz8nJDjGLePZR"
    "8A44VJfW0iIbfrjpEaf9YklAGVALx9lKjiCa76QyzMVbCnHi1qWtH00PUxVOoTjruct2l8B4isMpetpXMoM+TfUSBRI3S931Nd8+x6O/ccQTqY"
    "H5EDuOpFLDiCA5K8ygVJshMLKkY/Ps4t4o08ajHzCJBsBHh81U+HRikcQ8I8aPMRSifkSzJ/Gh+5I7N70PGBtojHhsdO4wG2ELNbriZfwmXseh"
    "lGMthqkfwDTxkPav6CLxWEUQW+cEcfTsGByasDwFzp45N8JJrN8zhM8BNmGpGlHWrULXGDy/4+0Z+d4STOrFgnyQ+Y/9thowkTjyMTSu7j/zdv"
    "MrEnNREeITRv8qpBkZDUWB75NDdCOF+kC10GW8BoAHdFFiEdEyr+DAFiNxJAYcbAsWu05+uWC53t9TrTwndgpJleWv/Xm9rx8efogD4Gz7jTA0"
    "2djv0yW/FeIUw4x8KxlJl8eaNEkivwbY1zFNZk+zxATLH254rxh0ZebS7aFLvBfw2o51G2DDPAcrCCyfqkxaygvBEYnTHnW3tqgMNFvGNBRI8X"
    "7mSo58pJqTfQMpa6fkjFjKgRTL475EGistwgJUB+Uu6IkaYdcyjVQaRxVbrijoIAlQHp5PymZt/HJs26vndhAbpt/VxejDyDBcj+d8UxzBxER/"
    "at9VJ58U5/a+wYrmofoEYFNEXtZymSn7zjinaUrIms5UKzKiBrthryM79KyW4YvKeHe/RgCbkWfYVg6jJEvqU2TuVwv2nIKs313v7iifWsEnaU"
    "BCLn37LnmpKNV4q0zbNQQZ0KL1McbKk8kooCtfbiM+F+i0VByimlKi25MTWMriW5vubngSSKgdhDiQjAq66EJwkBArskAt03kqDWc5m1VGZ1wb"
    "jHn7j1uxfh5X10n1lgFNx4hWZRsvUPL21zXt8cetKknEsHFVifwDWGYkwGGzSKL4ysPTBuBbyLHrXfVlfrUsPXU0+lSxCae267DDewGhxtZKnQ"
    "XP4NNuZXqim6MUM9IdxNyCaxbbWFW9v7DtIiNbMmAukURn8UELotjRW+sFi9NC5huYi4jOOe6YQWXl7OYg7LLJEz+9oSUnEg6lky0mwCmvrhyc"
    "7Fi7SG2oid0vrMxGHfmX+VPcqi+jrEQ1JMgPGRvVMkgKEGqlA3HdYXo9rdkO0BZ8ffUtyeMqT4RwtGrPGZ3WvVETrpg6C5I9RT4gmhnJXqnEci"
    "e+bOnxG1n83fYJpTLWk47UMaYMI8Vc4VJp3uIkgq0b0ivXlw6Zqwkb/ipp41vnr3YwIEI1RLYscd8zYdDTfmj+EKQUE7GaQQkIIp6wUfn9Qst8"
    "O8zVORDfg36PigKHBOK8AsXga1hHDoxFimz40cfs4SApskhcmG0VOF2PIRqY1ig11xwmvDv+NR41njW3uzgKhgs8rLYKzwWn0xEdtvy3bGUyN1"
    "GWy+ZA2xlwJjez0lPtSuaVY20+hloxv4SL2ghKrazmjhEiVyLFEBeCKvq0NfVT/Xfmfrp+n9EL12oHgVcUi6wrH1OqUT4fH91KoYSpcw7Q0yDq"
    "xtmVkwTS9yl5Z5/tqCbaSsHmWtxMwX/adwhP1UmKyxo7vK4xVDeEZYd5Yez/6mX/1lgGQZoz2GL8CcEtHV9srriNd63RPu7WgCbAh+pwe5rOJe"
    "aDD36JASU9IYPt4DCLfhabUwntN6PBHf19wCZ1o9sEQ99MfumSUGeVp5P6OsJfrsAWiwjOPWFcQqY4AzUy/p3y/C2q/qC1TCsQA+7KmMV5tdky"
    "MMo6X+UYhxiSZvV4Hs2ddGtZWJFjUEOlm5x5zBsCCRm0nq7TkH0nQXfpqnHFPluIyGSKjbNfjeRPdsofq/NYDymO+DhPTRPIswgBH25z8pJ/2I"
    "Sj4Z0okjG0c8XFYN40iZ8TIwUbAOJ2gpzoOdLLJVVbaKfTIVY7s293uESPc9a0QBV/FOMalGk0Rn9bI8Xz0hwC5bsEDkJWX7w+WTLDLZAnAJP+"
    "uIXyfnZFLwsOZS2vzfkzek4mgcSi/WNpS/2NsP5DxExup52pbGGULfy3+Svk+5zZbGtgMEyxzK8q7M05F2hiFuqM2pvvHbMJXTGOJVRnYsnDHs"
    "qGx+WFyxT6JSaGeIeeVvZZ15z+qvyVpTbLTCoW0UvSuq0Y3euFg8HeWfbVLrpv5MCFVR7tOwXPSCG+6UeXtyZ6e9rzo2/4OS+x2Dy5fdI9m1YD"
    "6FNcjwBWx+xnS50bFCDobuzOu19rZr4X/RShbv60BsrAA2RoBdAUnz3uVdqpgZxRCnj+MrSk3Z9nxpbvjEYalP1J657A8t8PgTgXaf97BM6z3e"
    "jzE+wqEhpEkjPnM+3lMwUoZ75rylt2lk3YkKfy/JX79/2l/SK5PPA5NFKkjM7LhFRAUEOgbxmfDoaNg5r3Eu4V97Abzt594zqOmb4rMzR+J8qC"
    "cPYCpCvt4aoo5z6gHTCgDJomt8OEeCniWhvRcP9tgNd3RcGn5R1VVFm9+SzPcTaWFb2+dg2dHEOOHWG/m1Qp6VTNjzmSSuzCzfKtiViuurRzXh"
    "hqYsSxDSs+WuTh9BmkQuyoxCRYlDCSwQXO6cDZCFWkR9ZGFjYc+Ki3RZsibMMoMSmwfnX2XewOp9GSNySNipfM8d4mcm123QW2H7/NELrW5wVY"
    "TricL7Of4mPCMeWI5uvW4nOxoxp5QYLWO+s4yYfYOVjQMzQyx0Ur7cd0QvknmhLzk1BHUSXJZzgptrtKqpA7KrYGy77Bar1y+ljEQmSFjlnvbk"
    "p2d83HYSLhWnf6UgMZS3gSWpYaFpIF4rMW5gfBA0iFRRmV5Uy3evAXX3SZ46NSujwCQ+vY8nauw+3U9lXOzdVLm3Smn09i1ZLSE4zBZHLI2xA7"
    "5quGLjSjBkKwtrxE7AmpMZAL1lmktXUGbkrU2bcpSaiaWh4q8BNY2O98GF/nylkPuCKv6vyQgA7UkCSd4RJVc0vrSSYIt2aRIK/rKUOKiMvYcq"
    "aEqLF4dwnQToZJmKdA1N7aUiSs5Wfx4ryBsZHZb9xWAbJ7ATRPydy2L92QRdTBVtylohGbpmeeoyx7ZsBtX0X+W4/XTYuFn8Stj+tnhK5dhEk6"
    "dso42Wuwkm0YKYdDywlqb0i/BHhveqKHrlj0sr/NNyBCmSH8bWIkDEls9+eUEg/uPqk0+QMOjgyh33jBg4y8GOFWNy0jgp7WM/z8iOkc3Wot0V"
    "f49TLJlsDdgUXc0TblYAnRXkVabmwN8rhhxznZoXERgdjkAItiifFo7UHlcdpgZWgzMDMIBldVDvoEES8mlWd2FZxm2GEiCZ0PUeicI0oROy9q"
    "EbcnJ4Xjr67E2yOICuKFURVrcxYqhJgVTY4xR2vaI9biT9vVOTVDDZiwwQ83qenpNTuGU5+3jiR0IrVa+rLQMX2/G8mC4prVzzWSCVocvGl+4N"
    "+7nfRcdd7kU1/ScamMysdHFjYfhVhwUIlepAGZFbomRQZVCINRn2Ahsc1Ys1Bxc13BA3W9LtmbMlC0M4aghmiCo+xuVOggPZzXEOJNqwCUyba3"
    "hhWpKGwnEDXJdD3ckcIIUgTWfTrmqHEXshQRkMjjQcL/TJSTK7Ny6wOMV9dCScMOScutCPgHXVFkMqUyg5pjynFBNZ2KjEFA9mg5tP9qclvU7h"
    "R9upO5ppeTnS+6rKyfA/l4F6ONv5pcb7KdVbgK7GWWpv/1ajdinM2Rr7Dged/T+gHWLRbqotP92CC1KGO8h6pNGNJygt+1Xz8/mW5OBwrAyVDJ"
    "D+pFrdi1Tt0+MBOAAJ2SsQvzLuaf+ZYTUzuzA1wo6drL2WOYgWKzDCJKbfjK4Ca1w5Kb8dIgcmMFEvt0IOYyjQp7eoHPYRy5OHz6ByF50Q0DR+"
    "Z9CfvGTACCIdzMyclTKNmVF37nSsypzwo/Ef5QdYuM+jxlt9PVnWojzOfg2nMJ1NxBcsiGMEV+xUa6CoNJJEidblXlp0XZG8L9iClyeXsnu7zT"
    "qaLwy20ImibTnNx/xIpJ3N9Z3eCsy/xqq2DhU+n0xiO9X7jLFQhV+ekZvLu9WoTDACjBm9oOiosR3HxdhVVacULquKP2LFaz53VJ6VNcF92Xf9"
    "h8UCYUZogD7m6FuqSXmveJf9M0UDudf0zvoQoaKw4xhMnQOhF6dpc8ETum44Ivro3bIowsdkGz4ZiU+dcncdeqYsbzNhV5GOEROcDez7jc2IjN"
    "biJQAgvsUXIL1Z2UXwlO4yeXYJ0y0ekdh6casRrcOLV0VKHlVqxkWe3JNaqlwUS/QignHrhoZr9swUyEFcqMTmn4UHSzfLFdTIOwrdPBSUyXdU"
    "xswJeH90I4JE9N8nGermFSpy+M+Rh355U9WZFiaavBdAzYVtK3JI6p11IJSEo4Jwrkwt3Ig2Mpu9Et+u8JnZO6rmOw9yOPetzs972KI+P8d3jm"
    "KnQ/K8hA7VT0Yslk/gCMz7deBxmBObAb6LUCVdsxY+Z9XQylzapyw0ZyuDrrAjpGyNk8o0TezoXzkhkZn5nirE478tfjilCf8xG38nDK9IxOve"
    "cwQHVxad1Vuz5F/GafEYB3g5kZscvt7/qvMUHq+kRqNWkm1ogLWCSR4svJcotkx+Ui5aUkfRSjdf+2tKmTzhYvPd4Gi65QXdliKux3ZnBRDB6D"
    "Y26ubN+HJvVuiAAipKaQWDu4gXSePN/xq3EhG6p5fLhZz1O3xBqvo8osZZHhzntVswP6CiiHvdNGxlgvN8CKoDnVOpSN7ob9H+PtKfUTg0wHLN"
    "5+6MbCz0gOem/kPetLijo5TK6arbF3sUSZFtSd4swSmPGHx2VJQtlvCQSBOkx6b26yLSMZdsp/Z2U/0ioHcJcKC3e0eJ8o65xVF4dn/kfgPU7G"
    "BPpIuP+kpFhzZjQLxnMmU+o899OqY8Gx8zppRrpn3SGwfxxokT36xJNFN27RBzbDSqee+CC9qEZWfy9fl5gih5TVQVhW6zgEHpEXKn8LYnBCsP"
    "pPxxK0VnDcm2OMcJS92nmi8fh5noLykypyJcq2lP9cRAJlqK1XV+P9gD1TFgU8AjvIlJwO37e9mNwqvseU2NQzOvkKVqLgXZ15G8h0weL+mb2N"
    "89ISEbCZsnZnLBQRaH1vBkei2LBjOZDm+fdLSchYLbnGFW0DWvrPzp+d5p1dna6IuIRP99yG7GZMr00LHeLh+lAdjFyoYPuxy6q2ylqTTYnRBH"
    "C8stO+ua/s4cjciVhaW7fEYcHoawSkrmYqALDB32axVVVr/CxlOdUF8CtJEF0hy1/JqnNBxTnGs45E3/B0KIDUVKqR/PFnsEij2Y0R8AYzwhDC"
    "MtPlKjPcRPZwmvmrEW7M6k7wAuNSH02qUDgYLlRLgXT88v/wVGxExRVYRFgA9BN18QgOaqSWm05BBSO0FzSGgzjW+iy0OI9Tj4yqOXphRomQaL"
    "eKqT5sulScP3kRIZd1a65q6zXh5+Sm7BEviixu+NNFGvVh35Bd3tTe8CmRRl4Q0P2M9+9YsKIv1WjvowT6rFrGT+1hNoLoK16s0rppvU/1Kd6q"
    "9UlfYFcg95wUaT0tsMpz+JSGhlmQ6hYauZ4FiX8TPuROXU8J6C34DXB+JwgnOf/U02W1OyREUYwguZWLU2onNmE5PUtlWvlrLZHvDTmOo5u0Z8"
    "JzOryW6glUnBOzE1msbBmdMBaEuTP1SOLq3iNpQueHF+coh7aViwC6P5P/bkN9dMStrnQuO7x96mHgwCw1e935Xb98nWSM/2pCN0JH2yM4fO/R"
    "QgFi1C8hTTfvFVDWu9aJXhg1ITddYaKI91uWtaUtfDilcVA90sSVnwBGBQ/+Vz3jF0gQ0FR3crsLdZf53R9Rp069U2ub2RT1hGcXEU+JRtO3qV"
    "7p9ywi7nPgY8lWYnpu6erA9r6sKlFcef0lllsq+KHi8hBwB6O2wPpUuXDt6oOtisgRfEC1Tn2msvFdVgnKMwAAAA")


def hero(title: str, subtitle: str) -> None:
    with st.container(key="hero"):
        st.html(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p><img class="hero-art" alt="" src="{HERO_IMG}">'
                '<div class="slogan"><b>강한 국방,<br>데이터로 이어집니다.</b></div></div>')


def real_bar(src: str) -> None:
    """샘플이 아닌 실측 집계를 쓰는 구역·페이지 표시(데모 경고 띠의 초록판)."""
    st.html(f'<div class="demo-bar real"><b>✔ 실측 집계</b><span>{src}</span></div>')


def style_fig(fig, height: int | None = None):
    grid = "#e7eefa"
    m = fig.layout.margin                   # 차트가 미리 정한 여백(예: 가로 막대의 라벨 자리)은 그대로 둔다
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TEXT, size=12), title_font=dict(size=14, color=TEXT),
                      legend=dict(font=dict(color=MUTED), bgcolor="rgba(0,0,0,0)"),
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor=LINE, font=dict(color=TEXT)),
                      margin=dict(l=8 if m.l is None else m.l, r=8 if m.r is None else m.r,
                                  t=10 if m.t is None else m.t, b=8 if m.b is None else m.b))
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED),
                     automargin=True)             # 아래 여백(8px)이 좁아도 가로축 글씨(국가명 등)가 잘리지 않게
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED),
                     automargin=True)             # 여백이 좁아도 눈금 숫자(10k 등)가 잘리지 않게
    if height:
        fig.update_layout(height=height)
    return fig


def rules_card(title: str, items: list[tuple[str, str]], head: str = "", tip: str = "", cols: int = 1) -> str:
    """✓ 원칙 목록 카드. head = 제목과 목록 사이에 넣을 HTML(없으면 비움).
    tip = 제목 오른쪽 위 ⓘ 말풍선 설명 — funnel_card 처럼 .h .sub 에 넣으면 ⓘ 로 바뀐다(없으면 ⓘ 도 없음).
    cols = 한 줄에 놓을 항목 수. 1(기본)이면 세로로 쌓고(감싸는 칸 없음 — 기존 카드 HTML 그대로),
    2 이상이면 항목을 grid 칸(repeat(cols, 1fr))으로 감싸 가로로 나란히 둔다."""
    body = "".join(f'<div class="rule"><span class="ck">✓</span><div><b>{t}</b><span>{d}</span></div></div>'
                   for t, d in items)
    if cols > 1:
        body = f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:16px">{body}</div>'
    sub = f' <span class="sub">{tip}</span>' if tip else ""
    return f'<div class="card"><div class="h">{title}{sub}</div>{head}{body}</div>'


FUNNEL_COLORS = ["#2456c8", "#3b82f6", "#1fa7c4", "#2fae7a"]


def funnel_card(title: str, sub: str, rows: list[tuple], note: str = "", step: float = 5.5) -> str:
    """층마다 사다리꼴 하나인 깔때기 카드. rows = (이름, 값[, 설명]) — 설명이 없으면 첫 층 대비 % 를 쓴다.
    step = 층마다 양옆이 좁아지는 폭(%). 폭은 값에 비례하지 않는다(단계를 보이는 도형)."""
    base = rows[0][1]
    body = "".join(
        f'<div class="fr"><div class="tz" style="background:{FUNNEL_COLORS[i % len(FUNNEL_COLORS)]};animation-delay:{i * .08:.2f}s;'
        f'clip-path:polygon({i * step}% 0,{100 - i * step}% 0,{100 - (i + 1) * step}% 100%,{(i + 1) * step}% 100%)">'
        f'{r[1]:,}</div><div class="lb"><div>{r[0]}<small>'
        f'{r[2] + " · " if len(r) > 2 else ""}{r[1] / base * 100:.1f}%</small></div></div></div>'
        for i, r in enumerate(rows))
    tip = sub + (f"<br>{note}" if note else "")
    return f'<div class="card"><div class="h">{title} <span class="sub">{tip}</span></div><div class="funnel">{body}</div></div>'


def rank_card(title: str, sub: str, rows: list[tuple[str, float, str]], unit: str) -> str:
    top = max(v for _, v, _ in rows) or 1
    body = "".join(
        f'<div class="rank"><span class="no">{i}</span><span class="nm">{n}</span>'
        f'<span class="tr"><span class="fl" style="width:{v / top * 100:.0f}%;background:{c}"></span></span>'
        f'<span class="vl">{v:,.0f}</span></div>'
        for i, (n, v, c) in enumerate(rows, 1))
    return (f'<div class="card"><div class="h">{title} <span class="sub">단위: {unit}</span></div>'
            f'<div style="font-size:11px;color:{MUTED};margin-bottom:6px">{sub}</div>{body}</div>')


# ── 공급망 현황 · 공급 집중도 요소 ────────────────────────────────────────────
def hhi_level(hhi: float) -> tuple[str, str]:
    """HHI 구간 이름과 색. 위험 예측이 아니라 집중 수준만 나눈다."""
    if hhi >= 4000:
        return "매우 높음", "#e5484d"
    if hhi >= 2500:
        return "높음", "#f59e0b"
    return "보통", "#12b76a"


def _svg_img(svg: str, w: int, h: int, cls: str = "") -> str:
    """st.html 은 <svg> 태그를 지우므로 data URI 이미지로 싸서 넣는다. SVG 안의 <style> 애니메이션은 그대로 돈다."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img class="{cls}" width="{w}" height="{h}" alt="" src="data:image/svg+xml;base64,{b64}">'


# 이미지 속 SVG 애니메이션은 브라우저에 따라 멈춰 있을 수 있어 SVG 는 정지 그림으로 두고,
# 왼쪽부터 드러나는 움직임은 페이지 CSS(.spark 의 clip-path)로 준다.
_SPARK_STYLE = "<style>polyline{fill:none;stroke-width:1.7;stroke-linejoin:round}</style>"


def sparkline(vals: list[float], color: str, w: int = 118, h: int = 30) -> str:
    """주식 차트처럼 왼쪽에서 오른쪽으로 그려지는 작은 선(끝점 강조)."""
    lo, hi = min(vals), max(vals)
    sx = (w - 6) / (len(vals) - 1)
    pts = [(2 + i * sx, h - 4 - (v - lo) / ((hi - lo) or 1) * (h - 8)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{_SPARK_STYLE}'
           f'<polygon class="f" points="2,{h} {line} {pts[-1][0]:.1f},{h}" fill="{color}" fill-opacity=".10"/>'
           f'<polyline points="{line}" stroke="{color}" pathLength="1"/>'
           f'<circle class="f" cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.8" fill="{color}"/></svg>')
    return _svg_img(svg, w, h, "spark")


def supply_table(rows: list[dict]) -> str:
    head = ("<tr><th>No.</th><th>품목군</th><th>1위 공급국</th><th>최근 수입액 추이<small>(최근 12개월)</small></th>"
            "<th>수입액 변화<small>(전년 대비)</small></th><th>수입국<small>(개)</small></th>"
            "<th>집중도<small>(HHI)</small></th><th>1위 점유율</th><th>공급 집중</th></tr>")
    body = ""
    for i, f in enumerate(rows, 1):
        up = f["yoy"] >= 0
        color = "#e5484d" if up else "#2b6ef6"          # 주식처럼 오르면 빨강, 내리면 파랑
        lvl, lc = hhi_level(f["hhi"])
        body += (f'<tr><td class="no">{i}</td><td class="nm">{f["name"]}<em>HS {f["hs"]}</em></td>'
                 f'<td>{f["top"]}</td><td>{sparkline(f["m"], color)}</td>'
                 f'<td class="{"up" if up else "dn"}">{"▲" if up else "▼"} {abs(f["yoy"]):.1f}%</td>'
                 f'<td>{f["n"]}</td><td>{f["hhi"]:,}</td><td>{f["s1"]:.1f}%</td>'
                 f'<td class="lv"><i style="background:{lc}"></i><span style="color:{lc}">{lvl}</span></td></tr>')
    tip = (f"품목군 {len(rows)}개 · 공급 집중 = HHI 4,000 이상 매우 높음 · 2,500 이상 높음<br>"
           "추이 · 변화율은 최근 12개월과 그 전 12개월의 월별 수입액 비교(샘플)<br>"
           "국산화율은 이 대시보드가 다루지 않습니다")
    return (f'<div class="card"><div class="h">부품별 공급망 현황{info_btn(tip)}</div>'
            f'<table class="sc"><thead>{head}</thead><tbody>{body}</tbody></table></div>')


def share_card(f: dict) -> str:
    sh = f["shares"]
    rest = sum(s for _, s in sh[5:])
    cmap = {c[0]: c[4] for c in COUNTRIES}
    rows = [(n, s, cmap.get(n, "#94a7c8")) for n, s in sh[:5]] + ([("기타", rest, ETC)] if rest > 0.05 else [])
    body = "".join(f'<div class="row" title="{n} {s:.1f}%"><div class="nm">{n}</div><div class="track">'
                   f'<div class="fill" style="width:{s:.1f}%;background:{c}"></div><div class="ref"></div></div>'
                   f'<div class="pct">{s:.1f}%</div></div>' for n, s, c in rows)
    return (f'<div class="card"><div class="h">공급 국가 비중 <span class="sub">{f["name"]} · HS {f["hs"]} · '
            f'점선 = 50%<br>수입국 {f["n"]}개 중 상위 5개국 · 샘플</span></div><div class="bars big">{body}</div></div>')


# ════════════════════════════════════════════════════════════════════════════
# 3. 지구본 · 세계지도 공급 흐름 컴포넌트
#    지구본(회전 · 끌어서 돌리기)과 세계지도를 단추로 오간다. 처음에 지구본이 돌다가
#    저절로 지도로 펼쳐지던 연출만 뺐다 — 지도는 이제 사용자가 눌러서 본다.
#    흐름선에는 공급국 → 대한민국 방향 화살표가 붙고, 머리 화살표 뒤로 흐름 화살표가 계속 흐른다.
#    원 위에 커서를 올리면 회전이 멈추고 나라·수입액·1위 품목군이 뜬다.
# ════════════════════════════════════════════════════════════════════════════
KOREA = [127.8, 36.5]
_GLOBE = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;
       color:#16233f;background:transparent;overflow:hidden;user-select:none}
  #wrap{position:relative;width:100%;height:__H__px;border-radius:12px;overflow:hidden;
        background:linear-gradient(170deg,#f4f9ff,#e6f0fd)}
  canvas{position:absolute;inset:0;width:100%;height:100%}
  #globe-c{transition:opacity .55s ease, transform .75s cubic-bezier(.65,0,.35,1)}
  #map-c{opacity:0;transition:opacity .6s ease .12s, transform .75s cubic-bezier(.65,0,.35,1);transform:scale(.88)}
  .flat #globe-c{opacity:0;transform:scale(1.35)}
  .flat #map-c{opacity:1;transform:scale(1)}
  #hud{position:absolute;left:14px;top:12px;display:flex;align-items:center;gap:8px;z-index:5;pointer-events:none}
  #dot{width:7px;height:7px;border-radius:50%;background:#2b6ef6;box-shadow:0 0 0 0 rgba(43,110,246,.55);animation:pulse 1.8s infinite}
  @keyframes pulse{70%{box-shadow:0 0 0 9px rgba(43,110,246,0)}100%{box-shadow:0 0 0 0 rgba(43,110,246,0)}}
  #status{font-size:11.5px;font-weight:700;color:#3d5b8c;letter-spacing:-.2px}
  #ctrl{position:absolute;right:12px;top:10px;display:flex;gap:6px;z-index:6}
  #ctrl button{font:600 11.5px Pretendard,system-ui,sans-serif;color:#3d5b8c;background:rgba(255,255,255,.88);
    border:1px solid #dde5f2;border-radius:9px;padding:5px 11px;cursor:pointer;box-shadow:0 1px 3px rgba(19,42,84,.08);transition:all .15s}
  #ctrl button:hover{background:#fff;color:#2b6ef6;border-color:#b9d1fb;transform:translateY(-1px)}
  #ctrl button.on{background:#2b6ef6;color:#fff;border-color:transparent;box-shadow:0 3px 10px rgba(43,110,246,.35)}
  #tip{position:absolute;z-index:9;pointer-events:none;opacity:0;transform:translate(-50%,-118%);background:#fff;
    border:1px solid #dde5f2;border-radius:10px;padding:8px 11px;box-shadow:0 8px 24px rgba(19,42,84,.16);
    transition:opacity .12s;white-space:nowrap}
  #tip b{display:block;font-size:12.5px;font-weight:800;letter-spacing:-.3px}
  #tip .v{font-size:12px;color:#2b6ef6;font-weight:800;margin-top:2px}
  #tip .n{font-size:10.5px;color:#6b7a99;margin-top:3px;max-width:230px;white-space:normal;line-height:1.45}
</style></head><body>
<div id="wrap">
  <canvas id="globe-c"></canvas><canvas id="map-c"></canvas>
  <div id="hud"><span id="dot"></span><span id="status">지구본 회전 중…</span></div>
  <div id="ctrl"><button id="b-globe" class="on">🌍 지구본</button><button id="b-map">🗺️ 지도</button><button id="b-replay">↻ 다시</button></div>
  <div id="tip"></div>
</div>
<script>
const PTS = __DATA__, KOREA = __KOREA__, UNIT = "__UNIT__", OUTBOUND = __DIR__;
// 선 · 화살표 방향 — 수입은 그 나라 → 한국, 수출(OUTBOUND)은 한국 → 그 나라
const lane=p=>OUTBOUND?d3.geoInterpolate(KOREA,[p.lon,p.lat]):d3.geoInterpolate([p.lon,p.lat],KOREA);
const wrap=document.getElementById('wrap'), tip=document.getElementById('tip'), statusEl=document.getElementById('status');
const gc=document.getElementById('globe-c'), mc=document.getElementById('map-c');
const gx=gc.getContext('2d'), mx=mc.getContext('2d');
let W=0,H=0,DPR=Math.min(window.devicePixelRatio||1,2), world=null;
const graticule=d3.geoGraticule10(), maxVal=Math.max(1,...PTS.map(p=>+p.value||0));
const projG=d3.geoOrthographic().clipAngle(90).precision(0.4);
const projM=d3.geoNaturalEarth1().precision(0.4);
let pathG,pathM;

function size(){
  W=wrap.clientWidth; H=wrap.clientHeight;
  for(const c of [gc,mc]){c.width=W*DPR;c.height=H*DPR;}
  gx.setTransform(DPR,0,0,DPR,0,0); mx.setTransform(DPR,0,0,DPR,0,0);
  projG.scale(Math.min(W,H)*0.40).translate([W/2,H/2+6]);
  projM.fitExtent([[18,34],[W-18,H-34]],{type:'Sphere'});
  pathG=d3.geoPath(projG,gx); pathM=d3.geoPath(projM,mx);
}
function paintSphere(ctx,path,proj,isGlobe){
  ctx.clearRect(0,0,W,H);
  ctx.beginPath(); path({type:'Sphere'});
  if(isGlobe){
    const c=proj.translate(), r=proj.scale();
    const g=ctx.createRadialGradient(c[0]-r*.35,c[1]-r*.4,r*.1,c[0],c[1],r*1.08);
    g.addColorStop(0,'#eaf4ff'); g.addColorStop(.55,'#d3e6fb'); g.addColorStop(1,'#b9d5f3');
    ctx.fillStyle=g;
  } else ctx.fillStyle='#dce9fa';
  ctx.fill();
  if(isGlobe){ctx.save();ctx.shadowColor='rgba(43,110,246,.28)';ctx.shadowBlur=22;ctx.fill();ctx.restore();}
  ctx.beginPath(); path(graticule); ctx.strokeStyle='rgba(90,130,190,.22)'; ctx.lineWidth=.6; ctx.stroke();
  if(world){ctx.beginPath();path(world);ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle='#c2d3ec';ctx.lineWidth=.7;ctx.stroke();}
  ctx.beginPath(); path({type:'Sphere'});
  ctx.strokeStyle=isGlobe?'rgba(43,110,246,.45)':'rgba(150,180,220,.5)'; ctx.lineWidth=1.1; ctx.stroke();
}
function radius(v){return 4+20*Math.sqrt((+v||0)/maxVal);}
function seen(lon,lat,isGlobe){
  if(!isGlobe) return true;
  const rot=projG.rotate();
  return d3.geoDistance([lon,lat],[-rot[0],-rot[1]])<Math.PI/2;
}
function visible(p,proj,isGlobe){return seen(p.lon,p.lat,isGlobe);}

/* ── 흐름 화살표 — 대권 위 t 지점의 진행 방향으로 삼각형을 그린다 ──────── */
function arrow(ctx,proj,isGlobe,p,t,alpha,s){
  if(t<=0.03) return;
  const inter=lane(p);
  const c0=inter(Math.max(0,t-0.035)), c1=inter(t);
  if(!seen(c0[0],c0[1],isGlobe)||!seen(c1[0],c1[1],isGlobe)) return;
  const a=proj(c0), b=proj(c1); if(!a||!b) return;
  const dx=b[0]-a[0], dy=b[1]-a[1], L=Math.hypot(dx,dy);
  if(L<0.4||L>90) return;                         // 지도 이음매를 건널 때는 건너뛴다
  const ux=dx/L, uy=dy/L;
  ctx.beginPath();
  ctx.moveTo(b[0]+ux*s, b[1]+uy*s);
  ctx.lineTo(b[0]-ux*s*0.75-uy*s*0.62, b[1]-uy*s*0.75+ux*s*0.62);
  ctx.lineTo(b[0]-ux*s*0.28, b[1]-uy*s*0.28);
  ctx.lineTo(b[0]-ux*s*0.75+uy*s*0.62, b[1]-uy*s*0.75-ux*s*0.62);
  ctx.closePath(); ctx.fillStyle='rgba(43,110,246,'+alpha+')'; ctx.fill();
}
function paintPoints(ctx,path,proj,isGlobe,arcProgress,hoverIdx,flow){
  if(arcProgress>0){
    PTS.forEach((p,i)=>{
      if(!visible(p,proj,isGlobe)) return;
      const inter=lane(p);
      const pts=d3.range(0,arcProgress+1e-9,1/28).map(inter);
      if(pts.length<2) return;
      const lw=0.9+2.4*Math.sqrt((+p.value||0)/maxVal);
      ctx.beginPath(); path({type:'LineString',coordinates:pts});
      ctx.strokeStyle=i===hoverIdx?'rgba(43,110,246,.75)':'rgba(43,110,246,.38)';
      ctx.lineWidth=i===hoverIdx?lw+1:lw; ctx.lineCap='round'; ctx.stroke();

      // 머리 화살표 — 그리는 동안은 선 끝, 다 그린 뒤에는 한국 바로 앞에 선다
      arrow(ctx,proj,isGlobe,p,arcProgress<1?arcProgress:0.88,i===hoverIdx?1:.9,5+lw*0.85);
      // 흐름 화살표 — 선을 따라 계속 한국 쪽으로 흐른다
      if(arcProgress>=1){
        const t=0.12+0.72*((flow+i*0.17)%1);
        arrow(ctx,proj,isGlobe,p,t,.5,4+lw*0.5);
      }
    });
  }
  PTS.forEach((p,i)=>{
    if(!visible(p,proj,isGlobe)){p._xy=null;return;}
    const xy=proj([p.lon,p.lat]); p._xy=xy; if(!xy) return;
    const r=radius(p.value), on=i===hoverIdx;
    ctx.beginPath(); ctx.arc(xy[0],xy[1],r,0,2*Math.PI);
    ctx.fillStyle=p.color||'rgba(43,110,246,.55)';
    ctx.globalAlpha=on?.95:.72; ctx.fill(); ctx.globalAlpha=1;
    ctx.lineWidth=on?2.4:1.4; ctx.strokeStyle=on?'#12234a':'#fff'; ctx.stroke();
  });
  const k=proj(KOREA);
  if(k&&seen(KOREA[0],KOREA[1],isGlobe)){
    ctx.beginPath(); ctx.arc(k[0],k[1],5.5,0,2*Math.PI);
    ctx.fillStyle='#ff6b9a'; ctx.fill(); ctx.lineWidth=2; ctx.strokeStyle='#fff'; ctx.stroke();
    ctx.font='700 11px Pretendard, system-ui, sans-serif'; ctx.fillStyle='#12234a'; ctx.textAlign='center';
    ctx.fillText('대한민국',k[0],k[1]-11);
  }
  if(!isGlobe){
    ctx.font='600 10.5px Pretendard, system-ui, sans-serif'; ctx.textAlign='center'; ctx.fillStyle='#41537a';
    PTS.forEach(p=>{if(p._xy) ctx.fillText(p.name,p._xy[0],p._xy[1]+radius(p.value)+11);});
  }
}

let mode='globe', spinning=true, arc=0, hover=-1, mouse=null, drag=null, t0=performance.now();
function drawGlobe(){
  const f=((performance.now()-t0)/2600)%1;
  paintSphere(gx,pathG,projG,true);
  paintPoints(gx,pathG,projG,true,mode==='globe'?arc:0,mode==='globe'?hover:-1,f);
}
function drawMap(){
  const f=((performance.now()-t0)/2600)%1;
  paintSphere(mx,pathM,projM,false);
  paintPoints(mx,pathM,projM,false,mode==='map'?arc:0,mode==='map'?hover:-1,f);
}

/* ── 커서 정보 — 매 프레임 다시 찾는다(지구본이 돌아도 따라붙게) ───────── */
function hitTest(){
  if(!mouse||drag) return -1;
  let found=-1,best=1e9;
  PTS.forEach((p,i)=>{if(!p._xy)return;const d=Math.hypot(p._xy[0]-mouse[0],p._xy[1]-mouse[1]);
    if(d<radius(p.value)+6&&d<best){best=d;found=i;}});
  return found;
}
function fillTip(p){
  tip.innerHTML='<b>'+p.name+'</b><div class="v">'+p.value.toLocaleString(undefined,{maximumFractionDigits:1})+' '+UNIT+'</div>'
    +(p.note?'<div class="n">'+p.note+'</div>':'');
}
function syncTip(){
  const p=hover>=0?PTS[hover]:null;
  if(!p||!p._xy){tip.style.opacity=0;return;}
  tip.style.left=p._xy[0]+'px'; tip.style.top=p._xy[1]+'px'; tip.style.opacity=1;
}
function idleStatus(){
  return mode==='map'?'세계지도 — 공급국을 짚어 보세요':(spinning?'지구본 회전 중…':'멈춤 — 끌어서 돌릴 수 있습니다');
}

function loop(){
  try{
    const h=hitTest();
    if(h!==hover){
      hover=h;
      if(h>=0){fillTip(PTS[h]); statusEl.textContent=PTS[h].name+' — 커서를 떼면 다시 돕니다';}
      else statusEl.textContent=idleStatus();
    }
    if(spinning&&mode==='globe'&&hover<0&&!drag){const rot=projG.rotate();projG.rotate([rot[0]+0.2,rot[1],rot[2]]);}
    if(arc<1) arc=Math.min(1,arc+0.02);
    if(mode==='globe') drawGlobe(); else drawMap();
    syncTip();
  }catch(e){ statusEl.textContent='그리기 오류: '+(e&&e.message?e.message:e); return; }
  requestAnimationFrame(loop);
}
function setMode(next){
  mode=next; arc=0; t0=performance.now(); hover=-1; tip.style.opacity=0;
  wrap.classList.toggle('flat',next==='map');
  document.getElementById('b-globe').classList.toggle('on',next==='globe');
  document.getElementById('b-map').classList.toggle('on',next==='map');
  spinning=next==='globe';
  statusEl.textContent=idleStatus();
  drawGlobe(); drawMap();
}
wrap.addEventListener('mousemove',ev=>{
  const b=wrap.getBoundingClientRect(); mouse=[ev.clientX-b.left, ev.clientY-b.top];
});
wrap.addEventListener('mouseleave',()=>{mouse=null;});
wrap.addEventListener('mousedown',ev=>{if(mode!=='globe')return;
  drag={x:ev.clientX,y:ev.clientY,r:projG.rotate()};spinning=false;statusEl.textContent='끌어서 돌리는 중';});
window.addEventListener('mouseup',()=>{if(!drag)return;drag=null;
  if(mode==='globe'){spinning=true;statusEl.textContent=idleStatus();}});
window.addEventListener('mousemove',ev=>{if(!drag)return;
  projG.rotate([drag.r[0]+(ev.clientX-drag.x)*0.32,
    Math.max(-80,Math.min(80,drag.r[1]-(ev.clientY-drag.y)*0.32)),drag.r[2]]);});
document.getElementById('b-globe').onclick=()=>setMode('globe');
document.getElementById('b-map').onclick=()=>setMode('map');
document.getElementById('b-replay').onclick=()=>{arc=0;t0=performance.now();};
window.addEventListener('resize',()=>{size();drawGlobe();drawMap();});
size(); projG.rotate([-KOREA[0]+18,-20,0]); loop();
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then(r=>r.json()).then(topo=>{
  world=topojson.feature(topo,topo.objects.countries); drawGlobe(); drawMap();
}).catch(()=>{statusEl.textContent='지도 데이터를 불러오지 못해 경위선만 표시합니다(인터넷 연결 확인)';});
</script></body></html>
"""


def supply_globe(points: list[dict], height: int = 430, unit: str = "백만 USD", outbound: bool = False) -> None:
    """공급 흐름 지구본. outbound=True(수출)면 선 · 화살표가 한국 → 그 나라 방향."""
    html = (_GLOBE.replace("__DATA__", json.dumps(points, ensure_ascii=False))
            .replace("__DIR__", "true" if outbound else "false")
            .replace("__KOREA__", json.dumps(KOREA)).replace("__UNIT__", unit)
            .replace("__H__", str(height - 10)))
    components.html(html, height=height, scrolling=False)


# ════════════════════════════════════════════════════════════════════════════
# 3-2. 인트로 — 깨끗한 지구본(국가 표시·화살표 없음) 한 장
#      접속 직후 화면 전체를 덮었다가 스스로 사라지고, 그 밑에서 대시보드가 드러난다.
#      세션당 한 번만 뜬다(필터를 바꿔 다시 그려질 때는 뜨지 않는다). 새로고침하면 다시 본다.
# ════════════════════════════════════════════════════════════════════════════
_INTRO = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
<style>
  *{box-sizing:border-box}
  body{margin:0;background:transparent;overflow:hidden;user-select:none;
       font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif}
  #stage{width:100%;height:__H__px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px}
  /* 제목 · 부제 → 지구본 → 진행 막대 · 안내. 아이콘 칸 없이 글씨와 지구본(460px)만으로 균형을 맞춘다 */
  .ttl{font-size:32px;font-weight:800;letter-spacing:-.9px;color:#0f2c5e;line-height:1.15;
    animation:up .45s ease .04s both}
  .sub{margin-top:8px;font-size:14px;font-weight:600;color:#4a6da8;letter-spacing:-.2px;
    animation:up .45s ease .08s both}
  canvas{display:block;margin-top:14px;animation:fadein .55s ease .12s both}
  .bar{width:240px;height:3px;border-radius:3px;background:#cfe0f7;overflow:hidden;margin-top:16px;
    animation:up .45s ease .17s both}
  .bar i{display:block;height:100%;border-radius:3px;background:#2b6ef6;
    width:0;animation:fill __SEC__s linear .1s forwards}
  .msg{margin-top:10px;font-size:11.5px;font-weight:600;color:#6d89b8;letter-spacing:.3px;
    animation:up .45s ease .20s both}
  @keyframes up{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:none}}
  @keyframes fadein{from{opacity:0}to{opacity:1}}
  @keyframes fill{to{width:100%}}
</style></head><body>
<div id="stage">
  <div class="ttl">K-Defense</div>
  <div class="sub">방산 전자부품 수입 집중도 · 국산화 현황 대시보드</div>
  <canvas id="c" width="460" height="460"></canvas>
  <div class="bar"><i></i></div>
  <div class="msg">대시보드를 준비하는 중…</div>
</div>
<script>
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const DPR = Math.min(window.devicePixelRatio || 1, 2), S = 460;
cv.width = S * DPR; cv.height = S * DPR; cv.style.width = S + 'px'; cv.style.height = S + 'px';
ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

// 반지름을 캔버스의 42% 로 — 둘레 빛 번짐(shadowBlur)이 캔버스 끝에서 잘려 네모 테두리가 보이지 않게 여백을 둔다
const proj = d3.geoOrthographic().clipAngle(90).precision(0.4).scale(S * 0.42).translate([S / 2, S / 2]);
const path = d3.geoPath(proj, ctx), grat = d3.geoGraticule10();
let world = null;

function draw() {
  ctx.clearRect(0, 0, S, S);
  // 바다 — 왼쪽 위에서 빛이 드는 구
  ctx.beginPath(); path({type: 'Sphere'});
  const g = ctx.createRadialGradient(S * .36, S * .33, S * .05, S / 2, S / 2, S * .42);
  g.addColorStop(0, '#f2f9ff'); g.addColorStop(.5, '#d8eafd'); g.addColorStop(1, '#a9caee');
  ctx.fillStyle = g; ctx.fill();
  ctx.save(); ctx.shadowColor = 'rgba(43,110,246,.30)'; ctx.shadowBlur = 26; ctx.fill(); ctx.restore();
  // 경위선
  ctx.beginPath(); path(grat);
  ctx.strokeStyle = 'rgba(88,128,190,.26)'; ctx.lineWidth = .75; ctx.stroke();
  // 육지
  if (world) {
    ctx.beginPath(); path(world);
    ctx.fillStyle = '#ffffff'; ctx.fill();
    ctx.strokeStyle = '#bcd0ea'; ctx.lineWidth = .85; ctx.stroke();
  }
  // 테두리
  ctx.beginPath(); path({type: 'Sphere'});
  ctx.strokeStyle = 'rgba(43,110,246,.40)'; ctx.lineWidth = 1.5; ctx.stroke();
}
function spin() {
  const r = proj.rotate();
  proj.rotate([r[0] + 0.30, r[1], r[2]]);
  draw();
  requestAnimationFrame(spin);
}
proj.rotate([-30, -18, 0]);
draw(); spin();
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json")
  .then(r => r.json())
  .then(t => { world = topojson.feature(t, t.objects.countries); draw(); })
  .catch(() => {});   // 못 받으면 경위선만 — 인트로는 어차피 곧 사라진다
</script></body></html>
"""

DEMO_WAIT = 1.0          # 데모 전용 — 로딩 지구본이 보이도록 일부러 두는 시간(초). 실제 앱에는 없다
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
    st.html(f"""<style>
/* 인트로 바깥 감싸개도 흐름에서 뺀다 — 남겨 두면 높이 0 칸 + 칸 사이 간격(18px)만큼 첫 화면의 배너가 아래로 밀렸다
   (다른 페이지에 다녀오면 인트로를 다시 그리지 않아 제자리로 돌아오던 문제). 미니 사이드바와 같은 방식 */
[data-testid="stLayoutWrapper"]:has(> .st-key-intro){{position:fixed; left:0; top:0; width:0; height:0; margin:0; z-index:999999}}
.st-key-intro{{
  position:fixed; inset:0; z-index:999999; margin:0; padding:0;
  display:flex; align-items:center; justify-content:center;
  background:linear-gradient(160deg,#eef6ff 0%,#dfeafb 52%,#cfe0f7 100%);
  animation:introOut .4s ease {INTRO_SEC + .1}s forwards;
}}
.st-key-intro > div{{width:100%; max-width:680px}}
.st-key-intro iframe{{width:100%!important; border:0}}
@keyframes introOut{{
  from{{opacity:1}}
  to{{opacity:0; visibility:hidden; pointer-events:none}}
}}
</style>""")

# ── 로딩 중 지구본 ──────────────────────────────────────────────────────────
# 조회·필터를 바꿔 화면을 다시 그리는 동안 보여 주는 작은 지구본(인트로의 1/4 크기).
# st.spinner 대신 쓴다 — `with globe_loading("…"):` 블록이 끝나면 저절로 사라진다.
_MINI = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
<style>
  *{box-sizing:border-box}
  body{margin:0;background:transparent;overflow:hidden;user-select:none;
       font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif}
  #box{width:100%;height:__H__px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:11px;
       animation:in .3s ease both}
  canvas{display:block}
  .lbl{font-size:12px;font-weight:700;color:#4a6da8;letter-spacing:-.2px}
  .lbl i{font-style:normal;animation:blink 1.2s ease-in-out infinite}
  .lbl i:nth-child(2){animation-delay:.15s} .lbl i:nth-child(3){animation-delay:.3s}
  @keyframes in{from{opacity:0}to{opacity:1}}
  @keyframes blink{0%,80%,100%{opacity:.25}40%{opacity:1}}
</style></head><body>
<div id="box">
  <canvas id="c" width="300" height="300"></canvas>
  <div class="lbl">__LABEL__<i>.</i><i>.</i><i>.</i></div>
</div>
<script>
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const DPR = Math.min(window.devicePixelRatio || 1, 2), S = 300;
cv.width = S * DPR; cv.height = S * DPR; cv.style.width = S + 'px'; cv.style.height = S + 'px';
ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

const proj = d3.geoOrthographic().clipAngle(90).precision(0.4).scale(S * 0.40).translate([S / 2, S / 2]);
const path = d3.geoPath(proj, ctx), grat = d3.geoGraticule10();
let world = null;

function draw() {
  ctx.clearRect(0, 0, S, S);
  ctx.beginPath(); path({type: 'Sphere'});
  const g = ctx.createRadialGradient(S * .35, S * .32, S * .05, S / 2, S / 2, S * .42);
  g.addColorStop(0, '#f2f9ff'); g.addColorStop(.5, '#d8eafd'); g.addColorStop(1, '#a9caee');
  ctx.fillStyle = g; ctx.fill();
  ctx.save(); ctx.shadowColor = 'rgba(43,110,246,.28)'; ctx.shadowBlur = 22; ctx.fill(); ctx.restore();
  ctx.beginPath(); path(grat);
  ctx.strokeStyle = 'rgba(88,128,190,.26)'; ctx.lineWidth = .6; ctx.stroke();
  if (world) {
    ctx.beginPath(); path(world);
    ctx.fillStyle = '#ffffff'; ctx.fill();
    ctx.strokeStyle = '#bcd0ea'; ctx.lineWidth = .7; ctx.stroke();
  }
  ctx.beginPath(); path({type: 'Sphere'});
  ctx.strokeStyle = 'rgba(43,110,246,.40)'; ctx.lineWidth = 1.2; ctx.stroke();
}
function spin() {
  const r = proj.rotate();
  proj.rotate([r[0] + 0.85, r[1], r[2]]);     // 로딩용이라 인트로보다 빠르게 돈다
  draw();
  requestAnimationFrame(spin);
}
proj.rotate([-30, -18, 0]);
draw(); spin();
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json")
  .then(r => r.json())
  .then(t => { world = topojson.feature(t, t.objects.countries); draw(); })
  .catch(() => {});
</script></body></html>
"""


@contextlib.contextmanager
def globe_loading(text: str = "조회 중", height: int = 340, slot=None):
    """조회·집계가 끝날 때까지 작은 지구본을 돌린다. `with globe_loading("…"):` 로 쓰고,
    블록을 벗어나면(오류가 나도) 자리를 비운다. st.spinner 를 대신한다.
    slot(st.empty)을 주면 그 자리에 지구본을 그리고, 끝나도 비우지 않는다 — 곧이어 같은 자리에 결과를 그려
    지구본이 이전 결과 전체를 대신한다(자리를 따로 만들면 지구본만 이전 결과 위에 한 칸 끼어 보였다). 오류가 나면 비운다."""
    own = slot is None
    slot = slot if slot is not None else st.empty()
    # slot 을 받았으면 container 없이 지구본 요소 하나만 그 자리에 둔다 — 결과 container(블록) 자리를 요소가 대신해야
    # 이전 차트 · 탭이 한 번에 사라진다. container 로 감싸면 같은 블록으로 이어져 옛 차트가 실행이 끝날 때까지 남았다
    with (slot if not own else slot.container()):
        components.html(_MINI.replace("__H__", str(height - 10)).replace("__LABEL__", escape(text)),
                        height=height, scrolling=False)
    try:
        yield
    except BaseException:
        slot.empty()
        raise
    finally:
        if own:
            slot.empty()

# ════════════════════════════════════════════════════════════════════════════
# 3-3. 도넛 공통 — 반지름·둘레·굵기와 커서 반응(조각 확대 · 가운데 라벨)
# ════════════════════════════════════════════════════════════════════════════
R = 80                       # 도넛 반지름
C = round(2 * 3.141592653589793 * R, 2)      # 둘레 = stroke-dasharray 기준
STROKE = 48                  # 도넛 두께
# 커서를 올린 조각: 굵기를 키우면서 바깥쪽으로 확대한다. 안쪽 가장자리는 그대로 두어(≈56) 가운데 글자를
# 가리지 않고, 보이는 두께는 약 2배(48 → 96)가 된다.
HOVER_STROKE = 74
HOVER_SCALE = 1.3
HOVER_OUT = round(HOVER_SCALE * (R + HOVER_STROKE / 2))     # 커진 조각의 바깥 반지름 ≈ 152

# ── 도넛 공통: 조각(또는 범례)에 커서를 올리면 그 조각이 두꺼워지고 가운데에 라벨·값·비율이 뜬다 ──
# 조각 <circle> 에 class="hv", 가운데 글자는 .c-lab / .c-sub / .c-val, 범례 항목은 .lg 로 맞춰 두면 된다.
def _hover_css(cx: float, cy: float) -> str:
    return f"""
  .hv{{transform-origin:{cx}px {cy}px}}
  .hv.on{{stroke-width:{HOVER_STROKE};transform:scale({HOVER_SCALE})}}
  .focusing .hv:not(.on){{stroke-opacity:.28}}
  .c-val{{font-size:12px;font-weight:600;fill:#6b7a99;text-anchor:middle}}
  .lg{{padding:2px 6px;border-radius:6px;cursor:default;transition:background .15s, opacity .15s}}
  .lg.on{{background:#eaf1ff}}
  .focusing .lg:not(.on){{opacity:.4}}
"""

_HOVER_JS = r"""
<script>
(function () {
  const D = __DATA__, CX = __CX__, CY = __CY__, IN = __IN__, OUT = __OUT__, OUT_H = __OUTH__,
        ON = '__ON__', UNIT = __UNIT__;
  const stage = document.getElementById('stage');
  const svg = stage.querySelector('svg');
  const lab = stage.querySelector('.c-lab'), sub = stage.querySelector('.c-sub'), val = stage.querySelector('.c-val');
  const orig = [lab.textContent, sub.textContent];
  const segs = D.map((_, i) => document.getElementById('seg' + i));
  const lgs = [...stage.querySelectorAll('.lg')];
  let cur = -1;
  function focus(i) {
    if (i === cur) return; cur = i;
    stage.classList.toggle('focusing', i >= 0);
    segs.forEach((s, k) => s.classList.toggle('on', k === i));
    lgs.forEach((g, k) => g.classList.toggle('on', k === i));
    if (i < 0) { lab.textContent = orig[0]; sub.textContent = orig[1]; val.textContent = ''; return; }
    const d = D[i];
    lab.textContent = (d.p * 100).toFixed(1) + '%';
    sub.textContent = d.l;
    val.textContent = d.v.toLocaleString('ko-KR') + (UNIT ? ' ' + UNIT : '');
  }
  // 조각 판정은 각도로 한다 — 12시 = 0, 시계 방향(도넛을 -90° 돌려 그린 것과 같다)
  svg.addEventListener('mousemove', e => {
    if (!stage.classList.contains(ON)) return focus(-1);
    const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    const dx = p.x - CX, dy = p.y - CY, r = Math.hypot(dx, dy);
    if (r < IN || r > (cur >= 0 ? OUT_H : OUT)) return focus(-1);   // 커진 조각 위에서는 바깥 범위도 넓힌다
    let a = Math.atan2(dx, -dy) / (2 * Math.PI); if (a < 0) a += 1;
    let acc = 0, hit = D.length - 1;
    for (let k = 0; k < D.length; k++) { acc += D[k].p; if (a < acc) { hit = k; break; } }
    focus(hit);
  });
  svg.addEventListener('mouseleave', () => focus(-1));
  lgs.forEach((g, k) => {
    g.addEventListener('mouseenter', () => { if (stage.classList.contains(ON)) focus(k); });
    g.addEventListener('mouseleave', () => focus(-1));
  });
})();
</script>"""


def _hover_js(rows: list[tuple[str, float, str]], cx: float, cy: float, on: str, unit: str) -> str:
    """on = 도넛이 다 펼쳐졌을 때 #stage 에 붙는 클래스. 그 전에는 커서를 올려도 반응하지 않는다."""
    total = float(sum(float(v) for _, v, _ in rows))
    data = [{"l": str(l), "v": float(v), "p": float(v) / total} for l, v, _ in rows]
    return (_HOVER_JS.replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__CX__", str(cx)).replace("__CY__", str(cy))
            .replace("__IN__", str(R - STROKE / 2 - 4)).replace("__OUT__", str(R + STROKE / 2 + 4))
            .replace("__OUTH__", str(HOVER_OUT))
            .replace("__ON__", on).replace("__UNIT__", json.dumps(unit, ensure_ascii=False)))


# ── 도넛 — 바로 펼쳐지고, 조각(또는 범례)에 커서를 올리면 3-3 의 반응을 한다 ──
def hover_donut(rows: list[tuple[str, float, str]], center: str, sub: str = "", value_unit: str = "",
                height: int = 430, size: int = 340, top: bool = False) -> None:
    """도넛(커서를 올리면 조각이 커진다). size = 도넛 그림 크기(px, 기본 340).
    top=True 면 그림을 iframe 위쪽에 붙이고 그림 위 빈 여백을 잘라(커진 조각이 들어갈 자리만 남김) 제목 바로 아래에서 시작한다."""
    rows = [r for r in rows if float(r[1]) > 0]
    if not rows:
        components.html("<div style='font:12px system-ui;color:#6b7a99'>표시할 값이 없습니다.</div>", height=40)
        return
    total = float(sum(float(v) for _, v, _ in rows))
    segs, legend, css, cum = [], [], [], 0.0
    for i, (label, value, color) in enumerate(rows):
        pct = float(value) / total
        length = round(C * pct, 2)
        segs.append(f'<circle id="seg{i}" class="seg hv" cx="170" cy="170" r="{R}" stroke="{color}" />')
        css.append(f".shown #seg{i}{{stroke-dasharray:{length} {C};stroke-dashoffset:{round(-cum, 2)}}}")
        cum += length
        legend.append(f'<div class="lg"><span style="background:{color}"></span>{escape(label)} '
                      f'<b>{pct * 100:.1f}%</b></div>')
    html = (_DONUT_TPL.replace("__SEGS__", "\n      ".join(segs))
            .replace("__LEGEND__", "\n    ".join(legend))
            .replace("__CSS__", "\n  ".join(css) + _hover_css(170, 170))
            .replace("__CENTER__", escape(center))
            .replace("__SUB__", escape(sub))
            .replace("__C__", str(C))
            .replace("__H__", str(height - 10))
            .replace("__JC__", "flex-start" if top else "center")
            # top: viewBox 를 위 14 만큼 잘라 그린다(커진 조각 바깥 반지름 HOVER_OUT ≈ 152 → 위 18 이 필요, 4 남김)
            .replace("__VB__", "0 14 340 312" if top else "0 0 340 340")
            .replace("__SW__", str(size)).replace("__SH__", str(round(size * 312 / 340) if top else size))
            .replace("__HOVER__", _hover_js(rows, 170, 170, "shown", value_unit)))
    components.html(html, height=height, scrolling=False)


_DONUT_TPL = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  *{box-sizing:border-box}
  body{margin:0;background:transparent;overflow:hidden;user-select:none;
       font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;color:#16233f}
  #stage{width:100%;height:__H__px;display:flex;flex-direction:column;align-items:center;justify-content:__JC__}
  .ring-g{transform:rotate(-90deg);transform-origin:170px 170px}   /* 12시에서 시작 */
  .seg{fill:none;stroke-width:48;stroke-dasharray:0 __C__;
    transition:stroke-dasharray 1s cubic-bezier(.2,.8,.25,1), opacity .3s ease,
               stroke-width .25s cubic-bezier(.2,.8,.25,1), stroke-opacity .2s ease,
               transform .25s cubic-bezier(.2,.8,.25,1)}
  .c-lab{font-size:24px;font-weight:800;fill:#12234a;text-anchor:middle;letter-spacing:-.6px}
  .c-sub{font-size:12.5px;fill:#6b7a99;text-anchor:middle}
  .legend{display:flex;gap:7px 12px;flex-wrap:wrap;justify-content:center;max-width:460px;margin-top:6px;
    font-size:11.5px;color:#5d6d8c}
  .lg span{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:5px;vertical-align:middle}
  .lg b{color:#16233f;font-weight:700}
  __CSS__
</style></head><body>
<div id="stage">
  <svg width="__SW__" height="__SH__" viewBox="__VB__">
    <g class="ring-g">
      __SEGS__
    </g>
    <text x="170" y="165" class="c-lab">__CENTER__</text>
    <text x="170" y="185" class="c-sub">__SUB__</text>
    <text x="170" y="203" class="c-val"></text>
  </svg>
  <div class="legend">
    __LEGEND__
  </div>
</div>
<script>setTimeout(() => document.getElementById('stage').classList.add('shown'), 30);</script>
__HOVER__
</body></html>
"""

# ════════════════════════════════════════════════════════════════════════════
# 3-6. 국가별 수입·수출 분포 지도 · 지역(시·도)별 수입·수출 분포 지도
#      둘 다 오른쪽 위 「수입 | 수출」 단추로 바꾼다(다시 그리지 않고 브라우저 안에서 색만 바뀐다).
#      지도 모양은 CDN 에서 받는다 — 세계: world-atlas, 시·도: southkorea-maps(통계청 2013).
# ════════════════════════════════════════════════════════════════════════════
_MAP_HEAD = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;
       color:#16233f;background:transparent;overflow:hidden;user-select:none}
  #wrap{position:relative;width:100%;height:__H__px;border-radius:12px;overflow:hidden;
        background:linear-gradient(170deg,#f6faff,#e9f1fc);--c:#2b6ef6}
  #top{position:absolute;left:14px;right:12px;top:10px;display:flex;align-items:center;justify-content:space-between;z-index:6}
  #unit{font-size:11px;color:#6b7a99;font-weight:600}
  #seg{display:flex;background:#fff;border:1px solid #dde5f2;border-radius:11px;padding:3px;box-shadow:0 1px 3px rgba(19,42,84,.06)}
  #seg button{font:700 12px Pretendard,system-ui,sans-serif;color:#5b6f94;background:transparent;border:0;border-radius:8px;
    padding:6px 22px;cursor:pointer;transition:all .18s}
  #seg button:hover{color:var(--c)}
  #seg button.on{color:#fff;background:var(--c);box-shadow:0 3px 10px rgba(19,42,84,.18)}
  #seg.one{display:none}
  svg{display:block}
  .land{stroke:#fff;stroke-width:.6;transition:fill .55s ease,opacity .15s}
  .land.has:hover{opacity:.78}
  #tip{position:absolute;z-index:9;pointer-events:none;opacity:0;transform:translate(-50%,-120%);background:#fff;
    border:1px solid #dde5f2;border-radius:10px;padding:8px 11px;box-shadow:0 8px 24px rgba(19,42,84,.16);
    transition:opacity .12s;white-space:nowrap;font-size:11.5px;color:#44567a;line-height:1.55}
  #tip b{display:block;font-size:12.5px;font-weight:800;color:#16233f;letter-spacing:-.3px}
  #tip em{font-style:normal;font-weight:800}
  #msg{position:absolute;inset:0;display:grid;place-items:center;font-size:12px;color:#6b7a99;pointer-events:none}
  @keyframes pop{from{opacity:0;transform:translate(-50%,-50%) scale(.7)}to{opacity:1;transform:translate(-50%,-50%)}}
  @keyframes fade{from{opacity:0}to{opacity:1}}
"""

_WORLD_MAP = _MAP_HEAD + r"""
  /* 나라 경계(흰 선)가 보이게 — 값 없는 나라를 한 단계 진한 회청색으로 칠하고(paint) 선을 조금 굵게 */
  .land{stroke:#fff;stroke-width:1}
  #svg{position:absolute;inset:0;width:100%;height:100%}
  .dotc{stroke:#fff;stroke-width:1.3;transition:fill .55s}
  .lead{stroke:#8ea3c4;stroke-width:1;stroke-dasharray:2 2;animation:fade .4s ease both}
  .anc{fill:#12234a;animation:fade .4s ease both}
  #labels{position:absolute;inset:0;pointer-events:none;z-index:4}
  .lb{position:absolute;transform:translate(-50%,-50%);background:rgba(255,255,255,.96);border:1px solid #d5e0f2;
    border-radius:9px;padding:4px 10px;text-align:center;box-shadow:0 4px 12px rgba(19,42,84,.13);white-space:nowrap;
    animation:pop .42s cubic-bezier(.18,.89,.32,1.3) both}
  .lb b{display:block;font-size:11.5px;font-weight:800;color:#16233f;letter-spacing:-.3px;line-height:1.3}
  .lb span{display:block;font-size:13px;font-weight:800;letter-spacing:-.3px;line-height:1.25}
  #legend{position:absolute;left:12px;bottom:12px;z-index:5;background:rgba(255,255,255,.92);border:1px solid #dde5f2;
    border-radius:10px;padding:7px 12px;font-size:11px;color:#44567a}
  #legend div{display:flex;align-items:center;gap:7px;line-height:1.8}
  #legend i{width:12px;height:12px;border-radius:50%;display:inline-block}
</style></head><body>
<div id="wrap">
  <div id="top"><span id="unit"></span><div id="seg"></div></div>
  <svg id="svg"><g id="gl"></g><g id="gd"></g><g id="gk"></g></svg>
  <div id="labels"></div><div id="legend"></div><div id="tip"></div>
  <div id="msg">세계지도를 불러오는 중…</div>
</div>
<script>
const D = __DATA__, INFO = __INFO__, MODES = __MODES__, UNIT = "__UNIT__", TOPN = __TOPN__, NOTE = "__NOTE__";
// 1% 미만은 수입 · 수출 모두 회색(값 없는 나라 #d3dbe7 보다 한 단계 진하게) — 아주 옅은 파랑 · 초록은 값 없는 나라와 헷갈렸다
const PAL = {imp: {c: '#2b6ef6', t: '#1c4ec4', bins: ['#1543c2', '#2f6ff0', '#6b9cf5', '#a9c7fa', '#a3adbd']},
             exp: {c: '#0fa595', t: '#0b7f78', bins: ['#0b7f78', '#14a89c', '#46c7b9', '#93e1d5', '#a3adbd']}};
const CUT = [20, 10, 5, 1, 0], CUT_TXT = ['20% 이상', '10 - 20%', '5 - 10%', '1 - 5%', '1% 미만'];
const KOR = {imp: '수입', exp: '수출'};
const wrap = document.getElementById('wrap'), tip = document.getElementById('tip'), labels = document.getElementById('labels');
const gl = d3.select('#gl'), gd = d3.select('#gd'), gk = d3.select('#gk');
const byId = {}; for (const [n, v] of Object.entries(INFO)) byId[v[0]] = n;
const proj = d3.geoNaturalEarth1(), path = d3.geoPath(proj);
let mode = MODES[0], world = null;

function shares(m) {
  const o = D[m] || {}, t = Object.values(o).reduce((a, b) => a + b, 0) || 1, r = {};
  for (const k in o) if (o[k] > 0) r[k] = {v: o[k], p: o[k] / t * 100};
  return r;
}
function bin(p) { for (let i = 0; i < CUT.length; i++) if (p >= CUT[i]) return i; return CUT.length - 1; }
function tipShow(ev, n, s, other) {
  const b = wrap.getBoundingClientRect();
  if (!s) { tip.style.opacity = 0; return; }
  const o = other && other.v ? '<br>' + KOR[mode === 'imp' ? 'exp' : 'imp'] + ' ' + other.v.toLocaleString(undefined, {maximumFractionDigits: 1}) + ' ' + UNIT : '';
  tip.innerHTML = '<b>' + n + '</b>' + KOR[mode] + ' <em style="color:' + PAL[mode].t + '">'
    + s.v.toLocaleString(undefined, {maximumFractionDigits: 1}) + ' ' + UNIT + '</em> · ' + s.p.toFixed(1) + '%' + o;
  tip.style.left = (ev.clientX - b.left) + 'px'; tip.style.top = (ev.clientY - b.top) + 'px'; tip.style.opacity = 1;
}
function tipHide() { tip.style.opacity = 0; }

function layout() {
  const W = wrap.clientWidth, H = wrap.clientHeight;
  if (!W || !H || !world) return false;
  const feats = world.features.filter(f => f.id !== '010');           // 남극은 뺀다
  proj.fitExtent([[8, 44], [W - 8, H - 4]], {type: 'FeatureCollection', features: feats});
  d3.select('#svg').attr('viewBox', '0 0 ' + W + ' ' + H);
  gl.selectAll('path').data(feats, f => f.id).join('path').attr('class', 'land').attr('d', path);
  return true;
}
function paint() {
  const S = shares(mode), O = shares(mode === 'imp' ? 'exp' : 'imp'), P = PAL[mode];
  wrap.style.setProperty('--c', P.c);
  document.getElementById('unit').textContent = '(단위: ' + UNIT + ' · ' + KOR[mode] + ' 합계 대비 비중' + (NOTE ? ' · ' + NOTE : '') + ')';
  gl.selectAll('path')
    .classed('has', f => !!S[byId[f.id]])
    .attr('fill', f => { const s = S[byId[f.id]]; return s ? P.bins[bin(s.p)] : '#d3dbe7'; })   // 값 없는 나라 — 흰 경계가 보이는 회청색
    .on('mousemove', (ev, f) => { const n = byId[f.id]; tipShow(ev, n, S[n], O[n]); })
    .on('mouseleave', tipHide);
  // world-atlas 110m 에 면이 없는 작은 나라(싱가포르 등)는 점으로 찍는다
  const have = new Set(world.features.map(f => f.id));
  const dots = Object.keys(S).filter(n => INFO[n] && !have.has(INFO[n][0]));
  gd.selectAll('circle').data(dots, d => d).join('circle').attr('class', 'dotc').attr('r', 5.5)
    .attr('cx', n => proj([INFO[n][2], INFO[n][1]])[0]).attr('cy', n => proj([INFO[n][2], INFO[n][1]])[1])
    .attr('fill', n => P.bins[bin(S[n].p)])
    .on('mousemove', (ev, n) => tipShow(ev, n, S[n], O[n])).on('mouseleave', tipHide);
  // 상위 국가 라벨 — 옮긴 라벨은 점선으로 나라와 잇는다
  labels.innerHTML = ''; gk.selectAll('*').remove();
  Object.entries(S).filter(([n]) => INFO[n]).sort((a, b) => b[1].v - a[1].v).slice(0, TOPN).forEach(([n, s], k) => {
    const [, la, lo, dx, dy] = INFO[n], xy = proj([lo, la]);
    if (!xy) return;
    if (dx || dy) {
      gk.append('line').attr('class', 'lead').attr('x1', xy[0]).attr('y1', xy[1]).attr('x2', xy[0] + dx).attr('y2', xy[1] + dy);
      gk.append('circle').attr('class', 'anc').attr('r', 2.4).attr('cx', xy[0]).attr('cy', xy[1]);
    }
    const el = document.createElement('div');
    el.className = 'lb'; el.style.left = (xy[0] + dx) + 'px'; el.style.top = (xy[1] + dy) + 'px';
    el.style.animationDelay = (k * .06) + 's';
    el.innerHTML = '<b>' + n + '</b><span style="color:' + P.t + '">' + s.p.toFixed(1) + '%</span>';
    labels.appendChild(el);
  });
  document.getElementById('legend').innerHTML = CUT_TXT.map((t, i) => '<div><i style="background:' + P.bins[i] + '"></i>' + t + '</div>').join('');
  document.querySelectorAll('#seg button').forEach(b => b.classList.toggle('on', b.dataset.m === mode));
}
const seg = document.getElementById('seg');
seg.innerHTML = MODES.map(m => '<button data-m="' + m + '">' + KOR[m] + '</button>').join('');
if (MODES.length < 2) seg.classList.add('one');
seg.querySelectorAll('button').forEach(b => b.onclick = () => { mode = b.dataset.m; if (world) paint(); });
new ResizeObserver(() => { if (layout()) paint(); }).observe(wrap);     // 탭 안에 숨어 있다가 보일 때도 다시 맞춘다
let lastW = 0;                                   // 숨은 탭에서 크기 알림을 놓쳐도 폭이 바뀌면 다시 그린다
setInterval(() => { if (world && wrap.clientWidth && wrap.clientWidth !== lastW) { lastW = wrap.clientWidth; if (layout()) paint(); } }, 400);
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then(r => r.json()).then(t => {
  world = topojson.feature(t, t.objects.countries);
  document.getElementById('msg').remove();
  if (layout()) paint();
}).catch(() => { document.getElementById('msg').textContent = '세계지도를 불러오지 못했습니다(인터넷 연결 확인)'; });
</script></body></html>
"""


def country_map(imp: dict, exp: dict, modes: tuple[str, ...] = ("imp", "exp"), height: int = 400,
                unit: str = "백만 USD", top_n: int = 6, note: str = "") -> None:
    """국가별 수입·수출 분포(단계 구분도). 색 = 합계 대비 비중 구간, 상위 top_n 개국은 이름·비중 라벨.
    modes 가 하나면 전환 단추를 숨긴다."""
    info = {n: v for n, v in WORLD.items() if n in imp or n in exp}
    html = (_WORLD_MAP.replace("__DATA__", json.dumps({"imp": imp, "exp": exp}, ensure_ascii=False))
            .replace("__INFO__", json.dumps(info, ensure_ascii=False))
            .replace("__MODES__", json.dumps(list(modes))).replace("__UNIT__", unit)
            .replace("__TOPN__", str(top_n)).replace("__NOTE__", escape(note))
            .replace("__H__", str(height - 10)))
    components.html(html, height=height, scrolling=False)


_REGION_MAP = _MAP_HEAD + r"""
  #body{position:absolute;inset:48px 12px 12px 12px;display:flex;gap:12px}
  #mapbox{position:relative;flex:1 1 auto;min-width:0}
  #svg{position:absolute;inset:0;width:100%;height:100%}
  .rl{font-size:11.5px;font-weight:800;text-anchor:middle;dominant-baseline:middle;pointer-events:none;letter-spacing:-.3px;
      paint-order:stroke;stroke-linejoin:round;animation:fade .5s ease .25s both}
  .rl.lt{fill:#10214a;stroke:rgba(255,255,255,.9);stroke-width:3.2px}
  .land{stroke-width:1}
  #side{flex:0 0 172px;display:flex;flex-direction:column;gap:7px}
  .lgd{background:rgba(255,255,255,.94);border:1px solid #dde5f2;border-radius:10px;padding:6px 11px;font-size:11px;color:#44567a;
       transition:opacity .25s, box-shadow .25s}
  .lgd.on{box-shadow:0 4px 14px rgba(19,42,84,.10);border-color:var(--c)}
  .lgd b{display:block;font-size:11.5px;color:#16233f;font-weight:800;margin-bottom:4px;line-height:1.35}
  .lgd div{display:flex;align-items:center;gap:8px;line-height:1.5}
  .lgd i{width:20px;height:11px;border-radius:3px;display:inline-block}
  .top{background:rgba(255,255,255,.94);border:1px solid #dde5f2;border-radius:10px;padding:8px 11px;font-size:11px}
  .top b{display:block;font-size:11.5px;color:#16233f;font-weight:800;margin-bottom:5px}
  .tr{display:grid;grid-template-columns:30px 1fr 42px;align-items:center;gap:6px;height:17px;color:#44567a}
  .tr .bar{height:8px;border-radius:3px;background:#eef2f9;position:relative;overflow:hidden}
  .tr .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:3px;transition:width .5s ease}
  .tr span:last-child{text-align:right;font-weight:700;color:#16233f}
</style></head><body>
<div id="wrap">
  <div id="top"><span id="unit">(단위: 천 USD · 시·도 = 통관 신고 기준 소재지)</span><div id="seg"></div></div>
  <div id="body">
    <div id="mapbox"><svg id="svg"><g id="gl"></g><g id="gt"></g></svg></div>
    <div id="side"></div>
  </div>
  <div id="tip"></div>
  <div id="msg">시·도 지도를 불러오는 중…</div>
</div>
<script>
const R = __DATA__;
const PAL = {imp: {c: '#2b6ef6', bins: ['#1553d6', '#4a86f2', '#86aef6', '#bcd3fa', '#e3edfd']},
             exp: {c: '#0fa595', bins: ['#0b8f86', '#2cb5a7', '#6fd0c3', '#aee6dd', '#dcf5f0']}};
const CUT = [1000, 500, 100, 10, 0], TXT = ['≥ 1,000', '500 - 1,000', '100 - 500', '10 - 100', '< 10'];
const KOR = {imp: '수입', exp: '수출'}, IDX = {imp: 1, exp: 2};
const wrap = document.getElementById('wrap'), box = document.getElementById('mapbox'), tip = document.getElementById('tip');
const gl = d3.select('#gl'), gt = d3.select('#gt');
const proj = d3.geoMercator(), path = d3.geoPath(proj);
let mode = 'imp', geo = null;

function bin(v) { for (let i = 0; i < CUT.length; i++) if (v >= CUT[i]) return i; return CUT.length - 1; }
function fmt(v) { return Math.round(v).toLocaleString(); }
function layout() {
  const W = box.clientWidth, H = box.clientHeight;
  if (!W || !H || !geo) return false;
  proj.fitExtent([[4, 4], [W - 4, H - 4]], geo);
  d3.select('#svg').attr('viewBox', '0 0 ' + W + ' ' + H);
  gl.selectAll('path').data(geo.features, f => f.properties.code).join('path').attr('class', 'land has').attr('d', path)
    .on('mousemove', (ev, f) => {
      const r = R[f.properties.code]; if (!r) return;
      const b = wrap.getBoundingClientRect();
      tip.innerHTML = '<b>' + f.properties.name + '</b>수입 <em style="color:#1c4ec4">' + fmt(r[1]) + '</em> · 수출 <em style="color:#0b7f78">'
        + fmt(r[2]) + '</em> 천 USD<br>무역수지 ' + (r[2] - r[1] >= 0 ? '+' : '') + fmt(r[2] - r[1]) + ' 천 USD';
      tip.style.left = (ev.clientX - b.left) + 'px'; tip.style.top = (ev.clientY - b.top) + 'px'; tip.style.opacity = 1;
    })
    .on('mouseleave', () => tip.style.opacity = 0);
  gt.selectAll('text').data(geo.features, f => f.properties.code).join('text')
    .attr('x', f => path.centroid(f)[0] + ((R[f.properties.code] || [])[3] || 0))
    .attr('y', f => path.centroid(f)[1] + ((R[f.properties.code] || [])[4] || 0))
    .text(f => (R[f.properties.code] || [f.properties.name])[0]);
  return true;
}
function legend(m) {       // 고른 쪽(수입 · 수출) 범례 하나만 — 두 범례가 같은 자리에 번갈아 나온다
  return '<div class="lgd on" style="--c:' + PAL[m].c + '"><b>' + KOR[m] + ' 금액<br>(천USD)</b>'
    + TXT.map((t, i) => '<div><i style="background:' + PAL[m].bins[i] + '"></i>' + t + '</div>').join('') + '</div>';
}
function paint() {
  const P = PAL[mode], k = IDX[mode];
  wrap.style.setProperty('--c', P.c);
  gl.selectAll('path').attr('fill', f => { const r = R[f.properties.code]; return r ? P.bins[bin(r[k])] : '#eef3fa'; });
  gt.selectAll('text').attr('class', 'rl lt');      // 짙은 칸에서도 흰 테두리 글자로 읽힌다
  const rows = Object.values(R).sort((a, b) => b[k] - a[k]).slice(0, 5), mx = rows[0][k] || 1;
  document.getElementById('side').innerHTML = legend(mode)
    + '<div class="top"><b>' + KOR[mode] + ' 상위 5개 시·도</b>' + rows.map(r => '<div class="tr"><span>' + r[0]
    + '</span><span class="bar"><i style="width:' + (r[k] / mx * 100).toFixed(0) + '%;background:' + P.bins[1] + '"></i></span><span>'
    + fmt(r[k]) + '</span></div>').join('') + '</div>';
  document.querySelectorAll('#seg button').forEach(b => b.classList.toggle('on', b.dataset.m === mode));
}
const seg = document.getElementById('seg');
seg.innerHTML = ['imp', 'exp'].map(m => '<button data-m="' + m + '">' + KOR[m] + '</button>').join('');
seg.querySelectorAll('button').forEach(b => b.onclick = () => { mode = b.dataset.m; paint(); });
paint();
new ResizeObserver(() => { if (layout()) paint(); }).observe(box);
let lastW = 0;
setInterval(() => { if (geo && box.clientWidth && box.clientWidth !== lastW) { lastW = box.clientWidth; if (layout()) paint(); } }, 400);
fetch("https://cdn.jsdelivr.net/gh/southkorea/southkorea-maps@master/kostat/2013/json/skorea_provinces_topo_simple.json")
  .then(r => r.json()).then(t => {
    geo = topojson.feature(t, t.objects[Object.keys(t.objects)[0]]);
    document.getElementById('msg').remove();
    if (layout()) paint();
  }).catch(() => { document.getElementById('msg').textContent = '시·도 지도를 불러오지 못했습니다(인터넷 연결 확인)'; });
</script></body></html>
"""


def region_map(height: int = 440) -> None:
    """시·도별 수입·수출 분포. 색 = 금액 구간(천 USD), 오른쪽에 고른 쪽(수입/수출) 범례 하나와 상위 5개 시·도."""
    html = (_REGION_MAP.replace("__DATA__", json.dumps(REGIONS, ensure_ascii=False))
            .replace("__H__", str(height - 10)))
    components.html(html, height=height, scrolling=False)


# ════════════════════════════════════════════════════════════════════════════
# 4. 샘플 데이터 — 전부 가짜다(실제 DB 값 아님)
# ════════════════════════════════════════════════════════════════════════════
YEARS = list(range(2016, 2027))

COUNTRIES = [
    # 이름, 위도, 경도, 수입액(백만 USD), 색, 1위 품목군
    ("미국", 38.0, -97.0, 8942, SERIES[0], "항공기 부분품, 항공 항행기기, 레이더 기기"),
    ("독일", 51.0, 10.4, 3120, SERIES[1], "컴퍼스"),
    ("일본", 36.2, 138.2, 2815, SERIES[2], "증폭기 IC"),
    ("중국", 35.8, 104.1, 2420, SERIES[3], "안테나, 통신 · 레이더 부분품"),
    ("프랑스", 46.2, 2.2, 1906, SERIES[4], "항행기기 부분품"),
    ("대만", 23.6, 121.0, 1540, SERIES[5], "기타 IC, 증폭기 IC"),
    ("싱가포르", 1.35, 103.8, 980, "#34d399", "무선항행"),
]

GLOBE_PTS = [{"name": n, "lat": la, "lon": lo, "value": v, "color": c, "note": "1위 품목군: " + note}
             for n, la, lo, v, c, note in COUNTRIES]

# 품목군별 1위 공급국 점유율 — 분석 대상 13개(TARGET_HS). (HS6, 품목군, 1위국, 1위 점유율 %, HHI, 수입국 수)
# 발표 자료(2026-09-22 포트폴리오)와 맞춘 값: 2025 기준 HHI 2,500 초과 7개 · 1위국 50% 초과 5개 ·
# 가장 심한 것 = 항공기 부분품 HHI 5,887 · 미국 76.4%. 나머지 품목군별 값은 샘플
ITEMS = [
    ("880730", "항공기 부분품", "미국", 76.4, 5887, 14),
    ("901420", "항공 항행기기", "미국", 71.4, 5320, 8),
    ("852610", "레이더 기기", "미국", 58.9, 4120, 7),
    ("854231", "프로세서 IC", "대만", 52.3, 3480, 12),
    ("841191", "터보제트 부분품", "미국", 51.2, 3210, 9),
    ("901490", "항행기기 부분품", "프랑스", 46.3, 2940, 12),
    ("852910", "안테나", "중국", 41.8, 2610, 16),
    ("901410", "컴퍼스", "독일", 38.2, 2280, 10),
    ("854233", "증폭기 IC", "일본", 36.4, 2150, 14),
    ("852990", "통신 · 레이더 부분품", "중국", 33.9, 1980, 17),
    ("901480", "기타 항행기기", "미국", 32.1, 1870, 13),
    ("854239", "기타 IC", "대만", 31.4, 1820, 19),
    ("852691", "무선항행", "싱가포르", 28.7, 1640, 13),
]

# 분석 대상 13개 연간 수입 · 수출(백만 USD). 2025 = 발표 자료 478.2억 · 606.6억 달러, 앞 연도는 샘플.
# 2026 은 1~8월 부분연도라 추세에서 뺀다(완결연도 2016~2025)
IMPORT_TREND = pd.DataFrame({
    "연도": YEARS[:-1],
    "수입": [15380, 18370, 20960, 25090, 28400, 31810, 35430, 40120, 44960, 47820],
    "수출": [14030, 16670, 20690, 26450, 28790, 33190, 39900, 47500, 54150, 60660],
})

# 국산화개발 전자 계열 군급 분포 — 합계 2,717행 · FSG 60(광섬유) 0행은 발표 자료 값, 58 · 59 나눔은 샘플
FSG_DIST = [("FSG 58 (통신 · 탐지 장비)", 1512, SERIES[0]), ("FSG 59 (전기 · 전자 구성품)", 1205, SERIES[1]),
            ("FSG 60 (광섬유)", 0, SERIES[2])]

LOCAL_STATUS = [("국산화 완료", 1206, SERIES[0]), ("국산화 추진", 200, SERIES[1]),
                ("진행중", 419, SERIES[2]), ("수입품목", 892, ETC)]

EQUIPMENT = [("K9 자주포", 842, SERIES[0]), ("KF-21 전투기", 621, SERIES[1]), ("이지스 구축함", 518, SERIES[2]),
             ("천무 다연장로켓", 422, SERIES[3]), ("K2 전차", 361, SERIES[4])]

BUDGET = pd.DataFrame({
    "연도": YEARS,
    "국외조달 예산(억 원)": [12400, 13100, 14800, 16200, 17900, 19400, 21200, 23800, 26100, 28400, 30200],
    "전체 방위력개선비 대비(%)": [18.2, 18.9, 19.4, 20.1, 20.8, 21.2, 21.9, 22.4, 23.1, 23.6, 24.0],
})

PLAN_BY_FSC = [("5820 무선 통신장비", 1240, SERIES[0]), ("5935 커넥터", 892, SERIES[1]), ("5962 전자 집적회로", 621, SERIES[2]),
               ("5999 기타 전기 · 전자 부품", 418, SERIES[3]), ("5865 전자전 장비", 352, SERIES[4])]

# ③ 조달계획 대비 국산화 군급 — PLAN_BY_FSC 군급마다 국산화개발 기록 수(샘플). 두 값은 출처 · 단위가 달라 비율로 계산하지 않는다
LOCAL_BY_FSC = {"5820 무선 통신장비": 386, "5935 커넥터": 512, "5962 전자 집적회로": 148, "5999 기타 전기 · 전자 부품": 297, "5865 전자전 장비": 64}

ARMY_MIX = pd.DataFrame({
    "연도": YEARS[-6:],
    "육군": [312, 348, 390, 421, 468, 402],
    "해군": [198, 214, 243, 268, 291, 254],
    "공군": [264, 289, 318, 352, 386, 331],
    "해병대": [58, 63, 71, 79, 86, 74],
})

# COUNTRIES 7개국 밖의 공급국(이름, ISO3, 수입액). 2016~2025 합산, 백만 USD
MAP_OTHERS = [("영국", "GBR", 860), ("이스라엘", "ISR", 740), ("이탈리아", "ITA", 520), ("스위스", "CHE", 410),
              ("캐나다", "CAN", 380), ("네덜란드", "NLD", 350), ("스웨덴", "SWE", 240), ("말레이시아", "MYS", 210),
              ("베트남", "VNM", 180), ("인도", "IND", 95), ("호주", "AUS", 88), ("스페인", "ESP", 72),
              ("튀르키예", "TUR", 41), ("핀란드", "FIN", 33), ("노르웨이", "NOR", 27), ("폴란드", "POL", 12),
              ("체코", "CZE", 9), ("브라질", "BRA", 8.5), ("멕시코", "MEX", 6.2), ("남아공", "ZAF", 3.1),
              ("인도네시아", "IDN", 2.4), ("필리핀", "PHL", 1.8), ("사우디아라비아", "SAU", 0.6)]

# 국가별 수입·수출 분포 지도 — 이름: [ISO 숫자코드(world-atlas id), 위도, 경도, 라벨 dx, dy(px)].
# dx·dy 는 가까운 나라끼리 라벨이 겹치지 않게 옮기는 거리(0 이면 나라 위에 바로 얹는다).
WORLD = {
    "미국": ["840", 39.0, -98.0, 0, 0], "캐나다": ["124", 58.0, -105.0, 0, -6], "멕시코": ["484", 23.6, -102.5, 0, 0],
    "브라질": ["076", -10.0, -52.0, 0, 0], "영국": ["826", 53.0, -1.5, -42, -26], "프랑스": ["250", 46.6, 2.4, -60, 16],
    "독일": ["276", 51.0, 10.4, -30, -36], "네덜란드": ["528", 52.2, 5.5, -46, -8], "스위스": ["756", 46.8, 8.2, -18, 34],
    "이탈리아": ["380", 42.8, 12.5, 18, 36], "스페인": ["724", 40.0, -3.7, -30, 24], "스웨덴": ["752", 62.0, 15.0, 0, -30],
    "노르웨이": ["578", 61.0, 9.0, -34, -30], "핀란드": ["246", 63.0, 26.0, 30, -30], "에스토니아": ["233", 58.7, 25.5, 40, -22],
    "폴란드": ["616", 52.0, 19.4, 32, -38], "체코": ["203", 49.8, 15.5, 0, 0], "루마니아": ["642", 45.9, 25.0, 34, 14],
    "튀르키예": ["792", 39.0, 35.0, 30, -18], "이스라엘": ["376", 31.2, 34.9, -34, 24], "이집트": ["818", 26.5, 30.0, -30, 26],
    "사우디아라비아": ["682", 24.0, 45.0, -46, 22], "아랍에미리트": ["784", 24.0, 54.0, 48, 20], "인도": ["356", 22.0, 79.0, 0, 0],
    "중국": ["156", 34.0, 103.0, -22, 0], "일본": ["392", 36.5, 138.5, 46, -26], "대만": ["158", 23.7, 121.0, 52, 24],
    "베트남": ["704", 15.0, 106.5, -34, 22], "태국": ["764", 15.5, 101.0, -40, 10], "말레이시아": ["458", 3.8, 102.3, -44, 14],
    "싱가포르": ["702", 1.35, 103.8, 34, 22], "인도네시아": ["360", -2.5, 118.0, 0, 16], "필리핀": ["608", 12.8, 122.0, 40, 8],
    "호주": ["036", -25.0, 134.0, 0, 0], "남아공": ["710", -29.0, 24.7, 0, 0],
}
TRADE_IMP = {c[0]: c[3] for c in COUNTRIES} | {n: v for n, _, v in MAP_OTHERS}       # 2016~2025 합산, 백만 USD
TRADE_EXP = {                                                                         # 방산 연관 품목 수출(샘플)
    "폴란드": 3120, "미국": 2860, "사우디아라비아": 1540, "아랍에미리트": 1210, "호주": 980, "캐나다": 640,
    "인도": 520, "튀르키예": 410, "이집트": 380, "루마니아": 350, "노르웨이": 260, "필리핀": 240,
    "인도네시아": 220, "영국": 190, "에스토니아": 120, "태국": 95, "말레이시아": 70, "독일": 60,
    "베트남": 45, "브라질": 30, "멕시코": 18, "스페인": 12, "핀란드": 8, "일본": 6.5, "싱가포르": 4.2,
}
# 수출 쪽 국가별 값 — TRADE_EXP(샘플) 상위 7개국(지도 좌표 WORLD 가 있는 나라만). 수입 쪽 COUNTRIES 와 같은 모양
# (이름, 위도, 경도, 수출액, 색). 품목군별 수출 상대국 비중은 파일에 없어 만들지 않는다(→ HHI · 품목군별 비중은 수입만)
EXPORT_TOP = [(n, WORLD[n][1], WORLD[n][2], v, COUNTRIES[i][4]) for i, (n, v) in enumerate(   # 색은 수입 쪽 7색 그대로
    sorted(((n, v) for n, v in TRADE_EXP.items() if n in WORLD), key=lambda r: -r[1])[:7])]
GLOBE_PTS_EXP = [{"name": n, "lat": la, "lon": lo, "value": v, "color": c, "note": "수출(샘플)"}
                 for n, la, lo, v, c in EXPORT_TOP]
# 조회 페이지의 국가 목록 — 목업 순서(주요 수출국)를 앞에, 나머지는 교역 규모순
Q_COUNTRIES = ["미국", "폴란드", "사우디아라비아", "아랍에미리트", "호주", "캐나다"]
Q_COUNTRIES += sorted((n for n in set(TRADE_IMP) | set(TRADE_EXP) if n not in Q_COUNTRIES),
                      key=lambda n: -(TRADE_IMP.get(n, 0) + TRADE_EXP.get(n, 0)))

# 지역별 수입·수출 분포(시·도) — 코드는 통계청 2013 시·도 코드(southkorea-maps). 단위: 천 USD, 샘플
# 코드: [짧은 이름, 수입, 수출, 라벨 dx, dy(px)]
REGIONS = {
    "11": ["서울", 620, 260, 10, -6], "21": ["부산", 380, 430, 6, 4], "22": ["대구", 260, 170, 0, 0],
    "23": ["인천", 780, 190, -8, 12], "24": ["광주", 60, 60, 0, 0], "25": ["대전", 180, 720, 4, 4],
    "26": ["울산", 540, 380, 4, 0], "29": ["세종", 25, 12, 8, -6], "31": ["경기", 1850, 980, 12, 14],
    "32": ["강원", 45, 40, 0, 0], "33": ["충북", 150, 120, 4, -6], "34": ["충남", 240, 210, -10, 6],
    "35": ["전북", 70, 85, 0, 0], "36": ["전남", 40, 55, 0, 12], "37": ["경북", 310, 610, 8, 0],
    "38": ["경남", 1420, 2350, 0, 4], "39": ["제주", 6, 4, 0, 0],
}

# 공급국 × 품목군 구성비(마리메코) — 막대 폭은 COUNTRIES 수입액, 구성비(%)는 MIX_GROUPS 순서.
# 각 나라의 가장 큰 칸이 COUNTRIES 의 「1위 품목군」과 맞도록 잡았다.
MIX_GROUPS = [("항공기·엔진 부품", SERIES[0]), ("항행기기", SERIES[1]), ("레이더·통신", SERIES[2]),
              ("반도체·IC", SERIES[3]), ("광학기기", SERIES[4]), ("기타", ETC)]
MIX_SHARE = {
    "미국": [30, 14, 22, 18, 8, 8],
    "독일": [14, 24, 10, 8, 34, 10],
    "일본": [10, 8, 14, 42, 16, 10],
    "중국": [6, 8, 40, 22, 10, 14],
    "프랑스": [28, 34, 14, 6, 10, 8],
    "기타": [6, 18, 14, 46, 6, 10],      # 대만 + 싱가포르
}
_amt = {c[0]: c[3] for c in COUNTRIES}
SUPPLY_MIX = ([(n, _amt[n], MIX_SHARE[n]) for n in ("미국", "독일", "일본", "중국", "프랑스")]
              + [("기타", _amt["대만"] + _amt["싱가포르"], MIX_SHARE["기타"])])

# 분야별 국외조달 예산(히트맵) — 연도마다 합계가 BUDGET 「국외조달 예산」과 같다
BUDGET_FIELDS = ["항공기", "육상장비", "해상장비", "유도무기", "전자통신", "기타"]
_S0 = [30, 18, 17, 14, 13, 8]        # 2016 비중(%)
_S1 = [37, 11, 14, 20, 12, 6]        # 2026 비중(%)


def _field_split() -> list[list[int]]:
    rows = [[0] * len(YEARS) for _ in BUDGET_FIELDS]
    for j, total in enumerate(BUDGET["국외조달 예산(억 원)"]):
        t = j / (len(YEARS) - 1)
        w = [(a + (b - a) * t) * (1 + 0.07 * math.sin(j * 1.7 + i * 2.3))
             for i, (a, b) in enumerate(zip(_S0, _S1))]
        for i in range(len(w) - 1):
            rows[i][j] = round(total * w[i] / sum(w))
        rows[-1][j] = int(total) - sum(rows[i][j] for i in range(len(w) - 1))   # 반올림 차이는 「기타」가 받는다
    return rows


FIELD_BUDGET = _field_split()

# 입찰 공고 ↔ 결과 매칭(DATA CENTER 깔때기) — 단위: 행
BID_MATCH = [("입찰 공고 행", 10842), ("입찰 결과 행", 7405), ("공고키 존재 결과행", 7072), ("공통 고유키", 6872)]

# 분석 대상 선정(DATA CENTER 깔때기) — 발표 자료(2026-09-22) 「1,003개에서 13개까지」. 단위: HS 6단위 개수
# 채택 기준 = ① 세관 군용 전용 세분류 · ② 세분류 이름에 용도 명시. 전략물자 · 국산화 대응은 기준에서 뺐다
HS_SELECT = [("HS 6단위 전체", 1003, "84 · 85 · 88 · 90류"),
             ("두 기준 중 하나 이상 충족", 52, "군용 전용 세분류 · 용도 명시"),
             ("전자 계열 = 분석 대상", 13, "기계 · 전장 계열 39개 제외")]
# 군수품 FSC/FSG 분류 기준 깔때기(DATA CENTER) — DB QA D-04 최종 확정 값(DB_QA_최종결과). 단위: 행
#   13,615 = 국외 조달계획 원본(clean_dapa_overseas_plan_api)
#   13,236 = FSG 판별 가능 행(v_overseas_plan_api_fsc VIEW 가 nsn IS NOT NULL 기준으로 집계 — 화면이 VIEW 를 직접 읽지는 않음)
#   13,017 = 분석 모집단(13,236 에서 FSC 9999 219행 제외, clean 테이블 직접 조회)
#    2,267 = 전자·통신 FSG 58·59·60
# 반드시 2튜플 — funnel_card() 는 3번째 원소가 있으면(빈 문자열이어도) 설명 뒤에 「·」를 붙인다
# TODO: DB 연결 시 하드코딩을 걷어 내고 위 테이블 · VIEW 실제 쿼리 결과로 바꾼다
FSC_SELECT = [
    ("국외 조달계획 원본", 13615),
    ("FSG 판별 가능(예외 포함)", 13236),
    ("분석 모집단(FSC9999 제외)", 13017),
    ("전자·통신 FSG 58·59·60", 2267),
]
# 전처리 단계별 건수(DATA CENTER) — 기획안 2절. (자료, 원본 행, 정제 행, 제외 행, 제외 사유). 원본 = 정제 + 제외 를 검산한다
PREP_COUNTS = [("관세청 품목별 국가별 수출입", 294420, 294174, 246, "국가 합계 행 분리(원본 합계와 대조 · 불일치 0)"),
               ("방위사업청 국산화개발품목", 33965, 25025, 8940, "완전 중복 제거"),
               ("방위사업청 국외 조달계획", 13615, 13615, 0, "제외 없음 · 적용장비명 결측 2,018행은 채우지 않고 「미상」 표시")]
# 자료별 기준일(DATA CENTER) — 기획안 1-2 · 앱 수집 기록. (자료, 기간 · 판, 기준)
AS_OF = [("관세청 수출입(국가 · 시군구)", "2016.01 ~ 2026.08", "수집 2026-09-14 · 2026년은 1~8월"),
         ("방위사업청 국외 조달계획", "2016 ~ 2026", "OpenAPI 스냅샷"),
         ("방위사업청 입찰공고 · 입찰결과", "스냅샷", "공통 고유키로 결합(왼쪽)"),
         ("방위사업청 국산화개발품목", "시점 미표기", "파일데이터 · 원본에 기준일 없음"),
         ("HS부호 · HSK 연계표", "2026년판", "관세청 · 무역안보관리원"),
         ("군급분류집(FSG/FSC)", "2025년판", "방위사업청 파일데이터"),
         ("열린재정 세부사업 예산", "2016 ~ 2027", "2027은 정부안"),
         ("분석 대상 13개 확정", "2026-09-21", "진입 = R1 또는 R2")]

# 국외조달 절차(정책·산업 배경) — 단계, 아이콘, 설명, 건수, 원 색. 건수는 실측(clean 테이블 행 수):
# 계획 clean_dapa_overseas_plan 3,023 · 입찰 clean_dapa_overseas_bid_result 2,494 · 계약 clean_dapa_overseas_contract 6,333
PROC_STEPS = [
    ("계획", "📋", "조달 필요 확인<br>구매계획 수립", 3023, "#2b6ef6"),
    ("입찰", "⚖️", "국외 공고 및 입찰<br>업체 평가 · 선정", 2494, "#2b6ef6"),
    ("계약", "🤝", "계약 체결<br>납품 및 이행 관리", 6333, "#0f9f78"),
]

# 부품별 공급망 현황(홈 표) · 품목군별 공급 집중도(수입 집중도 탭) — 1위 공급국이 서로 다른 5개 품목군
FOCUS_HS = ["880730", "854231", "852910", "901410", "852691"]
_FOCUS_TREND = {"880730": 0.22, "854231": 0.15, "852910": 0.10, "901410": -0.08, "852691": -0.05}  # 24개월 기울기(샘플)


def _monthly(g: float, k: int) -> list[float]:
    """최근 24개월 월별 수입액 지수(샘플). 앞 12개월 = 전년, 뒤 12개월 = 최근 12개월."""
    return [round(100 * (1 + g * m / 23) * (1 + 0.07 * math.sin(m * 1.1 + k * 1.9) + 0.03 * math.sin(m * 2.7 + k)), 1)
            for m in range(24)]


def _country_shares(top: str, s1: float, hhi: float, n: int) -> list[tuple[str, float]]:
    """1위 점유율(s1)과 HHI 가 ITEMS 값과 맞도록 나머지 n-1 개국 몫을 등비로 나눈다(샘플).
    등비 r 이 작을수록 한 나라에 몰려 제곱합이 커지므로, 제곱합이 HHI 에 맞을 때까지 r 을 이분 탐색한다."""
    others = [c for c in [c[0] for c in COUNTRIES] + [m[0] for m in MAP_OTHERS] if c != top][:n - 1]
    rem, target = 100 - s1, hhi - s1 ** 2

    def split(r: float) -> list[float]:
        w = [r ** k for k in range(n - 1)]
        return [rem * x / sum(w) for x in w]

    lo, hi = 1e-4, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if sum(s * s for s in split(mid)) > target:
            lo = mid
        else:
            hi = mid
    return [(top, s1)] + list(zip(others, split((lo + hi) / 2)))


_items = {r[0]: r for r in ITEMS}
FOCUS = []
for _k, _hs in enumerate(FOCUS_HS):
    _, _name, _top, _s1, _hhi, _n = _items[_hs]
    _m = _monthly(_FOCUS_TREND[_hs], _k)
    FOCUS.append({"hs": _hs, "name": _name, "top": _top, "s1": _s1, "hhi": _hhi, "n": _n, "m": _m[12:],
                  "yoy": sum(_m[12:]) / sum(_m[:12]) * 100 - 100,
                  "shares": _country_shares(_top, _s1, _hhi, _n)})

# ── 실측값(샘플 아님) — defense_dashboard(AWS RDS) clean 테이블을 팀 문서에 기록한 값 ──────────────
# 출처: docs/report/null-profile-2026-09-19.md, evidence-reliability-review-2026-09-17.md,
#       reference/contract-class5-rules-alt-2026-09-17.md, csv-capability-map-2026-09-14.md,
#       reference/data-cleaning-rules.md, db/table-guide.md, data-usage-decision-2026-09-18.md
# 국내 계약 방법(clean_dapa_contract, 테스트 업체 6행 제외 전 43,111행 기준)
DOM_METHOD = [("수의계약", 30255, SERIES[2]), ("일반경쟁", 6542, SERIES[0]), ("제한경쟁", 5184, SERIES[1]),
              ("협상", 666, SERIES[3]), ("2단계", 435, SERIES[4]), ("지명경쟁", 29, SERIES[5])]
# 수의계약 사유 상위(행). 나머지는 기타로 묶는다
PRIVATE_REASON = [("추정가격 2천만원 이하", 18760), ("소기업 1억 이하", 4332), ("우수조달물품", 1101), ("국가기관 간", 1100)]
# 국내 경쟁입찰 결과(clean_dapa_bid_result, 결과 행)
BID_RESULT = [("개찰완료(낙찰)", 5275, SERIES[0]), ("유찰", 1746, DOWN), ("순위확정", 382, SERIES[1])]

# ── 운영 DB 값(배포 앱 defense-trade.streamlit.app 이 RDS 에서 읽어 그린 값, 2026-09-21 확인) ──
# 방산업체 분야별 평균가동률(clean_kosis_utilization), 2016~2024, %
UTIL_YEARS = list(range(2016, 2025))
UTIL = {
    "통신전자": [73.4, 70.8, 75.2, 72.3, 73.6, 73.4, 71.7, 89.0, 85.0],
    "평균":     [68.6, 69.2, 71.2, 72.0, 72.9, 81.4, 75.6, 77.0, 80.3],
    "기동":     [68.6, 63.5, 70.1, 71.2, 67.6, 75.0, 72.4, 73.0, 80.2],
    "탄약":     [75.4, 72.3, 75.1, 70.5, 65.3, 81.0, 78.9, 73.2, 77.9],
    "함정":     [65.3, 68.1, 81.6, 79.1, 85.9, 86.8, 78.9, 79.3, 82.0],
    "항공유도": [65.3, 69.2, 66.4, 66.4, 69.5, 72.9, 76.7, 76.4, 80.4],
    "화력":     [69.4, 70.9, 66.3, 77.4, 80.5, 82.0, 72.3, 68.3, 69.7],
    "화생방":   [60.3, 61.4, 70.6, 79.5, 67.8, 77.1, 72.6, 74.1, 66.3],
    "기타":     [38.6, 36.3, 42.5, 67.8, 79.2, 40.8, 51.9, 59.1, 87.8],
}
# 열린재정 세부사업 예산(clean_openfiscal_program_budget), 억 원. 2027 = 정부안
RND_BUDGET = {
    "부품국산화": ([2021, 2022, 2023, 2024, 2025, 2026, 2027], [886.4, 1691.1, 1845.1, 1232.7, 1278.8, 1336.0, 1283.2]),
    "공급망":     ([2025, 2026, 2027], [7.5, 52.5, 55.5]),
    "국방반도체": ([2027], [565.1]),
}
# 국외조달 계획 연도 × 집행유형 건수(clean_dapa_overseas_plan → v_overseas_plan_yearly), 합계 3,023
OV_PLAN_YEARS = list(range(2017, 2026))
OV_PLAN_TYPE = {
    "장비":       [74, 149, 146, 105, 99, 88, 61, 58, 67],
    "(확정)부품": [121, 129, 93, 59, 44, 44, 52, 58, 71],
    "장비정비":   [79, 72, 81, 60, 55, 65, 53, 43, 56],
    "한도액부품": [84, 60, 66, 48, 42, 59, 39, 40, 49],
    "물자":       [24, 26, 56, 38, 9, 7, 6, 6, 13],
    "기타":       [23, 33, 27, 31, 33, 32, 33, 27, 30],
}
# 분야별 방산업체 지정 수(방위사업청 방산업체 지정현황), 총 84개사
DEF_COMPANY = [("항공유도", 16), ("통신전자", 15), ("기동", 12), ("함정", 9), ("탄약", 9),
               ("화력", 8), ("기타", 8), ("화생방", 3), ("항공", 1)]
# 분석 대상 13개(진입 = R1 군용전용 또는 R2 항공·항행, 2026-09-21 확정). 나머지 11개는 배경 자료
TARGET_HS = {"841191", "852610", "852691", "852910", "852990", "854231", "854233", "854239",
             "880730", "901410", "901420", "901480", "901490"}

# HS6 24개 선정 근거(data/reference/hs_whitelist.csv 의 evidence 열 그대로)
BASIS_TAGS = [("HSK-군용", "R1 군용전용 — 제9301·9306호 전용 세분류(진입 근거)"),
              ("HSK-항공/항행", "R2 항공·항행 — 항공기용·항행·레이더·무인기 세분류(진입 근거)"),
              ("전략물자-DU", "R3 이중용도 전략물자 3·5·6·7부 — 참고일 뿐 진입 근거 아님"),
              ("B2-FSC", "R4 국산화개발품목 FSC 대응 — 공식 연계표가 없어 규칙에서 뺌"),
              ("A6", "국방반도체 연구 인용(참고)"), ("팀판단", "기획 단계 팀 판단(규칙 미해당)")]
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

items_df = pd.DataFrame(ITEMS, columns=["HS6", "품목군", "1위 공급국", "1위 점유율(%)", "HHI", "수입국 수"])
# 품목군 × 연도 HHI(샘플) — 연도별 실측이 없어 ITEMS 의 HHI(2025)에서 품목군마다 완만한 기울기 · 잔물결을 준 값. 2025 열은 ITEMS 와 같다
HHI_YEARS = YEARS[:-1]                                    # 완결연도 2016~2025
HHI_YEARLY = {name: [round(hhi * (1 + (i % 3 - 1) * 0.02 * (y - 2025) + (0.03 * math.sin(i + y) if y != 2025 else 0)))
                     for y in HHI_YEARS]
              for i, (_, name, _, _, hhi, _) in enumerate(ITEMS)}


# ════════════════════════════════════════════════════════════════════════════
# 5. 화면
# ════════════════════════════════════════════════════════════════════════════
def hbar(rows: list[tuple[str, int, str]], height: int = 300, unit: str = "") -> go.Figure:
    rows = list(reversed(rows))
    fig = go.Figure(go.Bar(x=[r[1] for r in rows], y=[r[0] for r in rows], orientation="h",
                           marker=dict(color=[r[2] for r in rows], line=dict(color="#fff", width=1)),
                           text=[f"{r[1]:,}" for r in rows], textposition="outside",
                           textfont=dict(size=11, color=TEXT), cliponaxis=False,
                           hovertemplate="%{y}<br>%{x:,}" + f" {unit}<extra></extra>"))
    label_w = max(len(str(r[0])) for r in rows) * 11 + 14      # 한글 한 자 ≈ 11px — 왼쪽 라벨이 잘리지 않게
    fig.update_layout(height=height, showlegend=False, margin=dict(l=min(label_w, 230), r=48, t=10, b=8))
    return fig


def mirror_bar(labels: list[str], left: list[int], right: list[int], left_name: str, right_name: str,
               height: int = 360) -> go.Figure:
    """대칭 막대 — 같은 군급 축에 왼쪽(left)과 오른쪽(right)을 나란히 놓는다. 왼쪽 값은 음수로 그리고 눈금 · 라벨만 양수로 보인다."""
    labels, left, right = labels[::-1], left[::-1], right[::-1]    # 첫 군급이 맨 위에 오도록
    top = max(left + right) * 1.25
    fig = go.Figure([
        go.Bar(y=labels, x=[-v for v in left], orientation="h", name=left_name, marker_color=SERIES[3],
               text=[f"{v:,}" for v in left], textposition="outside", cliponaxis=False, customdata=left,
               hovertemplate="%{y}<br>" + left_name + " %{customdata:,}건<extra></extra>"),
        go.Bar(y=labels, x=right, orientation="h", name=right_name, marker_color=SERIES[0],
               text=[f"{v:,}" for v in right], textposition="outside", cliponaxis=False,
               hovertemplate="%{y}<br>" + right_name + " %{x:,}건<extra></extra>"),
    ])
    ticks = [-top * 0.8, -top * 0.4, 0, top * 0.4, top * 0.8]
    fig.update_layout(barmode="overlay", bargap=0.35, height=height, margin=dict(l=8, r=8, t=36, b=8),
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=1.08))
    fig.update_xaxes(range=[-top, top], tickvals=ticks, ticktext=[f"{abs(t):,.0f}" for t in ticks])
    fig.add_vline(x=0, line_color=LINE, line_width=1)
    return fig


def mekko(height: int = 380) -> go.Figure:
    """막대 폭 = 국가 수입액, 칸 높이 = 그 나라 안에서의 품목군 비중(합 100%)."""
    total = sum(v for _, v, _ in SUPPLY_MIX)
    mids, widths, x0 = [], [], 0.0
    for _, v, _ in SUPPLY_MIX:
        w = v / total * 100
        mids.append(x0 + w / 2); widths.append(w); x0 += w
    fig = go.Figure()
    for gi in reversed(range(len(MIX_GROUPS))):          # 첫 품목군이 맨 위에 오도록 거꾸로 쌓는다
        g, color = MIX_GROUPS[gi]
        ys = [s[gi] for _, _, s in SUPPLY_MIX]
        fig.add_trace(go.Bar(
            x=mids, y=ys, width=widths, name=g,
            marker=dict(color=color, line=dict(color="#fff", width=1.5)),
            text=[f"{y}%" for y in ys], textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color=TEXT if color == ETC else "#fff"),
            customdata=[[nm, v] for nm, v, _ in SUPPLY_MIX],
            hovertemplate="%{customdata[0]} · " + g + "<br>구성비 %{y}%<br>국가 수입액 %{customdata[1]:,} 백만 USD<extra></extra>"))
    fig.update_layout(barmode="stack", bargap=0, height=height,
                      legend=dict(traceorder="reversed", orientation="h", y=-0.04, yanchor="top", font=dict(size=11)))
    fig.update_xaxes(tickvals=mids, ticktext=[nm for nm, _, _ in SUPPLY_MIX], side="top", range=[0, 100],
                     showgrid=False, tickfont=dict(size=12, color=TEXT))
    fig.update_yaxes(range=[0, 100], ticksuffix="%", showgrid=False)
    return fig


def field_heatmap(height: int = 330) -> go.Figure:
    """색 = 분야 안에서의 상대 크기(그 분야 최저 0 ~ 최고 1). 금액이 큰 항공기가 색을 독차지하지 않게 한다.
    실제 금액(억 원)은 마우스를 올리면 보인다."""
    rel = [[(v - min(row)) / ((max(row) - min(row)) or 1) for v in row] for row in FIELD_BUDGET]
    fig = go.Figure(go.Heatmap(
        z=rel, x=YEARS, y=BUDGET_FIELDS, xgap=2, ygap=2, zmin=0, zmax=1, customdata=FIELD_BUDGET,
        colorscale=[[0, "#2f6fe4"], [.35, "#9cc8f8"], [.62, "#fbe38a"], [1, "#e5483b"]],
        colorbar=dict(thickness=10, len=.9, outlinewidth=0, tickvals=[0, 1],
                      ticktext=["낮음", "높음"], tickfont=dict(color=MUTED, size=11)),
        hovertemplate="%{y} · %{x}년<br>%{customdata:,}억 원<extra></extra>"))
    fig.update_layout(height=height)
    fig.update_xaxes(dtick=1, showgrid=False, tickfont=dict(size=10.5))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


# ── Main(첫 화면) — 국방과학연구소 첫 화면처럼 큰 사진 + 글씨 ──────────────────────
# 사진은 Unsplash 무료 사진(상업적 사용 가능 · 출처 표기 선택)을 주소로 불러온다 — 인터넷이 없으면 사진 자리는 파란 바탕만 보인다
def _ph(pid: str, w: int = 1600) -> str:
    return f"https://images.unsplash.com/photo-{pid}?auto=format&fit=crop&w={w}&q=70"


MAIN_SLIDES = [_ph("1551796880-ddd03f861ae7", 2000),    # 푸른 하늘의 전투기
               _ph("1685178362030-9b574eb9ae7c", 2000),  # 항공모함
               _ph("1610457642191-05328cdf34ff", 2000)]  # 밤하늘 레이더
MAIN_CARDS = [  # (url, 소분류, 사진, 분류, 제목, 설명)
    ("parts", "summary", _ph("1592659762303-90081d34b277", 900), "PARTS", "전자부품 현황",
     "분석 대상 13개 품목군을 어느 나라에서 얼마나 들여오고 내보내는지, 공급국 집중도와 함께 봅니다."),
    ("fsc", "code", _ph("1578575437130-527eed3abbec", 900), "CLASSIFICATION", "군급 분류와 조달",
     "군수품 분류(군 FSG · 군급 FSC)로 전자 군급의 국외 조달계획과 국내 계약 · 입찰을 봅니다."),
    ("local", "done", _ph("1587293852726-70cdb56c2866", 900), "LOCALIZATION", "국산화 현황",   # 조달 물자 창고
     "군(FSG) 58 · 59 · 60에 속한 전자 군급 부품 중 국산화개발을 마친 부품을 군급별로 봅니다."),
    ("background", "policy", _ph("1676090438227-141cac59c405", 900), "BACKGROUND", "배경과 자료",
     "정책 흐름과 예산, 국내 생산 기반, 그리고 이 숫자들이 어디서 왔는지 봅니다."),
]
# 첫 화면 「데이터 출처」 목록 — (기관, 데이터, 수록 기간 · 기준, 원본 페이지). 기간은 AS_OF(④ 자료별 기준일) · 참고 자료 md 와 같게.
# 누르면 새 탭에서 원본 페이지로 — 공공데이터포털 주소는 docs/data-sources.md 의 데이터셋 번호(2026-09-30 접속 확인).
# KOSIS 한 줄 = 두 표 모두 KOSIS 수록 통계라 기관은 하나로 둔다(가동률 = 방산업체 경영분석 orgId 409, 생산지수 = 통계청 orgId 101).
#   가동률 표 번호(tblId)는 팀 기록에 없어(db/meta_dataset.csv 「tblId 미확인」) 링크는 확인된 생산지수 표 DT_1F02001 로.
# 열린재정 = 세부사업 예산편성현황(총액) UOPKOSDA01(팀 원본 파일 코드와 같음 · 2026-09-30 검색으로 찾은 임시 주소)
MAIN_SOURCES = [("관세청", "품목별 국가별 수출입실적", "2016.01 ~ 2026.08 · 2026년 부분연도",
                 "https://www.data.go.kr/data/15100475/openapi.do"),
                ("방위사업청", "국외 조달계획", "요구연도 2016 ~ 2026",
                 "https://www.data.go.kr/data/15158418/openapi.do"),
                ("방위사업청", "국산화개발품목", "시점 미상 · 원본에 기준일 없음",
                 "https://www.data.go.kr/data/15119899/fileData.do"),
                ("방위사업청", "군급분류집(FSG/FSC)", "2025-12-31 기준",
                 "https://www.data.go.kr/data/15119907/fileData.do"),
                ("KOSIS", "방산 가동률 · 광공업생산지수", "가동률 2016 ~ 2024 · 생산지수 2016.01 ~ 2026.07",
                 "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1F02001"),
                ("열린재정", "세부사업 예산", "2016 ~ 2027 · 2027년 정부안",
                 "https://www.openfiscaldata.go.kr/op/ko/sd/UOPKOSDA01")]
MAIN_STATS = [("13", "개", "분석 대상 품목군"), ("478.2", "억 달러", "2025 수입액"),
              ("5", "개", "특정국 50% 초과 품목군"), ("2,717", "행", "국산화개발 전자 계열")]

MAIN_CSS = """<style>
/* ── 큰 사진 — 6초마다 다음 장으로, 보이는 동안 천천히 커진다. 아래 ‹ › 단추로 바로 이전 · 다음 장(MV_JS) ─────── */
.mv{position:relative;height:620px;overflow:hidden;background:#002a73}
.mv-sl{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transform:scale(1.02);
  transition:opacity .9s ease,transform 7s linear;will-change:opacity,transform}
.mv-sl.on{opacity:1;transform:scale(1.12)}
.mv::after{content:"";position:absolute;inset:0;
  background:linear-gradient(180deg,rgba(0,22,70,.62) 0%,rgba(0,40,120,.30) 45%,rgba(0,18,60,.78) 100%)}
.mv-txt{position:absolute;left:0;right:0;top:128px;z-index:2;text-align:center;color:#fff;padding:0 24px}
.mv-txt small{display:inline-block;font-size:13px;font-weight:800;letter-spacing:4px;color:#bcd6ff;
  padding:6px 16px;border:1px solid rgba(188,214,255,.5);border-radius:30px;margin-bottom:22px}
.mv-txt h1{margin:0;font-size:58px;font-weight:900;letter-spacing:-2px;line-height:1.15;color:#fff;
  text-shadow:0 4px 24px rgba(0,10,40,.45)}
.mv-txt .en{margin:16px 0 0;font-size:30px;font-weight:800;letter-spacing:-.5px;color:#7cc4ff}
.mv-txt p{margin:16px 0 0;font-size:16px;line-height:1.7;color:#e3ecfb}
.mv-bar{position:absolute;left:50%;bottom:34px;transform:translateX(-50%);z-index:2;display:flex;align-items:center;gap:14px;
  color:#fff;font-size:13px;font-weight:700;letter-spacing:1px}
.mv-bar .tr{width:180px;height:2px;background:rgba(255,255,255,.3);position:relative;overflow:hidden}
.mv-bar .tr::after{content:"";position:absolute;left:0;top:0;height:100%;width:100%;background:#fff;transform-origin:left;
  transform:scaleX(0)}
.mv-bar .tr.run::after{animation:mvProg 6s linear forwards}   /* 장이 바뀔 때마다 처음부터 다시 찬다 */
@keyframes mvProg{from{transform:scaleX(0)}to{transform:scaleX(1)}}
/* 이전 · 다음 단추(예전 01 · 03 자리) */
.mv-arr{width:28px;height:28px;padding:0;border-radius:50%;border:1.5px solid rgba(255,255,255,.75);background:rgba(0,20,60,.15);
  color:#fff;display:grid;place-items:center;cursor:pointer;transition:background .15s,border-color .15s}
.mv-arr:hover{background:rgba(255,255,255,.22);border-color:#fff}
.mv-arr::before{content:"";width:7px;height:7px;border-top:1.8px solid currentColor;border-left:1.8px solid currentColor}
.mv-arr.prev::before{transform:translateX(1.5px) rotate(-45deg)}   /* ‹ */
.mv-arr.next::before{transform:translateX(-1.5px) rotate(135deg)}  /* › */
.st-key-mvjs,[data-testid="stLayoutWrapper"]:has(> .st-key-mvjs){display:none!important}
/* 사진 위 단추 두 개 — 글씨 아래에 올린다 */
.st-key-mv_cta{margin:-236px 0 0!important;height:236px;position:relative;z-index:3;justify-content:center;gap:14px!important;
  pointer-events:none}
.st-key-mv_cta [data-testid="stPageLink"]{pointer-events:auto}
.st-key-mv_cta [data-testid="stPageLink"] a{height:52px;padding:0 30px;border:1.5px solid #fff;border-radius:0;background:transparent;
  transition:background .2s,color .2s}
.st-key-mv_cta [data-testid="stPageLink"] a p{font-size:16px!important;font-weight:700;color:#fff!important;letter-spacing:-.2px}
.st-key-mv_cta [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{color:#fff}
.st-key-mv_cta [data-testid="stPageLink"] a:hover{background:#fff}
.st-key-mv_cta [data-testid="stPageLink"] a:hover p,.st-key-mv_cta [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"]{color:#003899!important}
.st-key-mv_cta > div:first-child [data-testid="stPageLink"] a{background:#1d4ed8;border-color:#1d4ed8}

/* ── 소개 줄 — 왼쪽 글 · 오른쪽 둥근 아이콘 바로가기(국방과학연구소 첫 화면 아래 줄) ─────────── */
.st-key-mi{padding:70px __PAD__ 64px;gap:50px!important;align-items:center!important;flex-wrap:nowrap!important;background:#fff}
.mi-txt{max-width:460px}
.mi-txt .k{display:flex;align-items:center;gap:12px;font-size:14px;font-weight:800;color:#0b1f4d;letter-spacing:-.2px}
.mi-txt .k::before{content:"";width:34px;height:3px;background:#0b1f4d}
.mi-txt h2{margin:18px 0 0;font-size:34px;font-weight:900;letter-spacing:-1.2px;line-height:1.3;color:#0b1f4d}
.mi-txt h2 em{font-style:normal;color:#1d4ed8}
.mi-txt p{margin:16px 0 0;font-size:14.5px;line-height:1.8;color:#55637d;word-break:keep-all}
.mi-txt p b{color:#0b1f4d;font-weight:800}
.mi-ref{margin-right:1px;font-size:11px;font-weight:800;color:#1d4ed8}
.mi-hit{cursor:help}
.mi-src{transition:color .15s,font-size .15s}
.mi-txt:has(.mi-hit:hover) .mi-src{color:#1d4ed8;font-size:13.5px}
.mi-txt p + p{margin-top:10px}
.mi-src{display:block;margin-top:12px;font-size:12px;color:#8a97ad;line-height:1.6}
.st-key-mi_links [data-testid="stPageLink"] a p{white-space:normal!important;word-break:keep-all;line-height:1.35!important}
.st-key-mi_links{gap:0!important;flex-wrap:nowrap!important}
.st-key-mi_links > div{flex:1 1 0!important;min-width:0;border-left:1px solid #e3e8f0}
.st-key-mi_links [data-testid="stPageLink"] a{flex-direction:column;gap:18px!important;padding:14px 8px;background:transparent!important;width:100%}
.st-key-mi_links [data-testid="stPageLink"] a > span:first-child{width:auto!important;height:auto!important;justify-content:center!important}
.st-key-mi_links [data-testid="stPageLink"] a{height:auto!important}
.st-key-mi > div:last-child{flex:1 1 0!important;min-width:0}
.st-key-mi > div:first-child{flex:0 0 480px!important;width:480px!important;max-width:480px}
.st-key-mi_links [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{font-size:44px!important;width:96px;height:96px;margin:0!important;
  border:2px solid #1b2540;border-radius:50%;display:grid;place-items:center;color:#1b2540;transition:all .25s}
.st-key-mi_links [data-testid="stPageLink"] a p{font-size:16px!important;font-weight:800;color:#1b2540!important;letter-spacing:-.4px;text-align:center}
.st-key-mi_links [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"]{background:#1d4ed8;border-color:#1d4ed8;color:#fff;
  transform:translateY(-6px);box-shadow:0 14px 26px rgba(29,78,216,.3)}
.st-key-mi_links [data-testid="stPageLink"] a:hover p{color:#1d4ed8!important}

/* ── 주요 분석 카드 — 사진 + 분류 · 제목 · 설명 · 자세히 보기 ───────────────── */
.mc-head{padding:64px __PAD__ 26px;background:#f3f6fb;display:flex;align-items:flex-end;justify-content:space-between}
.mc-head h2{margin:0;font-size:32px;font-weight:900;letter-spacing:-1px;color:#0b1f4d}
.mc-head h2 small{display:block;font-size:13px;font-weight:800;letter-spacing:3px;color:#1d4ed8;margin-bottom:8px}
.mc-head span{font-size:13.5px;color:#6b7a99}
.st-key-mcards{padding:0 __PAD__ 72px;background:#f3f6fb;gap:22px!important;flex-wrap:nowrap!important;align-items:stretch!important}
.st-key-mcards > div{flex:1 1 0!important;min-width:0}
div[class*="st-key-mc_"]{height:100%;background:#fff;border:1px solid #e1e8f3;gap:0!important;overflow:hidden;
  transition:transform .25s,box-shadow .25s}
div[class*="st-key-mc_"]:hover{transform:translateY(-6px);box-shadow:0 18px 36px rgba(0,40,120,.14)}
.mc-img{height:210px;overflow:hidden;position:relative}
.mc-img div{position:absolute;inset:0;background-size:cover;background-position:center;transition:transform .5s}
div[class*="st-key-mc_"]:hover .mc-img div{transform:scale(1.08)}
.mc-img b{position:absolute;left:16px;top:16px;z-index:1;font-size:11px;font-weight:800;letter-spacing:2px;color:#fff;
  background:#1d4ed8;padding:5px 10px}
.mc-body{padding:22px 22px 8px}
.mc-body h3{margin:0;font-size:20px;font-weight:800;letter-spacing:-.6px;color:#0b1f4d}
.mc-body p{margin:10px 0 0;font-size:13.5px;line-height:1.7;color:#5b6b88;min-height:69px}
div[class*="st-key-mc_"] [data-testid="stPageLink"]{padding:0 22px 22px}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a{padding:0;background:transparent!important;flex-direction:row-reverse;justify-content:flex-end;gap:6px!important}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a p{font-size:14px!important;font-weight:800;color:#1d4ed8!important}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{color:#1d4ed8;font-size:18px!important;margin:0!important;
  transition:transform .2s}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"]{transform:translateX(4px)}
/* 카드 어디를 눌러도(사진 · 제목 · 설명) 「자세히 보기」 링크로 간다 — 링크의 투명 ::before 를 카드 전체에 덮는다.
   카드와 링크 사이 칸들은 position 을 풀어 ::before 가 카드(position:relative) 기준으로 펼쳐지게 한다 */
div[class*="st-key-mc_"]{position:relative;cursor:pointer}
div[class*="st-key-mc_"] div:has([data-testid="stPageLink"] a),
div[class*="st-key-mc_"] [data-testid="stPageLink"] div:has(a){position:static!important}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a{position:static!important}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a::before{content:"";position:absolute;inset:0;z-index:2}
div[class*="st-key-mc_"]:hover [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{transform:translateX(4px)}

/* ── 숫자 띠 — 사진 위 파랑 ───────────────────────────────────────── */
.mst{position:relative;padding:62px __PAD__;background-size:cover;background-position:center;background-attachment:fixed}
.mst::before{content:"";position:absolute;inset:0;background:linear-gradient(100deg,rgba(0,35,107,.94),rgba(29,78,216,.86))}
.mst-in{position:relative;display:grid;grid-template-columns:260px repeat(4,1fr);align-items:center}
.mst-h b{display:block;font-size:26px;font-weight:900;color:#fff;letter-spacing:-.8px;line-height:1.3}
.mst-h span{display:block;margin-top:8px;font-size:12.5px;color:#b9cdf2;line-height:1.6}
.mst-i{text-align:center;border-left:1px solid rgba(255,255,255,.18);padding:6px 10px}
.mst-i .v{font-size:46px;font-weight:900;color:#fff;letter-spacing:-1.5px;line-height:1.1}
.mst-i .v small{font-size:16px;font-weight:700;color:#bcd6ff;margin-left:4px;letter-spacing:0}
.mst-i .l{margin-top:8px;font-size:14px;font-weight:600;color:#d6e3fa}

/* ── 아래 줄 — 데이터 갱신 목록 · 이용 안내 ─────────────────────────────── */
.st-key-mb{padding:64px __PAD__ 76px;gap:40px!important;flex-wrap:nowrap!important;align-items:stretch!important;background:#fff}
.st-key-mb > div:first-child{flex:1.7 1 0!important;min-width:0}
.st-key-mb > div:last-child{flex:1 1 0!important;min-width:0;position:relative;top:49px}   /* GUIDE 상자 윗변 = 왼쪽 「데이터 출처」 제목 밑 남색 선 윗변(제목 줄 높이 − 선 2px). 크기는 그대로 두고 자리만 내린다 */
.mb-h{display:flex;justify-content:space-between;align-items:flex-end;padding-bottom:14px;border-bottom:2px solid #0b1f4d}
.mb-h h3{margin:0;font-size:22px;font-weight:900;letter-spacing:-.7px;color:#0b1f4d}
.mb-h span{font-size:12.5px;color:#6b7a99}
.mb-list{list-style:none;margin:0!important;padding:0!important}
.mb-list li{border-bottom:1px solid #e6ebf3;font-size:14.5px}
.mb-list li a{display:flex;align-items:center;gap:16px;padding:15px 4px;color:inherit;text-decoration:none;transition:background .15s}   /* 줄 전체가 원본 페이지 링크 */
.mb-list li a:hover{background:#f5f8fd}
.mb-list li a:hover span{color:#1d4ed8;text-decoration:underline;text-underline-offset:3px}
.mb-list li .ms{flex:0 0 auto;font-family:'Material Symbols Rounded';font-style:normal;font-size:16px;line-height:1;color:#a3afc4}
.mb-list li a:hover .ms{color:#1d4ed8}
.mb-list li b{flex:0 0 72px;box-sizing:border-box;text-align:center;font-size:11px;font-weight:800;color:#1d4ed8;background:#eaf1ff;padding:4px 8px;letter-spacing:.5px}   /* 기관 이름 길이가 달라도 자료 이름이 한 줄로 맞게 폭 고정 */
.mb-list li span{flex:1;min-width:0;color:#1b2540;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mb-list li em{flex:0 0 auto;font-style:normal;font-size:13px;color:#7a879e}
.mb-box{height:100%;padding:30px 30px 26px;color:#fff;background:linear-gradient(140deg,#002a73,#1d4ed8);position:relative;overflow:hidden}
.mb-box::after{content:"shield";font-family:'Material Symbols Rounded';font-size:190px;line-height:1;position:absolute;right:-26px;bottom:-34px;
  color:rgba(255,255,255,.08);font-feature-settings:'liga'}
.mb-box small{font-size:12px;font-weight:800;letter-spacing:3px;color:#9fc2ff}
.mb-box h3{margin:10px 0 0;font-size:24px;font-weight:900;letter-spacing:-.8px;line-height:1.35;color:#fff}
.mb-box ul{margin:16px 0 0!important;padding:0!important;list-style:none}
.mb-box li{font-size:13px;line-height:1.75;color:#a5d8ff;padding-left:14px;position:relative}   /* 파스텔 하늘색 */
.mb-box li::before{content:"";position:absolute;left:0;top:10px;width:5px;height:5px;background:#7cc4ff}
.st-key-mb_go{gap:8px!important;margin-top:-86px!important;padding:0 30px;position:relative;z-index:2}
.st-key-mb_go [data-testid="stPageLink"] a{background:#fff;border-radius:0;padding:10px 16px}
.st-key-mb_go [data-testid="stPageLink"] a p{font-size:13.5px!important;font-weight:800;color:#003899!important}
.st-key-mb_go [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{color:#003899}
.st-key-mb_go [data-testid="stPageLink"] a:hover{background:#eaf1ff}
.st-key-landing,.st-key-zone_main{gap:0!important;margin:0!important}
.st-key-main_css,[data-testid="stLayoutWrapper"]:has(> .st-key-main_css){display:none!important}   /* CSS 담는 칸 — 자리 차지 없음 */
</style>"""


# 큰 사진 넘기기 — st.html 은 스크립트를 돌리지 않아, 보이지 않는 components.html 안에서 바깥 화면(window.parent)을 다룬다.
# 6초마다 다음 장, ‹ › 를 누르면 바로 이전 · 다음 장으로 가고 6초를 처음부터 다시 센다. 보던 장 번호는 다시 그려져도 이어진다
MV_JS = r"""<script>
(function () {
  const P = window.parent, doc = P.document, DUR = 6000;
  if (P.__mvTimer) P.clearInterval(P.__mvTimer);
  if (P.__mvClick) doc.removeEventListener('click', P.__mvClick, true);
  function show(k) {
    const mv = doc.querySelector('.mv'); if (!mv) return false;
    const sl = mv.querySelectorAll('.mv-sl'); if (!sl.length) return false;
    const i = ((k % sl.length) + sl.length) % sl.length;
    P.__mvIdx = i;
    sl.forEach((s, j) => s.classList.toggle('on', j === i));
    const tr = mv.querySelector('.mv-bar .tr');
    if (tr) { tr.classList.remove('run'); void tr.offsetWidth; tr.classList.add('run'); }
    return true;
  }
  function restart() {
    if (P.__mvTimer) P.clearInterval(P.__mvTimer);
    P.__mvTimer = P.setInterval(() => {
      if (!doc.querySelector('.mv')) { P.clearInterval(P.__mvTimer); return; }   // 첫 화면을 떠나면 멈춘다
      show((P.__mvIdx || 0) + 1);
    }, DUR);
  }
  P.__mvClick = e => {
    const b = e.target.closest && e.target.closest('.mv-arr');
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    show((P.__mvIdx || 0) + (b.classList.contains('prev') ? -1 : 1));
    restart();
  };
  doc.addEventListener('click', P.__mvClick, true);
  let n = 0;
  const t = P.setInterval(() => { n++; if (show(P.__mvIdx || 0) || n > 50) { P.clearInterval(t); restart(); } }, 100);
})();
</script>"""


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
        st.page_link(page_of["parts"][0], label="대시보드 둘러보기", icon=":material/dashboard:", query_params={"sec": "summary"})
        st.page_link(page_of["parts"][0], label="직접 조회하기", icon=":material/search:", query_params={"sec": "detail"})

    # 2) 왜 전자부품인가 — 이유(본문) + 그 이유를 확인하는 화면 네 곳(아이콘). 아이콘은 이야기 순서 ① → ① → ③ → ④
    #    98.9% 는 인용(국방반도체 발전전략 본문 · 2023-12 조사) — 본문에는 각주 표시(*)만, 출처 · 한계는 아래 각주 줄에.
    #    * · 98.9% 에 마우스를 올리면 아래 각주 줄이 파란 글씨로 커진다(.mi-hit — CSS :has)
    #    「의존도」 · 「공급망」은 쓰지 않는다
    with st.container(key="mi", horizontal=True):
        st.html('<div class="mi-txt"><div class="k">WHY ELECTRONICS</div>'
                '<h2>왜 <em>전자부품</em>인가?</h2>'
                '<p>탐지 · 통신 · 항법 · 제어 같은 무기체계의 핵심 기능은 반도체와 전자부품이 맡습니다. '
                '그런데 무기체계에 들어가는 반도체의 <span class="mi-hit"><sup class="mi-ref">*</sup><b>98.9%</b></span>는 해외에서 들여오고, '
                '분석 대상 13개 품목군 중 <b>5개</b>는 2025년 수입액의 절반 이상을 한 나라에서 들여왔습니다(민수 포함). '
                '우리 정부도 2024년 국방반도체 발전전략, 2026년 국방반도체법으로 반도체와 부품국산화 사업으로 전자부품 전반의 국산화를 추진하고 있습니다.</p>'
                '<p>이 대시보드는 공개 데이터로 이 부품들의 <b>수출입 → 군 조달 → 국산화</b> 현황을 차례로 보여 줍니다.</p>'
                '<small class="mi-src">* 무기체계 적용 반도체의 해외 도입 비중 — 국방반도체 발전전략(2024-11)이 인용한 2023-12 조사 값입니다. '
                '팀이 계산한 값이 아니며 분모 기준은 확인하지 못했습니다.</small></div>')
        with st.container(key="mi_links", horizontal=True):
            for u, sec, label, icon in [("parts", "summary", "13개 품목군은 무엇인가", "memory"),
                                        ("parts", "trade", "어느 나라에서 들여오나", "public"),   # 지구본은 수출입 현황으로 옮김
                                        ("local", "done", "무엇을 국산화했나", "build"),
                                        ("background", "policy", "정책 · 예산은 어떻게", "account_balance")]:
                st.page_link(page_of[u][0], label=label, icon=f":material/{icon}:", query_params={"sec": sec})

    # 3) 주요 분석 사진 카드
    st.html('<div class="mc-head"><h2><small>ANALYSIS</small>주요 분석 바로가기</h2>'
            '<span>카드를 누르면 해당 메뉴의 첫 화면으로 이동합니다</span></div>')
    with st.container(key="mcards", horizontal=True):
        for i, (u, sec, img, cat, title, desc) in enumerate(MAIN_CARDS):
            with st.container(key=f"mc_{i}"):
                st.html(f'<div class="mc-img"><b>{cat}</b><div style="background-image:url(\'{img}\')"></div></div>'
                        f'<div class="mc-body"><h3>{title}</h3><p>{desc}</p></div>')
                st.page_link(page_of[u][0], label="자세히 보기", icon=":material/arrow_forward:", query_params={"sec": sec})

    # 4) 숫자 띠
    stats = "".join(f'<div class="mst-i"><div class="v">{v}<small>{u}</small></div><div class="l">{l}</div></div>'
                    for v, u, l in MAIN_STATS)
    st.html(f'<div class="mst" style="background-image:url(\'{_ph("1562408590-e32931084e23", 1800)}\')"><div class="mst-in">'
            f'<div class="mst-h"><b>숫자로 보는<br>K-Defense</b><span>2025년 기준 · 화면 배치용 샘플 값</span></div>'
            f'{stats}</div></div>')

    # 5) 데이터 출처 목록 · 이용 안내 (09-30 피드백 — 자료 일자 대신 데이터 출처. 기준 시점은 ④ 데이터 출처 · 검증에 있다)
    with st.container(key="mb", horizontal=True):
        rows = "".join(f'<li><a href="{link}" target="_blank" rel="noopener" title="{org} · {n} 원본 페이지 새 탭으로 열기">'
                       f'<b>{org}</b><span>{n}</span><em>{when}</em><i class="ms">open_in_new</i></a></li>'
                       for org, n, when, link in MAIN_SOURCES)
        st.html(f'<div><div class="mb-h"><h3>데이터 출처</h3><span>자료별 제공 기관 · 수록 기간</span></div>'
                f'<ul class="mb-list">{rows}</ul></div>')
        with st.container():
            st.html('<div class="mb-box"><small>GUIDE</small><h3>처음 오셨나요?<br>이렇게 보시면 됩니다</h3><ul>'
                    '<li>상단 메뉴에 커서를 올리면 메뉴별 화면 목록이 펼쳐집니다</li>'
                    '<li>각 메뉴 왼쪽 목록에서 화면을 하나씩 고릅니다</li>'
                    '<li>각 메뉴의 「상세 조회」에서 조건을 골라 직접 그려 봅니다</li>'
                    '<li>화면의 숫자는 배치를 보여 주기 위한 샘플입니다</li></ul>'
                    '<div style="height:70px"></div></div>')
            with st.container(key="mb_go", horizontal=True):
                st.page_link(page_of["parts"][0], label="현황표 보기", icon=":material/insights:", query_params={"sec": "summary"})
                st.page_link(page_of["background"][0], label="데이터 출처", icon=":material/folder_open:",
                             query_params={"sec": "source"})








def pct_rows(rows: list[tuple[str, float, str]]) -> str:
    """이름 · 막대 · % 한 줄씩(점선 = 50%). 공급 국가 비중 카드와 같은 모양."""
    return '<div class="bars big">' + "".join(
        f'<div class="row" title="{n} {v:.1f}%"><div class="nm">{n}</div><div class="track">'
        f'<div class="fill" style="width:{v:.1f}%;background:{c}"></div><div class="ref"></div></div>'
        f'<div class="pct">{v:.1f}%</div></div>' for n, v, c in rows) + "</div>"






BASIS_SHOW = 6                # 선정 근거 표에서 처음부터 보이는 줄 수 — 나머지는 펼쳐 보기


def basis_matrix(rows: list[tuple[str, str, str, str]], start: int = 0, title: str = "", card: bool = True,
                 tag_cols: list[tuple[str, str]] = BASIS_TAGS) -> str:
    """선정 근거 행렬. start = 전체 목록에서 이 표의 첫 줄 위치(분석 대상/배경 경계선과 등장 순서용).
    tag_cols = 보여 줄 근거 열(기본 전부) — 종합 현황표는 HS↔FSC 연결 흔적인 R4(B2-FSC) 열을 뺀다."""
    tag_color = {"HSK-군용": "#e5484d", "HSK-항공/항행": SERIES[0], "전략물자-DU": SERIES[2],
                 "B2-FSC": SERIES[1], "A6": SERIES[3], "팀판단": "#94a7c8"}
    rule = {"HSK-군용": "R1", "HSK-항공/항행": "R2", "전략물자-DU": "R3", "B2-FSC": "R4"}
    head = "".join(f'<th title="{d}">{t}{"<br><small>" + rule[t] + "</small>" if t in rule else ""}</th>' for t, d in tag_cols)
    body = ""
    for k, (hs, name, cat, ev) in enumerate(rows):
        tags = set(ev.split(";"))
        cells = "".join(f'<td>{f"<i style=background:{tag_color[t]};animation-delay:{k * .025:.2f}s></i>" if t in tags else ""}</td>'
                        for t, _ in tag_cols)
        tgt = ('<span style="color:#067647;font-weight:700">분석 대상</span>' if hs in TARGET_HS
               else '<span style="color:#8494ae">배경</span>')
        sep = ' style="border-top:2px solid #b7c7e2"' if start + k == len(TARGET_HS) and k else ""
        body += f'<tr{sep}><td class="nm"><em>{hs}</em>{name}</td><td class="cat">{cat}</td><td>{tgt}</td>{cells}</tr>'
    table = (f'<table class="basis"><thead><tr><th style="text-align:left">품목군(HS6)</th><th>분류</th><th>구분</th>{head}</tr></thead>'
             f'<tbody>{body}</tbody></table>')
    if not card:
        return table
    return (f'<div class="card"><div class="h">{title} <span class="sub">전체 {len(HS_BASIS)}개 · 진입 = R1 또는 R2'
            f'(2026-09-21 확정) · 점 = 해당 근거 · 열 제목에 커서를 올리면 뜻</span></div>{table}</div>')


def basis_summary() -> str:
    n = len(HS_BASIS)
    cnt = {t: sum(1 for *_, ev in HS_BASIS if t in ev.split(";")) for t, _ in BASIS_TAGS}
    colors = [("HSK-군용", "#e5484d"), ("HSK-항공/항행", SERIES[0]), ("전략물자-DU", SERIES[2]),
              ("B2-FSC", SERIES[1]), ("A6", SERIES[3]), ("팀판단", "#94a7c8")]
    rows = [(f"{t} ({cnt[t]})", cnt[t] / n * 100, c) for t, c in colors]
    cats = {}
    for _, _, cat, _ in HS_BASIS:
        cats[cat] = cats.get(cat, 0) + 1
    cat_txt = " · ".join(f"{c} {v}" for c, v in sorted(cats.items(), key=lambda x: -x[1]))
    return (f'<div class="card"><div class="h">근거별 해당 품목군 비율 <span class="sub">수집 24개 중 · 괄호 = 개수</span></div>'
            + pct_rows(rows)
            + f'<div class="note" style="margin-top:12px"><b>분석 대상 {len(TARGET_HS)}개 = R1 또는 R2</b> — '
              f'13개 모두 R2(항공·항행), 그중 3개(IC)는 R1 도 해당. 나머지 {n - len(TARGET_HS)}개는 배경 자료.<br>'
              f'분류: {cat_txt}</div></div>')


def basis_legend() -> str:
    return '<div class="note" style="margin-top:10px">' + "<br>".join(
        f"· <b>{t}</b> — {d}" for t, d in BASIS_TAGS) + "</div>"




# ── 조회 — DATA CENTER 목업용 샘플(실제 데이터 아님) ──────────────────────────────
# TODO: DB 연결 시 제거할 DATA CENTER 목업용 샘플 — 아래 MOCK_* 는 화면 구조 · 인터랙션 확인용으로 지어낸 값이다.
#       코드 · 이름 · 건수 모두 실제 DB 값이 아니며, DB 연결 단계에서 조회 결과로 통째로 바꾼다.
# 품목코드(HS6) — 분석 대상 13개(TARGET_HS)와 이름(HS_BASIS)을 그대로 쓴다. 홈 표의 5개(FOCUS_HS)를 앞에
_HS_NAME = {c: n for c, n, *_ in HS_BASIS}
MOCK_HS6 = {c: _HS_NAME[c] for c in FOCUS_HS + sorted(TARGET_HS - set(FOCUS_HS))}
# 품목코드(HS10) — 목업용 샘플: HS6 하나를 「군용」 · 「기타」 두 세분으로 나눈 임시 코드(실제 HSK 10단위 아님)
MOCK_HS10 = {f"{c}{s}": f"{n}({t})" for c, n in MOCK_HS6.items() for s, t in (("1000", "군용"), ("9000", "기타"))}
# 품목코드 선택 비중(목업용 샘플) — 품목을 골라 내면 교역액을 이 비중만큼만 보여 준다. 13개 모두 = 1(기존 값 그대로)
MOCK_HS_WEIGHT = {c: 1 + (int(c) % 7) / 3 for c in MOCK_HS6}

# 군수품 FSG / FSC — 목업용 샘플(이름은 군급분류집 표기를 줄여 쓴 것, 건수는 지어낸 값)
MOCK_FSG = {"58": "통신·탐지", "59": "전기·전자 구성품", "60": "광섬유"}
MOCK_FSC = {
    "58": {"5820": "무선 통신장비", "5821": "항공기용 무선장비", "5840": "레이더 장비", "5845": "수중 음향장비",
           "5865": "전자전 장비"},
    "59": {"5905": "저항기", "5910": "축전기", "5915": "필터 및 회로망", "5961": "반도체 디바이스",
           "5962": "마이크로전자회로"},
    "60": {"6010": "광섬유 전도체", "6015": "광섬유 케이블", "6060": "광섬유 연결기"},
}
MOCK_FSC_NAME = {c: n for g in MOCK_FSC.values() for c, n in g.items()}
MOCK_FSC_FSG = {c: g for g, fs in MOCK_FSC.items() for c in fs}
MOCK_BRANCHES = ["육군", "해군", "공군", "해병대", "국직"]
MOCK_REQ_YEARS = list(range(2020, 2028))                      # 요구연도 목업 범위
MOCK_ITEM_KINDS = ["전체", "완성품", "구성품", "수리부속"]
MOCK_EQUIP = ["K9 자주포", "K2 전차", "천무 다연장로켓", "KF-21 전투기", "이지스 구축함", "K21 보병전투차", "수리온 헬기"]
_MOCK_WORDS = {"5820": "송수신기", "5821": "항공 무전기", "5840": "레이더 송신부", "5845": "소나 센서", "5865": "재밍 모듈",
               "5905": "정밀 저항기", "5910": "세라믹 축전기", "5915": "RF 필터", "5961": "전력 트랜지스터",
               "5962": "FPGA 모듈", "6010": "광섬유 전도체", "6015": "광케이블 조립체", "6060": "광 커넥터"}
_MOCK_FUNC = ["신호처리", "전원공급", "송수신", "탐지", "제어"]


def _mock_fsg_items() -> pd.DataFrame:
    """군수품 품목 목록(목업용 샘플) — FSC 마다 품목 몇 개를 규칙적으로 지어낸다. NSN 도 가짜 번호."""
    rows = []
    for i, (fsc, word) in enumerate(_MOCK_WORDS.items()):
        for k in range(4 + i % 4):
            n = i * 11 + k
            rows.append({"NSN": f"{fsc}-00-{(n * 7919) % 900 + 100:03d}-{(n * 104729) % 9000 + 1000:04d}",
                         "품목명": f"{word} {chr(65 + k)}형", "FSG": MOCK_FSC_FSG[fsc], "FSC": fsc,
                         "기능명": _MOCK_FUNC[n % len(_MOCK_FUNC)], "품목종류": MOCK_ITEM_KINDS[1 + n % 3],
                         "군종": MOCK_BRANCHES[n % len(MOCK_BRANCHES)], "요구연도": MOCK_REQ_YEARS[n % len(MOCK_REQ_YEARS)],
                         "적용장비": MOCK_EQUIP[n % len(MOCK_EQUIP)], "KDSIS 연결": n % 3 != 0})
    return pd.DataFrame(rows)


MOCK_FSG_ITEMS = _mock_fsg_items()

# 국산화개발 — 목업용 샘플(사업명은 예시, 업체명은 가상의 「샘플업체」, 부품관리번호 · NSN 은 가짜 번호)
MOCK_LOCALIZED_PROJECTS = ["K9", "K9A1", "천무", "K2", "K21", "소형전술차량"]
MOCK_COMPANIES = [f"샘플업체 {c}" for c in "ABCDEFGH"]


def _mock_localized() -> pd.DataFrame:
    """국산화개발 기록(목업용 샘플) — 기록 하나 = 부품 × 사업 × 관련 업체. 같은 부품이 여러 사업에 나온다."""
    rows = []
    fscs = [c for c in _MOCK_WORDS if MOCK_FSC_FSG[c] != "60"]   # 국산화개발은 FSG 60(광섬유) 행이 없다(DB 0행 · 홈 KPI 와 맞춤)
    for n in range(84):
        fsc = fscs[(n * 7) % len(fscs)]                         # 7 은 FSC 10개와 서로소 — 모든 FSC 가 나온다
        part = n % 52                                           # 52개 부품이 84행에 나눠 나온다(고유 부품 < 기록 수)
        rows.append({"부품관리번호": f"LP-{part + 1:04d}",
                     "NSN": f"{fsc}-01-{(part * 6151) % 900 + 100:03d}-{(part * 7873) % 9000 + 1000:04d}",
                     "품목명": f"{_MOCK_WORDS[fsc]} 국산화품", "FSG": MOCK_FSC_FSG[fsc], "FSC": fsc,
                     "사업명": MOCK_LOCALIZED_PROJECTS[(n * 5) % len(MOCK_LOCALIZED_PROJECTS)],   # n*3 은 K9 · K2 만 나왔다
                     "관련 업체": MOCK_COMPANIES[(n * 5 + part) % len(MOCK_COMPANIES)]})
    return pd.DataFrame(rows)


MOCK_LOCALIZED = _mock_localized()
MOCK_LOCALIZED_FSG = {g: n for g, n in MOCK_FSG.items() if g in set(MOCK_LOCALIZED["FSG"])}   # 58 · 59


# ── 조회 — 분석 조건 설정 ───────────────────────────────────────────────────
# 데이터 유형 — 고르면 조회조건 · 지표 · 차트 · 결과 탭이 통째로 바뀐다. 유형마다 session_state 키 앞머리가 다르다
Q_TYPE_PREFIX = {"수출입 HS": "qs_", "군수품 FSG/FSC": "qf_", "국산화개발": "ql_"}
Q_AREAS = ["수출입", "수출", "수입"]
Q_YEARS = list(range(2016, 2027))                            # 기간 — 시작 연도 ~ 끝 연도(2026 은 1~8월 부분연도)
# 지표 이름, 단위, 아이콘, 쓸 수 있는 분석영역 — 목업처럼 3개씩 두 줄
Q_METRICS = [("수출액", "백만 USD", "upload", {"수출입", "수출"}), ("수입액", "백만 USD", "download", {"수출입", "수입"}),
             ("무역수지", "백만 USD", "balance", {"수출입"}), ("수출중량", "톤", "directions_boat", {"수출입", "수출"}),
             ("수입중량", "톤", "inventory_2", {"수출입", "수입"}), ("거래건수", "건", "receipt_long", {"수출입", "수출", "수입"})]
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
Q_METRIC_COLOR = {"수출액": "#0fa595", "수입액": ACCENT, "무역수지": SERIES[3], "수출중량": "#0b7f78",
                  "수입중량": SERIES[2], "거래건수": SERIES[4]}
Q_PALETTE = SERIES + ["#34d399", "#f59e0b", "#a78bfa", "#94a3b8", "#fb7185", "#22d3ee", "#84cc16", "#e879f9"]

Q_DEFAULT = {"qs_area": "수출입", "qs_hs": "HS6", "qs_ctry": ["미국", "폴란드", "사우디아라비아"],
             "qs_item": list(FOCUS_HS), "qs_item_all": True,     # 품목코드 — 기본은 전체 품목(기존 결과 값 그대로)
             "qs_y0": Q_YEARS[0], "qs_y1": Q_YEARS[-1], "qs_chart": "막대 그래프",
             **{f"qs_m_{m}": m in Q_MONEY for m, *_ in Q_METRICS}}

# 군수품 FSG/FSC — 지표(이름, 단위, 아이콘) · 차트. HS 지표는 이 유형에서 그리지 않는다
QF_BRANCH_ROWS = {"qf_branch_a": MOCK_BRANCHES[:3], "qf_branch_b": MOCK_BRANCHES[3:]}   # 군종 버튼 두 줄(3 + 2)
QF_METRICS = [("품목 건수", "건", "inventory_2"), ("FSC 수", "개", "category"),
              ("적용장비 수", "종", "precision_manufacturing"), ("KDSIS 연결 건수", "건", "link")]
QF_CHARTS = ["막대 그래프", "누적 막대 그래프", "도넛 그래프", "트리맵 차트", "꺾은선 그래프"]
QF_DEFAULT = {"qf_fsg": list(MOCK_FSG), "qf_fsg_all": True, "qf_fsc": [],
              **{k: list(v) for k, v in QF_BRANCH_ROWS.items()}, "qf_y0": MOCK_REQ_YEARS[0], "qf_y1": MOCK_REQ_YEARS[-1],
              "qf_name": "", "qf_func": "", "qf_kind": "전체", "qf_nsn": "", "qf_chart": "막대 그래프",
              **{f"qf_m_{m}": m in ("품목 건수", "FSC 수") for m, *_ in QF_METRICS}}
# 국산화개발 — 스냅샷 자료라 건수 · 개수만 센다(국산화율 · 성공률 · BOM 대비 비율 · 연도별 추이는 만들지 않는다)
QL_METRICS = [("국산화개발 기록 수", "건", "library_books"), ("고유 부품 수", "개", "extension"),
              ("사업 수", "개", "inventory"), ("관련 업체 수", "개", "factory")]
QL_CHARTS = ["막대 그래프", "도넛 그래프", "트리맵 차트"]
QL_DEFAULT = {"ql_proj": list(MOCK_LOCALIZED_PROJECTS[:3]), "ql_proj_all": False, "ql_fsg": list(MOCK_LOCALIZED_FSG),
              "ql_fsg_all": True, "ql_fsc": [], "ql_name": "", "ql_comp": [], "ql_comp_all": True,
              "ql_part": "", "ql_nsn": "", "ql_chart": "막대 그래프",
              **{f"ql_m_{m}": m in ("국산화개발 기록 수", "고유 부품 수") for m, *_ in QL_METRICS}}
Q_TYPE_DEFAULT = {"수출입 HS": Q_DEFAULT, "군수품 FSG/FSC": QF_DEFAULT, "국산화개발": QL_DEFAULT}
# 빠른 설정 — 고르면 아래 조건이 한꺼번에 바뀐다(적지 않은 값은 기본값)
Q_QUICK = {
    "빠른 설정 불러오기": None,
    "방산 수출 주력국 (폴란드·중동·호주)": {"qs_area": "수출", "qs_ctry": ["폴란드", "사우디아라비아", "아랍에미리트", "호주"],
                                  "qs_chart": "누적 막대 그래프", "qs_m_수출액": True, "qs_m_거래건수": True},
    "대미 교역 점검 (미국 수출입)": {"qs_ctry": ["미국"], "qs_chart": "꺾은선 그래프", "qs_y0": 2021, "qs_y1": 2025},
    "아시아 공급망 (중국·일본·대만)": {"qs_area": "수입", "qs_ctry": ["중국", "일본", "대만", "싱가포르"], "qs_chart": "도넛 그래프",
                                "qs_m_수입액": True},
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


def trade_frame(names: list[str], y0: int, y1: int, hs: str, items: list[str] | None = None) -> pd.DataFrame:
    """국가 × 연도 교역 표(샘플). 2016~2025 합 = TRADE_IMP·TRADE_EXP, 2026 은 1~8월 부분연도.
    HS10 은 같은 금액을 더 잘게 나눠 신고한 것이라 거래건수만 늘어난다.
    items(품목코드)를 주면 그 품목 몫(MOCK_HS_WEIGHT, 목업용 비중)만큼만 남긴다 — None(전체 품목)이면 기존 값 그대로."""
    share = 1.0
    if items is not None:
        # HS10 은 위 HS6 몫을 세분 수만큼 똑같이 나눈다(목업) — HS6 하나 = HS10 두 개
        per = {c: MOCK_HS_WEIGHT[c[:6]] / (1 if len(c) == 6 else 2) for c in items}
        share = sum(per.values()) / sum(MOCK_HS_WEIGHT.values())
    rows = []
    for k, n in enumerate(names):
        wi = [(1 + 0.07 * i) * (1 + 0.06 * math.sin(i * 1.3 + k)) for i in range(len(YEARS))]
        we = [(1 + 0.11 * i) * (1 + 0.08 * math.sin(i * 0.9 + k * 1.7)) for i in range(len(YEARS))]
        si, se = sum(wi[:-1]), sum(we[:-1])
        for i, y in enumerate(YEARS):
            if not y0 <= y <= y1:
                continue
            part = 0.62 if y == 2026 else 1
            imp = TRADE_IMP.get(n, 0) * wi[i] / si * part * share
            exp = TRADE_EXP.get(n, 0) * we[i] / se * part * share
            cnt = round(((imp + exp) * 1.8 + 3) * (1.6 if hs == "HS10" else 1))
            rows.append({"국가": n, "연도": y, "수출액": round(exp, 1), "수입액": round(imp, 1),
                         "무역수지": round(exp - imp, 1), "수출중량": round(exp * 0.52, 1),
                         "수입중량": round(imp * 0.38, 1), "거래건수": cnt})
    return pd.DataFrame(rows)


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


def _q_reset() -> None:
    """초기화 버튼 — 지금 데이터 유형의 분석 조건을 처음(사용자가 바꾸기 전) 상태로 되돌린다. 데이터 유형은 그대로 둔다."""
    ss = st.session_state
    _q_apply(Q_TYPE_DEFAULT[ss["qd_type"]], force=True)
    if ss["qd_type"] == "수출입 HS":
        ss["qs_quick"] = "빠른 설정 불러오기"
    ss["q_reset_n"] = ss.get("q_reset_n", 0) + 1                # 누를 때마다 아이콘 회전 애니메이션을 다시 건다


def _q_hs_unit() -> None:
    """HS6 ↔ HS10 전환 — 고른 품목코드를 새 단위로 옮긴다(HS6 → 그 아래 HS10 전부, HS10 → 위 HS6)."""
    ss = st.session_state
    cur = ss.get("qs_item", [])
    if ss.get("qs_hs", "HS6") == "HS10":
        ss["qs_item"] = [c for c in MOCK_HS10 if c[:6] in {x[:6] for x in cur}]
    else:
        ss["qs_item"] = [c for c in MOCK_HS6 if c in {x[:6] for x in cur}]


def _q_keep(key: str, options: list) -> list:
    """위젯을 그리기 전에 선택값을 지금 목록(options)에 있는 것만 남긴다 — 상위 조건(FSG · HS 단위)이 바뀌어
    목록에서 사라진 값이 남아 있으면 multiselect 가 오류를 낸다."""
    ss = st.session_state
    ss[key] = [v for v in ss.get(key, []) if v in options]
    return ss[key]


# 왼쪽 글씨 칸 높이 = 오른쪽 첫 입력칸 높이(px). 위로 붙여 놓고 그 높이 안에서 가운데 → 글씨와 입력칸이 같은 가로선
Q_ROW_H = {"dtype": 32, "area": 32, "hs": 32, "item": 40, "ctry": 40, "period": 40, "metric": 40,
           "fsg": 40, "fsc": 40, "branch": 32, "year": 40, "name": 40, "proj": 40, "comp": 40}
Q_CHIP_COLS = 3                                               # 고른 국가를 입력칸 밑에 한 줄 3개씩
Q_CHIP_SCROLL = 10                                            # 체크박스 드롭다운에서 이만큼 이상 고르면 칩 칸을 스크롤로
Q_CHIP_ROWS = 3                                               # 스크롤 칸에 한 번에 보이는 칩 줄 수(칩 30px · 줄 간격 6px)
# 칩 다중선택 — 선택창 key → 칩 묶음 key. 국가는 예전 key(qs_chips) 그대로
Q_CHIP_KEY = {"qs_ctry": "qs_chips", "qs_item": "qs_item_chips", "qf_fsg": "qf_fsg_chips", "qf_fsc": "qf_fsc_chips",
              "ql_proj": "ql_proj_chips", "ql_fsg": "ql_fsg_chips", "ql_fsc": "ql_fsc_chips", "ql_comp": "ql_comp_chips"}
# 파란 선택창 — 데이터 유형 드롭다운 · 기간 · 요구연도
Q_YEAR_KEYS = ["qd_type", "qs_y0", "qs_y1", "qf_y0", "qf_y1"]


def _q_form_css(hints: dict[str, str]) -> str:
    """분석 조건 카드 CSS. hints = {칩 다중선택 key: 입력칸 안 안내 문구} — 그 화면에 그린 선택창만 넘긴다.
    국가/지역에만 걸려 있던 칩 UX(선택창 파랑 · 선택값은 칸 밖 칩)를 hints 의 key 마다 똑같이 만든다."""
    rows = "".join(f".st-key-card_form .st-key-qlab_{k}{{height:{h}px !important;flex:0 0 auto !important;justify-content:center !important}}"
                   for k, h in Q_ROW_H.items())
    ms = list(hints)
    chips = [Q_CHIP_KEY[k] for k in ms]
    sel = lambda keys, tail: ",".join(f".st-key-{k} {tail}" for k in keys)
    hint_css = "".join(
        f'.st-key-{k} [data-testid="stMultiSelectTagsContainer"]::before{{content:"{h}"}}' for k, h in hints.items())
    return f"""<style>{rows}
/* Streamlit 기본 margin-bottom:-16px 이 글씨 칸을 3px 로 눌러 글씨가 아래로 삐져나왔다(약 8px 낮아 보이던 원인) */
.st-key-card_form div[class*="st-key-qlab_"] [data-testid="stMarkdownContainer"],
.st-key-card_form [data-testid="stMarkdownContainer"]:has(h3){{margin-bottom:0 !important}}
.st-key-card_form div[class*="st-key-qlab_"] [data-testid="stMarkdownContainer"] p{{line-height:1.2}}
/* 칩 다중선택(국가/지역 · 품목코드 · FSG · FSC · 사업명 · 관련 업체) · 연도 선택창 — 분석영역에서 고른 칸과 같은 색 */
{sel(ms, '[data-testid="stMultiSelect"] > div:last-child > div')},
{sel(Q_YEAR_KEYS, '[data-testid="stSelectbox"] > div:last-child > div')}{{background:rgba(43,110,246,.1) !important;
  border:1px solid var(--accent) !important}}
{sel(Q_YEAR_KEYS, '[data-testid="stSelectbox"] > div:last-child svg')},
{sel(ms, '[data-testid="stMultiSelect"] > div:last-child svg')}{{color:var(--accent)}}
/* 연도 숫자는 검은색 */
{sel(Q_YEAR_KEYS, '[data-testid="stSelectbox"] > div:last-child div')},
{sel(Q_YEAR_KEYS, '[data-testid="stSelectbox"] input')}{{color:#111;font-weight:600}}
/* 고른 값은 입력칸 안이 아니라 밑에 칩으로 쌓는다 */
{sel(ms, '[data-testid="stMultiSelectTagsContainer"] > span')}{{display:none}}
{sel(ms, '[data-testid="stMultiSelectTagsContainer"]::before')}{{color:#5a7fc9;font-size:14px;
  padding-left:4px;white-space:nowrap;align-self:center}}
{hint_css}
{sel(ms, '[data-testid="stMultiSelectTagsContainer"]:has(input:focus)::before')}{{content:none}}
{sel(ms, 'input:disabled::placeholder')}{{color:transparent}}   /* 전체 선택으로 잠기면 안내 문구만(관련 업체 칸에서 겹쳤다) */
{sel(chips, '')}{{gap:6px}}
{sel(chips, '[data-testid="stHorizontalBlock"]')}{{gap:6px;margin-bottom:0 !important}}
{sel(chips, 'button')}{{min-height:0;height:30px;padding:0 8px 0 12px;border-radius:6px;border:0;background:#1f3a6e;color:#fff;
  justify-content:space-between}}
{sel(chips, 'button:hover')}{{background:#142850;color:#fff}}   /* 칩 — 남색 */
{sel(chips, 'button > div')},{sel(chips, 'button > div > span')}{{width:100%;justify-content:space-between}}
{sel(chips, 'button p')}{{font-size:13px;font-weight:400;text-align:left;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}}
{sel(chips, 'button [data-testid="stMarkdownContainer"]')}{{min-width:0;flex:1 1 auto;overflow:hidden;text-align:left}}   /* wrap=True 라도 한 줄 · … */
{sel(chips, 'button [data-testid="stIconMaterial"]')}{{color:#fff !important;font-size:15px}}
/* 군종 두 줄 — 칸마다 폭을 한 줄 3칸 기준(1/3)으로 고정해 윗줄 · 아랫줄 칸 넓이를 맞춘다.
   다중선택 segmented_control 은 고른 칸에 aria-checked 없이 data-selected 만 붙어 전역 파랑 규칙이 안 걸렸다 → 여기서 같은 색 */
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"]{{flex:0 0 calc(100% / 3) !important;
  max-width:calc(100% / 3);min-width:0}}
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"][data-selected]{{
  background:rgba(43,110,246,.1);border-color:var(--accent);color:var(--accent)}}
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"][data-selected] p{{font-weight:700}}   /* 고른 군종은 굵게 */
div[class*="st-key-qf_branch_"] [data-testid="stButtonGroup"] > div{{justify-content:flex-start}}
.st-key-qf_branch_box{{gap:0 !important}}
.st-key-qf_branch_box [data-testid="stElementContainer"]:has(.st-key-qf_branch_b),.st-key-qf_branch_b{{margin-top:-1px}}
/* 커서를 올렸을 때 — Streamlit 기본 강조색(빨강)이 테두리에 들던 것을 테마 파랑으로. 고른 칸은 조금 진한 파랑 바탕 */
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"]:hover,
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"]:focus-visible{{
  border-color:var(--accent) !important;color:var(--accent) !important;background:rgba(43,110,246,.05) !important;
  box-shadow:none !important}}
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"][data-selected]:hover{{
  background:rgba(43,110,246,.16) !important}}
div[class*="st-key-qf_branch_"] button[data-variant="segmented_control"]:hover *{{color:var(--accent) !important}}
/* 두 줄이 맞닿는 모서리는 직각 — 윗줄 아래 모서리 · 아랫줄 위 모서리. 윗줄 끝 칸(공군) 아래 오른쪽은 밑에 칸이 없어 둥근 채로 */
.st-key-qf_branch_a button[data-variant="segmented_control"]{{border-bottom-left-radius:0 !important}}
.st-key-qf_branch_a button[data-variant="segmented_control"]:not(:last-of-type){{border-bottom-right-radius:0 !important}}
.st-key-qf_branch_b button[data-variant="segmented_control"]{{border-top-left-radius:0 !important;border-top-right-radius:0 !important}}
/* 체크박스 드롭다운(FSC) — 펼친 목록이 아래 줄을 덮도록 위로 올린다 */
div[class*="st-key-"][class*="fsc_box"]{{position:relative;z-index:40;overflow:visible}}
/* 상세검색 접이 칸 — 카드 안에서 얇게 */
.st-key-card_form [data-testid="stExpander"] summary p{{font-size:13.5px;font-weight:700;color:#16233f}}
</style>"""


def _q_row(icon: str, text: str, key: str):
    """분석 조건 한 줄 — 왼쪽 글씨 칸(높이 Q_ROW_H[key]) · 오른쪽 입력 칸을 돌려준다."""
    a, b = st.columns([1, 2.55], vertical_alignment="top")
    with a.container(key=f"qlab_{key}"):
        _q_label(icon, text)
    return b


def _q_chip_select(key: str, options: list, fmt, placeholder: str, all_key: str | None = None,
                   all_label: str = "") -> list:
    """국가/지역과 같은 칩 다중선택 — 검색 가능한 선택창 + 고른 값은 밑에 칩(✕ 로 빼기) + (있으면) 전체 선택 체크.
    all_key 가 켜져 있으면 options 전부를 돌려준다. 선택창 안내 문구는 _q_hint 로 CSS 에 넣는다."""
    ss = st.session_state
    all_on = bool(all_key and ss[all_key])
    _q_keep(key, options)
    picked = st.multiselect(key, options, key=key, format_func=fmt, label_visibility="collapsed",
                            placeholder=placeholder, disabled=all_on)
    if not all_on:
        _q_chips(key, picked, fmt)
    if all_key:
        st.checkbox(all_label, key=all_key)
    return list(options) if all_on else picked


# 칩 말풍선 — 글씨가 칩 안에서 … 로 잘린 칩에만 보인다. 잘렸는지는 화면 폭에 따라 달라 서버에서 알 수 없으므로
# (글자 수로 어림하던 방식은 사우디아라비아처럼 잘리는데도 말풍선이 안 떴다) 모든 칩에 help 를 달고,
# 브라우저에서 커서를 올린 순간 글씨 폭(scrollWidth > clientWidth)을 재서 안 잘린 칩이면 <html data-chipfit> 를 켜
# 말풍선 층을 숨긴다. 말풍선은 한 번에 하나만 뜨므로 칩 위에 있을 때만 켜지는 이 표시로 충분하다
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

# 왼쪽 메뉴(스크롤형) — 소분류 링크(a.lnb-a)를 누르면 페이지를 다시 열지 않고 그 소분류 칸(.st-key-sub_*)으로 부드럽게
# 스크롤한다. 스크롤하면 지금 보이는 소분류를 ✓(.on) 로 · 위쪽 경로(.crumb b)도 그 이름으로 바꾼다.
# data.go = [소분류, 번호] — 다른 페이지 · 위쪽 메뉴에서 ?sec= 로 들어왔을 때 열린 뒤 한 번만 그 소분류로 간다
_LNB_JS = """
export default function (component) {
  const { data } = component
  window.__kdLnbLabels = data.labels || {}
  const subOf = k => document.querySelector(".st-key-sub_" + k)
  if (!window.__kdLnb) {
    window.__kdLnb = true
    const setOn = k => {
      document.querySelectorAll("a.lnb-a").forEach(a => a.classList.toggle("on", a.dataset.sub === k))
      const b = document.querySelector(".crumb b"), t = window.__kdLnbLabels[k]
      if (b && t) b.textContent = t
    }
    window.__kdLnbSetOn = setOn
    document.addEventListener("click", e => {
      const a = e.target.closest && e.target.closest("a.lnb-a")
      const el = a && subOf(a.dataset.sub)
      if (!el) return
      e.preventDefault(); e.stopPropagation()
      window.__kdLnbLock = Date.now() + 900         // 부드럽게 가는 동안 스크롤 감지가 ✓ 를 흔들지 않게
      setOn(a.dataset.sub)
      el.scrollIntoView({ behavior: "smooth", block: "start" })
    }, true)
    // 스크롤 위치 → 지금 보이는 소분류(칸 위쪽이 화면 위 160px 안으로 들어온 마지막 소분류)
    let raf = 0
    document.addEventListener("scroll", () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        if (Date.now() < (window.__kdLnbLock || 0)) return
        const subs = [...document.querySelectorAll("a.lnb-a")].map(a => a.dataset.sub)
        if (!subs.length) return
        let cur = subs[0]
        for (const k of subs) { const el = subOf(k); if (el && el.getBoundingClientRect().top <= 160) cur = k }
        setOn(cur)
      })
    }, true)
  }
  const go = data.go
  if (go && go[1] !== window.__kdLnbGoN) {
    window.__kdLnbGoN = go[1]
    let tries = 0
    const tick = () => {
      const el = subOf(go[0])
      if (el) { window.__kdLnbLock = Date.now() + 900; window.__kdLnbSetOn(go[0]); el.scrollIntoView({ block: "start" }) }
      else if (tries++ < 60) setTimeout(tick, 100)   // 그 소분류가 아직 그려지기 전이면 잠깐 기다린다
    }
    tick()
  }
}
"""
_LNB = st.components.v2.component("kd_lnb_scroll", html="<span></span>", js=_LNB_JS)


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
                # 말풍선 = 전체 이름(안 잘린 칩은 _CHIP_FIT_JS 가 숨긴다).
                # wrap=True — 끄면(기본) Streamlit 이 라벨에 브라우저 기본 말풍선(title)까지 달아 말풍선이 둘 뜬다.
                # 한 줄 · … 말줄임은 칩 CSS(_q_form_css)가 맡는다
                c.button(label, icon=":material/close:", icon_position="right",
                         key=f"qs_chip_{n}" if key == "qs_ctry" else f"{key}_chip_{n}",
                         on_click=_q_drop, args=(key, n), width="stretch", wrap=True, help=label)


# 체크박스 드롭다운(CCv2) — FSC 선택용. 목록 앞 체크박스로 여러 개를 고르는 동안에는 반영하지 않고,
# 드롭다운 밖으로 포커스가 나가면(바깥 클릭 · Tab · Esc) 고른 것을 한 번에 넘긴다(commit 트리거 → rerun 1번).
# 기본 multiselect 는 하나 고를 때마다 rerun 해서 조회 결과가 매번 다시 그려졌다
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
.dd{position:relative;font:14px Pretendard,'Malgun Gothic',system-ui,sans-serif}
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
.tools button{border:0;background:none;color:#2b6ef6;font:600 12.5px inherit;cursor:pointer;padding:2px 4px}
.tools .cnt{margin-left:auto;color:#6b7a99;font-size:12px}
.list{max-height:240px;overflow-y:auto}
.list label{display:flex;align-items:center;gap:8px;padding:6px 6px;border-radius:6px;cursor:pointer;color:#16233f;font-size:13.5px}
.list label:hover{background:rgba(43,110,246,.07)}
.list input{width:16px;height:16px;margin:0;accent-color:#2b6ef6;cursor:pointer}
.empty{padding:10px 6px;color:#6b7a99;font-size:13px}
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


def query_panel(fixed: str) -> dict:
    """분석 조건 설정 카드(목업 「분석 조건 설정」). 데이터 유형(fixed)에 따라 HS · FSG/FSC · 국산화개발 조건을 그리고,
    고른 조건을 dict 로 돌려준다(q["type"] = 데이터 유형). 유형은 메뉴마다 고정 — ① 수출입 HS · ② 군수품 FSG/FSC · ③ 국산화개발.
    유형마다 조건 키 앞머리(qs_ · qf_ · ql_)가 달라, 메뉴를 옮겨 다녀도 각 유형의 조건은 섞이지 않는다."""
    st.session_state["qd_type"] = fixed
    dtype = fixed
    _q_apply(Q_TYPE_DEFAULT[dtype])
    with st.container(border=True, key="card_form"):
        h1, h2 = st.columns([1.25, 1], vertical_alignment="center")
        h1.markdown("### :material/settings: 분석 조건 설정")
        if dtype == "수출입 HS":                                   # 빠른 설정은 HS 조건 묶음이라 HS 에서만
            h2.selectbox("빠른 설정", list(Q_QUICK), key="qs_quick", on_change=_q_quick, label_visibility="collapsed")
        panel = {"수출입 HS": query_panel_hs, "군수품 FSG/FSC": query_panel_fsg, "국산화개발": query_panel_localized}[dtype]
        q = panel()
        _q_reset_button()
        with st.container(key="chipfit_js"):
            _CHIP_FIT(key="chipfit")
    return q | {"type": dtype}


def _q_reset_button() -> None:
    """차트 유형 밑 초기화 버튼. 누르면 🔁 화살표 아이콘이 한 바퀴 돌고 조건이 처음 상태로 돌아간다.
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
.st-key-q_reset button:active [data-testid="stIconMaterial"]{{transform:rotate(180deg);transition:transform .25s}}
</style>""")
    st.button("조건 초기화", icon=":material/sync:", key="q_reset", on_click=_q_reset, width="stretch")


def query_panel_hs() -> dict:
    """수출입 HS 조건 — 분석영역 · HS 단위 · 품목코드 · 국가/지역 · 기간 · 지표 · 차트."""
    ss = st.session_state
    hs = ss["qs_hs"]
    codes = MOCK_HS6 if hs == "HS6" else MOCK_HS10
    st.html(_q_form_css({
        "qs_item": _q_hint("qs_item", "qs_item_all", "품목코드", f"전체 {hs} 품목 선택 중"),
        "qs_ctry": f"국가명을 검색하세요 · {len(ss['qs_ctry'])}개 선택" if ss["qs_ctry"] else ""}))

    area = _q_row(":material/travel_explore:", "분석영역", "area").segmented_control(
        "분석영역", Q_AREAS, key="qs_area", required=True, label_visibility="collapsed", width="stretch")
    hs = _q_row(":material/qr_code_2:", "HS6/HS10", "hs").segmented_control(
        "HS 단위", ["HS6", "HS10"], key="qs_hs", required=True, on_change=_q_hs_unit, label_visibility="collapsed")
    with _q_row(":material/barcode:", "품목코드", "item"):
        items = _q_check_select("qs_item", list(codes), lambda c: f"{c} - {codes[c]}", "품목코드",
                                f"{hs} 품목코드를 고르세요.", f"{hs} 코드 · 품목명 검색", "qs_item_all",
                                f"전체 품목 선택 ({hs} {len(codes)}개)", f"전체 {hs} 품목 선택 중")
    with _q_row(":material/public:", "국가/지역", "ctry"):
        names = _q_check_select("qs_ctry", Q_COUNTRIES, str, "국가", "국가를 고르세요.", "국가명 검색")
    with _q_row(":material/calendar_month:", "기간", "period"):
        # 두 칸에서 연도를 고른다 — 시작 칸은 끝 연도까지만, 끝 칸은 시작 연도부터만 보여 앞뒤가 뒤집히지 않는다
        c0, mid, c1 = st.columns([1, .16, 1], vertical_alignment="center", gap="small")
        y0 = c0.selectbox("시작 연도", [y for y in Q_YEARS if y <= ss["qs_y1"]], key="qs_y0", label_visibility="collapsed")
        mid.html('<div style="text-align:center;font-size:16px;font-weight:700;color:#6b7a99">~</div>')
        y1 = c1.selectbox("끝 연도", [y for y in Q_YEARS if y >= y0], key="qs_y1", label_visibility="collapsed")

    with _q_row(":material/leaderboard:", "지표 선택", "metric"):
        # 분석영역에 맞는 지표만 그린다(맞지 않는 지표는 잠그지 않고 아예 뺀다)
        shown = [m for m, _, _, areas in Q_METRICS if area in areas]
        cols = st.columns(3)
        metrics = [m for i, m in enumerate(shown) if cols[i % 3].checkbox(m, key=f"qs_m_{m}")]

    _q_label(":material/donut_large:", "차트 유형")
    chart = _q_chart_grid(Q_CHARTS, "qs_chart")
    names = [n for n in Q_COUNTRIES if n in names]
    return {"area": area, "hs": hs, "names": names, "items": items, "items_all": ss["qs_item_all"],
            "period": f"{y0} ~ {y1}", "years": (y0, y1), "metrics": metrics, "chart": chart}


def _q_fsg_fsc(pre: str, fsc_ph: str, groups: dict[str, str] = MOCK_FSG) -> tuple[list[str], list[str], list[str]]:
    """FSG(칩 다중선택 + 전체) → FSC(고른 FSG 안의 것만, 칩 다중선택). FSC 를 비우면 고른 FSG 의 FSC 전부.
    군수품 · 국산화개발 두 화면이 같이 쓴다(pre = qf_ / ql_). groups = 그 자료에 있는 FSG 만.
    (FSG, 사용자가 고른 FSC(비었으면 []), 조회에 쓸 FSC(비었으면 고른 FSG 의 전부)) — 군수품은 둘째 값이 비었는지로
    집계 단위(FSG · FSC)를 정한다."""
    with _q_row(":material/category:", "FSG", "fsg"):
        fsg = _q_chip_select(f"{pre}fsg", list(groups), lambda g: f"{g} - {MOCK_FSG[g]}", "FSG 를 검색하세요.",
                             f"{pre}fsg_all", f"전체 FSG 선택 ({len(groups)}개)")
    opts = [c for g in fsg for c in MOCK_FSC[g]]
    with _q_row(":material/account_tree:", "FSC", "fsc"):
        fsc = _q_check_select(f"{pre}fsc", opts, lambda c: f"{c} - {MOCK_FSC_NAME[c]}", "FSC", fsc_ph)
    return fsg, fsc, fsc or opts


# 지표 체크박스에 쓰는 짧은 이름 — 두 칸 폭에서 「국산화개발 기…」로 잘리던 것. 지표 키 · 카드 제목은 원래 이름
Q_METRIC_SHORT = {"국산화개발 기록 수": "기록 수"}


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
    st.html(_q_form_css({"qf_fsg": _q_hint("qf_fsg", "qf_fsg_all", "FSG", "전체 FSG 선택 중"),
                         "qf_fsc": _q_hint("qf_fsc", None, "FSC", "")}))
    # 집계 단위는 따로 고르지 않는다 — FSC 를 비우면(= 고른 FSG 아래 전체) FSG 단위, 하나라도 고르면 FSC 단위.
    # FSG 가 FSC 의 상위 분류라 「분류 단위 FSG/FSC」 토글은 두 분류체계 중 하나를 고르는 것처럼 보여 없앴다
    fsg, picked_fsc, fsc = _q_fsg_fsc("qf_", "FSC 를 고르세요 · 비우면 FSG 단위로 집계")
    unit = "FSC" if picked_fsc else "FSG"
    with _q_row(":material/military_tech:", "군종", "branch"), st.container(key="qf_branch_box", gap=None):
        # 다섯 칸을 한 줄에 두면 카드 폭이 좁아 가려져 두 줄(3 + 2)로 나눈다. 고른 값은 두 줄을 합친다.
        # gap=None + 아랫줄 -1px — 두 줄 사이 틈 없이 테두리가 한 줄로 겹쳐 붙는다
        branch = [b for k, opts in QF_BRANCH_ROWS.items()
                  for b in (st.segmented_control(f"군종 {k[-1]}", opts, key=k, selection_mode="multi",
                                                 label_visibility="collapsed", width="stretch") or [])]
    with _q_row(":material/calendar_month:", "요구연도", "year"):
        c0, mid, c1 = st.columns([1, .16, 1], vertical_alignment="center", gap="small")
        y0 = c0.selectbox("시작 연도", [y for y in MOCK_REQ_YEARS if y <= ss["qf_y1"]], key="qf_y0", label_visibility="collapsed")
        mid.html('<div style="text-align:center;font-size:16px;font-weight:700;color:#6b7a99">~</div>')
        y1 = c1.selectbox("끝 연도", [y for y in MOCK_REQ_YEARS if y >= y0], key="qf_y1", label_visibility="collapsed")
    name = _q_row(":material/search:", "품목명", "name").text_input(
        "품목명", key="qf_name", placeholder="품목명을 입력하세요.", label_visibility="collapsed")
    with st.expander("상세검색 — 기능명 · 품목종류 · NSN", icon=":material/tune:"):
        d1, d2, d3 = st.columns(3)
        func = d1.text_input("기능명", key="qf_func", placeholder="예: 신호처리")
        kind = d2.selectbox("품목종류", MOCK_ITEM_KINDS, key="qf_kind")
        nsn = d3.text_input("NSN", key="qf_nsn", placeholder="예: 5962-00")
    metrics = _q_metric_row("qf_", QF_METRICS)
    _q_label(":material/donut_large:", "차트 유형")
    chart = _q_chart_grid(QF_CHARTS, "qf_chart", "분류", QF_SHAPES)
    return {"unit": unit, "fsg": fsg, "fsc": fsc, "branch": branch or [], "years": (y0, y1), "name": name.strip(),
            "func": func.strip(), "kind": kind, "nsn": nsn.strip(), "metrics": metrics, "chart": chart}


def query_panel_localized() -> dict:
    """국산화개발 조건 — 사업명 · FSG · FSC · 품목명 · 관련 업체 · 상세검색 · 지표 · 차트. 기간 조건은 없다(스냅샷)."""
    st.html(_q_form_css({"ql_proj": _q_hint("ql_proj", "ql_proj_all", "사업명", "전체 사업 선택 중"),
                         "ql_fsg": _q_hint("ql_fsg", "ql_fsg_all", "FSG", "전체 FSG 선택 중"),
                         "ql_fsc": _q_hint("ql_fsc", None, "FSC", ""),
                         "ql_comp": _q_hint("ql_comp", "ql_comp_all", "관련 업체", "전체 관련 업체 선택 중")}))
    with _q_row(":material/inventory:", "사업명", "proj"):
        proj = _q_chip_select("ql_proj", MOCK_LOCALIZED_PROJECTS, str, "사업명을 검색하세요.",
                              "ql_proj_all", f"전체 사업 선택 ({len(MOCK_LOCALIZED_PROJECTS)}개)")
    fsg, _, fsc = _q_fsg_fsc("ql_", "FSC 를 고르세요 · 비우면 고른 FSG 전체", MOCK_LOCALIZED_FSG)
    name = _q_row(":material/search:", "품목명", "name").text_input(
        "품목명", key="ql_name", placeholder="국산화개발 품목명을 입력하세요.", label_visibility="collapsed")
    with _q_row(":material/factory:", "관련 업체", "comp"):
        comp = _q_chip_select("ql_comp", MOCK_COMPANIES, str, "관련 업체를 검색하세요.",
                              "ql_comp_all", f"전체 관련 업체 선택 ({len(MOCK_COMPANIES)}개)")
    with st.expander("상세검색 — 부품관리번호 · NSN", icon=":material/tune:"):
        d1, d2 = st.columns(2)
        part = d1.text_input("부품관리번호", key="ql_part", placeholder="예: LP-0012")
        nsn = d2.text_input("NSN", key="ql_nsn", placeholder="예: 5962-01")
    metrics = _q_metric_row("ql_", QL_METRICS)
    _q_label(":material/donut_large:", "차트 유형")
    chart = _q_chart_grid(QL_CHARTS, "ql_chart", "FSC", QL_SHAPES)
    return {"proj": proj, "fsg": fsg, "fsc": fsc, "name": name.strip(), "comp": comp, "part": part.strip(),
            "nsn": nsn.strip(), "metrics": metrics, "chart": chart}


def query_chart(df: pd.DataFrame, q: dict) -> None:
    """차트 유형에 맞춰 그린다. 금액 지표(수출액·수입액·무역수지)끼리만 한 축에 두고,
    중량·건수는 금액이 하나도 없을 때만 그린다(단위가 달라 한 축에 섞지 않는다)."""
    names, chart = q["names"], q["chart"]
    plot_ms = [m for m in q["metrics"] if m in Q_MONEY] or q["metrics"][:1]
    primary = plot_ms[0]
    unit = Q_UNIT[primary]
    by_c = df.groupby("국가", sort=False)[list(Q_UNIT)].sum()
    color = {n: Q_PALETTE[i % len(Q_PALETTE)] for i, n in enumerate(names)}
    note = ""
    fig = go.Figure()
    if chart not in ("도넛 그래프", "막대 그래프", "꺾은선 그래프", "누적 막대 그래프", "면적 그래프"):
        # 나머지 차트는 CSV 와 같은 모양의 표로 그린다(내려받는 CSV 와 그림이 어긋나지 않게)
        out, note = csv_shape(chart, df, q)
        fig = csv_preview(chart, out)
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch", theme=None)
        st.html(info_line(f'그래프 기준: {note} · {q["hs"]} 기준.'))
        return
    if chart == "도넛 그래프":
        pm = primary if primary != "무역수지" else ("수출액" if q["area"] != "수입" else "수입액")
        if pm != primary:
            note = "무역수지는 음수가 있어 원형으로 나눌 수 없어 수출액으로 그렸습니다."
        rows = sorted(((n, float(by_c.loc[n, pm]), color[n]) for n in names), key=lambda r: -r[1])
        rows = rows[:7] + ([("기타", sum(r[1] for r in rows[7:]), ETC)] if len(rows) > 7 else [])
        hover_donut(rows, f"{sum(r[1] for r in rows):,.0f}", f"{pm} 합계 · {Q_UNIT[pm]}", value_unit=Q_UNIT[pm], height=420)
        fig = None
    elif chart == "막대 그래프":
        order = by_c.loc[names].sort_values(primary, ascending=False).index.tolist()
        for m in plot_ms:
            fig.add_trace(go.Bar(x=order, y=by_c.loc[order, m], name=m,
                                 marker=dict(color=Q_METRIC_COLOR[m], line=dict(color="#fff", width=1)),
                                 text=[f"{v:,.0f}" for v in by_c.loc[order, m]] if len(plot_ms) == 1 else None,
                                 textposition="outside", textfont=dict(size=11, color=TEXT), cliponaxis=False,
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
        if 2026 in years:
            note = "2026년은 1~8월 부분연도입니다."
    if fig is not None:
        fig.update_layout(legend=dict(orientation="h", y=1.12), height=400, margin=dict(l=58, r=10, t=30, b=8))
        fig.update_yaxes(tickformat=",.0f")
        st.plotly_chart(style_fig(fig), width="stretch", theme=None)
    dropped = [m for m in q["metrics"] if m not in plot_ms and chart != "도넛 그래프"]
    msg = " ".join(x for x in (note, f"{'·'.join(dropped)}은(는) 단위가 달라 그래프에서 빼고 위 지표 카드와 표에만 둡니다."
                               if dropped else "") if x)
    st.html(info_line(f'그래프 기준: {"·".join(plot_ms)} ({unit}) · {q["hs"]} 기준. {msg}'))


# ── 조회 — 차트 유형 15종 설명 · CSV 를 차트 모양대로(KOSIS 「데이터 시각화 체험하기」 차트 목록 참고) ──────────
# 분석 조건 설정의 차트 유형 버튼 → 커서를 올리면 그 차트 설명(그림 · 설명 · 용도)이 뜨고, 오른쪽 아래 버튼으로 그 차트 모양의 CSV 를 내려받는다
_CB, _CT, _CP, _CG, _CY, _CO, _CA = "#3b6ff5", "#00cdb4", "#ff3b84", "#dfe4ec", "#f8d53a", "#ff8a2a", "#9aa5b8"
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
              "행 = 국가 · X = 수입액 · Y = 수출액 · 크기 = 거래건수"),
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
.st-key-qs_ct_grid button [data-testid="stIconMaterial"]{font-size:22px;width:22px;height:22px;color:inherit !important}
.st-key-qs_ct_grid button [data-testid="stMarkdownContainer"]{text-align:center}
.st-key-qs_ct_grid button p{font-size:12.5px;line-height:1.2;white-space:nowrap;color:inherit}
.st-key-qs_ct_grid button:hover{border-color:var(--accent);color:var(--accent) !important}
.st-key-qs_ct_grid button[data-testid="stBaseButton-primary"]{background:rgba(43,110,246,.08);border:1.5px solid var(--accent);color:var(--accent) !important}
.st-key-qs_ct_grid button[data-testid="stBaseButton-primary"] p{font-weight:700}
/* 커서를 올린 버튼의 설명 칸 — 버튼 묶음 바로 위로 떠서 조건 칸을 덮는다. 커서를 받지 않아 깜빡이지 않는다 */
.st-key-qs_ct_grid [data-testid="stLayoutWrapper"]:has(> div[class*="st-key-qs_pop_"]){position:absolute;inset:0;pointer-events:none}
.st-key-qs_ct_grid div[class*="st-key-qs_pop_"]{position:absolute;left:0;bottom:calc(100% + 10px);width:100% !important;
  max-width:none !important;z-index:60;pointer-events:none;opacity:0;visibility:hidden;transform:translateY(6px);
  transition:opacity .16s,transform .16s,visibility .16s}
.st-key-qs_ct_grid [data-testid="stColumn"]:has(button:hover) div[class*="st-key-qs_pop_"]{opacity:1;visibility:visible;transform:none}
.csv-pop{background:#fff;border:1px solid #c9d3e6;border-radius:14px;padding:14px 18px 18px;box-shadow:0 14px 36px rgba(20,40,80,.22)}
.csv-h{font-size:19px;font-weight:800;color:#e8574a}
.csv-crumb{font-size:12px;color:#4b515d}.csv-crumb b{color:#1d2a44}
.csv-top{display:grid;grid-template-columns:150px 1fr;gap:14px}
.csv-fig{border:1.5px solid #6b7280;border-radius:12px;background:#fff;display:flex;align-items:center;justify-content:center;min-height:150px}
.csv-desc{background:#f2f2f3;border-radius:12px;padding:16px 20px;font-size:13px;color:#30343c;line-height:1.65}
.csv-desc hr{border:0;border-top:1px solid #c8cbd2;margin:12px 0}
.csv-desc h5{font-size:15px;font-weight:800;margin:0 0 6px;color:#1d2330}
.csv-desc .shape{display:inline-block;margin-top:10px;padding:3px 12px;border-radius:14px;background:#fff;border:1px solid #d6dbe6;
  font-weight:700;color:#3d4a6b;font-size:12px}
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
            out.insert(1, "국가코드(ISO)", [WORLD.get(n, [""])[0] for n in s.index])
            out.insert(2, "위도", [WORLD.get(n, ["", None])[1] for n in s.index])
            out.insert(3, "경도", [WORLD.get(n, ["", None, None])[2] for n in s.index])
        else:
            out["비중(%)"] = (s / s.sum() * 100).round(1).values
        note = f"값 = {col(vm)}" + (" · 무역수지는 음수가 있어 대신 씁니다" if vm != pm else "")
    elif chart == "버블 차트":
        out = by_c[["수입액", "수출액", "거래건수"]].reset_index().rename(
            columns={"수입액": "X_수입액(백만 USD)", "수출액": "Y_수출액(백만 USD)", "거래건수": "크기_거래건수(건)"})
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
    if 2026 in set(df["연도"]) and chart not in ("피라미드 그래프", "막대 그래프"):
        note += " · 2026년은 1~8월 부분연도"
    return out.round(1), note


def csv_preview(chart: str, out: pd.DataFrame) -> go.Figure:
    """CSV 모양(out) 만 가지고 그 차트를 그린다 — 조회 결과 차트와 내려받는 CSV 가 같은 표에서 나온다."""
    fig = go.Figure()
    first = out.columns[0]
    pal = lambda i: Q_PALETTE[i % len(Q_PALETTE)]
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
        fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], gridcolor="#e2e8f2", tickfont=dict(size=9)),
                                     angularaxis=dict(gridcolor="#e2e8f2")))
    elif chart == "히트맵 차트":
        fig.add_trace(go.Heatmap(z=out.iloc[:, 1:].values, x=list(out.columns[1:]), y=out[first],
                                 colorscale=[[0, "#fff6cf"], [.5, _CO], [1, "#e6334d"]], xgap=2, ygap=2))
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
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.14, font=dict(size=10)))
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
/* 슬레이트 머리 · 베이지 줄무늬 · 국가 열 고정 · 가로/세로 스크롤 */
.st-tbl{border-collapse:collapse;font-size:12.5px;min-width:100%}
.st-scroll{max-height:405px;overflow:auto;border:1px solid #d9d2bb;border-radius:6px;background:#fff}
.st-tbl th{position:sticky;top:0;z-index:2;background:#4b6a87;color:#fff;font-weight:700;padding:6px 10px;text-align:center;
  border-right:1px solid #6d88a1;border-bottom:1px solid #6d88a1;white-space:nowrap}
.st-tbl th small{font-weight:500;opacity:.85}
.st-tbl thead tr:nth-child(2) th{top:31px;background:#5d7c98;font-weight:600;font-size:11.5px}
.st-tbl td{padding:6px 10px;border-bottom:1px solid #ece7d6;border-right:1px solid #f1ede0;text-align:right;color:#2f3e4f;white-space:nowrap}
/* 국가 열만 고정 — 머리 둘째 줄의 첫 칸(첫 연도 첫 지표)은 국가 칸이 rowspan 이라 :first-child 에 걸리므로 첫 줄로 한정 */
.st-tbl td:first-child,.st-tbl thead tr:first-child th:first-child{position:sticky;left:0;z-index:1;text-align:left}
.st-tbl thead tr:first-child th:first-child{z-index:3}
.st-tbl td:first-child{background:#fff;font-weight:700}
.st-tbl tr:nth-child(even) td{background:#faf8f0}
.st-tbl td.neg{color:#d64545}
.st-tbl .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px;vertical-align:-1px}
.st-note{font-size:11.5px;color:#6b7a99;margin-top:6px}
</style>"""


def _stat_cell(v: float, m: str) -> str:
    txt = f"{v:,.0f}" if Q_UNIT[m] == "건" else f"{v:,.1f}"          # 건수는 소수점 없이
    return f'<td class="neg">{txt}</td>' if v < 0 else f"<td>{txt}</td>"


def result_csv(df: pd.DataFrame, q: dict) -> bytes:
    """「결과 표」 탭 그대로의 CSV — 행 = 국가, 열 = 연도 × 지표(단위)."""
    names, ms = q["names"], q["metrics"]
    years = sorted(df["연도"].unique())
    piv = df.pivot_table(index="국가", columns="연도", values=ms, aggfunc="sum").reindex(names)
    out = pd.DataFrame({"국가": names})
    for y in years:
        for m in ms:
            out[f"{y}{'(1~8월)' if y == 2026 else ''} {m}({Q_UNIT[m]})"] = [float(piv.loc[n, (m, y)]) for n in names]
    return out.to_csv(index=False).encode("utf-8-sig")


# 차트 · 지도 그림 내려받기 — 탭 칸 안의 차트(plotly 그림 또는 차트 창)를 화면에 보이는 그대로 PNG 로 찍는다.
# 그림을 그리는 쪽 창에 html-to-image(jsDelivr)를 한 번 불러 두고 그 창에서 찍는다. st.html 은 스크립트를 돌리지 않아
# 보이지 않는 components.html 안에서 바깥 화면(window.parent)을 다룬다
IMG_DL_JS = r"""<script>
(function () {
  const P = window.parent, doc = P.document;
  const LIB = "https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js";
  function lib(win) {
    if (win.htmlToImage) return Promise.resolve(win.htmlToImage);
    if (!win.__h2iLoading) win.__h2iLoading = new Promise((ok, bad) => {
      const sc = win.document.createElement('script');
      sc.src = LIB; sc.onload = () => ok(win.htmlToImage); sc.onerror = bad;
      win.document.head.appendChild(sc);
    });
    return win.__h2iLoading;
  }
  function save(url, file) {
    const a = doc.createElement('a'); a.href = url; a.download = file;
    doc.body.appendChild(a); a.click(); a.remove();
  }
  async function shoot(btn) {
    const card = btn.closest('.st-key-card_res'); if (!card) return;
    // 화면에 그려진 탭 칸(지금 고른 탭) — Streamlit 은 고르지 않은 탭 칸을 숨기거나 아예 그리지 않는다
    const panels = [...card.querySelectorAll('[role="tabpanel"]')];
    const panel = panels.find(el => el.offsetHeight > 0) || panels[0]; if (!panel) return;
    let node = panel.querySelector('.js-plotly-plot'), win = P;
    if (!node) {
      const fr = [...panel.querySelectorAll('iframe')].find(f => f.offsetHeight > 20);
      if (!fr) return;
      win = fr.contentWindow; node = fr.contentDocument.body;
    }
    const label = btn.lastChild.textContent;
    btn.disabled = true; btn.lastChild.textContent = '이미지 만드는 중…';
    try {
      const h2i = await lib(win);
      const url = await h2i.toPng(node, {pixelRatio: 2, backgroundColor: '#ffffff', skipFonts: true,
        filter: el => !(el.classList && el.classList.contains('modebar-container'))});
      save(url, btn.dataset.file);
    } catch (e) { console.error('[img-dl]', e); }
    btn.disabled = false; btn.lastChild.textContent = label;
  }
  if (P.__imgDl) doc.removeEventListener('click', P.__imgDl, true);
  P.__imgDl = e => {
    const b = e.target.closest && e.target.closest('.img-dl');
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    if (!b.disabled) shoot(b);
  };
  doc.addEventListener('click', P.__imgDl, true);
})();
</script>"""


def stat_table(df: pd.DataFrame, q: dict) -> None:
    """분석 조건 그대로 — 고른 국가(행) × 기간 안의 연도(시점) × 고른 지표(항목). 국가 색은 차트와 같다."""
    names, ms = q["names"], q["metrics"]
    years = sorted(df["연도"].unique())
    color = {n: Q_PALETTE[i % len(Q_PALETTE)] for i, n in enumerate(names)}
    piv = df.pivot_table(index="국가", columns="연도", values=ms, aggfunc="sum").reindex(names)
    yl = lambda y: f"{y}<small> (1~8월)</small>" if y == 2026 else str(y)
    head1 = "".join(f'<th colspan="{len(ms)}">{yl(y)}</th>' for y in years)
    head2 = "".join(f"<th>{m}<br><small>{Q_UNIT[m]}</small></th>" for _ in years for m in ms)
    body = "".join(f'<tr><td><span class="dot" style="background:{color[n]}"></span>{n}</td>'
                   + "".join(_stat_cell(float(piv.loc[n, (m, y)]), m) for y in years for m in ms) + "</tr>"
                   for n in names)
    st.html(STAT_CSS + f'<div class="st-scroll"><table class="st-tbl"><thead><tr><th rowspan="2">국가</th>{head1}</tr>'
            f'<tr>{head2}</tr></thead><tbody>{body}</tbody></table></div>'
            f'<div class="st-note">통계표 · 국가 {len(names)}개 × 시점 {len(years)}개({years[0]}~{years[-1]}) × 항목 {len(ms)}개 · '
            f'{q["area"]} · {q["hs"]} · 가로로 넘겨 보세요'
            + (" · 2026년은 1~8월 부분연도" if 2026 in years else "") + "</div>")


@st.fragment
def search_block(dtype: str) -> None:
    """각 대분류의 「상세 조회」 — 분석 조건 설정 · 조회 결과(예전 DATA CENTER 「데이터 시각화」). 데이터 유형은 메뉴마다 고정.
    fragment — 안의 조건 · 차트 유형 · 칩 · 초기화를 바꾸면 이 구역만 다시 돈다(KPI · 다른 차트 · 메뉴는 그대로).
    안에서 st.rerun() 을 부르지 않고, 콜백(_q_*)은 이 구역만 읽는 조회 키(qs_ · qf_ · ql_ · qd_type · q_reset_n)만 바꾼다"""
    for _ in zone("sel", "상세 조회"):
        c_form, c_res = st.columns([1, 1.55], gap="medium")
        with c_form:
            q = query_panel(dtype)
        with c_res.container(border=True, key="card_res"):
            if q["type"] == "군수품 FSG/FSC":
                query_result_fsg(q)
            elif q["type"] == "국산화개발":
                query_result_localized(q)
            else:
                y0, y1 = q["years"]
                n_item = "전체 품목" if q["items_all"] else f"품목 {len(q['items'])}개"
                st.html(f'<div class="h">조회 결과 <span class="sub">{q["area"]} · {q["hs"]} · {n_item} · '
                        f'{len(q["names"])}개국 · {y0}~{y1} · {q["chart"]}</span></div>')
                if not q["names"]:
                    st.info("국가를 하나 이상 고르세요.")
                elif not q["items"]:
                    st.info("품목코드를 하나 이상 고르거나 「전체 품목 선택」을 켜 주세요.")
                elif not q["metrics"]:
                    st.info("지표를 하나 이상 고르세요. 분석영역에 맞는 지표만 목록에 나옵니다.")
                else:
                    query_result(q, y0, y1)


def _q_only_chart(q: dict) -> bool:
    """이번 실행이 차트 종류만 바꾼 것인지 — 차트를 뺀 조건(데이터 유형 포함)이 직전과 같고 차트만 다르면 True.
    직전 조건은 session_state 에 둔다(_q 앞머리 — 데이터 유형 전환 때 지우는 qs_ · qf_ · ql_ 와 겹치지 않는다)."""
    ss = st.session_state
    sig = repr(sorted((k, v) for k, v in q.items() if k != "chart"))
    only = ss.get("_q_prev_sig") == sig and ss.get("_q_prev_chart") != q["chart"]
    ss["_q_prev_sig"], ss["_q_prev_chart"] = sig, q["chart"]
    return only


@contextlib.contextmanager
def _q_loading(slot, on: bool = True, text: str = "조회 결과를 계산하는 중"):
    """on 이면 slot 자리에 지구본을 띄우고 계산한다. 샘플은 즉시 끝나 지구본이 안 보이므로 데모에서만 잠깐 멈춘다
    (실제 앱은 DB 조회 시간만큼). on=False 면 지구본 없이 바로 계산한다."""
    if not on:
        yield
        return
    with globe_loading(text, slot=slot):
        time.sleep(DEMO_WAIT)
        yield


@contextlib.contextmanager
def _q_chart_slot(loading: bool):
    """차트 탭 안 차트 자리. loading(차트 종류만 바꿈)이면 지표 카드 · 탭은 그대로 두고 이 자리에만 지구본을 띄웠다가
    차트로 바꾼다 — 지구본이 요소 하나로 이전 차트 자리를 대신해 옛 차트가 남지 않는다."""
    slot = st.empty()
    with _q_loading(slot, loading, "차트를 그리는 중"):
        pass
    with slot.container():
        yield


def query_result(q: dict, y0: int, y1: int) -> None:
    """조회 결과 카드 안 — 지표 카드 · 차트/지도/표 탭."""
    # 조건을 바꾸면 여기가 다시 계산된다 — 그동안 작은 지구본이 돈다.
    # 샘플 데이터는 즉시 끝나 지구본이 안 보이므로 데모에서만 잠깐 멈춘다(실제 앱은 DB 조회 시간만큼).
    # 지구본 · 결과가 같은 한 자리(st.empty) — 조건을 바꾸면 지구본이 이전 결과 전체를 대신하고, 계산이 끝나면 새 결과로 바뀐다
    only = _q_only_chart(q)                  # 차트 종류만 바꿨으면 지구본은 차트 자리에만(_q_chart_slot)
    body = st.empty()
    with _q_loading(body, not only):
        df = trade_frame(q["names"], y0, y1, q["hs"], None if q["items_all"] else q["items"])
    with body.container():
        tot = df[list(Q_UNIT)].sum()
        icon = {m: ic for m, _, ic, _ in Q_METRICS}
        cards = "".join(
            kpi(m, f"{tot[m]:+,.0f}" if m == "무역수지" else f"{tot[m]:,.0f}", Q_UNIT[m],
                f"{len(q['names'])}개국 · {y0}~{y1} 합계", icon=icon[m]) for m in q["metrics"])
        st.html(f'<div class="kpis q" style="grid-template-columns:repeat({min(len(q["metrics"]), 3)},1fr)">{cards}</div>')

        t_chart, t_map, t_tbl = st.tabs(["📈 차트", "🗺️ 국가별 분포 지도", "📋 결과 표"])
        with t_chart, _q_chart_slot(only):
            query_chart(df, q)
        with t_map:
            by_c = df.groupby("국가")[["수입액", "수출액"]].sum()
            modes = {"수출입": ("imp", "exp"), "수출": ("exp",), "수입": ("imp",)}[q["area"]]
            country_map({n: float(v) for n, v in by_c["수입액"].items() if v > 0},
                        {n: float(v) for n, v in by_c["수출액"].items() if v > 0},
                        modes=modes, height=400, note="선택 국가 기준")
        with t_tbl:
            stat_table(df, q)
            st.html(info_line('오른쪽 아래 버튼으로 이 결과 표를 CSV 로 내려받습니다.'))
        # 내려받기 — 탭마다 다르다(탭 칸 오른쪽 아래, 지금 고른 탭의 단추만 보인다 · CSS).
        #  차트 탭 = 보이는 차트 그림 그대로 PNG · 지도 탭 = 보이는 지도 그림 그대로 PNG(IMG_DL_JS 가 화면을 찍는다) · 결과 표 탭 = CSV
        base = f"조회결과_{q['area']}_{y0}_{y1}"
        with st.container(key="res_dl", horizontal=True, horizontal_alignment="right"):
            with st.container(key="dl_chart", width="content"):
                st.html(f'<button class="img-dl" type="button" data-tab="0" data-file="{base}_{q["chart"].replace(" ", "")}_차트.png">'
                        '<span class="ms">image</span>차트 이미지 내려받기</button>')
            with st.container(key="dl_map", width="content"):
                st.html(f'<button class="img-dl" type="button" data-tab="1" data-file="{base}_국가별분포지도.png">'
                        '<span class="ms">map</span>지도 이미지 내려받기</button>')
            with st.container(key="dl_tbl", width="content"):
                st.download_button("결과 표 CSV 내려받기", result_csv(df, q), f"{base}_결과표_샘플.csv",
                                   "text/csv", icon=":material/download:", type="primary")
        with st.container(key="imgdl_js"):
            components.html(IMG_DL_JS, height=0)


# ── 조회 결과 — 군수품 FSG/FSC · 국산화개발(목업용 샘플 MOCK_FSG_ITEMS · MOCK_LOCALIZED 를 걸러 센다) ──────────
# TODO: DB 연결 시 mock_result_fsg · mock_result_localized 두 함수만 DB 조회로 바꾸면 아래 화면은 그대로 쓴다
QF_AGG = {"품목 건수": ("NSN", "size"), "FSC 수": ("FSC", "nunique"), "적용장비 수": ("적용장비", "nunique"),
          "KDSIS 연결 건수": ("KDSIS 연결", "sum")}
QL_AGG = {"국산화개발 기록 수": ("부품관리번호", "size"), "고유 부품 수": ("부품관리번호", "nunique"),
          "사업 수": ("사업명", "nunique"), "관련 업체 수": ("관련 업체", "nunique")}
_has = lambda col, txt: col.str.contains(txt, case=False, regex=False)   # 부분검색(대소문자 무시)


def mock_result_fsg(q: dict) -> pd.DataFrame:
    """군수품 품목 목록을 조건으로 거른다(목업). 빈 검색칸은 조건에서 뺀다."""
    d = MOCK_FSG_ITEMS
    d = d[d["FSC"].isin(q["fsc"]) & d["군종"].isin(q["branch"]) & d["요구연도"].between(*q["years"])]
    for col, txt in (("품목명", q["name"]), ("기능명", q["func"]), ("NSN", q["nsn"])):
        if txt:
            d = d[_has(d[col], txt)]
    if q["kind"] != "전체":
        d = d[d["품목종류"] == q["kind"]]
    return d


def mock_result_localized(q: dict) -> pd.DataFrame:
    """국산화개발 기록을 조건으로 거른다(목업)."""
    d = MOCK_LOCALIZED
    d = d[d["사업명"].isin(q["proj"]) & d["FSC"].isin(q["fsc"]) & d["관련 업체"].isin(q["comp"])]
    for col, txt in (("품목명", q["name"]), ("부품관리번호", q["part"]), ("NSN", q["nsn"])):
        if txt:
            d = d[_has(d[col], txt)]
    return d


def _cat_label(col: str, v: str) -> str:
    return f"FSG {v} {MOCK_FSG[v]}" if col == "FSG" else f"{v} {MOCK_FSC_NAME[v]}"


def cat_table(df: pd.DataFrame, note: str = "", colors: dict | None = None, fmt: dict | None = None) -> None:
    """결과 표(목록형) — HS 결과 표와 같은 통계표 모양(STAT_CSS). 글자 열은 왼쪽, 숫자 열은 오른쪽 정렬.
    HTML 표라 앱 테마(다크 모드)와 상관없이 늘 흰 표로 보인다 — st.dataframe 은 캔버스라 CSS 가 닿지 않아 다크에서 검게 그려진다.
    fmt = {열: 값 → 칸 안 HTML} — 그 열만 따로 그린다(예: 점유율 막대)."""
    flag = {c for c in df.columns if df[c].dtype == bool}
    num = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in flag}

    def cell(c, v, first):
        dot = f'<span class="dot" style="background:{colors[v]}"></span>' if first and colors and v in colors else ""
        if fmt and c in fmt:
            return f"<td>{fmt[c](v)}</td>"
        if c in num:
            return f"<td>{v:,.0f}</td>"
        v = ("연결" if v else "—") if c in flag else escape(str(v))
        return f'<td style="text-align:left">{dot}{v}</td>'
    head = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(cell(c, r[c], i == 0) for i, c in enumerate(df.columns)) + "</tr>"
                   for _, r in df.iterrows())
    st.html(STAT_CSS + f'<div class="st-scroll"><table class="st-tbl"><thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>' + (f'<div class="st-note">{note}</div>' if note else ""))


def _share_bar(v: float) -> str:
    """점유율(%) 칸 — 막대 + 숫자(예전 st.dataframe ProgressColumn 모양)."""
    return (f'<div style="display:flex;align-items:center;gap:8px;min-width:150px">'
            f'<span style="flex:1;height:8px;border-radius:4px;background:#eef2f9;overflow:hidden">'
            f'<i style="display:block;height:100%;width:{v:.1f}%;background:{ACCENT}"></i></span>{v:.1f}%</div>')


def cat_chart(by: pd.DataFrame, q: dict, units: dict, yearly: pd.DataFrame | None = None) -> None:
    """분류(FSG · FSC)별 차트 — by: 행 = 분류 이름, 열 = 지표. 막대 · 트리맵 · 누적 막대 · 꺾은선은 HS 의 csv_preview 를,
    도넛은 hover_donut 을 그대로 쓴다. yearly = 요구연도 × 분류 표(누적 막대 · 꺾은선용)."""
    chart, ms = q["chart"], q["metrics"]
    pm = ms[0]
    color = {n: Q_PALETTE[i % len(Q_PALETTE)] for i, n in enumerate(by.index)}
    note = f"값 = {pm}({units[pm]})"
    if chart == "도넛 그래프":
        rows = sorted(((n, float(v), color[n]) for n, v in by[pm].items()), key=lambda r: -r[1])
        rows = rows[:7] + ([("기타", sum(r[1] for r in rows[7:]), ETC)] if len(rows) > 7 else [])
        hover_donut(rows, f"{sum(r[1] for r in rows):,.0f}", f"{pm} 합계 · {units[pm]}", value_unit=units[pm], height=420)
    else:
        if chart == "막대 그래프":
            out = by[ms].rename(columns=lambda m: f"{m}({units[m]})").rename_axis("분류").reset_index()
            note = "값 = 조건에 맞는 건수 · 개수" + (" · 지표마다 단위가 달라 크기만 비교" if len(ms) > 1 else "")
        elif chart == "트리맵 차트":
            s = by[pm]
            out = pd.DataFrame({"분류": s.index, f"{pm}({units[pm]})": s.values, "비중(%)": (s / s.sum() * 100).round(1).values})
        else:                                   # 누적 막대 · 꺾은선 — 요구연도 흐름
            out = (yearly.assign(합계=yearly.sum(axis=1)) if chart == "누적 막대 그래프" else yearly).reset_index()
            note += " · 요구연도별"
        fig = csv_preview(chart, out)
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch", theme=None)
    st.html(info_line(f"그래프 기준: {note}. 목업용 샘플 값이며 실제 DB 집계가 아닙니다."))


def _cat_kpis(tot: dict, ms: list[str], units: dict, icons: dict, sub: str) -> None:
    cards = "".join(kpi(m, f"{tot[m]:,.0f}", units[m], sub, icon=icons[m]) for m in ms)
    st.html(f'<div class="kpis q" style="grid-template-columns:repeat({min(len(ms), 4)},1fr)">{cards}</div>')


def _cat_downloads(base: str, chart: str, tab2: tuple[str, bytes], tab3: tuple[str, bytes]) -> None:
    """내려받기 — HS 결과와 같은 자리 · 같은 방식(차트 탭 = 그림, 둘째 · 셋째 탭 = CSV). 탭별 표시는 dl_* CSS 가 맡는다."""
    with st.container(key="res_dl", horizontal=True, horizontal_alignment="right"):
        with st.container(key="dl_chart", width="content"):
            st.html(f'<button class="img-dl" type="button" data-tab="0" data-file="{base}_{chart.replace(" ", "")}_차트.png">'
                    '<span class="ms">image</span>차트 이미지 내려받기</button>')
        for key, (label, data) in (("dl_map", tab2), ("dl_tbl", tab3)):
            with st.container(key=key, width="content"):
                st.download_button(f"{label} CSV 내려받기", data, f"{base}_{label.replace('·', '')}_샘플.csv",
                                   "text/csv", icon=":material/download:", type="primary")
    with st.container(key="imgdl_js"):
        components.html(IMG_DL_JS, height=0)


def query_result_fsg(q: dict) -> None:
    """군수품 FSG/FSC 조회 결과 — 지표 카드 · [분포 차트] [분류 상세] [결과 표]. 국가 지도는 없다."""
    unit, ms = q["unit"], q["metrics"]
    y0, y1 = q["years"]
    # 집계 기준 — unit 은 사용자가 고른 값이 아니라 FSC 를 골랐는지로 정해진다(query_panel_fsg)
    if unit == "FSC":
        basis = f'FSC {q["fsc"][0]} 기준' if len(q["fsc"]) == 1 else f'FSC {q["fsc"][0]} 등 {len(q["fsc"])}개 기준'
    else:
        basis = f'FSG {len(q["fsg"])}개 기준 · FSC 전체 {len(q["fsc"])}개'
    st.html(f'<div class="h">조회 결과 <span class="sub">군수품 · {basis} · '
            f'{"·".join(q["branch"]) or "군종 없음"} · 요구연도 {y0}~{y1} · {q["chart"]}</span></div>')
    if not q["fsg"]:
        return st.info("FSG 를 하나 이상 고르거나 「전체 FSG 선택」을 켜 주세요.")
    if not q["branch"]:
        return st.info("군종을 하나 이상 고르세요.")
    if not ms:
        return st.info("지표를 하나 이상 고르세요.")
    # 지구본 · 결과가 같은 한 자리(st.empty) — 조건을 바꾸면 지구본이 이전 결과 전체를 대신하고, 계산이 끝나면 새 결과로 바뀐다
    only = _q_only_chart(q)                  # 차트 종류만 바꿨으면 지구본은 차트 자리에만(_q_chart_slot)
    body = st.empty()
    with _q_loading(body, not only):
        d = mock_result_fsg(q)
    with body.container():
        if d.empty:
            return st.info("조건에 맞는 샘플 품목이 없습니다. 품목명 · 상세검색 조건을 줄여 보세요.")
        units, icons = {m: u for m, u, _ in QF_METRICS}, {m: ic for m, _, ic in QF_METRICS}
        tot = {m: float(d.agg({c: f})[c]) for m, (c, f) in QF_AGG.items()}
        _cat_kpis(tot, ms, units, icons, f"요구연도 {y0}~{y1} · 목업 샘플")

        lab = lambda s: s.map(lambda v: _cat_label(unit, v))
        by = d.groupby(unit).agg(**QF_AGG).rename(index=lambda v: _cat_label(unit, v))
        yearly = (d.assign(분류=lab(d[unit])).groupby(["요구연도", "분류"]).agg(v=QF_AGG[ms[0]]).reset_index()
                  .pivot(index="요구연도", columns="분류", values="v").reindex(columns=by.index)
                  .reindex(range(y0, y1 + 1)).fillna(0))
        detail = (d.groupby(["FSG", "FSC"]).agg(**QF_AGG).reset_index()
                  .assign(FSG=lambda x: x["FSG"].map(lambda g: f"{g} {MOCK_FSG[g]}"), FSC명=lambda x: x["FSC"].map(MOCK_FSC_NAME))
                  [["FSG", "FSC", "FSC명", *QF_AGG]])
        items = d.assign(FSC=d["FSC"].map(lambda c: f"{c} {MOCK_FSC_NAME[c]}"))[
            ["NSN", "품목명", "FSC", "기능명", "품목종류", "군종", "요구연도", "적용장비", "KDSIS 연결"]].sort_values(["FSC", "NSN"])

        t_chart, t_det, t_tbl = st.tabs(["📈 분포 차트", "🗂️ 분류 상세", "📋 결과 표"])
        with t_chart, _q_chart_slot(only):
            cat_chart(by, q, units, yearly)
        with t_det:
            cat_table(detail, f"분류 상세 · FSG {detail['FSG'].nunique()}개 → FSC {len(detail)}개 · 목업용 샘플")
        with t_tbl:
            cat_table(items, f"결과 표 · 품목 {len(items)}건 · NSN 은 가짜 번호(목업용 샘플)")
        _cat_downloads(f"조회결과_군수품_{unit}_{y0}_{y1}", q["chart"],
                       ("분류 상세", detail.to_csv(index=False).encode("utf-8-sig")),
                       ("결과 표", items.to_csv(index=False).encode("utf-8-sig")))


def query_result_localized(q: dict) -> None:
    """국산화개발 조회 결과 — 지표 카드 · [분포 차트] [사업·업체] [품목 상세]. 비율 · 추세 지표는 두지 않는다(스냅샷)."""
    ms = q["metrics"]
    st.html(f'<div class="h">조회 결과 <span class="sub">국산화개발 · 사업 {len(q["proj"])}개 · FSG {len(q["fsg"])}개 · '
            f'FSC {len(q["fsc"])}개 · 관련 업체 {len(q["comp"])}개 · {q["chart"]}</span></div>')
    for ok, msg in ((q["proj"], "사업명을 하나 이상 고르거나 「전체 사업 선택」을 켜 주세요."),
                    (q["fsg"], "FSG 를 하나 이상 고르거나 「전체 FSG 선택」을 켜 주세요."),
                    (q["comp"], "관련 업체를 하나 이상 고르거나 「전체 관련 업체 선택」을 켜 주세요."),
                    (ms, "지표를 하나 이상 고르세요.")):
        if not ok:
            return st.info(msg)
    # 지구본 · 결과가 같은 한 자리(st.empty) — 조건을 바꾸면 지구본이 이전 결과 전체를 대신하고, 계산이 끝나면 새 결과로 바뀐다
    only = _q_only_chart(q)                  # 차트 종류만 바꿨으면 지구본은 차트 자리에만(_q_chart_slot)
    body = st.empty()
    with _q_loading(body, not only):
        d = mock_result_localized(q)
    with body.container():
        if d.empty:
            return st.info("조건에 맞는 샘플 기록이 없습니다. 품목명 · 상세검색 조건을 줄여 보세요.")
        units, icons = {m: u for m, u, _ in QL_METRICS}, {m: ic for m, _, ic in QL_METRICS}
        tot = {m: float(d.agg({c: f})[c]) for m, (c, f) in QL_AGG.items()}
        _cat_kpis(tot, ms, units, icons, "스냅샷 · 국산화율 아님 · 목업 샘플")

        by = d.groupby("FSC").agg(**QL_AGG).rename(index=lambda v: _cat_label("FSC", v))
        pc = pd.crosstab(d["사업명"], d["관련 업체"])
        pc = pc.assign(합계=pc.sum(axis=1)).reset_index().rename(columns={"사업명": "사업명 \\ 관련 업체"})
        items = d.assign(FSC=d["FSC"].map(lambda c: f"{c} {MOCK_FSC_NAME[c]}"))[
            ["부품관리번호", "NSN", "품목명", "FSC", "사업명", "관련 업체"]].sort_values(["부품관리번호", "사업명"])

        t_chart, t_pc, t_tbl = st.tabs(["📈 분포 차트", "🏭 사업·업체", "📋 품목 상세"])
        with t_chart, _q_chart_slot(only):
            cat_chart(by, q, units)
        with t_pc:
            cat_table(pc, "사업 × 관련 업체 · 칸 = 국산화개발 기록 수(건) · 목업용 샘플(업체명은 가상)")
        with t_tbl:
            cat_table(items, f"품목 상세 · 기록 {len(items)}건 · 부품관리번호 · NSN 은 가짜 번호(목업용 샘플)")
        _cat_downloads("조회결과_국산화개발", q["chart"],
                       ("사업·업체", pc.to_csv(index=False).encode("utf-8-sig")),
                       ("품목 상세", items.to_csv(index=False).encode("utf-8-sig")))


# ════════════════════════════════════════════════════════════════════════════
# 대분류 4개 · 소분류 화면 — 한 소분류 = 한 화면. 왼쪽 메뉴에서 소분류를 고르면(?sec=) 그 화면의 블록만 그린다.
# 블록 코드는 예전 7개 페이지(종합 현황 · 수출입 현황 · 부품→무기체계 · 국내 조달 · 품목군 현황표 · 정책·산업 배경 ·
# DATA CENTER)에서 그대로 옮겼다. 옮긴 곳은 참고 자료 11~14 md §3 표를 따른다.
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


# ── ① 부품 현황 ──────────────────────────────────────────────────────────


# 품목군 자세히 보기 표의 배지 — 묶음(SYSTEM_FAMILY) · 선정 근거(HS_BASIS evidence → 화면 이름).
# R4(B2-FSC)는 HS↔FSC 연결 흔적이라 어디에도 표시하지 않는다. 전략물자(R3)는 진입 근거가 아니라 참고 배지(점선)로만
_BASIS_BADGE = {"HSK-군용": ("군용 전용 세분류", "main"), "HSK-항공/항행": ("전문 용도 명시", "main"),
                "전략물자-DU": ("전략물자 통제", "ref")}
_BADGE_STYLE = {
    "main": "background:rgba(43,110,246,.1);color:#1f4fbf;border:1px solid rgba(43,110,246,.35)",
    "ref": "background:#fff;color:#6b7a99;border:1px dashed #b7c4da",
    "fam": "background:#eef2f9;color:#3d4a6b;border:1px solid #d6dbe6",
    "warn": "background:#fef3c7;color:#92400e;border:1px solid #fde68a",   # 소재장비 = 전자부품 아님(§7 표현 경계)
}
_NON_ELEC = {"841191", "880730"}                                  # 소재장비 — 전자부품이 아님을 배지에 밝힌다


def _badge(text: str, kind: str) -> str:
    return (f'<span style="display:inline-block;padding:1px 7px;border-radius:5px;font-size:11px;font-weight:600;'
            f'white-space:nowrap;{_BADGE_STYLE[kind]}">{escape(text)}</span>')


def _ro(word: str) -> str:
    """조사 「으로/로」 — 끝 글자에 받침이 있으면(ㄹ 받침 제외) 「으로」. 한글이 아니면 「로」."""
    c = ord(word[-1]) - 0xAC00
    return "으로" if 0 <= c < 11172 and c % 28 not in (0, 8) else "로"


def _items_detail_view() -> pd.DataFrame:
    """품목군 자세히 보기 표 — HS6 | 품목군(+묶음 배지) | 품목 설명 | 선정 근거 | 1위 공급국 | 1위 점유율 | HHI | 수입국 수.
    칸은 HTML 로 만들어 cat_table(fmt) 에 그대로 넘긴다. items_df 자체는 건드리지 않는다."""
    ev = {c: e for c, _, _, e in HS_BASIS}
    fam = lambda hs: (_badge("소재장비 · 전자부품 아님", "warn") if hs in _NON_ELEC else _badge(SYSTEM_FAMILY[hs], "fam"))
    df = items_df.copy()
    df["품목군"] = [f'<div style="text-align:left;white-space:nowrap">{escape(n)} {fam(hs)}</div>'
                  for hs, n in zip(df["HS6"], df["품목군"])]
    # 한 줄 말줄임 · 커서를 올리면(title) 전체 문장
    df.insert(2, "품목 설명", [
        f'<div title="{escape(DEFENSE_USE_KO[hs], quote=True)}" style="max-width:260px;overflow:hidden;'
        f'text-overflow:ellipsis;white-space:nowrap;text-align:left">{escape(DEFENSE_USE_KO[hs])}</div>' for hs in df["HS6"]])
    df.insert(3, "선정 근거", [
        '<div style="display:flex;gap:4px;flex-wrap:wrap">'
        + "".join(_badge(*_BASIS_BADGE[t]) for t in ev[hs].split(";") if t in _BASIS_BADGE) + "</div>"
        for hs in df["HS6"]])
    return df


# 품목군 자세히 보기 표만 머리 줄을 진한 파랑으로 — cat_table 공통 CSS(.st-tbl th)는 두고 이 칸(items_detail) 안에서만 덮는다
_ITEMS_DETAIL_CSS = """<style>
.st-key-items_detail .st-tbl th{background:#0b2a6b;border-right-color:#24457f;border-bottom-color:#24457f}
</style>"""


def _parts_summary() -> None:
    for _ in zone("kpi", "한눈에 보는 KPI"):
        n_top50 = int((items_df["1위 점유율(%)"] >= 50).sum())
        n_hhi = int((items_df["HHI"] >= 2500).sum())
        ask(f"{len(items_df)}개 품목군을 한눈에 보면 어떤가",
            f"{len(items_df)}개 중 {n_top50}개는 수입액의 절반 이상을 한 나라에서 들여온다(2025년 · 민수 포함).")
        st.html('<div class="kpis home k4 parts-kpi-row">'
                + kpi("분석 대상 품목군", "13", "개",
                      "HS6 후보 1,003개 중 기준 충족 52개 → 전자 계열 13개 · 관세청 수집 24개 중", icon="inventory_2")
                + kpi("2025 수입액", "478.2", "억 달러",
                      "분석 대상 13개 합계 · 국가 전체 수입 · 민수 포함 · 수출은 606.6억 달러", icon="payments")
                + kpi("특정국 50% 이상 품목군", f"{n_top50}", "개",
                      f"1위 공급국 점유율 기준 · 13개 중 · 2025년 합계 · HHI 2,500 이상은 {n_hhi}개", icon="warning")
                + kpi("HHI 2,500 이상", f"{n_hhi}", "개",
                      f"공급국 집중도(HHI) 기준 · {len(items_df)}개 중 · 2025년 합계", icon="stacked_bar_chart")
                + "</div>")

    for _ in zone("itemtbl", "품목군 현황표"):
        # 품목군마다 한 줄 — HHI 가 큰 순. 점유율 칸은 막대(_share_bar)
        cat_table(items_df.sort_values("HHI", ascending=False)[["HS6", "품목군", "1위 공급국", "1위 점유율(%)", "HHI", "수입국 수"]],
                  fmt={"1위 점유율(%)": _share_bar, "수입국 수": lambda v: f"{v}개"},
                  note="HHI 가 큰 순 · 2025년 합계 · HHI = Σ(국가 점유율 %)², 0~10,000 · 2,500 이상 = 높은 집중")

    for _ in zone("hsbasis", "HS 분류기준"):
        ask("왜 이 13개를 분석 대상으로 삼았나",
            "HS 6단위 1,003개 가운데 군용 전용이거나 전문 용도가 이름에 적힌 52개를 추리고, 그중 전자 계열 13개만 남겼다.")
        # 왼쪽 = 분석 대상 선정 깔때기(1,003 → 52 → 13) · 오른쪽 = 분석 대상 13개의 선정 근거 매트릭스(R4 열 없음)
        c1, c2 = st.columns(2, gap="medium")
        c1.html(funnel_card("분석 대상 선정", "단위: HS 6단위 개수 · % = 모집단 대비", HS_SELECT,
                            "전략물자 통제 목록은 1,003개 중 275개가 해당돼 기준으로 쓰지 않았고, 국산화 군수품 대응은 "
                            "공식 대조표가 없어 뺐습니다. 관세청 수집은 24개 = 분석 대상 13 + 배경 자료 11."))
        rows = [r for r in HS_BASIS if r[0] in TARGET_HS]
        tags = [t for t in BASIS_TAGS if t[0] != "B2-FSC"]
        c2.html(f'<div class="card"><div class="h">품목군 선정 근거 <span class="sub">분석 대상 {len(rows)}개 · '
                f'진입 = R1 또는 R2(2026-09-21 확정) · 점 = 해당 근거 · 열 제목에 커서를 올리면 뜻</span></div>'
                f'{basis_matrix(rows, card=False, tag_cols=tags)}</div>')

    for _ in zone("tree", "품목군별 수입 집중도"):
        c1, c2 = st.columns(2, gap="medium")
        with c1.container(border=True, key="card_tree"):
            # 제목 = 결론 문장 — HHI 가 가장 높은 · 낮은 품목군을 items_df 에서 찾아 넣는다
            hi, lo = items_df.loc[items_df["HHI"].idxmax(), "품목군"], items_df.loc[items_df["HHI"].idxmin(), "품목군"]
            st.html(f'<div class="h">기간 합계 HHI는 {hi}{_ro(hi)} 가장 높고 {lo}{_ro(lo)} 가장 낮다 '
                    '<span class="sub">칸 크기 = HHI(0~10,000, 클수록 수입이 소수 국가에 몰림) · 색 = 1위 공급국 점유율</span></div>')
            fig = go.Figure(go.Treemap(
                labels=items_df["품목군"], parents=[""] * len(items_df), values=items_df["HHI"],
                marker=dict(colors=items_df["1위 점유율(%)"], colorscale=[[0, "#dbeafe"], [1, ACCENT]],
                            line=dict(color="#fff", width=2)),
                texttemplate="%{label}<br>%{customdata:.1f}%", customdata=items_df["1위 점유율(%)"],
                hovertemplate="%{label}<br>HHI %{value:,}<br>1위 점유율 %{customdata:.1f}%<extra></extra>"))
            fig.update_layout(height=380)
            st.plotly_chart(style_fig(fig), width="stretch", theme=None)
        with c2.container(border=True, key="card_cnt"):
            st.html('<div class="h">품목군별 수입국 수 <span class="sub">많을수록 공급처가 분산</span></div>')
            fig = go.Figure(go.Bar(x=items_df["품목군"], y=items_df["수입국 수"],
                                   marker=dict(color=items_df["수입국 수"], colorscale=[[0, "#c7ddfb"], [1, ACCENT]],
                                               line=dict(color="#fff", width=1)),
                                   hovertemplate="%{x}<br>%{y}개국<extra></extra>"))
            fig.update_layout(height=380)
            fig.update_xaxes(tickangle=-40)
            st.plotly_chart(style_fig(fig), width="stretch", theme=None)

    # 품목군 자세히 보기 — 8칸 상세 표만(기본 접힘). 분석 대상 선정 · 선정 근거는 위 HS 분류기준으로 옮겼고,
    # 옛 부품별 현황 표(supply_table)는 같은 정보를 겹쳐 보여 뺐다
    with st.expander("품목군 자세히 보기", expanded=False, icon=":material/table_view:"):
        with st.container(key="items_detail"):
            st.html(_ITEMS_DETAIL_CSS)
            html = lambda v: v                                     # 이미 HTML 로 만든 칸(_items_detail_view)은 그대로
            cat_table(_items_detail_view(),
                      fmt={"품목군": html, "품목 설명": html, "선정 근거": html,
                           "1위 점유율(%)": _share_bar, "수입국 수": lambda v: f"{v}개"},
                      note="선정 기준: 관세청 HSK 세분류에서 군용 전용 또는 항공·항행·레이더 등 전문 용도가 확인된 품목을 기준으로 "
                           "선정(전략물자 통제 목록은 참고)<br>"
                           "출처: 관세청 HS부호 마스터 · 품목별 국가별 수출입실적 · 2016.01~2026.08")
    caution("금액은 국가 전체 수입(민수 포함)이다 — 군 수요만 떼어 낸 값이 아니다",
            "HHI 와 1위 공급국 점유율은 수입이 몇 나라에 몰렸는지를 보여 줄 뿐, 위험도나 의존도를 뜻하지 않는다")


def _parts_trade() -> None:
    with globe_loading("수입 집계를 읽는 중"):
        time.sleep(DEMO_WAIT)
    for _ in zone("kpi2", "핵심 지표"):
        # 1위 수입국 · 수출국 — TRADE_IMP · TRADE_EXP(2016~2025 합산, 백만 USD)에서 값이 가장 큰 나라와 그 비중
        top_i, top_e = max(TRADE_IMP, key=TRADE_IMP.get), max(TRADE_EXP, key=TRADE_EXP.get)
        sh_i = TRADE_IMP[top_i] / sum(TRADE_IMP.values()) * 100
        sh_e = TRADE_EXP[top_e] / sum(TRADE_EXP.values()) * 100
        top2 = sorted(TRADE_IMP, key=TRADE_IMP.get, reverse=True)[:2]
        sh2 = sum(TRADE_IMP[c] for c in top2) / sum(TRADE_IMP.values()) * 100
        ask("어느 나라에서 얼마나 들여오고 내보내나",
            f"수입의 {sh2:.0f}%는 {top2[0]} · {top2[1]} 두 나라에서 들어온다(2016~2025 합산). "
            "2025년에는 수출(606.6억 달러)이 수입(478.2억 달러)보다 많았다.")
        st.html('<div class="kpis k4 parts-kpi-row">'                  # 한눈에 보는 KPI 처럼 1줄 4칸(860px 이하 2 × 2)
                + kpi("2025 수입액", "478.2", "억 달러", "13개 합계 · 국가 전체 수입 · 민수 포함", icon="payments")
                + kpi("2025 수출액", "606.6", "억 달러", "13개 합계 · 국가 전체 수출 · 민수 포함", icon="upload")
                + kpi("1위 수입국", top_i, "", f"수입 비중 {sh_i:.1f}% · 2016~2025 합산 · {TRADE_IMP[top_i]:,.0f} 백만 USD",
                      icon="download")
                + kpi("1위 수출국", top_e, "", f"수출 비중 {sh_e:.1f}% · 2016~2025 합산 · {TRADE_EXP[top_e]:,.0f} 백만 USD",
                      icon="flight_takeoff")
                + "</div>")

    flow = _flow_switch("trade_flow")
    imp = flow == "수입"
    # 9. 지구본 · 연도별 추이 · 비중 도넛을 한 구역으로 — 바깥 2열, 왼쪽 열 = 지구본 하나, 오른쪽 열 = 추이 카드 + 비중 카드를
    #    위아래로(행 합치기 대신 열 안에서 차례로 그린다). 지구본 높이 ≈ 오른쪽 두 카드 합(차트 225 + 도넛 칸 300 + 카드 머리 · 여백 · 간격)
    for _ in zone("trend", f"국가별 {flow} 규모 · 연도별 추이"):
        c_map, c_side = st.columns([1.15, 1], gap="medium")
        with c_map.container(border=True, key="card_map"):
            way = "대한민국으로 들어오는" if imp else "대한민국에서 나가는"
            st.html(f'<div class="h">국가별 {flow} 규모'
                    + info_btn(f"지구본 · 지도 버튼으로 전환합니다<br>원 크기 = {flow}액 · 화살표 = {way} 방향<br>"
                               "원 위에 커서를 올리면 상세" + ("" if imp else "<br>수출은 샘플 값(상위 7개국)")) + '</div>')
            supply_globe(GLOBE_PTS if imp else GLOBE_PTS_EXP, height=605, unit="백만 USD", outbound=not imp)
        with c_side:
            with st.container(border=True, key="card_trend"):
                st.html(f'<div class="h">연도별 {flow} 추이 <span class="sub">분석 대상 13개 합계 · 완결연도 2016~2025 · '
                        '단위: 백만 USD · 민수 포함</span></div>')
                color = SERIES[0] if imp else SERIES[1]
                fig = go.Figure(go.Scatter(x=IMPORT_TREND["연도"], y=IMPORT_TREND[flow], name=flow,
                                           mode="lines+markers", line=dict(color=color, width=2.5),
                                           marker=dict(size=7, color="#fff", line=dict(color=color, width=2))))
                fig.update_layout(showlegend=False)
                st.plotly_chart(style_fig(fig, 225), width="stretch", theme=None)     # 300 → 225(약 25% 줄임)
            with st.container(border=True, key="card_share"):
                st.html(f'<div class="h">{"공급국" if imp else "수출 상대국"} 비중 '
                        '<span class="sub">조각에 커서를 올려 보세요 · 2016~2025 합산 · 단위: 백만 USD'
                        + ("" if imp else " · 수출은 샘플 값") + '</span></div>')
                rows = [(c[0], c[3], c[4]) for c in COUNTRIES] if imp else [(n, v, c) for n, _, _, v, c in EXPORT_TOP]
                hover_donut(rows, f"{sum(r[1] for r in rows):,.0f}", "백만 USD", value_unit="백만 USD",
                            height=300, size=270, top=True)   # 도넛 360 → 270(약 25% 줄임) · 제목 바로 아래부터(위 여백 자름)
        caution("군수 수요 비중이 아니라 국가 전체 교역 규모(민수 포함)다 — 「방산 수입 · 수출」로 읽지 않는다",
                "수출 쪽 나라별 값은 샘플 값(상위 7개국)이다")


def _flow_switch(key: str) -> str:
    """「수입 | 수출」 전환 — 같은 자리의 차트가 이 값에 따라 바뀐다. 기본은 수입."""
    return st.segmented_control("수입 · 수출", ["수입", "수출"], default="수입", key=key, required=True,
                                label_visibility="collapsed")


def _no_export(what: str) -> None:
    """수출 쪽 데이터가 없는 자리 — 임의 값으로 채우지 않고 그렇다고 적는다."""
    st.info(f"{what}은(는) 수입 기준 데이터만 있습니다. 품목군별 수출 상대국 데이터가 없어 수출 화면은 만들지 않았습니다.",
            icon=":material/info:")


def _parts_conc() -> None:
    flow = _flow_switch("conc_flow")
    imp = flow == "수입"
    for _ in zone("conc", "공급국 집중도"):
        n_hhi = int((items_df["HHI"] >= 2500).sum())
        ask("수입은 몇 나라에 몰려 있나",
            f"{len(items_df)}개 품목군 중 {n_hhi}개는 HHI 2,500 이상 — 수입이 소수 국가에 몰려 있다(2025년 합계).")
        c1, c2 = st.columns([1, 1.25], gap="medium")
        if imp:
            c1.html(rank_card("주요 수입국 TOP 7", "괄호 안은 전체 대비 비중",
                              [(c[0], c[3], c[4]) for c in COUNTRIES], "백만 USD"))
        else:
            c1.html(rank_card("주요 수출국 TOP 7", "2016~2025 합산 · 수출은 샘플 값",
                              [(n, v, c) for n, _, _, v, c in EXPORT_TOP], "백만 USD"))
        with c2.container(border=True, key="card_hhi"):
            st.html(f'<div class="h">품목군별 집중도(HHI) <span class="sub">2,500 이상 = 높은 집중 · {flow} 기준</span></div>')
            if not imp:
                _no_export("품목군별 집중도(HHI) · 1위 공급국 점유율")
            else:
                fig = go.Figure(go.Scatter(
                    x=items_df["1위 점유율(%)"], y=items_df["HHI"], mode="markers+text",
                    text=items_df["품목군"], textposition="top center", textfont=dict(size=10, color=MUTED),
                    marker=dict(size=14, color=[dict((c[0], c[4]) for c in COUNTRIES).get(n, ETC)
                                                for n in items_df["1위 공급국"]],
                                line=dict(color="#fff", width=1.5)),
                    hovertemplate="%{text}<br>1위 점유율 %{x:.1f}%<br>HHI %{y:,}<extra></extra>"))
                fig.add_hline(y=2500, line=dict(color="#94a7c8", dash="dash", width=1),
                              annotation_text="HHI 2,500", annotation_font=dict(color=MUTED, size=11))
                fig.update_xaxes(title="1위 공급국 점유율(%)")
                fig.update_yaxes(title="HHI")
                st.plotly_chart(style_fig(fig, 360), width="stretch", theme=None)

    for _ in zone("focus", "품목군별 공급 집중도"):
        if not imp:
            _no_export("품목군별 공급 국가 비중")
            continue
        st.html('<div class="note" style="margin-bottom:4px">탭을 누르면 품목군이 바뀝니다 — 품목군별 공급 국가 비중입니다.</div>')
        for tab, f in zip(st.tabs([f["name"] for f in FOCUS]), FOCUS):
            with tab:
                st.html(share_card(f))

    for _ in zone("hhiyear", "연도별 집중도 변화"):
        if not imp:
            _no_export("품목군 × 연도 집중도(HHI)")
            continue
        names = list(items_df.sort_values("HHI")["품목군"])              # 아래 → 위로 HHI 가 커지게
        always = [n for n in names if min(HHI_YEARLY[n]) >= 2500]
        ask("한 나라에 쏠린 정도는 나아지고 있나",
            f"{len(always)}개 품목군은 {HHI_YEARS[0]}~{HHI_YEARS[-1]}년 내내 HHI 2,500 이상이었다 — 쏠림이 풀리지 않은 품목이다(샘플 값).")
        with st.container(border=True, key="card_hhiyear"):
            st.html('<div class="h">품목군 × 연도 집중도(HHI) <span class="sub">칸 색 = 그해 HHI · 진한 칸이 이어지는 줄 = 늘 쏠린 품목<br>'
                    '연도별 값은 샘플 값(2025년 열만 품목군 현황표와 같음)</span></div>')
            z = [HHI_YEARLY[n] for n in names]
            fig = go.Figure(go.Heatmap(
                z=z, x=[str(y) for y in HHI_YEARS], y=names, zmin=1000, zmax=6000, xgap=3, ygap=3,
                colorscale=[[0, "#eaf2ff"], [0.3, "#bfd6fb"], [1, ACCENT]],   # 0.3 = HHI 2,500 근처에서 색이 짙어지기 시작
                text=[[f"{v:,}" for v in row] for row in z], texttemplate="%{text}", textfont=dict(size=10.5),
                colorbar=dict(title="HHI", thickness=10, len=0.8),
                hovertemplate="%{y} · %{x}년<br>HHI %{z:,}<extra></extra>"))
            fig.update_layout(height=470, margin=dict(l=8, r=8, t=10, b=8))
            fig.update_xaxes(type="category")                             # 연도를 한 칸도 빠짐없이 적는다
            st.plotly_chart(style_fig(fig), width="stretch", theme=None)
        caution("HHI = Σ(국가 점유율 %)², 0~10,000 · 2,500 이상 = 높은 집중. 위험도나 의존도를 뜻하지 않는다",
                "품목군별 집중도는 수입 기준만 있다 — 품목군별 수출 상대국 자료가 없다")


def page_parts() -> None:
    _mk_css()
    _run_sub({"summary": _parts_summary, "trade": _parts_trade,
              "conc": _parts_conc, "detail": lambda: search_block("수출입 HS")})


# ── ② 군급 분류와 조달 ───────────────────────────────────────────────────


_FSG_NAME = {"58": "통신 · 탐지 장비", "59": "전기 · 전자 구성품", "60": "광섬유"}


def _fsc_code() -> None:
    for _ in zone("codeintro", "군급코드란"):
        ask("군은 전자부품을 어떤 분류로 관리하나",
            "군은 무역 통계(HS)와 다른 분류(FSG → FSC → NSN)로 부품을 관리하고, 조달 · 국산화 자료는 모두 이 분류를 쓴다.")
        st.html('<div class="mk-tree">'
                '<div><h4>군(FSG) · 2자리</h4><p>큰 묶음. 전자는 58 통신 · 탐지 장비 · 59 전기 · 전자 구성품 · 60 광섬유</p></div><i>▶</i>'
                '<div><h4>군급(FSC) · 4자리</h4><p>FSG 를 나눈 분류. 예: 5840 레이더 장비 · 5962 전자 집적회로 · 5935 커넥터</p></div><i>▶</i>'
                '<div><h4>재고번호(NSN) · 13자리</h4><p>FSC 4자리 + 품목 식별번호 9자리 — 부품 하나하나의 번호</p></div></div>')
        c1, c2 = st.columns([1.35, 1], gap="medium")
        with c1.container(border=True, key="card_fsctree"):
            st.html('<div class="h">전자 군(FSG) · 군급(FSC) 계층 <span class="sub">안쪽 고리 = 군(FSG) · 바깥 고리 = 군급(FSC)<br>'
                    '대표 군급만 보여 주며 칸 크기는 모두 같다(건수가 아님)</span></div>')
            # 고리 — 가운데(전자 군급) → 군(FSG) → 군급(FSC). 군급 칸은 모두 값 1(계층만 보여 준다)
            ids, labels, parents, colors = ["전자 군급"], ["전자 군급"], [""], ["#ffffff"]
            for i, (g, fs) in enumerate(MOCK_FSC.items()):
                ids.append(f"FSG {g}"); labels.append(f"FSG {g}<br>{_FSG_NAME[g]}"); parents.append("전자 군급"); colors.append(SERIES[i])
                for c, n in fs.items():
                    ids.append(c); labels.append(f"{c}<br>{n}"); parents.append(f"FSG {g}"); colors.append(SERIES[i])
            fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents,
                                        values=[1 if len(i) == 4 else 0 for i in ids],
                                        marker=dict(colors=colors, line=dict(color="#fff", width=2)),
                                        insidetextorientation="radial", textfont=dict(size=11),
                                        hovertemplate="%{label}<extra></extra>"))
            fig.update_layout(height=430, margin=dict(l=4, r=4, t=4, b=4))
            st.plotly_chart(style_fig(fig), width="stretch", theme=None)
        c2.html(rules_card("군급코드 읽는 법", [
            ("앞 2자리 = 군(FSG)", "5962 의 59 — 전기 · 전자 구성품이라는 큰 묶음입니다."),
            ("4자리 = 군급(FSC)", "5962 — 전자 집적회로. 조달계획 · 국산화 자료의 집계 단위입니다."),
            ("13자리 = 재고번호(NSN)", "군급 4자리 뒤에 품목 식별번호 9자리가 붙어 부품 하나를 가리킵니다."),
            ("전자 군급의 범위", "이 대시보드는 군(FSG) 58 · 59 · 60에 속한 군급만 전자 군급으로 봅니다."),
        ]))

    for _ in zone("fscsel", "FSC/FSG 분류 기준 · 결합 원칙"):
        n_src, n_elec = FSC_SELECT[0][1], FSC_SELECT[-1][1]
        ask("전자 군급은 어떻게 추렸고, HS 품목과는 왜 잇지 않나",
            f"국외 조달계획 {n_src:,}행에서 군급 미분류(FSC 9999)를 빼고 전자 군급 {n_elec:,}행을 추렸다. "
            "HS 와 군급 사이에는 공식 대조표가 없어 두 분류를 코드로 잇지 않는다.")
        # 3줄 — 군수품 FSC/FSG 분류 기준 깔때기(QA 확정 값 FSC_SELECT) · HS ↔ FSC/FSG/NSN 결합 원칙
        # 깔때기 안 % 는 funnel_card 가 첫 층(원본 13,615행) 대비로 자동 계산 → 전자·통신 2,267행 ≈ 16.7%.
        # 따로 강조하는 17.42% 는 분석 모집단 13,017행 대비라 분모가 달라, 설명(ⓘ)에 둘 다 적는다
        c1, c2 = st.columns([1.35, 1], gap="medium")
        c1.html(funnel_card("FSC/FSG 분류 기준", "단위: 행 · % = 원본 13,615행 대비", FSC_SELECT,
                            "FSC 9999(기타 품목)는 사실상 군급 미분류로 보고 분석 "
                            "모집단에서 제외합니다. 깔때기 안 %는 원본 13,615행 대비이며, "
                            "전자·통신 비중 17.42%는 분석 모집단 13,017행 대비로 "
                            "분모가 다릅니다(2,267 / 13,017 = 17.42%)."))
        c2.html(rules_card("분류체계 결합 원칙", [
            ("직접 JOIN하지 않음", "HS/HSK ↔ FSC/FSG/NSN 사이 공식 대조표가 없어 코드를 직접 연결하지 않습니다."),
            ("품명 유사도 매핑하지 않음", "품목명 텍스트 유사도로 두 체계를 잇지 않습니다."),
            ("각 분류체계 안에서 독립 분석", "HS 기반 분석과 FSC/FSG 기반 분석은 서로 다른 화면·조건에서 독립적으로 이뤄집니다."),
        ], head='<div class="nomap"><span class="sys">HS/HSK<small>관세·무역 분류</small></span>'
                '<span class="x">✕<small>공식 직접 매핑 없음</small></span>'
                '<span class="sys">FSC/FSG/NSN<small>군수품 분류</small></span></div>',
           tip="NSN은 군수품 식별번호로 사용하며, FSC/FSG와의 계층·식별 기준은 원천 데이터의 코드 구조를 따릅니다."))
        caution("소개 · 전자부품 현황의 HS 13개와 이 군급 분류는 코드로 잇지 않는다 — 같은 전자부품 영역을 두 공식 분류로 나란히 본다",
                "깔때기 안 %는 원본 13,615행 대비, 전자 군급 비중 17.42%는 분석 모집단 13,017행 대비라 분모가 다르다")


def _fsc_plan() -> None:
    for _ in zone("kpi3", "국외 조달계획 현황"):
        (f1, v1, _), (f2, v2, _) = PLAN_BY_FSC[:2]
        ask("군은 전자 군급 중 무엇을 해외에서 사려 하나",
            f"해외 조달계획은 {f1}({v1:,}건) · {f2}({v2:,}건) 군급에 가장 많다.")
        # 2026 국외조달 예산 · 방위력개선비 대비 — BUDGET(연도 ↔ 값)에서 2026 행을 찾아 읽는다(값을 다시 적지 않는다)
        b26 = BUDGET.set_index("연도").loc[2026]
        unit_note = "예산(계획 금액)과 조달계획 건수/적용장비 수는 단위가 다르며 직접 계산된 비율이 아님"
        st.html('<div class="kpis k4">'
                + kpi("국외 조달계획", "13,615", "행", "적용장비 842종 · 건수 기준 · 금액 미사용", icon="folder")
                + kpi("적용장비", "842", "종",
                      "국외 조달계획 13,615행 기준 고유 수 · 육군 7,404 · 해군 5,254 · 공군 717행", icon="public")
                + kpi("2026 국외조달 예산", f"{b26['국외조달 예산(억 원)']:,.0f}", "억 원", unit_note, icon="payments")
                + kpi("방위력개선비 대비", f"{b26['전체 방위력개선비 대비(%)']:.1f}", "%",
                      "2026 국외조달 예산 ÷ 전체 방위력개선비 · " + unit_note, icon="percent")
                + "</div>")

    for _ in zone("fsc", "FSC 상위 품목군"):
        with st.container(border=True, key="card_fsc"):
            st.html('<div class="h">FSC 상위 품목군 <span class="sub">단위: 품목 수</span></div>')
            st.plotly_chart(style_fig(hbar(PLAN_BY_FSC, 300, "건")), width="stretch", theme=None)

    for _ in zone("eq", "적용장비"):
        st.html(rank_card("적용장비 TOP 품목", "국외 조달계획 기준", EQUIPMENT, "품목 수"))
        caution("건수만 있다(금액 없음) — 품목 단위 자료라 계획 금액을 쓰지 않는다",
                "예산(억 원)과 조달계획 건수 · 적용장비 수는 단위가 달라 서로 나누거나 더하지 않는다")


def _fsc_army() -> None:
    for _ in zone("army", "연도별 군별 조달계획"):
        tot = {a: int(ARMY_MIX[a].sum()) for a in ["육군", "해군", "공군", "해병대"]}
        top = max(tot, key=tot.get)
        y0, y1 = int(ARMY_MIX["연도"].iloc[0]), int(ARMY_MIX["연도"].iloc[-1])
        ask("어느 군이 해외 조달을 가장 많이 요구하나",
            f"{y0}~{y1}년 합계로는 {top}이 {tot[top]:,}건으로 가장 많고, 전체의 {tot[top] / sum(tot.values()) * 100:.0f}%를 차지한다.")
        with st.container(border=True, key="card_army"):
            st.html('<div class="h">연도별 군별 조달계획 <span class="sub">단위: 건</span></div>')
            fig = go.Figure()
            for i, army in enumerate(["육군", "해군", "공군", "해병대"]):
                fig.add_trace(go.Bar(x=ARMY_MIX["연도"], y=ARMY_MIX[army], name=army,
                                     marker=dict(color=SERIES[i], line=dict(color="#fff", width=1))))
            fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.14), height=330)
            st.plotly_chart(style_fig(fig), width="stretch", theme=None)


def _fsc_domestic() -> None:
    for _ in zone("dkpi", "국내 조달 핵심 지표"):
        ask("국내에서는 어떤 방법으로 계약하나",
            "국내 계약의 70.2%가 수의계약이다. 다만 대부분 소액 · 소기업 사유라, 이 비중을 곧 진입 장벽으로 읽지 않는다.")
        st.html('<div class="kpis">'
                + kpi("국내 계약", "37,602", "건", "계약 단위(최종 차수) · 정제 행 43,105", icon="description")
                + kpi("수의계약 비중", "70.2", "%", "30,255 / 43,111행 · 국외조달은 20.1%", icon="handshake")
                + kpi("입찰공고", "10,842", "건", "2024 1,274 · 2025 9,566", icon="campaign")
                + kpi("경쟁입찰 유찰률", "24.2", "%", "유찰 1,741 / 공고 키 7,201", icon="block")
                + kpi("낙찰업체", "3,211", "개", "사업자번호 기준 · 계약정보 연결 96.4%", icon="apartment")
                + "</div>")

    for _ in zone("dmethod", "계약 방법"):
        c1, c2 = st.columns([1.4, 1], gap="medium")
        with c1.container(border=True, key="card_dmethod"):
            st.html('<div class="h">계약 체결 방법별 건수 <span class="sub">clean_dapa_contract · 단위: 행</span></div>')
            st.plotly_chart(style_fig(hbar(DOM_METHOD, 300, "행")), width="stretch", theme=None)
        c2.html('<div class="card"><div class="h">수의계약 비중 — 국내 vs 국외 <span class="sub">점선 = 50%<br>'
                '국내 30,255 / 43,111행 · 국외 1,276 / 6,333계약(clean_dapa_overseas_contract).<br>'
                '국내는 소액·소기업 사유가 대부분이라 비중 차이를 곧 진입 장벽으로 읽지 않습니다.</span></div>'
                + pct_rows([("국내조달", 70.2, SERIES[2]), ("국외조달", 20.1, SERIES[0])]) + '</div>')

    for _ in zone("dreason", "수의계약 사유"):
        total_private = sum(v for _, v, _ in DOM_METHOD[:1])
        small = sum(v for _, v in PRIVATE_REASON[:2])
        ask("왜 수의계약이 이렇게 많나",
            f"수의계약 {total_private:,}행 중 {small / total_private * 100:.0f}%가 소액(추정가격 2천만원 이하) · 소기업(1억 이하) 사유다.")
        c1, c2 = st.columns([1.4, 1], gap="medium")
        rows = [(n, v, SERIES[i]) for i, (n, v) in enumerate(PRIVATE_REASON)]
        rows.append(("기타 사유", total_private - sum(v for _, v in PRIVATE_REASON), ETC))
        with c1.container(border=True, key="card_dreason"):
            st.html(f'<div class="h">수의계약 사유 상위 <span class="sub">수의계약 {total_private:,}행 · 단위: 행</span></div>')
            st.plotly_chart(style_fig(hbar(rows, 300, "행")), width="stretch", theme=None)
        c2.html(rules_card("사유를 읽는 법", [
            ("경쟁 실패 후 수의 1,847계약", "재공고·1인 입찰·공고 후 수의 — 조달 지연의 간접 신호(2025년 5.7%)."),
            ("단일공급·호환성·특허 747계약", "공급자가 한정된 경우. 진입 장벽 신호는 여기까지로 한정합니다."),
            ("소액·소기업 사유 21,718계약", "추정가격 기준 소액·소기업 사유 — 진입 장벽 신호가 아닙니다."),
        ]))

    for _ in zone("dbid", "입찰 결과"):
        c1, c2 = st.columns([1.2, 1], gap="medium")
        with c1.container(border=True, key="card_dbid"):
            st.html('<div class="h">국내 경쟁입찰 개찰 결과 <span class="sub">clean_dapa_bid_result · 조각에 커서를 올려 보세요</span></div>')
            hover_donut(BID_RESULT, f"{sum(v for _, v, _ in BID_RESULT):,}", "개찰 결과 행", value_unit="행", height=430)
        c2.html('<div class="card"><div class="h">공고 · 입찰 참고 지표 <span class="sub">서로 단위가 달라 한 줄로 비교하지 않습니다<br>'
                '긴급 공고 5,677 / 10,840 · 유찰 1,741 / 7,201 공고 키.<br>'
                '국외조달 입찰결과는 2025-01~09 부분연도(유찰 2,146 · 낙찰 348행, 달러 표시)라 연간 유찰률로 쓰지 않고 '
                '국내와 나란히 두지 않습니다. 낙찰금액 ≠ 계약금액.</span></div>'
                + pct_rows([("긴급 공고(국내)", 5677 / 10840 * 100, SERIES[3]), ("유찰(국내, 공고 키)", 1741 / 7201 * 100, DOWN)])
                + '</div>')
        caution("방위사업청 국내조달 계약정보 · 입찰공고 · 입찰결과를 건수로만 본다 — 공고 예산 ≠ 낙찰금액 ≠ 계약금액이라 금액은 쓰지 않는다",
                "HS 품목군 · 관세청 수입액과는 연결하지 않는다")


def page_fsc() -> None:
    _mk_css()
    _run_sub({"code": _fsc_code, "plan": _fsc_plan, "army": _fsc_army, "domestic": _fsc_domestic,
              "detail": lambda: search_block("군수품 FSG/FSC")})


# ── ③ 국산화 현황 ────────────────────────────────────────────────────────


def _local_done() -> None:
    for _ in zone("kpi3", "국산화 현황"):
        (g1, n1, _), n_all = max(FSG_DIST, key=lambda r: r[1]), sum(v for _, v, _ in FSG_DIST)
        ask("전자 부품 중 무엇을 국산화했나",
            f"국산화개발을 마친 전자 계열 {n_all:,}행 중 {n1:,}행이 {g1}에 있다 — 가장 많은 군이다.")
        st.html('<div class="kpis k4 row1">'
                + kpi("국산화개발 전자 계열", "2,717", "행", "FSG 58·59·60 · 군급 유효 25,009행 중 · 국산화율 아님", icon="library_books")
                + kpi("반도체 군급", "67", "개", "전자 계열 2,717행 중 · FSG 60(광섬유)은 0행", icon="extension")
                + kpi("국산화개발 사업", "28", "개", "지상 기동 · 화력 사업 한정 · 개발 시점 미상", icon="inventory")
                + kpi("전자 비중 최고 사업", "44.2", "%", "한국형기동헬기 후속 · 최저 경기관총 0%", icon="check_circle")
                + "</div>")

    # 군(FSG)별 분포 · 국산화 상태를 한 줄 좌우 2열로(차트 높이를 맞춘다)
    c_fsg, c_loc = st.columns(2, gap="medium")
    with c_fsg:
        for _ in zone("fsg", "군(FSG)별 분포"):
            with st.container(border=True, key="card_fsg"):
                st.html('<div class="h">FSG 58·59·60 분포 <span class="sub">국산화개발 전자 계열 2,717행 · 단위: 행</span></div>')
                st.plotly_chart(style_fig(hbar(FSG_DIST, 430, "행")), width="stretch", theme=None)
    with c_loc:
        for _ in zone("loc", "국산화 상태"):
            with st.container(border=True, key="card_loc"):
                st.html('<div class="h">전자 군급 부품 국산화 상태 '
                        '<span class="sub">조각에 커서를 올려 보세요 · 단위: 품목 수 · 국산화율 아님</span></div>')
                hover_donut(LOCAL_STATUS, f"{sum(v for _, v, _ in LOCAL_STATUS):,}", "전체 품목 수",
                            value_unit="개", height=430)
    caution("완료 부품 수 ≠ 국산화율 — 전체 부품 수(분모)가 없어 비율을 계산할 수 없다",
            "국산화개발품목 원본에는 기준일이 없다 — 연도별 추이는 그릴 수 없다")


def _local_pair() -> None:
    for _ in zone("pair", "군급 국산화 현황"):
        top_plan = max(PLAN_BY_FSC, key=lambda r: r[1])[0]
        top_loc = max(LOCAL_BY_FSC, key=LOCAL_BY_FSC.get)
        ask("해외에서 많이 사려는 군급을 국산화도 많이 했나",
            f"국외 조달계획이 가장 많은 군급은 {top_plan}, 국산화개발 기록이 가장 많은 군급은 {top_loc}다 — 두 순위가 같지 않다(샘플 값).")
        c1, c2 = st.columns([1.6, 1], gap="medium")
        with c1.container(border=True, key="card_pair"):
            st.html('<div class="h">군급별 국외 조달계획 · 국산화개발 <span class="sub">국외 조달계획 상위 5개 군급(FSC) · 단위: 건 · 샘플 값</span></div>')
            labels = [n for n, _, _ in PLAN_BY_FSC]
            st.plotly_chart(style_fig(mirror_bar(labels, [v for _, v, _ in PLAN_BY_FSC], [LOCAL_BY_FSC[n] for n in labels],
                                                 "국외 조달계획", "국산화개발")), width="stretch", theme=None)
        c2.html(rules_card("읽는 법", [
            ("왼쪽 · 오른쪽", "왼쪽은 해외에서 사 오려는 계획 건수, 오른쪽은 국산화개발을 한 기록 수입니다."),
            ("비율이 아닙니다", "두 자료는 출처와 세는 기준이 달라 나누거나 빼지 않습니다. 막대 길이를 나란히 볼 뿐입니다."),
            ("눈여겨볼 곳", "왼쪽은 긴데 오른쪽이 짧은 군급 — 해외 조달은 많은데 국산화 기록은 적은 곳입니다."),
        ]))


def page_local() -> None:
    _mk_css()
    _run_sub({"done": _local_done, "pair": _local_pair, "detail": lambda: search_block("국산화개발")})


# ── ④ 배경과 자료 ────────────────────────────────────────────────────────


def _bg_policy() -> None:
    for _ in zone("bud", "국외조달 예산 추이"):
        b0, b1 = BUDGET.iloc[0], BUDGET.iloc[-1]
        ask("정부는 해외 조달에 예산을 얼마나 쓰나",
            f"국외조달 예산은 {int(b0['연도'])}년 {b0['국외조달 예산(억 원)']:,.0f}억 원에서 {int(b1['연도'])}년 "
            f"{b1['국외조달 예산(억 원)']:,.0f}억 원으로 늘었고, 방위력개선비 대비 비중도 "
            f"{b0['전체 방위력개선비 대비(%)']:.1f}%에서 {b1['전체 방위력개선비 대비(%)']:.1f}%로 올랐다.")
        st.caption("연도별 예산 막대와 방위력개선비 대비 비중 선 그래프입니다. 단위는 각각 억 원과 %입니다.")
        c1, c2 = st.columns(2, gap="medium")
        with c1.container(border=True, key="card_bud"):
            st.html('<div class="h">연도별 국외조달 예산 '
                    '<span class="sub">단위: 억 원</span></div>')
            ys = BUDGET["국외조달 예산(억 원)"]
            fig = go.Figure(go.Bar(x=BUDGET["연도"], y=ys, marker=dict(color="#9dbdf9", line=dict(color="#fff", width=1)),
                                   text=[f"{v:,}" for v in ys], textposition="outside",
                                   textfont=dict(size=10.5, color=TEXT), cliponaxis=False,
                                   hovertemplate="%{x}년<br>%{y:,}억 원<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(tickformat=",.0f", range=[0, max(ys) * 1.15])
            fig.update_layout(showlegend=False, bargap=.35, margin=dict(l=50, r=8, t=20, b=8))
            st.plotly_chart(style_fig(fig, 330), width="stretch", theme=None)
        with c2.container(border=True, key="card_ratio"):
            st.html('<div class="h">방위력개선비 대비 비중 <span class="sub">단위: %</span></div>')
            fig = go.Figure(go.Scatter(x=BUDGET["연도"], y=BUDGET["전체 방위력개선비 대비(%)"],
                                       mode="lines+markers", line=dict(color=ACCENT, width=2.5),
                                       marker=dict(size=7, color="#fff", line=dict(color=ACCENT, width=2)),
                                       fill="tozeroy", fillcolor="rgba(43,110,246,.10)",
                                       hovertemplate="%{x}년<br>%{y:.1f}%<extra></extra>"))
            fig.update_yaxes(range=[15, 26])
            st.plotly_chart(style_fig(fig, 330), width="stretch", theme=None)

    for _ in zone("proc", "국외조달 절차와 분야별 예산"):
        st.caption("계획·입찰·계약의 절차와 분야별 예산 분포를 보여줍니다. 단계별 건수는 서로 다른 기간의 자료입니다.")
        c1, c2 = st.columns([1, 1.35], gap="medium")
        steps = '<div class="ar">➜</div>'.join(
            f'<div class="st"><div class="ci" style="background:{bg}"><span>{ic}</span><b>{nm}</b></div>'
            f'<div class="ds">{ds}</div><div class="n">{n:,}<small>건</small></div></div>'
            for nm, ic, ds, n, bg in PROC_STEPS)
        c1.html('<div class="card"><div class="h">국외조달 프로세스 <span class="sub">단계별 건수(실측) · 단위: 건<br>'
                '계획 clean_dapa_overseas_plan(2017~2025) · 입찰 clean_dapa_overseas_bid_result(2025-01~09 부분연도, 행) · '
                '계약 clean_dapa_overseas_contract(2017~2025).<br>'
                '기간·단위가 달라 앞 단계 대비 전환율로 읽지 않습니다 — 조달계획 ≠ 계약.</span></div>'
                f'<div class="proc">{steps}</div></div>')
        with c2.container(border=True, key="card_heat"):
            st.html('<div class="h">분야별 국외조달 예산 '
                    '<span class="sub">색 = 분야 안에서의 상대 크기 · 올리면 억 원 · 연도 합계 = 연도별 국외조달 예산</span></div>')
            fig = style_fig(field_heatmap(330))
            fig.update_layout(margin=dict(l=70, r=8, t=10, b=30))   # 왼쪽 분야 이름 · 아래 연도 자리
            st.plotly_chart(fig, width="stretch", theme=None)

    for _ in zone("facts", "국외조달 계획과 국방 R&D 예산"):
        st.caption("집행유형별 국외조달 계획 건수와 부품국산화·공급망·국방반도체 예산을 보여줍니다.")
        c1, c2 = st.columns(2, gap="medium")
        with c1.container(border=True, key="card_ovplan"):
            total = sum(sum(v) for v in OV_PLAN_TYPE.values())
            st.html(f'<div class="h">국외조달 계획 — 집행유형별 건수 <span class="sub">clean_dapa_overseas_plan · '
                    f'2017~2025 합계 {total:,}건 · 단위: 건<br>'
                    '계획(원화 집행 예정액 기준)이며 계약·집행 실적이 아닙니다.<br>'
                    '국가 정보가 없어 수입국과 연결하지 않습니다.</span></div>')
            fig = go.Figure()
            for i, (name, ys) in enumerate(OV_PLAN_TYPE.items()):
                fig.add_trace(go.Bar(x=OV_PLAN_YEARS, y=ys, name=name,
                                     marker=dict(color=(SERIES + [ETC])[i], line=dict(color="#fff", width=1)),
                                     hovertemplate=name + " %{x}년 %{y}건<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.16), bargap=.3)
            st.plotly_chart(style_fig(fig, 330), width="stretch", theme=None)
        with c2.container(border=True, key="card_rnd"):
            st.html('<div class="h">부품국산화 · 공급망 · 국방반도체 예산 <span class="sub">clean_openfiscal_program_budget · '
                    '단위: 억 원 · 흐린 막대 = 2027 정부안<br>'
                    '부품국산화는 2021년 세부사업으로 편성된 뒤 2023년 1,845억이 가장 큽니다.<br>'
                    '공급망(무기체계 공급망 관리)은 2025년 7.5억 → 2026년 52.5억, 국방반도체는 2027년 정부안에 처음 565억.<br>'
                    '같은 기간 국방기술개발은 2.84조 원(2026) — 규모 차이가 커 이 그림에는 넣지 않았습니다. '
                    '관세청 수입액과 합산하지 않습니다.</span></div>')
            fig = go.Figure()
            for i, (name, (xs, ys)) in enumerate(RND_BUDGET.items()):
                color = [SERIES[0], SERIES[1], SERIES[2]][i]
                fig.add_trace(go.Bar(x=xs, y=ys, name=name,
                                     marker=dict(color=color, opacity=[.45 if x == 2027 else 1 for x in xs],
                                                 line=dict(color="#fff", width=1)),
                                     text=[f"{v:,.0f}" if v >= 100 else f"{v:,.1f}" for v in ys],
                                     textposition="outside", textfont=dict(size=10.5, color=TEXT), cliponaxis=False,
                                     hovertemplate=name + " %{x}년 %{y:,.1f}억 원<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(range=[0, 2100])
            fig.update_layout(barmode="group", legend=dict(orientation="h", y=1.14), bargap=.25)
            st.plotly_chart(style_fig(fig, 330), width="stretch", theme=None)
        caution("예산 · 조달계획 건수 · 국내 생산 지표는 단위와 기준이 서로 다르다 — 합하거나 관세청 수입액과 직접 비교하지 않는다")


def _bg_industry() -> None:
    # 키 facts_ind — 정책과 예산의 facts 와 같은 페이지에 이어져 키가 겹치지 않게 둔다.
    for _ in zone("facts_ind", "방산 가동률과 업체 현황"):
        st.caption("통신전자 분야를 강조한 연도별 가동률 선 그래프와 분야별 지정 방산업체 수 막대입니다.")
        c1, c2 = st.columns(2, gap="medium")
        with c1.container(border=True, key="card_util"):
            st.html('<div class="h">방산 분야별 가동률 <span class="sub">clean_kosis_utilization · 통신전자 강조 · 점선 = 평균 · 단위: %<br>'
                    '통신전자는 2016~2022년 70.8~75.2%에서 2023년 89.0%로 9개 분야 중 가장 크게 올랐습니다.<br>'
                    '조사 기반 값이라 생산 능력·국산화 수준이 아니며, 수입 증감과 인과로 읽지 않습니다.</span></div>')
            fig = go.Figure()
            for name, ys in UTIL.items():
                if name in ("통신전자", "평균"):
                    continue
                fig.add_trace(go.Scatter(x=UTIL_YEARS, y=ys, name=name, mode="lines", showlegend=False,
                                         line=dict(color="#cdd6e4", width=1.4),
                                         hovertemplate=name + " %{x}년 %{y:.1f}%<extra></extra>"))
            fig.add_trace(go.Scatter(x=UTIL_YEARS, y=UTIL["평균"], name="9개 분야 평균", mode="lines",
                                     line=dict(color=SERIES[3], width=2, dash="dash"),
                                     hovertemplate="평균 %{x}년 %{y:.1f}%<extra></extra>"))
            fig.add_trace(go.Scatter(x=UTIL_YEARS, y=UTIL["통신전자"], name="통신전자", mode="lines+markers",
                                     line=dict(color=SERIES[1], width=3),
                                     marker=dict(size=7, color="#fff", line=dict(color=SERIES[1], width=2)),
                                     hovertemplate="통신전자 %{x}년 %{y:.1f}%<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(range=[30, 95], ticksuffix="%")
            fig.update_layout(legend=dict(orientation="h", y=1.14))
            st.plotly_chart(style_fig(fig, 330), width="stretch", theme=None)
        with c2.container(border=True, key="card_defco"):
            st.html(f'<div class="h">분야별 방산업체 지정 수 <span class="sub">방위사업청 방산업체 지정현황 · '
                    f'분야 합 {sum(v for _, v in DEF_COMPANY)}개사<br>'
                    f'운영 앱 제목은 「총 84개사」인데 분야별 막대 합은 {sum(v for _, v in DEF_COMPANY)}개사입니다'
                    f'(차이 3개사 — 원인 미확인).<br>지정 기준 값이며 생산 능력이나 국산화 수준을 뜻하지 않습니다.</span></div>')
            rows = [(n, v, SERIES[1] if n == "통신전자" else "#9dbdf9") for n, v in DEF_COMPANY]
            st.plotly_chart(style_fig(hbar(rows, 330, "개사")), width="stretch", theme=None)

    for _ in zone("geo", "지역별 수출입 신고 현황"):
        st.caption("시도별 수입·수출 신고 분포 지도입니다. 신고 업체 소재지는 실제 생산지나 사용지와 다를 수 있습니다.")
        c1, c2 = st.columns([1.3, 1], gap="medium")
        with c1.container(border=True, key="card_geo"):
            st.html('<div class="h">지역별 수입·수출 분포 '
                    '<span class="sub">시·도별 · 오른쪽 위에서 수입/수출 전환 · 시·도에 올리면 수입·수출·수지</span></div>')
            region_map(height=520)
        c2.html(rules_card("해석할 때 주의", [
            ("시·도 = 신고 소재지", "통관 신고 업체 소재지 기준이라 생산지·사용지와 다를 수 있습니다."),
            ("예산은 비정산통로로 사용", "예산은 분석의 보조 지표로만 활용합니다."),
            ("조달계획 ≠ 계약", "계획 건수는 실제 계약 실적이 아닙니다."),
            ("국산화 부품 수 ≠ 국산화율", "개발을 마친 부품 수이며 비율 지표가 아닙니다."),
            ("단위가 다른 자료는 합치지 않음", "관세청 USD 와 예산 원화는 같은 축에 두지 않습니다."),
        ]))


def _bg_source() -> None:
    for _ in zone("src", "데이터 출처"):
        st.caption("사용한 자료의 제공 기관, 데이터 이름, 기간과 수집 방식을 표로 정리했습니다.")
        ask("이 대시보드의 숫자는 어디서 왔나",
            "관세청 · 방위사업청 · 열린재정 · KOSIS 의 공개 자료다. 기준과 단위가 서로 달라 자료끼리 합치지 않고 각자 따로 본다.")
        cat_table(pd.DataFrame([
            ["관세청", "품목별 국가별 수출입실적", "OpenAPI", "2016.01~2026.08", "월 단위 갱신"],
            ["방위사업청", "국외 조달계획", "OpenAPI 15158418", "요구연도 2024~2027", "품목 단위, 건수만"],
            ["방위사업청", "국외 입찰공고 · 입찰결과", "OpenAPI", "스냅샷", "공통 고유키로 결합"],
            ["방위사업청", "국산화개발 품목", "파일데이터", "스냅샷", "국산화율 아님"],
            ["방위사업청", "군급분류집(FSG/FSC)", "파일데이터", "스냅샷", "전자 판정은 팀 확인 전 잠정"],
            ["열린재정", "국외조달 예산", "파일데이터", "2016~2026", "보조 지표로만 사용"],
            ["KOSIS", "방산 가동률 · 광공업생산지수", "OpenAPI", "2016~2026", "잠정치(p) 구간 포함"],
        ], columns=["기관", "데이터", "형태", "기간", "비고"]))

    for _ in zone("match", "자료 결합과 정제 검증"):
        st.caption("입찰공고와 결과의 연결 건수, 자료별 기준일, 전처리 전후 건수를 확인합니다.")
        # 1줄 — 입찰 공고 ↔ 결과 매칭 · 자료별 기준일
        c1, c2 = st.columns([1.35, 1], gap="medium")
        (_, n_ann), (_, n_res), (_, n_key), (_, n_uni) = BID_MATCH
        c1.html(funnel_card("입찰 공고 ↔ 결과 매칭", "단위: 행 · % = 공고 행 대비", BID_MATCH,
                            f"공고키가 없는 결과 {n_res - n_key:,}행 · 키가 맞지 않거나 중복인 {n_key - n_uni:,}행을 빼고 "
                            f"공통 고유키 {n_uni:,}행만 결합합니다. 결과가 없는 공고는 매칭 대상이 아닙니다."))
        asof = "".join(f'<tr><td class="nm">{n}</td><td><b>{d}</b></td><td class="cat">{m}</td></tr>' for n, d, m in AS_OF)
        c2.html('<div class="card"><div class="h">자료별 기준일 <span class="sub">기간 · 판 · 수집 시점<br>'
                '부분연도(2026) · 정부안(2027)은 완결 값과 섞지 않고 라벨로 구분합니다.</span></div>'
                f'<table class="basis asof"><thead><tr><th>자료</th><th>기간 · 판</th><th>기준</th></tr></thead>'
                f'<tbody>{asof}</tbody></table></div>')

        prep = "".join(
            f'<tr><td class="nm">{n}</td><td>{raw:,}</td><td><b>{clean:,}</b></td><td>{drop:,}</td>'
            + (f'<td style="color:#067647;font-weight:700">차이 0 ✓</td></tr>' if raw == clean + drop
               else f'<td style="color:{DOWN};font-weight:700">차이 {raw - clean - drop:+,}</td></tr>')
            + f'<tr><td colspan="5" class="cat" style="text-align:left;white-space:normal;padding-top:0">└ {why}</td></tr>'
            for n, raw, clean, drop, why in PREP_COUNTS)
        st.html('<div class="card"><div class="h">전처리 단계별 건수 <span class="sub">단위: 행<br>'
                '원본 파일은 고치지 않고, 단계마다 「원본 = 정제 + 제외」 차이가 0 인지 확인합니다.</span></div>'
                '<table class="basis"><thead><tr><th>자료</th><th>원본</th><th>정제</th><th>제외</th><th>검산</th></tr></thead>'
                f'<tbody>{prep}</tbody></table></div>')

    st.html('<div class="caption">이 데모 파일의 모든 수치는 샘플입니다. '
            '실제 값과 기준일은 운영 앱(dashboard/main.py)이 AWS RDS 에서 읽어 화면마다 표시합니다.</div>')


def page_background() -> None:
    _mk_css()
    subs = {"policy": _bg_policy, "industry": _bg_industry, "source": _bg_source}
    for i, (key, title) in enumerate(SECTIONS["background"], 1):
        with st.container(key=f"sub_{key}"):
            st.html(f'<div class="bg-group"><span>{i:02d}</span><h2>{title}</h2></div>')
            subs[key]()


# ── 소개(KDD_v2 의 「왜 이 부품인가」 + 「어디에 쓰이나」를 옮겨 옴) ──────────────────────
# 구역 하나 = 질문 · 답(ask) → 설명 재료 → 읽을 때 주의(caution). 차트가 있는 화면은 ask · caution 을 구역 위 · 아래에 직접 쓴다
MOCK_CSS = """<style>
.mk-mark{display:none}
.mk-card .ms{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;line-height:1;
  letter-spacing:normal;text-transform:none;white-space:nowrap;-webkit-font-feature-settings:'liga';font-feature-settings:'liga'}
.mk-q{font-size:15px;color:#5a6b85;margin:2px 0 10px}
/* 질문 + 결론 한 상자 — 윗줄 = 질문(파란 글씨 · Q. 는 흰 글씨 파란 칸), 아랫줄 = 그 답(짙은 남색 굵은 글씨) */
.mk-msg{background:#eef4ff;border-left:4px solid #1d4ed8;border-radius:0 10px 10px 0;padding:14px 18px;margin:0 0 16px}
.mk-msg .q{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:700;color:#1d4ed8;margin-bottom:7px;letter-spacing:-.2px}
.mk-msg .q i{flex:0 0 auto;font-style:normal;font-size:11.5px;font-weight:800;color:#fff;background:#1d4ed8;border-radius:5px;padding:2px 7px}
.mk-msg .a{font-size:17px;font-weight:700;color:#0f1f3d;line-height:1.55;word-break:keep-all}
.mk-note{background:#fafafa;border:1px solid #e5e7eb;border-radius:10px;padding:10px 16px;margin:0 0 26px;font-size:13px;color:#4b5563}
.mk-note b{color:#92400e;margin-right:6px}
.mk-note ul{margin:4px 0 0;padding-left:18px}
.mk-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 16px}
.mk-card{border:1px solid #dae5f3;border-radius:12px;background:#fff;padding:14px 16px}
.mk-card .ms{font-size:28px;color:#1d4ed8}
.mk-card h4{margin:6px 0 4px;font-size:15px;color:#0f1f3d}
.mk-card p{margin:0;font-size:13px;color:#5a6b85;line-height:1.55}
.mk-card small{display:block;font-size:11px;font-weight:800;color:#4978c4;margin-bottom:2px}
.mk-card a{font-size:12px;color:#1d4ed8}
.mk-funnel{display:flex;flex-direction:column;align-items:center;gap:6px;margin:0 0 16px}
.mk-funnel div{background:#1d4ed8;color:#fff;border-radius:8px;padding:12px 16px;text-align:center;font-size:14px}
.mk-funnel div small{display:block;font-size:12px;opacity:.85;margin-top:2px}
.mk-funnel i{font-style:normal;color:#9fb3d6;font-size:18px;line-height:1}
.mk-grp{font-size:14px;font-weight:800;color:#27406b;margin:6px 0 8px}
.mk-grp span{font-weight:600;color:#6b7c96;font-size:12px;margin-left:6px}
.mk-card.warn{background:#fffbeb;border-color:#fde68a}
.mk-tree{display:flex;align-items:stretch;gap:10px;margin:0 0 16px}
.mk-tree>div{flex:1;border:1px solid #dae5f3;border-radius:12px;background:#fff;padding:14px 16px}
.mk-tree>i{align-self:center;font-style:normal;color:#9fb3d6;font-size:22px}
.mk-tree h4{margin:0 0 4px;font-size:15px;color:#1d4ed8}
.mk-tree p{margin:0;font-size:13px;color:#5a6b85;line-height:1.55}
@media (max-width:860px){.mk-cards{grid-template-columns:1fr!important}.mk-tree{flex-direction:column}.mk-tree>i{transform:rotate(90deg)}}
</style>"""

def _mk_css() -> None:
    # <style> 만 있는 st.html 은 이벤트 칸으로 빠지므로 빈 표식을 붙여 본문 칸에 남긴다(main_landing 과 같은 방법)
    with st.container(key=f"mk_css_{url}"):
        st.html(MOCK_CSS + '<i class="mk-mark"></i>')


def ask(question: str, message: str) -> None:
    """질문 + 그 답(이 구역의 결론)을 한 상자에 — 구역 맨 위에 둔다."""
    st.html(f'<div class="mk-msg"><div class="q"><i>Q.</i>{question}</div><div class="a">{message}</div></div>')


def caution(*notes: str) -> None:
    """읽을 때 주의 — 구역 맨 아래에 둔다."""
    st.html('<div class="mk-note"><b>읽을 때 주의</b><ul>' + "".join(f"<li>{n}</li>" for n in notes) + '</ul></div>')


def mock_screen(key: str, title: str, question: str, message: str, notes: tuple = (), extra: str = "") -> None:
    """설명 화면 한 구역 — 질문 · 답 → 설명 재료(extra) → 읽을 때 주의."""
    for _ in zone(key, title):
        ask(question, message)
        if extra:
            st.html(extra)
        if notes:
            caution(*notes)


# ── 소개 — 왜 이 부품인가 ────────────────────────────────────────────────────────
_FUNCS = [("radar", "탐지", "레이더 · 전자광학으로 표적을 찾고 쫓습니다", "레이더 기기 · 증폭 IC"),
          ("cell_tower", "통신", "부대와 체계가 정보를 주고받습니다", "안테나 · 송수신 부분품"),
          ("explore", "항법", "위치와 자세를 알아 길을 찾습니다", "GPS/INS 수신기 · 항행 계기"),
          ("memory", "제어", "신호를 처리해 사격과 비행을 제어합니다", "프로세서 · FPGA · 특수목적 IC")]


def _why_elec() -> None:
    cards = "".join(f'<div class="mk-card"><span class="ms">{ic}</span><h4>{n}</h4><p>{d}</p>'
                    f'<p style="margin-top:6px"><small>맡는 부품</small>{p}</p></div>' for ic, n, d, p in _FUNCS)
    mock_screen(
        "elec", "왜 전자부품인가",
        "무기체계에서 전자부품은 무슨 일을 하나",
        "무기체계의 눈 · 귀 · 두뇌(탐지 · 통신 · 항법 · 제어)는 전자부품이 맡는다. 그런데 무기체계에 들어가는 반도체의 대부분을 해외에서 들여온다.",
        extra=f'<div class="mk-cards">{cards}</div>',
        notes=("「반도체 98.9% 해외 도입」은 국방반도체 발전전략(2024-11)이 인용한 2023-12 조사 값 — 팀 계산값 아님 · 분모 기준 미확인",))


def _why_select() -> None:
    # 한 줄 깔때기는 1,003 → 52 → 13 만(HS_SELECT — 전자부품 현황 「HS 분류기준」과 같은 값). 수집 24 는 진입 52 의
    # 부분집합이 아니라서 층으로 넣지 않고 아래 한 줄로 따로 적는다(plan-revision-2026-09-23.md §2-1)
    (_, n_all, g_all), (_, n_in, _), (_, n_tgt, g_tgt) = HS_SELECT
    n_col = len(HS_BASIS)
    funnel = ('<div class="mk-funnel">'
              f'<div style="width:92%">HS 6단위 전체 {n_all:,}개<small>{g_all}</small></div><i>▼</i>'
              f'<div style="width:64%">진입 기준 충족 {n_in}개<small>군용 전용 세분류 또는 세분류 이름에 전문 용도 명시</small></div><i>▼</i>'
              f'<div style="width:38%;background:#0f2f73"><b>분석 대상 {n_tgt}개 품목군</b><small>전자 계열만 — 「항공기용」 세분류로 걸린 {g_tgt}</small></div>'
              '</div>'
              f'<div class="mk-q" style="text-align:center">수집은 {n_col}개 = 분석 대상 {len(TARGET_HS)}개 + 배경 자료 {n_col - len(TARGET_HS)}개 '
              f'(배경 {n_col - len(TARGET_HS)}개는 진입 {n_in}개 밖에서 따로 모았다)</div>')
    mock_screen(
        "select", "어떻게 골랐나",
        f"{n_all:,}개 품목 중 왜 이 {n_tgt}개인가",
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
    mock_screen(
        "items", "13개 품목군",
        "13개는 각각 어떤 부품인가",
        "13개는 반도체 3 · 전자부품 8 · 소재장비 2로 나뉜다. 이야기의 중심은 반도체와 전자부품 11개다.",
        extra=html)


# ── 소개 — 어디에 쓰이나 ─────────────────────────────────────────────
_ROLE = [("memory", "반도체 3개", "신호 처리 · 사격통제 · 항전 컴퓨터", "화력 · 항공 · 감시정찰"),
         ("radar", "레이더 · 통신 부분품 3개", "표적 탐지 · 추적, 전술통신 · 데이터링크", "감시정찰 · 지휘통제통신"),
         ("explore", "항법 · 항공전자 5개", "위치 · 자세 측정, 항행 계기", "항공 · 함정 · 유도무기")]


def _use_role() -> None:
    cards = "".join(f'<div class="mk-card"><span class="ms">{ic}</span><h4>{n}</h4><p>{d}</p>'
                    f'<p style="margin-top:6px"><small>주로 쓰이는 무기체계 분야</small>{s}</p></div>' for ic, n, d, s in _ROLE)
    mock_screen(
        "role", "부품이 하는 일",
        "13개 품목군은 무기체계의 어떤 기능을 맡나",
        "반도체는 두뇌, 레이더 · 통신 부분품은 눈과 귀, 항법 기기는 길잡이 — 모두 무기체계의 핵심 기능이다.",
        extra=f'<div class="mk-cards" style="grid-template-columns:repeat(3,minmax(0,1fr))">{cards}</div>',
        notes=("부품 종류의 일반적인 쓰임이다 — 특정 무기체계의 부품 목록(BOM)이나 수입 품목의 실제 사용처가 아니다",))


def _use_sys() -> None:
    cards = "".join(f'<div class="mk-card"><small>{c}</small><h4>{n}</h4><p>{d}</p>'
                    f'<p style="margin-top:6px;font-size:12px">{ex}</p></div>' for c, n, d, ex in SYSTEMS)
    mock_screen(
        "sys", "무기체계 분류",
        "우리나라는 무기체계를 어떻게 나누나",
        "방위사업청 분류체계는 무기체계를 10개 대분류로 나눈다. 전자부품은 거의 모든 분류에 들어간다.",
        extra=f'<div class="mk-cards" style="grid-template-columns:repeat(5,minmax(0,1fr))">{cards}</div>',
        notes=("출처: 방위사업청 무기체계 분류체계(별표3)",))


def _use_cases() -> None:
    cards = "".join(f'<div class="mk-card"><small>{f} · {co}</small><h4>{sysn}</h4><p>{stt} · {when}<br>{desc}</p>'
                    f'<a href="{link}" target="_blank" rel="noopener">공식 발표 보기 ↗</a></div>'
                    for f, co, sysn, stt, when, desc, link in CASES)
    mock_screen(
        "cases", "공개 사례",
        "국산 전자부품 · 무기체계는 실제로 어디까지 왔나",
        "KF-21 레이다, 항재밍 수신기처럼 국산 전자부품이 양산 · 수출까지 이어진 사례가 나오고 있다.",
        extra=f'<div class="mk-cards">{cards}</div>',
        notes=("각 사례는 기업 · 기관의 공개 발표다 — 분석 대상 13개 품목의 수입 · 조달 자료와 연결하지 않는다",))


def _intro_use() -> None:
    # 「어디에 쓰이나」 = 부품이 하는 일 · 무기체계 분류 · 공개 사례를 한 소분류에 차례로
    _use_role()
    _use_sys()
    _use_cases()


def page_intro() -> None:
    _mk_css()
    _run_sub({"elec": _why_elec, "select": _why_select, "items": _why_items, "use": _intro_use})


# ════════════════════════════════════════════════════════════════════════════
# 6. 라우터 · 사이드바
# ════════════════════════════════════════════════════════════════════════════
# 사이드바 메뉴 — (페이지, 메뉴 이름, 아이콘, 배너 제목, 배너 부제).
# 아이콘은 차트 유형 버튼과 같은 Material Symbols(Rounded) 이름 — 이모티콘은 글꼴마다 색 · 모양이 달라 통일감이 없었다
PAGES = [
    (st.Page(page_home, title="K-Defense 홈", url_path="home", default=True), "홈", "home",
     "K-Defense 데이터 대시보드", "방산 전자부품 13개 품목군의 수출입과 국산화 현황"),
    (st.Page(page_intro, title="소개", url_path="intro"), "소개", "info",
     "소개", "무기체계의 핵심 기능을 맡는 전자부품 — 왜 이 13개를 골랐고, 어디에 쓰이나"),
    (st.Page(page_parts, title="전자부품 현황", url_path="parts"), "전자부품 현황", "memory",
     "전자부품 현황", "분석 대상 13개 품목군(HS)을 어디서 얼마나 들여오고 내보내나"),
    (st.Page(page_fsc, title="군급 분류와 조달", url_path="fsc"), "군급 분류와 조달", "category",
     "군급 분류와 조달", "군수품 분류(군 FSG · 군급 FSC)로 보면 전자부품을 무엇을, 어떻게 조달하나"),
    (st.Page(page_local, title="국산화 현황", url_path="local"), "국산화 현황", "build",
     "국산화 현황", "군(FSG) 58 · 59 · 60에 속한 전자 군급 부품 중 무엇을 국산화했나"),
    (st.Page(page_background, title="배경과 자료", url_path="background"), "배경과 자료", "account_balance",
     "배경과 자료", "정책·예산, 국내 생산 현황과 데이터 출처를 확인합니다"),
]

pg = st.navigation([p[0] for p in PAGES], position="hidden")

# ── 데이터 정보(ⓘ) — 사이드바 왼쪽 아래 단추 → 대화상자(데이터.png 참고) ─────────────
st.html("""<style>
/* ⓘ 단추 — 둥근 파란 단추, 커서를 올리면 「데이터 정보」 말풍선 */
.st-key-info_btn,.st-key-info_btn_rail{width:auto!important}
.st-key-info_btn [data-testid="stTooltipHoverTarget"],
.st-key-info_btn_rail [data-testid="stTooltipHoverTarget"]{justify-content:flex-start!important}   /* 말풍선 감싸개가 오른쪽 정렬이라 왼쪽으로 */
.st-key-info_btn{padding:4px 20px 16px}
[data-testid="stSidebarUserContent"]{padding-bottom:14px!important}   /* 단추는 사이드바 맨 끝에만 둔다(따라다니지 않음) — 기본 96px 여백을 줄여 끝까지 내리면 바닥에 닿게 */
.st-key-info_btn button,.st-key-info_btn_rail button{width:23px;height:23px;min-width:23px;flex-shrink:0;min-height:0;padding:0;border-radius:50%;border:none;
  display:flex;align-items:center;justify-content:center;
  background:linear-gradient(140deg,#2b6ef6,#3fa9f5);box-shadow:0 2px 7px rgba(43,110,246,.45);transition:transform .16s,box-shadow .16s}
.st-key-info_btn button:hover,.st-key-info_btn_rail button:hover{transform:scale(1.1);box-shadow:0 3px 10px rgba(43,110,246,.6)}
.st-key-info_btn button > *,.st-key-info_btn_rail button > *{margin:0!important;gap:0!important;justify-content:center}   /* 안쪽 감싸개도 가운데로 */
.st-key-info_btn button [data-testid="stMarkdownContainer"],
.st-key-info_btn_rail button [data-testid="stMarkdownContainer"]{display:none}   /* 빈 라벨 자리가 아이콘을 왼쪽으로 밀어서 숨김 */
.st-key-info_btn button [data-testid="stIconMaterial"],
.st-key-info_btn_rail button [data-testid="stIconMaterial"]{color:#fff;font-size:15px;margin:0!important;line-height:1}
.st-key-info_btn_rail{position:absolute!important;left:50%;transform:translateX(-50%);bottom:19px}   /* 미니 사이드바(60px) 가로 가운데 */

/* 대화상자 안 카드 */
[data-testid="stDialog"] [role="dialog"]{border-radius:18px;background:#f2f4f7}
[data-testid="stDialog"] h2{font-size:24px!important;font-weight:800!important;letter-spacing:-.6px;color:#12234a}
.di-lead{font-size:13px;color:#44567a;line-height:1.65;margin:-4px 0 12px}
.di-card{display:flex;gap:14px;padding:14px 15px;margin-bottom:10px;border:1px solid #dde5f2;border-radius:14px;background:#fff;
  box-shadow:0 1px 2px rgba(19,42,84,.05);animation:rise .38s cubic-bezier(.18,.89,.32,1.15) both}
.di-card:nth-child(3){animation-delay:.05s} .di-card:nth-child(4){animation-delay:.1s}
.di-card:nth-child(5){animation-delay:.15s} .di-card:nth-child(6){animation-delay:.2s}
/* 카드 아이콘 — KPI 카드 아이콘(.kpi .ico)과 같은 모양: 옅은 색 둥근 네모 칸 + 같은 계열 진한 색 Material Symbols */
.di-ic{width:34px;height:34px;flex:0 0 34px;border-radius:9px;display:grid;place-items:center;background:#e8f0ff;color:#2b6ef6}
.di-ic .ms,.di-flow .ms{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;line-height:1;letter-spacing:0;
  font-feature-settings:'liga';-webkit-font-smoothing:antialiased}
.di-ic .ms{font-size:19px}
.di-card:nth-child(3) .di-ic{background:#e4fbf6;color:#0f9f85}
.di-card:nth-child(4) .di-ic{background:#f0ecff;color:#7a5af8}
.di-card:nth-child(5) .di-ic{background:#fff2e3;color:#e0851a}
.di-card:nth-child(6) .di-ic{background:#ffe9f1;color:#e0457b}
.di-card > div:last-child{flex:1;min-width:0}
.di-t{font-size:14px;font-weight:800;color:#12234a;letter-spacing:-.3px;margin-bottom:5px}
.di-big{font-size:15px;font-weight:800;color:#16233f;line-height:1.45;letter-spacing:-.3px}
.di-s{font-size:12px;color:#6b7a99;line-height:1.55;margin-top:2px}
.di-chip{display:inline-block;margin-top:7px;padding:4px 11px;border-radius:8px;background:#eaf2ff;font-size:12px;color:#1c4ea3;font-weight:600}
.di-chip b{font-weight:800;margin-left:6px}
.di-kv{display:grid;grid-template-columns:62px 1fr;gap:4px 10px;font-size:12.5px;color:#44567a;line-height:1.5}
.di-kv b{color:#16233f;font-weight:700}
.di-card.warn{background:#fff6f6;border-color:#fbd0d2}
.di-card.warn .di-ic{background:#ffe4e5;color:#e5484d}
.di-card.warn .di-t{color:#b42318}
.di-warn{margin:0!important;padding:0!important;list-style:none;counter-reset:w}
.di-warn li{counter-increment:w;position:relative;padding-left:24px;font-size:12.5px;color:#3b2a2a;line-height:1.55;margin-bottom:5px}
.di-warn li::before{content:counter(w);position:absolute;left:0;top:2px;width:17px;height:17px;border-radius:50%;background:#e5484d;
  color:#fff;font-size:10.5px;font-weight:800;display:grid;place-items:center}
.di-flow{display:flex;align-items:center;flex-wrap:wrap;gap:6px;font-size:12px;margin:4px 0 10px}
.di-flow span:not(.ms){padding:5px 10px;border-radius:8px;background:#eef3fb;border:1px solid #dde5f2;font-weight:700;color:#1c4ea3}
.di-flow .ms{font-size:18px;color:#8fb3f4}
.di-sec{font-size:12.5px;font-weight:800;color:#12234a;margin:10px 0 6px}
.di-tbl{width:100%;border-collapse:collapse;font-size:12px}
.di-tbl td{padding:5px 6px;border-bottom:1px solid #eef2f9;color:#44567a;vertical-align:top}
.di-tbl td:first-child{font-weight:700;color:#16233f;white-space:nowrap}
.di-tbl.gl td:first-child{width:96px}   /* 용어 설명 — 카드마다 용어 칸 폭을 같게 */
.di-demo{font-size:11px;color:#8494ae;margin-top:8px;line-height:1.6}
</style>""")


@st.dialog("데이터 정보", width="medium")
def data_info_dialog() -> None:
    """ⓘ 단추를 누르면 뜨는 데이터 정보. 상세는 펼쳐 보기와 ④ 데이터 출처 · 검증으로 잇는다."""
    n_all, n_tgt = len(HS_BASIS), len(TARGET_HS)
    warns = ["HS 코드만으로 군용/민수용을 구분할 수 없습니다.",
             "특정 국가에 대한 ‘해외 의존도’라는 표현을 사용하지 않습니다.",
             "지역 통계의 수출은 ‘제조장소’, 수입은 ‘납세의무자 주소지’ 기준입니다.",
             "본 대시보드는 실제 방산 수출 실적과 차이가 있을 수 있습니다."]
    st.html(
        '<div class="di-lead">대시보드에 사용된 데이터의 출처, 수집 범위, 처리 과정 및 주요 주의사항을 안내합니다.</div>'
        '<div class="di-card"><div class="di-ic"><span class="ms">database</span></div><div><div class="di-t">데이터 출처</div>'
        '<div class="di-big">관세청 OpenAPI (data.go.kr)<br>데이터셋 ID: 15100475</div>'
        '<div class="di-s">수출입무역통계 (HS품목, 국가, 지역별)</div></div></div>'
        '<div class="di-card"><div class="di-ic"><span class="ms">calendar_month</span></div><div><div class="di-t">분석 기간</div>'
        '<div class="di-big">2016.01 ~ 2026.08</div><div class="di-s">(월별, 부분연도 포함)</div>'
        '<span class="di-chip">최신 수집일:<b>2026-09-14</b></span></div></div>'
        '<div class="di-card"><div class="di-ic"><span class="ms">travel_explore</span></div><div><div class="di-t">수집 범위</div><div class="di-kv">'
        '<span>국가</span><span><b>238개국</b> (ref_country 기준)</span>'
        f'<span>HS6</span><span><b>{n_all}개</b> (수집범위) → <b>{n_tgt}개</b> (분석대상)</span>'
        '<span>국내 지역</span><span><b>17개 시도</b> (관세청 지역 분류 기준)</span></div></div></div>'
        '<div class="di-card"><div class="di-ic"><span class="ms">straighten</span></div><div><div class="di-t">데이터 단위</div><div class="di-kv">'
        '<span>국가 통계</span><span><b>USD</b> (관세청 기준)</span>'
        '<span>지역 통계</span><span><b>천 USD</b> (관세청 기준)</span></div></div></div>'
        '<div class="di-card warn"><div class="di-ic"><span class="ms">warning</span></div><div><div class="di-t">주요 주의사항</div><ol class="di-warn">'
        + "".join(f"<li>{w}</li>" for w in warns) + '</ol></div></div>')
    with st.expander("상세 정보 보기 (주요 테이블, 데이터 처리 흐름, 용어 설명 등)", icon=":material/info:"):
        st.html(
            '<div class="di-sec">데이터 처리 흐름</div><div class="di-flow">'
            '<span>OpenAPI · 파일 수집</span><span class="ms">arrow_forward</span><span>정제 (clean_*)</span><span class="ms">arrow_forward</span>'
            '<span>집계 (점유율 · HHI)</span><span class="ms">arrow_forward</span><span>대시보드</span></div>'
            '<div class="di-sec">주요 테이블</div><table class="di-tbl">'
            '<tr><td>관세청 수출입</td><td>HS 품목 × 국가 × 지역 · 월별 수출입 실적</td></tr>'
            '<tr><td>clean_dapa_overseas_*</td><td>방위사업청 국외 조달계획 · 입찰결과 · 계약</td></tr>'
            '<tr><td>clean_dapa_contract · bid_*</td><td>방위사업청 국내 계약 · 입찰공고 · 입찰결과</td></tr>'
            '<tr><td>clean_kosis_utilization</td><td>KOSIS 방산 분야별 가동률</td></tr>'
            '<tr><td>clean_openfiscal_program_budget</td><td>열린재정 세부사업 예산</td></tr></table>'
            '<div class="di-sec">용어 설명</div><table class="di-tbl">'
            '<tr><td>HS6 / HS10</td><td>국제 공통 6자리 품목 분류 / 한국 세분류 10자리(HSK)</td></tr>'
            '<tr><td>1위 점유율</td><td>품목군 수입액 중 가장 큰 공급국의 비중</td></tr>'
            '<tr><td>HHI</td><td>국가별 점유율(%) 제곱 합 · 2,500 이상 = 높은 집중</td></tr>'
            '<tr><td>R1 / R2</td><td>분석 대상 진입 규칙 — 군용전용 / 항공·항행 세분류</td></tr>'
            '<tr><td>FSG / FSC</td><td>군수품 분류(군급 · 군별) — HS 와 직접 연결하지 않음</td></tr></table>')
        st.page_link(page_of["background"][0], label="배경과 자료에서 더 보기", icon=":material/arrow_forward:",
                     query_params={"sec": "source"})
    st.html('<div class="di-demo">※ 이 데모의 화면 숫자는 대부분 샘플입니다. 위 출처·범위는 운영 앱 기준입니다.</div>')


@st.fragment
def info_button(key: str) -> None:
    """머리글 오른쪽 위 「데이터 정보」 글씨 단추(예전 ⓘ 자리). fragment 라서 눌러도 이 단추와 대화상자만 다시 돌고,
    본문 페이지(표·차트)는 다시 그리지 않는다."""
    if st.button("데이터 정보", key=key, type="tertiary"):
        data_info_dialog()


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
        ("실측", "운영 DB 에서 실제로 센 값(표시 없는 숫자는 샘플)"),
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
SECTIONS = {
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
# 왼쪽 메뉴 아래 파란 칸 — 대분류마다 「이렇게 보세요」 팁 1~2줄(09-30 피드백 — 핵심만). (머리말, 내용) — 머리말은 굵게, 내용은 짧은 명사형으로
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
# 왼쪽 뒤에 있던 두 번째 자주포는 지우고 주변 흙먼지로 번지게 메웠다. 파일 하나로 돌아가게 base64
SV_K9 = ("data:image/jpeg;base64,"
    "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")
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
st.html(f"""<style>
/* ── 새 틀: 사이드바 없음 · 흰 바탕 · 본문 폭 제한 없음(줄마다 안쪽 여백으로 가운데 맞춤) ───────────── */
[data-testid="stSidebar"],[data-testid="stExpandSidebarButton"],[data-testid="stSidebarCollapseButton"]{{display:none!important}}
/* Streamlit 기본 머리 띠(보이지 않는 도구 막대)가 로고 · ⓘ 위를 덮어 클릭을 가로챈다 — 사이드바가 없으니 통째로 숨긴다 */
[data-testid="stHeader"],[data-testid="stToolbar"]{{display:none!important}}
[data-testid="stAppViewContainer"]{{background:#fff}}
.block-container{{padding:0 0 0!important;max-width:none!important}}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]{{gap:0}}

/* ── 머리글 1줄: 로고 · 안내 · 데이터 정보 ─────────────────────────────────── */
.st-key-hdr_top{{padding:0 {_PAD};height:78px!important;min-height:78px;align-items:center!important;border-bottom:1px solid #e3e8f0;background:#fff;
  position:relative}}
/* 로고 위 투명 링크 — 로고 자리(왼쪽 끝 · 폭 370px)만 덮는다 */
[data-testid="stLayoutWrapper"]:has(> .st-key-brand_link){{position:absolute!important;left:{_PAD};top:0;width:370px;height:78px;z-index:3;margin:0}}
.st-key-brand_link,.st-key-brand_link [data-testid="stElementContainer"],.st-key-brand_link [data-testid="stPageLink"]{{width:100%!important;height:78px}}
.st-key-brand_link [data-testid="stPageLink"] a{{display:block;width:100%;height:78px;padding:0;margin:0;opacity:0;cursor:pointer}}
.brand{{display:flex;align-items:center;gap:12px}}
/* 머리글 로고 — 방패 아이콘 가운데에 작은 태극(TAEGEUK, 15px · 시계방향 40도). 방패 모양의 눈대중 가운데가 살짝 위라 46% 에 둔다 */
.brand .mark{{position:relative;display:inline-grid;place-items:center;line-height:0}}
.brand .mark .tg{{position:absolute;left:50%;top:46%;width:15px;height:15px;transform:translate(calc(-50% + 0.3px),-50%) rotate(40deg);pointer-events:none}}
.brand .ms{{font-family:'Material Symbols Rounded'!important;font-size:38px;line-height:1;color:{BLUE_D};
  font-variation-settings:'FILL' 1;font-feature-settings:'liga'}}
.brand b{{display:block;font-size:23px;font-weight:800;letter-spacing:-.6px;color:#0b1f4d;line-height:1.1}}
.brand small{{display:block;font-size:11.5px;font-weight:600;color:#5b6b88;letter-spacing:-.1px;margin-top:3px}}
.util{{font-size:12.5px;color:#6b7a99;display:flex;align-items:center;gap:10px;white-space:nowrap}}
.st-key-hdr_util [data-testid="stElementContainer"]{{width:auto!important;flex:0 0 auto!important}}
.util i{{font-style:normal;color:#cbd3e1}}
.util .badge{{text-decoration:none;padding:3px 9px;border-radius:4px;background:#fff7e6;border:1px solid #fcd9a0;color:#a16207;font-weight:700;font-size:11.5px}}
.st-key-hdr_util{{gap:10px;flex-wrap:nowrap!important}}   /* 「|」와 「데이터 정보」 사이도 안내 글씨끼리와 같은 10px */
.st-key-hdr_util > div{{width:auto!important}}
.st-key-info_btn{{padding:0!important;position:relative;top:1px}}   /* 옆 안내 글씨와 눈높이를 맞추려 1px 아래로 */
/* 「데이터 정보」 — 옆 안내 글씨와 같은 모양의 글씨 단추. 누르면 데이터 정보 대화상자(예전 ⓘ 둥근 단추를 대신함) */
.st-key-info_btn button{{width:auto!important;height:auto!important;min-width:0!important;min-height:0!important;padding:0!important;
  font-size:12.5px!important;line-height:20px!important;
  border-radius:0!important;background:transparent!important;box-shadow:none!important;transform:none!important}}
.st-key-info_btn button [data-testid="stMarkdownContainer"]{{display:block!important}}
.st-key-info_btn button p{{font-size:12.5px!important;line-height:20px!important;color:#6b7a99!important;font-weight:400;white-space:nowrap;
  text-decoration:none}}
.st-key-info_btn button:hover p{{color:{BLUE}!important}}

/* ── 머리글 2줄: 상단 메뉴(GNB) ─────────────────────────────────────── */
.st-key-gnb{{padding:0 {_PAD};height:66px!important;background:#fff;border-bottom:1px solid #e3e8f0;position:relative;z-index:50;
  flex-wrap:nowrap!important;align-items:stretch!important;justify-content:center!important;gap:0!important}}
.st-key-gnb > div{{height:100%}}
div[class*="st-key-gi_"]{{position:relative;height:66px;justify-content:center;flex:1 1 0!important;min-width:0}}
/* 칸 폭은 가로 줄의 칸(바깥 감싸개)에만 준다 — 안쪽 칸은 세로로 쌓이는 틀이라 여기에 flex 크기를 주면 높이가 바뀐다 */
[data-testid="stLayoutWrapper"]:has(> div[class*="st-key-gi_"]){{flex:0 0 {GNB_W}px!important;width:{GNB_W}px!important;max-width:{GNB_W}px!important}}
div[class*="st-key-gi_"] > div:first-child,div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"],
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] > div{{width:100%!important;max-width:none!important}}
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a{{width:100%}}
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a,.gnb-on{{display:flex;justify-content:center;align-items:center;
  height:66px;padding:0 6px;margin:0;border-radius:0;background:transparent!important;position:relative}}
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a p,.gnb-on{{font-size:17px!important;font-weight:700;color:#141c2e!important;
  letter-spacing:-.4px;white-space:nowrap}}
/* 밑줄 — 지금 페이지는 늘 보이고, 다른 메뉴는 커서를 올리면 가운데서 퍼진다 */
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a::after,.gnb-on::after{{content:"";position:absolute;left:50%;bottom:14px;
  width:0;height:4px;border-radius:2px;background:{BLUE};transform:translateX(-50%);transition:width .2s ease}}
.gnb-on::after,div[class*="st-key-gi_"]:hover > div:first-child [data-testid="stPageLink"] a::after{{width:64px}}
.gnb-on{{color:{BLUE}!important}}
div[class*="st-key-gi_"]:hover > div:first-child [data-testid="stPageLink"] a p{{color:{BLUE}!important}}
/* 메뉴 글씨 — 커서 전 · 커서를 올렸을 때 · 지금 페이지 모두 같은 크기(19px) · 같은 자리(칸 위쪽 여백 12px — 가운데 정렬이라 글씨는 그 절반인 6px 만큼 아래).
   커서를 올리거나 지금 페이지일 때는 파란 글씨로만 바뀌고, 밑줄은 쓰지 않는다 */
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a,.gnb-on{{box-sizing:border-box;padding-top:12px!important}}
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a p,.gnb-on{{font-size:19px!important;transition:color .15s}}
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a::after,.gnb-on::after{{display:none!important}}
/* 펼침 메뉴 — 상단 메뉴 어디에 커서를 올려도 모든 메뉴의 블록 목록이 한꺼번에 짙은 파랑 띠에 펼쳐진다 */
div[class*="st-key-gs_"]{{display:none!important;position:absolute;top:66px;left:0;right:0;padding:14px 6px 0 12px;gap:0!important;z-index:3}}
.st-key-gnb:has(div[class*="st-key-gi_"]:hover) div[class*="st-key-gs_"],.st-key-gnb.open div[class*="st-key-gs_"]{{display:flex!important}}
/* 띠는 「부품 현황」 왼쪽 세로선 ~ 「배경과 자료」 오른쪽 세로선 사이만(가운데 모은 메뉴 칸 폭) — 양옆과 전체 메뉴(≡) 아래는 비운다 */
.st-key-gnb::after{{content:"";position:absolute;left:calc(50% - {len(GNB) * GNB_W // 2}px);width:{len(GNB) * GNB_W}px;top:66px;height:{_DROP_H}px;background:{BLUE_D};border-radius:0 0 14px 14px;
  box-shadow:0 12px 24px rgba(0,30,90,.25);opacity:0;visibility:hidden;transition:opacity .15s;z-index:1}}
.st-key-gnb:has(div[class*="st-key-gi_"]:hover)::after,.st-key-gnb.open::after{{opacity:1;visibility:visible}}
.st-key-gnb:has(div[class*="st-key-gi_"]:hover),.st-key-gnb.open{{height:{66 + _DROP_H}px!important;padding-bottom:{_DROP_H}px;margin-bottom:-{_DROP_H}px;box-sizing:border-box}}   /* 펼친 띠까지 커서가 머무는 자리로 */
/* 펼쳤을 때 늘어난 아랫부분은 투명하게 — 흰 바탕은 메뉴 줄(66px)까지만, 밑줄도 그 자리(65px)에 그린다(원래 border-bottom 은 늘어난 맨 아래로 내려가므로 숨김).
   파란 띠 양옆(≡ 아래 포함)은 모두 비운다 */
.st-key-gnb:has(div[class*="st-key-gi_"]:hover),.st-key-gnb.open{{border-bottom-color:transparent!important;
  background:linear-gradient(#e3e8f0,#e3e8f0) 0 65px/100% 1px no-repeat,linear-gradient(#fff,#fff) 0 0/100% 66px no-repeat!important}}
div[class*="st-key-gs_"] [data-testid="stPageLink"] a{{padding:10px 8px 10px 13px;margin:0;border-radius:4px;background:transparent}}   /* 줄 간격 넓게 · 글자는 왼쪽 여백 +5px */
div[class*="st-key-gs_"] > div{{flex-shrink:0!important;margin:0!important}}   /* 칸 높이에 눌려 줄끼리 겹치지 않게 */
div[class*="st-key-gs_"] [data-testid="stPageLink"] a p{{font-size:16px!important;font-weight:500;color:#c9d8f5!important;
  white-space:normal;line-height:1.35!important;word-break:keep-all}}   /* 칸보다 긴 이름은 잘리지 않고 두 줄로 */
div[class*="st-key-gs_"] [data-testid="stPageLink"] a:hover{{background:rgba(255,255,255,.1)}}
div[class*="st-key-gs_"] [data-testid="stPageLink"] a:hover p{{color:#fff!important}}
div[class*="st-key-gi_"]:hover div[class*="st-key-gs_"]{{background:rgba(255,255,255,.06);height:{_DROP_H}px}}
/* 펼침 메뉴 칸 나눔 — 메뉴(부품 현황 · 군급 분류와 조달 …)마다 띠 높이만큼 옅은 세로선으로 가른다. 맨 끝 배경과 자료는 오른쪽에도 선을 그어 양 끝을 닫는다 */
div[class*="st-key-gs_"]{{height:{_DROP_H}px;box-sizing:border-box;border-left:1px solid rgba(255,255,255,.2)}}
.st-key-gs_background{{border-right:1px solid rgba(255,255,255,.2)}}
/* 띠 아래 모서리를 둥글게 한 만큼 양 끝 칸(커서를 올리면 옅게 밝아짐)도 같은 반지름으로 깎는다 */
.st-key-gs_{GNB[0]}{{border-bottom-left-radius:14px}}
.st-key-gs_{GNB[-1]}{{border-bottom-right-radius:14px}}
/* 전체 메뉴(≡) */
.st-key-gnb_all{{width:66px!important;flex:0 0 66px!important}}
/* 전체 메뉴(≡)는 흐름에서 빼 파란 펼침 띠 바로 오른쪽에 — 띠 오른쪽 끝(50% + 메뉴 칸 폭 합의 절반)에 붙인다. 세로 자리는 메뉴 줄 그대로 */
[data-testid="stLayoutWrapper"]:has(> .st-key-gnb_all){{position:absolute!important;left:calc(50% + {len(GNB) * GNB_W // 2}px);right:auto;top:0;height:66px}}
.gnb-all{{width:66px;height:66px;display:grid;place-items:center;border:none;border-radius:0;background:{BLUE_D};padding:0;cursor:pointer;
  transition:background .15s}}
.gnb-all:hover,.st-key-gnb.open .gnb-all{{background:{BLUE}}}
.gnb-all .ms{{font-family:'Material Symbols Rounded'!important;font-size:30px;line-height:1;color:#fff;font-weight:400;font-style:normal;
  font-feature-settings:'liga'}}
.st-key-gnbjs,[data-testid="stLayoutWrapper"]:has(> .st-key-gnbjs){{display:none!important}}

/* ── 서브 배너 — 짙은 파랑 바탕 + 항공모함 · K9 자주포 사진, 왼쪽 아래에 페이지 제목 칸 ─────────────── */
.sv{{position:relative;overflow:hidden;height:168px;padding:0 {_PAD};
  background:linear-gradient(100deg,#00236b 0%,{BLUE_D} 38%,{BLUE_D} 100%)}}   /* 제목 칸부터 오른쪽 끝까지 제목 부분과 같은 짙은 파랑 */
/* 배너 격자무늬 — 없앴다 */
/* 배너 그림 — 예전 그림(HERO_IMG, 배 + 전투기 한 장 · 가로 811px)이 놓이던 자리를 그대로 쓴다.
   왼쪽 배 자리(53.6%)에는 항공모함 사진(Unsplash, 파란 바탕 색을 입힘)을, 오른쪽 자리에는 K9 자주포를 둔다 */
.sv-ph{{position:absolute;top:0;bottom:0;right:max(0px, calc((100% - {WRAP}px) / 2));width:811px;pointer-events:none}}
.sv-ph i{{position:absolute;top:0;bottom:0;background-repeat:no-repeat}}
.sv-ph .ship{{left:110px;width:53.6%;background-size:cover;background-position:center 62%;mix-blend-mode:luminosity;opacity:.5;
  -webkit-mask-image:linear-gradient(90deg,transparent 0,#000 25%,#000 50%,transparent 100%);
  mask-image:linear-gradient(90deg,transparent 0,#000 25%,#000 50%,transparent 100%)}}
/* K9 자주포 — 배 사진과 같은 효과(파란 바탕 색 · luminosity · 40%, 양 끝을 넓게 녹임).
   사진 폭을 칸의 90% 로 두고, 자주포가 칸 가운데 · 살짝 아래에 오게 30% 68% 자리.
   사진이 칸보다 좁아 양옆에 사진 끝(칸의 3% · 93% 자리)이 생기므로, 마스크가 그 안쪽(4% · 92%)에서 이미 투명해지게 해 경계선이 보이지 않게 */
.sv-ph .k9{{right:0;width:46.4%;background-size:90% auto;background-position:30% calc(68% - 3px);mix-blend-mode:luminosity;opacity:.4;
  transform:translateX(-40px);   /* 왼쪽 40px (위로 3px 은 background-position 에서) */
  -webkit-mask-image:linear-gradient(90deg,transparent 4%,#000 24%,#000 62%,transparent 92%);
  mask-image:linear-gradient(90deg,transparent 4%,#000 24%,#000 62%,transparent 92%)}}
.sv-in{{position:relative;height:100%;display:flex;align-items:flex-end}}
.sv-box{{width:{LNB_W}px;height:112px;flex:0 0 {LNB_W}px;display:flex;flex-direction:column;justify-content:center;align-items:center;
  background:#fff;color:{BLUE_D};border-top:4px solid {BLUE};box-shadow:0 -6px 18px rgba(0,20,70,.18)}}
.sv-box small{{font-size:11px;font-weight:700;letter-spacing:2px;color:#7b8fb5;margin-bottom:6px}}
.sv-box b{{font-size:22px;font-weight:800;letter-spacing:-.6px;text-align:center;line-height:1.25;padding:0 10px}}
.sv-title{{align-self:center;padding:0 0 0 44px;color:#fff}}   /* 배너 세로 가운데 */
.sv-title h1{{margin:0;font-size:31px;font-weight:800;letter-spacing:-.8px;color:#fff;line-height:1.2}}
.sv-title p{{margin:8px 0 0;font-size:13px;color:#c7d7f6;letter-spacing:-.1px}}

/* ── 본문 줄: 왼쪽 메뉴(LNB) + 오른쪽 본문 ───────────────────────────── */
/* 본문 줄을 제목 칸 높이(112px)만큼 배너 위로 끌어올린다 — 왼쪽 메뉴 맨 위의 제목 칸이 배너 아래쪽에 걸치고,
   오른쪽 본문은 같은 높이만큼 위 여백을 두어 배너 아래에서 시작한다(끌어올린 자리는 투명해 배너가 그대로 보인다) */
.st-key-body{{padding:0 {_PAD} 70px;gap:44px!important;flex-wrap:nowrap!important;align-items:flex-start!important;background:transparent;
  margin-top:-112px!important;position:relative;z-index:3}}
.st-key-lnb{{gap:6px!important;padding-top:0;position:relative;left:-41px}}   /* 제목 칸 + 메뉴 묶음을 41px 왼쪽 */
.sv-sp{{width:{LNB_W}px;flex:0 0 {LNB_W}px}}
.lnb-box{{margin-bottom:10px;border-radius:12px 12px 0 0}}   /* 제목 칸은 아래 메뉴와 같은 세로줄 · 위쪽 모서리는 퀵메뉴처럼 둥글게 */
/* 소분류 칸 — 글자 길이와 상관없이 왼쪽 메뉴 폭(LNB_W)을 꽉 채우는 같은 크기의 직사각형.
   page_link 는 기본이 글자 폭만큼이라 감싸는 칸까지 모두 100% 로 늘린다. 테두리도 같은 두께(투명)로 두어 선택 칸과 크기가 같다 */
.st-key-lnb [data-testid="stElementContainer"],.st-key-lnb [data-testid="stPageLink"],
.st-key-lnb [data-testid="stPageLink"] > div{{width:100%!important;max-width:none!important}}
.st-key-lnb [data-testid="stPageLink"] a,.lnb-on{{display:flex;align-items:center;justify-content:space-between;width:100%;min-height:50px;
  box-sizing:border-box;padding:0 18px;margin:0;border:1.5px solid transparent;border-radius:0;background:#f3f6fb;position:relative;transition:background .15s}}
.st-key-lnb [data-testid="stPageLink"] a p,.lnb-on{{font-size:15px!important;font-weight:700;color:#1b2540!important;letter-spacing:-.4px}}
/* 기호 — 선택 안 된 칸 「·」 · 선택된 칸 「✓」 */
.st-key-lnb [data-testid="stPageLink"] a::after,.lnb-on::after{{flex:0 0 auto;margin-left:8px;line-height:1}}
.st-key-lnb [data-testid="stPageLink"] a::after{{content:"·";font-size:24px;font-weight:700;color:#9aa6bd}}
.st-key-lnb [data-testid="stPageLink"] a:hover{{background:#e8effb}}
.st-key-lnb [data-testid="stPageLink"] a:hover p,.st-key-lnb [data-testid="stPageLink"] a:hover::after{{color:{BLUE}!important}}
.lnb-on{{background:#fff;border-color:{BLUE_D};color:{BLUE_D}!important}}
.lnb-on::after{{content:"✓";font-size:16px;font-weight:800;color:{BLUE_D}}}
/* 소분류 링크(스크롤형) — 예전 page_link 칸과 같은 모양 · 크기. 지금 보이는 소분류(.on)는 선택 칸(✓) 모양 */
.lnb-nav{{display:flex;flex-direction:column;gap:6px}}
.lnb-a{{display:flex;align-items:center;justify-content:space-between;width:100%;min-height:50px;box-sizing:border-box;padding:0 18px;
  margin:0;border:1.5px solid transparent;border-radius:0;background:#f3f6fb;transition:background .15s;text-decoration:none!important;
  font-size:15px;font-weight:700;color:#1b2540!important;letter-spacing:-.4px}}
.lnb-a::after{{content:"·";flex:0 0 auto;margin-left:8px;line-height:1;font-size:24px;font-weight:700;color:#9aa6bd}}
.lnb-a:hover{{background:#e8effb;color:{BLUE}!important}}
.lnb-a:hover::after{{color:{BLUE}}}
.lnb-a.on{{background:#fff;border-color:{BLUE_D};color:{BLUE_D}!important}}
.lnb-a.on::after{{content:"✓";font-size:16px;font-weight:800;color:{BLUE_D}}}
/* 배경과 자료에서는 현재 읽는 절의 목차 항목만 크게 표시한다. */
.st-key-body:has(.st-key-sub_policy) .lnb-a.on{{min-height:66px;padding:0 20px;background:#e8f0ff;
  border-left:4px solid {BLUE_D};font-size:18px;font-weight:800}}
.st-key-body:has(.st-key-sub_policy) .lnb-a.on::after{{font-size:17px}}
div[class*="st-key-sub_"]{{scroll-margin-top:22px}}   /* 소분류로 스크롤해 갈 때 위 여백 — zone 과 같게 */
.st-key-lnbjs,[data-testid="stLayoutWrapper"]:has(> .st-key-lnbjs){{display:none!important}}
/* 왼쪽 메뉴는 스크롤해도 화면 위쪽에 붙어 따라온다 */
[data-testid="stLayoutWrapper"]:has(> .st-key-lnb){{position:sticky;top:98px;align-self:flex-start;z-index:5;flex:0 0 {LNB_W}px!important;width:{LNB_W}px!important;min-width:{LNB_W}px!important;max-width:{LNB_W}px!important}}
.st-key-lnb{{width:{LNB_W}px!important;min-width:{LNB_W}px!important;max-width:{LNB_W}px!important;flex:0 0 {LNB_W}px!important}}   /* 메뉴 폭 고정 — 글자 길이로 늘거나 줄지 않게 */
.lnb-sub{{margin:4px 0 8px;padding:0 4px 0 18px}}
.lnb-sub li{{font-size:12.5px;color:#5b6b88;line-height:1.9;list-style:none;position:relative}}
.lnb-sub li::before{{content:"";position:absolute;left:-10px;top:11px;width:3px;height:3px;background:#8b98b0}}
.lnb-help{{margin-top:18px;padding:16px 16px 16px;background:linear-gradient(135deg,{BLUE_D},{BLUE});color:#fff;border-radius:2px 2px 12px 12px}}   /* 아래쪽 모서리 둥글게 */
.lnb-help b{{display:block;font-size:14px;font-weight:800;margin-bottom:5px}}
.lnb-help span{{font-size:11.5px;color:#cfdcf7;line-height:1.6}}
.lnb-help ul{{margin:4px 0 0!important;padding:0!important;list-style:none}}
.lnb-help li{{position:relative;margin:0 0 10px!important;padding:0 0 0 11px!important;font-size:12px;line-height:1.6;color:#e3ecfb;word-break:keep-all}}
.lnb-help li em{{display:block;font-style:normal;font-size:12.5px;font-weight:800;color:#fff;margin-bottom:1px}}   /* 머리말 한 줄 + 내용 한 줄 */
.lnb-help li::before{{content:"";position:absolute;left:0;top:9px;width:4px;height:4px;border-radius:50%;background:#7cc4ff}}
.lnb-help li:last-child{{margin-bottom:0!important}}   /* 마지막 줄 아래 여백은 칸 안쪽 여백(16px)만 — 위아래 여백을 같게 */
.st-key-main{{min-width:0;gap:0!important;padding-top:112px}}
.crumb{{display:flex;justify-content:flex-end;align-items:center;gap:8px;padding:18px 0 14px;font-size:15px;color:#6b7a99}}
.crumb .ms{{font-family:'Material Symbols Rounded'!important;font-size:17px;line-height:1;color:#6b7a99;font-variation-settings:'FILL' 1}}
.crumb i{{font-style:normal;color:#b3bdcf;font-size:13px}}
.crumb b{{color:#1b2540;font-weight:700}}
/* 홈 아이콘 링크 + 「› 메뉴 이름」 — 한 줄 오른쪽 끝. 링크 글씨(「홈」)는 숨기고 아이콘만 보인다 */
.st-key-crumb{{gap:8px!important;padding:18px 0 14px;flex-wrap:nowrap!important}}
.st-key-crumb > div{{width:auto!important;flex:0 0 auto!important}}
.st-key-crumb .crumb{{padding:0}}
.st-key-crumb [data-testid="stPageLink"] a{{padding:0;margin:0;background:transparent!important;gap:0!important;min-height:0}}
.st-key-crumb [data-testid="stPageLink"] a p{{display:none}}
.st-key-crumb [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{{font-size:20px!important;color:#6b7a99;margin:0!important;
  font-variation-settings:'FILL' 1;transition:color .15s}}
.st-key-crumb [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"]{{color:{BLUE}}}
.ctitle{{display:flex;align-items:baseline;gap:12px;margin:2px 0 22px;padding-bottom:16px;border-bottom:2px solid #1b2540}}
.ctitle h2{{margin:0;padding:0;font-size:26px;font-weight:800;letter-spacing:-.7px;color:#101a33}}
.ctitle span{{font-size:13px;color:#6b7a99}}
/* 블록 — 한 페이지에 차례로 이어진다. 테두리 · 이름표 대신 블록마다 제목 줄(.sec-h) */
div[class*="st-key-zone_"]{{border:none;border-radius:0;background:transparent;padding:0;margin:4px 0 64px;scroll-margin-top:22px}}
.sec-h{{display:flex;align-items:baseline;gap:12px;margin:0 0 20px;padding-bottom:14px;border-bottom:2px solid #1b2540}}
.sec-h h2{{margin:0;padding:0;font-size:25px;font-weight:800;letter-spacing:-.7px;color:#101a33}}
/* 배경과 자료 페이지(.st-key-sub_policy 가 있는 본문)만 — 세부 구역 제목(.sec-h) 아래 검은 선을 뺀다. 대분류 파란 선(.bg-group)은 그대로 */
.st-key-body:has(.st-key-sub_policy) .sec-h{{border-bottom:none;padding-bottom:0}}
.bg-group{{display:flex;align-items:baseline;gap:12px;margin:20px 0 28px;padding:0 0 15px;border-bottom:3px solid {BLUE_D}}}
.bg-group span{{font-size:13px;font-weight:800;color:{BLUE}}}
.bg-group h2{{margin:0;font-size:29px;font-weight:850;color:#101a33}}
div[class*="st-key-zone_"]::before{{display:none}}
/* 첫 블록 KPI — 페이지마다 카드 수(4 · 5 · 6개)가 달라도 카드 한 장의 크기 · 비율은 모든 페이지에서 같게 한다.
   한 줄 3칸 폭(6칸 격자에서 2칸씩)으로 고정하고, 덜 찬 줄은 가운데로 모은다 — 5개는 3 + 2, 4개는 2 + 2, 6개는 3 + 3.
   줄 높이도 1fr 로 같게(설명이 두 줄인 카드가 있어도 모든 카드 높이가 같다) */
.kpis:not(.q),.kpis.k4:not(.q),.kpis.k6:not(.q){{grid-template-columns:repeat(6,minmax(0,110px));grid-auto-rows:1fr;justify-content:center}}   /* 카드 폭 = 110 × 2 + 칸 사이 26 = 246px */
.kpis:not(.q) .kpi{{grid-column:span 2;min-height:170px}}
.kpis:not(.q):not(.k4):not(.k6) .kpi:nth-child(4){{grid-column:2 / span 2}}
.kpis.k4:not(.q) .kpi:nth-child(odd){{grid-column:2 / span 2}}
/* 한 줄 4장(.row1) — ③ 국산화 완료 부품. 카드는 다른 페이지와 같은 246 × 170px(제목 「국산화개발 전자 계열」이 한 줄에 들어가는 폭),
   칸 사이만 26 → 20px 로 좁혀 4장이 본문 폭(1400 - 여백 64 - 왼쪽 메뉴 230 - 간격 44 = 1,062px) 안에 한 줄로 들어간다 */
.kpis.k4.row1:not(.q){{grid-template-columns:repeat(4,minmax(0,246px));gap:20px}}
.kpis.k4.row1:not(.q) .kpi,.kpis.k4.row1:not(.q) .kpi:nth-child(odd){{grid-column:auto}}
/* ① 부품 현황 KPI(.parts-kpi-row — 종합 현황표 · 수출입 현황 핵심 지표)만 — 넓은 화면은 1줄 4칸, 860px 이하는 2 × 2.
   배치(격자 칸 · grid-column)만 바꾸고 카드 모양 · 글씨는 위 규칙 그대로. 다른 페이지 4장(.kpis.k4)은 2 + 2 가운데 그대로 */
.kpis.k4.parts-kpi-row:not(.q){{grid-template-columns:repeat(4,minmax(0,1fr))}}
.kpis.k4.parts-kpi-row:not(.q) .kpi,.kpis.k4.parts-kpi-row:not(.q) .kpi:nth-child(odd){{grid-column:auto}}
@media (max-width:860px){{
  .kpis.k4.parts-kpi-row:not(.q){{grid-template-columns:repeat(2,minmax(0,1fr))}}
}}
/* 공급국 비중 카드(수출입 현황) — 제목과 도넛 사이 기본 간격(1rem)을 줄인다 */
.st-key-card_share{{gap:4px!important}}
/* 글씨 크기도 페이지 상관없이 같게 */
.kpis:not(.q) .kpi .l,.kpis:not(.q) .kpi .l.long,.kpis.k6:not(.q) .kpi .l{{font-size:17px;letter-spacing:-.3px}}
.kpis:not(.q) .kpi .v,.kpis.k6:not(.q) .kpi .v{{font-size:35px}}
.kpis:not(.q) .kpi .v.long{{font-size:30px}}

.st-key-kdjs,[data-testid="stLayoutWrapper"]:has(> .st-key-kdjs){{display:none!important}}

/* ── 바닥글 ─────────────────────────────────────────────────────── */
.st-key-ft{{background:#1f2633;padding:30px {_PAD} 34px;gap:44px!important;align-items:flex-start!important;flex-wrap:nowrap!important;color:#9aa4b8}}
.st-key-ft .brand .ms{{color:#fff;font-size:34px}}   /* 바닥글 방패 — 흰색 */
.st-key-ft .brand .mark .tg{{width:13.5px;height:13.5px}}   /* 바닥글 방패(34px)에 맞춰 머리글(38px · 15px)과 같은 비율 */
.st-key-ft .brand b{{color:#dfe5ef;font-size:20px}}
.st-key-ft .brand small{{color:#8591a6}}
/* 로고 — 위에 투명 링크를 덮어 누르면 Main 으로 */
.st-key-ft_brand{{position:relative;gap:0!important}}
.st-key-ft_brand [data-testid="stElementContainer"]:has([data-testid="stPageLink"]){{position:absolute!important;inset:0;width:100%!important;height:100%;z-index:2;margin:0}}
.st-key-ft_brand [data-testid="stPageLink"],.st-key-ft_brand [data-testid="stPageLink"] > div{{width:100%!important;height:100%}}
.st-key-ft_brand [data-testid="stPageLink"] a{{display:block;width:100%;height:100%;padding:0;margin:0;opacity:0;cursor:pointer}}
.st-key-ft_mid{{flex:1 1 0!important;min-width:0;gap:6px!important}}
.ft-mid{{font-size:12.5px;line-height:1.95;color:#9aa4b8}}
/* 링크 줄 — 데이터 이용 안내 | 데이터 출처 | 용어 설명 | 주의사항 */
.st-key-ft_links{{gap:0!important;flex-wrap:wrap!important}}
.st-key-ft_links > div{{width:auto!important;flex:0 0 auto!important;display:flex!important;align-items:center;flex-direction:row!important}}
.st-key-ft_links [data-testid="stVerticalBlock"]{{gap:0!important;width:auto!important}}   /* 용어 설명(fragment) 칸 — 한 줄에 맞춤 */
.st-key-ft_links button [data-testid="stMarkdownContainer"]{{display:block!important}}
.st-key-ft_links > div + div::before{{content:"";display:inline-block;width:1px;height:10px;background:#566074;margin:0 12px;vertical-align:middle}}
.ftl{{font-size:12.5px;color:#c9d1de;font-weight:600;line-height:1.95;transition:color .15s}}
/* 링크 줄 글씨는 모두 같은 흰색 계열 — 커서를 올린 항목만 파랑(#7fb0ff) */
.st-key-ft_links [data-testid="stPageLink"] a{{position:relative;top:1px}}   /* 페이지 링크(데이터 출처)만 글자가 1px 위에 떠서 옆 글씨와 높이를 맞춤 */
.st-key-ft_links [data-testid="stPageLink"] a,.st-key-ft_links button{{padding:0!important;margin:0;min-height:0!important;height:auto!important;
  background:transparent!important;border:none!important;box-shadow:none!important}}
.st-key-ft_links [data-testid="stPageLink"] a p,.st-key-ft_links button p{{font-size:12.5px!important;color:#c9d1de!important;font-weight:600;line-height:1.95!important}}
.st-key-ft_links [data-testid="stPageLink"] a:hover p,.st-key-ft_links button:hover p,.ftl:hover{{color:#7fb0ff!important}}
.ft-team{{color:#c9d1de;font-weight:600;text-decoration:none}}
.ft-team:hover{{color:#fff;text-decoration:underline}}
.ft-rel{{width:230px;background:#151a24;border:1px solid #2f3848;font-size:12.5px}}
.ft-rel summary{{padding:11px 14px;cursor:pointer;color:#c9d1de;list-style:none;display:flex;justify-content:space-between}}
.ft-rel summary::after{{content:"▲";font-size:9px;color:#8591a6}}
.ft-rel[open] summary::after{{content:"▼"}}
.ft-rel a{{display:block;padding:7px 14px;color:#9aa4b8;text-decoration:none;border-top:1px solid #262e3c}}
.ft-rel a:hover{{color:#fff;background:#262e3c}}
</style>""")

intro_screen()

# ── 머리글 ──────────────────────────────────────────────────────────────
with st.container(key="hdr_top", horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
    st.html(f'<div class="brand"><span class="mark"><span class="ms">shield</span>{TAEGEUK}</span><div><b>K-Defense Electronics</b>'
            '<small>방산 전자부품 수입 집중도 · 국산화 · 조달 데이터 대시보드</small></div></div>')
    with st.container(key="hdr_util", horizontal=True, width="content", vertical_alignment="center"):
        st.html('<div class="util"><span>로그인</span><i>|</i>'
                '<span>공지사항</span><i>|</i></div>')
        info_button("info_btn")
    # 로고(방패 · K-Defense · 부제) 위에 투명한 링크를 덮어, 누르면 홈(Main 첫 화면)으로 간다
    with st.container(key="brand_link"):
        st.page_link(page_of["home"][0], label="K-Defense 홈", query_params={"sec": "main"})

# ≡ 단추 — 누르면 파란 펼침 띠가 커서를 떼도 계속 펼쳐져 있고, 다시 누르면 닫힌다(열려 있을 때는 × 모양).
# st.html 은 스크립트를 돌리지 않아, 보이지 않는 components.html 안에서 바깥 화면(window.parent)을 다룬다
GNB_JS = r"""<script>
(function () {
  const P = window.parent, doc = P.document;
  function apply() {
    const g = doc.querySelector('.st-key-gnb'); if (!g) return false;
    g.classList.toggle('open', !!P.__gnbOpen);
    const ic = doc.querySelector('.gnb-all .ms'); if (ic) ic.textContent = P.__gnbOpen ? 'close' : 'menu';
    return true;
  }
  if (P.__gnbClick) doc.removeEventListener('click', P.__gnbClick, true);
  P.__gnbClick = e => {
    const b = e.target.closest && e.target.closest('.gnb-all');
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    P.__gnbOpen = !P.__gnbOpen;
    apply();
  };
  doc.addEventListener('click', P.__gnbClick, true);
  let n = 0;
  const t = P.setInterval(() => { n++; if (apply() || n > 50) P.clearInterval(t); }, 100);
})();
</script>"""

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
                ' — 화면의 숫자는 샘플이며 DB 에 접속하지 않습니다 · © 2026 K-Defense 팀 프로젝트</div>')
    st.html('<details class="ft-rel"><summary>관련 사이트 바로가기</summary>'
            '<a href="https://unipass.customs.go.kr/ets/" target="_blank">관세청 수출입무역통계</a>'
            '<a href="https://www.dapa.go.kr" target="_blank">방위사업청</a>'
            '<a href="https://kosis.kr" target="_blank">KOSIS 국가통계포털</a>'
            '<a href="https://www.openfiscaldata.go.kr" target="_blank">열린재정</a>'
            '<a href="https://www.data.go.kr" target="_blank">공공데이터포털</a></details>', width="content")

# ── 화면이 바뀌면 맨 위로 ──────────────────────────────────────────────────
# st.html 은 스크립트를 돌리지 않아, 보이지 않는 components.html 안에서 바깥 화면(window.parent)을 다룬다.
# __NAV__ 에 대분류 · 소분류를 넣어 화면이 바뀔 때만 새로 붙는다(같은 화면에서 위젯을 만질 때는 스크롤 그대로)
_TOP_JS = r"""<script>
(function () {
  const P = window.parent, doc = P.document, NAV = "__NAV__";
  if (P.__kdNav === NAV) return;
  P.__kdNav = NAV;
  let n = 0;
  const t = P.setInterval(() => {
    n++;
    const m = doc.querySelector('[data-testid="stMain"]');
    if (m) { m.scrollTop = 0; P.clearInterval(t); } else if (n > 20) P.clearInterval(t);
  }, 100);
})();
</script>"""
with st.container(key="kdjs"):
    components.html(_TOP_JS.replace("__NAV__", f"{url}|{_SEC['sel']}"), height=0)
