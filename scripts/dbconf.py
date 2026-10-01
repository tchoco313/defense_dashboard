"""DB 접속 설정의 단일 지점 — 운영 DB는 AWS RDS(MySQL 8.4, defense_dashboard).

접속 정보는 코드에 두지 않는다. 읽는 순서:
  1. 프로젝트 루트 `.env` 의 MARIADB_* (로컬·적재 스크립트·노트북)
  2. `.env` 가 없거나 MARIADB_HOST 가 비면 Streamlit `st.secrets` 의 같은 키 (Community Cloud)

키 (둘 다 같은 이름):
  MARIADB_HOST · MARIADB_PORT · MARIADB_USER · MARIADB_PASSWORD · MARIADB_DATABASE · MARIADB_SSL(1이면 TLS)
  MARIADB_ADMIN_USER · MARIADB_ADMIN_PASSWORD — role="admin" 일 때만 (alter·reset·계정 관리). Streamlit Secrets 에는 넣지 않는다.

역할(role): "etl"(기본, .env 의 MARIADB_USER=etl_rw — SELECT/INSERT/UPDATE/DELETE) · "admin"(마스터) · Streamlit 은 Secrets 의 app_ro(SELECT).
반환 dict 는 비밀번호를 담으므로 print·log 하지 않는다.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
# Amazon RDS 글로벌 CA 번들(공개 파일, https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem).
# MARIADB_SSL=1 이면 이 CA 로 서버 인증서·호스트명을 검증한다 — pymysql 은 ca 없이 ssl={} 만 주면 검증을 끄므로(CERT_NONE) 반드시 지정.
RDS_CA_PATH = ROOT / "certs" / "rds-global-bundle.pem"
REQUIRED = ("MARIADB_HOST", "MARIADB_USER", "MARIADB_PASSWORD")


class DBConfigError(RuntimeError):
    """접속 정보가 없을 때. 메시지에 비밀값을 넣지 않는다."""


def _from_env_file() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    from dotenv import dotenv_values
    return {k: v.strip() for k, v in dotenv_values(ENV_PATH).items() if v and k.startswith("MARIADB_")}


def _from_streamlit_secrets() -> dict[str, str]:
    try:
        import streamlit as st
        return {k: str(v) for k, v in st.secrets.items() if k.startswith("MARIADB_") and v}
    except Exception:  # streamlit 미설치, secrets.toml 없음 등
        return {}


def settings(role: str = "etl") -> dict[str, str]:
    """MARIADB_* 를 모아 host/port/user/password/database/ssl 로 정규화한다."""
    env = _from_env_file()
    if not env.get("MARIADB_HOST"):
        env = _from_streamlit_secrets()
    if role == "etl":
        need = REQUIRED
    elif role == "admin":
        need = ("MARIADB_HOST", "MARIADB_ADMIN_USER", "MARIADB_ADMIN_PASSWORD")
    else:
        raise ValueError(f"role 은 'etl' 또는 'admin': {role!r}")
    missing = [k for k in need if not env.get(k)]
    if missing:
        raise DBConfigError(f"{', '.join(missing)} 가 없습니다 — 로컬은 프로젝트 루트 .env, Streamlit Cloud 는 앱 설정 Secrets 에 넣으세요"
                            + (" (admin 역할은 로컬 .env 전용)" if role == "admin" else ""))
    user = env["MARIADB_ADMIN_USER" if role == "admin" else "MARIADB_USER"]
    password = env["MARIADB_ADMIN_PASSWORD" if role == "admin" else "MARIADB_PASSWORD"]
    return {
        "host": env["MARIADB_HOST"],
        "port": int(env.get("MARIADB_PORT") or 3306),
        "user": user,
        "password": password,
        "database": env.get("MARIADB_DATABASE") or "defense_dashboard",
        "ssl": env.get("MARIADB_SSL", "").lower() in ("1", "true", "yes"),
    }


def ssl_opts() -> dict:
    """pymysql `ssl=` 인자 — RDS CA 번들로 서버 인증서를 검증(CERT_REQUIRED)하고 호스트명도 대조한다."""
    if not RDS_CA_PATH.exists():
        raise DBConfigError(f"RDS CA 번들이 없습니다: certs/{RDS_CA_PATH.name} (저장소에 포함돼야 함)")
    return {"ca": str(RDS_CA_PATH), "check_hostname": True}


def pymysql_kwargs(role: str = "etl", **extra) -> dict:
    """`pymysql.connect(**pymysql_kwargs())`. RDS(MARIADB_SSL=1)면 TLS + RDS CA 번들로 서버 인증서·호스트명 검증."""
    s = settings(role)
    kw = dict(host=s["host"], port=s["port"], user=s["user"], password=s["password"], database=s["database"],
              charset="utf8mb4", connect_timeout=10)
    if s["ssl"]:
        kw["ssl"] = ssl_opts()
    kw.update(extra)
    return kw


def sqlalchemy_url(role: str = "etl"):
    """`create_engine()` 에 넘길 URL 객체. 비밀번호에 `@`·`:`·`%` 가 있어도 안전하게 인코딩된다(문자열 f-string 금지)."""
    from sqlalchemy.engine import URL
    s = settings(role)
    return URL.create("mysql+pymysql", username=s["user"], password=s["password"], host=s["host"],
                      port=s["port"], database=s["database"], query={"charset": "utf8mb4"})


def sqlalchemy_connect_args(role: str = "etl") -> dict:
    args: dict = {"connect_timeout": 5}
    if settings(role)["ssl"]:
        args["ssl"] = ssl_opts()
    return args


def describe(role: str = "etl") -> str:
    """로그용 한 줄 — 비밀번호 없음."""
    s = settings(role)
    return f"{s['user']}@{s['host']}:{s['port']}/{s['database']} ssl={'on' if s['ssl'] else 'off'}"
