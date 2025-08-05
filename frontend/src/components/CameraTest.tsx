import React, { useRef, useEffect, useState } from 'react';
import * as tf from '@tensorflow/tfjs';
import * as poseDetection from '@tensorflow-models/pose-detection';
import '@tensorflow/tfjs-backend-webgl';
import { Camera, Youtube, Play, RotateCcw } from 'lucide-react';

interface CameraTestProps {
  test: any;
  onComplete: (keypoints: any[]) => void;
  onClose: () => void;
}

export const CameraTest: React.FC<CameraTestProps> = ({ test, onComplete, onClose }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [detector, setDetector] = useState<poseDetection.PoseDetector | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [capturedKeypoints, setCapturedKeypoints] = useState<any[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // ADD THESE NEW STATE VARIABLES
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [detectionConfidence, setDetectionConfidence] = useState<number>(0);
  const animationFrameId = useRef<number | null>(null);

  useEffect(() => {
    const initializeTFAndCamera = async () => {
      try {
        setIsLoading(true);
        
        // Initialize TensorFlow.js
        await tf.ready();
        
        // MODIFIED: Try WebGL first, fallback to CPU
        try {
          await tf.setBackend('webgl');
        } catch (e) {
          console.warn('WebGL not available, falling back to CPU');
          await tf.setBackend('cpu');
        }
        
        // Load MoveNet model
        const detectorConfig = {
          modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING,
          enableSmoothing: true,  // ADD THIS
          minPoseScore: 0.3      // ADD THIS
        };
        const detector = await poseDetection.createDetector(
          poseDetection.SupportedModels.MoveNet,
          detectorConfig
        );
        setDetector(detector);
        
        // Setup camera
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          setError('Camera not available on this device');
          return;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { 
            width: 640, 
            height: 480,
            facingMode: 'user'
          },
          audio: false,
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          
          // IMPORTANT: Start detection loop when video is ready
          videoRef.current.onloadedmetadata = () => {
            setIsLoading(false);
            detectPose(); // ADD THIS LINE - Start continuous detection
          };
        }
      } catch (err) {
        console.error('Error initializing:', err);
        setError(err instanceof Error ? err.message : 'Failed to initialize camera');
        setIsLoading(false);
      }
    };

    initializeTFAndCamera();

    // Cleanup
    return () => {
      if (videoRef.current?.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
      // ADD: Cancel animation frame
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, []);

  // ADD: Timeout protection for capture
  useEffect(() => {
    if (isCapturing && countdown === 0) {
      const timeout = setTimeout(() => {
        if (!capturedKeypoints) {
          setCaptureError("Capture timeout. Please try again.");
          setIsCapturing(false);
          setCountdown(null);
        }
      }, 5000); // 5 second timeout
      
      return () => clearTimeout(timeout);
    }
  }, [isCapturing, countdown, capturedKeypoints]);

  // COMPLETELY REPLACE the detectPose function
  const detectPose = async () => {
    if (!detector || !videoRef.current || !canvasRef.current || !videoRef.current.readyState) {
      // Retry if not ready
      animationFrameId.current = requestAnimationFrame(detectPose);
      return;
    }

    try {
      const poses = await detector.estimatePoses(videoRef.current);
      
      // Draw skeleton
      const ctx = canvasRef.current.getContext('2d');
      if (!ctx) return;

      ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
      
      if (poses.length > 0) {
        drawKeypoints(poses[0].keypoints, ctx);
        drawSkeleton(poses[0].keypoints, ctx);
        
        // Calculate average confidence
        const avgConfidence = poses[0].keypoints.reduce((sum, kp) => 
          sum + (kp.score || 0), 0) / poses[0].keypoints.length;
        setDetectionConfidence(avgConfidence);
        
        // Capture when countdown reaches 0 AND confidence is good
        if (isCapturing && countdown === 0 && !capturedKeypoints) {
          if (avgConfidence > 0.5) {
            setCapturedKeypoints(poses[0].keypoints);
            setIsCapturing(false);
            setCountdown(null);
            return; // Stop the loop after capture
          } else {
            setCaptureError("Please ensure you're fully visible in the camera");
          }
        }
      }

      // Continue detection loop unless we've captured
      if (!capturedKeypoints) {
        animationFrameId.current = requestAnimationFrame(detectPose);
      }
    } catch (err) {
      console.error('Error detecting pose:', err);
      // Continue trying even if there's an error
      animationFrameId.current = requestAnimationFrame(detectPose);
    }
  };

  // REPLACE the startCapture function
  const startCapture = () => {
    if (!detector || isLoading) return;
    
    setCountdown(3);
    setIsCapturing(true);
    setCaptureError(null); // Clear any previous errors
    
    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev === null || prev <= 0) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Make sure detection is running
    if (!animationFrameId.current) {
      detectPose();
    }
  };

  // Keep the rest of the functions the same
  const drawKeypoints = (keypoints: any[], ctx: CanvasRenderingContext2D) => {
    keypoints.forEach((keypoint: any) => {
      if (keypoint.score && keypoint.score > 0.3) {
        ctx.beginPath();
        ctx.arc(keypoint.x, keypoint.y, 5, 0, 2 * Math.PI);
        ctx.fillStyle = '#00ff00';
        ctx.fill();
      }
    });
  };

  const drawSkeleton = (keypoints: any[], ctx: CanvasRenderingContext2D) => {
    const adjacentKeyPoints = poseDetection.util.getAdjacentPairs(poseDetection.SupportedModels.MoveNet);
    
    adjacentKeyPoints.forEach(([i, j]) => {
      const kp1 = keypoints[i];
      const kp2 = keypoints[j];
      
      if (kp1.score > 0.3 && kp2.score > 0.3) {
        ctx.beginPath();
        ctx.moveTo(kp1.x, kp1.y);
        ctx.lineTo(kp2.x, kp2.y);
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });
  };

  const handleComplete = () => {
    if (capturedKeypoints) {
      // Normalize keypoints for backend
      const normalizedKeypoints = capturedKeypoints.map(kp => ({
        x: kp.x / 640,  // Normalize to 0-1
        y: kp.y / 480,  // Normalize to 0-1
        score: kp.score || 0,
        name: kp.name || ''
      }));
      onComplete(normalizedKeypoints);
    }
  };

  const retry = () => {
    setCapturedKeypoints(null);
    setCountdown(null);
    setCaptureError(null);
    setDetectionConfidence(0);
    detectPose(); // Restart detection
  };

  if (error) {
    return (
      <div className="camera-modal">
        <div className="camera-content">
          <div className="camera-header">
            <h2>Camera Error</h2>
            <button className="close-button" onClick={onClose}>×</button>
          </div>
          <p style={{ color: 'red', marginTop: '20px' }}>{error}</p>
          <p>Please ensure:</p>
          <ul>
            <li>You've allowed camera permissions</li>
            <li>No other application is using your camera</li>
            <li>You're using a supported browser (Chrome, Firefox, Edge)</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="camera-modal">
      <div className="camera-content">
        <div className="camera-header">
          <h2>{test.name}</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <p>{test.description}</p>
        
        <div className="test-buttons" style={{ marginBottom: '20px' }}>
          <a 
            href={test.youtube_link} 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn-secondary"
          >
            <Youtube size={16} />
            Watch Tutorial
          </a>
        </div>

        <div className="video-container">
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            muted
            width={640} 
            height={480}
            style={{ display: isLoading ? 'none' : 'block' }}
          />
          <canvas 
            ref={canvasRef} 
            width={640} 
            height={480}
            style={{ display: isLoading ? 'none' : 'block' }}
          />
          
          {isLoading && (
            <div style={{ width: 640, height: 480, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f3f4f6' }}>
              <div className="loading">
                <div className="spinner"></div>
                <span>Loading camera and AI model...</span>
              </div>
            </div>
          )}
          
          {countdown !== null && countdown > 0 && (
            <div className="countdown">{countdown}</div>
          )}
          
          {/* ADD: Confidence meter */}
          {detectionConfidence > 0 && !capturedKeypoints && (
            <div className="confidence-meter">
              <div className="confidence-label">Pose Detection Quality</div>
              <div className="confidence-bar">
                <div 
                  className="confidence-fill" 
                  style={{ 
                    width: `${detectionConfidence * 100}%`,
                    backgroundColor: detectionConfidence > 0.5 ? '#10b981' : '#f59e0b'
                  }}
                />
              </div>
            </div>
          )}
        </div>

        {/* ADD: Error display */}
        {captureError && (
          <div style={{ color: 'red', marginTop: '10px', textAlign: 'center' }}>
            {captureError}
          </div>
        )}

        <div className="camera-controls">
          {!capturedKeypoints ? (
            <button 
              className="btn-primary" 
              onClick={startCapture}
              disabled={isCapturing || isLoading || !detector}
            >
              <Camera size={20} />
              {isCapturing ? 'Get Ready...' : 'Start Test'}
            </button>
          ) : (
            <>
              <button className="btn-secondary" onClick={retry}>
                <RotateCcw size={20} />
                Retry
              </button>
              <button className="btn-primary" onClick={handleComplete}>
                <Play size={20} />
                Analyze Movement
              </button>
            </>
          )}
        </div>

        {capturedKeypoints && (
          <div className="results-container">
            <h3>Position Captured!</h3>
            <p>Click "Analyze Movement" to see your results.</p>
          </div>
        )}
      </div>
    </div>
  );
};