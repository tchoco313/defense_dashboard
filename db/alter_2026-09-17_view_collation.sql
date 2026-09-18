-- =============================================================================
-- 뷰 15개 콜레이션 재생성 (작성 2026-09-17, 검토 보고서 2026-09-16 F3)
--
-- 문제: 팀 서버(MySQL 8.4.11)에서 뷰를 만든 세션의 collation_connection 이 utf8mb4_0900_ai_ci 였고
--       (information_schema.VIEWS.COLLATION_CONNECTION 실측), 테이블·접속 콜레이션은 utf8mb4_unicode_ci 다.
--       뷰 안 CASE 문자열 열(b1_status·b2_status·civil_mix_rule·verdict·use_tag 등)을 리터럴과 비교하면
--       "ERROR 1267 Illegal mix of collations (utf8mb4_0900_ai_ci,COERCIBLE) and (utf8mb4_unicode_ci,COERCIBLE)" 가 난다.
--       예: SELECT COUNT(*) FROM v_review_list WHERE b1_status='미적재';   -- 오류
-- 조치: 세션 콜레이션을 utf8mb4_unicode_ci 로 맞춘 뒤 db/schema.sql §6 의 뷰 15개를 정의 변경 없이 CREATE OR REPLACE 한다.
--       (뷰 본문은 schema.sql 993~1299행과 동일하게 유지한다. 정의를 바꿀 때는 두 파일을 함께 고친다.)
-- 실행(docs/runbook/commands.md 증분 변경 방식, 계정은 .env MARIADB_USER):
--       mariadb.exe -h <서버IP> -u <계정> --protocol=TCP --skip-ssl-verify-server-cert --default-character-set=utf8mb4 --show-warnings --table defense_dashboard < db/alter_2026-09-17_view_collation.sql
-- 재실행: 가능(CREATE OR REPLACE VIEW 만 있음). 데이터·테이블은 건드리지 않는다.
-- 검증: SELECT TABLE_NAME, COLLATION_CONNECTION FROM information_schema.VIEWS WHERE TABLE_SCHEMA='defense_dashboard';  -- 15개 전부 utf8mb4_unicode_ci
--       SELECT COUNT(*) FROM v_review_list WHERE b1_status='미적재' AND year=2025;                                        -- 24
-- 앞으로: 팀 서버에서 뷰를 만들거나 고칠 때(alter_*.sql)는 항상 아래 SET NAMES … COLLATE 를 먼저 둔다.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET SESSION group_concat_max_len = 65535;

-- 아래는 db/schema.sql §6 뷰 정의(993~1299행) 사본 --------------------------------------------------------
-- HS6 × 연도 × 국가 수입·수출액. 부분연도 판정은 is_partial_year(수집이 끝나지 않은 연도)만 쓴다.
-- month_count는 "거래가 발생한 월 수"라서 12 미만이어도 부분연도가 아니다(국가×HS6 단위에서는 거래 없는 달이 흔함).
CREATE OR REPLACE VIEW v_import_hs6_year AS
SELECT f.hs6, f.year, f.stat_cd,
       SUM(f.imp_dlr)        AS imp_dlr,
       SUM(f.exp_dlr)        AS exp_dlr,
       COUNT(DISTINCT f.month) AS month_count,
       MAX(f.is_partial_year)  AS is_partial_year
FROM fact_customs_monthly f
GROUP BY f.hs6, f.year, f.stat_cd;

-- 국가 점유율·순위 (HS6 × 연도 내). ZZ(기타국) 포함.
CREATE OR REPLACE VIEW v_import_share_hs6_year AS
SELECT v.hs6, v.year, v.stat_cd, v.imp_dlr, v.is_partial_year,
       SUM(v.imp_dlr) OVER (PARTITION BY v.hs6, v.year)                     AS imp_dlr_total,
       v.imp_dlr / NULLIF(SUM(v.imp_dlr) OVER (PARTITION BY v.hs6, v.year), 0) AS share,
       RANK() OVER (PARTITION BY v.hs6, v.year ORDER BY v.imp_dlr DESC)     AS rnk
