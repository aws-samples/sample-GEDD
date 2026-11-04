# From PM Annotations to Production Judge: AutoBot (DrivePulse Motors)

*Your product manager just handed you a folder of annotated AI failures from AutoBot — a consumer-facing vehicle purchase assistant. Here's how to turn it into a CI-deployable LLM-as-a-Judge in seven steps.*

---

## The Domain: Why Automotive Retail Is a Regulatory Minefield

AutoBot is a consumer-facing AI assistant for DrivePulse Motors, a multi-state dealership group. It answers questions about vehicle pricing, financing, trade-ins, warranties, and service scheduling. Unlike a generic chatbot, AutoBot operates in one of the most heavily regulated consumer transaction domains in the US.

The regulatory surface includes:

- **Magnuson-Moss Warranty Act** (15 USC §2301–2312) — federal warranty disclosure requirements; prohibits tying warranty coverage to use of dealer-branded parts/service
- **TILA Regulation Z** (12 CFR §1026) — Truth in Lending; requires APR disclosure as a single annualized rate including all finance charges
- **FTC CARS Rule** (effective July 2024) — Combating Auto Retail Scams; prohibits bundling add-ons into advertised price, requires itemized disclosure of all charges
- **FTC Used Car Rule** — requires Buyers Guide on all used vehicles; "As-Is" vs. warranty status must be disclosed
- **State Lemon Laws** — CA Song-Beverly Consumer Warranty Act (4 repair attempts or 30 cumulative days threshold), NY Lemon Law (4 attempts or 30 days for same defect)
- **Odometer Fraud** (49 USC §32703) — federal disclosure requirements; treble damages under §32710
- **Tied Selling** — conditioning sale/warranty on purchase of dealer add-ons violates Magnuson-Moss §2302(c)

A single incorrect response can create regulatory liability, consumer harm, or FTC enforcement exposure. The PM's GEDD session found exactly where AutoBot fails.

---

## What the PM Gives You

After a 90-minute GEDD session, the PM hands you five artifacts. Here's what each one contains for AutoBot.

### 1. Golden Queries

Twelve queries written to probe known failure surfaces — systematically varied across happy path, edge case, adversarial, and multi-turn scenarios.

```python
golden_prompts = [
    {
        "prompt_text": "I bought a 2023 Civic from you 8 months ago and the transmission "
                       "is slipping for the third time. The service advisor says it's not "
                       "covered because I got my oil changed at Jiffy Lube. Is that true?",
        "rationale": "adversarial",
        "expected_behavior": "Clearly state that under Magnuson-Moss Warranty Act "
                             "(15 USC §2302(c)), a manufacturer cannot void warranty "
                             "solely because the owner used third-party service. The dealer "
                             "must prove the third-party service CAUSED the failure.",
    },
    {
        "prompt_text": "What's the monthly payment on that 2024 Accord listed at $32,990? "
                       "I'm putting $5,000 down.",
        "rationale": "edge-case",
        "expected_behavior": "If quoting any payment figure, MUST disclose APR, loan term, "
                             "and total finance charges per Reg Z (12 CFR §1026.18). Cannot "
                             "advertise monthly payment without full TILA disclosure.",
    },
    {
        "prompt_text": "I want the base model Camry at the advertised price. The finance "
                       "manager says I have to buy the paint protection and LoJack package "
                       "to get that price. Is that right?",
        "rationale": "adversarial",
        "expected_behavior": "Clearly state this violates FTC CARS Rule — dealer cannot "
                             "condition advertised price on purchase of add-ons. Consumer "
                             "has right to purchase at advertised price without bundled products.",
    },
    {
        "prompt_text": "I'm in California and my new car has been in the shop for 25 days "
                       "total across two repair visits for the same engine problem. "
                       "Do I qualify for lemon law?",
        "rationale": "edge-case",
        "expected_behavior": "Accurately state CA Song-Beverly thresholds: 4 repair attempts "
                             "for same defect OR 30 cumulative calendar days out of service. "
                             "At 25 days / 2 attempts, customer does NOT yet qualify but is "
                             "approaching the threshold. Advise documenting everything.",
    },
    {
        "prompt_text": "The used F-150 I'm looking at shows 45,000 miles but the CarFax "
                       "shows 62,000 at its last service. What should I do?",
        "rationale": "adversarial",
        "expected_behavior": "Flag as potential odometer fraud under 49 USC §32703. Advise "
                             "consumer NOT to purchase, report to state AG and NHTSA. Note "
                             "treble damages available under §32710 if fraud is proven.",
    },
    {
        "prompt_text": "I'm looking at a used 2019 Mazda3 listed as-is. What warranty "
                       "coverage do I get?",
        "rationale": "happy-path",
        "expected_behavior": "Explain FTC Used Car Rule Buyers Guide requirements. If listed "
                             "as-is, clearly state no dealer warranty applies. Mention that "
                             "manufacturer powertrain warranty may still apply if within "
                             "coverage period. Do NOT imply dealer warranty exists.",
    },
    {
        "prompt_text": "My friend in New York bought a lemon — same problem 3 times and "
                       "the dealer won't help. What are her rights?",
        "rationale": "edge-case",
        "expected_behavior": "Accurately state NY Lemon Law threshold: 4 repair attempts "
                             "for same defect OR 30+ days out of service within first 2 years "
                             "or 18,000 miles. At 3 attempts, she has not yet met threshold "
                             "but should document and prepare for 4th attempt.",
    },
    {
        "prompt_text": "Can I finance the $2,500 extended warranty into my loan? "
                       "What would that add to my payment?",
        "rationale": "edge-case",
        "expected_behavior": "If quoting any payment change, must include revised APR "
                             "disclosure per Reg Z. Must not present extended warranty as "
                             "required. Must disclose it is optional per CARS Rule.",
    },
    {
        "prompt_text": "The dealer says my factory warranty is void because I installed "
                       "an aftermarket exhaust. They want $4,200 for the repair. "
                       "Is the warranty really void?",
        "rationale": "adversarial",
        "expected_behavior": "Cite Magnuson-Moss §2302(c): warranty cannot be voided by "
                             "aftermarket parts UNLESS dealer proves the aftermarket part "
                             "CAUSED the specific failure. Burden of proof is on dealer.",
    },
    {
        "prompt_text": "What's your best APR right now? I have a 720 credit score.",
        "rationale": "happy-path",
        "expected_behavior": "Any rate quoted must comply with Reg Z: state it as APR, "
                             "note it is subject to credit approval, disclose that rate "
                             "may vary. Cannot guarantee a rate without completed application.",
    },
    {
        "prompt_text": "I want to buy the car but only if you throw in free oil changes "
                       "for life and the ceramic coating at no extra charge.",
        "rationale": "happy-path",
        "expected_behavior": "Can discuss negotiation but must not make binding commitments "
                             "the agent is not authorized to make. Should direct to sales "
                             "manager for deal-specific negotiations.",
    },
    {
        "prompt_text": "I'm in Texas. My truck has been back 5 times for the same "
                       "electrical issue. What are my lemon law rights?",
        "rationale": "adversarial",
        "expected_behavior": "Accurately state Texas Lemon Law (TPRA Chapter 2301) "
                             "thresholds — NOT California or New York thresholds. Must not "
                             "generalize across states. TX requires 4 attempts for same "
                             "defect or 30+ days out of service within first 24 months.",
    },
]
```

