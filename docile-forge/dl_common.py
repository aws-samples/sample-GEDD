"""DocILE key-field extraction: data, prompt, parsing, normalisation, grading and a cached async eval.

Task: given page 1 of a business document as an image, return JSON with 10 key fields (null if absent).
Each (document, field) pair is one pass/fail case. Bootstrap groups = DocILE layout clusters.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import subprocess
import time
from pathlib import Path

from dateutil import parser as dateparser
from dotenv import load_dotenv
from PIL import Image

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")
DATA = HERE / "data" / "docile"
CACHE = HERE / "cache"
SPLITS = HERE / "splits"
RESULTS = HERE / "results"

DPI = 150          # render resolution for page images
# Longest side sent to the model, px. Training used 1600; the serverless sampler caps one image at 2,048 tokens,
# so scoring the fine-tune (and its matched baseline) uses DOCILE_MAX_SIDE=1344.
MAX_SIDE = int(os.environ.get("DOCILE_MAX_SIDE", "1600"))
MAX_PIXELS = 1_450_000  # ~2,000 image tokens for GLM 5.3 Flash
IMAGES = CACHE / (f"images_{MAX_SIDE}" if MAX_SIDE != 1600 else "images")

# The 10 most common single-answer DocILE KILE fieldtypes, with the description shown to the model.
FIELDS = {
    "document_id": "invoice / order / document number",
    "date_issue": "date the document was issued",
    "date_due": "payment due date",
    "vendor_name": "name of the vendor / supplier / seller",
    "customer_billing_name": "name of the customer being billed",
    "order_id": "order number (purchase order / sales order) referenced on the document",
    "payment_terms": "payment terms, e.g. 'Net 30'",
    "amount_total_gross": "total amount including tax",
    "amount_due": "amount due / balance to pay",
    "currency_code_amount_due": "currency of the amount due as an ISO code, e.g. USD",
}
AMOUNTS = {"amount_total_gross", "amount_due"}
DATES = {"date_issue", "date_due"}

SYSTEM = "You are an accounts-payable assistant that reads scanned business documents and extracts key fields."
PROMPT = (
    "Extract these fields from the document image. Copy values exactly as printed. "
    "Use null for any field that is not on the page.\n\n"
    + "\n".join(f"- {k}: {v}" for k, v in FIELDS.items())
    + "\n\nAnswer with only a JSON object with exactly these keys."
)

MODELS = {
    # price = serverless inference USD per 1M (input, output) tokens
    "glm": {"label": "GLM 5.3 Flash", "model": "accounts/fireworks/models/glm-5p3-flash", "host": "fireworks", "price": (0.15, 0.50)},
    # Frontier baselines via OpenRouter (billed to OPENROUTER_API_KEY, not Fireworks); same prompt, temperature 0.
    "gemini4": {"label": "Gemini 4 Argon", "model": "google/gemini-4-argon", "host": "openrouter", "price": (2.00, 10.00)},
    "opus55": {"label": "Claude Opus 5.5", "model": "anthropic/claude-opus-5.5", "host": "openrouter", "price": (4.00, 20.00)},
    "gpt61": {"label": "GPT-6.1 Terra Pro", "model": "openai/gpt-6.1-terra-pro", "host": "openrouter", "price": (1.00, 5.00)},
}


# ---------- data ----------

def annotation(docid: str) -> dict:
    return json.loads((DATA / "annotations" / f"{docid}.json").read_text())


def gold_fields(ann: dict, page: int = 0) -> dict[str, list[str]]:
    """All labelled texts per field on the given page (a field can be printed several times)."""
    out = {k: [] for k in FIELDS}
    for f in ann["field_extractions"]:
        if f["fieldtype"] in FIELDS and f["page"] == page and f.get("text"):
            out[f["fieldtype"]].append(f["text"])
    return out


def build_splits() -> dict:
    SPLITS.mkdir(exist_ok=True)
    counts = {}
    for name, src in (("test", "val"), ("train", "train")):
        rows = []
        for docid in json.loads((DATA / f"{src}.json").read_text()):
            a = annotation(docid)
            m = a["metadata"]
            rows.append({"id": docid, "cluster": m["cluster_id"], "doc_type": m["document_type"],
                         "pages": m["page_count"], "gold": gold_fields(a)})
        (SPLITS / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        counts[name] = len(rows)
    train_clusters = {r["cluster"] for r in load_split("train")}
    test = load_split("test")
    for r in test:
        r["unseen_layout"] = r["cluster"] not in train_clusters
    (SPLITS / "test.jsonl").write_text("".join(json.dumps(r) + "\n" for r in test))
    counts["test_unseen_layout"] = sum(r["unseen_layout"] for r in test)
    return counts


def load_split(split: str) -> list[dict]:
    return [json.loads(l) for l in (SPLITS / f"{split}.jsonl").read_text().splitlines() if l.strip()]


def image_path(docid: str) -> Path:
    out = IMAGES / f"{docid}.png"
    if not out.exists():
        IMAGES.mkdir(parents=True, exist_ok=True)
        stem = IMAGES / f"{docid}.tmp"
        subprocess.run(["pdftoppm", "-r", str(DPI), "-f", "1", "-l", "1", "-singlefile", "-png",
                        str(DATA / "pdfs" / f"{docid}.pdf"), str(stem)], check=True)
        img = Image.open(f"{stem}.png").convert("L")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        if MAX_SIDE != 1600 and img.width * img.height > MAX_PIXELS:  # keep near-square pages under the token cap
            k = (MAX_PIXELS / (img.width * img.height)) ** 0.5
            img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
        img.save(out, optimize=True)
        Path(f"{stem}.png").unlink()
    return out


def image_url(docid: str) -> str:
    buf = io.BytesIO(image_path(docid).read_bytes())
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def messages(r: dict) -> list[dict]:
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url(r["id"])}},
                                         {"type": "text", "text": PROMPT}]}]


def target_json(r: dict) -> str:
    """SFT target: first labelled instance of each field, null if absent."""
    return json.dumps({k: (v[0] if v else None) for k, v in r["gold"].items()}, ensure_ascii=False)


# ---------- parsing and normalisation ----------

def parse(text: str) -> dict | None:
    t = re.sub(r"<think>[\s\S]*?</think>", "", text or "")
    t = re.sub(r"```(?:json)?", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


CURRENCY = {"$": "USD", "us$": "USD", "usd": "USD", "dollars": "USD", "us dollars": "USD", "€": "EUR", "eur": "EUR",
            "euro": "EUR", "£": "GBP", "gbp": "GBP", "¥": "JPY", "jpy": "JPY", "cad": "CAD", "c$": "CAD",
            "chf": "CHF", "aud": "AUD", "a$": "AUD", "inr": "INR", "₹": "INR"}


def norm_text(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", str(s).casefold())


def norm_amount(s: str) -> float | None:
    t = re.sub(r"[^0-9.,\-]", "", str(s))
    if not re.search(r"\d", t):
        return None
    if re.search(r",\d{2}$", t) and "." not in t[-3:]:   # 1.234,56 style
        t = t.replace(".", "").replace(",", ".")
    t = t.replace(",", "")
    try:
        return round(abs(float(t.strip("-").rstrip("."))), 2)
    except ValueError:
        return None


def norm_date(s: str):
    try:
        return dateparser.parse(str(s), fuzzy=True, default=None).date()
    except (ValueError, OverflowError, TypeError, AttributeError):
        return None


def norm_currency(s: str) -> str:
    t = str(s).strip().casefold()
    return CURRENCY.get(t, CURRENCY.get(re.sub(r"[^a-z$€£¥₹]", "", t), t.upper()))


def is_null(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip().casefold() in {"", "null", "none", "n/a", "na", "-"})


def match(field: str, pred, golds: list[str]) -> bool:
    if not golds:
        return is_null(pred)
    if is_null(pred):
        return False
    if isinstance(pred, (list, dict)):
        return False
    pred = str(pred)
    # Some labels span several printed lines (e.g. a name block); a single line of it also counts.
    golds = golds + [line for g in golds if "\n" in g for line in g.splitlines() if line.strip()]
    for g in golds:
        if norm_text(pred) and norm_text(pred) == norm_text(g):
            return True
        if field in AMOUNTS and norm_amount(pred) is not None and norm_amount(pred) == norm_amount(g):
            return True
        if field in DATES and norm_date(pred) is not None and norm_date(pred) == norm_date(g):
            return True
        if field == "currency_code_amount_due" and norm_currency(pred) == norm_currency(g):
            return True
    return False


def grade(r: dict, pred: dict | None) -> list[dict]:
    """One pass/fail row per field."""
    pred = pred or {}
    return [{"id": f"{r['id']}-{k}", "doc": r["id"], "field": k, "cluster": r["cluster"],
             "unseen_layout": r.get("unseen_layout", False), "present": bool(r["gold"][k]),
             "gold": r["gold"][k][:3], "pred": pred.get(k), "score": float(match(k, pred.get(k), r["gold"][k]))}
            for k in FIELDS]


# ---------- cached async eval ----------

def results_path(tag: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    return RESULTS / f"results_{tag}.jsonl"


def load_results(tag: str) -> dict[str, dict]:
    """Per-document records keyed by docid."""
    p = results_path(tag)
    if not p.exists():
        return {}
    return {r["doc"]: r for r in (json.loads(l) for l in p.read_text().splitlines() if l.strip())}


def field_rows(tag: str) -> list[dict]:
    return [f for r in load_results(tag).values() for f in r["fields"]]


async def eval_model(model: str, tag: str, split: str = "test", *, build_messages=None, concurrency: int = 8,
                     max_tokens: int = 4096, temperature: float = 0.0, limit: int | None = None,
                     endpoint: str | None = None, extra: dict | None = None):
    """Cached: re-running only fills documents that are missing or errored."""
    from openai import AsyncOpenAI
    from tqdm.asyncio import tqdm

    m = MODELS.get(model, {"label": model, "model": model, "host": "fireworks", "price": (0.0, 0.0)})
    rows = load_split(split)
    done = {k for k, r in load_results(tag).items() if not r.get("error")}
    todo = [r for r in rows if r["id"] not in done][:limit]
    print(f"{tag}: {m['label']} on {split} · to_run={len(todo)}")
    if m["host"] == "openrouter":
        client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"], timeout=300)
        kw = {"extra_body": {"reasoning": {"effort": "low"}}, **(extra or {})}
    else:
        client = AsyncOpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key=os.environ["FIREWORKS_API_KEY"],
                             timeout=300)
        kw = {"reasoning_effort": "low", **(extra or {})}
    sem, lock = asyncio.Semaphore(concurrency), asyncio.Lock()
    build = build_messages or messages

    async def one(r):
        t0, text, err, usage = time.perf_counter(), "", None, None
        msgs = await asyncio.to_thread(build, r)
        async with sem:
            for attempt in range(4):
                try:
                    resp = await client.chat.completions.create(model=endpoint or m["model"], messages=msgs,
                                                                max_tokens=max_tokens, temperature=temperature, **kw)
                    text, usage, err = (resp.choices[0].message.content or "").strip(), resp.usage, None
                    break
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"[:500]
                    await asyncio.sleep(3 * (attempt + 1))
        pred = parse(text)
        pin, pout = m["price"]
        ptok = getattr(usage, "prompt_tokens", 0) or 0
        ctok = getattr(usage, "completion_tokens", 0) or 0
        rec = {"doc": r["id"], "model": tag, "cluster": r["cluster"], "parsed": pred is not None,
               "fields": grade(r, pred), "text": text[-2000:], "error": err if not text else None,
               "prompt_tokens": ptok, "completion_tokens": ctok, "cost_usd": (ptok * pin + ctok * pout) / 1e6,
               "latency_s": round(time.perf_counter() - t0, 2)}
        async with lock:
            with results_path(tag).open("a") as f:
                f.write(json.dumps(rec) + "\n")

    if todo:
        await tqdm.gather(*(one(r) for r in todo), desc=tag)
    summarize(tag)


def summarize(tag: str) -> dict:
    res = load_results(tag)
    fr = [f for r in res.values() for f in r["fields"]]
    if not fr:
        return {}
    acc = lambda xs: sum(x["score"] for x in xs) / max(len(xs), 1)  # noqa: E731
    out = {"tag": tag, "docs": len(res), "field_accuracy": acc(fr),
           "present_accuracy": acc([f for f in fr if f["present"]]),
           "absent_accuracy": acc([f for f in fr if not f["present"]]),
           "unseen_layout_accuracy": acc([f for f in fr if f["unseen_layout"]]),
           "parse_rate": sum(r["parsed"] for r in res.values()) / len(res),
           "errors": sum(bool(r.get("error")) for r in res.values()),
           "prompt_tokens": sum(r["prompt_tokens"] for r in res.values()),
           "completion_tokens": sum(r["completion_tokens"] for r in res.values())}
    print(f"{tag}: field acc {out['field_accuracy']:.1%} · present {out['present_accuracy']:.1%} · "
          f"absent {out['absent_accuracy']:.1%} · unseen layouts {out['unseen_layout_accuracy']:.1%} · "
          f"parsed {out['parse_rate']:.1%} · errors {out['errors']} · docs {out['docs']}")
    return out
