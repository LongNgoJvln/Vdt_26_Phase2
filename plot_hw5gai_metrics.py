#!/usr/bin/env python3
"""
Plot metrics for AI services in the 'hw5gai' namespace.

Connects to the Prometheus HTTP API and generates time-series charts
for CPU usage, Memory usage, Network I/O, and Pod Restart count.

Requirements:
    pip install requests matplotlib pandas

Usage:
    python plot_hw5gai_metrics.py
    python plot_hw5gai_metrics.py --prom-url http://10.110.133.180:8000 --hours 6
    python plot_hw5gai_metrics.py --namespace hw5gai --hours 24 --output dashboard.png
"""

import argparse
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta


# ──────────────────────────────────────────────
# Prometheus client helpers
# ──────────────────────────────────────────────

class PrometheusClient:
    """Thin wrapper around the Prometheus HTTP API."""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api = f"{self.base_url}/api/v1"

    def check_health(self) -> bool:
        """Verify Prometheus is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/-/healthy", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def range_query(self, query: str, start: float, end: float, step: str) -> dict:
        """
        Execute a range query.
        Returns a dict: { "pod_name": pd.Series(values, index=timestamps) }
        """
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }
        resp = requests.get(f"{self.api}/query_range", params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        if data["status"] != "success":
            raise RuntimeError(f"Query failed: {data}")

        result = {}
        if "data" not in data or "result" not in data["data"]:
            return result

        for series in data["data"]["result"]:
            metric = series.get("metric", {})
            name = short_name(metric)
            values = series.get("values", [])
            if not values:
                continue
            ts = [datetime.fromtimestamp(float(v[0])) for v in values]
            vals = [float(v[1]) for v in values]
            result[name] = pd.Series(vals, index=ts, name=name)

        return result

    def instant_query(self, query: str):
        """Execute an instant query (single point in time)."""
        resp = requests.get(f"{self.api}/query", params={"query": query}, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "success":
            raise RuntimeError(f"Query failed: {data}")
        return data["data"]["result"]


# ──────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────

def short_name(metric: dict) -> str:
    """Extract a short, readable name from metric labels."""
    pod = metric.get("pod")
    container = metric.get("container")
    if pod:
        parts = pod.rsplit("-", 1)
        if len(parts) == 2 and len(parts[1]) <= 6 and parts[1].isalnum():
            return parts[0]
        return pod
    if container and container not in ("", "POD"):
        return container
    return metric.get("instance", metric.get("job", "unknown"))


def pick_step(hours: float) -> str:
    """Choose a sensible resolution step based on the time window."""
    if hours <= 1:
        return "15s"
    if hours <= 6:
        return "30s"
    if hours <= 24:
        return "60s"
    return "300s"


# ──────────────────────────────────────────────
# Main plotting functions
# ──────────────────────────────────────────────

def plot_metrics(prom: PrometheusClient, namespace: str, hours: float, output_file: str):
    """Fetch metrics from Prometheus and plot them as a 2×2 dashboard."""

    now = datetime.now()
    start = (now - timedelta(hours=hours)).timestamp()
    end = now.timestamp()
    step = pick_step(hours)
    ns = namespace

    # ── Query definitions ──────────────────────
    queries = {
        "cpu": (
            f'sum by (pod) ('
            f'rate(container_cpu_usage_seconds_total{{namespace="{ns}", container!=""}}[5m])'
            f') * 1000'
        ),
        "mem": (
            f'container_memory_working_set_bytes'
            f'{{namespace="{ns}", container!="", container!="POD"}}'
        ),
        "net_rx": (
            f'rate(container_network_receive_bytes_total{{namespace="{ns}"}}[5m])'
        ),
        "net_tx": (
            f'rate(container_network_transmit_bytes_total{{namespace="{ns}"}}[5m])'
        ),
        "restarts": (
            f'kube_pod_container_status_restarts_total{{namespace="{ns}"}}'
        ),
    }

    # ── Fetch all metrics ──────────────────────
    print("📡 Querying Prometheus...")
    results = {}
    for name, q in queries.items():
        try:
            results[name] = prom.range_query(q, start, end, step)
            print(f"   ✅ {name:12s} → {len(results[name])} series")
        except Exception as e:
            print(f"   ❌ {name:12s} → {e}")
            results[name] = {}

    net_rx = results["net_rx"]
    net_tx = results["net_tx"]

    # ── Build subplots: 2 rows × 2 cols ────────
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.subplots_adjust(hspace=0.35, wspace=0.25, top=0.92)
    fig.suptitle(
        f"AI Services Metrics — namespace `{ns}`\n"
        f"({hours}h window  ·  step={step}  ·  {datetime.now():%Y-%m-%d %H:%M})",
        fontsize=16, fontweight="bold",
    )

    ax_cpu, ax_mem = axes[0]
    ax_net, ax_restart = axes[1]

    # ── 1) CPU Usage (millicores) ──────────────
    _plot_series(ax_cpu, results["cpu"], "CPU Usage (millicores)", "CPU (mC)")
    ax_cpu.axhline(0, color="gray", ls="--", lw=0.5)

    # ── 2) Memory Usage (MB) ───────────────────
    mem_mb = {k: v / (1024 * 1024) for k, v in results["mem"].items()}
    _plot_series(ax_mem, mem_mb, "Memory Usage (MB)", "Memory (MB)")

    # ── 3) Network I/O (KB/s) ──────────────────
    for name, series in net_rx.items():
        ax_net.plot(series.index, series.values / 1024,
                    label=f"{name} (RX)", linewidth=1)
    for name, series in net_tx.items():
        ax_net.plot(series.index, series.values / 1024,
                    label=f"{name} (TX)", linewidth=1, linestyle="--")
    ax_net.set_title("Network I/O (KB/s)", fontsize=13, fontweight="bold")
    ax_net.set_ylabel("Bandwidth (KB/s)")
    ax_net.legend(fontsize=7, ncol=2, loc="upper left")
    _style_axis(ax_net)

    # ── 4) Pod Restarts (cumulative) ───────────
    _plot_series(ax_restart, results["restarts"], "Pod Restarts (cumulative)", "Restarts")

    # ── Save & Show ────────────────────────────
    if output_file:
        fig.savefig(output_file, dpi=150, bbox_inches="tight")
        print(f"\n💾 Saved to {output_file}")

    plt.show()
    return fig


def _plot_series(ax, data: dict, title: str, ylabel: str):
    """Plot multiple line series on a single axis."""
    for label, series in data.items():
        ax.plot(series.index, series.values, label=label, linewidth=1.2)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    _style_axis(ax)


def _style_axis(ax):
    """Common styling for all subplot axes."""
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.tick_params(axis="x", rotation=30, labelsize=8)


# ──────────────────────────────────────────────
# CLI entrypoint
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Plot AI service metrics from Prometheus as time-series charts."
    )
    parser.add_argument(
        "--prom-url",
        default="http://prometheus-server:9090",
        help="Prometheus base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--namespace", default="hw5gai",
        help="Kubernetes namespace (default: %(default)s)",
    )
    parser.add_argument(
        "--hours", type=float, default=6.0,
        help="Time window in hours (default: %(default)s)",
    )
    parser.add_argument(
        "--output", default="hw5gai_metrics.png",
        help="Output PNG file (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout", type=int, default=30,
        help="Request timeout in seconds (default: %(default)s)",
    )
    args = parser.parse_args()

    prom = PrometheusClient(args.prom_url, timeout=args.timeout)

    # ── Health check ───────────────────────────
    print(f"🌐 Connecting to Prometheus at {args.prom_url} ...")
    if not prom.check_health():
        print("❌ Cannot reach Prometheus. Check the URL or network access.")
        return
    print("✅ Prometheus is healthy.\n")

    # ── Plot ───────────────────────────────────
    plot_metrics(prom, args.namespace, args.hours, args.output)


if __name__ == "__main__":
    main()
