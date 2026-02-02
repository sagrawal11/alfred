"""
Agent orchestrator (Option B): router mini → tools → voice 4o → summarizer mini.

This is the new \"Alfred brain\". It is intentionally designed to:
- Keep user-visible voice premium (gpt-4o)
- Keep internal steps cheap (gpt-4o-mini)
- Ground responses in Supabase via tool calls
- Write durable memory back to Supabase (summary + memory items + embeddings)
"""

from __future__ import annotations

import json
import os
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from openai import OpenAI
from supabase import Client

from data import UserMemoryEmbeddingsRepository, UserMemoryItemsRepository, UserMemoryStateRepository, UserRepository
from .tool_executor import ToolExecutor


def _first_name(full: str) -> str:
    t = (full or "").strip()
    if not t:
        return "there"
    return t.split()[0].strip() or "there"


def _split_sms_messages(text: str, max_parts: int = 3, max_chars: int = 1500) -> List[str]:
    """
    Split a model response into 1–3 SMS-sized parts.
    We prefer splitting on blank lines; fallback to hard chunking.
    """
    if not text:
        return []
    raw = text.strip()
    if len(raw) <= max_chars:
        return [raw]

    parts = [p.strip() for p in raw.split("\n\n") if p.strip()]
    if len(parts) > 1:
        out: List[str] = []
        buf = ""
        for p in parts:
            candidate = (buf + ("\n\n" if buf else "") + p).strip()
            if len(candidate) <= max_chars:
                buf = candidate
                continue
            if buf:
                out.append(buf[:max_chars])
                buf = p.strip()
            else:
                out.append(p[:max_chars])
                buf = ""
            if len(out) >= max_parts:
                return out[:max_parts]
        if buf and len(out) < max_parts:
            out.append(buf[:max_chars])
        return out[:max_parts]

    # Hard chunk fallback
    out = []
    s = raw
    while s and len(out) < max_parts:
        out.append(s[:max_chars].strip())
        s = s[max_chars:].strip()
    return out


@dataclass
class AgentConfig:
    enabled: bool
    model_voice: str
    model_router: str
    model_summarizer: str
    embedding_model: str
    max_tool_rounds: int = 2
    max_tool_calls_total: int = 8
    max_output_tokens_voice: int = 520  # ~1–3 SMS


