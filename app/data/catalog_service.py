import json
import numpy as np
import re
import os
from typing import List, Dict, Set, Optional
from sentence_transformers import SentenceTransformer
import faiss
from app.config import *

class CatalogService:
    """Loads, indexes, and searches SHL product catalog"""
    
    def __init__(self):
        self.catalog: Dict[str, Dict] = {}
        self.keyword_index: Dict[str, Set[str]] = {}
        self.faiss_index = None
        self.product_ids = []
        self.embeddings_model = None
        
    def load_catalog(self, json_path: str) -> None:
        """Load and enrich catalog"""
        print(f"Loading catalog from {json_path}...")
        
        try:
            # Load JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                raw_products = json.load(f)
            
            # Filter & enrich
            for product in raw_products:
                if self._is_individual_test(product):
                    enriched = self._enrich_product(product)
                    if enriched:
                        self.catalog[enriched["id"]] = enriched
            
            print(f"Loaded {len(self.catalog)} products")
            
            # Check if we should use precomputed FAISS index
            if USE_PRECOMPUTED_INDEX and os.path.exists(FAISS_INDEX_PATH):
                print("Loading precomputed FAISS index...")
                self._load_faiss_index(FAISS_INDEX_PATH, PRODUCT_IDS_PATH)
                print("Precomputed FAISS index loaded ✓")
            else:
                # Load embeddings model and build index
                print("Loading embeddings model...")
                self.embeddings_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
                self._build_faiss_index()
                # Save for future use
                self._save_faiss_index(FAISS_INDEX_PATH, PRODUCT_IDS_PATH)
            
            # Build keyword index
            self._build_keyword_index()
            print("Catalog loaded successfully ✓")
            
        except Exception as e:
            print(f"Error loading catalog: {e}")
            raise
    
    def _is_individual_test(self, product: Dict) -> bool:
        """Filter to Individual Test Solutions"""
        return product.get("status") == "ok"
    
    def _enrich_product(self, product: Dict) -> Optional[Dict]:
        """Extract & enhance product information"""
        try:
            full_text = f"{product['name']} {product.get('description', '')}"
            keywords = self._extract_keywords(full_text)
            
            return {
                "id": product["entity_id"],
                "name": product["name"],
                "url": product.get("link", ""),
                "description": product.get("description", ""),
                "category": self._infer_category(product),
                "duration_minutes": self._parse_duration(product.get("duration_raw", "")),
                "languages": product.get("languages", []),
                "job_levels": product.get("job_levels", []),
                "keys": product.get("keys", []),
                "keywords": keywords,
                "embedding": None,
            }
        except Exception as e:
            print(f"Error enriching product: {e}")
            return None
    
    def _infer_category(self, product: Dict) -> str:
        """Infer product category"""
        keys = product.get("keys", [])
        if "Knowledge & Skills" in keys:
            return "Knowledge & Skills"
        elif "Personality & Behavior" in keys:
            return "Personality & Behavior"
        elif "Ability & Aptitude" in keys:
            return "Ability & Aptitude"
        return "Other"
    
    def _parse_duration(self, duration_raw: str) -> Optional[int]:
        """Parse duration string to minutes"""
        if not duration_raw:
            return None
        try:
            match = re.search(r'=\s*(\d+)', duration_raw)
            return int(match.group(1)) if match else None
        except:
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        stopwords = {
            "the", "a", "an", "and", "or", "in", "of", "to", 
            "is", "this", "that", "with", "for", "from"
        }
        words = text.lower().split()
        keywords = [
            w.replace(".", "").replace(",", "")
            for w in words 
            if len(w) > 3 and w.lower() not in stopwords
        ]
        return list(set(keywords))[:20]
    
    def _build_faiss_index(self) -> None:
        """Generate embeddings & build FAISS index"""
        print("Building FAISS index...")
        
        texts = [p["description"] for p in self.catalog.values()]
        self.product_ids = list(self.catalog.keys())
        
        # Generate embeddings
        embeddings = self.embeddings_model.encode(texts, convert_to_numpy=True)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatL2(dimension)
        self.faiss_index.add(embeddings.astype(np.float32))
        
        # Store embeddings
        for idx, product_id in enumerate(self.product_ids):
            self.catalog[product_id]["embedding"] = embeddings[idx]
        
        print(f"FAISS index created with {len(texts)} vectors ✓")
    
    def _build_keyword_index(self) -> None:
        """Build keyword → product_ids mapping"""
        print("Building keyword index...")
        
        for product_id, product in self.catalog.items():
            index_terms = (
                product["keywords"] + 
                product["name"].lower().split() +
                [jl.lower() for jl in product["job_levels"]]
            )
            
            for term in index_terms:
                term_lower = term.lower()
                if term_lower not in self.keyword_index:
                    self.keyword_index[term_lower] = set()
                self.keyword_index[term_lower].add(product_id)
        
        print(f"Keyword index built with {len(self.keyword_index)} terms ✓")
    
    def search_by_keywords(self, keywords: List[str]) -> List[str]:
        """Keyword search"""
        matches = {}
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self.keyword_index:
                for product_id in self.keyword_index[keyword_lower]:
                    matches[product_id] = matches.get(product_id, 0) + 1
        
        ranked = sorted(matches.items(), key=lambda x: x[1], reverse=True)
        return [product_id for product_id, _ in ranked]
    
    def search_by_semantic(self, query: str, top_k: int = 10) -> List[str]:
        """Semantic search using FAISS"""
        if not self.faiss_index:
            return []
        
        query_embedding = self.embeddings_model.encode(query, convert_to_numpy=True)
        distances, indices = self.faiss_index.search(
            np.array([query_embedding], dtype=np.float32),
            k=min(top_k, len(self.product_ids))
        )
        
        return [self.product_ids[i] for i in indices[0]]
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Retrieve full product details"""
        return self.catalog.get(product_id)
    
    def filter_by_job_level(self, level: str) -> List[str]:
        """Filter products matching job level"""
        return [
            pid for pid, p in self.catalog.items()
            if level.lower() in [jl.lower() for jl in p["job_levels"]]
        ]
    
    def filter_by_category(self, category: str) -> List[str]:
        """Filter products by category"""
        return [
            pid for pid, p in self.catalog.items()
            if p["category"] == category
        ]
    
    def _save_faiss_index(self, faiss_path: str, ids_path: str) -> None:
        """Save FAISS index and product IDs to disk"""
        try:
            if not self.faiss_index:
                print("Warning: FAISS index not built, skipping save.")
                return
            
            print(f"Saving FAISS index to {faiss_path}...")
            faiss.write_index(self.faiss_index, faiss_path)
            
            print(f"Saving product IDs to {ids_path}...")
            with open(ids_path, 'w', encoding='utf-8') as f:
                json.dump(self.product_ids, f)
            
            print("FAISS index saved successfully ✓")
        except Exception as e:
            print(f"Error saving FAISS index: {e}")
    
    def _load_faiss_index(self, faiss_path: str, ids_path: str) -> None:
        """Load precomputed FAISS index and product IDs from disk"""
        try:
            if not os.path.exists(faiss_path):
                raise FileNotFoundError(f"FAISS index not found: {faiss_path}")
            if not os.path.exists(ids_path):
                raise FileNotFoundError(f"Product IDs file not found: {ids_path}")
            
            print(f"Loading FAISS index from {faiss_path}...")
            self.faiss_index = faiss.read_index(faiss_path)
            
            print(f"Loading product IDs from {ids_path}...")
            with open(ids_path, 'r', encoding='utf-8') as f:
                self.product_ids = json.load(f)
            
            print(f"Loaded {len(self.product_ids)} product IDs ✓")
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            raise
