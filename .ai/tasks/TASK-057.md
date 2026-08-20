# TASK-057 — M11.2C.2 Pinned Local MiniMax-M3 Asset Renderer + Exact Input Counter Reissue

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API PRECALL TOKEN AUTHORITY
MILESTONE: M11.2C.2
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 867cb5cdb730639db93a1f184f065dbb97230cd0
TARGET_BRANCH: ai/task-057
```

## Recovery Lock

TASK-056 is a closed no-op execution attempt.

```text
TASK_056_RETRY: FORBIDDEN
TASK_056_REACTIVATION: FORBIDDEN
TASK_056_PUBLICATION_AUTHORITY: NONE
TASK_057: SOLE NEW IMPLEMENTATION AUTHORITY FOR M11.2C.2
```

Do not inspect or reuse local TASK-056 worktree state as implementation authority. Start TASK-057 from the exact baseline main above.

## Purpose

Implement the first production trusted-local full-provider-input counter for MiniMax-M3 without requiring the Executor to reconstruct upstream Jinja bytes.

The counter must load BOTH pinned local runtime assets:

```text
chat_template.jinja
tokenizer.json
```

validate them against an exact local manifest, render the validated local official template in a sandbox with existing AIOS `render_messages()` output, tokenize the complete rendered prompt locally, and return exact TASK-055 provider-input evidence.

No asset download, token-count endpoint, MiniMax call, or paid spend is authorized.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
REVIEW_055_PATH: .ai/reviews/REVIEW-055.md
REVIEW_055_BLOB_SHA: 9dab73286e7e83ef9d7d70c2a23cad2b12e5c3c8
BLUEPRINT_PATH: .ai/context/TASK-057-M11.2C2-PINNED-LOCAL-MINIMAX-M3-ASSET-RENDERER-REISSUE-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 9405f9823b613dd976f8bff6ffe4e9a7bdc85878
```

Historical no-op anchors only:

```text
TASK_056_PATH: .ai/tasks/TASK-056.md
TASK_056_BLOB_SHA: c14991ade6d981b06aae55908ae9951bf1d14f2b
TASK_056_BLUEPRINT_BLOB_SHA: 4888eafc926463761a0d4680f69a5b8156c9cd8b
```

Merged source anchors:

```text
src/aios_bridge/provider_input_budget.py                  0a6f9b5c5201215ef654b068aea215f370cc4593
src/aios_bridge/paid_api_brain_escape.py                  8d536dd8dff7f7fb562666d6427a661a9e0dd15e
src/aios_bridge/external_brain/prompt.py                  5e43eec724c8efebc47a2f1dc741e5cf8b616601
src/aios_bridge/external_brain/providers/minimax.py       f907deeccf5d24ec80d4de58f7769330126f3624
requirements.txt                                           272f324e5fad503979a797a4f0cb89987d201ecf
```

## Official Source Pin

```text
SOURCE_REPOSITORY: MiniMaxAI/MiniMax-M3
SOURCE_REVISION: 3a41b311ffa5719cef48fed3974ccf2cc03733ea
CHAT_TEMPLATE_PATH: chat_template.jinja
TOKENIZER_PATH: tokenizer.json
PROVIDER_ID: minimax
MODEL_ID: MiniMax-M3
```

Mutable upstream `main` is forbidden as runtime authority.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/context/TASK-057-M11.2C2-PINNED-LOCAL-MINIMAX-M3-ASSET-RENDERER-REISSUE-BLUEPRINT.md","blob_sha":"9405f9823b613dd976f8bff6ffe4e9a7bdc85878"},{"path":".ai/reviews/REVIEW-055.md","blob_sha":"9dab73286e7e83ef9d7d70c2a23cad2b12e5c3c8"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/minimax_m3_input_counter.py","src/aios_bridge/provider_input_budget.py","requirements.txt","tests/aios_bridge/test_minimax_m3_input_counter.py"]

Bridge-generated `.ai/results/RESULT-057.md` is publication output only.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, fallback, second executor, or paid Executor.

## Child Executor Role Lock

The Bridge E4-spawned Codex process is the bounded implementation Executor child, NOT the visible `aios-worker` operator UI.

```text
visible Codex + aios-worker skill = operator UI
Bridge E4 spawned Codex process  = bounded implementation Executor
```

The child MUST implement now. It MUST NOT invoke the worker adapter again and MUST NOT commit, push, publish, merge, download upstream assets, install packages from network, access credentials, or make any provider/network call.

## Exact Writable Files

Create/modify exactly:

```text
src/aios_bridge/minimax_m3_input_counter.py
src/aios_bridge/provider_input_budget.py
requirements.txt
tests/aios_bridge/test_minimax_m3_input_counter.py
```

No other implementation/test file is writable.

## Dependencies

Add exact pins:

```text
tokenizers==0.23.1
Jinja2==3.1.6
```

Lazy-import runtime engines. Do not require E4 to download/install them. Missing real runtime dependency must fail closed at real counter construction.

No `transformers`, `huggingface_hub`, remote code, or model weights.

## Asset Bundle Contract

Constructor accepts one local asset directory containing exactly the required files:

```text
asset-manifest.json
chat_template.jinja
tokenizer.json
```

Manifest semantic field set exactly:

```text
schema_version
source_repository
source_revision
chat_template_path
chat_template_sha256
tokenizer_path
tokenizer_sha256
```

Required constants:

```text
schema_version = 1
source_repository = MiniMaxAI/MiniMax-M3
source_revision = 3a41b311ffa5719cef48fed3974ccf2cc03733ea
chat_template_path = chat_template.jinja
tokenizer_path = tokenizer.json
```

