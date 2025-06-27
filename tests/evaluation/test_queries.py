#!/usr/bin/env python3
"""
Test Query Definitions for ChatBGP Evaluation

Contains all test cases for comprehensive evaluation including:
- Entity extraction evaluation (ASNs, prefixes, IPs, keywords)
- RAG retrieval evaluation (RFC document retrieval)

Organized by test type and difficulty level.
"""

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class RAGTestQuery:
    """Test query for RAG retrieval evaluation with expected relevant documents"""
    query: str
    expected_docs: List[str]  # List of document IDs that should be retrieved
    description: str          # Why these documents are relevant


def get_easy_test_cases() -> List[Dict]:
    """Simple BGP queries with straightforward entity extraction"""
    return [
        {
            "query": "What prefixes are originated by AS15169?",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixes", "originated"],
                "time_references": []
            }
        },
        {
            "query": "Can you tell me about prefixes from ASN 15169",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixes", "ASN"],
                "time_references": []
            }
        },
        {
            "query": "Show information for prefixes by the company with number 15169",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixes", "company"],
                "time_references": []
            }
        },
        {
            "query": "What routes are announced by Google (AS15169)",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["routes", "announced", "Google"],
                "time_references": []
            }
        },
        {
            "query": "Tell me about AS-15169 announcements",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["announcements"],
                "time_references": []
            }
        },
        {
            "query": "What about autonomous system 15169?",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["autonomous system"],
                "time_references": []
            }
        },
        {
            "query": "Information about subnets with prefix 8.8.8/24",
            "ground_truth": {
                "asns": [],
                "prefixes": ["8.8.8.0/24"],
                "ip_addresses": [],
                "keywords": ["subnets", "prefix"],
                "time_references": []
            }
        },
        {
            "query": "Show me routes for eight.eight.eight.eight",
            "ground_truth": {
                "asns": [],
                "prefixes": [],
                "ip_addresses": ["8.8.8.8"],
                "keywords": ["routes"],
                "time_references": []
            }
        },
        {
            "query": "What about prefix 8 8 8 0 slash 24",
            "ground_truth": {
                "asns": [],
                "prefixes": ["8.8.8.0/24"],
                "ip_addresses": [],
                "keywords": ["prefix"],
                "time_references": []
            }
        },
        {
            "query": "AS15169 is announcing 8.8.8/24 and AS-13335 has 1.1.1/24",
            "ground_truth": {
                "asns": ["15169", "13335"],
                "prefixes": ["8.8.8.0/24", "1.1.1.0/24"],
                "ip_addresses": [],
                "keywords": ["announcing"],
                "time_references": []
            }
        }
    ]


def get_hard_test_cases() -> List[Dict]:
    """Complex BGP queries with multiple entities and relationships"""
    return [
        {
            "query": "Compare Google (AS15169) and Cloudflare (AS13335) prefixes from last week",
            "ground_truth": {
                "asns": ["15169", "13335"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixes", "compare"],
                "time_references": ["last week"]
            }
        },
        {
            "query": "What prefixes come from autonomous system number 15169 since yesterday?",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixes", "autonomous system"],
                "time_references": ["yesterday", "since"]
            }
        },
        {
            "query": "Show AS path from AS-15169 via ASN3356 to AS701 for 8.8.8.0/24 at 14:30 UTC",
            "ground_truth": {
                "asns": ["15169", "3356", "701"],
                "prefixes": ["8.8.8.0/24"],
                "ip_addresses": [],
                "keywords": ["AS path", "via"],
                "time_references": ["14:30", "UTC"]
            }
        },
        {
            "query": "Check if autonomous system 13335 and AS15169 are announcing 1.1.1.0/24 and 8.8.8.0/24 respectively",
            "ground_truth": {
                "asns": ["13335", "15169"],
                "prefixes": ["1.1.1.0/24", "8.8.8.0/24"],
                "ip_addresses": [],
                "keywords": ["autonomous system", "announcing"],
                "time_references": []
            }
        },
        {
            "query": "Find routes from AS15169 and AS-13335 to 8.8.8.8 and 1.1.1.1 before 2024-01-01",
            "ground_truth": {
                "asns": ["15169", "13335"],
                "prefixes": [],
                "ip_addresses": ["8.8.8.8", "1.1.1.1"],
                "keywords": ["routes"],
                "time_references": ["2024-01-01", "before"]
            }
        },
        {
            "query": "What prefixes did autonomous system fifteen one six nine announce between March 1st and March 2nd?",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixes", "autonomous system", "announce"],
                "time_references": ["March 1st", "March 2nd", "between"]
            }
        },
        {
            "query": "Show me BGP updates for prefix eight dot eight dot eight dot zero slash twenty-four from AS one five one six nine",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": ["8.8.8.0/24"],
                "ip_addresses": [],
                "keywords": ["BGP", "updates"],
                "time_references": []
            }
        },
        {
            "query": "Compare routes for subnets 192.168.0.0/16 and 10.0.0.0/8 from ASN-12345 during the outage",
            "ground_truth": {
                "asns": ["12345"],
                "prefixes": ["192.168.0.0/16", "10.0.0.0/8"],
                "ip_addresses": [],
                "keywords": ["routes", "subnets", "outage"],
                "time_references": ["during"]
            }
        },
        {
            "query": "Check announcements from Google's AS and Cloudflare's autonomous system for their public DNS IPs",
            "ground_truth": {
                "asns": ["15169", "13335"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["announcements", "Google", "Cloudflare", "autonomous system", "public DNS"],
                "time_references": []
            }
        },
        {
            "query": "Find all prefixes from AS one-five-one-six-nine containing IP eight.eight.eight.eight",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": ["8.8.8.8"],
                "keywords": ["prefixes", "containing"],
                "time_references": []
            }
        }
    ]


