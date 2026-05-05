#!/usr/bin/env python3
import cv2
import numpy as np
import time
import os
import sys

# --- SUPPRESS C++ STARTUP ERRORS ---
try:
    null_fd = os.open(os.devnull, os.O_WRONLY)
    save_err = os.dup(2)
    os.dup2(null_fd, 2)
    silenced = True
except Exception:
    silenced = False

# --- GLOBAL STATE ---
state = {
    'pos':   np.array([0.0, 0.0, 10.0]), 
    'piv':   np.array([0.0, 0.0, 0.0]),  
    'light': np.array([5.0, -5.0, 0.0]), 
    'yaw': 0.0, 
    'pitch': 0.0,
    # Speeds are now tracked independently per mode
    'step_mult': {'OBJECT': 1.0, 'LIGHT': 1.0, 'PIVOT': 1.0},         
    'control_mode': 'OBJECT'
}

def print_status():
    mode = state['control_mode']
    current_speed = state['step_mult'][mode]
    
    base = f"\r⚙️  MODE: [{mode:<6}] | SPEED: {current_speed:.1f}x "
    
    if mode == 'PIVOT':
        extra = f"| PIVOT POS: ({state['pos'][0]:.1f}, {state['pos'][1]:.1f}, {state['pos'][2]:.1f})      "
    elif mode == 'OBJECT':
        extra = f"| POS: ({state['pos'][0]:.1f}, {state['pos'][1]:.1f}, {state['pos'][2]:.1f}) | ROT: ({np.degrees(state['pitch']):.0f}°, {np.degrees(state['yaw']):.0f}°)      "
    else:
        extra = "                                                                 "
    print(base + extra, end="", flush=True)

# --- ENGINE INITIALIZATION ---
if not hasattr(cv2, 'ovis'):
    if silenced:
        os.dup2(save_err, 2); os.close(null_fd)
    print("❌ cv2.ovis not available")
    sys.exit(1)

full_model_path = "./obj/barbie.obj"
model_exists = os.path.exists(full_model_path)
model_filename = ""
target_entity = "model" if model_exists else "plane_entity"

if model_exists:
    model_dir = os.path.dirname(full_model_path)
    model_filename = os.path.basename(full_model_path)
    cv2.ovis.addResourceLocation(model_dir)

win = cv2.ovis.createWindow("OGRE .obj Viewer", (800, 600), cv2.ovis.SCENE_INTERACTIVE)
K = np.array([[800, 0, 400], [0, 800, 300], [0, 0, 1]], dtype=np.float32)
cam = win.createCameraEntity("main_cam", K, (800, 600), 1000.0)

tvec_zero = np.array([0.0, 0.0, 0.0])
rvec_zero = np.array([0.0, 0.0, 0.0])

win.createLightEntity("key_light", state['light'], rvec_zero)
win.createLightEntity("fill_light", np.array([-5.0, -2.0, 2.0]), rvec_zero)
win.createLightEntity("rim_light", np.array([0.0, -5.0, 15.0]), rvec_zero)

if model_exists:
    win.createEntity("model", model_filename)
    win.setCameraPose(tvec_zero, rvec_zero) 
else:
    cv2.ovis.createPlaneMesh("plane_mesh", (3, 3))
    win.createEntity("plane_entity", "plane_mesh") 
    win.setCameraPose(np.array([0.0, 0.0, 4.0]), rvec_zero)

win.setBackgroundColor((0.3, 0.3, 0.35)) 

# Create Red Dot
radius = 0.15
pts = []
for phi in np.linspace(0, np.pi, 15):
    for theta in np.linspace(0, 2*np.pi, 15):
        pts.append([radius*np.sin(phi)*np.cos(theta), radius*np.sin(phi)*np.sin(theta), radius*np.cos(phi)])
pivot_pts = np.array(pts, dtype=np.float32).reshape(-1, 1, 3)
pivot_colors = np.full(pivot_pts.shape, [0, 0, 255], dtype=np.uint8) 

cv2.ovis.createPointCloudMesh("pivot_mesh", pivot_pts, pivot_colors)
win.createEntity("pivot_marker", "pivot_mesh")

# --- RESTORE CONSOLE OUTPUT ---
if silenced:
    os.dup2(save_err, 2)
    os.close(null_fd)

os.system('cls' if os.name == 'nt' else 'clear') 

print("=" * 70)
print(" OpenCV 4.13 + OGRE 1.12.13 + ovis — Independent Speeds Edition")
print("=" * 70)
print("\n🎮 CONTROLS:")
print("   - Left Click + Drag : Orbit Camera Angle")
print("   - 'M' Key           : Cycle Modes (OBJECT -> LIGHT -> PIVOT)")
print("   - 'o' / 'p' Keys    : Decrease / Increase Movement Speed (Per Mode)")
print("\n🧭 MOVEMENT (Depends on Mode):")
print("   - 'I', 'J', 'K', 'L': Move Up, Left, Down, Right")
print("   - 'Q' / 'E' Keys    : Move Depth Forward/Backward")
print("\n🔄 ROTATION (OBJECT MODE ONLY):")
print("   - 'W' / 'S' Keys    : Spin Object on X Axis (Pitch)")
print("   - 'A' / 'D' Keys    : Spin Object on Y Axis (Yaw)")
print("\n🎥 NUMPAD VIEWS (Retains Pivot & Position):")
print("   - '1' : Front         - '2' : Back")
print("   - '3' : Right         - '4' : Left")
print("   - '7' : Top           - '9' : Bottom")
print("\n🔥 RESETS:")
print("   - 'C' Key           : Reset ONLY Camera Angle (from Mouse Drag)")
print("   - 'R' Key           : FULL Reset (Everything)")
print("\n🚪 Press 'ESC' to Exit\n")

