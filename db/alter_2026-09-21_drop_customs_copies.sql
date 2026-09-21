-- =============================================================================
-- 사전 밖 표 2개 삭제: clean_customs_trade · clean_customs_progress  (작성·적용 2026-09-21, 사용자 승인)
--
-- 배경: 2026-09-20 밤 RDS에 생성된 두 표(P1 담당 작업으로 추정)는 raw_customs_trade · raw_customs_progress 의 복사본이다.
--       점검(docs/report/feedback/open-decisions-2026-09-21.md D14): 값은 raw 와 전부 일치(294,420행)하나 총계행 246 포함 · 금액 VARCHAR ·
--       추적 열 없음 · meta_load_log/meta_column_dict/스크립트 없음. P1 목표 객체는 이미 있는 fact_customs_monthly(명세 §2 #1)이며
--       progress 는 「clean 불필요」(§2 #2). schema.sql · column_dict.csv · reset_data.sql 에 없어 카탈로그 경고(사전 누락 2)가 난다.
-- 영향: 뷰 · 앱 · 노트북 어디에서도 참조하지 않음(2026-09-21 grep 0건). 원본 raw_ 두 표는 그대로.
-- 후속: P1 검산은 표 대신 db/query_p1_customs_check.sql 로(docs/report/data/p1-recheck-list-2026-09-21.md).
-- =============================================================================

USE defense_dashboard;
DROP TABLE IF EXISTS clean_customs_trade;
DROP TABLE IF EXISTS clean_customs_progress;

-- 확인: SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='defense_dashboard' AND TABLE_NAME LIKE 'clean_customs%';  -- 0행
