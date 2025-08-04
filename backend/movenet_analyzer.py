from typing import Dict, List, Tuple
import numpy as np

class MoveNetAnalyzer:
    """Analyzes MoveNet keypoints for mobility tests"""
    
    # MoveNet keypoint indices
    KEYPOINTS = {
        'nose': 0,
        'left_eye': 1,
        'right_eye': 2,
        'left_ear': 3,
        'right_ear': 4,
        'left_shoulder': 5,
        'right_shoulder': 6,
        'left_elbow': 7,
        'right_elbow': 8,
        'left_wrist': 9,
        'right_wrist': 10,
        'left_hip': 11,
        'right_hip': 12,
        'left_knee': 13,
        'right_knee': 14,
        'left_ankle': 15,
        'right_ankle': 16
    }
    
    @staticmethod
    def calculate_angle(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """Calculate angle between three points"""
        # Vector from p2 to p1
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        # Vector from p2 to p3
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        # Calculate angle
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        
        return np.degrees(angle)
    
    def analyze_shoulder_flexion(self, keypoints: List[Dict]) -> Dict:
        """Analyze shoulder flexion from keypoints"""
        left_shoulder = keypoints[self.KEYPOINTS['left_shoulder']]
        left_elbow = keypoints[self.KEYPOINTS['left_elbow']]
        left_wrist = keypoints[self.KEYPOINTS['left_wrist']]
        left_hip = keypoints[self.KEYPOINTS['left_hip']]
        
        # Calculate angle between hip-shoulder-wrist
        angle = self.calculate_angle(
            (left_hip['x'], left_hip['y']),
            (left_shoulder['x'], left_shoulder['y']),
            (left_wrist['x'], left_wrist['y'])
        )
        
        return {
            "angle": angle,
            "pass": angle >= 170,
            "compensation": self._check_shoulder_compensation(keypoints)
        }
    
    def analyze_hip_internal_rotation(self, keypoints: List[Dict]) -> Dict:
        """Analyze hip internal rotation"""
        hip = keypoints[self.KEYPOINTS['left_hip']]
        knee = keypoints[self.KEYPOINTS['left_knee']]
        ankle = keypoints[self.KEYPOINTS['left_ankle']]
        
        # Calculate angle of lower leg relative to vertical
        angle = self.calculate_angle(
            (knee['x'], knee['y'] - 0.1),  # Point above knee (vertical reference)
            (knee['x'], knee['y']),
            (ankle['x'], ankle['y'])
        )
        
        return {
            "angle": angle,
            "pass": angle >= 35,
            "details": "Normal range: 35-45 degrees"
        }
    
    def analyze_overhead_squat(self, keypoints: List[Dict]) -> Dict:
        """Comprehensive overhead squat analysis"""
        results = {
            "heel_lift": self._check_heel_lift(keypoints),
            "knee_valgus": self._check_knee_valgus(keypoints),
            "arm_fall": self._check_arm_fall(keypoints),
            "forward_lean": self._check_forward_lean(keypoints),
            "depth": self._check_squat_depth(keypoints)
        }
        
        # Overall pass if no major compensations
        results["pass"] = not any([
            results["heel_lift"],
            results["knee_valgus"],
            results["arm_fall"],
            results["forward_lean"]
        ])
        
        return results
    
    def _check_heel_lift(self, keypoints: List[Dict]) -> bool:
        """Check if heels are lifting during squat"""
        # Simplified check - in practice would track ankle position over time
        ankle = keypoints[self.KEYPOINTS['left_ankle']]
        # Check if ankle confidence is low (might indicate heel lift)
        return ankle.get('score', 1.0) < 0.5
    
    def _check_knee_valgus(self, keypoints: List[Dict]) -> bool:
        """Check for knee caving inward"""
        left_hip = keypoints[self.KEYPOINTS['left_hip']]
        left_knee = keypoints[self.KEYPOINTS['left_knee']]
        left_ankle = keypoints[self.KEYPOINTS['left_ankle']]
        
        # Check if knee is medial to ankle-hip line
        expected_knee_x = left_ankle['x'] + (left_hip['x'] - left_ankle['x']) * 0.5
        return abs(left_knee['x'] - expected_knee_x) > 0.05  # 5% threshold
    
    def _check_arm_fall(self, keypoints: List[Dict]) -> bool:
        """Check if arms fall forward during squat"""
        shoulder = keypoints[self.KEYPOINTS['left_shoulder']]
        wrist = keypoints[self.KEYPOINTS['left_wrist']]
        
        # Arms should stay relatively overhead
        return wrist['y'] > shoulder['y'] - 0.1
    
    def _check_forward_lean(self, keypoints: List[Dict]) -> bool:
        """Check for excessive forward lean"""
        shoulder = keypoints[self.KEYPOINTS['left_shoulder']]
        hip = keypoints[self.KEYPOINTS['left_hip']]
        ankle = keypoints[self.KEYPOINTS['left_ankle']]
        
        # Check if shoulder is too far forward of ankle
        return shoulder['x'] > ankle['x'] + 0.15
    
    def _check_squat_depth(self, keypoints: List[Dict]) -> str:
        """Check squat depth"""
        hip = keypoints[self.KEYPOINTS['left_hip']]
        knee = keypoints[self.KEYPOINTS['left_knee']]
        
        if hip['y'] > knee['y']:
            return "Above parallel"
        elif hip['y'] > knee['y'] - 0.05:
            return "Parallel"
        else:
            return "Below parallel"
    
    def _check_shoulder_compensation(self, keypoints: List[Dict]) -> List[str]:
        """Check for shoulder compensations"""
        compensations = []
        
        # Check for shoulder shrug
        shoulder = keypoints[self.KEYPOINTS['left_shoulder']]
        ear = keypoints[self.KEYPOINTS['left_ear']]
        if shoulder['y'] < ear['y'] + 0.1:
            compensations.append("Shoulder shrugging detected")
        
        # Check for elbow bend
        shoulder = keypoints[self.KEYPOINTS['left_shoulder']]
        elbow = keypoints[self.KEYPOINTS['left_elbow']]
        wrist = keypoints[self.KEYPOINTS['left_wrist']]
        
        elbow_angle = self.calculate_angle(
            (shoulder['x'], shoulder['y']),
            (elbow['x'], elbow['y']),
            (wrist['x'], wrist['y'])
        )
        
        if elbow_angle < 170:
            compensations.append("Elbow bending detected")
        
        return compensations