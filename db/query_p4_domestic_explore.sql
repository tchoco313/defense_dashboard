-- ============================================================================
-- P4(김훈희) 방사청 국내조달·업체 — raw 탐색·검산 복붙용 쿼리 (2026-09-18)
--   대상: raw_dapa_contract · raw_dapa_bid_notice · raw_dapa_bid_result
--         raw_dapa_domestic_plan · raw_dapa_contract_exec_by_service · raw_dapa_defense_company
--   목표: clean_dapa_contract(정의 있음, 0행) · clean_company/clean_company_name_link(정의 있음, 0행)
--         clean_dapa_bid_notice · clean_dapa_bid_result · clean_dapa_domestic_plan · clean_dapa_contract_exec_by_service · clean_excluded_row(db/alter_2026-09-18_p4_clean.sql, 2026-09-18 DDL)
--   주석의 "기대" 값은 docs/db/schema-design.md §7 · table-guide.md · 전환 명세(docs/reference/clean-conversion-spec-2026-09-18.md) 기준.
--   raw 는 읽기만 한다(원본 동결). 한 블록씩 복사해 실행.
-- ============================================================================

USE defense_dashboard;

-- ----------------------------------------------------------------------------
-- 0. 착수 전 행 수 확인 (명세: 착수 전 SELECT COUNT(*) 다시 확인)
--    기대: 43,112 / 10,842 / 7,405 / 35,859 / 40 / 84
-- ----------------------------------------------------------------------------
SELECT 'raw_dapa_contract'                 AS tbl, COUNT(*) AS n FROM raw_dapa_contract
UNION ALL SELECT 'raw_dapa_bid_notice',             COUNT(*) FROM raw_dapa_bid_notice
UNION ALL SELECT 'raw_dapa_bid_result',             COUNT(*) FROM raw_dapa_bid_result
UNION ALL SELECT 'raw_dapa_domestic_plan',          COUNT(*) FROM raw_dapa_domestic_plan
UNION ALL SELECT 'raw_dapa_contract_exec_by_service', COUNT(*) FROM raw_dapa_contract_exec_by_service
UNION ALL SELECT 'raw_dapa_defense_company',        COUNT(*) FROM raw_dapa_defense_company
UNION ALL SELECT 'clean_dapa_contract (목표, 지금 0)', COUNT(*) FROM clean_dapa_contract
UNION ALL SELECT 'clean_company (목표, 지금 0)',       COUNT(*) FROM clean_company
UNION ALL SELECT 'ref_sido_map (P2 보강 대상)',        COUNT(*) FROM ref_sido_map;


-- ============================================================================
-- 1. raw_dapa_contract  →  clean_dapa_contract   (★★ 과제 요건 1만 건)
-- ============================================================================

-- 1-1. 생김새 보기
SELECT * FROM raw_dapa_contract LIMIT 20;

-- 1-2. 열 목록·주석 (clean 열과 대응 확인용)
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'raw_dapa_contract'
ORDER BY ORDINAL_POSITION;

-- 1-3. 차수 표기 혼재  (기대: '0' 837 · '00' 34,365 · 그 외 01,02…)
SELECT contract_seq, COUNT(*) AS n
FROM raw_dapa_contract
GROUP BY contract_seq
ORDER BY n DESC;

-- 1-4. 정규화 후 키 고유성  (기대: 행 43,112 · 키 고유 43,111 · 계약번호 고유 37,608)
SELECT COUNT(*)                                                     AS rows_total,
       COUNT(DISTINCT contract_no, LPAD(contract_seq, 2, '0'))      AS key_unique,
       COUNT(DISTINCT contract_no)                                  AS contract_unique
FROM raw_dapa_contract;

-- 1-5. 충돌 키 (같은 계약번호×차수에 원본 2행)  (기대: 2024UMM1504-01 한 건)
SELECT contract_no, LPAD(contract_seq, 2, '0') AS seq_norm,
       COUNT(*) AS n, GROUP_CONCAT(row_id) AS row_ids
FROM raw_dapa_contract
GROUP BY contract_no, LPAD(contract_seq, 2, '0')
HAVING COUNT(*) > 1;

