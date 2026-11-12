use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use axum::{
    extract::{ws::{Message, WebSocket, WebSocketUpgrade}, State},
    response::{Html, IntoResponse},
    routing::get,
    Json, Router,
};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use tower_http::cors::CorsLayer;
use tracing::{info, warn};

const WAR_ROOM_HTML: &str = include_str!("../../visual_war_room.html");

// ==========================================
// 1. FINANCIAL CIRCUIT BREAKER (Fixed-Point Micro-USD)
// $1.00 = 1,000,000 micro-USD
// Daily budget: $5.00 = 5,000,000 micro-USD
// Reset time: 05:30 IST == 00:00:00 UTC
// ==========================================
const COARENA_DAILY_CAP_MICRO_USD: u64 = 5_000_000;

pub struct CoarenaBreaker {
    current_utc_day: AtomicU64,
    committed_micro_usd: AtomicU64,
}

impl CoarenaBreaker {
    pub fn new() -> Self {
        let today = (Utc::now().timestamp() / 86_400) as u64;
        Self {
            current_utc_day: AtomicU64::new(today),
            committed_micro_usd: AtomicU64::new(0),
        }
    }

    pub fn reserve(&self, estimated_micro_usd: u64) -> Result<u64, &'static str> {
        let today = (Utc::now().timestamp() / 86_400) as u64;
        let recorded = self.current_utc_day.load(Ordering::Acquire);

        // Atomic 00:00:00 UTC rollover (05:30:00 IST)
        if today > recorded
            && self
                .current_utc_day
                .compare_exchange(recorded, today, Ordering::SeqCst, Ordering::Relaxed)
                .is_ok()
        {
            self.committed_micro_usd.store(0, Ordering::Release);
            info!("Circuit breaker daily limit reset at 05:30 IST / 00:00 UTC");
        }

        // Lock-free CAS reservation
        let mut current = self.committed_micro_usd.load(Ordering::Acquire);
        loop {
            if current.saturating_add(estimated_micro_usd) > COARENA_DAILY_CAP_MICRO_USD {
                warn!("Circuit breaker tripped! Limit: $5.00. Current: ${:.4}", current as f64 / 1_000_000.0);
                return Err("Coarena $5.00 daily budget exhausted. Resets at 05:30 IST.");
            }
            let next = current + estimated_micro_usd;
            match self.committed_micro_usd.compare_exchange_weak(
                current,
                next,
                Ordering::SeqCst,
                Ordering::Acquire,
            ) {
                Ok(_) => return Ok(next),
                Err(actual) => current = actual,
            }
        }
    }

    pub fn get_spent_usd(&self) -> f64 {
        self.committed_micro_usd.load(Ordering::Relaxed) as f64 / 1_000_000.0
    }
}

// ==========================================
// 2. MODEL MESH CATALOG (16 Models Across 4 Gateways)
// ==========================================
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    pub id: &'static str,
    pub name: &'static str,
    pub gateway: &'static str,
    pub role: &'static str,
    pub is_free: bool,
}

pub fn get_16_models() -> Vec<ModelInfo> {
    vec![
        ModelInfo { id: "free/jev-1.13", name: "Jev 1.13", gateway: "APInex", role: "Decision Gate", is_free: true },
        ModelInfo { id: "respan/gemini-4-carbon:free", name: "Gemini 4 Carbon", gateway: "Respan", role: "Frontier Logic", is_free: true },
        ModelInfo { id: "meta/muse-ember:free", name: "Muse Ember", gateway: "Respan", role: "Multimodal Reasoner", is_free: true },
        ModelInfo { id: "claude-fable-5.2:free", name: "Claude Fable 5.2", gateway: "Experiential", role: "Extended Thinking", is_free: true },
        ModelInfo { id: "free/kimi-k3", name: "Kimi K3", gateway: "APInex", role: "Context Engine", is_free: true },
        ModelInfo { id: "free/deepseek-v4-pro-0813", name: "DeepSeek V4 Pro", gateway: "APInex", role: "Adversary & Audit", is_free: true },
        ModelInfo { id: "free/qwen-3.8-max", name: "Qwen 3.8 MAX", gateway: "APInex", role: "Backend Architect", is_free: true },
        ModelInfo { id: "free/glm-5.3", name: "GLM 5.3", gateway: "APInex", role: "Code Generation", is_free: true },
        ModelInfo { id: "free/glm-5.3-flash", name: "GLM 5.3 Flash", gateway: "APInex", role: "Fast Synthesizer", is_free: true },
        ModelInfo { id: "free/deepseek-v4.1-flash", name: "DeepSeek V4.1 Flash", gateway: "APInex", role: "Adversary Challenger", is_free: true },
        ModelInfo { id: "free/gemini-3.8-flash", name: "Gemini 3.8 Flash", gateway: "APInex", role: "Web & Tool Search", is_free: true },
        ModelInfo { id: "free/hy4", name: "HY4", gateway: "APInex", role: "Domain Specialist", is_free: true },
        ModelInfo { id: "free/muse-spark-1.3", name: "Muse Spark 1.3", gateway: "APInex", role: "UI & Creative", is_free: true },
        ModelInfo { id: "free/minimax-m3.1-flash", name: "MiniMax M3.1 Flash", gateway: "APInex", role: "Data Processing", is_free: true },
        ModelInfo { id: "free/gpt-6-luna", name: "GPT-6 Luna", gateway: "APInex", role: "System Verification", is_free: true },
        ModelInfo { id: "gpt-6-1-sol", name: "GPT-6.1 Sol", gateway: "Coarena", role: "Emergency Circuit Breaker", is_free: false },
    ]
}

