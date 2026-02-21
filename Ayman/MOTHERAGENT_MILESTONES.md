# MotherAgent --- Nested Milestone Roadmap (Local → Hosted)

------------------------------------------------------------------------

# Milestone 0 --- Decisions and Repo Skeleton

## 0.1 Lock decisions

-   Supabase = auth + Postgres + pgvector
-   S3 = blob storage (per-user files)
-   Block DB + reference packages = core knowledge substrate
-   Embed-based prompt injection = primary intelligence mechanism
-   LLM calls = native SDKs only (Paid-compatible)
-   Non-streaming only

## 0.2 Repo structure

-   apps/web (Next.js)
-   apps/api (Python FastAPI preferred)
-   packages/block_db
-   packages/reference_packages
-   packages/prompt_injection

## 0.3 Python dependency policy

-   Use UV
-   Commit lockfile
-   CI bans pip installs

------------------------------------------------------------------------

# Milestone 1 --- Everything Works on Localhost

## 1.1 Local infra

-   Supabase project configured
-   S3 dev bucket configured
-   DB migrations applied

## 1.2 Backend (localhost)

-   FastAPI boots
-   Health endpoint
-   Supabase connection verified
-   JWT validation works

## 1.3 Frontend (localhost)

-   Next.js boots
-   Login works
-   Protected routes work

## 1.4 End-to-end smoke test

-   User logs in
-   Creates agent draft
-   Runs simple execution
-   Result persists and displays

------------------------------------------------------------------------

# Milestone 2 --- Supabase Schema + RLS

## 2.1 Core tables

-   orgs
-   org_members
-   user_profiles
-   agents
-   agent_versions
-   executions
-   execution_steps
-   blocks
-   block_versions
-   block_knowledge_chunks (+ embeddings)
-   reference_packages
-   reference_package_chunks (+ embeddings)
-   files
-   file_chunks (+ embeddings)
-   memory_items (+ embeddings)

## 2.2 RLS

-   Org-scoped reads/writes
-   Service role bypass for backend

------------------------------------------------------------------------

# Milestone 3 --- S3 File Storage

## 3.1 Backend endpoints

-   POST /files/presign-upload
-   POST /files/{fileId}/complete
-   GET /files
-   GET /files/{fileId}/download-url

## 3.2 Frontend UX

-   Upload component
-   Progress tracking
-   Status indicator

## 3.3 File ingestion

-   Extract text
-   Chunk
-   Generate embeddings
-   Store in Supabase

------------------------------------------------------------------------

# Milestone 4 --- Reference Packages

## 4.1 Format + versioning

-   Define structure
-   Define version rules

## 4.2 Ingestion

-   Chunk
-   Embed
-   Store

## 4.3 Retrieval API

-   POST /retrieval/reference-packages

------------------------------------------------------------------------

# Milestone 5 --- Block DB + Block-Checker (#2)

## 5.1 Block spec

-   Immutable versions
-   Canonical embedding text

## 5.2 Similarity search

-   POST /retrieval/block-similarity
-   Reuse vs new decision logic

## 5.3 Checker integration

-   Inject similarity context
-   Append new blocks with embeddings

------------------------------------------------------------------------

# Milestone 6 --- Embed-Based Prompt Injection

## 6.1 Injection stages

-   Decomposition
-   Block-checker
-   Runtime execution

## 6.2 Prompt assembler

-   Token budget manager
-   Dedup + ranking
-   Deterministic ordering
-   Injection trace persistence

## 6.3 Retrieval sources

-   Blocks
-   Reference packages
-   Memory items
-   File chunks

------------------------------------------------------------------------

# Milestone 7 --- MotherAgent Runner

## 7.1 Runner contract

-   Execute AgentVersion
-   Persist step state
-   Retry + timeout logic

## 7.2 Step types

-   LLM step
-   Tool step
-   Memory read/write step

## 7.3 Observability

-   execution_steps table populated
-   Step input/output summaries stored

------------------------------------------------------------------------

# Milestone 8 --- Backend Hosting (Isolated)

## 8.1 Deploy backend

-   Production host configured
-   Env vars + secrets set
-   Health monitoring

## 8.2 Production connectivity

-   Supabase connected
-   S3 presign works
-   Ingestion worker deployed

## 8.3 Hardening

-   Rate limits
-   Request size limits
-   Structured logs

------------------------------------------------------------------------

# Milestone 9 --- Frontend Hosting (Isolated)

## 9.1 Deploy frontend

-   Env vars set
-   Backend URL configured
-   Supabase callbacks updated

## 9.2 Hosted end-to-end

-   Login works
-   Agent creation works
-   File upload works
-   Execution works
-   Logs display correctly

------------------------------------------------------------------------

# Milestone 10 --- Paid AI Cost Integration

## 10.1 Enforcement

-   Native SDK usage only
-   Embeddings use native SDK
-   Attribution metadata included

## 10.2 Reporting

-   Cost per execution persisted
-   Basic cost reporting endpoint

------------------------------------------------------------------------

# Milestone 11 --- Paid AI Hosting (Later)

## 11.1 Execution handoff

-   Define execution contract
-   Ensure DB remains canonical
-   Validate margin reporting

------------------------------------------------------------------------

# Milestone 12 --- Production Readiness

## 12.1 Limits

-   Max file size
-   Max chunks
-   Max injected tokens
-   Max run duration

## 12.2 Security

-   RLS audit
-   S3 policy audit
-   Presign TTL audit

## 12.3 Performance

-   pgvector indexing
-   Retrieval caching
-   Ingestion stress tests
