-- =============================================================================
-- 품목군 대응표 확정 · b2_scope 설정 (초안 작성 2026-09-17 — **팀 결정 후 실행**, 미적용)
--
-- 근거: docs/report/category-map-decision-2026-09-17.md §2·§3 권장안. 결정이 권장안과 다르면 아래 map_id 목록을 고친다.
-- 효과: v_review_list 의 b2_status / b2_completed_part_count / b2_project_part_count 가 채워진다
--       (대응표 link_status='확정' AND clean_dapa_localized_item.category_link_status='확정' 인 행만 집계).
-- 실행: docs/runbook/commands.md 증분 변경 방식(mariadb.exe, 계정 .env MARIADB_USER). DBHub 는 readonly 라 불가.
--       실행 전 decided_by · decided_at 을 회의 날짜로 바꾼다.
-- 재실행: 가능(UPDATE 는 멱등, INSERT 는 NOT EXISTS 가드).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

SET @decided_by = '팀 회의(권장안, 초안)';   -- 회의 후 수정
SET @decided_at = '2026-09-17';              -- 회의 후 수정

-- §1 확정 14행 (map_id 는 팀 서버 2026-09-17 실측: schema seed 순서)
UPDATE ref_category_map
   SET link_status = '확정', decided_by = @decided_by, decided_at = @decided_at,
       link_basis  = CONCAT('확정(FSC 수준, category-map-decision-2026-09-17 §2). ', COALESCE(link_basis, ''))
 WHERE map_type = 'fsc4' AND map_id IN (
   5, 4, 3,          -- 5962 → 854231 · 854233 · 854239 (집적회로 27부품, HS6 세분 불가·합산 금지)
   9, 8, 7, 6,       -- 5961 → 854110 · 854121 · 854129 · 854159 (다이오드 6 · 트랜지스터 7 · LED 1 · 조립체 1)
   14,               -- 5820 → 852560 (무전기·송수신기 + 부속 19)
   16,               -- 5895 → 852990 (통신장비 부분품 41)
   10,               -- 5985 → 852990 (안테나 부속 12)
   13,               -- 5840 → 852610 (레이더 부속 4)
   12,               -- 5825 → 852691 (위성항법 세트 1)
   2, 15             -- 5855 · 5860 → 901380 (야시·조준경·레이저 18)
 );

-- §2 대응불가 3행 (삭제하지 않고 사유 기록)
UPDATE ref_category_map
   SET link_status = '대응불가', decided_by = @decided_by, decided_at = @decided_at,
       link_basis  = CASE map_id
         WHEN 17 THEN '대응불가: 5895 품명이 덮개·하우징·증폭기·모뎀 등 부분품이라 완제품 HS 852560 이 아니라 852990 으로 대응(category-map-decision-2026-09-17 §2)'
         WHEN 11 THEN '대응불가: 5895 에 무선원격조종 송신기 품명 없음(제어장치,원격스위치용 1건은 스위치 제어기)'
         WHEN 1  THEN '대응불가: 5825 유일 품목 "항법세트,위성신호용"은 852691(무선항행) 에 해당. 901480 에 두면 같은 부품 2회 표시'
       END
 WHERE map_type = 'fsc4' AND map_id IN (17, 11, 1);

-- §3 신규 1행: 5985 → 852910 안테나 (2026-09-16 화이트리스트 추가분, related_fsc 미기재)
INSERT INTO ref_category_map (map_type, source_key, category, hs6, link_status, link_basis, decided_by, decided_at)
SELECT 'fsc4', '5985', '전자부품', '852910', '확정',
       '확정: B2 5985 품명 "안테나"(4)·"안테나 세트"(1) 가 HS 852910 안테나·반사기에 직접 해당. hs_whitelist.csv related_fsc 에 5985 추가 예정(category-map-decision-2026-09-17 §2)',
       @decided_by, @decided_at
 WHERE NOT EXISTS (SELECT 1 FROM ref_category_map WHERE map_type = 'fsc4' AND source_key = '5985' AND hs6 = '852910');

-- §4 clean_ 쪽도 '확정' 이어야 뷰가 센다. 확정된 FSC 의 후보 행만 올린다(대응불가 FSC 는 없음 — 5895·5825 는 다른 HS6 로 확정됨).
UPDATE clean_dapa_localized_item c
   SET c.category_link_status = '확정'
 WHERE c.category_link_status = '후보'
   AND EXISTS (SELECT 1 FROM ref_category_map m
                WHERE m.map_type = 'fsc4' AND m.source_key = c.fsc4 AND m.link_status = '확정');

-- §5 b2_scope
UPDATE ref_hs_whitelist SET b2_scope = 'B2 범위 밖' WHERE hs6 IN ('841191', '880730', '901420', '848620');
UPDATE ref_hs_whitelist SET b2_scope = '대응 가능'  WHERE b2_scope IS NULL AND category IN ('반도체', '전자부품');

-- §6 검증
SELECT link_status, COUNT(*) AS n FROM ref_category_map GROUP BY link_status;                 -- 확정 15 · 대응불가 3
SELECT category_link_status, COUNT(*) AS n, COUNT(DISTINCT part_mgmt_no) AS parts
  FROM clean_dapa_localized_item GROUP BY category_link_status;                                -- 확정 400 / 137
SELECT b2_scope, COUNT(*) AS n FROM ref_hs_whitelist GROUP BY b2_scope;                       -- 대응 가능 20 · B2 범위 밖 4
SELECT hs6, name_ko, b2_status, b2_completed_part_count, b2_project_part_count
  FROM v_review_list WHERE year = 2025 ORDER BY hs6;                                           -- 결정 문서 §2 예상표와 대조
