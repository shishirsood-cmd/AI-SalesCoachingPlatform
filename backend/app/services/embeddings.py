from functools import lru_cache

from fastembed import TextEmbedding

from app.models.knowledge import EMBEDDING_DIM

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def _get_model() -> TextEmbedding:
    # Runs locally (ONNX), no API key required. This keeps RAG ingestion working
    # without external dependencies; swap for Voyage AI or another hosted
    # embeddings API later if quality/scale needs outgrow a local model.
    return TextEmbedding(model_name=MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = [vec.tolist() for vec in model.embed(texts)]
    for vec in vectors:
        assert len(vec) == EMBEDDING_DIM
    return vectors
