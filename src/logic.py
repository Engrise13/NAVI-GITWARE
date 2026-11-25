import hashlib
import json
import subprocess
from pathlib import Path

import ollama
import pymupdf
from fastembed import TextEmbedding
from pydantic import BaseModel

EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-base-code"
LLM_MODEL = "qwen3.5:4b"

embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL)


class SecurityReview(BaseModel):
    vulnerable: bool
    reason: str
    file: str
    snippet: str


def get_embedding(text: str) -> list[float]:
    return next(embedding_model.embed([text])).tolist()


def vector_compare(vec1: list[float], vec2: list[float]) -> float:
    return sum(a * b for a, b in zip(vec1, vec2))


def pdf_to_text(path: Path | str) -> str:
    with pymupdf.open(Path(path)) as pdf:
        return "\n".join(page.get_text() for page in pdf)


def update_cache(reports_path: Path | str, cache_file_path: Path | str) -> dict:
    reports_path, cache_file_path = Path(reports_path), Path(cache_file_path)
    if cache_file_path.exists():
        old_cache = json.loads(cache_file_path.read_text(encoding="utf-8"))
    else:
        old_cache = {}

    new_cache = {}

    for pdf in reports_path.glob("*.pdf"):
        file_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
        new_cache[file_hash] = old_cache.get(file_hash) or {
            "report_filename": pdf.name,
            "report_text": (text := pdf_to_text(pdf)),
            "report_embedding": get_embedding(text),
        }

    if old_cache.keys() != new_cache.keys():
        cache_file_path.parent.mkdir(parents=True, exist_ok=True)
        cache_file_path.write_text(
            json.dumps(new_cache, ensure_ascii=False), encoding="utf-8"
        )

    return new_cache


def check_git_diff(diff: str, report: str) -> SecurityReview:
    prompt = (
        "You are a security code reviewer. Check if the provided git diff introduces "
        "or repeats the vulnerability described in the security report.\n\n"
        "Field rules:\n"
        "- vulnerable: true if the diff is vulnerable, false otherwise.\n"
        "- reason: one short sentence in English explaining why, or 'PASS' if safe.\n"
        "- file: vulnerable file path from the diff (without 'b/' prefix), or empty string if safe.\n"
        "- snippet: exact vulnerable line or short snippet from the diff (without leading '+'), or empty string if safe.\n\n"
        f"Security Report:\n{report}\n\n"
        f"Git Diff:\n{diff}"
    )

    response = ollama.generate(
        model=LLM_MODEL,
        prompt=prompt,
        format=SecurityReview.model_json_schema(),
        options={"temperature": 0.1},
        think=False,
    )
    return SecurityReview.model_validate_json(response["response"])


def get_push_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "@{u}..HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    if result.returncode != 0:
        result = subprocess.run(
            ["git", "diff", "origin/main..HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    return result.stdout
