# 실행 명령

모두 저장소 루트에서 실행한다. 린터는 없다. 테스트는 `tests/`(unittest, DB 불필요 — 실행 명령은 §10 앱 공통 계층 항목).

## 1. 관세청 수출입 OpenAPI 수집

`.env`의 `DATA_GO_KR_SERVICE_KEY`가 필요하다.

```bash
python scripts/fetch_customs.py --sample                      # US × 854231 × 2025 → 12행 확인
python scripts/fetch_customs.py --all-countries               # 확정 원본: cntyCd 생략 → HS×연도당 1호출로 전체 국가(231회) → customs_all_<HS>.csv, progress_all.csv
python scripts/fetch_customs.py                               # 국가 지정(기본 20개) 수집 → customs_<HS>.csv, progress.csv (검증용 부분집합)
python scripts/fetch_customs.py --years 2024 2025 --countries US CN JP --hs 854231
```

- 대상 HS 코드는 `data/reference/hs_whitelist.csv`에서 읽는다.
- 출력 경로: `data/raw/customs/`
- `--all-countries` 결과(`customs_all_*.csv`)가 확정 원본이다. 기본 실행 결과(`customs_*.csv`)는 검증용 부분집합이며 원본 건수로 쓰지 않는다.

## 2. KRIT 부품국산화 공고 표 추출 (hwpx · pdf · hwp)

```bash
python scripts/parse_krit.py resource/krit/<공고>.hwp                    # 표 목록·크기 확인(hwp/hwpx는 문서 내 번호)
python scripts/parse_krit.py resource/krit/<공고>.hwp --table 8          # 8번째 표 화면 출력
python scripts/parse_krit.py resource/krit/<공고>.pdf --page 3 --table 2 # pdf는 쪽 안 번호
python scripts/parse_krit.py resource/krit/*.pdf resource/krit/*.hwp --out data/raw/krit   # SPEC 표만 CSV 저장
python scripts/parse_krit.py <파일> --out <임시경로> --all               # SPEC 무시, 모든 표(양식 포함) 저장
```

- (2026-09-18) 형식 3종 지원. pdf는 `pdfplumber`(단어 시작 x·세로 중심으로 셀 배정 — 병합 오판·경계 넘침 보정), hwp 5.0은 `olefile`로 BodyText 레코드를 직접 읽는다(암호화·배포용 문서 미지원). 어느 표가 과제표인지는 스크립트 상단 `SPEC`(파일명 → 쪽·표 번호·사업 구분)에 적어 두었고 근거는 `docs/data-sources.md` KRIT 절이다. 새 공고를 받으면 `--table`로 훑어 과제표 번호를 찾고 `SPEC`에 추가한 뒤 `--out data/raw/krit`.
- 저장 규칙: 헤더는 원문 그대로(단위가 헤더에 있음), 본문 셀 줄바꿈은 공백, `담당자`가 든 열은 저장하지 않음(개인정보), 표 제목의 사업 구분은 마지막 열 `구분(표제목)`. 파일명은 hwp/hwpx `<stem>_t<N>.csv`, pdf `<stem>_p<쪽>_t<N>.csv`.
- 25-1차 수정공고문은 1쪽 수정사항표(2·14·15·16번)와 본문 표를 대조한 로그를 함께 출력한다(2026-09-18: 4건 모두 일치 — 본문이 수정본).
- 적재(2026-09-22부터 DB raw_ 표 없음): `python scripts/load_db.py --dry-run --tables raw_krit_task`(기대 96행)로 파서 대조 후 `notebooks/clean_p5_krit_p2_budget.ipynb`가 `read_raw`로 읽어 `clean_krit_task`를 채운다. `frame_krit`이 파일명 토큰으로 `notice_type`(예비RFP·예비공고→예비 / 수정공고→수정 / 재공고 / 공고문→본공고)을 채우고, 차수별 다른 헤더는 `KRIT_HEADER_ALIAS`로 공통 5열에 잇되 원래 헤더를 `extra_json["원본열명"]`에 남긴다. 파일을 더하면 `RAW_TABLES['raw_krit_task'].expected`를 올리고 `clean_krit_task`를 TRUNCATE 한 뒤 노트북을 재실행한다(파서 순번이 바뀔 수 있으므로 전체 재적재).

## 3. 강사 안내 자료 텍스트 재생성

`resource/drive/` → `docs/drive-text/*.txt`

```bash
python scripts/extract_drive_docs.py
```

## 4. DB 스키마 적용 (`db/schema.sql`)

설계는 `docs/db/schema-design.md`. DDL은 전체 DROP 후 재생성(수작업 대응표·`meta_` 기록까지 삭제)이므로 **최초 구축·빈 개발 DB 초기화 전용**. 적재된 데이터가 있는 서버에서는 실행 전 덤프(`db-connection.md` §5). 데이터만 비우고 다시 적재할 때는 `db/reset_data.sql`(§5 재적재 3모드).

**운영 DB는 2026-09-18부터 AWS RDS**(`db-connection.md`)다. 아래 `mariadb.exe` 명령은 폐기된 내부망 팀 서버에 재현할 때만 쓰고, 운영 DB에는 다음 명령을 쓴다(`.env`의 `MARIADB_HOST`·`MARIADB_ADMIN_*`; DDL·reset·계정 관리는 `admin`, 적재는 `etl_rw`):

```powershell
# RDS(운영). MySQL 8.0 클라이언트 + TLS 필수. 비밀번호는 .env MARIADB_ADMIN_PASSWORD 를 PowerShell 변수로 읽어 넘긴다(화면 출력 금지)
$env:MYSQL_PWD = ((Get-Content .env | Where-Object { $_ -match '^MARIADB_ADMIN_PASSWORD=' }) -replace '^MARIADB_ADMIN_PASSWORD=','')
$h = ((Get-Content .env | Where-Object { $_ -match '^MARIADB_HOST=' }) -replace '^MARIADB_HOST=','')
cmd /c "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`" -h $h -P 3306 -u admin --protocol=TCP --ssl-mode=REQUIRED --default-character-set=utf8mb4 --show-warnings --table defense_dashboard < db\alter_YYYY-MM-DD_topic.sql"
```

**팀 서버 적용 완료(2026-09-15)** — MySQL 8.4.11, 테이블 31 + 뷰 6, FK 12, 오류 0(`schema-change-log.md` §6). **데이터가 있는 DB에서 다시 실행하면 안전장치가 DROP 전에 오류(`ERROR 1146 … stop_schema_sql_db_has_data …`)로 멈춘다** — 강제 초기화는 덤프 후 파일 앞 안전장치 블록을 지우고 실행. 이 PC에는 `mysql` CLI가 없어 MariaDB 12.2 클라이언트를 쓴다. 비밀번호는 `MYSQL_PWD` 환경변수로 넘기고(`--password=`를 주면 12.x 클라이언트가 서버 인증서 검증을 켜서 MySQL 자체서명 인증서에 `ERROR 2026`이 난다), `--skip-ssl-verify-server-cert`를 붙인다.

```powershell
# 팀 DB(AWS RDS). .env 의 MARIADB_* 값 사용. PowerShell 에서:
$env:MYSQL_PWD = "<MARIADB_PASSWORD>"
cmd /c '"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" -h <RDS_ENDPOINT> -P 3306 -u <MARIADB_USER> --protocol=TCP --default-character-set=utf8mb4 --show-warnings defense_dashboard < db\schema.sql'
# 확인(2026-09-15 당시): 테이블 31(+ 조장의 test_table) + 뷰 6 — 2026-09-18 테이블 48(+test_table) + 뷰 31 — 2026-09-19 RDS 실측 BASE TABLE 56 + 뷰 31(test_table·clean_kdsis_nsn_ref는 alter_2026-09-19_drop_unused.sql로 삭제)
cmd /c '"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" -h <RDS_ENDPOINT> -P 3306 -u <MARIADB_USER> --protocol=TCP defense_dashboard -e "SHOW FULL TABLES"'

