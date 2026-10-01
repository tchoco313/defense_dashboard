"""④ 4-1 정책 · 예산 배경 — 정책은 어떻게 흘러왔고 예산은 어떻게 바뀌었나.

첫 화면은 흐름(타임라인)이 먼저, 숫자 카드는 두지 않는다.
값: 정책 연표 · 인용 수치 · 과제 · 7대 유형 = 발전전략 참조표(rds.policy · quotes · strategy_tasks · chip_types),
국외조달 계획 예산 = 방위사업청 국외조달 계획(원화 계획액, rds.overseas_budget), R&D 예산 = 열린재정 세부사업(rds.rnd_budget).
원화 예산은 관세청 수입액(달러)과 합산 · 비교하지 않는다.
"""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R
from kdesign import ETC, SERIES

LEAD = '국방 전자부품 · 반도체 국산화는 <span class="key">2024년 발전전략 이후 법과 예산</span>으로 이어지고 있다'
SEE = "국방반도체 정책 흐름과 국외조달 계획 예산 추이"
SOURCE = "방위사업청 · 국방반도체 발전전략(2024-11) · 국외조달 계획 / 열린재정 · 세부사업 예산"


def won(eok: float) -> str:
    """억 원 값 → 「4조 9,413억 원」(1만 억 이상은 조 단위로 끊어 읽는다). 1조 미만은 「9,413억 원」."""
    n = int(round(eok))
    jo, rest = divmod(abs(n), 10000)
    txt = (f"{jo:,}조" + (f" {rest:,}억" if rest else "")) if jo else f"{rest:,}억"
    return ("-" if n < 0 else "") + txt + " 원"


TOP_TYPES = 5            # 집행유형은 전체 계획 예산 큰 순 5개 + 그 밖(「기타」 유형 포함)

st.html("""<style>
.tl2{display:flex;position:relative;margin:4px 0 2px}
.tl2::before{content:"";position:absolute;left:5%;right:5%;top:10px;height:2px;background:#c9d6ee}
.tl2 div{flex:1;text-align:center;position:relative}
.tl2 div::before{content:"";display:block;width:14px;height:14px;border-radius:50%;background:#1d4ed8;margin:4px auto 10px;border:3px solid #dbe6fb}
.tl2 div.gov::before{background:#9db7ef}
.tl2 b{display:block;font-size:15px;font-weight:800;color:#0b1f4d} .tl2 i{display:block;font-style:normal;font-size:12px;font-weight:700;color:#1d4ed8}
.tl2 span{display:block;font-size:13px;color:#44567a;line-height:1.5;padding:0 6px;word-break:keep-all}
.qts{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}
.qts div{flex:1;min-width:220px;border:1px solid #f1d58a;background:#fffaf0;border-radius:8px;padding:10px 14px}
.qts b{font-size:22px;color:#0b1f4d} .qts small{font-size:13px;color:#5b6b88}
.qts .ex{font-size:11px;font-weight:800;color:#9a5b00;background:#fff4e5;padding:2px 7px;border-radius:10px;margin-right:6px}
</style>""")

P.lead(LEAD, "정책 흐름이 먼저, 예산은 그 흐름을 뒷받침하는 배경입니다 — 관세청 수입액과 합산 · 비교하지 않습니다")
key = R.policy_key()
qs = R.quotes()
with P.card("tl"):
    P.title("국방반도체 정책 흐름", f"대표 {len(key)}점(조사 · 전략 · 과제 · 법 · 예산) · 논의 · 조직 등 나머지는 「자세히 보기」")
    pts = "".join(f'<div class="{"gov" if r.category == "예산" else ""}"><b>{escape(r.date[:7])}</b><i>{escape(r.category)}</i>'
                  f'<span>{escape(r.event)}{" (정부안)" if r.category == "예산" and "정부안" not in r.event else ""}</span></div>'
                  for r in key.itertuples())
    quotes = "".join(f'<div><span class="ex">인용</span><small>{escape(n)}</small><br><b>{escape(v)}</b><small>{escape(u)}</small></div>'
                     for n, v, u, _ in qs)
    st.html(f'<div class="tl2">{pts}</div><div class="qts">{quotes}</div>'
            f'<div class="caption">인용 수치는 {escape(qs[0][3] if qs else "방위사업청 「국방반도체 발전전략」")} 값 — 팀이 계산한 값이 아니며 '
            '분모 기준(종류 · 수량 · 금액)은 공개되지 않았습니다.</div>')

