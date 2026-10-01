"""① 1-1 종합 현황표 — 13개 품목군을 한 표로(명세 11_cat_parts.md §3 · §4, 차트 세부 22_category_table.md).

값: 관세청 연도 × 국가 수입(rds.trade)을 고른 기간만큼 합산한 뒤 점유율 · HHI(metrics.concentration — 한 해면 DB 뷰와 같은 값),
추이 = 최근 12개월 월별 수입액(rds.monthly12), 선정 근거 = 관세청 HS부호 규칙 판정(rds.items r1 · r2).
"""
from __future__ import annotations

from html import escape

import streamlit as st

import parts as P
import rds as R
from kdesign import LV_BG, LV_FG, hhi_level, sparkline

LEAD = '{n}개 품목군 중 <span class="key">{k}개는 1위 공급국 점유율이 50% 이상</span>이다'
LEAD_SUB = "{period} 합계 · 국가 전체 수입(민수 포함) · 우선순위를 정한 목록은 아닙니다"
SEE = "13개 품목군의 수입이 몇 나라에 몰렸는지(1위 공급국 점유율 · HHI)와 품목이 무엇인지"

# 품목군 현황표 — 6줄 높이만 보이고 그 아래는 표 안에서 스크롤(머리줄은 위에 고정). 표 모양은 다른 표(.pt)와 같다
ROW_H, HEAD_H, SHOW = 62, 38, 6
TBL_CSS = f"""<style>
.pt-scroll{{max-height:{HEAD_H + ROW_H * SHOW}px;overflow:auto}}
.pt-scroll .pt th{{position:sticky;top:0;z-index:2;height:{HEAD_H}px;box-sizing:border-box}}
.pt-scroll .pt td{{height:{ROW_H}px;box-sizing:border-box;padding-top:6px;padding-bottom:6px}}
.pt-scroll .pt .c2{{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}   /* 긴 품명은 두 줄까지만(전체는 커서를 올리면) — 줄 높이를 같게 */
.pt-scroll .pt td:last-child,.pt-scroll .pt td.nm{{white-space:nowrap}}   /* 선정 근거 배지 · 품목군 이름 줄(HS + 묶음 배지)은 한 줄에 — 줄 높이를 같게 */
</style>"""

# HHI 칸 그림 — 칸은 .ftree 안에서 % 좌표로 놓는다. 칸 바탕은 흰색, 오른쪽 위에 1위 공급국 국기를 작게 둔다
TREE_CSS = """<style>
.ftree{position:relative;height:360px;border-radius:8px;overflow:hidden}
.ft{position:absolute;box-sizing:border-box;background:#fff;border:1px solid #c5d3ea;border-radius:4px;padding:6px 8px;overflow:hidden;
  display:flex;flex-direction:column;gap:1px;transition:background .15s,box-shadow .15s}
.ft:hover{background:#f3f7ff;box-shadow:inset 0 0 0 2px #1d4ed8;z-index:1}
.ft img{position:absolute;top:6px;right:7px;width:26px;height:17px;object-fit:cover;border:1px solid #d5deee;border-radius:2px}
.ft b,.ft span,.ft em{color:#0b1f4d;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ft b{padding-right:30px}        /* 국기 자리만큼 이름을 줄인다 */
.ft b{font-size:13.5px;font-weight:800}
.ft span{font-size:12.5px;font-weight:700}
.ft em{font-style:normal;font-size:11.5px;font-weight:700;color:#33415c}
</style>"""