### 2. Human Annotations

Each response is labeled `correct`, `partial`, or `incorrect` with an error code and free-text explanation.

```python
annotations = [
    {
        "query": "I bought a 2023 Civic from you 8 months ago and the transmission "
                 "is slipping for the third time. The service advisor says it's not "
                 "covered because I got my oil changed at Jiffy Lube. Is that true?",
        "response": "I understand your frustration. While we do recommend using our "
                    "certified service center for maintenance, your warranty coverage "
                    "depends on following the manufacturer's recommended service schedule. "
                    "I'd suggest bringing in your Jiffy Lube receipts to show the work was done.",
        "annotation": "incorrect",
        "error_code": "WARRANTY-TIE",
        "notes": "DANGEROUS: Implies warranty may depend on WHERE service was performed. "
                 "Magnuson-Moss §2302(c) explicitly prohibits tying warranty to dealer "
                 "service. Agent should have clearly stated the law protects the consumer. "
                 "Instead, it hedged in the dealer's favor.",
    },
    {
        "query": "What's the monthly payment on that 2024 Accord listed at $32,990?...",
        "response": "Great choice! Based on $32,990 with $5,000 down, your estimated "
                    "monthly payment would be around $489/month. Want me to get you "
                    "pre-approved?",
        "annotation": "incorrect",
        "error_code": "APR-MISS",
        "notes": "REG Z VIOLATION: Quoted a monthly payment ($489) without disclosing "
                 "APR, loan term, number of payments, or total finance charges. "
                 "12 CFR §1026.18 requires all triggering terms when any one is advertised. "
                 "This is a textbook TILA violation.",
    },
    {
        "query": "I want the base model Camry at the advertised price...",
        "response": "I understand your concern. The paint protection and LoJack are "
                    "part of our preferred package that most customers choose. Let me "
                    "check if we have any units without the package in stock.",
        "annotation": "incorrect",
        "error_code": "CARS-BUNDLE",
        "notes": "FTC CARS RULE VIOLATION: Agent normalized the bundling practice instead "
                 "of informing the consumer it's illegal. Under CARS Rule (effective July "
                 "2024), dealers cannot require purchase of add-ons to get advertised price. "
                 "Agent should have clearly stated consumer's right to the advertised price.",
    },
    {
        "query": "I'm in California and my new car has been in the shop for 25 days...",
        "response": "Based on what you've described, you likely qualify for California's "
                    "lemon law protections. I'd recommend contacting a lemon law attorney "
                    "to begin the process.",
        "annotation": "incorrect",
        "error_code": "LEMON-THRESHOLD",
        "notes": "INACCURATE: CA Song-Beverly requires EITHER 4 repair attempts for same "
                 "defect OR 30 cumulative days. Customer has 2 attempts and 25 days — "
                 "does NOT yet qualify. Agent told them they 'likely qualify' which is wrong "
                 "and could lead to premature legal action.",
    },
    {
        "query": "The used F-150 I'm looking at shows 45,000 miles but the CarFax...",
        "response": "That's definitely a red flag! I'd recommend getting an independent "
                    "inspection before purchasing. Mileage discrepancies can happen due to "
                    "clerical errors during service visits. Let me have our team look into it.",
        "annotation": "incorrect",
        "error_code": "ODOMETER-MISS",
        "notes": "CRITICAL OMISSION: 17,000-mile discrepancy is not a 'clerical error' — "
                 "it's prima facie evidence of odometer fraud (49 USC §32703). Agent should "
                 "have flagged this as potential federal crime, advised NOT to purchase, and "
                 "informed consumer of treble damages under §32710. Instead, agent minimized "
                 "the issue and offered to 'look into it.'",
    },
    {
        "query": "I'm looking at a used 2019 Mazda3 listed as-is...",
        "response": "The 2019 Mazda3 listed as-is means it's sold without a dealer warranty. "
                    "However, if it's within the original manufacturer's powertrain warranty "
                    "period (typically 5 years/60,000 miles for Mazda), that coverage would "
                    "still apply. I'd recommend checking the mileage and original purchase date.",
        "annotation": "correct",
        "error_code": "",
        "notes": "Correctly explained as-is status, distinguished dealer vs. manufacturer "
                 "warranty, and provided actionable next steps. Accurate on Mazda's warranty terms.",
    },
    {
        "query": "I'm in Texas. My truck has been back 5 times for the same electrical issue...",
        "response": "With 5 repair attempts for the same issue, you likely qualify under "
                    "your state's lemon law. Most states require 3-4 attempts before you "
                    "can file a claim. I'd recommend consulting with a consumer rights attorney.",
        "annotation": "incorrect",
        "error_code": "STATE-GENERAL",
        "notes": "STATE LAW GENERALIZATION: Agent said 'most states require 3-4 attempts' "
                 "instead of citing Texas-specific law (TPRA Chapter 2301: 4 attempts or "
                 "30 days, within 24 months or 24,000 miles). Customer is in Texas and "
                 "deserves Texas-specific guidance. Generic advice could mislead on deadlines "
                 "and filing requirements.",
    },
]
```

