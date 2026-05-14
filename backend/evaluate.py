import os
import sys
import json
import asyncio
import time
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.schemas import InferenceRequest, InferenceConfig
from app.pipelines.llm_only import run_llm_only_inference
from app.pipelines.basic_rag import run_basic_rag_inference
from app.pipelines.graphrag import run_graphrag_inference

console = Console()

class BenchmarkStats:
    def __init__(self, name: str):
        self.name = name
        self.total_questions = 0
        self.total_latency_ms = 0.0
        self.cumulative_tokens = 0
        self.pass_count = 0
        self.na_count = 0
        self.success_count = 0  # Number of successful pipeline executions
        
    def add_result(self, result: Any):
        self.total_questions += 1
        if isinstance(result, Exception):
            return
            
        self.success_count += 1
        metrics = result.metrics
        self.total_latency_ms += metrics.total_latency_ms if hasattr(metrics, 'total_latency_ms') else metrics.latency_ms
        self.cumulative_tokens += (metrics.prompt_tokens + metrics.completion_tokens)
        
        if metrics.judge_score == "PASS":
            self.pass_count += 1
        elif metrics.judge_score == "N/A":
            self.na_count += 1

    @property
    def avg_latency(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count

    @property
    def pass_rate(self) -> float:
        # Pass rate is calculated out of valid evaluations (excluding N/A and pipeline failures)
        valid_evals = self.pass_count + (self.success_count - self.pass_count - self.na_count)
        if valid_evals == 0:
            return 0.0
        return (self.pass_count / valid_evals) * 100.0

async def evaluate_pipeline(pipeline_fn, questions: List[Dict[str, str]], stats: BenchmarkStats, progress: Progress, task_id):
    # To prevent rate limits, we execute sequentially with a small delay
    for item in questions:
        req = InferenceRequest(
            query=item["query"],
            ground_truth=item["ground_truth"],
            config=InferenceConfig(temperature=0.0)
        )
        
        try:
            result = await pipeline_fn(req)
            stats.add_result(result)
        except Exception as e:
            console.print(f"[red]Error in {stats.name} for query '{item['query'][:20]}...': {e}[/red]")
            stats.add_result(e)
            
        progress.advance(task_id)
        # Small delay to prevent API rate limiting
        await asyncio.sleep(0.5)

async def main(dataset_path: str):
    if not os.path.exists(dataset_path):
        console.print(f"[red]Dataset not found: {dataset_path}[/red]")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    num_questions = len(questions)
    console.print(f"[bold green]Starting benchmark on {num_questions} questions...[/bold green]\n")

    stats_llm = BenchmarkStats("LLM Only")
    stats_rag = BenchmarkStats("Basic RAG")
    stats_graph = BenchmarkStats("GraphRAG")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_llm = progress.add_task("[cyan]Evaluating LLM Only...", total=num_questions)
        task_rag = progress.add_task("[magenta]Evaluating Basic RAG...", total=num_questions)
        task_graph = progress.add_task("[yellow]Evaluating GraphRAG...", total=num_questions)

        # Run pipelines concurrently but internally they loop over questions
        # Running all 3 pipelines concurrently for each question might hit rate limits fast,
        # so we run the pipelines' question loops concurrently. Since we added a 0.5s delay
        # per question, it should be manageable.
        await asyncio.gather(
            evaluate_pipeline(run_llm_only_inference, questions, stats_llm, progress, task_llm),
            evaluate_pipeline(run_basic_rag_inference, questions, stats_rag, progress, task_rag),
            evaluate_pipeline(run_graphrag_inference, questions, stats_graph, progress, task_graph)
        )

    # Build Results Table
    console.print("\n[bold]Benchmark Results[/bold]")
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Pipeline", style="dim", width=15)
    table.add_column("Total Questions", justify="right")
    table.add_column("Avg Latency (ms)", justify="right")
    table.add_column("Pass Rate (%)", justify="right")
    table.add_column("Cumulative Tokens", justify="right")

    for s in [stats_llm, stats_rag, stats_graph]:
        table.add_row(
            s.name,
            str(s.total_questions),
            f"{s.avg_latency:.2f}",
            f"{s.pass_rate:.1f}%",
            str(s.cumulative_tokens)
        )

    console.print(table)

if __name__ == "__main__":
    default_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_questions.json")
    dataset = sys.argv[1] if len(sys.argv) > 1 else default_data
    
    # We must allow testing environment variable if we want mock data
    os.environ["TESTING"] = "true"
    
    asyncio.run(main(dataset))
