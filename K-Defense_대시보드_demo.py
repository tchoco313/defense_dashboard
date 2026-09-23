"""K-Defense 대시보드 — 디자인 데모(단독 실행본).

실행:  바탕화면의 `K-Defense_데모_실행.bat` 더블클릭(권장).
       직접 칠 때는 라이트 테마 플래그를 같이 준다 — 이 폴더에는 `.streamlit/config.toml` 이 없어서
       플래그가 없으면 표·위젯이 OS 다크모드를 따라간다:
         streamlit run "K-Defense_대시보드_데모.py" --theme.base light

이 파일 하나만 있으면 돌아간다. DB·`.env`·프로젝트 폴더가 전혀 필요 없다(다른 PC로 복사해도 같다).
필요한 것은 streamlit·pandas·plotly 뿐이고, 지구본의 세계지도 데이터만 인터넷(CDN)에서 받는다
(못 받으면 경위선만 그리고 화면에 알린다).

★ 화면의 모든 숫자는 **화면 배치·색·움직임을 보여 주기 위한 샘플**이다. 실제 DB 값이 아니며,
  어떤 보고·발표 자료에도 그대로 쓰면 안 된다. 실제 값은 운영 앱(app/main.py)이 AWS RDS 에서 읽는다.

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

st.set_page_config(page_title="K-Defense 대시보드 — 디자인 데모", page_icon="🛰️", layout="wide",
                   initial_sidebar_state="expanded")

# ════════════════════════════════════════════════════════════════════════════
# 1. 색 토큰 · CSS
# ════════════════════════════════════════════════════════════════════════════
BG, PANEL, PANEL2, LINE = "#eef3fb", "#ffffff", "#eef2f9", "#dde5f2"
TEXT, MUTED, ACCENT = "#16233f", "#6b7a99", "#2b6ef6"
NAVY, NAVY2 = "#0d2a5c", "#071c40"
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
:root{{
  --bg:{BG}; --panel:{PANEL}; --panel2:{PANEL2}; --line:{LINE};
  --text:{TEXT}; --muted:{MUTED}; --accent:{ACCENT}; --navy:{NAVY}; --navy2:{NAVY2};
  --up:{UP}; --down:{DOWN};
  --shadow:0 1px 2px rgba(19,42,84,.06), 0 6px 18px rgba(19,42,84,.06);
  --shadow-h:0 2px 4px rgba(19,42,84,.08), 0 14px 32px rgba(19,42,84,.12);
}}

html, body, [class*="st-"]{{font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif}}
/* 위 규칙이 아이콘 span 까지 덮으면 아이콘 이름(keyboard_double_arrow_left 등)이 글씨로 찍힌다 — 아이콘 글꼴 복원 */
[data-testid="stIconMaterial"]{{font-family:'Material Symbols Rounded'!important}}
/* 헤더를 통째로 숨기면 그 안의 '사이드바 열기' 버튼까지 사라진다 — 헤더는 투명하게 두고 메뉴·툴바만 숨긴다 */
[data-testid="stHeader"]{{background:transparent;height:0;pointer-events:none}}
[data-testid="stToolbar"] > *:not(:has([data-testid="stExpandSidebarButton"])),
[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="stMainMenu"],
[data-testid="stToolbarActions"],[data-testid="stAppDeployButton"]{{display:none!important}}
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
.st-key-minirail{{position:fixed;left:0;top:0;bottom:0;width:60px;z-index:999980;   /* 헤더(999990, » 버튼이 들어 있음)보다 아래 */
flex-direction:column;align-items:center;
  justify-content:center;gap:12px;padding:72px 0;overflow:visible;
  background:linear-gradient(175deg,var(--navy) 0%,var(--navy2) 100%);box-shadow:2px 0 14px rgba(7,28,64,.18)}}
.st-key-minirail > div{{width:auto!important;overflow:visible}}
/* 평소엔 이모티콘만 보이는 40px 칸 — 커서를 올리면 오른쪽으로 펼쳐지며 이모티콘+글씨가 커진다 */
.st-key-minirail [data-testid="stPageLink"] a,
.mr-on{{display:flex;align-items:center;box-sizing:border-box;width:max-content;height:40px;max-width:40px;padding:0 10px;margin:0;
  overflow:hidden;white-space:nowrap;border-radius:10px;background:transparent;transform-origin:left center;
  transition:max-width .22s ease,transform .18s ease,background .16s,box-shadow .16s}}
.st-key-minirail [data-testid="stPageLink"] a p,
.mr-on{{font-family:{SIDE_STACK};font-size:16px;font-weight:700;letter-spacing:-.2px;color:#fff;white-space:nowrap}}
.mr-on{{background:linear-gradient(95deg,#2b6ef6,#3fa9f5);box-shadow:0 4px 14px rgba(43,110,246,.42);
  height:38px;max-width:38px;padding-left:9px}}   /* 지금 페이지 파란 칸 — 다른 칸(40px)보다 2px 작게.
     칸이 좁아져 가운데로 1px 들어온 만큼 왼쪽 여백을 1px 줄여, 누르기 전후로 이모티콘 자리가 그대로이게 한다 */
.st-key-minirail [data-testid="stPageLink"] a:hover,
.mr-on:hover{{max-width:240px;padding-right:16px;transform:scale(1.12);position:relative;z-index:2;
  background:linear-gradient(95deg,#2b6ef6,#3fa9f5);box-shadow:0 8px 22px rgba(13,42,92,.38)}}
.st-key-sidebrand{{padding:14px 20px 18px;   /* 위쪽은 닫기 버튼(«)이 놓이는 사이드바 헤더(60px) 바로 아래 */
border-bottom:1px solid rgba(255,255,255,.08)}}
.sb-brand{{display:flex;align-items:center;gap:11px}}
.sb-mark{{width:38px;height:38px;border-radius:11px;flex:0 0 38px;display:grid;place-items:center;font-size:19px;
  background:linear-gradient(140deg,#3b82f6,#22d3ee);box-shadow:0 4px 14px rgba(34,211,238,.32)}}
.sb-brand b{{display:block;font-size:19.5px;font-weight:800;letter-spacing:-.3px;color:#fff;line-height:1.2}}
.sb-brand small{{display:block;font-size:11.5px;color:#93b0dd;line-height:1.55;margin-top:4px}}
.st-key-sidenav{{padding:14px 12px 0}}
.st-key-sidenav [data-testid="stVerticalBlock"]{{gap:3px}}
.st-key-sidenav [data-testid="stPageLink"] a{{padding:10px 14px;border-radius:10px;background:transparent;transition:background .16s,transform .16s}}
.st-key-sidenav [data-testid="stPageLink"] a:hover{{background:rgba(255,255,255,.08);transform:translateX(2px)}}
.st-key-sidenav [data-testid="stPageLink"] a p{{font-size:14.5px;font-weight:600;color:#b9cdea;white-space:nowrap}}
.nav-on{{display:flex;align-items:center;padding:10px 14px;margin:0;font-size:14.5px;font-weight:700;color:#fff;
  border-radius:10px;background:linear-gradient(95deg,#2b6ef6,#3fa9f5);box-shadow:0 4px 14px rgba(43,110,246,.42)}}
.st-key-sidefoot{{padding:26px 20px 20px;margin-top:8px}}
.sb-tag{{font-size:11.5px;font-weight:800;letter-spacing:2.2px;line-height:1.85;color:#5e8bd0}}
.sb-note{{margin-top:16px;font-size:12.5px;color:#9fb8de;line-height:1.6}}
.sb-ver{{margin-top:18px;padding-top:14px;border-top:1px solid rgba(255,255,255,.08);font-size:10.5px;color:#587298}}

/* ── 히어로 ───────────────────────────────────────────────────────────── */
.st-key-hero{{margin:0 -34px 8px;padding:0}}
.hero{{position:relative;overflow:hidden;min-height:112px;padding:24px 300px 26px 34px;
  background:linear-gradient(105deg,#e8f1ff 0%,#dbeafe 42%,#cfe4fb 70%,#bfdcf7 100%)}}
.hero::after{{content:"";position:absolute;right:-60px;top:-40px;width:420px;height:230px;border-radius:50%;
  background:radial-gradient(circle at 40% 40%,rgba(255,255,255,.75),rgba(255,255,255,0) 68%)}}
.hero h1{{margin:0;font-size:27px;font-weight:800;letter-spacing:-.6px;color:#0f2c5e;line-height:1.25}}
.hero p{{margin:7px 0 0;font-size:13px;color:#3d5b8c;line-height:1.55}}
.hero .slogan{{position:absolute;right:34px;top:24px;width:250px;text-align:right;z-index:1}}
.hero .slogan b{{display:block;font-size:16px;font-weight:800;color:#1c4ea3;letter-spacing:-.4px;line-height:1.4;font-style:italic}}
.hero .slogan small{{display:block;margin-top:7px;font-size:11px;color:#5a7cb0;line-height:1.5}}

/* ── 샘플 데이터 경고 띠 ──────────────────────────────────────────────── */
.demo-bar{{display:flex;align-items:center;gap:10px;margin:0 0 14px;padding:10px 16px;border-radius:10px;
  background:#fff7e6;border:1px solid #fcd9a0;border-left:4px solid #f59e0b}}
.demo-bar b{{font-size:12.5px;font-weight:800;color:#92400e}}
.demo-bar span{{font-size:11.5px;color:#a16207;line-height:1.5}}

/* ── 구역 ─────────────────────────────────────────────────────────────── */
div[class*="st-key-zone_"]{{position:relative;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.55);
  padding:32px 16px 18px;margin:14px 0 18px}}
div[class*="st-key-zone_"]::before{{position:absolute;top:-12px;left:18px;z-index:1;
  background:linear-gradient(95deg,#2b6ef6,#3fa9f5);color:#fff;font-size:12px;font-weight:700;letter-spacing:-.2px;
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
.kpi .l{{font-size:12px;font-weight:600;color:#5a6b8c;line-height:1.35}}
.kpi .v{{font-size:29px;font-weight:800;margin-top:9px;letter-spacing:-1px;color:#12234a;line-height:1.1}}
.kpi .v small{{font-size:13px;color:var(--muted);font-weight:600;margin-left:4px;letter-spacing:0}}
.kpi .s{{font-size:11px;color:var(--muted);margin-top:6px;line-height:1.5}}
.kpi .s .up{{color:var(--up);font-weight:700}} .kpi .s .dn{{color:var(--down);font-weight:700}}
.ex{{display:inline-block;font-size:10px;font-weight:700;color:#b45309;background:#fef3c7;border:1px solid #fde68a;
  border-radius:5px;padding:0 5px;margin-left:5px;vertical-align:middle}}

/* ── 글 ───────────────────────────────────────────────────────────────── */
.h{{font-size:14.5px;font-weight:700;margin-bottom:11px;display:flex;align-items:center;gap:8px;color:var(--text);letter-spacing:-.3px}}
.h::before{{content:"";width:4px;height:15px;border-radius:3px;background:linear-gradient(180deg,#2b6ef6,#3fa9f5);flex:0 0 4px}}
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

/* 입찰 공고 ↔ 결과 매칭 깔때기(DATA INFO) — 층마다 사다리꼴 하나 */
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
.spark{display:block;margin:0 auto;animation:revealX 1.3s cubic-bezier(.65,0,.35,1) .2s both}   /* 왼쪽부터 그려지듯 드러난다 */
.sc tbody tr:nth-child(2) .spark{animation-delay:.3s} .sc tbody tr:nth-child(3) .spark{animation-delay:.4s}
.sc tbody tr:nth-child(4) .spark{animation-delay:.5s} .sc tbody tr:nth-child(5) .spark{animation-delay:.6s}
@keyframes revealX{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}

.kgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}   /* 좁으면 1열, 넓으면 2열 */
.kc{display:flex;gap:12px;align-items:center;padding:14px 12px;border:1px solid #dde5f2;border-radius:12px;background:#fff;
  animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both}
.kc:nth-child(2){animation-delay:.07s} .kc:nth-child(3){animation-delay:.14s} .kc:nth-child(4){animation-delay:.21s}
.kc .ic{width:44px;height:44px;flex:0 0 44px;border-radius:50%;display:grid;place-items:center;font-size:20px}
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
[data-testid="stTabs"] [data-testid="stTab"] p{font-size:12.5px;font-weight:700;color:#5b6f94}
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
.kpis.q{gap:10px;margin-bottom:6px}
.kpis.q .kpi .v{font-size:23px}
</style>""")


