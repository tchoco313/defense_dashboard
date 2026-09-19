-- ============================================================================
-- alter_2026-09-19_sido_backfill_test_vendor.sql — P2 검수(09-18) 반영: sido_code 백필 + 테스트 업체 6행 제외 (2026-09-19)
-- ============================================================================
-- 배경: docs/report/ref-review-p2-2026-09-18.md §3·§0 #7. db/alter_2026-09-18_sido_gwangju.sql(ref_sido_map 45→44, 같은 날 적용)의
--       주석 "clean_dapa_contract 는 0행이라 재계산 대상 없음"은 작성 시점(09-18 17:20) 기준이고, 09-19 P4 적재로 43,111행이 있어
--       clean 값을 여기서 고친다. 재적재 시 같은 결과가 나오도록 notebooks/clean_p4_domestic.ipynb 셀 2·4에도 같은 규칙을 넣었다.
--
--   §1 sido_code 백필 — 주소 첫 토큰 '충남대전시'(1989년 대전 분리 전 표기) → '30'. RDS 사전 조회(2026-09-19, DBHub):
--      clean_dapa_contract sido_code NULL 20 = 충남대전시 16 · 용산구 2 · '**' 1 · '1' 1 → 16행 백필. 용산구 2행은 §2 테스트 업체로 제외 → 남는 NULL은 '**'·'1' 2행(판별 불가).
--      clean_company sido_code NULL 4 = 충남대전시 1 · 용산구 1(테스트 업체, §2에서 삭제) · '**' 1 · '1' 1 → 1행 백필.
--      clean_dapa_bid_result.winner_sido_code: 사업자번호 있는 행 중 NULL 0 → 해당 없음.
--      '광주 서구' 1건은 이미 29(둘째 토큰 규칙과 같은 결과) → UPDATE 없음.
--   §2 테스트 업체 제외 — 대표업체명이 정확히 '조달테스트업체Ⅰ'(U+2160, 2행: 2024SFC0165·2025SFC0086, 주소 '용산구 갈월동 34∼38 테스트',
--      사업자번호 106-83-07018) · '테스트업체1'(4행: 2025LMH0104·2025LMZ0052·0053·0056, 주소 '서울특별시 종로구 종로0-1',
--      사업자번호 111-11-11119)인 6행. raw_dapa_contract에서도 정확히 6행. 사용자 결정(09-19): 제외(clean_excluded_row PLACEHOLDER).
--      키워드 '테스트'로 거르지 않는다 — 이테스트 주식회사·(주)테스트링크(업체), 결함테스트기·콘테스트(품명)는 실제 값.
--      6개 계약번호 모두 차수 '00' 하나뿐 → is_latest_seq 재계산 대상 없음(SUM(is_latest_seq) 37,608 → 37,602).
--      clean_company의 두 사업자번호 행은 다른 clean 계약·낙찰 행에 없고 clean_company_name_link 참조 0, 참조 뷰 0 → 함께 삭제.
--   §3 meta_column_dict — ref_sido_map.token 설명 "시드 45행" → "44행"(db/column_dict.csv:542와 동기, 849행 유지).
--
-- 기대 영향: clean_dapa_contract 43,111 → 43,105 · clean_excluded_row 5 → 11(KEY_CONFLICT 1·COL_SHIFT 4·PLACEHOLDER 6)
--            · clean_company 14,838 → 14,836 · 검산 raw 43,112 = clean 43,105 + excluded 7.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-19_sido_backfill_test_vendor.sql   (admin, 재실행 시 전부 0행)
-- 되돌리기: §2는 raw_dapa_contract(row_id 12361·24736·27786·40275·40368·41769)에서 노트북 규칙으로 재생성하거나
--           clean_excluded_row에서 해당 6행 DELETE 후 TRUNCATE·재적재. §1은 sido_code='30'이고 첫 토큰이 '충남대전시'인 행을 NULL로.
-- ============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §0 적용 전 확인(주석)
-- SELECT COUNT(*) FROM ref_sido_map;                                                                        -- 기대 44 (sido_gwangju alter 적용 후)
-- SELECT SUBSTRING_INDEX(TRIM(vendor_address),' ',1) tok, COUNT(*) FROM clean_dapa_contract WHERE sido_code IS NULL GROUP BY 1;  -- 충남대전시 16·용산구 2·** 1·1 1
-- SELECT raw_row_id, contract_no, vendor_name FROM clean_dapa_contract WHERE vendor_name IN ('조달테스트업체Ⅰ','테스트업체1');  -- 6행

