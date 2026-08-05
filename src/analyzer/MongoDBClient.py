from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_shared_mongo_client():
    base_dir = Path(__file__).resolve().parent
    candidate_paths = [
        base_dir / "scheduler" / "MongoDBClient.py",
        base_dir.parent / "scheduler" / "MongoDBClient.py",
    ]

    for candidate in candidate_paths:
        if candidate.is_file():
            spec = spec_from_file_location("shared_mongodb_client", candidate)
            if spec and spec.loader:
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.MongoDBClient

    raise ModuleNotFoundError("No module named 'MongoDBClient'")


MongoDBClient = _load_shared_mongo_client()