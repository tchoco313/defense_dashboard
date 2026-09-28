"""화면 디자인 — 틀은 팀원 디자인 데모(tchoco313/defense_dashboard `dashboard/demo/design_demo.py`), 겉모양은 UI/UX 참고 URL.

데모에서 가져온 것: 사이드바 메뉴 · 머리띠 · 알약 태그 구역 · 카드 배치 · 조회 화면(조건 패널 | 결과 탭) · 세계지도 · 도넛 컴포넌트.
참고 URL 로 바꾼 것(dashboard/specs/01_design_system.md): Tremor 카드 · KPI · 밑줄 탭, KOSIS 차트 유형 타일, Datawrapper 차트 제목 · 격자 · 출처 줄.
전체 색은 파랑 · 하늘 · 흰색. 그라데이션 · 애니메이션 · 이모지 아이콘은 쓰지 않는다(흔한 AI 대시보드처럼 보이지 않게).
화면 숫자는 각 페이지가 RDS 에서 읽어 인자로 넘긴다. 이 모듈은 import 만으로 그리지 않는다 — CSS 는 inject() 로 넣는다.
"""
from __future__ import annotations

import base64
import contextlib
import re
import json
from html import escape

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ════════════════════════════════════════════════════════════════════════════
# 1. 색 토큰 · CSS
#    틀(사이드바 · 머리띠 · 구역 · 카드 배치)은 데모, 겉모양은 UI/UX 참고 URL 을 따른다(dashboard/specs/01_design_system.md):
#    Tremor = 흰 카드 · 얇은 테두리 · 작은 라벨 + 큰 숫자 · 증감 알약 배지 · 밑줄 탭 · 가는 행 구분선 · 강조색 파랑 하나,
#    KOSIS = 차트 유형 타일(그림 위 · 이름 아래), Datawrapper = 결론형 제목(핵심 구절만 색) · 옅은 가로 격자 · 아래 출처 한 줄.
#    전체 색은 파랑 · 하늘 · 흰색(2026-09-23 사용자). 그라데이션 · 그림자 들썩임 · 애니메이션 · 이모지 아이콘은 쓰지 않는다.
# ════════════════════════════════════════════════════════════════════════════
BG, PANEL, PANEL2, LINE = "#edf4fc", "#ffffff", "#eef5fc", "#dbe5f1"   # BG = 옅은 하늘(흰 카드가 도드라지게), 카드 = 흰색
TEXT, MUTED, ACCENT = "#0f1f3a", "#5b6b82", "#1d4ed8"                  # ACCENT = 대표 파랑
SKY, SKY_WEAK = "#38bdf8", "#e6f3fd"                                  # 하늘(보조 강조) · 옅은 하늘(선택 배경)
NAVY, NAVY2 = "#163c8c", "#163c8c"                                    # 사이드바 — 평면 파랑(그라데이션 없음)
UP, DOWN = "#c42b21", "#1d4ed8"                                       # 증감 — 오르면 빨강 · 내리면 파랑(2026-09-24 사용자). 옅은 배지 바탕 위 대비 4.5:1 이상
# 데이터 범주색 — 화면 틀(파랑 · 하늘 · 흰색)과 따로, 서로 잘 구분되는 8색을 고정 순서로 쓴다(dataviz 검증 팔레트).
# 검증 2026-09-23(흰 바탕): 색맹 인접 ΔE 9.1 ≥ 8 · 일반 시각 19.6 ≥ 15 통과. 청록 · 노랑 · 분홍은 대비 3:1 미만 → 범례 · 값 라벨 · 표와 함께 쓴다.
# 9번째부터는 새 색을 만들지 않고 기타(ETC)로 묶는다. 크기(연속값)는 파랑 한 계열의 진하기로(히트맵 · HHI 등급 · 지도 구간).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ETC = "#b8c2cf"

# 외부 CDN 스크립트(d3 · topojson · world-atlas · plotly.js)는 정확한 버전 + 무결성 해시(SRI)로 고정한다 — CDN 변조 시 실행되지 않게.
# 버전을 올릴 때는 새 파일의 sha384 를 다시 계산해 integrity 를 함께 바꾼다(2026-09-24 보안 감사).
# ── 글꼴 ────────────────────────────────────────────────────────────────────
SIDE_STACK = "Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif"
# @import 는 다른 규칙보다 반드시 앞에 와야 브라우저가 읽는다(뒤에 두면 통째로 무시된다).
_PRETENDARD = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
_FONTS = f"@import url('{_PRETENDARD}');\n"
_FONT_LINK = f'<link rel="stylesheet" href="{_PRETENDARD}">'   # iframe(지구본 · 도넛 · 지도 · PNG 단추)도 본문과 같은 글꼴로


