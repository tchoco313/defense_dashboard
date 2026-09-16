-- =============================================================================
-- 정량 지표 도입: ref_hs_indicator · raw_hsk_control · 뷰 3개 · ref_hs_whitelist civil_mix 3열 (작성 2026-09-16, 팀 서버 적용 2026-09-16 — 계정 defense, mariadb.exe 2회 실행으로 재실행성 확인, 검증값 §7 기대와 일치)
--
-- 근거: docs/reference/hs-whitelist-definition.md §7 (지표 정의·문턱값), docs/report/design-validity-review-2026-09-15.md §2-3
-- 목적: civil_mix "팀 판단" 라벨을 폐기하고, 관세청 HS10 용도 세분류 수입 비중(7개 품목군)으로 규칙 도출한 값만 남긴다.
--       정량 경로가 없는 14개 품목군은 NULL(civil_mix_basis='판단불가').
-- 실행: DBHub는 readonly라 불가. docs/runbook/commands.md "DB 스키마 적용"과 같이 mariadb.exe + MYSQL_PWD 로:
--       mariadb.exe -h <서버IP> -u <계정> --protocol=TCP --skip-ssl-verify-server-cert --default-character-set=utf8mb4 defense_dashboard < db/alter_2026-09-16_indicator.sql
-- 재실행: 가능. ALTER는 information_schema 검사 후 건너뛰고, CREATE TABLE IF NOT EXISTS, 뷰는 OR REPLACE, 지표는 삭제 후 재삽입, 열 사전은 ON DUPLICATE KEY.
-- 순서: §1 ALTER → §2 CREATE TABLE 2 → §3 뷰 3 → §4 지표 INSERT → §5 civil_mix UPDATE → §6 meta_column_dict → §7 검증
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4;

-- §1 ref_hs_whitelist 열 추가 (이미 있으면 건너뜀)
SET @has_col = (SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'ref_hs_whitelist' AND COLUMN_NAME = 'civil_mix_basis');
SET @q = IF(@has_col = 0,
  "ALTER TABLE ref_hs_whitelist
     MODIFY COLUMN civil_mix ENUM('높음','중간','낮음') NULL COMMENT '민수 혼합 정도 — v_civil_mix_rule 규칙 도출값 스냅샷(2026-09-16). 정량 지표 없는 품목군은 NULL(판단불가). 09-15 팀 판단 라벨은 폐기',
     ADD COLUMN civil_mix_basis ENUM('hs10','hsk','판단불가') NOT NULL DEFAULT '판단불가' COMMENT 'civil_mix를 정한 지표 종류: hs10=관세청 HS10 용도 세분류 수입 비중, hsk=전략물자 HSK 연계표(적재 후), 판단불가=정량 경로 없음' AFTER civil_mix,
     ADD COLUMN civil_mix_note VARCHAR(200) NULL COMMENT '근거 수치 요약(예: 군용전용 HS10 0.026% 2021~2025). ref_hs_indicator에 원값' AFTER civil_mix_basis,
     COMMENT = 'HS6 화이트리스트 21개 — 품목군 기준표(원본 15열: 8열 + 2026-09-15 정의 열 4개 + civil_mix·civil_mix_basis·civil_mix_note)'",
  "SELECT 'civil_mix_basis already exists, ALTER skipped' AS info");
PREPARE s1 FROM @q; EXECUTE s1; DEALLOCATE PREPARE s1;

-- §2 테이블 (정의는 db/schema.sql과 동일하게 유지)
CREATE TABLE IF NOT EXISTS ref_hs_indicator (
  indicator_id  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  hs6           CHAR(6)      NOT NULL,
  axis          ENUM('civil_mix','defense_relevance') NOT NULL,
  indicator     VARCHAR(30)  NOT NULL COMMENT 'mil_hs10_share / aero_hs10_share / auto_hs10_share / hsk_control_hs10_ratio / hsk_control_imp_share / b2_part_count / b2_row_count / a7_plan_count / a7_plan_budget / krit_task_count',
  value_num     DECIMAL(18,4) NOT NULL COMMENT '비율(%)이면 0~100, 건수·금액이면 그 값',
  numerator     BIGINT       NULL COMMENT '분자(재현용)',
  denominator   BIGINT       NULL COMMENT '분모(재현용). 건수 지표는 NULL',
  unit          VARCHAR(10)  NOT NULL COMMENT '% / 건 / USD / KRW',
  period_start  SMALLINT     NULL COMMENT '연도. 시점 미상(B2)은 NULL',
  period_end    SMALLINT     NULL,
  period_key    SMALLINT     GENERATED ALWAYS AS (COALESCE(period_end, 0)) STORED
                COMMENT 'UNIQUE용. period_end NULL(시점 미상)은 UNIQUE에서 서로 다른 값으로 취급돼 중복을 못 막으므로 0으로 치환(ref_category_map.hs6_key와 같은 이유)',
  link_status   ENUM('확정','후보','해당없음') NOT NULL DEFAULT '해당없음' COMMENT '대응표 경유 지표만 확정/후보. 관세청 HS10 지표는 해당없음',
  source        VARCHAR(50)  NOT NULL COMMENT 'meta_dataset.dataset_key',
  method        VARCHAR(300) NOT NULL COMMENT '산식 또는 뷰 이름',
  computed_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  note          VARCHAR(300) NULL COMMENT '해석 한계(하한선·민항 포함·1:N 중복 등)',
  PRIMARY KEY (indicator_id),
  UNIQUE KEY ux_ind (hs6, indicator, period_key),
  KEY ix_ind_axis (axis, indicator),
  CONSTRAINT fk_ind_hs6 FOREIGN KEY (hs6) REFERENCES ref_hs_whitelist (hs6)
) ENGINE=InnoDB COMMENT='품목군별 정량 지표(민수 혼합·국방 관련성) — 라벨의 수치 근거';

