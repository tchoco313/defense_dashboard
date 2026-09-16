-- =============================================================================
-- HS6 선정 규칙 도입: raw_hs_code_master · raw_hs_unit_name · 뷰 5개 · ref_hs_whitelist evidence 3열 · ref_hs_rule_flag(R1~R4 스냅샷) (작성 2026-09-16, 원본 3개 확보·헤더 반영 2026-09-16, 팀 서버 적용 — 미적용)
--
-- 근거: docs/reference/hs-whitelist-definition.md §8 (자료·법령·규칙 R1~R4), 계획 2026-09-16 "HS6 화이트리스트를 공식 자료 규칙으로 다시 도출"
-- 목적: "어떤 HS6를 관세청에서 수집할지"를 팀 판단이 아니라 관세청 HS부호 마스터(15049722)·전략물자 HSK 연계표(15034135)에
--       규칙을 적용해 도출하고, 현재 21개와 대조(v_hs6_candidate_vs_whitelist)한다. evidence 3열은 그 스냅샷.
-- 실행: DBHub는 readonly라 불가. docs/runbook/commands.md "DB 스키마 적용"과 같이 mariadb.exe + MYSQL_PWD 로:
--       mariadb.exe -h <서버IP> -u <계정> --protocol=TCP --skip-ssl-verify-server-cert --default-character-set=utf8mb4 --show-warnings --table defense_dashboard < db/alter_2026-09-16_hs_rule.sql
-- 재실행: 가능. ALTER는 information_schema 검사 후 건너뛰고, CREATE TABLE IF NOT EXISTS, 뷰는 OR REPLACE, 열 사전은 ON DUPLICATE KEY.
-- 순서: §1 ALTER → §2 CREATE TABLE 3 → §3 뷰 5 → §4 meta_column_dict → §5 evidence 스냅샷·강등·신규 3행(정적) + 5-4 규칙 플래그 스냅샷(원본 적재 후) → §6 검증
-- 선행: raw_hsk_control은 db/alter_2026-09-16_indicator.sql로 이미 있음. 원본 3개(15049722·15130660·15034135)는 2026-09-16 내려받아 헤더를 확인했고
--       scripts/load_db.py --raw --tables raw_hs_code_master raw_hs_unit_name raw_hsk_control 으로 적재한다.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4;
-- §5-4 INSERT…SELECT가 v_hsk_control_by_hs6의 GROUP_CONCAT(통제번호 목록)을 물질화하는데, MySQL 8.4 기본 group_concat_max_len=1024 + STRICT 모드에서는
-- 잘림이 오류 1260(Row … was cut by GROUP_CONCAT)이 된다(팀 서버 2026-09-16 실측, 665행째). 세션 한도를 올린다. SELECT만 하는 화면 조회는 잘려도 경고뿐.
SET SESSION group_concat_max_len = 65535;

-- §1 ref_hs_whitelist evidence 3열 (이미 있으면 건너뜀)
SET @has_col = (SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'ref_hs_whitelist' AND COLUMN_NAME = 'evidence_basis');
SET @q = IF(@has_col = 0,
  "ALTER TABLE ref_hs_whitelist
     MODIFY COLUMN evidence VARCHAR(120) NULL COMMENT '근거 키. 규칙 도출 후: HSK-군용;HSK-항공/항행;전략물자-ML;전략물자-DU;B2-FSC (v_hs6_candidate_rule.evidence_rule 스냅샷). 도출 전(09-15 팀 판단): A6;B2-FSC;KRIT;A7;팀판단 — docs/reference/hs-whitelist-definition.md §8',
     ADD COLUMN evidence_basis ENUM('rule','팀판단') NOT NULL DEFAULT '팀판단' COMMENT 'evidence를 정한 방식: rule=공식 자료(관세청 HSK 마스터·전략물자 HSK 연계표) 규칙 도출, 팀판단=09-15 기획 단계 판단 — 2026-09-16 추가' AFTER evidence,
     ADD COLUMN evidence_note VARCHAR(300) NULL COMMENT '규칙 근거 수치 요약(예: HSK10 11개 중 군용전용 1 / 통제 HSK 5개(ML 2) / B2 부품 27). 원값은 v_hs6_candidate_rule' AFTER evidence_basis,
     COMMENT = 'HS6 화이트리스트 21개 — 품목군 기준표(원본 17열: 8열 + 2026-09-15 정의 열 4개 + civil_mix 3열 + evidence_basis·evidence_note)'",
  "SELECT 'evidence_basis already exists, ALTER skipped' AS info");
PREPARE s1 FROM @q; EXECUTE s1; DEALLOCATE PREPARE s1;

