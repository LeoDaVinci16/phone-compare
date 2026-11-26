"""phone-compare: compare phones spec by spec against a base phone, with CSV, plots and a report."""

from .compare import Comparison, compare, goodness
from .data import Dataset, load_dataset
from .validate import find_issues

__version__ = "1.0.0"
__all__ = ["Comparison", "Dataset", "compare", "find_issues", "goodness", "load_dataset"]
