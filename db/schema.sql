-- =============================================================================
-- defense_dashboard 스키마 DDL  (작성 2026-09-15, 리뷰 반영 2026-09-15, 교수 피드백 반영 2026-09-15 A7 국외조달 5테이블, 2026-09-16 정량 지표 ref_hs_indicator·raw_hsk_control·뷰 3, 2026-09-16 HS6 선정 규칙 raw_hs_code_master·raw_hs_unit_name·뷰 4·evidence 2열·ref_hs_rule_flag·v_hs_whitelist_rule, 설계 문서: docs/db/schema-design.md)
--
-- 대상: MariaDB 10.4+ / MySQL 8.0.16+ 양쪽에서 실행되는 문법만 사용
--       (팀 서버 실측 VERSION()=8.4.11, 로컬 검증 MariaDB 12.2)
-- 실행: mysql -h <서버IP> -u <계정> -p --default-character-set=utf8mb4 < db/schema.sql
-- 용도: 최초 구축 · 빈 개발 DB 초기화 전용. 아래 DROP이 수작업 대응표(ref_category_map·ref_sido_map)와
--       meta_ 기록까지 전부 지우므로 데이터가 들어간 DB에는 재실행하지 않는다.
--       데이터만 비우고 다시 적재할 때는 db/reset_data.sql(ref_·meta_dataset·meta_column_dict 보존) 사용.
-- 순서: 0 DB → 1 ref_ → 2 raw_ → 3 meta_ → 4 dim_/fact_ → 5 clean_ → 6 v_ 뷰
--
-- 원칙
--   raw_*  : CSV 원본 보존. 전 열 문자열, PK는 대리키 row_id 뿐. 업무키 UNIQUE는 어느 raw 테이블에도 없다
--            (원본 중복·갱신본 재수집 행 그대로 보존, 파일·행 위치는 source_file·source_row_no로 추적).
--            적재 후 UPDATE/DELETE 금지. 열명은 db/column_dict.csv(원본 한글 열명 ↔ 영문) 기준.
--   clean_*: 정제 결과(형 변환·정규화·분류 속성). 값은 사용자 정제 노트북이 채운다.
--   fact_/dim_: 관세청 원본에서 규칙이 확정된 형 변환만 수행(총계행 제외·연월 파싱·HS6 파생).
--   v_*    : 집계 뷰. 시나리오(제한률) 값은 DB에 저장하지 않고 화면에서 계산한다.
--   meta_* : 출처 기록·단계별 건수·열 사전. 보고서 표를 SELECT로 뽑기 위한 것.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS defense_dashboard
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE defense_dashboard;

-- -----------------------------------------------------------------------------
-- 안전장치 (2026-09-15 추가): 이미 데이터가 적재된 DB에서 이 파일을 실행하면 아래 DROP 전에 오류로 중단된다.
--   2026-09-15 15:12 팀 서버에서 이 파일이 다시 실행되어 적재 데이터 65만 행이 전부 지워진 사고 이후 추가.
--   (ERD 도구에 "Import"할 때는 서버에 연결하지 말고 파일만 읽히거나, 빈 로컬 DB를 쓴다.)
--   정말 초기화하려면 ① 먼저 덤프(mysqldump)를 뜨고 ② 이 블록(SET @has_tbl … DEALLOCATE PREPARE guard2;)을 지운 뒤 실행한다.
--   중단 시 메시지: ERROR 1146 Table 'stop_schema_sql_db_has_data_remove_guard_to_force_reset' doesn't exist
-- -----------------------------------------------------------------------------
SET @has_tbl = (SELECT COUNT(*) FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'raw_customs_trade');
SET @q = IF(@has_tbl = 1, 'SELECT COUNT(*) INTO @loaded_rows FROM defense_dashboard.raw_customs_trade', 'SET @loaded_rows = 0');
PREPARE guard1 FROM @q; EXECUTE guard1; DEALLOCATE PREPARE guard1;
SET @q = IF(@loaded_rows > 0,
            'SELECT 1 FROM `STOP_schema_sql_DB_has_data_remove_guard_to_force_reset`',
            'SELECT ''schema.sql guard: DB is empty, continuing'' AS guard');
PREPARE guard2 FROM @q; EXECUTE guard2; DEALLOCATE PREPARE guard2;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 재실행 가능하도록 역순 DROP (뷰 → clean/fact → meta → raw → ref)
DROP VIEW IF EXISTS v_hs_whitelist_rule, v_hs6_candidate_vs_whitelist, v_hs6_candidate_rule, v_hsk_control_by_hs6, v_hs10_use_tag_all,
  v_civil_mix_rule, v_defense_relevance_b2, v_hs10_use_share,
  v_overseas_plan_yearly, v_contract_monthly, v_review_list, v_hhi_hs6_year, v_import_share_hs6_year, v_import_hs6_year;
DROP TABLE IF EXISTS clean_dapa_overseas_plan, clean_company_name_link, clean_company, clean_krit_task, clean_dapa_localized_item, clean_dapa_contract;
DROP TABLE IF EXISTS fact_customs_monthly, dim_hs10;
DROP TABLE IF EXISTS meta_load_log, meta_column_dict, meta_dataset;
DROP TABLE IF EXISTS raw_hs_unit_name, raw_hs_code_master, raw_hsk_control, raw_dapa_contract_exec_by_service, raw_dapa_domestic_plan, raw_dapa_overseas_bid_result,
  raw_dapa_overseas_contract, raw_dapa_overseas_plan,
  raw_customs_progress, raw_kosis_production_index, raw_kosis_utilization,
  raw_dapa_defense_company, raw_dapa_bid_result, raw_dapa_bid_notice, raw_krit_task,
  raw_dapa_localized_item, raw_dapa_contract, raw_customs_trade;
