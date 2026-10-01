"""① 1-0 HS코드란 — HS(류 · 호 · 소호)는 무엇이고 13개 품목군은 그 안의 어디인가(② 군급코드란과 짝이 되는 화면, 2026-10-01 신규).

용어: HS = 세계관세기구(WCO) 국제통일상품분류. 앞 6자리(류 2 · 호 4 · 소호 6)가 국제 공통이고, 우리나라는 여기에 4자리를 붙인
10자리(HSK)를 쓴다. 이 대시보드의 「품목군」 = HS 6자리 한 개. 군급(FSC)과는 코드로 잇지 않는다.
"""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

import parts as P
import rds as R

LEAD = ('무역 통계는 품목을 <span class="key">HS 코드</span>로 나눈다. 앞 6자리가 국제 공통이고, '
        '이 대시보드의 품목군 {n}개는 <span class="key">HS 6자리 {n}개</span>다')
BASIS = [
    "HS(Harmonized System)는 세계관세기구(WCO)가 정한 국제통일상품분류입니다. 앞 2자리는 류(Chapter), 4자리는 호(Heading), "
    "6자리는 소호(Subheading)이며, 6자리까지는 모든 나라가 같은 코드를 씁니다.",
    "우리나라는 6자리 뒤에 4자리를 더 붙인 10자리(HSK · 관세통계통합품목분류표)로 수출입을 신고하고 통계를 냅니다.",
    "이 대시보드는 나라끼리 견줄 수 있는 6자리를 품목군 하나로 보고, 선정 근거는 10자리 세분류 이름"
    "(군용 전용 · 항공기용 · 항행 · 레이더 등)에서 찾았습니다.",
]
BASIS_SRC = "관세청 · HS부호 마스터 / 세계관세기구(WCO) 국제통일상품분류"
SEE = "류 → 호 → 소호의 관계와 분석 대상 13개 품목군이 속한 류"
SOURCE = "관세청 · HS부호 마스터 · 품목별 국가별 수출입실적"
CHAPTER = {"84": "기계류", "85": "전기 · 전자기기", "88": "항공기 · 부분품", "90": "광학 · 측정 · 항행기기"}
CH_COLOR = {"84": "#f59e0b", "85": "#1d4ed8", "88": "#7c6cf0", "90": "#17a597"}
EX = "854231"   # 예시 품목군 — 프로세서 IC

# 자릿수 블록 · 근거 목록 모양은 ② 군급코드란(fsc_code.py)과 같다
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

it = R.items()
by = R.base_year()
imp = R.conc((by,)).set_index("hs6")["total"] / R.E8          # 품목군별 기준 연도 수입액(억 달러)
it = it.assign(ch=it["hs6"].str[:2])
by_ch = it.groupby("ch").size()
ex_name = dict(zip(it["hs6"], it["short"])).get(EX, "")
P.lead(LEAD.format(n=len(it)), "공식 표기: 류 = 앞 2자리 · 호 = 4자리 · 소호 = 6자리 · 군급(FSC)과는 서로 대응표가 없어 코드로 잇지 않습니다")

a, b = st.columns([1, 1.15], gap="medium")
with a, st.container(border=True, key="card_hsd", height="stretch"):
    P.title("HS 코드 10자리 안의 품목군", f"예시 = {EX[:4]}.{EX[4:]}(류 {EX[:2]} · 호 {EX[:4]}, {escape(ex_name)}) · 뒤 4자리는 가림")
    st.html('<div class="nsn"><div class="nsn-row">'
            f'<div class="nb g"><b>{EX[:2]}</b><small>류<br>Chapter</small></div>'
            f'<div class="nb c"><b>{EX[2:4]}</b><small>호<br>Heading</small></div>'
            f'<div class="nb n"><b>{EX[4:]}</b><small>소호<br>Subheading</small></div>'
            '<div class="nb s"><b>xxxx</b><small>국내 세분류 4자리(HSK)</small></div></div>'
            '<div class="nsn-br"><span style="flex:3.1">HS 6자리 — 국제 공통(= 품목군 하나)</span><span style="flex:2.2">우리나라만</span></div>'
            '</div><div class="basis-h"><span class="ms">account_tree</span>무역 통계 분류 기준</div>'
            '<ul class="basis">' + "".join(f"<li>{x}</li>" for x in BASIS) + "</ul>"
            f'<div class="basis-src">출처: {BASIS_SRC}</div>')
