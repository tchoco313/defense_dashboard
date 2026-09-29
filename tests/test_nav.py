"""dashboard/nav.py 페이지 레지스트리 — DB·Streamlit 실행 컨텍스트 없이 정의만 검사한다.

st.Page 객체는 만들지 않는다(실행 컨텍스트 밖에서는 반쪽 객체가 되므로). 블록 목록은 페이지 소스의 zone() 호출에서 읽는다.
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

    def test_menu_items_have_label_icon_and_banner(self):
        # 상단 메뉴 · 왼쪽 메뉴 제목 칸 · 서브 배너(frame.py)는 PAGE_SPECS 의 label · icon · heading · lead 로 그린다 — 빈 값이면 칸이 비어 보인다
        for s in nav.PAGE_SPECS:
            for f in ("label", "icon", "heading", "lead"):
                self.assertTrue(getattr(s, f).strip(), f"{s.key}.{f}")

    def test_gnb_is_nav_order_without_search(self):
        self.assertEqual(nav.GNB_ORDER, tuple(k for k in nav.NAV_ORDER if k != "search"))


class TestSections(unittest.TestCase):
    """왼쪽 메뉴 · 펼침 메뉴의 블록은 페이지 파일의 zone("키", "이름") 글자를 읽어 만든다(nav.sections)."""

    def test_every_zone_call_is_read(self):
        # zone( 호출이 f-string · 변수로 바뀌면 정규식이 놓쳐 메뉴에서 조용히 빠진다 — 호출 수와 읽은 수가 같아야 한다
        for s in nav.PAGE_SPECS:
            src = (nav.APP / s.file).read_text(encoding="utf-8")
            n_calls = src.count("zone(")
            found = [k for k, _ in nav.sections(s.key) if k != "main"]
            self.assertEqual(len(found), n_calls, f"{s.file}: zone( {n_calls}회 · 읽은 블록 {len(found)}개")

    def test_sections_nonempty_and_unique(self):
        for s in nav.PAGE_SPECS:
            keys = [k for k, _ in nav.sections(s.key)]
            self.assertTrue(keys, s.key)
            self.assertEqual(len(keys), len(set(keys)), f"{s.key}: 블록 키 중복 {keys}")

    def test_home_starts_with_main(self):
        self.assertEqual(nav.sections("home")[0], ("main", "Main"))


if __name__ == "__main__":
    unittest.main()
