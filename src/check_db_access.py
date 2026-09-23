# -*- coding: utf-8 -*-
"""팀 DB 에 붙을 수 있는지 세 단계로 확인한다.

    python3 src/check_db_access.py              # config.py 에 적힌 서버로
    python3 src/check_db_access.py <호스트> <포트>   # 다른 서버를 시험할 때

★ 왜 필요한가.
   "안 돼요" 에는 원인이 세 가지나 있다 — 네트워크, 서버, 계정.
   어디서 막혔는지 모르면 엉뚱한 데를 고치게 된다. 이 스크립트가 그걸 갈라 준다.

★ 결과를 어떻게 읽나.
   ① 부터 막히면        → 인터넷 자체가 안 된다. 와이파이부터 확인.
   ① 만 되고 ② 가 막히면 → 서버에 못 닿는다. DB 는 AWS RDS 라 어디서든 열려 있어야 한다.
                           config.py 의 DB_HOST(엔드포인트)를 잘못 적었거나,
                           RDS 보안그룹이 내 접속을 막는 것이다 — 조장에게 알린다.
   ② 까지 되고 ③ 이 실패 → 네트워크는 통과. config.py 의 계정·비밀번호 문제다.
"""
import os
import socket
import sys

# config.py 는 저장소 맨 위에 있다. src/ 에서 실행해도 찾도록 경로를 더한다
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TIMEOUT = 6


def tcp(host, port, label):
    """TCP 로 붙을 수 있는지만 본다. 로그인은 하지 않는다."""
    try:
        with socket.create_connection((host, int(port)), timeout=TIMEOUT):
            print("   [O] %-22s %s:%s" % (label, host, port))
            return True
    except Exception as exc:
        print("   [X] %-22s %s:%s  — %s" % (label, host, port, type(exc).__name__))
        return False


def main():
    try:
        import config
    except Exception:
        print("   [X] config.py 가 없습니다.  cp config_example.py config.py 부터 하세요.")
        return

    # 인자를 주면 그걸 쓰고, 없으면 config.py 에 적힌 팀 서버를 본다
    if len(sys.argv) >= 3:
        host, port = sys.argv[1], sys.argv[2]
    else:
        host, port = config.DB_HOST, config.DB_PORT

    print("=" * 62)
    print("① 인터넷 자체 (대조군)")
    if not tcp("www.google.com", 443, "HTTPS"):
        print("\n   → 인터넷이 안 됩니다. 여기서 멈추세요. 와이파이부터 확인.")
        return

    print("\n" + "=" * 62)
    print("② 팀 DB 서버 포트")
    if not tcp(host, port, "팀 DB"):
        print("\n   → 서버에 못 닿습니다. RDS 는 어디서든 열려 있어야 합니다.")
        print("      · config.py 의 DB_HOST(엔드포인트)를 다시 확인하세요")
        print("      · 엔드포인트가 맞는데 막히면 RDS 보안그룹 문제입니다 — 조장에게 알리세요")
        return

    print("\n" + "=" * 62)
    print("③ 실제 로그인")
    try:
        import pymysql
    except ImportError:
        print("   [-] pymysql 이 없습니다.  pip install -r requirements.txt")
        return

    # DB_SSL 은 config.py 가 정한다. RDS 는 True 다
    ssl_opt = {"ssl": {}} if getattr(config, "DB_SSL", False) else None
    try:
        conn = pymysql.connect(
            host=host, port=int(port),
            user=config.DB_USER, password=config.DB_PASSWORD, database=config.DB_NAME,
            charset="utf8mb4",
            ssl=ssl_opt,
            connect_timeout=TIMEOUT,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION(), @@hostname")
            ver, name = cur.fetchone()
            print("   [O] %s 로 로그인 성공 — MySQL %s @ %s" % (config.DB_USER, ver, name))
        conn.close()
        print("\n   → 다 통과했습니다. 그대로 작업하면 됩니다.")
    except Exception as exc:
        print("   [X] 로그인 실패 —", type(exc).__name__, str(exc)[:120])
        print("      서버까지는 닿았으니 config.py 의 계정·비밀번호 문제입니다.")


if __name__ == "__main__":
    main()
