import argparse
from io.dataset_reader import DatasetReader
from ui.word_cloud_ui import WordCloudUI
from preprocessing.clustering_preprocessor import ClusteringPreprocessor
from preprocessing.text_transforms import TextTransforms
from dtos.preprocessing_results import PreprocessingResults
from io.preprocessing import save_preprocessing_results


argument_parser = argparse.ArgumentParser("Rotulate dataset")
argument_parser.add_argument("hashtag", help="Hashtag used to create the dataset", type=str, required=True)
args = argument_parser.parse_args()

reader = DatasetReader(args.hashtag, 'train')
transforms = TextTransforms()

lemmatized_dataset =  reader.get_lemmatized_tweets()
tokenized_dataset = transforms.vectorize(lemmatized_dataset)

preprocessor = ClusteringPreprocessor()
preprocessor.fit(lemmatized_dataset)

clusters = preprocessor.create_clusters()

gui = WordCloudUI(clusters=clusters)

gui.show()

centroids = [c.centroid for c in clusters]
clustering_mask = preprocessor.get_clustering_mask()
assigned_labels = gui.get_assigned_labels()

preprocessing_results = PreprocessingResults(centroids, clustering_mask, assigned_labels)

save_preprocessing_results(args.hashtag, preprocessing_results)