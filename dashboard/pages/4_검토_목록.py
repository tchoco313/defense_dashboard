"""③ 검토 목록 — 품목군 현황표. 팀원 디자인 데모 「품목군 현황표」(page_table) 배치를 그대로 옮기고 값만 RDS 로 바꿨다.

구역: 품목군 현황표(표 · 기간 기준 · CSV) → 1위 공급국 분포(도넛 · 읽는 법) → 집중도 한눈에(트리맵 · 수입국 수 막대)
→ 품목군 선정 근거(실측 — ref_hs_whitelist 24개 evidence).
- 지표는 기간 기준(홈과 같은 3개 선택지, 완결 연도만) 합계로 계산한다(metrics.concentration — 홈·조회와 같은 산식). 여러 해를 고르면
  기간 합계의 국가 점유율로 HHI 를 낸다(연도별 HHI 평균 아님). 라벨은 「기간 합계 HHI」(M6).
- 정렬 = 수입 HHI(기간 합계) 내림차순, 관문도 수입 기준(CLAUDE.md). 「추가 검토 목록」이며 우선순위 확정이 아니다.
- 수입국 수 = 기간 합계 수입액 > 0 인 국가 수(수출만 있는 국가는 뺌).
- 선정 근거: evidence 키를 R1·R2(진입)·R3(참고)·A6·팀판단으로 읽는다. R4(B2-FSC 대응)는 2026-09-21 규칙에서 제외 —
  관세청 HS 를 FSC 와 엮지 않으므로 B2-FSC 열은 두지 않는다(CLAUDE.md). 「관련 군급(후보)」·과천 비중 열도 두지 않는다.
"""
from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import data_stamp, query
from kdesign import LV_BG, LV_FG, TEXT
from metrics import concentration
from ui import (ETC, SHORT, hhi_level, chart_source, chart_title, country_colors, csv_header, hero, hover_donut, period_control,
                png_button, rules_card, style_fig, zone)

SRC_PATH = "관세청 품목별 국가별 수출입실적 OpenAPI(15100475)"   # 화면 출처 = 기관 · 데이터명 · 기간만(DB 표 · 뷰 이름은 쓰지 않는다 — 보안)
M6 = 1e6   # 백만 달러 = USD ÷ 1e6 (표시 전용 변환)
BASIS_SHOW = 6                # 선정 근거 표에서 처음부터 보이는 줄 수 — 나머지는 펼쳐 보기
# evidence 키 → (화면 이름, 뜻). 화면에는 R1~R4 기호 대신 이름을 쓴다(docs/report/plan/plan-revision-2026-09-23.md §3-2 #3).
# 규칙 정의는 docs/reference/hs-whitelist-definition.md §8-2. 국산화 이력(R4)은 규칙에서 제외해 열을 두지 않는다
BASIS_TAGS = [("HSK-군용", "군용 전용", "군용 전용 세분류 — 「제9301·9306호 물품 전용」 세분류가 있음(진입 근거)"),
              ("HSK-항공/항행", "전문 용도", "전문 용도 명시 — 항공기용 · 항행 · 레이더 · 무인기 세분류가 있음(진입 근거)"),
              ("전략물자-DU", "전략물자 통제", "전략물자 통제 — 이중용도 통제품목 3·5·6·7부(참고일 뿐 진입 근거 아님)"),
              ("A6", "연구 인용", "국방반도체 연구 인용(참고)"), ("팀판단", "팀 판단", "기획 단계 팀 판단(진입 규칙 미해당)")]
TAG_COLOR = {"HSK-군용": "#2a78d6", "HSK-항공/항행": "#eb6834", "전략물자-DU": "#1baf7a", "A6": "#4a3aa7", "팀판단": "#b8c2cf"}   # 근거 종류 = 범주색(검증 팔레트 순서)


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wl_all = query("SELECT hs6, category, name_ko, priority, evidence FROM ref_hs_whitelist ORDER BY priority, hs6")
    tgt = wl_all.loc[wl_all["priority"].isin([1, 2]), "hs6"].tolist()          # 분석 대상 13개(M5)
    trade = query("""
        SELECT hs6, year, stat_cd, imp_dlr, exp_dlr, is_partial_year
        FROM v_import_hs6_year WHERE hs6 IN :hs
    """, {"hs": tgt})
    ctry = query("SELECT stat_cd, name_ko FROM ref_country")
    return wl_all, trade, ctry