# ════════════════════════════════════════════════════════════════════════════
# 2. 공용 요소
# ════════════════════════════════════════════════════════════════════════════
def kpi(label: str, value: str, unit: str, sub: str, tag: str = "", icon: str = "📊") -> str:
    t = f'<span class="ex">{tag}</span>' if tag else ""
    return (f'<div class="card kpi"><div class="kt"><span class="ico">{icon}</span>'
            f'<div class="l">{label}{t}</div></div>'
            f'<div class="v">{value}<small>{unit}</small></div><div class="s">{sub}</div></div>')


def zone(key: str, tag: str):
    st.html(f'<style>.st-key-zone_{key}::before{{content:"{tag}"}}</style>')
    return st.container(key=f"zone_{key}")


def hero(title: str, subtitle: str) -> None:
    with st.container(key="hero"):
        st.html(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p>'
                '<div class="slogan"><b>강한 국방,<br>데이터로 이어집니다.</b>'
                '<small>대한민국의 오늘,<br>더 안전한 내일</small></div></div>')


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
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED),
                     automargin=True)             # 여백이 좁아도 눈금 숫자(10k 등)가 잘리지 않게
    if height:
        fig.update_layout(height=height)
    return fig


def rules_card(title: str, items: list[tuple[str, str]]) -> str:
    body = "".join(f'<div class="rule"><span class="ck">✓</span><div><b>{t}</b><span>{d}</span></div></div>'
                   for t, d in items)
    return f'<div class="card"><div class="h">{title}</div>{body}</div>'


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
    return (f'<div class="card"><div class="h">부품별 공급망 현황 <span class="sub">품목군 {len(rows)}개 · '
            f'공급 집중 = HHI 4,000 이상 매우 높음 · 2,500 이상 높음</span></div>'
            f'<table class="sc"><thead>{head}</thead><tbody>{body}</tbody></table>'
            f'<div class="caption">추이·변화율은 최근 12개월과 그 전 12개월의 월별 수입액 비교(샘플) · '
            f'국산화율은 이 대시보드가 다루지 않습니다.</div></div>')


def core_kpis() -> str:
    hi = sum(1 for r in ITEMS if r[4] >= 2500)
    avg = sum(r[4] for r in ITEMS) / len(ITEMS)
    cards = [("🧩", "#e8f0ff", "비교 품목군", f"{len(ITEMS)}", "개", "현황표 품목군(전체 24개 중)", ""),
             ("⚠️", "#ffe9ea", "고집중 품목군", f"{hi}", "개", "HHI 2,500 이상", "color:#e5484d"),
             ("📐", "#e4fbf6", "평균 집중도", f"{avg:,.0f}", "HHI", f"{len(ITEMS)}개 품목군 단순 평균", ""),
             ("🌐", "#eef2ff", "공급 국가", f"{len(COUNTRIES) + len(MAP_OTHERS)}", "개국", "지도에 표시된 공급국", "")]
    body = "".join(f'<div class="kc"><span class="ic" style="background:{bg}">{ic}</span><div>'
                   f'<div class="l">{l}</div><div class="v" style="{vs}">{v}<small>{u}</small></div>'
                   f'<div class="s">{s}</div></div></div>' for ic, bg, l, v, u, s, vs in cards)
    return (f'<div class="card"><div class="h">핵심 지표 <span class="sub" style="margin-left:auto">기준: 2016~2025 합산</span></div>'
            f'<div class="kgrid">{body}</div></div>')


def share_card(f: dict) -> str:
    sh = f["shares"]
    rest = sum(s for _, s in sh[5:])
    cmap = {c[0]: c[4] for c in COUNTRIES}
    rows = [(n, s, cmap.get(n, "#94a7c8")) for n, s in sh[:5]] + ([("기타", rest, ETC)] if rest > 0.05 else [])
    body = "".join(f'<div class="row" title="{n} {s:.1f}%"><div class="nm">{n}</div><div class="track">'
                   f'<div class="fill" style="width:{s:.1f}%;background:{c}"></div><div class="ref"></div></div>'
                   f'<div class="pct">{s:.1f}%</div></div>' for n, s, c in rows)
    return (f'<div class="card"><div class="h">공급 국가 비중 <span class="sub">{f["name"]} · HS {f["hs"]} · '
            f'점선 = 50%</span></div><div class="bars big">{body}</div>'
            f'<div class="caption">수입국 {f["n"]}개 중 상위 5개국 · 샘플</div></div>')


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
  #ctrl button.on{background:linear-gradient(95deg,#2b6ef6,#3fa9f5);color:#fff;border-color:transparent;box-shadow:0 3px 10px rgba(43,110,246,.35)}
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
const PTS = __DATA__, KOREA = __KOREA__, UNIT = "__UNIT__";
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
  const inter=d3.geoInterpolate([p.lon,p.lat],KOREA);
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
      const inter=d3.geoInterpolate([p.lon,p.lat],KOREA);
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


