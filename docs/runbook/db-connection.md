# 팀 DB 접속 (AWS RDS, 2026-09-18 이후)

팀 DB는 **AWS RDS(MySQL 8.4) 한 곳**이다. 학원 PC 내부망 서버는 2026-09-18 폐기했다(§8).

**이 문서에 실제 엔드포인트·계정·비밀번호를 적지 않는다.** 저장소가 공개되거나 외부에 제출될 수 있고, 한 번 커밋되면 지워도 git 이력에 남는다. 문서는 `<RDS_ENDPOINT>` 같은 플레이스홀더로 쓰고, 실제 값은 **로컬 `.env`** 와 **Streamlit Secrets** 에만 둔다. 두 곳 다 gitignore 대상이다.

스키마는 `docs/db/schema-design.md` + `db/schema.sql`. 명령 모음은 `docs/runbook/commands.md`.

## 1. 접속 정보는 어디에 두나

| 어디서 쓰나 | 출처 | 파일 |
|---|---|---|
| 로컬 스크립트·노트북 | 프로젝트 루트 `.env` 의 `MARIADB_*` | gitignore |
| Streamlit Community Cloud | 앱 설정 → Secrets (같은 키 이름) | 저장소에 없음 |
| DBHub MCP (조회 검증) | 사용자 환경변수 `MARIADB_USER`·`MARIADB_PASSWORD` + `~/.claude/dbhub.toml` | 저장소 밖 |

`.env` 키 (값은 조장에게 받는다):

```
MARIADB_HOST=<RDS_ENDPOINT>          # ...rds.amazonaws.com
MARIADB_PORT=3306
MARIADB_USER=<계정>
MARIADB_PASSWORD=<비밀번호>
MARIADB_DATABASE=defense_dashboard
MARIADB_SSL=1                        # RDS 는 1
```

**비밀번호를 팀 채팅에 올리지 않는다.** RDS 는 인터넷에서 닿는 주소라 내부망 서버와 위험도가 다르다 — 채팅 이력에 남은 비밀번호는 회수할 방법이 없다.

## 2. 붙기

```bash
python3 src/check_db_access.py        # DNS → 포트 → 로그인 순서로 본다
```

파이썬 코드는 `.env` 를 읽어 쓴다(`scripts/load_db.py` 와 같은 키). GUI 는 Workbench·DBeaver·HeidiSQL 아무거나 — 호스트에 RDS 엔드포인트, 포트 3306, **SSL 사용**.

내부망 서버와 달리 **집·핫스팟에서도 붙는다.** 학원에 있어야 할 이유가 없어졌다.

## 3. 계정·권한

| 계정 | 무엇에 쓰나 | 권한 |
|---|---|---|
| 적재·DDL 계정 | 수집·전처리 스크립트, `db/alter_*.sql` 적용 | `defense_dashboard.*` 에 ALL |
| 조회 전용 계정 | **Streamlit 대시보드** | `defense_dashboard.*` 에 SELECT 만 |

- **대시보드는 조회 전용 계정으로만 붙인다.** 앱이 공개 URL이므로 쓰기 권한이 섞이면 사고 범위가 DB 전체가 된다.
- `root`(RDS 마스터 계정)는 우리 코드 어디에도 넣지 않는다.
- 조회 전용 계정 만들기:

```sql
CREATE USER '<조회계정>'@'%' IDENTIFIED BY '<비밀번호>';
GRANT SELECT ON defense_dashboard.* TO '<조회계정>'@'%';
FLUSH PRIVILEGES;
SHOW GRANTS FOR '<조회계정>'@'%';     -- SELECT 만 나와야 한다
```

앱이 실제로 읽는 객체는 7개뿐이다(`v_import_hs6_year`·`v_hhi_hs6_year`·`v_hhi_export_hs6_year`·`fact_customs_monthly`·`ref_hs_whitelist`·`ref_country`·`raw_hs_unit_name`). 더 좁히려면 DB 전체 SELECT 대신 이 7개에만 `GRANT` 한다.

## 4. DDL·적재

절차는 내부망 때와 같다 — 호스트만 RDS 엔드포인트로 바뀐다. 명령은 `docs/runbook/commands.md` "DB 스키마 적용"·"증분 변경"·"DB 적재".

- **TLS 검증을 끄지 않는다.** 내부망 MySQL은 자체서명 인증서라 `--skip-ssl-verify-server-cert` 를 붙였지만, RDS 는 공인 CA 인증서이므로 이 옵션이 필요 없다. 붙이면 중간자 공격을 막지 못한다.
- `LOAD DATA LOCAL INFILE` 은 RDS 에서 서버 측 `local_infile` 파라미터그룹 설정이 필요하다. 지금까지 적재는 전부 `scripts/load_db.py`(pymysql INSERT)로 했으므로 그대로 쓴다.
- `sql_mode` 의 `STRICT_TRANS_TABLES`, 뷰 콜레이션(`utf8mb4_unicode_ci`), cp949 원본, 파일별 줄끝 — 적재 시 주의점은 서버가 바뀌어도 같다. 상세는 `docs/db/schema-design.md` §5.
- 원본 테이블(`raw_*`)은 적재 후 수정하지 않는다. 정제 결과는 `clean_*` 로 따로 둔다.

