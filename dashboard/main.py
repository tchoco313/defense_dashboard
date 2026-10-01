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
[data-testid="stAppViewContainer"]{{background:var(--bg)}}
.block-container{{padding:0 34px 40px;max-width:1500px}}

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
/* 조회 결과 카드(차트 · 결과 표 탭) — ⓘ 은 탭 칸 오른쪽 위에 띄우고 말풍선은 아래로 연다(오른쪽 아래는 내려받기 단추 자리) */
.st-key-card_res [role="tabpanel"]{{position:relative}}
.st-key-card_res .st-scroll{{margin-top:22px}}   /* 결과 표는 ⓘ 아래에서 시작(표 모서리와 겹치지 않게) */
/* 말풍선은 ⓘ 위로 연다 — 아래로 열면 차트를 가렸다. 탭 칸(높이 고정 · overflow-y:auto)이 위로 나간 말풍선을 자르므로
   ⓘ 에 커서가 있는 동안만 탭 칸 · 결과 카드의 넘침을 보이게 한다(탭 칸 내용은 500px 안이라 평소 스크롤바가 없어 폭이 안 바뀐다) */
.card:has(.ib:hover,.sub:hover),[data-testid="stElementContainer"]:has(.ib:hover,.sub:hover),
[data-testid="stVerticalBlock"]:has(.ib:hover,.sub:hover),[data-testid="stLayoutWrapper"]:has(.ib:hover,.sub:hover),
[data-testid="stColumn"]:has(.ib:hover,.sub:hover){{position:relative;z-index:90}}
/* 단, 조회 결과 탭 칸 안의 감싸개는 제외 — ⓘ 은 탭 칸 기준 absolute 인데, 커서를 올리는 순간 위 규칙이 안쪽 감싸개
   (차트 자리 container 등)를 relative 로 바꿔 기준이 바뀌면 ⓘ 이 왼쪽 아래로 밀려 커서를 벗어나고, 다시 제자리로
   돌아오며 깜빡였다. 앞으로 올리기는 ⓘ 칸 자신(z-index:90)과 탭 칸(relative)으로 충분하다 */
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

