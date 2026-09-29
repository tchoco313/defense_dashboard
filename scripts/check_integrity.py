"""운영 DB 정합성 점검(읽기 전용) — 2026-09-28 DB 수정협의안(docs/report/data/db-qa-response-2026-09-28.md)의 재발 방지.

세 가지를 PASS/FAIL 로 본다(etl_rw SELECT 만, 비밀값 출력 없음). data-cleaning-rules.md §1 #14~#16 의 점검 도구다.
  1. seed    — 시드·참조 CSV ↔ DB 값(D-01 유형). db/seed_ref.sql(ref_fsg·ref_sido_map)과 data/reference/*.csv·db/column_dict.csv
               로 적재한 표. DB에서만 고친 값은 다음 load_db.py --ref(시드 덮어쓰기)나 재적재 때 사라진다.
  2. balance — 원본 = clean + 제외 검산(D-03 유형). 원본 행 수는 load_db.RAW_TABLES 의 파서 기대 건수, 제외는 clean_excluded_row.
               검산 설정(BALANCE·BALANCE_SKIP)에 없는 clean_ 표가 생기면 FAIL — 새 표를 만들 때 여기에 등록한다.
  3. flag    — 전자 판정(FSG 58·59·60, 09-21 M4) 일치: ref_fsg ↔ ref_fsc ↔ clean 3표(KDSIS·B2·국외조달 API).

사용(저장소 루트):
  python scripts/check_integrity.py                  # 전부. FAIL 이 하나라도 있으면 종료 코드 1
  python scripts/check_integrity.py --only seed flag
돌리는 때: alter 적용 · load_db.py --ref · 정제 노트북 적재 직후, 데이터 제출(10-02) 전.
"""
from __future__ import annotations

import argparse
import datetime as dt
import decimal
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import load_db  # noqa: E402  RAW_TABLES · read_csv_str · SEED_SQL · SEMI_REF · connect 재사용

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REF_DIR = load_db.ROOT / "data" / "reference"
# CSV 로 적재하는 표 — (표, 파일, 인코딩, 열 이름 바꾸기). load_db.do_ref 와 같은 매핑
CSV_REF = [("ref_hs_whitelist", REF_DIR / "hs_whitelist.csv", "utf-8-sig", {"hs_code": "hs6"}),
           ("ref_country", REF_DIR / "country_ref.csv", "utf-8-sig", {"statCd": "stat_cd"}),
           ("meta_column_dict", load_db.COLUMN_DICT, "utf-8-sig", {}),
           *[(t, REF_DIR / f, "utf-8", {"date": "event_date"}) for t, f, _ in load_db.SEMI_REF]]

# 원본 = clean + 제외 검산 방식 — clean 표: (원본 데이터셋 키, 방식)
#   rows      clean 행 1:1                     원본 = COUNT(*) + 제외
#   distinct  원본 1행이 여러 행으로 펼쳐짐     원본 = COUNT(DISTINCT raw_row_id) + 제외
#   dup_count 원본 행 수를 dup_count 로 보존    원본 = SUM(dup_count) + 제외(KEY_CONFLICT 는 대표 행의 dup_count 에 이미 들어 있어 뺀다)
BALANCE = {
    "clean_customs_region": ("raw_customs_region", "rows"),
    "clean_dapa_bid_notice": ("raw_dapa_bid_notice", "rows"),
    "clean_dapa_bid_result": ("raw_dapa_bid_result", "rows"),
    "clean_dapa_contract": ("raw_dapa_contract", "rows"),
    "clean_dapa_contract_exec_by_service": ("raw_dapa_contract_exec_by_service", "rows"),
    "clean_dapa_defense_company": ("raw_dapa_defense_company", "rows"),
    "clean_dapa_domestic_plan": ("raw_dapa_domestic_plan", "rows"),
    "clean_dapa_overseas_bid_result": ("raw_dapa_overseas_bid_result", "rows"),
    "clean_dapa_overseas_contract": ("raw_dapa_overseas_contract", "rows"),
    "clean_dapa_overseas_plan_api": ("raw_dapa_overseas_plan_api", "rows"),
    "clean_kosis_production_index": ("raw_kosis_production_index", "rows"),
    "clean_kosis_utilization": ("raw_kosis_utilization", "rows"),
    "clean_krit_task": ("raw_krit_task", "rows"),
    "clean_openfiscal_program_budget": ("raw_openfiscal_program_budget", "rows"),
    "clean_hsk_control": ("raw_hsk_control", "distinct"),
    "clean_dapa_localized_item": ("raw_dapa_localized_item", "dup_count"),
    "clean_dapa_overseas_plan": ("raw_dapa_overseas_plan", "dup_count"),
}
# 검산하지 않는 clean 표와 이유 — 원본 행과 행 수가 대응하지 않는 축약·파생 표
BALANCE_SKIP = {
    "clean_kdsis_nsn": "NSN 1개 = 1행 축약(원본은 NSN당 여러 속성 행) — 원본 행 수 열 없음",
    "clean_company": "파생(clean_dapa_contract · clean_dapa_bid_result 의 사업자번호 마스터)",
    "clean_company_name_link": "파생(업체명 → clean_company 연결 결과)",
    "clean_openfiscal_program_link": "파생(세부사업명 개편 연결표)",
    "clean_excluded_row": "제외 기록 표 자체",
}

