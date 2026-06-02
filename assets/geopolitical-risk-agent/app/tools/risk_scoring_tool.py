"""AI-based risk scoring tool with rule-based fallback â includes mitigation recommendations."""
import logging
import os
import json
from langchain.tools import tool

logger = logging.getLogger(__name__)

SEVERITY_MAP = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}

CAMEO_SEVERITY = {
    "MILITARY_ATTACK": 4, "CONFLICT": 3, "HOSTILITY": 3,
    "SANCTION": 3, "PROTEST": 2, "MILITARY": 3, "CRISISLEX_CRISISLEXREC": 2
}

RULE_BASED_RECOMMENDATIONS = {
    "Critical": [
        "IMMEDIATE: Activate emergency procurement protocol â contact all affected suppliers within 24 hours.",
        "Initiate alternative sourcing from pre-approved backup suppliers outside the conflict zone.",
        "Expedite any open POs with delivery dates within the next 30 days â request early shipment.",
        "Coordinate with logistics to reroute shipments avoiding affected regions; update freight forwarders.",
        "Place safety stock orders for critical materials with â¥60-day lead times.",
        "Escalate to CPO and Supply Chain Director â recommend executive briefing within 48 hours.",
        "Freeze new PO commitments to suppliers in the affected region until situation stabilises.",
    ],
    "High": [
        "Contact affected suppliers within 48 hours to confirm delivery status and assess disruption risk.",
        "Identify alternative suppliers in unaffected regions for the top 3 impacted material categories.",
        "Review contract force-majeure clauses for all affected suppliers â notify legal team.",
        "Increase safety stock targets by 20â30% for affected materials over the next 60 days.",
        "Monitor GDELT/NewsAPI signals daily â escalate if severity increases to Critical.",
        "Prepare contingency sourcing plan ready to activate within 72 hours.",
    ],
    "Medium": [
        "Monitor situation closely â schedule weekly supplier check-in calls for affected regions.",
        "Review open PO delivery schedules and flag any at-risk deliveries to the procurement team.",
        "Update risk register with current event details and assigned risk owner.",
        "Consider minor safety stock increase (10â15%) for affected materials as a precaution.",
    ],
    "Low": [
        "Log event in risk register for audit trail.",
        "No immediate procurement action required â continue routine supplier monitoring.",
    ]
}


def _rule_based_score(event: dict, supplier_count: int, po_count: int, total_po_value: float) -> dict:
    """Fallback rule-based scoring using CAMEO codes and business impact."""
    themes_str = str(event.get("themes", "")).upper()
    base_score = 1
    for theme, score in CAMEO_SEVERITY.items():
        if theme in themes_str:
            base_score = max(base_score, score)

    tone = float(event.get("tone_score", 0))
    if tone < -10:
        base_score = min(4, base_score + 1)
    if supplier_count > 5:
        base_score = min(4, base_score + 1)
    elif supplier_count > 2:
        base_score = min(4, base_score)

    severity = SEVERITY_MAP.get(base_score, "Low")
    return {
        "severity": severity,
        "score_numeric": base_score,
        "justification": (
            f"Rule-based score: detected themes [{themes_str[:120]}], "
            f"sentiment tone={tone:.1f}, {supplier_count} supplier(s) affected, "
            f"${total_po_value:,.0f} PO value at risk."
        ),
        "recommendations": RULE_BASED_RECOMMENDATIONS.get(severity, []),
        "affected_supplier_count": supplier_count,
        "affected_po_count": po_count,
        "total_po_value": total_po_value,
        "scoring_method": "rule_based"
    }


@tool
def score_risk(event: dict, affected_suppliers: list, affected_pos: list) -> dict:
    """Score the risk severity of a geopolitical event and generate mitigation recommendations.

    Uses LLM via SAP AI Core (GPT-4o) with rule-based fallback.

    Args:
        event: Dict with event_id, headline, date, source_country, themes, tone_score
        affected_suppliers: List of supplier dicts from get_suppliers_by_region
        affected_pos: List of PO dicts from get_open_pos_by_supplier

    Returns:
        Dict with severity (Low/Medium/High/Critical), score_numeric (1-4), justification,
        recommendations (list of action strings), affected_supplier_count,
        affected_po_count, total_po_value
    """
    supplier_count = len(affected_suppliers)
    po_count       = len(affected_pos)
    total_po_value = sum(po.get("net_value", 0) for po in affected_pos)

    try:
        from litellm import completion
        supplier_names = ", ".join(
            s.get("name", s.get("supplier_id", "")) for s in affected_suppliers[:5]
        )
        po_summary = f"{po_count} open POs totalling ${total_po_value:,.0f} USD"

        prompt = f"""You are a senior supply chain risk analyst at a multinational company.
Assess the geopolitical risk of the following event and provide actionable mitigation recommendations.

EVENT DETAILS:
  Headline   : {event.get('headline', 'Unknown event')}
  Date       : {event.get('date', '')}
  Country    : {event.get('source_country', '')}
  CAMEO Themes: {event.get('themes', '')}
  Sentiment  : {event.get('tone_score', 0)} (scale: very negative = -100, neutral = 0)

BUSINESS IMPACT:
  Affected suppliers : {supplier_count} ({supplier_names})
  Open POs at risk   : {po_summary}

Respond ONLY with valid JSON in exactly this schema:
{{
  "severity": "<Low|Medium|High|Critical>",
  "score_numeric": <1-4>,
  "justification": "<2â3 sentences explaining the score>",
  "recommendations": [
    "<Specific, actionable recommendation 1>",
    "<Specific, actionable recommendation 2>",
    "<Specific, actionable recommendation 3>",
    "<Specific, actionable recommendation 4>",
    "<Specific, actionable recommendation 5>"
  ]
}}

Requirements:
- severity and score_numeric must be consistent (Low=1, Medium=2, High=3, Critical=4)
- justification must reference the specific event and suppliers
- recommendations must be procurement/supply-chain specific, numbered, and immediately actionable
- For Critical/High events include at least one recommendation on alternative sourcing
- For Critical events include timeline (e.g. "within 24 hours", "within 72 hours")
"""

        model    = os.environ.get("AICORE_LLM_MODEL", "gpt-4o")
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        parsed = json.loads(response.choices[0].message.content)
        return {
            "severity":               parsed.get("severity", "Low"),
            "score_numeric":          int(parsed.get("score_numeric", 1)),
            "justification":          parsed.get("justification", ""),
            "recommendations":        parsed.get("recommendations", []),
            "affected_supplier_count": supplier_count,
            "affected_po_count":      po_count,
            "total_po_value":         total_po_value,
            "scoring_method":         "llm"
        }

    except Exception as e:
        logger.warning("LLM scoring failed (%s) â using rule-based fallback", str(e))
        return _rule_based_score(event, supplier_count, po_count, total_po_value)