def tint(hex_color: str, a: float = 0.2) -> str:
    """국가 색을 흰색과 섞은 옅은 바탕색(표 칸 · 글자는 본문색으로 둬 노랑 같은 옅은 색도 읽히게)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(*(round(255 - (255 - v) * a) for v in (r, g, b)))


def on_color(hex_color: str) -> str:
    """칸 색 위 글자색 — 밝은 칸(노랑 · 분홍 · 기타 회색)은 본문색, 짙은 칸은 흰색."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return TEXT if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#ffffff"


def ig(word: str) -> str:
    """받침에 맞춘 주격 조사(이/가) — 결론형 제목에 품목 · 국가 이름을 넣을 때."""
    c = word[-1] if word else ""
    return word + ("이" if "가" <= c <= "힣" and (ord(c) - 0xAC00) % 28 else "가")


def pct_rows(rows: list[tuple[str, float, str]]) -> str:
    """이름 · 막대 · % 한 줄씩(점선 = 50%). 데모 공급 국가 비중 카드와 같은 모양."""
    return '<div class="bars big">' + "".join(
        f'<div class="row" title="{n} {v:.1f}%"><div class="nm">{n}</div><div class="track">'
        f'<div class="fill" style="width:{v:.1f}%;background:{c}"></div><div class="ref"></div></div>'
        f'<div class="pct">{v:.1f}%</div></div>' for n, v, c in rows) + "</div>"


def basis_matrix(rows: pd.DataFrame, n_all: int, n_tgt: int, start: int = 0, title: str = "", card: bool = True) -> str:
    """선정 근거 행렬(데모 basis_matrix). start = 전체 목록에서 이 표의 첫 줄 위치(분석 대상/배경 경계선용)."""
    head = "".join(f'<th title="{d}">{s}</th>' for _, s, d in BASIS_TAGS)
    body = ""
    for k, r in enumerate(rows.itertuples()):
        tags = set((r.evidence or "").split(";"))
        cells = "".join(f'<td>{f"<i style=background:{TAG_COLOR[t]}></i>" if t in tags else ""}</td>'
                        for t, _, _ in BASIS_TAGS)
        tgt = ('<span style="color:#067647;font-weight:700">분석 대상</span>' if r.priority in (1, 2)
               else '<span style="color:var(--muted)">배경</span>')
        sep = ' style="border-top:2px solid #b7c7e2"' if start + k == n_tgt and k else ""
        body += (f'<tr{sep}><td class="nm"><em>{r.hs6}</em>{escape(r.name_ko)}</td><td class="cat">{escape(r.category)}</td>'
                 f'<td>{tgt}</td>{cells}</tr>')
    table = (f'<table class="basis"><thead><tr><th style="text-align:left">품목군(HS6)</th><th>분류</th><th>구분</th>{head}</tr></thead>'
             f'<tbody>{body}</tbody></table>')
    if not card:
        return table
    return (f'<div class="card"><div class="h"><span>{title}</span><span class="sub">HS6 {n_all}개 · 점 = 해당 근거 · '
            f'열 제목에 커서를 올리면 뜻</span></div>{table}</div>')


def basis_summary(wl_all: pd.DataFrame) -> str:
    n = len(wl_all)
    ev = wl_all["evidence"].fillna("").str.split(";")
    cnt = {t: int(ev.map(lambda s, t=t: t in s).sum()) for t, _, _ in BASIS_TAGS}
    short = {t: s for t, s, _ in BASIS_TAGS}
    rows = [(f"{short[t]} ({cnt[t]})", cnt[t] / n * 100, TAG_COLOR[t]) for t, _, _ in BASIS_TAGS]
    tgt = wl_all[wl_all["priority"].isin([1, 2])]
    tev = tgt["evidence"].fillna("").str.split(";")
    n_r1, n_r2 = int(tev.map(lambda s: "HSK-군용" in s).sum()), int(tev.map(lambda s: "HSK-항공/항행" in s).sum())
    cats = wl_all["category"].value_counts()
    cat_txt = " · ".join(f"{c} {v}" for c, v in cats.items())
    top_t = max(cnt, key=cnt.get) if n else None
    title = (f'수집 {n}개 중 <span class="key">{short[top_t]} 근거가 {cnt[top_t]}개</span>로 가장 많다'
             if top_t and cnt[top_t] else f"수집 {n}개 품목군의 근거별 해당 비율")
    return (f'<div class="card"><div class="h"><span>{title}</span><span class="sub">% · 괄호 = 개수</span></div>'
            + pct_rows(rows)
            + f'<div class="note" style="margin-top:12px"><b>분석 대상 {len(tgt)}개 = 군용 전용 세분류 또는 전문 용도 명시</b> — '
              f'전문 용도 {n_r2}개, 군용 전용 {n_r1}개(겹칠 수 있음). 나머지 {n - len(tgt)}개는 배경 자료. '
              f'국산화 이력(국산화개발품목 군급 대응)은 규칙에서 제외.<br>분류: {cat_txt}</div></div>')


