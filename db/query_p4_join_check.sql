-- ============================================================================
-- P4(김훈희) 방사청 국내조달·업체 — 조인 키 값 검증(뷰 생성 가능성) 복붙용 쿼리 (2026-09-18)
--   목적: clean_ 이 비어 있는 상태에서 raw 값으로 "엮으려는 표끼리 키 값이 실제로 맞아 뷰를 만들 수 있는가"를 판정한다.
--         건수·열 존재만 맞추는 구조 검증(query_p4_domestic_explore.sql)과 구분한다.
--   축:   A 사업자등록번호 · B 공고↔결과 · C 주소→시도 · D 업체명→업체 마스터 · E 계약 이력 · F 조달계획·군별
--   주석의 실측값은 2026-09-18 RDS(MySQL 8.4.11, app_ro/DBHub) 결과. 전부 읽기 전용, 한 블록씩 복사해 실행.
--   상관 서브쿼리 EXISTS 는 인덱스가 없어 타임아웃이 나므로 파생표 JOIN 으로 쓴다.
--   판정 요약과 문서 반영: docs/reference/data-cleaning-rules.md §2-2·§2-9·§2-10·§3, docs/db/schema-change-log.md §7-22.
-- ============================================================================

USE defense_dashboard;

-- ============================================================================
-- A. 사업자등록번호 축 — contract.vendor_biz_reg_no ↔ bid_result.winner_biz_reg_no ↔ clean_company.biz_reg_no CHAR(12)
--    판정: 조인 가능, 정규화 불필요 (양쪽 100% 'NNN-NN-NNNNN' 12자)
-- ============================================================================

-- A-1. 계약정보 형식.  실측: 43,112행 / NULL 0 / 빈값 0 / 12자 43,112 / 하이픈 패턴 43,112 / 고유 14,723(정규화 후에도 14,723)
SELECT COUNT(*) AS total_rows,
       SUM(vendor_biz_reg_no IS NULL) AS n_null,
       SUM(vendor_biz_reg_no IS NOT NULL AND TRIM(vendor_biz_reg_no) = '') AS n_empty,
       SUM(vendor_biz_reg_no REGEXP '^[0-9]{3}-[0-9]{2}-[0-9]{5}$') AS n_pattern_hyphen,
       COUNT(DISTINCT vendor_biz_reg_no) AS n_distinct_raw,
       COUNT(DISTINCT REGEXP_REPLACE(COALESCE(vendor_biz_reg_no, ''), '[^0-9]', '')) AS n_distinct_norm
FROM raw_dapa_contract;
SELECT LENGTH(vendor_biz_reg_no) AS len, COUNT(*) AS n FROM raw_dapa_contract GROUP BY len;

-- A-2. 입찰결과 형식 + 개찰결과별 NULL.  실측: 12자 5,275 / NULL 2,129 / 9자 1(열 밀림 행) / 고유 3,210
--      NULL 2,129 = 유찰 1,746(100%) + 순위확정 382(100%) + 열 밀림 1 → 결측이 아니라 낙찰업체가 없는 구조적 NULL
SELECT LENGTH(winner_biz_reg_no) AS len, COUNT(*) AS n FROM raw_dapa_bid_result GROUP BY len;
SELECT opening_result_name, COUNT(*) AS n,
       SUM(winner_biz_reg_no IS NULL OR TRIM(winner_biz_reg_no) = '') AS n_null_or_empty,
       ROUND(100 * SUM(winner_biz_reg_no IS NULL OR TRIM(winner_biz_reg_no) = '') / COUNT(*), 1) AS pct_null
FROM raw_dapa_bid_result GROUP BY opening_result_name ORDER BY n DESC;

-- A-3. 두 표 교집합(정규화 전/후).  실측: contract 고유 14,723 / result 고유 3,210 / 교집합 3,094 / 정규화 후 3,094(변화 없음)
--      → 낙찰업체 3,210 중 3,094 계약정보 존재(96.4%). 분모 3,210에는 열 밀림 1건(9자)이 포함되며 유효 분모 3,209 기준으로도 96.4%
WITH c  AS (SELECT DISTINCT vendor_biz_reg_no AS v FROM raw_dapa_contract),
     r  AS (SELECT DISTINCT winner_biz_reg_no AS v FROM raw_dapa_bid_result WHERE winner_biz_reg_no IS NOT NULL),
     cn AS (SELECT DISTINCT REGEXP_REPLACE(vendor_biz_reg_no, '[^0-9]', '') AS v FROM raw_dapa_contract),
     rn AS (SELECT DISTINCT REGEXP_REPLACE(winner_biz_reg_no, '[^0-9]', '') AS v FROM raw_dapa_bid_result WHERE winner_biz_reg_no IS NOT NULL)
