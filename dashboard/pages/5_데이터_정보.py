"""⑤ 데이터 정보 — 팀원 디자인 데모(K-Defense) 「DATA INFO」 화면 배치를 그대로 옮기고 값은 RDS 에서 읽는다.

데모 배치: 머리 안내(lede) → 「데이터 출처」 표 → 「데이터 결합 검증」(입찰 공고 ↔ 결과 깔때기 + 읽는 법) → 「한계와 주의」 카드 2장
+ 세분류 용도별 수입 비중(EDA A1 — 기간을 고르면 이 카드만 다시 조회, 태그 규칙은 v_hs10_use_share 와 같음).
데모의 샘플 값은 모두 바꿨다:
- 출처 표 = DB meta_dataset(= db/meta_dataset.csv) — 화면이 문서와 따로 놀지 않게 DB에서 읽는다
- 깔때기 = clean_dapa_bid_notice · clean_dapa_bid_result 행 수와 notice_link_status(공고번호 + 차수 대조, v_bid_notice_result_link 와 같은 기준)
- 1만 건 요건 2종(M2)의 원본 건수는 출처 표(meta_dataset)에서 포털 ID 로 골라 쓴다
데모에 없던 기존 내용(선정 규칙 · 지표 정의 · 용어 · 쓰지 않은 데이터 · 말하지 않는 것)은 출처 · 정의 정확성에 필요해 「상세 정의」 펼침으로 둔다.

근거 문서(문구를 바꿀 때 먼저 고친다):
- 선정 규칙: docs/reference/hs-whitelist-definition.md §8-2 — 진입 R1 OR R2(2026-09-21 회의 M5, R4 제외). 분석 제외 = priority 3
- 제외 데이터: docs/report/data/data-usage-decision-2026-09-18.md §1 「제외」, docs/idea-review.md §2-C
- 과장 금지: docs/idea-review.md §3 유의사항
"""
from __future__ import annotations

import re
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import data_stamp, query, safe_query, try_query
from metrics import count_state
from ui import SHORT, chart_source, chart_title, csv_header, hero, html_table, png_button, rules_card, style_fig, zone

# 1만 건 요건 2종(2026-09-21 회의 M2) + 부록 — 출처 표에서 포털 ID 로 찾는다(표시용)
ID_CUSTOMS, ID_LOCAL, ID_CONTRACT = "15100475", "15119899", "15050920"
FUNNEL_COLORS = ["#1e3a8a", "#1d4ed8", "#3b82f6", "#0284c7"]
# 「군용」 신고 비중(EDA A1) — 용도 태그 = 파랑 한 계열 농도(군용 전용이 가장 진함), 태그가 없는 세분류 = 옅은 회색
USE_TAGS = [("군용전용", "군용 전용(제9301·9306호)", "#1e3a8a"), ("항공기용", "항공기용 · 우주항행", "#3b82f6"),
            ("자동차용", "자동차용", "#93c5fd"), ("기타", "용도 표기 없음", "#e5eaf1")]
SRC_USE = "관세청 품목별 국가별 수출입실적 OpenAPI(15100475) · 관세청 HS 코드표(세분류 품명) · 국가 전체 수입(민수 포함)"   # 깔때기 — 파랑 → 하늘(단계가 좁아질수록 옅게) · 흰 숫자 대비 3:1 이상

# 건수 3종 — 캐시 밖(try_query): 실패해도 페이지는 그리고 숫자만 뺀다
rule_df, rule_err = try_query("SELECT COUNT(*) AS n FROM ref_hs_rule_flag")
wl_df, wl_err = try_query("SELECT hs6, name_ko, priority FROM ref_hs_whitelist ORDER BY priority, hs6")
b2_df, b2_err = try_query("SELECT COUNT(DISTINCT project_name) AS n FROM clean_dapa_localized_item")
st_rule, n_rule = count_state(rule_df, rule_err, "n")
st_b2, n_b2 = count_state(b2_df, b2_err, "n")
n_wl = int((wl_df["priority"] <= 2).sum()) if wl_df is not None else None      # 분석 대상 13개(priority 1·2)
excl_items = ([f"{r.hs6} {SHORT.get(r.hs6, r.name_ko)}" for r in wl_df.itertuples() if r.priority == 3]
              if wl_df is not None else [])                                       # 규칙 미해당 11개(priority 3)


@st.cache_data(ttl=3600, show_spinner=False)
def customs_full_years() -> list[int]:
    return [int(y) for y in query("SELECT DISTINCT year AS y FROM fact_customs_monthly WHERE is_partial_year = 0 ORDER BY y")["y"]]