def _js(obj) -> str:
    """iframe <script> 에 넣는 JSON — DB 문자열에 </script> 나 태그가 섞여도 스크립트 밖으로 새지 않게 < > & 를 이스케이프한다."""
    return (json.dumps(obj, ensure_ascii=False)
            .replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026"))

# 화면 배율 — 데모는 1.1 로 전체를 키웠으나, 배율이 오른쪽 · 아래 빈 띠와 차트 마우스 위치 어긋남을 만들어 1(끔)로 둔다.
# 1 이 아니면 아래 ZOOM_CSS 가 차트 · 표 · 선택창의 배율을 되돌리는 보정을 함께 넣는다.
APP_ZOOM = 1.0
ZOOM_CSS = "" if APP_ZOOM == 1 else (
    f"html{{zoom:{APP_ZOOM}}}"
    f'[data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{{zoom:calc(1 / {APP_ZOOM})}}'
    f'[data-rac][data-trigger],[data-rac][role="tooltip"]{{zoom:calc(1 / {APP_ZOOM})}}'
    f'[data-rac][data-trigger] > *,[data-rac][role="tooltip"] > *{{zoom:{APP_ZOOM}}}'
    f'[data-testid="stMain"]{{height:calc(100dvh / {APP_ZOOM})!important;max-height:calc(100dvh / {APP_ZOOM})!important}}')

CSS = f"""<style>
{_FONTS}{ZOOM_CSS}
html,body{{background:{BG}}}
:root{{
  --bg:{BG}; --panel:{PANEL}; --panel2:{PANEL2}; --line:{LINE};
  --text:{TEXT}; --muted:{MUTED}; --accent:{ACCENT}; --sky:{SKY}; --sky-weak:{SKY_WEAK}; --navy:{NAVY}; --navy2:{NAVY2};
  --up:{UP}; --down:{DOWN};
  --shadow:0 1px 2px rgba(15,31,58,.05);
  --shadow-h:0 1px 2px rgba(15,31,58,.05);
}}
html, body, [class*="st-"]{{font-family:{SIDE_STACK}}}
[data-testid="stIconMaterial"]{{font-family:'Material Symbols Rounded'!important}}
.material-symbols-rounded{{font-family:'Material Symbols Rounded';font-weight:400;font-style:normal;font-size:21.5px;line-height:1;
  letter-spacing:normal;text-transform:none;white-space:nowrap;direction:ltr;-webkit-font-smoothing:antialiased}}
/* 헤더는 투명하게 두고 메뉴 · 툴바만 숨긴다(사이드바 열기 버튼은 남긴다) */
[data-testid="stHeader"]{{background:transparent;height:0;pointer-events:none}}
[data-testid="stToolbar"]{{pointer-events:none}}   /* 보이지 않는 도구 막대가 머리띠 오른쪽 위 「자료 기준」 버튼 클릭을 가로채지 않게 */
[data-testid="stToolbar"] > *:not(:has([data-testid="stExpandSidebarButton"])),
[data-testid="stDecoration"],[data-testid="stStatusWidget"],[data-testid="stMainMenu"],
[data-testid="stToolbarActions"],[data-testid="stAppDeployButton"]{{display:none!important}}
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] button{{width:36px;height:36px;min-height:0;padding:0;border:none;border-radius:8px;
  display:grid;place-items:center;background:transparent}}
[data-testid="stExpandSidebarButton"]{{position:fixed!important;left:10px;top:16px;margin:0;z-index:999991;pointer-events:auto;
  background:{NAVY}}}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]{{color:#dbe7fb}}
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button{{visibility:visible!important}}
[data-testid="stSidebarCollapseButton"]{{display:block!important;position:absolute;right:10px;top:16px;margin:0;z-index:2}}
[data-testid="stAppViewContainer"]{{background:var(--bg)}}
.block-container{{padding:0 34px 40px;max-width:1500px}}

/* ── 사이드바(데모 틀 · 평면 파랑) ─────────────────────────────────────── */
[data-testid="stSidebar"]{{background:var(--navy);border-right:none;width:240px!important}}
[data-testid="stSidebar"] > div{{padding-top:0}}
[data-testid="stSidebarContent"]{{padding:0}}
[data-testid="stSidebarNav"]{{display:none}}
.st-key-sidebrand{{padding:18px 20px 16px;border-bottom:1px solid rgba(255,255,255,.12)}}
.sb-brand b{{display:block;font-size:19px;font-weight:700;letter-spacing:-.3px;color:#fff;line-height:1.25}}
.sb-brand small{{display:block;font-size:13px;color:#b8cdf0;line-height:1.5;margin-top:4px}}
.st-key-sidenav{{padding:12px 10px 0}}
.st-key-sidenav [data-testid="stVerticalBlock"]{{gap:2px}}
.st-key-sidenav [data-testid="stPageLink"] a{{padding:8px 12px;border-radius:8px;background:transparent}}
.st-key-sidenav [data-testid="stPageLink"] a:hover{{background:rgba(255,255,255,.08)}}
.st-key-sidenav [data-testid="stPageLink"] a p{{font-size:15.5px;font-weight:500;color:#dbe7fb;white-space:nowrap}}
.st-key-sidenav [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{{color:#9fbbe8}}
.st-key-nav_cur [data-testid="stPageLink"] a{{background:#fff!important;pointer-events:none}}   /* 현재 페이지 = 흰 바탕 · 다시 누르지 않게 */
.st-key-nav_cur [data-testid="stPageLink"] a p{{color:{NAVY}!important;font-weight:600}}
.st-key-nav_cur [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{{color:{ACCENT}!important}}
.st-key-sidefoot{{padding:22px 20px 16px;margin-top:8px}}
.sb-note{{font-size:13.5px;color:#b8cdf0;line-height:1.6}}
.sb-ver{{margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,.12);font-size:12.5px;color:#9fbbe8;line-height:1.6}}

/* ── 머리띠(데모 hero 자리 · 평면 옅은 하늘) ───────────────────────────── */
.st-key-hero{{margin:14px 0 6px;padding:0}}
.hero{{display:flex;align-items:flex-start;justify-content:space-between;gap:28px;padding:22px 26px 20px;background:#1e4fa8;border-radius:12px}}
.hero .ht{{flex:1 1 0;min-width:0}}
.hero h1{{margin:0;font-size:27px;font-weight:700;letter-spacing:-.5px;color:#ffffff;line-height:1.3}}
.hero p{{margin:7px 0 0;font-size:14.5px;color:#d6e6fb;line-height:1.55}}
.hero .slogan{{flex:0 0 auto;text-align:right;padding-left:22px;border-left:1px solid rgba(255,255,255,.28)}}
.hero .slogan b{{display:block;font-size:14px;font-weight:600;color:#ffffff;line-height:1.5}}
.hero .slogan small{{display:block;margin-top:5px;font-size:13px;color:#b9d2f3;line-height:1.5}}
.hero .slogan .k{{margin:0 0 3px;font-size:12px;color:#b9d2f3}}
.hero .slogan .row{{display:block;font-size:13.5px;line-height:1.6;color:#ffffff;font-weight:600;white-space:nowrap}}
.hero .slogan .row em{{font-style:normal;font-weight:400;color:#cfe0f7;margin-right:6px}}
/* 자료 기준 — 머리띠 오른쪽 알약 버튼, 누르면 아래로 흰 카드(출처 「?」와 같은 방식) */
details.basis{{flex:0 0 auto;width:max-content;position:relative;align-self:flex-start}}
details.basis > summary{{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:6px;padding:6px 13px;
  border:1px solid rgba(255,255,255,.5);border-radius:999px;color:#fff;font-size:13.5px;font-weight:600;user-select:none;white-space:nowrap}}
details.basis > summary::-webkit-details-marker{{display:none}}
/* 달력 아이콘 = CSS 배경 SVG(st.html 은 svg 태그를 걸러 낸다 · 이 CSS 안에 꺾쇠 태그 글자를 쓰면 블록 전체가 버려진다) — 글꼴 아이콘이 아니라 페이지를 옮길 때 「calendar_month」 글자가 번쩍이지 않는다 */
details.basis > summary .cal{{display:inline-block;flex:none;width:17px;height:17px;background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23cfe0f7' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='5' width='18' height='16' rx='2'/%3E%3Cpath d='M16 3v4M8 3v4M3 10h18'/%3E%3C/svg%3E") center/contain no-repeat}}
details.basis > summary:hover,details.basis[open] > summary{{background:rgba(255,255,255,.16)}}
details.basis .basis-pop{{position:absolute;right:0;top:calc(100% + 8px);z-index:50;min-width:300px;background:#fff;
  border:1px solid var(--line);border-radius:10px;padding:12px 16px;box-shadow:0 6px 18px rgba(15,31,58,.14);text-align:left}}
.basis-pop .bt{{font-size:12px;color:var(--muted);margin-bottom:6px}}
.basis-pop .row{{display:flex;justify-content:space-between;gap:18px;font-size:13.5px;line-height:1.75;color:var(--text);font-weight:600;white-space:nowrap}}
.basis-pop .row em{{font-style:normal;font-weight:400;color:var(--muted)}}
.basis-pop .bl{{margin-top:6px;padding-top:6px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}}
[class*="st-key-hero"],[class*="st-key-hero"] *:has(> details.basis){{overflow:visible}}

.demo-bar{{display:flex;align-items:center;gap:10px;margin:0 0 14px;padding:9px 14px;border-radius:8px;
  background:var(--sky-weak);border:1px solid #cfe5f8}}
.demo-bar b{{font-size:14px;font-weight:700;color:#0f2a5c}}
.demo-bar span{{font-size:13px;color:var(--muted);line-height:1.5}}

/* ── 구역(데모 알약 태그 · 평면) ───────────────────────────────────────── */
div[class*="st-key-zone_"]{{position:relative;border:1px solid var(--line);border-radius:12px;background:#fff;
  padding:30px 16px 16px;margin:16px 0 18px}}
div[class*="st-key-zone_"]::before{{position:absolute;top:-11px;left:16px;z-index:1;background:var(--accent);color:#fff;
  font-size:13.5px;font-weight:600;letter-spacing:-.1px;padding:3px 11px;border-radius:999px}}

/* ── 카드(Tremor) ─────────────────────────────────────────────────────── */
.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:15px 17px;height:100%;box-shadow:var(--shadow)}}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [class*="st-key-card_"]),
div[class*="st-key-card_"]{{background:var(--panel);border:1px solid var(--line)!important;border-radius:10px;box-shadow:var(--shadow)}}
/* 같은 줄 카드 높이 맞추기(Tremor 격자) — 열은 이미 줄 높이만큼 늘어나 있으므로, 열의 마지막 카드가 남은 높이를 채운다 */
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:last-child:has(> [class*="st-key-card_"]),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:last-child > [class*="st-key-card_"],
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:last-child:has(> [data-testid="stHtml"] > .card:only-child){{flex:1 1 auto}}
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:last-child > [data-testid="stHtml"]:has(> .card:only-child){{height:100%}}

/* ── KPI(Tremor: 작은 라벨 · 큰 숫자 · 알약 증감) ─────────────────────── */
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}}
.kpis.k4{{grid-template-columns:repeat(4,1fr)}}
.kpis.k6{{grid-template-columns:repeat(6,1fr)}}
.card.kpi{{border-top:3px solid var(--accent)}}
.kpi .kt{{display:flex;align-items:center;gap:8px;min-height:18px}}
.kpi .ico{{display:none}}
.kpi .l{{font-size:14px;font-weight:500;color:var(--muted);line-height:1.35}}
.kpi .v{{font-size:31.5px;font-weight:600;margin-top:8px;letter-spacing:-.8px;color:var(--text);line-height:1.1;
  font-variant-numeric:tabular-nums}}
.kpi .v small{{font-size:14.5px;color:var(--muted);font-weight:500;margin-left:4px;letter-spacing:0;white-space:nowrap}}   /* 단위가 「백 / 만 USD」로 쪼개지지 않게 */
.kpi .s{{font-size:13px;color:var(--muted);margin-top:8px;line-height:1.55}}
.kpi .s .up,.kpi .s .dn{{display:inline-block;color:var(--up);background:#fdecea;font-weight:600;font-size:13px;
  border-radius:6px;padding:1px 7px;margin-right:3px;font-variant-numeric:tabular-nums}}
.kpi .s .dn{{color:var(--down);background:#e8f0fe}}   /* 증감 — 오르면 빨강 · 내리면 파랑(2026-09-24 사용자) */
.ex{{display:inline-block;font-size:12px;font-weight:600;color:#075985;background:#e0f2fe;border-radius:5px;
  padding:0 6px;margin-left:6px;vertical-align:middle}}

/* ── 글(Datawrapper: 결론형 제목 · 출처 한 줄) ─────────────────────────── */
.h{{font-size:16px;font-weight:700;margin-bottom:10px;display:flex;align-items:baseline;flex-wrap:wrap;gap:4px 8px;
  color:var(--text);letter-spacing:-.3px;line-height:1.45}}
.h .sub{{font-size:13px;color:var(--muted);font-weight:400;letter-spacing:0}}
.h .key,.key{{color:var(--accent)}}
.note{{font-size:13.5px;color:#4b5b73;line-height:1.7}}
.note b{{color:var(--text);font-weight:600}}
.legend{{display:flex;gap:12px;flex-wrap:wrap;font-size:13px;color:var(--muted)}}
.legend i{{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:middle}}
.caption{{font-size:13px;color:var(--muted);line-height:1.7;margin-top:6px}}
.lede{{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;
  padding:10px 14px;margin-bottom:4px}}

/* 원칙 목록 */
.rule{{display:flex;gap:10px;margin-bottom:11px}}
.rule .ck{{width:18px;height:18px;flex:0 0 18px;border-radius:50%;display:grid;place-items:center;font-size:12px;
  background:#e8f0fe;color:var(--accent);font-weight:700}}
.rule b{{display:block;font-size:14px;font-weight:600;color:var(--text);letter-spacing:-.2px}}
.rule span{{display:block;font-size:13px;color:var(--muted);margin-top:2px;line-height:1.5}}

/* 순위 목록 */
.rank{{display:grid;grid-template-columns:22px minmax(104px,40%) 1fr 64px;align-items:center;gap:9px;height:28px;font-size:13.5px}}
.rank .no{{width:20px;height:20px;border-radius:50%;background:var(--panel2);color:var(--muted);font-size:12px;font-weight:700;
  display:grid;place-items:center}}
.rank .nm{{font-weight:500;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rank .tr{{position:relative;height:10px;border-radius:3px;background:var(--panel2)}}
.rank .fl{{position:absolute;left:0;top:0;bottom:0;border-radius:3px}}
.rank .vl{{text-align:right;font-weight:600;color:var(--text);font-size:13px;font-variant-numeric:tabular-nums}}

/* 점유율 막대 */
.bars .row{{display:grid;grid-template-columns:150px 1fr 52px;align-items:center;gap:8px;height:21px;font-size:13px}}
.bars .nm{{color:{TEXT};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bars .nm em{{color:{MUTED};font-style:normal;font-size:12px;margin-left:3px}}
.bars .track{{position:relative;height:11px;border-radius:3px;background:{PANEL2}}}
.bars .fill{{position:absolute;left:0;top:0;bottom:0;border-radius:3px}}
.bars .ref{{position:absolute;top:-4px;bottom:-4px;left:50%;border-left:1px dashed #94a7c8}}
.bars .pct{{text-align:right;color:{MUTED};font-variant-numeric:tabular-nums}}

/* 국외조달 절차 — 원 → 화살표 → 원(평면) */
.proc{{display:grid;grid-template-columns:1fr 30px 1fr 30px 1fr;align-items:start;padding:6px 0 2px}}
.proc .st{{text-align:center}}
.proc .ci{{width:84px;height:84px;margin:0 auto;border-radius:50%;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:3px;color:#fff;background:var(--accent)}}
.proc .st:nth-child(3) .ci{{background:#0369a1}} .proc .st:nth-child(5) .ci{{background:#1e3a8a}}
.proc .ci span{{display:none}}
.proc .ci b{{font-size:17.5px;font-weight:700;letter-spacing:-.3px}}
.proc .ar{{margin-top:30px;text-align:center;font-size:20px;color:#6b8fc9}}
.proc .ds{{margin-top:10px;font-size:13.5px;color:#44567a;line-height:1.55}}
.proc .n{{margin-top:6px;font-size:23.5px;font-weight:700;color:#0f2a5c;letter-spacing:-.5px;font-variant-numeric:tabular-nums}}
.proc .n small{{font-size:13.5px;color:var(--muted);font-weight:500;margin-left:3px}}

/* 깔때기(DATA INFO) */
.funnel .fr{{display:grid;grid-template-columns:1.3fr 1fr;align-items:center;gap:10px;height:48px;margin-bottom:6px}}
.funnel .tz{{height:100%;display:grid;place-items:center;color:#fff;font-size:20px;font-weight:700;letter-spacing:-.3px}}
.funnel .lb{{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;color:var(--text)}}
.funnel .lb::before{{content:"";flex:0 0 34px;border-top:1px dashed #b7c7e2}}
.funnel .lb small{{display:block;font-size:12.5px;color:var(--muted);font-weight:500;margin-top:2px}}

/* ── 위젯 ─────────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div{{background:#fff;border-color:var(--line);border-radius:8px}}
[data-testid="stSegmentedControl"] button{{border-radius:8px}}
[data-testid="stButtonGroup"] > div:not([data-testid]){{flex-wrap:wrap;row-gap:6px}}   /* 칩(pills)이 칸보다 길면 잘리지 않고 다음 줄로 */
[data-testid="stDataFrame"]{{border-radius:8px;overflow:hidden;border:1px solid var(--line)}}
[data-testid="stExpander"]{{background:#fff;border:1px solid var(--line)!important;border-radius:10px}}
.stButton button,.stDownloadButton button{{border-radius:8px;font-weight:500}}
</style>"""

# 위젯 라이트 고정 — 테마 설정 없이 OS 다크모드에서 열어도 버튼 · 선택창 · 체크박스가 같은 색으로 보이게(데모와 같은 목적)
WIDGET_CSS = """<style>
:root{color-scheme:light}
[data-testid="stMain"],div[role="dialog"]{color:var(--text)}
div[role="dialog"]{background:#fff}
button[data-testid="stBaseButton-secondary"]{background:#fff;border-color:var(--line);color:var(--text)}
button[data-testid="stBaseButton-secondary"]:hover{border-color:var(--accent);color:var(--accent)}
button[data-testid="stBaseButton-primary"]{background:var(--accent);border-color:var(--accent);color:#fff}
button[data-testid="stBaseButton-primary"]:hover{background:#1e40af;border-color:#1e40af;color:#fff}
button[data-variant="segmented_control"]{background:#fff;border-color:var(--line);color:var(--text)}
button[data-variant="segmented_control"]:hover{color:var(--accent)}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"][aria-checked="true"][data-selected]{
  background:var(--sky-weak);border-color:var(--accent);color:var(--accent)}
[data-testid="stCheckbox"] label > div:not([data-testid]){background:#fff;border-color:#b7c4da}
[data-testid="stCheckbox"] label:has(input:checked) > div:not([data-testid]){background:var(--accent);border-color:var(--accent)}
[data-testid="stCheckbox"] label:has(input:disabled){opacity:.45}
[data-testid="stSelectbox"] div[role="group"],[data-testid="stMultiSelect"] div[role="group"]{background:#fff;border-color:var(--line);color:var(--text)}
[data-testid="stSelectbox"] div[role="group"]:focus-within,[data-testid="stMultiSelect"] div[role="group"]:focus-within{border-color:var(--accent)}
[data-testid="stSelectbox"] input,[data-testid="stMultiSelect"] input{color:var(--text)}
[data-testid="stSelectbox"] input::placeholder,[data-testid="stMultiSelect"] input::placeholder{color:var(--muted)}
[data-testid="stSelectbox"] div[role="group"] button,[data-testid="stMultiSelect"] div[role="group"] button{color:var(--muted)}
[data-rac][data-trigger="ComboBox"]{background:#fff;border-color:var(--line);color:var(--text)}
[data-rac][data-trigger="ComboBox"] [role="option"] *{color:var(--text)}
[data-testid="stTooltipContent"]{background:#fff;color:var(--text)}
[data-testid="stAlertContainer"]{background:var(--sky-weak);color:#0f2a5c}
</style>"""

CHART_ANIM = ""   # 데모의 막대 · 선 등장 연출은 쓰지 않는다(정적 차트)

# ── 표 · 핵심 지표 카드 · 탭 · 조회 카드 ─────────────────────────────────────
TABLE_CSS = r"""<style>
.sc{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
.sc th{font-size:13px;font-weight:600;color:var(--muted);background:#f6f9fd;padding:9px 6px;text-align:center;
  border-bottom:1px solid var(--line);line-height:1.35;white-space:nowrap}
.sc th small{display:block;font-weight:400;color:var(--muted);font-size:12px}
.sc td{padding:9px 5px;text-align:center;border-bottom:1px solid #edf2f8;color:var(--text);white-space:nowrap}
.card:has(> table.sc){overflow-x:auto}
.sc td.no{color:var(--muted);font-weight:600}
.sc td.nm{text-align:left;font-weight:600}
.sc td.nm em{display:block;font-style:normal;font-weight:400;font-size:12px;color:var(--muted)}
.sc td.up{color:var(--up);font-weight:600} .sc td.dn{color:var(--down);font-weight:600}
.sc td.lv{font-weight:600} .sc td.lv i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px}
.sc .lvb{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12.5px;font-weight:600;white-space:nowrap}
.sc .cdot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:0}
.demo-bar.real{background:var(--sky-weak);border-color:#cfe5f8}
.basis{width:100%;border-collapse:collapse;font-size:13.5px}
.basis th{font-size:12px;font-weight:600;color:var(--muted);background:#f6f9fd;padding:7px 4px;border-bottom:1px solid var(--line);line-height:1.3}
.basis td{padding:5px 4px;border-bottom:1px solid #edf2f8;text-align:center;white-space:nowrap}
.basis td.nm{text-align:left;font-weight:500;color:var(--text)}
.basis td.nm em{font-style:normal;color:var(--muted);font-size:12px;margin-right:6px}
.basis td.cat{color:var(--muted);font-size:12.5px}
.basis i{display:inline-block;width:11px;height:11px;border-radius:50%}
.spark{display:block;margin:0 auto}
.sc .spark{width:clamp(84px,8vw,118px);height:auto}   /* 좁은 화면에서 추이선을 줄여 표 끝 칸이 잘리지 않게 */

.kgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.kc{display:flex;gap:12px;align-items:center;padding:13px 14px;border:1px solid var(--line);border-radius:10px;background:#fff}
.kc .ic{display:none}
.kc .l{font-size:13.5px;font-weight:500;color:var(--muted)}
.kc .v{font-size:27px;font-weight:600;color:var(--text);letter-spacing:-.6px;line-height:1.2;margin-top:4px;font-variant-numeric:tabular-nums}
.kc .v small{font-size:13.5px;color:var(--muted);font-weight:500;margin-left:3px;letter-spacing:0}
.kc .s{font-size:12.5px;color:var(--muted);margin-top:3px;line-height:1.4}

.bars.big{display:flex;flex-direction:column;gap:5px;margin-top:4px}
.bars.big .row{height:28px;font-size:14px}
.bars.big .track{height:14px;border-radius:3px}
.bars.big .fill{border-radius:3px}

/* 탭 — Tremor 밑줄형: 고른 탭만 파란 글씨 + 파란 밑줄 */
[data-testid="stTabs"] [role="tablist"]{gap:2px 18px;border-bottom:1px solid var(--line);box-shadow:none;padding:0 2px;margin:0;
  flex-wrap:wrap}   /* 탭이 많으면 옆으로 숨기지 않고 두 줄로 — 고른 탭 표시는 밑줄(아래 aria-selected)이 맡는다 */
[data-testid="stTabs"] [data-baseweb="tab-highlight"],[data-testid="stTabs"] [data-baseweb="tab-border"]{display:none}
[data-testid="stTabs"] [role="tablist"]::after,[data-testid="stTabs"] [role="tablist"]::before{display:none}
[data-testid="stTabs"] [data-testid="stTab"]{height:auto;padding:8px 2px 9px;margin:0 0 -1px;background:transparent;border:none;
  border-bottom:2px solid transparent;border-radius:0}
[data-testid="stTabs"] [data-testid="stTab"] p{font-size:14.5px;font-weight:500;color:var(--muted)}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"]{border-bottom-color:var(--accent)}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] p{color:var(--accent);font-weight:600}
[data-testid="stTabs"] [data-testid="stTab"] > div:not([data-testid]){display:none}
[data-testid="stTabs"] [role="tabpanel"]{padding:14px 0 0}

/* 조회 — 분석 조건 설정 카드(데모 배치) */
.st-key-card_form{padding:18px 18px 14px}
.st-key-card_form h3{font-size:20px;font-weight:700;color:var(--text);letter-spacing:-.4px;padding:0;margin:0}
.st-key-card_form [data-testid="stIconMaterial"]{color:var(--accent)}
.st-key-card_form [data-testid="stMarkdownContainer"] p{margin:0}
.st-key-card_form [data-testid="stMarkdownContainer"] strong{font-size:15px;font-weight:600;color:var(--text);letter-spacing:-.2px}
.st-key-card_form [data-testid="stMarkdownContainer"] p [data-testid="stIconMaterial"]{font-size:21.5px;vertical-align:-4px}
.st-key-card_form [data-testid="stCheckbox"] label p{font-size:14.5px}
.st-key-card_form [data-testid="stHorizontalBlock"]{margin-bottom:4px}
/* 조회 결과 — 탭을 바꿔도 카드 높이가 크게 흔들리지 않게 탭 칸에 최소 높이. CSV 단추는 탭 아래 오른쪽(차트 위에 겹치지 않게) */
.st-key-card_res [data-testid="stTabs"] [role="tabpanel"]{min-height:560px;box-sizing:border-box}
.st-key-res_dl{margin-top:4px;position:relative;z-index:2;pointer-events:none}
[data-testid="stLayoutWrapper"]:has(> .st-key-card_form),[data-testid="stLayoutWrapper"]:has(> .st-key-card_res),
.st-key-card_form,.st-key-card_res{flex:1 1 auto}
.st-key-res_dl button{pointer-events:auto}
.kpis.q{gap:10px;margin-bottom:6px}
.kpis.q .kpi .v{font-size:26px}
/* 출처 — 오른쪽 아래 「?」 원, 누르면 아래로 펼친다 */
details.src{margin-top:8px}
details.src > summary{list-style:none;display:grid;place-items:center;margin-left:auto;width:24px;height:24px;border-radius:50%;
  border:1px solid #c9d6e8;background:#fff;color:var(--muted);font-size:13.5px;font-weight:700;cursor:pointer;user-select:none}
details.src > summary::-webkit-details-marker{display:none}
details.src > summary:hover{border-color:var(--accent);color:var(--accent)}
details.src[open] > summary{border-color:var(--accent);background:var(--sky-weak);color:var(--accent)}
details.src .src-body{margin-top:6px;padding:9px 12px;border-radius:8px;background:var(--panel2);border:1px solid var(--line);
  font-size:13px;color:#4b5b73;line-height:1.65}
</style>"""


# ════════════════════════════════════════════════════════════════════════════
# 2. 공용 요소
# ════════════════════════════════════════════════════════════════════════════
def kpi(label: str, value: str, unit: str, sub: str, tag: str = "", icon: str = "") -> str:
    """KPI 카드(Tremor) — 라벨 · 큰 숫자 · 단위 · 설명. icon 은 데모 호환용 인자이며 그리지 않는다(이모지 아이콘 안 씀)."""
    t = f'<span class="ex">{tag}</span>' if tag else ""
    return (f'<div class="card kpi"><div class="kt"><div class="l">{label}{t}</div></div>'
            f'<div class="v">{value}<small>{unit}</small></div><div class="s">{sub}</div></div>')


def zone(key: str, tag: str):
    st.html(f'<style>.st-key-zone_{key}::before{{content:"{tag}"}}</style>')
    return st.container(key=f"zone_{key}")


def _stamp_period(st_: dict) -> str:
    """data_stamp 결과 → 머리띠에 쓰는 기간 문구. 기간이 없는 목록형 자료는 「기준일 미표기」, 조회 실패는 그대로 알린다."""
    if st_.get("error") and not st_.get("has_period"):
        return "조회 실패"
    if not st_.get("has_period"):
        return "기준일 미표기"
    return str(st_["period"]).replace(" (부분)", "")


def hero(title: str, subtitle: str, side: str = "", side_sub: str = "", stamps: list | None = None) -> None:
    """머리띠(데모 hero 자리) — 제목 · 이 화면에서 보는 것 한 문장 · 오른쪽 「자료 기준」 버튼.
    stamps = [(데이터 이름, db.data_stamp(...)), …] 를 주면 버튼을 누를 때 「이름 · 기간」 줄이 펼쳐진다(DB 반영일은 출처 「?」 · CSV 에)."""
    if stamps:
        # 자료 기준은 버튼 뒤에 접어 둔다 — 누르면 아래로 카드가 펼쳐진다(HTML details · 서버 재실행 없음)
        rows = "".join(f'<span class="row"><em>{escape(n)}</em>{escape(_stamp_period(s_))}</span>' for n, s_ in stamps)
        right = ('<details class="basis"><summary title="자료 기간 보기">'
                 '<span class="cal" aria-hidden="true"></span>자료 기준</summary>'
                 f'<div class="basis-pop"><div class="bt">자료 기준</div>{rows}</div></details>')
    else:
        right = f'<div class="slogan"><b>{side}</b><small>{side_sub}</small></div>' if side else ""
    with st.container(key="hero"):
        st.html(f'<div class="hero"><div class="ht"><h1>{title}</h1><p>{subtitle}</p></div>{right}</div>')


def real_bar(src: str) -> None:
    """실측 집계를 쓰는 구역 표시(데모 경고 띠 자리)."""
    st.html(f'<div class="demo-bar real"><b>실측 집계</b><span>{src}</span></div>')


def style_fig(fig, height: int | None = None):
    """Datawrapper 식 — 배경 투명 · 옅은 가로 격자만 · 세로 격자와 축선 없음 · 범례는 위 가로."""
    grid = "#e8eef6"
    m = fig.layout.margin                   # 차트가 미리 정한 여백(예: 가로 막대의 라벨 자리)은 그대로 둔다
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=SIDE_STACK, color=TEXT, size=13.5), title_font=dict(size=15.5, color=TEXT),
                      legend=dict(font=dict(color=MUTED), bgcolor="rgba(0,0,0,0)"),
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor=LINE, font=dict(color=TEXT)),
                      margin=dict(l=8 if m.l is None else m.l, r=8 if m.r is None else m.r,
                                  t=10 if m.t is None else m.t, b=8 if m.b is None else m.b))
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, tickfont=dict(color=MUTED), title_font=dict(color=MUTED),
                     automargin=True)
    fig.update_yaxes(gridcolor=grid, zeroline=False, showline=False, tickfont=dict(color=MUTED), title_font=dict(color=MUTED),
                     automargin=True)
    # 눈금 숫자는 화면 다른 곳처럼 쉼표로(6000 → 6,000, 5k → 5,000). 연도 축(2016 …)은 쉼표를 넣지 않는다
    for axis, update in (("x", fig.update_xaxes), ("y", fig.update_yaxes)):
        years = any(_yearish(t[axis]) for t in fig.data if axis in t and t[axis] is not None)
        update(exponentformat="none", **({} if years else {"separatethousands": True}))
    if fig.layout.legend.orientation is None:
        fig.update_layout(legend=dict(orientation="h", y=1.1, x=0, title=None))
    if height:
        fig.update_layout(height=height)
    _floor_fonts(fig)
    return fig


