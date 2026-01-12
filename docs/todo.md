# KairoCortex Implementation Roadmap

## Current Status: Phase 2 Complete, Phase 3 Next

---

## Phase 1: API Endpoints and MessageBoard ✅ COMPLETE

- [x] Create KairoCortex MessageBoard on Pi4
  - [x] SSH to Pi4 (ssh -p 2222 pibbs@192.168.58.7)
  - [x] Django shell: Create MessageBoard with name='KairoCortex'
  - [x] Configure settings: is_realtime=True, local_poll_interval=1.0s
  - [x] Note board ID for later use

- [x] Implement API endpoints (core/views/kairo_api.py)
  - [x] `POST /api/kairo/intent/` - Receive SemanticIntent
    - [x] JWT authentication
    - [x] Parse JSON body
    - [x] Create Message on KairoCortex board with subject='SemanticIntent'
    - [x] Return message ID and status
  - [x] `GET /api/kairo/events/` - SSE stream
    - [x] JWT auth via token query param
    - [x] Subscribe to RealtimeMessageService
    - [x] Filter for subject='CortexSuggestion'
    - [x] Stream updates to client

- [x] Add URL routes (core/urls.py)
  - [x] Import kairo_api views
  - [x] Add path('kairo/intent/', ...)
  - [x] Add path('kairo/events/', ...)

- [x] Test endpoints
  - [x] Create test user via Django shell
  - [x] Generate JWT token via /api/token/
  - [x] Test POST /api/kairo/intent/ with curl
  - [x] Test GET /api/kairo/events/ with curl -N
  - [x] Verify message appears on board

- [x] Copy files back to local repo
  - [x] scp kairo_api.py to ~/axon_bbs/
  - [x] scp urls.py to ~/axon_bbs/

---

## Phase 2: KairoCortex Service ✅ COMPLETE

- [x] Create service file (core/agents/kairo_cortex_service.py)
  - [x] KairoCortexService class
  - [x] __init__(board_id, llama_binary, llama_model)
  - [x] start() - Start monitor thread
  - [x] stop() - Shutdown gracefully
  - [x] _monitor_loop() - Poll board every 1s
  - [x] Track last_processed_time

- [x] Implement intent processing
  - [x] _process_intent(intent_msg)
  - [x] Parse JSON from message body
  - [x] Extract intent_id, compressed_concepts, context

- [x] Implement candidate generation (stubbed)
  - [x] _generate_candidates(intent_data)
  - [x] Return mock candidates for now
  - [x] TODO: Add API integration (Grok/Gemini/Claude)

- [x] Implement Llama critic
  - [x] _llama_critic(candidate)
  - [x] Construct critic prompt
  - [x] subprocess.run(llama-cli)
  - [x] Parse PASS/REJECT from output
  - [x] Fail-open on timeout/error
  - [x] Return True (allow) or False (reject)

- [x] Post results to board
  - [x] Create CortexSuggestion message on pass
  - [x] Create rejection message if all candidates fail
  - [x] Include intent_id, predictions, confidence, critique_passed

- [x] Service registration
  - [x] Create agent user: kairocortex_agent (is_agent=True)
  - [x] Test start via service_manager.start_agent()
  - [x] Verify monitoring thread running

- [x] Testing
  - [x] Post test intent to API
  - [x] Verify service processes intent
  - [x] Check CortexSuggestion appears on board
  - [x] Verify SSE stream receives response

- [x] Copy files back to local repo
  - [x] scp kairo_cortex_service.py to ~/axon_bbs/

---

## Phase 2.5: Prepare Agent for Rust Backend ⏸️ PENDING

- [ ] Modify KairoCortex Agent (core/agents/kairo_cortex_service.py)
  - [ ] Add HTTP client for Rust backend
  - [ ] Replace _generate_candidates() stub with POST to http://localhost:8001/process_intent
  - [ ] Add timeout configuration (default 10s)
  - [ ] Add retry logic (max 3 attempts)
  - [ ] Add health check before processing intents
  - [ ] Option: Keep _llama_critic() or move to Rust backend