def basis_legend() -> str:
    return '<div class="note" style="margin-top:10px">' + "<br>".join(
        f"· <b>{s}</b> — {d}" for _, s, d in BASIS_TAGS) + "</div>"


with st.spinner("관세청 집계를 읽는 중"):
    wl_all, trade, ctry = load()
wl = wl_all[wl_all["priority"].isin([1, 2])]
cname = dict(zip(ctry["stat_cd"], ctry["name_ko"]))
stamp = data_stamp("customs_all", "fact_customs_monthly")
SRC = (f"{SRC_PATH} · 자료 기간 {stamp['period'] if stamp['has_period'] else '—'} · "
       "국가는 선적국(원산지 아님)")

hero("④ 검토 목록", "분석 대상 품목군을 수입 집중도(HHI)가 높은 순으로 한 표에서 비교합니다 — 우선순위를 정한 목록은 아닙니다",
     stamps=[("관세청 수출입", stamp)])
st.html('<div class="lede"><div class="note">분석 대상 품목군을 한 표로 비교합니다. '
        '표는 열 머리를 눌러 정렬할 수 있고, 오른쪽 위 아이콘으로 검색·전체화면이 됩니다. 기본 정렬은 수입 HHI(기간 합계) 내림차순입니다.</div></div>')

# ── 품목군 현황표 ─────────────────────────────────────────────────────────────
with zone("tbl", "품목군 현황표"):
    years, y_label = period_control(trade, "기간 기준을 바꾸면 점유율 · 상위 3개국 비중 · HHI · 도넛 · 트리맵 · 막대 · CSV 가 같은 기준으로 다시 계산됩니다",
                                    key="period_p3")
    if not years:
        st.stop()
    per = y_label if len(years) == 1 else f"{y_label} 합계"
    sel = trade[trade["year"].isin(years)]
    conc = concentration(sel, "imp_dlr").set_index("hs6")          # 수입 실적(>0) 없는 hs6 는 없다 → join 뒤 NaN
    exp_sum = sel.groupby("hs6")["exp_dlr"].sum()
    t = wl.set_index("hs6").join([conc[["total", "hhi", "country_count"]].rename(columns={"total": "imp_dlr", "country_count": "n_ctry"}),
                                  exp_sum.rename("exp_dlr")], how="left")
    t["top1_cd"] = conc["top1_stat_cd"]
    t["top1"] = t["top1_cd"].map(lambda c: cname.get(c, c) if isinstance(c, str) else "—")
    t["top1_share"] = conc["top1_share"] * 100
    t["top3_share"] = conc["top3_share"] * 100
    t["short"] = [SHORT.get(h, n) for h, n in zip(t.index, t["name_ko"])]
    missing = t[t["imp_dlr"].isna()]
    t = t[t["imp_dlr"].notna()].sort_values("hhi", ascending=False)   # 검토 정렬 = 수입 HHI 내림차순(CLAUDE.md)
    if t.empty:
        st.info(f"{y_label} 수입 실적이 있는 품목군이 없습니다.")
        st.stop()

    cnt = t["top1_cd"].value_counts()
    cmap = country_colors(cnt.index.tolist())   # 1위 공급국 국가 색 — 표 · 도넛 · 트리맵 · 막대가 같은 색 키를 쓴다
    top_r = t.iloc[0]
    n_hi = int((t["hhi"] >= 2500).sum())
    chart_title(f'{len(t)}개 품목군 중 <span class="key">{n_hi}개가 기간 합계 HHI 2,500 이상</span>이고, '
                f'가장 높은 것은 {escape(str(top_r["short"]))}(HHI {top_r["hhi"]:,.0f} · 1위 {escape(str(top_r["top1"]))} '
                f'{top_r["top1_share"]:.1f}%)',
                f"{per} · 수입 HHI 내림차순 · 금액 백만 USD")
    amt_col = f"수입액(백만 USD, {per})"
    items = pd.DataFrame({
        "HS6": t.index, "품목군": t["short"], "1위 공급국": t["top1"], "1위 점유율(%)": t["top1_share"].round(1),
        "상위 3개국 비중(%)": t["top3_share"].round(1), "HHI": t["hhi"].round(0).astype(int), "수입국 수": t["n_ctry"].astype(int),
        amt_col: (t["imp_dlr"] / M6).round(1), "수출/수입": (t["exp_dlr"] / t["imp_dlr"]).round(2),
    }).reset_index(drop=True)
    codes = t["top1_cd"].tolist()                 # items 와 같은 순서(표 정렬 = HHI 내림차순)
    ccol = [cmap.get(c, ETC) for c in codes]      # 품목군별 1위 공급국 국가 색
    # 표 색: 1위 공급국 = 그 나라 색의 옅은 바탕, HHI = 집중 등급 배지색(홈 공급망 표와 같은 규칙). 정렬은 그대로 된다
    styler = (items.style
              .apply(lambda col: [f"background-color:{tint(c)};color:{TEXT};font-weight:600" for c in ccol], subset=["1위 공급국"])
              .apply(lambda col: [f"background-color:{LV_BG[hhi_level(v)[0]]};color:{LV_FG[hhi_level(v)[0]]};font-weight:600"
                                  for v in col], subset=["HHI"]))
    with st.spinner("품목군 집계를 다시 계산하는 중"):
        st.dataframe(
            styler, width="stretch", hide_index=True, height=min(38 + 35 * len(items), 520),
            column_config={
                "1위 점유율(%)": st.column_config.ProgressColumn("1위 점유율(%)", min_value=0, max_value=100, format="%.1f%%"),
                "상위 3개국 비중(%)": st.column_config.ProgressColumn(
                    "상위 3개국 비중(%)", min_value=0, max_value=100, format="%.1f%%",
                    help="선택 기간 합계 수입액 기준 상위 3개국 점유율의 합. 위험도가 아니라 공급국이 몇 나라에 몰려 있는지"),
                "HHI": st.column_config.NumberColumn("HHI", format="localized", help="기간 합계 HHI — Σ(국가 점유율 %)², 0~10,000. "
                                                                             "연도별 HHI 평균 아님. 2,500 이상 = 높은 집중"),
                "수입국 수": st.column_config.NumberColumn("수입국 수", format="%d개", help="기간 합계 수입액 > 0 인 국가 수"),
                amt_col: st.column_config.NumberColumn(format="localized"),
                "수출/수입": st.column_config.NumberColumn(format="%.2f", help="1보다 크면 수출이 수입보다 많음"),
            })
    cond = (f"분석 대상 {len(wl)}개 중 {len(t)}개 품목군 · 기간 {per}(완결 연도만) · 정렬 수입 HHI(기간 합계) 내림차순 · "
            "단위 백만 USD")
    head = csv_header(cond, SRC_PATH, [("관세청 수출입", stamp, None)],
                      extra="추가 검토 목록(우선순위 확정 아님) · HHI · 상위 3개국 비중 = 기간 합계 점유율 기준 · 수입국 수 = 수입 실적(>0) 국가 수 · "
                            "국가 전체 수입·수출(민수 포함) · 국가는 선적국")
    st.download_button("현황표 CSV 내려받기", (head + items.to_csv(index=False)).encode("utf-8-sig"),
                       f"품목군_현황표_{y_label.replace('~', '-')}.csv", "text/csv", key="p3_csv", icon=":material/download:")
    st.html('<div class="legend" style="margin-top:6px"><span><b>HHI 칸</b></span>'
            + "".join(f'<span><i style="background:{LV_BG[k]};border:1px solid #cbd5e1"></i>{k}</span>'
                      for k in ("높음", "보통"))
            + '<span>· HHI 2,500 이상 높음</span><span style="margin-left:10px"><b>1위 공급국 칸</b> = 국가 색</span></div>')
    miss_txt = (f" · {y_label} 수입 실적이 없어 뺀 품목군: " + ", ".join(f"{h} {n}" for h, n in zip(missing.index, missing["short"]))
                if not missing.empty else "")
    chart_source(f"{SRC} · 선택 연도를 국가별로 합산한 뒤 점유율·HHI 계산{escape(miss_txt)}")

