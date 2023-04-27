import numpy as np
from numpy import ndarray
from infra.utils import create_file_path, create_dataset_folder



def save_results(hashtag: str, results: ndarray) -> None:
    
    create_dataset_folder(hashtag)
    
    np.save(create_file_path(hashtag, None, 'result'), results)