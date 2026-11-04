# LoRA, explained for someone who has never fine-tuned a model

*A walk through what actually happens when we "fine-tune GLM 5.3 Flash with a LoRA adapter" to read invoices.*

---

## 1. The problem: a smart new hire who doesn't know your rules

Imagine hiring an experienced accounts-payable clerk. They can already read any invoice. But on day one they still make
mistakes that are really about *your company's rules*:

- They write "USD" in the currency box even when no currency is printed, because "it's obviously dollars".
- They put the customer's purchase-order number in the "order number" box when your team only wants the vendor's.
- They leave a field blank when it's printed in a corner they didn't expect.

You could hand them a page of written instructions. That helps a bit, but some habits only change after they've seen a
few hundred corrected examples.

A large language model is that new hire. **Prompting** is the page of written instructions. **Fine-tuning** is the
few hundred corrected examples.

In our project the base model, GLM 5.3 Flash, scored 78.5% on 5,000 invoice fields. Writing the rules into the prompt
got it to 80.7%. But the rules also made it *too* cautious: it started leaving real totals blank. That's the point where
you stop writing instructions and start showing examples.

---

## 2. What "a model" is, physically

A model is a very large pile of numbers called **weights** (or parameters), arranged in tables called **matrices**.
When you send the model an invoice image and a question, the input is turned into numbers and multiplied through
layer after layer of these matrices until numbers come out the other end that turn back into words — here, a JSON object.

Everything the model "knows" — how to read a date, what an invoice looks like, how to write JSON — is encoded in those
weights. GLM 5.3 Flash has billions of them.

**Fine-tuning means changing the weights a little, so the model's outputs move toward the answers you want.**

---

## 3. Full fine-tuning, and why we don't do it

The obvious way to fine-tune is to adjust *every* weight. That's called **full fine-tuning**. It works, but:

- **It's expensive.** You need enough GPU memory to hold the model, a gradient for every weight, and the optimizer's
  bookkeeping for every weight — several times the size of the model itself.
- **Every task gets its own full copy.** An invoice model, a contract model and a receipt model would each be a
  complete multi-gigabyte model to store and serve.
- **It's easy to break things.** Changing billions of numbers with a few thousand examples can make the model forget
  skills you didn't mean to touch.

For a one-day hackathon with a $50 budget, none of that is an option.

---

## 4. LoRA: leave the model alone, add a small correction

**LoRA** stands for **Low-Rank Adaptation**. The idea fits in one sentence:

> Freeze all of the original weights, and learn a small "correction" that gets added on top.

Take one weight matrix inside the model, call it **W**. Say it's 4,096 × 4,096 — about **16.8 million** numbers.

Full fine-tuning would learn a change **ΔW** of the same size: another 16.8 million numbers.

LoRA bets that the change you need is much simpler than that. Instead of learning ΔW directly, it learns two thin
matrices and multiplies them together:

```
ΔW  =  B  ×  A
      (4096 × 16)   (16 × 4096)
```

- **A** squeezes the 4,096-wide input down to just 16 numbers.
- **B** expands those 16 numbers back to 4,096.

Together they produce a full-size correction, but they only contain 4,096 × 16 × 2 = **131,072** numbers. That's
**less than 1%** of the original matrix.

That **16** is the **rank**. It's the "width" of the bottleneck, and it controls how expressive the correction can be:

| Rank | Numbers per 4,096 × 4,096 matrix | Share of the original |
| --- | --- | --- |
| 4 | 32,768 | 0.2% |
| **16 (ours)** | **131,072** | **0.8%** |
| 64 | 524,288 | 3.1% |
| full fine-tune | 16,777,216 | 100% |

When the model runs, each adapted layer computes its usual output **plus** the correction:

```
output  =  W · x   +   (α / r) · B · A · x
          original       LoRA correction
          (frozen)       (trained)
```

Two details worth knowing:

