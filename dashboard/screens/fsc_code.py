"""② 2-1 군급코드란 — 군(FSG) · 군급(FSC)은 무엇이고 어떤 관계인가.

용어: 군급 = 4자리 FSC, 앞 2자리 = 군(FSG), 뒤 2자리 = 급(Class). HS 품목군과는 코드로 잇지 않는다.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R

LEAD = ('군수품은 4자리 <span class="key">군급(FSC)</span>으로 분류되고, 앞 2자리가 <span class="key">군(FSG)</span>이다. '
        "전자 관련 군은 58 · 59 · 60, 그 아래 군급은 {n}개다")
BASIS = [  # 우리나라 분류 기준(근거 표)
    "군급분류(FSC)는 군수품을 기능별로 나누는 4자리 코드입니다. 앞 2자리는 군(Group), 뒤 2자리는 급(Class)이며, 재고번호 13자리의 앞 4자리입니다.",
    "재고번호 13자리는 군급 4자리와 품목식별번호 9자리(국가부호 2자리 + 일련번호 7자리)로 이루어지며, 우리나라 국가부호는 37입니다.",
    "방위사업청은 방위사업법에 따라 군수품에 품명과 재고번호를 부여해 목록으로 관리하며, NATO 목록체계의 후원 2단계(Tier 2) 국가로서 "
    "이 체계에 따라 목록화합니다(방위사업청 발표 기준).",
]
BASIS_SRC = "방위사업청 · 군급분류집(2025-12-31 기준) / 국방부 · 군수품관리 훈령"
SEE = "군 → 군급 → 재고번호의 관계와 전자 관련 군 3개 아래의 군급"
SOURCE = "방위사업청 · 군급분류집 · 국외 조달계획(품목)"

CSS = """<style>
.nsn{display:flex;flex-direction:column;gap:8px;margin:6px 0 4px}
.nsn-row{display:flex;gap:6px}
.nb{flex:1;text-align:center;border-radius:8px;padding:12px 4px 10px;color:#fff}
.nb b{display:block;font-size:30px;font-weight:900;letter-spacing:1px;font-variant-numeric:tabular-nums}
.nb small{display:block;font-size:12px;font-weight:700;opacity:.92;margin-top:2px}
.nb.g{background:#1d4ed8} .nb.c{background:#5b8def} .nb.n{background:#17a597} .nb.s{background:#94a3b8;flex:2.2}
.nsn-br{display:flex;gap:6px;font-size:12.5px;font-weight:800;color:#33415c;text-align:center}
.nsn-br span{border-top:2px solid #33415c;padding-top:5px}
.nsn-cap{font-size:13px;color:#5b6b88;line-height:1.6;text-align:center}
.basis{margin:12px 0 0;padding:0;list-style:none} .basis li{font-size:14px;color:#1b2540;line-height:1.65;padding:6px 0 6px 18px;
  position:relative;border-top:1px dashed #dde5f2} .basis li::before{content:"";position:absolute;left:3px;top:15px;width:6px;height:6px;
  border-radius:50%;background:#1d4ed8}
/* 출처 줄은 카드 맨 아래에 — 이 HTML 칸이 카드의 남는 높이를 채우게 하고(flex), 출처를 바닥으로 민다(오른쪽 카드의 맨 아래 글씨와 같은 높이) */
[data-testid="stElementContainer"]:has(> .stHtml > .basis-src){flex:1 1 auto;display:flex;flex-direction:column}
.stHtml:has(> .basis-src){flex:1 1 auto;display:flex;flex-direction:column}
.basis-src{font-size:12.5px;color:#7a879e;margin-top:auto;padding-top:18px}
.basis-h{display:flex;align-items:center;gap:7px;margin:34px 0 0;font-size:15px;font-weight:800;color:#12234a}
.basis-h .ms{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;font-size:21px;line-height:1;color:#1d4ed8}
.basis-h + .basis{margin-top:8px}
</style>"""
st.html(CSS)

ref = R.fsc_ref()
fsg_name = R.fsg_names()
plan_n = R.plan().groupby("fsc4").size()
by_g = ref.groupby("fsg").size()
P.lead(LEAD.format(n=len(ref)), "공식 표기: 군급 = 4자리 FSC · 군 = 앞 2자리 FSG · HS 품목군(①)과는 서로 대응표가 없어 코드로 잇지 않습니다")

a, b = st.columns([1, 1.15], gap="medium")
with a, st.container(border=True, key="card_nsn", height="stretch"):
    P.title("재고번호(NSN) 13자리 안의 군급", f"예시 = 5962(군 59 · 급 62, {R.fsc_names().get('5962', '')}) · 일련번호는 가림")
    st.html('<div class="nsn"><div class="nsn-row">'
            '<div class="nb g"><b>59</b><small>군<br>Group(FSG)</small></div>'
            '<div class="nb c"><b>62</b><small>급<br>Class</small></div>'
            '<div class="nb n"><b>37</b><small>국가부호<br>(대한민국)</small></div>'
            '<div class="nb s"><b>xxx-xxxx</b><small>일련번호 7자리</small></div></div>'
            '<div class="nsn-br"><span style="flex:2">군급(FSC) 4자리</span><span style="flex:3.2">품목식별번호(NIIN) 9자리</span></div>'
            '</div><div class="basis-h"><span class="ms">account_tree</span>FSG · FSC 분류 기준</div>'
            '<ul class="basis">' + "".join(f"<li>{x}</li>" for x in BASIS) + "</ul>"
            f'<div class="basis-src">출처: {BASIS_SRC}</div>')
with b, st.container(border=True, key="card_sun", height="stretch"):       # 왼쪽 카드와 높이를 맞춘다
    ttl = st.empty()          # 제목 자리(「보기」 라벨 대신) — 부제는 고른 보기에 따라 아래에서 채운다
    mode = st.segmented_control("보기", ["분류 체계", "조달계획 건수"], default="분류 체계", key="p21_mode",
                                label_visibility="collapsed") or "분류 체계"
    ids, labels, parents, values, colors, hover = [], [], [], [], [], []
    for g in R.FSGS:
        rows = ref[ref["fsg"] == g]
        if mode != "분류 체계":
            rows = rows[rows["fsc4"].map(plan_n).fillna(0) > 0]
        vals = {r.fsc4: (1 if mode == "분류 체계" else int(plan_n[r.fsc4])) for r in rows.itertuples()}
        if not vals:
            continue
        ids.append(g); labels.append(f"군 {g}"); parents.append(""); values.append(sum(vals.values()))
        colors.append(R.FSG_COLOR[g]); hover.append(fsg_name[g])
        for r in rows.itertuples():
            ids.append(r.fsc4); labels.append(r.fsc4); parents.append(g); values.append(vals[r.fsc4])
            colors.append("#e5e9f0" if r.closed else R.FSG_COLOR[g] + "99")
            hover.append(r.name + (" (폐지)" if r.closed else ""))
    if mode == "분류 체계":
        gmax = by_g.idxmax()
        cap = f'전자 관련 군 3개 아래 군급 {len(ref)}개 — <span class="key">군 {gmax}가 {int(by_g[gmax])}개</span>로 가장 많다'
        with ttl.container():
            P.title("군급 분류 체계",
                    f"안쪽 = 군(FSG 2자리) · 바깥 = 군급(FSC 4자리) · 칸 크기 같음 · 회색 = 폐지 {int(ref['closed'].sum())}개 · 안쪽 · 바깥 어느 칸이든 누르면 그 군만 펼치기")
    else:
        pg = R.plan().groupby("fsg").size()
        cap = f'국외 조달계획 {int(pg.sum()):,}건 중 <span class="key">군 {pg.idxmax()}가 {int(pg.max()):,}건</span>으로 가장 많다'
        with ttl.container():
            P.title("군급 분류 체계",
                    "안쪽 = 군 · 바깥 = 군급 · 칸 크기 = 국외 조달계획 건수(0건 군급은 빠짐)")
    fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                                marker=dict(colors=colors, line=dict(color="#fff", width=1)),
                                customdata=hover, insidetextorientation="auto", textfont=dict(color="#111827"),   # 칸 안 글씨는 검정(10-01 사용자)
                                hovertemplate="%{label} %{customdata}<br>%{value:,}<extra></extra>"))
    fig.update_layout(height=444, margin=dict(l=0, r=0, t=4, b=20))   # 고리 아래에 여백 — 카드 바닥에 붙어 보이지 않게
    P.chart(fig, "p21_sun")
    P.caption(cap)
    P.ring_hint("card_sun")      # 바깥 칸도 눌리게 + 안내 딱지
P.see(SEE, SOURCE)

with P.more("HS와 군급은 무엇이 다른가 — 같은 전자부품을 보는 두 공식 분류"):
    st.html('<table class="pt"><thead><tr><th></th><th>HS(관세 · 무역 통계)</th><th>군급(군수품 분류)</th></tr></thead><tbody>'
            '<tr><td>누가 쓰나</td><td class="l">관세청 수출입 통계</td><td class="l">국방 군수품 목록 · 조달</td></tr>'
            '<tr><td>무엇으로 나누나</td><td class="l">품목의 성질 · 재질 · 용도</td><td class="l">보급 관리를 위한 기능 분류</td></tr>'
            '<tr><td>자릿수</td><td class="l">국제 6자리 + 국내 10자리</td><td class="l">군 2 · 군급 4 · 재고번호 13</td></tr>'
            '<tr><td>이 대시보드에서</td><td class="l">① 부품 현황(13개 품목군)</td><td class="l">② 군급 분류와 조달 · ③ 국산화 현황</td></tr>'
            '</tbody></table><div class="caption">두 분류 사이에 공식 대응표가 없어 품목끼리 짝짓지 않습니다.</div>')
with P.more("전자 군급은 이렇게 셌다"):
    st.html(" → ".join(f"<b>{n:,}</b> {name}" for name, n in R.plan_funnel())
            + '<div class="caption">전자 군급 = 군 58 · 59 · 60에 속한 군급 · 조달계획은 건수만(금액 통화 미확인)</div>')
