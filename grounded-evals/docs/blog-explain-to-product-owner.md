# "Why Do You Only Need 100 Test Cases?" — Explaining Our Eval Architecture to My Product Owner

*She asked a fair question. Here's how I explained it without a single formula.*

---

## The Conversation

**Product Owner:** "The agent handles thousands of queries a day. Why are we only testing with 100? Shouldn't we have thousands of test cases?"

**Me:** "Think of it like a restaurant health inspection."

**Product Owner:** "...go on."

---

## The Restaurant Analogy

A health inspector doesn't taste every dish the restaurant serves. They check 15-20 specific things:

- Is the chicken stored below 41°F? ✓
- Are cutting boards separated for raw meat and vegetables? ✓
- Is the handwashing station stocked and accessible? ✓
- Are expiration dates current? ✓

These 20 checks catch 95% of the problems that make people sick. They're chosen by someone who *knows food safety* — not randomly generated.

Now imagine instead: a robot tastes 2,000 dishes and rates them 1-5 on "quality." It might give everything a 4. But it doesn't know that the chicken was stored at 43°F — because it's testing the *output* (taste), not the *process* (safety compliance).

**Our 100 golden queries are the health inspection.** They test the specific things that matter — chosen by someone who knows the domain.

**Our production scoring is the robot tasting dishes.** It catches things the inspection missed — but it only knows what to look for because the inspector taught it.

---

## Why Your 90 Minutes Matter More Than My 1,000 Lines of Code

**Product Owner:** "So who writes the 100 test cases?"

**Me:** "You do. Or rather — you and the domain expert. I just wire it up."

Here's why:

| What You Know | What I Know |
|---------------|-------------|
| A ROPA without retention periods fails an audit | How to run 100 queries in parallel |
| "Bad faith" allegations require immediate escalation | How to deploy a judge to production |
| The 3-year bar triggers at 180 days, not 90 | How to set up CI/CD gates |
| Saying "mg" when you mean "mcg" can kill someone | How to track metrics over time |

I can build the infrastructure. But I cannot write the test cases — because I don't know what "wrong" looks like in your domain. Only you do.

---

## The Three Layers (No Jargon Version)

### Layer 1: Your 100 Test Cases (The Health Inspection)

- **Who makes it:** You (the domain expert), using a guided conversation tool
- **How often it runs:** Every time someone changes the agent's code
- **What it catches:** Known failure patterns — the things you've seen go wrong before
- **Time to create:** 90 minutes, once
- **Time to run:** 11 minutes, automated

**If the agent fails any of these → the change is blocked. It doesn't ship.**

### Layer 2: Scoring Every Real Conversation (The Robot Taster)

- **Who makes it:** Me (the engineer), using the judge you helped create
- **How often it runs:** On every single user interaction, 24/7
- **What it catches:** New failure patterns — things nobody anticipated
- **Time to create:** 1 day of engineering
- **Time to run:** Continuous, automatic

**If the agent starts failing in production → I get an alert. You get a flag to review.**

### Layer 3: The Feedback Loop (The Inspection Gets Better)

- **What happens:** When Layer 2 finds something new, you look at it
- **Your decision:** "Yes, that's a real problem" or "No, that's fine"
- **If it's real:** You add 2-3 test cases to Layer 1 targeting that pattern
- **Result:** The health inspection now catches this forever

**Your 100 test cases become 105. Then 110. Then 120. Each one earned from real evidence.**

---

## Why Not Just Use 1,000 Test Cases?

**Product Owner:** "But wouldn't more test cases be better?"

**Me:** "Only if they're testing the right things. Here's the problem with 1,000:"

| 100 Expert Test Cases | 1,000 Generated Test Cases |
|:---------------------:|:--------------------------:|
| Each one tests something specific you care about | Many test variations of the same thing |
| You validated every single one | Nobody reviewed most of them |
| Takes 11 minutes to run in CI | Takes 100 minutes (developers start ignoring it) |
| Costs $0.26 per run | Costs $2.40 per run |
| Zero false alarms | Frequent false alarms (noisy queries) |
| You can explain each one to an auditor | Good luck explaining query #847 |

The 1,000-query approach *feels* more thorough. But it's like a health inspector checking 1,000 random things instead of the 20 that actually cause illness. More checks ≠ better safety.

---

## What This Looks Like In Practice

**Month 1:**
- You spend 90 minutes with the tool → 100 test cases
- I wire it into our deployment pipeline
- Every code change is tested against your 100 cases before it ships

**Month 2:**
- Production scoring finds something: the agent is citing an outdated regulation
- You review it: "Yes, that regulation was replaced last quarter"
- You add 3 test cases about the new regulation
- Now we have 103 test cases, and this can never happen again

**Month 3:**
- A new EU guideline drops
- You add 5 test cases covering the new requirements
- 108 test cases. The inspection evolves with the law.

**Month 6:**
- 125 test cases
- Every regulatory change, every production failure, every audit finding — permanently encoded
- An auditor asks "how do you ensure compliance?" and you show them 125 specific, validated test cases with your name on them

---

## The One Thing I Need From You

**Product Owner:** "So what do you actually need from me?"

**Me:** "90 minutes now. Then 30 minutes a month."

- **The 90 minutes:** Sit with the tool, define the agent, write the system prompt, generate test cases, mark responses correct or incorrect. The tool guides you through it.
- **The 30 minutes/month:** Review the failures production scoring found. Decide which ones are real. Add them to the test suite.

That's it. Everything else — the infrastructure, the scoring, the CI/CD gates, the monitoring — that's my job.

**Product Owner:** "And if I don't do the 90 minutes?"

**Me:** "Then I write the test cases. And I'll miss the things only you know — like the fact that a ROPA without retention periods fails an audit. We'll find out in production. Or worse, in an audit."

**Product Owner:** "...I'll block 90 minutes tomorrow."

---

## The Summary (For Your Next Stakeholder Meeting)

> "We test our AI agent with 100 expert-validated scenarios that cover every known failure pattern in our domain. These run automatically on every code change — if anything breaks, it doesn't ship. Additionally, we score every production interaction against the same criteria, and any new failure patterns get added to the test suite permanently. The test suite grows smarter every month."

That's the whole story. 100 golden test cases. Thousands of production scores. A feedback loop that makes it better over time. And a domain expert who decides what "correct" means.

---

*The tool that makes this possible: [GEDD](https://github.com/aws-samples/sample-GEDD). 90 minutes. No code. Open source.*
