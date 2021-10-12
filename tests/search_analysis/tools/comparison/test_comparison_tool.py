from search_analysis.tools.comparison import ComparisonTool
import pytest
from elasticmock import elasticmock

from search_analysis import ESEvaluationObject


@elasticmock
def test_create_comparison_tool():
    es_object1 = ESEvaluationObject("localhost", {}, "test-index", "name")
    es_object2 = ESEvaluationObject("localhost", {}, "test-index", "name")

    ct = ComparisonTool("localhost", {}, es_object1, es_object2)
