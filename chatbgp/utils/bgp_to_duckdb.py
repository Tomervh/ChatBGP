#!/usr/bin/env python3
"""
 Parses a BGP RIB dump (MRT format) and loads it into DuckDB.
"""

import pybgpstream
import duckdb
import time
import os
from datetime import datetime

DUCKDB_FILE = "bgp_rib_snapshot.duckdb"
RIB_TABLE_NAME = "rib_entries"

def create_rib_table(con):
    """Creates the RIB table in DuckDB if it doesn't exist."""
    try:
        con.execute("INSTALL inet;")
        con.execute("LOAD inet;")
    except:
        pass

    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {RIB_TABLE_NAME} (
            dump_time TIMESTAMP,
            record_time TIMESTAMP,
            collector VARCHAR,
            peer_address INET,
            peer_asn BIGINT,
            prefix INET,
            as_path VARCHAR,
            origin_as BIGINT,
            next_hop INET,
            communities VARCHAR,
            med BIGINT,
            local_pref BIGINT,
            atomic_aggregate BOOLEAN,
            aggregator_as BIGINT,
            aggregator_address INET
        );
    """)

def create_live_updates_table(con):
    """Creates a table specifically for live BGP updates if it doesn't exist."""
    try:
        con.execute("INSTALL inet;")
        con.execute("LOAD inet;")
    except:
        pass

    con.execute("""
        CREATE TABLE IF NOT EXISTS rrc03_updates (
            timestamp TIMESTAMP,
            collector VARCHAR,
            peer_address INET,
            peer_asn BIGINT,
            prefix INET,
            update_type CHAR(1),
            as_path VARCHAR,
            origin_as BIGINT,
            next_hop INET,
            communities VARCHAR,
            med BIGINT,
            local_pref BIGINT,
            atomic_aggregate BOOLEAN,
            aggregator VARCHAR
        );
    """)
    
    con.execute("CREATE INDEX IF NOT EXISTS idx_updates_timestamp ON rrc03_updates(timestamp);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_updates_prefix ON rrc03_updates(prefix);")

def store_live_update(update, con):
    """Store a single BGP update in the live updates table."""
    try:
        if update.update_type not in ['A', 'W']:
            return True

        if not update.prefix or update.prefix.strip() == "":
            return False

        if update.update_type == 'W':
            con.execute("""
                INSERT INTO rrc03_updates (
                    timestamp, collector, peer_address, peer_asn, 
                    prefix, update_type
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, [
                update.timestamp,
                update.collector,
                update.peer_address,
                update.peer_asn,
                update.prefix,
                'W'
            ])
        else:
            con.execute("""
                INSERT INTO rrc03_updates (
                    timestamp, collector, peer_address, peer_asn,
                    prefix, update_type, as_path, origin_as, next_hop,
                    communities, med, local_pref, atomic_aggregate, aggregator
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                update.timestamp,
                update.collector,
                update.peer_address,
                update.peer_asn,
                update.prefix,
                'A',
                update.as_path,
                update.origin_as,
                update.next_hop,
                update.communities,
                update.med,
                update.local_pref,
                update.atomic_aggregate,
                update.aggregator
            ])
        return True
    except:
        return False

def parse_as_path_to_data(as_path_str):
    """Parses an AS path string into a list of integers and extracts the origin AS."""
    if not as_path_str:
        return None, None
    
    as_numbers = []
    raw_asns = as_path_str.split()
    for asn_token in raw_asns:
        try:
            if '{' in asn_token:
                clean_token = asn_token.strip('{}')
                parts = clean_token.split(',')
                if parts and parts[0].isdigit():
                    as_numbers.append(int(parts[0]))
            elif '(' in asn_token:
                pass
            elif asn_token.isdigit():
                as_numbers.append(int(asn_token))
        except ValueError:
            continue

    if not as_numbers:
        return " ".join(raw_asns) if raw_asns else None, None

    origin_as = as_numbers[-1] if as_numbers else None
    return " ".join(map(str, as_numbers)), origin_as

def parse_communities_to_string(communities_list):
    """Converts a list of communities to a space-separated string."""
    if not communities_list:
        return None
        
    if isinstance(communities_list, str):
        return communities_list
        
    result = []
    for c in communities_list:
        if isinstance(c, dict):
            result.append(f"{c.get('asn',0)}:{c.get('value',0)}")
        elif isinstance(c, str):
            result.append(c)
        else:
            continue
            
    return " ".join(result) if result else None

def load_rib_to_duckdb(rib_file_path, db_file=DUCKDB_FILE, table_name=RIB_TABLE_NAME):
    """Parses a BGP RIB dump (MRT) file and loads its entries into a DuckDB table."""
    if not os.path.exists(rib_file_path):
        return

    con = duckdb.connect(database=db_file, read_only=False)
    create_rib_table(con)

    stream = pybgpstream.BGPStream()
    stream.set_data_interface("singlefile")
    stream.set_data_interface_option("singlefile", "rib-file", rib_file_path)
    stream.start()

    dump_processing_time = datetime.now()
    inserted_count = 0
    processed_count = 0
    batch_data = []
    BATCH_SIZE = 10000

    while True:
        rec = stream.get_next_record()
        if rec is None:
            break
        if rec.status != "valid":
            continue
        
        processed_count += 1

        elem = rec.get_next_elem()
        while elem:
            if elem.type == "R":
                as_path_str, origin_as = parse_as_path_to_data(elem.fields.get("as-path"))
                communities_str = parse_communities_to_string(elem.fields.get("communities"))
                
                entry_data = (
                    dump_processing_time,
                    datetime.fromtimestamp(rec.time) if rec.time else None,
                    rec.collector,
                    str(elem.peer_address) if elem.peer_address else None,
                    elem.peer_asn,
                    elem.fields.get("prefix"),
                    as_path_str,
                    origin_as,
                    elem.fields.get("next-hop"),
                    communities_str,
                    elem.fields.get("med"),
                    elem.fields.get("local-pref"),
                    'atomic-aggregate' in elem.fields,
                    elem.fields.get("aggregator", "::").split(":",1)[0] if "aggregator" in elem.fields and elem.fields.get("aggregator").count(":") >=1 else None,
                    elem.fields.get("aggregator", "::").split(":",1)[-1] if "aggregator" in elem.fields and elem.fields.get("aggregator").count(":") >=1 else None
                )
                batch_data.append(entry_data)

                if len(batch_data) >= BATCH_SIZE:
                    con.executemany(f"INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch_data)
                    inserted_count += len(batch_data)
                    batch_data = []
            
            elem = rec.get_next_elem()

    if batch_data:
        con.executemany(f"INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch_data)
        inserted_count += len(batch_data)

    con.close()

if __name__ == "__main__":
    rib_file = "data/bgp_data/bview.20250504.0800"

    if os.path.exists(rib_file):
        load_rib_to_duckdb(rib_file) 