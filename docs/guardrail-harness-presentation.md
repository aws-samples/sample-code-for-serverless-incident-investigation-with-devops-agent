# Bedrock Guardrails: Latency & False Positive Benchmarking with Kiro
## TMEGS Offsite | May 19, 2026 | Vijay Kumar

---

## Slide 1: Title

**Bedrock Guardrails: Latency & False Positive Benchmarking with Kiro**

Vijay Kumar | Sr. TAM, TMEGS
TMEGS GenAI Offsite | May 19, 2026

*Speaker Notes:*
Quick intro — I built a guardrail optimization harness using Kiro's spec-driven development. I'll show you the problem, the solution, and how Kiro changed the way I approached building it.

---

## Slide 2: The Customer Problem

**"Our guardrails block legitimate customer queries"**

- Bedrock Guardrails are powerful — but hard to tune
- Too aggressive → false positives (legitimate queries blocked)
- Too loose → unsafe content passes through
- No easy way to benchmark latency impact of guardrail configurations
- Customers ask: "What's the right filter strength for MY use case?"

*Speaker Notes:*
This came from real customer conversations. TAMs hear this regularly — customer enables guardrails, then support tickets come in because legitimate queries are getting blocked. There's no tooling to systematically test and tune guardrail configurations before deploying them.

---

## Slide 3: What I Built

**Guardrail Optimization Harness**

Three capabilities:
1. **False Positive Analyzer** — Tests guardrail configs against known-safe queries, measures block rate
2. **Latency Benchmark** — Measures p50/p95/p99 latency impact of guardrail configurations
3. **Filter Strength Tuner** — Iterates through filter strengths, finds optimal balance

Output: Actionable report with pass rates, latency percentiles, and tuning recommendations

*Speaker Notes:*
This is a CLI tool. You point it at a guardrail, give it a corpus of test queries, and it produces a report telling you exactly where your false positives are, what your latency overhead is, and what filter strength gives you the best balance. Published as a blog on builder.aws.

---

## Slide 4: Without Kiro — How I Would Have Built This

**Traditional approach: ~25 hours across 3-4 days**

| Phase | Time |
|-------|------|
| Research Bedrock Guardrails API, find examples | 2-3 hrs |
| Design architecture (in my head or a doc) | 1-2 hrs |
| Scaffold project (TypeScript, jest, tsconfig) | 1 hr |
| Write core logic (analyzer, benchmark, tuner) | 8-10 hrs |
| Build CLI interface | 2 hrs |
| Report generation | 2 hrs |
| Write tests, debug edge cases | 3-4 hrs |
| Refactor, fix bugs | 2-3 hrs |
| Documentation | 1-2 hrs |

**Pain points:** Blank page problem, design decisions made mid-code, tests bolted on after, docs written last (or never)

*Speaker Notes:*
Be honest here — this is how most of us build things. You start coding, realize halfway through that your architecture doesn't work, refactor, then write tests at the end when you're tired. Documentation is an afterthought. The result works but it's messy and hard for anyone else to pick up.

---

## Slide 5: With Kiro — What Actually Happened

**Spec-driven approach: ~5 hours in 1 day**

| Phase | Time | What Kiro Did |
|-------|------|---------------|
| Spec creation | 30 min | Requirements, design, correctness properties, task breakdown |
| Implementation | 3 hrs | Executed tasks — code, tests, CLI, reports (I reviewed) |
| Iteration | 1 hr | I gave feedback, Kiro refined |
| Blog + polish | 1 hr | Kiro helped write the blog post |

**4-5x faster. Better architecture. Documentation as a byproduct.**

*Speaker Notes:*
The key insight: I spent my time reviewing and giving feedback, not writing boilerplate. Kiro forced the design-first approach — I had requirements and correctness properties before a single line of code existed. The spec IS the documentation.

---

## Slide 6: The Kiro Workflow (Visual)

