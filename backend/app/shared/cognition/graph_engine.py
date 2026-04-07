from __future__ import annotations

import json
import os

from brain.memory_engine import get_memory
from modules.task_module import get_task_data


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NEXTGEN_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "nextgen_features.json")


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _tokenize(text: str) -> set[str]:
    tokens = set()
    for raw in _compact_text(text).lower().split():
        cleaned = "".join(char for char in raw if char.isalnum())
        if len(cleaned) >= 3:
            tokens.add(cleaned)
    return tokens


def _safe_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def _contact_nodes(limit: int = 8) -> list[dict]:
    synced = get_memory("personal.synced_google_contacts") or []
    contacts = []
    seen = set()
    if isinstance(synced, list):
        for item in synced:
            if not isinstance(item, dict):
                continue
            name = _compact_text(item.get("display_name") or item.get("name"))
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            contacts.append({"id": f"contact:{name.lower()}", "type": "contact", "label": name})
            if len(contacts) >= limit:
                break
    emergency = _compact_text(get_memory("personal.contact.emergency_contact.name"))
    if emergency and emergency.lower() not in seen:
        contacts.append({"id": f"contact:{emergency.lower()}", "type": "contact", "label": emergency})
    return contacts[:limit]


def build_knowledge_graph(limit: int = 120) -> dict:
    task_data = get_task_data()
    tasks = list(task_data.get("tasks") or [])
    reminders = list(task_data.get("reminders") or [])
    nextgen = _safe_json(NEXTGEN_PATH, {})
    goals = list(nextgen.get("goals") or [])
    habits = list(nextgen.get("habits") or [])
    contacts = _contact_nodes()

    nodes = []
    edges = []
    seen_nodes = set()

    def add_node(node_id: str, node_type: str, label: str, meta: dict | None = None):
        clean_id = _compact_text(node_id)
        if not clean_id or clean_id in seen_nodes:
            return
        seen_nodes.add(clean_id)
        nodes.append({"id": clean_id, "type": node_type, "label": _compact_text(label) or node_type, "meta": meta or {}})

    def add_edge(source: str, target: str, relation: str):
        if not source or not target or source == target:
            return
        edges.append({"source": source, "target": target, "relation": relation})

    add_node("user:self", "user", "You")
    for contact in contacts:
        add_node(contact["id"], contact["type"], contact["label"])
        add_edge("user:self", contact["id"], "knows")

    for habit in habits[:12]:
        name = _compact_text(habit.get("name") or habit.get("title"))
        if not name:
            continue
        habit_id = f"habit:{name.lower()}"
        add_node(habit_id, "habit", name, {"last_done": habit.get("last_done", "")})
        add_edge("user:self", habit_id, "tracks")

    for goal in goals[:16]:
        title = _compact_text(goal.get("title"))
        if not title:
            continue
        goal_id = f"goal:{title.lower()}"
        add_node(goal_id, "goal", title)
        add_edge("user:self", goal_id, "pursues")
        for milestone in goal.get("milestones") or []:
            milestone_title = _compact_text(milestone.get("title"))
            if not milestone_title:
                continue
            milestone_id = f"milestone:{title.lower()}:{milestone_title.lower()}"
            add_node(milestone_id, "milestone", milestone_title, {"done": bool(milestone.get("done"))})
            add_edge(goal_id, milestone_id, "has_milestone")

    for task in tasks[:20]:
        title = _compact_text(task.get("title"))
        if not title:
            continue
        task_id = f"task:{title.lower()}"
        add_node(task_id, "task", title, {"completed": bool(task.get("completed"))})
        add_edge("user:self", task_id, "needs")
        task_tokens = _tokenize(title)
        for goal in goals[:16]:
            goal_title = _compact_text(goal.get("title"))
            if not goal_title:
                continue
            goal_tokens = _tokenize(goal_title)
            if task_tokens & goal_tokens:
                add_edge(task_id, f"goal:{goal_title.lower()}", "supports")
        for contact in contacts:
            if contact["label"].lower() in title.lower():
                add_edge(task_id, contact["id"], "relates_to")

    for reminder in reminders[:20]:
        title = _compact_text(reminder.get("title"))
        if not title:
            continue
        reminder_id = f"reminder:{title.lower()}"
        add_node(reminder_id, "reminder", title, {"due_at": reminder.get("due_at") or reminder.get("due_date") or ""})
        add_edge("user:self", reminder_id, "scheduled")
        for contact in contacts:
            if contact["label"].lower() in title.lower():
                add_edge(reminder_id, contact["id"], "relates_to")

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes[: max(1, limit)],
        "edges": edges[: max(1, limit * 2)],
        "summary": f"Knowledge graph built with {len(nodes)} nodes and {len(edges)} relationships.",
    }


def knowledge_graph_context(query: str, limit: int = 3) -> list[str]:
    graph = build_knowledge_graph(limit=120)
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    related = []
    for node in graph.get("nodes", []):
        label = _compact_text(node.get("label"))
        overlap = len(query_tokens & _tokenize(label))
        if overlap <= 0:
            continue
        related_edges = [
            edge for edge in graph.get("edges", [])
            if edge.get("source") == node.get("id") or edge.get("target") == node.get("id")
        ][:2]
        if related_edges:
            fragments = []
            for edge in related_edges:
                counterpart = edge.get("target") if edge.get("source") == node.get("id") else edge.get("source")
                fragments.append(f"{edge.get('relation')} {counterpart}")
            related.append(f"{label}: {' | '.join(fragments)}")
        else:
            related.append(label)
        if len(related) >= max(1, limit):
            break
    return related
