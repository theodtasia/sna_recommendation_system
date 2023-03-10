import pickle
from os.path import exists

import networkx as nx
import torch
from tqdm import tqdm

from preprocessing.clean_datasets import CleanData
from other.handle_files import TEST_EDGES_PATH, EDGE_ATTRIBUTES_PATH
from other.utils import dotdict


class EdgeHandler:

    def __init__(self, args):

        self.use_edge_attrs = args.use_edge_attrs
        self.day_limit = args.rerun_edge_attrs_day_limit

        if args.find_test_edges or args.rerun_edge_attrs:
            print("Prepare edges")
            self._prepare_edges()


    def loadTestEdges(self, day):
        test_edges = dotdict(pickle.load(open(EdgeHandler._negativeEdgesFile(day), 'rb')))

        test_edges.attributes = self.lookup_edge_attributes(self.loadEdgeAttributes(day), test_edges.edges) \
                                if self.use_edge_attrs else None
        return test_edges

    def loadEdgeAttributes(self, day):
        try:
            return pickle.load(open(EdgeHandler._edgeAttributesFile(day), 'rb'))
        except Exception:
            return None

    def _prepare_edges(self):
        self.graphs = CleanData.loadDayGraphs()
        self.merged = nx.Graph()

        for day, graph in enumerate(tqdm(self.graphs)):
            self.merged = nx.compose(self.merged, graph)
            if not exists(self._negativeEdgesFile(day)):
                self._save_negativeGi(
                    self._dayGraph_negativeEdges(graph), day
                )
            if self.use_edge_attrs and day <= self.day_limit and not exists(self._edgeAttributesFile(day)) :
                self._save_edge_attributes(day)

    def _dayGraph_negativeEdges(self, graph):

        test_edges = torch.tensor([sorted(edge) for edge in graph.edges()], dtype=torch.long).T
        targets = [1] * test_edges.shape[1]
        indexes = test_edges[0].tolist()

        negative_tests = []
        for v in graph.nodes():
            negatives = [(v, u) for u in graph.nodes()
                         if v < u and not self.merged.has_edge(v, u) and not self.merged.has_edge(u, v)]
            negative_tests.extend(negatives)
            targets.extend([0] * len(negatives))
            indexes.extend([v] * len(negatives))

        test_edges = {
            'edges': torch.cat([test_edges, torch.tensor(negative_tests, dtype=torch.long).T],
                                    dim=1),
            'targets': torch.tensor(targets, dtype=torch.bool),
            'indexes': torch.tensor(indexes, dtype=torch.long)
        }
        return test_edges


    def _save_negativeGi(self, test_edges, day):
        pickle.dump(
            test_edges,
            open(EdgeHandler._negativeEdgesFile(day), 'wb'))

    @staticmethod
    def _negativeEdgesFile(day):
        return f'{TEST_EDGES_PATH}negativeG_{day}'


    def _save_edge_attributes(self, day):

        attributes_functs = [nx.jaccard_coefficient, nx.resource_allocation_index, nx.preferential_attachment]
        attributes = [
            list(nx_funct(self.merged)) for nx_funct in attributes_functs
        ]
        attributes = {
            EdgeHandler.edge_key(v,u): [jaccard, res_alloc, attach]
            for (v, u, jaccard), (_, _, res_alloc), (_, _, attach) in zip(*attributes)
        }
        pickle.dump(
            attributes,
            open(EdgeHandler._edgeAttributesFile(day), 'wb'))

    @staticmethod
    def edge_key(v, u):
        return min(v, u), max(v, u)

    @staticmethod
    def lookup_edge_attributes(attributes, edge_index, edge_attrs_dim=3):

        attributes = [
            attributes.get(EdgeHandler.edge_key(v, u),
                           [0] * edge_attrs_dim)
            for (v, u) in edge_index.T
        ]
        return torch.tensor(attributes, dtype=torch.float32)

    @staticmethod
    def _edgeAttributesFile(day):
        return f'{EDGE_ATTRIBUTES_PATH}edge_attrsG_{day}'
