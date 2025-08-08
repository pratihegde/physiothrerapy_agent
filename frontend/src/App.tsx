import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { CameraTest } from './components/CameraTest';
import { physiotherapyAPI } from './api';
import { Message, Test, Routine } from './types';
import { Send, Camera, Youtube, CheckCircle } from 'lucide-react';

function App() {
  const [sessionId] = useState(`session_${Date.now()}`);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentTest, setCurrentTest] = useState<Test | null>(null);
  const [completedTests, setCompletedTests] = useState<string[]>([]);
  const [routine, setRoutine] = useState<Routine | null>(null);
  const [assessmentState, setAssessmentState] = useState<'chat' | 'testing' | 'complete'>('chat');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    startAssessment();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startAssessment = async () => {
    try {
      setIsLoading(true);
      const response = await physiotherapyAPI.startAssessment(sessionId, 'there');
      addMessage('agent', response.message);
    } catch (error) {
      console.error('Error starting assessment:', error);
      addMessage('agent', 'Sorry, there was an error starting the assessment. Please refresh and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const addMessage = (type: 'user' | 'agent', content: string, tests?: Test[]) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      type,
      content,
      tests
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue;
    setInputValue('');
    addMessage('user', userMessage);
    setIsLoading(true);

    try {
      if (assessmentState === 'chat') {
        const response = await physiotherapyAPI.submitProblemAreas(sessionId, userMessage);
        addMessage('agent', response.message, response.recommended_tests);
        if (response.recommended_tests && response.recommended_tests.length > 0) {
          setAssessmentState('testing');
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      addMessage('agent', 'Sorry, there was an error processing your message.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartTest = (test: Test) => {
    setCurrentTest(test);
  };

  const handleTestComplete = async (keypoints: any[]) => {
    if (!currentTest) return;

    setIsLoading(true);
    try {
      const response = await physiotherapyAPI.analyzeMovement(sessionId, currentTest.id, keypoints);
      addMessage('agent', response.explanation);
      setCompletedTests(prev => [...prev, currentTest.id]);
      setCurrentTest(null);

      // Check if all tests are complete
      const allTestsInLastMessage = messages[messages.length - 1]?.tests || [];
      if (completedTests.length + 1 >= allTestsInLastMessage.length) {
        setTimeout(() => generateRoutine(), 2000);
      }
    } catch (error) {
      console.error('Error analyzing movement:', error);
      addMessage('agent', 'Sorry, there was an error analyzing your movement.');
    } finally {
      setIsLoading(false);
    }
  };

  const generateRoutine = async () => {
    setIsLoading(true);
    addMessage('agent', 'Great job completing all the tests! Let me create your personalized mobility routine...');

    try {
      const response = await physiotherapyAPI.generateRoutine(sessionId);
      setRoutine(response);
      setAssessmentState('complete');
      addMessage('agent', 'Your personalized mobility routine is ready! Scroll down to see your exercises.');
    } catch (error) {
      console.error('Error generating routine:', error);
      addMessage('agent', 'Sorry, there was an error generating your routine.');
    } finally {
      setIsLoading(false);
    }
  };

  const renderTests = (tests: Test[]) => {
    return tests.map(test => (
      <div key={test.id} className="test-card">
        <h3>{test.name}</h3>
        <p>{test.description}</p>
        <div className="test-buttons">
          <button 
            className="btn-primary"
            onClick={() => handleStartTest(test)}
            disabled={completedTests.includes(test.id)}
          >
            {completedTests.includes(test.id) ? (
              <>
                <CheckCircle size={16} />
                Completed
              </>
            ) : (
              <>
                <Camera size={16} />
                Start Test
              </>
            )}
          </button>
          <a 
            href={test.youtube_link} 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn-secondary"
          >
            <Youtube size={16} />
            Tutorial
          </a>
        </div>
      </div>
    ));
  };

  return (
    <div className="App">
      <div className="container">
        <h1 style={{ textAlign: 'center', marginBottom: '30px' }}>
          AI Physiotherapy Assessment
        </h1>

        <div className="chat-container">
          <div className="chat-header">
            <h2>Movement Assessment Chat</h2>
          </div>

          <div className="chat-messages">
            {messages.map(message => (
              <div key={message.id}>
                <div className={`message ${message.type}`}>
                  {message.content}
                </div>
                {message.tests && (
                  <div style={{ marginTop: '10px' }}>
                    {renderTests(message.tests)}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="loading">
                <div className="spinner"></div>
                <span>Thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Describe your mobility issues or pain areas..."
              disabled={isLoading || assessmentState !== 'chat'}
            />
            <button 
              onClick={handleSendMessage} 
              disabled={isLoading || !inputValue.trim() || assessmentState !== 'chat'}
            >
              <Send size={20} />
              Send
            </button>
          </div>
        </div>

        {routine && (
          <div className="routine-container">
            <h2>Your Personalized Mobility Routine</h2>
            <p style={{ marginBottom: '20px' }}>{routine.explanation}</p>
            
            <h3>Exercises:</h3>
            {routine.exercises.map((exercise, index) => (
              <div key={index} className="exercise-card">
                <h4>{index + 1}. {exercise.name}</h4>
                <p>{exercise.description}</p>
                <div className="exercise-details">
                  {exercise.sets && <span>Sets: {exercise.sets}</span>}
                  {exercise.reps && <span>Reps: {exercise.reps}</span>}
                  {exercise.duration && <span>Duration: {exercise.duration}</span>}
                  <span>Target: {exercise.target}</span>
                  <span>Level: {exercise.difficulty}</span>
                </div>
              </div>
            ))}
            
            <div style={{ marginTop: '20px', padding: '16px', background: '#e0e7ff', borderRadius: '8px' }}>
              <h4>Schedule:</h4>
              <p>{routine.schedule}</p>
            </div>
          </div>
        )}
      </div>

      {currentTest && (
        <CameraTest
          test={currentTest}
          onComplete={handleTestComplete}
          onClose={() => setCurrentTest(null)}
        />
      )}
    </div>
  );
}

export default App;