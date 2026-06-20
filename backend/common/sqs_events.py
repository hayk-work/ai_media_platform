import json
from typing import Any


def extract_s3_object_from_message(body: str) -> tuple[str, str] | None:
    payload = json.loads(body)
    if "Records" in payload:
        record = payload["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        return bucket, key

    detail = payload.get("detail")
    if not isinstance(detail, dict):
        return None

    bucket = detail.get("bucket", {}).get("name")
    key = detail.get("object", {}).get("key")
    if bucket and key:
        return bucket, key
    return None


def normalize_event_payload(payload: dict[str, Any]) -> tuple[str, str] | None:
    return extract_s3_object_from_message(json.dumps(payload))