_LABEL_POS = {   # plotly textposition → 라벨 상자 왼쪽 위(점 중심 기준, 픽셀). r = 점 반지름, w · h = 라벨 크기
    "top center": lambda r, w, h: (-w / 2, -r - 2 - h), "bottom center": lambda r, w, h: (-w / 2, r + 2),
    "middle right": lambda r, w, h: (r + 3, -h / 2), "middle left": lambda r, w, h: (-r - 3 - w, -h / 2),
    "top right": lambda r, w, h: (r * .6, -r - h), "top left": lambda r, w, h: (-r * .6 - w, -r - h),
    "bottom right": lambda r, w, h: (r * .6, r), "bottom left": lambda r, w, h: (-r * .6 - w, r),
}


def point_labels(xs, ys, texts, xr, yr, w: float = 460, h: float = 290, fs: float = 13, r: float = 7):
    """산점도 점 이름이 서로 · 다른 점과 겹치지 않게 자리(textposition)를 고른다. 세로값이 큰 점부터 놓고,
    여덟 자리 모두 막히면 그 점의 이름은 비운다(커서를 올리면 보인다). xr · yr = 그림에 줄 축 범위, w · h = 그림 칸 대략 픽셀."""
    pts = [((x - xr[0]) / (xr[1] - xr[0]) * w, (1 - (y - yr[0]) / (yr[1] - yr[0])) * h) for x, y in zip(xs, ys)]
    dots = [(cx - r, cy - r, 2 * r, 2 * r) for cx, cy in pts]
    placed: list[tuple[float, float, float, float]] = []
    over = lambda a, b: a[0] < b[0] + b[2] and a[0] + a[2] > b[0] and a[1] < b[1] + b[3] and a[1] + a[3] > b[1]
    out_t, out_p = [""] * len(pts), ["top center"] * len(pts)
    for i in sorted(range(len(pts)), key=lambda k: -ys[k]):
        t = str(texts[i])
        tw, th = sum(fs * (1.0 if ord(c) > 0x2E80 else .6) for c in t), fs * 1.3
        for pos, off in _LABEL_POS.items():
            dx, dy = off(r, tw, th)
            box = (pts[i][0] + dx, pts[i][1] + dy, tw, th)
            if box[0] < 0 or box[1] < 0 or box[0] + tw > w or box[1] + th > h:
                continue
            if any(over(box, d) for k, d in enumerate(dots) if k != i) or any(over(box, p) for p in placed):
                continue
            placed.append(box)
            out_t[i], out_p[i] = t, pos
            break
    return out_t, out_p


