-- =============================================================================
-- raw 직독 뷰 14개 → clean_ 기준 전환 + clean 열 2개 보강  (작성 2026-09-19)
--
-- 배경: raw→clean 전환이 끝났지만 아래 뷰들은 raw_ 테이블을 직접 읽고 있었다(docs/db/schema-change-log.md §7-20④·§7-24⑤·§7-26⑦ 보류 항목).
--       담당 표가 팀원 것이라 팀 결정 뒤로 미뤘던 것을 2026-09-19 사용자 지시("보류가 뭐야, 그냥 다 해")로 Claude 가 잠정 결정 + 문서 기록으로 실행한다.
--       계획: C:\Users\kimhh\.claude\plans\staged-spinning-peacock.md 작업 1.
-- 원칙:
--   · 뷰 이름·출력 열 이름은 유지한다(상위 뷰 v_hs6_candidate_rule·v_kdsis_link_summary·v_contract_reason_group_yearly 가 그대로 동작).
--     예외 2개: v_overseas_contract_yearly.demand_org_count 삭제(clean 이 단일값 열을 뺐으므로 항상 1) ·
--              v_kdsis_link_summary 에 raw 행 기준 열 3개 추가(기존 열 유지) + v_b2_localized_kdsis 끝에 dup_count 추가.
--   · raw 는 읽기만 한다. clean 에 없던 값 2개는 clean 열로 추가하고 raw_row_id 조인으로 백필한다(§1).
--   · 의미가 바뀌는 곳은 clean 정제 때 문서화된 결정을 따른다(각 뷰 주석 "의미 변경" 참조). 전환 전/후 지표 대조는 schema-change-log.md §6.
--   · 뷰는 열 사전(meta_column_dict)에 넣지 않는다. 새 clean 열 2개만 §2 에서 등록한다.
--   · GROUP_CONCAT 구분자 ';' 는 0x3B(hex 리터럴)로 쓴다 — scripts/apply_alter.py 가 세미콜론으로 문장을 나누므로 문자열 안에 ';' 를 둘 수 없다.
--     (MySQL 8.4 실측: SEPARATOR 0x3B 결과 콜레이션 utf8mb4_unicode_ci, 값 'a;b'.)
--   · v_defense_company_sector 는 clean 이 없어(raw_dapa_defense_company 정제 표 미설계, 84행 보조 자료) 전환하지 않는다 — raw 직독 유지.
-- 구조: §1 clean 열 2개 추가(조건부) + 백필 → §2 meta_column_dict 2행 → §3 뷰 CREATE OR REPLACE 15문(전환 14 + 요약 열 추가 1) → §4 검증 SQL(주석)
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-19_views_to_clean.sql   (RDS admin). DBHub(app_ro)는 불가.
-- 재실행 가능: information_schema 확인 후 PREPARE/EXECUTE(ADD COLUMN) · UPDATE 는 WHERE 로 미백필 행만 · ON DUPLICATE KEY UPDATE · CREATE OR REPLACE VIEW.
-- 정의 변경 시 db/schema.sql §5(clean 2표)·§6(뷰) 과 함께 고친다(두 파일의 뷰 본문은 동일해야 한다).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- §1 clean 열 2개 추가 + 백필 (물리 순서 = 열 사전 ordinal 순서라 AFTER 없이 뒤에 붙인다)
--   1-1 clean_dapa_contract.private_contract_reason — raw 수의계약사유 원문. v_contract_private_reason 이 raw 대신 이 열을 읽는다.
--       공란('')은 NULL 로 둔다(뷰가 '(사유 미기재)' 로 표시). 원본 TEXT 이지만 조문 문자열이라 VARCHAR(500) — 넘치면 STRICT 오류로 멈춘다(자름 없음).
--   1-2 clean_dapa_domestic_plan.is_budget_approx — raw budget_amount 가 지수 표기('1.71528E+12', 유효숫자 6자리)였던 행 = 1(11행 기대).
--       budget_krw 는 근사값이라 합계에 억 원 단위 오차가 있을 수 있다는 표시. v_domestic_plan_yearly.approx_amount_rows 의 원천.
-- -----------------------------------------------------------------------------
SET @has_col = (SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'clean_dapa_contract' AND COLUMN_NAME = 'private_contract_reason');
SET @q = IF(@has_col = 0,
  "ALTER TABLE clean_dapa_contract
     ADD COLUMN private_contract_reason VARCHAR(500) NULL COMMENT '수의계약사유 원문(raw private_contract_reason, 공란은 NULL). v_contract_private_reason 원천. 같은 계약번호 안에서 전 차수 동일(실측 충돌 0)'",
  "SELECT 'clean_dapa_contract.private_contract_reason already exists, ALTER skipped' AS info");
