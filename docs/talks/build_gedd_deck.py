"""Build the GEDD workshop deck (docs/talks/gedd-workshop.pptx) from the repo's real results.

Numbers are read from experiments/docile-invoices/results/*.json, so the deck stays in sync with
FINDINGS.md. Run with any Python that has python-pptx, e.g. the experiment's environment:

  cd experiments/docile-invoices && uv run python ../../docs/talks/build_gedd_deck.py
"""

from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments" / "docile-invoices"
FIG = EXP / "figures"
ASSETS = Path(__file__).resolve().parent / "assets"
OUT = Path(__file__).resolve().parent / "gedd-workshop.pptx"

INK = RGBColor(0x24, 0x29, 0x2F)
MUTED = RGBColor(0x57, 0x60, 0x6A)
PURPLE = RGBColor(0x82, 0x50, 0xDF)
BLUE = RGBColor(0x09, 0x69, 0xDA)
GREEN = RGBColor(0x1A, 0x7F, 0x37)
RED = RGBColor(0xCF, 0x22, 0x2E)
AMBER = RGBColor(0x9A, 0x67, 0x00)
CARD = RGBColor(0xF6, 0xF8, 0xFA)
LINE = RGBColor(0xD0, 0xD7, 0xDE)
FONT = "Helvetica Neue"

W, H = Inches(13.333), Inches(7.5)

rigor = json.loads((EXP / "results" / "rigor.json").read_text())
gate = json.loads((EXP / "results" / "reward_gate_ppi.json").read_text())
audit = json.loads((EXP / "results" / "reward_audit.json").read_text())
cmp = {(c["a"], c["b"], c["slice"]): c for c in rigor["comparisons"]}
sft_vs_base = cmp[("glm_sft_1344", "glm_1344", "all")]
sft_unseen = cmp[("glm_sft_1344", "glm_1344", "unseen")]
hb_unseen = cmp[("glm_rules_ocr", "glm", "unseen")]
docs_sft = next(x for x in rigor["doc_success"] if x["system"] == "glm_sft_1344")
docs_a = next(x for x in rigor["doc_success"] if x["system"] == "glm_rules")
tax = rigor["taxonomy"]
A = audit["rewards"]


def pts(x: float) -> str:
    return f"{x * 100:+.1f}"


prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, s, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT, font=FONT):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    lines = s if isinstance(s, list) else [s]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(size), bold, color, font
        p.space_after = Pt(size * 0.35)
    return box


def rich(slide, x, y, w, h, parts_lines, size=18):
    """parts_lines: list of lines; each line a list of (text, bold, color)."""
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    for i, parts in enumerate(parts_lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(size * 0.5)
        for t, b, c in parts:
            r = p.add_run()
            r.text = t
            r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(size), b, c or INK, FONT
    return box


def card(slide, x, y, w, h, fill=CARD, line=LINE):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shp.adjustments[0] = 0.06
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.color.rgb = line
    shp.shadow.inherit = False
    return shp


def header(slide, kicker, title, subtitle=None):
    text(slide, Inches(0.6), Inches(0.35), Inches(12), Inches(0.4), kicker.upper(), 12, PURPLE, True)
    text(slide, Inches(0.6), Inches(0.65), Inches(12.2), Inches(0.9), title, 32, INK, True)
    if subtitle:
        text(slide, Inches(0.6), Inches(1.45), Inches(12.2), Inches(0.6), subtitle, 16, MUTED)


def footer(slide, s):
    text(slide, Inches(0.6), Inches(6.95), Inches(12.2), Inches(0.4), s, 10, MUTED)


def new(kicker=None, title=None, subtitle=None):
    s = prs.slides.add_slide(BLANK)
    if title:
        header(s, kicker or "", title, subtitle)
    return s


def section(part, title, sub):
    s = new()
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.35), H)
    bar.fill.solid()
    bar.fill.fore_color.rgb = PURPLE
    bar.line.fill.background()
    text(s, Inches(1.0), Inches(2.6), Inches(11), Inches(0.5), part.upper(), 16, PURPLE, True)
    text(s, Inches(1.0), Inches(3.0), Inches(11), Inches(1.2), title, 48, INK, True)
    text(s, Inches(1.0), Inches(4.2), Inches(11), Inches(0.8), sub, 20, MUTED)


