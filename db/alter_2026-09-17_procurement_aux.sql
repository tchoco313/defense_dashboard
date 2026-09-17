-- =============================================================================
-- 국내 축 확장: 조달 보조 데이터 6종 + 계약정보 수의계약 사유 집계 뷰 9개 (작성 2026-09-17)
--
-- 배경: raw_dapa_domestic_plan(35,859)·raw_dapa_bid_notice(10,842)·raw_dapa_bid_result(7,405)·raw_dapa_overseas_contract(6,333)·
--       raw_dapa_overseas_bid_result(2,494)·raw_dapa_defense_company(84)는 적재만 되고 어느 뷰도 참조하지 않았다.
--       계약정보 raw_dapa_contract.private_contract_reason(수의계약 사유, 국계법 시행령 조문 단위 42종)도 미사용이었다.
--       이 뷰들은 핵심 ② "관련 조달·국산화 근거"의 조달 섹션(연도·계약방법·사유·업체 축)과 배경 ⓪ 카드에 쓴다.
-- 원칙: · 6종 모두 FSC·NSN이 없으므로 FSC·HS6 축으로 옮기지 않는다(품목군 대응 없음).
--       · raw 직접 집계 뷰만 만든다. clean_dapa_contract·clean_company(5분류·업체 마스터)는 사용자 노트북 정제 영역이라 손대지 않는다.
--       · 열 밀림 행은 뷰에서 제외하고 제외 건수를 연결 요약 뷰에 남긴다(raw는 그대로).
--       · 담당자명·대표자명·연락처·주소는 어느 뷰에도 넣지 않는다.
--       · 금액: 조달계획 예산 = 집행 예정액(진행상태 계약완료 외에는 "집행 예산"이라 쓰지 않음), 낙찰금액 ≠ 계약금액,
--         관세청 수입액·열린재정 편성액과 합산·비율 금지. 국내 vs 국외 조달계획 예산 비율은 2024~2025 한정.
--       · "수의계약 사유"는 조달 지연·공급자 락인의 **간접** 신호다. "국산화 필요 근거"라고 쓰지 않는다.
--         관리규정 §23(개발부품 수의계약)에 해당하는 사유 코드는 42종 어디에도 없다(국산화·개발 검색 6건 = 중기부 개발제품 협약).
-- 실행: docs/runbook/commands.md 증분 변경 방식(mariadb.exe, 계정 defense). DBHub는 readonly라 불가.
--       CREATE OR REPLACE VIEW 만 있어 재실행 가능. 데이터·테이블은 건드리지 않는다.
-- 검증(§10)은 파일 끝. 기대값은 2026-09-17 DBHub 실측.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;   -- 뷰 콜레이션 규칙(alter_2026-09-17_view_collation.sql)

-- §1 계약정보 수의계약 사유 구성 — 계약번호당 1행(43,112행 → 계약 37,608). 사유·계약방법은 같은 계약번호 안에서 전부 동일(실측 충돌 0).
--    금액 = 최종 차수(contract_seq 최대)의 총계약금액. 계약번호+차수 충돌 1건(2024UMM1504-01, 같은 차수 2행)은 큰 값을 취한다.
--    연도 = 계약번호의 최초 계약체결일(변경계약은 최초 연도에 최종 금액으로 잡힌다 — v_contract_monthly와 같은 규칙).
--    reason_group은 팀 그룹핑이며 조문 원문은 reason_text에 그대로 둔다:
--      경쟁실패 후 수의   = 국계법시행령 §27(재공고후·1인입찰후·공고후 수의) + §28(낙찰자 불이행) + 특례규정 §23①1(응찰자 없음)
--      단일공급·호환성·특허 = §26①2 자(단일업체)·사(호환성 없음)·아(특허·실용신안)·바(제조공급자 직접 설치·정비) + §26①1다(군용물자 연구개발업체)
--                          + 특례규정 §23①2(대체품 없음)·§23①4(부품교환·설비확충)
--      소액·소기업        = §26①5가(추정가격 2천만 원 이하, 1억 원 이하 소기업·여성기업·학술 등, 소액 공사·임대차)
--      기관 간·위탁       = §26①5 바(국가기관·지자체)·마(법령상 위탁·대행)·다(가공·하역·운송)
--      우수·혁신·인증제품 = §26①3(우수조달물품·혁신제품·성능인증·신기술·개발제품 협약 등)
--      사회적 배려        = §26①4(중증장애인생산품·국가유공자 단체·사회복지법인)
--      방위사업법 특례    = 방위사업법시행령 §61③(성과기반계약·국내업체 정비·시제품 양산)
--      사유 미기재        = 경쟁계약 전부(사유 열 없음) + 수의계약 9건
--      기타              = 그 외(긴급 §23①3, 분할 §29, 용역·공사 §26①2 차카·가-마 등)
CREATE OR REPLACE VIEW v_contract_private_reason AS
SELECT c.contract_year, c.contract_method_name, c.biz_type_name, c.reason_group, c.reason_text,
       COUNT(*)                          AS contract_count,
       SUM(c.total_contract_amount_krw)  AS total_contract_amount_krw