PREPARE s1 FROM @q; EXECUTE s1; DEALLOCATE PREPARE s1;

SET @has_col = (SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'clean_dapa_domestic_plan' AND COLUMN_NAME = 'is_budget_approx');
SET @q = IF(@has_col = 0,
  "ALTER TABLE clean_dapa_domestic_plan
     ADD COLUMN is_budget_approx TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'raw budget_amount 가 지수 표기(1.71528E+12, 유효숫자 6자리)라 budget_krw 가 근사값 = 1 (11행 기대). 합계에 억 원 단위 오차 가능'",
  "SELECT 'clean_dapa_domestic_plan.is_budget_approx already exists, ALTER skipped' AS info");
PREPARE s2 FROM @q; EXECUTE s2; DEALLOCATE PREPARE s2;

-- 백필(재실행 안전: 이미 채운 행은 WHERE 에서 빠진다)
UPDATE clean_dapa_contract c
  JOIN raw_dapa_contract r ON r.row_id = c.raw_row_id
   SET c.private_contract_reason = r.private_contract_reason
 WHERE c.private_contract_reason IS NULL
   AND r.private_contract_reason IS NOT NULL AND r.private_contract_reason <> '';

UPDATE clean_dapa_domestic_plan c
  JOIN raw_dapa_domestic_plan r ON r.row_id = c.raw_row_id
   SET c.is_budget_approx = 1
 WHERE c.is_budget_approx = 0
   AND r.budget_amount REGEXP '[eE]';

-- -----------------------------------------------------------------------------
-- §2 meta_column_dict (db/column_dict.csv 와 같은 내용. 2행)
-- -----------------------------------------------------------------------------
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_contract', 41, 'private_contract_reason', '수의계약사유', 'VARCHAR(500)', '수의계약 사유 원문(공란은 NULL). v_contract_private_reason 원천. 같은 계약번호 안에서 전 차수 동일'),
('clean_dapa_domestic_plan', 17, 'is_budget_approx', '(파생)', 'TINYINT(1)', 'raw 예산금액이 지수 표기(1.71528E+12)라 budget_krw 가 근사값이면 1 (11행). 합계에 억 원 단위 오차 가능')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- -----------------------------------------------------------------------------
-- §3 뷰 전환 (db/schema.sql §6 과 동일 본문. 순서는 의존 관계대로: 하위 → 상위)
-- -----------------------------------------------------------------------------

-- 3-1 v_defense_relevance_b2 — raw_dapa_localized_item → clean_dapa_localized_item(fsc4·dup_count).
--     b2_row_count = SUM(dup_count) 로 raw 행 의미 유지(1,001 기대), b2_part_count = part_mgmt_no DISTINCT(319 기대). 의미 변경 없음.
--     정량 지표 ② HS6별 B2 국산화개발품목 건수(ref_category_map fsc4 경유, 후보 포함). FSC→HS6 1:N 이라 HS6 간 합산 금지. v_hs6_candidate_rule R4 입력.
CREATE OR REPLACE VIEW v_defense_relevance_b2 AS
SELECT m.hs6,
       GROUP_CONCAT(DISTINCT m.source_key ORDER BY m.source_key SEPARATOR 0x3B) AS fsc4_list,
       MIN(m.link_status)                 AS link_status,
       COUNT(DISTINCT b.part_mgmt_no)     AS b2_part_count,
       COALESCE(SUM(b.dup_count), 0)      AS b2_row_count
FROM ref_category_map m
LEFT JOIN clean_dapa_localized_item b ON b.fsc4 = m.source_key
WHERE m.map_type = 'fsc4' AND m.hs6 IS NOT NULL
GROUP BY m.hs6;