FROM v_import_hs6_year v;

-- HHI = Σ(점유율×100)² (0~10,000). "전체 수입 중" HHI이며 "방산 수입 HHI"가 아니다.
CREATE OR REPLACE VIEW v_hhi_hs6_year AS
SELECT s.hs6, s.year,
       MAX(s.imp_dlr_total)                 AS imp_dlr_total,
       SUM(POWER(s.share * 100, 2))         AS hhi,
       COUNT(*)                             AS country_count,
       MAX(CASE WHEN s.rnk = 1 THEN s.stat_cd END) AS top1_stat_cd,
       MAX(CASE WHEN s.rnk = 1 THEN s.share   END) AS top1_share,
       MAX(s.is_partial_year)               AS is_partial_year
FROM v_import_share_hs6_year s
GROUP BY s.hs6, s.year;

-- 핵심 ③ 추가 검토 목록 (연도별 전체 행. 화면에서 최근 완결연도로 필터, 기본 정렬 hhi DESC, imp_dlr_total DESC)
--
-- 정의: "선택 연도(year)의 수입 집중도" + "현재 확보한 국산화 근거". 두 축의 시점은 일치하지 않는다.
--   · 무역 열(imp_dlr_total·hhi 등)만 year를 따른다.
--   · b1_*·b2_* 열은 연도 조건 없이 현재 clean_ 테이블 전체를 센다. B2는 시점 미상 스냅샷이라 연도별 국산화 현황으로 해석하면 안 된다.
--     화면에는 근거 기준(b1_latest_round_year, B2 원본 파일 날짜 dapa_localized_items_20260509)을 따로 표시한다.
-- 건수 규칙:
--   · 집계 대상 = 품목군 대응표(ref_category_map) link_status='확정' + clean_ 쪽 category_link_status='확정'만. 후보 연결은 세지 않는다.
--   · NULL = 미확인(해당 clean_ 테이블 미적재 / 대응표 미확정 / B2 범위 밖). 0 = 확인 결과 실제로 없음. 사유는 b1_status·b2_status.
--   · b2_completed_part_count = 고유 부품 수(part_mgmt_no DISTINCT). b2_project_part_count = 사업×부품 건수(같은 부품이 사업 수만큼 반복).
--   · 한 FSC·과제가 여러 hs6에 대응하면 각 hs6 행에 중복 집계된다. HS별 값을 합산하면 같은 부품·과제가 다시 중복된다.
CREATE OR REPLACE VIEW v_review_list AS
SELECT w.hs6, w.category, w.name_ko, w.priority, w.axis,
       h.year, h.imp_dlr_total, h.top1_stat_cd, h.top1_share, h.hhi, h.country_count, h.is_partial_year,
       -- B1: KRIT 공고 과제(확정 연결·집계용 1건)
       CASE WHEN NOT EXISTS (SELECT 1 FROM clean_krit_task) THEN '미적재' ELSE '집계' END AS b1_status,
       CASE WHEN NOT EXISTS (SELECT 1 FROM clean_krit_task) THEN NULL
            ELSE (SELECT COUNT(*) FROM clean_krit_task k
                   WHERE k.hs6 = w.hs6 AND k.category_link_status = '확정' AND k.is_counted = 1) END AS b1_target_count,
       (SELECT MAX(k.round_year) FROM clean_krit_task k
         WHERE k.hs6 = w.hs6 AND k.category_link_status = '확정' AND k.is_counted = 1)    AS b1_latest_round_year,
       -- B2: 국산화개발품목(지상체계 한정, 시점 미상)
       CASE WHEN w.b2_scope = 'B2 범위 밖' THEN 'B2 범위 밖'
            WHEN NOT EXISTS (SELECT 1 FROM clean_dapa_localized_item) THEN '미적재'
            WHEN NOT EXISTS (SELECT 1 FROM ref_category_map m
                              WHERE m.map_type = 'fsc4' AND m.hs6 = w.hs6 AND m.link_status = '확정') THEN '대응표 없음'
            ELSE '집계' END                                                               AS b2_status,
       CASE WHEN w.b2_scope = 'B2 범위 밖'
              OR NOT EXISTS (SELECT 1 FROM clean_dapa_localized_item)
              OR NOT EXISTS (SELECT 1 FROM ref_category_map m
                              WHERE m.map_type = 'fsc4' AND m.hs6 = w.hs6 AND m.link_status = '확정') THEN NULL
            ELSE (SELECT COUNT(DISTINCT li.part_mgmt_no) FROM clean_dapa_localized_item li
                   JOIN ref_category_map m ON m.map_type = 'fsc4' AND m.source_key = li.fsc4
                                          AND m.hs6 = w.hs6 AND m.link_status = '확정'
                   WHERE li.category_link_status = '확정') END                            AS b2_completed_part_count,
       CASE WHEN w.b2_scope = 'B2 범위 밖'
              OR NOT EXISTS (SELECT 1 FROM clean_dapa_localized_item)
              OR NOT EXISTS (SELECT 1 FROM ref_category_map m
                              WHERE m.map_type = 'fsc4' AND m.hs6 = w.hs6 AND m.link_status = '확정') THEN NULL
            ELSE (SELECT COUNT(*) FROM clean_dapa_localized_item li
                   JOIN ref_category_map m ON m.map_type = 'fsc4' AND m.source_key = li.fsc4
                                          AND m.hs6 = w.hs6 AND m.link_status = '확정'
                   WHERE li.category_link_status = '확정') END                            AS b2_project_part_count
