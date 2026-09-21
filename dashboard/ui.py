"""공용 화면 요소 — 다크 테마 CSS, 상단 바(브랜드·메뉴·기준일), 구역 틀, 국가 색.

디자인 기준: docs/report/app/mockup-2026-09-18/(main.html · common.css). 색 토큰은 common.css 와 같은 값을 쓴다.
"""
from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from metrics import period_years

# ── 색 토큰(common.css) ─────────────────────────────────────────────────────
BG, PANEL, PANEL2, LINE = "#0e1320", "#161c2a", "#1c2436", "#2a3347"
TEXT, MUTED, ACCENT = "#e7eaf0", "#8b94a8", "#5b9bff"

# 국가 색: 목업 6개 고정 + 나머지는 순서대로, 다 쓰면 기타 회색
COUNTRY_COLOR = {"US": "#5b9bff", "TW": "#f2b33d", "CN": "#b07cff", "SG": "#2ec4b6", "VN": "#ff8fab", "JP": "#9aa5b1"}
EXTRA_COLORS = ["#7fd1ff", "#ffb37f", "#9be38a", "#e67d7d", "#d9c27a"]
ETC = "#4a5570"
IMP, EXP = ACCENT, "#ff8f4d"                   # 수입 파랑 · 수출 주황(시리즈 고정)
IMP_DIM, EXP_DIM = "#35507f", "#8a4f31"        # 부분연도(점선)


# 품목군 짧은 이름(목업 표기) — 홈 막대·지도, ③ 현황표. 없으면 ref_hs_whitelist.name_ko
SHORT = {"901420": "항공 항행기기", "841191": "터보제트 부분품", "880730": "항공기 부분품", "854110": "다이오드",
         "854231": "프로세서 IC", "901490": "항행 부분품", "852692": "원격조종기기", "901380": "광학기기",
         "852691": "무선항행", "854239": "기타 IC", "852610": "레이더 기기", "854129": "트랜지스터 ≥1W",
         "852990": "통신·레이더 부분품", "901410": "컴퍼스", "852560": "송수신기", "901480": "기타 항행기기",
         "852910": "안테나", "854233": "증폭기 IC", "854121": "트랜지스터 <1W"}


def country_colors(codes: list[str]) -> dict[str, str]:
    """등장 순서대로 색을 정한다(고정 6개국은 항상 같은 색)."""
    out, extra = {}, iter(EXTRA_COLORS)
    for c in codes:
        if c not in out:
            out[c] = COUNTRY_COLOR.get(c) or next(extra, ETC)
    return out