-- 3-2 v_b2_fsg_summary — clean fsc2·dup_count. 행 수 = SUM(dup_count)(33,965 기대), 고유 부품 = part_mgmt_no DISTINCT(12,788 기대).
--     의미 변경: raw 의 fsc ''·'0' 두 그룹이 clean fsc2 NULL 한 그룹으로 합쳐져 58→57행. NULL 그룹의 fsc4_count 는 0(raw 는 ''·'0' 을 값으로 세어 1).
CREATE OR REPLACE VIEW v_b2_fsg_summary AS
SELECT b.fsc2                              AS fsg_code,
       f.name_ko                           AS fsg_name_ko,
       f.name_en                           AS fsg_name_en,
       COALESCE(f.is_electronic_group, 0)  AS is_electronic_group,
       SUM(b.dup_count)                    AS b2_row_count,
       COUNT(DISTINCT b.part_mgmt_no)      AS b2_part_count,
       COUNT(DISTINCT b.project_name)      AS b2_project_count,
       COUNT(DISTINCT b.fsc4)              AS fsc4_count
FROM clean_dapa_localized_item b
LEFT JOIN ref_fsg f ON f.fsg_code = b.fsc2
GROUP BY b.fsc2, f.name_ko, f.name_en, f.is_electronic_group;

-- 3-3 v_hsk_control_by_hs6 — raw_hsk_control(쉼표 목록) → clean_hsk_control(HSK10 × 통제번호 1개 세로형).
--     HS6 1,119 · DU 707 유지 기대. ml = regime '군용물자'(자료에 0), du_elec = is_du_elec(part_no 3·5·6·7).
--     의미 변경: control_no_list 가 raw 쉼표 목록 문자열들의 ';' 결합에서 통제번호 낱개(DISTINCT)의 ';' 결합으로 바뀐다. group_concat_max_len(기본 1024) 초과분은 잘린다(종전과 같은 제약).
CREATE OR REPLACE VIEW v_hsk_control_by_hs6 AS
SELECT c.hs6,
       COUNT(DISTINCT c.hsk10)                                                     AS control_hsk10_count,
       COUNT(DISTINCT CASE WHEN c.regime = '군용물자' THEN c.hsk10 END)            AS ml_hsk10_count,
       COUNT(DISTINCT CASE WHEN c.is_du_elec = 1 THEN c.hsk10 END)                AS du_elec_hsk10_count,
       GROUP_CONCAT(DISTINCT c.control_no ORDER BY c.control_no SEPARATOR 0x3B)   AS control_no_list
FROM clean_hsk_control c
GROUP BY c.hs6;

-- 3-4 v_overseas_plan_api_fsc — raw_dapa_overseas_plan_api → clean_dapa_overseas_plan_api.
--     의미 변경(§7-24⑤ 해소): ① 모집단을 숫자13 NSN(9,970)에서 clean nsn 전체(숫자13 9,970 + 영숫자13 3,266 = 13,236)로 넓힌다 — P3 정제가 NCB 37 영숫자 NSN 을 유효로 확정.
--     ② is_electronic_group = is_elec(fsg2 58·59·60, 종전 58·59) → 전자군 품목 1,819→2,267 기대. ③ army_name = army_std(군 표준값, 종전 원문 부대명).
--     ④ 적용장비 집계는 is_equipment_missing=0(공란·'*' 제외, 종전과 같은 규칙). 금액은 통화 미검증이라 뷰에 넣지 않는다(건수만). 파일판과 합산 금지.
CREATE OR REPLACE VIEW v_overseas_plan_api_fsc AS
SELECT a.fsc4,
       a.fsg2                                                       AS fsg_code,
       f.name_ko                                                    AS fsc_name_ko,
       g.name_ko                                                    AS fsg_name_ko,
       a.is_elec                                                    AS is_electronic_group,
       a.army_std                                                   AS army_name,
       a.demand_year,
       COUNT(*)                                                     AS plan_item_count,
       COUNT(DISTINCT CASE WHEN a.is_equipment_missing = 0 THEN a.equipment_name END)    AS equipment_name_count,
       SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT CASE WHEN a.is_equipment_missing = 0 THEN a.equipment_name END SEPARATOR ' | '), ' | ', 3) AS equipment_sample
FROM clean_dapa_overseas_plan_api a
LEFT JOIN ref_fsc f ON f.fsc4 = a.fsc4
LEFT JOIN ref_fsg g ON g.fsg_code = a.fsg2
WHERE a.nsn IS NOT NULL
GROUP BY a.fsc4, a.fsg2, f.name_ko, g.name_ko, a.is_elec, a.army_std, a.demand_year;

