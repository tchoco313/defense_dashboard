"""공개 공고와 후속 발표로 읽는 무기체계·부품국산화 소개.

공고 집계는 hscode 공고문에서 추출한 지원대상과제.csv(2026-09-29 검토)의
과제명이 있는 197행이다. 재공고·수정공고를 포함하며 선정·완료 과제 수가 아니다.
기업 사례는 .private/무기체계/{한화_국산화_수출,기타기업_국산화_수출}/자료_안내.md의
공식 출처를 검토해 선별한 공개 발표다. 두 자료 사이에는 연결키가 없다.
"""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from ui import chart_title, hero, kpi, style_fig, zone


# 과제명 비어 있지 않은 공고 추출표 197행. 사업유형 표기 변형을 첫 단어로 묶었다.
NOTICE_TYPES = (("핵심부품", 159), ("전략부품", 23), ("수출연계", 4), ("유형 미기재", 11))
RFP_THEMES = (
    ("전원·제어", "전원 공급, 상태 감시, 신호 제어와 고장 진단", "전원장치·회로카드·제어기"),
    ("탐지·광학", "영상 획득, 거리·방향 측정, 센서 신호 처리", "카메라·영상증폭·광학 부품"),
    ("통신·반도체", "무선 신호 증폭, 통신 연결, 전자회로 기능", "증폭장치·통신 칩셋·반도체"),
    ("항법·운용", "위치·자세 정보와 운용 상태를 표시·제어", "항법 센서·표시기·계기"),
)

# (기업, 분야, 공개된 대상, 단계, 기준일, 확인된 내용, 공식 URL)
CASES = (
    ("한화시스템", "전자·센서", "KF-21 AESA 레이다", "양산 출고", "2025-08", "국내 개발 후 양산 1호기 출고 발표", "https://www.hanwhasystems.com/kr/prcenter/newsView.do?bbidx=715"),
    ("한화시스템", "전자·센서", "항공기 AESA 안테나", "공급 계약", "2024-05", "레오나르도와 공급 계약 발표", "https://www.hanwhasystems.com/kr/prcenter/newsView.do?bbidx=634"),
    ("한화시스템", "전자·센서", "천궁-II 다기능레이다", "수출 계약 관련", "2025", "중동 수출 계약 관련 레이다 공급 사례 발표", "https://www.hanwhasystems.com/kr/prcenter/newsView.do?bbidx=732"),
    ("한화시스템", "전자·센서", "L-SAM-II 다기능레이다", "개발 선정", "2025-05", "시제 개발 사업자 선정 발표", "https://www.hanwhasystems.com/kr/prcenter/newsView.do?bbidx=707"),
    ("한화에어로스페이스", "완성 체계·엔진", "K9 국산 엔진", "시험 완료", "2025-02", "국내 개발 엔진의 이집트 내구도 시험 완료 발표", "https://www.hanwhaaerospace.com/kor/media/newsroom/view.do?seq=478"),
    ("한화에어로스페이스", "완성 체계·엔진", "레드백 보병전투장갑차", "수출 계약", "2023-12", "호주 공급 본계약 발표", "https://www.hanwhaaerospace.com/kor/media/newsroom/view.do?seq=378"),
    ("한화에어로스페이스", "완성 체계·엔진", "K9·K10", "수출 계약", "2024-07", "루마니아 공급 계약 발표", "https://www.hanwhaaerospace.com/eng/media/newsroom/view.do?seq=419"),
    ("한화에어로스페이스", "완성 체계·엔진", "천무", "수출 계약", "2026-02", "노르웨이 계약 체결 발표", "https://www.hanwhaaerospace.com/kor/media/newsroom/view.do?seq=597"),
    ("방위사업청·중소기업", "부품국산화", "천마 패키지 부품", "개발 성공", "2026-02", "중소기업 18개사 참여, 9개 품목 최종평가 성공 발표", "https://www.dapa.go.kr/dapa/doc/selectDoc.do?bbsSeq=326&docSeq=58250&menuSeq=3069"),
    ("RFHIC", "전자·센서", "고출력 증폭기 부품", "수출 합의", "2025-05", "레오나르도 관련 부품 수출 합의 발표", "https://www.dapa.go.kr/dapa/doc/selectDoc.do?bbsSeq=326&docSeq=21025&menuSeq=3069"),
    ("마이크로인피니티", "전자·센서", "항재밍 수신기 부품", "수출 계약", "2024-10", "영국 MBDA와 부품 수출 계약 발표", "https://www.daejeon.go.kr/drh/board/boardNormalView.do?boardId=normal_0189&menuSeq=1632&ntatcSeq=1467432347&pageIndex=1"),
    ("인텔릭스", "전자·센서", "중앙영상처리장치", "수출 합의", "2026-03", "독일 Hensoldt 관련 부품 수출 합의 발표", "https://www.dapa.go.kr/dapa/doc/selectDoc.do?bbsSeq=326&docSeq=58339&menuSeq=3069"),
    ("현대로템", "완성 체계·엔진", "K2", "현지 협력 계약", "2026-04", "폴란드 현지 생산·정비 협력 계약 발표", "https://www.hyundai-rotem.co.kr/ko/company/press/details.do?seq=2635"),
    ("LIG넥스원", "완성 체계·엔진", "천궁-II", "수출 계약", "2022", "UAE 수출 계약을 소개한 회사 자료", "https://www.lignex1.com/web/kor/prcenter/news/view.do?seq=3022"),
)

