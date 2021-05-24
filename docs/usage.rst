=====
Usage
=====

To use Search Analysis in a project::

 from search_analysis import EvaluationObject, ComparisonTool


# Evaluation Object


The Evaluation Object is a tool to get some analysis data out of one approach.

.. autofunction:: search_analysis.__init__.EvaluationObject



## Functions to use with the Evaluation Object


.. autofunction:: search_analysis.__init__.EvaluationObject.get_true_positives
.. autofunction:: search_analysis.__init__.EvaluationObject.get_false_positives
.. autofunction:: search_analysis.__init__.EvaluationObject.get_false_negatives
.. autofunction:: search_analysis.__init__.EvaluationObject.get_recall
.. autofunction:: search_analysis.__init__.EvaluationObject.get_precision
.. autofunction:: search_analysis.__init__.EvaluationObject.get_fscore
.. autofunction:: search_analysis.__init__.EvaluationObject.count_distribution
.. autofunction:: search_analysis.__init__.EvaluationObject.explain_query

# Comparison Tool


"""The Evaluation Object is a tool to get some analysis data out of one approach."""

.. autofunction:: search_analysis.__init__.ComparisonTool



## Functions to use with the Comparison Tool


.. autofunction:: search_analysis.__init__.EvaluationObject.calculate_difference
.. autofunction:: search_analysis.__init__.EvaluationObject.get_disjoint_sets
.. autofunction:: search_analysis.__init__.EvaluationObject.visualize_distributions
.. autofunction:: search_analysis.__init__.EvaluationObject.visualize_condition
.. autofunction:: search_analysis.__init__.EvaluationObject.visualize_explanation_csv




