# NAVI GITWARE

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Ollama-Local_LLM-000000?style=flat-square&logo=ollama&logoColor=white" alt="Ollama" />
  <img src="https://img.shields.io/badge/FastEmbed-Code_Embeddings-FF6F00?style=flat-square" alt="FastEmbed" />
  <img src="https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic" />
  <img src="https://img.shields.io/badge/Rich-CLI-00D26A?style=flat-square" alt="Rich" />
  <img src="https://img.shields.io/badge/OWASP-Top_10_2025-B71C1C?style=flat-square&logo=owasp&logoColor=white" alt="OWASP Top 10 2025" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License" />
</p>

Automated local `pre-push` security gate powered by semantic code embeddings and local LLMs via Ollama. Ships **out of the box with a pre-packaged OWASP Top 10:2025 PDF knowledge base**, intercepts outgoing `git push` diffs, retrieves the closest matching vulnerability advisory via SHA-256 cached vector search, enforces strict structured output via Pydantic v2, and blocks vulnerable commits with syntax-highlighted diagnostics in the terminal using `rich`.

![NAVI Gitware Showcase](showcase.png)

---

## Architecture

```text
[Git Push Diff (@{u}..HEAD)]    [reports/*.pdf (OWASP 2025)]
              │                             │
              ▼                             ▼
       get_push_diff()               update_cache()        --> Extracts PDF text (PyMuPDF) & SHA-256 caches vectors
              │                             │
              ▼                             │
       get_embedding()                      │              --> Encodes diff via jina-embeddings-v2-base-code
              │                             │
              └──────────────┬──────────────┘
                             ▼
                      vector_compare()                     --> Dot-product similarity search for best report match
                             │
                             ▼
                      check_git_diff()                     --> Ollama inference (qwen3.5:4b, temp=0.1, JSON schema)
                             │
                             ▼
                  SecurityReview (Pydantic)                --> Validates boolean verdict, reason, file & snippet
                             │
                             ▼
                     Rich Terminal Gate                    --> Allows push (exit 0) or blocks with red Panel (exit 1)
```

---

## Built-in Knowledge Base (OWASP Top 10:2025)

The `reports/` directory comes **pre-populated out of the box** with 10 structured security advisories covering the **OWASP Top 10:2025** standard. Each PDF contains diff detection patterns, CWE mappings, vulnerable block conditions, and secure remediation code:

| ID | Bundled Report File | Covered Vulnerability Domain |
| :--- | :--- | :--- |
| **A01** | `A01_2025_Broken_Access_Control_and_SSRF.pdf` | IDOR, missing ownership/role checks, Server-Side Request Forgery |
| **A02** | `A02_2025_Security_Misconfiguration.pdf` | Production `DEBUG=True`, wildcard CORS, exposed admin panels/buckets |
| **A03** | `A03_2025_Software_Supply_Chain_Failures.pdf` | Unpinned dependencies, mutable `:latest` images, unverified remote scripts |
| **A04** | `A04_2025_Cryptographic_Failures.pdf` | Hardcoded secrets/keys, MD5/SHA-1 password hashing, `verify=False` TLS |
| **A05** | `A05_2025_Injection_SQLi_XSS_CMDi.pdf` | String-formatted SQLi, `subprocess(..., shell=True)`, unescaped HTML/XSS |
| **A06** | `A06_2025_Insecure_Design.pdf` | Missing rate limits, client-trusted pricing/logic, unbounded resource allocation |
| **A07** | `A07_2025_Authentication_Failures.pdf` | Unverified JWT signatures, insecure session cookies (`HttpOnly`/`Secure`) |
| **A08** | `A08_2025_Software_Data_Integrity_Failures.pdf` | Unsafe `pickle.loads()` / `yaml.load()`, missing webhook HMAC/SRI checks |
| **A09** | `A09_2025_Logging_and_Alerting_Failures.pdf` | Credential/token leakage in logs, swallowed auth errors, CRLF log injection |
| **A10** | `A10_2025_Mishandling_Exceptional_Conditions.pdf` | Fail-open `except` blocks in auth checks, non-atomic state rollbacks |

