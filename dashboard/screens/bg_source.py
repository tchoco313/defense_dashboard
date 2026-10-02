"""④ 4-4 데이터 출처 · 검증 — 숫자는 어디서 왔고 무엇을 뜻하지 않는가.

시각화 도구는 ①②③ 「상세 조회」에 있고, 여기에는 출처 · 검증 · 한계만 둔다.
값: 출처 표 = 데이터셋 기록(rds.sources — 원본 건수는 실제 내려받아 파서로 센 행 수), 결합 검증 = 입찰 공고 ↔ 결과 대조(rds.bid_match).
"""
from __future__ import annotations

from html import escape

import streamlit as st

import pandas as pd

import parts as P
import rds as R

NOT_SAY = [
    ("군수 몫을 말하지 않습니다", "관세청 수입액은 국가 전체 수입(민수 포함)이며 HS 코드만으로 군용 · 민수용을 나눌 수 없습니다."),
    ("원산지를 말하지 않습니다", "국가는 관세청 통계의 선적국입니다."),
    ("국산화율을 말하지 않습니다", "국산화 완료 부품 수만 있고, 필요한 전체 부품 수(분모)는 공개되지 않았습니다."),
    ("우선순위를 확정하지 않습니다", "현황표는 추가 검토 목록이며, 수입액과 조달 예산은 합하거나 직접 비교하지 않습니다."),
]

src = R.sources()
n_of = dict(zip(src["dataset_key"], src["raw_row_count"]))


def period(r) -> str:
    s0, s1 = r.period_start, r.period_end
    if pd.isna(s0) and pd.isna(s1):
        return "기준일 미표기"
    txt = (f"{pd.Timestamp(s0):%Y.%m}" if pd.notna(s0) else "") + "~" + (f"{pd.Timestamp(s1):%Y.%m}" if pd.notna(s1) else "")
    return txt + (" (부분)" if int(r.is_partial_period or 0) else "")


P.lead(f'대시보드의 숫자는 <span class="key">공개 데이터 {len(src)}종</span>에서 왔고, '
       "1만 건 요건은 관세청 · 국산화개발품목 2종으로 채웁니다",
       f"원본 건수 = 실제 내려받아 센 행 수 · 관세청 {int(n_of.get('customs_all', 0)):,} + "
       f"국산화개발품목 {int(n_of.get('dapa_localized_item', 0)):,}")
with P.card("src"):
    P.title("데이터 출처", "기관 · 데이터명 · 원본 건수 · 자료 기간 · 쓰인 곳")
    head = "".join(f"<th>{h}</th>" for h in ("기관", "데이터명", "원본 건수", "자료 기간", "쓰인 곳"))
    body = "".join(
        f"<tr><td class='l'>{escape(str(r.provider))}</td><td class='l'>{escape(str(r.title).split(' (')[0])}</td>"
        f"<td>{int(r.raw_row_count):,}행</td>"
        f"<td>{period(r)}</td><td class='l'>{escape(str(r.use))}</td></tr>" for r in src.itertuples())
    st.html(f'<div style="overflow-x:auto"><table class="pt"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
with P.card("notsay"):
    P.title("이 대시보드가 말하지 않는 것")
    st.html("".join(f'<div class="rule"><span class="ck">✓</span><div><b>{t}</b><span>{d}</span></div></div>' for t, d in NOT_SAY))
P.see("숫자의 출처와 해석 경계", "각 기관 공개 자료 · 공공데이터포털 데이터 ID 기준")

with P.more("데이터 결합 검증 — 입찰 공고 ↔ 결과"):
    bm = R.bid_match()
    rate = bm["n_linked"] / bm["n_result"] * 100 if bm["n_result"] else 0
    st.html(f'<b>입찰 공고</b> {bm["n_notice"]:,}행 · <b>입찰 결과</b> {bm["n_result"]:,}행 → '
            f'<b>공고와 연결된 결과</b> {bm["n_linked"]:,}행({rate:.1f}%) · 그중 1:1 {bm["n_one"]:,}행 · '
            f'미연결 {bm["n_result"] - bm["n_linked"]:,}행'
            '<div class="caption">공고번호 + 차수로 대조한 결과입니다. 미연결 · 다중 일치를 그대로 보고하며 성공으로 꾸미지 않습니다.</div>')
with P.more("계산 방법 · 용어"):
    st.markdown("- **HHI** = 국가별 점유율(%) 제곱 합 · **1위 공급국 점유율** = 가장 큰 선적국 비중\n"
                "- **군급(FSC)** = 군수품 4자리 분류 · 앞 2자리 = **군(FSG)**\n- **전자 군급** = 군 58 · 59 · 60에 속한 군급")

P.next_link("bg-source")
