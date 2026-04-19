from typing import Any, Dict, List
import numpy as np
from .base import Tool


class FormulaTool(Tool):
    def __init__(self):
        super().__init__(
            name="generate_formula_plot",
            description="Generate interactive plot data for mathematical functions using Plotly.js format"
        )

    def execute(self, formula: str, x_range: List[float] = [-10, 10], points: int = 100) -> Dict[str, Any]:
        # 强制限制数据点数量为 30，防止大字符串传输导致浏览器内存卡顿
        points = 30
        """
        Generate plot data for a mathematical formula

        Args:
            formula: Mathematical formula as string (e.g., "sin(x),cos(x)")
            x_range: List of [min, max] for x-axis
            points: Number of data points to generate

        Returns:
            Plotly.js compatible JSON data structure
        """
        formulas = [f.strip() for f in formula.split(',')]

        x = np.linspace(x_range[0], x_range[1], points)

        data = []
        for i, f in enumerate(formulas):
            try:
                namespace = {'x': x, 'np': np}
                namespace.update({
                    'sin': np.sin,
                    'cos': np.cos,
                    'tan': np.tan,
                    'exp': np.exp,
                    'log': np.log,
                    'sqrt': np.sqrt,
                    'abs': np.abs
                })

                y = eval(f, namespace)

                data.append({
                    "x": x.tolist(),
                    "y": y.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": f
                })
            except Exception as e:
                data.append({
                    "x": [],
                    "y": [],
                    "type": "scatter",
                    "mode": "markers",
                    "name": f"Error: {str(e)}"
                })

        layout = {
            "title": "Interactive Plot",
            "xaxis": {
                "title": "x",
                "rangemode": "tozero",
                "showgrid": True
            },
            "yaxis": {
                "title": "y",
                "rangemode": "tozero",
                "showgrid": True
            },
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1
            },
            "margin": {
                "l": 40,
                "r": 40,
                "t": 40,
                "b": 40
            }
        }

        return {
            "data": data,
            "layout": layout,
            "config": {
                "responsive": True,
                "displayModeBar": True,
                "scrollZoom": True
            },
            "type": "plot"
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "formula": {
                    "type": "string",
                    "description": "Mathematical formula(s) to plot, separated by commas (e.g., 'sin(x),cos(x)')"
                },
                "x_range": {
                    "type": "array",
                    "items": {
                        "type": "number"
                    },
                    "description": "X-axis range as [min, max]"
                },
                "points": {
                    "type": "integer",
                    "description": "Number of data points to generate"
                }
            },
            "required": ["formula"]
        }