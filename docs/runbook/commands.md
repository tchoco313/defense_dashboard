# 실행 명령

모두 저장소 루트에서 실행한다. 테스트 스위트·린터는 없다.

## 관세청 수출입 OpenAPI 수집

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

## KRIT 부품국산화 공고 hwpx 표 추출

```bash
python scripts/parse_krit.py resource/krit/<공고>.hwpx          # 표 목록·크기 확인
python scripts/parse_krit.py resource/krit/*.hwpx --out data/raw/krit
```

## 강사 안내 자료 텍스트 재생성

`resource/drive/` → `docs/drive-text/*.txt`

```bash
python scripts/extract_drive_docs.py
```

## DB 스키마 적용 (`db/schema.sql`)

설계는 `docs/db/schema-design.md`. DDL은 전체 DROP 후 재생성(수작업 대응표·`meta_` 기록까지 삭제)이므로 **최초 구축·빈 개발 DB 초기화 전용**. 적재된 데이터가 있는 서버에서는 실행 전 덤프(`mariadb-remote-setup.md` §5). 데이터만 비우고 다시 적재할 때는 `db/reset_data.sql`(§5 재적재 3모드).

**팀 서버 적용 완료(2026-09-15)** — MySQL 8.4.11, 테이블 31 + 뷰 6, FK 12, 오류 0(`schema-design.md` §6). **데이터가 있는 DB에서 다시 실행하면 안전장치가 DROP 전에 오류(`ERROR 1146 … stop_schema_sql_db_has_data …`)로 멈춘다** — 강제 초기화는 덤프 후 파일 앞 안전장치 블록을 지우고 실행. 이 PC에는 `mysql` CLI가 없어 MariaDB 12.2 클라이언트를 쓴다. 비밀번호는 `MYSQL_PWD` 환경변수로 넘기고(`--password=`를 주면 12.x 클라이언트가 서버 인증서 검증을 켜서 MySQL 자체서명 인증서에 `ERROR 2026`이 난다), `--skip-ssl-verify-server-cert`를 붙인다.

```powershell
# 팀 서버(내부망). .env 의 MARIADB_* 값 사용. PowerShell 에서:
$env:MYSQL_PWD = "<MARIADB_PASSWORD>"
cmd /c '"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" -h 192.168.100.221 -P 3306 -u defense3 --protocol=TCP --skip-ssl-verify-server-cert --default-character-set=utf8mb4 --show-warnings defense_dashboard < db\schema.sql'
# 확인(2026-09-15 당시): 테이블 31(+ 조장의 test_table) + 뷰 6 — 2026-09-17 현재는 테이블 43(+test_table) + 뷰 31
cmd /c '"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" -h 192.168.100.221 -P 3306 -u defense3 --protocol=TCP --skip-ssl-verify-server-cert defense_dashboard -e "SHOW FULL TABLES"'

# 데이터 계층만 비우기(ref_·meta_dataset·meta_column_dict 보존). clean_ → fact_/dim_ → raw_ → meta_load_log 순 TRUNCATE
cmd /c '"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" ... defense_dashboard < db\reset_data.sql'
```

### 증분 변경 (`db/alter_*.sql`) — 적재된 서버에 스키마를 더할 때

`schema.sql`은 전체 DROP이라 적재된 서버에 못 돌린다. 열·테이블·뷰를 더할 때는 `db/alter_<날짜>_<주제>.sql`을 만들어 같은 `mariadb.exe` 방식으로 실행하고, `schema.sql`에도 같은 정의를 반영해 둘을 일치시킨다. DBHub MCP는 `readonly`라 ALTER·UPDATE가 안 되고(`READONLY_VIOLATION`), 계정은 `.env`의 `MARIADB_USER`(2026-09-16 `defense`, ALL PRIVILEGES — `mariadb-remote-setup.md` §6-1)를 쓴다.

