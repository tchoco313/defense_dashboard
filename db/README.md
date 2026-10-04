# db — DB 스키마 · 적재 · 덤프

팀 DB 는 **AWS RDS MySQL 8.4** 의 `defense_dashboard` 하나다. 지금 구성은 **표 44개 · 뷰 31개, 약 90만 행**이다. 원본 파일은 DB 에 넣지 않고(Drive `2_데이터수집_저장` 에 보관), DB 에는 정제한 데이터 · 참조표 · 뷰만 둔다.

## 이 폴더의 파일

| 파일 | 내용 |
|---|---|
| `schema.sql` | 전체 DDL — 표 44 · 뷰 31. 빈 DB 에서만 실행된다(데이터가 있으면 맨 앞 안전장치가 멈춘다) |
| `seed_ref.sql` | 손으로 넣는 참조값(시도 매핑 · 군 목록 FSG 80행) — `load_db.py --ref` 가 실행, 여러 번 실행해도 같다 |
| `reset_data.sql` | 정제 · 사실 표만 비우고 참조표는 남긴다(다시 적재할 때, 관리자 계정) |
| `table_dict.csv` · `column_dict.csv` | 표 사전(역할 · 원천 · 단위 · 쓰는 화면) · 열 사전(916열) — DB 의 `meta_column_dict` 와 같은 내용 |
| `meta_dataset.csv` | 데이터셋 대장 — 출처 · URL · 기간 · 파일 크기 · SHA-256 · 파서 건수 |
| `clean_transform_map.csv` | 원본 열 → 정제 표 열 대응(분해 · 이동한 열 근거) |
| `query_eda2_2026-09-23.sql` | EDA 노트북 11 · 14 가 블록 단위로 읽는 집계 쿼리(대시보드와 같은 SQL) |
| `query_erd_link_rates.sql` | ERD 점선(논리 키) 연결률을 다시 재는 쿼리 |
| `query_join_key_check.sql` | 정제 규칙을 정할 때 조인 키를 검증한 기록 — 지금은 없는 원본층 표를 읽으므로 실행하면 실패한다(근거 보관용) |

설계 설명은 [`docs/db/schema-design.md`](../docs/db/schema-design.md), 관계도는 [`docs/db/erd.md`](../docs/db/erd.md), 표 · 열 정의는 [`docs/db/table-catalog.md`](../docs/db/table-catalog.md)(제출본 PDF: `docs/제출/03`, `04`).

## 표 묶음

| 접두어 | 개수 | 뜻 | 예 |
|---|---|---|---|
| `ref_` | 17 | 참조 · 기준표(팀 작성 + 공식 코드표) | `ref_hs_whitelist`(품목군 기준표 24행) · `ref_country` · `ref_fsg` · `ref_fsc` · `ref_hs_code_master` |
| `meta_` | 3 | 데이터셋 대장 · 열 사전 · **적재 기록** | `meta_dataset` · `meta_column_dict` · `meta_load_log` |
| `dim_` · `fact_` | 2 | 관세청 수출입 사실 표와 HS10 차원 | `fact_customs_monthly`(294,174행) · `dim_hs10` |
| `clean_` | 22 | 원본 파일을 정제한 표(정제 노트북 01~06 이 채움) | `clean_dapa_localized_item`(25,025) · `clean_dapa_contract`(43,105) · `clean_kdsis_nsn`(135,864) |
| `v_` (뷰) | 31 | 화면 · 보고서용 집계 | `v_import_hs6_year` · `v_hhi_hs6_year`(공급국 집중도) · `v_overseas_plan_yearly` |

표마다 행 수는 덤프와 함께 주는 `db_rowcount.csv` 에 있다.

## 어떻게 적재했나

```
원본 파일(data/raw/, Drive 2_데이터수집_저장)
  │  scripts/fetch_customs*.py · parse_krit.py      수집 · 공고 표 추출
  ▼
db/schema.sql                                       빈 DB 에 표 · 뷰 생성
  │  scripts/load_db.py --ref                       참조표 · 열 사전 · 데이터셋 대장 · 시드(seed_ref.sql)
  │  scripts/load_db.py --fact                      관세청 → dim_hs10 · fact_customs_monthly · clean_customs_region
  │  notebooks/01~06_clean_*.ipynb                  원본 → clean_* (제외한 행은 clean_excluded_row 에 사유와 함께)
  ▼
scripts/check_integrity.py · load_db.py --verify    시드 · 건수 검산 · 전자 판정 플래그 점검(PASS/FAIL)
```

