-- =============================================================================
-- 카테고리 맵(HS6↔FSC4 대응) 폐기 — ref_category_map DROP · v_defense_relevance_b2 DROP · v_review_list B2 열 제거 ·
-- v_hs6_candidate_rule R4 항 제거 · ref_hs_whitelist.related_fsc DROP · ref_hs_indicator defense_relevance 28행 삭제 · 열 사전 11행 삭제
-- (작성·적용 2026-09-21)
--
-- 결정: 2026-09-21 사용자 — "카테고리맵은 아예 안 하는 걸로, 이유는 수출입 현황이니까" + 실제 DROP 승인. 경과는 CLAUDE.md 핵심 제약·
--       app/specs/00_common.md §6·§8 M5. 관세청 HS 데이터를 NSN/FSC 코드와 어떤 수준에서도 엮지 않는다.
-- 의존: RDS information_schema 실측(09-21) — ref_category_map·v_defense_relevance_b2 를 참조하는 뷰는 v_review_list·v_hs6_candidate_rule 둘뿐.
--       ref_hs_rule_flag(09-16 스냅샷 표)의 r4_b2·b2_part_count 열은 이력이라 남긴다.
-- 조치 순서: ① v_review_list 재정의(B2 열 3개 제거, B1 열은 clean_krit_task만 보므로 유지) ② v_hs6_candidate_rule 재정의(v_defense_relevance_b2 JOIN 제거,
--       b2_part_count NULL·r4_b2 0 상수, 진입식 R1 OR R2, priority_rule 1/2/3=R3만(진입 아님)) ③ DROP VIEW v_defense_relevance_b2
--       ④ DELETE ref_hs_indicator axis='defense_relevance'(28행, 원천 뷰가 사라짐) ⑤ DROP TABLE ref_category_map(17행 후보, FK 자식 없음)
--       ⑥ ALTER ref_hs_whitelist DROP COLUMN related_fsc ⑦ meta_column_dict 11행 삭제(ref_category_map 10 + related_fsc 1) + ref_hs_whitelist ordinal 12~17 → 11~16(1회만, @mx 가드)
-- 정본 동기: db/schema.sql(CREATE 2개 삭제·뷰 2개·DROP 목록·related_fsc 열), db/seed_ref.sql(ref_category_map INSERT 블록 삭제),
--       db/reset_data.sql 주석, data/reference/hs_whitelist.csv related_fsc 열 삭제, db/table_dict.csv 2행·column_dict.csv 11행, scripts/load_db.py 시드 출력·verify 목록.
-- 남기는 것(별도 결정): ref_hs_whitelist.b2_scope(NULL 전부), clean_dapa_contract·clean_dapa_localized_item·clean_krit_task 의 category·category_link_status 열
--       (노트북 산출 열 — 사용자 영역), v_review_list B1 열.
-- 되돌리기: 이 파일로는 불가(표 DROP). 재생성은 git 이력의 schema.sql(2026-09-21 이전)·seed_ref.sql.
-- 주의: apply_alter.py 가 ';' 로 문장을 나누므로 evidence_rule 구분자는 CHAR(59)(= ';')로 쓴다(schema.sql 정본은 ';' 리터럴, 결과 동일).
-- 멱등: 2회째 실행 시 DROP … IF EXISTS 는 Note, UPDATE/DELETE 0행, ALTER DROP COLUMN 은 information_schema 조건(2회째 SELECT 1).
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-21_drop_category_map.sql   (admin)
-- 기대: 1회째 DELETE 28 · DROP TABLE · ALTER · meta_column_dict 11. 2회째 전부 0/Note. 검증 §8.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 v_review_list — 화이트리스트 × 연도별 HHI + B1(KRIT 과제, clean_krit_task.hs6 기준 — 대응표 없이 전부 0)
CREATE OR REPLACE VIEW v_review_list AS
SELECT w.hs6, w.category, w.name_ko, w.priority, w.axis,
       h.year, h.imp_dlr_total, h.top1_stat_cd, h.top1_share, h.hhi, h.country_count, h.is_partial_year,
       CASE WHEN NOT EXISTS (SELECT 1 FROM clean_krit_task) THEN '미적재' ELSE '집계' END AS b1_status,
       CASE WHEN NOT EXISTS (SELECT 1 FROM clean_krit_task) THEN NULL
            ELSE (SELECT COUNT(*) FROM clean_krit_task k
                   WHERE k.hs6 = w.hs6 AND k.category_link_status = '확정' AND k.is_counted = 1) END AS b1_target_count,
       (SELECT MAX(k.round_year) FROM clean_krit_task k
         WHERE k.hs6 = w.hs6 AND k.category_link_status = '확정' AND k.is_counted = 1)    AS b1_latest_round_year