SELECT (SELECT COUNT(*) FROM c) AS contract_distinct,
       (SELECT COUNT(*) FROM r) AS result_distinct,
       (SELECT COUNT(*) FROM r JOIN c ON c.v = r.v) AS intersect_raw,
       (SELECT COUNT(*) FROM rn JOIN cn ON cn.v = rn.v) AS intersect_norm;

-- A-4. 같은 사업자번호에 업체명이 여러 개인가(두 표 합산).  실측: 고유 사업자 14,839(계약 14,723 + 결과에만 116) / 표기 변이 0건(최대 1)
--      → clean_company.name_raw 에 "가장 많이 쓰인 원문" 집계 규칙이 필요 없다(임의 1개 = 유일값)
WITH u AS (
  SELECT REGEXP_REPLACE(vendor_biz_reg_no, '[^0-9]', '') AS biz, TRIM(vendor_name) AS nm FROM raw_dapa_contract
  UNION ALL
  SELECT REGEXP_REPLACE(winner_biz_reg_no, '[^0-9]', ''), TRIM(winner_name) FROM raw_dapa_bid_result WHERE winner_biz_reg_no IS NOT NULL
), g AS (SELECT biz, COUNT(DISTINCT nm) AS n_names FROM u GROUP BY biz)
SELECT COUNT(*) AS distinct_biz_union, SUM(n_names > 1) AS multi_name, MAX(n_names) AS max_names FROM g;


-- ============================================================================
-- B. 공고↔결과 축 — bid_result.(bid_notice_no, bid_notice_seq) ↔ bid_notice.(bid_notice_no, bid_notice_seq)
--    판정: 키 단위 요약 뷰만 가능. 행 단위 1:1 조인은 불가(다중 303키에서 행 증식 → 금액 중복 합산)
-- ============================================================================

-- B-1. 차수 형식.  실측: 세 열 모두 '1'~'6' 한 자리(0/00/01 혼재 없음). notice.bid_notice_seq = ref_notice_seq 분포 동일(1:8,107 / 2:2,489 / 3:205 / 4:35 / 5:6)
--      → *_seq_norm CHAR(2) 의 LPAD 는 무해하지만 매칭 수를 바꾸지 않는다
SELECT 'notice.bid_notice_seq' AS col, bid_notice_seq AS val, COUNT(*) AS n FROM raw_dapa_bid_notice GROUP BY val
UNION ALL SELECT 'notice.ref_notice_seq', ref_notice_seq, COUNT(*) FROM raw_dapa_bid_notice GROUP BY ref_notice_seq
UNION ALL SELECT 'result.bid_notice_seq', bid_notice_seq, COUNT(*) FROM raw_dapa_bid_result GROUP BY bid_notice_seq
ORDER BY col, val;

-- B-2. 행 단위 조인 산출 행 수(정규화 전/후).  실측: 7,545 / 7,545 (결과 7,405행보다 140 많음 = 다중 키 증식)
SELECT (SELECT COUNT(*) FROM raw_dapa_bid_result r JOIN raw_dapa_bid_notice n
          ON n.bid_notice_no = r.bid_notice_no AND n.bid_notice_seq = r.bid_notice_seq) AS join_plain,
       (SELECT COUNT(*) FROM raw_dapa_bid_result r JOIN raw_dapa_bid_notice n
          ON n.bid_notice_no = r.bid_notice_no AND LPAD(n.bid_notice_seq, 2, '0') = LPAD(r.bid_notice_seq, 2, '0')) AS join_lpad;

