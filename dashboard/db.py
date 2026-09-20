"""운영 DB(AWS RDS MySQL 8.4, defense_dashboard) 읽기 전용 접속 — Streamlit 페이지 공용.

- 접속 정보는 scripts/dbconf.py 가 읽는다: 로컬은 `.env`의 MARIADB_*(etl_rw), Streamlit Community Cloud 는 앱 설정 Secrets 의
  같은 키(app_ro, SELECT 전용). MARIADB_SSL=1 이면 TLS.
- 조회는 SQLAlchemy `text()` + 바인딩 파라미터만 쓴다(문자열 포맷으로 SQL을 만들지 않는다).
- 결과는 `st.cache_data`(TTL 1시간)로 캐시 — 관세청 뷰는 하루 안에 바뀌지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from decimal import Decimal

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dbconf  # noqa: E402  접속 설정 단일 지점(.env → st.secrets)
from dbconf import DBConfigError  # noqa: E402,F401  (페이지에서 import 하던 이름 유지)

CACHE_TTL = 3600


@st.cache_resource(show_spinner=False)
def engine() -> Engine:
    # pool_pre_ping: 끊긴 연결을 재사용하지 않도록
    return create_engine(dbconf.sqlalchemy_url("etl"), pool_pre_ping=True, pool_recycle=1800,
                         connect_args=dbconf.sqlalchemy_connect_args("etl"))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """SELECT 한 문장을 DataFrame 으로. 파라미터는 `:name` 바인딩(list/tuple 값은 `IN :name` 확장).

    MySQL SUM()·DECIMAL 열은 `Decimal` 객체로 오므로 float 로 바꿔 돌려준다(차트·서식용).
    """
    params = params or {}
    stmt = text(sql)
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            stmt = stmt.bindparams(bindparam(k, expanding=True))
    with engine().connect() as conn:
        df = pd.read_sql(stmt, conn, params=params)
    for c in df.columns[df.dtypes == object]:
        first = df[c].dropna()
        if not first.empty and isinstance(first.iloc[0], Decimal):
            df[c] = df[c].astype("float64")
    return df


def safe_query(sql: str, params: dict | None = None) -> pd.DataFrame | None:
    """query() 와 같지만 실패(테이블 미적재·접속 끊김)하면 None — 화면 한 칸만 「—」로 비우고 나머지는 그린다."""
    try:
        return query(sql, params)
    except (SQLAlchemyError, DBConfigError, pd.errors.DatabaseError):  # pandas 가 SQL 오류를 DatabaseError 로 감싼다
        return None


def db_ready() -> bool:
    """접속 확인. 실패하면 안내 + 재시도 버튼을 그리고 False 를 돌려준다(UI/UX 9원칙)."""
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except DBConfigError as e:
        st.error(f"DB 설정 오류 — {e}")
    except SQLAlchemyError as e:
        # 비밀번호·호스트가 메시지에 섞이지 않도록 원인 클래스만 보여 준다
        st.error(f"DB(AWS RDS)에 연결하지 못했습니다 ({type(e.orig).__name__ if getattr(e, 'orig', None) else type(e).__name__}). "
                 "RDS 보안 그룹에 현재 공인 IP가 허용돼 있는지와 Secrets/`.env`의 MARIADB_* 값을 확인하세요.")
    if st.button("다시 연결", type="primary"):
        engine.clear()
        query.clear()
        st.rerun()
    return False
