"""
AI Code Analysis Service - Handles code analysis and execution validation
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from openai import OpenAI

from .ai_models import ConversationContext


class AICodeAnalysisService:
    def __init__(self, client: OpenAI, socketio_instance):
        self.client = client
        self.socketio = socketio_instance
        
        # Execution validation tracking
        self.execution_attempts = {}  # Track attempts per room for graduated help
        self.validation_tasks = {}    # Track running validation tasks

    def analyze_code_block(self, code: str, language: str, context: Dict[str, Any], 
                          problem_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a code block for potential issues and provide suggestions"""
        print(f"🔍 Starting code analysis with OpenAI")
        
        if not self.client:
            return self._mock_code_analysis(code, language, context, problem_context)
        
        try:
            print("🚀 Using OpenAI analysis")
            # Create analysis prompt with problem context
            analysis_prompt = self._create_code_analysis_prompt(code, language, context, problem_context)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert code reviewer and pair programming partner. Analyze code blocks for potential issues, bugs, security vulnerabilities, performance problems, and best practice violations. Consider the problem context when evaluating whether code is appropriate - partial solutions and work-in-progress code should be judged differently than complete solutions. Provide practical, actionable suggestions."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            analysis = self._parse_code_analysis(analysis_text, code, context, problem_context)
            
            return {
                'issues': analysis.get('issues', []),
                'suggestions': analysis.get('suggestions', []),
                'timestamp': datetime.now().isoformat(),
                'confidence': analysis.get('confidence', 'medium')
            }
            
        except Exception as e:
            print(f"❌ Error in OpenAI code analysis: {e}")
            # Return empty result if OpenAI fails
            return {
                'issues': [],
                'suggestions': [],
                'timestamp': datetime.now().isoformat(),
                'confidence': 'low'
            }

    def _mock_code_analysis(self, code: str, language: str, context: Dict[str, Any], 
                           problem_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Provide mock analysis when OpenAI is not available"""
        issues = []
        
        print(f"🔍 Mock analysis with problem context: {problem_context}")
        
        # Context-aware analysis based on problem
        if problem_context:
            problem_title = problem_context.get('title', '').lower()
            problem_description = problem_context.get('description', '').lower()
            
            # Check if code aligns with problem expectations
            if 'two sum' in problem_title or 'sum' in problem_title:
                if 'for' in code and 'range' in code:
                    # Check for undefined variables in range()
                    import re
                    range_matches = re.findall(r'range\(([^)]+)\)', code)
                    for match in range_matches:
                        if match.strip() not in ['len(arr)', 'len(nums)', 'len(array)'] and not match.strip().isdigit():
                            # Check if it's a variable that might be undefined
                            if match.strip() in ['n', 'm', 'size', 'length'] and match.strip() not in code.replace('range', ''):
                                issues.append({
                                    'id': 'undefined_variable',
                                    'type': 'Bug Risk',
                                    'severity': 'high',
                                    'title': f'Undefined Variable: {match.strip()}',
                                    'description': f'The variable "{match.strip()}" is used in range() but not defined. This will cause a NameError.',
                                    'suggestedFix': {
                                        'description': f'Replace {match.strip()} with len(arr) or define the variable',
                                        'code': f'for i in range(len(arr)):  # Use len(arr) instead of {match.strip()}',
                                        'explanation': 'Use len(arr) to get the actual length of the array'
                                    }
                                })
        
        # General pattern-based analysis
        if 'password' in code.lower() and ('=' in code or ':' in code):
            issues.append({
                'id': 'hardcoded_password',
                'type': 'Security',
                'severity': 'high',
                'title': 'Hardcoded Password Detected',
                'description': 'Hardcoded passwords in source code pose security risks. Use environment variables or secure configuration instead.',
                'line': context.get('cursorLine', 1),
                'codeSnippet': code.split('\n')[0] if code else '',
                'suggestedFix': {
                    'description': 'Use environment variables for sensitive data',
                    'code': 'password = os.getenv("DB_PASSWORD")'
                }
            })
        
        return {
            'issues': issues,
            'suggestions': [],
            'timestamp': datetime.now().isoformat(),
            'confidence': 'medium' if issues else 'low'
        }

    def _create_code_analysis_prompt(self, code: str, language: str, context: Dict[str, Any], 
                                   problem_context: Optional[Dict[str, Any]] = None) -> str:
        """Create a comprehensive prompt for code analysis"""
        
        problem_info = ""
        if problem_context:
            problem_info = f"""
                            PROBLEM CONTEXT:
                            Title: {problem_context.get('title', 'Unknown')}
                            Description: {problem_context.get('description', 'No description provided')}

                            IMPORTANT: This code is being written to solve the above problem. Consider whether the approach is:
                            - Appropriate for the problem requirements
                            - A reasonable work-in-progress solution
                            - Following expected algorithmic patterns for this type of problem
                            - Missing key components needed for the solution

                            """
        
        return f"""
                Analyze this {language} code block for learning purposes:

                ```{language}
                {code}
                ```

                Context:
                - Lines: {context.get('startLine', 1)}-{context.get('endLine', 1)}
                - Cursor position: Line {context.get('cursorLine', 1)}

                {problem_info}

                IMPORTANT: Focus on functional correctness, logic, and learning opportunities.
                DO NOT comment on:
                - Naming conventions (camelCase vs snake_case is fine)
                - Missing comments (code can be self-explanatory)
                - Code style preferences (spacing, formatting)
                - Code organization preferences

                Analyze for learning purposes:
                1. **Undefined Variables**: Variables used but not defined
                2. **Logic Errors**: Algorithm mistakes, wrong loop bounds, incorrect conditions
                3. **Syntax Errors**: Missing parentheses, colons, indentation errors
                4. **Runtime Errors**: Index out of bounds, division by zero, type errors
                5. **Algorithm Optimization**: Inefficient approaches, better algorithms available
                6. **Learning Opportunities**: Algorithmic improvements

                If the code is functionally correct and reasonably efficient, respond with positive feedback.

                Format as JSON:
                {{
                "issue": {{
                    "title": "Brief title covering main problem(s) or 'Code looks good!'",
                    "description": "Concise explanation of what's wrong OR positive feedback (1-2 sentences)",
                    "hint": "Quick practical solution OR encouragement (1-2 sentences)"
                }}
                }}

                If code is good, return positive feedback like:
                {{"issue": {{"title": "Code looks good!", "description": "Your solution is working correctly and follows good algorithmic practices.", "hint": "Great work! This approach should solve the problem effectively."}}}}

                Examples of VALID issues:
                - "Optimization Opportunity: O(n²) nested loops could be O(n) with hash map. Hint: Store seen values for faster lookup."
                - "Logic Error: Loop condition 'i <= len(arr)' causes index error. Hint: Use 'i < len(arr)'."
                
                Examples of INVALID issues (DO NOT report):
                - Variable naming conventions
                - Missing comments
                - Code formatting/style
                """

    def _parse_code_analysis(self, analysis_text: str, code: str, context: Dict[str, Any], 
                           problem_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse the AI response and create structured analysis"""
        try:
            # Simple slice to remove ```json and ``` from the response
            cleaned_text = analysis_text.strip()
            if cleaned_text.startswith('```json') and cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[7:-4].strip()
            
            analysis = json.loads(cleaned_text)
            
            # Handle single-issue format
            if 'issue' in analysis:
                issue_data = analysis.get('issue')
                if issue_data is None:
                    # No issues found
                    return {'issues': []}
                
                # Check if this is positive feedback (code is good)
                title = issue_data.get('title', '').lower()
                is_positive_feedback = any(phrase in title for phrase in [
                    'code looks good', 'good', 'great', 'excellent', 'well done', 
                    'correct', 'nice', 'perfect', 'solid'
                ])
                
                if is_positive_feedback:
                    # For positive feedback, create a success-type entry
                    positive_feedback = {
                        'id': f"feedback_{hash(issue_data.get('title', 'good'))}",
                        'type': 'Success',
                        'severity': 'info',
                        'title': issue_data.get('title', 'Code looks good!'),
                        'description': issue_data.get('description', 'Your code is working well!'),
                        'line': context.get('cursorLine', 1),
                        'codeSnippet': code.split('\n')[0] if code else '',
                        'suggestedFix': {
                            'description': issue_data.get('hint', 'Keep up the great work!'),
                            'code': '',
                            'explanation': issue_data.get('hint', 'Continue with this approach!')
                        }
                    }
                    return {'issues': [positive_feedback]}
                
                # Convert single issue to array format for frontend
                single_issue = {
                    'id': f"issue_{hash(issue_data.get('title', 'unknown'))}",
                    'type': 'Code Review',
                    'severity': 'medium',
                    'title': issue_data.get('title', 'Code Issue'),
                    'description': issue_data.get('description', 'No description provided'),
                    'line': context.get('cursorLine', 1),
                    'codeSnippet': code.split('\n')[0] if code else '',
                    'suggestedFix': {
                        'description': issue_data.get('hint', 'No hint provided'),
                        'code': '',
                        'explanation': issue_data.get('hint', '')
                    }
                }
                
                return {'issues': [single_issue]}
            
            # Fallback for any other format
            return {'issues': []}
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"🔍 Raw response: {analysis_text}")
            return {'issues': []}
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {'issues': []}

    def analyze_execution_for_panel(self, code: str, result: dict, problem_context: str = None) -> dict:
        """Generate concise help for execution panel display"""
        
        if not self.client:
            return None
        
        try:
            # Only analyze if there's an issue or potential improvement
            has_error = not result.get('success', True)
            output = result.get('output', '')
            error = result.get('error', '')
            
            # Only analyze if there's an error OR we have problem context to validate against
            if not has_error and not problem_context:
                return None  # Don't analyze successful code without knowing what it should do
            
            prompt = f"""Analyze this code execution:

                    Code: {code[:500]}
                    Problem Context: {problem_context or 'General coding task'}
                    Execution Success: {result.get('success', True)}
                    Output: {output[:300] if output else 'No output'}
                    Error: {error[:300] if error else 'No error'}

                    Instructions:
                    - If syntax/runtime errors: suggest the fix:
                    * "Fix: [issue]"
                    - If code runs but gives incorrect output (i.e., doesn’t meet requirements):
                    * "Output: [why the output is incorrect, and what it should be]"
                    - If code works but can be optimize, suggest optimization, for example :
                    * Nested loops for searching/finding pairs → "Optimize: Use hash map"
                    * Linear search in loops → "Optimize: Use hash map/set"
                    * O(n²) when O(n) possible → "Optimize: Better algorithm"
                    - Only return "correct" if code is both working AND reasonably efficient

                    Provide analysis (max 150 characters):
                    - Error: "Fix: [issue]"
                    - Wrong output: "Output: [issue]" 
                    - Inefficient: "Optimize: [suggestion]"
                    - Good code: "correct"

                    Examples: "Fix: Missing )", "output does not match the requirement, fix: ...", "Optimize: Use hash map", "correct"
                    """
            print(f"🔍 Panel analysis prompt: {prompt}...")  # Log first 200 chars

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )
            
            analysis = response.choices[0].message.content.strip()

            print(f"🔍 Panel analysis response: {analysis}")
            
            if analysis.lower() == "correct":
                return {
                    "message": "✅ Code works correctly",
                    "type": "success",
                }
            
            # Determine type based on content
            if analysis.lower().startswith("fix:"):
                analysis_type = "error"
            elif analysis.lower().startswith("optimize:"):
                analysis_type = "optimization" 
            elif analysis.lower().startswith("output:"):
                analysis_type = "warning"
            else:
                analysis_type = "error" if has_error else "warning"
            
            return {
                "message": analysis,  # Match the prompt limit
                "type": analysis_type,
            }
            
        except Exception as e:
            logging.error(f"Error in panel analysis: {e}")
            return None

    def analyze_code_execution_async_optimized(self, code: str, execution_result: Dict[str, Any], 
                                                   problem_context: Optional[str] = None, 
                                                   room_id: Optional[str] = None) -> Dict[str, Any]:
        """OPTIMIZED: Single AI call for analysis + help message generation"""
        if not self.client:
            return {"needs_help": False, "help_message": ""}
            
        try:
            # Get attempt count for context
            attempts = self.execution_attempts.get(room_id, 1) if room_id else 1
            
            # OPTIMIZATION: Include problem context but keep prompt concise
            prompt = f"""Analyze code execution for correctness:

                        Code: {code}
                        Problem: {problem_context or 'General coding task'}
                        Success: {execution_result.get('success', False)}
                        Output: {execution_result.get('output', '')}
                        Error: {execution_result.get('error', '')}
                        Attempt: {attempts}

                        Check: Does code solve the problem correctly? Any errors?

                        JSON response:
                        {{"needs_help": boolean, "is_correct": boolean, "help_message": "brief help (max 25 words) or empty if correct"}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,  # Slightly higher for problem-aware analysis
                temperature=0.3  # Very low for consistency
            )
            
            return self._parse_execution_analysis_fast(response.choices[0].message.content.strip())
            
        except Exception as e:
            logging.error(f"Error in optimized analysis: {e}")
            return {"needs_help": True, "is_correct": False, "help_message": "Need help? 🐛"}

    def _parse_execution_analysis_fast(self, analysis_text: str) -> Dict[str, Any]:
        """Fast parser for optimized execution analysis"""
        try:
            # Try to extract JSON
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = analysis_text[json_start:json_end]
                return json.loads(json_str)
            else:
                # Quick fallback
                return {
                    "needs_help": True,
                    "is_correct": False,
                    "help_message": "Need help? 🤖"
                }
                
        except Exception:
            return {
                "needs_help": True,
                "is_correct": False,
                "help_message": "Having trouble? 🐛"
            }

    def start_panel_analysis(self, room_id: str, code: str, result: dict, conversation_history):
        """Start non-blocking AI analysis for execution panel"""
        try:
            # Store execution results in conversation context for later reference
            if room_id not in conversation_history:
                from .ai_models import ConversationContext
                conversation_history[room_id] = ConversationContext(
                    messages=[],
                    room_id=room_id
                )
            
            context = conversation_history[room_id]
            context.last_execution_code = code
            context.last_execution_output = result.get('output', '')
            context.last_execution_error = result.get('error', '')
            context.last_execution_success = result.get('success', True)
            context.last_execution_time = datetime.now()
            
            # Get problem context from conversation history
            problem_context = ""
            if context.problem_description or context.problem_title:
                problem_context = context.problem_description or context.problem_title
            else:
                # If no explicit problem, look for recent problem-related messages
                recent_messages = context.messages[-10:] if context.messages else []
                for msg in reversed(recent_messages):
                    content = msg.content.lower()
                    if any(word in content for word in ['problem', 'task', 'write', 'function', 'create']):
                        problem_context = msg.content[:200]
                        break
            
            # Use socketio background task for non-blocking execution
            if self.socketio:
                self.socketio.start_background_task(
                    self._run_panel_analysis, room_id, code, result, problem_context
                )
                print(f"🔍 Started panel analysis for room {room_id}")
                
        except Exception as e:
            logging.error(f"Error starting panel analysis: {e}")

    def _run_panel_analysis(self, room_id: str, code: str, result: dict, problem_context: str):
        """Background task for panel analysis"""
        try:
            analysis = self.analyze_execution_for_panel(code, result, problem_context)
            
            if analysis:
                print(f"📊 Panel analysis: {analysis['message']}")
                self.socketio.emit('execution_analysis', {
                    'analysis': analysis,
                    'room_id': room_id
                }, room=room_id, namespace='/ws')
                
        except Exception as e:
            logging.error(f"Error in panel analysis background task: {e}")

    def handle_code_execution_validation_optimized(self, room_id: str, code: str, 
                                                        execution_result: Dict[str, Any],
                                                        conversation_history, send_help_callback) -> None:
        """OPTIMIZED: Single AI call, faster message delivery"""
        try:
            # Get current problem context
            context = conversation_history.get(room_id)
            if not context:
                from .ai_models import ConversationContext
                context = ConversationContext([], room_id)
                conversation_history[room_id] = context
                
            problem_context = context.problem_description or context.problem_title
            
            # OPTIMIZATION: Single AI call that analyzes AND generates help message
            analysis = self.analyze_code_execution_async_optimized(
                code, execution_result, problem_context, room_id
            )
            
            print(f"🔍 Optimized analysis result: {analysis}")

            # Track attempts for graduated help
            if room_id not in self.execution_attempts:
                self.execution_attempts[room_id] = 0
                
            # Only offer help if needed and not correct
            if analysis.get('needs_help', False) and not analysis.get('is_correct', True):
                self.execution_attempts[room_id] += 1
                
                # OPTIMIZATION: Skip the wait and activity check for faster response
                help_message = analysis.get('help_message', '')
                if help_message.strip():
                    # Send help message via callback
                    send_help_callback(room_id, help_message)
            else:
                # Reset attempts if code is correct
                self.execution_attempts[room_id] = 0
                
        except Exception as e:
            logging.error(f"Error in optimized code execution validation: {e}")

    def start_execution_validation_optimized(self, room_id: str, code: str, execution_result: Dict[str, Any],
                                           conversation_history, send_help_callback) -> None:
        """OPTIMIZED: Start validation with minimal overhead"""
        try:
            if self.socketio:
                # Use the optimized validation method
                self.socketio.start_background_task(
                    self._run_async_validation_optimized, room_id, code, execution_result,
                    conversation_history, send_help_callback
                )
                print(f"🚀 Started optimized AI validation for room {room_id}")
        except Exception as e:
            logging.error(f"Error starting optimized validation: {e}")

    def _run_async_validation_optimized(self, room_id: str, code: str, execution_result: Dict[str, Any],
                                      conversation_history, send_help_callback) -> None:
        """OPTIMIZED: Direct execution without event loop"""
        try:
            # Run the validation directly
            self.handle_code_execution_validation_optimized(
                room_id, code, execution_result, conversation_history, send_help_callback
            )
            
        except Exception as e:
            logging.error(f"Error in optimized validation thread: {e}")

    def reset_execution_tracking(self, room_id: str):
        """Reset execution tracking for a room"""
        if room_id in self.execution_attempts:
            del self.execution_attempts[room_id]
        if room_id in self.validation_tasks:
            del self.validation_tasks[room_id]
