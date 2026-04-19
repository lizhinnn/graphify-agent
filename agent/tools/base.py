from abc import ABC, abstractmethod
from typing import Any, Dict, List


class Tool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        pass

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters()
        }

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        pass
