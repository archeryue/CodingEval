"""Dataset plugins — auto-registers all built-in datasets on import."""

from codingeval.datasets.custom import CustomDataset
from codingeval.datasets.registry import register_dataset
from codingeval.datasets.swebench import SWEBenchDataset
from codingeval.regression.dataset import RegressionDataset

register_dataset("swebench", lambda: SWEBenchDataset("swebench"))
register_dataset("swebench-lite", lambda: SWEBenchDataset("swebench-lite"))
register_dataset("swebench-verified", lambda: SWEBenchDataset("swebench-verified"))
register_dataset("custom", CustomDataset)
register_dataset("regression", RegressionDataset)
