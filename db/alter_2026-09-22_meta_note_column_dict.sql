-- =============================================================================
-- meta_dataset.note 정정 1행 + meta_column_dict 미등재 8열 등재  (작성·적용 2026-09-22)
--   표·뷰 구조 변경 없음. 근거: docs/next.md A3(사전 미등재 8열) + 명세서 생성 중 확인한 note 구버전 1행.
-- 1) ref_hs_whitelist note — 2026-09-21 삭제된 related_fsc 열·b2_scope 문구가 남아 있어 현재 기준(M5: R1 OR R2, 13개, R4·카테고리 맵 폐기)으로 교체.
-- 3) ref_hs_whitelist.evidence dtype 사전 VARCHAR(50) → RDS 실측 VARCHAR(120)으로 정정(gen_data_spec_xlsx.py 경고).
-- 2) 열 사전 8행 — raw_krit_task 5(round_label·notice_type·extra_json·table_index·source_url), raw_kosis_* source_col_no 2, clean_kdsis_nsn.cleaned_at 1.
--    db/column_dict.csv 에 같은 8행을 추가했다(사전 823 → 831).
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-22_meta_note_column_dict.sql   기대: 1회차 UPDATE 1·INSERT 8·UPDATE 1, 2회차 0
-- =============================================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

UPDATE meta_dataset
SET note = '24개 = 수집 기준. 분석 대상은 priority 1·2 = 13개(진입 규칙 R1 OR R2, 2026-09-21 M5 — R4·카테고리 맵 폐기, related_fsc 열 삭제). priority 3 = 규칙 미해당 11개(「근거 미확인」). civil_mix 는 v_civil_mix_rule 규칙값(hs10 / hsk / 판단불가). 2026-09-16 규칙 도출로 21→24(852910·901410·901490). 정의·선정 규칙: docs/reference/hs-whitelist-definition.md §2·§8',
    updated_on = '2026-09-21'
WHERE dataset_key = 'ref_hs_whitelist' AND note LIKE '%related_fsc·evidence%';

INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('raw_krit_task', 6, 'round_label', '(파일명)', 'VARCHAR(20)', '차수 원문(예 `26-1차`). parse_krit.py 가 파일명에서 부여'),
('raw_krit_task', 7, 'notice_type', '(파일명)', 'VARCHAR(20)', '예비 / 본공고 / 재공고 / 수정 — 파일명 토큰. 사업 구분(핵심·전략·수출연계)은 extra_json["구분(표제목)"]'),
('raw_krit_task', 8, 'extra_json', '(차수별 추가 열)', 'TEXT', '표마다 다른 열을 {"원본열명": "값"} JSON 문자열로 보존(총과제비·구분(표제목) 등)'),
('raw_krit_task', 9, 'table_index', '(파생)', 'SMALLINT', '문서 내 표 번호(parse_krit.py _tN). pdf 는 쪽 내 번호, 쪽은 source_file 의 _p<쪽>'),
('raw_krit_task', 10, 'source_url', '(파생)', 'VARCHAR(300)', '원문 공고 URL(방위사업청 공지 미러). 원문 8건 URL·SHA-256 은 docs/data-sources.md KRIT 표'),
('raw_kosis_utilization', 4, 'source_col_no', '(셀 위치)', 'SMALLINT', '광폭 원본의 열 번호(1부터). 세로형 변환 전 위치 추적(source_row_no 와 짝)'),
('raw_kosis_production_index', 6, 'source_col_no', '(셀 위치)', 'SMALLINT', '광폭 원본의 열 번호(1부터). stat_ym 이 `p)` 인 결함 16행(253~256)의 월 복원 근거(clean is_month_restored)'),
('clean_kdsis_nsn', 24, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각')
AS new
ON DUPLICATE KEY UPDATE ordinal = new.ordinal, original_name = new.original_name, dtype = new.dtype, description = new.description;

UPDATE meta_column_dict SET dtype = 'VARCHAR(120)'
WHERE table_name = 'ref_hs_whitelist' AND column_name = 'evidence' AND dtype <> 'VARCHAR(120)';
