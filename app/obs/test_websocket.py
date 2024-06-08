import asyncio
import websockets
import time


async def test_websocket():
    uri = "ws://localhost:8080/ws"
    async with websockets.connect(uri) as websocket:
        start_time = time.time()
        try:
            while True:
                message = await websocket.recv()
                elapsed_time = time.time() - start_time
                print(f"Received: {message} at {elapsed_time} seconds")
                # Check if the message is received within an acceptable window

                # Reset the timer
                start_time = time.time()
                # Optionally limit the number of messages to check
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")


# Run the test
asyncio.run(test_websocket())