# 전자 판정 일치 — (이름, 불일치 행 수를 세는 SQL). ref_fsg 에 없는 군급은 비전자(0)로 본다
FLAG_SQL = [
    ("ref_fsg ↔ ref_fsc(하위 FSC 4자리)",
     "SELECT COUNT(*) FROM ref_fsc c JOIN ref_fsg g ON g.fsg_code = c.fsc2 WHERE c.is_electronic_group <> g.is_electronic_group"),
    ("clean_kdsis_nsn.is_electronic_group ↔ ref_fsg",
     "SELECT COUNT(*) FROM clean_kdsis_nsn k LEFT JOIN ref_fsg g ON g.fsg_code = k.fsg2 "
     "WHERE k.is_electronic_group <> COALESCE(g.is_electronic_group, 0)"),
    ("clean_dapa_localized_item.is_electronic_group ↔ ref_fsg",
     "SELECT COUNT(*) FROM clean_dapa_localized_item b LEFT JOIN ref_fsg g ON g.fsg_code = b.fsc2 "
     "WHERE b.is_electronic_group <> COALESCE(g.is_electronic_group, 0)"),
    ("clean_dapa_overseas_plan_api.is_elec ↔ ref_fsg",
     "SELECT COUNT(*) FROM clean_dapa_overseas_plan_api a LEFT JOIN ref_fsg g ON g.fsg_code = a.fsg2 "
     "WHERE a.is_elec <> COALESCE(g.is_electronic_group, 0)"),
]


# ---------------------------------------------------------------------------
# 시드 SQL 해석 · 값 비교 (DB 접속 없음 — tests/test_check_integrity.py)
# ---------------------------------------------------------------------------
_INSERT = re.compile(r"INSERT\s+(?:IGNORE\s+)?INTO\s+(\w+)\s*\(([^)]*)\)\s*VALUES", re.IGNORECASE)
_BARE = re.compile(r"[^,)\s]+")


def parse_seed_sql(text: str) -> dict[str, tuple[list[str], list[tuple]]]:
    """seed_ref.sql 의 INSERT … VALUES 튜플 → {표: (열 목록, 행 목록)}. 값은 문자열 · None(NULL), 숫자도 문자열 그대로.
    줄 머리 -- 주석은 load_db 처럼 먼저 걷어내고, 줄 끝 -- 주석은 튜플 사이에서 건너뛴다."""
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
    out: dict[str, tuple[list[str], list[tuple]]] = {}
    for m in _INSERT.finditer(body):
        cols = [c.strip().strip("`") for c in m.group(2).split(",")]
        rows = out.setdefault(m.group(1), (cols, []))[1]
        i = m.end()
        while True:
            i = _skip(body, i)
            if i >= len(body) or body[i] != "(":
                break
            row, i = _tuple(body, i + 1)
            rows.append(row)
            i = _skip(body, i)
            if i < len(body) and body[i] == ",":
                i += 1
                continue
            break
    return out


def _skip(s: str, i: int) -> int:
    """공백과 줄 끝 -- 주석을 건너뛴다."""
    while i < len(s):
        if s[i].isspace():
            i += 1
        elif s.startswith("--", i):
            j = s.find("\n", i)
            i = len(s) if j < 0 else j
        else:
            break
    return i


def _tuple(s: str, i: int) -> tuple[tuple, int]:
    """'(' 다음 위치부터 ')' 까지 값 목록. 작은따옴표 문자열('' 과 \\ 이스케이프) · NULL · 따옴표 없는 값."""
    vals: list = []
    while True:
        i = _skip(s, i)
        if s[i] == "'":
            j, buf = i + 1, []
            while True:
                if s.startswith("''", j):
                    buf.append("'")
                    j += 2
                elif s[j] == "'":
                    break
                elif s[j] == "\\":
                    buf.append(s[j + 1])
                    j += 2
                else:
                    buf.append(s[j])
                    j += 1
            vals.append("".join(buf))
            i = j + 1
        else:
            m = _BARE.match(s, i)
            if not m:
                raise ValueError(f"시드 구문 해석 실패(위치 {i}): {s[i:i + 40]!r}")
            vals.append(None if m.group(0).upper() == "NULL" else m.group(0))
            i = m.end()
        i = _skip(s, i)
        if s[i] == ",":
            i += 1
        elif s[i] == ")":
            return tuple(vals), i + 1
        else:
            raise ValueError(f"시드 구문 해석 실패(위치 {i}): {s[i:i + 40]!r}")


