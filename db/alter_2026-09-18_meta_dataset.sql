-- 2026-09-18 meta_dataset 보완 (evidence-reliability-review-2026-09-17.md §6 A-6)
-- 실행: docs/runbook/commands.md "증분 변경" 방식(mariadb.exe, 계정 defense). 멱등.
-- 기대: customs_all·customs_progress published_on 2022-05-25 / updated_on 2026-05-22,
--       dapa_contract is_partial_period 1 (2024는 11~12월만 12,304행, 2025 완결 30,808행 — raw_dapa_contract 실측)
USE defense_dashboard;

UPDATE meta_dataset
   SET published_on = '2022-05-25',
       updated_on   = '2026-05-22',
       note = CONCAT_WS(' | ', NULLIF(note, ''), '포털 등록 2022-05-25·수정 2026-05-22·갱신주기 1개월(2026-09-18 확인)')
 WHERE dataset_key IN ('customs_all', 'customs_progress')
   AND published_on IS NULL;

UPDATE meta_dataset
   SET is_partial_period = 1,
       note = CONCAT_WS(' | ', NULLIF(note, ''), '2024는 11~12월만 12,304행(부분연도), 2025 완결 30,808행(팀 DB 2026-09-18 실측)')
 WHERE dataset_key = 'dapa_contract'
   AND is_partial_period = 0;

SELECT dataset_key, is_partial_period, published_on, updated_on FROM meta_dataset
 WHERE dataset_key IN ('customs_all', 'customs_progress', 'dapa_contract');
