import pickle

EMBEDDINGS_FILE = "embeddings/embeddings.pkl"

with open(EMBEDDINGS_FILE, "rb") as f:
    data = pickle.load(f)

names = data["names"]
from collections import Counter
print(Counter(names))
