# -*- coding: utf-8 -*-
"""방위사업청 조달 데이터 전처리 — 원본 CSV → 분석용 CSV

    python3 src/preprocess.py

읽는 곳  data/raw/*.csv        (src/fetch_data.py 로 먼저 받는다)
쓰는 곳  data/clean/*.csv

★ 이 파일은 EDA 보고서의 「전처리」 절이 된다. 무엇을 왜 했는지 주석으로 남긴다.

──────────────────────────────────────────────────────────────────────
이 데이터에서 실제로 확인한 것 (2026-09-11, 43,112행 기준)
  · 금액에 쉼표가 없다. 날짜가 이미 YYYY-MM-DD 다. 변환 실패 0건
  · 완전중복 0건. 28개 컬럼 중 22개가 결측 0%
  · 컬럼명에 공백·괄호가 없어 MySQL 에 그대로 들어간다
  → 흔한 함정은 거의 없다. 대신 「판단」 이 필요한 자리가 셋 있다. 아래 ★ 표시.
──────────────────────────────────────────────────────────────────────
"""
import re
import pathlib
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
CLEAN = BASE / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

ENC = "cp949"          # ★ 공공데이터포털 파일은 대부분 cp949 다. utf-8 로 열면 깨진다.


def read(name: str) -> pd.DataFrame:
    """원본 CSV 를 전부 문자열로 읽는다.

    dtype=str 로 읽는 이유: pandas 가 알아서 숫자로 바꾸면
    '0012' 같은 코드가 12 가 되어 조인이 깨진다. 필요한 컬럼만 뒤에서 숫자로 바꾼다.
    """
    path = RAW / name
    if not path.exists():
        raise SystemExit(f"없다: {path}\n먼저 `python3 src/fetch_data.py` 를 돌려라.")
    return pd.read_csv(path, encoding=ENC, low_memory=False, dtype=str)


def to_num(s: pd.Series) -> pd.Series:
    """문자열을 숫자로. 쉼표와 공백을 먼저 지운다."""
    return pd.to_numeric(s.astype(str).str.replace(r"[,\s]", "", regex=True), errors="coerce")


def norm_company(s: pd.Series) -> pd.Series:
    """기업명 표기를 통일한다.

    ★ 판단 1 — 같은 회사가 다르게 적혀 있다.
      '주식회사' 17,539건 · '(주)' 6,590건 · '㈜' 16건 · '유한회사' 261건.
      이걸 지우고 공백을 없애면 14,430개 → 14,146개로 284개가 합쳐진다.
      지우지 않으면 「한화시스템」과 「(주)한화시스템」이 남남이 되어 기업별 집계가 틀린다.
    """
    return (s.fillna("")
             .str.replace(r"\(주\)|㈜|주식회사|유한회사|\(유\)|㈜", "", regex=True)
             .str.replace(r"\s+", "", regex=True)
             .str.strip())


def split_period(s: pd.Series):
    """'2024-11-01~2024-12-01' 처럼 한 칸에 든 두 날짜를 둘로 쪼갠다."""
    parts = s.fillna("").str.split("~", n=1, expand=True)
    if parts.shape[1] < 2:
        parts[1] = None
    a = pd.to_datetime(parts[0].str.strip(), errors="coerce")
    b = pd.to_datetime(parts[1].str.strip(), errors="coerce")
    return a, b