FROM ref_hs_whitelist w
JOIN v_hhi_hs6_year h ON h.hs6 = w.hs6;

-- 핵심 ② 월별 계약 건수·금액 (물품/용역·5분류 분리)
--   월   = 계약번호별 "최초 체결월" (MIN(contract_date)). 차수 00이 없는 계약번호가 있어 '00' 행이 아니라 MIN으로 잡는다.
--          MIN(contract_date)가 첫 차수의 계약일과 다른 계약이 있으면 정제 노트북에서 확인해 기록한다.
--   건수 = 계약번호당 1(is_latest_seq=1 행), 금액 = 최종 차수의 total_contract_amount. 변경계약은 최초 월에 최종 금액으로 잡힌다.
--   변경일 기준 월별 추이가 필요하면 이 뷰가 아니라 clean_dapa_contract.contract_date를 직접 집계한다.
CREATE OR REPLACE VIEW v_contract_monthly AS
SELECT DATE_FORMAT(f.first_contract_date, '%Y%m') AS yyyymm,
       c.biz_type, c.class5,
       COUNT(*)                     AS contract_count,
       SUM(c.total_contract_amount) AS total_contract_amount
FROM clean_dapa_contract c
JOIN (SELECT contract_no, MIN(contract_date) AS first_contract_date
      FROM clean_dapa_contract GROUP BY contract_no) f ON f.contract_no = c.contract_no
WHERE c.is_latest_seq = 1
GROUP BY DATE_FORMAT(f.first_contract_date, '%Y%m'), c.biz_type, c.class5;

-- 배경 ⓪: 연도 × 집행유형 예산(계획)·건수·전자 관련 후보(검수 확정분 별도). 관세청 수입액과 합산·비교 금지.
CREATE OR REPLACE VIEW v_overseas_plan_yearly AS
SELECT plan_year, exec_type,
       COUNT(*)                                                                     AS plan_count,
       SUM(budget_krw)                                                              AS budget_krw,
       SUM(is_contracted)                                                           AS contracted_count,
       SUM(CASE WHEN is_electronics_candidate = 1 THEN 1 ELSE 0 END)                AS elec_candidate_count,
       SUM(CASE WHEN is_electronics_candidate = 1 THEN budget_krw ELSE 0 END)       AS elec_candidate_budget_krw,
       SUM(CASE WHEN electronics_review_status = '확정' THEN budget_krw ELSE 0 END) AS elec_confirmed_budget_krw
FROM clean_dapa_overseas_plan
GROUP BY plan_year, exec_type;

