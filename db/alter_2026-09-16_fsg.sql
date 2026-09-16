-- =============================================================================
-- FSG(Federal Supply Group, 군급 2자리) 참조표 ref_fsg 신설 + B2 FSG 집계 뷰 (작성 2026-09-16, 팀 서버 적용 2026-09-16 완료(3회 실행, 멱등))
--
-- 근거: 팀원 공유 new_data/DLA_FSG_공식분류표.csv(77행) → data/reference/fsg_master.csv(80행). 계획 2026-09-16 "국내 부분 데이터 판정"
-- 목적: FSC 4자리 라벨(ref_fsc)은 출처가 없어 0행이었다. FSG 2자리 라벨을 두어 핵심 ② 국산화 완료 섹션의
--       "사업 × FSC군 히트맵"·"FSC별 막대"에 국문 군급명을 붙인다. 계약정보·조달계획·입찰 CSV에는 FSC가 없으므로 이 표와 엮이지 않는다.
-- 95·96·99: 원 파일에 없으나 B2·국방표준종합·사전의향서 데이터에 등장 → GSA PSC Manual 2025-04(product group)로 확인해 보완.
--       DLA 원문(ZSMT_FSG.txt)은 국내에서 403(Akamai)이라 미대조 — note_ko·docs/data-sources.md에 기록.
-- 실행: DBHub는 readonly라 불가. docs/runbook/commands.md 방식:
--       mariadb.exe -h <서버IP> -u <계정> --protocol=TCP --skip-ssl-verify-server-cert --default-character-set=utf8mb4 --show-warnings --table defense_dashboard < db/alter_2026-09-16_fsg.sql
-- 재실행: 가능. CREATE TABLE IF NOT EXISTS, 시드는 ON DUPLICATE KEY UPDATE, 뷰는 OR REPLACE, 열 사전은 ON DUPLICATE KEY.
-- 순서: §1 ref_fsg → §2 시드 80행 → §3 v_b2_fsg_summary → §4 meta_column_dict · 4-2 meta_dataset → §5 검증
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4;

-- §1 ref_fsg (정의는 db/schema.sql과 동일하게 유지)
CREATE TABLE IF NOT EXISTS ref_fsg (
  fsg_code             CHAR(2)      NOT NULL COMMENT 'FSG 2자리 = FSC 앞 2자리',
  name_en              VARCHAR(200) NOT NULL,
  name_ko              VARCHAR(100) NOT NULL COMMENT '팀원 번역(원 파일 fsg_name_ko)',
  status               CHAR(1)      NOT NULL DEFAULT 'A' COMMENT '원 파일 status(전부 A)',
  is_historical        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '21·33 = 파일 유지 목적 Historical FSG(신규 품목 추가 불가)',
  is_electronic_group  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '58·59 = 1 (ref_fsc.is_electronic_group과 같은 기준, 핵심 ② 기본 필터)',
  note_ko              VARCHAR(300) NULL,
  source_url           VARCHAR(300) NULL COMMENT '원 파일: DLA ZSMT_FSG.txt / 보완 3행: GSA PSC Manual 2025-04 xlsx',
  PRIMARY KEY (fsg_code)
) ENGINE=InnoDB COMMENT='FSG 군급 2자리 라벨 80행 (data/reference/fsg_master.csv). 4자리 라벨 ref_fsc는 출처 없음';

-- §2 시드 (data/reference/fsg_master.csv 80행과 동일. 재실행 시 덮어씀)
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

-- §3 B2 국산화개발품목 × FSG 집계 (핵심 ② ⓐ·ⓑ 라벨용). raw 기준(clean_ 미적재).
--    행 수 = 사업×부품 행(완전 중복 8,940 포함), 고유 부품 수 = 부품관리번호 DISTINCT. fsg_code가 ref_fsg에 없으면(공란 등) name_ko NULL.
CREATE OR REPLACE VIEW v_b2_fsg_summary AS
SELECT LEFT(b.fsc, 2)                     AS fsg_code,
       f.name_ko                           AS fsg_name_ko,
       f.name_en                           AS fsg_name_en,
       COALESCE(f.is_electronic_group, 0)  AS is_electronic_group,
       COUNT(b.row_id)                     AS b2_row_count,
       COUNT(DISTINCT b.part_mgmt_no)      AS b2_part_count,
       COUNT(DISTINCT b.project_name)      AS b2_project_count,
       COUNT(DISTINCT b.fsc)               AS fsc4_count
