# MariaDB 학원 내부망 서버 구축·원격 접속 (2026-09-15 팀 작업용)

> 실측 2026-09-22(`mariadb.exe -h 192.168.100.221`): `@@hostname = DESKTOP-MRPP9MH`, 서버 버전 **MySQL 8.4.11**(문서의 MariaDB 아님), BASE TABLE 54, 이미 삭제된 `ref_category_map`·`test_table` 잔존 = 09-18 이전 스냅샷. 이 서버 수치를 RDS 실측으로 쓰면 안 된다(DBHub는 `~/.claude/dbhub.toml` → RDS `ip-10-7-0-61`).

> **2026-09-18부터 이 서버는 백업·로컬 연습용이다.** 운영 DB는 AWS RDS(`docs/runbook/aws-rds-setup.md`)이며 적재·alter·앱 접속은 전부 RDS로 한다. 이 서버에 새 데이터를 쓰지 않고, 필요할 때 RDS 덤프를 복원해 연습하는 용도로만 남긴다(`aws-rds-setup.md` §6). 아래 내용은 2026-09-15~18 구축 기록이다.

한 팀원 PC에 DB 서버를 두고 나머지가 같은 내부망에서 원격 접속하는 구성. 서버는 **협업 편의 수단**이고, 과제 제출물은 DDL·덤프 파일이다. 서버 PC가 없어도 작업이 멈추지 않도록 §5 덤프 공유를 매일 한다.

스키마는 `docs/db/schema-design.md` + `db/schema.sql`(2026-09-15, 구 초안 `dashboard-scope-2026-09-14.md` §5는 이관됨). 적재 코드(노트북)는 팀원이 작성하며 이 문서는 절차·설정값만 다룬다.

## 0. 시작 전 결정 (5분)

| 항목 | 선택 | 비고 |
|---|---|---|
| 서버 PC | (이름) | **유선 연결** 권장. 무선이면 §2-4 격리 확인 먼저 |
| DBMS | **MariaDB (확정, 2026-09-14)** | 과제 문구는 MySQL(`PROJECT.md`). 질문 받으면 "MySQL 호환 포크, pymysql·SQLAlchemy·Workbench 동일 동작"으로 답한다 |
| DB명 | `defense_dashboard` | `.env.example` 기본값 |
| 문자셋 | `utf8mb4` / `utf8mb4_unicode_ci` | 서버·DB·테이블 모두 |
| 팀 계정 | `team` / 비밀번호 | root는 원격 금지 |

설치하면 `docs/install-log/INSTALLED.md`에 제품·버전·설치 경로를 한 줄 추가한다.

## 1. 서버 PC 설정 (Windows)

### 1-1. 설정 파일

`C:\Program Files\MariaDB xx.x\data\my.ini`

```ini
[mysqld]
bind-address=0.0.0.0
port=3306
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
local_infile=1
```

수정 후 서비스 재시작(`services.msc` 또는 관리자 PowerShell에서 `Restart-Service MariaDB`). 서버 PC에 MySQL 8.0도 깔려 있으면 3306이 겹치므로 MySQL 서비스는 중지한다.

### 1-2. DB·계정 생성 (서버 PC에서 root로)

```sql
CREATE DATABASE defense_dashboard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'team'@'192.168.%' IDENTIFIED BY '<비밀번호>';
GRANT ALL PRIVILEGES ON defense_dashboard.* TO 'team'@'192.168.%';
FLUSH PRIVILEGES;
```

- `192.168.%`는 학원 대역에 맞춘다(`ipconfig`의 IPv4 앞 두 자리). `10.x`면 `'team'@'10.%'`.
- `'team'@'%'`는 내부망 전체 허용이라 급할 때만.

### 1-3. Windows 방화벽

관리자 PowerShell:

```powershell
Get-NetConnectionProfile                       # NetworkCategory가 Public이면 아래로 변경
Set-NetConnectionProfile -InterfaceIndex <번호> -NetworkCategory Private
New-NetFirewallRule -DisplayName "MariaDB 3306" -Direction Inbound -Protocol TCP -LocalPort 3306 -Action Allow -Profile Private,Domain
```

### 1-4. 유지

- 전원 옵션: 절전 안 함, 뚜껑 닫아도 계속(노트북). 화면 잠금은 무관.
- `ipconfig`로 IPv4 확인해 팀 채팅에 공유. DHCP라 **다음 날 바뀔 수 있으니 매일 아침 재확인**.

## 2. 클라이언트 접속 (나머지 팀원)

```powershell
Test-NetConnection <서버IP> -Port 3306         # TcpTestSucceeded : True 면 네트워크 OK
mysql -h <서버IP> -P 3306 -u team -p defense_dashboard
```

GUI: MySQL Workbench / DBeaver / HeidiSQL 아무거나. 호스트·포트·계정 동일.

프로젝트 코드는 `.env`만 바꾼다:

