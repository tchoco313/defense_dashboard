"""화면 틀 — 동현님 새 디자인(dashboard/demo/K-Defense_brandnew.py, 2026-09-28)의 국방과학연구소(add.re.kr/kps) 방식.

흰 머리글(로고 · 자료 기간 · ⓘ) → 상단 메뉴(커서를 올리면 모든 페이지의 블록 목록이 짙은 파랑 띠로 펼쳐짐 · 돋보기 · 전체 메뉴)
→ 서브 배너(항공모함 · K9 자주포 사진, 제목 · 부제) → 왼쪽 메뉴(이 페이지의 블록 · 스크롤을 따라옴) + 본문 → 빠른 메뉴 · 바닥글.
홈을 ?sec= 없이 열면 서브 배너 · 왼쪽 메뉴 없이 첫 화면(landing.py)만 그린다.

- 블록은 주소의 ?sec= 로 고른다(예: /import?sec=trend). 페이지의 블록은 모두 그리고, 고른 블록으로 스크롤한다.
- 배너 제목 · 부제 · 메뉴 이름은 nav.py, 블록 목록은 페이지 파일의 zone() 호출(nav.sections)에서 온다.
- 화면 숫자는 이 모듈에 없다. 머리글의 자료 기간만 main.py 가 RDS 에서 읽어 넘긴다(DB 표 이름 · 적재일은 쓰지 않는다).
"""
from __future__ import annotations

import base64
import math
from collections.abc import Callable
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from nav import GNB_ORDER, NAV_ORDER, SPEC_BY_KEY, sections

WRAP = 1400                    # 본문 최대 폭(px) — 머리글 · 배너 · 바닥글 배경은 화면 끝까지, 내용은 이 폭 안에
LNB_W = 230                    # 왼쪽 메뉴 폭 = 서브 배너의 제목 칸 폭
BLUE, BLUE_D = "#1d4ed8", "#003899"   # 강조 파랑 · 짙은 파랑(제목 칸 · 펼침 메뉴)
PAD = f"max(32px, calc((100% - {WRAP}px) / 2 + 32px))"   # 줄마다 안쪽 여백 — 내용을 가운데 WRAP 폭 안으로
QUICK = (("search", "조회", "search"), ("table", "검토 목록", "table_chart"), ("info", "DATA INFO", "folder_open"))
LABEL_KEY = "_kd_label"        # 경로 표시(⌂ › 페이지)에 쓰는 현재 페이지 이름 — kdesign.hero 가 읽는다

# 태극 — 위 빨강(#CD2E3A) · 아래 파랑(#0047A0). st.html 은 <svg> 를 지우므로 그림(data URI)으로 넣는다
_TG_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-11 -11 22 22">'
           '<circle r="10" fill="#0047A0"/>'
           '<path d="M-10 0A10 10 0 0 1 10 0A5 5 0 0 0 0 0A5 5 0 0 1-10 0Z" fill="#CD2E3A"/>'
           '<circle r="10" fill="none" stroke="#fff" stroke-width="1.6"/></svg>')
TAEGEUK = f'<img class="tg" alt="" src="data:image/svg+xml;base64,{base64.b64encode(_TG_SVG.encode()).decode()}">'
# 배너 사진 — 항공모함(Unsplash · 무료, 브라우저가 직접 받음) · K9 자주포(흑백 840×473, 저장소 파일)
SV_SHIP = "https://images.unsplash.com/photo-1685178362030-9b574eb9ae7c?auto=format&fit=crop&w=1400&q=80"
SV_K9 = "data:image/jpeg;base64," + base64.b64encode(
    (Path(__file__).resolve().parent / "assets" / "k9_banner.jpg").read_bytes()).decode()


def _drop_h() -> int:
    """펼침 메뉴 높이 — 블록이 가장 많은 메뉴 기준. 한 줄 약 40px, 칸(약 14자)보다 긴 이름은 줄마다 20px 더."""
    return max(sum(40 + 20 * (math.ceil(len(t) / 14) - 1) for _, t in sections(k)) for k in GNB_ORDER) + 34