class AgentOrchestrator:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.log = logging.getLogger("alfred.agent")
        self.user_repo = UserRepository(supabase)
        self.tools = ToolExecutor(supabase)
        self.memory_state_repo = UserMemoryStateRepository(supabase)
        self.memory_items_repo = UserMemoryItemsRepository(supabase)
        self.memory_embeddings_repo = UserMemoryEmbeddingsRepository(supabase)

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for agent mode")
        self.oa = OpenAI(api_key=api_key)

        self.cfg = AgentConfig(
            enabled=os.getenv("AGENT_MODE_ENABLED", "false").lower() == "true",
            model_voice=os.getenv("OPENAI_MODEL_VOICE", "gpt-4o"),
            model_router=os.getenv("OPENAI_MODEL_ROUTER", "gpt-4o-mini"),
            model_summarizer=os.getenv("OPENAI_MODEL_SUMMARIZER", os.getenv("OPENAI_MODEL_ROUTER", "gpt-4o-mini")),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )

        # In-memory recency window (for dev); durable summary handles long-term memory.
        self._recent_turns: Dict[int, List[Dict[str, str]]] = {}

    # ------------------------------------------------------------------
    # Tool schemas (OpenAI function tools)
    # ------------------------------------------------------------------
    def _tool_schemas(self) -> List[Dict[str, Any]]:
        # Keep tool list small and stable for accuracy.
        # Strict mode requires additionalProperties=false and all fields required.
        return [
            {
                "type": "function",
                "name": "get_user_profile",
                "description": "Get the user's profile basics (name, timezone, plan).",
                "strict": True,
                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            },
            {
                "type": "function",
                "name": "get_user_preferences",
                "description": "Get the user's preferences/settings (units, quiet hours, goals, etc.).",
                "strict": True,
                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            },
            {
                "type": "function",
                "name": "get_memory_summary",
                "description": "Get Alfred's running memory summary for the user (short).",
                "strict": True,
                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            },
            {
                "type": "function",
                "name": "search_memory",
                "description": "Search the user's memory items for relevant past info.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": ["integer", "null"]},
                    },
                    "required": ["query", "top_k"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_recent_activity",
                "description": "Fetch recent activity across logs (food/water/sleep/workouts/todos).",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "types": {"type": ["array", "null"], "items": {"type": "string"}},
                        "days": {"type": ["integer", "null"]},
                        "limit": {"type": ["integer", "null"]},
                    },
                    "required": ["types", "days", "limit"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_stats",
                "description": "Get simple totals for a metric across a timeframe in days.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric": {"type": "string"},
                        "timeframe_days": {"type": ["integer", "null"]},
                    },
                    "required": ["metric", "timeframe_days"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "log_water",
                "description": "Log a water intake event.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount_ml": {"type": "number"},
                        "source": {"type": ["string", "null"]},
                    },
                    "required": ["amount_ml", "source"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "log_food",
                "description": "Log one or more food items with macros.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "food_name": {"type": "string"},
                                    "calories": {"type": "number"},
                                    "protein": {"type": "number"},
                                    "carbs": {"type": "number"},
                                    "fat": {"type": "number"},
                                    "restaurant": {"type": ["string", "null"]},
                                    "portion_multiplier": {"type": ["number", "null"]},
                                },
                                "required": ["food_name", "calories", "protein", "carbs", "fat", "restaurant", "portion_multiplier"],
                                "additionalProperties": False,
                            },
                        },
                        "source": {"type": ["string", "null"]},
                        "metadata": {"type": ["object", "null"]},
                    },
                    "required": ["items", "source", "metadata"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "add_todo",
                "description": "Add a todo item. due_at is optional ISO8601.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "due_at": {"type": ["string", "null"]},
                    },
                    "required": ["text", "due_at"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "set_preference",
                "description": "Update a user preference (units, quiet hours, goals, etc.).",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {},
                    },
                    "required": ["key", "value"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "append_memory_item",
                "description": "Store a durable memory item about the user (fact/preference/plan/etc.).",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string"},
                        "content": {"type": "string"},
                        "importance": {"type": ["number", "null"]},
                        "source": {"type": ["string", "null"]},
                    },
                    "required": ["kind", "content", "importance", "source"],
                    "additionalProperties": False,
                },
            },
        ]

    # ------------------------------------------------------------------
    # Main entrypoint
    # ------------------------------------------------------------------
    def handle_message(self, *, user_id: int, phone_number: str, text: str, source: str = "sms") -> List[str]:
        """
        Returns 1–3 SMS message parts.
        """
        if not self.cfg.enabled:
            raise RuntimeError("Agent mode disabled (set AGENT_MODE_ENABLED=true)")

        user = self.user_repo.get_by_id(int(user_id)) or {}
        name = _first_name(user.get("name") or "")
        self.log.info("agent_turn start user_id=%s source=%s", user_id, source)

        # Ensure memory state exists
        mem_state = self.memory_state_repo.ensure(int(user_id))
        mem_summary = (mem_state.get("summary") or "").strip()

        # Update in-memory recency
        recent = self._recent_turns.setdefault(int(user_id), [])
        recent.append({"role": "user", "content": text})
        recent[:] = recent[-20:]

        # 1) Router mini: decide tools + call them
        tool_results = self._run_tool_loop(user_id=int(user_id), name=name, message=text, memory_summary=mem_summary)
        self.log.info("agent_turn tool_results user_id=%s tools=%s", user_id, list(tool_results.keys()))

        # 2) Voice 4o: produce final user-visible reply
        final_text = self._run_voice(
            user_id=int(user_id),
            name=name,
            message=text,
            memory_summary=mem_summary,
            tool_results=tool_results,
            recent_turns=recent,
        )

        parts = _split_sms_messages(final_text, max_parts=3, max_chars=1500)
        if not parts:
            parts = ["Sorry — I didn’t quite get that. Can you say it another way?"]

        # Record assistant output in recency
        recent.append({"role": "assistant", "content": "\n\n".join(parts)})
        recent[:] = recent[-20:]

        # 3) Summarizer mini: update durable memory
        self._update_memory(user_id=int(user_id), old_summary=mem_summary, user_msg=text, assistant_msg="\n\n".join(parts), tool_results=tool_results, source=source)
        self.log.info("agent_turn done user_id=%s parts=%s", user_id, len(parts))

        return parts

    # ------------------------------------------------------------------
    # Router tool loop
    # ------------------------------------------------------------------
    def _run_tool_loop(self, *, user_id: int, name: str, message: str, memory_summary: str) -> Dict[str, Any]:
        tools = self._tool_schemas()
        instructions = (
            "You are Alfred's routing layer. Decide which functions to call to answer the user's message.\n"
            "- Call functions only when needed.\n"
            "- Prefer minimal retrieval.\n"
            "- Do not write user-facing prose.\n"
        )
        input_list: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    f"User: {name}\n"
                    f"MemorySummary: {memory_summary or '(empty)'}\n"
                    f"Message: {message}\n"
                    "If the user asks about past logs, fetch only what you need."
                ),
            }
        ]

        results: Dict[str, Any] = {}
        tool_calls_total = 0

        for _round in range(self.cfg.max_tool_rounds):
            resp = self.oa.responses.create(
                model=self.cfg.model_router,
                instructions=instructions,
                tools=tools,
                input=input_list,
                max_tool_calls=max(0, self.cfg.max_tool_calls_total - tool_calls_total),
                parallel_tool_calls=True,
            )
            input_list += resp.output
            try:
                usage = getattr(resp, "usage", None)
                if usage:
                    self.log.debug("router_usage user_id=%s usage=%s", user_id, usage)
            except Exception:
                pass

            any_calls = False
            for item in resp.output:
                if getattr(item, "type", None) != "function_call":
                    continue
                any_calls = True
                tool_calls_total += 1
                try:
                    args = json.loads(getattr(item, "arguments", "") or "{}")
                except Exception:
                    args = {}

                r = self.tools.execute(user_id=user_id, tool_name=getattr(item, "name", ""), arguments=args)
                out_obj = {"ok": r.ok, "result": r.result, "error": r.error}

                # Save latest result per tool name (good enough for v1)
                if getattr(item, "name", None):
                    results[str(item.name)] = out_obj

                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": getattr(item, "call_id", ""),
                        "output": json.dumps(out_obj),
                    }
                )

                if tool_calls_total >= self.cfg.max_tool_calls_total:
                    break

            if not any_calls or tool_calls_total >= self.cfg.max_tool_calls_total:
                break

        return results

    # ------------------------------------------------------------------
    # Voice model
    # ------------------------------------------------------------------
    def _run_voice(
        self,
        *,
        user_id: int,
        name: str,
        message: str,
        memory_summary: str,
        tool_results: Dict[str, Any],
        recent_turns: List[Dict[str, str]],
    ) -> str:
        system = (
            "You are Alfred, a personal SMS assistant.\n"
            "- Sound like a normal person: warm, concise, not robotic.\n"
            "- Output 1–3 SMS-sized messages max.\n"
            "- Be grounded: use only the provided context and tool results.\n"
            "- If you need info you don't have, ask 1 clarifying question.\n"
            "- Do not mention internal tools.\n"
        )

        # Provide compact context to keep costs sane
        context_obj = {
            "user_first_name": name,
            "memory_summary": memory_summary,
            "tool_results": tool_results,
            "recent_turns": recent_turns[-10:],
        }

        prompt = (
            "Context (JSON):\n"
            f"{json.dumps(context_obj, ensure_ascii=False)}\n\n"
            f"User message: {message}\n\n"
            "Write your reply now."
        )

        resp = self.oa.responses.create(
            model=self.cfg.model_voice,
            instructions=system,
            input=prompt,
            max_output_tokens=self.cfg.max_output_tokens_voice,
        )
        try:
            usage = getattr(resp, "usage", None)
            if usage:
                self.log.debug("voice_usage user_id=%s usage=%s", user_id, usage)
        except Exception:
            pass
        return getattr(resp, "output_text", "") or ""

    # ------------------------------------------------------------------
    # Durable memory update (summary + embeddings)
    # ------------------------------------------------------------------
    def _update_memory(
        self,
        *,
        user_id: int,
        old_summary: str,
        user_msg: str,
        assistant_msg: str,
        tool_results: Dict[str, Any],
        source: str,
    ) -> None:
        instructions = (
            "You update Alfred's durable memory.\n"
            "Return ONLY valid JSON with this exact shape:\n"
            "{\n"
            '  \"summary\": \"string (<= 1200 chars)\",\n'
            '  \"memory_items\": [\n'
            "    {\n"
            '      \"kind\": \"fact|preference|plan|relationship|note\",\n'
            '      \"content\": \"string (<= 400 chars)\",\n'
            '      \"importance\": number (0 to 1)\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "- Only include memory_items if the user clearly stated a stable preference/fact/plan.\n"
            "- Max 3 memory_items.\n"
        )

        payload = {
            "old_summary": old_summary,
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "tool_results": tool_results,
        }

        resp = self.oa.responses.create(
            model=self.cfg.model_summarizer,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=False),
            max_output_tokens=420,
        )
        text = (getattr(resp, "output_text", "") or "").strip()
        try:
            usage = getattr(resp, "usage", None)
            if usage:
                self.log.debug("summarizer_usage user_id=%s usage=%s", user_id, usage)
        except Exception:
            pass

        summary = old_summary
        memory_items: List[Dict[str, Any]] = []
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                summary = str(obj.get("summary") or "").strip()[:1200]
                mi = obj.get("memory_items") or []
                if isinstance(mi, list):
                    memory_items = [x for x in mi if isinstance(x, dict)][:3]
        except Exception:
            # If parsing fails, fall back to keeping old summary.
            return

        # Persist summary
        try:
            self.memory_state_repo.ensure(user_id)
            self.memory_state_repo.update(
                user_id,
                {
                    "summary": summary,
                    "summary_updated_at": datetime.now().isoformat(),
                },
            )
        except Exception:
            pass

        # Persist memory items + embeddings
        for item in memory_items:
            try:
                kind = str(item.get("kind") or "note").strip()[:40]
                content = str(item.get("content") or "").strip()[:400]
                if not content:
                    continue
                importance = float(item.get("importance") or 0.5)
                if importance < 0:
                    importance = 0.0
                if importance > 1:
                    importance = 1.0

                row = self.memory_items_repo.create_item(
                    user_id=user_id,
                    kind=kind,
                    content=content,
                    source=source,
                    importance=importance,
                )
                memory_item_id = int(row.get("id"))

                emb = self.oa.embeddings.create(model=self.cfg.embedding_model, input=content)
                vec = emb.data[0].embedding  # type: ignore[index]
                self.memory_embeddings_repo.upsert_embedding(memory_item_id, vec, self.cfg.embedding_model)
            except Exception:
                continue