-- 3-5 v_budget_rnd_yearly — raw_openfiscal_program_budget(쉼표 문자열) → clean_openfiscal_program_budget(정수 천원 열).
--     §7-26⑦ "raw 그대로" 결정 번복. 규칙 동일(억원 = 천원 ÷ 100,000, 확정 합 0 → 정부안) → 연도별 합 차이 0 기대(total 1,995,815 · tech_dev 215,989).
CREATE OR REPLACE VIEW v_budget_rnd_yearly AS
SELECT fiscal_year,
       CASE WHEN SUM(confirmed_krw_k) = 0 THEN '정부안' ELSE '확정' END                                                    AS amount_basis,
       ROUND(SUM(gov_plan_krw_k) / 100000, 1)                                                                             AS total_gov_100m,
       ROUND(SUM(CASE WHEN unit_program_name = '국방기술개발'  THEN gov_plan_krw_k  ELSE 0 END) / 100000, 1)             AS tech_dev_gov_100m,
       ROUND(SUM(CASE WHEN unit_program_name = '국방기술개발'  THEN confirmed_krw_k ELSE 0 END) / 100000, 1)             AS tech_dev_confirmed_100m,
       ROUND(SUM(CASE WHEN sub_program_name LIKE '부품국산화%' THEN gov_plan_krw_k  ELSE 0 END) / 100000, 1)             AS localization_gov_100m,
       ROUND(SUM(CASE WHEN sub_program_name LIKE '국방반도체%' THEN gov_plan_krw_k  ELSE 0 END) / 100000, 1)             AS semiconductor_gov_100m,
       ROUND(SUM(CASE WHEN sub_program_name LIKE '기초연구%'   THEN gov_plan_krw_k  ELSE 0 END) / 100000, 1)             AS basic_research_gov_100m,
       ROUND(SUM(CASE WHEN sub_program_name LIKE '%공급망%'    THEN gov_plan_krw_k  ELSE 0 END) / 100000, 1)             AS supply_chain_gov_100m,
       COUNT(*)                                                                                                           AS row_count
FROM clean_openfiscal_program_budget
GROUP BY fiscal_year;

-- 3-6 v_overseas_plan_api_kdsis — clean_dapa_overseas_plan_api(raw 1:1) ↔ clean_kdsis_nsn. 13,615행 · 연결 616 유지 기대.
--     stock_no = 원문(stock_no_raw), is_nsn13 = nsn_format '숫자13'(9,970), 조인 키 = 정제된 nsn(13자, 하이픈 없음). kdsis_matched 는 조인 결과(clean kdsis_link_status='연결' 과 같아야 함).
CREATE OR REPLACE VIEW v_overseas_plan_api_kdsis AS
SELECT a.raw_row_id                               AS api_row_id,
       a.stock_no_raw                             AS stock_no,
       (a.nsn_format = '숫자13')                  AS is_nsn13,
       a.demand_year,
       a.army_name_raw                            AS army_name,
       a.item_name                                AS api_item_name,
       a.equipment_name,
       (k.nsn IS NOT NULL)                        AS kdsis_matched,
       k.nsn_format                               AS kdsis_nsn_format,
       k.fsc4                                     AS kdsis_fsc4,
       k.item_name_en                             AS kdsis_item_name_en,
       k.item_name_ko                             AS kdsis_item_name_ko,
       k.niin_status                              AS kdsis_niin_status,
       k.ref_count                                AS kdsis_ref_count,
       k.cage_count                               AS kdsis_cage_count
FROM clean_dapa_overseas_plan_api a
LEFT JOIN clean_kdsis_nsn k ON k.nsn = a.nsn;

