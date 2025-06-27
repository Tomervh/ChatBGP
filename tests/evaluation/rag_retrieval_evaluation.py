#!/usr/bin/env python3
"""
Evaluate RAG retrieval performance using ground truth document relevance.
Tests if the retriever returns the expected RFC sections for common BGP queries.
"""

import os
import sys
from typing import Dict, List, Tuple

# add chatbgp package to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chatbgp.retrievers.document_retriever import DocumentRetriever
from chatbgp.models.config import ChatBGPConfig
from test_queries import get_rag_retrieval_test_cases, RAGTestQuery

def evaluate_retrieval(retriever: DocumentRetriever, queries: List[RAGTestQuery], top_k: int = 3) -> Dict:
    """Evaluate retriever performance against ground truth."""
    total_queries = len(queries)
    hits_at_k = 0
    total_relevant = 0
    total_retrieved_relevant = 0
    
    query_results = []
    
    for query in queries:
        results = retriever.get_relevant_documents(query.query)
        
        expected_rfcs = set()
        for expected_doc in query.expected_docs:
            rfc_num = expected_doc.split('-')[0].replace('RFC', '')
            expected_rfcs.add(rfc_num)
        
        matches = []
        for rfc_num in expected_rfcs:
            for doc in results[:top_k]:
                content = doc.page_content.lower()
                metadata_str = str(doc.metadata).lower()
                filename = doc.metadata.get('source', '').lower()
                
                rfc_patterns = [
                    f"rfc {rfc_num}",
                    f"rfc{rfc_num}",
                    f"rfc_{rfc_num}",
                    f"rfc{rfc_num}_"
                ]
                
                if any(pattern in content for pattern in rfc_patterns) or \
                   any(pattern in filename for pattern in rfc_patterns):
                    matches.append(f"RFC{rfc_num}")
                    break
        
        if matches:
            hits_at_k += 1
        
        total_relevant += len(expected_rfcs)
        total_retrieved_relevant += len(matches)
        
        query_results.append({
            'query': query.query,
            'expected_rfcs': list(expected_rfcs),
            'retrieved': [f"{doc.metadata.get('source', 'unknown')} - {doc.page_content[:50]}..." for doc in results[:top_k]],
            'matches': matches,
            'hit': len(matches) > 0
        })
    
    hit_rate = hits_at_k / total_queries
    precision = total_retrieved_relevant / (total_queries * top_k) if total_queries * top_k > 0 else 0
    recall = total_retrieved_relevant / total_relevant if total_relevant > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0
    
    return {
        'hit_rate_at_k': hit_rate,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'total_queries': total_queries,
        'query_results': query_results
    }

def run_rag_evaluation() -> Dict:
    """Run the RAG retrieval evaluation"""
    try:
        config = ChatBGPConfig()
        retriever = DocumentRetriever(config)
        test_queries = get_rag_retrieval_test_cases()
        metrics = evaluate_retrieval(retriever, test_queries)
        return metrics
    except Exception as e:
        return {'error': str(e)}

def main():
    """Run the evaluation"""
    metrics = run_rag_evaluation()
    return metrics

if __name__ == "__main__":
    main() 