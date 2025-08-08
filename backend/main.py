from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
import uvicorn
from agent import PhysiotherapyAgent
from mobility_tests import MOBILITY_TESTS

app = FastAPI(title="Physiotherapy Agent API")

# Configure CORS
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store sessions
agents: Dict[str, PhysiotherapyAgent] = {}

# Pydantic models
class StartAssessmentRequest(BaseModel):
    session_id: str
    user_name: Optional[str] = "there"

class ProblemAreasRequest(BaseModel):
    session_id: str
    message: str

class MoveNetAnalysisRequest(BaseModel):
    session_id: str
    test_id: str
    keypoints: List[Dict]  # MoveNet keypoints

class GenerateRoutineRequest(BaseModel):
    session_id: str

@app.get("/")
def read_root():
    return {"message": "Physiotherapy Agent API is running!"}

@app.get("/available_tests")
def get_available_tests():
    """Get all available mobility tests"""
    return {"tests": MOBILITY_TESTS}

@app.post("/start_assessment")
def start_assessment(request: StartAssessmentRequest):
    """Initialize assessment"""
    try:
        agent = agents.get(request.session_id)
        if agent is None:
            agent = PhysiotherapyAgent()
            agents[request.session_id] = agent
        response = agent.start_assessment(request.user_name)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit_problem_areas")
def submit_problem_areas(request: ProblemAreasRequest):
    """Process problem areas and get test recommendations"""
    if request.session_id not in agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        response = agents[request.session_id].process_problem_areas(request.message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_movement")
def analyze_movement(request: MoveNetAnalysisRequest):
    """Analyze MoveNet keypoints for specific test"""
    if request.session_id not in agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        results = agents[request.session_id].analyze_movenet_results(
            request.test_id, 
            request.keypoints
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_routine")
def generate_routine(request: GenerateRoutineRequest):
    """Generate personalized routine based on assessment"""
    if request.session_id not in agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        routine = agents[request.session_id].generate_routine()
        return routine
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test_details/{test_id}")
def get_test_details(test_id: str):
    """Get details for specific test including YouTube link"""
    try:
        area, test_type = test_id.split('_', 1)
        test_info = MOBILITY_TESTS[area][test_type]
        return {
            "test_id": test_id,
            "details": test_info
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Test not found")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)