-- §2 원본 테이블 (정의는 db/schema.sql과 동일하게 유지)
-- 2-0 raw_hsk_control 열 넓히기 (2026-09-16 내려받은 파일: 품명(영문) 최대 368자, 통제번호는 쉼표 목록 최대 1,218자 — VARCHAR(30)이면 1406 오류). 재실행 안전.
ALTER TABLE raw_hsk_control
  MODIFY COLUMN name_en    VARCHAR(400) NULL COMMENT '품명(영문, 최대 368자)',
  MODIFY COLUMN control_no TEXT         NULL COMMENT '통제번호 — 쉼표 목록(예 3A001.a.1.,5A002.), 최대 1,218자. 2026-09-16 확인: 별표2 이중용도만, ML 0건';


-- 관세청 HS부호 마스터 (data.go.kr 15049722 「관세청_HS부호_20260101」, XLSX 1시트, 2026-09-16 확보: 12,469행 = 10자리 11,327 + 7~9자리 호 수준 1,142, 전부 적용종료 2026-12-31).
-- 용도: HS6 선정 규칙(v_hs10_use_tag_all → v_hs6_candidate_rule). 현행(2026) 코드표라 과거 연도에만 있던 세분류(예 8542.31-4010 군용전용)는 없다 —
--       그 코드들은 수집된 dim_hs10(2016~2026 응답)에 남아 있어 뷰에서 UNION한다. 원본 열 20개 그대로(헤더 확인됨).
-- 법령 근거: 관세법 §84(품목분류체계) → 「관세·통계통합품목분류표」(기획재정부 고시)의 10단위 세분류.
CREATE TABLE IF NOT EXISTS raw_hs_code_master (
  row_id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  hs_code          VARCHAR(12)  NULL COMMENT 'HS부호(7~10자리)',
  apply_start      VARCHAR(20)  NULL COMMENT '적용시작일자',
  apply_end        VARCHAR(20)  NULL COMMENT '적용종료일자',
  name_ko          VARCHAR(500) NULL COMMENT '한글품목명(최대 459자)',
  name_en          VARCHAR(600) NULL COMMENT '영문품목명(최대 519자)',
  hs_desc          VARCHAR(500) NULL COMMENT 'HS부호내용(전부 빈값)',
  ksic_trade_nm    VARCHAR(50)  NULL COMMENT '한국표준무역분류명',
  qty_unit_max     VARCHAR(10)  NULL COMMENT '수량단위최대단가',
  wt_unit_max      VARCHAR(10)  NULL COMMENT '중량단위최대단가',
  qty_unit_cd      VARCHAR(10)  NULL COMMENT '수량단위코드',
  wt_unit_cd       VARCHAR(10)  NULL COMMENT '중량단위코드',
  exp_nature_cd    VARCHAR(10)  NULL COMMENT '수출성질코드',
  imp_nature_cd    VARCHAR(10)  NULL COMMENT '수입성질코드',
  spec_item_nm     VARCHAR(50)  NULL COMMENT '품목규격명',
  spec_required    VARCHAR(200) NULL COMMENT '필수규격명',
  spec_reference   VARCHAR(100) NULL COMMENT '참고규격명',
  spec_desc        TEXT         NULL COMMENT '규격설명(최대 549자)',
  spec_detail      TEXT         NULL COMMENT '규격사항내용(최대 574자)',
  nature_class_cd  VARCHAR(10)  NULL COMMENT '성질통합분류코드',
  nature_class_nm  VARCHAR(100) NULL COMMENT '성질통합분류코드명',
  source_file      VARCHAR(100) NOT NULL,
  source_row_no    INT UNSIGNED NULL,
  loaded_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_hcm_code (hs_code)
) ENGINE=InnoDB COMMENT='관세청 HS부호 마스터 원본(15049722, 2026-01-01 기준 HSK 전체 12,469행). 2026-09-16 확보';

-- 관세청 HS부호 단위별 품목명 (data.go.kr 15130660, XLSX 5시트 HS2단위 97 · HS4단위 1,228 · HS6단위(5단위포함) 3,278 · HS8단위(7,9단위포함) 1,142 · HS10단위 11,327 = 17,072행).
-- 시트마다 첫 열 이름이 다르므로(HS2단위·HS4단위·…) load_db.py special='hs_unit'이 5시트를 세로로 합치고 hs_unit에 시트 단위를 넣는다.
-- 용도: 규칙 후보 HS6의 공식 명칭(v_hs6_candidate_rule.hs6_name_ko) + HS6 명칭 자체의 용도 키워드(레이더·항행 등) 판정.
CREATE TABLE IF NOT EXISTS raw_hs_unit_name (
  row_id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  hs_code        VARCHAR(12)  NULL COMMENT '시트 첫 열(HS2단위/HS4단위/HS6단위/HS8단위/HS10단위)',
  hs_unit        CHAR(2)      NOT NULL COMMENT '시트 단위 02/04/06/08/10 (6시트는 5자리, 8시트는 7·9자리 포함)',
  name_ko        VARCHAR(700) NULL COMMENT '한글품목명(최대 603자, HS6 시트)',
  name_en        VARCHAR(800) NULL COMMENT '영문품목명(최대 745자, HS6 시트)',
  source_file    VARCHAR(100) NOT NULL,
  source_row_no  INT UNSIGNED NULL COMMENT '시트 안 행 번호',
  loaded_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_hun_code (hs_code)
) ENGINE=InnoDB COMMENT='관세청 HS부호 단위별 품목명 원본(15130660, 5시트 17,072행). 2026-09-16 확보';