def get_spelling_mistake_cases() -> List[Dict]:
    """Test cases with common typos and spelling mistakes"""
    return [
        {
            "query": "What prefixs are anounced by AS fiften one six nine?",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixs", "anounced"],
                "time_references": []
            }
        },
        {
            "query": "Check BGP updats from AS-13three3five",
            "ground_truth": {
                "asns": ["13335"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["BGP", "updats"],
                "time_references": []
            }
        },
        {
            "query": "Show me the route for ate.ate.ate.ate",
            "ground_truth": {
                "asns": [],
                "prefixes": [],
                "ip_addresses": ["8.8.8.8"],
                "keywords": ["route"],
                "time_references": []
            }
        },
        {
            "query": "What hapened to AS15169s prefixs yesterday?",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixs", "hapened"],
                "time_references": ["yesterday"]
            }
        },
        {
            "query": "Find routes from AS-15169 n AS13335 to 8.8.8.8 n 1.1.1.1",
            "ground_truth": {
                "asns": ["15169", "13335"],
                "prefixes": [],
                "ip_addresses": ["8.8.8.8", "1.1.1.1"],
                "keywords": ["routes"],
                "time_references": []
            }
        },
        {
            "query": "Compare prefixs from AS15169 n AS13335 during outge",
            "ground_truth": {
                "asns": ["15169", "13335"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["prefixs", "outge"],
                "time_references": ["during"]
            }
        },
        {
            "query": "Check if AS15169 iz anouncing 8.8.8.0/24 since lst week",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": ["8.8.8.0/24"],
                "ip_addresses": [],
                "keywords": ["anouncing"],
                "time_references": ["lst week", "since"]
            }
        },
        {
            "query": "What routes r available 4 prefix 8.8.8.0/24 frm AS15169?",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": ["8.8.8.0/24"],
                "ip_addresses": [],
                "keywords": ["routes"],
                "time_references": []
            }
        },
        {
            "query": "Give me d BGP updats 4 AS15169 n AS13335",
            "ground_truth": {
                "asns": ["15169", "13335"],
                "prefixes": [],
                "ip_addresses": [],
                "keywords": ["BGP", "updats"],
                "time_references": []
            }
        },
        {
            "query": "Look for prefixs containin IP 8.8.8.8 frm AS15169",
            "ground_truth": {
                "asns": ["15169"],
                "prefixes": [],
                "ip_addresses": ["8.8.8.8"],
                "keywords": ["prefixs", "containin"],
                "time_references": []
            }
        }
    ]