FROM (
  SELECT r.contract_no,
         LEFT(MIN(r.contract_date), 4)                                   AS contract_year,
         MAX(r.contract_method_name)                                     AS contract_method_name,
         MAX(r.biz_type_name)                                            AS biz_type_name,
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
         MAX(CASE WHEN CAST(r.contract_seq AS UNSIGNED) = k.max_seq
                  THEN CAST(r.total_contract_amount AS DECIMAL(20,0)) END) AS total_contract_amount_krw
  FROM raw_dapa_contract r
  JOIN (SELECT contract_no, MAX(CAST(contract_seq AS UNSIGNED)) AS max_seq FROM raw_dapa_contract GROUP BY contract_no) k
    ON k.contract_no = r.contract_no
  GROUP BY r.contract_no
) c
GROUP BY c.contract_year, c.contract_method_name, c.biz_type_name, c.reason_group, c.reason_text;

-- §2 국내 경쟁입찰 결과 요약 — 개찰연도 × 업무구분(물품/용역) × 개찰결과(개찰완료/유찰/순위확정).
--    단위 = (입찰공고번호, 차수) 고유 키(7,201). 같은 키가 여러 행이면(199키 403행: 복수 낙찰 108키·결과가 다른 73키) 결과별로 각각 1회 센다 → key_count 합은 7,201보다 약간 크다.
--    열 밀림 2행(LCF0223 1·2차: 개찰결과 열에 날짜)은 제외. 낙찰률·낙찰금액은 숫자형 행만(비숫자·공란 2,154행 = 유찰 포함) 평균한다.
--    2024는 11~12월(개찰 913행)이라 연간 실적이 아니다. 낙찰금액 ≠ 계약금액.
CREATE OR REPLACE VIEW v_bid_result_summary AS
SELECT LEFT(opening_date, 4)                                            AS opening_year,
       biz_type_name,
       opening_result_name,
       COUNT(DISTINCT CONCAT(bid_notice_no, '|', bid_notice_seq))         AS key_count,
       COUNT(*)                                                           AS row_count,
       SUM(final_award_rate REGEXP '^[0-9.]+$')                           AS rate_numeric_rows,
       ROUND(AVG(CASE WHEN final_award_rate REGEXP '^[0-9.]+$' THEN CAST(final_award_rate AS DECIMAL(8,3)) END), 2) AS avg_award_rate_pct,
       ROUND(MIN(CASE WHEN final_award_rate REGEXP '^[0-9.]+$' THEN CAST(final_award_rate AS DECIMAL(8,3)) END), 2) AS min_award_rate_pct,
       ROUND(MAX(CASE WHEN final_award_rate REGEXP '^[0-9.]+$' THEN CAST(final_award_rate AS DECIMAL(8,3)) END), 2) AS max_award_rate_pct,
       SUM(CASE WHEN final_award_amount REGEXP '^[0-9]+$' THEN CAST(final_award_amount AS DECIMAL(20,0)) ELSE 0 END) AS award_amount_krw
FROM raw_dapa_bid_result
WHERE opening_result_name IS NOT NULL AND opening_result_name NOT REGEXP '^[0-9]{4}-'
GROUP BY LEFT(opening_date, 4), biz_type_name, opening_result_name;

