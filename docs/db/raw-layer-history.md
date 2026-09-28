# raw_ 계층 — 만들었다가 없앤 경위 (2026-09-15 ~ 09-22)

처음에는 원본 데이터를 RDS 에 `raw_` 표로 그대로 넣고 그 위에 정제(`clean_`)·집계(`fact_`/`dim_`)·뷰(`v_`)를 쌓았다.
09-22 중간 점검 피드백을 받고 원본은 **파일**로만 두고 DB 에서는 `raw_` 표를 모두 지웠다. 이 문서는 그 과정을 한 곳에 모은 것이다.
세부 근거는 아래 링크의 원문에 있다.

## 한눈에

| 시점 | DB 구성 | 무슨 일 |
|---|---|---|
| 09-15 | 표 31 · 뷰 6 | 스키마 설계. `ref_` → **`raw_`** → `clean_` → `fact_`/`dim_` → `v_` 5계층. 팀 결정 "다 넣어야" 로 원본까지 전부 적재 |
| 09-18 | 표 48 · 뷰 31 | 국외조달(A7) · 방사청 API · KOSIS 등 `raw_` 추가, AWS RDS 로 이전 |
| 09-19 | 표 56 · 뷰 31 (그중 `raw_` 23) | 정제 노트북 6개가 RDS `raw_` 를 읽어 `clean_` 을 채움 |
| **09-22** | 표 56 → **37** · 뷰 31 | 교수 피드백 → `raw_` 23표 삭제. 원본은 `data/raw/` 파일 + SHA-256 기록 |
| 09-23 | 표 44 · 뷰 31 | 국방반도체 참조표 `ref_semi_*` 7개 추가 (현재) |

## 1. 왜 처음엔 raw 를 DB 에 넣었나 (09-15)

`docs/db/schema-design.md` 첫 판(커밋 `2a899f0`)의 설계 원칙 「원본 보존, 정제와 분리」.

- **원본 그대로 보존**: `raw_*` 는 CSV 열을 전부 문자열로 받고 업무키 UNIQUE 를 걸지 않았다. 원본의 중복(국산화품목 완전 중복 8,940행, 계약 충돌 1키, 입찰결과 199키)도 지우지 않고 그대로 담았다.
- **계보 추적**: `clean_*.raw_row_id` 가 `raw_*.row_id` 를 FK 로 가리켜, 정제된 한 행이 원본 몇 번째 행에서 왔는지 SQL 로 따라갈 수 있게 했다.
- **파일별 건수 재현**: `source_file` · `source_row_no` 로 원본 건수를 SQL 로 다시 셀 수 있게 했다.
- **실제로 한 번 도움이 됐다**: 09-15 15:12 팀원이 ERD 작업 중 `db/schema.sql` 을 서버에 실행해 적재 데이터 약 65만 행이 지워졌다. 이때 `load_db.py --ref --raw --fact` 로 1분 만에 재적재했다(`schema-design.md` 재적재 절).

## 2. 무엇이 문제였나 (09-22 중간 점검)

교수 피드백 원문 요지(`docs/report/feedback/professor-feedback-2026-09-22.md` §0):

> 원본(Raw) 데이터를 그대로 RDB 테이블로 구축하는 것은 비효율적이다. 원본은 파일 형태로 관리하고, DB 에는 전처리가 완료된 정제 데이터와 검색 최적화를 위한 뷰 위주로 설계해야 한다.

구두 보충: 테이블 수를 늘리기보다 **표마다 어디에 쓰는지 설명할 수 있어야** 하고, 발표 흐름은 **수집 → 전처리 → DB 저장 → 활용** 이어야 한다.
팀은 이것을 "raw 금지" 가 아니라 "과제 규모에 맞게 DB 를 단순하게" 로 읽었다.

## 3. 어떻게 없앴나 (09-22, 커밋 `9b4a4b9`)

지우기 전에 **파일만으로 같은 결과가 나오는지 먼저 증명**하고, 두 단계로 나눠 적용했다.

