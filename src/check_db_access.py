# -*- coding: utf-8 -*-
"""학원 네트워크에서 외부 DB 에 붙을 수 있는지 확인한다.

    python3 src/check_db_access.py <호스트> <포트>

예)  python3 src/check_db_access.py mysql-abc123.k.aivencloud.com 21234

★ 왜 필요한가.
   학원·회사 네트워크는 바깥으로 나가는 포트를 막아 두는 경우가 많다.
   막혀 있으면 클라우드 DB 를 쓸 수 없고, 그걸 9/17 에 알면 늦는다.

★ 결과를 어떻게 읽나.
   ① 만 되고 ② 가 막히면  → 인터넷은 되는데 그 포트만 막힌 것. 다른 포트를 시도하거나 로컬로.
   ① 부터 막히면           → 네트워크 자체 문제. 와이파이를 다시 붙어 보라.
   ② 까지 되고 ③ 이 실패   → 방화벽은 통과. 계정·비밀번호·SSL 설정 문제다.
"""
import socket
import sys

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
    print("=" * 62)
    print("① 인터넷 자체 (대조군)")
    net = tcp("www.google.com", 443, "HTTPS")
    if not net:
        print("\n   → 인터넷이 안 됩니다. 여기서 멈추세요. 와이파이부터 확인.")
        return

    if len(sys.argv) < 3:
        print("\n" + "=" * 62)
        print("② 대상 호스트를 안 줬습니다.")
        print("   Aiven 등에서 인스턴스를 먼저 만들고, 거기 적힌 Host 와 Port 로:")
        print("     python3 src/check_db_access.py <호스트> <포트>")
        print("\n   ※ Aiven 은 3306 이 아니라 2만번대 임의 포트를 줍니다.")
        print("      학원이 3306 만 막아 뒀다면 오히려 뚫릴 수 있습니다.")
        return

    host, port = sys.argv[1], sys.argv[2]

    print("\n" + "=" * 62)
    print("② 외부 DB 포트")
    if not tcp(host, port, "대상 DB"):
        print("\n   → 이 포트가 막혀 있습니다. 클라우드 DB 는 학원에서 못 씁니다.")
        print("      선택지: 다른 포트를 주는 서비스 / 학원 컴퓨터 한 대를 서버로 / 각자 로컬")
        return

    print("\n" + "=" * 62)
    print("③ 실제 로그인 (선택 — 계정을 이미 만들었을 때만)")
    try:
        import pymysql
    except ImportError:
        print("   [-] pymysql 이 없습니다.  pip install pymysql")
        return

    try:
        from config import DB_USER, DB_PASSWORD, DB_NAME
    except Exception:
        print("   [-] config.py 에 클라우드 계정을 아직 안 적었습니다. ② 까지 통과면 충분합니다.")
        return

    try:
        conn = pymysql.connect(
            host=host, port=int(port),
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME,
            charset="utf8mb4",
            ssl={"ssl": {}},          # Aiven 등은 SSL 이 필수다
            connect_timeout=TIMEOUT,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            print("   [O] 로그인 성공 — MySQL", cur.fetchone()[0])
        conn.close()
        print("\n   → 클라우드 DB 구조로 가도 됩니다.")
    except Exception as exc:
        print("   [X] 로그인 실패 —", type(exc).__name__, str(exc)[:120])
        print("      방화벽은 통과했으니 계정·비밀번호·SSL 문제입니다.")


if __name__ == "__main__":
    main()
