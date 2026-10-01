"""「부품 → 무기체계」 화면의 공개 자료 기반 설명 구역.

대분류: .private/무기체계/무기체계_분류체계_별표3.pdf (방위사업청 분류체계).
개발 수요: hscode 공고문 22개 RFP 및 지원대상과제.csv 검토본.
사례: .private/무기체계/한화_국산화_수출/자료_안내.md 및
      .private/무기체계/기타기업_국산화_수출/자료_안내.md의 공식 발표.
2026-09-29에 확인한 설명용 스냅샷이며 기존 HS/FSC 집계와 연결하지 않는다.
"""
from __future__ import annotations

from html import escape

import streamlit as st


SYSTEMS = (
    ("W01", "지휘통제통신", "정보를 공유하고 부대·체계의 판단과 명령을 연결합니다.", "지휘통제체계 · 전술통신 · 데이터링크"),
    ("W02", "감시·정찰", "레이다·전자광학·음탐 등으로 주변 상황을 탐지합니다.", "레이다 · 전자광학 · 수중감시"),
    ("W03", "기동", "지상에서 이동하며 작전을 수행하는 체계입니다.", "전차 · 장갑차 · 지상무인체계"),
    ("W04", "함정", "해상과 수중에서 작전을 수행하는 플랫폼입니다.", "수상함 · 잠수함"),
    ("W05", "항공", "공중에서 작전을 수행하는 플랫폼입니다.", "고정익 · 회전익 · 무인항공기"),
    ("W06", "화력", "표적에 화력을 전달하는 체계입니다.", "화포 · 유도무기"),
    ("W07", "방호", "인원과 장비를 위협으로부터 보호합니다.", "방호 장비 · 화생방 대응"),
    ("W08", "사이버", "사이버 공간에서 작전을 지원·수행합니다.", "사이버 무기체계"),
    ("W09", "우주", "우주 영역에서 정보·작전 기능을 수행합니다.", "우주 무기체계"),
    ("W10", "기타", "앞의 분류에 속하지 않는 체계를 담습니다.", "기타 무기체계"),
)

# 특정 공고의 부품과 개별 완성 체계를 연결하지 않는, 각각 독립적인 공개 발표 사례.
CASES = (
    ("감시·정찰", "한화시스템", "KF-21 AESA 레이다", "양산 출고", "2025-08", "국내 개발 후 양산 1호기 출고 발표", "https://www.hanwhasystems.com/kr/prcenter/newsView.do?bbidx=715"),
    ("감시·정찰", "한화시스템", "천궁-II 다기능레이다", "수출 계약 관련", "2025", "중동 수출 계약 관련 공급 사례 발표", "https://www.hanwhasystems.com/kr/prcenter/newsView.do?bbidx=732"),
    ("기동", "한화에어로스페이스", "레드백 보병전투장갑차", "수출 계약", "2023-12", "호주 공급 본계약 발표", "https://www.hanwhaaerospace.com/kor/media/newsroom/view.do?seq=378"),
    ("화력", "한화에어로스페이스", "K9 국산 엔진", "시험 완료", "2025-02", "국내 개발 엔진의 내구도 시험 완료 발표", "https://www.hanwhaaerospace.com/kor/media/newsroom/view.do?seq=478"),
    ("화력", "한화에어로스페이스", "천무", "수출 계약", "2026-02", "노르웨이 공급 계약 발표", "https://www.hanwhaaerospace.com/kor/media/newsroom/view.do?seq=597"),
    ("부품국산화", "방위사업청·중소기업", "천마 패키지 부품", "개발 성공", "2026-02", "18개 중소기업 참여, 9개 품목 최종평가 성공 발표", "https://www.dapa.go.kr/dapa/doc/selectDoc.do?bbsSeq=326&docSeq=58250&menuSeq=3069"),
    ("전자부품", "RFHIC", "고출력 증폭기 부품", "수출 합의", "2025-05", "이탈리아 기업 관련 부품 수출 합의 발표", "https://www.dapa.go.kr/dapa/doc/selectDoc.do?bbsSeq=326&docSeq=21025&menuSeq=3069"),
    ("전자부품", "마이크로인피니티", "항재밍 수신기 부품", "수출 계약", "2024-10", "영국 기업과 부품 수출 계약 발표", "https://www.daejeon.go.kr/drh/board/boardNormalView.do?boardId=normal_0189&menuSeq=1632&ntatcSeq=1467432347&pageIndex=1"),
)

_CSS = """<style>
.ws-lead{font-size:15px;line-height:1.7;color:#3e5677;margin:3px 0 19px}
.ws-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:14px 0 20px}
.ws-class{border:1px solid #dae5f3;border-radius:10px;background:#fff;padding:13px;min-height:125px}
.ws-class small{display:block;color:#4978c4;font-size:11px;font-weight:800;margin-bottom:5px}
.ws-class b{display:block;color:#173864;font-size:15px;margin-bottom:7px}
.ws-class span{font-size:12px;color:#5b6d89;line-height:1.45}
.ws-flow{display:flex;gap:8px;align-items:stretch;margin:15px 0;flex-wrap:wrap}
.ws-flow div{flex:1 1 150px;border-radius:9px;background:#edf4ff;padding:13px;color:#274466;font-size:13px;line-height:1.5}
.ws-flow b{display:block;color:#174c9c;font-size:14px;margin-bottom:4px}
.ws-note{background:#f4f8ff;border-left:4px solid #3d78d8;border-radius:6px;padding:12px 15px;color:#3b5575;font-size:13px;line-height:1.65;margin:16px 0}
.ws-cases{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:13px 0}
.ws-case{border:1px solid #dce5f2;border-radius:10px;background:#fff;padding:16px}
.ws-case b{display:block;color:#193b70;font-size:16px}.ws-case small{color:#667c9c;font-size:12px}
.ws-case p{font-size:13px;color:#455a78;line-height:1.5;margin:8px 0}
.ws-case a{font-size:12px;color:#1d4ed8;font-weight:700;text-decoration:none}
.ws-tag{display:inline-block;color:#1554a5;background:#e8f0ff;border-radius:20px;padding:2px 8px;font-size:11px;margin:5px 0}
@media(max-width:1000px){.ws-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:650px){.ws-grid,.ws-cases{grid-template-columns:1fr}}
</style>"""


