from pathlib import Path

import ollama
import pymupdf as fitz
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
    embedding = next(embedding_model.embed([text]))
    return embedding.tolist()


def vector_compare(vec1: list[float], vec2: list[float]) -> float:
    return sum(a * b for a, b in zip(vec1, vec2))


def pdf_to_text(path: Path | str) -> str:
    with fitz.open(Path(path)) as pdf:
        return "\n".join(page.get_text() for page in pdf)


def check_git_diff(diff: str, report: str) -> str:
    prompt = (
        "You are a security code reviewer. Check if the provided git diff introduces "
        "or repeats the vulnerability described in the security report.\n\n"
        "Respond ONLY with valid JSON matching this schema:\n"
        "{\n"
        '  "vulnerable": boolean,\n'
        '  "reason": "one short sentence in English explaining why, or PASS if safe",\n'
        '  "file": "path to the vulnerable file from the diff (without b/ prefix), or empty string if safe",\n'
        '  "snippet": "exact vulnerable line or short code snippet from the diff (without leading +), or empty string if safe"\n'
        "}\n"
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
    return response["response"]