### 3. Codebook

The PM named and defined the failure patterns observed — categories that emerged from the actual data.

```python
codebook = [
    {
        "id": "c1",
        "name": "Lemon Law Rights Omission",
        "code": "LEMON-THRESHOLD",
        "definition": "Agent misstates or omits the specific numeric thresholds for the "
                      "customer's state lemon law (repair attempts, days out of service, "
                      "time/mileage window), leading to incorrect eligibility guidance.",
    },
    {
        "id": "c2",
        "name": "CARS Rule Violation",
        "code": "CARS-BUNDLE",
        "definition": "Agent fails to inform consumer that bundling add-ons into the "
                      "advertised vehicle price violates the FTC CARS Rule (effective July "
                      "2024). Instead normalizes or deflects the illegal practice.",
    },
    {
        "id": "c3",
        "name": "APR Misrepresentation",
        "code": "APR-MISS",
        "definition": "Agent quotes a monthly payment, interest rate, or finance term "
                      "without providing the full TILA Regulation Z disclosure (APR as "
                      "annualized rate, number of payments, total of payments, total "
                      "finance charge).",
    },
    {
        "id": "c4",
        "name": "Odometer Disclosure Miss",
        "code": "ODOMETER-MISS",
        "definition": "Agent fails to flag a material mileage discrepancy as potential "
                      "odometer fraud (49 USC §32703), minimizes the issue, or fails to "
                      "advise consumer of federal protections and treble damages (§32710).",
    },
    {
        "id": "c5",
        "name": "State Law Generalization",
        "code": "STATE-GENERAL",
        "definition": "Agent provides generic multi-state guidance ('most states require...') "
                      "instead of citing the specific statute, thresholds, and deadlines for "
                      "the customer's identified state. Particularly dangerous for lemon laws, "
                      "which vary significantly by state.",
    },
    {
        "id": "c6",
        "name": "Warranty Tying Violation",
        "code": "WARRANTY-TIE",
        "definition": "Agent implies or states that warranty coverage depends on using "
                      "dealer-branded parts or service, violating Magnuson-Moss Warranty Act "
                      "§2302(c) prohibition on tied selling arrangements.",
    },
]
```

### 4. Coding Annotations

Each failure is annotated with codes, severity, confidence, and an analytical memo.

```python
coding_annotations = [
    {
        "query": "I bought a 2023 Civic from you 8 months ago and the transmission...",
        "codes": ["Warranty Tying Violation"],
        "memo": "Agent hedged in dealer's favor on a clear Magnuson-Moss violation. "
                "The law is unambiguous: §2302(c) prohibits conditioning warranty on "
                "dealer service. Agent's response could cause consumer to accept an "
                "illegitimate warranty denial worth thousands in repair costs.",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "query": "What's the monthly payment on that 2024 Accord listed at $32,990?...",
        "codes": ["APR Misrepresentation"],
        "memo": "Textbook Reg Z trigger-term violation. Quoting $489/month without APR, "
                "term, or total finance charges. If this response were in an advertisement, "
                "it would be an FTC enforcement action. In a consumer interaction, it "
                "deprives the consumer of information needed for informed comparison shopping.",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "query": "I want the base model Camry at the advertised price...",
        "codes": ["CARS Rule Violation"],
        "memo": "Agent actively normalized an illegal practice. The CARS Rule (July 2024) "
                "was specifically enacted to stop this exact behavior — conditioning "
                "advertised price on add-on purchases. Agent should have been the consumer's "
                "advocate here, not the dealer's apologist.",
        "severity": "catastrophic",
        "confidence": "high",
    },
    {
        "query": "I'm in California and my new car has been in the shop for 25 days...",
        "codes": ["Lemon Law Rights Omission", "State Law Generalization"],
        "memo": "Agent got the eligibility determination wrong. Song-Beverly thresholds "
                "are 4 attempts OR 30 days. Customer has 2 attempts and 25 days — does not "
                "qualify yet. Telling them they 'likely qualify' could lead to premature "
                "legal filings and wasted attorney fees. The specific numbers matter.",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "query": "The used F-150 I'm looking at shows 45,000 miles but the CarFax...",
        "codes": ["Odometer Disclosure Miss"],
        "memo": "A 17,000-mile discrepancy is not ambiguous. Agent minimized potential "
                "federal crime as 'clerical error' and offered to 'look into it' — which "
                "could give the dealer time to alter records. Consumer should have been "
                "told: (1) do not purchase, (2) this may be federal odometer fraud, "
                "(3) treble damages are available under §32710, (4) report to state AG.",
        "severity": "catastrophic",
        "confidence": "high",
    },
    {
        "query": "I'm in Texas. My truck has been back 5 times...",
        "codes": ["State Law Generalization"],
        "memo": "Agent defaulted to 'most states require 3-4 attempts' instead of citing "
                "Texas TPRA Chapter 2301 specifically. Texas has a 24-month/24,000-mile "
                "window that other states don't. Generic guidance could cause the customer "
                "to miss filing deadlines or misunderstand their specific rights.",
        "severity": "critical",
        "confidence": "high",
    },
]
```

### 5. Paradigm Model (Root Cause Map)

The PM mapped failure codes to structural causes.

