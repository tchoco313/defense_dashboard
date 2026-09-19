-- =============================================================================
-- P5-4 KRIT 공고(clean_krit_task 열 보강) + P2-6 열린재정 예산(clean_ 2표 신설)  (작성 2026-09-19)
--
-- 배경: 팀 raw·ref → clean 전환 분배 명세(new_data/K_Defense_clean전환_담당분배_명세_20260918.md §6-4 · §3-4·5).
--       clean_krit_task 는 정의가 이미 db/schema.sql 에 있고 0행이라 새로 만들지 않고 ALTER 로 열만 보강한다.
--       clean_openfiscal_program_budget · clean_openfiscal_program_link 는 신설이다(A9 예산에는 clean 정의가 없었다).
-- 원칙: raw 는 읽기만(원본 동결). 모든 clean 행에 raw_row_id(FK). 금액 단위는 열 이름에 표기(_krw_k=천원, _100m_krw=억원).
--       판단 속성은 NULL 또는 '미확인'·'후보' 기본값. HS6↔FSC 대응표(ref_category_map)는 만들지 않는다 → clean_krit_task.hs6 는 NULL 유지.
-- 구조: §1 clean_krit_task 열 9개 보강 → §2 clean_openfiscal_program_budget → §3 clean_openfiscal_program_link
--       → §4 meta_column_dict(9 + 21 + 13 = 43행, db/column_dict.csv 와 동일) → §5 검증
-- 적재: 정제 노트북 notebooks/clean_p5_krit_p2_budget.ipynb(etl_rw). 이 파일은 표·열만 만든다(0행). meta_load_log 는 적재 후 노트북이 기록.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-19_krit_budget_clean.sql   (RDS admin). DBHub(app_ro)는 불가.
-- 재실행 가능: CREATE TABLE IF NOT EXISTS + information_schema 확인 후 PREPARE/EXECUTE(ADD COLUMN) + ON DUPLICATE KEY UPDATE.
-- 콜레이션: defense_dashboard 기본이 utf8mb4_0900_ai_ci 라 CREATE TABLE 에 COLLATE=utf8mb4_unicode_ci 를 명시한다
--          (2026-09-18 alter_2026-09-18_p4_clean.sql 과 같은 규칙).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- §1 clean_krit_task 열 보강 (기존 16열 → 25열. 물리 순서 = 열 사전 ordinal 순서라 AFTER 를 쓰지 않고 뒤에 붙인다)
--    이유(2026-09-19 raw 96행 실측):
--     · raw_krit_task.task_seq('순')는 표(구분: 핵심부품/수출연계/전략부품)마다 1부터 다시 시작한다
--       → 23-4차 본공고 1~16 + 1~2, 25-1차 수정 1~18 + 1~4 처럼 (round_id, notice_type, task_no) PK 가 충돌한다.
--       24-1차 예비 11행은 '순' 자리에 구분값('핵심'·'수출')이 들어 있어 숫자도 아니다.
--       → task_no 는 (round_id, notice_type) 안에서 raw row_id 순으로 새로 매기고, 원문은 task_seq_text 에 보존한다.
--     · gov_fund_text 는 차수마다 단위가 다르다(23-4차 '14.64억' / 26-2차 본공고 '10.35억원' / 26-2차 예비 '1,657'=백만원,
--       24-1차 예비는 정부지원금 자체가 없고 총과제비만 extra_json). 원문·단위 근거를 함께 남긴다.
--     · 같은 차수 안에서 예비→본공고, 수정→재공고로 같은 과제가 다시 공고된다(25-1차 3쌍, 26-2차 20쌍).
--       is_latest 는 (round_id, task_name)별 최신 공고 1행 = 1. is_counted 는 같은 값으로 채운다(기존 열 의미 유지).
-- -----------------------------------------------------------------------------
SET @has_col = (SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'clean_krit_task' AND COLUMN_NAME = 'is_latest');
SET @q = IF(@has_col = 0,
  "ALTER TABLE clean_krit_task
     ADD COLUMN task_seq_text       VARCHAR(10)  NULL COMMENT 'raw task_seq 원문(표 안 순번. 24-1차 예비는 구분값 핵심/수출)',
     ADD COLUMN gov_fund_text       VARCHAR(30)  NULL COMMENT 'raw gov_fund_text 원문(14.64억 / 10.35억원 / 1,657)',
     ADD COLUMN gov_fund_unit_text  VARCHAR(30)  NULL COMMENT '원본 헤더가 밝힌 금액 단위(억 / 억원 / 백만원 / 없음). extra_json[원본열명] 근거',
     ADD COLUMN dev_period_text     VARCHAR(30)  NULL COMMENT 'raw dev_period_text 원문(36개월 / 36)',
     ADD COLUMN note                VARCHAR(300) NULL COMMENT 'raw note 원문(비고). 자리표시 - · 는 NULL',
     ADD COLUMN notice_order        TINYINT      NOT NULL DEFAULT 0 COMMENT '공고 진행 순서 예비1<본공고2<수정3<재공고4 (잠정 규칙, is_latest 계산용)',
     ADD COLUMN is_latest           TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '같은 차수·같은 과제명 중 최신 공고 1행 = 1. 차수별 과제 수는 이 열로만 센다',
     ADD COLUMN dup_task_row_count  SMALLINT     NOT NULL DEFAULT 1 COMMENT '같은 (round_id, task_name) raw 행 수(예비+본공고 등)',
     ADD COLUMN cleaned_by          VARCHAR(50)  NULL COMMENT '정제 담당(CURRENT_USER)',
     COMMENT = 'B1 KRIT 국산화 대상 과제 정제(raw 96행 1:1. 차수별 과제 수는 is_latest=1 로 센다 — 예비·본·재공고 합산 금지)'",
  "SELECT 'clean_krit_task.is_latest already exists, ALTER skipped' AS info");