-- 정량 지표 ① HS6 × HS10 용도 태그별 수입액 (완결 연도 2021~2025, is_partial_year=0). 태그는 dim_hs10.name_ko 규칙:
--   군용전용 = '9301'(군용 무기)·'9306'(폭탄·탄약) 물품 전용 세분류 / 항공기용 = '항공기용|항공용|우주항행' / 자동차용 = '자동차용' / 그 외 기타
--   군용전용 비중은 신고자가 일반 코드로 신고할 수 있어 하한선, 항공기용은 민항 포함이라 군수 비중이 아니다.
CREATE OR REPLACE VIEW v_hs10_use_share AS
SELECT t.hs6, t.use_tag,
       SUM(t.imp_dlr)                                                   AS imp_dlr,
       SUM(SUM(t.imp_dlr)) OVER (PARTITION BY t.hs6)                    AS imp_dlr_hs6,
       ROUND(100 * SUM(t.imp_dlr) / NULLIF(SUM(SUM(t.imp_dlr)) OVER (PARTITION BY t.hs6), 0), 4) AS share_pct,
       COUNT(DISTINCT t.hs10)                                           AS hs10_count,
       2021 AS period_start, 2025 AS period_end
FROM (SELECT d.hs6, d.hs10,
             CASE WHEN d.name_ko REGEXP '9301|9306'                    THEN '군용전용'
                  WHEN d.name_ko REGEXP '항공기용|항공용|우주항행'        THEN '항공기용'
                  WHEN d.name_ko REGEXP '자동차용'                       THEN '자동차용'
                  ELSE '기타' END AS use_tag,
             COALESCE(f.imp_dlr, 0) AS imp_dlr
      FROM dim_hs10 d
      LEFT JOIN fact_customs_monthly f ON f.hs10 = d.hs10 AND f.year BETWEEN 2021 AND 2025 AND f.is_partial_year = 0) t
GROUP BY t.hs6, t.use_tag;

-- 정량 지표 ② HS6별 B2 국산화개발품목 건수 (ref_category_map fsc4 경유, 후보 포함 — v_review_list의 '확정만' 규칙과 다르다).
--   FSC→HS6가 1:N(5961→4개, 5962→3개)이라 HS6 행끼리 같은 부품이 반복된다. HS6 간 합산 금지. clean_ 미적재 상태라 raw 기준.
--   조인 키는 raw의 fsc(군급분류) 열. nsn(재고번호) 열은 9자리 코드라 FSC를 담지 않는다. 고유 부품 = part_mgmt_no(v_review_list와 동일 기준).
CREATE OR REPLACE VIEW v_defense_relevance_b2 AS
SELECT m.hs6,
       GROUP_CONCAT(DISTINCT m.source_key ORDER BY m.source_key SEPARATOR ';') AS fsc4_list,
       MIN(m.link_status)                 AS link_status,
       COUNT(DISTINCT b.part_mgmt_no)     AS b2_part_count,
       COUNT(b.row_id)                    AS b2_row_count
FROM ref_category_map m
LEFT JOIN raw_dapa_localized_item b ON b.fsc = m.source_key
WHERE m.map_type = 'fsc4' AND m.hs6 IS NOT NULL
GROUP BY m.hs6;

-- B2 국산화개발품목 × FSG 집계 (핵심 ② ⓐ·ⓑ 라벨용). raw 기준(clean_ 미적재).
--    행 수 = 사업×부품 행(완전 중복 8,940 포함), 고유 부품 수 = 부품관리번호 DISTINCT. fsg_code가 ref_fsg에 없으면(공란 등) name_ko NULL.
CREATE OR REPLACE VIEW v_b2_fsg_summary AS
SELECT LEFT(b.fsc, 2)                     AS fsg_code,
       f.name_ko                           AS fsg_name_ko,
       f.name_en                           AS fsg_name_en,
       COALESCE(f.is_electronic_group, 0)  AS is_electronic_group,
       COUNT(b.row_id)                     AS b2_row_count,
       COUNT(DISTINCT b.part_mgmt_no)      AS b2_part_count,
       COUNT(DISTINCT b.project_name)      AS b2_project_count,
       COUNT(DISTINCT b.fsc)               AS fsc4_count
