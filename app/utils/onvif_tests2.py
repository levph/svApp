import cv2
from ffpyplayer.player import MediaPlayer
import threading

# Function to play video and audio using ffpyplayer
def play_video_with_audio(stream_uri, stop_event):
    def video_loop():
        cap = cv2.VideoCapture(stream_uri)
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow('frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_event.set()
                break
        cap.release()
        cv2.destroyAllWindows()

    def audio_loop():
        player = MediaPlayer(stream_uri)
        while not stop_event.is_set():
            audio_frame, val = player.get_frame()
            if val == 'eof' or audio_frame is None:
                break

    video_thread = threading.Thread(target=video_loop)
    audio_thread = threading.Thread(target=audio_loop)

    video_thread.start()
    audio_thread.start()

    video_thread.join()
    audio_thread.join()

# Example usage
main_stream_uri = 'rtsp://172.20.245.64:554/av0_0'  # Replace with your main stream URI
stop_event = threading.Event()

play_video_with_audio(main_stream_uri, stop_event)
