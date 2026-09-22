"""resource/drive/ 아래 PDF·DOCX·XLSX 파일의 텍스트를 docs/drive-text/*.txt 로 추출한다.

구글 드라이브에서 받은 안내 자료를 Claude/사람이 바로 읽을 수 있게 평문으로 바꾸는 용도.
추가 설치 없이 표준 라이브러리 + PyMuPDF(pymupdf)만 사용한다.
저장소 루트에서 실행: python scripts/extract_drive_docs.py
"""

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

SRC = Path("resource/drive")
DEST = Path("docs/drive-text")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# 엑셀 시트는 앞부분만 기록한다 (명세서 헤더·컬럼 정의 파악 목적)
XLSX_MAX_ROWS = 40


def extract_pdf(path: Path) -> str:
    import pymupdf

    doc = pymupdf.open(path)
    parts = [f"# {path.name} ({len(doc)} pages)"]
    for i, page in enumerate(doc, 1):
        parts.append(f"\n--- page {i} ---\n{page.get_text().strip()}")
    return "\n".join(parts)


def extract_docx(path: Path) -> str:
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    lines = [f"# {path.name}"]
    for p in root.iter(W + "p"):
        text = "".join(t.text or "" for t in p.iter(W + "t")).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def extract_xlsx(path: Path) -> str:
    z = zipfile.ZipFile(path)
    names = z.namelist()
    shared = []
    if "xl/sharedStrings.xml" in names:
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(S + "si"):
            shared.append("".join(t.text or "" for t in si.iter(S + "t")))
    rels = {
        r.get("Id"): r.get("Target")
        for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    }
    out = [f"# {path.name}"]
    for sheet in ET.fromstring(z.read("xl/workbook.xml")).iter(S + "sheet"):
        target = rels[sheet.get(R + "id")]
        sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        root = ET.fromstring(z.read(sheet_path))
        rows = list(root.iter(S + "row"))
        out.append(f"\n## 시트: {sheet.get('name')} (rows={len(rows)}, 앞 {XLSX_MAX_ROWS}행만)")
        for row in rows[:XLSX_MAX_ROWS]:
            cells = []
            for c in row.iter(S + "c"):
                v = c.find(S + "v")
                if v is not None:
                    val = shared[int(v.text)] if c.get("t") == "s" else v.text
                elif c.find(S + "is") is not None:
                    val = "".join(t.text or "" for t in c.find(S + "is").iter(S + "t"))
                else:
                    val = ""
                if val:
                    cells.append(f"{c.get('r')}={val.strip()}")
            if cells:
                out.append(" | ".join(cells))
    return "\n".join(out)


def extract_zip_listing(path: Path) -> str:
    lines = [f"# {path.name} (파일 목록)"]
    for n in zipfile.ZipFile(path).namelist():
        try:
            n = n.encode("cp437").decode("cp949")  # 한글 파일명(윈도우 zip) 복원
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        lines.append(n)
    return "\n".join(lines)


HANDLERS = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".xlsx": extract_xlsx,
    ".zip": extract_zip_listing,
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    DEST.mkdir(parents=True, exist_ok=True)
    for src in sorted(SRC.iterdir()):
        handler = HANDLERS.get(src.suffix.lower())
        if handler is None:
            print(f"건너뜀 (지원 안 함): {src.name}")
            continue
        text = handler(src)
        dest = DEST / (src.stem + ".txt")
        dest.write_text(text, encoding="utf-8")
        print(f"{src.name} -> {dest} ({len(text):,}자)")


if __name__ == "__main__":
    main()
