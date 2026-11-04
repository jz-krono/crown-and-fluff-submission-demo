# Crown & Fluff · executable operating demo

**Five workers. An independent verifier. One inspectable Recorder.**

Kronowave built Crown & Fluff as a functioning pet-card business during the Meta Global AI Developer Hackathon. The [live product](https://cf.kronowave.com/) and submission film show its customer experience and finished art. This separate repository lets a judge run an intelligible slice of its operating pattern locally: a simulated paid event starts the work; five role-scoped Muse Spark calls work on a sample card; Muse Image edits the supplied cat photograph into a **generic illustrated environment**; independent Muse Spark calls review consequential actions; local gates record the observed outcome; the Recorder displays each touchpoint.

The demonstration's prompts and visuals were newly written for this repo. The generated image has no Crown & Fluff greeting, typography, watermark, or production scene recipe. The production harness, card compositor, private agent instructions, cloud infrastructure, customers, and provider credentials remain in Kronowave's private systems.

## Run locally

Python 3.10+; no package installation, AWS account, payment account, or email service is needed.

**Windows PowerShell** (including an active Conda environment):

```powershell
git clone https://github.com/jz-krono/crown-and-fluff-submission-demo.git
cd .\crown-and-fluff-submission-demo
python --version
python -m unittest discover -s tests -v
python app.py
```

If `python` is unavailable in PowerShell, use `py -3` for the two Python commands.

**macOS / Linux:**

```bash
git clone https://github.com/jz-krono/crown-and-fluff-submission-demo.git
cd crown-and-fluff-submission-demo
python3 -m unittest discover -s tests -v
python3 app.py
```

Open **http://127.0.0.1:8765**. Click **Open sample replay**, **Show payment gate**, **Three-card sample**, or **Five-card sample** to explore without a key. Replays are visibly marked **SAMPLE REPLAY** or **SAMPLE PACK**; their example verdicts and pack prices are illustrative and make no Meta call.

For an actual Muse run, create a Meta **Model API** key at [dev.meta.ai](https://dev.meta.ai/), then either set it in the shell or copy `.env.example` to `.env` and replace `YOUR_KEY_HERE` **in `.env` only**. The tracked `.env.example` must keep its placeholder:

```bash
export MODEL_API_KEY='your-own-model-api-key'
python3 app.py
```

In Windows PowerShell, run `Copy-Item .env.example .env`, then open `.env` locally and replace its placeholder with your key. The optional `.env` stays local and is ignored by Git. Delete `.env` or unset the variable when your review is complete. **Never paste a key into GitHub, the app's browser screen, an issue, or a submission form.**

Click **Start live Meta run · veto example**. The run makes five role-scoped Muse Spark calls (Operations, Studio, Finance, Customer Care, Marketing), three independent Muse Spark verifier calls (visual delivery review, fee review, and publication review), and one Muse Image edit. The image call can take several minutes; the Recorder updates as results arrive. The verifier receives the source and generated **image bytes** for the delivery review. Sharing permission starts off, so the publication proposal must be held by the verifier and/or local permission gate. **Run with sharing approved** exercises the allowed local publication branch. The same Meta key is used only in the server process for outbound API calls; it is not sent to the browser or stored in the Recorder.

This makes actual Meta API calls and may incur your Model API usage charges. Each click creates a fresh run. Muse Image interprets the requested `1024x1024` as an aspect ratio; the Recorder records the actual returned WebP dimensions.

## What the Recorder proves

| Layer | Live local run | External product proof |
| --- | --- | --- |
| Worker | Muse Spark response ID, model, usage, bounded proposal | Five governed role scopes in the production product |
| Verifier | Separate Muse Spark call and verdict, including visual input on the image review | Independently recorded production verdicts |
| Gate | Current local paid, asset-hash, and sharing checks | Production adapters have separate controls |
| Effect | Local payment, email outbox, publication, and refund receipts | Stripe TEST, SES, and social outcomes shown in the submission film |

**Payment and external effects are simulations in this repo.** A local paid event enables the card workflow; the pending-payment example holds it. Email assembles a downloadable `.eml` with the actual reviewed WebP attached and records an inspectable local outbox receipt; it sends no message to a person. Publishing records a local result, not an Instagram/X post. A sample problem report can enter a local case; an explicit button confirmation is required before a local refund receipt. Three- and five-card replays show a single affected child while other cards stay unchanged. Repeating the payment event or refund returns the same recorded effect. This single-user localhost button illustrates the human decision path; production operator authentication remains in the private deployment.

The **Production proof** panel contains aggregate redacted **TEST** operating figures, separately sourced from the private architecture snapshot. These are not live customer revenue or outcomes generated by this local demo. The video and public site show the product itself.

## File map

| File | Purpose |
| --- | --- |
| `app.py`, `web/` | Loopback-only app and responsive Recorder. |
| `workflow.py`, `ledger.py`, `local_adapters.py` | Fresh local worker flow, state checks, idempotent effects, SQLite event history, inspectable MIME email. |
| `meta_client.py` | Direct `muse-spark-1.3` chat completions and `muse-image-1.0` image edit calls. |
| `examples/meta-source.jpg` | The supplied Sphynx cat input photo. |
| `evidence/test-summary.json` | Aggregate TEST evidence, with distinct provenance. |
| `tests/` | Reproducible local success, veto, payment, duplicate, refund, and API checks. |
| `NOTICE.md`, `.env.example`, `.gitignore` | Ownership and key/output handling. |

The local state and generated WebPs are under ignored `.local/`. Delete that folder to reset the demo. `python3 app.py --port 8888` selects another local port.

© 2026 Kronowave, Inc. All rights reserved. See [NOTICE.md](NOTICE.md).
