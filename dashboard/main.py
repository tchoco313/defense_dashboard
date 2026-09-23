"""주요 방산 전자부품 수출입 및 국산화 현황 대시보드 — 진입점(라우터). 제목·페이지 라벨은 2026-09-21 회의 M1(app/specs/00_common.md §1·§8).

실행: streamlit run app/main.py
틀은 팀원 디자인 데모 — 왼쪽 파랑 사이드바 메뉴 · ⓘ 데이터 정보 대화상자(app/kdesign.py). 겉모양은 UI/UX 참고 URL 기준.
페이지 파일·제목·URL·메뉴 순서는 nav.py(PAGE_SPECS·NAV_ORDER) 한 곳에서 정한다. 머리띠(hero)는 각 페이지가 그린다.
DB 접속 확인(db_ready)은 여기서 한 번만 — 페이지 파일은 검사하지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
from db import data_stamp, db_ready, safe_query  # noqa: E402
from nav import NAV_ORDER, nav_items, page  # noqa: E402
from ui import inject_css, sidebar  # noqa: E402

st.set_page_config(page_title="방산 전자부품 수출입 및 국산화 현황", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()

pg = st.navigation([page(k) for k in NAV_ORDER], position="hidden")


@st.dialog("데이터 정보", width="medium")
def data_info_dialog() -> None:
    """ⓘ — 데모 대화상자 모양. 숫자(기간·적재일·국가 수·HS6 수)는 RDS 에서 읽는다."""
    s = data_stamp("customs_all", "fact_customs_monthly")
    n = safe_query("SELECT (SELECT COUNT(*) FROM ref_hs_whitelist) AS n_all, "
                   "(SELECT COUNT(*) FROM ref_hs_whitelist WHERE priority IN (1, 2)) AS n_tgt, "
                   "(SELECT COUNT(DISTINCT stat_cd) FROM fact_customs_monthly) AS n_ctry")
    n_all, n_tgt, n_ctry = (("—",) * 3) if n is None or n.empty else (int(n.at[0, "n_all"]), int(n.at[0, "n_tgt"]), int(n.at[0, "n_ctry"]))
    period = s["period"] if s["has_period"] else "—(조회 실패)"
    warns = ["HS 코드만으로 군용/민수용을 구분할 수 없습니다 — 수입액은 국가 전체(민수 포함)입니다.",
             "특정 국가에 대한 ‘의존도’라는 표현을 쓰지 않습니다 — 「수입 집중도」·「1위 공급국 점유율」·HHI 로 씁니다.",
             "국가는 관세청 통계의 선적국입니다(원산지 아님).",
             "관세청 수입액과 방위사업청 조달 예산은 합산·직접 비교하지 않습니다."]
    st.html(
        '<div class="di-lead">대시보드에 사용된 데이터의 출처, 수집 범위, 처리 과정 및 주요 주의사항을 안내합니다.</div>'
        '<div class="di-card"><div><div class="di-t">데이터 출처</div>'
        '<div class="di-big">관세청 OpenAPI (data.go.kr)<br>데이터셋 ID: 15100475</div>'
        '<div class="di-s">품목별 국가별 수출입실적 · 방위사업청 조달 파일데이터 · KRIT 부품국산화</div></div></div>'
        '<div class="di-card"><div><div class="di-t">분석 기간</div>'
        f'<div class="di-big">{period}</div><div class="di-s">(월별, 마지막 연도는 부분연도)</div></div></div>'
        '<div class="di-card"><div><div class="di-t">수집 범위</div><div class="di-kv">'
        f'<span>국가</span><span><b>{n_ctry}개국</b> (실적이 있는 선적국)</span>'
        f'<span>HS6</span><span><b>{n_all}개</b> (수집범위) → <b>{n_tgt}개</b> (분석대상)</span></div></div></div>'
        '<div class="di-card"><div><div class="di-t">데이터 단위</div><div class="di-kv">'
        '<span>수출입</span><span><b>USD</b> (화면은 백만 USD · 억 달러)</span>'
        '<span>중량</span><span><b>kg</b> (참고값, 화면은 톤)</span></div></div></div>'
        '<div class="di-card warn"><div><div class="di-t">주요 주의사항</div><ol class="di-warn">'
        + "".join(f"<li>{w}</li>" for w in warns) + '</ol></div></div>')
    st.page_link(page("info"), label="DATA INFO 페이지에서 더 보기", icon=":material/arrow_forward:")


def foot() -> str:
    """사이드바 아래 — 관세청 자료 기간(db.data_stamp, 비캐시). DB 적재일 · 표 이름은 화면에 쓰지 않는다(보안, 2026-09-24)."""
    s = data_stamp("customs_all", "fact_customs_monthly")
    period = s["period"] if s["has_period"] else "—"
    return ('<div class="sb-note">공개 자료로 확인·인용하는<br>수출입 · 조달 · 국산화 현황</div>'
            f'<div class="sb-ver">관세청 자료 {period}</div>')


items = nav_items()
sidebar(items, pg, foot(), on_info=data_info_dialog)
if not db_ready():      # 접속 실패면 오류·「다시 연결」만 보이고 페이지 본문은 실행하지 않는다
    st.stop()
pg.run()
