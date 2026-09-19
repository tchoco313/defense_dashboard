-- =============================================================================
-- 결측 어휘 확정: 열 사전 85행 + 집계 뷰 4개 미기재 건수 열 + clean_kdsis_nsn.niin 빈 문자열→NULL  (작성 2026-09-20)
--
-- 배경: docs/report/null-profile-2026-09-19.md 가 clean·fact·dim 22표의 결측 77열을 실측해 판정 4종(의도된 NULL·원본 결측·구조적·미확인)과
--       화면 표기·집계 처리를 "제안"으로 남겼다(§2 표·§3 구조적 예외 38행·§5 다음 단계). 2026-09-20 사용자 결정으로 그 제안값을 그대로 확정한다:
--         · 열 사전 description 에 「NULL = <판정> n행(근거) → 화면 「어휘」, 집계 <처리>」 를 적는다(어휘: 미기재 / 판단 보류 / 해당 없음 / 표시 안 함).
--         · 구조적 예외 38행(bid_notice.joint_supply_method_name 2 · briefing_date 3 · bid_result.reserve_price_krw·final_award_rate 24 · contract.private_contract_reason 9)은
--           열 사전에 예외 수를 적고 화면에서 「해당 없음」이 아니라 「미기재」로 구분한다.
--         · clean_kdsis_nsn.niin 빈 문자열 3행은 NULL 로 바꾼다(§5-4). clean_dapa_overseas_plan_api.item_seq 842행은 PK 라 '' 유지 + is_item_seq_missing.
--       수치는 2026-09-20 DBHub 재실측값(09-19 스냅샷과 다른 곳: clean_dapa_contract 43,111→43,105 · sido_code 20→2 · clean_company 4→2 ·
--       clean_dapa_overseas_contract 6,333→6,327 · period_end 731→725 · 수의계약 30,255→30,249. 나머지 열은 동일).
-- 원칙:
--   · data-cleaning-rules.md §1 규칙 #9 「NULL ≠ 0」: 전 행 NULL 인 그룹의 SUM 을 0 으로 바꾸지 않는다(v_bid_notice_monthly 의 COALESCE(…, 0) 제거).
--     미기재는 분모에서 빼고 건수를 병기한다(*_missing_count).
--   · 뷰는 열 사전(meta_column_dict)에 넣지 않는다(alter_2026-09-19_views_to_clean.sql 원칙). 열 사전 85행 = null-profile §2 의 77열 + CSV↔RDS 불일치 8행
--     (ref_hs_whitelist.related_fsc · clean_openfiscal_program_budget 6열 · clean_openfiscal_program_link.program_name — db/column_dict.csv 가 정본).
--   · 문자열 안에 ';' 를 두지 않는다(scripts/apply_alter.py 세미콜론 분리). related_fsc 설명의 ';' 는 CHAR(59 USING utf8mb4) 로 이어 붙인다.
--   · 뷰 이름·기존 출력 열 이름·순서는 유지하고 새 열은 끝에 붙인다. 상위 뷰 v_contract_reason_group_yearly 는 reason_group 분리로 결과 행 18→20.
-- 구조: §1 clean_kdsis_nsn.niin UPDATE + MODIFY COMMENT → §2 뷰 4개 CREATE OR REPLACE(v_contract_monthly · v_contract_private_reason · v_bid_notice_monthly · v_domestic_plan_yearly)
--       → §3 meta_column_dict 85행 INSERT … ON DUPLICATE KEY UPDATE(16표) → §4 검증 SQL(주석)
-- 대상: clean_kdsis_nsn(3행 UPDATE, 열 정의 변경 없음 — COMMENT 만) · 뷰 4개 · meta_column_dict(행 수 849 불변, description 갱신)
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-20_null_vocab.sql   (RDS admin). DBHub(app_ro)는 불가.
-- 기대: 1회차 UPDATE rows=3, 2회차 0 · niin='' 0 · v_bid_notice_monthly 538행/미기재 합 596/예산 합 10,672,865,445,613(전 행 NULL 그룹 46개는 0→NULL) ·
--       v_contract_monthly 28행/amount_missing_count 합 1 · v_domestic_plan_yearly 62행/budget_missing_count 합 4,965 ·
--       v_contract_private_reason 144행 불변, reason_group 해당 없음(경쟁계약) 10,734 + 사유 미기재 9(종전 사유 미기재 10,743) · v_contract_reason_group_yearly 20행 ·
--       meta_column_dict 849. 경고는 deprecated VALUES() 1287 뿐.
-- 되돌리기: §1 은 되돌리지 않는다(규칙 #9). §2 는 db/schema.sql 의 2026-09-19 판 뷰 본문(커밋 7ee01ca 의 db/schema.sql)으로 CREATE OR REPLACE, §3 은 alter_2026-09-19_column_dict_11tables.sql ·
--       alter_2026-09-18_column_dict_gap.sql 등 이전 INSERT 를 다시 실행하면 종전 설명으로 돌아간다(85행 모두 ON DUPLICATE KEY UPDATE).
-- 주의: 이전 alter(alter_2026-09-17_procurement_aux.sql · alter_2026-09-19_views_to_clean.sql)의 뷰 본문은 구판으로 남는다.
--       그 파일들을 재실행하면 이 4개 뷰가 구판으로 돌아가므로 재실행 시 이 파일을 뒤에 다시 적용한다. 정본은 db/schema.sql(이 파일과 본문 동일).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- §1 clean_kdsis_nsn.niin 빈 문자열 → NULL (3행, 멱등). alter_2026-09-17_kdsis_nsn.sql 의 CONCAT(COALESCE(ncb_code,''),COALESCE(iin_serial,'')) 가
--    둘 다 공란인 4자 NSN(5330·5331·5340)에서 '' 를 만들었다. 규칙 #9 상 NULL 이 맞다(null-profile §2·§5-4). 09-17 alter 의 INSERT 도 NULLIF 로 고쳤다.
-- -----------------------------------------------------------------------------
UPDATE clean_kdsis_nsn SET niin = NULL WHERE niin = '';
ALTER TABLE clean_kdsis_nsn MODIFY niin VARCHAR(10) NULL COMMENT 'NCB 2자 + 일련번호 7자 = NSN 뒤 9자리. ncb_code·iin_serial 모두 공란이면 NULL(빈 문자열 아님, 2026-09-20)';

-- -----------------------------------------------------------------------------
-- §2 집계 뷰 4개: 미기재 건수 열 추가 (CREATE OR REPLACE VIEW, 기존 열 순서 유지, 새 열은 끝에). 본문은 db/schema.sql 과 문자 그대로 동일.
--   2-1 v_contract_monthly      + amount_missing_count = SUM(total_contract_amount IS NULL)  (is_latest_seq=1 행 기준, 합 1 기대)
--   2-2 v_contract_private_reason  reason_text · reason_group 에 경쟁계약 분기 추가(해당 없음(경쟁계약) 10,734) — 종전 '사유 미기재' 는 수의계약 9건만 남는다.
--                                  + amount_missing_count = SUM(계약 단위 금액 IS NULL) (합 1 기대).
--                                  전제 실측(09-20): 계약번호 안 계약방법 혼재 0 · 비수의계약에 사유 있음 0 · contract_method_name NULL 0.
--   2-3 v_bid_notice_monthly     COALESCE(SUM(budget_amount_krw), 0) → SUM(budget_amount_krw) (규칙 #9: 전 행 NULL 그룹 46개가 0 으로 나오던 것을 NULL 로)
--                                  + budget_missing_count = SUM(budget_amount_krw IS NULL) (합 596 기대)
--   2-4 v_domestic_plan_yearly   + budget_missing_count = SUM(budget_krw IS NULL) (합 4,965 기대)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_contract_monthly AS
SELECT DATE_FORMAT(f.first_contract_date, '%Y%m') AS yyyymm,
       c.biz_type, c.class5,
       COUNT(*)                     AS contract_count,
       SUM(c.total_contract_amount) AS total_contract_amount,
       SUM(c.total_contract_amount IS NULL) AS amount_missing_count
FROM clean_dapa_contract c
JOIN (SELECT contract_no, MIN(contract_date) AS first_contract_date
      FROM clean_dapa_contract GROUP BY contract_no) f ON f.contract_no = c.contract_no
WHERE c.is_latest_seq = 1
GROUP BY DATE_FORMAT(f.first_contract_date, '%Y%m'), c.biz_type, c.class5;

CREATE OR REPLACE VIEW v_contract_private_reason AS
SELECT c.contract_year, c.contract_method_name, c.biz_type_name, c.reason_group, c.reason_text,
       COUNT(*)                          AS contract_count,
       SUM(c.total_contract_amount_krw)  AS total_contract_amount_krw,
       SUM(c.total_contract_amount_krw IS NULL) AS amount_missing_count
FROM (
  SELECT r.contract_no,
         YEAR(MIN(r.contract_date))                                      AS contract_year,
         MAX(r.contract_method_name)                                     AS contract_method_name,
         MAX(r.biz_type)                                                 AS biz_type_name,
         CASE WHEN MAX(r.contract_method_name) <> '수의계약' THEN '(해당 없음)'
              ELSE COALESCE(NULLIF(MAX(r.private_contract_reason), ''), '(사유 미기재)') END AS reason_text,
         CASE
           WHEN MAX(r.contract_method_name) <> '수의계약'                                                 THEN '해당 없음(경쟁계약)'
           WHEN COALESCE(MAX(r.private_contract_reason), '') = ''                                        THEN '사유 미기재'
           WHEN MAX(r.private_contract_reason) REGEXP '제27조|제28조|특례규정제23조제1호'                   THEN '경쟁실패 후 수의'
           WHEN MAX(r.private_contract_reason) REGEXP '제26조제1항제2호 (자목|사목|아목|바목)|제26조제1항제1호 다목|특례규정제23조제2호|특례규정제23조제4호'
                                                                                                          THEN '단일공급·호환성·특허'
           WHEN MAX(r.private_contract_reason) REGEXP '제26조제1항제5호 가목'                              THEN '소액·소기업'
           WHEN MAX(r.private_contract_reason) REGEXP '제26조제1항제5호 (바목|마목|다목)'                   THEN '기관 간·위탁'
           WHEN MAX(r.private_contract_reason) REGEXP '제26조제1항제3호'                                  THEN '우수·혁신·인증제품'
           WHEN MAX(r.private_contract_reason) REGEXP '제26조제1항제4호'                                  THEN '사회적 배려'
           WHEN MAX(r.private_contract_reason) REGEXP '방위사업법'                                        THEN '방위사업법 특례'
           ELSE '기타' END                                                AS reason_group,
         MAX(CASE WHEN r.is_latest_seq = 1 THEN r.total_contract_amount END) AS total_contract_amount_krw
  FROM clean_dapa_contract r
  GROUP BY r.contract_no
) c
GROUP BY c.contract_year, c.contract_method_name, c.biz_type_name, c.reason_group, c.reason_text;

CREATE OR REPLACE VIEW v_bid_notice_monthly AS
SELECT DATE_FORMAT(bid_notice_date, '%Y-%m')                             AS notice_month,
       bid_notice_status                                                 AS bid_notice_status_name,
       contract_method_name,
       biz_type                                                          AS biz_type_name,
       COUNT(*)                                                          AS notice_count,
       SUM(budget_amount_krw)                                            AS budget_amount_krw,
       SUM(budget_amount_krw IS NULL)                                    AS budget_missing_count
FROM clean_dapa_bid_notice
GROUP BY DATE_FORMAT(bid_notice_date, '%Y-%m'), bid_notice_status, contract_method_name, biz_type;

CREATE OR REPLACE VIEW v_domestic_plan_yearly AS
SELECT plan_year,
       exec_type,
       contract_method,
       COUNT(*)                                                           AS plan_count,
       SUM(budget_krw)                                                    AS budget_krw,
       SUM(is_contracted)                                                 AS contracted_count,
       SUM(is_budget_approx)                                              AS approx_amount_rows,
       SUM(budget_krw IS NULL)                                            AS budget_missing_count
FROM clean_dapa_domestic_plan
GROUP BY plan_year, exec_type, contract_method;

-- -----------------------------------------------------------------------------
-- §3 열 사전 85행 (db/column_dict.csv 와 동일. 생성기: scratchpad gen_null_vocab.py — 커밋하지 않음. 표별 1문, PK (table_name, column_name) 충돌 시 갱신)
--    77행 = null-profile §2 결측 열(description 에 판정·화면 어휘·집계 처리) + 8행 = CSV↔RDS 불일치(설명만 CSV 로 맞춤).
-- -----------------------------------------------------------------------------
-- clean_company (1행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_company', 5, 'sido_code', '(파생)', 'CHAR(2)', 'address → ref_sido_map 적용 결과. NULL = 의도된 NULL 2행(결정: 미매핑 토큰 **·1은 추정 금지, 규칙 §2-2) → 화면 「미기재(시도 미확인)」, 집계 시도별 집계 시 미확인 건수 병기')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_company_name_link (2행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_company_name_link', 5, 'biz_reg_no', '(파생)', 'CHAR(12)', '연결된 clean_company 키(FK). NULL = 구조적 324행(match_type≠exact — multi 14·none 310, 예외 0) → 화면 「해당 없음(미연결)」, 집계 연결률 분모 포함 + 미연결·다중 건수 병기(규칙 §2-10)'),
('clean_company_name_link', 8, 'note', '(파생)', 'VARCHAR(200)', '연결 메모(multi만 기록). NULL = 구조적 477행(match_type≠multi, 예외 0) → 화면 표시 안 함, 집계 무시')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_dapa_bid_notice (7행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_bid_notice', 12, 'joint_supply_method_name', '공동수급방식명', 'VARCHAR(50)', '공동수급 방식. NULL = 구조적 10,350행(joint_contract_yn=0) + 예외 2행(공동계약 490건 중 원본 공란) → 화면 「해당 없음」/예외 「미기재」, 집계 무시(행정 속성, 규칙 §2-9 ✕)'),
('clean_dapa_bid_notice', 24, 'briefing_date', '설명회실시일자', 'DATE', '설명회 일자(시각은 raw). NULL = 구조적 10,707행(briefing_yn=0) + 예외 3행(설명회 실시 133건 중 원본 공란) → 화면 표시 안 함(표시 시 「해당 없음」/예외 「미기재」), 집계 무시'),
('clean_dapa_bid_notice', 25, 'briefing_place', '설명회실시장소', 'VARCHAR(200)', '설명회 장소. NULL = 구조적 10,707행(briefing_yn=0, 예외 0) → 화면 표시 안 함, 집계 무시'),
('clean_dapa_bid_notice', 30, 'budget_amount_krw', '예산금액', 'BIGINT', '공고 예산(원). 낙찰액·계약액과 다름. NULL = 원본 결측 596행(raw 공란) → 화면 「미기재」, 집계 분모 제외 + 미기재 건수 병기(v_bid_notice_monthly.budget_missing_count)'),
('clean_dapa_bid_notice', 31, 'allocated_budget_amount_krw', '배정예산금액(설계금액)', 'BIGINT', '배정예산(원). NULL = 원본 결측 30행(raw 공란, 예산금액도 공란 26) → 화면 「미기재」, 집계 분모 제외'),
('clean_dapa_bid_notice', 33, 'eligible_region_name', '참가가능지역명', 'VARCHAR(200)', '참가 가능 지역. NULL = 구조적 10,840행(region_limit_yn=1 0건, raw도 전 행 공란) → 화면 표시 안 함(정보 없음), 집계 무시'),
('clean_dapa_bid_notice', 35, 'license_limit_groups', '(파생)', 'VARCHAR(2500)', '면허제한 그룹 원문 결합('' | ''). NULL = 구조적 7,336행(license_limit_group_count=0, 예외 0) → 화면 「해당 없음(면허제한 없음)」, 집계 무시(규칙 §2-9 ✕)')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_dapa_bid_result (10행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_bid_result', 18, 'award_lower_limit_rate', '낙찰하한율', 'DECIMAL(7,3)', '낙찰하한율(%). NULL = 원본 결측 654행(raw 공란, 개찰결과 무관 — 유찰 249·개찰완료 376·순위확정 29, 협상 방식 196/330 편중) → 화면 「미기재」, 집계 분모 제외'),
('clean_dapa_bid_result', 19, 'reserve_price_krw', '예정가격', 'BIGINT', '예정가격(원). NULL = 구조적 2,128행(is_awarded=0) + 예외 24행(낙찰 5,275건 중 원본 공란 — 협상 22·최저가격제 2) → 화면 「해당 없음」/예외 「미기재」, 집계 분모 제외'),
('clean_dapa_bid_result', 20, 'base_amount_krw', '기초금액', 'BIGINT', '기초금액(원). NULL = 원본 결측 184행(raw 공란 — 유찰 44·개찰완료 139·순위확정 1, 협상 방식 173/330 편중) → 화면 「미기재」, 집계 분모 제외'),
('clean_dapa_bid_result', 25, 'final_award_amount_krw', '최종낙찰금액', 'BIGINT', '최종 낙찰금액(원). 계약금액과 다름. NULL = 구조적 2,128행(is_awarded=0 — 유찰 1,746·순위확정 382, 예외 0) → 화면 「해당 없음(미낙찰)」, 집계 낙찰액 합은 is_awarded=1만 + 유찰·순위확정 건수 병기'),
('clean_dapa_bid_result', 26, 'final_award_rate', '최종낙찰율', 'DECIMAL(7,3)', '최종 낙찰률(%). NULL = 구조적 2,128행(is_awarded=0) + 예외 24행(낙찰인데 원본 공란, reserve_price_krw 예외와 같은 행) → 화면 「해당 없음」/예외 「미기재」, 집계 분모 제외'),
('clean_dapa_bid_result', 27, 'final_award_date', '최종낙찰일자', 'DATE', '최종 낙찰일. NULL = 구조적 2,128행(is_awarded=0, 예외 0) → 화면 「해당 없음」, 집계 무시'),
('clean_dapa_bid_result', 28, 'winner_name', '최종낙찰업체명', 'VARCHAR(200)', '낙찰업체명(원문). NULL = 구조적 2,128행(is_awarded=0, 예외 0) → 화면 「해당 없음」, 집계 낙찰업체 수 분모 = is_awarded=1(5,275)'),
('clean_dapa_bid_result', 29, 'winner_biz_reg_no', '최종낙찰업체사업자등록번호', 'CHAR(12)', '낙찰업체 사업자등록번호(clean_company 키). NULL = 구조적 2,128행(is_awarded=0, 예외 0. 낙찰 5,275행은 전부 clean_company 연결) → 화면 「해당 없음」, 집계 연결률 분모 = 5,275'),
('clean_dapa_bid_result', 30, 'winner_address', '최종낙찰업체주소', 'VARCHAR(300)', '낙찰업체 소재지(생산·납품 위치 아님). NULL = 구조적 2,128행(is_awarded=0, 예외 0) → 화면 표시 안 함(규칙 #7, 시도만 표시), 집계 무시'),
('clean_dapa_bid_result', 31, 'winner_sido_code', '(파생)', 'CHAR(2)', '소재지 시도코드(ref_sido_map). NULL = 구조적 2,128행(winner_address NULL과 1:1, 미매핑 0) → 화면 「해당 없음」, 집계 시도 집계 분모 = 5,275')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_dapa_contract (9행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_contract', 14, 'total_contract_amount', '총계약금액', 'BIGINT', '전체 계약액(원). 계약 단위 금액 = 최종 차수의 이 값. NULL = 원본 결측 1행(raw 공란, is_latest_seq=1 행이라 계약 1건 금액 결측) → 화면 「미기재」, 집계 분모 제외 + 미기재 건수 병기(v_contract_monthly.amount_missing_count)'),
('clean_dapa_contract', 15, 'reserve_price', '예정가격', 'BIGINT', '예정가격(원). NULL = 원본 결측 36행(raw 공란) → 화면 「미기재」, 집계 무시(규칙 §2-2 ▲/✕)'),
('clean_dapa_contract', 21, 'sido_code', '(파생)', 'CHAR(2)', '주소 첫 토큰 → ref_sido_map 적용 결과. NULL = 의도된 NULL 2행(결정: 미매핑 토큰 **·1은 추정 금지, 규칙 §2-2. 충남대전시 16행은 09-19 30으로 백필) → 화면 「미기재(시도 미확인)」, 집계 시도별 집계 시 미확인 건수 병기'),
('clean_dapa_contract', 25, 'conflict_raw_row_ids', '(파생)', 'VARCHAR(100)', 'seq_conflict_flag=1일 때 적재하지 않은 나머지 원본 row_id(쉼표 구분). NULL = 구조적 43,104행(seq_conflict_flag=0, 충돌 1행과 1:1) → 화면 표시 안 함, 집계 무시'),
('clean_dapa_contract', 30, 'matched_keywords', '(파생)', 'VARCHAR(200)', '후보 선정 키워드(후보일 뿐, 합산 금지). NULL = 의도된 NULL(후속 예정: class5 키워드 규칙 확정 후 UPDATE, 현재 전 행 43,105) → 화면 「판단 보류」, 집계 무시'),
('clean_dapa_contract', 31, 'evidence', '(파생)', 'TEXT', '분류 근거(검수 메모·출처·충돌 행에서 달랐던 열). NULL = 구조적 43,104행(충돌 1행만 값, class5 근거는 규칙 확정 후) → 화면 표시 안 함, 집계 무시'),
('clean_dapa_contract', 33, 'contract_group', '(파생)', 'VARCHAR(50)', '계약 후보 품목군명(정제에서 부여). NULL = 의도된 NULL(후속 예정: class5 키워드 규칙 확정 후 UPDATE, 현재 전 행 43,105) → 화면 「판단 보류」, 집계 무시'),
('clean_dapa_contract', 34, 'category', '(파생)', 'VARCHAR(20)', '대응된 HS category. NULL = 의도된 NULL 43,105행(결정: ref_category_map 확정하지 않음 2026-09-18, category_link_status 전부 미연결) → 화면 「판단 보류(대응표 없음)」, 집계 무시'),
('clean_dapa_contract', 41, 'private_contract_reason', '수의계약사유', 'VARCHAR(500)', '수의계약 사유 원문. v_contract_private_reason 원천, 같은 계약번호 안에서 전 차수 동일. NULL = 구조적 12,856행(비수의계약) + 예외 9행(수의계약 30,249행 중 원본 공란) → 화면 「해당 없음(경쟁계약)」/예외 「미기재」, 집계 뷰 reason_group을 해당 없음(경쟁계약)·사유 미기재로 분리 병기')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_dapa_domestic_plan (2행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_domestic_plan', 11, 'budget_krw', '예산금액', 'BIGINT', '예산금액(원, 집행 예정액). 지수 표기 11행은 정수로 변환. NULL = 원본 결측 4,965행(raw 공란, 0 아님. 2024 778/4,545·2025 4,187/31,314) → 화면 「미기재」, 집계 분모 제외 + 미기재 건수 병기(v_domestic_plan_yearly.budget_missing_count). 편중 확인(09-20 stats-advisor, null-profile §6): MAR, 상태별 V=0.99(집행계획 단계 99.5% NULL, 그 외 0.3%)'),
('clean_dapa_domestic_plan', 13, 'progress_status', '진행상태', 'VARCHAR(30)', '진행상태. NULL = 원본 결측 190행(raw 공란 — 2024 14·2025 176) → 화면 「미기재」, 집계 is_contracted 판정 불가 → 미확인 별도 건수 병기')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_dapa_localized_item (8행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_localized_item', 3, 'nsn', '재고번호', 'VARCHAR(20)', 'NSN 13자리. KDSIS 연결 키. NULL = 원본 결측 10행(raw 공란) → 화면 「미기재」, 집계 KDSIS 연결 대상에서 제외(대상아님)'),
('clean_dapa_localized_item', 4, 'fsc4', '군급분류', 'CHAR(4)', 'FSC 4자리 — ref_fsc·국외 API LEFT(invntryNo,4) 조인 키. NULL = 원본 결측 16행(raw 0 15·공란 1, 규칙 §2-3) → 화면 「미기재」, 집계 FSG 집계 시 미대응 그룹 별도(v_b2_fsg_summary NULL 그룹)'),
('clean_dapa_localized_item', 5, 'fsc2', '(파생)', 'CHAR(2)', 'LEFT(fsc4,2) — 58·59가 전자 계열. NULL = 구조적 16행(fsc4 NULL 파생, 1:1) → 화면 「미기재」, 집계 fsc4와 같음'),
('clean_dapa_localized_item', 6, 'item_name', '품명', 'VARCHAR(200)', '품명(raw 그대로. 부품명이며 HS 매핑에 쓰지 않음). NULL = 원본 결측 30행(raw 공란) → 화면 「미기재」, 집계 무시'),
('clean_dapa_localized_item', 7, 'contractor_name', '계약업체', 'VARCHAR(200)', '계약 상대(개발 주체 아님). 국산 제조의 증거로 쓰지 않음. NULL = 원본 결측 34행(raw 공란, 중복 축약 후) → 화면 「미기재」, 집계 업체 연결 분모 제외'),
('clean_dapa_localized_item', 8, 'contractor_name_norm', '(파생)', 'VARCHAR(200)', '업체명 정규화(법인 표기 제거·공백 제거). clean_company_name_link 연결률 보고용. NULL = 구조적 34행(contractor_name NULL 파생, 1:1) → 화면 「미기재」, 집계 contractor_name과 같음'),
('clean_dapa_localized_item', 9, 'last_modified_date', '최종수정일', 'DATE', '포털 스냅샷 수정일. 연도 축으로 쓰지 않음. NULL = 원본 결측 18,160행(raw 공란, 72.6%) → 화면 표시 안 함, 집계 무시. 편중 확인(09-20 stats-advisor, null-profile §6): MAR, 사업별 V=0.33, 값은 2021-06~07 일괄갱신 창, MNAR 배제 불가'),
('clean_dapa_localized_item', 12, 'category', '(파생)', 'VARCHAR(20)', 'ref_category_map(map_type=fsc4) 결과. NULL = 의도된 NULL 24,625행(결정: 대응표 확정하지 않음 2026-09-18, 후보 400행만 값·확정 0) → 화면 「판단 보류(대응표 없음)」, 집계 v_review_list B2는 확정만 → NULL + b2_status')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_dapa_overseas_contract (2행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_overseas_contract', 9, 'period_end', '계약기간', 'DATE', '계약기간 종료. NULL = 구조적 725행(raw YYYY-MM-DD~ 종료일 미기재 → is_open_ended=1, 1:1, 규칙 §2-8) → 화면 「해당 없음(종료일 없음)」, 집계 기간 계산 분모 제외'),
('clean_dapa_overseas_contract', 12, 'vendor_name', '대표업체명', 'VARCHAR(200)', '외국 업체명. 국가 추정 금지. NULL = 원본 결측 60행(raw 공란) → 화면 「미기재」, 집계 업체 수 분모 제외 + 미기재 건수 병기')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_dapa_overseas_plan (2행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_overseas_plan', 4, 'rep_item_name', '대표품명', 'VARCHAR(500)', '전자 관련 후보 키워드 분류 대상. NULL = 원본 결측 1행(raw 공란) → 화면 「미기재」, 집계 전자 후보 판정 불가 → 미확인(후보 아님으로 세지 않음)'),
('clean_dapa_overseas_plan', 13, 'system_family_hint', '(파생)', 'VARCHAR(30)', '레이더/통신/항법/전자광학/음탐 등 키워드 계열 라벨(품목군 대응 아님, 집계 축 아님). NULL = 구조적 2,631행(is_electronics_candidate=0, 예외 0) → 화면 표시 안 함, 집계 무시')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_dapa_overseas_plan_api (12행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_overseas_plan_api', 2, 'item_seq', 'iemNo', 'VARCHAR(10)', 'PK 2. 품목순번. '''' = 원본 결측 842행(PK라 NULL 불가, is_item_seq_missing=1) → 화면 「미기재」, 집계 건수 포함(행 고유)'),
('clean_dapa_overseas_plan_api', 9, 'function_name', 'fnctSe', 'VARCHAR(30)', '기능구분. NULL = 원본 결측 1,657행(raw 공란) → 화면 「미기재」, 집계 기능구분 집계 시 미기재 별도 건수 병기'),
('clean_dapa_overseas_plan_api', 10, 'function_code', 'fnctSeCode', 'VARCHAR(4)', '기능구분 코드. NULL = 원본 결측 1,657행(function_name과 같은 행) → 화면 「미기재」, 집계 function_name과 같음'),
('clean_dapa_overseas_plan_api', 11, 'item_kind_name', 'prdlstKndSe', 'VARCHAR(20)', '품목종류구분. NULL = 원본 결측 1,657행(raw 공란, function_name과 같은 행) → 화면 「미기재」, 집계 품목종류 집계 시 미기재 별도 건수 병기'),
('clean_dapa_overseas_plan_api', 12, 'item_kind_code', 'prdlstKndSeCode', 'VARCHAR(4)', '품목종류구분 코드. NULL = 원본 결측 1,657행(item_kind_name과 같은 행) → 화면 「미기재」, 집계 item_kind_name과 같음'),
('clean_dapa_overseas_plan_api', 15, 'nsn', '(파생)', 'VARCHAR(13)', '13자 재고번호일 때만. 하이픈 없음 — clean_kdsis_nsn.nsn 형식. NULL = 구조적 379행(nsn_format 자리표시 347·기타 32, 규칙 §2-6, 예외 0) → 화면 「해당 없음(NSN 없음)」, 집계 FSC 모집단 13,236에서 제외 + 대상아님 379 병기'),
('clean_dapa_overseas_plan_api', 18, 'fsc4', '(파생)', 'CHAR(4)', '군급 4자리(ref_fsc). HS6 대응은 만들지 않음. NULL = 구조적 379행(nsn NULL 파생, 1:1) → 화면 「해당 없음」, 집계 nsn과 같음'),
('clean_dapa_overseas_plan_api', 19, 'fsg2', '(파생)', 'CHAR(2)', '군급 2자리(ref_fsg). NULL = 구조적 379행(nsn NULL 파생, 1:1) → 화면 「해당 없음」, 집계 nsn과 같음'),
('clean_dapa_overseas_plan_api', 22, 'equipment_code', 'eqpmnCode', 'VARCHAR(20)', '적용장비코드(코드로 장비를 묶지 않음). NULL = 원본 결측 1,834행(raw 공란) → 화면 표시 안 함, 집계 무시'),
('clean_dapa_overseas_plan_api', 23, 'equipment_name', 'eqpmnNm', 'VARCHAR(100)', '적용장비명 원문. NULL = 원본 결측 2,018행(raw 공란 1,159 + 자리표시 * 859 → is_equipment_missing=1, 규칙 §2-6) → 화면 「미기재」, 집계 장비명 수 분모 제외 + 미기재 건수 병기'),
('clean_dapa_overseas_plan_api', 24, 'equipment_name_norm', '(파생)', 'VARCHAR(100)', '기계적 정규화 결과. NULL = 구조적 2,018행(equipment_name NULL 파생, 1:1) → 화면 「미기재」, 집계 equipment_name과 같음'),
('clean_dapa_overseas_plan_api', 25, 'equipment_name_std', '(파생)', 'VARCHAR(100)', '표준명(잠정). NULL = 의도된 NULL 13,176행(결정: 표준명 근거 없음 — ref_equipment_alias는 표기 변이 관측 40종만 후보, 값 439행·원문 39종, 규칙 §2-6) → 화면 「원문 표시(표준명 없음)」, 집계 원문 기준')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_kdsis_nsn (9행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_kdsis_nsn', 3, 'review_note', '(파생)', 'VARCHAR(50)', '검토 사유(nsn_format=검토일 때). NULL = 구조적 135,331행(nsn_format=숫자13, 예외 0) → 화면 표시 안 함, 집계 무시'),
('clean_kdsis_nsn', 7, 'ncb_code', 'ncbCd_4130', 'VARCHAR(4)', 'NCB. NULL = 원본 결측 3행(raw 공란, NIIN 없는 4자 NSN) → 화면 「미기재」, 집계 무시(조회 전용)'),
('clean_kdsis_nsn', 8, 'niin', '(파생)', 'VARCHAR(10)', 'NCB 2자 + 일련번호 7자 = NSN 뒤 9자리. NULL = 원본 결측 3행(ncb_code·iin_serial 모두 공란, 2026-09-20 빈 문자열→NULL) → 화면 「미기재」, 집계 무시'),
('clean_kdsis_nsn', 9, 'niin_status', 'niinStatCd_2670', 'VARCHAR(2)', 'NIIN 상태. NULL = 원본 결측 2,189행(raw 공란, 코드 정의 미확인) → 화면 「미기재」, 집계 무시'),
('clean_kdsis_nsn', 12, 'item_name_en', 'shrtNm2301', 'VARCHAR(150)', '품명(영문). NULL = 원본 결측 5,260행(raw 공란) → 화면 「미기재」, 집계 무시'),
('clean_kdsis_nsn', 13, 'item_name_ko', 'shrtNmK122', 'VARCHAR(50)', '품명(한글). NULL = 원본 결측 5,260행(raw 공란) → 화면 「미기재」, 집계 무시'),
('clean_kdsis_nsn', 14, 'mfr_item_name_en', 'entprzEnglshItmnm', 'VARCHAR(120)', '업체 품명(영문). NULL = 원본 결측 19,066행(raw 공란) → 화면 「미기재」, 집계 무시'),
('clean_kdsis_nsn', 15, 'mfr_item_name_ko', 'entprzHanglItmnm', 'VARCHAR(80)', '업체 품명(한글). NULL = 원본 결측 6,217행(raw 공란) → 화면 「미기재」, 집계 무시'),
('clean_kdsis_nsn', 16, 'assigned_date', 'assndDt_2180', 'DATE', 'YYYY-MM-DD 형식일 때만. NULL = 원본 결측 17행(raw 공란, 형식 위반 0. 규칙 §2-14 연도 축 없음) → 화면 표시 안 함, 집계 무시')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_krit_task (6행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_krit_task', 6, 'program_type', '(본문 절 제목)', 'VARCHAR(30)', '핵심부품 / 수출연계 E/L / 전략부품 / 상생협력. NULL = 원본 결측 2행(표 제목·순 구분값 둘 다 없음, 26-1차 본공고) → 화면 「미기재」, 집계 구분별 집계 시 미기재 건수 병기'),
('clean_krit_task', 8, 'gov_fund_100m_krw', '정부지원\\n연구개발비', 'DECIMAL(10,2)', '정부지원 연구개발비(억원). 원문 23.67억 → 숫자 변환. NULL = 원본 결측 11행(24-1차 예비 공고는 정부지원금 열 자체 없음, gov_fund_unit_text=없음, 규칙 §2-4) → 화면 「미기재」, 집계 지원금 합 분모 제외 + 미기재 건수 병기'),
('clean_krit_task', 10, 'category', '(파생)', 'VARCHAR(20)', 'ref_category_map(map_type=krit_task) 결과. NULL = 의도된 NULL 96행(결정: 대응표 확정하지 않음 2026-09-18, 규칙 §7) → 화면 「판단 보류(대응표 없음)」, 집계 무시'),
('clean_krit_task', 11, 'hs6', '(파생)', 'CHAR(6)', '품목군 대응 HS6(근거 있을 때만). 텍스트 매칭으로 채우지 않음. NULL = 의도된 NULL 96행(결정: 대응 근거 없음, 규칙 §2-4. category_link_status 전부 미연결) → 화면 「판단 보류(대응표 없음)」, 집계 v_review_list B1 NULL + b1_status'),
('clean_krit_task', 18, 'gov_fund_text', '정부지원\\n연구개발비', 'VARCHAR(30)', '정부지원 연구개발비 원문(14.64억 / 10.35억원 / 1,657). NULL = 원본 결측 11행(gov_fund_100m_krw와 같은 행) → 화면 「미기재」, 집계 gov_fund_100m_krw와 같음'),
('clean_krit_task', 21, 'note', '비고', 'VARCHAR(300)', '비고 원문. NULL = 원본 결측 79행(raw 공란 66 + 자리표시 - · 13) → 화면 표시 안 함, 집계 무시')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_openfiscal_program_budget (8행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_openfiscal_program_budget', 3, 'program_name', '프로그램명', 'VARCHAR(100)', '프로그램명(2018년 개칭 — 기준축 아님)'),
('clean_openfiscal_program_budget', 9, 'expense_type', '경비구분', 'VARCHAR(50)', '경비구분 원문(3종)'),
('clean_openfiscal_program_budget', 10, 'outlay_type', '지출구분', 'VARCHAR(50)', '지출구분 원문(2종)'),
('clean_openfiscal_program_budget', 12, 'gov_plan_100m_krw', '(파생)', 'DECIMAL(18,5)', '정부안금액(억원) = 천원 / 100000'),
('clean_openfiscal_program_budget', 16, 'is_unconfirmed', '(파생)', 'TINYINT(1)', '1 = 국회확정 전(2027 268행). 0원이 아님'),
('clean_openfiscal_program_budget', 17, 'is_unit_tech_dev', '(파생)', 'TINYINT(1)', '1 = 단위사업 국방기술개발(93행)'),
('clean_openfiscal_program_budget', 18, 'budget_group_candidate', '(파생)', 'VARCHAR(20)', '⑤ 탭 예산 3선 키워드 후보(확정 아님, 합산 금지). NULL = 의도된 NULL 2,767행(결정: 규칙 §2-12 키워드 후보 93행 외 — 국방기술개발 85·부품국산화 7·국방반도체 1) → 화면 「해당 없음(3선 외)」, 집계 후보만 집계, 세 값 합산 금지'),
('clean_openfiscal_program_budget', 19, 'budget_group_basis', '(파생)', 'VARCHAR(200)', '후보값 판정 근거. NULL = 구조적 2,767행(budget_group_candidate NULL과 1:1, 예외 0) → 화면 표시 안 함, 집계 무시')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- clean_openfiscal_program_link (3행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_openfiscal_program_link', 2, 'program_name', '프로그램명', 'VARCHAR(100)', '프로그램명(참고)'),
('clean_openfiscal_program_link', 4, 'from_sub_program_name', '세부사업명', 'VARCHAR(200)', '바뀌기 전 세부사업명. NULL = 구조적 8행(link_type=신설, 예외 0) → 화면 「해당 없음(신설)」, 집계 무시'),
('clean_openfiscal_program_link', 5, 'from_last_year', '(파생)', 'SMALLINT', '바뀌기 전 이름의 마지막 회계연도. NULL = 구조적 8행(link_type=신설, from_sub_program_name과 같은 행) → 화면 「해당 없음(신설)」, 집계 무시')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- dim_hs10 (3행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('dim_hs10', 4, 'master_name_ko', '한글품목명', 'VARCHAR(500)', '관세청 HS부호 마스터(15049722, 2026 현행) 품목명. NULL = 원본 결측 104행(현행 마스터에 없는 이력 코드 — 851762 35·852990 18·848620 16…, master_link_status=마스터없음 1:1, 추정 금지) → 화면 「현행 마스터 없음」(품명은 name_ko 표시), 집계 무시(라벨 열). 편중 확인(09-20 stats-advisor, null-profile §6): MAR, hs6 V=0.56(HS 2022 개정 전 폐지 코드, 2016~21 수입액 14~24%)'),
('dim_hs10', 5, 'apply_start', '적용시작일자', 'DATE', '마스터 적용시작일. NULL = 원본 결측 104행(master_name_ko와 같은 행) → 화면 표시 안 함, 집계 무시'),
('dim_hs10', 6, 'apply_end', '적용종료일자', 'DATE', '마스터 적용종료일(현행 코드는 전부 2026-12-31). NULL = 원본 결측 104행(master_name_ko와 같은 행) → 화면 표시 안 함, 집계 무시')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- ref_hs_whitelist (1행)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('ref_hs_whitelist', 11, 'related_fsc', 'related_fsc', 'VARCHAR(30)', CONCAT('B2 대응 FSC4 후보(', CHAR(59 USING utf8mb4), ' 구분). 확정하지 않음(2026-09-18) — R4 입력용 후보'))
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- -----------------------------------------------------------------------------
-- §4 검증 (주석 — DBHub app_ro 로 실행. 기대값은 2026-09-20 적용 전 실측으로 계산한 값)
-- -----------------------------------------------------------------------------
-- SELECT SUM(niin=''), SUM(niin IS NULL), COUNT(*) FROM clean_kdsis_nsn;                                                  -- 0 · 3 · 135,864
-- SELECT COUNT(*), SUM(notice_count), SUM(budget_missing_count), SUM(budget_amount_krw) FROM v_bid_notice_monthly;         -- 538 · 10,840 · 596 · 10,672,865,445,613
-- SELECT SUM(budget_amount_krw IS NULL) FROM v_bid_notice_monthly;                                                        -- 46 (종전 0 — 전 행 NULL 그룹이 0 이었음)
-- SELECT COUNT(*), SUM(contract_count), SUM(amount_missing_count) FROM v_contract_monthly;                                -- 28 · 37,602 · 1
-- SELECT COUNT(*), SUM(plan_count), SUM(budget_missing_count) FROM v_domestic_plan_yearly;                                -- 62 · 35,859 · 4,965
-- SELECT reason_group, SUM(contract_count) FROM v_contract_private_reason GROUP BY 1;
--   -- 해당 없음(경쟁계약) 10,734 · 사유 미기재 9 · 나머지 8그룹 불변(소액·소기업 21,714 · 경쟁실패 후 수의 1,845 · 기관 간·위탁 1,288 · 우수·혁신·인증제품 1,094 ·
--   --   단일공급·호환성·특허 747 · 사회적 배려 105 · 방위사업법 특례 35 · 기타 31). 합 37,602
-- SELECT COUNT(*), SUM(contract_count), SUM(amount_missing_count) FROM v_contract_private_reason;                         -- 144 · 37,602 · 1
-- SELECT COUNT(*) FROM v_contract_reason_group_yearly;                                                                    -- 20 (18 + 해당 없음(경쟁계약) 2024·2025 분리)
-- SELECT COUNT(*) FROM meta_column_dict;                                                                                  -- 849
-- SELECT COUNT(*) FROM meta_column_dict WHERE description LIKE '%→ 화면%';                                                -- 77
-- SELECT description FROM meta_column_dict WHERE table_name='ref_hs_whitelist' AND column_name='related_fsc';            -- B2 대응 FSC4 후보(; 구분). 확정하지 않음(2026-09-18) — R4 입력용 후보
-- SELECT TABLE_NAME, COLLATION_CONNECTION FROM information_schema.VIEWS WHERE TABLE_SCHEMA='defense_dashboard'
--   AND TABLE_NAME IN ('v_contract_monthly','v_contract_private_reason','v_bid_notice_monthly','v_domestic_plan_yearly'); -- 전부 utf8mb4_unicode_ci
