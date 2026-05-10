#!/usr/bin/env python
"""
Precompute FAISS index and product IDs for production deployment.

Run this ONCE locally before deployment to save embeddings and indexes.
This reduces memory usage on Render by 90%+ by avoiding loading the embedding model.

Usage:
    python precompute_faiss.py
"""

import os
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("SHL Assessment Recommender - FAISS Index Precomputation")
    print("=" * 70 + "\n")
    
    # Set environment variable to build fresh index
    os.environ["USE_PRECOMPUTED_INDEX"] = "0"
    
    try:
        from app.data.catalog_service import CatalogService
        from app.config import CATALOG_PATH
        
        print("Step 1: Loading catalog and building FAISS index...")
        print("-" * 70)
        
        catalog = CatalogService()
        catalog.load_catalog(str(CATALOG_PATH))
        
        print("\n" + "=" * 70)
        print("✓ FAISS Index precomputation complete!")
        print("=" * 70)
        
        # Verify files were created
        if os.path.exists("faiss.index") and os.path.exists("product_ids.json"):
            faiss_size = os.path.getsize("faiss.index") / (1024 * 1024)  # MB
            ids_size = os.path.getsize("product_ids.json") / 1024  # KB
            
            print(f"\n✓ Files created successfully:")
            print(f"  - faiss.index ({faiss_size:.1f} MB)")
            print(f"  - product_ids.json ({ids_size:.1f} KB)")
            print(f"\nNext steps:")
            print(f"  1. Commit these files to your GitHub repo")
            print(f"  2. On Render, set environment variable: USE_PRECOMPUTED_INDEX=1")
            print(f"  3. Deploy - no embedding model will be loaded on server!")
            print(f"\nMemory savings: ~90% reduction on Render!")
        else:
            print("\n⚠️  Warning: Expected files not found!")
            return 1
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Error during precomputation: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
