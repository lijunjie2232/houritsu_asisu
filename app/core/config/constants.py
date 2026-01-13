# Constants for Japanese Law AI Agent

# Legal document types
LEGAL_DOC_TYPES = [
    "constitution",
    "statute",
    "ordinance",
    "regulation",
    "court_decision",
    "legal_interpretation",
]

# Legal categories in Japan
LEGAL_CATEGORIES = [
    "constitutional_law",
    "civil_law",
    "criminal_law",
    "commercial_law",
    "administrative_law",
    "tax_law",
    "labor_law",
    "family_law",
    "succession_law",
    "real_property_law",
    "intellectual_property_law",
    "contract_law",
    "tort_law",
]

# Japanese legal periods
LEGAL_PERIODS = ["meiji", "taisho", "showa", "heisei", "reiwa"]

# Response templates
RESPONSE_TEMPLATES = {
    "law_citation": "{law_name} ({law_number}), Article {article_number}",
    "court_decision_citation": "{court_level}, {date}, {case_number}",
    "interpretation_citation": "Constitutional/Legal Interpretation No. {number}",
}

# Error messages
ERROR_MESSAGES = {
    "NO_RELEVANT_LAW": "申し訳ありませんが、ご質問に関連する法律が見つかりませんでした。",
    "GENERAL_INFO_ONLY": "私はAIアシスタントです。法的助言はできません。専門の弁護士にご相談ください。",
    "UNKNOWN_ERROR": "エラーが発生しました。後ほど再度お試しください。",
}

# Default values
DEFAULT_TOP_K = 5
DEFAULT_SEARCH_RADIUS = 1.0
