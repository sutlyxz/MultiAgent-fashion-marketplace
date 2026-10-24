# Agent Contract and Team Ownership

## Shared ProjectState

The shared ProjectState is documented in `docs/data_schema.md` and `docs/agent_contract.md` (historically prototyped as a Python TypedDict in `models/state.py`) and is used across all six Antigravity native agent skills and the master orchestration workflow. It includes:

- project_goal
- project_description
- requirements
- user_stories
- mvp_scope
- architecture
- technology_stack
- database_schema
- api_specification
- frontend_code
- backend_code
- test_cases
- test_results
- bugs
- qa_status
- security_findings
- security_status
- compliance_check
- current_stage
- iteration_count
- final_status

Agents receive the shared ProjectState contract. Workflow adapters run agents against a copy and merge only the fields owned by that agent, so parallel branches do not publish full-state updates.

## Team members and ownership

- Person 1: PM Agent -> [`.agents/skills/pm-agent/SKILL.md`](file:///.agents/skills/pm-agent/SKILL.md) (formerly `agents/pm_agent.py`)
- Person 2: Software Architect Agent -> [`.agents/skills/architect-agent/SKILL.md`](file:///.agents/skills/architect-agent/SKILL.md) (formerly `agents/architect_agent.py`)
- Person 3: Frontend Developer Agent -> [`.agents/skills/frontend-developer/SKILL.md`](file:///.agents/skills/frontend-developer/SKILL.md) (formerly `agents/frontend_agent.py`)
- Person 4: Backend Developer Agent -> [`.agents/skills/backend-developer/SKILL.md`](file:///.agents/skills/backend-developer/SKILL.md) (formerly `agents/backend_agent.py`)
- Person 5: QA & Software Tester Agent -> [`.agents/skills/qa-agent/SKILL.md`](file:///.agents/skills/qa-agent/SKILL.md) (formerly `agents/qa_agent.py`)
- Person 6: Security & Compliance Agent -> [`.agents/skills/security-agent/SKILL.md`](file:///.agents/skills/security-agent/SKILL.md) (formerly `agents/security_agent.py`)
- Lifecycle Orchestration: Master Workflow -> [`.agents/skills/master-workflow/SKILL.md`](file:///.agents/skills/master-workflow/SKILL.md) (formerly `workflow/graph.py` / `orchestrator.py`)

Shared contract authorities include:

- `docs/agent_contract.md`
- `docs/data_schema.md`
- `workflow.md`
- `.agents/skills/master-workflow/SKILL.md`

These files define the canonical inter-agent contracts and should not be modified independently without team agreement.

## Agent responsibilities

### PM Agent
Input:
- project_goal
- project_description
Output:
- requirements
- user_stories
- mvp_scope
Responsibilities:
- Analyze the project goal
- Define functional and non-functional requirements
- Create user stories
- Define MVP scope

### Software Architect Agent
Input:
- project_goal
- project_description
- requirements
- user_stories
- mvp_scope
Output:
- architecture
- technology_stack
- database_schema
- api_specification
Responsibilities:
- Design system architecture
- Define technology stack
- Design database schema
- Define API specification

The current selected technology baseline is React, TypeScript, Vite, Tailwind CSS,
React Router; Python/FastAPI; PostgreSQL with SQLAlchemy ORM and Alembic migrations;
Redis with BullMQ; LangGraph,
LangChain, and Google Gemini API; ChromaDB; JWT with Bcrypt; REST/JSON; and Pytest.
The Architect records these choices as confirmed rather than asking downstream agents
to choose among alternatives.

The architecture artifacts describe variant-level `Stock` as authoritative inventory
and `Product.stock_quantity` as a display aggregate. Payment records represent the MVP
PaymentSlip evidence lifecycle (uploaded/processing/verified/rejected); upload alone
does not verify payment. Inventory is conditionally decremented in an idempotent
PostgreSQL transaction only after payment verification, and insufficient stock leaves
inventory unchanged and routes the paid order to manual resolution/refund review.
`CheckoutSession` models an expiring fast-link bound to the buyer, product variant,
and quantity. `CRMTag`/`UserCRMTag` support seller-scoped customer tagging.
`SupportTicket` represents logistics tickets that can be created for tracking
anomalies; `Claim` represents a ClaimRequest. ChromaDB retrieves policy and warranty
context for LangGraph/LangChain/Gemini recommendations, while sellers retain final
claim decisions. These are design artifacts, not claims that backend behavior has
already been implemented.

### Frontend Developer Agent
Input:
- project_goal
- project_description
- requirements
- user_stories
- mvp_scope
- architecture
- technology_stack
- api_specification
- frontend_code
- bugs
- test_results
- security_findings
Output:
- frontend_code
Responsibilities:
- Design frontend structure
- Create UI components
- Implement frontend logic
- Integrate frontend with backend APIs
- Fix frontend bugs reported by QA
- Fix frontend security issues

The Frontend Developer implements source code according to PM requirements and
Architect-defined technical contracts. Architect remains authoritative for system
architecture, technology selection, API paths/methods/contracts, and database design;
Frontend may choose implementation details within the frontend domain but must report
a blocker rather than silently changing an Architect-owned decision.

`FrontendDeveloperAgent.run()` reads the existing React application, validates PM and
Architect inputs, and—when an LLM generator is configured—generates and writes the
validated changed source files under `frontend/`. It returns only the owned
`frontend_code` update. Its result records created/modified paths, implementation and
validation status, blockers, test status, and remaining work; it does not store full
source-code contents in ProjectState. Files absent from a generation result are never
deleted. If no generator is configured, it reports that no implementation was
generated rather than claiming completion. A generated source change is not described
as built or tested unless those operations actually ran.

The `ProjectOrchestrator` runs PM, Architect, then Frontend, and can run the frontend
build and configured tests as separate operations. The Frontend Agent does not own
`current_stage`; workflow/orchestration sets stage transitions. Mock login is a
browser demonstration, not real authentication or security, and mock checkout is not
payment processing or verification. API mappings describe Architect contracts only;
service integration remains mock-based until implemented against an aligned Backend
contract.

Mock login is a browser demonstration, not real authentication or security, and mock
checkout is not payment processing or verification. API mappings describe Architect
contracts only; service integration remains mock-based until implemented against an
aligned Backend contract.

### Backend Developer Agent
Input:
- requirements
- user_stories
- architecture
- technology_stack
- database_schema
- api_specification
- backend_code
- bugs
- test_results
- security_findings
Output:
- backend_code
Responsibilities:
- Translate Architect-owned architecture, technology stack, database schema, and API specification into a deterministic implementation plan in `backend_code`
- Plan API, persistence, domain-service, payment, inventory, CRM, logistics, warranty, AI/RAG, and integration implementation tasks
- Preserve Architect-owned decisions; report missing or conflicting artifacts as structured blockers rather than redesigning them
- Fix backend bugs reported by QA
- Fix backend security issues

The current Backend Agent produces implementation-planning artifacts only. It does not
create or write marketplace backend source files, call external providers, or claim
that integrations have been tested. It reads optional PM requirements and user stories
for traceability, and includes backend-owned QA/security feedback. It preserves the
incoming `current_stage`; workflow/orchestration remains responsible for stage changes.
The plan follows routes and entities from the Architect artifacts and calls out
unresolved implementation choices, including PostgreSQL connection/deployment
configuration, payment-slip QR/OCR provider, carrier, and Python-to-BullMQ integration.

### QA & Software Tester Agent
Input:
- requirements
- user_stories
- frontend_code
- backend_code
- api_specification
Output:
- test_cases
- test_results
- bugs
- qa_status
Bug format:
{
  "id": "BUG-001",
  "agent": "frontend",
  "description": "A UI issue was identified.",
  "severity": "high"
}
Agent field values:
- frontend
- backend

### Security & Compliance Agent
Input:
- requirements
- architecture
- frontend_code
- backend_code
- database_schema
- api_specification
Output:
- security_findings
- security_status
- compliance_check
Security finding format:
{
  "id": "SEC-001",
  "agent": "backend",
  "description": "A backend vulnerability requires remediation.",
  "severity": "high"
}
Agent field values:
- frontend
- backend
- both

## Frontend Implementation Flow

The Frontend Developer inspects the existing `frontend/` source locally, uses PM and
Architect artifacts plus relevant QA/Security feedback, generates only the needed
changes, validates its structured output, and writes those changes under `frontend/`.
No separate Frontend implementation Agent, outbound-source approval pipeline, or
preview/write-approval stage is part of this contract. The Agent does not delete
files. The ProjectOrchestrator runs PM -> Architect -> Frontend; build and test remain
separate, explicitly reported validation operations.

## Workflow Field Ownership

Workflow nodes must return partial updates containing only their owned output fields:

- PM Agent: requirements, user_stories, mvp_scope
- Software Architect Agent: architecture, technology_stack, database_schema, api_specification
- Frontend Agent: frontend_code
- Backend Agent: backend_code
- QA Agent: test_cases, test_results, bugs, qa_status
- Security Agent: security_findings, security_status, compliance_check

`current_stage` and `iteration_count` are workflow/orchestrator-owned fields. PM,
Architect, and Backend `run()` methods update their domain fields and return the
passed ProjectState, but do not change `current_stage`. The LangGraph adapter and
`ProjectOrchestrator` run agents on copied state, merge only domain fields, and set
stage values themselves; an Agent-returned stage is never authoritative. Frontend and
Backend may run in parallel; QA must be behind a synchronization join that waits for
both branches, and the workflow updates `current_stage` only after that join.

## Workflow and Future Review Routing

The default `build_workflow()` includes PM and Architect only and ends after Architect.
The optional downstream graph requires all four downstream callables to be explicitly
supplied through `build_workflow(downstream_agents=...)`; it is not enabled
automatically. The Backend Agent can be supplied for its `backend_code` planning
output, but is not wired into the default graph. The LangGraph flow does not invoke
the Frontend Gemini generation path.

The future graph uses max_retries as a shared remediation-round budget across QA and Security. Failed QA routes the last reported bug to its owning Frontend or Backend handler; a passing QA result proceeds to Security. Failed Security routes the last finding to its owner, or runs Frontend then Backend for a finding assigned to both, and returns through QA. Ambiguous statuses, missing or invalid ownership, and exhausted retry budgets route to human escalation.

Successful QA and Security checks set final_status = "READY_FOR_HUMAN_REVIEW". Unresolved failures set final_status = "NEEDS_HUMAN_REVIEW". In both cases the graph ends after setting the status; it does not pause for interactive human input. A caller must inspect the status and provide any later approval workflow.

## Current Implementation Status

Implemented:

- PM Agent: deterministic baseline requirements, user stories, and MVP scope; no LLM or network is required by default.
- Software Architect Agent: deterministic architecture, selected technology stack, database schema, and API specification; no LLM or network is required. Its opt-in Gemini planner is validated against the selected stack and required architecture contract.
- Frontend Developer Agent: reads the existing React application and can generate and write validated changes under `frontend/` when an LLM generator is configured. It returns only `frontend_code` metadata and truthful implementation/validation/test status; without a configured generator it does not claim to have implemented new changes.
- Backend Developer Agent: deterministic, validated implementation planning artifacts in `backend_code` based on Architect-owned outputs. It reports missing/conflicting Architect data and open integration decisions; it does not implement or write the marketplace backend source.
- Workflow path: PM -> Architect, with owned-field updates and a real executable invocation.

Not implemented:

- QA Agent and Security Agent remain TODO stubs. Their presence in the repository does not make them production workflow steps.
- The marketplace backend application itself (FastAPI routes, database integration, payment processing, carrier services, AI/RAG runtime, and production authentication) is not implemented by the Backend Agent planning task.
- `ProjectOrchestrator` runs PM -> Architect -> Frontend and exposes build/test as separate operations. `workflow/graph.py` is a separate general state workflow: `build_workflow()` defaults to PM -> Architect and ends there. Its optional downstream branch is included only when all downstream Agent callables are explicitly supplied.
- Mock login is a browser demonstration only; mock checkout does not provide authentication, payment processing, verification, or persistent orders.
- The human-review node records a status and ends; it does not collect human input or resume execution.