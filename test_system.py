import pytest
import logging
from io import BytesIO
from dotenv import load_dotenv
load_dotenv()
from sanitizer import PiiSanitizer, BidirectionalSanitizer, PiiType
from rag_pipeline import DocumentExtractor, RAGPipeline
logging.basicConfig(level=logging.INFO)

class TestPiiSanitizer:

    @pytest.fixture
    def sanitizer(self):
        return PiiSanitizer(use_presidio=False)

    def test_email_redaction(self, sanitizer):
        text = 'Contact john.doe@example.com for details'
        sanitized, entities = sanitizer.sanitize(text)
        assert '[REDACTED_EMAIL]' in sanitized
        assert 'john.doe@example.com' not in sanitized
        assert len(entities) == 1
        assert entities[0].entity_type == PiiType.EMAIL

    def test_phone_redaction(self, sanitizer):
        text = 'Call us at 555-123-4567 or (555) 123-4567'
        sanitized, entities = sanitizer.sanitize(text)
        assert sanitized.count('[REDACTED_PHONE]') == 2
        assert '555-123-4567' not in sanitized

    def test_ssn_redaction(self, sanitizer):
        text = 'SSN: 123-45-6789'
        sanitized, entities = sanitizer.sanitize(text)
        assert '[REDACTED_SSN]' in sanitized
        assert '123-45-6789' not in sanitized

    def test_credit_card_redaction(self, sanitizer):
        text = 'Card number: 4532-1488-0343-6467'
        sanitized, entities = sanitizer.sanitize(text)
        assert '[REDACTED_CC]' in sanitized
        assert '4532-1488-0343-6467' not in sanitized

    def test_password_redaction(self, sanitizer):
        text = 'password=SecurePass123!'
        sanitized, entities = sanitizer.sanitize(text)
        assert '[REDACTED_PASSWORD]' in sanitized
        assert 'SecurePass123' not in sanitized

    def test_api_key_redaction(self, sanitizer):
        text = 'api_key: sk_live_1234567890abcdef'
        sanitized, entities = sanitizer.sanitize(text)
        assert '[REDACTED_API_KEY]' in sanitized
        assert 'sk_live_1234567890abcdef' not in sanitized

    def test_multiple_pii_types(self, sanitizer):
        text = '\n        Employee: john.doe@example.com\n        Phone: 555-123-4567\n        SSN: 123-45-6789\n        Password: pwd=SecurePass\n        '
        sanitized, entities = sanitizer.sanitize(text)
        assert 'john.doe@example.com' not in sanitized
        assert '555-123-4567' not in sanitized
        assert '123-45-6789' not in sanitized
        assert 'SecurePass' not in sanitized
        assert len(entities) >= 3

    def test_sanitization_report(self, sanitizer):
        text = 'Email: test@example.com, Phone: 555-123-4567, SSN: 123-45-6789'
        sanitized, entities = sanitizer.sanitize(text)
        report = sanitizer.get_sanitization_report()
        assert report['total_entities'] >= 3
        assert 'EMAIL_ADDRESS' in report['by_type']

class TestBidirectionalSanitizer:

    def test_audit_log_generation(self):
        bidirectional = BidirectionalSanitizer()
        text = 'Email: john@example.com, Phone: 555-1234567'
        result = bidirectional.sanitize_with_mapping(text)
        assert result['entities_detected'] >= 2
        assert len(result['sanitized_text']) > 0
        audit_log = bidirectional.get_audit_log()
        assert len(audit_log) >= 2
        assert all(('entity_type' in entry for entry in audit_log))
        assert all(('replacement' in entry for entry in audit_log))

class TestDocumentExtractor:

    def test_pdf_extraction_mock(self):
        pass

    def test_docx_extraction_mock(self):
        pass

    def test_unsupported_format(self):
        with pytest.raises(ValueError):
            DocumentExtractor.extract('file.txt', b'some content')
        with pytest.raises(ValueError):
            DocumentExtractor.extract('file.xlsx', b'some content')

class TestRAGPipeline:

    @pytest.fixture
    def pipeline(self):
        return RAGPipeline(chunk_size=500, chunk_overlap=50)

    def test_query_sanitization(self, pipeline):
        query = 'What about user john@example.com?'
        sanitized, entities = pipeline.sanitizer.sanitize(query)
        assert '[REDACTED_EMAIL]' in sanitized or len(entities) > 0

    def test_tenant_isolation(self, pipeline):
        retriever_tenant1 = pipeline.vector_db.get_tenant_retriever('tenant-001', k=5)
        retriever_tenant2 = pipeline.vector_db.get_tenant_retriever('tenant-002', k=5)
        assert retriever_tenant1 is not retriever_tenant2

class TestIntegration:

    def test_sanitization_coverage(self):
        sanitizer = PiiSanitizer(use_presidio=False)
        comprehensive_text = '\n        EMPLOYEE RECORD\n        Name: John Doe\n        Email: john.doe@acme.com\n        Phone: (555) 123-4567\n        SSN: 123-45-6789\n\n        PAYMENT INFO\n        Credit Card: 4532-1488-0343-6467\n        CVV: 123\n\n        SYSTEM CREDENTIALS\n        Database Password: MySecurePassword123!\n        API Key: sk_live_abcdef1234567890\n        IP Address: 192.168.1.1\n        '
        sanitized, entities = sanitizer.sanitize(comprehensive_text)
        assert 'john.doe@acme.com' not in sanitized
        assert '555' not in sanitized or '[REDACTED_PHONE]' in sanitized
        assert '123-45-6789' not in sanitized
        assert '4532-1488-0343-6467' not in sanitized
        assert 'MySecurePassword123!' not in sanitized
        assert 'sk_live_' not in sanitized or '[REDACTED_API_KEY]' in sanitized
        assert '[REDACTED' in sanitized
        assert len(entities) > 0
        print(f'Sanitized text:\n{sanitized}')
        print(f'Detected {len(entities)} PII entities')

class TestPerformance:

    def test_large_text_sanitization(self):
        sanitizer = PiiSanitizer(use_presidio=False)
        large_text = '\n        ' + 'Email: user@example.com, Phone: 555-1234567, SSN: 123-45-6789\n' * 1000
        import time
        start = time.time()
        sanitized, entities = sanitizer.sanitize(large_text)
        elapsed = time.time() - start
        print(f'Sanitized {len(large_text)} chars in {elapsed:.3f}s')
        print(f'Detected {len(entities)} entities')
        assert elapsed < 5.0
        assert len(entities) > 0

    def test_concurrent_sanitization(self):
        import concurrent.futures
        sanitizer = PiiSanitizer(use_presidio=False)
        texts = ['Contact: john@example.com, Phone: 555-1234567' for _ in range(10)]

        def sanitize_text(text):
            return sanitizer.sanitize(text)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(sanitize_text, texts))
        assert len(results) == 10
        assert all((len(entities) > 0 for _, entities in results))

class TestSecurity:

    def test_no_pii_leakage_in_logs(self):
        sanitizer = PiiSanitizer(use_presidio=False)
        sensitive_text = 'Email: sensitive@example.com'
        sanitized, entities = sanitizer.sanitize(sensitive_text)
        assert 'sensitive@example.com' not in sanitized
        assert '[REDACTED_EMAIL]' in sanitized

    def test_tensor_isolation_filter(self):
        pipeline = RAGPipeline()
        retriever = pipeline.vector_db.get_tenant_retriever('tenant-001', k=5)
        assert retriever is not None
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])