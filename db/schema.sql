-- =============================================================================
-- defense_dashboard 스키마 DDL (설계 문서: docs/db/schema-design.md, 관계도: docs/db/erd.md)
--
-- 대상: MariaDB 10.4+ / MySQL 8.0.16+ 양쪽에서 실행되는 문법만 사용
--       (운영 DB AWS RDS MySQL 8.4, 로컬 검증 MariaDB 12.2)
-- MySQL 8.4 에서 뷰를 만들 때는 SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci 를 먼저 둔다(기본 0900_ai_ci 와 콜레이션이 섞이면 비교가 실패한다).
-- 실행: mysql -h <호스트> -u <계정> -p --default-character-set=utf8mb4 < db/schema.sql
-- 용도: 최초 구축 · 빈 개발 DB 초기화 전용. 아래 DROP이 수작업 참조표(ref_sido_map)와
--       meta_ 기록까지 전부 지우므로 데이터가 들어간 DB에는 재실행하지 않는다.
--       데이터만 비우고 다시 적재할 때는 db/reset_data.sql(ref_·meta_dataset·meta_column_dict 보존) 사용.
-- 순서: 0 DB → 1 ref_ → 2 (원본 파일 계층 — DB 밖) → 3 meta_ → 4 dim_/fact_ → 5 clean_ → 6 v_ 뷰
--
-- 원칙
--   원본 파일: DB 에 넣지 않는다. data/raw/ 파일이 원본이며 scripts/load_db.py read_raw(<데이터셋 키>) 가
--            파일을 DataFrame 으로 읽는다(열명·헤더 대조는 db/column_dict.csv 의 raw_* 행 = 원본 파일 열 사전).
--            read_raw 의 row_id(파일명 정렬 × 행 순 파서 순번) 가 clean_*.raw_row_id 의 정의다. 원본 위치·크기·SHA-256·파서 건수는 meta_dataset.
--   clean_*: 정제 결과(형 변환·정규화·분류 속성). 값은 사용자 정제 노트북이 채운다.
--   fact_/dim_: 관세청 원본에서 규칙이 확정된 형 변환만 수행(총계행 제외·연월 파싱·HS6 파생).
--   v_*    : 집계 뷰. 시나리오(제한률) 값은 DB에 저장하지 않고 화면에서 계산한다.
--   meta_* : 출처 기록·단계별 건수·열 사전. 보고서 표를 SELECT로 뽑기 위한 것.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS defense_dashboard
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE defense_dashboard;

-- -----------------------------------------------------------------------------
-- 안전장치: 이미 데이터가 적재된 DB에서 이 파일을 실행하면 아래 DROP 전에 오류로 중단된다(전체 DROP 으로 적재 데이터가 지워지는 것을 막는다).
--   (ERD 도구에 "Import"할 때는 서버에 연결하지 말고 파일만 읽히거나, 빈 로컬 DB를 쓴다.)
--   정말 초기화하려면 ① 먼저 덤프(mysqldump)를 뜨고 ② 이 블록(SET @has_tbl … DEALLOCATE PREPARE guard2;)을 지운 뒤 실행한다.
--   중단 시 메시지: ERROR 1146 Table 'stop_schema_sql_db_has_data_remove_guard_to_force_reset' doesn't exist
-- -----------------------------------------------------------------------------
SET @has_tbl = (SELECT COUNT(*) FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'fact_customs_monthly');
SET @q = IF(@has_tbl = 1, 'SELECT COUNT(*) INTO @loaded_rows FROM defense_dashboard.fact_customs_monthly', 'SET @loaded_rows = 0');
PREPARE guard1 FROM @q; EXECUTE guard1; DEALLOCATE PREPARE guard1;
SET @q = IF(@loaded_rows > 0,
            'SELECT 1 FROM `STOP_schema_sql_DB_has_data_remove_guard_to_force_reset`',
            'SELECT ''schema.sql guard: DB is empty, continuing'' AS guard');
PREPARE guard2 FROM @q; EXECUTE guard2; DEALLOCATE PREPARE guard2;

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET FOREIGN_KEY_CHECKS = 0;

-- 재실행 가능하도록 역순 DROP (뷰 → clean/fact → meta → ref)
DROP VIEW IF EXISTS v_customs_region_gwacheon_year, v_contract_reason_group_yearly, v_defense_company_sector, v_overseas_contract_yearly, v_domestic_plan_yearly, v_overseas_bid_chain,
  v_bid_notice_result_link, v_bid_notice_monthly, v_bid_result_summary, v_contract_private_reason,
  v_kdsis_link_summary, v_b2_localized_kdsis, v_overseas_plan_api_kdsis, v_budget_rnd_yearly, v_overseas_plan_api_fsc, v_b2_fsg_summary, v_hs_whitelist_rule, v_hs6_candidate_vs_whitelist, v_hs6_candidate_rule, v_hsk_control_by_hs6, v_hs10_use_tag_all,
  v_civil_mix_rule, v_hs10_use_share,
  v_overseas_plan_yearly, v_contract_monthly, v_review_list, v_hhi_export_hs6_year, v_export_share_hs6_year, v_hhi_hs6_year, v_import_share_hs6_year, v_import_hs6_year;
DROP TABLE IF EXISTS clean_dapa_defense_company, clean_customs_region, clean_kosis_production_index, clean_kosis_utilization, clean_hsk_control, clean_openfiscal_program_link, clean_openfiscal_program_budget,
  clean_dapa_overseas_bid_result, clean_dapa_overseas_contract, clean_dapa_overseas_plan_api,
  clean_dapa_contract_exec_by_service, clean_dapa_domestic_plan, clean_dapa_bid_result, clean_dapa_bid_notice, clean_excluded_row,
  clean_kdsis_nsn, clean_dapa_overseas_plan, clean_company_name_link, clean_company, clean_krit_task, clean_dapa_localized_item, clean_dapa_contract;
