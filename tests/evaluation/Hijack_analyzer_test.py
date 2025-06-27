#!/usr/bin/env python3
"""
Hijack analyzer test

Tests the heuristic analyzer using known hijack cases.
"""

import os
import sys
import csv
import time
from typing import Dict, List
from dataclasses import dataclass

# Add chatbgp to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from chatbgp.utils.external_data import fetch_whois_data, fetch_rpki_validation
from chatbgp.analyzers.heuristic_analyzer import analyze_bgp_discrepancies

@dataclass
class HijackCase:
    """Represents a single hijack case from the CSV"""
    event_id: int
    prefix: str
    hijacker_asn: int
    victim_asn: int
    confidence: int

class HijackAnalyzerTester:
    """Tests the heuristic analyzer using known hijack cases"""
    
    def __init__(self, csv_path: str):
        """Initialize with path to hijacks CSV"""
        self.csv_path = csv_path
        self.hijack_cases: List[HijackCase] = []
        self.load_hijack_data()
        
    def load_hijack_data(self):
        """Load hijack cases from CSV"""
        with open(self.csv_path, mode='r') as infile:
            reader = csv.reader(infile)
            for row in reader:
                try:
                    event_id = int(row[0])
                    prefix = row[1].strip('"')
                    hijacker_asn = int(row[2])
                    victim_asn = int(row[3])
                    confidence = int(row[6]) if len(row) > 6 and row[6] else 0
                    
                    self.hijack_cases.append(HijackCase(
                        event_id=event_id,
                        prefix=prefix,
                        hijacker_asn=hijacker_asn,
                        victim_asn=victim_asn,
                        confidence=confidence
                    ))
                except (ValueError, IndexError):
                    continue
    
    def simulate_bgp_state(self, case: HijackCase) -> Dict:
        """
        Simulate BGP state for a hijack case.
        Returns what would normally come from the live BGP feed.
        """
        return {
            "prefix": case.prefix,
            "origin_as": case.hijacker_asn,  # Simulate seeing the hijacker as origin
            "as_path": [case.hijacker_asn],  # Simple path with just the hijacker
            "timestamp": int(time.time())
        }
    
    def test_single_case(self, case: HijackCase) -> Dict:
        """Test a single hijack case"""
        simulated_bgp_data = self.simulate_bgp_state(case)
        
        try:
            rpki_data = fetch_rpki_validation(case.prefix, f"AS{case.hijacker_asn}")
        except Exception:
            rpki_data = None
        
        try:
            irr_data = fetch_whois_data(case.prefix)
        except Exception:
            irr_data = None
        
        analysis_result = analyze_bgp_discrepancies(
            live_bgp_data=simulated_bgp_data,
            rpki_data=rpki_data,
            irr_data=irr_data,
            historical_updates=[]
        )
        
        flags = analysis_result.get("flags", []) if analysis_result else []
        detected = any(flag in flags for flag in ["POTENTIAL_HIJACK", "RPKI_INVALID", "IRR_MISMATCH"])
        
        return {
            "detected": detected,
            "flags": flags,
            "confidence": case.confidence
        }
    
    def run_tests(self):
        """Run tests on all hijack cases"""
        detected_count = 0
        total_cases = len(self.hijack_cases)
        
        for case in self.hijack_cases:
            result = self.test_single_case(case)
            if result["detected"]:
                detected_count += 1
                print(f"Detected hijack: {case.prefix} (AS{case.hijacker_asn}) - Flags: {result['flags']}")
        
        print(f"\nResults: {detected_count}/{total_cases} hijacks detected ({detected_count/total_cases*100:.1f}%)")

def main():
    """Main function"""
    base_dir = os.path.join(os.path.dirname(__file__), "../..")
    csv_path = os.path.join(base_dir, "docs", "hijacks_clean.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        return
    
    tester = HijackAnalyzerTester(csv_path)
    tester.run_tests()

if __name__ == "__main__":
    main() 