def supply_globe(points: list[dict], height: int = 430, unit: str = "백만 USD") -> None:
    html = (_GLOBE.replace("__DATA__", json.dumps(points, ensure_ascii=False))
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
  .mark{width:46px;height:46px;border-radius:14px;display:grid;place-items:center;font-size:23px;
    background:linear-gradient(140deg,#3b82f6,#22d3ee);box-shadow:0 10px 30px rgba(34,211,238,.35);
    animation:pop .45s cubic-bezier(.18,.89,.32,1.3) both}
  .ttl{margin-top:12px;font-size:26px;font-weight:800;letter-spacing:-.7px;color:#0f2c5e;
    animation:up .45s ease .06s both}
  .sub{margin-top:6px;font-size:13px;font-weight:600;color:#4a6da8;letter-spacing:-.2px;
    animation:up .45s ease .10s both}
  canvas{display:block;margin-top:6px;animation:fadein .55s ease .14s both}
  .bar{width:210px;height:3px;border-radius:3px;background:#cfe0f7;overflow:hidden;margin-top:10px;
    animation:up .45s ease .17s both}
  .bar i{display:block;height:100%;border-radius:3px;background:linear-gradient(90deg,#2b6ef6,#3fa9f5);
    width:0;animation:fill __SEC__s linear .1s forwards}
  .msg{margin-top:9px;font-size:11.5px;font-weight:600;color:#6d89b8;letter-spacing:.3px;
    animation:up .45s ease .20s both}
  @keyframes pop{from{opacity:0;transform:scale(.6)}to{opacity:1;transform:none}}
  @keyframes up{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:none}}
  @keyframes fadein{from{opacity:0}to{opacity:1}}
  @keyframes fill{to{width:100%}}
</style></head><body>
<div id="stage">
  <div class="mark">🛰️</div>
  <div class="ttl">K-Defense</div>
  <div class="sub">방산 전자부품 수입 집중도 · 국산화 현황 대시보드</div>
  <canvas id="c" width="520" height="520"></canvas>
  <div class="bar"><i></i></div>
  <div class="msg">대시보드를 준비하는 중…</div>
</div>
<script>
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const DPR = Math.min(window.devicePixelRatio || 1, 2), S = 520;
cv.width = S * DPR; cv.height = S * DPR; cv.style.width = S + 'px'; cv.style.height = S + 'px';
ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

const proj = d3.geoOrthographic().clipAngle(90).precision(0.4).scale(S * 0.46).translate([S / 2, S / 2]);
const path = d3.geoPath(proj, ctx), grat = d3.geoGraticule10();
let world = null;

function draw() {
  ctx.clearRect(0, 0, S, S);
  // 바다 — 왼쪽 위에서 빛이 드는 구
  ctx.beginPath(); path({type: 'Sphere'});
  const g = ctx.createRadialGradient(S * .35, S * .32, S * .05, S / 2, S / 2, S * .46);
  g.addColorStop(0, '#f2f9ff'); g.addColorStop(.5, '#d8eafd'); g.addColorStop(1, '#a9caee');
  ctx.fillStyle = g; ctx.fill();
  ctx.save(); ctx.shadowColor = 'rgba(43,110,246,.30)'; ctx.shadowBlur = 38; ctx.fill(); ctx.restore();
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
INTRO_SEC = 1.0          # 지구본이 머무는 시간(초). 이 뒤 0.4초 동안 사라져 전체 약 1.5초


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
def globe_loading(text: str = "조회 중", height: int = 340):
    """조회·집계가 끝날 때까지 작은 지구본을 돌린다. `with globe_loading("…"):` 로 쓰고,
    블록을 벗어나면(오류가 나도) 자리를 비운다. st.spinner 를 대신한다."""
    slot = st.empty()
    with slot.container():
        components.html(_MINI.replace("__H__", str(height - 10)).replace("__LABEL__", escape(text)),
                        height=height, scrolling=False)
    try:
        yield
    finally:
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
                height: int = 430) -> None:
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
            .replace("__HOVER__", _hover_js(rows, 170, 170, "shown", value_unit)))
    components.html(html, height=height, scrolling=False)


_DONUT_TPL = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  *{box-sizing:border-box}
  body{margin:0;background:transparent;overflow:hidden;user-select:none;
       font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;color:#16233f}
  #stage{width:100%;height:__H__px;display:flex;flex-direction:column;align-items:center;justify-content:center}
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
  <svg width="340" height="340" viewBox="0 0 340 340">
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
const PAL = {imp: {c: '#2b6ef6', t: '#1c4ec4', bins: ['#1543c2', '#2f6ff0', '#6b9cf5', '#a9c7fa', '#d8e6fd']},
             exp: {c: '#0fa595', t: '#0b7f78', bins: ['#0b7f78', '#14a89c', '#46c7b9', '#93e1d5', '#d3f4ee']}};
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
    .attr('fill', f => { const s = S[byId[f.id]]; return s ? P.bins[bin(s.p)] : '#eef3fa'; })
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
  .lgd.off{opacity:.42}
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
function legend(m) {
  return '<div class="lgd ' + (m === mode ? 'on' : 'off') + '" style="--c:' + PAL[m].c + '"><b>' + KOR[m] + ' 금액<br>(천USD)</b>'
    + TXT.map((t, i) => '<div><i style="background:' + PAL[m].bins[i] + '"></i>' + t + '</div>').join('') + '</div>';
}
function paint() {
  const P = PAL[mode], k = IDX[mode];
  wrap.style.setProperty('--c', P.c);
  gl.selectAll('path').attr('fill', f => { const r = R[f.properties.code]; return r ? P.bins[bin(r[k])] : '#eef3fa'; });
  gt.selectAll('text').attr('class', 'rl lt');      // 짙은 칸에서도 흰 테두리 글자로 읽힌다
  const rows = Object.values(R).sort((a, b) => b[k] - a[k]).slice(0, 5), mx = rows[0][k] || 1;
  document.getElementById('side').innerHTML = legend('imp') + legend('exp')
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
    """시·도별 수입·수출 분포. 색 = 금액 구간(천 USD), 오른쪽에 두 범례(고른 쪽만 진하게)와 상위 5개 시·도."""
    html = (_REGION_MAP.replace("__DATA__", json.dumps(REGIONS, ensure_ascii=False))
            .replace("__H__", str(height - 10)))
    components.html(html, height=height, scrolling=False)


# ════════════════════════════════════════════════════════════════════════════
# 4. 샘플 데이터 — 전부 가짜다(실제 DB 값 아님)
# ════════════════════════════════════════════════════════════════════════════
YEARS = list(range(2016, 2027))

COUNTRIES = [
    # 이름, 위도, 경도, 수입액(백만 USD), 색, 1위 품목군
    ("미국", 38.0, -97.0, 8942, SERIES[0], "항공기 부분품, 레이더 기기, 프로세서 IC"),
    ("독일", 51.0, 10.4, 3120, SERIES[1], "광학기기, 컴퍼스"),
    ("일본", 36.2, 138.2, 2815, SERIES[2], "다이오드, 트랜지스터 <1W"),
    ("중국", 35.8, 104.1, 2420, SERIES[3], "안테나, 송수신기"),
    ("프랑스", 46.2, 2.2, 1906, SERIES[4], "항행 부분품"),
    ("대만", 23.6, 121.0, 1540, SERIES[5], "기타 IC, 증폭기 IC"),
    ("싱가포르", 1.35, 103.8, 980, "#34d399", "무선항행"),
]

GLOBE_PTS = [{"name": n, "lat": la, "lon": lo, "value": v, "color": c, "note": "1위 품목군: " + note}
             for n, la, lo, v, c, note in COUNTRIES]

# 품목군별 1위 공급국 점유율
ITEMS = [
    ("901420", "항공 항행기기", "미국", 71.4, 5820, 8),
    ("880730", "항공기 부분품", "미국", 64.2, 4910, 11),
    ("852610", "레이더 기기", "미국", 58.9, 4120, 7),
    ("854231", "프로세서 IC", "대만", 52.3, 3480, 12),
    ("841191", "터보제트 부분품", "미국", 49.7, 3210, 9),
    ("901380", "광학기기", "독일", 44.1, 2860, 14),
    ("852910", "안테나", "중국", 41.8, 2610, 16),
    ("854110", "다이오드", "일본", 38.5, 2340, 18),
    ("852560", "송수신기", "중국", 35.2, 2080, 15),
    ("901410", "컴퍼스", "독일", 33.6, 1950, 10),
    ("854239", "기타 IC", "대만", 31.4, 1820, 19),
    ("852691", "무선항행", "싱가포르", 28.7, 1640, 13),
]

IMPORT_TREND = pd.DataFrame({
    "연도": YEARS,
    "전체 수입": [7050, 8420, 9610, 11500, 13020, 14580, 16240, 18390, 20610, 21920, 20840],
    "방산 연관 수입": [2642, 3138, 3895, 4980, 5421, 6248, 7512, 8942, 10195, 11420, 9830],
})

FSG_DIST = [("FSG 58 (전자장비)", 892, SERIES[0]), ("FSG 59 (전자부품)", 743, SERIES[1]),
            ("FSG 60 (전기장비)", 485, SERIES[2]), ("기타", 280, ETC)]

LOCAL_STATUS = [("국산화 완료", 1206, SERIES[0]), ("국산화 추진", 200, SERIES[1]),
                ("진행중", 419, SERIES[2]), ("수입품목", 892, ETC)]

EQUIPMENT = [("K9 자주포", 842, SERIES[0]), ("KF-21 전투기", 621, SERIES[1]), ("이지스 구축함", 518, SERIES[2]),
             ("천무 다연장로켓", 422, SERIES[3]), ("K2 전차", 361, SERIES[4])]

BUDGET = pd.DataFrame({
    "연도": YEARS,
    "국외조달 예산(억 원)": [12400, 13100, 14800, 16200, 17900, 19400, 21200, 23800, 26100, 28400, 30200],
    "전체 방위력개선비 대비(%)": [18.2, 18.9, 19.4, 20.1, 20.8, 21.2, 21.9, 22.4, 23.1, 23.6, 24.0],
})

PLAN_BY_FSC = [("5820 통신장비", 1240, SERIES[0]), ("5935 전자부품", 892, SERIES[1]), ("5962 변환기", 621, SERIES[2]),
               ("5999 기타전자", 418, SERIES[3]), ("5865 안테나", 352, SERIES[4])]

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

# 입찰 공고 ↔ 결과 매칭(DATA INFO 깔때기) — 단위: 행
BID_MATCH = [("입찰 공고 행", 10842), ("입찰 결과 행", 7405), ("공고키 존재 결과행", 7072), ("공통 고유키", 6872)]

# 국외조달 절차(정책·산업 배경) — 단계, 아이콘, 설명, 건수, 원 색. 건수는 실측(clean 테이블 행 수):
# 계획 clean_dapa_overseas_plan 3,023 · 입찰 clean_dapa_overseas_bid_result 2,494 · 계약 clean_dapa_overseas_contract 6,333
PROC_STEPS = [
    ("계획", "📋", "조달 필요 확인<br>구매계획 수립", 3023, "linear-gradient(140deg,#1d4fb8,#2b6ef6)"),
    ("입찰", "⚖️", "국외 공고 및 입찰<br>업체 평가 · 선정", 2494, "linear-gradient(140deg,#2b6ef6,#3fa9f5)"),
    ("계약", "🤝", "계약 체결<br>납품 및 이행 관리", 6333, "linear-gradient(140deg,#0f9f78,#34c98f)"),
]

# 부품별 공급망 현황(홈 표) · 품목군별 공급 집중도(수입 집중도 탭) — 1위 공급국이 서로 다른 5개 품목군
FOCUS_HS = ["901420", "854231", "901380", "852910", "854110"]
_FOCUS_TREND = {"901420": 0.22, "854231": 0.15, "901380": -0.08, "852910": 0.10, "854110": -0.05}  # 24개월 기울기(샘플)


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

items_df = pd.DataFrame(ITEMS, columns=["HS6", "품목군", "1위 공급국", "1위 점유율(%)", "HHI", "수입국 수"])


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


def page_home() -> None:
    with zone("kpi", "한눈에 보는 KPI"):
        st.html('<div class="kpis">'
                + kpi("분석 대상 품목군", "24", "개", "공식 분류·통제표 + 팀 규칙 R1~R4 · 3개는 R4 잠정", icon="📦")
                + kpi("2016~2025 수입액", "33,894", "백만 USD", '<span class="up">▲ +1,120</span> 전년 대비 · 민수 포함', icon="💵")
                + kpi("특정국 50% 이상 품목군", "5", "개", "1위 공급국 점유율 기준 · 2016~2025", icon="⚠️")
                + kpi("전자 군급 국외 조달계획", "1,206", "건", "적용장비 337종 · FSG 58·59·60", "잠정", "🌐")
                + kpi("국산화개발 전자 부품", "2,380", "개", "전자 군급 · 국산화율 아님", "", "🛠️")
                + "</div>")

    with zone("chain", "부품별 공급망 현황"):
        c1, c2 = st.columns([2.3, 1], gap="medium")
        c1.html(supply_table(FOCUS))
        c2.html(core_kpis())

    with zone("where", "어디서 들어오나"):
        c_map, c_bar = st.columns([1.35, 1], gap="medium")
        with c_map.container(border=True, key="card_map"):
            st.html('<style>.st-key-globe_legend{margin-top:-18px}</style><div class="h">국가별 수입 규모 '
                    '<span class="sub">지구본 · 지도 전환 · 화살표 = 들어오는 방향 · 원에 올리면 상세</span></div>')
            supply_globe(GLOBE_PTS, height=430, unit="백만 USD")
            # 범례 — 지구본 칸 안이 아니라 그 밑에 둔다(지구본을 가리지 않게). 칸 아래 빈 틈(iframe 여백 10 + 간격 16)을 당겨 8px 만 띄운다
            with st.container(key="globe_legend"):
                st.html('<div style="display:inline-flex;align-items:center;gap:13px;font-size:10.5px;color:#6b7a99;'
                        'background:#fff;border:1px solid #dde5f2;border-radius:9px;padding:5px 11px">'
                        '<span><i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#2b6ef6;'
                        'margin-right:5px;vertical-align:middle"></i>원 크기 = 수입액</span>'
                        '<span>화살표 = 대한민국으로 들어오는 방향</span><span>원 위에 올리면 상세</span></div>')
        rows = "".join(
            f'<div class="row" title="{n} {s:.1f}%"><div class="nm">{nm}<em>{hs}</em></div>'
            f'<div class="track"><div class="fill" style="width:{s:.1f}%;background:{dict((c[0], c[4]) for c in COUNTRIES).get(n, ETC)}"></div>'
            f'<div class="ref"></div></div><div class="pct">{s:.1f}%</div></div>'
            for hs, nm, n, s, _, _ in ITEMS)
        legend = "".join(f'<span><i style="background:{c[4]}"></i>{c[0]}</span>' for c in COUNTRIES)
        c_bar.html(f'<div class="card"><div class="h">품목군별 1위 공급국 점유율 '
                   f'<span class="sub">2016~2025 · 점선 = 50%</span></div>'
                   f'<div class="bars">{rows}</div><div class="legend" style="margin-top:10px">{legend}</div></div>')

    with zone("guide", "안내"):
        c2, c3 = st.columns(2, gap="small")
        c2.html('<div class="card"><div class="h">읽는 법</div><div class="note">'
                '· 「수입 집중도」 = 품목군 수입액 중 특정국 비중(점유율·HHI)<br>'
                '· 국가 전체 수입으로 <b>민수가 포함</b>됩니다<br>'
                '· 군수 몫은 관세 통계로 나뉘지 않습니다<br>'
                '· 조달계획 ≠ 계약, 국산화개발 부품 수 ≠ 국산화율</div></div>')
        c3.html('<div class="card"><div class="h">출처</div><div class="note">'
                '관세청 품목별 국가별 수출입실적<br>'
                '방위사업청 국외 조달계획 · 국산화개발품목 · 군급분류집<br>'
                '열린재정 예산 · KOSIS 방산 가동률 · 광공업생산지수<br>'
                '<span style="color:#8494ae">모든 수치에 기준일·산식 표시 · 상세는 ⑤ DATA INFO</span></div></div>')


def page_import() -> None:
    with globe_loading("수입 집계를 읽는 중"):
        time.sleep(DEMO_WAIT)
    st.html('<div class="lede"><div class="note">HS/HSK 기반 방산 연관 수입 구조 · 공급국 집중도 · 품목군 동향. '
            '군수 수요 비중이 아니라 <b>국가 전체 교역 규모</b>입니다.</div></div>')
    with zone("kpi2", "핵심 지표"):
        st.html('<div class="kpis k6">'
                + kpi("화이트리스트 HS6", "25", "개", '<span class="up">▲ +3</span> 전년 대비', icon="📋")
                + kpi("HSK 통제코드", "28", "개", '<span class="up">▲ +5</span> 전년 대비', icon="🔐")
                + kpi("민군겸용 후보", "680", "건", '<span class="up">▲ +37</span> 전년 대비', icon="🔀")
                + kpi("항공 후보", "419", "건", '<span class="up">▲ +24</span> 전년 대비', icon="✈️")
                + kpi("전자 후보", "145", "건", '<span class="up">▲ +12</span> 전년 대비', icon="⚙️")
                + kpi("분석 기간", "2016–2026", "", "총 11년", icon="🗓️")
                + "</div>")

    with zone("trend", "연도별 · 국가별"):
        c1, c2 = st.columns([1.3, 1], gap="medium")
        with c1.container(border=True, key="card_trend"):
            st.html('<div class="h">연도별 수입액 추이 <span class="sub">단위: 백만 USD</span></div>')
            fig = go.Figure()
            for name, color in (("전체 수입", SERIES[0]), ("방산 연관 수입", SERIES[1])):
                fig.add_trace(go.Scatter(x=IMPORT_TREND["연도"], y=IMPORT_TREND[name], name=name,
                                         mode="lines+markers", line=dict(color=color, width=2.5),
                                         marker=dict(size=7, color="#fff", line=dict(color=color, width=2))))
            fig.update_layout(legend=dict(orientation="h", y=1.12))
            st.plotly_chart(style_fig(fig, 430), width="stretch", theme=None)
        with c2.container(border=True, key="card_share"):
            st.html('<div class="h">공급국 비중 '
                    '<span class="sub">조각에 커서를 올려 보세요 · 2016~2025 합산 · 단위: 백만 USD</span></div>')
            hover_donut([(c[0], c[3], c[4]) for c in COUNTRIES],
                        f"{sum(c[3] for c in COUNTRIES):,}", "백만 USD", value_unit="백만 USD", height=440)

    with zone("conc", "공급국 집중도"):
        c1, c2 = st.columns([1, 1.25], gap="medium")
        c1.html(rank_card("주요 수입국 TOP 7", "괄호 안은 전체 대비 비중",
                          [(c[0], c[3], c[4]) for c in COUNTRIES], "백만 USD"))
        with c2.container(border=True, key="card_hhi"):
            st.html('<div class="h">품목군별 집중도(HHI) <span class="sub">2,500 이상 = 높은 집중</span></div>')
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

    with zone("focus", "품목군별 공급 집중도"):
        st.html('<div class="note" style="margin-bottom:4px">탭을 누르면 품목군이 바뀝니다 — 품목군별 공급 국가 비중입니다.</div>')
        for tab, f in zip(st.tabs([f["name"] for f in FOCUS]), FOCUS):
            with tab:
                st.html(share_card(f))

    with zone("mix", "지도 · 품목군 구성"):
        c1, c2 = st.columns([1.15, 1], gap="medium")
        with c1.container(border=True, key="card_choro"):
            st.html('<div class="h">국가별 수입 분포 '
                    '<span class="sub">색 = 합계 대비 비중 · 상위 6개국 라벨 · 2016~2025 합산 · 오른쪽 위에서 수출로 전환</span></div>')
            country_map(TRADE_IMP, TRADE_EXP, height=410)
        with c2.container(border=True, key="card_mekko"):
            st.html('<div class="h">공급국 × 품목군 구성비 '
                    '<span class="sub">마리메코 · 막대 폭 = 국가 수입액 · 기타 = 대만·싱가포르</span></div>')
            fig = style_fig(mekko(410))
            fig.update_layout(margin=dict(l=40, r=8, t=30, b=8))   # 위쪽 국가명 · 왼쪽 % 눈금 자리
            st.plotly_chart(fig, width="stretch", theme=None)


def page_parts() -> None:
    st.html('<div class="lede"><div class="note">전자 군급(FSG 58 통신·탐지 · 59 전기·전자 구성품 · 60 광섬유)을 기준으로, '
            '국외 조달계획과 국산화 개발 부품을 군급(FSC)별로 나란히 봅니다. '
            'HS 품목군과는 <b>연결하지 않습니다</b>(공식 대응표 없음).</div></div>')
    with zone("kpi3", "전자 군급 현황"):
        st.html('<div class="kpis">'
                + kpi("전자그룹 후보 합계", "2,717", "개", '<span class="up">▲ +126</span> 전월 대비', icon="📚")
                + kpi("KDSIS NSN", "33,894", "건", '<span class="up">▲ +1,120</span> 전월 대비', icon="🗄️")
                + kpi("국산화 + exact 매칭", "1,206", "개", '<span class="up">▲ +37</span> 전월 대비', icon="⚙️")
                + kpi("B2 후보 품목", "337", "개", '<span class="up">▲ +12</span> 전월 대비', icon="📁")
                + kpi("B2 최종 품목", "2,380", "개", '<span class="up">▲ +84</span> 전월 대비', icon="✅")
                + "</div>")

    with zone("fsg", "군급 분포"):
        c1, c2 = st.columns(2, gap="medium")
        with c1.container(border=True, key="card_fsg"):
            st.html('<div class="h">FSG 58·59·60 분포 <span class="sub">단위: 품목 수</span></div>')
            st.plotly_chart(style_fig(hbar(FSG_DIST, 300, "개")), width="stretch", theme=None)
        with c2.container(border=True, key="card_fsc"):
            st.html('<div class="h">FSC 상위 품목군 <span class="sub">단위: 품목 수</span></div>')
            st.plotly_chart(style_fig(hbar(PLAN_BY_FSC, 300, "건")), width="stretch", theme=None)

    with zone("loc", "국산화 상태"):
        c1, c2 = st.columns([1.5, 1], gap="medium")
        with c1.container(border=True, key="card_loc"):
            st.html('<div class="h">전자 군급 부품 국산화 상태 '
                    '<span class="sub">조각에 커서를 올려 보세요 · 단위: 품목 수</span></div>')
            hover_donut(LOCAL_STATUS, f"{sum(v for _, v, _ in LOCAL_STATUS):,}", "전체 품목 수",
                        value_unit="개", height=430)
        c2.html(rules_card("읽는 법", [
            ("국산화율이 아닙니다", "국산화개발을 마친 부품 수이며 비율 지표가 아닙니다."),
            ("조각 크기 = 품목 수", "금액이 아니라 품목(부품) 개수 기준입니다."),
        ]))

    with zone("eq", "적용장비 · 군별"):
        c1, c2 = st.columns([1, 1.3], gap="medium")
        c1.html(rank_card("적용장비 TOP 품목", "국외 조달계획 기준", EQUIPMENT, "품목 수"))
        with c2.container(border=True, key="card_army"):
            st.html('<div class="h">연도별 군별 조달계획 <span class="sub">단위: 건</span></div>')
            fig = go.Figure()
            for i, army in enumerate(["육군", "해군", "공군", "해병대"]):
                fig.add_trace(go.Bar(x=ARMY_MIX["연도"], y=ARMY_MIX[army], name=army,
                                     marker=dict(color=SERIES[i], line=dict(color="#fff", width=1))))
            fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.14), height=330)
            st.plotly_chart(style_fig(fig), width="stretch", theme=None)


def pct_rows(rows: list[tuple[str, float, str]]) -> str:
    """이름 · 막대 · % 한 줄씩(점선 = 50%). 공급 국가 비중 카드와 같은 모양."""
    return '<div class="bars big">' + "".join(
        f'<div class="row" title="{n} {v:.1f}%"><div class="nm">{n}</div><div class="track">'
        f'<div class="fill" style="width:{v:.1f}%;background:{c}"></div><div class="ref"></div></div>'
        f'<div class="pct">{v:.1f}%</div></div>' for n, v, c in rows) + "</div>"


def page_domestic() -> None:
    real_bar("이 페이지의 숫자는 샘플이 아니라 defense_dashboard(AWS RDS) clean 테이블을 실측해 팀 문서"
             "(null-profile 09-19 · evidence-reliability 09-17 · class5 규칙 초안 09-17 · csv-capability-map)에 기록한 값입니다. "
             "운영 앱에는 이 자료 화면이 없어 DB 화면으로 다시 대조하지는 못했습니다.")
    st.html('<div class="lede"><div class="note">방위사업청 <b>국내조달</b> 계약정보(clean_dapa_contract) · 입찰공고(clean_dapa_bid_notice) · '
            '입찰결과(clean_dapa_bid_result)를 <b>건수</b>로만 봅니다. 금액은 쓰지 않습니다 — 공고 예산 ≠ 낙찰금액 ≠ 계약금액. '
            'HS 품목군·관세청 수입액과는 연결하지 않습니다.</div></div>')
    with zone("dkpi", "국내 조달 핵심 지표"):
        st.html('<div class="kpis">'
                + kpi("국내 계약", "37,602", "건", "계약 단위(최종 차수) · 정제 행 43,105", icon="📑")
                + kpi("수의계약 비중", "70.2", "%", "30,255 / 43,111행 · 국외조달은 20.1%", icon="🤝")
                + kpi("입찰공고", "10,842", "건", "2024 1,274 · 2025 9,566", icon="📢")
                + kpi("경쟁입찰 유찰률", "24.2", "%", "유찰 1,741 / 공고 키 7,201", icon="⛔")
                + kpi("낙찰업체", "3,211", "개", "사업자번호 기준 · 계약정보 연결 96.4%", icon="🏢")
                + "</div>")

    with zone("dmethod", "계약 방법"):
        c1, c2 = st.columns([1.4, 1], gap="medium")
        with c1.container(border=True, key="card_dmethod"):
            st.html('<div class="h">계약 체결 방법별 건수 <span class="sub">clean_dapa_contract · 단위: 행</span></div>')
            st.plotly_chart(style_fig(hbar(DOM_METHOD, 300, "행")), width="stretch", theme=None)
        c2.html('<div class="card"><div class="h">수의계약 비중 — 국내 vs 국외 <span class="sub">점선 = 50%</span></div>'
                + pct_rows([("국내조달", 70.2, SERIES[2]), ("국외조달", 20.1, SERIES[0])])
                + '<div class="caption">국내 30,255 / 43,111행 · 국외 1,276 / 6,333계약(clean_dapa_overseas_contract). '
                  '국내는 소액·소기업 사유가 대부분이라 비중 차이를 곧 진입 장벽으로 읽지 않습니다.</div></div>')

    with zone("dreason", "수의계약 사유"):
        c1, c2 = st.columns([1.4, 1], gap="medium")
        total_private = sum(v for _, v, _ in DOM_METHOD[:1])
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

    with zone("dbid", "입찰 결과"):
        c1, c2 = st.columns([1.2, 1], gap="medium")
        with c1.container(border=True, key="card_dbid"):
            st.html('<div class="h">국내 경쟁입찰 개찰 결과 <span class="sub">clean_dapa_bid_result · 조각에 커서를 올려 보세요</span></div>')
            hover_donut(BID_RESULT, f"{sum(v for _, v, _ in BID_RESULT):,}", "개찰 결과 행", value_unit="행", height=430)
        c2.html('<div class="card"><div class="h">공고 · 입찰 참고 지표 <span class="sub">서로 단위가 달라 한 줄로 비교하지 않습니다</span></div>'
                + pct_rows([("긴급 공고(국내)", 5677 / 10840 * 100, SERIES[3]), ("유찰(국내, 공고 키)", 1741 / 7201 * 100, DOWN)])
                + '<div class="caption" style="margin-top:10px">긴급 공고 5,677 / 10,840 · 유찰 1,741 / 7,201 공고 키.<br>'
                  '국외조달 입찰결과는 2025-01~09 부분연도(유찰 2,146 · 낙찰 348행, 달러 표시)라 연간 유찰률로 쓰지 않고 '
                  '국내와 나란히 두지 않습니다. 낙찰금액 ≠ 계약금액.</div></div>')


def page_table() -> None:
    st.html('<div class="lede"><div class="note">분석 대상 품목군을 한 표로 비교합니다. '
            '표는 열 머리를 눌러 정렬할 수 있고, 오른쪽 위 아이콘으로 검색·전체화면·CSV 내려받기가 됩니다.</div></div>')
    with zone("tbl", "품목군 현황표"):
        c_note, c_seg = st.columns([3, 2], vertical_alignment="center")
        c_note.html('<div class="note">기간 기준을 바꾸면 점유율·HHI가 같은 기준으로 다시 계산됩니다(데모에서는 표시만 바뀝니다)</div>')
        with c_seg:
            st.segmented_control("기간", ["2025 기준 연도", "최근 5년", "전체 2016~"], default="전체 2016~",
                                 key="tbl_period", label_visibility="collapsed", width="stretch")
        with globe_loading("품목군 집계를 다시 계산하는 중"):
            time.sleep(DEMO_WAIT)
        st.dataframe(
            items_df, width="stretch", hide_index=True, height=440,
            column_config={
                "1위 점유율(%)": st.column_config.ProgressColumn("1위 점유율(%)", min_value=0, max_value=100, format="%.1f%%"),
                "HHI": st.column_config.NumberColumn("HHI", format="%d"),
                "수입국 수": st.column_config.NumberColumn("수입국 수", format="%d개"),
            })
        st.download_button("CSV 내려받기", items_df.to_csv(index=False).encode("utf-8-sig"),
                           "품목군_현황표_샘플.csv", "text/csv")

    with zone("lead", "1위 공급국 분포"):
        c1, c2 = st.columns([1.5, 1], gap="medium")
        with c1.container(border=True, key="card_lead"):
            st.html('<div class="h">품목군을 어느 나라가 1위로 잡고 있나 '
                    '<span class="sub">조각에 커서를 올려 보세요 · 단위: 품목군 수</span></div>')
            cnt = items_df["1위 공급국"].value_counts()
            cmap = {c[0]: c[4] for c in COUNTRIES}
            hover_donut([(n, int(v), cmap.get(n, ETC)) for n, v in cnt.items()],
                        f"{len(items_df)}", "개 품목군", value_unit="개 품목군", height=430)
        c2.html(rules_card("읽는 법", [
            ("품목군 수이지 금액이 아닙니다", "1위로 잡은 품목군을 세어 만든 분포입니다."),
            ("1위라고 과반은 아닙니다", "점유율은 표의 「1위 점유율」 열에서 따로 봅니다."),
        ]))

    with zone("tree", "집중도 한눈에"):
        c1, c2 = st.columns(2, gap="medium")
        with c1.container(border=True, key="card_tree"):
            st.html('<div class="h">품목군 규모 · 1위 점유율 <span class="sub">칸 크기 = HHI</span></div>')
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

    with zone("basis", "품목군 선정 근거(실측)"):
        real_bar("위 표·차트의 12개 품목군은 샘플이지만, 이 구역은 실제 기준표 hs_whitelist.csv(HS6 24개)의 선정 근거와 "
                 "운영 앱(RDS)의 분석 대상 13개(2026-09-21 확정)를 그대로 옮겼습니다.")
        c1, c2 = st.columns([1.7, 1], gap="medium")
        rows = sorted(HS_BASIS, key=lambda r: r[0] not in TARGET_HS)       # 분석 대상 13개를 위로
        with c1:
            st.html(basis_matrix(rows[:BASIS_SHOW], title=f"HS6 선정 근거 — 분석 대상 {BASIS_SHOW}개 먼저"))
            with st.expander(f"나머지 {len(rows) - BASIS_SHOW}개 펼쳐 보기 (분석 대상 {len(TARGET_HS) - BASIS_SHOW}개 · "
                             f"배경 {len(rows) - len(TARGET_HS)}개)"):
                st.html(basis_matrix(rows[BASIS_SHOW:], start=BASIS_SHOW, card=False) + basis_legend())
        c2.html(basis_summary())


BASIS_SHOW = 6                # 선정 근거 표에서 처음부터 보이는 줄 수 — 나머지는 펼쳐 보기


def basis_matrix(rows: list[tuple[str, str, str, str]], start: int = 0, title: str = "", card: bool = True) -> str:
    """선정 근거 행렬. start = 전체 목록에서 이 표의 첫 줄 위치(분석 대상/배경 경계선과 등장 순서용)."""
    tag_color = {"HSK-군용": "#e5484d", "HSK-항공/항행": SERIES[0], "전략물자-DU": SERIES[2],
                 "B2-FSC": SERIES[1], "A6": SERIES[3], "팀판단": "#94a7c8"}
    rule = {"HSK-군용": "R1", "HSK-항공/항행": "R2", "전략물자-DU": "R3", "B2-FSC": "R4"}
    head = "".join(f'<th title="{d}">{t}{"<br><small>" + rule[t] + "</small>" if t in rule else ""}</th>' for t, d in BASIS_TAGS)
    body = ""
    for k, (hs, name, cat, ev) in enumerate(rows):
        tags = set(ev.split(";"))
        cells = "".join(f'<td>{f"<i style=background:{tag_color[t]};animation-delay:{k * .025:.2f}s></i>" if t in tags else ""}</td>'
                        for t, _ in BASIS_TAGS)
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


def page_background() -> None:
    st.html('<div class="lede"><div class="note">수입 의존 현황의 배경 — 정부 예산, 방위사업청 국외조달 계획, 국내 생산 기반. '
            '각 자료는 단위·기준이 달라 서로 합하거나 관세청 수입액과 <b>직접 비교하지 않습니다</b>.</div></div>')
    with zone("bkpi", "예산 · 조달"):
        st.html('<div class="kpis k4">'
                + kpi("2026 국외조달 예산", "30,200", "억 원", '<span class="up">▲ +6.3%</span> 전년 대비', icon="🏛️")
                + kpi("방위력개선비 대비", "24.0", "%", '<span class="up">▲ +0.4%p</span> 전년 대비', icon="📈")
                + kpi("국내 방산 가동률", "78.4", "%", '<span class="dn">▼ -1.2%p</span> 전년 대비', icon="🏭")
                + kpi("전자부품 생산지수", "112.6", "", "2020 = 100 · 잠정치 포함", "잠정", "⚡")
                + "</div>")

    with zone("bud", "예산 추이"):
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

    with zone("proc", "국외조달 절차 · 분야별 예산"):
        c1, c2 = st.columns([1, 1.35], gap="medium")
        steps = '<div class="ar">➜</div>'.join(
            f'<div class="st"><div class="ci" style="background:{bg}"><span>{ic}</span><b>{nm}</b></div>'
            f'<div class="ds">{ds}</div><div class="n">{n:,}<small>건</small></div></div>'
            for nm, ic, ds, n, bg in PROC_STEPS)
        c1.html('<div class="card"><div class="h">국외조달 프로세스 <span class="sub">단계별 건수(실측) · 단위: 건</span></div>'
                f'<div class="proc">{steps}</div>'
                '<div class="caption" style="margin-top:14px">계획 clean_dapa_overseas_plan(2017~2025) · '
                '입찰 clean_dapa_overseas_bid_result(2025-01~09 부분연도, 행) · 계약 clean_dapa_overseas_contract(2017~2025). '
                '기간·단위가 달라 앞 단계 대비 전환율로 읽지 않습니다 — 조달계획 ≠ 계약.</div></div>')
        with c2.container(border=True, key="card_heat"):
            st.html('<div class="h">분야별 국외조달 예산 '
                    '<span class="sub">색 = 분야 안에서의 상대 크기 · 올리면 억 원 · 연도 합계 = 연도별 국외조달 예산</span></div>')
            fig = style_fig(field_heatmap(330))
            fig.update_layout(margin=dict(l=70, r=8, t=10, b=30))   # 왼쪽 분야 이름 · 아래 연도 자리
            st.plotly_chart(fig, width="stretch", theme=None)

    with zone("facts", "운영 DB 실측 — 가동률 · 국산화 예산 · 국외조달 계획"):
        real_bar("이 구역은 샘플이 아닙니다 — 운영 앱(defense-trade.streamlit.app)이 AWS RDS 의 clean_kosis_utilization · "
                 "clean_openfiscal_program_budget · clean_dapa_overseas_plan 등에서 읽어 그린 값을 2026-09-21 에 옮겼습니다.")
        c1, c2 = st.columns(2, gap="medium")
        with c1.container(border=True, key="card_util"):
            st.html('<div class="h">방산 분야별 가동률 <span class="sub">clean_kosis_utilization · 통신전자 강조 · 점선 = 평균 · 단위: %</span></div>')
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
            st.html('<div class="caption">통신전자는 2016~2022년 70.8~75.2%에서 2023년 89.0%로 9개 분야 중 가장 크게 올랐습니다. '
                    '조사 기반 값이라 생산 능력·국산화 수준이 아니며, 수입 증감과 인과로 읽지 않습니다.</div>')
        with c2.container(border=True, key="card_rnd"):
            st.html('<div class="h">부품국산화 · 공급망 · 국방반도체 예산 <span class="sub">clean_openfiscal_program_budget · '
                    '단위: 억 원 · 흐린 막대 = 2027 정부안</span></div>')
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
            st.html('<div class="caption">부품국산화는 2021년 세부사업으로 편성된 뒤 2023년 1,845억이 가장 큽니다. '
                    '공급망(무기체계 공급망 관리)은 2025년 7.5억 → 2026년 52.5억, 국방반도체는 2027년 정부안에 처음 565억. '
                    '같은 기간 국방기술개발은 2.84조 원(2026) — 규모 차이가 커 이 그림에는 넣지 않았습니다. 관세청 수입액과 합산하지 않습니다.</div>')

        c1, c2 = st.columns([1.35, 1], gap="medium")
        with c1.container(border=True, key="card_ovplan"):
            total = sum(sum(v) for v in OV_PLAN_TYPE.values())
            st.html(f'<div class="h">국외조달 계획 — 집행유형별 건수 <span class="sub">clean_dapa_overseas_plan · '
                    f'2017~2025 합계 {total:,}건 · 단위: 건</span></div>')
            fig = go.Figure()
            for i, (name, ys) in enumerate(OV_PLAN_TYPE.items()):
                fig.add_trace(go.Bar(x=OV_PLAN_YEARS, y=ys, name=name,
                                     marker=dict(color=(SERIES + [ETC])[i], line=dict(color="#fff", width=1)),
                                     hovertemplate=name + " %{x}년 %{y}건<extra></extra>"))
            fig.update_xaxes(dtick=1)
            fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.16), bargap=.3)
            st.plotly_chart(style_fig(fig, 330), width="stretch", theme=None)
            st.html('<div class="caption">계획(원화 집행 예정액 기준)이며 계약·집행 실적이 아닙니다. 국가 정보가 없어 수입국과 연결하지 않습니다.</div>')
        with c2.container(border=True, key="card_defco"):
            st.html(f'<div class="h">분야별 방산업체 지정 수 <span class="sub">방위사업청 방산업체 지정현황 · '
                    f'분야 합 {sum(v for _, v in DEF_COMPANY)}개사</span></div>')
            rows = [(n, v, SERIES[1] if n == "통신전자" else "#9dbdf9") for n, v in DEF_COMPANY]
            st.plotly_chart(style_fig(hbar(rows, 330, "개사")), width="stretch", theme=None)
            st.html(f'<div class="caption">운영 앱 제목은 「총 84개사」인데 분야별 막대 합은 {sum(v for _, v in DEF_COMPANY)}개사입니다'
                    f'(차이 3개사 — 원인 미확인). 지정 기준 값이며 생산 능력이나 국산화 수준을 뜻하지 않습니다.</div>')

    with zone("geo", "국내 생산 기반"):
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


