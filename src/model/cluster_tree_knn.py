import numpy as np
from numpy import ndarray
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.neighbors import KNeighborsClassifier
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from scipy.cluster.hierarchy import dendrogram, linkage, ClusterNode
from scipy.spatial import distance
from scipy.spatial import KDTree
import scipy

from dtos.bottom_level_cluster import BottomLevelCluster
from dtos.hyper_level_cluster import HyperLevelCluster 
from dtos.upper_level_cluster import UpperLevelCluster 



class ClusterTreeKNN(BaseEstimator, ClassifierMixin):
    """
    KNN over a cluster based tree.
    
    Parameters
    ----------
    initial_hyperlevel_threshold : float, default=0.5
        Tthreshold for the radius of each cluster at the hypernode level.
    
    sigma_nearest_nodes : int, default=5
        Number of nodes be searched in the upper level at prediction.

    References
    ----------
    Oliveira, E., Roatti, H., Nogueira, M., Basoni, H. e Ciarelli M. (2015). Using the Cluster-based
    Tree Structure of k-Nearest Neighbor to Reduce the Effort Required to Classify Unlabeled Large
    Datasets.

    Zhang, B. e Srihari, S. N. (2004). Fast k-Nearest Neighbor Classification Using Cluster-Based
    Trees. IEEE Trans. Pattern Anal. Mach. Intell., 26(4): 525-528.
    """

    def __init__(
        self,
        clusters_masks,
        centroids,
        n_neighbors:int=5, 
        metric:callable=distance.euclidean,
        initial_hyperlevel_threshold:float=5,
        sigma_nearest_nodes:int=5,
    ):
        super(ClusterTreeKNN, self).__init__()

        # Parameters
        self.n_neighbors = n_neighbors
        self.metric = metric
        self.initial_hyperlevel_threshold = initial_hyperlevel_threshold
        self.sigma_nearest_nodes = sigma_nearest_nodes

        self.clusters_masks = clusters_masks
        self.centroids = centroids

        self._max_iter = 100

        self.Blevel = None
        self.Hlevel = None
        self.Plevel = None



    def fit(
        self, 
        X:ndarray,
        y:ndarray, 
    ) -> None:
        """
        Fit the clustering k-nearest neighbors classifier from the training dataset. 
        It assumes that just valid clusters are passed as arguments.
        
        Parameters
        ----------
        X : ndarray
            Training data.

        y : ndarray
            Target values.
        
        Returns
        ----------
            self : The fitted clustering k-nearest neighbors classifier.
        """

        # Step 1. 
        # Initialize the bottom level of the cluster tree
        # with all template documents that are labeled
        # during the process described in Section 4.1.
        # These templates constitute a single level B;
        remaining_clusters_labels = [label for label in np.unique(self.clusters_masks)]
        
        self.Blevel = [BottomLevelCluster(
                i, 
                X[label == self.clusters_masks], 
                y[label == self.clusters_masks], 
                self.centroids[i]
            ) for i, label in enumerate(remaining_clusters_labels)]
        
        self.Hlevel = []
        self.Plevel = []

        X_length = X.shape[0]

        iter = 0

        while len(remaining_clusters_labels) > 0:
            
            # Step 2. 
            # ∀Sl ∈ Ω, extract one of the most dissimilar
            # samples, for instance d1 , and compute the lo-
            # cal properties of each sample d1 = d: γ(d),
            # ψ(d) and ℓ(d). Then, rank all clusters Sl in
            # descending order of ℓ(.);
            
            remaining_clusters_mask = np.isin(self.clusters_masks, remaining_clusters_labels)

            _clusters_masks = self.clusters_masks[remaining_clusters_mask]
            _X = X[remaining_clusters_mask]
            _y = y[remaining_clusters_mask]

            X_length = _X.shape[0]
            
            most_dissimilars = np.array(
                [self.Blevel[i].data[np.linalg.norm(self.Blevel[i].data - self.centroids[i], axis=1).argmax()] 
                for i, _ in enumerate(remaining_clusters_labels)])

            assert(most_dissimilars.shape[0] > 0)
            assert(_X.shape[0] > 0)

            most_dissimilars_indexes = [np.where((_X == m).all(axis=1))[0] for m in most_dissimilars]
            most_dissimilars_indexes = np.array([dist[0] if len(dist) > 0 else 0 for dist in most_dissimilars_indexes])
            
            dissimilarities = np.array([np.linalg.norm(i - j) for i in _X for j in _X]).reshape((X_length, X_length))

            if np.unique(_y).shape[0] > 1:
                
                gamma_d = np.array([dissimilarities[i][_y[i] != _y].min() for i in most_dissimilars_indexes])
                psi_d = [_X[(_y[i] == _y) & (dissimilarities[i] < gamma_d[k])] for k, i in enumerate(most_dissimilars_indexes)]
                psi_d_labels = [_y[(_y[i] == _y) & (dissimilarities[i] < gamma_d[k])] for k, i in enumerate(most_dissimilars_indexes)]
                lambda_d = np.array([len(psi) for psi in psi_d])
                new_hyper_node_index = lambda_d.argmax()
                
                # Step 3. 
                # Take the sample d1 with the biggest ℓ(.) as
                # a hypernode, and let all samples of ψ(d1 ) be
                # nodes at the bottom level of the tree, B . Then,
                # remove d1 and all samples in ψ(d1 ) from the
                # original dataset, and set up a link between d1
                # and each pattern of ψ(d1 ) in B ;

                new_hyper_node = HyperLevelCluster(
                    len(self.Hlevel), 
                    most_dissimilars[new_hyper_node_index], 
                    _y[most_dissimilars_indexes[new_hyper_node_index]],
                    gamma_d[new_hyper_node_index]
                )

                self.Hlevel.append(new_hyper_node)

                new_bottol_level_data = psi_d[new_hyper_node_index]
                new_bottom_level_labels = psi_d_labels[new_hyper_node_index]

                new_bottom_level_node = BottomLevelCluster(
                    len(self.Blevel), 
                    new_bottol_level_data,
                    new_bottom_level_labels, 
                    None
                )
                
                cluster_to_be_removed = _clusters_masks[most_dissimilars_indexes[new_hyper_node_index]]
                
                remaining_clusters_labels.remove(cluster_to_be_removed)
                new_hyper_node.add_child(new_bottom_level_node)
                
                self.Blevel.append(new_bottom_level_node)
            else:
                new_hyper_node = HyperLevelCluster(
                    len(self.Hlevel), 
                    most_dissimilars[0], 
                    _y[0],
                    gamma_d[0]
                )

                new_bottom_level_node = BottomLevelCluster(len(self.Blevel), _X, _y, None)

                self.Hlevel.append(new_hyper_node)
                new_hyper_node.add_child(new_bottom_level_node)

                self.Blevel.append(new_bottom_level_node)
                
                remaining_clusters_labels.pop()

            # Step 4. 
            # Repeat Step 2 and Step 3 until the Ω set be-
            # comes empty. At this point, the cluster tree is
            # configured with a hyperlevel, H , and a bottom level, B ;
            iter = iter + 1
            assert(iter < self._max_iter)
        
        assert(len(self.Hlevel) > 0)

        # Step 5. 
        # Select a threshold η and cluster all templates
        # in H so that the radius of each cluster is less
        # than or equal to η. All cluster centers form
        # another level of the cluster tree, P ;
        hyperlevel_threshold = self.initial_hyperlevel_threshold

        self.Plevel = self.Hlevel
        iter = 0

        while len(self.Plevel) != 1:
            hyperlevel_data = np.array([cluster.data for cluster in self.Plevel]) 
            new_P_level = None
            
            if hyperlevel_data.shape[0] == 2:
                upper_node = UpperLevelCluster(len(self.Plevel), hyperlevel_data)
                
                for child in self.Plevel:
                    upper_node.add_child(child)

                new_P_level = [upper_node]
            else:
                hyperlevel_data_size = hyperlevel_data.shape[0]
                min_samples = int(0.2 * hyperlevel_data_size)
                
                if min_samples < 3:
                    min_samples = 3
                
                hyperlevel_clustering = DBSCAN(eps=self.initial_hyperlevel_threshold, min_samples=min_samples)
                hyperlevel_clustering.fit(hyperlevel_data)
                
                if np.unique(hyperlevel_clustering.labels_).shape[0] > 1 and hyperlevel_clustering.core_sample_indices_.shape[0] < hyperlevel_data.shape[0]:
                    new_P_level = []
                    core_indeces = hyperlevel_clustering.core_sample_indices_
                    
                    for i, centr_ind in enumerate(core_indeces):
                        upper_node = UpperLevelCluster(i, hyperlevel_data[centr_ind])
                        
                        for child in self.Plevel:
                            upper_node.add_child(child)
                        
                        new_P_level.append(upper_node)
                else:
                    upper_node = UpperLevelCluster(len(self.Plevel), hyperlevel_data)
                    
                    for child in self.Plevel:
                        upper_node.add_child(child)

                    new_P_level = [upper_node]

            self.Plevel = new_P_level
            hyperlevel_threshold = hyperlevel_threshold + 0.5
            # Step 6. 
            # Increase the threshold η and repeat Step 5 for
            # all nodes at the level P until a single node is
            # left in the resulting level.

            iter = iter + 1
            assert(iter < self._max_iter)

        return self



    def predict(self, sample: ndarray) -> ndarray:
        if sample.shape[0] > 1:
            return np.array([self._predict(_sample) for _sample in sample])
        return self._predict(sample)



    def _predict(self, sample: ndarray) -> ndarray:
        """
        Predict the class labels for the provided data.
        
        Parameters
        ----------
        sample : ndarray
            Test samples.

        Returns
        ----------
            ndarray : Class labels for each data sample.
        """
        
        # Step 1. 
        # First, we compute the dissimilarity between x
        # and each node at the top level of the cluster
        # tree and choose the ς nearest nodes as a node
        # set Lx ;
        distances = np.array([np.linalg.norm(cluster.data - sample) for cluster in self.Plevel])
        indexes = distances.argsort()[:self.sigma_nearest_nodes]
        
        Lx = np.take(self.Plevel, indexes)
        
        assert(Lx.shape[0] > 0)

        iter = 0

        while not any(isinstance(cluster, HyperLevelCluster) for cluster in Lx):
            
            # Step 2. 
            # Compute the dissimilarity between x and
            # each subnode linked to the nodes in Lx , and
            # again choose the ς nearest nodes, which are
            # used to update the node set Lx ;
            subnodes = np.array([cluster.children for cluster in Lx]).flatten()
            distances = np.array([np.linalg.norm(cluster.data - sample) for cluster in subnodes])
            indexes = distances.argsort()[:self.sigma_nearest_nodes]

            Lx = np.take(subnodes, indexes)

            # Step 3. 
            # Repeat Step 2 until reaching the hyperlevel
            # in the tree. When the searching stops at the
            # hyperlevel, Lx consists of ς hypernodes;
            iter = iter + 1
            assert(iter < self._max_iter)


        # Step 4. 
        # Search Lx for the hypernode:
        # Lh = {Y |d(y, x) ≤ γ(d), y ∈ Lx }. 
        #TODO implement conditions
        # Lh_hyper_nodes = [node for node in Lx]
        Lh_hyper_nodes = [node for node in Lx if np.linalg.norm(node.data - sample) <= node.gamma_d]
        
        if len(Lh_hyper_nodes) == 0:
            Lh_hyper_nodes = Lx

        # If all nodes in Lh have the same class label, then this class is as-
        # sociated with x and the classification process
        # stops; otherwise, go to Step 5;
        Lh_hyper_node_labels = np.unique(np.array([c.label for c in Lh_hyper_nodes]))
        
        if not len(Lh_hyper_node_labels) > 1:
            return Lh_hyper_node_labels[0]
        else:
            # Step 5. 
            # Compute the dissimilarity between x and
            # every subnode linked to the nodes in Lx , and
            # choose the k nearest samples. Then, take a
            # majority voting among the k nearest samples
            # to determine the class label for x.
            bottom_level_data = []
            bottom_level_label = []

            for node in Lh_hyper_nodes:
                for child in node.children:
                    bottom_level_data.append(child.data)
                    bottom_level_label.append(child.labels)

            bottom_level_data = np.concatenate(bottom_level_data)
            bottom_level_label = np.concatenate(bottom_level_label)
            
            n_neighbors = self.n_neighbors

            if bottom_level_data.shape[0] < n_neighbors:
                n_neighbors = bottom_level_data.shape[0]

            knn = KNeighborsClassifier(n_neighbors=n_neighbors)
            
            knn.fit(bottom_level_data, bottom_level_label)

            return knn.predict([sample])[0]
            