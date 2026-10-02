"""제출 문서(Markdown)를 A4 PDF로 만든다 — Markdown → HTML(인쇄용 CSS) → 헤드리스 Chrome 인쇄.

만드는 문서(원본 md → docs/제출/ 의 PDF):
  01  docs/제출/01_화면설계서.md        → docs/제출/01_화면설계서.pdf
  02  docs/제출/02_시스템아키텍처.md    → docs/제출/02_시스템아키텍처.pdf
  03  docs/db/erd.md                    → docs/제출/03_DB설계서_ERD.pdf
  04  docs/db/table-catalog.md          → docs/제출/04_DB설계서_테이블정의서.pdf

처리:
  - 표지(팀 · 과제명 · 문서명 · 문서 일자)와 목차(## 제목)를 붙이고, md 의 첫 # 제목은 표지가 대신한다.
  - ```mermaid 블록은 mermaid.js(cdnjs)가 인쇄 전에 SVG 로 그린다. 그림 경로는 md 파일 위치 기준이다.
  - 중간 HTML 은 --build-dir(기본: 시스템 임시 폴더 아래 docs_build)에 쓰고 저장소에는 남기지 않는다.

필요한 것: Python 패키지 `markdown`(pip install markdown), Google Chrome, 인터넷(글꼴 · mermaid.js).

사용(저장소 루트에서):
  python scripts/build_docs_pdf.py                 # 네 문서 모두
  python scripts/build_docs_pdf.py --only 01 03    # 고른 문서만
  python scripts/build_docs_pdf.py --html-only     # HTML 만 만들고 PDF 는 건너뛴다(미리 보기)
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "제출"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TEAM = "훈수안이조"
PROJECT = "주요 방산 전자부품 수출입 및 국산화 현황 대시보드"
DOC_DATE = "2026-10-02"
PRETENDARD = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
MERMAID_JS = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.12.2/mermaid.min.js"

# 키 → (원본 md, PDF 이름, 표지 문서명, 목차 깊이(""면 목차 없음 — md 에 목차가 있는 문서), 문서별 추가 CSS)
DOCS = {
    "01": (OUT_DIR / "01_화면설계서.md", "01_화면설계서.pdf", "화면설계서", "2-3",
           "h3[id^=\"p-\"]{break-before:page} h2 + p + h3[id^=\"p-\"]{break-before:auto}"),
    "02": (OUT_DIR / "02_시스템아키텍처.md", "02_시스템아키텍처.pdf", "시스템 아키텍처", "2-2",
           "h2{break-before:auto;margin-top:26px} h2:has(+ p > img){break-before:page} figure{break-inside:avoid;margin:10px 0 14px}"),
    "03": (ROOT / "docs" / "db" / "erd.md", "03_DB설계서_ERD.pdf", "DB 설계서 — ERD(테이블 관계도)", "2-2",
           ".mermaid{font-size:12px}"),
    "04": (ROOT / "docs" / "db" / "table-catalog.md", "04_DB설계서_테이블정의서.pdf", "DB 설계서 — 테이블 정의서", "",
           "body{font-size:9.4pt} table{font-size:8.2pt} h3{font-size:11pt;margin-top:16px}"),
}

CSS = """
@import url('%(font)s');
@page { size: A4; margin: 16mm 15mm 17mm 15mm;
  @bottom-center { content: counter(page) " / " counter(pages); font-size: 8.5pt; color: #6b7a99; }
  @bottom-left { content: "%(team)s · %(doc)s"; font-size: 8.5pt; color: #6b7a99; } }
@page :first { @bottom-center { content: none; } @bottom-left { content: none; } }
:root { --ink:#16233f; --muted:#5b6b88; --line:#c9d3e3; --head:#eef3fb; --accent:#1d4ed8; --navy:#003899; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; color: var(--ink); background: #fff; font-size: 10.2pt; line-height: 1.62;
  font-family: Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif; word-break: keep-all; }
.cover { height: 255mm; display: flex; flex-direction: column; justify-content: center; padding: 0 6mm;
  border-left: 7px solid var(--navy); }
.cover .team { font-size: 13pt; font-weight: 700; color: var(--accent); letter-spacing: .5px; }
.cover .proj { font-size: 15pt; font-weight: 700; margin-top: 10mm; color: var(--muted); }
.cover .doc { font-size: 30pt; font-weight: 800; letter-spacing: -1px; margin-top: 3mm; color: var(--navy); }
.cover .meta { margin-top: 18mm; font-size: 10.5pt; color: var(--muted); }
.cover .lede { margin-top: 8mm; font-size: 10pt; color: var(--muted); max-width: 150mm; }
.toc-page { break-before: page; }
.toc-page h2 { border: 0; break-before: auto; }
.toc-page ul { list-style: none; padding-left: 0; margin: 0; }
.toc-page ul ul { padding-left: 16px; }
.toc-page li { padding: 3px 0; border-bottom: 1px dotted var(--line); }
.toc-page a { color: var(--ink); text-decoration: none; }
h1 { font-size: 20pt; color: var(--navy); margin: 0 0 8px; }
h2 { font-size: 15pt; color: var(--navy); break-before: page; border-bottom: 2px solid var(--navy);
  padding-bottom: 4px; margin: 0 0 12px; }
.content > h2:first-child { break-before: auto; }
h3 { font-size: 12pt; color: var(--ink); margin: 18px 0 8px; break-after: avoid; }
h4 { font-size: 10.5pt; margin: 14px 0 6px; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
a { color: var(--accent); }
code { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: .86em; background: #f1f4f9;
  padding: 1px 4px; border-radius: 3px; word-break: break-all; }
pre { background: #f5f7fb; border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px;
  font-size: 8.4pt; line-height: 1.45; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; word-break: normal; }
table { width: 99.7%%; border-collapse: collapse; margin: 8px 0 14px; font-size: 9pt; }
th, td { border: 1px solid var(--line); padding: 5px 7px; vertical-align: top; text-align: left; overflow-wrap: anywhere; }
th { background: var(--head); font-weight: 700; }
td:first-child, th:first-child { white-space: nowrap; }
tr { break-inside: avoid; }
blockquote { margin: 10px 0; padding: 8px 12px; border-left: 4px solid var(--accent); background: #f5f8fe; color: #33415c; }
img { display: block; max-width: 100%%; max-height: 236mm; width: auto; height: auto; margin: 8px auto 4px;
  border: 1px solid var(--line); object-fit: contain; }
img.diagram, img[src$=".svg"] { border: 0; max-height: none; }
.caption, figcaption { text-align: center; font-size: 8.6pt; color: var(--muted); margin-bottom: 12px; }
.mermaid { break-inside: avoid; text-align: center; background: #fff; border: 0; }
.mermaid svg { max-width: 100%%; height: auto; }
hr { border: 0; border-top: 1px solid var(--line); margin: 14px 0; }
%(extra)s
"""

MERMAID_INIT = """<script src="%s"></script>
<script>mermaid.initialize({startOnLoad: true, theme: "neutral", securityLevel: "loose",
  er: {useMaxWidth: true}, flowchart: {useMaxWidth: true},
  themeVariables: {fontFamily: "Pretendard, Apple SD Gothic Neo, sans-serif"}});</script>"""


def to_html(md_path: Path, doc_name: str, toc_depth: str, extra_css: str) -> str:
    """md 한 편 → 표지 · 목차가 붙은 인쇄용 HTML 문자열."""
    text = md_path.read_text(encoding="utf-8")
    text = re.sub(r"\A# .*\n+", "", text, count=1)          # 첫 # 제목은 표지가 대신한다
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "attr_list", "md_in_html", "sane_lists"],
                           extension_configs={"toc": {"toc_depth": toc_depth or "2-2"}})
    body = md.convert(text)
    has_mermaid = "language-mermaid" in body
    # fenced_code 가 만든 <pre><code class="language-mermaid"> → mermaid.js 가 그리는 <pre class="mermaid">
    body = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>',
                  r'<pre class="mermaid">\1</pre>', body, flags=re.S)
    toc = md.toc
    # 첫 ## 앞의 머리 문단은 표지 아래로 옮긴다(본문 첫 장이 한 줄짜리 쪽이 되지 않게)
    cut = body.find("<h2")
    lede, body = (body[:cut], body[cut:]) if cut > 0 else ("", body)
    cover = (f'<section class="cover"><div class="team">{TEAM}</div><div class="proj">{PROJECT}</div>'
             f'<div class="doc">{html.escape(doc_name)}</div>'
             f'<div class="meta">문서 일자 {DOC_DATE}</div>'
             f'<div class="lede">{lede}</div></section>')
    toc_html = f'<section class="toc-page"><h2>목차</h2>{toc}</section>' if toc_depth and "<li>" in toc else ""
    css = CSS % {"font": PRETENDARD, "team": TEAM, "doc": doc_name.replace('"', ""), "extra": extra_css}
    base = md_path.parent.resolve().as_uri() + "/"
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><base href="{base}">'
            f"<title>{TEAM} · {html.escape(doc_name)}</title><style>{css}</style></head><body>"
            f'{cover}{toc_html}<main class="content" style="break-before:page">{body}</main>'
            f"{MERMAID_INIT % MERMAID_JS if has_mermaid else ''}</body></html>")


def print_pdf(html_path: Path, pdf_path: Path) -> None:
    """헤드리스 Chrome 으로 인쇄한다. virtual-time-budget 동안 글꼴 · 그림 · mermaid 가 그려진다."""
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=30000", f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", choices=sorted(DOCS), help="만들 문서 키(기본: 전부)")
    ap.add_argument("--build-dir", type=Path, default=Path(tempfile.gettempdir()) / "docs_build",
                    help="중간 HTML 을 쓸 폴더(저장소 밖)")
    ap.add_argument("--html-only", action="store_true", help="HTML 만 만든다")
    a = ap.parse_args()
    a.build_dir.mkdir(parents=True, exist_ok=True)
    for key in a.only or sorted(DOCS):
        src, pdf_name, doc_name, depth, extra = DOCS[key]
        html_path = a.build_dir / f"{key}.html"
        html_path.write_text(to_html(src, doc_name, depth, extra), encoding="utf-8")
        if a.html_only:
            print(f"[HTML] {html_path}")
            continue
        out = OUT_DIR / pdf_name
        print_pdf(html_path, out)
        print(f"[PDF] {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
