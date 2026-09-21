-- =============================================================================
-- meta_dataset: 팀원 공유 파일 3건의 data.go.kr ID·URL·포털 등록/수정일 채움 + 군별 계약집행 범위 라벨  (작성·적용 2026-09-21)
--   근거 docs/report/feedback/open-decisions-2026-09-21.md D10·D11. 표·뷰 변경 없음, UPDATE 4문.
-- D10 확인(2026-09-21 포털 웹 조회): 제목·기준일·행 수가 확보본과 일치
--   · 국외조달 조달계획_20251231  → 15050925 (등록 2026-01-14 · 수정 2026-01-14, 3,029행 = 확보본)
--   · 국외조달 입찰결과_20250915  → 15050923 (등록 2026-01-12 · 수정 2026-01-13, 열 13 = 확보본)
--   · 국내조달 조달계획_20251231  → 15050919 (등록 2026-01-12 · 수정 2026-01-12, 35,859행 = 확보본)
--   다운로드일은 팀원 공유분이라 여전히 미상 → acquired_on(공유 수령일 2026-09-15) 유지.
-- D11 추론: 포털 설명은 "국방전자조달 군구분별 계약집행 … 국방조달규모"이며 국내·국외 구분 언급 없음. 연 15~16조(2019~2024)는
--   방사청 전체 계약 규모 수준이라 국내조달만으로 보기 어렵다 → 라벨 「계약집행액(억원) — 국내·국외 구분 없는 총액」. 「국내+국외 합계」로 단정하지 않는다.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-21_meta_dataset_ids.sql   기대: 1회차 rows 1·1·1·1, 2회차 0
-- =============================================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

UPDATE meta_dataset
SET dataset_id = '15050925', url = 'https://www.data.go.kr/data/15050925/fileData.do',
    published_on = '2026-01-14', updated_on = '2026-01-14',
    note = 'A7 배경 ⓪. 팀원 공유분(new_data/방위사업청_국외조달 조달계획_20251231.csv), ID 15050925 · 포털 3,029행 일치(2026-09-21 확인), 다운로드일 미상(공유 수령 2026-09-15). 판단번호 고유 3,024. 예산금액은 집행 예정액·국가 없음 → 관세청 수입액과 합산·비교 금지. officer_name은 적재 시 NULL'
WHERE dataset_key = 'dapa_overseas_plan' AND dataset_id IS NULL;

UPDATE meta_dataset
SET dataset_id = '15050923', url = 'https://www.data.go.kr/data/15050923/fileData.do',
    published_on = '2026-01-12', updated_on = '2026-01-13',
    note = 'A7 배경 보조(유찰률). 팀원 공유분, ID 15050923 · 포털 열 13 일치(2026-09-21 확인), 다운로드일 미상(공유 수령 2026-09-15). 개찰 2025-01~09 부분연도. 판단번호 고유 97(조달계획과 교집합 83)'
WHERE dataset_key = 'dapa_overseas_bid_result' AND dataset_id IS NULL;

UPDATE meta_dataset
SET dataset_id = '15050919', url = 'https://www.data.go.kr/data/15050919/fileData.do',
    published_on = '2026-01-12', updated_on = '2026-01-12',
    note = 'A7 보조(국내 vs 국외 규모). 팀원 공유분, ID 15050919 · 포털 35,859행 일치(2026-09-21 확인), 다운로드일 미상(공유 수령 2026-09-15). 1만 건 요건에는 쓰지 않음. 2024 4,545 / 2025 31,314. officer_name·officer_phone은 적재 시 NULL'
WHERE dataset_key = 'dapa_domestic_plan' AND dataset_id IS NULL;

UPDATE meta_dataset
SET note = 'A7 KPI. 팀원 공유분(원 파일명 ''방위사업청_군별 계약집행 현황_20241231 (1).csv''). 2015~2024 × 육군/해군/공군/국직. 포털 15070269(등록 2025-12-31·수정 2026-01-02) 설명 "국방전자조달 군구분별 계약집행 … 국방조달규모"에 국내·국외 구분 없음 → 라벨 「계약집행액(억원) — 국내·국외 구분 없는 총액」(연 15~16조는 방사청 전체 계약 규모 수준, 추론). 「국내+국외 합계」로 단정하지 않는다'
WHERE dataset_key = 'dapa_contract_exec_by_service' AND note LIKE '%국내·국외 조달 포함 여부 미확인%';

-- 검증: SELECT dataset_key, dataset_id, published_on, updated_on FROM meta_dataset WHERE dataset_key IN ('dapa_overseas_plan','dapa_overseas_bid_result','dapa_domestic_plan');
--       SELECT COUNT(*) FROM meta_dataset WHERE dataset_id IS NULL;   -- 0