# 데이터 계층만 비우기(ref_ 10·meta_dataset·meta_column_dict 보존, 25표 TRUNCATE — 목록은 schema.sql DROP과 1:1, 2026-09-22 raw_ 계층 제거 반영). clean_ 22 → fact_/dim_ 2 → meta_load_log 순. RDS는 admin 계정으로
cmd /c '"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" ... defense_dashboard < db\reset_data.sql'
```

### 증분 변경 (`db/alter_*.sql`) — 적재된 서버에 스키마를 더할 때

`schema.sql`은 전체 DROP이라 적재된 서버에 못 돌린다. 열·테이블·뷰를 더할 때는 `db/alter_<날짜>_<주제>.sql`을 만들어 같은 `mariadb.exe` 방식으로 실행하고, `schema.sql`에도 같은 정의를 반영해 둘을 일치시킨다. DBHub MCP는 `readonly`라 ALTER·UPDATE가 안 된다(`READONLY_VIOLATION`) — **2026-09-22부터 DBHub는 RDS를 본다**(그전에는 구 내부망 팀 서버였다. `~/.claude/dbhub.toml`, 종전 설정은 `dbhub.toml.team-backup`). 계정은 RDS에서는 `.env`의 `MARIADB_USER`(이 맥 `dev_taeho`, DDL 권한 있음 — admin은 이 맥에 미설정이라 `apply_alter.apply`에 `etl` 커넥션을 넘겨 쓴다), 팀 서버 재현 때는 `defense`(ALL PRIVILEGES — `mariadb-remote-setup.md` §6-1)를 쓴다.

| 파일 | 내용 | 적용 |
|---|---|---|
| `db/alter_2026-09-15_civil_mix.sql` | `ref_hs_whitelist.civil_mix` 추가(팀 판단 라벨) | 2026-09-16 적용, 같은 날 아래로 대체. 파일은 2026-09-17 삭제(git 이력) |
| `db/alter_2026-09-16_indicator.sql` | `ref_hs_indicator`·`raw_hsk_control`·뷰 3개(`v_hs10_use_share`·`v_defense_relevance_b2`·`v_civil_mix_rule`)·`civil_mix` 3열 + 지표 채우기 + `civil_mix` 규칙값 UPDATE | 2026-09-16 적용(2회 실행 확인) |
| `db/alter_2026-09-16_fsg.sql` | FSG 2자리 참조표 `ref_fsg`(80행 정적 시드) + `v_b2_fsg_summary` + 열 사전 8행 + `meta_dataset` `fsg_master` | **2026-09-16 적용**(팀 서버 3회 실행, 멱등. 기대: `ref_fsg` 80 · historical 2 · electronic 2 / `v_b2_fsg_summary` 53 16,300 · 59 2,942 · 58 379 / 미대응 `0`·NULL 18행 / `meta_column_dict` 289) |
| `db/alter_2026-09-17_view_collation.sql` | 뷰 15개를 `SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci` 세션에서 정의 변경 없이 재생성. 팀 서버(MySQL 8.4) 뷰가 `utf8mb4_0900_ai_ci`로 만들어져 `WHERE b1_status='미적재'` 같은 상태 열 비교가 `ERROR 1267 Illegal mix of collations`로 실패하던 문제 | **2026-09-17 적용**(exit 0, `information_schema.VIEWS` 15개 전부 `utf8mb4_unicode_ci`, 데이터 294,420행 보존). **앞으로 뷰를 만드는 alter는 머리에 같은 SET NAMES를 둔다** |
| ~~`db/alter_2026-09-17_category_map.sql`~~ | 품목군 대응표 확정 14 + 신규 1 + 대응불가 3 (초안) | **2026-09-18 폐기 — FSC↔HS 근거 없음(팀 결정), 파일 삭제(git 이력 `26d2672` 이전)**. 결정 기록 `docs/report/data/category-map-decision-2026-09-17.md` 머리 절 |
| `db/alter_2026-09-18_r4_provisional.sql` | 대응표 미확정 결정 반영: R3∧R4로만 진입한 HS6 6개 `evidence_note`에 "R4 잠정" 사유 추가, `v_review_list.b2_status` 라벨 `대응 미확정`→`대응표 없음`. 표·행 수 불변, 멱등 | **2026-09-18 적용**(exit 0, `evidence_note` 잠정 6행 · `v_review_list` 2025 `대응표 없음` 24 · `ref_category_map` 후보 17 · 뷰 콜레이션 unicode_ci · `ref_hs_rule_flag` r4 14 불변) |
| `db/alter_2026-09-16_api_budget.sql` | 팀 드라이브 채택 3종: `raw_dapa_overseas_plan_api`(국외 조달계획 OpenAPI 품목 단위 13,615)·`raw_dapa_fsc_catalog`(군급분류집 756)·`raw_openfiscal_program_budget`(열린재정 12파일 2,860) + `ref_fsc` 열 보강·시드(§3, raw 적재 후 **다시 실행**해야 676행) + 뷰 `v_overseas_plan_api_fsc`·`v_budget_rnd_yearly` + 열 사전 48행 + `meta_dataset` 3행 | **2026-09-16 적용**(2회 실행, exit 0. 기대: 3표 `--verify` 일치 · `ref_fsc` 676/전자군 46/폐지 22 · 뷰 합 9,970/전자군 1,819 · 예산 뷰 2020 10,053.3 → 2027 30,741.4 정부안 · `meta_column_dict` 337) |
| `db/alter_2026-09-17_kdsis_nsn.sql` | 국방표준종합서비스(KDSIS) NSN 목록 보조 조회용: `raw_kdsis_nsn`(228,027) + 파생 `clean_kdsis_nsn`(NSN별 1행 135,864)·`clean_kdsis_nsn_ref`(NSN×CAGE×참조번호 225,635 — **2026-09-19 삭제됨**, `alter_2026-09-19_drop_unused.sql`, 사유 `docs/db/report-views.md` §3) + 뷰 3(`v_overseas_plan_api_kdsis`·`v_b2_localized_kdsis`·`v_kdsis_link_summary`) + 열 사전 51행 + `meta_dataset` `kdsis_nsn` + 로그 2행. 원본은 `new_data/raw_kdsis_nsn.csv`(팀원 정리본, 2016 CSV 포함) | **2026-09-17 적용**(1차 표·뷰 → `load_db.py --raw --tables raw_kdsis_nsn` 89.6s → 2차 clean 채움. 기대: raw 228,027 · 숫자13 135,331 · 검토 533 · 속성 충돌 0 · ref 225,635 · `meta_column_dict` 388 · 기존 뷰 집계 불변 확인) |
| `db/alter_2026-09-17_procurement_aux.sql` | 국내 축 확장 뷰 9개: 조달 보조 6종(`raw_dapa_domestic_plan`·`bid_notice`·`bid_result`·`overseas_contract`·`overseas_bid_result`·`defense_company`) raw 직접 집계 + 계약정보 수의계약 사유(`v_contract_private_reason`·`v_contract_reason_group_yearly`). `CREATE OR REPLACE VIEW`만 있어 데이터·표를 건드리지 않음. FSC·HS6 축 아님 | **2026-09-17 적용**(1회, exit 0, 뷰 29개 전부 `utf8mb4_unicode_ci`). 기대값은 파일 §10(계약 37,608 · 수의 그룹 경쟁실패 1,847·단일공급 747 · 유찰 키 1,741 · 공고 10,840 · 국외 사슬 1,362/97 · 국내 계획 2025 8.558조 등). 재실행 가능 |
| `db/alter_2026-09-17_export.sql` | 수출 축 동등 배치(2026-09-17 팀 결정): `v_export_share_hs6_year`·`v_hhi_export_hs6_year`(수입 뷰와 같은 구조, `exp_dlr` 기준). `CREATE OR REPLACE VIEW`만, 표·데이터 불변 | **2026-09-17 적용**(exit 0, 뷰 31개, 두 뷰 `utf8mb4_unicode_ci`. 확인: 2025 수출 HHI 854231 1,788(CN 26.9%) · 854239 1,945(TW 26.2%) · 852990 5,038(CN 69.3%)) |
| `db/alter_2026-09-18_meta_dataset.sql` | `meta_dataset` UPDATE 2문(표·뷰 변경 없음): 관세청 `customs_all`·`customs_progress` `published_on` 2022-05-25·`updated_on` 2026-05-22(포털 확인), `dapa_contract` `is_partial_period` 1(2024는 11~12월만 12,304행). 멱등 | **2026-09-18 적용**(exit 0, `db/meta_dataset.csv`와 일치) |
| `db/alter_2026-09-16_hs_rule.sql` | HS6 선정 규칙: `raw_hs_code_master`·`raw_hs_unit_name`·`ref_hs_rule_flag`(R1~R4 스냅샷)·뷰 5개(`v_hs10_use_tag_all`·`v_hsk_control_by_hs6`·`v_hs6_candidate_rule`·`v_hs6_candidate_vs_whitelist`·`v_hs_whitelist_rule`)·`ref_hs_whitelist` `evidence_basis`·`evidence_note` + 열 사전. §5는 정적 UPDATE(rule 16)·강등(5)·INSERT(신규 3) — 적재 전 실행 가능. §5-4 `ref_hs_rule_flag` 스냅샷은 원본 3개 적재 후 **다시 한 번 실행**해야 1,003행이 채워짐(미적재면 0행) | **2026-09-16 적용**(팀 서버 2회 — 1차 ALTER·뷰·§5 정적값, 원본 3개 적재 후 2차에서 §5-4 스냅샷 1,003행. MySQL 8.4에서 `group_concat_max_len` 오류 1260 → 스크립트가 세션 한도를 올림) |
| `db/alter_2026-09-18_p4_clean.sql` | P4 국내조달 clean 4표(`clean_dapa_bid_notice`·`clean_dapa_bid_result`·`clean_dapa_domestic_plan`·`clean_dapa_contract_exec_by_service`) + 전 담당 공용 `clean_excluded_row` DDL(0행) + 열 사전 101행. 콜레이션 `utf8mb4_unicode_ci` 명시 | **2026-09-18 적용**(1차에서 5표가 0900_ai_ci로 생성돼 CONVERT TO로 바로잡음. 기대: clean 13표 · `meta_column_dict` 489 · FK 4). 적재는 9/22~ P4 노트북, 검산은 파일 §7 |
| `db/alter_2026-09-18_column_dict_gap.sql` | 열 사전 공백 4표 보충: `clean_dapa_contract`(40)·`clean_company`(6)·`clean_company_name_link`(8)·`ref_sido_map`(3) = 57행을 `meta_column_dict`에 INSERT(테이블 구조 변경 없음) | **2026-09-18 적용**(`scripts/apply_alter.py --twice`, 2회 exit 0, 경고는 deprecated `VALUES()` 1287뿐. RDS `meta_column_dict` 489 → 546, 4표 40/6/8/3, 열 사전 ↔ DB 열 누락 0. 사전 검증: 로컬 MariaDB 12.2 스크래치 3307에서 동일 결과) |
| `db/alter_2026-09-18_bid_result_dup_kind.sql` | `clean_dapa_bid_result.dup_kind` ENUM에 `동일 결과 반복` 추가(0행 표, 데이터 영향 없음) + 열 사전 설명 갱신. 근거: 중복 199키 재집계 73·108·18(`schema-change-log.md` §7-23) | **2026-09-18 적용**(`scripts/apply_alter.py --twice`, exit 0. COLUMN_TYPE 5값 확인, `meta_column_dict` 546 유지) |
| `db/alter_2026-09-19_column_dict_11tables.sql` | 열 사전 미등재 11표 보충: `clean_dapa_localized_item`(15)·`clean_dapa_overseas_plan`(17)·`clean_krit_task`(16)·`dim_hs10`(3)·`fact_customs_monthly`(13)·`meta_column_dict`(6)·`meta_dataset`(23)·`meta_load_log`(10)·`ref_category_map`(10)·`ref_fsc`(6)·`ref_hs_indicator`(16) = 135행 INSERT + `meta_column_dict.dtype` VARCHAR(50)→(100)(`meta_load_log.stage` ENUM 표기 55자) | **2026-09-19 적용**(`scripts/apply_alter.py --twice` 후 dtype 확장 재실행, exit 0. 1차에 1265 dtype 잘림 1건 → 확장 후 재INSERT로 해소. RDS `meta_column_dict` 546 → 681 = 48표 전부, 미등재 BASE TABLE은 `test_table`만(2026-09-19 삭제됨, 아래 `drop_unused`). 경고는 deprecated `VALUES()` 1287뿐) |
| `db/alter_2026-09-19_p3_clean.sql` | P3 국외조달 clean 3표(`clean_dapa_overseas_plan_api`·`clean_dapa_overseas_contract`·`clean_dapa_overseas_bid_result`) + 표기 통일 사전 `ref_equipment_alias` DDL(0행) + `ref_fsg`/`ref_fsc` FSG 60 전자 플래그 0→1(조건부 UPDATE) + 열 사전 82행 | **2026-09-19 적용**(`python scripts/apply_alter.py --twice db/alter_2026-09-19_p3_clean.sql`, 2회 exit 0. 기대: 표 4개 · `meta_column_dict` +82 · `ref_fsg` 60=1 · `ref_fsc` fsc2='60' 24행 전부 1 · 콜레이션 `utf8mb4_unicode_ci`. 1차 적재 때 `ref_equipment_alias.name_raw`가 기본 콜레이션이라 PK 충돌(1062) → 파일에 `utf8mb4_bin` + `ALTER … MODIFY` 반영 후 재적용). 적재는 `notebooks/clean_p3_overseas.ipynb` |
| `db/alter_2026-09-19_p1_customs_hs.sql` | P1 관세청 수입 축: `dim_hs10` 현행 마스터 열 4개(`master_name_ko`·`apply_start`·`apply_end`·`master_link_status`) + `clean_hsk_control` 신설(HSK 연계표 세로형, 0행) + `ref_hs_rule_flag.hs6_name_src` + `ref_hs_indicator` `hsk_control_hs10_ratio`·`hsk_control_imp_share` 각 24행 + 열 사전 21행 신규·8행 설명 정정(금액 단위) | **2026-09-19 적용**(`python scripts/apply_alter.py --twice db/alter_2026-09-19_p1_customs_hs.sql`, 2회 exit 0. 실측: `meta_column_dict` 806 → **827**, `ref_hs_indicator` 41 → **89**, `dim_hs10` 7열, `v_hs6_candidate_vs_whitelist` verdict 분포 **전후 동일**(유지 19 / 신규 후보 39 / 강등·제외 5), `v_civil_mix_rule` basis 판단불가 15 → hsk 15(라벨은 NULL 유지). 경고는 deprecated `VALUES()` 1287뿐). 적재는 `notebooks/clean_p1_customs_hs.ipynb` |
| `db/alter_2026-09-19_kosis_clean.sql` | P5-5 KOSIS 2종 clean 세로형 신설(0행): `clean_kosis_utilization`(10열, raw 1:1 81 기대) · `clean_kosis_production_index`(16열, raw 1:1 1,016 기대, `stat_month` DATE·`is_provisional`·`scope_grade` ENUM ★/▲/✕·`is_month_restored`) + 열 사전 26행. raw `stat_ym='p)'` 결함 16행의 월 복원 규칙(`source_col_no`)은 파일 머리 주석 | **2026-09-19 적용 완료**(`python scripts/apply_alter.py --twice db/alter_2026-09-19_kosis_clean.sql`, 2회 exit 0. 작성 시점에는 이 PC 공인 IP 변경으로 보안 그룹에 막혀 지연 — `schema-change-log.md` §7-29). 실측: 표 2개 생성(콜레이션 `utf8mb4_unicode_ci`), 열 사전 +26. 적재 결과는 §6 `clean_p5_kosis.ipynb` 행 |
| `db/alter_2026-09-19_views_to_clean.sql` | raw 직독 뷰 14개를 clean 기준으로 전환(`CREATE OR REPLACE VIEW` 15문 = 14 + `v_kdsis_link_summary` raw 행 기준 열 3개 추가) + clean 열 2개 조건부 추가·백필(`clean_dapa_contract.private_contract_reason` ← raw 원문, `clean_dapa_domestic_plan.is_budget_approx` ← raw 지수 표기 11행) + 열 사전 2행. `v_defense_company_sector`는 clean 없음이라 제외. 의미 변경(전자 58·59·60, NSN 모집단 13,236, B2 kdsis 고유 부품 기준, `demand_org_count` 삭제)은 파일 §3 주석·`schema-change-log.md` §7-27. `SEPARATOR ';'`는 `0x3B`로 씀(apply_alter.py 세미콜론 분리 제약) | **2026-09-19 적용 완료**(`python scripts/apply_alter.py --twice db/alter_2026-09-19_views_to_clean.sql`, 2회 exit 0 — 1회차 백필 `private_contract_reason` 30,246행·`is_budget_approx` 11행, 2회차 0행. 사전에 로컬 MariaDB 12.2 스크래치(3307)에서 문법·멱등·열 위치 검증). 전후 스냅샷 실측(`schema-change-log.md` §6): 예상 외 변화 0 — 바뀐 것은 `v_b2_fsg_summary` 58→57행, `v_b2_localized_kdsis` 33,965→25,025행·연결 449→310, `v_kdsis_link_summary` matched 1,065→926·eligible 31,531→26,868, `v_overseas_plan_api_fsc` 2,321→2,566행·모집단 9,970→13,236·전자 1,819→2,267, `v_bid_notice_result_link` 키 7,201→7,199·낙찰업체 3,210→3,209, `v_overseas_contract_yearly` `demand_org_count` 삭제뿐. 뷰 31개 전부 `utf8mb4_unicode_ci`, `v_hs6_candidate_vs_whitelist` 39/19/5 불변 |
| `db/alter_2026-09-19_drop_unused.sql` | 미사용 테이블 2개 DROP: `clean_kdsis_nsn_ref`(225,635 — 뷰·앱·노트북 참조 0)·`test_table`(4, 사용자 임시 표) + `meta_column_dict`에서 `clean_kdsis_nsn_ref` 6행 DELETE. `meta_load_log` 이력은 유지. 후보 선정·사유는 `docs/db/report-views.md` §3, 되돌리기는 `alter_2026-09-17_kdsis_nsn.sql` INSERT…SELECT | **2026-09-19 적용 완료**(`python scripts/apply_alter.py --twice db/alter_2026-09-19_drop_unused.sql`, 2회 exit 0. 기대·실측 일치: 표 2개 삭제 → RDS BASE TABLE **56**(= `schema.sql` 정의 표 전부) + 뷰 31, `meta_column_dict` 855 → **849**(−6, `db/column_dict.csv`도 849)) |
| `db/alter_2026-09-18_sido_gwangju.sql` | (조장 작성, P2 검수 `docs/report/data/ref-review-p2-2026-09-18.md` §3) `ref_sido_map` 토큰 `광주`·`광주시` DELETE(경기 광주시와 겹침 — 정제 코드가 둘째 토큰으로 29/41 판별) + `충남대전시`→30 INSERT. 45→44행. `db/seed_ref.sql`도 같은 내용 | **2026-09-19 저녁 적용**(`python scripts/apply_alter.py --twice`, 1회차 DELETE 2·INSERT 1, 2회차 0·0(1062 경고 = IGNORE), exit 0). DBHub 실측 44행·광주 토큰 0·충남대전시=30. 파일 주석의 "clean_dapa_contract 0행이라 재계산 대상 없음"은 작성 시점(09-18) 기준 — 실제로는 09-19 적재분 43,111행이 있어 아래 alter로 백필 |
| `db/alter_2026-09-20_p3_test_vendor.sql` | P3 검수 회신(09-20) 반영: `clean_dapa_overseas_contract`에서 대표업체명 `TEST2` 테스트 계약 6행(`raw_row_id` 202·203·709·713·1558·1559 명시) `clean_excluded_row` PLACEHOLDER 기록·DELETE + `meta_load_log` 「검증된 분석 대상」 1행(6,327). 키워드 TEST/테스트로는 거르지 않음(실제 계약 19행). 판정 근거 `docs/report/data/p3-review-response-2026-09-20.md` | **2026-09-20 적용**(`--twice`, 1회차 rows 6·6·1, 2회차 전부 0, exit 0). DBHub 실측: 6,333 = 6,327 + 6(gap 0), `v_overseas_contract_yearly` 2017 703·2018 850·2019 824, 고유 업체 442, `meta_load_log` 130 |
| `db/alter_2026-09-19_sido_backfill_test_vendor.sql` | P2 검수 반영 ②③: `clean_dapa_contract`·`clean_company` `sido_code` 백필(`충남대전시`→30) + 테스트 업체 6행(`조달테스트업체Ⅰ` 2·`테스트업체1` 4, `raw_row_id` 명시) `clean_excluded_row` PLACEHOLDER 기록·DELETE + `clean_company` 테스트 업체 2행 DELETE(다른 clean 행·`name_link` 참조 0 조건) + `meta_column_dict` `ref_sido_map.token` 설명 45→44행 | **2026-09-19 저녁 적용**(`--twice`, 1회차 rows 16·1·6·6·2·1, 2회차 전부 0, exit 0). DBHub 실측: `clean_dapa_contract` 43,105·`sido_code` NULL 2(`**`·`1`)·`is_latest_seq=1` 37,602 = 계약번호 수·위반 0, `clean_excluded_row` 11(KEY_CONFLICT 1·COL_SHIFT 4·PLACEHOLDER 6), 검산 raw 43,112 = 43,105 + 7(5표 gap 0), `clean_company` 14,836·NULL 2, 사전 849. 노트북 셀 2·4 규칙(광주 둘째 토큰·테스트 업체 정확 일치 제외)과 SQL 동치 확인: 계약 43,105·낙찰 5,275 불일치 0 |
| `db/alter_2026-09-20_null_vocab.sql` | 결측 어휘 확정(팀 결정 2026-09-20, `null-profile-2026-09-19.md` §2 제안 그대로 + 예외 38행 「미기재」): §1 `clean_kdsis_nsn.niin` 빈 문자열 3행 → NULL + COMMENT · §2 집계 뷰 4개 `CREATE OR REPLACE`(`v_contract_monthly`·`v_contract_private_reason`·`v_bid_notice_monthly`·`v_domestic_plan_yearly`에 `*_missing_count` 열, `v_bid_notice_monthly` `COALESCE(…,0)` 제거, `v_contract_private_reason` `reason_group`에 `해당 없음(경쟁계약)` 분리) · §3 `meta_column_dict` 85행 `INSERT … ON DUPLICATE KEY UPDATE`(77열 결측 판정·화면 어휘·집계 처리 + CSV↔RDS 불일치 8행 정정, `related_fsc`의 `;`는 `CHAR(59 USING utf8mb4)`) · §4 검증 SQL. `db/schema.sql` 뷰 4개·niin 주석, `db/alter_2026-09-17_kdsis_nsn.sql` L130 `NULLIF` 동기 | **2026-09-20 적용 완료**(`python scripts/apply_alter.py --twice db/alter_2026-09-20_null_vocab.sql`, 24문 × 2회 exit 0, 2회차 변경 0, 경고는 deprecated `VALUES()` 1287뿐). DBHub 실측: niin `''` 0·NULL 3 / 뷰 열 수 7·6·8·8 / `v_bid_notice_monthly` 538행·미기재 합 596·전 행 NULL 그룹 46(0→NULL)·예산 합 불변 / `v_contract_monthly` 28·37,602·미기재 1 / `v_domestic_plan_yearly` 62·35,859·4,965 / `v_contract_private_reason` 144행, `해당 없음(경쟁계약)` 10,734·`사유 미기재` 9·나머지 8그룹 불변 / `v_contract_reason_group_yearly` 18→20 / `meta_column_dict` 849, `db/column_dict.csv`와 6필드 전체 diff 0(스크래치 `verify_dict.py`) |
| `db/alter_2026-09-18_domestic_plan_budget_null.sql` | `clean_dapa_domestic_plan.budget_krw` NULL 허용(예산 미기재 행 보존) | 2026-09-18 적용 — 2026-09-20 RDS 실측 `IS_NULLABLE=YES`(`file-cleanup-audit-2026-09-20.md` §2) |
| `db/alter_2026-09-19_krit_budget_clean.sql` | `clean_krit_task` 열 9개 보강 + 열린재정 clean 2표(`clean_openfiscal_program_budget`·`clean_openfiscal_program_link`) 신설 | 2026-09-19 적용 — 2026-09-20 RDS 실측 열·표 존재 |
| `db/alter_2026-09-21_elec_fsg60.sql` | 전자 판정 플래그 FSG 60 기준 통일: `clean_kdsis_nsn.is_electronic_group` fsg2='60' 0→1 + 두 표(`clean_kdsis_nsn`·`clean_dapa_localized_item`) 열 COMMENT·열 사전 2행을 「58·59·60, 잠정」으로. 근거 `open-decisions-2026-09-21.md` D5 | **2026-09-21 적용**(`apply_alter.py --twice`, 2회 exit 0. 1회째 UPDATE 317·0·1·1, 2회째 전부 0. 실측: kdsis 60 317/317, 전자군 합 33,577 → **33,894**, `clean_dapa_localized_item` 2,717 불변. 경고는 1681 display width뿐) |
| `db/alter_2026-09-21_hhi_views.sql` | HHI 뷰 4개 정정(`open-decisions-2026-09-21.md` D6·D7): `v_import_share_hs6_year`·`v_export_share_hs6_year` `share`를 `CAST(… AS DOUBLE)`(DECIMAL 4자리 반올림 제거 → 뷰 HHI = pandas HHI), `v_hhi_hs6_year`·`v_hhi_export_hs6_year` `country_count`를 `CAST(SUM(imp_dlr>0) AS UNSIGNED)`(실적 있는 국가 수). 09-20 제안 파일 `alter_2026-09-20_country_count.sql` 대체·삭제. `schema.sql`·`table_dict.csv`·카탈로그 동기 | **2026-09-21 적용**(`apply_alter.py --twice`, 5문 × 2회 exit 0). DBHub 실측 2025 `country_count` 847180 127→**73** · 854231 86→**68** · 852692 104→**50** · 851762 144→**86**(수출 118·69·92·138), `v_review_list` 동일, hhi 정수 자리·top1 불변(5276.18→5276.11 등 소수만), 열 타입 `share`·`top1_share`·`hhi` double, 246행 |
| `db/alter_2026-09-21_drop_customs_copies.sql` | 사전 밖 표 2개 DROP(`clean_customs_trade` 294,420·`clean_customs_progress` 264 — 09-20 밤 생성된 raw 복사본, `open-decisions-2026-09-21.md` D14) | **2026-09-21 적용**(`apply_alter.py --twice`, 2회 exit 0, 2회째 Note 1051뿐). 실측: BASE TABLE 58 → **56**, `clean_customs%` 0, raw 2표 294,420·264 불변 |
| `db/alter_2026-09-22_drop_clean_copies.sql` | 사전 밖 표 4개 DROP — 09-21 DROP한 `clean_customs_trade`(294,420)·`clean_customs_progress`(264)가 09-21 16:12·18:03 재생성되고 `clean_hs_unit_name`(17,072)·`clean_hs_code_master`(12,469)가 09-22 00:29·00:33 추가(raw 1:1, 사전·로그 0건, 만든 계정 미확인). `open-decisions-2026-09-21.md` D14 재발 항목 | **2026-09-22 적용**(`apply_alter.py --twice`, 5문 × 2회 exit 0, 2회째 Note 1051뿐). DBHub 실측(`ip-10-7-0-61`): BASE TABLE 60 → **56**, 뷰 31, `clean_customs%`·`clean_hs_%` 잔여는 사전 등재 표 `clean_hsk_control`뿐, raw 4표 294,420·264·17,072·12,469 불변, `fact_customs_monthly` 294,174·`dim_hs10` 211·`ref_hs_rule_flag` 1,003 불변. `gen_table_catalog.py` 객체 87(사전 누락 0·RDS 누락 0) |
| `db/alter_2026-09-22_meta_note_column_dict.sql` | `meta_dataset.note` 1행 정정(`ref_hs_whitelist` — 삭제된 `related_fsc`·`b2_scope` 문구 → M5 기준 13개/R4 폐기) + `meta_column_dict` 미등재 8열 INSERT(`raw_krit_task` 5 · `raw_kosis_*.source_col_no` 2 · `clean_kdsis_nsn.cleaned_at`). 표·뷰 변경 없음. + `ref_hs_whitelist.evidence` dtype VARCHAR(50)→(120) 정정(RDS 실측). `db/column_dict.csv` 823 → 831 같이 갱신. 발견 경로 `docs/next.md` A3(09-22)·`gen_data_spec_xlsx.py` 경고 | **2026-09-22 적용**(`apply_alter.py --twice`, 1회차 UPDATE 1·INSERT 8·UPDATE 1, 2회차 0). 실측: `meta_column_dict` 831, RDS 열 ↔ 사전 누락 0(적재 메타 4열 제외), `gen_table_catalog.py` 사전 누락 0 |
| `db/alter_2026-09-21_meta_dataset_ids.sql` | `meta_dataset` UPDATE 4문(표·뷰 변경 없음): 팀원 공유 파일 3건 `dataset_id`·`url`·포털 등록/수정일(15050919·15050925·15050923, D10) + 군별 계약집행 note 라벨 「국내·국외 구분 없는 총액」(D11) | **2026-09-21 적용**(`apply_alter.py --twice`, 1회차 rows 1·1·1·1, 2회차 0). `dataset_id` NULL 0 |
| `db/alter_2026-09-21_gwacheon_view.sql` | `v_customs_region_gwacheon_year` 신설(D1 ⑤): HS6 × 연도 전국 수입액·과천시 수입액·비중·건수·시군구 수(금액 천 달러). 화면 반영은 M7 결정 후 | **2026-09-21 적용**(`apply_alter.py --twice`, 2문 × 2회 exit 0). DBHub 실측: 246행, 2025 880730 0.3009(224,248/745,179) · 901490 0.2700 · 852560 0.2015 · 841191 0.0948 · 854231 0.0016 — `data-sources.md` 검증값과 일치. 뷰 31 → **32** |
| `db/alter_2026-09-21_customs_region.sql` | 관세청 시군구별 수출입실적(15134343) raw 표 `raw_customs_region` 신설(13열 + 적재 열, `utf8mb4_unicode_ci`) + 열 사전 13행 + `meta_dataset` `customs_region` 1행. clean·뷰 없음 — 화면 채택 여부는 팀 결정(`open-decisions-2026-09-21.md` D1). **금액 단위 천 달러** | **2026-09-21 적용**(조장 맥에 admin 계정이 없어 CREATE 권한이 있는 `dev_taeho`로 `apply_alter.apply` 2회, exit 0 — 1회째 rows 0·13·1, 2회째 전부 0, 경고는 1287·1050뿐). 이어서 `load_db.py --raw --tables raw_customs_region` 24파일 **273,586행 [일치]** 37.3s. 실측: 파일 24 · HS6 24 · 시군구 234 · 2016.01~2026.08 · NULL 0 · 키(`stat_ym`,`sgg_name`,`hs_cd`) 중복 0 · 880730 2025 수입 합 745,179(천$) · 2025 상위 5개 HS6 합이 `fact_customs_monthly`÷1,000 과 100.00% · `meta_column_dict` 849 → 862 · BASE TABLE 56 → 57 |
| `db/alter_2026-09-22_drop_p1_clean.sql` | **P1 관세청 정제 4표 폐기**(2026-09-22 팀 결정, `next.md` A1 종결): §1 `clean_customs_trade`·`clean_customs_progress`·`clean_hs_code_master`·`clean_hs_unit_name` `DROP TABLE IF EXISTS`(RDS 에는 이미 없었다 — 사용자 DROP, Note 1051), §2 `meta_column_dict` 47행 DELETE, §3 검증. 관세청 분석 축은 `fact_customs_monthly`·`dim_hs10` 만 남는다 | **2026-09-22 적용**(`dev_taeho` 로 `apply_alter.apply` 2회, 11문 × 2회 exit 0 — 1회째 DELETE 47, 2회째 0). 실측: 4표 0, 사전 잔여 0, `meta_column_dict` 870 → **823**, BASE TABLE **56** · VIEW **31**, `gen_table_catalog.py` 「사전 누락 0 · RDS 누락 0」. `db/schema.sql`(CREATE 56 = DROP 56)·`db/reset_data.sql`(TRUNCATE 46)·`db/table_dict.csv`(87)·`db/column_dict.csv`(823)·`scripts/load_db.py` REF_EXPECTED 823 동기 |
| `db/alter_2026-09-22_p1_clean_dict.sql` | P1 담당(수아) 클렌징 SQL 로 생긴 clean 4표(`clean_customs_trade` 294,420 · `clean_customs_progress` 264 · `clean_hs_code_master` 12,469 · `clean_hs_unit_name` 17,072)를 사전에 등록: §1 `clean_hs_unit_name` 의 실패했던 열 삭제 정정(원본 SQL 792행 `DROP COLUMN located_at` 이 `loaded_at` 오타 → MySQL 1091 로 ALTER 전체 무효), §2 `LIKE raw_` 복사로 raw 문구가 그대로 붙은 테이블 COMMENT 4개 + 옛 건수였던 `raw_customs_trade`(268,909)·`raw_customs_progress`(231) COMMENT 정정, §3 `meta_column_dict` 47행 INSERT, §4 검증. 행 수·값 불변 | **2026-09-22 적용**(admin 계정이 이 맥 `.env` 에 없어 09-21 `customs_region` 과 같이 `dev_taeho` 로 `apply_alter.apply` 2회, 20문 × 2회 exit 0 — 1회째 INSERT rows 47, 2회째 0, 경고는 deprecated `VALUES()` 1287뿐). 실측: `clean_hs_unit_name` 열 8 → **6**(`row_id`·`hs_code`·`hs_unit`·`name_ko`·`name_en`·`source_file` — `source_file` 은 원본 SQL 에서 의도적으로 주석 처리한 것이라 유지), 사전 4표 **16/6/19/6**, `meta_column_dict` 823 → **870**(`db/column_dict.csv` 도 870), 표 행 수 불변, `gen_table_catalog.py` 「사전 누락 4 → 0」. `db/schema.sql`(CREATE 60 = DROP 60)·`db/reset_data.sql`(TRUNCATE 50)·`db/table_dict.csv`(91)·`scripts/load_db.py` REF_EXPECTED 870 동기 |
| `db/alter_2026-09-21_m5_r4_exclude.sql` | 회의 M5(R4 제외, 진입식 R1 OR R2): R3∧R4로만 진입했던 6개(854110·854121·854129·852560·852692·901380) `priority` → 3 + `evidence_note` 머리 「규칙 미해당(2026-09-21 M5)」, `meta_column_dict` priority 행 1. 값 외 표·뷰 불변. 앱 필터는 `priority IN (1, 2)` | **2026-09-21 적용**(`apply_alter.py --twice`, 4문 × 2회 exit 0. 1회째 rows 6·1, 2회째 0). DBHub 실측: priority 1 **8** · 2 **5** · 3 **11**, `priority IN (1,2)` = 13, M5 노트 6행(전부 `evidence_basis='rule'` 유지) |
| `db/alter_2026-09-21_m4_elec_confirmed.sql` | 회의 M4(전자 판정 FSG 58·59·60 + 영숫자 NSN 확정): `clean_kdsis_nsn`·`clean_dapa_localized_item` `is_electronic_group` COMMENT의 「잠정」 제거(MODIFY, 정의 불변) + `meta_column_dict` 4행(두 표 + `ref_fsg`·`ref_fsc`의 뒤처진 「58·59」 문구 → 58·59·60). 값 불변 | **2026-09-21 적용**(`apply_alter.py --twice`, 8문 × 2회 exit 0. 1회째 UPDATE 1·1·1·1, 2회째 0, ALTER 경고는 1681뿐). 실측 kdsis 전자군 33,894 불변, `ref_fsg` 58·59·60 = 1 |
| `db/alter_2026-09-21_drop_category_map.sql` | 카테고리 맵 폐기(팀 결정·DROP 승인): `v_review_list` B2 열 제거·`v_hs6_candidate_rule` R4 항 제거 재정의 → `v_defense_relevance_b2` DROP → `ref_hs_indicator` defense_relevance 28행 DELETE → `ref_category_map` DROP → `ref_hs_whitelist.related_fsc` DROP(information_schema 조건 PREPARE) → 열 사전 11행 삭제·ordinal 재번호(`@mx` 가드, `ORDER BY ordinal`). 문자열 안 `;`는 `CHAR(59)` | **2026-09-21 적용**(`apply_alter.py --twice`, 16문 × 2회 exit 0. 1회째 DELETE 28·10·1, ordinal 6, 2회째 0). 실측: 표 56·뷰 31·사전 851, `ref_hs_indicator` civil_mix 61만, `v_hs6_candidate_rule` 후보 52(R4 0), `v_review_list` 246 |
| `db/alter_2026-09-21_drop_category_link_cols.sql` | 카테고리 맵 폐기 후속: `v_review_list` B1 열 제거(HHI만) → `clean_krit_task` FK·인덱스·`hs6`·`category`·`category_link_status` / `clean_dapa_localized_item` 인덱스·`category`·`category_link_status` / `clean_dapa_contract` `contract_group`·`category`·`category_link_status` / `ref_hs_whitelist.b2_scope` DROP(information_schema 조건 PREPARE) → 열 사전 8행 삭제·4표 ordinal 재번호(변수 카운터) | **2026-09-21 적용**(`apply_alter.py --twice`, 35문 × 2회 exit 0. 1회째 DELETE 3·2·3, ordinal 13·2·6). 실측: 남은 연결 열 0, `v_review_list` 246, 사전 823 |
| `db/alter_2026-09-21_drop_low_variance.sql` | 규칙 #13(clean_ 저분산 원본 속성 열 제외) 첫 적용: `v_overseas_bid_chain`에서 `ordering_agency` 제거 → 5표 20열 DROP(`clean_dapa_bid_notice` 10 · `clean_dapa_contract` 3 · `clean_dapa_overseas_bid_result` 4 · `clean_dapa_domestic_plan` 1 · `clean_openfiscal_program_budget` 2) + `meta_column_dict` 20행 삭제·5표 ordinal 재부여(851→831) + `meta_load_log` 5행. 행 수 불변. 적용 직전 5표 `db/dump_20260921_pre_drop.sql`(gitignore) | **2026-09-21 적용**(`apply_alter.py` 1회, 12문 전부 ok: DELETE 20 · ordinal UPDATE 118·118 · 로그 5). 실측 열 수 28/38/17/16/19 · `meta_column_dict` 831(ordinal 빈틈 0) · `v_overseas_bid_chain` 1,362행 · 5표 행 수 불변 · 표 56/뷰 31. DROP COLUMN 은 재실행 시 1091 오류가 정상이라 `--twice` 안 씀. 카탈로그 재생성(사전 누락 0·RDS 누락 0) |
| `db/alter_2026-09-20_meta_dataset_sha.sql` | `meta_dataset` UPDATE 3문(표·뷰 변경 없음): `customs_progress` sha256·file_bytes를 현행 264행 파일 값으로, `ref_hs_whitelist` sha256을 현행 17열 파일 값으로, `krit_task` sha256 NULL(다중 파일)·note. 근거 `file-cleanup-audit-2026-09-20.md` §2·§5 | **2026-09-20 적용 완료**(사용자 실행 `apply_alter.py`, 5문 exit 0, UPDATE 3문 각 rows=1). DBHub 실측: customs_progress 8,538/`fc1d199e…`, ref_hs_whitelist 14,363/`47ca912f…`, krit_task sha256 NULL |
| `db/alter_2026-09-23_semi_ref.sql` | 국방반도체 발전전략 참조표 7개 신설(`ref_semi_chip_type`·`_domestic_case`·`_market_share`·`_policy_timeline`·`_public_fab`·`_strategy_task`·`_stat`) + 열 사전 58행 + `meta_dataset` `semi_strategy`. 원본 `data/reference/semi_*.csv`(수작업, 발전전략 PDF·보도자료). 적재는 `load_db.py --ref`(`SEMI_REF`, 빈 표만). ⓪ 반도체 구역이 CSV 직독 대신 DB 를 읽게 한 팀 결정(2026-09-23) | **2026-09-23 적용**(admin, `--twice` 13문 × 2회 exit 0, 2회째 Note 1050·경고 1287·1681뿐). `--ref` 적재 7·13·16·12·14·12·2 = 76행 전부 기대 일치. `meta_column_dict` 916 = `db/column_dict.csv` 916, `gen_table_catalog.py` 사전 누락 0 · RDS 누락 0, BASE TABLE 44 · 뷰 31 |

```powershell
$env:MYSQL_PWD = "<MARIADB_PASSWORD>"
cmd /c '"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" -h <RDS_ENDPOINT> -P 3306 -u <MARIADB_USER> --protocol=TCP --default-character-set=utf8mb4 --show-warnings --table defense_dashboard < db\alter_2026-09-16_indicator.sql'
```

- **적용 대상은 운영 DB(RDS) 하나**(2026-09-18 전환): 위 "DB 스키마 적용" 절의 RDS 명령(`admin`)으로 실행하고 표 "적용" 칸에 기록한다. 팀 서버는 백업·연습용이라 같이 적용하지 않는다(필요하면 `mariadb.exe` 구 내부망 서버 명령으로 재현). 뷰 DEFINER는 실행 계정 `admin`으로 잡힌다.

- 재실행 가능: ALTER는 `information_schema` 검사 후 건너뛰고, 지표(`mil/aero/auto_hs10_share`·`b2_*`)는 **삭제 후 재삽입**이라 관세청·B2 데이터를 다시 적재한 뒤 이 파일을 다시 돌리면 지표와 `civil_mix`가 갱신된다. 실행 끝의 검증 SELECT 기대값(2026-09-16 당시 21개 기준): `civil_mix` 높음 3 / 중간 2 / 낮음 2 / NULL 14, 지표 39행, `meta_column_dict` 226 — 2026-09-19 RDS 현재는 NULL 15 · `ref_hs_indicator` 89 · `meta_column_dict` 849.
- `VALUES()` deprecated 경고(MySQL 8.4, Code 1287)는 무시. MariaDB 호환을 위해 alias 문법으로 바꾸지 않는다.
- HSK 연계표(`raw_hsk_control`)를 적재한 뒤에는 `hsk_control_*` 지표 INSERT와 `v_civil_mix_rule` 3번 규칙(문턱값)을 이 파일에 추가한다(`docs/reference/hs-whitelist-definition.md` §7).
- `alter_2026-09-16_hs_rule.sql` 기대값: `evidence_basis` rule 19 · 팀판단 5, 뷰 5개, `meta_column_dict` 281, `ref_hs_rule_flag` 원본 적재 후 1,003행(r1 3 · r3_ml 0 · r4 14 · in_whitelist 24). 노트북: `SELECT * FROM ref_hs_rule_flag WHERE rule_version='2026-09-16'`. 적재 후 대조: `SELECT verdict, COUNT(*) FROM v_hs6_candidate_vs_whitelist GROUP BY verdict;` → 결과를 `hs-whitelist-definition.md` §8-3에 채우고 사용자와 제외·추가 범위를 정한 뒤 §5 UPDATE 실행.

```bash
# 로컬 MariaDB 12.2로 문법만 검증할 때 (서비스 대신 스크래치 데이터 디렉터리를 3307에 띄움)
"C:\Program Files\MariaDB 12.2\bin\mariadb-install-db.exe" --datadir=<임시경로> --port=3307 --password=x
"C:\Program Files\MariaDB 12.2\bin\mariadbd.exe" --defaults-file=<임시경로>\my.ini --port=3307 --console
"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" -u root -px -P 3307 --protocol=TCP --default-character-set=utf8mb4 < db/schema.sql
```

### alter 적용 스크립트 (`scripts/apply_alter.py`, 2026-09-18)

mysql.exe 없이 `db/alter_*.sql`을 RDS admin(`scripts/dbconf.py` role="admin", `.env`의 `MARIADB_ADMIN_*`)으로 적용한다. 주석 줄을 뺀 뒤 세미콜론 단위로 한 문장씩 보내고 문장마다 `SHOW WARNINGS`를 출력한다(문자열 안 세미콜론은 지원하지 않음).

```bash
python scripts/apply_alter.py --dry-run db/alter_2026-09-18_bid_result_dup_kind.sql   # 문장 분리만 확인
python scripts/apply_alter.py --twice   db/alter_2026-09-18_bid_result_dup_kind.sql   # 2회 실행해 재실행 가능성 확인
```

## 5. DB 적재 (`scripts/load_db.py`)

적재 대상은 **AWS RDS**(2026-09-18부터)이며 접속은 `scripts/dbconf.py`가 `.env`의 `MARIADB_*`(계정 `etl_rw` — SELECT/INSERT/UPDATE/DELETE, TLS)를 읽는다. `LOAD DATA LOCAL`은 쓰지 않고 pymysql `executemany`(2,000행 배치)로 넣는다. `TRUNCATE`(`db/reset_data.sql`)는 `etl_rw` 권한 밖이라 위 절의 `admin` 명령으로 실행한다. 열 매핑은 `db/column_dict.csv`로 CSV 헤더를 순서 대조한 뒤 영문 열로 넣고, 빈 셀은 NULL, `source_file`·`source_row_no`(파서 레코드 순번)를 채운다.

```bash
python scripts/load_db.py --dry-run          # DB 접속 없이 원본 파일 파싱(read_raw)·헤더 대조·건수 대조(기대 건수는 RAW_TABLES.expected). --tables <데이터셋 키…> 로 일부만
python scripts/load_db.py --ref              # ref_hs_whitelist 24 · ref_country 238 · meta_column_dict 858(db/column_dict.csv = DB 표 + 원본 파일 열 사전 319) · meta_dataset · db/seed_ref.sql · ref_hs_code_master 11,327 · ref_hs6_name 2,254(원본 파일에서 read_raw, 2026-09-22)
python scripts/load_db.py --fact             # dim_hs10 · fact_customs_monthly · clean_customs_region — 원본 파일을 read_raw 로 읽어 pandas 로 만든다(ref_country·ref_hs_whitelist 누락 사전 검사. 2026-09-22 raw_ 표 삭제로 SQL INSERT…SELECT 대체)
python scripts/load_db.py --verify           # DB 건수 대조표(ref·meta·dim/fact·clean) + 원본 파일 파서 건수
```

- 순서: `--ref` → `--fact` → 정제 노트북(§6). **원본은 DB에 넣지 않는다**(2026-09-22 교수 피드백, `docs/report/feedback/professor-feedback-2026-09-22.md`) — `RAW_TABLES`는 원본 파일 데이터셋 23종의 파일·인코딩·기대 건수 명세이고 `read_raw(<키>)`가 파일을 DataFrame 으로 읽어 파서 순번 `row_id`를 붙인다(`clean_*.raw_row_id`의 정의). `meta_load_log`의 `원본 전체` 단계는 노트북·`--fact`가 `log_raw_stage`로 기록한다(`meta_dataset`에 키가 있어야 함).
- ~~`raw_hsk_control`(2026-09-16 등록, **미확보**)~~ → **확보·적재 완료(2026-09-16 밤, 2,161행 — 다음 항목)**. 당시 절차(기록용): 사용자가 data.go.kr `15034135` CSV를 `data/raw/kosti/hsk_control_15034135.csv`에 두고 `db/meta_dataset.csv`에 `kosti_hsk_control` 행(제공기관 무역안보관리원, `acquired_on`·`raw_row_count` 필수)을 추가한 뒤 `--raw --tables raw_hsk_control`. 인코딩(잠정 utf-8)·헤더(잠정 `품목번호`·`품명(국문)`·`품명(영문)`·`통제번호`)가 다르면 `RAW_TABLES`·`column_dict.csv`를 맞춘다.
- `raw_hs_code_master`·`raw_hs_unit_name`·`raw_hsk_control`(HS6 선정 규칙 원본 — `hs-whitelist-definition.md` §8): 2026-09-16 `data/raw/customs/`·`data/raw/kosti/`에 배치하고 팀 서버 적재 완료(12,469 / 17,072 / 2,161). XLSX는 `pandas.read_excel(openpyxl)`, 단위별 품목명은 5시트를 `special='hs_unit'`이 세로로 합친다. `raw_hsk_control.control_no`는 쉼표 목록(최대 1,218자)이라 TEXT. **주의**: `--ref`는 비어 있지 않은 `meta_dataset`을 건너뛰므로 새 dataset_key 행은 `INSERT`로 따로 넣어야 `meta_load_log`가 기록된다(09-16에는 pymysql로 직접 삽입).
- 관세청 HS6 **추가 수집·추가 적재**(2026-09-16 신규 852910·901410·901490): `python scripts/fetch_customs.py --all-countries --hs <신규>`(HS6당 11호출) 뒤, 팀 서버처럼 이미 적재된 DB에는 TRUNCATE 재적재 대신 신규 파일만 `raw_customs_trade`에 넣고 `DIM_SQL`·`FACT_SQL`을 `LEFT(hs_cd,6) IN (<신규>)`로 한정해 실행한다(09-16 실행 기록: raw +25,511 · progress +33 · dim +14 · fact +25,478 → 294,420 / 264 / 211 / 294,174). 그 다음 `db/alter_2026-09-16_indicator.sql` 재실행으로 지표·`civil_mix` 갱신. `load_db.py` 기대치는 24개 기준(294,420 / 264 / 294,174 / 2025 26,211)으로 바뀌었다.

- 재적재는 스크립트가 하지 않는다. 대상 표가 비어 있지 않으면 건너뛰므로 `db/reset_data.sql`(또는 그 표만 TRUNCATE)로 먼저 비운다. 원본 파일은 `read_raw`가 매번 다시 읽으므로 되돌릴 것이 없다.
- 파서: KOSIS 2종은 광폭 → 세로형 형식 변환(`source_row_no`·`source_col_no`로 셀 위치 보존 — 09-19 수정으로 잠정치 헤더 `p)`도 월로 읽는다), KRIT는 `<차수>_…_t<N>.csv` 파일명에서 `round_label`·`table_index`를 얻고 공통 5열 외는 `extra_json`. A7 담당자명·연락처 열은 NULL로 읽는다(`null_cols`). 파일이 이 PC에 없는 데이터셋(`raw_customs_region`, 맥 수집분)은 `read_raw`가 FileNotFoundError.
- `sql_mode`에 `STRICT_TRANS_TABLES`가 있어 열 길이 초과는 오류(1406)로 잡힌다 — 2026-09-15 입찰공고 여부 열(열 밀림 원본 2행)과 면허제한그룹, 입찰결과 적격심사여부가 걸려 열을 넓혔다(`schema-change-log.md` §6).
- `db/seed_ref.sql`은 `ref_sido_map`(시도 토큰 44개 — 2026-09-18 모호한 광주·광주시 제외, 충남대전시 추가)과 `ref_category_map` 후보(`ref_hs_whitelist.related_fsc` 분해, `link_status='후보'`)를 넣는다. 재실행해도 중복되지 않는다.
- 열 사전 `db/column_dict.csv`는 `meta_column_dict` 테이블에 그대로 적재한다(UTF-8).
- `LOAD DATA`를 쓸 수 있는 환경(로컬 검증 등)에서는 cp949 파일에 `CHARACTER SET euckr`, 줄끝은 파일별로 확인(`db-connection.md` §4).

## 6. 정제 노트북 (`notebooks/*.ipynb`) — `clean_` 채우기

`clean_` 테이블은 노트북이 채운다. **입력은 원본 파일**(`from load_db import read_raw`, 노트북 안 헬퍼 `raw(<데이터셋 키>, [열…])` — 2026-09-22 RDS `raw_` 표 삭제 후 전환, `raw_row_id` = 파서 순번), 접속은 `scripts/load_db.py`의 `connect()`(→ `scripts/dbconf.py`, `.env`의 `MARIADB_*`=RDS·`etl_rw`)를 재사용하고, 대상 테이블이 **비어 있을 때만** INSERT한 뒤 `meta_load_log`에 `원본 전체`(`log_raw_stage`)·`중복 처리 후`·`관련 후보` 단계를 기록한다. 검산은 `원본 파서 행 수 = clean + excluded`. 2026-09-22 전환 후 6개 전부 재실행(오류 0, 차이 0).

```bash
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/clean_b2_a7.ipynb
```

| 노트북 | 채우는 테이블 | 실행 결과(실행일 명시) |
|---|---|---|
| `notebooks/clean_p4_domestic.ipynb` | P4 8표 + `clean_excluded_row`: `clean_dapa_contract`·`clean_dapa_bid_notice`·`clean_dapa_bid_result`·`clean_dapa_domestic_plan`·`clean_dapa_contract_exec_by_service`·`clean_company`·`clean_company_name_link`·`clean_dapa_defense_company`(2026-09-22 신설, 84) | **2026-09-19 실행**(전역 Python의 nbconvert + 커널 `defense-dashboard`: `py -3.14 -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 --ExecutePreprocessor.kernel_name=defense-dashboard notebooks/clean_p4_domestic.ipynb`). 43,111(계약 단위 37,608) / 10,840 / 7,403(키 7,199) / 35,859 / 40 / 14,838 / 491, 제외 행 5(KEY_CONFLICT 1·COL_SHIFT 4), 검산 `raw = clean + excluded` gap 0, `meta_load_log` 10행(83~92). 판단 속성(`class5` 등)은 기본값. **09-19 저녁 P2 검수 반영**: 셀 2 `sido_code()`에 광주 둘째 토큰 규칙(29/41, 그 밖은 NULL), 셀 4에 테스트 업체 6행 정확 일치 제외(PLACEHOLDER, `is_latest_seq` 계산 전) 추가 — RDS는 재실행 대신 `db/alter_2026-09-19_sido_backfill_test_vendor.sql`로 같은 상태를 만들었고(43,105 / 14,836 / 제외 11), 재실행 시 이 값이 나와야 한다(`ref_sido_map` 44 토큰 기준) |
| `notebooks/clean_p3_overseas.ipynb` | P3 4표: `clean_dapa_overseas_plan_api`·`ref_equipment_alias`·`clean_dapa_overseas_contract`·`clean_dapa_overseas_bid_result` | **2026-09-19 실행**(`py -3.14 -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 --ExecutePreprocessor.kernel_name=defense-dashboard notebooks/clean_p3_overseas.ipynb`). 13,615 / 843 / 6,333 / 2,494, 제외 행 0(검산 `raw = clean` gap 0), `meta_load_log` 11행(103~113). 전자 FSG 58·59·60 = 2,267행, KDSIS 연결 616행(고유 NSN 412/8,210). 장비명 표준명은 40종만 `후보`, 803종은 NULL·`미확인`. DDL은 `db/alter_2026-09-19_p3_clean.sql` |
| `notebooks/clean_p5_krit_p2_budget.ipynb` | P5-4 + P2-6 3표: `clean_krit_task`(B1 KRIT 공고) · `clean_openfiscal_program_budget`(A9 열린재정 예산) · `clean_openfiscal_program_link`(세부사업명 개편 연결표) | **2026-09-19 실행**(`py -3.14 -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 --ExecutePreprocessor.kernel_name=defense-dashboard notebooks/clean_p5_krit_p2_budget.ipynb`). 96 / 2,860 / 22, 제외 행 0(검산 `raw = clean + excluded` gap 0), `meta_load_log` 5행(98~101·114). KRIT `is_latest=1` **73**(23-4 18 / 24-1 11 / 25-1 22 / 26-1 2 / 26-2 20), `hs6`는 전부 NULL·`미연결`. 예산 연도별 합계·`국방기술개발` 단위사업 합계가 `v_budget_rnd_yearly`와 **차이 0**. DDL은 `db/alter_2026-09-19_krit_budget_clean.sql` |
| `notebooks/clean_p1_customs_hs.ipynb` | P1 1표 적재 + 검증 5건: `clean_hsk_control` 적재 / `fact_customs_monthly`(원본 파일과 대조)·`raw_customs_progress`(파일)·`ref_hs_whitelist` 검증 / `dim_hs10` 마스터 열 UPDATE(`ref_hs_code_master`) / `ref_hs_rule_flag` 이름 열 UPDATE(`ref_hs6_name`) | **2026-09-19 실행**(`py -3.14 -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 --ExecutePreprocessor.kernel_name=defense-dashboard notebooks/clean_p1_customs_hs.ipynb`). `clean_hsk_control` **10,104행**(HSK10 2,161 고유 = raw, 제외 0), 총계행 246 대조 불일치 0, `dim_hs10` 현행 107 / 마스터없음 104, `ref_hs_rule_flag` 이름 998/1,003(06시트 509 · 10시트단일 489 · 없음 5, 규칙 플래그 불변), `ref_hs_whitelist` CSV↔DB 불일치 0, `meta_load_log` 11행(115~125). DDL은 `db/alter_2026-09-19_p1_customs_hs.sql` |
| `notebooks/clean_p5_kosis.ipynb` | P5-5 KOSIS 2표: `clean_kosis_utilization`(방산업체 분야별 평균가동률) · `clean_kosis_production_index`(광공업생산지수 C26 계열) | **2026-09-19 실행**(`py -3.14 -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 --ExecutePreprocessor.kernel_name=defense-dashboard notebooks/clean_p5_kosis.ipynb`, exit 0. 2회째 실행은 두 표 "비어 있지 않음 → 건너뜀" 확인. 설정 셀 `sys.stdout.reconfigure`에 Jupyter 커널 가드 `hasattr` 추가). 실측: **81 / 1,016**(= raw, 제외 0), `stat_month` 고유 **127**개월(2016-01-01~2026-07-01), `is_provisional` **16** = `is_month_restored` 16(raw `stat_ym='p)'` 결함 행을 `source_col_no`로 복원), `is_partial_year` 56, `scope_grade` ★ 254 / ▲ 254 / ✕ 508, `in_scope` 9 · `is_avg_row` 9, `meta_load_log` 4행(**126~129**: 중복 처리 후 81·1,016 / 관련 후보 9·254). DDL은 `db/alter_2026-09-19_kosis_clean.sql` |
| `notebooks/clean_b2_a7.ipynb` | `clean_dapa_localized_item`(B2 사업×부품 고유) · `clean_dapa_overseas_plan`(A7 판단번호 단위) | 25,025(고유 부품 12,788) / 3,023(필수값 결측 `TST00001001` 1행 제외, 같은 판단번호 5쌍은 PK 축약 — 별개 계획 행이라 23.6억 원이 빠짐, `has_conflict=1`). 전자 후보 392건(13.0%, 예산 21.3% 잠정·미검수). `meta_load_log` 4행 추가(46~49) |

- 재적재: `TRUNCATE clean_x` 후 노트북 재실행(입력이 원본 파일이라 표 간 순서 제약 없음). 원본 파일은 건드리지 않는다. `clean_company.ipynb`는 P4 §6과 중복이라 2026-09-22 삭제.
- 판단 속성(`category_link_status='확정'`, `electronics_review_status='확정'/'오탐'`)은 노트북이 만들지 않는다 — 팀 결정·표본 검수 후 UPDATE.

## 7. Markdown 문서 → PDF (`scripts/md_to_pdf.py`)

설계 문서·보고서를 제출·공유용 A4 PDF로 만든다. reportlab + 나눔고딕(`C:\Windows\Fonts\NanumGothic*.ttf`) 임베드. 제목·표·목록·코드 블록·인라인 코드를 옮기고, Mermaid `erDiagram`은 관계 목록 표로 바꾼다. `##`/`###` 제목이 목차와 PDF 북마크가 된다.

```bash
python scripts/md_to_pdf.py docs/db/schema-design.md --subtitle "데이터베이스 설계 문서"   # → docs/db/schema-design.pdf
python scripts/md_to_pdf.py docs/idea-review.md -o out/idea-review.pdf --no-toc
python scripts/md_to_pdf.py docs/db/table-guide.md --subtitle "팀원용 DB 테이블 가이드"        # 팀 공유용 6쪽
```

- 생성된 PDF는 파생 파일이라 커밋하지 않는다(`.gitignore` `docs/**/*.pdf`). md를 고치면 다시 뽑는다.
- 렌더링 확인은 `pypdfium2`로 PNG를 뽑아 본다(설치돼 있음). 표 열 폭은 가장 긴 단어가 잘리지 않게 자동 배분하므로, 셀에 아주 긴 식별자가 많으면 다른 열이 좁아진다.

## 8. RDS 계정 관리 (`scripts/rds_accounts.py`)

실행법·옵션(`--dry-run`, `--add-dev dev_<이름>`)과 계정 3종 권한은 `docs/runbook/aws-rds-setup.md` §4·§6, 실제 계정·IP 현황은 `docs/runbook/rds-access-registry.md`를 본다. admin 접속이 필요하고 비밀번호는 파일에만 기록한다(화면·로그 비출력).

## 9. 방사청 파일데이터

OpenAPI 없이 data.go.kr에서 수동 다운로드해 `data/raw/dapa/`에 둔다(cp949). 확보 기록은 `docs/report/data/data-feasibility-check-2026-09-13.md` 형식을 따른다.

## 10. Streamlit 배포 (Community Cloud, 2026-09-18 구축)

- 앱 URL **https://defense-trade.streamlit.app** — 워크스페이스 `kimhh080888-blip`(GitHub 로그인), 저장소 `kimhh080888-blip/Defense_Dashboard` `main` / 메인 파일 `app/main.py` / Python 3.14 / 루트 `requirements.txt` 사용. `main`에 push하면 자동 재배포(첫 빌드 약 2분, 2026-09-18 01:49 UTC 성공).
- 접속 정보: 로컬은 `.env`, 클라우드는 **앱 설정 → Secrets**(TOML, `.streamlit/secrets.toml.example` 그대로 채움). `app/db.py`가 `.env` → `st.secrets` 순으로 읽고, `MARIADB_SSL=1`이면 TLS(AWS RDS용).
- 현재 상태(2026-09-18): Secrets에 RDS `app_ro`(SELECT 전용) 접속 정보(`.streamlit/secrets.toml`과 동일 — `scripts/rds_accounts.py`가 생성)를 넣었고 화면 ①이 RDS 데이터로 뜬다. **RDS가 유일한 운영 DB**이므로 적재·alter가 RDS에 들어가면 앱에 그대로 반영된다(캐시 1시간, 즉시 보려면 앱 ⋮ → Reboot). 계정 3종·보안 그룹·크레딧은 `docs/runbook/db-connection.md`. 홈·① 수출입 현황 두 화면이 `db_ready()` 통과 후 KPI·차트를 그린다(2025 수입 498억$ · 수출 625억$ · 1위 수입국 대만 45.4% · 1위 수출국 중국 31.4%).
- 공개 범위: private 저장소 앱은 기본이 "Only specific people"(팀원에게 안 보임) → **2026-09-18 "This app is public and searchable"로 변경**(팀 결정). 다시 제한하려면 앱 설정 → 공유하기에서 되돌리고 이메일 초대. GitHub 권한은 OAuth `repo` 스코프(계정 전체 저장소 읽기)로 부여됨 — 작업 공간 설정 → 연결된 계정에서 해제 가능.
- **공개 앱 + 인터넷에서 닿는 DB 조합이라 확인할 것 넷** — Secrets 의 계정이 조회 전용인지, RDS 보안그룹 범위, 담당자명 열의 RDS 적재 정책, 공개 범위 유지 여부. `db-connection.md` §7 에 안건으로 정리해 두었다. 앱 쪽은 이미 `SELECT *` 없이 열을 명시하고 담당자명 열을 한 번도 조회하지 않으며(`app/` 전체 확인), 접속 실패 메시지에 비밀번호·호스트를 섞지 않는다.
- 로컬 실행: `streamlit run app/main.py` (`.streamlit/config.toml`: headless·통계 수집 끔·`client.showErrorDetails = "type"` — 브라우저에는 예외 유형만, 전체 메시지는 콘솔. 로컬에서 전부 보려면 `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=full`).
- 앱 공통 계층(2026-09-20): `app/metrics.py`(집중도·기간·건수 상태 — streamlit 미의존), `app/db.py`(`try_query` 실패=예외 클래스명, `data_stamp` 데이터별 자료 기간·적재일), `app/ui.py`(`period_control`·`csv_header`). 회귀 검증: `.venv\Scripts\python.exe -m unittest discover -s tests -v`(DB 불필요, 22 케이스).

## 10-2. Jupyter MCP (2026-09-21)

Claude Code가 노트북 셀을 실행·검산하도록 JupyterLab을 MCP로 연결한다(설치 기록 `docs/install-log/INSTALLED.md` 2026-09-21). 세션마다 JupyterLab이 떠 있어야 `jupyter` MCP가 붙는다.

```powershell
$tok = (Get-Content .jupyter\token.env) -replace '^JUPYTER_TOKEN=',''
Start-Process .venv\Scripts\jupyter.exe -ArgumentList @('lab','--no-browser','--port','8888','--ServerApp.root_dir=C:\Defense_Dashboard',"--IdentityProvider.token=$tok") -WindowStyle Hidden
claude mcp get jupyter      # Status: Connected 확인. 안 붙으면 Claude Code 재시작
```

- 토큰 파일 `.jupyter/token.env`(gitignore)는 로컬 전용. 새 PC에서는 `python -c "import secrets;print(secrets.token_hex(24))"`로 만들고 `claude mcp add jupyter --scope local -e JUPYTER_URL=http://localhost:8888 -e JUPYTER_TOKEN=<토큰> -- <프로젝트>\.venv\Scripts\jupyter.exe mcp start --transport stdio`.
- 용도 경계: 정제·EDA 코드는 사용자가 쓴다. Claude는 검산 셀 실행·결과 확인·`stats-advisor` 자문 결과 확인에 쓴다.

