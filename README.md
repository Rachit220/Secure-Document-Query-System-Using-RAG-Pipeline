# Secure Document Query System (RAG Pipeline)

A multi-tenant document querying backend API equipped with automated Personally Identifiable Information (PII) masking, data isolation, and grounded LLM retrieval. Built using Python, FastAPI, LangChain, and ChromaDB.

The system includes an offline Mock AI Mode for cost-free local testing and an interactive dark-themed dashboard UI for visual testing.

---

## 1. System Features & Architecture

* **Multi-Tenant Isolation:** Documents are stored in ChromaDB tagged with explicit `tenant_id` metadata. Retrieval queries enforce strict metadata equality filtering to mathematically prevent cross-tenant data leakage.
* **Automated PII Protection:** Integrated with Microsoft Presidio and customized regex engines to redact SSNs, emails, phone numbers, passwords, API keys, and corporate credentials prior to vector storage.
* **Grounded RAG Pipeline:** Restricts LLM responses strictly to retrieved document context to eliminate hallucinations.
* **Offline Mock AI Mode:** Allows full test execution without active OpenAI API keys or quota expenses.
* **Interactive Dashboard:** Built-in web UI at `http://localhost:8000/` for interactive uploads and query testing.

---

## 2. Installation & Setup

### Prerequisites
* Python 3.11+
* Pip

### Step 1: Environment Setup
```bash
# Clone the repository
git clone https://github.com/Rachit220/Secure-Document-Query-System-Using-RAG-Pipeline.git
cd Secure-Document-Query-System-Using-RAG-Pipeline

# Create and activate virtual environment
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Environment Variables
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your-openai-api-key-here
API_KEY=dev-key-change-in-production
MOCK_AI=true
```

### Step 3: Run the Application
```bash
python main.py
```

* **Visual Dashboard:** Open [http://localhost:8000/](http://localhost:8000/) in your browser.
* **Swagger API Documentation:** Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

---

## 3. API Endpoints

### 1. Ingest Document
* **Method:** `POST`
* **Path:** `/upload`
* **Headers:** `X-API-Key: <your-api-key>`
* **Parameters (Form Data):**
  * `tenant_id` (string)
  * `file` (PDF or DOCX)

### 2. Query Documents
* **Method:** `POST`
* **Path:** `/query`
* **Headers:** `X-API-Key: <your-api-key>`
* **Content-Type:** `application/json`
* **Payload:**
```json
{
  "query": "What are the main terms in the document?",
  "tenant_id": "tenant-001",
  "top_k": 5
}
```

### 3. Health Check
* **Method:** `GET`
* **Path:** `/health`

---

## 4. Comprehensive Testing & Verification Guide

### 4.1 Included Test Dataset
The repository contains two sample documents in the `tests/` folder designed to verify PII masking and tenant boundaries:

* **tests/Test_Employment_Agreement.docx** (HR Domain — `tenant-acme-hr`)
  * **Sensitive fields:** Emails (`john.thompson@corporateclient.com`), Phone (`(555) 234-5678`), SSN (`456-78-9123`), Credit Card (`4532-1488-0343-6467`), Passwords (`MySecurePass2024!#$`), API Keys (`sk_live_stripe_api_key_placeholder_12345`), and PostgreSQL connection strings.
* **tests/Test_Financial_Report.pdf** (Finance Domain — `tenant-finance`)
  * **Sensitive fields:** Executive emails (`robert.williams@acme-corp.com`), Bank Account (`4892847392`), Routing Number (`031000503`), Investment IDs (`INV-847394756`), Passwords (`InvestSecure2024#$%`), and MySQL connection strings.

### 4.2 Test Execution Protocols

#### Protocol 1: Document Ingestion and PII Redaction
Upload Document 1 under HR tenant boundary:
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "X-Tenant-ID: tenant-acme-hr" \
  -F "tenant_id=tenant-acme-hr" \
  -F "file=@tests/Test_Employment_Agreement.docx"
```

Upload Document 2 under Finance tenant boundary:
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "X-Tenant-ID: tenant-finance" \
  -F "tenant_id=tenant-finance" \
  -F "file=@tests/Test_Financial_Report.pdf"
```

* **Verification:** Confirm that `sanitization_report` in the JSON response details entity detection for `EMAIL_ADDRESS`, `PHONE_NUMBER`, `SSN`, `CREDIT_CARD`, and `API_KEY`.

#### Protocol 2: Contextual RAG Retrieval
Grounded Extraction (HR Tenant):
```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the position title for John Thompson?",
    "tenant_id": "tenant-acme-hr",
    "top_k": 5
  }'
```
* **Expected Result:** Answers strictly using document context (*Senior Software Engineer*).

Inbound Query Sanitization:
```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the terms for john.thompson@corporateclient.com?",
    "tenant_id": "tenant-acme-hr",
    "top_k": 5
  }'
```
* **Expected Result:** System masks raw email payload, sets `"sanitization_needed": true`, and retrieves terms.

#### Protocol 3: Multi-Tenant Boundary Isolation (Security Validation)
Test Case A: Cross-Tenant Access (Finance requesting HR data)
```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the employee name?",
    "tenant_id": "tenant-finance",
    "top_k": 5
  }'
```

Test Case B: Cross-Tenant Access (HR requesting Finance data)
```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What was the total revenue?",
    "tenant_id": "tenant-acme-hr",
    "top_k": 5
  }'
```
* **Expected Behavior for both Test Cases:** The API returns 0 context chunks and outputs: *"I cannot find relevant information in your uploaded documents."*

#### Protocol 4: Authentication & Validation Verification
Invalid API Key Request:
```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: invalid-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "tenant_id": "tenant-finance"}'
```
* **Expected Result:** `HTTP 401 Unauthorized` status.

Invalid Tenant Formatting:
```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "tenant_id": "tenant@invalid!"}'
```
* **Expected Result:** `HTTP 400 Bad Request` status.

---

### 4.3 Test Matrix Summary

| Test Criteria | Target Endpoint | Pass Condition |
|---|---|---|
| **Document Parsing** | `POST /upload` | Text extraction from `.docx` and `.pdf` files |
| **PII Detection** | Pre-embedding pipeline | Redaction of emails, SSNs, credit cards, passwords, and keys |
| **Data Isolation** | `POST /query` | Metadata filtering (`tenant_id`) blocks cross-tenant reads |
| **Grounded Output** | `POST /query` | Handles unknown context gracefully without hallucinating |
| **API Security** | Middleware | Unauthorized header rejection with `HTTP 401` |