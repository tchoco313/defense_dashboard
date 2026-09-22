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

**새 표를 만들기 전에**: `docs/reference/clean-conversion-spec-2026-09-18.md` §2에 목표 객체가 이미 있으면(예: 관세청 → `fact_customs_monthly`, HS 마스터 → `dim_hs10`·`ref_hs_rule_flag`) 새 표를 만들지 않는다. 필요하면 명세 갱신 → alter 파일 → 열 사전 → `meta_load_log` 순으로 등록한다. 사전 밖 표는 카탈로그 경고가 나고 제출 명세서와 어긋나므로 삭제 대상이다(09-21·09-22 `clean_customs_*`·`clean_hs_*` 4표 DROP 사례).

## ER 다이어그램 (PK·FK 구조 보기)

1. 연결 트리에서 `defense_dashboard` 스키마를 더블클릭(또는 우클릭 › **View Diagram**) › 상단 **ER Diagram** 탭 — 테이블 56개와 FK 선이 한 화면에 그려진다.
2. 표가 많으면 툴바 검색·**Show/Hide entities**로 `raw_*`·`ref_*`를 숨기고 `clean_*`만 남긴다. 배치는 **Layout › Auto layout**, 저장은 툴바 **Export diagram**(PNG·SVG).
3. 선택한 표만 그리려면 트리의 **Diagrams › New ER diagram** › 표를 끌어다 놓는다. 이 다이어그램은 DBeaver 프로젝트에만 저장되고 DB는 바뀌지 않는다.

**한계**: DB의 FK 제약은 22개뿐이라(주로 `clean_ → raw_ 원본행`, `→ ref_hs_whitelist`, `→ ref_country`) 선이 그만큼만 나온다. `clean_` 표끼리의 실제 연결 키(HS6·판단번호·업체명 등)는 FK가 아니며 `docs/reference/clean-conversion-spec-2026-09-18.md` §7·`docs/db/table-guide.md` §2에 있다. 다이어그램에 그 선을 넣으려면 표 › Properties › **Foreign Keys › New virtual foreign key**로 가상 FK를 추가한다(DBeaver 로컬 설정, DB 미변경).
