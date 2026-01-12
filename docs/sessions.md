# KairoCortex Implementation Sessions

## Session 3: Architecture Finalization (2025-12-31)

### Context
After completing Phase 1 and 2, read comprehensive KairoKensei design documents to understand the full scope:
- INPUTDESIGN.md - Semantic compression and prediction system
- KAIROKENSEI_ARCHITECTURE.md - Complete remote GUI utility architecture
- HELPER_ARCHITECTURE.md - Backend helper categories and extraction
- KAIROKENSEI_INTERFACE_DESIGN.md - Visual design system
- COMPASS_CENTRIC_UI.md - 3x3 grid interface for all interactions

**Key Realization:** KairoCortex is not just a keyboard predictor, but a universal AI orchestration system coordinating multiple helpers (Grok, Gemini, Claude Code, Terminal, Browser, etc.) through semantic data extraction.

### Architectural Decision: Hybrid Rust/Python Stack

**User Proposal:** "Option C but I think we may need to build the backend in Rust and use the axon_bbs and the subagent that was just built as a method to communicate between the frontend to the rust backend."

**Architecture Chosen:**
```
KairoKensei Frontend (Rust/egui)
    ↓ Tor HTTP/SSE
Axon BBS (Django/Python) - Middleware
    ↓ MessageBoard polling
KairoCortex Agent (Python) - Protocol Translator
    ↓ HTTP API (localhost)
KairoCortex Backend (Rust) - Helper Orchestrator
```

**Benefits:**
- Leverage existing Axon BBS infrastructure (Tor, auth, federation, persistence)
- KairoCortex Agent becomes proven communication bridge
- Rust backend handles performance-critical orchestration
- Type safety across frontend (egui) and backend (both Rust)
- Clean separation of concerns

### Work Completed

1. **Created Comprehensive Architecture Spec**
   - File: `docs/KAIROCORTEX_RUST_ARCHITECTURE.md`
   - Documented full stack from egui frontend to Rust backend
   - Defined communication protocols (SemanticIntent, CortexSuggestion)
   - Implementation phases (1-8)
   - Security model, performance targets, configuration

2. **Frontend Correction**
   - Updated all documentation from Dioxus to **egui** (immediate mode GUI)
   - egui better suited for responsive compass interactions

3. **Phase 3: Rust Backend Skeleton ✅ COMPLETE**
   - Created Cargo project: `$HOME/kairocortex_backend/`
   - Configured dependencies (axum, tokio, serde, reqwest, async-trait, anyhow, tracing)
   - Implemented type system (`src/types.rs`):
     - IntentRequest, IntentResponse, HelperResponse
     - HealthResponse, HelpersListResponse
   - Created Helper trait system (`src/helpers/mod.rs`)
   - Implemented 4 stub helpers:
     - GrokHelper - Mock predictions based on concepts
     - GeminiHelper - Mock predictions
     - ClaudeCodeHelper - Mock predictions
     - TerminalHelper - Stub for future CLI integration
   - Built Orchestrator (`src/orchestrator.rs`):
     - Helper registration and management
     - Auto-routing based on intent type
     - Validation placeholder (TODO: implement 10th Man)
   - Created Axum web server (`src/main.rs`):
     - GET /health - Server health check
     - POST /process_intent - Process semantic intents
     - GET /helpers - List registered helpers
     - Binds to localhost:8001 (security: no external access)
   - **Testing:**
     - ✅ cargo build - Compiled successfully
     - ✅ GET /health - Returns status, version, uptime
     - ✅ GET /helpers - Lists 4 helpers with capabilities
     - ✅ POST /process_intent - Processes intent and returns predictions