# ── 조회 — 분석 조건 설정 ───────────────────────────────────────────────────
Q_AREAS = ["수출입", "수출", "수입"]
Q_YEARS = list(range(2016, 2027))                            # 기간 — 시작 연도 ~ 끝 연도(2026 은 1~8월 부분연도)
# 지표 이름, 단위, 아이콘, 쓸 수 있는 분석영역 — 목업처럼 3개씩 두 줄
Q_METRICS = [("수출액", "백만 USD", "📤", {"수출입", "수출"}), ("수입액", "백만 USD", "📥", {"수출입", "수입"}),
             ("무역수지", "백만 USD", "⚖️", {"수출입"}), ("수출중량", "톤", "🚢", {"수출입", "수출"}),
             ("수입중량", "톤", "📦", {"수출입", "수입"}), ("거래건수", "건", "🧾", {"수출입", "수출", "수입"})]
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

Q_DEFAULT = {"qs_area": "수출입", "qs_hs": "HS6", "qs_ctry": ["미국", "폴란드", "사우디아라비아"], "qs_all": False,
             "qs_y0": Q_YEARS[0], "qs_y1": Q_YEARS[-1], "qs_chart": "막대 그래프",
             **{f"qs_m_{m}": m in Q_MONEY for m, *_ in Q_METRICS}}
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
    st.session_state.update(Q_DEFAULT)
    if any(k.startswith("qs_m_") for k in preset):           # 지표를 정한 설정이면 그 지표만 켠다
        st.session_state.update({f"qs_m_{m}": False for m, *_ in Q_METRICS})
    st.session_state.update(preset)
    st.session_state["qs_quick"] = "빠른 설정 불러오기"       # 고른 뒤에는 다시 안내 문구로