def _yearish(vals) -> bool:
    """축 값이 모두 연도(1900~2100 정수)인가 — 연도 눈금에는 천 단위 쉼표를 넣지 않는다."""
    try:
        xs = [float(v) for v in vals if v is not None]
    except (TypeError, ValueError):
        return False
    return bool(xs) and all(1900 <= v <= 2100 and v == int(v) for v in xs)


def _floor_fonts(fig, lo: float = 13) -> None:
    """차트 글씨 하한(2026-09-23 사용자 — 작게 만들지 않는다): 눈금 · 범례 · 주석 · 값 라벨에 lo 보다 작게 정한 크기를 lo 로 올린다."""
    small = lambda f: f is not None and isinstance(f.size, (int, float)) and f.size < lo
    for ax in [*fig.select_xaxes(), *fig.select_yaxes()]:
        if small(ax.tickfont):
            ax.tickfont.size = lo
    if small(fig.layout.legend.font):
        fig.layout.legend.font.size = lo
    for a in fig.layout.annotations or ():
        if small(a.font):
            a.font.size = lo
    for tr in fig.data:
        if "textfont" in tr and small(tr.textfont):
            tr.textfont.size = lo


def chart_title(title: str, sub: str = "", where=None) -> None:
    """Datawrapper 결론형 제목 줄 — title 은 결론 문장(핵심 구절 하나만 <span class="key">…</span>), sub 는 단위 · 기간만.
    DB 에서 온 이름(품목 · 국가)은 호출하는 쪽이 escape 해서 넣는다. 표 · 뷰 이름은 여기 넣지 않고 chart_source 로."""
    (where or st).html(f'<div class="h"><span>{title}</span>' + (f'<span class="sub">{sub}</span>' if sub else "") + "</div>")


