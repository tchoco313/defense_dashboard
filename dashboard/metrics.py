"""순수 계산·판정 함수 — streamlit·DB 를 import 하지 않는다(tests/test_metrics.py 가 그대로 import).

- concentration: 홈·③·🔎 KPI 가 같은 단위(hs6 × 국가, 선택 연도 합산 뒤 점유율)로 쓰는 집중도 계산.
  ①은 DB 뷰(v_hhi_hs6_year, 단일 연도)를 그대로 읽으므로 여기를 쓰지 않는다 — 여러 해 합산 HHI 와 연도별 HHI 는 다른 지표.
- period_years: 기간 선택지(기준 연도 / 최근 5년 / 전체)의 연도 목록. 완결 연도만 받는다(부분연도는 호출부에서 뺀다).
- count_state: safe/try_query 결과를 「조회 실패 / 미적재 / 실제 0 / n」 네 상태(failed/unloaded/zero/ok)로 나눈다(실제 0 과 미적재·조회 실패를 구분).
"""
from __future__ import annotations

import pandas as pd

CONC_COLS = ["hs6", "total", "top1_stat_cd", "top1_share", "top3_share", "hhi", "country_count"]


def _empty_conc() -> pd.DataFrame:
    return pd.DataFrame({"hs6": pd.Series(dtype="str"), "total": pd.Series(dtype="float64"),
                         "top1_stat_cd": pd.Series(dtype="str"), "top1_share": pd.Series(dtype="float64"),
                         "top3_share": pd.Series(dtype="float64"), "hhi": pd.Series(dtype="float64"), "country_count": pd.Series(dtype="int64")})


def concentration(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """hs6 × stat_cd 행(여러 연도가 섞여 있어도 됨 — 연도 필터는 호출부) → hs6 별 집중도.

    단위: hs6 × 국가, 선택 연도를 합산한 뒤 점유율.
    - 국가 = value > 0 인 stat_cd 만(0·NaN·음수는 국가로 세지 않는다 → 수출만 있는 국가는 수입 국가 수에서 빠진다)
    - total = 양수 합 · top1_share 0~1 · top3_share = 상위 3개국 점유율 합 0~1(국가가 3개 미만이면 있는 만큼) · hhi = Σ(share×100)² (0~10,000) · country_count = 양수 국가 수
    - 합계 0 인 hs6 는 결과에 없다(= 이 기간 실적 없음. 호출부는 join 뒤 NaN 으로 구분). 빈 입력 → 열만 있는 빈 표
    - 1위 동률: value 내림차순 → stat_cd **내림차순** — DB 뷰 v_hhi_hs6_year 의 `MAX(CASE WHEN rnk=1 THEN stat_cd END)` 와 같은 규칙
      (단일 연도를 넣으면 뷰와 같은 1위국·점유율·HHI 가 나와야 한다. 2026-09-20 실측: 1위 자리 동률 0건)
    """
    if df.empty:
        return _empty_conc()
    pos = df.loc[df[value_col] > 0, ["hs6", "stat_cd", value_col]]
    by_c = pos.groupby(["hs6", "stat_cd"], as_index=False)[value_col].sum()
    if by_c.empty:
        return _empty_conc()
    by_c = by_c.assign(share=by_c[value_col] / by_c.groupby("hs6")[value_col].transform("sum"))
    ranked = by_c.sort_values(["hs6", value_col, "stat_cd"], ascending=[True, False, False], kind="stable")
    top1 = ranked.drop_duplicates("hs6").set_index("hs6")
    top3 = ranked.groupby("hs6").head(3).groupby("hs6")["share"].sum()   # 3위 동률은 1위와 같은 규칙으로 3개만
    g = by_c.groupby("hs6")
    out = pd.DataFrame({"total": g[value_col].sum().astype("float64"),
                        "top1_stat_cd": top1["stat_cd"],
                        "top1_share": top1["share"].astype("float64"),
                        "top3_share": top3.astype("float64"),
                        "hhi": by_c.assign(sq=(by_c["share"] * 100) ** 2).groupby("hs6")["sq"].sum().astype("float64"),
                        "country_count": g["stat_cd"].nunique().astype("int64")})
    return out.reset_index().loc[:, CONC_COLS]


def period_years(full_years) -> dict[str, list[int]]:
    """완결 연도 목록 → {'base': [최근 완결 연도], 'recent5': 최근 5년(자료 시작 연도 하한, 완결 연도만), 'all': 완결 연도 전부}.
    빈 입력 → {} (호출부가 안내 후 멈춘다). 연속 범위가 아니라 실제 있는 완결 연도만 돌려준다."""
    ys = sorted({int(y) for y in full_years})
    if not ys:
        return {}
    y1, y0 = ys[-1], ys[0]
    return {"base": [y1], "recent5": [y for y in ys if y >= max(y0, y1 - 4)], "all": ys}


def count_state(df: pd.DataFrame | None, err: str | None, col: str, total_col: str | None = None) -> tuple[str, int | None]:
    """COUNT 한 줄 결과를 네 상태로 나눈다(실제 0 과 미적재·조회 실패를 섞지 않는다).

    ('failed', None)  조회 실패(err = 예외 클래스명) 또는 df None
    ('unloaded', 0)   total_col(표 전체 행 수)이 0/NULL/빈 결과 = 표는 있으나 적재 0행. total_col 이 없으면 결과 0행/NULL 을 여기로
    ('zero', 0)       표에 행은 있으나 조건에 맞는 행이 0 = 실제 0
    ('ok', n)
    """
    if err or df is None:
        return "failed", None
    if df.empty:
        return "unloaded", 0
    row = df.iloc[0]
    if total_col is not None:
        if pd.isna(row[total_col]) or int(row[total_col]) == 0:
            return "unloaded", 0
        n = 0 if pd.isna(row[col]) else int(row[col])
        return ("zero", 0) if n == 0 else ("ok", n)
    if pd.isna(row[col]) or int(row[col]) == 0:
        return "unloaded", 0
    return "ok", int(row[col])
