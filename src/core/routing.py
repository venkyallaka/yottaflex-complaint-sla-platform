"""
Dynamic Routing & Agent Assignment Engine.
"""
from typing import Dict, Any, List

TEAM_ROUTING_MAP = {
    "CAT-01": "Safety & Regulatory Escalations",
    "CAT-02": "Product Quality Team",
    "CAT-03": "Logistics & Fulfillment",
    "CAT-04": "Finance & Billing Ops",
    "CAT-05": "Returns & Settlement",
    "CAT-06": "Security & Identity",
    "CAT-07": "Service Excellence Team",
    "CAT-08": "Inventory & Parts Ops",
    "CAT-09": "Catalog & Compliance",
    "CAT-10": "Technical Support Tier 2"
}

def determine_team_and_agent(category_id: str, priority: str) -> Dict[str, str]:
    """
    Selects specialized team and agent based on category and priority tier.
    """
    if priority == "P1_CRITICAL":
        team = "Safety & Regulatory Escalations"
        agent = "AGT-0015"
    else:
        team = TEAM_ROUTING_MAP.get(category_id, "Tier 1 Support")
        agent_id_map = {
            "Safety & Regulatory Escalations": "AGT-0016",
            "Product Quality Team": "AGT-0002",
            "Logistics & Fulfillment": "AGT-0028",
            "Finance & Billing Ops": "AGT-0022",
            "Returns & Settlement": "AGT-0005",
            "Security & Identity": "AGT-0010",
            "Service Excellence Team": "AGT-0008",
            "Inventory & Parts Ops": "AGT-0011",
            "Catalog & Compliance": "AGT-0012",
            "Technical Support Tier 2": "AGT-0014"
        }
        agent = agent_id_map.get(team, "AGT-0001")
        
    return {
        "team_name": team,
        "agent_id": agent
    }
