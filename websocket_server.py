import asyncio
import websockets
import json
import threading
from websocket import WebSocketApp
from openai import OpenAI
import os
import socket
import base64
import io
from PIL import Image, ImageDraw

HOST = "0.0.0.0"
CONNECTABLE_ENDPOINT = None
PORT = 12345

clients = set()  # Track connected WebSocket clients

# # OpenAI WebSocket API Configuration
# openai_connector = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def handle_client(websocket):
    """Handles an incoming WebSocket client connection."""
    print(f"✅ Client Connected: {websocket.remote_address}")
    clients.add(websocket)

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "query":
                    user_query = data.get("msg")
                    user_img_query = data.get("image", None)
                    referent_point_query = data.get("point", None)
                    print(f"[Query] {user_query}")
                    
                    if user_img_query and referent_point_query:
                        user_img_query = draw_red_circle_on_image(user_img_query, referent_point_query)

                    # # Forward query to OpenAI API
                    # openai_response = send_query_to_openai(user_query, user_img_query)
                    openai_response = 'Hello world'
                    print(f"[Response] {openai_response}")
                    
                    # Send OpenAI response back to client
                    response = {"type": "response", "msg": openai_response}
                    await websocket.send(json.dumps(response))
                elif msg_type == "disconnect":
                    print(f"❌ Client {websocket.remote_address} disconnected.")
                    break  # Exit loop to remove the client below

            except json.JSONDecodeError:
                print("⚠️ Received invalid JSON from client.")

    except websockets.exceptions.ConnectionClosedError:
        print(f"❌ Client {websocket.remote_address} unexpectedly disconnected.")

    finally:
        if websocket in clients:
            clients.remove(websocket)
        # print(f"📢 Active Clients: {len(clients)}")

def save_image_for_debugging(image, filename="debug_output.jpg"):
    image.save(filename, format="JPEG")
    print(f"Debug image saved as {filename}")
    
def draw_red_circle_on_image(image_b64, point_str, radius=15):
    # Decode the base64 image to bytes.
    image_bytes = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")  # Ensure image is in RGB mode.
    
    # Parse the referent point from the string "x,y"
    try:
        x_str, y_str = point_str.split(',')
        x = int(x_str)
        y = int(y_str)
    except Exception as e:
        print("Invalid point format:", point_str)
        return image_b64  # return original if parsing fails.
    
    # Draw a red circle (ellipse) on the image.
    draw = ImageDraw.Draw(image)
    left_up = (x - radius, y - radius)
    right_down = (x + radius, y + radius)
    draw.ellipse([left_up, right_down], fill="red")
    
    # save_image_for_debugging(image)
    
    # Save image to a bytes buffer.
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    new_image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return new_image_b64


def send_query_to_openai(query, img_b64_str):
    """Sends a query to OpenAI's WebSocket API and waits for a response."""

    try:
        if img_b64_str is None:
            print("Empty image input")
        else:
            query_response = openai_connector.chat.completions.create(
            model="gpt-4o-mini",
            # model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistant that answer concisely on the questions."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64_str}"},
                        }
                    ]
                }],
            temperature=0,
            max_tokens=25
            )
            return query_response.choices[0].message.content
        return None
    
    except Exception as e:
        print(f"⚠️ OpenAI Query Error: {e}")
        return f"⚠️ Error: {str(e)}"

def get_ip_addr():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip
    
async def main():
    CONNECTABLE_ENDPOINT = get_ip_addr()
    print(f"📢 WebSocket Server Running on >> [ws://{CONNECTABLE_ENDPOINT}:{PORT}]")


    # Start WebSocket Server
    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()  # Keep the server running


# Run the WebSocket server
asyncio.run(main())
