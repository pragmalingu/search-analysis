from abc import ABC, abstractmethod


class ComparisonToolBase(ABC):
    @abstractmethod
    def calculate_difference(self, condition='fscore', dumps=False):
        pass

    @abstractmethod
    def get_disjoint_sets(self, distribution, highest=False):
        pass

    @abstractmethod
    def get_specific_comparison(self, query_id, doc_id, fields=['text', 'title']):
        pass

    @abstractmethod
    def visualize_distributions(self, queries=None, eval_objs=None,
                                distributions=['true_positives', 'false_positives', 'false_negatives'], download=False,
                                path_to_file='./save_vis_distributions.svg'):
        pass

    @abstractmethod
    def visualize_condition(self, queries=None, eval_objs=None, conditions=['precision', 'recall', 'fscore'],
                            download=False, path_to_file='./save_vis_condition.svg'):
        pass

    @abstractmethod
    def visualize_explanation(self, query_id, doc_id, fields=['text', 'title'], eval_objs=None, download=False,
                              path_to_file='./save_vis_explaination.svg'):
        pass

    @abstractmethod
    def visualize_explanation_csv(self, query_id, doc_id, path_to_save_to, fields=['text', 'title'],
                                  decimal_separator=',', eval_objs=None):
        pass


class EvaluationObject(ABC):
    @abstractmethod
    def get_true_positives(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        pass

    @abstractmethod
    def get_false_positives(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        pass

    @abstractmethod
    def get_false_negatives(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        pass

    @abstractmethod
    def get_recall(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        pass

    @abstractmethod
    def get_precision(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        pass

    @abstractmethod
    def get_fscore(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False, factor=1):
        pass

    @abstractmethod
    def count_distribution(self, distribution, distribution_json, dumps=False, k=20):
        pass

    @abstractmethod
    def explain_query(self, query_id, doc_id, fields=['text', 'title'], dumps=True):
        pass
