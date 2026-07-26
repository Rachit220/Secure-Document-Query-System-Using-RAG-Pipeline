import os
import json
import requests
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
API_KEY = os.getenv('API_KEY', 'dev-key-change-in-production')
HEADERS_BASE = {'X-API-Key': API_KEY}

class SecureDocQueryClient:

    def __init__(self, base_url: str=BASE_URL, api_key: str=API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()

    def _get_headers(self, tenant_id: str) -> Dict[str, str]:
        headers = HEADERS_BASE.copy()
        headers['X-Tenant-ID'] = tenant_id
        return headers

    def health_check(self) -> Dict:
        try:
            response = self.session.get(f'{self.base_url}/health', timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f'[Error] Health check failed: {e}')
            return {'status': 'error'}

    def get_info(self) -> Dict:
        response = self.session.get(f'{self.base_url}/info')
        response.raise_for_status()
        return response.json()

    def upload_document(self, tenant_id: str, file_path: str) -> Dict:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f'File not found: {file_path}')
        if file_path.suffix.lower() not in ['.pdf', '.docx']:
            raise ValueError('Only PDF and DOCX files are supported')
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f)}
                data = {'tenant_id': tenant_id}
                headers = self._get_headers(tenant_id)
                response = self.session.post(f'{self.base_url}/upload', headers=headers, files=files, data=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            print()
            return result
        except requests.exceptions.RequestException as e:
            print(f'[Error] Upload failed: {e}')
            if hasattr(e.response, 'text'):
                print(f'   Error details: {e.response.text}')
            raise

    def query(self, tenant_id: str, query: str, top_k: int=5) -> Dict:
        payload = {'query': query, 'tenant_id': tenant_id, 'top_k': top_k}
        headers = HEADERS_BASE.copy()
        headers['Content-Type'] = 'application/json'
        try:
            response = self.session.post(f'{self.base_url}/query', headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            print()
            return result
        except requests.exceptions.RequestException as e:
            print(f'[Error] Query failed: {e}')
            if hasattr(e.response, 'text'):
                print(f'   Error details: {e.response.text}')
            raise

    def display_query_result(self, result: Dict):
        print('\n' + '=' * 70)
        print('QUERY RESULT')
        print('=' * 70)
        print(f"\n ANSWER:\n{result['answer']}\n")
        if result['sources']:
            print('SOURCES:')
            for i, source in enumerate(result['sources'], 1):
                print(f"   {i}. {source['filename']} (chunk {source['chunk_id']})")
        else:
            print('SOURCES: None')
        print(f'\n METADATA:')
        print(f"   Tenant: {result['tenant_id']}")
        print(f"   Context Chunks: {result['context_chunks']}")
        print(f"   Avg Relevance: {result['average_relevance_score']:.3f}")
        print(f"   Query Sanitized: {result['sanitization_needed']}")
        print('\n' + '=' * 70)

def example_1_basic_workflow():
    print('\n' + '=' * 70)
    print('EXAMPLE 1: BASIC WORKFLOW')
    print('=' * 70)
    client = SecureDocQueryClient()
    print('\n1.  Checking API health...')
    health = client.health_check()
    print(f"   Status: {health.get('status', 'unknown')}")
    print('\n2.  Retrieving system info...')
    info = client.get_info()
    print(f"   LLM Model: {info['llm_model']}")
    print(f"   Embedding Model: {info['embedding_model']}")
    print(f"   Chunk Size: {info['chunk_size']}")
    print('\n3.  Uploading test document...')
    print('   Note: Create a test PDF/DOCX file or use sample_document.pdf')
    print('\n4.  Querying document...')
    print('   (Skipping actual upload/query - requires real document)')

def example_2_multi_tenant_isolation():
    print('\n' + '=' * 70)
    print('EXAMPLE 2: MULTI-TENANT ISOLATION')
    print('=' * 70)
    client = SecureDocQueryClient()
    tenants = ['tenant-acme', 'tenant-globex', 'tenant-initech']
    print('\n* System architecture ensures:')
    print("  - Each tenant's documents are isolated")
    print("  - Metadata filter: {'tenant_id': {'$eq': tenant_id}}")
    print('  - Vector DB enforces strict equality check')
    print('  - Cross-tenant queries return 0 results')
    for tenant in tenants:
        print(f'\n  Example filter for {tenant}:')
        print(f"    filter_dict = {{'tenant_id': {{'$eq': '{tenant}'}}}}")
        print(f"    -> Only documents with tenant_id='{tenant}' are visible")

def example_3_pii_sanitization_audit():
    print('\n' + '=' * 70)
    print('EXAMPLE 3: PII SANITIZATION AUDIT')
    print('=' * 70)
    print('\n* Automatically detected and redacted:')
    print('  - Email addresses -> [REDACTED_EMAIL]')
    print('  - Phone numbers -> [REDACTED_PHONE]')
    print('  - Social Security numbers -> [REDACTED_SSN]')
    print('  - Credit card numbers -> [REDACTED_CC]')
    print('  - Passwords -> [REDACTED_PASSWORD]')
    print('  - API keys -> [REDACTED_API_KEY]')
    print('  - IP addresses -> [REDACTED_IP]')
    print('\n* Sample audit report:')
    sample_report = {'total_entities': 5, 'by_type': {'EMAIL_ADDRESS': 2, 'PHONE_NUMBER': 2, 'SSN': 1}}
    print(json.dumps(sample_report, indent=2))

def example_4_error_handling():
    print('\n' + '=' * 70)
    print('EXAMPLE 4: ERROR HANDLING')
    print('=' * 70)
    client = SecureDocQueryClient()
    print('\n1.  Invalid tenant ID:')
    try:
        result = client.query('tenant@invalid!', 'What is this?')
    except Exception as e:
        print(f'   * Caught error: {type(e).__name__}')
        print(f'   * Message: {str(e)[:80]}...')
    print('\n2.  Missing document:')
    try:
        result = client.query('tenant-empty', 'What is this?')
        print(f"   * Response: {result.get('answer', 'No answer')[:80]}...")
    except Exception as e:
        print(f'   * Caught error: {type(e).__name__}')
    print('\n3.  Invalid query:')
    try:
        result = client.query('tenant-001', 'hi')
    except Exception as e:
        print(f'   * Caught error: {type(e).__name__}')
        print(f'   * Message: Query must be at least 3 characters')

def example_5_advanced_querying():
    print('\n' + '=' * 70)
    print('EXAMPLE 5: ADVANCED QUERYING TECHNIQUES')
    print('=' * 70)
    print('\n1.  Follow-up questions:')
    print('   Q1: What is the main finding?')
    print('   Q2: Why is that significant?  (follow-up)')
    print('   -> Each query is independent but uses same context')
    print('\n2.  Specific section queries:')
    print("   Q: What does the 'Methodology' section say?")
    print('   -> Chunks include document structure')
    print('\n3.  Negative queries:')
    print('   Q: Is there mention of X in the documents?')
    print("   -> System responds: 'I cannot find...' if not present")
    print('\n4.  Summarization:')
    print('   Q: Summarize the key points')
    print('   -> LLM generates grounded summary from context')

def example_6_production_deployment():
    print('\n' + '=' * 70)
    print('EXAMPLE 6: PRODUCTION DEPLOYMENT')
    print('=' * 70)
    print('\n* Docker deployment:')
    print('  docker-compose -f docker-compose.yml up -d')
    print('\n* Environment configuration:')
    print('  OPENAI_API_KEY=sk_...        # Required')
    print('  API_KEY=<strong-random-key>  # Change from default!')
    print('  WORKERS=4                    # For production')
    print('  USE_PRESIDIO=true           # Enable PII detection')
    print('\n* Vector database options:')
    print('  - Local: ChromaDB (dev, small deployments)')
    print('  - Production: PostgreSQL + PgVector')
    print('  - Serverless: Pinecone or Weaviate')
    print('\n* Monitoring:')
    print('  - Prometheus metrics on port 9090')
    print('  - Grafana dashboards on port 3000')
    print('  - Structured JSON logging')
    print('\n* Security best practices:')
    print('  - Use strong API keys')
    print('  - Enable HTTPS/TLS')
    print('  - Implement rate limiting')
    print('  - Audit log all operations')
    print('  - Regular security updates')

def main():
    print('\n' + '=' * 70)
    print('SECURE DOCUMENT QUERY SYSTEM - USAGE EXAMPLES')
    print('=' * 70)
    try:
        example_1_basic_workflow()
        example_2_multi_tenant_isolation()
        example_3_pii_sanitization_audit()
        example_4_error_handling()
        example_5_advanced_querying()
        example_6_production_deployment()
        print('\n' + '=' * 70)
        print('[Success] EXAMPLES COMPLETED')
        print('=' * 70)
        print('\nNext steps:')
        print('1. Install dependencies: pip install -r requirements.txt')
        print('2. Set OpenAI API key: export OPENAI_API_KEY=sk_...')
        print('3. Start server: python main.py')
        print('4. Test API: curl http://localhost:8000/health')
        print('5. Upload document: POST /upload')
        print('6. Query document: POST /query')
    except Exception as e:
        print(f'\n[Error] Error: {e}', exc_info=True)
if __name__ == '__main__':
    main()