- **B starts at zero.** So before training, the correction is exactly zero and the model behaves exactly like the
  original. Training moves it away from the original only as far as the examples require.
- **α / r is a volume knob.** α ("alpha") scales how loudly the correction speaks. We use rank 16 and alpha 32, so the
  correction is multiplied by 2. This mostly matters because it keeps the effective learning rate sensible if you change
  the rank.

### Why "low rank" works

It sounds too good to be true that 1% of the numbers can do the job. The reason it works: the base model already knows
how to read documents. You're not teaching it to see; you're nudging *which* of its existing skills it uses and how it
formats the answer — "answer null when no currency is printed", "the order number is the one labelled P.O." Those nudges
turn out to be simple, low-dimensional changes. Research and a lot of practice show LoRA usually gets close to full
fine-tuning for this kind of task, at a fraction of the cost.

### Where the adapters go

A model has several kinds of matrices. Our run attaches LoRA adapters to three:

- **Attention** (`train_attn=True`): the part that decides which pieces of the input to look at together — for
  example linking the words "Invoice No." to the number printed next to them.
- **MLP / feed-forward** (`train_mlp=True`): the part that transforms what it's looking at — much of the model's stored
  knowledge and habits.
- **Unembedding** (`train_unembed=True`): the final layer that turns the model's internal numbers into the next word.
  Adapting it helps with output style, like always writing `null` instead of "N/A".

---

## 5. What training actually does, step by step

Here's our run, in plain terms.

### The examples

Each training example is a conversation with the right answer filled in:

```
[system]    You are an accounts-payable assistant...
[user]      <page image>  Extract these fields ... Answer with only a JSON object.
[assistant] {"document_id": "990304502", "date_issue": "03/25/99", "currency_code_amount_due": "$",
             "order_id": null, ...}
```

The assistant's answer comes straight from DocILE's human labels. We used **1,400** such documents.

### Turning it into tokens

Models don't read characters; they read **tokens** (chunks of text, roughly ¾ of a word each). The image is also turned
into tokens. In our project one example is about **2,800 tokens**, and roughly 2,700 of them are the image. That's
why training cost is dominated by the pictures, not the JSON.

### The loss: how wrong was the guess?

For each example, the model reads the image and prompt, then tries to predict the answer one token at a time. At every
position we check how much probability it gave to the *correct* next token. If it was confident and right, the
penalty is small; if it was confident and wrong, the penalty is large. Averaged together, that penalty is the
**loss** (technically, cross-entropy).

Importantly, **we only score the answer**. The model isn't penalised for failing to predict the prompt or the image —
we don't want it to learn to write invoices, only to read them.

### One step

1. Take a **batch** of 16 examples.
2. **Forward pass:** run them through the model and compute the loss.
3. **Backward pass:** work out, for every LoRA number, which direction would have made the loss smaller. That
   direction is the **gradient**. The original weights are frozen, so we only compute gradients for the small A and B
   matrices — this is where LoRA saves most of the memory.
4. **Optimizer step:** move each LoRA number a little in that direction. How far is set by the **learning rate**
   (ours: 0.0001). The optimizer we use, **Adam**, keeps a running average of past gradients so steps are smoother.

That's one **step**. 1,400 documents ÷ 16 per batch ≈ **88 steps**. Going through every training example once is one
**epoch**; we do one epoch.

On Fireworks' serverless training, our Python script on a laptop runs this loop, but steps 2–4 happen on Fireworks'
GPUs:

```python
tc = service.create_lora_training_client(base_model="accounts/fireworks/models/glm-5p3-flash",
                                         rank=16, alpha=32)
for batch in batches(examples, size=16):
    tc.forward_backward(batch, "cross_entropy").result()   # steps 2 and 3
    tc.optim_step(adam).result()                           # step 4
```

### Watching the loss

Our loss started at **0.37** and was around **0.07** a third of the way through. Falling loss means the model's guesses
are getting closer to the labelled answers on the training examples.

