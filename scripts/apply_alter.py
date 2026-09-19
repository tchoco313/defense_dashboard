"""db/alter_*.sql 을 운영 DB(RDS)에 admin 계정으로 적용한다.

접속은 scripts/dbconf.py role="admin"(.env 의 MARIADB_ADMIN_USER/PASSWORD, TLS). mysql.exe 없이 pymysql 로 실행하며,
파일을 세미콜론 단위로 나눠 한 문장씩 보낸다(주석 줄 제거, 문자열 안의 세미콜론은 지원하지 않음 — alter 파일 규칙).
각 문장 뒤 SHOW WARNINGS 를 출력하고, 오류가 나면 그 문장에서 멈춘다(autocommit — DDL 은 어차피 롤백 불가).

사용:
  python scripts/apply_alter.py db/alter_2026-09-18_column_dict_gap.sql            # 1회 적용
  python scripts/apply_alter.py --twice db/alter_....sql                             # 2회 실행해 멱등성 확인
  python scripts/apply_alter.py --dry-run db/alter_....sql                           # 문장 분리 결과만 출력
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymysql

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dbconf  # noqa: E402


def split_statements(sql: str) -> list[str]:
    body = "\n".join(line for line in sql.split("\n") if not line.lstrip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def apply(path: Path, conn, label: str) -> None:
    stmts = split_statements(path.read_text(encoding="utf-8"))
    cur = conn.cursor()
    for i, stmt in enumerate(stmts, 1):
        head = " ".join(stmt.split())[:90]
        try:
            affected = cur.execute(stmt)
        except pymysql.MySQLError as e:
            print(f"[{label}] {i}/{len(stmts)} 실패: {head}\n  {e}")
            raise SystemExit(1)
        cur.execute("SHOW WARNINGS")
        warns = cur.fetchall()
        note = f" warnings={len(warns)}" if warns else ""
        print(f"[{label}] {i}/{len(stmts)} ok rows={affected}{note}: {head}")
        for w in warns:
            print(f"    {w}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--twice", action="store_true", help="같은 파일을 두 번 실행해 재실행 가능성 확인")
    ap.add_argument("--dry-run", action="store_true", help="접속 없이 문장 분리 결과만 출력")
    args = ap.parse_args()

    if args.dry_run:
        for p in args.files:
            for i, s in enumerate(split_statements(p.read_text(encoding="utf-8")), 1):
                print(f"{p.name} {i}: {' '.join(s.split())[:120]}")
        return

    print(dbconf.describe("admin"))
    conn = pymysql.connect(**dbconf.pymysql_kwargs("admin", autocommit=True))
    try:
        for p in args.files:
            apply(p, conn, f"{p.name} #1")
            if args.twice:
                apply(p, conn, f"{p.name} #2")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