FROM raw_dapa_localized_item b
LEFT JOIN ref_fsg f ON f.fsg_code = LEFT(b.fsc, 2)
GROUP BY LEFT(b.fsc, 2), f.name_ko, f.name_en, f.is_electronic_group;

-- 민수 혼합 라벨 도출 규칙 (팀 규칙 2026-09-16, docs/reference/hs-whitelist-definition.md §7). ref_hs_whitelist.civil_mix 3열은 이 뷰의 스냅샷.
--   1) mil_hs10_share 있음 → <1% 높음 / 1~20% 중간 / ≥20% 낮음
--   2) 아니면 aero_hs10_share 있음 → <20% 높음 / 20~80% 중간 / ≥80% 낮음
--   3) 아니면 hsk_control_hs10_ratio 있음 → 문턱값 미정(적재 후 분포 보고 결정) — 현재는 NULL
--   4) 어느 것도 없음 → NULL, basis '판단불가'
CREATE OR REPLACE VIEW v_civil_mix_rule AS
SELECT w.hs6,
       CASE WHEN mil.value_num IS NOT NULL THEN
              CASE WHEN mil.value_num < 1 THEN '높음' WHEN mil.value_num < 20 THEN '중간' ELSE '낮음' END
            WHEN aero.value_num IS NOT NULL THEN
              CASE WHEN aero.value_num < 20 THEN '높음' WHEN aero.value_num < 80 THEN '중간' ELSE '낮음' END
            ELSE NULL END                                                        AS civil_mix_rule,
       CASE WHEN mil.value_num IS NOT NULL OR aero.value_num IS NOT NULL THEN 'hs10'
            WHEN hsk.value_num IS NOT NULL THEN 'hsk'
            ELSE '판단불가' END                                                    AS civil_mix_basis,
       CASE WHEN mil.value_num IS NOT NULL THEN
              CONCAT('군용전용 HS10 수입 비중 ', mil.value_num, '% (', mil.period_start, '~', mil.period_end, ', 하한선)')
            WHEN aero.value_num IS NOT NULL THEN
              CONCAT('항공기용 HS10 수입 비중 ', aero.value_num, '% (', aero.period_start, '~', aero.period_end, ', 민항 포함)')
            WHEN hsk.value_num IS NOT NULL THEN
              CONCAT('전략물자 통제 HSK10 비율 ', hsk.value_num, '% (문턱값 미정)')
            ELSE 'HS10 용도 세분류·HSK 연계표 어느 것도 없음' END                   AS civil_mix_note,
       mil.value_num  AS mil_hs10_share,
       aero.value_num AS aero_hs10_share,
       hsk.value_num  AS hsk_control_hs10_ratio
FROM ref_hs_whitelist w
LEFT JOIN ref_hs_indicator mil  ON mil.hs6  = w.hs6 AND mil.indicator  = 'mil_hs10_share'
LEFT JOIN ref_hs_indicator aero ON aero.hs6 = w.hs6 AND aero.indicator = 'aero_hs10_share'
LEFT JOIN ref_hs_indicator hsk  ON hsk.hs6  = w.hs6 AND hsk.indicator  = 'hsk_control_hs10_ratio';

