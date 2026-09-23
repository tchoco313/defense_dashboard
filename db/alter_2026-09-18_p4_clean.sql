-- =============================================================================
-- P4 국내조달·업체 clean 테이블 4개 + 제외 행 공용 표 (작성 2026-09-18)
--
-- 배경: 팀 raw·ref → clean 전환 분배 명세(docs/reference/clean-conversion-spec-2026-09-18.md §5, 담당 김훈희).
--       6개 중 clean_dapa_contract·clean_company·clean_company_name_link 는 정의가 있고(0행), 입찰공고·입찰결과·국내 조달계획·군별 계약집행 4개는 없어 여기서 만든다.
--       schema-change-log.md §7-19(raw→clean 일괄 복제 안 함)와의 관계: 이 4개는 단순 복제가 아니라 명세가 요구하는 형 변환·키 정규화·열 밀림 격리·개인정보 제외 산출물이다(§7-20).
-- 원칙: raw 는 읽기만(원본 동결). 모든 clean 행에 raw_row_id(FK). 금액은 BIGINT + 단위 접미(_krw, _100m_krw). 날짜는 DATE. Y/N → TINYINT(1).
--       담당자명·대표자명·연락처 열은 clean 에 두지 않는다. 표준값이 미확인인 열(공고상태·업무구분 등)은 ENUM 대신 VARCHAR + COMMENT.
-- 구조: §1 clean_excluded_row(공용) → §2 clean_dapa_bid_notice → §3 clean_dapa_bid_result → §4 clean_dapa_domestic_plan → §5 clean_dapa_contract_exec_by_service
--       → §6 meta_column_dict(101행, db/column_dict.csv 와 동일) → §7 검증
-- 적재: 사용자 정제 노트북(etl_rw). 이 파일은 표만 만든다(0행). meta_load_log 는 적재 후 노트북이 기록.
-- 실행: RDS admin 계정, docs/runbook/aws-rds-setup.md 방식(mysql.exe --ssl-mode=REQUIRED). DBHub(app_ro)는 불가.
-- 재실행 가능: CREATE TABLE IF NOT EXISTS + ON DUPLICATE KEY UPDATE.
-- 콜레이션: RDS의 defense_dashboard 기본 콜레이션은 utf8mb4_0900_ai_ci(복원 시 CREATE DATABASE 절 미적용)라 CREATE TABLE 에 COLLATE=utf8mb4_unicode_ci 를 명시한다
--          (2026-09-18 1차 적용에서 5표가 0900_ai_ci 로 생성돼 ALTER TABLE … CONVERT TO 로 바로잡음. 이후 alter 도 명시 필수).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;   -- 2026-09-17 뷰 콜레이션 규칙(alter_2026-09-17_view_collation.sql)

