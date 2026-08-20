# TASK-056 — M11.2C.2 Pinned Local MiniMax-M3 Exact Provider-Input Counter

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API PRECALL TOKEN AUTHORITY
MILESTONE: M11.2C.2
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 867cb5cdb730639db93a1f184f065dbb97230cd0
TARGET_BRANCH: ai/task-056
```

## Purpose

Implement the first production trusted-local full-provider-input counter for MiniMax-M3, using only a pre-provisioned local tokenizer asset bundle and the pinned official MiniMax-M3 chat-template semantics.

TASK-056 must make it possible for M11.2C.1 to obtain exact local full-input evidence without any token-count network call. It does NOT authorize a real provider call, tokenizer download, or M11.3 execution.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
BLUEPRINT_PATH: .ai/context/TASK-056-M11.2C2-PINNED-LOCAL-MINIMAX-M3-INPUT-COUNTER-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 4888eafc926463761a0d4680f69a5b8156c9cd8b
REVIEW_055_PATH: .ai/reviews/REVIEW-055.md
REVIEW_055_BLOB_SHA: 9dab73286e7e83ef9d7d70c2a23cad2b12e5c3c8
```

Merged source anchors:

```text
src/aios_bridge/provider_input_budget.py                  0a6f9b5c5201215ef654b068aea215f370cc4593
src/aios_bridge/paid_api_brain_escape.py                  8d536dd8dff7f7fb562666d6427a661a9e0dd15e
src/aios_bridge/external_brain/prompt.py                  5e43eec724c8efebc47a2f1dc741e5cf8b616601
src/aios_bridge/external_brain/providers/minimax.py       f907deeccf5d24ec80d4de58f7769330126f3624
requirements.txt                                           272f324e5fad503979a797a4f0cb89987d201ecf
```

## Official MiniMax Source Pin

```text
SOURCE_REPOSITORY: MiniMaxAI/MiniMax-M3
SOURCE_REVISION: 3a41b311ffa5719cef48fed3974ccf2cc03733ea
CHAT_TEMPLATE_PATH: chat_template.jinja
PROVIDER_ID: minimax
MODEL_ID: MiniMax-M3
```

Mutable upstream `main` is forbidden as runtime authority.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/context/TASK-056-M11.2C2-PINNED-LOCAL-MINIMAX-M3-INPUT-COUNTER-BLUEPRINT.md","blob_sha":"4888eafc926463761a0d4680f69a5b8156c9cd8b"},{"path":".ai/reviews/REVIEW-055.md","blob_sha":"9dab73286e7e83ef9d7d70c2a23cad2b12e5c3c8"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/minimax_m3_input_counter.py","src/aios_bridge/provider_input_budget.py","requirements.txt","tests/aios_bridge/test_minimax_m3_input_counter.py"]

Bridge-generated `.ai/results/RESULT-056.md` is publication output only.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, no paid Executor.

## Child Executor Role Lock

The Bridge E4-spawned Codex process is the bounded implementation Executor child, NOT the visible `aios-worker` operator UI.

```text
visible Codex + aios-worker skill = operator UI
Bridge E4 spawned Codex process  = bounded implementation Executor
```

The child MUST implement this task now. It MUST NOT invoke the worker adapter again and MUST NOT commit, push, publish, merge, download tokenizer/model assets, access provider credentials, or make any network/provider call.

## Exact Writable Files

Create/modify exactly:

```text
src/aios_bridge/minimax_m3_input_counter.py
src/aios_bridge/provider_input_budget.py
requirements.txt
tests/aios_bridge/test_minimax_m3_input_counter.py
```

No other implementation/test file is writable.

## Production Counter Contract

Implement exact concrete type:

```text
MiniMaxM3LocalProviderInputCounter
```

Properties:

```text
provider_id == "minimax"
model_id == "MiniMax-M3"
is_exact is True
counter_id includes pinned revision + actual tokenizer SHA-256
```

It must satisfy TASK-055 `ProviderInputTokenCounter` and return exact `ProviderInputCountEvidence`.

## Local Asset Contract

Constructor accepts a local asset directory only. Expected files:

```text
tokenizer.json
asset-manifest.json
```

Manifest fields must be exact:

```text
schema_version
source_repository
source_revision
source_path
tokenizer_sha256
```

Required values:

