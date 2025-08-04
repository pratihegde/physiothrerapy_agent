MOBILITY_TESTS = {
    "shoulder": {
        "flexion": {
            "name": "Shoulder Flexion Test",
            "description": "Raise your arms straight overhead",
            "movenet_check": "shoulder_flexion",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_SHOULDER_FLEXION",
            "pass_criteria": {
                "angle": 170,  # degrees
                "description": "Arms should reach near ears without arching back"
            },
            "common_compensations": ["Arching lower back", "Shrugging shoulders", "Bending elbows"]
        },
        "external_rotation": {
            "name": "Shoulder External Rotation Test", 
            "description": "Elbow at 90°, rotate forearm outward",
            "movenet_check": "shoulder_external_rotation",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_SHOULDER_ER",
            "pass_criteria": {
                "angle": 90,
                "description": "Forearm should reach 90° from starting position"
            }
        },
        "internal_rotation": {
            "name": "Shoulder Internal Rotation Test",
            "description": "Hand behind back, reach up spine",
            "movenet_check": "shoulder_internal_rotation", 
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_SHOULDER_IR",
            "pass_criteria": {
                "description": "Thumb should reach between shoulder blades"
            }
        }
    },
    "hip": {
        "internal_rotation": {
            "name": "Hip Internal Rotation Test",
            "description": "Seated, rotate foot outward (knee stays still)",
            "movenet_check": "hip_internal_rotation",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_HIP_IR",
            "pass_criteria": {
                "angle": 35,
                "description": "35-45° of internal rotation is normal"
            }
        },
        "external_rotation": {
            "name": "Hip External Rotation Test",
            "description": "Seated, rotate foot inward (knee stays still)",
            "movenet_check": "hip_external_rotation",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_HIP_ER",
            "pass_criteria": {
                "angle": 45,
                "description": "45° of external rotation is normal"
            }
        },
        "flexion": {
            "name": "Hip Flexion Test",
            "description": "Lying down, bring knee to chest",
            "movenet_check": "hip_flexion",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_HIP_FLEXION",
            "pass_criteria": {
                "angle": 120,
                "description": "Knee should come close to chest without opposite leg lifting"
            }
        }
    },
    "ankle": {
        "dorsiflexion": {
            "name": "Ankle Dorsiflexion Test",
            "description": "Knee to wall test - how far can your toe be from wall?",
            "movenet_check": "ankle_dorsiflexion",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_ANKLE_DF",
            "pass_criteria": {
                "distance": 10,  # cm
                "description": "Normal is 10-12cm from wall to toe"
            }
        }
    },
    "spine": {
        "flexion": {
            "name": "Spine Flexion Test",
            "description": "Standing forward bend",
            "movenet_check": "spine_flexion",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_SPINE_FLEXION",
            "pass_criteria": {
                "description": "Fingertips should reach floor or within 10cm"
            }
        },
        "rotation": {
            "name": "Thoracic Rotation Test",
            "description": "Seated with stick across shoulders, rotate left and right",
            "movenet_check": "thoracic_rotation",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_THORACIC_ROT",
            "pass_criteria": {
                "angle": 45,
                "description": "45° rotation each direction is normal"
            }
        }
    },
    "functional": {
        "overhead_squat": {
            "name": "Overhead Squat Assessment",
            "description": "Arms overhead, perform full squat",
            "movenet_check": "overhead_squat",
            "youtube_link": "https://youtube.com/watch?v=PLACEHOLDER_OVERHEAD_SQUAT",
            "pass_criteria": {
                "description": "Heels stay down, knees track over toes, arms stay overhead, no excessive forward lean"
            },
            "check_points": ["heel_lift", "knee_valgus", "arm_fall", "forward_lean"]
        }
    }
}