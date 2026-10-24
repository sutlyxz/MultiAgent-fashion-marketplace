---
name: master-workflow
description: Orchestrates the multi-agent software engineering lifecycle for Clothify Marketplace across PM, Architect, Frontend, Backend, QA, and Security skills with bounded 3-retry remediation and explicit human escalation.
---

# Master Orchestration Workflow Specification

**Role:** Master Lifecycle Orchestrator  
**Domain Scope:** Multi-Agent Lifecycle Coordination, Phase Gating, Remediations, Bounded Retries, and Escalation Routing  
**Contract Authority:** [`workflow.md`](file:///c:/multi-agent-fashion-marketplace/workflow.md), [`docs/agent_contract.md`](file:///c:/multi-agent-fashion-marketplace/docs/agent_contract.md), [`docs/data_schema.md`](file:///c:/multi-agent-fashion-marketplace/docs/data_schema.md)  
**Participating Skills:**
- [`pm-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/pm-agent/SKILL.md)
- [`architect-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/architect-agent/SKILL.md)
- [`frontend-developer`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/frontend-developer/SKILL.md)
- [`backend-developer`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/backend-developer/SKILL.md)
- [`qa-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/qa-agent/SKILL.md)
- [`security-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/security-agent/SKILL.md)

---

## 1. Purpose

The **Master Orchestration Workflow** governs the end-to-end software development lifecycle for the Clothify Luxury Fashion Marketplace. It defines the formal sequence of transitions, quality and security barriers, and defect remediation loops ensuring that AI coding assistants operate deterministically, maintain strict separation of concerns, and never release unverified or unhardened code.

### Core Architectural Principles
1. **Strict Upstream Dependency Order:** Downstream stages never execute until upstream prerequisites are verified and committed to state.
2. **Architecture Before Code:** Implementation begins only after system architecture, technology stack, database schemas, and REST API contracts are fully defined and approved.
3. **Quality Precedes Security:** Security audits evaluate only functionally complete implementations that have earned a `PASS` verdict from QA.
4. **Remediation Regression Barrier:** Every security remediation that modifies code must route back through QA regression testing before returning to Security.
5. **Bounded Iteration Budget:** Remediation loops are capped at a strict maximum of **3 retries per issue group** and **5 cumulative loops** across the task.
6. **Human Gatekeeper Authority:** Automated agents cannot autonomously approve production deployment; release authority rests strictly with human stakeholders.

---

## 2. Agent Workflow

The workflow executes in a strict 7-stage sequence:

```
[Stage 1: PM Agent]
        │
        ▼
[Stage 2: Software Architect Agent]
        │
        ▼
[Gate 1: Human Architecture Approval]
        │
        ├───────────────────────────────┐
        ▼ (Parallel or Sequential)      ▼
[Stage 3A: Frontend Developer]   [Stage 3B: Backend Developer]
        │                               │
        └───────────────┬───────────────┘
                        ▼
[Stage 4: QA & Functional Testing Gate] ◄──────┐
                        │                      │
        ┌───────────────┴───────────────┐      │
  (qa_status == PASS)             (FAIL)│      │
        │                               ▼      │
        ▼                    [QA Defect Fix Loop]
[Stage 5: Security Audit Gate]     (≤ 3 Retries)
        │
  ┌─────┴───────────────┐
(PASS)            (FAIL)│
  │                     ▼
  │          [Security Defect Fix Loop]
  │                (≤ 3 Retries)
  │                     │
  │                     └──────────────────────┘
  ▼
[Stage 6: Final Human Review & Sign-Off]
```

### Stage Summary
1. **Stage 1 — Product Definition ([`pm-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/pm-agent/SKILL.md)):** Deconstructs business goals into 7 requirement categories, user stories with acceptance criteria, and prioritized MVP scope (`MUST`, `SHOULD`, `COULD`).
2. **Stage 2 — System Architecture ([`architect-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/architect-agent/SKILL.md)):** Defines layered architecture, confirms 10-category technology stack, specifies 14 relational database entities, and establishes 21 authoritative REST API contracts.
3. **Stage 3 — Implementation ([`frontend-developer`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/frontend-developer/SKILL.md) & [`backend-developer`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/backend-developer/SKILL.md)):**
   - **Parallel Track:** Once Architecture is approved by Human Review, Frontend and Backend developers can proceed in parallel on disjoint file sets.
   - **Sequential Track (Recommended in single chat session):** Executes Frontend then Backend (or vice versa) to prevent tool conflict and merge collisions.
4. **Stage 4 — Quality Assurance ([`qa-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/qa-agent/SKILL.md)):** Performs build verification, automated unit/integration tests (`npm run build`, `pytest backend/tests`), and validates acceptance criteria.
5. **Stage 5 — Security Audit ([`security-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/security-agent/SKILL.md)):** Assesses 9 security domains (Auth, RBAC, IDOR, SQL/Command Injection, Secrets, Uploads, Stock Integrity).
6. **Stage 6 — Final Human Review:** Stakeholders review the verified implementation dossier for production sign-off.

---

## 3. Approval Gates

The workflow enforces 4 formal transition barriers:

| Gate | Timing | Evaluation Criteria | Enforcement Action |
| :--- | :--- | :--- | :--- |
| **Gate 1: Human Architecture Approval** | Post-Architect, Pre-Implementation | PM alignment, tech stack confirmation, 14 DB entities, 21 REST API contracts, and domain invariants validated by human. | Developers cannot write production code until architecture is explicitly approved. |
| **Gate 2: QA Functional Gate** | Post-Developer, Pre-Security | All acceptance criteria satisfied, `npm run build` succeeds, `pytest` passes 100%, `qa_status == "PASS"`. | **Strict Barrier:** Prohibited from entering Security review while QA status is not `PASS`. |
| **Gate 3: Security Gate** | Post-QA, Pre-Human Review | 9 security domains audited, zero Critical or High vulnerabilities, `security_status == "PASS"`. | **Strict Barrier:** Prohibited from advancing to Final Human Review with open Critical/High findings. |
| **Gate 4: Final Human Review** | Lifecycle Completion | Verified test results, clean git diff, security clearance, and zero unresolved blockers. | Release authority rests exclusively with human stakeholders. Agents halt and await instruction. |

---

## 4. Handoff Contract

All agents communicate exclusively through the shared `ProjectState` structure defined in [`docs/data_schema.md`](file:///c:/multi-agent-fashion-marketplace/docs/data_schema.md) and [`docs/agent_contract.md`](file:///c:/multi-agent-fashion-marketplace/docs/agent_contract.md):

| Field Name | Writer / Owner Skill | Permitted Consumers | Description |
| :--- | :--- | :--- | :--- |
| `requirements` | [`pm-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/pm-agent/SKILL.md) | Architect, Developers, QA, Security | 7 mandatory requirement categories |
| `user_stories` | [`pm-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/pm-agent/SKILL.md) | Architect, Developers, QA | User stories with structured acceptance criteria |
| `mvp_scope` | [`pm-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/pm-agent/SKILL.md) | Architect, Developers, QA | Prioritized feature scope (`MUST`, `SHOULD`, `COULD`) |
| `architecture` | [`architect-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/architect-agent/SKILL.md) | Developers, QA, Security | Macro design, components, and 7 domain details |
| `technology_stack` | [`architect-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/architect-agent/SKILL.md) | Developers, QA, Security | 10 confirmed technology decisions |
| `database_schema` | [`architect-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/architect-agent/SKILL.md) | Backend, QA, Security | 14 canonical relational entities and relationships |
| `api_specification` | [`architect-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/architect-agent/SKILL.md) | Frontend, Backend, QA, Security | 21 authoritative REST API contracts |
| `frontend_code` | [`frontend-developer`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/frontend-developer/SKILL.md) | QA, Security, Orchestrator | Implementation metadata and touched `frontend/` files |
| `backend_code` | [`backend-developer`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/backend-developer/SKILL.md) | QA, Security, Orchestrator | Implementation metadata and touched `backend/` files |
| `test_cases` / `test_results` | [`qa-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/qa-agent/SKILL.md) | Developers, Security, Orchestrator | Test definitions, execution logs, and pass/fail metrics |
| `bugs` / `qa_status` | [`qa-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/qa-agent/SKILL.md) | Developers, Orchestrator | Structured defect tickets and standardized QA verdict |
| `security_findings` / `security_status` | [`security-agent`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/security-agent/SKILL.md) | Developers, QA, Orchestrator | Security vulnerability records and audit verdict |
| `current_stage` / `iteration_count` | Master Orchestrator | All Skills | Active lifecycle stage and remediation attempt counter |
| `final_status` | Master Orchestrator | Human Stakeholders | Task completion or escalation status |

### Invariant Business Rules Carried Across Handoffs
- **Variant-Level Stock Authority:** Inventory is authoritative only at `Stock.quantity`. `Product.stock_quantity` is a display aggregate.
- **Payment Slip is Evidence:** Uploading a slip sets status to `uploaded`; payment verification is an asynchronous verification step, never instant credit.
- **Atomic Stock Decrement:** Stock deduction occurs inside an atomic PostgreSQL transaction only after payment verification succeeds.
- **Expiring Fast-Link Checkout:** Fast-link checkout sessions expire and never lock or reserve inventory prior to order creation.
- **Seller Claim Approval:** Warranty claim approval requires explicit seller authorization; AI provides advisory assessments only.
- **No-Adhoc-File-Backups:** Prohibit generating ad-hoc copy files (`*.bak`, `*.backup_*`) in source directories during code edits. Rely on Git Working Tree, `git diff`, and Git revision history.

---

## 5. QA & Bug Fix Loop

When functional verification fails (`qa_status == "FAIL"`):

1. **Defect Ticket Generation:** QA Agent compiles a structured bug ticket:
   ```json
   {
     "issue_id": "BUG-001",
     "severity": "CRITICAL | HIGH | MEDIUM | LOW",
     "description": "Concise failure summary",
     "evidence": "Terminal traceback, assertion error, or build log",
     "agent": "frontend | backend | both"
   }
   ```
2. **Targeted Dispatch:**
   - If `agent == "frontend"`: Dispatched to [`frontend-developer`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/frontend-developer/SKILL.md).
   - If `agent == "backend"`: Dispatched to [`backend-developer`](file:///c:/multi-agent-fashion-marketplace/.agents/skills/backend-developer/SKILL.md).
   - If `agent == "both"`: Dispatched sequentially to Frontend then Backend.
3. **Mandatory QA Retest:** Once the developer modifies code, execution **must return directly to Stage 4 (QA Gate)** for full regression testing.
4. **Exit Barrier:** Execution cannot proceed to Stage 5 (Security) until QA issues an unambiguous `PASS`.

---

## 6. Security & Retest Loop

When security audit discovers vulnerabilities (`security_status == "FAIL"`):

1. **Vulnerability Finding Generation:** Security Agent compiles a structured finding:
   ```json
   {
     "finding_id": "SEC-001",
     "severity": "CRITICAL | HIGH | MEDIUM | LOW",
     "vulnerability_type": "IDOR | SQLi | RBAC_BYPASS | DATA_EXPOSURE | INVENTORY_INTEGRITY",
     "reproduction": "Proof of concept or exploit vector",
     "agent": "frontend | backend | both"
   }
   ```
2. **Targeted Remediation:** Dispatched to the responsible developer agent (`frontend-developer`, `backend-developer`, or both).
3. **Mandatory 3-Step Verification Sequence:**
   $$\text{Security Finding} \longrightarrow \text{Developer Fix} \longrightarrow \mathbf{\text{QA Regression Test}} \longrightarrow \mathbf{\text{Security Retest}}$$
   - **Regression Protection:** It is strictly prohibited to return directly from Developer to Security retest. The fix must first pass QA regression to confirm that business logic and tests did not break.
4. **Exit Barrier:** Execution cannot advance to Stage 6 (Final Human Review) while any Critical or High security findings remain open.

---

## 7. Retry & Stop Rules

To guarantee termination and prevent infinite repair cycles, the orchestrator enforces strict budget rules:

| Metric | Threshold | Enforcement Action |
| :--- | :--- | :--- |
| **Max Retries per Issue Group** | 3 cycles | Halt loop, assign `final_status = "NEEDS_HUMAN_REVIEW"`, escalate to human |
| **Global Task Iteration Ceiling** | 5 total loops | Halt workflow immediately and escalate to human |
| **Environment / Runtime Outage** | 1 failure | Designate `BLOCKED`, do not consume retry budget, alert human |

### Explicit Stop Conditions
1. **Exceeded Retry Budget:** When `iteration_count` reaches 3 for any single defect category, automated agent re-dispatch must halt.
2. **Contract Impasse:** When a defect is caused by an irreconcilable conflict between PM requirements and Architectural contracts, halt and request human clarification.
3. **Environment Failure:** If local database harnesses, compilers, or test runners fail to execute due to machine configuration, mark status as `BLOCKED` and halt.
4. **Data Corruption Threat:** If an operation threatens database corruption, data loss, or unsafe schema drop, abort immediately.

---

## 8. Final Human Review

Before concluding a workflow run, the orchestrator compiles and presents an audit dossier to human stakeholders:

### Required Dossier Contents
1. **Executive Summary:** Overview of requested features or bug fixes implemented.
2. **Verified File Changes:** Explicit list of files created or modified, validated via `git status` and `git diff`.
3. **QA Verification Evidence:** Automated test logs, exit codes, and test counts (`npm run build`, `pytest backend/tests`).
4. **Security Clearance Evidence:** Security domain audit results and confirmation of zero open Critical/High findings.
5. **Iteration & Budget Audit:** Number of remediation cycles consumed and remaining retry allowance.
6. **Known Technical Debt & Unverified Items:** Honest disclosure of edge cases or external providers not verifiable in the local environment.

> [!IMPORTANT]
> **Final Human Authority:** Automated agents halt upon delivering the dossier and await explicit human instructions. Agents must never declare production deployment or conclude sign-off without human approval.

---

## 9. Limitations & Operational Reality

When executing this workflow within the Antigravity IDE:

1. **Cognitive State Tracking:** In the Antigravity pair programming environment, state transitions and retry counters (`iteration_count`) are maintained cognitively in the conversation context and prompt reasoning. There is no active OS daemon or background process automatically killing the agent process or persisting state across process restarts.
2. **Sequential Session Reality:** Unless independent subagents are explicitly spawned with non-overlapping workspace permissions, tasks execute sequentially in the single conversation session to prevent file write collisions.
3. **No-Adhoc-File-Backups Enforcement:** Agents must adhere strictly to version control practices: do not copy files into `*.bak` or `*.backup_*` in `frontend/src/` or `backend/app/`. Physical backups are reserved strictly for explicit user requests or irreversible high-risk operations, stored immutably in designated locations (such as `backups/`).
4. **Honest Verification Mandate:** Never report `PASS` for tests or security audits that were not actually executed in the terminal. If an environment limitation prevents running a test, report it transparently as `BLOCKED` or `NOT_RUN`.