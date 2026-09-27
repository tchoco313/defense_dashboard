"""app/live.py 순수 함수 — 관세청 응답 파싱 · 조회 기간 · 최신 월 판정. 네트워크 · streamlit 없이 돈다.

실행(저장소 루트): .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))   # app/ 은 패키지가 아니다

import live  # noqa: E402

XML = """<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
<body><items>
<item><year>2026.08</year><statCd>US</statCd><hsCd>8542311000</hsCd><impDlr>100</impDlr><expDlr>5</expDlr></item>
<item><year>2026.08</year><statCd>CN</statCd><hsCd>8542311000</hsCd><impDlr>50</impDlr><expDlr>0</expDlr></item>
<item><year>2026.09</year><statCd>US</statCd><hsCd>8542312000</hsCd><impDlr>30</impDlr><expDlr>1</expDlr></item>
<item><year>총계</year><statCd>-</statCd><hsCd>-</hsCd><impDlr>180</impDlr><expDlr>6</expDlr></item>
</items></body></response>"""


class ParseTest(unittest.TestCase):
    def test_monthly_rows_only(self):
        rows = live.parse_items(XML)
        self.assertEqual(len(rows), 3)                       # 총계행 제외
        self.assertEqual(rows[0]["yyyymm"], "202608")
        self.assertEqual(rows[2]["imp"], 30.0)

    def test_monthly_totals(self):
        t = live.monthly_totals(live.parse_items(XML)).set_index("yyyymm")
        self.assertEqual(t.loc["202608", "imp"], 150.0)
        self.assertEqual(t.loc["202609", "exp"], 1.0)

    def test_empty_items(self):
        xml = "<response><header><resultCode>00</resultCode></header><body><items/></body></response>"
        self.assertEqual(live.parse_items(xml), [])
        self.assertTrue(live.monthly_totals([]).empty)

    def test_error_code_raises_without_detail(self):
        xml = "<response><header><resultCode>30</resultCode><resultMsg>SERVICE KEY IS NOT REGISTERED</resultMsg></header></response>"
        with self.assertRaises(RuntimeError) as cm:
            live.parse_items(xml)
        self.assertEqual(str(cm.exception), "resultCode=30")

    def test_entity_expansion_blocked(self):
        bomb = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "x">]><response>&a;</response>'
        with self.assertRaises(Exception):
            live.parse_items(bomb)


class WindowClassifyTest(unittest.TestCase):
    def test_window(self):
        self.assertEqual(live.month_window("202608", "202609"), ("202608", "202609"))
        self.assertEqual(live.month_window("202401", "202609"), ("202510", "202609"))   # 1년 이내로 자른다
        self.assertIsNone(live.month_window("202610", "202609"))

    def test_classify(self):
        self.assertEqual(live.classify("202608", ["202608"]), ("same", "202608"))
        self.assertEqual(live.classify("202608", ["202608", "202609"]), ("newer", "202609"))
        self.assertEqual(live.classify("202608", []), ("unknown", None))

    def test_line_text_has_no_forbidden_words(self):
        for s in ("same", "newer", "unknown", "nokey", "failed"):
            txt = live.line_text({"state": s, "db_latest": "202608", "src_latest": "202609", "checked_at": "09-24 14:05",
                                  "error": "ConnectTimeout"})
            for w in ("실시간", "모니터링", "감시"):
                self.assertNotIn(w, txt)


if __name__ == "__main__":
    unittest.main()
