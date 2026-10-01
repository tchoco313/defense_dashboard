"""관세청 원천 최신 월 확인 — 페이지를 볼 때 관세청 OpenAPI(15100475)에 직접 물어, 화면(DB)에 반영된 최신 월보다
새 달이 공개됐는지 본다. DB 값은 바꾸지 않는다(적재는 scripts/fetch_customs.py → scripts/load_db.py).

- 확인: 분석 대상 품목(코드 순)에 「DB 최신 월 ~ 이번 달(KST)」을 묻되, 행이 오는 첫 품목에서 멈춘다(보통 1회 · 작은 응답).
  응답의 가장 늦은 월 = 관세청 공개 최신 월. DB 최신 월보다 늦으면 그 새 달만 분석 대상 품목 수만큼 더 물어 합계를 낸다.
- 캐시: 성공 6시간(개발계정 10,000회/일). 실패는 캐시하지 않되 10분간 다시 부르지 않는다(해외 서버에서 막힐 때 페이지가 매번 기다리지 않게).
- 키: DATA_GO_KR_SERVICE_KEY — 환경변수 · 로컬 .env · 공개 앱 st.secrets 순. 요청 URL 에 키가 들어가므로 예외는 **클래스명만** 남긴다
  (str(e) 를 화면 · 로그에 내지 않는다).
- 문구: 「실시간 · 모니터링 · 감시」라고 부르지 않는다 — 「원천 최신 월 확인 · 확인 시각」.
- 순수 함수(parse_items · month_window · monthly_totals · classify)는 streamlit · 네트워크 없이 tests/test_live.py 가 검증한다.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

import pandas as pd

ENDPOINT = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"   # scripts/fetch_customs.py 와 같은 API
KEY_NAME = "DATA_GO_KR_SERVICE_KEY"
KST = timezone(timedelta(hours=9))
OK_TTL = 6 * 3600
FAIL_PAUSE = 600
SOURCE = "관세청 품목별 국가별 수출입실적 OpenAPI(15100475)"


# ── 순수 함수 ────────────────────────────────────────────────────────────────
def ym_add(yyyymm: str, n: int) -> str:
    p = pd.Period(f"{yyyymm[:4]}-{yyyymm[4:]}", "M") + n
    return p.strftime("%Y%m")


def ym_dot(yyyymm: str | None) -> str:
    return f"{yyyymm[:4]}.{yyyymm[4:]}" if yyyymm else "—"


def month_window(db_latest: str, now_ym: str) -> tuple[str, str] | None:
    """DB 최신 월부터 이번 달까지(API 조회 기간은 1년 이내). DB 가 이번 달보다 늦으면(시계 오류 등) None."""
    if db_latest > now_ym:
        return None
    start = max(db_latest, ym_add(now_ym, -11))
    return start, now_ym


def parse_items(xml_text: str) -> list[dict]:
    """응답 XML → 월별 행 [{yyyymm, hs10, stat_cd, imp, exp}]. 총계행(year 가 'YYYY.MM' 아님)은 뺀다.
    resultCode 가 00 이 아니면 RuntimeError(코드만 — 메시지에 요청 정보를 넣지 않는다)."""
    from defusedxml import ElementTree as DET   # 외부 응답 → XXE · 엔티티 폭탄 방지

    root = DET.fromstring(xml_text)
    code = (root.findtext(".//resultCode") or "").strip()
    if code and code != "00":
        raise RuntimeError(f"resultCode={code}")
    out = []
    for item in root.iter("item"):
        y = (item.findtext("year") or "").strip()
        if len(y) != 7 or y[4] != "." or not y.replace(".", "").isdigit():
            continue
        out.append({"yyyymm": y.replace(".", ""), "hs10": (item.findtext("hsCd") or "").strip(),
                    "stat_cd": (item.findtext("statCd") or "").strip(),
                    "imp": float((item.findtext("impDlr") or "0").strip() or 0),
                    "exp": float((item.findtext("expDlr") or "0").strip() or 0)})
    return out


def monthly_totals(rows: list[dict]) -> pd.DataFrame:
    """월별 행 → 월 합계(yyyymm, imp, exp)."""
    if not rows:
        return pd.DataFrame({"yyyymm": pd.Series(dtype="str"), "imp": pd.Series(dtype="float64"),
                             "exp": pd.Series(dtype="float64")})
    return pd.DataFrame(rows).groupby("yyyymm", as_index=False)[["imp", "exp"]].sum()


def classify(db_latest: str, months: list[str]) -> tuple[str, str | None]:
    """(상태, 관세청 공개 최신 월). same = DB 와 같은 달까지 공개 / newer = 새 달 공개 / unknown = 응답에 DB 최신 월도 없음."""
    if not months:
        return "unknown", None
    src = max(months)
    if src > db_latest:
        return "newer", src
    return ("same", src) if src == db_latest else ("unknown", src)


# ── 네트워크(streamlit 캐시) ──────────────────────────────────────────────────
def _key() -> str:
    key = os.getenv(KEY_NAME, "").strip()
    if not key:
        env = Path(__file__).resolve().parents[1] / ".env"
        if env.exists():
            from dotenv import dotenv_values
            key = (dotenv_values(env).get(KEY_NAME) or "").strip()
    if not key:
        try:
            import streamlit as st
            key = str(st.secrets.get(KEY_NAME, "")).strip()
        except Exception:   # noqa: BLE001 — secrets.toml 없음 등: 키 없음과 같다
            key = ""
    return unquote(key) if "%" in key else key


def _call(key: str, hs: str, start: str, end: str) -> list[dict]:
    import requests

    r = requests.get(ENDPOINT, params={"serviceKey": key, "strtYymm": start, "endYymm": end, "hsSgn": hs},
                     timeout=(5, 20))
    r.raise_for_status()
    return parse_items(r.text)


def _cached():
    """streamlit 캐시 함수 두 개를 한 번만 만든다(모듈 import 시 streamlit 을 요구하지 않게 — 테스트용)."""
    import streamlit as st

    @st.cache_data(ttl=OK_TTL, show_spinner=False)
    def fetch(db_latest: str, hs_list: tuple[str, ...], now_ym: str) -> dict:
        key = _key()
        win = month_window(db_latest, now_ym)
        if win is None:
            raise RuntimeError("window")
        months: list[str] = []
        for h in hs_list:                     # 행이 오는 첫 품목으로 확인(보통 첫 호출에서 끝난다)
            months = monthly_totals(_call(key, h, *win))["yyyymm"].tolist()
            if months:
                break
            time.sleep(0.15)
        state, src = classify(db_latest, months)
        new = None
        if state == "newer":
            rows = []
            for h in hs_list:
                t = monthly_totals(_call(key, h, ym_add(db_latest, 1), src))
                rows.append(t.assign(hs6=h))
                time.sleep(0.15)
            new = pd.concat(rows, ignore_index=True)
        return {"state": state, "src_latest": src, "new": new,
                "checked_at": datetime.now(KST).strftime("%m-%d %H:%M")}

    @st.cache_resource
    def pause() -> dict:
        return {"until": 0.0, "error": None}

    return fetch, pause


_FNS = None


def source_check(db_latest: str, hs_list: list[str]) -> dict:
    """{state: same|newer|unknown|failed|nokey, src_latest, db_latest, new(DataFrame|None), checked_at, error(클래스명)}."""
    global _FNS
    base = {"db_latest": db_latest, "src_latest": None, "new": None, "checked_at": datetime.now(KST).strftime("%m-%d %H:%M"),
            "error": None}
    if not db_latest or not hs_list:
        return {**base, "state": "unknown"}
    if not _key():
        return {**base, "state": "nokey"}
    if _FNS is None:
        _FNS = _cached()
    fetch, pause = _FNS
    p = pause()
    if time.time() < p["until"]:
        return {**base, "state": "failed", "error": p["error"]}
    try:
        res = fetch(db_latest, tuple(sorted(set(hs_list))), datetime.now(KST).strftime("%Y%m"))   # 정렬 → 홈 · ① 이 같은 캐시
    except Exception as e:   # noqa: BLE001 — 클래스명만(요청 URL 에 키가 있다)
        p["until"], p["error"] = time.time() + FAIL_PAUSE, type(e).__name__
        return {**base, "state": "failed", "error": type(e).__name__}
    return {**base, **res}


def line_text(c: dict) -> str:
    """한 줄 문구(HTML 아님 — 호출부가 escape)."""
    db, src, at = ym_dot(c["db_latest"]), ym_dot(c.get("src_latest")), c.get("checked_at", "")
    s = c["state"]
    if s == "same":
        return f"관세청 공개 최신 {src} = 화면 반영 {db} · 일치 · 확인 {at}"
    if s == "newer":
        return f"관세청이 {src}까지 공개 · 화면은 {db}까지(다음 적재 때 반영) · 확인 {at}"
    if s == "unknown":
        return f"관세청 응답에서 {db} 행을 찾지 못해 확인 보류 · 화면 값은 DB 기준 · 확인 {at}"
    if s == "nokey":
        return "원천 확인 꺼짐(인증키 미설정) · 화면 값은 DB 기준"
    return f"관세청 원천 확인 실패({c.get('error') or '—'}) · 화면 값은 DB 기준"


def as_stamp(c: dict) -> dict:
    """kdesign.hero 의 「자료 기준」 줄 형식(data_stamp 모양)으로."""
    return {"has_period": True, "period": line_text(c), "error": None}