-- HS6 규칙 판정 스냅샷 (2026-09-16 팀 회의: "R1~R4를 전부 만들어 두고, 해외 수입 의존도 시각화 때 DB에서 가져와 주피터에서 정제한 뒤 쓸지 정한다").
--   한 행 = HS6(84·85·88·90류, 마스터·dim_hs10·연계표에 등장하는 것 전부) × rule_version. v_hs6_candidate_rule을 그대로 물질화한 것이라
--   원본 3개(raw_hs_code_master·raw_hs_unit_name·raw_hsk_control)가 없는 DB에서도 읽을 수 있다. 채우기: db/alter_2026-09-16_hs_rule.sql §5-4(삭제 후 재삽입).
--   진입 규칙(어느 R가 화이트리스트 진입을 결정하는지)은 팀이 시각화 단계에서 확정 — is_candidate_provisional은 잠정식 R1 OR R2 OR (R3∧R4)의 참고값.
--   노트북: SELECT * FROM ref_hs_rule_flag WHERE rule_version = '2026-09-16';
CREATE TABLE IF NOT EXISTS ref_hs_rule_flag (
  hs6                       CHAR(6)       NOT NULL,
  rule_version              VARCHAR(20)   NOT NULL COMMENT '규칙 정의 버전(docs/reference/hs-whitelist-definition.md §8-2 날짜)',
  hs2                       CHAR(2)       NOT NULL,
  hs6_name_ko               VARCHAR(700)  NULL COMMENT '관세청 HS6 공식 명칭(raw_hs_unit_name 06단위). 없으면 NULL',
  r1_mil                    TINYINT(1)    NOT NULL COMMENT 'R1 군용전용 HSK 세분류(제9301호ㆍ제9306호 전용) 존재',
  r2_aero_nav               TINYINT(1)    NOT NULL COMMENT 'R2 항공기용·항행·레이더·무인기 HSK 세분류 또는 HS6 명칭 용도어 존재',
  r3_du                     TINYINT(1)    NOT NULL COMMENT 'R3 전략물자 이중용도(별표2) 3·5·6·7부 통제 HSK 존재',
  r3_ml                     TINYINT(1)    NOT NULL COMMENT 'R3 전략물자 군용물자(별표3 ML) 통제 HSK 존재 — 현재 자료(15034135)에 ML 0건이라 항상 0, 별표3 연계 자료 확보 시 채움',
  r4_b2                     TINYINT(1)    NOT NULL COMMENT 'R4 B2 국산화개발품목 FSC 후보 대응 존재(b2_part_count > 0)',
  mil_cnt                   SMALLINT      NOT NULL,
  aero_cnt                  SMALLINT      NOT NULL,
  uav_cnt                   SMALLINT      NOT NULL,
  radar_cnt                 SMALLINT      NOT NULL,
  nav_cnt                   SMALLINT      NOT NULL,
  hs10_total                SMALLINT      NOT NULL COMMENT '현행 마스터 HSK10 + dim_hs10 이력 코드',
  hs10_master               SMALLINT      NOT NULL COMMENT '현행(2026) 마스터 HSK10 수',
  control_hsk10_count       SMALLINT      NOT NULL COMMENT '연계표에 있는 HSK10 수(부 무관)',
  du_elec_hsk10_count       SMALLINT      NOT NULL COMMENT '그중 3·5·6·7부 통제번호가 있는 HSK10 수',
  ml_hsk10_count            SMALLINT      NOT NULL,
  control_ratio_pct         DECIMAL(5,1)  NULL COMMENT 'control_hsk10_count / hs10_master × 100',
  control_no_list           TEXT          NULL COMMENT '통제번호 목록(; 구분, 원본은 쉼표 목록)',
  b2_part_count             INT           NULL COMMENT 'B2 고유 부품 수(FSC 후보 대응 경유, HS6 간 합산 금지). NULL = 대응 없음',
  is_candidate_provisional  TINYINT(1)    NOT NULL COMMENT '잠정 진입식 R1 OR R2 OR (R3_du AND R4) — 팀 확정 전 참고값',
  priority_rule             TINYINT       NULL COMMENT '잠정 우선순위 제안 1/2/3',
  evidence_rule             VARCHAR(120)  NULL,
  evidence_note             VARCHAR(300)  NULL,
  in_whitelist              TINYINT(1)    NOT NULL COMMENT '스냅샷 시점에 ref_hs_whitelist에 있었는지',
  computed_at               DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  source_note               VARCHAR(300)  NULL COMMENT '원본 dataset_key·한계(마스터는 2026 현행, dim_hs10 이력 코드 UNION, 연계표는 별표2만)',
  PRIMARY KEY (hs6, rule_version),
  KEY ix_hrf_flags (rule_version, r1_mil, r2_aero_nav, r3_du, r4_b2),
  KEY ix_hrf_hs2 (hs2)
) ENGINE=InnoDB COMMENT='HS6별 선정 규칙 R1~R4 판정·근거 수치 스냅샷(84·85·88·90류 전체). 진입 규칙 확정은 시각화 단계로 이연';