**Idea → Spec → Implementation → Ship**

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────┐     ┌──────────┐
│ Rough Idea  │ ──→ │  Requirements    │ ──→ │  Design Doc    │ ──→ │  Tasks   │
│ "I need a   │     │  13 user stories │     │  Architecture  │     │  15 task │
│  guardrail  │     │  Acceptance      │     │  Correctness   │     │  groups  │
│  test tool" │     │  criteria        │     │  properties    │     │          │
└─────────────┘     └──────────────────┘     └────────────────┘     └──────────┘
                              ↕                        ↕                    ↓
                     I reviewed & refined    I reviewed & refined    Kiro executed
                                                                    I reviewed code
```

*Speaker Notes:*
Walk through each step. I started with a rough idea — "I need a tool to test guardrail false positives." Kiro asked clarifying questions, produced requirements with acceptance criteria, then a technical design with correctness properties (formal specifications of what "correct" means). Then it broke that into tasks and executed them one by one. At every stage, I was the decision-maker — Kiro was the builder.

---

## Slide 7: What the Spec Looks Like (Screenshot)

**Show: `.kiro/specs/bedrock-guardrails-optimization/`**

- `requirements.md` — User stories, acceptance criteria
- `design.md` — Architecture, data flow, correctness properties
- `tasks.md` — Implementation checklist with sub-tasks

*Speaker Notes:*
Open the actual files in Kiro and show them. Point out: "This is my documentation. I didn't write a separate design doc or README — the spec IS the documentation. Anyone on my team can read this and understand what was built, why, and how."

---

## Slide 8: Key Moments — Where Kiro Shined

**1. Correctness Properties**
- Kiro proposed formal properties: "false positive rate must be calculable", "latency measurements must be statistically valid"
- These became my test assertions — tests designed WITH the code, not after

**2. Edge Cases I Missed**
- Kiro's design identified: "What if the guardrail returns a timeout vs a block? They're different failure modes."
- I wouldn't have thought of this until production

**3. Iteration Speed**
- "The report format isn't readable enough" → Kiro rewrote the report generator in 2 minutes
- Traditional approach: 30 min of refactoring

*Speaker Notes:*
These are the "aha" moments. The correctness properties one is the biggest — Kiro made me think about what "correct" means before writing code. That's something senior engineers do naturally but it's easy to skip when you're in a hurry.

---

## Slide 9: The Result

**Published: builder.aws blog post**
**Reusable: Any TAM can run this for their customers**

- CLI tool: `npx ts-node src/cli/index.ts analyze --guardrail-id <ID>`
- Produces: false positive report, latency report, tuning recommendations
- Tests: 65 unit tests passing
- Used by: [your customer count if any]

*Speaker Notes:*
The blog is live. The tool is in my repo. Any TAM facing the "guardrails are too aggressive" conversation can point their customer at this or run it themselves. That's the force-multiplier effect.

---

## Slide 10: Live Demo

**Demo: Run the harness against a guardrail configuration**

1. Show the CLI command
2. Show the output report (false positive rate, latency percentiles)
3. Show how changing filter strength affects results

*Speaker Notes:*
Keep this to 3-4 minutes. Run the command, show the report, point out the key metrics. If time allows, show the Kiro spec files side by side.

---

## Slide 11: Takeaways for TAMs

**Why this matters for your customer conversations:**

1. **Kiro is not just a code generator** — it's a thinking partner that forces good engineering practices (design first, test alongside, document as you go)

2. **Spec-driven development scales** — I used the same approach for the streaming media workshop (7 labs), the DevOps Agent demo, and this harness. Same workflow, different domains.

3. **The output is customer-ready** — Blog published, tool reusable, documentation built-in. Not a hack that only I understand.

4. **Time savings are real** — 4-5x for this project. Your mileage varies, but the blank-page elimination alone is worth it.

*Speaker Notes:*
End with the call to action: "If you have a customer problem that needs a tool or a demo, try Kiro's spec workflow. Start with the idea, let it build the spec, review it, then let it execute. You'll be surprised how fast you go from idea to something shippable."

---

## Slide 12: Q&A

**Questions?**

Vijay Kumar | @vijaykrs
Blog: builder.aws.com (search "Bedrock Guardrails Optimization")
Repo: Available on request

---
