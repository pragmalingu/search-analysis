import pytest
from elasticmock import elasticmock

from search_analysis import ESEvaluationObject


@elasticmock
def test_create_comparison_tool():
    es_object = ESEvaluationObject("localhost", {}, "test-index", "name")
    es_object.get_true_positives()
