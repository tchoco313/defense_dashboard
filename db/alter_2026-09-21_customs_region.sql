-- =============================================================================
-- 관세청 시군구별 품목별 수출입실적(data.go.kr 15134343) raw 적재용 표 신설 (작성 2026-09-21)
--
-- 원본: data/raw/customs/customs_region_<HS6>.csv 24개(utf-8, 13열, 273,586행, 36,155,622 bytes — scripts/fetch_customs_region.py 2026-09-18 수집).
--       HS6 24개 × 시도 17개 × 2016~2026(2026은 8월까지 부분연도). 거래 없는 조합은 행이 없다. 총계행 없음.
-- 용도: 보조. 수입자 소재지(납세의무자 주소지) 기준 시군구별 수입 — 「과천시 소재 수입자 비중(추정 하한)」 검토용.
--       화면·KPI 채택 여부는 팀 결정(docs/report/feedback/open-decisions-2026-09-21.md D1). 이 파일은 raw 표만 만든다(clean·뷰 없음).
-- 주의: 금액 단위는 **천 달러**다(raw_customs_trade·fact_customs_monthly 는 달러). 합치거나 비교할 때 ×1,000.
--       검산: 880730 2025년 17개 시도 imp_usd_amt 합 745,179(천$) ↔ 품목별 국가별 API 총계 745,240,449$.
--       수입은 납세의무자 주소지, 수출은 제조장소 우편번호 기준(명세 원문). 시군구 코드는 응답에 없고 명칭(sgg_name)만 온다.
--       2026-07-01 지방행정체계 개편으로 개편 전후 명칭이 다를 수 있다 — 원본 그대로 저장.
-- 구조: §1 raw_customs_region → §2 열 사전 13행 → §3 meta_dataset 1행 → (적재: python scripts/load_db.py --raw --tables raw_customs_region) → §4 검증
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-21_customs_region.sql (재실행 가능 — IF NOT EXISTS · ON DUPLICATE KEY UPDATE)
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 raw (정의는 db/schema.sql §2와 동일). 열 순서 = CSV 헤더 순서(db/column_dict.csv). 값은 전부 문자열(금액·건수는 쉼표 포함 원문).
CREATE TABLE IF NOT EXISTS raw_customs_region (
  row_id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  stat_ym           VARCHAR(10)  NULL COMMENT '원본 priodTitle: YYYY.MM',
  sgg_name          VARCHAR(50)  NULL COMMENT '원본 sggNm: 시도 + 시군구명(예: 경기도 과천시). 코드 없음',
  hs_cd             VARCHAR(10)  NULL COMMENT '원본 hsSgn(HS6)',
  item_name_ko      VARCHAR(300) NULL COMMENT '원본 korePrlstNm',
  exp_cnt           VARCHAR(20)  NULL COMMENT '원본 expCnt(수출 건수)',
  exp_usd_amt       VARCHAR(20)  NULL COMMENT '원본 expUsdAmt — 천 달러',
  imp_cnt           VARCHAR(20)  NULL COMMENT '원본 impCnt(수입 건수)',
  imp_usd_amt       VARCHAR(20)  NULL COMMENT '원본 impUsdAmt — 천 달러. 납세의무자 주소지 기준',
  trade_balance_amt VARCHAR(20)  NULL COMMENT '원본 cmtrBlncAmt(무역수지, 천 달러)',
  req_hs            CHAR(6)      NULL,
  req_sido          CHAR(2)      NULL COMMENT '요청 시도코드(11 26 27 28 29 30 31 36 41 43 44 46 47 48 50 51 52)',
  req_year          CHAR(4)      NULL,
  fetched_at        VARCHAR(20)  NULL,
  source_file       VARCHAR(100) NOT NULL COMMENT 'customs_region_<HS6>.csv',
  source_row_no     INT UNSIGNED NULL COMMENT '파일 내 레코드 순번(헤더 제외, 1부터)',
  loaded_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rcr_hs (req_hs, req_year),
  KEY ix_rcr_key (hs_cd, sgg_name, stat_ym)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='관세청 시군구별 수출입실적 원본 273,586행(24개 HS6 × 시도 17, 2016.01~2026.08, 2026-09-18 수집). 금액 천 달러';

-- §2 meta_column_dict 13행 (db/column_dict.csv와 동일. load_db.py --ref 로도 들어감)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('raw_customs_region', 1, 'stat_ym', 'priodTitle', 'VARCHAR(10)', '연월 `YYYY.MM`. 총계행 없음'),
('raw_customs_region', 2, 'sgg_name', 'sggNm', 'VARCHAR(50)', '시도 + 시군구명(예: 경기도 과천시, 고유 234). 시군구 코드는 응답에 없다. 2026-07-01 행정체계 개편 전후 명칭이 다를 수 있음 — 원본 그대로'),
('raw_customs_region', 3, 'hs_cd', 'hsSgn', 'VARCHAR(10)', 'HS6(요청값 req_hs 와 전부 같음)'),
('raw_customs_region', 4, 'item_name_ko', 'korePrlstNm', 'VARCHAR(300)', 'HS6 품명(관세청 표기)'),
('raw_customs_region', 5, 'exp_cnt', 'expCnt', 'VARCHAR(20)', '수출 건수(쉼표 포함 원문)'),
('raw_customs_region', 6, 'exp_usd_amt', 'expUsdAmt', 'VARCHAR(20)', '수출금액 — **천 달러**(raw_customs_trade 는 달러). 제조장소 우편번호 기준'),
('raw_customs_region', 7, 'imp_cnt', 'impCnt', 'VARCHAR(20)', '수입 건수(쉼표 포함 원문)'),
('raw_customs_region', 8, 'imp_usd_amt', 'impUsdAmt', 'VARCHAR(20)', '수입금액 — **천 달러**(raw_customs_trade 는 달러). 납세의무자 주소지 우편번호 기준. 검산: 880730 2025 합 745,179'),
('raw_customs_region', 9, 'trade_balance_amt', 'cmtrBlncAmt', 'VARCHAR(20)', '무역수지(천 달러) = 수출 − 수입. 파생값이라 계산에 쓰지 않음'),
('raw_customs_region', 10, 'req_hs', 'req_hs', 'CHAR(6)', '요청 HS6(화이트리스트)'),
('raw_customs_region', 11, 'req_sido', 'req_sido', 'CHAR(2)', '요청 시도코드(17개)'),
('raw_customs_region', 12, 'req_year', 'req_year', 'CHAR(4)', '요청 연도(2016~2026, 2026은 8월까지)'),
('raw_customs_region', 13, 'fetched_at', 'fetched_at', 'VARCHAR(20)', '수집일')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §3 meta_dataset 1행 (db/meta_dataset.csv와 동일). 다중 파일이라 sha256 은 NULL — 파일별 크기·해시는 docs/data-sources.md
INSERT INTO meta_dataset (dataset_key, tier, provider, dataset_id, title, url, access_method, acquired_on, period_start, period_end, is_partial_period, query_condition, raw_path, file_bytes, sha256, encoding, parser, raw_row_count, target_table, note) VALUES
('customs_region', '보조', '관세청', '15134343', '시군구별 품목별 수출입실적 (HS6 24개 × 시도 17 × 2016~2026)', 'https://www.data.go.kr/data/15134343/openapi.do', 'OpenAPI', '2026-09-18', '2016-01-01', '2026-08-31', 1,
 'fetch_customs_region.py: HsSgn=<HS6> × sidoCd=<17개> × strtYymm/endYymm=<연도> 1년 범위, 4,488호출', 'data/raw/customs/customs_region_*.csv', 36155622, NULL, 'utf-8',
 'pandas read_csv dtype=str keep_default_na=False', 273586, 'raw_customs_region',
 '24개 파일, 2026-09-21 RDS 적재. 수입은 납세의무자 주소지, 수출은 제조장소 기준. 금액 단위 천 달러(품목별 국가별 API는 달러). 2026-07-01 행정개편으로 시군구 명칭 변경 주의. 파일별 크기·SHA-256·검증(과천 비중)은 docs/data-sources.md. 포털 등록·수정일 미확인. 화면 채택 여부는 팀 결정(open-decisions D1)')
ON DUPLICATE KEY UPDATE tier = VALUES(tier), provider = VALUES(provider), dataset_id = VALUES(dataset_id), title = VALUES(title), url = VALUES(url), access_method = VALUES(access_method), acquired_on = VALUES(acquired_on), period_start = VALUES(period_start), period_end = VALUES(period_end), is_partial_period = VALUES(is_partial_period), query_condition = VALUES(query_condition), raw_path = VALUES(raw_path), file_bytes = VALUES(file_bytes), encoding = VALUES(encoding), parser = VALUES(parser), raw_row_count = VALUES(raw_row_count), target_table = VALUES(target_table), note = VALUES(note);

-- §4 검증 (적재 후 손으로 실행)
-- SELECT COUNT(*) FROM raw_customs_region;                                                          -- 273,586
-- SELECT COUNT(DISTINCT source_file), COUNT(DISTINCT req_hs), COUNT(DISTINCT sgg_name) FROM raw_customs_region;   -- 24 · 24 · 234
-- SELECT SUM(CAST(REPLACE(imp_usd_amt, ',', '') AS SIGNED)) FROM raw_customs_region WHERE req_hs='880730' AND req_year='2025';   -- 745,179(천$)
-- SELECT table_collation FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='raw_customs_region';       -- utf8mb4_unicode_ci
-- SELECT COUNT(*) FROM meta_column_dict;                                                            -- 849 + 13 = 862
