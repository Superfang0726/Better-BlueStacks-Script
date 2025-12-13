import cv2
try:
    sift = cv2.SIFT_create()
    print("SIFT Available")
except Exception as e:
    print(f"SIFT Not Available: {e}")

try:
    orb = cv2.ORB_create()
    print("ORB Available")
except Exception as e:
    print(f"ORB Not Available: {e}")
