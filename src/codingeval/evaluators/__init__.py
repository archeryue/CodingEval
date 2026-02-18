"""Evaluator plugins — auto-registers all built-in evaluators on import."""

from codingeval.evaluators.registry import register_evaluator
from codingeval.evaluators.swebench import SWEBenchEvaluator

register_evaluator("swebench", SWEBenchEvaluator)
