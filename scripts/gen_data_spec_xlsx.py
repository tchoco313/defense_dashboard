# -*- coding: utf-8 -*-
"""산출물 3 「데이터 수집 목록 및 명세서」 xlsx 생성 (2026-09-22).

db/meta_dataset.csv(수집 데이터셋 26종) + db/table_dict.csv(역할·한 행·주의)
+ db/column_dict.csv(열 설명) + 원본 파일 실측(scripts/load_db.py read_raw — 행 수·열·예시값. 2026-09-22 raw_ 표 삭제 후)
+ RDS 실측(정제·기준·뷰 행 수·열) + db/clean_transform_map.csv(원본→정제층 이름이 바뀐 대응 48건)
  → docs/report/data/3_데이터수집목록및명세서-<날짜>.xlsx
    (시트 = 목록 1 + 수집 데이터셋 26 + (참고) DB 테이블·뷰 1 + 정제변경 요약·상세 2)

서식은 resource/drive/3_데이터수집목록및명세서_샘플.xlsx 실측값을 그대로 따른다
(폰트 Malgun Gothic 11 / 제목 20 bold / 머리행 회색 FFD8D8D8 / 전 셀 thin 테두리 / 행 높이 16.5).
손으로 xlsx를 고치지 말고 세 CSV를 고친 뒤 재생성한다. dbconf etl SELECT 만 한다.

    .venv/bin/python scripts/gen_data_spec_xlsx.py
    .venv/bin/python scripts/gen_data_spec_xlsx.py --out /tmp/spec.xlsx --asof 2026-10-02
"""
import argparse
import collections
import csv
import datetime
import math
import pathlib
import re
import sys

import pymysql
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.hyperlink import Hyperlink

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dbconf  # noqa: E402
from load_db import RAW_TABLES, read_raw  # noqa: E402  원본 파일 데이터셋(파서)

sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("--out", help="출력 xlsx 경로(기본 docs/report/data/3_데이터수집목록및명세서-<asof>.xlsx)")
ap.add_argument("--asof", default=datetime.date.today().isoformat(), help="작성일자(YYYY-MM-DD)")
ARGS = ap.parse_args()
TODAY = ARGS.asof

# ── 샘플 실측 서식 ──────────────────────────────────────────────
FONT = "Malgun Gothic"
THIN = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill("solid", fgColor="FFD8D8D8")
F_BODY = Font(name=FONT, sz=11)
F_HEAD = Font(name=FONT, sz=11, b=True)
F_TITLE = Font(name=FONT, sz=20, b=True)
# 링크 글자: 샘플 목록 C열 실측(밑줄 single + 하이퍼링크 색). 샘플은 theme 10 을 쓰는데 그 테마의
# hlink 는 0563C1 이고 openpyxl 기본 테마는 0000FF 라 색이 달라진다 → 보이는 색을 맞추려 RGB 로 고정.
F_LINK = Font(name=FONT, sz=11, u="single", color="FF0563C1")
A_C = Alignment(horizontal="center", vertical="center", wrap_text=True)
A_L = Alignment(horizontal="left", vertical="center", wrap_text=True)
A_R = Alignment(horizontal="right", vertical="center")
A_V = Alignment(vertical="center", wrap_text=True)
ROW_H = 16.5


def put(ws, coord, value, font=F_BODY, align=A_V, fill=None, fmt=None):
    c = ws[coord]
    c.value = value
    c.font = font
    c.alignment = align
    c.border = BORDER
    if fill:
        c.fill = fill
    if fmt:
        c.number_format = fmt
    return c


def border_range(ws, ref):
    """병합 범위 전체에 테두리(샘플과 동일하게 조각 셀도 테두리를 갖는다)."""
    cells = ws[ref]
    if not isinstance(cells, tuple):
        cells = ((cells,),)
    for row in cells:
        if not isinstance(row, tuple):
            row = (row,)
        for c in row:
            c.border = BORDER


def label(ws, ref, text):
    """회색 라벨 셀(병합 가능)."""
    first = ref.split(":")[0]
    if ":" in ref:
        ws.merge_cells(ref)
    border_range(ws, ref)
    put(ws, first, text, font=F_HEAD, align=A_C, fill=HEAD_FILL)


def value(ws, ref, text, align=A_L, fmt=None):
    first = ref.split(":")[0]
    if ":" in ref:
        ws.merge_cells(ref)
    border_range(ws, ref)
    put(ws, first, text, align=align, fmt=fmt)


def title_block(ws, ref, text):
    ws.merge_cells(ref)
    border_range(ws, ref)
    put(ws, ref.split(":")[0], text, font=F_TITLE, align=A_C)


def link_cell(cell, location, display=None):
    """같은 통합문서 안으로 가는 내부 링크.

    `cell.hyperlink = "#..."` 처럼 문자열을 넣으면 openpyxl 이 TargetMode="External" 관계로 써서
    Excel 은 따라가지만 macOS Numbers 는 무시한다. 샘플 xlsx 와 같이 `location=` 만 있는
    내부 링크(<hyperlink ref=".." location="'시트'!A1"/>, r:id 없음)로 써야 양쪽에서 눌린다.
    """
    cell.hyperlink = Hyperlink(ref=cell.coordinate, location=location,
                               display=display or str(cell.value))
    cell.font = F_LINK
    return cell


# ── 원천 읽기 ──────────────────────────────────────────────────
meta = {r["dataset_key"]: r for r in csv.DictReader(open(ROOT / "db/meta_dataset.csv", encoding="utf-8"))}
tdict = {r["table_name"]: r for r in csv.DictReader(open(ROOT / "db/table_dict.csv", encoding="utf-8"))}
cdict = collections.defaultdict(list)
for r in csv.DictReader(open(ROOT / "db/column_dict.csv", encoding="utf-8")):
    cdict[r["table_name"]].append(r)
for t in cdict:
    cdict[t].sort(key=lambda x: int(x["ordinal"]))