def _q_short(nm: str) -> str:
    """버튼에는 「그래프」 · 「차트」를 떼고 이름만 — 설명 칸 · CSV 파일명에는 전체 이름을 쓴다."""
    return nm.removesuffix(" 그래프").removesuffix(" 차트")


def _q_pick(nm: str) -> None:
    st.session_state["qs_chart"] = nm


def trade_frame(names: list[str], y0: int, y1: int, hs: str) -> pd.DataFrame:
    """국가 × 연도 교역 표(샘플). 2016~2025 합 = TRADE_IMP·TRADE_EXP, 2026 은 1~8월 부분연도.
    HS10 은 같은 금액을 더 잘게 나눠 신고한 것이라 거래건수만 늘어난다."""
    rows = []
    for k, n in enumerate(names):
        wi = [(1 + 0.07 * i) * (1 + 0.06 * math.sin(i * 1.3 + k)) for i in range(len(YEARS))]
        we = [(1 + 0.11 * i) * (1 + 0.08 * math.sin(i * 0.9 + k * 1.7)) for i in range(len(YEARS))]
        si, se = sum(wi[:-1]), sum(we[:-1])
        for i, y in enumerate(YEARS):
            if not y0 <= y <= y1:
                continue
            part = 0.62 if y == 2026 else 1
            imp = TRADE_IMP.get(n, 0) * wi[i] / si * part
            exp = TRADE_EXP.get(n, 0) * we[i] / se * part
            cnt = round(((imp + exp) * 1.8 + 3) * (1.6 if hs == "HS10" else 1))
            rows.append({"국가": n, "연도": y, "수출액": round(exp, 1), "수입액": round(imp, 1),
                         "무역수지": round(exp - imp, 1), "수출중량": round(exp * 0.52, 1),
                         "수입중량": round(imp * 0.38, 1), "거래건수": cnt})
    return pd.DataFrame(rows)