PREPARE s1 FROM @q; EXECUTE s1; DEALLOCATE PREPARE s1;


-- -----------------------------------------------------------------------------
-- §2 clean_openfiscal_program_budget — 열린재정 방위사업청 일반회계 세부사업 예산(2016~2027, raw 2,860행 1:1)
--    키: raw_row_id(PK). 업무 키 (회계연도·프로그램명·단위사업명·세부사업명) 는 2,860 고유(2026-09-19 실측)이지만
--        문자열 길이 합이 400자라 UNIQUE 대신 KEY 로 둔다.
--    제외한 raw 열(명세 §3-4 · data-cleaning-rules §2-12): seq_no(No.) · ministry_name(방위사업청 1값) · account_name(일반회계 1값)
--        · sub_account_name(계정명 — 2,860행 전부 공란) · sector_name · field_name(각 1값) · source_file · source_row_no.
--    금액: 원본 천원 쉼표 문자열 → _krw_k(BIGINT, 천원) + _100m_krw(DECIMAL, 억원 = 천원 ÷ 100,000. 나눗셈만이라 반올림하지 않는다).
--    is_unconfirmed: 그 회계연도의 국회확정금액 합이 0이면 1(2027 268행 = 정부안만 있는 상태). 0원이 아니라 미확정이라는 뜻이다.
--        연도 합이 0이 아닌 해의 개별 0행(2017·2018·2020·2025·2026 각 1행, 2022 5행)은 실제 미반영이므로 0 그대로 둔다.
--    budget_group_candidate: ⑤ 탭 예산 3선의 키워드 후보값일 뿐 확정 분류가 아니다. 부품국산화·국방반도체 행은 국방기술개발 단위사업
--        안에도 들어 있으므로(is_unit_tech_dev=1) 세 값을 더하면 중복 집계된다.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clean_openfiscal_program_budget (
  raw_row_id              BIGINT UNSIGNED NOT NULL COMMENT 'PK. → raw_openfiscal_program_budget.row_id (raw 1:1)',
  fiscal_year             SMALLINT        NOT NULL COMMENT '회계연도 2016~2027(편성 연도. 사건 날짜 아님)',
  program_name            VARCHAR(100)    NOT NULL COMMENT '프로그램명',
  unit_program_name       VARCHAR(100)    NOT NULL COMMENT '단위사업명. 시계열 대표 축은 국방기술개발',
  sub_program_name        VARCHAR(200)    NOT NULL COMMENT '세부사업명(원문). 2021·2023 개편이 있어 연도 간 직접 비교 금지',
  sub_program_key         VARCHAR(200)    NOT NULL COMMENT '세부사업명 표기 정규화 키(공백·(R&D)·(방사청) 제거). 표기만 바뀐 사업을 잇는 용도',
  sub_program_first_year  SMALLINT        NOT NULL COMMENT '이 sub_program_key 가 자료에 처음 나온 회계연도',
  sub_program_last_year   SMALLINT        NOT NULL COMMENT '이 sub_program_key 가 자료에 마지막으로 나온 회계연도',
  expense_type            VARCHAR(50)     NULL COMMENT '경비구분(원문)',
  outlay_type             VARCHAR(50)     NULL COMMENT '지출구분(원문)',
  gov_plan_krw_k          BIGINT          NOT NULL COMMENT '정부안금액(천원). 원본 쉼표 문자열 → 숫자',
  gov_plan_100m_krw       DECIMAL(18,5)   NOT NULL COMMENT '정부안금액(억원) = 천원 ÷ 100,000',
  confirmed_krw_k         BIGINT          NOT NULL COMMENT '국회확정금액(천원). 2027은 전부 0 = 미확정(is_unconfirmed)',
  confirmed_100m_krw      DECIMAL(18,5)   NOT NULL COMMENT '국회확정금액(억원)',
  amount_basis            ENUM('확정','정부안') NOT NULL COMMENT '그 회계연도 확정액 합이 0이면 정부안. v_budget_rnd_yearly 와 같은 규칙',
  is_unconfirmed          TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 국회확정 전(정부안만). 확정액 0을 0원으로 읽지 말 것',
  is_unit_tech_dev        TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 단위사업 국방기술개발(⑤ 탭 대표 시계열 대상)',
  budget_group_candidate  VARCHAR(20)     NULL COMMENT '⑤ 탭 예산 3선 키워드 후보: 국방반도체 / 부품국산화 / 국방기술개발. 확정 분류 아님, 합산 금지',
  budget_group_basis      VARCHAR(200)    NULL COMMENT '후보값을 붙인 근거(어느 열의 어떤 패턴에 걸렸는지)',
  cleaned_at              DATETIME        NULL,
  cleaned_by              VARCHAR(50)     NULL,
  PRIMARY KEY (raw_row_id),
  KEY ix_copb_year_unit (fiscal_year, unit_program_name(50)),
  KEY ix_copb_key (sub_program_key(100), fiscal_year),
  KEY ix_copb_group (budget_group_candidate, fiscal_year),
  CONSTRAINT fk_copb_raw FOREIGN KEY (raw_row_id) REFERENCES raw_openfiscal_program_budget (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='열린재정 방위사업청 세부사업 예산 정제 2,860행(2016~2027). 배경 ④ 전용 — 관세청 수입액·조달계획과 합산·비율 금지';


-- -----------------------------------------------------------------------------
-- §3 clean_openfiscal_program_link — 세부사업명 개편 구간 연결표
--    "사업명 개편 구간은 상위 사업(단위사업) 합계로 연결" 하되, 어떤 이름이 어떤 이름으로 바뀌었는지는 공식 근거가 없으므로
--    표기 정규화로 확인되는 것만 '확정'이고 나머지는 '후보'·'미확인'이다. 근거 없는 1:1 연결을 만들지 않는다.
--      link_type 표기변경 : sub_program_key 가 같고 원문 표기만 다름((R&D)·(방사청) 접미) → link_status 확정
--      link_type 승계 후보: 같은 프로그램·단위사업 안에서 한 세부사업이 Y년에 끝나고 다른 세부사업이 Y+1년에 시작 → link_status 후보
--                           (다중 후보면 candidate_count>1 — 1:1로 확정하지 않는다)
--      link_type 종료/신설: 짝을 찾지 못한 단절 → link_status 미확인
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clean_openfiscal_program_link (
  link_id                INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  program_name           VARCHAR(100)  NOT NULL COMMENT '프로그램명(연결을 찾은 범위)',
  unit_program_name      VARCHAR(100)  NOT NULL COMMENT '단위사업명(연결을 찾은 범위. 상위 합계 축)',
  from_sub_program_name  VARCHAR(200)  NULL COMMENT '바뀌기 전 세부사업명(신설이면 NULL)',
  from_last_year         SMALLINT      NULL COMMENT '바뀌기 전 이름의 마지막 회계연도',
  to_sub_program_name    VARCHAR(200)  NULL COMMENT '바뀐 뒤 세부사업명(종료면 NULL)',
  to_first_year          SMALLINT      NULL COMMENT '바뀐 뒤 이름의 첫 회계연도',
  link_type              ENUM('표기변경','승계 후보','신설','종료') NOT NULL COMMENT '연결 유형',
  link_status            ENUM('확정','후보','미확인') NOT NULL DEFAULT '미확인' COMMENT '표기변경만 확정. 승계는 후보, 짝 없으면 미확인',
  candidate_count        SMALLINT      NOT NULL DEFAULT 0 COMMENT '같은 from 에 대한 to 후보 수(>1이면 1:1 연결 불가)',
  link_basis             VARCHAR(300)  NULL COMMENT '판정 근거(정규화 키 동일 / 연도 인접 등). 공식 개편 고시를 확인한 것이 아님',
  created_at             DATETIME      NULL,
  created_by             VARCHAR(50)   NULL,
  PRIMARY KEY (link_id),
  KEY ix_copl_unit (unit_program_name(50), link_status),
  KEY ix_copl_from (from_sub_program_name(80)),
  KEY ix_copl_to (to_sub_program_name(80))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='열린재정 세부사업명 개편 연결표(2021·2023 개편). 확정=표기 차이만, 승계는 후보 — 공식 근거 없음';


-- -----------------------------------------------------------------------------
-- §4 meta_column_dict (db/column_dict.csv 와 같은 내용. 43행)
-- -----------------------------------------------------------------------------
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_krit_task', 17, 'task_seq_text', '순', 'VARCHAR(10)', '원문 순번(표마다 1부터. 24-1차 예비는 구분값 핵심/수출)'),
('clean_krit_task', 18, 'gov_fund_text', '정부지원\\n연구개발비', 'VARCHAR(30)', '정부지원 연구개발비 원문(14.64억 / 10.35억원 / 1,657)'),
('clean_krit_task', 19, 'gov_fund_unit_text', '(원본 헤더)', 'VARCHAR(30)', '원본 헤더가 밝힌 금액 단위(억 / 억원 / 백만원 / 없음)'),
('clean_krit_task', 20, 'dev_period_text', '개발\\n기간', 'VARCHAR(30)', '개발 기간 원문(36개월 / 36)'),
('clean_krit_task', 21, 'note', '비고', 'VARCHAR(300)', '비고 원문. 자리표시 - · 는 NULL'),
('clean_krit_task', 22, 'notice_order', '(파생)', 'TINYINT', '공고 진행 순서 예비1<본공고2<수정3<재공고4 (잠정)'),
('clean_krit_task', 23, 'is_latest', '(파생)', 'TINYINT(1)', '같은 차수·과제명 중 최신 공고 1행 = 1. 차수별 과제 수는 이 열로만 센다'),
('clean_krit_task', 24, 'dup_task_row_count', '(파생)', 'SMALLINT', '같은 (round_id, task_name) raw 행 수'),
('clean_krit_task', 25, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('clean_openfiscal_program_budget', 1, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', 'PK. 원본 행 추적(FK, raw 1:1)'),
('clean_openfiscal_program_budget', 2, 'fiscal_year', '회계연도', 'SMALLINT', '회계연도 2016~2027(편성 연도)'),
('clean_openfiscal_program_budget', 3, 'program_name', '프로그램명', 'VARCHAR(100)', '프로그램명'),
('clean_openfiscal_program_budget', 4, 'unit_program_name', '단위사업명', 'VARCHAR(100)', '단위사업명. 시계열 대표 축은 국방기술개발'),
('clean_openfiscal_program_budget', 5, 'sub_program_name', '세부사업명', 'VARCHAR(200)', '세부사업명 원문. 2021·2023 개편으로 연도 간 직접 비교 금지'),
('clean_openfiscal_program_budget', 6, 'sub_program_key', '(파생)', 'VARCHAR(200)', '세부사업명 표기 정규화 키(공백·(R&D)·(방사청) 제거)'),
('clean_openfiscal_program_budget', 7, 'sub_program_first_year', '(파생)', 'SMALLINT', '정규화 키가 자료에 처음 나온 회계연도'),
('clean_openfiscal_program_budget', 8, 'sub_program_last_year', '(파생)', 'SMALLINT', '정규화 키가 자료에 마지막으로 나온 회계연도'),
('clean_openfiscal_program_budget', 9, 'expense_type', '경비구분', 'VARCHAR(50)', '경비구분 원문'),
('clean_openfiscal_program_budget', 10, 'outlay_type', '지출구분', 'VARCHAR(50)', '지출구분 원문'),
('clean_openfiscal_program_budget', 11, 'gov_plan_krw_k', '정부안금액', 'BIGINT', '정부안금액(천원). 쉼표 제거 후 숫자'),
('clean_openfiscal_program_budget', 12, 'gov_plan_100m_krw', '(파생)', 'DECIMAL(18,5)', '정부안금액(억원) = 천원 / 100,000'),
('clean_openfiscal_program_budget', 13, 'confirmed_krw_k', '국회확정금액', 'BIGINT', '국회확정금액(천원). 2027은 전부 0 = 미확정'),
('clean_openfiscal_program_budget', 14, 'confirmed_100m_krw', '(파생)', 'DECIMAL(18,5)', '국회확정금액(억원)'),
('clean_openfiscal_program_budget', 15, 'amount_basis', '(파생)', 'ENUM', '확정 / 정부안(그 해 확정액 합이 0)'),
('clean_openfiscal_program_budget', 16, 'is_unconfirmed', '(파생)', 'TINYINT(1)', '1 = 국회확정 전. 0원이 아님'),
('clean_openfiscal_program_budget', 17, 'is_unit_tech_dev', '(파생)', 'TINYINT(1)', '1 = 단위사업 국방기술개발'),
('clean_openfiscal_program_budget', 18, 'budget_group_candidate', '(파생)', 'VARCHAR(20)', '⑤ 탭 예산 3선 키워드 후보(확정 아님, 합산 금지)'),
('clean_openfiscal_program_budget', 19, 'budget_group_basis', '(파생)', 'VARCHAR(200)', '후보값 판정 근거'),
('clean_openfiscal_program_budget', 20, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_openfiscal_program_budget', 21, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('clean_openfiscal_program_link', 1, 'link_id', '(파생)', 'INT UNSIGNED', 'PK. 자동 증가'),
('clean_openfiscal_program_link', 2, 'program_name', '프로그램명', 'VARCHAR(100)', '연결을 찾은 범위(프로그램)'),
('clean_openfiscal_program_link', 3, 'unit_program_name', '단위사업명', 'VARCHAR(100)', '연결을 찾은 범위(단위사업, 상위 합계 축)'),
('clean_openfiscal_program_link', 4, 'from_sub_program_name', '세부사업명', 'VARCHAR(200)', '바뀌기 전 세부사업명(신설이면 NULL)'),
('clean_openfiscal_program_link', 5, 'from_last_year', '(파생)', 'SMALLINT', '바뀌기 전 이름의 마지막 회계연도'),
('clean_openfiscal_program_link', 6, 'to_sub_program_name', '세부사업명', 'VARCHAR(200)', '바뀐 뒤 세부사업명(종료면 NULL)'),
('clean_openfiscal_program_link', 7, 'to_first_year', '(파생)', 'SMALLINT', '바뀐 뒤 이름의 첫 회계연도'),
('clean_openfiscal_program_link', 8, 'link_type', '(파생)', 'ENUM', '표기변경 / 승계 후보 / 신설 / 종료'),
('clean_openfiscal_program_link', 9, 'link_status', '(파생)', 'ENUM', '확정(표기 차이만) / 후보 / 미확인'),
('clean_openfiscal_program_link', 10, 'candidate_count', '(파생)', 'SMALLINT', '같은 from 의 to 후보 수(>1이면 1:1 연결 불가)'),
('clean_openfiscal_program_link', 11, 'link_basis', '(파생)', 'VARCHAR(300)', '판정 근거. 공식 개편 고시를 확인한 것이 아님'),
('clean_openfiscal_program_link', 12, 'created_at', '(파생)', 'DATETIME', '생성 시각'),
('clean_openfiscal_program_link', 13, 'created_by', '(파생)', 'VARCHAR(50)', '생성 담당')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);


-- §5 검증 (같은 클라이언트 또는 DBHub)
-- SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='clean_krit_task';        -- 25
-- SHOW TABLES LIKE 'clean_openfiscal%';                                                                                   -- 2
-- SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES
--  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME LIKE 'clean_openfiscal%';                                                 -- utf8mb4_unicode_ci
-- SELECT table_name, COUNT(*) FROM meta_column_dict
--  WHERE table_name IN ('clean_krit_task','clean_openfiscal_program_budget','clean_openfiscal_program_link')
--  GROUP BY table_name;                                                                                                   -- 25 / 21 / 12
-- [적재 후 검산]
-- SELECT (SELECT COUNT(*) FROM raw_krit_task) raw_n, (SELECT COUNT(*) FROM clean_krit_task) clean_n,
--        (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name='raw_krit_task') excluded_n;                            -- 96 = 96 + 0
-- SELECT round_id, SUM(is_latest) latest_n, COUNT(*) rows_ FROM clean_krit_task GROUP BY 1;                                -- 23-4 18/18 · 24-1 11/11 · 25-1 22/25 · 26-1 2/2 · 26-2 20/40
-- SELECT (SELECT COUNT(*) FROM raw_openfiscal_program_budget) raw_n,
--        (SELECT COUNT(*) FROM clean_openfiscal_program_budget) clean_n;                                                   -- 2,860 = 2,860
-- SELECT fiscal_year, amount_basis, ROUND(SUM(gov_plan_100m_krw),1) total_gov_100m,
--        ROUND(SUM(CASE WHEN is_unit_tech_dev=1 THEN gov_plan_100m_krw ELSE 0 END),1) tech_dev_100m
--   FROM clean_openfiscal_program_budget GROUP BY 1,2;                                       -- v_budget_rnd_yearly 의 total_gov_100m·tech_dev_gov_100m 와 동일해야 함