# ── RDS 실측: 행 수 · 열 · 예시값 ──────────────────────────────
def fetch_files(dataset_tables):
    """FACTS(원본 파일 데이터셋별 행 수·열·예시값) — scripts/load_db.py read_raw(파일 파서). 파일이 없는 데이터셋은
    열 사전·meta_dataset.raw_row_count 로 채우고 예시값은 비운다(경고 출력)."""
    facts = {}
    dict_type = {t: {c["column_name"]: c["dtype"] for c in cols} for t, cols in cdict.items()}
    for t in dataset_tables:
        if t not in RAW_TABLES:            # 참조표 3종(ref_hs_whitelist·ref_country·ref_fsg)은 DB 표 그대로 실측
            facts[t] = fetch_db_sample(t)
            continue
        try:
            df = read_raw(t)
        except FileNotFoundError as e:
            print(f"[경고] {t}: 원본 파일 없음 → 열 사전·meta_dataset 건수로 대체, 예시값 없음 ({e})")
            cols = [c["column_name"] for c in cdict.get(t, [])] + ["source_file", "source_row_no"]
            cnt = next((int(m["raw_row_count"]) for m in meta.values() if m["target_table"] == t and m.get("raw_row_count")), None)
            facts[t] = {"count": cnt, "sample": {}, "dbcols": [{"name": c, "type": dict_type.get(t, {}).get(c, "VARCHAR").upper()} for c in cols]}
            continue
        cols = [c for c in df.columns if c != "row_id"]
        head = df.head(300)
        sample = {}
        for c in cols:
            v = None
            for cell in head[c]:
                if cell is None or (isinstance(cell, float) and math.isnan(cell)):
                    continue
                sv = str(cell).strip()
                if sv in ("", "-"):
                    continue
                v = sv
                break
            if v is None and len(head):
                v = "" if head[c].iloc[0] is None else str(head[c].iloc[0])
            sample[c] = (v or "")[:80]
        facts[t] = {"count": len(df), "sample": sample,
                    "dbcols": [{"name": c, "type": dict_type.get(t, {}).get(c, "INT" if c.endswith("_no") else "VARCHAR").upper()} for c in cols]}
    return facts


def fetch_db_sample(t):
    """DB 표 1개의 행 수·열·예시값(참조표 데이터셋용)."""
    conn = pymysql.connect(**dbconf.pymysql_kwargs("etl", connect_timeout=20))
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT column_name, column_type FROM information_schema.columns "
                        "WHERE table_schema = DATABASE() AND table_name = %s ORDER BY ordinal_position", (t,))
            dbcols = [{"name": c, "type": ct.upper()} for c, ct in cur.fetchall()]
            cols = [c["name"] for c in dbcols]
            cur.execute(f"SELECT COUNT(*) FROM `{t}`")
            cnt = cur.fetchone()[0]
            cur.execute("SELECT " + ",".join(f"`{c}`" for c in cols) + f" FROM `{t}` LIMIT 300")
            head = cur.fetchall()
    finally:
        conn.close()
    sample = {}
    for i, c in enumerate(cols):
        v = None
        for row in head:
            cell = row[i]
            if cell is None:
                continue
            sv = str(cell).strip()
            if sv in ("", "-"):
                continue
            v = sv
            break
        if v is None and head:
            v = "" if head[0][i] is None else str(head[0][i])
        sample[c] = (v or "")[:80]
    return {"count": cnt, "sample": sample, "dbcols": dbcols}


def fetch_db():
    """OBJS(RDS 전 테이블·뷰 행 수·열 수)."""
    conn = pymysql.connect(**dbconf.pymysql_kwargs("etl", connect_timeout=20))
    objs = {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, table_type FROM information_schema.tables "
                "WHERE table_schema = DATABASE() ORDER BY table_name"
            )
            kinds = {n: ("table" if t == "BASE TABLE" else "view") for n, t in cur.fetchall()}
            cur.execute(
                "SELECT table_name, column_name, column_type FROM information_schema.columns "
                "WHERE table_schema = DATABASE() ORDER BY table_name, ordinal_position"
            )
            dbcols = collections.defaultdict(list)
            for t, c, ct in cur.fetchall():
                dbcols[t].append({"name": c, "type": ct.upper()})
            for name, kind in kinds.items():
                rows = None
                if kind == "table":
                    cur.execute(f"SELECT COUNT(*) FROM `{name}`")
                    rows = cur.fetchone()[0]
                objs[name] = {"type": kind, "rows": rows, "cols": len(dbcols[name])}
    finally:
        conn.close()
    return objs


DATASET_TABLES = []
for _r in meta.values():
    if _r["target_table"] not in DATASET_TABLES:
        DATASET_TABLES.append(_r["target_table"])
FACTS = fetch_files(DATASET_TABLES)
OBJS = fetch_db()
print(f"원본 파일 실측: 데이터셋 {len(FACTS)}종 · RDS 테이블·뷰 {len(OBJS)}개")

# meta_dataset 에 비어 있던 다중 파일 데이터셋 크기(실측 합계, 2026-09-22)
FILE_BYTES_FIX = {
    "customs_all": (34907137, "24파일 합계"),
    "openfiscal_program_budget": (653287, "12파일 합계"),
}

