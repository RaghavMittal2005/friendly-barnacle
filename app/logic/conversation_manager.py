import re
from typing import List, Dict, Optional
from app.data.catalog_service import CatalogService
from app.ai.llm_service import LLMService
from app.logic.search_engine import AdaptiveSearchEngine
from app.models import Recommendation

class ConversationManager:
    """Routes user messages through conversational behaviors"""
    
    def __init__(self, catalog_service: CatalogService, llm_service: LLMService):
        self.catalog = catalog_service
        self.llm = llm_service
        self.search_engine = AdaptiveSearchEngine(catalog_service)
        self.max_turns = 8
    
    def process_message(self,
                   user_message: str,
                   conversation_history: List[Dict]) -> Dict:
    
     history = list(conversation_history)
    
     turn_count = len(history) // 2

     if self._is_end_signal(user_message) or turn_count >= self.max_turns:
        result = self._handle_conversation_end(history, user_message)
     else:
        intent = self._detect_intent(user_message, history)

        if intent == "clarify":
            result = self._handle_clarification(user_message)
        elif intent == "recommend":
            result = self._handle_recommendation(user_message, history)
        elif intent == "refine":
            result = self._handle_refinement(user_message, history)
        elif intent == "compare":
            result = self._handle_comparison(user_message, history)
        else:
            result = self._handle_clarification(user_message)

    # Append BOTH turns AFTER generating the reply
     history.append({"role": "user", "content": user_message})
     history.append({"role": "assistant", "content": result["reply"]})

     result["conversation_history"] = history  # return it to caller
     return result
    
    def _detect_intent(self, user_msg: str, history: List[Dict]) -> str:
        """Classify user intent"""
        
        msg_lower = user_msg.lower()
        is_refinement = any(
            word in msg_lower
            for word in ["also", "add", "plus", "include", "besides", "instead", "remove", "shorter", "longer"]
        )
        
        # STOP asking questions after first exchange - just recommend!
        # If we have multiple turns in history, user already responded to something
        if len(history) >= 2:
            # Check for comparison request
            if any(word in msg_lower for word in ["compare", "difference", "vs ", "versus"]):
                return "compare"
            if is_refinement:
                return "refine"
            # Otherwise always recommend - don't ask more questions
            return "recommend"
        
        # Check for comparison
        if any(word in msg_lower for word in ["compare", "difference", "vs ", "versus"]):
            return "compare"
        
        # Check for refinement
        if is_refinement:
            if len(history) > 0:  # Has context
                return "refine"
        
        # Check for recommendation request
        if any(word in msg_lower for word in ["test", "assessment", "what", "which", "recommend"]):
            return "recommend"
        
        # Check for clarification needed
        if any(word in msg_lower for word in ["hiring", "recruit", "senior", "junior", "develop"]):
            if len(history) == 0:  # First message
                return "clarify"
            else:
                return "recommend"
        
        # Default to clarify if first message, recommend otherwise
        return "recommend" if len(history) > 0 else "clarify"
    
    def _is_end_signal(self, message: str) -> bool:
        """Check if user wants to end conversation"""
        end_signals = ["thanks", "thank you", "perfect", "good", "done", "that's all", "great", "helpful"]
        return any(signal in message.lower() for signal in end_signals)
    
    def _handle_clarification(self, user_query: str) -> Dict:
        """Behavior 1: Ask clarifying questions"""
        
        agent_reply = self.llm.ask_clarifying_questions(user_query)
        
        return {
            "reply": agent_reply,
            "recommendations": [],
            "end_of_conversation": False
        }
    
    def _handle_recommendation(self, user_message: str, history: List[Dict]) -> Dict:
        """Behavior 2: Recommend products"""
        
        # Build full conversation context
        full_context = " ".join([m.get('content', '') for m in history] + [user_message])
        
        # Search catalog adaptively
        candidates_ids = self.search_engine.search_adaptive(full_context, history)
        
        # Get candidate products
        candidates = [
            self.catalog.get_product(pid)
            for pid in candidates_ids[:20]
            if self.catalog.get_product(pid)
        ]
        
        if not candidates:
            return {
                "reply": "I couldn't find matching assessments in our catalog. Could you provide more details about the role or skills you're looking for?",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        # Get LLM recommendations with full conversation history
        recommendations = self.llm.get_recommendations(
            history,
            user_message,
            candidates,
            max_recommendations=10
        )
        
        # Format response
        agent_reply = self._format_recommendations_reply(recommendations)
        
        return {
            "reply": agent_reply,
            "recommendations": self._hydrate_recommendations(recommendations),
            "end_of_conversation": False
        }
    
    def _handle_refinement(self, user_message: str, history: List[Dict]) -> Dict:
        """Behavior 3: Refine existing recommendations"""
        
        # Extract previous recommendations from history
        prev_recs = self._extract_previous_recommendations(history)
        
        if not prev_recs:
            return self._handle_recommendation(user_message, history)
        
        # Refine with LLM using full conversation history
        refined = self.llm.refine_recommendations(
            history,
            user_message,
            prev_recs,
            self.catalog.catalog
        )
        
        agent_reply = self._format_recommendations_reply(refined)
        
        return {
            "reply": agent_reply,
            "recommendations": self._hydrate_recommendations(refined),
            "end_of_conversation": False
        }
    
    def _handle_comparison(self, user_message: str, history: List[Dict]) -> Dict:
        """Behavior 4: Compare products"""
        
        # Extract product references from conversation
        product_ids = self._extract_product_ids(user_message, history)
        
        if len(product_ids) < 2:
            return {
                "reply": "Please specify which products you'd like me to compare.",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        # Get products
        products = [
            self.catalog.get_product(pid)
            for pid in product_ids[:3]
            if self.catalog.get_product(pid)
        ]
        
        if not products:
            return {
                "reply": "I couldn't find those products. Could you rephrase?",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        # Get comparison with full conversation history
        comparison = self.llm.compare_products(
            history,
            user_message,
            products
        )
        
        return {
            "reply": comparison,
            "recommendations": [],
            "end_of_conversation": False
        }
    
    def _handle_conversation_end(self, history: List[Dict], user_message: str) -> Dict:
        """When user is done"""
        
        final_summary = self._build_final_summary(history, user_message)
        
        return {
            "reply": final_summary,
            "recommendations": [],
            "end_of_conversation": True
        }
    
    # Helper methods
    
    
    def _format_recommendations_reply(self, recommendations: List[Dict]) -> str:
        """Format recommendations as readable text"""
        
        if not recommendations:
            return "I couldn't generate recommendations at this time. Could you provide more details?"
        
        lines = ["Here are the assessments I recommend:"]
        for index, rec in enumerate(recommendations, 1):
            product_id = rec.get("id")
            product = self.catalog.get_product(product_id) if product_id else None
            if not product:
                continue

            reason = rec.get("reason", "Matches your requirements")
            duration = product.get("duration_minutes")
            duration_text = f"{duration} min" if duration else "Duration not listed"
            lines.append(
                f"{index}. [{product_id}] {product['name']} - {reason} "
                f"({product['category']}, {duration_text})"
            )
        
        return "\n".join(lines)
    
    def _hydrate_recommendations(self, rec_data: List[Dict]) -> List[Recommendation]:
        """Convert LLM recommendations to full Recommendation objects"""
        
        result = []
        for rec in rec_data:
            product_id = rec.get('id')
            if product_id and product_id in self.catalog.catalog:
                product = self.catalog.get_product(product_id)
                result.append(Recommendation(
                    id=product_id,
                    name=product['name'],
                    url=product['url'],
                    duration_minutes=product['duration_minutes'],
                    category=product['category'],
                    reason=rec.get('reason', 'Matches your requirements')
                ))
        
        return result
    
    def _extract_previous_recommendations(self, history: List[Dict]) -> List[Dict]:
        """Try to extract previous recommendations from history"""
        recs = []
        seen = set()

        for message in history:
            if message.get("role") != "assistant":
                continue

            content = message.get("content", "")
            for product_id in re.findall(r"\[([^\]]+)\]", content):
                if product_id in self.catalog.catalog and product_id not in seen:
                    seen.add(product_id)
                    recs.append({
                        "id": product_id,
                        "reason": "Previously recommended in this conversation"
                    })

        return recs
    
    def _extract_product_ids(self, user_message: str, history: List[Dict]) -> List[str]:
        """Extract product IDs mentioned by user"""
        # Look for product names/IDs in the latest message and prior assistant replies.
        product_ids = []
        combined_text = " ".join(
            [user_message] + [m.get("content", "") for m in history]
        )
        msg_lower = combined_text.lower()
        
        for product_id in re.findall(r"\[([^\]]+)\]", combined_text):
            if product_id in self.catalog.catalog and product_id not in product_ids:
                product_ids.append(product_id)
        
        for product_id, product in self.catalog.catalog.items():
            if product_id not in product_ids and product['name'].lower() in msg_lower:
                product_ids.append(product_id)
        
        return product_ids[:3]
    
    def _extract_comparison_aspect(self, user_message: str) -> str:
        """Extract what to compare on"""
        
        if "difference" in user_message.lower():
            return "differences and similarities"
        elif "cost" in user_message.lower() or "price" in user_message.lower():
            return "pricing and duration"
        elif "personality" in user_message.lower() or "behavioral" in user_message.lower():
            return "personality measurement approach"
        else:
            return "key differences and when to use each"
    
    def _build_final_summary(self, history: List[Dict], user_message: str) -> str:
        """Build end-of-conversation summary"""
        
        return """Thank you for using the SHL Assessment Recommender! 

Based on our conversation, I've identified assessments that match your hiring needs. 

**Next steps:**
1. Review the recommended assessments
2. Consider the time commitment and candidate profile
3. Consider combining assessments for a comprehensive evaluation

If you need further clarification or have questions about any of these assessments, feel free to reach out!"""
