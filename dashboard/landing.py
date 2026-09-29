"""홈 첫 화면(Main) — 동현님 새 디자인(dashboard/demo/K-Defense_brandnew.py main_landing)의 배치에 값만 RDS 로.

큰 사진(자동 전환) · 소개와 둥근 바로가기 · 주요 분석 사진 카드 · 숫자 띠 · 데이터 기준 시점 · 이용 안내.
main.py 가 홈을 ?sec= 없이(또는 ?sec=main) 열 때 서브 배너 · 왼쪽 메뉴 없이 화면 전체 폭으로 그린다.
- 숫자 띠 = 관세청 품목별 국가별 수출입실적의 최근 완결 연도(부분연도 제외) · 분석 대상 품목군(priority 1·2) 합계.
  1위 공급국 점유율 50% 이상 품목군 수는 metrics.concentration(홈 · ④ · 조회와 같은 산식) — 홈 KPI 「기준 연도」 값과 같아야 한다.
- 데이터 기준 시점 = db.data_stamp 의 자료 기간만(DB 적재일 · 표 이름은 쓰지 않는다 — 보안, 2026-09-24).
- 사진은 Unsplash(무료) 주소를 브라우저가 직접 받는다. 조회 실패 · 미적재는 숫자 대신 「—」와 사유를 쓴다.
"""
from __future__ import annotations

from html import escape

import streamlit as st

from db import data_stamp, try_query
from frame import PAD
from kdesign import stamp_period
from metrics import concentration
from nav import SPEC_BY_KEY


def _ph(pid: str, w: int = 1600) -> str:
    return f"https://images.unsplash.com/photo-{pid}?auto=format&fit=crop&w={w}&q=70"


SLIDES = [_ph("1551796880-ddd03f861ae7", 2000),    # 푸른 하늘의 전투기
          _ph("1685178362030-9b574eb9ae7c", 2000),  # 항공모함
          _ph("1610457642191-05328cdf34ff", 2000)]  # 밤하늘 레이더
CARDS = [  # (페이지 키, 블록, 사진, 분류) — 제목 · 설명은 nav.py 의 메뉴 이름 · 배너 부제
    ("trade", "kpi2", _ph("1578575437130-527eed3abbec", 900), "TRADE"),
    ("background", "bkpi", _ph("1676090438227-141cac59c405", 900), "BUDGET"),
    ("parts", "kpi3", _ph("1592659762303-90081d34b277", 900), "PARTS"),
    ("table", "tbl", _ph("1714255288526-cc155b548aac", 900), "REVIEW"),
]
LINKS = [("trade", "public"), ("parts", "memory"), ("table", "table_chart"), ("info", "folder_open")]
AS_OF = [  # (기관, 데이터 이름, dataset_key, 표) — 자료 기간만 보인다
    ("관세청", "품목별 국가별 수출입실적", "customs_all", "fact_customs_monthly"),
    ("방사청", "국외 조달계획", "dapa_overseas_plan_api", "clean_dapa_overseas_plan_api"),
    ("방사청", "국산화개발품목", "dapa_localized_item", "clean_dapa_localized_item"),
    ("방사청", "국내 계약정보", "dapa_contract", "clean_dapa_contract"),
    ("열린재정", "세부사업 예산", "openfiscal_program_budget", "clean_openfiscal_program_budget"),
    ("KOSIS", "방산 가동률", "kosis_utilization", "clean_kosis_utilization"),
]

WL_SQL = "SELECT hs6 FROM ref_hs_whitelist WHERE priority IN (1, 2)"
IMP_SQL = ("SELECT hs6, year, stat_cd, imp_dlr, is_partial_year FROM v_import_hs6_year "
           "WHERE hs6 IN :hs AND imp_dlr > 0 AND is_partial_year = 0")


def stats() -> dict:
    """숫자 띠 값 — 실패는 {'error': 클래스명}, 완결 연도 실적이 없으면 {'error': '미적재'}. query() 가 결과를 캐시한다."""
    wl, e1 = try_query(WL_SQL)
    if e1 or wl is None or wl.empty:
        return {"error": e1 or "미적재"}
    imp, e2 = try_query(IMP_SQL, {"hs": wl["hs6"].tolist()})
    if e2 or imp is None or imp.empty:
        return {"error": e2 or "미적재"}
    y = int(imp["year"].max())
    sel = imp[imp["year"] == y]
    conc = concentration(sel, "imp_dlr")
    return {"error": None, "n_tgt": len(wl), "year": y, "imp": float(sel["imp_dlr"].sum()),
            "k50": int((conc["top1_share"] >= 0.5).sum()), "n_ctry": int(sel["stat_cd"].nunique())}


