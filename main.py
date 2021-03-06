import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from functools import partial
from contextlib import ExitStack
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from skfuzzy.cluster import cmeans, cmeans_predict


raw_datasets = ["models/" + name for name in ["pima.tr", "pima.te"]]
datasets = ["models/" + name for name in ["training.csv", "test.csv"]]


def preprocess_datasets() -> None:
    with ExitStack() as stack:
        raws = [stack.enter_context(open(file, 'r')) for file in raw_datasets]
        processed = [stack.enter_context(open(file, 'w')) for file in datasets]
        for raw, proc in zip(raws, processed):
            dataset = raw.readlines()
            dataset = [re.sub(r"^ +", "", row) for row in dataset]
            dataset = [re.sub(r" +", ",", row) for row in dataset]
            proc.writelines(dataset)


def import_datasets() -> tuple:
    cols = pd.read_csv(datasets[0], nrows=1).columns
    return tuple(pd.read_csv(file, usecols=cols[:-1]) for file in datasets)


def read_diagnoses() -> tuple:
    cols = pd.read_csv(datasets[0], nrows=1).columns
    diagnoses = tuple()
    for dataset in datasets:
        read = pd.read_csv(dataset, usecols=cols[-1:])
        diagnoses += (np.array([*map(lambda x: 1 if x == "Yes" else 0,
                                     read.values)]),)
    return diagnoses


def perform_crisp_clustering(training: np.array, test: np.array,
                             clusters: int) -> tuple:
    kmeans = KMeans(clusters)
    kmeans.fit(training)
    return kmeans.labels_, kmeans.predict(test)


def perform_fuzzy_clustering(training: np.array, test: np.array,
                             clusters: int, m: int) -> tuple:
    center, train_labels = cmeans(training.T, clusters, m, 0.005, 1000)[0:2]
    test_labels = cmeans_predict(test.T, center, m, 0.005, 1000)[0]
    return *(np.argmax(label, 0) for label in [train_labels, test_labels]),
    # *((label[1] > 0.2).astype(int) for label in [train_labels, test_labels]),
 

def perform_pca(training: np.array, test: np.array) -> list:
    pca = PCA(2)
    pca_datasets = [training, test]
    for pos, dataset in enumerate(pca_datasets):
        pca.fit(dataset)
        pca_datasets[pos] = pca.transform(dataset)
    return pca_datasets

# np.apply_along_axis(np.bincount, axis=1, arr= test_array,
#                                           minlength = np.max(test_array) +1)
# np.bincount(np.argsort(center, 0)).argmax()

def plot_datasets(pca_datasets: list, diagnoses: tuple,
                  clusters: int, title: str) -> None:
    for idx, (dataset, diagnose) in enumerate(zip(pca_datasets, diagnoses)):
        for j in range(clusters):
            plt.plot(dataset[diagnose == j, 0],
                     dataset[diagnose == j, 1], 'o', markersize=3,
                     label='series ' + str(j))
        plt.title(title + (" training set" if not idx else " test set"))
        plt.legend()
        plt.show()


def test_algorithms(training: np.array, test: np.array, pca_datasets: list,
                    clusters: int, diagnoses: tuple) -> None:
    algorithms = [partial(perform_fuzzy_clustering, training,
                          test, clusters, m) for m in range(2, 5)]
    algorithms += [partial(perform_crisp_clustering, training, test, clusters)]
    for algorithm in algorithms:
        result = algorithm()
        print([sum(res) for res in [x == y for x, y in
                                    zip(result, diagnoses)]])
        title = "Clusters: {}, Function: {}".format(clusters,
                                                    algorithm.func.__name__)
        if "fuzzy" in algorithm.func.__name__:
            title += ", m: {}".format(algorithm.args[-1])
        plot_datasets(pca_datasets, result, clusters, title)


def main():
    preprocess_datasets()
    training_set, test_set = import_datasets()
    training, test = training_set.values, test_set.values
    diagnoses = read_diagnoses()
    pca_datasets = perform_pca(training, test)
    plot_datasets(pca_datasets, diagnoses, 2, "Default diagnoses")
    for clusters in range(2, 4):
        test_algorithms(training, test, pca_datasets, clusters, diagnoses)


if __name__ == "__main__":
    main()
