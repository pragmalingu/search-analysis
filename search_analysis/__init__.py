"""Top-level package for Search Analysis."""

__author__ = """PragmaLingu"""
__email__ = 'info@pragmalingu.de'
__version__ = '0.1.9'

import csv
from collections import OrderedDict, defaultdict
import warnings
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from elasticsearch import Elasticsearch
import json
import re


class EvaluationObject:
    def __init__(self, host, query_rel_dict, index, name):
        self.queries_rels = query_rel_dict
        self.index = index
        self.name = name
        self.elasticsearch = Elasticsearch([host], ca_certs=False, verify_certs=False, read_timeout=120)
        self.elasticsearch.ping()
        self.true_positives = {}
        self.false_positives = {}
        self.false_negatives = {}
        self.recall = {}
        self.precision = {}
        self.fscore = {}
        # orange, green, turquoise, black, red, yellow, white
        self.pragma_colors = ['#ffb900', '#8cab13', '#22ab82', '#242526', '#cc0000', '#ffcc00', '#ffffff']

    def _check_size(self, k, size):
        """
        checking `size` argument; size needs to be >= k;
        :param k: ranking size
        :param size: search size, if size is None, it will set Elastisearch default value
        :return: adjusted search size
        """
        if size is not None:
            if size < k:
                size = k
        return size

    def _get_search_result(self, query_id, size, fields):
        """
        Sends a search request for every query to Elasticsearch and returns the result including highlighting
        :param query_id: int, current query id
        :param fields: list of fields that should be searched on
        :param size: int, search size
        :return: returns search result from Elasticsearch
        """
        body = self._get_highlights_search_body(self.queries_rels[query_id]['question'], size, fields)
        result = self.elasticsearch.search(index=self.index, body=body)
        return result

    def _get_highlights_search_body(self, query, size=20, fields=["text", "title"]):
        """
        :param query: str, query to search on
        :param size: int, searched size
        :param fields: list of str, fields, that should be searched
        :return: highlighting for the matched results
        """
        return {
            "size": size,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": fields
                }
            },
            "highlight": {
                "fields": {
                    "*": {}
                }
            }
        }

    def _check_searched_queries(self, query_ids):
        """
        Checks if query_ids is an int or None and transforms it to a list.
        If it's None, all available queries are used for the search.
        :param query_ids: can be a list, an int or None
        :return: transformed query ids
        """
        # in case of integer query_IDs argument; transform into list;
        if type(query_ids) == int:
            query_ids = [query_ids]
        if query_ids is None:
            query_ids = [*self.queries_rels]
        return query_ids

    def _create_hit(self, pos, hit, fields):
        """
        Creates an overview of the hit from Elasticsearch
        :param pos: ranking position
        :type hit: hit found in Elasticsearch
        :param fields: fields so analyze
        """
        doc_fields = {}
        highlights = {}
        for curr_field in fields:
            try:
                doc_fields[curr_field] = hit["_source"][curr_field]
                if curr_field in hit["highlight"].keys():
                    highlights[curr_field] = hit["highlight"][curr_field]
            except KeyError:
                continue

        variable = {
            "position": pos,
            "score": hit["_score"],
            "doc": {"id": int(hit["_id"])},
            "highlight": {}
        }
        for field_name, highlight in highlights.items():
            variable["highlight"][field_name] = highlight
        for field, data in doc_fields.items():
            variable["doc"][field] = data
        return variable

    def _initialize_distributions(self, searched_queries=None, fields=['text', 'title'], size=20, k=20):
        """
        Gets values for self.true_positives, self.false_positives and self.false_negatives
                Calculates false positives from given search queries
        :param searched_queries: int or list of int of query ids or None; if None it searches with all queries
        :param fields: list of str, fields that should be searched on
        :param size: int, search size
        :param k: int, k top results that should be returned from Elasticsearch
        """
        size = self._check_size(k, size)
        searched_queries = self._check_searched_queries(searched_queries)
        self.true_positives = self.get_true_positives(searched_queries, fields, size, k, False)
        self.false_positives = self.get_false_positives(searched_queries, fields, size, k, False)
        self.false_negatives = self.get_false_negatives(searched_queries, fields, size, k, False)

    def _calculate_recall(self, tp, fn):
        """
        Calculates Recall
        :param tp: int, true positives
        :param fn: int, false negatives
        :return: Recall value
        """
        if (tp + fn) == 0:
            warnings.warn('Sum of true positives and false negatives is 0. Please check your data, '
                          'this shouldn\'t happen. Maybe you tried searching on the wrong index, with the wrong '
                          'queries or on the wrong fields.')
            return 0
        return tp / (tp + fn)

    def _calculate_precision(self, tp, fp):
        """
        Calculates Precision
        :param tp: int, true positives
        :param fn: int, false negatives
        :return: Precision value
        """
        if (tp + fp) == 0:
            warnings.warn('Sum of true positives and false positives is 0. Please check your data, '
                          'this shouldn\'t happen. Maybe you tried searching on the wrong index, with the wrong '
                          'queries or on the wrong fields.')
            return 0
        return tp / (tp + fp)

    def _calculate_fscore(self, precision, recall, factor=1):
        """
        Calculates F-score
        :param precision: int, precision value
        :param recall: int, recall value
        :param factor: int, 1 is the default to calculate F1-Score
        :return: F-score value
        """
        if recall or precision != 0:
            if factor is 1:
                return (2 * precision * recall) / (precision + recall)
            else:
                return (1 + factor ** 2) * ((precision * recall) / (factor ** 2 * precision + recall))
        else:
            warnings.warn('The value of precision and/or recall is 0.')
            return 0

    def get_true_positives(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        """
        Calculates true positives from given search queries
        :param searched_queries: int or list of int of query ids or None; if None it searches with all queries
        :param fields: list of str, fields that should be searched on
        :param size: int, search size
        :param k: int, k top results that should be returned from Elasticsearch
        :param dumps: True or False, if True it returns json.dumps, if False it returns json
        :return: true positives as json
        """
        size = self._check_size(k, size)
        searched_queries = self._check_searched_queries(searched_queries)
        # initializing dictionary of true positives;
        true_pos = {}
        for query_ID in searched_queries:
            true_pos["Query_" + str(query_ID)] = {
                "question": self.queries_rels[query_ID]['question'],
                "true_positives": []
            }
            result = self._get_search_result(query_ID, size, fields)
            for pos, hit in enumerate(result["hits"]["hits"], start=1):
                # check if `hit` IS a relevant document; in case `hits` position < k, it counts as a true positive;
                if int(hit["_id"]) in self.queries_rels[query_ID]['relevance_assessments'] and pos <= k:
                    true = self._create_hit(pos, hit, fields)
                    true_pos["Query_" + str(query_ID)]["true_positives"].append(true)
        if dumps:
            return json.dumps(true_pos, indent=4)
        else:
            return true_pos

    def get_false_positives(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        """
        Calculates false positives from given search queries
        :param searched_queries: int or list of int of query ids or None; if None it searches with all queries
        :param fields: list of str, fields that should be searched on
        :param size: int, search size
        :param k: int, k top results that should be returned from Elasticsearch
        :param dumps: True or False, if True it returns json.dumps, if False it returns json
        :return: false positives as json
        """
        size = self._check_size(k, size)
        searched_queries = self._check_searched_queries(searched_queries)
        # initializing dictionary of false positives;
        false_pos = {}
        for query_ID in searched_queries:
            false_pos["Query_" + str(query_ID)] = {
                "question": self.queries_rels[query_ID]['question'],
                "false_positives": []
            }
            result = self._get_search_result(query_ID, size, fields)
            # for every `hit` in the search results... ;
            for pos, hit in enumerate(result["hits"]["hits"], start=1):
                # check if `hit` IS a relevant document; in case `hits` position < k, it counts as a true positive;
                if int(hit["_id"]) not in self.queries_rels[query_ID]['relevance_assessments'] and pos < k:
                    false = self._create_hit(pos, hit, fields)
                    false_pos["Query_" + str(query_ID)]["false_positives"].append(false)
        if dumps:
            return json.dumps(false_pos, indent=4)
        else:
            return false_pos

    def get_false_negatives(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        """
        Calculates false negatives from given search queries
        :param searched_queries: int or list of int of query ids or None; if None it searches with all queries
        :param fields: list of str, fields that should be searched on
        :param size: int, search size
        :param k: int, k top results that should be returned from Elasticsearch
        :param dumps: True or False, if True it returns json.dumps, if False it returns json
        :return: false negatives as json
        """
        size = self._check_size(k, size)
        searched_queries = self._check_searched_queries(searched_queries)
        # initializing dictionary of false negatives;
        false_neg = {}
        for query_ID in searched_queries:
            false_neg["Query_" + str(query_ID)] = {
                "question": self.queries_rels[query_ID]['question'],
                "false_negatives": []
            }
            result = self._get_search_result(query_ID, size, fields)
            # iterating through the results;
            query_rel = self.queries_rels[query_ID]['relevance_assessments'].copy()
            for pos, hit in enumerate(result["hits"]["hits"], start=1):
                # false negatives require that the result belongs to the relevance assessments;
                if int(hit["_id"]) in query_rel:
                    if pos > k:
                        # create a `false negative`;
                        false = self._create_hit(pos, hit, fields)
                        # save `false hit/positive`;
                        false_neg["Query_" + str(query_ID)]["false_negatives"].insert(0, false)
                        # removes the `hit` from the remaining relevant documents;
                    query_rel.remove(int(hit["_id"]))
            # adds all missing relevant docs to the start of the `false negatives` with `position = -1`;
            for relevant_doc in query_rel:
                # create a `false negative`;
                false = {
                    "position": -1,
                    "score": None,
                    "doc": {
                        "id": relevant_doc
                    }
                }
                false_neg["Query_" + str(query_ID)]["false_negatives"].insert(0, false)
        if dumps:
            return json.dumps(false_neg, indent=4)
        else:
            return false_neg

    def get_recall(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        """
        Calculates recall for every search query given
        :param searched_queries: int or list of int of query ids or None; if None it searches with all queries
        :param fields: list of str, fields that should be searched on
        :param size: int, search size
        :param k: int, k top results that should be returned from Elasticsearch
        :param dumps: True or False, if True it returns json.dumps, if False saves to object variable
        :return: json with Recall values
        """
        if not self.true_positives:
            self._initialize_distributions(searched_queries, fields, size, k)
        true_pos = self.count_distribution('true_positives', self.true_positives, False, k)
        false_neg = self.count_distribution('false_negatives', self.false_negatives, False, k)
        recall = defaultdict(dict)
        recall_sum = 0.0
        for query, data in true_pos.items():
            if not query == 'total':
                recall_value = self._calculate_recall(true_pos[query]['count'], false_neg[query]['count'])
                recall[query]['recall'] = recall_value
                recall_sum += recall_value
        recall = OrderedDict(sorted(recall.items(), key=lambda i: i[1]['recall']))
        recall['total'] = (recall_sum / len(self.queries_rels))
        if dumps:
            return json.dumps(recall, indent=4)
        else:
            self.recall = recall

    def get_precision(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False):
        """
        Calculates Precision for every given query
        :param searched_queries: int or list of int of query ids or None; if None it searches with all queries
        :param fields: list of str, fields that should be searched on
        :param size: int, search size
        :param k: int, k top results that should be returned from Elasticsearch
        :param dumps: True or False, if True it returns json.dumps, if False saves to object variable
        :return: json with Precision values
        """
        if not self.true_positives:
            self._initialize_distributions(searched_queries, fields, size, k)
        true_pos = self.count_distribution('true_positives', self.true_positives, False, k)
        false_pos = self.count_distribution('false_positives', self.false_positives, False, k)
        precision = defaultdict(dict)
        precision_sum = 0.0
        for query, data in true_pos.items():
            if not query == 'total':
                precision_value = self._calculate_precision(true_pos[query]['count'], false_pos[query]['count'])
                precision[query]['precision'] = precision_value
                precision_sum += precision_value
        precision = OrderedDict(sorted(precision.items(), key=lambda i: i[1]['precision']))
        precision['total'] = (precision_sum / len(self.queries_rels))
        if dumps:
            return json.dumps(precision, indent=4)
        else:
            self.precision = precision

    def get_fscore(self, searched_queries=None, fields=['text', 'title'], size=20, k=20, dumps=False, factor=1):
        """
        :param searched_queries: int or list of int of query ids or None; if None it searches with all queries
        :param fields: list of str, fields that should be searched on
        :param size: int, search size
        :param k: int, k top results that should be returned from Elasticsearch
        :param factor: int, can be used to weight the F score, default is 1
        :param dumps: True or False, if True it returns json.dumps, if False saves to object variable
        :return: F-Score value
        """
        if not self.recall:
            self.get_recall(searched_queries, fields, size, k, False)
        if not self.precision:
            self.get_precision(searched_queries, fields, size, k, False)
        fscore = defaultdict(dict)
        for query, data in self.precision.items():
            if not query == 'total':
                fscore_value = self._calculate_fscore(self.precision[query]['precision'], self.recall[query]['recall'],
                                                       factor)
                fscore[query]['fscore'] = fscore_value
        fscore = OrderedDict(sorted(fscore.items(), key=lambda i: i[1]['fscore']))
        fscore['total'] = self._calculate_fscore(self.precision['total'], self.recall['total'], factor)
        if dumps:
            return json.dumps(fscore, indent=4)
        else:
            self.fscore = fscore

    def count_distribution(self, distribution, distribution_json, dumps=False, k=20):
        """
        :param dumps: True or False, if True it returns json.dumps, if False it returns json
        :param distribution: string, 'true_positives', 'false_positives' or 'false_negatives'
        :param distribution_json: json or json as str with all the distributions needed
        :param k: int, size of k top search results
        :return: counted distribution per query, as a sum and as a percentage
        """
        if isinstance(distribution_json, str):
            result_json = json.loads(distribution_json)
        else:
            result_json = distribution_json
        counts = defaultdict(dict)
        sum_rels = 0
        sum_count = 0
        for query in result_json:
            query_id = int(query.strip('Query_'))
            count_query = int(len(result_json[query][distribution]))
            count_rels = int(len(self.queries_rels[query_id]['relevance_assessments']))
            if distribution == 'false_positives':
                f = k - count_query
                if f == count_rels or count_rels == 0:
                    percentage = 0
                else:
                    percentage = (count_rels - f) * 100 / count_rels
            else:
                if count_rels == 0:
                    percentage = 0
                else:
                    percentage = (100 * count_query / count_rels)
            counts[query] = {'count': count_query, 'percentage': percentage, 'relevant documents': count_rels}
            sum_rels += count_rels
            sum_count += count_query
        if distribution == 'false_positives':
            f = (k * len(counts)) - sum_count
            if f == sum_rels or sum_rels == 0:
                sum_percentage = 0
            else:
                sum_percentage = (sum_rels - f) * 100 / sum_rels
        else:
            if sum_rels == 0:
                sum_percentage = 0
            else:
                sum_percentage = (100 * sum_count / sum_rels)
        sorted_counts = OrderedDict(sorted(counts.items(), key=lambda i: i[1]['percentage']))
        sorted_counts['total'] = {'total sum': sum_count, 'percentage': str(sum_percentage) + '%'}
        if dumps:
            return json.dumps(sorted_counts, indent=4)
        else:
            return sorted_counts

    def explain_query(self, query_id, doc_id, fields=['text', 'title'], dumps=True):
        """
        Returns an Elasticsearch explanation for given query
        :param query_id: int, query that should be explained
        :param doc_id: int, id of document that should be explained
        :param fields: list of str, fields that should be searched on
        :param dumps: True by default, if False it won't convert dict to json
        :return: json
        """
        query_body = {
            "query": {
                "multi_match": {
                    "fields": fields,
                    "query": self.queries_rels[query_id]['question']
                }
            }
        }
        explain = defaultdict(lambda: defaultdict(lambda: []))
        explanation = self.elasticsearch.explain(self.index, doc_id, query_body)['explanation']
        explain["score"] = explanation['value']
        if explain["score"] == 0.0:
            print('No hits with that request, please check all the parameters like index, fields, query dictionary, '
                  'etc.')
            return explanation
        if explanation['description'] != "max of:":
            explanation = {'details': [explanation]}

        for el in explanation['details']:
            field = ''.join(f for f in fields if re.search(f, el['details'][0]['description']))
            explain[field]["total_value"] = el['details'][0]['value']
            explain[field]["details"] = []
            for detail in el['details']:
                doc_freq = 0
                term_freq = 0.0
                for val in detail['details'][0]["details"]:
                    try:
                        if re.match('n, number of documents', val["details"][0]["description"]):
                            doc_freq = val["details"][0]["value"]
                    except IndexError:
                        continue
                    try:
                        if re.match(r'.*[Ff]req', val["details"][0]["description"]):
                            term_freq = val["details"][0]["value"]
                    except IndexError:
                        continue
                explain[field]["details"].append(
                    {"function": {
                        "value": detail['value'],
                        "description": detail['description'],
                        "n, number of documents containing term": doc_freq,
                        "freq, occurrences of term within document": term_freq}})
        if dumps:
            return json.dumps(explain, indent=4)
        else:
            return explain


class ComparisonTool:
    def __init__(self, host, qry_rel_dict, eval_obj_1=None, eval_obj_2=None,
                 fields=['text', 'title'], index_1=None, index_2=None, name_1='approach_1',
                 name_2='approach_2', size=20, k=20):
        if eval_obj_1 is None:
            eval_obj_1 = EvaluationObject(host, qry_rel_dict, index_1, name_1)
        if eval_obj_2 is None:
            eval_obj_1 = EvaluationObject(host, qry_rel_dict, index_2, name_2)
        self.eval_obj_1 = eval_obj_1
        self.eval_obj_2 = eval_obj_2
        self.eval_obj_1.get_fscore(None, fields, size, k)
        self.eval_obj_2.get_fscore(None, fields, size, k)
        # orange, green, turquoise, black, red, yellow, white
        self.pragma_colors = ['#ffb900', '#8cab13', '#22ab82', '#242526', '#cc0000', '#ffcc00', '#ffffff']
        self.recall_diffs = {}
        self.precision_diffs = {}
        self.fscore_diffs = {}

    def _get_conditions(self, queries, eval_objs, conditions):
        """
        Gets condition values for the vizualisation as a pandas data frame.
        :param queries: int or list of ints of query ids
        :param eval_objs: list of EvaluationObj
        :param conditions: list of conditions that should be printed
        :return: pandas data frame
        """
        vis_dict = defaultdict(list)
        for obj in eval_objs:
            for con in conditions:
                for query in queries:
                    vis_dict['Approach'].append(obj.name)
                    vis_dict['Value'].append(getattr(obj, con)['Query_' + str(query)][con])
                    vis_dict['Scores'].append(con)
        return pd.DataFrame(data=vis_dict)

    def _get_distributions(self, queries, eval_objs, distributions):
        """
        Gets distributions values for the vizualisation as a pandas data frame.
        :param queries: int or list of ints of query ids
        :param eval_objs: list of EvaluationObj
        :param distributions: list of distributions that should be printed
        :return: pandas data frame
        """
        dis_dict = defaultdict(list)
        for obj in eval_objs:
            for dist in distributions:
                for query in queries:
                    for el in getattr(obj, dist)['Query_' + str(query)][dist]:
                        dis_dict['Approach'].append(obj.name)
                        dis_dict['Distributions'].append(dist)
        return pd.DataFrame(data=dis_dict)

    def _get_explain_terms(self, query_id, doc_id, fields, eval_objs):
        """
        Returns pandas data frame containing all the found terms and their scores.
        :param query_id: int, query id of query that should be explained
        :param doc_id: int, id of document that should be explained
        :param fields: list of fields that should be searched, by default 'text' and 'title' are searched
        :param eval_objs: list of EvaluationObj; if None it uses the ones from the ComparisonTool
        :return: pandas data frame
        """
        explain_dict = defaultdict(list)
        for obj in eval_objs:
            # explain_dict[obj.name] = defaultdict(list)
            explain = obj.explain_query(query_id, doc_id, fields, dumps=False)
            for field in fields:
                for function in explain[field]['details']:
                    explain_dict['Approach'].append(obj.name)
                    explain_dict['Field'].append(field)
                    explain_dict['Terms'].append(self._extract_terms(function["function"]["description"]))
                    explain_dict['Term Score'].append(function["function"]["value"])
                    explain_dict['Term Frequency per Document'].append(
                        function["function"]["n, number of documents containing term"])
                    explain_dict['Occurrences of Term within Document'].append(
                        function["function"]["freq, occurrences of term within document"])
        # group_counter= 1
        # for terms_1 in explain_dict[eval_objs[0].name]['Terms']:
        #   explain_dict[eval_objs[0].name]['Group'] = group_counter
        #  for eval_obj in eval_objs[1:]:
        #     for terms_2 in explain_dict[eval_obj.name]['Terms']:
        #        if not set(terms_1).isdisjoint(terms_2):
        #           explain_dict[eval_objs[0].name]['Group'] = group_counter
        return pd.DataFrame(data=explain_dict).sort_values(by=['Terms'])

    def _get_csv_terms(self, query_id, doc_id, fields, eval_objs):
        """
        Returns dict containing all the found terms and their scores.
        :param query_id: int, query id of query that should be explained
        :param doc_id: int, id of document that should be explained
        :param fields: list of fields that should be searched, by default 'text' and 'title' are searched
        :param eval_objs: list of EvaluationObj; if None it uses the ones from the ComparisonTool
        :return: dict
        """
        explain_dict = defaultdict()
        for obj in eval_objs:
            explain_dict[obj.name] = ['searched terms']
            explain_dict[obj.name+'2'] = ['term score']
            explain = obj.explain_query(query_id, doc_id, fields, dumps=False)
            for field in fields:
                for function in explain[field]['details']:
                    explain_dict[obj.name].append(self._extract_terms(function["function"]["description"]))
                    explain_dict[obj.name+'2'].append(str(function["function"]["value"]).replace('.', ','))
        longest_term_list = len(explain_dict[eval_objs[0].name])
        for term_1 in explain_dict[eval_objs[0].name]:
            for eval_obj in eval_objs[1:]:
                longest_term_list = len(explain_dict[eval_obj.name]) if longest_term_list < len(explain_dict[eval_obj.name]) else longest_term_list
                for term_2 in explain_dict[eval_obj.name]:
                    if (not term_1 == term_2) and (term_1 in term_2 or term_2 in term_1):
                        new_term = term_1+'\n'+term_2
                        explain_dict[eval_objs[0].name] = [t.replace(term_1, new_term) for t in explain_dict[eval_objs[0].name]]
                        explain_dict[eval_obj.name] = [t.replace(term_1, new_term) for t in explain_dict[eval_obj.name]]
        for eval_obj in eval_objs:
            if longest_term_list > len(explain_dict[eval_obj.name]):
                term_ext = ['']*(longest_term_list-len(explain_dict[eval_obj.name]))
                val_ext = [0]*(longest_term_list-len(explain_dict[eval_obj.name]))
                explain_dict[eval_obj.name].extend(term_ext)
                explain_dict[eval_obj.name+'2'].extend(val_ext)
        return explain_dict

    def _extract_terms(self, string):
        """
        Extracts terms from explain_query method
        :param string:
        :return: list of extracted terms
        """
        term_regx = re.compile(':[a-zA-ZäöüÄÖÜß]*\s')
        terms = re.findall(term_regx, string)
        terms = ', '.join([term.replace(':', '').strip() for term in terms])
        return terms

    def calculate_difference(self, condition='fscore', dumps=False):
        """
        Calculates the difference per query for the given condition.
        "fscore", "precision" and "recall" are possible conditions.
        :param condition: string, "fscore", "precision" or "recall"
        :param dumps: True or False, if True it returns json.dumps, if False saves to object variable
        :return: dictionary with value differences
        """
        diff = defaultdict(dict)
        diff_name = condition + '_diffs'
        # get all condition values from the first approach
        for query, data in getattr(self.eval_obj_1, condition).items():
            if not query == 'total':
                # save for each query the difference between condition value of approach 1 and approach 2
                diff[query] = {diff_name: abs(data[condition] - getattr(self.eval_obj_2, condition)[query][condition])}
        # sort values descending
        diff_ordered = OrderedDict(sorted(diff.items(), key=lambda i: i[1][diff_name]))
        diff_ordered['total'] = {
            diff_name: abs(getattr(self.eval_obj_1, condition)['total'] - getattr(self.eval_obj_2, condition)['total'])}
        if dumps:
            return json.dumps(diff_ordered, indent=4)
        else:
            setattr(self, diff_name, diff_ordered)

    def get_disjoint_sets(self, distribution, highest=False):
        """
        Returns the disjoint sets of the given distribution
        :param distribution: str, possible arguments are 'false_positives' and 'false_negatives'
        :param highest: if True it returns the set with the highest count of disjoints
        :return: a dict with disjoint lists for each approach in a dictionary for each query regarding the distribution
        """
        results = defaultdict(dict)
        # get query names
        for query, data in getattr(self.eval_obj_1, distribution).items():
            results[query]['question'] = data['question']
            results[query][distribution + ' ' + self.eval_obj_1.name] = []
            results[query][distribution + ' ' + self.eval_obj_2.name] = []
            # iterate over list of results in set 1 and find disjoint results
            for res_1 in data[distribution]:
                # if result is in set 1 but not in set 2 it's saved
                if not any(res_1['doc']['id'] in el['doc'].values() for el in
                           getattr(self.eval_obj_2, distribution)[query][distribution]):
                    results[query][distribution + ' ' + self.eval_obj_1.name].append(res_1)
            # iterate over list of results in set 2 and find disjoint results
            for res_2 in getattr(self.eval_obj_2, distribution)[query][distribution]:
                # if result is in set 2 but not in set 1 it's saved
                if not any(res_2['doc']['id'] in el['doc'].values() for el in
                           getattr(self.eval_obj_1, distribution)[query][distribution]):
                    results[query][distribution + ' ' + self.eval_obj_2.name].append(res_2)
            results[query]['count'] = len(results[query][distribution + ' ' + self.eval_obj_1.name]) + len(
                results[query][distribution + ' ' + self.eval_obj_2.name])
        filtered_results = {key: val for key, val in results.items() if val['count'] != 0}
        ordered_results = OrderedDict(sorted(filtered_results.items(), key=lambda i: i[1]['count']))
        if not highest:
            return ordered_results
        else:
            elements = list(ordered_results.items())
            return elements[-1]

    def visualize_distributions(self, queries=None, eval_objs=None,
                                distributions=['true_positives', 'false_positives', 'false_negatives']):
        """
        Visualizes distributions in comparison for given queries and given approaches.
        :param queries: int or list of ints of query ids or None; if None it searches with all queries
        :param eval_objs: list of EvaluationObj; if None it uses the ones from the ComparisonTool
        :param distributions: list of distributions that should be printed; by default tp, fp and fn are used
        """
        if not eval_objs:
            eval_objs = [self.eval_obj_1, self.eval_obj_2]
        queries = eval_objs[0]._check_searched_queries(queries)
        panda_dist = self._get_distributions(queries, eval_objs, distributions)
        dist_colors = [self.pragma_colors[1], self.pragma_colors[4], self.pragma_colors[5]]
        custom_palette = sns.set_palette(sns.color_palette(dist_colors))
        sns.set_theme(context='paper', style='whitegrid', palette=custom_palette)
        plt.figure(figsize=(12, 8))
        ax = sns.countplot(x="Approach", hue="Distributions", data=panda_dist, palette=custom_palette)
        ax.set_title("true positives, false positives and false negatives")
        ax.set_xlabel("Approaches")
        ax.set_ylabel("Distributions")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.show()

    def visualize_condition(self, queries=None, eval_objs=None, conditions=['precision', 'recall', 'fscore']):
        """
        Visualizes distributions in comparison for given queries and given approaches.
        :param queries: int or list of ints of query ids or None; if None it searches with all queries
        :param eval_objs: list of EvaluationObj; if None it uses the ones from the ComparisonTool
        :param conditions: list of conditions that should be printed; by default precision, recall and f1-score are used
        """
        if conditions is None:
            conditions = ['precision', 'recall', 'fscore']
        if not eval_objs:
            eval_objs = [self.eval_obj_1, self.eval_obj_2]
        queries = eval_objs[0]._check_searched_queries(queries)
        panda_cond = self._get_conditions(queries, eval_objs, conditions)
        custom_palette = sns.set_palette(sns.color_palette(self.pragma_colors))
        sns.set_theme(context='paper', style='whitegrid', palette=custom_palette)
        g = sns.catplot(
            data=panda_cond, kind="bar",
            x="Value", y='Scores', hue="Approach",
            ci=None, alpha=.6, height=8
        )
        g.despine(left=True)
        g.set_axis_labels('Approach comparison')
        plt.show()

    def visualize_explanation(self, query_id, doc_id, fields=['text', 'title'], eval_objs=None):
        """
        Visualize in comparison which words were better scored using approach, specific query and a specific document.
        :param query_id: int, query id of query that should be explained
        :param doc_id: int, id of document that should be explained
        :param fields: list of fields that should be searched, by default 'text' and 'title' are searched
        :param eval_objs: list of EvaluationObj; if None it uses the ones from the ComparisonTool
        """
        if not eval_objs:
            eval_objs = [self.eval_obj_1, self.eval_obj_2]
        panda_explain = self._get_explain_terms(query_id, doc_id, fields, eval_objs)
        custom_palette = sns.set_palette(sns.color_palette(self.pragma_colors))
        sns.set_context('paper', rc={'figure.figsize': (20, 14)})
        sns.set_theme(context='paper', style='whitegrid', palette=custom_palette)
        g = sns.barplot(x='Term Score', y='Terms', data=panda_explain, hue="Approach")
        sns.despine(left=True, bottom=True)
        plt.show()

    def visualize_explanation_csv(self, query_id, doc_id, path_to_save_to, fields=['text', 'title'], eval_objs=None):
        """
        Saves explanation table to csv
        :param query_id: int, query id of query that should be explained
        :param doc_id: int, id of document that should be explained
        :param path_to_save_to: path and filename the csv should be saved to
        :param fields: list of fields that should be searched, by default 'text' and 'title' are searched
        :param eval_objs: list of EvaluationObj; if None it uses the ones from the ComparisonTool
        :return: csv file to feed it into Google Sheets
        """
        if not eval_objs:
            eval_objs = [self.eval_obj_1, self.eval_obj_2]
        panda_explain = self._get_csv_terms(query_id, doc_id, fields, eval_objs)
        keys = sorted(panda_explain.keys())
        with open(path_to_save_to, "w") as outfile:
            writer = csv.writer(outfile, delimiter=";")
            writer.writerow(keys)
            writer.writerows(zip(*[panda_explain[key] for key in keys]))


    def get_specific_comparison(self, doc_id):
        """
        :param doc_id: int or list, doc id that should be looked at
        :return: dict, filled with comparison for given doc id
        """
        if type(doc_id) == int:
            doc_id = [doc_id]
        comp_dict = defaultdict()
        attr_list = ['true_positives', 'false_positives', 'false_negatives']
        for i in doc_id:
            comp_dict[i] = defaultdict()
            for attr in attr_list:
                for query, dist in getattr(self.eval_obj_1, attr).items():
                    for hit in dist[attr]:
                        try:
                            hit['doc'][i]
                            info = defaultdict
                            info[i] = hit['doc']
                            info[self.eval_obj_1.name + ' ' + attr] = [hit['highlight'], hit['position'], hit['score'],
                                                                       query]
                            comp_dict[i] = info
                        except KeyError:
                            pass
                for query, dist in getattr(self.eval_obj_2, attr).items():
                    for hit in dist[attr]:
                        try:
                            hit['doc'][i]
                            info = defaultdict
                            info[i] = hit['doc']
                            info[self.eval_obj_2.name + ' ' + attr] = [hit['highlight'], hit['position'], hit['score'],
                                                                       query]
                            comp_dict[i] = info
                        except KeyError:
                            pass
        return comp_dict