st.html("""<style>
.wc-lead{font-size:15px;line-height:1.75;color:#405674;margin:8px 0 22px}
.wc-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:10px 0 20px}
.wc-card{background:#fff;border:1px solid #dce5f2;border-radius:12px;padding:18px;min-height:142px}
.wc-card b{display:block;color:#173b76;font-size:17px;margin-bottom:9px}
.wc-card p{font-size:14px;color:#405674;line-height:1.55;margin:0 0 12px}
.wc-card small{color:#6c7f9c;font-size:12px}
.wc-note{background:#f4f8ff;border-left:4px solid #3975df;border-radius:7px;padding:15px 18px;color:#34516f;font-size:14px;line-height:1.65;margin:12px 0 22px}
.wc-case{background:#fff;border:1px solid #dce5f2;border-radius:12px;padding:16px 19px;margin:10px 0}
.wc-case .top{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:7px}
.wc-case b{font-size:17px;color:#163765}.wc-case .pill{font-size:12px;color:#1752a5;background:#e9f1ff;border-radius:30px;padding:3px 9px}
.wc-case p{font-size:14px;color:#425877;line-height:1.55;margin:5px 0}.wc-case small{font-size:12px;color:#71819a}
.wc-case a{color:#1d4ed8;font-size:13px;font-weight:700;text-decoration:none}
.wc-links{display:flex;gap:14px;flex-wrap:wrap;margin:12px 0 20px}.wc-links a{color:#174aa1;font-weight:700}
@media(max-width:900px){.wc-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:550px){.wc-grid{grid-template-columns:1fr}}
</style>""")

if not st.session_state.get("_kd_demo_shell"):
    hero()
st.html('<p class="wc-lead">무기체계는 전자·센서 부품부터 엔진과 완성 체계까지 여러 층으로 이루어집니다. 이 화면은 개발 공고가 제시한 기술 수요와, 별도 공식 발표로 확인되는 국산화·수출 사례를 소개합니다.</p>')

with zone("guide", "자료를 읽는 순서"):
    st.html('<div class="wc-grid">'
            '<div class="wc-card"><b>① 개발 수요</b><p>공고·RFP에서 개발 대상과 필요한 기능을 확인합니다.</p><small>모집·제안 단계</small></div>'
            '<div class="wc-card"><b>② 국산 개발</b><p>선정·시험·평가 발표로 진행 단계를 따로 확인합니다.</p><small>개발·검증 단계</small></div>'
            '<div class="wc-card"><b>③ 양산·공급</b><p>양산 출고와 공급 계약은 각각 발표 내용대로 표시합니다.</p><small>생산·계약 단계</small></div>'
            '<div class="wc-card"><b>④ 수출</b><p>계약·합의·인도를 구별해 해외 사업을 읽습니다.</p><small>후속 사업 단계</small></div>'
            '</div>')
    st.html('<div class="wc-note">공고 목록과 기업 발표는 서로 다른 자료입니다. 같은 무기체계나 부품처럼 보여도 이 화면에서 과제와 기업 실적을 직접 연결하지 않습니다.</div>')

with zone("notice", "공고가 보여주는 국산화 수요"):
    st.html('<div class="kpis k4">'
            + kpi("과제 기재 행", "197", "행", "공고 추출표 · 재공고 포함", icon="description")
            + kpi("상세 RFP", "22", "건", "기능·개발 중점 검토", icon="article")
            + kpi("핵심부품 유형", "159", "행", "사업유형 표기 정규화", icon="memory")
            + kpi("전략·수출연계", "27", "행", "전략 23 · 수출연계 4", icon="category")
            + '</div>')
    chart_title("공고 추출표에서 가장 많은 사업유형은 핵심부품", "과제명이 있는 197행 · 원본 사업유형 표기를 묶음 · 재공고/수정공고 중복 포함")
    labels, values = zip(*NOTICE_TYPES)
    fig = go.Figure(go.Bar(x=list(values), y=list(labels), orientation="h", text=list(values), textposition="outside",
                           marker_color=["#2c62cf", "#5592dc", "#81b7df", "#b6c3d7"]))
    fig.update_layout(height=250, showlegend=False, margin=dict(l=10, r=45, t=10, b=10), xaxis_title="과제 기재 행")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(style_fig(fig), width="stretch", config={"displayModeBar": False})
    st.html('<div class="wc-note">197은 선정·개발 성공 건수가 아닙니다. 과제명 문자열의 고유값은 161개지만 재공고와 명칭 변형을 정리한 사업 수가 아니므로 지표로 쓰지 않습니다. 공고의 예상개발비·최대지원금도 집행액이 아닙니다.</div>')

