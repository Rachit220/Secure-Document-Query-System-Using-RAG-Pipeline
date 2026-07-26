import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
logger = logging.getLogger(__name__)

class PiiType(str, Enum):
    EMAIL = 'EMAIL_ADDRESS'
    PHONE = 'PHONE_NUMBER'
    SSN = 'SSN'
    CREDIT_CARD = 'CREDIT_CARD'
    PASSWORD = 'PASSWORD'
    API_KEY = 'API_KEY'
    IP_ADDRESS = 'IP_ADDRESS'
    NATIONAL_ID = 'NATIONAL_ID'

@dataclass
class PiiEntity:
    entity_type: str
    value: str
    start: int
    end: int
    replacement: str

class PiiSanitizer:
    REGEX_PATTERNS: Dict[str, str] = {PiiType.EMAIL: '\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b', PiiType.PHONE: '(\\+?1[-.\\s]?)?\\(?([0-9]{3})\\)?[-.\\s]?([0-9]{3})[-.\\s]?([0-9]{4})', PiiType.SSN: '\\b\\d{3}-\\d{2}-\\d{4}\\b', PiiType.CREDIT_CARD: '\\b(?:\\d[ -]*?){13,19}\\b', PiiType.PASSWORD: '(?i)(password|passwd|pwd)\\s*[:=]\\s*[^\\s]+', PiiType.API_KEY: '(?i)(api[_\\- ]?key|apikey|secret|token)\\s*[:=]\\s*[^\\s]+', PiiType.IP_ADDRESS: '\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b'}
    REPLACEMENT_TOKENS: Dict[str, str] = {PiiType.EMAIL: '[REDACTED_EMAIL]', PiiType.PHONE: '[REDACTED_PHONE]', PiiType.SSN: '[REDACTED_SSN]', PiiType.CREDIT_CARD: '[REDACTED_CC]', PiiType.PASSWORD: '[REDACTED_PASSWORD]', PiiType.API_KEY: '[REDACTED_API_KEY]', PiiType.IP_ADDRESS: '[REDACTED_IP]', PiiType.NATIONAL_ID: '[REDACTED_NID]'}

    def __init__(self, use_presidio: bool=True):
        self.use_presidio = use_presidio and PRESIDIO_AVAILABLE
        self.detected_entities: List[PiiEntity] = []
        if self.use_presidio:
            try:
                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
                logger.info('Presidio PII Detection Engine initialized')
            except Exception as e:
                logger.warning(f'Failed to initialize Presidio: {e}. Falling back to regex.')
                self.use_presidio = False
        else:
            logger.info('Using regex-based PII detection')

    def sanitize(self, text: str) -> Tuple[str, List[PiiEntity]]:
        self.detected_entities = []
        if self.use_presidio:
            return self._sanitize_presidio(text)
        else:
            return self._sanitize_regex(text)

    def _sanitize_presidio(self, text: str) -> Tuple[str, List[PiiEntity]]:
        try:
            results = self.analyzer.analyze(text=text, languages=['en'], score_threshold=0.5)
            if not results:
                return (text, [])
            anonymization_results = self.anonymizer.anonymize(text=text, analyzer_results=results, operators={entity.entity_type: {'type': 'replace', 'new_value': self.REPLACEMENT_TOKENS.get(entity.entity_type, '[REDACTED]')} for entity in results})
            for entity in results:
                pii = PiiEntity(entity_type=entity.entity_type, value=text[entity.start:entity.end], start=entity.start, end=entity.end, replacement=self.REPLACEMENT_TOKENS.get(entity.entity_type, '[REDACTED]'))
                self.detected_entities.append(pii)
            logger.debug("Presidio detection completed")
            return (anonymization_results.text, self.detected_entities)
        except Exception as e:
            logger.error(f'Presidio sanitization failed: {e}')
            return self._sanitize_regex(text)

    def _sanitize_regex(self, text: str) -> Tuple[str, List[PiiEntity]]:
        sanitized = text
        entities = []
        for pii_type, pattern in self.REGEX_PATTERNS.items():
            replacement = self.REPLACEMENT_TOKENS.get(pii_type, '[REDACTED]')
            for match in re.finditer(pattern, text):
                entity = PiiEntity(entity_type=pii_type, value=match.group(), start=match.start(), end=match.end(), replacement=replacement)
                entities.append(entity)
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        self.detected_entities = entities
        logger.debug(f'Regex detected {len(entities)} PII entities')
        return (sanitized, entities)

    def get_sanitization_report(self) -> Dict:
        report = {'total_entities': len(self.detected_entities), 'by_type': {}}
        for entity in self.detected_entities:
            entity_type = entity.entity_type
            report['by_type'][entity_type] = report['by_type'].get(entity_type, 0) + 1
        return report

class BidirectionalSanitizer:

    def __init__(self):
        self.sanitizer = PiiSanitizer()
        self.original_text: Optional[str] = None
        self.sanitized_text: Optional[str] = None
        self.mapping: List[PiiEntity] = []

    def sanitize_with_mapping(self, text: str) -> Dict:
        self.original_text = text
        self.sanitized_text, self.mapping = self.sanitizer.sanitize(text)
        return {'original_length': len(text), 'sanitized_length': len(self.sanitized_text), 'entities_detected': len(self.mapping), 'sanitized_text': self.sanitized_text, 'entity_types': list(set((e.entity_type for e in self.mapping))), 'report': self.sanitizer.get_sanitization_report()}

    def get_audit_log(self) -> List[Dict]:
        return [{'entity_type': e.entity_type, 'original_position': (e.start, e.end), 'replacement': e.replacement, 'value_length': len(e.value)} for e in self.mapping]