-- 1-6. 충돌 2행 나란히 보기 → 어느 열이 다른지 evidence 에 적을 것
SELECT * FROM raw_dapa_contract
WHERE contract_no = '2024UMM1504' AND LPAD(contract_seq, 2, '0') = '01';

-- 1-7. 연도별·업무구분별  (기대: 2024 12,304 / 2025 30,808 · 물품 31,549 / 용역 11,563)
SELECT LEFT(contract_date, 4) AS yr, biz_type_name, COUNT(*) AS n
FROM raw_dapa_contract
GROUP BY yr, biz_type_name
ORDER BY yr, biz_type_name;

-- 1-8. 날짜 형식 점검 (YYYY-MM-DD 가 아닌 값이 있는지)
SELECT contract_date, COUNT(*) AS n
FROM raw_dapa_contract
WHERE contract_date IS NULL OR contract_date NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
GROUP BY contract_date;

-- 1-9. 계약기간 형식 표본 → period_start / period_end 분리 규칙 정하기
SELECT contract_period, COUNT(*) AS n
FROM raw_dapa_contract
GROUP BY contract_period
ORDER BY n DESC
LIMIT 30;

-- 1-10. 기간 이상치 (종료일 2525-01-16 류 → period_anomaly_flag=1)
SELECT contract_no, contract_seq, contract_period
FROM raw_dapa_contract
WHERE contract_period LIKE '%25__-%' AND contract_period NOT LIKE '%202_-%'
   OR contract_period LIKE '%2525%'
LIMIT 50;

-- 1-11. 금액 3열 숫자 변환 가능 여부 (비숫자·공란 건수)
SELECT
  SUM(contract_amount       IS NULL OR contract_amount       = '' OR REPLACE(contract_amount,       ',', '') NOT REGEXP '^[0-9]+$') AS bad_contract_amount,
  SUM(total_contract_amount IS NULL OR total_contract_amount = '' OR REPLACE(total_contract_amount, ',', '') NOT REGEXP '^[0-9]+$') AS bad_total_amount,
  SUM(reserve_price         IS NULL OR reserve_price         = '' OR REPLACE(reserve_price,         ',', '') NOT REGEXP '^[0-9]+$') AS bad_reserve_price
FROM raw_dapa_contract;

-- 1-12. 미확정: 계약금액 vs 총계약금액 관계 표본 (차수별 금액 / 누계?)  — 여러 차수 있는 계약번호로 확인
SELECT contract_no, LPAD(contract_seq, 2, '0') AS seq_norm, contract_date,
       contract_amount, total_contract_amount
FROM raw_dapa_contract
WHERE contract_no IN (
  SELECT contract_no FROM raw_dapa_contract GROUP BY contract_no HAVING COUNT(*) >= 3
)
ORDER BY contract_no, seq_norm
LIMIT 60;

-- 1-13. 최종 차수(is_latest_seq=1) 후보 — 계약번호당 1행이어야 함  (기대: 37,608)
SELECT COUNT(*) AS latest_rows
FROM (
  SELECT contract_no, MAX(LPAD(contract_seq, 2, '0')) AS max_seq
  FROM raw_dapa_contract
  GROUP BY contract_no
) t;

-- 1-14. 주소 첫 토큰 → ref_sido_map 매칭률 (누락 토큰은 P2 안태호에게 전달, 9/23)
SELECT SUBSTRING_INDEX(TRIM(vendor_address), ' ', 1) AS token,
       m.sido_code, COUNT(*) AS n
FROM raw_dapa_contract c
LEFT JOIN ref_sido_map m ON m.token = SUBSTRING_INDEX(TRIM(c.vendor_address), ' ', 1)
GROUP BY token, m.sido_code
ORDER BY (m.sido_code IS NULL) DESC, n DESC;

-- 1-15. 국내업체여부 값 분포 (기대: 전부 국내 → "국산 근거 아님" 주석 유지)
SELECT domestic_vendor_yn, COUNT(*) AS n FROM raw_dapa_contract GROUP BY domestic_vendor_yn;

