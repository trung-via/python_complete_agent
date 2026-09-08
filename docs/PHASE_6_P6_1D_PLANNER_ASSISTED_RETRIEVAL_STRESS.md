# P6.1d Planner-Assisted Retrieval Stress Benchmark

Status: P6.1d is CURRENT with TASK-170 as its planner-assisted closure candidate.
Runtime verification, semantic review, publication, and separate Brain/Human
interpretation remain downstream gates.

## Immutable source and authority composition

P6.1d binds the exact published TASK-169 descriptor at
`tests/fixtures/p6_1c_retrieval_stress/benchmark.json`, SHA-256
`1710f775860e3d715e535795aecef45d460cd58bf2a923628f1e1a26a0034c5f`.
That descriptor transitively binds the published TASK-168 benchmark descriptor,
capture bundle, and six source manifests. P6.1d copies or mutates none of those
fixture trees.

Each complete offline run reconstructs the same three families and six ordered
singleton profiles through TASK-138, TASK-139/TASK-140,
TASK-141/TASK-116, TASK-120, and TASK-121. It then passes each exact TASK-169
`retrieval_query` to TASK-134 exactly once as the planner question. After all six
planned queries exist, one TASK-164 call evaluates all six cases at `limit=3`;
TASK-122 is reachable for scoring only through TASK-164. No local planner,
retriever, matcher, label transformation, provider, model, browser, network, or
external state participates.

## Exact planner-assisted results

The committed empirical snapshot is:

| Case | Exact TASK-169 stress intent / TASK-134 input | Exact TASK-134 selected query | TP | FP | FN | Precision | Recall |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `p6-1d-001` | `bình nước thép không gỉ giữ nóng lạnh` | `không gỉ giữ nóng lạnh` | 2 | 0 | 0 | 1/1 | 1/1 |
| `p6-1d-002` | `bình lớn có lọc trà mang đi làm` | `có lọc trà mang đi làm` | 2 | 0 | 0 | 1/1 | 1/1 |
| `p6-1d-003` | `keyboard gaming k550 nhiều màu` | `gaming k550 nhiều màu` | 2 | 0 | 0 | 1/1 | 1/1 |
| `p6-1d-004` | `bàn phím chơi game có đèn` | `bàn phím chơi game có đèn` | 2 | 0 | 0 | 1/1 | 1/1 |
| `p6-1d-005` | `mouse bluetooth sạc lại cho laptop` | `bluetooth sạc lại cho laptop` | 2 | 0 | 0 | 1/1 | 1/1 |
| `p6-1d-006` | `chuột dùng cho máy tính bảng android` | `cho máy tính bảng android` | 2 | 0 | 0 | 1/1 | 1/1 |
| **Micro aggregate** | | | **12** | **0** | **0** | **1/1** | **1/1** |

All true-positive rows preserve the two TASK-169 Human labels in their published
order. There are no false-positive or false-negative variant IDs in this
snapshot.

## Comparison and decision boundary

P6.1c measures the six fixed stress intents directly through raw TASK-122 and
records 2 TP, 0 FP, 10 FN, micro precision 1/1, and micro recall 1/6. P6.1d
measures the existing production planning composition TASK-134 -> TASK-122 over
the same immutable corpus and Human labels, recording 12 TP, 0 FP, 0 FN, and
micro precision and recall of 1/1.

The improved measurement does not prove semantic understanding. TASK-134 selects
a bounded contiguous lexical span by probing TASK-122, so a shorter selected
span can recover lexical hits without embeddings, translation, semantic
entailment, or new product-truth authority.

There is no metric threshold, automatic architecture decision, or automatic
quality pass/fail gate. Weak or strong planner-assisted results are valid measured
evidence. P6.2 remains GATED / DECISION PENDING until TASK-170 receives Runtime
PASS, semantic PASS, and publication, followed by separate Brain/Human review of
the published P6.1c and P6.1d evidence. P6.3-P6.6 remain deferred and
unimplemented.