def get_edge_cases() -> List[Dict]:
    """Edge cases and tricky scenarios"""
    return [
        {
            "query": "AS path 174 3356 1299 65001 shows route to 192.0.2.0/24 but not 192.0.2.1",
            "ground_truth": {
                "asns": ["174", "3356", "1299", "65001"],
                "prefixes": ["192.0.2.0/24"],
                "ip_addresses": ["192.0.2.1"],
                "keywords": ["AS path", "route"],
                "time_references": []
            }
        },
        {
            "query": "Check 2001:db8::1/128 vs 2001:db8::/64 announcements from AS-SET AS-EXAMPLE",
            "ground_truth": {
                "asns": [],
                "prefixes": ["2001:db8::1/128", "2001:db8::/64"],
                "ip_addresses": [],
                "keywords": ["announcements", "AS-SET", "AS-EXAMPLE"],
                "time_references": []
            }
        },
        {
            "query": "Route 0.0.0.0/0 default from AS7922 conflicts with 8.8.8.8/32 specific",
            "ground_truth": {
                "asns": ["7922"],
                "prefixes": ["0.0.0.0/0", "8.8.8.8/32"],
                "ip_addresses": [],
                "keywords": ["Route", "default", "conflicts", "specific"],
                "time_references": []
            }
        },
        {
            "query": "AS4294967295 (4-byte ASN) announces 198.51.100.0/24 with communities 65000:100 65000:200",
            "ground_truth": {
                "asns": ["4294967295"],
                "prefixes": ["198.51.100.0/24"],
                "ip_addresses": [],
                "keywords": ["4-byte", "ASN", "announces", "communities"],
                "time_references": []
            }
        },
        {
            "query": "Malformed prefix 256.256.256.256/33 rejected by AS1234 at 25:61 invalid time",
            "ground_truth": {
                "asns": ["1234"],
                "prefixes": [],  # Malformed, should not be extracted
                "ip_addresses": [],
                "keywords": ["Malformed", "prefix", "rejected", "invalid"],
                "time_references": ["25:61"]  # Invalid time but still a time reference
            }
        }
    ]


def get_rag_retrieval_test_cases() -> List[RAGTestQuery]:
    """RAG retrieval test queries for evaluating document retrieval performance"""
    return [
        RAGTestQuery(
            query="Which NOTIFICATION sub-code is used when a BGP FSM detects a connection collision?",
            expected_docs=["RFC4271"],
            description="Error-handling section listing NOTIFICATION sub-codes."
        ),
        RAGTestQuery(
            query="What is the meaning of Extended Community Type 0x03 (high-order byte) in BGP?",
            expected_docs=["RFC4360"],
            description="Table of Extended Community Type values."
        ),
        RAGTestQuery(
            query="State the loop-prevention rule that a Route Reflector must follow with the cluster-list.",
            expected_docs=["RFC4456"],
            description="Loop-detection procedure comparing Cluster_IDs."
        ),
        RAGTestQuery(
            query="How is the Restart Time encoded in the Graceful Restart Capability TLV?",
            expected_docs=["RFC4724"],
            description="Definition of the 12-bit Restart Time field."
        ),
        RAGTestQuery(
            query="Give the SAFI values originally assigned to IPv4- and IPv6-Multicast NLRI in the MP-BGP specification.",
            expected_docs=["RFC4760"],
            description="AFI/SAFI registry table."
        ),
        RAGTestQuery(
            query="Name the three possible origin-validation states in BGP and indicate which one is considered 'uncertain'.",
            expected_docs=["RFC6811"],
            description="Valid, Invalid, NotFound enumeration."
        ),
        RAGTestQuery(
            query="For eBGP sessions protected by GTSM, what TTL value is recommended as best practice?",
            expected_docs=["RFC7454"],
            description="Operational guidance on TTL-security."
        ),
        RAGTestQuery(
            query="Under the enhanced UPDATE error handling rules, which class of errors triggers 'treat-as-withdraw'?",
            expected_docs=["RFC7606"],
            description="Decision matrix mapping error categories to recovery actions."
        ),
        RAGTestQuery(
            query="What is the Large BGP Community format?",
            expected_docs=["RFC8092"],
            description="Attribute Code 32; optional transitive."
        ),
        RAGTestQuery(
            query="Which single exception is allowed to the default-deny inbound filter requirement on external BGP sessions?",
            expected_docs=["RFC8212"],
            description="Clause permitting routes from directly connected EBGP neighbour."
        )
    ]


def get_all_test_cases() -> List[Dict]:
    """Get all test cases in order of difficulty"""
    return (
        get_easy_test_cases() +
        get_hard_test_cases() +
        get_spelling_mistake_cases() +
        get_edge_cases()
    ) 