def image(slide, path, x, y, w=None, h=None):
    return slide.shapes.add_picture(str(path), x, y, width=w, height=h)


def table(slide, x, y, w, rows, col_w=None, size=13, header_fill=INK, highlight=None, left_cols=(0,)):
    nr, nc = len(rows), len(rows[0])
    t = slide.shapes.add_table(nr, nc, x, y, w, Inches(0.4) * nr).table
    if col_w:
        for i, cw in enumerate(col_w):
            t.columns[i].width = Emu(int(w * cw))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = str(val) if str(val) else " "
            p = c.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j in left_cols else PP_ALIGN.CENTER
            r = p.runs[0]
            r.font.size, r.font.name = Pt(size), FONT
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = header_fill
                r.font.color.rgb, r.font.bold = RGBColor(0xFF, 0xFF, 0xFF), True
            else:
                c.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i % 2 else CARD
                r.font.color.rgb = INK
                if highlight and highlight(i, j, val):
                    r.font.bold, r.font.color.rgb = True, RED
    return t


def big_numbers(slide, items, y=Inches(2.2)):
    n = len(items)
    gap = Inches(0.3)
    cw = (W - Inches(1.2) - gap * (n - 1)) / n
    for i, (num, label, note, color) in enumerate(items):
        x = Inches(0.6) + (cw + gap) * i
        card(slide, x, y, cw, Inches(3.4))
        text(slide, x + Inches(0.3), y + Inches(0.35), cw - Inches(0.6), Inches(1.2), num,
             44 if len(num) <= 6 else 34, color, True)
        text(slide, x + Inches(0.3), y + Inches(1.55), cw - Inches(0.6), Inches(0.6), label.upper(), 12, MUTED, True)
        text(slide, x + Inches(0.3), y + Inches(2.05), cw - Inches(0.6), Inches(1.3), note, 14, INK)


def steps(slide, items, y=Inches(2.0), size=17):
    for i, (head, body) in enumerate(items):
        yy = y + Inches(0.92) * i
        circ = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.7), yy, Inches(0.55), Inches(0.55))
        circ.fill.solid()
        circ.fill.fore_color.rgb = PURPLE
        circ.line.fill.background()
        tf = circ.text_frame
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        r = tf.paragraphs[0].add_run()
        r.text, r.font.size, r.font.bold = str(i + 1), Pt(16), True
        r.font.color.rgb, r.font.name = RGBColor(0xFF, 0xFF, 0xFF), FONT
        rich(slide, Inches(1.5), yy - Inches(0.02), Inches(11.2), Inches(0.9),
             [[(head + "   ", True, INK), (body, False, MUTED)]], size)


def recipe(slide, items, y=Inches(2.0)):
    n = len(items)
    gap = Inches(0.25)
    cw = (W - Inches(1.2) - gap * (n - 1)) / n
    for i, (head, body, detail) in enumerate(items):
        x = Inches(0.6) + (cw + gap) * i
        card(slide, x, y, cw, Inches(4.3))
        text(slide, x + Inches(0.25), y + Inches(0.25), cw, Inches(0.4), str(i + 1), 28, PURPLE, True)
        text(slide, x + Inches(0.25), y + Inches(0.85), cw - Inches(0.5), Inches(0.4), head.upper(), 13, MUTED, True)
        text(slide, x + Inches(0.25), y + Inches(1.3), cw - Inches(0.5), Inches(1.2), body, 18, INK, True)
        text(slide, x + Inches(0.25), y + Inches(2.55), cw - Inches(0.5), Inches(1.7), detail, 13, MUTED)


# ── 1 title ───────────────────────────────────────────────────────────────────
s = new()
text(s, Inches(0.8), Inches(2.0), Inches(11.5), Inches(0.5), "GEDD WORKSHOP", 16, PURPLE, True)
text(s, Inches(0.8), Inches(2.5), Inches(11.8), Inches(1.2),
     "Grounded Evidence Driven Development", 40, INK, True)
text(s, Inches(0.8), Inches(3.55), Inches(11.5), Inches(1.0),
     "One expert-built failure codebook → your evaluation, your training reward and your response gate",
     22, MUTED)
