"""NTIS 국가R&D 과제검색(대국민용, data.go.kr 15077315 LINK형) 수집.

`.env`의 `NTIS_API_KEY`(NTIS 발급 승인키 — data.go.kr 키와 다름)가 필요하고, **활용신청 때 등록한 IP에서만** 된다.

두 축으로 모은다.
  A. 주제축 — 국방반도체 관련 키워드 × 제목/키워드 필드 한정 검색
  B. 기관축 — `data/reference/semi_public_fab.csv` 공공 팹 14곳 × 반도체 (전체 검색 AND)

사용:
  python scripts/fetch_ntis.py --counts           # 질의별 총건수만(내려받지 않음)
  python scripts/fetch_ntis.py --out <디렉터리>    # 수집
  python scripts/fetch_ntis.py --track A --max 300

기본 출력 디렉터리는 원본 영역(훅으로 보호)이므로 `--out`으로 명시해 쓴다.
개인정보(연구책임자·참여연구원 성명, 사업자등록번호)는 수집하지 않는다.
"""

from __future__ import annotations

import argparse
import csv
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import certifi

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "raw" / "ntis"
ENDPOINT = "https://www.ntis.go.kr/rndopen/openApi/public_project"
PAGE = 100
SLEEP = 0.7
TAG_RE = re.compile(r"<[^>]+>")

# 주제축: (라벨, SRWR, searchFd) — searchFd 는 TI 제목 / KW 키워드 / '' 전체
TOPIC_QUERIES = [
    ("국방반도체_구문", '"국방반도체"', ""),
    ("국방반도체_제목", "국방반도체", "TI"),
    ("국방반도체_키워드", "국방반도체", "KW"),
    ("국방_반도체_제목", "국방 AND 반도체", "TI"),
    ("GaN_제목", "GaN", "TI"),
    ("질화갈륨_제목", "질화갈륨", "TI"),
    ("MMIC_제목", "MMIC", "TI"),
    ("화합물반도체_제목", "화합물반도체", "TI"),
    ("전력반도체_제목", "전력반도체", "TI"),
    ("내방사선_제목", "내방사선", "TI"),
    ("우주용반도체_제목", "우주용 AND 반도체", "TI"),
    ("AESA_제목", "AESA", "TI"),
    ("적외선검출기_제목", "적외선검출기", "TI"),
]

COLS = [
    "query_label", "project_number", "project_year", "title_ko", "title_en",
    "research_agency", "manage_agency", "ministry", "order_agency", "business_name",
    "big_project", "period_start", "period_end", "total_start", "total_end",
    "gov_funds", "sbusiness_funds", "total_funds",
    "keyword_ko", "science_large", "science_medium", "science_small",
    "six_technology", "apply_area_first", "apply_area_second", "apply_area_third",
    "region", "perform_agent", "development_phases", "continuous_flag",
    "policy_project", "secret_project", "man_count", "woman_count",
    "goal_full", "effect_full", "collected_at",
]


def load_key() -> str:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("NTIS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("NTIS_API_KEY 없음 — .env에 추가")


def clean(s: str | None) -> str:
    return TAG_RE.sub("", s or "").strip()


def fetch(key: str, ctx, srwr: str, fd: str, start: int, count: int) -> ET.Element:
    params = {"apprvKey": key, "userId": "", "collection": "project", "SRWR": srwr,
              "searchFd": fd, "addQuery": "", "searchRnkn": "",
              "startPosition": start, "displayCnt": count}
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60, context=ctx) as r:
        root = ET.fromstring(r.read().decode("utf-8", "replace"))
    if root.tag == "error":
        raise RuntimeError(f"NTIS 오류: {root.text}")
    return root


def total_of(root: ET.Element) -> int:
    c = root.find('.//COLCOUNT[@NAME="project"]')
    return int(c.text) if c is not None and c.text else 0


def text_at(hit: ET.Element, path: str) -> str:
    el = hit.find(path)
    return clean(el.text) if el is not None else ""


