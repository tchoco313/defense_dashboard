# 프로젝트 파일 정리 검증·실행 기록 (2026-09-20)

`data/`·`new_data/`·`resource/`·`db/`의 로컬 파일을 운영 DB(AWS RDS `defense_dashboard`)와 대조해 완전 중복·구버전·미채택·재생성 가능 산출물을 판정하고, 승인된 A 목록(완전 중복 65개)을 삭제한 기록. 이 문서의 수치는 전부 이 세션의 실측(확인됨)이며, 문서 인용·추론·미확인은 따로 표시한다.

## 1. 대조 방법

- DB 대상 확인: `SELECT DATABASE(), CURRENT_USER(), @@version, @@hostname` → `defense_dashboard` / `app_ro@%` / `8.4.11` / `ip-10-7-0-61`(RDS). BASE TABLE 56 · VIEW 31 = `db/schema.sql`. DBHub `execute_sql` SELECT만 실행.
- 내용 대조: 로컬 원본을 `scripts/load_db.py`의 적재 함수(`frame_generic`·`frame_krit`·`frame_kosis_wide1/2`)로 그대로 변환한 뒤 행마다 `SHA-256(모든 열을 0x1F로 연결)` 앞 60비트를 합산(중복 다중도 보존). DB에서는 `source_file`별 `SUM(CAST(CONV(LEFT(SHA2(CONCAT_WS(CHAR(31 USING utf8mb4), IFNULL(c1,''), …),256),15),16,10) AS DECIMAL(20,0)))`를 계산해 비교. 적재 규칙(빈 문자열→NULL, 담당자 열 NULL, `int_cols` 정수화)만 적용하고 그 외 정규화는 하지 않음.
- 파일 동일성: SHA-256 전수(4개 폴더 247파일). Google Drive `국방부품_공급망_데이터`는 `rclone md5sum`(읽기)으로 대조.

## 2. 결과 요약

| 항목 | 결과 |
| --- | --- |
| raw 22표 파서 건수 | `load_db.py` expected·DB `COUNT(*)`와 22/22 일치 |
| 행 해시 대조 | 22표 66파일 전부 일치(xlsx 2표는 `openpyxl` 재설치 뒤 대조: 12,469 / 17,072 일치). 불일치 1: `raw_kosis_production_index` — DB에 `stat_ym='p)'` 16행(파서 09-19 수정 후 미재적재, `load_db.py:305-308`) |
| `meta_dataset` | DB 25행 vs `db/meta_dataset.csv` 26행(CSV의 `customs_region` 행은 DB에 없고 tier가 ENUM 밖). DB sha256은 단일 파일 17건 중 15건 로컬 일치. 불일치 2: `customs_progress`(DB 값 = 231행판 7,471 B `af359f89…`, 현행 264행 파일은 `fc1d199e…` 8,538 B), `krit_task`(sha는 `26-1차_…_t7.csv` 1개 값, bytes는 12파일 합 10,331). `ref_hs_whitelist` sha는 09-18 열 추가 전 값이나 DB 표 내용은 현행 CSV 24행·17열 전부 일치(행 해시) |
| `ref_country` | 238행 일치, 값은 DECIMAL(9,6) 패딩 표기 차이 52행(수치 대조 미수행) |
| alter 적용 실측 | `alter_2026-09-18_domestic_plan_budget_null` 적용됨(`budget_krw` NULL 허용), `alter_2026-09-19_krit_budget_clean` 적용됨(`clean_krit_task` 열·`clean_openfiscal_program_*` 존재) — 둘 다 `commands.md` 적용표에 없음. `alter_2026-09-20_country_count` 미적용(머리 주석과 일치) |
| 덤프 2개 | `db/dump_20260918_rds.sql`(295,204,037 B)·`_nodefiner.sql`(295,202,363 B) 모두 **팀 서버(192.168.100.x, 8.4.11) 원천, 2026-09-18 12:02 완료**, 표 44·뷰 31·루틴 0. `_nodefiner`는 DEFINER 절 31개를 빈 줄로 바꾼 것 외 diff 0. 현재 RDS 대비 표 14개 없음(P3·P4·KOSIS·열린재정 clean, `clean_excluded_row`, `ref_equipment_alias` 등), 덤프에만 있는 표 2(`clean_kdsis_nsn_ref`·`test_table`, 09-19 DROP), 덤프 내 빈 표 4(`clean_company`·`clean_company_name_link`·`clean_dapa_contract`·`clean_krit_task`), alter 15개 미반영 → **현재 DB 복구 수단이 아님**. 09-18 이후 RDS 역방향 덤프 기록 없음 |
| Google Drive | 64파일 중 61 MD5 일치(데이터 파일 전부), 불일치 3(`00_README/README.md`·`데이터_대응표.md`·`05_reference/country_ref.csv` — Drive가 구판), `team_budget_README`는 Drive에 없음 |
| 미확인 | AWS 자동 백업(보존 1일)·스냅샷 `defense-dashboard-pre-cutover-20260918` 존재 여부(문서 기록만), 팀 서버 현재 상태, new_data 원본의 팀 공유처 사본, 재생성 시험 |