DROP TABLE IF EXISTS ref_hs_rule_flag, ref_hs_indicator, ref_fsc, ref_sido_map, ref_category_map, ref_country, ref_hs_whitelist;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- 1. ref_  참조표  (data/reference/*.csv 및 수작업 대응표)
-- =============================================================================

-- HS6 화이트리스트 24행(2026-09-16: 21 + 규칙 신규 852910·901410·901490). 수집·집계·사이드바 필터의 기준 테이블.
-- 원본: data/reference/hs_whitelist.csv (17열: 8열 + 2026-09-15 정의 열 4개 + civil_mix 3열 + evidence_basis·evidence_note) + 파생 b2_scope
-- civil_mix 3열은 v_civil_mix_rule(정량 지표 → 규칙 도출)의 스냅샷이다. 값을 손으로 고치지 말고 db/alter_2026-09-16_indicator.sql §5 UPDATE로 갱신한다.
-- evidence 3열(evidence·evidence_basis·evidence_note)은 v_hs6_candidate_rule(관세청 HSK 마스터·전략물자 HSK 연계표 규칙 도출)의 스냅샷 — db/alter_2026-09-16_hs_rule.sql §5(정적 UPDATE, 2026-09-16 반영: rule 19 · 팀판단 5, 미해당 5개는 priority 3).
CREATE TABLE ref_hs_whitelist (
  hs6        CHAR(6)      NOT NULL COMMENT 'HS 6단위 코드(원본 hs_code)',
  hs_level   TINYINT      NOT NULL DEFAULT 6,
  category   VARCHAR(20)  NOT NULL COMMENT '반도체 / 전자부품 / 소재장비(배경, 기본 필터 제외)',
  name_ko    VARCHAR(100) NOT NULL,
  name_en    VARCHAR(200) NOT NULL,
  rationale  TEXT         NULL,
  priority   TINYINT      NOT NULL COMMENT '1~3',
  axis       ENUM('import','export','both') NOT NULL,
  system_family  VARCHAR(30)  NULL COMMENT '무기체계 계열(반도체/레이더/통신/통신·레이더 부분품/항법/전자광학/항공전자/AI연산/소재장비) — 2026-09-15 추가',
  defense_use_ko VARCHAR(300) NULL COMMENT '국방 용도 1문장(팀 판단, 공식 분류 아님)',
  related_fsc    VARCHAR(30)  NULL COMMENT 'B2 대응 FSC4 후보(; 구분). ref_category_map 확정 전까지 후보',
  evidence       VARCHAR(120) NULL COMMENT '근거 키. 규칙 도출 후: HSK-군용;HSK-항공/항행;전략물자-ML;전략물자-DU;B2-FSC (v_hs6_candidate_rule.evidence_rule 스냅샷). 도출 전(09-15 팀 판단): A6;B2-FSC;KRIT;A7;팀판단 — docs/reference/hs-whitelist-definition.md §8',
  evidence_basis ENUM('rule','팀판단') NOT NULL DEFAULT '팀판단' COMMENT 'evidence를 정한 방식: rule=공식 자료(관세청 HSK 마스터·전략물자 HSK 연계표) 규칙 도출, 팀판단=09-15 기획 단계 판단 — 2026-09-16 추가',
  evidence_note  VARCHAR(300) NULL COMMENT '규칙 근거 수치 요약(예: HSK10 11개 중 군용전용 1 / 통제 HSK 5개(ML 2) / B2 부품 27). 원값은 v_hs6_candidate_rule',
  civil_mix      ENUM('높음','중간','낮음') NULL COMMENT '민수 혼합 정도 — v_civil_mix_rule 규칙 도출값 스냅샷(2026-09-16). 정량 지표 없는 품목군은 NULL(판단불가). 09-15 팀 판단 라벨은 폐기',
  civil_mix_basis ENUM('hs10','hsk','판단불가') NOT NULL DEFAULT '판단불가' COMMENT 'civil_mix를 정한 지표 종류: hs10=관세청 HS10 용도 세분류 수입 비중, hsk=전략물자 HSK 연계표(적재 후), 판단불가=정량 경로 없음',
  civil_mix_note VARCHAR(200) NULL COMMENT '근거 수치 요약(예: 군용전용 HS10 0.026% 2021~2025). ref_hs_indicator에 원값',
  b2_scope   ENUM('대응 가능','B2 범위 밖') NULL
             COMMENT 'B2 국산화개발품목(지상체계 한정)으로 개발 완료를 채울 수 있는지. 항공·함정·유도 품목군(841191·880730·901420 등)은 B2 범위 밖 — 팀 확정 후 UPDATE',
  PRIMARY KEY (hs6),
  KEY ix_hs_category (category, priority)
) ENGINE=InnoDB COMMENT='HS6 화이트리스트 24개 — 품목군 기준표(원본 17열: 8열 + 2026-09-15 정의 열 4개 + civil_mix 3열 + evidence_basis·evidence_note)';

-- 국가 참조 237행. 원본: data/reference/country_ref.csv
CREATE TABLE ref_country (
  stat_cd  CHAR(2)      NOT NULL COMMENT '관세청 statCd(ISO2). ZZ=기타국',
  name_en  VARCHAR(100) NOT NULL,
  name_ko  VARCHAR(100) NOT NULL COMMENT '관세청 코드표 명칭 그대로(유의사항 7)',
  lat      DECIMAL(9,6) NULL COMMENT 'ZZ는 NULL → 지도 집계 제외',
  lon      DECIMAL(9,6) NULL,
  source   VARCHAR(100) NULL,
  PRIMARY KEY (stat_cd)
) ENGINE=InnoDB COMMENT='국가코드 → 명칭·좌표';

-- 품목군 대응표(수작업). HS↔FSC↔품명 직접 매핑이 아니라 "품목군 수준" 연결만 기록한다.
--   map_type='fsc4'          : B2 군급분류(FSC4) → 화이트리스트 hs6 후보 (idea-review §2 B2 대응 후보)
--   map_type='contract_group': 계약 후보 품목군명(5분류 정제에서 부여) → category/hs6
--   map_type='krit_task'     : B1 과제 → category/hs6 (과제별 판단 근거를 link_basis에)
-- 한 source_key가 여러 hs6에 대응할 수 있다(예 5825 → 852691·901480) → 뷰 집계 시 중복 집계됨을 라벨에 명시.
CREATE TABLE ref_category_map (
  map_id       INT UNSIGNED NOT NULL AUTO_INCREMENT,
  map_type     ENUM('fsc4','contract_group','krit_task') NOT NULL,
  source_key   VARCHAR(50)  NOT NULL COMMENT 'FSC4 / 품목군명 / round_id:task_no',
  category     VARCHAR(20)  NULL COMMENT '반도체 / 전자부품 / 소재장비',
  hs6          VARCHAR(6)   NULL COMMENT '대응되는 화이트리스트 HS6. 품목군(category)까지만 연결되면 NULL. VARCHAR인 이유: MariaDB는 CHAR 열을 생성열 식에 못 쓴다(ERROR 1901)',
  hs6_key      VARCHAR(6)   GENERATED ALWAYS AS (COALESCE(hs6, '')) STORED
               COMMENT 'UNIQUE용. hs6 NULL은 UNIQUE에서 서로 다른 값으로 취급돼 중복을 못 막으므로 빈 문자열로 치환',
  link_status  ENUM('확정','후보','대응불가') NOT NULL DEFAULT '후보',
  link_basis   TEXT         NULL COMMENT '연결 근거(문서·표본 검수 결과)',
  decided_by   VARCHAR(50)  NULL,
  decided_at   DATE         NULL,
  PRIMARY KEY (map_id),
  UNIQUE KEY ux_map (map_type, source_key, hs6_key),
  KEY ix_map_hs6 (hs6),
  CONSTRAINT fk_map_hs6 FOREIGN KEY (hs6) REFERENCES ref_hs_whitelist (hs6)
) ENGINE=InnoDB COMMENT='품목군 수준 대응표(수작업). 직접 매핑 아님';

-- 주소 첫 토큰 → 17개 시도 정규화(보조 ⑤ choropleth). 수작업.
CREATE TABLE ref_sido_map (
  token      VARCHAR(30) NOT NULL COMMENT '주소 첫 토큰 원문(서울/서울특별시/서울시 …)',
  sido_code  CHAR(2)     NOT NULL COMMENT '행정표준코드 앞 2자리(11 서울 … 50 제주)',
  sido_name  VARCHAR(20) NOT NULL COMMENT '표준 시도명',
  PRIMARY KEY (token),
  KEY ix_sido_code (sido_code)
) ENGINE=InnoDB COMMENT='대표업체주소 첫 토큰 → 시도';

-- FSC(군급분류) 4자리 라벨. B2 히트맵·조회표 라벨용. 수작업(선택).
CREATE TABLE ref_fsc (
  fsc4                 CHAR(4)      NOT NULL,
  fsc2                 CHAR(2)      NOT NULL,
  name_ko              VARCHAR(100) NULL,
  name_en              VARCHAR(200) NULL,
  is_electronic_group  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '58xx·59xx = 1 (기본 필터)',
  PRIMARY KEY (fsc4),
  KEY ix_fsc2 (fsc2)
) ENGINE=InnoDB COMMENT='FSC 군급분류 라벨';

-- 품목군별 정량 지표 (2026-09-16). 한 행 = HS6 × 지표 × 기간. "팀판단" 라벨을 대체하는 수치의 원본 저장소.
--   axis='civil_mix'          : 민수 혼합 — mil_hs10_share(군용 전용 HS10 수입 비중, 하한선) · aero_hs10_share(항공기용, 민항 포함) ·
--                               auto_hs10_share(자동차용) · hsk_control_hs10_ratio / hsk_control_imp_share(전략물자 HSK 연계표, raw_hsk_control 적재 후)
--   axis='defense_relevance'  : 국방 관련성 — b2_part_count / b2_row_count(B2 국산화개발품목, ref_category_map fsc4 후보 경유 → link_status='후보', HS6 간 중복·합산 금지) ·
--                               a7_plan_count / a7_plan_budget(국외조달 조달계획, 사용자 키워드 검수 후) · krit_task_count(clean_krit_task 적재 후)
--   값은 v_hs10_use_share·v_defense_relevance_b2에서 INSERT…SELECT로 채우고(db/alter_2026-09-16_indicator.sql), 산식은 method에 남긴다.
--   라벨 도출 규칙은 v_civil_mix_rule. 문턱값은 팀 규칙이며 docs/reference/hs-whitelist-definition.md §7.
CREATE TABLE ref_hs_indicator (
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

-- HS6 규칙 판정 스냅샷 (2026-09-16 팀 회의: "R1~R4를 전부 만들어 두고, 해외 수입 의존도 시각화 때 DB에서 가져와 주피터에서 정제한 뒤 쓸지 정한다").
--   한 행 = HS6(84·85·88·90류, 마스터·dim_hs10·연계표에 등장하는 것 전부) × rule_version. v_hs6_candidate_rule을 그대로 물질화한 것이라
--   원본 3개(raw_hs_code_master·raw_hs_unit_name·raw_hsk_control)가 없는 DB에서도 읽을 수 있다. 채우기: db/alter_2026-09-16_hs_rule.sql §5-4(삭제 후 재삽입).
--   진입 규칙(어느 R가 화이트리스트 진입을 결정하는지)은 팀이 시각화 단계에서 확정 — is_candidate_provisional은 잠정식 R1 OR R2 OR (R3∧R4)의 참고값.
--   노트북: SELECT * FROM ref_hs_rule_flag WHERE rule_version = '2026-09-16';
CREATE TABLE ref_hs_rule_flag (
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

-- =============================================================================
-- 2. raw_  원본 보존  (전 열 문자열, 대리키만, 적재 후 수정 금지)
-- =============================================================================

-- 관세청 품목별 국가별 수출입실적 (data.go.kr 15100475, OpenAPI)
-- 원본: data/raw/customs/customs_all_<HS6>.csv × 21 (UTF-8, 15열)
-- 기대 건수: 294,420 = 총계행 246(is_total='1') + 월별 상세행 294,174 (2026-09-16 24개 기준. 21개일 때 268,909 = 213 + 268,696)
-- 등급: 핵심 1
CREATE TABLE raw_customs_trade (
  row_id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stat_ym        VARCHAR(10)  NULL COMMENT '원본 year: YYYY.MM 또는 총계',
  stat_cd        VARCHAR(4)   NULL COMMENT '원본 statCd. 총계행은 -',
  cnty_name_ko   VARCHAR(100) NULL COMMENT '원본 statCdCntnKor1',
  hs_cd          VARCHAR(10)  NULL COMMENT '원본 hsCd(HS10). 총계행은 -',
  item_name_ko   VARCHAR(300) NULL COMMENT '원본 statKor',
  exp_wgt        VARCHAR(20)  NULL COMMENT '원본 expWgt',
  exp_dlr        VARCHAR(20)  NULL COMMENT '원본 expDlr',
  imp_wgt        VARCHAR(20)  NULL COMMENT '원본 impWgt',
  imp_dlr        VARCHAR(20)  NULL COMMENT '원본 impDlr',
  bal_payments   VARCHAR(20)  NULL COMMENT '원본 balPayments',
  req_hs         CHAR(6)      NULL,
  req_cnty       VARCHAR(4)   NULL COMMENT 'ALL',
  req_year       CHAR(4)      NULL,
  fetched_at     VARCHAR(20)  NULL,
  is_total       CHAR(1)      NULL COMMENT '1=연간 총계행(전 세계 합산, HS10 구분 없음)',
  source_file    VARCHAR(100) NOT NULL COMMENT 'customs_all_<HS6>.csv',
  source_row_no  INT UNSIGNED NULL COMMENT '파일 내 레코드 순번(헤더 제외, 1부터)',
  loaded_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rct_hs (req_hs, is_total),
  KEY ix_rct_key (hs_cd, stat_cd, stat_ym)
) ENGINE=InnoDB COMMENT='관세청 수출입실적 원본(총계행 포함) 294,420행(24개 HS6, 2026-09-16)';

-- 방위사업청 국내조달 계약정보 (data.go.kr 15050920, 파일데이터)
-- 원본: data/raw/dapa/dapa_domestic_contract_20251231.csv (cp949, 28열)
-- 기대 건수: 43,112 (계약번호+차수 고유 43,111 — 1키 2행은 충돌 기록, 삭제 금지)
-- 등급: 핵심 2 / 1만 건 요건(원본 전체 기준, 2025 단독 30,808)
CREATE TABLE raw_dapa_contract (
  row_id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  contract_no               VARCHAR(20)  NULL COMMENT '계약번호',
  contract_seq              VARCHAR(4)   NULL COMMENT '계약차수(0/00 혼재)',
  contract_name             VARCHAR(500) NULL COMMENT '계약명',
  biz_type_name             VARCHAR(20)  NULL COMMENT '업무구분명',
  contract_form_name        VARCHAR(50)  NULL COMMENT '계약체결형태명',
  contract_method_name      VARCHAR(50)  NULL COMMENT '계약체결방법명',
  joint_contract_yn         VARCHAR(20)  NULL COMMENT '공동계약여부',
  contract_date             VARCHAR(10)  NULL COMMENT '계약체결일자',
  contract_period           VARCHAR(30)  NULL COMMENT '계약기간',
  contract_amount           VARCHAR(20)  NULL COMMENT '계약금액(해당 차수)',
  total_contract_amount     VARCHAR(20)  NULL COMMENT '총계약금액',
  reserve_price             VARCHAR(20)  NULL COMMENT '예정가격',
  private_contract_reason   TEXT         NULL COMMENT '수의계약사유',
  contract_org_type_name    VARCHAR(50)  NULL COMMENT '계약기관구분명',
  contract_org_name         VARCHAR(100) NULL COMMENT '계약기관명',
  contract_org_dept_name    VARCHAR(100) NULL COMMENT '계약기관담당부서명',
  contract_org_officer_name VARCHAR(50)  NULL COMMENT '계약기관담당자명(화면 미노출)',
  demand_org_type_name      VARCHAR(50)  NULL COMMENT '수요기관구분명',
  demand_org_name           VARCHAR(100) NULL COMMENT '수요기관명',
  demand_org_dept_name      VARCHAR(100) NULL COMMENT '수요기관담당부서명',
  demand_org_officer_name   VARCHAR(50)  NULL COMMENT '수요기관담당자명(화면 미노출)',
  vendor_name               VARCHAR(200) NULL COMMENT '대표업체명',
  domestic_vendor_yn        VARCHAR(20)  NULL COMMENT '국내업체여부(전부 국내업체, 국산 근거 아님)',
  vendor_ceo_name           VARCHAR(50)  NULL COMMENT '대표업체대표자명(화면 미노출)',
  vendor_biz_reg_no         VARCHAR(20)  NULL COMMENT '대표업체사업자등록번호',
  vendor_address            VARCHAR(300) NULL COMMENT '대표업체주소(계약업체 소재지)',
  contract_type             VARCHAR(50)  NULL COMMENT '계약유형',
  price_adjust_method       VARCHAR(100) NULL COMMENT '물가변동계약금액조정방법',
  source_file               VARCHAR(100) NOT NULL,
  source_row_no             INT UNSIGNED NULL,
  loaded_at                 DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rdc_key (contract_no, contract_seq),
  KEY ix_rdc_date (contract_date),
  KEY ix_rdc_vendor (vendor_biz_reg_no)
) ENGINE=InnoDB COMMENT='방사청 국내조달 계약정보 원본 43,112행';

-- 방위사업청 국방전자조달시스템 국산화개발품목 (data.go.kr 15119899, 파일데이터) — B2
-- 원본: data/raw/dapa/dapa_localized_items_20260509.csv (cp949, 10열)
-- 기대 건수: 33,965 (완전 중복 8,940 포함 → 고유 25,025 = 사업명×부품관리번호, 부품관리번호 고유 12,788)
-- 등급: 핵심 2 보강. 지상 기동·화력 28개 사업 한정, 시점 미상 스냅샷(최종수정일은 연도 축 사용 금지)
CREATE TABLE raw_dapa_localized_item (
  row_id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  project_name        VARCHAR(100) NULL COMMENT '사업명',
  part_mgmt_no        VARCHAR(20)  NULL COMMENT '부품관리번호',
  nsn                 VARCHAR(20)  NULL COMMENT '재고번호',
  fsc                 VARCHAR(4)   NULL COMMENT '군급분류',
  item_name           VARCHAR(200) NULL COMMENT '품명',
  drawing_no          VARCHAR(50)  NULL COMMENT '도면번호(화면 미노출)',
  drawing_part_no     VARCHAR(50)  NULL COMMENT '도면부품번호(화면 미노출)',
  spec_no             VARCHAR(50)  NULL COMMENT '규격번호(화면 미노출)',
  contractor_name     VARCHAR(200) NULL COMMENT '계약업체(계약 상대, 개발 주체 아님)',
  last_modified_date  VARCHAR(10)  NULL COMMENT '최종수정일(공란 25,191)',
  source_file         VARCHAR(100) NOT NULL,
  source_row_no       INT UNSIGNED NULL,
  loaded_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rli_key (project_name, part_mgmt_no),
  KEY ix_rli_fsc (fsc)
) ENGINE=InnoDB COMMENT='방사청 국산화개발품목 원본 33,965행(완전 중복 포함)';

-- KRIT 무기체계 부품국산화개발 지원사업 공고 과제표 — B1
-- 원본: scripts/parse_krit.py 출력 / PDF 표 추출(data/raw/krit/). 차수마다 열 구성이 달라
--       공통 열 5개(26-1차 기준) + extra_json(나머지 열 JSON 문자열)로 받는다.
-- 기대 건수: 2023~2026 누적 100건 안팎(23-4차 18 / 24-1차 예비 11 / 25-1차 수정 22·재공고 3 / 26-1차 2 / 26-2차 예비 20)
-- 등급: 핵심 2(B1). 같은 차수의 예비·본·재공고는 합산 금지 → notice_type 유지
CREATE TABLE raw_krit_task (
  row_id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  round_label      VARCHAR(20)  NOT NULL COMMENT '차수 원문(예 26-1차)',
  notice_type      VARCHAR(20)  NULL COMMENT '예비 / 본공고 / 재공고 / 수정 (파일명·본문에서)',
  task_seq         VARCHAR(4)   NULL COMMENT '순',
  task_name        VARCHAR(300) NULL COMMENT '국산화 개발대상 과제명',
  gov_fund_text    VARCHAR(30)  NULL COMMENT '정부지원 연구개발비 원문',
  dev_period_text  VARCHAR(30)  NULL COMMENT '개발 기간 원문',
  note             VARCHAR(300) NULL COMMENT '비고',
  extra_json       TEXT         NULL COMMENT '차수별 추가 열 {"원본열명": "값"} JSON 문자열',
  table_index      SMALLINT     NULL COMMENT '문서 내 표 번호(parse_krit.py _tN)',
  source_file      VARCHAR(200) NOT NULL COMMENT '공고 파일명(hwpx/pdf/csv)',
  source_url       VARCHAR(300) NULL,
  source_row_no    INT UNSIGNED NULL,
  loaded_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rkt_round (round_label, notice_type)
) ENGINE=InnoDB COMMENT='KRIT 부품국산화 공고 과제표 원본';

-- 방위사업청 국내조달 경쟁 입찰공고 (data.go.kr 15050916) — 보조
-- 원본: data/raw/dapa/dapa_domestic_bid_notice_20251231.csv (cp949, 47열). 기대 건수: 10,842
-- 2026-09-15 팀 서버 적재 시 STRICT 모드 잘림(1406)으로 여부 열 5개 VARCHAR(2)→(20), 면허제한그룹 8열 (100)→(300) 확장. 원본에 열 밀림 행 2건이 있어 여부 열에 날짜·금액이 들어 있으나 raw 는 그대로 보존한다
CREATE TABLE raw_dapa_bid_notice (
  row_id                       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  bid_notice_no                VARCHAR(20)  NULL COMMENT '입찰공고번호(연도 미포함, 비유일)',
  bid_notice_seq               VARCHAR(4)   NULL COMMENT '입찰공고차수',
  ref_notice_no                VARCHAR(30)  NULL COMMENT '참조공고번호(실제 키)',
  ref_notice_seq               VARCHAR(4)   NULL COMMENT '참조공고차수',
  g2b_notice_yn                VARCHAR(20)  NULL COMMENT '나라장터공고여부',
  bid_notice_name              VARCHAR(500) NULL COMMENT '입찰공고명',
  bid_notice_status_name       VARCHAR(20)  NULL COMMENT '입찰공고상태명',
  bid_notice_date              VARCHAR(10)  NULL COMMENT '입찰공고일자',
  biz_type_name                VARCHAR(20)  NULL COMMENT '업무구분명',
  joint_contract_yn            VARCHAR(20)  NULL COMMENT '공동계약여부(열 밀림 원본 2행은 날짜가 들어 있음 — 원본 보존)',
  joint_supply_method_name     VARCHAR(50)  NULL COMMENT '공동수급방식명',
  e_bid_yn                     VARCHAR(20)  NULL COMMENT '전자입찰여부',
  contract_form_name           VARCHAR(50)  NULL COMMENT '계약체결형태명',
  contract_method_name         VARCHAR(50)  NULL COMMENT '계약체결방법명',
  award_method_name            VARCHAR(50)  NULL COMMENT '낙찰자결정방법명',
  notice_org_name              VARCHAR(100) NULL COMMENT '공고기관명',
  notice_org_code              VARCHAR(20)  NULL COMMENT '공고기관코드',
  notice_org_dept_name         VARCHAR(100) NULL COMMENT '공고기관담당자부서명',
  notice_org_officer_name      VARCHAR(50)  NULL COMMENT '공고기관담당자명(화면 미노출)',
  demand_org_name              VARCHAR(100) NULL COMMENT '수요기관명',
  demand_org_code              VARCHAR(20)  NULL COMMENT '수요기관코드',
  demand_org_dept_name         VARCHAR(100) NULL COMMENT '수요기관담당자부서명',
  demand_org_officer_name      VARCHAR(50)  NULL COMMENT '수요기관담당자명(화면 미노출)',
  briefing_yn                  VARCHAR(20)  NULL COMMENT '설명회실시여부(열 밀림 원본 2행 보존)',
  briefing_date                VARCHAR(10)  NULL COMMENT '설명회실시일자',
  briefing_time                VARCHAR(10)  NULL COMMENT '설명회실시시각',
  briefing_place               VARCHAR(200) NULL COMMENT '설명회실시장소',
  qualification_deadline_date  VARCHAR(10)  NULL COMMENT '입찰참가자격등록마감일자',
  qualification_deadline_time  VARCHAR(10)  NULL COMMENT '입찰참가자격등록마감시각',
  bid_deadline_date            VARCHAR(10)  NULL COMMENT '입찰마감일자',
  bid_deadline_time            VARCHAR(10)  NULL COMMENT '입찰마감시각',
  opening_date                 VARCHAR(10)  NULL COMMENT '개찰일자',
  opening_time                 VARCHAR(10)  NULL COMMENT '개찰시각',
  opening_place                VARCHAR(200) NULL COMMENT '개찰장소',
  budget_amount                VARCHAR(20)  NULL COMMENT '예산금액',
  allocated_budget_amount      VARCHAR(20)  NULL COMMENT '배정예산금액(설계금액)',
  region_limit_yn              VARCHAR(20)  NULL COMMENT '지역제한여부(열 밀림 원본 2행 보존)',
  eligible_region_name         VARCHAR(200) NULL COMMENT '참가가능지역명',
  license_limit_group1         VARCHAR(300) NULL COMMENT '공종및면허제한그룹1(최대 148자 실측)',
  license_limit_group2         VARCHAR(300) NULL,
  license_limit_group3         VARCHAR(300) NULL,
  license_limit_group4         VARCHAR(300) NULL,
  license_limit_group5         VARCHAR(300) NULL,
  license_limit_group6         VARCHAR(300) NULL,
  license_limit_group7         VARCHAR(300) NULL,
  license_limit_group8         VARCHAR(300) NULL COMMENT '공종및면허제한그룹8',
  bid_notice_url               VARCHAR(300) NULL COMMENT '입찰공고URL',
  source_file                  VARCHAR(100) NOT NULL,
  source_row_no                INT UNSIGNED NULL,
  loaded_at                    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rbn_key (ref_notice_no, ref_notice_seq),
  KEY ix_rbn_date (bid_notice_date)
) ENGINE=InnoDB COMMENT='방사청 국내조달 입찰공고 원본 10,842행(보조)';

-- 방위사업청 국내조달 경쟁 입찰결과 (data.go.kr 15050917) — 보조
-- 원본: data/raw/dapa/dapa_domestic_bid_result_20251231.csv (cp949, 27열). 기대 건수: 7,405 (키 고유 7,201 — 199키 중복은 성격 미확인)
-- 2026-09-15 적격심사여부 VARCHAR(2)→(20) 확장(열 밀림 원본 2행 보존)
CREATE TABLE raw_dapa_bid_result (
  row_id                   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  bid_notice_no            VARCHAR(20)  NULL COMMENT '입찰공고번호',
  bid_notice_seq           VARCHAR(4)   NULL COMMENT '입찰공고차수',
  bid_notice_name          VARCHAR(500) NULL COMMENT '입찰공고명',
  biz_type_name            VARCHAR(20)  NULL COMMENT '업무구분명',
  contract_form_name       VARCHAR(50)  NULL COMMENT '계약체결형태명',
  contract_method_name     VARCHAR(50)  NULL COMMENT '계약체결방법명',
  award_method_name        VARCHAR(50)  NULL COMMENT '낙찰자결정방법명',
  qualification_review_yn  VARCHAR(20)  NULL COMMENT '적격심사여부(열 밀림 원본 2행은 ''제한경쟁'' — 원본 보존)',
  notice_org_name          VARCHAR(100) NULL COMMENT '공고기관명',
  notice_org_code          VARCHAR(20)  NULL COMMENT '공고기관코드',
  demand_org_name          VARCHAR(100) NULL COMMENT '수요기관명',
  demand_org_code          VARCHAR(20)  NULL COMMENT '수요기관코드',
  award_lower_limit_rate   VARCHAR(10)  NULL COMMENT '낙찰하한율',
  reserve_price            VARCHAR(20)  NULL COMMENT '예정가격',
  base_amount              VARCHAR(20)  NULL COMMENT '기초금액',
  estimated_price          VARCHAR(20)  NULL COMMENT '추정가격',
  opening_date             VARCHAR(10)  NULL COMMENT '개찰일자',
  opening_time             VARCHAR(10)  NULL COMMENT '개찰시각',
  opening_result_name      VARCHAR(20)  NULL COMMENT '개찰결과구분명',
  final_award_amount       VARCHAR(20)  NULL COMMENT '최종낙찰금액',
  final_award_rate         VARCHAR(10)  NULL COMMENT '최종낙찰율',
  final_award_date         VARCHAR(10)  NULL COMMENT '최종낙찰일자',
  winner_name              VARCHAR(200) NULL COMMENT '최종낙찰업체명',
  winner_ceo_name          VARCHAR(50)  NULL COMMENT '최종낙찰업체대표자명(화면 미노출)',
  winner_officer_name      VARCHAR(50)  NULL COMMENT '최종낙찰업체담당자명(화면 미노출)',
  winner_biz_reg_no        VARCHAR(20)  NULL COMMENT '최종낙찰업체사업자등록번호',
  winner_address           VARCHAR(300) NULL COMMENT '최종낙찰업체주소(낙찰업체 소재지)',
  source_file              VARCHAR(100) NOT NULL,
  source_row_no            INT UNSIGNED NULL,
  loaded_at                DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rbr_key (bid_notice_no, bid_notice_seq),
  KEY ix_rbr_winner (winner_biz_reg_no)
) ENGINE=InnoDB COMMENT='방사청 국내조달 입찰결과 원본 7,405행(보조)';

-- 방위사업청 방산업체 지정현황 (data.go.kr 15081929) — 보조. 주소 없음.
-- 원본: data/raw/dapa/dapa_defense_company_20260831.csv (cp949, 5열). 기대 건수: 84
CREATE TABLE raw_dapa_defense_company (
  row_id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  seq_no           VARCHAR(4)   NULL COMMENT '순번',
  company_name     VARCHAR(200) NULL COMMENT '업체명',
  sector           VARCHAR(20)  NULL COMMENT '분야',
  designated_date  VARCHAR(10)  NULL COMMENT '지정일자',
  note             VARCHAR(300) NULL COMMENT '비고',
  source_file      VARCHAR(100) NOT NULL,
  source_row_no    INT UNSIGNED NULL,
  loaded_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id)
) ENGINE=InnoDB COMMENT='방산업체 지정현황 원본 84행(보조)';

-- KOSIS 409 방산업체 경영분석 분야별 평균가동률 — 보조 (A4)
-- 원본: data/raw/kosis/kosis_409_utilization_by_sector_2016_2024.csv (cp949, 광폭 9행×연도 9열)
-- 광폭 → 세로형 변환은 "형식 변환"이며 값은 원문 문자열 그대로. 기대 건수: 9 × 9 = 81 (파일 1개당)
-- 업무키 UNIQUE 없음: 갱신본을 다시 받으면 같은 (sector_name, year)가 다른 source_file로 추가된다. 조회 시 source_file로 구분.
CREATE TABLE raw_kosis_utilization (
  row_id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sector_name    VARCHAR(20) NOT NULL COMMENT '분야별(평균·항공유도·화력·탄약·기동·통신전자·함정·화생방·기타)',
  year           CHAR(4)     NOT NULL COMMENT '광폭 열 헤더',
  value_text     VARCHAR(20) NULL COMMENT '평균가동률 %(원문)',
  source_file    VARCHAR(100) NOT NULL,
  source_row_no  INT UNSIGNED NULL COMMENT '광폭 원본의 행 번호(헤더 제외, 1부터)',
  source_col_no  SMALLINT     NULL COMMENT '광폭 원본의 열 번호(1부터). 세로형 변환 전 위치 추적',
  loaded_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rku (sector_name, year)
) ENGINE=InnoDB COMMENT='KOSIS 409 분야별 평균가동률(세로형) 81행/파일(보조)';

-- KOSIS 101 광공업생산지수 C26·C261·C262·C264 (DT_1F02001, 2020=100) — 보조 (A5)
-- 원본: data/raw/kosis/kosis_101_production_index_c26_201601_202607.csv (cp949, 헤더 2행 광폭 4행×254값)
-- 기대 건수: 4 산업 × 127개월 × 2항목 = 1,016 (파일 1개당)
-- 업무키 UNIQUE 없음: 잠정치(p)가 확정치로 바뀐 갱신본을 다시 받으면 다른 source_file로 추가된다.
CREATE TABLE raw_kosis_production_index (
  row_id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  region_name    VARCHAR(30)  NOT NULL COMMENT 'A 시도별(00 전국)',
  industry_name  VARCHAR(100) NOT NULL COMMENT 'B 산업별(C26/C261/C262/C264 + 명칭)',
  stat_ym        VARCHAR(10)  NOT NULL COMMENT '1행 헤더 YYYY.MM',
  item_name      VARCHAR(50)  NOT NULL COMMENT '2행 헤더(T10 원지수 / T20 계절조정)',
  value_text     VARCHAR(20)  NULL COMMENT '지수 원문(2026.07 잠정 p)',
  source_file    VARCHAR(100) NOT NULL,
  source_row_no  INT UNSIGNED NULL COMMENT '광폭 원본의 행 번호(헤더 2행 제외, 1부터)',
  source_col_no  SMALLINT     NULL COMMENT '광폭 원본의 열 번호(1부터). 세로형 변환 전 위치 추적',
  loaded_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rkp (region_name, industry_name, stat_ym, item_name)
) ENGINE=InnoDB COMMENT='KOSIS 101 광공업생산지수 C26(세로형) 1,016행/파일(보조)';

-- 관세청 수집 진행 로그 — 재현성 증빙. 원본: data/raw/customs/progress_all.csv. 기대 건수: 264 (24개 × 11년, 2026-09-16; 21개일 때 231) (rows 합 268,909)
-- 업무키 UNIQUE 없음: 재수집 회차마다 progress 파일이 새로 생기면 같은 (hs, cnty, year)가 누적된다. source_file·fetched_at으로 회차 구분.
CREATE TABLE raw_customs_progress (
  row_id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  hs             CHAR(6)     NOT NULL,
  cnty           VARCHAR(4)  NOT NULL COMMENT 'ALL',
  year           CHAR(4)     NOT NULL,
  row_count      INT         NOT NULL COMMENT '원본 rows. 0 = HS2022 신설 코드 공백(18건)',
  fetched_at     VARCHAR(20) NULL,
  source_file    VARCHAR(100) NOT NULL,
  source_row_no  INT UNSIGNED NULL COMMENT '파일 내 레코드 순번(헤더 제외, 1부터)',
  loaded_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rcp (hs, cnty, year)
) ENGINE=InnoDB COMMENT='관세청 호출별 반환 행수 231행/파일(메타)';

-- -----------------------------------------------------------------------------
-- A7. 방위사업청 국외조달·조달계획 파일데이터 (2026-09-15 교수 피드백 반영, 배경 ⓪ 예산 추이)
-- 팀원 공유분(new_data/ → data/raw/dapa/ 이동 예정). data.go.kr ID·다운로드일 미확인 → meta_dataset.dataset_id NULL 허용.
-- 모두 1만 건 요건 아님. 담당자명·연락처 열은 개인정보이므로 LOAD DATA 시 SET officer_name = NULL 로 비운다(열 사전 순서는 유지).
-- -----------------------------------------------------------------------------

-- 국외조달 조달계획 — 배경 ⓪ 핵심. 원본: dapa_overseas_plan_20251231.csv (cp949, 10열). 기대 건수: 3,029 (판단번호 고유 3,024)
-- 집행예정월 2017~2025. 예산금액은 원화 "집행 예정액"(계획)이며 실적이 아니다. 국가 열 없음 → 관세청 수입액과 합산·비교 금지(idea-review §3-15)
CREATE TABLE raw_dapa_overseas_plan (
  row_id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  plan_month       VARCHAR(10)  NULL COMMENT '집행예정월(YYYY-MM-01)',
  decision_no      VARCHAR(20)  NULL COMMENT '판단번호(입찰결과와 공유, 계약정보에는 없음)',
  rep_item_name    VARCHAR(500) NULL COMMENT '대표품명(전자 관련 후보 분류 대상)',
  exec_type        VARCHAR(30)  NULL COMMENT '집행유형(장비/(확정)부품/한도액부품/장비정비/물자/기술용역/기름(연료)/기타 등)',
  contract_method  VARCHAR(30)  NULL COMMENT '계약방법',
  exec_agency      VARCHAR(100) NULL COMMENT '집행기관',
  budget_amount    VARCHAR(20)  NULL COMMENT '예산금액(원, 집행 예정액)',
  bid_method       VARCHAR(30)  NULL COMMENT '입찰방법',
  progress_status  VARCHAR(30)  NULL COMMENT '진행상태(계약/부분계약/N차공고중/N차공고의뢰중/판단완료 등)',
  officer_name     VARCHAR(50)  NULL COMMENT '담당자명(개인정보 — 적재 시 NULL)',
  source_file      VARCHAR(100) NOT NULL,
  source_row_no    INT UNSIGNED NULL,
  loaded_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rop_month (plan_month),
  KEY ix_rop_decision (decision_no),
  KEY ix_rop_type (exec_type)
) ENGINE=InnoDB COMMENT='방사청 국외조달 조달계획 원본 3,029행(2017~2025, 배경 ⓪)';

-- 국외조달 계약정보 — 배경 보조(건수만). 원본: dapa_overseas_contract_20251231.csv (cp949, 14열). 기대 건수: 6,333
-- 금액·국가·사업자번호 열 없음. 대표업체명(외국 업체명)으로 국가를 추정하지 않는다. 화면 노출은 고유 업체 수 등 집계 단위로 제한
CREATE TABLE raw_dapa_overseas_contract (
  row_id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  contract_no               VARCHAR(20)  NULL COMMENT '계약번호',
  contract_name             VARCHAR(500) NULL COMMENT '계약명',
  biz_type_name             VARCHAR(20)  NULL COMMENT '업무구분명(전부 외자)',
  contract_form_name        VARCHAR(50)  NULL COMMENT '계약체결형태명',
  contract_method_name      VARCHAR(50)  NULL COMMENT '계약체결방법명',
  contract_date             VARCHAR(10)  NULL COMMENT '계약체결일자',
  contract_period           VARCHAR(30)  NULL COMMENT '계약기간',
  contract_org_type_name    VARCHAR(50)  NULL COMMENT '계약기관구분명',
  contract_org_name         VARCHAR(100) NULL COMMENT '계약기관명',
  contract_org_dept_name    VARCHAR(100) NULL COMMENT '계약기관담당부서명',
  contract_org_officer_name VARCHAR(50)  NULL COMMENT '계약기관담당자명(개인정보 — 적재 시 NULL)',
  demand_org_type_name      VARCHAR(50)  NULL COMMENT '수요기관구분명',
  demand_org_name           VARCHAR(100) NULL COMMENT '수요기관명',
  vendor_name               VARCHAR(200) NULL COMMENT '대표업체명(외국 업체, 국가 추정 금지)',
  source_file               VARCHAR(100) NOT NULL,
  source_row_no             INT UNSIGNED NULL,
  loaded_at                 DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_roc_no (contract_no),
  KEY ix_roc_date (contract_date)
) ENGINE=InnoDB COMMENT='방사청 국외조달 계약정보 원본 6,333행(2017~2025, 금액·국가 없음)';

-- 국외조달 입찰결과 — 배경 보조(유찰률). 원본: dapa_overseas_bid_result_20250915.csv (cp949, 13열). 기대 건수: 2,494 (판단번호 고유 97)
-- 개찰일시 2025-01~09 부분연도. 예산금액(달러). 낙찰업체 열 없음
CREATE TABLE raw_dapa_overseas_bid_result (
  row_id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  bid_notice_no     VARCHAR(20)  NULL COMMENT '공고번호',
  decision_no       VARCHAR(20)  NULL COMMENT '판단번호(조달계획과 공유)',
  item_seq          VARCHAR(6)   NULL COMMENT '항목번호',
  bid_item_name     VARCHAR(500) NULL COMMENT '입찰건명',
  ordering_agency   VARCHAR(100) NULL COMMENT '발주기관',
  contract_method   VARCHAR(30)  NULL COMMENT '계약방법',
  bid_method        VARCHAR(30)  NULL COMMENT '입찰방법',
  award_method      VARCHAR(30)  NULL COMMENT '낙찰방법',
  opening_datetime  VARCHAR(20)  NULL COMMENT '개찰일시',
  unit_price_type   VARCHAR(30)  NULL COMMENT '단가제유형',
  prequalification  VARCHAR(30)  NULL COMMENT '사전심사',
  bid_result        VARCHAR(20)  NULL COMMENT '입찰결과(유찰/낙찰)',
  budget_amount_usd VARCHAR(20)  NULL COMMENT '예산금액(달러)',
  source_file       VARCHAR(100) NOT NULL,
  source_row_no     INT UNSIGNED NULL,
  loaded_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_robr_decision (decision_no),
  KEY ix_robr_result (bid_result)
) ENGINE=InnoDB COMMENT='방사청 국외조달 입찰결과 원본 2,494행(2025-01~09 부분연도)';

-- 국내조달 조달계획 — 보조(국내 vs 국외 예산 규모). 원본: dapa_domestic_plan_20251231.csv (cp949, 11열). 기대 건수: 35,859 (2024: 4,545 / 2025: 31,314)
-- 1만 건 요건에는 쓰지 않는다(사용자 결정 2026-09-15). 국외 조달계획과 열이 같고 연락처 1열이 더 있다
CREATE TABLE raw_dapa_domestic_plan (
  row_id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  plan_month       VARCHAR(10)  NULL COMMENT '집행예정월(YYYY-MM-01)',
  decision_no      VARCHAR(20)  NULL COMMENT '판단번호',
  rep_item_name    VARCHAR(500) NULL COMMENT '대표품명',
  exec_type        VARCHAR(30)  NULL COMMENT '집행유형(구매/제조/제조/구매/기타/공사/리스/공급)',
  contract_method  VARCHAR(30)  NULL COMMENT '계약방법',
  exec_agency      VARCHAR(100) NULL COMMENT '집행기관',
  budget_amount    VARCHAR(20)  NULL COMMENT '예산금액(원, 집행 예정액)',
  bid_method       VARCHAR(30)  NULL COMMENT '입찰방법',
  progress_status  VARCHAR(30)  NULL COMMENT '진행상태',
  officer_name     VARCHAR(50)  NULL COMMENT '담당자명(개인정보 — 적재 시 NULL)',
  officer_phone    VARCHAR(30)  NULL COMMENT '연락처(개인정보 — 적재 시 NULL)',
  source_file      VARCHAR(100) NOT NULL,
  source_row_no    INT UNSIGNED NULL,
  loaded_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rdp_month (plan_month),
  KEY ix_rdp_type (exec_type)
) ENGINE=InnoDB COMMENT='방사청 국내조달 조달계획 원본 35,859행(2024~2025, 보조)';

-- 군별 계약집행 현황 — KPI. 원본: dapa_contract_exec_by_service_20241231.csv (cp949, 3열). 기대 건수: 40 (2015~2024 × 육군/해군/공군/국직)
CREATE TABLE raw_dapa_contract_exec_by_service (
  row_id                   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  year                     CHAR(4)      NULL COMMENT '년도',
  service_branch           VARCHAR(10)  NULL COMMENT '군구분(육군/해군/공군/국직)',
  contract_amount_100m_krw VARCHAR(20)  NULL COMMENT '계약금액(억원)',
  source_file              VARCHAR(100) NOT NULL,
  source_row_no            INT UNSIGNED NULL,
  loaded_at                DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id)
) ENGINE=InnoDB COMMENT='방사청 군별 계약집행 현황 원본 40행(2015~2024, KPI)';

-- 무역안보관리원 HSK 연계표 (data.go.kr 15034135, 전략물자 통제번호 ↔ HSK 10자리). 2026-09-16 확보: 2,161행(포털 표시와 일치), utf-8-sig, 헤더 품목번호·품명(국문)·품명(영문)·통제번호.
-- 용도: ref_hs_indicator hsk_control_* (HS6 아래 통제 HSK10 비율·수입액 비중). 원본 열 4개 그대로.
CREATE TABLE raw_hsk_control (
  row_id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  hsk10          VARCHAR(12)  NULL COMMENT '품목번호(HSK 10자리)',
  name_ko        VARCHAR(300) NULL COMMENT '품명(국문)',
  name_en        VARCHAR(400) NULL COMMENT '품명(영문, 최대 368자)',
  control_no     TEXT         NULL COMMENT '통제번호 — 쉼표 목록(예 3A001.a.1.,5A002.), 최대 1,218자. 2026-09-16 확인: 별표2 이중용도만, ML 0건',
  source_file    VARCHAR(100) NOT NULL,
  source_row_no  INT UNSIGNED NULL,
  loaded_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_hsk10 (hsk10)
) ENGINE=InnoDB COMMENT='무역안보관리원 HSK 연계표 원본(15034135, 2,161행). 2026-09-16 확보';

-- 관세청 HS부호 마스터 (data.go.kr 15049722 「관세청_HS부호_20260101」, XLSX 1시트, 2026-09-16 확보: 12,469행 = 10자리 11,327 + 7~9자리 호 수준 1,142, 전부 적용종료 2026-12-31).
-- 용도: HS6 선정 규칙(v_hs10_use_tag_all → v_hs6_candidate_rule). 현행(2026) 코드표라 과거 연도에만 있던 세분류(예 8542.31-4010 군용전용)는 없다 —
--       그 코드들은 수집된 dim_hs10(2016~2026 응답)에 남아 있어 뷰에서 UNION한다. 원본 열 20개 그대로(헤더 확인됨).
-- 법령 근거: 관세법 §84(품목분류체계) → 「관세·통계통합품목분류표」(기획재정부 고시)의 10단위 세분류.
CREATE TABLE raw_hs_code_master (
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
CREATE TABLE raw_hs_unit_name (
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

-- =============================================================================
-- 3. meta_  출처 기록 · 단계별 건수 · 열 사전
-- =============================================================================

-- 데이터셋 1건 = 확보한 원본 1종. docs/data-sources.md "원본 확보 기록"을 행으로 옮긴다.
CREATE TABLE meta_dataset (
  dataset_key        VARCHAR(40)  NOT NULL COMMENT '예 customs_all, dapa_contract, dapa_localized_item',
  tier               ENUM('핵심','보조','참조','메타') NOT NULL,
  provider           VARCHAR(100) NOT NULL COMMENT '제공기관',
  dataset_id         VARCHAR(40)  NULL COMMENT '포털 ID(15100475 등) / tblId',
  title              VARCHAR(200) NOT NULL,
  url                VARCHAR(300) NULL,
  access_method      VARCHAR(50)  NOT NULL COMMENT 'OpenAPI / 파일 다운로드 / 웹 다운로드 / 수작업',
  acquired_on        DATE         NOT NULL COMMENT '확보일',
  period_start       DATE         NULL COMMENT '실제 대상 기간(사건 날짜 기준)',
  period_end         DATE         NULL,
  is_partial_period  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '부분연도·부분기간 여부',
  published_on       DATE         NULL COMMENT '포털 게시일',
  updated_on         DATE         NULL COMMENT '포털 수정일',
  query_condition    TEXT         NULL COMMENT '조회 조건·호출 파라미터',
  raw_path           VARCHAR(300) NOT NULL COMMENT 'data/raw/... 상대 경로(패턴 허용)',
  file_bytes         BIGINT       NULL,
  sha256             CHAR(64)     NULL COMMENT '단일 파일일 때. 다중 파일은 note에',
  encoding           VARCHAR(20)  NOT NULL,
  parser             VARCHAR(100) NULL COMMENT '건수 집계 파서(pandas read_csv dtype=str 등)',
  raw_row_count      INT          NOT NULL COMMENT '파서 기준 레코드 수(헤더 제외)',
  portal_row_count   INT          NULL COMMENT '포털 표시 건수(다르면 둘 다 기록)',
  target_table       VARCHAR(64)  NULL COMMENT '적재 대상 raw_ 테이블',
  note               TEXT         NULL,
  PRIMARY KEY (dataset_key)
) ENGINE=InnoDB COMMENT='원본 확보 기록(출처·확보일·해시·건수)';

-- 단계별 건수: 원본 전체 → 선택 연도 → 중복 처리 후 → 관련 후보 → 검증된 분석 대상 (CLAUDE.md 보고 규칙)
CREATE TABLE meta_load_log (
  log_id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  dataset_key       VARCHAR(40)  NOT NULL,
  table_name        VARCHAR(64)  NOT NULL COMMENT '건수를 잰 테이블',
  stage             ENUM('원본 전체','선택 연도 원본','중복 처리 후','관련 후보','검증된 분석 대상') NOT NULL,
  stage_detail      VARCHAR(100) NULL COMMENT '예 2025 / HS10 / HS6 집계 / 5분류=방산 장비·부품 후보',
  row_count         INT          NOT NULL,
  exclusion_reason  TEXT         NULL COMMENT '이전 단계 대비 제외 사유',
  method            TEXT         NULL COMMENT '집계 SQL 또는 노트북 셀 참조',
  measured_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  measured_by       VARCHAR(50)  NULL,
  PRIMARY KEY (log_id),
  KEY ix_mll (dataset_key, stage),
  CONSTRAINT fk_mll_dataset FOREIGN KEY (dataset_key) REFERENCES meta_dataset (dataset_key)
) ENGINE=InnoDB COMMENT='단계별 건수 보고(원본→정제→분석 대상)';

-- 열 사전: db/column_dict.csv 와 동일 내용(원본 한글 열명 ↔ 영문 열명)
CREATE TABLE meta_column_dict (
  table_name     VARCHAR(64)  NOT NULL,
  ordinal        SMALLINT     NOT NULL COMMENT '원본 열 순서',
  column_name    VARCHAR(64)  NOT NULL COMMENT 'DB 열명',
  original_name  VARCHAR(100) NOT NULL COMMENT '원본 CSV 헤더(줄바꿈은 \\n)',
  dtype          VARCHAR(50)  NOT NULL COMMENT '설계 타입(raw는 문자열)',
  description    VARCHAR(300) NULL,
  PRIMARY KEY (table_name, column_name),
  UNIQUE KEY ux_mcd_ord (table_name, ordinal)
) ENGINE=InnoDB COMMENT='원본 열명 ↔ DB 열명 사전';

-- =============================================================================
-- 4. dim_ / fact_  관세청 정형 (규칙 확정: 총계행 제외 · YYYY.MM 파싱 · hs6 = LEFT(hs10,6))
-- =============================================================================

CREATE TABLE dim_hs10 (
  hs10     CHAR(10)     NOT NULL,
  hs6      CHAR(6)      NOT NULL,
  name_ko  VARCHAR(300) NULL COMMENT '관세청 statKor(코드당 최근 값)',
  PRIMARY KEY (hs10),
  KEY ix_dh_hs6 (hs6),
  CONSTRAINT fk_dh_hs6 FOREIGN KEY (hs6) REFERENCES ref_hs_whitelist (hs6)
) ENGINE=InnoDB COMMENT='HS10 → HS6 · 품명';

-- 한 행 = HS10 × 국가 × 월 (총계행 제외). 기대 건수: 294,174(24개, 2026-09-16; 21개일 때 268,696). 2025 단독 26,211(21개일 때 23,844).
CREATE TABLE fact_customs_monthly (
  hs10             CHAR(10)  NOT NULL,
  stat_cd          CHAR(2)   NOT NULL,
  yyyymm           CHAR(6)   NOT NULL,
  hs6              CHAR(6)   NOT NULL,
  year             SMALLINT  NOT NULL,
  month            TINYINT   NOT NULL,
  imp_dlr          BIGINT    NOT NULL DEFAULT 0 COMMENT 'USD, CIF',
  exp_dlr          BIGINT    NOT NULL DEFAULT 0 COMMENT 'USD, FOB',
  imp_wgt          BIGINT    NULL COMMENT 'kg(참고값, 반올림 오차)',
  exp_wgt          BIGINT    NULL,
  bal_payments     BIGINT    NULL,
  is_partial_year  TINYINT(1) NOT NULL DEFAULT 0 COMMENT '2026(1~8월) = 1. 연간 실적처럼 쓰지 않음',
  raw_row_id       BIGINT UNSIGNED NULL COMMENT '→ raw_customs_trade.row_id (1:1)',
  PRIMARY KEY (hs10, stat_cd, yyyymm),
  UNIQUE KEY ux_fcm_raw (raw_row_id),
  KEY ix_fcm_hs6_year (hs6, year, stat_cd),
  KEY ix_fcm_cnty_year (stat_cd, year),
  KEY ix_fcm_ym (yyyymm),
  CONSTRAINT fk_fcm_hs6  FOREIGN KEY (hs6)        REFERENCES ref_hs_whitelist (hs6),
  CONSTRAINT fk_fcm_cnty FOREIGN KEY (stat_cd)    REFERENCES ref_country (stat_cd),
  CONSTRAINT fk_fcm_hs10 FOREIGN KEY (hs10)       REFERENCES dim_hs10 (hs10),
  CONSTRAINT fk_fcm_raw  FOREIGN KEY (raw_row_id) REFERENCES raw_customs_trade (row_id)
) ENGINE=InnoDB COMMENT='관세청 월별 상세(총계행 제외) 294,174행(24개 HS6). 국가 전체 수입(민수 포함)';

-- 채우기 예시 (팀이 raw 적재·ref 적재 후 실행. 실행 전 ref_country가 상세행 stat_cd 238개를 모두 갖는지 확인)
-- name_ko는 HS10별 "가장 최근 연월(stat_ym)"의 품명. MAX(item_name_ko)는 문자열 정렬 최댓값이라 쓰지 않는다.
-- INSERT INTO dim_hs10 (hs10, hs6, name_ko)
--   SELECT hs_cd, LEFT(hs_cd,6), item_name_ko
--   FROM (SELECT hs_cd, item_name_ko,
--                ROW_NUMBER() OVER (PARTITION BY hs_cd ORDER BY stat_ym DESC, row_id DESC) AS rn
--         FROM raw_customs_trade WHERE is_total='0') t
--   WHERE rn = 1;
-- INSERT INTO fact_customs_monthly
--   (hs10, stat_cd, yyyymm, hs6, year, month, imp_dlr, exp_dlr, imp_wgt, exp_wgt, bal_payments, is_partial_year, raw_row_id)
--   SELECT hs_cd, stat_cd, CONCAT(LEFT(stat_ym,4), RIGHT(stat_ym,2)), LEFT(hs_cd,6),
--          CAST(LEFT(stat_ym,4) AS SIGNED), CAST(RIGHT(stat_ym,2) AS SIGNED),
--          CAST(imp_dlr AS SIGNED), CAST(exp_dlr AS SIGNED), CAST(imp_wgt AS SIGNED), CAST(exp_wgt AS SIGNED),
--          CAST(bal_payments AS SIGNED), IF(LEFT(stat_ym,4)='2026',1,0), row_id
--   FROM raw_customs_trade WHERE is_total='0';
-- 대조: SELECT COUNT(*) FROM fact_customs_monthly;  -- 294,174 기대(24개)
--       SELECT year, COUNT(*) FROM fact_customs_monthly GROUP BY year;  -- 2025 = 26,211 기대

-- =============================================================================
-- 5. clean_  정제 결과 (값은 사용자 정제 노트북이 채운다)
-- =============================================================================

-- 계약정보 정제. 한 행 = 계약번호 × 정규화 차수 → 43,111행.
-- 같은 키에 원본 2행이 있는 충돌 키(2024UMM1504-01, 1건)는 PK를 넓히지 않는다(넓히면 is_latest_seq=1 행이 둘이 되어 v_contract_monthly 건수·금액이 두 번 잡힘).
-- 규칙: raw에는 두 행 모두 보존, clean에는 대표 행 1개(raw_row_id 작은 쪽 등 정제 노트북이 정한 기준)만 넣고
--       seq_conflict_flag=1 + conflict_raw_row_ids에 나머지 원본 row_id, evidence에 선택 근거(어느 열이 달랐는지)를 기록한다.
CREATE TABLE clean_dapa_contract (
  contract_no             VARCHAR(20)  NOT NULL,
  contract_seq_norm       CHAR(2)      NOT NULL COMMENT '0 → 00 정규화',
  raw_row_id              BIGINT UNSIGNED NOT NULL COMMENT '→ raw_dapa_contract.row_id',
  contract_name           VARCHAR(500) NOT NULL,
  biz_type                ENUM('물품','용역') NOT NULL,
  contract_form_name      VARCHAR(50)  NULL,
  contract_method_name    VARCHAR(50)  NULL,
  joint_contract_yn       TINYINT(1)   NULL COMMENT '공동계약=1',
  contract_date           DATE         NOT NULL COMMENT '사건 연도 기준 열',
  period_start            DATE         NULL,
  period_end              DATE         NULL,
  period_anomaly_flag     TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '종료일 2525-01-16 류 이상치',
  contract_amount         BIGINT       NULL COMMENT '해당 차수 계약액(원)',
  total_contract_amount   BIGINT       NULL COMMENT '전체 계약액(원). 계약 단위 금액 = 최종 차수의 이 값',
  reserve_price           BIGINT       NULL,
  contract_org_name       VARCHAR(100) NULL,
  demand_org_name         VARCHAR(100) NULL,
  vendor_name             VARCHAR(200) NULL,
  vendor_biz_reg_no       CHAR(12)     NULL,
  vendor_address          VARCHAR(300) NULL COMMENT '계약업체 소재지',
  sido_code               CHAR(2)      NULL COMMENT 'ref_sido_map 적용 결과',
  contract_type           VARCHAR(50)  NULL,
  -- 이력
  is_latest_seq           TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '계약번호별 최종 차수 = 1 (집계 기준). 계약번호당 정확히 1행',
  seq_conflict_flag       TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '같은 키에 원본 여러 행 → 대표 행 1개만 적재하고 1로 표시',
  conflict_raw_row_ids    VARCHAR(100) NULL COMMENT 'seq_conflict_flag=1일 때 적재하지 않은 나머지 원본 row_id(쉼표 구분)',
  -- 분류(5분류·속성은 서로 독립. 근거 없으면 미확인)
  class5                  ENUM('방산 장비·부품 후보','정비·기술지원','일반 군수물자','일반 행정·운영','판단 보류') NOT NULL DEFAULT '판단 보류',
  is_electronic           ENUM('예','아니오','미확인') NOT NULL DEFAULT '미확인' COMMENT '전자 관련성',
  is_part                 ENUM('예','아니오','미확인') NOT NULL DEFAULT '미확인' COMMENT '부품 여부(완제품·전산장비·용역과 구분)',
  is_defense_related      ENUM('예','아니오','미확인') NOT NULL DEFAULT '미확인' COMMENT '방산 관련성',
  matched_keywords        VARCHAR(200) NULL COMMENT '후보 선정 키워드(후보일 뿐, 합산 금지)',
  evidence                TEXT         NULL COMMENT '분류 근거(검수 메모·출처)',
  review_status           ENUM('후보','검수완료','보류') NOT NULL DEFAULT '후보',
  -- 품목군 연결(품목군 수준만, ref_category_map contract_group)
  contract_group          VARCHAR(50)  NULL COMMENT '계약 후보 품목군명(정제에서 부여)',
  category                VARCHAR(20)  NULL COMMENT '대응된 HS category',
  category_link_status    ENUM('확정','후보','대응불가','미연결') NOT NULL DEFAULT '미연결',
  -- 국산화 상태(우선순위 아님, 두 열 독립)
  is_target_b1            ENUM('예','아니오','미확인') NOT NULL DEFAULT '미확인' COMMENT 'B1 KRIT 공고 대상',
  is_completed_b2         ENUM('예','아니오','미확인') NOT NULL DEFAULT '미확인' COMMENT 'B2 국산화개발품목(지상체계 한정)',
  domestic_mfg_status     ENUM('국내 제조 확인','미확인') NOT NULL DEFAULT '미확인' COMMENT '국내 주소·국내 납품은 근거 아님',
  cleaned_at              DATETIME     NULL,
  cleaned_by              VARCHAR(50)  NULL,
  PRIMARY KEY (contract_no, contract_seq_norm),
  UNIQUE KEY ux_cdc_raw (raw_row_id),
  KEY ix_cdc_date (contract_date, biz_type),
  KEY ix_cdc_class (class5, review_status),
  KEY ix_cdc_vendor (vendor_biz_reg_no),
  KEY ix_cdc_latest (is_latest_seq, contract_date),
  KEY ix_cdc_sido (sido_code),
  CONSTRAINT fk_cdc_raw FOREIGN KEY (raw_row_id) REFERENCES raw_dapa_contract (row_id)
) ENGINE=InnoDB COMMENT='계약정보 정제(차수 정규화·5분류·속성·국산화 상태)';

-- B2 정제: 완전 중복 제거 → 사업명×부품관리번호 고유 25,025행. dup_count로 원본 행 수 보존.
CREATE TABLE clean_dapa_localized_item (
  project_name          VARCHAR(100) NOT NULL,
  part_mgmt_no          VARCHAR(20)  NOT NULL,
  nsn                   VARCHAR(20)  NULL,
  fsc4                  CHAR(4)      NULL,
  fsc2                  CHAR(2)      NULL,
  item_name             VARCHAR(200) NULL,
  contractor_name       VARCHAR(200) NULL COMMENT '계약 상대(개발 주체 아님)',
  contractor_name_norm  VARCHAR(200) NULL COMMENT '업체명 정규화(연결률 보고용)',
  last_modified_date    DATE         NULL COMMENT '연도 축 사용 금지(스냅샷)',
  dup_count             SMALLINT     NOT NULL DEFAULT 1 COMMENT '원본 완전 중복 행 수',
  is_electronic_group   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'fsc2 IN (58,59)',
  category              VARCHAR(20)  NULL COMMENT 'ref_category_map(fsc4) 결과',
  category_link_status  ENUM('확정','후보','대응불가','조회표 전용') NOT NULL DEFAULT '조회표 전용'
                        COMMENT '5995/5935/5930/5998 등 화이트리스트 HS 대응 없는 FSC = 조회표 전용',
  first_raw_row_id      BIGINT UNSIGNED NULL COMMENT '대표 원본 행',
  cleaned_at            DATETIME     NULL,
  PRIMARY KEY (project_name, part_mgmt_no),
  KEY ix_cli_fsc (fsc4),
  KEY ix_cli_part (part_mgmt_no),
  KEY ix_cli_cat (category, category_link_status),
  KEY ix_cli_contractor (contractor_name_norm)
) ENGINE=InnoDB COMMENT='B2 국산화개발품목 정제 25,025행(사업×부품). 부품 수는 part_mgmt_no 고유 12,788';

-- B1 정제: 차수·공고유형·과제번호 단위. 같은 차수의 예비·본·재공고 합산 금지 → notice_type 포함 키.
CREATE TABLE clean_krit_task (
  round_id            VARCHAR(10)  NOT NULL COMMENT '예 26-1',
  notice_type         ENUM('예비','본공고','재공고','수정','미확인') NOT NULL DEFAULT '미확인',
  task_no             SMALLINT     NOT NULL,
  round_year          SMALLINT     NOT NULL,
  round_seq           TINYINT      NOT NULL,
  program_type        VARCHAR(30)  NULL COMMENT '핵심부품 / 수출연계 E/L / 전략부품 / 상생협력',
  task_name           VARCHAR(300) NOT NULL,
  gov_fund_100m_krw   DECIMAL(10,2) NULL COMMENT '정부지원 연구개발비(억원)',
  dev_period_months   SMALLINT     NULL,
  category            VARCHAR(20)  NULL COMMENT 'ref_category_map(krit_task) 결과',
  hs6                 CHAR(6)      NULL COMMENT '품목군 대응(근거 있을 때만)',
  category_link_status ENUM('확정','후보','대응불가','미연결') NOT NULL DEFAULT '미연결',
  is_counted          TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '같은 차수 중복 공고 중 집계에 쓰는 1건 = 1',
  raw_row_id          BIGINT UNSIGNED NULL COMMENT '→ raw_krit_task.row_id',
  source_file         VARCHAR(200) NULL,
  cleaned_at          DATETIME     NULL,
  PRIMARY KEY (round_id, notice_type, task_no),
  KEY ix_ckt_year (round_year),
  KEY ix_ckt_hs6 (hs6),
  KEY ix_ckt_raw (raw_row_id),
  CONSTRAINT fk_ckt_hs6 FOREIGN KEY (hs6)        REFERENCES ref_hs_whitelist (hs6),
  CONSTRAINT fk_ckt_raw FOREIGN KEY (raw_row_id) REFERENCES raw_krit_task (row_id)
) ENGINE=InnoDB COMMENT='B1 KRIT 국산화 대상 과제 정제(100건 안팎)';

-- 업체 마스터(사업자등록번호 있는 출처만: 계약정보·입찰결과). 업체 조회 탭용.
CREATE TABLE clean_company (
  biz_reg_no         CHAR(12)     NOT NULL,
  name_norm          VARCHAR(200) NOT NULL COMMENT '법인격 표기 제거·공백 정리',
  name_raw           VARCHAR(200) NOT NULL COMMENT '가장 많이 쓰인 원문',
  address            VARCHAR(300) NULL COMMENT '계약업체 소재지',
  sido_code          CHAR(2)      NULL,
  first_seen_source  ENUM('contract','bid_result') NOT NULL,
  PRIMARY KEY (biz_reg_no),
  KEY ix_cc_name (name_norm)
) ENGINE=InnoDB COMMENT='업체 마스터(사업자번호 기준)';

-- 사업자번호 없는 출처(B2 계약업체·방산업체 지정현황)의 업체명 → clean_company 연결 시도 기록.
-- 연결률·다중 일치를 보고한 뒤에만 화면에 사용(idea-review §4 업체 조회 탭 규칙).
CREATE TABLE clean_company_name_link (
  link_id      INT UNSIGNED NOT NULL AUTO_INCREMENT,
  source       ENUM('localized_item','defense_company') NOT NULL,
  name_raw     VARCHAR(200) NOT NULL,
  name_norm    VARCHAR(200) NOT NULL,
  biz_reg_no   CHAR(12)     NULL,
  match_type   ENUM('exact','multi','none') NOT NULL,
  match_count  SMALLINT     NOT NULL DEFAULT 0,
  note         VARCHAR(200) NULL,
  PRIMARY KEY (link_id),
  UNIQUE KEY ux_ccnl (source, name_raw),
  KEY ix_ccnl_biz (biz_reg_no),
  CONSTRAINT fk_ccnl_company FOREIGN KEY (biz_reg_no) REFERENCES clean_company (biz_reg_no)
) ENGINE=InnoDB COMMENT='업체명 연결 결과(연결률 보고용). match_type=none이면 biz_reg_no NULL';

-- A7 국외조달 조달계획 정제 — 판단번호 단위(원본 3,029 → 고유 3,024, 같은 판단번호 5쌍은 dup_count·충돌로 기록).
-- 전자 관련 후보(is_electronics_candidate)·검수 상태는 사용자 노트북이 채운다. 검수 전 값은 화면에서 "잠정" 라벨.
CREATE TABLE clean_dapa_overseas_plan (
  decision_no               VARCHAR(20)  NOT NULL,
  plan_year                 CHAR(4)      NOT NULL COMMENT '집행예정월 앞 4자리',
  plan_month                CHAR(7)      NULL     COMMENT 'YYYY-MM',
  rep_item_name             VARCHAR(500) NULL,
  exec_type                 VARCHAR(30)  NOT NULL,
  contract_method           VARCHAR(30)  NULL,
  exec_agency               VARCHAR(100) NULL,
  budget_krw                BIGINT       NOT NULL COMMENT '예산금액(원, 집행 예정액 — 실적 아님)',
  progress_status           VARCHAR(30)  NULL,
  is_contracted             TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'progress_status IN (계약, 부분계약)',
  is_electronics_candidate  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '대표품명 키워드 후보(검수 전)',
  electronics_review_status ENUM('미검수','확정','오탐','판단 보류') NOT NULL DEFAULT '미검수',
  system_family_hint        VARCHAR(30)  NULL COMMENT '레이더/통신/항법/전자광학/음탐 등 키워드 계열(품목군 대응 아님)',
  dup_count                 SMALLINT     NOT NULL DEFAULT 1 COMMENT '같은 판단번호 원본 행 수',
  has_conflict              TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '같은 판단번호에 다른 내용',
  first_raw_row_id          BIGINT UNSIGNED NULL,
  cleaned_at                DATETIME     NULL,
  PRIMARY KEY (decision_no),
  KEY ix_cop_year_type (plan_year, exec_type),
  KEY ix_cop_elec (is_electronics_candidate, electronics_review_status),
  CONSTRAINT fk_cop_raw FOREIGN KEY (first_raw_row_id) REFERENCES raw_dapa_overseas_plan (row_id)
) ENGINE=InnoDB COMMENT='A7 국외조달 조달계획 정제(판단번호 단위, 배경 ⓪)';

-- =============================================================================
-- 6. v_  집계 뷰 (시나리오 값 없음. 모든 무역 값은 "국가 전체 수입(민수 포함)")
-- =============================================================================

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
                              WHERE m.map_type = 'fsc4' AND m.hs6 = w.hs6 AND m.link_status = '확정') THEN '대응 미확정'
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
-- =============================================================================
-- 참고: 팀 확정 후 실행할 참조 데이터 갱신 예시 (idea-review §5 B2 규칙 ②)
-- UPDATE ref_hs_whitelist SET b2_scope = 'B2 범위 밖' WHERE hs6 IN ('841191','880730','901420');
-- UPDATE ref_hs_whitelist SET b2_scope = '대응 가능' WHERE b2_scope IS NULL AND category IN ('반도체','전자부품');
-- =============================================================================
