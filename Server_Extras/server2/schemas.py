from pydantic import BaseModel
from typing import Dict, List, Union

class AnalysisResult(BaseModel):
    total_connections: int
    failed_attempts: int
    suspicious_ips: List[str]
    possible_bruteforce: bool
    ip_reputation: Dict[str, Union[str, dict]]
