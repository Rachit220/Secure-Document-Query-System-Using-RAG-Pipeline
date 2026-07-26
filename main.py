import os
import logging
import traceback
from typing import Optional, List
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    status,
    Depends,
    Header,
)
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn

from rag_pipeline import RAGPipeline, UploadMetadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SourceInfo(BaseModel):
    filename: str
    chunk_id: int


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    context_chunks: int = Field(..., description="Number of context chunks retrieved")
    average_relevance_score: float = Field(
        ..., description="Average similarity score of retrieved chunks"
    )
    tenant_id: str
    sanitization_needed: bool = Field(
        ..., description="Whether user query contained PII that was sanitized"
    )


class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: str
    tenant_id: str
    file_hash: str
    upload_timestamp: str
    file_size: int
    content_length: int
    chunk_count: int
    sanitization_report: dict


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    tenant_id: str = Field(..., min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v):
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("tenant_id must contain only alphanumeric, dash, or underscore")
        return v


class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict


rag_pipeline: Optional[RAGPipeline] = None


def get_tenant_id(tenant_id: str = Header(..., alias="X-Tenant-ID")) -> str:
    if not tenant_id or not all(c.isalnum() or c in "-_" for c in tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format",
        )
    return tenant_id


from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    expected_key = os.getenv("API_KEY", "dev-key-change-in-production")
    
    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_pipeline
    logger.info("Initializing RAG Pipeline...")

    try:
        rag_pipeline = RAGPipeline(
            chroma_persist_dir=os.getenv("CHROMA_DB_PATH", "./chroma_db"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 100)),
        )
        logger.info("RAG Pipeline initialized successfully")

        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set in environment")

    except Exception as e:
        logger.error(f"Failed to initialize RAG Pipeline: {e}", exc_info=True)
        raise

    yield
    logger.info("Shutting down RAG Pipeline...")


app = FastAPI(
    title="Secure Document Query System",
    description="Multi-tenant RAG API with PII protection and vector-based retrieval",
    version="1.0.0",
    lifespan=lifespan,
)


HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Document Query System - Interview Assignment</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #121214;
            --panel-bg: #1e1e24;
            --border-color: #2b302c;
            --primary: #134e32;
            --primary-light: #217a4c;
            --accent: #52b788;
            --text-main: #e9ecef;
            --text-muted: #9ba4b0;
            --dark-grey: #2d3142;
            --light-grey: #3b4252;
            --alert-bg: rgba(82, 183, 136, 0.05);
            --redact-bg: rgba(247, 127, 0, 0.15);
            --redact-text: #f77f00;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.6;
            padding: 2rem 1.5rem;
            display: flex;
            justify-content: center;
        }

        .container {
            max-width: 1280px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem;
            background: linear-gradient(135deg, #1b201d, #141715);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        .header-title h1 {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 0.6rem;
            letter-spacing: -0.02em;
        }

        .header-title p {
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-top: 0.2rem;
        }

        .header-badge {
            background-color: rgba(33, 122, 76, 0.15);
            border: 1px solid rgba(82, 183, 136, 0.3);
            color: var(--accent);
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .config-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            padding: 1.25rem;
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            flex: 1;
            min-width: 200px;
        }

        label {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        input, select {
            background-color: #121214;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.65rem 1rem;
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.25s ease;
        }

        input:focus, select:focus {
            border-color: var(--accent);
            box-shadow: 0 0 8px rgba(82, 183, 136, 0.25);
        }

        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 1.5rem;
        }

        @media (max-width: 960px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }

        .card {
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.75rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
            margin-bottom: 0.25rem;
        }

        .card h2 {
            font-size: 1.3rem;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .dropzone {
            border: 2px dashed rgba(82, 183, 136, 0.3);
            background-color: rgba(18, 18, 20, 0.6);
            padding: 3rem 2rem;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.8rem;
        }

        .dropzone:hover, .dropzone.dragover {
            border-color: var(--accent);
            background-color: rgba(82, 183, 136, 0.04);
            transform: translateY(-2px);
        }

        .dropzone-icon {
            font-size: 2.2rem;
            color: var(--accent);
        }

        .dropzone p {
            color: var(--text-muted);
            font-size: 0.9rem;
        }

        .btn {
            background-color: var(--primary);
            color: #ffffff;
            border: 1px solid rgba(82, 183, 136, 0.2);
            padding: 0.8rem 1.75rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            justify-content: center;
            align-items: center;
            gap: 0.6rem;
        }

        .btn:hover {
            background-color: var(--primary-light);
            box-shadow: 0 4px 12px rgba(33, 122, 76, 0.25);
            transform: translateY(-1px);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn-accent {
            background-color: var(--accent);
            color: #121214;
            border: none;
        }

        .btn-accent:hover {
            background-color: #74c69d;
            box-shadow: 0 4px 12px rgba(82, 183, 136, 0.3);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
            box-shadow: none !important;
        }

        #file-info {
            font-size: 0.9rem;
            color: var(--accent);
            font-weight: 500;
            background-color: rgba(82, 183, 136, 0.06);
            padding: 0.5rem 1rem;
            border-radius: 6px;
            width: 100%;
            text-align: center;
            display: none;
        }

        .log-section {
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
        }

        .console {
            background-color: #121214;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            color: #e9ecef;
            min-height: 120px;
            max-height: 250px;
            overflow-y: auto;
            white-space: pre-wrap;
        }

        .chat-container {
            border: 1px solid var(--border-color);
            background-color: #121214;
            border-radius: 10px;
            padding: 1.25rem;
            height: 380px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .chat-message {
            max-width: 85%;
            padding: 0.85rem 1.1rem;
            border-radius: 14px;
            font-size: 0.92rem;
            line-height: 1.5;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .msg-user {
            background-color: var(--primary);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 3px;
            box-shadow: 0 2px 8px rgba(19, 78, 50, 0.3);
        }

        .msg-bot {
            background-color: #242926;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            align-self: flex-start;
            border-bottom-left-radius: 3px;
        }

        .msg-system {
            background-color: rgba(33, 122, 76, 0.05);
            border: 1px dashed rgba(82, 183, 136, 0.2);
            color: var(--accent);
            align-self: center;
            font-size: 0.8rem;
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            text-align: center;
            max-width: 100%;
        }

        .sources-list {
            margin-top: 0.6rem;
            padding-top: 0.6rem;
            border-top: 1px solid var(--border-color);
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
        }

        .source-tag {
            background-color: #1b201d;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
        }

        .query-box {
            display: flex;
            gap: 0.6rem;
            margin-top: 0.25rem;
        }

        .query-box input {
            flex: 1;
            padding: 0.8rem 1.1rem;
            border-radius: 8px;
        }

        .pii-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 0.6rem;
            margin-top: 0.5rem;
        }

        .pii-stat-card {
            background-color: #121214;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.75rem;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }

        .pii-count {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--redact-text);
        }

        .pii-label {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .redacted-span {
            background-color: var(--redact-bg);
            color: var(--redact-text);
            padding: 0.1rem 0.35rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 500;
            font-size: 0.8rem;
            border: 1px solid rgba(247, 127, 0, 0.2);
        }

        .loader-ring {
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            border-top-color: #ffffff;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .card-desc {
            font-size: 0.88rem;
            color: var(--text-muted);
            line-height: 1.4;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <h1>🛡️ Secure Document Query System</h1>
                <p>Enterprise multi-tenant RAG pipeline featuring strict data isolation and Presidio PII masking</p>
            </div>
            <div class="header-badge">Mock AI Active</div>
        </header>

        <!-- Configuration Bar -->
        <div class="config-bar">
            <div class="form-group">
                <label for="api-key-input">Authentication Key (X-API-Key)</label>
                <input type="text" id="api-key-input" value="dev-key-change-in-production" placeholder="Enter API Key">
            </div>
            <div class="form-group">
                <label for="tenant-id-input">Active Tenant ID (Data Isolation)</label>
                <input type="text" id="tenant-id-input" value="tenant-001" placeholder="e.g. tenant-001, tenant-002">
            </div>
        </div>

        <div class="main-grid">
            <!-- Left Side: Ingestion and Sanitization Report -->
            <div class="card">
                <div class="card-header">
                    <h2>Ingest Document</h2>
                </div>
                <p class="card-desc">
                    Upload PDF or DOCX files. The backend will parse text, run it through the PII sanitizer, and register chunks into the vector store.
                </p>

                <div class="dropzone" id="drop-zone">
                    <div class="dropzone-icon">📤</div>
                    <p><strong>Drag & Drop PDF/DOCX</strong> or click to browse</p>
                    <p style="font-size: 0.75rem;">Supported formats: PDF, DOCX (Max 10MB)</p>
                    <input type="file" id="file-input" accept=".pdf,.docx" style="display: none;">
                </div>

                <div id="file-info">Selected: <span id="filename-span"></span></div>

                <button class="btn btn-accent" id="upload-btn" disabled>
                    <span>Ingest Document</span>
                    <div class="loader-ring" id="upload-spinner" style="display: none;"></div>
                </button>

                <div class="log-section">
                    <label>Ingestion Server Logs & Metadata</label>
                    <div class="console" id="upload-console">Waiting for document upload...</div>
                </div>

                <div class="log-section" id="pii-report-section" style="display: none;">
                    <label>PII Sanitization Audit Report</label>
                    <div class="pii-grid" id="pii-stats-container"></div>
                </div>
            </div>

            <!-- Right Side: RAG Query Chat Interface -->
            <div class="card">
                <div class="card-header">
                    <h2>RAG Inquiries</h2>
                </div>
                <p class="card-desc">
                    Ask questions bounded strictly to the active tenant's document base. Cross-tenant retrieval is mathematically impossible.
                </p>

                <div class="chat-container" id="chat-container">
                    <div class="chat-message msg-system">
                        Enter queries to query document base for tenant.
                    </div>
                </div>

                <div class="query-box">
                    <input type="text" id="query-input" placeholder="Type your query here..." disabled>
                    <button class="btn btn-accent" id="query-btn" disabled>
                        <span>Ask</span>
                        <div class="loader-ring" id="query-spinner" style="display: none;"></div>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const fileInfo = document.getElementById('file-info');
        const filenameSpan = document.getElementById('filename-span');
        const uploadBtn = document.getElementById('upload-btn');
        const uploadSpinner = document.getElementById('upload-spinner');
        const uploadConsole = document.getElementById('upload-console');
        const piiReportSection = document.getElementById('pii-report-section');
        const piiStatsContainer = document.getElementById('pii-stats-container');

        const chatContainer = document.getElementById('chat-container');
        const queryInput = document.getElementById('query-input');
        const queryBtn = document.getElementById('query-btn');
        const querySpinner = document.getElementById('query-spinner');

        const apiKeyInput = document.getElementById('api-key-input');
        const tenantIdInput = document.getElementById('tenant-id-input');

        let selectedFile = null;

        // Dropzone drag & drop handlers
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileSelect);

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                handleFileSelect();
            }
        });

        function handleFileSelect() {
            if (fileInput.files.length > 0) {
                selectedFile = fileInput.files[0];
                filenameSpan.textContent = selectedFile.name;
                fileInfo.style.display = 'block';
                uploadBtn.disabled = false;
            }
        }

        // Document Upload handler
        uploadBtn.addEventListener('click', async () => {
            if (!selectedFile) return;

            const apiKey = apiKeyInput.value.trim();
            const tenantId = tenantIdInput.value.trim();

            if (!apiKey || !tenantId) {
                alert('Please ensure X-API-Key and Tenant ID are set.');
                return;
            }

            uploadBtn.disabled = true;
            uploadSpinner.style.display = 'inline-block';
            uploadConsole.textContent = 'Ingesting document... parsing pages and applying PII mask...';

            const formData = new FormData();
            formData.append('tenant_id', tenantId);
            formData.append('file', selectedFile);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    headers: {
                        'X-API-Key': apiKey
                    },
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    uploadConsole.textContent = JSON.stringify(data, null, 2);
                    displayPiiReport(data.sanitization_report);
                    queryInput.disabled = false;
                    queryBtn.disabled = false;

                    // Add system chat confirmation
                    appendChatMessage(`System: Ingested "${data.filename}" (${data.chunk_count} chunks stored).`, 'msg-system');
                } else {
                    uploadConsole.textContent = `Error ${response.status}: ${data.detail || data.error || 'Upload failed'}`;
                }
            } catch (err) {
                uploadConsole.textContent = `Upload network error: ${err.message}`;
            } finally {
                uploadBtn.disabled = false;
                uploadSpinner.style.display = 'none';
            }
        });

        function displayPiiReport(report) {
            piiStatsContainer.innerHTML = '';
            if (!report || report.total_entities === 0) {
                piiReportSection.style.display = 'block';
                piiStatsContainer.innerHTML = '<div style="grid-column: 1/-1; color: var(--accent); font-size: 0.9rem;">No PII detected. Document is naturally clean!</div>';
                return;
            }

            piiReportSection.style.display = 'block';
            
            // Total entities card
            const totalCard = document.createElement('div');
            totalCard.className = 'pii-stat-card';
            totalCard.innerHTML = `
                <div class="pii-count">${report.total_entities}</div>
                <div class="pii-label">Redacted Items</div>
            `;
            piiStatsContainer.appendChild(totalCard);

            // Group cards
            for (const [type, count] of Object.entries(report.by_type || {})) {
                const card = document.createElement('div');
                card.className = 'pii-stat-card';
                card.innerHTML = `
                    <div class="pii-count" style="color: var(--accent);">${count}</div>
                    <div class="pii-label">${type.replace('_', ' ')}</div>
                `;
                piiStatsContainer.appendChild(card);
            }
        }

        // Query Inquiry handler
        queryBtn.addEventListener('click', executeQuery);
        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') executeQuery();
        });

        async function executeQuery() {
            const queryText = queryInput.value.trim();
            const apiKey = apiKeyInput.value.trim();
            const tenantId = tenantIdInput.value.trim();

            if (!queryText) return;
            if (!apiKey || !tenantId) {
                alert('Please ensure X-API-Key and Tenant ID are set.');
                return;
            }

            // Append user query to chat
            appendChatMessage(queryText, 'msg-user');
            queryInput.value = '';
            queryInput.disabled = true;
            queryBtn.disabled = true;
            querySpinner.style.display = 'inline-block';

            try {
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: {
                        'X-API-Key': apiKey,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: queryText,
                        tenant_id: tenantId,
                        top_k: 3
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    let botContent = data.answer;
                    
                    // Format sources if present
                    if (data.sources && data.sources.length > 0) {
                        botContent += '<div class="sources-list">';
                        data.sources.forEach(src => {
                            botContent += `<span class="source-tag">📄 ${src.filename} (Chunk ${src.chunk_id})</span>`;
                        });
                        botContent += '</div>';
                    }
                    
                    appendChatMessage(botContent, 'msg-bot');
                } else {
                    appendChatMessage(`Error ${response.status}: ${data.detail || data.error || 'Failed to process RAG query.'}`, 'msg-bot');
                }
            } catch (err) {
                appendChatMessage(`Inquiry error: ${err.message}`, 'msg-bot');
            } finally {
                queryInput.disabled = false;
                queryBtn.disabled = false;
                querySpinner.style.display = 'none';
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }

        function appendChatMessage(content, className) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `chat-message ${className}`;
            msgDiv.innerHTML = content;
            chatContainer.appendChild(msgDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return HTMLResponse(content=HTML_CONTENT, status_code=200)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    components_status = {
        "rag_pipeline": "initialized" if rag_pipeline is not None else "not_initialized",
        "vector_db": "ready" if rag_pipeline is not None else "not_ready",
    }

    return HealthResponse(
        status="healthy" if all(v == "initialized" or v == "ready" for v in components_status.values()) else "degraded",
        version="1.0.0",
        components=components_status,
    )


@app.get("/info")
async def info():
    return {
        "service": "Secure Document Query System",
        "version": "1.0.0",
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "llm_model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "chunk_size": int(os.getenv("CHUNK_SIZE", 1000)),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", 100)),
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    api_key: str = Depends(get_api_key),
) -> UploadResponse:
    logger.info(f"Upload request from tenant {tenant_id}, file: {file.filename}")

    if rag_pipeline is None:
        logger.error("RAG Pipeline not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready",
        )

    try:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must have a name",
            )

        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ["pdf", "docx"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and DOCX files are supported",
            )

        file_content = await file.read()
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty",
            )

        metadata: UploadMetadata = rag_pipeline.ingest_document(
            tenant_id=tenant_id,
            filename=file.filename,
            file_content=file_content,
        )

        sanitization_report = rag_pipeline.sanitizer.get_sanitization_report()

        logger.info(f"Document uploaded for tenant {tenant_id}")

        return UploadResponse(
            success=True,
            message=f"Document processed successfully. {metadata.chunk_count} chunks created.",
            filename=metadata.filename,
            tenant_id=metadata.tenant_id,
            file_hash=metadata.file_hash,
            upload_timestamp=metadata.upload_timestamp,
            file_size=metadata.file_size,
            content_length=metadata.content_length,
            chunk_count=metadata.chunk_count,
            sanitization_report=sanitization_report,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


@app.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    api_key: str = Depends(get_api_key),
) -> QueryResponse:
    tenant_id = request.tenant_id
    user_query = request.query
    top_k = request.top_k

    logger.info(
        f"Query from tenant {tenant_id}: {user_query[:80]}... (top_k={top_k})"
    )

    if rag_pipeline is None:
        logger.error("RAG Pipeline not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready",
        )

    try:
        result = rag_pipeline.query(
            tenant_id=tenant_id,
            user_query=user_query,
            k=top_k,
        )

        sources = [
            SourceInfo(
                filename=source.get("filename", "unknown"),
                chunk_id=source.get("chunk_id", -1),
            )
            for source in result["sources"]
        ]

        logger.info("Query successfully processed")

        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            context_chunks=result["context_chunks"],
            average_relevance_score=result["average_relevance_score"],
            tenant_id=result["tenant_id"],
            sanitization_needed=result["sanitization_needed"],
        )

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}",
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
        },
    )


def get_config() -> dict:
    config = {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "chroma_db_path": os.getenv("CHROMA_DB_PATH", "./chroma_db"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "llm_model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "chunk_size": int(os.getenv("CHUNK_SIZE", "1000")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "100")),
        "api_key": os.getenv("API_KEY", "dev-key-change-in-production"),
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", "8000")),
        "workers": int(os.getenv("WORKERS", "1")),
        "use_presidio": os.getenv("USE_PRESIDIO", "true").lower() == "true",
    }
    return config


if __name__ == "__main__":
    config = get_config()

    if not config["openai_api_key"]:
        logger.warning(
            "OPENAI_API_KEY not set. Please set it before running the server."
        )

    logger.info("Starting Secure Document Query System...")
    logger.info(f"Configuration: {config}")

    uvicorn.run(
        "main:app",
        host=config["host"],
        port=config["port"],
        workers=config["workers"],
        log_level="info",
        reload=False,
    )