import axios from 'axios';

const API_BASE = 'http://localhost:8000'; // Change to your Railway URL in production

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const physiotherapyAPI = {
  startAssessment: async (sessionId: string, userName: string = 'there') => {
    const response = await api.post('/start_assessment', { session_id: sessionId, user_name: userName });
    return response.data;
  },

  submitProblemAreas: async (sessionId: string, message: string) => {
    const response = await api.post('/submit_problem_areas', { session_id: sessionId, message });
    return response.data;
  },

  analyzeMovement: async (sessionId: string, testId: string, keypoints: any[]) => {
    const response = await api.post('/analyze_movement', { 
      session_id: sessionId, 
      test_id: testId, 
      keypoints 
    });
    return response.data;
  },

  generateRoutine: async (sessionId: string) => {
    const response = await api.post('/generate_routine', { session_id: sessionId });
    return response.data;
  },

  getTestDetails: async (testId: string) => {
    const response = await api.get(`/test_details/${testId}`);
    return response.data;
  },
};