import json
import re
import warnings
from collections import defaultdict
from collections import OrderedDict

from elasticsearch import Elasticsearch

from search_analysis.tools import EvaluationObject


class ESEvaluationObject(EvaluationObject):
    def __init__(self, host, query_rel_dict, index, name, verified_certificates=False):
        self.queries_rels = dict(query_rel_dict)
        self.index = index
        self.name = name
        if verified_certificates:
            self.elasticsearch = Elasticsearch([host])
        else:
            self.elasticsearch = Elasticsearch(
                [host],
                ca_certs=False,
                verify_certs=verified_certificates,
                read_timeout=120,
            )
        self.elasticsearch.ping()
        self.true_positives = {}
        self.false_positives = {}
        self.false_negatives = {}
        self.recall = {}
        self.precision = {}
        self.fscore = {}
        # orange, green, turquoise, black, red, yellow, white
        self.pragma_colors = [
            "#ffb900",
            "#8cab13",
            "#22ab82",
            "#242526",
            "#cc0000",
            "#ffcc00",
            "#ffffff",
        ]

    def _check_size(self, k, size):
        """
        Checking `size` argument; size needs to be >= k.

        Parameters
        ----------
        :arg k: int
            ranking size
        :arg size: int or None
            search size, if size is None, it will set Elastisearch default value

        :Returns:
        -------

        :size: int
            adjusted search size

        """
        if size is not None:
            if size < k:
                size = k
        return size

    def _get_search_result(self, query_id, size, fields):
        """
        Sends a search request for every query to Elasticsearch and returns the result including highlighting.

        Parameters
        ----------
        :arg query_id: int
            current query id
        :arg size: int
            search size
        :arg fields: list of strings
            fields that should be searched on

        :Returns:
        -------
        :result: nested dict
            search result from Elasticsearch

        """
        body = self._get_highlights_search_body(
            self.queries_rels[query_id]["question"], size, fields
        )
        result = self.elasticsearch.search(index=self.index, body=body)
        return result

    def _get_highlights_search_body(self, query, size=20, fields=["text", "title"]):
        """
        Creates a search body with the highlights option to return a highlighted search result.

        Parameters
        ----------
        :arg query: str
            query to search on
        :arg size: int
            searched size
        :arg fields: list of str
            fields, that should be searched

        :Returns:
        -------
        search body for highlighting the matched results

        """
        return {
            "size": size,
            "query": {"multi_match": {"query": query, "fields": fields}},
            "highlight": {"fields": {"*": {}}},
        }

    def _check_searched_queries(self, query_ids):
        """
        Checks if query_ids is an int or None and transforms it to a list.
        If it's None, all available queries are used for the search.

        Parameters
        ----------
        :arg query_ids: list, int or None

        :Returns:
        -------
        :query_ids: list
            transformed query ids

        """
        if type(query_ids) == int:
            query_ids = [query_ids]
        if query_ids is None:
            query_ids = [*self.queries_rels]
        return query_ids

    def _create_hit(self, pos, hit, fields):
        """
        Creates a structured dict of the hit from Elasticsearch.

        Parameters
        ----------
        :arg pos: int or str,
            ranking position
        :arg hit: nested dict
            hit found in Elasticsearch
        :arg fields: list of strings
            fields so analyze

        :Returns:
        -------
        :variable: nested dict
            structured hit

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
            "highlight": {},
        }
        for field_name, highlight in highlights.items():
            variable["highlight"][field_name] = highlight
        for field, data in doc_fields.items():
            variable["doc"][field] = data
        return variable

    def _initialize_distributions(
        self, searched_queries=None, fields=["text", "title"], size=20, k=20
    ):
        """
        Gets distributions and saves them in self.true_positives, self.false_positives and self.false_negatives.

        Parameters
        ----------
        :arg searched_queries: int or list or None
            query ids; if None it searches with all queries
        :arg fields: list of str
            fields that should be searched on
        :arg size: int
            search size
        :arg k: int
            number of results that should be returned and ranked

        Returns
        -------

        """
        size = self._check_size(k, size)
        searched_queries = self._check_searched_queries(searched_queries)
        self.true_positives = self.get_true_positives(
            searched_queries, fields, size, k, False
        )
        self.false_positives = self.get_false_positives(
            searched_queries, fields, size, k, False
        )
        self.false_negatives = self.get_false_negatives(
            searched_queries, fields, size, k, False
        )

    def _calculate_recall(self, tp, fn):
        """
        Calculates Recall.

        https://en.wikipedia.org/wiki/Precision_and_recall

        Parameters
        ----------
        :arg tp: int
            true positives
        :arg fn: int
            false negatives

        :Returns:
        -------
        Recall value

        """
        if (tp + fn) == 0:
            warnings.warn(
                "Sum of true positives and false negatives is 0. Please check your data, "
                "this shouldn't happen. Maybe you tried searching on the wrong index, with the wrong "
                "queries or on the wrong fields."
            )
            return 0
        return tp / (tp + fn)

    def _calculate_precision(self, tp, fp):
        """
        Calculates Precision.

        https://en.wikipedia.org/wiki/Precision_and_recall

        Parameters
        ----------
        :arg tp: int
            true positives
        :arg fp: int
            false positives

        :Returns:
        -------
        Precision value

        """
        if (tp + fp) == 0:
            warnings.warn(
                "Sum of true positives and false positives is 0. Please check your data, "
                "this shouldn't happen. Maybe you tried searching on the wrong index, with the wrong "
                "queries or on the wrong fields."
            )
            return 0
        return tp / (tp + fp)

    def _calculate_fscore(self, precision, recall, factor=1):
        """
        Calculates F-Score.

        https://en.wikipedia.org/wiki/F-score

        Parameters
        ----------
        :arg precision: int
            precision value
        :arg recall: int
            recall value
        :arg factor: int or float
            1 is the default to calculate F1-Score, but you can also choose another factor

        :Returns:
        -------
        F-Score value

        """
        if recall or precision != 0:
            if factor is 1:
                return (2 * precision * recall) / (precision + recall)
            else:
                return (1 + factor ** 2) * (
                    (precision * recall) / (factor ** 2 * precision + recall)
                )
        else:
            warnings.warn("The value of precision and/or recall is 0.")
            return 0

    def get_true_positives(
        self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False,
    ):
        """
        Calculates true positives from given search queries.


        Parameters
        ----------
        :arg searched_queries: int or list or None
            query ids; if None it searches with all queries
        :arg fields: list of str
            fields that should be searched on
        :arg size: int
            search size
        :arg k: int
            top results that should be returned from Elasticsearch
        :arg dumps: True or False
            if True it returns json.dumps, if False it returns json

        :Returns:
        -------

        :true positives: json

        """
        size = self._check_size(k, size)
        searched_queries = self._check_searched_queries(searched_queries)
        # initializing dictionary of true positives;
        true_pos = {}
        for query_ID in searched_queries:
            true_pos["Query_" + str(query_ID)] = {
                "question": self.queries_rels[query_ID]["question"],
                "true_positives": [],
            }
            result = self._get_search_result(query_ID, size, fields)
            for pos, hit in enumerate(result["hits"]["hits"], start=1):
                # check if `hit` IS a relevant document; in case `hits` position < k, it counts as a true positive;
                if (
                    int(hit["_id"])
                    in self.queries_rels[query_ID]["relevance_assessments"]
                    and pos <= k
                ):
                    true = self._create_hit(pos, hit, fields)
                    true_pos["Query_" + str(query_ID)]["true_positives"].append(true)
        if dumps:
            return json.dumps(true_pos, indent=4)
        else:
            return true_pos

    def get_false_positives(
        self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False,
    ):
        """
        Calculates false positives from given search queries.

        Parameters
        ----------
        :arg searched_queries: int or list or None
            query ids; if None it searches with all queries
        :arg fields: list of str
            fields that should be searched on
        :arg size: int
            search size
        :arg k: int
            top results that should be returned from Elasticsearch
        :arg dumps: True or False
            if True it returns json.dumps, if False it returns json

        :Returns:
        -------

        :false positives: json

        """
        size = self._check_size(k, size)
        searched_queries = self._check_searched_queries(searched_queries)
        # initializing dictionary of false positives;
        false_pos = {}
        for query_ID in searched_queries:
            false_pos["Query_" + str(query_ID)] = {
                "question": self.queries_rels[query_ID]["question"],
                "false_positives": [],
            }
            result = self._get_search_result(query_ID, size, fields)
            # for every `hit` in the search results... ;
            for pos, hit in enumerate(result["hits"]["hits"], start=1):
                # check if `hit` IS a relevant document; in case `hits` position < k, it counts as a true positive;
                if (
                    int(hit["_id"])
                    not in self.queries_rels[query_ID]["relevance_assessments"]
                    and pos < k
                ):
                    false = self._create_hit(pos, hit, fields)
                    false_pos["Query_" + str(query_ID)]["false_positives"].append(false)
        if dumps:
            return json.dumps(false_pos, indent=4)
        else:
            return false_pos

    def get_false_negatives(
        self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False,
    ):
        """
        Calculates false negatives from given search queries.

        Parameters
        ----------
        :arg searched_queries: int or list or None
            query ids; if None it searches with all queries
        :arg fields: list of str
            fields that should be searched on
        :arg size: int
            search size
        :arg k: int
            top results that should be returned from Elasticsearch
        :arg dumps: True or False
            if True it returns json.dumps, if False it returns json

        :Returns:
        -------

        :false negatives: json

        """
        size = self._check_size(k, size)
        searched_queries = self._check_searched_queries(searched_queries)
        # initializing dictionary of false negatives;
        false_neg = {}
        for query_ID in searched_queries:
            false_neg["Query_" + str(query_ID)] = {
                "question": self.queries_rels[query_ID]["question"],
                "false_negatives": [],
            }
            result = self._get_search_result(query_ID, size, fields)
            # iterating through the results;
            query_rel = self.queries_rels[query_ID]["relevance_assessments"].copy()
            for pos, hit in enumerate(result["hits"]["hits"], start=1):
                # false negatives require that the result belongs to the relevance assessments;
                if int(hit["_id"]) in query_rel:
                    if pos > k:
                        # create a `false negative`;
                        false = self._create_hit(pos, hit, fields)
                        # save `false hit/positive`;
                        false_neg["Query_" + str(query_ID)]["false_negatives"].insert(
                            0, false
                        )
                        # removes the `hit` from the remaining relevant documents;
                    query_rel.remove(int(hit["_id"]))
            # adds all missing relevant docs to the start of the `false negatives` with `position = -1`;
            for relevant_doc in query_rel:
                # create a `false negative`;
                false = {"position": -1, "score": None, "doc": {"id": relevant_doc}}
                false_neg["Query_" + str(query_ID)]["false_negatives"].insert(0, false)
        if dumps:
            return json.dumps(false_neg, indent=4)
        else:
            return false_neg

    def get_recall(
        self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False,
    ):
        """
        Calculates recall for every search query given.

        Parameters
        ----------
        :arg searched_queries: int or list or None
            searched queries; if None it searches with all queries
        :arg fields: list of str
            fields that should be searched on
        :arg size: int
            search size
        :arg k: int
            top results that should be returned from Elasticsearch
        :arg dumps: True or False
            if True it returns json.dumps, if False it saves to object variable

        :Returns:
        -------

        json with Recall values

        """
        if not self.true_positives:
            self._initialize_distributions(searched_queries, fields, size, k)
        true_pos = self.count_distribution(
            "true_positives", self.true_positives, False, k
        )
        false_neg = self.count_distribution(
            "false_negatives", self.false_negatives, False, k
        )
        recall = defaultdict(dict)
        recall_sum = 0.0
        for query, data in true_pos.items():
            if not query == "total":
                recall_value = self._calculate_recall(
                    true_pos[query]["count"], false_neg[query]["count"]
                )
                recall[query]["recall"] = recall_value
                recall_sum += recall_value
        recall = OrderedDict(sorted(recall.items(), key=lambda i: i[1]["recall"]))
        recall["total"] = recall_sum / len(self.queries_rels)
        if dumps:
            return json.dumps(recall, indent=4)
        else:
            self.recall = recall

    def get_precision(
        self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False,
    ):
        """
        Calculates precision for every search query given.

        Parameters
        ----------
        :arg searched_queries: int or list or None
            searched queries; if None it searches with all queries
        :arg fields: list of str
            fields that should be searched on
        :arg size: int
            search size
        :arg k: int
            top results that should be returned from Elasticsearch
        :arg dumps: True or False
            if True it returns json.dumps, if False it saves to object variable

        :Returns:
        -------

        json with Precision values

        """
        if not self.true_positives:
            self._initialize_distributions(searched_queries, fields, size, k)
        true_pos = self.count_distribution(
            "true_positives", self.true_positives, False, k
        )
        false_pos = self.count_distribution(
            "false_positives", self.false_positives, False, k
        )
        precision = defaultdict(dict)
        precision_sum = 0.0
        for query, data in true_pos.items():
            if not query == "total":
                precision_value = self._calculate_precision(
                    true_pos[query]["count"], false_pos[query]["count"]
                )
                precision[query]["precision"] = precision_value
                precision_sum += precision_value
        precision = OrderedDict(
            sorted(precision.items(), key=lambda i: i[1]["precision"])
        )
        precision["total"] = precision_sum / len(self.queries_rels)
        if dumps:
            return json.dumps(precision, indent=4)
        else:
            self.precision = precision

    def get_fscore(
        self,
        searched_queries=None,
        fields=["text", "title"],
        size=20,
        k=20,
        dumps=False,
        factor=1,
    ):
        """
        Calculates f-score for every search query given.

        Parameters
        ----------
        :arg searched_queries: int or list or None
            searched queries; if None it searches with all queries
        :arg fields: list of str
            fields that should be searched on
        :arg size: int
            search size
        :arg k: int
            top results that should be returned from Elasticsearch
        :arg dumps: True or False
            if True it returns json.dumps, if False it saves to object variable
        :arg factor: int
            can be used to weight the F score, default is 1

        :Returns:
        -------

        json with F-score values

        """
        if not self.recall:
            self.get_recall(searched_queries, fields, size, k, False)
        if not self.precision:
            self.get_precision(searched_queries, fields, size, k, False)
        fscore = defaultdict(dict)
        for query, data in self.precision.items():
            if not query == "total":
                fscore_value = self._calculate_fscore(
                    self.precision[query]["precision"],
                    self.recall[query]["recall"],
                    factor,
                )
                fscore[query]["fscore"] = fscore_value
        fscore = OrderedDict(sorted(fscore.items(), key=lambda i: i[1]["fscore"]))
        fscore["total"] = self._calculate_fscore(
            self.precision["total"], self.recall["total"], factor
        )
        if dumps:
            return json.dumps(fscore, indent=4)
        else:
            self.fscore = fscore

    def count_distribution(self, distribution, distribution_json, dumps=False, k=20):
        """
        Counts given distribution per query, relevant documents and calculates percentages given the relevant documents.

        Parameters
        ----------
        :arg distribution: string
            'true_positives', 'false_positives' or 'false_negatives'
        :arg distribution_json: json
            json with all the distributions needed; e.g. EvaluationObject.true_positives
        :arg dumps: True or False
            if True it returns json.dumps, if False it returns json
        :arg k: int
            size of k top search results

        :Returns:
        ---------
        :sorted_counts: json
                counted distribution per query, as a sum and as a percentage

        """
        if isinstance(distribution_json, str):
            result_json = json.loads(distribution_json)
        else:
            result_json = distribution_json
        counts = defaultdict(dict)
        sum_rels = 0
        sum_count = 0
        for query in result_json:
            query_id = int(query.strip("Query_"))
            count_query = int(len(result_json[query][distribution]))
            count_rels = int(len(self.queries_rels[query_id]["relevance_assessments"]))
            if distribution == "false_positives":
                f = k - count_query
                if f == count_rels or count_rels == 0:
                    percentage = 0
                else:
                    percentage = (count_rels - f) * 100 / count_rels
            else:
                if count_rels == 0:
                    percentage = 0
                else:
                    percentage = 100 * count_query / count_rels
            counts[query] = {
                "count": count_query,
                "percentage": percentage,
                "relevant documents": count_rels,
            }
            sum_rels += count_rels
            sum_count += count_query
        if distribution == "false_positives":
            f = (k * len(counts)) - sum_count
            if f == sum_rels or sum_rels == 0:
                sum_percentage = 0
            else:
                sum_percentage = (sum_rels - f) * 100 / sum_rels
        else:
            if sum_rels == 0:
                sum_percentage = 0
            else:
                sum_percentage = 100 * sum_count / sum_rels
        sorted_counts = OrderedDict(
            sorted(counts.items(), key=lambda i: i[1]["percentage"])
        )
        sorted_counts["total"] = {
            "total sum": sum_count,
            "percentage": str(sum_percentage) + "%",
        }
        if dumps:
            return json.dumps(sorted_counts, indent=4)
        else:
            return sorted_counts

    def explain_query(self, query_id, doc_id, fields=["text", "title"], dumps=True):
        """
        Returns an Elasticsearch explanation for given query and document.

        https://www.elastic.co/guide/en/elasticsearch/reference/current/search-explain.html

        Parameters
        ----------
        :arg query_id: int
            id of query that should be explained
        :arg doc_id: int
            id of document that should be explained
        :arg fields: list of str
            fields that should be searched on
        :arg dumps: True or False
            True by default, if False it won't convert dict to json

        :Returns:
        -------

        json or dict explaining query and document match
        """
        query_body = {
            "query": {
                "multi_match": {
                    "fields": fields,
                    "query": self.queries_rels[query_id]["question"],
                }
            }
        }
        explain = defaultdict(lambda: defaultdict(lambda: []))
        explanation = self.elasticsearch.explain(self.index, doc_id, query_body)[
            "explanation"
        ]
        explain["score"] = explanation["value"]
        if explain["score"] == 0.0:
            print(
                "No hits with that request, please check all the parameters like index, fields, query dictionary, "
                "etc."
            )
            return explanation
        if explanation["description"] != "max of:":
            explanation = {"details": [explanation]}

        for el in explanation["details"]:
            field = "".join(
                f for f in fields if re.search(f, el["details"][0]["description"])
            )
            explain[field]["total_value"] = el["details"][0]["value"]
            explain[field]["details"] = []
            for detail in el["details"]:
                doc_freq = 0
                term_freq = 0.0
                for val in detail["details"][0]["details"]:
                    try:
                        if re.match(
                            "n, number of documents", val["details"][0]["description"]
                        ):
                            doc_freq = val["details"][0]["value"]
                    except IndexError:
                        continue
                    try:
                        if re.match(r".*[Ff]req", val["details"][0]["description"]):
                            term_freq = val["details"][0]["value"]
                    except IndexError:
                        continue
                explain[field]["details"].append(
                    {
                        "function": {
                            "value": detail["value"],
                            "description": detail["description"],
                            "n, number of documents containing term": doc_freq,
                            "freq, occurrences of term within document": term_freq,
                        }
                    }
                )
        if dumps:
            return json.dumps(explain, indent=4)
        else:
            return explain
