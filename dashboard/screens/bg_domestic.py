"""④ 4-3 국내 조달(부록) — 국내 조달은 어떤 방식으로 이뤄지나.

부록 — 근거 자료가 아니다(계약정보에 부품 연결 키가 없음). 수의계약 사유는 간접 신호일 뿐이다.
연도 선택창 — 전체 기간 또는 한 해만(계약 · 사유 = 계약연도, 개찰 결과 = 개찰연도, 공고 = 공고연도).
값: 계약 = 계약번호별 최종 차수(rds.domestic method), 사유 = 수의계약 사유 그룹(팀 분류, 경쟁계약 제외),
유찰률 = 유찰 공고 키 ÷ 공고 키. 금액은 쓰지 않는다(공고 예산 ≠ 낙찰금액 ≠ 계약금액).
"""
from __future__ import annotations

import streamlit as st

import parts as P
import rds as R
from kdesign import SERIES

SEE = "국내 계약의 방법 구성과 수의계약 사유"
SOURCE = "방위사업청 · 국내조달 계약정보 · 경쟁 입찰공고 · 입찰결과"
NOT_PRIVATE = "해당 없음(경쟁계약)"
# 계약 방법별 색 — 방법마다 다른 색. 오른쪽 「수의계약 사유」 막대는 모두 수의계약 색으로 통일한다
METHOD_COLOR = {"수의계약": SERIES[3], "일반경쟁": SERIES[0], "제한경쟁": SERIES[2], "협상": SERIES[1], "2단계": SERIES[4], "지명경쟁": SERIES[5]}   # 수의계약 = 보라


def method_color(name: str) -> str:
    """계약 방법 이름 → 색. 「협상에의한계약(전자)」 · 「2단계경쟁(동시)」처럼 뒤에 말이 붙어도 같은 종류는 같은 색."""
    return next((c for k, c in METHOD_COLOR.items() if name.startswith(k)), "#c3cede")


# 개찰 결과별 색 — 유찰은 수의계약(보라)과 겹치지 않게 분홍
BID_COLOR = {"개찰완료": SERIES[0], "유찰": SERIES[4], "순위확정": SERIES[1]}


def bid_color(name: str) -> str:
    """개찰 결과 이름 → 색. 「개찰완료(낙찰)」처럼 뒤에 말이 붙어도 같은 색."""
    return next((c for k, c in BID_COLOR.items() if name.startswith(k)), "#c3cede")


ys = R.domestic_years()
span = f"{ys[0]}~{ys[-1]}" if len(ys) > 1 else str(ys[0])
ALL = "전체"
years = {ALL: None} | {str(y): y for y in ys}
st.session_state.setdefault("p43_year_btn", ALL)


def _keep_one() -> None:
    """고른 단추를 다시 눌러 풀면 「전체」로 돌아간다 — 늘 하나는 눌려 있게."""
    if st.session_state.get("p43_year_btn") not in years:
        st.session_state["p43_year_btn"] = ALL


# 군급별 국외 조달계획의 군(FSG) · 소요군 단추와 같은 모양 — 전체 · 연도별 단추(하나만 고른다)
pick = st.pills("연도", list(years), selection_mode="single", key="p43_year_btn", on_change=_keep_one) or ALL
year = years[pick]
period = f"{year or span}년"

d = R.domestic(year)
m = d["method"]
total = int(m["n"].sum())
priv = int(m.loc[m["m"] == "수의계약", "n"].sum())
bid = d["bid"].set_index("r")["keys_n"].astype(int)
fail, keys = int(bid.get("유찰", 0)), int(bid.sum())

P.lead(f'{period} 국내 계약 {total:,}건 중 <span class="key">수의계약이 {priv / total * 100:.1f}%</span>이다', "조달 계약 ≠ 방산 매출")
P.kpis([P.kpi("국내 계약", f"{total:,}", "건", f"계약번호별 최종 차수 · 계약연도 {period}"),
        P.kpi("수의계약 비중", f"{priv / total * 100:.1f}", "%", f"수의계약 {priv:,}건 · 계약 방법 기준"),
        P.kpi("경쟁 입찰공고", f"{d['notice']:,}", "건", f"국내 입찰공고 · 공고연도 {period}"),
        P.kpi("유찰률", f"{fail / keys * 100:.1f}" if keys else "—", "%", f"유찰 {fail:,} / 공고 키 {keys:,}")])

a, b, c = st.columns([1, 1.1, .75], gap="medium")   # 계약 방법 · 수의계약 사유 · 개찰 결과를 한 줄에
with a, P.card("method"):
    P.title("계약 방법 분포", f"건 · 계약 방법별 · 계약연도 {period}")
    P.chart(P.hbar([(r.m, int(r.n), method_color(r.m)) for r in m.itertuples()], "건", 300), "p43_method")
with b, P.card("reason"):
    rs = d["reason"][d["reason"]["g"] != NOT_PRIVATE]
    P.title("수의계약 사유 분포", f"건 · 사유 그룹별(팀 분류) · 경쟁계약 제외 · 계약연도 {period}")
    fig = P.hbar([(r.g, int(r.n), METHOD_COLOR["수의계약"]) for r in rs.itertuples()], "건", 300)   # 모두 수의계약의 사유 — 왼쪽 수의계약 막대와 같은 색
    fig.update_xaxes(nticks=4)   # 칸이 좁아 눈금이 많으면 글씨가 기운다
    P.chart(fig, "p43_reason")
with c, P.card("bid"):
    br = d["bid"]
    P.title("개찰 결과 분포", f"행 · 국내 경쟁입찰 개찰 결과별 · 개찰연도 {period} · 결과 {int(br['n'].sum()):,}행")
    fig = P.hbar([(r.r, int(r.n), bid_color(r.r)) for r in br.itertuples()], "행", 300)
    fig.update_traces(width=.3)   # 막대가 3개뿐이라 그대로 두면 두꺼워진다 — 옆 두 그래프 막대 굵기에 맞춘다
    P.chart(fig, "p43_bid")
P.read1("수의계약 사유는 조달 지연 · 공급자 고정의 간접 신호일 뿐, 국산화가 필요하다는 근거가 아닙니다")
P.see(SEE, SOURCE)
