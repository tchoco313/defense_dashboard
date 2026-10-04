"""화면 디자인 — 본문 부품(블록 · 카드 · KPI · 차트 · 지구본 · 도넛 · 지도 · 표). 화면 틀(머리글 · 메뉴 · 배너 · 바닥글)은 진입점 파일이 그린다.

디자인: 블록은 테두리 없이 제목 줄(.sec-h),
카드는 둥근 모서리 · 그림자 · hover, KPI 는 아이콘 배지 · 가운데 큰 숫자, 카드 제목은 왼쪽 파란 막대, 탭은 폴더형, 차트는 등장 연출.
화면 숫자는 각 페이지가 RDS 에서 읽어 인자로 넘긴다. 이 모듈은 import 만으로 그리지 않는다 — CSS 는 inject() 로 넣는다.
"""
from __future__ import annotations

import base64
import contextlib
import itertools
import re
import json
from html import escape
from pathlib import Path
from string import Template

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

LABEL_KEY = "_kd_label"        # 경로 표시(⌂ › 페이지)에 쓰는 현재 페이지 이름 — hero 가 읽는다

# ════════════════════════════════════════════════════════════════════════════
# 1. 색 토큰 · CSS
#    글씨 하한 13px 안팎(화면 확대 대신 글씨를 키운다), 카드 제목 아래 단위 · 기간 줄은 ⓘ 말풍선에 숨기지 않고 보인다(해석 경계),
#    증감은 오르면 빨강 · 내리면 파랑.
# ════════════════════════════════════════════════════════════════════════════
BG, PANEL, PANEL2, LINE = "#eef3fb", "#ffffff", "#eef2f9", "#dde5f2"   # BG = 옅은 파랑(탭 · 선택 배경 등 보조), 페이지 바탕은 흰색, 카드 = 흰색
TEXT, MUTED, ACCENT = "#16233f", "#6b7a99", "#2b6ef6"                  # ACCENT = 대표 파랑
SKY, SKY_WEAK = "#38bdf8", "#eaf1ff"                                  # 하늘(보조 강조) · 옅은 파랑(선택 배경)
NAVY, NAVY2 = "#003899", "#003899"                                    # 짙은 파랑(머리글 · 펼침 메뉴와 같은 색)
UP, DOWN = "#d92d20", "#1f5fe0"                                       # 증감 — 오르면 빨강 · 내리면 파랑. 흰 바탕 글자 대비 4.5:1 이상
# 데이터 범주색 — 파랑 · 청록 · 주황 · 보라 · 분홍 · 하늘에 연두 · 남색을 더해 8색.
# 순서는 파랑 · 주황 · 청록 먼저(페이지가 번호로 고른 색 — 군급 · 소요군 · 계열 — 의 이름이 바뀌지 않게).
# 9번째부터는 새 색을 만들지 않고 기타(ETC)로 묶는다. 청록 · 연두 · 하늘은 흰 바탕 대비가 낮아 범례 · 값 라벨 · 표와 함께 쓴다.
SERIES = ["#2b6ef6", "#ff9f43", "#17c8b5", "#7c6cf0", "#ff6b9a", "#38bdf8", "#84cc16", "#1e3a8a"]
ETC = "#c3cede"

# 외부 CDN 스크립트(d3 · topojson · world-atlas · plotly.js)는 정확한 버전 + 무결성 해시(SRI)로 고정한다 — CDN 변조 시 실행되지 않게.
# 버전을 올릴 때는 새 파일의 sha384 를 다시 계산해 integrity 를 함께 바꾼다.
# ── 글꼴 ────────────────────────────────────────────────────────────────────
SIDE_STACK = "Pretendard,'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif"
# @import 는 다른 규칙보다 반드시 앞에 와야 브라우저가 읽는다(뒤에 두면 통째로 무시된다).
_PRETENDARD = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
_FONTS = f"@import url('{_PRETENDARD}');\n"
_FONT_LINK = f'<link rel="stylesheet" href="{_PRETENDARD}">'   # iframe(지구본 · 도넛 · 지도 · PNG 단추)도 본문과 같은 글꼴로


# 화면용 HTML · CSS · JS 는 static/kdesign/ 파일에 두고 읽는다(main.py 의 static/ 과 같은 방식).
# 이름이 .tpl 로 끝나는 파일의 ${이름} 자리는 _tpl 이 파이썬 값(색 · 글꼴)으로 채운다 — 그 파일에 $ 를 쓰려면 $$.
_STATIC_DIR = Path(__file__).resolve().parent / "static"


def _static(name: str) -> str:
    return (_STATIC_DIR / name).read_text(encoding="utf-8")


def _tpl(name: str, **vals) -> str:
    return Template(_static(name)).substitute(vals)