## 3. 파일별 판정

판정: **A** 완전 중복·정리 승인 · **B** 별도 보관 후 분리 · **C** 재생성 가능·조건부 · **D** 구버전·미채택·추가 확인 · **E** 현재 사용·보존 · **F** 근거 부족·보류

| 경로 | 용량(B) | 용도 | 로컬 근거 | DB 대조 | 보존 사본·복구 수단 | 참조 영향 | 판정 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `data/drive_stage/01_customs/customs_all_*.csv` 21 | 29,857,819 | 09-14 드라이브 스테이징 사본 | SHA = `data/raw/customs/` 동일. Drive MD5 일치 | 원본 `raw_customs_trade` 21/21 파일 해시 일치 | `data/raw/customs/` + Drive | 코드 참조 0 | **A → 삭제** |
| `data/drive_stage/02_dapa/*.csv` 4 | 29,262,718 | 사본 | SHA = `data/raw/dapa/` 동일. Drive 일치 | 4표 해시 일치 | `data/raw/dapa/` + Drive | 0 | **A → 삭제** |
| `data/drive_stage/03_krit/` 9 | 14,864,797 | 사본 | SHA = `resource/krit/` 8(git)·`data/raw/krit/…_t7.csv` 동일. Drive 일치 | `raw_krit_task` 12파일 일치 | `resource/krit/`(git) + `data/raw/krit/` + Drive | 0 | **A → 삭제** |
| `data/drive_stage/99_verification/customs_*.csv` 21 + `progress.csv` | 17,304,694 | 검증용 부분집합 사본 | SHA = `data/raw/customs/` 동일. Drive 일치 | 원본 자체 미적재 | `data/raw/customs/` + Drive | 0 | **A → 삭제** |
| `data/drive_stage/04_aux/` 3 + `05_reference/country_ref.csv` | 37,625 | 사본 | SHA = `data/raw/dapa·kosis/`·`data/reference/` 동일 | 84 / 81 / 1,016 해시 일치, `ref_country` 238 | `data/raw/` + `data/reference/`(git) | 0 | **A → 삭제** |
| `data/drive_stage/05_reference/hs_whitelist.csv` | 3,042 | 구버전(21행·8열) | 현행 24행·17열. git `d1a1e27`~`d2cb4eb`에 21행판 존재. Drive 일치 | DB `ref_hs_whitelist` 24 = 현행 CSV | git + Drive | `data-cleaning-rules.md:285,366` 인용 | **D**(보존) |
| `data/drive_stage/99_verification/progress_all.csv` | 7,471 | 구버전(231행 ⊂ 264행) | 231행 전부 현행에 포함 | DB 264 = 현행 파일. DB `meta_dataset.customs_progress.sha256`은 이 파일 값 | Drive | `meta_dataset` 정정 필요 | **D**(보존) |
| `data/drive_stage/00_README/` 3 | 24,443 | 스테이징 설명·SHA 표 | §4 SHA 표 표본 3건 현행과 일치 | — | 로컬 유일 | `data-cleaning-rules.md:5` | **E** |
| `new_data/` 국외 조달계획·계약정보·입찰결과, 국내 조달계획, 군별 계약집행 `(1)` 5개 | 6,370,084 | 팀원 공유 원본 사본 | SHA = `data/raw/dapa/` 동일 | 5표 해시 일치 | `data/raw/dapa/`(로컬 유일, gitignore). 팀 공유처 사본 미확인 | 문서만 | **A → 삭제**(사용자 승인) |
| `new_data/방위사업청_국내조달 계약정보_20251231.csv` | 17,391,252 | 엑셀 재저장 손상본 | 계약번호 앞자리 0 소실 39행, 차수 `0`↔`00` 42,221행, 금액 지수표기 75셀 | DB는 `data/raw/dapa/` 원본과 일치 | 원본 `data/raw/dapa/` | `data-sources.md:62` 미사용 | **D** |
| `new_data/` 사전의향서(18,753)·입찰참여업체(176,021)·용어사전(420)·신기술(99)·국외 입찰공고(340) | 10,776,008 | 미채택 원본 | 파서 건수 문서와 일치. 코드 참조 0 | 미적재 | data.go.kr 재다운로드 가능(추론) | 문서만 | **D** |
| `new_data/raw_kdsis_nsn.csv` | 54,216,434 | 적재 원본(`load_db.py:125`) | SHA = DB `meta_dataset.sha256` | 228,027 해시 일치 | 로컬 유일 | 코드 입력 | **E** |
| `new_data/국방표준종합서비스2016.csv` | 10,961,634 | 합본 원천(55,335행) 증빙 | `alter_2026-09-17_kdsis_nsn.sql:5` | 직접 적재 없음 | 로컬 유일 | DB메타·문서 | **E** |
| `new_data/DLA_FSG_공식분류표.csv` | 16,477 | 구버전(77 ⊂ 80행) | 77행 전부 `fsg_master.csv`에 포함 | `ref_fsg` 80 | `data/reference/fsg_master.csv`(git) | 문서 | **D** |
| `docs/reference/clean-conversion-spec-2026-09-18.md` | 18,612 | 현행 기준 문서 | `CLAUDE.md:43`·노트북 5·alter 6 인용 | — | **없음**(gitignore) | 높음 | **E** + 조치(§5) |
| `new_data/데이터 정제 기준.md`, `기획서_양식_초안_2026-09-16.md` | 46,330 | 초안(후속본 `data-cleaning-rules.md`·`project-plan-2026-09-16.md`) | 후속 문서가 관계 명시 | — | 없음 | 문서 | **D**(이력 보존) |
| `new_data/PLAN_DRAFT_v7·v8.md`, `V8_정의_DB_CSV_근거설명.md`, `verification_summary.md` | 157,997 | 미채택 이력 | docs에 사본·후속 없음 | — | 없음 | v8은 `alter_2026-09-16_api_budget.sql:4` | **D**(보존) |
| `db/dump_20260918_rds_nodefiner.sql` | 295,202,363 | 덤프 변환본 | `_rds.sql`에서 DEFINER 제거만(diff 0). 재생성 명령 `aws-rds-setup.md:80` | 09-18 팀 서버 상태(§2) | `_rds.sql` | 0 | **C** |
| `db/dump_20260918_rds.sql` | 295,204,037 | 덤프 원본 | mysqldump 8.0.45, 09-18 12:02:56 | 위와 같음 | 없음(gitignore) | `aws-rds-setup.md:170` | **F**(신규 RDS 덤프 확보 전 보류) |
| `data/raw/customs/customs_<HS>.csv` 21 + `progress.csv` | 17,304,694 | 검증용 20개국 부분집합 | `fetch_customs.py` 기본 모드 출력. 읽는 코드 0. `csv-capability-map:48-54` | 미적재 | Drive `99_verification/`(MD5 일치) — drive_stage 사본 삭제 후 Drive가 유일 외부 사본 | 문서 | **B** |
| `data/raw/` 적재 원본 나머지 | ≈60 MB | 적재 원본 | 파서 건수 = expected = DB | 파일별 해시 일치(xlsx 2개 포함) | 훅 보호·gitignore. Drive에는 09-14분만 | 코드 입력 | **E** |
| `data/reference/` 11 | 84 KB | 기준표·앱 입력(`semi_*.csv` 6개는 `app/pages/4_…:59`) | `contract_class5_rules_alt.csv`는 문서 참조만 | `ref_hs_whitelist`·`ref_country` 일치 | git | 높음 | **E** |
| `data/derived/` 9 | 762 KB | 팀 수작업 산출물 | 코드 참조 0, 재생성 코드 없음 | — | git | 문서 | **E** |
| `resource/drive/` 6 · `resource/krit/` 8 | 21 MB | 증빙·`parse_krit.py`/`extract_drive_docs.py` 입력 | git | — | git + Drive(03_krit) | 코드 입력 | **E** |
| `db/query_p4_ko_views.sql` | 10 KB | 탐색 SQL | 참조 0 | — | git | 0 | **F** |
| `db/` 그 외 | ≈600 KB | 스키마·이력·사전 | — | alter 적용 §2 | git | 높음 | **E** |

