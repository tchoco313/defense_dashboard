"""팀 DB(defense_dashboard) 적재 스크립트 — ref_ / meta_ / raw_ / dim_·fact_ 계층.

서버는 local_infile=0 이라 LOAD DATA LOCAL 을 못 쓴다(defense3 권한으로 못 켬). pymysql executemany 로 넣는다.
열 매핑은 db/column_dict.csv 의 (table_name, ordinal, column_name, original_name) 을 기준으로 CSV 헤더를 순서 대조한 뒤 적재한다.
clean_ 계층은 다루지 않는다(정제 규칙은 사용자 노트북 영역).

사용:
  python scripts/load_db.py --dry-run                 # 파일 파싱·헤더 대조·건수만 (DB 접속 없음)
  python scripts/load_db.py --ref                     # ref_hs_whitelist·ref_country·meta_column_dict·meta_dataset + db/seed_ref.sql
  python scripts/load_db.py --raw                     # raw_ 18개 전부 (파일 없는 테이블은 SKIP)
  python scripts/load_db.py --raw --tables raw_dapa_contract raw_krit_task
  python scripts/load_db.py --fact                    # dim_hs10·fact_customs_monthly 채우기 (schema.sql §4)
  python scripts/load_db.py --verify                  # 건수 대조표만 출력

재적재는 하지 않는다: 대상 테이블이 비어 있지 않으면 중단한다. 먼저 db/reset_data.sql 또는 DELETE … WHERE source_file=… 로 비운다.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import pymysql

if hasattr(sys.stdout, "reconfigure"):  # Jupyter 커널(OutStream)에는 없음
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
COLUMN_DICT = ROOT / "db" / "column_dict.csv"
META_DATASET_CSV = ROOT / "db" / "meta_dataset.csv"
SEED_SQL = ROOT / "db" / "seed_ref.sql"
BATCH = 2000
SCRIPT_TAG = "scripts/load_db.py"

# ---------------------------------------------------------------------------
# 테이블별 원본 파일·인코딩·기대 건수 (docs/db/schema-design.md §3-2)
#   dataset_key 는 meta_dataset.dataset_key (meta_load_log FK)
#   null_cols   는 개인정보 열 → 적재 시 NULL
#   int_cols    는 raw 중 유일한 정수 열
# ---------------------------------------------------------------------------
RAW_TABLES: dict[str, dict] = {
    "raw_customs_trade": dict(
        files="data/raw/customs/customs_all_*.csv", encoding="utf-8", expected=294_420,   # 2026-09-16: 21개 268,909 + 신규 3개(852910·901410·901490) 25,511
        dataset_key="customs_all", tier="핵심"),
    "raw_customs_progress": dict(
        files="data/raw/customs/progress_all.csv", encoding="utf-8", expected=264,   # 231 + 33
        dataset_key="customs_progress", int_cols={"row_count"}, tier="메타"),
    "raw_dapa_contract": dict(
        files="data/raw/dapa/dapa_domestic_contract_20251231.csv", encoding="cp949", expected=43_112,
        dataset_key="dapa_contract", tier="핵심"),
    "raw_dapa_localized_item": dict(
        files="data/raw/dapa/dapa_localized_items_20260509.csv", encoding="cp949", expected=33_965,
        dataset_key="dapa_localized_item", tier="핵심"),
    "raw_krit_task": dict(
        files="data/raw/krit/*_t*.csv", encoding="utf-8-sig", expected=None,
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
    # 무역안보관리원 HSK 연계표(data.go.kr 15034135). 2026-09-16 내려받아 확인: utf-8-sig, 2,161행(포털 표시와 일치), 헤더 품목번호·품명(국문)·품명(영문)·통제번호.
    # 통제번호는 쉼표 목록(최대 1,218자) → raw_hsk_control.control_no TEXT (db/alter_2026-09-16_hs_rule.sql §2-0).
    "raw_hsk_control": dict(
        files="data/raw/kosti/hsk_control_15034135.csv", encoding="utf-8-sig", expected=2_161,
        dataset_key="kosti_hsk_control", tier="보조"),
    # 관세청 HS부호 마스터(data.go.kr 15049722, XLSX 1시트 20열) · HS부호 단위별 품목명(15130660, XLSX 5시트) — HS6 선정 규칙(schema.sql §6 v_hs6_candidate_rule)의 원본.
    # 2026-09-16 내려받아 헤더 확인(12,469행 = 포털 표시와 일치 / 5시트 합 17,072행 일치). .xlsx 는 pandas read_excel(openpyxl)로 읽는다.
    # 마스터는 frame_generic(첫 시트, 열 순서 column_dict 대조), 단위별 품목명은 special='hs_unit'(시트마다 첫 열 이름이 달라 5시트를 세로로 합침).
    "raw_hs_code_master": dict(
        files="data/raw/customs/hs_code_master_15049722.xlsx", encoding=None, expected=12_469,
        dataset_key="customs_hs_code_master", tier="참조"),
    "raw_hs_unit_name": dict(
        files="data/raw/customs/hs_unit_name_15130660.xlsx", encoding=None, expected=17_072,
        dataset_key="customs_hs_unit_name", special="hs_unit", tier="참조"),
    # 2026-09-16 팀 드라이브 채택 3종(db/alter_2026-09-16_api_budget.sql). 원본은 조장이 수집해 드라이브 1조/2_데이터수집_저장에 올린 것을 내려받음.
    # 국외 조달계획 OpenAPI 품목 단위(15158418, 요구연도별 호출) — 파일판 raw_dapa_overseas_plan(사업 단위·원)과 다른 표. 헤더 24열 utf-8-sig, 13,615행.
    "raw_dapa_overseas_plan_api": dict(
        files="data/raw/dapa/dapa_overseas_plan_api_20260916.csv", encoding="utf-8-sig", expected=13_615,
        dataset_key="dapa_overseas_plan_api", tier="핵심"),
    # 군급분류집(15119907) cp949 10열 756행(FSG 그룹행 80 + FSC 676) → ref_fsc 시드는 alter §3 INSERT…SELECT.
    "raw_dapa_fsc_catalog": dict(
        files="data/raw/dapa/dapa_fsc_catalog_20251231.csv", encoding="cp949", expected=756,
        dataset_key="dapa_fsc_catalog", tier="참조"),
    # 열린재정 세부사업 예산편성현황(총액) 방위사업청·일반회계, 회계연도별 12파일(2016~2027) utf-8-sig 14열, 합 2,860행(2020~2027 1,981 + 2016~2019 879). 마지막 줄 개행 없음.
    "raw_openfiscal_program_budget": dict(
        files="data/raw/budget/openfiscal_dapa_program_budget_*.csv", encoding="utf-8-sig", expected=2_860,
        dataset_key="openfiscal_program_budget", tier="보조"),
    # 2026-09-17 국방표준종합서비스(KDSIS) NSN 목록 팀원 정리본(db/alter_2026-09-17_kdsis_nsn.sql). new_data/ 에 그대로 두고 읽는다(원본 두 파일 .txt+2016.csv 합본).
    # utf-8-sig 22열 228,027행. CSV의 source_file/source_row_no 열은 origin_file/origin_row_no 로 들어가고, DB의 source_file/source_row_no 는 frame_generic 이 붙인다.
    "raw_kdsis_nsn": dict(
        files="new_data/raw_kdsis_nsn.csv", encoding="utf-8-sig", expected=228_027,
        dataset_key="kdsis_nsn", int_cols={"origin_row_no"}, tier="보조"),
}

REF_EXPECTED = {"ref_hs_whitelist": 24, "ref_country": 238, "meta_column_dict": 388}  # 388 = column_dict.csv (2026-09-17 KDSIS 51행 추가 후. 이전 337)


# ---------------------------------------------------------------------------
# 공통
# ---------------------------------------------------------------------------
def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def connect():
    env = load_env()
    return pymysql.connect(
        host=env["MARIADB_HOST"], port=int(env.get("MARIADB_PORT", "3306")),
        user=env["MARIADB_USER"], password=env["MARIADB_PASSWORD"],
        database=env.get("MARIADB_DATABASE", "defense_dashboard"),
        charset="utf8mb4", autocommit=False, local_infile=False,
    )


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


def frame_krit(path: Path, spec: dict, dict_cols: list[tuple[int, str, str]]) -> tuple[list[str], list[tuple]]:
    """parse_krit.py 출력(<차수>_<문서명>_t<N>.csv). 공통 5열은 사전 순서대로, 나머지 열은 extra_json."""
    df = read_csv_str(path, spec["encoding"])
    header = [norm_header(c) for c in df.columns]
    expected = [o for _, _, o in dict_cols]
    common = {o: c for _, c, o in dict_cols}
    if [h for h in header if h in common] != expected:
        raise ValueError(f"KRIT 공통 5열 불일치 {path.name}: {header}")
    stem = path.stem                      # 26-1차_연구개발기관모집_공고문_t7
    round_label = stem.split("_")[0]
    table_index = int(stem.rsplit("_t", 1)[1]) if "_t" in stem else None
    extra_names = [h for h in header if h not in common]
    cols = ["round_label", "notice_type", "task_seq", "task_name", "gov_fund_text", "dev_period_text", "note",
            "extra_json", "table_index", "source_file", "source_url", "source_row_no"]
    rows = []
    for i, rec in enumerate(df.itertuples(index=False, name=None), start=1):
        d = dict(zip(header, rec))
        extra = {k: d[k] for k in extra_names if d[k] != ""}
        rows.append((round_label, None,
                     nz(d["순"]), nz(d["국산화 개발대상 과제명"]), nz(d["정부지원\\n연구개발비"]),
                     nz(d["개발\\n기간"]), nz(d["비고"]),
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


def frame_kosis_wide2(path: Path, spec: dict, dict_cols) -> tuple[list[str], list[tuple]]:
    """KOSIS 101: 헤더 2행(1행 'M201601 2016.01', 2행 'T10 …') 광폭 → 세로형."""
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
            stat_ym = h1[c].split()[-1]          # 'M201601 2016.01' → '2016.01'
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
# 단계별 실행
# ---------------------------------------------------------------------------
def do_dry_run(tables: list[str]):
    cd = read_column_dict()
    print(f"{'테이블':36} {'파일':3} {'행':>8} {'기대':>8}  판정")
    ok = True
    for t in tables:
        spec = RAW_TABLES[t]
        files = resolve_files(spec)
        if not files:
            print(f"{t:36} {0:3} {'-':>8} {str(spec['expected'] or '-'):>8}  SKIP(파일 없음: {spec['files']})")
            ok = False
            continue
        total = 0
        try:
            for p in files:
                _, rows = FRAMERS[spec.get("special")](p, spec, cd.get(t, []))
                total += len(rows)
        except Exception as e:  # noqa: BLE001
            print(f"{t:36} {len(files):3} {'-':>8} {str(spec['expected'] or '-'):>8}  오류: {e}")
            ok = False
            continue
        exp = spec["expected"]
        verdict = "일치" if exp is None or exp == total else f"불일치(차이 {total - exp:+})"
        print(f"{t:36} {len(files):3} {total:8,} {str(exp or '-'):>8}  {verdict}")
    return ok


def do_ref(conn):
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
    # 수작업 시드 (ref_sido_map · ref_category_map 후보)
    if SEED_SQL.exists():
        # 주석 행을 먼저 걷어낸 뒤 ";\n" 로 문장을 나눈다(문자열 안의 ';' 는 줄 끝에 오지 않는다)
        body_all = "\n".join(l for l in SEED_SQL.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--"))
        stmts = [s.strip() for s in body_all.split(";\n") if s.strip()]
        for s in stmts:
            cur.execute(s)
        conn.commit()
        print(f"  seed_ref.sql: {len(stmts)}문 실행 → ref_sido_map {table_count(cur,'ref_sido_map')} · ref_category_map {table_count(cur,'ref_category_map')}")
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


def do_raw(conn, tables: list[str]) -> bool:
    cd = read_column_dict()
    cur = conn.cursor()
    user = current_user(cur)
    all_ok = True
    for t in tables:
        spec = RAW_TABLES[t]
        files = resolve_files(spec)
        if not files:
            print(f"- {t}: SKIP(파일 없음: {spec['files']})")
            all_ok = False
            continue
        if (n0 := table_count(cur, t)) > 0:
            print(f"- {t}: 비어 있지 않음({n0:,}행) → 건너뜀. 재적재는 reset_data.sql 또는 DELETE … WHERE source_file 후")
            all_ok = False
            continue
        t0 = time.time()
        total = 0
        try:
            for p in files:
                cols, rows = FRAMERS[spec.get("special")](p, spec, cd.get(t, []))
                n = insert_rows(cur, t, cols, rows)
                log_stage(cur, spec["dataset_key"], t, "원본 전체", p.name, n, None,
                          f"{SCRIPT_TAG} --raw ({p.name}, pandas {'read_excel' if p.suffix.lower() == '.xlsx' else 'read_csv'} dtype=str)", user)
                conn.commit()
                total += n
                print(f"    {p.name}: {n:,}행")
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            print(f"- {t}: 오류 → 롤백. {e}")
            all_ok = False
            continue
        # meta_dataset 의 크기·해시가 비어 있으면(--ref 시점에 파일이 없던 A7 등) 단일 파일일 때 채운다
        if len(files) == 1:
            cur.execute("UPDATE meta_dataset SET file_bytes=%s, sha256=%s WHERE dataset_key=%s AND sha256 IS NULL",
                        (files[0].stat().st_size, sha256_of(files[0]), spec["dataset_key"]))
            conn.commit()
        cnt = table_count(cur, t)
        exp = spec["expected"]
        verdict = "일치" if exp is None or exp == cnt else f"불일치(기대 {exp:,})"
        print(f"- {t}: {len(files)}파일 {cnt:,}행 [{verdict}] {time.time()-t0:.1f}s")
        if exp is not None and exp != cnt:
            all_ok = False
    return all_ok


DIM_SQL = """
INSERT INTO dim_hs10 (hs10, hs6, name_ko)
  SELECT hs_cd, LEFT(hs_cd,6), item_name_ko
  FROM (SELECT hs_cd, item_name_ko,
               ROW_NUMBER() OVER (PARTITION BY hs_cd ORDER BY stat_ym DESC, row_id DESC) AS rn
        FROM raw_customs_trade WHERE is_total='0') t
  WHERE rn = 1
