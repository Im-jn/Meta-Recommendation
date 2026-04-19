import json
import os
import sys
from pathlib import Path


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    contract_path = repo_root / "contracts" / "metarec-openapi.json"

    # Make app import deterministic in CI environments without secrets.
    os.environ.setdefault("LLM_API_KEY", "dummy-key")
    os.environ.setdefault("OPENAI_API_KEY", "dummy-key")

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from main import app  # noqa: WPS433

    contract_path.parent.mkdir(parents=True, exist_ok=True)
    with contract_path.open("w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"OpenAPI contract exported to: {contract_path}")


if __name__ == "__main__":
    main()
