import json
from pathlib import Path

from src.models.product import SourceProduct, TargetProduct


DATA_DIR = Path(__file__).parent.parent.parent / "data"


def load_source_products(category: str) -> list[SourceProduct]:
    path = DATA_DIR / f"source_products_{category}.json"
    return _load_products(path, SourceProduct)


def load_target_pool(category: str) -> list[TargetProduct]:
    path = DATA_DIR / f"target_pool_{category}.json"
    return _load_products(path, TargetProduct)


def _load_products(path: Path, model_class):
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    return [model_class(**item) for item in data]


def save_submission(submissions: list, category: str) -> Path:
    output_dir = Path(__file__).parent.parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / f"submission_{category}.json"

    data = [s.model_dump() for s in submissions]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return path
