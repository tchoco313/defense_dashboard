-- =============================================================================
-- 수작업 참조표 시드 (작성 2026-09-15). scripts/load_db.py --ref 가 실행한다(문장 구분은 ";\n").
--   ref_sido_map     : 대표업체주소 첫 토큰 → 시도. 행정표준코드 앞 2자리(강원 51·전북 52 는 특별자치도 전환 후 코드,
--                      구 코드 42·45 는 쓰지 않는다).
--   ref_category_map : ref_hs_whitelist.related_fsc(; 구분)를 풀어 FSC4 → hs6 '후보'로 넣는다.
--                      '확정' 전환은 팀 확인 후 UPDATE (docs/db/schema-design.md §7-2).
--   ref_fsg          : FSG 2자리 라벨 80행(data/reference/fsg_master.csv, 2026-09-16). 증분 적용본은 db/alter_2026-09-16_fsg.sql.
-- 재실행 가능: 이미 있으면 건너뛴다(INSERT IGNORE / NOT EXISTS).
-- =============================================================================

INSERT IGNORE INTO ref_sido_map (token, sido_code, sido_name) VALUES
  ('서울','11','서울특별시'), ('서울특별시','11','서울특별시'), ('서울시','11','서울특별시'),
  ('부산','26','부산광역시'), ('부산광역시','26','부산광역시'), ('부산시','26','부산광역시'),
  ('대구','27','대구광역시'), ('대구광역시','27','대구광역시'), ('대구시','27','대구광역시'),
  ('인천','28','인천광역시'), ('인천광역시','28','인천광역시'), ('인천시','28','인천광역시'),
  ('광주광역시','29','광주광역시'),  -- '광주'·'광주시'는 경기 광주시와 겹쳐 제외(2026-09-18, db/alter_2026-09-18_sido_gwangju.sql). 정제 코드에서 둘째 토큰으로 판별
  ('대전','30','대전광역시'), ('대전광역시','30','대전광역시'), ('대전시','30','대전광역시'),
  ('충남대전시','30','대전광역시'),  -- 2026-09-18 추가: 계약 주소 16건이 1989년 이전 표기로 적힘(db/alter_2026-09-18_sido_gwangju.sql)
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