def _css(drop: int) -> str:
    return f"""<style>
/* ── 틀: 사이드바 없음 · 흰 바탕 · 본문 폭 제한 없음(줄마다 안쪽 여백으로 가운데 맞춤) ───────────── */
[data-testid="stSidebar"],[data-testid="stExpandSidebarButton"],[data-testid="stSidebarCollapseButton"]{{display:none!important}}
/* Streamlit 기본 머리 띠(보이지 않는 도구 막대)가 로고 · ⓘ 위를 덮어 클릭을 가로챈다 — 사이드바가 없으니 통째로 숨긴다 */
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"]{{display:none!important}}
html,body,[data-testid="stAppViewContainer"]{{background:#fff}}
.block-container{{padding:0!important;max-width:none!important}}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]{{gap:0}}

/* ── 머리글 1줄: 로고 · 자료 기간 · ⓘ ───────────────────────────────── */
.st-key-hdr_top{{padding:0 {PAD};height:78px!important;min-height:78px;align-items:center!important;border-bottom:1px solid #e3e8f0;
  background:#fff;position:relative}}
[data-testid="stLayoutWrapper"]:has(> .st-key-brand_link){{position:absolute!important;left:{PAD};top:0;width:min(420px, calc(100vw - 110px));height:78px;z-index:3;margin:0}}
.st-key-brand_link,.st-key-brand_link [data-testid="stElementContainer"],.st-key-brand_link [data-testid="stPageLink"]{{width:100%!important;height:78px}}
.st-key-brand_link [data-testid="stPageLink"] a{{display:block;width:100%;height:78px;padding:0;margin:0;opacity:0;cursor:pointer}}
.brand{{display:flex;align-items:center;gap:12px}}
.brand .mark{{position:relative;display:inline-grid;place-items:center;line-height:0}}
.brand .mark .tg{{position:absolute;left:50%;top:46%;width:15px;height:15px;transform:translate(calc(-50% + 0.3px),-50%) rotate(40deg);pointer-events:none}}
.brand .ms{{font-family:'Material Symbols Rounded'!important;font-size:38px;line-height:1;color:{BLUE_D};
  font-variation-settings:'FILL' 1;font-feature-settings:'liga'}}
.brand b{{display:block;font-size:23px;font-weight:800;letter-spacing:-.6px;color:#0b1f4d;line-height:1.1}}
.brand small{{display:block;font-size:12px;font-weight:600;color:#5b6b88;letter-spacing:-.1px;margin-top:3px}}
.util{{font-size:13px;color:#6b7a99;display:flex;align-items:center;gap:10px;white-space:nowrap}}
.util b{{color:#1b2540;font-weight:700}}
.util i{{font-style:normal;color:#cbd3e1}}
.st-key-hdr_util{{gap:14px;flex-wrap:nowrap!important}}
.st-key-hdr_util > div,.st-key-hdr_util [data-testid="stElementContainer"]{{width:auto!important;flex:0 0 auto!important}}

/* ── 머리글 2줄: 상단 메뉴(GNB) ─────────────────────────────────────── */
.st-key-gnb{{padding:0 {PAD};height:66px!important;background:#fff;border-bottom:1px solid #e3e8f0;position:relative;z-index:50;
  flex-wrap:nowrap!important;align-items:stretch!important;gap:0!important}}
.st-key-gnb > div{{height:100%}}
div[class*="st-key-gi_"]{{position:relative;height:66px;justify-content:center;flex:1 1 0!important;min-width:0}}
div[class*="st-key-gi_"] > div:first-child,div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"],
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] > div{{width:100%!important;max-width:none!important}}
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a{{width:100%}}
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a,.gnb-on{{display:flex;justify-content:center;align-items:center;
  box-sizing:border-box;height:66px;padding:8px 6px 0!important;margin:0;border-radius:0;background:transparent!important;position:relative}}
div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a p,.gnb-on{{font-size:18px!important;font-weight:700;color:#141c2e!important;
  letter-spacing:-.5px;white-space:nowrap;transition:color .15s}}
.gnb-on,div[class*="st-key-gi_"]:hover > div:first-child [data-testid="stPageLink"] a p{{color:{BLUE}!important}}
/* 펼침 메뉴 — 상단 메뉴 어디에 커서를 올려도 모든 메뉴의 블록 목록이 한꺼번에 짙은 파랑 띠에 펼쳐진다 */
div[class*="st-key-gs_"]{{display:none!important;position:absolute;top:66px;left:0;right:0;padding:14px 6px 0;gap:0!important;z-index:3;
  height:{drop}px;box-sizing:border-box;border-left:1px solid rgba(255,255,255,.2)}}
.st-key-gs_info{{border-right:1px solid rgba(255,255,255,.2)}}
.st-key-gnb:hover div[class*="st-key-gs_"]{{display:flex!important}}
.st-key-gnb::after{{content:"";position:absolute;left:0;right:0;top:66px;height:{drop}px;background:{BLUE_D};
  box-shadow:0 12px 24px rgba(0,30,90,.25);opacity:0;visibility:hidden;transition:opacity .15s;z-index:1}}
.st-key-gnb:hover::after{{opacity:1;visibility:visible}}
.st-key-gnb:hover{{height:{66 + drop}px!important;padding-bottom:{drop}px;margin-bottom:-{drop}px;box-sizing:border-box}}   /* 펼친 띠까지 커서가 머무는 자리로 */
div[class*="st-key-gs_"] [data-testid="stPageLink"] a{{padding:10px 8px;margin:0;border-radius:4px;background:transparent}}
div[class*="st-key-gs_"] > div{{flex-shrink:0!important;margin:0!important}}
div[class*="st-key-gs_"] [data-testid="stPageLink"] a p{{font-size:15px!important;font-weight:500;color:#c9d8f5!important;
  white-space:normal;line-height:1.35!important;word-break:keep-all}}   /* 칸보다 긴 이름은 잘리지 않고 두 줄로 */
div[class*="st-key-gs_"] [data-testid="stPageLink"] a:hover{{background:rgba(255,255,255,.1)}}
div[class*="st-key-gs_"] [data-testid="stPageLink"] a:hover p{{color:#fff!important}}
div[class*="st-key-gi_"]:hover div[class*="st-key-gs_"]{{background:rgba(255,255,255,.06)}}
/* 돋보기(조회) · 전체 메뉴(≡) */
.st-key-gnb_search{{width:66px!important;flex:0 0 66px!important;justify-content:center}}
.st-key-gnb_search [data-testid="stPageLink"] a{{height:66px;justify-content:center;background:transparent!important}}
.st-key-gnb_search [data-testid="stPageLink"] a p{{display:none}}
.st-key-gnb_search [data-testid="stIconMaterial"]{{font-size:27px!important;color:#141c2e;margin:0!important}}
.st-key-gnb_search [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"],.st-key-gnb_search.on [data-testid="stIconMaterial"]{{color:{BLUE}}}
.st-key-gnb_all{{width:66px!important;flex:0 0 66px!important}}
.st-key-gnb_all button{{width:66px;height:66px;min-height:0;border:none;border-radius:0;background:{BLUE_D};padding:0}}
.st-key-gnb_all button:hover{{background:{BLUE}}}
.st-key-gnb_all button p{{display:none}}
.st-key-gnb_all button [data-testid="stIconMaterial"]{{color:#fff;font-size:28px!important;margin:0!important}}
.st-key-gnb_all button > div > div:last-child{{display:none}}     /* 펼침 화살표 */
.st-key-gnb_all button *{{color:#fff}}
.sm-h{{font-size:15px;font-weight:800;color:{BLUE_D};padding:0 0 8px;margin-bottom:6px;border-bottom:2px solid {BLUE_D};white-space:nowrap}}
.st-key-sitemap [data-testid="stPageLink"] a{{padding:3px 0;background:transparent}}
.st-key-sitemap [data-testid="stPageLink"] a p{{font-size:13px;color:#44567a;white-space:normal;word-break:keep-all;line-height:1.4}}
.st-key-sitemap [data-testid="stPageLink"] a:hover p{{color:{BLUE}}}

/* ── 서브 배너 — 짙은 파랑 바탕 + 항공모함 · K9 자주포 사진, 왼쪽 아래에 페이지 제목 칸 ─────────────── */
.sv{{position:relative;overflow:hidden;height:168px;padding:0 {PAD};
  background:linear-gradient(100deg,#00236b 0%,{BLUE_D} 38%,{BLUE_D} 100%)}}
.sv-ph{{position:absolute;top:0;bottom:0;right:max(0px, calc((100% - {WRAP}px) / 2));width:811px;pointer-events:none}}
.sv-ph i{{position:absolute;top:0;bottom:0;background-repeat:no-repeat}}
.sv-ph .ship{{left:110px;width:53.6%;background-size:cover;background-position:center 62%;mix-blend-mode:luminosity;opacity:.5;
  -webkit-mask-image:linear-gradient(90deg,transparent 0,#000 25%,#000 50%,transparent 100%);
  mask-image:linear-gradient(90deg,transparent 0,#000 25%,#000 50%,transparent 100%)}}
.sv-ph .k9{{right:0;width:46.4%;background-size:90% auto;background-position:30% calc(68% - 3px);mix-blend-mode:luminosity;opacity:.4;
  transform:translateX(-40px);
  -webkit-mask-image:linear-gradient(90deg,transparent 4%,#000 24%,#000 62%,transparent 92%);
  mask-image:linear-gradient(90deg,transparent 4%,#000 24%,#000 62%,transparent 92%)}}
.sv-in{{position:relative;height:100%;display:flex;align-items:flex-end}}
.sv-sp{{width:{LNB_W}px;flex:0 0 {LNB_W}px}}
.sv-title{{align-self:center;padding:0 0 0 44px;color:#fff;max-width:760px}}
.sv-title h1{{margin:0;padding:0;font-size:31px;font-weight:800;letter-spacing:-.8px;color:#fff;line-height:1.2}}
.sv-title p{{margin:8px 0 0;font-size:13.5px;color:#c7d7f6;letter-spacing:-.1px;line-height:1.5}}
.sv-slogan{{position:absolute;right:max(32px, calc((100% - {WRAP}px) / 2 + 32px));top:50%;transform:translateY(-50%);text-align:right;
  font-size:17px;font-weight:800;color:#fff;letter-spacing:-.4px;line-height:1.4;opacity:.92}}
@media (max-width:1100px){{.sv-slogan{{display:none}}}}
.sv-box{{width:{LNB_W}px;height:112px;flex:0 0 {LNB_W}px;display:flex;flex-direction:column;justify-content:center;align-items:center;
  background:#fff;color:{BLUE_D};border-top:4px solid {BLUE};box-shadow:0 -6px 18px rgba(0,20,70,.18)}}
.sv-box small{{font-size:11px;font-weight:700;letter-spacing:2px;color:#7b8fb5;margin-bottom:6px}}
.sv-box b{{font-size:21px;font-weight:800;letter-spacing:-.6px;text-align:center;line-height:1.25;padding:0 10px;word-break:keep-all}}

/* ── 본문 줄: 왼쪽 메뉴(LNB) + 오른쪽 본문 ───────────────────────────── */
/* 본문 줄을 제목 칸 높이(112px)만큼 배너 위로 끌어올린다 — 제목 칸이 배너 아래쪽에 걸치고, 본문은 같은 높이만큼 위 여백 */
.st-key-body{{padding:0 {PAD} 70px;gap:44px!important;flex-wrap:nowrap!important;align-items:flex-start!important;background:transparent;
  margin-top:-112px!important;position:relative;z-index:3}}
.st-key-lnb{{gap:6px!important;padding-top:0;position:relative;left:-41px}}
[data-testid="stLayoutWrapper"]:has(> .st-key-lnb){{position:sticky;top:24px;align-self:flex-start;z-index:5}}   /* 스크롤해도 화면 위쪽에 붙어 따라온다 */
.lnb-box{{margin-bottom:10px;border-radius:12px 12px 0 0}}
.st-key-lnb [data-testid="stPageLink"] a{{display:flex;align-items:center;justify-content:space-between;min-height:50px;
  padding:0 18px;margin:0;border-radius:0;background:#f3f6fb;position:relative;transition:background .15s}}
.st-key-lnb [data-testid="stPageLink"] a p{{font-size:15px!important;font-weight:700;color:#1b2540!important;letter-spacing:-.4px}}
.st-key-lnb [data-testid="stPageLink"] a::after{{content:"+";font-size:19px;font-weight:300;color:#9aa6bd;margin-left:8px}}
.st-key-lnb [data-testid="stPageLink"] a:hover{{background:#e8effb}}
.st-key-lnb [data-testid="stPageLink"] a:hover p{{color:{BLUE}!important}}
.lnb-nav{{display:flex;flex-direction:column;gap:6px}}
.lnb-nav a{{display:flex;align-items:center;justify-content:space-between;min-height:50px;padding:8px 18px;background:#f3f6fb;
  border:1.5px solid transparent;font-size:15px;font-weight:700;color:#1b2540;letter-spacing:-.4px;text-decoration:none;line-height:1.35;
  word-break:keep-all;transition:background .15s,border-color .15s,color .15s}}
.lnb-nav a::after{{content:"+";font-size:19px;font-weight:300;color:#9aa6bd;margin-left:8px}}
.lnb-nav a:hover{{background:#e8effb;color:{BLUE}}}
.lnb-nav a.on{{background:#fff;border-color:{BLUE_D};color:{BLUE_D}}}
.lnb-nav a.on::after{{content:"−";font-weight:400;color:{BLUE_D}}}
.lnb-help{{margin-top:18px;padding:16px 16px 15px;background:linear-gradient(135deg,{BLUE_D},{BLUE});color:#fff;border-radius:2px 2px 12px 12px}}
.lnb-help b{{display:block;font-size:14px;font-weight:800;margin-bottom:5px}}
.lnb-help span{{display:block;font-size:12px;color:#dbe6fa;line-height:1.65}}
.st-key-main{{min-width:0;gap:12px!important;padding-top:112px}}

/* ── 오른쪽 빠른 메뉴 ─────────────────────────────────────────────── */
.st-key-quick{{position:fixed;right:14px;top:50%;transform:translateY(-50%);z-index:60;width:74px!important;gap:0!important;
  background:#fff;border:1px solid #d9e2f0;border-radius:12px;box-shadow:0 8px 24px rgba(0,30,90,.14);overflow:hidden}}
[data-testid="stLayoutWrapper"]:has(> .st-key-quick){{position:fixed;width:0;height:0;margin:0}}
.st-key-quick [data-testid="stPageLink"] a{{flex-direction:column;gap:4px!important;padding:12px 4px;margin:0;border-radius:0;
  border-bottom:1px solid #eef2f8;background:#fff;align-items:center!important;justify-content:center!important;height:auto!important;width:100%}}
.st-key-quick [data-testid="stPageLink"] a > span{{width:100%!important;height:auto!important;justify-content:center!important;
  display:flex!important;overflow:visible!important}}
.st-key-quick [data-testid="stElementContainer"],.st-key-quick [data-testid="stPageLink"]{{width:100%!important}}
.st-key-quick [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{{font-size:24px!important;color:{BLUE};margin:0!important}}
.st-key-quick [data-testid="stPageLink"] a p{{font-size:11px!important;font-weight:700;color:#33415c;text-align:center;white-space:nowrap}}
.st-key-quick [data-testid="stPageLink"] a:hover{{background:{BLUE_D}}}
.st-key-quick [data-testid="stPageLink"] a:hover p,.st-key-quick [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"]{{color:#fff!important}}
.qk-h{{background:{BLUE_D};color:#fff;font-size:10.5px;font-weight:800;letter-spacing:1px;text-align:center;padding:7px 0}}
@media (max-width:1500px){{.st-key-quick{{display:none!important}}}}
.st-key-kdjs,[data-testid="stLayoutWrapper"]:has(> .st-key-kdjs){{display:none!important}}

/* ── 바닥글 ─────────────────────────────────────────────────────── */
.ft{{background:#1f2633;padding:30px {PAD} 34px;display:flex;gap:44px;align-items:flex-start;color:#9aa4b8}}
.ft .brand .ms{{color:#8ea4cf;font-size:34px}}
.ft .brand .mark .tg{{width:13.5px;height:13.5px}}
.ft .brand b{{color:#dfe5ef;font-size:20px}}
.ft .brand small{{color:#8591a6}}
.ft-mid{{flex:1;font-size:12.5px;line-height:1.95}}
.ft-mid b{{color:#c9d1de;font-weight:600}}
.ft details{{width:230px;background:#151a24;border:1px solid #2f3848;font-size:12.5px}}
.ft summary{{padding:11px 14px;cursor:pointer;color:#c9d1de;list-style:none;display:flex;justify-content:space-between}}
.ft summary::after{{content:"▲";font-size:9px;color:#8591a6}}
.ft details[open] summary::after{{content:"▼"}}
.ft details a{{display:block;padding:7px 14px;color:#9aa4b8;text-decoration:none;border-top:1px solid #262e3c}}
.ft details a:hover{{color:#fff;background:#262e3c}}

/* ── 노트북 폭 — 왼쪽 메뉴를 제자리에 두고(화면 밖으로 밀리지 않게), 상단 메뉴 이름은 작게 · 두 줄까지 ───────── */
@media (max-width:1480px){{.st-key-lnb{{left:0}}}}
@media (max-width:1200px){{
  div[class*="st-key-gi_"] > div:first-child [data-testid="stPageLink"] a p,.gnb-on{{font-size:15.5px!important;white-space:normal!important;
    text-align:center;line-height:1.25!important;word-break:keep-all}}
}}
/* ── 좁은 화면 — 상단 메뉴 항목은 숨기고 돋보기 · 전체 메뉴(≡)로 옮겨 다닌다, 왼쪽 메뉴는 본문 위로 쌓는다 ─────── */
@media (max-width:900px){{
  .st-key-hdr_util .util{{display:none}}
  div[class*="st-key-gi_"]{{display:none!important}}
  .st-key-gnb{{justify-content:flex-end!important}}
  .st-key-sitemap{{flex-wrap:wrap!important}}
  .st-key-gnb:hover div[class*="st-key-gs_"],.st-key-gnb:hover::after{{display:none!important}}
  .st-key-gnb:hover{{height:66px!important;padding-bottom:0;margin-bottom:0}}
  .st-key-body{{flex-direction:column!important;flex-wrap:wrap!important;gap:16px!important}}
  .st-key-lnb{{left:0;width:100%!important}}
  [data-testid="stLayoutWrapper"]:has(> .st-key-lnb){{position:relative;top:0;width:100%}}
  .sv-box,.lnb-help{{display:none}}
  .st-key-main{{padding-top:0}}
  .st-key-body{{margin-top:0!important;padding-top:16px}}
  .sv-title{{padding-left:0}} .sv-sp{{display:none}}
  .ft{{flex-wrap:wrap;gap:20px}} .ft details{{width:100%}}
}}
</style>"""


