"""dashboard/nav.py 페이지 레지스트리 — DB·Streamlit 실행 컨텍스트 없이 정의만 검사한다.

st.Page 객체는 만들지 않는다(실행 컨텍스트 밖에서는 반쪽 객체가 되므로). 홈 탭 안내의 키는 소스에서 정규식으로 읽는다.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

import nav  # noqa: E402


class TestPageSpecs(unittest.TestCase):
    def test_keys_and_url_paths_unique(self):
        keys = [s.key for s in nav.PAGE_SPECS]
        urls = [s.url_path for s in nav.PAGE_SPECS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(urls.count(""), 1, "기본 페이지(url_path='')는 정확히 하나")

    def test_files_exist(self):
        for s in nav.PAGE_SPECS:
            self.assertTrue((nav.APP / s.file).is_file(), s.file)

    def test_nav_order_covers_registry(self):
        self.assertEqual(set(nav.NAV_ORDER), set(nav.SPEC_BY_KEY), "NAV_ORDER 와 PAGE_SPECS 키가 같아야 한다")
        self.assertEqual(len(nav.NAV_ORDER), len(set(nav.NAV_ORDER)))
        self.assertEqual(nav.NAV_ORDER[0], "home")

    def test_sidebar_items_have_label_and_icon(self):
        # 사이드바(데모 K-Defense 틀)는 PAGE_SPECS 의 label·icon 으로 그린다 — 빈 값이면 메뉴 칸이 비어 보인다
        for s in nav.PAGE_SPECS:
            self.assertTrue(s.label.strip(), s.key)
            self.assertTrue(s.icon.strip(), s.key)

if __name__ == "__main__":
    unittest.main()