| 순서 | 한 일 | 확인 |
|---|---|---|
| ① 파일 입력 도구 | `scripts/load_db.py` 에 `read_raw(<데이터셋 키>)` 추가 — 원본 파일을 DB 와 같은 파서로 읽는다 | 23종 중 22종 기대 건수 일치(1종은 파일이 다른 PC 에 있었음) |
| ② 동일성 검증 | 파일 ↔ RDS `raw_` 22표를 열별 비NULL 수 · 문자 길이 합으로 대조 | 전부 일치. 행 순번 불일치 2표는 따로 처리 |
| ③ 노트북 전환 | 정제 노트북 6개가 RDS 대신 `read_raw` 로 파일을 읽게 바꾸고 다시 실행 | 오류 0, `원본 = 정제 + 제외` 차이 0 |
| ④ 대체 표 | 뷰 · 화면이 raw 를 직접 읽던 4곳을 정제·기준 표로 대체 — `ref_hs_code_master` · `ref_hs6_name` · `clean_customs_region` · `clean_dapa_defense_company` | 뷰 4개 재정의 후 판정 결과 유지 |
| ⑤ 1단계 alter | `db/alter_2026-09-22_raw_successors.sql` — 대체 표 생성, raw 를 가리키던 FK 15개 제거 | 2회 실행 멱등 |
| ⑥ 백업 | DROP 직전 덤프 `data/db_dump/raw_tables_2026-09-22.sql.gz` (268MB → 32MB, 깃에 없음) | — |
| ⑦ 2단계 alter | `db/alter_2026-09-22_drop_raw_layer.sql` — `raw_` 23표 DROP | 표 37 · 뷰 31 · 전 뷰 조회 정상 |

같은 날 raw 를 거의 그대로 복사한 `clean_` 표 4개도 지웠다(`db/alter_2026-09-22_drop_clean_copies.sql` · `drop_p1_clean.sql`).

## 4. 지운 뒤에도 남긴 것

- **원본 파일**: `data/raw/` (읽기 전용으로 동결, 깃에는 안 올림 · 팀 드라이브 사본). `meta_dataset` 에 경로 · 크기 · SHA-256 · 파서 건수를 기록해 파일이 바뀌면 알 수 있다.
- **원본 열 사전**: `raw_` 23종의 열 설명 319행은 `db/column_dict.csv` · RDS `meta_column_dict` 에 **원본 파일 열 사전**으로 유지했다. `db/table_dict.csv` 에서는 `kind=file` 이다. 데이터 명세서(산출물 3)의 원천이다.
- **계보 열**: `clean_*.raw_row_id` 는 남기되 뜻을 「원본 파일 파서 순번」 으로 바꿨다.
- **데이터셋 키**: 파일을 부르는 이름은 옛 표 이름 그대로다 — `read_raw("raw_customs_trade")`.

## 5. 당시 기록이라 고치지 않은 파일

아래는 raw 가 DB 에 있던 때의 작업물이다. **지금 RDS 에서 실행하면 표가 없어 실패한다.** 과정을 보여 주는 기록으로 남긴다.

| 파일 | 당시 용도 |
|---|---|
| `db/query_p4_domestic_explore.sql` · `query_p4_join_check.sql` · `query_p4_ko_views.sql` | 국내조달 raw 탐색 · 조인 키 검증 (09-18) |
| `db/query_p1_customs_check.sql` | 관세청 raw → fact 검산 (09-21) |
| `db/query_null_profile.sql` | 결측 프로파일 (09-19) |
| `db/alter_2026-09-15` ~ `09-21` 의 raw 관련 파일 | raw 표를 만들고 고친 변경 이력 |
| 중간 발표 기록 3종 (`docs/report/feedback/midterm-*-2026-09-22.md`) | 발표 당시 상태(표 56 · raw 적재)를 담은 자료 |

## 6. 되돌려야 한다면

- 덤프 복원: `mysql … defense_dashboard < raw_tables_2026-09-22.sql` (덤프는 로컬 `data/db_dump/`)
- 또는 raw 적재 코드가 있던 판으로: `git show 9b4a4b9^:scripts/load_db.py` 의 `--raw`

## 원문

- 결정 · 영향 · 실행 기록: `docs/report/feedback/professor-feedback-2026-09-22.md` §1 ~ §3
- 변경 기록: `docs/db/schema-change-log.md` 26번 · `docs/db/schema-design.md` §1-1
- alter 머리말: `db/alter_2026-09-22_raw_successors.sql` · `db/alter_2026-09-22_drop_raw_layer.sql`