def _js(obj) -> str:
    """iframe <script> 에 넣는 JSON — DB 문자열에 </script> 나 태그가 섞여도 스크립트 밖으로 새지 않게 < > & 를 이스케이프한다."""
    return (json.dumps(obj, ensure_ascii=False)
            .replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026"))

# 화면 배율 — 배율(예: 1.1)은 오른쪽 · 아래 빈 띠와 차트 마우스 위치 어긋남을 만들어 1(끔)로 둔다.
# 1 이 아니면 아래 ZOOM_CSS 가 차트 · 표 · 선택창의 배율을 되돌리는 보정을 함께 넣는다.
APP_ZOOM = 1.0
ZOOM_CSS = "" if APP_ZOOM == 1 else (
    f"html{{zoom:{APP_ZOOM}}}"
    f'[data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{{zoom:calc(1 / {APP_ZOOM})}}'
    f'[data-rac][data-trigger],[data-rac][role="tooltip"]{{zoom:calc(1 / {APP_ZOOM})}}'
    f'[data-rac][data-trigger] > *,[data-rac][role="tooltip"] > *{{zoom:{APP_ZOOM}}}'
    f'[data-testid="stMain"]{{height:calc(100dvh / {APP_ZOOM})!important;max-height:calc(100dvh / {APP_ZOOM})!important}}')

CSS = _tpl("kdesign/base.css.tpl", _FONTS=_FONTS, ZOOM_CSS=ZOOM_CSS, BG=BG, PANEL=PANEL, PANEL2=PANEL2, LINE=LINE, TEXT=TEXT, MUTED=MUTED, ACCENT=ACCENT, SKY=SKY, SKY_WEAK=SKY_WEAK, NAVY=NAVY, NAVY2=NAVY2, UP=UP, DOWN=DOWN, SIDE_STACK=SIDE_STACK)

# 위젯 라이트 고정 — 테마 설정 없이 OS 다크모드에서 열어도 버튼 · 선택창 · 체크박스가 같은 색으로 보이게
WIDGET_CSS = _static("kdesign/widget.css")

# 막대 · 선 그래프 등장 연출 — 막대는 왼쪽 것부터 차례로 바닥에서 자라고(가로 막대는 왼쪽에서 뻗고), 선은 왼쪽에서 오른쪽으로 그려진다.
# 차트가 새로 그려질 때(페이지 이동 · 창 크기 변경)마다 다시 재생된다
_STAGGER = "\n".join(
    f".js-plotly-plot .barlayer .point:nth-child({i}) path{{animation-delay:{0.05 + i * 0.07:.2f}s}}\n"
    f".js-plotly-plot .barlayer .point:nth-child({i}) text{{animation-delay:{0.45 + i * 0.07:.2f}s}}"
    for i in range(1, 16))
CHART_ANIM = _tpl("kdesign/chart_anim.css.tpl", _STAGGER=_STAGGER)

# ── 표 · 핵심 지표 카드 · 탭 · 조회 카드 ─────────────────────────────────────
TABLE_CSS = _static("kdesign/table.css")


# ════════════════════════════════════════════════════════════════════════════
# 2. 공용 요소
# ════════════════════════════════════════════════════════════════════════════
# KPI 아이콘 — 제목에 든 낱말로 고른다(위에서부터 먼저 맞는 것). 단색 Material Symbols 이름, 이모지는 쓰지 않는다
KPI_ICON = (("무역수지", "balance"), ("중량", "scale"), ("수의계약", "handshake"), ("입찰공고", "campaign"),
            ("유찰", "block"), ("낙찰", "apartment"), ("국내 계약", "description"), ("수입국", "flag"),
            ("수출국", "flight_takeoff"), ("수입액", "download"), ("수출액", "upload"), ("가동률", "factory"),
            ("생산지수", "bolt"), ("예산", "account_balance"), ("건수", "receipt_long"), ("적용장비", "precision_manufacturing"),
            ("과제", "task_alt"), ("나노팹", "science"), ("미국", "public"), ("반도체", "memory"), ("사업", "work"),
            ("국산화", "build"), ("조달계획", "assignment"), ("조달 계획", "assignment"), ("군급", "category"),
            ("50%", "warning"), ("기간", "calendar_month"), ("품목", "inventory_2"), ("HS6", "inventory_2"))


def kpi(label: str, value: str, unit: str, sub: str, tag: str = "", icon: str = "") -> str:
    """KPI 카드 — 아이콘 배지 + 제목 · 가운데 큰 숫자 · 단위 · 설명. icon 을 비우면 제목 낱말로 KPI_ICON 에서 고른다.
    긴 제목(공백 빼고 10자 이상) · 긴 숫자(태그 빼고 8자 이상, 예 2016–2026)는 한 단계 작게 해 한 줄에 맞춘다."""
    t = f'<span class="ex">{tag}</span>' if tag else ""
    plain = lambda x: re.sub(r"<[^>]+>", "", x)
    icon = icon or next((ic for w, ic in KPI_ICON if w in plain(label)), "")
    lc = " long" if len(plain(label).replace(" ", "")) >= 10 else ""
    vc = " long" if len(plain(value)) >= 8 else ""
    ic = f'<span class="ico"><span class="ms">{icon}</span></span>' if icon else ""
    return (f'<div class="card kpi"><div class="kt">{ic}<div class="l{lc}">{label}{t}</div></div>'
            f'<div class="v{vc}">{value}<small>{unit}</small></div><div class="s">{sub}</div></div>')


def zone(key: str, tag: str):
    """페이지 안 블록 하나 — 제목 줄 + 내용(`with zone("키", "이름"):`). 키는 왼쪽 메뉴 · 주소 ?sec= 와 같다."""
    c = st.container(key=f"zone_{key}")
    c.html(f'<div class="sec-h"><h2>{escape(tag)}</h2></div>')
    return c


def stamp_period(st_: dict) -> str:
    """data_stamp 결과 → 머리띠에 쓰는 기간 문구. 기간이 없는 목록형 자료는 「기준일 미표기」, 조회 실패는 그대로 알린다."""
    if st_.get("error") and not st_.get("has_period"):
        return "조회 실패"
    if not st_.get("has_period"):
        return "기준일 미표기"
    return str(st_["period"]).replace(" (부분)", "")


def hero(stamps: list | None = None) -> None:
    """본문 맨 위 경로 줄 — 왼쪽 「자료 기준」 버튼 · 오른쪽 ⌂ › 페이지. 페이지 제목 · 부제는 서브 배너에 있다.
    stamps = [(데이터 이름, db.data_stamp(...)), …] 를 주면 버튼을 누를 때 「이름 · 기간」 줄이 펼쳐진다(DB 반영일은 출처 「?」 · CSV 에)."""
    left = ""
    if stamps:
        # 자료 기준은 버튼 뒤에 접어 둔다 — 누르면 아래로 카드가 펼쳐진다(HTML details · 서버 재실행 없음)
        rows = "".join(f'<span class="row"><em>{escape(n)}</em>{escape(stamp_period(s_))}</span>' for n, s_ in stamps)
        left = ('<details class="basis"><summary title="자료 기간 보기">'
                '<span class="cal" aria-hidden="true"></span>자료 기준</summary>'
                f'<div class="basis-pop"><div class="bt">자료 기준</div>{rows}</div></details>')
    label = escape(st.session_state.get(LABEL_KEY, ""))
    with st.container(key="hero"):
        st.html(f'<div class="crumb-row">{left}<div class="crumb"><span class="ms">home</span><i>›</i><b>{label}</b></div></div>')


def real_bar(src: str) -> None:
    """실측 집계를 쓰는 구역 표시."""
    st.html(f'<div class="demo-bar real"><b>실측 집계</b><span>{src}</span></div>')


def hbar_key(fig, key: str) -> str | None:
    """가로 막대 차트면 그 차트를 감쌀 칸의 키(hb_… · 0 에서 양쪽으로 갈리면 hbd_…), 아니면 None.
    등장 연출(CHART_ANIM · static/chart_anim.css)이 이 키로 가로 막대를 알아보고 왼쪽에서 오른쪽으로 뻗게 한다."""
    bars = [t for t in fig.data if t.type == "bar" and t.orientation == "h"]
    if not bars:
        return None
    xs = [v for v in (bars[0].x if bars[0].x is not None else []) if v is not None]
    split = len(bars) > 1 and bool(xs) and max(xs) <= 0 and min(xs) < 0
    return f"{'hbd' if split else 'hb'}_{key}"


def style_fig(fig, height: int | None = None):
    """차트 공통 모양 — 배경 투명 · 옅은 가로 · 세로 격자 · 범례는 위 가로. 글씨는 하한 13px(_floor_fonts)."""
    grid = "#e7eefa"
    m = fig.layout.margin                   # 차트가 미리 정한 여백(예: 가로 막대의 라벨 자리)은 그대로 둔다
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=SIDE_STACK, color=TEXT, size=13.5), title_font=dict(size=15.5, color=TEXT),
                      legend=dict(font=dict(color=MUTED), bgcolor="rgba(0,0,0,0)"),
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor=LINE, font=dict(color=TEXT)),
                      margin=dict(l=8 if m.l is None else m.l, r=8 if m.r is None else m.r,
                                  t=10 if m.t is None else m.t, b=8 if m.b is None else m.b))
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED),
                     automargin=True)
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED),
                     automargin=True)
    # 눈금 글자를 「차트 밖으로 넘친다」고 숨기지 않게 한다 — Plotly 기본값(hide past div)은 글자 자리를 화면 좌표로 재는데,
    # 화면 배율(html zoom)이 걸려 있으면 그 값이 어긋나 맨 끝 눈금(예: 연도 축의 마지막 해)을 넘친 것으로 보고 지웠다
    fig.update_xaxes(ticklabeloverflow="allow")
    fig.update_yaxes(ticklabeloverflow="allow")
    # 눈금 숫자는 화면 다른 곳처럼 쉼표로(6000 → 6,000, 5k → 5,000). 연도 축(2016 …)은 쉼표를 넣지 않는다
    for axis, update in (("x", fig.update_xaxes), ("y", fig.update_yaxes)):
        years = any(_yearish(t[axis]) for t in fig.data if axis in t and t[axis] is not None)
        update(exponentformat="none", **({} if years else {"separatethousands": True}))
    if fig.layout.legend.orientation is None:
        fig.update_layout(legend=dict(orientation="h", y=1.1, x=0, title=None))
    if height:
        fig.update_layout(height=height)
    _floor_fonts(fig)
    return fig


