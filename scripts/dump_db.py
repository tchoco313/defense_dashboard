"""팀 DB(defense_dashboard) 전체를 MySQL 덤프 한 파일로 내보낸다 — 제출 패키지 · 로컬 실행용.

만드는 것(기본 build/db/, 깃에 올리지 않음):
  defense_dashboard_dump.sql   CREATE DATABASE · 표 44개(구조 + 데이터) · 뷰 31개. MySQL Workbench 「Data Import」나
                               `mysql -u root -p < defense_dashboard_dump.sql` 로 그대로 복원된다(복원 방법은 db/README.md).
  db_rowcount.csv              표마다 행 수(table_name,row_count) — 복원한 DB 가 원본과 같은지 대조하는 기준.

처리:
  - 접속 정보는 scripts/dbconf.py 가 읽는다(.env). 비밀번호는 권한 0600 임시 설정 파일로만 mysqldump 에 넘기고
    끝나면 지운다 — 명령줄 · 화면 출력에 남기지 않는다.
  - 뷰의 DEFINER(만든 계정)를 지운다 — 덤프에 팀 계정 이름이 남지 않고, 그 계정이 없는 PC 에서도 오류 없이 복원된다.
  - 머리 주석의 서버 주소(-- Host:)를 지운다.
  - --single-transaction 으로 한 시점의 일관된 스냅숏을 뜬다(잠금 없음).

필요한 것: MySQL 클라이언트의 mysqldump(8.0 이상). PATH 에 없으면 --mysqldump 로 경로를 준다.

사용(저장소 루트에서):
  python scripts/dump_db.py                       # build/db/ 에 덤프 + 행 수
  python scripts/dump_db.py --out-dir <폴더>
  python scripts/dump_db.py --mysqldump /usr/local/mysql/bin/mysqldump
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dbconf  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DUMP_NAME = "defense_dashboard_dump.sql"
COUNT_NAME = "db_rowcount.csv"
DEFINER_RE = re.compile(rb"DEFINER=`[^`]*`@`[^`]*`\s*")
HOST_RE = re.compile(rb"^-- Host: .*?(\s+Database: )", re.M)


def find_mysqldump(given: str | None) -> str:
    cands = [given] if given else [shutil.which("mysqldump"), "/usr/local/mysql/bin/mysqldump",
                                   "/opt/homebrew/bin/mysqldump", r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe",
                                   r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"]
    for c in cands:
        if c and Path(c).exists():
            return c
    sys.exit("mysqldump 를 찾지 못했습니다 — MySQL 클라이언트를 설치하거나 --mysqldump 로 경로를 주세요.")


def write_defaults_file(s: dict) -> str:
    """[client] 접속 정보를 0600 임시 파일로 — mysqldump --defaults-extra-file 용."""
    fd, path = tempfile.mkstemp(prefix="dumpdb_", suffix=".cnf")
    os.chmod(path, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        pw = s["password"].replace("\\", "\\\\").replace('"', '\\"')
        f.write(f'[client]\nuser="{s["user"]}"\npassword="{pw}"\nhost="{s["host"]}"\nport={s["port"]}\n')
    return path


def dump(mysqldump: str, out: Path) -> None:
    s = dbconf.settings("etl")
    cnf = write_defaults_file(s)
    cmd = [mysqldump, f"--defaults-extra-file={cnf}",
           "--databases", s["database"],
           "--single-transaction", "--no-tablespaces", "--set-gtid-purged=OFF",
           "--default-character-set=utf8mb4", "--hex-blob", "--triggers"]
    if s["ssl"]:
        cmd += [f"--ssl-ca={dbconf.ssl_opts()['ca']}", "--ssl-mode=VERIFY_IDENTITY"]
    try:
        with open(out, "wb") as f:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            head_done = False
            for line in proc.stdout:
                if not head_done and line.startswith(b"-- Host:"):
                    line = HOST_RE.sub(rb"-- Host: (team database)\1", line)
                    head_done = True
                if b"DEFINER=" in line and not line.startswith(b"INSERT"):
                    line = DEFINER_RE.sub(b"", line)
                f.write(line)
            err = proc.stderr.read().decode("utf-8", "replace")
            if proc.wait() != 0:
                sys.exit(f"mysqldump 실패(종료 코드 {proc.returncode}): {err.strip()[:500]}")
            if err.strip():
                print(f"[mysqldump 경고] {err.strip()[:500]}")
    finally:
        os.remove(cnf)


def row_counts(out: Path) -> list[tuple[str, int]]:
    import pymysql
    conn = pymysql.connect(**dbconf.pymysql_kwargs("etl"))
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' ORDER BY table_name")
            tables = [r[0] for r in cur.fetchall()]
            rows = []
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM `{t}`")   # 표 이름은 information_schema 에서 온 값
                rows.append((t, int(cur.fetchone()[0])))
    finally:
        conn.close()
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["table_name", "row_count"])
        w.writerows(rows)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=ROOT / "build" / "db")
    ap.add_argument("--mysqldump", default=None, help="mysqldump 실행 파일 경로(PATH 에 없을 때)")
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    dump_path, count_path = a.out_dir / DUMP_NAME, a.out_dir / COUNT_NAME

    t0 = time.time()
    print(f"덤프 시작 — {dbconf.settings('etl')['database']}")
    dump(find_mysqldump(a.mysqldump), dump_path)
    text = dump_path.read_bytes()
    n_tables = len(re.findall(rb"^CREATE TABLE `", text, re.M))
    n_views = len(re.findall(rb"^/\*!50001 VIEW `", text, re.M))
    left = len(DEFINER_RE.findall(text.replace(b"INSERT", b"")))
    print(f"  {dump_path.name}: {dump_path.stat().st_size / 1e6:,.1f} MB · CREATE TABLE {n_tables} · "
          f"VIEW {n_views} · 남은 DEFINER {left}")
    rows = row_counts(count_path)
    print(f"  {count_path.name}: 표 {len(rows)}개 · 합계 {sum(n for _, n in rows):,}행")
    print(f"끝 ({time.time() - t0:,.0f}초)")


if __name__ == "__main__":
    main()