CREATE TABLE IF NOT EXISTS raw_hsk_control (
  row_id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  hsk10          VARCHAR(12)  NULL COMMENT '품목번호(HSK 10자리)',
  name_ko        VARCHAR(300) NULL COMMENT '품명(국문)',
  name_en        VARCHAR(300) NULL COMMENT '품명(영문)',
  control_no     VARCHAR(30)  NULL COMMENT '통제번호(전략물자 통제 리스트 번호)',
  source_file    VARCHAR(100) NOT NULL,
  source_row_no  INT UNSIGNED NULL,
  loaded_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_hsk10 (hsk10)
) ENGINE=InnoDB COMMENT='무역안보관리원 HSK 연계표 원본(15034135). 미확보 — 사용자 다운로드 후 load_db.py --raw';

-- §2-1 (2026-09-16 1차 실행분 보정) period_key 생성열이 없으면 추가하고 UNIQUE를 교체.
--   UNIQUE 교체 전에 period_end NULL 로 중복 적재된 B2 행을 먼저 지운다(§4에서 다시 채움) — 안 지우면 ADD UNIQUE가 1062로 실패
DELETE FROM ref_hs_indicator WHERE indicator IN ('b2_nsn_count','b2_part_count','b2_row_count');
SET @has_pk = (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'ref_hs_indicator' AND COLUMN_NAME = 'period_key');
SET @q = IF(@has_pk = 0,
  "ALTER TABLE ref_hs_indicator
     ADD COLUMN period_key SMALLINT GENERATED ALWAYS AS (COALESCE(period_end, 0)) STORED
       COMMENT 'UNIQUE용. period_end NULL(시점 미상)은 UNIQUE에서 서로 다른 값으로 취급돼 중복을 못 막으므로 0으로 치환(ref_category_map.hs6_key와 같은 이유)' AFTER period_end,
     DROP INDEX ux_ind,
     ADD UNIQUE KEY ux_ind (hs6, indicator, period_key)",
  "SELECT 'period_key already exists, ALTER skipped' AS info");
PREPARE s2 FROM @q; EXECUTE s2; DEALLOCATE PREPARE s2;

-- §3 뷰 (정의는 db/schema.sql §6과 동일)
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

-- 조인 키는 raw의 fsc(군급분류) 열. nsn(재고번호)은 9자리 코드라 FSC를 담지 않는다. 고유 부품 = part_mgmt_no(v_review_list와 동일 기준).
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

-- §4 지표 채우기 (이 스크립트가 계산하는 지표는 삭제 후 재삽입 — 재실행 시 값 갱신, 중복 없음)
DELETE FROM ref_hs_indicator
 WHERE indicator IN ('mil_hs10_share','aero_hs10_share','auto_hs10_share','b2_nsn_count','b2_part_count','b2_row_count');

-- 4-1 관세청 HS10 용도 세분류 (군용전용 3 · 항공기용 7 · 자동차용 1 = 11행. 항공기용 세분류가 있으나 수입 0인 IC 3종도 0%로 기록)
INSERT INTO ref_hs_indicator (hs6, axis, indicator, value_num, numerator, denominator, unit, period_start, period_end, link_status, source, method, note)
SELECT u.hs6, 'civil_mix',
       CASE u.use_tag WHEN '군용전용' THEN 'mil_hs10_share' WHEN '항공기용' THEN 'aero_hs10_share' ELSE 'auto_hs10_share' END,
       u.share_pct, u.imp_dlr, u.imp_dlr_hs6, '%', u.period_start, u.period_end, '해당없음', 'customs_all',
       'v_hs10_use_share: SUM(imp_dlr of HS10 tagged by dim_hs10.name_ko REGEXP) / SUM(imp_dlr of hs6), 2021~2025 is_partial_year=0',
       CASE u.use_tag WHEN '군용전용' THEN '제9301호(군용 무기)·제9306호(폭탄·탄약) 전용 세분류. 신고자가 일반 코드로 신고 가능 → 하한선'
                      WHEN '항공기용' THEN '항공기용 세분류는 민항 포함 → 군수 비중 아님'
                      ELSE '자동차용 세분류' END