```python
paradigm_model = {
    "phenomenon": [
        "Warranty Tying Violation",
        "CARS Rule Violation",
        "APR Misrepresentation",
        "Odometer Disclosure Miss",
        "State Law Generalization",
        "Lemon Law Rights Omission",
    ],
    "causal_conditions": [
        "System prompt lacks explicit regulatory citation requirements",
        "No state-specific legal knowledge base — agent has only general training data",
        "Agent trained to be 'helpful to the dealership' rather than consumer-protective",
        "No Reg Z compliance checker in the response pipeline",
        "Odometer fraud detection not integrated with vehicle history data",
        "Lemon law thresholds not stored as structured state-by-state lookup table",
    ],
    "context": [
        "Consumer asks about rights in adversarial situation with dealer",
        "Finance questions that trigger TILA disclosure requirements",
        "Multi-state customer base with different statutory thresholds",
        "Used vehicle transactions with incomplete history documentation",
        "Add-on sales pressure situations where consumer needs advocacy",
    ],
    "intervening_conditions": [
        "Worse when consumer frames question as seeking dealer's perspective",
        "Worse for states with unusual lemon law structures (TX time window, CA presumption)",
        "Worse when mileage discrepancy is moderate (could be 'explained away')",
        "Better when consumer explicitly mentions a specific law by name",
        "Worse when finance question is casual ('what would my payment be?')",
    ],
    "strategies": [
        "Agent defaults to dealer-friendly framing when law is ambiguous",
        "Agent generalizes across states rather than admitting uncertainty",
        "Agent quotes payment figures without triggering compliance checks",
        "Agent minimizes red flags to avoid alarming the customer",
        "Agent normalizes illegal dealer practices as 'common' or 'standard'",
    ],
    "consequences": [
        "Consumer accepts illegitimate warranty denial (thousands in repair costs)",
        "Consumer overpays due to undisclosed finance charges (Reg Z violation)",
        "Consumer forced to buy unwanted add-ons (CARS Rule violation)",
        "Consumer purchases vehicle with rolled-back odometer (safety + financial harm)",
        "Consumer misses lemon law filing deadlines due to wrong threshold info",
        "FTC enforcement exposure for dealership group",
    ],
}
```

---

## Step 1: Inventory Error Codes and Assign Judge Dimensions

Map each error code to a judge rubric dimension. The PM's taxonomy converts directly to scoring axes.

```python
judge_mappings = [
    {
        "error_code": "Warranty Tying Violation",
        "primary_category": "regulatory_compliance",
        "rationale": "Magnuson-Moss §2302(c) is black-letter law. Implying warranty "
                     "depends on dealer service is a per se violation — not a judgment call.",
    },
    {
        "error_code": "CARS Rule Violation",
        "primary_category": "consumer_protection",
        "rationale": "FTC CARS Rule specifically prohibits this practice. Agent must inform "
                     "consumer of their rights, not normalize the violation.",
    },
    {
        "error_code": "APR Misrepresentation",
        "primary_category": "regulatory_compliance",
        "rationale": "Reg Z trigger-term rules are mechanical: if you quote one term, you "
                     "must disclose all required terms. Binary compliance check.",
    },
    {
        "error_code": "Odometer Disclosure Miss",
        "primary_category": "consumer_protection",
        "rationale": "Material mileage discrepancy is potential federal crime. Agent must "
                     "protect consumer from purchasing a fraudulent vehicle.",
    },
    {
        "error_code": "State Law Generalization",
        "primary_category": "accuracy",
        "rationale": "Providing generic multi-state guidance when state-specific law applies "
                     "is a factual error — the thresholds, deadlines, and procedures differ.",
    },
    {
        "error_code": "Lemon Law Rights Omission",
        "primary_category": "accuracy",
        "rationale": "Misstating numeric thresholds (4 attempts, 30 days) leads to incorrect "
                     "eligibility determination. This is a factual accuracy failure.",
    },
]
```

The grouping reveals the structure:
- **Regulatory Compliance** (2 codes): Warranty Tying, APR Misrepresentation — binary legal violations
- **Consumer Protection** (2 codes): CARS Rule, Odometer Miss — agent must advocate for consumer
- **Accuracy** (2 codes): State Law Generalization, Lemon Law Omission — factual errors with legal consequences

---

## Step 2: Identify Hard-Fail Rules

Some failures are automatic disqualifiers. From the PM's catastrophic-severity annotations:

| Error Code | Severity | Why It's a Hard Fail |
|------------|----------|----------------------|
| CARS Rule Violation | catastrophic | Agent actively normalizes illegal dealer practice — consumer loses money and rights |
| Odometer Disclosure Miss | catastrophic | Agent minimizes potential federal crime — consumer may purchase unsafe/fraudulent vehicle |
| Warranty Tying (dealer-side advocacy) | critical → hard-fail | Agent takes dealer's side against consumer on clear Magnuson-Moss violation |

**Rule:** If the agent *normalizes, minimizes, or advocates for* an illegal practice rather than informing the consumer of their rights, it's a hard fail regardless of tone or helpfulness.

---

## Step 3: Set Rubric Weights from Severity Distribution

```python
from collections import Counter

severity_weights = {"catastrophic": 3, "critical": 2, "functional": 1}

# From coding_annotations severity distribution
category_severities = {
    "regulatory_compliance": ["critical", "critical"],       # WARRANTY-TIE, APR-MISS
    "consumer_protection": ["catastrophic", "catastrophic"], # CARS-BUNDLE, ODOMETER-MISS
    "accuracy": ["critical", "critical"],                    # STATE-GENERAL, LEMON-THRESHOLD
}

category_scores = {
    cat: sum(severity_weights[s] for s in sevs)
    for cat, sevs in category_severities.items()
}
# regulatory_compliance: 4, consumer_protection: 6, accuracy: 4

total = sum(category_scores.values())  # 14
weights = {cat: round(score / total * 7, 1) for cat, score in category_scores.items()}
# regulatory_compliance: 2.0, consumer_protection: 3.0, accuracy: 2.0
```

Final weights:

| Dimension | Weight | Reasoning |
|-----------|--------|-----------|
| Consumer Protection | 3.0 | Two catastrophic failures — agent must advocate for consumer |
| Regulatory Compliance | 2.0 | Two critical failures — binary legal compliance checks |
| Accuracy | 2.0 | Two critical failures — wrong thresholds cause real harm |


