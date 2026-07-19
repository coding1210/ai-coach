// Plain-language, one-line explanations of every competency and domain, aimed
// at a newcomer. Shown inline under jargon terms in the report and roadmap so a
// beginner can actually read their own evaluation. Keyed by the ids the backend
// emits (competency_map.json). Missing key → no gloss (graceful).

const COMPETENCY: Record<string, string> = {
  // RAG
  "rag.chunking": "Splitting documents into bite-size pieces so the AI can search them well.",
  "rag.embeddings": "Turning text into number-vectors so similar meaning sits close together.",
  "rag.vector_dbs": "Databases built to store those vectors and find the closest matches fast.",
  "rag.hybrid_rerank": "Mixing keyword + meaning search, then re-sorting the best results to the top.",
  "rag.retrieval_eval": "Measuring whether your search actually pulls back the right documents.",
  "rag.graph_rag": "Using a knowledge graph (linked facts) to answer questions, not just text chunks.",
  "rag.when_not": "Knowing when plain retrieval is the wrong tool for the job.",
  // Agents
  "agents.tool_calling": "Letting the model call functions/APIs — and handling that safely.",
  "agents.react_planning": "The think → act → observe loop an agent runs to solve a task step by step.",
  "agents.langgraph": "A framework for building agents as state machines you can pause and resume.",
  "agents.multi_agent": "Multiple AI agents dividing up and coordinating on a task.",
  "agents.memory": "How an agent remembers earlier context across steps or sessions.",
  "agents.mcp": "A standard way to plug tools/data into an AI app (Model Context Protocol).",
  "agents.failure_modes": "Stopping runaway loops and bad tool calls before they break things.",
  // Evaluation
  "eval.design_golden": "Building a labeled test set of 'right answers' to measure your system against.",
  "eval.llm_judge": "Using an LLM to grade outputs — fairly, without it fooling itself.",
  "eval.frameworks": "Tools (RAGAS, DeepEval, etc.) that run and track evaluations for you.",
  "eval.regression": "Catching when a change quietly makes the system worse than before.",
  "eval.offline_online": "The difference between testing on saved data vs. on live traffic.",
  "eval.agent_quality": "Measuring whether a multi-step agent actually did the job well.",
  // LLM fundamentals
  "llm.tokens_context": "How models chop text into tokens and how much they can 'see' at once.",
  "llm.sampling": "Settings like temperature that control how random/creative outputs are.",
  "llm.structured_output": "Getting reliable JSON back from a model instead of free text.",
  "llm.streaming": "Sending the answer token-by-token as it's generated, not all at once.",
  "llm.multi_provider": "Working across OpenAI / Anthropic / Groq behind one interface.",
  "llm.model_selection": "Picking the right model for the cost, speed, and quality you need.",
  "llm.cost_awareness": "Knowing what tokens cost and keeping spend under control.",
  // Context & prompting
  "ctx.system_prompt": "Writing the instructions that set the model's role and rules.",
  "ctx.few_shot": "Showing examples in the prompt so the model copies the pattern.",
  "ctx.window_mgmt": "Fitting the right info into the limited context the model can read.",
  "ctx.tool_descriptions": "Describing tools clearly enough that the model uses them correctly.",
  "ctx.templating_versioning": "Managing prompts like code — templates you can version and reuse.",
  "ctx.hallucination": "Reducing made-up answers through better prompting.",
  // Production
  "prod.fastapi_streaming": "Serving an LLM app over an API with live streaming/WebSockets.",
  "prod.caching": "Reusing past results so you don't pay to compute the same thing twice.",
  "prod.routing_fallback": "Sending requests to the best model and failing over when one is down.",
  "prod.latency_cost_opt": "Making responses faster and cheaper without hurting quality.",
  "prod.rate_concurrency": "Handling rate limits and many requests at once without crashing.",
  "prod.deployment": "Actually shipping the app so real users can reach it.",
  // Observability
  "obs.tracing": "Recording each step of a request so you can see what happened.",
  "obs.cost_monitoring": "Tracking token usage and spend over time.",
  "obs.prompt_versioning": "Keeping prompt changes tied to your code history.",
  "obs.logging": "Saving inputs/outputs so you can debug what went wrong.",
  "obs.cicd": "Automated testing and deploy pipelines for LLM apps.",
  // Python
  "py.async": "Running many tasks at once (async/await) instead of one-at-a-time.",
  "py.typing": "Type hints + Pydantic to catch mistakes and validate data.",
  "py.testing": "Writing tests, including faking LLM calls so tests stay fast.",
  "py.packaging": "Structuring and installing your project and its dependencies.",
  "py.architecture": "Organizing code cleanly so it stays easy to change.",
  "py.error_handling": "Retries, timeouts, and failing gracefully when things break.",
  // Safety
  "safety.prompt_injection": "Stopping hidden instructions in untrusted text from hijacking your app.",
  "safety.jailbreak": "Resisting attempts to trick the model past its guardrails.",
  "safety.guardrails": "Rules that block unsafe or off-limits inputs and outputs.",
  "safety.pii": "Detecting and scrubbing personal data before it leaks.",
  "safety.red_teaming": "Deliberately attacking your own system to find weaknesses.",
  // Fine-tuning
  "ft.decision": "Deciding when to fine-tune vs. just prompt or use RAG.",
  "ft.lora_qlora": "Cheap fine-tuning methods (LoRA/QLoRA) that tweak a few weights.",
  "ft.dataset_curation": "Building the clean, labeled data a fine-tune needs.",
  "ft.eval_tuned": "Checking a fine-tuned model actually got better.",
};

const DOMAIN: Record<string, string> = {
  rag: "Feeding an LLM the right documents so it answers from real sources.",
  agents: "AI that plans, uses tools, and takes multi-step actions on its own.",
  evaluation: "Proving your AI works — and catching when it regresses.",
  llm_fundamentals: "The core mechanics of calling and controlling language models.",
  context_prompt: "Getting the most out of a model through what you put in the prompt.",
  production: "Serving LLM apps reliably, fast, and affordably to real users.",
  observability: "Seeing inside a running LLM app to monitor and debug it.",
  python: "The software-engineering foundations everything else is built on.",
  safety: "Keeping the system secure, private, and hard to misuse.",
  finetuning: "Training a model on your own data when prompting isn't enough.",
};

export function glossForCompetency(id: string): string | undefined {
  return COMPETENCY[id];
}

export function glossForDomain(id: string): string | undefined {
  return DOMAIN[id];
}
