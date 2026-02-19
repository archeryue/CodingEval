"""Evaluator plugins — auto-registers all built-in evaluators on import."""

from codingeval.evaluators.registry import register_evaluator
from codingeval.evaluators.swebench import SWEBenchEvaluator
from codingeval.regression.evaluator import RegressionEvaluator

register_evaluator("swebench", SWEBenchEvaluator)
register_evaluator("regression", RegressionEvaluator)