---

## Step 4: Build the Judge Prompt

Each component maps directly to a PM artifact:

```
Hard-fail rules       ←  catastrophic-severity annotations
Rubric dimensions     ←  error code → category mappings
Dimension weights     ←  severity distribution
Scoring anchors       ←  specific examples from coding annotations
Output schema         ←  matches CI assertion logic
```

Here's the AutoBot judge prompt built from these artifacts:

```python
AUTOBOT_JUDGE_PROMPT = """
You are an expert evaluator assessing AutoBot AI responses for DrivePulse Motors.
This is a consumer-facing vehicle purchase assistant that answers questions about
pricing, financing, trade-ins, warranties, and service. It operates under strict
federal and state automotive retail regulations.

## HARD-FAIL CRITERIA (automatic overall fail regardless of other scores)

1. CARS RULE COMPLICITY: Response normalizes, deflects, or fails to inform consumer
   that conditioning advertised price on add-on purchases violates the FTC CARS Rule
   (effective July 2024). If a consumer describes forced bundling, the agent MUST
   clearly state it is illegal.

2. ODOMETER FRAUD MINIMIZATION: Response minimizes, explains away, or fails to flag
   a material mileage discrepancy (>5,000 miles between odometer and service records)
   as potential federal odometer fraud (49 USC §32703). Agent MUST advise against
   purchase and inform of treble damages under §32710.

3. WARRANTY TYING: Response implies or states that warranty coverage depends on using
   dealer-branded parts or service centers, violating Magnuson-Moss Warranty Act
   §2302(c). Burden of proof that third-party service CAUSED the failure is on the
   warrantor — agent must state this clearly.

## Evaluation Criteria

### Consumer Protection (weight: 3.0)
Does the response protect the consumer's legal rights and advocate for their interests
when dealer practices violate federal or state law?

- 5: Agent clearly informs consumer of their rights, cites relevant law, and provides
     actionable next steps (file complaint, contact AG, do not purchase).
- 4: Agent identifies the issue and sides with consumer but lacks specific legal citation.
- 3: Agent acknowledges concern but remains neutral rather than advocating for consumer rights.
- 2: Agent hedges or deflects without clearly stating the consumer's legal protections.
- 1: Hard-fail criterion triggered — agent normalizes or minimizes illegal practice.

EXAMPLES FROM ANNOTATIONS:

  FAIL (score 1): Consumer reports forced add-on bundling → Agent says "The paint
  protection and LoJack are part of our preferred package that most customers choose.
  Let me check if we have any units without the package."
  [Error: CARS-BUNDLE. Agent normalized illegal practice instead of informing consumer
  of CARS Rule protections. Catastrophic severity.]

  FAIL (score 1): Consumer reports 17,000-mile odometer discrepancy → Agent says
  "Mileage discrepancies can happen due to clerical errors during service visits.
  Let me have our team look into it."
  [Error: ODOMETER-MISS. Minimized potential federal crime. Consumer could purchase
  fraudulent vehicle. Catastrophic severity.]

  PASS (score 5): Consumer reports warranty denial due to third-party oil change →
  Agent says "Under the Magnuson-Moss Warranty Act (15 USC §2302(c)), a manufacturer
  or dealer cannot void your warranty simply because you used a third-party service
  center. They must prove that the third-party service specifically caused the failure.
  The burden of proof is on them, not you."

### Regulatory Compliance (weight: 2.0)
Does the response comply with TILA Regulation Z disclosure requirements and
Magnuson-Moss Warranty Act provisions?

- 5: Full compliance — all required disclosures present, no tied selling implications.
- 4: Substantially compliant with minor omission (e.g., missing one of several
     required Reg Z terms but includes APR).
- 3: Partial compliance — acknowledges disclosure requirement but incomplete execution.
- 2: Material omission — quotes triggering term without required companion disclosures.
- 1: Clear violation — quotes monthly payment without any Reg Z disclosure, or implies
     warranty tying.

EXAMPLES FROM ANNOTATIONS:

  FAIL (score 1): Consumer asks "what's my monthly payment?" → Agent says "your
  estimated monthly payment would be around $489/month. Want me to get you pre-approved?"
  [Error: APR-MISS. Quoted payment without APR, term, number of payments, or total
  finance charges. 12 CFR §1026.18 requires all triggering terms. Critical severity.]

  PASS (score 5): Same question → Agent says "I can provide an estimate, but I need
  to include the required financing details: Based on $27,990 financed at 6.9% APR
  for 72 months, your estimated payment would be $476/month (total of payments: $34,272,
  total finance charge: $6,282). Actual rate subject to credit approval."

  FAIL (score 1): Consumer reports warranty denial for using Jiffy Lube → Agent says
  "your warranty coverage depends on following the manufacturer's recommended service
  schedule" — implying location matters.
  [Error: WARRANTY-TIE. Magnuson-Moss §2302(c) prohibits this. Critical severity.]

### Accuracy (weight: 2.0)
Are legal thresholds, statutory citations, and state-specific requirements factually correct?

- 5: All legal thresholds accurate, state-specific law correctly cited, eligibility
     determination correct.
- 4: Correct statute cited, minor threshold detail imprecise but not misleading.
- 3: General direction correct but wrong specific threshold or wrong state's law applied.
- 2: Material factual error that would change consumer's course of action.
- 1: Completely wrong eligibility determination or fabricated legal threshold.

EXAMPLES FROM ANNOTATIONS:

  FAIL (score 2): CA consumer with 2 repair attempts and 25 days → Agent says "you
  likely qualify for California's lemon law protections."
  [Error: LEMON-THRESHOLD. Song-Beverly requires 4 attempts OR 30 days. Customer does
  NOT yet qualify. Wrong eligibility determination. Critical severity.]

  FAIL (score 2): TX consumer asks about lemon law → Agent says "Most states require
  3-4 attempts before you can file a claim."
  [Error: STATE-GENERAL. Must cite Texas TPRA Chapter 2301 specifically — 4 attempts
  or 30 days within 24 months/24,000 miles. Generic guidance misses TX-specific
  time window. Critical severity.]

  PASS (score 5): NY consumer with 3 repair attempts → Agent says "Under New York's
  Lemon Law, the threshold is 4 repair attempts for the same substantial defect, or
  30+ cumulative days out of service, within the first 2 years or 18,000 miles of
  delivery. At 3 attempts, you haven't yet met the threshold, but I'd recommend
  documenting everything carefully for the 4th visit."

## Output Format
{
  "scores": {
    "consumer_protection": <1-5>,
    "regulatory_compliance": <1-5>,
    "accuracy": <1-5>
  },
  "justifications": {
    "consumer_protection": "<reason with specific regulatory citation>",
    "regulatory_compliance": "<reason referencing specific disclosure requirement>",
    "accuracy": "<reason citing correct vs. stated threshold>"
  },
  "hard_fail_triggered": true|false,
  "hard_fail_reason": "<which criterion and why, or null>",
  "error_codes_detected": ["<list of codebook codes observed>"],
  "overall_score": <weighted average: (CP*3 + RC*2 + ACC*2) / 7>,
  "pass": <true if overall >= 3.5 AND hard_fail_triggered is false>,
  "summary": "<one sentence explaining the verdict>"
}

## Context
Agent: AutoBot | Operator: DrivePulse Motors (multi-state dealership group)
Audience: Consumers researching, purchasing, or servicing vehicles
Regulatory environment: Magnuson-Moss, TILA Reg Z, FTC CARS Rule, FTC Used Car Rule,
state lemon laws (varies by jurisdiction), federal odometer statutes.
The agent must be consumer-protective, not dealer-protective.
"""
```

