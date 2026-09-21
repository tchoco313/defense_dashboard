-- =============================================================================
-- 회의 결정 M5 반영 — HS6 선정 규칙에서 R4(B2 FSC 대응) 제외, R3∧R4로만 진입한 6개를 priority 3으로 강등  (작성·적용 2026-09-21)
--
-- 결정: 2026-09-21 팀 회의 M5(app/specs/00_common.md §8). 진입식 R1 OR R2 OR (R3 AND R4) → **R1 OR R2**.
--       09-21 「관세청 데이터를 NSN/FSC 코드와 어떤 수준에서도 엮지 않는다」(CLAUDE.md)와 정합. 분석 대상 19 → 13.
-- 대상 6개(evidence = '전략물자-DU;B2-FSC', 09-18 alter로 evidence_note 에 'R4 잠정' 표기됨):
--       854110 · 854121 · 854129(종전 priority 1) · 852560 · 852692 · 901380(종전 priority 2)
-- 조치: priority = 3 + evidence_note 머리에 '규칙 미해당(2026-09-21 M5: …)' — 09-16 §5-3 강등(847180 등 5개)과 같은 형식.
--       evidence·evidence_basis('rule')는 바꾸지 않는다: 근거 키를 규칙으로 도출한 사실은 그대로이고, 진입식만 바뀌었다.
--       ref_hs_rule_flag·v_hs6_candidate_rule(rule_version 2026-09-16)은 스냅샷이라 불변 — 문서에 「진입식은 09-21 M5로 대체」.
-- 파급: 앱 분석 대상 필터 evidence_basis='rule' → priority IN (1, 2)(app/home.py·pages 1·2·3·5·6), metrics.r4_provisional 삭제,
--       data/reference/hs_whitelist.csv 6행 동기, docs/reference/hs-whitelist-definition.md §8-2·§8-3.
-- 원칙: 멱등(2회째 UPDATE 0행). 표·행 수 불변(24). 화면 ①③ 선택지·홈 KPI 값이 바뀐다(2025 기준: 수입액 합 498.9 → 478.2억$, 1위≥50% 7 → 5, HHI>2,500 7).
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-21_m5_r4_exclude.sql   (admin)
-- 기대: 1회째 UPDATE 6 · meta_column_dict 1, 2회째 전부 0(ALTER COMMENT 는 매회 rows 0). 검증 §3.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 강등 6행
UPDATE ref_hs_whitelist
   SET priority = 3,
       evidence_note = CONCAT('규칙 미해당(2026-09-21 M5): 진입식 R1 OR R2로 확정, R4(B2 FSC 후보 대응) 제외 — R3(전략물자 이중용도) 단독 진입 불가. priority 3으로 강등, 화면 ''분석 제외'' / ',
                              COALESCE(evidence_note, ''))
 WHERE hs6 IN ('854110', '854121', '854129', '852560', '852692', '901380')
   AND (evidence_note IS NULL OR evidence_note NOT LIKE '규칙 미해당(2026-09-21 M5)%');

-- §1-2 스냅샷 표 COMMENT (정의 불변 — db/schema.sql 과 동일 문구)
ALTER TABLE ref_hs_rule_flag COMMENT='HS6별 선정 규칙 R1~R4 판정·근거 수치 스냅샷(84·85·88·90류 전체). 진입식은 2026-09-21 M5로 R1 OR R2 확정(is_candidate_provisional은 09-16 잠정식 참고값)';

-- §2 열 사전 (db/column_dict.csv 와 동일 문구)
UPDATE meta_column_dict
   SET description = '1~3. 1·2 = 분석 대상 13개(진입 R1 OR R2, 2026-09-21 M5) / 3 = 규칙 미해당 11개(09-16 팀판단 5 + 09-21 R4 제외 6, 화면 ''분석 제외'')'
 WHERE table_name = 'ref_hs_whitelist' AND column_name = 'priority'
   AND description <> '1~3. 1·2 = 분석 대상 13개(진입 R1 OR R2, 2026-09-21 M5) / 3 = 규칙 미해당 11개(09-16 팀판단 5 + 09-21 R4 제외 6, 화면 ''분석 제외'')';

-- §3 확인 (주석 — DBHub app_ro)
-- SELECT priority, COUNT(*) FROM ref_hs_whitelist GROUP BY priority;                                   -- 1: 8 · 2: 5 · 3: 11
-- SELECT hs6, priority, evidence_basis FROM ref_hs_whitelist WHERE evidence_note LIKE '규칙 미해당(2026-09-21 M5)%' ORDER BY hs6;   -- 6행, 전부 3·rule
-- SELECT COUNT(*) FROM ref_hs_whitelist WHERE priority IN (1, 2);                                       -- 13
