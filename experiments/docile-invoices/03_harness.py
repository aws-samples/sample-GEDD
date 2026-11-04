"""Step 3: prompt-only ideas on base GLM 5.3 Flash, same test set, temperature 0.

A (glm_rules): spell out the annotation conventions the baseline gets wrong (only what is printed, which order number).
B (glm_rules_ocr): A plus DocILE's pre-computed OCR text of page 1, in reading order.
"""
import asyncio
import json
import sys

import dl_common as d

RULES = """
Rules:
- Only extract what is literally printed on this page. Never infer or assume a value.
- currency_code_amount_due: only if a currency symbol or code (e.g. $, USD, EUR) is printed next to the amount due or total; otherwise null. Return the ISO code.
- order_id: the purchase order / order number referenced on the document. If the only number is the document's own invoice number, use null.
- document_id: the number that identifies this document (invoice no., order no. of an order form, receipt no.).
- vendor_name: the company issuing the document, usually in the letterhead or 'remit to'. customer_billing_name: the company being billed ('bill to', 'sold to').
- amount_total_gross: the total including tax. amount_due: the amount the customer must pay. Use null if not printed.
- date_due: only if an explicit due date is printed; do not compute it from payment terms.
"""


def ocr_text(docid: str, max_chars: int = 6000) -> str:
    ocr = json.loads((d.DATA / "ocr" / f"{docid}.json").read_text())
    words = []
    for block in ocr["pages"][0]["blocks"]:
        for line in block["lines"]:
            words.append(" ".join(w["value"] for w in line["words"]))
    return "\n".join(words)[:max_chars]


def messages_rules(r):
    m = d.messages(r)
    m[1]["content"][1]["text"] = d.PROMPT.replace("\n\nAnswer with only", RULES + "\nAnswer with only")
    return m


def messages_rules_ocr(r):
    m = messages_rules(r)
    m[1]["content"][1]["text"] = f"OCR text of the page (may contain errors):\n{ocr_text(r['id'])}\n\n" + m[1]["content"][1]["text"]
    return m


VARIANTS = {"glm_rules": messages_rules, "glm_rules_ocr": messages_rules_ocr}

if __name__ == "__main__":
    for tag in sys.argv[1:] or VARIANTS:
        asyncio.run(d.eval_model("glm", tag, build_messages=VARIANTS[tag], concurrency=12))
