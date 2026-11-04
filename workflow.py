"""A separately authored, local demonstration of worker, verifier, gate, effect and receipt."""

import hashlib
from pathlib import Path

from ledger import Ledger
from local_adapters import write_sample_email
from meta_client import MetaClient, MetaError, media_type


SCENES = {
    "greenhouse": "a luminous botanical greenhouse with glass arches and soft green foliage",
    "observatory": "a whimsical hilltop observatory with a brass telescope and a violet sky",
}


class RunEngine:
    def __init__(self, root, photo, meta_factory=MetaClient):
        self.root = Path(root)
        self.ledger = Ledger(self.root)
        self.photo = Path(photo)
        self.meta_factory = meta_factory

    def create(self, *, paid=True, consent=False, mode="LIVE MODEL RUN"):
        source = self.photo.read_bytes()
        media_type(source)
        if len(source) > 8 * 1024 * 1024:
            raise ValueError("The example photo exceeds 8 MiB")
        run_id = self.ledger.create(mode, consent, paid, hashlib.sha256(source).hexdigest())
        self.ledger.event(run_id, "Customer", "sample.order.created",
                          {"cardId": "CARD-1", "amountCents": 1000,
                           "payment": "local simulation", "customer": "Sample customer"})
        if paid:
            self.apply_payment(run_id, "sample-payment-" + run_id)
        else:
            self.ledger.event(run_id, "Payment simulator", "sample.payment.pending",
                              {"effect": "card work is held"})
            self.ledger.update(run_id, "payment pending")
        return run_id

    def apply_payment(self, run_id, payment_id):
        run = self.ledger.get(run_id)
        if not run:
            raise ValueError("Unknown run")
        if not run["paid"]:
            raise ValueError("The sample order is not marked paid")
        return self.ledger.effect_once(run_id, "paid:" + run_id,
                                       "sample.payment.verified",
                                       {"provider": "LOCAL SIMULATOR", "paymentId": payment_id,
                                        "amountCents": run["amount_cents"]})

    def _worker(self, meta, run_id, role, action, facts, extra=""):
        instruction = ("You are the " + role + " worker in an independently written pet-art business demo. "
                       "Use only the stated sample facts. Return JSON with action exactly '" + action +
                       "' and a short note. " + extra)
        result, receipt = meta.spark(role, instruction, facts)
        self.ledger.event(run_id, role, "meta.call.completed", receipt)
        self.ledger.event(run_id, role, "worker.proposed", result)
        if result.get("action") != action:
            raise ValueError(role + " returned an invalid action")
        return result

    def _verify(self, meta, run_id, scope, facts, images=(), required=True):
        instruction = ("You are an independent verifier in a local demonstration. "
                       "Read the supplied facts yourself, without relying on a worker's conclusion. "
                       "Return JSON with verdict exactly 'approve' or 'reject', and a short reason. "
                       "Reject when evidence is missing or contradicts the proposed action. " +
                       ("Review the actual images, including whether the result retains the same cat's "
                        "recognizable appearance and is a readable image. " if images else ""))
        result, receipt = meta.spark("Independent verifier", instruction, facts, images)
        self.ledger.event(run_id, "Independent verifier", "meta.call.completed", receipt)
        self.ledger.event(run_id, "Independent verifier", "verifier.verdict",
                          {"scope": scope, "verdict": result.get("verdict"),
                           "reason": str(result.get("reason", ""))[:500]})
        valid = result.get("verdict") == "approve"
        if required and result.get("verdict") not in ("approve", "reject"):
            raise ValueError("Verifier returned an invalid verdict")
        return valid

    def execute(self, run_id):
        run = self.ledger.get(run_id)
        if not run or not run["paid"] or run["mode"] != "LIVE MODEL RUN":
            return
        source = self.photo.read_bytes()
        try:
            meta = self.meta_factory()
            self._worker(meta, run_id, "Operations", "assign_card",
                         "A simulated payment of 1000 cents is verified for one sample card. Assign its creation.")
            self.ledger.event(run_id, "Local gate", "gate.approved",
                              {"scope": "assignment", "paid": True})
            studio = self._worker(meta, run_id, "Studio", "create_scene",
                                  "The supplied source is a Sphynx cat. Pick one scene: greenhouse or observatory. "
                                  "Return a scene field with that exact one-word value.",
                                  "Include the scene field with one allowed value: greenhouse or observatory.")
            scene = str(studio.get("scene", "")).strip().lower()
            if scene not in SCENES:
                raise ValueError("Studio selected a scene outside the public demo choices")
            prompt = ("Create a delightful editorial illustration of the SAME cat shown in the reference "
                      "photo, placed in " + SCENES[scene] + ". Keep its recognizable hairless Sphynx face "
                      "and ears. Square composition. No words, typography, plaques, logos, watermarks, "
                      "royal costumes, or greeting-card layout.")
            image, receipt = meta.image_edit(source, prompt)
            assets = self.root / "assets"
            assets.mkdir(parents=True, exist_ok=True)
            path = assets / (run_id + ".webp")
            path.write_bytes(image)
            self.ledger.update(run_id, "reviewing image", image_file=str(path))
            self.ledger.event(run_id, "Studio", "meta.image.completed", receipt)
            self.ledger.event(run_id, "Studio", "asset.created",
                              {"sha256": receipt["sha256"], "width": receipt["width"],
                               "height": receipt["height"], "scene": scene})

            reviewed = self._verify(meta, run_id, "sample delivery",
                                    "A sample paid card uses the source cat image first and the generated "
                                    "illustration second. Review the visible result before local delivery. "
                                    "The scene is " + scene + ".", (source, image))
            deliver = reviewed and self.ledger.get(run_id)["paid"] and path.is_file() and \
                hashlib.sha256(path.read_bytes()).hexdigest() == receipt["sha256"]
            self.ledger.event(run_id, "Local gate", "gate.checked",
                              {"scope": "sample delivery", "allowed": bool(deliver),
                               "pixelInputSentToVerifier": True, "assetSha256": receipt["sha256"]})
            if deliver:
                email_receipt = write_sample_email(self.root, run_id, image, receipt["sha256"])
                self.ledger.effect_once(run_id, "email:" + run_id, "sample.email.outbox.created",
                                        email_receipt)

            finance = self._worker(meta, run_id, "Finance", "reconcile_demo_payment",
                                   "Local sample: customer paid 1000 cents; simulated processing fee 59 cents; "
                                   "net is 941 cents. Record a sample reconciliation, with no real charge or refund.",
                                   "Include integer netCents in the reply.")
            latest = self.ledger.get(run_id)
            payment = next(e["detail"] for e in latest["events"] if e["kind"] == "sample.payment.verified")
            gross, fee, proposed_net = payment["amountCents"], 59, finance.get("netCents")
            finance_ok = self._verify(meta, run_id, "sample fee reconciliation",
                                      "Sample fee reconciliation. Independently loaded local ledger: " +
                                      str(gross) + " cents paid, " + str(fee) + " cents fee, "
                                      "proposed " + str(proposed_net) + " cents net. Finance proposal: " +
                                      str(finance.get("note", ""))[:300])
            finance_allowed = finance_ok and type(proposed_net) is int and gross - fee == proposed_net
            self.ledger.event(run_id, "Local gate", "gate.checked",
                              {"scope": "sample fee reconciliation", "allowed": finance_allowed})
            if finance_allowed:
                self.ledger.effect_once(run_id, "finance:" + run_id, "sample.finance.reconciled",
                                        {"provider": "LOCAL SIMULATOR", "grossCents": gross,
                                         "feeCents": fee, "netCents": proposed_net})

            care = self._worker(meta, run_id, "Customer Care", "answer_sample_question",
                                "A sample customer asks where to find their card. "
                                "The local outbox " + ("contains the card" if deliver else "is held pending visual review") + ".",
                                "Include a short reply field explaining the sample status.")
            if not isinstance(care.get("reply"), str) or not care["reply"].strip():
                raise ValueError("Customer Care returned no reply")
            self.ledger.event(run_id, "Customer Care", "sample.care.reply.prepared",
                              {"delivery": "local draft only", "reply": care["reply"][:350]})

            marketing = self._worker(meta, run_id, "Marketing", "propose_demo_post",
                                     "Prepare a short, generic sample caption for this illustrated cat. "
                                     "A post would require card sharing permission. "
                                     "This is a local simulation and will not reach any social network.",
                                     "Include a short caption field with the proposed text.")
            if not isinstance(marketing.get("caption"), str) or not marketing["caption"].strip():
                raise ValueError("Marketing returned no caption")
            latest = self.ledger.get(run_id)
            asset = next(e["detail"] for e in latest["events"] if e["kind"] == "asset.created")
            delivery_recorded = any(e["kind"] == "sample.email.outbox.created" for e in latest["events"])
            marketing_ok = self._verify(meta, run_id, "sample publication",
                                        "Marketing proposes a sample post. Independently loaded current sharing "
                                        "permission is " + ("ON" if latest["consent"] else "OFF") + ". "
                                        "A post must be rejected if sharing permission is OFF. "
                                        "Local delivery recorded: " + str(delivery_recorded) + ". "
                                        "Reviewed asset SHA-256: " + asset["sha256"] + ". "
                                        "Proposed caption: " + marketing["caption"][:200])
            latest = self.ledger.get(run_id)
            publish = (marketing_ok and latest["consent"] and
                       any(e["kind"] == "sample.email.outbox.created" for e in latest["events"]) and
                       hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"])
            self.ledger.event(run_id, "Local gate", "gate.checked",
                              {"scope": "sample publication", "allowed": bool(publish),
                               "sharingPermission": latest["consent"]})
            if publish:
                self.ledger.effect_once(run_id, "post:" + run_id, "sample.post.recorded",
                                        {"provider": "LOCAL SIMULATOR", "networkCall": False})
            else:
                self.ledger.event(run_id, "Marketing", "sample.post.withheld",
                                  {"reason": "verifier veto or local permission gate"})
            self.ledger.update(run_id, "delivered locally" if deliver else "held for review")
        except (MetaError, ValueError, OSError) as exc:
            # Provider errors are deliberately summarized; credentials and full provider bodies never enter the ledger.
            reason = str(exc)[:200]
            self.ledger.event(run_id, "System", "run.stopped", {"reason": reason})
            self.ledger.update(run_id, "stopped", error=reason)

    def create_sample(self):
        run_id = self.create(paid=True, consent=False, mode="SAMPLE REPLAY")
        self.ledger.event(run_id, "Operations", "sample.worker.proposed",
                          {"action": "assign_card", "source": "illustrative fixture"})
        self.ledger.event(run_id, "Studio", "sample.image.placeholder",
                          {"source": "illustrative fixture", "liveImageAvailableAfterKeyedRun": True})
        self.ledger.event(run_id, "Finance", "sample.finance.reconciled",
                          {"grossCents": 1000, "feeCents": 59, "provider": "illustrative fixture"})
        self.ledger.event(run_id, "Customer Care", "sample.care.reply.prepared",
                          {"delivery": "illustrative fixture"})
        self.ledger.event(run_id, "Independent verifier", "sample.verifier.verdict",
                          {"scope": "sample publication", "verdict": "reject",
                           "reason": "Sharing permission is off", "source": "illustrative fixture"})
        self.ledger.event(run_id, "Local gate", "sample.gate.checked",
                          {"scope": "publication", "allowed": False})
        self.ledger.event(run_id, "Marketing", "sample.post.withheld",
                          {"source": "illustrative fixture", "networkCall": False})
        self.ledger.update(run_id, "sample replay")
        return run_id

    def create_pack_sample(self, count):
        if count not in (3, 5):
            raise ValueError("Sample pack must contain three or five cards")
        source = self.photo.read_bytes()
        run_id = self.ledger.create("SAMPLE PACK", False, True,
                                    hashlib.sha256(source).hexdigest(), amount_cents=count * 400)
        self.ledger.event(run_id, "Customer", "sample.order.created",
                          {"cardCount": count, "amountCents": count * 400,
                           "provider": "illustrative fixture"})
        self.apply_payment(run_id, "sample-pack-payment-" + run_id)
        for slot in range(1, count + 1):
            self.ledger.event(run_id, "Studio", "sample.card.delivered",
                              {"cardId": "CARD-" + str(slot), "slotIndex": slot,
                               "source": "illustrative fixture"})
        self.ledger.effect_once(run_id, "case:" + run_id, "sample.case.needs_operator",
                                {"cardId": "CARD-2", "refundCents": 400,
                                 "reason": "illustrative card-specific defect", "provider": "LOCAL SIMULATOR"})
        self.ledger.update(run_id, "sample replay")
        return run_id

    def case(self, run_id):
        run = self.ledger.get(run_id)
        if not run or run["status"] not in ("delivered locally", "sample replay", "sample refunded"):
            raise ValueError("A finished sample card is required")
        self.ledger.effect_once(run_id, "case:" + run_id, "sample.case.needs_operator",
                                {"reason": "sample delivered file problem", "cardId": "CARD-1",
                                 "refundCents": run["amount_cents"], "provider": "LOCAL SIMULATOR"})

    def operator_refund(self, run_id, confirmed=False):
        if not confirmed:
            raise ValueError("Explicit local operator confirmation is required")
        run = self.ledger.get(run_id)
        if not run or not any(event["kind"] == "sample.case.needs_operator" for event in run["events"]):
            raise ValueError("The sample case must await an operator decision")
        case_event = next(e for e in run["events"] if e["kind"] == "sample.case.needs_operator")
        return self.ledger.operator_refund_once(run_id,
                                                {"provider": "LOCAL SIMULATOR",
                                                 "cardId": case_event["detail"]["cardId"],
                                                 "amountCents": case_event["detail"]["refundCents"],
                                                 "otherCards": "unchanged", "networkCall": False})