```
MARIADB_HOST=<서버IP>
MARIADB_USER=team
MARIADB_PASSWORD=<비밀번호>
MARIADB_DATABASE=defense_dashboard
```

### 2-4. 안 될 때 진단 순서

| 단계 | 명령 | 실패 시 원인 |
|---|---|---|
| 1 | `ping <서버IP>` | Wi-Fi 클라이언트 격리(AP isolation) 또는 다른 서브넷. 유선으로 바꾸거나 한 명 핫스팟에 전원 접속. 안 되면 §5 로컬 복원 방식으로 전환 |
| 2 | `Test-NetConnection <서버IP> -Port 3306` | ping은 되는데 실패 → 서버 방화벽(§1-3) 또는 네트워크 프로필 Public |
| 3 | `mysql -h ...`에서 `Can't connect` | `bind-address`가 127.0.0.1(§1-1), 서비스 미실행 |
| 4 | `Access denied for user 'team'@'192.168.x.x'` | 계정 호스트 패턴 불일치(§1-2) 또는 비밀번호 |
| 5 | 한글 깨짐 | 클라이언트 `--default-character-set=utf8mb4`, 서버 문자셋(§1-1), CSV 인코딩(§3) |

## 3. 적재 시 주의

- **(2026-09-15 실측) 팀 서버는 `local_infile=0`** — `LOAD DATA LOCAL INFILE`이 `ERROR 3948`로 막힌다. `defense3`는 DB 한정 권한이라 `SET GLOBAL local_infile=1`을 못 한다(조장이 서버 PC `my.ini`에 `local_infile=1`을 넣고 재시작해야 함). 그래서 실제 적재는 `scripts/load_db.py`(pymysql INSERT, `docs/runbook/commands.md` "DB 적재")로 했다. 아래 `LOAD DATA` 항목은 서버 설정이 바뀌거나 로컬 검증 인스턴스에서만 해당.
- **`sql_mode`에 `STRICT_TRANS_TABLES`** — 열 길이 초과가 경고가 아니라 오류(1406)로 롤백된다. 2026-09-15 입찰공고·입찰결과 열 확장 사례는 `schema-design.md` §5.
- **방사청 CSV는 cp949**(`data/raw/dapa/`). 노트북에서 `encoding="cp949"`로 읽어 pandas → `to_sql`로 넣거나, `LOAD DATA`를 쓰면 **`CHARACTER SET euckr`** 지정(2026-09-15 정정: MariaDB·MySQL에 `cp949`라는 문자셋 이름은 없어 `ERROR 1115`가 난다).
- **줄끝이 파일마다 다르다**: 계약정보·KOSIS 2종은 LF, 나머지(관세청·입찰공고·입찰결과·국산화개발품목·방산업체·참조표)는 CRLF. `LOAD DATA`의 `LINES TERMINATED BY`를 파일에 맞춘다(안 맞으면 0행 또는 마지막 열에 `\r`). `LOAD DATA LOCAL`은 중복 키를 조용히 건너뛰므로 적재 후 반드시 건수 대조. 상세는 `docs/db/schema-design.md` §5.
- 국가 참조표: pandas로 다룰 때 `keep_default_na=False` — `"NA"`(나미비아)가 결측으로 사라진다(`schema-change-log.md` §7-1).
- `LOAD DATA LOCAL INFILE`은 **클라이언트 쪽 파일**을 읽으므로 원격에서도 된다. 서버 `local_infile=1`(§1-1) + 클라이언트 옵션(`mysql --local-infile=1`, pymysql `local_infile=True`) 둘 다 필요.
- 원본 테이블(`dapa_contract_raw` 등)은 CSV 그대로, 정제 결과는 별도 테이블(`*_clean`). 원본 테이블은 적재 후 수정하지 않는다(CLAUDE.md 데이터 검증 규칙).
- 적재 후 `SELECT COUNT(*)`를 파서 기준 원본 건수(`docs/data-sources.md`, `docs/report/data/data-feasibility-check-2026-09-13.md`)와 대조해 기록한다. 물리 줄 수와 다를 수 있다.
- 관세청 `customs_all_*.csv`는 utf-8. 총계행(`is_total`) 포함 그대로 적재.

## 4. 하지 말 것

- (팀 서버에 한함) 공유기 포트포워딩·외부 인터넷 노출. 외부 접속이 필요한 용도는 RDS가 맡는다(`aws-rds-setup.md` — 보안 그룹 `/32` 허용만).
- root 비밀번호 공백, root 원격 허용.
- `.env` 커밋(이미 gitignore). 비밀번호는 팀 채팅으로만.
- 원본 CSV 수정·덮어쓰기.

## 5. 덤프 공유·백업 (매일 종료 전)

서버 PC에서:

```powershell
mysqldump -u root -p --default-character-set=utf8mb4 --routines defense_dashboard > db/dump_$(Get-Date -Format yyyyMMdd).sql
```

