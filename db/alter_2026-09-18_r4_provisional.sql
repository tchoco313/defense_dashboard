-- =============================================================================
-- 품목군 대응표 "확정하지 않음" 결정 반영 (작성 2026-09-18)
--
-- 결정: HS6↔FSC4 대응표(ref_category_map)는 확정하지 않는다 — FSC↔HS 공식 연계표 없음(미 DLA·WCO·UN),
--       국방기술진흥연구소 2025 「군급분류-HS코드 간 매칭 모델 연구」 결과 비공개. docs/report/category-map-decision-2026-09-17.md 머리 절.
-- 조치 1: R3∧R4로만 화이트리스트에 진입한 HS6 6개의 evidence_note 에 "R4 잠정" 사유를 덧붙인다(evidence·evidence_basis 는 바꾸지 않는다 —
--         ref_hs_rule_flag 스냅샷·문서 수치와 어긋나지 않게).
-- 조치 2: v_review_list.b2_status 라벨 '대응 미확정' → '대응표 없음'(설계 결정). 정의는 db/schema.sql §6 과 동일.
-- 표·행 수·데이터 불변. 재실행 가능(UPDATE 는 NOT LIKE 가드, 뷰는 CREATE OR REPLACE).
-- 실행: docs/runbook/commands.md 증분 변경 방식(mariadb.exe, 계정 defense).
-- 검증: 아래 SELECT 3문 — evidence_note 잠정 6행 / b2_status '대응표 없음' 24행·'대응 미확정' 0행 / ref_category_map 후보 17행.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 R4 잠정 표기 (6행)
UPDATE ref_hs_whitelist
   SET evidence_note = CONCAT_WS(' | ', NULLIF(evidence_note, ''), 'R4 잠정 — FSC↔HS 공식 연계표 없음, 후보 대응 의존(2026-09-18)')
 WHERE hs6 IN ('852560', '852692', '854110', '854121', '854129', '901380')
   AND (evidence_note IS NULL OR evidence_note NOT LIKE '%R4 잠정%');

-- §2 v_review_list 라벨 (db/schema.sql §6 사본)
CREATE OR REPLACE VIEW v_review_list AS
SELECT w.hs6, w.category, w.name_ko, w.priority, w.axis,
       h.year, h.imp_dlr_total, h.top1_stat_cd, h.top1_share, h.hhi, h.country_count, h.is_partial_year,
       -- B1: KRIT 공고 과제(확정 연결·집계용 1건)
       CASE WHEN NOT EXISTS (SELECT 1 FROM clean_krit_task) THEN '미적재' ELSE '집계' END AS b1_status,
       CASE WHEN NOT EXISTS (SELECT 1 FROM clean_krit_task) THEN NULL
            ELSE (SELECT COUNT(*) FROM clean_krit_task k
                   WHERE k.hs6 = w.hs6 AND k.category_link_status = '확정' AND k.is_counted = 1) END AS b1_target_count,
       (SELECT MAX(k.round_year) FROM clean_krit_task k
         WHERE k.hs6 = w.hs6 AND k.category_link_status = '확정' AND k.is_counted = 1)    AS b1_latest_round_year,
       -- B2: 국산화개발품목(지상체계 한정, 시점 미상)
       CASE WHEN w.b2_scope = 'B2 범위 밖' THEN 'B2 범위 밖'
            WHEN NOT EXISTS (SELECT 1 FROM clean_dapa_localized_item) THEN '미적재'
            WHEN NOT EXISTS (SELECT 1 FROM ref_category_map m
                              WHERE m.map_type = 'fsc4' AND m.hs6 = w.hs6 AND m.link_status = '확정') THEN '대응표 없음'
            ELSE '집계' END                                                               AS b2_status,
       CASE WHEN w.b2_scope = 'B2 범위 밖'
              OR NOT EXISTS (SELECT 1 FROM clean_dapa_localized_item)
              OR NOT EXISTS (SELECT 1 FROM ref_category_map m
                              WHERE m.map_type = 'fsc4' AND m.hs6 = w.hs6 AND m.link_status = '확정') THEN NULL
            ELSE (SELECT COUNT(DISTINCT li.part_mgmt_no) FROM clean_dapa_localized_item li
                   JOIN ref_category_map m ON m.map_type = 'fsc4' AND m.source_key = li.fsc4
                                          AND m.hs6 = w.hs6 AND m.link_status = '확정'
                   WHERE li.category_link_status = '확정') END                            AS b2_completed_part_count,
       CASE WHEN w.b2_scope = 'B2 범위 밖'
              OR NOT EXISTS (SELECT 1 FROM clean_dapa_localized_item)
              OR NOT EXISTS (SELECT 1 FROM ref_category_map m
                              WHERE m.map_type = 'fsc4' AND m.hs6 = w.hs6 AND m.link_status = '확정') THEN NULL
            ELSE (SELECT COUNT(*) FROM clean_dapa_localized_item li
                   JOIN ref_category_map m ON m.map_type = 'fsc4' AND m.source_key = li.fsc4
                                          AND m.hs6 = w.hs6 AND m.link_status = '확정'
                   WHERE li.category_link_status = '확정') END                            AS b2_project_part_count
FROM ref_hs_whitelist w
JOIN v_hhi_hs6_year h ON h.hs6 = w.hs6;

-- §3 검증
SELECT hs6, evidence_note FROM ref_hs_whitelist WHERE evidence_note LIKE '%R4 잠정%' ORDER BY hs6;
SELECT b2_status, COUNT(*) AS n FROM v_review_list WHERE year = 2025 GROUP BY b2_status;
SELECT link_status, COUNT(*) AS n FROM ref_category_map GROUP BY link_status;