/* 원칙 목록(「분석 원칙」 카드) */
.rule{{display:flex;gap:10px;margin-bottom:12px}}
.rule .ck{{width:20px;height:20px;flex:0 0 20px;border-radius:50%;display:grid;place-items:center;font-size:11px;
  background:#dcfce7;color:#15803d;font-weight:800}}
.rule b{{display:block;font-size:12.5px;font-weight:700;color:var(--text);letter-spacing:-.2px}}
.rule span{{display:block;font-size:11px;color:var(--muted);margin-top:2px;line-height:1.5}}

/* 순위 목록(「주요 수입국」 카드) */
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
.js-plotly-plot .barlayer .point text{{animation:barTxt .4s ease both}}
@keyframes barY{{from{{transform:scaleY(0)}}to{{transform:none}}}}
@keyframes barX{{from{{transform:scaleX(0)}}to{{transform:none}}}}
@keyframes barTxt{{from{{opacity:0}}to{{opacity:1}}}}
.js-plotly-plot .scatterlayer .trace:has(.js-line){{animation:lineIn 1.5s cubic-bezier(.65,0,.35,1) both}}
.js-plotly-plot .scatterlayer .trace:nth-child(2):has(.js-line){{animation-delay:.18s}}
.js-plotly-plot .scatterlayer .trace:nth-child(3):has(.js-line){{animation-delay:.36s}}
.js-plotly-plot .scatterlayer .js-line{{filter:drop-shadow(0 5px 5px rgba(43,110,246,.28))}}
@keyframes lineIn{{from{{clip-path:inset(-20px 100% -20px -20px)}}to{{clip-path:inset(-20px -20px -20px -20px)}}}}
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
/* 상세 조회 — 분석 조건 설정 카드 */
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
.st-key-chipfit_js,[data-testid="stLayoutWrapper"]:has(> .st-key-chipfit_js){display:none!important}
/* 안 잘린 칩에 커서가 있을 때(_CHIP_FIT_JS) — 말풍선 층을 숨긴다 */
html[data-chipfit] [role="tooltip"]:has([data-testid="stTooltipContent"]),
html[data-chipfit] [data-testid="stTooltipContent"]{display:none!important}
.kpis.q{gap:10px;margin-bottom:6px}
.kpis.q .kpi .v{font-size:23px}
</style>""")


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
STORY_CSS = """<style>
.mk-mark{display:none}
.mk-card .ms{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;line-height:1;
  letter-spacing:normal;text-transform:none;white-space:nowrap;-webkit-font-feature-settings:'liga';font-feature-settings:'liga'}
.mk-q{font-size:15px;color:#5a6b85;margin:2px 0 10px}
.mk-q b{color:#1d4ed8;margin-right:6px}
.mk-msg{background:#eef4ff;border-left:4px solid #1d4ed8;border-radius:0 10px 10px 0;padding:14px 18px;margin:0 0 16px}
.mk-msg small{display:block;font-size:11px;font-weight:800;color:#1d4ed8;letter-spacing:.04em;margin-bottom:4px}
.mk-msg b{font-size:17px;color:#0f1f3d;line-height:1.55}
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
@media (max-width:860px){.mk-cards{grid-template-columns:1fr!important}}
</style>"""

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
V2_SEE_CSS = """<style>
.see.q b{font-size:15px;font-weight:800;color:#1d4ed8;letter-spacing:0}
.see.q span:not(.src){font-size:15px;color:#5a6b85}
/* 차트 출처 — 오른쪽 아래 「?」 원, 누르면 아래로 펼친다(dashboard/kdesign.py 와 같은 규칙. KDD_v2 는 kdesign CSS 를 불러오지 않아
   없으면 브라우저 기본 「▶ ?」로 보인다. --sky-weak 는 KDD_v2 에 없어 SKY_WEAK 값을 직접 적음) */
details.src{margin-top:8px}
details.src > summary{list-style:none;display:grid;place-items:center;margin-left:auto;width:24px;height:24px;border-radius:50%;
  border:1px solid #c9d6e8;background:#fff;color:var(--muted);font-size:13.5px;font-weight:700;cursor:pointer;user-select:none}
details.src > summary::-webkit-details-marker{display:none}
details.src > summary:hover{border-color:var(--accent);color:var(--accent)}
details.src[open] > summary{border-color:var(--accent);background:#eaf1ff;color:var(--accent)}
details.src .src-body{margin-top:6px;padding:9px 12px;border-radius:8px;background:var(--panel2);border:1px solid var(--line);
  font-size:13px;color:#4b5b73;line-height:1.65}
</style>"""
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
st.html("""<style>
[data-testid="stSidebarUserContent"]{padding-bottom:14px!important}   /* 단추는 사이드바 맨 끝에만 둔다(따라다니지 않음) — 기본 96px 여백을 줄여 끝까지 내리면 바닥에 닿게 */

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
.di-tbl{width:100%;border-collapse:collapse;font-size:12px}
.di-tbl td{padding:5px 6px;border-bottom:1px solid #eef2f9;color:#44567a;vertical-align:top}
.di-tbl td:first-child{font-weight:700;color:#16233f;white-space:nowrap}
.di-tbl.gl td:first-child{width:96px}   /* 용어 설명 — 카드마다 용어 칸 폭을 같게 */
</style>""")


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
# 왼쪽 뒤에 있던 두 번째 자주포는 지우고 주변 흙먼지로 번지게 메웠다. 파일 하나로 돌아가게 base64
SV_K9 = ("data:image/jpeg;base64,"
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC"
    "0oMCUoKSj/wgALCAHZA0gBAREA/8QAGwAAAgMBAQEAAAAAAAAAAAAAAQIAAwQFBgf/2gAIAQEAAAAB80WUmw239LJVHNjCWWMYSUhhjLXXKqqo"
    "JXSioK1IZQzTRpWu8sz2NEzLK4IwrId2d2ZoSTCXZvLyMGtdtPVx1pDc5kZmMYqxIFipSEWqiBEpWuwUyCBWseCzRYz2uIudCKpCtbhjY7OxMM"
    "LK9jP5co0a663XtyVoj2l2JYtA8dopaVVLWiVqKa6lhamkspAZqTbt0XSRitNSqjQoCrNaxYsQwcly7eYgLvddovvroWuWWO5aM8hewrAYirWl"
    "dVdddVKWF5VWWgESOdl1rKWirTStbGMrGEtYYWglhLFn8sTBbfqvvtXOqiw32Fo1gBtsiAkVqStVFKivPQSHFSsCII99jhzLCUprSksSwEZldn"
    "KsSzliT5sxC2jVp0EUKSZptZgzAl2isWFVTOlVdKE581JhCiowFX03WxVjuCKwuZkLggxoXjAhrHMJHAUErfr1XlUAd3uZ7GkDRjI1gldQdK1r"
    "rW2jLStj1KKwDY72sUkZlMUirO6RXgjGFjGjF2gLDgCMJfp0WuBEe2y9nd4gLM0JaSutQpIqVkx01uyVJFNrNYseBYwFgSiVgQEozgmMYzlmWQ"
    "nglZFu06LbSZGZ9Ds7tWpdmMLQKqopIWFK6KklSopssAci6VhiagVWisBlAjEO0YQ2OxWEt54iqTRrtutaMzl73D2sJIzSEwgBK1LAiqLXVSgi"
    "G1HUtdalZaJQsZc1DQitWVmZ2gYuxYQw+dAWLq2WWWWs0d2vsjWsSWAEMLABaq40cVE0pTWjKzMyV26iqlDXkhK0Zw0iJDHd2gjMxZpDOBKoxu"
    "1WO9phd3vuZmeMWADRZmuz60WpYXVga6KK0uBe2JSb7nrWtUprUrXSjNWHBJZmgEZ3LExvPAh3a53saNLL7NFheFnIaedxemvXm5epsrrRAIzE"
    "1567K4CHgWaLTXVWwqpQIiIAA0LMWhgjWtGYk+ejBmsjO5L2W323uzmM1Xj6K/O7dXaW6n1mtErVKhHtRFgFRRSwh1O1dCWhM+WuREgAMZmJMW"
    "O7kxrDPOK9riFrSxNl999tlhLM3G83SPP4tvfGzV7OJWFqQSw+A6Pf2qEpVIYxud6kBC5sdZiIoLMXjkrJHZoWLPPOob3gLu7F7tF1tttgDOfl"
    "7CHKndg6Pr2CBahI2H5h6zz/ANQWJRXSLGaO9aqFZcuRLKlAqssY2GGGQsxZyWI8xGvsexjGZ303XWWWsZG5vzq2THz9XoZH93dAgCCHyXkux0"
    "u51JXXRVLGWF6lWtmTPnrsrqiI1js5hLQO7MzEwzyJbRbboNjsXstusex2JI8b5a8hadG+Q+71SLXFA878ufb2eP8AVrOXyZ3NZikIkISLRTXD"
    "WqhGdmJZnZmdoxMizzEsa225me+1i99tjMxJp8Z52wqLH1CH3HQkWtQD5PwD+tr8/wDS/N+SyY/b+6ChKnBsWoCuqupq6VkZy0Z7LbS0hJkAnl"
    "5ba9ljvfdYxa2+xyxh4W/590fK3UWb2uzdr1W968VuOi7X8v5B9Hqo7nz5Rn7/ANOVErR3DrWIqV01pShLFnDXvY5jNJJBB5kPfbc8OjRYWsut"
    "d2MJ8Q3kQOv53Jty7NXcoq6uzmdfiC30fy0Ts9nn8zAt13tfRilQVkKwEItdNVCGRizWWNY5jEyQATz0OjRYWssucvbbY7Ek1/O8vIzi30bcLk"
    "7exi1H3cWeZqr4FF06CgUaPX9uwqqSQICIDXFSnOsiyyxyzOWLGSQBR5920XF7LHssZ7LbixMzcPxI1cWt5T0PQF/Pem0d3Wp8Rnv9N4fy+zU9"
    "nQ0P6fWRCAkggAgQMlWVGhlrlmaQkmQELF4D2WzS7u7u72XWxmk+Y1cPq7PPqzp6a2LwPS5c9SHPxvYavK8e7pN6Vs/WbodAsQqITAAioWWvMj"
    "xrWEZ4JGkJBACcV7bY9rO1jO9j2OzHkfNOcvWPPpvPZ2mDznpOLxevpqwbGyznZZ0PpfW8zk7g9A0ikCSQUVV1tZYESR2rrLiSFgIRBAvBtuvt"
    "Jdi7s7u9lhPjvG8yyy3O9N3VUrMXf8tm7d/MQ2DLZZo7mwZcPrKNPpgqvDJJMtFYY7bKHsV8uOKwhJMAkiyNwLXvsdmZmLsz2WWPPnnmc9ixM2"
    "xul0ba6sFvkre5Ryo+yzJv21c+ynq7e+09VAskjAiitQYDlXS+gZCsZIzFRAYoZqTGKrCWZi7u9lh+acfBffjrl67elqoSji8e/uYubDbrXZq5"
    "d+rN2S3eu9PAFALSBVAERald7FClSpZ7qFgBEMrMLBFJLFmdntsPnPEWZ8lGXRYL9mio4uLkv63PpS7sNi13LZ6DpeZbB6Hr+mgUSQwSAKhCAM"
    "5SKJACzgAAyEUEkqoJMZi7u9p8B5rRZzwkCE6ctvPqy3aEQdLfRNO/N2+hRnwN2NF/oYskkkEMRYK0hYqpJigEwmAEwZTBIDCYWYu9lx+eYXqw"
    "d6nh5kyqoMsyAQGWdFO11eZ3cfku3009FF9XBJIJJJAihKwXIgJiwSGEySSYCAWhhMJJayzRVkKcjyGboYc64arq1dq60WFtPRvv1Yuzg4q+mu"
    "mL0XrpADCJIQFRa0QsZCZIZFEhMII5zIzgwwyEkvdq8154HP0uFRfVKqm6Vmu7ZzfOYrXt2JW7a+Zp16Tm9M+7oaX4HM6ffkkkAVURFMJBhEMk"
    "CgkmFeYWYyQySGQtfs8zwGonVyJXUKlyKdlXVwcmu3s356dXI6eWo675O62Qd3dx/P8AW9qJJJAERFEkkMimEAQQtCJypYxkgMkkBa/d4TMKG6"
    "rmzmZMejVzOX1T0eBRNXW52/m1psr1rqK7urfylpXr9y/cJIJBFVEEIMggJCiQENJJx2tsdJBIJAI1+75vup3G6/VzfM4bvReo8L6Lz2z13l6c"
    "HT0cR/OejevgezX1reYm7t1eX817Tl40+g9GQSSBRWikyGQCEACQwgScay24KIJIABG0b/JZ206YU53M3Z/N9Td6YZs3nnr29ZuZ4/t+t5HmPo"
    "R1POf0/nvWu0cf0lWPsepgkEgCoghkMgEggkkMEk4lltoUQSELFDaN/nMena5TleY52t+xky87Y3OGSJHW3Shrv1szbNByTdzMXW17vWdCQQSA"
    "IghgMEABgghkgk4lruVBBAkQBrt3j7ujokycry+RrTZVSejw3zRIb9HRDDkJU0bq543Z1U47OX9A9jJBBIqqskBMCiSAAmSCHh3MYDIJBFCm7R"
    "5nboeU4MXNWG6qivK/PfOQHhtU2pdnyCaKui1zW1rn+m+lMEEEVQoEMIgAEAEYkCTgXMWBMMAiqst1ePv2utNVOvVyut1pbk8dxRircSazlpja"
    "PRZvMVs2r1u4vSuar0nrIRIBFVVkUySCCRQA8JEHl9VpBZiSAAiy3d5jFrrVK6dd2TL0O2eN53Dp38/MdXS0V+ezRuh3s/lqbK9/0w7r4mfHr7"
    "5gkACqghUSQwQQAwEmKPI6nZrXZjIAqoLNnnsECKlYWuvboPLyWYNPR0tK8WBM8br9avz2NRo+iM2nNXXRr9tBIAAqqIIIRCJIJJIZIPHXWs9t"
    "ljGEBUVI3nc8EdaOTRUAaN6bUmWx1UE0R+tvXiYwt3Ql2kNds9B6YwQABFAgkBkkgkkhkgk8mxa226xjCFiKgfy2WI1kz88nPtq5vcy2VJja+s"
    "wylj077+BQz2PkvECel9715AAiorSSSCGSRYDDDJAPHYl16eldY5gAARTf4PPALnp51SMSnTqC581l1BjClm6V7cIapdrxU9ReXt6/0HoERVrV"
    "KkQAsXeMCqRpZBA4i8VWrv0WsZIBAFN3huazEsvMvTPrrxbXQZc5cAFbqh0NlPIt0y7Tz9KMtfU+hdmQKqqK89Wd7AXsAFsrQxgGK11npVW2VJ"
    "CBAsMAh8jx5DBOTWjk03alpyqpjKHakM9a6bW1zn6tq8/fb9V0yKEEVa0RWRjcCiuxkCsVgqW4EgytFpeWuVCzzvCQRZm571lk6uX03ajIiLXR"
    "Ucnnm5BIa2/fip2WKl236xbAAAAorStDJdCtjSKhisWUzPmroldt9jWKwZUCpyeHQkC8qkVtOj9L2abHdi0CmYPmnI4zSqwXqmzXYlur0nvZIA"
    "FWRJJVnDaQoUllMAjOABTTVgG6rGasxesXuRTzaa6hOAgrZ/Sen1G1aNHTuW1rHzeB+fWKyWJZJffYuvZ9M6RkEUBYK6hVZVbfBaikoIUuKQUa"
    "gjJZM3O4VNeK7PY1pIQCmnHyUSQ7TUiJJLTe9yFMzvnequxorGzV7T3sMgIVUrozTaWQ0gy4Zxc1sIpsTO+yLLLDFiStauPjz5aa2rqlGZMtNU"
    "uq1Xc+pApsUQMzNXHa7PYtEMt6n1nokwRUlirValblQLBQxBWtXljtKHyW7TYEmHoSRTGWqVZEo13C1ceXm5O3fotyTM1ea+Ymtx2MmDRlrlaa"
    "qaNNHou02q+kIeV2LbTUGWArapZShCqFkVxZUBdJVqKkhirxBosC150qroXTm52l9b2pl02CvUqxLVaxjRKbqqxpimlbUy03XaqrbSkWp7GLsU"
    "pstSsNQ4aybIAFGa6DPSy0y67I9uy5xEVwiGvNi6FcousNMouFaW1u2yVPdkiCltSXslJE2HBqFVVL1U2HTqlDB601lKIzDosCJiR8R3aa2qla"
    "1Rq2E03ORclgAAqyWOjUwVXtGrBSu/ZXCsfLc1Lmu/QiIyQ0oy4yj25BpvWpLdlSuM/bgixKDl1Vkk0trKVmU2WJLJLmYU3QNM2HSuRNeenYbc"
    "dptfGOhoOZCtFz0WZ414vz5rmNLWPlpbma70YE2tmL5vQmEKkMcFjII4CVZWpFNINfYy5tiattsAGcUVugQIl715U6tiCxTVaArmqytdFlb241"
    "ol7w0rUXqR7LRaNYLpYyBWvzElblYq2IWZNGQ8nZq0Uv4v0y7NOpGeV1rytFrUYtGmrS0p0DINtcwdFc1txGGvpEWXWY8Ntdt1q14lFuipM+2u"
    "r/xAAxEAABBAECBQMDBAIDAQEAAAABAAIDEQQQEgUTICExIjAyFBVBIzNAUCRCBjRDFkT/2gAIAQEAAQUC6hoECh4R6B/BGpGlIhEa2rROt6uG"
    "o0PdV0W5bnbLJaAhpSpAKtKRaneVXUekfyAiE1NCb4Pk9A0rUe1XRSKrodpSpEaFUi1bUWoj2bW9WghoNB0FHoOh0I6bVoe4PYpBDRoTQvy/5a"
    "hD3KVdFaUiFSpUjpWhR0PS4KkFWlaUhodGoBBq2qukohEa2h0V/KBQ0aEEzyfMnnoGg666AFWtdNItW1EaEaHQoKtSLRCIQVdFKlSpNHcIK/Yd"
    "7FdFaj3x0hBN0j833f46QgqVKtAFWoCA9g60iEQiEQqRati2Lb36HaDoOtIBAaV0DWlSKpObrXWPbHXSrStAU1BBN7Lsnd+itAhpXVXXSpUiNB"
    "odCFWtIhOC2qltW1UqRHQdKQCaFSDUdD0HopFUq6qVa17A9w6BNTesaAIaDSvZrpKOpW1EIhEIDRzURqFSI1IVKkAqW1AdBQ0HTerv5p6Agggh"
    "1DQIaV/APVSpELatqITgqVaHQjWlSAValBUqVdFa1ofaHvH22oIFDprUIdA9+lXtFq2JzVtRGlIjSkGoBVoNAFSIR0pUiOikWoj+GPetNQ0HsB"
    "DUIa0qVe5XVSrWkUeghUq6KQVJrVSKpUq0PSU7pKKHSOsezXUxDUIdQQ1HVSpV7Z9oqkemlSDVWrUNKVdDukoo9dKv4Na+VWlKk0IajqGg6B7n"
    "44SWmPio2Y2M9zxqfZKKKpAKlWg1IVaBDU6lEIoaFFHoKHvD2iFSpUghqOkIIIe5xHO5D8XiEe6KVsujvjwdwEefkcybFH6eh0rW+l2lKkRpXW"
    "EAq0KOlKk4dRVanpr2h7le2EEEOqlSmdy4i0PQERJewR7+bPcKg/xc0T5Clyp2swnVBJ6srGH6OhVKkVWoQUjmxhrg8EKlSIR9gIalHWkQnI9B"
    "6q9qvbOg1rUIdIQQQQQ6+KOqKQ9qaxpY2KN0Nks7tgfzIY+VE+EvOA4cuLHk+vAodFI6UqVaZ+XuzsTKaoZOYaVIhEKtDqNRqepyd0lX0hVpXu"
    "100ghoQqVIaAagINQCAQCAQCpVoFSbRTnb59ecYU8+qB/+RekP6JjyJBM023StKRGtaZ7XnCwoOfkM4UXDAnMM+lIhEaHQKlWg0vUnocUUFSOp"
    "1HRXRXXSpUq6LVoIataqVLaqVLagEAgFSpDr3siTRR1yv23SMDcYf5GrPlD3h9rM41HDM/OfzI890kcAgYsTMiyVWpCIRCpUq1HUNCiERq4Kkd"
    "R7VKlSpUqVKlXWAho0dACrSkAgEAgFSHXPkNjdF8dSGkfTwkQsZeo84nfH9ilxrK5GNtILgmYTihYjx53QZP1LDJvesjiETF9U5R58LnQv3KlW"
    "lKugKkRqUdCNDpehGoVdAVKlSpVpSpVpXTQ0pDQdAQQGoQQ9iZ3LhzYt3DWfHXtt9JZFRHRgf9boPTxkQyPLGtTTtMQMmNI6SJX9NxXhrzJjcV"
    "4ja3rKeXOC4ZkEwDu3UlX7JRCIVaFHoHVSGgVe4NAgqQGg0CCHQEPY4xKI8bLxxkYWLjTzv4hixYZEznOlMsLxkN3fVRlYrxKI5g8ZDxAfqY1F"
    "iyyswAWxBzdJHBjDl44DJGSibLjif9fCmZcT3SvEcebMZJdMPIaIpg5yc4xSZ3EKxHr8Pj5odG/fhjaGt2tR0I0GldNaUiERqVSrqpAIfwKW3Q"
    "aUtq2oIIdACAQHscdex2TxrLniiinenmWUY0zYZ/t+TPjS4mRCqKw5OXN2U0xfEWbuH/cHQsGbmZTjHNjKHi0sceXJm5GNhsycMjPyApHmTIUb"
    "hHIZYssZH78LOZIY3B/D3CNSFoTpjy3epvyTWOvlOUcEsh4Zw76c6HWlXtFUiERpWldNIfwRSJQopgC2qtQNB0DQdb3tjZnuGRm8UmdmSMgcnx"
    "kJ7GbMefJx2M4xNtbnSSN4hLkuQgmeGRZga8Ty4uHiM+pl4fS4fJJhD6LGevt+KvtuKvt8CmYI8lSvdHGJZWSxxPmkeGxKIucA/lgG9KT4wTHD"
    "Jz4+GMCjY2NvTXvEIhUq0KrSlSrWv4ICb1jUaDr+oh38XnbyXkuTTuW39OQ24atm2CFnPDaDB53LHfuzMf8Ady3AwYPfCc5rFzGrdayj/nWoz+"
    "o8Bpzcjct1mE6NKHcsjFSQRTuhwGxStmG1rg4dNdNa1012pEI6Uq0DUAq0pUq/gV2A0CA1HWOuXa7IOe4SOcCsZlQZD/0FJ2azwmRb3tbtGhWF"
    "/wBlnnMk2w4vF5WROmfkFA7TnNfkOLJGu4ZH9OsvO3Nm+BHeJ6Dwt7VwyLnY0rdqohA9linQBV0V7B6PwindACH8WtBoWoaj3eJzugxXPO00m9"
    "3bjy8o00J5BQ0xo9jdSsS/qAs5lqNQXSeaEJc+SOTu6QlOPfyJGUiNI2Et/wCPjl42W5rVnhjHRzFmQ/xE7bJQVKlWlKltC2hbQtoW1bUQijoN"
    "OWuUFyQuQuSuShEFQW1Utv8ACGgQQ9kaDQdHHptpkp4G5q/G65Zzb1FydotM8nmyCshf5CP1KvJWL/2j4y5d74lB8E5we+aZzzGfTa8q3bmvDl"
    "saVGGsdkPhOPi8UxmLJ4nBK4ytlZl9oyexIaMPLecrQ6D2H61qwiuye9rTuauyoXQUze3sn22jQBD3BoENeK1NnSPuSQofGFtzHufwwIaYTgU4"
    "sYQwFFrQm7Hs+nayfLfsxyolD8Mm6b2baY6kDelHZw/tPM4yOa5hT/WdgDWs3GG92Q3djQO5uKQsTDac33Ciq0rUuNHTf2a/uHJ3xVKuqkfbAV"
    "LaFSpEe6Nc+J+PkFoci3u1vd3Zqf8AFuvD/wB2TY6fwpf24WtbFO/bLmybyo1D+3kOs6i0IztPaNlNia4nEddtHfIjJEY7ReJX7Y8DM2Rxu5jG"
    "A8z3aVdNKltQCAVdJ0pVo1UnDvSr+UNeNPayGHbsG3fIQ1PPY+H3UO0gIrCfsLpwcj6hqmnaYo52iLLmBL/io02SoSiNGN3GOFrVP+069xZb5H"
    "bIMpvcRPDsSEzGXAZtcx8L5PVBDjFzojy4mnaf6O0f5I1GvHZd0sbi3SBm6R3dyLbFaFQ9k39w+ZSv9ZD63/FMRkCLgtwQIUDowhLEpnBwlJDk"
    "1u6B/qH5hKn4m2Fzc3FylOwxTM9PEGs2yE0Ict4n/hHoH8KvYtX7A6ghpnwummjZsYxnqB2Bha14jjei2Br5gBJo5BxB7q057ih5cPTXXaxh62"
    "d5aWP+2/tGFlZHIANyB+JKzhTefBP6Xu7L8Q4jZMr+tH8IIKSRkaiyYpmFmK5fSYxXEMSGKHKiMMjX7WWHiSCcv5GQuROn+lAgnluRC7K2re1E"
    "sR2rsqCoKkGKOIOfFHU5w+UmmwI53NpwiEzHNzI2zJ8IjDG03gkobJks5sX1UcuMxz9vD3v6CrH9SNR7wKBQXGTRf8gqCl7vzMZkrPpjT8eQKQ"
    "GxYRc5cyQJznWyV7UySdydLk2ZHVFIEAwnIhg2ENRbaa1pUbI3GNkG6OPFeo49pmh2Mgjc7GGTyk39QGNwWKN03wzCymNZRdlvbK+AFMhhTYoo"
    "l9Q1BwOnGnuZiwTuEeHkiU/3ATU1cX7yu+Q7MjNitzw7s4EyUUYi5GFy+lko4kqOJMU7HkCETqDH2/GmjZ3av9ch9Nd5tBQgtaZQpmKwJHtjkZ"
    "kGNkcUuzB37YjIXticInsALjRTSAm48cskrXyNAc4SY7Q1scFQTYscf12OuKTRZOK2S4OFjY/+5ah4kmOQtpcvU1rCgfU3xsQBKDS9skLGy5GK"
    "45H00zWtxpHSS42ViqayjK8GOWblkOKd2Y8kmltKhaXTPDxHHiSTKPGyg9rcl0T3ZAjaHYilyJnPxZXPcyScMdLK9QABFpCpYha4D5BhTN86MM"
    "oWxy5b1ib2yHFBUGKyL+qCHvtX/mWnYACCy5KdTI7L29ox6WrPie1P5ttMwduds4HkRw5XGMqD6HhwM+bk4kcEfJka3FMj5uXG4S4+2TkOU+K9"
    "YuOzkxYu/B+mz2LdngSvcxT23C49E9rph/h4rgZ28VdC2Lij+e7Fx3vnc3GxjxF/L5WNFLHNyHR5GPMnMZhQSyyyYUZx1Ph8PgDMRuUsiH6ZYp"
    "yIlg5H1EPtn+WNB74TU3xlxiOceNqYxNYntsAU1zqUvETDG7NHObxchmVxAZMXKiCjliY7FyoIclvFcNR5mMFJmwb3ZeFTZIXCsdGOArFdDAZO"
    "JdvubCc3iHNgla4ulfI5PysaUcRMTxhMmhkD5CoTM2ISzrnTJ+6ZY3D2My3g1zJsYPnfPi8N+ikw4vtl5zsUO4LmQRY/FZYc/JdgyR4fAW1D/T"
    "N0b/AameMunTpgtNaqVI+JXd84+orHh5gx21JyIw5sUboMtrBpjOp+WFvZtuh3J71atbkflsdLIcDIs4WQE3EygXMkhZBPNEhxDKavuuWvu2Uh"
    "xSVMy8qRuHlvYjxKRS5bZFBlviEnENwnMeQhFCFjSQxKTIxysDiMGOMTLjyv6YIfwWpppsnyja5N7IVo5SHs5Zjg+RyFqNz2EPeGmabbJJJIUC"
    "QpTviHyd58K+2gX+zBZ8G0274ldp2g8OW5Ok/TLrNq1hM3JkLHLltKcGc/IjDGkr/jI/xv6Ufwmon9IOUbhqTSc7sXG5XFOwHvJ4ZKD9ulCfw6"
    "cNPDZ0eH5CbhZFSYmQ0PhkaI/wBsD1HzSDVS2rwbNgkISPXMeua9SzyTL8thL1JCWany53pHyaBtDLW14G1+0c8OIKcXFbCTwBnLwv6UH+E1bd"
    "0d9w5A9mvRet68pyhkHLMwoyG8eYK2uHZNCmOxr8mRydQe+Eo3oNKVJmO9ydjuaK76BMFlrNrJW9ninL8mlhw87Idwr0faWtR4S4SfaSpeFSBH"
    "hMqfwmXa3hri3hOLyZ/6VpVoH+A1NNNyZRKm/K0XK0VuW82z4gWJB2WPbTdGAkrichtZHZQTJ0bZA7HcFscEI3FMxnFRwtZo9wa0nvrjC5FJ4n"
    "/dpOQWG7ZliVtc8bW5AXNC5rUZm0Z22ZWrGkHP/pWq0CtyBQ91qHdkofAtxJ3K1aKK8I5IYvuDQvr2L62NxZxGJhdxaIqPjMEadmRvRmiT9r2h"
    "lpj3RJk7StwVqwnSsCfkpzi4nxoFh/JOWU39RFAWou03aq7NFJxtXSNp3d3kxOvI/pmlDQaD3dxDXvc9WnFX2B0KPib5mNGNBtt2FbVIFy6DY7"
    "a34jzKeyD6BdSvo/GgWKrVqfu8dyUF4P3LIs8VyGgcWlB+7SV90TeLMK+5RkxZEcqx8Z9/0u1VoNAh7lIAKZ7CUSie27s09gneJb3AhdlEzZIS"
    "1FoqQU1/iMdl+Zvgm+e1dH41x/A7ulFKU92+aVdgPUWfqZLKZRqnLY9PFILhe9cNe5+N1WrVrer/AJbpWg89wX1b6bkAiOTemoKvYpVpSa1PG1"
    "197R8BNQTlL3cYwtgW5hj2oNbc5DnPTPB0m+ITfLoy0K1atE9lemP8W+XWnnuzzSpR+aG7OrlprfQ5R7nEN7xs5cWCxrcf2Drau0Ct5vmlCRb0"
    "9+0Nfatdwty5gXM7iRbluVhWFuC3BbwtwW4LcFuCfS5YToaQZHYYLDUB7VaUgsxoGR+V+ENALUpp7tpa0NDYow13hOaC2U/qudab8D5Cn0tbir"
    "V6kptAPqwon9mu2nInJaUzT8R+b9eYfS+1+orkqWw7fImOmrhLnPwvZIW1Fvd7XJoTeycKVdha8jaiFRKDaRARaqXfo8aUtpVOV0t4QDUHtsUq"
    "C2NW1UqVdVKlSrXiI/yT5R8fhNTfPzJaEW+kHcuyJFO/7O5A+hy3gJ7tx6xodLXMcidG6xC0T3yPVLX6rfSpEwOQbaKx2tbD0lXpehKCpDySrt"
    "HyPlS8FeF3XZUqW0LaEWgnatqFBUiFSLFtXjQHTeAt65idIQhNaM4AE5Lt7kHFA62rVq1xL5FFOR8FNPaR22NriCXlOeg/tvC32ZuFZDUzAy3F"
    "vB519lxLbwTEC+x4i+w4q+wQL/5+Ff8Az0aP/Hwj/wAeK/8AnpNx/wCPyKXgsrFPjuik+jeW7grAQIVhWg5M7m9reao/VO31L13u2HcS4OkULH"
    "zyRt2R+1SINon0mQJrw5hpcwKzXcq0TaC7FeFa3BeV4Qoo+VWhYg2ltCdLGEZDQle4EPc7Yjucmh6ET3hjVs7kK+wIVq0SrVq0XLN7tT/Lk/w7"
    "x/rO7urKJN2VZXDGCXMamoH2yp27hxdrQm5MW0Du9R+V/oCi9wW9xVpnZrHEIPNuemH0teuDQc3J9q1uW5Wvz6UXbE5waGFrhSrsNO7UTSB791"
    "fYeAr7fnwg8rdaL6W61ZVgouFNbafHTXviCLY63Fq38ofWxg/WxORy4SHZ1L662jN9P1rkMx9/VlfVL6hc5Su3NKITgnp/wHxJ3PPnshrwl7Ym"
    "tzIkM6EJvEoF9yx0eLYrU7jWME3jGIo82GRfUNCGU0oTtrnMsSNVqVwA4oWywL8Humo+T8W+XpgVesHvaBKG5zm70C4DAgGPje33T2runns0lE"
    "bh+aQsL8A9+y7LsjQVKu/g2USi/uCNKVIea2rYFsCbExq2NXKZfLC5QX0kd5+C6YDhUwX2/ICODOnY0jSIpFVOW4K0CtyLluGpRFiZ+2L8Wj0B"
    "9DmlGUrmlc0reVvK3lB7gua5c0puXM1HKkcRlvX1Mi+syV9TI5C2O55s7THsajA9bXIJ3hice6tEimVTdq4LAXz+xSpEdu4XrUj5WuilkT5KDX"
    "tIsAW213sWV6kGOvdSsItQNLmdhIrCHdbVsRBKokV227kTWrg1DtrSpUqW1FvZ1NG2k+BrhLw0Fx4cQnYUgToJGFwcNNoKMRRiK2uRjcn4rnoc"
    "OyHJ2FM1fSyLkSrky2MWe5IpGHHxXTAcMyi+THljdyn7dpVaUthW0qiqOlqyty3KtB2RkdbJpAi4oPbt3CvyrV9wVih0j8WOPEx7692n4pFeor"
    "siAFtK2ohUiEWhN7tLNy2Wg1wO2ltOlLlFbaQurfduW5wW9Od25vdyMjmDHk9L9gaNO69VOcGtfkObJfc9kDuBDkNysouITTacAQdoAY0l2Owr"
    "6drE+JlclpTWbXel4bGm2E6FjicSOzhuLpMUgDHe0QBpYGthLHByNgncGOxoF9HjB/0WIpOFYkrRwfHTcDGapOE4kxdwRi+xwJ3CsXYeCQEfY4"
    "UODY4U3A4nL7JIncFaGngpX2WRHgk1O4PkBfapEODWvsz19q3F3A3BreEyLCxTCpId7hGQmvLXuftHPQyQS3IDpHS2MeSUDc22krxobW0o0ESA"
    "mnct3cvW+iPiGrYCqCK7uVUthKp4VkK0dA1O7J5JTS8J24LwXQFwfTGs5lepc+lzu4dIX7w5hcGJslrmMXNYnTNahMHAP3J0m1cxqLmXI5oEbg"
    "V3tUi1bEIKRYb2ORe1qMtxskoteHuysdr19OQ84TyvpngcuYsgifHE218Wmc8uGT0yutrXblRLxtv0uFC0X07mEp0tIOcVv9IAVouTwEGAnYn0"
    "1b4iv0pW9qIAVNIHdOFosITGtc0AsEhsjbusRJzgxW2NnPtnMFMNNsleUxyLivB3tJtFvbygSDu7lElF7k2RcxGiXA0LKoLcFdIFoQPqJrS9ey"
    "7LaCjVbgXUmspvLC5RTWlq9TU9sjUZXOQcZEKRj9IaQWcwJkj2oT+rety3LcFuRd37BNop8THLktXL7chrk9jl/kBNFr1PBY4BsTSnRrw0ytXZ"
    "62vW5jQ0tW0NJaHIxzsXOjczluKj3MT3u3tcHEv7GSNAraU5ia1Bm1PYSe7WRkpzGBFoCDgVuBT72gvRII5Pp5dnsUWgCYP5bd23aN1p55jQdz"
    "XWuXa2PqMubHznbhKuchISuY4ua999i604yVC+Ro5vcucRuFcxoQG4R7LeAUYO+60Fa3d7VqXIamzNLjNG2SXNDHOyJJCyRwD5GsQkat7QmtC9"
    "IRa0gMRa6hJaJjco7rkWD2O9qD0HWvK8LeAV+dPwyqc0EFtrYNroKcAQPKBaUe7RJZ3NBbRcGoWgSXMaxCrdEh6RsZW0uHqCY/uO6I9TWp26r9"
    "Q2lbLRYQt1EFrwR3avzQaGHuWhy5Yutq2ICkfUmta4FgRZRXqovanZDQ66UjrQIc94e5Mcx6Fg7/S7bQftX1fp5oco3bTzDW9qLW25dkD3oIgE"
    "ABFHSk6Jrm8ppacWJxMTKdjhyEVgRFbZFskTsXemQcpBr1y+7ouxbtQda+KD7NdvJtxDBashu5ttka1WhqIWh6I3AChSpGIbmYTWPLDbYSEYAX"
    "Oxe/LcQ6FyYxqaVImSUx8nZrrTraWvNF4uWRrkx7mDmOAD7RKNOHqCa5PXhNPd20mnNLh2aC53gte4Jz3pkzFzApNiEYC8gsC2tTmrlteuUwox"
    "sIlxt5OJua2NzU6BjJgHBxIItwTr2tiaW8llQwhi5btxHYNcEI+5jJRZsOlq9SLVFfjSlddNV0FEEosK3bnuBKqgO4e0E/rLdIHc4sWNPvBsIz"
    "zAyukTZqZ/6te5Bwq9O2pftTgi4lBbQqaE6gNokRJCa7eiA5zQ4ODWW5hKfEnRgFjjt3EG3E7lfatyO7aZNp7EWiAQ1x3EAP7oE009ntsO8Cnr"
    "YnRKONwRanNXgNmDl5e0hwCJcD8jKCAfIKcjRaA/cHFDeuZSa7cg5rmtpFraGg8r/bo/J/cTl+ND8iho1P0Kk+T/AD/v+IfnN+3j/tnxB8fyp/"
    "if3v8A1xf3X/sDynaDyineP9T+435f7Rr8S+IEfnH84/l/pJ+z/wDo/Cd5x1+Hfts8Yv7bfD0zy74BOR8/+uX8IVD5/wDUeWaf+snzk/dk+c/h"
    "RftyfGbwnftwfFv7n5d5l+KGjV//xABEEAABAwICBwQFCgQGAgMAAAABAAIRITEDEhAiMkFRYXETIIGRBDAzQqEjUFJgYnKCkrHBFEDR4QU0Q3"
    "OToiREg6Dw/9oACAEBAAY/AvVD5zoVeq1vnQf/AEM3TyUfSIHxTswpuP1i7Nu1FSofigdVquDuh0HosQm0BYbfdmUev1ec/gszxJKLW3F09zHu"
    "OXg4pvaGnNOGds7qLLhekANxGTmbVU9IPkEZxuWynx9lNH2Sm8/WS4wqfVFreJWVqIFzcrLZp3onCzuaN+WyGUOPgmy2jlqmS7emy7VasVt3as"
    "BFrgM2WT09aSCCxtAtpvmiPqfQ2WI47z3OTjBCDh2WW8ZlliK7jTSThapui+mYiCYQPq8ZuGMzi2IT2TlMIF2IyOiw8OpAxI+p/pD3uDYt5Iz3"
    "QGnEB3pjxYk91nT1ZwsNnaRQulF+G1mGTtQNpZBDZ96U3Ebhglz5JUMkO4H6nelipdiyBwju69lmhNLN1u6zp6o4bDGK+3ILcroF7sgImXNKhm"
    "Iynupj23aVkww5794G7qtbBMcnAqGazlnxMTKFDMavNQ6/1He/6IlYONZ2Hq9Z7pzWX2YQy27o9UBiNByi61TvUhYLu0e3VihWYYrzHFZ2jZfI"
    "CzuwuzcT5o4WBs73cdAbuA0VOxZA/UbJNcQwmejt1WiEWMw7X5LDz4ph3JBrGZibALLi4RYeah4ooNuiflGzu4oUuofelAt/ks+GJHVOabtdCO"
    "sPPQXPMNFSUCcZgkSJKnDe1w5FZDJdyXv+SDQTJ4hOedyM6W4Rmd0K0Bei47Gkue2LbwnBvtXCvLTq7Y3cVGUyuzbVzkBw+o3o7Z1m1Kwmj5N5"
    "1nZapxD3AuvBUudmH2nJjpH6QiS9j3E5m6yjEwXfqtlYnuy1UNVhtxGsGUQDvWHaGlzp3mVhswsMMww6SQdpPaMXDADqAnKq4AdnvlemMPorjF"
    "Jqn4X8LhDOI9qjH+HlzuOaVrf4fijosZ5YWEnZO6mhrnTDTJTcPDfc1WJFsxTWZss705vAwnh/vWoqldmyjOCIX66crGFxXaYtcTcOH1GLnmAF"
    "2zdmBQoENywIutZwCq5vktUy7osuFiuaLxKg4LC7jmhGG4eEeJd+yDcTFbiMvqouGGYQDcIwE7Df6K9pO9qy42dkVg71OA84jpkNyrsvTvRJwS"
    "dpzZyqewwYP2Av8vhflXsG/FbEfjcsZrbA8Z3aHPbtNqF2+Utc+uZvFENHMyoBzHeVTUHFahM/SN0dIM5SaLDws2HL/wDr1QzvLulFDGgD6jPZ"
    "2rMzNoTZMa0gzUoAX0Zke5GWUHOEN/VZQq6HOrXggng/RKwZ+iEMzg2eJXtGeauF6R979tDKb7Kw4p2WA0nciV4aaLXuh2hj7ohZm4v9VrXUj6"
    "jYzzUSUXOhzTud7qkOhdU2NNdACAHc8NGIeUINEZWiBIRfiGf20SKFdpq54ruzICsldr6QJdu17eCys6aCFXTin3gUMzr27jh9RSWCpOXoneQQ"
    "lszzQpVGd5gJreA0Dnpk3PdoYpoLnYhy8FG5HWPTRVAy7J8ES2yqe5VXWY0aFrXcZVm+SY5tnL0ZnuuJClA/y91dX+bMLDJH0lDDQcUeCFKrDb"
    "uvosnZzrCw0hzMTLyXtfgvaN8ltt8ltM8kObUVAsO4c1WN93iVyHcMKIKsQg4NBjihizDbRvlVc4D7q1cSnRNyulMxN7Hgoha1AuyxMhadkj+T"
    "rpvoGiR81Ga5dULloui7cO92fCqbm3ndoqgWzVNgEtIIMp3G3c5Id0leC+zuULkpOiBZYo+ysJ+8tCqhjiBlFo/mK/NhDoe51aImKqE1tOKPef"
    "CwmvbmuoFk7NwTcoNRWSsO++yMWHcjh3S51E1OBOUuCzTrNQ56Apadfcryn5TUBZcZwyAUEIOAMFYeW+YfURk3JTnTvU8BRc0JVECU7PSlI46X"
    "GJTDBoCrFOFbJkzZYeS9e5GUjn3IXE6MMRTiq2WUMJzbxuWFG9bBQDmkRdfJgNRBEJ3FYrDttqEHs2DtDggeH1EDCCIQDap08A1Vs2qOivcdph"
    "BBHv1eJXtGpgYQaprMwI0OYCvRz9oacpIlZMR4B5iFHC3MJh+myESLG4UlNw3ZDhmgP1DxHmRPEIBOnin8SFrNlSGYEeKh7GR9iUQ3Z3dymm6C"
    "PqWrx0s5O/fQK34IuIlfKYLmO+kCsVmN/pbJWBifReqrkmPGUBlxx+oWu4BSTl3Q5WwlRo8HKWuykmBmWV+Wb0K5E1QLSE7JgucJuF/l8Rf5fG"
    "/KtZrh1CgTK2H/AJVY+Wi6v37oCUWTakoPzgqiacLEythGauaVmtyKbBE8U7tXNkRY3Uh29HDIo4VqsRrOoWXFlr4g0Q+XIbwTcr+0dMGfqFhe"
    "KOiywm7pTXgkOHxCgO3ypFSLc1KuVtHzW27zVSVtHzQyvEczKHykeCrjtn/aWtiYP/GjnGC5v3P7InssGnBezw1sBGWBR2dVVjiOqfqObGzrSn"
    "mlbBF+cGORWJjZ4a2m+qA+UjkUY31VQUxroyb12bdl1csIB0ENX2TcI5Q2iqAvlcjP3UsxG8aKx+CuNDS0+8mF2sC1amanE/PmEOSKeVVNM2Ub"
    "kZ4KFSFu80IbPivZlT2Tl7N3kth3kgIcFmdOUcHIX80FlG9U01NSgDiKWyHIjNMIh0eCwxhHMyTYpz2iPsuTSIkrWb5IOyT1JXaa2bqjV8dUKu"
    "jwTiC9oPinN7ShEbKg4n/Ra7g4jkoL3+EoNNY3kL2nwUYLszmnNCa0UgQgBGsfnxr8WQRyUghHMO5KrA8E4B3hCY3Nmzck5n8RIaJt+ya/Pqng"
    "UMPC9IOIfsygcR2K0IuBIcLwtt3mjLhldzQoYCkmiJOiyaGtJ5IODZBpSqcRAj6SaDGXjNkX4ZBZhiCtYO7J2+LoajmZj7yyxLM2XMRRdnGGNU"
    "3ohlwnxF8qLcTDJpSijEzN4UVj5KYRyjXG7Nfoomq2T5J+UF0L2b/JWWyUC4xzDFbBd+CFMa36fPbuiZtdFUeS2irgqrWlWjRDjqodi1/goOcO"
    "gwF745woxM3KizPOqRGbgnMGI17nWiqIeaFOe3DD29Kg/wBE578AZ5ADIoR0QlwZkPsnGKL3Si0AQFTKqU4pzznGLhiab1nwpGMW8S2qOpiVrR"
    "ytjhNa17srr1uvRPlDle8asCiwS7Ez392FhM7ZrmvxicsKYssoY2Nw4JrsRsmMkAc1mc109U57Q90CyDXYbhiWcie2JzGj98pr8drXtdbGAWRm"
    "KCXUWJiCXQLLE9JxCCGuAybinN7JxLveNwtehiweZR/gsLGpvOInMxhjtxAJ26IHtHhxsA5SYzChjfz+ey3DoyLKo0bu7kLcwNqxCGK1kHrML3"
    "56o4ZOI0H/APcVq4uIPw/3THS/M0+BXaHMd0xuW1ifkR/h8SG/Rdh2R7Z+C7gHYRoqD0Un7rlL8PCk+C/9f85W1h+GKp2v/mWo0ZvvhbLx4hFn"
    "o2q40LnGKJnIQvRmBrDh4UG9ysmI5pCwBg5TB3LtMlRaVDsX0Z34CmwfRbcStr0U/jVvR/8AlUYuFhuH+6sxNjmDYp5p3YMaT7+C51EWOxA0zs"
    "8CgzExi8mC5mXd1X/lNGab1WMMSNvVvsrNgYpLDSoNE7DxH5ZMgprGZnNa0jM0LtMTFAcCIaI4rEJN4/T57dCHfboJJTpaHNFJIkBFoY2XOcAD"
    "uhbGVzS0HjXemOwg3IZqJ/fRHFAqBhjN9KVBVFPdbBA3CV7h/EtkfmWx8VlxKTzR7LEe2bwVT0jE/MvbO+C2x+QKow/+NqluFhOH+2FjkBvaGo"
    "EUlfKYHo5dzw0fkcIT9EQtUwOC2bHcVnxM88iqHFHiFs9rP0wCtXDLPugItIdB4BO7KdW8j56PqBBsqFUKlri3oUQHGDeqaM7obaqnEJOiVPqa"
    "aL6Gdw6W7obCvpGZgLTNSPhyQYRAys1uZKaW4Ik5qTAvcpwwtncm6MZ3F8fD55d09RRZg5tUKtNYVx5okR4FUAPithT2ZO5eycpLXZdxhEaD6i"
    "6urodoZjv5dG18FtBQHQDulAZrc1IxHT1Uk6x3ralQsp2y4mPnkjiPUUTdF4UO81LSNOtYVW1lHALqpajN+9bvxoPcaz6Slr5g2hUxPghrAtPw"
    "W0EDmBqtpvmjljzWbOATysi5zs1I+eSUMrMvfouWgrko3KujL56GKHaKVVirKtFz0VR7g0nuYTuDgjXQK94Vr88kclE34eojLPivZu817J35l7"
    "Nw8VRj0Jw8RVZi+SJdmryVC7y0UVbLgr6Lq61Qqo+rYjx000lBYccR88mFrGe+VXfpA36Rocj646T3BF17n5Vs4fkhqYZ81XCZ5quD/wBlXBd+"
    "Zezf8EYzDqmPBaW3+ear5NmTx75Ta0VdGcmh0FMEC+hyp3K+qKvZT3Qih1TYCs1bCbTcrInDA5yvlLhxHzNUOR1Oi2AtgyrR/IEaT3CoI0gXhe"
    "95qpcFhxx0E90BU9SVzWue6FVN6pm1zlCqutfdoe7MWlNylxza0u/kRotpvTTZV9ZIPhCs9Vw1GUKgH8hiDn6jaoDRXEoklV3jQZN1hDh3R6mt"
    "1TRCkKD3QimdUIXur3UMo3KwQcW6tpTXPMmT6qysqaanvwFVWVD366bKujVRbBppoP5A98lcQFZWUkLZWxpCr6+/fJlMaqiBELKjF1rX56A0CJ"
    "O5MDIyxu9ad+il+aALa+tuVfvU07iqrWorjz0WWyrUVlCt6lp77udFPFWVlZbKClkYnSiH/j4ibr4fPkpPaH8SM9ofxL/V/MtvF817XF+C9vie"
    "QVPSH/lVPST+Rf5kfkVPSGR91f5hn5SvasPgUGOLa71mBGXuXV9JKqsy3yrlS8lEt/Rf2QYyM5TW8BHrKI0MrVV1I1uiohXRVSBp4qyr6y4KJA"
    "GXihOYTyUF0jipJFFDcvmqXV48VrEqw0V9SO+Gqiur6WBwoNb18IOc2YMXUHBHWdA7tKK+jqrKyqDVbJWwV21AGbvWW7klWKlyloHiq6K+rsqi"
    "NFVTRQqXf2Rgz00QcX4rbBd5IX6BHKMTnlbK1s/PkqOeEdY+RWqc3hC3go0qrKsKyt6kIuVu65znbS2ltrahe0C256BTr/lQ1yJ5LUxGnxXDxR"
    "ipG4Fb1tLaHnpxA0V9QO5tK6vZbvJVAKa0CHGruvrrFQFx0RlBaFsg8u9VVjucVYq3euFshWVGAdNGzGjqpiqBYahUI81GUeBVcPxVWFUY7wC3"
    "ydEH1RHHRfuwPUUOnVeVL3Onroo546Fe2xD4qtVJZ5tWxhH8CknDHINqqYgPgVRjj+FWOgaDotoqt67QO1MP9fXasLd4qSzuUMK6odE5lZWVxG"
    "ic1FxW5U01C3jQEAB8Vf4aKwqLn6qoClu9c72W0PNVVlUaLqhOi6pmWownwWsI6rcvZuQHZulbBUPEInOwRuJRaMJ1EW4jHNI4hZspy8e9bvVU"
    "S7z07wVtnzUhxPVV/RGWyVQfHvBrG5nHcms1W8eZ9TfTzQrHUKt1TuX+CqqXWtErcqFVtooVzVvIKv6Lf5qyBmnBbS/sqlXVS1cUc2c+FlrBxI"
    "3wi51BxWrbT/ZS42qsOAC08FcqZQINNHNVCtor+iy3RMKThsPOFZkcMqsz8qrkHRHJFK2UHIX9FDY8Fs0mqsqgNVMsK0eClZTE9F7rZ3QqO2Ve"
    "Gpwysi0ESq4LYG6KBfJYTMxUP9Hw5vLRCljI+4v9Rewb+IqWDs+QKpinxCqXOKydlv2gaqmI8HnVbWJ8FUYh8VOE8jkV7pHVDWrwVHiVdvmqQV"
    "XDJ6L2fxX0Hbqp2swwYQyk/wBFLcTNyWy7xQcctPgqO6QhBhQVO7iqR4p1CGix4pzfoqGbZsUc2JMbUhROiqurraXPoqyVwW8KIQmyoaKZJ5KZ"
    "KuqL+2jdo49FUHRGYEqwnioK1Y81rAnwUgUV/BZTUfeVZ81Ji9BmWtdVB6LaA8FrxA5qXCQeUqGAeSqFUrgUIDj0VJ8lQ2Wt8VuQ5rmtUieRVt"
    "NtEkjyUz5BSHFw4FQ+GvVXAmbgFEFpFbgKGOf0IuqPyngsvagfiU5m+a2hXe1QHCY3o58TW3ckSRCmhcK1CJw2y5DMA13Bah1uQlVGbwQ+TyhX"
    "F1CpFUdyGt5KrKL2jWhDerQpElWVReiki6OrXzV1WwutbyVHO4Lkt6irVBfvR106rwta/NQ2cqyieJKcwkuj6SdnstuSd29TPwUzKsfCqFyhQj"
    "9l/RUV4Ukyd63/AIdEA9VQ20AaKAFUbRUnRWVOstao6LVjyWWaq/golsogHwWsAQueiysqhUAVvijLU0Bp1aiKKmZRUniuKMM6VTpzTuC1sRw6"
    "rMIf0oqYbXeKqyBXet9VTyNUWgZOYbQpxaQEe1xAQOaqVSFWBp3IUU6KreeplWBKFI6KgGYISAeMKxCzAxydRTMcVIr4qu/goecyDeFoCEFwRJ"
    "IJ4rXInkFLYjiNyAzX3lfJlubmtVoI+iUQ7EAdvUNdq9UQf1QDMRsb1R0la+UIa8k2U3VCs0lxG7ijDYWySVvMXWqRl5o9o0feWbfEXU5JHNQR"
    "RBuYLVE9VrNcFEUO4hVB8KKH5qc9EGI4KMJ7GnyW4lfZ4BUYRwqssV5rITrDfCoxsfeUtoRxVZKtCGYYg6qhkjmjljxXJapbRawRjVPFXEo6vk"
    "iC11OJXNf0Wur06KXV6KkSor5omT3Lacv7KDNFGbasiBrkKcFoy8yh/ENy7plaxhEV8tFHdKKHOklT7p4IwTHVVcprPNUIzQq6x6qihwd1WUl7"
    "Z5KlVs6dZw7t1SumikCei1w+FcrKHZi3mtyIwwDF0ZhamWvJDNGYcgum9e0GVU2uLr+CjfwhUc6QhmM1uVqgM8FINFLkJbP7KjTCK2Y8Vv8ABQ"
    "4Hqoouq2LcdFK8lYT1Ul0K4hA2+K1jXkto9NHFbIhE5SuHNEXCoqXW4caKjp6KJFFAKvPUoarTvG4psug/RCpkp8UdbK4c1WY5cFJPIBDVVviv"
    "ZPTSbHcVz5Lj4KjAg6oOjbhajydNArISFvVgD0VQ3ysqtDlPZ+ZTRkAjgqud5qCQ7dULj10CyEusdyDWxBNKKpb5La8FdTkJRaP0UfBawytshu"
    "6qf3RDpRnNwQpOiZI5aL6S6s9dBBVBpseqLmOcJW26+8K6mk9UD+huhnhOh9OqBJBKrYKZMhWqbqXPLK9VevREjyVYVaKBixP0UBmzAcVJAVAr"
    "LWEKhotbwVQFQHrot4r+6lZXAeChqugdyjJCgCVuClo8FUCVLgfBUcF+7VWvMFWDv1CO9SQ13gocAVBa3Khisz3qE59S4oUaOoUZfipaOq+U2r"
    "XR1AFqxVbS2vgsrrcVT9VVZmX/AF7+0Qryq37ltNNFO7SiklFgfULaK1Z8VXMpbSFQSEIg+Kd2sBFxBWqVGQ+CnO8coQ1q804tq7eFQt4Kumuk"
    "6pyjeqQiJDSFrD4qyg0myNNVAwKcFMiimhbeizbJHvKc2ruU71z4KrQtWR4qqFCoqOaMx0QpCjLo1vNS2yrI0UOrwhSVevFfsvorVyqM6kGdFD"
    "rKsFUX91Kn4LZPWioXKZVKhAZaqQCUDlMozmbXeuqmi1bcyt1KL+yiD5KmUo5m/DR/X1Y7pTe+ENBRRTuhTOixeqC8UxeCHVeCxkEO+UE5BBO0"
    "P+6h0TEeqC8dPiivBP8AvaCisT750hDQU5eGkrwQ0u6IdUEE3QEUEEF4JqHRNXih0RTUV//EACkQAQACAgICAQQCAwEBAQAAAAEAESExEEFRYX"
    "EggZGhscEw0fDh8UD/2gAIAQEAAT8hg8JCVTBK43Q/inbcEzBl8qgQ4GD9LuZlQJUFSok8ErjTxJDkqi3FjCxOAjqXuU3DaYah7m5VygNUdOF/"
    "aB5mkq4e8xZfMHjLuZJjFXFVHhzCVKVyWPI4Di4fSQZcHgOUhN8DfFIJ6ZgFGpmrIOTP0VSoIcVA4dSuA4VwRgYioazEjBKZeX4EgxqZRLhwhO"
    "4YiwzKpuPmV3LlXqCD1LVM+4/oK4vFPEW8X5mIM8C88FO5WJ3wI5B4uEr6O5XIMck3KgcBDA4c5HBgpRlfQEGVKlcVwkCBfLUSVKQI8JhhgRj4"
    "TXKTCXNzJKuJL1cGMzWJGAm+ZhLxNsQGZsZl5ChmYypfBBfMVxtxTsjn5leeFWSmVCFVKJUCVD6TgOCBwZ4+ZZyDgEELxzDKRIkI4QfRXAcEhA"
    "4GKlcKrhnUfoxTgSCNw3w8puHCplPAlI/E+0pwpDDgYxB3AvFwrhPEc8YcMTMqDxjhScBMJXLXFSpXBwQgTUOV8MN4mEeeBwNHiZhjGJAgcDDk"
    "1yKicgEZUSVKlQSoEZwfSRGOEcsRRA8moolkFS/ESEFTcQ8wiyVkCawxBa5EcMoxk+YzgxCF3HwlXOoa4vj2nUIcHIzEvgSuTgHBCuFVyd5lFN"
    "2uOnFXyCoMwwOASoErjKBDh4CHE8KuFcGXzaJKuOMqlsYIY0jw4YbjlgU54BiPKTCBUBUrgQGBLTJGOZiQWRoyk9QmOHUy4EJ6T5hqXDlOBDm+"
    "F4XgmkIWKKDw8VM/QByDhUeD6KvgEDkQQKnUFx+gLklY5usyoOV1DXAQxbuEh4QqBLmXB39AZcY6sikxjubJpizTLjGDKuagwbhzUqEIZhFhLl"
    "8jioxzLi4uHjqd8DhpK4HFR5CVAlQIfQIkqOIw4PNNJij3xasDhRPHwy3XL2gZlczBhGkrMBhM5WZioio4JYi2RJccxHgl4i8rh9NwYcjxOSVw"
    "4ly8Qi+jD6VQm814OSRIkIcBK5OUjDCRJrh4rxEiS7h4YIeFKjwaxws4WCCJMsOKJUJMvoNz2hVKIuZVyoalQaizcEIsJTAxwR4DgHLxUqEuDF"
    "iwYUY/HE4GuL4IECCD6iuQivrqVKlRhJUOKhLFSuQRGJAlvMFENysR+iGBBGScJiHE7jCBDUyjvMJ8w5PaWcnDuVKncPqVwHLwXipTcCTWEOSp"
    "rghFxqVBAlSpUDkeFSpUCGSzJqMqJHgwhCXU3HDDgxEM64dSocGTgk7g8ylSozvEgWxCaR3wS6mcEvfGZuOpuMyl4FQLhiHNSoQ4qBKlSuFSwZ"
    "QJtKhyhgQOBL4uDBAhgSpXI4PoqVE4dviEhor86gIHI0asNf2EYxg4uE6huUMrg8qqxE7hLAcAlcW0pNS8EqJnhcWZcQxwYvMXA4Mkx4fPF8Er"
    "jcqVyXBKhxUqVKiYh8cRJwCuBCKXBnUIIYMwyuA5ObPJAuU+IVnWTweo3JHaZfVXm4YkH538R8cF/UtIqkeguVfNiRIIxiq5DxUrgkbsBXAEby"
    "oQZceBniIT6A5BOFj9BXAlVwe4HAODUIR4qEHBzUDiqlzfURgoQl1BhDgxBhfIeYQJUqEEGx0x8yyBlKy5zTRcfuflxwTLZWVXcB2oysn5mCTl"
    "ml+JtJ+5NJabC2Orax+ovVoxLHeUqJBGWBGK+g3lNe5YOAScAcMHmrZUOZrBzHlrMqyPhwHh8TvMYM84jmVLECBCEqEThIQEr6SHAS3ChklY4B"
    "Kg+kfUwQJUOCEqL2/9954gsq0GWSnEFvl7lBsAnCFLI7uL+DRTe8dQCzP4L/5BizBlzKwciHbiosIpS9KCAaMSokSVGBK5SQot1F7rLwnkgcVe"
    "oPAKF7mv0EYqCpuViHMrMrndx5jxcuP014ixcLhK4F8agJqbOUgQIHASoHAIEJceDWESHIDkqWyr6tBIYqDgiaG2SK2tV/fBOpQKyRjhiYEqQ0"
    "8lQMGPAtwGWoLl+I60M2Q2y8Ncg5DUu7aDxUYSPAqJCKlyNiGt4l5VbFnvUGwOHKaSHViy3EqVHkCQWwKgxDgqjizCbl1wDcuLiZpdlrjhMIRI"
    "cTuBwq4FcjgOFSoEISoQcBFSpUMIRvKwmyCz48bS0JFKJj1ChJhBA4qVK4xIGg9A/tjnpd9Nn0KvvnbfB1+ICjZud/QsI7HrzUThJUqVKmQm6U"
    "v1H4wvSXeYhCzSOnqAjZ33vz1/czsEt3cEifQAScTKgjqMqJKgiQQnhrMNcJAjEuBhuDCGJuVwQjwEknEQcFSuaSB65tRIGOCtMG406geoQP0Q"
    "ECBKlSpUqAyw8BmX77hrDX0OqWcwplxzYsHlgVl9Gufo0qVKiROGVww1uunkbgQqPvAryfUGIrGR/BKVbLBdfiXhtqjs7IqEZY/3dSm6PsH4gN"
    "v8RFh+6aIKo/bGaKHX3K8E41CYjEi4BKrmIkCCcE4YvUCahTKcCE3yEEHGH0CuFSubu4UMcMT3hxOKheRUrgYIEqBxXPvpgarJf5v5WHDg4X1T"
    "Mcvt8MRsdePoNkd/OyuX6ASos6ydy+oNaIqh2TGGZdhdma/uebIqjZ4i3/LaePxA1orKbHTbvEvuoNH+h6gimPJehP3iQyLKKo7LjLi1wWnUIN"
    "9TRHMTPDByGE6g43BleoJUPXG4QgQIOASuKlfQ8VATHA4h9EHAQ8BAghgQJUCVKlQziIfjuXi3ihnB/uZIW9a+6bWLvxmlEkWsKPBcCej6zKux"
    "GcoyZjiDIMtRaQMpewl2On9QXuVTN9aQi0QrO6IoQoYUGOB2FsdEI3lgrJ1XO7oyp1KHVw7Af99w7VKMM0sm68y4WnPtiQWg6hqK7gvogJY92W"
    "E2Jh6W/ivxL8XVRps3J0igsoqzVP8Acv6fayqjHkgY7Z6HBEgjPFKglcAxGJK4pHmqRGGfKecOSVMpkmECBA4OAlSvrWGMwfcCniEILR8IIYYE"
    "qB9AAQPoqVCPs3arFH6jmg8jywDDiIWqb+ZbAV1S/wAsqrHlIIG7que6ZgR7sKfklSXtKQufV4yRQFBtQpdwegJ7SDFt/jCP4qAw5CvtZcx8gq"
    "nxXmWKFhYb+ZTF/kMo2LCBojQ2Kc6vB4PUB/5v2ghoeXBN7JivWgvHxLOANapo+Ytq8D8y7hbVuo7atvwi76KWtsh1faNwxVNUt2w+8IlPDr0S"
    "YCqPcegsnr4hKJTpNf8AvhLhlRgIx19NcJEgjwqiJxDgHASoQJUIcEqBD/DUZgdXDsYDuAdMw74CBAggSoEEOFQ+k83eYdIrmc2dQl5Gj8pfoL"
    "1mY696UvhfZT+5miODCUfx0GJuslj/AJ94I0sCgX7iZh2lRx3IaiBPGwTfiaRho9pUrjsSXNxCUbP9SkYBYw8n4cek/in9wEx9oP7hTocMujt4"
    "dmgs9wQcqhXtMmDZgHtmm2WJ+j/cLXOztMAnst/+ItjlZcw1Mgdo9Metwvb2i3NdmCemZnBGJE4VNyo8VK4qJiMCISziZYMQDFm4EIOAJUICVx"
    "X1PDyBAIFwkIVUCBCHAhwIIHB9A3mEQYHVifGv5lx83UFNNkGN+aJZoIRxKRr2uXwk+YqQo8EYbK9RpcVQVHG1WRdnmaF6H8TPju/UG8HYLnhb"
    "7YHAX4Z+IfwhlKEzK2jeYn06KdS6hpAqNymIjcoZrBWFVnCqqN6qgqhdVfzqa/qac0hwPDFhuXNsjwSokeVSuFSuFR1GVwuHNOHwiY1PVyqnWH"
    "BUr6nio8MZnxPREol0YJaFWIQ4EIcEI4MuDybm5AnyXOkLyzhWPUYbK8X4lReFV/bAOo5J3Folq9oxje4AigKIY41m75x1eWZ3+yFPjqxo9xIj"
    "uvXpEPBGJUMiYlH0FM7Lz8xc01A3cMg8uSwr7LmNqxk+Jn8JVAQhsRu2oh3fxDwIGviopIFqw2zY3UuDGZ/u/QKlR4JAlSokqVyYSuUQIcgjAl"
    "SocVK4SvpZ1xUTgpDPAPJG6hQzAgQQhCEIQhCHNzQ1vbuWNKFhdoLF4VK0/wAkzNjBLqtz0mHAGl/KacWh1+o+lkFy+auKrlARhrco2M/DcyWH"
    "WWJmWKsEYJecBXBoWZYjaLNqWMdRvs0z4DC/KPgo2e5a/JZU6HLYjLAfXm47Np+eob+aX9rTCFfHCsolfETWuQ9XFWVlTy1w6gU2xTti3bK+Ur"
    "5RGIFtuI4YnplxgpWJX0VHiocVEx9NrnxDiYHKoHBD6BwJtDkhkA17XR/cAgGx8pcLV/5gFm1+0U23bD7x3wPzPgS5844NRrWSB31UwTs+XbPV"
    "ihpvmUiq/ZDRv+YddNjHUsydU3Zs+YtRdVij+V6mVNBQGgmce+SiiudTvR4q4f8AkEZrrRsYmLDbceFShDRRnAukVlxTqi9RVXbPT/8AJ5T4Ze"
    "Fkq4Me9s5+8xB5LEUqYlniYmJiNRZ1EiXwQ6IaLjPMcRHuFJjmAzDHZcJU+gqa5rg5lcVwE6lSpUqI9MDiMIErk5OB4EX0MbAp9jf7ZhNenRMt"
    "VgzCbPDRLD8JHY+ZpMtbe4KJ3M4MhX5hwXVBNhiru4YuAbzLZoH4g52II1iXEaWEUUf7RZTSKAiz6gaQIMUa8+Jm9F7mSXXv/MzEybbnR11xZj"
    "Q/8JgW1/U9i2/EDy5fOmAlCzwyhKr8z0w4Ywly5cuXLjM4JpyTBNajKwQg8AqWCAY7UqZcagRhK4HMqVxXLDkPEr4J6CA8Svjhr6DkhCEPoNML"
    "ReaV6jD6sxtH6irClaErXxbGKqdvJlFLad/aGiDKlo1F0QOA8ReMXuo/kS2OomKhLAu5XF1nuLNov2l8HEDWJcGZsQbbQsIXIaVxAo9tVxVX4K"
    "1mZLOWffAXjR4nTiwBye4ML9j5jUrcHO5S2MCpT9oAEC8xKavxdypX0MqVK+hOdJUTEqMP1WklcCBFXCKgzmJlGnIkJUqVKlQ3yb4Y/UcEIPI4"
    "+cE9TR1qla2ehMoN92Ihg+Ja3bqU+Rn3AMNMzWG4rYxOy8C5dGr2VNQYyANeooNp2PJHlxtAYI6TzsxRHcJuvazFe0I7Gt8eURmZuSy6KJudPt"
    "UBM8/DCLHYViMqp6Nx0S/TNNitp5mIcTus8fxBs3yX2+jxPc64ZLNcP019NSpUSVKlRjMTECJxceKlR5GGUVvKXK4qJKKlQ5OHnRwcEIcCHA4x"
    "9GoIeiNfNwKXf+RBt1MI73llQKhiVDHJ5HzHd/UGXzMXBvp0XyPeUQtQnlxXuW8uIPYF+pQ/sjYV6TKlujJDcI4tuHSef7wlQW4qZOGy6gtoac"
    "T7ywK7Ih6833H/AMlq6/OeYCJQbZqvGufoqVK+upUSVwwRlcCMbd8VKlRJUTirlRgSuK4VAiSocXwIWd87+kQYctOB6NLkwSheioVurh+J6GCE"
    "MXw6lBYuyn9wwlnav7RNVtt4jGWlysMvyYryyntYhWzmj9JLal3zrFS+Y0uDH2syL/8AIRfhlZFa7ZCdjHtlRoFFr8kpdd8joc18R1TitTwyl7"
    "VKHKlH5JvuCnlX+CpXFRI8seCEX/AkqV9SfWWX/ivkYMGOawi7HV9xyAWpwZsV+EjriB2q9ixhTUdoqLUW2wO6nUAd/aM2EhSmOv8AGRjApPn0"
    "gKwtAbiOzzW0rcj8qV2lCR5Y6FT2RPOeyeyV8wGMK9sKmoIPWqukq/MHEUq8QWVxyXcQ9Uc1t/4hNK0ujMIpxeeLxqYbKgz2/wBSpI1obgCrTb"
    "StrByWqq7rxDsOAtb5mVkHlN4Vl8O6+30IC3BBNJzUripUrliRjGVni/oPor6KiQ5uX9OUeB/g75uXLmaZprKH6/pHDMcEtqzGUNO7MQGB2f7P"
    "UcOWZNYSCp9EMMuw0WRf7if+xRwyr5x11V5Y+pT4wlgX8oRD5x8UDub8+D/5j7Mw9K/UwpzDWCjb7Ny9n8ETQ/iYQitS/wBWHtPxKrMM5YJlr9"
    "hl+RiJBvgzRGO3FV/1M1DsP6YFqwNpRLXGaDqMYhrMLajB04hSU0WQTXuLRQoPUucGhJVttWrgyV85Iui1oWv+sLKccKW/uWX+u39wIT83FDJq"
    "fpmM8l8xeACOwblf4GJEjEjwkqVElf43g4Dg575PpI/VeeFFNZ8UX8w380wQ0RMjMEtS2vMS/d+nzDKmn33Mlow0+5Cf/NzzkLwHiN5g34myGA"
    "q7OsptRNWqRlY2NlR3H1bRaqX4JWM+XxGGRlvMYOFWHVDN8QyJm8PeZaKIKKKhjAo2zAEfKo2kkcuZrWNbByGo1f7EoAeckmaEaIm6BrfjGIfh"
    "D/UUK4Ko2/U2ks1lAlXAJlBo3V//AFOs4WoQv1MWpvMZjiK8ms89PujDVgHXbN/lnGyaDb95x/z/AI0jwkr6q+kOHllf4LncOKjw89/Sy4Rx5M"
    "xRLGhUwnL6WNO9LNmE+ZWL0SsNnS/i5ij4MYeSw22h2OzNAPcoLGsYfBC33r9PzFJr/vMuHLQq1KrL44X7rqUwQ1GZkaRN/iWxsguog9Zc72pZ"
    "uv5mG7Vxl1cAqx4eYvpArF1/qogBt5D7JnMg00fMTa4dVurlVfEOVP8A7LsAeQPmFEMsQUI1tGlI/eKjjgVY+YPl3bV/Mebr+UEH8hNt9nd8FR"
    "DUPW8yzYp8pX+JuswbMDO/+HMC0EyX+JaX87+pjOPekurdH+NiRI81KlSokqMqBwnD9FcH03DgIn17+i5eYPG/yI/VDamPt+YwxUavM/1zLx+0"
    "QjEr1O7KXY+PUTTPd3+IgqgyDZGTmd2XGohBu+AfEpb90tLTHu0pm7mP9N4vEYDxq7Uu/P8ACAqawCjuKdYFyPwZhmp+JkImMk9p+I8sCdOmGw"
    "9KsYa1c894q57ktoyLNlv5i2LA3l/qUCAsGGULN/TqjeJgV1FimTxLhUBszGW/vBwp7U9zFUY0HoU6jL7lUvLzHCXmzmE8BtiqyMFh8j1FXBiN"
    "PwzLBc7379xDJgBZfmU8gdMvXUsMcd+zT1cf7Kn4eoeK51j+AxGsHTgfuU7CF6vUZXMrG/VefH4ncb8DCwekf8bweD/DXNcVKlSpX1ZQ4nPf1M"
    "uMWXFHmZ0dMBwoV4yoP0wDnJ8y7JYlVqTCalWTJiZzNLoO9G0vc3UpFe+v8TayBAbgbafwgwVhyX8hLT7dFt5NXLeQ+VH37Av2N69S23mKF90v"
    "Wi4N36lJ3yWf1Bux8F/Ua0RfkHimhU3z27Ur7MQL93D/ADLgmCBHpBYCi29w5IQxvsuNU7CN/wCoIJPbXBUzMOsG347gVh3kv7lawpsmf7cEPf"
    "nj/wAzC9COvxUD4dHVPFdqmcnwBb/TKW5cvaT+mJjCy9ruAEpcKXDHZK2AXaV6UY63LDiwA/ls9whp8b/MvAKWlXVX1cANNbYUGffxHaFW7f8A"
    "jseT/JX+GvrGdcXjP1MXk4qGhlWJ1FqDRHoTXMqRYibP3HmFUQNUTIlBMsu6Ny9jfigHSajO+4RzZXp6CHWZomVPcXiZRGo+IoCtMt/iOCXmLR"
    "UC62D3L+YLzCxDf3QwLsjojU0j4E7a+BLkI+T/ALmfieNpkEjbLgWmaMp/7Nv6h2L/AM+Jh2H3/onkSE2kWE/oRS5pndKC7+1z87gIe26tFxiu"
    "nYF/xGk8lYf9RtX/ACQwNhklR8eJdqpkcN/s9QWtB91V51A284YG/wDExIkr/wDUEJcuP16lxjO4RSwfBcSvnLHu7JgzECXcVcJ5t1KQkjTA/e"
    "M21X4ZY0JuiHE2U7XEIvB8VQGjNX1G4gUYEGj5i/tLtoYaaPnnaHrcUadxdjTE1p+ZYKv7Qg0azUSk+JrGVGsvxUYhVR0GFbX/AD3PJmYNPEmH"
    "HYXR2/lK/wD5G536ubcOrQhh6DMRvrS6jgJaw58CPw/9f42P+Jl/Q/494cHFy/8AEwYpWvtOmrOE50wzieZOpFZZgVafDKnhnWcTHcdb63HQWC"
    "IVF1klPAOsIfVvdkUAK1em9RypheK1K9y2YMWX5nZh+0TKeWM7QNHU2O5pmYBeLb/SBomR6nxVrm4JawHc90cPA6aRYW97i7tl8wGlnwy37oCz"
    "LtDkHSJVyKU3JZVqXZzCyxhWyYYZ1uA6gmvk0a/xsf8AFUr6Xi/8GeDwMvg4OH6Hh5N7aEMRQ/E8UctcptnlmV5nyhUdmBu3UA6C5cKlfxMdM3"
    "iAim9RvtIDdI5gK0pyjbT68OIy3/8AcZ5p4yzAgxqJwzYBeB7l8q/iYxUqCUBCIwlSpTuJ3SWJTLrQbVcUBqXVZfzCm3/P/uVwQRacp43+blMH"
    "BYbqMoiu7aF+0qKpIK2j7pRivH9f436VzL5v6nh4IfXc7hSWRZcv/CkY87M6LmDlPHfF68WbFGHKTcoDsagI9EsnkaH7IaC7GQlwyyRh7DOYil"
    "aw+nqKyyXm4JWvzL535Je6o7ksAOeCpoi/J4ZLJmI8BP3uMECvlnSC4AZlJOh8zCLVcw3MaD8uNIhrXLQv7TPRplLVZr/Ex+lP81fWzBuGEpJp"
    "LooMOD6kicKoqvaiOipBzDCnJZZpDK4OJ4ZSsrpuxr/qdb+F/qZFM+BL5h+ydFF+IQ5Top/uJhurYyn7iCGs0dktZU+I1UNvlBdCV8kq2PzNrb"
    "4jOKvbLA7eAw4DN9RguCqPXqbxFiZDwj+5VYID5YxPB/Mq2KuLGL+8WFuNwtnC+ZVD9kKgpzfPf+BjHh/x19Vc19WuAZneJtCZQ4rmuGMSMGLH"
    "BqZRa6tlLmCydswXBxwdSq+gfxBclw8VZAAWsL24sstm/eLqXyE9iJpfE+1MVgy8sJg+45y+e0dw4Yr9TKKI7EBknjDbFWEpKHY4NUo7tf7gx5"
    "Xp+5ZRx6UErRnx/wCJ+htP9TLIXD2kLUn+5aME22ef8LH/APNX1PVYVnUXmDwECBKlSuHhJUThWaWVkgbANmUHMxMyIaZ+dHwcBppqCEwY433K"
    "G47iIyJNzLRitH5HcFH4mA1GgqPLuL9uCIpZE2HWJ2z45eXccelTaVqvqpkcGUIXYJ6CXH2jcAsar/ExEtjOAti2/wCcFsixiU+0vyvWawfUxi"
    "0XKdiRNb+upXNf/gGCb9RvVA9vEoAfdhmvNOoy39WC4IRUqVEjKjwYqEA4ZnZQajSXfjWz8S9E0IZVbac/OJTuq+8uxl+8zA05rqUXBD9szDJj"
    "F6hCRZ41fPAKDuJGid5l1MOJFcXwGLJBlVWKGOtAu9VLnUN+sJ0gkWKXBh/8qJXmp8GupRRAUysx/i3xLw1CbwWjq8xmJ9w/QxYxjqUrc3FLpi"
    "xack7rY9949xCw53CrMVcrO6ILH8zaRQ6v1M78TRk/wiQb2eJ8keiLLpUfEnxnunuJ7J7ZkmC7h5pn3M1dzItCvJLabLexqDouiyWyJPNzSA6q"
    "UHDUqVKiYlSpXKswjGGzVu4mMS4mUrDMIaJZTy1F8qFuoAfsQUFyk13UytCEGhUZtjXxAjfXmGvae0eT94McsSwyvJcuXMzIG3mdhiKFki9hLd"
    "D9oszrBl8A7leJcXtAwUvq4NSr17jmtq8MwgvaHZ+SPqVN9+4xFs74v6GMeGIVqWGkfLKeoZ5Fxa8MPmdzNqg9Q3J94OlI9SurMvdH3lFmTENu"
    "ZQcI0xFLX5JfbVyvG5i7VCffMrPmXgSrP5Rxu7m6kj2xkybilF1XcCNj2eIwgg26iw6+ZfEnEfH0dpMSuGVHkMVDEIQKUGDCeD3wO0uLBFsVVv"
    "4mwGhetSlrcMaDBPLcUf8AuDttZTc2LWCICaDcpaqo96/iJbVGiHB6mZnudy8wZvqdV14mDLhWYqtEXMWMrEGXiWA+0wTZir5V2ewP5msLRGp3"
    "ShhLGpwxSLipLIC4rC5FD4f4RHmLiKmtSiaye4OqZX3Gbp9pYWD0EzAU73mFyBPXUq0cPUs6aPiFU5tgfmb9jMtrHIL3K+oBxWI9135It5uEIH"
    "cdPUpd3mAM5PEccJUtb/crOxUy27JbUaF89xXzRjEUxT7sXsHyi4kreG67Jg4tBsml8yqJmLvzLAj4uMxXxFHb5J2T8xHUuXGHiYC0sVUEwT5i"
    "1HlFRMCKo3/LDAPBInp+YtHtkIvy5lRbl8zCBvGI8Z7d7H5hQ5PJU2Ob3/8AqC1fnl7DuhpX4n/L/wAzwD9n+ovovtwif7AJ/fH/AKnQ+5/6iY"
    "u91QwOon9FiYHJfgQRdBd6uW+fxFhb+ohwz/sQJkhO6YqvcozQER2l7v8A8izTE0JPk/tMCiu9bj2i6jE1mXuWENVCD0f4H0PDKJ3qMKcm/cvB"
    "Wp+JlLRfMQIlFNsoh4+UpzSjzsiRTN1fcK2fzMlxfc/MrW2/eP5no+UKGAQpD1XBB6YFPAeIVK/mWNbty+IDdUwwNxCsEu1ZPLudhLAuDSGZhc"
    "NCfZQtZeEThdwfkMoK1eto4bOFVeGCFu7qFoyLolrbvNzCrnxCmCvvLFXbK3WpTzBjxvAzx0x4NyKMHBw+I1ByWsVrKhmHX8SuKRA6a9Rq6/Ec"
    "I5letfuKPgGDBg8XLjwTIlivEPz0zRV/EGWsVlvHIjDtjDGoqX+yaKqi73G37i8Bt5uaKejCSsTK8D9pvGTxbvr/AAfDMkH3FVqCYfGlibwyyz"
    "EyCq9QkV9ypasL9TXBj1D9oeLcKNBzG70nxCjVyvlz4jtD9kbYo/EKAUgbNX4nhk+Z0YfiA5Vn9T0p6NRG35QovrolKBZqv7mBvcb1CmPERWr3"
    "uBr/AABKa2hy3LAIpeLv6mV9MH9IYIumy5ZtC/AQGMT2MqVae9lysk6TRG7OtaGYNljyZjNG/GcRG7H5ngDwSzxny/mB8Mq7xBUuCWxGOwjw9z"
    "O7TueaLuUVGHTKXLt2y6O5kdOg8BCb/SDZF+IhyvkStr9TMYte5gjal1Xb3EZeQXAhGWsCKEa9kFwu03BLF2/hNBA+4ssrgKYbPU948QaHbzmN"
    "wdpiiqbfnhFwc/CWMc54Yz6k6QY1r2S7wRbqPy++MEhwAOY8kpe3p9bMTEs8ynqU/FRkxT5zBxwN16iOo/BMzFPHf7hpeK6qpaVACrZjux4RhR"
    "g8PU9j8Qf/AFM87JjkJS8JQbUYO8/gzHUqeIXs34ZhsMdkEHd4lIL36mBTmJjfcp5piM9yhtlig/sl/gi/SKq0+G40UmGFdLB2EX2fiUjVwr5y"
    "7tgMTdmrm2a7WV9k94GWnA12MxxmnnEr2r5IrKeEkoTQJ5gXyTDY3MvUpdQTcfJwwDuHswQTcuJLrfO5lai4vcJeZd1iPqAnsnkz42Kx8/B7Yx"
    "dDM2UYG2KMLQ4+5ZSgQoUPEf5NSVlUDptNbM+pkohnqmdjeETLne3SWVceJZNEbRRKxL5Jiw5uBWdsGtkpekwAblIozOXAs9+TNtMc3zfGIiW6"
    "YmxcTMFke9P2iLOe3MKVmX0lNiepatPisxtNX6gg3cabs+UENd4hFG+oBqkqYl+1y2EeT2xETA9sRrWqVsgs17aepg0eEbrHzqV6am2anbF/DK"
    "y18FzywfaeSvESk0dYzH1d7YuVj2xBmC8WwUOl5qGUzFHJV6iJk3bCci4EtPjBbLKjXqKrY+pp0bUYijnwDGbArzpFW/dhcEvPy6mNse5U7Ipx"
    "+DP91RuB+Ny81v1NMVdBcwdMbwmAFeMIo/pWbjQtgeCd0GsRBKr/ABLE8u+4YrAMVb7+JZpWy4H4ZsAkIVEC7TRTHAvxKYN1PXE4o6nohZBe+K"
    "zi35gq0vEPjKexSVyGz4j7NprKXKCt5RLdL+EoXiEaqJ5o+Yu7MvgWtFvce1jg3L9pV5/I5gHSP0riXUteSXiyAsNvzL+X8y1Vsa9xtFM4KgEH"
    "hNNLl2lr4gQzbMVGvce1yL+x8zFoe8TtPIJQNoWIRU1I9o2ePjuFWX4WFIDQXuXCqgvRBErAbKnx/SMCl+bln4gjZQK7aJuKV4gFDR9p/tCUwE"
    "f3EvjwqUzBdkLR5i1WaBhapnW1L3KSqtiWmSq7jAQCy4qDGA1yf/I+gmJx0ZZniTd3KH8Qi2qXXVwtw62QBxo8TarHzFosfdARNijBO2jz3H3H"
    "77Youq1NMP6HnX3SUguPYYaMQpUUnyhRGqih0agNMsgf5uALDZp7hLFnj/iWZJR5de+kDAUe3UyPu1H+0ryFigCkwQrRwNV0w0aVBh3nSRImbo"
    "B6o+P3KYNGxmGO8PTp+8br0f8ACZglveDBGLj5aqd0X5f7gBq7wmdenj+yA/jiEq7CrOG8W9ylfFwSFWF9wm+Brp+CbhPuCAJnyCfuJ0v+JWLq"
    "vDiDmPedYBXYaq5RBnwY17+xGJTpTFTMWCFA4l0xomX6p+xmZ5601MbEnWEoxV/f3l4tQYKP2gFOLupaMbW6m4FN21HW3y7RoaBYQJEAZHLES6"
    "ik8/E3A+GWvX3mb+iUBHHiF2Yab0PmY3r13Fdp9hLFUq7jKWPREF0/Kb9xi+mXV8l9yoklIG2x6lbb2WCVCjXuZh/hEl+MNFRYF0Sg4y7IdwT3"
    "EG/gJltZ24mNCpPb2hK6r0GPzFjaHkcQOlbyQM0hijKBQdttUn2llJ95zM4NF2x/7MFgUqnb7ZfXPgHH+4NDDwzcpZL0UvMW0EYwqWz4PD7x6w"
    "ajN9oQHFYLE1M9b8/aBN0erh33/JATYaDcYt9NJAp7GbjHUto0uFSqA3EW00wkw9Kde4K28byV8wsL9r6gW2Y+I16IC6fM1w/kuEyxrKUuaN8Z"
    "P5ZXewKe5nVHs/MzZKyNrqNeIERr79weJ2/xkaL/ACGh9RqqutJbu7pX/MKGxXslL5gxz5qLIK+D9zLbFndGfczphRo/+QoFOr79sTXPVKlosj"
    "X6DMXKO9L9RtR9tlfaWV2aL3C1gmRp8SxWdL2Nzaqwa1Omu17eql1yjtmBoMjsgQujlx1MsnbyTpA5pLmdUj5xKkcX4GCKFdK3L5YvJGWtcemL"
    "avsF/mUrRjQ7+CJR8lkX1MKNg/MBFXeLUxEIXerSNGA6UVc8o9Dn8QgBFrEBBW10e/MYbHB1+5Z1RQRdfMucitoMDWVb3nu4FtS1Uf3KjCbyjE"
    "xMIxl38zctz0ISxd77iTJJtIvCka8oraSjGbP5lrNy0Xi4r7RLlELau/UotHTWszQziwvULwR1sZ4VfxLmYj34lrfEIFR6jULRsVlFmh1WZl0j"
    "FoT5liEfE7x6LhqsV/KKuil4YZB6aQjvMUUwiwhu0+wDU69NT4v3l+cPUXFZkvQQfMAF0k6ifc7wiC0QeoHMNg/p43uWtcnlaqGa6EWGc/LEQk"
    "V0Bj+orVZnyX1cL7A6wxKNuy8kDtgMqIXkuGJAod3TdeoDQY+6I8i2WRKMLnvMa/4Q/mAUE9wyyvBUp7N9T4nzEk/meQfKBQh9VKTAPdTNov7S"
    "57+fHuFB+wsT+7O4sWXsWBl6nZjMshpi1MTa+A2sRwV0Fj8QFUXo3/8AIB2OyRwhEe6ffcUtFSkrf4hTKFOiesRvbo6TUovRVWQndHdOSJLkso"
    "n6bncPWg+0cTCZFKSiN2Vn0yiCaZK8wYvsX7y8PN2W2viJPnkJl8ym1hVOZVZ05t8SwShv4epZ4P2TIrmMFR0vjCP2lzmj3FNtrZmvvBDdyg5v"
    "/vMaFR6RiPpa0DH6lKs/ePiGWJZql/7jqRpencs1D+WHEb8WhawHZLpwK7b8wd8R6YvVRL/edPnzDTea+RlLLfDBLTybdDMoovbLjeatFQaFVX"
    "yfiX+5vRJd2+hj/EJ3hVUiz8SufnVXuUIodUtTaFsC2V6b1DRLqmPukqK3QCj+4pGsOhcrXGWKOpaWXFDfxBdkdGalr43hUH151u54u1SjIsFK"
    "mTbUEJXzr9op3d/8x7Sxjb9wqQe8qgTtiu63BTY4a0mgkwYsixW/cC1DRBbyPiIMl43RANlL2xsxFCkP400lrMy4Knqpoo94fuTKwvBg/JChE+"
    "5bsbe3DMdJzVyziLyKYiP+JYjGQ9sy+2BAs5fMMbw1i8wlgh0qr5mwa8obr2oUWx8y19r6pBgbma9qj0YVUdeLVXUUZRWEO4YO09kDLKOyomAF"
    "95ZXYtfE8xacU6I3EfLG1GnnuBIeO82xWInvxNKnM1UF4Ki4JGwwl2wPdXNNXpljpBHKvtEbE/zLABVnryVFCgGUc4jyFhUIN3sNB5iYIbSXuv"
    "w7lQGq3bb7oTtvhTi4VeDH46l7AehUpfsK1jQO28Y/eo1h3TfVEdDI1qLjE7jiK0At6CCWAzxW0AwrZ0hdeY6SxcWab8xAayYYJXpQFaS1iH8L"
    "LQq7tLdNdbRINt6alLhg1XuWi+FVh7mhZbtVzIYtK1HMvPkI3ULb1MKbet5X7wEGTqoaOx6QqV0Wt/m5a1+e5nMvLdQW9iFWpMmB2HofEI9Nmy"
    "UWrm66lMhdxsv1Auo9rUyts82Yv8S8V2NRR6Yec2OghbrZ+kBRaLYP7JTaqXGZXsT66RT6HeIrwsT5/fuCgJTy19pXqCLH4GSo62HKDUy0hX3q"
    "d1xfBEca+SUav7RIJhgTRNLE+oLbJ49QAHH5Rbn5DaOT14NIVSPsgWxrqGDRoJJqmmDeoSnK8qFXAeqQrdU9eP1K0dsPzHqYEQ6Rm2waVD5qG2"
    "MZ9vMzvevwj/8Al/U/IXBdQkEKd4TctrQvP/sscw0WswVGW/8ALmDtfWIxo1kQqALLVlklGuviFAcLvuIYR8sP2m7Q+qMTyjDNkBtHvKvxKz1c"
    "EDh8MGpKOiGvmfeSyKO/T1Fr/wDCZYqyqHkvRL9AM4rnzEbFJ5Q+U2axmnP5gzLp3kfePwvzmYlqaaar7ylad5hi3/IuCrzFRhDO7fb0mO3vYZ"
    "RVp7lEb8ZLI2eLW/cr1oCK384ixQdY1AA2Hgg+FSw9PcPyYsubL9bYIaHBq8RMnpNI+Lv2Sq9KpGkRRSMyi31VxQtfj/uAstl3SVidrxYu51zz"
    "6SXg5c9VGwX+1fMpsQHqDVnwNQ/b8s/IXZZogdi1ABB62ZuOc/yEpU0O0uBlt2CEL0ouj+SJ9wn/AJB9F6ZcJW2w/wBytx+3/qmQG4dEyuhsSD"
    "2uq6H5mIrBlbMdcvKtRFrmtzaxydE1LC5DjNpgC67R80vrSAeEr/sA08TEKiAIWjeSiU9n4jnGX1Af5k1DAqPkYl3SJ8QV0Ym5dXHAKTyTN+p1"
    "qXcUOExPgELLgY7mbysWTC3iGFrVMAN/E2Ka3GptavDMCwfa4NwF4uWEttXcw8/h0VFcbDTFRHxYLPknbAp3b7qIFI9dfMuRS9gcQ+oPTf3gnw"
    "VYV/aFtld8HuU25vyrxc3g+XEpHJr8xoaeI+amO8L7lXEDTURLvazi7mKBX/xFZnF10YiFCr6rMud8/KNRwedVBSI55f8AXKFHTtqPTyzxmOfQ"
    "JEOVZwzBUB5TYABxgwFHD+SyAMccg5QX72sygHWO53m9LuKaXYzTf+oAo0XUSL4fE/A6YmJh/CCKh9fMxMSe/E2UxKLQxb+0KPVaNyqoq2oShv"
    "vLLBEVh1VY9w/MOa7/AFEGQ9StQJAt1Veot4CmIjdy+oOWCsur9RlRq+mUASrp0f8AyKV2nW4+0JIy+8QAgddzYVXg/wBwFBA7UK9yyjvIVcWy"
    "/ZCcHQpX2fMquGkVbk/EpyujNtRCqL3/AEEYNYZsJUfkeMxuyK6wjf2kUnDwxhwF9F5qYNKPTE6zxP4J5n9J5+Y/1Ong2+J/Jnj5nf5jpPHxOp"
    "/Z5DU0Z/SG5vH/AB+OD+mfxT+FP+54n77+Z+//AIn6c6Qb+X9zR85+u/mMv1J+2fzP0P75dfbgNzafqT+Gfuk/aZ/Mz+qf04rSf82fuv44z/Lw"
    "G0N/lDXw43/T4hzM/wC154Nn4n8if9/if6/xNfnP0oS/7+80+39T9mP/AD88baG4/pz/ALfZP4E/a/ufsTr7cf8ARn70Nz+2zb8p+jDmIH803n"
    "qNPjP/2gAIAQEAAAAQG8kLDmXT0JwU7Btb3e4rIbVolZAx3emiuWG74ZxCDwUUSh2xK8TQBhTEKv2MLiOO0jqZiSZN1faYv+WBXLPOIfSNXiLf"
    "6rFmpBWlZoESHdtERl6tVNaK7Ew7xXqIr+Elx93MoWsjCb3BNBsCg1sodwr6tPmX4RXCJ4kEU9QO9N5FPWTmaNMa25+E0cO0FcqgCo2e3+RqJP"
    "BqbbY7fuYpx7hSCgOqnYwGOYoAj2uLC7DeqZ1A7pf0Y+8r6dpGOs8f0pI1bg5fcN6XIRHcKgRKGTDpf90vX0Hq6O4S1kePGleUCX2zNUL4pD4L"
    "0ngR+4yf6YGrkCoY2Zlzzxvrkwl0VX+KSUuFy9/cdE12nV3CdVJNeCszmmDGgV5TcFjdX7IQjt0MQHmuBaq/vZZAqemyNvhYI9eUE10YRhxh5d"
    "MyK6mv1I4wbxKd6MMn2pX3MbGiXqMEni6Lx0DN7kpOaNra6mZoh4DU6F3Df564Ka3QO9MKvK/8LWfOfk8oq180OFnGEEgTztAZA7c5w0ZlyVna"
    "rZMuc/yL/uT2BVmLJthBU8LHuZ+QNVaZ/VE8Oumx/gcgYPAEML0B+02uLgWAKhLHb+to5CLi7eZ6dMYUoASAhKNsHg/PaVdtevqjtB/OS7M6Om"
    "3mhrNDLyhTc1YTJCP7i0OWntvsDn6WoQ7G+tqhgB0d9CC+OUsZHpIt+l5Pc/p7K1/C3+WtlpNgSH0AD83Cbm8ltODvnBTEArAvDtWMJsz8DWw/"
    "i8RlmmUgqkOTKMaHmGpq1IZBS/LOHV72wq4TGPb0/wAK1tiGUa0rm1eXUOll+Rv8wTBvIICBSVmFRSSkP0x6uxnekj1+7GSuJTPQc6sbT+pwR4"
    "GVhS8zpMaJHjQpwxlHplAjeEauWG3ofo4WQ/Gy2TUc4iZIWq19y/AtQe3wj51qpPlkIhLVEuhRSkb3jjEbEl1/CotfYrjfx/C9gXZKuJFgcFtR"
    "4eX12eY/iqgr+Q6tA7DfEBG2u2VAg7AhLsGMYrwf9mVfSlQTLMoF8wAVj+Snemig8zcnGfrgr+yc0zxP/8QAJxABAAICAgEEAgMBAQEAAAAAAQ"
    "ARITFBUWEQcYGRobHB0fDhIPH/2gAIAQEAAT8QL6ZnpmHMHYsJWSChhuOQkabqNgRm4XpG9gfMe4UQXEy1CuGZxMWkb1RHHMxqDiYJZdxglYh6"
    "DhEgsSjDPCWMkyyEbTHhxyzLkj2cMXqU4qArzFEQmX4lGzEd1klG2/RFhWMW7qE8ES4bgVk1HYuoIGcTIH1jpKVMpNkSAKEhZY0shBcWywEmqY"
    "by+82IFYTuKqFvSGUS1dsMiLjOoAQAlgMELtQiDXEyruI8MFNXCafqIouXU1LzULqpgLh+JWsQvtAukicwafQSJ5hjUzBxuLi/RxlsMlwHMBrE"
    "FFxqYLCP8SwQaWdCJwTgBFvJCE2zE5S0lqZdzxxPE1oLhVCgcQLI9Z5wzxiL8QZ1K6hY9AqCDtA4qYdTaXIGYcVN0oynEzMKQTkfuWfEcbq42R"
    "RsSIYTMIvGYIZykuSW8So6ZQIxkyhLqFpl9lEUDUx4hVloiN5mmVdQTlbCiEoBpKJcZBafMDW9ICmYWt4gKQJsUhchRLIRzKxiAFhMjMLKRAUu"
    "FCoraIJ4gUlQFT6giUkQ2NQEpMbq3A2dyrcRiqlnYygamSoNGrgGbRtpl17wzuBxAhwxuUwruVQVDWIsVEpiVHK3F94hcCMq3FaqX+Zk1CQ8yo"
    "L4qODMGI7TIsr7QFRellCRQLx6a7gShlLczgrKhU1McFLNzqgVErUesYgVmDbuU8TVGU50gWzHzArMlvEapTe4WsQsqNWoY1HCRPchW5cW8wUM"
    "MQQpmGBuDaNrBLOKCLCJpqmAFaibJhFBrEUZg9QHdRWVKSR+IHm42MMtBI6maKspeCUG4M0jFy31FwLsGoYWkJzmaCXCjGIZY1GTEFeYAly7Ze"
    "YOZ2Zl1ENwcTLU7ICcx04lJbxL5ECzggtzJ0MJjhl9ZYZrcYNQB1ZO5QHslsEJixAswZ3KJ5lLAYECWG4Z1O6I6g4xDWoiyw1MMrEagLltJlMT"
    "PZEvSAmonEWwzZK2gjZxEIlQ5IYiBhpqAK0iCElSUSCqbZbscTIqoAK5YHVSr5QBMxcYC2NLvUUqrGEAiHyhRTiVkYDZHJhxMDxEi4ZzA3tFCG"
    "RnUWMrfEVbgN+IdI2mCNrGwYyRTSagnGSUO9xLTiAXZEEEagOdQ6SlgrthhCpFziBMsMhUoQWS3cqG1Lgoslw1BWALuHE0gUVcsGI6dQ8kDmmI"
    "IgOds1LOmZzoy01HvMwYm2dxGYIG4WMS5hljAB6pH06SDHotYZRw1Hr6dpeQEurgmGJY6IIuMy11ArnU4BCFjEzURtYVAqkiDrEqubiqLCYhaZ"
    "XYLUJeYTVEwUcdQDRqKMW+ICLMIhaC+47dx4JbncR0mUizAESNcwsPMS7uZ0EBOiVtgVlzABeohlTDZs3KulEN0mdJEXTuLeomqhzCRqNDJRBW"
    "sRdx1jMuss7YAbUlEqWgshhuGCGSAxLCEI5XNAZilxMWIi1EWE+qHCpzMxRoXNy3CODM6GAm4BMReER1mmBRUAsXiN9no4GZ8SouVEFQFglQWc"
    "jAjqDx6F/EEGFx4ySl0EBbzGixDG5zEZgU3LEqbhJEdblgXACZR9DULwgaSJRAVp1FcCNeIzRSykyTGmQ5gOkDnmdAzC6TMU3xKDDqZCiaKhXJ"
    "ApsnuCWgwEEzCrmZF2hR01AvjcSmyC7czLbuNDJHwmIavqKM8oWEVcIAdREU8S8cSxg7lLivia3BrzLcQWp0Ti55YLLXFQqZayy4NRUPSBikwj"
    "l1LGoPoBfETErC4CahVjXKPEK5gxKGCiVmBKrUttDwjnE7I7iQmBNyDauAqlDcW9S3REqqlFNTglw1GLoi9oVYcfBmWyUFCcDLTGIaatl7gjqO"
    "KpvVmCNBBGYQYlAonJNoimIC7mKo3FRxPZuKzArMK5BzNCJGMkdipR5Y1ozE41Boq4WMGZY3F9xnbEUZkREaiDO5jEFhumA6hAxmbDKe6CoFZi"
    "I9YWi5qWXNFQq421iBrioA5jtY1KtVKDEHmX1GtVmU9RFiqg1K1ENQDhAsKekLjQhlQljCj/4IKlSmJmXsyx6y0KBcxtMUy3CzqAMy/SAWI2Kq"
    "LkJnKirFVFOJuRKSBcOpQdIWczPZFGBiNTqArBC4Qhb8Q0s3KMp0AlnwgNy45l0tVcuGItJjJRg3E1jZMfzD2wBhhtZMLmFPEvdViA2iXNoUZJ"
    "mxEou+4PHMpT2hcHu5Z7zEthl1AxGrUVseo2sGo4XLGcVVwW1EhuIdo/xHcBcaF6jMSuY2D1L8egWmFWDMECoBqPuFVBcoIV1KGD0h6gKgQFZj"
    "E9DJKJczLBBCmNdEArMopAu9zP4lF1EDLkpmZkQqWc6I6ncRbQg61AGSUOHEqhy4jdQ0jYEVMykxENkL6jPGpZRnTEy4zPeOEreUQgZUzKheo2"
    "CTfLUF03FClekO8TtUAuEljUWYWY1KKcwKc+oHUQcwXMlwJomTDibYx6KBmeM8sVG449y0zMS8yyozCyb4jx5j5MMFkICzEEslrdTPiUkCU3My"
    "oK9G7qPjDGUOptzAqZlQlzcYYYZzeki4SoA8RMHZAzhnLuKSK2wGcTrmdcXmcyShcanmDwcwa6uWKBiZ5EozBTM24O3DEQw4Iz5leXEp8pQymZ"
    "uRC0Bc6moa/wBwLRidxpQYiEq4FlD5JUY6YVyEHSIYjuzXUu8VHikgRqA0gOdw2iXlABiG4u5YS4UkQynU7GVm4VAFLblVyxDcoZi4jNQXAVom"
    "L5l7gVgqAuGGIbiqMSUMVynMCyjfpEglKgwDESjJK9BFPQAyANkbL6gAuwD0YMQTBgzMGokitmKLXG4VY9rEs1LHBBGYRdRDaCXRqEBUGtxKlk"
    "7gZVE3qdZEuCQgYCpS4luMQe2oITauD0VSkKPqWdVK3ipVE3QMwcFkyOIUyRKXCUvcoEuOskvRMSgxHWSNpLbamdYlW6zK7m0FUHcoQpZl6QEh"
    "eNYYZmJFBrLLYoHiKKvER1LOILkiJiUBDheh1DnFYK/RZ1HGLL9wJAVBUwwZlQYgFUTAxPQDUAMTTHS9L9RZxDYbtz8/xLBSzyiFp3oj1ZWx2v"
    "J7Yz5gZvmA5lWpVFxwm+4uksWlC3cQQqtQQsiS8y1t8x0L0AmYBqJWpfU5jcb+8ozLZOPQCi2WblKlSmlTBYt3U5mVN9xzBl7uWGDcWWGoUZtL"
    "AzAYGFEziGKblg0EMNQbwkJcbaICViUDzEVLRUwS11uDlMmZpAkrqHoWYSHC4cg4QhKNzmZn1KPEfA9LuYwAiZay4CsRZQektCACBPBAqUwwLg"
    "VMjs95tGY1bfUqVqXzfXhjPyQJZdVhfFrghAKZCE5yRbmYOP2IKoTLwb1EeEAXkvtsmoINHnBmYZljkFxGO6XWY5Q3cErELzAgxiDzucRiGNE5"
    "6zKjM+BKBUAMw1LRHMablgg13MGJ2wWeYKiWzDbEcS4hjzLDFQ6ohHHMQ9mHOalGaomJVNEsq3EE7dQzMsQLplKoZjiVBFpa4qmGGdwN1AwsqC"
    "9wCBbia+gGYkGLmCYuADtLRRAFsvKpEaMJmWpbmZv0LoeGpezEGNTTiCoF6iLMUrcOsbmJMzuh2sB9ywAV9vP6l1xbM5aVfsYUTCJg8BL15lLT"
    "bP7pyvGjPUymkQsryNEPqpd9GjG70q7Hi6eI3BTC4b5xKHlyp2FUJp8whcK/u4Rbb41eCEMoL/MRVShlvFzJMsCow4l+SAwMGIMEFQ2roJfFrz"
    "K2YIgt6mPUUTEcFSxEdykp4j7xAStYmB1KHogxBVwKwrnCgQgINLgUsdPcVXIhAm6l1pTdOpio0N5gBjMAlLKGo42kwQ9y3xHwhdSjUquJcwr3"
    "FvENZVJDcITWVqVLGEFGSCkeyalTKkoGdQOGIdejgRtYahBT1E0UsusDCkDOyJWpYg7gFyk0iLM3C+Ah0IKBV0Xr3c/FzMogC2nC980E3cmtlx"
    "QN39S0OFwAmlcd4h83GlX6ghxUcRa7HOHPGIFXalr0L9sr/wCx85L5nzbwua+IAhYjedgc5xKhKbYb+ykrv7gB0QDoPRfMsfXF3cWsFZUoLgog"
    "AtVoCMjUoNDaeW8+0McxbYiRjoRoGrdY55mGkVZRLOIKYiC3M7hI6g08Q2XNh9K141BgmmAEyiC8koNkBeI03MhuVtIEYZeovHM7IizKxARs4g"
    "zczRJoqcjM0gdVOZGtCY4LmtwFYW6l+vS8EqpkuWZhzCjR6ODMEBXiJdkGpRw3M+IQLGHeYZQcRhzqdmpR1PAmFeICOYGMQhuXlyisTk9JJeds"
    "IZFqCckW/bq9qXct4iuEv9MSQNufqXiBCRFlSRedbvEcakhYqDXYlfXmGQKLQ4L3+j6gy1Zd+ZTtcFgunPuywHeUWKY6uJsTK8lwjeZIExYmWB"
    "6mXEyWwtxERjEp2UvNOudSrJ+ySwCq1UGKjb926hUoivTFD5yclpEAnWIZ6nimHG4oq+haEfCdOFFOpzI7hw1Fhq4tLWZqNS53LniImU+ka4gF"
    "GBuZiRTHdyxyQWlZgJV4nVA1mPFv0gXHkQRLiXCxmY+mghxqDiZ+jh1LDPB6V1BEQxgfMQbTogqU0XAFRaiBmvSTJbrxEKwpHcxxcwsWywLHMI"
    "DKouNTxQMzylWFWV3KLMQtyC0XXliSM5pJzYmEz6AVBzmOVAtasvhlUihSRaXVuM18R2YAChQ0prO8LycQzNQzKr+55n/RUrMCMUMZdHeXWNIL"
    "giG3pPGyorTzqyDHtbFggqijpAfMQ55o09+DvPUQ5CBTAKU5Ld9m42oYWYG0TDVkO0wx25eMEuZ/HpAzHU6RsTJiYQRaqa4jIy15mSYNzDnBL7"
    "EoWo1g3nLBQiDEHTC1cUDplqKhfoIXMoMFy6xw6lTIglhZBXqWEU9pzVDHUp9ADxMZjKGVmOhqctsxbxvzLFYg0JypqkpupgAtmquB2EHiX5Ir"
    "KZmHEGtSmJ/42SeEzmeK3M0PyASxeVfSCYK4eruE4gtbB4xUCIkV2g0B3vnMIx6jr3Y7blPwLGvoz9Olldwcei1x8pLXZWjWL4AbzcMkCYyX6i"
    "HdsQXz51MXb2gusWfmpbQFF+HNg7G7Gob4GlfFRzZZACEzUJYJQ/DmZ4RzUu8h+o6Mx5G6eb8Sh67cDwBONZmXyHH3EJupGpzagTUA3ELc5CUd"
    "OZm4YxkSMs3yQRjcyXAt1MipjZn3iAzNSATTKyyaZibBmGyXXiDwY9m4BuFsjMIghtBxAuSYMRXUv4hXUx5gZS/QGeEIYSmG45IpiHJBQ0IC8J"
    "g0aiWY+0AUluJibqDGYbkJ5kM4HXpWememr0gQPEBVqm9wx+ag9oU9DR9z7DKLziO4qsTiOMwiGzYd+Iki8zWFPxK7egJXjMYkrqYs9zJW6P8A"
    "N/zMuJRKJWCNyr9Q0o4ilqwJ915gG4esBVK+0Y6wEFzVlfzMNgoMbJaflES3CmfMrLyCS9CE/OW9e1XzKzmkAVD5E0LesRU2wjfmj8ufaPZF3u"
    "VsWThbm4SxbpErIbG0HISuVB/cuWuKupUlJmNmIK57gS6/MvUio3gzBxKjDExDEGY7dRuAmONlm4YynJKXiPSYaYh1A3dSjxiBINZMwTaa4jOY"
    "nMISDzADBr01mFuJb1x6EvfpQZWNULhKM3BbbhLZcoYCRgZiyYmYMwygielmj36lgh61tCKCBwbqij8HzH/UKGj0Bq1F/MG7WFFd1k+ygCvEvf"
    "nmQmNp2ZINl9pTaAAZZSKXLl8NcOemXrVRQ3eqmKMELa8alNoWwojVWY0kR804h83ozjOrO5UGQwzqPFZHfiOBQ8nD6YTfVahEBbF8wFOChWQD"
    "pDssiopvAfTnD4YVxScR/p0MAWrFiGWTXSXXT7VmMTJsYj1ZDoJCHFYNpmsxOEukP6gutrgK6LhAW3yOD5aIT3KOe3b/AB8QS0ZlDBsIUXItBS"
    "q3dj/yXaNpFafDR9sfmBbryvc6N7QXfSsrSDyg1MaNDWPY/iFKDrE0rAChqlxTrniYpoC6F5dT5nVQ1j7gWl5XugJWwByEo44mC7QqajBmaZiE"
    "mFbDWtRXLEOOZgRZc+nSOIvTKUW5m4EUFG/ELxiBWoQnMoEQsRyBQJc6hMoI6ilXMGvS0gYlSolSrnEziDuAyLjVOprVRhOI9CmIAu0iBtGEwx"
    "+otTDiWixrgXKoF+kHqQQKa8ISxVnlXsTQhjotGAsKW/MHdhQmaw92EsURA7ouP5gMPAD2N3kOO4X6Fq9mLWRCjqMKxP7dCZp2LAMp3MDA7dCh"
    "KX5ipe1DEKUdGNmoJ8vkNVt07c9ai4S8rlqDDbZJnmIdSyWMgSKtt9BFN0DGtLQseL3UFs0e5GTBMlqNbuUJWpUF80Jz+IKrD1ojjJnEZkFNJI"
    "63OKi7W1igbeFYzesH2wFODrqAK4VzEZ3RNDL7Et+3sG1uBjNQako08g6/EESxr2WaFJnZTRwqRTxiK2vbLYJq8jCQ73VaP4mXIJDYq38vxFbc"
    "0D08fmFkLQLnUfbh+GOS4D2l/wCcEg/30Q93Qe8wD6k3ftvnhejiM5BMviBvVQY1HlVK/aU4Q1TLxMzEDdyiswrgcy3yQHEysRMMuwxysjtgMw"
    "xiUMqVEG1RM+ZpJrMcQ5hmCImCBiTcqJKqO7iy4tlANYolTHmIZseSNiEdJaBgzMW5tQ+4Ab9I9EEIZhEEyQtxBUCpUrMJvOl2cB5YCUeMGWwa"
    "zzcOBZG4FLZ7wgDRbK74Eo5lEey0V+ZhUhSovkv+nEMCOKZc4RAeTmcDebEdpmvuoehtVrWy1Z4uE3XhIOAZ87TMxeuQA8bjfbrb0XrLq+JU7C"
    "CBZThnzLcsZliDrQ/Mug7DXaF3Sg3ouo4wJPExlRP2PMt9gAoT4IHWJrAfqNVT7X6I0OcYn6kuiIt2bFd8sDGEzqEdRQWAbMRJHZDo1UNC8Jy7"
    "I9a94L3lHUfX4ZgeHfyz7TPFqQ22hywewEEvdcD2+4Wh2GeUrm7H8R9ASjl1n2vfE2m6rMhQNOLDOKzK87rCvjbXzBZFw1fl7feaiKjjWRLgEL"
    "3GrYxKSpDnEBm0pcSHoY7lg3DCwRZEBNkzLRLZVxUrbzNQlmJfK+IZ9SniDT0u2FPECEBRAlQK9PCNsMqVUsNYxN4yQfh3GLQXABhIEAZqqJjE"
    "OLhLuYRYxMvQZmnVDc0gRxLhRDQI4Xm/zWuY6MrXUD+UWFA2nW9V/MQyNqzxMJgjyStNXR8SxU/MDWa+IqKbmEDVcOViNf0Gz4HR5lFZlAYCBP"
    "cO0AcBxfiG8LQCKmBQaPMUShjL4lWwgXq0aiWiszkv8xsMVVgvFy7Xro/vi13c0L+piiqNOZ2UBadBL0RZwBSz9wToJScvXHX6mPAQQJ21tqM3"
    "xlCGWbR+8xy8RGwo8QoMXAR9skDYLMOEbNntCrZKnATM0gtWGo/VTAkE2cL7keakJNeWW7gfhDZSPpbdQPMLQZgiUwqZSvM8IyuKqKJkIM1GvM"
    "TZvNyrCJmYtVAvtMo5mEdYDJLcuUp2QBA8xCcIfMrWJQmUDxK/8D0tUFSrgr0Cmi4wQ+UMVL5mbi8ypviILAeqiaqZeYc2wUmZeAXDzxHqdk6I"
    "eMs4l01Ftmj3i4M4wIt+UF+pmXsBXrR+AHwWXLTGkWPDO4DcSC8Gz9TBAu8wYP3MtLl/ZLKs+4LatGYNzEWrL0csqjMHQR09Fl7Rf7+SU1tDLY"
    "3gF7cK+rlDfRyBRduvlh3/AENYt0NHtMJ2eI55rOw+EhurFYE0y6aUYC67iXWLfqb1LoUV6pTQdjlcStOBhrRFfMxV07xOw7s88xkqxF8wgyOm"
    "a204/tOV5Uwcfe7gQpCU4LoxuIVJ0DklG8g/DEJp+ZmFFgT8P8QLu/Q0hWMnGo8o6zH6cJaRrLfELeI4I1cQKamuzmPMFEtbnhgriIPEDmYtQA"
    "YIKhUrqGkAErqKuFCcxkHiJOIEA5iDRB2lWVPfPLEZZMXUeFESFVDQyRGmJWBVRjeZU6mSUtmhBbuK2d4yeMVENwVN5lRswSeIbBy0NecxLi+H"
    "k/4FfLEaugWWHVc85iAQCUgTHhhYZvdKDl5Wod5hnxRn8s5rDILQpVZz+vzEUJyR0HDpM/4z9ehLmtnJAjD06GThlJPBAWVQNV+Czyy9UFoWj5"
    "PmE2PneB1G0CjiVfELMVSjauB5o6uV7vlPIv5rWo1QNq3EzRQMopiR/wBJ1EXDyQ2po6uNJdFKH/MXtgAaMf3D1j6PuGJYh4gwUBg7uBR8yg5e"
    "8uS3RG+nX6lYxb8Lh/uLWiBagPUQlTqLwWF2alXHoFOKnuxcqmWIYDuCmoKDMcrth8xMcu4EWx6m8n/VcR19U/8AkwaFC6xM3a9oI1Sjd/vOgq"
    "Nc0RA7q+IYbIFMcwCAJW8kQfSJQ7lLlB95rmMYmIxldMBKYuIy+DcC5dyr3mYniM1iAhiBVxTDWVhsh4ieYPMAzxbnRFZD0eCjs7OPrMA7ZyjL"
    "4txX3M0GDs6J0kxZV1amGKx7waALJdWl/n8Qwa7npz/MLRo/LDQcAGoSxHy/UFMKMus+IguOALunP/IAg1EFMEezQXKWlj6PwS/fhoNB4AE/ED"
    "oDmz9RkNALOHGfziLf2FfklkltBwvL/EVe5Hk8/wBEG1sLlSxwW1dcY5YnQUx+hQcFEABvJ+oK24mi5eYpalYl3WOIK2Mrv/SOZd5G3sMvcI+8"
    "CVhFreAcsW3qiN1n6z9XLwSsTvd6hZTo2K12EbBfAWz8wg+goh1v6zK9aCei2i+oLveidUOz9S6agdR5xGFsRixBpr0F9JfSX0iZqXqgQN8y9D"
    "xxHmhhCQoIg0GzHcAG0GziNRCLcFdznDL6VUMjT7SuojMvMyKYjtDMCEVMmGEzceRKiRJYE3iVrWepxsgGGrolqlMYiLLXUdbuF0qAkA43H2QD"
    "E3K2VAZgzHiV2EoCVmPRjsSnNB/ZvqZZhukaufMJoBwMvuuvq5rBVToXk7Yx6i8dH+Yqe0sU6y2HRWq8wQqDWEv05U84/uLblGivvz2QqS2wqp"
    "cIFV0gs2RtpVpX4g7BxmhSqN0/Uo/Ie6pr4uXMoX3qVY8r+JnwDVtq3j3lOHJv33NnmLa5WGECrOyV5471Fk7ZC1bOYBhktGA05fiWenKQljhy"
    "7/USWCVvB3XRHhFaffn3ZWCF5zK1wZVr5IwgipHIOPmBaK0Q7QzuPC8ILK7seYyAmELH4maiw5LYNYKionHoGJh6CSdIx5RFQWcTDKZcyqgEhk"
    "KReErSjhjO26ipHfiVFIdRkPBEKuAW9kassIIeGAHMBEeYAa5gzDCe4mX6GvMr0BVxcansjYC8SrCAWhXtL9/VCw4vEsmH1L7uCNFEXdBqYXUD"
    "moXT3K1mZYYqo81cB3MXEWJjmYVTDUtMm4uOLgFgqNqul1H01oKbMVruIpGSqP6S2cJWDwZv5mAzCA6WOhlhzAlRA0YllR+alYheSiuf5QUSDN"
    "oPDz+o6NpA4Dg+od72hZ1EGZ2btHF6LXB3KwyVBQEo5cw1RL3F5f4+JZzH2vXxMT3QcqX2xQvj9R+jPNGDu8G7gTheWvF9HiAAYyNNBl+5XnAF"
    "UoWmuHB8so+MDnsgy61nEoQ3yrq3tMXmKKhCm0MNm3qmqsmuXPiPk2Gktcr5m4ygFAcj2XMGisUG0sXaPOPmVjAQ5rv+faNVSm92oZellOPQkS"
    "yJB6CCKzKlQUjlKEHVQqwHyjik7Jc4uFc0xB1EvUKnmUuPQtzDDzBSy7j1mGwMRLtnslOCxiHVxKCBuyMVECy3MyjRhaNCH0B6XM3qZXUaCYrD"
    "KrcDMvqGwgZ8T3YjxKAgjRcWi4sYg3KqAnAzUcPKW37xJyOUtuMH4r7jW0srkhV/bMnKKTNF4Dz/AMg6titMma/iG/w7EREAUQIsiQ2xkaHeGf"
    "IiCBdAaqqyf1CHilDNmJeceXrv3gGFYWNvzA+KDbIPMLgUrQlJZ+ZZ7f8AMuKvCKKLvbecdBBdyyqwmmYNJCUyqgLEa4vY4jrc/nb/AIj0ZNZ5"
    "1f1F6q2C9nUU/FikGWCExvPUGePWUpCWv6jy6lOCbuy/l3EhN509kIUK+IWa5logvrIG6+bjIYi9VhV2yJh4GTUcDNMoBLRZ7R9Dg9KleipVSv"
    "R9BjxRSwEXULABZDtAXiF3MG4lSkPMC/ThL8RLhcqjZriZyXHcHhCrKGVgpcNTccZvDcNzedxYzBsYmC5RgzBHe4s5hl6uOvMSzxml3FnzKOeo"
    "8XNIMJrWQOaWxmTowm1k34omPRLo5sqko/fvh4/llwuxjjMw1rqUdItYjsYYQAJimtqYRX2/csY0FvvAag0fwRbi6BM+D/7C5UbQHcUHASjEpW"
    "o+Jzz6YagvsY/xopGx9S0G3WaRqyVvdIYuDIWtBhTC7M/qCwKhzCUR2vspfplxYFgO0b+o8bzmBa7ujiZu4KJ9UbYkxXpK8aHzUqqCmgQw/OZu"
    "FOb5D/mKXDX8Me5uHSNaaCEqgYVaxZz1KjqJf/gVKiSpUqEOE6o5SuoMegcBChe5V6idy7GnacyzCAdQalNzAwMw4IK4M+YHM28SjGI5ZjRuFi"
    "GtMo1GKt1LI0jCOIiR6TAxRmB5gYzGqi+4WNxStwx53mD3livEEPnUCHccIwfgJvWhat9sqpZsvAz93EviAMVy3+4/m2rKeUN+0sB10B8dYQQp"
    "EotPP7EC0di22QfMcdkraNWvzFzUaEaqHNYyrShyRDAigMfqPDXcuCs1FHELdN0cTUfSokcQcFqOAW8HriM9lRv5l3wEoJyI/MsiaJodaFfeIK"
    "3nBSlJ9ypvWqgl24l4hLBk93zKVi6PvhoOeo+kJkjP4A/My5EyBjf7isABq1xHmmuxD/s1qvqYuACtO78bj5ieionpUCJmJPl6K8eoMcRKmsNk"
    "viaR4nRMMqtSniCjTCOomZyy8EXiC3Htm4bg1uWagYmoZ9MXLjlzKmo3lqwMQsKZYfMK5jhliWEM1NQAYlc3L6lGYa5xL3EuaiukNiAoVNDIds"
    "c4kMA5pcjFQd8F/CTLoPLf2yiQKVzeLBTBvUO4EhslzfxAhYKDAOqzBgF4zyopLM7jZF9EwWz+IJtfnAv6YIVAN54jcY2UkC9elVXQcz5SDf1r"
    "cWp3oX7JTtR5Eilohuoo5m3Nm41pP4gbYPiW8Q3/AN54sH/7jEODRWF153N/k4wrz+YeaXN6AVFuaC6l3MWJsB5ejG5rE+N6renisyxQJ1Grde"
    "YsIUMDjVc+K3E9pAgApLO2+PMxAgcJg1hFVWb/AHKrOyyh738QGBqFGCzekKp7OpRRUk8n8IGdVwENFPNNTMCQPEc1iu6cTMXilq7hYM7HmIRJ"
    "URKBywG1Hdwp1K9DFPoPQqJBc7IMQOYaliMm4cD0StQ1NpuGCYhlmV3AlTdxEmG47m6qFGEOScyolZlk2x2VKbi8zxKe8TEvqXfEOMy6avEwdo"
    "uaJeNwsdwy1A1mVWIiJlaKO4V/IjhXdNfiZRSuyXLHnEQNzA3wbfEOm6k8FW6O/KyxhgOfZZH9S+1b6FveOq3mB0tqOGskUwXkRMu0/wAdxi3e"
    "iyy/eFk6QbHD5ltGNEPmpeIWzKHmsoHPUtdp3Juwg3wVV5iU8+/ky0gMAq73ZUq6qI+yFW10oocYxNdi9lf1LUGvVCvzAUQdIBvin4/iOLSMEE"
    "LDLmXtbhSB2j7dszN0FA76BVefuCPaE0sf+fUGJ0RXlDbTnxE2DGw2HYKq8ZeSYoVcIOgvBWMfEsmtCj5Fzi8/uX4MjRRfV67gqK9XdK38/uXk"
    "rKY1YAPN67lv887B0V4jKCO7sxkQzjWL4g7edxWz517QCIWABpza1s83iXbtFetwGQ/4hfFbeycGzioKGU3YPis/iU0CDSB+pUVI6G6xZ/EJfN"
    "NQKuR+IfrNo6Dbx+ZhKlSpUCbiQeh2QTFDAt8zBCbyzXorqB6B36b5lN7mblxcy1+pzMkeptGIsOkG2AVFRGZJWI41FEQ13LpzB5i4uXWY3hcE"
    "0Zg47i5xCRlR8j+pYXvEiSgF8Nx63WcyoZ3CEX3C44NDpI4xbl7XkfzAjw6e4n0BBtPyy1QW/wA8wZALDiFNjUAgqmWg1CBuVA3u2XqX2uoVDC"
    "YWfiIsAgLLeV1CGqB0+6nEsZ5bsCuSriUkIKlDjcUjObW66RAUK5zCyrEBPE1KD4lAAEB8A6r+Zr8YqqiHxsgDngILdGErmY10VFiqJgMYlYzG"
    "ord7P5lxxNK4b4HLUuYO1GuKsK28cSzGBZpq+IczKIomvfzCNe3RoeTtQ1emTi6hIzwiqOd3/MFBLCUNZyIiWNlrbdGPFS7C+R1VbEf5lNiJqM"
    "GOVeKplqeE50GmDldwhziFQW6b8Gxx05l/Es7KvLln9qP+IJcx31RMhwNxbZbt2hUR4w1qLaCEHURB45elSonpXpUqJ6RiTBMZUCvQKlW+gImY"
    "4YCzJKnhH0FwgKYbgzDNTmMMoMO4FkO2oNVC7j6MwZuELFpxHVrBsiZRSoqcy5JUjQK/BG1OhAyF1pPmYqllqJ/FwBkZ7K9yMVoCoCoSaYGBlv"
    "LMe01aRjJv5+4ZjVqC+TGY5a6g8O661KGx2ltPJbvB1D+8T9i6jQBSo8x2CHbuTTTFBm2XMO3XOtD/AOTK2oZNcUpfhlSRriCtYKENDVXehG36"
    "QXFV7blrb7ZmY2sg1gQ3Q+WWAglSTfQ79jglvA1uwfuDAomrEzE1ija81yoYyQZZMN1ILDZrPMqdbTLbGAex1uGRwtYzIuzkI7IqmsFShaU8S8"
    "rXBagUdpVeJbNvQhQDhrXhzMRgDirhWOyCA4owKRc28lFwv6QLIBZSn3ln2gU2A0Xi0pw86IcLJtk8jYorq8wh8kkfqJLMa7PaaU2WnvVovNXf"
    "RGrhWjhTeN4gGka4LPaV9hChMrZx2EdUgN3qPBvvVl/VzyjFVYhE1QwbK5JTkc+Y+rA3Yfn+KUbSagEroXXlyypUqJK9UlRILl8qmkq4BcpN5W"
    "EJXoDxC+5Q5lTZGCUV6VmOFwIKiVOPQgrlmHEv3qBNxDVxKMQQi5hAygaggVLUSCNwUJcaosKMumv4Y6YYu3hd2fqFLHap/GYgBZhgxVHF/wDJ"
    "TsvKP7IDMacJdySZ5R6ufllhNqmAqdpY18TH0O1OGxrLzK6CimxaFWrbDU3NDL7qbOkCUC6pjI5feZs+awRwtaMVHleBSQWVoAQ5bmZI9wnBbe"
    "0xfEH4Ex0DWrwu87ZNNUISQsoVTFCUd3cN6Sk04CpA1nGJYBgsrGO1EiVK4/EbKHjLfzGmOotdCYw4I5rEw0IKHJWLjFd4rIbcJntC9y6WKJxg"
    "vCzQHxM5XCACvcQm2LU1Mhh1OYzKWNlVueHGZc4Wy6W6A/OowwQeKJS9IIKrmMIJVoC6YcVfEQ49VYwDyC3PdcTCXIMiEirN41H15VTtcpmBQm"
    "Xo8HdXWoqLYFCmVZo8I93CBVrDRGk2Z4psYFHALOtJANWU5ruDg5cWo0FKUOmLWdDWk0cBu3beLhyorgFDAmgKzl3KwdDeUu9UB4RhSqFocXsV"
    "8x8VCQZisaO8XASOHCi773rbkjSHtdNWJ4scrFyqxE1gKEuAjkAa4ycelelf+EjiObmnoHMbgz6VAlQO4hEzKjFRlL3EIviXqYy0F1AiXKqVKl"
    "R5mDDZKBFzmazLcos48y8sy1UusO4njMO24mokKYYBrMwLlHAQRHSTH8SWiTNLmUUG8XtKCwXbtUTI4TqKw6XhhKRC8x7HSStlqWJ/pauWkGx6"
    "94XQgruUtVDlpHMAKu2sxPYBKmY3ZypvtGN03YmfiGWr+JByKu/eZYJRWaMhkcliXi8y0ymzI+lhg1cD27CCc9gbqjEXUQUWHWTnbuFt8NdY0c"
    "SM0ZZiPBRls5GS0/MDMztP6lwdrVjdZaRxhj5ei11yO2GNo1Z8u6mwtHWkON5dXwR+UDRyiWvGYpFSobmhdD+pbgEHnhp0fIzBSFrVLcbf1KiM"
    "DVRezXandbgujS9wPdUHuGAlCjYvIO45W2ZoUfLcYj5yiCvQH9IXBkWmRLs2U+eIUFO2bi75sKalyjw5oZE5Ck3TKTIG6Cx2qwOAw1LW+rYiij"
    "QLu/dhcOyMwqItsWNwxXWYVcovBQsmvMrHjrrRZTTjmGWWIRaEFKZUN+8QzwFlCLwEcv1M6zfiDXjODqO5USVj/wApEhmcSJBE9A9WJKr0uJ6K"
    "zGX6EPSoxz6LmDbiKowNQdsQTN7lNU17RL1hhh3GgvmLyRLkKImgiy7c8RllR1VwsrjnFg64QBlUlXuLmweYAqK7CEFuYBz6yTmTcrRxAA0tZ9"
    "yanWCJAoGy/MEqyUWgWa2QPMWxhG44KzvNt1glj+fBTAdIZApAaT37gINE7MNxzYze4V1gV8y8JW1+49UGR/dwhh5o8NRHUVxbUCMil4XnxFQF"
    "oaL1MvCjOWIigPtKCzcETdEFn0y0kLUX7gmKPe/mKVFUNOFgmGpvTTkWCgQCoV6aZTA1iIAaC410N5P4GKBcc2tz8kdxcvVZtBh3aBB/iC7Eqg"
    "4q+CXpjCKntze+4TgwlgRA1g5ffmXer6pW0FZ/iWyIKG2sbz+IaJdbKPbCNzh2g/BG7L9L17OdsxOsp/wUiOHvKzyIyoeJsACgOFAotfLEoTQa"
    "2QMt6f8AwkSV6sF3/wCABUJRKgSpUTEqPoTEWNS5cPRhH0qIyECsRUwxuZbmHtDcTiVcwHmOS4q41Fh6TUqdogWYgyOJmK1B7++hcLjbad+8Ff"
    "ZyEdQCXgcfqZbJpGpXvm5v1DKugiaaIt1t3MTTXk2MZjyN1OEYgcAbZOsMwaJCDkvPNF91HAyI26JWccdQCLIuLwGDLKBsd9QHAjY1Kqc1ddNT"
    "5EWAt5jdS1VMzL91pkqfHoFoeJkRNlwzPGU0Yw5l4FspamAzNcYg08hlcEleBHd/vUxJ2PiDhq/QkmUUrLMBy2oGpnVYBl9okxoJMW2/y/EC1u"
    "htysAaW0LKX/yGToulX9BzcDJ1gXSEDrKFeCKV9CA4SvQ2XRG5xcxGM1eau6vioyYg6vnUMHF2xbN0F6Aj6J/4YwemvV9D0xH0OEucxL9CVLqD"
    "qX6B3EjDPpUit4nMRUWiNncaJRG3NziB3uGs4jhvbHeZvMc6i1gLYnmapQw9MH6oOUEyvmUwCh3FY1R0rKgCOI5kWcYvMSkDwWQxYmxFHRqAmw"
    "jtKkWNWV8yiAFrTCQB+7AoC2jlgr5ypYjrnqYBcMCt/MJmAbBFDt7fcBMapfs+fMPIEtAUsr4jCreAPklBMAcyoHo/Ec44hU311BbqzMG7FSpd"
    "8iy4FlPhEDACtQ7YC23FMD7hlRNLEGGUt7Vqql249iVU0GOJj5tKLrdfJGZpM3DdQELvdQ7kOQykrFUFqV9MXzg63f6p1dK1PJzFVzC3yOQ4+I"
    "OmPNbLpt7VruZjJbqe4oVysgxpO4Upn8xymWNWBbWYPTiPo69H0Y+gejFh6G/VpjDeJU3HXoql2wyhDfox3A9EwXEucMVNSrcTzF4NxYzLPmIv"
    "PqzUrOY3C1ZiLxuLJBeJezEBaYHYxDIbtsiCD9HilHLDqslzEUOHvBEuHiVppLqAowtvyzJ8ll1lqMzsAWHiQAUYfd7i8asHI3DQA6zqUUY2Qv"
    "JA3tUHZ1Hm6YVDhkzLy4AreguZZVuyVKGkUHFM2wLDlcwwgVIKsEG9pdRQwTarqGzwP6iS+4egUDa1Ck0Z8sxoalW6GoiZYhFqF3Fw5azGLBWq"
    "wWse0eHuV2AvwtmZAoWhhIUhhIJUlnI0mPEbxp7poT8QY9O/RNLrNXb8zPqlVkfmpdgcBki6Dy1+Y6OuIzJO7B/ESK7m2V2f+vQ9H0SPoxiixa"
    "l3K9AYS5fov1YTSOoLJTLDFiG4McyoxYOXCXN4g6VASe6AxNJB5gWXqZSOJxHnEylVGrcVMBfiAjcUHKB0exB1ma4bexL0L7lKLYlihxF5tQx3"
    "KhpgDUM0O47ELpoXcpJdFUalyygNcy6+U2i8QsiGo84+YlwCr26/UDewNN3j6gk6gb6Y/lHCW1rcHkx+SFo6HSEaFtSbVfF/U0w9yIWL7RkQeb"
    "cBE/kv+SoO9ho5YTU4ZkymJepnhgbfE0lr9pXnn+EU5auoRqqorE0i42cBXaqD+FgGrUPF0jefEUKMXCnWP8ys+wxbKQUc3jK4qWm1sso8ylku"
    "2yBcRS1vCXHKhN44iMiaPKjm5x/6ZcXcXoeYsuXMlzBLlz3hDzFjqEWJjEzeZVkIpIbgSvUZlwtFf5ystzFO0VTw6nJBlxHUftNu9St2bjdVKQ"
    "icSqVBMx1TGYFIvtKglGbyu6xmLCwReI2K4jcUl7sYmI2Th5iyMhuNXQINF8U4jZEA6HzDUqFcRAhMCl3XOtyhlawFha25Ra5vOYoU/JT4hnlW"
    "By33HG1VWn8wzYXdKLr+ZhOgWSDCvpdkor+5qG2g94cP3TjH3E0Kus5aAPuMcNblgGwzVEwYJZSIq4lYlBJxAm2bl0AitVMSYMsCgCe5UGCpFq"
    "CcF8rMf26fslGyy4OhcVKhb0srqpRa9eCpUSL0ev7liED7JycEBwu6z1HkTGq0BD3Wx2/+WPo29CzT1uOYmYSsQInqCZGJcSV6KlQECo+qXAQP"
    "EwUuGcjJLAguXzjzLLWJi3Kt8QigHllLWI5eZVOWbaxAA3M2IG7ilxQEGicYiJXFK5rxNy0YFdlzAXcupe1oxcN0iExDy9lQmEvEKXTD8QWxYG"
    "lYGgR23cT+ZGuhf7lcsfzDtAClcMpxFVU3Vf8A2HGCWPUIoli5gV1VX4XDg7Xh3GsbKf3K6g7yxbu4ysGDpjqpxFO3E/UNeIvRBlAVAGIiAWLG"
    "Xmc9Q/ITnDDzOgA6ItF0TCkFKX/tTK2cU0/TAVR2d1CSE3iBfUK902U/7gD4h6/MKFqsVoMcXAhbjdK9uSBwEqGqwvHC5TfDRXZZ/ncd+r6Mcx"
    "YosxjGo+hGcwfTiHqxfQ9ax6KiXKiYjAHS4g6MtFmFd7S6qmUSq5mKVkFU8YYQMyvUDDCrUcf4mSeBORy8hyQVoGBFfmA/OXV9xw10EK/CrgLO"
    "kK1fYiAFyYPuAUraMzdXv5lyljjYjrUCryOyoINTTvmOlK4zshXsAwmVKuLaAnPpuGOtE95dRbKDKULpB96mVqrZx3AHXIB7g48RTJBaTcYS5y"
    "SZMkzw5ZVC6ahDmYpjlWDbn8Qe3xMZ2Es2CEl7qv7ghh0L7ZiSdqvMy6giQ0mZWaOsMFFM60XipRJQgfUFYAUOLaOY5BQw3NccEqZCr3x8x7qt"
    "YoxjfnLAW1F6kTiAJgN0i2XUa5OHIAY4g+txYsRuIlLd0JEHEd7lE1zFlhAuUdwMxI9IRUqNJUr0ZXrUZc3KiRImYyiVaESQaxYry8xRNy0W4k"
    "JptwfDLCEPcjgeI9UwqD7mAE1yYiOCJiDXUcIMBFJmX55jXcsScSCUym3ML4YNFt3MVuyNU8TAM8IR7epfzXEaDiZCMBrABrziUdg6ViC2ieFC"
    "21cFlFlRAT3Fw1FvBYXnxLJcbBuqrf3EtyrwuaoiGu709xal0W+Zpxhi3uU19R24Zl7RpdXuUTAyLIHvBYcwe1wXUwz3ll+SVDXzLXzcrdhUC4"
    "tKFuFhkdfEO7KzKgDAfmdcLidxlx7wLw0EaYZpuZ1H7lHsV9Y1MC1nzCoCEXF4QtVBDWveGRGjbGAEcCkbs8HmHYC8DxexLuG9oQ1cBdcFA15h"
    "Llxeg+olibVnxHmxemKC7KuVuFuvaACaGmXdrKxeJj8ADeWZQAHDqUaQvVZqXgEaxEi0uQM035SWal1is3DG7Uu1hjY7AmQaYqJtAtLpH6jwLc"
    "tHGDVVAwSjdsOi0OM7h3lfxcDYKL8xOrGdSsFL3mWt4VPWGEqHbOO1El0lwOXMHd04efMFYyxXZvZiLGK2ai/ioEXSANGdtS+hDLNHzE4YxZeI"
    "1FRswrmrldxzMy91Ub4RvV7jewmnmItzLUxUuYhHctVNJ0vMOwyXKV9pDqecRJ7EuDqo2XYQg7l/EgumxGu5nHKUFYXLqVsCBTmAqpiUTF8XJc"
    "UOJWU5/wCTmG67Y8WFZpz7xxPdv8StNFTqBQ1b7uJUIc4i58NMFLJ0tjGmWKd+jAKfeKfRglotULsBzgjvWVwlVHHL5hbVK2MCKA5S4haO60mU"
    "9GIK+EoPeNqeYqVKCCKNjX/dzMO8XwS8KC9pQf8A2UVlQAZXiJQUn/hGmmss/U3eFSVqoM5ESBnROWj6nhxHAoH4h6Po39CXCncRereNS8LgcY"
    "qWNAqzP4lRVRhxiUcLIadMGKbCkNMSxgXlkPEJI0UrRe5eRPHaPtRN2w34lQLicicxZqgGBjqGLj268Qi0nFjRBAGe2R6mUvDjyxbBedNYltUh"
    "uvxKLug2Ew+CGoZBtlmyscQWnOrMntLJLH2yQStDHxjlAW64Sdg1dXqIxRWLgnCBzUUR2WUl8gugp9niW3SJIs6PJGmSDVuJSzSGS2Oq16YhS6"
    "GYumYmoALjlmZmIh5uA2uYWbsljcZwKqD1mYOIsoPyyK3iv4gqBVPtGq8COkdsdJDF8Esv5JSiwi+Rf8RQZyO12fz/ANjKDZNhDGGxL3CsUBQX"
    "d5/7CQqvFyKsMIvVuR+JiwqsjZaX/M3C83gNysFllPeMnUcL4mwaDQiO4CjogaSm+JxkiRymTm2FtGPYhgK+CA4MOCYvq20NDC5MwriI9xwVHv"
    "Fdlj77ZWvIgjWYJyHLiXJgYqEN2RqyWV5VXNWlfqVqJLN2rmL+FBcys1JAeOu4wglmSdH1BI7AxXEsYk5QCC8Bb+JQb0Nylqe7b/4Y+Yk1uFiu"
    "SW9w19NkpWHsh1DlVpcV4A10ZLBAHId5Ue0Bn2ZboVxQv3lLPhdC39IjgwyCt8G7uBFpOl/uOFc590uFwc8wGlVGKq89Ryg+AQpbzrOLIjanFr"
    "8wDAbKc/uY5gayVOGs5M/MxFAAX8RwQBHGpS5WvDEHut4moEA8kJZIixOOpXIDwltq4vN6qE2G3qxIdRugq8wApjesVm0K3LJKUDZYAV7sCgdd"
    "ZYrjMAgDX8InglZowcTNBpVtmL9pabAAqL/qiXjV3aHj6mMnWFlUWg0YB4iynTyEWolc0hS0xjVQZvmLrDUU5iRz3MG5aEppPD/2JZjmH30UA8"
    "yiVw+MxB8YLJavYinNCn8XGDAXgUdzTic/wgQSiFGwz8cQGCR1tCpcpabyiM46ByuGXEt0/QUX8QUCwCQ+VcHvEqKUoL24xw9v5iBI2o4PnBKg"
    "qcC9CBfmFZVGt0hb4nPUPYDqz+IutCQu4J0v+Y/R9ibaV+LZswWinsWj9zKr9w/mWiL/AMNRmbQ2haZsvjiO9xnpTgurhzrsXRU5iveXTFnAr3"
    "QqmedQYWLu49V2g9gWm214+5ftW8uIqCAOLaBxmYD0AGDFvyRodfGR4iqAMG+3UvtB3a1SuCoO1/uDlO9i87WaXd14D+PVYpZEe3xBs7iOGhnc"
    "FZoqs4gFw8aJUqRsT6uLABvl9QWChyph+vuIl2tqvPmZYLLN9tfEU1ACQH17iCs72wFX73qBhW7C/wCku4RQsplghC3lOKjRmPFEYqAnezDrJX"
    "krUonRfyiq8Rlma1Svapf2eQa+4wErBQxFCspsxCCDy4XMeIYDQ7gbSvF1z7ygFKcUfErB2uXmBWnu5hAHB/sRTQK+xGKBWNqv9ZgwjbsIG6M7"
    "joA4Al3avjirjRArNmWMPJMRpSjJeOSN+LFSEV+OOP3E6ro2B8YmQdGAt9XB8Yhx3g+ribtpu4uum+fMTFo5BuFderNVLiRobsZsFp4gVYVOAk"
    "olO4PcExcTXG/b2f8AJjmia64ZrSrHuKw9SqrcMpVS5tcfNTKkS6rUupZ7CIzkxVZLggAgBcrwIWtHsVW9vGGIaruFjEwetBd4uBBKgKlIsRc+"
    "gCEJQl7EsKwKGiy+WpWqwTW0Eu+/mYvRCDTplluJh70H5R+ljpnE4vyl+2tdLZcC7WGqnPyjd0hHQ2lqA+33Buxzqxx1KxfahQMpqHdeikAbfu"
    "IIkm8A98wL6kQBsTNxRS/UPRZUdS8y1GyouKC4jXd+0W8/bmahrV4mIWYvKfqcdRsr8SjBt82L7yoLgLxz79xwJZV0riWxFukWxjj5mah3SM33"
    "3KvtqEh9JMh02B5Sy+FAq2WbMgvAMBWAcU3FyJcjbEW5WiXG9lDyHHj9xaBRpWJZJHnUoioAFb+eYkG6bwMQZiQNj8pOYUujL/sLpcrbs9l8x2"
    "wwB4t9StKVPAeSDfRQdZxFUrCwNYbr5IZyFLMDnk+ILUJDWb7DqFQkeNXTuUAkKGoXk5X5ZfrgMqK5zrzqbE0NbjBYrxXmF2YW27WRVfzUTq7Q"
    "DUyPKeSAhGhClvOV5/qP1mIahdYttVzkgZvZ0jOOfP4gE3XMHf31LPAbkPJY3jNytL4CqKZc/wASxJo4F4llCuDLD/UWG0Vdx+YVbPhbKVmyFu"
    "T+Y7x/KV5XYlMK6lyxycVHBIwPuazYlSqqBdF5/UcdBUl3R19R1CfJFBHMe0SvTjcrbQvRRAtTljMLpVALkZfdfxEMgnlB6LwKxYVYOfPtUQaP"
    "lo+6jtJNP2moPnNRsj5YPziKk/QYPdzUpo4Ls8cxHaiwZ7LYwhIggdc0QA0GDL/iDvzMqzuWSRzSpfi7lceqtRoc8wQgmICQ2p5lC3YygDcSBn"
    "EokN1hm0GnJUoDi5WnfoyhVVYsII3gzkjQ1cYqNETlRX7nKsjQWcEo1o9x/MtWwDFXFW3mGxYldxeXNGq4g+mZmNx9pRmyUMsmMVxLUq/iLYBr"
    "GYOGyve/1AiK8ixcob6yp0/X+qKrTazo9upozbtaLM0Yf4jWLaL+CWYUKoK+/UoAFV4DJ+L8wS4NCV6alhk424Z+YR+9ZVqUKqxWbqXZhP1LeW"
    "DjUBBkKVrLgJhhgLsAe0CgFKFGa95WBgt8n1KnkmAB+CVMzBS7lti8roHIyoGOBVYg2OWELBazTm3/AOzcWN28dy0oAYFplYFTQt3epgGnSJcA"
    "QrQM69onbLUSz32wDPdrKfUGVwhQWvBG1AVtQFvLZAOwJXNb66jh5xYjZp3CUrSSh7ylc3WMAMBVC+Td/ZC0x0bQOBzlgXaHQ+jX6YMqg2j5mm"
    "waRcGU4Vcb63ChW2gdvUVQNwN3EVw65nvCXU2ADyxV4X4hnWYDnriX1TEYgjbUeXc+si/jHzCggL0p4imi2ztWLXLPEdHlgralkLJ1C4GERp1l"
    "6z8Y1g4OyMWIVwYio7W/DFhCtlURWxKtOYVmoyWaiF5KUav37m6rwOvqCKK5sfUW07VHH1ceVn7o6+6GUYZWOH0x2LCsqq+0zgjBl+GzUyKg4p"
    "w8VNZpuxW+dcZ9yWgixUm+tZg1Al4D9kMS+lINEdDw1DQOmXR5qd1CwsPaWZVV1D5h6FVEZcrOGFJyFAOeiDEFyhzpTit37EHEuaS7lxrlgjEs"
    "5CbF8RzWHfMcjO6IEorurjQVC7brj2ZolGsR/qWoqS5H7GJmY0tVWuZSlqVatuS4AsUNXlUKAY2UlHeoiCxnO6+H+J7nBVxxNsxA8e8MpOy1/i"
    "GDA2jThudA26HbFMIBi6PiWqh2OVXW2DkQMdPvAEGQiXblhDd7IQz5mEJpS2P8RVWFCh77g2yy5SKq2pL/ALoAhREFhOd78eIkW2F3GxxUK733"
    "A3LO0KdP+3FyVOQVvFtrLWF3bYqKbp6w/MV1S2Gbd6KlkqjQpPn8S02VyGj/AH7gtYWD2gza/FQC844mFYb/AFLi1fcNS4AU3XvEUiqutykNhn"
    "uLRQMLi2iuXcEQKZcTPfgIQOwtlt8+zESjMCB28QYC2P5EX/ql2JzUE9kWUjdA8ZMcwWEBCppn2lUqV8ivMN5Y7+f0xBfSVdGPiD1ThZUA78j/"
    "AHEAGGyafyx3JZYLy1/MNoiNkEOLaL8RpC2llfkiALtYJsrWDcERBltNXC6DlHP+IR1FRaBW7dHsy+FsDpTp5JiaYk1sMVRq2zcrm9VFNDJhu8"
    "VN3j/Pdj8wGZiXd6HUGsD4HMHyr2iXEawhyA+ZsFXcOYjRdvqKzELtpxUC0v3AFjLuoZu+MlVFu9HuUPglZlYKLA4lZG4SRCkYj7miwhcX55j2"
    "6im/6N+YFmlFCXdVKxV9rH1X8weYCeLMNqxLFUNhWJSNbeyOtDGCe7UqWHMNjjDItzLDENNN0wfeXXcXzFeScD8xYaMxulBw3OYltFvMbYJwoX"
    "2gzRiztGXYxqCKTng+Z+4FPHUQNBw5DaXmWwEG1NebizEGTBv2g6/GOn5lIxFrC6IKUs4wEXUNlwovSDEx6Kln++pYLCwrn08wsMQQVbPJUQOq"
    "LTdxndGnR4/qGhdNlqPKtQ1i1eVTFyS5NnknHRLyPNEpDc5Sg9Zl8EaUyX2qU7erK+Nj9y9GI5Su7S69rlkHW8A3+oDTDbRVXvOwQ24/NStYjQ"
    "0Od3R8RVcM0A5e+4iWIF6a940oQAlXm/a8+JQjhtwjloBYnk5gg2on8S6wOL2MPP1KCuKMoMqeW7ziY1O2KpbeMuo8DeoGlWxgf5bMWYOnOYCA"
    "SmFePPmAUKyI67YGIIHypM1FNEXYqj3uCASWpX8GoIiKGusvTmJVeLKmuX/m4CyY4dr/APkBDQMuQ9k5/iEgYhp5bDB3GukqtCqc48UVL+pUAp"
    "rdBncLhOwcOaMXXzx8QJTrQAlRmhR9cMMqMLY4wKGTDcXqxQ8vINa3iFO9RbQOwL19QZEIX6HCfPEcQdVF5xszxvjEUHGt6t0GnXXUYjuzWves"
    "s5wy1qGqLO7Bv89wyz4nAO7W4TfC2dfb5hFaqbC1RbRQ97hegmplbCrz4ZWK5isWE7e+DN8RoniDIXJFlO8ROHMU9DIErDp9l6l3hDlwF1NYYp"
    "fNTho4HBXxFgSKUMPP4I4lIJqGQRy0qJvj2YWabo075xv+46CkIXHDqqZ7rODKQhdQ6Pwbp+txqohCg45w/r3qE0fMlr5upu8KQuKC30xg5gkb"
    "bUMDWAr3leL1dlD8ViBlS2we7kqXD3IEFyXv9zPF9CvFVv5l3od5JvsRxz81GoELi01mzF+0u3Jo0cOsntGUIUZr4WoXsELp8NO4SzyUh+Dm8w"
    "mpQWuStLoffcsGla7N5axvnuV2RyG0q1Ml2WLqVo7kX9LzjftZENsocJ9uX23C2THAnBTlEvP9SyyTgBHnJXTCytgu9baq8NXLoRiTSgd62YYp"
    "rNLVpW0eJekmQQQTmh9s2X5mRRBACGS+Lav3lsFJLF4xqmONYCHDDlmnioYLXSs2x3Ylik9sMvJTKD0DPtGMxi0eXhgCmeF1/riDTYpWXmXGUC"
    "O3IuyveV4BdNPj8RGoLTQ6ub12aTHBR+5WZHDZw/zKF5uwsNWf/JnRWmimngf/AJDKuiOEeLDfzVQK2lZenLVVHUMn4TFZ+4UGFgKhXxmZ+lc3"
    "Sn5PncTSHRUx+ZYaVrA4fdsQxRKtDHw8QyzKW1X8Q0uwHC0IUUKkUXbyDqZEBKI/B8nmLATL2icTKvyBN87p5gG2zAQa6cfcx4fIi2s4jYrKkB"
    "WN1ULLkGQPf9RruppG/ZNOSFMm3HJVx/MaYyLTVTVqvlUKzGZ/gQqhxvB3MplTcDGqUqm9f3B0jezcU84C20wWHxFGUBDpQss553zUAuuVlnn2"
    "wxhnl7AcoCz3bruMAiyVQ58j+phIYIT24rWNxMhoUVor4VGKkU2yzrHd2SpbQ2Zu33nUbC3LvQL8fMKFASzeRTGJrFoTB8mazmZfaxBb0eZouS"
    "2Q53rXTFBXbnec9fMuTUAOel8cPfMsshhAq0LxVREBjIBbDzFygbWhn3ZWsqMtYzq/ywWNHSs/mVKUFj0OsspPQylXd8pvuAKsbopa8n8XLica"
    "FcMULTV5Mm+ojbx81591809xW00IF0vNJgsrVw6SIxe2BoYxcUamRKfNMGnD9QPfNZxdWwjxb+YLoQpamOMbzwVEL3MiXPTRFQArRtznoxWesE"
    "xI9OAOQG/CJXmZA2sLF5pKV2XjshLD6JLVVM1MdqqkG6ULtv0tZlMbyxppSJVG6UpDiFKhG8vyFXe9ndRq6YFwejRmturiXkRDYrZZNI4b+biK"
    "VXKXHoUtm+IwIGou4ZU2r7QGgdgBSnm68xBuVRoEsrnNcyzngNbuqd85fiGYr2ALurbfJ1MFiDkM3WcWfTCvdgQ4dax7sFuOoqqctjr235lDFQ"
    "ilfvReOYYED4s4bpfwdyhtqItLWYOWIoCFmn2F37cwyqSUypugbfji4k2zoS3hFxr6IAiRehdW5vDjPFZohxfQ6Epu3Wd/9iQWblBP4NZlN4s2"
    "xwRz7fiCK8kEpAmq5OKc3C3WDCAsv/czEUaMBvLTaNd1LMibaoNO9XfXtEqWxED7bWucWTCRVAormjNX3/yLS2gYOQm8d7gFAK+gXalrv9lYI1"
    "LuuMlpWUAb4E2RKDw0rVjZSh2ZzUQrqoaWqg4vODvOYJRMAFXhoKZ25pPEUZgNEDwAxmt9wDVpfCJsqhxVkvxSooFVtB13KVU71X54MXXtBbNW"
    "DbYNbvOosWYNqt+11HUDWRa86a8x3Cutbuxw6rXUx/Faa7zXNfecQKUzZZacrzQwVGy5xchda88ShVZJCl54bYUFq0F4xV7joctgsnji5QGlw/"
    "LHMQyXS0otfmMBou4CBeWzrQav3+IQtELFB4rgisbd6HHkhAHDoF1C5Iad2eL/ADKGcpZhr3unxMwKcghHXRuWdXVQMe2b/wCMSjIWsX4fzHzu"
    "4Lgc++S5ZAFIHL1v/e0thoFTnrH9fUEeOwNtVsujvnqFgp3rCoMsa2cuZhAgiKjeSPiQKH3iQIp5nHEojYTZG7wicwo+CYOSt0a/MewnwSPkwf"
    "wgjNllhBy/XjuLBQUmlXmrrHWdRxpGikzjesMuqANYXed/T7ljTRE8jIa7wSiOQabW4E31k49oMG00MTl5qnHzAKqLBEraLkyX/UN5+ClOqvX1"
    "7Q2nSotLGTe27s6YEOAS1XyOc00lwLIxK284yIcPONRQXCQDxHVa9vaPVBWhB4wYRfdCpTSuG9c17wUjCtgnTmDBDYeg5P6xOTRRmxX63CAAs4"
    "b8XqbW1tY/0e8ddp2tW/GI0ynwD711OAwjakbMIu5eicqWKStKmPI4/kBuY2MULhT7aqVhDVqktwd53LzTXYGwvnXMV7nKjyvgxvUeoJkvsfdn"
    "Pe4pYWKg6qw+/vZCTQGxZcYXAs6uOjw2+0NYp34+4soQLVNYWn2ZULMyo6zZtryZ2zT5YsGqqDHVVqXlCz3mLmq72zN+BQ7rQpfxVvuw0yRaU2"
    "LQU+wD4qFrzWBhlNlt4ynUXkHYHennj5qMXnTK2fFwQhx0mW7cH4YGMKsCDa6pDuIRXaBBQp43ezHzLKusl4V7NXKOxYJXdHFWaa/iECLChDVl"
    "vDnnfcsgwQ60NrqvmXju2uWl5V+m+4V2WtGB6N+RIuALN6m6zqlsmeQRQFgwctW5vVwqwBrJutAjXOzuPa44AS9CqxeSrYpdIMCiuqfD8y+0vd"
    "ZLel3rnzRmF5Y2c4yqawc1qZoBQLCxkyq4oMQag7qv7eITCvidjW5YDjZkV4E5xeccQvCpoFl1V++GZeqope7qr/xKXVDUGy6+LxLwBGyqqoKM"
    "FDeZTCc9ogxbDte68RWFrxwc6w+eHuNUGFp+iv8AYlJFTAEyuiz7jHat2rcFl/cPW8HKSsr3fngiAOvSja8hbPzKUSoYaGwrk+nI4jWRgVXpav"
    "SuGnxcMtSVgTaUjFfxMakFYU/DO/GY5+rETHSg14oSZchjQLbnNu5bnLFSleQK8aqEwELFr0Am/wCYyQmmi8tm/YlILWBi2bz5vnnmGR/WIFKs"
    "XS/EW3mZqnm0OnGYHRQLc27GxK4q/wCYsF6LZlNGXGX/ABFosoYh3SiGGpbNSASrsBqgzzqX0MAFnCZeqO4vDeQtZ5b4/wBUQmzkZOsD8ypaDY"
    "MZ3f8AaEAAyRAPYu6viLewCMuC8+H8wGNdAcO/OfaJZFWaE/Tl+4pxX3SbJbmV7LgaLbsu7tm1Wc2pl5hJOhTNfMNuBZFtntKHQZL0XmxxpzyS"
    "1DEuLsyhiv8A5LjCMqB09b2kPtRBfjfOzEYUkFXo3oHiKINSFdPcHDA17IsBhXY+XaZAIVUBqgUBqvb+JaIWhrv52OPeWZiXpY5qvPuyzCkUFR"
    "zYNd3nUIgQkqgyD6xjcacxrUh3VZOa1XxLGJAhfZFp5z7xTIa2t03V817Z6ltuAeBqXbWM3VtSgWgRkEdrm8VeOJQY25AWOeMcRl2mVtrxoQ6v"
    "zDsMvGhUri/OKmQSwCxVd+/9dwAAq3k6vDEwvVQavz3MKlqwsaMbiqoa3m35hjEE9wZMXmILq1QeJjrorD+YKWNji8jxL6N54i93qcWJrV+Q94"
    "mNsMgbvdxZnRbrXIWwsnMAxvSm67xGRaVtgb5q2m9+JhrGWlWDvVsJa15AGbwvMSbZdOxdI/PWtQaNHFraRJZrPUKyi8IpvBeK4mTJSUCl+DLn"
    "TKqRpeIsFvZ8JXmOcXcPazVVlMbrHcYAASlPhlyNb38QQlXCimdGdWVUZ4EyA0ZHNef7mcu3eOwqwFMNVqUNpU3DjNcccxUMPWEZquTz5mVL5q"
    "UXsOjshLLxnhVbdHTiszJAF23dGzN/qXISUsKzotw9RR5kihXH+YbqJVvlkdN8RyBEFJb49/8AsbCECK34xxxKFgq5a7pqnjceVmINKMZjjrVs"
    "AY07p6xDKJZQWI2+a8RuccAo9kdOeZfJnygEOcWVqoE9W2sVdBlje7MLl4N3R9TOTBQotfDB5SyCC8JtRhwdVAUrS7Hxxx8bjr2EcGxeT4v3uC"
    "4M4t8btHBEUK6wfoNkeKSZWaI7aOFvTl5vxVTJ66GQ8WNdalvfFLTon7iitiYY26PNZzFWERrT7JV88RVeYAy3DxvOoiN4WSnmj+pTWcIsxCrr"
    "zeLiFGVaBYcM/EMe1oKizS6eH8bj6ZYnM1bhn2qZeVwVI1prvd3c6jYYyZw3i+50jRccivI1ncpMklFHdho2XVTmMCLAg7zr/kc2XLw9i/3Dwr"
    "kqQVrBdZzi4AtdIoEVXk15JnA0DgccK41HLuBVO3nUH0CYKlecd3wwjM8SPfj+JQ5MrkFbwTcwZ3Qg7Gtf9i6zgOoOMPPmAsADVCq+paCKk4fE"
    "AFQ0EFNTebA/mASyyrPKo6A1lHbHzCE8hQ0/7E3c27XbOEplhoAcORCslxJ0l3Azmkq/uUcqRR1qzZnmHgSKOxQ5ovHzAS60cI5TPdbi0UthsV"
    "o5rXGIQET5VK+rMj3gydyXRaxriVs9fYnlxnm7/iZOIJSZyp0b3Kq5oBaF9LbreOIKyNMAKfDmBFpp0XHqFKkFXUPCqyvzAswFVpmsH+uAlNQo"
    "QBcrjNMzKShizciPnVYZXB3UcnFMP3KolhYozfHBN1hm5vQ5bgmW1H7zNfJHFo04GTXPMeAiKXg02Y694PGO2/KadZvMvWhvJaeFl2wm8dntHk"
    "axeuI4KLAEasSJU32n2rmAwftyRyCdJRZ7waRWFGDiohQUtutQTgaChYoDEcIlnI5zV4lKHbCuRYKO6z7y7oAFgDoqsXnP8x53ZRy7eUs2eMEY"
    "pdRYByKx5/mB5osHTigUsQVC4Fop7P8AV1GcnsXFFuQ5o5loKdgNNc+E5NZjAliMBpQJN/zmFlLZszG63eU1TjcH4gW12Wd/j4gm6o5TOgr/AL"
    "qORCxALfbXD2dRuL206Orq1jmFcCpSOtafEoiJgrV68fuGdBxMed0ekhFYCGpPBw6uIIlsbDzz8y5BVosPMqbK6cyiikVxRxv/ADBtMBKRW8m+"
    "7h1hKLBT3vF34iHBXcb7zv53DSi2wAPNVlikj4Zq9yBKmcyd4O+b8VGBsKBfmxNc4ij+aQo678y7pAQPxQeNXiYSQtk8ge/eVRTdDy9suv8AEp"
    "Ctgmjk7RE+oxMQ4AFPh/JiVYSZQoPyPqLmIh39SloDYqLjbTWZiBSjk1nkz/2AF27ZD9vziKbupTAqs7uKuQCKBwclO3H9wk6EJY4Pcz5i6EdB"
    "kdXs+5kqjSVfm8MpIKogXwZ+Y7BhWFqdaP5gA00yLVabL/cWaiVrvnkF+ceJT3Rwl1w3lj2WEXdjfQAlUzkBoE/hMRe9ALyPAM94gQMBIqGtuU"
    "OYYLHP5xnMLaPgh2XDpKsNGjqs1ccBAbOg+OfiZUs1S3dVSXjvMMMKrb2aH4iAA3q7GzmxKgsKwsRQ6cEopZvmJr+a/mLSUaE5lnjHiolyBzGs"
    "QvqBl1lr++oyWTSULXGtwVABkKP5ZnICWrLfUQEOFjePaNmRPRv3sl7V7Ah7xSkp97cb4m8vmBRYwUko1buuGGCgOKqq9peysvFs2LSn1KAwPB"
    "n7mosLa12xeE8LGr+Ii05rVr9rhcII6lOs7mEeQxGENPMKAZY2pznH53LNNVovBoTrUqNsAKUf+y72oFNB45vfiWSqdlR4NL5JfZDVEU6N/jEs"
    "EGclJaEOK/8AsfVIACw+F8kIvKpijlBvuNKVW7v/AOofUxBXnWW0YrEFBT4I8UwoN/KjZ8zOZFXiLUs4H23MhBew0lFYW5Xt4gDKy9NSqNbGiK"
    "qgC0IFy1d2ZdQwAKINDmaBCB87wxV8xr890aWtvHiXxqLpTCvmYTKgoUvf2N7lSYEbirc8b5mbTS9Sw3TQ8RvgQAN85/mOKjpAd+Srl5WGjaS8"
    "KVWPzMIUExWXF3f8TYPWKqvd9/mHjbJnD78/x3GBUOG3e2lF5ddxIIhpVPKVsxuMcwBdQPHvfEBgAUi4ARWLwDoJMT6qufuvtM0XJYMGNXx1C6"
    "lFt4D79yqw2YIWvzBCqWQUdDcN2w2Kk8OolwFyKRa+8RLTZpeG+U69pUEsWobatMrr2qMcFht3s5HeJXZg3Ntd5jdO6IDPY/xGsLlcZ6WNxqkr"
    "FlITO6X3D1polXRtsr/cx5IPLnWzmAkXHDAfeYgIymF0X1cFJvGxZxi6xK9kfdoPEthAttffzmWXirbr5uu64I+7pGPXnnR2ZjhEl7Xdh2x9ww"
    "q0bp4jIVko0HwxhbEUbL4sMSmWUg6BmvFwBlULEFJnjmZRy5Qsrld/hjKJogbFYoWnvGhDIBFOrU7izQEU65qz9zyPNAKwmYe93MOtwN0eURLg"
    "EEFAKo17YlyFXBu88DBsGDd/xc7EZameiIU2NFF5DMQnMVOXn/s/ZDXvf3NPu/U498Ycw1+Ufxzj4n4T9z8v9Ifsm3+NM/IYfshL8r+pw92afE"
    "0z8pnP3ej+/wDpn6c/r/iP4f3j+b+2f5vM/wA/t6Cf6nSfhofh/wAz8Z+/rg7R/uyfhf59a5H8Td95xj9TNnvNHtPzf8w/I/mf5fRP9vxD/N0T"
    "X/GiOvtn4D9von+bx6efhs3f5zNXz+2fgH6J/udz/X4n+/uzX3P0mj3f0T8U/ZPzP5Z/pdJ+8n5f9s/A/T0TZ9p/7PBP9HibP90zZ7+lPyP6J+"
    "7H5E0/M2e38z/R7Z+ch+L+0/3eE/zeSG/vn78/O+gfsfxP9Tqf5HifnP1PyX8T8Jm7/dTf/DM/Gf4n75+C/c//2Q==")
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
.util i{{font-style:normal;color:#cbd3e1}}
.util .badge{{text-decoration:none;padding:3px 9px;border-radius:4px;background:#fff7e6;border:1px solid #fcd9a0;color:#a16207;font-weight:700;font-size:11.5px}}

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
div[class*="st-key-gs_"] [data-testid="stPageLink"] a{{padding:10px 8px;margin:0;border-radius:4px;background:transparent}}   /* 줄 간격 넓게 */
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
.st-key-gs_parts{{border-bottom-left-radius:14px}}
.st-key-gs_background{{border-bottom-right-radius:14px}}
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
/* 블록 — 한 페이지에 차례로 이어진다. 테두리 · 이름표 대신 블록마다 제목 줄(.sec-h) */
div[class*="st-key-zone_"]{{border:none;border-radius:0;background:transparent;padding:0;margin:4px 0 64px;scroll-margin-top:22px}}
.sec-h{{display:flex;align-items:baseline;gap:12px;margin:0 0 14px;padding-bottom:0;border-bottom:none}}   /* 09-30 — 제목 아래 검은 줄 없앰 */
.sec-h h2{{margin:0;padding:0;font-size:25px;font-weight:800;letter-spacing:-.7px;color:#101a33}}
div[class*="st-key-zone_"]::before{{display:none}}
/* 첫 블록 KPI — 페이지마다 카드 수(4 · 5 · 6개)가 달라도 카드 한 장의 크기 · 비율은 모든 페이지에서 같게 한다.
   한 줄 3칸 폭(6칸 격자에서 2칸씩)으로 고정하고, 덜 찬 줄은 가운데로 모은다 — 5개는 3 + 2, 4개는 2 + 2, 6개는 3 + 3.
   줄 높이도 1fr 로 같게(설명이 두 줄인 카드가 있어도 모든 카드 높이가 같다) */
.kpis:not(.q),.kpis.k4:not(.q),.kpis.k6:not(.q){{grid-template-columns:repeat(6,minmax(0,110px));grid-auto-rows:1fr;justify-content:center}}   /* 카드 폭 = 110 × 2 + 칸 사이 26 = 246px */
.kpis:not(.q) .kpi{{grid-column:span 2;min-height:170px}}
.kpis:not(.q):not(.k4):not(.k6) .kpi:nth-child(4){{grid-column:2 / span 2}}
.kpis.k4:not(.q) .kpi:nth-child(odd){{grid-column:2 / span 2}}
/* 한 줄 4장(.row1) — ③ 국산화 완료 부품. 카드 폭을 246 → 210px 로 줄여 4장을 한 줄에 놓고,
   폭이 준 만큼 높이도 170 → 150px 로 줄여 비율을 맞춘다(줄 높이 1fr 라 4장 높이는 같다) */
/* ① 부품 현황 KPI(.parts-kpi-row — 종합 현황표 · 수출입 현황 핵심 지표)만 — 넓은 화면은 1줄 4칸, 860px 이하는 2 × 2.
   배치(격자 칸 · grid-column)만 바꾸고 카드 모양 · 글씨는 위 규칙 그대로. 다른 페이지 4장(.kpis.k4)은 2 + 2 가운데 그대로 */
@media (max-width:860px){{
}}
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
    # 오른쪽 위(훈수안이조 배지 · 로그인 · 공지사항 · 데이터 정보)는 09-30 비움 — 데이터 출처는 바닥글 · 배경과 자료에
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
