"""
TODO Reveal Service - Uses LLM to generate specific code implementations for TODO comments
This service analyzes the entire function context and TODO comment to generate targeted code
"""

import os
from openai import OpenAI
from typing import Optional, Dict

class TodoRevealService:
    def __init__(self):
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  Warning: No OpenAI API key found. TODO reveal will be disabled.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                print("✅ TODO Reveal Service initialized successfully!")
            except Exception as e:
                print(f"❌ Error initializing OpenAI client: {e}")
                self.client = None
    
    def generate_todo_code(self, todo_line: str, language: str, full_code: str = "", problem_context: str = "") -> Optional[Dict]:
        """
        Send TODO comment to LLM to generate specific code implementation
        Returns dict with generated code or None if not applicable
        """
        if not self.client:
            return None
        
        # Extract the actual TODO text (remove comment symbols)
        todo_text = self._extract_todo_text(todo_line, language)
        
        if not todo_text:
            return None
            
        try:
            # Create prompt for LLM
            prompt = f"""You are a coding assistant that helps implement specific TODO items within existing functions.

CONTEXT:
Language: {language}
TODO Line: "{todo_line.strip()}"
TODO Task: "{todo_text}"

Full Code Context:
```{language}
{full_code}
```

Problem Context:
{problem_context if problem_context else "No specific problem context provided"}

INSTRUCTIONS:
1. Analyze the TODO comment and the surrounding function context
2. Generate ONLY ONE LINE of specific code needed to implement this TODO
3. Make the code fit naturally within the existing function structure
4. Follow the existing code style and patterns
5. Generate EXACTLY ONE LINE - no multiple lines or complex blocks
6. DO NOT include the TODO comment itself in the response
7. DO NOT include surrounding code - just ONE implementation line
8. For loops, generate only the loop declaration line (e.g., "for item in items:")
9. For conditionals, generate only the if statement line (e.g., "if condition:")
10. For assignments, generate only the assignment line (e.g., "result = value")

RESPONSE FORMAT:
- Return ONLY ONE LINE of implementation code (no markdown, no explanations)
- If the TODO requires multiple lines, break it into smaller TODOs first
- If the TODO is unclear or cannot be implemented in one line: Return "CANNOT_IMPLEMENT"
- Use proper indentation to match the TODO line's indentation level
- Generate working, functional code that can stand alone as one line

EXAMPLES:

TODO: "# TODO: loop through each item in prices"
Response:
for item in prices:

TODO: "# TODO: calculate sum of numbers"
Response:  
total = sum(numbers)

TODO: "# TODO: check if user is valid"
Response:
if user and user.is_active:

TODO: "# TODO: append result to list"
Response:
results.append(result)

TODO: "// TODO: validate user input"
Response:
if (!input || input.trim() === '') {{
    throw new Error('Input cannot be empty');
}}

TODO: "# TODO: sort the array"
Response:
arr.sort()
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise coding assistant. Generate only ONE LINE of code needed to replace a TODO comment, with no extra explanations or formatting."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,  # Very restrictive to encourage single line responses
                temperature=0.1  # Lower temperature for more precise, focused code generation
            )
            
            generated_code = response.choices[0].message.content.strip()
            
            # Check if LLM said cannot implement
            if generated_code == "CANNOT_IMPLEMENT" or generated_code.startswith("CANNOT_IMPLEMENT"):
                return None
            
            # Ensure we only have one line (split by newlines and take first non-empty line)
            code_lines = [line.strip() for line in generated_code.split('\n') if line.strip()]
            if not code_lines:
                return None
            
            # Take only the first line to ensure single line response
            single_line_code = code_lines[0]
            
            # Validate that we got actual code (not just explanations)
            if self._is_valid_code_response(single_line_code, language):
                return {
                    "success": True,
                    "generatedCode": single_line_code,
                    "originalTodo": todo_line.strip(),
                    "todoText": todo_text,
                    "message": f"🎯 Code generated for: {todo_text}",
                    "language": language
                }
            else:
                print(f"⚠️  Generated response doesn't look like valid code: {single_line_code}")
                return None
            
        except Exception as e:
            print(f"❌ Error generating TODO code: {e}")
            return None

    def _extract_todo_text(self, todo_line: str, language: str) -> Optional[str]:
        """Extract the actual TODO text from the comment line"""
        line = todo_line.strip()
        
        # Common TODO patterns
        todo_patterns = [
            "# TODO:",
            "# todo:",
            "// TODO:",
            "// todo:",
            "/* TODO:",
            "/* todo:",
            "<!-- TODO:",
            "<!-- todo:"
        ]
        
        for pattern in todo_patterns:
            if pattern.lower() in line.lower():
                # Find the TODO text after the pattern
                start_idx = line.lower().find(pattern.lower()) + len(pattern)
                todo_text = line[start_idx:].strip()
                
                # Clean up any trailing comment symbols
                todo_text = todo_text.rstrip("*/").rstrip("-->").strip()
                
                if todo_text:
                    return todo_text
        
        return None
    
    def _is_valid_code_response(self, response: str, language: str) -> bool:
        """Basic validation that the response looks like code"""
        response = response.strip()
        
        # Check if response is too short or too explanatory
        if len(response) < 3:
            return False
        
        # Check for common non-code responses
        non_code_indicators = [
            "i cannot",
            "i can't", 
            "unable to",
            "this todo",
            "the todo",
            "explanation:",
            "here's how",
            "you need to",
            "you should",
            "based on the",
            "looking at the"
        ]
        
        response_lower = response.lower()
        for indicator in non_code_indicators:
            if indicator in response_lower:
                return False
        
        # Language-specific code indicators
        if language == "python":
            code_indicators = ["=", "def ", "if ", "for ", "while ", "return", "import", "print(", ".append(", ".extend("]
        elif language == "javascript":
            code_indicators = ["=", "function", "const ", "let ", "var ", "if (", "for (", "while (", "return", "console.log"]
        elif language == "java":
            code_indicators = ["=", "public ", "private ", "if (", "for (", "while (", "return", "System.out", "new "]
        else:
            # Generic code indicators
            code_indicators = ["=", "if", "for", "while", "return", "(", ")", "{", "}", "[", "]"]
        
        # Check if response contains code-like patterns
        has_code_indicators = any(indicator in response for indicator in code_indicators)
        
        return has_code_indicators
    
    def is_todo_line(self, line: str, language: str) -> bool:
        """Check if a line contains a TODO comment"""
        line_lower = line.strip().lower()
        
        todo_patterns = [
            "# todo",
            "// todo", 
            "/* todo",
            "<!-- todo"
        ]
        
        return any(pattern in line_lower for pattern in todo_patterns)