4. **Phase 3+: Performance & Helper Enhancements ✅ COMPLETE**
   - **Benchmark Endpoint** (`GET /benchmark`):
     - Latency measurement (microsecond precision)
     - Bandwidth testing (1KB, 10KB, 100KB payloads)
     - Compute test (fibonacci calculation)
     - Results: ~0.8ms avg latency, 76 Mbps effective bandwidth

   - **Speed Test Script** (`speedtest.sh`):
     - Health endpoint latency testing
     - Benchmark endpoint with bandwidth calculation
     - Process intent latency measurement
     - Concurrent request testing (configurable)
     - Sample: 250 req/s on health endpoint, 4ms avg per request

   - **Llama Helper Investigation**:
     - Attempted Pi4 SSH integration for Llama 3.2
     - Challenge: llama-cli interactive mode + SSH cert auth required
     - **Decision**: Keep Llama validation in Python Agent (already working)
     - Rust backend focuses on API helpers (Grok, Gemini, Claude)

   - **Architecture Clarification**:
     - Frontend ↔ Axon BBS: Over Tor
     - Axon BBS ↔ Python Agent: Local (same server)
     - Python Agent ↔ Rust Backend: localhost:8001 (HTTP)
     - Python Agent ↔ Pi4 Llama: Local SSH (SSH keys already configured)

5. **Phase 2.5: Python Agent → Rust Backend Integration ✅ COMPLETE**
   - **Implementation** (Sonnet 4.5 via Antigravity + manual fix):
     - Added `requests` library for HTTP client
     - Configuration: `KAIRO_BACKEND_URL`, `KAIRO_BACKEND_TIMEOUT` env vars
     - Replaced `_generate_candidates()` stub with POST to `localhost:8001/process_intent`
     - IntentRequest/IntentResponse JSON serialization
     - Comprehensive error handling (timeout, connection, JSON parse)
     - Non-blocking health check on startup
     - Fail-safe design: empty candidates on backend failure

   - **Manual Fix**:
     - Corrected response format transformation
     - Backend returns single `{predictions, confidence}` → wrap as list for `_llama_critic`

   - **Testing**:
     - ✅ Rust backend responds correctly (Grok stub predictions)
     - ✅ File deployed to Pi4 (`/home/pibbs/axon_bbs/core/agents/`)
     - ⏸️ End-to-end test pending (Rust backend deployment to Pi4)

   - **Deployment Note**:
     - Rust backend currently runs on development desktop
     - For Pi4 testing: Either run Rust on Pi4 OR set `KAIRO_BACKEND_URL=http://<desktop-ip>:8001`

### Next Steps: Rust Backend Deployment & Testing
- anyhow - Error handling

### Files Modified/Created This Session

- `docs/KAIROCORTEX_RUST_ARCHITECTURE.md` - Complete architecture specification

### Technical Notes

**Communication Flow:**
1. Frontend sends SemanticIntent via `POST /api/kairo/intent/`
2. Axon BBS creates Message on KairoCortex board
3. KairoCortex Agent polls board (1s), detects new intent
4. Agent calls `POST http://localhost:8001/process_intent`
5. Rust backend routes to appropriate helper
6. Helper generates candidates + validation
7. Backend returns approved response to Agent
8. Agent posts CortexSuggestion to MessageBoard
9. SSE stream pushes to frontend via `GET /api/kairo/events/`

**Security Model:**
- Frontend ↔ Axon BBS: JWT authentication over Tor
- Agent ↔ Backend: Localhost only (network isolation)
- No external network access to Rust backend

---

## Session 2: Phase 1 & 2 Implementation (2025-12-30)

### Phase 1: API Endpoints and MessageBoard ✅

1. **Created KairoCortex MessageBoard**
   - SSH to Pi4: `ssh -p 2222 pibbs@192.168.58.7`
   - Created via Django shell
   - Name: KairoCortex, ID: 12
   - Settings: is_realtime=True, local_poll_interval=1.0s

2. **Implemented API Endpoints**
   - File: `core/views/kairo_api.py`
   - `POST /api/kairo/intent/` - Receive semantic intents from KairoKensei
   - `GET /api/kairo/events/` - SSE stream for CortexSuggestion responses
   - JWT authentication via rest_framework_simplejwt

3. **Added URL Routes**
   - File: `core/urls.py`
   - Mapped kairo_api views to `/api/kairo/*`

