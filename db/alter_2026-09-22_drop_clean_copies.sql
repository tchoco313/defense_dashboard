-- =============================================================================
-- 사전 밖 표 4개 삭제: clean_customs_trade · clean_customs_progress · clean_hs_unit_name · clean_hs_code_master
-- (작성·적용 2026-09-22, 사용자 승인)
--
-- 배경: 2026-09-21 `alter_2026-09-21_drop_customs_copies.sql`로 지운 두 표가 같은 날 16:12·18:03(KST)에 다시 생성되고,
--       09-22 00:29·00:33에 HS 마스터 2표가 추가로 생겼다(information_schema CREATE_TIME, UTC+9). 만든 계정은 미확인
--       (app_ro로 감사 정보 조회 불가. CREATE 권한: admin + dev_sua·dev_taeho·dev_donghyun·dev_jisu).
-- 실측(DBHub app_ro, 09-22): 네 표 모두 raw 와 행 수 1:1 —
--       clean_customs_trade 294,420(총계행 246 포함, is_total=1) · clean_customs_progress 264 ·
--       clean_hs_unit_name 17,072 · clean_hs_code_master 12,469. 새 trade 표는 금액 BIGINT·stat_year/month 분리 등 09-20판보다
--       나아졌으나 COMMENT 「268,909행」 오기·추적 열 불일치·재현 스크립트 없음은 그대로.
-- 판단: schema.sql · table_dict.csv · column_dict.csv · meta_load_log · meta_column_dict 어디에도 없고 뷰·앱·노트북 참조 0건.
--       명세(clean-conversion-spec-2026-09-18.md §2 P1)의 목표 객체는 fact_customs_monthly(=raw − 총계 246 = 294,174) 검증 ·
--       progress 「clean 불필요」 · hs_code_master → dim_hs10 보강 · hs_unit_name → ref_hs_rule_flag.hs6_name_ko 원천이며,
--       네 표는 그 목표 객체가 아니다. 유지하면 데이터 명세서와 DB가 어긋난 채 제출된다(10-02).
-- 영향: 원본 raw_ 4표·fact_customs_monthly·dim_hs10·ref_hs_rule_flag 불변. BASE TABLE 60 → 56 기대.
-- 후속: open-decisions-2026-09-21.md D14 · docs/next.md 「재생성 방지 — 팀 확인」. 새 clean 표가 필요하면 명세 §2 갱신 →
--       alter_<날짜>_<주제>.sql → 열 사전 → meta_load_log 순으로 만든다(docs/runbook/commands.md §4·§11).
-- =============================================================================

USE defense_dashboard;
DROP TABLE IF EXISTS clean_customs_trade;
DROP TABLE IF EXISTS clean_customs_progress;
DROP TABLE IF EXISTS clean_hs_unit_name;
DROP TABLE IF EXISTS clean_hs_code_master;

-- 확인:
-- SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='defense_dashboard' AND TABLE_TYPE='BASE TABLE';  -- 56
-- SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='defense_dashboard'
--   AND (TABLE_NAME LIKE 'clean_customs%' OR TABLE_NAME LIKE 'clean_hs_%');                                            -- 0행
-- SELECT (SELECT COUNT(*) FROM raw_customs_trade), (SELECT COUNT(*) FROM raw_customs_progress),
--        (SELECT COUNT(*) FROM raw_hs_unit_name), (SELECT COUNT(*) FROM raw_hs_code_master);        -- 294420 · 264 · 17072 · 12469
