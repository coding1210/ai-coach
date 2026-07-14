# Judge calibration report

- Provider: **openai** · sample size: **22**
- Exact accuracy: **0.818**
- Within one level: **1.0**
- Mean absolute error: **0.182**
- Cohen's κ: **0.753** (substantial)
- Quadratic-weighted κ: **0.936** (almost perfect)

## Confusion matrix (rows = human, cols = judge)

```
        p1  p2  p3  p4  p5
  true1   2   1   0   0   0
  true2   0   6   0   0   0
  true3   0   0   2   2   0
  true4   0   0   0   7   0
  true5   0   0   0   1   1
```

## Per-item

| competency | human | judge | Δ |
| --- | --- | --- | --- |
| py.async | L4 | L4 | 0 |
| py.async | L2 | L2 | 0 |
| llm.structured_output | L4 | L4 | 0 |
| llm.structured_output | L2 | L2 | 0 |
| rag.vector_dbs | L4 | L4 | 0 |
| rag.vector_dbs | L1 | L1 | 0 |
| safety.prompt_injection | L4 | L4 | 0 |
| safety.prompt_injection | L1 | L2 | ⚠️1 |
| rag.retrieval_eval | L4 | L4 | 0 |
| rag.chunking | L4 | L4 | 0 |
| llm.model_selection | L4 | L4 | 0 |
| llm.model_selection | L2 | L2 | 0 |
| eval.llm_judge | L2 | L2 | 0 |
| ft.decision | L2 | L2 | 0 |
| ctx.hallucination | L2 | L2 | 0 |
| agents.react_planning | L3 | L3 | 0 |
| prod.fastapi_streaming | L3 | L4 | ⚠️1 |
| eval.regression | L3 | L3 | 0 |
| ctx.system_prompt | L3 | L4 | ⚠️1 |
| llm.tokens_context | L1 | L1 | 0 |
| agents.langgraph | L5 | L4 | ⚠️1 |
| agents.tool_calling | L5 | L5 | 0 |
