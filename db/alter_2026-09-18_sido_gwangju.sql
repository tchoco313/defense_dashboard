-- =============================================================================
-- ref_sido_map 토큰 정리 (2026-09-18) — 모호한 광주 토큰 제거 + 옛 표기 대전 토큰 추가
-- 실행 대상: **AWS RDS(운영 DB)**, 계정 admin(alter_* 관례, docs/runbook/aws-rds-setup.md §4). 팀 서버 192.168.100.221은 백업이라 적용하지 않는다.
--
-- ① 삭제: '광주'·'광주시'
--   광주광역시(29)와 경기도 광주시(41)가 겹친다. 첫 토큰만으로 29에 고정하면 경기 광주 주소가 잘못 분류된다.
--   영향(2026-09-18, 백업 서버 조회 — 컷오버 직후라 RDS와 같은 데이터): 계약 vendor_address + 낙찰 winner_address 중
--   '광주시'로 시작 0건, '광주'로 시작 1건('광주 서구' → 광주광역시). 이 1건은 정제 코드에서 둘째 토큰으로 처리한다:
--     첫 토큰 '광주'·'광주시' + 둘째 토큰 동구·서구·남구·북구·광산구 → 29
--     그 밖의 읍·면·동(오포읍·초월읍·곤지암읍 …)                      → 41
--     판별 불가                                                         → 미매칭, 사유 AMBIGUOUS_GWANGJU
-- ② 추가: '충남대전시' → 30
--   계약 주소 미매칭 21건 중 16건. 대전이 충남에서 분리(1989)되기 전 표기.
--   나머지 5건(테스트 주소 2, '**', '1 1', 사람 이름 1)은 토큰으로 처리하지 않는다 → 정제에서 미매칭 사유 기록.
--
-- ref_sido_map 을 읽는 뷰는 없음(information_schema.views 확인). clean_dapa_contract 는 0행이라 재계산 대상 없음.
-- 시드(db/seed_ref.sql)도 같은 날 같은 내용으로 고쳤다 → load_db.py --ref 재실행 시 되돌아가지 않는다.
-- 결과: 45행 → 44행 (−2 +1)
-- 되돌리기:
--   DELETE FROM ref_sido_map WHERE token = '충남대전시';
--   INSERT INTO ref_sido_map (token, sido_code, sido_name) VALUES ('광주','29','광주광역시'), ('광주시','29','광주광역시');
-- =============================================================================

START TRANSACTION;
DELETE FROM ref_sido_map WHERE token IN ('광주', '광주시');
INSERT IGNORE INTO ref_sido_map (token, sido_code, sido_name) VALUES ('충남대전시', '30', '대전광역시');
SELECT COUNT(*) AS rows_after_expect_44 FROM ref_sido_map;
COMMIT;