"""
FACT_SQL = """
INSERT INTO fact_customs_monthly
  (hs10, stat_cd, yyyymm, hs6, year, month, imp_dlr, exp_dlr, imp_wgt, exp_wgt, bal_payments, is_partial_year, raw_row_id)
  SELECT hs_cd, stat_cd, CONCAT(LEFT(stat_ym,4), RIGHT(stat_ym,2)), LEFT(hs_cd,6),
         CAST(LEFT(stat_ym,4) AS SIGNED), CAST(RIGHT(stat_ym,2) AS SIGNED),
         CAST(imp_dlr AS SIGNED), CAST(exp_dlr AS SIGNED), CAST(imp_wgt AS SIGNED), CAST(exp_wgt AS SIGNED),
         CAST(bal_payments AS SIGNED), IF(LEFT(stat_ym,4)='2026',1,0), row_id
  FROM raw_customs_trade WHERE is_total='0'
"""


def do_fact(conn) -> bool:
    cur = conn.cursor()
    user = current_user(cur)
    if table_count(cur, "raw_customs_trade") == 0:
        print("- raw_customs_trade 가 비어 있음 → --raw 먼저")
        return False
    if table_count(cur, "fact_customs_monthly") > 0 or table_count(cur, "dim_hs10") > 0:
        print("- dim_hs10/fact_customs_monthly 가 비어 있지 않음 → 건너뜀")
        return False
    cur.execute("SELECT DISTINCT r.stat_cd FROM raw_customs_trade r LEFT JOIN ref_country c ON c.stat_cd=r.stat_cd"
                " WHERE r.is_total='0' AND c.stat_cd IS NULL")
    missing = [r[0] for r in cur.fetchall()]
    if missing:
        print(f"- ref_country 에 없는 stat_cd {len(missing)}개: {missing[:20]} → 중단")
        return False
    cur.execute("SELECT DISTINCT LEFT(hs_cd,6) FROM raw_customs_trade r WHERE is_total='0'"
                " AND NOT EXISTS (SELECT 1 FROM ref_hs_whitelist w WHERE w.hs6=LEFT(r.hs_cd,6))")
    miss_hs = [r[0] for r in cur.fetchall()]
    if miss_hs:
        print(f"- ref_hs_whitelist 에 없는 hs6 {miss_hs} → 중단")
        return False
    t0 = time.time()
    n_dim = cur.execute(DIM_SQL)
    n_fact = cur.execute(FACT_SQL)
    cur.execute("SHOW WARNINGS")
    warns = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM fact_customs_monthly WHERE year=2025")
    n2025 = cur.fetchone()[0]
    log_stage(cur, "customs_all", "fact_customs_monthly", "원본 전체", "총계행 제외 월별 상세", n_fact,
              "연간 총계행(is_total=1) 213행 제외", f"{SCRIPT_TAG} --fact (schema.sql §4 INSERT…SELECT)", user)
    log_stage(cur, "customs_all", "fact_customs_monthly", "선택 연도 원본", "2025", n2025,
              "2025년 외 연도 제외", "SELECT COUNT(*) FROM fact_customs_monthly WHERE year=2025", user)
    conn.commit()
    print(f"- dim_hs10 {n_dim:,}행 · fact_customs_monthly {n_fact:,}행 (기대 294,174: {'일치' if n_fact==294_174 else '불일치'})"
          f" · 2025 {n2025:,}행 (기대 26,211: {'일치' if n2025==26_211 else '불일치'}) · 경고 {len(warns)} · {time.time()-t0:.1f}s")
    for w in warns[:10]:
        print("    ", w)
    return n_fact == 294_174


def do_verify(conn):
    cur = conn.cursor()
    print(f"{'테이블':36} {'건수':>10} {'기대':>10}  판정")
    for t, exp in list(REF_EXPECTED.items()) + [(t, s["expected"]) for t, s in RAW_TABLES.items()] + \
            [("dim_hs10", None), ("fact_customs_monthly", 294_174), ("meta_dataset", None), ("meta_load_log", None),
             ("ref_category_map", None), ("ref_sido_map", None)]:
        n = table_count(cur, t)
        v = "-" if exp is None else ("일치" if n == exp else f"불일치({n-exp:+})")
        print(f"{t:36} {n:10,} {str(exp or '-'):>10}  {v}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ref", action="store_true")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--fact", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--tables", nargs="*", default=None, help="raw_ 테이블 이름(생략 시 전부)")
    a = ap.parse_args()
    tables = a.tables or list(RAW_TABLES)
    bad = [t for t in tables if t not in RAW_TABLES]
    if bad:
        sys.exit(f"알 수 없는 테이블: {bad}")
    if not any([a.dry_run, a.ref, a.raw, a.fact, a.verify]):
        ap.print_help()
        return
    rc = 0
    if a.dry_run:
        rc |= 0 if do_dry_run(tables) else 1
    if a.ref or a.raw or a.fact or a.verify:
        conn = connect()
        try:
            if a.ref:
                print("[ref/meta]")
                do_ref(conn)
            if a.raw:
                print("[raw]")
                rc |= 0 if do_raw(conn, tables) else 1
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
