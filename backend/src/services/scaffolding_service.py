"""
Scaffolding Service - Uses LLM to generate code scaffolding from user comments
Simple approach: detect comment, ask LLM if scaffolding is needed, generate if yes
"""

import os
from openai import OpenAI
from typing import Optional, Dict

class ScaffoldingService:
    def __init__(self):
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  Warning: No OpenAI API key found. Scaffolding will be disabled.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                print("✅ Scaffolding Service initialized successfully!")
            except Exception as e:
                print(f"❌ Error initializing OpenAI client: {e}")
                self.client = None
    
    def generate_scaffolding(self, comment_line: str, language: str, full_code: str = "") -> Optional[Dict]:
        """
        Send comment to LLM to check if scaffolding is needed and generate it
        Returns dict with scaffolding info or None if no scaffolding needed
        """
        if not self.client:
            return None
            
        try:
            # Create prompt for LLM
            prompt = f"""You are a coding tutor that creates minimal scaffolding to help students learn by doing.

                        A user wrote this comment in a {language} file:
                        "{comment_line.strip()}"

                        Full code context:
                        ```{language}
                        {full_code}
                        ```

                        CRITICAL RULES:
                        1. Only provide scaffolding if the comment indicates the user wants to implement something
                        2. Generate MINIMAL scaffolding - just structure, NO solutions
                        3. Use descriptive TODO comments instead of ___ placeholders
                        4. Keep it SHORT (max 5-8 lines)
                        5. Students must fill in ALL the actual implementation

                        SCAFFOLDING REQUIREMENTS:
                        - Function signatures with TODO comments for body
                        - Class definitions with TODO comments for methods
                        - Control structures with TODO comments for conditions/logic
                        - Variable declarations with TODO comments for values
                        - Clear, descriptive TODO guidance
                        - NO actual implementation or solutions

                        OUTPUT FORMAT:
                        - If scaffolding needed: Return ONLY the minimal scaffolding code (NO markdown formatting, NO code blocks, just raw code)
                        - If no scaffolding needed: Return exactly "NO_SCAFFOLDING"
                        - Do NOT use ```language``` formatting in your response
                        - Return plain text code only

                        GOOD scaffolding examples:
                        Comment: "# Create a function to calculate average"
                        Output: 
                        def calculate_average(numbers):
                            # TODO: calculate sum of all numbers
                            # TODO: divide sum by count of numbers
                            # TODO: return the average

                        Comment: "// Implement bubble sort"
                        Output:
                        function bubbleSort(arr) {{
                            # TODO: loop through array multiple times
                            # TODO: compare adjacent elements
                            # TODO: swap if in wrong order
                            # TODO: return sorted array
                        }}

                        BAD examples (too much solution):
                        - Any actual calculations or logic
                        - Complete implementations
                        - Specific values or algorithms
                        """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a coding tutor that creates minimal scaffolding. Never provide complete solutions - only structure with blanks for students to fill in."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,  # Reduced to encourage shorter responses
                temperature=0.1  # Lower temperature for more consistent, focused output
            )
            
            print(response)

            scaffolding_code = response.choices[0].message.content.strip()
            
            # Check if LLM said no scaffolding needed
            if scaffolding_code == "NO_SCAFFOLDING" or scaffolding_code.startswith("NO_SCAFFOLDING"):
                return None
            
            # Additional safety check: reject if response is too long (likely a solution)
            if len(scaffolding_code.split('\n')) > 10:
                print("⚠️  Scaffolding response too long, likely contains solutions. Rejecting.")
                return None
            
            # Return scaffolding result
            return {
                "hasScaffolding": True,
                "scaffoldingCode": scaffolding_code,
                "originalComment": comment_line.strip(),
                "hint": f"💡 Scaffolding added! Follow the TODO comments to complete your implementation.",
                "language": language
            }
            
        except Exception as e:
            print(f"❌ Error generating scaffolding: {e}")
            return None
