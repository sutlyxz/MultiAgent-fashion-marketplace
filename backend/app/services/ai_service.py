import logging
from typing import Dict, Any, Optional
from app.database import db

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.policies = {
            "warranty": "Products are eligible for warranty claims within 30 days of delivery. Claims require proof of purchase and clear evidence of manufacturing defects.",
            "refund": "Refunds are processed only after the seller approves the claim. AI recommendations are advisory and do not execute refunds directly.",
            "shipping": "Standard shipping takes 3-5 business days. If tracking shows no update for more than 48 hours, a logistics ticket is automatically created."
        }

    def get_policy_context(self, query: str) -> str:
        query_lower = query.lower()
        context = []
        if "warranty" in query_lower or "claim" in query_lower:
            context.append(self.policies["warranty"])
        if "refund" in query_lower or "return" in query_lower:
            context.append(self.policies["refund"])
        if "shipping" in query_lower or "delivery" in query_lower or "track" in query_lower:
            context.append(self.policies["shipping"])

        return " ".join(context) if context else "General marketplace policy applies."

    def generate_chat_response(self, message: str, order_id: Optional[str] = None) -> Dict[str, Any]:
        context = self.get_policy_context(message)
        message_lower = message.lower()

        escalation_required = False
        suggested_action = None

        if "broken" in message_lower or "damaged" in message_lower or "defect" in message_lower:
            response = f"Based on our warranty policy: '{context}'. It looks like you have a product issue. I recommend submitting a warranty claim."
            suggested_action = "SUBMIT_WARRANTY_CLAIM"
        elif "where is my order" in message_lower or "delay" in message_lower or "tracking" in message_lower:
            response = f"Let me check the logistics status. According to our shipping policy: '{context}'. I will run a logistics check for you."
            suggested_action = "CHECK_LOGISTICS"
        else:
            response = f"Thank you for your inquiry. Here is some relevant policy information: {context}. How else can I assist you today?"

        return {
            "response": response,
            "escalation_required": escalation_required,
            "suggested_action": suggested_action
        }

    def get_warranty_recommendation(self, claim_reason: str) -> str:
        reason_lower = claim_reason.lower()
        if "defect" in reason_lower or "broken" in reason_lower or "torn" in reason_lower:
            return "AI Recommendation: APPROVE. The claim describes a clear manufacturing defect which is covered under our 30-day warranty policy."
        else:
            return "AI Recommendation: REJECT or REQUEST MORE INFO. The claim reason does not clearly indicate a manufacturing defect."

ai_service = AIService()