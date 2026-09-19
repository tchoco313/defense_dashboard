-- ============================================================================
-- 결측(NULL·빈값·센티널) 프로파일 복붙용 쿼리 (2026-09-19)
--   목적: "NULL ≠ 0"(data-cleaning-rules.md §1 규칙 9, table-guide.md §4-2)을 측정으로 뒷받침한다.
--         열별 NULL 수 / 빈 문자열 수 / 센티널 수 / 고유값 수 / 최소·최대를 한 표당 한 쿼리로 낸다.
--   사용: db-verifier(DBHub app_ro, 1,000행 제한)가 절차 D에서 쓴다. 전부 읽기 전용.
--   판정 4종(결과 옆에 적는다): 의도된 NULL(개인정보 적재 시 NULL, 대응표 없음, 범위 밖 — column_dict.csv description·schema-design.md §2 근거)
--                              / 원본 결측(raw_ 원본이 빈 셀) / 정제 누락(raw_에는 값이 있는데 clean_에서 NULL) / 미확인
--   센티널 후보: '-', '', '0', 'N/A', '미상', '해당없음', '총계'. 코드 열의 'NA'(나미비아)는 결측이 아니다.
-- ============================================================================

USE defense_dashboard;

-- 0. 표의 열 목록·NULL 허용·타입 (프로파일 쿼리를 만들 때 먼저 본다)
SELECT COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clean_dapa_domestic_plan'
ORDER BY ORDINAL_POSITION;

-- 1. 열별 프로파일 SQL 자동 생성 — 결과의 stmt 를 복사해 실행한다 (표 이름만 바꾼다)
SELECT CONCAT(
  'SELECT COUNT(*) AS n_rows',
  GROUP_CONCAT(CONCAT(
    ', SUM(`', COLUMN_NAME, '` IS NULL) AS `', COLUMN_NAME, '__null`',
    CASE WHEN DATA_TYPE IN ('char','varchar','text','enum')
         THEN CONCAT(', SUM(`', COLUMN_NAME, '`=\'\') AS `', COLUMN_NAME, '__blank`',
                     ', SUM(`', COLUMN_NAME, '` IN (\'-\',\'0\',\'N/A\',\'미상\',\'해당없음\')) AS `', COLUMN_NAME, '__sentinel`')
         ELSE '' END,
    ', COUNT(DISTINCT `', COLUMN_NAME, '`) AS `', COLUMN_NAME, '__distinct`'
  ) SEPARATOR ''),
  ' FROM `', TABLE_NAME, '`;') AS stmt
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clean_dapa_domestic_plan'
GROUP BY TABLE_NAME;
-- GROUP_CONCAT 은 기본 1024자에서 잘린다(2026-09-19 실측: clean_dapa_domestic_plan 16열에서 잘림). DBHub 읽기 전용 모드는 SET 을 막을 수 있으므로
--   WHERE 에 AND ORDINAL_POSITION BETWEEN 1 AND 8 처럼 열을 묶음으로 나눠 생성하거나, 콘솔에서는 SET SESSION group_concat_max_len = 65535; 를 먼저 실행한다.

-- 2. 실측 예 — 국내 조달계획 예산(미기재 4,965 = NULL, 0 아님. data-cleaning-rules.md §7)
SELECT COUNT(*) AS n_rows,
       SUM(budget_krw IS NULL) AS budget_null,
       SUM(budget_krw = 0)     AS budget_zero,
       SUM(plan_month IS NULL)    AS plan_month_null,
       SUM(exec_type IS NULL OR exec_type = '') AS exec_type_missing
FROM clean_dapa_domestic_plan;

-- 3. 그룹별 결측률 — 결측이 관측 변수(연도·유형)에 따라 다르면 MCAR 아님(MAR 가능성). stats-advisor 판정 입력.
SELECT plan_year AS yr, exec_type,
       COUNT(*) AS n, SUM(budget_krw IS NULL) AS budget_null,
       ROUND(100 * SUM(budget_krw IS NULL) / COUNT(*), 1) AS null_pct
FROM clean_dapa_domestic_plan
GROUP BY yr, exec_type
ORDER BY yr, exec_type;

-- 4. 공결측 패턴 — 어느 열들이 함께 비는가 (열 3개 예시, 표마다 바꿔 쓴다)
SELECT (budget_krw IS NULL) AS budget_null,
       (exec_type IS NULL OR exec_type = '') AS exec_missing,
       (plan_month IS NULL) AS month_null,
       COUNT(*) AS n
FROM clean_dapa_domestic_plan
GROUP BY 1, 2, 3
ORDER BY n DESC;

-- 5. raw ↔ clean 정제 누락 판정 — raw 에 값이 있는데 clean 에서 NULL 인 행 수 (키는 raw_row_id)
SELECT COUNT(*) AS lost_in_clean
FROM clean_dapa_domestic_plan c
JOIN raw_dapa_domestic_plan r ON r.row_id = c.raw_row_id
WHERE c.budget_krw IS NULL AND r.budget_amount <> '';
-- raw_ 열은 영문 column_name(원본 한글명은 db/column_dict.csv original_name). raw budget_amount(VARCHAR) → clean budget_krw(DECIMAL).

-- 6. 뷰의 NULL — v_review_list B1·B2 는 NULL 과 사유 열이 짝이어야 한다(table-guide.md §4-2)
SELECT b1_status, SUM(b1_target_count IS NULL) AS b1_null, COUNT(*) AS n
FROM v_review_list GROUP BY b1_status;
