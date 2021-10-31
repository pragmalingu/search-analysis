from search_analysis.tools.comparison import ComparisonTool
import pytest

from search_analysis.tools.elasticsearch.evaluation_object_mock import EvaluationObjectMock


def test_create_comparison_tool():
    es_object1 = EvaluationObjectMock()
    es_object2 = EvaluationObjectMock()

    ct = ComparisonTool("localhost", {}, es_object1, es_object2)
