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
                    {"role": "system", "content": "You are an expert code reviewer. Analyze for real errors only. Single loops through helper function results are efficient O(n). Only suggest optimization for actual nested loops (for i, for j patterns). Trust helper functions work correctly."},
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
        """Create a concise prompt for code analysis"""
        
        # Keep it simple - no verbose problem context
        
        return f"""Analyze this {language} code:
```{language}
{code}
```

Problem: {problem_context.get('title', 'Unknown') if problem_context else 'General coding'}

CRITICAL RULES:
- Trust helper functions (find_all_pairs() returns valid pairs)
- Max-finding algorithms using single loops are EFFICIENT and CORRECT
- ONLY suggest hashmap for actual nested loops (for i in range, for j in range pattern)
- Single loop iterating through function results = O(n) = EFFICIENT
- Don't flag: style, comments, missing subtasks, working algorithms

Only flag: undefined variables, syntax errors, actual logic bugs

JSON: {{"issue": {{"title": "...", "description": "...", "hint": "..."}}}}
Good code: {{"issue": {{"title": "Code looks good!", "description": "Correct and efficient.", "hint": "Well done!"}}}}"""

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
            
            prompt = f"""Code execution analysis:

Code: {code}
Problem: {problem_context or 'General coding'}
Success: {result.get('success', True)}
Output: {output if output else 'None'}
Error: {error if error else 'None'}

CRITICAL RULES:
- Trust helper functions (find_all_pairs() works correctly)
- Single loops through function results = EFFICIENT O(n)
- ONLY suggest hashmap for actual nested for loops (for i, for j pattern)
- Max-finding with single loop = CORRECT and EFFICIENT

Response (max 150 chars):
- Errors: "Fix: [issue]"
- Wrong output: "Output: [issue]"
- Actual inefficiency: "Optimize: [suggestion]"
- Working efficiently: "correct"

Examples: "Fix: Missing )", "correct", "Subtask 1: correct, subtask 2: replace nested loops with hashmap, subtask 3: ..."
"""
            print(f"🔍 Panel analysis prompt: {prompt}...")  # Log first 200 chars

            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                # max_tokens=50,
                # temperature=0.3
            )
            
            analysis = response.choices[0].message.content.strip()

            print(f"🔍 Panel analysis response: {analysis}")
            
            if analysis.lower() == "correct":
                return {
                    "message": "✅ Code works correctly",
                    "type": "success",
                }
            
            # Determine type based on content with subtask awareness
            if analysis.lower().startswith("fix:"):
                analysis_type = "error"
            elif analysis.lower().startswith("next:"):
                analysis_type = "info"  # Next subtask guidance
            elif analysis.lower().startswith("ready:"):
                analysis_type = "success"  # Ready for next step
            elif analysis.lower().startswith("output:"):
                analysis_type = "warning"  # Output mismatch
            elif analysis.lower().startswith("optimize:"):
                analysis_type = "optimization" 
            else:
                analysis_type = "error" if has_error else "warning"
            
            return {
                "message": analysis,  # Match the prompt limit
                "type": analysis_type,
            }
            
        except Exception as e:
            logging.error(f"Error in panel analysis: {e}")
            return None

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
                print(f"📊 Room ID: {room_id}")
                
                # Emit to the room (could be personal room like room123_personal_userId)
                self.socketio.emit('execution_analysis', {
                    'analysis': analysis,
                    'room_id': room_id
                }, room=room_id, namespace='/ws')
                
                # If this is a personal room, also emit to the base room
                # so the user receives the analysis regardless of which room they're connected to
                if '_personal_' in room_id:
                    base_room = room_id.split('_personal_')[0]
                    print(f"📊 Also emitting to base room: {base_room}")
                    self.socketio.emit('execution_analysis', {
                        'analysis': analysis,
                        'room_id': room_id  # Keep original room_id for context
                    }, room=base_room, namespace='/ws')
                
        except Exception as e:
            logging.error(f"Error in panel analysis background task: {e}")

    def reset_execution_tracking(self, room_id: str):
        """Reset execution tracking for a room"""
        if room_id in self.execution_attempts:
            del self.execution_attempts[room_id]
        if room_id in self.validation_tasks:
            del self.validation_tasks[room_id]
