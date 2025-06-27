#!/usr/bin/env python3
import os
import sys
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import duckdb
import gzip
import pickle

from .models.config import ChatBGPConfig, QueryType
from .retrievers.document_retriever import BGPRetriever
from .chains.llm_chain import BGPChain
from .extractors.llm_entity_extractor import LLMEntityExtractor
from .extractors.entity_extractor import RegexEntityExtractor
from .analyzers.heuristic_analyzer import analyze_bgp_discrepancies
from .utils.external_data import fetch_rpki_validation, fetch_whois_data


class ChatBGPRouter:
    """
    Main router that orchestrates BGP analysis components.
    Handles entity extraction, data retrieval, analysis, and response generation.
    """
    
    def __init__(self, config: Optional[ChatBGPConfig] = None):
        self.config = config or ChatBGPConfig()
        
        self.document_retriever = BGPRetriever(self.config)
        self.chain = BGPChain(self.config)
        
        if self.config.entity_extractor == "llm":
            try:
                self.entity_extractor = LLMEntityExtractor()
            except Exception as e:
                if self.config.verbose:
                    print(f"Warning: LLM extractor failed, using regex: {e}")
                self.entity_extractor = RegexEntityExtractor()
        else:
            self.entity_extractor = RegexEntityExtractor()
        
        self._load_radix_trees()
        self._connect_database()
    
    def _load_radix_trees(self):
        """Load radix trees for BGP routing data"""
        self.rtree_v4 = None
        self.rtree_v6 = None
        
        try:
            if os.path.exists(self.config.radix_v4_path) and os.path.exists(self.config.radix_v6_path):
                with gzip.open(self.config.radix_v4_path, "rb") as f:
                    self.rtree_v4 = pickle.load(f)
                with gzip.open(self.config.radix_v6_path, "rb") as f:
                    self.rtree_v6 = pickle.load(f)
                if self.config.verbose:
                    print(f"Loaded radix trees from {self.config.radix_v4_path}")
        except Exception as e:
            if self.config.verbose:
                print(f"Failed to load radix trees: {e}")
        
        if not self.rtree_v4 and self.config.verbose:
            print("Warning: No radix trees loaded. BGP lookups will not work.")
    
    def _connect_database(self):
        """Connect to DuckDB for historical data"""
        self.db_con = None
        
        if os.path.exists(self.config.bgp_database_path):
            try:
                self.db_con = duckdb.connect(self.config.bgp_database_path)
                self.db_con.execute('INSTALL inet; LOAD inet;')
                if self.config.verbose:
                    print(f"Connected to database: {self.config.bgp_database_path}")
            except Exception as e:
                if self.config.verbose:
                    print(f"Failed to connect to database: {e}")
        
        if not self.db_con and self.config.verbose:
            print("Warning: No database connection. Historical queries will not work.")
    
    def determine_query_type(self, query: str, entities: Dict[str, Any]) -> List[str]:
        """Determine what types of data sources are needed"""
        query_lower = query.lower()
        types = []
        static_keywords = [
            "what is", "explain", "definition", "how does", "describe",
            "route flapping", "flapping", "bgp", "border gateway protocol",
            "routing protocol", "autonomous system", "convergence", "rfc"
        ]
        
        if any(keyword in query_lower for keyword in static_keywords):
            types.append(QueryType.STATIC_DOCS)
        
        if entities.get("prefixes") or entities.get("ip_addresses") or entities.get("asns"):
            types.append(QueryType.LIVE_BGP)
        
        if "rpki" in query_lower or "roa" in query_lower or "valid" in query_lower:
            types.append(QueryType.RPKI_VALIDATION)
        
        if "history" in query_lower or "historical" in query_lower or entities.get("time_references"):
            types.append(QueryType.HISTORICAL)
        
        # Default to static docs for concept questions
        if not types:
            types.append(QueryType.STATIC_DOCS)
        
        return types
    
    def get_static_docs(self, query: str, max_docs: int = None) -> List[Dict[str, str]]:
        """Get relevant RFC documentation"""
        max_docs = max_docs or self.config.max_docs
        try:
            docs = self.document_retriever.get_relevant_documents(query)
            result = []
            for doc in docs[:max_docs]:
                source = doc.metadata.get("source", "Unknown")
                rfc_number = "Unknown RFC"
                if source.startswith("rfc") and source.endswith("_clean.txt"):
                    rfc_num = source.replace("rfc", "").replace("_clean.txt", "")
                    rfc_number = f"RFC {rfc_num}"
                
                result.append({
                    "content": doc.page_content,
                    "source": rfc_number,
                    "filename": source
                })
            return result
        except Exception as e:
            if self.config.verbose:
                print(f"Error retrieving static docs: {e}")
            return []
    
    def get_live_bgp_state(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Get current BGP state from radix trees"""
        if not self.rtree_v4 and not self.rtree_v6:
            return {"status": "no_data", "message": "No radix trees available"}
        
        result = {"status": "success", "routes": []}
        
        # prefixes
        for prefix in entities.get("prefixes", []):
            tree = self.rtree_v6 if ":" in prefix else self.rtree_v4
            if tree:
                node = tree.search_exact(prefix)
                if node:
                    result["routes"].append({
                        "type": "exact_match",
                        "prefix": prefix,
                        "data": node.data
                    })
        
        #IP addresses
        for ip in entities.get("ip_addresses", []):
            tree = self.rtree_v6 if ":" in ip else self.rtree_v4
            if tree:
                node = tree.search_best(ip)
                if node:
                    result["routes"].append({
                        "type": "longest_prefix_match", 
                        "ip": ip,
                        "matching_prefix": node.prefix,
                        "data": node.data
                    })
        
        return result
    
    def get_historical_data(self, entities: Dict[str, Any], prefix: str = None) -> List[Dict[str, Any]]:
        """Get historical BGP data from database"""
        if not self.db_con:
            return []
        
        try:
            target_prefix = prefix
            if not target_prefix and entities.get("prefixes"):
                target_prefix = entities["prefixes"][0]
            
            if not target_prefix:
                return []
            
            query = """
                SELECT prefix, origin_as, timestamp, type, as_path 
                FROM bgp_updates 
                WHERE prefix = ? 
                ORDER BY timestamp DESC 
            """
            
            result = self.db_con.execute(query, [target_prefix]).fetchall()
            return [
                {
                    "prefix": row[0],
                    "origin_as": row[1], 
                    "timestamp": row[2],
                    "type": row[3],
                    "as_path": row[4]
                }
                for row in result
            ]
        except Exception as e:
            if self.config.verbose:
                print(f"Error retrieving historical data: {e}")
            return []
    
    def get_validation_data(self, prefix: str, origin_as: str) -> Dict[str, Any]:
        """Get RPKI and IRR validation data"""
        validation_data = {"rpki": {}, "irr": {}}
        
        try:
            rpki_data = fetch_rpki_validation(prefix, origin_as)
            validation_data["rpki"] = rpki_data
        except Exception as e:
            if self.config.verbose:
                print(f"RPKI fetch error: {e}")
        
        try:
            irr_data = fetch_whois_data(prefix)
            validation_data["irr"] = irr_data
        except Exception as e:
            if self.config.verbose:
                print(f"IRR fetch error: {e}")
        
        return validation_data
    
    def query(self, query: str) -> Dict[str, Any]:
        """Main query processing method"""
        start_time = time.time() if self.config.enable_timing else None
        
        # extract entities
        entities = self.entity_extractor.extract(query)
        
        query_types = self.determine_query_type(query, entities)
        
        context_data = {}
        
        if QueryType.STATIC_DOCS in query_types:
            context_data["static_docs"] = self.get_static_docs(query)
        
        if QueryType.LIVE_BGP in query_types:
            context_data["live_bgp"] = self.get_live_bgp_state(entities)
        
        if QueryType.HISTORICAL in query_types:
            context_data["historical"] = self.get_historical_data(entities)
        
        validation_data = None
        if (QueryType.RPKI_VALIDATION in query_types or QueryType.LIVE_BGP in query_types) and \
           context_data.get("live_bgp", {}).get("routes"):
            first_route = context_data["live_bgp"]["routes"][0]
            if "data" in first_route and first_route["data"]:
                route_data = first_route["data"]
                prefix = first_route.get("prefix") or first_route.get("matching_prefix")
                origin_as = route_data.get("origin_as")
                
                if prefix and origin_as:
                    validation_data = self.get_validation_data(prefix, origin_as)
                    context_data["validation"] = validation_data
        
        analysis_result = None
        if context_data.get("live_bgp") and validation_data:
            live_data = context_data["live_bgp"]["routes"][0]["data"] if context_data["live_bgp"]["routes"] else {}
            historical_updates = context_data.get("historical", [])
            
            analysis_result = analyze_bgp_discrepancies(
                live_bgp_data=live_data,
                rpki_data=validation_data.get("rpki", {}),
                irr_data=validation_data.get("irr", {}),
                historical_updates=historical_updates
            )
            context_data["analysis"] = analysis_result
        
        # generate response using LLM chain
        response = self.chain.generate_response(
            query=query,
            entities=entities,
            context_data=context_data,
            query_types=query_types
        )
        
        # add timing
        if self.config.enable_timing and start_time:
            response["timing"] = {
                "total_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
        
        return response 