-- 3-7 v_b2_localized_kdsis — clean_dapa_localized_item(사업×부품 고유 25,025) ↔ clean_kdsis_nsn.
--     의미 변경: 행 단위가 raw 행(33,965)에서 고유 사업×부품(25,025)으로. b2_row_id = first_raw_row_id(대표 원본 행). 끝에 dup_count 추가(raw 행 기준 값 복원용).
--     link_key 규칙 동일: fsc4 숫자 4 + nsn 숫자 9 = 13자, 아니면 NULL(임의 0 채움 금지).
CREATE OR REPLACE VIEW v_b2_localized_kdsis AS
SELECT b.first_raw_row_id                         AS b2_row_id,
       b.project_name, b.part_mgmt_no,
       b.fsc4                                     AS fsc,
       b.nsn                                      AS b2_stock_no,
       b.item_name                                AS b2_item_name,
       CASE WHEN b.fsc4 REGEXP '^[0-9]{4}$' AND b.nsn REGEXP '^[0-9]{9}$' THEN CONCAT(b.fsc4, b.nsn) END AS link_key,
       (k.nsn IS NOT NULL)                        AS kdsis_matched,
       k.fsc4                                     AS kdsis_fsc4,
       k.item_name_en                             AS kdsis_item_name_en,
       k.item_name_ko                             AS kdsis_item_name_ko,
       k.niin_status                              AS kdsis_niin_status,
       k.ref_count                                AS kdsis_ref_count,
       k.cage_count                               AS kdsis_cage_count,
       b.dup_count
FROM clean_dapa_localized_item b
LEFT JOIN clean_kdsis_nsn k
       ON b.fsc4 REGEXP '^[0-9]{4}$' AND b.nsn REGEXP '^[0-9]{9}$' AND k.nsn = CONCAT(b.fsc4, b.nsn);

-- 3-8 v_kdsis_link_summary — 기존 6열 유지 + raw 행 기준 3열(total_raw_rows·eligible_raw_rows·matched_raw_rows) 추가.
--     의미 변경: B2 행의 total/eligible/matched_rows 가 고유 사업×부품 기준(25,025 / … / 310 기대)이 되고, raw 행 기준(33,965 / 31,531 / 449)은 *_raw_rows 열로 읽는다. API 행은 raw 1:1 이라 두 값이 같다.
CREATE OR REPLACE VIEW v_kdsis_link_summary AS
SELECT '국외 조달계획 API(stock_no=nsn)' AS link_target,
       COUNT(*)                                        AS total_rows,
       SUM(is_nsn13)                                   AS eligible_rows,
       SUM(kdsis_matched)                              AS matched_rows,
       COUNT(DISTINCT CASE WHEN kdsis_matched THEN stock_no END) AS matched_nsn_count,
       SUM(kdsis_matched AND kdsis_nsn_format = '검토') AS matched_review_rows,
       COUNT(*)                                        AS total_raw_rows,
       SUM(is_nsn13)                                   AS eligible_raw_rows,
       SUM(kdsis_matched)                              AS matched_raw_rows
FROM v_overseas_plan_api_kdsis
UNION ALL
SELECT '국산화 B2(fsc4+재고번호9=nsn)',
       COUNT(*), SUM(link_key IS NOT NULL), SUM(kdsis_matched),
       COUNT(DISTINCT CASE WHEN kdsis_matched THEN link_key END), 0,
       SUM(dup_count), SUM(CASE WHEN link_key IS NOT NULL THEN dup_count ELSE 0 END), SUM(CASE WHEN kdsis_matched THEN dup_count ELSE 0 END)
FROM v_b2_localized_kdsis;

-- 3-9 v_contract_private_reason — raw_dapa_contract → clean_dapa_contract(§1-1 private_contract_reason).
--     계약번호당 1행(43,111 → 계약 37,608 기대). 연도 = 최초 계약체결 연도(MIN contract_date), 금액 = 최종 차수(is_latest_seq=1)의 total_contract_amount(합 158,338억 기대).
--     의미 변경: 충돌 키 2024UMM1504-01(같은 차수 raw 2행)은 raw 뷰가 "큰 값"을 취했고 clean 은 대표 행 1개(seq_conflict_flag=1)라 그 계약 1건 금액이 다를 수 있다.
--     reason_group 팀 그룹핑·조문 REGEXP 는 종전과 같다(schema.sql 3-9 주석 참조).
CREATE OR REPLACE VIEW v_contract_private_reason AS
SELECT c.contract_year, c.contract_method_name, c.biz_type_name, c.reason_group, c.reason_text,
       COUNT(*)                          AS contract_count,
       SUM(c.total_contract_amount_krw)  AS total_contract_amount_krw