-- B-3. 결과 행 기준 매칭(명세 KPI).  실측: 7,405행 중 매칭 7,072 / 미매칭 333 (95.5%)
WITH nk AS (SELECT bid_notice_no, bid_notice_seq, COUNT(*) AS n_notice FROM raw_dapa_bid_notice GROUP BY 1, 2)
SELECT COUNT(*) AS result_rows, SUM(nk.n_notice IS NOT NULL) AS matched, SUM(nk.n_notice IS NULL) AS unmatched
FROM raw_dapa_bid_result r
LEFT JOIN nk ON nk.bid_notice_no = r.bid_notice_no AND nk.bid_notice_seq = r.bid_notice_seq;

-- B-4. 결과 키 기준(v_bid_notice_result_link 와 동일 정의).  실측: 7,201키 = 1:1 6,569 / 다중 303(결과 473행) / 미연결 329(결과 333행)
SELECT CASE WHEN n.cnt IS NULL THEN '미연결' WHEN n.cnt = 1 THEN '1:1' ELSE '다중' END AS link_type,
       COUNT(*) AS n_result_keys, SUM(r.cnt) AS n_result_rows
FROM (SELECT bid_notice_no, bid_notice_seq, COUNT(*) AS cnt FROM raw_dapa_bid_result GROUP BY 1, 2) r
LEFT JOIN (SELECT bid_notice_no, bid_notice_seq, COUNT(*) AS cnt FROM raw_dapa_bid_notice GROUP BY 1, 2) n
  ON n.bid_notice_no = r.bid_notice_no AND n.bid_notice_seq = r.bid_notice_seq
GROUP BY link_type;

-- B-5. 참조공고번호로 더 이을 수 있는가.  실측: bid_notice_no 는 7자(AAA9999 10,803 / AA99999 39), ref_notice_no 는 14~16자.
--      RIGHT(ref_notice_no, 7) = bid_notice_no → 0건.  LOCATE(bid_notice_no, ref_notice_no) = 5 → 10,842건 전부
--      → ref_notice_no = [연도 4][bid_notice_no 7][꼬리 4~5]. 공고표 내부 파생일 뿐이고 결과표에는 열이 없어 추가 연결 0 → 행 단위 연결 보류 유지
SELECT COUNT(*) AS rows_all,
       SUM(RIGHT(ref_notice_no, LENGTH(bid_notice_no)) = bid_notice_no) AS suffix_match,
       SUM(SUBSTRING(ref_notice_no, 5, 7) = bid_notice_no) AS pos5_match
FROM raw_dapa_bid_notice;
SELECT LENGTH(bid_notice_no) AS len, COUNT(*) AS n FROM raw_dapa_bid_result GROUP BY len;


-- ============================================================================
-- C. 주소 → 시도 축 — SUBSTRING_INDEX(TRIM(주소),' ',1) ↔ ref_sido_map.token
--    판정: 조인 가능. 미매핑은 sido_code NULL 로 두고 건수를 표기(값 추정 금지)
-- ============================================================================

-- C-1. 계약정보 커버리지.  실측: 매핑 43,092행(25토큰) / 미매핑 20행(4토큰) = 99.95%. 주소 NULL 0·빈값 0
--      미매핑 토큰: 충남대전시 16 · 용산구 2 · ** 1 · 1 1  → ref_sido_map 보강은 P2(명세 §7, 9/23) 판단. 임의 매핑하지 않는다
WITH t AS (SELECT SUBSTRING_INDEX(TRIM(vendor_address), ' ', 1) AS token FROM raw_dapa_contract
           WHERE vendor_address IS NOT NULL AND TRIM(vendor_address) <> '')
SELECT (t.token IN (SELECT token FROM ref_sido_map)) AS in_map, COUNT(*) AS n_rows, COUNT(DISTINCT t.token) AS n_tokens
FROM t GROUP BY in_map;
WITH t AS (SELECT SUBSTRING_INDEX(TRIM(vendor_address), ' ', 1) AS token FROM raw_dapa_contract)
SELECT t.token, COUNT(*) AS n FROM t LEFT JOIN ref_sido_map m ON m.token = t.token
WHERE m.token IS NULL GROUP BY t.token ORDER BY n DESC;