_LABEL_POS = {   # plotly textposition → 라벨 상자 왼쪽 위(점 중심 기준, 픽셀). r = 점 반지름, w · h = 라벨 크기
    "top center": lambda r, w, h: (-w / 2, -r - 2 - h), "bottom center": lambda r, w, h: (-w / 2, r + 2),
    "middle right": lambda r, w, h: (r + 3, -h / 2), "middle left": lambda r, w, h: (-r - 3 - w, -h / 2),
    "top right": lambda r, w, h: (r * .6, -r - h), "top left": lambda r, w, h: (-r * .6 - w, -r - h),
    "bottom right": lambda r, w, h: (r * .6, r), "bottom left": lambda r, w, h: (-r * .6 - w, r),
}


def point_labels(xs, ys, texts, xr, yr, w: float = 460, h: float = 290, fs: float = 13, r: float = 7):
    """산점도 점 이름이 서로 · 다른 점과 겹치지 않게 자리(textposition)를 고른다. 세로값이 큰 점부터 놓고,
    여덟 자리 모두 막히면 그 점의 이름은 비운다(커서를 올리면 보인다). xr · yr = 그림에 줄 축 범위, w · h = 그림 칸 대략 픽셀."""
    pts = [((x - xr[0]) / (xr[1] - xr[0]) * w, (1 - (y - yr[0]) / (yr[1] - yr[0])) * h) for x, y in zip(xs, ys)]
    dots = [(cx - r, cy - r, 2 * r, 2 * r) for cx, cy in pts]
    placed: list[tuple[float, float, float, float]] = []
    over = lambda a, b: a[0] < b[0] + b[2] and a[0] + a[2] > b[0] and a[1] < b[1] + b[3] and a[1] + a[3] > b[1]
    out_t, out_p = [""] * len(pts), ["top center"] * len(pts)
    for i in sorted(range(len(pts)), key=lambda k: -ys[k]):
        t = str(texts[i])
        tw, th = sum(fs * (1.0 if ord(c) > 0x2E80 else .6) for c in t), fs * 1.3
        for pos, off in _LABEL_POS.items():
            dx, dy = off(r, tw, th)
            box = (pts[i][0] + dx, pts[i][1] + dy, tw, th)
            if box[0] < 0 or box[1] < 0 or box[0] + tw > w or box[1] + th > h:
                continue
            if any(over(box, d) for k, d in enumerate(dots) if k != i) or any(over(box, p) for p in placed):
                continue
            placed.append(box)
            out_t[i], out_p[i] = t, pos
            break
    return out_t, out_p