def render(pages: dict) -> None:
    st.html(CSS.replace("__PAD__", PAD))
    home, search, info = pages["home"], pages["search"], pages["info"]

    # 1) 큰 사진 + 글씨
    slides = "".join(f'<div class="mv-sl" style="background-image:url(\'{u}\')"></div>' for u in SLIDES)
    st.html(f'<div class="mv">{slides}<div class="mv-txt"><small>K-DEFENSE DATA PLATFORM</small>'
            '<h1>데이터로 지키는<br>국방 공급망</h1><div class="en">Data-Driven Defense Supply Chain</div>'
            '<p>방산 전자부품의 수출입 · 조달 · 국산화 현황을<br>공개 자료로 한 화면에서 확인합니다.</p></div>'
            '<div class="mv-bar"><span>01</span><div class="tr"></div><em>03</em></div></div>')
    with st.container(key="mv_cta", horizontal=True, vertical_alignment="center"):
        st.page_link(home, label="대시보드 둘러보기", icon=":material/dashboard:", query_params={"sec": "kpi"})
        st.page_link(search, label="직접 조회하기", icon=":material/search:")

    # 2) 소개 + 둥근 아이콘 바로가기
    with st.container(key="mi", horizontal=True):
        st.html('<div class="mi-txt"><div class="k">K-Defense Data Platform</div>'
                '<h2>방산 전자부품의<br><em>수출입 · 조달 · 국산화</em>를<br>한눈에 봅니다</h2>'
                '<p>관세청 수출입무역통계와 방위사업청 조달 · 국산화 자료, 열린재정 · KOSIS 자료를 한곳에 모았습니다. '
                '단위 · 기준이 다른 자료는 합하거나 직접 비교하지 않습니다.</p></div>')
        with st.container(key="mi_links", horizontal=True):
            for k, icon in LINKS:
                st.page_link(pages[k], label=SPEC_BY_KEY[k].label, icon=f":material/{icon}:")

    # 3) 주요 분석 사진 카드
    st.html('<div class="mc-head"><h2><small>ANALYSIS</small>주요 분석 바로가기</h2>'
            '<span>카드를 누르면 해당 페이지의 첫 블록으로 이동합니다</span></div>')
    with st.container(key="mcards", horizontal=True):
        for i, (k, sec, img, cat) in enumerate(CARDS):
            spec = SPEC_BY_KEY[k]
            with st.container(key=f"mc_{i}"):
                st.html(f'<div class="mc-img"><b>{cat}</b><div style="background-image:url(\'{img}\')"></div></div>'
                        f'<div class="mc-body"><h3>{escape(spec.label)}</h3><p>{spec.lead}</p></div>')
                st.page_link(pages[k], label="자세히 보기", icon=":material/arrow_forward:", query_params={"sec": sec})

    # 4) 숫자 띠 — 관세청 최근 완결 연도 · 분석 대상 합계
    s = stats()
    if s["error"]:
        band = (f'<div class="mst-i"><div class="v">—</div><div class="l">조회 실패({escape(s["error"])})</div></div>'
                if s["error"] != "미적재" else '<div class="mst-i"><div class="v">—</div><div class="l">관세청 집계 미적재</div></div>')
        head = "관세청 집계를 읽지 못했습니다"
    else:
        y = s["year"]
        items = [(f'{s["n_tgt"]}', "개", "분석 대상 품목군"),
                 (f'{s["imp"] / 1e8:,.1f}', "억 달러", f"{y} 수입액(분석 대상 합계)"),
                 (f'{s["k50"]}', "개", "특정국 50% 이상 품목군"),
                 (f'{s["n_ctry"]}', "개국", f"{y} 수입 상대국")]
        band = "".join(f'<div class="mst-i"><div class="v">{v}<small>{u}</small></div><div class="l">{escape(lb)}</div></div>'
                       for v, u, lb in items)
        head = f"{y}년(완결 연도) 기준 · 관세청 품목별 국가별 수출입실적 · 국가 전체 수입(민수 포함)"
    st.html(f'<div class="mst" style="background-image:url(\'{_ph("1562408590-e32931084e23", 1800)}\')"><div class="mst-in">'
            f'<div class="mst-h"><b>숫자로 보는<br>K-Defense</b><span>{escape(head)}</span></div>{band}</div></div>')

    # 5) 데이터 기준 시점 · 이용 안내
    with st.container(key="mb", horizontal=True):
        rows = "".join(f'<li><b>{escape(org)}</b><span>{escape(name)}</span>'
                       f'<em>{escape(stamp_period(data_stamp(dk, tb)))}</em></li>'
                       for org, name, dk, tb in AS_OF)
        st.html(f'<div><div class="mb-h"><h3>데이터 기준 시점</h3><span>자료별 자료 기간</span></div>'
                f'<ul class="mb-list">{rows}</ul></div>')
        with st.container():
            st.html('<div class="mb-box"><small>GUIDE</small><h3>처음 오셨나요?<br>이렇게 보시면 됩니다</h3><ul>'
                    '<li>상단 메뉴에 커서를 올리면 페이지별 블록이 펼쳐집니다</li>'
                    '<li>각 페이지 왼쪽 메뉴를 누르면 그 블록으로 이동합니다</li>'
                    '<li>조회에서 국가 · 기간 · 지표를 골라 직접 그려 봅니다</li>'
                    '<li>수입액은 국가 전체 수입(민수 포함)이며 국가는 선적국 기준입니다</li></ul>'
                    '<div style="height:70px"></div></div>')
            with st.container(key="mb_go", horizontal=True):
                st.page_link(home, label="KPI 보기", icon=":material/insights:", query_params={"sec": "kpi"})
                st.page_link(info, label="DATA INFO", icon=":material/folder_open:")