-- C-2. 낙찰업체 주소 커버리지(사업자번호 있는 행).  실측: 5,275 / 5,276 = 99.98%, 미매핑 1행 = 열 밀림 행(첫 토큰이 인명)
--      → clean 단계에서 열 밀림 2행을 COL_SHIFT 로 먼저 제외하면 A·C 축 모두 100%
WITH t AS (SELECT SUBSTRING_INDEX(TRIM(winner_address), ' ', 1) AS token FROM raw_dapa_bid_result
           WHERE winner_biz_reg_no IS NOT NULL AND winner_address IS NOT NULL AND TRIM(winner_address) <> '')
SELECT (t.token IN (SELECT token FROM ref_sido_map)) AS in_map, COUNT(*) AS n_rows, COUNT(DISTINCT t.token) AS n_tokens
FROM t GROUP BY in_map;


-- ============================================================================
-- D. 업체명 → 업체 마스터 축 — 사업자번호 없는 출처(방산업체 지정현황 · B2 계약업체) → name_norm → clean_company
--    판정: 정규화 후 가능. 연결률·다중·미연결을 반드시 병기(data-cleaning-rules.md §3)
--    name_norm 잠정 규칙(2026-09-18, P5와 9/24 공유 전까지): (주)·㈜·주식회사·(유)·유한회사 제거 후 공백 제거.
--    query_p4_domestic_explore.sql 6-5(재단법인·사단법인 포함 8치환)·6-6(3치환)은 이 규칙으로 통일한다.
-- ============================================================================

-- D-1. 방산업체 84건 법인격 표기.  실측: (주) 0 · ㈜ 0 · 주식회사 0 · (유)/유한회사 0 → 전부 순수 상호
--      계약정보 vendor_name 은 주식회사 17,539행 · (주) 6,623 · (유)/유한회사 324 · ㈜ 16 → 정규화 없이는 원문 일치 2/84
SELECT SUM(company_name LIKE '%(주)%') AS n_ju_paren, SUM(company_name LIKE '%㈜%') AS n_ju_sym,
       SUM(company_name LIKE '%주식회사%') AS n_ju_full, SUM(company_name LIKE '%(유)%' OR company_name LIKE '%유한회사%') AS n_yu
FROM raw_dapa_defense_company;

-- D-2. 방산업체 → 계약정보 exact/multi/none.  실측: exact 49 / multi 2 / none 33 (연결률 60.7%)
--      → clean_company_name_link.match_type 배분(연결률 = exact 49/84 = 58.3%, multi 2 별도). none 33 중 LIKE 부분포함 후보 5, 나머지 28은 계약정보에 후보 없음
WITH dc AS (
  SELECT company_name,
         REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(company_name), '(주)', ''), '㈜', ''), '주식회사', ''), '(유)', ''), '유한회사', ''), ' ', '') AS nn
  FROM raw_dapa_defense_company),
ct AS (
  SELECT REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(vendor_name), '(주)', ''), '㈜', ''), '주식회사', ''), '(유)', ''), '유한회사', ''), ' ', '') AS nn,
         COUNT(DISTINCT vendor_biz_reg_no) AS n_biz
  FROM raw_dapa_contract GROUP BY 1)
SELECT COUNT(*) AS dc_rows, SUM(ct.n_biz = 1) AS exact_n, SUM(ct.n_biz > 1) AS multi_n, SUM(ct.nn IS NULL) AS none_n
FROM dc LEFT JOIN ct ON ct.nn = dc.nn;

-- D-3. B2 계약업체(raw_dapa_localized_item.contractor_name) → 계약정보.  실측: 공란 123행 / 고유 407 → 정규화 후 403
--      고유 업체 일치 128 / 403 = 31.8%,  행 기준 21,635 / 33,842 = 63.9%  → 뷰에 연결률·미연결 수 노출 필수
WITH li AS (
  SELECT REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(contractor_name), '(주)', ''), '㈜', ''), '주식회사', ''), '(유)', ''), '유한회사', ''), ' ', '') AS nn
  FROM raw_dapa_localized_item WHERE contractor_name IS NOT NULL AND TRIM(contractor_name) <> ''),
ct AS (
  SELECT DISTINCT REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(vendor_name), '(주)', ''), '㈜', ''), '주식회사', ''), '(유)', ''), '유한회사', ''), ' ', '') AS nn
  FROM raw_dapa_contract)
