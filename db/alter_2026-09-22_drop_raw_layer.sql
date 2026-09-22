-- =============================================================================
-- raw_ 계층 제거 2/2 — RDS raw_ 표 23개 DROP + 열 사전 정리  (작성 2026-09-22)
--
-- 결정: 2026-09-22 교수 중간 점검 피드백(docs/report/feedback/professor-feedback-2026-09-22.md §1) — 원본은 파일(data/raw/,
--       훅·읽기 전용 동결 + meta_dataset 의 경로·SHA-256·파서 건수 + 팀 드라이브 사본)로 관리하고 DB 에는 정제·기준·기록 표와 뷰만 둔다.
-- 선행: alter_2026-09-22_raw_successors.sql(후속 표 4개·뷰 4개·FK 15개 제거) 적용 완료, 노트북 6개 read_raw 전환·실행(오류 0, gap 0),
--       파일 ↔ RDS raw_ 동일성 실측(22표), DROP 직전 로컬 덤프 data/db_dump/raw_tables_2026-09-22.sql.gz(gitignore, 268MB → 32MB).
-- 조치: §1 DROP TABLE 23개(FK 자식 없음 — 1/2 에서 전부 제거)
--       §2 열 사전 — fact_customs_monthly.raw_row_id 행 삭제(열이 1/2 에서 사라짐), raw_row_id·first_raw_row_id 설명 18행을
--          「원본 파일 파서 순번(read_raw)」으로 교체. raw_ 23표의 열 사전 319행은 **원본 파일 열 사전**으로 유지한다
--          (frame_generic 의 헤더 대조 기준이자 산출물 3 데이터 명세서의 원천 — table_dict.csv kind=file).
--       §3 검증
-- 정본 동기(이 파일과 같은 커밋): db/schema.sql(raw_ CREATE 23·DROP 목록·가드 → fact 기준), db/reset_data.sql(raw_ 23줄 삭제),
--       db/table_dict.csv(raw 23행 kind=file), db/column_dict.csv(fact raw_row_id 삭제·설명 18행 교체), scripts/load_db.py REF_EXPECTED 858,
--       scripts/gen_table_catalog.py(파일 계층 표시), scripts/gen_data_spec_xlsx.py(원본 명세를 파일에서), docs/db/table-catalog.md 재생성.
-- 되돌리기: 이 파일로는 불가. 덤프 복원(mariadb < raw_tables_2026-09-22.sql) 또는 원본 파일 재적재(git 이력의 load_db.py --raw, 2026-09-22 이전 판).
-- 멱등: DROP … IF EXISTS(2회째 Note 1051), DELETE·UPDATE 는 2회째 0행.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-22_drop_raw_layer.sql
-- 기대: 1회째 DROP 23 · DELETE 1 · UPDATE 18. §3: raw_ 표 0, 표 37, 뷰 31, meta_column_dict 858.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- §1. raw_ 표 23개 DROP
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS raw_kdsis_nsn;
DROP TABLE IF EXISTS raw_openfiscal_program_budget;
DROP TABLE IF EXISTS raw_dapa_fsc_catalog;
DROP TABLE IF EXISTS raw_dapa_overseas_plan_api;
DROP TABLE IF EXISTS raw_hs_unit_name;
DROP TABLE IF EXISTS raw_hs_code_master;
DROP TABLE IF EXISTS raw_hsk_control;
DROP TABLE IF EXISTS raw_dapa_contract_exec_by_service;
DROP TABLE IF EXISTS raw_dapa_domestic_plan;
DROP TABLE IF EXISTS raw_dapa_overseas_bid_result;
DROP TABLE IF EXISTS raw_dapa_overseas_contract;
DROP TABLE IF EXISTS raw_dapa_overseas_plan;
DROP TABLE IF EXISTS raw_customs_region;
DROP TABLE IF EXISTS raw_customs_progress;
DROP TABLE IF EXISTS raw_kosis_production_index;
DROP TABLE IF EXISTS raw_kosis_utilization;
DROP TABLE IF EXISTS raw_dapa_defense_company;
DROP TABLE IF EXISTS raw_dapa_bid_result;
DROP TABLE IF EXISTS raw_dapa_bid_notice;
DROP TABLE IF EXISTS raw_krit_task;
DROP TABLE IF EXISTS raw_dapa_localized_item;
DROP TABLE IF EXISTS raw_dapa_contract;
DROP TABLE IF EXISTS raw_customs_trade;

