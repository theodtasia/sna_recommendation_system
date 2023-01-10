import networkx as nx
import torch
from torch_geometric.data import Data
from torch_geometric.utils import negative_sampling

from preprocessing.clean_datasets import *
from preprocessing.clean_datasets import clean_data_path, Graph_
from preprocessing.features_extraction import FeaturesExtraction
from preprocessing.edge_handler import EdgeHandler
from recommendation_task.utils import numOfGraphs, dotdict

INIT_DAY = 0
# change to True to include centrality based feats
EXTRACT_TOPOL_ATTRS = False
# feature extractor configuration (for ex, scale arg value) haven't changed
# since last run
SAME_ATTRS_CONFIG = True


class Dataset:

    def __init__(self, device):
        self.device = device

        # will be incremented to 0 when the first graph (Graph_{INIT_DAY}) is loaded
        self.day = INIT_DAY - 1
        self.numOfGraphs = numOfGraphs()

        self.featureExtractor = FeaturesExtraction(extract_topological_attr=EXTRACT_TOPOL_ATTRS,
                                                   load_from_file= SAME_ATTRS_CONFIG)
        self.edgeHandler = EdgeHandler()

        self.attr_dim = self.featureExtractor.attr_dim

        self.graph = Data(edge_index=torch.empty((2,0), dtype=torch.long, device=device))

    def has_next(self):
        # checked before loading graph
        # when day = -1, Graph_0 and Graph_1 will be loaded (therefore 2)
        return self.day + 2 < self.numOfGraphs


    def get_dataset(self):
        """
        :return:
            train_edges : positive (existing) edges for message passing and scoring (undirected tensor (2,M))
            test_edges : next day's edges (positive and negative) for testing.
                dotdict {edges : tensor (2, N),
                        attributes : (N, edge attributes dim)
                        targets, indexes : tensors (N, 1)}
        """
        self._set_day()
        train_edges = self._to_undirected(self.graph.edge_index)
        train_edges = dotdict({'edges':train_edges,
                              'attributes': self.edgeHandler.loadEdgeAttributes(self.day)})

        test_edges = self.edgeHandler.loadTestEdges(self.day + 1)
        return train_edges, test_edges


    def _set_day(self):
        self.day += 1
        day_edges = self._load_day_graph_edges(self.day)
        self.graph.edge_index = torch.cat([self.graph.edge_index,
                                           day_edges], dim=1)
        self.max_node = torch.max(self.graph.edge_index).item()
        self._update_node_attributes()


    def _update_node_attributes(self):
        # load feature vector x for the first day, or update daily if centrality based feats are included
        # if not, do nothing (x stays as it is every day)
        if self.day == INIT_DAY or EXTRACT_TOPOL_ATTRS:
            # dataframe
            x = self.featureExtractor.loadDayAttributesDataframe(self.day)
            x = x.values.tolist()
            x = torch.tensor(x, device=self.device, dtype=torch.float32)
            self.graph.x = x


    def _load_day_graph_edges(self, day):
        """
        :param day: to load Graph_{day}
        :return: edges : directed edge_index tensor
        + load current day edge attributes         """
        edges = pickle.load(open(f'{clean_data_path}{Graph_}{day}', 'rb')).edges()
        edges = torch.tensor(list(edges), dtype=torch.long, device=self.device).T
        self.edge_attributes = self.edgeHandler.loadEdgeAttributes(self.day)
        return edges


    def _to_undirected(self, edge_index):
        return torch.cat([edge_index, edge_index[[1, 0]]], dim=1)



    def negative_sampling(self):
        neg_edge_index = negative_sampling(
            edge_index=self.graph.edge_index,               # positive edges
            num_nodes=self.max_node,                        # max node index in graph
            num_neg_samples=self.graph.edge_index.size(1))  # num of negatives = num of positives
        neg_edge_index = self._to_undirected(neg_edge_index)
        return dotdict({
            'edges' : neg_edge_index,
            'attributes' : EdgeHandler.lookup_edge_attributes(self.edge_attributes, neg_edge_index)
        })




    """
    def _get_edge_attributes(self, graph, edges):
        if isinstance(edges, torch.Tensor):
            edges = edges.T.tolist()

        attributes_functs = [nx.jaccard_coefficient, nx.resource_allocation_index, nx.preferential_attachment]
        attributes = [
            list(nx_funct(graph, edges)) for nx_funct in attributes_functs
        ]
        attributes = [
            [jaccard, res_alloc, attach]
            for (v, u, jaccard), (_, _, res_alloc), (_, _, attach) in zip(*attributes)
        ]
        
        return attributes

    def edge_key(self, v, u):
        return min(v, u), max(v, u)


    def lookup_edge_attributes(self, attributes, edge_index):
        attributes = [
            attributes.get(EdgeHandler.edge_key(v, u),
                           [0] * EDGE_ATTRIBUTES_DIM)
            for (v, u) in edge_index.T
        ]
        return torch.tensor(attributes, dtype=torch.float32)
    """