def _q_label(icon: str, text: str) -> None:
    st.markdown(f"{icon}&nbsp; **{text}**")


def _q_drop(n: str) -> None:
    st.session_state["qs_ctry"] = [c for c in st.session_state["qs_ctry"] if c != n]


# 왼쪽 글씨 칸 높이 = 오른쪽 첫 입력칸 높이(px). 위로 붙여 놓고 그 높이 안에서 가운데 → 글씨와 입력칸이 같은 가로선
Q_ROW_H = {"area": 32, "hs": 32, "ctry": 40, "period": 40, "metric": 40}
Q_CHIP_COLS = 3                                               # 고른 국가를 입력칸 밑에 한 줄 3개씩


def _q_form_css(n_picked: int, all_c: bool) -> str:
    rows = "".join(f".st-key-card_form .st-key-qlab_{k}{{height:{h}px !important;flex:0 0 auto !important;justify-content:center !important}}"
                   for k, h in Q_ROW_H.items())
    hint = "전체 국가 선택 중" if all_c else (f"국가명을 검색하세요 · {n_picked}개 선택" if n_picked else "")
    return f"""<style>{rows}
/* Streamlit 기본 margin-bottom:-16px 이 글씨 칸을 3px 로 눌러 글씨가 아래로 삐져나왔다(약 8px 낮아 보이던 원인) */
.st-key-card_form div[class*="st-key-qlab_"] [data-testid="stMarkdownContainer"],
.st-key-card_form [data-testid="stMarkdownContainer"]:has(h3){{margin-bottom:0 !important}}
.st-key-card_form div[class*="st-key-qlab_"] [data-testid="stMarkdownContainer"] p{{line-height:1.2}}
/* 국가/지역 · 기간 선택창 — 분석영역에서 고른 칸과 같은 색(연한 파랑 바탕 · 파란 테두리 · 파란 글씨) */
.st-key-qs_ctry [data-testid="stMultiSelect"] > div:last-child > div,
.st-key-qs_y0 [data-testid="stSelectbox"] > div:last-child > div,
.st-key-qs_y1 [data-testid="stSelectbox"] > div:last-child > div{{background:rgba(43,110,246,.1) !important;
  border:1px solid var(--accent) !important}}
.st-key-qs_y0 [data-testid="stSelectbox"] > div:last-child svg,.st-key-qs_y1 [data-testid="stSelectbox"] > div:last-child svg,
.st-key-qs_ctry [data-testid="stMultiSelect"] > div:last-child svg{{color:var(--accent)}}
/* 기간 연도 숫자는 검은색 */
.st-key-qs_y0 [data-testid="stSelectbox"] > div:last-child div,.st-key-qs_y1 [data-testid="stSelectbox"] > div:last-child div,
.st-key-qs_y0 [data-testid="stSelectbox"] input,.st-key-qs_y1 [data-testid="stSelectbox"] input{{color:#111;font-weight:600}}
/* 국가/지역 — 고른 국가는 입력칸 안이 아니라 밑에 칩으로 쌓는다 */
.st-key-qs_ctry [data-testid="stMultiSelectTagsContainer"] > span{{display:none}}
.st-key-qs_ctry [data-testid="stMultiSelectTagsContainer"]::before{{content:"{hint}";color:#5a7fc9;font-size:14px;
  padding-left:4px;white-space:nowrap;align-self:center}}
.st-key-qs_ctry [data-testid="stMultiSelectTagsContainer"]:has(input:focus)::before{{content:none}}
.st-key-qs_chips{{gap:6px}}
.st-key-qs_chips [data-testid="stHorizontalBlock"]{{gap:6px;margin-bottom:0 !important}}
.st-key-qs_chips button{{min-height:0;height:30px;padding:0 8px 0 12px;border-radius:6px;border:0;background:#1f3a6e;color:#fff;
  justify-content:space-between}}
.st-key-qs_chips button:hover{{background:#142850;color:#fff}}   /* 국가 칩 — 남색 */
.st-key-qs_chips button > div,.st-key-qs_chips button > div > span{{width:100%;justify-content:space-between}}
.st-key-qs_chips button p{{font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.st-key-qs_chips button [data-testid="stIconMaterial"]{{color:#fff !important;font-size:15px}}
</style>"""


