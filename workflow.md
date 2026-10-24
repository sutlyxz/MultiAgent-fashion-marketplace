# Clothify Luxury Fashion Marketplace: Multi-Agent Workflow Specification

**Workflow Authority:** Antigravity Coordinator Specification  
**Architecture Model:** Antigravity-Orchestrated Markdown-Based Sub-Agents  
**Contract Baseline:** `workflow.md` (Self-Contained Markdown State), `.agents/skills/*/SKILL.md`, `docs/agent_contract.md`, `docs/data_schema.md`

---

## 1. Executive Overview & Workflow Philosophy

This document defines the central operational workflow for engineering, extending, and auditing the Clothify Multi-Agent Fashion Marketplace.

### The Antigravity Execution Model:
1. **Antigravity as Primary Coordinator:** Antigravity acts as the central orchestrator and executive intelligence, guided by `.agents/skills/master-workflow/SKILL.md`. It governs phase transitions, validates state contracts, performs handoffs, monitors retry budgets, and enforces human-in-the-loop gates.
2. **Native Skill Packages as Operational Directives:** The files in `.agents/skills/<skill-name>/SKILL.md` are **cognitive instruction sets and Antigravity native skill packages**, not standalone executable binaries or autonomous daemon processes.
3. **Mandatory Specification Inspection:** Antigravity must explicitly read and apply the designated Native Skill package before initiating any stage of work.
4. **Context Passing & Verification:** Antigravity explicitly extracts inputs from the current project context, injects them into the agent prompt/role, and inspects actual outputs on disk before transitioning to downstream stages.
5. **No Assumed Runtime Capabilities:** A documented workflow step does not imply that background threads, automated daemon scheduling, or parallel compilation exist unless explicitly supported and executed by tools in the environment. Where capabilities are absent, Antigravity executes tasks sequentially and transparently reports limitations.

---

## 2. Agent Ecosystem & Self-Contained Markdown Workflow Record

The primary operational workflow is governed directly by Antigravity using Markdown instructions rather than an executable Python TypedDict. Throughout a run, Antigravity maintains a lightweight, structured **Markdown Workflow Record** (in chat context and summary artifacts):

- **Task Identification:** Task ID/name, timestamp, and task operational mode (`IMPLEMENTATION` vs `READ_ONLY` / `DOCUMENTATION_REVIEW`).
- **Current Stage:** Active stage in the 10-stage engineering cycle (Stages 1 through 10).
- **Task Objective & Scope:** Clear definition of goal, scope boundaries (`"architecture"`, `"frontend"`, `"backend"`, or `"cross-functional"`), and deliverables.
- **Relevant Constraints:** Active safety rules (e.g., read-only mode, preserved branches, untouched backups).
- **Files Inspected / Changed:** Explicit lists of files read and modified.
- **Validation Results:** Terminal execution records, test commands run, exit codes, pass/fail metrics.
- **QA & Security Findings:** Structured defect records, severity, affected components, defect ownership (`agent: "frontend" | "backend"`).
- **Retry Count & Budget:** Remediation attempt counter (`iteration_count`) and remaining retry budget (max 3 cycles).
- **Human Approval Status:** Gate status (`"PENDING"`, `"APPROVED"`, `"REVISE"`, or `"CANCELLED"`).
- **Final Outcome & Handoff:** Summary of completed deliverables, evidence, and completion report.

This checklist-style record avoids coupling the Antigravity workflow to Python runtime dependencies or assuming automatic JSON persistence.

### Agent Roles & Skill Directives:

