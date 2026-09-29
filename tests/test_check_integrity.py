"""회귀 검증 — scripts/check_integrity.py 의 시드 해석·값 비교(DB 접속 없음).

실행(저장소 루트): .venv\\Scripts\\python.exe -m unittest discover -s tests -v
2026-09-28 QA D-01(시드의 FSG 60 이 0으로 남아 --ref 때 DB 값을 되돌림)의 재발 방지 장치가 깨지지 않았는지 본다.
"""
from __future__ import annotations

import csv
import datetime as dt
import decimal
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_integrity as ci  # noqa: E402

SAMPLE = """-- 머리 주석 (INSERT INTO 가 들어 있어도 무시)
INSERT IGNORE INTO t_map (token, code) VALUES
  ('서울','11'), ('광주광역시','29'),  -- 줄 끝 주석, 괄호(와) 쉼표, 도 무시
  ('it''s', NULL);

INSERT INTO t_grp (code, name, flag, note) VALUES
  ('60', 'Fiber, Optics (A)', 1, NULL),
  ('61', 'Wire', 0, '비고; 세미콜론')
ON DUPLICATE KEY UPDATE name = VALUES(name);
"""


class ParseSeedTest(unittest.TestCase):
    def test_tables_columns_rows(self):
        out = ci.parse_seed_sql(SAMPLE)
        self.assertEqual(set(out), {"t_map", "t_grp"})
        self.assertEqual(out["t_map"][0], ["token", "code"])
        self.assertEqual(out["t_map"][1], [("서울", "11"), ("광주광역시", "29"), ("it's", None)])
        self.assertEqual(out["t_grp"][1], [("60", "Fiber, Optics (A)", "1", None), ("61", "Wire", "0", "비고; 세미콜론")])

    def test_real_seed_matches_fsg_master_and_m4(self):
        # 실제 시드: ref_fsg 행 수 = fsg_master.csv 행 수, 전자 군급 = 58·59·60(09-21 M4 확정)
        cols, rows = ci.parse_seed_sql((ROOT / "db" / "seed_ref.sql").read_text(encoding="utf-8"))["ref_fsg"]
        with open(ROOT / "data" / "reference" / "fsg_master.csv", encoding="utf-8-sig", newline="") as f:
            n_csv = sum(1 for _ in csv.DictReader(f))
        self.assertEqual(len(rows), n_csv)
        flag = cols.index("is_electronic_group")
        self.assertEqual({r[0] for r in rows if r[flag] == "1"}, {"58", "59", "60"})


class NormTest(unittest.TestCase):
    def test_equivalents(self):
        self.assertIsNone(ci.norm(""))
        self.assertIsNone(ci.norm(None))
        self.assertEqual(ci.norm(decimal.Decimal("12.50")), ci.norm("12.5"))
        self.assertEqual(ci.norm(1), ci.norm("1"))
        self.assertEqual(ci.norm("True"), ci.norm(1))
        self.assertEqual(ci.norm(True), "1")
        self.assertEqual(ci.norm(dt.date(2026, 9, 28)), "2026-09-28")
        self.assertEqual(ci.norm("국방"), "국방")


class DiffRowsTest(unittest.TestCase):
    def test_value_and_membership_differences(self):
        src = [{"code": "58", "flag": "1"}, {"code": "60", "flag": "0"}, {"code": "99", "flag": "0"}]
        db = [{"code": "58", "flag": 1}, {"code": "60", "flag": 1}, {"code": "61", "flag": 0}]
        out = ci.diff_rows("t", ["code"], src, db, ["flag"], "시드")
        self.assertIn("t[99]: 시드에만 있음(DB에 없음)", out)
        self.assertIn("t[61]: DB에만 있음(시드에 없음)", out)
        self.assertIn("t[60].flag: DB 1 ≠ 시드 0", out)   # D-01 유형
        self.assertEqual(len(out), 3)

    def test_no_difference(self):
        rows = [{"code": "58", "flag": "1"}]
        self.assertEqual(ci.diff_rows("t", ["code"], rows, [{"code": "58", "flag": 1}], ["flag"], "시드"), [])


if __name__ == "__main__":
    unittest.main()
