"""NTIS 국가R&D 과제검색 OpenAPI(대국민용, data.go.kr 15077315 LINK형) 시험 호출.

.env의 NTIS_API_KEY(NTIS 사이트 발급 승인키 — data.go.kr 키와 다름)가 필요하다.
NTIS는 활용신청 때 적은 IP만 허용한다. 학원 (학원 공인 IP) / 신청 시 등록 (신청 시 등록 IP) (2026-09-22).

사용: python scripts/ntis_probe.py [검색어=국방반도체] [건수=5]
출력: 요청 URL(키 가림), HTTP 상태, 응답 앞부분, TOTALHITS, HIT별 연도·과제번호·과제명·연구기관·부처·기간, 첫 HIT 태그 목록.
오류 응답 예: <error>접근 허용 IP가 아닙니다.</error> / <error>유효한 인증키가 아닙니다.</error>
"""
import os
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import certifi  # 맥 python.org 파이썬은 시스템 CA를 못 읽어 certifi 번들 필요

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://www.ntis.go.kr/rndopen/openApi/public_project"


def load_key() -> str:
    key = os.environ.get("NTIS_API_KEY")
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("NTIS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("NTIS_API_KEY 없음 — .env에 NTIS_API_KEY=<키> 추가")
    return key


def text(el, path: str) -> str:
    x = el.find(path)
    return (x.text or "").strip() if x is not None else ""


def main() -> None:
    key = load_key()
    query = sys.argv[1] if len(sys.argv) > 1 else "국방반도체"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    params = {"apprvKey": key, "userId": "", "collection": "project", "SRWR": query,
              "searchFd": "", "addQuery": "", "searchRnkn": "",
              "startPosition": 1, "displayCnt": count}
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    print("GET", url.replace(key, "<KEY>"))
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, timeout=30, context=ctx) as r:
        body = r.read()
        print("HTTP", r.status, len(body), "bytes")
    txt = body.decode("utf-8", "replace")
    print(txt[:400].replace(key, "<KEY>"))
    try:
        root = ET.fromstring(txt)
    except ET.ParseError as e:
        sys.exit(f"XML 파싱 실패: {e}")
    if root.tag == "error":
        sys.exit(f"NTIS 오류: {root.text}")
    total = root.find(".//TOTALHITS")
    print("TOTALHITS:", total.text if total is not None else "(없음)", "| root:", root.tag)
    hits = root.findall(".//HIT")
    print("HIT", len(hits))
    for h in hits:
        print("-", text(h, "ProjectYear"), "|", text(h, "ProjectNumber"), "|",
              text(h, ".//ProjectTitle/Korean")[:60], "|", text(h, ".//ResearchAgency/Name"), "|",
              text(h, ".//Ministry/Name"), "|", text(h, ".//ProjectPeriod/Start"), "~", text(h, ".//ProjectPeriod/End"))
    if hits:
        print("\n첫 HIT 태그:", sorted({e.tag for e in hits[0].iter()}))


if __name__ == "__main__":
    main()