```text
schema_version = 1
source_repository = MiniMaxAI/MiniMax-M3
source_revision = 3a41b311ffa5719cef48fed3974ccf2cc03733ea
source_path = tokenizer.json
tokenizer_sha256 = exact lowercase SHA-256 of actual local tokenizer bytes
```

Requirements:
- regular files only;
- reject symlinks;
- reject missing/extra manifest fields;
- reject malformed digest;
- tokenizer actual digest must equal manifest digest;
- size ceiling before parse;
- read-only local use;
- no credentials/environment auth;
- no network/download path.

## Tokenizer Engine

Pin:

```text
tokenizers==0.23.1
```

in `requirements.txt`.

Use the local fast tokenizer file only. Real constructor must fail closed if the library is unavailable.

No `transformers`, `huggingface_hub`, model weights, remote code, or provider API token endpoint is required or authorized.

## Exact Message / Template Contract

Counter MUST start from existing:

```python
render_messages(model_request)
```

and accept only exact shape:

```text
message count: 2
message[0].role: system
message[0].content: exact str
message[1].role: user
message[1].content: exact str
```

All other shapes fail closed before tokenization.

Specialize the official MiniMax-M3 template at the pinned revision for this exact shape. It must include:

```text
default MiniMax root-system/model identity
thinking instructions with default/adaptive semantics
AIOS OpenAI system message in developer slot
AIOS user message in user slot
add_generation_prompt=True ai prefix
```

Pinned token strings:

```text
NS_TOKEN: ]<]minimax[>[
BOD_TOKEN: ]~!b[
BOS_TOKEN: ]~b]
EOS_TOKEN: [e~[
THINK_BEGIN_TOKEN: <mm:think>
THINK_END_TOKEN: </mm:think>
```

Exact whitespace/newlines must follow the locked blueprint.

## Exact Count

After rendering the complete provider prompt:

```text
encode(rendered_prompt, add_special_tokens=False)
counted_input_tokens = len(encoding.ids)
```

Return evidence bound to `fingerprint_model_request(model_request)`.

No prompt/raw tokenizer content may be persisted in evidence or output.

## Trusted Registration

Modify TASK-055 trusted-local registry so production trusts exactly:

```text
MiniMaxM3LocalProviderInputCounter
```

No other type.

Exact-type semantics remain mandatory:

```text
subclass: reject
wrapper: reject
Protocol-only arbitrary counter: reject
caller-injected backend/callable: forbidden production authority
```

The trusted class must own local asset validation and tokenizer load internally.

## Network / Spend Prohibition

Production counter and tests must not:

```text
call MiniMax
call a token-count endpoint
call Hugging Face
use requests/httpx/aiohttp/urllib network clients
open sockets
download assets
read API keys/Authorization headers
initialize provider transports
```

No real paid API call is authorized.

## Required Tests

Implement the complete test matrix from the blueprint, including at least:

```text
manifest/source/revision/path exactness
actual tokenizer digest binding
symlink/missing/oversize rejection
missing local tokenizer engine fail closed
exact two-message role/content shape
pinned root-system + thinking + developer + user + generation framing
add_special_tokens=False
encoded ID length is evidence count
request fingerprint exact
counter ID binds revision + tokenizer digest
production registry accepts exact class
subclass remains rejected
network/credential/provider surfaces absent
no real provider call
```

Tests may monkeypatch a PRIVATE module-local tokenizer loader only. No public caller-supplied tokenizer/backend injection surface is allowed.

## Targeted Test

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_minimax_m3_input_counter.py tests/aios_bridge/test_paid_api_brain_escape.py -q
```

Executor runs targeted tests. Bridge publication owns full repository tests.

## Explicit Out of Scope

```text
TOKENIZER_ASSET_DOWNLOAD: NO
TOKENIZER_ASSET_PROVISIONING_COMMAND: NO
REAL_MINIMAX_CALL: NO
REAL_PAID_API_CALL: NO
M11.3_OPERATIONAL_PROOF: NOT_STARTED
PROVIDER_CHANGE: NO
GATEWAY_CHANGE: NO
PROMPT_RENDERER_CHANGE: NO
PAID_GRANT_CONTRACT_CHANGE: NO
GRANT_STORE_CHANGE: NO
M10_CHANGE: NO
EXECUTOR_API: FORBIDDEN
H_SERIES: DEFERRED
```

## Completion Boundary

After code + targeted tests, leave only authorized worktree changes and exit normally for Bridge publication.

After publication:

```text
STOP
NEXT: Review TASK-056
```

Do not provision assets or begin M11.3 automatically.