# ── 1. 계약정보 (국내조달·시설공사 공통) ─────────────────────────────
def clean_contract(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    d = df.copy()
    d.columns = [c.strip() for c in d.columns]

    for col in ["계약금액", "예정가격", "총계약금액"]:
        if col in d:
            d[col] = to_num(d[col])

    d["계약체결일자"] = pd.to_datetime(d["계약체결일자"], errors="coerce")
    d["연월"] = d["계약체결일자"].dt.to_period("M").astype(str)
    d["계약시작일"], d["계약종료일"] = split_period(d.get("계약기간", pd.Series(dtype=str)))

    d["기업"] = norm_company(d["대표업체명"])
    d["시도"] = d["대표업체주소"].fillna("").str.split().str[0].replace("", np.nan)

    # ★ 판단 2 — 부대는 「수요기관명」에 없다.
    #   수요기관명은 값이 2개뿐이다 ('국방부(부대)', '방위사업청').
    #   실제 부대는 수요기관담당부서명에 224종 들어 있다. 시설공사 파일에는
    #   수요기관담당부서명이 없어서 계약기관담당부서명을 쓴다.
    for cand in ["수요기관담당부서명", "계약기관담당부서명"]:
        if cand in d.columns:
            d["부대"] = d[cand]
            break
    else:
        d["부대"] = np.nan

    d["경쟁여부"] = np.where(d["계약체결방법명"] == "수의계약", "수의", "경쟁")

    # 낙찰률 = 예정가격 대비 실제 계약금액. 낮을수록 싸게 산 것.
    d["낙찰률"] = np.where(d["예정가격"] > 0, d["계약금액"] / d["예정가격"] * 100, np.nan)

    # ★ 판단 3 — 이상치를 버리지 말고 «표시»한다.
    #   예정가격이 301원인데 계약금액이 3.3억인 건이 있다. 이런 게 1.9% 섞여
    #   평균 낙찰률을 314,645% 로 만든다 (중앙값은 99.9% 로 멀쩡하다).
    #   버리면 왜 버렸는지 설명할 근거가 사라지므로 컬럼으로 남긴다.
    d["낙찰률이상"] = (d["낙찰률"] < 50) | (d["낙찰률"] > 110)

    # ★★ 가장 조심할 것 — 수의계약사유가 29.8% 비어 있다고 dropna() 하지 마라.
    #    수의계약 30,255건은 사유가 100% 있고, 경쟁계약 12,857건은 0% 다.
    #    «결측» 이 아니라 «해당 없음» 이다. 지우면 경쟁계약이 통째로 사라지고,
    #    그러면 「경쟁이 싸다」 는 분석 자체가 불가능해진다.
    if "수의계약사유" in d.columns:
        d["수의계약사유"] = d["수의계약사유"].fillna("해당없음")

    d["구분"] = kind
    return d


# ── 2. 사전의향서 — 품목·수량·단가가 있는 유일한 파일 ────────────────
def clean_intent(df: pd.DataFrame, fsc: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d.columns = [c.strip() for c in d.columns]
    for col in ["요구수량", "요구단가", "요구금액"]:
        d[col] = to_num(d[col])
    d["요구일자"] = pd.to_datetime(d["요구일자"], errors="coerce")

    # 재고번호(NSN) 앞 4자리가 군급(FSC)이다. 이걸로 품목을 큰 갈래로 묶는다.
    d["FSC"] = d["재고번호"].astype(str).str.replace("-", "", regex=False).str[:4]
    d = d.merge(fsc[["군급", "명칭(한글)"]].rename(columns={"명칭(한글)": "군급명"}),
                left_on="FSC", right_on="군급", how="left")
    # 못 붙은 2.4% 는 폐지된 코드다. 억지로 채우지 않고 표시만 한다.
    d["군급명"] = d["군급명"].fillna("미분류")
    d["FSC대분류"] = d["FSC"].str[:2]
    return d.drop(columns=["군급"], errors="ignore")


# ── 3. 입찰 — 공고와 결과를 공고번호로 잇는다 ────────────────────────
def clean_bid(공고: pd.DataFrame, 결과: pd.DataFrame) -> pd.DataFrame:
    a = 공고.copy(); a.columns = [c.strip() for c in a.columns]
    b = 결과.copy(); b.columns = [c.strip() for c in b.columns]
    for col in ["예산금액", "배정예산금액(설계금액)"]:
        if col in a: a[col] = to_num(a[col])
    for col in ["예정가격", "기초금액", "추정가격", "최종낙찰금액", "최종낙찰율", "낙찰하한율"]:
        if col in b: b[col] = to_num(b[col])
    a["입찰공고일자"] = pd.to_datetime(a["입찰공고일자"], errors="coerce")
    b["개찰일자"] = pd.to_datetime(b["개찰일자"], errors="coerce")
    b["낙찰기업"] = norm_company(b["최종낙찰업체명"])

    # ★ 판단 4 — 공고번호만으로 이으면 행이 «부풀어» 오른다.
    #   입찰공고 10,842행에 공고번호는 7,817개뿐이다. 같은 번호에 차수가 여럿이라
    #   번호만으로 조인하면 결과 7,405행이 10,007행이 된다 (2,602행 증가).
    #   오류가 안 나고 조용히 늘어나므로 «조인 뒤에 행 수를 세지 않으면 모른다».
    #   → 번호 + 차수로 잇고, 공고쪽 중복 356건을 먼저 지운다.
    keys = ["입찰공고번호", "입찰공고차수"]
    a1 = a.drop_duplicates(keys)
    before = len(b)
    m = b.merge(a1[keys + ["입찰공고일자", "예산금액", "수요기관명"]],
                on=keys, how="left", suffixes=("", "_공고"))
    assert len(m) == before, f"조인이 행을 늘렸다: {before} → {len(m)}"
    m["공고연결"] = m["입찰공고일자"].notna()
    return m


def main():
    print("원본 읽는 중 …")
    계약 = read("dapa_국내조달_계약정보.csv")
    시설 = read("dapa_시설공사_계약정보.csv")
    사전 = read("dapa_국방전자조달_사전의향서.csv")
    군급 = read("dapa_군급분류집_FSC.csv")
    공고 = read("dapa_국내조달_경쟁_입찰공고.csv")
    결과 = read("dapa_국내조달_경쟁_입찰결과.csv")

    out = {}
    out["contract_domestic"] = clean_contract(계약, "국내조달")
    out["contract_facility"] = clean_contract(시설, "시설공사")
    out["intent_item"] = clean_intent(사전, 군급)
    out["bid"] = clean_bid(공고, 결과)

    print()
    for name, d in out.items():
        p = CLEAN / f"{name}.csv"
        d.to_csv(p, index=False, encoding="utf-8-sig")   # 엑셀에서 열어도 안 깨지게
        print(f"  {name:20} {len(d):>7,}행 × {len(d.columns):>3}열  → {p.name}")

    # ── 검산: 전처리가 제대로 됐는지 눈으로 본다 ──────────────────────
    c = out["contract_domestic"]
    print("\n검산")
    print(f"  계약금액 숫자 변환    {c['계약금액'].notna().sum():,}/{len(c):,}")
    print(f"  계약기간 분리        {c['계약시작일'].notna().sum():,}/{len(c):,}")
    print(f"  기업명 정규화        {c['대표업체명'].nunique():,}개 → {c['기업'].nunique():,}개")
    print(f"  낙찰률 이상 표시      {c['낙찰률이상'].sum():,}건 ({c['낙찰률이상'].mean()*100:.1f}%)")
    print(f"  수의계약사유 채움     결측 {c['수의계약사유'].isna().sum()}건 (0이어야 정상)")
    ok = c[~c["낙찰률이상"]]
    print("\n  계약방법별 평균 낙찰률 (이상치 제외)")
    print("   " + ok.groupby("경쟁여부")["낙찰률"].agg(["size", "mean"]).round(2).to_string().replace("\n", "\n   "))
    i = out["intent_item"]
    print(f"\n  품목 군급 매칭       {(i['군급명'] != '미분류').mean()*100:.1f}%")
    b = out["bid"]
    print(f"  입찰 공고-결과 연결   {b['공고연결'].mean()*100:.1f}%")


if __name__ == "__main__":
    main()
