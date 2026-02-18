"""Reporter plugins — auto-registers all built-in reporters on import."""

from codingeval.reporters.console import ConsoleReporter
from codingeval.reporters.json_reporter import JSONReporter
from codingeval.reporters.registry import register_reporter

register_reporter("console", ConsoleReporter)
register_reporter("json", JSONReporter)
