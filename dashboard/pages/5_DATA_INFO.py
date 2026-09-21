"""⑤ DATA INFO — 출처 · 자료 기간 · 선정 규칙 · 지표 정의 · 과천시 소재 수입자 비중(추정) · 제외 데이터와 이유 · 과장 금지 목록.

근거 문서(문구를 바꿀 때 먼저 고친다):
- 출처 표: DB meta_dataset(= db/meta_dataset.csv) — 화면이 문서와 따로 놀지 않게 DB에서 읽는다
- 선정 규칙 R1~R4: docs/reference/hs-whitelist-definition.md §8-2 (R3∧R4 로만 진입한 품목군 = R4 잠정, metrics.r4_provisional)
- 제외 데이터: docs/report/data-usage-decision-2026-09-18.md §1 「제외」, docs/idea-review.md §2-C
- 과장 금지: docs/idea-review.md §3 유의사항
- 과천: docs/data-sources.md 「지역 통계 검증」 절 — "과천시 소재 수입자 비중(방위사업청 소재지), 추정"으로만 쓰고 하한으로 단정하지 않는다.
  수치는 시군구별 수입이 RDS 에 없어 화면에 싣지 않는다(재현: notebooks/eda_customs.ipynb §11, 채택 여부는 팀 결정).
- 건수(품목군 수 · HS6 후보 수 · B2 사업 수)는 리터럴 대신 DB 에서 읽고, 실패하면 숫자 없이 표현한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_ready, safe_query, try_query  # noqa: E402
from metrics import count_state, r4_provisional  # noqa: E402
from ui import MUTED, SHORT, zone  # noqa: E402

if not db_ready():
    st.stop()

# 건수 3종 — 캐시 밖(try_query): 실패해도 페이지는 그리고 숫자만 뺀다
rule_df, rule_err = try_query("SELECT COUNT(*) AS n FROM ref_hs_rule_flag")
wl_df, wl_err = try_query("SELECT hs6, name_ko, evidence FROM ref_hs_whitelist WHERE evidence_basis = 'rule' ORDER BY hs6")
b2_df, b2_err = try_query("SELECT COUNT(DISTINCT project_name) AS n FROM clean_dapa_localized_item")
st_rule, n_rule = count_state(rule_df, rule_err, "n")
st_b2, n_b2 = count_state(b2_df, b2_err, "n")
n_wl = len(wl_df) if wl_df is not None else None
r4_items = ([f"{r.hs6} {SHORT.get(r.hs6, r.name_ko)}" for r in wl_df.itertuples() if r4_provisional(r.evidence)]
            if wl_df is not None else [])


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
        (f"분석 대상 {n_wl if n_wl is not None else ''}품목군은 이렇게 골랐습니다".replace("  ", " "), bullets([
            (f"범위: HS 84 · 85 · 88 · 90류의 HS6 {n_rule:,}개(ref_hs_rule_flag)" if st_rule == "ok"
             else "범위: HS 84 · 85 · 88 · 90류의 HS6 전체(ref_hs_rule_flag — 건수 조회 실패)"),
            "<b>공식 자료에서 확인한 사실</b>: 관세청 분류표의 세분류 명칭(R1·R2 입력), 전략물자수출입고시 별표2 HSK 연계표(R3 입력), "
            "방사청 국산화개발품목의 군급(R4 입력)",
            "<b>팀이 정한 규칙</b>: <b>R1 군용전용</b> — 「제9301호 · 제9306호 물품 전용」 세분류가 있음 / "
            "<b>R2 항공 · 항행</b> — 「항공기용 · 항행 · 레이더 · 무인기」 세분류가 있거나 HS6 명칭에 같은 용도어 / "
            "<b>R3 이중용도</b> — 별표2 3 · 5 · 6 · 7부(전자 · 정보통신 · 센서 · 항법) 통제품목 / "
            "<b>R4 국산화 대응</b> — B2 군급 후보 대응",
            "진입 = <b>R1 또는 R2 또는 (R3 그리고 R4)</b>. R3만으로는 들어오지 않습니다",
            "<b>잠정 대응</b>: R4 는 공식 HS↔군급 연계표가 없어 후보 대응에 기댑니다(2026-09-18 대응표 미확정 결정). "
            + (f"R3∧R4 로만 진입해 R4 잠정에 기대는 품목군 <b>{len(r4_items)}개</b>: {', '.join(r4_items)}" if r4_items
               else "R3∧R4 로만 진입한 품목군 목록은 조회 실패로 표시하지 못했습니다"),
            "규칙 조합·문턱값은 공식 자료에 적용한 <b>팀의 분석 규칙</b>이며 정부 공식 목록도, 통계적 검증도 아닙니다. "
            "규칙 미해당 품목군(팀 판단, priority 3)은 분석 대상에서 빼고 배경 자료로만 둡니다"])),
        ("지표는 이렇게 계산합니다", bullets([
            "<b>수입액</b> = 관세청 품목별 국가별 수출입실적, HS10 → HS6 합산, 총계 행 제외, USD",
            "<b>1위 공급국 점유율</b> = 1위 국가 수입액 ÷ 품목군 수입액(동률이면 국가코드가 큰 쪽 — DB 뷰와 같은 규칙)",
            "<b>HHI</b> = Σ(국가별 점유율 %)², 0~10,000. 2,500 이상을 「높은 집중」으로 봅니다(미 법무부 기준)",
            "여러 해를 고르면 <b>국가별로 기간 합계</b>를 낸 뒤 점유율 · HHI를 계산합니다(연도별 값의 평균 아님). "
            "① 화면의 연도별 HHI 와 홈 · ③ · 🔎의 기간 합계 HHI 는 다른 지표입니다",
            "<b>수입국 수</b> = 그 기간 수입 실적(>0)이 있는 국가 수. 수출만 있는 국가는 세지 않습니다",
            "<b>수출/수입</b> = 같은 기간 수출액 ÷ 수입액. HS6 합계라 민수 반도체가 대부분입니다",
            "<b>특정국 50% 이상</b> = 1위 공급국 점유율 50% 이상인 품목군 수(산업부 공급망 참고선)",
            "<b>국외 조달계획 건수</b> = clean_dapa_overseas_plan_api 에서 전자 군급(FSG 58 · 59 · 60, NSN 13자 숫자 · 영숫자)으로 판정한 행 수"
            "(조달요구번호 × 품목순번). 전자 판정은 팀 확인 전 <b>잠정</b>이며 금액은 통화 미검증이라 쓰지 않습니다",
            "국가는 <b>선적국</b> 기준입니다. 원산지와 다를 수 있습니다(홍콩 · 싱가포르 경유 등)"])),
    ]))

# ── 용어 ────────────────────────────────────────────────────────────────────
with zone("p5_terms", "용어"):
    terms = pd.DataFrame([
        ("코드", "HS6 · HS10", "국제 통일 상품분류. 6자리는 세계 공통, 10자리(HSK)는 한국 세분류. 군용 · 민수를 구분하지 않습니다"),
        ("코드", "품목군", "이 대시보드에서는 HS6 하나를 품목군 하나로 부릅니다. 분석 대상은 규칙으로 고른 19개입니다"),
        ("코드", "FSG · FSC(군급)", "미 연방보급분류. FSG = 앞 2자리 그룹, FSC = 4자리 군급"),
        ("코드", "전자 군급(FSG 58 · 59)", "58 = 통신 · 탐지 및 코히런트 방사 장비, 59 = 전기 및 전자 장비 구성품"),
        ("코드", "NSN(국가재고번호)", "군수품 13자리 번호. 앞 4자리가 FSC라서 전자 군급(58 · 59) 여부를 가릴 수 있습니다"),
        ("지표", "1위 공급국 점유율", "1위 국가 수입액 ÷ 품목군 수입액"),
        ("지표", "HHI", "Σ(국가별 점유율 %)², 0~10,000. 2,500 이상 = 높은 집중. 수입 집중도이며 위험도가 아닙니다"),
        ("지표", "선적국", "관세청 통계의 국가 기준. 원산지와 다를 수 있습니다(홍콩 · 싱가포르 경유 등)"),
        ("지표", "민수 포함", "수입액 · 수출액은 국가 전체 교역액입니다. 군수 몫만 따로 떼어 낸 통계는 없습니다"),
        ("지표", "과천시 소재 수입자 비중(추정)", "수입자 소재지가 경기 과천시인 수입 비중. 군수 몫의 참고 추정치이며 DB 미적재 · 하한이라고 단정하지 않습니다"),
        ("자료", "국외 조달계획", "방위사업청이 공개하는 품목 단위 국외 조달 계획. 계획이지 계약 · 실적이 아닙니다"),
        ("자료", "국산화개발품목", "방위사업청 국산화개발 완료 부품 목록(지상 28개 사업). 부품 수이지 국산화율이 아닙니다"),
        ("표시", "부분연도", "1년이 다 차지 않은 해(2026년은 8월까지). 연간 비교 · KPI · 전년비에서 뺍니다"),
        ("표시", "잠정", "정제 · 산출식 확정 전 값. 확정 뒤 표시를 뗍니다"),
        ("표시", "후보", "공식 연계표가 없어 확정하지 않은 대응(예: HS6 ↔ 군급). 참고용이며 집계 기준으로 쓰지 않습니다"),
    ], columns=["구분", "용어", "뜻"])
    st.dataframe(terms, hide_index=True, width="stretch", height=38 + 35 * len(terms),
                 column_config={"구분": st.column_config.TextColumn(width="small"), "용어": st.column_config.TextColumn(width="medium"),
                                "뜻": st.column_config.TextColumn(width="large")})
    st.html('<div class="note">· 표 오른쪽 위 돋보기로 용어를 찾을 수 있습니다 · 계산식은 위 「지표는 이렇게 계산합니다」가 기준입니다</div>')

# ── 3. 과천시 소재 수입자 비중(추정) — 관측값과 가설을 나눠 적는다 ─────────────
with zone("p5_gc", "과천시 소재 수입자 비중(추정) — 참고"):
    st.html(cards([
        ("무엇을 관측할 수 있나", bullets([
            "관세청 <b>시군구별</b> 품목별 수출입실적(15134343)에서 수입자 소재지가 <b>경기 과천시</b>인 수입액의 비중 — "
            "관세청 명세상 「<b>납세의무자 주소지</b>」 기준이며 사용처 · 생산지가 아닙니다",
            "관측값의 이름은 「과천시 소재 수입자 비중(방위사업청 소재지), 추정」입니다(docs/data-sources.md 지역 통계 검증 절)",
            "이 자료는 팀 DB(RDS)에 <b>적재되지 않았습니다</b>. 그래서 이 화면·① · ③ 어디에도 수치를 싣지 않습니다",
            "재현 경로: 시군구별 CSV(2016~2026) → docs/data-sources.md 지역 통계 검증 절(HS6별, 2025) · "
            "notebooks/eda_customs.ipynb §11(분류별, 2025). 분모는 각각 HS6 수입액 · 분류 수입액으로 다릅니다"])),
        ("왜 「군 직접 수입의 하한」이라고 쓰지 않나", bullets([
            "과천에 방위사업청(정부과천청사)과 국군수송사령부가 있다는 것은 사실이지만, 수입신고의 납세의무자가 실제로 그 기관인지는 "
            "공개 자료로 확인되지 않았습니다 — 이 부분은 <b>가설</b>입니다",
            "과천 소재 <b>민간 수입자</b>가 섞일 수 있어 비중이 군 몫보다 클 수 있고, 관세법 §92 위탁 업체 명의(창원 · 사천 등)로 들어오는 "
            "군수품은 빠져 작을 수도 있습니다 → 어느 쪽으로도 치우칠 수 있으므로 <b>하한도 상한도 아닙니다</b>",
            "채택 여부 · RDS 적재는 팀 결정 사항(2026-09-21 회의 안건: 보류 · 쓰더라도 보조 설명). 확정되기 전에는 관측값과 가설을 나눠 적습니다",
            f'<span style="color:{MUTED}">군수 몫은 관세 통계로 나뉘지 않습니다 — 품목군 지표는 국가 전체 수입(민수 포함)입니다</span>'])),
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
            "국산화개발 부품 수는 <b>완료 부품 목록</b>" + (f"(지상 {n_b2}개 사업)" if st_b2 == "ok" else "(지상 사업 한정)")
            + "이며 국산화율이 아닙니다. 빈칸은 「국산화 안 됨」이 아니라 「이 자료에 없음」",
            "HS 품목군(관세청)과 군급(방사청)은 <b>연결하지 않습니다</b>. 특정 부품의 수입국 → 무기체계 → 국산화 상태를 잇는 설명은 이 자료로 할 수 없고, "
            "두 축을 나란히 놓을 뿐입니다"])),
        ("표현 범위", bullets([
            "특정 기업 · 특정 무기체계의 취약 부품을 지목하지 않습니다. 품목군 · 군급 단위로만 집계합니다",
            "부대 위치 · 전력 수량 · 부품 구성은 수집 · 추정 · 역산하지 않습니다",
            "계약업체 주소는 생산시설 · 납품 위치가 아닙니다",
            "「잠정」 표시 값은 정제 · 산출식 확정 전입니다. 확정 뒤 표시를 뗍니다"])),
    ]))

st.html('<div class="caption">근거 문서: docs/data-sources.md · docs/reference/hs-whitelist-definition.md · docs/reference/data-cleaning-rules.md §2-6 · '
        'docs/report/data-usage-decision-2026-09-18.md · docs/idea-review.md §3 · 지표 검토 docs/report/app-metrics-review-2026-09-20.md</div>')