-- 1-16. 계약체결형태·방법 값 분포 (clean 은 VARCHAR 그대로, 표기 흔들림만 확인)
SELECT contract_form_name, contract_method_name, COUNT(*) AS n
FROM raw_dapa_contract
GROUP BY contract_form_name, contract_method_name
ORDER BY n DESC;

-- 1-17. 공동계약여부 값 (→ joint_contract_yn TINYINT)
SELECT joint_contract_yn, COUNT(*) AS n FROM raw_dapa_contract GROUP BY joint_contract_yn;

-- 1-18. 사업자등록번호 형식 (clean CHAR(12) = 'XXX-XX-XXXXX')
SELECT LENGTH(vendor_biz_reg_no) AS len, COUNT(*) AS n,
       MIN(vendor_biz_reg_no) AS sample
FROM raw_dapa_contract
GROUP BY len;

-- 1-19. clean_dapa_contract 열 정의 (적재 시 열 순서·ENUM 값 맞추기)
SHOW CREATE TABLE clean_dapa_contract;

-- 1-20. [적재 후 검산]  raw 43,112 = clean + 제외(충돌 1)
SELECT (SELECT COUNT(*) FROM raw_dapa_contract)   AS raw_n,
       (SELECT COUNT(*) FROM clean_dapa_contract) AS clean_n,
       (SELECT COUNT(*) FROM clean_dapa_contract WHERE seq_conflict_flag = 1) AS conflict_n,
       (SELECT COUNT(*) FROM clean_dapa_contract WHERE is_latest_seq = 1)     AS latest_n;   -- 기대 37,608

-- 1-21. [적재 후] 계약번호당 is_latest_seq=1 이 정확히 1행인지 (0행이어야 정상)
SELECT contract_no, SUM(is_latest_seq) AS latest_cnt
FROM clean_dapa_contract
GROUP BY contract_no
HAVING latest_cnt <> 1;


-- ============================================================================
-- 2. raw_dapa_bid_notice  →  clean_dapa_bid_notice (신설)
-- ============================================================================

-- 2-1. 생김새
SELECT * FROM raw_dapa_bid_notice LIMIT 20;

-- 2-2. 키 후보 비교  (기대: 참조공고번호+차수 고유 10,842 = 행 수 → 실제 키 / 공고번호+차수 고유 10,486 → 중복 초과 356)
SELECT COUNT(*)                                            AS rows_total,
       COUNT(DISTINCT ref_notice_no, ref_notice_seq)       AS ref_key_unique,
       COUNT(DISTINCT bid_notice_no, bid_notice_seq)       AS notice_key_unique,
       COUNT(*) - COUNT(DISTINCT bid_notice_no, bid_notice_seq) AS notice_key_dup_excess
FROM raw_dapa_bid_notice;

-- 2-3. 공고번호+차수 중복 사례 (같은 번호가 다른 연도에 재사용되는지)
SELECT bid_notice_no, bid_notice_seq, COUNT(*) AS n,
       GROUP_CONCAT(DISTINCT LEFT(bid_notice_date, 4)) AS years,
       GROUP_CONCAT(ref_notice_no) AS ref_nos
FROM raw_dapa_bid_notice
GROUP BY bid_notice_no, bid_notice_seq
HAVING COUNT(*) > 1
ORDER BY n DESC
LIMIT 30;

-- 2-4. 열 밀림 2행 찾기  (기대: 공고일자 NULL 이거나 계약방법이 'Y', 여부 열에 날짜)  → COL_SHIFT 사유로 격리
SELECT row_id, bid_notice_no, bid_notice_seq, ref_notice_no, bid_notice_date,
       joint_contract_yn, contract_method_name, briefing_yn, region_limit_yn
FROM raw_dapa_bid_notice
WHERE bid_notice_date IS NULL
   OR bid_notice_date NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
   OR joint_contract_yn NOT IN ('Y', 'N')
   OR contract_method_name = 'Y';

