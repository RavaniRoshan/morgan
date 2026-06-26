"""Tests for the Router module."""

import pytest
from unittest.mock import MagicMock, patch
from morgan.config import Config
from morgan.router import Router, BudgetExceededError

@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.bind_tools.return_value = mock
    # Return an async mock for ainvoke
    async def async_ainvoke(*args, **kwargs):
        response_mock = MagicMock()
        response_mock.response_metadata = {"token_usage": {"total_tokens": 1000}}
        return response_mock
    mock.ainvoke = async_ainvoke
    return mock

def test_router_initializes_with_budget(workspace: Config) -> None:
    router = Router(config=workspace)
    assert router.total_tokens == 0
    assert router.total_cost == 0.0

import asyncio

@patch("morgan.router.os.environ.get")
@patch("langchain_classic.chat_models.init_chat_model")
def test_router_tracks_tokens(mock_init_chat_model, mock_env_get, mock_llm, workspace: Config) -> None:
    mock_env_get.return_value = None
    mock_init_chat_model.return_value = mock_llm
    
    router = Router(config=workspace)
    model = router.get_model("mock-model")
    
    # Simulate an invocation
    asyncio.run(model.ainvoke([{"role": "user", "content": "hi"}]))
    
    assert router.total_tokens == 1000
    assert router.total_cost > 0.0

@patch("morgan.router.os.environ.get")
@patch("langchain_classic.chat_models.init_chat_model")
def test_router_enforces_budget_cap(mock_init_chat_model, mock_env_get, mock_llm, workspace: Config) -> None:
    mock_env_get.return_value = None
    mock_init_chat_model.return_value = mock_llm
    
    workspace.budget_cap = 0.0001  # Very low budget
    router = Router(config=workspace)
    model = router.get_model("mock-model")
    
    # First invocation should exceed the tiny budget
    asyncio.run(model.ainvoke([{"role": "user", "content": "hi"}]))
    
    # Second invocation should raise BudgetExceededError
    with pytest.raises(BudgetExceededError):
        asyncio.run(model.ainvoke([{"role": "user", "content": "hi"}]))
