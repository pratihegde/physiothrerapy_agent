from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
import json
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from mobility_tests import MOBILITY_TESTS
from movenet_analyzer import MoveNetAnalyzer

load_dotenv()

class PhysiotherapyAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-3.5-turbo",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.memory = ConversationBufferMemory(return_messages=True)
        self.analyzer = MoveNetAnalyzer()
        self.assessment_state = {
            "session_started": False,
            "greeting_sent": False,
            "completed_tests": [],
            "problem_areas": [],
            "test_results": {}
        }
        
        # Load exercises
        with open('exercises.json', 'r') as f:
            self.exercises = json.load(f)
        
        # Define Tara's personality in system prompt
        self.system_prompt = """You are Tara, a warm and caring physiotherapist. 

PERSONALITY:
- Address users as "beautiful soul" or other caring terms
- Be genuinely empathetic about their pain
- Use bullet points with proper line breaks for all responses
- Keep responses short and concise (under 100 words)
- Ask about connected body parts and past injuries

FORMATTING RULES (CRITICAL):
- ALWAYS use bullet points with line breaks like this:
  • First point
  • Second point  
  • Third point
- NEVER write long paragraphs
- Keep each bullet point short (max 10 words)
- Always end with a caring question

EXAMPLE RESPONSE FORMAT:
"I'm so sorry your neck hurts!

• Do you have shoulder tightness too?
• Any past neck injuries?
• Long hours at computer/phone?

What makes it feel worse, beautiful soul?"
"""
    
    def start_assessment(self, user_name: str = "there") -> Dict:
        """Start assessment with fixed greeting to prevent duplicates"""
        
        # Prevent duplicate greetings
        if self.assessment_state["greeting_sent"]:
            return {
                "message": "I'm still here to help! What area is bothering you?",
                "state": "awaiting_problem_areas"
            }
        
        # Mark greeting as sent
        self.assessment_state["greeting_sent"] = True
        self.assessment_state["session_started"] = True
        
        # Fixed greeting message (not LLM generated to prevent duplicates)
        greeting = """Hello beautiful soul! I'm Tara, your physiotherapist for the day.

• Tell me where it hurts
• I'm here to help you feel better

What area is giving you trouble today?"""
        
        self.memory.save_context(
            {"input": f"Start assessment for {user_name}"}, 
            {"output": greeting}
        )
        
        return {
            "message": greeting,
            "state": "awaiting_problem_areas"
        }
    
    def process_problem_areas(self, user_message: str) -> Dict:
        """Process user's problem areas with proper formatting"""
        
        # Update state
        self.assessment_state["user_concerns"] = user_message
        
        # Detect pain area
        pain_area = self._detect_primary_pain_area(user_message.lower())
        
        if not pain_area:
            return {
                "message": """I want to understand exactly where you're hurting.

• Could you tell me the specific area?
• Main areas: neck, shoulders, lower back, knees, ankles, or jaw

What's bothering you most?""",
                "recommended_tests": []
            }
        
        # Get empathetic response using prompt template
        response_template = PromptTemplate(
            input_variables=["pain_area", "user_message"],
            template="""User said they have {pain_area} pain: "{user_message}"

Respond as Tara with empathy and follow-up questions.

MUST follow this exact format:
Line 1: Empathetic statement about their {pain_area} pain
Line 2: Empty line
Line 3-5: Exactly 3 bullet points asking about:
• Connected body parts  
• Past injuries
• Activity that causes it
Line 6: Empty line  
Line 7: Caring follow-up question

Keep each bullet point under 8 words. Be warm but concise."""
        )
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=response_template.format(
                pain_area=pain_area,
                user_message=user_message
            ))
        ]
        
        response = self.llm.invoke(messages)
        empathetic_response = response.content
        
        # Get recommended tests
        recommended_tests = self._get_recommended_tests([pain_area])
        self.assessment_state["recommended_tests"] = recommended_tests
        
        # Add test message
        test_message = """

Based on what you've shared, let's do some movement tests:

• These will help me understand what's happening
• Ready to start your assessment?"""

        full_response = empathetic_response + test_message
        
        return {
            "message": full_response,
            "recommended_tests": [self._format_test_for_frontend(test) for test in recommended_tests]
        }
    
    def _detect_primary_pain_area(self, message: str) -> Optional[str]:
        """Detect primary pain area from user message"""
        pain_keywords = {
            "neck": ["neck", "cervical"],
            "shoulder": ["shoulder", "arm"],
            "lower_back": ["back", "lower back", "lumbar"],  
            "knee": ["knee", "kneecap"],
            "ankle": ["ankle", "foot"],
            "jaw": ["jaw", "tmj", "face"]
        }
        
        for area, keywords in pain_keywords.items():
            if any(keyword in message for keyword in keywords):
                return area
        
        return None
    
    def _get_recommended_tests(self, pain_areas: List[str]) -> List[Dict]:
        """Get test recommendations based on pain areas"""
        recommended = []
        
        for area in pain_areas:
            if area in MOBILITY_TESTS:
                area_tests = MOBILITY_TESTS[area]
                for test_type, test_info in area_tests.items():
                    test_id = f"{area}_{test_type}"
                    recommended.append({
                        "id": test_id,
                        "name": test_info['name'],
                        "description": test_info['description'],
                        "youtube_link": test_info['youtube_link']
                    })
        
        return recommended
    
    def _format_test_for_frontend(self, test: Dict) -> Dict:
        """Format test recommendation for frontend"""
        return test
    
    def analyze_movenet_results(self, test_id: str, keypoints: List[Dict]) -> Dict:
        """Analyze movement test results with Tara's encouraging tone"""
        try:
            if not keypoints:
                return {
                    "success": False,
                    "explanation": """I couldn't capture your movement properly!

• Don't worry - this happens sometimes
• Make sure you're well-lit and visible
• Let's try that test again
• I'm here to support you through this"""
                }
            
            # Validate keypoints
            for kp in keypoints:
                if 'x' not in kp or 'y' not in kp:
                    return {
                        "success": False,
                        "explanation": """Let's try that movement test again, dear!

• The camera didn't capture all data
• Make sure your whole body is visible
• Take your time - no rush
• We'll get this right together!"""
                    }
            
            # Analyze movement
            area, test_type = test_id.split('_', 1)
            
            analysis_method = f"analyze_{test_type}"
            if hasattr(self.analyzer, analysis_method):
                raw_results = getattr(self.analyzer, analysis_method)(keypoints)
            else:
                raw_results = {"pass": True, "details": "Test completed"}
            
            # Store results
            self.assessment_state["test_results"][test_id] = raw_results
            self.assessment_state["completed_tests"].append(test_id)
            
            # Generate encouraging explanation using prompt template
            explanation_template = PromptTemplate(
                input_variables=["test_name", "results", "area"],
                template="""User completed {test_name} for {area}.
Results: {results}

As Tara, give encouraging feedback in this format:
Line 1: Positive statement about completing the test
Line 2: Empty line
Line 3-4: 2 bullet points about what this reveals
Line 5: Empty line
Line 6: Encouraging statement about their progress

Keep it under 60 words total. Be warm and supportive."""
            )
            
            test_info = MOBILITY_TESTS[area][test_type]
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=explanation_template.format(
                    test_name=test_info['name'],
                    results=json.dumps(raw_results, indent=2),
                    area=area
                ))
            ]
            
            response = self.llm.invoke(messages)
            explanation = response.content
            
            return {
                "success": True,
                "explanation": explanation,
                "results": raw_results
            }
            
        except Exception as e:
            print(f"Error analyzing movement: {e}")
            return {
                "success": False,
                "explanation": """Something went wrong with analyzing your movement.

• Don't worry - technical hiccups happen!
• Let's try that test again when ready
• I'm still here to help you
• Your progress matters more than perfect data"""
            }
    
    def generate_routine(self) -> Dict:
        """Generate personalized routine with Tara's caring approach"""
        
        # Analyze all test results
        problem_areas = []
        for test_id, results in self.assessment_state["test_results"].items():
            if not results.get("pass", True):
                area, test_type = test_id.split('_', 1)
                problem_areas.append((area, test_type, results))
        
        routine_template = PromptTemplate(
            input_variables=["problem_areas", "user_concerns"],
            template="""Create personalized routine for user with these issues:
Problem areas: {problem_areas}
Original concerns: {user_concerns}

As Tara, respond in this format:
Line 1: Encouraging statement about their personalized routine
Line 2: Empty line  
Line 3-5: 3 bullet points about what the routine targets
Line 6: Empty line
Line 7: Motivational closing statement

Keep under 80 words total. Be warm and caring."""
        )
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=routine_template.format(
                problem_areas=str(problem_areas),
                user_concerns=self.assessment_state.get('user_concerns', 'General mobility')
            ))
        ]
        
        response = self.llm.invoke(messages)
        
        exercises = self._generate_targeted_exercises(problem_areas)
        
        return {
            "explanation": response.content,
            "exercises": exercises
        }
    
    def _generate_targeted_exercises(self, problem_areas: List) -> List[Dict]:
        """Generate exercises targeting specific problem areas"""
        exercises = []
        
        for area, test_type, results in problem_areas:
            if area == "neck":
                exercises.extend([
                    {
                        "name": "Gentle Neck Stretches",
                        "duration": "3 minutes",
                        "description": "Slowly stretch in all directions",
                        "sets": "Hold each direction 30 seconds"
                    }
                ])
            elif area == "shoulder":
                exercises.extend([
                    {
                        "name": "Cross-Body Shoulder Stretch",
                        "duration": "2 minutes",
                        "description": "Gentle stretch to improve mobility", 
                        "sets": "4 holds per arm"
                    }
                ])
            # Add more targeted exercises for other areas
            
        # Add default exercises if none specific
        if not exercises:
            exercises = [
                {
                    "name": "Daily Movement Flow",
                    "duration": "5 minutes",
                    "description": "Gentle full-body movement",
                    "sets": "1 flow"
                }
            ]
            
        return exercises