-- 2-5. 여부(Y/N) 열 값 분포 — 정상 값 외가 나오면 밀림 행
SELECT joint_contract_yn, e_bid_yn, briefing_yn, region_limit_yn, g2b_notice_yn, COUNT(*) AS n
FROM raw_dapa_bid_notice
GROUP BY joint_contract_yn, e_bid_yn, briefing_yn, region_limit_yn, g2b_notice_yn
ORDER BY n DESC;

-- 2-6. 공고월 × 상태  (기대 합계 10,840 = 밀림 2 제외 · 긴급 5,677 · 재공고 1,409)
SELECT LEFT(bid_notice_date, 7) AS ym, bid_notice_status_name, COUNT(*) AS n
FROM raw_dapa_bid_notice
WHERE bid_notice_date REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
GROUP BY ym, bid_notice_status_name
ORDER BY ym, bid_notice_status_name;

SELECT bid_notice_status_name, COUNT(*) AS n
FROM raw_dapa_bid_notice
GROUP BY bid_notice_status_name ORDER BY n DESC;

-- 2-7. 예산금액·배정예산 숫자 변환 가능 여부
SELECT
  SUM(budget_amount           IS NULL OR budget_amount           = '' OR REPLACE(budget_amount,           ',', '') NOT REGEXP '^[0-9]+$') AS bad_budget,
  SUM(allocated_budget_amount IS NULL OR allocated_budget_amount = '' OR REPLACE(allocated_budget_amount, ',', '') NOT REGEXP '^[0-9]+$') AS bad_allocated
FROM raw_dapa_bid_notice;

-- 2-8. 면허제한그룹 8열 채움 정도 (clean 에 넣을지 판단)
SELECT
  SUM(license_limit_group1 <> '' AND license_limit_group1 IS NOT NULL) AS g1,
  SUM(license_limit_group2 <> '' AND license_limit_group2 IS NOT NULL) AS g2,
  SUM(license_limit_group3 <> '' AND license_limit_group3 IS NOT NULL) AS g3,
  SUM(license_limit_group4 <> '' AND license_limit_group4 IS NOT NULL) AS g4,
  SUM(license_limit_group5 <> '' AND license_limit_group5 IS NOT NULL) AS g5,
  SUM(license_limit_group6 <> '' AND license_limit_group6 IS NOT NULL) AS g6,
  SUM(license_limit_group7 <> '' AND license_limit_group7 IS NOT NULL) AS g7,
  SUM(license_limit_group8 <> '' AND license_limit_group8 IS NOT NULL) AS g8
FROM raw_dapa_bid_notice;

-- 2-9. 기존 뷰 결과와 대조 (2026-09-17 적용)
SELECT * FROM v_bid_notice_monthly LIMIT 30;


-- ============================================================================
-- 3. raw_dapa_bid_result  →  clean_dapa_bid_result (신설)
-- ============================================================================

-- 3-1. 생김새
SELECT * FROM raw_dapa_bid_result LIMIT 20;

-- 3-2. 키 고유성  (기대: 행 7,405 · 키(공고번호+차수) 고유 7,201 · 중복 초과 204)
SELECT COUNT(*) AS rows_total,
       COUNT(DISTINCT bid_notice_no, bid_notice_seq) AS key_unique,
       COUNT(*) - COUNT(DISTINCT bid_notice_no, bid_notice_seq) AS dup_excess
FROM raw_dapa_bid_result;

-- 3-3. 중복 키 성격 분류  (실측 2026-09-18: 199키 403행 = 결과 상이 73 · 복수 낙찰 108(결과 같고 낙찰자 여럿) · 동일 결과 반복 18(결과·낙찰자 같음; 개찰일 다름 16키 + 같은 날 기초금액만 다름 2키 6행). 완전 중복(27열 동일) 0)
--      3분류 집계는 아래 3-3b. 두 번째 유형이 예전 기록(108·73)에서 18키가 빠져 있던 원인 = "결과 같고 낙찰자 1명" 조합을 세지 않음
SELECT bid_notice_no, bid_notice_seq, COUNT(*) AS n,
       COUNT(DISTINCT opening_result_name) AS result_kinds,
       COUNT(DISTINCT winner_biz_reg_no)   AS winner_kinds,
       GROUP_CONCAT(DISTINCT opening_result_name) AS results