SELECT COUNT(*) AS li_rows, SUM(ct.nn IS NOT NULL) AS li_rows_matched,
       COUNT(DISTINCT li.nn) AS li_distinct, COUNT(DISTINCT CASE WHEN ct.nn IS NOT NULL THEN li.nn END) AS li_distinct_matched
FROM li LEFT JOIN ct ON ct.nn = li.nn;


-- ============================================================================
-- E. 계약 이력 축 — contract_no × LPAD(contract_seq,2,'0') → is_latest_seq
--    판정: 가능. 형 변환 실패 0
-- ============================================================================

-- E-1. 최대 차수 행 유일성.  실측: 계약번호 37,608 / 최대차수 행 1개 37,607 / 충돌 1(2024UMM1504-01 2행)
WITH m  AS (SELECT contract_no, LPAD(contract_seq, 2, '0') AS seq_p FROM raw_dapa_contract),
     mx AS (SELECT contract_no, MAX(seq_p) AS max_seq FROM m GROUP BY contract_no),
     cnt AS (SELECT m.contract_no, COUNT(*) AS n FROM m JOIN mx ON mx.contract_no = m.contract_no AND mx.max_seq = m.seq_p GROUP BY 1)
SELECT COUNT(*) AS distinct_no, SUM(n = 1) AS unique_at_max, SUM(n > 1) AS conflict FROM cnt;

-- E-2. 형 변환 가능성.  실측: contract_date 변환 실패 0 / contract_amount 비숫자 0 / contract_period 'YYYY-MM-DD~YYYY-MM-DD'(길이 21) 43,112행 100%
SELECT SUM(STR_TO_DATE(contract_date, '%Y-%m-%d') IS NULL) AS date_fail,
       SUM(contract_amount IS NULL OR NOT contract_amount REGEXP '^[0-9]+$') AS amount_fail,
       SUM(NOT contract_period REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}~[0-9]{4}-[0-9]{2}-[0-9]{2}$') AS period_pattern_fail
FROM raw_dapa_contract;


-- ============================================================================
-- F. 조달계획·군별
-- ============================================================================

-- F-1. 국내 조달계획 키·형식.  실측: 35,859행 / decision_no 고유 35,035(중복 824 → UNIQUE 불가, PK raw_row_id 유지 = schema-design §7-20 ① 종결)
--      (plan_month, decision_no) 고유 35,850 / plan_month 'YYYY-MM-DD' 100%(월이 아니라 날짜) / budget_amount 지수표기 11 · NULL 4,965 / exec_type TRIM 전후 7 = 7(후행 공백 2값: '제조/구매 ' 1,669 · '리스 ' 97)
SELECT COUNT(*) AS n_rows, COUNT(DISTINCT decision_no) AS n_decision,
       COUNT(DISTINCT CONCAT(plan_month, '|', decision_no)) AS n_month_decision,
       SUM(NOT plan_month REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$') AS plan_month_not_date,
       SUM(budget_amount REGEXP '[Ee][+-]?[0-9]') AS budget_sci, SUM(budget_amount IS NULL) AS budget_null,
       COUNT(DISTINCT exec_type) AS exec_raw, COUNT(DISTINCT TRIM(exec_type)) AS exec_trim
FROM raw_dapa_domestic_plan;

-- F-2. 군별 계약집행.  실측: 40행, 육군·해군·공군·국직 각 10, 2015~2024, 억원 숫자 변환 실패 0 (단위 억 원 — 원 단위 표와 합산 금지)
SELECT service_branch, COUNT(*) AS n, MIN(year) AS y_min, MAX(year) AS y_max,
       SUM(NOT contract_amount_100m_krw REGEXP '^[0-9]+(\\.[0-9]+)?$') AS amount_fail
FROM raw_dapa_contract_exec_by_service GROUP BY service_branch;

-- ----------------------------------------------------------------------------
-- 판정 요약(2026-09-18)
--   A 가능(정규화 불필요) · B 키 단위 요약만(행 조인 금지) · C 가능(미매핑 20행 NULL) · D 정규화 후 가능(연결률 병기)
--   E 가능 · F-1 조건부(대리키, plan_month 날짜, 지수표기·NULL 처리) · F-2 가능
--   콜레이션: 관련 14표 전부 utf8mb4_unicode_ci(실측) → 문자열 키 조인 시 1267 위험 없음
-- ----------------------------------------------------------------------------