| 파일 | 내용 | 적용 |
|---|---|---|
| `db/alter_2026-09-15_civil_mix.sql` | `ref_hs_whitelist.civil_mix` 추가(팀 판단 라벨) | 2026-09-16 적용, 같은 날 아래로 대체. 파일은 2026-09-17 삭제(git 이력) |
| `db/alter_2026-09-16_indicator.sql` | `ref_hs_indicator`·`raw_hsk_control`·뷰 3개(`v_hs10_use_share`·`v_defense_relevance_b2`·`v_civil_mix_rule`)·`civil_mix` 3열 + 지표 채우기 + `civil_mix` 규칙값 UPDATE | 2026-09-16 적용(2회 실행 확인) |
| `db/alter_2026-09-16_fsg.sql` | FSG 2자리 참조표 `ref_fsg`(80행 정적 시드) + `v_b2_fsg_summary` + 열 사전 8행 + `meta_dataset` `fsg_master` | **2026-09-16 적용**(팀 서버 3회 실행, 멱등. 기대: `ref_fsg` 80 · historical 2 · electronic 2 / `v_b2_fsg_summary` 53 16,300 · 59 2,942 · 58 379 / 미대응 `0`·NULL 18행 / `meta_column_dict` 289) |
| `db/alter_2026-09-17_view_collation.sql` | 뷰 15개를 `SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci` 세션에서 정의 변경 없이 재생성. 팀 서버(MySQL 8.4) 뷰가 `utf8mb4_0900_ai_ci`로 만들어져 `WHERE b1_status='미적재'` 같은 상태 열 비교가 `ERROR 1267 Illegal mix of collations`로 실패하던 문제 | **2026-09-17 적용**(exit 0, `information_schema.VIEWS` 15개 전부 `utf8mb4_unicode_ci`, 데이터 294,420행 보존). **앞으로 뷰를 만드는 alter는 머리에 같은 SET NAMES를 둔다** |
| `db/alter_2026-09-17_category_map.sql` | 품목군 대응표 확정 14 + 신규 1(5985→852910) + 대응불가 3, `clean_dapa_localized_item` 후보→확정, `b2_scope` 설정 | **미적용 — 팀 결정 후**(`docs/report/category-map-decision-2026-09-17.md`) |
| `db/alter_2026-09-16_api_budget.sql` | 팀 드라이브 채택 3종: `raw_dapa_overseas_plan_api`(국외 조달계획 OpenAPI 품목 단위 13,615)·`raw_dapa_fsc_catalog`(군급분류집 756)·`raw_openfiscal_program_budget`(열린재정 12파일 2,860) + `ref_fsc` 열 보강·시드(§3, raw 적재 후 **다시 실행**해야 676행) + 뷰 `v_overseas_plan_api_fsc`·`v_budget_rnd_yearly` + 열 사전 48행 + `meta_dataset` 3행 | **2026-09-16 적용**(2회 실행, exit 0. 기대: 3표 `--verify` 일치 · `ref_fsc` 676/전자군 46/폐지 22 · 뷰 합 9,970/전자군 1,819 · 예산 뷰 2020 10,053.3 → 2027 30,741.4 정부안 · `meta_column_dict` 337) |
| `db/alter_2026-09-17_kdsis_nsn.sql` | 국방표준종합서비스(KDSIS) NSN 목록 보조 조회용: `raw_kdsis_nsn`(228,027) + 파생 `clean_kdsis_nsn`(NSN별 1행 135,864)·`clean_kdsis_nsn_ref`(NSN×CAGE×참조번호 225,635) + 뷰 3(`v_overseas_plan_api_kdsis`·`v_b2_localized_kdsis`·`v_kdsis_link_summary`) + 열 사전 51행 + `meta_dataset` `kdsis_nsn` + 로그 2행. 원본은 `new_data/raw_kdsis_nsn.csv`(팀원 정리본, 2016 CSV 포함) | **2026-09-17 적용**(1차 표·뷰 → `load_db.py --raw --tables raw_kdsis_nsn` 89.6s → 2차 clean 채움. 기대: raw 228,027 · 숫자13 135,331 · 검토 533 · 속성 충돌 0 · ref 225,635 · `meta_column_dict` 388 · 기존 뷰 집계 불변 확인) |
| `db/alter_2026-09-17_procurement_aux.sql` | 국내 축 확장 뷰 9개: 조달 보조 6종(`raw_dapa_domestic_plan`·`bid_notice`·`bid_result`·`overseas_contract`·`overseas_bid_result`·`defense_company`) raw 직접 집계 + 계약정보 수의계약 사유(`v_contract_private_reason`·`v_contract_reason_group_yearly`). `CREATE OR REPLACE VIEW`만 있어 데이터·표를 건드리지 않음. FSC·HS6 축 아님 | **2026-09-17 적용**(1회, exit 0, 뷰 29개 전부 `utf8mb4_unicode_ci`). 기대값은 파일 §10(계약 37,608 · 수의 그룹 경쟁실패 1,847·단일공급 747 · 유찰 키 1,741 · 공고 10,840 · 국외 사슬 1,362/97 · 국내 계획 2025 8.558조 등). 재실행 가능 |
| `db/alter_2026-09-17_export.sql` | 수출 축 동등 배치(2026-09-17 사용자 결정): `v_export_share_hs6_year`·`v_hhi_export_hs6_year`(수입 뷰와 같은 구조, `exp_dlr` 기준). `CREATE OR REPLACE VIEW`만, 표·데이터 불변 | **2026-09-17 적용**(exit 0, 뷰 31개, 두 뷰 `utf8mb4_unicode_ci`. 확인: 2025 수출 HHI 854231 1,788(CN 26.9%) · 854239 1,945(TW 26.2%) · 852990 5,038(CN 69.3%)) |
| `db/alter_2026-09-16_hs_rule.sql` | HS6 선정 규칙: `raw_hs_code_master`·`raw_hs_unit_name`·`ref_hs_rule_flag`(R1~R4 스냅샷)·뷰 5개(`v_hs10_use_tag_all`·`v_hsk_control_by_hs6`·`v_hs6_candidate_rule`·`v_hs6_candidate_vs_whitelist`·`v_hs_whitelist_rule`)·`ref_hs_whitelist` `evidence_basis`·`evidence_note` + 열 사전. §5는 정적 UPDATE(rule 16)·강등(5)·INSERT(신규 3) — 적재 전 실행 가능. §5-4 `ref_hs_rule_flag` 스냅샷은 원본 3개 적재 후 **다시 한 번 실행**해야 1,003행이 채워짐(미적재면 0행) | **2026-09-16 적용**(팀 서버 2회 — 1차 ALTER·뷰·§5 정적값, 원본 3개 적재 후 2차에서 §5-4 스냅샷 1,003행. MySQL 8.4에서 `group_concat_max_len` 오류 1260 → 스크립트가 세션 한도를 올림) |

