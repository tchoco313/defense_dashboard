-- =============================================================================
-- 수작업 참조표 시드 (작성 2026-09-15). scripts/load_db.py --ref 가 실행한다(문장 구분은 ";\n").
--   ref_sido_map     : 대표업체주소 첫 토큰 → 시도. 행정표준코드 앞 2자리(강원 51·전북 52 는 특별자치도 전환 후 코드,
--                      구 코드 42·45 는 쓰지 않는다).
--   ref_category_map : ref_hs_whitelist.related_fsc(; 구분)를 풀어 FSC4 → hs6 '후보'로 넣는다.
--                      '확정' 전환은 팀 확인 후 UPDATE (docs/db/schema-design.md §7-2).
-- 재실행 가능: 이미 있으면 건너뛴다(INSERT IGNORE / NOT EXISTS).
-- =============================================================================

INSERT IGNORE INTO ref_sido_map (token, sido_code, sido_name) VALUES
  ('서울','11','서울특별시'), ('서울특별시','11','서울특별시'), ('서울시','11','서울특별시'),
  ('부산','26','부산광역시'), ('부산광역시','26','부산광역시'), ('부산시','26','부산광역시'),
  ('대구','27','대구광역시'), ('대구광역시','27','대구광역시'), ('대구시','27','대구광역시'),
  ('인천','28','인천광역시'), ('인천광역시','28','인천광역시'), ('인천시','28','인천광역시'),
  ('광주','29','광주광역시'), ('광주광역시','29','광주광역시'), ('광주시','29','광주광역시'),
  ('대전','30','대전광역시'), ('대전광역시','30','대전광역시'), ('대전시','30','대전광역시'),
  ('울산','31','울산광역시'), ('울산광역시','31','울산광역시'), ('울산시','31','울산광역시'),
  ('세종','36','세종특별자치시'), ('세종특별자치시','36','세종특별자치시'), ('세종시','36','세종특별자치시'),
  ('경기','41','경기도'), ('경기도','41','경기도'),
  ('강원','51','강원특별자치도'), ('강원도','51','강원특별자치도'), ('강원특별자치도','51','강원특별자치도'),
  ('충북','43','충청북도'), ('충청북도','43','충청북도'),
  ('충남','44','충청남도'), ('충청남도','44','충청남도'),
  ('전북','52','전북특별자치도'), ('전라북도','52','전북특별자치도'), ('전북특별자치도','52','전북특별자치도'),
  ('전남','46','전라남도'), ('전라남도','46','전라남도'),
  ('경북','47','경상북도'), ('경상북도','47','경상북도'),
  ('경남','48','경상남도'), ('경상남도','48','경상남도'),
  ('제주','50','제주특별자치도'), ('제주도','50','제주특별자치도'), ('제주특별자치도','50','제주특별자치도');

INSERT INTO ref_category_map (map_type, source_key, category, hs6, link_status, link_basis, decided_by, decided_at)
SELECT 'fsc4',
       TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(w.related_fsc, ';', n.n), ';', -1)) AS fsc4,
       w.category, w.hs6, '후보',
       'ref_hs_whitelist.related_fsc 후보(docs/reference/hs-whitelist-definition.md). 팀 확인 전 — 확정 시 link_status·decided_by 갱신',
       'load_db.py seed', CURDATE()
FROM ref_hs_whitelist w
JOIN (SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) n
  ON n.n <= 1 + LENGTH(w.related_fsc) - LENGTH(REPLACE(w.related_fsc, ';', ''))
WHERE w.related_fsc IS NOT NULL AND w.related_fsc <> ''
  AND NOT EXISTS (SELECT 1 FROM ref_category_map m
                  WHERE m.map_type = 'fsc4' AND m.hs6 = w.hs6
                    AND m.source_key = TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(w.related_fsc, ';', n.n), ';', -1)));
