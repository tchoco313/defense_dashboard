"""관세청 품목별 국가별 수출입실적 (data.go.kr 15100475) 수집.

엔드포인트: https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList
제약: 조회기간 1년 이내 / 호출당. 개발계정 10,000회/일.
국가 파라미터(cntyCd)는 생략 가능하며 생략하면 해당 HS·연도의 **전체 국가**(2025년 기준 최대 192개)가 한 응답에 온다
(2026-09-14 확인). 따라서 전체 국가 수집은 (HS6 × 연도) 조합마다 1회 → 21개 × 11년 = 231회로 끝난다(화이트리스트 24개로 늘린 852910·901410·901490 은 progress_all.csv 에 없어 재실행 시 33회만 더 호출).
국가를 지정하는 모드는 특정 국가만 빠르게 볼 때 쓴다.

사용법 (저장소 루트에서):
  python scripts/fetch_customs.py --sample                 # US × 854231 × 2025 → 12행 확인
  python scripts/fetch_customs.py --all-countries          # 전체 국가 수집 (2016~2026, 화이트리스트) → customs_all_<HS>.csv
  python scripts/fetch_customs.py                          # 국가 지정 수집 (기본 국가 20개) → customs_<HS>.csv
  python scripts/fetch_customs.py --years 2024 2025 --countries US CN JP
  python scripts/fetch_customs.py --hs 854231 852610

키: .env 의 DATA_GO_KR_SERVICE_KEY (활용신청 후 마이페이지에서 확인).
출력: data/raw/customs/customs_<HS>.csv (국가 지정) 또는 customs_all_<HS>.csv (전체 국가, req_cnty="ALL")
      + progress.csv / progress_all.csv (완료 조합, 재실행 시 건너뜀). 두 모드의 파일은 섞이지 않는다.
응답 구조: 한 행 = HS10 세부코드 × 국가 × 월. 호출당 연간 총계행 1개(year='총계', statCd·hsCd='-')가 섞여 오며
is_total=1 로 표시한다. 거래가 없는 월은 행이 없다.
"""

import argparse
import csv
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

import requests
from dotenv import load_dotenv
import os

# 윈도우 콘솔(cp949)에서도 한글 출력이 깨지지 않게
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "data" / "reference" / "hs_whitelist.csv"
OUT_DIR = ROOT / "data" / "raw" / "customs"

# 전체 국가 모드(--all-countries)에서 req_cnty 에 기록하는 값. 실제 요청에는 cntyCd 를 보내지 않는다.
ALL = "ALL"


def progress_path(all_countries: bool) -> Path:
    return OUT_DIR / ("progress_all.csv" if all_countries else "progress.csv")


def out_path(hs: str, all_countries: bool) -> Path:
    return OUT_DIR / (f"customs_all_{hs}.csv" if all_countries else f"customs_{hs}.csv")

ENDPOINT = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"

# 관세청 국가코드(ISO2). 상위 수입국 후보 — 실제 점유율 확인 후 조정.
DEFAULT_COUNTRIES = [
    "US", "CN", "JP", "TW", "DE", "MY", "SG", "HK", "VN", "PH",
    "TH", "NL", "GB", "FR", "IL", "CH", "IT", "MX", "IN", "ID",
]

# 응답 item 의 필드 (data.go.kr 명세 그대로)
FIELDS = [
    "year", "statCd", "statCdCntnKor1", "hsCd", "statKor",
    "expWgt", "expDlr", "impWgt", "impDlr", "balPayments",
]
# 저장 컬럼: 응답 필드 + 호출 조건 기록
COLUMNS = FIELDS + ["req_hs", "req_cnty", "req_year", "fetched_at"]

SLEEP_SEC = 0.15
RETRY = 3


def load_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
    if not key:
        sys.exit("DATA_GO_KR_SERVICE_KEY 가 .env 에 없습니다. data.go.kr 에서 15100475 활용신청 후 키를 넣어주세요.")
    # 포털이 주는 키는 URL 인코딩된 형태(%2B, %3D …)일 때가 많다. requests 가 다시 인코딩하므로 원문으로 되돌린다.
    return unquote(key) if "%" in key else key


def load_whitelist() -> list[str]:
    with open(WHITELIST, encoding="utf-8") as f:
        return [row["hs_code"] for row in csv.DictReader(f)]


