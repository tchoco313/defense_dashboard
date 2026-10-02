# certs — DB 접속용 공개 인증서

`rds-global-bundle.pem` 은 Amazon RDS 가 공개하는 **CA 인증서 묶음**이다(https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem). 비밀 정보가 아니다.

팀 DB(AWS RDS)에 TLS 로 접속할 때(`.env` 의 `MARIADB_SSL=1`) `scripts/dbconf.py` 가 이 파일로 서버 인증서와 호스트 이름을 검증한다. 로컬 MySQL 에 덤프를 복원해 쓸 때(`MARIADB_SSL=0`)는 쓰지 않는다.
