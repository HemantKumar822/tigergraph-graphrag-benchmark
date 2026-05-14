# System Architecture

## First-Principles Workflow Analysis

This application acts as a comparative benchmarking platform to test the hypothesis that **Graph-augmented Generation (GraphRAG) lowers LLM token consumption while maintaining or improving accuracy compared to standard Vector RAG.**

### Core Components
1. **Frontend Benchmark UI (Next.js):** 
   - Accepts a user query and an (optional) Ground Truth answer.
   - Triggers three parallel requests to the backend to minimize synchronous wait times.
   - Renders telemetry data (Tokens In/Out, Latency, Cost, BERTScore, Judge Score) dynamically.

2. **Backend Gateway (FastAPI):**
   - Routes incoming user evaluation requests to three distinct Q&A pipelines.
   - Handles the asynchronous execution of evaluator metrics.

3. **The Three Pipelines:**
   - **Pipeline 1: LLM-Only (`llm_only.py`)** -> Passes the raw query to Gemini-3.1-flash-lite. No context retrieval. High hallucination risk.
   - **Pipeline 2: Basic RAG (`basic_rag.py`)** -> Uses `ChromaDB` (via ONNX local embeddings) for semantic search. Returns large document chunks to the LLM. Extremely high token usage.
   - **Pipeline 3: GraphRAG (`graphrag.py`)** -> Connects to **TigerGraph Cloud/Local**. Extracts entities, expands query context through multi-hop graph traversal, scores semantic overlap, and filters to highly dense textual evidence. Vastly reduces payload size while keeping factual grounding.

4. **Concurrent Evaluator (`concurrent.py`):**
   - If Ground Truth is provided, automatically scores the generated candidate answers.
   - Runs **BERTScore** (Hugging Face / DistilBERT) for semantic overlap.
   - Runs **LLM-as-a-judge** (Gemini) for a rigorous `PASS/FAIL` fact-check.

---

## Architectural Diagram

```text
                      +-------------------+
                      |    User (UI)      |
                      |  (Next.js App)    |
                      +---------+---------+
                                | (Query + Ground Truth)
                                v
                      +-------------------+
                      |  FastAPI Gateway  |
                      +---------+---------+
                                |
            +-------------------+-------------------+
            |                   |                   |
            v                   v                   v
      +-----------+       +-----------+       +-----------+
      | Pipeline 1|       | Pipeline 2|       | Pipeline 3|
      | LLM-Only  |       | Vector RAG|       | GraphRAG  |
      +-----------+       +-----+-----+       +-----+-----+
            |                   |                   |
            |                   | (KNN Search)      | (Hybrid Rescue + Graph Traversal)
            |                   v                   v
            |             +-----------+       +-----------+
            |             | ChromaDB  |       | TigerGraph|
            |             | (Local)   |       | (Cloud)   |
            |             +-----------+       +-----------+
            |                   |                   |
            +-------------------+-------------------+
                                | (Answers)
                                v
                      +-------------------+
                      | LLM Generation    |
                      | Gemini 3.1 Flash  |
                      +---------+---------+
                                | 
                                v
                      +-------------------+
                      | Concurrent Eval   |
                      | (BERT & Judge)    |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      | UI Metric Display |
                      | (Tokens, Latency) |
                      +-------------------+
```