-- §3 국내 경쟁입찰 공고 월별 — 공고월 × 공고상태(긴급/정상/재공고/취소/정정/연기) × 계약방법 × 업무구분.
--    단위 = 행(참조공고번호+차수가 고유 10,842). 열 밀림 2행(공고일자 NULL, 계약방법 'Y')은 제외 → 10,840.
--    이 표는 "경쟁 입찰공고"만 담는다(수의계약은 공고 없음). 공고 예산은 공고 시점 예산이며 낙찰·계약액이 아니다.
CREATE OR REPLACE VIEW v_bid_notice_monthly AS
SELECT LEFT(bid_notice_date, 7)                                         AS notice_month,
       bid_notice_status_name,
       contract_method_name,
       biz_type_name,
       COUNT(*)                                                           AS notice_count,
       SUM(CASE WHEN budget_amount REGEXP '^[0-9]+$' THEN CAST(budget_amount AS DECIMAL(20,0)) ELSE 0 END) AS budget_amount_krw
FROM raw_dapa_bid_notice
WHERE bid_notice_date IS NOT NULL AND bid_notice_date <> ''
GROUP BY LEFT(bid_notice_date, 7), bid_notice_status_name, contract_method_name, biz_type_name;

-- §4 연결 요약(보고용) — 입찰공고 ↔ 입찰결과, 입찰결과 낙찰업체 ↔ 계약정보 업체.
--    공고의 실제 키는 참조공고번호+차수(연도 포함)인데 결과 표에는 그 열이 없어 입찰공고번호+차수(연도 미포함, 공고 쪽 비유일 10,486/10,842)로만 이을 수 있다.
--    → 결과 키 7,201 중 1:1 6,569 · 다중일치 303 · 미연결 329 (2026-09-17 실측). 화면에서 공고↔결과를 행 단위로 잇지 않고 각각 집계만 한다.
--    낙찰업체 사업자번호 3,210개 중 3,094개가 계약정보 vendor_biz_reg_no에 있다(96%). 업체 축 연결은 clean_company 정제 후 화면에 쓴다.
CREATE OR REPLACE VIEW v_bid_notice_result_link AS
SELECT '입찰결과→입찰공고(공고번호+차수)' AS link_target,
       COUNT(*)                                        AS result_key_count,
       SUM(x.m = 0)                                    AS unmatched_keys,
       SUM(x.m = 1)                                    AS one_match_keys,
       SUM(x.m > 1)                                    AS multi_match_keys,
       (SELECT COUNT(*) FROM raw_dapa_bid_result)      AS result_rows,
       (SELECT COUNT(*) FROM raw_dapa_bid_result WHERE opening_result_name REGEXP '^[0-9]{4}-') AS result_shifted_rows,
       (SELECT COUNT(*) FROM raw_dapa_bid_notice WHERE bid_notice_date IS NULL OR bid_notice_date = '') AS notice_shifted_rows
FROM (SELECT r.bid_notice_no, r.bid_notice_seq, COUNT(n.row_id) AS m
      FROM (SELECT DISTINCT bid_notice_no, bid_notice_seq FROM raw_dapa_bid_result) r
      LEFT JOIN raw_dapa_bid_notice n ON n.bid_notice_no = r.bid_notice_no AND n.bid_notice_seq = r.bid_notice_seq
      GROUP BY r.bid_notice_no, r.bid_notice_seq) x
UNION ALL
SELECT '낙찰업체→계약정보(사업자번호)',
       COUNT(DISTINCT r.winner_biz_reg_no),
       COUNT(DISTINCT CASE WHEN c.vendor_biz_reg_no IS NULL THEN r.winner_biz_reg_no END),
       COUNT(DISTINCT CASE WHEN c.vendor_biz_reg_no IS NOT NULL THEN r.winner_biz_reg_no END),
       0, 0, 0, 0
FROM raw_dapa_bid_result r
LEFT JOIN (SELECT DISTINCT vendor_biz_reg_no FROM raw_dapa_contract) c ON c.vendor_biz_reg_no = r.winner_biz_reg_no
WHERE r.winner_biz_reg_no IS NOT NULL AND r.winner_biz_reg_no <> '';