DROP TABLE IF EXISTS fact_customs_monthly, dim_hs10;
DROP TABLE IF EXISTS meta_load_log, meta_column_dict, meta_dataset;
DROP TABLE IF EXISTS ref_semi_domestic_case, ref_semi_chip_type, ref_semi_market_share, ref_semi_policy_timeline, ref_semi_public_fab, ref_semi_strategy_task, ref_semi_stat;
DROP TABLE IF EXISTS ref_hs6_name, ref_hs_code_master, ref_equipment_alias, ref_hs_rule_flag, ref_hs_indicator, ref_fsg, ref_fsc, ref_sido_map, ref_country, ref_hs_whitelist;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- 1. ref_  참조표  (data/reference/*.csv 및 수작업 대응표)
-- =============================================================================

-- HS6 화이트리스트 24행. 수집·집계·사이드바 필터의 기준 테이블.
-- 원본: data/reference/hs_whitelist.csv (16열: 기본 8열 + 정의 열 3개 + civil_mix 3열 + evidence_basis·evidence_note)
-- civil_mix 3열은 v_civil_mix_rule(정량 지표 → 규칙 도출)의 스냅샷이다. 값을 손으로 고치지 않는다.
-- evidence 3열(evidence·evidence_basis·evidence_note)은 v_hs6_candidate_rule(관세청 HSK 마스터·전략물자 HSK 연계표 규칙 도출)의 스냅샷(rule 19 · 팀판단 5, 미해당 5개는 priority 3).
-- 분석 대상 = priority IN (1, 2) 13개(진입식 R1 OR R2, R4 제외 — R3∧R4로만 진입했던 6개는 priority 3). evidence_basis 는 근거 도출 방식이지 분석 대상 여부가 아니다.
CREATE TABLE ref_hs_whitelist (
  hs6        CHAR(6)      NOT NULL COMMENT 'HS 6단위 코드(원본 hs_code)',
  hs_level   TINYINT      NOT NULL DEFAULT 6,
  category   VARCHAR(20)  NOT NULL COMMENT '반도체 / 전자부품 / 소재장비(배경, 기본 필터 제외)',
  name_ko    VARCHAR(100) NOT NULL,
  name_en    VARCHAR(200) NOT NULL,
  rationale  TEXT         NULL,
  priority   TINYINT      NOT NULL COMMENT '1~3. 1·2 = 분석 대상 13개(진입 R1 OR R2, 2026-09-21 M5) / 3 = 규칙 미해당 11개(09-16 팀판단 5 + 09-21 R4 제외 6, 화면 ''분석 제외'')',
  axis       ENUM('import','export','both') NOT NULL,
  system_family  VARCHAR(30)  NULL COMMENT '무기체계 계열(반도체/레이더/통신/통신·레이더 부분품/항법/전자광학/항공전자/AI연산/소재장비) — 2026-09-15 추가',
  defense_use_ko VARCHAR(300) NULL COMMENT '국방 용도 1문장(팀 판단, 공식 분류 아님)',
  evidence       VARCHAR(120) NULL COMMENT '근거 키. 규칙 도출 후: HSK-군용;HSK-항공/항행;전략물자-ML;전략물자-DU;B2-FSC (v_hs6_candidate_rule.evidence_rule 스냅샷). 도출 전(09-15 팀 판단): A6;B2-FSC;KRIT;A7;팀판단 — docs/reference/hs-whitelist-definition.md §8',
  evidence_basis ENUM('rule','팀판단') NOT NULL DEFAULT '팀판단' COMMENT 'evidence를 정한 방식: rule=공식 자료(관세청 HSK 마스터·전략물자 HSK 연계표) 규칙 도출, 팀판단=09-15 기획 단계 판단 — 2026-09-16 추가',
  evidence_note  VARCHAR(300) NULL COMMENT '규칙 근거 수치 요약(예: HSK10 11개 중 군용전용 1 / 통제 HSK 5개(ML 2) / B2 부품 27). 원값은 v_hs6_candidate_rule',
  civil_mix      ENUM('높음','중간','낮음') NULL COMMENT '민수 혼합 정도 — v_civil_mix_rule 규칙 도출값 스냅샷(2026-09-16). 정량 지표 없는 품목군은 NULL(판단불가). 09-15 팀 판단 라벨은 폐기',
  civil_mix_basis ENUM('hs10','hsk','판단불가') NOT NULL DEFAULT '판단불가' COMMENT 'civil_mix를 정한 지표 종류: hs10=관세청 HS10 용도 세분류 수입 비중, hsk=전략물자 HSK 연계표(적재 후), 판단불가=정량 경로 없음',
  civil_mix_note VARCHAR(200) NULL COMMENT '근거 수치 요약(예: 군용전용 HS10 0.026% 2021~2025). ref_hs_indicator에 원값',
  PRIMARY KEY (hs6),
  KEY ix_hs_category (category, priority)
) ENGINE=InnoDB COMMENT='HS6 화이트리스트 24개 — 품목군 기준표(원본 16열: 8열 + 2026-09-15 정의 열 3개 + civil_mix 3열 + evidence_basis·evidence_note — related_fsc·b2_scope 는 09-21 삭제)';

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

-- 주소 첫 토큰 → 17개 시도 정규화(보조 ⑤ choropleth). 수작업.
CREATE TABLE ref_sido_map (
  token      VARCHAR(30) NOT NULL COMMENT '주소 첫 토큰 원문(서울/서울특별시/서울시 …)',
  sido_code  CHAR(2)     NOT NULL COMMENT '행정표준코드 앞 2자리(11 서울 … 50 제주)',
  sido_name  VARCHAR(20) NOT NULL COMMENT '표준 시도명',
  PRIMARY KEY (token),
  KEY ix_sido_code (sido_code)
) ENGINE=InnoDB COMMENT='대표업체주소 첫 토큰 → 시도';

-- FSC(군급분류) 4자리 라벨. B2 히트맵·조회표·국외 조달계획 API 라벨용.
--   시드: 군급분류집(15119907) 756행 중 FSG 그룹행(끝 00) 80을 뺀 676행.
CREATE TABLE ref_fsc (
  fsc4                 CHAR(4)      NOT NULL,
  fsc2                 CHAR(2)      NOT NULL,
  name_ko              VARCHAR(200) NULL COMMENT '명칭(한글), 군급분류집 최대 104자',
  name_en              VARCHAR(200) NULL COMMENT '명칭(영문)',
  status               CHAR(1)      NULL COMMENT '군급상태 A 유효 / C 폐지 (군급분류집)',
  is_electronic_group  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '58xx·59xx·60xx = 1 (기본 필터. 60 광섬유는 2026-09-19 추가, alter_2026-09-19_p3_clean.sql §5)',
  PRIMARY KEY (fsc4),
  KEY ix_fsc2 (fsc2)
) ENGINE=InnoDB COMMENT='FSC 군급분류 4자리 라벨 676행(군급분류집 15119907, 2026-09-16 시드)';

-- FSG(군급 2자리) 라벨. 시드는 db/seed_ref.sql(load_db.py --ref).
--   원본 data/reference/fsg_master.csv 80행 = DLA FSG 표 77행 + 95·96·99 보완(GSA PSC Manual 2025-04). 4자리 라벨 ref_fsc는 군급분류집(15119907)에서 시드.
CREATE TABLE ref_fsg (
  fsg_code             CHAR(2)      NOT NULL COMMENT 'FSG 2자리 = FSC 앞 2자리',
  name_en              VARCHAR(200) NOT NULL,
  name_ko              VARCHAR(100) NOT NULL COMMENT '팀원 번역(원 파일 fsg_name_ko)',
  status               CHAR(1)      NOT NULL DEFAULT 'A' COMMENT '원 파일 status(전부 A)',
  is_historical        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '21·33 = 파일 유지 목적 Historical FSG(신규 품목 추가 불가)',
  is_electronic_group  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '58·59·60 = 1 (ref_fsc.is_electronic_group과 같은 기준, 핵심 ② 기본 필터. 60 광섬유는 2026-09-19 추가)',
  note_ko              VARCHAR(300) NULL,
  source_url           VARCHAR(300) NULL COMMENT '원 파일: DLA ZSMT_FSG.txt / 보완 3행: GSA PSC Manual 2025-04 xlsx',
  PRIMARY KEY (fsg_code)
) ENGINE=InnoDB COMMENT='FSG 군급 2자리 라벨 80행 (data/reference/fsg_master.csv). 4자리 라벨 ref_fsc는 군급분류집 시드(2026-09-16)';

-- 적용장비명 표기 통일 사전. 한 행 = 원문 1종. 843행은 notebooks/03_clean_overseas.ipynb §2가 채운다.
--    name_norm 은 기계적 정규화(판단 아님). name_std 는 같은 정규화 키에 원문이 2종 이상 모여 표기 변이가 실제로 관측된 묶음에만 채우고(link_status='후보'),
--    변이 근거가 없는 원문은 name_std NULL + link_status='미확인' 으로 둔다(근거 없는 판단 값 대신 NULL).
--    장비코드로는 묶지 않는다(같은 장비가 파생형별로 코드 여러 개).
CREATE TABLE ref_equipment_alias (
  name_raw            VARCHAR(100) COLLATE utf8mb4_bin NOT NULL COMMENT '적용장비명 원문(raw_dapa_overseas_plan_api.equipment_name). utf8mb4_bin — 기본 콜레이션(unicode_ci)에서는 서로 다른 원문 2종이 같은 키로 취급돼 적재가 막힘(2026-09-19 실측)',
  name_norm           VARCHAR(100) NOT NULL COMMENT '기계적 정규화(NFKC·공백 제거·대괄호→소괄호·대문자). 판단 없음',
  variant_key         VARCHAR(100) NOT NULL COMMENT 'name_norm 에 표기 변이 규칙(레이다→레이더 등)을 더한 묶음 키 — 잠정',
  name_std            VARCHAR(100) NULL COMMENT '표준명(잠정). 같은 variant_key 에 원문 2종 이상일 때 최빈 원문. 근거 없으면 NULL',
  variant_group_size  SMALLINT     NOT NULL DEFAULT 1 COMMENT '같은 variant_key 를 공유하는 원문 종수',
  row_count           INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '이 원문이 나온 raw 행 수',
  elec_row_count      INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '그중 fsg2 IN (58,59,60) 행 수',
  code_count          SMALLINT     NOT NULL DEFAULT 0 COMMENT '이 원문에 붙은 장비코드 고유 수(코드로 묶지 않는 근거)',
  in_elec_scope       TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '전자·통신 건에 나오는 원문 = 1 (명세가 먼저 통일하라고 한 범위)',
  link_status         ENUM('후보','확정','미확인') NOT NULL DEFAULT '미확인' COMMENT '후보 = 자동 매핑(검수 전) / 확정 = 사람이 확인 / 미확인 = 표준명 없음',
  basis               VARCHAR(300) NULL COMMENT '매핑 근거(규칙 이름·검수자 메모)',
  decided_at          DATETIME     NULL COMMENT '확정 시점',
  PRIMARY KEY (name_raw),
  KEY ix_rea_key (variant_key),
  KEY ix_rea_std (name_std),
  KEY ix_rea_status (link_status, in_elec_scope)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='적용장비명 원문 → 표준명 사전(잠정). 자동 매핑은 link_status=후보, 근거 없으면 name_std NULL';

-- 품목군별 정량 지표. 한 행 = HS6 × 지표 × 기간. "팀판단" 라벨을 대체하는 수치의 원본 저장소.
--   axis='civil_mix'          : 민수 혼합 — mil_hs10_share(군용 전용 HS10 수입 비중, 하한선) · aero_hs10_share(항공기용, 민항 포함) ·
--                               auto_hs10_share(자동차용) · hsk_control_hs10_ratio / hsk_control_imp_share(전략물자 HSK 연계표)
--   axis='defense_relevance'  : (카테고리 맵을 두지 않아 현재 쓰지 않음 — ENUM 값만 남음) ·
--                               a7_plan_count / a7_plan_budget(국외조달 조달계획, 사용자 키워드 검수 후) · krit_task_count(clean_krit_task 적재 후)
--   값은 v_hs10_use_share에서 INSERT…SELECT로 채우고, 산식은 method에 남긴다.
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

-- HS6 규칙 판정 스냅샷. R1~R4를 전부 계산해 두고 노트북·화면이 DB에서 읽어 쓴다.
--   한 행 = HS6(84·85·88·90류, 마스터·dim_hs10·연계표에 등장하는 것 전부) × rule_version. v_hs6_candidate_rule을 그대로 물질화한 것이라
--   원본 3개(HS 마스터·HS6 명칭·HSK 연계표)가 없는 DB에서도 읽을 수 있다.
--   진입 규칙은 R1 OR R2 — is_candidate_provisional은 잠정식 R1 OR R2 OR (R3∧R4)의 참고값(스냅샷 불변).
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
  hs6_name_src              ENUM('06시트','10시트단일','없음') NOT NULL DEFAULT '없음'
                            COMMENT 'hs6_name_ko 출처(2026-09-19 P1): 06시트=단위별 품목명 HS6 행, 10시트단일=6단위 행이 없고 10자리 자식이 1개뿐이라 그 이름을 쓴 경우, 없음=공식 명칭 미확인. 실측 509 / 489 / 5',
  PRIMARY KEY (hs6, rule_version),
  KEY ix_hrf_flags (rule_version, r1_mil, r2_aero_nav, r3_du, r4_b2),
  KEY ix_hrf_hs2 (hs2)
) ENGINE=InnoDB COMMENT='HS6별 선정 규칙 R1~R4 판정·근거 수치 스냅샷(84·85·88·90류 전체). 진입식은 2026-09-21 M5로 R1 OR R2 확정(is_candidate_provisional은 09-16 잠정식 참고값)';

-- 관세청 HS 기준표 2종(원본 파일에서 load_db.py --ref 가 만든다)
CREATE TABLE ref_hs_code_master (
  hs10         CHAR(10)     NOT NULL COMMENT 'HSK 10자리(2026-01-01 현행)',
  name_ko      VARCHAR(500) NULL COMMENT '한글품목명(관세청 HS부호 마스터 15049722)',
  name_en      VARCHAR(600) NULL COMMENT '영문품목명',
  apply_start  DATE         NULL COMMENT '적용시작일자',
  apply_end    DATE         NULL COMMENT '적용종료일자(현행 코드는 전부 2026-12-31)',
  PRIMARY KEY (hs10),
  KEY ix_rhcm_hs6 (hs10(6))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='관세청 HS부호 마스터(15049722) 중 2026 현행 HSK10 11,327행 — 화면 HS10 품명 라벨 · dim_hs10 보강 · v_hs10_use_tag_all(선정 규칙 R1·R2). 원본 파일 raw_hs_code_master 12,469행(7~9자리 1,142 · 규격/단위 열은 사용처 없어 제외)';

CREATE TABLE ref_hs6_name (
  hs6      CHAR(6)      NOT NULL COMMENT 'HS 6자리',
  name_ko  VARCHAR(700) NULL COMMENT '한글품목명(관세청 HS부호 단위별 품목명 15130660, HS6 시트)',
  name_en  VARCHAR(800) NULL COMMENT '영문품목명',
  PRIMARY KEY (hs6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='HS6 공식 명칭 2,254행 — v_hs6_candidate_rule R2 용도어 · ref_hs_rule_flag.hs6_name_ko. 원본 파일 raw_hs_unit_name 5시트 17,072행 중 06시트 6자리만(5자리 중간 수준 1,024 제외, 10시트 11,327은 ref_hs_code_master 와 코드·품명 동일)';

-- 국방반도체 발전전략 참조표 7개. data/reference/semi_*.csv 를 load_db.py --ref 로 적재.
-- 배경 화면 반도체 구역 전용 — 관세청 수입액과 합산·비교하지 않는다. related_hs6 는 참고 표시(연결 키 아님).
CREATE TABLE ref_semi_chip_type (
  type_no          TINYINT UNSIGNED NOT NULL COMMENT '국방반도체 7대 유형 번호(참고9)',
  name_ko          VARCHAR(50)  NOT NULL,
  summary          VARCHAR(200) NOT NULL COMMENT '유형 개요(참고9 요약)',
  material_process VARCHAR(50)  NOT NULL COMMENT '소재·공정(화합물·실리콘 등)',
  example_devices  VARCHAR(100) NOT NULL,
  related_hs6      VARCHAR(60)  NULL COMMENT '팀이 붙인 참고 HS6(세미콜론 구분). 수입액 연결 키 아님',
  hs_basis         VARCHAR(10)  NOT NULL COMMENT 'related_hs6 근거. team = 팀 표시',
  source           VARCHAR(100) NOT NULL,
  PRIMARY KEY (type_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국방반도체 7대 유형(발전전략 참고9) 7행';

CREATE TABLE ref_semi_domestic_case (
  case_no        SMALLINT UNSIGNED NOT NULL,
  type_no        TINYINT UNSIGNED  NOT NULL COMMENT 'ref_semi_chip_type.type_no',
  org            VARCHAR(60)  NOT NULL COMMENT '기관·기업(공동이면 · 로 연결)',
  title          VARCHAR(150) NOT NULL,
  event_date     VARCHAR(10)  NULL COMMENT '원본 date — 발표·보도일(YYYY-MM-DD 또는 YYYY-MM). 미기재 NULL',
  target_system  VARCHAR(80)  NULL COMMENT '적용 대상 체계(기사 표현)',
  stage          VARCHAR(30)  NOT NULL COMMENT '양산 · 개발 착수 등 기사 표현',
  source_title   VARCHAR(50)  NOT NULL,
  source_url     VARCHAR(255) NOT NULL,
  verify_level   VARCHAR(20)  NOT NULL COMMENT '기사 원문 · 보도자료 등 확인 수준',
  note           VARCHAR(120) NULL,
  dapa_2025_task TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1 = 방위사업청 2025 국방반도체 핵심기술 과제(2025-05-19 보도자료)',
  PRIMARY KEY (case_no),
  KEY ix_rsdc_type (type_no),
  CONSTRAINT fk_rsdc_type FOREIGN KEY (type_no) REFERENCES ref_semi_chip_type (type_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국방반도체 국내 개발 사례(보도·기사) 13행';

CREATE TABLE ref_semi_market_share (
  country   VARCHAR(20)  NOT NULL,
  segment   VARCHAR(20)  NOT NULL COMMENT 'IDM · 파운드리 · 팹리스 등',
  share_pct DECIMAL(5,1) NOT NULL COMMENT '점유율(%) — 참고3 막대그래프에서 읽은 값',
  source    VARCHAR(100) NOT NULL,
  caveat    VARCHAR(100) NOT NULL COMMENT '원출처·기준연도 미표기 등 한계',
  PRIMARY KEY (country, segment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국가별 반도체 공급망 점유율(발전전략 참고3 인용) 16행';

CREATE TABLE ref_semi_policy_timeline (
  row_no       SMALLINT UNSIGNED NOT NULL COMMENT 'CSV 행 순서(시간순, 1부터)',
  event_date   VARCHAR(10)  NOT NULL COMMENT '원본 date — YYYY · YYYY-MM · YYYY-MM-DD',
  category     VARCHAR(10)  NOT NULL,
  event        VARCHAR(100) NOT NULL,
  detail       VARCHAR(150) NOT NULL,
  source_title VARCHAR(100) NOT NULL,
  source_url   VARCHAR(255) NULL,
  verify_level VARCHAR(20)  NOT NULL,
  PRIMARY KEY (row_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국방반도체 발전전략 추진 경과 12행';

CREATE TABLE ref_semi_public_fab (
  fab_no      TINYINT UNSIGNED NOT NULL,
  name_ko     VARCHAR(40)  NOT NULL,
  abbr        VARCHAR(10)  NULL,
  parent_org  VARCHAR(30)  NULL,
  ministry    VARCHAR(10)  NOT NULL COMMENT '소관 부처',
  field       VARCHAR(60)  NOT NULL,
  field_group VARCHAR(10)  NOT NULL COMMENT '실리콘 · 화합물 등',
  city        VARCHAR(10)  NOT NULL,
  lat         DECIMAL(9,6) NOT NULL COMMENT '도시 단위 근사 좌표',
  lon         DECIMAL(9,6) NOT NULL,
  coord_basis VARCHAR(10)  NOT NULL COMMENT 'approx = 도시 단위 근사',
  source      VARCHAR(100) NOT NULL,
  PRIMARY KEY (fab_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='공공 나노팹(발전전략 참고10) 14행';

CREATE TABLE ref_semi_strategy_task (
  task_no        TINYINT UNSIGNED NOT NULL,
  direction_no   TINYINT UNSIGNED NOT NULL,
  direction_key  VARCHAR(10)  NOT NULL,
  direction_name VARCHAR(60)  NOT NULL,
  sub_no         TINYINT UNSIGNED NOT NULL,
  task_name      VARCHAR(80)  NOT NULL,
  source         VARCHAR(100) NOT NULL,
  PRIMARY KEY (task_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국방반도체 발전전략 4방향 12과제(본문 17-3) 12행';

CREATE TABLE ref_semi_stat (
  stat_key  VARCHAR(40)  NOT NULL,
  label     VARCHAR(60)  NOT NULL,
  value_num DECIMAL(6,1) NOT NULL,
  unit_txt  VARCHAR(20)  NOT NULL COMMENT '% · % 이상(하한) 등 원문 단위 표현',
  note      VARCHAR(200) NOT NULL,
  source    VARCHAR(100) NOT NULL,
  PRIMARY KEY (stat_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국방반도체 발전전략 본문 인용 수치 2행(팀 계산값 아님)';

-- =============================================================================
-- 2. 원본 파일 계층 — DB 밖 (원본은 파일로, DB 는 정제·기준·뷰만)
-- =============================================================================
-- RDS 에 raw_ 표는 없다. 원본은 data/raw/(gitignore, 읽기 전용) 파일이며
-- scripts/load_db.py 의 RAW_TABLES(원본 파일 데이터셋 키 raw_… 23종 — 옛 표 이름을 그대로 물려받음) + read_raw(키) 가 파서 순번
-- row_id 를 붙여 DataFrame 으로 읽는다. 데이터셋별 파일·인코딩·건수·SHA-256 은 meta_dataset(db/meta_dataset.csv), 원본 열 사전은
-- db/column_dict.csv 의 raw_* 행(319, table_dict.csv kind=file). 정제 노트북(notebooks/clean_*.ipynb)과 --fact/--ref 가 이 경로로 읽는다.
-- 원본 → DB 대응: raw_customs_trade → dim_hs10·fact_customs_monthly / raw_customs_region → clean_customs_region /
--   raw_hs_code_master → ref_hs_code_master(10자리만) / raw_hs_unit_name → ref_hs6_name(06시트 6자리만) / 나머지 → clean_* 1:1(이름 규칙 raw_X → clean_X).
--   raw_customs_progress(수집 기록)·raw_dapa_fsc_catalog(ref_fsc 시드)는 파일로만 둔다.

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
  dtype          VARCHAR(100)  NOT NULL COMMENT '설계 타입(raw는 문자열). ENUM 전체 표기를 위해 2026-09-19 50→100',
  description    VARCHAR(300) NULL,
  PRIMARY KEY (table_name, column_name),
  UNIQUE KEY ux_mcd_ord (table_name, ordinal)
) ENGINE=InnoDB COMMENT='원본 열명 ↔ DB 열명 사전';

-- =============================================================================
-- 4. dim_ / fact_  관세청 정형 (규칙 확정: 총계행 제외 · YYYY.MM 파싱 · hs6 = LEFT(hs10,6))
-- =============================================================================

-- 현행 마스터 열 4개: 관세청 HS부호 마스터(15049722, 2026-01-01 현행) 10자리 11,327행과 hs10 로 조인.
--   실측 211행 중 현행 107 / 마스터없음 104(과거 연도에만 있던 이력 코드 — 값을 추정하지 않고 NULL).
--   name_ko(관세청 statKor)는 그대로 둔다 — v_hs10_use_tag_all·v_hs10_use_share 가 이 열을 읽는다.
CREATE TABLE dim_hs10 (
  hs10                CHAR(10)     NOT NULL,
  hs6                 CHAR(6)      NOT NULL,
  name_ko             VARCHAR(300) NULL COMMENT '관세청 statKor(코드당 최근 값)',
  master_name_ko      VARCHAR(500) NULL COMMENT '관세청 HS부호 마스터(15049722, 2026 현행)의 한글품목명. 마스터에 없는 이력 코드는 NULL',
  apply_start         DATE         NULL COMMENT '마스터 적용시작일자. 코드가 언제부터 쓰였는지',
  apply_end           DATE         NULL COMMENT '마스터 적용종료일자(현행 코드는 전부 2026-12-31)',
  master_link_status  ENUM('현행','마스터없음') NOT NULL DEFAULT '마스터없음' COMMENT '2026 현행 마스터에 같은 HS10 이 있으면 현행, 없으면 마스터없음(과거 연도에만 존재한 이력 코드)',
  PRIMARY KEY (hs10),
  KEY ix_dh_hs6 (hs6),
  CONSTRAINT fk_dh_hs6 FOREIGN KEY (hs6) REFERENCES ref_hs_whitelist (hs6)
) ENGINE=InnoDB COMMENT='HS10 → HS6 · 품명 · 현행 마스터 대조';

-- 한 행 = HS10 × 국가 × 월 (총계행 제외). 기대 건수: 294,174(화이트리스트 24개). 2025 단독 26,211.
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
  PRIMARY KEY (hs10, stat_cd, yyyymm),
  KEY ix_fcm_hs6_year (hs6, year, stat_cd),
  KEY ix_fcm_cnty_year (stat_cd, year),
  KEY ix_fcm_ym (yyyymm),
  CONSTRAINT fk_fcm_hs6  FOREIGN KEY (hs6)        REFERENCES ref_hs_whitelist (hs6),
  CONSTRAINT fk_fcm_cnty FOREIGN KEY (stat_cd)    REFERENCES ref_country (stat_cd),
  CONSTRAINT fk_fcm_hs10 FOREIGN KEY (hs10)       REFERENCES dim_hs10 (hs10)
) ENGINE=InnoDB COMMENT='관세청 월별 상세(총계행 제외) 294,174행(24개 HS6). 국가 전체 수입(민수 포함)';

-- 채우기: scripts/load_db.py --fact — read_raw('raw_customs_trade')(원본 파일) → build_customs_dim_fact(pandas) → INSERT.
--   규칙: 총계행(is_total='1') 제외 · hs6 = LEFT(hs10,6) · yyyymm = 'YYYY.MM' → 'YYYYMM' · 2026 = is_partial_year 1
--   dim_hs10.name_ko 는 HS10 별 "가장 최근 연월(stat_ym)"의 품명(동률이면 파서 순번 큰 쪽). MAX(item_name_ko)는 문자열 정렬 최댓값이라 쓰지 않는다.
--   실행 전 ref_country 가 상세행 stat_cd 238개를, ref_hs_whitelist 가 hs6 24개를 모두 갖는지 스크립트가 확인한다.
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
  raw_row_id              BIGINT UNSIGNED NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_contract.row_id)',
  contract_name           VARCHAR(500) NOT NULL,
  biz_type                ENUM('물품','용역') NOT NULL,
  contract_method_name    VARCHAR(50)  NULL,
  contract_date           DATE         NOT NULL COMMENT '사건 연도 기준 열',
  period_start            DATE         NULL,
  period_end              DATE         NULL,
  period_anomaly_flag     TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '종료일 2525-01-16 류 이상치',
  contract_amount         BIGINT       NULL COMMENT '해당 차수 계약액(원)',
  total_contract_amount   BIGINT       NULL COMMENT '전체 계약액(원). 계약 단위 금액 = 최종 차수의 이 값',
  reserve_price           BIGINT       NULL,
  contract_org_name       VARCHAR(100) NULL,
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
  -- 국산화 상태(우선순위 아님, 두 열 독립)
  is_target_b1            ENUM('예','아니오','미확인') NOT NULL DEFAULT '미확인' COMMENT 'B1 KRIT 공고 대상',
  is_completed_b2         ENUM('예','아니오','미확인') NOT NULL DEFAULT '미확인' COMMENT 'B2 국산화개발품목(지상체계 한정)',
  domestic_mfg_status     ENUM('국내 제조 확인','미확인') NOT NULL DEFAULT '미확인' COMMENT '국내 주소·국내 납품은 근거 아님',
  cleaned_at              DATETIME     NULL,
  cleaned_by              VARCHAR(50)  NULL,
  private_contract_reason VARCHAR(500) NULL COMMENT '수의계약사유 원문(raw private_contract_reason, 공란은 NULL). v_contract_private_reason 원천. 같은 계약번호 안에서 전 차수 동일(실측 충돌 0). 2026-09-19 alter_2026-09-19_views_to_clean.sql §1',
  PRIMARY KEY (contract_no, contract_seq_norm),
  UNIQUE KEY ux_cdc_raw (raw_row_id),
  KEY ix_cdc_date (contract_date, biz_type),
  KEY ix_cdc_class (class5, review_status),
  KEY ix_cdc_vendor (vendor_biz_reg_no),
  KEY ix_cdc_latest (is_latest_seq, contract_date),
  KEY ix_cdc_sido (sido_code)
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
  is_electronic_group   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'fsc2 IN (58,59,60) = 1. 전자 여부 속성(기본 필터), 기준 확정 2026-09-21(M4). 60은 2026-09-21 기준 통일(해당 행 0)',
  first_raw_row_id      BIGINT UNSIGNED NULL COMMENT '대표 원본 행의 파서 순번(read_raw)',
  cleaned_at            DATETIME     NULL,
  PRIMARY KEY (project_name, part_mgmt_no),
  KEY ix_cli_fsc (fsc4),
  KEY ix_cli_part (part_mgmt_no),
  KEY ix_cli_contractor (contractor_name_norm)
) ENGINE=InnoDB COMMENT='B2 국산화개발품목 정제 25,025행(사업×부품). 부품 수는 part_mgmt_no 고유 12,788';

-- B1 정제: 차수·공고유형·과제번호 단위. 같은 차수의 예비·본·재공고 합산 금지 → notice_type 포함 키 + is_latest.
-- 원문 순번(raw task_seq)은 표(구분)마다 1부터 다시 시작해 PK 로 쓸 수 없다
-- (그대로 쓰면 30행 충돌, 24-1차 예비는 숫자도 아님) → task_no 는 (round_id, notice_type) 안에서 raw row_id 순으로 재부여하고
-- 원문은 task_seq_text 에 보존한다. 금액 단위도 차수마다 달라(억 / 억원 / 백만원 / 없음) gov_fund_text·gov_fund_unit_text 를 함께 남긴다.
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
  is_counted          TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '같은 차수 중복 공고 중 집계에 쓰는 1건 = 1',
  raw_row_id          BIGINT UNSIGNED NULL COMMENT '원본 파일 파서 순번(read_raw raw_krit_task.row_id)',
  source_file         VARCHAR(200) NULL,
  cleaned_at          DATETIME     NULL,
  task_seq_text       VARCHAR(10)  NULL COMMENT 'raw task_seq 원문(표 안 순번. 24-1차 예비는 구분값 핵심/수출)',
  gov_fund_text       VARCHAR(30)  NULL COMMENT 'raw gov_fund_text 원문(14.64억 / 10.35억원 / 1,657)',
  gov_fund_unit_text  VARCHAR(30)  NULL COMMENT '원본 헤더가 밝힌 금액 단위(억 45 / 억원 20 / 백만원 20 / 없음 11). extra_json[원본열명] 근거',
  dev_period_text     VARCHAR(30)  NULL COMMENT 'raw dev_period_text 원문(36개월 / 36)',
  note                VARCHAR(300) NULL COMMENT 'raw note 원문(비고). 자리표시 - · 는 NULL',
  notice_order        TINYINT      NOT NULL DEFAULT 0 COMMENT '공고 진행 순서 예비1<본공고2<수정3<재공고4 (잠정 규칙, is_latest 계산용)',
  is_latest           TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '같은 차수·같은 과제명 중 최신 공고 1행 = 1(73행). 차수별 과제 수는 이 열로만 센다',
  dup_task_row_count  SMALLINT     NOT NULL DEFAULT 1 COMMENT '같은 (round_id, task_name) raw 행 수(예비+본공고 등)',
  cleaned_by          VARCHAR(50)  NULL COMMENT '정제 담당(CURRENT_USER)',
  PRIMARY KEY (round_id, notice_type, task_no),
  KEY ix_ckt_year (round_year),
  KEY ix_ckt_raw (raw_row_id)
) ENGINE=InnoDB COMMENT='B1 KRIT 국산화 대상 과제 정제(raw 96행 1:1. 차수별 과제 수는 is_latest=1 로 센다 — 예비·본·재공고 합산 금지)';


-- 열린재정 방위사업청 일반회계 세부사업 예산 정제. 원본 2,860행 1:1, 제외 0.
-- 뺀 raw 열: No.·소관명·회계명·계정명(전부 공란)·분야명·부문명(각 1값)·source_*. 금액은 천원(_krw_k) + 억원(_100m_krw) 두 벌.
-- 배경 ④ 전용 — 관세청 수입액(달러·실적)·조달계획(원·집행 예정)과 합산·비율 금지.
CREATE TABLE clean_openfiscal_program_budget (
  raw_row_id              BIGINT UNSIGNED NOT NULL COMMENT 'PK. 원본 파일 파서 순번(read_raw raw_openfiscal_program_budget.row_id, 원본 1:1)',
  fiscal_year             SMALLINT        NOT NULL COMMENT '회계연도 2016~2027(편성 연도. 사건 날짜 아님)',
  program_name            VARCHAR(100)    NOT NULL COMMENT '프로그램명(2018년 국방연구개발사업 → 방위사업정책지원으로 바뀜 — 기준축 아님)',
  unit_program_name       VARCHAR(100)    NOT NULL COMMENT '단위사업명. 시계열 대표 축은 국방기술개발',
  sub_program_name        VARCHAR(200)    NOT NULL COMMENT '세부사업명(원문). 2021·2023 개편이 있어 연도 간 직접 비교 금지',
  sub_program_key         VARCHAR(200)    NOT NULL COMMENT '세부사업명 표기 정규화 키(공백·(R&D)·(방사청) 제거). 원문 674종 → 키 606종',
  sub_program_first_year  SMALLINT        NOT NULL COMMENT '이 sub_program_key 가 자료에 처음 나온 회계연도',
  sub_program_last_year   SMALLINT        NOT NULL COMMENT '이 sub_program_key 가 자료에 마지막으로 나온 회계연도',
  gov_plan_krw_k          BIGINT          NOT NULL COMMENT '정부안금액(천원). 원본 쉼표 문자열 → 숫자',
  gov_plan_100m_krw       DECIMAL(18,5)   NOT NULL COMMENT '정부안금액(억원) = 천원 ÷ 100,000',
  confirmed_krw_k         BIGINT          NOT NULL COMMENT '국회확정금액(천원). 2027은 전부 0 = 미확정(is_unconfirmed)',
  confirmed_100m_krw      DECIMAL(18,5)   NOT NULL COMMENT '국회확정금액(억원)',
  amount_basis            ENUM('확정','정부안') NOT NULL COMMENT '그 회계연도 확정액 합이 0이면 정부안. v_budget_rnd_yearly 와 같은 규칙',
  is_unconfirmed          TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 국회확정 전(2027 268행). 확정액 0을 0원으로 읽지 말 것',
  is_unit_tech_dev        TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 단위사업 국방기술개발(93행, ⑤ 탭 대표 시계열)',
  budget_group_candidate  VARCHAR(20)     NULL COMMENT '⑤ 탭 예산 3선 키워드 후보: 국방반도체 1 / 부품국산화 7 / 국방기술개발 85. 확정 분류 아님, 합산 금지',
  budget_group_basis      VARCHAR(200)    NULL COMMENT '후보값을 붙인 근거(어느 열의 어떤 패턴에 걸렸는지)',
  cleaned_at              DATETIME        NULL,
  cleaned_by              VARCHAR(50)     NULL,
  PRIMARY KEY (raw_row_id),
  KEY ix_copb_year_unit (fiscal_year, unit_program_name(50)),
  KEY ix_copb_key (sub_program_key(100), fiscal_year),
  KEY ix_copb_group (budget_group_candidate, fiscal_year)
) ENGINE=InnoDB COMMENT='열린재정 방위사업청 세부사업 예산 정제 2,860행(2016~2027). 배경 ④ 전용 — 관세청 수입액·조달계획과 합산·비율 금지';


-- 세부사업명 개편 연결표. 공식 개편 고시를 확인한 것이 아니라 근거 없는 1:1 연결을 만들지 않는다.
-- 확정 9 = 표기 차이만(같은 단위사업·정규화 키). 후보 5 = 국방기술개발 안에서 연도 인접(핵심기술개발 → 2023 3분할 등, candidate_count>1이면 1:1 불가).
-- 미확인 8 = 짝 없는 신설. 다른 단위사업의 승계는 후보 쌍이 1,028개라 넣지 않고 budget 표의 first/last_year 로만 읽는다.
CREATE TABLE clean_openfiscal_program_link (
  link_id                INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  program_name           VARCHAR(100)  NOT NULL COMMENT '프로그램명(참고)',
  unit_program_name      VARCHAR(100)  NOT NULL COMMENT '단위사업명(연결을 찾은 범위. 상위 합계 축)',
  from_sub_program_name  VARCHAR(200)  NULL COMMENT '바뀌기 전 세부사업명(신설이면 NULL)',
  from_last_year         SMALLINT      NULL COMMENT '바뀌기 전 이름의 마지막 회계연도',
  to_sub_program_name    VARCHAR(200)  NULL COMMENT '바뀐 뒤 세부사업명(종료면 NULL)',
  to_first_year          SMALLINT      NULL COMMENT '바뀐 뒤 이름의 첫 회계연도',
  link_type              ENUM('표기변경','승계 후보','신설','종료') NOT NULL COMMENT '연결 유형',
  link_status            ENUM('확정','후보','미확인') NOT NULL DEFAULT '미확인' COMMENT '표기변경만 확정. 승계는 후보, 짝 없으면 미확인',
  candidate_count        SMALLINT      NOT NULL DEFAULT 0 COMMENT '같은 from 에 대한 to 후보 수(>1이면 1:1 연결 불가)',
  link_basis             VARCHAR(300)  NULL COMMENT '판정 근거(정규화 키 동일 / 연도 인접 / 연도 범위 겹침 등)',
  created_at             DATETIME      NULL,
  created_by             VARCHAR(50)   NULL,
  PRIMARY KEY (link_id),
  KEY ix_copl_unit (unit_program_name(50), link_status),
  KEY ix_copl_from (from_sub_program_name(80)),
  KEY ix_copl_to (to_sub_program_name(80))
) ENGINE=InnoDB COMMENT='열린재정 세부사업명 개편 연결표(2021·2023 개편). 확정=표기 차이만, 승계는 후보 — 공식 근거 없음';

-- HSK 연계표 세로형.
-- raw_hsk_control 2,161행은 HSK10 1행 + 통제번호 쉼표 목록(최대 1,218자) 구조라 통제번호 단위 집계를 못 한다 → 1행 = HSK10 × 통제번호 1개.
-- 행이 늘어난 것은 원본 규모가 아니다: 원본 건수는 HSK10 2,161개이고 이 표의 행 수(실측 10,104)는 「통제번호 부여 건수」다.
-- 통제번호 체계(대외무역법 §19 → 전략물자수출입고시): 첫 글자 = 부(0~9), 둘째 글자 = 그룹(A~E). ML(별표3 군용물자)은 이 자료에 0건 — 「자료에 없음」.
CREATE TABLE clean_hsk_control (
  hsk_ctrl_id     INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  raw_row_id      BIGINT UNSIGNED NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_hsk_control.row_id) (1 raw 행 = N 통제번호)',
  hsk10           CHAR(10)        NOT NULL COMMENT '품목번호 HSK 10자리(원본 전 행 숫자 10자리, 고유 2,161)',
  hs6             CHAR(6)         NOT NULL COMMENT 'LEFT(hsk10,6) — ref_hs_whitelist.hs6 조인 키(FK 없음: 화이트리스트 밖 HS6 도 들어온다)',
  hs2             CHAR(2)         NOT NULL COMMENT 'LEFT(hsk10,2) 류',
  name_ko         VARCHAR(300)    NULL COMMENT '품명(국문) — raw 값 그대로, HSK10 단위라 같은 값이 여러 행에 반복된다',
  control_no      VARCHAR(40)     NOT NULL COMMENT '통제번호 1개(원본 목록에서 잘라내 앞뒤 공백만 제거한 값, 예 3A001.a.1.)',
  control_no_norm VARCHAR(40)     NOT NULL COMMENT '대문자 + 끝 마침표 제거(예 3A001.A.1). 중복 판정·조인용',
  regime          ENUM('이중용도','군용물자') NOT NULL DEFAULT '이중용도' COMMENT '별표2 이중용도 / 별표3 군용물자(ML). 현재 자료는 전부 이중용도',
  part_no         TINYINT         NULL COMMENT '부 0~9(통제번호 첫 글자). ML 은 NULL',
  part_name_ko    VARCHAR(30)     NULL COMMENT '부 이름(0 원자력전용 / 1 특수재질 / 2 재료가공 / 3 전자 / 4 컴퓨터 / 5 통신·정보보안 / 6 센서·레이저 / 7 항법·항공전자 / 8 해양 / 9 항공우주·추진)',
  group_code      CHAR(1)         NULL COMMENT '그룹 A~E(A 시스템·장비 / B 시험·생산장비 / C 재료 / D 소프트웨어 / E 기술)',
  is_du_elec      TINYINT(1)      NOT NULL DEFAULT 0 COMMENT 'part_no IN (3,5,6,7) = 1 — R3 전략물자-DU 가 쓰는 부 집합',
  seq_in_row      SMALLINT        NOT NULL DEFAULT 1 COMMENT '원본 control_no 목록 안 순번(1부터). 원본 위치 추적용',
  cleaned_at      DATETIME        NULL,
  cleaned_by      VARCHAR(50)     NULL,
  PRIMARY KEY (hsk_ctrl_id),
  UNIQUE KEY ux_chc_pair (hsk10, control_no_norm),
  KEY ix_chc_raw (raw_row_id),
  KEY ix_chc_hs6 (hs6, is_du_elec),
  KEY ix_chc_part (part_no, group_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='HSK 연계표 세로형(1행 = HSK10 × 통제번호 1개). 원본 규모는 HSK10 2,161개이고 이 표의 행 수는 통제번호 부여 건수다. ML(군용물자)은 자료에 없음';

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
-- 연결률·다중 일치를 보고한 뒤에만 화면에 사용.
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
  KEY ix_cop_elec (is_electronics_candidate, electronics_review_status)
) ENGINE=InnoDB COMMENT='A7 국외조달 조달계획 정제(판단번호 단위, 배경 ⓪)';

-- KDSIS NSN 파생 표 — 원본 파일 raw_kdsis_nsn 에서 채운다.
-- 2-1 NSN 기본정보: NSN별 1행. 원본에서 NSN이 같으면 아래 속성이 모두 같았다(pandas 검증, 속성 불일치 NSN 0) → 대표 행 = row_id 최소 행.
--     그래도 has_attr_conflict 로 재검증한다(속성 조합이 2개 이상인 NSN = 1).
CREATE TABLE clean_kdsis_nsn (
  nsn                 VARCHAR(20)  NOT NULL,
  nsn_format          ENUM('숫자13','검토') NOT NULL COMMENT '숫자13 = ^[0-9]{13}$ (135,331). 검토 = 그 외(533: NIIN 영문 포함 13자·NIIN 없는 4자)',
  review_note         VARCHAR(50)  NULL COMMENT '검토 사유(nsn_format=검토일 때)',
  fsc4                VARCHAR(4)   NULL COMMENT '군급 4자리',
  fsg2                VARCHAR(2)   NULL COMMENT '군급 앞 2자리(ref_fsg 조인)',
  is_electronic_group TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'fsg2 IN (58,59,60) = 1, 기준 확정 2026-09-21(M4). 60은 2026-09-21 추가(317행)',
  ncb_code            VARCHAR(4)   NULL,
  niin                VARCHAR(10)  NULL COMMENT 'NCB 2자 + 일련번호 7자 = NSN 뒤 9자리. ncb_code·iin_serial 모두 공란이면 NULL(빈 문자열 아님, 2026-09-20)',
  niin_status         VARCHAR(2)   NULL,
  inc                 VARCHAR(10)  NULL,
  item_div_code       VARCHAR(4)   NULL,
  item_name_en        VARCHAR(150) NULL,
  item_name_ko        VARCHAR(50)  NULL,
  mfr_item_name_en    VARCHAR(120) NULL,
  mfr_item_name_ko    VARCHAR(80)  NULL,
  assigned_date       DATE         NULL COMMENT 'YYYY-MM-DD 형식일 때만, 아니면 NULL',
  oid                 VARCHAR(40)  NULL,
  raw_row_count       INT UNSIGNED NOT NULL COMMENT '이 NSN의 raw 행 수',
  ref_count           INT UNSIGNED NOT NULL COMMENT 'CAGE×참조번호 고유 수(적재 시 raw에서 집계; 상세 표 clean_kdsis_nsn_ref는 2026-09-19 삭제)',
  cage_count          INT UNSIGNED NOT NULL COMMENT 'CAGE 고유 수(공란 제외)',
  origin_files        VARCHAR(100) NULL COMMENT '나온 원본 파일 목록',
  has_attr_conflict   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '같은 NSN에 기본정보 조합이 2개 이상이면 1(기대 0)',
  first_raw_row_id    BIGINT UNSIGNED NOT NULL COMMENT '대표 원본 행의 파서 순번(read_raw, row_id 최소)',
  cleaned_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (nsn),
  KEY ix_ckn_fsc (fsc4),
  KEY ix_ckn_fmt (nsn_format),
  KEY ix_ckn_niin (niin)
) ENGINE=InnoDB COMMENT='KDSIS NSN 기본정보 — NSN별 1행 135,864(숫자13 135,331 + 검토 533). 조회·연결 키 전용';

-- 국내조달 clean 4개 + 제외 행 공용 표.
-- 적재는 정제 노트북(04_clean_domestic). 열 밀림·중복 등 clean 으로 옮기지 않은 원본 행은 clean_excluded_row 에 사유 코드로 남긴다(검산 원본 = clean + excluded).
CREATE TABLE clean_excluded_row (
  excl_id      INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  table_name   VARCHAR(64)      NOT NULL COMMENT '제외 대상 raw 테이블명(예 raw_dapa_bid_notice)',
  raw_row_id   BIGINT UNSIGNED  NOT NULL COMMENT '제외한 원본 행의 파서 순번(read_raw <table_name>.row_id)',
  reason_code  ENUM('DUP_EXACT','COL_SHIFT','PLACEHOLDER','OUT_OF_SCOPE','KEY_CONFLICT','OTHER') NOT NULL COMMENT '명세 §1-2 사유 코드',
  note         VARCHAR(300)     NULL COMMENT '어느 열이 어떻게 잘못됐는지',
  excluded_by  VARCHAR(50)      NULL,
  excluded_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (excl_id),
  UNIQUE KEY ux_cer_row (table_name, raw_row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='clean 전환에서 제외한 raw 행과 사유(전 담당 공용). 검산 raw = clean + excluded 의 근거';

CREATE TABLE clean_dapa_bid_notice (
  ref_notice_no                VARCHAR(30)      NOT NULL COMMENT '참조공고번호(실제 키)',
  ref_notice_seq_norm          CHAR(2)          NOT NULL COMMENT '참조공고차수 2자리 정규화(0→00)',
  raw_row_id                   BIGINT UNSIGNED  NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_bid_notice.row_id)',
  bid_notice_no                VARCHAR(20)      NOT NULL COMMENT '입찰공고번호(연도 미포함·비유일 — 입찰결과와 맞추는 키)',
  bid_notice_seq_norm          CHAR(2)          NOT NULL COMMENT '입찰공고차수 2자리 정규화',
  bid_notice_name              VARCHAR(500)     NOT NULL,
  bid_notice_status            VARCHAR(20)      NULL COMMENT '긴급/정상/재공고/취소/정정/연기 (표준값, ENUM 아님)',
  bid_notice_date              DATE             NOT NULL COMMENT '사건 연도 기준 열',
  biz_type                     VARCHAR(20)      NULL COMMENT '물품/용역',
  contract_form_name           VARCHAR(50)      NULL,
  contract_method_name         VARCHAR(50)      NULL,
  award_method_name            VARCHAR(50)      NULL,
  notice_org_name              VARCHAR(100)     NULL,
  notice_org_code              VARCHAR(20)      NULL,
  notice_org_dept_name         VARCHAR(100)     NULL,
  demand_org_name              VARCHAR(100)     NULL,
  demand_org_code              VARCHAR(20)      NULL,
  demand_org_dept_name         VARCHAR(100)     NULL,
  qualification_deadline_date  DATE             NULL COMMENT '시각은 raw 참조',
  bid_deadline_date            DATE             NULL COMMENT '시각은 raw 참조',
  opening_date                 DATE             NULL COMMENT '시각은 raw 참조',
  budget_amount_krw            BIGINT           NULL COMMENT '예산금액(원). 공고 예산 — 낙찰·계약액 아님',
  allocated_budget_amount_krw  BIGINT           NULL COMMENT '배정예산(설계금액, 원)',
  license_limit_group_count    TINYINT          NOT NULL DEFAULT 0 COMMENT '공종및면허제한그룹1~8 중 비공란 수',
  license_limit_groups         VARCHAR(2500)    NULL COMMENT '그룹1~8을 세로줄( | )로 결합(원문은 raw)',
  bid_notice_url               VARCHAR(300)     NULL,
  cleaned_at                   DATETIME         NULL,
  cleaned_by                   VARCHAR(50)      NULL,
  PRIMARY KEY (ref_notice_no, ref_notice_seq_norm),
  UNIQUE KEY ux_cbn_raw (raw_row_id),
  KEY ix_cbn_date (bid_notice_date, bid_notice_status),
  KEY ix_cbn_notice (bid_notice_no, bid_notice_seq_norm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국내조달 입찰공고 정제(참조공고번호+차수 단위, 열 밀림 2행 제외 → 10,840 기대). 담당자명 제외';

CREATE TABLE clean_dapa_bid_result (
  bid_notice_no            VARCHAR(20)      NOT NULL,
  bid_notice_seq_norm      CHAR(2)          NOT NULL COMMENT '차수 2자리 정규화',
  result_seq               TINYINT          NOT NULL DEFAULT 1 COMMENT '같은 키 안 row_id 순 1..n (중복 키 행 보존)',
  raw_row_id               BIGINT UNSIGNED  NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_bid_result.row_id)',
  key_row_count            SMALLINT         NOT NULL DEFAULT 1 COMMENT '같은 (공고번호, 차수) raw 행 수',
  dup_kind                 ENUM('단일','복수 낙찰','결과 상이','동일 결과 반복','미확인') NOT NULL DEFAULT '단일' COMMENT '중복 키 성격(2026-09-18 실측: 결과 상이 73키·복수 낙찰 108키·동일 결과 반복 18키 = 199키). 단일 = 키당 1행',
  is_key_representative    TINYINT(1)       NOT NULL DEFAULT 1 COMMENT '키당 1행 = 1 (키 기준 집계, v_bid_result_summary 키 수와 대조)',
  bid_notice_name          VARCHAR(500)     NULL,
  biz_type                 VARCHAR(20)      NULL COMMENT '물품/용역',
  contract_form_name       VARCHAR(50)      NULL,
  contract_method_name     VARCHAR(50)      NULL,
  award_method_name        VARCHAR(50)      NULL,
  qualification_review_yn  TINYINT(1)       NULL COMMENT 'Y=1',
  notice_org_name          VARCHAR(100)     NULL,
  notice_org_code          VARCHAR(20)      NULL,
  demand_org_name          VARCHAR(100)     NULL,
  demand_org_code          VARCHAR(20)      NULL,
  award_lower_limit_rate   DECIMAL(7,3)     NULL COMMENT '%',
  reserve_price_krw        BIGINT           NULL COMMENT '원',
  base_amount_krw          BIGINT           NULL COMMENT '원',
  estimated_price_krw      BIGINT           NULL COMMENT '원',
  opening_date             DATE             NOT NULL COMMENT '사건 연도 기준 열',
  opening_result           ENUM('유찰','개찰완료','순위확정') NOT NULL COMMENT '개찰결과구분(열 밀림 2행은 clean_excluded_row)',
  is_awarded               TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '최종낙찰금액 있음 = 1',
  final_award_amount_krw   BIGINT           NULL COMMENT '원. 낙찰금액 ≠ 계약금액',
  final_award_rate         DECIMAL(7,3)     NULL COMMENT '%',
  final_award_date         DATE             NULL,
  winner_name              VARCHAR(200)     NULL,
  winner_biz_reg_no        CHAR(12)         NULL COMMENT 'XXX-XX-XXXXX → clean_company 연결 키',
  winner_address           VARCHAR(300)     NULL COMMENT '낙찰업체 소재지(생산시설·납품 위치 아님)',
  winner_sido_code         CHAR(2)          NULL COMMENT 'ref_sido_map 적용 결과',
  notice_link_status       ENUM('1:1','다중','미연결') NOT NULL DEFAULT '미연결' COMMENT '공고번호+차수로 clean_dapa_bid_notice 대조한 상태(행 단위 조인은 하지 않음)',
  cleaned_at               DATETIME         NULL,
  cleaned_by               VARCHAR(50)      NULL,
  PRIMARY KEY (bid_notice_no, bid_notice_seq_norm, result_seq),
  UNIQUE KEY ux_cbr_raw (raw_row_id),
  KEY ix_cbr_open (opening_date, opening_result),
  KEY ix_cbr_winner (winner_biz_reg_no),
  KEY ix_cbr_rep (is_key_representative, opening_result)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국내조달 입찰결과 정제(공고번호+차수+결과순번, 열 밀림 2행 제외 → 7,403 기대). 중복 키 199는 행 보존·dup_kind 로 구분. 대표자·담당자명 제외';

CREATE TABLE clean_dapa_domestic_plan (
  raw_row_id          BIGINT UNSIGNED  NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_domestic_plan.row_id) (PK — 판단번호 고유성 미확인)',
  decision_no         VARCHAR(20)      NULL COMMENT '판단번호(고유이면 후속 alter 로 UNIQUE)',
  decision_row_count  SMALLINT         NOT NULL DEFAULT 1 COMMENT '같은 판단번호 raw 행 수',
  plan_month          DATE             NOT NULL COMMENT '집행예정월 YYYY-MM-01',
  plan_year           CHAR(4)          NOT NULL,
  is_partial_year     TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '2024 = 1 (4,545행, 불완전 연도)',
  rep_item_name       VARCHAR(500)     NULL,
  exec_type           VARCHAR(30)      NOT NULL COMMENT '표준값(구매/제조/제조/구매/기타/공사/리스/공급)',
  contract_method     VARCHAR(30)      NULL,
  exec_agency         VARCHAR(100)     NULL,
  budget_krw          BIGINT           NULL COMMENT '예산금액(원, 집행 예정액 — 실적 아님). NULL = 원본 미기재(4,965행), 0 아님',
  progress_status     VARCHAR(30)      NULL,
  is_contracted       TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'progress_status = 계약완료 (2025 24,013 기대)',
  cleaned_at          DATETIME         NULL,
  cleaned_by          VARCHAR(50)      NULL,
  is_budget_approx    TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'raw budget_amount 가 지수 표기(1.71528E+12, 유효숫자 6자리)라 budget_krw 가 근사값 = 1 (11행 기대). 합계에 억 원 단위 오차 가능. 2026-09-19 alter_2026-09-19_views_to_clean.sql §1',
  PRIMARY KEY (raw_row_id),
  KEY ix_cdp_month_type (plan_month, exec_type),
  KEY ix_cdp_decision (decision_no),
  KEY ix_cdp_year (plan_year, is_contracted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국내조달 조달계획 정제(raw 1:1, 35,859 기대). 판단번호 고유성 확인 후 UNIQUE 추가 검토. 담당자·연락처 열 없음. 예산은 집행 예정액 — 관세청 수입액과 합산·비교 금지';

CREATE TABLE clean_dapa_contract_exec_by_service (
  year                      SMALLINT         NOT NULL COMMENT '2015~2024',
  service_branch            ENUM('육군','해군','공군','국직') NOT NULL COMMENT '표준값',
  contract_amount_100m_krw  DECIMAL(14,1)    NOT NULL COMMENT '계약금액(억원)',
  raw_row_id                BIGINT UNSIGNED  NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_contract_exec_by_service.row_id)',
  cleaned_at                DATETIME         NULL,
  cleaned_by                VARCHAR(50)      NULL,
  PRIMARY KEY (year, service_branch),
  UNIQUE KEY ux_ces_raw (raw_row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='군별 계약집행 현황 정제(연도×군, 40행 기대). KPI 배경 — 조달 금액 ≠ 방산 매출';

-- 국외조달 clean 3개.
-- 적재는 notebooks/03_clean_overseas.ipynb. 제외 행 0(열 밀림·키 충돌 없음)이라 원본 = clean 이 그대로 검산이다.
-- §1 clean_dapa_overseas_plan_api — 국외 조달계획 OpenAPI 품목 단위(raw 13,615).
--    키: (procure_demand_no, item_seq) 는 원본에서 고유 13,615 → PK. 품목순번 공란 842행은 빈 문자열 + is_item_seq_missing=1.
--    NSN: stock_no 13자 중 숫자13 9,970 · 영숫자13 3,266(NCB 37 국내 부여) → nsn 채움. 나머지 379행(13자 1 + 13자 아님 378, NSN·NSN001 같은 자리표시 포함)은 nsn NULL.
--    is_elec = fsg2 IN ('58','59','60'). 13자 기준 2,267행.
--    금액: budget_amount·unit_price 는 통화 미검증(원화 혼입 의심) → DECIMAL 로 담되 amount_unverified=1 고정, 합산 금지.
--    제외 열: org_name·org_code·purchase_request_no·qa_grade·standard_no·component_no 는 내부 행정 코드라 clean 에 두지 않는다.
CREATE TABLE clean_dapa_overseas_plan_api (
  procure_demand_no    VARCHAR(20)      NOT NULL COMMENT '조달요구번호 prcureDemandNo (PK 1)',
  item_seq             VARCHAR(10)      NOT NULL DEFAULT '' COMMENT '품목순번 iemNo (PK 2). 원본 공란 842행은 빈 문자열',
  raw_row_id           BIGINT UNSIGNED  NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_overseas_plan_api.row_id)',
  is_item_seq_missing  TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '품목순번 원본 공란 = 1',
  demand_year          SMALLINT         NOT NULL COMMENT '요구연도(_demandYear_req). 2018 1건·2020 11건은 원자료 공백 구간 — 추세에서 제외',
  army_name_raw        VARCHAR(20)      NULL COMMENT '소요군·부대명 원문 armySe',
  army_std             ENUM('육군','해군','공군','해병대','국직','미확인') NOT NULL DEFAULT '미확인' COMMENT '군 표준값. 부대명이 국방부 직할로 확인되면 국직, 확인 불가는 미확인',
  army_code            VARCHAR(4)       NULL COMMENT 'armySeCode',
  function_name        VARCHAR(30)      NULL COMMENT '기능구분 fnctSe(항공/함정/공병/기동/방공/화력/통신(건전지) …)',
  function_code        VARCHAR(4)       NULL COMMENT 'fnctSeCode',
  item_kind_name       VARCHAR(20)      NULL COMMENT '품목종류구분 prdlstKndSe',
  item_kind_code       VARCHAR(4)       NULL COMMENT 'prdlstKndSeCode',
  item_name            VARCHAR(200)     NULL COMMENT '품명 prdlstNm',
  stock_no_raw         VARCHAR(20)      NOT NULL COMMENT '재고번호 원문 invntryNo(정제하지 않은 값)',
  nsn                  VARCHAR(13)      NULL COMMENT '13자 재고번호일 때만. 하이픈 없음 — clean_kdsis_nsn.nsn 과 같은 형식',
  nsn_format           ENUM('숫자13','영숫자13','자리표시','기타') NOT NULL DEFAULT '기타' COMMENT '숫자13 9,970 · 영숫자13 3,266(NCB 37) · 자리표시 NSN/N-A/TBD/0 류 · 기타 나머지',
  is_placeholder_nsn   TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'NSN·NSN001·NSN-01 같은 자리표시 = 1 (명세 §4-1)',
  fsc4                 CHAR(4)          NULL COMMENT 'nsn 앞 4자리(ref_fsc 조인). HS6 대응은 만들지 않는다',
  fsg2                 CHAR(2)          NULL COMMENT 'nsn 앞 2자리(ref_fsg 조인)',
  is_elec              TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'fsg2 IN (58,59,60) = 1 — 전자·통신·광섬유',
  kdsis_link_status    ENUM('연결','미연결','대상아님') NOT NULL DEFAULT '대상아님' COMMENT 'nsn exact → clean_kdsis_nsn.nsn. nsn 이 NULL 이면 대상아님',
  equipment_code       VARCHAR(20)      NULL COMMENT '적용장비코드 eqpmnCode. 파생형마다 달라 코드로 묶지 않는다(명세 §4-3)',
  equipment_name       VARCHAR(100)     NULL COMMENT '적용장비명 원문 eqpmnNm',
  equipment_name_norm  VARCHAR(100)     NULL COMMENT '기계적 정규화 결과(NFKC·공백 제거·대괄호→소괄호·대문자)',
  equipment_name_std   VARCHAR(100)     NULL COMMENT '표준명(ref_equipment_alias.name_std). 근거 없는 항목은 NULL',
  is_equipment_missing TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '적용장비명이 공란 또는 * = 1 (원본 2,018행)',
  quantity             INT              NULL COMMENT '수량 qy(정수)',
  unit                 VARCHAR(10)      NULL COMMENT '단위 unit',
  budget_amount_num    DECIMAL(18,2)    NULL COMMENT '예산금액 budgetAmount 숫자형 — 통화 미검증, 집계 금지',
  unit_price_num       DECIMAL(18,2)    NULL COMMENT '단가 untpc 숫자형 — 통화 미검증, 집계 금지',
  amount_unverified    TINYINT(1)       NOT NULL DEFAULT 1 COMMENT '1 = 통화 미검증이라 합계·비교에 쓰지 않음(현재 전 행 1)',
  progress_status      VARCHAR(20)      NULL COMMENT '진행상태 progrsSttus',
  is_contracted        TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'progress_status IN (계약, 부분계약) = 1',
  cleaned_at           DATETIME         NULL,
  cleaned_by           VARCHAR(50)      NULL,
  PRIMARY KEY (procure_demand_no, item_seq),
  UNIQUE KEY ux_copa_raw (raw_row_id),
  KEY ix_copa_year (demand_year, is_elec),
  KEY ix_copa_fsc (fsc4),
  KEY ix_copa_nsn (nsn),
  KEY ix_copa_eq (equipment_name_std)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국외 조달계획 OpenAPI 품목 단위 정제(조달요구번호+품목순번, 13,615 기대). 금액은 통화 미검증 — 건수만 사용. 파일판 clean_dapa_overseas_plan 과 조인·합산 금지';

-- §3 clean_dapa_overseas_contract — 국외조달 계약정보(원본 6,333). 계약번호 고유 6,333 → PK.
--    계약기간은 단일 패턴(완결 5,602 + 종료일 없음 731) → period_start/period_end + is_open_ended.
--    제외 열: contract_org_officer_name(개인정보), 그리고 단일값 3열(계약기관구분명·계약기관명·수요기관구분명·수요기관명 = 전부 '국가기관'/'방위사업청')은 정보가 없어 두지 않는다.
--    금액·국가 열이 원본에 없다. vendor_name 으로 국가를 추정하지 않는다.
CREATE TABLE clean_dapa_overseas_contract (
  contract_no             VARCHAR(20)      NOT NULL COMMENT '계약번호(PK, raw 고유 6,333)',
  raw_row_id              BIGINT UNSIGNED  NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_overseas_contract.row_id)',
  contract_name           VARCHAR(500)     NULL COMMENT '계약명',
  contract_form_name      VARCHAR(50)      NULL COMMENT '계약체결형태명(총액제/단가제(최저가)/내역입찰(최저가)/리스입찰 …)',
  contract_method_name    VARCHAR(50)      NULL COMMENT '계약체결방법명',
  contract_date           DATE             NOT NULL COMMENT '계약체결일자(사건 연도 기준 열, 2017-02-01~2025-12-31)',
  contract_year           SMALLINT         NOT NULL COMMENT '계약체결 연도',
  period_start            DATE             NULL COMMENT '계약기간 시작(원문 YYYY-MM-DD~YYYY-MM-DD)',
  period_end              DATE             NULL COMMENT '계약기간 종료. 원문에 종료일이 없으면 NULL',
  is_open_ended           TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '계약기간 종료일이 원문에 없음 = 1 (731행)',
  contract_org_dept_name  VARCHAR(100)     NULL COMMENT '계약기관담당부서명(담당자명은 제외)',
  vendor_name             VARCHAR(200)     NULL COMMENT '대표업체명(외국 업체). 업체명으로 국가를 추정하지 않는다',
  cleaned_at              DATETIME         NULL,
  cleaned_by              VARCHAR(50)      NULL,
  PRIMARY KEY (contract_no),
  UNIQUE KEY ux_coc_raw (raw_row_id),
  KEY ix_coc_date (contract_date),
  KEY ix_coc_vendor (vendor_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국외조달 계약정보 정제(계약번호 단위, 6,333 기대). 금액·국가 열 없음 — 건수·업체 수만. 담당자명 제외';

-- §4 clean_dapa_overseas_bid_result — 국외조달 입찰결과(원본 2,494). 업무 식별자만으로는 고유하지 않다(실측:
--    공고번호 고유 14 · 판단번호 고유 97 · 판단번호+항목번호 1,362) → PK 는 raw_row_id, 고유 조합 (공고번호, 판단번호, 항목번호, 개찰일시) 2,494 는 UNIQUE 로만 건다.
--    개찰일시 2025-03-27 ~ 2025-09-15 = 부분연도 → is_partial_year=1 고정. 연간 유찰률로 표현하지 않는다.
--    예산금액은 원본이 달러 표기라 budget_amount_usd 로 두되 A7 원화(clean_dapa_overseas_plan.budget_krw)와 합산하지 않는다.
CREATE TABLE clean_dapa_overseas_bid_result (
  raw_row_id         BIGINT UNSIGNED  NOT NULL COMMENT '원본 파일 파서 순번(read_raw raw_dapa_overseas_bid_result.row_id) (PK — 업무 식별자 단독 고유성 없음)',
  bid_notice_no      VARCHAR(20)      NULL COMMENT '공고번호 원문(예 EHG0001-1 = 공고번호-차수)',
  notice_no_base     VARCHAR(20)      NULL COMMENT '공고번호에서 - 앞부분',
  notice_seq         VARCHAR(4)       NULL COMMENT '공고번호에서 - 뒷부분(차수)',
  decision_no        VARCHAR(20)      NULL COMMENT '판단번호(파일판 raw_dapa_overseas_plan 과 공유, 계약정보에는 없음)',
  item_seq           VARCHAR(6)       NULL COMMENT '항목번호',
  bid_item_name      VARCHAR(500)     NULL COMMENT '입찰건명',
  opening_at         DATETIME         NULL COMMENT '개찰일시(원문 YYYY-MM-DD HH:MM)',
  opening_date       DATE             NULL COMMENT '개찰일',
  opening_ym         CHAR(7)          NULL COMMENT '개찰 연월 YYYY-MM',
  is_partial_year    TINYINT(1)       NOT NULL DEFAULT 1 COMMENT '2025-03~09 부분연도 = 1 (전 행). 연간 지표로 쓰지 않는다',
  bid_result_std     ENUM('낙찰','유찰','미확인') NOT NULL DEFAULT '미확인' COMMENT '입찰결과 표준값',
  is_awarded         TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'bid_result_std = 낙찰 이면 1',
  budget_amount_usd  DECIMAL(18,2)    NULL COMMENT '예산금액(달러 표기). A7 원화 예산과 합산 금지',
  plan_link_status   ENUM('연결','미연결') NOT NULL DEFAULT '미연결' COMMENT '판단번호가 raw_dapa_overseas_plan 에 있으면 연결(판단번호 97 중 83 교집합)',
  cleaned_at         DATETIME         NULL,
  cleaned_by         VARCHAR(50)      NULL,
  PRIMARY KEY (raw_row_id),
  UNIQUE KEY ux_cobr_key (bid_notice_no, decision_no, item_seq, opening_at),
  KEY ix_cobr_result (bid_result_std, opening_date),
  KEY ix_cobr_decision (decision_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국외조달 입찰결과 정제(2,494 기대, 개찰 2025-03~09 부분연도). 달러 예산은 원화와 합산 금지. 낙찰업체 열 원본에 없음';

-- KOSIS 2종 clean 세로형. 적재 notebooks/06_clean_kosis.ipynb.
-- 원본이 이미 세로형이라 두 표 모두 원본 1:1(PK raw_row_id). 형 변환(연도·월·숫자) + data-cleaning-rules §2-11 등급 플래그 + 잠정치 플래그만 더하고 원문은 value_text 에 보존.
-- 지수·가동률(%)을 금액과 합산·비율 계산하지 않는다(§1-10). 가동률은 KOSIS 원본 통계 명칭 그대로("율" 오용 아님).
CREATE TABLE clean_kosis_utilization (
  raw_row_id       BIGINT UNSIGNED NOT NULL COMMENT 'PK. → raw_kosis_utilization.row_id (raw 1:1)',
  sector_name      VARCHAR(20)     NOT NULL COMMENT '분야(평균·항공유도·화력·탄약·기동·통신전자·함정·화생방·기타). 원문 앞뒤 공백 제거',
  is_avg_row       TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 「평균」 행(KOSIS 가 준 전 분야 평균). 분야 값으로 다시 평균 내지 않는다',
  in_scope         TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 통신전자(data-cleaning-rules §2-11 ★). 나머지 분야는 0(✕ 스코프 밖, 배경 비교용)',
  year             SMALLINT        NOT NULL COMMENT '연도 2016~2024(광폭 열 헤더). 연간 확정치',
  utilization_pct  DECIMAL(5,1)    NULL COMMENT '평균가동률(%). value_text 숫자화. 숫자가 아니면 NULL. 금액과 합산·비율 계산 금지',
  value_text       VARCHAR(20)     NULL COMMENT 'raw value_text 원문 보존',
  source_file      VARCHAR(100)    NOT NULL COMMENT 'raw source_file(갱신본 구분 키)',
  cleaned_at       DATETIME        NULL,
  cleaned_by       VARCHAR(50)     NULL,
  PRIMARY KEY (raw_row_id),
  UNIQUE KEY ux_cku_key (source_file, sector_name, year),
  KEY ix_cku_scope (in_scope, year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='KOSIS 409 방산업체 분야별 평균가동률 정제 81행(raw 1:1, 2016~2024). 보조 ④ — 통신전자 행만 in_scope=1. %를 금액과 합산·비율 계산 금지';

-- stat_month 복원 규칙(raw stat_ym='p)' 결함 16행 대응): 광폭 3열 = 2016.01 T10, 4열 = 2016.01 T20(실측), 이후 2열씩 1개월.
--   month_idx = (source_col_no - 3) DIV 2, stat_month = 2016-01-01 + month_idx 개월. 253·254 → 2026-06, 255·256 → 2026-07. 정상 행은 파싱값 = 복원값(노트북 검산 불일치 0).
-- scope_grade(§2-11): 00 전국 × C26·C261 × T20 계절조정 = ★ / 같은 조합 T10 원지수 = ▲ / 그 외(C262·C264, 시도별) = ✕.
CREATE TABLE clean_kosis_production_index (
  raw_row_id         BIGINT UNSIGNED NOT NULL COMMENT 'PK. → raw_kosis_production_index.row_id (raw 1:1)',
  region_name        VARCHAR(30)     NOT NULL COMMENT '시도 원문(현재 파일은 00 전국 뿐)',
  industry_code      VARCHAR(5)      NOT NULL COMMENT 'KSIC 산업 코드 = industry_name 앞 토큰(C26 / C261 / C262 / C264)',
  industry_name      VARCHAR(100)    NOT NULL COMMENT '산업명(코드 뒤 원문. 예 반도체 제조업)',
  stat_month         DATE            NOT NULL COMMENT '통계 월 YYYY-MM-01. stat_ym 파싱값. 결함 행 16은 source_col_no 로 복원(is_month_restored)',
  is_month_restored  TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = raw stat_ym 이 p) 라 source_col_no 로 월을 복원한 행(2026-06·07, 16행)',
  item_code          CHAR(3)         NOT NULL COMMENT 'T10 원지수 / T20 계절조정 = item_name 앞 토큰',
  item_name          VARCHAR(50)     NOT NULL COMMENT '항목명(코드 뒤 원문. 예 생산지수(계절조정))',
  index_value        DECIMAL(8,3)    NULL COMMENT '생산지수(2020=100). value_text 숫자화. 숫자가 아니면 NULL. 금액과 합산·비율 계산 금지',
  is_provisional     TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 잠정치(원본 헤더 p), 2026.06·2026.07). 확정치로 갱신되면 새 source_file 로 누적',
  is_partial_year    TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 2026(1~7월 부분연도). 연간 지표로 쓰지 않는다',
  scope_grade        ENUM('★','▲','✕') NOT NULL DEFAULT '✕' COMMENT 'data-cleaning-rules §2-11 등급: 전국×C26·C261×T20=★, 같은 조합 T10=▲, 그 외 ✕',
  value_text         VARCHAR(20)     NULL COMMENT 'raw value_text 원문 보존',
  source_file        VARCHAR(100)    NOT NULL COMMENT 'raw source_file(갱신본 구분 키)',
  cleaned_at         DATETIME        NULL,
  cleaned_by         VARCHAR(50)     NULL,
  PRIMARY KEY (raw_row_id),
  UNIQUE KEY ux_ckp_key (source_file, region_name, industry_code, stat_month, item_code),
  KEY ix_ckp_scope (scope_grade, stat_month),
  KEY ix_ckp_ind (industry_code, item_code, stat_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='KOSIS 101 광공업생산지수 C26 계열 정제 1,016행(raw 1:1, 2016.01~2026.07, 2020=100). 보조 ④ — ★는 전국×C26·C261×계절조정. 지수를 금액과 합산·비율 계산 금지';

-- 뷰가 원본을 직접 읽던 2곳의 정제 표(clean_customs_region 은 load_db.py --fact, clean_dapa_defense_company 는 04_clean_domestic §6)
CREATE TABLE clean_customs_region (
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

CREATE TABLE clean_dapa_defense_company (
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
       CAST(v.imp_dlr AS DOUBLE) / NULLIF(SUM(v.imp_dlr) OVER (PARTITION BY v.hs6, v.year), 0) AS share,   -- DOUBLE: DECIMAL 4자리 반올림 방지
       RANK() OVER (PARTITION BY v.hs6, v.year ORDER BY v.imp_dlr DESC)     AS rnk
FROM v_import_hs6_year v;

-- HHI = Σ(점유율×100)² (0~10,000). "전체 수입 중" HHI이며 "방산 수입 HHI"가 아니다.
CREATE OR REPLACE VIEW v_hhi_hs6_year AS
SELECT s.hs6, s.year,
       MAX(s.imp_dlr_total)                 AS imp_dlr_total,
       SUM(POWER(s.share * 100, 2))         AS hhi,
       CAST(SUM(s.imp_dlr > 0) AS UNSIGNED) AS country_count,   -- 수입 실적(>0) 국가 수
       MAX(CASE WHEN s.rnk = 1 THEN s.stat_cd END) AS top1_stat_cd,
       MAX(CASE WHEN s.rnk = 1 THEN s.share   END) AS top1_share,
       MAX(s.is_partial_year)               AS is_partial_year
FROM v_import_share_hs6_year s
GROUP BY s.hs6, s.year;

-- 수출 국가 점유율·순위 (HS6 × 연도 내). ZZ(기타국) 포함. 수출 0인 국가 행도 남는다(share 0).
CREATE OR REPLACE VIEW v_export_share_hs6_year AS
SELECT v.hs6, v.year, v.stat_cd, v.exp_dlr, v.is_partial_year,
       SUM(v.exp_dlr) OVER (PARTITION BY v.hs6, v.year)                     AS exp_dlr_total,
       CAST(v.exp_dlr AS DOUBLE) / NULLIF(SUM(v.exp_dlr) OVER (PARTITION BY v.hs6, v.year), 0) AS share,
       RANK() OVER (PARTITION BY v.hs6, v.year ORDER BY v.exp_dlr DESC)     AS rnk
FROM v_import_hs6_year v;

-- 수출 HHI = Σ(점유율×100)² (0~10,000). "전체 수출 중" HHI이며 "방산 수출 HHI"가 아니다.
CREATE OR REPLACE VIEW v_hhi_export_hs6_year AS
SELECT s.hs6, s.year,
       MAX(s.exp_dlr_total)                 AS exp_dlr_total,
       SUM(POWER(s.share * 100, 2))         AS hhi_export,
       CAST(SUM(s.exp_dlr > 0) AS UNSIGNED) AS country_count,   -- 수출 실적(>0) 국가 수
       MAX(CASE WHEN s.rnk = 1 THEN s.stat_cd END) AS top1_stat_cd,
       MAX(CASE WHEN s.rnk = 1 THEN s.share   END) AS top1_share,
       MAX(s.is_partial_year)               AS is_partial_year
FROM v_export_share_hs6_year s
GROUP BY s.hs6, s.year;

-- 과천시 소재 수입자 비중(방위사업청 소재지), 추정 — HS6 × 연도. 분모 전국(17시도) 수입액, 분자 sgg_name '경기도 과천시'. 금액 천 달러.
-- 「군 직접 수입 하한」이라 쓰지 않는다. 화면에는 쓰지 않고 EDA 참고로 둔다. 246행(HS2022 신설 코드는 2022 이전 행 없음).
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

-- 핵심 ③ 추가 검토 목록 (연도별 전체 행. 화면에서 최근 완결연도로 필터, 기본 정렬 hhi DESC, imp_dlr_total DESC)
--
-- 정의: "선택 연도(year)의 수입 집중도" + "현재 확보한 국산화 근거". 두 축의 시점은 일치하지 않는다.
--   · 무역 열(imp_dlr_total·hhi 등)만 year를 따른다.
--     화면에는 근거 기준(b1_latest_round_year, B2 원본 파일 날짜 dapa_localized_items_20260509)을 따로 표시한다.
-- 건수 규칙:
--   · 카테고리 맵을 두지 않으므로 B1·B2 열은 없다. 국산화 근거(B1 KRIT·B2 국산화개발품목)는 HS6에 붙이지 않고 FSC 축에서만 본다.
--   · NULL = 미확인(해당 clean_ 테이블 미적재 / 대응표 없음 / B2 범위 밖). 0 = 확인 결과 실제로 없음. 사유는 b1_status·b2_status.
--   · 한 FSC·과제가 여러 hs6에 대응하면 각 hs6 행에 중복 집계된다. HS별 값을 합산하면 같은 부품·과제가 다시 중복된다.
CREATE OR REPLACE VIEW v_review_list AS
SELECT w.hs6, w.category, w.name_ko, w.priority, w.axis,
       h.year, h.imp_dlr_total, h.top1_stat_cd, h.top1_share, h.hhi, h.country_count, h.is_partial_year
FROM ref_hs_whitelist w
JOIN v_hhi_hs6_year h ON h.hs6 = w.hs6;

-- 핵심 ② 월별 계약 건수·금액 (물품/용역·5분류 분리)
--   월   = 계약번호별 "최초 체결월" (MIN(contract_date)). 차수 00이 없는 계약번호가 있어 '00' 행이 아니라 MIN으로 잡는다.
--          MIN(contract_date)가 첫 차수의 계약일과 다른 계약이 있으면 정제 노트북에서 확인해 기록한다.
--   건수 = 계약번호당 1(is_latest_seq=1 행), 금액 = 최종 차수의 total_contract_amount. 변경계약은 최초 월에 최종 금액으로 잡힌다.
--   변경일 기준 월별 추이가 필요하면 이 뷰가 아니라 clean_dapa_contract.contract_date를 직접 집계한다.
--   amount_missing_count = total_contract_amount NULL 건수(규칙 #9 분모 제외·건수 병기).
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

-- 배경: 연도 × 집행유형 예산(계획)·건수·전자 관련 후보(검수 확정분 별도). 관세청 수입액과 합산·비교 금지.
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

-- 3-2 v_b2_fsg_summary — clean fsc2·dup_count. 행 수 = SUM(dup_count)(33,965), 고유 부품 = part_mgmt_no DISTINCT(12,788).
--     원본 fsc ''·'0' 은 clean fsc2 NULL 한 그룹으로 모인다(57행). NULL 그룹의 fsc4_count 는 0.
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

-- 민수 혼합 라벨 도출 규칙 (docs/reference/hs-whitelist-definition.md §7). ref_hs_whitelist.civil_mix 3열은 이 뷰의 스냅샷.
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
-- HS6 선정 규칙 (docs/reference/hs-whitelist-definition.md §8). "어떤 HS6를 수집할지"를 팀 판단이 아니라
-- 공식 자료에 규칙을 적용해 도출한다. HS 마스터·HSK 연계표 적재 전에는 빈 결과(또는 전부 '규칙 미해당')를 낸다.
--   자료 S1 관세청 HS부호 마스터(15049722, 2026 현행) ∪ 수집된 dim_hs10(2016~2026 이력 코드) — 법령: 관세법 §84 → 관세·통계통합품목분류표(기획재정부 고시)
--   자료 S2 무역안보관리원 HSK 연계표(15034135) — 법령: 대외무역법 §19·§29 → 전략물자수출입고시(산업통상부 고시) **별표2 이중용도품목(0~9부)만** 실려 있다
--            (2,161행 중 ML(별표3 군용물자) 0건. 통제번호는 '3A001.a.1.,5A002.' 같은 쉼표 목록). 84·85·88·90류 HS6 486개가 걸리는
--            "해당 가능성" 목록이라 단독 진입 근거로 쓰지 않는다.
-- 규칙: R1 군용전용 HSK 존재 / R2 항공기용·항행·레이더·무인기 HSK 세분류(또는 HS6 명칭의 같은 용도어) 존재 / R3 이중용도 3·5·6·7부 통제 HSK 존재(참고, 진입 아님)
--   진입 = R1 OR R2. priority_rule = R1→1, R2→2, R3만→3(진입 아님). 잠정식 R1 OR R2 OR (R3 AND R4)의 결과는 ref_hs_rule_flag(rule_version 2026-09-16)에 스냅샷으로만 남고, R4·b2_part_count 열은 0·NULL 상수. 범위 HS 2단위 84·85·88·90(93·87·89류는 주제 밖).
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
FROM (SELECT LEFT(m.hs10, 6) AS hs6, m.hs10, m.name_ko, 'master_2026' AS src
      FROM ref_hs_code_master m
      UNION ALL
      SELECT d.hs6, d.hs10, d.name_ko, 'collected'
      FROM dim_hs10 d
      WHERE NOT EXISTS (SELECT 1 FROM ref_hs_code_master m2 WHERE m2.hs10 = d.hs10)) u;

-- 3-3 v_hsk_control_by_hs6 — clean_hsk_control(HSK10 × 통제번호 1개 세로형) 기준.
--     HS6 1,119 · DU 707. ml = regime '군용물자'(자료에 0), du_elec = is_du_elec(part_no 3·5·6·7).
--     control_no_list 는 통제번호 낱개(DISTINCT)의 ';' 결합. group_concat_max_len(기본 1024) 초과분은 잘린다.
CREATE OR REPLACE VIEW v_hsk_control_by_hs6 AS
SELECT c.hs6,
       COUNT(DISTINCT c.hsk10)                                                     AS control_hsk10_count,
       COUNT(DISTINCT CASE WHEN c.regime = '군용물자' THEN c.hsk10 END)            AS ml_hsk10_count,
       COUNT(DISTINCT CASE WHEN c.is_du_elec = 1 THEN c.hsk10 END)                AS du_elec_hsk10_count,
       GROUP_CONCAT(DISTINCT c.control_no ORDER BY c.control_no SEPARATOR 0x3B)   AS control_no_list
FROM clean_hsk_control c
GROUP BY c.hs6;

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
-- 3-4 v_overseas_plan_api_fsc — clean_dapa_overseas_plan_api 기준.
--     ① 모집단은 clean nsn 전체(숫자13 9,970 + 영숫자13 3,266 = 13,236) — NCB 37 영숫자 NSN 도 유효.
--     ② is_electronic_group = is_elec(fsg2 58·59·60) → 전자군 품목 2,267. ③ army_name = army_std(군 표준값).
--     ④ 적용장비 집계는 is_equipment_missing=0(공란·'*' 제외). 금액은 통화 미검증이라 뷰에 넣지 않는다(건수만). 파일판과 합산 금지.
--     화면 미사용 — 화면은 clean_dapa_overseas_plan_api 를 직접 읽고, 군별 전자 비중 분모는
--     「FSG 판별 가능 − FSC 9999」 13,017. 이 뷰의 모집단(NSN 있음 13,236)과 다르다(data-cleaning-rules.md §1 #16).
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

-- 3-5 v_budget_rnd_yearly — clean_openfiscal_program_budget(정수 천원 열) 기준.
--     억원 = 천원 ÷ 100,000, 확정 합 0 → 정부안(total 1,995,815 · tech_dev 215,989).
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

-- KDSIS 연결 조회 뷰 3개. 모두 LEFT JOIN이라 왼쪽 표 행수가 그대로다(clean_kdsis_nsn PK nsn).
-- 3-6 v_overseas_plan_api_kdsis — clean_dapa_overseas_plan_api(원본 1:1) ↔ clean_kdsis_nsn. 13,615행 · 연결 616.
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
--     행 단위 = 고유 사업×부품(25,025, 원본 33,965행). b2_row_id = first_raw_row_id(대표 원본 행). 끝에 dup_count(원본 행 기준 값 복원용).
--     link_key 규칙: fsc4 숫자 4 + nsn 숫자 9 = 13자, 아니면 NULL(임의 0 채움 금지).
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

-- 3-8 v_kdsis_link_summary — 연결 요약 6열 + 원본 행 기준 3열(total_raw_rows·eligible_raw_rows·matched_raw_rows).
--     B2 행의 total/eligible/matched_rows 는 고유 사업×부품 기준(25,025 / … / 310)이고, 원본 행 기준(33,965 / 31,531 / 449)은 *_raw_rows 열로 읽는다. API 행은 원본 1:1 이라 두 값이 같다.
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

-- -----------------------------------------------------------------------------
-- 국내 축 확장 뷰 9개 — v_defense_company_sector 를 뺀 8개는 clean_ 기준.
-- 조달 보조 6종(clean_dapa_domestic_plan·bid_notice·bid_result·overseas_contract·overseas_bid_result + 방산업체 지정현황)과
-- 계약정보 수의계약 사유(clean_dapa_contract.private_contract_reason)를 집계. FSC·HS6 축 아님(연도·계약방법·사유·업체 축).
-- -----------------------------------------------------------------------------
-- §1 계약정보 수의계약 사유 구성 — 계약번호당 1행(clean 43,111행 → 계약 37,608). 사유·계약방법은 같은 계약번호 안에서 전부 동일(실측 충돌 0).
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
--      해당 없음(경쟁계약) = 경쟁계약 전부(사유 열 없음)
--      사유 미기재        = 수의계약 9건(원본 공란)
--      기타              = 그 외(긴급 §23①3, 분할 §29, 용역·공사 §26①2 차카·가-마 등)
-- 3-9 v_contract_private_reason — clean_dapa_contract(private_contract_reason) 기준.
--     계약번호당 1행(43,111 → 계약 37,608). 연도 = 최초 계약체결 연도(MIN contract_date), 금액 = 최종 차수(is_latest_seq=1)의 total_contract_amount(합 158,338억).
--     충돌 키 2024UMM1504-01(같은 차수 원본 2행)은 clean 대표 행 1개(seq_conflict_flag=1) 기준이다.
--     reason_group 그룹 정의는 위 주석.
--     amount_missing_count 열, 경쟁계약은 reason_text '(해당 없음)' · reason_group '해당 없음(경쟁계약)'(사유 미기재 9건과 구분).
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

-- 3-10 v_bid_result_summary — clean_dapa_bid_result(opening_date DATE·opening_result ENUM·bid_notice_seq_norm·final_award_rate/amount 숫자형).
--     열 밀림 2행은 clean 에 없다(7,403). 키 = 공고번호 + 정규화 차수.
--     낙찰률·낙찰금액은 숫자형이라 REGEXP 판별이 필요 없다(rate_numeric_rows = final_award_rate IS NOT NULL).
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

-- 3-11 v_bid_notice_monthly — clean_dapa_bid_notice(bid_notice_date DATE·budget_amount_krw BIGINT). 열 밀림 2행 제외 = 10,840.
--      전 행 NULL 그룹은 0 이 아니라 NULL(규칙 #9) + budget_missing_count(합 596).
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

-- 3-12 v_bid_notice_result_link — 연결 요약. 1행: clean_dapa_bid_result 키 대표 행의 notice_link_status(1:1/다중/미연결) 집계(키 7,199, 열 밀림 2행 제외).
--      result_rows 는 clean 행 수(7,403), *_shifted_rows 는 clean_excluded_row COL_SHIFT 건수(2·2). 2행: 낙찰업체 사업자번호 ↔ clean_dapa_contract.vendor_biz_reg_no(3,209).
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
--      원본 속성 저분산 열(ordering_agency)은 두지 않는다(규칙 #13).
--      단위 = 판단번호 × 항목번호(1,362). 공고 횟수는 bid_notice_no(차수 포함) DISTINCT 그대로. 달러 예산은 A7 원화와 합산 금지.
--      파일판 판단번호 중복 5쌍은 clean 대표 행 1개 기준이다.
CREATE OR REPLACE VIEW v_overseas_bid_chain AS
SELECT b.decision_no,
       b.item_seq,
       MAX(b.bid_item_name)                                              AS bid_item_name,
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

-- 3-14 v_domestic_plan_yearly — clean_dapa_domestic_plan(plan_year·exec_type 표준값·budget_krw·is_contracted·is_budget_approx). 35,859 · 지수 표기 11.
--      budget_krw NULL(원본 미기재 4,965행)은 SUM 에서 빠진다.
--      budget_missing_count = 예산 미기재 건수(합 4,965).
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

-- 3-15 v_overseas_contract_yearly — clean_dapa_overseas_contract(contract_year·contract_method_name·contract_no PK·vendor_name). 6,333 · 업체 1,697.
--      contract_no_count 는 PK 라 contract_count 와 같다.
CREATE OR REPLACE VIEW v_overseas_contract_yearly AS
SELECT contract_year,
       contract_method_name,
       COUNT(*)                                                           AS contract_count,
       COUNT(DISTINCT contract_no)                                        AS contract_no_count,
       COUNT(DISTINCT vendor_name)                                        AS vendor_count
FROM clean_dapa_overseas_contract
GROUP BY contract_year, contract_method_name;

-- §8 방산업체 지정현황 분야별 — 84행, 분야 공란 3은 '미기재'. 주소·사업자번호·품목 없음(업체명 정규화 연결은 clean_company_name_link 정제 후).
CREATE OR REPLACE VIEW v_defense_company_sector AS
SELECT COALESCE(sector, '미기재')                                          AS sector,
       COUNT(*)                                                           AS company_count,
       MIN(YEAR(designated_date))                                         AS first_designated_year,
       MAX(YEAR(designated_date))                                         AS last_designated_year
FROM clean_dapa_defense_company
GROUP BY COALESCE(sector, '미기재');

-- §9 수의계약 사유 그룹 연도 요약(화면 카드용) — §1을 그룹 단위로 접은 것. 비중 분모 = 그 해 전체 계약(경쟁 포함).
--    결과 20행(해당 없음(경쟁계약) 포함, 사유 미기재는 9건).
CREATE OR REPLACE VIEW v_contract_reason_group_yearly AS
SELECT contract_year, reason_group,
       SUM(contract_count)                                                AS contract_count,
       SUM(total_contract_amount_krw)                                     AS total_contract_amount_krw,
       ROUND(100 * SUM(contract_count) / SUM(SUM(contract_count)) OVER (PARTITION BY contract_year), 2) AS share_pct
FROM v_contract_private_reason
GROUP BY contract_year, reason_group;