# ── 1위 공급국 분포 ───────────────────────────────────────────────────────────
with zone("lead", "1위 공급국 분포"):
    c1, c2 = st.columns([1.5, 1], gap="medium")
    with c1.container(border=True, key="card_lead"):
        rows = [(cname.get(c, c), int(v), cmap.get(c, ETC)) for c, v in cnt.items()]
        lead_ties = [r for r in rows if r[1] == rows[0][1]] if rows else []
        t_lead = (f'{len(t)}개 품목군 중 <span class="key">{rows[0][1]}개는 {escape(ig(str(rows[0][0])))}</span> 1위 공급국'
                  if len(lead_ties) == 1 else
                  f'{len(t)}개 품목군의 1위 공급국은 <span class="key">'
                  f'{" · ".join(escape(str(r[0])) for r in lead_ties)} 각 {rows[0][1]}개</span>로 가장 많다' if rows else
                  f"{per} 1위 공급국이 있는 품목군이 없다")
        chart_title(t_lead, f"품목군 수 · {per} · 조각에 커서를 올려 보세요")
        hover_donut(rows, f"{len(t)}", "개 품목군", value_unit="개 품목군", height=430)
        fig_d = go.Figure(go.Pie(labels=[r[0] for r in rows], values=[r[1] for r in rows], hole=.55, sort=False,
                                 marker=dict(colors=[r[2] for r in rows], line=dict(color="#fff", width=1.5)),
                                 textinfo="label+value"))
        fig_d.update_layout(height=420, annotations=[dict(text=f"{len(t)}<br>개 품목군", showarrow=False, font=dict(size=17))])
        src_lead = f"{SRC} · 1위 = 선택 기간 합계 점유율 1위(동률은 국가 코드 내림차순)"
        chart_source(src_lead)
        png_button(style_fig(fig_d), f"1위공급국_분포_{y_label.replace('~', '-')}", title=t_lead, source=src_lead)
    c2.html(rules_card("읽는 법", [
        ("품목군 수이지 금액이 아닙니다", "1위로 잡은 품목군을 세어 만든 분포입니다."),
        ("1위라고 과반은 아닙니다", "점유율은 표의 「1위 점유율」 열에서 따로 봅니다."),
        ("국가는 선적국입니다", "관세청 통계의 선적국이며 원산지가 아닙니다."),
    ]))