_DB_BITS = re.compile(r"\b(?:clean|fact|dim|ref|meta|raw)_[a-z0-9_]+|\bv_[a-z0-9_]+|\b[a-z][a-z0-9]*_[a-z0-9_]+\b"
                      r"|DB\s*(?:적재|반영)|팀\s*DB|AWS|RDS|DBHub|schema|스키마")


def public_source(text: str) -> str:
    """사용자에게 보이는 출처에서 DB 내부 정보(표 · 뷰 · 열 이름, 「팀 DB」, DB 적재 · 반영일)를 걸러 낸다 — 보안(2026-09-24 사용자).
    「기관 · 데이터명 → DB 표 · 기간 · DB 적재 날짜」 → 「기관 · 데이터명 · 기간」. 화면 출처 「?」 · PNG 출처 줄 · CSV 머리줄이 모두 이 함수를 지난다."""
    parts = [p.strip(" ·,.;") for p in re.split(r"\s*(?:→|->|·)\s*", str(text))]
    keep = [p for p in parts if p and not _DB_BITS.search(p)]
    out = " · ".join(dict.fromkeys(keep))          # 같은 조각이 겹치면 한 번만
    return re.sub(r"^출처:\s*", "", out).strip() or "공개 자료"


def source_pop(text: str) -> str:
    """출처를 「?」 원 뒤에 접어 두는 HTML — 누르면 펼쳐지고 다시 누르면 접힌다(HTML details · 서버 재실행 없음).
    화면은 깔끔하게, 인용할 사람은 한 번 눌러 확인한다. 내려받는 PNG · CSV 에는 출처가 그대로 들어간다."""
    body = f"출처: {public_source(text)}"
    return (f'<details class="src"><summary title="출처 보기" aria-label="출처 보기">?</summary>'
            f'<div class="src-body">{body}</div></details>')


def chart_source(text: str, where=None) -> None:
    """차트 아래 출처 — 「?」 원을 누르면 「출처: 기관 · 데이터명 → DB 표 · 자료 기간 · 적재일」이 펼쳐진다."""
    (where or st).html(source_pop(text))


def rules_card(title: str, items: list[tuple[str, str]]) -> str:
    body = "".join(f'<div class="rule"><span class="ck">✓</span><div><b>{t}</b><span>{d}</span></div></div>'
                   for t, d in items)
    return f'<div class="card"><div class="h">{title}</div>{body}</div>'


def rank_card(title: str, sub: str, rows: list[tuple[str, float, str]], unit: str) -> str:
    top = max(v for _, v, _ in rows) or 1
    body = "".join(
        f'<div class="rank"><span class="no">{i}</span><span class="nm" title="{n}">{n}</span>'
        f'<span class="tr"><span class="fl" style="width:{v / top * 100:.0f}%;background:{c}"></span></span>'
        f'<span class="vl">{v:,.0f}</span></div>'
        for i, (n, v, c) in enumerate(rows, 1))
    # 제목은 한 <span> 으로 싼다 — .h 는 flex 라 글자 · 강조 구절이 따로 놓이면 사이가 벌어진다
    return (f'<div class="card"><div class="h"><span>{title}</span><span class="sub">단위: {unit}</span></div>'
            f'<div style="font-size:13px;color:{MUTED};margin-bottom:6px">{sub}</div>{body}</div>')


# ── 공급망 현황 · 공급 집중도 요소 ────────────────────────────────────────────
def hhi_level(hhi: float) -> tuple[str, str]:
    """HHI 구간 이름과 색 — 위험 예측이 아니라 집중 수준만 나눈다. 색은 파랑 명도(진할수록 집중)."""
    if hhi >= 2500:   # 한 단계만 — 2010 합병 지침 고집중 기준(근거 없는 4,000 구간은 두지 않는다)
        return "높음", "#1e3a8a"
    return "보통", "#93c5fd"


def _svg_img(svg: str, w: int, h: int, cls: str = "") -> str:
    """st.html 은 <svg> 태그를 지우므로 data URI 이미지로 싸서 넣는다."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img class="{cls}" width="{w}" height="{h}" alt="" src="data:image/svg+xml;base64,{b64}">'


_SPARK_STYLE = "<style>polyline{fill:none;stroke-width:1.6;stroke-linejoin:round}</style>"


def sparkline(vals: list[float], color: str = ACCENT, w: int = 118, h: int = 30) -> str:
    """작은 추이선(끝점 강조) — 정지 그림."""
    lo, hi = min(vals), max(vals)
    sx = (w - 6) / (len(vals) - 1)
    pts = [(2 + i * sx, h - 4 - (v - lo) / ((hi - lo) or 1) * (h - 8)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{_SPARK_STYLE}'
           f'<polygon points="2,{h} {line} {pts[-1][0]:.1f},{h}" fill="{color}" fill-opacity=".08"/>'
           f'<polyline points="{line}" stroke="{color}"/>'
           f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.6" fill="{color}"/></svg>')
    return _svg_img(svg, w, h, "spark")


LV_BG = {"높음": "#1e3a8a", "보통": "#f1f5fa"}    # 공급 집중 등급 배지 — 진할수록 집중
LV_FG = {"높음": "#ffffff", "보통": "#5b6b82"}


def supply_table(rows: list[dict]) -> str:
    """부품별 공급망 현황 표. rows 의 color(1위 공급국 국가 색)가 있으면 이름 앞 점 · 추이선에 쓴다(같은 나라 = 같은 색)."""
    head = ("<tr><th>No.</th><th>품목군</th><th>1위 공급국</th><th>최근 수입액 추이<small>(최근 12개월)</small></th>"
            "<th>수입액 변화<small>(전년 대비)</small></th><th>수입국<small>(개)</small></th>"
            "<th>집중도<small>(HHI)</small></th><th>1위 점유율</th><th>공급 집중</th></tr>")
    body = ""
    for i, f in enumerate(rows, 1):
        up = f["yoy"] >= 0
        lvl, lc = hhi_level(f["hhi"])
        body += (f'<tr><td class="no">{i}</td><td class="nm">{escape(str(f["name"]))}<em>HS {escape(str(f["hs"]))}</em></td>'
                 f'<td><span class="cdot" style="background:{f.get("color", ACCENT)}"></span>{escape(str(f["top"]))}</td>'
                 f'<td>{sparkline(f["m"], f.get("color", ACCENT))}</td>'
                 f'<td class="{"up" if up else "dn"}">{"▲" if up else "▼"} {abs(f["yoy"]):.1f}%</td>'
                 f'<td>{f["n"]}</td><td>{f["hhi"]:,}</td><td>{f["s1"]:.1f}%</td>'
                 f'<td class="lv"><span class="lvb" style="background:{LV_BG[lvl]};color:{LV_FG[lvl]}">{lvl}</span></td></tr>')
    return (f'<div class="card"><div class="h">부품별 공급망 현황 <span class="sub">품목군 {len(rows)}개 · '
            f'공급 집중 = HHI 2,500 이상 높음</span></div>'
            f'<table class="sc"><thead>{head}</thead><tbody>{body}</tbody></table>'
            f'<div class="caption">추이·변화율은 최근 12개월과 그 전 12개월의 월별 수입액 비교 · '
            f'국산화율은 이 대시보드가 다루지 않습니다.</div></div>')


def core_kpis(cards: list[tuple[str, str, str, str, str, str, str]], basis: str) -> str:
    """핵심 지표 카드 묶음. cards = [(아이콘(안 그림), 배경(안 씀), 라벨, 값, 단위, 설명, 값 style)]."""
    body = "".join(f'<div class="kc"><div>'
                   f'<div class="l">{l}</div><div class="v" style="{vs}">{v}<small>{u}</small></div>'
                   f'<div class="s">{s}</div></div></div>' for _ic, _bg, l, v, u, s, vs in cards)
    return (f'<div class="card"><div class="h">핵심 지표 <span class="sub" style="margin-left:auto">기준: {basis}</span></div>'
            f'<div class="kgrid">{body}</div></div>')


def share_card(f: dict) -> str:
    sh = f["shares"]
    rest = sum(s for _, s in sh[5:])
    cmap = f.get("colors", {})
    rows = [(n, s, cmap.get(n, "#93c5fd")) for n, s in sh[:5]] + ([("기타", rest, ETC)] if rest > 0.05 else [])
    body = "".join(f'<div class="row" title="{n} {s:.1f}%"><div class="nm">{n}</div><div class="track">'
                   f'<div class="fill" style="width:{s:.1f}%;background:{c}"></div><div class="ref"></div></div>'
                   f'<div class="pct">{s:.1f}%</div></div>' for n, s, c in rows)
    return (f'<div class="card"><div class="h">공급 국가 비중 <span class="sub">{f["name"]} · HS {f["hs"]} · '
            f'점선 = 50%</span></div><div class="bars big">{body}</div>'
            f'<div class="caption">수입국 {f["n"]}개 중 상위 5개국</div></div>')


# ════════════════════════════════════════════════════════════════════════════
# 3. 공급국 지구본 · 로딩 표시
#    지구본은 데모 HOME 그대로(회전 · 끌어 돌리기 · 지구본↔지도 · 흐름 화살표) — 버튼 이모지 · 그라데이션만 뺐다(2026-09-24 사용자).
#    데모의 인트로 화면 · 로딩 지구본은 쓰지 않는다(globe_loading 은 로딩 문구).
# ════════════════════════════════════════════════════════════════════════════
KOREA = [127.8, 36.5]
_GLOBE = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">__FONTLINK__
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js" integrity="sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js" integrity="sha384-Ukv1p/xTma6P4/2bY5KzWBw+ydSpXmhCMtyciIQVDJ1RmOxtCYNMF1uXT9T63H67" crossorigin="anonymous"></script>
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
  #status{font-size:13px;font-weight:700;color:#3d5b8c;letter-spacing:-.2px}
  #ctrl{position:absolute;right:12px;top:10px;display:flex;gap:6px;z-index:6}
  #ctrl button{font:600 13px Pretendard,system-ui,sans-serif;color:#3d5b8c;background:rgba(255,255,255,.88);
    border:1px solid #dde5f2;border-radius:9px;padding:5px 11px;cursor:pointer;box-shadow:0 1px 3px rgba(19,42,84,.08);transition:all .15s}
  #ctrl button:hover{background:#fff;color:#1d4ed8;border-color:#b9d1fb}
  #ctrl button.on{background:#1d4ed8;color:#fff;border-color:#1d4ed8}
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
  <div id="ctrl"><button id="b-globe" class="on">지구본</button><button id="b-map">지도</button><button id="b-replay">흐름 다시</button></div>
  <div id="tip"></div>
</div>
<script>
const PTS = __DATA__, KOREA = __KOREA__, UNIT = "__UNIT__";
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
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
  tip.innerHTML='<b>'+esc(p.name)+'</b><div class="v">'+p.value.toLocaleString(undefined,{maximumFractionDigits:1})+' '+UNIT+'</div>'
    +(p.note?'<div class="n">'+esc(p.note)+'</div>':'');
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
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json", {integrity: "sha384-yOCJ+8ShBm8UDqtAVtAvxTDDf4gXo5edxl/YG0FmVC5OTmqVLl7utuVGBDEeZWHf"}).then(r=>r.json()).then(topo=>{
  world=topojson.feature(topo,topo.objects.countries); drawGlobe(); drawMap();
}).catch(()=>{statusEl.textContent='지도 데이터를 불러오지 못해 경위선만 표시합니다(인터넷 연결 확인)';});
</script></body></html>
"""




