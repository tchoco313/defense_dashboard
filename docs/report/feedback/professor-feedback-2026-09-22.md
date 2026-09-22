# 교수 피드백 대응 (2026-09-22, 중간 점검)

9/22 중간 점검(`midterm-checkin-2026-09-22.md`)에서 받은 피드백과 그 대응. 09-15·09-17 문서와 같은 형식이며, 이 문서가 뒤집는 종전 결정은 §1에 명시한다. 수치는 저장소 기록(`docs/db/schema-design.md`, `docs/next.md`)과 2026-09-22 RDS 실측에서 가져왔고 새로 계산한 값은 없다.

## 0. 피드백 원문 요지

**데이터베이스 설계 최적화** — 원본(Raw) 데이터를 그대로 RDB 테이블로 구축하는 것은 비효율적이다. 원본은 파일(또는 오브젝트 스토리지) 형태로 관리하고, DB에는 전처리가 완료된 정제 데이터(Clean Schema)와 검색 최적화를 위한 뷰(View) 위주로 설계해야 한다.

구두 보충(사용자 정리):

1. 수집한 원본을 전부 DB 테이블로 만들 필요는 없다. 파일로 보관하고 위치·링크를 관리하면 된다. S3는 예시일 뿐 이 프로젝트에서 반드시 쓰라는 뜻은 아니다.
2. 현재 구성은 원본까지 DB에 들어가 있어 불필요하게 많은 데이터를 저장한다.
3. DB에는 실제 분석·대시보드에 쓰는 정제 데이터를 중심으로 넣는다 — 필요한 행·열을 고르고 결측·중복·표준화를 처리한 뒤 저장.
4. 테이블 수를 늘리기보다 **표마다 어디에 쓰는지 설명할 수 있어야** 한다.
5. 작업·발표 순서는 **수집 → 전처리 → DB 저장 → 활용**. 과거 데이터를 모아 분석하는 과제이므로 전처리를 먼저 설명하고 "정제된 데이터를 이런 스키마로 저장했고, 조회를 편하게 하려고 뷰를 구성했다"는 흐름으로 보여 준다.
6. 실시간 자동 수집이라면 자동화 파이프라인이 필요하지만 이 과제는 그 방식이 아니므로 그 수준까지 만들 필요 없다.

**해석**: "raw 테이블 금지"나 "즉시 삭제"가 아니라, 과제 규모와 사용 방식에 맞게 DB를 단순하게 구성하라는 피드백이다.

## 1. 결정 (2026-09-22, 사용자)

| 항목 | 결정 | 근거 | 종전 결정과의 관계 |
|---|---|---|---|
| 원본 계층 | RDS `raw_` 23표를 **삭제**한다. 원본은 `data/raw/` 파일(훅·읽기 전용으로 동결) + `meta_dataset`의 경로·크기·SHA-256·파서 건수 + 팀 드라이브 사본으로 관리한다 | 요지 1·2 | 09-15 "raw_ 계층까지 DB에 적재"(schema-design §1-1)를 **뒤집음** |
| 오브젝트 스토리지 | S3는 쓰지 않는다(비용 0 유지, 파일+SHA로 충분) | 요지 1, AWS 무료 크레딧 원칙 | — |
| 남기는 표 | 정제(`clean_`·`fact_`·`dim_`) + 기준(`ref_`) + 기록(`meta_`) + 뷰(`v_`). 뷰·화면이 raw를 직접 읽던 4곳만 정제·기준 표로 대체(`clean_customs_region`·`clean_dapa_defense_company`·`ref_hs_code_master`·`ref_hs6_name`) — 각각 사용처가 있다 | 요지 3·4 | 09-22 오전 "P1 clean 4표 폐기"(단순 복제본)와 양립 — 이번 4표는 유일한 DB 사본이며 필요한 열·행만 담는다 |
| 원본 추적 열 | `clean_*.raw_row_id`는 유지하되 뜻을 **원본 파일 파서 순번**(파일명 정렬 × 파일 내 행 순, `load_db.read_raw`가 매김)으로 재정의. `fact_customs_monthly.raw_row_id`는 삭제(자연키 hs10+stat_cd+yyyymm로 충분) | 09-15 계보 원칙 유지, PK·노트북 변경 최소 | — |
| 정제 입력 | 노트북 6개는 RDS raw_ 대신 `scripts/load_db.py`의 `read_raw()`로 `data/raw/` 파일을 읽는다(파서·헤더 대조·개인정보 마스킹은 기존 함수 재사용). `clean_company.ipynb`는 P4 §6과 중복이라 삭제 | 요지 5 재현성 | 런북 §6 노트북 목록에서 `clean_company` 제외 |
| 설명 순서 | 문서·아키텍처 도면·발표는 **수집 → 전처리 → DB 저장 → 활용** | 요지 5 | `next.md` #10 도면 순서 변경 |

## 2. 영향 범위