# 카테고리 · 표시 순서 · 시트명
CATS = [
    ("1", "무역·품목", [
        ("customs_all",            "품목별 국가별 수출입실적"),
        ("customs_region",         "시군구별 품목별 수출입실적"),
        ("customs_hs_code_master", "관세청 HS부호 마스터"),
        ("customs_hs_unit_name",   "HS부호 단위별 품목명"),
        ("kosti_hsk_control",      "HSK 전략물자 연계표"),
        ("customs_progress",       "관세청 수집 호출 로그"),
    ]),
    ("2", "방산 조달", [
        ("dapa_contract",                 "국내조달 계약정보"),
        ("dapa_bid_notice",               "국내조달 입찰공고"),
        ("dapa_bid_result",               "국내조달 입찰결과"),
        ("dapa_domestic_plan",            "국내조달 조달계획"),
        ("dapa_overseas_plan",            "국외조달 조달계획(사업)"),
        ("dapa_overseas_plan_api",        "국외조달 조달계획(품목)"),
        ("dapa_overseas_contract",        "국외조달 계약정보"),
        ("dapa_overseas_bid_result",      "국외조달 입찰결과"),
        ("dapa_contract_exec_by_service", "군별 계약집행 현황"),
    ]),
    ("3", "부품 국산화", [
        ("dapa_localized_item", "국산화개발품목"),
        ("krit_task",           "KRIT 부품국산화 공고 과제"),
    ]),
    ("4", "재정·예산", [
        ("openfiscal_program_budget", "방위사업청 세부사업 예산"),
    ]),
    ("5", "산업·업체", [
        ("kosis_production_index",  "광공업생산지수 C26 계열"),
        ("kosis_utilization",       "방산업체 분야별 평균가동률"),
        ("dapa_defense_company",    "방산업체 지정현황"),
    ]),
    ("6", "참조·분류", [
        ("ref_hs_whitelist",  "HS6 화이트리스트"),
        ("ref_country",       "국가코드 참조표"),
        ("fsg_master",        "FSG 군급 2자리 분류표"),
        ("dapa_fsc_catalog",  "군급분류집(FSC 4자리)"),
        ("kdsis_nsn",         "KDSIS NSN 목록"),
    ]),
]

COL_HEADERS = ["No", "컬럼명(영문)", "컬럼명(한글)", "Data Type", "데이터형식(예시)", None, "비고", None]

# 한글명을 열 사전 설명에서 뽑을 때 자르는 자리(원본 열명이 영문인 관세청 API·파생 열용)
_KO_CUT = ("`", "(", "—", ". ", ".", ",", " 또는", " 등", "…")


def has_hangul(t):
    return any("\uac00" <= ch <= "\ud7a3" for ch in str(t or ""))


# 원본 열명도 영문이고 열 사전 설명도 이름 구실을 못 하는 열(주로 ref_ 참조표)의 한글명.
# 열 사전의 description 은 「설명」이라 이름으로 못 쓰는 경우가 있어 여기서만 보완한다.
KO_FALLBACK = {
    "hs": "HS6(숫자형)", "hs6": "HS6 코드", "hs_cd": "HS6 코드", "hs_level": "HS 단위",
    "cnty": "국가코드", "stat_cd": "국가코드", "year": "연도", "fetched_at": "수집일",
    "name_ko": "국문명", "name_en": "영문명", "rationale": "선정 사유", "priority": "우선순위",
    "axis": "분석 축", "source": "출처", "source_url": "출처 URL",
    "is_historical": "폐지 군급 여부", "work_drawing_yn": "작업도면 보유 여부",
}


def ko_name(column_name, original_name, description):
    """컬럼명(한글). 원본 열명이 한글이면(방사청 CSV 헤더) 그대로, 영문이면(관세청 API) 설명 첫 구절."""
    if has_hangul(original_name):
        return original_name.replace("\\n", " ").strip()
    d = (description or "").strip()
    if d:
        cut = min((d.find(t) for t in _KO_CUT if d.find(t) > 0), default=len(d))
        head = d[:cut].strip(" ·-")
        if has_hangul(head):
            return head[:40]
    if column_name in KO_FALLBACK:
        return KO_FALLBACK[column_name]
    if d:
        cut = min((d.find(t) for t in _KO_CUT if d.find(t) > 0), default=len(d))
        head = d[:cut].strip(" ·-")
        if head:
            return head[:40]
    return (original_name or column_name).replace("\\n", " ").strip()

# 원본에 없는 적재·파생 열 (열 사전에 없어 DB 실측으로 채운다)
LOAD_COLS = {
    "row_id": "행 ID(적재 시 부여)", "source_file": "원본 파일명", "source_row_no": "원본 행 번호",
    "source_col_no": "원본 열 번호", "loaded_at": "적재 시각", "source_url": "원문 URL",
    "cleaned_at": "정제 시각", "cleaned_by": "정제 계정", "raw_row_id": "원본 행 ID",
    "round_label": "공고 차수", "notice_type": "공고유형", "extra_json": "표 원문 나머지 열(JSON)",
    "table_index": "원문 표 번호",
}
LOAD_NOTE = {
    "row_id": "적재 일련번호(PK) — 원본에 없는 열",
    "source_file": "원본 파일명(재현성 추적)",
    "source_row_no": "원본 파일 내 행 번호",
    "source_col_no": "원본 파일 내 열 번호(광폭 → 세로형 변환분)",
    "loaded_at": "적재 시각",
    "source_url": "원문(공고) URL",
    "round_label": "공고 차수(파일명 토큰) — 열 사전 미등재",
    "notice_type": "공고유형(예비/본/재공고, 파일명 토큰) — 열 사전 미등재",
    "extra_json": "표 원문의 나머지 열을 JSON으로 보존 — 열 사전 미등재",
    "table_index": "원문 문서 내 표 번호 — 열 사전 미등재",
}

# 개인정보성 열은 실제 값을 명세서에 싣지 않는다(열 이름에 이 토큰이 들어가면 마스킹).
# 원본 CSV 자체에는 들어 있고 raw_ 에 보존되지만, 제출 문서에 실을 이유가 없다.
PII_TOKENS = ("officer_name", "officer_phone", "ceo_name", "biz_reg_no",
              "corporation_num", "biz_num", "address")
PII_MASK = "예시 생략(개인정보)"

# 열 사전 dtype 이 RDS 와 어긋난 것(생성 끝에 경고로 낸다)
DTYPE_DRIFT = []


def sample_value(col_name: str, raw: str) -> str:
    if raw and any(tok in col_name for tok in PII_TOKENS):
        return PII_MASK
    return raw


