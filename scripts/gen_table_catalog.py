"""db/table_dict.csv(테이블 사전) + db/column_dict.csv(열 사전) + RDS 실측 → docs/db/table-catalog.md 생성.

접속은 scripts/dbconf.py role="etl"(SELECT 만). RDS 에서 가져오는 것: 객체 목록·PK·행 수(COUNT(*))·뷰 열 목록.
사전에 없는 객체 / RDS 에 없는 사전 행은 머리에 경고로 적는다(둘 다 0 이어야 정상).
table_dict.csv 의 kind=file 행(원본 파일 데이터셋 raw_…, 2026-09-22 raw_ 표 삭제 후)은 RDS 밖이라 대조하지 않고
「원본 파일」 절에 파서 기대 건수(scripts/load_db.py RAW_TABLES.expected)로 싣는다.

사용:
  python scripts/gen_table_catalog.py                  # docs/db/table-catalog.md 덮어씀
  python scripts/gen_table_catalog.py --no-count       # 행 수 생략(빠름)
  python scripts/gen_table_catalog.py --out <경로>
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dbconf  # noqa: E402
from load_db import RAW_TABLES  # noqa: E402  원본 파일 데이터셋 키·기대 건수

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GROUPS = [("ref", "참조표 — 기준·라벨"), ("raw", "원본 파일 — DB 밖(data/raw/, read_raw 로 읽음. RDS raw_ 표는 2026-09-22 삭제)"), ("meta", "기록 — 출처·적재 단계·열 사전"),
          ("dim", "차원 — 관세청 HS10"), ("fact", "사실 — 관세청 월별 수출입"), ("clean", "정제 — 노트북이 채움, 화면·뷰의 원천"),
          ("v", "뷰 — 화면이 읽는 집계")]
RAW_COMMON = {"row_id", "source_file", "source_row_no", "loaded_at"}


def esc(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "db" / "table-catalog.md")
    ap.add_argument("--no-count", action="store_true")
    a = ap.parse_args()

    with open(ROOT / "db" / "table_dict.csv", encoding="utf-8") as f:
        tdict = {r["table_name"]: r for r in csv.DictReader(f)}
    cols: dict[str, list[dict]] = {}
    with open(ROOT / "db" / "column_dict.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            cols.setdefault(r["table_name"], []).append(r)
    for v in cols.values():
        v.sort(key=lambda r: int(r["ordinal"]))

    conn = pymysql.connect(**dbconf.pymysql_kwargs("etl"))
    try:
        cur = conn.cursor()
        cur.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema=DATABASE()")
        objs = {n: t for n, t in cur.fetchall()}
        cur.execute("SELECT table_name, GROUP_CONCAT(column_name ORDER BY ordinal_position) FROM information_schema.key_column_usage "
                    "WHERE table_schema=DATABASE() AND constraint_name='PRIMARY' GROUP BY table_name")
        pk = {n: c for n, c in cur.fetchall()}
        cur.execute("SELECT table_name, column_name, column_type FROM information_schema.columns "
                    "WHERE table_schema=DATABASE() ORDER BY table_name, ordinal_position")
        dbcols: dict[str, list[tuple[str, str]]] = {}
        for n, c, t in cur.fetchall():
            dbcols.setdefault(n, []).append((c, t))
        counts: dict[str, int] = {}
        if not a.no_count:
            for n in objs:
                cur.execute(f"SELECT COUNT(*) FROM `{n}`")
                counts[n] = cur.fetchone()[0]
    finally:
        conn.close()

    files = {n for n, r in tdict.items() if r.get("kind") == "file"}   # 원본 파일 데이터셋(RDS 객체 아님)
    missing_dict = sorted(set(objs) - set(tdict))
    missing_db = sorted(set(tdict) - set(objs) - files)
    today = date.today().isoformat()
    n_tab = sum(1 for t in objs.values() if t == "BASE TABLE")
    n_view = len(objs) - n_tab

    L = [f"# 테이블 카탈로그 — 역할·키·주요 열 (RDS `defense_dashboard` 실측 {today})", "",
         f"`scripts/gen_table_catalog.py`가 `db/table_dict.csv`(역할·원천·한 행·쓰는 곳·주의) + `db/column_dict.csv`(열 설명) + RDS(행 수·PK·뷰 열)로 만든다. **손으로 고치지 말고 두 CSV를 고친 뒤 재생성.** "
         f"테이블 {n_tab} · 뷰 {n_view} · 원본 파일 데이터셋 {len(files)}(DB 밖). 화면↔테이블 대응·SQL 예시는 `docs/db/table-guide.md`, DDL은 `db/schema.sql`.", ""]
    if missing_dict or missing_db:
        L += ["> **경고** " + (f"사전에 없는 RDS 객체: {', '.join(missing_dict)}. " if missing_dict else "")
              + (f"RDS에 없는 사전 행: {', '.join(missing_db)}." if missing_db else ""), ""]
    L += ["읽는 법: 행 수는 실측 `COUNT(*)`(원본 파일은 파서 기대 건수). `raw_`는 원본 파일 데이터셋 키이며 열은 원본 파일 열 사전(`column_dict.csv`)이고 파서가 붙이는 `source_file`·`source_row_no`는 표에서 뺐다. PK 열은 굵게. 뷰 열은 열 사전 대상이 아니라(설계 원칙) 이름·타입만 싣는다.", "",
          "## 목차", ""]
    def group_names(g):
        pool = files if g == "raw" else set(objs)
        return sorted(n for n in pool if tdict.get(n, {}).get("grp") == g)

    for g, title in GROUPS:
        L.append(f"- **{g}_** {title}: " + ", ".join(f"`{n}`" for n in group_names(g)))
    L.append("")

    for g, title in GROUPS:
        names = group_names(g)
        L += [f"## {g}_ — {title}", ""]
        for n in names:
            d = tdict[n]
            if n in files:
                exp = RAW_TABLES.get(n, {}).get("expected")
                rows = f"{exp:,}(파서 기대)" if exp else "—"
                pk_txt = "없음(파일 — read_raw row_id = 파서 순번)"
            else:
                rows = f"{counts[n]:,}" if n in counts else "—"
                pk_txt = pk.get(n) or "없음(뷰)"
            L += [f"### `{n}`", "",
                  f"- **역할**: {d['role']}",
                  f"- **원천**: {d['source']} · **한 행**: {d['grain']} · **PK**: `{pk_txt}` · **행 수**: {rows}",
                  f"- **쓰는 곳**: {d['used_by']}"]
            if d["caution"]:
                L.append(f"- **주의**: {d['caution']}")
            L.append("")
            if n in cols:
                pkset = set((pk.get(n) or "").split(","))
                L += ["| 열 | 타입 | 원본 열명 | 설명 |", "|---|---|---|---|"]
                for c in cols[n]:
                    if g == "raw" and c["column_name"] in RAW_COMMON:
                        continue
                    name = f"**`{c['column_name']}`**" if c["column_name"] in pkset else f"`{c['column_name']}`"
                    L.append(f"| {name} | {esc(c['dtype'])} | {esc(c['original_name'])} | {esc(c['description'])} |")
            else:  # 뷰
                L += ["| 열 | 타입 |", "|---|---|"]
                L += [f"| `{c}` | {t} |" for c, t in dbcols.get(n, [])]
            L.append("")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[저장] {a.out} — 객체 {len(objs)} + 원본 파일 {len(files)}(사전 누락 {len(missing_dict)}, RDS 누락 {len(missing_db)})")


if __name__ == "__main__":
    main()