| Agent Role | Skill Directive | Primary Output Fields in Workflow Record | Source Artifacts |
| :--- | :--- | :--- | :--- |
| **Master Orchestrator** | [`.agents/skills/master-workflow/SKILL.md`](file:///.agents/skills/master-workflow/SKILL.md) | `current_stage`, `iteration_count`, `final_status` | Workflow orchestration & gate evaluation |
| **Project Manager (PM)** | [`.agents/skills/pm-agent/SKILL.md`](file:///.agents/skills/pm-agent/SKILL.md) | `requirements`, `user_stories`, `mvp_scope`, `revision_plan` | State dictionaries / checklists |
| **Software Architect** | [`.agents/skills/architect-agent/SKILL.md`](file:///.agents/skills/architect-agent/SKILL.md) | `architecture`, `technology_stack`, `database_schema`, `api_specification` | Architecture specs & schema definitions |
| **Frontend Developer** | [`.agents/skills/frontend-developer/SKILL.md`](file:///.agents/skills/frontend-developer/SKILL.md) | `frontend_code` (metadata / touched files) | `frontend/src/*`, `frontend/package.json` |
| **Backend Developer** | [`.agents/skills/backend-developer/SKILL.md`](file:///.agents/skills/backend-developer/SKILL.md) | `backend_code` (metadata / touched files) | `backend/app/*`, `backend/alembic.ini` |
| **QA & Software Tester** | [`.agents/skills/qa-agent/SKILL.md`](file:///.agents/skills/qa-agent/SKILL.md) | `test_cases`, `test_results`, `bugs`, `qa_status` | Test logs, pytest, build results |
| **Security & Compliance** | [`.agents/skills/security-agent/SKILL.md`](file:///.agents/skills/security-agent/SKILL.md) | `security_findings`, `security_status`, `compliance_check` | Threat logs, vulnerability tickets |

---

## 3. The 10-Stage Standard Engineering Workflow

```
[Stage 1: Intake & Clarification]
               │
               ▼
   [Stage 2: PM Agent]
               │
               ▼
[Stage 3: Architect Agent]
               │
               ▼
[Stage 4: Implementation Planning]
               │
               ▼
[Stage 5: Developer Implementation] ◄─── (Remediation Loop)
    ├── 5A: Frontend Developer           │
    └── 5B: Backend Developer            │
               │                         │
               ▼                         │
 [Stage 6: Integration Review]           │
               │                         │
               ▼                         │
      [Stage 7: QA Gate] ────────────────┤ (QA FAIL)
               │ (QA PASS)               │
               ▼                         │
   [Stage 8: Security Gate] ─────────────┘ (SEC FAIL)
               │ (SEC PASS)
               ▼
 [Stage 9: Human Review & Approval]
               │ (Approved)
               ▼
[Stage 10: Final Handoff & Report]
```

---

### Stage 1: Request Intake & Clarification
- **Purpose:** Analyze user intent, extract business objectives, identify change scope, and resolve immediate ambiguities before activating agents.
- **Inputs:** User prompt, current repository state, optional revision feedback.
- **Specification:** Antigravity orchestrator guidelines.
- **Expected Outputs:** Well-defined `project_goal`, `project_description`, scope classification (`"architecture"`, `"frontend"`, `"backend"`, or `"cross-functional"`), and task operational mode (`"IMPLEMENTATION"` vs. `"READ_ONLY"` / `"DOCUMENTATION_REVIEW"`).
- **Validation Before Handoff:** Confirm project goal, description, and task operational mode are non-empty and non-conflicting.
- **Failure Handling:** If user intent is contradictory or underspecified, halt and ask clarifying questions directly before touching code.
- **Condition to Proceed:** Clear, non-conflicting goal and operational mode agreed upon with user.

---

### Stage 2: Project Manager (PM) Agent
- **Purpose:** Deconstruct project goals into structured functional requirements, user stories with acceptance criteria, and prioritized MVP scope.
- **Inputs:** `project_goal`, `project_description`, optional `revision_plan` or `feedback`.
- **Specification:** [`.agents/skills/pm-agent/SKILL.md`](file:///.agents/skills/pm-agent/SKILL.md).
- **Expected Outputs:**
  - `requirements`: Exactly 7 categories (`functional`, `non_functional`, `constraints`, `assumptions`, `out_of_scope`, `dependencies`, `risks`).
  - `user_stories`: Structured list containing `id`, `actor`, `goal`, `benefit`, `acceptance_criteria`.
  - `mvp_scope`: Feature list with `phase`, `priority` (`MUST`, `SHOULD`, `COULD`), and `feature`.
- **Validation Before Handoff:** Ensure all 7 requirement categories exist, all User Stories have explicit acceptance criteria, and priorities are valid.
- **Failure Handling:** Re-evaluate requirements; request human clarification if business trade-offs cannot be resolved deterministically.
- **Condition to Proceed:** Requirements and MVP scope fully validated and recorded in state.

---

### Stage 3: Software Architect Agent
- **Purpose:** Translate PM requirements into macro system architecture, confirm technology stack, design database schemas, and define authoritative REST API contracts.
- **Inputs:** `requirements`, `user_stories`, `mvp_scope`, `project_goal`, `project_description`.
- **Specification:** [`.agents/skills/architect-agent/SKILL.md`](file:///.agents/skills/architect-agent/SKILL.md).
- **Expected Outputs:**
  - `architecture`: `system_pattern` ("layered"), components, cross-cutting concerns, and 7 mandatory `design_details` domains.
  - `technology_stack`: 10 confirmed categories (`"confirmed"` status with justifications).
  - `database_schema`: Canonical 14 entities with field roles and relationships.
  - `api_specification`: Base path `/api`, REST/JSON format, and 21 mandatory endpoints.
- **Validation Before Handoff:** Check presence of all 10 tech items, 14 entities, 21 endpoints, and required design detail keywords (atomic stock decrement, payment slip evidence state, expiring fast-link checkout, seller claim approval).
- **Condition to Proceed:** Architectural contracts complete and immutable. Work proceeds **immediately** to Developer Implementation without a mandatory intermediate human architecture approval pause. (If an unresolvable contradiction or critical information gap arises, report a Blocker and halt for human decision).

---

### Stage 4: Implementation Planning & Dependency Analysis
- **Purpose:** Establish dependency graph between Frontend and Backend, determine file change boundaries, and select sequential vs. parallel execution track.
- **Inputs:** `api_specification`, `database_schema`, `frontend_code`, `backend_code`.
- **Specification:** Antigravity coordination directives.
- **Expected Outputs:** Work breakdown identifying files to create/modify under `frontend/` and `backend/`.
- **Execution Track Selection:**
  - **Sequential Track (Default & Recommended):** Run Frontend Developer, then Backend Developer (or vice-versa). This eliminates merge conflicts, ensures predictable tool invocations, and avoids context saturation.
  - **Parallel Track (Conditional):** Allowed *only* if Antigravity delegates work to independent sub-agents with non-overlapping file write paths.
- **Condition to Proceed:** File targets confirmed and execution sequence selected.

---

### Stage 5: Developer Implementation
#### 5A: Frontend Developer Agent
- **Purpose:** Implement client-side UI, components, routing, and mock/API integration under `frontend/`.
- **Inputs:** `requirements`, `user_stories`, `mvp_scope`, `architecture`, `api_specification`, `existing_frontend`.
- **Specification:** [`.agents/skills/frontend-developer/SKILL.md`](file:///.agents/skills/frontend-developer/SKILL.md).
- **Expected Outputs:** Complete source files under `frontend/` (`.tsx`, `.ts`, `.css`), updated `state["frontend_code"]` (`status: "implemented"`, `summary`, `files`, `notes`).
- **Validation Before Handoff:** Validate file paths stay inside `frontend/` (no absolute paths or `..`), no empty files, no code fences inside files, no hardcoded secrets.

#### 5B: Backend Developer Agent
- **Purpose:** Implement FastAPI routers, SQLAlchemy models, database migrations, and business logic under `backend/`.
- **Inputs:** `requirements`, `user_stories`, `architecture`, `database_schema`, `api_specification`, `existing_backend`.
- **Specification:** [`.agents/skills/backend-developer/SKILL.md`](file:///.agents/skills/backend-developer/SKILL.md).
- **Expected Outputs:** Complete source files under `backend/` (`.py`, `.sql`, `.ini`), updated `state["backend_code"]` (`status: "implemented"`, `summary`, `files`, `notes`).
- **Validation Before Handoff:** Validate file paths stay inside `backend/`, implement strictly Architect-specified endpoints and 14 entities, enforce atomic stock decrement post-slip verification, no hardcoded secrets.

> [!CRITICAL]
> **Strict Status Reporting Rule:** The status `"implemented"` must **never** be used to describe code or components that were not actually implemented or written to disk. In `READ_ONLY` or `DOCUMENTATION_REVIEW` tasks where no source code modifications take place, developer reporting must explicitly record `"reviewed_no_code_changes"` or `"not_applicable"`, rather than falsely claiming `"implemented"`.

---

### Stage 6: Integration Review (Synchronization Join)
- **Purpose:** Verify compatibility between Frontend client calls and Backend API contracts before entering testing gates.
- **Inputs:** Generated `frontend_code["files"]` and `backend_code["files"]`.
- **Specification:** Cross-agent compatibility contract (`docs/agent_contract.md`).
- **Expected Outputs:** Joint verification confirming API routes, payloads, and parameter formats match.
- **Validation Before Handoff:** Ensure neither agent mutated unowned fields.
- **Condition to Proceed:** Implementation join complete (`current_stage = "IMPLEMENTATION_AGENTS_COMPLETE"`).

---

### Stage 7: QA & Software Testing Gate
- **Purpose:** Execute independent software quality assurance, build verification, and automated testing.
- **Inputs:** `requirements`, `user_stories`, `frontend_code`, `backend_code`, `api_specification`.
- **Specification:** [`.agents/skills/qa-agent/SKILL.md`](file:///.agents/skills/qa-agent/SKILL.md).
- **Execution Actions:**
  - Execute frontend build check: `npm run build` (or `tsc --noEmit`).
  - Execute backend automated test suite: `pytest backend/tests`.
  - Validate core business invariants (variant stock authority, slip upload as evidence, fast-link expiration, seller claim review).
- **Expected Outputs:**
  - `test_cases`: Traceability list mapping User Stories to tests.
  - `test_results`: Quantitative summary (`checks_run`, `checks_passed`, `checks_failed`).
  - `bugs`: Defect tickets containing `id`, `agent` (`"frontend"` | `"backend"`), `description`, `severity`, reproduction steps.
  - `qa_status`: Verdict (`PASS`, `FAIL`, or `BLOCKED`).
- **Gate Evaluation:**
  - **Read-Only / Documentation Review Tasks:**
    - If defects, stale claims, or documentation discrepancies are discovered, record and report all findings in `test_cases` and `bugs`.
    - **Do NOT** automatically dispatch defects to Developer Agents for implementation or file editing.
    - Route the evaluation directly to **Stage 9 (Human Review)** with verified findings.
    - Antigravity must wait for explicit user approval before expanding task scope to include file modifications.
  - **Implementation Tasks:**
    - If `qa_status == "PASS"` ➔ Proceed to **Stage 8 (Security Gate)**.
    - If `qa_status == "FAIL"` ➔ Dispatch to **Remediation Loop (Section 5)** for developer code repair.
    - If `qa_status == "BLOCKED"` ➔ Escalate immediately to **Stage 9 (Human Review)**.

---

### Stage 8: Security & Compliance Gate
- **Purpose:** Independent vulnerability assessment, RBAC audit, payment integrity verification, and secret detection.
- **Inputs:** `requirements`, `architecture`, `api_specification`, `database_schema`, `frontend_code`, `backend_code`.
- **Specification:** [`.agents/skills/security-agent/SKILL.md`](file:///.agents/skills/security-agent/SKILL.md).
- **Execution Timing:** Security review executes **only after Stage 7 (QA Gate) passes**.
- **Execution Actions:**
  - Static audit of authentication (`bcrypt`, JWT `HS256`, token expiration).
  - RBAC verification (`buyer` vs `seller` access control, IDOR prevention on claims/orders).
  - Payment & stock integrity audit (atomic decrement, slip upload evidence boundary).
  - File upload safety checks (MIME validation, size limits, path traversal defenses).
  - Secret scanning (ensure no cleartext keys in code, `.env` excluded).
- **Expected Outputs:**
  - `security_findings`: Vulnerability tickets containing `id`, `agent` (`"frontend"`, `"backend"`, or `"both"`), `severity`, `description`.
  - `security_status`: Verdict (`PASS`, `FAIL`, or `BLOCKED`).
  - `compliance_check`: Structured compliance summary.
- **Gate Evaluation:**
  - **Read-Only / Documentation Review Tasks:**
    - If vulnerabilities, secret exposures, or sensitive disclosures are identified, record findings in `security_findings` and route directly to **Stage 9 (Human Review)** without invoking Developer Agents.
  - **Implementation Tasks:**
    - If `security_status == "PASS"` ➔ Proceed to **Stage 9 (Human Review)**.
    - If `security_status == "FAIL"` ➔ Dispatch to **Remediation Loop (Section 5)**.
    - If `security_status == "BLOCKED"` ➔ Escalate immediately to **Stage 9 (Human Review)**.

---

### Stage 9: Human Review & Approval
- **Purpose:** Present holistic verification evidence, open risks, and acceptance recommendations to the human user for formal sign-off.
- **Mandatory Trigger Conditions:**
  1. Completion of full workflow with `qa_status == "PASS"` and `security_status == "PASS"`.
  2. Retry budget exhaustion (3 repair attempts reached).
  3. Any `BLOCKED` status in QA or Security gates.
  4. Discovery of high-risk or destructive architectural changes.
  5. Completion of QA or Security review on a `READ_ONLY` or `DOCUMENTATION_REVIEW` task containing discovered defects or discrepancies (requires explicit user approval before expanding task scope to file modifications).
- **Expected Outputs:** Human decision (`"APPROVED"`, `"REVISE"`, or `"CANCELLED"`).
- **Rule:** Agent recommendations **never** replace human approval.

---

### Stage 10: Final Handoff & Completion Report
- **Purpose:** Deliver finished codebase, summarize modified files, report testing evidence, and conclude run.
- **Outputs:** Comprehensive Markdown summary delivered in chat.

---

## 4. Defect Schemas & State Compatibility

To maintain strict contract compatibility with `docs/data_schema.md` and `docs/agent_contract.md`, defects must adhere to the standardized schema:

```json
{
  "id": "BUG-001 (or SEC-001)",
  "agent": "frontend | backend | both",
  "description": "Clear description of defect or vulnerability.",
  "severity": "Critical | High | Medium | Low | Info",
  "title": "Concise defect title",
  "status": "OPEN | IN_PROGRESS | READY_FOR_RETEST | VERIFIED",
  "affected_component": "frontend/src/... or backend/app/...",
  "related_requirement": "US-001 to US-008",
  "reproduction_steps": ["1. Step one", "2. Step two"],
  "expected_behavior": "What should have happened",
  "actual_behavior": "What actually occurred",
  "evidence": "Log snippet, test failure trace, or file:line reference",
  "recommended_fix": "Actionable guidance for the developer"
}
```

*Routing Requirement:* The field `agent` is mandatory for developer routing. The orchestrator routes remediation based on `bugs[-1].get("agent")` and `findings[-1].get("agent")`.

### 4.1 Appropriate Defect Ownership Rules
- **Code Defects:** Assign `agent: "frontend"` for client UI/routing issues, or `agent: "backend"` for API/database issues.
- **Documentation Defects:** Assign ownership to the Agent responsible for the specific documentation asset or architectural authority:
  - System architecture documentation discrepancies (e.g., `README.md` folder structure, Tech Stack, 14 DB entities, 21 endpoints) belong to `architect_agent` (or `pm_agent` for scope/requirements).
  - Do **NOT** assign a README wording issue to the Backend Agent solely because the text mentions a backend technology! Ownership is determined by who owns the document/concept, not superficial keyword mentions.
  - In `READ_ONLY` tasks, documentation defects route directly to Stage 9 (Human Review) and do not trigger erroneous developer code modifications.
- **Contract Compatibility:** Always preserve baseline contract fields (`id`, `agent`, `description`, `severity`). Additional metadata (`title`, `reproduction_steps`, `evidence`, `recommended_fix`) enhances detail without breaking existing schema consumers.

---

## 5. Bounded Remediation & Escalation Rules

```
                      ┌────────────────────────────────────────┐
                      ▼                                        │
[QA/Sec Failure] ──► [Inspect Agent Field]                     │
                           │                                   │
              ┌────────────┴────────────┐                      │
              ▼                         ▼                      │
     [agent == "frontend"]     [agent == "backend"]            │
              │                         │                      │
              ▼                         ▼                      │
     [Frontend Agent Fix]      [Backend Agent Fix]             │
              │                         │                      │
              └────────────┬────────────┘                      │
                           ▼                                   │
                 [Increment Iteration]                         │
                           │                                   │
               (iteration_count <= 3)                          │
               ┌───────────┴───────────┐                       │
       (Yes)   ▼               (No)    ▼                       │
    [Re-run QA Gate]              [Halt & Human Review]        │
           │                                                   │
     (QA Fails) ───────────────────────────────────────────────┘
```

1. **Retry Budget:** Exactly **3 remediation cycles** are permitted per issue or issue group.
2. **Iteration Counter:** Antigravity tracks attempts using `state["iteration_count"]` (or task session record).
3. **Remediation Routing for Implementation Tasks:**
   - If `agent == "frontend"` ➔ Dispatch repair to Frontend Developer Agent.
   - If `agent == "backend"` ➔ Dispatch repair to Backend Developer Agent.
   - If `agent == "both"` ➔ Dispatch repair sequentially to Frontend then Backend Developer Agent.
4. **Bypass for Read-Only Tasks:**
   - Read-Only and Documentation Review tasks **bypass** the automated developer remediation loop entirely. Discovered defects are recorded and routed directly to **Stage 9 (Human Review)** for user decision.
5. **Mandatory Post-Fix QA Re-Verification:**
   - Even when fixing a Security defect, execution **must return to Stage 7 (QA Gate)** first to confirm that the security fix did not cause functional regressions.
   - Once QA passes, execution returns to Stage 8 (Security Gate) to verify vulnerability mitigation.
6. **Budget Exhaustion Protocol:**
   - If defects remain unresolved after 3 attempts:
     - Immediately halt automated agent dispatch.
     - Set `final_status = "NEEDS_HUMAN_REVIEW"`.
     - Compile an Escalation Report detailing all attempted fixes, reproduction evidence, and root-cause blockers.

---

## 6. File Safety & Scope Control Protocol

Before modifying any project file, Antigravity must execute this 5-point safety check:
1. **Target Authorization:** Confirm the file is explicitly authorized for modification under the current task boundary.
2. **Pre-Modification Inspection:** Read the existing file in full to understand dependencies and avoid overwriting unrelated code.
3. **No Unrelated Refactoring:** Confine changes strictly to requested features or verified bug fixes.
4. **Complete File Delivery:** Developer agents must deliver complete file content. No truncated stubs, partial diffs, or `// ... rest of code` markers.
5. **Post-Modification Verification:** Inspect Git status and file contents immediately after writing to confirm no unintended files were modified.

### 6.1 No-Adhoc-File-Backups & Version Control Protocol

1. **No Ad-Hoc Backups in Source Directories:** Never create ad-hoc duplicate or backup files (such as `*.bak`, `*.backup_*`, `*.old`, `*.copy`) inside application source directories (`frontend/src/`, `backend/app/`, etc.) during routine code modifications.
2. **Git as Authoritative Rollback & Diff Engine:** Rely strictly on Git Working Tree, `git diff`, and Git revision history for inspecting, validating, or reverting code changes. Do not copy files to run `--no-index` diff comparisons.
3. **High-Risk Backup Exceptions (User Request or Irreversible Operations):** Creating a physical file backup is permitted strictly when:
   - Explicitly requested by the user.
   - Performing high-risk, irreversible operations where git rollback is insufficient (e.g., destructive production database migrations or bulk schema alterations).
4. **Designated Backup Storage & Immutability:** When a high-risk backup is authorized, store it exclusively in designated locations (`backups/` or artifact `scratch/`), never mixed into application source folders. Existing backup files must never be overwritten; use distinct timestamps or version identifiers (e.g., `backups/db_backup_YYYYMMDD_HHMMSS.dump`).
5. **Code & Data Preservation Invariant:** This rule does not conflict with code preservation or data loss prevention: all existing working implementations, test fixtures, and valid backups remain strictly preserved.

---


## 7. Python Workflow Integration & Runtime Capabilities Gap

| Capability | Python Runtime Implementation (`workflow/graph.py` / `orchestrator.py`) | Antigravity Markdown Coordination | Operational Reality |
| :--- | :--- | :--- | :--- |
| **Workflow State Container** | `ProjectState` TypedDict in memory | Structured JSON context in chat / prompt | Antigravity passes state context explicitly |
| **State Persistence** | `RunStore` atomic writes to `.agent_runs/*.json` | Session conversation context & project files | Disk persistence requires explicit file save; Markdown instructions do not automatically save JSON run records |
| **Routing Enforcement** | LangGraph conditional edges (`_route_qa`, `_route_security`) | Antigravity reasoning & handoff contracts | Antigravity coordinates based on `agent` field |
| **Retry Counter** | Incremented by graph nodes (`_advance_iteration`) | Tracked in workflow record (`iteration_count`) | Maintained within the active session |
| **Test Execution** | Subprocess commands (`npm run build`, `pytest`) | Antigravity terminal execution tool | Requires real command execution by Antigravity |
| **Parallel Execution** | LangGraph asyncio/thread pooling for [Frontend, Backend] | Sequential execution by default in single chat | Antigravity coordinates sequentially to prevent merge conflicts |

> [!NOTE]
> **Operational Status of Legacy Python Components:**  
> `workflow.md`, `.agents/skills/*/SKILL.md`, and `.agents/skills/master-workflow/SKILL.md` represent the authoritative operational workflow for Antigravity. The legacy Python multi-agent prototype files (`main.py`, `workflow/`, `agents/`, `models/state.py`) have been retired in favor of native Antigravity skill packages. CLI capabilities such as persistent JSON run state and command-line resume are not automatically provided by Markdown instructions alone; Antigravity provides orchestration directly in the development session.

---

## 8. Completion & Sign-Off Checklist

Before completing an end-to-end development cycle, verify:
- [ ] User request and scope clarification recorded in Stage 1.
- [ ] PM requirements, user stories, and MVP scope validated in Stage 2.
- [ ] Architect tech stack (10 items), database schema (14 entities), and API spec (21 endpoints) confirmed in Stage 3.
- [ ] Frontend and Backend implementations completed under `frontend/` and `backend/` in Stage 5.
- [ ] Integration review confirmed contract alignment in Stage 6.
- [ ] QA Gate executed real test suites and rendered `qa_status: "PASS"` in Stage 7.
- [ ] Security Gate completed threat audit and rendered `security_status: "PASS"` in Stage 8.
- [ ] Human Review received verified evidence and provided confirmed user approval in Stage 9.
- [ ] Final handoff report prepared and delivered to the user in Stage 10.