def period_text(m):
    s, e = m["period_start"], m["period_end"]
    if not s and not e:
        return "기간 정보 없음(시점 스냅샷)"
    fmt = lambda d: d[:7].replace("-", ".") if d else "?"
    txt = f"{fmt(s)} ~ {fmt(e)}"
    if m["is_partial_period"] == "1":
        txt += " (부분연도 포함)"
    return txt


def size_text(key, m):
    """원본 파일 크기(KB). meta_dataset 이 비어 있는 다중 파일 데이터셋은 실측 합계를 쓴다."""
    b = m["file_bytes"]
    if not b:
        fix = FILE_BYTES_FIX.get(key)
        if not fix:
            return "-"
        b = fix[0]
    txt = f"{math.ceil(int(b) / 1024):,}KB"
    fix = FILE_BYTES_FIX.get(key)
    if fix and not m["file_bytes"]:
        txt += f"({fix[1]}, 로컬 실측)"
    return txt


def desc_lines(key, m, table, n):
    td = tdict.get(table, {})
    role = (td.get("role") or m["title"]).strip()
    out = [f"  - {role}"]
    out.append(f"  - 기간: {period_text(m)}")
    out.append(f"  - 한 행: {td.get('grain') or '-'} · 적재 행 수: {n:,}행 (RDS 실측 {TODAY})")
    caution = (td.get("caution") or "").strip()
    if caution:
        out.append(f"  - 주의: {caution}")
    return "\n".join(out)


wb = Workbook()

# ══ 시트 1: 목록 ═══════════════════════════════════════════════
ws = wb.active
ws.title = "목록"
ws.sheet_view.showGridLines = False
for col, w in {"A": 5.25, "B": 11.0, "C": 36.83203125, "D": 10.5, "E": 10.5, "F": 10.5, "G": 42.0}.items():
    ws.column_dimensions[col].width = w
ws.row_dimensions[1].height = ROW_H
ws.row_dimensions[2].height = 31.5
for r in (3, 4):
    ws.row_dimensions[r].height = ROW_H

title_block(ws, "A2:G2", "데이터 목록")
value(ws, "G3", f"작성일자: {TODAY}", align=A_R)
ws["G3"].border = Border(left=THIN, top=THIN)

heads = ["No", "카테고리", "데이터명(한글)", "데이터크기", "개수", "데이터유형", "제공처"]
for i, h in enumerate(heads, start=1):
    put(ws, f"{get_column_letter(i)}4", h, font=F_HEAD, align=A_C, fill=HEAD_FILL)

row = 5
sheet_plan = []  # (sheet_name, no, cat_name, short, key)
for cat_no, cat_name, items in CATS:
    start = row
    for i, (key, short) in enumerate(items, start=1):
        m = meta[key]
        table = m["target_table"]
        n = FACTS[table]["count"]
        no = f"{cat_no}-{i:02d}"
        sheet_nm = f"{no} {short}"[:31]
        put(ws, f"A{row}", no, align=A_C, fmt="@")
        put(ws, f"B{row}", None, align=A_C)
        # 데이터명 → 해당 명세 시트 내부 링크(샘플과 같은 방식·위치·글자 서식)
        link_cell(put(ws, f"C{row}", short), f"'{sheet_nm}'!A1", short)
        put(ws, f"D{row}", size_text(key, m), align=A_C)
        put(ws, f"E{row}", n, align=A_C, fmt="#,##0")
        put(ws, f"F{row}", "정형", align=A_C)
        put(ws, f"G{row}", m["provider"], align=A_C)
        ws.row_dimensions[row].height = ROW_H
        sheet_plan.append((sheet_nm, no, cat_name, short, key))
        row += 1
    if row - 1 > start:
        ws.merge_cells(f"B{start}:B{row - 1}")
    border_range(ws, f"B{start}:B{row - 1}")
    put(ws, f"B{start}", f"{cat_name}\n({len(items)})", align=A_C)

ws.freeze_panes = "A5"

note_row = row + 1
ws.row_dimensions[note_row].height = ROW_H
n_customs = FACTS["raw_customs_trade"]["count"]
n_local = FACTS["raw_dapa_localized_item"]["count"]
ws.merge_cells(f"A{note_row}:G{note_row}")
c = ws[f"A{note_row}"]
c.value = (f"※ 「개수」는 원본 파일을 파서(scripts/load_db.py read_raw)로 센 행 수({TODAY})이며 포털 표시 건수가 아니다. "
           f"「데이터크기」는 meta_dataset.file_bytes(단일 파일) 또는 로컬 원본 파일 크기 합(다중 파일). "
           f"1만 건 요건 2종 = 1-01 품목별 국가별 수출입실적 {n_customs:,}행 · 3-01 국산화개발품목 {n_local:,}행.")
c.font = F_BODY
c.alignment = A_L
ws.row_dimensions[note_row].height = ROW_H
note_row2 = note_row + 1
ws.merge_cells(f"A{note_row2}:G{note_row2}")
c2 = ws[f"A{note_row2}"]
c2.value = "※ 데이터셋별 컬럼 명세는 각 데이터명을 눌러 이동. 원본(raw_ 데이터셋 키)은 파일로 보관하고 DB 에 넣지 않는다 — DB 계층: clean_·fact_·dim_ = 정제층 / ref_ = 참조표 / meta_ = 기록 / v_ = 집계 뷰(전체 목록은 「(참고) DB 테이블·뷰」). 원본 → 정제층 열 대응은 「정제변경_요약」·「정제변경_상세」 시트. 담당자·대표자명·연락처·사업자·법인번호·주소 열은 개인정보라 예시값을 생략했다(원본 파일에는 보존). 생성: scripts/gen_data_spec_xlsx.py"
c2.font = F_BODY
c2.alignment = A_L
ws.row_dimensions[note_row2].height = ROW_H