-- §1 sido_code 백필 (충남대전시 → 30)
-- 기대 16
UPDATE clean_dapa_contract SET sido_code = '30'
 WHERE sido_code IS NULL AND SUBSTRING_INDEX(TRIM(vendor_address), ' ', 1) = '충남대전시';
-- 기대 1
UPDATE clean_company SET sido_code = '30'
 WHERE sido_code IS NULL AND SUBSTRING_INDEX(TRIM(address), ' ', 1) = '충남대전시';

-- §2 테스트 업체 6행 제외 — raw_row_id를 명시해 정확히 그 행만 (이름 조건은 이중 확인)
-- 기대 6
INSERT IGNORE INTO clean_excluded_row (table_name, raw_row_id, reason_code, note, excluded_by)
SELECT 'raw_dapa_contract', raw_row_id, 'PLACEHOLDER',
       CONCAT('테스트 업체명: ', vendor_name, ' (', contract_no, '-', contract_seq_norm, '). P2 검수 09-18, 제외 결정 09-19'),
       'P2 검수 09-18 / alter 09-19 (admin)'
  FROM clean_dapa_contract
 WHERE raw_row_id IN (12361, 24736, 27786, 40275, 40368, 41769)
   AND vendor_name IN ('조달테스트업체Ⅰ', '테스트업체1');
-- 기대 6
DELETE FROM clean_dapa_contract
 WHERE raw_row_id IN (12361, 24736, 27786, 40275, 40368, 41769)
   AND vendor_name IN ('조달테스트업체Ⅰ', '테스트업체1');
-- 기대 2
DELETE FROM clean_company
 WHERE biz_reg_no IN ('106-83-07018', '111-11-11119')
   AND biz_reg_no NOT IN (SELECT vendor_biz_reg_no FROM clean_dapa_contract WHERE vendor_biz_reg_no IS NOT NULL)
   AND biz_reg_no NOT IN (SELECT winner_biz_reg_no FROM clean_dapa_bid_result WHERE winner_biz_reg_no IS NOT NULL)
   AND biz_reg_no NOT IN (SELECT biz_reg_no FROM clean_company_name_link WHERE biz_reg_no IS NOT NULL);

-- §3 열 사전 설명 동기
-- 기대 1
UPDATE meta_column_dict SET description = REPLACE(description, '시드 db/seed_ref.sql 45행', '시드 db/seed_ref.sql 44행')
 WHERE table_name = 'ref_sido_map' AND column_name = 'token';

-- §4 검증(주석)
-- SELECT COUNT(*), SUM(sido_code IS NULL), SUM(is_latest_seq) FROM clean_dapa_contract;     -- 43,105 · 2 · 37,602 (RDS 실측 2026-09-19 일치)
-- SELECT reason_code, COUNT(*) FROM clean_excluded_row GROUP BY 1;                          -- KEY_CONFLICT 1 · COL_SHIFT 4 · PLACEHOLDER 6
-- SELECT contract_no FROM clean_dapa_contract GROUP BY contract_no HAVING SUM(is_latest_seq) <> 1;  -- 0행
-- SELECT COUNT(*), SUM(sido_code IS NULL) FROM clean_company;                               -- 14,836 · 2 (실측 일치)
-- 적용 기록: 2026-09-19 apply_alter.py --twice, 1회차 rows 16·1·6·6·2·1, 2회차 전부 0. 검산 gap 0, 계약번호당 latest 1행 위반 0.