def query_panel() -> dict:
    """분석 조건 설정 카드(목업 「분석 조건 설정」). 고른 조건을 dict 로 돌려준다."""
    for k, v in Q_DEFAULT.items():
        st.session_state.setdefault(k, v)
    with st.container(border=True, key="card_form"):
        h1, h2 = st.columns([1.25, 1], vertical_alignment="center")
        h1.markdown("### :material/settings: 분석 조건 설정")
        h2.selectbox("빠른 설정", list(Q_QUICK), key="qs_quick", on_change=_q_quick, label_visibility="collapsed")

        all_c = st.session_state["qs_all"]
        st.html(_q_form_css(len(st.session_state["qs_ctry"]), all_c))

        def row(icon: str, text: str, key: str):
            a, b = st.columns([1, 2.55], vertical_alignment="top")
            with a.container(key=f"qlab_{key}"):
                _q_label(icon, text)
            return b

        area = row(":material/travel_explore:", "분석영역", "area").segmented_control(
            "분석영역", Q_AREAS, key="qs_area", required=True, label_visibility="collapsed", width="stretch")
        hs = row(":material/qr_code_2:", "HS6/HS10", "hs").segmented_control(
            "HS 단위", ["HS6", "HS10"], key="qs_hs", required=True, label_visibility="collapsed")

        with row(":material/public:", "국가/지역", "ctry"):
            picked = st.multiselect("국가/지역", Q_COUNTRIES, key="qs_ctry", label_visibility="collapsed",
                                    placeholder="국가명을 검색하세요.", disabled=all_c)
            if picked and not all_c:
                with st.container(key="qs_chips"):
                    for r in range(0, len(picked), Q_CHIP_COLS):
                        for c, n in zip(st.columns(Q_CHIP_COLS, gap="small"), picked[r:r + Q_CHIP_COLS]):
                            c.button(n, icon=":material/close:", icon_position="right", key=f"qs_chip_{n}",
                                     on_click=_q_drop, args=(n,), width="stretch", help=f"{n} 빼기")
            st.checkbox(f"전체 국가 선택 ({len(Q_COUNTRIES)}개국)", key="qs_all")
        with row(":material/calendar_month:", "기간", "period"):
            # 두 칸에서 연도를 고른다 — 시작 칸은 끝 연도까지만, 끝 칸은 시작 연도부터만 보여 앞뒤가 뒤집히지 않는다
            ss = st.session_state
            c0, mid, c1 = st.columns([1, .16, 1], vertical_alignment="center", gap="small")
            y0 = c0.selectbox("시작 연도", [y for y in Q_YEARS if y <= ss["qs_y1"]], key="qs_y0", label_visibility="collapsed")
            mid.html('<div style="text-align:center;font-size:16px;font-weight:700;color:#6b7a99">~</div>')
            y1 = c1.selectbox("끝 연도", [y for y in Q_YEARS if y >= y0], key="qs_y1", label_visibility="collapsed")

        with row(":material/leaderboard:", "지표 선택", "metric"):
            cols = st.columns(3)
            metrics = []
            for i, (m, _, _, areas) in enumerate(Q_METRICS):
                ok = area in areas
                if cols[i % 3].checkbox(m, key=f"qs_m_{m}", disabled=not ok) and ok:
                    metrics.append(m)

        _q_label(":material/donut_large:", "차트 유형")
        if st.session_state["qs_chart"] not in Q_CHARTS:
            st.session_state["qs_chart"] = Q_DEFAULT["qs_chart"]
        chart = st.session_state["qs_chart"]
        st.html(_csv_css())
        # 버튼에 커서를 올리면 그 차트 설명(차트 목록 설명 칸)이 버튼 묶음 위로 떠서 조건 칸을 덮는다
        with st.container(key="qs_ct_grid"):
            for r in range(0, len(Q_CHARTS), Q_CHART_COLS):
                cols = st.columns(Q_CHART_COLS, gap="small")
                for i, (c, nm) in enumerate(zip(cols, Q_CHARTS[r:r + Q_CHART_COLS]), start=r):
                    c.button(_q_short(nm), icon=Q_CHART_ICON[nm], key=f"qs_ct_{i}", width="stretch", on_click=_q_pick, args=(nm,),
                             type="primary" if chart == nm else "secondary")
                    with c.container(key=f"qs_pop_{i}"):
                        st.html(csv_info(nm))

        names = Q_COUNTRIES if all_c else [n for n in Q_COUNTRIES if n in picked]
        q = {"area": area, "hs": hs, "names": names, "period": f"{y0} ~ {y1}", "years": (y0, y1),
             "metrics": metrics, "chart": chart}
        # CSV — 고른 차트 모양대로(조회 결과와 같은 표를 다시 짠다). 카드 오른쪽 아래.
        with st.container(key="qs_dl", horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
            if names and metrics:
                out, note = csv_shape(chart, trade_frame(names, *q["years"], hs), q)
                st.html(f'<div class="csv-note">{len(out):,}행 × {len(out.columns)}열 · {note}</div>')
                st.download_button(f"「{chart}」 모양으로 CSV 내려받기", out.to_csv(index=False).encode("utf-8-sig"),
                                   f"조회결과_{chart.replace(' ', '')}_{area}_{q['years'][0]}_{q['years'][1]}_샘플.csv",
                                   "text/csv", icon=":material/download:", type="primary")
            else:
                st.button("CSV 내려받기", icon=":material/download:", disabled=True, help="국가와 지표를 하나 이상 고르세요.")
    return q


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
        st.html(f'<div class="caption">그래프 기준: {note} · {q["hs"]} 기준.</div>')
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
    st.html(f'<div class="caption">그래프 기준: {"·".join(plot_ms)} ({unit}) · {q["hs"]} 기준. {msg}</div>')


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
/* 카드 오른쪽 아래 — CSV 내려받기 */
.st-key-qs_dl{margin-top:10px;padding-top:12px;border-top:1px dashed var(--line);gap:10px}
.csv-note{font-size:11.5px;color:#6b7a99;text-align:right}
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


def csv_info(nm: str) -> str:
    """차트 설명 칸 — 차트 목록 > 이름 · 그림 · 설명 · 용도 · CSV 모양. 차트 유형 버튼에 커서를 올리면 뜬다."""
    desc, uses, _, shape_txt = CSV_CHARTS[nm]
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
.st-tbl td:first-child,.st-tbl th:first-child{position:sticky;left:0;z-index:1;text-align:left}
.st-tbl th:first-child{z-index:3}
.st-tbl td:first-child{background:#fff;font-weight:700}
.st-tbl tr:nth-child(even) td{background:#faf8f0}
.st-tbl td.neg{color:#d64545}
.st-tbl .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px;vertical-align:-1px}
.st-note{font-size:11.5px;color:#6b7a99;margin-top:6px}
</style>"""


def _stat_cell(v: float, m: str) -> str:
    txt = f"{v:,.0f}" if Q_UNIT[m] == "건" else f"{v:,.1f}"          # 건수는 소수점 없이
    return f'<td class="neg">{txt}</td>' if v < 0 else f"<td>{txt}</td>"


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


def page_search() -> None:
    with zone("sel", "분석 조건 설정"):
        c_form, c_res = st.columns([1, 1.55], gap="medium")
        with c_form:
            q = query_panel()
        with c_res.container(border=True, key="card_res"):
            y0, y1 = q["years"]
            st.html(f'<div class="h">조회 결과 <span class="sub">{q["area"]} · {q["hs"]} · {len(q["names"])}개국 · '
                    f'{y0}~{y1} · {q["chart"]}</span></div>')
            if not q["names"]:
                st.info("국가를 하나 이상 고르거나 「전체 국가 선택」을 켜 주세요.")
            elif not q["metrics"]:
                st.info("지표를 하나 이상 고르세요. 분석영역에 맞지 않는 지표는 흐리게 잠깁니다.")
            else:
                query_result(q, y0, y1)


def query_result(q: dict, y0: int, y1: int) -> None:
    """조회 결과 카드 안 — 지표 카드 · 차트/지도/표 탭."""
    # 조건을 바꾸면 여기가 다시 계산된다 — 그동안 작은 지구본이 돈다.
    # 샘플 데이터는 즉시 끝나 지구본이 안 보이므로 데모에서만 잠깐 멈춘다(실제 앱은 DB 조회 시간만큼).
    with globe_loading("조회 결과를 계산하는 중"):
        time.sleep(DEMO_WAIT)
        df = trade_frame(q["names"], y0, y1, q["hs"])
    tot = df[list(Q_UNIT)].sum()
    icon = {m: ic for m, _, ic, _ in Q_METRICS}
    cards = "".join(
        kpi(m, f"{tot[m]:+,.0f}" if m == "무역수지" else f"{tot[m]:,.0f}", Q_UNIT[m],
            f"{len(q['names'])}개국 · {y0}~{y1} 합계", icon=icon[m]) for m in q["metrics"])
    st.html(f'<div class="kpis q" style="grid-template-columns:repeat({min(len(q["metrics"]), 3)},1fr)">{cards}</div>')

    t_chart, t_map, t_tbl = st.tabs(["📈 차트", "🗺️ 국가별 분포 지도", "📋 결과 표"])
    with t_chart:
        query_chart(df, q)
    with t_map:
        by_c = df.groupby("국가")[["수입액", "수출액"]].sum()
        modes = {"수출입": ("imp", "exp"), "수출": ("exp",), "수입": ("imp",)}[q["area"]]
        country_map({n: float(v) for n, v in by_c["수입액"].items() if v > 0},
                    {n: float(v) for n, v in by_c["수출액"].items() if v > 0},
                    modes=modes, height=400, note="선택 국가 기준")
    with t_tbl:
        stat_table(df, q)
        st.html('<div class="caption">CSV 는 분석 조건 설정 오른쪽 아래 버튼으로, 고른 차트 유형 모양대로 내려받습니다.</div>')


def page_info() -> None:
    st.html('<div class="lede"><div class="note">이 대시보드의 숫자가 어디서 왔고, 어떻게 계산했고, '
            '무엇을 뜻하지 <b>않는지</b> 적어 둔 곳입니다.</div></div>')
    with zone("src", "데이터 출처"):
        st.dataframe(pd.DataFrame([
            ["관세청", "품목별 국가별 수출입실적", "OpenAPI", "2016.01~2026.08", "월 단위 갱신"],
            ["방위사업청", "국외 조달계획", "OpenAPI 15158418", "요구연도 2024~2027", "품목 단위, 건수만"],
            ["방위사업청", "국외 입찰공고 · 입찰결과", "OpenAPI", "스냅샷", "공통 고유키로 결합"],
            ["방위사업청", "국산화개발 품목", "파일데이터", "스냅샷", "국산화율 아님"],
            ["방위사업청", "군급분류집(FSG/FSC)", "파일데이터", "스냅샷", "전자 판정은 팀 확인 전 잠정"],
            ["열린재정", "국외조달 예산", "파일데이터", "2016~2026", "보조 지표로만 사용"],
            ["KOSIS", "방산 가동률 · 광공업생산지수", "OpenAPI", "2016~2026", "잠정치(p) 구간 포함"],
        ], columns=["기관", "데이터", "형태", "기간", "비고"]), width="stretch", hide_index=True)

    with zone("match", "데이터 결합 검증"):
        c1, c2 = st.columns([1.35, 1], gap="medium")
        base, step = BID_MATCH[0][1], 5.5          # step = 층마다 양옆이 좁아지는 폭(%)
        colors = ["#2456c8", "#3b82f6", "#1fa7c4", "#2fae7a"]
        rows = "".join(
            f'<div class="fr"><div class="tz" style="background:{colors[i]};animation-delay:{i * .08:.2f}s;'
            f'clip-path:polygon({i * step}% 0,{100 - i * step}% 0,{100 - (i + 1) * step}% 100%,{(i + 1) * step}% 100%)">'
            f'{v:,}</div><div class="lb"><div>{nm}<small>({v / base * 100:.1f}%)</small></div></div></div>'
            for i, (nm, v) in enumerate(BID_MATCH))
        c1.html('<div class="card"><div class="h">입찰 공고 ↔ 결과 매칭 '
                f'<span class="sub">단위: 행 · 괄호 = 공고 행 대비</span></div><div class="funnel">{rows}</div></div>')
        (_, n_ann), (_, n_res), (_, n_key), (_, n_uni) = BID_MATCH
        c2.html(rules_card("읽는 법", [
            (f"공고키가 없는 결과 {n_res - n_key:,}행은 뺍니다", "어느 공고의 결과인지 알 수 없어 결합하지 않습니다."),
            (f"키가 맞지 않거나 중복인 {n_key - n_uni:,}행도 뺍니다", "공고 쪽에 같은 키가 없거나 한 키에 여러 행이 붙은 경우입니다."),
            (f"분석에는 공통 고유키 {n_uni:,}행만 씁니다", f"공고 {n_ann:,}행 대비 {n_uni / n_ann * 100:.1f}% — 결과가 없는 공고는 매칭 대상이 아닙니다."),
        ]))

    with zone("limit", "한계와 주의"):
        c1, c2 = st.columns(2, gap="medium")
        c1.html(rules_card("이 대시보드가 말하지 않는 것", [
            ("군수 수요 비중이 아닙니다", "관세 통계는 군수·민수를 나누지 않습니다. 국가 전체 수입액입니다."),
            ("국산화율이 아닙니다", "국산화개발을 마친 부품 수이며 비율 지표가 아닙니다."),
            ("리스크 예측·조기경보가 아닙니다", "과거 공개 통계의 현황을 보여 주는 화면입니다."),
        ]))
        c2.html(rules_card("계산 방법", [
            ("점유율", "선택 연도 수입액 합산 → 국가별 비중. 수입 실적 0 초과 국가만 셉니다."),
            ("HHI", "국가별 점유율(%)의 제곱 합. 2,500 이상이면 높은 집중으로 봅니다."),
            ("기간 기준", "부분연도(예: 2026.01~08)는 빼고 완결 연도만 씁니다."),
        ]))

    st.html('<div class="caption">이 데모 파일의 모든 수치는 샘플입니다. '
            '실제 값과 기준일은 운영 앱(app/main.py)이 AWS RDS 에서 읽어 화면마다 표시합니다.</div>')


# ════════════════════════════════════════════════════════════════════════════
# 6. 라우터 · 사이드바
# ════════════════════════════════════════════════════════════════════════════
PAGES = [
    (st.Page(page_home, title="홈", url_path="home", default=True), "HOME", "🏠",
     "K-Defense 데이터 대시보드", "방산 전자부품 수입 집중도 · 국산화 · 조달 현황 통합 모니터링"),
    (st.Page(page_import, title="수출입 현황", url_path="import"), "수출입 현황", "📊",
     "수출입 현황 대시보드", "HS/HSK 기반 방산 연관 수입 구조 · 공급국 집중도 · 품목군 동향"),
    (st.Page(page_parts, title="부품→무기체계", url_path="parts"), "부품 → 무기체계", "🧩",
     "부품 · 무기체계 대시보드", "FSG/FSC/NSN 기반 전자·통신·군수품 · 국산화 · 적용장비 분석"),
    (st.Page(page_domestic, title="국내 조달", url_path="domestic"), "국내 조달", "🧾",
     "국내 조달 대시보드", "방사청 국내 계약 · 입찰공고 · 입찰결과 — 계약 방법 · 수의계약 사유 · 유찰(실측)"),
    (st.Page(page_table, title="품목군 현황표", url_path="table"), "품목군 현황표", "📋",
     "품목군 현황표 대시보드", "분석 대상 품목군을 한 표로 비교 · 집중도 · CSV 내려받기"),
    (st.Page(page_background, title="정책·산업 배경", url_path="background"), "정책 · 산업 배경", "🏛️",
     "정책 · 산업 배경 대시보드", "정부 예산 · 방위사업청 국외조달 계획 · 국내 생산 기반"),
    (st.Page(page_search, title="조회", url_path="search"), "조회", "🔎",
     "선택형 시각화 대시보드", "원하는 조건으로 나만의 시각화를 구성하고, 결과를 내려받습니다"),
    (st.Page(page_info, title="DATA INFO", url_path="info"), "DATA INFO", "🗂️",
     "DATA INFO", "숫자가 어디서 왔고, 어떻게 계산했고, 무엇을 뜻하지 않는지"),
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
.di-ic{width:40px;height:40px;flex:0 0 40px;border-radius:50%;display:grid;place-items:center;font-size:19px;color:#fff;
  background:linear-gradient(140deg,#2b6ef6,#3fa9f5);box-shadow:0 4px 12px rgba(43,110,246,.3)}
.di-card > div:last-child{flex:1;min-width:0}
.di-t{font-size:14px;font-weight:800;color:#12234a;letter-spacing:-.3px;margin-bottom:5px}
.di-big{font-size:15px;font-weight:800;color:#16233f;line-height:1.45;letter-spacing:-.3px}
.di-s{font-size:12px;color:#6b7a99;line-height:1.55;margin-top:2px}
.di-chip{display:inline-block;margin-top:7px;padding:4px 11px;border-radius:8px;background:#eaf2ff;font-size:12px;color:#1c4ea3;font-weight:600}
.di-chip b{font-weight:800;margin-left:6px}
.di-kv{display:grid;grid-template-columns:62px 1fr;gap:4px 10px;font-size:12.5px;color:#44567a;line-height:1.5}
.di-kv b{color:#16233f;font-weight:700}
.di-card.warn{background:#fff6f6;border-color:#fbd0d2}
.di-card.warn .di-ic{background:linear-gradient(140deg,#e5484d,#f97066);box-shadow:0 4px 12px rgba(229,72,77,.3);font-weight:900}
.di-card.warn .di-t{color:#b42318}
.di-warn{margin:0!important;padding:0!important;list-style:none;counter-reset:w}
.di-warn li{counter-increment:w;position:relative;padding-left:24px;font-size:12.5px;color:#3b2a2a;line-height:1.55;margin-bottom:5px}
.di-warn li::before{content:counter(w);position:absolute;left:0;top:2px;width:17px;height:17px;border-radius:50%;background:#e5484d;
  color:#fff;font-size:10.5px;font-weight:800;display:grid;place-items:center}
.di-flow{display:flex;align-items:center;flex-wrap:wrap;gap:6px;font-size:12px;margin:4px 0 10px}
.di-flow span{padding:5px 10px;border-radius:8px;background:#eef3fb;border:1px solid #dde5f2;font-weight:700;color:#1c4ea3}
.di-flow i{font-style:normal;color:#8fb3f4;font-weight:800}
.di-sec{font-size:12.5px;font-weight:800;color:#12234a;margin:10px 0 6px}
.di-tbl{width:100%;border-collapse:collapse;font-size:12px}
.di-tbl td{padding:5px 6px;border-bottom:1px solid #eef2f9;color:#44567a;vertical-align:top}
.di-tbl td:first-child{font-weight:700;color:#16233f;white-space:nowrap}
.di-demo{font-size:11px;color:#8494ae;margin-top:8px;line-height:1.6}
</style>""")


@st.dialog("데이터 정보", width="medium")
def data_info_dialog() -> None:
    """ⓘ 단추를 누르면 뜨는 데이터 정보. 상세는 펼쳐 보기와 DATA INFO 페이지로 잇는다."""
    n_all, n_tgt = len(HS_BASIS), len(TARGET_HS)
    warns = ["HS 코드만으로 군용/민수용을 구분할 수 없습니다.",
             "특정 국가에 대한 ‘해외 의존도’라는 표현을 사용하지 않습니다.",
             "지역 통계의 수출은 ‘제조장소’, 수입은 ‘납세의무자 주소지’ 기준입니다.",
             "본 대시보드는 실제 방산 수출 실적과 차이가 있을 수 있습니다."]
    st.html(
        '<div class="di-lead">대시보드에 사용된 데이터의 출처, 수집 범위, 처리 과정 및 주요 주의사항을 안내합니다.</div>'
        '<div class="di-card"><div class="di-ic">🗄️</div><div><div class="di-t">데이터 출처</div>'
        '<div class="di-big">관세청 OpenAPI (data.go.kr)<br>데이터셋 ID: 15100475</div>'
        '<div class="di-s">수출입무역통계 (HS품목, 국가, 지역별)</div></div></div>'
        '<div class="di-card"><div class="di-ic">📅</div><div><div class="di-t">분석 기간</div>'
        '<div class="di-big">2016.01 ~ 2026.08</div><div class="di-s">(월별, 부분연도 포함)</div>'
        '<span class="di-chip">최신 수집일:<b>2026-09-14</b></span></div></div>'
        '<div class="di-card"><div class="di-ic">🧩</div><div><div class="di-t">수집 범위</div><div class="di-kv">'
        '<span>국가</span><span><b>238개국</b> (ref_country 기준)</span>'
        f'<span>HS6</span><span><b>{n_all}개</b> (수집범위) → <b>{n_tgt}개</b> (분석대상)</span>'
        '<span>국내 지역</span><span><b>17개 시도</b> (관세청 지역 분류 기준)</span></div></div></div>'
        '<div class="di-card"><div class="di-ic">📊</div><div><div class="di-t">데이터 단위</div><div class="di-kv">'
        '<span>국가 통계</span><span><b>USD</b> (관세청 기준)</span>'
        '<span>지역 통계</span><span><b>천 USD</b> (관세청 기준)</span></div></div></div>'
        '<div class="di-card warn"><div class="di-ic">!</div><div><div class="di-t">주요 주의사항</div><ol class="di-warn">'
        + "".join(f"<li>{w}</li>" for w in warns) + '</ol></div></div>')
    with st.expander("상세 정보 보기 (주요 테이블, 데이터 처리 흐름, 용어 설명 등)", icon="ℹ️"):
        st.html(
            '<div class="di-sec">데이터 처리 흐름</div><div class="di-flow">'
            '<span>OpenAPI · 파일 수집</span><i>➜</i><span>정제 (clean_*)</span><i>➜</i>'
            '<span>집계 (점유율 · HHI)</span><i>➜</i><span>대시보드</span></div>'
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
        st.page_link(PAGES[-1][0], label="DATA INFO 페이지에서 더 보기", icon=":material/arrow_forward:")
    st.html('<div class="di-demo">※ 이 데모의 화면 숫자는 대부분 샘플입니다. 위 출처·범위는 운영 앱 기준입니다.</div>')


@st.fragment
def info_button(key: str) -> None:
    """ⓘ 단추. fragment 라서 눌러도 이 단추와 대화상자만 다시 돌고, 본문 페이지(표·차트)는 다시 그리지 않는다."""
    if st.button("", icon=":material/info:", key=key, help="데이터 정보"):
        data_info_dialog()


intro_screen()

with st.sidebar:
    with st.container(key="sidebrand"):
        st.html('<div class="sb-brand"><div class="sb-mark">🛰️</div>'
                '<div><b>K-Defense</b><small>데이터로 만드는<br>더 강한 대한민국</small></div></div>')
    with st.container(key="sidenav"):
        for page, label, icon, _, _ in PAGES:
            if page is pg:
                st.html(f'<div class="nav-on">{icon}&nbsp;&nbsp;{label}</div>')
            else:
                st.page_link(page, label=f"{icon}\u2002{label}", width="stretch")
    with st.container(key="sidefoot"):
        st.html('<div class="sb-tag">DEFENSE<br>DATA<br>FOR A STRONGER<br>TOMORROW</div>'
                '<div class="sb-note">국방 데이터,<br>더 나은 의사결정을 위한 힘입니다.</div>'
                '<div class="sb-ver">디자인 데모 (샘플 데이터)<br>DB 접속 없음</div>')
    # 왼쪽 아래 ⓘ — 사이드바 맨 끝에 놓인다(굴려도 따라다니지 않음)
    info_button("info_btn")

title, sub = next((t, s) for page, _, _, t, s in PAGES if page is pg)
hero(title, sub)
pg.run()

# 미니 사이드바 — CSS 로 화면 왼쪽에 고정되고, 사이드바가 닫혔을 때만 보인다.
# 본문 흐름 중간에 두면 빈 간격이 생기므로 페이지를 다 그린 뒤 맨 끝에 둔다.
with st.container(key="minirail"):
    for page, label, icon, _, _ in PAGES:
        if page is pg:
            st.html(f'<div class="mr-on">{icon}&nbsp;&nbsp;{label}</div>')
        else:
            st.page_link(page, label=f"{icon} {label}")
    info_button("info_btn_rail")     # 사이드바를 닫았을 때
