"""
Prism Benchmark & Diagnostics Module

Provides performance measurement and system diagnostics for debugging
and validation purposes. Designed for Developer Mode only.
"""

import time
import platform
import statistics
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Stores results from a benchmark run."""
    timestamp: str = ""
    prism_version: str = "v2.3.1-stable"
    device: str = ""
    os: str = ""
    indexing_metrics: list = field(default_factory=list)
    search_metrics: list = field(default_factory=list)
    system_metrics: list = field(default_factory=list)


class Benchmarker:
    """
    Runs performance benchmarks for Prism's indexing and search operations.
    Designed as a diagnostic tool, not a marketing comparison.
    """
    
    # Standard queries for consistent benchmark comparisons
    STANDARD_QUERIES = [
        "car at intersection",
        "pedestrian crossing street",
        "traffic light",
        "bicycle on road",
        "truck turning left",
    ]
    
    def __init__(self, engine, db):
        self.engine = engine
        self.db = db
        self.last_report: Optional[BenchmarkResult] = None
    
    def run_full_benchmark(self, sample_path: str = "data/sample"):
        """
        Generator that runs a full benchmark and yields progress updates.
        
        Phases:
        1. System metrics collection
        2. Indexing benchmark
        3. Search benchmark
        """
        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            device=self.engine.device,
            os=f"{platform.system()} {platform.release()}"
        )
        
        # Phase 1: System Metrics
        yield {"phase": "system", "current": 0, "total": 3, "message": "Collecting system metrics..."}
        result.system_metrics = self._collect_system_metrics()
        yield {"phase": "system", "current": 1, "total": 3, "message": "System metrics collected"}
        
        # Phase 2: Indexing Benchmark
        yield {"phase": "indexing", "current": 0, "total": 1, "message": "Running indexing benchmark..."}
        indexing_metrics, index_progress = self._run_indexing_benchmark(sample_path)
        for prog in index_progress:
            yield prog
        result.indexing_metrics = indexing_metrics
        
        # Phase 3: Search Benchmark
        yield {"phase": "search", "current": 0, "total": len(self.STANDARD_QUERIES), "message": "Running search benchmark..."}
        search_metrics, search_progress = self._run_search_benchmark()
        for prog in search_progress:
            yield prog
        result.search_metrics = search_metrics
        
        # Complete
        self.last_report = result
        yield {"phase": "complete", "current": 1, "total": 1, "message": "Benchmark complete!"}
    
    def _collect_system_metrics(self) -> list:
        """Collect system-level metrics."""
        metrics = []
        context = f"device={self.engine.device}"
        
        try:
            import psutil
            
            # RAM usage
            mem = psutil.virtual_memory()
            metrics.append({
                "name": "ram_used_mb",
                "value": round(mem.used / (1024 ** 2), 1),
                "unit": "MB",
                "context": context
            })
            metrics.append({
                "name": "ram_total_mb",
                "value": round(mem.total / (1024 ** 2), 1),
                "unit": "MB",
                "context": context
            })
            
            # CPU count
            metrics.append({
                "name": "cpu_count",
                "value": psutil.cpu_count(logical=True),
                "unit": "cores",
                "context": context
            })
            
        except ImportError:
            logger.warning("psutil not available for system metrics")
        
        # GPU VRAM (PyTorch)
        try:
            import torch
            if torch.cuda.is_available():
                vram_used = torch.cuda.memory_allocated() / (1024 ** 2)
                vram_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)
                metrics.append({
                    "name": "gpu_vram_used_mb",
                    "value": round(vram_used, 1),
                    "unit": "MB",
                    "context": f"device=cuda, gpu={torch.cuda.get_device_name(0)}"
                })
                metrics.append({
                    "name": "gpu_vram_total_mb",
                    "value": round(vram_total, 1),
                    "unit": "MB",
                    "context": f"device=cuda, gpu={torch.cuda.get_device_name(0)}"
                })
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                metrics.append({
                    "name": "gpu_device",
                    "value": 1,
                    "unit": "Apple MPS",
                    "context": "device=mps"
                })
        except ImportError:
            pass
        
        # Model load time
        model_load_time = self._measure_model_load_time()
        if model_load_time:
            metrics.append({
                "name": "model_load_time_ms",
                "value": round(model_load_time, 1),
                "unit": "ms",
                "context": context
            })
        
        return metrics
    
    def _measure_model_load_time(self) -> Optional[float]:
        """Measure time to load models (if not already loaded)."""
        if self.engine.model is not None:
            return None  # Already loaded, can't measure
        
        start = time.perf_counter()
        self.engine._load_siglip()
        self.engine._load_yolo()
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed
    
    def _run_indexing_benchmark(self, sample_path: str):
        """Run indexing benchmark on sample data."""
        import os
        from PIL import Image
        
        metrics = []
        progress_updates = []
        context = f"device={self.engine.device}, batch_size=8"
        
        # Find sample images
        sample_files = []
        if os.path.exists(sample_path):
            for f in os.listdir(sample_path):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    sample_files.append(os.path.join(sample_path, f))
        
        if not sample_files:
            metrics.append({
                "name": "error",
                "value": 0,
                "unit": "N/A",
                "context": f"No sample files found in {sample_path}"
            })
            return metrics, progress_updates
        
        total_files = len(sample_files)
        progress_updates.append({
            "phase": "indexing",
            "current": 0,
            "total": total_files,
            "message": f"Found {total_files} sample images"
        })
        
        # Ensure models are loaded
        self.engine._load_siglip()
        self.engine._load_yolo()
        
        # Measure embedding latencies
        embedding_times = []
        detection_times = []
        failures = 0
        
        start_total = time.perf_counter()
        
        for i, file_path in enumerate(sample_files):
            try:
                img = Image.open(file_path).convert("RGB")
                
                # Detection timing
                det_start = time.perf_counter()
                _ = self.engine.yolo(img, verbose=False)
                detection_times.append((time.perf_counter() - det_start) * 1000)
                
                # Embedding timing
                emb_start = time.perf_counter()
                _ = self.engine.compute_embedding(img)
                embedding_times.append((time.perf_counter() - emb_start) * 1000)
                
            except Exception as e:
                logger.warning(f"Benchmark failed for {file_path}: {e}")
                failures += 1
            
            progress_updates.append({
                "phase": "indexing",
                "current": i + 1,
                "total": total_files,
                "message": f"Processed {os.path.basename(file_path)}"
            })
        
        total_time = time.perf_counter() - start_total
        
        # Calculate metrics
        if embedding_times:
            metrics.append({
                "name": "frames_per_second",
                "value": round(total_files / total_time, 2),
                "unit": "fps",
                "context": context
            })
            metrics.append({
                "name": "avg_embedding_latency_ms",
                "value": round(statistics.mean(embedding_times), 2),
                "unit": "ms",
                "context": context
            })
            metrics.append({
                "name": "avg_detection_latency_ms",
                "value": round(statistics.mean(detection_times), 2),
                "unit": "ms",
                "context": context
            })
            metrics.append({
                "name": "failure_rate",
                "value": round(failures / total_files * 100, 2),
                "unit": "%",
                "context": context
            })
        
        return metrics, progress_updates
    
    def _run_search_benchmark(self):
        """Run search benchmark with standard queries."""
        metrics = []
        progress_updates = []
        context = f"device={self.engine.device}"
        
        query_times = []
        embedding_times = []
        similarity_times = []
        
        for i, query in enumerate(self.STANDARD_QUERIES):
            try:
                # Text embedding timing
                emb_start = time.perf_counter()
                _ = self.engine.compute_text_embedding(query)
                emb_time = (time.perf_counter() - emb_start) * 1000
                embedding_times.append(emb_time)
                
                # Full query timing
                query_start = time.perf_counter()
                _ = self.engine.search(query, self.db, limit=10)
                query_time = (time.perf_counter() - query_start) * 1000
                query_times.append(query_time)
                
                # Similarity time is query - embedding
                similarity_times.append(query_time - emb_time)
                
            except Exception as e:
                logger.warning(f"Search benchmark failed for '{query}': {e}")
            
            progress_updates.append({
                "phase": "search",
                "current": i + 1,
                "total": len(self.STANDARD_QUERIES),
                "message": f"Tested: '{query}'"
            })
        
        # Calculate metrics
        if query_times:
            sorted_times = sorted(query_times)
            p50_idx = len(sorted_times) // 2
            p95_idx = int(len(sorted_times) * 0.95)
            
            metrics.append({
                "name": "query_latency_p50_ms",
                "value": round(sorted_times[p50_idx], 2),
                "unit": "ms",
                "context": context
            })
            metrics.append({
                "name": "query_latency_p95_ms",
                "value": round(sorted_times[min(p95_idx, len(sorted_times) - 1)], 2),
                "unit": "ms",
                "context": context
            })
            metrics.append({
                "name": "avg_embedding_time_ms",
                "value": round(statistics.mean(embedding_times), 2),
                "unit": "ms",
                "context": context
            })
            metrics.append({
                "name": "avg_similarity_time_ms",
                "value": round(statistics.mean(similarity_times), 2),
                "unit": "ms",
                "context": context
            })
        
        return metrics, progress_updates
    
    def get_last_report(self) -> Optional[BenchmarkResult]:
        """Return the last benchmark report."""
        return self.last_report
    
    def export_json(self) -> str:
        """Export last report as JSON string."""
        import json
        if not self.last_report:
            return "{}"
        
        return json.dumps({
            "timestamp": self.last_report.timestamp,
            "prism_version": self.last_report.prism_version,
            "device": self.last_report.device,
            "os": self.last_report.os,
            "indexing_metrics": self.last_report.indexing_metrics,
            "search_metrics": self.last_report.search_metrics,
            "system_metrics": self.last_report.system_metrics,
        }, indent=2)
    
    def export_markdown(self) -> str:
        """Export last report as Markdown string."""
        if not self.last_report:
            return "No benchmark report available."
        
        r = self.last_report
        lines = [
            "# Prism Benchmark Report",
            "",
            f"**Timestamp:** {r.timestamp}",
            f"**Version:** {r.prism_version}",
            f"**Device:** {r.device}",
            f"**OS:** {r.os}",
            "",
            "## System Metrics",
            "| Metric | Value | Unit | Context |",
            "|--------|-------|------|---------|",
        ]
        for m in r.system_metrics:
            lines.append(f"| {m['name']} | {m['value']} | {m['unit']} | {m['context']} |")
        
        lines.extend([
            "",
            "## Indexing Metrics",
            "| Metric | Value | Unit | Context |",
            "|--------|-------|------|---------|",
        ])
        for m in r.indexing_metrics:
            lines.append(f"| {m['name']} | {m['value']} | {m['unit']} | {m['context']} |")
        
        lines.extend([
            "",
            "## Search Metrics",
            "| Metric | Value | Unit | Context |",
            "|--------|-------|------|---------|",
        ])
        for m in r.search_metrics:
            lines.append(f"| {m['name']} | {m['value']} | {m['unit']} | {m['context']} |")
        
        return "\n".join(lines)
