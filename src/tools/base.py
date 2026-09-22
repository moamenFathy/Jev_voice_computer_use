"""
Base Tool Interface and Tool Registry for JEV (Phase 2 Architecture).
Encapsulates individual OS, Web, App, and System capabilities into testable,
modular tool components with unified execution, observation, and verification interfaces.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.core.observation import Observation
from src.verification.verifier import Verifier


class BaseTool(ABC):
    """
    Abstract base class for all JEV OS and Agent tools.
    Every tool defines its execution, observation extraction, default verifier,
    and whether the action is idempotent (safe to repeat on retry).
    """

    name: str = "base_tool"
    description: str = "Base tool description"
    is_idempotent: bool = True

    @abstractmethod
    def execute(self, target: str, **kwargs) -> ToolResult:
        """Executes the tool action against the target parameter."""
        pass

    def observe(self, target: str, **kwargs) -> Observation:
        """Captures observation of system/app state after tool execution."""
        return Observation(source="system", description=f"Executed {self.name} on '{target}'")

    def get_verifier(self) -> Optional[Verifier]:
        """Returns the domain verifier associated with this tool, or None."""
        return None

    def reobserve(self) -> None:
        """Optional hook called before retries to refresh UI or state caches."""
        pass


class ToolRegistry:
    """
    Central registry for discovering, registering, and invoking JEV tools.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> BaseTool:
        """Registers a tool instance into the registry."""
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieves a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, BaseTool]:
        """Returns a copy of all registered tools."""
        return dict(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __getitem__(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry.")
        return self._tools[name]


# Global tool registry singleton
tool_registry = ToolRegistry()
