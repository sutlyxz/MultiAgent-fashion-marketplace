# Project Data Schema

## 1. Overview

This document describes the data exchanged through the shared `ProjectState` contract across Antigravity Native Skills (`.agents/skills/*/SKILL.md`) and the Master Orchestration Workflow (`.agents/skills/master-workflow/SKILL.md`). It records the canonical top-level field names, data types, and initial values, distinguishing verified structures from recommended conventions.

- `docs/data_schema.md` and `docs/agent_contract.md` serve as the authoritative sources of truth for state keys, types, and inter-agent data contracts (historically prototyped as a Python TypedDict in `models/state.py`).
- `docs/agent_contract.md` defines agent responsibilities and input/output ownership boundaries.
- `workflow.md` and `.agents/skills/master-workflow/SKILL.md` govern execution order, read QA/security outcomes and findings to route work, increment `iteration_count` on failures, and enforce human-in-the-loop gates.

The Data Schema defines data structure; the Agent Contract defines agent responsibilities and I/O boundaries. This document does not add fields or implement marketplace behavior. The schema provides a formal contract for agent reasoning and workflow validation.

## Contents

- [ProjectState Definition](#2-projectstate-definition)
- [Detailed Field Schemas](#3-detailed-field-schemas)
- [Agent Input and Output Mapping](#4-agent-input-and-output-mapping)
- [Status and Enum Definitions](#5-status-and-enum-definitions)
- [Data Validation Rules](#6-data-validation-rules)
- [Example ProjectState](#7-example-projectstate)
- [Known Gaps and Recommendations](#8-known-gaps-and-recommendations)

## 2. ProjectState Definition

All 21 keys are required by the current `TypedDict` (none are declared optional). `create_initial_state` populates every key. This is a static typing contract, not runtime validation: Python does not automatically reject missing keys, wrong value types, or malformed nested data.

Each field below is grouped by its role in the workflow. **Initial value** comes from `create_initial_state` unless marked caller-supplied. Writers/readers describe the Agent Contract and current workflow; they are not access controls.

### Project input and planning

| Field (type) | Purpose | Writer / readers | Default | Validation |
|---|---|---|---|---|
| `project_goal` (`str`) | High-level project objective. | Caller / PM, Architect | Caller-supplied | **Implemented:** type annotation only. **Recommended:** non-empty. |
| `project_description` (`str`) | Additional context for the objective. | Caller / PM, Architect | Caller-supplied | **Implemented:** type annotation only. **Recommended:** non-empty. |
| `requirements` (`dict`) | Requirements produced during project planning. | PM / Architect, Frontend, Backend, QA, Security | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |
| `user_stories` (`list`) | User stories from planning. | PM / Architect, Frontend, Backend, QA | `[]` | **Implemented:** top-level type only. Item shape is **Recommended**, not enforced. |
| `mvp_scope` (`list`) | Agreed initial product scope. | PM / Architect | `[]` | **Implemented:** top-level type only. Item type is **Recommended**, not enforced. |

**Examples**

```json
{
    "project_goal": "Plan a secondhand clothing marketplace",
    "project_description": "Buyers and sellers list pre-owned clothing.",
    "requirements": {"functional": [], "non_functional": []},
    "user_stories": [
        {"id": "US-001", "story": "As a buyer, I can browse listings.", "acceptance_criteria": []}
    ],
    "mvp_scope": ["Browse clothing listings"]
}
```

### Architecture and implementation

| Field (type) | Purpose | Writer / readers | Default | Validation |
|---|---|---|---|---|
| `architecture` (`dict`) | System architecture proposal. | Architect / Frontend, Backend, Security | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |
| `technology_stack` (`dict`) | Selected or proposed technologies. | Architect / Frontend, Backend | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |
| `database_schema` (`dict`) | Proposed persistent data model. | Architect / Backend, Security | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |
| `api_specification` (`dict`) | Proposed API contracts. | Architect / Frontend, Backend, QA, Security | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |
| `frontend_code` (`dict`) | Frontend design/code artifact container. | Frontend / Frontend, QA, Security | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |
| `backend_code` (`dict`) | Backend design/code artifact container. | Backend / Backend, QA, Security | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |

**Examples**

```json
{
    "architecture": {"components": [], "decisions": []},
    "technology_stack": {"frontend": "React", "backend": "Python"},
    "database_schema": {"entities": []},
    "api_specification": {"endpoints": []},
    "frontend_code": {"components": []},
    "backend_code": {"modules": []}
}
```

### QA and security

| Field (type) | Purpose | Writer / readers | Default | Validation |
|---|---|---|---|---|
| `test_cases` (`list`) | QA test case descriptions. | QA / QA; other readers are not specified. | `[]` | **Implemented:** top-level type only. Item shape is **Recommended**, not enforced. |
| `test_results` (`dict`) | QA execution results. | QA / Frontend, Backend; QA may use its own results. | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |
| `bugs` (`list`) | QA defects assigned to frontend or backend. | QA / Frontend, Backend; workflow reads the last entry on QA `FAIL`. | `[]` | **Documented:** keys are `id`, `agent`, `description`, `severity`; `agent` is `frontend` or `backend`. **Implemented:** exact `backend` routes to Backend; other values route to Frontend. No shape validation. |
| `qa_status` (`str`) | QA outcome consumed by workflow routing. | QA / workflow | `""` | **Implemented:** exact `"PASS"` continues to Security; exact `"FAIL"` routes to remediation and increments iteration count; any other value ends the graph. No enum validator. |
| `security_findings` (`list`) | Security issues assigned to frontend, backend, or both. | Security / Frontend, Backend; workflow reads the last entry on Security `FAIL`. | `[]` | **Documented:** keys are `id`, `agent`, `description`, `severity`; `agent` is `frontend`, `backend`, or `both`. **Implemented:** `both` routes through Frontend then Backend. No shape validation. |
| `security_status` (`str`) | Security outcome consumed by workflow routing. | Security / workflow | `""` | **Implemented:** exact `"PASS"` routes to Human Review; exact `"FAIL"` routes to remediation and increments iteration count; any other value ends the graph. No enum validator. |
| `compliance_check` (`dict`) | Security/compliance review artifact. | Security / no consumer is specified in the current contract/workflow. | `{}` | **Implemented:** top-level type only. Nested schema is **Recommended**, not enforced. |

**Examples**

```json
{
    "test_cases": [{"id": "TC-001", "description": "Browse listings", "expected": "Listings are shown"}],
    "test_results": {"total": 1, "passed": 1, "failed": 0},
    "bugs": [{"id": "BUG-001", "agent": "frontend", "description": "Listing image is not displayed.", "severity": "high"}],
    "qa_status": "PASS",
    "security_findings": [{"id": "SEC-001", "agent": "both", "description": "Validate listing content at the API boundary.", "severity": "high"}],
    "security_status": "PASS",
    "compliance_check": {"reviewed": true, "notes": []}
}
```

### Workflow and review

| Field (type) | Purpose | Writer / readers | Default | Validation |
|---|---|---|---|---|
| `current_stage` (`str`) | Latest stage marker. | Every current agent writes its completion marker; Human Review writes `HUMAN_REVIEW`. Human/operator may read it; workflow routing does not. | `"INITIALIZED"` | **Implemented:** values are assigned by current nodes but not validated. See [Status and Enum Definitions](#5-status-and-enum-definitions). |
| `iteration_count` (`int`) | Count of QA and Security failure/remediation iterations. | Caller / workflow | `0` | **Implemented:** type annotation only; workflow converts the existing value with `int(...)` when incrementing. **Recommended:** non-negative. |
| `final_status` (`str`) | Terminal readiness result. | Human Review workflow node / Human/operator; workflow routing does not read it. | `""` | **Implemented:** Human Review assigns `"READY_FOR_HUMAN_REVIEW"`; no validator. |

**Examples**

```json
{
    "current_stage": "HUMAN_REVIEW",
    "iteration_count": 1,
    "final_status": "READY_FOR_HUMAN_REVIEW"
}
```

## 3. Detailed Field Schemas

The structures in this section are examples for a future shared convention. Unless a rule is explicitly identified as implemented or documented, nested keys and item types are **Recommended**, not enforced. Empty containers in the initial state are valid placeholders and do not imply a nested schema.

#### Planning and architecture fields

| Field | Expected structure and key meanings |
|---|---|
| `requirements` | **Recommended:** object with `functional` and `non_functional` lists. Each entry may have `id` (string), `description` (string), and optional `priority` (string). No keys or priority values are currently prescribed. |
| `user_stories` | **Recommended:** list of objects with `id` (string), `story` (string), and `acceptance_criteria` (list of strings). The contract requires user stories but does not define their shape. |
| `mvp_scope` | **Recommended:** list of strings naming in-scope capabilities. The contract does not say whether entries must be strings or objects. |
| `architecture` | **Recommended:** object with `components` (list of component descriptions) and `decisions` (list of architecture decisions). Inner shapes remain team-defined. |
| `technology_stack` | **Recommended:** object mapping roles to technology names (strings). Role names are not fixed by code. |
| `database_schema` | **Recommended:** object containing an `entities` list. Entity and field structures are not defined by the project code; this is a design artifact, not an implemented marketplace database. |
| `api_specification` | **Recommended:** object containing an `endpoints` list. Method, path, request, and response conventions require team agreement. |

**Illustrative examples**

```json
{
    "requirements": {
        "functional": [{"id": "REQ-F-001", "description": "Buyers can browse clothing listings.", "priority": "must"}],
        "non_functional": [{"id": "REQ-NF-001", "description": "Listing pages should load promptly.", "priority": "should"}]
    },
    "user_stories": [
        {"id": "US-001", "story": "As a buyer, I can browse clothing listings.", "acceptance_criteria": ["Listings show a title and price."]}
    ],
    "mvp_scope": ["Browse clothing listings", "Create a seller listing"],
    "architecture": {
        "components": [{"name": "Web client", "responsibility": "Browse and manage listings"}],
        "decisions": [{"decision": "Use an API boundary between client and server", "reason": "Separate presentation and application logic"}]
    },
    "technology_stack": {"frontend": "React", "backend": "Python", "workflow": "LangGraph", "tests": "pytest"},
    "database_schema": {
        "entities": [{"name": "Listing", "fields": [{"name": "title", "type": "string"}, {"name": "price", "type": "decimal"}]}]
    },
    "api_specification": {
        "endpoints": [{"method": "GET", "path": "/listings", "purpose": "Retrieve clothing listings"}]
    }
}
```

#### Development artifact fields

| Field | Expected structure and key meanings |
|---|---|
| `frontend_code` | **Recommended:** object of frontend artifacts. A possible `components` list can contain objects with `name` and `purpose`. Code storage format (source text, paths, or structured descriptions) is not defined. |
| `backend_code` | **Recommended:** object of backend artifacts. A possible `modules` list can contain objects with `name` and `purpose`. Code storage format is not defined. |

**Illustrative examples**

```json
{
    "frontend_code": {"components": [{"name": "ListingGrid", "purpose": "Present a collection of clothing listings"}]},
    "backend_code": {"modules": [{"name": "listing_service", "purpose": "Describe listing retrieval operations"}]}
}
```

#### QA fields

| Field | Expected structure and key meanings |
|---|---|
| `test_cases` | **Recommended:** list of objects with `id`, `description`, and `expected` (strings). The contract requires test cases but does not define their item schema. |
| `test_results` | **Recommended:** object with numeric `total`, `passed`, `failed` counts and optionally a `cases` list of per-case outcomes. Outcome values are not defined by code. |
| `bugs` | **Documented format:** list of objects with `id` (string), `agent` (`"frontend"` or `"backend"`), `description` (string), and `severity` (string; the contract's example is `"high"`). Severity vocabulary and ID format are not enforced. Workflow selects the last bug when QA fails. |

**Illustrative examples**

```json
{
    "test_cases": [{"id": "TC-001", "description": "Open the listing browse view.", "expected": "The view presents available listings."}],
    "test_results": {"total": 1, "passed": 1, "failed": 0, "cases": [{"id": "TC-001", "result": "PASS"}]},
    "bugs": [{"id": "BUG-001", "agent": "frontend", "description": "The listing card omits its price.", "severity": "high"}]
}
```

#### Security fields

| Field | Expected structure and key meanings |
|---|---|
| `security_findings` | **Documented format:** list of objects with `id` (string), `agent` (`"frontend"`, `"backend"`, or `"both"`), `description` (string), and `severity` (string; the contract's example is `"high"`). Workflow selects the last finding when Security fails. `"both"` causes frontend and then backend remediation before returning to QA. |
| `compliance_check` | **Recommended:** object recording the review outcome and notes, e.g. `reviewed` (boolean) and `notes` (list of strings). The contract names the output but defines no nested format. |

**Illustrative examples**

```json
{
    "security_findings": [{"id": "SEC-001", "agent": "both", "description": "Reject malformed listing data in both client and API validation.", "severity": "high"}],
    "compliance_check": {"reviewed": true, "notes": ["Review data-retention expectations before implementation."]}
}
```

## 4. Agent Input and Output Mapping

Inputs and logical outputs below follow `docs/agent_contract.md`. The current agent bodies are placeholders: each sets `current_stage` and returns the shared state; their TODO comments do not implement the contract outputs. **Must not modify** describes a recommended ownership boundary, not an enforced access restriction. Every agent receives the whole state and can technically mutate any field.

#### PM Agent

- **Inputs:** `project_goal`, `project_description`
- **Outputs:** `requirements`, `user_stories`, `mvp_scope`
- **Ownership:** Must not modify fields outside its outputs. `current_stage` is a current implementation side effect.
- **Validation:** Keep outputs at the existing top-level keys. Nested conventions in Section 3 are recommendations only.

#### Software Architect Agent

- **Inputs:** `project_goal`, `project_description`, `requirements`, `user_stories`, `mvp_scope`
- **Outputs:** `architecture`, `technology_stack`, `database_schema`, `api_specification`
- **Ownership:** Must not modify fields outside its outputs. `current_stage` is a current implementation side effect.
- **Validation:** Keep outputs at the existing top-level keys. Nested conventions in Section 3 are recommendations only.

#### Frontend Developer Agent

- **Inputs:** `requirements`, `user_stories`, `architecture`, `technology_stack`, `api_specification`, `frontend_code`, `bugs`, `test_results`, `security_findings`
- **Outputs:** `frontend_code`
- **Ownership:** Must not modify fields outside `frontend_code`. `current_stage` is a current implementation side effect.
- **Validation:** Preserve the dictionary top-level type. When addressing a finding, use its `agent` assignment as the ownership signal. No runtime validation exists.

#### Backend Developer Agent

- **Inputs:** `requirements`, `user_stories`, `architecture`, `technology_stack`, `database_schema`, `api_specification`, `backend_code`, `bugs`, `test_results`, `security_findings`
- **Outputs:** `backend_code`
- **Ownership:** Must not modify fields outside `backend_code`. `current_stage` is a current implementation side effect.
- **Validation:** Preserve the dictionary top-level type. When addressing a finding, use its `agent` assignment as the ownership signal. No runtime validation exists.

#### QA & Software Tester Agent

- **Inputs:** `requirements`, `user_stories`, `frontend_code`, `backend_code`, `api_specification`
- **Outputs:** `test_cases`, `test_results`, `bugs`, `qa_status`
- **Ownership:** Must not modify fields outside its outputs. `current_stage` is a current implementation side effect.
- **Validation:** `bugs` should follow the documented format; set `qa_status` to a recognized routing value (`PASS` or `FAIL`). The current agent does not enforce either rule.

#### Security & Compliance Agent

- **Inputs:** `requirements`, `architecture`, `frontend_code`, `backend_code`, `database_schema`, `api_specification`
- **Outputs:** `security_findings`, `security_status`, `compliance_check`
- **Ownership:** Must not modify fields outside its outputs. `current_stage` is a current implementation side effect.
- **Validation:** `security_findings` should follow the documented format, including supported owner `both`; set `security_status` to a recognized routing value (`PASS` or `FAIL`). The current agent does not enforce either rule.

The workflow also reads `bugs` and `security_findings` only when the corresponding status is `FAIL`, increments `iteration_count` on those failures, and writes `current_stage` plus `final_status` in Human Review. It does not currently consume the detailed structures suggested in Section 3.

## 5. Status and Enum Definitions

No Python enum, `Literal`, or runtime validation is defined for these string fields. Values below are either assignments/comparisons present in code or recommendations; they must not be mistaken for validated enums.

| Field | Implemented values/behavior | Recommendation / notes |
|---|---|---|
| `qa_status` | Initial value is `""`. Workflow recognizes exact `"PASS"` and exact `"FAIL"`. `PASS` proceeds to Security; `FAIL` increments `iteration_count` and routes to remediation. Any other value ends the workflow. | Use only uppercase `PASS` or `FAIL` after QA completes. Empty is an initial/incomplete value, not a pass. No enum validator currently enforces this. |
| `security_status` | Initial value is `""`. Workflow recognizes exact `"PASS"` and exact `"FAIL"`. `PASS` proceeds to Human Review; `FAIL` increments `iteration_count` and routes to remediation. Any other value ends the workflow. | Use only uppercase `PASS` or `FAIL` after Security completes. Empty is an initial/incomplete value, not a pass. No enum validator currently enforces this. |
| `current_stage` | Initial `"INITIALIZED"`; agent code assigns `"PM_AGENT_COMPLETE"`, `"ARCHITECT_AGENT_COMPLETE"`, `"FRONTEND_AGENT_COMPLETE"`, `"BACKEND_AGENT_COMPLETE"`, `"QA_AGENT_COMPLETE"`, or `"SECURITY_AGENT_COMPLETE"`; Human Review assigns `"HUMAN_REVIEW"`. | These are observed assignments, not a closed enum. Future nodes may need coordinated names. No validator enforces a fixed set. |
| `final_status` | Initial `""`; Human Review assigns `"READY_FOR_HUMAN_REVIEW"`. | These are the only current values. Empty means not finalized; the readiness value does not mean human approval or deployment. No validator enforces this. |

The status fields remain plain `str` values in `ProjectState`. Workflow routing recognizes exact uppercase tokens; it does not normalize case or whitespace.

## 6. Data Validation Rules

### Implemented

- `ProjectState` declares all listed keys with top-level annotations. `create_initial_state` returns every key with the defaults shown in Section 2.
- The current code provides no runtime validation for key presence, Python value types, nested dictionary/list structures, bug/finding shape, or status vocabulary.
- The workflow recognizes exact `PASS` and `FAIL` for QA and Security. An empty, missing, or other status does not route to a pass path; it ends the workflow.
- On either exact `FAIL`, the workflow increments `iteration_count`. QA uses the last bug if present (otherwise routes to backend); Security uses the last finding if present (otherwise routes to frontend). For a security finding whose `agent` is `both`, the graph invokes frontend then backend before returning to QA.
- Human Review sets `current_stage` to `HUMAN_REVIEW` and `final_status` to `READY_FOR_HUMAN_REVIEW`.

### Recommended, not currently enforced

- Keep every declared top-level key present and preserve its annotated type; do not use `None` to mean "not yet produced." Use the existing empty string, empty list, empty dictionary, or zero defaults as appropriate until the agent produces a result.
- After an agent has run, distinguish "not evaluated" from "evaluated and empty." In particular, empty `bugs` or `security_findings` can mean no issues, but an empty `qa_status` or `security_status` means the result is incomplete. Do not infer `PASS` from empty findings.
- Before a QA or Security outcome is routed, require exact uppercase `PASS` or `FAIL`. If an output is missing, malformed, or outside the agreed vocabulary, stop or return it for correction rather than treating it as a pass. The current workflow stops on an unrecognized status but has no explicit recovery node.
- Validate every finding as an object with non-empty string `id` and `description`, a supported `agent` value, and a team-agreed `severity` value. The workflow currently assumes entries support `.get(...)` and uses only the last entry; malformed entries may fail at runtime or route unexpectedly.
- Keep result fields internally consistent; for example, if `test_results` has counts, `total` should equal `passed + failed`, and the counts should agree with `test_cases`. No such cross-field rules currently exist.
- Treat workflow-owned fields (`iteration_count`, terminal `current_stage`, and `final_status`) as workflow-owned; agents should not change them except for the current skeleton's `current_stage` completion marker behavior.
- If parallel branches can write the same state key, agree on reducers or another merge policy before relying on concurrent execution. The graph currently contains Architect-to-Frontend and Architect-to-Backend fan-out, while `ProjectState` has no reducer/merge definitions.

## 7. Example ProjectState

This is a complete illustrative state with all keys. The nested formats are examples, not enforced schemas. It represents a completed set of reviews ready for a human decision and contains no real personal information or secrets.

```python
example_state = {
    "project_goal": "Plan a marketplace for pre-owned clothing.",
    "project_description": "Buyers browse clothing listings and sellers manage listings.",
    "requirements": {
        "functional": [
            {"id": "REQ-F-001", "description": "Buyers can browse listings.", "priority": "must"}
        ],
        "non_functional": [
            {"id": "REQ-NF-001", "description": "Listing pages should load promptly.", "priority": "should"}
        ],
    },
    "user_stories": [
        {
            "id": "US-001",
            "story": "As a buyer, I can browse clothing listings.",
            "acceptance_criteria": ["Listings show a title and price."],
        }
    ],
    "mvp_scope": ["Browse clothing listings", "Create a seller listing"],
    "architecture": {
        "components": [{"name": "Web client", "responsibility": "Browse and manage listings"}],
        "decisions": [{"decision": "Separate client and API", "reason": "Keep presentation separate from application logic"}],
    },
    "technology_stack": {"frontend": "React", "backend": "Python", "workflow": "LangGraph"},
    "database_schema": {
        "entities": [
            {"name": "Listing", "fields": [{"name": "title", "type": "string"}, {"name": "price", "type": "decimal"}]}
        ]
    },
    "api_specification": {
        "endpoints": [{"method": "GET", "path": "/listings", "purpose": "Retrieve clothing listings"}]
    },
    "frontend_code": {"components": [{"name": "ListingGrid", "purpose": "Present clothing listings"}]},
    "backend_code": {"modules": [{"name": "listing_service", "purpose": "Describe listing retrieval"}]},
    "test_cases": [
        {"id": "TC-001", "description": "Open the listing browse view.", "expected": "Available listings are presented."}
    ],
    "test_results": {
        "total": 1,
        "passed": 1,
        "failed": 0,
        "cases": [{"id": "TC-001", "result": "PASS"}],
    },
    "bugs": [],
    "qa_status": "PASS",
    "security_findings": [],
    "security_status": "PASS",
    "compliance_check": {"reviewed": True, "notes": []},
    "current_stage": "HUMAN_REVIEW",
    "iteration_count": 0,
    "final_status": "READY_FOR_HUMAN_REVIEW",
}
```

## 8. Known Gaps and Recommendations

- **Nested schemas are not implemented.** Most dictionary and list fields have only a broad built-in type annotation. The suggested structures in this document need team agreement before agents rely on them.
- **No runtime validation exists.** `TypedDict` provides static typing support; it does not validate dictionaries returned at runtime. A malformed or incomplete agent output can pass through without a clear validation error.
- **Statuses have no enforced enum.** Workflow comparisons define the recognized QA and Security routing tokens, but `ProjectState` declares plain strings and agents currently do not set either status. An invalid value ends the graph without a dedicated error or recovery path.
- **Contract outputs are not produced yet.** The Agent Contract assigns outputs to all six agents, but current agent methods contain TODOs and only set their `current_stage` completion marker. No agent currently populates its specified output fields.
- **Current-stage ownership is broader in code than in the contract.** Each agent mutates `current_stage`, though the contract describes domain outputs and does not list that field among agent outputs.
- **Finding selection is limited.** On failure the workflow routes using only the last bug or security finding. QA finding ownership outside `frontend`/`backend` is not specified; Security explicitly permits `both`. Malformed or unexpected finding owners are not validated before routing.
- **Parallel merge semantics are unresolved.** Architect fans out to separate frontend and backend nodes. Both receive the shared state and may write it; `ProjectState` defines no reducers or explicit merge rules. The workflow contains a TODO to address synchronization/state merge before relying on parallel fan-out.
- **Iteration policy is minimal.** The graph increments `iteration_count` on QA and Security failures but does not define a maximum, exhaustion behavior, or non-negative-value validator.
- **Recommended next agreement:** decide nested structures, status/error policy, severity vocabulary, finding ID conventions, state ownership, and merge rules, then add validators and focused tests in a separately approved implementation change.