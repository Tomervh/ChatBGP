#!/usr/bin/env python3
"""
Entity Extraction Comparison Test

Compares regex and LLM entity extractors on BGP queries.
"""

import os
import sys
import time
import json
import csv
from collections import defaultdict
from typing import Dict, List
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chatbgp.extractors.entity_extractor import RegexEntityExtractor
from chatbgp.extractors.llm_entity_extractor import LLMEntityExtractor
from test_queries import get_all_test_cases

class ExtractionComparison:
    """Compare regex and LLM entity extractors"""
    
    def __init__(self):
        self.regex_extractor = RegexEntityExtractor()
        try:
            self.llm_extractor = LLMEntityExtractor()
            self.llm_available = True
        except Exception:
            self.llm_available = False
        
        self.results = {
            'regex': {'metrics': defaultdict(list), 'timing': []},
            'llm': {'metrics': defaultdict(list), 'timing': []},
            'detailed_results': []
        }

    def normalize_entity(self, entity, entity_type):
        """Normalize entities for comparison"""
        if entity_type == 'asns':
            normalized = ''.join(c for c in str(entity) if c.isdigit())
            return normalized if normalized else None
        elif entity_type == 'prefixes':
            entity_str = str(entity)
            if '/' in entity_str:
                ip_part, prefix_part = entity_str.split('/')
                if ':' in ip_part:
                    return entity_str  # IPv6
                ip_parts = ip_part.split('.')
                if len(ip_parts) == 3 and not ip_part.endswith('.0'):
                    ip_part = ip_part + '.0'
                elif len(ip_parts) == 2:
                    ip_part = ip_part + '.0.0'
                elif len(ip_parts) == 1:
                    ip_part = ip_part + '.0.0.0'
                return f"{ip_part}/{prefix_part}"
            return entity_str
        elif entity_type == 'time_references':
            entity_str = str(entity).lower().strip()
            words = entity_str.split()
            if len(words) > 1:
                return ' '.join(''.join(c for c in word if c not in 'aeiou') for word in words)
            else:
                return ''.join(c for c in entity_str if c not in 'aeiou')
        elif entity_type == 'keywords':
            return str(entity).lower().strip()
        else:
            return str(entity).strip()

    def calculate_metrics(self, extracted: Dict, ground_truth: Dict) -> Dict:
        """Calculate precision, recall, F1 for each entity type"""
        metrics = {}
        
        for entity_type in ground_truth.keys():
            extracted_normalized = set()
            for e in extracted.get(entity_type, []):
                if e:
                    normalized = self.normalize_entity(e, entity_type)
                    if normalized:
                        extracted_normalized.add(normalized)
            
            truth_normalized = set()
            for e in ground_truth[entity_type]:
                if e:
                    normalized = self.normalize_entity(e, entity_type)
                    if normalized:
                        truth_normalized.add(normalized)
            
            if len(truth_normalized) == 0 and len(extracted_normalized) == 0:
                precision = recall = f1 = 1.0
            elif len(truth_normalized) == 0:
                precision = 0.0 if len(extracted_normalized) > 0 else 1.0
                recall = 1.0
                f1 = 0.0
            elif len(extracted_normalized) == 0:
                precision = 1.0
                recall = 0.0
                f1 = 0.0
            else:
                true_positives = len(extracted_normalized & truth_normalized)
                precision = true_positives / len(extracted_normalized)
                recall = true_positives / len(truth_normalized)
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            metrics[entity_type] = {
                'precision': precision,
                'recall': recall,
                'f1': f1
            }
        
        return metrics

    def run_comparison(self) -> Dict:
        """Run extraction comparison and return results"""
        test_cases = get_all_test_cases()
        
        for test_case in test_cases:
            query = test_case["query"]
            ground_truth = test_case["ground_truth"]
            
            start_time = time.time()
            regex_result = self.regex_extractor.extract(query)
            regex_time = time.time() - start_time
            regex_metrics = self.calculate_metrics(regex_result, ground_truth)
            
            if self.llm_available:
                start_time = time.time()
                llm_result = self.llm_extractor.extract(query)
                llm_time = time.time() - start_time
                llm_metrics = self.calculate_metrics(llm_result, ground_truth)
            else:
                llm_result = {'ip_addresses': [], 'prefixes': [], 'asns': [], 'keywords': [], 'time_references': []}
                llm_time = 0
                llm_metrics = {}
            
            self.results['detailed_results'].append({
                'query': query,
                'regex_result': regex_result,
                'llm_result': llm_result,
                'regex_metrics': regex_metrics,
                'llm_metrics': llm_metrics,
                'timing': {'regex': regex_time, 'llm': llm_time}
            })
            
            for entity_type, metrics in regex_metrics.items():
                self.results['regex']['metrics'][f"{entity_type}_precision"].append(metrics['precision'])
                self.results['regex']['metrics'][f"{entity_type}_recall"].append(metrics['recall'])
                self.results['regex']['metrics'][f"{entity_type}_f1"].append(metrics['f1'])
            
            if self.llm_available:
                for entity_type, metrics in llm_metrics.items():
                    self.results['llm']['metrics'][f"{entity_type}_precision"].append(metrics['precision'])
                    self.results['llm']['metrics'][f"{entity_type}_recall"].append(metrics['recall'])
                    self.results['llm']['metrics'][f"{entity_type}_f1"].append(metrics['f1'])
            
            self.results['regex']['timing'].append(regex_time)
            if self.llm_available:
                self.results['llm']['timing'].append(llm_time)
        
        return self.get_summary()

    def get_summary(self) -> Dict:
        """Generate summary statistics"""
        entity_types = ['ip_addresses', 'prefixes', 'asns', 'keywords', 'time_references']
        
        summary = {
            'regex': {},
            'llm': {} if self.llm_available else None,
            'timing': {
                'regex_avg': sum(self.results['regex']['timing']) / len(self.results['regex']['timing']) if self.results['regex']['timing'] else 0,
                'llm_avg': sum(self.results['llm']['timing']) / len(self.results['llm']['timing']) if self.llm_available and self.results['llm']['timing'] else 0
            }
        }
        
        for entity_type in entity_types:
            f1_key = f"{entity_type}_f1"
            p_key = f"{entity_type}_precision"
            r_key = f"{entity_type}_recall"
            
            if f1_key in self.results['regex']['metrics'] and self.results['regex']['metrics'][f1_key]:
                summary['regex'][entity_type] = {
                    'precision': sum(self.results['regex']['metrics'][p_key]) / len(self.results['regex']['metrics'][p_key]),
                    'recall': sum(self.results['regex']['metrics'][r_key]) / len(self.results['regex']['metrics'][r_key]),
                    'f1': sum(self.results['regex']['metrics'][f1_key]) / len(self.results['regex']['metrics'][f1_key])
                }
        
        if self.llm_available:
            for entity_type in entity_types:
                f1_key = f"{entity_type}_f1"
                p_key = f"{entity_type}_precision"
                r_key = f"{entity_type}_recall"
                
                if f1_key in self.results['llm']['metrics'] and self.results['llm']['metrics'][f1_key]:
                    summary['llm'][entity_type] = {
                        'precision': sum(self.results['llm']['metrics'][p_key]) / len(self.results['llm']['metrics'][p_key]),
                        'recall': sum(self.results['llm']['metrics'][r_key]) / len(self.results['llm']['metrics'][r_key]),
                        'f1': sum(self.results['llm']['metrics'][f1_key]) / len(self.results['llm']['metrics'][f1_key])
                    }
        
        return summary

    def save_results(self, output_dir: str = ".") -> str:
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/extraction_comparison_{timestamp}.json"
        
        output_data = {
            'summary': self.get_summary(),
            'detailed_results': self.results['detailed_results']
        }
        
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        return filename

def run_extraction_comparison(save_results: bool = True, output_dir: str = ".") -> Dict:
    """
    Run entity extraction comparison test
    
    Returns:
        Dict containing summary statistics and detailed results
    """
    comparison = ExtractionComparison()
    summary = comparison.run_comparison()
    
    if save_results:
        comparison.save_results(output_dir)
    
    return {
        'summary': summary,
        'detailed_results': comparison.results['detailed_results']
    }

def main():
    """Run extraction comparison"""
    results = run_extraction_comparison()
    return results

if __name__ == "__main__":
    main() 