FROM raw_dapa_bid_result
GROUP BY bid_notice_no, bid_notice_seq
HAVING COUNT(*) > 1
ORDER BY n DESC;

-- 3-3b. 3분류 집계  (실측: keys 199 / rows 403 / 결과 상이 73 / 복수 낙찰 108 / 동일 결과 반복 18)
WITH k AS (
  SELECT bid_notice_no, bid_notice_seq, COUNT(*) AS n,
         COUNT(DISTINCT opening_result_name) AS n_result,
         COUNT(DISTINCT COALESCE(winner_biz_reg_no, '')) AS n_winner
  FROM raw_dapa_bid_result GROUP BY 1, 2 HAVING n > 1)
SELECT COUNT(*) AS keys_, SUM(n) AS rows_,
       SUM(n_result > 1)                 AS result_differs,          -- dup_kind '결과 상이'
       SUM(n_result = 1 AND n_winner > 1) AS same_result_multi_winner, -- dup_kind '복수 낙찰'
       SUM(n_result = 1 AND n_winner = 1) AS same_result_same_winner   -- 세 번째 유형(ENUM 미정의 → schema-design §7-23)
FROM k;

-- 3-4. 개찰결과 검산  (기대: 유찰 1,746 + 개찰완료 5,275 + 순위확정 382 + 데이터오류(날짜값) 2 = 7,405)
SELECT opening_result_name, COUNT(*) AS n
FROM raw_dapa_bid_result
GROUP BY opening_result_name
ORDER BY n DESC;

-- 3-5. 열 밀림 2행  (기대: LCF0223 1·2차 — 개찰결과 열에 날짜, 적격심사여부 '제한경쟁')  → COL_SHIFT 격리
SELECT row_id, bid_notice_no, bid_notice_seq, bid_notice_name,
       qualification_review_yn, opening_result_name, final_award_amount, final_award_rate
FROM raw_dapa_bid_result
WHERE opening_result_name NOT IN ('유찰', '개찰완료', '순위확정')
   OR qualification_review_yn NOT IN ('Y', 'N');

SELECT * FROM raw_dapa_bid_result WHERE bid_notice_no LIKE '%LCF0223%';

-- 3-6. 낙찰금액·낙찰률 숫자 변환 가능 여부 (비숫자·공란 2,154 = 유찰 포함이면 정상)
SELECT
  SUM(final_award_amount IS NULL OR final_award_amount = '' OR REPLACE(final_award_amount, ',', '') NOT REGEXP '^[0-9]+$') AS bad_amount,
  SUM(final_award_rate   IS NULL OR final_award_rate   = '' OR final_award_rate NOT REGEXP '^[0-9.]+$')                  AS bad_rate
FROM raw_dapa_bid_result;

-- 3-7. 공고↔결과 연결률  — 단위 두 가지 모두 기록
--   (a) 행 기준: 결과 7,405행 중 공고(bid_notice_no+seq) 존재 행 수  (명세 기대: 7,072 = 95.5%)
SELECT COUNT(*) AS result_rows,
       SUM(EXISTS (SELECT 1 FROM raw_dapa_bid_notice n
                   WHERE n.bid_notice_no = r.bid_notice_no AND n.bid_notice_seq = r.bid_notice_seq)) AS matched_rows
FROM raw_dapa_bid_result r;

--   (b) 키 기준: 기존 뷰 (기대: 7,201키 → 1:1 6,569 · 다중 303 · 미연결 329)
SELECT * FROM v_bid_notice_result_link;

-- 3-8. 낙찰업체 사업자번호 → 계약정보 존재  (기대: 낙찰업체 3,210 중 3,094 존재)
SELECT COUNT(DISTINCT r.winner_biz_reg_no) AS winners,
       COUNT(DISTINCT c.vendor_biz_reg_no) AS winners_in_contract
FROM raw_dapa_bid_result r
LEFT JOIN raw_dapa_contract c ON c.vendor_biz_reg_no = r.winner_biz_reg_no
WHERE r.winner_biz_reg_no IS NOT NULL AND r.winner_biz_reg_no <> '';

