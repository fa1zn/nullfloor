"""What does a policy that never reads the question score on a benchmark?

Downloads three public benchmarks and computes their null-policy floor at pass@k:
the score reachable by guessing from the benchmark's own answer distribution,
with no access to the input at all.

Two floors are reported, because pass@k admits two honest readings.

  ENUM  Submit the k most common gold answers, all distinct. A legitimate policy
        under the metric as stated ("did any of k attempts succeed"), but it
        violates the i.i.d. sampling assumption behind the standard estimator.

  IID   Sample k times from the answer prior. This is what the Chen et al.
        pass@k estimator actually measures, and it is the conservative number.

Usage:  python nullfloor.py
"""

import collections
import gzip
import io
import json
import re
import urllib.request

import numpy as np

SOURCES = {
    "GSM8K": ("https://raw.githubusercontent.com/openai/grade-school-math/"
              "master/grade_school_math/data/test.jsonl", "gsm8k"),
    "MATH-500": ("https://huggingface.co/datasets/HuggingFaceH4/MATH-500/"
                 "resolve/main/test.jsonl", "math500"),
    "HumanEval": ("https://raw.githubusercontent.com/openai/human-eval/"
                  "master/data/HumanEval.jsonl.gz", "humaneval"),
}
KS = (1, 2, 5, 10, 20, 50, 100)
GSM_ANS = re.compile(r"#### (\-?[0-9\.\,]+)")


def fetch(url):
    raw = urllib.request.urlopen(url, timeout=60).read()
    if url.endswith(".gz"):
        raw = gzip.decompress(raw)
    return [json.loads(line) for line in io.StringIO(raw.decode()) if line.strip()]


def gold_answers(rows, kind):
    if kind == "gsm8k":
        return [GSM_ANS.search(r["answer"]).group(1).replace(",", "") for r in rows]
    if kind == "math500":
        return [r["answer"].strip() for r in rows]
    if kind == "humaneval":
        # Scored by executing hidden unit tests. There is no answer string a
        # guessing policy could emit, so the floor is 0 at every k by
        # construction — this is the control, not an omission.
        return None
    raise ValueError(kind)


def floors(gold):
    n = len(gold)
    counts = collections.Counter(gold)
    ranked = [a for a, _ in counts.most_common()]
    p = np.array([counts[a] / n for a in gold])
    out = []
    for k in KS:
        enum = sum(counts[a] for a in ranked[: min(k, len(ranked))]) / n * 100
        iid = float((1 - (1 - p) ** k).mean() * 100)
        out.append({"k": k, "enum": enum, "iid": iid})
    return {"n": n, "distinct": len(counts), "floors": out,
            "top": [(a, counts[a] / n * 100) for a, _ in counts.most_common(5)]}


def main():
    results = {}
    for name, (url, kind) in SOURCES.items():
        rows = fetch(url)
        gold = gold_answers(rows, kind)
        if gold is None:
            results[name] = {"n": len(rows), "distinct": None, "execution_verified": True,
                             "floors": [{"k": k, "enum": 0.0, "iid": 0.0} for k in KS]}
        else:
            results[name] = floors(gold)

    header = "".join(f"{('k=%d' % k):>14}" for k in KS)
    print("NULL-POLICY pass@k FLOOR — enum / iid\n")
    print(f"{'benchmark':<12}{'n':>6}{header}")
    for name, r in results.items():
        row = "".join("%6.1f /%5.1f%%" % (f["enum"], f["iid"]) for f in r["floors"])
        print(f"{name:<12}{r['n']:>6}{row}")

    print("\nHumanEval is execution-verified — no answer string exists to guess.")
    print("The contrast is the finding: answer-matching benchmarks carry a large")
    print("pass@k floor; execution-verified ones carry none.\n")

    for name, r in results.items():
        if r.get("execution_verified"):
            continue
        print(f"{name}: {r['distinct']} distinct answers over {r['n']} problems")
        for a, pct in r["top"]:
            print(f"   {a[:36]:<38} {pct:.2f}%")
        print()

    json.dump(results, open("floors.json", "w"), indent=1)
    print("-> floors.json")


if __name__ == "__main__":
    main()