-- §3 뷰 5개 (정의는 db/schema.sql §6과 동일)

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

-- §4 열 사전 동기화 (db/column_dict.csv 와 일치. 원본 열명은 2026-09-16 내려받은 파일 헤더로 확인)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
  ('ref_hs_whitelist', 16, 'evidence_basis', 'evidence_basis', "ENUM('rule','팀판단')", 'evidence를 정한 방식(2026-09-16): rule=공식 자료 규칙 도출 / 팀판단=09-15 기획 단계'),
  ('ref_hs_whitelist', 17, 'evidence_note', 'evidence_note', 'VARCHAR(300)', '규칙 근거 수치 요약. 원값은 v_hs6_candidate_rule'),
  ('raw_hs_code_master', 1, 'hs_code', 'HS부호', 'VARCHAR(12)', '7~10자리'),
  ('raw_hs_code_master', 2, 'apply_start', '적용시작일자', 'VARCHAR(20)', ''),
  ('raw_hs_code_master', 3, 'apply_end', '적용종료일자', 'VARCHAR(20)', ''),
  ('raw_hs_code_master', 4, 'name_ko', '한글품목명', 'VARCHAR(500)', ''),
  ('raw_hs_code_master', 5, 'name_en', '영문품목명', 'VARCHAR(600)', ''),
  ('raw_hs_code_master', 6, 'hs_desc', 'HS부호내용', 'VARCHAR(500)', '전부 빈값'),
  ('raw_hs_code_master', 7, 'ksic_trade_nm', '한국표준무역분류명', 'VARCHAR(50)', ''),
  ('raw_hs_code_master', 8, 'qty_unit_max', '수량단위최대단가', 'VARCHAR(10)', ''),
  ('raw_hs_code_master', 9, 'wt_unit_max', '중량단위최대단가', 'VARCHAR(10)', ''),
  ('raw_hs_code_master', 10, 'qty_unit_cd', '수량단위코드', 'VARCHAR(10)', ''),
  ('raw_hs_code_master', 11, 'wt_unit_cd', '중량단위코드', 'VARCHAR(10)', ''),
  ('raw_hs_code_master', 12, 'exp_nature_cd', '수출성질코드', 'VARCHAR(10)', ''),
  ('raw_hs_code_master', 13, 'imp_nature_cd', '수입성질코드', 'VARCHAR(10)', ''),
  ('raw_hs_code_master', 14, 'spec_item_nm', '품목규격명', 'VARCHAR(50)', ''),
  ('raw_hs_code_master', 15, 'spec_required', '필수규격명', 'VARCHAR(200)', ''),
  ('raw_hs_code_master', 16, 'spec_reference', '참고규격명', 'VARCHAR(100)', ''),
  ('raw_hs_code_master', 17, 'spec_desc', '규격설명', 'TEXT', ''),
  ('raw_hs_code_master', 18, 'spec_detail', '규격사항내용', 'TEXT', ''),
  ('raw_hs_code_master', 19, 'nature_class_cd', '성질통합분류코드', 'VARCHAR(10)', ''),
  ('raw_hs_code_master', 20, 'nature_class_nm', '성질통합분류코드명', 'VARCHAR(100)', ''),
  ('raw_hs_unit_name', 1, 'hs_code', '(시트 첫 열 HS2단위/HS4단위/HS6단위/HS8단위/HS10단위)', 'VARCHAR(12)', '5시트 세로 결합'),
  ('raw_hs_unit_name', 2, 'hs_unit', '(시트 이름)', 'CHAR(2)', '02/04/06/08/10'),
  ('raw_hs_unit_name', 3, 'name_ko', '한글품목명', 'VARCHAR(700)', '최대 603자'),
  ('raw_hs_unit_name', 4, 'name_en', '영문품목명', 'VARCHAR(800)', '최대 745자')
  ,('raw_hsk_control', 3, 'name_en', '품명(영문)', 'VARCHAR(400)', '최대 368자')
  ,('raw_hsk_control', 4, 'control_no', '통제번호', 'TEXT', '전략물자 통제번호 쉼표 목록(별표2 이중용도, ML 없음)')
  ,('ref_hs_rule_flag', 1, 'hs6', 'hs6', 'CHAR(6)', 'PK1')
  ,('ref_hs_rule_flag', 2, 'rule_version', 'rule_version', 'VARCHAR(20)', 'PK2, 규칙 정의 버전')
  ,('ref_hs_rule_flag', 3, 'hs2', 'hs2', 'CHAR(2)', '')
  ,('ref_hs_rule_flag', 4, 'hs6_name_ko', 'hs6_name_ko', 'VARCHAR(700)', '관세청 HS6 공식 명칭')
  ,('ref_hs_rule_flag', 5, 'r1_mil', 'r1_mil', 'TINYINT(1)', 'R1 군용전용 세분류')
  ,('ref_hs_rule_flag', 6, 'r2_aero_nav', 'r2_aero_nav', 'TINYINT(1)', 'R2 항공·항행·레이더·무인기')
  ,('ref_hs_rule_flag', 7, 'r3_du', 'r3_du', 'TINYINT(1)', 'R3 이중용도 3·5·6·7부')
  ,('ref_hs_rule_flag', 8, 'r3_ml', 'r3_ml', 'TINYINT(1)', 'R3 군용물자 ML(현재 자료 0건)')
  ,('ref_hs_rule_flag', 9, 'r4_b2', 'r4_b2', 'TINYINT(1)', 'R4 B2 FSC 후보 대응')
  ,('ref_hs_rule_flag', 10, 'mil_cnt', 'mil_cnt', 'SMALLINT', '')
  ,('ref_hs_rule_flag', 11, 'aero_cnt', 'aero_cnt', 'SMALLINT', '')
  ,('ref_hs_rule_flag', 12, 'uav_cnt', 'uav_cnt', 'SMALLINT', '')
  ,('ref_hs_rule_flag', 13, 'radar_cnt', 'radar_cnt', 'SMALLINT', '')
  ,('ref_hs_rule_flag', 14, 'nav_cnt', 'nav_cnt', 'SMALLINT', '')
  ,('ref_hs_rule_flag', 15, 'hs10_total', 'hs10_total', 'SMALLINT', '현행+이력')
  ,('ref_hs_rule_flag', 16, 'hs10_master', 'hs10_master', 'SMALLINT', '현행 2026')
  ,('ref_hs_rule_flag', 17, 'control_hsk10_count', 'control_hsk10_count', 'SMALLINT', '')
  ,('ref_hs_rule_flag', 18, 'du_elec_hsk10_count', 'du_elec_hsk10_count', 'SMALLINT', '')
  ,('ref_hs_rule_flag', 19, 'ml_hsk10_count', 'ml_hsk10_count', 'SMALLINT', '')
  ,('ref_hs_rule_flag', 20, 'control_ratio_pct', 'control_ratio_pct', 'DECIMAL(5,1)', '')
  ,('ref_hs_rule_flag', 21, 'control_no_list', 'control_no_list', 'TEXT', '')
  ,('ref_hs_rule_flag', 22, 'b2_part_count', 'b2_part_count', 'INT', 'NULL=대응 없음')
  ,('ref_hs_rule_flag', 23, 'is_candidate_provisional', 'is_candidate_provisional', 'TINYINT(1)', '잠정 진입식 R1 OR R2 OR (R3_du AND R4)')
  ,('ref_hs_rule_flag', 24, 'priority_rule', 'priority_rule', 'TINYINT', '')
  ,('ref_hs_rule_flag', 25, 'evidence_rule', 'evidence_rule', 'VARCHAR(120)', '')
  ,('ref_hs_rule_flag', 26, 'evidence_note', 'evidence_note', 'VARCHAR(300)', '')
  ,('ref_hs_rule_flag', 27, 'in_whitelist', 'in_whitelist', 'TINYINT(1)', '')
  ,('ref_hs_rule_flag', 28, 'computed_at', 'computed_at', 'DATETIME', '')
  ,('ref_hs_rule_flag', 29, 'source_note', 'source_note', 'VARCHAR(300)', '')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §5 evidence 스냅샷 + 강등 + 신규 3행 (2026-09-16 사용자 결정 '권장안'. 값은 로컬 스크래치 DB의 v_hs6_candidate_rule 결과를 그대로 옮긴 정적 문장이라
--    원본 3개를 적재하기 전에 실행해도 같은 결과. 적재 후 `SELECT * FROM v_hs6_candidate_vs_whitelist`로 재확인. data/reference/hs_whitelist.csv 와 동일.)
-- 5-1 규칙 해당 16개: evidence 3열 교체(priority는 팀 값 유지)
UPDATE ref_hs_whitelist SET evidence = 'HSK-항공/항행', evidence_basis = 'rule', evidence_note = 'HSK10 2개(현행 2) 중 군용전용 0·항공 1·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 2개(현행 대비 100%, 3·5·6·7부 0)' WHERE hs6 = '841191';
UPDATE ref_hs_whitelist SET evidence = '전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 3개(현행 3) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 3개(현행 대비 100%, 3·5·6·7부 3) / B2 부품 60(후보 대응)' WHERE hs6 = '852560';
UPDATE ref_hs_whitelist SET evidence = 'HSK-항공/항행;전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 2개(현행 2) 중 군용전용 0·항공 1·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 2개(현행 대비 100%, 3·5·6·7부 2) / B2 부품 4(후보 대응)' WHERE hs6 = '852610';
UPDATE ref_hs_whitelist SET evidence = 'HSK-항공/항행;전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 11개(현행 11) 중 군용전용 0·항공 4·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 11개(현행 대비 100%, 3·5·6·7부 11) / B2 부품 1(후보 대응)' WHERE hs6 = '852691';
UPDATE ref_hs_whitelist SET evidence = '전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 1개(현행 1) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 1개(현행 대비 100%, 3·5·6·7부 1) / B2 부품 41(후보 대응)' WHERE hs6 = '852692';
UPDATE ref_hs_whitelist SET evidence = 'HSK-항공/항행;전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 28개(현행 10) 중 군용전용 0·항공 0·무인기 0·레이더 1·항행 1 / 이중용도 통제 HSK 4개(현행 대비 40%, 3·5·6·7부 4) / B2 부품 53(후보 대응)' WHERE hs6 = '852990';
UPDATE ref_hs_whitelist SET evidence = '전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 2개(현행 2) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 1개(현행 대비 50%, 3·5·6·7부 1) / B2 부품 15(후보 대응)' WHERE hs6 = '854110';
UPDATE ref_hs_whitelist SET evidence = '전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 2개(현행 2) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 2개(현행 대비 100%, 3·5·6·7부 2) / B2 부품 15(후보 대응)' WHERE hs6 = '854121';
UPDATE ref_hs_whitelist SET evidence = '전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 2개(현행 2) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 2개(현행 대비 100%, 3·5·6·7부 2) / B2 부품 15(후보 대응)' WHERE hs6 = '854129';
UPDATE ref_hs_whitelist SET evidence = 'HSK-군용;HSK-항공/항행;전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 11개(현행 4) 중 군용전용 1·항공 1·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 4개(현행 대비 100%, 3·5·6·7부 4) / B2 부품 27(후보 대응)' WHERE hs6 = '854231';
UPDATE ref_hs_whitelist SET evidence = 'HSK-군용;HSK-항공/항행;전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 11개(현행 4) 중 군용전용 1·항공 1·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 4개(현행 대비 100%, 3·5·6·7부 4) / B2 부품 27(후보 대응)' WHERE hs6 = '854233';
UPDATE ref_hs_whitelist SET evidence = 'HSK-군용;HSK-항공/항행;전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 11개(현행 4) 중 군용전용 1·항공 1·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 4개(현행 대비 100%, 3·5·6·7부 4) / B2 부품 27(후보 대응)' WHERE hs6 = '854239';
UPDATE ref_hs_whitelist SET evidence = 'HSK-항공/항행;전략물자-DU', evidence_basis = 'rule', evidence_note = 'HSK10 3개(현행 3) 중 군용전용 0·항공 0·무인기 1·레이더 0·항행 0 / 이중용도 통제 HSK 3개(현행 대비 100%, 3·5·6·7부 1)' WHERE hs6 = '880730';
UPDATE ref_hs_whitelist SET evidence = '전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 12개(현행 3) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 1개(현행 대비 33%, 3·5·6·7부 1) / B2 부품 18(후보 대응)' WHERE hs6 = '901380';
UPDATE ref_hs_whitelist SET evidence = 'HSK-항공/항행;전략물자-DU', evidence_basis = 'rule', evidence_note = 'HSK10 1개(현행 1) 중 군용전용 0·항공 1·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 1개(현행 대비 100%, 3·5·6·7부 1)' WHERE hs6 = '901420';
UPDATE ref_hs_whitelist SET evidence = 'HSK-항공/항행;전략물자-DU;B2-FSC', evidence_basis = 'rule', evidence_note = 'HSK10 3개(현행 2) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 1 / 이중용도 통제 HSK 2개(현행 대비 100%, 3·5·6·7부 2) / B2 부품 1(후보 대응)' WHERE hs6 = '901480';
-- 5-2 규칙 미해당 5개: priority 3 강등, evidence(09-15 팀 판단 키)는 그대로, basis '팀판단'
UPDATE ref_hs_whitelist SET priority = 3, evidence_basis = '팀판단', evidence_note = '규칙 미해당(2026-09-16): 관세청 HSK 용도 세분류 없음, 전략물자 이중용도+B2 대응 동시 충족 안 함 → 09-15 팀 판단 근거만 있음. priority 3으로 강등, 화면 ''근거 미확인'' / HSK10 4개(현행 3) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 2개(현행 대비 67%, 3·5·6·7부 2)' WHERE hs6 = '847180';
UPDATE ref_hs_whitelist SET priority = 3, evidence_basis = '팀판단', evidence_note = '규칙 미해당(2026-09-16): 관세청 HSK 용도 세분류 없음, 전략물자 이중용도+B2 대응 동시 충족 안 함 → 09-15 팀 판단 근거만 있음. priority 3으로 강등, 화면 ''근거 미확인'' / HSK10 41개(현행 25) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 18개(현행 대비 72%, 3·5·6·7부 11)' WHERE hs6 = '848620';
UPDATE ref_hs_whitelist SET priority = 3, evidence_basis = '팀판단', evidence_note = '규칙 미해당(2026-09-16): 관세청 HSK 용도 세분류 없음, 전략물자 이중용도+B2 대응 동시 충족 안 함 → 09-15 팀 판단 근거만 있음. priority 3으로 강등, 화면 ''근거 미확인'' / HSK10 44개(현행 9) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 9개(현행 대비 100%, 3·5·6·7부 8)' WHERE hs6 = '851762';
UPDATE ref_hs_whitelist SET priority = 3, evidence_basis = '팀판단', evidence_note = '규칙 미해당(2026-09-16): 관세청 HSK 용도 세분류 없음, 전략물자 이중용도+B2 대응 동시 충족 안 함 → 09-15 팀 판단 근거만 있음. priority 3으로 강등, 화면 ''근거 미확인'' / HSK10 1개(현행 1) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 0개(현행 대비 0%, 3·5·6·7부 0)' WHERE hs6 = '854142';
UPDATE ref_hs_whitelist SET priority = 3, evidence_basis = '팀판단', evidence_note = '규칙 미해당(2026-09-16): 관세청 HSK 용도 세분류 없음, 전략물자 이중용도+B2 대응 동시 충족 안 함 → 09-15 팀 판단 근거만 있음. priority 3으로 강등, 화면 ''근거 미확인'' / HSK10 2개(현행 2) 중 군용전용 0·항공 0·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 0개(현행 대비 0%, 3·5·6·7부 0) / B2 부품 15(후보 대응)' WHERE hs6 = '854159';
-- 5-3 신규 3개(관세청 미수집 — fetch_customs.py --all-countries --hs 852910 901410 901490 후 --raw/--fact). 이미 있으면 건너뜀
INSERT INTO ref_hs_whitelist (hs6, hs_level, category, name_ko, name_en, rationale, priority, axis, system_family, defense_use_ko, related_fsc, evidence, evidence_basis, evidence_note, civil_mix, civil_mix_basis, civil_mix_note)
SELECT '852910', 6, '전자부품', '안테나·반사식 안테나와 그 부분품', 'Aerials and aerial reflectors of all kinds; parts', '레이더·통신 안테나. 2026-09-16 HS6 선정 규칙 R2(HS10 세분류 ''레이더기기용''·''항행용 무선기기용'')+전략물자 5·6부로 추가', 2, 'both', '통신·레이더 부분품', '레이더·전술통신·데이터링크의 안테나·반사기·급전 부분품(팀 판단)', NULL, 'HSK-항공/항행;전략물자-DU', 'rule', 'HSK10 4개(현행 4) 중 군용전용 0·항공 0·무인기 0·레이더 1·항행 1 / 이중용도 통제 HSK 4개(현행 대비 100%, 3·5·6·7부 4)', NULL, '판단불가', '미수집 — 관세청 수집·적재 후 v_hs10_use_share로 계산'
WHERE NOT EXISTS (SELECT 1 FROM ref_hs_whitelist WHERE hs6 = '852910');
INSERT INTO ref_hs_whitelist (hs6, hs_level, category, name_ko, name_en, rationale, priority, axis, system_family, defense_use_ko, related_fsc, evidence, evidence_basis, evidence_note, civil_mix, civil_mix_basis, civil_mix_note)
SELECT '901410', 6, '전자부품', '방향탐지용 컴퍼스', 'Direction finding compasses', '항법 계열. 2026-09-16 규칙 R2(HS10 항공기용 세분류 2개)+전략물자 7부로 추가', 2, 'import', '항법', '항공기·함정·차량 항법용 자기·자이로 컴퍼스(팀 판단)', NULL, 'HSK-항공/항행;전략물자-DU', 'rule', 'HSK10 5개(현행 5) 중 군용전용 0·항공 2·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 5개(현행 대비 100%, 3·5·6·7부 5)', NULL, '판단불가', '미수집 — 관세청 수집·적재 후 v_hs10_use_share로 계산'
WHERE NOT EXISTS (SELECT 1 FROM ref_hs_whitelist WHERE hs6 = '901410');
INSERT INTO ref_hs_whitelist (hs6, hs_level, category, name_ko, name_en, rationale, priority, axis, system_family, defense_use_ko, related_fsc, evidence, evidence_basis, evidence_note, civil_mix, civil_mix_basis, civil_mix_note)
SELECT '901490', 6, '전자부품', '항행용 기기 부분품·부속품', 'Parts and accessories of navigational instruments', '항법 계열. 2026-09-16 규칙 R2(HS10 항공기용 세분류)+전략물자 6·7부로 추가', 2, 'import', '항법', '항법 기기(9014 계열)의 부분품(팀 판단)', NULL, 'HSK-항공/항행;전략물자-DU', 'rule', 'HSK10 2개(현행 2) 중 군용전용 0·항공 1·무인기 0·레이더 0·항행 0 / 이중용도 통제 HSK 2개(현행 대비 100%, 3·5·6·7부 2)', NULL, '판단불가', '미수집 — 관세청 수집·적재 후 v_hs10_use_share로 계산'
WHERE NOT EXISTS (SELECT 1 FROM ref_hs_whitelist WHERE hs6 = '901490');

