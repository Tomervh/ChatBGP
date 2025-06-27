
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class ChatBGPConfig:
    """Main configuration for ChatBGP system"""
    
    # Entity extraction
    entity_extractor: str = "llm"  # "llm" or "regex"
    
    # Data paths
    vectorstore_path: str = "data/vectorstore"
    bgp_database_path: str = "data/bgp_data/bgp_rib_snapshot.duckdb"
    radix_v4_path: str = "data/bgp_data/radix_v4_obj.pkl.gz"
    radix_v6_path: str = "data/bgp_data/radix_v6_obj.pkl.gz"
    rfc_documents_path: str = "data/rfc_documents"
    
    # LLM settings
    model_name: str = "gpt-4.1-mini"
    temperature: float = 0.1
    max_tokens: int = 1000
    
    # Retrieval settings
    max_docs: int = 3
    chunk_size: int = 800
    chunk_overlap: int = 100
    
    # Performance settings
    enable_timing: bool = False
    verbose: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.entity_extractor not in ["llm", "regex"]:
            raise ValueError("entity_extractor must be 'llm' or 'regex'")


class QueryType:
    """Query type constants"""
    STATIC_DOCS = "static"          # RFC/documentation only
    LIVE_BGP = "live"               # Current BGP state
    RPKI_VALIDATION = "rpki"        # RPKI validation
    HISTORICAL = "historical"       # Historical BGP data
    HYBRID = "hybrid"               # Multiple sources 