def _yearish(vals) -> bool:
    """축 값이 모두 연도(1900~2100 정수)인가 — 연도 눈금에는 천 단위 쉼표를 넣지 않는다."""
    try:
        xs = [float(v) for v in vals if v is not None]
    except (TypeError, ValueError):
        return False
    return bool(xs) and all(1900 <= v <= 2100 and v == int(v) for v in xs)


def _floor_fonts(fig, lo: float = 13) -> None:
    """차트 글씨 하한(작게 만들지 않는다): 눈금 · 범례 · 주석 · 값 라벨에 lo 보다 작게 정한 크기를 lo 로 올린다."""
    small = lambda f: f is not None and isinstance(f.size, (int, float)) and f.size < lo
    for ax in [*fig.select_xaxes(), *fig.select_yaxes()]:
        if small(ax.tickfont):
            ax.tickfont.size = lo
    if small(fig.layout.legend.font):
        fig.layout.legend.font.size = lo
    for a in fig.layout.annotations or ():
        if small(a.font):
            a.font.size = lo
    for tr in fig.data:
        if "textfont" in tr and small(tr.textfont):
            tr.textfont.size = lo


def chart_title(title: str, sub: str = "", where=None) -> None:
    """카드 제목 줄(왼쪽 파란 막대) — title 은 결론 문장(핵심 구절 하나만 <span class="key">…</span>), sub 는 단위 · 기간만.
    DB 에서 온 이름(품목 · 국가)은 호출하는 쪽이 escape 해서 넣는다. 표 · 뷰 이름은 여기 넣지 않고 chart_source 로."""
    (where or st).html(f'<div class="h"><span>{title}</span>' + (f'<span class="sub">{sub}</span>' if sub else "") + "</div>")


_DB_BITS = re.compile(r"\b(?:clean|fact|dim|ref|meta|raw)_[a-z0-9_]+|\bv_[a-z0-9_]+|\b[a-z][a-z0-9]*_[a-z0-9_]+\b"
                      r"|DB\s*(?:적재|반영)|팀\s*DB|AWS|RDS|DBHub|schema|스키마")


def public_source(text: str) -> str:
    """사용자에게 보이는 출처에서 DB 내부 정보(표 · 뷰 · 열 이름, 「팀 DB」, DB 적재 · 반영일)를 걸러 낸다 — 보안.
    「기관 · 데이터명 → DB 표 · 기간 · DB 적재 날짜」 → 「기관 · 데이터명 · 기간」. 화면 출처 「?」 · PNG 출처 줄 · CSV 머리줄이 모두 이 함수를 지난다."""
    parts = [p.strip(" ·,.;") for p in re.split(r"\s*(?:→|->|·)\s*", str(text))]
    keep = [p for p in parts if p and not _DB_BITS.search(p)]
    out = " · ".join(dict.fromkeys(keep))          # 같은 조각이 겹치면 한 번만
    return re.sub(r"^출처:\s*", "", out).strip() or "공개 자료"


def source_pop(text: str) -> str:
    """출처를 「?」 원 뒤에 접어 두는 HTML — 누르면 펼쳐지고 다시 누르면 접힌다(HTML details · 서버 재실행 없음).
    화면은 깔끔하게, 인용할 사람은 한 번 눌러 확인한다. 내려받는 PNG · CSV 에는 출처가 그대로 들어간다."""
    body = f"출처: {public_source(text)}"
    return (f'<details class="src"><summary title="출처 보기" aria-label="출처 보기">?</summary>'
            f'<div class="src-body">{body}</div></details>')


def chart_source(text: str, where=None) -> None:
    """차트 아래 출처 — 「?」 원을 누르면 「출처: 기관 · 데이터명 → DB 표 · 자료 기간 · 적재일」이 펼쳐진다."""
    (where or st).html(source_pop(text))