def supply_globe(points: list[dict], height: int = 430, unit: str = "백만 USD"):
    """공급국 지구본(데모 HOME 그대로) — 회전 · 끌어서 돌리기 · 지구본↔지도 전환 · 공급국 → 한국 흐름 화살표.
    points = [{name, lat, lon, value, color, note}] — 원 색 = 국가 색(표 · 막대와 같은 색), 원 크기 = 수입액.
    지구본은 HTML 이라 PNG 로 바로 저장할 수 없어, 같은 값의 평면 지도(plotly)를 만들어 돌려준다(화면에는 그리지 않음 — PNG 단추용)."""
    html = (_GLOBE.replace("__DATA__", _js(points))
            .replace("__KOREA__", _js(KOREA)).replace("__UNIT__", unit)
            .replace("__H__", str(height - 10)).replace("__FONTLINK__", _FONT_LINK))
    components.html(html, height=height, scrolling=False)
    fig = go.Figure()
    if points:
        vmax = max(p["value"] for p in points) or 1
        fig.add_trace(go.Scattergeo(
            lat=[p["lat"] for p in points], lon=[p["lon"] for p in points], mode="markers+text",
            text=[p["name"] for p in points], textposition="top center", textfont=dict(size=12.5, color=TEXT),
            marker=dict(size=[p["value"] for p in points], sizemode="area", sizeref=2 * vmax / 46 ** 2, sizemin=5,
                        color=[p.get("color", ACCENT) for p in points], opacity=.85, line=dict(color="#ffffff", width=1.2))))
    fig.update_geos(projection_type="natural earth", showland=True, landcolor="#e8f0fa", showocean=True, oceancolor="#ffffff",
                    showcountries=True, countrycolor="#ffffff", coastlinecolor="#d3e0f0", showframe=False, bgcolor="rgba(0,0,0,0)",
                    lataxis_range=[-50, 75])
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      font=dict(family=SIDE_STACK))
    return fig


@contextlib.contextmanager
def globe_loading(text: str = "조회 중", height: int = 0):
    """조회 · 집계가 끝날 때까지 로딩 문구를 보인다(데모의 회전 지구본 대신). height 는 호환용."""
    with st.spinner(text):
        yield

# ════════════════════════════════════════════════════════════════════════════
# 3-3. 도넛 공통 — 반지름·둘레·굵기와 커서 반응(조각 확대 · 가운데 라벨)
# ════════════════════════════════════════════════════════════════════════════
R = 92                       # 도넛 반지름(얇은 링 — Tremor)
C = round(2 * 3.141592653589793 * R, 2)      # 둘레 = stroke-dasharray 기준
STROKE = 24                  # 도넛 두께
# 커서를 올린 조각: 굵기를 키우면서 바깥쪽으로 확대한다. 안쪽 가장자리는 그대로 두어(≈56) 가운데 글자를
# 가리지 않고, 보이는 두께는 약 2배(48 → 96)가 된다.
HOVER_STROKE = 24
HOVER_SCALE = 1.0
HOVER_OUT = round(HOVER_SCALE * (R + HOVER_STROKE / 2))     # 커진 조각의 바깥 반지름 ≈ 152

# ── 도넛 공통: 조각(또는 범례)에 커서를 올리면 그 조각이 두꺼워지고 가운데에 라벨·값·비율이 뜬다 ──
# 조각 <circle> 에 class="hv", 가운데 글자는 .c-lab / .c-sub / .c-val, 범례 항목은 .lg 로 맞춰 두면 된다.
def _hover_css(cx: float, cy: float) -> str:
    return f"""
  .hv{{transform-origin:{cx}px {cy}px}}
  .hv.on{{stroke-width:{HOVER_STROKE};transform:scale({HOVER_SCALE})}}
  .focusing .hv:not(.on){{stroke-opacity:.28}}
  .c-val{{font-size:13.5px;font-weight:600;fill:#6b7a99;text-anchor:middle}}
  .lg{{padding:2px 6px;border-radius:6px;cursor:default;}}
  .lg.on{{background:#e6f3fd}}
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
  // 가운데 설명이 도넛 구멍보다 길면 두 줄로 나눈다(띄어쓰기 기준) — 링 위로 넘치지 않게
  const MAXW = 2 * IN - 16, VAL_Y = +val.getAttribute('y');
  function putSub(text) {
    sub.textContent = text;
    let lines = 1;
    if (sub.getComputedTextLength() > MAXW) {
      const w = text.split(' ');
      if (w.length > 1) {
        let k = 1, best = 1e9;
        for (let j = 1; j < w.length; j++) {
          const d = Math.abs(w.slice(0, j).join(' ').length - w.slice(j).join(' ').length);
          if (d < best) { best = d; k = j; }
        }
        sub.textContent = '';
        [w.slice(0, k).join(' '), w.slice(k).join(' ')].forEach((s, i) => {
          const t = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
          t.setAttribute('x', CX); t.setAttribute('dy', i ? '1.3em' : '0'); t.textContent = s; sub.appendChild(t);
        });
        lines = 2;
      }
    }
    val.setAttribute('y', VAL_Y + (lines - 1) * 17);
  }
  putSub(orig[1]);
  const segs = D.map((_, i) => document.getElementById('seg' + i));
  const lgs = [...stage.querySelectorAll('.lg')];
  let cur = -1;
  function focus(i) {
    if (i === cur) return; cur = i;
    stage.classList.toggle('focusing', i >= 0);
    segs.forEach((s, k) => s.classList.toggle('on', k === i));
    lgs.forEach((g, k) => g.classList.toggle('on', k === i));
    if (i < 0) { lab.textContent = orig[0]; putSub(orig[1]); val.textContent = ''; return; }
    const d = D[i];
    lab.textContent = (d.p * 100).toFixed(1) + '%';
    putSub(d.l);
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
    return (_HOVER_JS.replace("__DATA__", _js(data))
            .replace("__CX__", str(cx)).replace("__CY__", str(cy))
            .replace("__IN__", str(R - STROKE / 2 - 4)).replace("__OUT__", str(R + STROKE / 2 + 4))
            .replace("__OUTH__", str(HOVER_OUT))
            .replace("__ON__", on).replace("__UNIT__", _js(unit)))


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
            .replace("__H__", str(height - 10)).replace("__FONTLINK__", _FONT_LINK)
            .replace("__HOVER__", _hover_js(rows, 170, 170, "shown", value_unit)))
    components.html(html, height=height, scrolling=False)


_DONUT_TPL = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">__FONTLINK__
<style>
  *{box-sizing:border-box}
  body{margin:0;background:transparent;overflow:hidden;user-select:none;
       font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;color:#0f1f3a}
  #stage{width:100%;height:__H__px;display:flex;flex-direction:column;align-items:center;justify-content:center}
  .ring-g{transform:rotate(-90deg);transform-origin:170px 170px}   /* 12시에서 시작 */
  .seg{fill:none;stroke-width:24;stroke-dasharray:0 __C__;transition:stroke-opacity .15s ease}
  .c-lab{font-size:24.5px;font-weight:700;fill:#0f1f3a;text-anchor:middle;letter-spacing:-.6px}
  .c-sub{font-size:14px;fill:#6b7a99;text-anchor:middle}
  .legend{display:flex;gap:7px 12px;flex-wrap:wrap;justify-content:center;max-width:460px;margin-top:6px;
    font-size:13px;color:#5d6d8c}
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
<!DOCTYPE html><html><head><meta charset="utf-8">__FONTLINK__
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js" integrity="sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js" integrity="sha384-Ukv1p/xTma6P4/2bY5KzWBw+ydSpXmhCMtyciIQVDJ1RmOxtCYNMF1uXT9T63H67" crossorigin="anonymous"></script>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;
       color:#16233f;background:transparent;overflow:hidden;user-select:none}
  #wrap{position:relative;width:100%;height:__H__px;border-radius:12px;overflow:hidden;
        background:#ffffff;--c:#1d4ed8}
  #top{position:absolute;left:14px;right:12px;top:10px;display:flex;align-items:center;justify-content:space-between;z-index:6}
  #unit{font-size:12.5px;color:#6b7a99;font-weight:600}
  #seg{display:flex;background:#fff;border:1px solid #dde5f2;border-radius:11px;padding:3px}
  #seg button{font:700 13.5px Pretendard,system-ui,sans-serif;color:#5b6f94;background:transparent;border:0;border-radius:8px;
    padding:6px 22px;cursor:pointer}
  #seg button:hover{color:var(--c)}
  #seg button.on{color:#fff;background:var(--c)}
  #seg.one{display:none}
  svg{display:block}
  .land{stroke:#fff;stroke-width:.6}
  .land.has:hover{opacity:.78}
  #tip{position:absolute;z-index:9;pointer-events:none;opacity:0;transform:translate(-50%,-120%);background:#fff;
    border:1px solid #dde5f2;border-radius:10px;padding:8px 11px;box-shadow:0 2px 8px rgba(15,31,58,.10);
    white-space:nowrap;font-size:13px;color:#44567a;line-height:1.55}
  #tip b{display:block;font-size:14px;font-weight:800;color:#16233f;letter-spacing:-.3px}
  #tip em{font-style:normal;font-weight:800}
  #msg{position:absolute;inset:0;display:grid;place-items:center;font-size:13.5px;color:#6b7a99;pointer-events:none}
  @keyframes pop{from{opacity:0;transform:translate(-50%,-50%) scale(.7)}to{opacity:1;transform:translate(-50%,-50%)}}
  @keyframes fade{from{opacity:0}to{opacity:1}}
"""