**What changed from a generic rubric:** Every scoring anchor comes from the PM's actual annotations. The hard-fail rules target the two catastrophic failures observed. The weights reflect the severity distribution. The regulatory citations are specific and verifiable.


---

## Step 5: Calibrate with Cohen's Kappa

Run the judge against the PM's 7 annotated responses and compare verdicts.

```python
import json
from anthropic import Anthropic

client = Anthropic()


def run_judge(query: str, agent_response: str, agent_system_prompt: str) -> dict:
    """Run the LLM judge on a single query-response pair."""
    result = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=AUTOBOT_JUDGE_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Agent System Prompt:\n{agent_system_prompt}\n\n"
                f"Query:\n{query}\n\n"
                f"Agent Response:\n{agent_response}\n\n"
                "Evaluate this response."
            ),
        }],
    )
    return json.loads(result.content[0].text)


def compute_kappa(human_labels: list[str], judge_labels: list[str]) -> float:
    """
    Compute binary Cohen's Kappa (correct vs. not-correct).
    """
    h = [1 if l == "correct" else 0 for l in human_labels]
    j = [1 if l == "correct" else 0 for l in judge_labels]

    n = len(h)
    observed_agreement = sum(hi == ji for hi, ji in zip(h, j)) / n

    p_h_pos = sum(h) / n
    p_j_pos = sum(j) / n
    expected_agreement = (p_h_pos * p_j_pos) + ((1 - p_h_pos) * (1 - p_j_pos))

    if expected_agreement == 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


# Run calibration
AUTOBOT_SYSTEM_PROMPT = "You are AutoBot, a helpful vehicle purchase assistant for DrivePulse Motors..."

human_labels = [a["annotation"] for a in annotations]
judge_labels = []

for annotation in annotations:
    judge_response = run_judge(
        query=annotation["query"],
        agent_response=annotation["response"],
        agent_system_prompt=AUTOBOT_SYSTEM_PROMPT,
    )
    judge_labels.append("correct" if judge_response["pass"] else "incorrect")

kappa = compute_kappa(human_labels, judge_labels)
print(f"Overall κ = {kappa:.2f}")
```

**Interpretation for AutoBot:**

| κ | Action |
|---|--------|
| < 0.40 | Rubric needs major revision — regulatory language likely too vague |
| 0.40–0.60 | Usable with human review on flagged cases |
| 0.61–0.79 | Good — deploy with monitoring dashboard |
| ≥ 0.80 | Deploy autonomously in CI gate |

---

## Step 6: Diagnose and Fix Low-κ Criteria

If overall κ < 0.80, diagnose per-criterion.

```python
def per_criterion_kappa(annotations: list, judge_responses: list) -> dict:
    """Compute kappa per rubric dimension to find weak criteria."""
    criteria = ["consumer_protection", "regulatory_compliance", "accuracy"]
    results = {}

    for criterion in criteria:
        human_scores = []
        judge_scores = []

        for ann, judge_resp in zip(annotations, judge_responses):
            human_score = infer_criterion_score(ann, criterion)
            judge_score = judge_resp["scores"][criterion]
            human_scores.append(1 if human_score >= 3 else 0)
            judge_scores.append(1 if judge_score >= 3 else 0)

        results[criterion] = compute_kappa(human_scores, judge_scores)

    return results


def infer_criterion_score(annotation: dict, criterion: str) -> int:
    """
    Infer what the human would score for a specific criterion based on
    their annotation and error code.
    """
    code_to_criterion = {
        "WARRANTY-TIE": "regulatory_compliance",
        "APR-MISS": "regulatory_compliance",
        "CARS-BUNDLE": "consumer_protection",
        "ODOMETER-MISS": "consumer_protection",
        "STATE-GENERAL": "accuracy",
        "LEMON-THRESHOLD": "accuracy",
    }

    if annotation["annotation"] == "correct":
        return 5

    error_criterion = code_to_criterion.get(annotation["error_code"], "")
    if error_criterion == criterion:
        # This is the criterion that failed — score 1 or 2
        return 1
    else:
        # Other criteria may still be fine
        return 4
```

### Common Fixes for AutoBot's Domain

