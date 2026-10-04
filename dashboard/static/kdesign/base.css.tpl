<style>
${_FONTS}${ZOOM_CSS}
:root{
  --bg:${BG}; --panel:${PANEL}; --panel2:${PANEL2}; --line:${LINE};
  --text:${TEXT}; --muted:${MUTED}; --accent:${ACCENT}; --sky:${SKY}; --sky-weak:${SKY_WEAK}; --navy:${NAVY}; --navy2:${NAVY2};
  --up:${UP}; --down:${DOWN};
  --shadow:0 1px 2px rgba(19,42,84,.06), 0 6px 18px rgba(19,42,84,.06);
  --shadow-h:0 2px 4px rgba(19,42,84,.08), 0 14px 32px rgba(19,42,84,.12);
}
html, body, [class*="st-"]{font-family:${SIDE_STACK}}
[data-testid="stIconMaterial"]{font-family:'Material Symbols Rounded'!important}
.material-symbols-rounded{font-family:'Material Symbols Rounded';font-weight:400;font-style:normal;font-size:21.5px;line-height:1;
  letter-spacing:normal;text-transform:none;white-space:nowrap;direction:ltr;-webkit-font-smoothing:antialiased}
/* 바탕 · Streamlit 기본 머리 띠 · 사이드바 숨김 · 본문 폭은 화면 틀 CSS 에 있다 */

/* ── 한글 줄바꿈 — 단어 중간에서 끊지 않는다(「수출입 현 / 황」 「대 / 만」). 넘치는 긴 낱말만 끊는다 ── */
[data-testid="stMain"]{word-break:keep-all;overflow-wrap:break-word}

