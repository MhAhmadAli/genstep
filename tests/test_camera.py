import cv2

def test_camera():
    print("Testing Camera initialization...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open video device.")
        return
        
    print("Camera opened successfully. Reading a frame...")
    ret, frame = cap.read()
    
    if ret:
        print(f"Success! Captured frame with shape {frame.shape}")
    else:
        print("Error: Could not read frame.")
        
    cap.release()

if __name__ == "__main__":
    test_camera()
