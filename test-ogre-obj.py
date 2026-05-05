#!/usr/bin/env python3
import cv2
import numpy as np
import time
import os
import sys

print("=" * 70)
print(" OpenCV 4.13 + OGRE 1.12.13 + ovis — Studio Lighting Edition")
print("=" * 70)

if not hasattr(cv2, 'ovis'):
    print("❌ cv2.ovis not available")
    sys.exit(1)

# --- GLOBAL STATE ---
state = {
    # Object State
    'obj_x': 0.0, 'obj_y': 0.0, 'obj_z': 10.0, 'obj_yaw': 0.0,
    # Main Light State
    'light_x': 5.0, 'light_y': -5.0, 'light_z': 0.0,
    
    # System State
    'step_mult': 1.0,         # 1.0 is default speed
    'control_mode': 'OBJECT'  # Toggles between 'OBJECT' and 'LIGHT'
}

def print_status():
    # \r overwrites the current line in the terminal so it doesn't spam your console
    print(f"\r⚙️  MODE: [{state['control_mode']}] | SPEED: {state['step_mult']:.1f}x      ", end="", flush=True)

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

# --- 3-POINT STUDIO LIGHTING ---
# We track the Key Light so we can move it. Fill and Rim lights stay static.
win.createLightEntity("key_light", np.array([state['light_x'], state['light_y'], state['light_z']]), rvec_zero)
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

print("\n🎮 CONTROLS:")
print("   - Left Click + Drag : Orbit Camera")
print("   - 'M' Key           : Swap Controls (OBJECT vs LIGHT)")
print("   - 'o' and 'p' Keys  : Decrease / Increase Movement Speed")
print("\n🧭 MOVEMENT (Based on Current Mode):")
print("   - 'I', 'J', 'K', 'L': Pan Up, Left, Down, Right")
print("   - 'W' / 'S' Keys    : Move Forward / Backward (Zoom or Brightness)")
print("   - 'A' / 'D' Keys    : Spin Object (Disabled in Light Mode)")
print("\n🔄 RESETS:")
print("   - 'R' Key           : Reset Everything (Positions, Speeds, and Camera)")
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
        
        # Base speeds affected by the step multiplier
        move_speed = 0.5 * state['step_mult']
        spin_speed = 0.1 * state['step_mult']

        if char_key == 27: # ESC
            print("\n✅ Test finished! Window closed.")
            break
            
        # --- SYSTEM CONTROLS ---
        elif char_key == ord('m'):
            state['control_mode'] = 'LIGHT' if state['control_mode'] == 'OBJECT' else 'OBJECT'
            print_status()
        elif char_key == ord('o'):
            state['step_mult'] = max(0.1, state['step_mult'] - 0.2)
            print_status()
        elif char_key == ord('p'):
            state['step_mult'] = min(5.0, state['step_mult'] + 0.2)
            print_status()
            
        # --- RESETS ---
        elif char_key == ord('r'):
            state['obj_x'], state['obj_y'], state['obj_z'], state['obj_yaw'] = 0.0, 0.0, 10.0, 0.0
            state['light_x'], state['light_y'], state['light_z'] = 5.0, -5.0, 0.0
            state['step_mult'] = 1.0
            state['control_mode'] = 'OBJECT'
            win.setCameraPose(tvec_zero, rvec_zero)
            print_status()

        # --- DYNAMIC MOVEMENT (Depends on Mode) ---
        elif state['control_mode'] == 'OBJECT':
            if char_key == ord('w'): state['obj_z'] -= move_speed 
            elif char_key == ord('s'): state['obj_z'] += move_speed 
            elif char_key == ord('d'): state['obj_yaw'] -= spin_speed 
            elif char_key == ord('a'): state['obj_yaw'] += spin_speed 
            elif char_key == ord('i'): state['obj_y'] -= move_speed
            elif char_key == ord('k'): state['obj_y'] += move_speed
            elif char_key == ord('j'): state['obj_x'] -= move_speed
            elif char_key == ord('l'): state['obj_x'] += move_speed
            
        elif state['control_mode'] == 'LIGHT':
            # Note: Moving a light closer on Z axis increases its intensity!
            if char_key == ord('w'): state['light_z'] -= move_speed 
            elif char_key == ord('s'): state['light_z'] += move_speed 
            elif char_key == ord('i'): state['light_y'] -= move_speed
            elif char_key == ord('k'): state['light_y'] += move_speed
            elif char_key == ord('j'): state['light_x'] -= move_speed
            elif char_key == ord('l'): state['light_x'] += move_speed

    # 1. Update Object Pose
    Rx, _ = cv2.Rodrigues(np.array([np.pi, 0.0, 0.0]))
    Ry, _ = cv2.Rodrigues(np.array([0.0, state['obj_yaw'], 0.0]))
    rvec_obj, _ = cv2.Rodrigues(Ry @ Rx)
    tvec_obj = np.array([state['obj_x'], state['obj_y'], state['obj_z']])
    win.setEntityPose(target_entity, tvec_obj, rvec_obj)
    
    # 2. Update Main Light Pose
    tvec_light = np.array([state['light_x'], state['light_y'], state['light_z']])
    win.setEntityPose("key_light", tvec_light, rvec_zero)
        
    # Frame Limiter
    elapsed_time = time.time() - loop_start_time
    time_to_sleep = FRAME_TIME - elapsed_time
    if time_to_sleep > 0:
        time.sleep(time_to_sleep)
