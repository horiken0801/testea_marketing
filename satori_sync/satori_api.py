"""SATORI カスタマーバルクAPI v4（upsert）のクライアント。

APIキーは環境変数から読み込む（リポジトリには保存しない）:
  SATORI_USER_KEY, SATORI_USER_SECRET, SATORI_COMPANY_KEY, SATORI_COMPANY_SECRET

仕様: https://satorihelp.zendesk.com/hc/ja/articles/360000796993
  - upsert は未登録のメールアドレスを新規登録してしまうため、呼び出し側で既存カスタマーだけに絞ること
  - 空欄の値は既存の値を上書きしない
  - 1リクエスト 10,000件まで
"""

import csv
import io
import json
import os
import time
import urllib.parse
import urllib.request
import uuid

BASE_URL = "https://api.satr.jp/api/v4/public/bulk_customers"
MAX_ROWS = 10000
ENV_KEYS = {
    "user_key": "SATORI_USER_KEY",
    "user_secret": "SATORI_USER_SECRET",
    "company_key": "SATORI_COMPANY_KEY",
    "company_secret": "SATORI_COMPANY_SECRET",
}


def load_credentials():
    missing = [env for env in ENV_KEYS.values() if not os.environ.get(env)]
    if missing:
        raise SystemExit("SATORIのAPIキーが環境変数に設定されていません: " + ", ".join(missing))
    return {param: os.environ[env] for param, env in ENV_KEYS.items()}


def build_csv(header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([row.get(h, "") for h in header])
    return buf.getvalue().encode("utf-8")


def _multipart(fields, file_field, file_name, file_bytes):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{file_name}"\r\n'
        f"Content-Type: text/csv\r\n\r\n".encode() + file_bytes + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _request(req):
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"SATORI APIエラー: HTTP {e.code} {e.read().decode('utf-8', 'replace')}")


def upsert(credentials, csv_bytes):
    fields = dict(credentials, identity_type="email")
    body, content_type = _multipart(fields, "customer_csv_file", "customers.csv", csv_bytes)
    req = urllib.request.Request(f"{BASE_URL}/upsert.json", data=body, method="POST",
                                 headers={"Content-Type": content_type})
    return _request(req)


def status(credentials, process_code):
    query = urllib.parse.urlencode(dict(credentials, process_code=process_code))
    return _request(urllib.request.Request(f"{BASE_URL}/status.json?{query}", method="GET"))


def extract_process_code(response):
    message = response.get("message")
    if isinstance(message, dict):
        return message.get("process_code")
    return response.get("process_code")


def upsert_and_wait(credentials, header, rows, poll_interval=10, timeout=1800):
    """rows を 10,000件ずつ upsert し、処理完了まで待って結果のリストを返す。"""
    results = []
    for start in range(0, len(rows), MAX_ROWS):
        chunk = rows[start:start + MAX_ROWS]
        response = upsert(credentials, build_csv(header, chunk))
        process_code = extract_process_code(response)
        if not process_code:
            raise SystemExit(f"SATORI APIの応答にprocess_codeがありません: {response}")
        print(f"送信しました: {len(chunk)}件 (process_code={process_code})")

        deadline = time.time() + timeout
        while True:
            result = status(credentials, process_code)
            message = result.get("message", result)
            if isinstance(message, dict) and message.get("process_status") == "finished":
                results.append(message)
                break
            if time.time() > deadline:
                raise SystemExit(f"処理完了を待ちきれませんでした (process_code={process_code})")
            time.sleep(poll_interval)
    return results
