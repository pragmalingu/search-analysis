import collections
import csv
from collections import OrderedDict, defaultdict
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
import re

from src.search_analysis import ComparisonToolBase
from src.search_analysis.tools.elasticsearch.es_evaluation_object import ESEvaluationObject


class ComparisonTool(ComparisonToolBase):
    def __init__(self, host, qry_rel_dict, eval_obj_1=None, eval_obj_2=None,
                 fields=['text', 'title'], index_1=None, index_2=None, name_1='approach_1',
                 name_2='approach_2', size=20, k=20):
        self.qrys_rels = qry_rel_dict
        if eval_obj_1 is None:
            eval_obj_1 = ESEvaluationObject(host, self.qrys_rels, index_1, name_1)
        if eval_obj_2 is None:
            eval_obj_1 = ESEvaluationObject(host, self.qrys_rels, index_2, name_2)
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
        Gets condition values for the visualization as a pandas data frame.

        Parameters
        ----------
        :arg queries: int or list
            query ids
        :arg eval_objs: list
            EvaluationObjs that should be compared
        :arg conditions: list
            conditions that should be printed

        :Returns:
        -------
        pandas data frame

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
        Gets distribution values for the visualization as a pandas data frame.

        Parameters
        ----------
        :arg queries: int or list
            query ids
        :arg eval_objs: list
            EvaluationObjs that should be compared
        :arg distributions: list
            distributions that should be printed

        :Returns:
        -------
        pandas data frame

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

        Parameters
        ----------
        :arg query_id: int
            query id of query that should be explained
        :arg doc_id: int
            id of document that should be explained
        :arg fields: list
            fields that should be searched
        :arg eval_objs: list
            EvaluationObjs that should be compared

        :Returns:
        -------
        pandas data frame

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

    def _get_csv_terms(self, query_id, doc_id, fields, decimal_separator, eval_objs):
        """
        Returns dict containing all the found terms and their scores.

        Parameters
        ----------
        :arg query_id: int
            query id of query that should be explained
        :arg doc_id: int
            id of document that should be explained
        :arg fields: list
            fields that should be searched
        :arg decimal_separator: string
            choose a decimal separator; by default it's a comma, but for english you might prefer a dot
        :arg eval_objs: list
            EvaluationObjs that should be compared

        Returns
        -------

        """
        term_dict = defaultdict(dict)
        for obj in eval_objs:
            explain = obj.explain_query(query_id, doc_id, fields, dumps=False)
            for field in fields:
                for function in explain[field]['details']:
                    term_dict[obj.name][field+': '+(self._extract_terms(function["function"]["description"]))] = str(
                        function["function"]["value"]).replace('.', decimal_separator)
        extra_1 = set(term_dict[eval_objs[0].name]) - set(term_dict[eval_objs[1].name])
        for key in extra_1:
            term_dict[eval_objs[1].name][key] = 0
        extra_2 = set(term_dict[eval_objs[1].name]) - set(term_dict[eval_objs[0].name])
        for key in extra_2:
            term_dict[eval_objs[0].name][key] = 0
        explain_dict = defaultdict()
        for obj in eval_objs:
            ordered_terms = collections.OrderedDict(sorted(term_dict[obj.name].items()))
            searched_terms = list(ordered_terms.keys())
            term_scores = list(ordered_terms.values())
            explain_dict[obj.name] = ['searched terms']
            explain_dict[obj.name + '2'] = ['term score']
            explain_dict[obj.name].extend(searched_terms)
            explain_dict[obj.name + '2'].extend(term_scores)
        return explain_dict

    def _extract_terms(self, string):
        """
        Extracts terms from explain_query method.

        Parameters
        ----------
        :arg string: str
            string of all the matched terms

        :Returns:
        -------
        :terms: list of str
            extracted terms

        """
        term_regx = re.compile(':[a-zA-ZäöüÄÖÜß]*\s')
        terms = re.findall(term_regx, string)
        terms = ', '.join([term.replace(':', '').strip() for term in terms])
        return terms

    def calculate_difference(self, condition='fscore', dumps=False):
        """
        Calculates the difference per query for the given condition.

        Parameters
        ----------
        :arg condition: string
            "fscore", "precision" or "recall"
        :arg dumps: True or False
            if True it returns json.dumps, if False saves to object variable

        :Returns:
        -------
        json with value differences

        """
        diff = defaultdict(dict)
        diff_name = condition + '_diffs'
        # get all condition values from the first approach
        for query, data in getattr(self.eval_obj_1, condition).items():
            if not query == 'total':
                # save for each query the difference between condition value of approach 1 and approach 2
                diff[query] = {
                    str(self.eval_obj_1.name): data[condition],
                    str(self.eval_obj_2.name): getattr(self.eval_obj_2, condition)[query][condition],
                    diff_name: abs(data[condition] - getattr(self.eval_obj_2, condition)[query][condition])}
        # sort values descending
        diff_ordered = OrderedDict(sorted(diff.items(), key=lambda i: i[1][diff_name]))
        diff_ordered['total'] = {
            str(self.eval_obj_1.name): getattr(self.eval_obj_1, condition)['total'],
            str(self.eval_obj_2.name): getattr(self.eval_obj_2, condition)['total'],
            diff_name: abs(getattr(self.eval_obj_1, condition)['total'] - getattr(self.eval_obj_2, condition)['total'])}
        if dumps:
            return json.dumps(diff_ordered, indent=4)
        else:
            setattr(self, diff_name, diff_ordered)

    def get_disjoint_sets(self, distribution, highest=False):
        """
        Returns the disjoint sets of the given distribution.

        Parameters
        ----------
        :arg distribution: str
            distribution to return; possible arguments are 'false_positives' and 'false_negatives'
        :arg highest: True or False
            if True it only returns the set with the highest count of disjoints

        :Returns:
        -------

        :ordered_results: OrderedDict
            disjoint lists for each approach in a dictionary for each query regarding the distribution

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

    def get_specific_comparison(self, query_id, doc_id, fields=['text', 'title']):
        """
        Function to get position, highlights and scores for a specific query and a specific query in comparison.

        Parameters
        ----------
        :arg query_id
        :arg doc_id: int
            doc id that should be looked at
        :arg fields: list
            list of fields that should be searched on
        :Returns:
        -------
        :json.dumps(comp_dict): dict dumped as json
            filled with comparison for given query and doc id
        """
        comp_dict = defaultdict()
        attr_list = ['true_positives', 'false_positives', 'false_negatives']
        eval_objs = [self.eval_obj_1, self.eval_obj_2]
        comp_dict['Query ' + str(query_id)] = self.qrys_rels[query_id]
        comp_dict[str(self.eval_obj_1.name)] = defaultdict()
        comp_dict[str(self.eval_obj_2.name)] = defaultdict()
        for attr in attr_list:
            for obj in eval_objs:
                if 'Query_' + str(query_id) in getattr(obj, attr).keys():
                    hit_list = getattr(obj, attr)['Query_' + str(query_id)][attr]
                    for hit in hit_list:
                        if hit['doc']['id'] == doc_id:
                            try:
                                if not comp_dict[str(obj.name)]:
                                    comp_dict['Document ' + str(doc_id)] = {field: hit['doc'][field] for field in
                                                                            fields}
                                    comp_dict[str(obj.name)]['position'] = hit['position']
                                    comp_dict[str(obj.name)]['score'] = hit['score']
                                    comp_dict[str(obj.name)]['highlight'] = hit['highlight']
                                    comp_dict[str(obj.name)]['distribution'] = attr
                            except KeyError:
                                pass
        for obj in eval_objs:
            if not comp_dict[str(obj.name)]:
                logging.warning('There is no hit for query ' + str(query_id) + ' and document ' + str(doc_id) + '. This might be because of a too small size. Keep in mind that the size is 20 by default.')
        return print(json.dumps(comp_dict, indent=4))

    def visualize_distributions(self, queries=None, eval_objs=None,
                                distributions=['true_positives', 'false_positives', 'false_negatives'], download=False,
                                path_to_file='./save_vis_distributions.svg'):
        """
        Visualizes distributions in comparison for given queries and given approaches.

        Parameters
        ----------
        :arg queries: int or list or None
            if None it searches with all queries
        :arg eval_objs: list
            EvaluationObjs; if None it uses the ones already implemented in the ComparisonTool object
        :arg distributions: list
            distributions that should be printed; by default tp, fp and fn are used
        :arg download: True or False
            saves the plot as svg; by default False which leads to not saving the visualization
        :arg path_to_file: string
            path and filename the visualization should be saved to, e.g. './myfolder/save_this.svg'

        :Prints:
        -------

        visualization via matplot as plt.show()

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
        if download:
            plt.gcf().subplots_adjust(bottom=0.08)
            plt.savefig(path_to_file, format="svg")
        plt.show()

    def visualize_condition(self, queries=None, eval_objs=None, conditions=['precision', 'recall', 'fscore'],
                            download=False, path_to_file='./save_vis_condition.svg'):
        """
        Visualizes conditions in comparison for given queries and given approaches.

        Parameters
        ----------
        :arg queries: int or list or None
            if None it searches with all queries
        :arg eval_objs: list
            EvaluationObjs; if None it uses the ones already implemented in the ComparisonTool object
        :arg conditions: list
            conditions that should be printed; by default precision, recall and f1-score are used
        :arg download: True or False
            saves the plot as svg; by default False which leads to not saving the visualization
        :arg path_to_file: string
            path and filename the visualization should be saved to, e.g. './myfolder/save_this.svg'

        :Prints:
        -------

        visualization via matplot as plt.show()

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
        if download:
            plt.gcf().subplots_adjust(bottom=0.08)
            plt.savefig(path_to_file, format="svg")
        plt.show()

    def visualize_explanation(self, query_id, doc_id, fields=['text', 'title'], eval_objs=None, download=False,
                              path_to_file='./save_vis_explaination.svg'):
        """
        Visualize in comparison which words were better scored using approach, specific query and a specific document.

        Parameters
        ----------
        :arg queries: int or list or None
            if None it searches with all queries
        :arg doc_id: int
            id of document that should be explained
        :arg fields: list
            fields that should be searched, by default 'text' and 'title' are searched
        :arg eval_objs: list
            EvaluationObjs; if None it uses the ones already implemented in the ComparisonTool object
        :arg download: True or False
            saves the plot as svg; by default False which leads to not saving the visualization
        :arg path_to_file: string
            path and filename the visualization should be saved to, e.g. './myfolder/save_this.svg'

        :Prints:
        -------

        visualization via matplot as plt.show()

        """
        if not eval_objs:
            eval_objs = [self.eval_obj_1, self.eval_obj_2]
        panda_explain = self._get_explain_terms(query_id, doc_id, fields, eval_objs)
        custom_palette = sns.set_palette(sns.color_palette(self.pragma_colors))
        sns.set_context('paper', rc={'figure.figsize': (20, 14)})
        sns.set_theme(context='paper', style='whitegrid', palette=custom_palette)
        g = sns.barplot(x='Term Score', y='Terms', data=panda_explain, hue="Approach")
        sns.despine(left=True, bottom=True)
        if download:
            plt.gcf().subplots_adjust(bottom=0.08)
            plt.savefig(path_to_file, format="svg")
        plt.show()

    def visualize_explanation_csv(self, query_id, doc_id, path_to_save_to, fields=['text', 'title'], decimal_separator=',', eval_objs=None):
        """
        Saves explanation table to csv

        Parameters
        ----------
        :arg query_id: int
            query id of query that should be explained
        :arg doc_id: int
            id of document that should be explained
        :arg path_to_save_to: string
            path and filename the visualization should be saved to, e.g. './myfolder/save_that.csv'
        :arg fields: list
            fields that should be searched, by default 'text' and 'title' are searched
        :arg decimal_separator: string
            choose a decimal separator; by default it's a comma, but for english you might prefer a dot
        :arg eval_objs: list or None
            exactly two EvaluationObjs; if None it uses the ones from the ComparisonTool

        :Returns:
        -------
        csv file to feed it to program to create graphs, e.g. Google Sheets or Microsoft Excel

        """
        if not eval_objs:
            eval_objs = [self.eval_obj_1, self.eval_obj_2]
        panda_explain = self._get_csv_terms(query_id, doc_id, fields, decimal_separator, eval_objs)
        keys = sorted(panda_explain.keys())
        with open(path_to_save_to, "w") as outfile:
            writer = csv.writer(outfile, delimiter=";")
            writer.writerow(keys)
            writer.writerows(zip(*[panda_explain[key] for key in keys]))
