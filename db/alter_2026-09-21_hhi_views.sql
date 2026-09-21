-- =============================================================================
-- HHI 뷰 4개 정의 정정: share DOUBLE 정밀 계산 + country_count 「실적(>0) 국가 수」  (작성·적용 2026-09-21)
--   근거 docs/report/feedback/open-decisions-2026-09-21.md D6·D7 (Claude 결정, 사용자 위임). 09-20 제안 파일 alter_2026-09-20_country_count.sql 을 대체·삭제.
--
-- D6 country_count: v_hhi_hs6_year · v_hhi_export_hs6_year 의 COUNT(*) 는 v_import_hs6_year 의 모든 (hs6, year, stat_cd) 행을 세므로
--       수입액 0(수출만 있는 국가)도 포함해 「수입국 수」가 부풀려진다. 2025 실측: 847180 127 → 실제 수입>0 73 · 854231 86 → 68 ·
--       852692 104 → 50 · 851762 144 → 86. 화면 ①(app/pages/1_수출입_현황.py)이 이 열을 「N개국」으로 그대로 표시하므로 발표 전 정정.
-- D7 share: v_import_share_hs6_year · v_export_share_hs6_year 의 share 가 DECIMAL 나눗셈이라 소수 4자리로 반올림돼, 그 위의 뷰 HHI 가
--       pandas 정밀 계산(app/metrics.concentration · notebooks/eda_customs)과 최대 0.70점 어긋났다. CAST(... AS DOUBLE) 로 계산해 두 값을 일치시킨다.
-- 원칙:
--   · 뷰 이름 · 출력 열 이름 · 순서 유지. country_count 는 CAST(SUM(불리언) AS UNSIGNED) 로 정수형 유지.
--   · 정본 db/schema.sql 의 같은 뷰 4개 본문도 이 파일과 동일하게 고쳤다. alter_2026-09-17_view_collation.sql · alter_2026-09-17_export.sql 은
--     구판으로 남으므로 재실행 시 이 파일을 뒤에 다시 적용.
--   · db/table_dict.csv role(수입·수출 HHI 뷰 「실적(>0) 국가 수」) 갱신 → docs/db/table-catalog.md 재생성.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-21_hhi_views.sql   (RDS admin). DBHub(app_ro)는 불가.
-- 기대: 2회 모두 exit 0. 검증 SQL(§3) 2025 847180=73 · 854231=68 · 852692=50 · 851762=86, hhi 정수 자리·top1_stat_cd 불변.
-- 되돌리기: 이전 정의 = share 를 v.imp_dlr / NULLIF(...) 로, country_count 를 COUNT(*) 로 CREATE OR REPLACE.
-- =============================================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 점유율 뷰 2개: share 를 DOUBLE 로
CREATE OR REPLACE VIEW v_import_share_hs6_year AS
SELECT v.hs6, v.year, v.stat_cd, v.imp_dlr, v.is_partial_year,
       SUM(v.imp_dlr) OVER (PARTITION BY v.hs6, v.year)                                          AS imp_dlr_total,
       CAST(v.imp_dlr AS DOUBLE) / NULLIF(SUM(v.imp_dlr) OVER (PARTITION BY v.hs6, v.year), 0)  AS share,
       RANK() OVER (PARTITION BY v.hs6, v.year ORDER BY v.imp_dlr DESC)                          AS rnk
FROM v_import_hs6_year v;

CREATE OR REPLACE VIEW v_export_share_hs6_year AS
SELECT v.hs6, v.year, v.stat_cd, v.exp_dlr, v.is_partial_year,
       SUM(v.exp_dlr) OVER (PARTITION BY v.hs6, v.year)                                          AS exp_dlr_total,
       CAST(v.exp_dlr AS DOUBLE) / NULLIF(SUM(v.exp_dlr) OVER (PARTITION BY v.hs6, v.year), 0)  AS share,
       RANK() OVER (PARTITION BY v.hs6, v.year ORDER BY v.exp_dlr DESC)                          AS rnk
FROM v_import_hs6_year v;

-- §2 HHI 뷰 2개: country_count = 실적(>0) 국가 수
CREATE OR REPLACE VIEW v_hhi_hs6_year AS
SELECT s.hs6, s.year,
       MAX(s.imp_dlr_total)                                  AS imp_dlr_total,
       SUM(POWER(s.share * 100, 2))                          AS hhi,
       CAST(SUM(s.imp_dlr > 0) AS UNSIGNED)                  AS country_count,   -- 수입액 > 0 인 국가 수
       MAX(CASE WHEN s.rnk = 1 THEN s.stat_cd END)           AS top1_stat_cd,
       MAX(CASE WHEN s.rnk = 1 THEN s.share   END)           AS top1_share,
       MAX(s.is_partial_year)                                AS is_partial_year
FROM v_import_share_hs6_year s
GROUP BY s.hs6, s.year;

CREATE OR REPLACE VIEW v_hhi_export_hs6_year AS
SELECT s.hs6, s.year,
       MAX(s.exp_dlr_total)                                  AS exp_dlr_total,
       SUM(POWER(s.share * 100, 2))                          AS hhi_export,
       CAST(SUM(s.exp_dlr > 0) AS UNSIGNED)                  AS country_count,   -- 수출액 > 0 인 국가 수
       MAX(CASE WHEN s.rnk = 1 THEN s.stat_cd END)           AS top1_stat_cd,
       MAX(CASE WHEN s.rnk = 1 THEN s.share   END)           AS top1_share,
       MAX(s.is_partial_year)                                AS is_partial_year
FROM v_export_share_hs6_year s
GROUP BY s.hs6, s.year;

-- §3 검증 SQL (주석 — 적용 뒤 DBHub app_ro 로)
-- SELECT hs6, country_count, ROUND(hhi,2), top1_stat_cd, top1_share FROM v_hhi_hs6_year WHERE year = 2025 AND hs6 IN ('847180','854231','852692','851762');
--   -- 73 · 68 · 50 · 86 / 적용 전 hhi 5276.18 · 3492.53 · 3608.14 · 1899.42 와 정수 자리 동일 / top1 CN · TW · VN · CN
-- SELECT hs6, country_count FROM v_review_list WHERE year = 2025 ORDER BY hs6;   -- 같은 값으로 바뀜(의미 변경 확인)