with zone("technology", "상세 RFP의 전자·센서 기능"):
    st.html('<p class="wc-lead">22건의 상세 RFP에서 확인한 기능을 소개용으로 묶었습니다. 아래 네 묶음은 정량 분류가 아니며, 특정 장비와 취약 부품의 대응표가 아닙니다.</p>')
    cards = ''.join(f'<div class="wc-card"><b>{escape(name)}</b><p>{escape(desc)}</p><small>예: {escape(example)}</small></div>'
                    for name, desc, example in RFP_THEMES)
    st.html(f'<div class="wc-grid">{cards}</div>')
    st.html('<div class="wc-note">국산화 공고에서 반복되는 이유는 수입품 대체, 단종·수급 대응, 호환성 확보, 성능·정비성 개선입니다. 개별 과제가 그 목표를 달성했는지는 후속 평가 자료가 있어야 확인할 수 있습니다.</div>')

with zone("cases", "공개 발표로 확인한 개발·수출 사례"):
    st.html('<p class="wc-lead">기업과 정부의 공식 발표를 기준으로 단계가 확인된 사례를 골랐습니다. 수출 계약·합의는 실제 납품액이나 관세청 수출액을 뜻하지 않습니다.</p>')
    c1, c2 = st.columns(2)
    with c1:
        area = st.selectbox("분야", ["전체", "전자·센서", "완성 체계·엔진", "부품국산화"], key="wc_area")
    with c2:
        stage = st.selectbox("진행 단계", ["전체", "개발·시험·양산", "계약·합의", "개발 성공"], key="wc_stage")
    selected = []
    for row in CASES:
        company, category, item, status, when, detail, url = row
        if area != "전체" and category != area:
            continue
        if stage == "개발·시험·양산" and status not in ("개발 선정", "시험 완료", "양산 출고"):
            continue
        if stage == "계약·합의" and "계약" not in status and "합의" not in status:
            continue
        if stage == "개발 성공" and status != "개발 성공":
            continue
        selected.append(row)
    st.caption(f"선택한 공개 발표 {len(selected)}건 · 조사 기준 2026-09-29")
    if not selected:
        st.info("해당 조건의 사례가 없습니다. 다른 분야 또는 단계를 선택해 주세요.")
    else:
        for company, category, item, status, when, detail, url in selected:
            st.html('<div class="wc-case"><div class="top"><b>' + escape(item) + '</b><span class="pill">' + escape(status)
                    + '</span></div><small>' + escape(company) + ' · ' + escape(category) + ' · ' + escape(when)
                    + '</small><p>' + escape(detail) + '</p><a href="' + escape(url, quote=True)
                    + '" target="_blank" rel="noopener noreferrer">공식 발표 보기 ↗</a></div>')

with zone("sources", "출처와 기존 분석 연결"):
    st.html('<p class="wc-lead">공고·RFP는 국산화 수요의 배경 자료이고, 기존 대시보드의 관세청 HS 수출입·방위사업청 FSC 조달/완료 부품 집계와 집계 단위가 다릅니다.</p>')
    st.html('<div class="wc-links">'
            '<a href="https://www.krit.re.kr/krit/bbs/gbby_list.do" target="_blank" rel="noopener noreferrer">국방기술진흥연구소 사업 공고 ↗</a>'
            '<a href="https://www.dapa.go.kr/dapa/page/selectPage.do?menuSeq=4091&pageSeq=4201" target="_blank" rel="noopener noreferrer">방위사업청 부품국산화 사업 소개 ↗</a>'
            '<a href="/parts">조달·국산화 화면 →</a><a href="/import">수출입 화면 →</a></div>')
    st.html('<div class="wc-note">화면 자료: hscode 공고문 추출표(지원대상과제.csv) · 상세 RFP 22건 · 방위사업청 부품국산화 자료 · 한화시스템·한화에어로스페이스 및 관련 기업·기관의 공식 발표. HS 코드와 개별 무기체계를 1:1 대응하거나 국산화율을 계산하지 않습니다.</div>')