def header(pages: dict, cur: str, period: str, on_info: Callable[[], None] | None) -> None:
    """흰 머리글(로고 · 관세청 자료 기간 · ⓘ) + 상단 메뉴(펼침 블록 · 조회 돋보기 · 전체 메뉴)."""
    st.html(_css(_drop_h()))
    with st.container(key="hdr_top", horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
        st.html(f'<div class="brand"><span class="mark"><span class="ms">shield</span>{TAEGEUK}</span><div><b>K-Defense</b>'
                '<small>주요 방산 전자부품 수출입 및 국산화 현황 대시보드</small></div></div>')
        with st.container(key="hdr_util", horizontal=True, width="content", vertical_alignment="center"):
            st.html(f'<div class="util"><span>관세청 자료 <b>{escape(period)}</b></span><i>|</i><span>데이터 정보</span></div>')
            if on_info:
                if st.button("", icon=":material/info:", key="info_btn", help="데이터 정보"):
                    on_info()
        with st.container(key="brand_link"):   # 로고 위 투명 링크 — 누르면 홈 첫 화면
            st.page_link(pages["home"], label="K-Defense 홈", query_params={"sec": "main"})

    with st.container(key="gnb", horizontal=True, vertical_alignment="center"):
        for k in GNB_ORDER:
            label = SPEC_BY_KEY[k].label
            with st.container(key=f"gi_{k}", width="stretch"):
                if k == cur:
                    st.html(f'<div class="gnb-on">{escape(label)}</div>')
                else:
                    st.page_link(pages[k], label=label)
                with st.container(key=f"gs_{k}"):
                    for s, t in sections(k):
                        st.page_link(pages[k], label=t, query_params={"sec": s})
        with st.container(key="gnb_search", width="content"):
            st.page_link(pages["search"], label="조회", icon=":material/search:")
        with st.container(key="gnb_all", width="content"):
            with st.popover("전체 메뉴", icon=":material/menu:"):
                with st.container(key="sitemap", horizontal=True, gap="large"):
                    for k in NAV_ORDER:
                        with st.container(width=170):
                            st.html(f'<div class="sm-h">{escape(SPEC_BY_KEY[k].label)}</div>')
                            for s, t in sections(k):
                                st.page_link(pages[k], label=t, query_params={"sec": s})


def selected(cur: str) -> str | None:
    """주소의 ?sec= — 이 페이지의 블록 키일 때만 받는다(스크롤 스크립트에 들어가므로 목록 밖 값은 버린다)."""
    q = st.query_params.get("sec")
    return q if q in dict(sections(cur)) else None


def body(pages: dict, cur: str, sec: str | None):
    """서브 배너 + 본문 줄(왼쪽 메뉴 | 본문). 본문 컨테이너를 돌려준다 — main.py 가 그 안에서 pg.run()."""
    spec = SPEC_BY_KEY[cur]
    st.session_state[LABEL_KEY] = spec.label
    slogan = '<div class="sv-slogan">강한 국방,<br>데이터로 이어집니다.</div>' if cur == "home" else ""
    st.html(f'<div class="sv"><div class="sv-ph"><i class="ship" style="background-image:url({SV_SHIP})"></i>'
            f'<i class="k9" style="background-image:url({SV_K9})"></i></div>{slogan}'
            f'<div class="sv-in"><div class="sv-sp"></div>'
            f'<div class="sv-title"><h1>{spec.heading}</h1><p>{spec.lead}</p></div></div></div>')

    nav_secs = [(k, t) for k, t in sections(cur) if k != "main"]
    row = st.container(key="body", horizontal=True)
    with row:
        with st.container(key="lnb", width=LNB_W):
            st.html(f'<div class="sv-box lnb-box"><small>K-DEFENSE</small><b>{escape(spec.label)}</b></div>')
            if cur == "home":        # 첫 화면(Main)은 따로 된 화면이라 페이지 이동
                st.page_link(pages["home"], label="Main", query_params={"sec": "main"}, width="stretch")
            first = sec if sec in dict(nav_secs) else (nav_secs[0][0] if nav_secs else "")
            # 누르면 그 블록으로 부드럽게 이동, 스크롤하면 지금 보이는 블록이 선택 표시(아래 _SCROLL_JS)
            st.html('<nav class="lnb-nav">' + "".join(
                f'<a href="?sec={k}" data-sec="{k}" class="{"on" if k == first else ""}">{escape(t)}</a>'
                for k, t in nav_secs) + '</nav>')
            st.html('<div class="lnb-help"><b>읽는 법</b><span>수입액은 국가 전체 수입(민수 포함)이며, 국가는 선적국 기준입니다. '
                    '관세청 수입액과 조달 예산은 합하거나 직접 비교하지 않습니다. 출처와 범위는 머리글의 ⓘ 에서 확인하세요.</span></div>')
        main = st.container(key="main")
    return main


def footer(pages: dict) -> None:
    """오른쪽 빠른 메뉴 · 짙은 바닥글."""
    with st.container(key="quick"):
        st.html('<div class="qk-h">QUICK</div>')
        for k, label, icon in QUICK:
            st.page_link(pages[k], label=label, icon=f":material/{icon}:")
    st.html('<div class="ft"><div class="brand"><span class="mark"><span class="ms">shield</span>' + TAEGEUK + '</span><div><b>K-Defense</b>'
            '<small>공개 자료로 확인하는 방산 전자부품 현황</small></div></div>'
            '<div class="ft-mid">자료: 관세청 품목별 국가별 수출입실적 · 방위사업청 국외 조달계획 · 국산화개발품목 · 국내 계약 · 입찰 · '
            'KOSIS 방산 가동률 · 생산지수 · 열린재정 세부사업 예산<br>'
            '수입액은 국가 전체 수입(민수 포함)이며 HS 코드만으로 군용 · 민수용을 구분할 수 없습니다 · '
            '<b>© 2026 K-Defense 팀 프로젝트</b> (K-디지털 트레이닝)</div>'
            '<details><summary>관련 사이트 바로가기</summary>'
            '<a href="https://unipass.customs.go.kr/ets/" target="_blank" rel="noopener">관세청 수출입무역통계</a>'
            '<a href="https://www.dapa.go.kr" target="_blank" rel="noopener">방위사업청</a>'
            '<a href="https://kosis.kr" target="_blank" rel="noopener">KOSIS 국가통계포털</a>'
            '<a href="https://www.openfiscaldata.go.kr" target="_blank" rel="noopener">열린재정</a>'
            '<a href="https://www.data.go.kr" target="_blank" rel="noopener">공공데이터포털</a></details></div>')


# ── 왼쪽 메뉴 ↔ 스크롤 연결 ─────────────────────────────────────────────────
# st.html 은 스크립트를 돌리지 않아, 보이지 않는 components.html 안에서 바깥 화면(window.parent)을 다룬다.
#  · 메뉴를 누르면 그 블록으로 부드럽게 이동   · 스크롤하면 지금 보이는 블록이 메뉴에서 선택 표시
#  · 페이지를 새로 열면 주소의 ?sec= 블록으로(없으면 맨 위로) 이동
# __NAV__ 에 주소를 넣어 페이지 · 블록이 바뀔 때만 새로 이동한다(같은 페이지에서 위젯을 만질 때는 그대로).
# 넣는 값은 페이지 키와 목록 안의 블록 키뿐이다(selected() 가 거른다) — 주소창 글자를 그대로 넣지 않는다.
_SCROLL_JS = r"""<script>
(function () {
  const P = window.parent, doc = P.document, NAV = "__NAV__", TARGET = "__SEC__";
  const main = () => doc.querySelector('[data-testid="stMain"]');
  const zones = () => [...doc.querySelectorAll('div[class*="st-key-zone_"]')];
  const keyOf = el => (el.className.match(/st-key-zone_(\S+)/) || [])[1];
  function mark(k) {
    doc.querySelectorAll('.lnb-nav a[data-sec]').forEach(a => a.classList.toggle('on', a.dataset.sec === k));
  }
  function go(k, smooth) {
    const el = doc.querySelector('.st-key-zone_' + k);
    if (!el) return false;
    const m = main(); if (!m) return false;
    P.__kdLock = Date.now() + (smooth ? 900 : 200);   // 이동하는 동안은 스크롤 표시를 멈춘다
    mark(k);
    const z = parseFloat(P.getComputedStyle(doc.documentElement).zoom) || 1;
    const d = (el.getBoundingClientRect().top - m.getBoundingClientRect().top) / z - 20;
    const to = Math.max(0, m.scrollTop + d);
    if (!smooth) { m.scrollTop = to; return true; }
    const from = m.scrollTop, dur = 450, t0 = P.performance.now(), id = (P.__kdAnim || 0) + 1;
    P.__kdAnim = id;
    const step = now => {
      if (P.__kdAnim !== id) return;
      const p = Math.min(1, (now - t0) / dur);
      m.scrollTop = from + (to - from) * (1 - Math.pow(1 - p, 3));
      if (p < 1) P.requestAnimationFrame(step);
    };
    P.requestAnimationFrame(step);
    P.setTimeout(() => { if (P.__kdAnim === id) m.scrollTop = to; }, dur + 150);
    return true;
  }
  function spy() {
    if (P.__kdLock && Date.now() < P.__kdLock) return;
    const m = main(), zs = zones().filter(z => doc.querySelector('.lnb-nav a[data-sec="' + keyOf(z) + '"]'));
    if (!m || !zs.length) return;
    const top = m.getBoundingClientRect().top + 140;
    let cur = zs[0];
    for (const z of zs) if (z.getBoundingClientRect().top <= top) cur = z;
    if (m.scrollTop + m.clientHeight >= m.scrollHeight - 4) cur = zs[zs.length - 1];   // 맨 아래면 마지막 블록
    mark(keyOf(cur));
  }
  if (P.__kdClick) doc.removeEventListener('click', P.__kdClick, true);
  P.__kdClick = e => {
    const a = e.target.closest && e.target.closest('.lnb-nav a[data-sec]');
    if (!a) return;
    e.preventDefault(); e.stopPropagation();
    go(a.dataset.sec, true);
  };
  doc.addEventListener('click', P.__kdClick, true);
  const bindScroll = () => {
    const m = main(); if (!m) return false;
    if (P.__kdScrollEl && P.__kdScroll) P.__kdScrollEl.removeEventListener('scroll', P.__kdScroll);
    P.__kdScroll = () => spy();
    P.__kdScrollEl = m;
    m.addEventListener('scroll', P.__kdScroll, {passive: true});
    return true;
  };
  if (P.__kdNav !== NAV) {
    P.__kdNav = NAV;
    let n = 0;
    const t = P.setInterval(() => {
      n++;
      bindScroll();
      if (TARGET && TARGET !== "main") { if (go(TARGET, false) || n > 40) P.clearInterval(t); }
      else { const m = main(); if (m) m.scrollTop = 0; P.clearInterval(t); }
    }, 150);
  } else {
    bindScroll();
  }
})();
</script>"""


def scroll_js(cur: str, sec: str | None) -> None:
    with st.container(key="kdjs"):
        components.html(_SCROLL_JS.replace("__NAV__", f"{cur}|{sec or ''}").replace("__SEC__", sec or ""), height=0)
