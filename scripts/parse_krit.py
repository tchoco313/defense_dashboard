"""KRIT 무기체계 부품국산화개발 지원사업 공고 첨부(hwpx · pdf · hwp)에서 과제 목록 표를 추출한다.

형식별 읽기:
  hwpx  zip 안 Contents/section*.xml 의 <hp:tbl>. 표준 라이브러리만.
  pdf   pdfplumber 로 쪽 단위 표 검출(find_tables). 셀 텍스트는 단어의 시작 x·세로 중심으로
        셀에 배정해 읽는다 — extract_tables() 는 병합으로 오판한 셀(24-1차 `구분` 열)을 비우고,
        셀 경계를 넘어 그려진 과제명(23-4차)의 넘친 글자를 옆 열에 붙이기 때문.
  hwp   HWP 5.0 OLE 바이너리. olefile 로 BodyText/Section* 을 읽어 zlib(-15) 해제 후
        레코드(tag 10bit · level 10bit · size 12bit)를 순회, HWPTAG_TABLE(77) 아래
        LIST_HEADER(72, 셀 col/row/span) + PARA_TEXT(67, UTF-16LE) 로 셀을 채운다.
        암호화(FileHeader flag bit1)·배포용(bit2) 문서는 지원하지 않는다.

어느 표가 과제표인지는 자동 판별이 안 되므로 파일별 SPEC 에 적어 둔다(docs/data-sources.md
"원본 확보 기록 — KRIT" 표의 확인 결과를 코드화한 것). SPEC 에 있는 파일은 기본으로 그 표만
저장하고, 표 제목에 있던 사업 구분(핵심부품/수출연계/전략부품)을 마지막 열 `구분(표제목)` 으로
붙인다. 사람 이름·전화번호가 든 열(헤더에 `담당자`)은 CSV 에 쓰지 않는다(개인정보 —
docs/reference/data-cleaning-rules.md §1-7).

사용법 (저장소 루트에서):
  python scripts/parse_krit.py resource/krit/26-2차_공고문.hwp               # 표 목록·크기 출력
  python scripts/parse_krit.py resource/krit/26-2차_공고문.hwp --table 8     # 8번째 표를 화면에 출력
  python scripts/parse_krit.py resource/krit/*.pdf resource/krit/*.hwp --out data/raw/krit
                                                                            # SPEC 표만 CSV 저장
  python scripts/parse_krit.py x.pdf --out tmp --all                        # SPEC 무시, 모든 표 저장

저장 파일명: hwpx·hwp 는 <원문 stem>_t<문서 내 표 번호>.csv, pdf 는 <원문 stem>_p<쪽>_t<쪽 내 표 번호>.csv.
scripts/load_db.py frame_krit 이 stem 앞 토큰에서 차수, 파일명 토큰에서 공고 유형, `_t<N>` 에서 표 번호를 읽는다.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

# 윈도우 콘솔(cp949)에서도 한글 출력이 깨지지 않게
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"

# 파일별 과제표 위치. key = 파일명, tables = [(page, table_no, program_type)] — page 는 pdf 만(1부터),
# table_no 는 pdf 는 쪽 내 번호, hwp/hwpx 는 문서 내 번호(둘 다 1부터). program_type 은 표 위 제목.
# 건수 근거: docs/data-sources.md "원본 확보 기록 — KRIT 부품국산화 공고 첨부" (2026-09-14 PyMuPDF 확인)
SPEC: dict[str, list[tuple[int | None, int, str | None]]] = {
    # 방사청 공고 제2023-126호. 3쪽 핵심 16 + 4쪽 수출연계 2
    "23-4차_주관기업모집_공고문.pdf": [(3, 2, "핵심부품"), (4, 1, "수출연계")],
    # 방사청 공고 제2024-26호 RFP 사전공개. 2쪽 한 표에 핵심 10 + 수출연계 1 — 구분은 표 안 `구분` 열
    "24-1차_과제_예비공고.pdf": [(2, 4, None)],
    # 방사청 공고 제2025-51호(수정). 4쪽 핵심 18 + 5쪽 전략 4. 1쪽 수정사항표(2·14·15·16번)는 본문과 대조해 로그만
    "25-1차_연구개발기관모집_수정공고문.pdf": [(4, 2, "핵심부품"), (5, 1, "전략부품")],
    # 방사청 공고 제2025-107호(재공고). 3쪽 핵심 2 + 전략 1
    "25-1차_연구개발기관모집_재공고문.pdf": [(3, 2, "핵심부품"), (3, 3, "전략부품")],
    # 26-2차 예비 RFP. 3쪽 핵심 13 + 전략 7
    "26-2차_예비RFP.pdf": [(3, 2, "핵심부품"), (3, 3, "전략부품")],
    # 26-2차 본공고(hwp 5.0). 문서 내 표 8 = "1. 핵심부품국산화" 13, 표 9 = "2. 전략부품국산화" 7
    "26-2차_연구개발기관모집_공고문.hwp": [(None, 8, "핵심부품"), (None, 9, "전략부품")],
}
PERSONAL_HEADER_TOKENS = ("담당자",)   # 이 토큰이 든 헤더 열은 저장하지 않는다
PROGRAM_COL = "구분(표제목)"


# ---------------------------------------------------------------------------
# hwpx
# ---------------------------------------------------------------------------
def cell_text(tc: ET.Element) -> str:
    # 셀 안의 문단(hp:p)별 텍스트를 줄바꿈으로 잇고, 문단 안 hp:t 조각은 그대로 붙인다.
    paras = []
    for p in tc.iter(f"{HP}p"):
        t = "".join((x.text or "") for x in p.iter(f"{HP}t"))
        if t.strip():
            paras.append(t.strip())
    return "\n".join(paras)


def extract_tables_hwpx(path: Path) -> list[pd.DataFrame]:
    tables = []
    with zipfile.ZipFile(path) as z:
        sections = sorted(n for n in z.namelist() if n.startswith("Contents/section") and n.endswith(".xml"))
        if not sections:
            raise RuntimeError(f"{path.name}: Contents/section*.xml 없음 — hwpx 가 아니거나 구조가 다름")
        for name in sections:
            root = ET.fromstring(z.read(name))
            for tbl in root.iter(f"{HP}tbl"):
                rows = []
                for tr in tbl.findall(f"{HP}tr"):
                    cells = []
                    for tc in tr.findall(f"{HP}tc"):
                        txt = cell_text(tc)
                        # 병합 셀(colSpan)은 같은 값을 반복해 열 수를 맞춘다
                        cs = tc.find(f"{HP}cellSpan")
                        span = int(cs.get("colSpan", "1")) if cs is not None else 1
                        cells.extend([txt] * span)
                    rows.append(cells)
                if not rows:
                    continue
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                tables.append(pd.DataFrame(rows))
    return tables


# ---------------------------------------------------------------------------
# hwp 5.0 (OLE 바이너리)
# ---------------------------------------------------------------------------
TAG_PARA_TEXT, TAG_LIST_HEADER, TAG_TABLE = 67, 72, 77
# 제어문자(코드 0~31) 중 인라인·확장 제어는 8 문자(16바이트)를 차지한다. 나머지는 1 문자.
_CTRL_8 = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}


def _hwp_records(data: bytes):
    pos = 0
    while pos + 4 <= len(data):
        hdr = struct.unpack("<I", data[pos:pos + 4])[0]
        pos += 4
        tag, level, size = hdr & 0x3FF, (hdr >> 10) & 0x3FF, (hdr >> 20) & 0xFFF
        if size == 0xFFF:
            size = struct.unpack("<I", data[pos:pos + 4])[0]
            pos += 4
        yield tag, level, data[pos:pos + size]
        pos += size


def _hwp_para_text(b: bytes) -> str:
    out, i, n = [], 0, len(b) // 2
    while i < n:
        c = struct.unpack("<H", b[2 * i:2 * i + 2])[0]
        if c < 32:
            if c in (10, 13):
                out.append("\n")
            i += 8 if c in _CTRL_8 else 1
            continue
        out.append(chr(c))
        i += 1
    return "".join(out)


def extract_tables_hwp(path: Path) -> list[pd.DataFrame]:
    import olefile  # 설치: pip install olefile (docs/install-log/INSTALLED.md)

    ole = olefile.OleFileIO(str(path))
    hdr = ole.openstream("FileHeader").read()
    if not hdr.startswith(b"HWP Document File"):
        raise RuntimeError(f"{path.name}: HWP 5.0 FileHeader 아님")
    flags = struct.unpack("<I", hdr[36:40])[0]
    if flags & 0b110:
        raise RuntimeError(f"{path.name}: 암호화/배포용 문서(flags={flags:#x})는 지원하지 않음")
    compressed = bool(flags & 1)
    names = sorted((n for n in ole.listdir() if n[0] == "BodyText"), key=lambda n: int(n[1][7:]))
    tables = []
    for n in names:
        data = ole.openstream(n).read()
        if compressed:
            data = zlib.decompress(data, -15)
        recs = list(_hwp_records(data))
        for i, (tag, level, b) in enumerate(recs):
            if tag != TAG_TABLE:
                continue
            nrows, ncols = struct.unpack("<HH", b[4:8])
            grid = [[""] * ncols for _ in range(nrows)]
            spans: list[tuple[int, int, int, int]] = []
            cell = None
            j = i + 1
            # 셀 LIST_HEADER 는 표와 같은 level, 셀 문단 텍스트는 level+1. 셀 안 중첩 표는 level+2 이하라 제외.
            while j < len(recs) and recs[j][1] >= level:
                t, l, bb = recs[j]
                if t == TAG_LIST_HEADER and l == level:
                    # 문단 수(2) 속성(4) 예약(2) 뒤에 col·row·colspan·rowspan UINT16 (실측 오프셋 8)
                    col, row, cs, rs = struct.unpack("<HHHH", bb[8:16])
                    cell = (row, col)
                    spans.append((row, col, cs, rs))
                elif t == TAG_PARA_TEXT and cell is not None and l == level + 1:
                    r, c = cell
                    if r < nrows and c < ncols:
                        txt = _hwp_para_text(bb).strip()
                        if txt:
                            grid[r][c] = (grid[r][c] + "\n" + txt).strip("\n")
                j += 1
            # 병합 셀은 hwpx 와 같이 같은 값을 반복해 채운다(rowSpan 포함)
            for r, c, cs, rs in spans:
                for rr in range(r, min(r + rs, nrows)):
                    for cc in range(c, min(c + cs, ncols)):
                        if (rr, cc) != (r, c):
                            grid[rr][cc] = grid[r][c]
            tables.append(pd.DataFrame(grid))
    return tables


# ---------------------------------------------------------------------------
# pdf
# ---------------------------------------------------------------------------
def _cell_text_pdf(words, bbox) -> str:
    """셀 bbox 에 속하는 단어를 줄 단위로 잇는다. 단어의 소속은 **시작 x 와 세로 중심**으로 정한다 —
    23-4차처럼 과제명이 셀 경계를 넘어 그려진 PDF 에서 글자 중심 기준(extract_tables·crop)은
    넘친 글자("판용")를 옆 열에 붙인다. 단어 단위면 넘친 단어도 시작한 셀에 남는다."""
    x0, top, x1, bottom = bbox
    hit = [w for w in words if x0 <= w["x0"] < x1 and top <= (w["top"] + w["bottom"]) / 2 < bottom]
    if not hit:
        return ""
    lines: list[list[dict]] = []
    for w in sorted(hit, key=lambda w: (round(w["top"]), w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) < 3:
            lines[-1].append(w)
        else:
            lines.append([w])
    return "\n".join(" ".join(w["text"] for w in sorted(ln, key=lambda w: w["x0"])) for ln in lines).strip()


def _pdf_table_frame(page, table) -> pd.DataFrame:
    """pdfplumber Table → 셀별 텍스트. 병합으로 판정돼 bbox 가 None 인 셀은 같은 열의 x 범위와
    같은 행의 y 범위로 bbox 를 복원해 읽는다(24-1차 `구분` 열: 행마다 글자가 있는데 None 으로 옴)."""
    rows = [list(r.cells) for r in table.rows]
    ncols = max(len(r) for r in rows) if rows else 0
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    col_x = {}
    for r in rows:
        for c, bbox in enumerate(r):
            if bbox is not None and c not in col_x:
                col_x[c] = (bbox[0], bbox[2])
    out = []
    for r in rows:
        ys = [(b[1], b[3]) for b in r if b is not None]
        row_y = (min(y for y, _ in ys), max(y for _, y in ys)) if ys else None
        cells = []
        for c in range(ncols):
            bbox = r[c] if c < len(r) else None
            if bbox is None and c in col_x and row_y:
                bbox = (col_x[c][0], row_y[0], col_x[c][1], row_y[1])
            cells.append(_cell_text_pdf(words, bbox) if bbox else "")
        out.append(cells)
    return pd.DataFrame(out)


def extract_tables_pdf(path: Path, pages: list[int] | None = None) -> list[tuple[int, int, pd.DataFrame]]:
    """[(page_no, table_no_in_page, df)]. pages 를 주면 그 쪽만."""
    import pdfplumber

    out = []
    with pdfplumber.open(str(path)) as pdf:
        targets = pages or range(1, len(pdf.pages) + 1)
        for p in targets:
            page = pdf.pages[p - 1]
            for k, tbl in enumerate(page.find_tables(), 1):
                out.append((p, k, _pdf_table_frame(page, tbl)))
    return out


# ---------------------------------------------------------------------------
# 공통
# ---------------------------------------------------------------------------
def tidy(df: pd.DataFrame) -> pd.DataFrame:
    """첫 행을 헤더로. 헤더는 줄바꿈을 보존(기존 hwpx 출력과 동일), 본문 셀은 줄바꿈 → 공백."""
    header = [str(c).strip() for c in df.iloc[0].tolist()]
    body = df.iloc[1:].map(lambda v: " ".join(str(v).split()))
    body.columns = header
    return body.reset_index(drop=True)


def drop_personal(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    dropped = [c for c in df.columns if any(tok in c for tok in PERSONAL_HEADER_TOKENS)]
    return df.drop(columns=dropped), dropped


def check_revision_25_1(path: Path, frames: dict[tuple[int, int], pd.DataFrame]) -> None:
    """25-1차 수정공고문 1쪽 수정사항표(당초→수정)와 본문 4·5쪽 표를 대조해 로그만 남긴다."""
    rev = extract_tables_pdf(path, pages=[1])
    rev_df = next((df for p, k, df in rev if 10 <= df.shape[1] <= 20 and df.shape[0] >= 3), None)
    if rev_df is None:
        print("  수정사항표(1쪽) 검출 실패 — 대조 생략")
        return
    body = pd.concat([tidy(frames[(4, 2)]), tidy(frames[(5, 1)])], ignore_index=True)
    name_col = next(c for c in body.columns if "과제명" in c)
    print("  25-1차 수정사항표 대조(순번 → 본문 과제명 / 수정 후 과제명):")
    for _, r in rev_df.iloc[2:].iterrows():
        vals = [" ".join(str(v).split()) for v in r.tolist()]
        seq = next((v for v in vals[1:4] if v.isdigit()), None)
        if not seq:
            continue
        after = vals[10] if len(vals) > 10 else ""
        hit = body[body.iloc[:, 0].astype(str).str.strip() == seq]
        got = hit[name_col].iloc[0] if len(hit) else "(본문에 없음)"
        flag = "일치" if after and after.replace(" ", "") == got.replace(" ", "") else "확인 필요"
        print(f"    {seq}: {got} / {after or '(수정 후 값 없음)'} → {flag}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--table", type=int, help="지정한 번호(1부터)의 표를 화면에 출력(hwp/hwpx: 문서 내, pdf: --page 안)")
    ap.add_argument("--page", type=int, help="pdf 에서 볼 쪽(1부터). 생략하면 SPEC 쪽 또는 전체")
    ap.add_argument("--out", type=Path, help="표를 이 디렉터리에 CSV 로 저장")
    ap.add_argument("--all", action="store_true", help="SPEC 무시하고 모든 표 저장(원문 헤더 그대로, 첫 행 포함)")
    args = ap.parse_args()

    for path in args.files:
        if not path.exists():
            print(f"없음: {path}", file=sys.stderr)
            continue
        suffix = path.suffix.lower()
        spec = None if args.all else SPEC.get(path.name)
        print(f"\n== {path.name}")
        try:
            if suffix == ".pdf":
                pages = [args.page] if args.page else (sorted({p for p, _, _ in spec}) if spec else None)
                found = extract_tables_pdf(path, pages)
                keyed = {(p, k): df for p, k, df in found}
                for (p, k), df in keyed.items():
                    head = " | ".join(str(c)[:12].replace("\n", "/") for c in df.iloc[0].tolist()[:6])
                    print(f"  [p{p} t{k}] {df.shape[0]}행 × {df.shape[1]}열  첫 행: {head}")
                if args.table and args.page:
                    show(keyed[(args.page, args.table)])
                targets = [((p, k), df) for (p, k), df in keyed.items()] if spec is None else \
                          [((p, k), keyed[(p, k)]) for p, k, _ in spec]
                if spec and "25-1차" in path.name and "수정" in path.name:
                    check_revision_25_1(path, keyed)
                name_of = lambda key: f"{path.stem}_p{key[0]}_t{key[1]}.csv"
            else:
                tables = extract_tables_hwp(path) if suffix == ".hwp" else extract_tables_hwpx(path)
                print(f"  표 {len(tables)}개")
                for i, df in enumerate(tables, 1):
                    if spec is None or any(i == t for _, t, _ in spec):
                        head = " | ".join(str(c)[:12].replace("\n", "/") for c in df.iloc[0].tolist()[:6])
                        print(f"  [{i}] {df.shape[0]}행 × {df.shape[1]}열  첫 행: {head}")
                if args.table:
                    show(tables[args.table - 1])
                targets = [((None, i), df) for i, df in enumerate(tables, 1)] if spec is None else \
                          [((None, t), tables[t - 1]) for _, t, _ in spec]
                name_of = lambda key: f"{path.stem}_t{key[1]}.csv"
        except Exception as e:  # 한 파일 실패가 나머지를 막지 않게 — 실패 파일은 "미추출"로 보고
            print(f"  !! 미추출: {type(e).__name__}: {e}", file=sys.stderr)
            continue

        if not args.out:
            continue
        args.out.mkdir(parents=True, exist_ok=True)
        prog = {(p, t): g for p, t, g in spec} if spec else {}
        for key, df in targets:
            dest = args.out / name_of(key)
            if spec is None:
                df.to_csv(dest, index=False, header=False, encoding="utf-8-sig")
                continue
            body = tidy(df)
            body, dropped = drop_personal(body)
            if prog.get(key):
                body[PROGRAM_COL] = prog[key]
            body.to_csv(dest, index=False, encoding="utf-8-sig")
            note = f" (제거 열: {', '.join(dropped)})" if dropped else ""
            print(f"  → {dest.name}: {len(body)}행 × {body.shape[1]}열{note}")


def show(df: pd.DataFrame) -> None:
    with pd.option_context("display.max_columns", None, "display.width", 200, "display.max_colwidth", 30):
        print(df)


if __name__ == "__main__":
    main()
