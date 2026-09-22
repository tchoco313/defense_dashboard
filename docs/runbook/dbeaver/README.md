# DBeaver로 RDS 접속 (팀원용)

접속 조건 2가지 — **공인 IP가 보안 그룹에 있고**(학원 `218.144.130.138`은 이미 허용, 집이면 `curl https://checkip.amazonaws.com` 값을 사용자에게 알려 추가) **본인 계정**(비밀번호는 사용자에게 직접 받음. 채팅·메일 금지).

## 방법 A — 파일 가져오기 (권장)
1. DBeaver › 파일 › 가져오기 › DBeaver › 프로젝트 설정(또는 `데이터베이스 › Import connections`) › `data-sources.json` 선택.
2. 가져온 연결 편집 › **인증** 탭에서 사용자명(`dev_지수` 계정명)·비밀번호 입력.
3. **SSL** 탭 › CA 인증서 경로를 이 저장소의 `certs/rds-global-bundle.pem`(절대 경로)으로 바꿈. `${workspace}`가 안 풀리면 직접 지정.
4. 드라이버 다운로드 확인(MySQL 8 Connector/J) › **테스트 연결**.

## 방법 B — 직접 입력
새 연결 › MySQL:
| 항목 | 값 |
|---|---|
| Server Host | `defense-dashboard.cja24us8a444.ap-northeast-2.rds.amazonaws.com` |
| Port | `3306` |
| Database | `defense_dashboard` |
| Username / Password | 본인 `dev_*` 계정 |
| SSL 탭 | **Use SSL 켬**, CA Certificate = `certs/rds-global-bundle.pem`, Verify server certificate 켬 |
| Driver properties | `characterEncoding=utf8` |

계정은 `REQUIRE SSL`이라 SSL을 끄면 1045/1251로 실패한다. 오류가 "Communications link failure"·시간 초과면 IP 미허용, "Access denied"면 계정·비밀번호·SSL 문제.

권한: `defense_dashboard` 안에서 SELECT·INSERT·UPDATE·DELETE·CREATE·ALTER·DROP·CREATE VIEW. 스키마 변경은 `db/schema.sql` 직접 실행 금지, `db/alter_<날짜>_<주제>.sql` 규칙(CLAUDE.md). 대장: `docs/runbook/rds-access-registry.md`.