CSS = f"""
<style>
:root{{--bg:{BG};--panel:{PANEL};--panel2:{PANEL2};--line:{LINE};--text:{TEXT};--muted:{MUTED};--accent:{ACCENT};--tag:#2b3550}}
[data-testid="stHeader"]{{display:none}}
.block-container{{padding:0 32px 24px;max-width:1440px}}
/* 상단 바 */
.st-key-topbar{{border-bottom:1px solid var(--line);background:#0b101b;margin:0 -32px 18px;padding:14px 32px}}
.st-key-topnav [data-testid="stHorizontalBlock"]{{gap:4px;flex-wrap:nowrap}}
.st-key-topnav [data-testid="stColumn"]{{flex:0 0 auto!important;width:auto!important;min-width:0!important}}
.st-key-topbar [data-testid="stPageLink"] a{{padding:5px 10px;border-radius:8px;background:transparent}}
.st-key-topbar [data-testid="stPageLink"] a p{{font-size:13px;color:var(--muted);white-space:nowrap}}
.nav-on{{display:inline-block;padding:5px 10px;font-size:13px;color:var(--text);white-space:nowrap;border-radius:8px;
  background:var(--panel2);box-shadow:inset 0 -2px 0 var(--accent)}}
.brand{{font-size:19px;font-weight:700;letter-spacing:-.3px;line-height:1.3;color:var(--text)}}
.brand small{{display:block;font-size:11px;color:var(--muted);font-weight:400;margin-top:2px}}
.nav-off{{display:inline-block;padding:5px 10px;font-size:13px;color:#566078;cursor:not-allowed;white-space:nowrap}}
.stamp{{font-size:12px;color:var(--muted);text-align:right;line-height:1.5}}
/* 구역(점선 틀 + 왼쪽 위 태그) */
div[class*="st-key-zone_"]{{position:relative;border:1px dashed #3a4560;border-radius:14px;padding:30px 16px 16px;margin:12px 0 16px;overflow:visible}}
div[class*="st-key-zone_"]::before{{position:absolute;top:-11px;left:16px;background:var(--accent);color:#08101f;
  font-size:12px;font-weight:700;padding:3px 10px;border-radius:20px;z-index:1}}
/* 카드·글 */
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;height:100%}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}}
.kpis.k4{{grid-template-columns:repeat(4,1fr)}}
.kpi .s .up{{color:#5fd39a}} .kpi .s .dn{{color:#ff8a8a}}
.page-h{{font-size:20px;font-weight:700;color:var(--text);margin:4px 0 2px}}
.kpi .l{{font-size:12px;color:var(--muted)}}
.kpi .v{{font-size:28px;font-weight:700;margin-top:6px;letter-spacing:-.5px;color:var(--text)}}
.kpi .v small{{font-size:14px;color:var(--muted);font-weight:500;margin-left:3px}}
.kpi .s{{font-size:11px;color:var(--muted);margin-top:4px}}
.ex{{display:inline-block;font-size:10px;color:#ffd48a;border:1px solid #6b5520;border-radius:4px;padding:0 4px;margin-left:4px;vertical-align:middle}}
.h{{font-size:14px;font-weight:700;margin-bottom:10px;display:flex;align-items:center;gap:8px;color:var(--text)}}
.h .sub{{font-size:11px;color:var(--muted);font-weight:400}}
.note{{font-size:11px;color:var(--muted);line-height:1.6}}
.note b{{color:var(--text)}}
.legend{{display:flex;gap:12px;flex-wrap:wrap;font-size:11px;color:var(--muted)}}
.legend i{{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:middle}}
.caption{{font-size:11px;color:#6f7890}}
/* Streamlit 카드 컨테이너(border=True)를 목업 카드처럼 */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [class*="st-key-card_"]),div[class*="st-key-card_"]{{background:var(--panel);border-color:var(--line)!important;border-radius:12px}}
</style>
"""


def style_fig(fig, height: int | None = None):
    """plotly 그림을 다크 카드에 맞춘다(배경 투명 · 격자 LINE · 글자 TEXT/MUTED). st.plotly_chart(theme=None)과 함께 쓴다."""
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TEXT, size=12), title_font=dict(size=14, color=TEXT),
                      legend=dict(font=dict(color=MUTED), bgcolor="rgba(0,0,0,0)"),
                      hoverlabel=dict(bgcolor=PANEL2, bordercolor=LINE, font=dict(color=TEXT)))
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    if height:
        fig.update_layout(height=height)
    return fig


def dark_geo(fig):
    """지도 배경을 홈 지도와 같게."""
    fig.update_geos(projection_type="natural earth", showland=True, landcolor="#232c40", showocean=True, oceancolor="#121827",
                    showcountries=True, countrycolor="#33405c", coastlinecolor="#33405c", bgcolor="rgba(0,0,0,0)", showframe=False)
    return fig


def kpi(label: str, value: str, unit: str, sub: str, tag: str = "") -> str:
    """KPI 카드 HTML 한 장. 여러 장을 <div class="kpis"> 로 감싼다."""
    t = f'<span class="ex">{tag}</span>' if tag else ""
    return (f'<div class="card kpi"><div class="l">{label}{t}</div>'
            f'<div class="v">{value}<small>{unit}</small></div><div class="s">{sub}</div></div>')


def period_options(full_years) -> dict[str, list[int]]:
    """홈·③ 기간 선택지 라벨 → 연도 목록(완결 연도만). 빈 입력 → {}."""
    p = period_years(full_years)
    if not p:
        return {}
    y1, y0 = p["base"][0], p["all"][0]
    return {f"{y1} 기준 연도": p["base"], "최근 5년": p["recent5"], f"전체 {y0}~": p["all"]}


