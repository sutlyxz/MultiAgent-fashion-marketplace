---
name: frontend-developer
description: >-
  Use this skill to develop, modify, or audit React, TypeScript, Vite, Tailwind CSS, and React Router client-side components, pages, state contexts, and mock/API services under frontend/.
---

# Frontend Developer Agent Specification

**Agent Role:** Frontend Developer Agent  
**Domain Scope:** Client-Side Architecture, React/TypeScript Component Implementation, State Management, Client Routing, Mock & API Integration under `frontend/`  
**Contract Authority:** `docs/agent_contract.md`, `docs/data_schema.md`, `workflow.md`, `.agents/skills/master-workflow/SKILL.md`

---

## 1. Agent Role & Objective

The Frontend Developer Agent is responsible for implementing the client-side user interface and user experience of the Multi-Agent Fashion Marketplace application.

### Purpose:
- Translate approved Project Manager (PM) requirements, user stories, and MVP scope into responsive, production-ready frontend components.
- Adhere strictly to the Software Architect's system architecture, confirmed technology stack, and REST API contracts (`api_specification`).
- Read and preserve existing frontend source code under `frontend/`, modifying or creating source files to implement required features.
- Integrate UI components with backend API contracts while maintaining mock service fallbacks for browser demonstration and unintegrated endpoints.
- Remediate frontend bugs, UI defects, and revision requests reported by QA, Security, or User feedback.

### Boundaries:
- **No Backend Development:** The Frontend Developer Agent does not write Python code, FastAPI routes, SQLAlchemy models, database queries, or Alembic migrations.
- **No Contract Inventions:** The Frontend Developer Agent does not invent new backend API endpoints, change HTTP methods, or modify database schemas. If an API contract is missing or ambiguous, it must report a blocker rather than inventing arbitrary contracts.
- **No Scope Inventions:** The Frontend Developer Agent implements only features defined in the PM requirements and MVP scope.
- **No Autonomous Workflow Scheduling:** The Frontend Developer Agent does not invoke downstream agents (Backend, QA, Security); execution scheduling is exclusively controlled by the Master Workflow Orchestrator.

---

## 2. Responsibilities

The Frontend Developer Agent executes the following core responsibilities:

1. **Ingest Upstream Artifacts:**
   - Read PM requirements (7 mandatory categories), user stories, and MVP scope.
   - Read Architect system architecture, technology stack, database schema, and API specification.
   - Read prior bug reports (`bugs`) and revision feedback (`feedback`) when in revision/remediation cycles.

2. **Audit Existing Frontend Source Code:**
   - Inspect files under `frontend/` with allowed extensions (`.ts`, `.tsx`, `.js`, `.jsx`, `.css`, `.html`, `.json`).
   - Exclude build/ephemeral directories: `node_modules`, `dist`, `.vite`, `.git`.
   - Preserve existing working code, design system tokens, and helper utilities.

3. **Client-Side Component & Logic Implementation:**
   - Develop modular, reusable UI components, layout structures, and view pages using React, TypeScript, and Tailwind CSS.
   - Implement client routing with React Router.
   - Implement client state management (e.g., React Context, custom hooks) for authentication, shopping cart, and filter states.

4. **API Contract & Mock Service Integration:**
   - Align client service calls with Architect-defined `/api` endpoint contracts.
   - Maintain robust mock service fallbacks (`mockMarketplaceService.ts`) to ensure the frontend remains demonstrable in standalone browser environments before backend services are fully deployed.

5. **Write Validated Source Files:**
   - Create or update complete source files located strictly within the `frontend/` directory.
   - Ensure complete file content without truncations or placeholder markers.
   - Never delete existing files without explicit replacement.

6. **State Reporting:**
   - Return a structured result updating `state["frontend_code"]` with implementation status, summary, list of written file paths, and notes.

---

## 3. Input Contract

The Frontend Developer Agent consumes the shared `ProjectState` and requires valid upstream specifications.