with b, st.container(border=True, key="card_hsun", height="stretch"):      # 왼쪽 카드와 높이를 맞춘다
    ttl = st.empty()          # 제목 자리(「보기」 라벨 대신) — 부제는 고른 보기에 따라 아래에서 채운다
    mode = st.segmented_control("보기", ["분류 체계", "수입액"], default="분류 체계", key="p10_mode",
                                label_visibility="collapsed") or "분류 체계"
    ids, labels, parents, values, colors, hover = [], [], [], [], [], []
    for ch, rows in it.groupby("ch"):
        vals = {r.hs6: (1 if mode == "분류 체계" else round(float(imp.get(r.hs6, 0) or 0), 2)) for r in rows.itertuples()}
        ids.append(ch); labels.append(f"{ch}류"); parents.append(""); values.append(sum(vals.values()))
        colors.append(CH_COLOR.get(ch, "#94a3b8")); hover.append(CHAPTER.get(ch, ""))
        for r in rows.itertuples():
            name = r.short.replace(" ", "<br>") if len(r.short) >= 8 else r.short   # 긴 이름은 줄을 나눠 가로로 들어가게
            ids.append(r.hs6); labels.append(f"{r.hs6}<br>{name}"); parents.append(ch); values.append(vals[r.hs6])
            colors.append(CH_COLOR.get(ch, "#94a3b8") + "99"); hover.append(r.name_ko)
    if mode == "분류 체계":
        cmax = by_ch.idxmax()
        cap = f'분석 대상 {len(it)}개 품목군은 류 {len(by_ch)}개에 걸쳐 있다 — <span class="key">{cmax}류가 {int(by_ch[cmax])}개</span>로 가장 많다'
        with ttl.container():
            P.title("품목군의 HS 분류 체계", "안쪽 = 류(HS 2자리) · 바깥 = 품목군(HS 6자리) · 칸 크기 같음 · 안쪽 · 바깥 어느 칸이든 누르면 그 류만 펼치기")
    else:
        tot = imp.reindex(it["hs6"]).fillna(0)
        top = tot.idxmax()
        cap = (f'{by}년 수입액 {tot.sum():,.1f}억 달러 중 <span class="key">{escape(dict(zip(it["hs6"], it["short"]))[top])}가 '
               f'{tot.max():,.1f}억 달러</span>로 가장 많다')
        with ttl.container():
            P.title("품목군의 HS 분류 체계", f"안쪽 = 류 · 바깥 = 품목군 · 칸 크기 = {by}년 수입액(억 달러 · 국가 전체 수입 · 민수 포함)")
    fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                                marker=dict(colors=colors, line=dict(color="#fff", width=1)),
                                customdata=hover, insidetextorientation="horizontal", textfont=dict(color="#111827"),   # 칸 안 글씨는 검정(10-01 사용자)
                                hovertemplate="%{label} %{customdata}<br>%{value:,}<extra></extra>"))
    fig.update_layout(height=444, margin=dict(l=0, r=0, t=4, b=20))   # 고리 아래에 여백 — 카드 바닥에 붙어 보이지 않게
    P.chart(fig, "p10_sun")
    P.caption(cap)
    P.ring_hint("card_hsun")      # 바깥 칸도 눌리게 + 안내 딱지
P.see(SEE, SOURCE)

with P.more("HS와 군급은 무엇이 다른가 — 같은 전자부품을 보는 두 공식 분류"):
    st.html('<table class="pt"><thead><tr><th></th><th>HS(관세 · 무역 통계)</th><th>군급(군수품 분류)</th></tr></thead><tbody>'
            '<tr><td>누가 쓰나</td><td class="l">관세청 수출입 통계</td><td class="l">국방 군수품 목록 · 조달</td></tr>'
            '<tr><td>무엇으로 나누나</td><td class="l">품목의 성질 · 재질 · 용도</td><td class="l">보급 관리를 위한 기능 분류</td></tr>'
            '<tr><td>자릿수</td><td class="l">국제 6자리 + 국내 10자리</td><td class="l">군 2 · 군급 4 · 재고번호 13</td></tr>'
            '<tr><td>이 대시보드에서</td><td class="l">전자부품 현황(13개 품목군)</td><td class="l">군급 분류와 조달 · 국산화 현황</td></tr>'
            '</tbody></table><div class="caption">두 분류 사이에 공식 대응표가 없어 품목끼리 짝짓지 않습니다.</div>')
with P.more("13개 품목군은 이렇게 골랐다"):
    st.html(" → ".join(f"<b>{n:,}</b> {name}" for name, _, n in R.hs_funnel())
            + '<div class="caption">관세청 HS 6자리(84 · 85 · 88 · 90류) 중 군용 전용 세분류 또는 전문 용도(항공기용 · 항행 · 레이더 · 무인기)가 '
              '이름에 적힌 품목만 → 그중 전자 계열만 분석 대상</div>')