def period_control(df, note: str, key: str = "period") -> tuple[list[int], str]:
    """기간 기준 버튼(기준 연도 / 최근 5년 / 전체). df 는 year·is_partial_year 열을 가진 연도 집계.
    부분연도는 선택지에서 뺀다(연속 범위가 아니라 실제 있는 완결 연도만). 완결 연도가 없으면 안내 후 ([], "") —
    호출부는 `if not years: st.stop()`. 페이지마다 다른 key 를 준다(라벨이 자료 범위에 따라 달라 세션값이 섞이지 않게).
    돌려주는 값: (연도 목록, 표시 라벨)."""
    full = df.loc[df["is_partial_year"] == 0, "year"].unique().tolist() if not df.empty else []
    opts = period_options(full)
    if not opts:
        st.info("완결 연도(부분연도 제외) 실적이 없어 기간 기준을 만들 수 없습니다.")
        return [], ""
    c_note, c_seg = st.columns([3, 2], vertical_alignment="center")
    c_note.html(f'<div class="note">{escape(note)}</div>')
    with c_seg:
        choice = st.segmented_control("기간 기준", list(opts), default=list(opts)[0], key=key,
                                      label_visibility="collapsed", width="stretch") or list(opts)[0]
    years = opts[choice]
    return years, (f"{years[0]}년" if len(years) == 1 else f"{years[0]}~{years[-1]}")


def csv_header(cond: str, source: str, stamps: list[tuple[str, dict, str | None]], extra: str = "") -> str:
    """내려받는 CSV 머리줄. stamps = [(데이터 이름, db.data_stamp(...), 기간 문구 재정의|None), …].
    「기준일」 하나로 뭉치지 않고 데이터별 자료 기간(원천)·DB 적재일과, 내려받은 날(파일 생성일)을 따로 적는다.
    조회 실패한 데이터는 기간·적재일을 「—(조회 실패)」로 적는다."""
    lines = [f"# 조건: {cond}", f"# 출처: {source}"]
    today = None
    for name, s, period in stamps:
        today = today or s.get("today")
        if s.get("error") and not s.get("loaded") and not s.get("has_period"):
            lines.append(f"# 자료 기간({name}): —(조회 실패) · DB 적재 —")
            continue
        lines.append(f"# 자료 기간({name}): {period or s.get('period') or '—'} · DB 적재 {s.get('loaded') or '—'}")
    lines.append(f"# 내려받은 날: {today or date.today().isoformat()}")
    if extra:
        lines.append(f"# {extra}")
    return "\n".join(lines) + "\n"


def inject_css() -> None:
    st.html(CSS)


def zone(key: str, tag: str):
    """점선 구역. 태그 글자는 CSS attr() 로 못 넘기므로 구역마다 규칙을 하나 더 넣는다."""
    # <style> 안은 HTML 엔티티를 풀지 않는다(escape 를 쓰면 & 가 &amp; 그대로 보인다) — CSS 문자열 규칙으로 막는다
    css_tag = tag.replace("\\", "\\\\").replace('"', '\\"').replace("<", "\\3C ").replace("\n", " ")
    st.html(f'<style>.st-key-zone_{key}::before{{content:"{css_tag}"}}</style>')
    return st.container(key=f"zone_{key}")


def top_bar(pages: list[tuple[object | None, str]], current: object, stamp: str) -> None:
    """브랜드 | 메뉴 | 기준일. pages = [(st.Page 또는 None(준비 중), 라벨)], current = 지금 페이지(강조, 링크 아님)."""
    with st.container(key="topbar"):
        c_brand, c_nav, c_stamp = st.columns([3.2, 7, 1.6], vertical_alignment="center")
        c_brand.html('<div class="brand">주요 방산 전자부품 수출입 및 국산화 현황'   # 2026-09-21 회의 M1·M8
                     '<small>공식 분류·통제표로 고른 전자부품 품목군 · 공개 데이터 기반 현황 대시보드</small></div>')
        with c_nav.container(key="topnav"):
            cols = st.columns(len(pages), gap=None, vertical_alignment="center")
            for col, (page, label) in zip(cols, pages):
                if page is None:
                    col.html(f'<span class="nav-off" title="준비 중">{escape(label)}</span>')
                elif page is current:
                    col.html(f'<span class="nav-on">{escape(label)}</span>')
                else:
                    col.page_link(page, label=label)
        c_stamp.html(f'<div class="stamp">{stamp}</div>')