def load_progress(progress: Path) -> set[tuple[str, str, str]]:
    if not progress.exists():
        return set()
    with open(progress, encoding="utf-8") as f:
        return {(r["hs"], r["cnty"], r["year"]) for r in csv.DictReader(f)}


def mark_progress(progress: Path, hs: str, cnty: str, year: str, n_rows: int) -> None:
    new = not progress.exists()
    with open(progress, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["hs", "cnty", "year", "rows", "fetched_at"])
        w.writerow([hs, cnty, year, n_rows, date.today().isoformat()])


def call(key: str, hs: str, cnty: str, year: int) -> list[dict]:
    params = {
        "serviceKey": key,
        "strtYymm": f"{year}01",
        "endYymm": f"{year}12",
        "hsSgn": hs,
    }
    if cnty != ALL:
        params["cntyCd"] = cnty  # 생략하면 전체 국가
    last_err = None
    for attempt in range(1, RETRY + 1):
        try:
            r = requests.get(ENDPOINT, params=params, timeout=90)  # 전체 국가 응답은 최대 수백 KB
            r.raise_for_status()
            return parse(r.text)
        except (requests.RequestException, ET.ParseError, RuntimeError) as e:
            last_err = e
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"{hs}/{cnty}/{year} 실패: {last_err}")


def parse(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    code = (root.findtext(".//resultCode") or "").strip()
    msg = (root.findtext(".//resultMsg") or "").strip()
    # 정상: "00". 데이터 없음도 정상 응답(item 0건)으로 온다.
    if code and code != "00":
        raise RuntimeError(f"resultCode={code} {msg}")
    rows = []
    for item in root.iter("item"):
        row = {f: (item.findtext(f) or "").strip() for f in FIELDS}
        # 월별 행 외에 '총계' 행이 섞여 온다. year 가 'YYYY.MM' 형식이 아니면 집계행.
        row["is_total"] = "1" if not row["year"].replace(".", "").isdigit() else "0"
        rows.append(row)
    return rows


def append_rows(hs: str, rows: list[dict], cnty: str, year: int) -> None:
    path = out_path(hs, cnty == ALL)
    new = not path.exists()
    cols = COLUMNS + ["is_total"]
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        for row in rows:
            row.update(req_hs=hs, req_cnty=cnty, req_year=year, fetched_at=date.today().isoformat())
            w.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", action="store_true", help="US × 854231 × 2025 한 번만 호출해 화면에 출력 (저장 안 함)")
    ap.add_argument("--hs", nargs="*", help="HS6 코드 목록 (기본: data/reference/hs_whitelist.csv)")
    ap.add_argument("--countries", nargs="*", default=DEFAULT_COUNTRIES, help="국가코드(ISO2) 목록")
    ap.add_argument("--years", nargs="*", type=int, default=list(range(2016, date.today().year + 1)))
    ap.add_argument("--all-countries", action="store_true",
                    help="cntyCd 를 생략해 HS×연도당 1회로 전체 국가를 받는다 (--countries 무시, customs_all_<HS>.csv 로 저장)")
    args = ap.parse_args()

    key = load_key()

    if args.sample:
        rows = call(key, "854231", "US", 2025)
        print(f"{len(rows)}행 수신 (총계행 포함)")
        for r in rows:
            print(r)
        return

    hs_list = args.hs or load_whitelist()
    countries = [ALL] if args.all_countries else args.countries
    progress = progress_path(args.all_countries)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = load_progress(progress)

    todo = [(h, c, y) for h in hs_list for c in countries for y in args.years if (h, c, str(y)) not in done]
    print(f"호출 예정 {len(todo)}건 (완료 {len(done)}건 건너뜀)")

    total_rows = 0
    for i, (h, c, y) in enumerate(todo, 1):
        try:
            rows = call(key, h, c, y)
        except RuntimeError as e:
            print(f"[{i}/{len(todo)}] {e}", file=sys.stderr)
            continue
        append_rows(h, rows, c, y)
        mark_progress(progress, h, c, str(y), len(rows))
        total_rows += len(rows)
        if i % 50 == 0 or i == len(todo):
            print(f"[{i}/{len(todo)}] {h} {c} {y} → 누적 {total_rows}행")
        time.sleep(SLEEP_SEC)

    print(f"완료. 이번 실행 {total_rows}행 저장 → {OUT_DIR}")


if __name__ == "__main__":
    main()
