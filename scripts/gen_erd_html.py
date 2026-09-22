"""docs/db/erd.md 의 Mermaid 5개를 담은 독립 정적 페이지 docs/db/erd.html 을 만든다.

실행: .venv/Scripts/python.exe scripts/gen_erd_html.py
- 브라우저에서 파일을 직접 열거나(더블클릭) GitHub Pages 로 서빙하면 렌더된다(mermaid 는 cdnjs 에서 로드).
- GitHub 저장소 화면에서는 erd.md 가 바로 그려지므로, 이 파일은 로컬 열람·Pages 용이다.
- erd.md 의 절 제목·설명은 md 가 기준이고, 여기서는 그 아래 mermaid 블록만 가져온다.
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "docs" / "db" / "erd.md"
OUT = ROOT / "docs" / "db" / "erd.html"
MERMAID_JS = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.12.2/mermaid.min.js"

md = MD.read_text(encoding="utf-8")
# "## n. 제목" 절마다 (제목, 설명 문단, mermaid) 를 뽑는다. §6 갱신 절은 mermaid 가 없어 제외된다.
sections = []
for m in re.finditer(r"^## \d+\. (.+?)\n(.*?)(?=^## |\Z)", md, re.S | re.M):
    title, body = m.group(1).strip(), m.group(2)
    mer = re.search(r"```mermaid\n(.*?)```", body, re.S)
    if not mer:
        continue
    note = re.sub(r"```mermaid\n.*?```", "", body, flags=re.S).strip()
    note = re.sub(r"`([^`]+)`", r"<code>\1</code>", note)
    sections.append((title, note, mer.group(1)))
assert len(sections) == 5, len(sections)

head_note = re.search(r"^# .+?\n\n(.+?)\n\n\*\*범례\*\*(.+?)\n", md, re.S)
lede = re.sub(r"`([^`]+)`", r"<code>\1</code>", head_note.group(1).strip())
legend = re.sub(r"`([^`]+)`", r"<code>\1</code>", head_note.group(2).strip(" —"))

parts = []
for title, note, mer in sections:
    parts.append(
        f"<section>\n<h2>{title}</h2>\n<p class=\"note\">{note}</p>\n"
        f"<div class=\"diagram\"><pre class=\"mermaid\">{mer}</pre></div>\n</section>"
    )

html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>국방 대시보드 ERD</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{ --paper:#F4F5F2; --surface:#FBFBF9; --ink:#1B2530; --muted:#5C6B7A; --line:#D5DAD9; --fk:#2E5C8A; --chip:#E8ECEA;
  --sans:"IBM Plex Sans KR","Noto Sans KR","Malgun Gothic",system-ui,sans-serif; --mono:"IBM Plex Mono",Consolas,monospace; }}
@media (prefers-color-scheme: dark){{ :root{{ --paper:#151A1F; --surface:#1C232B; --ink:#E6E9EC; --muted:#9AA6B2; --line:#2B333B; --fk:#7FA9D6; --chip:#242C35; }} }}
body{{ margin:0; background:var(--paper); color:var(--ink); font-family:var(--sans); font-size:15px; line-height:1.55; padding-inline:16px; padding-block:28px 56px; }}
.wrap{{ max-width:1180px; margin:0 auto; display:grid; gap:36px; }}
h1{{ font-size:26px; font-weight:600; margin:0 0 10px; }}
.lede,.legend,.note{{ margin:0; color:var(--muted); max-width:80ch; }}
.legend{{ margin-top:8px; font-size:13px; }}
h2{{ font-size:19px; font-weight:600; margin:0 0 8px; }}
.note{{ font-size:14px; margin-bottom:10px; }}
code{{ font-family:var(--mono); font-size:0.92em; color:var(--ink); }}
.diagram{{ background:var(--surface); border:1px solid var(--line); border-radius:8px; overflow-x:auto; padding:12px 8px; }}
.diagram pre.mermaid{{ margin:0; }}
footer{{ color:var(--muted); font-size:13px; border-top:1px solid var(--line); padding-top:14px; }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>국방 핵심 전자부품 대시보드 — 테이블 관계도</h1>
  <p class="lede">{lede}</p>
  <p class="legend"><b>범례</b> — {legend}</p>
</header>
{chr(10).join(parts)}
<footer>원본: <code>docs/db/erd.md</code>(GitHub에서 바로 렌더) · 이 파일은 <code>scripts/gen_erd_html.py</code>가 생성. PK·FK는 <code>db/schema.sql</code>, 연결률은 <code>db/query_erd_link_rates.sql</code>로 재실측.</footer>
</div>
<script src="{MERMAID_JS}"></script>
<script>
  mermaid.initialize({{ startOnLoad: true, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "neutral", er: {{ useMaxWidth: false }} }});
</script>
</body>
</html>
"""
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)} ({len(html):,} chars, {len(sections)} diagrams)")