- [ ] Configuration
  - [ ] Add KAIRO_BACKEND_URL env var (default http://localhost:8001)
  - [ ] Add KAIRO_BACKEND_TIMEOUT env var (default 10)
  - [ ] Document in KAIROCORTEX_NOTES.md

- [ ] Testing
  - [ ] Start Rust backend (Phase 3)
  - [ ] Verify Agent connects to backend
  - [ ] Test end-to-end flow: Intent → Agent → Rust → Response → SSE
  - [ ] Test error handling (backend down, timeout, invalid response)

---

## Phase 3: Rust Backend Skeleton ✅ COMPLETE

**Completed 2025-12-31**
- ✅ Created `$HOME/kairocortex_backend/` with Axum server on localhost:8001
- ✅ Implemented Helper trait system with 5 helpers (Grok, Gemini, Claude, Terminal, Llama)
- ✅ Built Orchestrator for intent routing
- ✅ Added benchmark endpoint with latency/bandwidth metrics (~0.8ms latency, 76 Mbps)
- ✅ Created `speedtest.sh` load testing script (250 req/s capability)
- ✅ Pi4 Llama wrapper script (works via SSH, architectural decision: keep in Python Agent)
- ✅ All endpoints tested and working

**Git commits:** 3e77fd9, 48d1f57, 71636b7

### 3.1: Project Setup
- [ ] Create Cargo project
  - [ ] cd $HOME
  - [ ] cargo new kairocortex_backend
  - [ ] cd kairocortex_backend

- [ ] Configure Cargo.toml dependencies
  - [ ] axum = "0.7" (web framework)
  - [ ] tokio = { version = "1", features = ["full"] } (async runtime)
  - [ ] serde = { version = "1", features = ["derive"] }
  - [ ] serde_json = "1"
  - [ ] tower-http = { version = "0.5", features = ["cors", "trace"] }
  - [ ] tracing = "0.1" (logging)
  - [ ] tracing-subscriber = "0.3"
  - [ ] reqwest = { version = "0.11", features = ["json"] } (HTTP client)
  - [ ] anyhow = "1" (error handling)

### 3.2: Project Structure
- [ ] Create module structure
  - [ ] src/main.rs - Server entry point
  - [ ] src/types.rs - Shared types (Intent, Response, etc.)
  - [ ] src/orchestrator.rs - Main orchestration logic
  - [ ] src/helpers/mod.rs - Helper trait definition
  - [ ] src/helpers/grok.rs - Grok helper (stub)
  - [ ] src/helpers/gemini.rs - Gemini helper (stub)
  - [ ] src/helpers/claude_code.rs - Claude Code helper (stub)
  - [ ] src/helpers/terminal.rs - Terminal helper (stub)
  - [ ] src/validators/mod.rs - Validation trait
  - [ ] src/validators/llama.rs - Llama validator (stub)

### 3.3: Type Definitions (src/types.rs)
- [ ] Define IntentRequest struct
  - [ ] intent_id: String
  - [ ] intent_type: IntentType enum
  - [ ] compressed_concepts: Vec<String>
  - [ ] context: String
  - [ ] confidence: f64
  - [ ] target_helper: Option<String>

- [ ] Define IntentResponse struct
  - [ ] intent_id: String
  - [ ] predictions: Vec<String>
  - [ ] confidence: f64
  - [ ] helper_used: String
  - [ ] validation_passed: bool
  - [ ] metadata: ResponseMetadata

- [ ] Derive Serialize, Deserialize for all types

### 3.4: Helper Trait System (src/helpers/mod.rs)
- [ ] Define Helper trait
  ```rust
  #[async_trait]
  pub trait Helper: Send + Sync {
      fn name(&self) -> &str;
      fn capabilities(&self) -> Vec<String>;
      async fn process(&self, intent: &IntentRequest) -> Result<HelperResponse>;
      async fn health_check(&self) -> bool;
  }
  ```

- [ ] Define HelperResponse struct
  - [ ] predictions: Vec<String>
  - [ ] confidence: f64
  - [ ] processing_time_ms: u64

- [ ] Create stub implementations (src/helpers/*.rs)
  - [ ] GrokHelper - Returns mock predictions
  - [ ] GeminiHelper - Returns mock predictions
  - [ ] ClaudeCodeHelper - Returns mock predictions
  - [ ] TerminalHelper - Returns empty for now

### 3.5: Orchestrator (src/orchestrator.rs)
- [ ] Define Orchestrator struct
  - [ ] helpers: HashMap<String, Box<dyn Helper>>

- [ ] impl Orchestrator
  - [ ] new() -> Self
  - [ ] register_helper(name, helper)
  - [ ] async process_intent(intent) -> Result<IntentResponse>
    - [ ] Route to target_helper or auto-select
    - [ ] Call helper.process()
    - [ ] Run validation (stub for now)
    - [ ] Build IntentResponse

### 3.6: Web Server (src/main.rs)
- [ ] Set up Axum router
  - [ ] GET /health -> health_handler
  - [ ] POST /process_intent -> process_intent_handler
  - [ ] GET /helpers -> list_helpers_handler

- [ ] Implement handlers
  - [ ] health_handler() - Return {"status": "ok"}
  - [ ] process_intent_handler(Json<IntentRequest>) -> Json<IntentResponse>
    - [ ] Call orchestrator.process_intent()
    - [ ] Handle errors, return 500 on failure
  - [ ] list_helpers_handler() - Return registered helpers and capabilities

- [ ] Configure server
  - [ ] Bind to 127.0.0.1:8001 (localhost only)
  - [ ] Add tracing middleware
  - [ ] Add CORS (allow localhost)

- [ ] Main function
  - [ ] Initialize tracing
  - [ ] Create Orchestrator
  - [ ] Register stub helpers
  - [ ] Start Axum server

### 3.7: Testing
- [ ] Build and run
  - [ ] cargo build
  - [ ] cargo run
  - [ ] Verify server starts on port 8001

- [ ] Test health endpoint
  - [ ] curl http://localhost:8001/health
  - [ ] Expect {"status": "ok"}

- [ ] Test process_intent endpoint
  - [ ] curl -X POST http://localhost:8001/process_intent with test JSON
  - [ ] Verify mock response returned

- [ ] Test helpers endpoint
  - [ ] curl http://localhost:8001/helpers
  - [ ] Verify stub helpers listed

### 3.8: Integration with Python Agent
- [ ] Start Rust backend: cargo run
- [ ] Restart Python agent with Phase 2.5 changes
- [ ] Post test intent via API
- [ ] Verify end-to-end flow works
- [ ] Check logs on both sides

---

## Phase 4: Helper Implementation 📋 PLANNED

### 4.1: API Helper - Grok
- [ ] Add xAI API client (src/helpers/grok.rs)
- [ ] Implement process() with real API call
- [ ] Add API key configuration (KAIRO_GROK_API_KEY env var)
- [ ] Add retry logic and rate limiting
- [ ] Add error handling
- [ ] Test with real xAI account

### 4.2: API Helper - Gemini
- [ ] Add Google Gemini API client (src/helpers/gemini.rs)
- [ ] Implement process() with real API call
- [ ] Add API key configuration (KAIRO_GEMINI_API_KEY)
- [ ] Add retry logic
- [ ] Test with real Gemini account

### 4.3: API Helper - Claude Code
- [ ] Add Anthropic API client (src/helpers/claude_code.rs)
- [ ] Implement process() with Claude API
- [ ] Add API key configuration (KAIRO_CLAUDE_API_KEY)
- [ ] Add streaming support (optional)
- [ ] Test with real Anthropic account

### 4.4: CLI Helper - Terminal
- [ ] Implement terminal command execution (src/helpers/terminal.rs)
- [ ] Add command sanitization and validation
- [ ] Add output capture and parsing
- [ ] Add timeout protection
- [ ] Security: Whitelist allowed commands

### 4.5: Web Helper - Browser
- [ ] Add web scraping (src/helpers/browser.rs)
- [ ] Use reqwest for HTTP fetching
- [ ] Add HTML parsing (scraper crate)
- [ ] Extract semantic content (text, links, metadata)
- [ ] Add rate limiting and caching

### 4.6: File Helper - FileSystem
- [ ] Implement file operations (src/helpers/filesystem.rs)
- [ ] Safe path handling
- [ ] Read/write/search operations
- [ ] Integration with rclone for Google Drive sync

---

## Phase 5: 10th Man Validation Framework 🧪 PLANNED

### 5.1: Validation Trait
- [ ] Define Validator trait (src/validators/mod.rs)
  ```rust
  #[async_trait]
  pub trait Validator: Send + Sync {
      async fn validate(&self, candidate: &HelperResponse) -> Result<ValidationResult>;
  }
  ```

- [ ] Define ValidationResult struct
  - [ ] passed: bool
  - [ ] confidence_adjustment: f64
  - [ ] reasoning: String

### 5.2: Llama Validator
- [ ] Implement LlamaValidator (src/validators/llama.rs)
- [ ] Option A: Subprocess call to llama-cli (like Python version)
- [ ] Option B: Use llama.cpp Rust bindings (llama-cpp-rs crate)
- [ ] Add fail-open configuration
- [ ] Add timeout handling
- [ ] Add prompt engineering for critic role

### 5.3: Integration
- [ ] Add validation step to Orchestrator.process_intent()
- [ ] Run validator on helper response before returning
- [ ] Adjust confidence based on ValidationResult
- [ ] Log validation results

### 5.4: Parallel Validation (Optional)
- [ ] Run multiple validators concurrently
- [ ] Aggregate results (voting/consensus)
- [ ] Performance optimization

---

## Phase 6: Production Deployment 🚀 PLANNED

### 6.1: Docker Container (Optional)
- [ ] Create Dockerfile for Rust backend
- [ ] Multi-stage build (builder + runtime)
- [ ] Minimize image size
- [ ] Test container locally

### 6.2: Pi4 Deployment
- [ ] Copy Rust binary to Pi4
  - [ ] cargo build --release
  - [ ] scp target/release/kairocortex_backend pibbs@192.168.58.7:~/

- [ ] Create systemd service
  - [ ] /etc/systemd/system/kairocortex-backend.service
  - [ ] Environment file for API keys
  - [ ] Auto-restart on failure

- [ ] Integration with Axon BBS startup
  - [ ] Ensure backend starts before Agent
  - [ ] Health check integration

### 6.3: Monitoring
- [ ] Add structured logging (tracing)
- [ ] Log aggregation (journalctl or file)
- [ ] Metrics collection (optional: Prometheus)
- [ ] Error alerting

### 6.4: Security Hardening
- [ ] Verify localhost-only binding
- [ ] API key rotation procedures
- [ ] Log sensitive data filtering
- [ ] Rate limiting on endpoints

---

## Phase 7: Advanced Features 🎯 FUTURE

### 7.1: Helper Chaining
- [ ] Allow helper output to feed another helper
- [ ] Define chain configuration syntax
- [ ] Implement pipeline execution
- [ ] Error handling in chains

### 7.2: Multi-Helper Consensus
- [ ] Query multiple helpers for same intent
- [ ] Implement voting/consensus algorithm
- [ ] Confidence aggregation
- [ ] Performance optimization (parallel queries)

### 7.3: Learning System
- [ ] Track helper performance per intent type
- [ ] Store metrics in database
- [ ] Auto-routing based on historical performance
- [ ] A/B testing framework

### 7.4: Caching Layer
- [ ] Add Redis integration (optional)
- [ ] Cache intent responses with TTL
- [ ] Cache invalidation strategies
- [ ] Performance benchmarking

### 7.5: Compression Optimization
- [ ] Optimize JSON payload sizes
- [ ] Consider binary protocols (MessagePack, Protocol Buffers)
- [ ] Benchmark Tor bandwidth usage
- [ ] Target <2KB per message

---

## Phase 8: Federation 🌐 FUTURE

### 8.1: Remote Cortex Instances
- [ ] Design multi-instance protocol
- [ ] Load balancing between instances
- [ ] Failover handling

### 8.2: Helper Capability Discovery
- [ ] Advertise helper capabilities across federation
- [ ] Route intents to instances with best helpers
- [ ] Capability caching

### 8.3: Distributed Validation
- [ ] 10th Man validation from remote instance
- [ ] Trust model for federated validators
- [ ] Performance implications

---

## Documentation 📚

### Completed
- [x] KAIROCORTEX_AGENT_SPEC.md - Original implementation spec
- [x] KAIROCORTEX_NOTES.md - Personal notes (gitignored)
- [x] KAIROCORTEX_RUST_ARCHITECTURE.md - Complete architecture spec

### Ongoing
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Helper implementation guide
- [ ] Deployment runbook
- [ ] Troubleshooting guide

### Future
- [ ] Performance tuning guide
- [ ] Security audit checklist
- [ ] Contributing guide

---

## Testing Checklist ✅

### Unit Tests
- [ ] Rust: Helper trait implementations
- [ ] Rust: Orchestrator routing logic
- [ ] Rust: Type serialization/deserialization
- [ ] Python: Agent message parsing
- [ ] Python: Agent HTTP client

### Integration Tests
- [ ] End-to-end: Intent → Response flow
- [ ] SSE stream delivery
- [ ] Error handling (timeout, API failure, validation rejection)
- [ ] Authentication (valid/invalid JWT)

### Load Tests
- [ ] Concurrent intent submission (10+ per second)
- [ ] SSE connection scaling (100+ clients)
- [ ] Helper API rate limits
- [ ] Memory usage under load

### Security Tests
- [ ] JWT token validation
- [ ] Localhost binding verification
- [ ] Command injection prevention (Terminal helper)
- [ ] Path traversal prevention (FileSystem helper)

---

## Current Blockers / Questions

None currently - ready to start Phase 3!

---

## Notes

- Keep all file paths relative or configurable via env vars
- No personal info (IPs, usernames) in committed files
- All personal notes in docs/KAIROCORTEX_NOTES.md (gitignored)
- Test on Pi4 after each phase
- Sync changes back to local repo before committing