## 4. 정리 실행 기록 (A 목록, 사용자 승인 2026-09-20)

- 절차: 후보·보존 사본의 존재와 SHA-256을 실행 직전 재계산해 일치한 것만 `os.remove`로 개별 삭제(와일드카드·재귀 삭제 없음). dry-run 65/65 일치 확인 후 실행.
- 결과: **65개 삭제, 97,697,737 B(93.17 MiB) 확보**, 중단 0. 비워진 폴더 `01_customs`·`02_dapa`·`03_krit`·`04_aux` 4개 제거(`rmdir`, 빈 폴더만).
- 삭제 후 보존 사본 재확인: `data/raw/dapa/dapa_domestic_plan_20251231.csv` `cae19fb6…`, `data/raw/customs/customs_all_841191.csv` `3f3b2249…`, `resource/krit/23-4차_주관기업모집_공고문.pdf` `1af28aee…`, `data/reference/country_ref.csv` `be7f3db1…` — 변경 없음.
- 남은 파일: `data/drive_stage/` 5개(README 3·`hs_whitelist.csv` 21행·`progress_all.csv` 231행, 60 KB), `new_data/` 19개(CSV 9·md 7·`raw_kdsis_nsn.csv` 포함, 90 MB). DB·AWS·코드·문서(이 파일 외)는 바꾸지 않았다.
- 참조 영향: 삭제 파일을 읽는 코드·설정은 없었고, 문서 인용은 `data/drive_stage/00_README/README.md`(자기 폴더 설명)와 `docs/reference/data-cleaning-rules.md:5`(README 인용)뿐 — README는 남겨 두었으므로 끊어진 인용 없음.

