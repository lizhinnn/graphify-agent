from typing import Any, Dict, List
import os
import json
from pathlib import Path
from .base import Tool
from graphify import extract, build, analyze
import networkx as nx


class GraphifyTool(Tool):
    def __init__(self):
        super().__init__(
            name="graphify",
            description="Ingest project and analyze code architecture using Graphify"
        )

    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        if action == "ingest_project":
            return self.ingest_project(**kwargs)
        elif action == "query_graph":
            return self.query_graph(**kwargs)
        elif action == "get_sample_graph":
            return self.get_sample_graph(**kwargs)
        else:
            return {"error": f"Unknown action: {action}"}

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'ingest_project' or 'query_graph'"
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to ingest (required for 'ingest_project')"
                },
                "graph_name": {
                    "type": "string",
                    "description": "Name of the graph to query (required for 'query_graph')"
                },
                "question": {
                    "type": "string",
                    "description": "Question about code architecture (required for 'query_graph')"
                }
            },
            "required": ["action"]
        }

    def ingest_project(self, directory: str) -> Dict[str, Any]:
        """Ingest project directory and build knowledge graph"""
        try:
            # Validate directory
            directory = Path(directory)
            if not directory.exists() or not directory.is_dir():
                return {"error": f"Directory does not exist: {directory}"}

            # Extract from all files
            extractions = []
            for ext in [".py", ".js", ".ts", ".tsx", ".java", ".c", ".cpp", ".cs", ".php", ".rb", ".kt", ".scala", ".lua", ".swift"]:
                for file_path in directory.rglob(f"*{ext}"):
                    # Get language config based on extension
                    config = self._get_language_config(ext)
                    if config:
                        extraction = extract._extract_generic(file_path, config)
                        if extraction and "nodes" in extraction:
                            extractions.append(extraction)

            if not extractions:
                return {"error": "No files found to extract"}

            # Build graph
            G = build.build(extractions, directed=True)

            # Create storage directory
            storage_dir = Path("storage/graphs")
            storage_dir.mkdir(parents=True, exist_ok=True)

            # Save graph
            graph_name = directory.name
            graph_path = storage_dir / f"{graph_name}.json"
            
            # Convert graph to JSON
            graph_data = {
                "nodes": [],
                "edges": []
            }
            for node_id, attrs in G.nodes(data=True):
                graph_data["nodes"].append({"id": node_id, **attrs})
            for u, v, attrs in G.edges(data=True):
                graph_data["edges"].append({"source": u, "target": v, **attrs})

            with open(graph_path, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)

            return {
                "status": "success",
                "message": f"Project ingested successfully",
                "graph_name": graph_name,
                "nodes_count": len(G.nodes()),
                "edges_count": len(G.edges()),
                "graph_path": str(graph_path)
            }
        except Exception as e:
            return {"error": f"Error ingesting project: {str(e)}"}

    def query_graph(self, graph_name: str, question: str) -> Dict[str, Any]:
        """Query graph for code architecture analysis"""
        try:
            # Load graph
            graph_path = Path("storage/graphs") / f"{graph_name}.json"
            if not graph_path.exists():
                return {"error": f"Graph not found: {graph_name}"}

            with open(graph_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)

            # Build graph
            G = build.build_from_json(graph_data, directed=True)

            # Analyze graph
            god_nodes_result = analyze.god_nodes(G, top_n=10)
            
            # Generate response
            response = {
                "status": "success",
                "graph_name": graph_name,
                "question": question,
                "analysis": {
                    "god_nodes": god_nodes_result,
                    "total_nodes": len(G.nodes()),
                    "total_edges": len(G.edges())
                }
            }

            # Add interactive HTML marker for complex data
            response["interactive_html"] = "[INTERACTIVE_HTML]storage/graphs/{graph_name}_visualization.html[/INTERACTIVE_HTML]".format(graph_name=graph_name)

            return response
        except Exception as e:
            return {"error": f"Error querying graph: {str(e)}"}

    def _get_language_config(self, ext: str) -> Any:
        """Get language config based on file extension"""
        config_map = {
            ".py": extract._PYTHON_CONFIG,
            ".js": extract._JS_CONFIG,
            ".ts": extract._TS_CONFIG,
            ".tsx": extract._TS_CONFIG,
            ".java": extract._JAVA_CONFIG,
            ".c": extract._C_CONFIG,
            ".cpp": extract._CPP_CONFIG,
            ".cs": extract._CSHARP_CONFIG,
            ".php": extract._PHP_CONFIG,
            ".rb": extract._RUBY_CONFIG,
            ".kt": extract._KOTLIN_CONFIG,
            ".scala": extract._SCALA_CONFIG,
            ".lua": extract._LUA_CONFIG,
            ".swift": extract._SWIFT_CONFIG
        }
        return config_map.get(ext)

    def get_sample_graph(self, **kwargs) -> Dict[str, Any]:
        """Get sample graph HTML from storage"""
        try:
            # Read sample graph HTML file
            graph_path = Path("storage/graphs/graph.html")
            if not graph_path.exists():
                return {"error": "未找到图谱文件，请先构建知识图谱"}

            # Read HTML content
            with open(graph_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Return formatted response
            return {
                "type": "graph_data",
                "content": f"[INTERACTIVE_HTML]{html_content}[/INTERACTIVE_HTML]"
            }
        except Exception as e:
            return {"error": f"获取图谱时出错: {str(e)}"}
