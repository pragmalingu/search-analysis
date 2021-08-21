from abc import ABC
from abc import abstractmethod

from search_analysis.tools.base import *


def test_base_comparison_tool():
    return issubclass(ComparisonToolBase, ABC)


def test_base_evaluation_object():
    return issubclass(EvaluationObject, ABC)
