# LocalLedger 0.1.0

Local household spending dashboard using your Ollaborate 0.1.0 and LibreIndex 0.1.0 source packages (bundled with their original licences). Python 3.11+.

## Run

Extract the archive, open a terminal in `LocalLedger`, then:

```sh
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501. Install Ollama separately, then download local models:

```sh
ollama pull qwen3:8b
ollama pull embeddinggemma
```

Use a smaller local model if memory is limited. Imports, charts and transfer review work without Ollama. Dependencies and model downloads require internet initially; inference uses a fixed loopback Ollama endpoint. Do not enter a cloud model name. No bank login or cloud inference is implemented.

## Workflow

1. Add accounts for each person, including savings and credit cards. Opening balances must precede the earliest imported transaction; a credit-card liability is negative.
2. Import UTF-8 CSV exports with a signed amount column. Map columns, date format, delimiter and decimal separator. Incoming is positive, outgoing negative. Review the preview first. Use stable bank transaction IDs where available.
3. Review Transfers. Equal opposite amounts in distinct accounts with the same currency and within three days are suggestions only. Confirm actual internal movements. Manual matching handles other booking dates, including different months. Undo is available.
4. Assign categories; optionally remember exact merchant descriptions. Ollaborate suggestions require manual acceptance.
5. View household or person aggregates and graphs. Refunds should be classified as Refund to reduce expenses rather than inflate income.
6. Ask Ollaborate to explain the verified summary. Inspect source transaction IDs. Upload supporting documents and explicitly index them with LibreIndex for separate cited document questions.

## Accounting behaviour and scope

Confirmed transfers never contribute to monthly income or expenses, even when the legs occur in different months. Both legs remain in each account balance. Person views also exclude confirmed household transfers: they describe external income/expenses, not settlement between family members. No transfer is inferred from model output.

Credit-card repayments are internal transfers only when both bank and card accounts are imported. Include the original card purchases to capture expenses. Missing counterpart accounts cause incomplete household coverage. Opening balances and imported coverage determine balances; the app does not reconcile against bank closing balances or report net worth.

Currencies are strictly separated: no FX conversions or combined cross-currency totals. Split transfer fees into separate expense records before matching; unequal or cross-currency transfers are not supported. Unconfirmed transfers affect totals. Zero amounts have no financial effect.

CSV import is atomic: a bad row cancels the import. Bank IDs deduplicate within each account. Without IDs the app fingerprints date, description, amount and occurrence count: this handles identical reimports and legitimate repeated rows, but differing overlapping exports can still require review. Transaction deletion/editing and import rollback are not yet implemented; back up the database before large imports.

Document retrieval is not a transaction importer. Text-based PDFs are supported by LibreIndex; scans need external OCR. Document answers and model explanations may be inaccurate; verified ledger tables are authoritative.

## Privacy and backup

Everything is stored under `data/` beside the app: `ledger.sqlite3`, documents and the document index. These files are not encrypted by the app; use OS disk encryption and protect backups. Shut down the app before copying `data/`. The app is intended for one local user/session, not a public server. It never executes model-generated SQL or tools. Streamlit telemetry is disabled in the supplied launch command.

## Verification

```sh
python -m unittest discover -s tests -v
```

Financial tests cover cross-month transfers, person views, balances, undo, currencies, duplicate imports, atomic failure, refunds, Swedish numbers and remembered categories. The package includes a fictional demonstration household. Live Ollama inference depends on your local installation and downloaded models.

References: https://docs.ollama.com/capabilities/structured-outputs and https://docs.streamlit.io/.
