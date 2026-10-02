"""④ 4-2 발전전략 과제와 수요 유형 — 정부는 무엇을 국산화하려 하나.

값: 방향 · 과제 = 발전전략 참조표(rds.strategy_tasks), 수요 유형 = 발전전략 참조표(rds.chip_types).
발전전략 본문을 옮긴 참조표다 — 팀이 계산하거나 분류한 값이 아니며, 과제 수 · 유형 수는 예산이나 우선순위를 뜻하지 않는다.
"""
from __future__ import annotations

from html import escape

import streamlit as st

import parts as P
import rds as R

SEE = "국방반도체 발전전략의 방향 · 과제와 정부가 밝힌 수요 유형"
SOURCE = "방위사업청 · 국방반도체 발전전략(2024-11)"

st.html("""<style>
.pt td.dir{font-weight:800;color:#0b1f4d;background:#f5f8fe;vertical-align:top;text-align:left;word-break:keep-all}
.pt td.dir i{display:block;font-style:normal;font-size:12px;font-weight:700;color:#1d4ed8}
/* 머리 줄은 남색 바탕 · 흰 글씨(자세히 보기 안의 표와 같은 색) · 방향 사이에 옅은 회색 줄 — 방향별 묶음을 가른다(마지막 방향 아래에는 긋지 않는다) */
.pt.navy th{background:#1b2f66;color:#fff;border-bottom-color:#33488a}
.pt td.dir.sep,.pt tr.end td{border-bottom:1px solid #c9d2e0}
</style>""")

tk = R.strategy_tasks()
ct = R.chip_types()
n_dir = tk["direction_no"].nunique()
P.lead(f'발전전략은 <span class="key">{n_dir}개 방향 {len(tk)}개 과제</span>로 짜였고, 국방반도체 수요를 {len(ct)}개 유형으로 나눈다',
       "발전전략 본문을 옮긴 참조표입니다 — 과제 · 유형의 수는 예산이나 우선순위를 뜻하지 않습니다")

a, b = st.columns(2, gap="medium")
with a, P.card("tasks"):
    P.title(f"{n_dir}개 방향 {len(tk)}개 과제", "방향별 과제 · 발전전략 본문 순서")
    rows = ""
    last_dir = tk["direction_no"].max()
    for d, g in tk.groupby("direction_no", sort=True):
        sep = d != last_dir                    # 마지막 방향 아래에는 구분선을 긋지 않는다
        for i, r in enumerate(g.itertuples()):
            head = (f'<td class="dir{" sep" if sep else ""}" rowspan="{len(g)}"><i>방향 {r.direction_no}</i>{escape(r.direction_name)}</td>' if i == 0 else "")
            end = ' class="end"' if sep and i == len(g) - 1 else ""
            rows += f"<tr{end}>{head}<td>{r.task_no}</td><td class='l'>{escape(r.task_name)}</td></tr>"
    st.html(f'<table class="pt navy"><thead><tr><th>방향</th><th>과제</th><th>과제명</th></tr></thead><tbody>{rows}</tbody></table>')
with b, P.card("types"):
    P.title(f"국방반도체 수요 {len(ct)}대 유형", "정부가 밝힌 수요 유형 · 발전전략 본문 순서")
    rows = "".join(f"<tr><td>{r.type_no}</td><td class='l'><b>{escape(r.name_ko)}</b></td><td class='l'>{escape(r.summary)}</td></tr>"
                   for r in ct.itertuples())
    st.html(f'<table class="pt navy"><thead><tr><th>유형</th><th>이름</th><th>설명</th></tr></thead><tbody>{rows}</tbody></table>')
P.see(SEE, SOURCE)
