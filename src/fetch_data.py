"""국방 조달 파일데이터 내려받기 (data.go.kr 파일데이터, 인증키·로그인 불필요)

2026-09-11 확인. 아래 건수는 전부 실제로 내려받아 csv 로 센 값이다 (추정 아님).

왜 이 경로인가
  - 방위사업청 오픈API(1690000/*)는 최근 1~2개월만 굴러가서 어느 것도 2천 건을 못 넘는다.
  - 조달청 나라장터 API 는 쓸 수 있지만 활용신청이 필요하고, 국방 건만 걸러내려면
    호출을 수백 번 해야 한다. 파일데이터는 클릭 한 번 분량으로 같은 걸 준다.

주의
  - 인코딩은 cp949 다. pandas 에서 encoding='cp949' 를 반드시 줘라.
  - data.go.kr 이 Referer 헤더를 본다. 아래 download() 의 헤더를 지우면 실패한다.

    python3 fetch_defense_procurement.py          # data_raw/defense_procurement/ 에 저장
"""
import csv
import io
import os
import re
import ssl
import sys
import urllib.request

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "data_raw", "defense_procurement")

# publicDataPk -> (파일이름, 2026-09-11 에 실제로 센 행 수)
DATASETS = {
    "15050916": ("dapa_국내조달_경쟁_입찰공고.csv", 10842),
    "15050920": ("dapa_국내조달_계약정보.csv",      43112),
    "15050929": ("dapa_시설공사_계약정보.csv",      49409),
    "15050919": ("dapa_국내조달_조달계획.csv",      35859),
    "15104349": ("dapa_국내조달_공사계획.csv",      19395),
    "15119858": ("dapa_국방전자조달_사전의향서.csv", 18753),
    "15119973": ("dapa_CS_지정품명집.csv",          38159),
    "15050917": ("dapa_국내조달_경쟁_입찰결과.csv",  7405),
    "15050918": ("dapa_국내조달_공개수의_입찰결과.csv", 4875),
    "15119907": ("dapa_군급분류집_FSC.csv",           756),
    # 국외조달 — 2026-09-13 추가. 컬럼이 14개뿐이고 계약금액·재고번호가 없다.
    #   국내조달과 공통 컬럼 14개로만 비교할 수 있다 (계약방법·형태·연도·담당부서).
    "15050924": ("dapa_국외조달_계약정보.csv",       6333),
    "15050922": ("dapa_국외조달_입찰공고.csv",        340),
}

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _get(url, referer=None, timeout=300):
    headers = {"User-Agent": "Mozilla/5.0"}
    if referer:
        headers["Referer"] = referer          # 이거 없으면 data.go.kr 이 거부한다
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        return r.read()


def download(pk):
    """publicDataPk 로 파일데이터 원본 bytes 를 가져온다."""
    page_url = "https://www.data.go.kr/data/%s/fileData.do" % pk
    page = _get(page_url).decode("utf-8", "replace")
    m = re.search(r"atchFileId=([A-Za-z0-9_]+)", page)
    if not m:
        raise RuntimeError("%s: 페이지에서 atchFileId 를 못 찾았다" % pk)
    dl = ("https://www.data.go.kr/cmm/cmm/fileDownload.do"
          "?atchFileId=%s&fileDetailSn=1" % m.group(1))
    return _get(dl, referer=page_url)


def count_rows(raw):
    """cp949 CSV 의 데이터 행 수. CSV 가 아니면 None."""
    if raw[:4] == b"\x89PNG":       # 일부 데이터셋은 이 링크가 미리보기 PNG 다
        return None
    for enc in ("cp949", "utf-8-sig", "euc-kr"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return None
    try:
        return len(list(csv.reader(io.StringIO(text)))) - 1
    except csv.Error:
        return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    for pk, (name, expected) in DATASETS.items():
        try:
            raw = download(pk)
        except Exception as exc:
            print("%-34s 실패: %s: %s" % (name, type(exc).__name__, exc))
            continue
        n = count_rows(raw)
        path = os.path.join(OUT_DIR, name)
        with open(path, "wb") as fh:
            fh.write(raw)
        if n is None:
            print("%-34s CSV 가 아니다 (%d bytes) — 브라우저로 받아라" % (name, len(raw)))
            continue
        total += n
        flag = "" if n == expected else "  <- 9/11 기준 %d 행에서 바뀜" % expected
        print("%-34s %8d 행%s" % (name, n, flag))
    print("-" * 60)
    print("합계 %d 행" % total)
    print("저장 위치: %s" % OUT_DIR)


if __name__ == "__main__":
    sys.exit(main())