FROM v_hs10_use_share u
WHERE u.use_tag IN ('군용전용','항공기용','자동차용');

-- 4-2 B2 국산화개발품목 건수 (ref_category_map fsc4 후보 경유, 14개 HS6 × 2지표 = 28행)
INSERT INTO ref_hs_indicator (hs6, axis, indicator, value_num, numerator, denominator, unit, period_start, period_end, link_status, source, method, note)
SELECT b.hs6, 'defense_relevance', 'b2_part_count', b.b2_part_count, b.b2_part_count, NULL, '건', NULL, NULL, b.link_status, 'dapa_localized_item',
       CONCAT('v_defense_relevance_b2: COUNT(DISTINCT part_mgmt_no) of raw_dapa_localized_item WHERE fsc IN (', b.fsc4_list, ')'),
       'FSC→HS6 후보 대응(1:N). 같은 부품이 여러 HS6에 반복되므로 HS6 간 합산 금지. B2는 지상체계 한정·시점 미상 스냅샷'
FROM v_defense_relevance_b2 b;

INSERT INTO ref_hs_indicator (hs6, axis, indicator, value_num, numerator, denominator, unit, period_start, period_end, link_status, source, method, note)
SELECT b.hs6, 'defense_relevance', 'b2_row_count', b.b2_row_count, b.b2_row_count, NULL, '건', NULL, NULL, b.link_status, 'dapa_localized_item',
       CONCAT('v_defense_relevance_b2: COUNT(*) of raw_dapa_localized_item WHERE fsc IN (', b.fsc4_list, ')'),
       '사업×부품 행 수(같은 부품이 사업 수만큼 반복, 원본 완전 중복 8,940행 포함). 고유 부품 수는 b2_part_count'
FROM v_defense_relevance_b2 b;

-- §5 civil_mix 스냅샷 (21행 전부 규칙값으로 덮어씀. 팀 판단 값은 남기지 않는다)
UPDATE ref_hs_whitelist w
JOIN v_civil_mix_rule r ON r.hs6 = w.hs6
   SET w.civil_mix = r.civil_mix_rule,
       w.civil_mix_basis = r.civil_mix_basis,
       w.civil_mix_note = r.civil_mix_note;

-- §6 열 사전 동기화 (db/column_dict.csv 226행과 일치)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
  ('ref_hs_whitelist', 13, 'civil_mix', 'civil_mix', "ENUM('높음','중간','낮음')", '민수 혼합 정도 — v_civil_mix_rule 규칙 도출값(2026-09-16). 정량 지표 없으면 NULL. docs/reference/hs-whitelist-definition.md §7'),
  ('ref_hs_whitelist', 14, 'civil_mix_basis', 'civil_mix_basis', "ENUM('hs10','hsk','판단불가')", 'civil_mix를 정한 지표 종류(2026-09-16)'),
  ('ref_hs_whitelist', 15, 'civil_mix_note', 'civil_mix_note', 'VARCHAR(200)', '근거 수치 요약. 원값은 ref_hs_indicator'),
  ('raw_hsk_control', 1, 'hsk10', '품목번호', 'VARCHAR(12)', 'HSK 10자리'),
  ('raw_hsk_control', 2, 'name_ko', '품명(국문)', 'VARCHAR(300)', ''),
  ('raw_hsk_control', 3, 'name_en', '품명(영문)', 'VARCHAR(300)', ''),
  ('raw_hsk_control', 4, 'control_no', '통제번호', 'VARCHAR(30)', '전략물자 통제 리스트 번호')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §7 검증 (기대: 높음/hs10 3 · 중간/hs10 2 · 낮음/hs10 2 · NULL/판단불가 14 / 지표 39행 / meta_column_dict 226)
SELECT civil_mix, civil_mix_basis, COUNT(*) AS n FROM ref_hs_whitelist GROUP BY civil_mix, civil_mix_basis ORDER BY civil_mix, civil_mix_basis;
SELECT hs6, civil_mix, civil_mix_basis, civil_mix_note FROM ref_hs_whitelist WHERE civil_mix IS NOT NULL ORDER BY hs6;
SELECT indicator, COUNT(*) AS n FROM ref_hs_indicator GROUP BY indicator ORDER BY indicator;
SELECT COUNT(*) AS meta_column_dict_rows FROM meta_column_dict;
