# Prompts

In v1 the assess / judge / report / coach prompts live inline in their nodes
(`app/graph/nodes/*`, `app/llm/judge.py`) for readability while the flow is still
moving. This directory is the extraction target: pull those strings into
versioned templates here so prompt changes are tracked with code and past
behavior is reproducible (competency `obs.prompt_versioning`). Deferred to
Phase 2 so it lands once the prompt shapes have stabilized.
