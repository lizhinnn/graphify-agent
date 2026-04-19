from typing import List, Dict, Any
from agent.tools import TOOLS


class ToolsAdapter:
    def __init__(self):
        self.tools = TOOLS

    def get_tools(self) -> List[Dict[str, Any]]:
        return [tool.get_schema() for tool in self.tools]

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.execute(**kwargs)
        raise ValueError(f"Tool '{tool_name}' not found")