Both digests are exact lowercase SHA-256 and must equal actual local bytes.

Reject before parse/render:
- missing/extra manifest keys;
- malformed digest;
- missing file;
- symlink/non-regular file;
- path escape;
- oversized template/tokenizer;
- digest mismatch;
- template invalid UTF-8.

No file mutation or auto-repair.

## Counter Contract

Create exact type:

```text
MiniMaxM3LocalProviderInputCounter
```

Properties:

```text
provider_id == minimax
model_id == MiniMax-M3
is_exact is True
counter_id binds source revision + chat_template_sha256 + tokenizer_sha256
```

No public constructor injection of tokenizer/template backend/callables.

## Exact Render Chain

`count_request()` MUST:

```text
1 require exact ModelRequest
2 call existing external_brain.prompt.render_messages(model_request)
3 require exact two-message dictionaries:
     system:str
     user:str
   with exact key set {role,content}
4 render validated LOCAL chat_template.jinja in sandbox
5 context exactly:
     messages=<two messages>
     tools=None
     add_generation_prompt=True
   and DO NOT explicitly pass thinking_mode
6 tokenize rendered prompt using validated LOCAL tokenizer.json
7 tokenizer.encode(..., add_special_tokens=False)
8 counted_input_tokens = len(encoding.ids)
9 return ProviderInputCountEvidence bound to fingerprint_model_request(model_request)
```

The counter must never persist rendered prompt, template bytes, tokenizer bytes, credentials, or authorization data.

## Jinja Sandbox

Use sandboxed Jinja execution with strict undefined behavior and no filesystem loader.

Compile only the already-read validated template string.

Expose no filesystem/network/provider/application globals. A bounded `raise_exception` helper may be supplied because the official template references it for invalid branches.

## Trusted Registration

Modify TASK-055 trust registry so production trusts exactly:

```text
MiniMaxM3LocalProviderInputCounter
```

Preserve exact-type semantics:

```text
exact class: allowed
subclass: rejected
wrapper: rejected
Protocol-only object: rejected
```

No additional trusted types.

## Required Tests

Implement the blueprint matrix, including at minimum:

```text
EXACT_PROVIDER_MODEL_IDS
IS_EXACT_TRUE
COUNTER_ID_BINDS_REVISION_TEMPLATE_SHA_TOKENIZER_SHA
MANIFEST_EXACT_FIELDS
SOURCE_REVISION_PATHS_EXACT
MANIFEST_TEMPLATE_TOKENIZER_SYMLINKS_REJECTED
MISSING_FILES_REJECTED
OVERSIZE_REJECTED_BEFORE_PARSE
TEMPLATE_AND_TOKENIZER_DIGEST_MISMATCH_REJECTED
INVALID_TEMPLATE_UTF8_REJECTED
MISSING_JINJA2_FAILS_CLOSED
MISSING_TOKENIZERS_FAILS_CLOSED
RENDER_MESSAGES_CALLED
EXACT_TWO_MESSAGE_SYSTEM_USER_STRING_SHAPE
EXTRA_MESSAGE_WRONG_ROLE_NON_STRING_REJECTED_BEFORE_TEMPLATE
SANDBOX_AND_STRICT_UNDEFINED
TOOLS_NONE
ADD_GENERATION_PROMPT_TRUE
THINKING_MODE_NOT_PASSED
TOKENIZER_ADD_SPECIAL_TOKENS_FALSE
COUNT_EQUALS_ENCODING_IDS_LENGTH
EVIDENCE_FINGERPRINT_EXACT
EVIDENCE_NO_PROMPT_OR_ASSET_BYTES
TRUST_REGISTRY_EXACT_CLASS_ONLY
SUBCLASS_REJECTED
NO_NETWORK_OR_CREDENTIAL_SURFACE
NO_REAL_PROVIDER_CALL
FULL_REPO_TESTS_PASS
```

Use temporary synthetic local assets and private module-loader monkeypatches only. No upstream/template download during tests. Do not copy the official upstream template into repository fixtures.

## Targeted Test

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_minimax_m3_input_counter.py tests/aios_bridge/test_paid_api_brain_escape.py -q
```

Executor runs targeted tests. Bridge publication owns full repository tests.

## M11.3 Boundary

TASK-057 MUST NOT make a real MiniMax call.

Later M11.3 must provision real pinned assets out-of-band and compare on the one authorized provider call:

```text
LOCAL_PRECALL_COUNT == PROVIDER_REPORTED_INPUT_TOKENS
```

Mismatch means M11.3 FAIL; consumed grant remains consumed; retry forbidden.

## Explicit Out of Scope

```text
TASK_056_RETRY: FORBIDDEN
TOKENIZER_TEMPLATE_DOWNLOAD: NO
ASSET_PROVISIONING_COMMAND: NO
REAL_MINIMAX_CALL: NO
REAL_PAID_API_CALL: NO
TOKEN_COUNT_ENDPOINT: NO
M11.3: NOT_STARTED
PROVIDER_CHANGE: NO
GATEWAY_CHANGE: NO
PROMPT_RENDERER_CHANGE: NO
GRANT_CHANGE: NO
GRANT_STORE_CHANGE: NO
M10_CHANGE: NO
EXECUTOR_API: FORBIDDEN
H_SERIES: DEFERRED
```

## Completion Boundary

After implementation + targeted tests, leave only authorized dirty paths and exit normally for Bridge publication.

After publication:

```text
STOP
NEXT: Review TASK-057
```
