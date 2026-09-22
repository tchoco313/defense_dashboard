-- =============================================================================
-- raw_ 계층 제거 1/2 — 후속 표 4개 신설 · 뷰 4개 재정의 · raw_ 참조 FK 15개 제거  (작성 2026-09-22)
--
-- 결정: 2026-09-22 교수 중간 점검 피드백(docs/report/feedback/professor-feedback-2026-09-22.md §1) — 원본은 파일로,
--       DB 에는 정제·기준·기록 표와 뷰만 둔다. 이 파일은 raw_ 표를 아직 지우지 않는다(DROP 은 2/2
--       alter_2026-09-22_drop_raw_layer.sql — 노트북 재실행 검증 뒤 사용자 확인 후 적용).
-- 배경: 뷰 4개·앱 4쿼리가 raw_ 를 직접 읽었고 clean 14표 + fact 1표가 raw_ 의 row_id 를 FK 로 참조했다.
--       원본 파일 ↔ RDS raw_ 동일성은 2026-09-22 실측(22표 열별 비NULL 수·문자 길이 합 일치. raw_customs_region 은
--       파일이 이 PC 에 없어 DB → clean 변환만). row_id = 파서 순번(read_raw) 은 20표 일치, 불일치 2표는 §3 에서 처리.
-- 조치: §1 후속 표 4개(사용처가 있는 것만, 필요한 열·행만) CREATE + INSERT…SELECT
--         ref_hs_code_master   2026 현행 HSK10 11,327(원본 12,469 중 10자리; 규격·단위 열 제외) — 화면 HS10 라벨·dim_hs10·v_hs10_use_tag_all
--         ref_hs6_name         06시트 6자리 2,254(원본 17,072; 10시트는 마스터와 코드·품명 동일해 제외) — v_hs6_candidate_rule·ref_hs_rule_flag 이름
--         clean_customs_region HS6 × 시군구 × 월 273,586(형 변환, 금액 천 달러) — v_customs_region_gwacheon_year(화면 24)
--         clean_dapa_defense_company 84(지정일 DATE, seq_no PK) — v_defense_company_sector(화면 4)·업체명 연결
--       §2 뷰 4개 raw_ → 후속 표 (v_hs6_candidate_vs_whitelist 는 열이 같아 재정의 불필요)
--       §3 계보 정리: fact_customs_monthly.raw_row_id 삭제(2회 적재로 순번 불일치 — 자연키 hs10+stat_cd+yyyymm 로 충분),
--         clean_krit_task.raw_row_id 96행을 파서 순번으로 재번호(차수별 추가 적재로 순번이 달랐음)
--       §4 raw_ 참조 FK 15개 DROP (열은 유지 — raw_row_id = 원본 파일 파서 순번)
--       §5 열 사전(meta_column_dict) — 새 표 4개 등록, raw_row_id 설명 교체
--       §6 검증
-- 정본 동기(이 파일과 같은 커밋): db/schema.sql(CREATE +4, FK -15, fact 열 -1, 뷰 4), db/reset_data.sql, db/table_dict.csv(+4),
--       db/column_dict.csv(+N), scripts/load_db.py(--ref/--fact 가 4표를 파일에서 만든다), notebooks/clean_p1·p4.
-- 되돌리기: §1 표 4개 DROP, 뷰 4개는 git 이력 schema.sql 정의로, FK 는 raw_ 표가 남아 있는 동안만 재생성 가능.
-- 멱등: CREATE TABLE IF NOT EXISTS · INSERT IGNORE(PK 충돌 무시) · CREATE OR REPLACE VIEW · FK/열 DROP 은 information_schema 가드.
--       §3 재번호는 old 값이 남아 있을 때만 바뀌므로 2회째 0행.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-22_raw_successors.sql
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- §1. 후속 표 4개
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ref_hs_code_master (
  hs10         CHAR(10)     NOT NULL COMMENT 'HSK 10자리(2026-01-01 현행)',
  name_ko      VARCHAR(500) NULL COMMENT '한글품목명(관세청 HS부호 마스터 15049722)',
  name_en      VARCHAR(600) NULL COMMENT '영문품목명',
  apply_start  DATE         NULL COMMENT '적용시작일자',
  apply_end    DATE         NULL COMMENT '적용종료일자(현행 코드는 전부 2026-12-31)',
  PRIMARY KEY (hs10),
  KEY ix_rhcm_hs6 (hs10(6))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='관세청 HS부호 마스터(15049722) 중 2026 현행 HSK10 11,327행 — 화면 HS10 품명 라벨 · dim_hs10 보강 · v_hs10_use_tag_all(선정 규칙 R1·R2). 원본 파일 raw_hs_code_master 12,469행(7~9자리 1,142 · 규격/단위 열은 사용처 없어 제외)';

INSERT IGNORE INTO ref_hs_code_master (hs10, name_ko, name_en, apply_start, apply_end)
SELECT hs_code, name_ko, name_en, STR_TO_DATE(LEFT(apply_start, 10), '%Y-%m-%d'), STR_TO_DATE(LEFT(apply_end, 10), '%Y-%m-%d')
FROM raw_hs_code_master WHERE hs_code REGEXP '^[0-9]{10}$';

CREATE TABLE IF NOT EXISTS ref_hs6_name (
  hs6      CHAR(6)      NOT NULL COMMENT 'HS 6자리',
  name_ko  VARCHAR(700) NULL COMMENT '한글품목명(관세청 HS부호 단위별 품목명 15130660, HS6 시트)',
  name_en  VARCHAR(800) NULL COMMENT '영문품목명',
  PRIMARY KEY (hs6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='HS6 공식 명칭 2,254행 — v_hs6_candidate_rule R2 용도어 · ref_hs_rule_flag.hs6_name_ko. 원본 파일 raw_hs_unit_name 5시트 17,072행 중 06시트 6자리만(5자리 중간 수준 1,024 제외, 10시트 11,327은 ref_hs_code_master 와 코드·품명 동일)';

INSERT IGNORE INTO ref_hs6_name (hs6, name_ko, name_en)
SELECT hs_code, name_ko, name_en FROM raw_hs_unit_name WHERE hs_unit = '06' AND hs_code REGEXP '^[0-9]{6}$';

CREATE TABLE IF NOT EXISTS clean_customs_region (
  hs6                 CHAR(6)      NOT NULL COMMENT '요청 HS6(원본 req_hs = hs_cd)',
  sido_code           CHAR(2)      NOT NULL COMMENT '요청 시도코드(11 26 27 28 29 30 31 36 41 43 44 46 47 48 50 51 52)',
  sgg_name            VARCHAR(50)  NOT NULL COMMENT '시도 + 시군구명(원본 sggNm, 예 경기도 과천시). 코드 없음',
  yyyymm              CHAR(6)      NOT NULL COMMENT '원본 stat_ym YYYY.MM → YYYYMM',
  year                SMALLINT     NOT NULL,
  month               TINYINT      NOT NULL,
  exp_cnt             INT          NULL COMMENT '수출 건수',
  exp_kusd            BIGINT       NULL COMMENT '수출액 천 달러',
  imp_cnt             INT          NULL COMMENT '수입 건수',
  imp_kusd            BIGINT       NULL COMMENT '수입액 천 달러 — 납세의무자 주소지 기준',
  trade_balance_kusd  BIGINT       NULL COMMENT '무역수지 천 달러',
  is_partial_year     TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '2026(1~8월) = 1',
  PRIMARY KEY (hs6, sgg_name, yyyymm),
  KEY ix_ccr_hs6_year (hs6, year),
  KEY ix_ccr_sido_year (sido_code, year),
  CONSTRAINT fk_ccr_hs6 FOREIGN KEY (hs6) REFERENCES ref_hs_whitelist (hs6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='관세청 시군구별 수출입실적(15134343) 정제 — HS6 × 시군구 × 월 273,586행(24 HS6 × 시도 17, 2016.01~2026.08). v_customs_region_gwacheon_year(화면 24 과천시 비중 KPI) 원천. 원본 파일 raw_customs_region(customs_region_<HS6>.csv, 파서 순번 = 자연키로 추적)';

INSERT IGNORE INTO clean_customs_region
  (hs6, sido_code, sgg_name, yyyymm, year, month, exp_cnt, exp_kusd, imp_cnt, imp_kusd, trade_balance_kusd, is_partial_year)
SELECT req_hs, req_sido, sgg_name, CONCAT(LEFT(stat_ym, 4), RIGHT(stat_ym, 2)),
       CAST(LEFT(stat_ym, 4) AS SIGNED), CAST(RIGHT(stat_ym, 2) AS SIGNED),
       CAST(REPLACE(exp_cnt, ',', '') AS SIGNED), CAST(REPLACE(exp_usd_amt, ',', '') AS SIGNED),
       CAST(REPLACE(imp_cnt, ',', '') AS SIGNED), CAST(REPLACE(imp_usd_amt, ',', '') AS SIGNED),
       CAST(REPLACE(trade_balance_amt, ',', '') AS SIGNED), IF(LEFT(stat_ym, 4) = '2026', 1, 0)
FROM raw_customs_region;

CREATE TABLE IF NOT EXISTS clean_dapa_defense_company (
  seq_no           SMALLINT     NOT NULL COMMENT '원본 순번',
  company_name     VARCHAR(200) NOT NULL COMMENT '업체명',
  sector           VARCHAR(20)  NULL COMMENT '분야(함정·항공유도·기동·화생방·화력·탄약·기타·통신전자·항공). 공란 3 = NULL → 뷰 「미기재」',
  designated_date  DATE         NULL COMMENT '지정일자',
  note             VARCHAR(300) NULL COMMENT '비고',
  raw_row_id       BIGINT UNSIGNED NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_defense_company)',
  cleaned_at       DATETIME     NULL,
  cleaned_by       VARCHAR(50)  NULL,
  PRIMARY KEY (seq_no),
  UNIQUE KEY ux_cdfc_name (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='방산업체 지정현황(방위사업청, 2026-08-31) 84행 정제 — v_defense_company_sector(화면 4 배경) · clean_company_name_link 업체명 연결 원천. 원본 파일 raw_dapa_defense_company';

INSERT IGNORE INTO clean_dapa_defense_company (seq_no, company_name, sector, designated_date, note, raw_row_id, cleaned_at, cleaned_by)
SELECT CAST(seq_no AS SIGNED), company_name, NULLIF(sector, ''), STR_TO_DATE(designated_date, '%Y-%m-%d'), note, row_id, NOW(), CURRENT_USER()
FROM raw_dapa_defense_company;

-- -----------------------------------------------------------------------------
-- §2. 뷰 4개 — raw_ 대신 후속 표
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_customs_region_gwacheon_year AS
SELECT r.hs6,
       r.year,
       SUM(r.imp_kusd)                                                          AS imp_kusd_total,
       SUM(CASE WHEN r.sgg_name = '경기도 과천시' THEN r.imp_kusd ELSE 0 END)     AS imp_kusd_gwacheon,
       CAST(SUM(CASE WHEN r.sgg_name = '경기도 과천시' THEN r.imp_kusd ELSE 0 END) AS DOUBLE)
         / NULLIF(SUM(r.imp_kusd), 0)                                           AS gwacheon_share,
       SUM(CASE WHEN r.sgg_name = '경기도 과천시' THEN r.imp_cnt ELSE 0 END)      AS imp_cnt_gwacheon,
       COUNT(DISTINCT r.sgg_name)                                                AS sgg_count,
       MAX(r.is_partial_year)                                                    AS is_partial_year
FROM clean_customs_region r
GROUP BY r.hs6, r.year;

CREATE OR REPLACE VIEW v_hs10_use_tag_all AS
SELECT u.hs6, u.hs10, u.name_ko, u.src,
       CASE WHEN u.name_ko REGEXP '9301|9306'                     THEN '군용전용'
            WHEN u.name_ko REGEXP '항공기용|항공용|우주항행'         THEN '항공기용'
            WHEN u.name_ko REGEXP '무인기|무인 항공'                 THEN '무인기'
            WHEN u.name_ko REGEXP '레이더'                          THEN '레이더'
            WHEN u.name_ko REGEXP '항행'                            THEN '항행'
            WHEN u.name_ko REGEXP '자동차용'                        THEN '자동차용'
            ELSE '기타' END AS use_tag
FROM (SELECT LEFT(m.hs10, 6) AS hs6, m.hs10, m.name_ko, 'master_2026' AS src
      FROM ref_hs_code_master m
      UNION ALL
      SELECT d.hs6, d.hs10, d.name_ko, 'collected'
      FROM dim_hs10 d
      WHERE NOT EXISTS (SELECT 1 FROM ref_hs_code_master m2 WHERE m2.hs10 = d.hs10)) u;

CREATE OR REPLACE VIEW v_hs6_candidate_rule AS
SELECT x.hs6, LEFT(x.hs6, 2) AS hs2,
       n6.name_ko                                                        AS hs6_name_ko,
       x.hs10_total, x.hs10_master, x.mil_cnt, x.aero_cnt, x.uav_cnt, x.radar_cnt, x.nav_cnt,
       COALESCE(k.control_hsk10_count, 0)                                AS control_hsk10_count,
       COALESCE(k.ml_hsk10_count, 0)                                     AS ml_hsk10_count,
       COALESCE(k.du_elec_hsk10_count, 0)                                AS du_elec_hsk10_count,
       ROUND(100 * COALESCE(k.control_hsk10_count, 0) / NULLIF(x.hs10_master, 0), 1) AS control_ratio_pct,
       k.control_no_list,
       CAST(NULL AS SIGNED)                                              AS b2_part_count,
       (x.mil_cnt > 0)                                                   AS r1_mil,
       (x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
        OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기')       AS r2_aero_nav,
       (COALESCE(k.ml_hsk10_count, 0) + COALESCE(k.du_elec_hsk10_count, 0) > 0) AS r3_control,
       0                                                                 AS r4_b2,
       (x.mil_cnt > 0
        OR x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
        OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기')       AS is_candidate,
       CASE WHEN x.mil_cnt > 0 OR COALESCE(k.ml_hsk10_count, 0) > 0                                         THEN 1
            WHEN x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
                 OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기'             THEN 2
            WHEN COALESCE(k.du_elec_hsk10_count, 0) > 0                                                     THEN 3
            ELSE NULL END                                                  AS priority_rule,
       NULLIF(CONCAT_WS(CHAR(59),
         IF(x.mil_cnt > 0, 'HSK-군용', NULL),
         IF(x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0 OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기', 'HSK-항공/항행', NULL),
         IF(COALESCE(k.ml_hsk10_count, 0) > 0, '전략물자-ML', NULL),
         IF(COALESCE(k.du_elec_hsk10_count, 0) > 0, '전략물자-DU', NULL)), '')        AS evidence_rule,
       CONCAT_WS(' / ',
         CONCAT('HSK10 ', x.hs10_total, '개(현행 ', x.hs10_master, ') 중 군용전용 ', x.mil_cnt, '·항공 ', x.aero_cnt, '·무인기 ', x.uav_cnt, '·레이더 ', x.radar_cnt, '·항행 ', x.nav_cnt),
         CONCAT('이중용도 통제 HSK ', COALESCE(k.control_hsk10_count, 0), '개(현행 대비 ', COALESCE(ROUND(100 * k.control_hsk10_count / NULLIF(x.hs10_master, 0)), 0), '%, 3·5·6·7부 ', COALESCE(k.du_elec_hsk10_count, 0), ')')) AS evidence_note
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
LEFT JOIN ref_hs6_name           n6 ON n6.hs6 = x.hs6
WHERE LEFT(x.hs6, 2) IN ('84', '85', '88', '90');

CREATE OR REPLACE VIEW v_defense_company_sector AS
SELECT COALESCE(sector, '미기재')                                          AS sector,
       COUNT(*)                                                           AS company_count,
       MIN(YEAR(designated_date))                                         AS first_designated_year,
       MAX(YEAR(designated_date))                                         AS last_designated_year
FROM clean_dapa_defense_company
GROUP BY COALESCE(sector, '미기재');

-- -----------------------------------------------------------------------------
-- §3. 계보 정리 — fact 의 raw_row_id 삭제(FK·UNIQUE 포함), clean_krit_task 재번호
-- -----------------------------------------------------------------------------
SET @has := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'defense_dashboard' AND table_name = 'fact_customs_monthly' AND column_name = 'raw_row_id');
SET @ddl := IF(@has > 0, 'ALTER TABLE fact_customs_monthly DROP FOREIGN KEY fk_fcm_raw, DROP INDEX ux_fcm_raw, DROP COLUMN raw_row_id', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;

-- clean_krit_task: RDS row_id(차수별 추가 적재 순) → read_raw 파서 순번(파일명 정렬 × 행 순). 2026-09-22 파일·DB (source_file, source_row_no) 대조로 만든 96행 매핑
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_ckt_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_krit_task DROP FOREIGN KEY fk_ckt_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @already := (SELECT COUNT(*) FROM clean_krit_task WHERE raw_row_id BETWEEN 1 AND 2);
UPDATE clean_krit_task SET raw_row_id = CASE raw_row_id
    WHEN 3 THEN 1 WHEN 4 THEN 2 WHEN 5 THEN 3 WHEN 6 THEN 4 WHEN 7 THEN 5 WHEN 8 THEN 6 WHEN 9 THEN 7 WHEN 10 THEN 8
    WHEN 11 THEN 9 WHEN 12 THEN 10 WHEN 13 THEN 11 WHEN 14 THEN 12 WHEN 15 THEN 13 WHEN 16 THEN 14 WHEN 17 THEN 15 WHEN 18 THEN 16
    WHEN 19 THEN 17 WHEN 20 THEN 18 WHEN 21 THEN 19 WHEN 22 THEN 20 WHEN 23 THEN 21 WHEN 24 THEN 22 WHEN 25 THEN 23 WHEN 26 THEN 24
    WHEN 27 THEN 25 WHEN 28 THEN 26 WHEN 29 THEN 27 WHEN 30 THEN 28 WHEN 31 THEN 29 WHEN 32 THEN 30 WHEN 33 THEN 31 WHEN 34 THEN 32
    WHEN 35 THEN 33 WHEN 36 THEN 34 WHEN 37 THEN 35 WHEN 38 THEN 36 WHEN 39 THEN 37 WHEN 40 THEN 38 WHEN 41 THEN 39 WHEN 42 THEN 40
    WHEN 43 THEN 41 WHEN 44 THEN 42 WHEN 45 THEN 43 WHEN 46 THEN 44 WHEN 47 THEN 45 WHEN 48 THEN 46 WHEN 49 THEN 47 WHEN 50 THEN 48
    WHEN 51 THEN 49 WHEN 52 THEN 50 WHEN 53 THEN 51 WHEN 54 THEN 52 WHEN 55 THEN 53 WHEN 56 THEN 54 WHEN 57 THEN 55 WHEN 58 THEN 56
    WHEN 59 THEN 57 WHEN 60 THEN 58 WHEN 61 THEN 59 WHEN 62 THEN 60 WHEN 63 THEN 61 WHEN 64 THEN 62 WHEN 65 THEN 63 WHEN 66 THEN 64
    WHEN 67 THEN 65 WHEN 68 THEN 66 WHEN 69 THEN 67 WHEN 70 THEN 68 WHEN 71 THEN 69 WHEN 72 THEN 70 WHEN 73 THEN 71 WHEN 74 THEN 72
    WHEN 75 THEN 73 WHEN 76 THEN 74 WHEN 77 THEN 75 WHEN 78 THEN 76 WHEN 79 THEN 77 WHEN 80 THEN 78 WHEN 81 THEN 79 WHEN 82 THEN 80
    WHEN 83 THEN 81 WHEN 84 THEN 82 WHEN 85 THEN 83 WHEN 86 THEN 84 WHEN 87 THEN 85 WHEN 88 THEN 86 WHEN 89 THEN 87 WHEN 90 THEN 88
    WHEN 91 THEN 89 WHEN 92 THEN 90 WHEN 93 THEN 91 WHEN 94 THEN 92 WHEN 95 THEN 93 WHEN 96 THEN 94 WHEN 97 THEN 95 WHEN 98 THEN 96
    ELSE raw_row_id END
  WHERE @already = 0 AND raw_row_id BETWEEN 3 AND 98;

-- -----------------------------------------------------------------------------
-- §4. raw_ 참조 FK 14개 DROP (fk_fcm_raw·fk_ckt_raw 는 §3 에서). 열 raw_row_id / first_raw_row_id 는 유지
-- -----------------------------------------------------------------------------
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_cdc_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_contract DROP FOREIGN KEY fk_cdc_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_copb_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_openfiscal_program_budget DROP FOREIGN KEY fk_copb_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_chc_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_hsk_control DROP FOREIGN KEY fk_chc_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_cop_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_overseas_plan DROP FOREIGN KEY fk_cop_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_cbn_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_bid_notice DROP FOREIGN KEY fk_cbn_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_cbr_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_bid_result DROP FOREIGN KEY fk_cbr_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_cdp_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_domestic_plan DROP FOREIGN KEY fk_cdp_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_ces_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_contract_exec_by_service DROP FOREIGN KEY fk_ces_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_copa_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_overseas_plan_api DROP FOREIGN KEY fk_copa_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_coc_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_overseas_contract DROP FOREIGN KEY fk_coc_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_cobr_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_dapa_overseas_bid_result DROP FOREIGN KEY fk_cobr_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_cku_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_kosis_utilization DROP FOREIGN KEY fk_cku_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;
SET @has := (SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND constraint_name = 'fk_ckp_raw');
SET @ddl := IF(@has > 0, 'ALTER TABLE clean_kosis_production_index DROP FOREIGN KEY fk_ckp_raw', 'SELECT 1');
PREPARE s FROM @ddl; EXECUTE s; DEALLOCATE PREPARE s;

-- -----------------------------------------------------------------------------
-- §5. 열 사전 — 새 표 4개(dtype 은 DDL 그대로), raw_row_id 설명 교체(원본 파일 파서 순번)
-- -----------------------------------------------------------------------------
INSERT IGNORE INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
 ('ref_hs_code_master', 1, 'hs10', 'HS부호', 'CHAR(10)', 'HSK 10자리(2026-01-01 현행). PK. 원본 파일 raw_hs_code_master 12,469행 중 10자리 11,327'),
 ('ref_hs_code_master', 2, 'name_ko', '한글품목명', 'VARCHAR(500)', '한글품목명(관세청 HS부호 마스터 15049722)'),
 ('ref_hs_code_master', 3, 'name_en', '영문품목명', 'VARCHAR(600)', '영문품목명'),
 ('ref_hs_code_master', 4, 'apply_start', '적용시작일자', 'DATE', '적용시작일자'),
 ('ref_hs_code_master', 5, 'apply_end', '적용종료일자', 'DATE', '적용종료일자(현행 코드는 전부 2026-12-31)'),
 ('ref_hs6_name', 1, 'hs6', 'HS6단위', 'CHAR(6)', 'HS 6자리. PK. 원본 파일 raw_hs_unit_name 06시트 중 6자리 2,254(5자리 중간 수준 제외)'),
 ('ref_hs6_name', 2, 'name_ko', '한글품목명', 'VARCHAR(700)', '한글품목명(관세청 HS부호 단위별 품목명 15130660)'),
 ('ref_hs6_name', 3, 'name_en', '영문품목명', 'VARCHAR(800)', '영문품목명'),
 ('clean_customs_region', 1, 'hs6', 'hsSgn', 'CHAR(6)', '요청 HS6(원본 req_hs = hs_cd). PK 1/3'),
 ('clean_customs_region', 2, 'sido_code', 'sidoCd', 'CHAR(2)', '요청 시도코드 17개'),
 ('clean_customs_region', 3, 'sgg_name', 'sggNm', 'VARCHAR(50)', '시도 + 시군구명(예 경기도 과천시). PK 2/3'),
 ('clean_customs_region', 4, 'yyyymm', 'priodTitle', 'CHAR(6)', 'YYYY.MM → YYYYMM. PK 3/3'),
 ('clean_customs_region', 5, 'year', '(파생)', 'SMALLINT', 'yyyymm 앞 4자리'),
 ('clean_customs_region', 6, 'month', '(파생)', 'TINYINT', 'yyyymm 뒤 2자리'),
 ('clean_customs_region', 7, 'exp_cnt', 'expCnt', 'INT', '수출 건수(쉼표 제거·정수)'),
 ('clean_customs_region', 8, 'exp_kusd', 'expUsdAmt', 'BIGINT', '수출액 천 달러'),
 ('clean_customs_region', 9, 'imp_cnt', 'impCnt', 'INT', '수입 건수'),
 ('clean_customs_region', 10, 'imp_kusd', 'impUsdAmt', 'BIGINT', '수입액 천 달러 — 납세의무자 주소지 기준'),
 ('clean_customs_region', 11, 'trade_balance_kusd', 'cmtrBlncAmt', 'BIGINT', '무역수지 천 달러'),
 ('clean_customs_region', 12, 'is_partial_year', '(파생)', 'TINYINT(1)', '2026(1~8월) = 1'),
 ('clean_dapa_defense_company', 1, 'seq_no', '순번', 'SMALLINT', '원본 순번. PK'),
 ('clean_dapa_defense_company', 2, 'company_name', '업체명', 'VARCHAR(200)', '업체명(UNIQUE)'),
 ('clean_dapa_defense_company', 3, 'sector', '분야', 'VARCHAR(20)', '분야. 공란 3 = NULL → 뷰 「미기재」'),
 ('clean_dapa_defense_company', 4, 'designated_date', '지정일자', 'DATE', '지정일자'),
 ('clean_dapa_defense_company', 5, 'note', '비고', 'VARCHAR(300)', '비고'),
 ('clean_dapa_defense_company', 6, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '원본 파일 파서 순번(read_raw raw_dapa_defense_company)'),
 ('clean_dapa_defense_company', 7, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
 ('clean_dapa_defense_company', 8, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 계정');

-- raw_row_id·first_raw_row_id 설명(19행)·fact 열 삭제 등 사전 정리는 2/2 alter_2026-09-22_drop_raw_layer.sql §3 에서 CSV 와 함께 맞춘다.

-- -----------------------------------------------------------------------------
-- §6. 검증 — 기대: 표 4개 행 수 11,327 / 2,254 / 273,586 / 84, raw_ 참조 FK 0, fact 열 없음, krit 재번호 1~96
-- -----------------------------------------------------------------------------
SELECT 'ref_hs_code_master' t, COUNT(*) n FROM ref_hs_code_master
UNION ALL SELECT 'ref_hs6_name', COUNT(*) FROM ref_hs6_name
UNION ALL SELECT 'clean_customs_region', COUNT(*) FROM clean_customs_region
UNION ALL SELECT 'clean_dapa_defense_company', COUNT(*) FROM clean_dapa_defense_company
UNION ALL SELECT 'fk_to_raw', COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = 'defense_dashboard' AND referenced_table_name LIKE 'raw\_%'
UNION ALL SELECT 'fact_raw_row_id_col', COUNT(*) FROM information_schema.columns WHERE table_schema = 'defense_dashboard' AND table_name = 'fact_customs_monthly' AND column_name = 'raw_row_id'
UNION ALL SELECT 'krit_raw_row_id_1_96', COUNT(*) FROM clean_krit_task WHERE raw_row_id BETWEEN 1 AND 96
UNION ALL SELECT 'v_gwacheon_rows', COUNT(*) FROM v_customs_region_gwacheon_year
UNION ALL SELECT 'v_use_tag_rows', COUNT(*) FROM v_hs10_use_tag_all
UNION ALL SELECT 'v_candidate_rows', COUNT(*) FROM v_hs6_candidate_rule
UNION ALL SELECT 'v_sector_rows', COUNT(*) FROM v_defense_company_sector;