```powershell
$env:MYSQL_PWD = "<MARIADB_PASSWORD>"
cmd /c '"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" -h 192.168.100.221 -P 3306 -u <MARIADB_USER> --protocol=TCP --skip-ssl-verify-server-cert --default-character-set=utf8mb4 --show-warnings --table defense_dashboard < db\alter_2026-09-16_indicator.sql'
```

- 재실행 가능: ALTER는 `information_schema` 검사 후 건너뛰고, 지표(`mil/aero/auto_hs10_share`·`b2_*`)는 **삭제 후 재삽입**이라 관세청·B2 데이터를 다시 적재한 뒤 이 파일을 다시 돌리면 지표와 `civil_mix`가 갱신된다. 실행 끝의 검증 SELECT 기대값: `civil_mix` 높음 3 / 중간 2 / 낮음 2 / NULL 14, 지표 39행, `meta_column_dict` 226.
- `VALUES()` deprecated 경고(MySQL 8.4, Code 1287)는 무시. MariaDB 호환을 위해 alias 문법으로 바꾸지 않는다.
- HSK 연계표(`raw_hsk_control`)를 적재한 뒤에는 `hsk_control_*` 지표 INSERT와 `v_civil_mix_rule` 3번 규칙(문턱값)을 이 파일에 추가한다(`docs/reference/hs-whitelist-definition.md` §7).
- `alter_2026-09-16_hs_rule.sql` 기대값: `evidence_basis` rule 19 · 팀판단 5, 뷰 5개, `meta_column_dict` 281, `ref_hs_rule_flag` 원본 적재 후 1,003행(r1 3 · r3_ml 0 · r4 14 · in_whitelist 24). 노트북: `SELECT * FROM ref_hs_rule_flag WHERE rule_version='2026-09-16'`. 적재 후 대조: `SELECT verdict, COUNT(*) FROM v_hs6_candidate_vs_whitelist GROUP BY verdict;` → 결과를 `hs-whitelist-definition.md` §8-3에 채우고 사용자와 제외·추가 범위를 정한 뒤 §5 UPDATE 실행.

```bash
# 로컬 MariaDB 12.2로 문법만 검증할 때 (서비스 대신 스크래치 데이터 디렉터리를 3307에 띄움)
"C:\Program Files\MariaDB 12.2\bin\mariadb-install-db.exe" --datadir=<임시경로> --port=3307 --password=x
"C:\Program Files\MariaDB 12.2\bin\mariadbd.exe" --defaults-file=<임시경로>\my.ini --port=3307 --console
"C:\Program Files\MariaDB 12.2\bin\mariadb.exe" -u root -px -P 3307 --protocol=TCP --default-character-set=utf8mb4 < db/schema.sql
```