_WORLD_MAP = _MAP_HEAD + r"""
  #svg{position:absolute;inset:0;width:100%;height:100%}
  .dotc{stroke:#fff;stroke-width:1.3}
  .lead{stroke:#8ea3c4;stroke-width:1;stroke-dasharray:2 2}
  .anc{fill:#0f1f3a}
  #labels{position:absolute;inset:0;pointer-events:none;z-index:4}
  .lb{position:absolute;transform:translate(-50%,-50%);background:rgba(255,255,255,.96);border:1px solid #d5e0f2;
    border-radius:6px;padding:3px 9px;text-align:center;white-space:nowrap}
  .lb b{display:block;font-size:13px;font-weight:800;color:#16233f;letter-spacing:-.3px;line-height:1.3}
  .lb span{display:block;font-size:14.5px;font-weight:800;letter-spacing:-.3px;line-height:1.25}
  #legend{position:absolute;left:12px;bottom:12px;z-index:5;background:rgba(255,255,255,.92);border:1px solid #dde5f2;
    border-radius:10px;padding:7px 12px;font-size:12.5px;color:#44567a}
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
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const PAL = {imp: {c: '#1d4ed8', t: '#1e3a8a', bins: ['#1e3a8a', '#1d4ed8', '#3b82f6', '#93c5fd', '#dbeafe']},
             exp: {c: '#eb6834', t: '#a8431c', bins: ['#a8431c', '#eb6834', '#f39a70', '#f8c4aa', '#fde8dd']}};
const CUT = [20, 10, 5, 1, 0], CUT_TXT = ['20% 이상', '10 - 20%', '5 - 10%', '1 - 5%', '1% 미만'];
const KOR = {imp: '수입', exp: '수출'};
const wrap = document.getElementById('wrap'), tip = document.getElementById('tip'), labels = document.getElementById('labels');
const gl = d3.select('#gl'), gd = d3.select('#gd'), gk = d3.select('#gk');
const byId = {};
function resolve() {                       // 국가 좌표를 품은 면을 찾아 면 id ↔ 국가명을 잇는다(없으면 점으로 찍는다)
  for (const [n, v] of Object.entries(INFO)) {
    const f = world.features.find(g => g.id !== '010' && d3.geoContains(g, [v[2], v[1]]));
    if (f && !(f.id in byId)) { v[0] = f.id; byId[f.id] = n; }
  }
}
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
  tip.innerHTML = '<b>' + esc(n) + '</b>' + KOR[mode] + ' <em style="color:' + PAL[mode].t + '">'
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
  const dots = Object.keys(S).filter(n => INFO[n] && !INFO[n][0]);
  gd.selectAll('circle').data(dots, d => d).join('circle').attr('class', 'dotc').attr('r', 5.5)
    .attr('cx', n => proj([INFO[n][2], INFO[n][1]])[0]).attr('cy', n => proj([INFO[n][2], INFO[n][1]])[1])
    .attr('fill', n => P.bins[bin(S[n].p)])
    .on('mousemove', (ev, n) => tipShow(ev, n, S[n], O[n])).on('mouseleave', tipHide);
  // 상위 국가 라벨 — 큰 나라부터 제자리에 놓고, 겹치면 빈 곳으로 옮겨 점선으로 나라와 잇는다(1위 라벨이 가려지지 않게)
  labels.innerHTML = ''; gk.selectAll('*').remove();
  const W = wrap.clientWidth, H = wrap.clientHeight, placed = [];
  const clash = r => placed.some(q => r.x < q.x + q.w + 4 && r.x + r.w + 4 > q.x && r.y < q.y + q.h + 4 && r.y + r.h + 4 > q.y);
  Object.entries(S).filter(([n]) => INFO[n]).sort((a, b) => b[1].v - a[1].v).slice(0, TOPN).forEach(([n, s], k) => {
    const [, la, lo] = INFO[n], xy = proj([lo, la]);
    if (!xy) return;
    const el = document.createElement('div');
    el.className = 'lb'; el.style.animationDelay = (k * .06) + 's';
    el.innerHTML = '<b>' + esc(n) + '</b><span style="color:' + P.t + '">' + s.p.toFixed(1) + '%</span>';
    labels.appendChild(el);
    const w = el.offsetWidth, h = el.offsetHeight, cand = [[0, 0]];
    for (const d of [1, 1.6, 2.3]) for (const [ux, uy] of [[0, -1], [0, 1], [1, 0], [-1, 0], [1, -1], [-1, -1], [1, 1], [-1, 1]])
      cand.push([ux * (w + 8) * d * .75, uy * (h + 6) * d]);
    let pick = null;
    for (const [dx, dy] of cand) {
      const r = {x: xy[0] + dx - w / 2, y: xy[1] + dy - h / 2, w, h};
      if (r.x < 4 || r.y < 44 || r.x + w > W - 4 || r.y + h > H - 4 || clash(r)) continue;
      pick = [dx, dy, r]; break;
    }
    if (!pick) { el.remove(); return; }                  // 놓을 자리가 없으면 라벨을 빼고 커서 정보로 본다
    const [dx, dy, r] = pick;
    placed.push(r);
    el.style.left = (xy[0] + dx) + 'px'; el.style.top = (xy[1] + dy) + 'px';
    if (dx || dy) {
      gk.append('line').attr('class', 'lead').attr('x1', xy[0]).attr('y1', xy[1]).attr('x2', xy[0] + dx).attr('y2', xy[1] + dy);
      gk.append('circle').attr('class', 'anc').attr('r', 2.4).attr('cx', xy[0]).attr('cy', xy[1]);
    }
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
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json", {integrity: "sha384-yOCJ+8ShBm8UDqtAVtAvxTDDf4gXo5edxl/YG0FmVC5OTmqVLl7utuVGBDEeZWHf"}).then(r => r.json()).then(t => {
  world = topojson.feature(t, t.objects.countries); resolve();
  document.getElementById('msg').remove();
  if (layout()) paint();
}).catch(() => { document.getElementById('msg').textContent = '세계지도를 불러오지 못했습니다(인터넷 연결 확인)'; });
</script></body></html>
"""


def country_map(imp: dict, exp: dict, modes: tuple[str, ...] = ("imp", "exp"), height: int = 400,
                unit: str = "백만 USD", top_n: int = 6, note: str = "", where: dict | None = None) -> None:
    """국가별 수입·수출 분포(단계 구분도). 색 = 합계 대비 비중 구간, 상위 top_n 개국은 이름·비중 라벨.
    modes 가 하나면 전환 단추를 숨긴다."""
    # where = 국가명 → (위도, 경도)(ref_country). 나라 면은 JS 가 좌표를 품은 면(d3.geoContains)으로 찾는다
    info = {n: [None, la, lo, 0, 0] for n, (la, lo) in (where or {}).items() if (n in imp or n in exp) and la is not None}
    html = (_WORLD_MAP.replace("__DATA__", _js({"imp": imp, "exp": exp}))
            .replace("__INFO__", _js(info))
            .replace("__MODES__", _js(list(modes))).replace("__UNIT__", unit)
            .replace("__TOPN__", str(top_n)).replace("__NOTE__", escape(note))
            .replace("__H__", str(height - 10)).replace("__FONTLINK__", _FONT_LINK))
    components.html(html, height=height, scrolling=False)





