"""공용 화면 요소 — 디자인 모듈 위의 호환 층.

본문 디자인(CSS·블록·경로 줄·카드·KPI·탭·지도·도넛)은 dashboard/kdesign.py 가 정본이다.
이 파일은 페이지들이 import 하던 이름(색 토큰·kpi·zone·style_fig·csv_header·period_control 등)을 유지하고 kdesign 으로 잇는다.
이름은 Cloud 재배포 호환을 위해 지우지 않는다(값·동작만 바뀜). 새 이름을 페이지에서 import 하면 Manage app → Reboot.
"""
from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

import kdesign
from kdesign import (chart_source, chart_title, source_pop, country_map, core_kpis, globe_loading, hero, hhi_level, hover_donut, png_button,  # noqa: F401
                     rank_card, rules_card, share_card, sparkline, supply_table)
from metrics import period_years

# ── 색 토큰 ─────────────────────────────────────────────────────────
BG, PANEL, PANEL2, LINE = kdesign.BG, kdesign.PANEL, kdesign.PANEL2, kdesign.LINE
TEXT, MUTED, ACCENT = kdesign.TEXT, kdesign.MUTED, kdesign.ACCENT
CAPTION, ZONE_LINE, BRAND_WEAK = "#8494ae", LINE, "#e8f0ff"
OK, WARN = kdesign.UP, kdesign.DOWN
NAVY = kdesign.NAVY

# 국가 색: 주요 7개국 고정 + 추가 1개국(등장 순) + 기타. 같은 국가 = 모든 차트에서 같은 색. 8개국을 넘으면 기타로 묶는다
# 미국 = 파랑 · 중국 = 주황 · 일본 = 보라. 대만은 미국과 나란히 크게 나오므로 파랑 계열(하늘)을 피해 청록
COUNTRY_COLOR = {"US": kdesign.SERIES[0], "TW": kdesign.SERIES[2], "CN": kdesign.SERIES[1], "JP": kdesign.SERIES[3],
                 "VN": kdesign.SERIES[4], "HK": kdesign.SERIES[5], "SG": kdesign.SERIES[6]}
EXTRA_COLORS = [kdesign.SERIES[7]]              # 그 밖 국가는 등장 순 1색, 다음부터는 기타(새 색을 만들지 않는다)
ETC = kdesign.ETC
IMP, EXP = kdesign.SERIES[0], "#0fa595"          # 수입 파랑 · 수출 청록(모든 차트 · 지도 · 조회에서 같은 짝)
IMP_DIM, EXP_DIM = "#a9c5fb", "#93e1d5"            # 부분연도(같은 색의 옅은 톤)
SERIES = kdesign.SERIES


# 품목군 짧은 이름 — 홈 막대·지도, ③ 현황표. 없으면 ref_hs_whitelist.name_ko
SHORT = {"901420": "항공 항행기기", "841191": "터보제트 부분품", "880730": "항공기 부분품", "854110": "다이오드",
         "854231": "프로세서 IC", "901490": "항행 부분품", "852692": "원격조종기기", "901380": "광학기기",
         "852691": "무선항행", "854239": "기타 IC", "852610": "레이더 기기", "854129": "트랜지스터 ≥1W",
         "852990": "통신·레이더 부분품", "901410": "컴퍼스", "852560": "송수신기", "901480": "기타 항행기기",
         "852910": "안테나", "854233": "증폭기 IC", "854121": "트랜지스터 <1W"}


def country_colors(codes: list[str]) -> dict[str, str]:
    """등장 순서대로 색을 정한다(고정 7개국은 항상 같은 색, 추가 색을 다 쓰면 기타)."""
    out, extra = {}, iter(EXTRA_COLORS)
    for c in codes:
        if c not in out:
            out[c] = COUNTRY_COLOR.get(c) or next(extra, ETC)
    return out


# 디자인 CSS 뒤에 얹는 호환 규칙 — 페이지가 쓰는 클래스(page-h·cond·kpis.w4422·delta·badge·key·kpi-src)를 같은 톤으로.
COMPAT_CSS = """<style>
.page-h{font-size:23.5px;font-weight:800;letter-spacing:-.5px;color:#0f2c5e;margin:0 0 4px;line-height:1.3}
.page-q{font-size:14.5px;color:#3d5b8c;margin:0 0 6px;line-height:1.55}
.cond{font-size:13px;color:var(--muted);padding:6px 2px;display:flex;gap:12px;flex-wrap:wrap}
.cond b{color:var(--text);font-weight:700}
.kpis.k5{grid-template-columns:repeat(5,minmax(0,1fr))} .kpis.w4422{grid-template-columns:2fr 2fr 1fr 1fr}
.kpi-src{font-size:12px;color:#8494ae;margin-top:6px}
.delta{display:inline-block;font-size:12.5px;font-weight:600;color:var(--accent);background:#e8f0fe;border-radius:6px;padding:1px 7px;margin-right:4px}
.badge{display:inline-block;font-size:12px;font-weight:600;color:#075985;background:#e0f2fe;border-radius:5px;padding:0 6px;margin-left:6px;vertical-align:middle}
.key{color:var(--accent)}
.h .key{color:var(--accent)}
div[class*="st-key-filters_"]{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 18px 6px}
.dt-wrap{overflow-x:auto}
.dt{width:100%;border-collapse:collapse;font-size:13.5px;line-height:1.5;color:var(--text)}
.dt th{background:#f4f7fc;color:var(--muted);font-weight:600;text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
.dt td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.dt td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.dt td.nw{white-space:nowrap}
.dt a{color:var(--accent)}
/* 조회 — 칸이 좁으면 조건 · 결과 칸을 위아래로 쌓는다. 옆으로 두면 국가 칩 · 연도 · 지표 이름이 한두 글자로 잘린다 */
.st-key-zone_sel{container-type:inline-size}
@container (max-width:880px){
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-card_form){flex-wrap:wrap}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-card_form) > [data-testid="stColumn"]{flex:1 1 100%!important;width:100%!important;min-width:100%}
}
</style>"""


