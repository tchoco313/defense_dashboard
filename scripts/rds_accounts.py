"""RDS 계정 정비(1회성, 2026-09-18) — app_ro 비밀번호 교체 + etl_rw 생성. 비밀값은 파일에만 쓰고 출력하지 않는다.

  python scripts/rds_accounts.py                    # app_ro 교체 + etl_rw 생성(1회성)
  python scripts/rds_accounts.py --dry-run          # 실행할 SQL(비밀번호 마스킹)만 출력
  python scripts/rds_accounts.py --add-dev dev_sua  # 팀원용 스키마 개발 계정 생성(2026-09-18 추가, --dry-run 병용 가능)

역할:
  admin  (마스터, .env MARIADB_ADMIN_*)  — 이 스크립트가 접속하는 계정. 초기 복원·DDL·계정 관리 전용
  app_ro — Streamlit 조회 전용: SELECT, SHOW VIEW. 새 비밀번호 → .streamlit/secrets.toml (사용자가 Community Cloud Secrets 에 붙여 넣음)
  etl_rw — load_db.py·정제 노트북 적재용: SELECT, INSERT, UPDATE, DELETE, SHOW VIEW. 새 비밀번호 → .env MARIADB_PASSWORD
  dev_*  — 팀원 스키마 개발용(--add-dev): defense_dashboard 안에서만 조회·적재·CREATE/ALTER/DROP/INDEX/CREATE VIEW.
           계정 관리·다른 DB·서버 설정 권한 없음. 새 비밀번호 → .credentials/<계정>.txt (gitignore, 전달 뒤 삭제)

전제: .env 에 MARIADB_HOST(RDS)·MARIADB_SSL=1·MARIADB_ADMIN_USER·MARIADB_ADMIN_PASSWORD 가 있어야 한다.
"""
from __future__ import annotations

import re
import secrets
import string
import sys
from pathlib import Path

import pymysql

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dbconf  # noqa: E402

ROOT = dbconf.ROOT
ENV = ROOT / ".env"
SECRETS = ROOT / ".streamlit" / "secrets.toml"
ALPHABET = string.ascii_letters + string.digits  # 따옴표·백슬래시 없이 → TOML·.env 에 그대로 쓸 수 있음

GRANTS = {
    "app_ro": "GRANT SELECT, SHOW VIEW ON `defense_dashboard`.* TO 'app_ro'@'%'",
    "etl_rw": "GRANT SELECT, INSERT, UPDATE, DELETE, SHOW VIEW ON `defense_dashboard`.* TO 'etl_rw'@'%'",
}
# 팀원 스키마 개발 계정(--add-dev). DB 한정 DDL — 글로벌 권한(CREATE USER, SUPER, FILE 등)은 주지 않는다
DEV_PRIVS = "SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW, CREATE TEMPORARY TABLES"
CREDENTIALS_DIR = ROOT / ".credentials"


