#!/usr/bin/env python3
"""
Test script for the simplified scaffolding service
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from services.scaffolding_service import ScaffoldingService

def test_scaffolding():
    print("🧪 Testing Simplified Scaffolding Service")
    print("=" * 50)
    
    service = ScaffoldingService()
    
    # Test cases
    test_cases = [
        {
            "comment": "# Create a function to calculate average",
            "language": "python",
            "code": "# Create a function to calculate average\n"
        },
        {
            "comment": "// Implement bubble sort algorithm", 
            "language": "javascript",
            "code": "// Implement bubble sort algorithm\n"
        },
        {
            "comment": "# This is just a regular comment",
            "language": "python", 
            "code": "x = 5\n# This is just a regular comment\ny = 10\n"
        },
        {
            "comment": "# Define a class for bank account",
            "language": "python",
            "code": "# Define a class for bank account\n"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🔬 Test {i}: {test['comment']}")
        print(f"Language: {test['language']}")
        
        result = service.generate_scaffolding(
            comment_line=test['comment'],
            language=test['language'],
            full_code=test['code']
        )
        
        if result:
            print("✅ Scaffolding generated:")
            print("📝 Code:")
            print(result['scaffoldingCode'])
            print(f"💡 Hint: {result['hint']}")
        else:
            print("❌ No scaffolding generated (LLM said NO_SCAFFOLDING)")
        
        print("-" * 40)

if __name__ == "__main__":
    test_scaffolding()