def rules_card(title: str, items: list[tuple[str, str]]) -> str:
    body = "".join(f'<div class="rule"><span class="ck">✓</span><div><b>{t}</b><span>{d}</span></div></div>'
                   for t, d in items)
    return f'<div class="card"><div class="h">{title}</div>{body}</div>'


def rank_card(title: str, sub: str, rows: list[tuple[str, float, str]], unit: str, note: str = "") -> str:
    top = max(v for _, v, _ in rows) or 1
    body = "".join(
        f'<div class="rank"><span class="no">{i}</span><span class="nm" title="{n}">{n}</span>'
        f'<span class="tr"><span class="fl" style="width:{v / top * 100:.0f}%;background:{c}"></span></span>'
        f'<span class="vl">{v:,.0f}</span></div>'
        for i, (n, v, c) in enumerate(rows, 1))
    # 제목은 한 <span> 으로 싼다 — .h 는 flex 라 글자 · 강조 구절이 따로 놓이면 사이가 벌어진다
    return (f'<div class="card"><div class="h"><span>{title}</span><span class="sub">단위: {unit}</span></div>'
            f'<div style="font-size:13px;color:{MUTED};margin-bottom:6px">{sub}</div>{body}'
            + (f'<div class="caption">{note}</div>' if note else "") + '</div>')


# ── 공급망 현황 · 공급 집중도 요소 ────────────────────────────────────────────
def hhi_level(hhi: float) -> tuple[str, str]:
    """HHI 구간 이름과 색 — 위험 예측이 아니라 집중 수준만 나눈다. 색은 파랑 명도(진할수록 집중)."""
    if hhi >= 2500:   # 한 단계만 — 2010 합병 지침 고집중 기준(근거 없는 4,000 구간은 두지 않는다)
        return "높음", "#1e3a8a"
    return "보통", "#93c5fd"


