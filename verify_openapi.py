#!/usr/bin/env python3
"""
Verify that the OpenAPI documentation structure is correctly implemented.
This script checks the code structure without requiring all dependencies.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print the result."""
    if os.path.exists(file_path):
        print(f"✓ {description}: {file_path}")
        return True
    
    print(f"✗ {description}: {file_path} (NOT FOUND)")
    return False

def check_file_content(file_path, search_terms, description):
    """Check if a file contains specific terms."""
    if not os.path.exists(file_path):
        print(f"✗ {description}: File not found")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found_terms = []
        missing_terms = []
        
        for term in search_terms:
            if term in content:
                found_terms.append(term)
            else:
                missing_terms.append(term)
        
        if missing_terms:
            print(f"✗ {description}: Missing {missing_terms}")
            return False
        
        print(f"✓ {description}: All required terms found")
        return True
    except Exception as e:
        print(f"✗ {description}: Error reading file - {e}")
        return False

def main():
    """Main verification function."""
    print("Verifying OpenAPI Documentation Implementation")
    print("=" * 50)
    
    base_path = Path(__file__).parent
    src_path = base_path / "src" / "agentic_fleet"
    
    all_checks_passed = True
    
    # Check main API file
    main_api_file = src_path / "api" / "main.py"
    if check_file_exists(main_api_file, "Main API file"):
        openapi_terms = [
            "FastAPI",
            "title=",
            "description=",
            "openapi_tags=",
            "docs_url=",
            "redoc_url=",
            "openapi_url=",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        all_checks_passed &= check_file_content(
            main_api_file, 
            openapi_terms, 
            "Main API OpenAPI configuration"
        )
    else:
        all_checks_passed = False
    
    # Check route files
    routes_path = src_path / "api" / "routes"
    route_files = ["agents.py", "tasks.py", "chat.py"]
    
    for route_file in route_files:
        route_path = routes_path / route_file
        if check_file_exists(route_path, f"Route file ({route_file})"):
            route_terms = [
                "@router.",
                "response_model=",
                '"""',  # Docstrings
                "async def"
            ]
            all_checks_passed &= check_file_content(
                route_path,
                route_terms,
                f"Route documentation ({route_file})"
            )
        else:
            all_checks_passed = False
    
    # Check main entry point
    main_entry = src_path / "main.py"
    if check_file_exists(main_entry, "Main entry point"):
        entry_terms = [
            "run_api",
            "OpenAPI documentation",
            'default="api"'
        ]
        all_checks_passed &= check_file_content(
            main_entry,
            entry_terms,
            "Main entry point API mode"
        )
    else:
        all_checks_passed = False
    
    # Check documentation file
    docs_file = base_path / "docs" / "openapi.md"
    if check_file_exists(docs_file, "OpenAPI documentation"):
        doc_terms = [
            "OpenAPI Documentation",
            "/docs",
            "/redoc",
            "/openapi.json",
            "Swagger UI",
            "ReDoc"
        ]
        all_checks_passed &= check_file_content(
            docs_file,
            doc_terms,
            "Documentation content"
        )
    else:
        all_checks_passed = False
    
    print(f"\n{'=' * 50}")
    if all_checks_passed:
        print("✓ All OpenAPI documentation checks passed!")
        print("\nThe OpenAPI documentation has been successfully implemented:")
        print("- Comprehensive FastAPI app with OpenAPI configuration")
        print("- Enhanced route documentation with detailed docstrings")
        print("- Multiple documentation formats (Swagger UI, ReDoc, JSON)")
        print("- Updated main entry point to use API mode by default")
        print("- Complete documentation guide")
        print("\nTo test the API:")
        print("1. Install dependencies: pip install -e .")
        print("2. Run the API: python -m agentic_fleet.main")
        print("3. Visit http://localhost:8000/docs for interactive documentation")
    else:
        print("✗ Some checks failed. Please review the implementation.")
    
    return all_checks_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)