-- 5-4 R1~R4 규칙 판정 스냅샷 (2026-09-16 팀 회의: 규칙은 전부 저장, 진입 규칙 확정은 시각화 단계로 이연). 삭제 후 재삽입 — 재실행 시 값 갱신.
--     원본 3개(raw_hs_code_master·raw_hs_unit_name·raw_hsk_control)와 dim_hs10·raw_dapa_localized_item이 적재된 뒤 실행해야 값이 들어간다(미적재면 0행).
DELETE FROM ref_hs_rule_flag WHERE rule_version = '2026-09-16';
INSERT INTO ref_hs_rule_flag
  (hs6, rule_version, hs2, hs6_name_ko, r1_mil, r2_aero_nav, r3_du, r3_ml, r4_b2,
   mil_cnt, aero_cnt, uav_cnt, radar_cnt, nav_cnt, hs10_total, hs10_master,
   control_hsk10_count, du_elec_hsk10_count, ml_hsk10_count, control_ratio_pct, control_no_list, b2_part_count,
   is_candidate_provisional, priority_rule, evidence_rule, evidence_note, in_whitelist, source_note)
SELECT c.hs6, '2026-09-16', c.hs2, c.hs6_name_ko,
       c.r1_mil, c.r2_aero_nav, (c.du_elec_hsk10_count > 0), (c.ml_hsk10_count > 0), c.r4_b2,
       c.mil_cnt, c.aero_cnt, c.uav_cnt, c.radar_cnt, c.nav_cnt, c.hs10_total, c.hs10_master,
       c.control_hsk10_count, c.du_elec_hsk10_count, c.ml_hsk10_count, c.control_ratio_pct, c.control_no_list, c.b2_part_count,
       c.is_candidate, c.priority_rule, c.evidence_rule, c.evidence_note, (w.hs6 IS NOT NULL),
       'customs_hs_code_master(2026 현행) ∪ dim_hs10 이력 코드 / customs_hs_unit_name / kosti_hsk_control(별표2 이중용도만, ML 0건) / dapa_localized_item(FSC 후보 대응)'
