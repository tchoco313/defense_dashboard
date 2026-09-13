# -*- coding: utf-8 -*-
"""접속 정보 틀 — 이 파일을 복사해서 이름을 config.py 로 바꾸고 자기 값을 채운다.
   config.py 는 .gitignore 에 있어서 깃에 안 올라간다. 안심하고 적어도 된다.

   쓰는 법 (수업에서 만든 모듈 파일과 똑같다):
       from config import DB_PASSWORD, NEIS_KEY
"""

# MySQL — root 는 쓰지 않는다. 아래 두 계정을 미리 만들어 둔다 (README 「처음 받는 사람」 참고)
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "defense_dashboard"

# 데이터를 넣고 고치는 계정 — 수집·전처리 스크립트가 쓴다
DB_USER = "defense"
DB_PASSWORD = "여기에_defense_비밀번호"

# 조회만 하는 계정 — Streamlit 대시보드가 쓴다
# 권한이 SELECT 뿐이라, 대시보드 코드가 실수로 지우는 일이 애초에 안 생긴다
DASH_USER = "dash"
DASH_PASSWORD = "여기에_dash_비밀번호"

# 공공데이터 인증키 (쓰는 것만 채우면 된다)
DATA_GO_KR_KEY = ""      # 공공데이터포털
NEIS_KEY = ""            # 나이스 교육정보 개방포털 (학교급식)