CSS = """<style>
/* ── 큰 사진 — 세 장이 번갈아(18초) 천천히 커지며 바뀐다 ───────────────────── */
.mv{position:relative;height:620px;overflow:hidden;background:#002a73}
.mv-sl{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;
  animation:mvFade 18s infinite;will-change:opacity,transform}
.mv-sl:nth-child(2){animation-delay:6s} .mv-sl:nth-child(3){animation-delay:12s}
@keyframes mvFade{0%{opacity:0;transform:scale(1.02)}5%{opacity:1}33%{opacity:1}39%{opacity:0;transform:scale(1.12)}100%{opacity:0}}
.mv::after{content:"";position:absolute;inset:0;
  background:linear-gradient(180deg,rgba(0,22,70,.62) 0%,rgba(0,40,120,.30) 45%,rgba(0,18,60,.78) 100%)}
.mv-txt{position:absolute;left:0;right:0;top:128px;z-index:2;text-align:center;color:#fff;padding:0 24px}
.mv-txt small{display:inline-block;font-size:13px;font-weight:800;letter-spacing:4px;color:#bcd6ff;
  padding:6px 16px;border:1px solid rgba(188,214,255,.5);border-radius:30px;margin-bottom:22px}
.mv-txt h1{margin:0;padding:0;font-size:58px;font-weight:900;letter-spacing:-2px;line-height:1.15;color:#fff;
  text-shadow:0 4px 24px rgba(0,10,40,.45)}
.mv-txt .en{margin:16px 0 0;font-size:30px;font-weight:800;letter-spacing:-.5px;color:#7cc4ff}
.mv-txt p{margin:16px 0 0;font-size:16px;line-height:1.7;color:#e3ecfb}
.mv-bar{position:absolute;left:50%;bottom:34px;transform:translateX(-50%);z-index:2;display:flex;align-items:center;gap:14px;
  color:#fff;font-size:13px;font-weight:700;letter-spacing:1px}
.mv-bar .tr{width:180px;height:2px;background:rgba(255,255,255,.3);position:relative;overflow:hidden}
.mv-bar .tr::after{content:"";position:absolute;left:0;top:0;height:100%;width:100%;background:#fff;transform-origin:left;
  animation:mvProg 6s linear infinite}
@keyframes mvProg{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.mv-bar em{font-style:normal;color:rgba(255,255,255,.6)}
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

/* ── 소개 줄 — 왼쪽 글 · 오른쪽 둥근 아이콘 바로가기 ─────────── */
.st-key-mi{padding:70px __PAD__ 64px;gap:50px!important;align-items:center!important;flex-wrap:nowrap!important;background:#fff}
.mi-txt{max-width:460px}
.mi-txt .k{display:flex;align-items:center;gap:12px;font-size:14px;font-weight:800;color:#0b1f4d;letter-spacing:-.2px}
.mi-txt .k::before{content:"";width:34px;height:3px;background:#0b1f4d}
.mi-txt h2{margin:18px 0 0;padding:0;font-size:34px;font-weight:900;letter-spacing:-1.2px;line-height:1.3;color:#0b1f4d}
.mi-txt h2 em{font-style:normal;color:#1d4ed8}
.mi-txt p{margin:16px 0 0;font-size:14.5px;line-height:1.8;color:#55637d}
.st-key-mi_links{gap:0!important;flex-wrap:nowrap!important}
.st-key-mi_links > div{flex:1 1 0!important;min-width:0;border-left:1px solid #e3e8f0}
.st-key-mi_links [data-testid="stPageLink"] a{flex-direction:column;gap:18px!important;padding:14px 8px;background:transparent!important;width:100%}
.st-key-mi_links [data-testid="stPageLink"] a > span:first-child{width:auto!important;height:auto!important;justify-content:center!important}
.st-key-mi_links [data-testid="stPageLink"] a{height:auto!important}
.st-key-mi > div:last-child{flex:1 1 0!important;min-width:0}
.st-key-mi > div:first-child{flex:0 0 480px!important;width:480px!important;max-width:480px}
.st-key-mi_links [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{font-size:44px!important;width:96px;height:96px;margin:0!important;
  border:2px solid #1b2540;border-radius:50%;display:grid;place-items:center;color:#1b2540;transition:all .25s}
.st-key-mi_links [data-testid="stPageLink"] a p{font-size:16px!important;font-weight:800;color:#1b2540!important;letter-spacing:-.4px;text-align:center;
  white-space:normal;word-break:keep-all}
.st-key-mi_links [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"]{background:#1d4ed8;border-color:#1d4ed8;color:#fff;
  transform:translateY(-6px);box-shadow:0 14px 26px rgba(29,78,216,.3)}
.st-key-mi_links [data-testid="stPageLink"] a:hover p{color:#1d4ed8!important}

/* ── 주요 분석 카드 — 사진 + 분류 · 제목 · 설명 · 자세히 보기 ───────────────── */
.mc-head{padding:64px __PAD__ 26px;background:#f3f6fb;display:flex;align-items:flex-end;justify-content:space-between}
.mc-head h2{margin:0;padding:0;font-size:32px;font-weight:900;letter-spacing:-1px;color:#0b1f4d}
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
.mc-body h3{margin:0;padding:0;font-size:20px;font-weight:800;letter-spacing:-.6px;color:#0b1f4d}
.mc-body p{margin:10px 0 0;font-size:13.5px;line-height:1.7;color:#5b6b88;min-height:92px}
div[class*="st-key-mc_"] [data-testid="stPageLink"]{padding:0 22px 22px}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a{padding:0;background:transparent!important;flex-direction:row-reverse;justify-content:flex-end;gap:6px!important}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a p{font-size:14px!important;font-weight:800;color:#1d4ed8!important}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{color:#1d4ed8;font-size:18px!important;margin:0!important;
  transition:transform .2s}
div[class*="st-key-mc_"] [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"]{transform:translateX(4px)}

/* ── 숫자 띠 — 사진 위 파랑 ───────────────────────────────────────── */
.mst{position:relative;padding:62px __PAD__;background-size:cover;background-position:center;background-attachment:fixed}
.mst::before{content:"";position:absolute;inset:0;background:linear-gradient(100deg,rgba(0,35,107,.94),rgba(29,78,216,.86))}
.mst-in{position:relative;display:grid;grid-template-columns:260px repeat(4,1fr);align-items:center}
.mst-h b{display:block;font-size:26px;font-weight:900;color:#fff;letter-spacing:-.8px;line-height:1.3}
.mst-h span{display:block;margin-top:8px;font-size:12.5px;color:#b9cdf2;line-height:1.6}
.mst-i{text-align:center;border-left:1px solid rgba(255,255,255,.18);padding:6px 10px}
.mst-i .v{font-size:46px;font-weight:900;color:#fff;letter-spacing:-1.5px;line-height:1.1;font-variant-numeric:tabular-nums}
.mst-i .v small{font-size:16px;font-weight:700;color:#bcd6ff;margin-left:4px;letter-spacing:0}
.mst-i .l{margin-top:8px;font-size:14px;font-weight:600;color:#d6e3fa}

/* ── 아래 줄 — 데이터 기준 시점 · 이용 안내 ─────────────────────────────── */
.st-key-mb{padding:64px __PAD__ 76px;gap:40px!important;flex-wrap:nowrap!important;align-items:stretch!important;background:#fff}
.st-key-mb > div:first-child{flex:1.7 1 0!important;min-width:0}
.st-key-mb > div:last-child{flex:1 1 0!important;min-width:0}
.mb-h{display:flex;justify-content:space-between;align-items:flex-end;padding-bottom:14px;border-bottom:2px solid #0b1f4d}
.mb-h h3{margin:0;padding:0;font-size:22px;font-weight:900;letter-spacing:-.7px;color:#0b1f4d}
.mb-h span{font-size:12.5px;color:#6b7a99}
.mb-list{list-style:none;margin:0!important;padding:0!important}
.mb-list li{display:flex;align-items:center;gap:16px;padding:15px 4px;border-bottom:1px solid #e6ebf3;font-size:14.5px}
.mb-list li b{flex:0 0 64px;text-align:center;font-size:11px;font-weight:800;color:#1d4ed8;background:#eaf1ff;padding:4px 8px;letter-spacing:.5px}
.mb-list li span{flex:1;min-width:0;color:#1b2540;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mb-list li em{flex:0 0 auto;font-style:normal;font-size:13px;color:#7a879e;font-variant-numeric:tabular-nums}
.mb-box{height:100%;padding:30px 30px 26px;color:#fff;background:linear-gradient(140deg,#002a73,#1d4ed8);position:relative;overflow:hidden}
.mb-box::after{content:"shield";font-family:'Material Symbols Rounded';font-size:190px;line-height:1;position:absolute;right:-26px;bottom:-34px;
  color:rgba(255,255,255,.08);font-feature-settings:'liga'}
.mb-box small{font-size:12px;font-weight:800;letter-spacing:3px;color:#9fc2ff}
.mb-box h3{margin:10px 0 0;padding:0;font-size:24px;font-weight:900;letter-spacing:-.8px;line-height:1.35;color:#fff}
.mb-box ul{margin:16px 0 0!important;padding:0!important;list-style:none}
.mb-box li{font-size:13px;line-height:1.75;color:#d4e1f8;padding-left:14px;position:relative}
.mb-box li::before{content:"";position:absolute;left:0;top:10px;width:5px;height:5px;background:#7cc4ff}
.st-key-mb_go{gap:8px!important;margin-top:-86px!important;padding:0 30px;position:relative;z-index:2}
.st-key-mb_go [data-testid="stPageLink"] a{background:#fff;border-radius:0;padding:10px 16px}
.st-key-mb_go [data-testid="stPageLink"] a p{font-size:13.5px!important;font-weight:800;color:#003899!important}
.st-key-mb_go [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{color:#003899}
.st-key-mb_go [data-testid="stPageLink"] a:hover{background:#eaf1ff}
.st-key-landing{gap:0!important;margin:0!important}

/* ── 좁은 화면 — 가로 줄을 세로로 쌓는다 ─────────────────────────────── */
@media (max-width:900px){
  .mv{height:520px} .mv-txt{top:80px} .mv-txt h1{font-size:38px} .mv-txt .en{font-size:20px}
  .st-key-mi,.st-key-mcards,.st-key-mb{flex-wrap:wrap!important}
  .st-key-mi > div:first-child{flex:1 1 100%!important;width:100%!important;max-width:100%}
  .st-key-mcards > div,.st-key-mb > div{flex:1 1 100%!important}
  .mst-in{grid-template-columns:repeat(2,1fr);gap:18px} .mst-h{grid-column:1 / -1}
}
</style>"""