FROM (
  SELECT r.contract_no,
         YEAR(MIN(r.contract_date))                                      AS contract_year,
         MAX(r.contract_method_name)                                     AS contract_method_name,
         MAX(r.biz_type)                                                 AS biz_type_name,
         COALESCE(NULLIF(MAX(r.private_contract_reason), ''), '(사유 미기재)') AS reason_text,
         CASE
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

-- 3-10 v_bid_result_summary — raw_dapa_bid_result → clean_dapa_bid_result(opening_date DATE·opening_result ENUM·bid_notice_seq_norm·final_award_rate/amount 숫자형).
--     열 밀림 2행은 clean 에 없다(7,403). 키 = 공고번호 + 정규화 차수(raw 뷰는 원문 차수) — 원문 차수 '0'/'00' 이 섞여 있었다면 키 수가 줄 수 있다(의미 변경 후보, 실측으로 확인).
--     낙찰률·낙찰금액은 clean 이 숫자형이라 REGEXP 판별이 필요 없다(rate_numeric_rows = final_award_rate IS NOT NULL).
CREATE OR REPLACE VIEW v_bid_result_summary AS
SELECT YEAR(opening_date)                                                AS opening_year,
       biz_type                                                          AS biz_type_name,
       opening_result                                                    AS opening_result_name,
       COUNT(DISTINCT CONCAT(bid_notice_no, '|', bid_notice_seq_norm))   AS key_count,
       COUNT(*)                                                          AS row_count,
       SUM(final_award_rate IS NOT NULL)                                 AS rate_numeric_rows,
       ROUND(AVG(final_award_rate), 2)                                   AS avg_award_rate_pct,
       ROUND(MIN(final_award_rate), 2)                                   AS min_award_rate_pct,
       ROUND(MAX(final_award_rate), 2)                                   AS max_award_rate_pct,
       COALESCE(SUM(final_award_amount_krw), 0)                          AS award_amount_krw
FROM clean_dapa_bid_result
GROUP BY YEAR(opening_date), biz_type, opening_result;

-- 3-11 v_bid_notice_monthly — raw_dapa_bid_notice → clean_dapa_bid_notice(bid_notice_date DATE·budget_amount_krw BIGINT). 열 밀림 2행 제외분 = clean 10,840 유지 기대.
CREATE OR REPLACE VIEW v_bid_notice_monthly AS
SELECT DATE_FORMAT(bid_notice_date, '%Y-%m')                             AS notice_month,
       bid_notice_status                                                 AS bid_notice_status_name,
       contract_method_name,
       biz_type                                                          AS biz_type_name,
       COUNT(*)                                                          AS notice_count,
       COALESCE(SUM(budget_amount_krw), 0)                               AS budget_amount_krw
FROM clean_dapa_bid_notice
GROUP BY DATE_FORMAT(bid_notice_date, '%Y-%m'), bid_notice_status, contract_method_name, biz_type;

-- 3-12 v_bid_notice_result_link — 연결 요약. 1행: clean_dapa_bid_result 키 대표 행의 notice_link_status(1:1/다중/미연결) 집계(키 7,199 기대, 종전 7,201 = 열 밀림 2행 제외).
--      result_rows 는 clean 행 수(7,403, 종전 raw 7,405), *_shifted_rows 는 clean_excluded_row COL_SHIFT 건수(2·2). 2행: 낙찰업체 사업자번호 ↔ clean_dapa_contract.vendor_biz_reg_no(3,210→3,209 기대).
CREATE OR REPLACE VIEW v_bid_notice_result_link AS
SELECT '입찰결과→입찰공고(공고번호+차수)' AS link_target,
       COUNT(*)                                        AS result_key_count,
       SUM(notice_link_status = '미연결')              AS unmatched_keys,
       SUM(notice_link_status = '1:1')                 AS one_match_keys,
       SUM(notice_link_status = '다중')                AS multi_match_keys,
       (SELECT COUNT(*) FROM clean_dapa_bid_result)    AS result_rows,
       (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name = 'raw_dapa_bid_result' AND reason_code = 'COL_SHIFT') AS result_shifted_rows,
       (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name = 'raw_dapa_bid_notice' AND reason_code = 'COL_SHIFT') AS notice_shifted_rows
FROM clean_dapa_bid_result
WHERE is_key_representative = 1
UNION ALL
SELECT '낙찰업체→계약정보(사업자번호)',
       COUNT(DISTINCT r.winner_biz_reg_no),
       COUNT(DISTINCT CASE WHEN c.vendor_biz_reg_no IS NULL THEN r.winner_biz_reg_no END),
       COUNT(DISTINCT CASE WHEN c.vendor_biz_reg_no IS NOT NULL THEN r.winner_biz_reg_no END),
       0, 0, 0, 0
FROM clean_dapa_bid_result r
LEFT JOIN (SELECT DISTINCT vendor_biz_reg_no FROM clean_dapa_contract) c ON c.vendor_biz_reg_no = r.winner_biz_reg_no
WHERE r.winner_biz_reg_no IS NOT NULL AND r.winner_biz_reg_no <> '';

-- 3-13 v_overseas_bid_chain — clean_dapa_overseas_bid_result(is_awarded·opening_at·budget_amount_usd) + clean_dapa_overseas_plan(PK decision_no).
--      단위 = 판단번호 × 항목번호(1,362 기대). 공고 횟수는 bid_notice_no(차수 포함) DISTINCT 그대로. 달러 예산은 A7 원화와 합산 금지.
--      의미 변경: 파일판 판단번호 중복 5쌍은 raw 뷰가 MAX 로 접었고 clean 은 대표 행 1개 → plan_year/exec_type/progress_status 가 최대 5건 다를 수 있다.
CREATE OR REPLACE VIEW v_overseas_bid_chain AS
SELECT b.decision_no,
       b.item_seq,
       MAX(b.bid_item_name)                                              AS bid_item_name,
       MAX(b.ordering_agency)                                            AS ordering_agency,
       COUNT(DISTINCT b.bid_notice_no)                                   AS notice_count,
       COUNT(*)                                                          AS result_rows,
       SUM(b.is_awarded)                                                 AS award_rows,
       CASE WHEN SUM(b.is_awarded) > 0 THEN '낙찰' ELSE '유찰' END        AS final_result,
       MIN(b.opening_at)                                                 AS first_opening,
       MAX(b.opening_at)                                                 AS last_opening,
       MAX(b.budget_amount_usd)                                          AS budget_usd,
       (p.decision_no IS NOT NULL)                                       AS plan_linked,
       p.plan_year,
       p.exec_type                                                       AS plan_exec_type,
       p.progress_status                                                 AS plan_progress_status
FROM clean_dapa_overseas_bid_result b
LEFT JOIN clean_dapa_overseas_plan p ON p.decision_no = b.decision_no
GROUP BY b.decision_no, b.item_seq, p.decision_no, p.plan_year, p.exec_type, p.progress_status;

-- 3-14 v_domestic_plan_yearly — clean_dapa_domestic_plan(plan_year·exec_type 표준값·budget_krw·is_contracted·§1-2 is_budget_approx). 35,859 · 지수 표기 11 유지 기대.
--      budget_krw NULL(원본 미기재 4,965행)은 SUM 에서 빠진다(raw 뷰는 ''→0 이라 합계 동일).
CREATE OR REPLACE VIEW v_domestic_plan_yearly AS
SELECT plan_year,
       exec_type,
       contract_method,
       COUNT(*)                                                           AS plan_count,
       SUM(budget_krw)                                                    AS budget_krw,
       SUM(is_contracted)                                                 AS contracted_count,
       SUM(is_budget_approx)                                              AS approx_amount_rows
FROM clean_dapa_domestic_plan
GROUP BY plan_year, exec_type, contract_method;

-- 3-15 v_overseas_contract_yearly — clean_dapa_overseas_contract(contract_year·contract_method_name·contract_no PK·vendor_name). 6,333 · 업체 1,697 유지 기대.
--      의미 변경: demand_org_count 열 삭제(clean 이 단일값 열 수요기관명='방위사업청' 을 제외 → 항상 1 이라 정보 없음). contract_no_count 는 PK 라 contract_count 와 같다(유지).
CREATE OR REPLACE VIEW v_overseas_contract_yearly AS
SELECT contract_year,
       contract_method_name,
       COUNT(*)                                                           AS contract_count,
       COUNT(DISTINCT contract_no)                                        AS contract_no_count,
       COUNT(DISTINCT vendor_name)                                        AS vendor_count
FROM clean_dapa_overseas_contract
GROUP BY contract_year, contract_method_name;

-- (전환하지 않음) v_defense_company_sector — raw_dapa_defense_company 의 clean 표가 없다(84행 보조 자료, 정제 표 미설계). raw 직독 유지.
-- (정의 변경 없음) v_contract_reason_group_yearly — v_contract_private_reason 파생. 3-9 전환 후 동작 확인만 한다.

-- -----------------------------------------------------------------------------
-- §4 검증 (DBHub app_ro 또는 같은 클라이언트). 기대값은 2026-09-19 전환 전 스냅샷(schema-change-log.md §6) 기준.
-- -----------------------------------------------------------------------------
-- [§1 열·백필]
-- SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='clean_dapa_contract';          -- 41
-- SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='clean_dapa_domestic_plan';     -- 17
-- SELECT COUNT(*) filled, SUM(private_contract_reason IS NULL) blank FROM clean_dapa_contract;                                 -- 43,111 / 공란 수 = raw '' 수
-- SELECT SUM(is_budget_approx) FROM clean_dapa_domestic_plan;                                                                  -- 11
-- SELECT COUNT(*) FROM meta_column_dict WHERE (table_name, column_name) IN (('clean_dapa_contract','private_contract_reason'),('clean_dapa_domestic_plan','is_budget_approx'));  -- 2
-- [§3 뷰 전/후 지표 — 전환 전 값]
-- SELECT COUNT(*), SUM(b2_row_count), SUM(b2_part_count) FROM v_defense_relevance_b2;                       -- 14 / 1,001 / 319 (동일)
-- SELECT COUNT(*), SUM(b2_row_count), SUM(b2_part_count) FROM v_b2_fsg_summary;                             -- 58→57 / 33,965 / 12,789 (행 수만 의미 변경)
-- SELECT COUNT(*), SUM(kdsis_matched), COUNT(DISTINCT CASE WHEN kdsis_matched THEN link_key END) FROM v_b2_localized_kdsis;   -- 33,965→25,025 / 449→310 / 171
-- SELECT link_target, total_rows, eligible_rows, matched_rows, matched_raw_rows FROM v_kdsis_link_summary;  -- API 13,615/9,970/616/616 · B2 25,025/…/310/449
-- SELECT SUM(plan_item_count), SUM(CASE WHEN is_electronic_group THEN plan_item_count END) FROM v_overseas_plan_api_fsc;       -- 9,970→13,236 / 1,819→2,267
-- SELECT COUNT(*), SUM(kdsis_matched), SUM(is_nsn13) FROM v_overseas_plan_api_kdsis;                        -- 13,615 / 616 / 9,970 (동일)
-- SELECT ROUND(SUM(total_gov_100m)), ROUND(SUM(tech_dev_gov_100m)) FROM v_budget_rnd_yearly;               -- 1,995,815 / 215,989 (동일)
-- SELECT COUNT(*), SUM(contract_count), ROUND(SUM(total_contract_amount_krw)/1e8) FROM v_contract_private_reason;   -- 144 / 37,608 / 158,338
-- SELECT COUNT(*), SUM(key_count), SUM(row_count) FROM v_bid_result_summary;                                -- 12 / 7,387 / 7,403
-- SELECT COUNT(*), SUM(notice_count), ROUND(SUM(budget_amount_krw)/1e8) FROM v_bid_notice_monthly;         -- 538 / 10,840 / 106,729
-- SELECT link_target, result_key_count, one_match_keys FROM v_bid_notice_result_link;                       -- 7,201→7,199 / 6,569 · 3,210→3,209 / 3,094
-- SELECT COUNT(*), SUM(plan_count), SUM(approx_amount_rows) FROM v_domestic_plan_yearly;                    -- 62 / 35,859 / 11
-- SELECT COUNT(*), SUM(final_result='낙찰'), SUM(plan_linked) FROM v_overseas_bid_chain;                    -- 1,362 / 342 / 1,331 (plan 대표행 차이 ≤5)
-- SELECT COUNT(*), SUM(contract_count), SUM(vendor_count) FROM v_overseas_contract_yearly;                  -- 39 / 6,333 / 1,697
-- SELECT COUNT(*), SUM(du_elec_hsk10_count), SUM(control_hsk10_count) FROM v_hsk_control_by_hs6;            -- 1,119 / 707 / 2,161
-- [상위 뷰 불변]
-- SELECT verdict, COUNT(*) FROM v_hs6_candidate_vs_whitelist GROUP BY verdict;                              -- 신규 후보 39 / 유지 19 / 강등 검토 5
-- SELECT SUM(r1_mil), SUM(r2_aero_nav), SUM(r3_control), SUM(r4_b2) FROM v_hs6_candidate_rule;             -- 전환 전과 동일
-- SELECT SUM(contract_count) FROM v_contract_reason_group_yearly;                                           -- 37,608