def render_overview() -> None:
    """분류 → 체계의 구성 → 기존 대시보드 지표의 관계를 설명한다."""
    st.html(_CSS)
    st.html('<p class="ws-lead"><b>무기체계</b>는 임무를 수행하도록 장비·소프트웨어·부품이 통합된 체계입니다. '
            '방위사업청의 분류체계는 이를 임무와 운용 영역에 따라 10개 대분류로 구분합니다.</p>')
    cards = ''.join(f'<div class="ws-class"><small>{escape(code)}</small><b>{escape(name)}</b><span>{escape(role)}</span></div>'
                    for code, name, role, _ in SYSTEMS)
    st.html(f'<div class="ws-grid">{cards}</div>')
    names = [f"{code} {name}" for code, name, _, _ in SYSTEMS]
    chosen = st.selectbox("분류별 역할 보기", names, key="weapon_class_pick")
    code, name, role, examples = SYSTEMS[names.index(chosen)]
    st.html(f'<div class="ws-note"><b>{escape(name)}</b> — {escape(role)}<br>분류표의 중분류 예: {escape(examples)}</div>')
    st.html('<p class="ws-lead">완성 체계 안에는 여러 기능과 부품이 함께 들어갑니다. 이 프로젝트는 그중 전자·통신·센서와 관련된 군급을 살펴봅니다.</p>')
    st.html('<div class="ws-flow"><div><b>① 임무</b>탐지·통신·기동·화력 등 수행 목적</div>'
            '<div><b>② 무기체계</b>여러 장비를 통합한 운용 단위</div>'
            '<div><b>③ 기능·부품</b>전원·제어·센서·통신 등 구성 요소</div>'
            '<div><b>④ 공급·국산화</b>조달계획과 완료 이력을 별도 자료로 확인</div></div>')
    st.html('<div class="ws-note">W01~W10은 무기체계의 임무별 분류, FSC는 군수품의 품목 분류, HS는 통관 품목 분류입니다. 이 자료들만으로 개별 무기체계와 부품·수출액을 1:1로 연결할 수 없습니다.</div>')
    st.caption("분류 출처: 방위사업청 「무기체계 분류체계」 별표 3 · 이 화면의 역할 설명은 분류표를 쉽게 풀어 쓴 것입니다.")


def render_examples() -> None:
    """공식 발표의 단계를 분리해 보여 주는 보조 사례."""
    st.html(_CSS)
    st.html('<p class="ws-lead">무기체계의 개발·생산·수출이 실제로 어떻게 이어지는지 보여 주는 공개 사례입니다. '
            '아래 발표는 기존 국산화 완료 부품 집계와 별개의 자료입니다.</p>')
    group = st.selectbox("사례 분야", ["전체", "감시·정찰", "기동", "화력", "부품국산화", "전자부품"], key="weapon_example_pick")
    chosen = [r for r in CASES if group == "전체" or r[0] == group]
    cards = ''.join('<div class="ws-case"><b>' + escape(item) + '</b><span class="ws-tag">' + escape(status)
                    + '</span><br><small>' + escape(company) + ' · ' + escape(when) + '</small><p>' + escape(detail)
                    + '</p><a href="' + escape(url, quote=True) + '" target="_blank" rel="noopener noreferrer">공식 발표 보기 ↗</a></div>'
                    for _, company, item, status, when, detail, url in chosen)
    st.html(f'<div class="ws-cases">{cards}</div>')
    st.html('<div class="ws-note">개발 성공·시험 완료·양산 출고·수출 계약·수출 합의는 서로 다른 단계입니다. 계약이나 합의 발표만으로 실제 인도액 또는 관세청 수출액을 알 수 없습니다.</div>')


def render_notice_context() -> None:
    """공고는 보조 근거로만 사용하며 개별 장비·부품 취약성은 나열하지 않는다."""
    st.html(_CSS)
    st.html('<p class="ws-lead">수집한 공고·상세 RFP에는 전원·제어, 통신·신호 증폭, 탐지·광학, 항법·표시 기능의 개발 수요가 나옵니다. '
            '해외 도입품 대체, 단종·수급 대응, 호환성 및 정비성 개선이 추진 배경으로 제시됩니다.</p>')
    st.html('<div class="ws-note">공고는 개발 대상의 모집 계획을 보여 줍니다. 과제 선정, 개발 성공, 양산 또는 수출의 증거로 읽지 않습니다. '
            '원자료의 재공고·수정공고가 섞여 있어 행 수를 성과 건수로 쓰지 않았습니다.</div>')
    st.html('<div class="ws-flow"><div><b>공고·RFP</b>무엇을 개발하려 했는가</div>'
            '<div><b>후속 평가</b>개발·시험이 어디까지 진행됐는가</div>'
            '<div><b>기업·기관 발표</b>양산·계약·납품이 확인됐는가</div></div>')
    st.caption("자료: hscode 공고문 · 상세 RFP 22건(2026-09 기준) · 방위사업청 부품국산화 사업 자료")