text(s, Inches(0.8), Inches(6.4), Inches(11.5), Inches(0.5),
     "github.com/aws-samples/sample-GEDD", 14, BLUE)

# ── 2 get the code ────────────────────────────────────────────────────────────
s = new("Try it", "Get the code",
        "Everything in this talk is open source and regenerated from saved per-case results by a script.")
for i, (path, desc) in enumerate([
    ("FINDINGS.md", "Every claim in this talk, with its status, evidence and the script that produces it"),
    ("experiments/docile-invoices/", "The case study: baseline, harnesses, fine-tune, rigor pass, reward audit, RL environment"),
    ("grounded-evals/", "The app for experts, plus the stats and reward packages and the CLI"),
    ("docs/", "Methodology, research positioning, guides, 17 worked domain judges"),
]):
    y = Inches(2.3) + Inches(1.05) * i
    card(s, Inches(0.6), y, Inches(12.1), Inches(0.85))
    text(s, Inches(0.9), y + Inches(0.2), Inches(4.2), Inches(0.5), path, 18, PURPLE, True, font="Menlo")
    text(s, Inches(5.2), y + Inches(0.22), Inches(7.3), Inches(0.5), desc, 16, INK)
footer(s, "CI re-runs the findings scripts on every pull request and fails if a reported number drifts.")

# ── 3 agenda ──────────────────────────────────────────────────────────────────
s = new("Agenda", "What we'll cover")
for i, (part, head, body) in enumerate([
    ("I", "Measure", "Prove a gain on a locked test set, with tests that respect how errors cluster."),
    ("II", "The reward model and the gate", "Turn the codebook into a reward and a gate, and see where that breaks."),
    ("III", "Reward hacking", "Score six rewards on the same invoices before training, and find the loopholes."),
    ("IV", "Wrap up", "What we found, the rules to reuse, and what comes next."),
]):
    y = Inches(1.9) + Inches(1.2) * i
    text(s, Inches(0.7), y, Inches(1.0), Inches(0.8), part, 36, PURPLE, True)
    text(s, Inches(1.8), y + Inches(0.05), Inches(10.5), Inches(0.5), head, 24, INK, True)
    text(s, Inches(1.8), y + Inches(0.55), Inches(10.5), Inches(0.5), body, 16, MUTED)

# ── PART I ────────────────────────────────────────────────────────────────────
section("Part I", "Measure", "Does our system beat the off-the-shelf model, and is the gain real?")

s = new("The problem", "AI quality is usually a definition problem",
        "Generic evaluators reward fluent, confident answers. Domain experts know which fluent answers are wrong.")
for i, (head, body) in enumerate([
    ("Evaluation rubric", "\"Be accurate\", written before anyone looked at outputs"),
    ("Training data", "Preferences collected with different criteria again"),
    ("Guardrail", "Hand-written rules that drift from both"),
]):
    x = Inches(0.6) + Inches(4.15) * i
    card(s, x, Inches(2.4), Inches(3.9), Inches(2.3))
    text(s, x + Inches(0.3), Inches(2.65), Inches(3.4), Inches(0.5), head, 20, INK, True)
    text(s, x + Inches(0.3), Inches(3.25), Inches(3.4), Inches(1.4), body, 16, MUTED)
rich(s, Inches(0.6), Inches(5.1), Inches(12.1), Inches(1.4), [[
    ("GEDD: ", True, PURPLE),
    ("experts label real outputs, failure codes emerge from the data, and one codebook defines all three.",
     False, INK)]], 20)

s = new("The idea", "The GEDD flywheel",
        "The same evidence measures the system, trains the next version and gates what customers see.")
image(s, ROOT / "docs" / "assets" / "diagrams" / "flywheel.png", Inches(0.6), Inches(2.3), w=Inches(12.1))
footer(s, "The reward model learns from expert verdicts, preference pairs and severity weights, then supplies "
          "the reward for Improve and the score for Guard.")

s = new("The case study", "The recipe: model, task, score, eval")
recipe(s, [
    ("The model", "An open vision-language model + LoRA", "Baseline at temperature 0. Two prompt harnesses. "
     "A rank-16 LoRA fine-tune on 1,400 training invoices."),
    ("The task", "Read 10 fields off one invoice page", "Invoice number, dates, vendor, customer, order number, "
     "terms, totals, currency. JSON out, null if not printed."),
    ("The score", "Normalised exact match per field", "Amounts as numbers, dates as dates, currency symbols to "
     "ISO codes. Absent fields must be null."),
    ("The eval", "500 locked invoices, 5,000 field cases", "204 layout clusters; 124 invoices on layouts never "
     "seen in training. Locked before any work."),
], y=Inches(1.75))

