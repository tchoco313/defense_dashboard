-- =============================================================================
-- v_customs_region_gwacheon_year — 과천시 소재 수입자 비중(방위사업청 소재지), 추정  (작성·적용 2026-09-21)
--   근거 open-decisions-2026-09-21.md D1 ⑤. 원천 raw_customs_region(시군구 × 월 × HS6, 금액 천 달러, 수입은 납세의무자 주소지 기준).
--   정의: HS6 × 연도. 분모 = 전국(17시도 전체) 수입액, 분자 = sgg_name '경기도 과천시' 수입액. docs/data-sources.md 「지역 통계 검증」과 같은 분모.
--   표현 규칙: 「과천시 소재 수입자 비중(방위사업청 소재지), 추정」 — 「군 직접 수입 하한」이라 쓰지 않는다(양방향 편의, app-metrics-review §1 #2).
--   화면 반영 여부는 팀 결정(M7). 뷰는 그 결정과 무관하게 재현 경로로 둔다.
-- 원칙: raw 금액은 쉼표 포함 문자열 → REPLACE 후 CAST. 실측 09-21: 쉼표 제거 후 숫자 아닌 값 0행. 2026년은 8개월(is_partial_year=1).
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-21_gwacheon_view.sql
-- 기대: 246행(24 × 11년 중 HS2022 신설 코드의 2022 이전 조합은 행 없음 — v_hhi_hs6_year 와 같은 246). 2025 검증값(data-sources.md와 일치) 880730 0.3009(745,179 / 224,248) · 901490 0.2700 · 852560 0.2015 · 841191 0.0948 · 854231 0.0016
-- 되돌리기: DROP VIEW v_customs_region_gwacheon_year (schema.sql·table_dict.csv에서도 제거)
-- =============================================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE OR REPLACE VIEW v_customs_region_gwacheon_year AS
SELECT r.req_hs                                                        AS hs6,
       CAST(r.req_year AS UNSIGNED)                                    AS year,
       SUM(CAST(REPLACE(r.imp_usd_amt, ',', '') AS UNSIGNED))          AS imp_kusd_total,      -- 전국 수입액(천 달러)
       SUM(CASE WHEN r.sgg_name = '경기도 과천시'
                THEN CAST(REPLACE(r.imp_usd_amt, ',', '') AS UNSIGNED) ELSE 0 END) AS imp_kusd_gwacheon,   -- 과천시 수입액(천 달러)
       CAST(SUM(CASE WHEN r.sgg_name = '경기도 과천시'
                     THEN CAST(REPLACE(r.imp_usd_amt, ',', '') AS UNSIGNED) ELSE 0 END) AS DOUBLE)
         / NULLIF(SUM(CAST(REPLACE(r.imp_usd_amt, ',', '') AS UNSIGNED)), 0)    AS gwacheon_share,       -- 0~1
       SUM(CASE WHEN r.sgg_name = '경기도 과천시'
                THEN CAST(REPLACE(r.imp_cnt, ',', '') AS UNSIGNED) ELSE 0 END)   AS imp_cnt_gwacheon,     -- 과천시 수입 건수
       COUNT(DISTINCT r.sgg_name)                                      AS sgg_count,           -- 수입 실적 시군구 수
       MAX(r.req_year = '2026')                                        AS is_partial_year
FROM raw_customs_region r
GROUP BY r.req_hs, r.req_year;

-- 검증(주석 — DBHub app_ro)
-- SELECT hs6, imp_kusd_total, imp_kusd_gwacheon, ROUND(gwacheon_share,4) FROM v_customs_region_gwacheon_year WHERE year=2025 ORDER BY gwacheon_share DESC;
-- SELECT COUNT(*) FROM v_customs_region_gwacheon_year;   -- 246
