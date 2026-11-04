import json
import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path

from workflow import RunEngine


SOURCE = Path(__file__).resolve().parents[1] / "examples/meta-source.jpg"


class FakeMeta:
    calls = []
    delivery_verdict = "approve"
    publication_verdict = "reject"
    finance_net = 941

    def spark(self, role, instruction, facts, images=()):
        self.calls.append((role, facts, len(images)))
        actions = {"Operations": "assign_card", "Studio": "create_scene",
                   "Finance": "reconcile_demo_payment", "Customer Care": "answer_sample_question",
                   "Marketing": "propose_demo_post"}
        if role == "Independent verifier":
            verdict = (self.delivery_verdict if images else
                       "approve" if "fee reconciliation" in facts.lower() else self.publication_verdict)
            response = {"verdict": verdict,
                        "reason": "Sample evidence checked"}
        else:
            response = {"action": actions[role], "note": "A bounded demo proposal"}
            if role == "Studio":
                response["scene"] = "greenhouse"
            if role == "Finance":
                response["netCents"] = self.finance_net
            if role == "Customer Care":
                response["reply"] = "Your sample card is in the local outbox."
            if role == "Marketing":
                response["caption"] = "A bright day for a curious cat."
        return response, {"model": "muse-spark-1.3", "responseId": "resp_mock",
                          "requestId": "req_mock", "usage": {"total_tokens": 17}, "role": role}

    def image_edit(self, source, prompt):
        assert b"\xff\xd8\xff" in source[:3]
        assert "greenhouse" in prompt
        return b"RIFF-fake-webp", {"model": "muse-image-1.0", "requestId": "req_mock_image",
                                    "width": 1024, "height": 1024, "sha256": __import__("hashlib").sha256(
                                        b"RIFF-fake-webp").hexdigest(), "bytes": 14}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        FakeMeta.calls = []
        FakeMeta.delivery_verdict = "approve"
        FakeMeta.publication_verdict = "reject"
        FakeMeta.finance_net = 941
        self.engine = RunEngine(self.directory.name, SOURCE, meta_factory=FakeMeta)

    def events(self, run_id):
        return self.engine.ledger.get(run_id)["events"]

    def test_paid_order_runs_five_workers_and_independent_vision_review(self):
        run_id = self.engine.create(paid=True, consent=False)
        self.engine.execute(run_id)
        run = self.engine.ledger.get(run_id)
        self.assertEqual(run["status"], "delivered locally")
        self.assertEqual([c[0] for c in FakeMeta.calls].count("Independent verifier"), 3)
        self.assertIn(("Independent verifier", FakeMeta.calls[2][1], 2), FakeMeta.calls)
        self.assertEqual({c[0] for c in FakeMeta.calls if c[0] != "Independent verifier"},
                         {"Operations", "Studio", "Finance", "Customer Care", "Marketing"})
        kinds = [e["kind"] for e in run["events"]]
        self.assertIn("sample.email.outbox.created", kinds)
        self.assertIn("sample.finance.reconciled", kinds)
        self.assertIn("sample.post.withheld", kinds)
        self.assertNotIn("sample.post.recorded", kinds)
        self.assertTrue(Path(run["image_file"]).is_file())
        outbox = Path(self.directory.name) / "outbox" / (run_id + ".eml")
        message = BytesParser(policy=policy.default).parsebytes(outbox.read_bytes())
        self.assertEqual(message["X-Demo-Mode"], "LOCAL-OUTBOX-ONLY")
        attachment = next(message.iter_attachments())
        self.assertEqual(attachment.get_content_type(), "image/webp")
        self.assertEqual(attachment.get_payload(decode=True), Path(run["image_file"]).read_bytes())

    def test_permission_gate_blocks_even_if_verifier_approves(self):
        FakeMeta.publication_verdict = "approve"
        run_id = self.engine.create(paid=True, consent=False)
        self.engine.execute(run_id)
        self.assertFalse(any(e["kind"] == "sample.post.recorded" for e in self.events(run_id)))
        gate = [e for e in self.events(run_id) if e["kind"] == "gate.checked" and
                e["detail"]["scope"] == "sample publication"][0]
        self.assertFalse(gate["detail"]["allowed"])

    def test_fee_gate_rejects_a_wrong_worker_amount(self):
        FakeMeta.finance_net = 940
        run_id = self.engine.create(paid=True)
        self.engine.execute(run_id)
        self.assertNotIn("sample.finance.reconciled", [e["kind"] for e in self.events(run_id)])
        gate = next(e for e in self.events(run_id) if e["kind"] == "gate.checked" and
                    e["detail"]["scope"] == "sample fee reconciliation")
        self.assertFalse(gate["detail"]["allowed"])

    def test_consented_publication_is_local_only(self):
        FakeMeta.publication_verdict = "approve"
        run_id = self.engine.create(paid=True, consent=True)
        self.engine.execute(run_id)
        post = next(e for e in self.events(run_id) if e["kind"] == "sample.post.recorded")
        self.assertEqual(post["detail"], {"provider": "LOCAL SIMULATOR", "networkCall": False})

    def test_payment_gate_prevents_model_and_email(self):
        run_id = self.engine.create(paid=False)
        self.engine.execute(run_id)
        self.assertEqual(self.engine.ledger.get(run_id)["status"], "payment pending")
        self.assertEqual(FakeMeta.calls, [])
        self.assertFalse(any("email" in e["kind"] for e in self.events(run_id)))

    def test_verifier_veto_holds_delivery_and_all_downstream_effects(self):
        FakeMeta.delivery_verdict = "reject"
        run_id = self.engine.create(paid=True, consent=True)
        self.engine.execute(run_id)
        self.assertEqual(self.engine.ledger.get(run_id)["status"], "held for review")
        kinds = [e["kind"] for e in self.events(run_id)]
        self.assertNotIn("sample.email.outbox.created", kinds)
        self.assertNotIn("sample.post.recorded", kinds)

    def test_payment_and_operator_refund_are_idempotent(self):
        run_id = self.engine.create(paid=True)
        self.assertFalse(self.engine.apply_payment(run_id, "second-provider-event"))
        self.engine.execute(run_id)
        self.engine.case(run_id)
        self.engine.case(run_id)
        with self.assertRaisesRegex(ValueError, "confirmation"):
            self.engine.operator_refund(run_id)
        self.assertTrue(self.engine.operator_refund(run_id, confirmed=True))
        self.assertFalse(self.engine.operator_refund(run_id, confirmed=True))
        kinds = [e["kind"] for e in self.events(run_id)]
        self.assertEqual(kinds.count("sample.payment.verified"), 1)
        self.assertEqual(kinds.count("sample.case.needs_operator"), 1)
        self.assertEqual(kinds.count("sample.refund.recorded"), 1)

    def test_sample_replay_is_labeled_and_has_no_live_calls(self):
        run_id = self.engine.create_sample()
        run = self.engine.ledger.get(run_id)
        self.assertEqual(run["mode"], "SAMPLE REPLAY")
        self.assertEqual(FakeMeta.calls, [])
        self.assertTrue(all(e["kind"].startswith("sample.") or e["kind"] == "run.created"
                            for e in run["events"]))

    def test_three_and_five_card_samples_refund_only_one_child(self):
        for count in (3, 5):
            run_id = self.engine.create_pack_sample(count)
            self.assertEqual(self.engine.ledger.get(run_id)["mode"], "SAMPLE PACK")
            self.assertEqual(len([e for e in self.events(run_id) if e["kind"] == "sample.card.delivered"]),
                             count)
            self.assertTrue(self.engine.operator_refund(run_id, confirmed=True))
            refund = next(e for e in self.events(run_id) if e["kind"] == "sample.refund.recorded")
            self.assertEqual(refund["detail"]["cardId"], "CARD-2")
            self.assertEqual(refund["detail"]["amountCents"], 400)
            self.assertEqual(refund["detail"]["otherCards"], "unchanged")
            self.assertFalse(self.engine.operator_refund(run_id, confirmed=True))
        self.assertEqual(FakeMeta.calls, [])


if __name__ == "__main__":
    unittest.main()