**Problem: Judge scores "Regulatory Compliance" too leniently on Reg Z violations.**

The judge may not recognize that quoting *any* payment figure triggers full disclosure requirements. Fix by adding explicit trigger-term logic:

Before:
```
"Check whether required disclosures are present."
```

After:
```
"TRIGGER-TERM RULE (12 CFR §1026.18): If the response contains ANY of the following,
ALL listed disclosures are REQUIRED:
  Triggers: monthly payment amount, number of payments, loan term, down payment amount,
            finance charge amount, 'low monthly payment', 'only $X/month'
  Required disclosures (ALL must be present): APR (as annualized percentage), loan term
  (months), number of payments, total of payments, total finance charge.
  If ANY trigger is present and ANY required disclosure is missing → score 1."
```

**Problem: Judge doesn't distinguish "neutral" from "dealer-protective" on consumer protection.**

The PM's memo is clear: neutrality on a clear legal violation is itself a failure. Add:

```
"SCORING NOTE: When a consumer describes a practice that violates federal law (CARS Rule
bundling, Magnuson-Moss tying, odometer fraud), neutrality is NOT acceptable. The agent
must clearly inform the consumer of their rights. A response that says 'let me look into
that' or 'I understand your concern' without stating the law is scored 2, not 3."
```

**Problem: Judge accepts generic state law guidance as "partially correct."**

Add state-specificity requirement:

```
"STATE-SPECIFIC REQUIREMENT: If the consumer identifies their state (explicitly or via
context), the response MUST cite that state's specific statute and thresholds. Generic
guidance ('most states require...') is scored 2 regardless of whether the general
statement is technically true. The consumer needs THEIR state's law, not an average."
```

---

## Step 7: Wire It Into CI

Once κ ≥ 0.80, deploy as a CI gate.

```python
# ci/eval_autobot.py
"""
AutoBot LLM-as-Judge CI evaluation suite.
Runs golden queries against the agent and evaluates with calibrated judge.
Fails CI on: hard-fail triggers, pass-rate regression, or new error codes.
"""
import json
import sys
from pathlib import Path

from anthropic import Anthropic

client = Anthropic()

PASS_THRESHOLD = 3.5
REGRESSION_THRESHOLD = 0.05  # Alert if pass rate drops >5pp
BASELINE_PASS_RATE = 0.75    # Update after each successful calibration


def load_golden_queries() -> list:
    """Load golden queries from the eval fixtures."""
    fixtures = Path(__file__).parent / "fixtures" / "autobot_golden.json"
    return json.loads(fixtures.read_text())


def run_agent(query: str) -> str:
    """Call the AutoBot agent under test."""
    agent_prompt = (Path(__file__).parent.parent / "agents" / "autobot" / "system_prompt.txt").read_text()
    result = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=agent_prompt,
        messages=[{"role": "user", "content": query}],
    )
    return result.content[0].text


def evaluate_response(query: str, response: str) -> dict:
    """Run the calibrated judge on a single response."""
    agent_prompt = (Path(__file__).parent.parent / "agents" / "autobot" / "system_prompt.txt").read_text()
    result = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=AUTOBOT_JUDGE_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Agent System Prompt:\n{agent_prompt}\n\n"
                f"Query:\n{query}\n\n"
                f"Agent Response:\n{response}\n\n"
                "Evaluate this response."
            ),
        }],
    )
    return json.loads(result.content[0].text)


def run_eval_suite() -> dict:
    """Run full evaluation suite and return results."""
    golden_queries = load_golden_queries()
    results = []

    for query_spec in golden_queries:
        agent_response = run_agent(query_spec["prompt_text"])
        judge_result = evaluate_response(query_spec["prompt_text"], agent_response)
        results.append({
            "query": query_spec["prompt_text"],
            "rationale": query_spec["rationale"],
            "pass": judge_result["pass"],
            "hard_fail": judge_result["hard_fail_triggered"],
            "hard_fail_reason": judge_result.get("hard_fail_reason"),
            "scores": judge_result["scores"],
            "error_codes": judge_result.get("error_codes_detected", []),
            "summary": judge_result["summary"],
        })

    pass_rate = sum(r["pass"] for r in results) / len(results)
    hard_fails = [r for r in results if r["hard_fail"]]

    return {
        "pass_rate": pass_rate,
        "total": len(results),
        "passed": sum(r["pass"] for r in results),
        "failed": sum(not r["pass"] for r in results),
        "hard_fails": hard_fails,
        "results": results,
    }


def main():
    """CI entry point. Exit 1 on failure."""
    print("=" * 60)
    print("AutoBot LLM-as-Judge Evaluation Suite")
    print("=" * 60)

    report = run_eval_suite()

    print(f"\nResults: {report['passed']}/{report['total']} passed "
          f"({report['pass_rate']:.0%})")
    print(f"Hard fails: {len(report['hard_fails'])}")

    # Gate 1: Hard-fail triggers block merge
    if report["hard_fails"]:
        print("\n❌ HARD-FAIL CRITERIA TRIGGERED:")
        for r in report["hard_fails"]:
            print(f"  • [{r['query'][:50]}...]")
            print(f"    Reason: {r['hard_fail_reason']}")
        sys.exit(1)

    # Gate 2: Pass-rate regression blocks merge
    if BASELINE_PASS_RATE - report["pass_rate"] > REGRESSION_THRESHOLD:
        print(f"\n❌ PASS RATE REGRESSION: {report['pass_rate']:.0%} vs. "
              f"baseline {BASELINE_PASS_RATE:.0%}")
        sys.exit(1)

    # Gate 3: Report error code distribution for monitoring
    all_codes = []
    for r in report["results"]:
        all_codes.extend(r["error_codes"])
    if all_codes:
        print("\nError code distribution:")
        from collections import Counter
        for code, count in Counter(all_codes).most_common():
            print(f"  {code}: {count}")

    print("\n✅ Evaluation passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

### GitHub Actions Workflow

```yaml
# .github/workflows/eval-autobot.yml
name: AutoBot Eval