-- -----------------------------------------------------------------------------
-- HS6 선정 규칙 (2026-09-16, docs/reference/hs-whitelist-definition.md §8). "어떤 HS6를 수집할지"를 팀 판단이 아니라
-- 공식 자료에 규칙을 적용해 도출한다. raw_hs_code_master·raw_hsk_control 적재 전에는 빈 결과(또는 전부 '규칙 미해당')를 낸다.
--   자료 S1 관세청 HS부호 마스터(15049722, 2026 현행) ∪ 수집된 dim_hs10(2016~2026 이력 코드) — 법령: 관세법 §84 → 관세·통계통합품목분류표(기획재정부 고시)
--   자료 S2 무역안보관리원 HSK 연계표(15034135) — 법령: 대외무역법 §19·§29 → 전략물자수출입고시(산업통상부 고시) **별표2 이중용도품목(0~9부)만** 실려 있다
--            (2026-09-16 확인: 2,161행 중 ML(별표3 군용물자) 0건. 통제번호는 '3A001.a.1.,5A002.' 같은 쉼표 목록). 84·85·88·90류 HS6 486개가 걸리는
--            "해당 가능성" 목록이라 단독 진입 근거로 쓰지 않는다.
--   자료 S3 B2 국산화개발품목 FSC(v_defense_relevance_b2) — ref_category_map 후보 대응이라 보조
-- 규칙(팀 규칙): R1 군용전용 HSK 존재 / R2 항공기용·항행·레이더·무인기 HSK 세분류(또는 HS6 명칭의 같은 용도어) 존재 / R3 이중용도 3·5·6·7부 통제 HSK 존재 / R4 B2 FSC 대응
--   진입 = R1 OR R2 OR (R3 AND R4). priority_rule = R1→1, R2 또는 R3∧R4→2, R4만→3(진입 아님). 범위 HS 2단위 84·85·88·90(93·87·89류는 주제 밖).
-- -----------------------------------------------------------------------------

-- 규칙 ① 관세청 HSK 용도 태그 — 현행 마스터 10자리 ∪ 수집된 dim_hs10(마스터에 없는 과거 세분류, 예 8542.31-4010 군용전용). v_hs10_use_share와 같은 규칙에 무인기·레이더·항행을 더했다.
CREATE OR REPLACE VIEW v_hs10_use_tag_all AS
SELECT u.hs6, u.hs10, u.name_ko, u.src,
       CASE WHEN u.name_ko REGEXP '9301|9306'                     THEN '군용전용'
            WHEN u.name_ko REGEXP '항공기용|항공용|우주항행'         THEN '항공기용'
            WHEN u.name_ko REGEXP '무인기|무인 항공'                 THEN '무인기'
            WHEN u.name_ko REGEXP '레이더'                          THEN '레이더'
            WHEN u.name_ko REGEXP '항행'                            THEN '항행'
            WHEN u.name_ko REGEXP '자동차용'                        THEN '자동차용'
            ELSE '기타' END AS use_tag
FROM (SELECT LEFT(m.hs_code, 6) AS hs6, m.hs_code AS hs10, m.name_ko, 'master_2026' AS src
      FROM raw_hs_code_master m WHERE m.hs_code REGEXP '^[0-9]{10}$'
      UNION ALL
      SELECT d.hs6, d.hs10, d.name_ko, 'collected'
      FROM dim_hs10 d
      WHERE NOT EXISTS (SELECT 1 FROM raw_hs_code_master m2 WHERE m2.hs_code = d.hs10)) u;

-- 규칙 ② HS6별 전략물자(이중용도) 통제 HSK. 통제번호가 쉼표 목록이라 '(^|,) *<부><그룹>' 로 찾는다. ML은 이 파일에 없어 항상 0(열은 별표3 자료를 얻을 때를 위해 남김).
CREATE OR REPLACE VIEW v_hsk_control_by_hs6 AS
SELECT LEFT(REGEXP_REPLACE(c.hsk10, '[^0-9]', ''), 6)                                                        AS hs6,
       COUNT(DISTINCT c.hsk10)                                                                               AS control_hsk10_count,
       COUNT(DISTINCT CASE WHEN UPPER(c.control_no) REGEXP '(^|,)[[:space:]]*ML'          THEN c.hsk10 END)   AS ml_hsk10_count,
       COUNT(DISTINCT CASE WHEN c.control_no REGEXP '(^|,)[[:space:]]*[3567][A-E]'        THEN c.hsk10 END)   AS du_elec_hsk10_count,
       GROUP_CONCAT(DISTINCT c.control_no ORDER BY c.control_no SEPARATOR ';')                               AS control_no_list
