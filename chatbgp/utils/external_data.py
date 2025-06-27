#!/usr/bin/env python3
"""
Functions for fetching RPKI and IRR data from external APIs
"""
import requests
import time
from typing import Dict, Any


def fetch_rpki_validation(prefix: str, origin_as: str, max_retries: int = 3, delay: float = 0.1) -> Dict[str, Any]:
    """
    Validate a prefix-origin pair against RPKI using the RIPE API.
    
    Args:
        prefix: IP prefix to validate (e.g., "8.8.8.0/24")
        origin_as: Origin ASN to validate (e.g., "15169" or "AS15169")
        max_retries: Maximum retry attempts for API calls
        delay: Delay between retries in seconds
        
    Returns:
        dict: {
            "prefix": str,
            "origin_as": str,
            "rpki_status": str,     # 'valid', 'invalid', or 'not-found'
            "covering_roas": list,  # List of ROAs that cover this prefix
            "status": str           # 'success' or 'error'
        }
    """
    # normalize ASN - strip AS prefix
    if origin_as.startswith("AS"):
        origin_as = origin_as[2:]
    
    url = f"https://stat.ripe.net/data/rpki-validation/data.json?resource={prefix}&prefix={prefix}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rpki_status = "not-found"
            covering_roas = []
            
            if "data" in data and "validating_roas" in data["data"]:
                roas = data["data"]["validating_roas"]
                
                for roa in roas:
                    covering_roas.append({
                        "prefix": roa.get("prefix"),
                        "max_length": roa.get("max_length"),
                        "origin": roa.get("origin"),
                        "validity": roa.get("validity")
                    })
                    
                    roa_origin = str(roa.get("origin", "")).replace("AS", "")
                    if roa_origin == origin_as:
                        validity = roa.get("validity", "unknown")
                        if validity == "valid":
                            rpki_status = "valid"
                        elif validity in ["invalid", "invalid_asn", "invalid_length"]:
                            rpki_status = "invalid"
            
            if rpki_status == "not-found" and covering_roas:
                for roa in covering_roas:
                    roa_origin = str(roa.get("origin", "")).replace("AS", "")
                    if roa_origin != origin_as and roa.get("validity") in ["valid"]:
                        rpki_status = "invalid"
                        break
            
            return {
                "prefix": prefix,
                "origin_as": origin_as,
                "rpki_status": rpki_status,
                "covering_roas": covering_roas,
                "status": "success"
            }
            
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
                continue
            
            return {
                "prefix": prefix,
                "origin_as": origin_as,
                "rpki_status": "error",
                "covering_roas": [],
                "status": "error",
                "error": str(e)
            }
    
    return {
        "prefix": prefix,
        "origin_as": origin_as,
        "rpki_status": "error",
        "covering_roas": [],
        "status": "error",
        "error": "Max retries exceeded"
    }


def fetch_whois_data(prefix: str) -> dict:
    """
    Query the RIPEstat API to get whois/IRR data for a given prefix.

    Args:
        prefix (str): IP prefix to check (e.g., "192.0.2.0/24")

    Returns:
        dict: {
            "prefix": str,
            "irr_origins": list,       # List of origin ASNs from IRR route objects (numbers only)
            "authorities": list,       # List of IRR authorities (RIPE, ARIN, etc.)
            "status": str             # 'success', 'not-found', or 'error'
        }
    """
    url = f"https://stat.ripe.net/data/whois/data.json?resource={prefix}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        irr_origins = []
        authorities = []
        
        if "data" in data and "irr_records" in data["data"]:
            for record in data["data"]["irr_records"]:
                for item in record:
                    if item.get("key") == "origin":
                        # normalize ASN - strip AS prefix and keep only digits
                        origin_as = item.get("value", "").replace("AS", "").strip()
                        if origin_as.isdigit() and origin_as not in irr_origins:
                            irr_origins.append(origin_as)
                    elif item.get("key") == "source":
                        source = item.get("value", "").strip()
                        if source and source not in authorities:
                            authorities.append(source)
        
        # Fallback: parse RIR records if no IRR route objects found
        if not irr_origins and "data" in data and "records" in data["data"]:
            for record in data["data"]["records"]:
                for item in record:
                    if item.get("key") in ["OriginAS", "origin"]:
                        # normalize ASN - strip AS prefix and keep only digits
                        origin_as = item.get("value", "").replace("AS", "").strip()
                        if origin_as.isdigit() and origin_as not in irr_origins:
                            irr_origins.append(origin_as)
                    elif item.get("key") == "source":
                        source = item.get("value", "").strip()
                        if source and source not in authorities:
                            authorities.append(source)

        return {
            "prefix": prefix,
            "irr_origins": irr_origins,
            "authorities": authorities,
            "status": "success" if irr_origins else "not-found"
        }

    except Exception as e:
        return {
            "prefix": prefix,
            "irr_origins": [],
            "authorities": [],
            "status": "error",
            "error": str(e)
        }