## 11. 새 스크립트 작성 규칙

윈도우 콘솔(cp949)에서 한글이 깨지지 않도록 파일 앞부분에 `sys.stdout.reconfigure(encoding="utf-8")`을 둔다. 기존 스크립트 3개 모두 같은 패턴이다.

### 계약명 토큰 빈도 (`scripts/contract_name_tokens.py`, 2026-09-20)

`clean_dapa_contract.contract_name`(최종 차수 37,602)의 유니그램·바이그램 빈도를 뽑아 `class5` 키워드 사전 초안의 기초 자료를 만든다(`dbconf.py` etl_rw SELECT만, 형태소 분석기 없이 `re`). 키워드는 후보일 뿐이며(`data-cleaning-rules.md` §1 #8) 정확도 측정 전에는 `class5`를 바꾸지 않는다. 결과 보고서 `docs/report/data/contract-name-tokens-2026-09-20.md`.

```powershell
python scripts/contract_name_tokens.py --top 300 --min-df 2 --out tokens.md     # 상위 300, 바이그램 문서 빈도 2 이상, 파일로도 저장
python scripts/contract_name_tokens.py --keep-verbs                            # 행위·수량어(구매·용역·등…)를 메인 표에 남김
python scripts/contract_name_tokens.py --rules data/reference/contract_class5_rules.csv   # 팀원 규칙표 pattern 커버리지: 규칙별 걸린 토큰 수·원문 걸린 행 수(단독 대조), 분류 충돌 토큰, 안 걸리는 토큰(파일 없으면 경고 1줄)
```

### 테이블 카탈로그 생성 (`scripts/gen_table_catalog.py`, 2026-09-20)

`db/table_dict.csv`(테이블 사전: 역할·원천·한 행·쓰는 곳·주의, 91행 — `kind=file` 23행은 원본 파일 데이터셋, RDS 대조 제외) + `db/column_dict.csv`(열 사전) + RDS 실측(행 수·PK·뷰 열) → `docs/db/table-catalog.md`. 새 테이블·뷰를 만들면 `table_dict.csv`에 1행 추가하고 재생성한다(사전 누락·RDS 누락이 0이어야 정상). etl_rw SELECT만.

```bash
python scripts/gen_table_catalog.py               # docs/db/table-catalog.md 덮어씀(COUNT(*) 포함, 약 1분)
python scripts/gen_table_catalog.py --no-count    # 행 수 생략(빠름)
```

### ERD 정적 페이지 생성 (`scripts/gen_erd_html.py`, 2026-09-22)

`docs/db/erd.md`의 Mermaid 5개를 담은 독립 페이지 `docs/db/erd.html`을 만든다(mermaid는 cdnjs 로드). GitHub 저장소 화면에서는 `erd.md`가 바로 그려지므로 html은 로컬 더블클릭·GitHub Pages용. `erd.md`를 고친 뒤 실행해 둘을 맞춘다.

```bash
.venv/Scripts/python.exe scripts/gen_erd_html.py
```

### 시도 경계 GeoJSON 생성 (`scripts/build_sido_geojson.py`, 2026-09-22)

```
.venv/Scripts/python.exe scripts/build_sido_geojson.py
```

southkorea-maps 통계청 2018 시도 TopoJSON(단순화본)을 내려받아 GeoJSON으로 디코딩하고 `sido_code`(행정표준 2자리)를 붙여 `data/reference/sido_boundary.geojson`(17 feature, 640 KB)을 만든다. 네트워크만 필요, 추가 의존성 없음. 재실행하면 같은 파일을 덮어쓴다. 앱에서는 `json.load` 후 `px.choropleth(geojson=..., locations="sido_code", featureidkey="id")`.

### 데이터 수집 목록 및 명세서 xlsx 생성 (`scripts/gen_data_spec_xlsx.py`, 2026-09-22)

산출물 3. `db/meta_dataset.csv`(수집 데이터셋 26종) + `db/table_dict.csv`(역할·한 행·주의) + `db/column_dict.csv`(열 설명) + `db/clean_transform_map.csv`(raw→clean 이름이 바뀐 대응 42건) + RDS 실측(행 수·열·타입·NULL·예시값) → `docs/report/data/3_데이터수집목록및명세서-<asof>.xlsx`(시트 **30** = 목록 1 + 데이터셋 26 + 「(참고) DB 테이블·뷰」 1 + 「정제변경_요약」·「정제변경_상세」 2). 담당자명·대표자명·연락처·사업자·법인번호·주소 열의 예시값은 `PII_TOKENS` 로 `예시 생략(개인정보)` 처리한다. 서식은 `resource/drive/3_데이터수집목록및명세서_샘플.xlsx` 실측값(Malgun Gothic 11 / 제목 20 bold / 머리행 `FFD8D8D8` / thin 테두리 / 행 높이 16.5)을 그대로 따른다. **xlsx를 손으로 고치지 말고 세 CSV를 고친 뒤 재생성.** etl SELECT만.

```bash
.venv/bin/python scripts/gen_data_spec_xlsx.py                    # 작성일자 = 오늘
.venv/bin/python scripts/gen_data_spec_xlsx.py --asof 2026-10-02  # 제출일로 고정
.venv/bin/python scripts/gen_data_spec_xlsx.py --out /tmp/spec.xlsx
```

「(참고) DB 테이블·뷰」 시트는 RDS 전체(테이블 37 · 뷰 31)와 원본 파일 데이터셋 23종(`raw_` 키, 행 수 = 파서 실측, DB 밖)을 접두어별로 싣는다. 데이터셋 26종의 열·예시값·건수는 **원본 파일**을 `read_raw`로 읽어 채운다(2026-09-22; 참조표 3종은 DB 표). 파일이 없는 데이터셋은 열 사전·`meta_dataset` 건수로 대체하고 경고를 낸다. 「정제변경」 2시트는 raw_ ↔ 정제층 21쌍(`raw_X`↔`clean_X` 18 + `raw_customs_trade`↔`fact_customs_monthly` + `raw_hs_code_master`↔`ref_hs_code_master` + `raw_hs_unit_name`↔`ref_hs6_name` — `PAIR_OVERRIDE`)의 열을 원본 파일 파서 열 ↔ `information_schema` 로 대조해 6유형(동일명 유지 · 동일명·타입 변경 · 이름변경·변환 48 · 파생 추가 · raw 미적재(업무열) · raw 메타 = 528행)으로 낸다. 요약에는 쌍별 `정제 규칙 위치`(table_dict.source 의 노트북 경로, 없으면 전환 명세 문서)와 1:1 대응이 아닌 파생·참조 표 블록이 붙는다. 이름이 바뀐 대응만 기계적으로 알 수 없어 `db/clean_transform_map.csv`(훈희씨 작성분을 RDS 로 검증해 옮기고 관세청 6행 추가)를 쓰며, **새 정제 열을 만들면 이 CSV 에 1행 추가**한다.

`컬럼명(한글)` 은 원본 열명이 한글이면(방사청 CSV 헤더) 그대로, 영문이면(관세청 API) 열 사전 설명의 첫 구절을 쓰고, 둘 다 안 되면 `KO_FALLBACK` 로 보완한다(441/441 채움). **`Data Type` 은 항상 RDS 실측**이며 열 사전 `dtype` 이 어긋나면 생성 로그가 경고한다(현재 1건: `ref_hs_whitelist.evidence`).

시트 간 이동 링크(목록 C열 → 명세 시트, 명세 H4 `← 목록`)는 `link_cell()` 로 **`location=` 만 있는 내부 링크**로 쓴다. openpyxl 에 `cell.hyperlink = "#'시트'!A1"` 처럼 문자열을 넣으면 `TargetMode="External"` 관계로 나가고 **macOS Numbers 에서 클릭이 안 된다**(Excel 은 됨). 샘플 xlsx 도 `<hyperlink ref="C5" location="'…'!A1"/>`(r:id 없음) 형식이다 — 검증은 xlsx 를 풀어 `xl/worksheets/_rels/` 가 없는지 보면 된다.