## DB 적재 (`scripts/load_db.py`)

팀 서버는 `local_infile=0`이라 `LOAD DATA LOCAL`이 막혀 있고 `defense3` 권한으로는 못 켠다(`SET GLOBAL`은 SUPER 필요). 그래서 적재는 pymysql `executemany`(2,000행 배치)로 한다. `.env`의 `MARIADB_*`를 읽는다. 열 매핑은 `db/column_dict.csv`로 CSV 헤더를 순서 대조한 뒤 영문 열로 넣고, 빈 셀은 NULL, `source_file`·`source_row_no`(파서 레코드 순번)를 채운다.

```bash
python scripts/load_db.py --dry-run          # DB 접속 없이 파일 파싱·헤더 대조·건수 대조(기대 건수는 스크립트 RAW_TABLES)
python scripts/load_db.py --ref              # ref_hs_whitelist 24 · ref_country 238 · meta_column_dict 281 · meta_dataset(db/meta_dataset.csv) · db/seed_ref.sql
python scripts/load_db.py --raw              # raw_ 18개(파일 없으면 SKIP, 비어 있지 않으면 건너뜀)
python scripts/load_db.py --raw --tables raw_dapa_overseas_plan raw_dapa_domestic_plan
python scripts/load_db.py --fact             # dim_hs10 · fact_customs_monthly (schema.sql §4 INSERT…SELECT, ref_country 누락 국가 사전 검사)
python scripts/load_db.py --verify           # 테이블별 건수 대조표
```

- 순서: `--ref` → `--raw` → `--fact`. `meta_load_log`에 파일별 `원본 전체` 단계가 자동 기록된다(`meta_dataset`에 키가 있어야 함).
- `raw_hsk_control`(2026-09-16 등록, **미확보**): 사용자가 data.go.kr `15034135` CSV를 `data/raw/kosti/hsk_control_15034135.csv`에 두고 `db/meta_dataset.csv`에 `kosti_hsk_control` 행(제공기관 무역안보관리원, `acquired_on`·`raw_row_count` 필수)을 추가한 뒤 `--raw --tables raw_hsk_control`. 인코딩(잠정 utf-8)·헤더(잠정 `품목번호`·`품명(국문)`·`품명(영문)`·`통제번호`)가 다르면 `RAW_TABLES`·`column_dict.csv`를 맞춘다.
- `raw_hs_code_master`·`raw_hs_unit_name`·`raw_hsk_control`(HS6 선정 규칙 원본 — `hs-whitelist-definition.md` §8): 2026-09-16 `data/raw/customs/`·`data/raw/kosti/`에 배치하고 팀 서버 적재 완료(12,469 / 17,072 / 2,161). XLSX는 `pandas.read_excel(openpyxl)`, 단위별 품목명은 5시트를 `special='hs_unit'`이 세로로 합친다. `raw_hsk_control.control_no`는 쉼표 목록(최대 1,218자)이라 TEXT. **주의**: `--ref`는 비어 있지 않은 `meta_dataset`을 건너뛰므로 새 dataset_key 행은 `INSERT`로 따로 넣어야 `meta_load_log`가 기록된다(09-16에는 pymysql로 직접 삽입).
- 관세청 HS6 **추가 수집·추가 적재**(2026-09-16 신규 852910·901410·901490): `python scripts/fetch_customs.py --all-countries --hs <신규>`(HS6당 11호출) 뒤, 팀 서버처럼 이미 적재된 DB에는 TRUNCATE 재적재 대신 신규 파일만 `raw_customs_trade`에 넣고 `DIM_SQL`·`FACT_SQL`을 `LEFT(hs_cd,6) IN (<신규>)`로 한정해 실행한다(09-16 실행 기록: raw +25,511 · progress +33 · dim +14 · fact +25,478 → 294,420 / 264 / 211 / 294,174). 그 다음 `db/alter_2026-09-16_indicator.sql` 재실행으로 지표·`civil_mix` 갱신. `load_db.py` 기대치는 24개 기준(294,420 / 264 / 294,174 / 2025 26,211)으로 바뀌었다.

