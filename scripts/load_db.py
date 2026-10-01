"""운영 DB(AWS RDS defense_dashboard) 적재 스크립트 — ref_ / meta_ / dim_·fact_ 계층 + 원본 파일 읽기(read_raw).

원본은 DB에 넣지 않는다. data/raw/ 파일이 원본이며,
정제 노트북과 --fact 는 read_raw(<데이터셋 키>) 로 파일을 pandas DataFrame 으로 읽는다. RAW_TABLES 의 키(raw_…)는 옛 raw_ 표 이름을
그대로 물려받은 **원본 파일 데이터셋 키**로, meta_dataset.target_table · clean_excluded_row.table_name · db/column_dict.csv(원본 파일
열 사전) 와 같은 값이다. read_raw 가 매기는 row_id(파일명 정렬 × 파일 내 행 순, 1부터)가 clean_*.raw_row_id 의 정의다.

접속은 scripts/dbconf.py(.env 의 MARIADB_*, 기본 계정 etl_rw, TLS). LOAD DATA LOCAL 은 쓰지 않고 pymysql executemany 로 넣는다.
열 매핑은 db/column_dict.csv 의 (table_name, ordinal, column_name, original_name) 을 기준으로 CSV 헤더를 순서 대조한다.
clean_ 계층은 다루지 않는다(정제 규칙은 노트북 영역, notebooks/clean_*.ipynb).

사용:
  python scripts/load_db.py --dry-run                 # 원본 파일 파싱·헤더 대조·건수만 (DB 접속 없음)
  python scripts/load_db.py --dry-run --tables raw_dapa_contract raw_krit_task
  python scripts/load_db.py --ref                     # ref_hs_whitelist·ref_country·meta_column_dict·meta_dataset + db/seed_ref.sql
                                                      #   (시드가 DB와 다르면 시드는 건너뛰고 차이를 출력 — 덮어쓰려면 --seed-overwrite)
  python scripts/load_db.py --fact                    # dim_hs10·fact_customs_monthly 를 관세청 원본 파일에서 pandas 로 만들어 적재
  python scripts/load_db.py --verify                  # 건수 대조표만 출력

재적재는 하지 않는다: 대상 테이블이 비어 있지 않으면 건너뛴다. 먼저 db/reset_data.sql 로 비운다.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dbconf  # noqa: E402  접속 설정 단일 지점

if hasattr(sys.stdout, "reconfigure"):  # Jupyter 커널(OutStream)에는 없음
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
COLUMN_DICT = ROOT / "db" / "column_dict.csv"
META_DATASET_CSV = ROOT / "db" / "meta_dataset.csv"
SEED_SQL = ROOT / "db" / "seed_ref.sql"
BATCH = 2000
SCRIPT_TAG = "scripts/load_db.py"

# ---------------------------------------------------------------------------
# 원본 파일 데이터셋별 파일·인코딩·기대 건수 (docs/db/schema-design.md §3-2 원본 파일 계층)
#   키          는 원본 파일 데이터셋 키(옛 raw_ 표 이름 그대로) — column_dict.csv 의 table_name 과 같다
#   dataset_key 는 meta_dataset.dataset_key (meta_load_log FK)
#   null_cols   는 개인정보 열 → 읽을 때 NULL
#   int_cols    는 원본 중 유일한 정수 열
# ---------------------------------------------------------------------------
RAW_TABLES: dict[str, dict] = {
    "raw_customs_trade": dict(
        files="data/raw/customs/customs_all_*.csv", encoding="utf-8", expected=294_420,   # 24개 = 21개 268,909 + 852910·901410·901490 25,511
        dataset_key="customs_all", tier="핵심"),
    "raw_customs_progress": dict(
        files="data/raw/customs/progress_all.csv", encoding="utf-8", expected=264,   # 231 + 33
        dataset_key="customs_progress", int_cols={"row_count"}, tier="메타"),
    "raw_customs_region": dict(
        files="data/raw/customs/customs_region_*.csv", encoding="utf-8", expected=273_586,   # HS6 24개(시군구별 15134343). 금액 천 달러
        dataset_key="customs_region", tier="보조"),
    "raw_dapa_contract": dict(
        files="data/raw/dapa/dapa_domestic_contract_20251231.csv", encoding="cp949", expected=43_112,
        dataset_key="dapa_contract", tier="핵심"),
    "raw_dapa_localized_item": dict(
        files="data/raw/dapa/dapa_localized_items_20260509.csv", encoding="cp949", expected=33_965,
        dataset_key="dapa_localized_item", tier="핵심"),
    "raw_krit_task": dict(
        files="data/raw/krit/*_t*.csv", encoding="utf-8-sig", expected=96,   # 26-1차 2 + PDF 5건 74 + 26-2차 본공고(hwp) 20
        dataset_key="krit_task", special="krit", tier="핵심"),
    "raw_dapa_bid_notice": dict(
        files="data/raw/dapa/dapa_domestic_bid_notice_20251231.csv", encoding="cp949", expected=10_842,
        dataset_key="dapa_bid_notice", tier="보조"),
    "raw_dapa_bid_result": dict(
        files="data/raw/dapa/dapa_domestic_bid_result_20251231.csv", encoding="cp949", expected=7_405,
        dataset_key="dapa_bid_result", tier="보조"),
    "raw_dapa_defense_company": dict(
        files="data/raw/dapa/dapa_defense_company_20260831.csv", encoding="cp949", expected=84,
        dataset_key="dapa_defense_company", tier="보조"),
    "raw_kosis_utilization": dict(
        files="data/raw/kosis/kosis_409_utilization_by_sector_2016_2024.csv", encoding="cp949", expected=81,
        dataset_key="kosis_utilization", special="kosis_wide1", tier="보조"),
    "raw_kosis_production_index": dict(
        files="data/raw/kosis/kosis_101_production_index_c26_201601_202607.csv", encoding="cp949", expected=1_016,
        dataset_key="kosis_production_index", special="kosis_wide2", tier="보조"),
    "raw_dapa_overseas_plan": dict(
        files="data/raw/dapa/dapa_overseas_plan_20251231.csv", encoding="cp949", expected=3_029,
        dataset_key="dapa_overseas_plan", null_cols={"officer_name"}, tier="핵심"),
    "raw_dapa_overseas_contract": dict(
        files="data/raw/dapa/dapa_overseas_contract_20251231.csv", encoding="cp949", expected=6_333,
        dataset_key="dapa_overseas_contract", null_cols={"contract_org_officer_name"}, tier="보조"),
    "raw_dapa_overseas_bid_result": dict(
        files="data/raw/dapa/dapa_overseas_bid_result_20250915.csv", encoding="cp949", expected=2_494,
        dataset_key="dapa_overseas_bid_result", tier="보조"),
    "raw_dapa_domestic_plan": dict(
        files="data/raw/dapa/dapa_domestic_plan_20251231.csv", encoding="cp949", expected=35_859,
        dataset_key="dapa_domestic_plan", null_cols={"officer_name", "officer_phone"}, tier="보조"),
    "raw_dapa_contract_exec_by_service": dict(
        files="data/raw/dapa/dapa_contract_exec_by_service_20241231.csv", encoding="cp949", expected=40,
        dataset_key="dapa_contract_exec_by_service", tier="보조"),
    # 무역안보관리원 HSK 연계표(data.go.kr 15034135). utf-8-sig, 2,161행(포털 표시와 일치), 헤더 품목번호·품명(국문)·품명(영문)·통제번호.
    # 통제번호는 쉼표 목록(최대 1,218자) → clean_hsk_control 에서 통제번호별 세로형으로 편다.
    "raw_hsk_control": dict(
        files="data/raw/kosti/hsk_control_15034135.csv", encoding="utf-8-sig", expected=2_161,
        dataset_key="kosti_hsk_control", tier="보조"),
    # 관세청 HS부호 마스터(data.go.kr 15049722, XLSX 1시트 20열) · HS부호 단위별 품목명(15130660, XLSX 5시트) — HS6 선정 규칙(schema.sql §6 v_hs6_candidate_rule)의 원본.
    # 행 수: 마스터 12,469행 · 단위별 품목명 5시트 합 17,072행(포털 표시와 일치). .xlsx 는 pandas read_excel(openpyxl)로 읽는다.
    # 마스터는 frame_generic(첫 시트, 열 순서 column_dict 대조), 단위별 품목명은 special='hs_unit'(시트마다 첫 열 이름이 달라 5시트를 세로로 합침).
    "raw_hs_code_master": dict(
        files="data/raw/customs/hs_code_master_15049722.xlsx", encoding=None, expected=12_469,
        dataset_key="customs_hs_code_master", tier="참조"),
    "raw_hs_unit_name": dict(
        files="data/raw/customs/hs_unit_name_15130660.xlsx", encoding=None, expected=17_072,
        dataset_key="customs_hs_unit_name", special="hs_unit", tier="참조"),
    # 아래 3종은 팀 드라이브 수집본(국외 조달계획 API · 군급분류집 · 열린재정 예산).
    # 국외 조달계획 OpenAPI 품목 단위(15158418, 요구연도별 호출) — 파일판 raw_dapa_overseas_plan(사업 단위·원)과 다른 표. 헤더 24열 utf-8-sig, 13,615행.
    "raw_dapa_overseas_plan_api": dict(
        files="data/raw/dapa/dapa_overseas_plan_api_20260916.csv", encoding="utf-8-sig", expected=13_615,
        dataset_key="dapa_overseas_plan_api", tier="핵심"),
    # 군급분류집(15119907) cp949 10열 756행(FSG 그룹행 80 + FSC 676) → ref_fsc 의 원천.
    "raw_dapa_fsc_catalog": dict(
        files="data/raw/dapa/dapa_fsc_catalog_20251231.csv", encoding="cp949", expected=756,
        dataset_key="dapa_fsc_catalog", tier="참조"),
    # 열린재정 세부사업 예산편성현황(총액) 방위사업청·일반회계, 회계연도별 12파일(2016~2027) utf-8-sig 14열, 합 2,860행(2020~2027 1,981 + 2016~2019 879). 마지막 줄 개행 없음.
    "raw_openfiscal_program_budget": dict(
        files="data/raw/budget/openfiscal_dapa_program_budget_*.csv", encoding="utf-8-sig", expected=2_860,
        dataset_key="openfiscal_program_budget", tier="보조"),
    # 국방표준종합서비스(KDSIS) NSN 목록 정리본(원본 두 파일 .txt+2016.csv 합본). new_data/ 에 두고 읽는다.
    # utf-8-sig 22열 228,027행. CSV의 source_file/source_row_no 열은 origin_file/origin_row_no 로 들어가고, DB의 source_file/source_row_no 는 frame_generic 이 붙인다.
    "raw_kdsis_nsn": dict(
        files="new_data/raw_kdsis_nsn.csv", encoding="utf-8-sig", expected=228_027,
        dataset_key="kdsis_nsn", int_cols={"origin_row_no"}, tier="보조"),
}

REF_EXPECTED = {"ref_hs_whitelist": 24, "ref_country": 238, "meta_column_dict": 916}  # 916 = db/column_dict.csv 행 수
# 국방반도체 발전전략 참조표 — (표, data/reference 파일, 기대 행 수). CSV 의 date 열은 event_date 로,
# 추진 경과는 CSV 행 순서를 row_no 로 붙인다. 표가 비어 있을 때만 채운다(다시 넣으려면 그 표를 비운다)
SEMI_REF = [("ref_semi_chip_type", "semi_chip_type.csv", 7), ("ref_semi_domestic_case", "semi_domestic_case.csv", 13),
            ("ref_semi_market_share", "semi_market_share.csv", 16), ("ref_semi_policy_timeline", "semi_policy_timeline.csv", 12),
            ("ref_semi_public_fab", "semi_public_fab.csv", 14), ("ref_semi_strategy_task", "semi_strategy_task.csv", 12),
            ("ref_semi_stat", "semi_stat.csv", 2)]


# ---------------------------------------------------------------------------
# 공통
# ---------------------------------------------------------------------------
def connect():
    """운영 DB(RDS) 접속 — 접속 정보·TLS 는 scripts/dbconf.py 가 .env 의 MARIADB_* 에서 읽는다(기본 역할 etl_rw)."""
    return pymysql.connect(**dbconf.pymysql_kwargs("etl", autocommit=False, local_infile=False))


def read_column_dict() -> dict[str, list[tuple[int, str, str]]]:
    """table_name -> [(ordinal, column_name, original_name)] (ordinal 순)."""
    out: dict[str, list[tuple[int, str, str]]] = {}
    with open(COLUMN_DICT, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["table_name"], []).append((int(r["ordinal"]), r["column_name"], r["original_name"]))
    for k in out:
        out[k].sort()
    return out


def norm_header(h: str) -> str:
    return h.replace("\ufeff", "").replace("\r\n", "\\n").replace("\n", "\\n").strip()


def read_csv_str(path: Path, encoding: str, **kw) -> pd.DataFrame:
    """CSV 는 pandas read_csv(전 열 문자열). .xlsx 는 read_excel(openpyxl, 첫 시트) 후 NaN 을 빈 문자열로 — 두 경로 모두 빈 셀은 nz()에서 NULL."""
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        return pd.read_excel(path, dtype=str, sheet_name=0, engine="openpyxl", **kw).fillna("")
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False, encoding=encoding, **kw)


def nz(v):
    """빈 문자열 → NULL. 나머지는 원문 문자열 그대로."""
    if v is None:
        return None
    if isinstance(v, str):
        return v if v != "" else None
    return v


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def table_count(cur, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM `{table}`")
    return cur.fetchone()[0]


def insert_rows(cur, table: str, cols: list[str], rows: list[tuple]) -> int:
    sql = f"INSERT INTO `{table}` ({', '.join('`'+c+'`' for c in cols)}) VALUES ({', '.join(['%s']*len(cols))})"
    n = 0
    for i in range(0, len(rows), BATCH):
        n += cur.executemany(sql, rows[i:i + BATCH])
    return n


def log_stage(cur, dataset_key: str, table: str, stage: str, detail: str | None, row_count: int,
              exclusion: str | None, method: str, measured_by: str):
    cur.execute("SELECT 1 FROM meta_dataset WHERE dataset_key=%s", (dataset_key,))
    if cur.fetchone() is None:
        print(f"    [경고] meta_dataset 에 '{dataset_key}' 없음 → meta_load_log 기록 생략")
        return
    cur.execute(
        "INSERT INTO meta_load_log (dataset_key, table_name, stage, stage_detail, row_count, exclusion_reason, method, measured_by)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (dataset_key, table, stage, detail, row_count, exclusion, method, measured_by))


# ---------------------------------------------------------------------------
# raw_ 파일 → 행 변환
# ---------------------------------------------------------------------------
def frame_generic(path: Path, spec: dict, dict_cols: list[tuple[int, str, str]]) -> tuple[list[str], list[tuple]]:
    df = read_csv_str(path, spec["encoding"])
    header = [norm_header(c) for c in df.columns]
    expected = [o for _, _, o in dict_cols]
    if header != expected:
        raise ValueError(f"헤더 불일치 {path.name}\n  파일  : {header}\n  사전  : {expected}")
    db_cols = [c for _, c, _ in dict_cols]
    null_cols = spec.get("null_cols", set())
    int_cols = spec.get("int_cols", set())
    rows = []
    for i, rec in enumerate(df.itertuples(index=False, name=None), start=1):
        vals = []
        for c, v in zip(db_cols, rec):
            if c in null_cols:
                vals.append(None)
            elif c in int_cols:
                vals.append(int(v) if v != "" else None)
            else:
                vals.append(nz(v))
        vals += [path.name, i]
        rows.append(tuple(vals))
    return db_cols + ["source_file", "source_row_no"], rows


# KRIT 공고 차수별로 다른 표 헤더 → column_dict.csv 의 공통 5열 원본명(norm_header 후 형태, 줄바꿈은 "\\n").
# 뜻이 같은 열만 잇는다. 24-1차 `총과제비(억원)` 는 정부지원금이 아니라 총 사업비라 잇지 않는다(extra_json 으로).
KRIT_HEADER_ALIAS = {
    "구분": "순",                                        # 24-1차 예비: 순번 대신 핵심/수출 구분 글자
    "과제명(예정)": "국산화 개발대상 과제명",              # 24-1차 예비 · 26-2차 예비RFP
    "최대 정부\\n지원금(백만원)": "정부지원\\n연구개발비",  # 26-2차 예비RFP (단위 백만원 — 원본열명을 extra_json 에 남긴다)
    "최대\\n정부지원금": "정부지원\\n연구개발비",         # 23-4차 (예상개발비 열은 extra_json)
    "개발기간\\n(개월)": "개발\\n기간",                  # 24-1차 · 26-2차 예비RFP
}
# 파일명 토큰 → raw_krit_task.notice_type (schema.sql 주석: 예비 / 본공고 / 재공고 / 수정). 앞에서부터 첫 일치.
KRIT_NOTICE_TYPES = (("예비RFP", "예비"), ("예비공고", "예비"), ("수정공고", "수정"), ("재공고", "재공고"), ("공고문", "본공고"))


def frame_krit(path: Path, spec: dict, dict_cols: list[tuple[int, str, str]]) -> tuple[list[str], list[tuple]]:
    """parse_krit.py 출력(<차수>_<문서명>_t<N>.csv 또는 _p<쪽>_t<N>.csv).
    공통 5열은 사전 순서대로(별칭 KRIT_HEADER_ALIAS 로 흡수, 없으면 NULL), 나머지 열은 extra_json.
    별칭으로 이은 열은 extra_json["원본열명"] 에 원래 헤더를 남겨 단위(억/백만원)를 잃지 않는다."""
    df = read_csv_str(path, spec["encoding"])
    header = [norm_header(c) for c in df.columns]
    canon = {h: KRIT_HEADER_ALIAS.get(h, h) for h in header}          # 원본 헤더 → 공통명(또는 그대로)
    common = {o: c for _, c, o in dict_cols}                            # 공통 원본명 → 영문 열
    if "국산화 개발대상 과제명" not in canon.values():
        raise ValueError(f"KRIT 과제명 열 없음 {path.name}: {header}")
    dup = [o for o in common if sum(1 for h in header if canon[h] == o) > 1]
    if dup:
        raise ValueError(f"KRIT 공통 열 중복 {path.name}: {dup}")
    by_common = {canon[h]: h for h in header if canon[h] in common}   # 공통명 → 실제 헤더
    renamed = {common[o]: h for o, h in by_common.items() if h != o}   # 별칭으로 이은 것만
    extra_names = [h for h in header if canon[h] not in common]
    stem = path.stem                      # 26-1차_연구개발기관모집_공고문_t7 / 26-2차_예비RFP_p3_t2
    round_label = stem.split("_")[0]
    table_index = int(stem.rsplit("_t", 1)[1]) if "_t" in stem else None
    notice_type = next((v for tok, v in KRIT_NOTICE_TYPES if tok in stem), None)
    cols = ["round_label", "notice_type", "task_seq", "task_name", "gov_fund_text", "dev_period_text", "note",
            "extra_json", "table_index", "source_file", "source_url", "source_row_no"]
    rows = []
    for i, rec in enumerate(df.itertuples(index=False, name=None), start=1):
        d = dict(zip(header, rec))
        get = lambda o: nz(d[by_common[o]]) if o in by_common else None
        extra = {k: d[k] for k in extra_names if d[k] != ""}
        if renamed:
            extra["원본열명"] = renamed
        rows.append((round_label, notice_type,
                     get("순"), get("국산화 개발대상 과제명"), get("정부지원\\n연구개발비"),
                     get("개발\\n기간"), get("비고"),
                     json.dumps(extra, ensure_ascii=False) if extra else None,
                     table_index, path.name, None, i))
    return cols, rows


def frame_kosis_wide1(path: Path, spec: dict, dict_cols) -> tuple[list[str], list[tuple]]:
    """KOSIS 409: '분야별', 2016..2024 광폭 → (sector_name, year, value_text) 세로형."""
    df = read_csv_str(path, spec["encoding"])
    header = [norm_header(c) for c in df.columns]
    if header[0] != "분야별" or not all(h.isdigit() and len(h) == 4 for h in header[1:]):
        raise ValueError(f"KOSIS 409 헤더 예상 밖: {header}")
    cols = ["sector_name", "year", "value_text", "source_file", "source_row_no", "source_col_no"]
    rows = []
    for r, rec in enumerate(df.itertuples(index=False, name=None), start=1):
        sector = rec[0]
        for c in range(1, len(header)):
            rows.append((sector, header[c], nz(rec[c]), path.name, r, c + 1))
    return cols, rows


_KOSIS_YM = re.compile(r"\d{4}\.\d{2}")


def frame_kosis_wide2(path: Path, spec: dict, dict_cols) -> tuple[list[str], list[tuple]]:
    """KOSIS 101: 헤더 2행(1행 'M201601 2016.01', 2행 'T10 …') 광폭 → 세로형.

    잠정치 열의 1행 헤더는 'M202606 M202606 2026.06 p)' 처럼 뒤에 p) 가 붙으므로, 마지막 토큰이 아니라
    YYYY.MM 토큰을 정규식으로 찾는다. 잠정 표기 p) 는 raw 에 담을 열이 없어 버린다(잠정 여부는 clean_kosis_production_index.is_provisional).
    이미 적재된 raw 는 원본 동결 원칙에 따라 재적재하지 않고, clean 이 source_col_no 로 월을 복원한다(notebooks/06_clean_kosis.ipynb §2).
    """
    with open(path, encoding=spec["encoding"], newline="") as f:
        rd = csv.reader(f)
        h1 = [norm_header(x) for x in next(rd)]
        h2 = [norm_header(x) for x in next(rd)]
        data = [row for row in rd if any(x.strip() for x in row)]
    if h1[:2] != ["A 시도별", "B 산업별"] or h2[:2] != ["A 시도별", "B 산업별"]:
        raise ValueError(f"KOSIS 101 헤더 예상 밖: {h1[:3]} / {h2[:3]}")
    cols = ["region_name", "industry_name", "stat_ym", "item_name", "value_text", "source_file", "source_row_no", "source_col_no"]
    rows = []
    for r, rec in enumerate(data, start=1):
        region, industry = rec[0], rec[1]
        for c in range(2, len(h1)):
            m = _KOSIS_YM.search(h1[c])           # 'M201601 2016.01' / 'M202606 M202606 2026.06 p)' → '2016.01' / '2026.06'
            if m is None:
                raise ValueError(f"KOSIS 101 1행 헤더 {c + 1}열에서 YYYY.MM 을 못 찾음: {h1[c]!r}")
            stat_ym = m.group(0)
            rows.append((region, industry, stat_ym, h2[c], nz(rec[c]) if c < len(rec) else None, path.name, r, c + 1))
    return cols, rows


def frame_hs_unit(path: Path, spec: dict, dict_cols) -> tuple[list[str], list[tuple]]:
    """관세청 HS부호 단위별 품목명(15130660): 시트 HS2단위·HS4단위·HS6단위(5단위포함)·HS8단위(7, 9단위포함)·HS10단위,
    각 시트 열 = <HSn단위>, 한글품목명, 영문품목명. 5시트를 세로로 합치고 hs_unit 에 시트 단위(02/04/06/08/10)를 넣는다."""
    book = pd.read_excel(path, dtype=str, sheet_name=None, engine="openpyxl")
    cols = ["hs_code", "hs_unit", "name_ko", "name_en", "source_file", "source_row_no"]
    rows = []
    for sheet, df in book.items():
        df = df.fillna("")
        header = [norm_header(c) for c in df.columns]
        if len(header) != 3 or not header[0].startswith("HS") or header[1:] != ["한글품목명", "영문품목명"]:
            raise ValueError(f"HS 단위별 품목명 시트 '{sheet}' 헤더 예상 밖: {header}")
        unit = header[0][2:].split("단위")[0]           # 'HS6단위' → '6'
        if not unit.isdigit():
            raise ValueError(f"시트 '{sheet}' 첫 열에서 단위를 못 읽음: {header[0]}")
        unit = unit.zfill(2)
        for i, rec in enumerate(df.itertuples(index=False, name=None), start=1):
            rows.append((nz(rec[0]), unit, nz(rec[1]), nz(rec[2]), path.name, i))
    return cols, rows


FRAMERS = {None: frame_generic, "krit": frame_krit, "kosis_wide1": frame_kosis_wide1, "kosis_wide2": frame_kosis_wide2,
           "hs_unit": frame_hs_unit}


def resolve_files(spec: dict) -> list[Path]:
    pat = str(ROOT / spec["files"])
    return sorted(Path(p) for p in glob.glob(pat))


# ---------------------------------------------------------------------------
# 원본 파일 → DataFrame (정제 노트북·--fact 의 입력. 유일한 원본 읽기 경로)
# ---------------------------------------------------------------------------
_DICT_CACHE: dict[str, list[tuple[int, str, str]]] | None = None


def read_raw(table: str, *, check_expected: bool = True) -> pd.DataFrame:
    """원본 파일 데이터셋 `table`(RAW_TABLES 키) 을 파서(FRAMERS)로 읽어 DataFrame 으로 돌려준다.

    열 = row_id + 파서 열(사전 순 영문 열 + source_file·source_row_no[·source_col_no]). 값은 전부 문자열 또는 None(빈 셀).
    row_id 는 파일명 정렬 순 × 파일 내 행 순으로 1부터 매긴 **파서 순번** — clean_*.raw_row_id · clean_excluded_row.raw_row_id 의 정의.
    check_expected=True 면 총 행 수가 RAW_TABLES.expected 와 다를 때 ValueError(원본 파일이 바뀌었거나 빠졌다는 뜻)."""
    global _DICT_CACHE
    if table not in RAW_TABLES:
        raise KeyError(f"알 수 없는 원본 데이터셋: {table} (RAW_TABLES 키 중 하나여야 함)")
    if _DICT_CACHE is None:
        _DICT_CACHE = read_column_dict()
    spec = RAW_TABLES[table]
    files = resolve_files(spec)
    if not files:
        raise FileNotFoundError(f"{table}: 원본 파일 없음 — {spec['files']}")
    cols: list[str] | None = None
    parts: list[pd.DataFrame] = []
    for p in files:
        c, rows = FRAMERS[spec.get("special")](p, spec, _DICT_CACHE.get(table, []))
        if cols is None:
            cols = c
        elif c != cols:
            raise ValueError(f"{table}: 파일마다 열이 다름 {p.name}: {c} vs {cols}")
        parts.append(pd.DataFrame(rows, columns=cols))
    df = pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
    df = df.astype(object).where(pd.notna(df), None)          # NaN → None (문자열 열이라 NaN 은 빈 셀뿐)
    df.insert(0, "row_id", range(1, len(df) + 1))
    exp = spec["expected"]
    if check_expected and exp is not None and len(df) != exp:
        raise ValueError(f"{table}: 행 수 {len(df):,} ≠ 기대 {exp:,} (파일 {len(files)}개: {[p.name for p in files][:5]}…)")
    return df


def log_raw_stage(cur, table: str, df: pd.DataFrame, measured_by: str, note: str = "") -> None:
    """read_raw 결과를 meta_load_log `원본 전체` 단계로 파일별 기록(옛 do_raw 가 하던 일을 노트북이 한다)."""
    spec = RAW_TABLES[table]
    for fname, n in df.groupby("source_file", sort=True).size().items():
        log_stage(cur, spec["dataset_key"], table, "원본 전체", fname, int(n), None,
                  f"{SCRIPT_TAG} read_raw({table!r}) — 파일 {fname} 파서 행 수{(' · ' + note) if note else ''}", measured_by)


# ---------------------------------------------------------------------------
# 단계별 실행
# ---------------------------------------------------------------------------
def do_dry_run(tables: list[str]):
    print(f"{'데이터셋':36} {'파일':3} {'행':>8} {'기대':>8}  판정")
    ok = True
    for t in tables:
        spec = RAW_TABLES[t]
        files = resolve_files(spec)
        if not files:
            print(f"{t:36} {0:3} {'-':>8} {str(spec['expected'] or '-'):>8}  SKIP(파일 없음: {spec['files']})")
            ok = False
            continue
        try:
            df = read_raw(t, check_expected=False)
        except Exception as e:  # noqa: BLE001
            print(f"{t:36} {len(files):3} {'-':>8} {str(spec['expected'] or '-'):>8}  오류: {e}")
            ok = False
            continue
        exp = spec["expected"]
        total = len(df)
        verdict = "일치" if exp is None or exp == total else f"불일치(차이 {total - exp:+})"
        print(f"{t:36} {len(files):3} {total:8,} {str(exp or '-'):>8}  {verdict}")
        if exp is not None and exp != total:
            ok = False
    return ok


def do_ref(conn, seed_overwrite: bool = False):
    cur = conn.cursor()
    user = current_user(cur)
    # ref_hs_whitelist (hs_code → hs6, b2_scope 는 NULL 유지)
    for table, path, kw in [
        ("ref_hs_whitelist", ROOT / "data/reference/hs_whitelist.csv", {}),
        ("ref_country", ROOT / "data/reference/country_ref.csv", {}),
        ("meta_column_dict", COLUMN_DICT, {}),
        ("meta_dataset", META_DATASET_CSV, {}),
    ]:
        if table_count(cur, table) > 0:
            print(f"  {table}: 비어 있지 않아 건너뜀({table_count(cur, table)}행)")
            continue
        df = read_csv_str(path, "utf-8-sig")
        cols = list(df.columns)
        if table == "ref_hs_whitelist":
            cols[cols.index("hs_code")] = "hs6"
        if table == "ref_country":
            cols[cols.index("statCd")] = "stat_cd"
        rows = [tuple(nz(v) for v in rec) for rec in df.itertuples(index=False, name=None)]
        if table == "meta_dataset":
            rows = fill_meta_dataset(df)
            cols = list(df.columns)
        n = insert_rows(cur, table, cols, rows)
        conn.commit()
        exp = REF_EXPECTED.get(table)
        print(f"  {table}: {n:,}행 적재" + (f" (기대 {exp}: {'일치' if exp == n else '불일치'})" if exp else ""))
    # 수작업 시드 (ref_sido_map · ref_fsg)
    # 시드는 DB 값을 덮어쓰므로(ref_fsg ON DUPLICATE KEY UPDATE) 먼저 대조하고, 다르면 멈춘다 — DB에서만 고친 값이
    # --ref 로 시드 값으로 되돌아가지 않게 한다(data-cleaning-rules.md §1 #14)
    from check_integrity import seed_drift   # 함수 안에서 import(check_integrity 가 이 모듈을 import 한다)
    drift = seed_drift(cur) if SEED_SQL.exists() else []
    if drift and not seed_overwrite:
        print(f"  seed_ref.sql: 건너뜀 — 시드와 DB가 {len(drift)}곳 다르다(실행하면 DB 값이 시드 값으로 바뀌거나 지운 행이 되살아난다)")
        for line in drift[:20]:
            print(f"    {line}")
        print("    → DB 값이 맞으면 db/seed_ref.sql 을 고쳐 커밋하고, 시드가 맞으면 --seed-overwrite 를 붙여 다시 실행")
    elif SEED_SQL.exists():
        # 주석 행을 먼저 걷어낸 뒤 ";\n" 로 문장을 나눈다(문자열 안의 ';' 는 줄 끝에 오지 않는다)
        body_all = "\n".join(l for l in SEED_SQL.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--"))
        stmts = [s.strip() for s in body_all.split(";\n") if s.strip()]
        for s in stmts:
            cur.execute(s)
        conn.commit()
        print(f"  seed_ref.sql: {len(stmts)}문 실행 → ref_sido_map {table_count(cur,'ref_sido_map')} · ref_fsg {table_count(cur,'ref_fsg')}")
    # 관세청 HS 기준표 2종 — 원본 파일(read_raw)에서 만든다
    for table, src, builder, exp in [("ref_hs_code_master", "raw_hs_code_master", build_hs_code_master, 11_327),
                                     ("ref_hs6_name", "raw_hs_unit_name", build_hs6_name, 2_254)]:
        if table_count(cur, table) > 0:
            print(f"  {table}: 비어 있지 않아 건너뜀({table_count(cur, table)}행)")
            continue
        try:
            df = builder(read_raw(src))
        except FileNotFoundError as e:
            print(f"  {table}: SKIP({e})")
            continue
        n = insert_rows(cur, table, list(df.columns), _rows(df))
        conn.commit()
        print(f"  {table}: {n:,}행 적재 (기대 {exp:,}: {'일치' if n == exp else '불일치'})")
    for table, fname, exp in SEMI_REF:
        if table_count(cur, table) > 0:
            print(f"  {table}: 비어 있지 않아 건너뜀({table_count(cur, table)}행)")
            continue
        df = read_csv_str(ROOT / "data/reference" / fname, "utf-8").rename(columns={"date": "event_date"})
        if table == "ref_semi_policy_timeline":
            df.insert(0, "row_no", [str(i) for i in range(1, len(df) + 1)])
        n = insert_rows(cur, table, list(df.columns), [tuple(nz(v) for v in rec) for rec in df.itertuples(index=False, name=None)])
        conn.commit()
        print(f"  {table}: {n:,}행 적재 (기대 {exp}: {'일치' if n == exp else '불일치'})")
    print(f"  (measured_by={user})")


def fill_meta_dataset(df: pd.DataFrame) -> list[tuple]:
    """db/meta_dataset.csv 의 file_bytes·sha256 이 비어 있으면 raw_path 가 단일 파일일 때 실제 파일에서 계산."""
    rows = []
    for rec in df.to_dict("records"):
        p = ROOT / rec["raw_path"]
        if rec.get("file_bytes", "") == "" and p.is_file():
            rec["file_bytes"] = str(p.stat().st_size)
        if rec.get("sha256", "") == "" and p.is_file():
            rec["sha256"] = sha256_of(p)
        rows.append(tuple(nz(v) for v in rec.values()))
    return rows


def current_user(cur) -> str:
    cur.execute("SELECT CURRENT_USER()")
    return cur.fetchone()[0]


def build_hs_code_master(df: pd.DataFrame) -> pd.DataFrame:
    """read_raw('raw_hs_code_master') → ref_hs_code_master (2026 현행 HSK10 11,327행: 10자리만, 이름·적용기간 5열)."""
    d = df[df["hs_code"].fillna("").str.fullmatch(r"[0-9]{10}")]
    return pd.DataFrame({"hs10": d["hs_code"], "name_ko": d["name_ko"], "name_en": d["name_en"],
                         "apply_start": pd.to_datetime(d["apply_start"].str[:10], errors="coerce").dt.date,
                         "apply_end": pd.to_datetime(d["apply_end"].str[:10], errors="coerce").dt.date}).reset_index(drop=True)


def build_hs6_name(df: pd.DataFrame) -> pd.DataFrame:
    """read_raw('raw_hs_unit_name') → ref_hs6_name (06시트 6자리 2,254행. 10시트는 ref_hs_code_master 와 코드·품명이 같아 두지 않는다)."""
    d = df[(df["hs_unit"] == "06") & df["hs_code"].fillna("").str.fullmatch(r"[0-9]{6}")]
    return d[["hs_code", "name_ko", "name_en"]].rename(columns={"hs_code": "hs6"}).reset_index(drop=True)


def build_customs_region(df: pd.DataFrame) -> pd.DataFrame:
    """read_raw('raw_customs_region') → clean_customs_region (HS6 × 시군구 × 월, 금액 천 달러, 쉼표 제거·정수)."""
    n = lambda s: pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce").astype("Int64")
    out = pd.DataFrame({
        "hs6": df["req_hs"], "sido_code": df["req_sido"], "sgg_name": df["sgg_name"],
        "yyyymm": df["stat_ym"].str[:4] + df["stat_ym"].str[-2:],
        "year": df["stat_ym"].str[:4].astype(int), "month": df["stat_ym"].str[-2:].astype(int),
        "exp_cnt": n(df["exp_cnt"]), "exp_kusd": n(df["exp_usd_amt"]), "imp_cnt": n(df["imp_cnt"]),
        "imp_kusd": n(df["imp_usd_amt"]), "trade_balance_kusd": n(df["trade_balance_amt"])})
    out["is_partial_year"] = (out["year"] == 2026).astype(int)
    return out


def build_customs_dim_fact(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """관세청 원본(read_raw('raw_customs_trade'))에서 dim_hs10 · fact_customs_monthly 행을 만든다(schema.sql §4 규칙).

    총계행(is_total='1') 제외, hs6 = LEFT(hs10,6), yyyymm = 'YYYY.MM' → 'YYYYMM', 금액·중량은 정수, 2026 = 부분연도.
    dim.name_ko 는 HS10 별 가장 최근 stat_ym 의 품명(동률이면 row_id 큰 쪽). MAX(item_name_ko)는 문자열 최댓값이라 쓰지 않는다."""
    d = df[df["is_total"] == "0"].copy()
    d["hs6"] = d["hs_cd"].str[:6]
    d["year"] = d["stat_ym"].str[:4].astype(int)
    d["month"] = d["stat_ym"].str[-2:].astype(int)
    d["yyyymm"] = d["stat_ym"].str[:4] + d["stat_ym"].str[-2:]
    for c in ("imp_dlr", "exp_dlr", "imp_wgt", "exp_wgt", "bal_payments"):
        d[c] = pd.to_numeric(d[c], errors="raise").astype("Int64")
    d["is_partial_year"] = (d["year"] == 2026).astype(int)
    fact = d[["hs_cd", "stat_cd", "yyyymm", "hs6", "year", "month", "imp_dlr", "exp_dlr", "imp_wgt", "exp_wgt",
              "bal_payments", "is_partial_year"]].rename(columns={"hs_cd": "hs10"})
    latest = d.sort_values(["hs_cd", "stat_ym", "row_id"]).drop_duplicates("hs_cd", keep="last")
    dim = latest[["hs_cd", "hs6", "item_name_ko"]].rename(columns={"hs_cd": "hs10", "item_name_ko": "name_ko"})
    return dim.reset_index(drop=True), fact.reset_index(drop=True)


def _rows(df: pd.DataFrame) -> list[tuple]:
    return [tuple(None if (v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA) else
                  (int(v) if hasattr(v, "__index__") and not isinstance(v, bool) else v) for v in rec)
            for rec in df.itertuples(index=False, name=None)]


def do_region(conn) -> bool:
    """clean_customs_region ← read_raw('raw_customs_region') (시군구별 15134343, 273,586행 기대). 파일 없으면 SKIP."""
    cur = conn.cursor()
    user = current_user(cur)
    if table_count(cur, "clean_customs_region") > 0:
        print(f"- clean_customs_region 비어 있지 않음({table_count(cur, 'clean_customs_region'):,}행) → 건너뜀")
        return True
    try:
        raw = read_raw("raw_customs_region")
    except FileNotFoundError as e:
        print(f"- clean_customs_region: SKIP({e})")
        return False
    df = build_customs_region(raw)
    n = insert_rows(cur, "clean_customs_region", list(df.columns), _rows(df))
    log_raw_stage(cur, "raw_customs_region", raw, user)
    log_stage(cur, "customs_region", "clean_customs_region", "중복 처리 후", "HS6 × 시군구 × 월(형 변환, 제외 0)", n, None,
              f"{SCRIPT_TAG} --fact (read_raw → build_customs_region, pandas)", user)
    conn.commit()
    print(f"- clean_customs_region {n:,}행 (기대 273,586: {'일치' if n == 273_586 else '불일치'})")
    return n == 273_586


def do_fact(conn) -> bool:
    cur = conn.cursor()
    user = current_user(cur)
    ok_region = do_region(conn)
    if table_count(cur, "fact_customs_monthly") > 0 or table_count(cur, "dim_hs10") > 0:
        print("- dim_hs10/fact_customs_monthly 가 비어 있지 않음 → 건너뜀")
        return ok_region
    t0 = time.time()
    raw = read_raw("raw_customs_trade")
    dim, fact = build_customs_dim_fact(raw)
    cur.execute("SELECT stat_cd FROM ref_country")
    known = {r[0] for r in cur.fetchall()}
    missing = sorted(set(fact["stat_cd"]) - known)
    if missing:
        print(f"- ref_country 에 없는 stat_cd {len(missing)}개: {missing[:20]} → 중단")
        return False
    cur.execute("SELECT hs6 FROM ref_hs_whitelist")
    wl = {r[0] for r in cur.fetchall()}
    miss_hs = sorted(set(fact["hs6"]) - wl)
    if miss_hs:
        print(f"- ref_hs_whitelist 에 없는 hs6 {miss_hs} → 중단")
        return False
    n_dim = insert_rows(cur, "dim_hs10", list(dim.columns), _rows(dim))
    n_fact = insert_rows(cur, "fact_customs_monthly", list(fact.columns), _rows(fact))
    n2025 = int((fact["year"] == 2025).sum())
    n_total = int((raw["is_total"] == "1").sum())
    log_raw_stage(cur, "raw_customs_trade", raw, user, "총계행 포함")
    log_stage(cur, "customs_all", "fact_customs_monthly", "원본 전체", "총계행 제외 월별 상세", n_fact,
              f"연간 총계행(is_total=1) {n_total}행 제외", f"{SCRIPT_TAG} --fact (read_raw → build_customs_dim_fact, pandas)", user)
    log_stage(cur, "customs_all", "fact_customs_monthly", "선택 연도 원본", "2025", n2025,
              "2025년 외 연도 제외", "fact['year'] == 2025 (pandas)", user)
    conn.commit()
    print(f"- dim_hs10 {n_dim:,}행 · fact_customs_monthly {n_fact:,}행 (기대 294,174: {'일치' if n_fact==294_174 else '불일치'})"
          f" · 2025 {n2025:,}행 (기대 26,211: {'일치' if n2025==26_211 else '불일치'}) · {time.time()-t0:.1f}s")
    return n_fact == 294_174


def do_verify(conn):
    """DB 건수 대조(ref·meta·dim/fact·clean) + 원본 파일 파서 건수(read_raw, 파일 쪽)."""
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE'"
                " AND table_name LIKE 'clean%' ORDER BY table_name")
    clean_tables = [r[0] for r in cur.fetchall()]
    print(f"{'테이블':36} {'건수':>10} {'기대':>10}  판정")
    for t, exp in list(REF_EXPECTED.items()) + [("dim_hs10", None), ("fact_customs_monthly", 294_174), ("meta_dataset", None), ("meta_load_log", None),
             ("ref_sido_map", None)] + [(t, e) for t, _, e in SEMI_REF] + [(t, None) for t in clean_tables]:
        n = table_count(cur, t)
        v = "-" if exp is None else ("일치" if n == exp else f"불일치({n-exp:+})")
        print(f"{t:36} {n:10,} {str(exp or '-'):>10}  {v}")
    print("\n[원본 파일] read_raw 파서 건수 (DB 아님)")
    do_dry_run(list(RAW_TABLES))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ref", action="store_true")
    ap.add_argument("--seed-overwrite", action="store_true", help="--ref 에서 seed_ref.sql 과 DB 가 달라도 시드를 실행(시드 값으로 덮어씀)")
    ap.add_argument("--fact", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--tables", nargs="*", default=None, help="--dry-run 대상 원본 데이터셋 키(RAW_TABLES, 생략 시 전부)")
    a = ap.parse_args()
    tables = a.tables or list(RAW_TABLES)
    bad = [t for t in tables if t not in RAW_TABLES]
    if bad:
        sys.exit(f"알 수 없는 원본 데이터셋: {bad}")
    if not any([a.dry_run, a.ref, a.fact, a.verify]):
        ap.print_help()
        return
    rc = 0
    if a.dry_run:
        rc |= 0 if do_dry_run(tables) else 1
    if a.ref or a.fact or a.verify:
        conn = connect()
        try:
            if a.ref:
                print("[ref/meta]")
                do_ref(conn, a.seed_overwrite)
            if a.fact:
                print("[dim/fact]")
                rc |= 0 if do_fact(conn) else 1
            if a.verify:
                print("[verify]")
                do_verify(conn)
        finally:
            conn.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
