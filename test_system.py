#!/usr/bin/env python
"""
Test script to validate SHL Assessment Recommender system
"""

import sys
import json
from pathlib import Path

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")
    try:
        from app.config import GROQ_API_KEY, LLM_MODEL, CATALOG_PATH
        from app.models import ChatRequest, ChatResponse, Message
        from app.data.catalog_service import CatalogService
        from app.ai.llm_service import LLMService
        from app.logic.search_engine import AdaptiveSearchEngine, AdaptiveRankingEngine
        from app.logic.conversation_manager import ConversationManager
        print("✓ All imports successful\n")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}\n")
        return False

def test_catalog_loading():
    """Test catalog service"""
    print("🔍 Testing catalog service...")
    try:
        from app.data.catalog_service import CatalogService
        from app.config import CATALOG_PATH
        
        service = CatalogService()
        service.load_catalog(CATALOG_PATH)
        
        catalog_size = len(service.catalog)
        print(f"✓ Catalog loaded: {catalog_size} products")
        
        # Test a product lookup
        sample_id = list(service.catalog.keys())[0] if service.catalog else None
        if sample_id:
            product = service.get_product(sample_id)
            print(f"  Sample: {product['name']}")
        
        print()
        return True
    except Exception as e:
        print(f"✗ Catalog loading failed: {e}\n")
        return False

def test_config():
    """Test configuration"""
    print("🔍 Testing configuration...")
    try:
        from app.config import GROQ_API_KEY, LLM_MODEL, CATALOG_PATH, API_TITLE
        
        issues = []
        if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
            issues.append("GROQ_API_KEY not configured")
        if not LLM_MODEL:
            issues.append("LLM_MODEL not set")
        if not Path(CATALOG_PATH).exists():
            issues.append(f"Catalog file not found: {CATALOG_PATH}")
        
        if issues:
            print(f"⚠️  Configuration issues:")
            for issue in issues:
                print(f"   - {issue}")
            print()
            return False
        
        print(f"✓ Configuration valid:")
        print(f"  - LLM Model: {LLM_MODEL}")
        print(f"  - API Title: {API_TITLE}")
        print()
        return True
    except Exception as e:
        print(f"✗ Configuration check failed: {e}\n")
        return False

def test_search_engine():
    """Test search engine"""
    print("🔍 Testing search engine...")
    try:
        from app.data.catalog_service import CatalogService
        from app.logic.search_engine import AdaptiveSearchEngine
        from app.config import CATALOG_PATH
        
        # Load catalog
        catalog = CatalogService()
        catalog.load_catalog(CATALOG_PATH)
        
        # Create search engine
        search_engine = AdaptiveSearchEngine(catalog)
        
        # Test search
        results = search_engine.search_adaptive("senior Python developer", [])
        print(f"✓ Search engine working:")
        print(f"  - Found {len(results)} results for 'senior Python developer'")
        if results:
            first_product = catalog.get_product(results[0])
            print(f"  - Top result: {first_product['name']}")
        
        print()
        return True
    except Exception as e:
        print(f"✗ Search engine test failed: {e}\n")
        return False

def test_models():
    """Test Pydantic models"""
    print("🔍 Testing models...")
    try:
        from app.models import Message, ChatRequest, ChatResponse, Recommendation
        
        # Test message creation
        msg = Message(role="user", content="Test")
        
        # Test request creation
        req = ChatRequest(messages=[msg])
        
        # Test recommendation
        rec = Recommendation(
            id="1",
            name="Test",
            url="http://test.com",
            duration_minutes=60,
            category="Test",
            reason="Test reason"
        )
        
        # Test response
        resp = ChatResponse(
            reply="Test",
            recommendations=[rec],
            end_of_conversation=False
        )
        
        print(f"✓ All models valid")
        print(f"  - Message, ChatRequest, ChatResponse, Recommendation")
        print()
        return True
    except Exception as e:
        print(f"✗ Model test failed: {e}\n")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("SHL Assessment Recommender - System Test")
    print("=" * 60 + "\n")
    
    tests = [
        ("Configuration", test_config),
        ("Imports", test_imports),
        ("Models", test_models),
        ("Catalog Service", test_catalog_loading),
        ("Search Engine", test_search_engine),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}\n")
            results.append((test_name, False))
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    print("-" * 60)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    if passed == total:
        print("✨ All tests passed! System is ready to use.")
        print("\nTo start the API server:")
        print("  python main.py")
        print("\nThen visit: http://localhost:8000/docs")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please check configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
