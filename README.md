# Secure Document Query System (RAG Pipeline)

A multi-tenant document querying backend API with PII (Personally Identifiable Information) masking and tenant data isolation. Built using FastAPI, LangChain, and ChromaDB.

The system is equipped with an offline **Mock AI Mode** that allows full testing without requiring active OpenAI API credits.

---

## Features

* **Multi-Tenant Isolation:** Documents are stored in ChromaDB labeled with a metadata tag (`tenant_id`). The search queries strictly enforce this metadata filter to prevent data mixing between tenants.
* **PII Protection:** Integrated with Microsoft Presidio and customized regex engines to automatically redact SSNs, emails, phone numbers, passwords, API keys, and other sensitive information.
* **Visual Dashboard:** Includes a user interface at `http://localhost:8000/` styled in a dark green and grey theme to test ingestion and queries interactively.
* **Fully Tested:** Over 19 automated integration and unit tests covering all components of text extraction, data masking, and RAG pipelines.

---

## Installation & Setup

### Prerequisites
* Python 3.11
* Pip

### 1. Set Up Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Settings
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your-openai-api-key-here
API_KEY=dev-key-change-in-production

# Enable offline mock testing (avoids OpenAI API costs and quota errors)
MOCK_AI=true
```

---

## Running the Application

Start the FastAPI server:
```powershell
python main.py
```

### Accessing the System
* **Interactive Visual Dashboard:** Open [http://localhost:8000/](http://localhost:8000/) in your browser.
* **API Documentation (Swagger):** Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser. Use the **Authorize** lock button in Swagger to authenticate requests using the configured `API_KEY`.

---

## API Endpoints

### 1. Ingest Document
* **Method:** `POST`
* **Path:** `/upload`
* **Headers:** `X-API-Key: <your-api-key>`
* **Parameters (Form Data):**
  * `tenant_id` (string)
  * `file` (PDF/DOCX file)

### 2. Query Documents
* **Method:** `POST`
* **Path:** `/query`
* **Headers:** `X-API-Key: <your-api-key>`
* **Payload (JSON):**
  ```json
  {
    "query": "What is the key information in the document?",
    "tenant_id": "tenant-001",
    "top_k": 5
  }
  ```

### 3. Health Check
* **Method:** `GET`
* **Path:** `/health`