@st.cache_data(ttl=3600, show_spinner=False)
def load_use_share(y0: int, y1: int) -> pd.DataFrame:
    """분석 대상 13개 품목의 세분류 용도 태그별 수입액(EDA A1). 태그 규칙은 v_hs10_use_share 뷰와 같고
    뷰에 고정된 기간(2021~2025)만 :y0 · :y1 로 바꿨다 — 기본값 2021~2025 는 뷰와 같은 값이어야 한다."""
    return query("""
        SELECT t.hs6, t.use_tag, SUM(t.imp_dlr) AS imp_dlr, COUNT(DISTINCT t.hs10) AS hs10_count
        FROM (SELECT d.hs6, d.hs10,
                     CASE WHEN d.name_ko REGEXP '9301|9306'             THEN '군용전용'
                          WHEN d.name_ko REGEXP '항공기용|항공용|우주항행' THEN '항공기용'
                          WHEN d.name_ko REGEXP '자동차용'                THEN '자동차용'
                          ELSE '기타' END AS use_tag,
                     COALESCE(f.imp_dlr, 0) AS imp_dlr
              FROM dim_hs10 d
              LEFT JOIN fact_customs_monthly f
                     ON f.hs10 = d.hs10 AND f.year BETWEEN :y0 AND :y1 AND f.is_partial_year = 0) t
        JOIN ref_hs_whitelist w ON w.hs6 = t.hs6 AND w.priority IN (1, 2)
        GROUP BY t.hs6, t.use_tag
    """, {"y0": y0, "y1": y1})


@st.fragment
def use_share_card() -> None:
    """세분류 용도별 수입 비중 — 기간을 바꾸면 이 카드만 다시 조회한다."""
    ys = customs_full_years()
    if not ys:
        st.info("관세청 완결 연도 집계가 없습니다(미적재).")
        return
    d0 = 2021 if 2021 in ys else ys[0]
    y0, y1 = st.select_slider("기간(완결 연도)", options=ys, value=(d0, ys[-1]), key="p5_use_years")
    u = load_use_share(int(y0), int(y1))
    tot = u.groupby("hs6")["imp_dlr"].transform("sum")
    u = u.assign(pct=(u["imp_dlr"] / tot.where(tot > 0) * 100).fillna(0))
    wide = u.pivot_table(index="hs6", columns="use_tag", values="pct", aggfunc="sum", fill_value=0)
    for k, _, _ in USE_TAGS:
        if k not in wide.columns:
            wide[k] = 0.0
    pos = u.groupby("hs6")["imp_dlr"].sum()
    wide = wide.loc[wide.index.isin(pos[pos > 0].index)].sort_values(["항공기용", "군용전용"], ascending=True)
    if wide.empty:
        st.info(f"{y0}~{y1} 분석 대상 품목의 수입 실적이 없습니다.")
        return
    names = {r.hs6: SHORT.get(r.hs6, r.name_ko) for r in wl_df.itertuples()} if wl_df is not None else {}
    labels = [f"{names.get(h, h)} {h}" for h in wide.index]
    mil_max = float(wide["군용전용"].max())
    span = f"{y0}~{y1}" if y0 != y1 else f"{y0}"
    t = (f"{span} 「군용 전용」 세분류로 신고된 수입액은 {len(wide)}개 품목 모두 "
         f'<span class="key">{mil_max:.2f}% 이하</span> — HS 통계로는 군용을 따로 떼어 낼 수 없다' if mil_max < 1 else
         f'{span} 「군용 전용」 세분류 수입 비중은 가장 높은 품목이 <span class="key">{mil_max:.1f}%</span>')
    chart_title(t, "품목별 100% = 기간 합계 수입액 · 세분류(HS10) 품명의 용도 표기로 나눔 · 항공기용 비중 순")
    fig = go.Figure()
    for k, lbl, col in USE_TAGS:
        fig.add_trace(go.Bar(y=labels, x=wide[k], orientation="h", name=lbl, marker=dict(color=col, line=dict(color="#fff", width=1)),
                             hovertemplate=f"%{{y}}<br>{lbl} %{{x:.2f}}%<extra></extra>"))
    fig.update_layout(barmode="stack", height=34 * len(wide) + 140, legend=dict(orientation="h", y=1.1, traceorder="normal"),
                      xaxis=dict(range=[0, 100], ticksuffix="%"), margin=dict(l=210, r=20, t=40, b=8))
    st.plotly_chart(style_fig(fig), width="stretch", theme=None, key="p5_use_share",
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "autoScale2d"]})
    png_button(fig, f"데이터정보_세분류용도비중_{span}", align="flex-start", title=t, source="출처: " + SRC_USE)
    st.html('<div class="caption">이 13개는 「항공기용 · 항행」 같은 전문 용도 세분류나 군용 전용 세분류가 있는 품목으로 골랐습니다. '
            '군용 전용 세분류가 있어도 실제 신고는 거의 없으므로 수입액은 국가 전체(민수 포함)로 읽습니다.</div>')
    chart_source(f"{SRC_USE} · 기간 {span}(완결 연도)")