-- §1 clean_excluded_row — 전 담당 공용. clean 으로 옮기지 않은 raw 행을 (table_name, raw_row_id, reason_code)로 남긴다.
--    검산: raw 행 수 = clean 행 수 + 이 표의 해당 table_name 행 수. 사유 코드는 명세 §1-2(DUP_EXACT/COL_SHIFT/PLACEHOLDER/OUT_OF_SCOPE) + KEY_CONFLICT/OTHER.
CREATE TABLE IF NOT EXISTS clean_excluded_row (
  excl_id      INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  table_name   VARCHAR(64)      NOT NULL COMMENT '제외 대상 raw 테이블명(예 raw_dapa_bid_notice)',
  raw_row_id   BIGINT UNSIGNED  NOT NULL COMMENT 'raw.row_id (테이블이 여러 개라 FK 없음)',
  reason_code  ENUM('DUP_EXACT','COL_SHIFT','PLACEHOLDER','OUT_OF_SCOPE','KEY_CONFLICT','OTHER') NOT NULL COMMENT '명세 §1-2 사유 코드',
  note         VARCHAR(300)     NULL COMMENT '어느 열이 어떻게 잘못됐는지',
  excluded_by  VARCHAR(50)      NULL,
  excluded_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (excl_id),
  UNIQUE KEY ux_cer_row (table_name, raw_row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='clean 전환에서 제외한 raw 행과 사유(전 담당 공용). 검산 raw = clean + excluded 의 근거';


-- §2 clean_dapa_bid_notice — 키는 참조공고번호+차수(raw 고유 10,842). 입찰공고번호+차수는 비유일(10,486)이라 KEY만.
--    열 밀림 원본 2행(공고일자 NULL·계약방법 'Y'·여부 열에 날짜)은 넣지 않고 clean_excluded_row 에 COL_SHIFT 로 → 10,840 기대(v_bid_notice_monthly 와 같은 수).
--    시각 열(설명회·마감·개찰 시각)과 면허제한 원문 8열은 raw 참조(clean 은 개수+결합 문자열만). 담당자명 2열 제외.
CREATE TABLE IF NOT EXISTS clean_dapa_bid_notice (
  ref_notice_no                VARCHAR(30)      NOT NULL COMMENT '참조공고번호(실제 키)',
  ref_notice_seq_norm          CHAR(2)          NOT NULL COMMENT '참조공고차수 2자리 정규화(0→00)',
  raw_row_id                   BIGINT UNSIGNED  NOT NULL COMMENT '→ raw_dapa_bid_notice.row_id',
  bid_notice_no                VARCHAR(20)      NOT NULL COMMENT '입찰공고번호(연도 미포함·비유일 — 입찰결과와 맞추는 키)',
  bid_notice_seq_norm          CHAR(2)          NOT NULL COMMENT '입찰공고차수 2자리 정규화',
  bid_notice_name              VARCHAR(500)     NOT NULL,
  bid_notice_status            VARCHAR(20)      NULL COMMENT '긴급/정상/재공고/취소/정정/연기 (표준값, ENUM 아님)',
  bid_notice_date              DATE             NOT NULL COMMENT '사건 연도 기준 열',
  biz_type                     VARCHAR(20)      NULL COMMENT '물품/용역',
  g2b_notice_yn                TINYINT(1)       NULL COMMENT 'Y=1',
  joint_contract_yn            TINYINT(1)       NULL COMMENT 'Y=1',
  joint_supply_method_name     VARCHAR(50)      NULL,
  e_bid_yn                     TINYINT(1)       NULL COMMENT 'Y=1',
  contract_form_name           VARCHAR(50)      NULL,
  contract_method_name         VARCHAR(50)      NULL,
  award_method_name            VARCHAR(50)      NULL,
  notice_org_name              VARCHAR(100)     NULL,
  notice_org_code              VARCHAR(20)      NULL,
  notice_org_dept_name         VARCHAR(100)     NULL,
  demand_org_name              VARCHAR(100)     NULL,
  demand_org_code              VARCHAR(20)      NULL,
  demand_org_dept_name         VARCHAR(100)     NULL,
  briefing_yn                  TINYINT(1)       NULL COMMENT 'Y=1',
  briefing_date                DATE             NULL COMMENT '시각은 raw 참조',
  briefing_place               VARCHAR(200)     NULL,
  qualification_deadline_date  DATE             NULL COMMENT '시각은 raw 참조',
  bid_deadline_date            DATE             NULL COMMENT '시각은 raw 참조',
  opening_date                 DATE             NULL COMMENT '시각은 raw 참조',
  opening_place                VARCHAR(200)     NULL,
  budget_amount_krw            BIGINT           NULL COMMENT '예산금액(원). 공고 예산 — 낙찰·계약액 아님',
  allocated_budget_amount_krw  BIGINT           NULL COMMENT '배정예산(설계금액, 원)',
  region_limit_yn              TINYINT(1)       NULL COMMENT 'Y=1',
  eligible_region_name         VARCHAR(200)     NULL,
  license_limit_group_count    TINYINT          NOT NULL DEFAULT 0 COMMENT '공종및면허제한그룹1~8 중 비공란 수',
  license_limit_groups         VARCHAR(2500)    NULL COMMENT '그룹1~8을 세로줄( | )로 결합(원문은 raw)',
  bid_notice_url               VARCHAR(300)     NULL,
  cleaned_at                   DATETIME         NULL,
  cleaned_by                   VARCHAR(50)      NULL,
  PRIMARY KEY (ref_notice_no, ref_notice_seq_norm),
  UNIQUE KEY ux_cbn_raw (raw_row_id),
  KEY ix_cbn_date (bid_notice_date, bid_notice_status),
  KEY ix_cbn_notice (bid_notice_no, bid_notice_seq_norm),
  CONSTRAINT fk_cbn_raw FOREIGN KEY (raw_row_id) REFERENCES raw_dapa_bid_notice (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국내조달 입찰공고 정제(참조공고번호+차수 단위, 열 밀림 2행 제외 → 10,840 기대). 담당자명 제외';


-- §3 clean_dapa_bid_result — 키 (공고번호, 차수) 7,201 중 199키가 여러 행(복수 낙찰 108·결과 상이 73, 2026-09-17 실측). 행을 지우지 않고 result_seq 로 보존,
--    dup_kind 로 성격을 적고 is_key_representative=1 행(키당 1)을 키 기준 집계에 쓴다(v_bid_result_summary 키 수와 대조).
--    열 밀림 2행(LCF0223 1·2차: 개찰결과 열에 날짜, 적격심사여부 '제한경쟁')은 clean_excluded_row COL_SHIFT → 7,403 기대. 대표자·담당자명 제외.
--    입찰공고와의 행 단위 조인은 하지 않는다(참조공고번호가 결과 표에 없음) — notice_link_status 로 상태만.
CREATE TABLE IF NOT EXISTS clean_dapa_bid_result (
  bid_notice_no            VARCHAR(20)      NOT NULL,
  bid_notice_seq_norm      CHAR(2)          NOT NULL COMMENT '차수 2자리 정규화',
  result_seq               TINYINT          NOT NULL DEFAULT 1 COMMENT '같은 키 안 row_id 순 1..n (중복 키 행 보존)',
  raw_row_id               BIGINT UNSIGNED  NOT NULL COMMENT '→ raw_dapa_bid_result.row_id',
  key_row_count            SMALLINT         NOT NULL DEFAULT 1 COMMENT '같은 (공고번호, 차수) raw 행 수',
  dup_kind                 ENUM('단일','복수 낙찰','결과 상이','미확인') NOT NULL DEFAULT '단일' COMMENT '중복 키 성격(2026-09-17 실측: 복수 낙찰 108키·결과 상이 73키)',
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
  KEY ix_cbr_rep (is_key_representative, opening_result),
  CONSTRAINT fk_cbr_raw FOREIGN KEY (raw_row_id) REFERENCES raw_dapa_bid_result (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국내조달 입찰결과 정제(공고번호+차수+결과순번, 열 밀림 2행 제외 → 7,403 기대). 중복 키 199는 행 보존·dup_kind 로 구분. 대표자·담당자명 제외';


-- §4 clean_dapa_domestic_plan — raw 1:1(35,859). 판단번호 고유성은 미확인이라 PK = raw_row_id; 탐색(query_p4_domestic_explore.sql 4-5)에서 고유로 확인되면 후속 alter 로 UNIQUE.
--    2024 는 4,545행 불완전 연도(is_partial_year=1). officer_name·officer_phone 은 raw 에서 이미 NULL — clean 에 열을 두지 않는다.
CREATE TABLE IF NOT EXISTS clean_dapa_domestic_plan (
  raw_row_id          BIGINT UNSIGNED  NOT NULL COMMENT '→ raw_dapa_domestic_plan.row_id (PK — 판단번호 고유성 미확인)',
  decision_no         VARCHAR(20)      NULL COMMENT '판단번호(고유이면 후속 alter 로 UNIQUE)',
  decision_row_count  SMALLINT         NOT NULL DEFAULT 1 COMMENT '같은 판단번호 raw 행 수',
  plan_month          DATE             NOT NULL COMMENT '집행예정월 YYYY-MM-01',
  plan_year           CHAR(4)          NOT NULL,
  is_partial_year     TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '2024 = 1 (4,545행, 불완전 연도)',
  rep_item_name       VARCHAR(500)     NULL,
  exec_type           VARCHAR(30)      NOT NULL COMMENT '표준값(구매/제조/제조/구매/기타/공사/리스/공급)',
  contract_method     VARCHAR(30)      NULL,
  exec_agency         VARCHAR(100)     NULL,
  budget_krw          BIGINT           NOT NULL COMMENT '예산금액(원, 집행 예정액 — 실적 아님)',
  bid_method          VARCHAR(30)      NULL,
  progress_status     VARCHAR(30)      NULL,
  is_contracted       TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'progress_status = 계약완료 (2025 24,013 기대)',
  cleaned_at          DATETIME         NULL,
  cleaned_by          VARCHAR(50)      NULL,
  PRIMARY KEY (raw_row_id),
  KEY ix_cdp_month_type (plan_month, exec_type),
  KEY ix_cdp_decision (decision_no),
  KEY ix_cdp_year (plan_year, is_contracted),
  CONSTRAINT fk_cdp_raw FOREIGN KEY (raw_row_id) REFERENCES raw_dapa_domestic_plan (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국내조달 조달계획 정제(raw 1:1, 35,859 기대). 판단번호 고유성 확인 후 UNIQUE 추가 검토. 담당자·연락처 열 없음. 예산은 집행 예정액 — 관세청 수입액과 합산·비교 금지';


-- §5 clean_dapa_contract_exec_by_service — 연도×군 40행. 억원 단위를 열 이름에 유지.
CREATE TABLE IF NOT EXISTS clean_dapa_contract_exec_by_service (
  year                      SMALLINT         NOT NULL COMMENT '2015~2024',
  service_branch            ENUM('육군','해군','공군','국직') NOT NULL COMMENT '표준값',
  contract_amount_100m_krw  DECIMAL(14,1)    NOT NULL COMMENT '계약금액(억원)',
  raw_row_id                BIGINT UNSIGNED  NOT NULL COMMENT '→ raw_dapa_contract_exec_by_service.row_id',
  cleaned_at                DATETIME         NULL,
  cleaned_by                VARCHAR(50)      NULL,
  PRIMARY KEY (year, service_branch),
  UNIQUE KEY ux_ces_raw (raw_row_id),
  CONSTRAINT fk_ces_raw FOREIGN KEY (raw_row_id) REFERENCES raw_dapa_contract_exec_by_service (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='군별 계약집행 현황 정제(연도×군, 40행 기대). KPI 배경 — 조달 금액 ≠ 방산 매출';

-- §6 meta_column_dict (db/column_dict.csv 와 동일. load_db.py --ref 는 표가 비어 있을 때만 넣으므로 RDS 에는 이 INSERT 가 실제 경로)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_excluded_row', 1, 'excl_id', '(파생)', 'INT UNSIGNED', 'PK'),
('clean_excluded_row', 2, 'table_name', '(파생)', 'VARCHAR(64)', '제외한 raw 테이블명'),
('clean_excluded_row', 3, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '제외한 raw 행의 row_id'),
('clean_excluded_row', 4, 'reason_code', '(파생)', 'ENUM', '제외 사유 코드: DUP_EXACT 완전 중복 / COL_SHIFT 열 밀림 / PLACEHOLDER 자리표시 / OUT_OF_SCOPE 범위 밖 / KEY_CONFLICT 키 충돌 / OTHER'),
('clean_excluded_row', 5, 'note', '(파생)', 'VARCHAR(300)', '제외 근거 메모(어느 열이 어떻게 이상한지)'),
('clean_excluded_row', 6, 'excluded_by', '(파생)', 'VARCHAR(50)', '기록자'),
('clean_excluded_row', 7, 'excluded_at', '(파생)', 'DATETIME', '기록 시각'),
('clean_dapa_bid_notice', 1, 'ref_notice_no', '참조공고번호', 'VARCHAR(30)', 'PK 1. 실제 고유 키(raw 고유 10,842)'),
('clean_dapa_bid_notice', 2, 'ref_notice_seq_norm', '참조공고차수', 'CHAR(2)', 'PK 2. 차수 2자리 정규화'),
('clean_dapa_bid_notice', 3, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '원본 행 추적(UNIQUE, FK)'),
('clean_dapa_bid_notice', 4, 'bid_notice_no', '입찰공고번호', 'VARCHAR(20)', '비유일(고유 10,486). 입찰결과 연결용'),
('clean_dapa_bid_notice', 5, 'bid_notice_seq_norm', '입찰공고차수', 'CHAR(2)', '차수 2자리 정규화'),
('clean_dapa_bid_notice', 6, 'bid_notice_name', '입찰공고명', 'VARCHAR(500)', '공고 제목'),
('clean_dapa_bid_notice', 7, 'bid_notice_status', '입찰공고상태명', 'VARCHAR(20)', '표준값 긴급/정상/재공고/취소/정정/연기'),
('clean_dapa_bid_notice', 8, 'bid_notice_date', '입찰공고일자', 'DATE', '공고일(연도 축)'),
('clean_dapa_bid_notice', 9, 'biz_type', '업무구분명', 'VARCHAR(20)', '물품/용역'),
('clean_dapa_bid_notice', 10, 'g2b_notice_yn', '나라장터공고여부', 'TINYINT(1)', '나라장터 공고 1/0'),
('clean_dapa_bid_notice', 11, 'joint_contract_yn', '공동계약여부', 'TINYINT(1)', '공동계약 1/0'),
('clean_dapa_bid_notice', 12, 'joint_supply_method_name', '공동수급방식명', 'VARCHAR(50)', '공동수급 방식'),
('clean_dapa_bid_notice', 13, 'e_bid_yn', '전자입찰여부', 'TINYINT(1)', '전자입찰 1/0'),
('clean_dapa_bid_notice', 14, 'contract_form_name', '계약체결형태명', 'VARCHAR(50)', '계약체결형태'),
('clean_dapa_bid_notice', 15, 'contract_method_name', '계약체결방법명', 'VARCHAR(50)', '계약체결방법(제한경쟁 등)'),
('clean_dapa_bid_notice', 16, 'award_method_name', '낙찰자결정방법명', 'VARCHAR(50)', '낙찰자 결정방법'),
('clean_dapa_bid_notice', 17, 'notice_org_name', '공고기관명', 'VARCHAR(100)', '공고기관'),
('clean_dapa_bid_notice', 18, 'notice_org_code', '공고기관코드', 'VARCHAR(20)', '공고기관 코드'),
('clean_dapa_bid_notice', 19, 'notice_org_dept_name', '공고기관담당자부서명', 'VARCHAR(100)', '공고기관 부서(담당자명은 제외)'),
('clean_dapa_bid_notice', 20, 'demand_org_name', '수요기관명', 'VARCHAR(100)', '수요기관'),
('clean_dapa_bid_notice', 21, 'demand_org_code', '수요기관코드', 'VARCHAR(20)', '수요기관 코드'),
('clean_dapa_bid_notice', 22, 'demand_org_dept_name', '수요기관담당자부서명', 'VARCHAR(100)', '수요기관 부서(담당자명은 제외)'),
('clean_dapa_bid_notice', 23, 'briefing_yn', '설명회실시여부', 'TINYINT(1)', '설명회 실시 1/0'),
('clean_dapa_bid_notice', 24, 'briefing_date', '설명회실시일자', 'DATE', '설명회 일자(시각은 raw)'),
('clean_dapa_bid_notice', 25, 'briefing_place', '설명회실시장소', 'VARCHAR(200)', '설명회 장소'),
('clean_dapa_bid_notice', 26, 'qualification_deadline_date', '입찰참가자격등록마감일자', 'DATE', '참가자격 등록 마감일'),
('clean_dapa_bid_notice', 27, 'bid_deadline_date', '입찰마감일자', 'DATE', '입찰 마감일'),
('clean_dapa_bid_notice', 28, 'opening_date', '개찰일자', 'DATE', '개찰일'),
('clean_dapa_bid_notice', 29, 'opening_place', '개찰장소', 'VARCHAR(200)', '개찰 장소'),
('clean_dapa_bid_notice', 30, 'budget_amount_krw', '예산금액', 'BIGINT', '공고 예산(원). 낙찰액·계약액과 다름'),
('clean_dapa_bid_notice', 31, 'allocated_budget_amount_krw', '배정예산금액(설계금액)', 'BIGINT', '배정예산(원)'),
('clean_dapa_bid_notice', 32, 'region_limit_yn', '지역제한여부', 'TINYINT(1)', '지역제한 1/0'),
('clean_dapa_bid_notice', 33, 'eligible_region_name', '참가가능지역명', 'VARCHAR(200)', '참가 가능 지역'),
('clean_dapa_bid_notice', 34, 'license_limit_group_count', '(파생)', 'TINYINT', '면허제한 그룹 수(raw 8열 중 비공란)'),
('clean_dapa_bid_notice', 35, 'license_limit_groups', '(파생)', 'VARCHAR(2500)', '면허제한 그룹 원문 결합('' | '')'),
('clean_dapa_bid_notice', 36, 'bid_notice_url', '입찰공고URL', 'VARCHAR(300)', '공고 URL'),
('clean_dapa_bid_notice', 37, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_dapa_bid_notice', 38, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('clean_dapa_bid_result', 1, 'bid_notice_no', '입찰공고번호', 'VARCHAR(20)', 'PK 1. 공고번호(연도 미포함)'),
('clean_dapa_bid_result', 2, 'bid_notice_seq_norm', '입찰공고차수', 'CHAR(2)', 'PK 2. 차수 2자리 정규화'),
('clean_dapa_bid_result', 3, 'result_seq', '(파생)', 'TINYINT', 'PK 3. 같은 키 안 순번(row_id 순)'),
('clean_dapa_bid_result', 4, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '원본 행 추적(UNIQUE, FK)'),
('clean_dapa_bid_result', 5, 'key_row_count', '(파생)', 'SMALLINT', '같은 키의 행 수(1이면 단일)'),
('clean_dapa_bid_result', 6, 'dup_kind', '(파생)', 'ENUM', '중복 키 성격. 단일 / 복수 낙찰(낙찰업체 여러 곳) / 결과 상이(개찰결과가 다름) / 미확인'),
('clean_dapa_bid_result', 7, 'is_key_representative', '(파생)', 'TINYINT(1)', '키 기준 집계용 대표 행(키당 정확히 1행)'),
('clean_dapa_bid_result', 8, 'bid_notice_name', '입찰공고명', 'VARCHAR(500)', '공고 제목'),
('clean_dapa_bid_result', 9, 'biz_type', '업무구분명', 'VARCHAR(20)', '물품/용역'),
('clean_dapa_bid_result', 10, 'contract_form_name', '계약체결형태명', 'VARCHAR(50)', '계약체결형태'),
('clean_dapa_bid_result', 11, 'contract_method_name', '계약체결방법명', 'VARCHAR(50)', '계약체결방법'),
('clean_dapa_bid_result', 12, 'award_method_name', '낙찰자결정방법명', 'VARCHAR(50)', '낙찰자 결정방법'),
('clean_dapa_bid_result', 13, 'qualification_review_yn', '적격심사여부', 'TINYINT(1)', '적격심사 1/0'),
('clean_dapa_bid_result', 14, 'notice_org_name', '공고기관명', 'VARCHAR(100)', '공고기관'),
('clean_dapa_bid_result', 15, 'notice_org_code', '공고기관코드', 'VARCHAR(20)', '공고기관 코드'),
('clean_dapa_bid_result', 16, 'demand_org_name', '수요기관명', 'VARCHAR(100)', '수요기관'),
('clean_dapa_bid_result', 17, 'demand_org_code', '수요기관코드', 'VARCHAR(20)', '수요기관 코드'),
('clean_dapa_bid_result', 18, 'award_lower_limit_rate', '낙찰하한율', 'DECIMAL(7,3)', '낙찰하한율(%)'),
('clean_dapa_bid_result', 19, 'reserve_price_krw', '예정가격', 'BIGINT', '예정가격(원)'),
('clean_dapa_bid_result', 20, 'base_amount_krw', '기초금액', 'BIGINT', '기초금액(원)'),
('clean_dapa_bid_result', 21, 'estimated_price_krw', '추정가격', 'BIGINT', '추정가격(원)'),
('clean_dapa_bid_result', 22, 'opening_date', '개찰일자', 'DATE', '개찰일(연도 축)'),
('clean_dapa_bid_result', 23, 'opening_result', '개찰결과구분명', 'ENUM', '유찰 / 개찰완료 / 순위확정'),
('clean_dapa_bid_result', 24, 'is_awarded', '(파생)', 'TINYINT(1)', '낙찰 확정 여부(낙찰금액 존재)'),
('clean_dapa_bid_result', 25, 'final_award_amount_krw', '최종낙찰금액', 'BIGINT', '최종 낙찰금액(원). 계약금액과 다름'),
('clean_dapa_bid_result', 26, 'final_award_rate', '최종낙찰율', 'DECIMAL(7,3)', '최종 낙찰률(%)'),
('clean_dapa_bid_result', 27, 'final_award_date', '최종낙찰일자', 'DATE', '최종 낙찰일'),
('clean_dapa_bid_result', 28, 'winner_name', '최종낙찰업체명', 'VARCHAR(200)', '낙찰업체명(원문)'),
('clean_dapa_bid_result', 29, 'winner_biz_reg_no', '최종낙찰업체사업자등록번호', 'CHAR(12)', '낙찰업체 사업자등록번호(clean_company 키)'),
('clean_dapa_bid_result', 30, 'winner_address', '최종낙찰업체주소', 'VARCHAR(300)', '낙찰업체 소재지(생산·납품 위치 아님)'),
('clean_dapa_bid_result', 31, 'winner_sido_code', '(파생)', 'CHAR(2)', '소재지 시도코드(ref_sido_map)'),
('clean_dapa_bid_result', 32, 'notice_link_status', '(파생)', 'ENUM', '입찰공고 대조 상태: 1:1 / 다중(공고 여러 행) / 미연결'),
('clean_dapa_bid_result', 33, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_dapa_bid_result', 34, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('clean_dapa_domestic_plan', 1, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', 'PK. 원본 행 추적(FK)'),
('clean_dapa_domestic_plan', 2, 'decision_no', '판단번호', 'VARCHAR(20)', '판단번호(고유성 확인 전)'),
('clean_dapa_domestic_plan', 3, 'decision_row_count', '(파생)', 'SMALLINT', '같은 판단번호의 행 수'),
('clean_dapa_domestic_plan', 4, 'plan_month', '집행예정월', 'DATE', '집행예정월(매월 1일)'),
('clean_dapa_domestic_plan', 5, 'plan_year', '(파생)', 'CHAR(4)', '집행예정 연도'),
('clean_dapa_domestic_plan', 6, 'is_partial_year', '(파생)', 'TINYINT(1)', '불완전 연도 라벨(2024=1)'),
('clean_dapa_domestic_plan', 7, 'rep_item_name', '대표품명', 'VARCHAR(500)', '대표품명'),
('clean_dapa_domestic_plan', 8, 'exec_type', '집행유형', 'VARCHAR(30)', '집행유형 표준값'),
('clean_dapa_domestic_plan', 9, 'contract_method', '계약방법', 'VARCHAR(30)', '계약방법'),
('clean_dapa_domestic_plan', 10, 'exec_agency', '집행기관', 'VARCHAR(100)', '집행기관'),
('clean_dapa_domestic_plan', 11, 'budget_krw', '예산금액', 'BIGINT', '예산금액(원, 집행 예정액). 실적·수입액 아님'),
('clean_dapa_domestic_plan', 12, 'bid_method', '입찰방법', 'VARCHAR(30)', '입찰방법'),
('clean_dapa_domestic_plan', 13, 'progress_status', '진행상태', 'VARCHAR(30)', '진행상태'),
('clean_dapa_domestic_plan', 14, 'is_contracted', '(파생)', 'TINYINT(1)', '계약완료 1/0'),
('clean_dapa_domestic_plan', 15, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_dapa_domestic_plan', 16, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('clean_dapa_contract_exec_by_service', 1, 'year', '년도', 'SMALLINT', 'PK 1. 연도'),
('clean_dapa_contract_exec_by_service', 2, 'service_branch', '군구분', 'ENUM', 'PK 2. 군 구분 표준값'),
('clean_dapa_contract_exec_by_service', 3, 'contract_amount_100m_krw', '계약금액(억원)', 'DECIMAL(14,1)', '계약금액(억원)'),
('clean_dapa_contract_exec_by_service', 4, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '원본 행 추적(UNIQUE, FK)'),
('clean_dapa_contract_exec_by_service', 5, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_dapa_contract_exec_by_service', 6, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §7 검증 (같은 클라이언트 또는 DBHub)
-- SHOW TABLES LIKE 'clean_%';                                                         -- 13개 (기존 8 + 신규 5)
-- SELECT table_name, COUNT(*) FROM meta_column_dict
--  WHERE table_name IN ('clean_excluded_row','clean_dapa_bid_notice','clean_dapa_bid_result','clean_dapa_domestic_plan','clean_dapa_contract_exec_by_service')
--  GROUP BY table_name;                                                               -- 7 / 38 / 34 / 16 / 6 = 101
-- SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS
--  WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_NAME IN ('fk_cbn_raw','fk_cbr_raw','fk_cdp_raw','fk_ces_raw');   -- 4행
-- SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'clean_%';  -- 전부 utf8mb4_unicode_ci
-- [적재 후 검산]
-- SELECT (SELECT COUNT(*) FROM raw_dapa_bid_notice) AS raw_n, (SELECT COUNT(*) FROM clean_dapa_bid_notice) AS clean_n,
--        (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name = 'raw_dapa_bid_notice') AS excluded_n;             -- 10,842 = 10,840 + 2
-- SELECT (SELECT COUNT(*) FROM raw_dapa_bid_result) AS raw_n, (SELECT COUNT(*) FROM clean_dapa_bid_result) AS clean_n,
--        (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name = 'raw_dapa_bid_result') AS excluded_n;             -- 7,405 = 7,403 + 2
-- SELECT bid_notice_no, bid_notice_seq_norm, SUM(is_key_representative) s FROM clean_dapa_bid_result GROUP BY 1,2 HAVING s <> 1;  -- 0행
-- SELECT opening_result, COUNT(*) FROM clean_dapa_bid_result GROUP BY 1;             -- 유찰 1,746 · 개찰완료 5,275 · 순위확정 382
-- SELECT plan_year, COUNT(*), SUM(budget_krw) FROM clean_dapa_domestic_plan GROUP BY 1;   -- 2024 4,545 / 2025 31,314
-- SELECT COUNT(*) FROM clean_dapa_contract_exec_by_service;                          -- 40