s = new("The score", "What counts as \"correct\"",
        "Illustrative cases for the scoring rules. Every (invoice, field) pair is one pass/fail case.")
table(s, Inches(0.6), Inches(2.2), Inches(12.1), [
    ["Field", "Prediction", "Labelled on the page", "Result", "Why"],
    ["amount_due", "$1,234.50", "1234.5", "✓", "amounts compared as numbers"],
    ["date_issue", "3/4/2020", "March 4, 2020", "✓", "dates compared as calendar dates"],
    ["currency_code_amount_due", "$", "USD", "✓", "symbols mapped to ISO codes"],
    ["order_id", "PO-88213", "(not printed)", "✗ invented_value", "absent fields must be null"],
    ["vendor_name", "null", "ACME Corp.", "✗ missed_value", "a printed field was skipped"],
    ["customer_billing_name", "ACME Holdings", "ACME Corp.", "✗ wrong_value", "printed, but a different value"],
], col_w=[0.22, 0.16, 0.2, 0.17, 0.25], size=14)
footer(s, "The three failure codes come from the error analysis. They're the codebook for this domain, "
          "with severities: invented = critical, wrong = high, missed = medium.")

s = new("Before we test anything", "Hold out content, not just cases")
steps(s, [
    ("Lock the test set.", "500 invoices, never used for prompt design, training or picking checkpoints."),
    ("Group by what shares mistakes.", "Invoices from one layout fail together, so the 204 layouts are the "
     "unit of uncertainty."),
    ("Report unseen layouts separately.", "124 invoices on layouts the fine-tune never saw."),
    ("Keep RL training leak-free.", "The RL pool only uses layouts absent from the test set."),
    ("State what the test can detect.", "Minimum detectable effect: ~3 pts overall, ~4.6–4.9 on unseen layouts."),
], y=Inches(1.9))

s = new("The GEDD bar", "When is a gain real?", "Both tests must agree. One alone changes conclusions.")
for i, (head, body) in enumerate([
    ("Exact McNemar test, Holm-adjusted",
     "Among cases where exactly one system is right, does yours win more than chance? Adjusted across every "
     "comparison in the round."),
    ("Layout-cluster bootstrap",
     "Resample whole layouts 5,000 times. The 95% interval of the gain must exclude zero."),
    ("Minimum detectable effect",
     "Report it, so a null result reads as underpowered or as no effect."),
]):
    x = Inches(0.6) + Inches(4.15) * i
    card(s, x, Inches(2.3), Inches(3.9), Inches(3.3))
    text(s, x + Inches(0.3), Inches(2.55), Inches(3.4), Inches(1.0), head, 19, INK, True)
    text(s, x + Inches(0.3), Inches(3.55), Inches(3.4), Inches(2.0), body, 15, MUTED)

s = new("The result", f"Fine-tuning: 78.5% → 88.4% of fields",
        f"Gain {pts(sft_vs_base['delta'])} pts · Holm p ≈ 1e-75 · layout-cluster 95% CI "
        f"[{pts(sft_vs_base['ci'][0])}, {pts(sft_vs_base['ci'][1])}]")
image(s, FIG / "leaderboard.png", Inches(1.6), Inches(2.1), h=Inches(4.7))

s = new("The result", "What it's worth")
big_numbers(s, [
    (f"{docs_sft['baseline']:.0%} → {docs_sft['acc']:.0%}", "invoices fully right",
     f"All 10 fields correct: the invoice skips review. 3×. CI [{pts(docs_sft['ci'][0])}, {pts(docs_sft['ci'][1])}].",
     GREEN),
    (pts(sft_unseen["delta"]), "pts on unseen layouts",
     f"Smaller than overall, still real: CI [{pts(sft_unseen['ci'][0])}, {pts(sft_unseen['ci'][1])}].", BLUE),
    ("< $50", "total compute", "Baseline, two harnesses, LoRA training and scoring.", PURPLE),
])

