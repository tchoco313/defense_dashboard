-- =============================================================================
-- 카테고리 맵 폐기 후속 — clean_ 3표의 품목군 연결 열(category·category_link_status·hs6·contract_group)과 ref_hs_whitelist.b2_scope 삭제,
-- v_review_list B1 열 제거  (작성·적용 2026-09-21, 사용자 "남긴 것도 해")
--
-- 배경: alter_2026-09-21_drop_category_map.sql 이 대응표·뷰·related_fsc 를 지웠고, 남겨 둔 연결 열(값은 전부 기본값 — RDS 실측 09-21:
--       clean_dapa_contract 43,105행 category NULL·contract_group NULL·category_link_status '미연결' / clean_dapa_localized_item 25,025행
--       category 400행('반도체' 67·'전자부품' 333, 옛 대응표 후보)·category_link_status '후보' 400·'조회표 전용' 24,625 /
--       clean_krit_task 96행 hs6·category NULL·'미연결' / ref_hs_whitelist.b2_scope 24행 NULL)을 이 파일로 마저 지운다.
-- 의존: v_review_list 의 B1 열이 clean_krit_task.hs6·category_link_status 를 읽으므로 먼저 재정의(화이트리스트 × 연도별 HHI만).
--       clean_krit_task.hs6 는 FK fk_ckt_hs6 + KEY ix_ckt_hs6, localized_item 은 KEY ix_cli_cat(category, category_link_status) → 열보다 먼저 삭제.
-- 정본 동기: db/schema.sql(열·인덱스·FK·b2_scope·v_review_list·말미 UPDATE 예시), db/column_dict.csv 10행 삭제 + 표별 ordinal 재번호,
--       notebooks/clean_b2_a7.ipynb(대응표 조회·category 산출 삭제) · clean_p5_krit_p2_budget.ipynb(hs6·category 열 제거) · clean_p4_domestic.ipynb(설명 줄).
-- 남김: ref_hs_rule_flag 의 r4_b2·b2_part_count(09-16 스냅샷 이력), clean_dapa_contract 의 is_target_b1·is_completed_b2(국산화 상태 속성, 대응표 무관).
-- 멱등: 열·인덱스 삭제는 information_schema 조건 PREPARE(2회째 SELECT 1). ordinal 재번호는 변수 카운터(연속이면 변화 0).
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-21_drop_category_link_cols.sql   (admin)
-- 기대: 1회째 ALTER 4문 실행 · meta_column_dict DELETE 10 · ordinal UPDATE(표별 재번호). 2회째 0/SELECT 1. 검증 §7.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 v_review_list — 화이트리스트 × 연도별 HHI(B1·B2 열 없음). 화면 코드는 metrics.concentration(기간 합산)을 쓰고 이 뷰는 노트북·검산용.
CREATE OR REPLACE VIEW v_review_list AS
SELECT w.hs6, w.category, w.name_ko, w.priority, w.axis,
       h.year, h.imp_dlr_total, h.top1_stat_cd, h.top1_share, h.hhi, h.country_count, h.is_partial_year
FROM ref_hs_whitelist w
JOIN v_hhi_hs6_year h ON h.hs6 = w.hs6;

-- §2 clean_krit_task — FK·인덱스·열 3개
SET @has := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'defense_dashboard' AND table_name = 'clean_krit_task' AND column_name = 'hs6');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_krit_task DROP FOREIGN KEY fk_ckt_hs6, DROP INDEX ix_ckt_hs6, DROP COLUMN hs6, DROP COLUMN category, DROP COLUMN category_link_status', 'SELECT 1');
PREPARE s FROM @ddl;
EXECUTE s;
DEALLOCATE PREPARE s;

-- §3 clean_dapa_localized_item — 인덱스·열 2개
SET @has := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'defense_dashboard' AND table_name = 'clean_dapa_localized_item' AND column_name = 'category_link_status');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_localized_item DROP INDEX ix_cli_cat, DROP COLUMN category, DROP COLUMN category_link_status', 'SELECT 1');
PREPARE s FROM @ddl;
EXECUTE s;
DEALLOCATE PREPARE s;

-- §4 clean_dapa_contract — 열 3개
SET @has := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'defense_dashboard' AND table_name = 'clean_dapa_contract' AND column_name = 'category_link_status');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_contract DROP COLUMN contract_group, DROP COLUMN category, DROP COLUMN category_link_status', 'SELECT 1');
PREPARE s FROM @ddl;
EXECUTE s;
DEALLOCATE PREPARE s;

-- §5 ref_hs_whitelist.b2_scope
SET @has := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'defense_dashboard' AND table_name = 'ref_hs_whitelist' AND column_name = 'b2_scope');
SET @ddl := IF(@has > 0, 'ALTER TABLE ref_hs_whitelist DROP COLUMN b2_scope', 'SELECT 1');
PREPARE s FROM @ddl;
EXECUTE s;
DEALLOCATE PREPARE s;

-- §6 열 사전 — 10행 삭제 후 표별 ordinal 재번호(오름차순 카운터, 새 값 <= 옛 값이라 UNIQUE 충돌 없음)
DELETE FROM meta_column_dict WHERE table_name = 'clean_krit_task' AND column_name IN ('hs6', 'category', 'category_link_status');
DELETE FROM meta_column_dict WHERE table_name = 'clean_dapa_localized_item' AND column_name IN ('category', 'category_link_status');
DELETE FROM meta_column_dict WHERE table_name = 'clean_dapa_contract' AND column_name IN ('contract_group', 'category', 'category_link_status');
DELETE FROM meta_column_dict WHERE table_name = 'ref_hs_whitelist' AND column_name = 'b2_scope';
SET @r := 0;
UPDATE meta_column_dict SET ordinal = (@r := @r + 1) WHERE table_name = 'clean_krit_task' ORDER BY ordinal;
SET @r := 0;
UPDATE meta_column_dict SET ordinal = (@r := @r + 1) WHERE table_name = 'clean_dapa_localized_item' ORDER BY ordinal;
SET @r := 0;
UPDATE meta_column_dict SET ordinal = (@r := @r + 1) WHERE table_name = 'clean_dapa_contract' ORDER BY ordinal;
SET @r := 0;
UPDATE meta_column_dict SET ordinal = (@r := @r + 1) WHERE table_name = 'ref_hs_whitelist' ORDER BY ordinal;

-- §7 확인 (주석 — DBHub app_ro)
-- SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='defense_dashboard'
--   AND column_name IN ('category','category_link_status','contract_group','b2_scope') AND table_name LIKE 'clean_%' OR (table_name='ref_hs_whitelist' AND column_name='b2_scope');   -- 0행
-- SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='defense_dashboard' AND table_name='clean_krit_task' AND column_name='hs6';   -- 0
-- SELECT COUNT(*) FROM v_review_list;   -- 246
-- SELECT COUNT(*) FROM meta_column_dict;   -- 851 → 841
