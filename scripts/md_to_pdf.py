"""저장소의 Markdown 문서를 A4 PDF로 변환한다 (reportlab, 나눔고딕 임베드).

지원 문법: `#`/`##`/`###` 제목, 문단, 파이프 표, `-` 목록, `1.` 목록, ``` 코드 블록,
인라인 `code`·**굵게**·~~취소선~~. Mermaid `erDiagram` 블록은 관계 목록 표로 바꿔 넣는다.
첫 번째 `#` 제목이 표지 제목, `##`/`###`이 목차·PDF 북마크가 된다.

사용법 (저장소 루트에서):
  python scripts/md_to_pdf.py docs/db/schema-design.md                     # 같은 폴더에 schema-design.pdf
  python scripts/md_to_pdf.py docs/db/schema-design.md -o out/schema.pdf
  python scripts/md_to_pdf.py docs/idea-review.md --subtitle "기획 확정본" --no-toc

생성된 PDF는 파생 파일이라 git에 넣지 않는다(.gitignore `docs/**/*.pdf`). md 수정 후 다시 뽑는다.
"""

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

PROJECT_NAME = "국방 핵심 전자부품 수출입 현황 대시보드"
FONT_DIR = Path("C:/Windows/Fonts")
FONT_FILES = {"NG": "NanumGothic.ttf", "NG-B": "NanumGothicBold.ttf", "NG-L": "NanumGothicLight.ttf"}

ACCENT = colors.HexColor("#1f3a5f")
CODE_BG = colors.HexColor("#f1f3f5")
CODE_FG = colors.HexColor("#8a1c3b")
GRID = colors.HexColor("#c9ced4")
HEAD_BG = colors.HexColor("#e6ecf3")
ZEBRA = colors.HexColor("#f8f9fb")


def register_fonts():
    for name, file in FONT_FILES.items():
        path = FONT_DIR / file
        if not path.exists():
            sys.exit(f"폰트 없음: {path} (나눔고딕 설치 필요)")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily("NG", normal="NG", bold="NG-B", italic="NG", boldItalic="NG-B")


S = {
    "title": ParagraphStyle("title", fontName="NG-B", fontSize=22, leading=28, textColor=ACCENT, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName="NG", fontSize=11, leading=16, textColor=colors.HexColor("#555")),
    "h1": ParagraphStyle("h1", fontName="NG-B", fontSize=15, leading=20, textColor=ACCENT, spaceBefore=16, spaceAfter=6, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="NG-B", fontSize=12, leading=16, textColor=ACCENT, spaceBefore=12, spaceAfter=4, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="NG-B", fontSize=10, leading=14, textColor=ACCENT, spaceBefore=8, spaceAfter=3, keepWithNext=1),
    "body": ParagraphStyle("body", fontName="NG", fontSize=9.2, leading=14, spaceAfter=5),
    "cell": ParagraphStyle("cell", fontName="NG", fontSize=7.6, leading=10.4),
    "cellh": ParagraphStyle("cellh", fontName="NG-B", fontSize=7.8, leading=10.6, textColor=ACCENT),
    "code": ParagraphStyle("code", fontName="NG", fontSize=7.8, leading=11, backColor=CODE_BG,
                           borderPadding=(6, 8, 6, 8), spaceBefore=4, spaceAfter=10),
    "note": ParagraphStyle("note", fontName="NG-L", fontSize=8.4, leading=12, textColor=colors.HexColor("#555")),
    "tochead": ParagraphStyle("tochead", fontName="NG-B", fontSize=15, leading=20, textColor=ACCENT, spaceBefore=16, spaceAfter=6),
    "toc1": ParagraphStyle("toc1", fontName="NG-B", fontSize=10, leading=15),
    "toc2": ParagraphStyle("toc2", fontName="NG", fontSize=9, leading=13, leftIndent=14),
}
S["li"] = ParagraphStyle("li", parent=S["body"], spaceAfter=2)
S["quote"] = ParagraphStyle("quote", parent=S["body"], leftIndent=10, textColor=colors.HexColor("#444"),
                            borderPadding=(2, 6, 2, 6), backColor=ZEBRA)