# ══ 시트 2~: 데이터셋별 명세서 ═════════════════════════════════
for sheet_name, no, cat_name, short, key in sheet_plan:
    m = meta[key]
    table = m["target_table"]
    fact = FACTS[table]
    cols = cdict[table]
    d = wb.create_sheet(sheet_name)
    d.sheet_view.showGridLines = False
    for col, w in {"A": 4.33203125, "B": 24.0, "C": 24.0, "D": 14.0,
                   "E": 12.0, "F": 12.0, "G": 9.0, "H": 46.0}.items():
        d.column_dimensions[col].width = w
    for r in range(1, 12):
        d.row_dimensions[r].height = ROW_H

    title_block(d, "A2:H3", "데이터 명세서")

    # 목록 시트로 되돌아가는 링크 (H4)
    nav = d["H4"]
    nav.value = "← 목록"
    nav.alignment = A_R
    link_cell(nav, "'목록'!A4")

    label(d, "A5:B5", "카테고리");          value(d, "C5:H5", f"  {cat_name}")
    label(d, "A6:B6", "데이터명(한글)");    value(d, "C6:H6", f"  {m['title']}")
    desc = desc_lines(key, m, table, fact["count"])
    label(d, "A7:B7", "설명");              value(d, "C7:H7", desc)
    d.row_dimensions[7].height = ROW_H * (desc.count("\n") + 1) + 4

    label(d, "A8:B8", "확보일자")
    value(d, "C8", datetime.date.fromisoformat(m["acquired_on"]), align=A_C, fmt="yyyy-mm-dd")
    label(d, "D8", "데이터기간");           value(d, "E8:F8", period_text(m), align=A_C)
    label(d, "G8", "제공처");               value(d, "H8", m["provider"], align=A_C)

    label(d, "A9:B9", "데이터 ID")
    value(d, "C9", m["dataset_id"] or "-", align=A_C, fmt="@")
    label(d, "D9", "개수");                 value(d, "E9:F9", fact["count"], align=A_C, fmt="#,##0")
    label(d, "G9", "적재 테이블");          value(d, "H9", table, align=A_C)

    label(d, "A10:B10", "원본 URL");        value(d, "C10:H10", f"  {m['url'] or '-'}")
    label(d, "A11:B11", "수집 방식·원본")
    value(d, "C11:H11", f"  {m['access_method']} · {m['raw_path']} (인코딩 {m['encoding']})")

    hr = 12
    d.row_dimensions[hr].height = ROW_H
    for i, h in enumerate(COL_HEADERS, start=1):
        put(d, f"{get_column_letter(i)}{hr}", h, font=F_HEAD, align=A_C, fill=HEAD_FILL)
    d.merge_cells(f"E{hr}:F{hr}")
    d.merge_cells(f"G{hr}:H{hr}")
    border_range(d, f"E{hr}:F{hr}")
    border_range(d, f"G{hr}:H{hr}")

    bydict = {cr["column_name"]: cr for cr in cols}
    r = hr + 1
    n_extra = 0
    for i, dc in enumerate(fact["dbcols"], start=1):
        name = dc["name"]
        cr = bydict.get(name)
        d.row_dimensions[r].height = ROW_H
        put(d, f"A{r}", i, align=A_C)
        put(d, f"B{r}", name)
        # Data Type: 원본 파일 데이터셋은 열 사전 dtype(파서가 읽는 형 — 전 열 문자열, 순번만 정수).
        put(d, f"D{r}", dc["type"], align=A_C)
        if cr:
            put(d, f"C{r}", ko_name(name, cr["original_name"], cr["description"]))
            note = cr["description"]
            orig = (cr["original_name"] or "").replace("\\n", " ").strip()
            if orig and orig != name and not has_hangul(orig):
                note = f"원본 필드 {orig}" + (f" · {note}" if note else "")
            if cr["dtype"].strip().replace(" ", "").upper() != dc["type"].replace(" ", ""):
                DTYPE_DRIFT.append((table, name, cr["dtype"], dc["type"]))
        else:
            n_extra += 1
            put(d, f"C{r}", LOAD_COLS.get(name, "(파생)"))
            note = LOAD_NOTE.get(name, "열 사전 미등재 — db/column_dict.csv 보완 필요(2026-09-22 확인)")
        d.merge_cells(f"E{r}:F{r}")
        border_range(d, f"E{r}:F{r}")
        put(d, f"E{r}", sample_value(name, fact["sample"].get(name, "")), align=A_C, fmt="@")
        d.merge_cells(f"G{r}:H{r}")
        border_range(d, f"G{r}:H{r}")
        put(d, f"G{r}", note)
        r += 1

    d.row_dimensions[r + 1].height = ROW_H
    d.merge_cells(f"A{r + 1}:H{r + 1}")
    cc = d[f"A{r + 1}"]
    tail = ("원본 파일은 수정하지 않고 DB 에 넣지 않는다(파서 read_raw 가 파일명·행 번호·순번을 붙여 정제 노트북이 읽는다)."
            if table.startswith("raw_") else "팀이 만든 기준 데이터다.")
    cc.value = (f"※ 열 {len(fact['dbcols'])}개 = 원본 열 {len(fact['dbcols']) - n_extra}개 "
                f"+ 파서·파생 열 {n_extra}개(원본 열명 칸에 (적재)·(파생) 표기). {tail}")
    cc.font = F_BODY
    cc.alignment = A_L

    d.freeze_panes = f"A{hr + 1}"

# ══ 마지막 시트: (참고) DB 테이블·뷰 ═══════════════════════════
PREFIX_GROUPS = [
    ("ref_",   "참조표 — 기준·라벨"),
    ("raw_",   "원본 파일 — DB 밖(data/raw/ 파일, scripts/load_db.py read_raw 로 읽음)"),
    ("meta_",  "기록 — 출처·적재 단계·열 사전"),
    ("dim_",   "차원"),
    ("fact_",  "사실 — 관세청 월별 수출입"),
    ("clean_", "정제 — 화면·뷰의 원천"),
    ("v_",     "뷰 — 화면이 읽는 집계"),
]

g = wb.create_sheet("(참고) DB 테이블·뷰")
g.sheet_view.showGridLines = False
for col, w in {"A": 5.25, "B": 12.0, "C": 34.0, "D": 10.5, "E": 8.0, "F": 62.0}.items():
    g.column_dimensions[col].width = w