/* ── 경로 줄(hero) — 서브 배너 아래 본문 맨 위: 왼쪽 「자료 기준」 · 오른쪽 ⌂ › 페이지 ───────────── */
.st-key-hero{margin:0;padding:0}
.crumb-row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 0 4px}
.crumb{display:flex;align-items:center;gap:8px;margin-left:auto;font-size:13px;color:#6b7a99;white-space:nowrap}
.crumb .ms{font-family:'Material Symbols Rounded'!important;font-size:17px;line-height:1;color:#6b7a99;font-variation-settings:'FILL' 1}
.crumb i{font-style:normal;color:#b3bdcf;font-size:11px}
.crumb b{color:#1b2540;font-weight:700}
/* 자료 기준 — 경로 줄 왼쪽 알약 버튼, 누르면 아래로 흰 카드(출처 「?」와 같은 방식) */
details.basis{flex:0 0 auto;width:max-content;position:relative;align-self:flex-start}
details.basis > summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:6px;padding:6px 13px;
  border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--text);font-size:13.5px;font-weight:600;user-select:none;white-space:nowrap;
  box-shadow:var(--shadow)}
details.basis > summary::-webkit-details-marker{display:none}
/* 달력 아이콘 = CSS 배경 SVG(st.html 은 svg 태그를 걸러 낸다 · 이 CSS 안에 꺾쇠 태그 글자를 쓰면 블록 전체가 버려진다) — 글꼴 아이콘이 아니라 페이지를 옮길 때 「calendar_month」 글자가 번쩍이지 않는다 */
details.basis > summary .cal{display:inline-block;flex:none;width:17px;height:17px;background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232b6ef6' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='5' width='18' height='16' rx='2'/%3E%3Cpath d='M16 3v4M8 3v4M3 10h18'/%3E%3C/svg%3E") center/contain no-repeat}
details.basis > summary:hover,details.basis[open] > summary{background:#f3f6fb;border-color:#b9c7dd}
details.basis .basis-pop{position:absolute;left:0;top:calc(100% + 8px);z-index:50;min-width:300px;background:#fff;
  border:1px solid var(--line);border-radius:10px;padding:12px 16px;box-shadow:0 6px 18px rgba(15,31,58,.14);text-align:left}
.basis-pop .bt{font-size:12px;color:var(--muted);margin-bottom:6px}
.basis-pop .row{display:flex;justify-content:space-between;gap:18px;font-size:13.5px;line-height:1.75;color:var(--text);font-weight:600;white-space:nowrap}
.basis-pop .row em{font-style:normal;font-weight:400;color:var(--muted)}
.basis-pop .bl{margin-top:6px;padding-top:6px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}
[class*="st-key-hero"],[class*="st-key-hero"] *:has(> details.basis){overflow:visible}

.demo-bar{display:flex;align-items:center;gap:10px;margin:0 0 14px;padding:9px 14px;border-radius:8px;
  background:var(--sky-weak);border:1px solid #cfe5f8}
.demo-bar b{font-size:14px;font-weight:700;color:#0f2a5c}
.demo-bar span{font-size:13px;color:var(--muted);line-height:1.5}

/* ── 블록 — 한 페이지에 차례로 이어진다. 테두리 · 이름표 대신 블록마다 제목 줄(.sec-h) ─────────── */
div[class*="st-key-zone_"]{border:none;border-radius:0;background:transparent;padding:0;margin:4px 0 52px;scroll-margin-top:22px}
.sec-h{display:flex;align-items:baseline;gap:12px;margin:0 0 4px;padding-bottom:14px;border-bottom:2px solid #1b2540}
.sec-h h2{margin:0;padding:0;font-size:25px;font-weight:800;letter-spacing:-.7px;color:#101a33;line-height:1.3}

/* ── 카드 — 둥근 14px · 옅은 그림자 · 커서를 올리면 살짝 떠오른다 ─────────────────── */
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;height:100%;
  box-shadow:var(--shadow);transition:box-shadow .2s ease,transform .2s ease}
.card:hover{box-shadow:var(--shadow-h);transform:translateY(-2px)}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [class*="st-key-card_"]),
div[class*="st-key-card_"]{background:var(--panel);border:1px solid var(--line)!important;border-radius:14px;box-shadow:var(--shadow)}
/* 같은 줄 카드 높이 맞추기 — 열은 이미 줄 높이만큼 늘어나 있으므로, 열의 마지막 카드가 남은 높이를 채운다 */
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:last-child:has(> [class*="st-key-card_"]),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:last-child > [class*="st-key-card_"],
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:last-child:has(> [data-testid="stHtml"] > .card:only-child){flex:1 1 auto}
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:last-child > [data-testid="stHtml"]:has(> .card:only-child){height:100%}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0);transform-origin:left}to{transform:none}}

/* ── KPI — 위 파란 선 · 아이콘 배지 + 굵은 제목 · 가운데 큰 숫자 · 아래 설명 ───────────── */
/* 한 줄 칸 수: 5장 = 3 + 2(아래 두 장은 넓게) · 6장 = 3 × 2 · 4장 = 2 × 2(본문이 왼쪽 메뉴만큼 좁아서). 좁으면 칸 폭 기준으로 접는다 */
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:20px}
.kpis > .kpi{grid-column:span 2}
.kpis:not(.k4):not(.k6):not(.q) > .kpi:nth-child(n+4){grid-column:span 3}
.kpis.k4{grid-template-columns:repeat(2,minmax(0,1fr))} .kpis.k4 > .kpi{grid-column:auto}
.kpis.k6{grid-template-columns:repeat(3,minmax(0,1fr))} .kpis.k6 > .kpi{grid-column:auto}
[data-testid="stHtml"]:has(> .kpis){container-type:inline-size}
@container (max-width:620px){.kpis,.kpis.k4,.kpis.k6{grid-template-columns:repeat(2,minmax(0,1fr))} .kpis > .kpi,.kpis:not(.k4):not(.k6):not(.q) > .kpi:nth-child(n+4){grid-column:auto}}
@container (max-width:440px){.kpis.q{grid-template-columns:repeat(2,minmax(0,1fr))!important}}   /* 조회 결과 카드(최대 3장, 인라인 열 수) */
@container (max-width:300px){.kpis,.kpis.k4,.kpis.k6,.kpis.q{grid-template-columns:minmax(0,1fr)!important}}
.kpi{animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both}
.kpis .kpi:nth-child(2){animation-delay:.07s} .kpis .kpi:nth-child(3){animation-delay:.12s}
.kpis .kpi:nth-child(4){animation-delay:.17s} .kpis .kpi:nth-child(5){animation-delay:.22s} .kpis .kpi:nth-child(6){animation-delay:.27s}
.card.kpi{border-top:4px solid #1d4ed8;container-type:inline-size;min-width:0}
.kpis:not(.q) .kpi{min-height:172px;display:flex;flex-direction:column}
.kpi .kt{display:flex;align-items:center;gap:10px;min-height:34px}
.kpi .ico{width:34px;height:34px;flex:0 0 34px;border-radius:9px;display:grid;place-items:center;background:#e8f0ff;color:#2b6ef6;
  transition:transform .2s ease}
.kpi:hover .ico{transform:scale(1.08) rotate(-4deg)}
.kpis .kpi:nth-child(2) .ico{background:#e4fbf6;color:#0f9f85} .kpis .kpi:nth-child(3) .ico{background:#f0ecff;color:#7a5af8}
.kpis .kpi:nth-child(4) .ico{background:#fff2e3;color:#e0851a} .kpis .kpi:nth-child(5) .ico{background:#ffe9f1;color:#e0457b}
.kpis .kpi:nth-child(6) .ico{background:#eaf4ff;color:#2f8fdc}
.kpi .ico .ms{font-family:'Material Symbols Rounded'!important;font-weight:400;font-style:normal;font-size:20px;line-height:1;
  letter-spacing:0;font-feature-settings:'liga';-webkit-font-smoothing:antialiased}
.kpi .l{font-size:17px;font-weight:700;color:#12234a;letter-spacing:-.3px;line-height:1.35}
.kpi .l.long{font-size:15.5px;letter-spacing:-.5px}
.kpi .v{margin:auto 0 0;padding:14px 0 2px;text-align:center;font-size:min(36px,17cqi);font-weight:800;letter-spacing:-1.2px;color:#12234a;
  line-height:1.1;font-variant-numeric:tabular-nums;overflow-wrap:normal}
.kpi .v.long{font-size:min(28px,13cqi);letter-spacing:-.8px}
.kpi .v .vr{font-size:.85em;letter-spacing:-.5px}   /* 긴 값(「2016–2026」 같은 기간)은 한 단계 작게 */
.kpi .v small{display:inline-block;font-size:14.5px;color:var(--muted);font-weight:600;margin-left:4px;letter-spacing:0;white-space:nowrap}
.kpi .s{margin:12px 0 auto;font-size:13px;color:var(--muted);line-height:1.55}
.kpi .s .up,.kpi .s .dn{color:var(--up);font-weight:700;font-variant-numeric:tabular-nums;margin-right:3px}
.kpi .s .dn{color:var(--down)}   /* 증감 — 오르면 빨강 · 내리면 파랑 */
.ex{display:inline-block;font-size:11.5px;font-weight:700;color:#b45309;background:#fef3c7;border:1px solid #fde68a;
  border-radius:5px;padding:0 5px;margin-left:6px;vertical-align:middle;letter-spacing:0}
/* 조회 결과 작은 카드 — 높이 · 가운데 숫자 없이 */
.kpis.q{grid-template-columns:repeat(3,minmax(0,1fr))} .kpis.q > .kpi{grid-column:auto}
.kpis.q .kpi .l{font-size:15px} .kpis.q .kpi .v{text-align:left;padding:8px 0 0;margin:0;font-size:min(26px,20cqi)}
.kpis.q .kpi .s{margin:8px 0 0}

/* ── 카드 제목(왼쪽 파란 막대) — 결론 문장 · 아래 줄에 단위 · 기간(말풍선에 숨기지 않는다) ──────── */
.h{position:relative;display:block;padding-left:14px;font-size:16px;font-weight:700;margin-bottom:12px;
  color:var(--text);letter-spacing:-.3px;line-height:1.45}
.h::before{content:"";position:absolute;left:0;top:4px;width:4px;height:16px;border-radius:3px;background:#2b6ef6}
.h .sub{display:block;margin-top:3px;font-size:13px;color:var(--muted);font-weight:500;letter-spacing:0}
.h .key,.key{color:var(--accent)}
.note{font-size:13.5px;color:#5d6d8c;line-height:1.7}
.note b{color:var(--text);font-weight:700}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
.legend i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:4px;vertical-align:middle}
.caption{font-size:13px;color:#8494ae;line-height:1.7;margin-top:6px}
.lede{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;
  padding:11px 15px;box-shadow:var(--shadow);margin-bottom:4px}

/* 원칙 목록 — 초록 체크 */
.rule{display:flex;gap:10px;margin-bottom:12px}
.rule .ck{width:20px;height:20px;flex:0 0 20px;border-radius:50%;display:grid;place-items:center;font-size:12px;
  background:#dcfce7;color:#15803d;font-weight:800}
.rule b{display:block;font-size:14px;font-weight:700;color:var(--text);letter-spacing:-.2px}
.rule span{display:block;font-size:13px;color:var(--muted);margin-top:2px;line-height:1.5}

/* 순위 목록 */
.rank{display:grid;grid-template-columns:22px minmax(104px,40%) 1fr 64px;align-items:center;gap:9px;height:30px;font-size:13.5px}
.rank .no{width:20px;height:20px;border-radius:50%;background:#eef2f9;color:#5a6b8c;font-size:12px;font-weight:800;
  display:grid;place-items:center}
.rank .nm{font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rank .tr{position:relative;height:11px;border-radius:4px;background:#eef2f9}
.rank .fl{position:absolute;left:0;top:0;bottom:0;border-radius:4px;animation:grow .7s cubic-bezier(.18,.89,.32,1.1) both}
.rank .vl{text-align:right;font-weight:700;color:var(--text);font-size:13px;font-variant-numeric:tabular-nums}

/* 점유율 막대 */
.bars .row{display:grid;grid-template-columns:150px 1fr 52px;align-items:center;gap:8px;height:22px;font-size:13px}
.bars .nm{color:${TEXT};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bars .nm em{color:${MUTED};font-style:normal;font-size:12px;margin-left:3px}
.bars .track{position:relative;height:12px;border-radius:4px;background:${PANEL2}}
.bars .fill{position:absolute;left:0;top:0;bottom:0;border-radius:4px;animation:grow .7s cubic-bezier(.18,.89,.32,1.1) both}
.bars .ref{position:absolute;top:-4px;bottom:-4px;left:50%;border-left:1px dashed #94a7c8}
.bars .pct{text-align:right;color:${MUTED};font-variant-numeric:tabular-nums}

/* 국외조달 절차 — 원 → 화살표 → 원 */
.proc{display:grid;grid-template-columns:minmax(0,1fr) 30px minmax(0,1fr) 30px minmax(0,1fr);align-items:start;padding:6px 0 2px}
[data-testid="stHtml"]:has(> .proc){container-type:inline-size}
@container (max-width:440px){.proc .ci{width:62px;height:62px} .proc .ci b{font-size:15px} .proc .n{font-size:19px} .proc .ds{font-size:12.5px} .proc .ar{margin-top:20px}}
.proc .st{text-align:center;animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both}
.proc .st:nth-child(3){animation-delay:.12s} .proc .st:nth-child(5){animation-delay:.24s}
.proc .ci{width:88px;height:88px;margin:0 auto;border-radius:50%;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:3px;color:#fff;background:#2b6ef6;box-shadow:0 6px 18px rgba(43,110,246,.26)}
.proc .st:nth-child(3) .ci{background:#17a8c4} .proc .st:nth-child(5) .ci{background:#1c4ec4}
.proc .ci span{display:none}
.proc .ci b{font-size:17px;font-weight:800;letter-spacing:-.3px}
.proc .ar{margin-top:30px;text-align:center;font-size:21px;color:#8fb3f4}
.proc .ds{margin-top:12px;font-size:13.5px;color:#44567a;line-height:1.55}
.proc .n{margin-top:8px;font-size:24px;font-weight:800;color:#1c4ea3;letter-spacing:-.5px;font-variant-numeric:tabular-nums;white-space:nowrap}
.proc .n small{font-size:13.5px;color:var(--muted);font-weight:600;margin-left:3px}

/* 깔때기 */
.funnel .fr{display:grid;grid-template-columns:1.3fr 1fr;align-items:center;gap:10px;height:52px;margin-bottom:6px}
.funnel .tz{height:100%;display:grid;place-items:center;color:#fff;font-size:20px;font-weight:800;letter-spacing:-.3px;
  animation:rise .42s cubic-bezier(.18,.89,.32,1.15) both}
.funnel .lb{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;color:var(--text)}
.funnel .lb::before{content:"";flex:0 0 34px;border-top:2px dotted #b7c7e2}
.funnel .lb small{display:block;font-size:12.5px;color:var(--muted);font-weight:500;margin-top:2px}

/* ── 위젯 ─────────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div{background:#fff;border-color:var(--line);border-radius:10px}
[data-testid="stSegmentedControl"] button{border-radius:9px}
[data-testid="stButtonGroup"] > div:not([data-testid]){flex-wrap:wrap;row-gap:6px}   /* 칩(pills)이 칸보다 길면 잘리지 않고 다음 줄로 */
[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden;border:1px solid var(--line)}
[data-testid="stExpander"]{background:#fff;border:1px solid var(--line)!important;border-radius:12px;box-shadow:var(--shadow)}
.stButton button,.stDownloadButton button{border-radius:10px;font-weight:600}
</style>