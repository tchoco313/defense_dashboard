"""운영 DB(AWS RDS MySQL 8.4, defense_dashboard) 읽기 전용 접속 — Streamlit 페이지 공용.

- 접속 정보는 scripts/dbconf.py 가 읽는다: 로컬은 `.env`의 MARIADB_*(etl_rw), Streamlit Community Cloud 는 앱 설정 Secrets 의
  같은 키(app_ro, SELECT 전용). MARIADB_SSL=1 이면 TLS.
- 조회는 SQLAlchemy `text()` + 바인딩 파라미터만 쓴다(문자열 포맷으로 SQL을 만들지 않는다).
- 결과는 `st.cache_data`(TTL 1시간)로 캐시 — 관세청 뷰는 하루 안에 바뀌지 않는다.
"""
from __future__ import annotations

import sys
from datetime import date
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


@st.cache_data(ttl=CACHE_TTL, show_spinner=False, max_entries=500)   # 조건 조합이 많아도 메모리가 끝없이 늘지 않게
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


def try_query(sql: str, params: dict | None = None) -> tuple[pd.DataFrame | None, str | None]:
    """(df, None) 성공 · (None, '<예외 클래스명>') 실패(테이블 미적재·접속 끊김).

    오류는 클래스 이름만 돌려준다 — 메시지·호스트·DSN·비밀번호는 담지 않는다(db_ready 와 같은 표기).
    실패값은 캐시되지 않으므로 어떤 `@st.cache_data` 함수 안에서도 부르지 않는다(실패가 TTL 동안 고정되는 것을 막는다).
    """
    try:
        return query(sql, params), None
    except (SQLAlchemyError, DBConfigError, pd.errors.DatabaseError) as e:  # pandas 가 SQL 오류를 DatabaseError 로 감싼다
        orig = getattr(e, "orig", None)
        return None, type(orig or e).__name__


def safe_query(sql: str, params: dict | None = None) -> pd.DataFrame | None:
    """try_query 의 df 만 — 실패하면 None. 빈 결과(0행)는 None 이 아니라 빈 DataFrame 이므로 호출부는 둘을 구분한다."""
    return try_query(sql, params)[0]


def data_stamp(dataset_key: str = "customs_all", table: str = "fact_customs_monthly") -> dict:
    """데이터 하나의 「자료 기간」과 「DB 적재일」 — 상단바·CSV 머리줄 공용. 캐시하지 않는다(안쪽 SELECT 는 query() 가 캐시).

    - period : 자료 자체의 기간. 관세청(fact_customs_monthly)은 적재된 yyyymm 실제 범위(예 2016.01~2026.08),
               그 밖은 meta_dataset.period_start~period_end(+「(부분)」). 둘 다 없으면 「기준일 미표기」(기간이 없는 목록형 자료).
    - loaded : meta_load_log 에서 **그 표**(table)의 최근 measured_at 날짜 — 표마다 다르다(전체 최근값이 아님).
    - today  : 내려받은 날(파일 생성일). 자료 기간·적재일과 섞어 「기준일」 하나로 부르지 않는다.
    - error  : 조회 실패 시 예외 클래스명(호스트·메시지 없음), 아니면 None.
    """
    e1 = None
    period = None
    if table == "fact_customs_monthly":
        cov, e1 = try_query("SELECT MIN(yyyymm) AS s, MAX(yyyymm) AS e FROM fact_customs_monthly")
        if cov is not None and not cov.empty and cov.iloc[0]["e"] is not None:
            s, e = str(cov.iloc[0]["s"]), str(cov.iloc[0]["e"])
            period = f"{s[:4]}.{s[4:]}~{e[:4]}.{e[4:]}"
    else:
        meta, e1 = try_query("SELECT period_start, period_end, is_partial_period FROM meta_dataset WHERE dataset_key = :k",
                             {"k": dataset_key})
        if meta is not None and not meta.empty and pd.notna(meta.iloc[0]["period_start"]):
            r = meta.iloc[0]
            end = f"{pd.Timestamp(r['period_end']):%Y.%m}" if pd.notna(r["period_end"]) else ""
            period = f"{pd.Timestamp(r['period_start']):%Y.%m}~{end}" + (" (부분)" if int(r["is_partial_period"] or 0) else "")
    log, e2 = try_query("SELECT DATE(MAX(measured_at)) AS d FROM meta_load_log WHERE table_name = :t", {"t": table})
    loaded = str(log.iloc[0]["d"]) if log is not None and not log.empty and pd.notna(log.iloc[0]["d"]) else None
    return {"dataset_key": dataset_key, "table": table, "period": period or "기준일 미표기", "has_period": period is not None,
            "loaded": loaded, "today": date.today().isoformat(), "error": e1 or e2}


def db_ready() -> bool:
    """접속 확인. 실패하면 안내 + 재시도 버튼을 그리고 False 를 돌려준다."""
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    # 공개 화면에는 인프라 구조(서비스 이름 · 방화벽 · 설정 키 이름)를 쓰지 않는다 — 점검 안내는 서버 콘솔(앱 소유자만 봄)로
    except DBConfigError as e:
        print(f"[db_ready] 접속 설정 오류: {e}", file=sys.stderr)
        st.error("데이터 연결 설정을 읽지 못했습니다(설정 오류). 잠시 뒤 다시 열어 주세요.")
    except SQLAlchemyError as e:
        cls = type(e.orig).__name__ if getattr(e, "orig", None) else type(e).__name__
        print(f"[db_ready] 접속 실패 {cls} — 보안 그룹 허용 IP · Secrets/.env 의 MARIADB_* 값을 확인", file=sys.stderr)
        st.error(f"데이터를 불러오지 못했습니다({cls}). 잠시 뒤 「다시 연결」을 눌러 주세요.")
    if st.button("다시 연결", type="primary"):
        engine.clear()          # 실패한 조회는 캐시되지 않으므로 조회 캐시는 비우지 않는다(누구나 전역 캐시를 비우지 못하게)
        st.rerun()
    return False
