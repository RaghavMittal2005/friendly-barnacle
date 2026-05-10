from typing import List, Dict, Tuple
from app.data.catalog_service import CatalogService

class AdaptiveRankingEngine:
    """Rank products based on user context"""
    
    def __init__(self, catalog_service: CatalogService):
        self.catalog = catalog_service
    
    def rank_products(self, 
                     candidates: List[str],
                     conversation_history: List[Dict],
                     user_message: str) -> List[Tuple[str, float]]:
        """Rank candidates based on detected context"""
        
        context = self._detect_context(conversation_history, user_message)
        strategy = self._choose_strategy(context)
        ranked = self._apply_strategy(candidates, strategy, context)
        
        return ranked
    
    def _detect_context(self, history: List[Dict], current_msg: str) -> Dict:
        """Analyze conversation to detect user requirements"""
        
        full_text = f"{' '.join([m.get('content', '') for m in history])} {current_msg}"
        full_text_lower = full_text.lower()
        
        SKILLS = {
            "java", "python", "rust", "golang", "javascript","data science", "machine learning", "devops", "aws", "azure",
            "c#", ".net", "sql", "react", "angular",
            "leadership", "communication", "innovation"
        }
        
        mentioned_skills = [
            skill for skill in SKILLS 
            if skill in full_text_lower
        ]
        
        has_selection = "hiring"
         
        
        job_levels = ["entry", "mid", "senior", "executive"]
        detected_level = next(
            (level for level in job_levels if level in full_text_lower),
            None
        )
        
        has_time_constraint = any(word in full_text_lower 
                                 for word in ["quick", "30 min", "fast", "short", "brief"])
        
        has_multiple = len(mentioned_skills) >= 2
        
        return {
            "mentioned_skills": mentioned_skills,
            "has_selection": has_selection,
            "job_level": detected_level,
            "has_time_constraint": has_time_constraint,
            "has_multiple_requirements": has_multiple,
            "is_comparison": "compare" in full_text_lower or "vs" in full_text_lower,
        }
    
    def _choose_strategy(self, context: Dict) -> str:
        """Decide which ranking strategy to use"""
        
        if context["is_comparison"]:
            return "comparison"
        
        if context["has_time_constraint"]:
            return "time_constrained"
        
        if context["has_multiple_requirements"]:
            return "multi_skill"
        
        if len(context["mentioned_skills"]) >= 1:
            return "specific_skill"
        
        if context["has_selection"]:
            return "selection_context"
        
        return "general_semantic"
    
    def _apply_strategy(self, candidates: List[str], 
                       strategy: str, context: Dict) -> List[Tuple[str, float]]:
        """Apply chosen ranking strategy"""
        
        if strategy == "specific_skill":
            return self._rank_specific_skill(candidates, context)
        elif strategy == "multi_skill":
            return self._rank_multi_skill(candidates, context)
        elif strategy == "selection_context":
            return self._rank_selection_context(candidates, context)
        elif strategy == "time_constrained":
            return self._rank_time_constrained(candidates, context)
        else:
            return self._rank_general_semantic(candidates)
    
    def _rank_specific_skill(self, candidates: List[str], context: Dict) -> List[Tuple[str, float]]:
        """Rank with HIGH keyword weight (3x)"""
        scores = {}
        
        for i, candidate_id in enumerate(candidates):
            product = self.catalog.get_product(candidate_id)
            if not product:
                continue
            
            # Position-based scoring
            keyword_score = (len(candidates) - i) * 3.0
            semantic_score = (len(candidates) - i) * 1.0
            
            level_bonus = 0
            if context["job_level"] and context["job_level"] in [
                jl.lower() for jl in product['job_levels']
            ]:
                level_bonus = 50
            
            scores[candidate_id] = keyword_score + semantic_score + level_bonus
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    def _rank_multi_skill(self, candidates: List[str], context: Dict) -> List[Tuple[str, float]]:
        """Rank based on how many skills each product covers"""
        scores = {}
        
        for i, candidate_id in enumerate(candidates):
            product = self.catalog.get_product(candidate_id)
            if not product:
                continue
            
            full_text = f"{product['name']} {product['description']}".lower()
            
            skill_matches = sum(
                1 for skill in context["mentioned_skills"]
                if skill.lower() in full_text
            )
            
            scores[candidate_id] = (
                skill_matches * 3.0 +
                (len(candidates) - i) * 2.0 +
                (len(candidates) - i) * 1.0
            )
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    def _rank_selection_context(self, candidates: List[str], context: Dict) -> List[Tuple[str, float]]:
        """Rank for hiring/selection scenarios"""
        scores = {}
        
        for i, candidate_id in enumerate(candidates):
            product = self.catalog.get_product(candidate_id)
            if not product:
                continue
            
            category_score = {
                "Knowledge & Skills": 100,
                "Personality & Behavior": 50,
                "Ability & Aptitude": 75,
            }.get(product['category'], 25)
            
            level_score = 0
            if context["job_level"] and context["job_level"] in [
                jl.lower() for jl in product['job_levels']
            ]:
                level_score = 100
            
            position_score = (len(candidates) - i) * 1.0
            
            scores[candidate_id] = category_score + level_score + position_score
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    def _rank_time_constrained(self, candidates: List[str], context: Dict) -> List[Tuple[str, float]]:
        """Prioritize shorter tests"""
        
        filtered = []
        for candidate_id in candidates:
            product = self.catalog.get_product(candidate_id)
            if product and product['duration_minutes'] and product['duration_minutes'] <= 30:
                filtered.append(candidate_id)
        
        if len(filtered) < 3:
            filtered = candidates
        
        return [(pid, float(i)) for i, pid in enumerate(filtered)]
    
    def _rank_general_semantic(self, candidates: List[str]) -> List[Tuple[str, float]]:
        """Default: semantic ranking"""
        return [(pid, float(i)) for i, pid in enumerate(candidates)]


class AdaptiveSearchEngine:
    """Hybrid search with adaptive ranking"""
    
    def __init__(self, catalog_service: CatalogService):
        self.catalog = catalog_service
        self.ranking_engine = AdaptiveRankingEngine(catalog_service)
    
    def search_adaptive(self,
                       user_query: str,
                       conversation_history: List[Dict]) -> List[str]:
        """Hybrid search with adaptive ranking"""
        
        # Extract keywords
        keywords = self._extract_keywords(user_query)
        
        # Hybrid search
        keyword_results = self.catalog.search_by_keywords(keywords)
        semantic_results = self.catalog.search_by_semantic(user_query, top_k=20)
        
        # Merge (default weights: keyword 2x, semantic 1x)
        merged = self._merge_results(keyword_results, semantic_results)
        
        # Adaptive ranking based on context
        ranked = self.ranking_engine.rank_products(
            merged[:20],
            conversation_history,
            user_query
        )
        
        return [pid for pid, _ in ranked]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        stopwords = {"the", "a", "in", "of", "to", "for", "is", "what", "how"}
        words = query.lower().split()
        return [w.strip(",.?!") for w in words 
                if len(w) > 3 and w.lower() not in stopwords]
    
    def _merge_results(self, keyword_results: List[str],
                      semantic_results: List[str]) -> List[str]:
        """Merge keyword and semantic results"""
        scores = {}
        
        for i, pid in enumerate(keyword_results):
            scores[pid] = scores.get(pid, 0) + (len(keyword_results) - i) * 2.0
        
        for i, pid in enumerate(semantic_results):
            scores[pid] = scores.get(pid, 0) + (len(semantic_results) - i) * 1.0
        
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [pid for pid, _ in sorted_results]