-- -----------------------------------------------------------------------------
-- §2. 열 사전 정리 (db/column_dict.csv 와 동일 내용)
-- -----------------------------------------------------------------------------
DELETE FROM meta_column_dict WHERE table_name = 'fact_customs_monthly' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '대표 원본 행의 파서 순번(read_raw raw_kdsis_nsn.row_id)' WHERE table_name = 'clean_kdsis_nsn' AND column_name = 'first_raw_row_id';
UPDATE meta_column_dict SET description = '제외한 원본 행의 파서 순번(read_raw <table_name>.row_id — 파일명 정렬 × 행 순)' WHERE table_name = 'clean_excluded_row' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '원본 파일 파서 순번(read_raw raw_dapa_bid_notice.row_id, UNIQUE)' WHERE table_name = 'clean_dapa_bid_notice' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '원본 파일 파서 순번(read_raw raw_dapa_bid_result.row_id, UNIQUE)' WHERE table_name = 'clean_dapa_bid_result' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = 'PK. 원본 파일 파서 순번(read_raw raw_dapa_domestic_plan.row_id)' WHERE table_name = 'clean_dapa_domestic_plan' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '원본 파일 파서 순번(read_raw raw_dapa_contract_exec_by_service.row_id, UNIQUE)' WHERE table_name = 'clean_dapa_contract_exec_by_service' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '원본 파일 파서 순번(read_raw raw_dapa_contract.row_id, UNIQUE)' WHERE table_name = 'clean_dapa_contract' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '대표 원본 행의 파서 순번(read_raw raw_dapa_localized_item.row_id)' WHERE table_name = 'clean_dapa_localized_item' AND column_name = 'first_raw_row_id';
UPDATE meta_column_dict SET description = '대표 원본 행의 파서 순번(read_raw raw_dapa_overseas_plan.row_id)' WHERE table_name = 'clean_dapa_overseas_plan' AND column_name = 'first_raw_row_id';
UPDATE meta_column_dict SET description = '원본 파일 파서 순번(read_raw raw_krit_task.row_id — 파일명 정렬 × 행 순. 2026-09-22 재번호)' WHERE table_name = 'clean_krit_task' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '원본 파일 파서 순번(read_raw raw_dapa_overseas_plan_api.row_id, UNIQUE)' WHERE table_name = 'clean_dapa_overseas_plan_api' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '원본 파일 파서 순번(read_raw raw_dapa_overseas_contract.row_id, UNIQUE)' WHERE table_name = 'clean_dapa_overseas_contract' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = 'PK. 원본 파일 파서 순번(read_raw raw_dapa_overseas_bid_result.row_id) — 업무 식별자 단독 고유성 없음' WHERE table_name = 'clean_dapa_overseas_bid_result' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = 'PK. 원본 파일 파서 순번(read_raw raw_openfiscal_program_budget.row_id, 원본 1:1)' WHERE table_name = 'clean_openfiscal_program_budget' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = '원본 파일 파서 순번(read_raw raw_hsk_control.row_id — 1 원본 행 = N 통제번호)' WHERE table_name = 'clean_hsk_control' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = 'PK. 원본 파일 파서 순번(read_raw raw_kosis_utilization.row_id, 원본 1:1)' WHERE table_name = 'clean_kosis_utilization' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = 'PK. 원본 파일 파서 순번(read_raw raw_kosis_production_index.row_id, 원본 1:1)' WHERE table_name = 'clean_kosis_production_index' AND column_name = 'raw_row_id';
UPDATE meta_column_dict SET description = 'seq_conflict_flag=1일 때 적재하지 않은 나머지 원본 행 파서 순번(read_raw row_id)(쉼표 구분). NULL = 구조적 43,104행(seq_conflict_flag=0, 충돌 1행과 1:1) → 화면 표시 안 함, 집계 무시' WHERE table_name = 'clean_dapa_contract' AND column_name = 'conflict_raw_row_ids';

-- -----------------------------------------------------------------------------
-- §3. 검증
-- -----------------------------------------------------------------------------
SELECT 'raw_tables' t, COUNT(*) n FROM information_schema.tables WHERE table_schema = 'defense_dashboard' AND table_name LIKE 'raw\_%'
UNION ALL SELECT 'base_tables', COUNT(*) FROM information_schema.tables WHERE table_schema = 'defense_dashboard' AND table_type = 'BASE TABLE'
UNION ALL SELECT 'views', COUNT(*) FROM information_schema.tables WHERE table_schema = 'defense_dashboard' AND table_type = 'VIEW'
UNION ALL SELECT 'meta_column_dict', COUNT(*) FROM meta_column_dict
UNION ALL SELECT 'meta_column_dict_raw_rows', COUNT(*) FROM meta_column_dict WHERE table_name LIKE 'raw\_%'
UNION ALL SELECT 'fact_customs_monthly', COUNT(*) FROM fact_customs_monthly
UNION ALL SELECT 'views_ok', COUNT(*) FROM v_customs_region_gwacheon_year;