## 5. 후속 조치 상태 (2026-09-20 밤)

| # | 항목 | 상태 |
| --- | --- | --- |
| 1 | RDS 역방향 덤프 | **완료** — `db/dump_20260920_rds.sql` 329,329,574 B(표 56·뷰 31·INSERT 355줄, DEFINER `admin@%` 31개, exit 0, 43초). `aws-rds-setup.md` 진행 기록에 반영. gitignore 대상 |
| 2 | `meta_dataset` 해시 정정 | **완료** — `db/alter_2026-09-20_meta_dataset_sha.sql`(UPDATE 3문, 멱등)을 사용자가 `apply_alter.py`로 적용(rows=1×3), DBHub 실측 일치. 2026-09-21 `db/meta_dataset.csv`의 빈 `sha256`·`file_bytes` 15행을 RDS 값으로 채움(로컬 파일 해시 15개 모두 RDS와 일치 확인, 남은 차이는 `ref_hs_whitelist.updated_on` CSV 09-16 vs RDS 09-15). `db/meta_dataset.csv`의 `customs_region` 행은 tier `보조`로 고치고 note에 "RDS 미적재·이 PC에 파일 없음" 명시 |
| 3 | 문서·경로 | **부분 완료** — `commands.md` 적용표에 alter 3행 추가, `data-cleaning-rules.md` 드라이브 구판 문구 갱신, `CLAUDE.md` drive_stage 표기, drive_stage README에 정리 사실 기재. **완료(2026-09-21)**: gitignore였던 담당분배 명세를 `docs/reference/clean-conversion-spec-2026-09-18.md`로 옮기고(담당 이름 열 제거) 인용 경로 17곳 갱신 |
| 4 | 환경 | **완료** — `.venv`에 `openpyxl==3.1.5` 재설치(`INSTALLED.md` 기록), xlsx 2표 내용 대조 완료. `db/reset_data.sql`은 2026-09-21 `schema.sql` DROP 목록과 1:1로 갱신(TRUNCATE 45표 = clean 20·fact/dim 2·raw 22·meta_load_log, ref 9·meta_dataset·meta_column_dict 보존, RDS 미실행) |
| 5 | 팀 결정 | **대기** — 조장의 개인 저장소 `kimhh080888-blip/Defense_Dashboard` 직접 push는 의도된 것(2026-09-21 사용자 확인: 그 저장소 `main`은 Claude를 쓰지 않는 팀원용 공개본). `raw_kosis_production_index` `stat_ym='p)'` 16행은 원본 동결 원칙대로 두고 clean이 월을 복원한 상태(`load_db.py frame_kosis_wide2` docstring) — 재적재(TRUNCATE 후 `load_db.py --raw --tables raw_kosis_production_index`, admin)는 사용자 판단. D(손상본 17.4 MB·미채택 CSV 10.3 MB·구버전 소파일), C(`dump_20260918_rds_nodefiner.sql` 281.5 MiB는 2026-09-21 사용자 승인으로 삭제 완료 — 원본 `_rds.sql`과 DEFINER 제거 외 diff 0, 필요 시 `aws-rds-setup.md:80` 명령으로 재생성. 원본 `_rds.sql` 1개는 이력으로 남길지 미결), B(검증용 관세청 20개국 CSV 21개 폴더 밖 보관) |
| 6 | 보안 그룹 | `211.217.244.4/32`는 `aws-rds-setup.md:189`에 자취방 상시 규칙으로 기록됨(임시 아님). 카페 임시 규칙 `121.158.146.147/32`의 삭제 여부는 `rds-access-registry.md` 기준으로 확인 필요 |
