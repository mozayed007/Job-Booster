"""LangChain + LangGraph AI layer for Job_Booster.

This package mirrors the Pydantic AI agent layer using LangChain chat models
and LangGraph stateful workflows. It exists so the two stacks can be compared
side-by-side without touching the existing Pydantic AI code paths.
"""

from app.langchain_layer.agents import (
    LangChainAgent,
    LCCoverLetterAgent,
    LCCvExtractorAgent,
    LCJobFinderAgent,
    LCResumeReviewerAgent,
    LCResumeTailorAgent,
)
from app.langchain_layer.factory import build_llm, get_model_name
from app.langchain_layer.graph import LangGraphPipeline, build_pipeline_graph, run_pipeline
from app.langchain_layer.state import LCGraphState
from app.langchain_layer.tools import get_lc_tools, get_lc_tools_for_agent

__all__ = [
    "LangChainAgent",
    "LCCvExtractorAgent",
    "LCResumeReviewerAgent",
    "LCResumeTailorAgent",
    "LCCoverLetterAgent",
    "LCJobFinderAgent",
    "LCGraphState",
    "build_llm",
    "get_model_name",
    "build_pipeline_graph",
    "LangGraphPipeline",
    "run_pipeline",
    "get_lc_tools",
    "get_lc_tools_for_agent",
]