- `db/` 폴더에 두고 팀 공유(용량이 크면 드라이브). 스키마만 따로 `db/schema.sql`(`--no-data`)로 뽑아 두면 그게 제출용 DDL.
- 서버 PC가 없는 날은 각자 로컬 DB에 복원해 계속 작업: `mysql -u root -p defense_dashboard < db/dump_YYYYMMDD.sql`
- 로컬에서 정제 결과를 바꿨으면 다음 날 서버에 다시 덤프로 반영. 같은 테이블을 두 명이 동시에 고치지 않도록 테이블별 담당을 정한다.

## 6. Claude Code MCP 연결 (서버가 뜬 뒤, 사용자 PC에서)

두 MCP 모두 **적재 후 스키마·건수 확인용**이다. 테이블 생성·INSERT 도구는 없으므로 DDL은 MariaDB 12.2 클라이언트(`mariadb.exe`, `commands.md`), 적재는 `scripts/load_db.py`(pymysql)로 한다(2026-09-15 팀 서버 구축 완료 — `schema-change-log.md` §6 "팀 서버 적용 기록").

### 6-1. DBHub (검증 완료, 2026-09-15)

`docs/install-log/INSTALLED.md` 2026-09-14·09-15 항목 참고. 설정 절차(완료된 값):

1. `~/.claude/dbhub.toml`의 source `defense` 호스트를 `192.168.100.221:3306`으로 변경 — 완료
2. 사용자 환경변수 `MARIADB_USER`, `MARIADB_PASSWORD` 설정(프로젝트 `.env`와 동일 값). DBHub는 `.env`를 읽지 않고 프로세스 환경변수만 치환하므로 `.env`만 고쳐서는 연결되지 않는다 — 완료
3. Claude Code 완전 재시작(MCP는 시작 시 한 번 뜸) 후 `execute_sql`로 조회 — 완료

검증 결과(2026-09-15, 내부망): `execute_sql`로 `SELECT VERSION(), CURRENT_USER()` → `8.4.11`, `defense3@%`; `SHOW TABLES` → `test_table` 1개(3행). 도구는 READ-ONLY·1000행 제한으로 동작 확인.

실제 서버 상태(런북 초안과 다른 점):
- 팀 계정은 `team`이 아니라 **`defense3`**(`defense_dashboard.*` ALL PRIVILEGES, 원격 `%`). §0 표·§3 `.env` 예시의 `team`은 조장이 발급한 계정명으로 읽는다.
- `VERSION()`이 `8.4.11`로 나와 서버 PC의 DBMS는 **MySQL 8.4**로 보인다(MariaDB면 `11.x-MariaDB` 형식). 접속·SQL·pymysql 동작은 동일하므로 작업에는 영향 없음. §1 설정 파일 경로·서비스명은 서버 PC 기준으로 조장이 관리.
- (2026-09-15) 계정 권한이 ALL이라 읽기 전용 보장은 DBHub `readonly=true`뿐이었다. **(2026-09-16 실측) `SHOW GRANTS`가 `SELECT, INSERT ON defense_dashboard.*`로 축소됨** — `ALTER`·`UPDATE`가 `ERROR 1142`로 거부되므로 DDL 변경(`db/alter_*.sql`)은 조장이 실행하거나 권한을 다시 받아야 한다. → **같은 날 `.env`를 새 계정 `defense`(`ALL PRIVILEGES ON defense_dashboard.*`)로 교체해 `mariadb.exe`로 ALTER·UPDATE 성공.** DBHub는 사용자 환경변수 `MARIADB_USER`/`MARIADB_PASSWORD`를 읽으므로 그쪽도 `defense`로 바꾸고 Claude Code를 재시작해야 같은 계정이 된다(읽기 전용이라 `defense3`인 채로도 조회는 됨). SELECT 전용 계정이 필요하면 §1-2대로 조장에게 요청.

### 6-2. MariaDB 공식 MCP (`github.com/mariadb/mcp`, 미설치)

- 요구: Python 3.11 + `uv`. 도구: `list_databases`, `list_tables`, `get_table_schema(_with_relations)`, `execute_sql`(읽기 전용), `create_database` (+ 임베딩 설정 시 벡터 스토어 5종)
- 연결 환경변수: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`. `MCP_READ_ONLY`는 기본 `true`이나 README가 "best effort"라고 하므로 실제 읽기 전용 보장은 계정 권한으로 한다(필요하면 `SELECT`만 가진 `reader` 계정을 §1-2에 추가)
- 설치 위치는 저장소 밖(예: `~/.claude/mcp/mariadb-mcp`), `uv sync` 후 `claude mcp add --scope user --transport stdio mariadb -- uv --directory <경로> run server.py` 형태로 등록. 환경변수는 `-e DB_HOST=...` 로 전달
- 등록 후 `INSTALLED.md`의 "설치하지 않음" 문구를 실제 설치 기록으로 교체
