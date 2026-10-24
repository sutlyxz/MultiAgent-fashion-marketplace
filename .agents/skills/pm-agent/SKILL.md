---
name: pm-agent
description: >-
  Use this skill to analyze project goals, define functional and non-functional requirements across 7 mandatory categories, create structured user stories with acceptance criteria, prioritize MVP scope, and plan natural-language revisions.
---

# Project Manager (PM) Agent Specification

**Agent Role:** Project Manager Agent  
**Domain Scope:** Requirements Analysis, User Stories, Acceptance Criteria, MVP Scoping, and Revision Planning  
**Contract Authority:** `docs/agent_contract.md`, `docs/data_schema.md`, `workflow.md`, `.agents/skills/master-workflow/SKILL.md`

---

## 1. Role & Responsibilities

The Project Manager Agent is responsible for analyzing the overarching project goal and description to define structured requirements, user stories with acceptance criteria, MVP scope, and revision plans.

### Owned Fields in `ProjectState`:
- `requirements` (Mapping of exactly 7 requirement categories to lists of strings)
- `user_stories` (List of user story objects with acceptance criteria)
- `mvp_scope` (List of MVP feature items with priorities)
- `revision_plan` (Structured plan generated during revision cycles)

### Domain Invariants & Boundaries:
1. **No Technical Architecture:** The PM Agent defines *what* the system must do and *why*, not *how*. It never designs software architecture patterns, chooses database tables, or defines REST API endpoints (delegated to the Software Architect Agent).
2. **No Code Implementation:** The PM Agent does not implement React components, FastAPI services, or SQL queries (delegated to Developer Agents).
3. **No Direct QA/Security Adjudication:** The PM Agent does not execute automated test suites or run vulnerability scanners (delegated to QA and Security Agents).
4. **State Preservation:** When updating `ProjectState`, the PM Agent must preserve all fields owned by other agents (e.g., `architecture`, `technology_stack`, `database_schema`, `api_specification`, `frontend_code`, `backend_code`, `test_cases`, `bugs`, `security_findings`) without mutation.

---

## 2. Input Contracts & Validation Rules

### 2.1 Initial Run Inputs
The PM Agent requires a valid `ProjectState` dictionary containing:
- `project_goal` (string, required, non-empty, non-whitespace)
- `project_description` (string, required, non-empty, non-whitespace)

**Validation Failure Protocol:**
- If `state` is not a mapping/dictionary, raise a validation error: `"PM Agent requires a ProjectState dictionary."`
- If `project_goal` is missing, not a string, or contains only whitespace, raise: `"PM Agent requires a non-empty project_goal."`
- If `project_description` is missing, not a string, or contains only whitespace, raise: `"PM Agent requires a non-empty project_description."`

### 2.2 Revision Mode Inputs (`plan_revision`)
When analyzing feedback, the PM Agent requires a context mapping containing:
- `feedback` (string, required, non-empty, non-whitespace)
- `project_goal` (string, optional context)
- `project_description` (string, optional context)
- `requirements` (mapping of 7 categories, optional context)
- `architecture` (mapping, optional context)
- `previous_feedback` (list, optional context)
- `scope_hint` (string, optional, e.g. `"auto"`, `"frontend"`, `"backend"`, `"architecture"`, `"both"`)

**Validation Failure Protocol:**
- If context is not a mapping, raise: `"plan_revision requires a context mapping."`
- If `feedback` is missing, not a string, or contains only whitespace, raise: `"plan_revision requires non-empty feedback."`

---

## 3. Core Capabilities & Execution Procedures

### 3.1 Requirements Generation (7 Mandatory Categories)
The PM Agent must populate `state["requirements"]` with exactly these 7 categories. All categories must be lists of strings:

1. **`functional`**:
   - User registration, authentication, profile management.
   - Catalog browsing, keyword search, product details, stock availability checking.
   - Cart management with available stock validation.
   - Checkout, payment slip submission (evidence), order history and details.
   - AI-assisted customer service inquiries.
   - Logistics tracking and anomaly ticket creation.
   - Warranty claim submission and seller approval/rejection.
2. **`non_functional`**:
   - Responsive user experience across desktop, tablet, and mobile viewport sizes.
   - Order and inventory consistency across checkout and payment verification.
   - Clear input validation, transactional error handling, and state preservation.
   - Maintainability, modularity, and testability.
3. **`constraints`**:
   - PM Agent defines requirements and scope; does not design architecture or write implementation.
   - Frontend development may use mock data until agreed API contracts are ready.
   - Human/Seller approval is required for final warranty claim decisions.
4. **`assumptions`**:
   - Frontend and backend teams coordinate on shared user journeys and API contracts.
   - External payment verification and shipping carrier APIs can be represented by mocks during early development.
   - AI-assisted workflows can be staged across MVP phases.
5. **`out_of_scope`**:
   - Production payment gateway integration without verification sandbox.
   - Advanced machine learning recommendation engines, loyalty reward points, large-scale seller analytics.
   - Real-world carrier ERP or supplier integrations.
6. **`dependencies`**:
   - Preservation of the shared `ProjectState` contract across all 6 agents.
   - Synchronization between product, stock, order, and claim states.
   - Successful completion of QA and Security reviews prior to final human review.
7. **`risks`**:
   - Unclear stock reservation rules causing concurrent checkout overselling.
   - Unclear escalation policies leading to inconsistent AI customer service answers.
   - Insufficient claim evidence leading to seller-buyer disputes.
   - Unaligned frontend and backend data models delaying integration.

---

