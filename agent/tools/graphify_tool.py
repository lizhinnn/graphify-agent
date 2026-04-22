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
            highlight_ids = kwargs.pop("highlight_ids", None)
            return self.get_sample_graph(highlight_ids=highlight_ids, **kwargs)
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

    def get_sample_graph(self, highlight_ids: list = None, **kwargs) -> Dict[str, Any]:
        """Get sample graph data from storage"""
        try:
            # 优先从 graph.json 文件读取数据
            graph_json_path = Path("storage/graphs/graph.json")
            if graph_json_path.exists():
                with open(graph_json_path, "r", encoding="utf-8") as f:
                    graph_data = json.load(f)
                
                # 处理高亮节点ID，实现模糊匹配逻辑
                actual_highlight_ids = []
                if highlight_ids:
                    # 构建 label 到 id 的映射
                    label_to_id = {}
                    if "nodes" in graph_data:
                        for node in graph_data["nodes"]:
                            if "label" in node and "id" in node:
                                label_to_id[node["label"].lower()] = node["id"]
                    
                    # 处理每个高亮节点
                    for item in highlight_ids:
                        item_lower = item.lower()
                        # 直接匹配 id
                        if item in [node["id"] for node in graph_data.get("nodes", [])]:
                            actual_highlight_ids.append(item)
                        # 模糊匹配 label
                        else:
                            for label, node_id in label_to_id.items():
                                if item_lower in label:
                                    actual_highlight_ids.append(node_id)
                                    break
                else:
                    actual_highlight_ids = []
                
                # 提取 nodes 和 links 数据
                nodes = graph_data.get("nodes", [])
                # 处理 edges 或 links
                links = graph_data.get("edges", [])
                if not links:
                    links = graph_data.get("links", [])
                
                # 为 nodes 添加 group 属性（如果不存在）
                for i, node in enumerate(nodes):
                    if "group" not in node:
                        node["group"] = (i % 3) + 1
                
                # Return formatted response with raw data
                return {
                    "type": "graph_data",
                    "nodes": nodes,
                    "links": links,
                    "highlight_ids": actual_highlight_ids
                }
            else:
                # 如果没有 graph.json 文件，尝试从 HTML 文件中提取数据
                graph_path = Path("storage/graphs/graph.html")
                if not graph_path.exists():
                    return {"error": "未找到图谱文件，请先构建知识图谱"}
                
                # 读取 HTML 内容
                with open(graph_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                
                # 尝试从 HTML 中提取 nodes 和 links 数据
                import re
                nodes_match = re.search(r'const nodes = \[(.*?)\];', html_content, re.DOTALL)
                links_match = re.search(r'const links = \[(.*?)\];', html_content, re.DOTALL)
                
                if nodes_match and links_match:
                    try:
                        nodes_str = f"[{nodes_match.group(1)}]"
                        links_str = f"[{links_match.group(1)}]"
                        nodes = json.loads(nodes_str)
                        links = json.loads(links_str)
                        
                        # 为 nodes 添加 group 属性（如果不存在）
                        for i, node in enumerate(nodes):
                            if "group" not in node:
                                node["group"] = (i % 3) + 1
                        
                        # 处理高亮节点ID
                        actual_highlight_ids = highlight_ids or []
                        
                        # Return formatted response with extracted data
                        return {
                            "type": "graph_data",
                            "nodes": nodes,
                            "links": links,
                            "highlight_ids": actual_highlight_ids
                        }
                    except json.JSONDecodeError:
                        return {"error": "无法解析图谱数据，请确保图谱文件格式正确"}
                else:
                    return {"error": "无法从图谱文件中提取数据，请确保图谱文件格式正确"}
        except Exception as e:
            return {"error": f"获取图谱时出错: {str(e)}"}
