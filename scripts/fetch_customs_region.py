"""관세청 시군구별 품목별 수출입실적 (data.go.kr 15134343) 수집.

엔드포인트: https://apis.data.go.kr/1220000/sigunguperprlstperacrs/getSigunguPerPrlstPerAcrs
요청 변수(전부 필수): serviceKey · strtYymm · endYymm · HsSgn(HS 6단위, 대문자 H) · sidoCd(시도코드)
제약: 조회기간 1년 이내 / 호출당. 개발계정 10,000회/일. 한 응답 = 그 시도의 모든 시군구 × 월(거래 없는 시군구·월은 행이 없거나 0).
집계 기준(명세 원문): 수입은 「납세의무자 주소지 우편번호」, 수출은 「제조장소 우편번호」. 금액은 수입 과세가격·수출 신고금액.
단위: 응답 impUsdAmt·expUsdAmt 는 **천 달러**(2026-09-18 확인: 880730 2025년 17개 시도 합 745,179 vs 품목별 국가별 API 총계 745,240,449$).
시도코드(2026-09-18 탐색으로 확인, 행정표준코드와 같음): 11 서울 26 부산 27 대구 28 인천 29 광주 30 대전 31 울산 36 세종
  41 경기 43 충북 44 충남 46 전남 47 경북 48 경남 50 제주 51 강원 52 전북 — 17개. (42 강원·45 전북 옛 코드는 응답 없음)
주의: 2026-07-01 지방행정체계 개편(전남·광주 통합, 인천)으로 시군구 코드·명칭이 바뀜. 개편 전후 sggNm 이 달라질 수 있어 원본 그대로 저장한다.

사용법 (저장소 루트에서):
  python scripts/fetch_customs_region.py --sample                 # 880730 × 경기(41) × 2025 → 화면 출력 (저장 안 함)
  python scripts/fetch_customs_region.py --years 2025             # 화이트리스트 24개 × 17시도 × 2025 = 408회
  python scripts/fetch_customs_region.py                          # 2016~올해 전체 (24 × 17 × 11 = 4,488회, 약 40분)
  python scripts/fetch_customs_region.py --hs 880730 852610 --sido 41 48

키: .env 의 DATA_GO_KR_SERVICE_KEY (15134343 활용신청 후 같은 키로 호출됨).
출력: data/raw/customs/customs_region_<HS>.csv (HS별 1파일, 시도×시군구×월 행) + progress_region.csv (완료 조합, 재실행 시 건너뜀)
"""

import argparse
import csv
import os
import sys
import time
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "data" / "reference" / "hs_whitelist.csv"
OUT_DIR = ROOT / "data" / "raw" / "customs"
PROGRESS = OUT_DIR / "progress_region.csv"
ENDPOINT = "https://apis.data.go.kr/1220000/sigunguperprlstperacrs/getSigunguPerPrlstPerAcrs"

SIDO = {
    "11": "서울", "26": "부산", "27": "대구", "28": "인천", "29": "광주", "30": "대전", "31": "울산", "36": "세종",
    "41": "경기", "43": "충북", "44": "충남", "46": "전남", "47": "경북", "48": "경남", "50": "제주", "51": "강원", "52": "전북",
}

# 응답 item 필드 (명세 그대로) + 호출 조건
FIELDS = ["priodTitle", "sggNm", "hsSgn", "korePrlstNm", "expCnt", "expUsdAmt", "impCnt", "impUsdAmt", "cmtrBlncAmt"]
COLUMNS = FIELDS + ["req_hs", "req_sido", "req_year", "fetched_at"]

SLEEP_SEC = 0.15
RETRY = 3


def load_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
    if not key:
        sys.exit(".env 에 DATA_GO_KR_SERVICE_KEY 가 없다")
    return key


def load_whitelist() -> list[str]:
    with open(WHITELIST, encoding="utf-8") as f:
        return [row["hs_code"] for row in csv.DictReader(f)]


def load_progress() -> set[tuple[str, str, str]]:
    if not PROGRESS.exists():
        return set()
    with open(PROGRESS, encoding="utf-8") as f:
        return {(r["hs"], r["sido"], r["year"]) for r in csv.DictReader(f)}


def mark_progress(hs: str, sido: str, year: str, n_rows: int) -> None:
    new = not PROGRESS.exists()
    with open(PROGRESS, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["hs", "sido", "year", "rows", "fetched_at"])
        w.writerow([hs, sido, year, n_rows, date.today().isoformat()])


def parse(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    code = root.findtext("header/resultCode")
    if code != "00":
        raise RuntimeError(f"resultCode={code} {root.findtext('header/resultMsg')}")
    rows = []
    for item in root.findall(".//item"):
        # 금액·건수는 우측 정렬 공백과 천 단위 쉼표가 붙어 온다(예 '           5,628'). 원본 보존을 위해 strip 만 한다.
        rows.append({f: (item.findtext(f) or "").strip() for f in FIELDS})
    return rows


def call(key: str, hs: str, sido: str, year: int) -> list[dict]:
    params = {"serviceKey": key, "strtYymm": f"{year}01", "endYymm": f"{year}12", "HsSgn": hs, "sidoCd": sido}
    last_err = None
    for attempt in range(1, RETRY + 1):
        try:
            r = requests.get(ENDPOINT, params=params, timeout=90)
            r.raise_for_status()
            return parse(r.text)
        except (requests.RequestException, ET.ParseError, RuntimeError) as e:
            last_err = e
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"{hs}/{sido}/{year} 실패: {last_err}")


def append_rows(hs: str, rows: list[dict], sido: str, year: int) -> None:
    path = OUT_DIR / f"customs_region_{hs}.csv"
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        for row in rows:
            row.update(req_hs=hs, req_sido=sido, req_year=year, fetched_at=date.today().isoformat())
            w.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", action="store_true", help="880730 × 경기(41) × 2025 한 번만 호출해 화면에 출력 (저장 안 함)")
    ap.add_argument("--hs", nargs="*", help="HS6 코드 목록 (기본: data/reference/hs_whitelist.csv)")
    ap.add_argument("--sido", nargs="*", default=list(SIDO), help="시도코드 목록 (기본 17개)")
    ap.add_argument("--years", nargs="*", type=int, default=list(range(2016, date.today().year + 1)))
    args = ap.parse_args()

    key = load_key()

    if args.sample:
        rows = call(key, "880730", "41", 2025)
        print(f"{len(rows)}행 수신")
        for r in rows[:15]:
            print(r)
        return

    hs_list = args.hs or load_whitelist()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = load_progress()
    todo = [(h, s, y) for h in hs_list for s in args.sido for y in args.years if (h, s, str(y)) not in done]
    print(f"호출 예정 {len(todo)}건 (완료 {len(done)}건 건너뜀)")

    total_rows = 0
    for i, (h, s, y) in enumerate(todo, 1):
        try:
            rows = call(key, h, s, y)
        except RuntimeError as e:
            print(f"[{i}/{len(todo)}] {e}", file=sys.stderr)
            continue
        append_rows(h, rows, s, y)
        mark_progress(h, s, str(y), len(rows))
        total_rows += len(rows)
        if i % 50 == 0 or i == len(todo):
            print(f"[{i}/{len(todo)}] {h} {SIDO.get(s, s)} {y} → 누적 {total_rows}행", flush=True)
        time.sleep(SLEEP_SEC)

    print(f"완료. 이번 실행 {total_rows}행 저장 → {OUT_DIR}")


if __name__ == "__main__":
    main()