for r in (1, 2, 3, 4):
    g.row_dimensions[r].height = ROW_H
g.row_dimensions[2].height = 31.5
title_block(g, "A2:F2", "(참고) DB 테이블·뷰 목록")
value(g, "F3", f"RDS defense_dashboard 실측: {TODAY}", align=A_R)
g["F3"].border = Border(left=THIN, top=THIN)

for i, h in enumerate(["No", "구분", "테이블·뷰명", "행 수", "열 수", "역할"], start=1):
    put(g, f"{get_column_letter(i)}4", h, font=F_HEAD, align=A_C, fill=HEAD_FILL)

# 사전에만 있고 RDS 에 없는 것 = 원본 파일 데이터셋(table_dict kind=file, raw_…). 그 밖의 것은 미생성 표.
FILE_SETS = {t for t, r in tdict.items() if r.get("kind") == "file"}
DICT_ONLY = [t for t in tdict if t not in OBJS and (t.startswith(("clean_", "raw_", "ref_", "v_", "dim_", "fact_", "meta_")))]

row = 5
no = 0
for pfx, gname in PREFIX_GROUPS:
    names = sorted([n for n in OBJS if n.startswith(pfx)]) + sorted([n for n in DICT_ONLY if n.startswith(pfx)])
    if not names:
        continue
    start = row
    for name in names:
        no += 1
        o = OBJS.get(name)
        td = tdict.get(name, {})
        g.row_dimensions[row].height = ROW_H
        put(g, f"A{row}", no, align=A_C)
        put(g, f"B{row}", None, align=A_C)
        put(g, f"C{row}", name)
        if name in FILE_SETS:
            f = FACTS.get(name, {})
            put(g, f"D{row}", f.get("count"), align=A_C, fmt="#,##0")
            put(g, f"E{row}", len(f.get("dbcols", [])) or len(cdict.get(name, [])) or None, align=A_C, fmt="#,##0")
        elif o is None:
            put(g, f"D{row}", "미생성", align=A_C)
            put(g, f"E{row}", len(cdict.get(name, [])) or None, align=A_C, fmt="#,##0")
        elif o["type"] == "view":
            put(g, f"D{row}", "(뷰)", align=A_C)
            put(g, f"E{row}", o["cols"], align=A_C, fmt="#,##0")
        else:
            put(g, f"D{row}", o["rows"], align=A_C, fmt="#,##0")
            put(g, f"E{row}", o["cols"], align=A_C, fmt="#,##0")
        role = (td.get("role") or "").strip()
        if name in FILE_SETS:
            role = (role + " ※ 원본 파일(DB 밖) — 행 수는 파서 실측").strip()
        elif o is None:
            role = (role + " ※ 열 사전만 등록, RDS 미생성(2026-09-22)").strip()
        put(g, f"F{row}", role)
        row += 1
    if row - 1 > start:
        g.merge_cells(f"B{start}:B{row - 1}")
    border_range(g, f"B{start}:B{row - 1}")
    put(g, f"B{start}", f"{pfx}\n({row - start})", align=A_C)

g.freeze_panes = "A5"
nrow = row + 1
g.merge_cells(f"A{nrow}:F{nrow}")
cc = g[f"A{nrow}"]
cc.value = ("※ 행 수·열 수는 RDS 실측(raw_ 원본 파일 데이터셋은 파서 실측, DB 밖). 뷰는 행 수 대신 (뷰) 표기. 수집 원본 데이터셋 26종의 컬럼 명세는 앞의 No 시트 참조. "
            "DDL은 db/schema.sql, 열 설명 원천은 db/column_dict.csv.")
cc.font = F_BODY
cc.alignment = A_L
g.row_dimensions[nrow].height = ROW_H

# ══ raw → clean 정제변경 2시트 ═════════════════════════════════
# 원천: RDS information_schema 열 대조(기계적) + db/clean_transform_map.csv
# (raw 열이 clean 의 다른 열로 분해·이동한 것 42건 — 팀원 작성분을 RDS 로 검증해 옮겼다.
#  이름만으로는 알 수 없는 대응이라 이 CSV 가 유일한 근거다. 새 정제 열을 만들면 여기 1행 추가.)
TRANSFORM = collections.defaultdict(list)
_tm_path = ROOT / "db/clean_transform_map.csv"
if _tm_path.exists():
    for r in csv.DictReader(open(_tm_path, encoding="utf-8")):
        TRANSFORM[(r["raw_table"], r["clean_table"])].append(r)

# raw_ ↔ 정제층 짝 + 그 데이터셋의 명세 시트 이름
SHEET_BY_TABLE = {meta[p[4]]["target_table"]: p[0] for p in sheet_plan}
TRACE_COLS = {"row_id", "source_file", "source_row_no", "source_col_no", "loaded_at", "source_url", "fetched_at"}

# 이름 규칙(raw_X → clean_X)으로 안 잡히는 짝. 관세청은 fact_ 가, HS 마스터·명칭은 ref_ 가 정제층이다.
PAIR_OVERRIDE = {"raw_customs_trade": "fact_customs_monthly", "raw_hs_code_master": "ref_hs_code_master", "raw_hs_unit_name": "ref_hs6_name"}

pairs = []
for raw_t in sorted(FACTS):
    tgt = PAIR_OVERRIDE.get(raw_t, "clean_" + raw_t[len("raw_"):])
    if tgt in OBJS:
        pairs.append((SHEET_BY_TABLE.get(raw_t, "-"), raw_t, tgt))
pairs.sort(key=lambda x: x[0])


def rule_where(clean_t):
    """정제 규칙이 적힌 곳. table_dict.source 의 노트북 경로를 쓰고, 없으면 전환 명세 문서."""
    src = (tdict.get(clean_t, {}).get("source") or "")
    m = re.search(r"(notebooks/[\w.\-]+\.ipynb)", src)
    if m and (ROOT / m.group(1)).exists():
        return m.group(1)
    return "docs/reference/clean-conversion-spec-2026-09-18.md"


