import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as tf from '@tensorflow/tfjs';
import * as poseDetection from '@tensorflow-models/pose-detection';
import '@tensorflow/tfjs-backend-webgl';
import { Camera, Youtube, Play, RotateCcw, RefreshCw } from 'lucide-react';

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
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [detectionConfidence, setDetectionConfidence] = useState<number>(0);
  const [isDetecting, setIsDetecting] = useState(false);
  const [initStatus, setInitStatus] = useState<string>('Starting...');
  
  const animationFrameId = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const initTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // MoveNet keypoint connections for skeleton drawing
  const adjacentKeyPoints = [
    [0, 1], [0, 2], [1, 3], [2, 4], [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
    [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16]
  ];

  const drawKeypoints = useCallback((keypoints: any[], ctx: CanvasRenderingContext2D) => {
    keypoints.forEach((keypoint: any) => {
      if (keypoint.score && keypoint.score > 0.3) {
        ctx.beginPath();
        ctx.arc(keypoint.x, keypoint.y, 6, 0, 2 * Math.PI);
        ctx.fillStyle = '#00ff00';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });
  }, []);

  const drawSkeleton = useCallback((keypoints: any[], ctx: CanvasRenderingContext2D) => {
    adjacentKeyPoints.forEach(([i, j]) => {
      const kp1 = keypoints[i];
      const kp2 = keypoints[j];
      
      if (kp1 && kp2 && kp1.score > 0.3 && kp2.score > 0.3) {
        ctx.beginPath();
        ctx.moveTo(kp1.x, kp1.y);
        ctx.lineTo(kp2.x, kp2.y);
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 3;
        ctx.stroke();
      }
    });
  }, []);

  const detectPose = useCallback(async () => {
    if (!detector || !videoRef.current || !canvasRef.current || !isDetecting) {
      if (isDetecting) {
        animationFrameId.current = requestAnimationFrame(detectPose);
      }
      return;
    }

    // Wait for video to be properly loaded
    if (videoRef.current.readyState < 2) {
      animationFrameId.current = requestAnimationFrame(detectPose);
      return;
    }

    try {
      const poses = await detector.estimatePoses(videoRef.current);
      const ctx = canvasRef.current.getContext('2d');
      
      if (!ctx) return;

      // Clear canvas
      ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
      
      if (poses.length > 0 && poses[0].keypoints.length > 0) {
        const keypoints = poses[0].keypoints;
        
        // Draw skeleton first (behind keypoints)
        drawSkeleton(keypoints, ctx);
        // Draw keypoints on top
        drawKeypoints(keypoints, ctx);
        
        // Calculate confidence
        const avgConfidence = keypoints.reduce((sum, kp) => 
          sum + (kp.score || 0), 0) / keypoints.length;
        setDetectionConfidence(avgConfidence);
        
        // Capture logic
        if (isCapturing && countdown === 0 && !capturedKeypoints) {
          if (avgConfidence > 0.35) { // Lowered threshold further
            console.log('Capturing pose with confidence:', avgConfidence);
            setCapturedKeypoints([...keypoints]);
            setIsCapturing(false);
            setCountdown(null);
            setCaptureError(null);
            return; // Stop detection after capture
          } else {
            setCaptureError(`Pose confidence: ${(avgConfidence * 100).toFixed(0)}%. Please ensure you're fully visible and well-lit.`);
          }
        }
      } else {
        setDetectionConfidence(0);
        if (isCapturing && countdown === 0) {
          setCaptureError("No pose detected. Please step back and ensure your full body is visible.");
        }
      }

      // Continue detection loop
      if (isDetecting && !capturedKeypoints) {
        animationFrameId.current = requestAnimationFrame(detectPose);
      }
    } catch (err) {
      console.error('Error detecting pose:', err);
      if (isDetecting) {
        animationFrameId.current = requestAnimationFrame(detectPose);
      }
    }
  }, [detector, isDetecting, isCapturing, countdown, capturedKeypoints, drawKeypoints, drawSkeleton]);

  const initializeCamera = useCallback(async () => {
    try {
      setInitStatus('Requesting camera access...');
      
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Camera not supported on this device or browser');
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: { ideal: 640, max: 1280 },
          height: { ideal: 480, max: 720 },
          facingMode: 'user',
          frameRate: { ideal: 30, max: 60 }
        },
        audio: false,
      });

      streamRef.current = stream;

      if (!videoRef.current) {
        throw new Error('Video element not available');
      }

      videoRef.current.srcObject = stream;
      
      return new Promise<void>((resolve, reject) => {
        const video = videoRef.current!;
        
        const handleVideoReady = () => {
          console.log('Video ready - dimensions:', video.videoWidth, 'x', video.videoHeight);
          video.removeEventListener('loadedmetadata', handleVideoReady);
          video.removeEventListener('error', handleVideoError);
          clearTimeout(videoTimeout);
          resolve();
        };

        const handleVideoError = (e: Event) => {
          console.error('Video error:', e);
          video.removeEventListener('loadedmetadata', handleVideoReady);
          video.removeEventListener('error', handleVideoError);
          clearTimeout(videoTimeout);
          reject(new Error('Failed to load video stream'));
        };

        const videoTimeout = setTimeout(() => {
          video.removeEventListener('loadedmetadata', handleVideoReady);
          video.removeEventListener('error', handleVideoError);
          reject(new Error('Video loading timeout'));
        }, 10000);

        video.addEventListener('loadedmetadata', handleVideoReady);
        video.addEventListener('error', handleVideoError);

        // If video is already ready
        if (video.readyState >= 1) {
          handleVideoReady();
        }
      });
    } catch (err) {
      console.error('Camera initialization error:', err);
      throw err;
    }
  }, []);

  const initializeTensorFlow = useCallback(async () => {
    try {
      setInitStatus('Loading AI model...');
      
      console.log('Initializing TensorFlow.js...');
      await tf.ready();
      
      // Try WebGL backend first, fallback to CPU
      try {
        await tf.setBackend('webgl');
        await tf.ready();
        console.log('Using WebGL backend');
      } catch (e) {
        console.warn('WebGL not available, trying CPU backend');
        await tf.setBackend('cpu');
        await tf.ready();
        console.log('Using CPU backend');
      }
      
      console.log('Loading MoveNet model...');
      const detectorConfig = {
        modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING,
        enableSmoothing: true,
        minPoseScore: 0.2
      };
      
      const newDetector = await poseDetection.createDetector(
        poseDetection.SupportedModels.MoveNet,
        detectorConfig
      );
      
      console.log('MoveNet model loaded successfully');
      return newDetector;
    } catch (err) {
      console.error('TensorFlow initialization error:', err);
      throw new Error(`AI model loading failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, []);

  const initializeSystem = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Clear any existing timeout
      if (initTimeoutRef.current) {
        clearTimeout(initTimeoutRef.current);
      }

      // Set overall timeout
      initTimeoutRef.current = setTimeout(() => {
        setError('Camera initialization timeout. Please try again.');
        setIsLoading(false);
      }, 30000); // 30 second timeout

      // Initialize TensorFlow and Camera in parallel for faster loading
      const [newDetector] = await Promise.all([
        initializeTensorFlow(),
        initializeCamera()
      ]);

      setDetector(newDetector);
      setInitStatus('Starting pose detection...');
      
      // Small delay to ensure everything is ready
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setIsLoading(false);
      setIsDetecting(true);
      
      // Clear timeout if successful
      if (initTimeoutRef.current) {
        clearTimeout(initTimeoutRef.current);
        initTimeoutRef.current = null;
      }
      
      console.log('System initialized successfully');
    } catch (err) {
      console.error('System initialization error:', err);
      setError(err instanceof Error ? err.message : 'Failed to initialize camera and AI model');
      setIsLoading(false);
      
      if (initTimeoutRef.current) {
        clearTimeout(initTimeoutRef.current);
        initTimeoutRef.current = null;
      }
    }
  }, [initializeTensorFlow, initializeCamera]);

  // Initialize system on mount
  useEffect(() => {
    initializeSystem();

    return () => {
      // Cleanup
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (initTimeoutRef.current) {
        clearTimeout(initTimeoutRef.current);
      }
      setIsDetecting(false);
    };
  }, [initializeSystem]);

  // Start pose detection when ready
  useEffect(() => {
    if (isDetecting && detector && !animationFrameId.current) {
      console.log('Starting pose detection loop');
      detectPose();
    }
  }, [isDetecting, detector, detectPose]);

  // Capture timeout protection
  useEffect(() => {
    if (isCapturing && countdown === 0) {
      const timeout = setTimeout(() => {
        if (!capturedKeypoints) {
          setCaptureError("Capture timeout. Please ensure you're visible and try again.");
          setIsCapturing(false);
          setCountdown(null);
        }
      }, 10000); // 10 second timeout for capture
      
      return () => clearTimeout(timeout);
    }
  }, [isCapturing, countdown, capturedKeypoints]);

  const startCapture = () => {
    if (!detector || isLoading || !isDetecting) {
      console.log('Cannot start capture - not ready');
      return;
    }
    
    console.log('Starting capture countdown');
    setCountdown(3);
    setIsCapturing(true);
    setCaptureError(null);
    
    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev === null || prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const retry = () => {
    console.log('Retrying capture');
    setCapturedKeypoints(null);
    setCountdown(null);
    setCaptureError(null);
    setDetectionConfidence(0);
    setIsDetecting(true);
    
    // Restart detection if needed
    if (!animationFrameId.current && detector) {
      detectPose();
    }
  };

  const handleComplete = () => {
    if (capturedKeypoints) {
      console.log('Completing with keypoints:', capturedKeypoints.length);
      const normalizedKeypoints = capturedKeypoints.map(kp => ({
        x: kp.x / 640,
        y: kp.y / 480,
        score: kp.score || 0,
        name: kp.name || ''
      }));
      onComplete(normalizedKeypoints);
    }
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  if (error) {
    return (
      <div className="camera-modal" style={modalStyles}>
        <div className="camera-content" style={contentStyles}>
          <div className="camera-header" style={headerStyles}>
            <h2>Camera Error</h2>
            <button className="close-button" onClick={onClose} style={closeButtonStyles}>×</button>
          </div>
          <div style={{ color: '#dc2626', marginTop: '20px', textAlign: 'center' }}>
            <p><strong>Error:</strong> {error}</p>
            <div style={{ marginTop: '15px', textAlign: 'left' }}>
              <p><strong>Troubleshooting steps:</strong></p>
              <ul style={{ marginLeft: '20px', textAlign: 'left' }}>
                <li>Click "Allow" when prompted for camera access</li>
                <li>Close other apps that might be using your camera (Zoom, Teams, etc.)</li>
                <li>Try using Chrome or Edge browser</li>
                <li>Make sure you're on HTTPS or localhost</li>
                <li>Check if camera works in other websites</li>
                <li>Try refreshing the page</li>
              </ul>
            </div>
            <div style={{ marginTop: '20px', display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button onClick={initializeSystem} style={buttonStyles.secondary}>
                <RotateCcw size={16} />
                <span style={{ marginLeft: '8px' }}>Try Again</span>
              </button>
              <button onClick={handleRefresh} style={buttonStyles.primary}>
                <RefreshCw size={16} />
                <span style={{ marginLeft: '8px' }}>Refresh Page</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="camera-modal" style={modalStyles}>
      <div className="camera-content" style={contentStyles}>
        <div className="camera-header" style={headerStyles}>
          <h2>{test.name}</h2>
          <button className="close-button" onClick={onClose} style={closeButtonStyles}>×</button>
        </div>

        <p style={{ marginBottom: '15px', color: '#374151' }}>{test.description}</p>
        
        <div style={{ marginBottom: '20px' }}>
          <a 
            href={test.youtube_link} 
            target="_blank" 
            rel="noopener noreferrer"
            style={buttonStyles.secondary}
          >
            <Youtube size={16} />
            <span style={{ marginLeft: '8px' }}>Watch Tutorial</span>
          </a>
        </div>

        <div style={{ position: 'relative', width: 640, height: 480, margin: '0 auto', background: '#000', borderRadius: '8px', overflow: 'hidden' }}>
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            muted
            width={640} 
            height={480}
            style={{ 
              display: isLoading ? 'none' : 'block',
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover'
            }}
          />
          <canvas 
            ref={canvasRef} 
            width={640} 
            height={480}
            style={{ 
              display: isLoading ? 'none' : 'block',
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
              zIndex: 2
            }}
          />
          
          {isLoading && (
            <div style={loadingStyles}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={spinnerStyles}></div>
                <span>{initStatus}</span>
              </div>
              <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '10px' }}>
                This may take 10-15 seconds on first load
              </div>
            </div>
          )}
          
          {countdown !== null && countdown > 0 && (
            <div style={countdownStyles}>{countdown}</div>
          )}
          
          {detectionConfidence > 0 && !capturedKeypoints && !isLoading && (
            <div style={confidenceMeterStyles.container}>
              <div style={confidenceMeterStyles.label}>
                Pose Detection: {(detectionConfidence * 100).toFixed(0)}%
                {detectionConfidence < 0.35 && ' - Move closer or improve lighting'}
              </div>
              <div style={confidenceMeterStyles.bar}>
                <div 
                  style={{ 
                    ...confidenceMeterStyles.fill,
                    width: `${detectionConfidence * 100}%`,
                    backgroundColor: detectionConfidence > 0.35 ? '#10b981' : '#f59e0b'
                  }}
                />
              </div>
            </div>
          )}
        </div>

        {captureError && (
          <div style={{ color: '#dc2626', marginTop: '10px', textAlign: 'center', fontSize: '14px', background: '#fef2f2', padding: '8px', borderRadius: '6px', border: '1px solid #fecaca' }}>
            {captureError}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '20px' }}>
          {!capturedKeypoints ? (
            <button 
              onClick={startCapture}
              disabled={isCapturing || isLoading || !detector || !isDetecting}
              style={{
                ...buttonStyles.primary,
                opacity: (isCapturing || isLoading || !detector || !isDetecting) ? 0.6 : 1
              }}
            >
              <Camera size={20} />
              <span style={{ marginLeft: '8px' }}>
                {isCapturing ? 'Get Ready...' : 'Start Test'}
              </span>
            </button>
          ) : (
            <>
              <button onClick={retry} style={buttonStyles.secondary}>
                <RotateCcw size={20} />
                <span style={{ marginLeft: '8px' }}>Retry</span>
              </button>
              <button onClick={handleComplete} style={buttonStyles.primary}>
                <Play size={20} />
                <span style={{ marginLeft: '8px' }}>Analyze Movement</span>
              </button>
            </>
          )}
        </div>

        {capturedKeypoints && (
          <div style={{ textAlign: 'center', marginTop: '20px', color: '#059669', background: '#f0fdf4', padding: '15px', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
            <h3 style={{ margin: '0 0 10px 0' }}>✓ Position Captured!</h3>
            <p style={{ margin: 0, fontSize: '14px' }}>Click "Analyze Movement" to see your results.</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Styles remain the same...
const modalStyles: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0, 0, 0, 0.8)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
  padding: '20px'
};

const contentStyles: React.CSSProperties = {
  backgroundColor: 'white',
  borderRadius: '12px',
  padding: '24px',
  maxWidth: '720px',
  maxHeight: '90vh',
  overflow: 'auto',
  position: 'relative'
};

const headerStyles: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '20px',
  borderBottom: '1px solid #e5e7eb',
  paddingBottom: '15px'
};

const closeButtonStyles: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontSize: '28px',
  cursor: 'pointer',
  color: '#6b7280',
  padding: '0',
  width: '32px',
  height: '32px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
};

const loadingStyles: React.CSSProperties = {
  width: '100%',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  background: '#f3f4f6',
  color: '#374151'
};

const spinnerStyles: React.CSSProperties = {
  width: '24px',
  height: '24px',
  border: '2px solid #e5e7eb',
  borderTop: '2px solid #3b82f6',
  borderRadius: '50%',
  animation: 'spin 1s linear infinite'
};

const countdownStyles: React.CSSProperties = {
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  fontSize: '72px',
  fontWeight: 'bold',
  color: '#ffffff',
  textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
  zIndex: 10
};

const confidenceMeterStyles = {
  container: {
    position: 'absolute' as const,
    top: '10px',
    left: '10px',
    right: '10px',
    backgroundColor: 'rgba(0,0,0,0.8)',
    padding: '10px',
    borderRadius: '6px',
    zIndex: 5
  },
  label: {
    color: 'white',
    fontSize: '12px',
    marginBottom: '4px',
    fontWeight: '500'
  },
  bar: {
    width: '100%',
    height: '4px',
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: '2px',
    overflow: 'hidden' as const
  },
  fill: {
    height: '100%',
    transition: 'width 0.3s ease'
  }
};

const buttonStyles = {
  primary: {
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    padding: '12px 20px',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    transition: 'background-color 0.2s'
  } as React.CSSProperties,
  secondary: {
    backgroundColor: '#f3f4f6',
    color: '#374151',
    border: '1px solid #d1d5db',
    padding: '12px 20px',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    textDecoration: 'none',
    transition: 'background-color 0.2s'
  } as React.CSSProperties
};