FROM ref_hs_whitelist w
JOIN v_hhi_hs6_year h ON h.hs6 = w.hs6;

-- §2 v_hs6_candidate_rule — R4(B2 FSC 대응) 항 제거. 열 목록은 유지(b2_part_count NULL, r4_b2 0)해 v_hs6_candidate_vs_whitelist 가 그대로 읽는다.
--    진입 = R1 OR R2(2026-09-21 M5). priority_rule: R1→1, R2→2, R3만→3(진입 아님), 없음 NULL.
CREATE OR REPLACE VIEW v_hs6_candidate_rule AS
SELECT x.hs6, LEFT(x.hs6, 2) AS hs2,
       n6.name_ko                                                        AS hs6_name_ko,
       x.hs10_total, x.hs10_master, x.mil_cnt, x.aero_cnt, x.uav_cnt, x.radar_cnt, x.nav_cnt,
       COALESCE(k.control_hsk10_count, 0)                                AS control_hsk10_count,
       COALESCE(k.ml_hsk10_count, 0)                                     AS ml_hsk10_count,
       COALESCE(k.du_elec_hsk10_count, 0)                                AS du_elec_hsk10_count,
       ROUND(100 * COALESCE(k.control_hsk10_count, 0) / NULLIF(x.hs10_master, 0), 1) AS control_ratio_pct,
       k.control_no_list,
       CAST(NULL AS SIGNED)                                              AS b2_part_count,
       (x.mil_cnt > 0)                                                   AS r1_mil,
       (x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
        OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기')       AS r2_aero_nav,
       (COALESCE(k.ml_hsk10_count, 0) + COALESCE(k.du_elec_hsk10_count, 0) > 0) AS r3_control,
       0                                                                 AS r4_b2,
       (x.mil_cnt > 0
        OR x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
        OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기')       AS is_candidate,
       CASE WHEN x.mil_cnt > 0 OR COALESCE(k.ml_hsk10_count, 0) > 0                                         THEN 1
            WHEN x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0
                 OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기'             THEN 2
            WHEN COALESCE(k.du_elec_hsk10_count, 0) > 0                                                     THEN 3
            ELSE NULL END                                                  AS priority_rule,
       NULLIF(CONCAT_WS(CHAR(59),
         IF(x.mil_cnt > 0, 'HSK-군용', NULL),
         IF(x.aero_cnt + x.uav_cnt + x.radar_cnt + x.nav_cnt > 0 OR COALESCE(n6.name_ko, '') REGEXP '레이더|항행|항공기용|항공용|우주항행|무인기', 'HSK-항공/항행', NULL),
         IF(COALESCE(k.ml_hsk10_count, 0) > 0, '전략물자-ML', NULL),
         IF(COALESCE(k.du_elec_hsk10_count, 0) > 0, '전략물자-DU', NULL)), '')        AS evidence_rule,
       CONCAT_WS(' / ',
         CONCAT('HSK10 ', x.hs10_total, '개(현행 ', x.hs10_master, ') 중 군용전용 ', x.mil_cnt, '·항공 ', x.aero_cnt, '·무인기 ', x.uav_cnt, '·레이더 ', x.radar_cnt, '·항행 ', x.nav_cnt),
         CONCAT('이중용도 통제 HSK ', COALESCE(k.control_hsk10_count, 0), '개(현행 대비 ', COALESCE(ROUND(100 * k.control_hsk10_count / NULLIF(x.hs10_master, 0)), 0), '%, 3·5·6·7부 ', COALESCE(k.du_elec_hsk10_count, 0), ')')) AS evidence_note
FROM (SELECT hs6,
             COUNT(*)                                     AS hs10_total,
             SUM(src = 'master_2026')                     AS hs10_master,
             SUM(use_tag = '군용전용')                     AS mil_cnt,
             SUM(use_tag = '항공기용')                     AS aero_cnt,
             SUM(use_tag = '무인기')                       AS uav_cnt,
             SUM(use_tag = '레이더')                       AS radar_cnt,
             SUM(use_tag = '항행')                         AS nav_cnt
      FROM v_hs10_use_tag_all GROUP BY hs6
      UNION
      SELECT k2.hs6, 0, 0, 0, 0, 0, 0, 0
      FROM v_hsk_control_by_hs6 k2
      WHERE NOT EXISTS (SELECT 1 FROM v_hs10_use_tag_all t2 WHERE t2.hs6 = k2.hs6)) x
LEFT JOIN v_hsk_control_by_hs6   k  ON k.hs6 = x.hs6
LEFT JOIN raw_hs_unit_name       n6 ON n6.hs_code = x.hs6 AND n6.hs_unit = '06'
WHERE LEFT(x.hs6, 2) IN ('84', '85', '88', '90');

-- §3 뷰 삭제
DROP VIEW IF EXISTS v_defense_relevance_b2;

-- §4 지표 스냅샷 — 원천 뷰가 사라진 축 삭제(28행)
DELETE FROM ref_hs_indicator WHERE axis = 'defense_relevance';

-- §5 대응표 삭제(17행 후보)
DROP TABLE IF EXISTS ref_category_map;

-- §6 화이트리스트의 후보 FSC 열 삭제 (MySQL 은 DROP COLUMN IF EXISTS 가 없어 information_schema 로 조건 실행 — 09-16 hs_rule alter §1 방식)
SET @has_col := (SELECT COUNT(*) FROM information_schema.columns
                  WHERE table_schema = 'defense_dashboard' AND table_name = 'ref_hs_whitelist' AND column_name = 'related_fsc');
SET @ddl := IF(@has_col > 0, 'ALTER TABLE ref_hs_whitelist DROP COLUMN related_fsc', 'SELECT 1');
PREPARE s FROM @ddl;
EXECUTE s;
DEALLOCATE PREPARE s;

-- §7 열 사전
DELETE FROM meta_column_dict WHERE table_name = 'ref_category_map';
DELETE FROM meta_column_dict WHERE table_name = 'ref_hs_whitelist' AND column_name = 'related_fsc';
SET @mx := (SELECT MAX(ordinal) FROM meta_column_dict WHERE table_name = 'ref_hs_whitelist');
UPDATE meta_column_dict SET ordinal = ordinal - 1 WHERE table_name = 'ref_hs_whitelist' AND ordinal > 11 AND @mx = 17 ORDER BY ordinal ASC;

-- §8 확인 (주석 — DBHub app_ro)
-- SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='defense_dashboard' AND table_name='ref_category_map';   -- 0
-- SELECT COUNT(*) FROM information_schema.views  WHERE table_schema='defense_dashboard' AND table_name='v_defense_relevance_b2';   -- 0
-- SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='defense_dashboard' AND table_name='ref_hs_whitelist' AND column_name='related_fsc';   -- 0
-- SELECT axis, COUNT(*) FROM ref_hs_indicator GROUP BY axis;                       -- civil_mix 61 만
-- SELECT COUNT(*) FROM v_review_list; SELECT COUNT(*) FROM v_hs6_candidate_rule WHERE is_candidate = 1;   -- 246 / R1 OR R2 후보 수
-- SELECT COUNT(*) FROM meta_column_dict;                                           -- 862 → 851
