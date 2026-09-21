-- ============================================================================
-- alter_2026-09-20_p3_test_vendor.sql — P3 검수(09-20 회신) 반영: 국외조달 계약정보 테스트 계약 6행 제외
-- ============================================================================
-- 배경: P3 담당이 raw 사본에서 검수한 SQL(docs/report/data/p3-review-response-2026-09-20.md §2-3)에서
--       대표업체명 'TEST2'를 결측으로 보고 NULL 처리했다. RDS 실측(2026-09-20, DBHub) 결과 raw_dapa_overseas_contract 에서
--       vendor_name = 'TEST2' 인 행은 정확히 6행이고 계약명·계약번호도 테스트 흔적이 있어(아래) 업체명만 지우는 것이 아니라
--       행 자체를 제외한다 — P2 검수 → P4 반영(alter_2026-09-19_sido_backfill_test_vendor.sql §2, 테스트 업체 6행 PLACEHOLDER)과 같은 처리.
--   raw_row_id 202  KD73AM08S35  2017  한도액계약테스트
--   raw_row_id 203  KD72CD08P92  2017  테스트점검용(국외확정)-CASE-038
--   raw_row_id 709  TE00GD08O01  2018  S/P FOR MOBILE EQP'T(태은테크놀러지)      — 계약번호 TE00…
--   raw_row_id 713  TESTGD08O02  2018  S/P FOR TRACKED VEHICLE (Double Dragon Trading) — 계약번호 TEST…
--   raw_row_id 1558 KD92CD08O01  2019  인지세테스트20190122
--   raw_row_id 1559 KD92CD08O02  2019  인지세TEST
--   6행 모두 contract_period 종료일 없음(is_open_ended=1). 키워드 'TEST'·'테스트'로 거르지 않는다 — 'REPAIR FOR AGM-65 TEST SYSTEMS',
--   '시험세트(TEST SET, RADAR)' 등 실제 계약 19행이 걸린다. 조건은 vendor_name = 'TEST2' + raw_row_id 명시(이중 확인).
--   재적재 시 같은 결과가 나오도록 notebooks/clean_p3_overseas.ipynb §3·§5 에 같은 규칙을 넣었다.
--
-- 기대 영향: clean_dapa_overseas_contract 6,333 → 6,327 · clean_excluded_row 11 → 17(PLACEHOLDER 6 → 12)
--            · 검산 raw 6,333 = clean 6,327 + excluded 6 · v_overseas_contract_yearly 2017 수의계약 175→174·일반경쟁 499→498,
--              2018 일반경쟁 657→655, 2019 일반경쟁 612→610 · 고유 업체(콜레이션 기준) 443 → 442.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-20_p3_test_vendor.sql   (admin, 재실행 시 전부 0행)
-- 되돌리기: clean_excluded_row 에서 해당 6행 DELETE 후 clean_dapa_overseas_contract TRUNCATE·노트북 §3 재적재(규칙 제거 뒤).
-- ============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §0 적용 전 확인(주석)
-- SELECT raw_row_id, contract_no, contract_name FROM clean_dapa_overseas_contract WHERE vendor_name = 'TEST2';   -- 6행
-- SELECT COUNT(*) FROM raw_dapa_overseas_contract WHERE vendor_name = 'TEST2';                                   -- 6

-- §1 테스트 계약 6행 제외 — raw_row_id 명시 + 업체명 조건(이중 확인)
-- 기대 6
INSERT IGNORE INTO clean_excluded_row (table_name, raw_row_id, reason_code, note, excluded_by)
SELECT 'raw_dapa_overseas_contract', raw_row_id, 'PLACEHOLDER',
       CONCAT('테스트 계약: 업체명 TEST2 (', contract_no, ', ', contract_name, '). P3 검수 09-20, 제외 결정 09-20'),
       'P3 검수 09-20 / alter 09-20 (admin)'
  FROM clean_dapa_overseas_contract
 WHERE raw_row_id IN (202, 203, 709, 713, 1558, 1559)
   AND vendor_name = 'TEST2';
-- 기대 6
DELETE FROM clean_dapa_overseas_contract
 WHERE raw_row_id IN (202, 203, 709, 713, 1558, 1559)
   AND vendor_name = 'TEST2';

-- §2 meta_load_log — 5단계 보고(검증된 분석 대상) 1행. 재실행 시 같은 stage_detail 이 있으면 넣지 않는다.
-- 기대 1
INSERT INTO meta_load_log (dataset_key, table_name, stage, stage_detail, row_count, exclusion_reason, method, measured_at, measured_by)
SELECT 'dapa_overseas_contract', 'clean_dapa_overseas_contract', '검증된 분석 대상', '테스트 계약 6행 제외 후',
       (SELECT COUNT(*) FROM clean_dapa_overseas_contract),
       '업체명 TEST2 테스트 계약 6행(raw_row_id 202·203·709·713·1558·1559) PLACEHOLDER 제외. 키워드 TEST/테스트로는 거르지 않음(실제 계약 19행)',
       'db/alter_2026-09-20_p3_test_vendor.sql §1 (P3 검수 09-20 회신)', NOW(), CURRENT_USER()
 WHERE NOT EXISTS (SELECT 1 FROM meta_load_log WHERE table_name = 'clean_dapa_overseas_contract' AND stage_detail = '테스트 계약 6행 제외 후');

-- §3 검증(주석)
-- SELECT COUNT(*) FROM clean_dapa_overseas_contract;                                                  -- 6,327
-- SELECT reason_code, table_name, COUNT(*) FROM clean_excluded_row GROUP BY 1, 2;                    -- raw_dapa_overseas_contract PLACEHOLDER 6
-- SELECT (SELECT COUNT(*) FROM raw_dapa_overseas_contract) - (SELECT COUNT(*) FROM clean_dapa_overseas_contract)
--        - (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name = 'raw_dapa_overseas_contract') AS gap;  -- 0
-- SELECT contract_year, SUM(contract_count) FROM v_overseas_contract_yearly GROUP BY 1;             -- 2017 703 · 2018 850 · 2019 824