-- 3-9. 기존 뷰 결과 (개찰연도×물품/용역×개찰결과)
SELECT * FROM v_bid_result_summary;


-- ============================================================================
-- 4. raw_dapa_domestic_plan  →  clean_dapa_domestic_plan (신설)
-- ============================================================================

-- 4-1. 생김새
SELECT * FROM raw_dapa_domestic_plan LIMIT 20;

-- 4-2. 연도별 행 수·예산  (기대: 2024 4,545행 1.075조(불완전 라벨) / 2025 31,314행 8.558조)
SELECT LEFT(plan_month, 4) AS yr, COUNT(*) AS n,
       SUM(CAST(REPLACE(budget_amount, ',', '') AS UNSIGNED)) AS budget_krw
FROM raw_dapa_domestic_plan
GROUP BY yr;

-- 4-3. plan_month 형식 (YYYY-MM-01 이 아닌 값)
SELECT plan_month, COUNT(*) AS n
FROM raw_dapa_domestic_plan
WHERE plan_month IS NULL OR plan_month NOT REGEXP '^[0-9]{4}-[0-9]{2}-01$'
GROUP BY plan_month;

-- 4-4. 집행유형·계약방법·진행상태 값 분포 (표준값 정하기; 기대: 2025 계약완료 24,013)
SELECT exec_type, COUNT(*) AS n FROM raw_dapa_domestic_plan GROUP BY exec_type ORDER BY n DESC;
SELECT contract_method, COUNT(*) AS n FROM raw_dapa_domestic_plan GROUP BY contract_method ORDER BY n DESC;
SELECT progress_status, COUNT(*) AS n FROM raw_dapa_domestic_plan GROUP BY progress_status ORDER BY n DESC;

-- 4-5. 판단번호 고유성 (같은 판단번호가 여러 행이면 품목 단위인지 확인)
SELECT COUNT(*) AS rows_total, COUNT(DISTINCT decision_no) AS decision_unique
FROM raw_dapa_domestic_plan;

-- 4-6. 개인정보 열이 실제로 NULL 인지 (기대: 전부 NULL → clean 에서 열 제외)
SELECT SUM(officer_name IS NOT NULL) AS officer_name_filled,
       SUM(officer_phone IS NOT NULL) AS officer_phone_filled
FROM raw_dapa_domestic_plan;

-- 4-7. 예산금액 숫자 변환 가능 여부
SELECT SUM(budget_amount IS NULL OR budget_amount = '' OR REPLACE(budget_amount, ',', '') NOT REGEXP '^[0-9]+$') AS bad_budget
FROM raw_dapa_domestic_plan;

-- 4-8. 기존 뷰
SELECT * FROM v_domestic_plan_yearly;


-- ============================================================================
-- 5. raw_dapa_contract_exec_by_service  →  clean_dapa_contract_exec_by_service (신설, 연도×군 세로형)
-- ============================================================================

-- 5-1. 전체 (40행이라 그대로 본다)  (기대: 2015~2024 × 육군/해군/공군/국직)
SELECT * FROM raw_dapa_contract_exec_by_service ORDER BY year, service_branch;

-- 5-2. 군 구분 표기 확인 → 표준값(육군/해군/공군/국직)
SELECT service_branch, COUNT(*) AS n FROM raw_dapa_contract_exec_by_service GROUP BY service_branch;

-- 5-3. 연도×군 고유성 (기대: 40 = 40)
SELECT COUNT(*) AS rows_total, COUNT(DISTINCT year, service_branch) AS key_unique
FROM raw_dapa_contract_exec_by_service;

-- 5-4. 금액 숫자 변환 (억원 단위 → 열 이름 _100m_krw 유지)
SELECT year, service_branch, contract_amount_100m_krw,
       CAST(REPLACE(contract_amount_100m_krw, ',', '') AS DECIMAL(14,1)) AS amount_100m_krw
FROM raw_dapa_contract_exec_by_service
ORDER BY year, service_branch;


-- ============================================================================
-- 6. raw_dapa_defense_company  →  clean_company · clean_company_name_link
-- ============================================================================

