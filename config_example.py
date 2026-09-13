# -*- coding: utf-8 -*-
"""접속 정보 틀 — 이 파일을 복사해서 이름을 config.py 로 바꾸고 자기 값을 채운다.
   config.py 는 .gitignore 에 있어서 깃에 안 올라간다. 안심하고 적어도 된다.

   쓰는 법 (수업에서 만든 모듈 파일과 똑같다):
       from config import DB_PASSWORD, NEIS_KEY
"""

# MySQL
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "여기에_자기_비밀번호"
DB_NAME = "defense_dashboard"

# 공공데이터 인증키 (쓰는 것만 채우면 된다)
DATA_GO_KR_KEY = ""      # 공공데이터포털
NEIS_KEY = ""            # 나이스 교육정보 개방포털 (학교급식)