# ---------- 인라인 마크다운 → reportlab 마크업 ----------
def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(t: str) -> str:
    codes = []

    def keep(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    t = re.sub(r"`([^`]+)`", keep, t)
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"~~(.+?)~~", r"<strike>\1</strike>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#1f5fa0">\1</link>', t)
    t = t.replace("²", "<super>2</super>")

    def restore(m):
        c = esc(codes[int(m.group(1))]).replace("²", "<super>2</super>")
        return f'<font color="#{CODE_FG.hexval()[2:]}" backColor="#{CODE_BG.hexval()[2:]}">{c}</font>'

    return re.sub(r"\x00(\d+)\x00", restore, t)


# ---------- 블록 파서 ----------
def split_row(line: str):
    line = line.strip().strip("|")
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


def is_sep(line: str) -> bool:
    return bool(re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?", line.strip()))


def parse(md: str):
    lines = md.splitlines()
    blocks, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            lang, buf, j = ln[3:].strip(), [], i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            blocks.append(("code", lang, buf))
            i = j + 1
            continue
        if re.match(r"^#{1,6} ", ln):
            level = len(ln) - len(ln.lstrip("#"))
            blocks.append(("h", level, ln[level:].strip()))
            i += 1
            continue
        if ln.strip().startswith("|") and i + 1 < len(lines) and is_sep(lines[i + 1]):
            header, rows, j = split_row(ln), [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            blocks.append(("table", header, rows))
            i = j
            continue
        if ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> "))
                i += 1
            blocks.append(("quote", " ".join(buf)))
            continue
        if re.match(r"^\s*[-*] ", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*] ", lines[i]):
                items.append(re.sub(r"^\s*[-*] ", "", lines[i]))
                i += 1
            blocks.append(("ul", items))
            continue
        if re.match(r"^\s*\d+\. ", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\. ", lines[i]):
                items.append(re.sub(r"^\s*\d+\. ", "", lines[i]))
                i += 1
            blocks.append(("ol", items))
            continue
        if ln.strip() == "" or re.fullmatch(r"\s*-{3,}\s*", ln):
            i += 1
            continue
        buf = [ln]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "```", ">")) \
                and not re.match(r"^\s*([-*]|\d+\.) ", lines[i]):
            buf.append(lines[i])
            i += 1
        blocks.append(("p", " ".join(buf)))
    return blocks


# ---------- 플로어블 ----------
def make_table(header, rows, avail_w):
    ncol = len(header)
    rows = [(r + [""] * ncol)[:ncol] for r in rows]

    def longest_token_w(txt):
        plain = re.sub(r"[`*~]", "", txt)
        toks = re.split(r"[\s/·,]+", plain)
        return max((pdfmetrics.stringWidth(t, "NG", S["cell"].fontSize) for t in toks if t), default=0) + 10

    # 최소 폭: 열에서 가장 긴 단어(식별자)가 잘리지 않게. 상한은 폭의 42%
    cap = 0.42 * avail_w
    mins = [min(cap, max(20 * mm, max([longest_token_w(header[c])] + [longest_token_w(r[c]) for r in rows])))
            for c in range(ncol)]
    # 긴 식별자 열이 많아 최소 폭 합이 쪽 폭을 넘으면 비례 축소한다(표가 오른쪽으로 넘치는 것보다 긴 단어를 줄바꿈하는 편이 낫다)
    if sum(mins) > avail_w:
        k = avail_w / sum(mins)
        mins = [m_ * k for m_ in mins]
    lens = []
    for c in range(ncol):
        vals = [len(header[c])] + [len(r[c]) for r in rows]
        lens.append(max(8, min(0.6 * max(vals) + 0.4 * sum(vals) / len(vals), 120)) ** 0.7)
    tot = sum(lens)
    widths = [avail_w * l / tot for l in lens]
    for _ in range(5):
        deficit = sum(max(0.0, mins[k] - widths[k]) for k in range(ncol))
        if deficit <= 0.01:
            break
        widths = [max(widths[k], mins[k]) for k in range(ncol)]
        big = [k for k in range(ncol) if widths[k] > mins[k]]
        big_tot = sum(widths[k] - mins[k] for k in big) or 1
        for k in big:
            widths[k] -= deficit * (widths[k] - mins[k]) / big_tot

    data = [[Paragraph(inline(h), S["cellh"]) for h in header]]
    data += [[Paragraph(inline(c), S["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
        ("GRID", (0, 0), (-1, -1), 0.3, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ] + [("BACKGROUND", (0, k), (-1, k), ZEBRA) for k in range(2, len(data), 2)]
    t.setStyle(TableStyle(style))
    return t


def erd_table(lines, avail_w):
    """mermaid erDiagram → 관계 목록 표. 실선(--)은 FK, 점선(..)은 논리 연결."""
    card = {"||": "1", "|o": "0..1", "o|": "0..1", "o{": "0..N", "}o": "0..N", "|{": "1..N", "}|": "1..N"}
    header = ["부모(참조 대상)", "부모 측", "자식(참조하는 쪽)", "자식 측", "연결", "연결 키"]
    rows = []
    for ln in lines:
        m = re.match(r"\s*(\S+)\s+(\S\S)(--|\.\.)(\S\S)\s+(\S+)\s*:\s*\"?([^\"]+)\"?\s*$", ln)
        if m:
            a, la, link, rb, b, key = m.groups()
            rows.append([f"`{a}`", card.get(la, la), f"`{b}`", card.get(rb, rb),
                         "FK" if link == "--" else "논리(대응표)", key])
    return make_table(header, rows, avail_w) if rows else None


def code_block(lines):
    return Paragraph("<br/>".join(esc(l).replace(" ", "&nbsp;") for l in lines) or "&nbsp;", S["code"])


class Doc(SimpleDocTemplate):
    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("h1", "h2"):
            level = 0 if fl.style.name == "h1" else 1
            key = f"h{self.seq.nextf('hd')}"
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (level, fl.getPlainText(), self.page, key))
            self.canv.addOutlineEntry(fl.getPlainText(), key, level=level, closed=False)


def make_on_page(left_text, right_text):
    def on_page(canv, doc):
        canv.saveState()
        w, h = A4
        canv.setFont("NG-L", 7.5)
        canv.setFillColor(colors.HexColor("#777"))
        canv.drawString(doc.leftMargin, h - 10 * mm, left_text)
        canv.drawRightString(w - doc.rightMargin, h - 10 * mm, right_text)
        canv.setStrokeColor(GRID)
        canv.line(doc.leftMargin, h - 11.5 * mm, w - doc.rightMargin, h - 11.5 * mm)
        canv.drawCentredString(w / 2, 8 * mm, str(doc.page))
        canv.restoreState()
    return on_page


def build(src: Path, out: Path, subtitle: str | None, toc: bool, repo_root: Path):
    blocks = parse(src.read_text(encoding="utf-8"))
    rel = src.relative_to(repo_root).as_posix() if src.is_relative_to(repo_root) else src.name

    title = subtitle_date = None
    if blocks and blocks[0][0] == "h" and blocks[0][1] == 1:
        raw = blocks[0][2]
        m = re.search(r"\((\d{4}-\d{2}-\d{2})\)\s*$", raw)
        subtitle_date = m.group(1) if m else None
        title = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", raw)
        blocks = blocks[1:]
    title = title or src.stem

    doc = Doc(str(out), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
              topMargin=17 * mm, bottomMargin=15 * mm,
              title=re.sub(r"[`*]", "", title), author="Defense Dashboard 팀", subject=PROJECT_NAME)
    avail_w = A4[0] - doc.leftMargin - doc.rightMargin
    story = [Spacer(1, 30 * mm), Paragraph(inline(title), S["title"])]
    story.append(Paragraph(f"{PROJECT_NAME}" + (f" — {esc(subtitle)}" if subtitle else ""), S["subtitle"]))
    story.append(Paragraph(f"원본 <b>{esc(rel)}</b>" + (f" · 작성일 {subtitle_date}" if subtitle_date else ""), S["subtitle"]))
    story.append(Spacer(1, 10 * mm))

    # 첫 절 제목 전까지의 도입 문단은 표지에 둔다
    idx = 0
    while idx < len(blocks) and blocks[idx][0] != "h":
        if blocks[idx][0] == "p":
            story.append(Paragraph(inline(blocks[idx][1]), S["body"]))
        idx += 1
    if toc:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("목차", S["tochead"]))
        t = TableOfContents()
        t.levelStyles = [S["toc1"], S["toc2"]]
        t.dotsMinLevel = 0
        story.append(t)
    story.append(PageBreak())

    in_erd = False
    frame_h = A4[1] - doc.topMargin - doc.bottomMargin
    rest = blocks[idx:]
    for bi, b in enumerate(rest):
        kind = b[0]
        if kind == "h":
            level, text = b[1], b[2]
            style = "h1" if level <= 2 else ("h2" if level == 3 else "h3")
            # 바로 뒤에 한 쪽을 넘는 큰 표가 오면 keepWithNext(제목+표 묶음)가 빈 쪽을 만든다(reportlab KeepTogether 동작).
            # 그때는 묶지 않고 CondPageBreak 로 제목이 쪽 끝에 고아로 남는 것만 막는다.
            nxt = rest[bi + 1] if bi + 1 < len(rest) else None
            if nxt is not None and nxt[0] == "table":
                _, h_ = make_table(nxt[1], nxt[2], avail_w).wrap(avail_w, frame_h)
                if h_ > 0.7 * frame_h:
                    story.append(CondPageBreak(60 * mm))
                    st = ParagraphStyle(style + "_nk", parent=S[style], keepWithNext=0)
                    story.append(Paragraph(inline(text), st))
                    in_erd = "ERD" in text.upper()
                    continue
            story.append(Paragraph(inline(text), S[style]))
            in_erd = "ERD" in text.upper()
        elif kind == "p":
            story.append(Paragraph(inline(b[1]), S["body"]))
        elif kind == "quote":
            story.append(Paragraph(inline(b[1]), S["quote"]))
        elif kind == "code":
            lang, lines = b[1], b[2]
            erd = erd_table(lines, avail_w) if lang == "mermaid" and any("erDiagram" in l for l in lines) else None
            if erd is not None:
                story.append(Paragraph("원본 문서의 Mermaid ERD를 관계 목록으로 옮긴 것이다. 1 / 0..1 / 0..N / 1..N 은 각 측의 카디널리티.", S["note"]))
                story.append(Spacer(1, 3))
                story.append(erd)
                story.append(Spacer(1, 6))
            else:
                story.append(code_block(lines))
        elif kind == "table":
            story.append(make_table(b[1], b[2], avail_w))
            story.append(Spacer(1, 8))
        elif kind in ("ul", "ol"):
            items = [ListItem(Paragraph(inline(t), S["li"]), leftIndent=12) for t in b[1]]
            story.append(ListFlowable(items, bulletType="bullet" if kind == "ul" else "1",
                                      bulletFontName="NG", bulletFontSize=8, leftIndent=12,
                                      bulletFormat=None if kind == "ul" else "%s.",
                                      start=None if kind == "ul" else 1))
            story.append(Spacer(1, 4))

    plain_title = re.sub(r"[`*]", "", title)
    on_page = make_on_page(plain_title if PROJECT_NAME in plain_title else f"{PROJECT_NAME} — {plain_title}",
                           rel + (f" · {subtitle_date}" if subtitle_date else ""))
    if toc:
        doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)
    else:
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path, help="변환할 Markdown 파일")
    ap.add_argument("-o", "--out", type=Path, help="출력 PDF 경로(기본: 원본과 같은 폴더, 확장자만 .pdf)")
    ap.add_argument("--subtitle", help="표지 부제(기본: 없음)")
    ap.add_argument("--no-toc", action="store_true", help="목차 생략")
    args = ap.parse_args()

    src = args.src.resolve()
    if not src.exists():
        sys.exit(f"파일 없음: {src}")
    out = (args.out or src.with_suffix(".pdf")).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    register_fonts()
    build(src, out, args.subtitle, not args.no_toc, Path(__file__).resolve().parent.parent)
    print(f"written: {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
