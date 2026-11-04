# Why invoice extraction is worth solving, and why accuracy is the whole game

*A business-strategy brief for the DocILE fine-tune. Market figures are third-party estimates (sources at the end);
everything labelled "measured" comes from our own test set.*

## 1. The market

**Intelligent document processing (IDP)** — software that reads documents and turns them into structured data — is one of
the fastest-growing enterprise AI categories.

| Figure | Value | Source |
| --- | --- | --- |
| IDP market, 2025 | **$10.4B** | Fortune Business Insights |
| IDP market, 2034 (forecast) | **$88.9B** | Fortune Business Insights |
| Growth rate, 2026–2034 | **26.8% CAGR** | Fortune Business Insights |
| Leading function | **Finance & accounting** | Fortune Business Insights |
| North America share, 2025 | 46% ($4.8B) | Fortune Business Insights |
| US bookkeeping, accounting & auditing clerks | **1.53M jobs** (2025), median **$24.36/hour** | US Bureau of Labor Statistics |
| Outlook for those jobs | −6% by 2035, with automation software named as the main driver | US Bureau of Labor Statistics |

Analyst estimates of IDP market size vary a lot between firms; treat the absolute numbers as directional. The direction
is not in doubt: finance and accounting is the biggest use case, and invoices are its highest-volume document.

**Who buys.** Accounts-payable (AP) teams, shared-service centres and business-process outsourcers that key in vendor
invoices, purchase orders and receipts. Their incumbent tools are OCR-plus-templates products (one template per vendor
layout) and, increasingly, LLM-based extraction.

## 2. Why this is still unsolved

**The long tail of layouts.** DocILE alone has 1,003 layout clusters in its training set. Template-based OCR needs a
template per vendor; general-purpose LLMs handle any layout but don't know each team's conventions.

**The house rules.** The hard part isn't reading text, it's knowing which text counts: the vendor's order number vs the
customer's PO, the total after commission, leaving currency blank when none is printed. Measured: base GLM 5.3 Flash
got order_id right 58% of the time and currency 66%.

**Messy inputs.** Real invoices are scans with stamps, handwriting and skew — the 1990s documents in DocILE are a fair
stress test.

## 3. Why accuracy has to be *high*, not just good

### Field accuracy compounds at the document level

A document can only skip human review if **every** field is right. Ten fields at 90% each is not "90% automated":

| System (measured, 500 test documents) | Field accuracy | Documents with all 10 fields right | Documents with ≤ 1 error | Errors per document |
| --- | --- | --- | --- | --- |
| Base GLM 5.3 Flash | 78.5% | **12.8%** | 38.6% | 2.15 |
| Best prompt (rules + OCR) | 81.1% | 18.8% | 46.2% | 1.89 |
| **Fine-tuned** | **88.4%** | **38.8%** | **70.0%** | **1.16** |

A +9.8-point gain in field accuracy is a **3× increase in fully automatable invoices**. That is why the last ten points
are worth more than the first seventy.

### Errors are asymmetric

- **A wrong amount is a wrong payment.** Measured: the fine-tune gets *both* money fields right on 84.2% of documents,
  vs 74.4% for the baseline. The rules prompt made this *worse* (63.4%) while improving other fields — prompting traded
  one error for another.
- **An invented value is worse than a blank.** A blank gets routed to a human; a confident wrong value goes straight
  into the ledger. Measured: the baseline left absent fields null only 65% of the time; the fine-tune 87%.
- **Errors are expensive downstream.** Wrong vendor, duplicate or mis-keyed invoices surface later as payment
  disputes, late fees and audit findings — far more costly than the original keystrokes.

### Accuracy is what unlocks straight-through processing

AP automation is judged by the share of invoices that flow through untouched. Every percentage point of document-level
accuracy is a point of straight-through processing, and every exception costs a human minutes.

## 4. Value, with the assumptions written out

Illustrative, for one AP team; replace the assumptions with a real team's numbers.

| Assumption | Value |
| --- | --- |
| Invoices per month | 5,000 |
| Human time to check and fix one invoice that isn't fully right | 3 minutes |
| Loaded labour rate | $24.36/hour (BLS median clerk wage, before overhead) |

| | Baseline | Fine-tune |
| --- | --- | --- |
| Invoices needing a human touch (1 − all-fields-right) | 87.2% → 4,360 | 61.2% → 3,060 |
| Human hours per month | 218 | 153 |
| **Saved** | | **~65 hours/month ≈ $1,600/month ≈ $19,000/year** |

That's per 5,000 invoices a month, before overhead, and before counting the cost of the errors that would otherwise
reach payment. The model itself is cheap: the base model cost **$0.24 for all 500 test documents** on Fireworks
serverless (about $0.0005 per invoice). Serving the fine-tune needs a dedicated deployment, which we did not measure.

## 5. Why a fine-tuned open model

- **Accuracy where it matters**: +9.8 points overall, every field better, and still +4.7 on vendor layouts it never saw.
- **Cost**: a small open model at fractions of a cent per invoice; one $36 training run.
- **Control**: open weights you own. Financial documents can stay in an environment you control.
- **A path to keep improving**: GEDD (see the README) turns AP experts' judgments on the remaining errors into an
  LLM-as-Judge gate (post / block / human review) and new training data.

## Sources

- Fortune Business Insights, *Intelligent Document Processing Market Size, Share & Industry Analysis*
  (fortunebusinessinsights.com/intelligent-document-processing-market-108590), accessed 2 Nov 2026.
- U.S. Bureau of Labor Statistics, *Occupational Outlook Handbook: Bookkeeping, Accounting, and Auditing Clerks*
  (bls.gov/ooh/office-and-administrative-support/bookkeeping-accounting-and-auditing-clerks.htm), accessed 2 Nov 2026.
- Šimsa et al., *DocILE Benchmark for Document Information Localization and Extraction*, ICDAR 2023.
- All "measured" figures: this repo, `results/*.jsonl`, 500 held-out DocILE documents.