s = new("The result", "The aggregate hides trade-offs", "Errors out of 5,000 field cases, by failure code.")
table(s, Inches(0.6), Inches(2.2), Inches(8.0), [
    ["System", "Invented", "Wrong value", "Missed", "Total"],
    *[[n, tax[t]["invented"], tax[t]["wrong"], tax[t]["missed"], tax[t]["total"]] for t, n in
      [("glm_1344", "Base model"), ("glm_rules", "Harness A (rules)"),
       ("glm_rules_ocr", "Harness B (rules + OCR)"), ("glm_sft_1344", "SFT fine-tune")]],
], col_w=[0.36, 0.16, 0.18, 0.15, 0.15], size=15)
rich(s, Inches(9.0), Inches(2.3), Inches(3.8), Inches(4), [
    [("Fine-tune: ", True, INK), ("invented values −62%, wrong values −39%.", False, MUTED)],
    [("But: ", True, RED), ("missed values +22%. It learned restraint, and slightly over-learned it.", False, MUTED)],
    [("Prompting ", True, INK), ("traded invented values for missed ones.", False, MUTED)],
], 16)

s = new("The result", "Requiring both tests changes conclusions")
for i, (head, body, verdict, color) in enumerate([
    ("Harness B on unseen layouts", f"{pts(hb_unseen['delta'])} pts, CI [{pts(hb_unseen['ci'][0])}, "
     f"{pts(hb_unseen['ci'][1])}], but the test can only detect ≥ {hb_unseen['mde_80'] * 100:.1f} pts.",
     "Underpowered, not \"no effect\"", AMBER),
    ("Rules prompt, invoices fully right", f"{pts(docs_a['delta'])} pts, McNemar p = {docs_a['p']:.2f}, but "
     f"cluster CI [{pts(docs_a['ci'][0])}, {pts(docs_a['ci'][1])}].", "Not a real gain", RED),
]):
    x = Inches(0.6) + Inches(6.15) * i
    card(s, x, Inches(2.0), Inches(5.9), Inches(3.8))
    text(s, x + Inches(0.35), Inches(2.3), Inches(5.2), Inches(0.6), head, 22, INK, True)
    text(s, x + Inches(0.35), Inches(3.1), Inches(5.2), Inches(1.6), body, 17, MUTED)
    text(s, x + Inches(0.35), Inches(4.8), Inches(5.2), Inches(0.6), verdict, 20, color, True)
footer(s, "Invoices from one layout share mistakes. Case-level tests alone are overconfident.")

# ── PART II ───────────────────────────────────────────────────────────────────
section("Part II", "The reward model and the gate", "Turn the codebook into a score, and test whether that helps.")

s = new("The reward model", "One reward, decomposed by failure code",
        "Calibrated per-code probabilities × severity weights the experts own.")
rich(s, Inches(0.6), Inches(2.2), Inches(12.1), Inches(1.2), [[
    ("reward  =  1  −  Σ", True, PURPLE), ("  severity(code)  ×  P(code present)", True, INK)]], 30)
for i, (head, body) in enumerate([
    ("Auditable", "Every low score names the failure code that caused it."),
    ("Expected-cost optimal", "If the probabilities are calibrated, auto-posting the highest-reward responses "
     "minimises expected business cost at any straight-through rate."),
    ("Conservative", "Several judges: score = mean − k × spread. Disagreement sends the case to human review."),
]):
    x = Inches(0.6) + Inches(4.15) * i
    card(s, x, Inches(3.5), Inches(3.9), Inches(2.8))
    text(s, x + Inches(0.3), Inches(3.75), Inches(3.4), Inches(0.5), head, 19, INK, True)
    text(s, x + Inches(0.3), Inches(4.35), Inches(3.4), Inches(1.9), body, 15, MUTED)

g = gate["gate"]["gate"]["codebook_sum_minus_scalar_sum"]["0.1_precision"]
s = new("Pilot · null result", "Decomposition only helps when the detectors are good",
        "Gold-free detectors built from cross-system agreement: calibrated (ECE ≤ 0.02) but weak (AUROC 0.55–0.83).")
