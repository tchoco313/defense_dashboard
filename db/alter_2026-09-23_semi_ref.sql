-- =============================================================================
-- 국방반도체 발전전략 참조표 7개 신설 (작성 2026-09-23)
--
-- 원본: data/reference/semi_*.csv 7개(utf-8, 수작업). 방위사업청 「국방반도체 발전전략」(2024-11-19) PDF 참고3·9·10·본문 17-1·17-3
--       + 추진 경과·국내 사례의 보도자료·언론 기사(행마다 출처 제목·URL·검증 수준).
-- 용도: ⓪ 국외조달 예산 · 배경 페이지 「국방반도체 발전전략 · 국내 기반」 구역. 2026-09-23 사용자 결정 —
--       화면의 모든 숫자는 RDS 에서 읽는다(그전에는 페이지가 CSV 를 직접 읽었다).
-- 주의: 관세청 수입 통계와 합산·비교하지 않는다. related_hs6 는 팀이 붙인 참고 표시(team)이며 수입액 연결 키가 아니다.
--       98.9% · 85% 이상(ref_semi_stat)은 발전전략 본문 인용이며 팀 계산값이 아니다(분모 기준 미확인).
-- 구조: §1 표 7개 → §2 열 사전 → §3 meta_dataset 1행 → (적재: python scripts/load_db.py --ref — 빈 표만 채운다) → §4 검증
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-23_semi_ref.sql (재실행 가능 — IF NOT EXISTS · ON DUPLICATE KEY UPDATE)
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 표 7개 (정의는 db/schema.sql 과 동일). CSV 의 date 열은 예약어를 피해 event_date 로 넣는다(값은 원문 YYYY · YYYY-MM · YYYY-MM-DD).
CREATE TABLE IF NOT EXISTS ref_semi_chip_type (
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

CREATE TABLE IF NOT EXISTS ref_semi_domestic_case (
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

CREATE TABLE IF NOT EXISTS ref_semi_market_share (
  country   VARCHAR(20)  NOT NULL,
  segment   VARCHAR(20)  NOT NULL COMMENT 'IDM · 파운드리 · 팹리스 등',
  share_pct DECIMAL(5,1) NOT NULL COMMENT '점유율(%) — 참고3 막대그래프에서 읽은 값',
  source    VARCHAR(100) NOT NULL,
  caveat    VARCHAR(100) NOT NULL COMMENT '원출처·기준연도 미표기 등 한계',
  PRIMARY KEY (country, segment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국가별 반도체 공급망 점유율(발전전략 참고3 인용) 16행';

CREATE TABLE IF NOT EXISTS ref_semi_policy_timeline (
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

CREATE TABLE IF NOT EXISTS ref_semi_public_fab (
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

CREATE TABLE IF NOT EXISTS ref_semi_strategy_task (
  task_no        TINYINT UNSIGNED NOT NULL,
  direction_no   TINYINT UNSIGNED NOT NULL,
  direction_key  VARCHAR(10)  NOT NULL,
  direction_name VARCHAR(60)  NOT NULL,
  sub_no         TINYINT UNSIGNED NOT NULL,
  task_name      VARCHAR(80)  NOT NULL,
  source         VARCHAR(100) NOT NULL,
  PRIMARY KEY (task_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국방반도체 발전전략 4방향 12과제(본문 17-3) 12행';

CREATE TABLE IF NOT EXISTS ref_semi_stat (
  stat_key  VARCHAR(40)  NOT NULL,
  label     VARCHAR(60)  NOT NULL,
  value_num DECIMAL(6,1) NOT NULL,
  unit_txt  VARCHAR(20)  NOT NULL COMMENT '% · % 이상(하한) 등 원문 단위 표현',
  note      VARCHAR(200) NOT NULL,
  source    VARCHAR(100) NOT NULL,
  PRIMARY KEY (stat_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국방반도체 발전전략 본문 인용 수치 2행(팀 계산값 아님)';

-- §2 meta_column_dict (db/column_dict.csv 와 동일)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('ref_semi_chip_type', 1, 'type_no', 'type_no', 'TINYINT UNSIGNED', 'PK. 국방반도체 7대 유형 번호(발전전략 참고9)'),
('ref_semi_chip_type', 2, 'name_ko', 'name_ko', 'VARCHAR(50)', '유형명'),
('ref_semi_chip_type', 3, 'summary', 'summary', 'VARCHAR(200)', '유형 개요(참고9 요약)'),
('ref_semi_chip_type', 4, 'material_process', 'material_process', 'VARCHAR(50)', '소재·공정'),
('ref_semi_chip_type', 5, 'example_devices', 'example_devices', 'VARCHAR(100)', '대표 소자'),
('ref_semi_chip_type', 6, 'related_hs6', 'related_hs6', 'VARCHAR(60)', '팀이 붙인 참고 HS6(세미콜론 구분). 수입액 연결 키 아님. 없으면 NULL'),
('ref_semi_chip_type', 7, 'hs_basis', 'hs_basis', 'VARCHAR(10)', 'related_hs6 근거(team = 팀 표시)'),
('ref_semi_chip_type', 8, 'source', 'source', 'VARCHAR(100)', '출처(발전전략 참고9)'),
('ref_semi_domestic_case', 1, 'case_no', 'case_no', 'SMALLINT UNSIGNED', 'PK. 사례 번호'),
('ref_semi_domestic_case', 2, 'type_no', 'type_no', 'TINYINT UNSIGNED', 'FK ref_semi_chip_type.type_no'),
('ref_semi_domestic_case', 3, 'org', 'org', 'VARCHAR(60)', '기관·기업(공동이면 · 로 연결)'),
('ref_semi_domestic_case', 4, 'title', 'title', 'VARCHAR(150)', '사례 제목(기사·보도자료 표현)'),
('ref_semi_domestic_case', 5, 'event_date', 'date', 'VARCHAR(10)', '발표·보도일(YYYY-MM-DD 또는 YYYY-MM). 미기재 NULL'),
('ref_semi_domestic_case', 6, 'target_system', 'target_system', 'VARCHAR(80)', '적용 대상 체계(기사 표현). 미기재 NULL'),
('ref_semi_domestic_case', 7, 'stage', 'stage', 'VARCHAR(30)', '단계(양산 · 개발 착수 등 기사 표현)'),
('ref_semi_domestic_case', 8, 'source_title', 'source_title', 'VARCHAR(50)', '출처 매체·문서명'),
('ref_semi_domestic_case', 9, 'source_url', 'source_url', 'VARCHAR(255)', '출처 URL'),
('ref_semi_domestic_case', 10, 'verify_level', 'verify_level', 'VARCHAR(20)', '확인 수준(기사 원문 · 보도자료 등)'),
('ref_semi_domestic_case', 11, 'note', 'note', 'VARCHAR(120)', '비고. 없으면 NULL'),
('ref_semi_domestic_case', 12, 'dapa_2025_task', 'dapa_2025_task', 'TINYINT(1)', '1 = 방위사업청 2025 국방반도체 핵심기술 과제(2025-05-19 보도자료)'),
('ref_semi_market_share', 1, 'country', 'country', 'VARCHAR(20)', 'PK1. 국가'),
('ref_semi_market_share', 2, 'segment', 'segment', 'VARCHAR(20)', 'PK2. 공급망 단계(IDM · 파운드리 · 팹리스 등)'),
('ref_semi_market_share', 3, 'share_pct', 'share_pct', 'DECIMAL(5,1)', '점유율(%) — 발전전략 참고3 막대그래프에서 읽은 값'),
('ref_semi_market_share', 4, 'source', 'source', 'VARCHAR(100)', '출처(발전전략 참고3)'),
('ref_semi_market_share', 5, 'caveat', 'caveat', 'VARCHAR(100)', '한계(원출처·기준연도 미표기 등)'),
('ref_semi_policy_timeline', 1, 'row_no', '(행 순서)', 'SMALLINT UNSIGNED', 'PK. CSV 행 순서(시간순, 1부터) — 적재 때 붙인다'),
('ref_semi_policy_timeline', 2, 'event_date', 'date', 'VARCHAR(10)', '시점(YYYY · YYYY-MM · YYYY-MM-DD 원문)'),
('ref_semi_policy_timeline', 3, 'category', 'category', 'VARCHAR(10)', '구분(논의 · 조사 · 전략 등)'),
('ref_semi_policy_timeline', 4, 'event', 'event', 'VARCHAR(100)', '사건'),
('ref_semi_policy_timeline', 5, 'detail', 'detail', 'VARCHAR(150)', '내용'),
('ref_semi_policy_timeline', 6, 'source_title', 'source_title', 'VARCHAR(100)', '출처 문서·매체'),
('ref_semi_policy_timeline', 7, 'source_url', 'source_url', 'VARCHAR(255)', '출처 URL. PDF 원문은 NULL'),
('ref_semi_policy_timeline', 8, 'verify_level', 'verify_level', 'VARCHAR(20)', '확인 수준'),
('ref_semi_public_fab', 1, 'fab_no', 'fab_no', 'TINYINT UNSIGNED', 'PK. 나노팹 번호(참고10 순서)'),
('ref_semi_public_fab', 2, 'name_ko', 'name_ko', 'VARCHAR(40)', '기관명'),
('ref_semi_public_fab', 3, 'abbr', 'abbr', 'VARCHAR(10)', '약칭. 없으면 NULL'),
('ref_semi_public_fab', 4, 'parent_org', 'parent_org', 'VARCHAR(30)', '소속 기관. 없으면 NULL'),
('ref_semi_public_fab', 5, 'ministry', 'ministry', 'VARCHAR(10)', '소관 부처'),
('ref_semi_public_fab', 6, 'field', 'field', 'VARCHAR(60)', '분야'),
('ref_semi_public_fab', 7, 'field_group', 'field_group', 'VARCHAR(10)', '분야 묶음(실리콘 · 화합물 등)'),
('ref_semi_public_fab', 8, 'city', 'city', 'VARCHAR(10)', '도시'),
('ref_semi_public_fab', 9, 'lat', 'lat', 'DECIMAL(9,6)', '위도 — 도시 단위 근사'),
('ref_semi_public_fab', 10, 'lon', 'lon', 'DECIMAL(9,6)', '경도 — 도시 단위 근사'),
('ref_semi_public_fab', 11, 'coord_basis', 'coord_basis', 'VARCHAR(10)', '좌표 근거(approx = 도시 단위 근사)'),
('ref_semi_public_fab', 12, 'source', 'source', 'VARCHAR(100)', '출처(발전전략 참고10)'),
('ref_semi_strategy_task', 1, 'task_no', 'task_no', 'TINYINT UNSIGNED', 'PK. 과제 번호(1~12)'),
('ref_semi_strategy_task', 2, 'direction_no', 'direction_no', 'TINYINT UNSIGNED', '추진 방향 번호(1~4)'),
('ref_semi_strategy_task', 3, 'direction_key', 'direction_key', 'VARCHAR(10)', '방향 약칭(설계 · 생산 등)'),
('ref_semi_strategy_task', 4, 'direction_name', 'direction_name', 'VARCHAR(60)', '추진 방향명'),
('ref_semi_strategy_task', 5, 'sub_no', 'sub_no', 'TINYINT UNSIGNED', '방향 안 과제 순번'),
('ref_semi_strategy_task', 6, 'task_name', 'task_name', 'VARCHAR(80)', '과제명'),
('ref_semi_strategy_task', 7, 'source', 'source', 'VARCHAR(100)', '출처(발전전략 본문 17-3)'),
('ref_semi_stat', 1, 'stat_key', 'stat_key', 'VARCHAR(40)', 'PK. 인용 수치 키(overseas_share · us_share_min)'),
('ref_semi_stat', 2, 'label', 'label', 'VARCHAR(60)', '화면 라벨'),
('ref_semi_stat', 3, 'value_num', 'value_num', 'DECIMAL(6,1)', '인용 값'),
('ref_semi_stat', 4, 'unit_txt', 'unit_txt', 'VARCHAR(20)', '원문 단위 표현(% · % 이상)'),
('ref_semi_stat', 5, 'note', 'note', 'VARCHAR(200)', '조사 범위·한계(분모 기준 미확인 등). 팀 계산값 아님'),
('ref_semi_stat', 6, 'source', 'source', 'VARCHAR(100)', '출처(발전전략 본문 17-1)')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §3 meta_dataset 1행 (db/meta_dataset.csv 와 동일). 다중 파일이라 file_bytes · sha256 은 NULL
INSERT INTO meta_dataset (dataset_key, tier, provider, dataset_id, title, url, access_method, acquired_on, period_start, period_end,
                          is_partial_period, published_on, updated_on, query_condition, raw_path, file_bytes, sha256, encoding, parser,
                          raw_row_count, portal_row_count, target_table, note)
VALUES ('semi_strategy', '참조', '방위사업청 「국방반도체 발전전략」 PDF · 보도자료 · 언론 기사 / 팀 작성', NULL,
        '국방반도체 발전전략 참조표 7종(유형 · 국내 사례 · 점유율 · 추진 경과 · 공공 나노팹 · 12과제 · 인용 수치)', NULL, '수작업',
        '2026-09-20', NULL, NULL, 0, '2024-11-19', '2026-09-23', NULL, 'data/reference/semi_*.csv', NULL, NULL, 'utf-8',
        'pandas read_csv dtype=str (scripts/load_db.py --ref)', 76, NULL, 'ref_semi_*',
        '2026-09-23 RDS 적재(그전에는 ⓪ 페이지가 CSV 를 직접 읽음). 98.9% · 85% 이상은 본문 인용(ref_semi_stat). 관세청 수입액과 합산 · 비교하지 않음')
ON DUPLICATE KEY UPDATE title = VALUES(title), updated_on = VALUES(updated_on), raw_row_count = VALUES(raw_row_count), note = VALUES(note);

-- §4 검증 (적재 뒤 기대: 7 · 13 · 16 · 12 · 14 · 12 · 2 = 76, 사전 58행)
SELECT 'ref_semi_chip_type' t, COUNT(*) n FROM ref_semi_chip_type
UNION ALL SELECT 'ref_semi_domestic_case', COUNT(*) FROM ref_semi_domestic_case
UNION ALL SELECT 'ref_semi_market_share', COUNT(*) FROM ref_semi_market_share
UNION ALL SELECT 'ref_semi_policy_timeline', COUNT(*) FROM ref_semi_policy_timeline
UNION ALL SELECT 'ref_semi_public_fab', COUNT(*) FROM ref_semi_public_fab
UNION ALL SELECT 'ref_semi_strategy_task', COUNT(*) FROM ref_semi_strategy_task
UNION ALL SELECT 'ref_semi_stat', COUNT(*) FROM ref_semi_stat;
SELECT COUNT(*) AS dict_rows FROM meta_column_dict WHERE table_name LIKE 'ref_semi%';