4. **Testing**
   - Created test user: kairotest / testpass123
   - Generated JWT tokens via `/api/token/`
   - Verified POST creates SemanticIntent messages on board
   - Verified SSE stream connects and waits for updates

### Phase 2: KairoCortex Service ✅

1. **Implemented Monitoring Service**
   - File: `core/agents/kairo_cortex_service.py`
   - `KairoCortexService` class with monitor thread
   - Polls KairoCortex board every 1s for new SemanticIntent messages
   - Processes intents using 10th Man pattern

2. **10th Man Implementation**
   - `_generate_candidates()` - Stub returning mock predictions
   - `_llama_critic()` - Calls local Llama 3.2 via subprocess
     - Binary: `/home/pibbs/llama.cpp/build/bin/llama-cli`
     - Model: `Llama-3.2-1B-Instruct-Q4_K_M.gguf` (771MB)
     - Prompt: "You are an adversarial critic... Reply PASS or REJECT"
     - Fail-open: Allow on timeout/crash (safety fallback)
   - Posts CortexSuggestion or rejection back to board

3. **Service Registration**
   - Initial attempt to modify ServiceManager failed
   - User corrected: "service can start as a user agent under the users"
   - Created agent user: kairocortex_agent (is_agent=True)
   - Tested via `service_manager.start_agent(agent_user, 'kairo_cortex', board_id=12)`
   - Service successfully running

4. **Testing**
   - Posted test intent via API
   - Verified intent reaches board (message ID: 788a8a21...)
   - Service monitoring confirmed

### Documentation and Git Hygiene

1. **Personal Info Sanitization**
   - Removed IP addresses from sessions.md, todo.md
   - Removed hardcoded /home/pibbs paths from docs
   - Copyright headers preserved (GPL v3)

2. **Created Personal Notes**
   - File: `docs/KAIROCORTEX_NOTES.md`
   - Contains Pi4 SSH details, test credentials, IP addresses
   - Added to `.gitignore` (personal documentation section)

3. **File Locations**
   - Source code: Pi4 `/home/pibbs/axon_bbs/`
   - Backed up to: Local `$HOME/axon_bbs/`
   - Workflow: Edit on Pi4, test immediately, sync back to local for git

---

## Session 1: Setup and Context (2025-12-29)

### Initial Context

**Goal:** Implement KairoCortex as Axon BBS sub-agent for 10th Man validation of keyboard predictions from KairoKensei client.

**Architecture:**
- KairoKensei (Rust/egui client) sends compressed semantic intent over Tor
- Axon BBS receives intent via API endpoint
- KairoCortex sub-agent processes using:
  - Generator: API calls (Grok/Gemini/Claude - stubbed initially)
  - Critic: Local Llama 3.2 (1B quantized model)
- Validated responses streamed back via SSE

### Pre-Session State

**Pi4 Setup (192.168.58.7:2222):**
- llama.cpp compiled at `/home/pibbs/llama.cpp/build/bin/llama-cli`
- Model downloaded: `Llama-3.2-1B-Instruct-Q4_K_M.gguf` (771MB)
- Inference time: 30-60s (acceptable for async validation)
- Axon BBS running on port 8000

**Documents Read:**
- LastSession.txt - Previous llama.cpp verification
- KAIROCORTEX_AGENT_SPEC.md - Detailed implementation spec
- CORTEX_ARCHITECTURE_SUMMARY.md - High-level design from Gemini

### Key Technical Decisions

1. **10th Man Pattern:**
   - Generator creates candidates (API - stubbed)
   - Critic validates (Llama - implemented)
   - Fail-open on critic failure (availability over perfect safety)

2. **MessageBoard Pattern:**
   - Following AxonChat example
   - Subject='SemanticIntent' for inbound
   - Subject='CortexSuggestion' for outbound
   - Real-time via RealtimeMessageService (1s poll, 5s federation)

3. **Security:**
   - All endpoints require JWT authentication
   - Llama runs in isolated subprocess (no network)
   - Intent messages include user context for audit trail