print_status()

TARGET_FPS = 60
FRAME_TIME = 1.0 / TARGET_FPS

while True:
    loop_start_time = time.time()
    
    win.update()
    raw_key = cv2.ovis.waitKey(1)
    
    if raw_key != -1:
        char_key = raw_key & 0xFF
        
        mode = state['control_mode']
        # Speed is now pulled specifically for the active mode
        move_speed = 0.5 * state['step_mult'][mode]
        spin_speed = 0.1 * state['step_mult'][mode]

        if char_key == 27: # ESC
            print("\n✅ Test finished! Window closed.")
            break
            
        elif char_key == ord('m'):
            modes = ['OBJECT', 'LIGHT', 'PIVOT']
            curr_idx = modes.index(state['control_mode'])
            state['control_mode'] = modes[(curr_idx + 1) % len(modes)]
            print_status()
            
        elif char_key == ord('o'):
            # Only updates the speed for the current mode
            state['step_mult'][mode] = max(0.1, state['step_mult'][mode] - 0.2)
            print_status()
            
        elif char_key == ord('p'):
            # Only updates the speed for the current mode
            state['step_mult'][mode] = min(5.0, state['step_mult'][mode] + 0.2)
            print_status()
            
        # --- BLENDER NUMPAD VIEWS ---
        elif char_key == ord('1'): state['yaw'], state['pitch'] = 0.0, 0.0; print_status()
        elif char_key == ord('2'): state['yaw'], state['pitch'] = np.pi, 0.0; print_status()
        elif char_key == ord('4'): state['yaw'], state['pitch'] = -np.pi/2, 0.0; print_status()
        elif char_key == ord('3'): state['yaw'], state['pitch'] = np.pi/2, 0.0; print_status()
        elif char_key == ord('7'): state['yaw'], state['pitch'] = 0.0, -np.pi/2; print_status()
        elif char_key == ord('9'): state['yaw'], state['pitch'] = 0.0, np.pi/2; print_status()
            
        # --- RESETS ---
        elif char_key == ord('c'):
            win.setCameraPose(tvec_zero, rvec_zero)
            print_status()

        elif char_key == ord('r'):
            state['pos'] = np.array([0.0, 0.0, 10.0])
            state['piv'] = np.array([0.0, 0.0, 0.0])
            state['light'] = np.array([5.0, -5.0, 0.0])
            state['yaw'], state['pitch'] = 0.0, 0.0
            state['step_mult'] = {'OBJECT': 1.0, 'LIGHT': 1.0, 'PIVOT': 1.0}
            state['control_mode'] = 'OBJECT'
            win.setCameraPose(tvec_zero, rvec_zero)
            print_status()

        # --- DYNAMIC MOVEMENT & PIVOT MATH FIX ---
        R_pitch_current, _ = cv2.Rodrigues(np.array([state['pitch'], 0.0, 0.0]))
        R_yaw_current, _   = cv2.Rodrigues(np.array([0.0, state['yaw'], 0.0]))
        R_user_current = R_yaw_current @ R_pitch_current

        dp_global = np.zeros(3)
        if char_key == ord('j'): dp_global[0] -= move_speed
        elif char_key == ord('l'): dp_global[0] += move_speed
        elif char_key == ord('i'): dp_global[1] -= move_speed
        elif char_key == ord('k'): dp_global[1] += move_speed
        elif char_key == ord('q'): dp_global[2] += move_speed
        elif char_key == ord('e'): dp_global[2] -= move_speed

        if np.any(dp_global):
            if state['control_mode'] == 'OBJECT':
                state['pos'] += dp_global
            elif state['control_mode'] == 'PIVOT':
                state['pos'] += dp_global
                state['piv'] += R_user_current.T @ dp_global
            elif state['control_mode'] == 'LIGHT':
                state['light'] += dp_global
            print_status()

        # --- ROTATION INPUTS ---
        if state['control_mode'] == 'OBJECT':
            if char_key == ord('w'): state['pitch'] -= spin_speed 
            elif char_key == ord('s'): state['pitch'] += spin_speed 
            elif char_key == ord('a'): state['yaw'] += spin_speed 
            elif char_key == ord('d'): state['yaw'] -= spin_speed 
            print_status()

    # --- RENDER MATRICES ---
    R_pitch, _ = cv2.Rodrigues(np.array([state['pitch'], 0.0, 0.0]))
    R_yaw, _   = cv2.Rodrigues(np.array([0.0, state['yaw'], 0.0]))
    R_user = R_yaw @ R_pitch 
    
    Rx_base, _ = cv2.Rodrigues(np.array([np.pi, 0.0, 0.0])) 
    R_total = R_user @ Rx_base
    rvec_obj, _ = cv2.Rodrigues(R_total)
    
    tvec_final = state['pos'] - (R_user @ state['piv'])
    
    win.setEntityPose(target_entity, tvec_final, rvec_obj)
    win.setEntityPose("pivot_marker", state['pos'], rvec_zero)
    win.setEntityPose("key_light", state['light'], rvec_zero)
        
    elapsed_time = time.time() - loop_start_time
    time_to_sleep = FRAME_TIME - elapsed_time
    if time_to_sleep > 0:
        time.sleep(time_to_sleep)