| 대상 | 내용 |
|---|---|
| RDS | 표 56 → **37**(raw 23 삭제, 후속 4 신설), 뷰 31 유지. FK 15개(clean 14 + fact 1)와 `fact_customs_monthly.raw_row_id` 삭제 |
| 뷰 4개 재정의 | `v_customs_region_gwacheon_year` · `v_defense_company_sector` · `v_hs10_use_tag_all` · `v_hs6_candidate_rule`(+의존 `v_hs6_candidate_vs_whitelist`) |
| 앱 4쿼리 | `1_수출입_현황.py`·`6_조회.py` HS10 라벨 → `ref_hs_code_master`, `4_정책_산업_배경.py` KOSIS 2쿼리 → `clean_kosis_*` |
| 스크립트 | `load_db.py`(`--raw` 제거, `read_raw`·pandas `--fact`), `gen_table_catalog.py`(파일 계층 표시), `gen_data_spec_xlsx.py`(원본 명세를 파일에서), `reset_data.sql` |
| 사전 | `table_dict.csv` raw 23행은 `kind=file`(원본 파일 데이터셋)로 유지, `column_dict.csv`·`meta_column_dict` raw 319행은 **원본 파일 열 사전**으로 유지(헤더 대조·산출물 3 명세의 원천) |
| 문서 | `CLAUDE.md`, `docs/db/*`, `docs/runbook/commands.md`, `docs/reference/data-cleaning-rules.md`, `app/specs` 4개, `docs/next.md`. 중간발표 기록 3종은 이력이라 고치지 않음 |

## 3. 실행 기록 (2026-09-22, 전부 실행·확인)

| 단계 | 결과 |
|---|---|
| 파일 입력 도구 | `scripts/load_db.py`: `read_raw(<데이터셋 키>)`·`log_raw_stage` 추가, `--raw`·`do_raw` 제거, `--fact`를 read_raw → pandas(`build_customs_dim_fact`, `build_customs_region`)로, `--ref`가 `ref_hs_code_master`·`ref_hs6_name`을 파일에서 생성. `--dry-run` 22/23 데이터셋 기대 건수 일치(`raw_customs_region` 파일은 이 PC 미보유) |
| DROP 전 검증 | 22표 파일↔RDS 열별 비NULL 수·문자 길이 합 일치. `row_id` = 파서 순번 20표 일치; 불일치는 `raw_customs_trade`(2회 적재 → fact의 `raw_row_id` 열 삭제)·`raw_krit_task`(차수별 추가 적재 → `clean_krit_task.raw_row_id` 96행 재번호). `raw_kosis_production_index`는 DB의 `stat_ym='p)'` 16행이 파일 파서(09-19 수정)에서는 정상 월로 읽힘 |
| 노트북 | 6개를 `raw(...)`(read_raw) 입력으로 전환, `clean_company.ipynb` 삭제, p4에 `clean_dapa_defense_company` 적재 블록 추가. nbconvert 실행 6/6 오류 0, `raw = clean + excluded` 차이 0 |
| alter 1/2 | `db/alter_2026-09-22_raw_successors.sql` 2회 실행(멱등): 후속 표 4개(11,327 / 2,254 / 273,586 / 84), 뷰 4개 재정의, FK 15개·fact `raw_row_id` 삭제. `v_hs6_candidate_vs_whitelist` 판정 유지 13 / 신규 39 / 강등 11 |
| 덤프 | `data/db_dump/raw_tables_2026-09-22.sql.gz`(mariadb-dump, 268MB → 32MB, gitignore) |
| alter 2/2 | `db/alter_2026-09-22_drop_raw_layer.sql` 2회 실행: raw_ 23표 DROP, 사전 정리. RDS 실측 표 37 · 뷰 31 · `meta_column_dict` 858(원본 파일 열 사전 319 유지) · fact 294,174 · 뷰 전부 조회 정상 |
| 정본 | `db/schema.sql`(CREATE 37, 가드 → fact, §2 원본 파일 계층 주석, 뷰 4개) — RDS 열 목록과 전 표 일치 확인. `db/reset_data.sql`(TRUNCATE 25), `db/table_dict.csv`(91, raw 23행 kind=file), `db/column_dict.csv`(858), `load_db.py REF_EXPECTED` 858 |
| 앱 | `1_수출입_현황.py`·`6_조회.py` → `ref_hs_code_master`, `4_정책_산업_배경.py` → `clean_kosis_*`(열 매핑만, 그리는 로직 불변), `5_DATA_INFO.py` 캡션. AppTest로 페이지 1·4·6 실행 예외 0, unittest 26 통과 |
| 생성기 | `gen_table_catalog.py`(원본 파일 절, 경고 0), `gen_data_spec_xlsx.py`(원본 명세를 read_raw로, xlsx 재생성), `gen_erd_html.py` 재생성 |
| 문서 | `CLAUDE.md`, `docs/db/schema-design.md`(§1·§2·§3-2·§3-4·§4·§5·§7 #26)·`table-guide.md`·`erd.md`·`table-catalog.md`, `docs/runbook/commands.md`, `docs/reference/data-cleaning-rules.md`·`clean-conversion-spec`, `docs/data-sources.md`, `app/specs` 20·24·32·91, `docs/next.md` |

**사용처 감사(보고만)**: 남은 37표 중 뷰·앱이 직접 읽지 않는 표 8개 — `clean_company`·`clean_company_name_link`(업체 축, 노트북 산출), `clean_dapa_contract_exec_by_service`(KPI 카드 예정), `clean_krit_task`(화면 ② 예정), `clean_openfiscal_program_link`(예산 연속성), `ref_equipment_alias`(노트북이 `equipment_std` 채움), `ref_sido_map`(시도 백필), `meta_column_dict`(기록·명세서). 모두 `table_dict.used_by`가 채워져 있고 노트북·스크립트가 쓴다. 화면 구현 후에도 안 쓰이면 그때 정리 대상.

**남은 것**: ① `raw_customs_region` 원본 CSV 24개를 맥에서 이 PC `data/raw/customs/`로 복사(명세서 예시값·`--fact` 재현) ② `clean_p1_customs_hs.ipynb` §6 priority 기대값을 13개 기준(8/5/11)으로 갱신(이번 변경과 무관한 기존 상태).