def squarify(values: list[float], W: float, H: float) -> list[tuple[float, float, float, float]]:
    """정사각형에 가깝게 채우는 칸 배치(squarified treemap) — 값이 큰 순으로 들어온 values 의 (x, y, w, h). 넓이 = 값 비율."""
    total = float(sum(values)) or 1.0
    areas = [v / total * W * H for v in values]
    out: list[tuple[float, float, float, float]] = []
    x = y = 0.0
    w, h = W, H
    row: list[float] = []

    def worst(r: list[float], side: float) -> float:
        s = sum(r)
        return max(max(side * side * a / (s * s), s * s / (side * side * a)) for a in r)

    def flush() -> None:
        nonlocal x, y, w, h
        s = sum(row)
        if w >= h:                       # 왼쪽에 세로 띠 하나
            bw, cy = s / h, y
            for a in row:
                out.append((x, cy, bw, a / bw)); cy += a / bw
            x, w = x + bw, w - bw
        else:                            # 위쪽에 가로 띠 하나
            bh, cx = s / w, x
            for a in row:
                out.append((cx, y, a / bh, bh)); cx += a / bh
            y, h = y + bh, h - bh
        row.clear()

    for a in areas:
        side = min(w, h)
        if row and worst(row + [a], side) > worst(row, side):
            flush()
        row.append(a)
    if row:
        flush()
    return out


ys = R.full_years()
by = ys[-1]
r5 = [y for y in ys if y >= by - 4]
PERIODS = {f"{by} 기준 연도": [by], f"최근 5년({r5[0]}~{by})": r5, f"전체({ys[0]}~{by})": ys}
period = st.segmented_control("기간 기준", list(PERIODS), default=list(PERIODS)[0], key="p11_period") or list(PERIODS)[0]
c = R.conc(tuple(PERIODS[period])).sort_values("hhi", ascending=False).reset_index(drop=True)
names = R.country_names()
col = R.colors(c["top1_stat_cd"].dropna().tolist())
k50 = int((c["top1_share"] >= 0.5).sum())
k25 = int((c["hhi"] >= 2500).sum())
total = c["total"].sum() / R.E8
cats = c["category"].value_counts()
cat_txt = " · ".join(f"{k} {int(cats[k])}" for k in ("반도체", "전자부품", "소재장비") if k in cats)
wide, m0, m1 = R.monthly12()
source = f"관세청 · 품목별 국가별 수출입실적 · {R.customs_period()} / 품목 선정: 관세청 HS부호 마스터"

P.lead(LEAD.format(n=len(c), k=k50), LEAD_SUB.format(period=period))
P.kpis([P.kpi("분석 대상 품목군", f"{len(c)}", "개", cat_txt),
        P.kpi("수입액", f"{total:,.1f}", "억 달러", f"{period} 합계 · 국가 전체 수입(민수 포함)"),
        P.kpi("1위 공급국 50% 이상", str(k50), "개", "1위 공급국 점유율 기준"),
        P.kpi("HHI 2,500 이상", str(k25), "개", "기간 합계 HHI · 공급 집중 「높음」", icon="stacked_bar_chart")])

head = ("<tr><th>No.</th><th>품목군</th><th>관세청 품명</th><th>1위 공급국</th><th>1위 점유율</th><th>최근 12개월 추이</th>"
        "<th>HHI</th><th>공급 집중</th><th>수입국</th><th>선정 근거</th></tr>")
body = ""
for i, r in enumerate(c.to_dict("records"), 1):
    lvl, _ = hhi_level(r["hhi"])
    color = col.get(r["top1_stat_cd"], "#94a7c8")
    spark = wide.loc[r["hs6"]].tolist() if r["hs6"] in wide.index else [0.0] * 12
    badges = "".join(f'<span class="bdg rule">{x}</span>' for x in R.rules(r))
    body += (f'<tr><td>{i}</td><td class="l nm"><b>{escape(r["short"])}</b><em>HS {r["hs6"]}</em> '
             f'<span class="bdg fam">{escape(str(r["family"]))}</span></td>'
             f'<td class="l" style="max-width:220px"><div class="c2" title="{escape(r["name_ko"])}">{escape(r["name_ko"])}</div></td>'
             f'<td><span class="cdot" style="background:{color}"></span>{escape(names.get(r["top1_stat_cd"], r["top1_stat_cd"]))}</td>'
             f'<td>{P.share_bar(r["top1_share"] * 100, color)}</td>'
             f'<td>{sparkline(spark, color)}</td><td>{r["hhi"]:,.0f}</td>'
             f'<td><span class="lvb" style="background:{LV_BG[lvl]};color:{LV_FG[lvl]}">{lvl}</span></td>'
             f'<td>{int(r["country_count"])}</td><td class="l">{badges}</td></tr>')