## 5. 백업

RDS 자동 백업(스냅샷) 보존 기간을 확인해 둔다. 과제 제출물은 여전히 **DDL + 덤프 파일**이므로, 제출 전에 한 번은 손으로 뽑는다:

```bash
mysqldump -h <RDS_ENDPOINT> -u <계정> -p --ssl-mode=REQUIRED \
  --default-character-set=utf8mb4 --routines defense_dashboard > db/dump_YYYYMMDD.sql
mysqldump -h <RDS_ENDPOINT> -u <계정> -p --no-data defense_dashboard > db/schema_dump.sql
```

덤프 파일은 `.gitignore` 가 막는다(`*.sql` + `dump_*.sql`). 공유는 드라이브로 한다.

## 6. 하지 말 것

- **보안그룹을 `0.0.0.0/0` 으로 열어 두지 않는다.** 3306 이 전 세계에 열려 있으면 스캐너가 며칠 안에 찾는다. 접속 출처를 좁힐 수 없다면 최소한 조회 전용 계정 + 32자 이상 랜덤 비밀번호 + TLS 강제(`require_secure_transport=ON`)를 걸어 둔다.
- 비밀번호를 팀 채팅·문서·커밋에 남기지 않는다.
- RDS 마스터 계정을 앱이나 스크립트에 넣지 않는다.
- `.env`·`secrets.toml` 커밋(이미 gitignore).
- 원본 CSV 수정·덮어쓰기.

## 7. 미결 안건 (팀 확인 필요)

| 안건 | 현재 상태 | 왜 |
|---|---|---|
| ① 대시보드 계정이 조회 전용인가 | **미확인** | Streamlit Secrets 의 `MARIADB_USER` 가 적재 계정(ALL)이면 공개 앱이 쓰기 권한으로 붙어 있는 것이다. §3 대로 교체 |
| ② 보안그룹 접속 출처 | **미확인** | Streamlit Community Cloud 는 고정 송신 IP 를 주지 않아 화이트리스트가 안 된다. 어떤 범위로 열려 있는지 확인 |
| ③ 담당자명 열을 RDS 에 올리는가 | 올라가 있음(추정) | `raw_dapa_contract`(담당자명 2열)·`raw_dapa_bid_notice`(2열)·`raw_dapa_bid_result`(1열)는 `column_dict.csv` 에 "화면 미노출"로만 적혀 있어 `scripts/load_db.py` 의 `null_cols` 마스킹이 걸리지 않는다. 내부망에서는 "뷰로 올리지 않는다"(`schema-design.md` §3)로 충분했지만, 인터넷에서 닿는 DB 에서는 정책을 다시 정해야 한다 — **마스킹 적용 여부는 팀 결정 사항이라 코드를 바꾸지 않았다** |
| ④ 앱 공개 범위 | "public and searchable" | `commands.md` "Streamlit 배포" 참고. ①③ 이 정리되기 전에는 초대 전용으로 되돌리는 쪽이 안전 |

## 8. 폐기된 구성 — 학원 내부망 서버 (2026-09-15 ~ 2026-09-18)

발표 때 "왜 옮겼나"를 설명할 수 있게 남긴다. **더 이상 쓰지 않는다.**

- 팀원 PC 한 대(Windows)에 MySQL 8.4 를 두고 학원 내부망에서만 붙는 구성이었다. `bind-address=0.0.0.0` + 방화벽 3306 인바운드 허용 + 계정 호스트 패턴 `@'%'`.
- 계정은 `defense3`(`SELECT, INSERT`) → `defense`(ALL PRIVILEGES) 로 바뀌었다. DDL 은 `mariadb.exe` + `MYSQL_PWD` 로 적용했고, DBHub MCP 는 `readonly` 라 조회 검증만 했다. 이 경위를 참조하는 이력 기록이 `schema-design.md` §6 에 있다.
- **한계 두 가지가 이관 이유다.** ① 학원 랜 밖에서 안 붙어(집·핫스팟 `TimeoutError`) DB 작업이 학원에 묶였다. ② Streamlit Community Cloud 에서 내부망에 닿지 않아 배포된 앱이 DB 를 읽지 못했다.
- 서버 PC 전원·DHCP 로 매일 IP 를 재확인하고 덤프를 매일 공유하던 절차도 같이 폐기했다.
