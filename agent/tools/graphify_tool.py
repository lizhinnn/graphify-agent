from typing import Any, Dict, List
from .base import Tool
from graphify import extract, analyze, ingest


class ExtractEntitiesTool(Tool):
    def __init__(self):
        super().__init__(
            name="extract_entities",
            description="Extract entities from the given text document"
        )

    def execute(self, text: str) -> Dict[str, Any]:
        return extract.extract_entities(text)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text document to extract entities from"}
            },
            "required": ["text"]
        }


class ExtractRelationshipsTool(Tool):
    def __init__(self):
        super().__init__(
            name="extract_relationships",
            description="Extract relationships between entities from the given text document"
        )

    def execute(self, text: str) -> Dict[str, Any]:
        return extract.extract_relationships(text)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text document to extract relationships from"}
            },
            "required": ["text"]
        }


class AnalyzeGraphTool(Tool):
    def __init__(self):
        super().__init__(
            name="analyze_graph",
            description="Analyze the knowledge graph structure"
        )

    def execute(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        return analyze.analyze_graph(graph)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "graph": {"type": "object", "description": "The knowledge graph to analyze"}
            },
            "required": ["graph"]
        }


class IngestDocumentTool(Tool):
    def __init__(self):
        super().__init__(
            name="ingest_document",
            description="Ingest a document into the knowledge graph system"
        )

    def execute(self, document: str) -> Dict[str, Any]:
        return ingest.ingest_document(document)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "The document to ingest"}
            },
            "required": ["document"]
        }