t = c.iloc[0]
with P.card("tbl"):
    P.title("품목군 현황표",
            f"{period} 합계 · HHI 내림차순 · {SHOW}줄씩 보임(표 안에서 스크롤) · 추이 = 최근 12개월({m0[:4]}.{m0[4:]}~{m1[:4]}.{m1[4:]}) 월별 수입액 · HHI 2,500 이상 = 높음")
    st.html(TBL_CSS + f'<div class="pt-scroll"><table class="pt"><thead>{head}</thead><tbody>{body}</tbody></table></div>')
P.see(SEE, source)

c1, c2 = st.columns([1.4, 1], gap="medium")
with c1, P.card("tree"):
    lo = c.iloc[-1]
    P.title(f'{period} 합계 HHI는 <span class="key">{escape(t["short"])} {t["hhi"]:,.0f}</span>로 가장 높고 '
            f'{escape(lo["short"])} {lo["hhi"]:,.0f}로 가장 낮다',
            "칸 크기 = HHI(0~10,000, 클수록 수입이 소수 국가에 몰림) · 오른쪽 위 국기 = 1위 공급국")
    tiles = ""
    ASPECT = 1.75                    # 그림 가로 ÷ 세로(약 630 × 360px) — 이 비율로 배치해야 칸이 정사각형에 가깝다. 좌표는 % 로 바꿔 쓴다
    for r, (x, y, w, h) in zip(c.to_dict("records"), squarify(c["hhi"].tolist(), 100.0 * ASPECT, 100.0)):
        x, w = x / ASPECT, w / ASPECT
        cd = str(r["top1_stat_cd"] or "")
        nat = names.get(cd, cd)
        flag = f'<img alt="" src="https://flagcdn.com/w80/{cd.lower()}.png">' if len(cd) == 2 and cd.isalpha() else ""
        tiles += (f'<div class="ft" title="{escape(r["short"])} · HHI {r["hhi"]:,.0f} · 1위 {escape(nat)}" '
                  f'style="left:{x:.3f}%;top:{y:.3f}%;width:{w:.3f}%;height:{h:.3f}%">{flag}'
                  f'<b>{escape(r["short"])}</b><span>HHI {r["hhi"]:,.0f}</span><em>{escape(nat)}</em></div>')
    st.html(TREE_CSS + f'<div class="ftree">{tiles}</div>')
with c2, P.card("nctry"):
    top_n = c.loc[c["country_count"].idxmax()]
    P.title(f'수입국 수는 <span class="key">{escape(top_n["short"])} {int(top_n["country_count"])}개국</span>이 가장 많다',
            f"개국 · {period} · 수입 실적 > 0인 선적국 · 색 = 1위 공급국")
    rows = [(r["short"], int(r["country_count"]), col.get(r["top1_stat_cd"], "#94a7c8"))
            for r in c.sort_values("country_count", ascending=False).to_dict("records")]
    P.chart(P.hbar(rows, "개국", 360), "p11_nctry")
P.read1("HHI 2,500 이상 = 「높음」(미 법무부 · 연방거래위원회 2010 합병 지침의 고집중 기준) · 집중 수준 구간일 뿐 위험 예측이 아닙니다")

with P.more("자세히 보기 — 산식 · 선정 규칙"):
    st.markdown("- **1위 공급국 점유율** = 품목군 수입액 중 가장 큰 선적국의 비중(고른 기간 합계)\n"
                "- **HHI** = 국가별 점유율(%)의 제곱 합(0~10,000) — 수입 실적이 있는 선적국만\n"
                "- **선정 근거**: 군용 전용 세분류(관세청 HS부호 마스터의 「제9301호 · 제9306호 물품 전용」) · "
                "전문 용도 명시(세분류 · 품명에 항공기용 · 항행 · 레이더 · 무인기)\n"
                "- 수입액은 국가 전체 수입(민수 포함)이며 군수 몫은 관세 통계로 나뉘지 않습니다")