@st.cache_data(ttl=3600, show_spinner=False)
def load_sources() -> pd.DataFrame | None:
    return safe_query("""
        SELECT tier, provider, dataset_key, dataset_id, title, url, access_method, acquired_on,
               period_start, period_end, is_partial_period, raw_row_count
        FROM meta_dataset WHERE tier <> '메타'
        ORDER BY FIELD(tier, '핵심', '보조', '참조'), provider, dataset_key
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def load_bid_match() -> pd.DataFrame | None:
    """입찰 공고 ↔ 결과 깔때기(행 단위). 연결 판정은 clean_dapa_bid_result.notice_link_status(공고번호 + 차수 대조)."""
    return safe_query("""
        SELECT (SELECT COUNT(*) FROM clean_dapa_bid_notice)                                    AS n_notice,
               (SELECT COUNT(*) FROM clean_dapa_bid_result)                                    AS n_result,
               (SELECT COUNT(*) FROM clean_dapa_bid_result WHERE notice_link_status <> '미연결') AS n_linked,
               (SELECT COUNT(*) FROM clean_dapa_bid_result WHERE notice_link_status = '1:1')    AS n_one
    """)


def card_title(col_ui, title: str, sub: str) -> None:
    """결론형 제목 + 조건 · 단위 부제(ui.chart_title 과 같은 모양)."""
    chart_title(title, sub, where=col_ui)


def cards(items: list[tuple[str, str]], widths: str = "1fr 1fr") -> str:
    """(제목, 본문 HTML) 카드 묶음."""
    body = "".join(f'<div class="card"><div class="h">{h}</div><div class="note">{b}</div></div>' for h, b in items)
    return f'<div style="display:grid;grid-template-columns:{widths};gap:12px;margin-top:8px">{body}</div>'


def bullets(items: list[str]) -> str:
    return "<br>".join("· " + i for i in items)


def period(r) -> str:
    if pd.isna(r.period_start):
        return "—"
    end = f"{pd.Timestamp(r.period_end):%Y.%m}" if pd.notna(r.period_end) else ""
    return f"{pd.Timestamp(r.period_start):%Y.%m}~{end}" + (" (부분)" if r.is_partial_period else "")


def stamp_txt(name: str, s: dict) -> str:
    """데이터 하나의 자료 기간(화면 · CSV 에 DB 적재일은 쓰지 않는다 — 보안, 2026-09-24). 조회 실패는 따로 적는다."""
    if s.get("error") and not s.get("has_period"):
        return f"{name} —(조회 실패)"
    return f"{name} 자료 {s['period']}"


_FILE_BITS = re.compile(r"\s*\([^)]*(?:/|\.(?:csv|txt|py|xlsx|json|ipynb))[^)]*\)"   # (정리본: a.txt + b.csv) · (new_data/)
                        r"|\s*→\s*[^|]*?\.py\b[^|·]*"                               # → parse_krit.py 표 추출
                        r"|\s*\S+\.(?:csv|txt|py|xlsx|json|ipynb)\b"                  # countries.csv
                        r"|\s*\([^)]*Claude[^)]*\)")                                   # (Claude in Chrome) — 작업 도구 이름


def plain_cell(v) -> str:
    """출처 표의 기관 · 데이터 · 형태 칸에서 스크립트 · 파일 이름 · 내부 경로를 뺀다(화면에 내부 정보 노출 금지)."""
    if not isinstance(v, str):
        return v
    t = _FILE_BITS.sub("", v)
    return re.sub(r"\s{2,}", " ", t).strip(" +·→") or "—"      # 칸 전체가 파일 이름이면 원문을 내보내지 않는다


def caption(text: str, top: int = 8) -> None:
    st.html(f'<div class="caption" style="margin-top:{top}px">{text}</div>')


def csv_button(df: pd.DataFrame, cond: str, source: str, stamps: list, fname: str, key: str) -> None:
    """표 CSV — 머리줄에 조건 · 출처 · 자료 기간 · 적재일(ui.csv_header)."""
    head = csv_header(cond, source, stamps)
    st.download_button("CSV 내려받기", (head + df.to_csv(index=False)).encode("utf-8-sig"), f"{fname}.csv", "text/csv",
                       icon=":material/download:", key=key)


# ── 데이터 ─────────────────────────────────────────────────────────────────
src = load_sources()
src_ok = src is not None and not src.empty


def src_row(dataset_id: str):
    """이미 읽은 출처 표(src)에서 포털 ID 로 행 하나를 고른다(표시용 — SQL 추가 없음). 없으면 None."""
    if not src_ok:
        return None
    hit = src[src["dataset_id"] == dataset_id]
    if dataset_id == ID_CUSTOMS:              # 15100475 은 행이 둘(customs_all 294,420 · customs_progress 264) — 수출입 본표를 키로 고른다
        hit = hit[hit["dataset_key"] == "customs_all"]
    return None if hit.empty else hit.iloc[0]


def rows_of(r) -> int | None:
    return None if r is None or pd.isna(r.raw_row_count) else int(r.raw_row_count)


r_cus, r_loc = src_row(ID_CUSTOMS), src_row(ID_LOCAL)
n_cus, n_loc, n_con = rows_of(r_cus), rows_of(r_loc), rows_of(src_row(ID_CONTRACT))

# 데이터별 자료 기간 · DB 적재일(meta_load_log 는 표마다 다르다)
stamp_customs = data_stamp("customs_all", "fact_customs_monthly")
stamp_local = data_stamp("dapa_localized_item", "clean_dapa_localized_item")
stamp_wl = data_stamp("ref_hs_whitelist", "ref_hs_whitelist")
stamp_flag = data_stamp("ref_hs_rule_flag", "ref_hs_rule_flag")
stamp_bid = data_stamp("dapa_bid_result", "clean_dapa_bid_result")

end = stamp_customs["period"].split("~")[-1] if stamp_customs["has_period"] else ""
partial_line = (f"관세청 {end[:4]}년은 {int(end[5:])}월까지의 부분연도라 연간 비교 · KPI에서 뺍니다"
                if len(end) == 7 and end[5:].isdigit() and end[5:] != "12"
                else "관세청 마지막 해가 부분연도이면 연간 비교 · KPI에서 뺍니다")
b2_txt = f"지상 {n_b2}개 사업" if st_b2 == "ok" else "지상 사업 한정"

# ── 머리띠(데모 hero) ──────────────────────────────────────────────────────
hero(stamps=[("관세청 수출입", stamp_customs)])

st.html('<div class="lede"><div class="note">이 대시보드의 숫자가 어디서 왔고, 어떻게 계산했고, '
        '무엇을 뜻하지 <b>않는지</b> 적어 둔 곳입니다. 값은 모두 아래 「데이터 출처」 표의 공개 자료에서 왔습니다.</div></div>')

# ── 데이터 출처 ────────────────────────────────────────────────────────────
with zone("src", "데이터 출처"):
    if not src_ok:
        st.info("출처 표를 읽지 못했습니다(조회 실패). 잠시 뒤 다시 열어 주세요.")
    else:
        tiers = src["tier"].value_counts()
        chart_title(f'대시보드의 숫자는 자료 <span class="key">{len(src)}종</span>에서 온다 — '
                    + " · ".join(f"{t} {int(tiers.get(t, 0))}" for t in ("핵심", "보조", "참조") if tiers.get(t, 0)),
                    "행 · 원본 건수 = 내려받아 파서로 센 수 · 「(부분)」 = 1년이 다 차지 않은 기간")
        view = pd.DataFrame({
            "기관": src["provider"].map(plain_cell), "데이터": src["title"].map(plain_cell), "형태": src["access_method"].map(plain_cell),
            "기간": [period(r) for r in src.itertuples()], "원본 건수(행)": src["raw_row_count"],
            "구분": src["tier"], "포털 ID": src["dataset_id"].fillna("—"), "확보일": src["acquired_on"].astype(str),
            "링크": src["url"],
        })
        # 줄바꿈되는 HTML 표 — st.dataframe 은 9열이 칸 폭을 넘어 오른쪽 열(건수 · 링크)이 잘렸다(2026-09-28 점검)
        st.html(html_table(view, num_cols=("원본 건수(행)",), link_cols=("링크",),
                           nowrap_cols=("구분", "포털 ID", "확보일")))
        req = ((f"과제 요건 「2종 × 각 1만 건」 = 관세청 수출입실적 <b>{n_cus:,}행</b> · 국산화개발품목 <b>{n_loc:,}행</b>"
                if n_cus is not None and n_loc is not None else "과제 요건 「2종 × 각 1만 건」 = 관세청 수출입실적 · 국산화개발품목")
               + "(관측 대상이 서로 다른 자료라 합산하지 않음) · "
               + (f"국내조달 계약정보({n_con:,}행)는 부록" if n_con is not None else "국내조달 계약정보는 부록"))
        c_note, c_dl = st.columns([4, 1], vertical_alignment="center")
        c_note.html(f'<div class="note">{req}<br>원본 건수 = 실제로 내려받아 파서로 센 수(5단계 보고의 「원본 전체」) · {partial_line}</div>')
        with c_dl:
            csv_button(view, "조건 없음 · 출처 표 전체", "대시보드 출처 표(팀 작성)",
                       [("관세청 수출입", stamp_customs, None)], "데이터정보_출처표", "p5_csv_src")
        chart_source(f"대시보드 출처 표(팀 작성) · 자료 {len(src)}종 · {stamp_txt('관세청 수출입', stamp_customs)}")

# ── 데이터 결합 검증 — 입찰 공고 ↔ 결과 깔때기(데모 배치, 값은 RDS) ─────────────
with zone("match", "데이터 결합 검증"):
    bm = load_bid_match()
    if bm is None or bm.empty:
        st.info("입찰 공고 · 결과 자료를 조회하지 못했습니다(조회 실패).")
    elif int(bm.at[0, "n_notice"]) == 0 or int(bm.at[0, "n_result"]) == 0:
        st.warning("입찰 공고 · 결과 표에 적재된 행이 없습니다(미적재).")
    else:
        n_ann, n_res, n_lnk, n_one = (int(bm.at[0, c]) for c in ("n_notice", "n_result", "n_linked", "n_one"))
        steps = [("입찰 공고 행", n_ann), ("입찰 결과 행", n_res), ("공고와 연결된 결과 행", n_lnk),
                 ("공고 1건과만 맞는 결과 행(1:1)", n_one)]
        c1, c2 = st.columns([1.35, 1], gap="medium")
        base, step = n_ann, 5.5          # step = 층마다 양옆이 좁아지는 폭(%)
        rows = "".join(
            f'<div class="fr"><div class="tz" style="background:{FUNNEL_COLORS[i]};'
            f'clip-path:polygon({i * step}% 0,{100 - i * step}% 0,{100 - (i + 1) * step}% 100%,{(i + 1) * step}% 100%)">'
            f'{v:,}</div><div class="lb"><div>{nm}<small>({v / base * 100:.1f}%)</small></div></div></div>'
            for i, (nm, v) in enumerate(steps))
        with c1.container(border=True, key="card_funnel"):
            chart_title(f"입찰 결과 {n_res:,}행 중 공고 1건과 정확히 맞는 결과는 "
                        f'<span class="key">{n_one / n_res * 100:.1f}%({n_one:,}행)</span>', "행 · 괄호 = 공고 행 대비")
            st.html(f'<div class="funnel">{rows}</div>')
        c2.html(rules_card("읽는 법", [
            (f"공고와 맞지 않는 결과 {n_res - n_lnk:,}행은 결합하지 않습니다",
             "공고번호 + 차수(2자리 정규화)가 입찰공고 쪽에 없어 어느 공고의 결과인지 알 수 없는 행입니다."),
            (f"공고 여러 건과 맞는 결과 {n_lnk - n_one:,}행은 따로 셉니다",
             "공고번호에 연도가 없어 같은 번호 · 차수가 여러 공고에 있는 경우입니다(다중 일치 — 행 단위 조인은 하지 않음)."),
            (f"1:1로 맞는 결과는 {n_one:,}행입니다",
             f"결과 {n_res:,}행 대비 {n_one / n_res * 100:.1f}% · 공고 {n_ann:,}행 대비 {n_one / n_ann * 100:.1f}% — "
             "결과가 없는 공고는 매칭 대상이 아닙니다."),
        ]))
        step_df = pd.DataFrame(steps, columns=["단계", "행 수"]).assign(**{"공고 행 대비(%)": lambda d: (d["행 수"] / n_ann * 100).round(1)})
        c_cap, c_dl = st.columns([4, 1], vertical_alignment="center")
        c_cap.html('<div class="caption">전자부품과 잇는 공통 식별자가 없어 화면 분석에는 쓰지 않습니다 · 연결 판정 = 공고번호 + 차수 대조</div>')
        with c_dl:
            csv_button(step_df, "입찰 공고 ↔ 결과 매칭 · 단위 행", "방위사업청 국내 입찰공고 · 입찰결과(파일데이터)",
                       [("입찰결과", stamp_bid, None)], "데이터정보_입찰매칭", "p5_csv_match")
        # 출처 「?」는 다른 구역처럼 줄 아래 오른쪽 끝에(설명 칸 안에 두면 CSV 단추 옆 어중간한 자리에 뜬다)
        chart_source("방위사업청 국내 입찰공고 · 입찰결과(파일데이터) · 연결 판정 = 공고번호 + 차수 대조 · "
                     f"{stamp_txt('입찰결과', stamp_bid)}")

# ── 한계와 주의 ────────────────────────────────────────────────────────────
with zone("limit", "한계와 주의"):
    c1, c2 = st.columns(2, gap="medium")
    c1.html(rules_card("이 대시보드가 말하지 않는 것", [
        ("군수 수요 비중이 아닙니다", "관세 통계는 군수·민수를 나누지 않습니다. 국가 전체 수입액(민수 포함)입니다."),
        ("국산화율이 아닙니다", f"국산화개발을 마친 부품 목록({b2_txt})이며 비율 지표가 아닙니다."),
        ("리스크 예측·조기경보가 아닙니다", "과거 공개 통계의 현황을 보여 주는 화면입니다. HHI 는 수입 집중도이며 위험도가 아닙니다."),
        ("관세청 수입액과 조달 예산을 합치지 않습니다", "국외 조달계획(원화 계획)과 관세청 수입액(달러 실적)은 합산 · 비율 · 직접 비교하지 않습니다."),
    ]))
    c2.html(rules_card("계산 방법", [
        ("점유율", "선택 연도 수입액을 국가별로 합산 → 국가별 비중. 수입 실적 0 초과 국가만 셉니다."),
        ("HHI", "국가별 점유율(%)의 제곱 합, 0~10,000. 2,500 이상이면 높은 집중으로 봅니다."),
        ("기간 기준", partial_line + " — 완결 연도만 씁니다."),
        ("국가", "관세청 통계의 선적국입니다. 원산지와 다를 수 있습니다(홍콩 · 싱가포르 경유 등)."),
    ]))
    with st.container(border=True, key="card_use_share"):
        use_share_card()

# ── 상세 정의 — 데모에 없던 기존 내용. 출처 · 정의 정확성에 필요해 펼침으로 둔다 ─────────
with zone("detail", "상세 정의"):
    # ── 선정 규칙과 지표 정의 ─────────────────────────────────────────────────
    with st.expander("품목 선정 규칙과 지표 정의"):
        if wl_df is not None and not wl_df.empty:
            rule_title = (f'수집 {len(wl_df)}개 품목군 중 분석 대상은 군용 전용 · 전문 용도 세분류에 해당하는 <span class="key">{n_wl}개</span>, '
                          f"나머지 {len(excl_items)}개는 배경 자료로만 둔다")
        else:
            rule_title = "품목 선정 규칙과 지표 정의 — 분석 대상 품목군"
        card_title(st, rule_title, "진입 = 군용 전용 세분류 또는 전문 용도 명시 · 전략물자 통제는 참고 · 국산화 이력 제외 · 지표 산식은 오른쪽 카드 · 여러 해는 기간 합계 후 계산")
        st.html(cards([
            (f"분석 대상 {n_wl if n_wl is not None else ''}품목군은 이렇게 골랐습니다".replace("  ", " "), bullets([
                (f"범위: HS 84 · 85 · 88 · 90류의 HS6 {n_rule:,}개 전수" if st_rule == "ok"
                 else "범위: HS 84 · 85 · 88 · 90류의 HS6 전수(건수 조회 실패)"),
                "<b>공식 자료에서 확인한 사실</b>: 관세청 분류표의 세분류 명칭(군용 전용 · 전문 용도 판정), 전략물자수출입고시 별표2 HSK 연계표(전략물자 통제 판정)",
                "<b>규칙</b>: <b>군용 전용 세분류</b> — 「제9301호 · 제9306호 물품 전용」 세분류가 있음 / "
                "<b>전문 용도 명시</b> — 「항공기용 · 항행 · 레이더 · 무인기」 세분류가 있거나 HS6 명칭에 같은 용도어 / "
                "<b>전략물자 통제</b> — 별표2 3 · 5 · 6 · 7부(전자 · 정보통신 · 센서 · 항법) 통제품목(참고, 진입 근거 아님)",
                "진입 = <b>군용 전용 세분류 또는 전문 용도 명시</b>. 전략물자 통제만으로는 들어오지 않습니다. 국산화 이력(국산화개발품목 군급 대응)은 규칙에서 뺐습니다 — "
                "관세청 HS 품목군은 군급(FSC) · 재고번호(NSN)와 잇지 않습니다",
                (f"수집 {len(wl_df)}개 중 진입 규칙(군용 전용 · 전문 용도) 미해당 <b>{len(excl_items)}개</b>는 분석 대상에서 빼고 배경 자료로만 둡니다: {escape(', '.join(excl_items))}" if excl_items
                 else "분석 제외 품목군 목록은 조회 실패로 표시하지 못했습니다"),
                "규칙 조합 · 문턱값은 공식 자료에 적용한 <b>팀의 분석 규칙</b>이며 정부 공식 목록도, 통계적 검증도 아닙니다"])),
            ("지표는 이렇게 계산합니다", bullets([
                "<b>수입액</b> = 관세청 품목별 국가별 수출입실적, HS10 → HS6 합산, 총계 행 제외, USD",
                "<b>1위 공급국 점유율</b> = 1위 국가 수입액 ÷ 품목군 수입액(동률이면 국가코드가 큰 쪽 — DB 뷰와 같은 규칙)",
                "<b>집중도(HHI)</b> = Σ(국가별 점유율 %)², 0~10,000. 2,500 이상을 「높은 집중」으로 봅니다(미 법무부 기준)",
                "여러 해를 고르면 <b>국가별로 기간 합계</b>를 낸 뒤 점유율 · HHI를 계산합니다(연도별 값의 평균 아님). "
                "① 화면의 연도별 HHI 와 홈 · ④ 검토 목록 · 조회 화면의 기간 합계 HHI 는 다른 지표입니다",
                "<b>수입국 수</b> = 그 기간 수입 실적(>0)이 있는 국가 수. 수출만 있는 국가는 세지 않습니다",
                "<b>수출/수입</b> = 같은 기간 수출액 ÷ 수입액. HS6 합계라 민수 반도체가 대부분입니다",
                "<b>특정국 50% 이상</b> = 1위 공급국 점유율 50% 이상인 품목군 수(산업부 공급망 참고선)",
                "<b>국외 조달계획 건수</b> = 국외 조달계획(품목 단위 OpenAPI)에서 전자 군급(FSG 58 · 59 · 60, NSN 13자 숫자 · 영숫자)으로 판정한 행 수"
                "(조달요구번호 × 품목순번). 금액은 통화 미검증이라 쓰지 않습니다",
                "국가는 <b>선적국</b> 기준입니다. 원산지와 다를 수 있습니다(홍콩 · 싱가포르 경유 등)"])),
        ]))
        chart_source("관세청 HS 분류표 세분류 명칭 · 전략물자수출입고시 별표2 · 팀 품목 선정 규칙(분석 대상 = 군용 전용 세분류 또는 전문 용도 명시) · "
                     f"{stamp_txt('품목군 기준표', stamp_wl)} · {stamp_txt('규칙 판정표', stamp_flag)}")

    # ── 용어 ────────────────────────────────────────────────────────────────────
    with st.expander("용어"):
        terms = pd.DataFrame([
            ("코드", "HS6 · HS10", "국제 통일 상품분류. 6자리는 세계 공통, 10자리(HSK)는 한국 세분류. 군용 · 민수를 구분하지 않습니다"),
            ("코드", "품목군", f"이 대시보드에서는 HS6 하나를 품목군 하나로 부릅니다. 수집 {len(wl_df) if wl_df is not None else '—'}개 중 분석 대상은 진입 규칙(군용 전용 · 전문 용도 세분류)으로 고른 {n_wl if n_wl is not None else '—'}개입니다"),
            ("코드", "FSG · FSC(군급)", "미 연방보급분류. FSG = 앞 2자리 그룹, FSC = 4자리 군급"),
            ("코드", "전자 군급(FSG 58 · 59 · 60)", "58 = 통신 · 탐지 및 코히런트 방사 장비, 59 = 전기 및 전자 장비 구성품, 60 = 광섬유 재료 · 구성품"),
            ("코드", "NSN(국가재고번호)", "군수품 13자리 번호(숫자 · 영숫자). 앞 4자리가 FSC라서 전자 군급(58 · 59 · 60) 여부를 가릴 수 있습니다"),
            ("지표", "1위 공급국 점유율", "1위 국가 수입액 ÷ 품목군 수입액"),
            ("지표", "집중도(HHI)", "Σ(국가별 점유율 %)², 0~10,000. 2,500 이상 = 높은 집중. 수입 집중도이며 위험도가 아닙니다"),
            ("지표", "선적국", "관세청 통계의 국가 기준. 원산지와 다를 수 있습니다(홍콩 · 싱가포르 경유 등)"),
            ("지표", "민수 포함", "수입액 · 수출액은 국가 전체 교역액입니다. 군수 몫만 따로 떼어 낸 통계는 없습니다"),
            ("자료", "국외 조달계획", "방위사업청이 공개하는 품목 단위 국외 조달 계획. 계획이지 계약 · 실적이 아닙니다"),
            ("자료", "국산화개발품목", f"방위사업청 국산화개발 완료 부품 목록({b2_txt}). 부품 수이지 국산화율이 아닙니다"),
            ("표시", "부분연도", "1년이 다 차지 않은 해(2026년은 8월까지). 연간 비교 · KPI · 전년비에서 뺍니다"),
            ("표시", "잠정", "정제 · 산출식 확정 전 값(KOSIS 잠정치 등). 확정 뒤 표시를 뗍니다"),
            ("표시", "후보", "키워드 · 코드 규칙으로 걸렸지만 아직 검수하지 않은 행(예: 대표품명 키워드로 뽑은 전자 관련 후보). "
                            "검증된 분석 대상과 구분하며 확정 값으로 쓰지 않습니다"),
        ], columns=["구분", "용어", "뜻"])
        by_kind = terms["구분"].value_counts()
        card_title(st, f'화면에서 만나는 용어 <span class="key">{len(terms)}개</span> — ' + " · ".join(f"{k} {by_kind.get(k, 0)}" for k in ("코드", "지표", "자료", "표시")),
                   "구분 · 용어 · 뜻 · 표 오른쪽 위 돋보기로 찾을 수 있습니다 · 계산식은 위 「지표는 이렇게 계산합니다」 카드가 기준")
        st.dataframe(terms, hide_index=True, width="stretch", height=38 + 35 * len(terms),
                     column_config={"구분": st.column_config.TextColumn(width="small"), "용어": st.column_config.TextColumn(width="medium"),
                                    "뜻": st.column_config.TextColumn(width="large")})
        csv_button(terms, "조건 없음 · 화면 용어 전체", "팀 작성 용어 정의", [("품목군 기준표", stamp_wl, None)], "데이터정보_용어", "p5_csv_terms")
        chart_source("팀 작성 용어 정의 · 코드는 관세청 HS 분류와 미 연방보급분류(FSG · FSC) 공식 명칭 · "
                     f"국산화개발 사업 수는 국산화개발품목 자료의 사업명 수({stamp_txt('국산화개발품목', stamp_local)})")

    # ── 3. 제외한 데이터 ────────────────────────────────────────────────────────
    with st.expander("쓰지 않은 데이터와 이유"):
        ex = pd.DataFrame([
            ("국외조달 입찰결과", "2025.03~09 6개월뿐, 전자 후보 9건. 행 = 품목이라 유찰률이 부풀려짐"),
            ("국외조달 계약정보", "금액 · 국가가 없고 조달계획과 역할이 겹침"),
            ("국내 입찰공고 · 입찰결과", "전자부품과 연결할 공통 식별자(군급 · 재고번호)가 없음"),
            ("군별 계약 집행 · 국내 조달계획", "부품 단위로 연결되지 않음"),
            ("사전의향서 CSV", "현재조달원이 전부 내자(국내)라 국외 조달 여부를 가를 수 없음"),
            ("국방표준종합서비스(2016)", "2016 한 시점 스냅샷이라 연도 축이 없고, 국산화 목록과 교집합이 거의 없음"),
            ("무기체계별 부품 구성(BOM) · 생산 대수", "비공개(군사기밀 · 영업비밀). 추정 · 역산하지 않음"),
            ("군용만 따로 뗀 반도체 수입액", "HS 코드는 용도(군용 · 민수)를 구분하지 않아 존재하지 않는 통계"),
            ("관세청 시군구별 수출입실적(과천 비중 추정)", "수입자 주소지 기준이라 신고자가 방위사업청인지 공개 자료로 확인되지 않음(가설) — 2026-09-28 화면에서 뺌"),
        ], columns=["데이터", "이유"])
        card_title(st, f'화면에 쓰지 않은 데이터 <span class="key">{len(ex)}종</span> — '
                       "부품 단위로 이을 식별자가 없거나, 기간 · 항목이 모자라거나, 비공개이거나, 존재하지 않는 통계",
                   "데이터 · 쓰지 않은 이유 · 표 오른쪽 위 돋보기로 찾을 수 있습니다")
        st.dataframe(ex, hide_index=True, width="stretch")
        csv_button(ex, "조건 없음 · 화면에 쓰지 않은 데이터 전체", "팀 데이터 사용 결정 기록(2026-09-18)",
                   [("관세청 수출입", stamp_customs, None)], "데이터정보_제외데이터", "p5_csv_ex")
        caption("일부(입찰 · 조달계획 등)는 위 출처 표에 있으나 화면에 쓰지 않습니다")
        chart_source("팀 데이터 사용 결정 기록(2026-09-18) · 팀 기획 검토")

    # ── 4. 과장 금지 ────────────────────────────────────────────────────────────
    with st.expander("이 대시보드가 말하지 않는 것"):
        card_title(st, "수입액은 민수를 포함한 국가 전체 교역액이고, 집중도(HHI)는 위험도가 아니며, 조달 계획과 수입 실적은 합치거나 직접 비교하지 않는다",
                   "수치 해석 5항 · 표현 범위 4항")
        st.html(cards([
            ("수치 해석", bullets([
                "수입액은 <b>국가 전체 수입(민수 포함)</b>입니다. 군수 몫만 떼어 낸 금액이 아니며, 그런 공식 통계는 없습니다",
                "HHI · 점유율은 <b>수입 집중도</b>이며 군수 수요 규모나 위험도를 뜻하지 않습니다. 예측 · 조기경보 · 실시간 감시를 하지 않습니다",
                "국외 조달계획은 <b>계획(원화 예정액)</b>, 관세청 수입액은 <b>실적(달러)</b>입니다. 합산 · 비율 · 직접 비교하지 않습니다(직접 비교 불가)",
                f"국산화개발 부품 수는 <b>완료 부품 목록</b>({b2_txt})이며 국산화율이 아닙니다. 빈칸은 「국산화 안 됨」이 아니라 「이 자료에 없음」",
                "HS 품목군(관세청)과 군급(방사청)은 <b>연결하지 않습니다</b>. 특정 부품의 수입국 → 무기체계 → 국산화 상태를 잇는 설명은 이 자료로 할 수 없고, "
                "두 축을 나란히 놓을 뿐입니다"])),
            ("표현 범위", bullets([
                "특정 기업 · 특정 무기체계의 취약 부품을 지목하지 않습니다. 품목군 · 군급 단위로만 집계합니다",
                "부대 위치 · 전력 수량 · 부품 구성은 수집 · 추정 · 역산하지 않습니다",
                "계약업체 주소는 생산시설 · 납품 위치가 아닙니다",
                "「잠정」 표시 값은 정제 · 산출식 확정 전입니다. 확정 뒤 표시를 뗍니다"])),
        ], "7fr 5fr"))
        chart_source("팀 기획 검토의 유의사항 · 팀 정제 공통 규칙")

with st.expander("산식 · 출처 · 표현 범위"):
    st.markdown("**이 화면의 숫자**  \n"
                "**원본 건수** = 내려받은 원본 파일을 파서로 센 레코드 수. 5단계 보고의 「원본 전체」.  \n"
                "**깔때기** = 입찰 공고 행 수 → 입찰 결과 행 수 → 공고와 연결된 결과 행 수 → 공고 1건과만 맞는 결과 행 수"
                "(연결 판정 = 공고번호 + 차수 대조).  \n"
                "**분석 대상 품목군 수** = 품목군 기준표에서 진입 규칙(군용 전용 세분류 또는 전문 용도 명시)에 해당하는 품목군 수. 나머지는 배경 자료.  \n"
                "**규칙 판정 범위** = HS 84·85·88·90류 HS6 전수.  \n"
                "**국산화개발 사업 수** = 국산화개발품목 자료의 서로 다른 사업명 수.  \n\n"
                "**출처** — 위 「데이터 출처」 표의 공개 자료(기관 · 데이터 · 포털 ID).")

chart_source("위 데이터 출처 표의 공개 자료 · 팀 품목 선정 규칙 · 팀 정제 공통 규칙 · 팀 데이터 사용 결정 기록")