*(You can drop any custom company security advisories or CVE `.pdf` files into `reports/` at any time—they are automatically indexed on the next push.)*

---

## Security Pipeline & Models

Every `git push` triggers a four-stage deterministic verification flow:

| Component | Implementation | Role |
| :--- | :--- | :--- |
| **Diff Extractor** | `git diff @{u}..HEAD` (fallback: `origin/main..HEAD`) | Captures outgoing changes prior to remote transfer |
| **Report Cache** | `SHA-256` + `PyMuPDF` + `reports_cache.json` | Incremental indexing of `reports/*.pdf` without re-embedding unchanged files |
| **Semantic Retriever** | `jinaai/jina-embeddings-v2-base-code` (`FastEmbed`) | Maps code diffs and vulnerability reports into a shared vector space |
| **Code Auditor** | `qwen3.5:4b` (`Ollama`, `temperature=0.1`, `think=False`) | Evaluates whether the diff introduces or repeats the matched vulnerability |

---

## Installation

### 1. Python Dependencies

```bash
pip install ollama pymupdf fastembed pydantic rich
```

### 2. Local LLM Setup

Ensure [Ollama](https://ollama.com/) is installed and pull the audit model:

```bash
ollama pull qwen3.5:4b
```

*(Note: `jinaai/jina-embeddings-v2-base-code` is downloaded automatically by `fastembed` on first execution.)*

---

## Execution & Git Hook Setup

### 1. Wire as a `pre-push` Hook
Since the OWASP Top 10:2025 reports are already included in `reports/`, no initial report setup is required. Link or copy `pre_push.py` into `.git/hooks/pre-push` and make it executable:

```bash
cat << 'EOF' > .git/hooks/pre-push
#!/usr/bin/env bash
python3 path/to/hooks/pre_push.py
EOF
chmod +x .git/hooks/pre-push
```

### 2. Adding Custom Advisories (Optional)
To extend the gate with internal security rules or specific CVE reports, drop additional `.pdf` files into `reports/`:

```bash
cp /path/to/custom_security_advisory.pdf reports/
```

### 3. Gate Behavior
- **Empty diff / missing `reports/`:** Prints status notice and exits with `0` (push proceeds).
- **Safe diff (`vulnerable: false`):** Prints `PASSED! pushing...` and exits with `0`.
- **Vulnerability detected (`vulnerable: true`):** Renders a `PUSH BLOCKED` `rich.panel.Panel` containing the matched report filename, root cause, target file, and `monokai` syntax-highlighted offending code snippet, then exits with `1`.

---

## Validation Contract (Pydantic v2)

LLM responses are constrained via `format=SecurityReview.model_json_schema()` (`temperature=0.1`) and validated against `SecurityReview` to return strictly:

```json
{
  "vulnerable": true,
  "reason": "string (one short sentence explaining why, or 'PASS' if safe)",
  "file": "string (vulnerable file path without 'b/' prefix, or empty string if safe)",
  "snippet": "string (exact vulnerable line/snippet without leading '+', or empty string if safe)"
}
```

---

## Project Structure

```text
├── src/
│   ├── pre_push.py                                      # Git pre-push entrypoint, pipeline orchestration, Rich UI
│   └── logic.py                                         # Git diff subprocess, PDF parser, SHA-256 cache, Ollama audit
├── reports/                                             # Built-in OWASP Top 10:2025 PDF knowledge base + custom PDFs
│   ├── A01_2025_Broken_Access_Control_and_SSRF.pdf
│   ├── A02_2025_Security_Misconfiguration.pdf
│   ├── A03_2025_Software_Supply_Chain_Failures.pdf
│   ├── A04_2025_Cryptographic_Failures.pdf
│   ├── A05_2025_Injection_SQLi_XSS_CMDi.pdf
│   ├── A06_2025_Insecure_Design.pdf
│   ├── A07_2025_Authentication_Failures.pdf
│   ├── A08_2025_Software_Data_Integrity_Failures.pdf
│   ├── A09_2025_Logging_and_Alerting_Failures.pdf
│   └── A10_2025_Mishandling_Exceptional_Conditions.pdf
└── reports_cache.json                                   # Auto-generated SHA-256 indexed text & embedding cache
```

---

## License

MIT