KIND_NOTE = {
    "이름변경·변환": "raw 열이 정제층에서 다른 열·구조로 대체됐다(대응은 db/clean_transform_map.csv)",
    "동일명·타입 변경": "같은 이름으로 남았고 타입·NULL 허용만 정제했다",
    "동일명 유지": "이름·타입 그대로 옮겼다",
    "raw 메타(원본 추적, 미적재)": "파서가 붙이는 추적 열이라 정제층에는 넣지 않았다(정제층은 raw_row_id = 파서 순번으로 원본 행을 가리킨다)",
    "raw 미적재(업무열)": "현재 화면·분석에 쓰지 않아 정제층에 넣지 않았다. 원본 파일에 보존",
    "파생 추가(정제 전용)": "원본에 없던 파생·정규화·감사 열",
}

detail_rows = []   # (시트, raw_t, clean_t, 유형, raw열, clean열/변경내용, raw타입, clean타입, 비고)
summary_rows = []

# FACTS 는 데이터셋 적재표만 갖고 있어 clean_ 표의 열이 없다 → information_schema 를 한 번 더 읽는다
_conn = pymysql.connect(**dbconf.pymysql_kwargs("etl", connect_timeout=20))
try:
    with _conn.cursor() as _cur:
        _cur.execute(
            "SELECT table_name, column_name, column_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = DATABASE() ORDER BY table_name, ordinal_position"
        )
        ALLCOLS = collections.defaultdict(dict)
        for _t, _c, _ct, _nl in _cur.fetchall():
            ALLCOLS[_t][_c] = (_ct, _nl)
finally:
    _conn.close()

for sheet_nm, raw_t, clean_t in pairs:
    rawc = {dc["name"]: (dc["type"], "YES") for dc in FACTS[raw_t]["dbcols"]}   # 원본 파일 열(파서 형)
    cleanc = ALLCOLS[clean_t]
    moved = {r["raw_column"]: r for r in TRANSFORM.get((raw_t, clean_t), [])}
    desc = {cr["column_name"]: cr["description"] for cr in cdict.get(clean_t, [])}
    desc_raw = {cr["column_name"]: cr["description"] for cr in cdict.get(raw_t, [])}
    n_kind = collections.Counter()
    unloaded_biz = []
    for c, (ct, nl) in rawc.items():
        if c in moved:
            k = "이름변경·변환"
            detail_rows.append((sheet_nm, raw_t, clean_t, k, c, moved[c]["clean_target"], ct,
                                "", moved[c]["note"] or KIND_NOTE[k]))
        elif c in cleanc:
            cct, cnl = cleanc[c]
            diffs = []
            if cct.replace(" ", "") != ct.replace(" ", ""):
                diffs.append("타입 변경")
            if cnl != nl:
                diffs.append(f"NULL 허용 {nl}→{cnl}")
            k = "동일명·타입 변경" if diffs else "동일명 유지"
            note = ((" / ".join(diffs) + " — ") if diffs else "") + (
                desc.get(c) or desc_raw.get(c) or KIND_NOTE[k])
            detail_rows.append((sheet_nm, raw_t, clean_t, k, c, c, ct, cct, note))
        elif c in TRACE_COLS:
            k = "raw 메타(원본 추적, 미적재)"
            detail_rows.append((sheet_nm, raw_t, clean_t, k, c, "", ct, "", KIND_NOTE[k]))
        else:
            k = "raw 미적재(업무열)"
            detail_rows.append((sheet_nm, raw_t, clean_t, k, c, "", ct, "",
                                (desc_raw.get(c) + " — " if desc_raw.get(c) else "") + KIND_NOTE[k]))
            unloaded_biz.append(c)
        n_kind[k] += 1
    for c, (cct, _cnl) in cleanc.items():
        if c in rawc:
            continue
        k = "파생 추가(정제 전용)"
        detail_rows.append((sheet_nm, raw_t, clean_t, k, "", c, "", cct,
                            desc.get(c) or KIND_NOTE[k]))
        n_kind[k] += 1
    summary_rows.append([sheet_nm, raw_t, clean_t, len(rawc), len(cleanc),
                         n_kind["동일명 유지"], n_kind["이름변경·변환"] + n_kind["동일명·타입 변경"],
                         n_kind["파생 추가(정제 전용)"], len(unloaded_biz),
                         ", ".join(unloaded_biz) or "-", rule_where(clean_t)])

# ── 정제변경_요약 ──────────────────────────────────────────────
sm = wb.create_sheet("정제변경_요약")
sm.sheet_view.showGridLines = False
for col, w in {"A": 5.25, "B": 30.0, "C": 32.0, "D": 32.0, "E": 9.0, "F": 9.0,
               "G": 11.0, "H": 11.0, "I": 12.0, "J": 12.0, "K": 46.0, "L": 34.0}.items():
    sm.column_dimensions[col].width = w
for r in (1, 2, 3, 4):
    sm.row_dimensions[r].height = ROW_H
sm.row_dimensions[2].height = 31.5
title_block(sm, "A2:L2", "raw → 정제층 열 대응 요약")
value(sm, "L3", f"RDS 실측: {TODAY}", align=A_R)
sm["L3"].border = Border(left=THIN, top=THIN)
sm_heads = ["No", "명세서 시트", "raw 테이블", "정제 테이블", "raw 열수", "정제 열수",
            "동일명 유지", "이름변경·변환", "파생 추가", "raw 미적재(업무열)",
            "미적재 열 목록", "정제 규칙 위치"]
for i, h in enumerate(sm_heads, start=1):
    put(sm, f"{get_column_letter(i)}4", h, font=F_HEAD, align=A_C, fill=HEAD_FILL)
r = 5
for i, sr in enumerate(summary_rows, start=1):
    sm.row_dimensions[r].height = ROW_H
    put(sm, f"A{r}", i, align=A_C)
    for j, v in enumerate(sr, start=2):
        put(sm, f"{get_column_letter(j)}{r}", v,
            align=A_C if isinstance(v, int) or j in (3, 4) else A_V)
    r += 1