def _svg_img(svg: str, w: int, h: int, cls: str = "") -> str:
    """st.html 은 <svg> 태그를 지우므로 data URI 이미지로 싸서 넣는다."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img class="{cls}" width="{w}" height="{h}" alt="" src="data:image/svg+xml;base64,{b64}">'


_SPARK_STYLE = "<style>polyline{fill:none;stroke-width:1.6;stroke-linejoin:round}</style>"


def sparkline(vals: list[float], color: str = ACCENT, w: int = 118, h: int = 30) -> str:
    """작은 추이선(끝점 강조) — 정지 그림."""
    lo, hi = min(vals), max(vals)
    sx = (w - 6) / (len(vals) - 1)
    pts = [(2 + i * sx, h - 4 - (v - lo) / ((hi - lo) or 1) * (h - 8)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{_SPARK_STYLE}'
           f'<polygon points="2,{h} {line} {pts[-1][0]:.1f},{h}" fill="{color}" fill-opacity=".08"/>'
           f'<polyline points="{line}" stroke="{color}"/>'
           f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.6" fill="{color}"/></svg>')
    return _svg_img(svg, w, h, "spark")


LV_BG = {"높음": "#1e3a8a", "보통": "#f1f5fa"}    # 공급 집중 등급 배지 — 진할수록 집중
LV_FG = {"높음": "#ffffff", "보통": "#5b6b82"}


def supply_table(rows: list[dict]) -> str:
    """부품별 공급망 현황 표. rows 의 color(1위 공급국 국가 색)가 있으면 이름 앞 점 · 추이선에 쓴다(같은 나라 = 같은 색)."""
    head = ("<tr><th>No.</th><th>품목군</th><th>1위 공급국</th><th>최근 수입액 추이<small>(최근 12개월)</small></th>"
            "<th>수입액 변화<small>(전년 대비)</small></th><th>수입국<small>(개)</small></th>"
            "<th>집중도<small>(HHI)</small></th><th>1위 점유율</th><th>공급 집중</th></tr>")
    body = ""
    for i, f in enumerate(rows, 1):
        up = f["yoy"] >= 0
        lvl, lc = hhi_level(f["hhi"])
        body += (f'<tr><td class="no">{i}</td><td class="nm">{escape(str(f["name"]))}<em>HS {escape(str(f["hs"]))}</em></td>'
                 f'<td><span class="cdot" style="background:{f.get("color", ACCENT)}"></span>{escape(str(f["top"]))}</td>'
                 f'<td>{sparkline(f["m"], f.get("color", ACCENT))}</td>'
                 f'<td class="{"up" if up else "dn"}">{"▲" if up else "▼"} {abs(f["yoy"]):.1f}%</td>'
                 f'<td>{f["n"]}</td><td>{f["hhi"]:,}</td><td>{f["s1"]:.1f}%</td>'
                 f'<td class="lv"><span class="lvb" style="background:{LV_BG[lvl]};color:{LV_FG[lvl]}">{lvl}</span></td></tr>')
    return (f'<div class="card"><div class="h">부품별 공급망 현황 <span class="sub">품목군 {len(rows)}개 · '
            f'공급 집중 = HHI 2,500 이상 높음</span></div>'
            f'<table class="sc"><thead>{head}</thead><tbody>{body}</tbody></table>'
            f'<div class="caption">추이·변화율은 최근 12개월과 그 전 12개월의 월별 수입액 비교 · '
            f'국산화율은 이 대시보드가 다루지 않습니다.</div></div>')


def core_kpis(cards: list[tuple[str, str, str, str, str, str, str]], basis: str) -> str:
    """핵심 지표 카드 묶음(둥근 아이콘). cards = [(아이콘, "배경색,글자색", 라벨, 값, 단위, 설명, 값 style)]."""
    def icon(ic: str, col: str) -> str:
        if not ic:
            return ""
        bg, fg = (col.split(",") + ["#2b6ef6"])[:2] if col else ("#e8f0ff", "#2b6ef6")
        return f'<span class="ic" style="background:{bg};color:{fg}"><span class="ms">{ic}</span></span>'
    body = "".join(f'<div class="kc">{icon(ic, col)}<div>'
                   f'<div class="l">{l}</div><div class="v" style="{vs}">{v}<small>{u}</small></div>'
                   f'<div class="s">{s}</div></div></div>' for ic, col, l, v, u, s, vs in cards)
    return (f'<div class="card"><div class="h">핵심 지표 <span class="sub" style="margin-left:auto">기준: {basis}</span></div>'
            f'<div class="kgrid">{body}</div></div>')


def share_card(f: dict) -> str:
    sh = f["shares"]
    rest = sum(s for _, s in sh[5:])
    cmap = f.get("colors", {})
    rows = [(n, s, cmap.get(n, "#93c5fd")) for n, s in sh[:5]] + ([("기타", rest, ETC)] if rest > 0.05 else [])
    body = "".join(f'<div class="row" title="{n} {s:.1f}%"><div class="nm">{n}</div><div class="track">'
                   f'<div class="fill" style="width:{s:.1f}%;background:{c}"></div><div class="ref"></div></div>'
                   f'<div class="pct">{s:.1f}%</div></div>' for n, s, c in rows)
    return (f'<div class="card"><div class="h">공급 국가 비중 <span class="sub">{f["name"]} · HS {f["hs"]} · '
            f'점선 = 50%</span></div><div class="bars big">{body}</div>'
            f'<div class="caption">수입국 {f["n"]}개 중 상위 5개국</div></div>')


# ════════════════════════════════════════════════════════════════════════════
# 3. 공급국 지구본 · 로딩 표시
#    지구본: 회전 · 끌어 돌리기 · 지구본↔지도 · 흐름 화살표. 로딩(globe_loading)은 static/loading_globe.html 의 작은 회전 지구본.
# ════════════════════════════════════════════════════════════════════════════
KOREA = [127.8, 36.5]
_GLOBE = _static("kdesign/globe.html")




def supply_globe(points: list[dict], height: int = 430, unit: str = "백만 USD", outbound: bool = False):
    """공급국 지구본 — 회전 · 끌어서 돌리기 · 지구본↔지도 전환 · 공급국 → 한국 흐름 화살표.
    outbound=True(수출)면 선 · 화살표가 한국 → 그 나라 방향이다.
    points = [{name, lat, lon, value, color, note}] — 원 색 = 국가 색(표 · 막대와 같은 색), 원 크기 = 수입액.
    지구본은 HTML 이라 PNG 로 바로 저장할 수 없어, 같은 값의 평면 지도(plotly)를 만들어 돌려준다(화면에는 그리지 않음 — PNG 단추용)."""
    html = (_GLOBE.replace("__DATA__", _js(points))
            .replace("__KOREA__", _js(KOREA)).replace("__UNIT__", unit)
            .replace("__DIR__", "true" if outbound else "false")
            .replace("__H__", str(height - 10)).replace("__FONTLINK__", _FONT_LINK))
    components.html(html, height=height, scrolling=False)
    fig = go.Figure()
    if points:
        vmax = max(p["value"] for p in points) or 1
        fig.add_trace(go.Scattergeo(
            lat=[p["lat"] for p in points], lon=[p["lon"] for p in points], mode="markers+text",
            text=[p["name"] for p in points], textposition="top center", textfont=dict(size=12.5, color=TEXT),
            marker=dict(size=[p["value"] for p in points], sizemode="area", sizeref=2 * vmax / 46 ** 2, sizemin=5,
                        color=[p.get("color", ACCENT) for p in points], opacity=.85, line=dict(color="#ffffff", width=1.2))))
    fig.update_geos(projection_type="natural earth", showland=True, landcolor="#e8f0fa", showocean=True, oceancolor="#ffffff",
                    showcountries=True, countrycolor="#ffffff", coastlinecolor="#d3e0f0", showframe=False, bgcolor="rgba(0,0,0,0)",
                    lataxis_range=[-50, 75])
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      font=dict(family=SIDE_STACK))
    return fig


_MINI_GLOBE = (Path(__file__).resolve().parent / "static" / "loading_globe.html").read_text(encoding="utf-8")
_GLOAD_N = itertools.count()


@contextlib.contextmanager
def globe_loading(text: str = "조회 중", height: int = 0):
    """조회 · 집계가 끝날 때까지 작은 회전 지구본을 보인다. 블록을 벗어나면(오류가 나도) 자리를 비운다.
    height = 지구본 칸 높이(0 이면 340). 0.35초 안에 끝나는 조회(캐시)는 지구본이 보이지 않는다 — components.css 의
    .st-key-gload_* 규칙이 그동안 칸을 접어 두어, 화면을 다시 그릴 때마다 깜빡이지 않는다."""
    height = height or 340
    slot = st.empty()
    with slot.container(key=f"gload_{next(_GLOAD_N)}"):
        components.html(_MINI_GLOBE.replace("__H__", str(height - 10)).replace("__LABEL__", escape(text)),
                        height=height, scrolling=False)
    try:
        yield
    finally:
        slot.empty()

# ════════════════════════════════════════════════════════════════════════════
# 3-3. 도넛 공통 — 반지름·둘레·굵기와 커서 반응(조각 확대 · 가운데 라벨)
# ════════════════════════════════════════════════════════════════════════════
R = 80                       # 도넛 반지름
C = round(2 * 3.141592653589793 * R, 2)      # 둘레 = stroke-dasharray 기준
STROKE = 48                  # 도넛 두께
# 커서를 올린 조각: 굵기를 키우면서 바깥쪽으로 확대한다. 안쪽 가장자리는 그대로 두어(≈56) 가운데 글자를
# 가리지 않고, 보이는 두께는 약 2배(48 → 96)가 된다.
HOVER_STROKE = 74
HOVER_SCALE = 1.3
HOVER_OUT = round(HOVER_SCALE * (R + HOVER_STROKE / 2))     # 커진 조각의 바깥 반지름 ≈ 152

# ── 도넛 공통: 조각(또는 범례)에 커서를 올리면 그 조각이 두꺼워지고 가운데에 라벨·값·비율이 뜬다 ──
# 조각 <circle> 에 class="hv", 가운데 글자는 .c-lab / .c-sub / .c-val, 범례 항목은 .lg 로 맞춰 두면 된다.
def _hover_css(cx: float, cy: float) -> str:
    return f"""
  .hv{{transform-origin:{cx}px {cy}px}}
  .hv.on{{stroke-width:{HOVER_STROKE};transform:scale({HOVER_SCALE})}}
  .focusing .hv:not(.on){{stroke-opacity:.28}}
  .c-val{{font-size:13.5px;font-weight:600;fill:#6b7a99;text-anchor:middle}}
  .lg{{padding:2px 6px;border-radius:6px;cursor:default;transition:background .15s, opacity .15s}}
  .lg.on{{background:#eaf1ff}}
  .focusing .lg:not(.on){{opacity:.4}}
"""

_HOVER_JS = _static("kdesign/hover_donut_script.html")


def _hover_js(rows: list[tuple[str, float, str]], cx: float, cy: float, on: str, unit: str) -> str:
    """on = 도넛이 다 펼쳐졌을 때 #stage 에 붙는 클래스. 그 전에는 커서를 올려도 반응하지 않는다."""
    total = float(sum(float(v) for _, v, _ in rows))
    data = [{"l": str(l), "v": float(v), "p": float(v) / total} for l, v, _ in rows]
    return (_HOVER_JS.replace("__DATA__", _js(data))
            .replace("__CX__", str(cx)).replace("__CY__", str(cy))
            .replace("__IN__", str(R - STROKE / 2 - 4)).replace("__OUT__", str(R + STROKE / 2 + 4))
            .replace("__OUTH__", str(HOVER_OUT))
            .replace("__ON__", on).replace("__UNIT__", _js(unit)))


# ── 도넛 — 바로 펼쳐지고, 조각(또는 범례)에 커서를 올리면 3-3 의 반응을 한다 ──
def hover_donut(rows: list[tuple[str, float, str]], center: str, sub: str = "", value_unit: str = "",
                height: int = 430, fit: bool = False) -> None:
    """fit=True — 칸 높이는 그대로 두고 도넛을 키운다: 그림 판 둘레 여백을 커서를 올린 조각의 바깥(HOVER_OUT)까지만 남기고
    범례 줄 간격을 좁힌다(낮은 칸에서 도넛이 작아 보일 때 · 전자부품 현황 수입국 비중)."""
    rows = [r for r in rows if float(r[1]) > 0]
    if not rows:
        components.html("<div style='font:12px system-ui;color:#6b7a99'>표시할 값이 없습니다.</div>", height=40)
        return
    total = float(sum(float(v) for _, v, _ in rows))
    segs, legend, css, cum = [], [], [], 0.0
    for i, (label, value, color) in enumerate(rows):
        pct = float(value) / total
        length = round(C * pct, 2)
        segs.append(f'<circle id="seg{i}" class="seg hv" cx="170" cy="170" r="{R}" stroke="{color}" />')
        css.append(f".shown #seg{i}{{stroke-dasharray:{length} {C};stroke-dashoffset:{round(-cum, 2)}}}")
        cum += length
        legend.append(f'<div class="lg"><span style="background:{color}"></span>{escape(label)} '
                      f'<b>{pct * 100:.1f}%</b></div>')
    html = (_DONUT_TPL.replace("__SEGS__", "\n      ".join(segs))
            .replace("__LEGEND__", "\n    ".join(legend))
            .replace("__CSS__", "\n  ".join(css) + _hover_css(170, 170))
            .replace("__CENTER__", escape(center))
            .replace("__SUB__", escape(sub))
            .replace("__C__", str(C))
            .replace("__H__", str(height - 10)).replace("__FONTLINK__", _FONT_LINK)
            .replace("__VB__", f"{170 - HOVER_OUT - 2} {170 - HOVER_OUT - 2} {2 * (HOVER_OUT + 2)} {2 * (HOVER_OUT + 2)}" if fit else "0 0 340 340")
            .replace("__LGAP__", "2px 12px" if fit else "7px 12px")
            .replace("__HOVER__", _hover_js(rows, 170, 170, "shown", value_unit)))
    components.html(html, height=height, scrolling=False)


_DONUT_TPL = _static("kdesign/donut.html")

# ════════════════════════════════════════════════════════════════════════════
# 3-6. 국가별 수입·수출 분포 지도 · 지역(시·도)별 수입·수출 분포 지도
#      둘 다 오른쪽 위 「수입 | 수출」 단추로 바꾼다(다시 그리지 않고 브라우저 안에서 색만 바뀐다).
#      지도 모양은 CDN 에서 받는다 — 세계: world-atlas, 시·도: southkorea-maps(통계청 2013).
# ════════════════════════════════════════════════════════════════════════════
_MAP_HEAD = _static("kdesign/map_head.html")

_WORLD_MAP = _MAP_HEAD + _static("kdesign/world_map_body.html")


def country_map(imp: dict, exp: dict, modes: tuple[str, ...] = ("imp", "exp"), height: int = 400,
                unit: str = "백만 USD", top_n: int = 6, note: str = "", where: dict | None = None) -> None:
    """국가별 수입·수출 분포(단계 구분도). 색 = 합계 대비 비중 구간, 상위 top_n 개국은 이름·비중 라벨.
    modes 가 하나면 전환 단추를 숨긴다."""
    # where = 국가명 → (위도, 경도)(ref_country). 나라 면은 JS 가 좌표를 품은 면(d3.geoContains)으로 찾는다
    info = {n: [None, la, lo, 0, 0] for n, (la, lo) in (where or {}).items() if (n in imp or n in exp) and la is not None}
    html = (_WORLD_MAP.replace("__DATA__", _js({"imp": imp, "exp": exp}))
            .replace("__INFO__", _js(info))
            .replace("__MODES__", _js(list(modes))).replace("__UNIT__", unit)
            .replace("__TOPN__", str(top_n)).replace("__NOTE__", escape(note))
            .replace("__H__", str(height - 10)).replace("__FONTLINK__", _FONT_LINK))
    components.html(html, height=height, scrolling=False)





INFO_CSS = _static("kdesign/info.css")


# ── 보이는 차트 그대로 PNG 로 내려받기 ─────────────────────────────────────────
# 서버에 이미지 엔진(kaleido·Chrome)이 없어도 되게 브라우저에서 만든다: 지금 그린 그림(fig)을 JSON 으로 싣고,
# 단추를 누르면 plotly.js 가 보이지 않는 칸에 같은 그림을 다시 그려 PNG 로 저장한다. 조건·차트 유형이 바뀌면
# 페이지가 다시 돌며 새 fig 가 실리므로 늘 화면과 같은 그림이 내려받아진다.
_PNG_BTN = _static("kdesign/png_button.html")


def _plotly_rich(text: str) -> str:
    """화면 제목 HTML → plotly 제목 문법. 결론형 제목의 강조 구절 <span class="key"> 만 파랑으로 살리고 나머지 태그는 지운다."""
    import re
    t = re.sub(r'<span class="key">(.*?)</span>', lambda m: f'<span style="color:{ACCENT}">{m.group(1)}</span>', text)
    return re.sub(r"<(?!/?span|br)[^>]+>", "", t)


def png_button(fig, filename: str, label: str = "PNG 이미지 내려받기", width: int = 1100, align: str = "flex-end",
               title: str | None = None, source: str | None = None, trigger: str | None = None) -> None:
    """지금 화면의 plotly 그림(fig)을 PNG 로 내려받는 단추(Datawrapper 내보내기 모양).
    title = 화면의 결론형 제목(HTML 가능, 강조 구절은 파랑), source = 아래 출처 한 줄 — 둘 다 이미지에만 들어가고 화면 그림은 그대로다.
    trigger = 바깥 Streamlit 단추의 key — 주면 이 칸의 단추는 숨기고(높이 0) 그 단추가 이 그림을 내려받게 한다
    (단추 모양을 CSV 단추와 똑같이 하려고. 클릭 연결은 static/img_dl.js)."""
    out = go.Figure(fig)
    h = int(out.layout.height or 420)
    m = out.layout.margin
    top, bottom = (m.t or 10), (m.b or 8)
    if title:
        out.update_layout(title=dict(text=f"<b>{_plotly_rich(title)}</b>", x=0.01, xanchor="left", y=0.98, yanchor="top",
                                     font=dict(size=18, color=TEXT)))
        top += 56
    if source:
        source = "출처: " + public_source(source)
        out.add_annotation(text=_plotly_rich(source), xref="paper", yref="paper", x=0, y=0, xanchor="left", yanchor="top",
                           yshift=-bottom - 18, showarrow=False, align="left", font=dict(size=12.5, color=MUTED))
        bottom += 34
    out.update_layout(margin=dict(t=top, b=bottom, l=m.l, r=m.r), height=h + (top - (m.t or 10)) + (bottom - (m.b or 8)))
    h = int(out.layout.height)
    html = (_PNG_BTN.replace("__FIG__", out.to_json()).replace("__FILE__", escape(filename).replace('"', ""))
            .replace("__LABEL__", escape(label)).replace("__W__", str(width)).replace("__HGT__", str(h))
            .replace("__ALIGN__", align).replace("__FONTLINK__", _FONT_LINK).replace("__TRIGGER__", trigger or ""))
    components.html(html, height=0 if trigger else 42, scrolling=False)


def inject() -> None:
    """디자인 CSS 층을 순서대로 넣는다."""
    st.html(CSS)
    st.html(WIDGET_CSS)
    if CHART_ANIM:
        st.html(CHART_ANIM)
    st.html(TABLE_CSS)
    st.html(INFO_CSS)
