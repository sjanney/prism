# Benchmarks & Diagnostics

Prism includes an optional **Benchmarks & Diagnostics** feature for developers and engineers who want to understand and validate system performance.

> **Note**: This feature is hidden by default. Enable Developer Mode to access it.

## Enabling Developer Mode

Edit your configuration file at `~/.prism/config.yaml`:

```yaml
developer_mode: true
```

Restart Prism, and you'll see the "Advanced" section in Settings.

## Accessing Benchmarks

1. Navigate to **Settings** (press `Tab` to cycle)
2. Under **ADVANCED**, press `b` to open Benchmarks
3. Press `Enter` to run a benchmark

## What Gets Measured

### Indexing Metrics
| Metric | Description |
|--------|-------------|
| `frames_per_second` | Total frames indexed per second |
| `avg_embedding_latency_ms` | Mean SigLIP inference time |
| `avg_detection_latency_ms` | Mean YOLO inference time |
| `failure_rate` | Percentage of skipped/failed frames |

### Search Metrics
| Metric | Description |
|--------|-------------|
| `query_latency_p50_ms` | 50th percentile query time |
| `query_latency_p95_ms` | 95th percentile query time |
| `avg_embedding_time_ms` | Text embedding generation time |
| `avg_similarity_time_ms` | Vector comparison time |

### System Metrics
| Metric | Description |
|--------|-------------|
| `ram_used_mb` | Current RAM usage |
| `gpu_vram_used_mb` | GPU VRAM usage (if available) |
| `model_load_time_ms` | Time to load AI models |
| `cpu_count` | Number of CPU cores |

## Keyboard Shortcuts (in Benchmark View)

| Key | Action |
|-----|--------|
| `Enter` | Run benchmark |
| `r` | Re-run benchmark |
| `Esc` | Return to Settings |

## Interpreting Results

Benchmarks are designed as a **diagnostic tool**, not a leaderboard. Use them to:

- Understand if performance issues stem from hardware, configuration, or dataset
- Justify Prism internally with concrete metrics  
- Debug slowdowns by comparing metric breakdowns
- Generate reproducible reports for GitHub issues

## Export (Coming Soon)

Future versions will support exporting reports as JSON or Markdown for:
- Internal evaluation
- GitHub issues
- Enterprise purchasing discussions