-- §5 국외 조달계획 → 국외 입찰결과 사슬(2025-01~09 부분연도) — 단위 = 판단번호 × 항목번호(1,362).
--    입찰결과 2,494행은 같은 항목이 공고 차수(EHG0001-1, -2 …)마다 반복된 것. 판단번호 97개 중 88개가 2회, 6개가 3회 공고 = 재공고.
--    final_result: 한 번이라도 낙찰이면 '낙찰', 아니면 '유찰'. 낙찰업체 열은 원본에 없다. 예산은 달러(입찰 표 자체 값)이며 A7 원화 예산과 합산하지 않는다.
--    A7 파일판(raw_dapa_overseas_plan)과 판단번호로 LEFT JOIN — 행 단위 연결률 낙찰 100%·유찰 97%(실측). 판단번호 중복 5쌍은 MAX로 1행 요약.
CREATE OR REPLACE VIEW v_overseas_bid_chain AS
SELECT b.decision_no,
       b.item_seq,
       MAX(b.bid_item_name)                                              AS bid_item_name,
       MAX(b.ordering_agency)                                            AS ordering_agency,
       COUNT(DISTINCT b.bid_notice_no)                                   AS notice_count,
       COUNT(*)                                                          AS result_rows,
       SUM(b.bid_result = '낙찰')                                        AS award_rows,
       CASE WHEN SUM(b.bid_result = '낙찰') > 0 THEN '낙찰' ELSE '유찰' END AS final_result,
       MIN(b.opening_datetime)                                           AS first_opening,
       MAX(b.opening_datetime)                                           AS last_opening,
       MAX(CASE WHEN b.budget_amount_usd REGEXP '^[0-9.]+$' THEN CAST(b.budget_amount_usd AS DECIMAL(20,2)) END) AS budget_usd,
       (p.decision_no IS NOT NULL)                                       AS plan_linked,
       p.plan_year,
       p.exec_type                                                       AS plan_exec_type,
       p.progress_status                                                 AS plan_progress_status
FROM raw_dapa_overseas_bid_result b
LEFT JOIN (SELECT decision_no,
                  MAX(LEFT(plan_month, 4)) AS plan_year,
                  MAX(TRIM(exec_type))     AS exec_type,
                  MAX(progress_status)     AS progress_status
           FROM raw_dapa_overseas_plan GROUP BY decision_no) p ON p.decision_no = b.decision_no
GROUP BY b.decision_no, b.item_seq, p.decision_no, p.plan_year, p.exec_type, p.progress_status;

-- §6 국내조달 조달계획 연도별 — 연도 × 집행유형 × 계약방법. v_overseas_plan_yearly(A7)와 같은 열 이름으로 두어 배경 ⓪ "국내 vs 국외 조달계획 예산(2024~2025)" 비교에 쓴다.
--    예산 = 집행 예정액(원). contracted_count = 진행상태 '계약완료'. 2024는 4,545행(31,314 대비 불완전) → 화면 라벨 "2024 불완전". 1만 건 요건에는 쓰지 않는다.
--    budget_amount 11행이 지수 표기('1.71528E+12', 6자리 유효숫자)라 CAST로 근사 — 합계에 억 원 단위 오차 가능.
--    exec_type 원본에 뒤 공백('리스 ', '제조/구매 ')이 있어 TRIM 한다.
CREATE OR REPLACE VIEW v_domestic_plan_yearly AS
SELECT LEFT(plan_month, 4)                                              AS plan_year,
       TRIM(exec_type)                                                    AS exec_type,
       contract_method,
       COUNT(*)                                                           AS plan_count,
       SUM(CAST(budget_amount AS DECIMAL(20,0)))                          AS budget_krw,
       SUM(progress_status = '계약완료')                                  AS contracted_count,
       SUM(budget_amount NOT REGEXP '^[0-9]+$')                           AS approx_amount_rows
FROM raw_dapa_domestic_plan
GROUP BY LEFT(plan_month, 4), TRIM(exec_type), contract_method;

-- §7 국외 계약정보 연도별 — 연도 × 계약방법 건수, 고유 업체 수·수요기관 수. 금액·국가 열이 원본에 없다(건수만). 업체명으로 국가를 추정하지 않는다.
CREATE OR REPLACE VIEW v_overseas_contract_yearly AS
SELECT LEFT(contract_date, 4)                                            AS contract_year,
       contract_method_name,
       COUNT(*)                                                           AS contract_count,
       COUNT(DISTINCT contract_no)                                        AS contract_no_count,
       COUNT(DISTINCT vendor_name)                                        AS vendor_count,
       COUNT(DISTINCT demand_org_name)                                    AS demand_org_count
