# -*- coding: utf-8 -*-
"""관세청 무역통계 API 가 실제로 되는지 확인한다.

    python3 src/check_trade_api.py

★ 2026-09-13 밤에 확인한 것 (조장)
   - 개발단계 자동승인. 신청 직후 호출됐다
   - 일일 한도 10,000 회
   - HS6 하나 × 국가 하나 × 1년 =  48 행
     (6자리로 물으면 10자리 하위 코드 4종이 온다 × 12개월)
   - 21 HS × 20국 × 11년이면 약 22만 행  →  2종 × 1만 건 요건 충족
   - 2025 미국발 수입 (8542.31 하나): $1,642,423,761

★ 수집할 때 조심할 것
   - 첫 항목이 year="총계" 인 합계 행이다. 빼지 않으면 이중 집계된다
   - year 는 연도가 아니라 연월이다 ("2025.01")
   - 국가명 statCdCntnKor1 · 품명 statKor · 수입액 impDlr(달러)
   - 조회 기간은 1년 이내. 연도별로 나눠 호출해야 한다
"""
import xml.etree.ElementTree as ET

import requests

from config import DATA_GO_KR_KEY

URL = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"


def main():
    r = requests.get(URL, timeout=30, params={
        "serviceKey": DATA_GO_KR_KEY,
        "strtYymm": "202501", "endYymm": "202512",   # 1년 이내만 된다
        "cntyCd": "US",                              # 국가는 필수. 하나씩
        "hsSgn": "854231",                           # 프로세서·컨트롤러
    })
    print("status:", r.status_code)

    root = ET.fromstring(r.text)
    msg = root.findtext(".//resultMsg")
    print("resultMsg:", msg)
    if root.findtext(".//resultCode") != "00":
        print("→ 키나 파라미터를 확인하라")
        return

    rows = [{c.tag: c.text for c in it} for it in root.findall(".//item")]
    real = [x for x in rows if x.get("year") != "총계"]     # 합계 행 제외
    print("항목 %d개 (합계행 제외 %d행)" % (len(rows), len(real)))
    print("HS 코드:", sorted({x["hsCd"] for x in real}))
    print("수입액 합계: $%s" % f'{sum(int(x["impDlr"]) for x in real):,}')


if __name__ == "__main__":
    main()
