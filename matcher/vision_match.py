"""Vision-based product matching using CLIP.

Downloads product images and matches by visual similarity.
Designed to run on GPU (spylab0).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import numpy as np

from .models import Match, Product

DEFAULT_MODEL = "openai/clip-vit-large-patch14-336"
BATCH_SIZE = 32


async def download_images(
    products: list[Product],
    output_dir: Path,
    max_concurrent: int = 10,
) -> dict[str, Path]:
    """Download product images. Returns {reference: image_path}."""
    output_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max_concurrent)
    result: dict[str, Path] = {}

    async def _download_one(p: Product):
        if not p.image_url:
            return
        ext = p.image_url.split(".")[-1].split("?")[0][:4]
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        path = output_dir / f"{p.reference}.{ext}"
        if path.exists():
            result[p.reference] = path
            return
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(p.image_url, timeout=10, follow_redirects=True)
                    if resp.status_code == 200:
                        path.write_bytes(resp.content)
                        result[p.reference] = path
            except (httpx.HTTPError, httpx.TimeoutException):
                pass

    await asyncio.gather(*[_download_one(p) for p in products])
    return result


def compute_image_embeddings(
    image_paths: list[Path],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = BATCH_SIZE,
) -> np.ndarray:
    """Compute CLIP image embeddings."""
    from transformers import CLIPProcessor, CLIPModel
    from PIL import Image
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(model_name).to(device)
    processor = CLIPProcessor.from_pretrained(model_name)

    all_embeddings = []
    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i + batch_size]
        images = []
        for p in batch_paths:
            try:
                img = Image.open(p).convert("RGB")
                images.append(img)
            except Exception:
                # Create a blank image as fallback
                images.append(Image.new("RGB", (224, 224)))

        inputs = processor(images=images, return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            outputs = model.get_image_features(**inputs)
            # Normalize
            embeddings = outputs / outputs.norm(dim=-1, keepdim=True)
            all_embeddings.append(embeddings.cpu().numpy())

    return np.vstack(all_embeddings).astype(np.float32)


def match_by_vision(
    sources: list[Product],
    targets: list[Product],
    source_image_dir: Path,
    target_image_dir: Path,
    model_name: str = DEFAULT_MODEL,
    top_k: int = 5,
    threshold: float = 0.88,
    source_embeddings: np.ndarray | None = None,
    target_embeddings: np.ndarray | None = None,
) -> list[Match]:
    """Match products by visual similarity using CLIP embeddings."""
    import faiss

    # Collect products that have images
    source_images = []
    source_products = []
    for s in sources:
        img_path = _find_image(s.reference, source_image_dir)
        if img_path:
            source_images.append(img_path)
            source_products.append(s)

    target_images = []
    target_products = []
    for t in targets:
        img_path = _find_image(t.reference, target_image_dir)
        if img_path:
            target_images.append(img_path)
            target_products.append(t)

    if not source_images or not target_images:
        print("No images available for vision matching")
        return []

    print(f"Vision matching: {len(source_images)} source images, {len(target_images)} target images")

    if source_embeddings is None:
        print("Computing source image embeddings...")
        source_embeddings = compute_image_embeddings(source_images, model_name)
    if target_embeddings is None:
        print("Computing target image embeddings...")
        target_embeddings = compute_image_embeddings(target_images, model_name)

    # Build FAISS index
    index = faiss.IndexFlatIP(target_embeddings.shape[1])
    index.add(target_embeddings)

    scores, indices = index.search(source_embeddings, top_k)

    matches = []
    for i, source in enumerate(source_products):
        for j in range(top_k):
            idx = indices[i][j]
            score = float(scores[i][j])
            if idx < 0 or score < threshold:
                continue
            target = target_products[idx]
            matches.append(Match(
                source_reference=source.reference,
                target_reference=target.reference,
                target_name=target.name,
                target_retailer=target.retailer or "",
                target_url=target.url or "",
                target_price=target.price_eur,
                confidence=score,
                method="vision",
            ))

    return matches


def _find_image(reference: str, image_dir: Path) -> Path | None:
    """Find an image file for a product reference."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = image_dir / f"{reference}.{ext}"
        if path.exists():
            return path
    return None


def save_image_embeddings(embeddings: np.ndarray, references: list[str], path: Path):
    """Save image embeddings for later use."""
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(path.with_suffix(".npy")), embeddings)
    with open(path.with_suffix(".refs.json"), "w") as f:
        json.dump(references, f)


def precompute_cli():
    """CLI for precomputing image embeddings on GPU."""
    import argparse

    parser = argparse.ArgumentParser(description="Precompute CLIP image embeddings on GPU")
    parser.add_argument("--image-dir", type=Path, required=True, help="Directory with product images")
    parser.add_argument("--output", type=Path, required=True, help="Output path (without extension)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    args = parser.parse_args()

    image_paths = sorted(args.image_dir.glob("*.*"))
    image_paths = [p for p in image_paths if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    print(f"Found {len(image_paths)} images in {args.image_dir}")

    references = [p.stem for p in image_paths]
    embeddings = compute_image_embeddings(image_paths, args.model)
    save_image_embeddings(embeddings, references, args.output)
    print(f"Saved {len(references)} image embeddings to {args.output}")


if __name__ == "__main__":
    precompute_cli()