FROM v_hs6_candidate_rule c
LEFT JOIN ref_hs_whitelist w ON w.hs6 = c.hs6;

-- §6 검증 (기대: evidence_basis rule 19 · 팀판단 5 = 24행 / priority 3 = 847180·848620·851762·854142·854159 / 뷰 5개 / meta_column_dict 281 /
--    ref_hs_rule_flag 원본 적재 후 약 500행: r1 3 · r3_ml 0 · r4 13 · in_whitelist 24, 미적재면 0행)
SELECT evidence_basis, COUNT(*) AS n FROM ref_hs_whitelist GROUP BY evidence_basis;
SELECT hs6, priority, evidence, evidence_basis FROM ref_hs_whitelist ORDER BY evidence_basis, priority, hs6;
SELECT (SELECT COUNT(*) FROM raw_hs_code_master) AS hs_code_master_rows, (SELECT COUNT(*) FROM raw_hs_unit_name) AS hs_unit_name_rows, (SELECT COUNT(*) FROM raw_hsk_control) AS hsk_control_rows;
SELECT TABLE_NAME FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME IN ('v_hs10_use_tag_all','v_hsk_control_by_hs6','v_hs6_candidate_rule','v_hs6_candidate_vs_whitelist','v_hs_whitelist_rule') ORDER BY TABLE_NAME;
SELECT COUNT(*) AS rule_flag_rows, SUM(r1_mil) AS r1, SUM(r2_aero_nav) AS r2, SUM(r3_du) AS r3_du, SUM(r3_ml) AS r3_ml, SUM(r4_b2) AS r4, SUM(in_whitelist) AS in_wl, SUM(is_candidate_provisional) AS cand FROM ref_hs_rule_flag WHERE rule_version = '2026-09-16';
SELECT COUNT(*) AS meta_column_dict_rows FROM meta_column_dict;
-- 적재 후: SELECT verdict, COUNT(*) FROM v_hs6_candidate_vs_whitelist GROUP BY verdict;  SELECT * FROM v_hs6_candidate_vs_whitelist ORDER BY verdict, hs6;