INFO_CSS = """<style>
/* ⓘ 데이터 정보 단추 · 대화상자(데모 배치 · 평면) */
.st-key-info_btn{width:auto!important;padding:4px 20px 16px}
.st-key-info_btn [data-testid="stTooltipHoverTarget"]{justify-content:flex-start!important}
[data-testid="stSidebarUserContent"]{padding-bottom:14px!important}
.st-key-info_btn button{width:26px;height:26px;min-width:26px;min-height:0;padding:0;border-radius:50%;border:1px solid rgba(255,255,255,.35);
  display:flex;align-items:center;justify-content:center;background:transparent}
.st-key-info_btn button:hover{background:rgba(255,255,255,.12)}
.st-key-info_btn button > *{margin:0!important;gap:0!important;justify-content:center}
.st-key-info_btn button [data-testid="stMarkdownContainer"]{display:none}
.st-key-info_btn button [data-testid="stIconMaterial"]{color:#dbe7fb;font-size:18px;margin:0!important;line-height:1}
[data-testid="stDialog"] [role="dialog"]{border-radius:12px;background:#f6f9fd}
[data-testid="stDialog"] h2{font-size:23.5px!important;font-weight:700!important;letter-spacing:-.5px;color:var(--text)}
.di-lead{font-size:14.5px;color:#44567a;line-height:1.65;margin:-4px 0 12px}
.di-card{display:flex;gap:14px;padding:13px 15px;margin-bottom:10px;border:1px solid var(--line);border-radius:10px;background:#fff}
.di-ic{display:none}
.di-card > div:last-child{flex:1;min-width:0}
.di-t{font-size:14px;font-weight:600;color:var(--muted);margin-bottom:5px}
.di-big{font-size:17px;font-weight:600;color:var(--text);line-height:1.45;letter-spacing:-.3px}
.di-s{font-size:13.5px;color:var(--muted);line-height:1.55;margin-top:2px}
.di-chip{display:inline-block;margin-top:7px;padding:3px 10px;border-radius:6px;background:var(--sky-weak);font-size:13.5px;color:#0f2a5c;font-weight:500}
.di-chip b{font-weight:700;margin-left:6px}
.di-kv{display:grid;grid-template-columns:62px 1fr;gap:4px 10px;font-size:14px;color:#44567a;line-height:1.5}
.di-kv b{color:var(--text);font-weight:600}
.di-card.warn{border-left:3px solid var(--accent)}
.di-card.warn .di-t{color:var(--accent)}
.di-warn{margin:0!important;padding:0!important;list-style:none;counter-reset:w}
.di-warn li{counter-increment:w;position:relative;padding-left:24px;font-size:14px;color:var(--text);line-height:1.55;margin-bottom:5px}
.di-warn li::before{content:counter(w);position:absolute;left:0;top:2px;width:17px;height:17px;border-radius:50%;background:var(--sky-weak);
  color:var(--accent);font-size:12px;font-weight:700;display:grid;place-items:center}
</style>"""


def sidebar(pages: list, current: object, foot: str, on_info=None) -> None:
    """데모 사이드바 — 브랜드 · 메뉴 · 아래 글 · ⓘ(데이터 정보). pages = [(st.Page, 라벨, 아이콘)] — 아이콘은 단색 Material 이름."""
    with st.sidebar:
        with st.container(key="sidebrand"):
            st.html('<div class="sb-brand"><b>방산 전자부품</b><small>수출입 및 국산화 현황 대시보드</small></div>')
        with st.container(key="sidenav"):
            for page, label, icon in pages:
                # 현재 페이지도 같은 st.page_link 로 그린다 — 아이콘 크기 · 글자 위치가 그대로라 눌러도 흔들리지 않고,
                # 아이콘 이름 글자(inventory_2 등)가 글꼴 도착 전에 크게 보이는 일도 없다. 표시는 감싼 컨테이너 키로 색만 바꾼다.
                if page is current:
                    with st.container(key="nav_cur"):
                        st.page_link(page, label=label, icon=f":material/{icon}:", width="stretch")
                else:
                    st.page_link(page, label=label, icon=f":material/{icon}:", width="stretch")
        with st.container(key="sidefoot"):
            st.html(foot)
        if on_info:
            info_button("info_btn", on_info)


def mini_rail(pages: list, current: object, on_info=None) -> None:
    """(호환용) 데모의 접힘 미니 레일은 쓰지 않는다 — 사이드바는 Streamlit 기본 접기 단추로 여닫는다."""
    return None


def info_button(key: str, on_info) -> None:
    if st.button("", icon=":material/info:", key=key, help="데이터 정보"):
        on_info()


# ── 보이는 차트 그대로 PNG 로 내려받기 ─────────────────────────────────────────
# 서버에 이미지 엔진(kaleido·Chrome)이 없어도 되게 브라우저에서 만든다: 지금 그린 그림(fig)을 JSON 으로 싣고,
# 단추를 누르면 plotly.js 가 보이지 않는 칸에 같은 그림을 다시 그려 PNG 로 저장한다. 조건·차트 유형이 바뀌면
# 페이지가 다시 돌며 새 fig 가 실리므로 늘 화면과 같은 그림이 내려받아진다.
_PNG_BTN = r"""<!DOCTYPE html><html><head><meta charset="utf-8">__FONTLINK__
<style>body{margin:0;background:transparent;font-family:Pretendard,'Malgun Gothic',system-ui,sans-serif;display:flex;justify-content:__ALIGN__}
button{font:600 14px Pretendard,'Malgun Gothic',system-ui,sans-serif;color:#1d4ed8;background:#fff;border:1px solid #c7d7f2;
  border-radius:8px;padding:7px 14px;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
button:hover{border-color:#1d4ed8} button:disabled{opacity:.5;cursor:wait}
#hid{position:absolute;left:-10000px;top:0;width:__W__px;height:__HGT__px}</style></head><body>
<button id="b" title="지금 화면에 보이는 그래프를 PNG 로 저장">__LABEL__</button><div id="hid"></div>
<script>
const FIG = __FIG__;
// plotly.js(약 3.5MB)는 단추를 처음 누를 때만 받는다 — 페이지를 열 때 단추마다 받으면 화면이 한동안 멈춘다
function loadPlotly() {
  if (window.Plotly) return Promise.resolve();
  return new Promise((ok, fail) => {
    const sc = document.createElement('script');
    sc.src = 'https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js';
    sc.integrity = 'sha384-cCVCZkAjYNxaYKbM8lsArLznDF/SvMFr1jcZrvOpSTCa0W40ZAdLzHCEulnUa5i7'; sc.crossOrigin = 'anonymous';
    sc.onload = ok; sc.onerror = fail; document.head.appendChild(sc);
  });
}
document.getElementById('b').onclick = async () => {
  const b = document.getElementById('b'); b.disabled = true;
  try {
    try { await loadPlotly(); } catch (e) { b.textContent = '그래프 도구를 불러오지 못했습니다(인터넷 연결 확인)'; return; }
    const lay = Object.assign({}, FIG.layout || {}, {paper_bgcolor: '#ffffff', plot_bgcolor: '#ffffff', width: __W__, height: __HGT__});
    await Plotly.newPlot('hid', FIG.data, lay, {staticPlot: true});
    await Plotly.downloadImage('hid', {format: 'png', filename: "__FILE__", width: __W__, height: __HGT__, scale: 2});
  } finally { b.disabled = false; }
};
</script></body></html>"""


def _plotly_rich(text: str) -> str:
    """화면 제목 HTML → plotly 제목 문법. 결론형 제목의 강조 구절 <span class="key"> 만 파랑으로 살리고 나머지 태그는 지운다."""
    import re
    t = re.sub(r'<span class="key">(.*?)</span>', lambda m: f'<span style="color:{ACCENT}">{m.group(1)}</span>', text)
    return re.sub(r"<(?!/?span|br)[^>]+>", "", t)


def png_button(fig, filename: str, label: str = "PNG 이미지 내려받기", width: int = 1100, align: str = "flex-end",
               title: str | None = None, source: str | None = None) -> None:
    """지금 화면의 plotly 그림(fig)을 PNG 로 내려받는 단추(Datawrapper 내보내기 모양).
    title = 화면의 결론형 제목(HTML 가능, 강조 구절은 파랑), source = 아래 출처 한 줄 — 둘 다 이미지에만 들어가고 화면 그림은 그대로다."""
    out = go.Figure(fig)
    h = int(out.layout.height or 420)
    m = out.layout.margin
    top, bottom = (m.t or 10), (m.b or 8)
    if title:
        out.update_layout(title=dict(text=f"<b>{_plotly_rich(title)}</b>", x=0.01, xanchor="left", y=0.98, yanchor="top",
                                     font=dict(size=18, color=TEXT)))
        top += 56
    if source:
        source = "출처: " + public_source(source)
        out.add_annotation(text=_plotly_rich(source), xref="paper", yref="paper", x=0, y=0, xanchor="left", yanchor="top",
                           yshift=-bottom - 18, showarrow=False, align="left", font=dict(size=12.5, color=MUTED))
        bottom += 34
    out.update_layout(margin=dict(t=top, b=bottom, l=m.l, r=m.r), height=h + (top - (m.t or 10)) + (bottom - (m.b or 8)))
    h = int(out.layout.height)
    html = (_PNG_BTN.replace("__FIG__", out.to_json()).replace("__FILE__", escape(filename).replace('"', ""))
            .replace("__LABEL__", escape(label)).replace("__W__", str(width)).replace("__HGT__", str(h))
            .replace("__ALIGN__", align).replace("__FONTLINK__", _FONT_LINK))
    components.html(html, height=42, scrolling=False)


def inject() -> None:
    """데모의 CSS 층을 순서대로 넣는다(데모 파일 맨 위에서 st.html 로 넣던 것들)."""
    st.html(CSS)
    st.html(WIDGET_CSS)
    if CHART_ANIM:
        st.html(CHART_ANIM)
    st.html(TABLE_CSS)
    st.html(INFO_CSS)
