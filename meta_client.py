"""Public Meta Model API calls for this independent demonstration."""

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE = "https://api.meta.ai/v1"
SPARK = "muse-spark-1.3"
IMAGE = "muse-image-1.0"
MAX_RESPONSE = 20 * 1024 * 1024


class MetaError(Exception):
    pass


def key_from_environment():
    key = os.environ.get("MODEL_API_KEY", "").strip()
    if key and key != "YOUR_KEY_HERE":
        return key

    path = Path(__file__).parent / ".env"
    if path.is_file():
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError):
            raise MetaError("Cannot read .env next to app.py; save it as UTF-8 text") from None
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name, separator, value = line.partition("=")
            if separator and name.strip() == "MODEL_API_KEY":
                key = value.strip().strip("'\"")
                if key and key != "YOUR_KEY_HERE":
                    return key
                break

    if path.with_name(".env.txt").is_file():
        raise MetaError("Found .env.txt next to app.py. Rename it to .env (remove .txt).")
    if path.is_file():
        raise MetaError("Found .env next to app.py, but MODEL_API_KEY has no key value.")
    raise MetaError("Save a file named .env next to app.py in " + str(path.parent))


def media_type(data):
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise MetaError("The input is not a JPEG, PNG, or WebP image")


def webp_dimensions(data):
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise MetaError("Meta did not return a WebP image")
    if data[12:16] == b"VP8X":
        return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
    if data[12:16] == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        return int.from_bytes(data[26:28], "little") & 0x3fff, int.from_bytes(data[28:30], "little") & 0x3fff
    if data[12:16] == b"VP8L" and data[20] == 0x2f:
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
    raise MetaError("Unrecognized WebP image header")


class MetaClient:
    def __init__(self, key=None, opener=urllib.request.urlopen):
        self._key = key or key_from_environment()
        self._opener = opener

    def _post(self, path, payload):
        request = urllib.request.Request(
            BASE + path, data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + self._key, "Content-Type": "application/json"},
            method="POST")
        for attempt in range(3):
            try:
                with self._opener(request, timeout=180) as response:
                    if response.status != 200:
                        raise MetaError("Meta returned HTTP " + str(response.status))
                    request_id = response.headers.get("x-request-id", "")
                    body = response.read(MAX_RESPONSE + 1)
                break
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                raise MetaError("Meta returned HTTP " + str(exc.code)) from None
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < 2:
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                raise MetaError("Meta connection failed: " + type(exc).__name__) from None
        if len(body) > MAX_RESPONSE:
            raise MetaError("Meta response exceeded the demonstration limit")
        try:
            return json.loads(body), request_id
        except (ValueError, UnicodeDecodeError):
            raise MetaError("Meta returned an invalid JSON response") from None

    def spark(self, role, instruction, facts, images=()):
        content = [{"type": "text", "text": facts}]
        for data in images:
            if len(data) > 8 * 1024 * 1024:
                raise MetaError("Vision input exceeded 8 MiB")
            content.append({"type": "image_url", "image_url": {
                "url": "data:" + media_type(data) + ";base64," + base64.b64encode(data).decode("ascii")}})
        payload = {"model": SPARK,
                   "response_format": {"type": "json_object"},
                   "messages": [{"role": "developer", "content": instruction +
                                 " Return one JSON object only, with the requested fields."},
                                {"role": "user", "content": content}]}
        response, request_id = self._post("/chat/completions", payload)
        try:
            result = json.loads(response["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError):
            raise MetaError("Muse Spark returned an unexpected response shape") from None
        if not isinstance(result, dict):
            raise MetaError("Muse Spark did not return a JSON object")
        return result, {"model": response.get("model", SPARK), "responseId": response.get("id", ""),
                        "requestId": request_id, "usage": response.get("usage", {}), "role": role}

    def image_edit(self, source, prompt):
        if len(source) > 8 * 1024 * 1024:
            raise MetaError("Image input exceeded 8 MiB")
        payload = {"model": IMAGE, "prompt": prompt, "n": 1, "size": "1024x1024",
                   "response_format": "b64_json", "output_format": "webp",
                   "images": [{"image_url": "data:" + media_type(source) + ";base64," +
                               base64.b64encode(source).decode("ascii")}]}
        response, request_id = self._post("/images/edits", payload)
        try:
            data = base64.b64decode(response["data"][0]["b64_json"], validate=True)
        except (KeyError, IndexError, TypeError, ValueError, base64.binascii.Error):
            raise MetaError("Muse Image returned no valid image") from None
        if not data or len(data) > MAX_RESPONSE:
            raise MetaError("Muse Image output exceeded the demonstration limit")
        width, height = webp_dimensions(data)
        receipt = {"model": IMAGE, "requestId": request_id, "width": width, "height": height,
                   "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        return data, receipt
