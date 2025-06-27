#!/usr/bin/env python3
"""
Parse RIB dump into radix trees and maintain live updates
"""

import pybgpstream
import radix
import gzip
import pickle
import time
import os
from .bgp_stream_wrapper import BGPStreamWrapper
from datetime import datetime, timedelta
import duckdb
from .bgp_to_duckdb import create_rib_table, create_live_updates_table, store_live_update

DUCKDB_FILE = "data/bgp_data/bgp_rib_snapshot.duckdb"

def init_duckdb_connection():
    """Initialize DuckDB connection and ensure tables exist."""
    con = duckdb.connect(DUCKDB_FILE)
    create_rib_table(con)
    create_live_updates_table(con)
    return con

def load_or_create_trees_OPTIMIZED(v4_path="data/bgp_data/radix_v4_obj.pkl.gz", 
                                  v6_path="data/bgp_data/radix_v6_obj.pkl.gz"):
    """Load existing Radix tree objects if they exist, otherwise indicate failure to load."""
    
    if os.path.exists(v4_path) and os.path.exists(v6_path):
        try:
            start_time = time.time()
            with gzip.open(v4_path, "rb") as f4:
                rtree_v4 = pickle.load(f4)
                print(f"Loaded IPv4 tree with {len(rtree_v4.nodes())} nodes.") 

            with gzip.open(v6_path, "rb") as f6:
                rtree_v6 = pickle.load(f6)
                print(f"Loaded IPv6 tree with {len(rtree_v6.nodes())} nodes.")

            end_time = time.time()
            print(f"Trees loaded directly in {end_time - start_time:.2f} seconds!")
            return rtree_v4, rtree_v6
        except Exception:
            return None, None
    else:
        return None, None

def save_trees_OPTIMIZED(rtree_v4, rtree_v6, 
                        v4_path="data/bgp_data/radix_v4_obj.pkl.gz",
                        v6_path="data/bgp_data/radix_v6_obj.pkl.gz"):
    """Save Radix tree objects directly to disk using pickle."""
    try:
        os.makedirs(os.path.dirname(v4_path), exist_ok=True)
        
        start_time = time.time()
        with gzip.open(v4_path, "wb") as f4:
            pickle.dump(rtree_v4, f4, protocol=pickle.HIGHEST_PROTOCOL)

        with gzip.open(v6_path, "wb") as f6:
            pickle.dump(rtree_v6, f6, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass

def create_trees_from_rib(rib_file_path):
    """Create radix trees from a BGP RIB dump file."""
    rtree_v4 = radix.Radix()
    rtree_v6 = radix.Radix()

    stream = pybgpstream.BGPStream()
    stream.set_data_interface("singlefile")
    stream.set_data_interface_option("singlefile", "rib-file", rib_file_path)
    stream.start()

    processed_count = 0

    while True:
        rec = stream.get_next_record()
        if rec is None:
            break
        if rec.status != "valid":
            continue

        elem = rec.get_next_elem()
        while elem:
            if elem.type == "R":
                prefix_str = elem.fields.get("prefix")
                as_path_str = elem.fields.get("as-path")

                if prefix_str and as_path_str:
                    try:
                        as_numbers = []
                        raw_asns = as_path_str.split()
                        for asn_token in raw_asns:
                            if '{' in asn_token:
                                clean_token = asn_token.strip('{}')
                                first_asn_in_set = clean_token.split(',')[0]
                                if first_asn_in_set.isdigit():
                                    as_numbers.append(int(first_asn_in_set))
                            elif asn_token.isdigit():
                                as_numbers.append(int(asn_token))
                        
                        if not as_numbers:
                            elem = rec.get_next_elem()
                            continue
                        
                        origin_as = as_numbers[-1]
                        
                        rnode = None
                        if ":" in prefix_str:
                            rnode = rtree_v6.add(prefix_str)
                        else:
                            rnode = rtree_v4.add(prefix_str)
                        
                        rnode.data["origin_as"] = origin_as
                        rnode.data["as_path"] = as_numbers
                        processed_count += 1

                    except (ValueError, IndexError, KeyError):
                        pass
            elem = rec.get_next_elem()

    return rtree_v4, rtree_v6

def handle_live_updates(rtree_v4, rtree_v6, rib_timestamp_str="20250504.0800"):
    """Handle live BGP updates from rrc03 starting from RIB snapshot time."""
    
    stream_wrapper = BGPStreamWrapper(collectors=["rrc03"])
    db_con = init_duckdb_connection()
    
    rib_time = datetime.strptime(rib_timestamp_str, "%Y%m%d.%H%M")
    current_time = rib_time + timedelta(minutes=10)
    
    update_count = 0
    last_save_count = 0
    SAVE_INTERVAL = 10000
    
    try:
        chunk_start = rib_time
        while chunk_start < current_time:
            chunk_end = min(chunk_start + timedelta(minutes=1), current_time)
            
            historical_updates = stream_wrapper.get_prefix_updates_in_range(
                start_time=chunk_start,
                end_time=chunk_end
            )
            
            if historical_updates:
                for update in historical_updates:
                    store_live_update(update, db_con)
                
                for update in historical_updates:
                    prefix_str = update.prefix
                    if not prefix_str:
                        continue

                    target_tree = rtree_v6 if ":" in prefix_str else rtree_v4
                    
                    if update.update_type == 'W':
                        if prefix_str in target_tree:
                            target_tree.delete(prefix_str)
                    
                    elif update.update_type == 'A':
                        if not update.as_path:
                            continue

                        try:
                            as_numbers = [int(asn) for asn in update.as_path.split()]
                            
                            if not as_numbers:
                                continue
                            
                            rnode = target_tree.add(prefix_str)
                            rnode.data["origin_as"] = int(update.origin_as) if update.origin_as else as_numbers[-1]
                            rnode.data["as_path"] = as_numbers
                            
                            update_count += 1
                            
                            if update_count - last_save_count >= SAVE_INTERVAL:
                                save_trees_OPTIMIZED(rtree_v4, rtree_v6)
                                last_save_count = update_count

                        except (ValueError, IndexError, KeyError):
                            continue
            
            chunk_start = chunk_end
        
    except KeyboardInterrupt:
        save_trees_OPTIMIZED(rtree_v4, rtree_v6)
        db_con.close()

if __name__ == "__main__":
    rtree_v4, rtree_v6 = load_or_create_trees_OPTIMIZED()

    if rtree_v4 is None or rtree_v6 is None:
        RIB_FILE = "data/bgp_data/bview.20250504.0800"
        if not os.path.exists(RIB_FILE):
            exit(1)
            
        rtree_v4, rtree_v6 = create_trees_from_rib(RIB_FILE)
        if rtree_v4 and rtree_v6:
            save_trees_OPTIMIZED(rtree_v4, rtree_v6)
        else:
            exit(1)

    handle_live_updates(rtree_v4, rtree_v6) 