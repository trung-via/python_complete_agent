# P6.1c Retrieval Stress Benchmark

Status: TASK-169 revision 2 implementation candidate. Runtime verification,
semantic review, publication, and Brain/Human interpretation remain downstream
gates.

## Published source and fixed Human cases

P6.1c reuses the published TASK-168 P6.1b fixture tree in place. Its descriptor
binds the exact bytes of
`tests/fixtures/p6_1b_real_evidence/benchmark.json` at SHA-256
`ad742b54f827441b42f9162dfccd34f0241adbbbcb0991e4d692614e54835e08`.
Normal offline verification checks that descriptor, its capture bundle, and all
six referenced source packs against their published digests. Nothing is copied
into the P6.1c fixture root, and no live or external evidence is imported.

Before any retrieval result was inspected, the Human fixed exactly six cases,
their order, queries, questions, and two relevant variant labels per case. Every
case uses `limit=3`. Retrieval hits, lexical overlap, evidence contents, and
measured metrics cannot derive or change those labels.

## Offline authority replay

Each complete run reconstructs the exact six TASK-168 profiles through the
published authority chain only:

- TASK-138 intakes each of the three exact committed cohort roots once.
- TASK-139/TASK-140 explicitly approve and admit the same three two-member
  families.
- TASK-141/TASK-116 explicitly review and admit each canonical family member as
  the same ordered singleton variant used by TASK-168.
- TASK-120 reloads a fresh disposable SQLite catalog, and TASK-121 projects each
  singleton profile from its exact one-to-one source pack.
- TASK-164 receives all six `RetrievalBenchmarkCase` values in one call with
  `limit=3`. TASK-122 remains reachable only through TASK-164.

The benchmark contains no local token matching, shadow retrieval, semantic
matching, alternate profile format, provider/model call, browser, network,
clock, random value, retry, or product-truth reconciliation. Repeated execution
uses fresh SQLite files and proves value-equal reports while both fixture trees
remain byte-identical.

## Exact lexical stress results

The committed TASK-164 snapshot is:

| Case | Fixed retrieval query | TP | FP | FN | Precision | Recall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `p6-1c-001` | `bình nước thép không gỉ giữ nóng lạnh` | 0 | 0 | 2 | 0/1 | 0/1 |
| `p6-1c-002` | `bình lớn có lọc trà mang đi làm` | 0 | 0 | 2 | 0/1 | 0/1 |
| `p6-1c-003` | `keyboard gaming k550 nhiều màu` | 0 | 0 | 2 | 0/1 | 0/1 |
| `p6-1c-004` | `bàn phím chơi game có đèn` | 2 | 0 | 0 | 1/1 | 1/1 |
| `p6-1c-005` | `mouse bluetooth sạc lại cho laptop` | 0 | 0 | 2 | 0/1 | 0/1 |
| `p6-1c-006` | `chuột dùng cho máy tính bảng android` | 0 | 0 | 2 | 0/1 | 0/1 |
| **Micro aggregate** | | **2** | **0** | **10** | **1/1** | **1/6** |

The zero-hit cases and weak micro recall are valid empirical evidence, not
benchmark failures. Micro precision is 1/1 because the only two returned hits
are relevant; it does not offset the ten false negatives or imply semantic
adequacy.

## Interpretation boundary and P6.2 gate

This snapshot measures only current TASK-122 lexical behavior under deliberately
more distant Human paraphrase and attribute wording. It does not evaluate
semantic entailment, grounded-answer prose, citation fidelity, factual
correctness, marketplace quality, identity correctness, business relevance, or
product truth. TASK-122 remains the sole lexical retrieval authority and
TASK-164 the sole quality evaluator.

There is no score threshold, automatic pass/fail quality gate, or automatic
roadmap decision. P6.2 remains GATED / DECISION PENDING until TASK-169 receives
Runtime PASS, ChatGPT semantic PASS, and publication, followed by separate
Brain/Human review of this measured evidence. Neither weak results nor strong
results automatically authorize semantic/vector retrieval or declare lexical
retrieval sufficient. P6.3-P6.6 remain deferred.
