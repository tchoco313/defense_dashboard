-- 2026-09-20 meta_dataset 해시·크기 정정 (docs/report/data/file-cleanup-audit-2026-09-20.md §2·§5-2)
-- 실행: python scripts/apply_alter.py db/alter_2026-09-20_meta_dataset_sha.sql (admin). 멱등 — WHERE 가 옛 값에만 맞는다.
-- 근거(2026-09-20 실측):
--   customs_progress : DB 값은 09-14 231행판(7,471 B, af359f89…). 현행 data/raw/customs/progress_all.csv 는 264행 8,538 B fc1d199e…
--                      이고 raw_customs_progress 264행과 행 해시 합산 일치.
--   ref_hs_whitelist : DB 값은 09-18 열 추가 전 파일. 현행 data/reference/hs_whitelist.csv(24행·17열, 14,363 B 47ca912f…)와
--                      ref_hs_whitelist 24행이 17열 전부 행 해시 일치.
--   krit_task        : sha256 이 12파일 중 26-1차_…_t7.csv 1개 값(809a9704…)이고 file_bytes 는 12파일 합. 다중 파일 데이터셋은
--                      sha256 을 비우고(DDL 주석 "단일 파일일 때") 파일별 SHA 는 docs/data-sources.md 표에 둔다.
USE defense_dashboard;

UPDATE meta_dataset
   SET sha256 = 'fc1d199e1204c57430252e6276131a51b348c67a9ad43d07946aa44538f6ba50',
       file_bytes = 8538
 WHERE dataset_key = 'customs_progress'
   AND sha256 = 'af359f891874e5ecaf758328ae03f64aca661817b68044857839eca58a3f9f23';

UPDATE meta_dataset
   SET sha256 = '47ca912f28937caf3da27fec16f57020567c0779f1c1978a5a68e47fc357d58e',
       file_bytes = 14363
 WHERE dataset_key = 'ref_hs_whitelist'
   AND sha256 = 'ac8ceefa2c860b95a9e9571e86b90f8379fb6907be3973f2aff1b6a9cafc0543';

UPDATE meta_dataset
   SET sha256 = NULL,
       note = CONCAT_WS(' | ', NULLIF(note, ''), '다중 파일(12)이라 sha256 없음, file_bytes 는 12파일 합. 파일별 SHA-256 은 docs/data-sources.md KRIT 표(2026-09-20 정정)')
 WHERE dataset_key = 'krit_task'
   AND sha256 = '809a9704a14e19540321c073de9ac6b232c9d9c7249a6e401e0df1a1b36d9149';

SELECT dataset_key, file_bytes, LEFT(sha256, 16) sha16 FROM meta_dataset
 WHERE dataset_key IN ('customs_progress', 'ref_hs_whitelist', 'krit_task');
