# Replace 'stream_uri' with the actual stream URI obtained in the previous step
import cv2

main_stream_uri = 'rtsp://172.20.254.66:554/av0_0'  # Replace with your main stream URI
stream2 = "rtsp://172.20.245.64:554/av0_1"
cap = cv2.VideoCapture(main_stream_uri)

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()
    # Display the resulting frame
    cv2.imshow('frame', frame)
    # Break the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()