def newpw(n: int = 28) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def set_env_key(path: Path, key: str, value: str) -> None:
    """KEY=... 줄을 바꾸거나 없으면 끝에 추가. 파일은 UTF-8 유지."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    line = f"{key}={value}"
    if re.search(rf"^{key}=.*$", text, flags=re.M):
        text = re.sub(rf"^{key}=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def write_secrets_toml(host: str, user: str, password: str) -> None:
    SECRETS.parent.mkdir(exist_ok=True)
    SECRETS.write_text(
        "# Streamlit Community Cloud → 앱 설정(⋮ → Settings) → Secrets 에 이 내용을 그대로 붙여 넣는다. 파일은 커밋하지 않는다.\n"
        f'MARIADB_HOST = "{host}"\n'
        'MARIADB_PORT = "3306"\n'
        f'MARIADB_USER = "{user}"\n'
        f'MARIADB_PASSWORD = "{password}"\n'
        'MARIADB_DATABASE = "defense_dashboard"\n'
        'MARIADB_SSL = "1"\n',
        encoding="utf-8", newline="\n")


def add_dev(name: str, dry: bool) -> int:
    """팀원용 스키마 개발 계정 생성. 비밀번호는 .credentials/<name>.txt 에만 기록."""
    if not re.fullmatch(r"dev_[a-z0-9_]{1,20}", name):
        print("계정 이름은 dev_ 로 시작하는 소문자·숫자·밑줄만 허용 (예: dev_sua)"); return 2
    s = dbconf.settings("admin")
    if not s["ssl"]:
        print("MARIADB_SSL=1 이 아닙니다 — RDS 가 아닌 서버에는 실행하지 않습니다"); return 2
    pw = newpw()
    stmts = [
        (f"CREATE USER IF NOT EXISTS '{name}'@'%%' IDENTIFIED BY %s REQUIRE SSL", (pw,)),
        (f"ALTER USER '{name}'@'%%' IDENTIFIED BY %s REQUIRE SSL", (pw,)),
        (f"GRANT {DEV_PRIVS} ON `defense_dashboard`.* TO '{name}'@'%'", ()),
        ("FLUSH PRIVILEGES", ()),
    ]
    print("대상:", dbconf.describe("admin"))
    for sql, _ in stmts:
        print("  ", sql.replace("%s", "'***'").replace("%%", "%"))
    if dry:
        return 0
    conn = pymysql.connect(**dbconf.pymysql_kwargs("admin"))
    try:
        with conn.cursor() as cur:
            for sql, params in stmts:
                cur.execute(sql, params or None)
            conn.commit()
            cur.execute(f"SHOW GRANTS FOR '{name}'@'%'")
            for (g,) in cur.fetchall():
                print("  ", g)
    finally:
        conn.close()
    CREDENTIALS_DIR.mkdir(exist_ok=True)
    out = CREDENTIALS_DIR / f"{name}.txt"
    out.write_text(
        f"# RDS 접속 정보 — 전달 뒤 이 파일을 삭제한다. 채팅·메일에 붙이지 말 것.\n"
        f"host={s['host']}\nport=3306\nuser={name}\npassword={pw}\ndatabase=defense_dashboard\nssl=required (CA: certs/rds-global-bundle.pem)\n",
        encoding="utf-8", newline="\n")
    print(f"{name} created → {out.relative_to(ROOT)} (비밀번호는 파일에만 기록)")
    return 0


def main() -> int:
    dry = "--dry-run" in sys.argv
    if "--add-dev" in sys.argv:
        i = sys.argv.index("--add-dev")
        if i + 1 >= len(sys.argv):
            print("--add-dev <계정이름> 형식으로 지정 (예: --add-dev dev_sua)"); return 2
        return add_dev(sys.argv[i + 1], dry)
    s = dbconf.settings("admin")
    if not s["ssl"]:
        print("MARIADB_SSL=1 이 아닙니다 — RDS 가 아닌 서버에는 실행하지 않습니다"); return 2
    pw_app, pw_etl = newpw(), newpw()
    stmts = [
        ("ALTER USER 'app_ro'@'%%' IDENTIFIED BY %s REQUIRE SSL", (pw_app,)),
        (GRANTS["app_ro"], ()),
        ("CREATE USER IF NOT EXISTS 'etl_rw'@'%%' IDENTIFIED BY %s REQUIRE SSL", (pw_etl,)),
        ("ALTER USER 'etl_rw'@'%%' IDENTIFIED BY %s REQUIRE SSL", (pw_etl,)),
        (GRANTS["etl_rw"], ()),
        ("FLUSH PRIVILEGES", ()),
    ]
    print("대상:", dbconf.describe("admin"))
    for sql, _ in stmts:
        print("  ", sql.replace("%s", "'***'").replace("%%", "%"))
    if dry:
        return 0
    conn = pymysql.connect(**dbconf.pymysql_kwargs("admin"))
    try:
        with conn.cursor() as cur:
            for sql, params in stmts:
                cur.execute(sql, params or None)  # params 없으면 % 포맷을 건너뛴다(GRANT 의 '%')
            conn.commit()
            for u in ("app_ro", "etl_rw"):
                cur.execute(f"SHOW GRANTS FOR '{u}'@'%'")
                for (g,) in cur.fetchall():
                    print("  ", g)
    finally:
        conn.close()
    # 파일에만 기록
    set_env_key(ENV, "MARIADB_USER", "etl_rw")
    set_env_key(ENV, "MARIADB_PASSWORD", pw_etl)
    write_secrets_toml(s["host"], "app_ro", pw_app)
    print("app_ro rotated → .streamlit/secrets.toml / etl_rw created → .env MARIADB_USER·MARIADB_PASSWORD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
