from typing import Dict, List, Optional
import pybgpstream
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class BGPUpdate:
    """Simplified BGP update dataclass with only essential fields."""
    timestamp: datetime
    prefix: str
    as_path: str
    update_type: str  # 'A' for announce, 'W' for withdraw
    origin_as: Optional[str]
    collector: str

class BGPStreamWrapper:
    """Minimal BGP stream wrapper for radix tree updates only."""
    
    def __init__(self, collectors: Optional[List[str]] = None):
        """Initialize with basic collector list."""
        self.collectors = collectors or ["rrc03"]
    
    def _create_stream(self, start_time: datetime, end_time: datetime) -> pybgpstream.BGPStream:
        """Create a BGP stream for the specified time range."""
        return pybgpstream.BGPStream(
            from_time=start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            until_time=end_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            collectors=self.collectors,
            record_type="updates"
        )
    
    def get_prefix_updates_in_range(self, 
                                  start_time: datetime,
                                  end_time: datetime,
                                  prefix: Optional[str] = None,
                                  asn: Optional[str] = None) -> List[BGPUpdate]:
        """
        Get BGP updates within a specific time range.
        Only method actually used by bgp_radix.py.
        """
        if not start_time or not end_time:
            return []
            
        # Limit window size to prevent massive queries
        time_diff = end_time - start_time
        if time_diff > timedelta(hours=1):
            end_time = start_time + timedelta(hours=1)
        
        try:
            stream = self._create_stream(start_time, end_time)
            updates = []
            
            for elem in stream:
                try:
                    current_prefix = elem.fields.get("prefix", "")
                    as_path = elem.fields.get("as-path", "")
                    
                    if prefix and current_prefix != prefix:
                        continue
                    if asn and (not as_path or asn not in as_path.split()):
                        continue
                    
                    update = BGPUpdate(
                        timestamp=datetime.utcfromtimestamp(elem.time),
                        prefix=current_prefix,
                        as_path=as_path,
                        update_type=elem.type,
                        origin_as=as_path.split()[-1] if as_path else None,
                        collector=elem.collector
                    )
                    updates.append(update)
                    
                except Exception:
                    continue
                    
        except Exception:
            return []
            
        return updates
    
    def summarize_updates(self, updates: List[BGPUpdate]) -> Dict:
        """Create a summary of BGP updates. Used by bgp_radix.py."""
        if not updates:
            return {"total_updates": 0, "status": "No updates found"}
            
        updates.sort(key=lambda x: x.timestamp)
        
        announcements = sum(1 for u in updates if u.update_type == 'A')
        withdrawals = sum(1 for u in updates if u.update_type == 'W')
        unique_as_paths = len(set(u.as_path for u in updates if u.as_path))
        
        return {
            "total_updates": len(updates),
            "announcements": announcements,
            "withdrawals": withdrawals,
            "unique_as_paths": unique_as_paths,
            "time_range": {
                "start": updates[0].timestamp.isoformat(),
                "end": updates[-1].timestamp.isoformat()
            },
            "most_recent_state": "withdrawn" if updates[-1].update_type == 'W' else "announced"
        } 