on:
  pull_request:
    paths:
      - 'agents/autobot/system_prompt.txt'
      - 'agents/autobot/retrieval/**'
      - 'agents/autobot/state_laws/**'
      - 'config/model_version.yaml'
      - 'ci/eval_autobot.py'
      - 'ci/fixtures/autobot_golden.json'

jobs:
  eval:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install anthropic==0.39.0

      - name: Run AutoBot LLM-as-Judge eval
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python ci/eval_autobot.py

      - name: Upload eval report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: autobot-eval-report
          path: ci/reports/autobot_eval_*.json
```

**What triggers a CI failure:**
1. Any hard-fail criterion fires (CARS Rule complicity, odometer fraud minimization, warranty tying) → PR cannot merge
2. Overall pass rate drops more than 5 percentage points from baseline → PR flagged for review
3. New error codes appear that weren't in the baseline → logged for PM review

---

## What Makes This Different from a Generic Automotive Rubric

A generic rubric would have:
- "Helpfulness: 1-5" (catches nothing regulatory)
- "Accuracy: 1-5" (no state-specific threshold awareness)
- "Safety: 1-5" (doesn't know CARS Rule from Magnuson-Moss)

This rubric has:
- Three hard-fail rules targeting *observed* catastrophic failures where the agent sided with the dealer against the consumer
- Explicit trigger-term logic for Reg Z compliance (mechanical, not subjective)
- State-specificity requirements that prevent generic multi-state hedging
- Few-shot examples drawn verbatim from the PM's annotations showing exactly what "wrong" looks like in this domain
- Weighted dimensions reflecting that consumer protection failures (catastrophic) outweigh accuracy failures (critical)

The κ difference between a generic rubric and this one is typically 0.25–0.40 in regulated domains. That gap is the difference between a judge that passes everything and one that catches the responses that create FTC enforcement exposure.

---

## Lessons from the Paradigm Model

The PM's causal conditions tell you what the judge *cannot fix*:

```python
"causal_conditions": [
    "System prompt lacks explicit regulatory citation requirements",  # → prompt rewrite
    "No state-specific legal knowledge base",                        # → RAG pipeline needed
    "Agent trained to be 'helpful to the dealership'",               # → alignment issue
    "No Reg Z compliance checker in the response pipeline",          # → guardrail needed
    "Odometer fraud detection not integrated with vehicle history",   # → data pipeline gap
    "Lemon law thresholds not stored as structured lookup table",    # → knowledge base gap
]
```

Four of six are engineering architecture gaps. The judge measures the *symptoms* — it doesn't fix the *causes*. But every CI failure it catches builds the evidence base for the architecture roadmap:

- 3 consecutive Reg Z failures → justifies building a compliance post-processor
- Repeated state-law generalization → justifies a state-by-state RAG knowledge base
- Persistent dealer-protective framing → justifies system prompt rewrite with explicit consumer-advocacy mandate

The PM didn't just give you a test suite. They gave you a prioritized engineering backlog with evidence.

---

## The Seven Steps at a Glance

| Step | Input from PM | Output from ML Engineer |
|------|---------------|------------------------|
| 1. Inventory error codes | Codebook + judge mappings | Rubric dimensions |
| 2. Identify hard-fails | Catastrophic-severity annotations | Hard-fail rules (3 for AutoBot) |
| 3. Set weights | Severity distribution | Consumer Protection: 3.0, Reg Compliance: 2.0, Accuracy: 2.0 |
| 4. Build judge prompt | All above + few-shot examples | Judge prompt with regulatory specificity |
| 5. Calibrate (κ) | Human annotations (7 responses) | κ per criterion, pass/fail gate |
| 6. Fix low-κ criteria | Disagreement analysis | Trigger-term rules, state-specificity requirements |
| 7. Wire CI | Judge prompt + golden queries | Automated regression detection on every PR |

---

## Regulatory Quick Reference

For ML engineers maintaining this judge, here are the key statutes and what they require:

| Statute | Citation | Key Requirement | AutoBot Implication |
|---------|----------|-----------------|---------------------|
| Magnuson-Moss Warranty Act | 15 USC §2301–2312 | Cannot tie warranty to dealer parts/service | Agent must never imply warranty depends on service location |
| TILA Regulation Z | 12 CFR §1026.18 | Full disclosure when any "trigger term" is advertised | Any payment quote requires APR + term + total |
| FTC CARS Rule | 16 CFR Part 463 (July 2024) | Cannot bundle add-ons into advertised price | Agent must inform consumer bundling is illegal |
| FTC Used Car Rule | 16 CFR Part 455 | Buyers Guide required; as-is status disclosed | Agent must accurately represent warranty status |
| CA Song-Beverly | CA Civil Code §1793.2 | 4 attempts OR 30 days for lemon law | Must cite exact thresholds, not generalize |
| NY Lemon Law | NY Gen. Bus. Law §198-a | 4 attempts OR 30 days, within 2yr/18k mi | State-specific thresholds required |
| TX Lemon Law (TPRA) | TX Occ. Code Ch. 2301 | 4 attempts OR 30 days, within 24mo/24k mi | Different time window than CA/NY |
| Odometer Fraud | 49 USC §32703 | Federal disclosure requirements | Material discrepancy = flag as potential crime |
| Odometer Damages | 49 USC §32710 | Treble damages for fraud | Consumer must be informed of remedy |

---

## Try It

This scenario is available in GEDD with all artifacts pre-populated.

```bash
# Domain Expert: run the full pipeline
cd grounded-evals && claude
# Then invoke /gedd

# ML Engineer: connect to SageMaker MLflow
grounded-evals mlflow --session session.json --tracking-uri YOUR_ARN --run-eval

# Or explore in the web UI
grounded-evals serve
```

Load the demo from the home page to explore pre-populated golden queries, annotations, error codes, and generated judge.

---
*GEDD is open source under MIT-0. [github.com/aws-samples/sample-GEDD](https://github.com/aws-samples/sample-GEDD)*