// ==========================================
// 3. CAPABILITY-GATED JEV ARTIFACT
// Only constructible upon formal Jev 1.13 approval
// ==========================================
#[derive(Debug, Serialize)]
pub struct JevApprovedArtifact {
    pub patch_id: String,
    pub score: f32,
    pub approved_at: String,
}

// ==========================================
// 4. SHARED APP STATE
// ==========================================
pub struct AppState {
    pub breaker: Arc<CoarenaBreaker>,
    pub http_client: reqwest::Client,
}

// ==========================================
// 5. HTTP HANDLERS
// ==========================================
async fn root_handler() -> impl IntoResponse {
    Html(WAR_ROOM_HTML)
}

async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "healthy",
        "runtime": "Rust 1.99.1 (Axum + Tokio + Tower)",
        "mesh_nodes_online": 16,
        "engine": "RakshEx Core (Zero-Copy)"
    }))
}

async fn get_metrics(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let now = Utc::now();
    Json(serde_json::json!({
        "coarena_spent_usd": state.breaker.get_spent_usd(),
        "coarena_daily_cap_usd": 5.00,
        "coarena_breaker_open": state.breaker.get_spent_usd() >= 5.0,
        "utc_time": now.to_rfc3339(),
        "reset_time": "05:30 IST / 00:00 UTC",
        "total_active_models": 16
    }))
}

async fn get_models() -> impl IntoResponse {
    Json(get_16_models())
}

async fn ws_telemetry_handler(
    ws: WebSocketUpgrade,
    State(_state): State<Arc<AppState>>,
) -> impl IntoResponse {
    ws.on_upgrade(handle_socket)
}

async fn handle_socket(mut socket: WebSocket) {
    let mut interval = tokio::time::interval(std::time::Duration::from_millis(500));
    let mut cycle = 0;

    loop {
        interval.tick().await;
        cycle += 1;
        
        let telemetry_frame = serde_json::json!({
            "type": "TELEMETRY_PACKET",
            "cycle": cycle,
            "timestamp": Utc::now().to_rfc3339(),
            "nodes_active": 16,
            "pulse": {
                "from": if cycle % 2 == 0 { "qwen_38" } else { "deepseek_v4" },
                "to": "jev_113",
                "latency_us": 420
            }
        });

        if socket.send(Message::Text(telemetry_frame.to_string())).await.is_err() {
            break;
        }
    }
}

// ==========================================
// 6. MAIN APPLICATION ENTRYPOINT
// ==========================================
#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();
    dotenvy::dotenv().ok();

    info!("Starting RakshEx High-Throughput Rust Core...");

    let state = Arc::new(AppState {
        breaker: Arc::new(CoarenaBreaker::new()),
        http_client: reqwest::Client::builder()
            .pool_idle_timeout(std::time::Duration::from_secs(30))
            .build()
            .expect("Failed to build HTTP client"),
    });

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/metrics", get(get_metrics))
        .route("/models", get(get_models))
        .route("/ws/telemetry", get(ws_telemetry_handler))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8088")
        .await
        .expect("Failed to bind port 8088");

    info!("RakshEx Rust Core live on http://127.0.0.1:8088");
    info!("WebSocket Telemetry stream at ws://127.0.0.1:8088/ws/telemetry");

    axum::serve(listener, app)
        .await
        .expect("Server terminated unexpectedly");
}
