"""④ 4-3 국내 조달(부록) — 국내 조달은 어떤 방식으로 이뤄지나.

부록 — 근거 자료가 아니다(계약정보에 부품 연결 키가 없음). 수의계약 사유는 간접 신호일 뿐이다.
값: 계약 = 계약번호별 최종 차수(rds.domestic method), 사유 = 수의계약 사유 그룹(팀 분류, 경쟁계약 제외),
유찰률 = 유찰 공고 키 ÷ 공고 키. 금액은 쓰지 않는다(공고 예산 ≠ 낙찰금액 ≠ 계약금액).
"""
from __future__ import annotations

import streamlit as st

import parts as P
import rds as R

SEE = "국내 계약의 방법 구성과 수의계약 사유"
SOURCE = "방위사업청 · 국내조달 계약정보 · 경쟁 입찰공고 · 입찰결과"
NOT_PRIVATE = "해당 없음(경쟁계약)"

d = R.domestic()
m = d["method"]
total = int(m["n"].sum())
priv = int(m.loc[m["m"] == "수의계약", "n"].sum())
bid = d["bid"].set_index("r")["keys_n"].astype(int)
fail, keys = int(bid.get("유찰", 0)), int(bid.sum())

st.html('<span class="bdg appx">부록 — 이 화면은 근거 자료가 아니라 조달 방식의 배경입니다(계약정보에 부품 연결 키가 없음)</span>')
P.lead(f'국내 계약 {total:,}건 중 <span class="key">수의계약이 {priv / total * 100:.1f}%</span>다', "건 · 계약 방법별 · 조달 계약 ≠ 방산 매출")
P.kpis([P.kpi("국내 계약", f"{total:,}", "건", "계약번호별 최종 차수"),
        P.kpi("수의계약 비중", f"{priv / total * 100:.1f}", "%", f"수의계약 {priv:,}건 · 계약 방법 기준"),
        P.kpi("경쟁 입찰공고", f"{d['notice']:,}", "건", "국내 입찰공고"),
        P.kpi("유찰률", f"{fail / keys * 100:.1f}" if keys else "—", "%", f"유찰 {fail:,} / 공고 키 {keys:,}")])

a, b = st.columns(2, gap="medium")
with a, P.card("method"):
    P.title(f'계약 방법 1위는 <span class="key">{m.iloc[0]["m"]}</span>', "건 · 계약 방법별")
    P.chart(P.hbar([(r.m, int(r.n), "#2b6ef6" if r.m == "수의계약" else "#c3cede") for r in m.itertuples()], "건", 300), "p43_method")
with b, P.card("reason"):
    rs = d["reason"][d["reason"]["g"] != NOT_PRIVATE]
    P.title(f'수의계약 사유 1위는 <span class="key">{rs.iloc[0]["g"]}</span>', "건 · 사유 그룹별(팀 분류) · 경쟁계약 제외")
    P.chart(P.hbar([(r.g, int(r.n), "#7c6cf0") for r in rs.itertuples()], "건", 300), "p43_reason")
P.read1("수의계약 사유는 조달 지연 · 공급자 고정의 간접 신호일 뿐, 국산화가 필요하다는 근거가 아닙니다")
P.see(SEE, SOURCE)