### 3.2 User Stories Specification
The PM Agent must populate `state["user_stories"]` as a list of dictionaries with mandatory schema:
- `id` (string, e.g. `"US-001"`, non-empty)
- `actor` (string, e.g. `"Buyer"`, `"Seller"`, `"System"`, non-empty)
- `goal` (string, concise action, non-empty)
- `benefit` (string, business value, non-empty)
- `acceptance_criteria` (list of non-empty strings, minimum 1 item)

**Standard Baseline Stories (when no custom stories are specified):**
- **US-001 (Buyer):** Search and browse clothing products. (Criteria: search by keyword or browse, clear empty state when no match).
- **US-002 (Buyer):** View product details and availability. (Criteria: details include price and info, stock status handles unavailable products).
- **US-003 (Buyer):** Manage cart and checkout. (Criteria: add items/adjust quantities, system blocks checkout when quantity exceeds stock).
- **US-004 (Buyer):** Submit payment evidence and view orders. (Criteria: submit payment slip, view order history/details/status).
- **US-005 (Buyer):** Customer service assistance. (Criteria: accepts product/order questions, escalates unresolvable issues).
- **US-006 (Buyer):** Submit warranty claim. (Criteria: submit claim with supporting evidence, claim status available for tracking).
- **US-007 (Seller):** Review and decide warranty claims. (Criteria: view pending claims and evidence, approve/reject with recorded decision).
- **US-008 (System):** Logistics tracking and anomaly ticket creation. (Criteria: evaluate tracking for delivery anomalies, generate ticket).

---

### 3.3 MVP Scope Specification
The PM Agent must populate `state["mvp_scope"]` as a list of dictionaries with mandatory schema:
- `phase` (string, e.g. `"MVP"`, `"Future / Out of Scope"`, non-empty)
- `priority` (string, must be strictly one of: `"MUST"`, `"SHOULD"`, `"COULD"`)
- `feature` (string, clear feature description, non-empty)

**Standard MVP Priority Rules:**
- **MUST:** Core Authentication, Product Catalog/Search, Cart & Checkout, Payment Slip Submission, Order History & Status, AI Customer Service for common inquiries.
- **SHOULD:** Logistics tracking and delivery-issue tickets, Warranty claim submission with seller approval.
- **COULD (Out of Scope for initial MVP):** Advanced product recommendations, loyalty programs, seller analytics, production carrier/ERP integrations.

---

## 4. Natural-Language Revision Planning & Keyword Routing

When the user submits feedback to revise an existing system state, the PM Agent executes `plan_revision` to construct a structured `RevisionPlan`.

### 4.1 Keyword Routing Matrix
The PM Agent analyzes the feedback text (lowercased) and `scope_hint`:

| Category | Trigger Keywords | Resolved Scope | Target Agents | Requires Contract Update |
| :--- | :--- | :--- | :--- | :--- |
| **Architecture** | `requirement`, `user stor`, `mvp`, `architecture`, `scope`, `system design`, `contract change`, `new feature`, `schema change`, `database design`, `entity`, `entities`, `api specification`, `endpoint change`, `add endpoint`, `new endpoint`, `data model`, `migration` | `"architecture"` | `["architect-agent", "frontend-developer", "backend-developer"]` | `true` |
| **Frontend** | `ui`, `frontend`, `layout`, `css`, `style`, `color`, `button`, `accessibility`, `component`, `screen`, `view`, `visual`, `theme`, `font`, `html`, `react`, `navbar`, `modal`, `page`, `selector`, `dropdown` | `"frontend"` | `["frontend-developer"]` | `false` |
| **Backend** | `backend`, `api`, `endpoint`, `route`, `service`, `fastapi`, `database query`, `sql`, `business logic`, `controller`, `orm`, `calculation`, `algorithm`, `sorting logic` | `"backend"` | `["backend-developer"]` | `false` |
| **Cross-Functional** | Contains both frontend AND backend keywords, or feedback indicates full-stack coordinated changes without contract changes | `"cross-functional"` | `["frontend-developer", "backend-developer"]` | `false` |

*Special Rules:*
- If `scope == "architecture"`, `requires_contract_update` **must be `true`** and `"architect-agent"` **must be in `target_agents`**.
- If `requires_contract_update` is `true`, `"architect-agent"` **must be placed first** in `target_agents`.
- Scope `"both"` is normalized to `"cross-functional"`.

### 4.2 `RevisionPlan` Output Schema
The revision plan must be a JSON/dictionary structure containing:
```json
{
  "interpretation": "Concise summary of what the user is asking to change.",
  "scope": "frontend | backend | cross-functional | architecture",
  "target_agents": ["frontend-developer", "backend-developer"],
  "requires_contract_update": false,
  "acceptance_criteria": [
    "Verify requested change: ...",
    "Ensure existing regression-free operation across the scope."
  ],
  "updated_requirements": {
    "functional": ["... existing requirements ...", "Revision request: ..."],
    "non_functional": ["..."],
    "constraints": ["..."],
    "assumptions": ["..."],
    "out_of_scope": ["..."],
    "dependencies": ["..."],
    "risks": ["..."]
  },
  "preserved_constraints": ["Preserve existing API contracts and DB schema..."],
  "out_of_scope": ["Changes outside the requested revision feedback."]
}
```

---

## 5. Execution & Output Verification Checklist

Before emitting or publishing state updates, verify:
1. `requirements` contains all 7 keys: `functional`, `non_functional`, `constraints`, `assumptions`, `out_of_scope`, `dependencies`, `risks`.
2. Each requirement value is a list of strings (no empty or null values).
3. `user_stories` contains all required keys: `id`, `actor`, `goal`, `benefit`, `acceptance_criteria`.
4. `mvp_scope` contains items with `phase`, `priority` (strictly MUST, SHOULD, or COULD), and `feature`.
5. Non-PM fields in `ProjectState` are strictly preserved without alteration.