image(s, FIG / "gate_tradeoff.png", Inches(0.6), Inches(2.2), w=Inches(8.6))
rich(s, Inches(9.5), Inches(2.3), Inches(3.4), Inches(4.3), [
    [("At the strictest gate ", True, INK), (f"the codebook reward posts {g['mean'] * 100:+.0f} pts more fully "
     f"correct invoices in {g['share_positive']:.0%} of 50 splits…", False, MUTED)],
    [("…but the range crosses zero, ", True, RED), ("and looser gates show no difference.", False, MUTED)],
    [("Takeaway: ", True, PURPLE), ("the form is necessary, not sufficient. Better judges are the next experiment.",
                                    False, MUTED)],
], 15)

p100 = gate["ppi"]["field_accuracy"]["by_n"]["100"]
s = new("Pilot", "Online estimates stay honest",
        "Judge scores on every trace + a small random expert sample (prediction-powered inference, PPI++).")
image(s, FIG / "ppi_width.png", Inches(0.6), Inches(2.1), h=Inches(4.6))
rich(s, Inches(7.6), Inches(2.3), Inches(5.2), Inches(4.3), [
    [("Valid: ", True, GREEN), (f"{p100['ppi_coverage']:.0%} coverage at nominal 95% with 100 expert labels.",
                                False, MUTED)],
    [("Not much tighter: ", True, AMBER), (f"intervals {1 - p100['width_ratio']:.0%} narrower than experts alone, "
     "because the judge is weak.", False, MUTED)],
    [("Safe by design: ", True, INK), ("with a weak judge PPI++ falls back to the experts instead of inheriting "
     "the judge's bias.", False, MUTED)],
], 16)

# ── PART III ──────────────────────────────────────────────────────────────────
section("Part III", "Reward hacking", "Change one line of the reward, get a different policy.")

s = new("Reward hacking", "What reward hacking is",
        "A policy finds a way to score high on the reward we wrote without doing the task we meant.")
for i, (head, sub, body) in enumerate([
    ("PROXY", "A stand-in reward", "It measures what we can check. Here: \"never invent a value\" stands in "
     "for \"extract the invoice correctly\"."),
    ("GAP", "It ignores something", "Anything the reward doesn't charge for is free. Here: answering null "
     "for a field that is printed."),
    ("AMPLIFY", "RL pushes on the gap", "Training grows whatever pays. Here: a policy that answers null "
     "everywhere scores a perfect 1.0."),
]):
    x = Inches(0.6) + Inches(4.15) * i
    card(s, x, Inches(2.3), Inches(3.9), Inches(3.8))
    text(s, x + Inches(0.3), Inches(2.55), Inches(3.4), Inches(0.5), head, 16, PURPLE, True)
    text(s, x + Inches(0.3), Inches(3.0), Inches(3.4), Inches(0.6), sub, 21, INK, True)
    text(s, x + Inches(0.3), Inches(3.75), Inches(3.4), Inches(2.2), body, 15, MUTED)

s = new("Reward hacking", "Six candidate rewards for the same task")
table(s, Inches(0.6), Inches(1.8), Inches(12.1), [
    ["Reward", "What it pays", "What it ignores"],
    ["gedd", "+1 per correct field, minus the severity of each failure", "— (the training reward)"],
    ["gedd, cost only", "1 − severity cost", "Never pays for being right"],
    ["exact", "Share of fields correct", "How bad each error is"],
    ["no invention", "1 − invented values ÷ absent fields", "Missing printed values"],
    ["coverage", "Fields filled ÷ 10", "Whether the values are right"],
    ["lenient", "Gold contained anywhere in the answer", "Answers that list every candidate"],
], col_w=[0.18, 0.47, 0.35], size=15, left_cols=(0, 1, 2))

s = new("Reward hacking", "Same invoices, six rewards",
        "Real systems vs three degenerate policies, scored before any training. ⚠ = matches or beats the base model.")
image(s, FIG / "reward_audit.png", Inches(1.2), Inches(2.0), h=Inches(4.85))

m = audit["rewards"]
s = new("Reward hacking", "Pay for the goal, charge for the cost",
        "A reward that only charges for failures leaves abstention almost as good as working.")