- 재적재는 스크립트가 하지 않는다. 대상 raw가 비어 있지 않으면 건너뛰므로 `db/reset_data.sql` 또는 `DELETE FROM raw_x WHERE source_file='…'`로 먼저 비운다.
- KOSIS 2종은 광폭 → 세로형 형식 변환(`source_row_no`·`source_col_no`로 셀 위치 보존), KRIT는 `<차수>_…_t<N>.csv` 파일명에서 `round_label`·`table_index`를 얻고 공통 5열 외는 `extra_json`. A7 담당자명·연락처 열은 NULL로 넣는다.
- `sql_mode`에 `STRICT_TRANS_TABLES`가 있어 열 길이 초과는 오류(1406)로 잡힌다 — 2026-09-15 입찰공고 여부 열(열 밀림 원본 2행)과 면허제한그룹, 입찰결과 적격심사여부가 걸려 열을 넓혔다(`schema-design.md` §6).
- `db/seed_ref.sql`은 `ref_sido_map`(시도 토큰 45개)과 `ref_category_map` 후보(`ref_hs_whitelist.related_fsc` 분해, `link_status='후보'`)를 넣는다. 재실행해도 중복되지 않는다.
- 열 사전 `db/column_dict.csv`는 `meta_column_dict` 테이블에 그대로 적재한다(UTF-8).
- `LOAD DATA`를 쓸 수 있는 환경(로컬 검증 등)에서는 cp949 파일에 `CHARACTER SET euckr`, 줄끝은 파일별로 확인(`mariadb-remote-setup.md` §3).

## 정제 노트북 (`notebooks/*.ipynb`) — `clean_` 채우기

`clean_` 테이블은 노트북이 채운다. 접속은 `scripts/load_db.py`의 `connect()`(`.env`)를 재사용하고, 대상 테이블이 **비어 있을 때만** INSERT한 뒤 `meta_load_log`에 `중복 처리 후`·`관련 후보` 단계를 기록한다.

```bash
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/clean_b2_a7.ipynb
```

| 노트북 | 채우는 테이블 | 2026-09-17 결과 |
|---|---|---|
| `notebooks/clean_b2_a7.ipynb` | `clean_dapa_localized_item`(B2 사업×부품 고유) · `clean_dapa_overseas_plan`(A7 판단번호 단위) | 25,025(고유 부품 12,788) / 3,023(필수값 결측 `TST00001001` 1행 제외, 같은 판단번호 5쌍은 PK 축약 — 별개 계획 행이라 23.6억 원이 빠짐, `has_conflict=1`). 전자 후보 392건(13.0%, 예산 21.3% 잠정·미검수). `meta_load_log` 4행 추가(46~49) |

- 재적재: `TRUNCATE clean_x` 후 노트북 재실행(clean_은 raw를 참조만 하므로 FK 문제 없음). raw는 건드리지 않는다.
- 판단 속성(`category_link_status='확정'`, `electronics_review_status='확정'/'오탐'`)은 노트북이 만들지 않는다 — 팀 결정·표본 검수 후 UPDATE.

## Markdown 문서 → PDF (`scripts/md_to_pdf.py`)

설계 문서·보고서를 제출·공유용 A4 PDF로 만든다. reportlab + 나눔고딕(`C:\Windows\Fonts\NanumGothic*.ttf`) 임베드. 제목·표·목록·코드 블록·인라인 코드를 옮기고, Mermaid `erDiagram`은 관계 목록 표로 바꾼다. `##`/`###` 제목이 목차와 PDF 북마크가 된다.

```bash
python scripts/md_to_pdf.py docs/db/schema-design.md --subtitle "데이터베이스 설계 문서"   # → docs/db/schema-design.pdf
python scripts/md_to_pdf.py docs/idea-review.md -o out/idea-review.pdf --no-toc
python scripts/md_to_pdf.py docs/db/table-guide.md --subtitle "팀원용 DB 테이블 가이드"        # 팀 공유용 6쪽
```

- 생성된 PDF는 파생 파일이라 커밋하지 않는다(`.gitignore` `docs/**/*.pdf`). md를 고치면 다시 뽑는다.
- 렌더링 확인은 `pypdfium2`로 PNG를 뽑아 본다(설치돼 있음). 표 열 폭은 가장 긴 단어가 잘리지 않게 자동 배분하므로, 셀에 아주 긴 식별자가 많으면 다른 열이 좁아진다.

## 방사청 파일데이터

OpenAPI 없이 data.go.kr에서 수동 다운로드해 `data/raw/dapa/`에 둔다(cp949). 확보 기록은 `docs/report/data_feasibility_check.md` 형식을 따른다.

## 새 스크립트 작성 규칙

윈도우 콘솔(cp949)에서 한글이 깨지지 않도록 파일 앞부분에 `sys.stdout.reconfigure(encoding="utf-8")`을 둔다. 기존 스크립트 3개 모두 같은 패턴이다.
