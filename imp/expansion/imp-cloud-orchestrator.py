"""Adaptive orchestration utilities for distributed cloud processing."""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set

ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "core"
LOG_DIR = ROOT / "logs"

HEALTH_LOG = LOG_DIR / "imp-node-health.json"
DISCOVERY_LOG = LOG_DIR / "imp-network-discovery.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json


class CloudOrchestrator:
    """Combine node telemetry with discovery summaries for adaptive scheduling."""

    def __init__(self, history_limit: int = 10) -> None:
        self.history_limit = max(1, history_limit)

    # -- public API -----------------------------------------------------
    def plan(
        self,
        nodes: Sequence[str],
        statuses: Sequence[Mapping[str, Any]] | None,
        meta: MutableMapping[str, Any],
        *,
        backlog: int | None = None,
    ) -> Dict[str, Any]:
        """Return orchestrated ordering and interval adjustments for *nodes*."""

        if not nodes:
            return {}

        health = self._load_health()
        discovery_summary = self._latest_discovery_summary()

        history = self._prepare_history(meta)
        ranked = self._rank_nodes(nodes, statuses or [], health, discovery_summary)
        region_allocations = self._region_allocations(ranked, statuses or [], health)
        risk_nodes = self._identify_risks(ranked, health, discovery_summary)
        confidence_scores = self._confidence_scores(
            ranked,
            statuses or [],
            health,
            discovery_summary,
            risk_nodes,
        )
        strategy, strategy_reason = self._determine_strategy(
            backlog,
            confidence_scores,
            risk_nodes,
            discovery_summary,
            history,
        )
        capacities = self._recommend_capacities(
            ranked,
            health,
            backlog,
            meta,
            history,
            risk_nodes=risk_nodes,
            region_allocations=region_allocations,
            confidence_scores=confidence_scores,
        )
        interval = self._recommend_interval(meta, ranked, health, backlog, history)
        stagger = self._recommend_stagger(ranked, health, backlog, discovery_summary)
        trend = self._trend_interval(history, interval)
        forecast_capacity = self._forecast_capacity(history, capacities)
        confidence_average = (
            mean(confidence_scores.values()) if confidence_scores else 0.0
        )
        operational_mode, operational_reason = self._classify_operational_mode(
            backlog,
            confidence_average,
            risk_nodes,
            discovery_summary,
            history,
            forecast_capacity,
        )
        redundancy_plan = self._assign_redundancy(
            ranked,
            risk_nodes,
            region_allocations,
            statuses or [],
            health,
        )
        energy_score = self._estimate_energy_score(
            ranked,
            statuses or [],
            health,
        )
        failure_projection = self._simulate_failure_impact(
            ranked,
            capacities,
            risk_nodes,
            history,
        )
        burst_candidates = self._recommend_burst_nodes(
            ranked,
            statuses or [],
            health,
            backlog,
            discovery_summary,
            capacities,
            risk_nodes,
        )
        standby_nodes = self._recommend_standby_nodes(
            ranked,
            capacities,
            risk_nodes,
            health,
        )

        telemetry = {
            "ranked_nodes": ranked,
            "base_interval": meta.get("remote_interval"),
            "recommended_interval": interval,
            "trend_interval": trend,
            "capacity_total": sum(capacities.values()),
            "stagger": stagger,
            "forecast_capacity": forecast_capacity,
            "risk_nodes": list(risk_nodes),
            "region_allocations": region_allocations,
            "confidence_scores": confidence_scores,
            "confidence_average": round(confidence_average, 4),
            "strategy": strategy,
            "strategy_reason": strategy_reason,
            "operational_mode": operational_mode,
            "operational_reason": operational_reason,
            "redundancy_plan": redundancy_plan,
            "energy_score": energy_score,
            "failure_projection": failure_projection,
            "burst_candidates": burst_candidates,
            "standby_nodes": standby_nodes,
        }
        if discovery_summary:
            telemetry["slow_host_count"] = discovery_summary.get("slow_host_count")
            telemetry["flapping_host_count"] = discovery_summary.get("flapping_host_count")

        self._update_history(
            history,
            nodes=ranked,
            interval=interval,
            capacities=capacities,
            backlog=backlog,
            stagger=stagger,
            risk_nodes=risk_nodes,
            forecast_capacity=forecast_capacity,
            region_allocations=region_allocations,
            confidence_scores=confidence_scores,
            confidence_average=confidence_average,
            strategy=strategy,
            strategy_reason=strategy_reason,
            operational_mode=operational_mode,
            operational_reason=operational_reason,
            redundancy_plan=redundancy_plan,
            energy_score=energy_score,
            failure_projection=failure_projection,
            burst_candidates=burst_candidates,
            standby_nodes=standby_nodes,
        )
        telemetry["history_window"] = min(len(history), self.history_limit)
        telemetry["forecast_capacity"] = forecast_capacity
        telemetry["risk_nodes"] = list(risk_nodes)
        telemetry["region_allocations"] = region_allocations

        meta["remote_capacities"] = capacities
        meta["remote_stagger"] = stagger
        meta["remote_risk_nodes"] = list(risk_nodes)
        meta["remote_region_allocations"] = region_allocations
        meta["remote_capacity_forecast"] = forecast_capacity
        meta["remote_confidence_scores"] = confidence_scores
        meta["remote_confidence_average"] = round(confidence_average, 4)
        meta["remote_strategy"] = strategy
        meta["remote_strategy_reason"] = strategy_reason
        meta["remote_operational_mode"] = operational_mode
        meta["remote_operational_reason"] = operational_reason
        meta["remote_redundancy_plan"] = redundancy_plan
        meta["remote_energy_score"] = energy_score
        meta["remote_failure_projection"] = failure_projection
        meta["remote_burst_candidates"] = burst_candidates
        meta["remote_standby_nodes"] = standby_nodes

        return {
            "nodes": ranked,
            "interval": interval,
            "capacities": capacities,
            "stagger": stagger,
            "strategy": strategy,
            "strategy_reason": strategy_reason,
            "confidence_scores": confidence_scores,
            "operational_mode": operational_mode,
            "operational_reason": operational_reason,
            "redundancy_plan": redundancy_plan,
            "energy_score": energy_score,
            "failure_projection": failure_projection,
            "burst_candidates": burst_candidates,
            "standby_nodes": standby_nodes,
            "telemetry": telemetry,
        }

    # -- helpers --------------------------------------------------------
    def _prepare_history(self, meta: MutableMapping[str, Any]) -> List[Dict[str, Any]]:
        history = meta.get("orchestration_history")
        if not isinstance(history, list):
            history = []
            meta["orchestration_history"] = history
        return history

    def _load_health(self) -> Dict[str, Dict[str, Any]]:
        data = read_json(HEALTH_LOG, {})
        if isinstance(data, dict):
            return {str(key): value for key, value in data.items() if isinstance(value, dict)}
        return {}

    def _latest_discovery_summary(self) -> Dict[str, Any] | None:
        history = read_json(DISCOVERY_LOG, [])
        if not isinstance(history, list) or not history:
            return None
        return history[-1].get("summary") if isinstance(history[-1], dict) else None

    def _rank_nodes(
        self,
        nodes: Sequence[str],
        statuses: Sequence[Mapping[str, Any]],
        health: Mapping[str, Mapping[str, Any]],
        summary: Mapping[str, Any] | None,
    ) -> List[str]:
        status_map = {str(entry.get("host")): entry for entry in statuses if entry.get("host")}
        slow_ips = self._slow_ip_lookup(summary)

        scored: List[tuple[str, float]] = []
        for host in nodes:
            host_key = str(host)
            status = status_map.get(host_key, {})
            info = health.get(host_key, {})
            score = 0.0

            if status.get("reachable"):
                score += 2.0
            elif info.get("state") == "online":
                score += 1.0
            else:
                score -= 1.0

            uptime = info.get("uptime_ratio")
            if isinstance(uptime, (int, float)):
                score += max(0.0, float(uptime)) * 2.5

            avg_latency = info.get("average_latency_ms")
            if isinstance(avg_latency, (int, float)):
                score += self._latency_bonus(float(avg_latency))

            if info.get("latency_warning_streak"):
                streak = float(info.get("latency_warning_streak", 0))
                score -= min(1.5, 0.1 * streak)

            if info.get("flapping"):
                score -= 0.75

            failures = info.get("consecutive_failures")
            if isinstance(failures, (int, float)) and failures > 0:
                score -= min(2.0, 0.25 * float(failures))

            last_latency = info.get("last_latency_ms")
            if isinstance(last_latency, (int, float)):
                latency_tag = f"{host_key}:{int(last_latency)}"
                if latency_tag in slow_ips:
                    score -= 0.5

            scored.append((host_key, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        ranked = [host for host, score in scored if score > 0]
        if not ranked:
            return list(nodes)
        return ranked

    def _confidence_scores(
        self,
        nodes: Sequence[str],
        statuses: Sequence[Mapping[str, Any]],
        health: Mapping[str, Mapping[str, Any]],
        summary: Mapping[str, Any] | None,
        risk_nodes: Iterable[str],
    ) -> Dict[str, float]:
        status_lookup = {str(entry.get("host")): entry for entry in statuses if entry.get("host")}
        slow_ips = self._slow_ip_lookup(summary)
        risk_lookup = {str(node) for node in risk_nodes}
        scores: Dict[str, float] = {}

        for host in nodes:
            host_key = str(host)
            info = health.get(host_key, {})
            status = status_lookup.get(host_key, {})
            score = 0.35

            uptime = info.get("uptime_ratio")
            if isinstance(uptime, (int, float)):
                score += max(0.0, min(0.45, float(uptime) * 0.45))

            avg_latency = info.get("average_latency_ms")
            if isinstance(avg_latency, (int, float)) and avg_latency > 0:
                if avg_latency <= 150:
                    score += 0.18
                elif avg_latency <= 350:
                    score += 0.1
                elif avg_latency <= 600:
                    score -= 0.05
                else:
                    score -= 0.12

            if status.get("reachable"):
                score += 0.12
            elif status:
                score -= 0.05

            if info.get("latency_warning_streak"):
                score -= min(0.18, 0.03 * float(info.get("latency_warning_streak", 0)))

            if info.get("flapping"):
                score -= 0.1

            failures = info.get("consecutive_failures")
            if isinstance(failures, (int, float)) and failures > 0:
                score -= min(0.25, 0.05 * float(failures))

            last_latency = info.get("last_latency_ms")
            if isinstance(last_latency, (int, float)):
                latency_tag = f"{host_key}:{int(last_latency)}"
                if latency_tag in slow_ips:
                    score -= 0.08

            if host_key in risk_lookup:
                score -= 0.25

            scores[host_key] = round(max(0.0, min(1.0, score)), 4)

        return scores

    def _determine_strategy(
        self,
        backlog: int | None,
        confidence_scores: Mapping[str, float],
        risk_nodes: Iterable[str],
        summary: Mapping[str, Any] | None,
        history: Sequence[Mapping[str, Any]],
    ) -> tuple[str, str]:
        backlog = int(backlog or 0)
        values = list(confidence_scores.values())
        average = mean(values) if values else 0.0
        risk_lookup = [str(node) for node in risk_nodes]
        risk_count = len(risk_lookup)
        slow_count = 0
        if summary:
            slow_count = int(summary.get("slow_host_count") or 0)

        last_average = None
        if history:
            last_entry = history[-1]
            if isinstance(last_entry, Mapping):
                confidence_block = last_entry.get("confidence")
                if isinstance(confidence_block, Mapping):
                    last_average = confidence_block.get("average")

        if risk_count or slow_count:
            reason = (
                f"risks={risk_count}, slow_hosts={slow_count}, avg_conf={average:.2f}"
            )
            strategy = "conservative" if average < 0.55 else "stabilize"
            return strategy, reason

        node_count = max(1, len(confidence_scores) or 1)
        if backlog > node_count * 2 and average >= 0.6:
            reason = f"backlog={backlog}, nodes={node_count}, avg_conf={average:.2f}"
            return "surge", reason

        if last_average is not None and average > float(last_average or 0.0) + 0.08:
            reason = f"confidence rising from {last_average} to {average:.2f}"
            return "accelerate", reason

        reason = f"steady backlog={backlog}, avg_conf={average:.2f}"
        return "balanced", reason

    def _latency_bonus(self, latency_ms: float) -> float:
        if latency_ms <= 0:
            return 0.5
        if latency_ms <= 120:
            return 1.5
        if latency_ms <= 250:
            return 1.0
        if latency_ms <= 400:
            return 0.5
        return max(-0.5, 0.5 - (latency_ms - 400) / 400)

    def _recommend_interval(
        self,
        meta: Mapping[str, Any],
        nodes: Sequence[str],
        health: Mapping[str, Mapping[str, Any]],
        backlog: int | None,
        history: Sequence[Mapping[str, Any]],
    ) -> float | None:
        try:
            base_interval = float(meta.get("remote_interval", 180.0))
        except Exception:
            base_interval = 180.0

        if not nodes:
            return base_interval

        latencies: List[float] = []
        warnings = 0
        for host in nodes:
            info = health.get(str(host), {})
            avg_latency = info.get("average_latency_ms")
            if isinstance(avg_latency, (int, float)) and avg_latency > 0:
                latencies.append(float(avg_latency))
            if info.get("latency_state") == "slow":
                warnings += 1

        adjustment = 1.0
        if latencies:
            avg_latency = mean(latencies)
            if avg_latency <= 150:
                adjustment *= 0.6
            elif avg_latency <= 400:
                adjustment *= 0.9
            else:
                adjustment *= min(2.0, 1.0 + (avg_latency - 400) / 400)

        if warnings:
            adjustment *= 1.1 + min(0.5, warnings * 0.05)

        if isinstance(backlog, int) and backlog > len(nodes):
            adjustment *= 0.85

        interval = base_interval * adjustment

        previous = [
            float(entry.get("interval"))
            for entry in history[-self.history_limit :]
            if isinstance(entry, Mapping) and isinstance(entry.get("interval"), (int, float))
        ]
        if previous:
            interval = 0.65 * interval + 0.35 * mean(previous)

        minimum = float(meta.get("remote_interval_min", 30.0))
        maximum = float(meta.get("remote_interval_max", base_interval * 2.5))
        return max(minimum, min(interval, maximum))

    def _recommend_capacities(
        self,
        nodes: Sequence[str],
        health: Mapping[str, Mapping[str, Any]],
        backlog: int | None,
        meta: Mapping[str, Any],
        history: Sequence[Mapping[str, Any]],
        *,
        risk_nodes: Set[str],
        region_allocations: Mapping[str, Sequence[str]],
        confidence_scores: Mapping[str, float] | None = None,
    ) -> Dict[str, int]:
        if not nodes:
            return {}

        base_per_node = int(meta.get("remote_base_concurrency", 1))
        base_per_node = max(1, base_per_node)

        target_total = base_per_node * len(nodes)
        if isinstance(backlog, int) and backlog > len(nodes):
            target_total += min(backlog - len(nodes), base_per_node * len(nodes))

        history_totals = [
            int(entry.get("capacity_total"))
            for entry in history[-self.history_limit :]
            if isinstance(entry, Mapping) and isinstance(entry.get("capacity_total"), (int, float))
        ]
        if history_totals:
            avg_total = mean(history_totals)
            target_total = int(round((target_total + avg_total) / 2))

        max_total = int(meta.get("remote_max_concurrency", max(target_total, len(nodes))))
        max_total = max(len(nodes), max_total)
        target_total = max(len(nodes), min(target_total, max_total))

        node_max = int(meta.get("remote_node_max_concurrency", max(2, base_per_node * 4)))

        weights: List[tuple[str, float]] = []
        confidence_scores = confidence_scores or {}
        for host in nodes:
            info = health.get(str(host), {})
            uptime = float(info.get("uptime_ratio", 0.5))
            latency = float(info.get("average_latency_ms", 350.0))
            latency_factor = max(0.2, 1.3 - min(latency, 900.0) / 500.0)
            failures = float(info.get("consecutive_failures", 0.0))
            failure_penalty = min(0.6, failures * 0.05)
            warning_penalty = 0.15 if info.get("latency_state") == "slow" else 0.0
            recovery_bonus = 0.2 if info.get("recovered") else 0.0
            confidence = float(confidence_scores.get(str(host), 0.5))
            confidence = max(0.0, min(1.0, confidence))

            weight = max(0.05, uptime * latency_factor - failure_penalty - warning_penalty)
            weight += recovery_bonus
            weight *= 0.5 + confidence * 0.5
            weights.append((str(host), weight))

        weight_sum = sum(weight for _, weight in weights)
        if weight_sum <= 0:
            return {str(host): min(node_max, base_per_node) for host in nodes}

        raw_allocations: Dict[str, int] = {}
        for host, weight in weights:
            allocation = max(1, min(node_max, int(round(weight / weight_sum * target_total))))
            raw_allocations[host] = allocation

        for host in nodes:
            if host in risk_nodes:
                raw_allocations[host] = 0

        safe_nodes = [host for host in nodes if host not in risk_nodes]
        if not safe_nodes:
            return {host: 0 for host in nodes}

        allocated = sum(raw_allocations[host] for host in safe_nodes)
        if allocated < target_total:
            remainder = target_total - allocated
            for host, _ in sorted(weights, key=lambda item: item[1], reverse=True):
                if host in risk_nodes:
                    continue
                if remainder <= 0:
                    break
                if raw_allocations[host] < node_max:
                    raw_allocations[host] += 1
                    remainder -= 1
        elif allocated > target_total:
            excess = allocated - target_total
            for host, _ in sorted(weights, key=lambda item: item[1]):
                if host in risk_nodes:
                    continue
                if excess <= 0:
                    break
                if raw_allocations[host] > 1:
                    raw_allocations[host] -= 1
                    excess -= 1

        for region_nodes in region_allocations.values():
            available = [node for node in region_nodes if node in safe_nodes]
            if not available:
                continue
            strongest = max(available, key=lambda node: raw_allocations.get(node, 0))
            if raw_allocations.get(strongest, 0) == 0:
                raw_allocations[strongest] = 1

        return raw_allocations

    def _recommend_stagger(
        self,
        nodes: Sequence[str],
        health: Mapping[str, Mapping[str, Any]],
        backlog: int | None,
        summary: Mapping[str, Any] | None,
    ) -> float:
        if not nodes:
            return 0.0

        latencies: List[float] = []
        slow_count = 0
        for host in nodes:
            info = health.get(str(host), {})
            avg_latency = info.get("average_latency_ms")
            if isinstance(avg_latency, (int, float)) and avg_latency > 0:
                latencies.append(float(avg_latency))
            if info.get("latency_state") == "slow":
                slow_count += 1

        if latencies:
            base = min(5.0, max(0.25, mean(latencies) / 600.0))
        else:
            base = 0.5

        if isinstance(backlog, int) and backlog > len(nodes) * 2:
            base *= 0.7
        elif slow_count:
            base *= 1.0 + min(0.5, 0.1 * slow_count)

        if summary and summary.get("flapping_host_count"):
            base *= 1.1

        return round(float(min(5.0, max(0.2, base))), 3)

    def _trend_interval(
        self, history: Sequence[Mapping[str, Any]], interval: float
    ) -> float:
        if not history:
            return 0.0
        last = history[-1]
        last_interval = last.get("interval") if isinstance(last, Mapping) else None
        if isinstance(last_interval, (int, float)):
            return round(interval - float(last_interval), 3)
        return 0.0

    def _update_history(
        self,
        history: List[Dict[str, Any]],
        *,
        nodes: Sequence[str],
        interval: float,
        capacities: Mapping[str, int],
        backlog: int | None,
        stagger: float,
        risk_nodes: Iterable[str],
        forecast_capacity: float,
        region_allocations: Mapping[str, Sequence[str]],
        confidence_scores: Mapping[str, float],
        confidence_average: float,
        strategy: str,
        strategy_reason: str,
        operational_mode: str,
        operational_reason: str,
        redundancy_plan: Mapping[str, str],
        energy_score: float,
        failure_projection: Mapping[str, Any],
        burst_candidates: Sequence[str],
        standby_nodes: Sequence[str],
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "nodes": list(nodes),
            "interval": float(interval),
            "capacity_total": int(sum(capacities.values())),
            "backlog": backlog,
            "stagger": float(stagger),
            "risk_nodes": list(risk_nodes),
            "forecast_capacity": float(forecast_capacity),
            "region_allocations": {
                key: list(value) for key, value in region_allocations.items()
            },
            "confidence": {
                "average": round(float(confidence_average), 4),
                "scores": {key: round(float(value), 4) for key, value in confidence_scores.items()},
            },
            "strategy": {
                "mode": strategy,
                "reason": strategy_reason,
            },
            "operational_mode": {
                "mode": operational_mode,
                "reason": operational_reason,
            },
            "redundancy_plan": dict(redundancy_plan),
            "energy_score": round(float(energy_score), 4),
            "failure_projection": dict(failure_projection),
            "burst_candidates": list(burst_candidates),
            "standby_nodes": list(standby_nodes),
        }
        history.append(entry)
        if len(history) > self.history_limit:
            del history[:-self.history_limit]

    def _classify_operational_mode(
        self,
        backlog: int | None,
        confidence_average: float,
        risk_nodes: Iterable[str],
        summary: Mapping[str, Any] | None,
        history: Sequence[Mapping[str, Any]],
        forecast_capacity: float,
    ) -> tuple[str, str]:
        risk_ratio = 0.0
        risk_nodes = list(risk_nodes)
        if history:
            last_backlog = history[-1].get("backlog")
        else:
            last_backlog = None
        if isinstance(backlog, int) and history:
            if isinstance(last_backlog, int):
                backlog_delta = backlog - last_backlog
            else:
                backlog_delta = backlog
        else:
            backlog_delta = backlog or 0
        if risk_nodes:
            denominator = history[-1].get("capacity_total", len(risk_nodes)) if history else len(risk_nodes)
            denominator = max(1, int(denominator))
            risk_ratio = len(risk_nodes) / denominator

        slow_count = summary.get("slow_host_count") if summary else 0
        flapping_count = summary.get("flapping_host_count") if summary else 0
        capacity_baseline = history[-1].get("capacity_total", 1) if history else 1
        backlog_level = (backlog or 0) / max(1, int(capacity_baseline))

        if backlog_level > 2.5 or confidence_average < 0.35:
            return (
                "crisis",
                "High backlog or low confidence requires emergency scaling",
            )
        if risk_ratio >= 0.5 or flapping_count:
            return (
                "resilience",
                "Multiple risky or flapping nodes demand resilient scheduling",
            )
        if backlog_delta < 0 and confidence_average >= 0.75 and not slow_count:
            return (
                "optimization",
                "Backlog shrinking with strong confidence allows optimisation",
            )
        baseline_capacity = history[-1].get("capacity_total", 0) if history else 0
        if forecast_capacity and forecast_capacity > max(1, baseline_capacity) * 1.3:
            return (
                "expansion",
                "Forecast capacity growth suggests expansion of workloads",
            )
        return (
            "steady",
            "Workload within expected bounds; maintain steady scheduling",
        )

    def _assign_redundancy(
        self,
        ranked: Sequence[str],
        risk_nodes: Iterable[str],
        region_allocations: Mapping[str, Sequence[str]],
        statuses: Sequence[Mapping[str, Any]],
        health: Mapping[str, Mapping[str, Any]],
    ) -> Dict[str, str]:
        redundancy: Dict[str, str] = {}
        status_map = {str(entry.get("host")): entry for entry in statuses if entry.get("host")}
        region_map: Dict[str, str] = {}
        for region, hosts in region_allocations.items():
            for host in hosts:
                region_map[str(host)] = str(region)

        available = [host for host in ranked if host not in set(risk_nodes)]
        for host in risk_nodes:
            host_key = str(host)
            host_region = region_map.get(host_key) or status_map.get(host_key, {}).get("metadata", {}).get("region")
            fallback = None
            for candidate in available:
                candidate_region = region_map.get(candidate) or status_map.get(candidate, {}).get("metadata", {}).get("region")
                if host_region and candidate_region == host_region:
                    fallback = candidate
                    break
            if fallback is None and available:
                fallback = available[0]
            if fallback:
                redundancy[host_key] = fallback
        return redundancy

    def _estimate_energy_score(
        self,
        ranked: Sequence[str],
        statuses: Sequence[Mapping[str, Any]],
        health: Mapping[str, Mapping[str, Any]],
    ) -> float:
        status_map = {str(entry.get("host")): entry for entry in statuses if entry.get("host")}
        scores: List[float] = []
        for host in ranked:
            info = health.get(str(host), {})
            metadata = status_map.get(str(host), {}).get("metadata", {})
            uptime = info.get("uptime_ratio")
            latency = info.get("average_latency_ms")
            uptime_component = float(uptime) if isinstance(uptime, (int, float)) else 0.6
            latency_penalty = 0.0
            if isinstance(latency, (int, float)):
                latency_penalty = min(0.6, float(latency) / 800.0)
            profile = metadata.get("power_profile")
            profile_bonus = 0.0
            if isinstance(profile, str):
                profile = profile.lower()
                if "green" in profile or "low" in profile:
                    profile_bonus = 0.1
                elif "legacy" in profile or "high" in profile:
                    profile_bonus = -0.1
            score = max(0.0, min(1.0, uptime_component - latency_penalty + profile_bonus))
            scores.append(score)
        if not scores:
            return 0.5
        return round(float(mean(scores)), 4)

    def _simulate_failure_impact(
        self,
        ranked: Sequence[str],
        capacities: Mapping[str, int] | None,
        risk_nodes: Iterable[str],
        history: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        capacity_map: Dict[str, int] = {}
        if isinstance(capacities, Mapping):
            for host in ranked:
                host_key = str(host)
                value = capacities.get(host_key)
                if value is None:
                    value = capacities.get(host) if host in capacities else None
                try:
                    capacity_map[host_key] = max(0, int(value))
                except Exception:
                    capacity_map[host_key] = 0
        if not capacity_map:
            capacity_map = {str(host): 1 for host in ranked}

        risk_set = {str(node) for node in risk_nodes}
        total_capacity = sum(capacity_map.values())
        lost_capacity = sum(capacity_map.get(node, 0) for node in risk_set)
        survivor_capacity = max(0, total_capacity - lost_capacity)
        loss_ratio = (
            round(lost_capacity / total_capacity, 4) if total_capacity else 0.0
        )

        trend = 0.0
        if history:
            last = history[-1]
            if isinstance(last, Mapping):
                previous = last.get("failure_projection")
                if isinstance(previous, Mapping):
                    prior_ratio = previous.get("loss_ratio")
                    if isinstance(prior_ratio, (int, float)):
                        trend = round(loss_ratio - float(prior_ratio), 4)

        return {
            "baseline": float(total_capacity),
            "lost_capacity": float(lost_capacity),
            "survivor_capacity": float(survivor_capacity),
            "loss_ratio": loss_ratio,
            "loss_ratio_trend": trend,
            "at_risk": sorted(risk_set),
        }

    def _recommend_burst_nodes(
        self,
        ranked: Sequence[str],
        statuses: Sequence[Mapping[str, Any]],
        health: Mapping[str, Mapping[str, Any]],
        backlog: int | None,
        summary: Mapping[str, Any] | None,
        capacities: Mapping[str, int] | None,
        risk_nodes: Iterable[str],
    ) -> List[str]:
        backlog = int(backlog or 0)
        if backlog <= max(1, len(ranked)):
            return []

        risk_set = {str(node) for node in risk_nodes}
        status_map = {str(entry.get("host")): entry for entry in statuses if entry.get("host")}
        slow_lookup = self._slow_ip_lookup(summary)

        capacity_map: Dict[str, int] = {}
        if isinstance(capacities, Mapping):
            for host in ranked:
                host_key = str(host)
                value = capacities.get(host_key)
                if value is None and host in capacities:
                    value = capacities[host]
                capacity_map[host_key] = max(0, int(value or 0))
        if not capacity_map:
            capacity_map = {str(host): 1 for host in ranked}

        candidates: List[tuple[str, int, float]] = []
        for host in ranked:
            host_key = str(host)
            if host_key in risk_set:
                continue
            info = health.get(host_key, {})
            if info.get("flapping") or info.get("state") == "offline":
                continue
            uptime = info.get("uptime_ratio")
            if isinstance(uptime, (int, float)) and uptime < 0.55:
                continue
            latency = info.get("average_latency_ms")
            if isinstance(latency, (int, float)) and latency > 650:
                continue
            last_latency = info.get("last_latency_ms")
            if isinstance(last_latency, (int, float)):
                tag = f"{host_key}:{int(last_latency)}"
                if tag in slow_lookup:
                    continue
            metadata = status_map.get(host_key, {}).get("metadata", {})
            priority_bonus = 0.0
            if isinstance(metadata, Mapping) and metadata.get("role") == "burst":
                priority_bonus = 0.25
            uptime_value = float(uptime) if isinstance(uptime, (int, float)) else 0.6
            score = capacity_map.get(host_key, 1) + uptime_value + priority_bonus
            candidates.append((host_key, capacity_map.get(host_key, 1), score))

        if not candidates:
            return []

        candidates.sort(key=lambda item: (item[1], item[2]), reverse=True)
        return [host for host, _capacity, _score in candidates[:3]]

    def _recommend_standby_nodes(
        self,
        ranked: Sequence[str],
        capacities: Mapping[str, int] | None,
        risk_nodes: Iterable[str],
        health: Mapping[str, Mapping[str, Any]],
    ) -> List[str]:
        capacity_map: Dict[str, int] = {}
        if isinstance(capacities, Mapping):
            for host in ranked:
                host_key = str(host)
                value = capacities.get(host_key)
                if value is None and host in capacities:
                    value = capacities[host]
                capacity_map[host_key] = max(0, int(value or 0))
        if not capacity_map:
            capacity_map = {str(host): 1 for host in ranked}

        risk_set = {str(node) for node in risk_nodes}
        standby: List[str] = []
        for host in ranked:
            host_key = str(host)
            if host_key in risk_set:
                continue
            allocation = capacity_map.get(host_key, 0)
            if allocation > 0:
                continue
            info = health.get(host_key, {})
            uptime = info.get("uptime_ratio")
            if isinstance(uptime, (int, float)) and uptime < 0.45:
                continue
            if info.get("flapping") or info.get("state") == "offline":
                continue
            standby.append(host_key)
        if standby:
            return standby[:5]

        ranked_pairs = [
            (str(host), capacity_map.get(str(host), 0))
            for host in ranked
            if str(host) not in risk_set
        ]
        ranked_pairs.sort(key=lambda item: item[1])
        return [host for host, _cap in ranked_pairs[:3]]

    def _slow_ip_lookup(self, summary: Mapping[str, Any] | None) -> set[str]:
        if not summary:
            return set()
        slow_entries = summary.get("slow_hosts")
        if not isinstance(slow_entries, list):
            return set()
        result = set()
        for entry in slow_entries[-self.history_limit :]:
            ip = entry.get("ip")
            latency = entry.get("latency_ms")
            if ip and isinstance(latency, (int, float)):
                result.add(f"{ip}:{int(latency)}")
        return result

    def _identify_risks(
        self,
        nodes: Sequence[str],
        health: Mapping[str, Mapping[str, Any]],
        summary: Mapping[str, Any] | None,
    ) -> Set[str]:
        risk: Set[str] = set()
        for host in nodes:
            info = health.get(str(host), {})
            failures = info.get("consecutive_failures")
            if isinstance(failures, (int, float)) and failures >= 3:
                risk.add(str(host))
                continue
            streak = info.get("latency_warning_streak")
            if isinstance(streak, (int, float)) and streak >= 4:
                risk.add(str(host))
                continue
            if info.get("flapping"):
                risk.add(str(host))
                continue
            if info.get("state") == "offline":
                risk.add(str(host))

        if summary and isinstance(summary.get("slow_hosts"), list):
            for entry in summary.get("slow_hosts", [])[-self.history_limit :]:
                host = entry.get("host") or entry.get("ip")
                if host:
                    risk.add(str(host))

        return risk

    def _forecast_capacity(
        self, history: Sequence[Mapping[str, Any]], capacities: Mapping[str, int]
    ) -> float:
        current_total = sum(capacities.values())
        if not history:
            return float(current_total)
        window = [
            float(entry.get("capacity_total"))
            for entry in history[-self.history_limit :]
            if isinstance(entry, Mapping) and isinstance(entry.get("capacity_total"), (int, float))
        ]
        if not window:
            return float(current_total)
        smoothed = 0.5 * current_total + 0.5 * mean(window)
        return round(smoothed, 3)

    def _region_allocations(
        self,
        nodes: Sequence[str],
        statuses: Sequence[Mapping[str, Any]],
        health: Mapping[str, Mapping[str, Any]],
    ) -> Dict[str, List[str]]:
        region_map: Dict[str, List[str]] = {}
        status_lookup: Dict[str, Mapping[str, Any]] = {
            str(entry.get("host")): entry for entry in statuses if entry.get("host")
        }

        for host in nodes:
            region = None
            status = status_lookup.get(str(host), {})
            if isinstance(status.get("metadata"), Mapping):
                region = status["metadata"].get("region")
            if not region:
                region = status.get("region")
            if not region:
                info = health.get(str(host), {})
                region = info.get("region")
            if not region:
                region = "unknown"
            region_map.setdefault(str(region), []).append(str(host))

        return region_map


__all__ = ["CloudOrchestrator"]

