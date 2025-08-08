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
        
        # Simplified system prompt for better formatting
        self.system_prompt = """You are Tara, a warm physiotherapist. Keep responses VERY SHORT (max 50 words).
Use this EXACT format:
- Opening statement (empathetic)
- Blank line
- Bullet points (each on new line, start with •)
- Blank line  
- Closing question

NEVER use paragraphs. Always use bullet points."""
    
    def format_response(self, text: str) -> str:
        """Helper to ensure proper formatting"""
        # Clean up the response
        text = text.strip()
        
        # Ensure bullet points are on new lines
        text = text.replace('• ', '\n• ')
        text = text.replace('- ', '\n• ')
        
        # Remove double newlines
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        
        # Ensure questions end with proper spacing
        text = text.replace('?', '?\n')
        
        # Clean up any extra whitespace
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def start_assessment(self, user_name: str = "there") -> Dict:
        """Start assessment with fixed greeting"""
        
        if self.assessment_state["greeting_sent"]:
            return {
                "message": "I'm still here to help!\n\nWhat area is bothering you?",
                "state": "awaiting_problem_areas"
            }
        
        self.assessment_state["greeting_sent"] = True
        self.assessment_state["session_started"] = True
        
        greeting = "Hello beautiful soul! I'm Tara, your physiotherapist for the day.\n\n• Tell me where it hurts\n• I'm here to help you feel better\n\nWhat area is giving you trouble today?"
        
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
        
        self.assessment_state["user_concerns"] = user_message
        pain_area = self._detect_primary_pain_area(user_message.lower())
        
        if not pain_area:
            response = """I want to understand where you're hurting.

• Neck, shoulders, or jaw?
• Lower back or hips?
• Knees or ankles?

What's bothering you most, beautiful soul?"""
            return {
                "message": response,
                "recommended_tests": []
            }
        
        # Generate formatted response for specific pain area
        response = self._generate_pain_response(pain_area, user_message)
        
        # Get recommended tests
        recommended_tests = self._get_recommended_tests([pain_area])
        self.assessment_state["recommended_tests"] = recommended_tests
        
        # Add test prompt
        test_message = "\n\nLet's do some movement tests:\n\n• These help me understand what's happening\n• Ready to start your assessment?"
        
        full_response = response + test_message
        
        return {
            "message": full_response,
            "recommended_tests": [self._format_test_for_frontend(test) for test in recommended_tests]
        }
    
    def _generate_pain_response(self, pain_area: str, user_message: str) -> str:
        """Generate pain-specific response with proper formatting"""
        
        # Pain-specific responses (keep them short and formatted)
        pain_responses = {
            "neck": """I'm so sorry your neck hurts!

• Any shoulder tightness too?
• Past neck injuries?
• Long hours at computer?

What makes it feel worse?""",
            
            "shoulder": """Oh no, shoulder pain is tough!

• Which shoulder hurts?
• Pain when lifting arms?
• Any neck stiffness?

When did this start?""",
            
            "lower_back": """Lower back pain is so common!

• Sharp or dull pain?
• Worse when sitting/standing?
• Any leg numbness?

What triggered this?""",
            
            "knee": """Knee pain can really limit you!

• Which knee bothers you?
• Pain when walking/stairs?
• Any swelling?

How long has this been happening?""",
            
            "ankle": """Ankle pain affects everything!

• Recent injury or twist?
• Swelling or stiffness?
• Pain when walking?

What activities hurt most?""",
            
            "jaw": """Jaw pain is so uncomfortable!

• Clicking or popping?
• Headaches too?
• Stress or teeth grinding?

When is it worst?"""
        }
        
        # Return the specific response or generate one
        if pain_area in pain_responses:
            return pain_responses[pain_area]
        
        # Fallback if area not found
        return f"""I understand you have {pain_area} pain.

• How severe is it?
• What triggers it?
• Any other symptoms?

Tell me more, beautiful soul."""
    
    def _detect_primary_pain_area(self, message: str) -> Optional[str]:
        """Detect primary pain area from user message"""
        pain_keywords = {
            "neck": ["neck", "cervical"],
            "shoulder": ["shoulder", "arm"],
            "lower_back": ["back", "lower back", "lumbar", "spine"],  
            "knee": ["knee", "kneecap", "leg"],
            "ankle": ["ankle", "foot", "heel"],
            "jaw": ["jaw", "tmj", "face", "mouth"]
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
                    "explanation": """I couldn't capture your movement!

• Make sure you're well-lit
• Stay in camera view
• Let's try again

Don't worry, we'll get it!"""
                }
            
            # Validate keypoints
            for kp in keypoints:
                if 'x' not in kp or 'y' not in kp:
                    return {
                        "success": False,
                        "explanation": """Let's try again, dear!

• Camera didn't capture all data
• Make sure whole body visible
• Take your time

We'll get this right together!"""
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
            
            # Generate simple encouraging feedback
            if raw_results.get("pass", True):
                explanation = f"""Great job completing the test!

• Your {area} mobility looks good
• Keep up the movement

Ready for the next test?"""
            else:
                explanation = f"""Test complete! I see what's happening.

• Your {area} needs some work
• We'll address this in your routine

Let's continue, beautiful soul!"""
            
            return {
                "success": True,
                "explanation": explanation,
                "results": raw_results
            }
            
        except Exception as e:
            print(f"Error analyzing movement: {e}")
            return {
                "success": False,
                "explanation": """Technical hiccup!

• Don't worry, it happens
• Let's try again
• I'm still here for you

Ready when you are!"""
            }
    
    def generate_routine(self) -> Dict:
        """Generate personalized routine with Tara's caring approach"""
        
        # Analyze all test results
        problem_areas = []
        for test_id, results in self.assessment_state["test_results"].items():
            if not results.get("pass", True):
                area, test_type = test_id.split('_', 1)
                problem_areas.append((area, test_type, results))
        
        # Generate simple routine message
        if problem_areas:
            areas_text = ", ".join([area for area, _, _ in problem_areas])
            explanation = f"""Your personalized routine is ready!

• Targets your {areas_text} issues
• Gentle progressive exercises
• Do daily for best results

You've got this, beautiful soul!"""
        else:
            explanation = """Great news! Your mobility is good!

• Maintenance routine created
• Keep your body moving
• Prevent future issues

Stay consistent, you're doing amazing!"""
        
        exercises = self._generate_targeted_exercises(problem_areas)
        
        return {
            "explanation": explanation,
            "exercises": exercises
        }
    
    def _generate_targeted_exercises(self, problem_areas: List) -> List[Dict]:
        """Generate exercises targeting specific problem areas"""
        exercises = []
        
        # Add targeted exercises based on problem areas
        area_exercises = {
            "neck": {
                "name": "Gentle Neck Stretches",
                "duration": "3 minutes",
                "description": "Slowly stretch in all directions",
                "sets": "Hold 30 seconds each"
            },
            "shoulder": {
                "name": "Shoulder Rolls & Stretches",
                "duration": "4 minutes",
                "description": "Improve shoulder mobility",
                "sets": "10 rolls, 4 stretches"
            },
            "lower_back": {
                "name": "Cat-Cow Stretches",
                "duration": "5 minutes",
                "description": "Mobilize your spine gently",
                "sets": "15 repetitions"
            },
            "knee": {
                "name": "Knee Strengthening",
                "duration": "5 minutes",
                "description": "Build knee stability",
                "sets": "10 reps each leg"
            },
            "ankle": {
                "name": "Ankle Circles & Flexes",
                "duration": "3 minutes",
                "description": "Improve ankle mobility",
                "sets": "15 circles each direction"
            },
            "jaw": {
                "name": "Jaw Release Exercises",
                "duration": "3 minutes",
                "description": "Relieve jaw tension",
                "sets": "5 gentle stretches"
            }
        }
        
        # Add exercises for identified problem areas
        added_areas = set()
        for area, _, _ in problem_areas:
            if area in area_exercises and area not in added_areas:
                exercises.append(area_exercises[area])
                added_areas.add(area)
        
        # Add general exercise if no specific problems or as addition
        if not exercises or len(exercises) < 3:
            exercises.append({
                "name": "Full Body Flow",
                "duration": "5 minutes",
                "description": "Gentle movement for overall health",
                "sets": "1 complete flow"
            })
        
        return exercises[:3]  # Limit to 3 exercises to keep it manageable