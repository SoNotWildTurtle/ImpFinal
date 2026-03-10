from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[1]


def _load_utils() -> Any:
    import sys

    spec = importlib.util.spec_from_file_location(
        "imp.core.imp_utils", ROOT / "core" / "imp_utils.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


utils = _load_utils()
CONFIG_PATH = ROOT / "config" / "imp-control-policies.json"
LOG_PATH = ROOT / "logs" / "imp-control-hub.json"
QUEUE_PATH = ROOT / "logs" / "imp-control-queue.json"
HISTORY_PATH = ROOT / "logs" / "imp-control-history.json"
DEFAULT_CONFIG: Dict[str, Any] = {
    "policies": [],
    "intent_keywords": [],
    "intents": {},
    "capabilities": [],
    "agents": [],
}

log_manager = utils.load_module("imp_log_manager", ROOT / "logs" / "imp-log-manager.py")
log_manager.ensure_logs()


def _ensure_log(path: Path) -> None:
    if not path.exists():
        utils.write_json(path, [])


@dataclass
class PolicyMatch:
    name: str
    require: List[str] = field(default_factory=list)
    deny_if: Optional[float] = None
    transforms: List[str] = field(default_factory=list)
    matched: bool = False


class ControlHub:
    """General-intelligence control coordination hub."""

    def __init__(
        self,
        config_path: Path = CONFIG_PATH,
        log_path: Path = LOG_PATH,
        queue_path: Path = QUEUE_PATH,
        history_path: Path = HISTORY_PATH,
    ) -> None:
        self.config_path = config_path
        self.log_path = log_path
        self.queue_path = queue_path
        self.history_path = history_path
        self.config = utils.read_json(config_path, DEFAULT_CONFIG)
        self.capabilities: Dict[str, Dict[str, Any]] = {
            entry["name"]: entry for entry in self.config.get("capabilities", [])
        }
        self.intent_templates: Dict[str, Dict[str, Any]] = self.config.get("intents", {})
        self.intent_keywords: List[Dict[str, Any]] = self.config.get("intent_keywords", [])
        self.policies: List[Dict[str, Any]] = self.config.get("policies", [])
        self.agents: Dict[str, Dict[str, Any]] = {
            entry["name"]: entry for entry in self.config.get("agents", [])
        }
        _ensure_log(self.log_path)
        _ensure_log(self.queue_path)
        _ensure_log(self.history_path)

    # ------------------------------------------------------------------
    # Capability management
    # ------------------------------------------------------------------
    def register_capability(self, name: str, description: str, scope: str) -> None:
        self.capabilities[name] = {"name": name, "description": description, "scope": scope}
        capabilities = list(self.capabilities.values())
        self.config["capabilities"] = capabilities
        utils.write_json(self.config_path, self.config)
        self._record_event("register_capability", {"name": name, "scope": scope})

    def list_capabilities(self) -> List[Dict[str, Any]]:
        return sorted(self.capabilities.values(), key=lambda entry: entry["name"])

    def capability_details(self, name: str) -> Optional[Dict[str, Any]]:
        capability = self.capabilities.get(name)
        if not capability:
            return None
        agents = [
            agent
            for agent in self.list_agents()
            if name in agent.get("capabilities", [])
        ]
        details = dict(capability)
        details["agents"] = agents
        return details

    # ------------------------------------------------------------------
    # Agent mesh helpers
    # ------------------------------------------------------------------
    def register_agent(
        self,
        name: str,
        scope: str,
        endpoint: str,
        capabilities: Optional[Iterable[str]] = None,
        notes: str = "",
    ) -> None:
        self.agents[name] = {
            "name": name,
            "scope": scope,
            "endpoint": endpoint,
            "capabilities": sorted(set(capabilities or [])),
            "notes": notes,
        }
        self.config["agents"] = list(self.agents.values())
        utils.write_json(self.config_path, self.config)
        self._record_event(
            "register_agent",
            {
                "name": name,
                "scope": scope,
                "capabilities": self.agents[name]["capabilities"],
            },
        )

    def list_agents(self) -> List[Dict[str, Any]]:
        return sorted(self.agents.values(), key=lambda entry: entry["name"])

    # ------------------------------------------------------------------
    # Intent parsing and planning
    # ------------------------------------------------------------------
    def parse_intent(self, goal_text: str) -> Dict[str, Any]:
        lowered = goal_text.lower()
        best_intent = "general.review"
        confidence = 0.2
        for mapping in self.intent_keywords:
            keywords = mapping.get("keywords", [])
            if all(keyword in lowered for keyword in keywords):
                best_intent = mapping.get("intent", best_intent)
                confidence = max(confidence, 0.6 + 0.1 * len(keywords))
                break
        return {"intent": best_intent, "confidence": round(confidence, 2)}

    def build_plan(
        self,
        goal_text: str,
        targets: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        intent_info = self.parse_intent(goal_text)
        intent = intent_info["intent"]
        template = self.intent_templates.get(intent, {})
        steps = list(template.get("steps", ["analyze_goal", "execute_plan", "report_results"]))
        selected_targets = list(targets) if targets else list(template.get("default_targets", []))
        policy = self.evaluate_policy(intent, metadata or {})
        plan = {
            "goal": goal_text,
            "intent": intent,
            "confidence": intent_info["confidence"],
            "description": template.get("description", "Adaptive plan"),
            "targets": selected_targets,
            "steps": self._apply_transforms(steps, policy.transforms),
            "policy": {
                "requirements": policy.require,
                "denied": policy.matched and policy.deny_if is not None and metadata and metadata.get("risk_score", 0) > policy.deny_if,
                "transforms": policy.transforms,
            },
            "timestamp": time.time(),
        }
        self._record_event("plan_built", plan)
        return plan

    # ------------------------------------------------------------------
    # Plan queue management
    # ------------------------------------------------------------------
    def submit_plan(
        self,
        plan: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        queue = utils.read_json(self.queue_path, [])
        plan_id = f"plan-{int(time.time() * 1000)}"
        entry = {
            "id": plan_id,
            "status": "pending",
            "plan": plan,
            "metadata": metadata or {},
            "submitted_at": time.time(),
        }
        queue.append(entry)
        queue = queue[-100:]
        utils.write_json(self.queue_path, queue)
        self._record_event("plan_submitted", {"id": plan_id, "intent": plan["intent"]})
        self._append_history(
            {
                "id": plan_id,
                "intent": plan["intent"],
                "status": "pending",
                "targets": plan.get("targets", []),
                "submitted_at": entry["submitted_at"],
                "metadata": entry["metadata"],
            }
        )
        return entry

    def list_plans(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        queue = utils.read_json(self.queue_path, [])
        if status and status != "all":
            queue = [entry for entry in queue if entry["status"] == status]
        return queue

    def approve_plan(self, plan_id: str) -> bool:
        queue = utils.read_json(self.queue_path, [])
        updated = False
        for entry in queue:
            if entry["id"] == plan_id:
                entry["status"] = "approved"
                entry["approved_at"] = time.time()
                updated = True
                break
        if updated:
            utils.write_json(self.queue_path, queue)
            self._record_event("plan_approved", {"id": plan_id})
            approved_at = next((entry.get("approved_at") for entry in queue if entry["id"] == plan_id), time.time())
            self._update_history(plan_id, {"status": "approved", "approved_at": approved_at})
        return updated

    # ------------------------------------------------------------------
    # Policy evaluation
    # ------------------------------------------------------------------
    def evaluate_policy(self, intent: str, metadata: Dict[str, Any]) -> PolicyMatch:
        policy_result = PolicyMatch(name="default")
        risk = metadata.get("risk_score", 0.0)
        for entry in self.policies:
            pattern = entry.get("match", "*")
            if fnmatch.fnmatch(intent, pattern):
                policy_result = PolicyMatch(
                    name=entry.get("name", pattern),
                    require=list(entry.get("require", [])),
                    deny_if=entry.get("deny_if", {}).get("risk_score") if isinstance(entry.get("deny_if"), dict) else entry.get("deny_if"),
                    transforms=list(entry.get("transforms", [])),
                    matched=True,
                )
                if policy_result.deny_if is not None and risk > policy_result.deny_if:
                    policy_result.require.append("manual_override")
                break
        return policy_result

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def latest_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        entries = utils.read_json(self.log_path, [])
        return entries[-limit:]

    def list_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        history = utils.read_json(self.history_path, [])
        if limit is None:
            return history
        return history[-limit:]

    def _apply_transforms(self, steps: List[str], transforms: List[str]) -> List[str]:
        transformed = list(steps)
        for transform in transforms:
            if transform == "preflight_health_check" and "preflight_health_check" not in transformed:
                transformed.insert(0, "preflight_health_check")
            elif transform == "append_summary" and "deliver_summary" not in transformed:
                transformed.append("deliver_summary")
        return transformed

    def pause_all(self, reason: str = "") -> None:
        self._record_event("pause_all", {"reason": reason})

    def audit_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.latest_events(limit)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        entries = utils.read_json(self.log_path, [])
        entries.append({
            "event": event_type,
            "timestamp": time.time(),
            "payload": payload,
        })
        entries = entries[-200:]
        utils.write_json(self.log_path, entries)

    def _append_history(self, record: Dict[str, Any]) -> None:
        history = utils.read_json(self.history_path, [])
        history.append(record)
        history = history[-200:]
        utils.write_json(self.history_path, history)

    def _update_history(self, plan_id: str, updates: Dict[str, Any]) -> None:
        history = utils.read_json(self.history_path, [])
        changed = False
        for entry in reversed(history):
            if entry.get("id") == plan_id:
                entry.update(updates)
                changed = True
                break
        if changed:
            utils.write_json(self.history_path, history)


def _cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="IMP Control Hub")
    parser.add_argument("--goal", help="Natural language goal to analyse")
    parser.add_argument("--targets", nargs="*", help="Optional explicit targets")
    parser.add_argument("--list-capabilities", action="store_true", help="List registered capabilities")
    parser.add_argument("--capability-details", help="Show a detailed view for a capability")
    parser.add_argument("--list-agents", action="store_true", help="List registered agents")
    parser.add_argument("--register-agent", help="Register a new agent by name")
    parser.add_argument("--agent-scope", default="general", help="Scope for the agent when registering")
    parser.add_argument("--agent-endpoint", help="Endpoint or connector identifier for a new agent")
    parser.add_argument(
        "--agent-capabilities",
        nargs="*",
        default=[],
        help="Capabilities handled by the new agent",
    )
    parser.add_argument("--agent-notes", default="", help="Optional notes for a new agent")
    parser.add_argument("--show-log", action="store_true", help="Display recent control hub events")
    parser.add_argument("--status", nargs="?", const="all", help="Show plan queue optionally filtered by status")
    parser.add_argument("--submit", action="store_true", help="Submit the generated plan to the queue")
    parser.add_argument("--approve", help="Approve a queued plan by id")
    parser.add_argument("--pause-all", action="store_true", help="Record a pause-all request")
    parser.add_argument("--pause-reason", default="", help="Reason to log when pausing all orchestration")
    parser.add_argument("--audit", action="store_true", help="Display recent audit events")
    parser.add_argument(
        "--history",
        type=int,
        nargs="?",
        const=10,
        help="Display the most recent plan history entries (default 10)",
    )
    parser.add_argument("--force-risk", type=float, default=0.0, help="Risk score to evaluate against policies")
    args = parser.parse_args(argv)

    hub = ControlHub()

    if args.register_agent:
        if not args.agent_endpoint:
            parser.error("--agent-endpoint is required when registering an agent")
        hub.register_agent(
            args.register_agent,
            args.agent_scope,
            args.agent_endpoint,
            capabilities=args.agent_capabilities,
            notes=args.agent_notes,
        )
        print(f"Registered agent {args.register_agent} with scope '{args.agent_scope}'.")
        return 0

    if args.list_capabilities:
        for capability in hub.list_capabilities():
            print(f"{capability['name']}: {capability['description']} ({capability['scope']})")
        return 0

    if args.capability_details:
        details = hub.capability_details(args.capability_details)
        if not details:
            print(f"Capability '{args.capability_details}' not found.")
            return 1
        print(f"Name: {details['name']}")
        print(f"Description: {details.get('description', '')}")
        print(f"Scope: {details.get('scope', 'general')}")
        if details.get("agents"):
            print("Agents:")
            for agent in details["agents"]:
                caps = ", ".join(agent.get("capabilities", [])) or "(none)"
                print(
                    f"  - {agent['name']} [{agent['scope']}] -> {agent['endpoint']} (capabilities: {caps})"
                )
        else:
            print("Agents: none registered")
        return 0

    if args.list_agents:
        for agent in hub.list_agents():
            caps = ", ".join(agent.get("capabilities", [])) or "(none)"
            print(f"{agent['name']} -> {agent['endpoint']} [{agent['scope']}]; capabilities: {caps}")
        return 0

    if args.show_log:
        for entry in hub.latest_events():
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["timestamp"]))
            print(f"[{ts}] {entry['event']}: {entry['payload']}")
        return 0

    if args.status is not None:
        status_filter = None if args.status in (None, "all") else args.status
        for entry in hub.list_plans(status=status_filter):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("submitted_at", 0)))
            print(f"{entry['id']} [{entry['status']}] {entry['plan']['intent']} targets={entry['plan']['targets']} submitted={ts}")
        return 0

    if args.approve:
        if hub.approve_plan(args.approve):
            print(f"Plan {args.approve} approved.")
        else:
            print(f"Plan {args.approve} not found.")
        return 0

    if args.pause_all:
        hub.pause_all(args.pause_reason)
        print("Pause-all request recorded.")
        return 0

    if args.audit:
        for entry in hub.audit_events():
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["timestamp"]))
            print(f"[{ts}] {entry['event']}: {entry['payload']}")
        return 0

    if args.history is not None:
        for entry in hub.list_history(limit=args.history):
            submitted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("submitted_at", 0)))
            approved = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("approved_at", 0)))
                if entry.get("approved_at")
                else "-"
            )
            print(
                f"{entry['id']} [{entry['status']}] intent={entry['intent']} targets={entry.get('targets', [])} "
                f"submitted={submitted} approved={approved}"
            )
        return 0

    if args.goal:
        plan = hub.build_plan(args.goal, targets=args.targets, metadata={"risk_score": args.force_risk})
        print("Intent:", plan["intent"], f"(confidence={plan['confidence']})")
        if plan["targets"]:
            print("Targets:", ", ".join(plan["targets"]))
        print("Steps:")
        for idx, step in enumerate(plan["steps"], 1):
            print(f"  {idx}. {step}")
        requirements = plan["policy"]["requirements"]
        if requirements:
            print("Requirements:", ", ".join(requirements))
        if plan["policy"]["denied"]:
            print("Policy decision: denied (risk too high)")
        if args.submit:
            submission = hub.submit_plan(plan, metadata={"risk_score": args.force_risk})
            print(f"Plan queued with id {submission['id']} and status {submission['status']}.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover - manual use
    raise SystemExit(_cli())
