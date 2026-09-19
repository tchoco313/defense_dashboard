-- ============================================================================
-- alter_2026-09-19_drop_unused.sql — 미사용 테이블 2개 삭제 (2026-09-19, 사용자 결정)
-- ============================================================================
-- 배경: 사용자 지시 "중복되거나 사용되지 않을 테이블은 삭제". RDS 뷰 의존성(information_schema.view_table_usage)
--       + app/·notebooks/·scripts/·docs/db/table-guide.md §2·dashboard-scope·alter 참조를 전수 집계해 후보를 뽑고
--       사용자가 아래 2개를 골랐다(보고용 뷰 5개는 삭제하지 않고 docs/db/report-views.md에 목록으로 정리).
--
--   1) clean_kdsis_nsn_ref — 225,635행. NSN × CAGE × 참조번호 고유 목록(2026-09-17 SQL 파생).
--      뷰·앱·노트북·화면 문서 참조 0. 필요한 집계(ref_count·cage_count)는 clean_kdsis_nsn에 이미 있고,
--      "CAGE→국가 판별은 하지 않는다"(table-guide §3-5). 원본 raw_kdsis_nsn(228,027)이 남아 재생성 가능.
--   2) test_table — 사용자가 직접 만든 임시 표(id·name·age, 4행). 담당분배 명세 §9 삭제 대상. 2026-09-19 사용자 삭제 승인.
--
-- 함께 정리: meta_column_dict의 clean_kdsis_nsn_ref 행 삭제(test_table은 미등재). meta_load_log의 clean_kdsis_nsn_ref
--            기록(2026-09-17 적재 이력)은 **지우지 않는다**(적재 이력은 사실 기록).
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-19_drop_unused.sql   (admin, 재실행 안전)
-- 정본 반영: db/schema.sql에서 두 표의 CREATE/DROP 목록 제거, db/column_dict.csv에서 clean_kdsis_nsn_ref 행 제거,
--            scripts/load_db.py REF_EXPECTED(meta_column_dict) 갱신, table-guide §3-5·data-cleaning-rules §2-14·schema-design §7 기록.
-- 되돌리기: clean_kdsis_nsn_ref는 db/alter_2026-09-17_kdsis_nsn.sql의 INSERT…SELECT로 raw에서 재생성. test_table은 복구하지 않는다.
-- ============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 삭제 전 확인(주석) — 의존성 0이어야 한다
-- SELECT COUNT(*) FROM information_schema.view_table_usage WHERE table_schema='defense_dashboard' AND table_name IN ('clean_kdsis_nsn_ref','test_table');  -- 기대 0
-- SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema='defense_dashboard' AND referenced_table_name IN ('clean_kdsis_nsn_ref','test_table');  -- 기대 0

-- §2 삭제
DROP TABLE IF EXISTS clean_kdsis_nsn_ref;
DROP TABLE IF EXISTS test_table;

-- §3 열 사전 정리
DELETE FROM meta_column_dict WHERE table_name IN ('clean_kdsis_nsn_ref', 'test_table');

-- §4 검증(주석)
-- SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='defense_dashboard' AND table_name IN ('clean_kdsis_nsn_ref','test_table');  -- 기대 0
-- SELECT COUNT(*) FROM meta_column_dict WHERE table_name='clean_kdsis_nsn_ref';  -- 기대 0
-- SELECT COUNT(*) FROM meta_load_log WHERE table_name='clean_kdsis_nsn_ref';     -- 이력 유지(0이 아니어도 정상)