style_fig = kdesign.style_fig


def dark_geo(fig):
    """지도 배경(라이트). 이름은 페이지 import 호환용으로 유지한다."""
    fig.update_geos(projection_type="natural earth", showland=True, landcolor="#e9eef5", showocean=True, oceancolor="#f4f9ff",
                    showcountries=True, countrycolor=LINE, coastlinecolor=LINE, bgcolor="rgba(0,0,0,0)", showframe=False)
    return fig


def kpi(label: str, value: str, unit: str, sub: str, tag: str = "", icon: str = "") -> str:
    """KPI 카드 한 장(아이콘 배지 · 제목 · 가운데 큰 숫자 · 설명). icon 을 비우면 제목 낱말로 고른다. 여러 장을 <div class="kpis"> (k4·k6) 로 감싼다."""
    return kdesign.kpi(label, value, unit, sub, tag, icon)


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


def html_table(df, num_cols: tuple = (), link_cols: tuple = (), nowrap_cols: tuple = ()) -> str:
    """칸 안에서 줄바꿈되는 HTML 표 — 긴 글 열이 있는 작은 표용. st.dataframe 은 칸 안 줄바꿈이 안 돼
    긴 이름이 잘리거나 표가 가로로 넘친다. 좁은 화면에서는 표만 가로로 밀린다."""
    def cell(c, v) -> str:
        if v is None or v != v:                                  # None · NaN
            return "<td>—</td>"
        if c in link_cols:
            s = str(v)
            return (f'<td><a href="{escape(s)}" target="_blank" rel="noopener">열기</a></td>' if s.startswith("http")
                    else "<td>—</td>")
        if c in num_cols:
            return f'<td class="n">{int(v):,}</td>'
        return f'<td{" class=nw" if c in nowrap_cols else ""}>{escape(str(v))}</td>'
    head = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(cell(c, v) for c, v in zip(df.columns, r)) + "</tr>" for r in df.itertuples(index=False))
    return f'<div class="dt-wrap"><table class="dt"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def csv_header(cond: str, source: str, stamps: list[tuple[str, dict, str | None]], extra: str = "") -> str:
    """내려받는 CSV 머리줄 — 조건 · 출처(기관 · 데이터명) · 데이터별 자료 기간 · 내려받은 날.
    DB 표 · 뷰 · 열 이름과 DB 적재일은 넣지 않는다(보안 — kdesign.public_source 로 거른다).
    stamps = [(데이터 이름, db.data_stamp(...), 기간 문구 재정의|None), …]. 조회 실패한 데이터는 「—(조회 실패)」."""
    lines = [f"# 조건: {kdesign.public_source(cond) if kdesign._DB_BITS.search(cond) else cond}",
             f"# 출처: {kdesign.public_source(source)}"]
    today = None
    for name, s, period in stamps:
        today = today or s.get("today")
        if s.get("error") and not s.get("has_period"):
            lines.append(f"# 자료 기간({name}): —(조회 실패)")
            continue
        lines.append(f"# 자료 기간({name}): {period or s.get('period') or '—'}")
    lines.append(f"# 내려받은 날: {today or date.today().isoformat()}")
    if extra:
        lines.append(f"# {kdesign.public_source(extra)}")
    return "\n".join(lines) + "\n"


# Streamlit 기본 페이지는 <html lang="en"> 이라 Chrome 이 영어로 보고 자동 번역해 한글을 깨뜨린다(예: 「HOME」→「집」).
# 고정 문자열만 실행한다 — 사용자 입력을 섞지 않는다.
LANG_JS = ("<script>(function(d){d.lang='ko';d.setAttribute('translate','no');d.classList.add('notranslate');})"
           "(document.documentElement);</script>")


def inject_css() -> None:
    kdesign.inject()
    st.html(COMPAT_CSS)
    st.html(LANG_JS, unsafe_allow_javascript=True)


zone = kdesign.zone

