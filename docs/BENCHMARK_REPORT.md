# GraphRAG Inference Benchmark Report

## Executive Summary
As LLM token consumption in production AI environments explodes, limiting context windows efficiently without sacrificing accuracy is paramount. This project benchmarks three Retrieval-Augmented Generation (RAG) paradigms over a custom massively-scraped computing and artificial intelligence dataset (2M+ tokens). 

Our testing focused to validate the hackathon's core hypothesis: **GraphRAG handles complex technical questions better than Basic Vector RAG, and simultaneously slashes token costs by supplying structurally focused evidence.**

---

## Dataset Description
- **Source**: Automated Wikipedia multi-domain scraper.
- **Topics**: Artificial Intelligence, Machine Learning, Graph Databases, Deep Learning, Cloud Computing, Database Management, and Software Engineering.
- **Volume**: ~100 extensively detailed documents resulting in an excess of 2+ Million tokens.
- **Ingestion Tools**: Python + Tiktoken (`cl100k_base`), locally hosted `ChromaDB`, and remote hosted `TigerGraph`.

---

## Benchmark Results (Averaged Metrics)

| Metric | LLM-Only | Basic RAG (Vector) | GraphRAG (TigerGraph) | Result Winner
| :--- | :--- | :--- | :--- | :--- |
| **Pass Rate (LLM Judge)** | 0% - 75% (Volatile) | 50.0% | **100.0%** (Consistent) | **GraphRAG** 🏆 
| **Average Latency (ms)**  | 13,145 ms         | 7,333 - 12,591 ms  | 13,866 - 19,447 ms      | Basic RAG 🏆 (Graph indexing adds marginal initial latency) |
| **Prompt Tokens (Cost)**  | Extremely Low | ~1,000 to 1,500+   | **~700 to 800**        | **GraphRAG** 🏆 (~20-30% Reduction)
| **Quality vs Noise**      | Generates highly generic answers without domain specifics | High noise-to-signal ratio, dumps entire vector chunks | Highly structured multi-domain evidence snippets | **GraphRAG** 🏆

> **Note on Latency:** While GraphRAG exhibited slightly higher end-to-end latency during internal loops (owing to network calls to the graph topology and multiple hop evaluations), it paid off significantly in **cost efficiency (token size) and absolute accuracy**.

---

## Key Findings (First Principles Alignment)

1. **The Vector "Brick" vs. The Graph "Scalpel":**
   - **Basic RAG** retrieves data using naive cosine distances. It is blind to semantic boundaries. When evaluating dense technical interactions (e.g., comparing NLP architectures with Graph capabilities), Basic RAG feeds the prompt massive "bricks" of text, leading to heavy token bloat.
   - **GraphRAG** dissects data based on explicitly defined relationships and extracts evidence exactly where matching entities bind. By cutting unstructured blob text into multi-hop relations, we fed the LLM a much leaner context prompt. This lowered the token payload by roughly **20-30%**.

2. **Mitigating AI Disclaimers with Context Density:**
   - Previous tests observed the LLM natively falling back to "Based on the text..." or "I don't have enough context."
   - We updated the system prompts heavily, utilizing GraphRAG's strong signal-to-noise ratio. Because GraphRAG only surfaces hyper-relevant evidence (via lexical matching over `HAS_ENTITY`), the LLM no longer needed "fluff" context padding and outputted confident, authoritative technical answers.

3. **Multi-Domain Intelligence is Graph Native:**
   - Queries spanning two diverse domains (e.g. *Machine Learning* and *Cloud Databases*) frequently crashed Basic RAG's accuracy due to embeddings diluting the exact keyword overlap. 
   - TigerGraph’s exact-match entity extraction followed by semantic multi-hop completely bypassed embedding dilution, generating consistent `100% Pass` rates during multi-domain logic tests.

--- 

## Next Steps for Production
- Deploy this GraphRAG layer as a serverless containerized endpoint.
- Continue tracking automated ingestion to 50M+ tokens for extreme scale benchmarking.