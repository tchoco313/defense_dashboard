"""공용 화면 요소 — 팀원 디자인 데모(K-Defense) 틀 위의 호환 층.

디자인(CSS·사이드바·머리띠·구역·카드·KPI·탭·지도·도넛)은 dashboard/kdesign.py(데모 1~3절을 그대로 옮긴 것)가 정본이다.
이 파일은 페이지들이 import 하던 이름(색 토큰·kpi·zone·style_fig·csv_header·period_control 등)을 유지하고 kdesign 으로 잇는다.
이름은 Cloud 재배포 호환을 위해 지우지 않는다(값·동작만 바뀜). 새 이름을 페이지에서 import 하면 Manage app → Reboot.
"""
from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

import kdesign
from kdesign import (chart_source, chart_title, source_pop, country_map, core_kpis, globe_loading, hero, hhi_level, hover_donut, mini_rail, png_button,  # noqa: F401
                     rank_card, rules_card, share_card, sidebar, sparkline, supply_table)
from metrics import period_years

# ── 색 토큰(데모 값) ─────────────────────────────────────────────────────────
BG, PANEL, PANEL2, LINE = kdesign.BG, kdesign.PANEL, kdesign.PANEL2, kdesign.LINE
TEXT, MUTED, ACCENT = kdesign.TEXT, kdesign.MUTED, kdesign.ACCENT
CAPTION, ZONE_LINE, BRAND_WEAK = "#8494ae", LINE, "#e8f0ff"
OK, WARN = kdesign.UP, kdesign.DOWN
NAVY = kdesign.NAVY

# 국가 색: 주요 7개국 고정 + 추가 1개국(등장 순) + 기타. 같은 국가 = 모든 차트에서 같은 색. 8개국을 넘으면 기타로 묶는다
COUNTRY_COLOR = {"TW": kdesign.SERIES[0], "CN": kdesign.SERIES[1], "US": kdesign.SERIES[2], "JP": kdesign.SERIES[3],
                 "VN": kdesign.SERIES[4], "SG": kdesign.SERIES[5], "HK": kdesign.SERIES[6]}
EXTRA_COLORS = [kdesign.SERIES[7]]              # 그 밖 국가는 등장 순 1색, 다음부터는 기타(새 색을 만들지 않는다)
ETC = kdesign.ETC
IMP, EXP = kdesign.SERIES[0], kdesign.SERIES[1]   # 수입 파랑 · 수출 주황(모든 차트 · 지도 · 조회에서 같은 짝)
IMP_DIM, EXP_DIM = "#9fc1ec", "#f5b597"            # 부분연도(같은 색의 옅은 톤)
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


# 데모 CSS 뒤에 얹는 호환 규칙 — 기존 페이지가 쓰던 클래스(page-h·cond·kpis.w4422·delta·badge·key·kpi-src)를 데모 톤으로.
COMPAT_CSS = """<style>
.page-h{font-size:23.5px;font-weight:800;letter-spacing:-.5px;color:#0f2c5e;margin:0 0 4px;line-height:1.3}
.page-q{font-size:14.5px;color:#3d5b8c;margin:0 0 6px;line-height:1.55}
.cond{font-size:13px;color:var(--muted);padding:6px 2px;display:flex;gap:12px;flex-wrap:wrap}
.cond b{color:var(--text);font-weight:700}
.kpis.k5{grid-template-columns:repeat(5,1fr)} .kpis.w4422{grid-template-columns:2fr 2fr 1fr 1fr}
.kpi-src{font-size:12px;color:#8494ae;margin-top:6px}
.delta{display:inline-block;font-size:12.5px;font-weight:600;color:var(--accent);background:#e8f0fe;border-radius:6px;padding:1px 7px;margin-right:4px}
.badge{display:inline-block;font-size:12px;font-weight:600;color:#075985;background:#e0f2fe;border-radius:5px;padding:0 6px;margin-left:6px;vertical-align:middle}
.key{color:var(--accent)}
.h .key{color:var(--accent)}
div[class*="st-key-filters_"]{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 18px 6px}
</style>"""


style_fig = kdesign.style_fig


def dark_geo(fig):
    """지도 배경(라이트). 이름은 페이지 import 호환용으로 유지한다."""
    fig.update_geos(projection_type="natural earth", showland=True, landcolor="#e9eef5", showocean=True, oceancolor="#f4f9ff",
                    showcountries=True, countrycolor=LINE, coastlinecolor=LINE, bgcolor="rgba(0,0,0,0)", showframe=False)
    return fig


def kpi(label: str, value: str, unit: str, sub: str, tag: str = "", icon: str = "") -> str:
    """KPI 카드 한 장(Tremor — 라벨 · 큰 숫자 · 단위 · 설명). icon 은 호환용(그리지 않음). 여러 장을 <div class="kpis"> (k4·k6) 로 감싼다."""
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


def csv_header(cond: str, source: str, stamps: list[tuple[str, dict, str | None]], extra: str = "") -> str:
    """내려받는 CSV 머리줄 — 조건 · 출처(기관 · 데이터명) · 데이터별 자료 기간 · 내려받은 날.
    DB 표 · 뷰 · 열 이름과 DB 적재일은 넣지 않는다(보안, 2026-09-24 사용자 — kdesign.public_source 로 거른다).
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


def inject_css() -> None:
    kdesign.inject()
    st.html(COMPAT_CSS)


zone = kdesign.zone


def top_bar(pages, current, stamp: str) -> None:
    """(호환용 — 2026-09-23 데모 틀 전환 뒤 쓰지 않음) 사이드바는 kdesign.sidebar."""
    return None
