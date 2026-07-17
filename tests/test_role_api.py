"""Test Casdoor role resolution via HTTP.

Usage:
    Set TEST_ADMIN_JWT and TEST_COLLECTOR_JWT environment variables, then run.
    Tokens can be obtained from Zata platform after login.
"""
import json
import os
import sys
import urllib.error
import urllib.request

os.environ.setdefault("NO_PROXY", "10.9.103.101,localhost,127.0.0.1")
h = urllib.request.ProxyHandler({})
urllib.request.install_opener(urllib.request.build_opener(h))

ADMIN_JWT = os.environ.get("TEST_ADMIN_JWT", "")
COLLECTOR_JWT = os.environ.get("TEST_COLLECTOR_JWT", "")


def test(token: str, label: str) -> None:
    req = urllib.request.Request(
        'http://localhost:8080/chat',
        data=json.dumps({"message": "hello", "session_id": f"test-{label}"}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method='POST',
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        print(f"[OK] {label}: HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"[FAIL] {label}: HTTP {e.code} — {body}")
    except Exception as e:
        print(f"[ERR] {label}: {e}")


if __name__ == "__main__":
    if not ADMIN_JWT or not COLLECTOR_JWT:
        print("ERROR: 请设置环境变量 TEST_ADMIN_JWT 和 TEST_COLLECTOR_JWT")
        sys.exit(1)
    print("=== Role Resolution E2E Test ===\n")
    test(ADMIN_JWT, "admin")
    test(COLLECTOR_JWT, "collector")
    print("\n=== Done ===")