FROM raw_dapa_overseas_contract
GROUP BY LEFT(contract_date, 4), contract_method_name;

-- §8 방산업체 지정현황 분야별 — 84행, 분야 공란 3은 '미기재'. 주소·사업자번호·품목 없음(업체명 정규화 연결은 clean_company_name_link 정제 후).
CREATE OR REPLACE VIEW v_defense_company_sector AS
SELECT COALESCE(NULLIF(sector, ''), '미기재')                             AS sector,
       COUNT(*)                                                           AS company_count,
       MIN(LEFT(designated_date, 4))                                      AS first_designated_year,
       MAX(LEFT(designated_date, 4))                                      AS last_designated_year
FROM raw_dapa_defense_company
GROUP BY COALESCE(NULLIF(sector, ''), '미기재');

-- §9 수의계약 사유 그룹 연도 요약(화면 카드용) — §1을 그룹 단위로 접은 것. 비중 분모 = 그 해 전체 계약(경쟁 포함).
CREATE OR REPLACE VIEW v_contract_reason_group_yearly AS
SELECT contract_year, reason_group,
       SUM(contract_count)                                                AS contract_count,
       SUM(total_contract_amount_krw)                                     AS total_contract_amount_krw,
       ROUND(100 * SUM(contract_count) / SUM(SUM(contract_count)) OVER (PARTITION BY contract_year), 2) AS share_pct
FROM v_contract_private_reason
GROUP BY contract_year, reason_group;

-- §10 검증 (DBHub, 2026-09-17 팀 서버 적용 후 실측값)
-- SELECT COUNT(*) FROM information_schema.views WHERE table_schema='defense_dashboard';                       -- 29 (전부 utf8mb4_unicode_ci)
-- SELECT SUM(contract_count) FROM v_contract_private_reason;                                                  -- 37,608 (계약번호 고유), 총계약금액 15.834조 원
-- SELECT reason_group, SUM(contract_count) FROM v_contract_private_reason WHERE contract_method_name='수의계약' GROUP BY 1;
--   -- 소액·소기업 21,718 · 경쟁실패 후 수의 1,847 · 기관 간·위탁 1,288 · 우수·혁신·인증제품 1,094 · 단일공급·호환성·특허 747
--   -- · 사회적 배려 105 · 방위사업법 특례 35(2.50조 원, 성과기반계약) · 기타 31 · 사유 미기재 9   (합 30,255 → 계약 단위 26,874)
--   -- (행 단위로는 경쟁실패 2,309행·단일공급 857행 — 차수 반복 때문에 계약 단위가 더 적다)
-- SELECT opening_result_name, SUM(key_count), SUM(row_count) FROM v_bid_result_summary GROUP BY 1;            -- 개찰완료 5,264/5,275 · 유찰 1,741/1,746 · 순위확정 382/382 (열 밀림 2 제외)
-- SELECT SUM(notice_count) FROM v_bid_notice_monthly;                                                         -- 10,840 (긴급 5,677 · 정상 2,433 · 재공고 1,409 · 취소 981 · 정정 324 · 연기 16)
-- SELECT * FROM v_bid_notice_result_link;                                                                     -- 7,201 / 329 / 6,569 / 303 ; 3,210 / 116 / 3,094
-- SELECT COUNT(*), COUNT(DISTINCT decision_no), SUM(final_result='낙찰'), SUM(plan_linked), SUM(notice_count>=2) FROM v_overseas_bid_chain;
--   -- 1,362 / 97 / 342 / 1,331 / 1,126   (유찰 1,020 중 (확정)부품 961)
-- SELECT plan_year, SUM(plan_count), ROUND(SUM(budget_krw)/1e12,3), SUM(contracted_count) FROM v_domestic_plan_yearly GROUP BY 1;
--   -- 2024 4,545 1.075조 3,431 / 2025 31,314 8.558조 24,013
-- SELECT SUM(contract_count) FROM v_overseas_contract_yearly;                                                 -- 6,333
-- SELECT SUM(company_count) FROM v_defense_company_sector;                                                    -- 84
