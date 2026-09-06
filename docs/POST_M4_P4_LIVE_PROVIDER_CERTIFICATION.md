# Post-M4 P4 Live Grounded-QA Provider Certification

Status: **TASK-144 CANDIDATE — P4 closes only after the gates below pass**  
Certification route: **explicit Vertex AI mode with Application Default Credentials**

## Certification lineage

TASK-142 established the production transport foundation for the repository's
single concrete `GeminiProvider` using `google-genai==2.22.0`. TASK-143 attempted
the separate live certification through the Gemini Developer API/API-key route.
That lineage remains parked as external-provider/authentication evidence; its
failed candidate was not reviewed or published as source.

TASK-144 adds the supported Vertex AI ADC route to the same `GeminiProvider`.
The two exact modes are explicit:

- `developer_api` remains the default and uses the existing API-key behavior;
- `vertex_ai` uses an explicit Google Cloud project and location and delegates
  credential discovery and refresh to the Google SDK/google-auth ADC boundary.

There is no authentication fallback, retry, failover, or reroute between these
modes. A failure in one mode never selects the other.

## Human-owned Vertex prerequisites

Before Runtime executes the live certification, a Human must configure ADC and
the Google Cloud project outside repository code. The Human is also responsible
for the enabled Vertex/Generative AI API, applicable IAM access, billing/quota,
and network availability. Repository code does not read credential files, run
`gcloud`, create credentials, or persist access or refresh tokens.

`.env.example` documents only the optional project and `global` location
configuration. It contains no real account or project identifier, OAuth value,
token, or credential path.

## Preserved provider and M4 boundaries

`LLMProvider`, `LLMResponse`, and `ProviderToolCall` remain the generic transport
contract, and `GeminiProvider` remains the sole concrete Gemini adapter. Both
backend modes preserve the same message translation, manual function declaration,
single async generation request, response mapping, cancellation propagation, and
causal provider-error conversion. Neither mode lists models, retries, executes
tools, parses Product Intelligence output, or selects another provider or model.

The live fixture makes one application call through the unchanged authority
chain:

`TASK-135 -> TASK-133 -> TASK-132 -> GeminiProvider -> Vertex AI ADC`

TASK-132 continues to own the one generic invocation and response syntax. TASK-129
continues to own final `GroundedAnswer` structural validation. Provider
availability, invocation/response-structure failure, and final grounded-answer
failure remain distinct sanitized certification categories.

## What a successful call proves

A passing live fixture proves that this candidate returned an exact TASK-129
`GroundedAnswer` with non-empty canonical context through the unchanged M4 chain.
It does not establish factual truth, semantic quality, exact wording, provider
SLA, model reliability, Product Intelligence truth authority, recommendation, or
approval. The fixture does not persist or print live model output.

## P4 closure gate

P4 becomes **CLOSED**, and P5 Human-Facing Product Intelligence Surface becomes
**CURRENT**, only after canonical TASK-144 Runtime PASS and ChatGPT semantic-review
PASS are both recorded for the same source candidate. Until both gates pass, P4
remains **IN PROGRESS** and P5 has not advanced. TASK-144 implements no P5 behavior.
