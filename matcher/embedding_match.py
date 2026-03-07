"""Embedding-based semantic matching using sentence-transformers + FAISS.

Designed to run on GPU (spylab0). Can also precompute embeddings and save
them for later use on a CPU machine.
"""

from __future__ import annotations

import json
import numpy as np
from pathlib import Path

from .models import Match, Product

# Model choice: multilingual, works well for product names in German/English
DEFAULT_MODEL = "intfloat/multilingual-e5-large-instruct"
BATCH_SIZE = 64


def _build_product_text(p: Product) -> str:
    """Build a rich text representation for embedding."""
    parts = []
    if p.brand:
        parts.append(p.brand)
    parts.append(p.name)
    if p.ean:
        parts.append(f"EAN:{p.ean}")
    # Add key specs
    for key in ["Modellnummer", "Modellbezeichnung", "model", "Model", "Typ"]:
        if key in p.specifications:
            parts.append(p.specifications[key])
    return " ".join(parts)


def compute_embeddings(
    products: list[Product],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = BATCH_SIZE,
    prefix: str = "query: ",
) -> np.ndarray:
    """Compute embeddings for a list of products using sentence-transformers.

    Returns numpy array of shape (len(products), embedding_dim).
    """
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    texts = [prefix + _build_product_text(p) for p in products]
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)
    return np.array(embeddings, dtype=np.float32)


def build_faiss_index(embeddings: np.ndarray):
    """Build a FAISS index for fast nearest-neighbor search."""
    import faiss

    dim = embeddings.shape[1]
    # Use inner product since embeddings are normalized (= cosine similarity)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def match_by_embedding(
    sources: list[Product],
    targets: list[Product],
    model_name: str = DEFAULT_MODEL,
    top_k: int = 5,
    threshold: float = 0.85,
    source_embeddings: np.ndarray | None = None,
    target_embeddings: np.ndarray | None = None,
) -> list[Match]:
    """Match source products to targets using embedding similarity.

    If pre-computed embeddings are provided, uses those instead of recomputing.
    """
    import faiss

    if source_embeddings is None:
        print("Computing source embeddings...")
        source_embeddings = compute_embeddings(sources, model_name, prefix="query: ")
    if target_embeddings is None:
        print("Computing target embeddings...")
        target_embeddings = compute_embeddings(targets, model_name, prefix="query: ")

    print(f"Building FAISS index over {len(targets)} targets...")
    index = build_faiss_index(target_embeddings)

    print(f"Searching for top-{top_k} matches per source product...")
    scores, indices = index.search(source_embeddings, top_k)

    matches = []
    for i, source in enumerate(sources):
        for j in range(top_k):
            idx = indices[i][j]
            score = float(scores[i][j])
            if idx < 0 or score < threshold:
                continue
            target = targets[idx]
            matches.append(Match(
                source_reference=source.reference,
                target_reference=target.reference,
                target_name=target.name,
                target_retailer=target.retailer or "",
                target_url=target.url or "",
                target_price=target.price_eur,
                confidence=score,
                method="embedding",
            ))

    return matches


def save_embeddings(embeddings: np.ndarray, products: list[Product], path: Path):
    """Save embeddings and product references for later use."""
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(path.with_suffix(".npy")), embeddings)
    refs = [p.reference for p in products]
    with open(path.with_suffix(".refs.json"), "w") as f:
        json.dump(refs, f)
    print(f"Saved {len(products)} embeddings to {path}")


def load_embeddings(path: Path) -> tuple[np.ndarray, list[str]]:
    """Load pre-computed embeddings and their product references."""
    embeddings = np.load(str(path.with_suffix(".npy")))
    with open(path.with_suffix(".refs.json")) as f:
        refs = json.load(f)
    return embeddings, refs


# --- CLI for running on GPU server ---

def precompute_cli():
    """CLI to precompute embeddings on a GPU server."""
    import argparse

    parser = argparse.ArgumentParser(description="Precompute product embeddings on GPU")
    parser.add_argument("--input", type=Path, required=True, help="Products JSON file")
    parser.add_argument("--output", type=Path, required=True, help="Output path (without extension)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--prefix", type=str, default="query: ")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)
    products = [Product.from_dict(d) for d in data]
    print(f"Loaded {len(products)} products from {args.input}")

    embeddings = compute_embeddings(products, args.model, prefix=args.prefix)
    save_embeddings(embeddings, products, args.output)


if __name__ == "__main__":
    precompute_cli()
