#!/usr/bin/env python3
import re
from typing import Dict, List


class RegexEntityExtractor:
    """Simple regex-based entity extractor for BGP queries"""
    
    def __init__(self):
        self.ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        self.prefix_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b')
        self.asn_pattern = re.compile(r'\bAS\s*(\d+)\b', re.IGNORECASE)
        
        self.keywords = {
            "route", "prefix", "path", "bgp", "origin", "as", "rpki", "roa", 
            "routing", "announce", "valid", "invalid", "peer", "hijack"
        }
        
        self.time_words = {
            "yesterday", "today", "now", "current", "hour", "minute", "week", 
            "month", "day", "ago", "since", "last", "this", "recent"
        }
    
    def extract(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from query"""

        all_ips = self.ip_pattern.findall(query)
        prefixes = self.prefix_pattern.findall(query)
        prefix_ips = [p.split('/')[0] for p in prefixes]
        ip_addresses = [ip for ip in all_ips if ip not in prefix_ips]
        asns = self.asn_pattern.findall(query)
        
        query_lower = query.lower()
        keywords = [kw for kw in self.keywords if kw in query_lower]
        time_references = [tw for tw in self.time_words if tw in query_lower]
        
        return {
            "ip_addresses": list(set(ip_addresses)),
            "prefixes": list(set(prefixes)),
            "asns": list(set(asns)),
            "keywords": list(set(keywords)),
            "time_references": list(set(time_references))
        } 