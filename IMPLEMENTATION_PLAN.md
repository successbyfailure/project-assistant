# FULCRUM PROJECT MANAGER - Implementation Plan

## 📊 Project Phases Overview

```
Phase 1: Multi-tenant Foundation     → 2-3 weeks
Phase 2: Identity & Integrations    → 2-3 weeks  
Phase 3: Remote Workspace Orchestration → 3-4 weeks
Phase 4: AI & Advanced Workflows    → 2 weeks
```

---

## 🎯 Phase 1: Multi-tenant Foundation

**Goal**: Dockerized environment with FastAPI and PostgreSQL supporting multiple users.

### Module 1.1: Docker Infrastructure

- [x] **1.1.1 Create Dockerized environment**
- [x] **1.1.2 Database Migration Layer**
- [x] **1.1.3 Integration Strategy Research**

### Module 1.2: Core API & Auth

- [x] **1.2.1 Auth System (JWT + Passlib)**
- [x] **1.2.2 Multi-tenant Task Engine (Migration to Postgres)**
- [x] **1.2.3 LLM Credential Management (Global + User-specific)**
- [x] **1.2.4 Project Registration (Local metadata)**

---

## 🎯 Phase 2: Identity & Integrations

**Goal**: Allow users to connect their Coder and GitHub accounts.

### Module 2.1: GitHub Integration
- [ ] **2.1.1 GitHub OAuth Flow**
  - Implement "Connect GitHub" feature.
  - Securely store encrypted access tokens.
- [ ] **2.1.2 Repository Discovery**
  - List user repositories via GitHub API.

### Module 2.2: Coder Integration
- [ ] **2.2.1 Coder Account Sync**
  - Support multiple Coder URLs and Tokens per user.
- [ ] **2.2.2 Workspace Discovery**
  - Fetch available Coder workspaces for the authenticated user.

### Module 2.3: GitHub Ecosystem Research
- [ ] **2.3.1 GH Actions & Resources**
  - Research Coder functionality replacement/enhancement with GitHub Actions, Codespaces, and GitHub resources.

---

## 🎯 Phase 3: Remote Workspace Orchestration

**Goal**: Execute project management tools on remote environments.

### Module 3.1: Remote MCP Bridge
- [ ] **3.1.1 Tunneling to Coder**
  - Implement connection logic to user's Coder workspaces (via Coder CLI or SSH).
- [ ] **3.1.2 Remote Tool Execution**
  - Execute Git and File tools on the remote workspace from the central server.

### Module 3.2: Project Dashboard
- [ ] **3.2.1 Global Project Status**
  - Combine data from GitHub (Issues/PRs) and Remote Coder (Git/Files).
- [ ] **3.2.2 Multi-project View**
  - Allow users to see all their connected projects in one place.

---

## 🎯 Phase 4: AI & Advanced Workflows

**Goal**: Add intelligence and automation on top of the cloud infrastructure.

### Module 4.1: Fulcrum PM Agent
- [ ] **4.1.1 Agent Brain Implementation**
  - Implement a central LLM-based coordinator.
  - Ability to context-switch between multiple projects.
- [ ] **4.1.2 Cloud Research Engine**
  - Implement research tasks using Celery/Redis workers.
  - Storage of research artifacts in a centralized volume/S3.

### Module 4.2: Automated PR Workflows
- [ ] **4.2.1 "Prepare Release" Workflow**
  - Automated versioning and PR creation across remote environments.

---

## 🎯 Success Criteria (Cloud version)

- [ ] Server runs in Docker.
- [ ] Multiple users can log in and have isolated data.
- [ ] User can connect a GitHub account and see their repos.
- [ ] User can connect a Coder account and see their workspaces.
- [ ] Project status can be fetched from a remote Coder workspace.
