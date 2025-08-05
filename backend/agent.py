from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, SystemMessage
import json
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT
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
            "completed_tests": [],
            "problem_areas": [],
            "test_results": {}
        }
        
        # Load exercises
        with open('exercises.json', 'r') as f:
            self.exercises = json.load(f)
    
    def start_assessment(self, user_name: str = "there") -> Dict:
        """Initial greeting and assessment start"""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Start a mobility assessment for {user_name}. Ask about their problem areas.")
        ]
        
        response = self.llm.invoke(messages)
        self.memory.save_context(
            {"input": f"Start assessment for {user_name}"}, 
            {"output": response.content}
        )
        
        return {
            "message": response.content,
            "state": "awaiting_problem_areas"
        }
    
    def process_problem_areas(self, user_message: str) -> Dict:
        """Process user's problem areas and recommend tests"""
        # Update state
        self.assessment_state["user_concerns"] = user_message
        
        # Get LLM to identify problem areas
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"""
            User said: "{user_message}"
            
            Based on this, which body areas should we test? Choose from:
            - shoulder (for neck, shoulder, upper back issues)
            - hip (for hip, lower back, leg issues)  
            - ankle (for ankle, calf, foot issues)
            - spine (for back, posture issues)
            - functional (for general movement quality)
            
            Recommend 3-4 specific tests from our available tests.
            """)
        ]
        
        response = self.llm.invoke(messages)
        
        # For MVP, let's recommend based on keywords
        recommended_tests = self._recommend_tests_from_message(user_message)
        
        self.memory.save_context(
            {"input": user_message},
            {"output": response.content}
        )
        
        return {
            "message": response.content,
            "recommended_tests": recommended_tests,
            "state": "ready_for_testing"
        }
    
    def _recommend_tests_from_message(self, message: str) -> List[Dict]:
        """Simple keyword-based test recommendation"""
        message_lower = message.lower()
        tests = []
        
        # Keyword mapping
        if any(word in message_lower for word in ["shoulder", "neck", "upper back", "reach"]):
            tests.extend([
                {"area": "shoulder", "test": "flexion"},
                {"area": "shoulder", "test": "external_rotation"}
            ])
        
        if any(word in message_lower for word in ["hip", "lower back", "squat", "sit"]):
            tests.extend([
                {"area": "hip", "test": "flexion"},
                {"area": "hip", "test": "internal_rotation"}
            ])
        
        if any(word in message_lower for word in ["ankle", "calf", "foot"]):
            tests.append({"area": "ankle", "test": "dorsiflexion"})
        
        if any(word in message_lower for word in ["back", "posture", "spine"]):
            tests.append({"area": "spine", "test": "flexion"})
        
        # Always add functional test
        tests.append({"area": "functional", "test": "overhead_squat"})
        
        # Get full test details
        detailed_tests = []
        for test in tests[:4]:  # Limit to 4 tests
            test_info = MOBILITY_TESTS[test["area"]][test["test"]]
            detailed_tests.append({
                "id": f"{test['area']}_{test['test']}",
                "name": test_info["name"],
                "description": test_info["description"],
                "youtube_link": test_info["youtube_link"]
            })
        
        return detailed_tests
    
    def analyze_movenet_results(self, test_id: str, keypoints: List[Dict]) -> Dict:
        """Analyze MoveNet keypoints for specific test"""
        try:
            # ADD: Validate keypoints format
            if not keypoints or len(keypoints) != 17:  # MoveNet has 17 keypoints
                return {
                    "success": False,
                    "explanation": "Invalid keypoint data received. Please try again."
                }
            
            # ADD: Ensure all keypoints have required fields
            for kp in keypoints:
                if 'x' not in kp or 'y' not in kp:
                    return {
                        "success": False,
                        "explanation": "Incomplete keypoint data. Please try again."
                    }
            
            # Your existing code continues here...
            area, test_type = test_id.split('_', 1)
            
            # Use MoveNetAnalyzer
            analysis_method = f"analyze_{test_type}"
            if hasattr(self.analyzer, analysis_method):
                raw_results = getattr(self.analyzer, analysis_method)(keypoints)
            else:
                raw_results = {"pass": True, "details": "Test completed"}
            
            # Store results
            self.assessment_state["test_results"][test_id] = raw_results
            self.assessment_state["completed_tests"].append(test_id)
            
            # ... rest of your existing code
            
        except Exception as e:
            # ADD: Better error handling
            print(f"Error analyzing movement: {e}")  # For debugging
            return {
                "success": False,
                "explanation": "Error analyzing movement. Please try again."
            }
    
    def _generate_test_explanation(self, test_id: str, results: Dict) -> str:
        """Generate user-friendly explanation of test results"""
        area, test_type = test_id.split('_', 1)
        test_info = MOBILITY_TESTS[area][test_type]
        
        prompt = f"""
        The user just completed the {test_info['name']}.
        Results: {json.dumps(results, indent=2)}
        Pass criteria: {test_info['pass_criteria']}
        
        Provide a brief, encouraging explanation of what this means for their mobility.
        If they didn't pass, explain why this matters and what it might indicate.
        Keep it conversational and supportive.
        """
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def _get_next_test(self, completed_test_id: str) -> Optional[Dict]:
        """Get next test in sequence"""
        # This would be more sophisticated in production
        # For now, just return None (frontend handles flow)
        return None
    
    def generate_routine(self) -> Dict:
        """Generate personalized routine based on all test results"""
        # Summarize findings
        findings_summary = self._summarize_findings()
        
        # Get exercise recommendations
        prompt = f"""
        Based on these mobility test results:
        {findings_summary}
        
        User's original concerns: {self.assessment_state.get('user_concerns', 'General mobility')}
        
        Create a personalized mobility routine selecting from these exercises:
        {json.dumps(self.exercises, indent=2)}
        
        Select 5-7 exercises that specifically address their limitations.
        Explain why each exercise was chosen.
        Provide a weekly schedule.
        """
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        # Structure the routine
        routine = {
            "explanation": response.content,
            "exercises": self._extract_recommended_exercises(response.content),
            "schedule": "3-4 times per week, 15-20 minutes per session",
            "test_results_summary": findings_summary
        }
        
        return routine
    
    def _summarize_findings(self) -> str:
        """Summarize all test results"""
        summary_parts = []
        
        for test_id, results in self.assessment_state["test_results"].items():
            area, test_type = test_id.split('_', 1)
            test_name = MOBILITY_TESTS[area][test_type]["name"]
            
            if results.get("pass", False):
                summary_parts.append(f"✓ {test_name}: Good mobility")
            else:
                summary_parts.append(f"✗ {test_name}: Restricted - {results.get('details', 'Needs improvement')}")
        
        return "\n".join(summary_parts)
    
    def _extract_recommended_exercises(self, llm_response: str) -> List[Dict]:
        """Extract exercises mentioned in LLM response"""
        recommended = []
        
        for category, exercises in self.exercises["exercises"].items():
            for exercise in exercises:
                if exercise["name"].lower() in llm_response.lower():
                    recommended.append({
                        "category": category,
                        **exercise
                    })
        
        return recommended[:7]