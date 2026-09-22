-- =============================================================================
-- defense_dashboard 데이터 계층 초기화 (기준 db/schema.sql 2026-09-22 — BASE TABLE 37 중 25를 비움, 12 보존)
--
-- 용도: 스키마는 그대로 두고 "적재한 데이터"만 비운 뒤 다시 적재할 때.
--       db/schema.sql(전체 DROP)과 달리 아래 12개는 보존한다.
--         ref_hs_whitelist · ref_country · ref_sido_map · ref_fsc · ref_fsg · ref_hs_code_master · ref_hs6_name
--         · ref_hs_indicator · ref_hs_rule_flag · ref_equipment_alias                (참조표·기준표·규칙표)
--         meta_dataset · meta_column_dict                                            (출처 기록·열 사전)
-- 비우는 것: clean_ 22 → fact_/dim_ 2 → meta_load_log. raw_ 표는 없다(2026-09-22 삭제 — 원본은 data/raw/ 파일, read_raw 로 읽음)
-- 실행: RDS admin 계정으로(etl_rw는 TRUNCATE 권한 없음). 명령은 docs/runbook/commands.md §5.
--
-- 계층별 부분 재적재는 이 파일을 통째로 돌리지 말고 필요한 블록만 실행한다.
--   · clean_ 만 다시 채울 때: clean_ 블록만 → 노트북 재실행(입력은 원본 파일이라 순서 제약 없음).
--   · fact_/dim_·clean_customs_region: 블록 실행 후 python scripts/load_db.py --fact.
-- 주의: FOREIGN_KEY_CHECKS=0 은 FK 부모 TRUNCATE를 허용하기 위한 것. 실행 후 반드시 1로 되돌린다.
--       clean_*.raw_row_id 는 파일 파서 순번(read_raw)이라 재적재해도 값이 바뀌지 않는다.
--       schema.sql에 표를 추가·삭제하면 이 파일의 목록도 같이 고친다(DROP 목록과 1:1).
-- =============================================================================

USE defense_dashboard;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. clean_ (22)
TRUNCATE TABLE clean_dapa_defense_company;
TRUNCATE TABLE clean_customs_region;
TRUNCATE TABLE clean_kosis_production_index;
TRUNCATE TABLE clean_kosis_utilization;
TRUNCATE TABLE clean_hsk_control;
TRUNCATE TABLE clean_openfiscal_program_link;
TRUNCATE TABLE clean_openfiscal_program_budget;
TRUNCATE TABLE clean_dapa_overseas_bid_result;
TRUNCATE TABLE clean_dapa_overseas_contract;
TRUNCATE TABLE clean_dapa_overseas_plan_api;
TRUNCATE TABLE clean_dapa_contract_exec_by_service;
TRUNCATE TABLE clean_dapa_domestic_plan;
TRUNCATE TABLE clean_dapa_bid_result;
TRUNCATE TABLE clean_dapa_bid_notice;
TRUNCATE TABLE clean_excluded_row;
TRUNCATE TABLE clean_kdsis_nsn;
TRUNCATE TABLE clean_dapa_overseas_plan;
TRUNCATE TABLE clean_company_name_link;
TRUNCATE TABLE clean_company;
TRUNCATE TABLE clean_krit_task;
TRUNCATE TABLE clean_dapa_localized_item;
TRUNCATE TABLE clean_dapa_contract;

-- 2. fact_ / dim_ (2)
TRUNCATE TABLE fact_customs_monthly;
TRUNCATE TABLE dim_hs10;

-- 4. meta_ (단계별 건수만. meta_dataset·meta_column_dict는 유지)
TRUNCATE TABLE meta_load_log;

SET FOREIGN_KEY_CHECKS = 1;

-- 확인: 아래가 모두 0이고 ref_hs_whitelist가 24이면 정상
-- SELECT (SELECT COUNT(*) FROM fact_customs_monthly) AS fact_customs,
--        (SELECT COUNT(*) FROM clean_customs_region) AS clean_region,
--        (SELECT COUNT(*) FROM clean_dapa_contract) AS clean_contract,
--        (SELECT COUNT(*) FROM meta_load_log) AS load_log,
--        (SELECT COUNT(*) FROM ref_hs_whitelist) AS ref_hs;