-- 6-1. 전체 (84행)
SELECT * FROM raw_dapa_defense_company ORDER BY CAST(seq_no AS UNSIGNED);

-- 6-2. 분야 분포 (기대: v_defense_company_sector 와 동일)
SELECT sector, COUNT(*) AS n FROM raw_dapa_defense_company GROUP BY sector ORDER BY n DESC;
SELECT * FROM v_defense_company_sector;

-- 6-3. 업체 마스터 후보: 사업자번호 있는 출처 두 개 합치기  (계약정보 + 입찰결과 낙찰업체)
--      같은 사업자번호에 업체명 표기가 여러 개면 가장 많이 쓰인 원문을 name_raw 로
SELECT biz_reg_no, COUNT(DISTINCT name_raw) AS name_variants, GROUP_CONCAT(DISTINCT name_raw) AS names
FROM (
  SELECT vendor_biz_reg_no AS biz_reg_no, vendor_name AS name_raw FROM raw_dapa_contract
  UNION ALL
  SELECT winner_biz_reg_no, winner_name FROM raw_dapa_bid_result
) u
WHERE biz_reg_no IS NOT NULL AND biz_reg_no <> ''
GROUP BY biz_reg_no
HAVING name_variants > 1
ORDER BY name_variants DESC
LIMIT 50;

-- 6-4. 마스터 규모 (사업자번호 고유 수)
SELECT COUNT(DISTINCT biz_reg_no) AS company_unique
FROM (
  SELECT vendor_biz_reg_no AS biz_reg_no FROM raw_dapa_contract
  UNION ALL
  SELECT winner_biz_reg_no FROM raw_dapa_bid_result
) u
WHERE biz_reg_no IS NOT NULL AND biz_reg_no <> '';

-- 6-5. name_norm 규칙 초안 시험 — 법인격 표기 제거·공백 제거. (P5 이동현과 같은 규칙 공유, 9/24)
--      아래 REPLACE 체인은 초안이며, 규칙을 확정하면 노트북 함수와 똑같이 맞출 것
--      2026-09-18: 6-5(8치환)와 6-6(3치환)이 달라 db/query_p4_join_check.sql D 의 5치환((주)·㈜·주식회사·(유)·유한회사 → 공백 제거)으로 통일한다. 실측 exact 49 / multi 2 / none 33 은 그 규칙 기준
SELECT company_name,
       REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(company_name,
         '주식회사', ''), '(주)', ''), '㈜', ''), '유한회사', ''), '(유)', ''), '재단법인', ''), '사단법인', ''), ' ', '') AS name_norm_draft
FROM raw_dapa_defense_company
ORDER BY company_name;

-- 6-6. 방산업체 84 → 계약정보 업체명 exact 매칭 시험 (사업자번호 없는 매칭 = 「후보」)
SELECT d.company_name,
       COUNT(DISTINCT c.vendor_biz_reg_no) AS match_count,
       GROUP_CONCAT(DISTINCT c.vendor_biz_reg_no) AS biz_reg_nos
FROM raw_dapa_defense_company d
LEFT JOIN raw_dapa_contract c
  ON REPLACE(REPLACE(REPLACE(c.vendor_name, '주식회사', ''), '(주)', ''), ' ', '')
   = REPLACE(REPLACE(REPLACE(d.company_name, '주식회사', ''), '(주)', ''), ' ', '')
GROUP BY d.company_name
ORDER BY match_count DESC, d.company_name;
--   match_count 0 → none / 1 → exact / 2+ → multi  → clean_company_name_link.match_type

-- 6-7. clean 목표 테이블 정의
SHOW CREATE TABLE clean_company;
SHOW CREATE TABLE clean_company_name_link;


-- ============================================================================
-- 7. 기록 테이블 (⑥ DATA INFO 탭) — 적재할 때마다 1행씩
-- ============================================================================
SELECT * FROM meta_load_log ORDER BY log_id DESC LIMIT 20;
SELECT * FROM meta_column_dict WHERE table_name LIKE 'clean_dapa_%' OR table_name LIKE 'clean_company%';
SHOW CREATE TABLE meta_load_log;
SHOW CREATE TABLE meta_column_dict;
