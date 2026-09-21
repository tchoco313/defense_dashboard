-- =============================================================================
-- defense_dashboard 데이터 계층 초기화 (기준 db/schema.sql 2026-09-21 — BASE TABLE 56 중 45를 비움, 11 보존)
--
-- 용도: 스키마는 그대로 두고 "적재한 데이터"만 비운 뒤 다시 적재할 때.
--       db/schema.sql(전체 DROP)과 달리 아래 9개는 보존한다.
--         ref_hs_whitelist · ref_country · ref_sido_map · ref_fsc · ref_fsg
--         · ref_hs_indicator · ref_hs_rule_flag · ref_equipment_alias                (참조표·수작업 대응표·규칙표)
--         meta_dataset · meta_column_dict                                            (출처 기록·열 사전)
-- 비우는 것: clean_ 20 → fact_/dim_ 2 → raw_ 23 → meta_load_log (FK 자식 → 부모 순)
-- 실행: RDS admin 계정으로(etl_rw는 TRUNCATE 권한 없음). 명령은 docs/runbook/commands.md §5.
--
-- 계층별 부분 재적재는 이 파일을 통째로 돌리지 말고 필요한 블록만 실행한다.
--   · raw_ 한 테이블만 다시 넣을 때: 그 raw를 참조하는 fact_/clean_ 을 먼저 비운다
--     (raw_customs_trade ← fact_customs_monthly, raw_dapa_contract ← clean_dapa_contract, raw_krit_task ← clean_krit_task,
--      raw_openfiscal_program_budget ← clean_openfiscal_program_budget, raw_hsk_control ← clean_hsk_control,
--      raw_dapa_overseas_plan_api ← clean_dapa_overseas_plan_api, raw_kosis_* ← clean_kosis_*  등 schema.sql의 fk_*_raw 참조).
--   · clean_ 만 다시 채울 때: clean_ 블록만.
--   · 특정 source_file 한 개만 걷어낼 때: DELETE FROM raw_x WHERE source_file = '...' (raw 수정 금지 원칙의 유일한 예외 = 재적재 전 회수).
-- 주의: FOREIGN_KEY_CHECKS=0 은 FK 부모 TRUNCATE를 허용하기 위한 것. 실행 후 반드시 1로 되돌린다.
--       TRUNCATE는 AUTO_INCREMENT를 1로 되돌리므로 raw row_id를 외부 문서에 적어 둔 것이 있으면 무효가 된다.
--       schema.sql에 표를 추가·삭제하면 이 파일의 목록도 같이 고친다(DROP 목록과 1:1).
-- =============================================================================

USE defense_dashboard;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. clean_ (20)
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

-- 3. raw_ (22)
TRUNCATE TABLE raw_kdsis_nsn;
TRUNCATE TABLE raw_openfiscal_program_budget;
TRUNCATE TABLE raw_dapa_fsc_catalog;
TRUNCATE TABLE raw_dapa_overseas_plan_api;
TRUNCATE TABLE raw_hs_unit_name;
TRUNCATE TABLE raw_hs_code_master;
TRUNCATE TABLE raw_hsk_control;
TRUNCATE TABLE raw_dapa_contract_exec_by_service;
TRUNCATE TABLE raw_dapa_domestic_plan;
TRUNCATE TABLE raw_dapa_overseas_bid_result;
TRUNCATE TABLE raw_dapa_overseas_contract;
TRUNCATE TABLE raw_dapa_overseas_plan;
TRUNCATE TABLE raw_customs_progress;
TRUNCATE TABLE raw_customs_region;
TRUNCATE TABLE raw_kosis_production_index;
TRUNCATE TABLE raw_kosis_utilization;
TRUNCATE TABLE raw_dapa_defense_company;
TRUNCATE TABLE raw_dapa_bid_result;
TRUNCATE TABLE raw_dapa_bid_notice;
TRUNCATE TABLE raw_krit_task;
TRUNCATE TABLE raw_dapa_localized_item;
TRUNCATE TABLE raw_dapa_contract;
TRUNCATE TABLE raw_customs_trade;

-- 4. meta_ (단계별 건수만. meta_dataset·meta_column_dict는 유지)
TRUNCATE TABLE meta_load_log;

SET FOREIGN_KEY_CHECKS = 1;

-- 확인: 아래가 모두 0이고 ref_hs_whitelist가 24이면 정상
-- SELECT (SELECT COUNT(*) FROM raw_customs_trade) AS raw_customs,
--        (SELECT COUNT(*) FROM fact_customs_monthly) AS fact_customs,
--        (SELECT COUNT(*) FROM clean_dapa_contract) AS clean_contract,
--        (SELECT COUNT(*) FROM meta_load_log) AS load_log,
--        (SELECT COUNT(*) FROM ref_hs_whitelist) AS ref_hs;