# ── 집중도 한눈에 ─────────────────────────────────────────────────────────────
legend_html = ('<div class="legend" style="margin-top:4px"><span><b>1위 공급국</b></span>'
               + "".join(f'<span><i style="background:{cmap.get(c, ETC)}"></i>{escape(str(cname.get(c, c)))}</span>'
                         for c in cnt.index) + "</div>")
with zone("tree", "집중도 한눈에"):
    c1, c2 = st.columns(2, gap="medium")
    with c1.container(border=True, key="card_tree"):
        t_tree = (f'기간 합계 HHI 는 <span class="key">{escape(ig(str(items.iloc[0]["품목군"])))} {items.iloc[0]["HHI"]:,}</span>로 가장 높고 '
                  f'{escape(ig(str(items.iloc[-1]["품목군"])))} {items.iloc[-1]["HHI"]:,}로 가장 낮다')
        chart_title(t_tree, f"칸 크기 = HHI(0~10,000) · 색 = 1위 공급국 · 칸 글자 = 1위 점유율(%) · {per}")
        fig = go.Figure(go.Treemap(
            labels=items["품목군"], parents=[""] * len(items), values=items["HHI"],
            marker=dict(colors=ccol, line=dict(color="#fff", width=2)),
            textfont=dict(color=[on_color(c) for c in ccol]),
            texttemplate="%{label}<br>%{customdata[0]:.1f}%",
            customdata=list(zip(items["1위 점유율(%)"], items["1위 공급국"])),
            hovertemplate="%{label}<br>HHI %{value:,}<br>1위 %{customdata[1]} %{customdata[0]:.1f}%<extra></extra>"))
        fig.update_layout(height=380)
        st.plotly_chart(style_fig(fig), width="stretch", theme=None)
        st.html(legend_html)
        src_tree = f"{SRC} · HHI = Σ(국가 점유율 %)², 기간 합계 점유율 기준"
        chart_source(src_tree)
        png_button(fig, f"품목군_HHI_트리맵_{y_label.replace('~', '-')}", title=t_tree, source=src_tree)
    with c2.container(border=True, key="card_cnt"):
        mx, mn = items.loc[items["수입국 수"].idxmax()], items.loc[items["수입국 수"].idxmin()]
        t_cnt = (f'수입국 수는 <span class="key">{escape(str(mx["품목군"]))} {mx["수입국 수"]}개국</span>이 가장 많고 '
                 f'{escape(str(mn["품목군"]))} {mn["수입국 수"]}개국이 가장 적다')
        chart_title(t_cnt, f"개국 · {per} · 수입 실적 > 0 국가 · 막대 색 = 1위 공급국")
        # 가로 막대 — 품목군 이름을 눕히지 않고 읽는다(많은 것이 위로)
        bc = items.sort_values("수입국 수")
        fig = go.Figure(go.Bar(y=bc["품목군"], x=bc["수입국 수"], orientation="h", customdata=bc["1위 공급국"],
                               marker=dict(color=[ccol[i] for i in bc.index], line=dict(color="#fff", width=1)),
                               text=bc["수입국 수"], textposition="outside", cliponaxis=False, textfont=dict(size=13, color=TEXT),
                               hovertemplate="%{y}<br>%{x}개국 · 1위 %{customdata}<extra></extra>"))
        fig.update_layout(height=380, bargap=.3, margin=dict(l=8, r=36, t=10, b=8))
        fig = style_fig(fig)
        fig.update_yaxes(showgrid=False)
        st.plotly_chart(fig, width="stretch", theme=None)
        st.html(legend_html)
        src_cnt = f"{SRC} · 수입국 수 = 기간 합계 수입액 > 0 인 국가 수"
        chart_source(src_cnt)
        png_button(fig, f"품목군_수입국수_{y_label.replace('~', '-')}", title=t_cnt, source=src_cnt)

