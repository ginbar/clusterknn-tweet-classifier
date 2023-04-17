import numpy as np
from ui.word_cloud_ui import WordCloudUI
from dtos.bottom_level_cluster import BottomLevelCluster
from preprocessing.clustering_preprocessor import ClusteringPreprocessor

#TODO Load data
dataset = np.array(['asdhj ahdas sasd', 'asdsa asd', 'asdsadsa sad', 'sdsa asdas xcxc', 'aass', 'as ass assss', 'asdc', 'ass'])

#TODO Apply elbow or silhouette methods 
n_clusters = 4

preprocessor = ClusteringPreprocessor(n_clusters)

preprocessor.fit(dataset)

clusters = preprocessor.create_clusters()

gui = WordCloudUI(clusters=clusters)

gui.show()