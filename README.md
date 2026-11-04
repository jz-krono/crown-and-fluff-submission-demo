# Crown & Fluff · executable operating demo

**Five workers. An independent verifier. One inspectable Recorder.**

## Judge quick start

This repository is an executable, local demonstration of the operating loop behind [Crown & Fluff](https://cf.kronowave.com/). The product and submission film show the finished branded cards. This repo transforms the supplied Sphynx photo into a **generic illustration** and records the model calls, independent reviews, and local effects.

1. Open a terminal, clone this repository, and enter its folder. On Windows PowerShell, use `python`; on macOS/Linux, use `python3`.
2. Put **your own Meta Model API key** in a file named `.env` **beside `app.py`**. The file must contain this exact assignment on one line: `MODEL_API_KEY=your_actual_key`. Replace the example value with your key. The key stays on your machine and `.env` is Git ignored.
3. Start the app from that folder, open [http://127.0.0.1:8765](http://127.0.0.1:8765), and click **Start live Meta run · veto example**.
4. Select the new **LIVE MODEL RUN** in the Recorder. The original photo appears immediately; the generated WebP appears beside it after Muse Image finishes. **Allow several minutes** for the sequential model calls. The page refreshes automatically.
5. Scroll through the touchpoints. Open **Inspect receipt** on the `meta.call.completed`, `meta.image.completed`, and `verifier.verdict` entries to see model IDs, response references, usage, and decisions. The default run starts with sharing off, so the publication proposal is withheld. An approved image review assembles a downloadable **local** email with the generated WebP attached.

**Windows PowerShell**, from any folder where you want the clone:

```powershell
git clone https://github.com/jz-krono/crown-and-fluff-submission-demo.git
cd .\crown-and-fluff-submission-demo
Copy-Item .env.example .env
notepad .env
# Replace YOUR_KEY_HERE in the existing MODEL_API_KEY= line, then save and close Notepad.
python app.py
```

**macOS/Linux**:

```bash
git clone https://github.com/jz-krono/crown-and-fluff-submission-demo.git
cd crown-and-fluff-submission-demo
cp .env.example .env
# Edit .env: replace YOUR_KEY_HERE in the existing MODEL_API_KEY= line with your own key.
python3 app.py
```

The **Open sample replay · no key** button is a labeled fixture for exploring the Recorder; it does not call Meta or generate an image. Payment, email delivery, publishing, and refunds are local simulations in this repo. The private Crown & Fluff production system and its branded image recipes are separate.

## Project and technical details

Kronowave built Crown & Fluff as a functioning pet-card business during the Meta Global AI Developer Hackathon. The [live product](https://cf.kronowave.com/) and submission film show its customer experience and finished art. This separate repository lets a judge run an intelligible slice of its operating pattern locally: a simulated paid event starts the work; five role-scoped Muse Spark calls work on a sample card; Muse Image edits the supplied cat photograph into a **generic illustrated environment**; independent Muse Spark calls review consequential actions; local gates record the observed outcome; the Recorder displays each touchpoint.

The demonstration's prompts and visuals were newly written for this repo. The generated image has no Crown & Fluff greeting, typography, watermark, or production scene recipe. The production harness, card compositor, private agent instructions, cloud infrastructure, customers, and provider credentials remain in Kronowave's private systems.

## Additional local notes

Python 3.10+ is required; no package installation or cloud account is needed. If `python` is unavailable in PowerShell, use `py -3 app.py`. Run `python -m unittest discover -s tests -v` (or `python3` on macOS/Linux) for the local tests.

The live path makes five role-scoped Muse Spark worker calls, three independent Muse Spark verifier calls (including a visual review of the source and generated **image bytes**), and one Muse Image edit. Each click creates a new run and may incur your Model API usage charges. **Run with sharing approved** exercises the alternate local publication branch. The actual returned WebP dimensions are recorded in the image receipt.

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