bud = R.overseas_budget()
rank = (bud[bud["exec_type"] != "기타"].groupby("exec_type")["eok"].sum().sort_values(ascending=False).index[:TOP_TYPES].tolist())
bud = bud.assign(t=bud["exec_type"].where(bud["exec_type"].isin(rank), "그 밖"))
wide = bud.pivot_table(index="plan_year", columns="t", values="eok", aggfunc="sum", fill_value=0)
order = rank + (["그 밖"] if "그 밖" in wide.columns else [])
color = {t: SERIES[i] for i, t in enumerate(rank)} | {"그 밖": ETC}
last_y = int(wide.index.max())
with P.card("bud"):
    P.title(f'{last_y}년 국외조달 계획 예산은 <span class="key">{won(wide.loc[last_y].sum())}</span>',
            f"조 · 억 원 · 계획(집행 예정액, 원화) · 계획연도 {int(wide.index.min())}~{last_y} · 집행유형별 쌓은 막대 · 상위 {TOP_TYPES}개 + 그 밖")
    fig = go.Figure()
    for t in order:
        fig.add_trace(go.Bar(x=list(wide.index), y=wide[t].round(0).tolist(), name=t, marker_color=color[t],
                             customdata=[won(v) for v in wide[t]],
                             hovertemplate=f"{t} · %{{x}}년 %{{customdata}}<extra></extra>"))
    fig.update_layout(barmode="stack", height=320)
    fig.update_xaxes(dtick=1)
    top = float(wide[order].sum(axis=1).max())                    # 세로축 눈금도 조 단위로(10,000억 = 1조)
    step = 10000 if top <= 80000 else 20000
    ticks = list(range(0, int(top) + step, step))
    fig.update_yaxes(tickvals=ticks, ticktext=["0"] + [f"{v // 10000}조" for v in ticks[1:]])
    P.chart(fig, "p41_bud")
P.see(SEE, SOURCE)

with P.more("국방 R&D 세부사업 예산 — 부품국산화 · 국방반도체"):
    rd = R.rnd_budget()
    rd = rd[(rd["loc"] > 0) | (rd["semi"] > 0)]
    op = [1 if b == "확정" else .45 for b in rd["basis"]]
    fig = go.Figure()
    for col_, name, c in (("loc", "부품국산화", "#2b6ef6"), ("semi", "국방반도체", "#ff9f43")):
        fig.add_trace(go.Bar(x=rd["year"], y=rd[col_].round(0), name=name, marker=dict(color=c, opacity=op),
                             customdata=[won(v) for v in rd[col_]],
                             hovertemplate=f"{name} · %{{x}}년 %{{customdata}}<extra></extra>"))
    fig.update_layout(barmode="group", height=280)
    fig.update_xaxes(dtick=1)
    P.chart(fig, "p41_rd")
    gov = rd.loc[rd["basis"] != "확정", "year"].tolist()
    st.html(f'<div class="caption">억 원 · 정부 예산 · {"·".join(map(str, gov))}년 = 정부안(흐린 막대) · '
            '열린재정 세부사업 예산 · 0인 해(편성 전)는 뺐습니다</div>')
with P.more("국외조달 절차 — 계획 → 입찰 → 계약"):
    pr = R.procedure()
    st.html(f'<b>계획</b> {int(pr["plan_n"]):,}건({pr["plan_y0"]}~{pr["plan_y1"]}) → '
            f'<b>입찰 결과</b> {int(pr["bid_n"]):,}건({pr["bid_y0"]}~{pr["bid_y1"]}) → '
            f'<b>계약</b> {int(pr["ctr_n"]):,}건({pr["ctr_y0"]}~{pr["ctr_y1"]})'
            '<div class="caption">단계마다 자료 · 기간 · 단위가 달라 건수를 이어 붙이거나 전환율로 읽지 않습니다.</div>')
with P.more("발전전략 4방향 12과제 · 국방반도체 수요 7대 유형"):
    tk = R.strategy_tasks()
    rows = "".join(f"<tr><td>{r.task_no}</td><td class='l'>{escape(r.direction_name)}</td><td class='l'>{escape(r.task_name)}</td></tr>"
                   for r in tk.itertuples())
    st.html(f'<table class="pt"><thead><tr><th>과제</th><th>방향</th><th>과제명</th></tr></thead><tbody>{rows}</tbody></table>')
    ct = R.chip_types()
    rows = "".join(f"<tr><td>{r.type_no}</td><td class='l'><b>{escape(r.name_ko)}</b></td><td class='l'>{escape(r.summary)}</td></tr>"
                   for r in ct.itertuples())
    st.html(f'<table class="pt" style="margin-top:14px"><thead><tr><th>유형</th><th>이름</th><th>설명</th></tr></thead><tbody>{rows}</tbody></table>'
            '<div class="caption">방위사업청 「국방반도체 발전전략」(2024-11) 본문을 옮긴 참조표 · 정책 연표 전체는 아래</div>')
    allp = R.policy()
    rows = "".join(f"<tr><td>{escape(r.date)}</td><td>{escape(r.category)}</td><td class='l'>{escape(r.event)}</td>"
                   f"<td class='l'>{escape(r.source_title)}</td></tr>" for r in allp.itertuples())
    st.html(f'<table class="pt" style="margin-top:14px"><thead><tr><th>날짜</th><th>분류</th><th>내용</th><th>출처</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')
