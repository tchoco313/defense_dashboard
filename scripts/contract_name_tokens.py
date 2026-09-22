"""clean_dapa_contract.contract_name(최종 차수 is_latest_seq=1) 단어 빈도 분포 — class5 키워드 사전 초안의 기초 자료.

접속은 scripts/dbconf.py role="etl"(.env 의 MARIADB_USER=etl_rw, TLS). SELECT 만 하며 DB 를 바꾸지 않는다.
형태소 분석기 없이 re 로만 나눈다(새 패키지 없음):
  접두 코드 제거(앞쪽 괄호 덩어리 반복, 'YY년·YY-… 연도 접두, YY-YY-NNN 번호 접두 — 휴리스틱이라 `(긴급)`·`[장비]` 같은 의미 있는
  접두도 벗겨지므로 벗긴 문자열 상위 30개를 따로 보인다)
  → 구분자 분리 → 숫자/문자 경계 분리 → 행위·수량어(VERB_WORDS, 길이 무관)는 별도 표로 빼고
  → 길이 2 이상·순수 숫자 아님·글자/숫자 포함 토큰만 유니그램·바이그램(인접 쌍, 제거된 토큰 자리에서 끊음)으로 집계.
집계 키는 upper, 표시는 가장 잦은 원문 형태. 원시 빈도 = 출현 횟수, 문서 빈도 = 토큰을 포함한 계약명 수(계약 단위 1행),
물품/용역 = 문서 빈도를 biz_type 으로 나눈 것. 표 정렬은 원시 빈도 ↓, 문서 빈도 ↓, 토큰.
키워드는 후보 선정 근거일 뿐이며(docs/reference/data-cleaning-rules.md §1 #8) 정확도 측정 전에는 class5 를 바꾸지 않는다.

사용:
  python scripts/contract_name_tokens.py                                        # 상위 300, 바이그램은 문서 빈도 2 이상
  python scripts/contract_name_tokens.py --top 500 --min-df 3 --out tokens.md   # 같은 내용을 파일로도 저장(UTF-8)
  python scripts/contract_name_tokens.py --keep-verbs                            # 행위·수량어를 메인 표에 남김
  python scripts/contract_name_tokens.py --rules data/reference/contract_class5_rules.csv
      # 팀원 규칙표(열: rule_id,order,target_col,value,input_col,pattern,negative_pattern,scope,extra_condition)의
      # pattern(Python re, IGNORECASE)을 유니그램 상위 N 토큰에 대조 — 규칙별 걸린 토큰 수·원문 걸린 행 수(규칙 단독,
      # 순서·negative_pattern·scope 미적용)·분류 충돌 토큰(class5 값이 다른 규칙에 함께 걸림)·안 걸리는 토큰. 파일 없으면 경고 1줄.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dbconf  # noqa: E402  접속 설정 단일 지점

if hasattr(sys.stdout, "reconfigure"):  # Jupyter 커널(OutStream)에는 없음
    sys.stdout.reconfigure(encoding="utf-8")

SQL = ("SELECT contract_no, contract_name, biz_type, contract_method_name "
       "FROM clean_dapa_contract WHERE is_latest_seq=1")

# 행위·수량어 — 메인 표에서 빼고 별도 표(R4 negative_pattern 참고용). 완전 일치만(외주정비용역 같은 붙은 말은 안 걸림).
VERB_WORDS = ("구매", "제조", "납품", "설치", "용역", "임차", "외주정비", "정비", "수리", "교체", "공사", "제작",
              "등", "종", "개", "식", "대", "사업", "계약", "년", "분기", "차")
VERB_KEYS = {w.upper() for w in VERB_WORDS}

# 접두 제거 휴리스틱(앞에서부터 맞는 것을 반복 적용)
PREFIX_PATTERNS = (
    ("괄호", re.compile(r"^\s*[\(\[（【][^\)\]）】]{1,20}[\)\]）】]\s*")),
    ("연도", re.compile(r"^'?\d{2}[-년]\S*\s*")),
    ("번호", re.compile(r"^\d{2}-\d{2}-\d{3}\s*")),
)
SPLIT_RE = re.compile(r"[\s\(\)\[\]（）【】,·ㆍ/\-–—~:'\"‘’“”]+")
BOUNDARY_RE = re.compile(r"(?<=\d)(?=\D)|(?<=\D)(?=\d)")  # 숫자/문자 경계
ALNUM_RE = re.compile(r"[^\W_]")  # 글자·숫자가 하나라도 있는지
BIZ_TYPES = ("물품", "용역")


def strip_prefix(name: str) -> tuple[str, list[str]]:
    """앞쪽 접두를 반복 제거하고 (본문, 벗겨낸 접두 목록)을 돌려준다."""
    removed: list[str] = []
    s = name
    while True:
        for _kind, pat in PREFIX_PATTERNS:
            m = pat.match(s)
            if m:
                removed.append(m.group(0).strip())
                s = s[m.end():]
                break
        else:
            return s, removed


def tokenize(text: str) -> list[str]:
    """구분자로 나눈 뒤 숫자/문자 경계에서 다시 나눈 원시 토큰(필터 전)."""
    out: list[str] = []
    for piece in SPLIT_RE.split(text):
        if piece:
            out.extend(p for p in BOUNDARY_RE.split(piece) if p)
    return out


def classify(tok: str, keep_verbs: bool) -> str:
    """'verb'(행위·수량어, 길이 무관) | 'drop'(1자·순수 숫자·기호만) | 'keep'"""
    if not keep_verbs and tok.upper() in VERB_KEYS:
        return "verb"
    if len(tok) < 2 or tok.isdigit() or not ALNUM_RE.search(tok):
        return "drop"
    return "keep"


def md_cell(v) -> str:
    return str(v).replace("|", "\\|")


def md_table(headers: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(md_cell(c) for c in r) + " |" for r in rows]
    return lines


def fmt(n: int) -> str:
    return f"{n:,}"


class Stats:
    """유니그램·바이그램·행위어·접두 집계."""

    def __init__(self) -> None:
        self.raw: Counter = Counter()
        self.df: Counter = Counter()
        self.df_by: dict[str, Counter] = defaultdict(Counter)
        self.forms: dict[str, Counter] = defaultdict(Counter)
        self.bi_raw: Counter = Counter()
        self.bi_df: Counter = Counter()
        self.bi_df_by: dict[str, Counter] = defaultdict(Counter)
        self.verb_raw: Counter = Counter()
        self.verb_df: Counter = Counter()
        self.verb_df_by: dict[str, Counter] = defaultdict(Counter)
        self.prefix: Counter = Counter()
        self.names: list[str] = []  # 계약명 원문(빈 값 제외) — --rules 의 원문 행 단위 대조용
        self.rows = 0
        self.rows_empty_name = 0
        self.rows_with_prefix = 0
        self.biz: Counter = Counter()
        self.n_raw_tokens = 0
        self.n_verb_tokens = 0
        self.n_dropped = 0
        self.n_kept = 0
        self.n_bigrams = 0

    def display(self, key: str) -> str:
        return self.forms[key].most_common(1)[0][0]

    def add_row(self, name: str | None, biz: str, keep_verbs: bool) -> None:
        self.rows += 1
        self.biz[biz] += 1
        if not name or not name.strip():
            self.rows_empty_name += 1
            return
        self.names.append(name)
        body, removed = strip_prefix(name)
        if removed:
            self.rows_with_prefix += 1
            self.prefix.update(removed)
        toks = tokenize(body)
        self.n_raw_tokens += len(toks)
        seq: list[str | None] = []
        seen: set[str] = set()
        seen_verb: set[str] = set()
        for t in toks:
            kind = classify(t, keep_verbs)
            if kind == "verb":
                self.n_verb_tokens += 1
                self.verb_raw[t.upper()] += 1
                seen_verb.add(t.upper())
                seq.append(None)
            elif kind == "drop":
                self.n_dropped += 1
                seq.append(None)
            else:
                self.n_kept += 1
                k = t.upper()
                self.raw[k] += 1
                self.forms[k][t] += 1
                seen.add(k)
                seq.append(k)
        for k in seen:
            self.df[k] += 1
            self.df_by[biz][k] += 1
        for k in seen_verb:
            self.verb_df[k] += 1
            self.verb_df_by[biz][k] += 1
        seen_bi: set[tuple[str, str]] = set()
        for a, b in zip(seq, seq[1:]):
            if a and b:  # 제거된 토큰 자리에서 끊는다(건너뛰어 붙이지 않음)
                self.n_bigrams += 1
                self.bi_raw[(a, b)] += 1
                seen_bi.add((a, b))
        for bk in seen_bi:
            self.bi_df[bk] += 1
            self.bi_df_by[biz][bk] += 1


def ranked(raw: Counter, df: Counter, keys) -> list:
    return sorted(keys, key=lambda k: (-raw[k], -df[k], str(k)))


def build_report(st: Stats, args, rules_path: Path | None) -> list[str]:
    L: list[str] = []
    L.append(f"# contract_name 토큰 빈도 — clean_dapa_contract is_latest_seq=1 (top={args.top}, min-df={args.min_df}, "
             f"keep-verbs={'on' if args.keep_verbs else 'off'})")
    L.append("")

    # ① 입력 요약
    L.append("## ① 입력 요약")
    L.append("")
    uni_keys = ranked(st.raw, st.df, st.raw.keys())
    bi_keys_all = ranked(st.bi_raw, st.bi_df, st.bi_raw.keys())
    bi_keys = [k for k in bi_keys_all if st.bi_df[k] >= args.min_df]
    rows = [
        ["행 수(계약 단위, is_latest_seq=1)", fmt(st.rows)],
        ["물품 / 용역", " / ".join(f"{b} {fmt(st.biz.get(b, 0))}" for b in BIZ_TYPES)
         + ("" if set(st.biz) <= set(BIZ_TYPES) else f" / 기타 {fmt(sum(v for k, v in st.biz.items() if k not in BIZ_TYPES))}")],
        ["계약명 NULL·빈값 행", fmt(st.rows_empty_name)],
        ["접두 제거된 행 수", fmt(st.rows_with_prefix)],
        ["벗겨낸 접두 조각 수 / 고유", f"{fmt(sum(st.prefix.values()))} / {fmt(len(st.prefix))}"],
        ["원시 토큰 수(구분자·숫자경계 분리 직후)", fmt(st.n_raw_tokens)],
        ["행위·수량어 토큰 수(별도 표)", fmt(st.n_verb_tokens)],
        ["제외 토큰 수(1자·순수 숫자·기호만)", fmt(st.n_dropped)],
        ["집계 토큰 수(유니그램)", fmt(st.n_kept)],
        ["고유 토큰 수", fmt(len(st.raw))],
        ["바이그램 수 / 고유 / 문서 빈도≥min-df 고유", f"{fmt(st.n_bigrams)} / {fmt(len(st.bi_raw))} / {fmt(len(bi_keys))}"],
    ]
    L += md_table(["항목", "값"], rows)
    L.append("")

    # ② 접두 상위 30
    L.append("## ② 벗겨낸 접두 상위 30 (손실 주의 — 의미 있는 접두도 섞임)")
    L.append("")
    L += md_table(["순위", "접두", "빈도"],
                  [[i, p, fmt(n)] for i, (p, n) in enumerate(st.prefix.most_common(30), 1)])
    L.append("")

    # ③ 행위·수량어
    L.append("## ③ 행위·수량어 빈도 (메인 표 제외분, R4 negative_pattern 참고)")
    L.append("")
    if args.keep_verbs:
        L.append("`--keep-verbs` 로 실행 — 행위·수량어를 메인 표에 남겼으므로 이 표는 비어 있다.")
    else:
        vrows = []
        for w in VERB_WORDS:
            k = w.upper()
            vrows.append([w, fmt(st.verb_raw[k]), fmt(st.verb_df[k])]
                         + [fmt(st.verb_df_by[b][k]) for b in BIZ_TYPES])
        vrows.sort(key=lambda r: -int(r[1].replace(",", "")))
        L += md_table(["단어", "원시 빈도", "문서 빈도", *BIZ_TYPES], vrows)
    L.append("")

    # ④ 유니그램
    top_uni = uni_keys[: args.top]
    L.append(f"## ④ 유니그램 상위 {len(top_uni)} (원시 빈도 순)")
    L.append("")
    L += md_table(["순위", "토큰", "원시 빈도", "문서 빈도", *BIZ_TYPES],
                  [[i, st.display(k), fmt(st.raw[k]), fmt(st.df[k])] + [fmt(st.df_by[b][k]) for b in BIZ_TYPES]
                   for i, k in enumerate(top_uni, 1)])
    L.append("")

    # ⑤ 바이그램
    top_bi = bi_keys[: args.top]
    L.append(f"## ⑤ 바이그램 상위 {len(top_bi)} (인접 토큰 쌍, 문서 빈도 ≥ {args.min_df}, 원시 빈도 순)")
    L.append("")
    L += md_table(["순위", "바이그램", "원시 빈도", "문서 빈도", *BIZ_TYPES],
                  [[i, f"{st.display(a)} {st.display(b)}", fmt(st.bi_raw[(a, b)]), fmt(st.bi_df[(a, b)])]
                   + [fmt(st.bi_df_by[t][(a, b)]) for t in BIZ_TYPES]
                   for i, (a, b) in enumerate(top_bi, 1)])
    L.append("")

    # ⑥ 규칙표 커버리지
    if rules_path is not None:
        L += rules_coverage(st, top_uni, rules_path)
    return L


def read_rules(path: Path) -> tuple[pd.DataFrame, str]:
    """utf-8-sig 로 읽고 디코딩 실패 시 cp949 로 한 번 더(둘 다 실패하면 예외 그대로)."""
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna(""), "utf-8-sig"
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, encoding="cp949").fillna(""), "cp949"


def rules_coverage(st: Stats, top_uni: list[str], path: Path) -> list[str]:
    rules, enc = read_rules(path)
    L = [f"## ⑥ 규칙표 커버리지 — `{path}` ({enc}, {len(rules)}행) × 유니그램 상위 {len(top_uni)}", ""]
    need = {"rule_id", "pattern"}
    missing = need - set(rules.columns)
    if missing:
        raise SystemExit(f"rules 파일에 필요한 열이 없습니다: {sorted(missing)} (있는 열: {list(rules.columns)})")
    tokens = [(k, st.display(k)) for k in top_uni]
    n_names = len(st.names)
    hit_by_token: dict[str, list[str]] = defaultdict(list)
    rule_info: dict[str, tuple[str, str, int]] = {}  # rule_id → (target_col, value, order)
    per_rule: list[list] = []
    skipped: list[str] = []
    for r in rules.itertuples(index=False):
        rid = str(getattr(r, "rule_id", ""))
        pattern = getattr(r, "pattern", "").strip()
        input_col = getattr(r, "input_col", "").strip() if "input_col" in rules.columns else ""
        if input_col and "contract_name" not in input_col:
            skipped.append(f"{rid}(input_col={input_col})")
            continue
        if not pattern:
            skipped.append(f"{rid}(pattern 공란)")
            continue
        rx = re.compile(pattern, re.IGNORECASE)  # 잘못된 정규식은 그대로 예외
        hits = [disp for k, disp in tokens if rx.search(disp)]
        for h in hits:
            hit_by_token[h].append(rid)
        order_s = str(getattr(r, "order", "")).strip() if "order" in rules.columns else ""
        rule_info[rid] = (str(getattr(r, "target_col", "")), str(getattr(r, "value", "")),
                          int(order_s) if order_s.isdigit() else 10**6)
        # 원문 행 단위: pattern 을 계약명 원문에 단순 대조(첫 일치 순서·negative_pattern·scope 미적용 → 노트북 apply_class5 재현 아님)
        n_rows = sum(1 for nm in st.names if rx.search(nm))
        per_rule.append([rid, rule_info[rid][0], rule_info[rid][1], pattern, fmt(len(hits)),
                         fmt(n_rows), f"{100 * n_rows / n_names:.1f}" if n_names else "-",
                         ", ".join(hits[:10]) + (" …" if len(hits) > 10 else "")])
    L.append(f"### 규칙별 걸린 토큰 수 · 원문 걸린 행 수 (원문 {fmt(n_names)}행, 규칙 단독 대조 — 순서·negative_pattern·scope 미적용)")
    L.append("")
    L += md_table(["rule_id", "target_col", "value", "pattern", "걸린 토큰 수", "원문 걸린 행 수", "원문 비율(%)", "예시(≤10)"],
                  per_rule)
    if skipped:
        L.append("")
        L.append(f"건너뛴 규칙 {len(skipped)}: " + "; ".join(skipped))
    L.append("")
    # 분류 충돌: 같은 토큰이 target_col=class5 이면서 value 가 다른 규칙에 함께 걸림 → order 가 가장 앞선 규칙이 확정
    conflicts: list[list] = []
    for k, d in tokens:
        c5 = [(rule_info[rid][2], rid, rule_info[rid][1]) for rid in hit_by_token.get(d, ()) if rule_info[rid][0] == "class5"]
        if len({v for _, _, v in c5}) > 1:
            c5.sort()
            conflicts.append([d, fmt(st.raw[k]), fmt(st.df[k]),
                              ", ".join(f"{rid}→{v}" for _, rid, v in c5), f"{c5[0][1]}→{c5[0][2]}"])
    L.append(f"### 분류 충돌 토큰 {len(conflicts)} (class5 값이 다른 규칙에 함께 걸림; 확정 = order 가 앞선 규칙)")
    L.append("")
    L += md_table(["토큰", "원시 빈도", "문서 빈도", "걸린 class5 규칙", "확정(order 순)"], conflicts)
    L.append("")
    unmatched = [(k, d) for k, d in tokens if d not in hit_by_token]
    unmatched.sort(key=lambda kd: (-st.df[kd[0]], -st.raw[kd[0]], kd[1]))
    L.append(f"### 어느 규칙에도 안 걸리는 토큰 {len(unmatched)} / {len(tokens)} (문서 빈도 순)")
    L.append("")
    L += md_table(["순위", "토큰", "원시 빈도", "문서 빈도", *BIZ_TYPES],
                  [[i, d, fmt(st.raw[k]), fmt(st.df[k])] + [fmt(st.df_by[b][k]) for b in BIZ_TYPES]
                   for i, (k, d) in enumerate(unmatched, 1)])
    L.append("")
    return L


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=300, help="유니그램·바이그램 상위 N (기본 300)")
    ap.add_argument("--min-df", type=int, default=2, help="바이그램 문서 빈도 하한 (기본 2)")
    ap.add_argument("--keep-verbs", action="store_true", help="행위·수량어를 메인 표에 남긴다")
    ap.add_argument("--out", type=Path, default=None, help="같은 내용을 이 경로에 저장(UTF-8)")
    ap.add_argument("--rules", type=Path, default=None, help="팀원 규칙표 CSV — pattern 커버리지 검사(없으면 경고 1줄)")
    args = ap.parse_args()

    rules_path: Path | None = None
    if args.rules is not None:
        if args.rules.exists():
            rules_path = args.rules
        else:
            print(f"[경고] rules 파일 없음: {args.rules}")

    print(dbconf.describe("etl"))
    conn = pymysql.connect(**dbconf.pymysql_kwargs("etl"))
    try:
        cur = conn.cursor()
        cur.execute(SQL)
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()

    st = Stats()
    for r in df.itertuples(index=False):
        st.add_row(r.contract_name, r.biz_type, args.keep_verbs)

    lines = build_report(st, args, rules_path)
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"[저장] {args.out}")


if __name__ == "__main__":
    main()
