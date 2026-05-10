import os
import json
import re
from groq import Groq
from typing import List, Dict, Optional
from app.config import *
from dotenv import load_dotenv
load_dotenv()
class LLMService:
    """Wrapper around Groq API"""
    
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = LLM_MODEL
    
    def ask_clarifying_questions(self, user_query: str) -> str:
        """Behavior 1: Ask clarifying questions"""
        
        system_prompt = """You are an expert SHL assessment consultant helping hiring managers find the right tests.

Understand user's query without any assumptions.Then Ask 1-2 targeted clarifying questions to better understand user's requirements. For Example like these:
1. Job seniority level (Entry-Level, Mid-Level, Senior, Executive)
2. Skills focus (Technical Skills, Behavioral/Leadership, Cognitive Ability, or combination)
3. Which Depaartment
4. Which language if any assistant type role(eg. HR,receptionist,admin assistant)

Be concise and friendly. Do NOT recommend anything yet. Keep response under 100 words."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM error in clarification: {e}")
            return "I'd like to help you find the right assessment. Could you tell me the job seniority level and whether this is for selection or development?"
    
    def get_recommendations(self, 
                           conversation_summary: str,
                           candidate_products: List[Dict],
                           max_recommendations: int = 10) -> List[Dict]:
        """Behavior 2: Select best products"""
        
        products_text = self._format_products_for_llm(candidate_products[:20])
        
        system_prompt = f"""You are an SHL assessment expert. Based on the hiring need, select the best {max_recommendations} products from the candidates list below.

CRITICAL RULES:
1. Return ONLY products that appear in the list below
2. Maximum {max_recommendations} recommendations
3. Provide a brief, specific reason for each (one sentence)
4. Return ONLY valid JSON, no other text

Your response must be valid JSON in this exact format:
{{"recommendations": [{{"id": "4094", "reason": "Measures .NET/MVC expertise for mid-level developers"}}, ...]}}"""
        
        user_message = f"""Hiring Need:
{conversation_summary}

Candidate Products (select from these only):
{products_text}

Return JSON with best {max_recommendations} products."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result.get("recommendations", [])
        except Exception as e:
            print(f"LLM error in recommendations: {e}")
        
        return []
    
    def refine_recommendations(self,
                              current_recommendations: List[Dict],
                              new_constraint: str,
                              all_products: Dict[str, Dict]) -> List[Dict]:
        """Behavior 3: Refine recommendations"""
        
        current_text = "\n".join([
            f"- [{all_products[r['id']]['id']}] {all_products[r['id']]['name']}"
            for r in current_recommendations
            if r['id'] in all_products
        ])
        
        system_prompt = """You are an SHL assessment expert. The user has added a new requirement.
Update the recommendation list accordingly. You can add, remove, or reorder products.
Keep 1-10 recommendations total.

Return JSON: {"recommendations": [{"id": "...", "reason": "..."}]}"""
        
        user_message = f"""Current recommendations:
{current_text}

New requirement added by user: {new_constraint}

Update and return the refined list as JSON."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result.get("recommendations", [])
        except Exception as e:
            print(f"LLM error in refinement: {e}")
        
        return current_recommendations
    
    def compare_products(self,
                        products: List[Dict],
                        comparison_aspect: str) -> str:
        """Behavior 4: Compare products"""
        
        products_text = self._format_products_for_llm(products)
        
        system_prompt = f"""You are an SHL assessment expert. Compare these products on: {comparison_aspect}

Ground your comparison ONLY in the catalog data provided below. Do not speculate or add information not in the catalog.
Be specific and factual."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": products_text}
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM error in comparison: {e}")
            return "I couldn't generate a comparison at this time."
    
    def _format_products_for_llm(self, products: List[Dict]) -> str:
        """Format products as readable text for LLM"""
        lines = []
        for i, p in enumerate(products, 1):
            lines.append(f"{i}. [{p['id']}] {p['name']}")
            lines.append(f"   Duration: {p.get('duration_minutes', 'N/A')} min")
            lines.append(f"   Category: {p['category']}")
            lines.append(f"   Levels: {', '.join(p.get('job_levels', [])[:3])}")
            lines.append(f"   {p['description'][:120]}...")
            lines.append("")
        
        return "\n".join(lines)