def parse_hit(hit: ET.Element, label: str, now: str) -> dict:
    # ScienceClass 는 여러 번 나오고 첫 블록이 빈 경우가 있다 → 처음으로 값이 있는 것을 쓴다
    sc = None
    for cand in hit.findall(".//ScienceClass"):
        if clean(cand.findtext("Large")):
            sc = cand
            break
    return {
        "query_label": label,
        "project_number": text_at(hit, "ProjectNumber"),
        "project_year": text_at(hit, "ProjectYear"),
        "title_ko": text_at(hit, ".//ProjectTitle/Korean"),
        "title_en": text_at(hit, ".//ProjectTitle/English"),
        "research_agency": text_at(hit, ".//ResearchAgency/Name"),
        "manage_agency": text_at(hit, ".//ManageAgency/Name"),
        "ministry": text_at(hit, ".//Ministry/Name"),
        "order_agency": text_at(hit, ".//OrderAgency/Name"),
        "business_name": text_at(hit, ".//BusinessName"),
        "big_project": text_at(hit, ".//BigprojectTitle"),
        "period_start": text_at(hit, ".//ProjectPeriod/Start"),
        "period_end": text_at(hit, ".//ProjectPeriod/End"),
        "total_start": text_at(hit, ".//ProjectPeriod/TotalStart"),
        "total_end": text_at(hit, ".//ProjectPeriod/TotalEnd"),
        "gov_funds": text_at(hit, ".//GovernmentFunds"),
        "sbusiness_funds": text_at(hit, ".//SbusinessFunds"),
        "total_funds": text_at(hit, ".//TotalFunds"),
        "keyword_ko": text_at(hit, ".//Keyword/Korean"),
        "science_large": clean(sc.findtext("Large")) if sc is not None else "",
        "science_medium": clean(sc.findtext("Medium")) if sc is not None else "",
        "science_small": clean(sc.findtext("Small")) if sc is not None else "",
        "six_technology": text_at(hit, ".//SixTechnology"),
        # 적용분야(ApplyArea) — 「국방」 값이 여기 들어온다. EconomicSocialGoal 은 비어 온다
        "apply_area_first": text_at(hit, ".//ApplyArea/First"),
        "apply_area_second": text_at(hit, ".//ApplyArea/Second"),
        "apply_area_third": text_at(hit, ".//ApplyArea/Third"),
        "region": text_at(hit, ".//Region"),
        "perform_agent": text_at(hit, ".//PerformAgent"),
        "development_phases": text_at(hit, ".//DevelopmentPhases"),
        "continuous_flag": text_at(hit, ".//ContinuousFlag"),
        "policy_project": text_at(hit, ".//PolicyProjectFlag"),
        "secret_project": text_at(hit, ".//SecretProject"),
        "man_count": text_at(hit, ".//Researchers/ManCount"),
        "woman_count": text_at(hit, ".//Researchers/WomanCount"),
        # Goal · Effect 는 Abstract 의 자식이 아니라 형제다
        "goal_full": text_at(hit, ".//Goal/Full")[:2000],
        "effect_full": text_at(hit, ".//Effect/Full")[:1000],
        "collected_at": now,
    }


def collect(key: str, ctx, label: str, srwr: str, fd: str, cap: int) -> list[dict]:
    now = datetime.now().isoformat(timespec="seconds")
    root = fetch(key, ctx, srwr, fd, 1, PAGE)
    total = total_of(root)
    take = min(total, cap)
    rows = [parse_hit(h, label, now) for h in root.findall(".//HIT")]
    pos = 1 + PAGE
    while len(rows) < take:
        time.sleep(SLEEP)
        root = fetch(key, ctx, srwr, fd, pos, PAGE)
        hits = root.findall(".//HIT")
        if not hits:
            break
        rows.extend(parse_hit(h, label, now) for h in hits)
        pos += PAGE
    rows = rows[:take]
    print(f"  {label:26s} 총 {total:>7,} → 수집 {len(rows):>5,}")
    return rows


def build_queries(track: str) -> list[tuple[str, str, str]]:
    qs: list[tuple[str, str, str]] = []
    if track in ("A", "all"):
        qs += TOPIC_QUERIES
    if track in ("B", "all"):
        fab = ROOT / "data" / "reference" / "semi_public_fab.csv"
        with fab.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = (row.get("name_ko") or "").strip()
                if name:
                    qs.append((f"팹_{name}", f'"{name}" AND 반도체', ""))
    return qs


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", choices=["A", "B", "all"], default="all")
    ap.add_argument("--counts", action="store_true", help="총건수만 세고 끝낸다")
    ap.add_argument("--max", type=int, default=500, help="질의당 최대 수집 건수")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="출력 디렉터리")
    args = ap.parse_args()

    key = load_key()
    ctx = ssl.create_default_context(cafile=certifi.where())
    queries = build_queries(args.track)

    if args.counts:
        print(f"질의 {len(queries)}개 — 총건수만")
        grand = 0
        for label, srwr, fd in queries:
            try:
                n = total_of(fetch(key, ctx, srwr, fd, 1, 1))
            except Exception as e:  # noqa: BLE001
                print(f"  {label:26s} 실패 {e}")
                continue
            grand += min(n, args.max)
            print(f"  {label:26s} {n:>7,}  (수집 예정 {min(n, args.max):,})")
            time.sleep(SLEEP)
        print(f"수집 예정 합계(중복 포함) {grand:,}행")
        return

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    print(f"질의 {len(queries)}개 수집 시작 (질의당 최대 {args.max:,}) → {out_dir}")
    for label, srwr, fd in queries:
        try:
            all_rows.extend(collect(key, ctx, label, srwr, fd, args.max))
        except Exception as e:  # noqa: BLE001
            print(f"  {label:26s} 실패 {e}")
        time.sleep(SLEEP)

    stamp = datetime.now().strftime("%Y%m%d")
    raw_path = out_dir / f"ntis_projects_raw_{stamp}.csv"
    write_csv(raw_path, all_rows)

    seen: dict[str, dict] = {}
    for r in all_rows:
        pn = r["project_number"]
        if pn and pn not in seen:
            seen[pn] = r
    uniq_path = out_dir / f"ntis_projects_unique_{stamp}.csv"
    write_csv(uniq_path, list(seen.values()))

    print(f"\n질의 결과 합계 {len(all_rows):,}행 → {raw_path}")
    print(f"과제번호 고유    {len(seen):,}행 → {uniq_path}")
    defense = sum(1 for r in seen.values()
                  if "국방" in (r["apply_area_first"] + r["apply_area_second"] + r["apply_area_third"]))
    print(f"적용분야(ApplyArea)에 「국방」 포함: {defense:,}건")


if __name__ == "__main__":
    main()
