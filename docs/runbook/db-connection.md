# 팀 DB 접속 (AWS RDS)

팀 DB는 **AWS RDS(MySQL 8.4) 한 곳**이며 DB 이름은 `defense_dashboard` 다. 스키마 설계는 `docs/db/schema-design.md`, DDL은 `db/schema.sql`.

**이 문서와 저장소에는 실제 엔드포인트·계정·비밀번호를 적지 않는다.** 실제 값은 로컬 `.env` 와 Streamlit Secrets 에만 둔다(둘 다 gitignore).

## 1. 접속 정보는 어디에 두나

| 어디서 쓰나 | 출처 |
|---|---|
| 로컬 스크립트·노트북 | 프로젝트 루트 `.env` 의 `MARIADB_*` (틀: `.env.example`) |
| Streamlit Community Cloud(배포 앱) | 앱 설정 → Secrets, 같은 키 이름 (틀: `.streamlit/secrets.toml.example`) |

코드는 접속 정보를 직접 적지 않고 `scripts/dbconf.py` 하나를 거친다. 읽는 순서는 ① `.env` → ② 없으면 Streamlit Secrets.

```
MARIADB_HOST=<RDS_ENDPOINT>
MARIADB_PORT=3306
MARIADB_USER=<계정>
MARIADB_PASSWORD=<비밀번호>
MARIADB_DATABASE=defense_dashboard
MARIADB_SSL=1                        # TLS 사용(인증서: certs/rds-global-bundle.pem)
```

## 2. 접속 확인

```bash
python scripts/check_db_access.py        # 인터넷 → 서버 포트 → 로그인 순서로 본다
```

GUI 도구(MySQL Workbench 등)로 붙을 때는 호스트에 RDS 엔드포인트, 포트 3306, **SSL 사용**.

## 3. 계정·권한

| 계정 | 무엇에 쓰나 | 권한 |
|---|---|---|
| `admin` (마스터) | DDL(`db/schema.sql`·`db/reset_data.sql`) · 계정 관리 | 전체 — 로컬 `.env` 의 `MARIADB_ADMIN_*` 에만 둔다 |
| `etl_rw` (적재) | `scripts/load_db.py` · 정제 노트북 | SELECT · INSERT · UPDATE · DELETE |
| `app_ro` (조회) | Streamlit 대시보드(배포 앱) | SELECT 만 |

- 대시보드는 조회 전용 계정으로만 붙인다. 공개 URL 이므로 쓰기 권한을 섞지 않는다.
- 마스터 계정은 앱·스크립트 설정에 넣지 않는다.

## 4. 주의

- **TLS 검증을 끄지 않는다.** RDS 는 공인 CA 인증서를 쓰므로 `certs/rds-global-bundle.pem` 으로 서버 인증서를 검증한다.
- 적재는 `LOAD DATA LOCAL INFILE` 대신 `scripts/load_db.py`(pymysql INSERT)로 한다.
- 연결 문자셋은 `utf8mb4` — 빼면 한글이 `???` 로 저장된다.
- `sql_mode` 의 `STRICT_TRANS_TABLES`, 뷰 콜레이션(`utf8mb4_unicode_ci`), cp949 원본 등 적재 시 주의점은 `docs/db/schema-design.md` §5.
- 원본 파일(`data/raw/`)은 수정하지 않는다. 정제 결과는 `clean_*` 표에 따로 둔다.

## 5. 백업

RDS 자동 백업(스냅샷)과 별도로, 필요하면 덤프를 뜬다. 덤프 파일은 `.gitignore` 가 막는다(`*.sql`·`dump_*.sql`).

```bash
mysqldump -h <RDS_ENDPOINT> -u <계정> -p --ssl-mode=REQUIRED \
  --default-character-set=utf8mb4 --routines defense_dashboard > db/dump_YYYYMMDD.sql
```
