"""Base interface for all tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    context: str = ""
    sources: list[str] = field(default_factory=list)
    data: dict | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class ToolDefinition:
    name: str
    description: str


class BaseTool(ABC):
    definition: ToolDefinition

    @abstractmethod
    def execute(self, user_id: str, **kwargs) -> ToolResult:
        ...
