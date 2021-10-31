from search_analysis.tools import EvaluationObject


class EvaluationObjectMock(EvaluationObject):
    def __init__(self):
        return

    def get_true_positives(self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False):
        pass

    def get_false_positives(self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False):
        pass

    def get_false_negatives(self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False):
        pass

    def get_recall(self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False):
        pass

    def get_precision(self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False):
        pass

    def get_fscore(
        self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False,
        factor=1,):
        pass

    def count_distribution(self, distribution, distribution_json, dumps=False, k=20):
        pass

    def explain_query(self, query_id, doc_id, fields=["text", "title"], dumps=True):
        pass