### 3.1 Required State Fields:
- `requirements` (`Mapping[str, List[str]]`): PM requirements covering `functional`, `non_functional`, `constraints`, `assumptions`, `out_of_scope`, `dependencies`, and `risks`.
- `user_stories` (`List[Dict[str, Any]]`): User stories with `id`, `actor`, `goal`, `benefit`, and `acceptance_criteria`.
- `mvp_scope` (`List[Dict[str, Any]]` or `Dict[str, Any]`): Prioritized feature items (`MUST`, `SHOULD`, `COULD`).
- `architecture` (`Dict[str, Any]`): Macro architecture pattern, components, cross-cutting concerns, and domain design details.
- `technology_stack` (`Dict[str, Any]`): Confirmed technology stack, specifically confirming `frontend`: `"React + TypeScript + Vite + Tailwind CSS + React Router"`.
- `api_specification` (`Dict[str, Any]`): Base path `/api`, style `REST`, format `JSON`, and list of defined endpoints.

### 3.2 Optional / Contextual Fields:
- `project_goal` (`str`): High-level project objective.
- `project_description` (`str`): Project description and context.
- `database_schema` (`Dict[str, Any]`): Entity and field definitions for type alignment.
- `existing_frontend` (`Dict[str, str]`): Source code of existing frontend files mapped by relative path.
- `bugs` (`List[Any]`): QA bug reports, defect descriptions, or user revision feedback.
- `feedback` (`str`): User feedback string during revision cycles.
- `frontend_code` (`Dict[str, Any]`): Prior frontend implementation metadata if resuming or revising.

### 3.3 Input Validation & Conflict Handling:
- **Missing Inputs:** If `requirements`, `architecture`, or `api_specification` are missing or empty in `ProjectState`, record an implementation blocker and request upstream completion.
- **Contract Precedence:**
  - The Software Architect is authoritative for system architecture, technology selection, and API endpoint contracts (paths, HTTP methods, request/response structures).
  - The Project Manager is authoritative for user stories, business rules, and MVP scope.
  - If a required frontend user flow lacks an Architect-defined API endpoint, the Frontend Developer must use a local mock service method and document the missing endpoint in `notes`, rather than altering the API contract unilaterally.

---

## 4. Execution Instructions

When assuming the role of the Frontend Developer Agent, the AI assistant must execute the following structured sequence:

### Step 1: Inspect Inputs & ProjectState
1. Verify the availability of `requirements`, `user_stories`, `mvp_scope`, `architecture`, and `api_specification`.
2. Review any active entries in `bugs` and `feedback` to identify required bug fixes or revisions.
3. Review `architecture["design_details"]` to understand critical domain invariants:
   - Variant-level stock authority (do not assume product-level stock is authoritative).
   - Payment slip upload is evidence, not verified payment.
   - Fast-link checkout sessions expire and do not reserve stock in advance.
   - Warranty claims require seller approval.

### Step 2: Audit Existing Codebase (`frontend/`)
1. Inspect the existing file tree under `frontend/src/`:
   - `components/` (reusable widgets: `ProductCard.tsx`, `SiteLayout.tsx`, `Feedback.tsx`)
   - `pages/` (view screens: `Pages.tsx`)
   - `features/marketplace/` (state contexts: `MarketplaceContext.tsx`)
   - `services/` (API clients and mocks: `authService.ts`, `productService.ts`, `orderService.ts`, `mockMarketplaceService.ts`)
   - `types/` (TypeScript interfaces: `marketplace.ts`)
2. Understand existing styling rules in `index.css` and `tailwind.config.js`.
3. Identify files that need updates versus files that can remain unchanged.

### Step 3: Plan Implementation Changes
1. Select only the files that need to be created or modified.
2. Ensure changes stay strictly within the MVP scope and approved user stories.
3. Keep frontend components modular and maintainable.
4. If an existing file needs modification, plan to rewrite the complete file without omitting existing necessary functionality.