FROM raw_hsk_control c
WHERE c.hsk10 IS NOT NULL AND c.hsk10 <> ''
GROUP BY LEFT(REGEXP_REPLACE(c.hsk10, '[^0-9]', ''), 6);

-- 규칙 ③ HS6 후보 판정. 한 행 = 84·85·88·90류의 HS6(마스터·dim_hs10 또는 연계표에 등장). evidence_rule·evidence_note는 ref_hs_whitelist evidence 3열의 스냅샷 원본.
CREATE OR REPLACE VIEW v_hs6_candidate_rule AS
SELECT x.hs6, LEFT(x.hs6, 2) AS hs2,
       n6.name_ko                                                        AS hs6_name_ko,
       x.hs10_total, x.hs10_master, x.mil_cnt, x.aero_cnt, x.uav_cnt, x.radar_cnt, x.nav_cnt,
       COALESCE(k.control_hsk10_count, 0)                                AS control_hsk10_count,
       COALESCE(k.ml_hsk10_count, 0)                                     AS ml_hsk10_count,
       COALESCE(k.du_elec_hsk10_count, 0)                                AS du_elec_hsk10_count,
       ROUND(100 * COALESCE(k.control_hsk10_count, 0) / NULLIF(x.hs10_master, 0), 1) AS control_ratio_pct,
       k.control_no_list,
       b.b2_part_count,
       (x.mil_cnt > 0)                                                   AS r1_mil,
       (x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
        OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기')       AS r2_aero_nav,
       (COALESCE(k.ml_hsk10_count, 0) + COALESCE(k.du_elec_hsk10_count, 0) > 0) AS r3_control,
       (COALESCE(b.b2_part_count, 0) > 0)                                AS r4_b2,
       (x.mil_cnt > 0
        OR x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
        OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기'
        OR (COALESCE(k.ml_hsk10_count, 0) + COALESCE(k.du_elec_hsk10_count, 0) > 0
            AND COALESCE(b.b2_part_count, 0) > 0))                        AS is_candidate,
       CASE WHEN x.mil_cnt > 0 OR COALESCE(k.ml_hsk10_count, 0) > 0                                         THEN 1
            WHEN x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
                 OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기'
                 OR (COALESCE(k.du_elec_hsk10_count, 0) > 0 AND COALESCE(b.b2_part_count, 0) > 0)         THEN 2
            WHEN COALESCE(b.b2_part_count, 0) > 0 OR COALESCE(k.du_elec_hsk10_count, 0) > 0                THEN 3
            ELSE NULL END                                                  AS priority_rule,
       NULLIF(CONCAT_WS(';',
         IF(x.mil_cnt > 0, 'HSK-군용', NULL),
         IF(x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0 OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기', 'HSK-항공/항행', NULL),
         IF(COALESCE(k.ml_hsk10_count, 0) > 0, '전략물자-ML', NULL),
         IF(COALESCE(k.du_elec_hsk10_count, 0) > 0, '전략물자-DU', NULL),
         IF(COALESCE(b.b2_part_count, 0) > 0, 'B2-FSC', NULL)), '')        AS evidence_rule,
       CONCAT_WS(' / ',
         CONCAT('HSK10 ', x.hs10_total, '개(현행 ', x.hs10_master, ') 중 군용전용 ', x.mil_cnt, '·항공 ', x.aero_cnt, '·무인기 ', x.uav_cnt, '·레이더 ', x.radar_cnt, '·항행 ', x.nav_cnt),
         CONCAT('이중용도 통제 HSK ', COALESCE(k.control_hsk10_count, 0), '개(현행 대비 ', COALESCE(ROUND(100 * k.control_hsk10_count / NULLIF(x.hs10_master, 0)), 0), '%, 3·5·6·7부 ', COALESCE(k.du_elec_hsk10_count, 0), ')'),
         IF(b.b2_part_count IS NOT NULL, CONCAT('B2 부품 ', b.b2_part_count, '(후보 대응)'), NULL)) AS evidence_note
FROM (SELECT hs6,
             COUNT(*)                                     AS hs10_total,
             SUM(src = 'master_2026')                     AS hs10_master,
             SUM(use_tag = '군용전용')                     AS mil_cnt,
             SUM(use_tag = '항공기용')                     AS aero_cnt,
             SUM(use_tag = '무인기')                       AS uav_cnt,
             SUM(use_tag = '레이더')                       AS radar_cnt,
             SUM(use_tag = '항행')                         AS nav_cnt
      FROM v_hs10_use_tag_all GROUP BY hs6
      UNION
      SELECT k2.hs6, 0, 0, 0, 0, 0, 0, 0
      FROM v_hsk_control_by_hs6 k2
      WHERE NOT EXISTS (SELECT 1 FROM v_hs10_use_tag_all t2 WHERE t2.hs6 = k2.hs6)) x
LEFT JOIN v_hsk_control_by_hs6   k  ON k.hs6 = x.hs6
LEFT JOIN v_defense_relevance_b2 b  ON b.hs6 = x.hs6
LEFT JOIN raw_hs_unit_name       n6 ON n6.hs_code = x.hs6 AND n6.hs_unit = '06'
WHERE LEFT(x.hs6, 2) IN ('84', '85', '88', '90');

-- 규칙 ④ 규칙 후보 ↔ 현재 화이트리스트 대조(MariaDB에 FULL OUTER JOIN이 없어 UNION). 마스터 적재 전에는 21개 전부 '규칙 미해당'으로 보이므로 적재 후에만 읽는다.
CREATE OR REPLACE VIEW v_hs6_candidate_vs_whitelist AS
SELECT c.hs6, c.hs2, w.name_ko AS whitelist_name, c.hs6_name_ko AS master_name, w.category,
       w.priority AS priority_current, c.priority_rule, w.evidence AS evidence_current, c.evidence_rule, c.evidence_note,
       CASE WHEN w.hs6 IS NOT NULL THEN '유지(근거 교체)' ELSE '신규 후보(미수집)' END AS verdict
FROM v_hs6_candidate_rule c
LEFT JOIN ref_hs_whitelist w ON w.hs6 = c.hs6
WHERE c.is_candidate = 1
UNION ALL
SELECT w.hs6, LEFT(w.hs6, 2), w.name_ko, c.hs6_name_ko, w.category,
       w.priority, c.priority_rule, w.evidence, c.evidence_rule, c.evidence_note,
       '강등·제외 검토(규칙 미해당)'
FROM ref_hs_whitelist w
LEFT JOIN v_hs6_candidate_rule c ON c.hs6 = w.hs6
WHERE c.hs6 IS NULL OR c.is_candidate = 0;

-- 화이트리스트 × 규칙 스냅샷(최신 rule_version). 화면·노트북이 24개의 R1~R4 플래그와 근거 수치를 한 번에 읽는다.
CREATE OR REPLACE VIEW v_hs_whitelist_rule AS
SELECT w.hs6, w.category, w.name_ko, w.system_family, w.priority, w.axis, w.evidence, w.evidence_basis, w.evidence_note,
       w.civil_mix, w.civil_mix_basis,
       f.rule_version, f.r1_mil, f.r2_aero_nav, f.r3_du, f.r3_ml, f.r4_b2,
       f.mil_cnt, f.aero_cnt, f.uav_cnt, f.radar_cnt, f.nav_cnt, f.hs10_total, f.hs10_master,
       f.control_hsk10_count, f.du_elec_hsk10_count, f.ml_hsk10_count, f.control_ratio_pct, f.b2_part_count,
       f.is_candidate_provisional, f.priority_rule, f.computed_at
FROM ref_hs_whitelist w
LEFT JOIN ref_hs_rule_flag f
       ON f.hs6 = w.hs6
      AND f.rule_version = (SELECT MAX(rule_version) FROM ref_hs_rule_flag);

-- 검증 ---------------------------------------------------------------------------------------------------
SELECT TABLE_NAME, COLLATION_CONNECTION FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'defense_dashboard' ORDER BY TABLE_NAME;
SELECT COUNT(*) AS review_list_2025_rows FROM v_review_list WHERE b1_status = '미적재' AND year = 2025;