FROM raw_dapa_localized_item b
LEFT JOIN ref_fsg f ON f.fsg_code = LEFT(b.fsc, 2)
GROUP BY LEFT(b.fsc, 2), f.name_ko, f.name_en, f.is_electronic_group;

-- §4 열 사전
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
  ('ref_fsg', 1, 'fsg_code', 'fsg_code', 'CHAR(2)', 'FSG 2자리 = FSC 앞 2자리'),
  ('ref_fsg', 2, 'name_en', 'fsg_name_en', 'VARCHAR(200)', '영문 군급명(DLA)'),
  ('ref_fsg', 3, 'name_ko', 'fsg_name_ko', 'VARCHAR(100)', '국문 군급명(팀원 번역)'),
  ('ref_fsg', 4, 'status', 'status', 'CHAR(1)', '원 파일 status(전부 A)'),
  ('ref_fsg', 5, 'is_historical', 'is_historical', 'TINYINT(1)', '21·33 Historical FSG'),
  ('ref_fsg', 6, 'is_electronic_group', '(파생)', 'TINYINT(1)', '58·59 = 1. 핵심 ② 기본 필터'),
  ('ref_fsg', 7, 'note_ko', 'note_ko', 'VARCHAR(300)', '보완 3행(95·96·99) 출처·미대조 사유'),
  ('ref_fsg', 8, 'source_url', 'source_url', 'VARCHAR(300)', 'DLA ZSMT_FSG.txt / GSA PSC Manual 2025-04')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §4-2 확보 기록 (db/meta_dataset.csv fsg_master 행과 동일. --ref는 비어 있지 않은 meta_dataset을 건너뛰므로 여기서 넣는다)
INSERT INTO meta_dataset (dataset_key, tier, provider, dataset_id, title, url, access_method, acquired_on, period_start, period_end, is_partial_period,
  published_on, updated_on, query_condition, raw_path, file_bytes, sha256, encoding, parser, raw_row_count, portal_row_count, target_table, note) VALUES
  ('fsg_master', '참조', 'DLA(미국 국방병참국) / 팀원 정리', NULL, 'DLA FSG(Federal Supply Group) 공식분류표 (군급 2자리)',
   'https://www.dla.mil/Portals/104/Documents/InformationOperations/LogisticsInformationServices/CatalogTools%20Tables/New/ZSMT_FSG.txt',
   '팀원 공유(new_data/) + 수작업 보완', '2026-09-16', NULL, NULL, 0, NULL, NULL, NULL, 'data/reference/fsg_master.csv', 17457,
   '806340417b4a69917cf87f5b840b99925132caeda68977cf885b8972754949e1', 'utf-8', 'Python csv (scripts/load_db.py --ref: db/seed_ref.sql)', 80, NULL, 'ref_fsg',
   '팀원 공유 원본 new_data/DLA_FSG_공식분류표.csv 77행(16,477 bytes, SHA-256 cc752af27c895199d10854baac7122ceb46782c091c5a4fc24e013ed275be9e8, 팀원 다운로드일 미확인) + 95·96·99 3행 보완(GSA PSC Manual 2025-04 xlsx product group으로 확인). DLA 원문 URL은 국내에서 403(Akamai)이라 미대조. 계약정보·조달계획·입찰 CSV에는 FSC가 없어 이 표와 엮이지 않음(B2·국방표준종합·사전의향서만 FSC 보유)')
ON DUPLICATE KEY UPDATE file_bytes = VALUES(file_bytes), sha256 = VALUES(sha256), raw_row_count = VALUES(raw_row_count), note = VALUES(note);

-- §5 검증 (기대: ref_fsg 80 · historical 2 · electronic 2 / v_b2_fsg_summary 상위 53 16,300 · 25 3,545 · 59 2,942 · 58 379 / 미대응 fsg_code는 공란·NULL만)
SELECT COUNT(*) AS ref_fsg_rows, SUM(is_historical) AS historical, SUM(is_electronic_group) AS electronic FROM ref_fsg;
SELECT fsg_code, fsg_name_ko, b2_row_count, b2_part_count FROM v_b2_fsg_summary ORDER BY b2_row_count DESC LIMIT 8;
SELECT fsg_code, b2_row_count FROM v_b2_fsg_summary WHERE fsg_name_ko IS NULL;
SELECT COUNT(*) AS meta_column_dict_rows FROM meta_column_dict;
SELECT dataset_key, raw_row_count, target_table FROM meta_dataset WHERE dataset_key = 'fsg_master';