def norm(v) -> str | None:
    """DB 값·원본 문자열을 비교용으로 — NULL·빈 문자열은 None, 숫자는 값(12.50 = 12.5), 참거짓은 1/0, 날짜는 ISO."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, dt.datetime):
        return v.isoformat(sep=" ")
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, bytes):
        v = v.decode("utf-8")
    s = str(v)
    if s == "":
        return None
    if s.lower() in ("true", "false"):
        return "1" if s.lower() == "true" else "0"
    try:
        d = decimal.Decimal(s)
    except decimal.InvalidOperation:
        return s
    return format(d.normalize(), "f") if d.is_finite() else s


def _short(v: str | None, n: int = 40) -> str:
    return "NULL" if v is None else (v if len(v) <= n else v[:n] + "…")


def diff_rows(table: str, key: list[str], src: list[dict], db: list[dict], cols: list[str], label: str) -> list[str]:
    """원본(시드·CSV) 행과 DB 행을 키로 맞춰 차이를 문장으로. cols 는 비교할 값 열(키 제외)."""
    def keyed(rows):
        return {tuple(norm(r.get(k)) for k in key): r for r in rows}
    s, d = keyed(src), keyed(db)
    name = lambda k: f"{table}[{', '.join(_short(x) for x in k)}]"  # noqa: E731
    out = [f"{name(k)}: {label}에만 있음(DB에 없음)" for k in sorted(set(s) - set(d), key=str)]
    out += [f"{name(k)}: DB에만 있음({label}에 없음)" for k in sorted(set(d) - set(s), key=str)]
    for k in sorted(set(s) & set(d), key=str):
        for c in cols:
            a, b = norm(s[k].get(c)), norm(d[k].get(c))
            if a != b:
                out.append(f"{name(k)}.{c}: DB {_short(b)} ≠ {label} {_short(a)}")
    return out


# ---------------------------------------------------------------------------
# DB 조회
# ---------------------------------------------------------------------------
def fetch(cur, table: str) -> list[dict]:
    cur.execute(f"SELECT * FROM `{table}`")
    names = [c[0] for c in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def primary_key(cur, table: str) -> list[str]:
    cur.execute("SELECT column_name FROM information_schema.key_column_usage WHERE table_schema = DATABASE() "
                "AND table_name = %s AND constraint_name = 'PRIMARY' ORDER BY ordinal_position", (table,))
    return [r[0] for r in cur.fetchall()]


def seed_drift(cur) -> list[str]:
    """seed_ref.sql ↔ DB 차이(비어 있지 않은 표만 — 빈 표는 첫 적재라 차이가 아니다). load_db.do_ref 가 시드를 돌리기 전에도 부른다."""
    out: list[str] = []
    for table, (cols, rows) in parse_seed_sql(load_db.SEED_SQL.read_text(encoding="utf-8")).items():
        db = fetch(cur, table)
        if not db:
            continue
        key = primary_key(cur, table)
        out += diff_rows(table, key, [dict(zip(cols, r)) for r in rows], db, [c for c in cols if c not in key], "시드")
    return out


# ---------------------------------------------------------------------------
# 점검 3종 — 각 결과는 (상태 PASS/FAIL/SKIP, 대상, 요약, 차이 줄 목록)
# ---------------------------------------------------------------------------
def check_seed(cur) -> list[tuple[str, str, str, list[str]]]:
    res = []
    for table, (cols, rows) in parse_seed_sql(load_db.SEED_SQL.read_text(encoding="utf-8")).items():
        db = fetch(cur, table)
        key = primary_key(cur, table)
        msgs = diff_rows(table, key, [dict(zip(cols, r)) for r in rows], db, [c for c in cols if c not in key], "시드")
        res.append(("FAIL" if msgs else "PASS", f"{table} ↔ db/seed_ref.sql", f"{len(rows)}행, 차이 {len(msgs)}", msgs))
    for table, path, enc, ren in CSV_REF:
        rel = path.relative_to(load_db.ROOT).as_posix()
        if not path.exists():
            res.append(("FAIL", f"{table} ↔ {rel}", "파일 없음", []))
            continue
        df = load_db.read_csv_str(path, enc).rename(columns=ren)
        if table == "ref_semi_policy_timeline":   # load_db 가 CSV 행 순서를 row_no 로 붙인다
            df.insert(0, "row_no", [str(i) for i in range(1, len(df) + 1)])
        db = fetch(cur, table)
        if not db:
            res.append(("FAIL", f"{table} ↔ {rel}", "DB 표가 비어 있음(load_db.py --ref 미적재)", []))
            continue
        key = primary_key(cur, table)
        cols = [c for c in df.columns if c in db[0] and c not in key]
        msgs = diff_rows(table, key, df.to_dict("records"), db, cols, "CSV")
        res.append(("FAIL" if msgs else "PASS", f"{table} ↔ {rel}", f"{len(df)}행, 차이 {len(msgs)}", msgs))
    return res


def check_balance(cur) -> list[tuple[str, str, str, list[str]]]:
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() "
                "AND table_type = 'BASE TABLE' AND table_name LIKE 'clean\\_%'")
    tables = sorted(r[0] for r in cur.fetchall())
    cur.execute("SELECT table_name, SUM(reason_code <> 'KEY_CONFLICT'), COUNT(*) FROM clean_excluded_row GROUP BY table_name")
    excl = {t: (int(a), int(b)) for t, a, b in cur.fetchall()}
    res = []
    for t in tables:
        if t in BALANCE_SKIP:
            res.append(("SKIP", t, BALANCE_SKIP[t], []))
            continue
        if t not in BALANCE:
            res.append(("FAIL", t, "검산 방식 미등록 — check_integrity.py BALANCE(또는 BALANCE_SKIP)에 원본 키·방식을 추가", []))
            continue
        key, how = BALANCE[t]
        raw = load_db.RAW_TABLES[key]["expected"]
        non_kc, all_ex = excl.get(key, (0, 0))
        if how == "rows":
            cur.execute(f"SELECT COUNT(*) FROM `{t}`")
            n = int(cur.fetchone()[0])
            got, expr = n + all_ex, f"clean {n:,} + 제외 {all_ex}"
        elif how == "distinct":
            cur.execute(f"SELECT COUNT(DISTINCT raw_row_id) FROM `{t}`")
            n = int(cur.fetchone()[0])
            got, expr = n + all_ex, f"원본 행 고유 {n:,} + 제외 {all_ex}"
        else:
            cur.execute(f"SELECT COALESCE(SUM(dup_count), 0) FROM `{t}`")
            n = int(cur.fetchone()[0])
            got, expr = n + non_kc, f"dup_count 합 {n:,} + 제외 {non_kc}(KEY_CONFLICT {all_ex - non_kc}행은 dup_count 에 포함)"
        ok = got == raw
        res.append(("PASS" if ok else "FAIL", t, f"{key} {raw:,} {'=' if ok else '≠'} {expr}", []))
    orphan = sorted(set(excl) - {k for k, _ in BALANCE.values()})
    for key in orphan:
        res.append(("FAIL", f"clean_excluded_row[{key}]", "제외 기록의 원본 키가 BALANCE 에 없음", []))
    return res


def check_flag(cur) -> list[tuple[str, str, str, list[str]]]:
    cur.execute("SELECT GROUP_CONCAT(fsg_code ORDER BY fsg_code) FROM ref_fsg WHERE is_electronic_group = 1")
    groups = cur.fetchone()[0]
    res = [("PASS" if groups == "58,59,60" else "FAIL", "ref_fsg 전자 군급", f"{groups} (기준 58·59·60, 09-21 M4)", [])]
    for name, sql in FLAG_SQL:
        cur.execute(sql)
        n = int(cur.fetchone()[0])
        res.append(("PASS" if n == 0 else "FAIL", name, f"불일치 {n:,}행", []))
    return res


CHECKS = {"seed": ("시드·참조 CSV ↔ DB", check_seed),
          "balance": ("원본 = clean + 제외", check_balance),
          "flag": ("전자 판정(FSG 58·59·60) 일치", check_flag)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", choices=list(CHECKS), help="일부 점검만")
    ap.add_argument("--max-detail", type=int, default=10, help="FAIL 한 건당 보여 줄 차이 줄 수")
    a = ap.parse_args()
    conn = load_db.connect()
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    try:
        cur = conn.cursor()
        for i, key in enumerate(a.only or list(CHECKS), 1):
            title, fn = CHECKS[key]
            print(f"[{i}] {title}")
            for status, target, info, detail in fn(cur):
                counts[status] += 1
                print(f"  {status:4}  {target} — {info}")
                for line in detail[:a.max_detail]:
                    print(f"          {line}")
                if len(detail) > a.max_detail:
                    print(f"          … 외 {len(detail) - a.max_detail}건")
    finally:
        conn.close()
    print(f"요약: FAIL {counts['FAIL']} · PASS {counts['PASS']} · SKIP {counts['SKIP']}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