# ── 품목군 선정 근거(실측) ─────────────────────────────────────────────────────
with zone("basis", "품목군 선정 근거(실측)"):
    c1, c2 = st.columns([1.7, 1], gap="medium")
    rows_b = wl_all.assign(_t=~wl_all["priority"].isin([1, 2])).sort_values(["_t", "priority", "hs6"])   # 분석 대상을 위로
    n_all, n_tgt = len(rows_b), len(wl)
    with c1:
        st.html(basis_matrix(rows_b.iloc[:BASIS_SHOW], n_all, n_tgt,
                             title=f'수집 {n_all}개 중 <span class="key">{n_tgt}개가 군용 전용 · 전문 용도 세분류</span>에 해당해 분석 대상이다'))
        with st.expander(f"나머지 {n_all - BASIS_SHOW}개 펼쳐 보기 (분석 대상 {n_tgt - BASIS_SHOW}개 · 배경 {n_all - n_tgt}개)"):
            st.html(basis_matrix(rows_b.iloc[BASIS_SHOW:], n_all, n_tgt, start=BASIS_SHOW, card=False) + basis_legend())
    c2.html(basis_summary(wl_all))
    chart_source("팀 작성 HS6 선정 기준표(수집 24개 · 근거 태그) · 진입 규칙 = 군용 전용 세분류 또는 전문 용도 명시 · "
                 "국산화 이력(국산화개발품목 군급 대응)은 규칙에서 제외")

with st.expander("산식 · 출처 · 표현 범위"):
    st.markdown("**수입액** = 관세청 품목별 국가별 수출입실적의 품목군 · 국가별 연간 수입액(USD)을 선택 연도에 걸쳐 합산. 백만 달러 = USD ÷ 10⁶.  \n"
                "**1위 공급국 · 점유율** = 선택 연도를 국가별로 먼저 합산한 뒤 국가 금액 ÷ 품목군 합계 × 100(수입 실적 > 0 국가만).  \n"
                "**HHI(기간 합계)** = Σ(국가 점유율 × 100)², 0~10,000. 연도별 HHI 평균이 아니며 ① 화면의 「연도별 HHI」와 다른 지표. "
                "2,500 이상 = 높은 집중.  \n"
                "**수입국 수** = 기간 합계 수입액 > 0 인 국가 수.  \n"
                "**수출/수입** = 기간 합계 수출액 ÷ 수입액.  \n\n"
                "**표현 범위** — 「추가 검토 목록」이며 우선순위 확정이 아닙니다. 수입액은 국가 전체(민수 포함) 교역액이며 군수 수요 규모를 "
                "뜻하지 않습니다. 이 화면은 FSC·NSN·조달 예산과 연결하지 않습니다.  \n\n"
                f"**출처** — {SRC_PATH}. 팀 작성 HS6 선정 기준표(분석 대상 = 군용 전용 세분류 또는 전문 용도 명시, {len(wl)}개), 국가 이름은 관세청 국가 코드표.")
