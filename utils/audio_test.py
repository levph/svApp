from ffpyplayer.player import MediaPlayer


# Function to play audio using ffpyplayer
def play_audio(stream_uri):
    player = MediaPlayer(stream_uri)
    while True:
        audio_frame, val = player.get_frame()
        if val == 'eof' or audio_frame is None:
            break


# Example usage
audio_stream_uri = 'rtsp://172.20.245.64:554/av0_1'  # Replace with your audio stream URI

play_audio(audio_stream_uri)
