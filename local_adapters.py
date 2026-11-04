"""Inspectable local effects. These adapters never contact payment, mail or social providers."""

import hashlib
from email.message import EmailMessage
from pathlib import Path


def write_sample_email(root, run_id, webp, asset_sha):
    if hashlib.sha256(webp).hexdigest() != asset_sha:
        raise ValueError("The attached image does not match the reviewed asset")
    msg = EmailMessage()
    msg["From"] = "Crown & Fluff local demo <demo@localhost.invalid>"
    msg["To"] = "Sample customer <sample@localhost.invalid>"
    msg["Subject"] = "Your illustrated cat is ready"
    msg["X-Demo-Mode"] = "LOCAL-OUTBOX-ONLY"
    msg.set_content("Your sample illustration is ready. This is a local demonstration email.\n")
    msg.add_alternative("""<!doctype html><html><body style="background:#102333;color:#f5f2eb;
        font-family:Arial,sans-serif;padding:30px;text-align:center"><h1>Your illustration is ready</h1>
        <p>The sample image is attached. This message was assembled locally and was not sent.</p>
        </body></html>""", subtype="html")
    msg.add_attachment(webp, maintype="image", subtype="webp", filename="sample-cat.webp")
    directory = Path(root) / "outbox"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (run_id + ".eml")
    data = msg.as_bytes()
    path.write_bytes(data)
    return {"provider": "LOCAL OUTBOX", "to": "Sample customer",
            "subject": str(msg["Subject"]), "attachmentSha256": asset_sha,
            "messageSha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