sm.freeze_panes = "A5"
sm.merge_cells(f"A{r + 1}:L{r + 1}")
cc = sm[f"A{r + 1}"]
cc.value = ("※ raw_ = 원본 보존층(전 열 문자열, 수정하지 않음) / clean_·fact_·dim_ = 정제층(노트북·load_db.py 가 채움, 화면·뷰의 원천) "
            "/ ref_ = 기준·라벨 참조표 / v_ = 화면이 읽는 집계 뷰. "
            "「raw 미적재」는 원본 삭제가 아니라 정제층에 넣지 않은 상태이며 raw 원본은 그대로 있다. "
            "열 대조는 RDS information_schema 실측이고, 이름이 바뀐 대응만 db/clean_transform_map.csv 를 쓴다.")
cc.font = F_BODY
cc.alignment = A_L
sm.row_dimensions[r + 1].height = ROW_H

# 위 표는 raw 1개 ↔ 정제 1개 대응만 싣는다. 그 밖의 파생·참조 표를 원천과 함께 따로 밝힌다.
paired = {p[2] for p in pairs} | {p[1] for p in pairs}
others = [t for t in sorted(OBJS)
          if OBJS[t]["type"] == "table" and t not in paired
          and not t.startswith(("meta_", "raw_"))]
r2 = r + 2
sm.merge_cells(f"A{r2}:L{r2}")
put(sm, f"A{r2}", "파생·참조 표(raw 1개 ↔ 정제 1개 대응이 아닌 표)", font=F_HEAD, align=A_L, fill=HEAD_FILL)
sm.row_dimensions[r2].height = ROW_H
r2 += 1
for t in others:
    td = tdict.get(t, {})
    sm.merge_cells(f"A{r2}:C{r2}")
    border_range(sm, f"A{r2}:C{r2}")
    put(sm, f"A{r2}", f"{t} ({OBJS[t]['rows']:,}행)")
    sm.merge_cells(f"D{r2}:L{r2}")
    border_range(sm, f"D{r2}:L{r2}")
    put(sm, f"D{r2}", f"원천: {td.get('source') or '-'} — {td.get('role') or ''}")
    sm.row_dimensions[r2].height = ROW_H
    r2 += 1
# raw 쪽에 정제층 짝이 없는 표
no_pair = [t for t in sorted(OBJS) if t.startswith("raw_") and t not in paired]
if no_pair:
    sm.merge_cells(f"A{r2}:L{r2}")
    c2 = sm[f"A{r2}"]
    parts = [f"{t}(→ {tdict.get(t, {}).get('used_by') or '아직 없음'})" for t in no_pair]
    c2.value = f"※ 정제층 짝이 없는 raw {len(no_pair)}개 — 괄호 안이 대신 쓰는 곳: " + " · ".join(parts)
    c2.font = F_BODY
    c2.alignment = A_L
    sm.row_dimensions[r2].height = ROW_H

# ── 정제변경_상세 ──────────────────────────────────────────────
sd = wb.create_sheet("정제변경_상세")
sd.sheet_view.showGridLines = False
for col, w in {"A": 5.25, "B": 30.0, "C": 30.0, "D": 30.0, "E": 24.0, "F": 26.0,
               "G": 40.0, "H": 16.0, "I": 16.0, "J": 52.0}.items():
    sd.column_dimensions[col].width = w
for r in (1, 2, 3, 4):
    sd.row_dimensions[r].height = ROW_H
sd.row_dimensions[2].height = 31.5
title_block(sd, "A2:J2", "raw → 정제층 열 대응 상세")
value(sd, "J3", f"RDS 실측: {TODAY}", align=A_R)
sd["J3"].border = Border(left=THIN, top=THIN)
sd_heads = ["No", "명세서 시트", "raw 테이블", "정제 테이블", "유형",
            "raw 컬럼", "정제 컬럼", "raw 타입", "정제 타입", "비고"]
for i, h in enumerate(sd_heads, start=1):
    put(sd, f"{get_column_letter(i)}4", h, font=F_HEAD, align=A_C, fill=HEAD_FILL)
KIND_ORDER = ["동일명 유지", "동일명·타입 변경", "이름변경·변환", "파생 추가(정제 전용)",
              "raw 미적재(업무열)", "raw 메타(원본 추적, 미적재)"]
detail_rows.sort(key=lambda x: (x[0], KIND_ORDER.index(x[3]), x[4] or x[5]))
r = 5
for i, dr in enumerate(detail_rows, start=1):
    sd.row_dimensions[r].height = ROW_H
    put(sd, f"A{r}", i, align=A_C)
    for j, v in enumerate(dr, start=2):
        put(sd, f"{get_column_letter(j)}{r}", v, align=A_V if j in (2, 3, 4, 7, 10) else A_C)
    r += 1
sd.freeze_panes = "A5"

kind_tally = collections.Counter(d[3] for d in detail_rows)
print("정제변경: 요약 {}행 · 상세 {}행 {}".format(len(summary_rows), len(detail_rows), dict(kind_tally)))

OUT = pathlib.Path(ARGS.out) if ARGS.out else ROOT / f"docs/report/data/3_데이터수집목록및명세서-{TODAY}.xlsx"
wb.save(OUT)
if DTYPE_DRIFT:
    print(f"[경고] 열 사전 dtype 이 RDS 와 다른 열 {len(DTYPE_DRIFT)}개 — 명세서는 RDS 값을 실었다. db/column_dict.csv 를 고칠 것:")
    for t, c, d, rds in DTYPE_DRIFT:
        print(f"   {t}.{c}: 사전 {d} / RDS {rds}")

print(f"저장: {OUT}  (시트 {len(wb.sheetnames)}개 = 목록 1 + 데이터셋 {len(sheet_plan)} + 참고 1 + 정제변경 2)")
