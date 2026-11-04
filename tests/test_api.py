import base64
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from app import Handler
from meta_client import MetaClient, MetaError, webp_dimensions
from workflow import RunEngine


class Response:
    status = 200
    headers = {"x-request-id": "req_meta"}

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, *_):
        return self.payload


class ApiTests(unittest.TestCase):
    def test_tracked_key_example_stays_a_placeholder(self):
        root = Path(__file__).resolve().parents[1]
        example = (root / ".env.example").read_text()
        self.assertEqual([line for line in example.splitlines() if line.startswith("MODEL_API_KEY=")],
                         ["MODEL_API_KEY=YOUR_KEY_HERE"])
        self.assertIn(".env", (root / ".gitignore").read_text().splitlines())

    def test_meta_calls_have_correct_models_visual_inputs_and_receipts(self):
        requests = []
        webp = b"RIFF" + b"\x00" * 4 + b"WEBPVP8X" + b"\x00" * 8 + \
               (63).to_bytes(3, "little") + (79).to_bytes(3, "little")

        def opener(request, timeout):
            requests.append((request.full_url, json.loads(request.data), request.get_header("Authorization")))
            if request.full_url.endswith("/chat/completions"):
                return Response({"id": "chat_123", "model": "muse-spark-1.3",
                                 "choices": [{"message": {"content": '{"verdict":"reject","reason":"No sharing permission"}'}}],
                                 "usage": {"total_tokens": 23}})
            return Response({"data": [{"b64_json": base64.b64encode(webp).decode()}]})

        client = MetaClient(key="test-key-in-memory", opener=opener)
        answer, receipt = client.spark("Independent verifier", "Review sharing", "Permission off", [b"\xff\xd8\xffabc"])
        image, image_receipt = client.image_edit(b"\xff\xd8\xffabc", "A generic scene")
        self.assertEqual(answer["verdict"], "reject")
        self.assertEqual(receipt["responseId"], "chat_123")
        self.assertEqual(receipt["usage"]["total_tokens"], 23)
        self.assertEqual(image, webp)
        self.assertEqual((image_receipt["width"], image_receipt["height"]), (64, 80))
        self.assertEqual(requests[0][0], "https://api.meta.ai/v1/chat/completions")
        self.assertEqual(requests[0][1]["model"], "muse-spark-1.3")
        self.assertEqual(requests[0][1]["messages"][1]["content"][1]["type"], "image_url")
        self.assertEqual(requests[1][1]["model"], "muse-image-1.0")
        self.assertEqual(requests[1][1]["response_format"], "b64_json")
        self.assertEqual(requests[1][1]["size"], "1024x1024")
        self.assertEqual(requests[0][2], "Bearer test-key-in-memory")
        self.assertNotIn("test-key-in-memory", json.dumps(receipt) + json.dumps(image_receipt))

    def test_loopback_app_serves_labeled_replay_and_blocks_other_origins(self):
        with tempfile.TemporaryDirectory() as directory:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            server.engine = RunEngine(directory, Path(__file__).resolve().parents[1] / "examples/meta-source.jpg")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            try:
                with urlopen(base + "/") as response:
                    self.assertIn(b"Business Recorder", response.read())
                request = Request(base + "/api/runs", data=b'{"kind":"sample"}',
                                  headers={"Content-Type": "application/json", "Origin": base}, method="POST")
                with urlopen(request) as response:
                    run_id = json.load(response)["id"]
                with urlopen(base + "/api/runs/" + run_id) as response:
                    self.assertEqual(json.load(response)["mode"], "SAMPLE REPLAY")
                wrong = Request(base + "/api/runs", data=b'{"kind":"sample"}',
                                headers={"Content-Type": "application/json", "Origin": "https://other.example"},
                                method="POST")
                with self.assertRaisesRegex(Exception, "403"):
                    urlopen(wrong)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
