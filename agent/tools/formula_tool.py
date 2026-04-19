from typing import Any, Dict
from .base import Tool


class InteractiveSceneTool(Tool):
    def __init__(self):
        super().__init__(
            name="generate_interactive_scene",
            description="Trigger interactive laboratory mode for concept visualization with interactive elements"
        )

    def execute(self, concept: str, requirements: str) -> Dict[str, Any]:
        return {
            "type": "interactive_request",
            "concept": concept,
            "requirements": requirements
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "The concept name to visualize in interactive mode"
                },
                "requirements": {
                    "type": "string",
                    "description": "Description of interactive requirements (e.g., 'slider to control phase of sin function')"
                }
            },
            "required": ["concept", "requirements"]
        }