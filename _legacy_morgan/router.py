"""Morgan router module — multi-provider model routing + budget tracking."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel


import logging
from typing import Any
import os
from morgan.config import Config, audit_log

logger = logging.getLogger("morgan.router")

class BudgetExceededError(Exception):
    """Raised when an API call would exceed the configured budget."""

class Router:
    """Selects the appropriate model based on task complexity and budget."""
    
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.total_tokens = 0
        self.total_cost = 0.0
        self.budget_cap = getattr(self.config, 'budget_cap', 10.0)

    def get_model(self, model_name: str | None = None, tools: list | None = None) -> Any:
        """Return a chat model instance, bound with tools and wrapped with tracking."""
        llm = None
        m_name = model_name or os.environ.get("MORGAN_MODEL")
        
        if not m_name:
            # Auto-detect logic
            provider_models = [
                ("ANTHROPIC_API_KEY", "claude-sonnet-4-20250514"),
                ("OPENAI_API_KEY", "gpt-4o-mini"),
                ("GOOGLE_API_KEY", "gemini-2.0-flash"),
                ("NVIDIA_API_KEY", "nvidia:meta/llama-3.1-70b-instruct"),
            ]
            for env_var, default_model in provider_models:
                if os.environ.get(env_var):
                    m_name = default_model
                    break
                    
        if not m_name:
            return None
            
        try:
            if m_name.startswith("nvidia:") or (os.environ.get("NVIDIA_API_KEY") and "llama" in m_name.lower()):
                from langchain_nvidia_ai_endpoints import ChatNVIDIA
                real_model = m_name.replace("nvidia:", "") if "nvidia:" in m_name else m_name
                llm = ChatNVIDIA(model=real_model)
            else:
                from langchain_classic.chat_models import init_chat_model
                llm = init_chat_model(m_name)
        except Exception as e:
            logger.error("Failed to initialize model %s: %s", m_name, e)
            return None

        if tools:
            # NVIDIA Llama 3.1 needs parallel_tool_calls=False
            llm = llm.bind_tools(tools, parallel_tool_calls=False)
            
        return self._wrap_with_tracking(llm, m_name)
        
    def _wrap_with_tracking(self, llm: Any, model_name: str) -> Any:
        class TrackedLLM:
            def __init__(self, inner, router, m_name):
                self.inner = inner
                self.router = router
                self.model_name = m_name
                
            async def ainvoke(self, messages: list) -> Any:
                if self.router.total_cost >= self.router.budget_cap:
                    raise BudgetExceededError(f"Budget cap of ${self.router.budget_cap} exceeded.")
                    
                response = await self.inner.ainvoke(messages)
                
                usage = getattr(response, "response_metadata", {}).get("token_usage", {})
                if usage:
                    total_tokens = usage.get("total_tokens", 0)
                    self.router.total_tokens += total_tokens
                    # Approximate cost calculation
                    estimated_cost = (total_tokens / 1000) * 0.001
                    self.router.total_cost += estimated_cost
                    audit_log("router_usage", {
                        "model": self.model_name,
                        "tokens": total_tokens, 
                        "cumulative_cost": self.router.total_cost
                    })
                    
                return response

        return TrackedLLM(llm, self, model_name)
