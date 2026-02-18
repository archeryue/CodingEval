"""Dataset plugins — auto-registers all built-in datasets on import."""

from codingeval.datasets.custom import CustomDataset
from codingeval.datasets.registry import register_dataset
from codingeval.datasets.swebench import SWEBenchDataset

register_dataset("swebench", lambda: SWEBenchDataset("swebench"))
register_dataset("swebench-lite", lambda: SWEBenchDataset("swebench-lite"))
register_dataset("swebench-verified", lambda: SWEBenchDataset("swebench-verified"))
register_dataset("custom", CustomDataset)