big_numbers(s, [
    (f"{m['Base model']['gedd_cost_only'] - m['All null (abstain)']['gedd_cost_only']:.2f}",
     "abstention gap · cost-only reward",
     f"Answer null everywhere: {m['All null (abstain)']['gedd_cost_only']:.2f} vs the base model's "
     f"{m['Base model']['gedd_cost_only']:.2f}. RL would drift toward silence.", RED),
    (f"{m['Base model']['gedd'] - m['All null (abstain)']['gedd']:.2f}", "abstention gap · GEDD reward",
     f"Add +1 per correct field: {m['All null (abstain)']['gedd']:.2f} vs {m['Base model']['gedd']:.2f}. "
     "About 8× the safety margin.", GREEN),
    (f"{m['All null (abstain)']['no_invention']:.2f}", "abstention · no-invention reward",
     f"A perfect score, above the fine-tune's {m['SFT fine-tune']['no_invention']:.2f}.", RED),
], y=Inches(2.1))

s = new("The RL environment", "From audit to training: the GEDD environment")
recipe(s, [
    ("Policy", "The VLM + a small LoRA", "Only the adapter trains. 4 tries per invoice at temperature 1."),
    ("Environment", "One invoice page → JSON", "Leak-free pool: only layouts absent from the test set."),
    ("Grader", "Any of the six rewards", "Every step logs all six rewards plus counts of each failure code."),
    ("Update", "GRPO", "Advantage = (reward − group mean) ÷ group spread, clipped. Flat groups teach nothing."),
], y=Inches(1.75))
footer(s, "Prediction to test (R1): the no-invention arm drifts to nulls, the coverage arm to invention, "
          "the GEDD arm improves exact accuracy. About $19 per arm.")

# ── PART IV ───────────────────────────────────────────────────────────────────
section("Part IV", "Wrap up", "What we found, and how to use it on your own project.")

s = new("Wrap up", "What we found")
big_numbers(s, [
    (f"{docs_sft['baseline']:.0%} → {docs_sft['acc']:.0%}", "invoices fully right",
     f"Fields 78.5% → 88.4%, real on unseen layouts too ({pts(sft_unseen['delta'])} pts).", GREEN),
    ("Null", "decomposed reward, weak judges",
     "Codebook form alone doesn't beat a scalar reward at the gate. Detector quality is the constraint.", AMBER),
    ("3 of 3", "proxy rewards gamed",
     "Abstain, guess or dump: each proxy pays one. GEDD and exact pay none, checked before training.", RED),
])

s = new("Wrap up", "Using GEDD on your own project")
steps(s, [
    ("Let experts find the failures first.", "Label real outputs; codes emerge; give each one a severity."),
    ("Lock the test set and group it.", "Report unseen groups separately, and state what the test can detect."),
    ("Require both tests.", "Holm-adjusted McNemar and a group bootstrap, or it isn't a gain."),
    ("Audit the reward before training.", "Score abstain, guess and dump policies. If one pays, fix the reward."),
    ("Pay for the goal, charge for the cost.", "Severity alone makes silence cheap; reward correct work too."),
], y=Inches(1.8))

s = new("What's next", "Pre-registered experiments")
table(s, Inches(0.6), Inches(1.9), Inches(12.1), [
    ["", "Question", "Status"],
    ["E1", "Where should criteria come from: generic, expert-written up front, LLM-written, or the GEDD codebook?",
     "Needs experts + a 2nd domain"],
    ["E2", "Codebook vs scalar LLM-judge reward under best-of-N pressure", "Script ready, ~$12"],
    ["R1", "Does RL amplify the loopholes the audit predicts?", "Environment + trainer ready, ~$19 / arm"],
    ["E3", "How much does each expert label buy, round after round?", "Planned"],
    ["L1", "Two experts double-label the 582 remaining errors", "Kit ready"],
], col_w=[0.06, 0.66, 0.28], size=15, left_cols=(0, 1, 2))

s = new()
text(s, Inches(0.8), Inches(2.6), Inches(11.5), Inches(1.2), "Questions?", 60, INK, True)
text(s, Inches(0.8), Inches(3.9), Inches(11.5), Inches(0.6),
     "FINDINGS.md has every number in this talk, and the script behind it.", 20, MUTED)
text(s, Inches(0.8), Inches(6.4), Inches(11.5), Inches(0.5), "github.com/aws-samples/sample-GEDD", 14, BLUE)

prs.save(OUT)
print(f"wrote {OUT} ({len(prs.slides)} slides)")