- 정제는 **비어 있는 표에만** 적재하고, 단계마다 건수를 `meta_load_log` 에 남긴다. `원본 = 정제 + 제외` 가 맞는지 노트북 안에서 검산한다.
- **처음 설계는 달랐다.** 처음에는 원본까지 DB 의 `raw_` 표(23개)로 넣고 그 위에서 정제했다. 중간 점검 피드백(「원본은 파일로, DB 는 정제 데이터와 뷰 위주로」)에 따라, 파일만으로 같은 결과가 나오는지 열 단위로 대조한 뒤 `raw_` 표 23개와 원본을 거의 그대로 복사한 `clean_` 표를 지웠다. 그 뒤 국방반도체 참조표 7개를 더해 지금 표 44개 · 뷰 31개가 됐다. 개발 중 스키마 변경은 `alter_*.sql` 로 적용했고, 지금은 모두 `schema.sql` 한 파일에 반영돼 있다(옛 alter 파일은 깃 기록에 있다).

### `meta_load_log` — 적재 기록 읽는 법

| 열 | 뜻 |
|---|---|
| `table_name` · `dataset_key` | 적재한 표 · 원본 데이터셋 |
| `stage` · `row_count` | 단계(원본 전체 → 선택 연도 → 중복 처리 후 → 관련 후보 → 검증된 분석 대상)와 그 단계의 행 수 |
| `exclusion_reason` | 그 단계에서 뺀 이유 |
| `method` | 적재에 쓴 스크립트 · 노트북 절 |
| `measured_at` · `measured_by` | 잰 시각 · 적재한 DB 계정 |

기록은 적재 당시 그대로 두었다. 그래서 `method` 에는 **옛 이름**이 남아 있다.

| 기록 속 이름 | 지금 파일 |
|---|---|
| `notebooks/clean_p1_customs_hs.ipynb` | `notebooks/01_clean_customs.ipynb` |
| `notebooks/clean_b2_a7.ipynb` | `notebooks/02_clean_localized_overseas_plan.ipynb` |
| `notebooks/clean_p3_overseas.ipynb` | `notebooks/03_clean_overseas.ipynb` |
| `notebooks/clean_p4_domestic.ipynb` | `notebooks/04_clean_domestic.ipynb` |
| `notebooks/clean_p5_krit_p2_budget.ipynb` | `notebooks/05_clean_krit_budget.ipynb` |
| `notebooks/clean_p5_kosis.ipynb` | `notebooks/06_clean_kosis.ipynb` |
| `scripts/load_db.py --raw (...)` | 원본층(`raw_`)에 넣던 단계 — 지금은 `load_db.read_raw()` 가 파일을 직접 읽는다 |
| `db/alter_2026-*.sql` | 개발 중 스키마 변경 — 지금은 `schema.sql` 에 반영 |

열 설명(COMMENT) 속 기호: `R1`~`R4` 는 품목군 선정 규칙(공식 자료 근거 — [`docs/reference/hs-whitelist-definition.md`](../docs/reference/hs-whitelist-definition.md)), `M4` · `M5` 는 그 기준을 확정한 팀 회의 안건 번호, 날짜는 그 열을 더하거나 바꾼 날이다.

## 덤프 · 복원 (로컬 실행용)

팀 RDS 는 허용된 IP 에서만 접속되므로, 검사 · 시연용으로 DB 전체를 덤프 한 파일로 제공한다.

```bash
python scripts/dump_db.py        # RDS → build/db/defense_dashboard_dump.sql + db_rowcount.csv (약 140MB)
python scripts/build_package.py  # 커밋된 프로젝트 + 덤프 → build/defense_dashboard_local_<날짜>.zip
```

- 덤프에는 `CREATE DATABASE defense_dashboard` · 표 44 · 뷰 31 · 데이터가 모두 들어 있다. 뷰를 만든 계정 정보(DEFINER)와 서버 주소는 지웠다.
- 받은 패키지에서는 `db/dump/` 에 있다. **MySQL 8.0 이상**에 복원한다(MySQL 8 의 기본 문자 정렬 규칙 `utf8mb4_0900_ai_ci` 를 쓰므로 MariaDB 에서는 확인하지 않았다).
  - MySQL Workbench: `Server` → `Data Import` → `Import from Self-Contained File` → `db/dump/defense_dashboard_dump.sql` → `Start Import`
  - 명령줄: `mysql -u root -p < db/dump/defense_dashboard_dump.sql`
- 복원 뒤 `.env.example` 을 `.env` 로 복사하고 비밀번호만 채우면 대시보드 · 노트북 · 점검 스크립트가 로컬 DB 를 읽는다.
- 확인: `db_rowcount.csv` 의 행 수와 `SELECT COUNT(*)` 가 같아야 한다. `python scripts/check_integrity.py` 는 FAIL 0 이어야 한다.