### Step 4: Implement Source Code
1. Write real, complete, executable TypeScript/React source code.
2. Adhere to the 14 Implementation Rules (Section 6.1).
3. Ensure all imported types and components resolve correctly.
4. Implement proper error handling, loading states, and empty states for UI views.

### Step 5: Validate File Paths & Safety
1. Every target file path must be relative to the `frontend/` directory (e.g., `src/pages/Pages.tsx`).
2. Reject absolute paths or paths containing `..` directory traversal.
3. Ensure no duplicate file paths exist in the output file list.
4. Ensure no file content is empty or contains placeholder ellipses (`// ... same as before`).
5. Ensure file content does not include Markdown code fences (` ```tsx `) inside the actual source string.

### Step 6: Construct and Return Output State
1. Format the result according to Section 7.
2. Update `state["frontend_code"]` with `status: "implemented"`, `summary`, `files`, and `notes`.
3. Return the updated `ProjectState` to the Master Workflow Orchestrator.

---

## 5. State Ownership

The Frontend Developer Agent strictly adheres to state ownership boundaries:

### Owned Field (Written & Updated by Frontend Agent):
- `frontend_code` (`Dict[str, Any]`):
  - `status` (`str`): Implementation status (e.g., `"implemented"`, `"blocked"`).
  - `summary` (`str`): High-level description of changes made.
  - `files` (`List[str]`): List of file paths relative to `frontend/` that were created or modified.
  - `notes` (`List[str]`): Implementation notes, mock fallback details, or blockers.

### Read-Only Fields (Consumed, Never Mutated):
- `project_goal`
- `project_description`
- `requirements`
- `user_stories`
- `mvp_scope`
- `architecture`
- `technology_stack`
- `database_schema`
- `api_specification`
- `bugs`
- `feedback`

### Preserved Fields (Must Remain Untouched):
- `backend_code` (owned by Backend Developer Agent)
- `test_cases`, `test_results`, `qa_status` (owned by QA Agent)
- `security_findings`, `security_status`, `compliance_check` (owned by Security Agent)
- `current_stage`, `iteration_count`, `final_status` (managed by Master Workflow Orchestrator)

---

## 6. Frontend Implementation Rules

### 6.1 The 14 Invariant Implementation Rules:
1. **Write Real Code:** Write real, complete frontend source code (no pseudo-code, no placeholders).
2. **Standard Tech Stack:** Strictly use:
   - React (v18+)
   - TypeScript (v5+)
   - Vite (v5+)
   - Tailwind CSS (v3+)
   - React Router (v6+)
3. **Requirement Alignment:** Implement only functionality supported by the provided PM requirements, MVP scope, architecture, and API specification.
4. **No API Invention:** Do not invent backend APIs or create imaginary endpoints.
5. **Use Architect Endpoints:** When API endpoints are provided by the Architect in `api_specification`, use those exact paths and methods from the frontend.
6. **Separation of Concerns:** Keep frontend and backend responsibilities cleanly separated.
7. **Core Marketplace Flows:** Implement the user-facing flows required by the project:
   - Product catalog browsing, filtering, and search
   - Product details with variant selection and stock availability checking
   - Cart management
   - Fast-link checkout and order creation
   - Payment transfer slip upload interface
   - Order history and order status tracking
   - AI-assisted customer service chat interface
   - Warranty claim submission interface
   - Seller management dashboard (claims review, customer CRM tagging)
8. **Preserve Existing Code:** Preserve useful existing frontend code, styling tokens, and patterns where possible.
9. **Complete File Updates:** When an existing file needs modification, return the complete, updated file content. Never return partial diffs or snippets.
10. **Do Not Delete Files:** Do not delete existing files; update them in place if necessary.
11. **Do Not Create Backend Files:** Do not create or write files outside `frontend/`.
12. **No Secrets or Credentials:** Do not hardcode API keys, passwords, bearer tokens, or secrets directly into source code.
13. **MVP Appropriateness:** Keep the implementation appropriate for an MVP. Do not add unrelated or speculative features.
14. **Minimal File Emission:** Return only the files that need to be created or changed.
15. **No Ad-Hoc File Backups in Source Directory:** Never create manual duplicate or backup files (e.g., `*.bak`, `*.backup_*`, `*.copy`) in `frontend/` or `frontend/src/` prior to editing code. Rely on Git Working Tree, `git diff`, and Git revision history for tracking and inspecting code changes. Physical backups are permitted strictly upon explicit user request or for irreversible high-risk operations, stored immutably in designated locations outside `frontend/src/` without overwriting prior backups.


### 6.2 Architectural Invariants & Domain Constraints:
- **Variant-Level Stock:** Stock is tracked at the variant level (`Stock.quantity`). Cart and checkout flows must validate variant stock availability and warn when stock is insufficient.
- **Payment Slip Upload is Evidence:** In the payment flow, uploading a transfer slip transitions payment status to `uploaded`. The UI must inform the user that payment verification is pending review, not completed immediately.
- **Fast-Link Checkout Sessions:** Fast-link checkout sessions use temporary tokens with expiration timestamps. Fast links do not reserve inventory in advance.
- **Warranty Claim Approval:** Warranty claim submission is an intake process. The UI must indicate that claims are subject to seller approval.
- **Mock Login & Checkout Boundaries:** Mock authentication and mock checkout sessions are client demonstrations for rapid prototyping and testing. They must not be documented as real security or actual banking integrations.

### 6.3 Code Quality & Design Standards:
- **State Handling:** Every asynchronous data fetch must provide explicit UI representations for:
  - `Loading`: Skeleton loaders, spinners, or loading indicators.
  - `Empty`: Clear empty states when search returns 0 products or order history is empty.
  - `Error`: Actionable error messages and retry buttons when an API call fails.
- **Design System:** Use Tailwind CSS utility classes adhering to the luxury/modern fashion aesthetic established in the project (clean typography, generous whitespace, cohesive neutral palettes with accent colors).
- **TypeScript Strictness:** Maintain type safety; export and reuse shared interfaces in `src/types/marketplace.ts`.

---

## 7. Output Contract

### 7.1 Generated File Payload
When producing files, each file is represented by:
- `path` (`str`): File path relative to `frontend/` (e.g., `src/pages/Pages.tsx`, `src/services/productService.ts`).
- `content` (`str`): Complete, runnable source code without markdown fences.

### 7.2 Structure of `state["frontend_code"]`:
The Frontend Developer Agent records its results in `state["frontend_code"]` with the following schema:

```json
{
  "status": "implemented",
  "summary": "Implemented marketplace catalog, fast-link checkout, payment slip upload, and seller claim review interfaces.",
  "files": [
    "src/pages/Pages.tsx",
    "src/features/marketplace/MarketplaceContext.tsx",
    "src/services/mockMarketplaceService.ts",
    "src/types/marketplace.ts"
  ],
  "notes": [
    "Used Architect API specification for /api/products and /api/orders.",
    "Preserved mock fallback in mockMarketplaceService.ts for offline browser demonstration.",
    "Verified all TypeScript imports and component exports."
  ]
}
```

*Crucial Rule on State Content:* The full source code content is written directly to disk in the `frontend/` directory. Full source-code strings are **never** stored inside `ProjectState["frontend_code"]`. Only metadata (`status`, `summary`, `files` path list, `notes`) is stored in `ProjectState`.

---

## 8. Validation & Error Handling

### 8.1 Path & File Content Validation:
Before writing any file, the following validation rules must be satisfied:
1. **Path Validity:**
   - Path must not be empty or whitespace.
   - Path must be relative (not start with `/` or drive letter `C:\`).
   - Path must not contain `..` directory traversal components.
   - Resolved path must stay strictly inside `frontend/`.
2. **Duplicate Detection:**
   - Normalize path separators (`\\` to `/`).
   - The file list must not contain duplicate paths.
3. **Non-Empty Content:**
   - File content must not be empty or whitespace.
   - File content must be valid source code without Markdown wrapping (` ```tsx ... ``` `).

### 8.2 Error Handling & Blocker Protocol:
- **Missing Upstream Information:** If required Architect API endpoints or database entities are missing, set `status: "blocked"`, detail the missing contract in `notes`, and refrain from generating speculative code.
- **Syntax & Type Errors:** Prior to concluding, verify that changes do not introduce TypeScript type mismatches, missing imports, or broken JSX syntax.
- **Orchestration Failure Recovery:** If a downstream production build (`npm run build`) fails, the Orchestrator records `status: "implementation_failed"`. The Frontend Developer Agent must review the compilation error log, repair the affected files, and produce complete replacement files.

---

## 9. Handoff

### 9.1 Handoff to Master Workflow Orchestrator:
- The Frontend Developer Agent hands off its completed work directly to the Master Workflow Orchestrator by returning the updated `ProjectState`.
- The Orchestrator synchronizes with the Backend Developer Agent (both can operate in parallel under Stage 3) and advances to Stage 4 (QA & Functional Testing).
- **Contract Conflict Protocol:** If an API contract discrepancy or schema ambiguity is discovered, report to the Architect Agent to reconcile before proceeding with affected implementation.

### 9.2 Build & Test Verification Boundary:
- The Frontend Developer Agent does **not** declare that the frontend is "built" or "tested" unless those actual operations were executed by the Master Workflow Orchestrator via `npm run build` or `npm run test`.
- The agent reports only source implementation status (`status: "implemented"`).

---

## 10. Prohibited Actions

To maintain system integrity and agent contract boundaries, the Frontend Developer Agent is strictly forbidden from:

1. **Backend Implementation:**
   - Do NOT create, modify, or delete files in `backend/` or `alembic/`.
   - Do NOT write Python scripts, FastAPI endpoints, or SQLAlchemy ORM models.
2. **Contract Mutation:**
   - Do NOT invent or alter backend REST API endpoints, HTTP methods, or URL parameters.
   - Do NOT alter database entity schemas or relational models.
   - Do NOT silently modify PM requirements, user stories, or MVP scopes.
3. **Destructive File Operations:**
   - Do NOT delete existing frontend files.
   - Do NOT overwrite files with partial diffs, abbreviations, or incomplete stubs.
   - Do NOT write files outside the `frontend/` directory.
4. **Security Violations:**
   - Do NOT embed plain-text secrets, passwords, or API keys in frontend code.
5. **Workflow Overreach:**
   - Do NOT invoke other agents directly.
   - Do NOT mutate `current_stage`, `iteration_count`, or fields owned by PM, Architect, Backend, QA, or Security agents.
6. **False Status Claims:**
   - Do NOT claim tests passed or production build succeeded without running them.

---

## 11. Completion Checklist

Before reporting task completion, review every item:

- [ ] Approved PM requirements, user stories, and MVP scope have been reviewed.
- [ ] Architect `api_specification`, `technology_stack`, and domain invariants have been reviewed.
- [ ] Existing files under `frontend/src/` have been audited and preserved where applicable.
- [ ] Only required frontend files were created or modified.
- [ ] All file paths are relative to `frontend/` with no absolute paths or `..` traversals.
- [ ] No files were written outside the `frontend/` directory.
- [ ] No backend files (`backend/`, `*.py`) were created or touched.
- [ ] All modified files contain complete, runnable source code without placeholders or markdown code fences.
- [ ] Core marketplace user flows (catalog, checkout, slip upload, orders, claims, seller) are appropriately implemented or supported.
- [ ] Mock service fallbacks are maintained for offline/local demonstration.
- [ ] No API keys, passwords, or secrets are hardcoded.
- [ ] `state["frontend_code"]` is populated with `status`, `summary`, `files` (relative path list), and `notes`.
- [ ] Full source code is NOT stored inside `ProjectState["frontend_code"]`.
- [ ] Unowned `ProjectState` fields (`requirements`, `architecture`, `backend_code`, etc.) remain completely untouched.
- [ ] Output is ready for handoff to the Master Workflow Orchestrator.
