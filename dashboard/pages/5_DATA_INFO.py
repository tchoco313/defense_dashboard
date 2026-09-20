"""⑤ DATA INFO — 출처 · 기준일 · 선정 규칙 · 지표 정의 · 과천 판별 방법 · 제외 데이터와 이유 · 과장 금지 목록.

근거 문서(문구를 바꿀 때 먼저 고친다):
- 출처 표: DB meta_dataset(= db/meta_dataset.csv) — 화면이 문서와 따로 놀지 않게 DB에서 읽는다
- 선정 규칙 R1~R4: docs/reference/hs-whitelist-definition.md §8-2
- 제외 데이터: docs/report/data-usage-decision-2026-09-18.md §1 「제외」, docs/idea-review.md §2-C
- 과장 금지: docs/idea-review.md §3 유의사항
- 과천 판별: 드라이브 「군 직접 수입 추정(과천) 판별 근거_2026-09-18」 요지
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_ready, safe_query  # noqa: E402
from ui import MUTED, zone  # noqa: E402

if not db_ready():
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def load_sources() -> pd.DataFrame | None:
    return safe_query("""
        SELECT tier, provider, dataset_id, title, url, access_method, acquired_on,
               period_start, period_end, is_partial_period, raw_row_count
        FROM meta_dataset WHERE tier <> '메타'
        ORDER BY FIELD(tier, '핵심', '보조', '참조'), provider, dataset_key
    """)


def cards(items: list[tuple[str, str]], cols: int = 2) -> str:
    """(제목, 본문 HTML) 카드 묶음."""
    body = "".join(f'<div class="card"><div class="h">{h}</div><div class="note" style="font-size:12px">{b}</div></div>'
                   for h, b in items)
    return f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:12px">{body}</div>'


def bullets(items: list[str]) -> str:
    return "<br>".join("· " + i for i in items)


def period(r) -> str:
    if pd.isna(r.period_start):
        return "—"
    end = f"{pd.Timestamp(r.period_end):%Y.%m}" if pd.notna(r.period_end) else ""
    return f"{pd.Timestamp(r.period_start):%Y.%m}~{end}" + (" (부분)" if r.is_partial_period else "")


st.html('<div class="page-h">⑤ DATA INFO</div>'
        '<div class="note">이 대시보드의 숫자가 어디서 왔고, 어떻게 계산했고, 무엇을 뜻하지 않는지 적어 둔 곳입니다.</div>')

# ── 1. 출처와 규모 ───────────────────────────────────────────────────────────
with zone("p5_src", "데이터 출처와 규모"):
    src = load_sources()
    if src is None or src.empty:
        st.info("출처 표(meta_dataset)를 읽지 못했습니다. 기준 문서: docs/data-sources.md · db/meta_dataset.csv")
    else:
        view = pd.DataFrame({
            "구분": src["tier"], "제공기관": src["provider"], "자료": src["title"], "포털 ID": src["dataset_id"].fillna("—"),
            "대상 기간": [period(r) for r in src.itertuples()], "확보일": src["acquired_on"].astype(str),
            "원본 건수": src["raw_row_count"], "방식": src["access_method"], "링크": src["url"],
        })
        st.dataframe(view, hide_index=True, width="stretch", height=min(38 + 35 * len(view), 560), column_config={
            "원본 건수": st.column_config.NumberColumn(format="localized", help="내려받은 원본을 파서로 센 레코드 수(포털 표시 건수 아님)"),
            "링크": st.column_config.LinkColumn(display_text="열기"),
        })
        n_big = int((src["raw_row_count"] >= 10_000).sum())
        st.html('<div class="note">'
                + bullets(["이 표는 팀 DB에 적재한 자료 전체입니다. 화면에 쓰지 않는 자료와 이유는 아래 「쓰지 않은 데이터」에 있습니다",
                           "원본 건수 = 실제로 내려받아 파서로 센 수입니다. 포털 표시 건수 · API 총건수 · 반복 수집분은 넣지 않았습니다",
                           f"1만 건 이상 원본 {n_big}종 — 과제 요건 「2종 × 각 1만 건」은 관측 대상이 서로 다른 자료로 셉니다",
                           "관세청 2026년은 8월까지의 부분연도라 연간 비교 · KPI에서 뺍니다"])
                + "</div>")

# ── 2. 선정 규칙과 지표 정의 ─────────────────────────────────────────────────
with zone("p5_rule", "품목 선정 규칙과 지표 정의"):
    st.html(cards([
        ("분석 대상 19개 품목군은 이렇게 골랐습니다", bullets([
            "범위: HS 84 · 85 · 88 · 90류의 HS6 1,003개",
            "<b>R1 군용전용</b> — 관세청 분류표(관세법 §84)에 「제9301호 · 제9306호 물품 전용」 세분류가 있음",
            "<b>R2 항공 · 항행</b> — 「항공기용 · 항행 · 레이더 · 무인기」 세분류가 있거나 HS6 명칭에 같은 용도어",
            "<b>R3 이중용도</b> — 전략물자수출입고시 별표2 3 · 5 · 6 · 7부(전자 · 정보통신 · 센서 · 항법) 통제품목",
            "<b>R4 국산화 대응</b> — 방사청 국산화개발품목(B2) 군급 후보 대응. <b>잠정</b>(공식 HS↔군급 연계표 없음)",
            "진입 = <b>R1 또는 R2 또는 (R3 그리고 R4)</b>. R3만으로는 들어오지 않습니다",
            "규칙은 공식 자료에서 도출한 팀 규칙이며 통계적 검증이 아닙니다"])),
        ("지표는 이렇게 계산합니다", bullets([
            "<b>수입액</b> = 관세청 품목별 국가별 수출입실적, HS10 → HS6 합산, 총계 행 제외, USD",
            "<b>1위 공급국 점유율</b> = 1위 국가 수입액 ÷ 품목군 수입액",
            "<b>HHI</b> = Σ(국가별 점유율 %)², 0~10,000. 2,500 이상을 「높은 집중」으로 봅니다(미 법무부 기준)",
            "여러 해를 고르면 <b>기간 합계</b>로 점유율 · HHI를 다시 계산합니다(연도별 값의 평균 아님)",
            "<b>수출/수입</b> = 같은 기간 수출액 ÷ 수입액. HS6 합계라 민수 반도체가 대부분입니다",
            "<b>특정국 50% 이상</b> = 1위 공급국 점유율 50% 이상인 품목군 수(산업부 공급망 참고선)",
            "국가는 <b>선적국</b> 기준입니다. 원산지와 다를 수 있습니다(홍콩 · 싱가포르 경유 등)"])),
    ]))

# ── 3. 과천 = 군 직접 수입(하한) ─────────────────────────────────────────────
with zone("p5_gc", "군 직접 수입(과천) 판별 방법"):
    st.html(cards([
        ("무엇을 보나", bullets([
            "관세청 <b>시군구별</b> 품목별 수출입실적(15134343)에서 수입자 소재지가 <b>경기 과천시</b>인 비중",
            "과천에는 방위사업청(정부과천청사)과 통관부대 국군수송사령부 본부가 있습니다",
            "2025년 기준 항공 · 항법 · 레이더 · 통신 품목에서 7~30%, 반도체에서 0~0.2%",
            "수입 지역은 관세청 명세상 「납세의무자 주소지」 기준입니다"])),
        ("왜 「하한 추정」인가", bullets([
            "관세법 §92에 따라 정부 위탁 업체 명의로도 군수품을 수입할 수 있어, 업체 소재지(창원 · 사천 등)로 잡히는 몫은 빠집니다",
            "그래서 과천 비중은 군 직접 수입의 <b>최소치</b>로만 씁니다",
            "수입신고필증의 납세의무자가 실제 방사청 · 국수사인지는 공개 문서로 확인되지 않았습니다 → 「추정(강한 정황)」",
            f'<span style="color:{MUTED}">현재 상태: 팀 DB 적재 전. 적재 뒤 ① · ③ 화면에 표시됩니다</span>'])),
    ]))

# ── 4. 제외한 데이터 ────────────────────────────────────────────────────────
with zone("p5_ex", "쓰지 않은 데이터와 이유"):
    ex = pd.DataFrame([
        ("국외조달 입찰결과", "2025.03~09 6개월뿐, 전자 후보 9건. 행 = 품목이라 유찰률이 부풀려짐"),
        ("국외조달 계약정보", "금액 · 국가가 없고 조달계획과 역할이 겹침"),
        ("국내 입찰공고 · 입찰결과", "전자부품과 연결할 공통 식별자(군급 · 재고번호)가 없음"),
        ("군별 계약 집행 · 국내 조달계획", "부품 단위로 연결되지 않음"),
        ("사전의향서 CSV", "현재조달원이 전부 내자(국내)라 수입 의존 판별 불가"),
        ("국방표준종합서비스(2016)", "2016 한 시점 스냅샷이라 연도 축이 없고, 국산화 목록과 교집합이 거의 없음"),
        ("무기체계별 부품 구성(BOM) · 생산 대수", "비공개(군사기밀 · 영업비밀). 추정 · 역산하지 않음"),
        ("「국방용 반도체」 수입액", "HS 코드는 용도를 구분하지 않아 존재하지 않는 통계"),
    ], columns=["데이터", "이유"])
    st.dataframe(ex, hide_index=True, width="stretch")

# ── 5. 과장 금지 ────────────────────────────────────────────────────────────
with zone("p5_no", "이 대시보드가 말하지 않는 것"):
    st.html(cards([
        ("수치 해석", bullets([
            "수입액은 <b>국가 전체 수입(민수 포함)</b>입니다. 「국방용 ○○ 수입 N억」이라고 쓰지 않습니다",
            "HHI · 점유율은 <b>수입 집중도</b>이지 군수 의존도나 위험도가 아닙니다. 예측 · 조기경보를 하지 않습니다",
            "국외 조달계획은 <b>계획(원화 예정액)</b>, 관세청 수입액은 <b>실적(달러)</b>입니다. 합산 · 비율 · 직접 비교하지 않습니다",
            "국산화개발 부품 수는 <b>완료 부품 목록</b>(지상 28개 사업)이며 국산화율이 아닙니다. 빈칸은 「국산화 안 됨」이 아니라 「이 자료에 없음」"])),
        ("표현 범위", bullets([
            "특정 기업 · 특정 무기체계의 취약 부품을 지목하지 않습니다. 품목군 · 군급 단위로만 집계합니다",
            "부대 위치 · 전력 수량 · 부품 구성은 수집 · 추정 · 역산하지 않습니다",
            "계약업체 주소는 생산시설 · 납품 위치가 아닙니다",
            "「잠정」 표시 값은 정제 · 산출식 확정 전입니다. 확정 뒤 표시를 뗍니다"])),
    ]))

st.html('<div class="caption">근거 문서: docs/data-sources.md · docs/reference/hs-whitelist-definition.md · '
        'docs/report/data-usage-decision-2026-09-18.md · docs/idea-review.md §3</div>')
