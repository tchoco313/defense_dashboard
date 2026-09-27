"""회귀 검증 — app/metrics.py(집중도·기간·건수 상태), app/ui.py(기간 선택지·CSV 머리줄), app/db.py(조회 실패 경로).

DB 접속 없이 돈다. 실행(저장소 루트): .venv\\Scripts\\python.exe -m unittest discover -s tests -v
기대값은 합성 데이터에서만 만든다(실측 건수 1,819·2,267 같은 과거 기록을 하드코딩하지 않는다).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))   # app/ 은 패키지가 아니다

import metrics  # noqa: E402
from metrics import concentration, count_state, period_years  # noqa: E402


def rows(*items):
    """(hs6, stat_cd, imp, exp, year) 튜플들 → DataFrame."""
    return pd.DataFrame([dict(hs6=h, stat_cd=c, imp_dlr=i, exp_dlr=e, year=y) for h, c, i, e, y in items])


class ConcentrationTest(unittest.TestCase):
    def test_basic_two_countries(self):
        out = concentration(rows(("A", "US", 60, 0, 2025), ("A", "CN", 40, 0, 2025)), "imp_dlr").set_index("hs6")
        self.assertEqual(out.loc["A", "total"], 100)
        self.assertEqual(out.loc["A", "top1_stat_cd"], "US")
        self.assertAlmostEqual(out.loc["A", "top1_share"], 0.6)
        self.assertAlmostEqual(out.loc["A", "hhi"], 60 ** 2 + 40 ** 2)   # 5,200
        self.assertEqual(out.loc["A", "country_count"], 2)

    def test_sums_years_per_country_before_share(self):
        # 국가별로 두 해를 먼저 합산(US 30+30=60, CN 40) → 점유율은 합산 뒤 계산
        df = rows(("A", "US", 30, 0, 2024), ("A", "US", 30, 0, 2025), ("A", "CN", 40, 0, 2025))
        out = concentration(df, "imp_dlr").set_index("hs6")
        self.assertAlmostEqual(out.loc["A", "top1_share"], 0.6)
        self.assertAlmostEqual(out.loc["A", "hhi"], 5200)
        self.assertEqual(out.loc["A", "country_count"], 2)

    def test_zero_and_export_only_countries_excluded(self):
        # JP 는 수입 0(수출만) → 국가 수·HHI 에서 제외. 단일 국가면 HHI 10,000
        df = rows(("A", "US", 100, 0, 2025), ("A", "JP", 0, 500, 2025))
        out = concentration(df, "imp_dlr").set_index("hs6")
        self.assertEqual(out.loc["A", "country_count"], 1)
        self.assertAlmostEqual(out.loc["A", "hhi"], 10_000)
        self.assertEqual(out.loc["A", "top1_stat_cd"], "US")

    def test_hs6_with_no_positive_value_is_absent(self):
        df = rows(("A", "US", 100, 0, 2025), ("B", "US", 0, 10, 2025))
        out = concentration(df, "imp_dlr")
        self.assertEqual(out["hs6"].tolist(), ["A"])

    def test_empty_input(self):
        out = concentration(pd.DataFrame(columns=["hs6", "stat_cd", "imp_dlr"]), "imp_dlr")
        self.assertTrue(out.empty)
        self.assertEqual(list(out.columns), metrics.CONC_COLS)

    def test_tie_break_matches_sql_view(self):
        # 뷰: RANK() … ORDER BY imp_dlr DESC + MAX(stat_cd) → 동률이면 국가코드가 큰 쪽
        df = rows(("A", "CN", 50, 0, 2025), ("A", "US", 50, 0, 2025))
        out = concentration(df, "imp_dlr").set_index("hs6")
        self.assertEqual(out.loc["A", "top1_stat_cd"], "US")
        self.assertAlmostEqual(out.loc["A", "top1_share"], 0.5)

    def test_nan_values_ignored(self):
        df = rows(("A", "US", 100, 0, 2025), ("A", "DE", float("nan"), 0, 2025))
        out = concentration(df, "imp_dlr").set_index("hs6")
        self.assertEqual(out.loc["A", "country_count"], 1)
        self.assertAlmostEqual(out.loc["A", "total"], 100)

    def test_top3_share(self):
        # 4개국 40·30·20·10 → 상위 3 = 0.9, 국가 2개면 있는 만큼(1.0)
        df = rows(("A", "US", 40, 0, 2025), ("A", "CN", 30, 0, 2025), ("A", "JP", 20, 0, 2025), ("A", "DE", 10, 0, 2025),
                  ("B", "US", 70, 0, 2025), ("B", "CN", 30, 0, 2025))
        out = concentration(df, "imp_dlr").set_index("hs6")
        self.assertAlmostEqual(out.loc["A", "top3_share"], 0.9)
        self.assertAlmostEqual(out.loc["B", "top3_share"], 1.0)

    def test_top3_tie_at_third_counts_three_only(self):
        # 3위 동률(JP·DE 각 10)이어도 3개만 — 0.8 + 0.1
        df = rows(("A", "US", 50, 0, 2025), ("A", "CN", 30, 0, 2025), ("A", "JP", 10, 0, 2025), ("A", "DE", 10, 0, 2025))
        out = concentration(df, "imp_dlr").set_index("hs6")
        self.assertAlmostEqual(out.loc["A", "top3_share"], 0.9)

    def test_export_axis_uses_value_col(self):
        df = rows(("A", "US", 0, 70, 2025), ("A", "CN", 0, 30, 2025), ("A", "JP", 999, 0, 2025))
        out = concentration(df, "exp_dlr").set_index("hs6")
        self.assertEqual(out.loc["A", "country_count"], 2)
        self.assertAlmostEqual(out.loc["A", "hhi"], 70 ** 2 + 30 ** 2)


class PeriodYearsTest(unittest.TestCase):
    def test_ten_full_years(self):
        p = period_years(range(2016, 2026))
        self.assertEqual(p["base"], [2025])
        self.assertEqual(p["recent5"], [2021, 2022, 2023, 2024, 2025])
        self.assertEqual(p["all"], list(range(2016, 2026)))

    def test_recent5_clamped_to_first_year(self):
        p = period_years([2023, 2024, 2025])
        self.assertEqual(p["recent5"], [2023, 2024, 2025])

    def test_empty_returns_empty_dict(self):
        self.assertEqual(period_years([]), {})

    def test_gap_years_not_filled(self):
        # 연속 범위가 아니라 실제 있는 완결 연도만(중간 부분연도·결측 연도는 들어가지 않는다)
        p = period_years([2016, 2017, 2019])
        self.assertEqual(p["all"], [2016, 2017, 2019])
        self.assertEqual(p["recent5"], [2016, 2017, 2019])

    def test_numpy_ints_and_duplicates(self):
        p = period_years(pd.Series([2025, 2024, 2025]).unique())
        self.assertEqual(p["base"], [2025])
        self.assertEqual(p["all"], [2024, 2025])


class PeriodOptionsTest(unittest.TestCase):
    def test_labels(self):
        from ui import period_options
        opts = period_options([2016, 2017, 2025])
        self.assertEqual(list(opts), ["2025 기준 연도", "최근 5년", "전체 2016~"])
        self.assertEqual(opts["최근 5년"], [2025])
        self.assertEqual(period_options([]), {})


class CountStateTest(unittest.TestCase):
    def test_failed(self):
        self.assertEqual(count_state(None, "OperationalError", "n"), ("failed", None))
        self.assertEqual(count_state(pd.DataFrame({"n": [3]}), "ProgrammingError", "n"), ("failed", None))

    def test_unloaded_vs_zero_vs_ok(self):
        self.assertEqual(count_state(pd.DataFrame({"n": [0], "n_all": [0]}), None, "n", "n_all"), ("unloaded", 0))
        self.assertEqual(count_state(pd.DataFrame({"n": [None], "n_all": [100]}), None, "n", "n_all"), ("zero", 0))
        self.assertEqual(count_state(pd.DataFrame({"n": [0], "n_all": [100]}), None, "n", "n_all"), ("zero", 0))
        self.assertEqual(count_state(pd.DataFrame({"n": [7.0], "n_all": [100]}), None, "n", "n_all"), ("ok", 7))

    def test_without_total_col(self):
        self.assertEqual(count_state(pd.DataFrame(columns=["n"]), None, "n"), ("unloaded", 0))
        self.assertEqual(count_state(pd.DataFrame({"n": [float("nan")]}), None, "n"), ("unloaded", 0))
        self.assertEqual(count_state(pd.DataFrame({"n": [12]}), None, "n"), ("ok", 12))


class CsvHeaderTest(unittest.TestCase):
    def test_lines(self):
        from ui import csv_header
        stamp = {"period": "2016.01~2026.08", "has_period": True, "loaded": "2026-09-18", "today": "2026-09-20", "error": None}
        head = csv_header("기간 2025", "관세청", [("관세청 수출입", stamp, None)], extra="HHI = 기간 합계")
        lines = head.rstrip("\n").split("\n")
        self.assertEqual(lines[0], "# 조건: 기간 2025")
        self.assertEqual(lines[2], "# 자료 기간(관세청 수출입): 2016.01~2026.08")   # DB 적재일은 넣지 않는다(보안)
        self.assertEqual(lines[3], "# 내려받은 날: 2026-09-20")
        self.assertEqual(lines[4], "# HHI = 기간 합계")

    def test_failed_stamp_and_period_override(self):
        from ui import csv_header
        bad = {"period": "기준일 미표기", "has_period": False, "loaded": None, "today": "2026-09-20", "error": "OperationalError"}
        ok = {"period": "2016.01~2026.12 (부분)", "has_period": True, "loaded": "2026-09-18", "today": "2026-09-20", "error": None}
        head = csv_header("c", "s", [("국외 조달계획", ok, "요구연도 2016~2026"), ("국산화개발품목", bad, None)])
        self.assertIn("# 자료 기간(국외 조달계획): 요구연도 2016~2026", head)
        self.assertIn("# 자료 기간(국산화개발품목): —(조회 실패)", head)
        self.assertNotIn("DB 적재", head)

    def test_source_hides_db_internals(self):
        # 화면 · PNG · CSV 출처에는 기관 · 데이터명 · 기간만 — DB 표 · 뷰 이름과 적재일은 걸러진다(2026-09-24 사용자)
        from ui import csv_header
        stamp = {"period": "2016.01~2026.08", "has_period": True, "loaded": "2026-09-18", "today": "2026-09-20", "error": None}
        head = csv_header("c", "관세청 수출입실적(15100475) → 팀 DB fact_customs_monthly → v_import_hs6_year · DB 적재 2026-09-18",
                          [("관세청 수출입", stamp, None)], extra="계약 = clean_dapa_contract · 유찰률 = 공고 키 기준")
        for bad in ("fact_customs_monthly", "v_import_hs6_year", "clean_dapa_contract", "팀 DB", "DB 적재"):
            self.assertNotIn(bad, head)
        self.assertIn("# 출처: 관세청 수출입실적(15100475)", head)


class DbFailurePathTest(unittest.TestCase):
    """db.query 를 가짜로 바꿔 조회 실패·복구 경로만 본다(접속 없음). 오류 문자열에 호스트·비밀번호가 없어야 한다."""

    def setUp(self):
        import db
        self.db = db
        self._orig = db.query

    def tearDown(self):
        self.db.query = self._orig

    def test_try_query_returns_class_name_only(self):
        from sqlalchemy.exc import OperationalError

        def boom(sql, params=None):
            raise OperationalError("SELECT 1", {}, Exception("(2003, \"Can't connect to MySQL server on 'secret-host:3306'\")"))
        self.db.query = boom
        df, err = self.db.try_query("SELECT 1")
        self.assertIsNone(df)
        self.assertEqual(err, "Exception")          # e.orig 의 클래스명
        self.assertNotIn("secret-host", err)
        self.assertIsNone(self.db.safe_query("SELECT 1"))

    def test_data_stamp_on_failure_and_recovery(self):
        calls = {"n": 0}

        def flaky(sql, params=None):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise pd.errors.DatabaseError("Execution failed on sql")
            if "yyyymm" in sql:
                return pd.DataFrame({"s": ["201601"], "e": ["202608"]})
            return pd.DataFrame({"d": [pd.Timestamp("2026-09-18").date()]})
        self.db.query = flaky
        s1 = self.db.data_stamp("customs_all", "fact_customs_monthly")
        self.assertFalse(s1["has_period"])
        self.assertEqual(s1["error"], "DatabaseError")
        self.assertIsNone(s1["loaded"])
        s2 = self.db.data_stamp("customs_all", "fact_customs_monthly")   # 캐시가 없으므로 다음 호출이 곧 재시도
        self.assertEqual(s2["period"], "2016.01~2026.08")
        self.assertEqual(s2["loaded"], "2026-09-18")
        self.assertIsNone(s2["error"])

    def test_data_stamp_non_customs_uses_meta_dataset(self):
        def fake(sql, params=None):
            if "meta_dataset" in sql:
                return pd.DataFrame({"period_start": [pd.Timestamp("2016-01-01").date()],
                                     "period_end": [pd.Timestamp("2026-12-31").date()], "is_partial_period": [1]})
            return pd.DataFrame({"d": [None]})
        self.db.query = fake
        s = self.db.data_stamp("dapa_overseas_plan_api", "clean_dapa_overseas_plan_api")
        self.assertEqual(s["period"], "2016.01~2026.12 (부분)")
        self.assertIsNone(s["loaded"])


if __name__ == "__main__":
    unittest.main()