Falling training loss is *necessary but not sufficient*. A model can also get better at the training examples by
memorising them. The only way to know if it learned something general is to test on documents it has never seen —
which is why the test set was locked away before any of this started.

---

## 6. What you get at the end

Not a new model — an **adapter**: a small file holding the trained A and B matrices for every adapted layer. To use it,
you load the original GLM 5.3 Flash and apply the adapter on top.

That has practical upsides:

- **Small to store and move**: megabytes to a few gigabytes, versus the whole model.
- **Swappable**: one base model can serve an invoice adapter, a contract adapter and a receipt adapter, chosen per
  request.
- **Reversible**: remove the adapter and you have the original model back, untouched.

On Fireworks, the lifecycle looks like this:

1. **Save for sampling**: snapshot the adapter and score the test set with those exact weights, inside the training
   session. This is the evidence for the hackathon.
2. **Promote**: turn the snapshot into a model in your Fireworks account.
3. **Deploy**: serve it on a dedicated (on-demand) deployment. This step bills for GPU time, so we haven't done it.

---

## 7. Will it actually help? How we check

A fine-tune that improves the training loss can still be worse on real documents. So we do exactly what we did for the
baseline:

- Run the fine-tuned model on the **same 500 test documents**, same prompt, temperature 0.
- Score the same 5,000 field cases.
- Call the gain real only if two tests agree:
  - **McNemar's test**: on the cases where exactly one model is right, does the fine-tune win far more often than a
    coin flip would?
  - **Layout-cluster bootstrap**: if we'd been handed a different set of document templates, would the gain still be
    above zero?
- Report separately the 124 test documents whose layout never appears in training. That's the honest test of whether
  the model learned to *read*, rather than memorised what a familiar template looks like.

---

## 8. When to reach for LoRA

| Situation | Try first |
| --- | --- |
| The model doesn't know a rule that fits in a sentence | A better prompt |
| The model knows the rules but applies them inconsistently | LoRA fine-tune |
| You need a specific output format, every time | LoRA fine-tune |
| You need cheaper or faster inference than a big model | LoRA on a small model |
| The model lacks basic knowledge entirely (a new language, a new domain) | More data, maybe full fine-tuning |

Our project sits in the second and third rows: GLM can read the invoices, but applies DocILE's labelling conventions
inconsistently, and prompting fixed one error by causing another.

---

## 9. Common pitfalls

- **Testing on what you trained on.** Split by *group* (here, layout cluster), not by row, or near-duplicates leak
  between train and test.
- **Too high a learning rate or too many epochs.** The model memorises the training set; training loss keeps falling
  while test accuracy drops.
- **Inconsistent labels.** The model learns your labels, including their mistakes. Garbage in, confident garbage out.
- **Comparing against a weakened baseline.** Same prompt, same settings, same test set for every system — or the gain
  isn't real.

---

## Glossary

| Term | Meaning |
| --- | --- |
| Weights / parameters | The numbers inside the model that encode what it knows |
| Fine-tuning | Adjusting weights with examples so outputs move toward what you want |
| SFT (supervised fine-tuning) | Fine-tuning on examples with the correct answer written out |
| LoRA | Freeze the model; learn a small low-rank correction (B × A) added to some layers |
| Rank (r) | Width of the LoRA bottleneck; higher = more expressive, more parameters |
| Alpha (α) | Scales the LoRA correction by α / r |
| Adapter | The file of trained LoRA matrices, applied on top of the base model |
| Token | A chunk of text (or a patch of an image) — the unit models read and are billed by |
| Loss | How wrong the model's predictions were; training tries to lower it |
| Gradient | The direction to nudge each trainable number to lower the loss |
| Learning rate | How big each nudge is |
| Batch | The group of examples processed in one step |
| Step | One forward pass, backward pass and weight update |
| Epoch | One full pass through the training data |
| Overfitting | Memorising the training examples instead of learning the general pattern |
