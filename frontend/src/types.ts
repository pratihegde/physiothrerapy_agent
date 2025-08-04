export interface Test {
    id: string;
    name: string;
    description: string;
    youtube_link: string;
  }
  
  export interface Message {
    id: string;
    type: 'user' | 'agent';
    content: string;
    tests?: Test[];
  }
  
  export interface TestResult {
    test_id: string;
    results: any;
    explanation: string;
  }
  
  export interface Exercise {
    name: string;
    description: string;
    sets?: string;
    reps?: string;
    duration?: string;
    target: string;
    difficulty: string;
    category: string;
  }
  
  export interface Routine {
    explanation: string;
    exercises: Exercise[];
    schedule: string;
  }