-- ref_fsg 시드 (fsg_master.csv 80행과 동일. 재실행 시 덮어씀)
INSERT INTO ref_fsg (fsg_code, name_en, name_ko, status, is_historical, is_electronic_group, note_ko, source_url) VALUES
  ('10', 'Weapons', '무기', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('11', 'Nuclear Ordnance', '핵 병기', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('12', 'Fire Control Equipment', '사격통제 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('13', 'Ammunition and Explosives', '탄약 및 폭발물', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('14', 'Guided Missiles', '유도 미사일', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('15', 'Aerospace Craft and Structural Components', '항공우주 비행체 및 구조 구성품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('16', 'Aerospace Craft Components and Accessories', '항공우주 비행체 구성품 및 부속품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('17', 'Aerospace Craft Launching, Landing, Ground Handling, and Servicing Equipment', '항공우주 비행체 발사·착륙·지상취급 및 정비 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('18', 'Space Vehicles', '우주 비행체', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('19', 'Ships, Small Craft, Pontoons, and Floating Docks', '선박·소형정·부교 및 부유식 도크', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('20', 'Ship and Marine Equipment', '선박 및 해양 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('21', 'Historical FSG', '과거 FSG', 'A', 1, 0, '파일 유지 목적의 Historical FSG. 신규 품목 추가 불가.', 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('22', 'Railway Equipment', '철도 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('23', 'Ground Effect Vehicles, Motor Vehicles, Trailers, and Cycles', '지면효과차량·자동차·트레일러 및 이륜차', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('24', 'Tractors', '트랙터', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('25', 'Vehicular Equipment Components', '차량 장비 구성품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('26', 'Tires and Tubes', '타이어 및 튜브', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('28', 'Engines, Turbines, and Components', '엔진·터빈 및 구성품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('29', 'Engine Accessories', '엔진 부속품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('30', 'Mechanical Power Transmission Equipment', '기계식 동력전달 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('31', 'Bearings', '베어링', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('32', 'Woodworking Machinery and Equipment', '목공 기계 및 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('33', 'Historical FSG', '과거 FSG', 'A', 1, 0, '파일 유지 목적의 Historical FSG. 신규 품목 추가 불가.', 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('34', 'Metalworking Machinery', '금속가공 기계', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('35', 'Service and Trade Equipment', '서비스 및 상업용 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('36', 'Special Industry Machinery', '특수 산업용 기계', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('37', 'Agricultural Machinery and Equipment', '농업 기계 및 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('38', 'Construction, Mining, Excavating, and Highway Maintenance Equipment', '건설·광업·굴착 및 도로 유지보수 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('39', 'Materials Handling Equipment', '자재 취급 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('40', 'Rope, Cable, Chain, and Fittings', '로프·케이블·체인 및 부속품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('41', 'Refrigeration, Air Conditioning, and Air Circulating Equipment', '냉동·공조 및 공기순환 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('42', 'Firefighting, Rescue, and Safety Equipment; and Environmental Protection Equipment and Materials', '소방·구조·안전 장비 및 환경보호 장비·자재', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('43', 'Pumps and Compressors', '펌프 및 압축기', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('44', 'Furnace, Steam Plant, and Drying Equipment; and Nuclear Reactors', '노·증기설비·건조 장비 및 원자로', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('45', 'Plumbing, Heating, and Waste Disposal Equipment', '배관·난방 및 폐기물 처리 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('46', 'Water Purification and Sewage Treatment Equipment', '정수 및 하수처리 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('47', 'Pipe, Tubing, Hose, and Fittings', '파이프·튜브·호스 및 부속품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('48', 'Valves', '밸브', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('49', 'Maintenance and Repair Shop Equipment', '정비 및 수리 작업장 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('51', 'Hand Tools', '수공구', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('52', 'Measuring Tools', '측정 공구', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('53', 'Hardware and Abrasives', '철물 및 연마재', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('54', 'Prefabricated Structures and Scaffolding', '조립식 구조물 및 비계', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('55', 'Lumber, Millwork, Plywood, and Veneer', '목재·목공제품·합판 및 단판', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('56', 'Construction and Building Materials', '건설 및 건축 자재', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('58', 'Communication, Detection, and Coherent Radiation Equipment', '통신·탐지 및 코히런트 방사 장비', 'A', 0, 1, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('59', 'Electrical and Electronic Equipment Components', '전기 및 전자 장비 구성품', 'A', 0, 1, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('60', 'Fiber Optics Materials, Components, Assemblies, and Accessories', '광섬유 재료·구성품·조립품 및 부속품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('61', 'Electric Wire, and Power and Distribution Equipment', '전선 및 전력·배전 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('62', 'Lighting Fixtures and Lamps', '조명기구 및 램프', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('63', 'Alarm, Signal and Security Detection Systems', '경보·신호 및 보안탐지 시스템', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('65', 'Medical, Dental, and Veterinary Equipment and Supplies', '의료·치과·수의 장비 및 용품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('66', 'Instruments and Laboratory Equipment', '계측기 및 실험실 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('67', 'Photographic Equipment', '사진 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('68', 'Chemicals and Chemical Products', '화학물질 및 화학제품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('69', 'Training Aids and Devices', '훈련 보조기구 및 장치', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('70', 'Information Technology Equipment (Including Firmware), Software, Supplies and Support Equipment', '정보기술 장비(펌웨어 포함)·소프트웨어·용품 및 지원 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('71', 'Furniture', '가구', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('72', 'Household and Commercial Furnishings and Appliances', '가정용·상업용 비품 및 가전제품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('73', 'Food Preparation and Serving Equipment', '식품 조리 및 제공 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('74', 'Office Machines, Text Processing Systems and Visible Record Equipment', '사무기기·문서처리 시스템 및 가시기록 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('75', 'Office Supplies and Devices', '사무용품 및 기기', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('76', 'Books, Maps, and Other Publications', '도서·지도 및 기타 간행물', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('77', 'Musical Instruments, Phonographs, and Home-Type Radios', '악기·축음기 및 가정용 라디오', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('78', 'Recreational and Athletic Equipment', '레크리에이션 및 체육 장비', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('79', 'Cleaning Equipment and Supplies', '청소 장비 및 용품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('80', 'Brushes, Paints, Sealers, and Adhesives', '브러시·도료·실러 및 접착제', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('81', 'Containers, Packaging, and Packing Supplies', '용기·포장 및 포장용품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('83', 'Textiles, Leather, Furs, Apparel and Shoe Findings, Tents and Flags', '직물·가죽·모피·의류 및 신발 부자재·텐트·깃발', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('84', 'Clothing, Individual Equipment, Insignia, and Jewelry', '의류·개인 장비·표장 및 장신구', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('85', 'Toiletries', '세면·위생용품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('87', 'Agricultural Supplies', '농업용품', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('88', 'Live Animals', '생축', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('89', 'Subsistence', '식량', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('91', 'Fuels, Lubricants, Oils, Waxes, and Electricity', '연료·윤활제·오일·왁스 및 전력', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('93', 'Nonmetallic Fabricated Materials', '비금속 가공재', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('94', 'Nonmetallic Crude Materials', '비금속 원재료', 'A', 0, 0, NULL, 'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt'),
  ('95', 'Metal Bars, Sheets, and Shapes', '금속 봉·판·형재', 'A', 0, 0, '원 파일(77행)에 없어 2026-09-16 보완. GSA PSC Manual 2025-04(product group, 1979-10-01 시작)로 확인, DLA ZSMT_FSG.txt는 국내에서 403(Akamai)이라 원문 미대조', 'https://www.acquisition.gov/sites/default/files/manual/PSC%20April%202025.xlsx'),
  ('96', 'Ores, Minerals, and Their Primary Products', '광석·광물 및 그 1차 제품', 'A', 0, 0, '원 파일(77행)에 없어 2026-09-16 보완. GSA PSC Manual 2025-04(product group, 1979-10-01 시작)로 확인, DLA ZSMT_FSG.txt는 국내에서 403(Akamai)이라 원문 미대조', 'https://www.acquisition.gov/sites/default/files/manual/PSC%20April%202025.xlsx'),
  ('99', 'Miscellaneous', '기타', 'A', 0, 0, '원 파일(77행)에 없어 2026-09-16 보완. GSA PSC Manual 2025-04(product group, 1979-10-01 시작)로 확인, DLA ZSMT_FSG.txt는 국내에서 403(Akamai)이라 원문 미대조', 'https://www.acquisition.gov/sites/default/files/manual/PSC%20April%202025.xlsx')
ON DUPLICATE KEY UPDATE name_en = VALUES(name_en), name_ko = VALUES(name_ko), status = VALUES(status),
  is_historical = VALUES(is_historical), is_electronic_group = VALUES(is_electronic_group),
  note_ko = VALUES(note_ko), source_url = VALUES(source_url);
