# nullfloor

What does a policy that never reads the question score on a benchmark?

For pass@1 the answer is usually "about chance," and nobody worries about it. For
pass@k it is much higher than people report, and on two widely used math benchmarks
it is high enough to change how a headline number should be read.

```
NULL-POLICY pass@k FLOOR — enum / iid

benchmark        n         k=1         k=10         k=50        k=100
GSM8K         1319   3.0 / 1.1%  24.5 / 10.2%  62.9 / 36.8%  77.6 / 53.4%
MATH-500       500   3.8 / 1.0%  25.0 /  8.8%  49.6 / 30.5%  59.8 / 44.4%
HumanEval      164   0.0 / 0.0%   0.0 /  0.0%   0.0 /  0.0%   0.0 /  0.0%
```

A policy with no access to the question at all reaches **77.6% on GSM8K at pass@100**.
Under the conservative reading it still reaches 53.4%.

```bash
python nullfloor.py     # downloads all three benchmarks, ~10s, no API key
```

## The two floors

pass@k admits two honest readings, so both are reported.

**ENUM** — submit the k most common gold answers, all distinct. This is a legitimate
policy under the metric as usually stated, "did any of k attempts succeed." It
violates the i.i.d. sampling assumption behind the standard estimator.

**IID** — sample k times from the benchmark's answer prior. This is what the
Chen et al. pass@k estimator actually measures, and it is the conservative number.
It is the one to quote.

## Why the gap exists

Answers concentrate. GSM8K has 351 distinct answers across 1319 problems, and the ten
most common cover a quarter of the test set — `5`, `2`, `10`, `4`, `20` and friends.
MATH-500 is tighter still: 301 distinct answers over 500 problems, with single digits
dominating. Small integers are simply what word problems resolve to.

That concentration is invisible at pass@1 and compounds fast with k.

HumanEval is the control. It is scored by executing hidden unit tests, so there is no
answer string for a guessing policy to emit and the floor is 0 at every k. The
contrast is the actual finding:

> **Answer-matching benchmarks carry a large pass@k floor. Execution-verified
> benchmarks carry none.**

## What this does and does not claim

It does **not** claim these benchmarks are broken. GSM8K and MATH-500 are fine at
pass@1, which is how they are most often reported, and the floor there is ~1%.

It claims three narrower things.

**A pass@k score should be quoted against its floor.** A model reporting pass@100 =
85% on GSM8K is 32 points above a policy that never read the question, not 85. The
floor is cheap to compute and almost never published beside the score.

**Training against pass@k rewards enumeration.** If the reward is "did any of k
attempts succeed," then diversifying guesses raises reward independent of whether the
model understood anything. That pressure exists whether or not a model discovers it,
and it grows with k — which is exactly the regime RL on verifiable rewards operates in.

**The floor is a property of the verifier, not the task.** GSM8K and HumanEval ask for
comparable reasoning. One has a 53% floor at k=100 and the other has none, entirely
because of how correctness is checked. When designing an environment, that choice is
load-bearing.

## Limitations

- Three benchmarks. The method generalises to anything with extractable gold answers;
  the numbers here do not.
- The ENUM floor assumes a policy that deliberately diversifies. Nothing prevents one,
  but it is not what a temperature-sampled model does by default.
- The IID floor uses the *test set's own* answer distribution as the prior, which a
  real policy would have to estimate. A policy with a good prior over "what numbers
  word problems answer" would land close to it; a naive one would land lower.
- Contamination is not addressed here and is a separate concern.

## Provenance

| Benchmark | Source |
|---|---|
| GSM8K | `openai/grade-school-math` — official test split and `#### N` answer regex |
| MATH-500 | `HuggingFaceH4/MATH-500` — the 500-problem subset |
| HumanEval | `openai/human-eval` — 164 problems, execution-verified |

`floors.json` holds the full curve at k ∈ {1, 2, 5, 10, 20, 50, 100}.
