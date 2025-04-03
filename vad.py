import os
import json
import base64
import asyncio
import re
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say
from dotenv import load_dotenv
from twilio.rest import Client
import uvicorn
import audioop
import whisper
import numpy as np
from openai import OpenAI
from collections import deque

# Load environment variables
load_dotenv()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
PORT = int(os.getenv('PORT', 5050))

# Initialize Whisper model
whisper_model = whisper.load_model("base")
transcriptions = []
audio_buffer = deque()

app = FastAPI()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    raise ValueError('Missing Twilio and/or OpenAI environment variables')

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    form_data = await request.form()
    caller_number = form_data.get("From")
    print(f"Incoming call from: {caller_number}")

    response = VoiceResponse()
    response.say("Please wait while we connect your call to the AI assistant.")
    response.pause(length=1)
    response.say("Okay, you can start talking!")

    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)

    return HTMLResponse(content=str(response), media_type="application/xml")

async def send_to_agent(transcription_list):
    """Process user input and generate AI response."""
    if not transcription_list:
        return ""

    last_transcription = str(transcription_list)
    return f"I heard you say: {last_transcription}"

async def text_to_audio(text):
    """Convert text to audio using OpenAI's TTS API."""
    if not text.strip():
        return None

    try:
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
            response_format="pcm"
        )

        audio_data = response.read()

        # Convert WAV to μ-law for Twilio
        audio = audioop.lin2lin(audio_data[44:], 2, 2)
        audio = audioop.ratecv(audio, 2, 1, 22050, 8000, None)[0]
        ulaw_audio = audioop.lin2ulaw(audio, 2)

        return base64.b64encode(ulaw_audio).decode('utf-8')
    except Exception as e:
        print(f"Error in text_to_audio: {e}")
        return None

async def process_transcription(audio_payload):
    """Process audio for live transcription using Whisper."""
    try:
        combined_bytes = b""
        for i in audio_payload:
            audio = base64.b64decode(i)
            audio = audioop.ulaw2lin(audio, 2)
            audio = audioop.ratecv(audio, 2, 1, 8000, 16000, None)[0]
            combined_bytes += audio

        audio_np = np.frombuffer(combined_bytes, dtype=np.int16)
        audio_np = audio_np.astype(np.float32) / 32768.0 

        result = whisper_model.transcribe(audio_np, language='en', no_speech_threshold=0.6)
        transcription_text = result["text"].strip()
        print("===========")
        print(transcription_text)
        transcriptions.append(transcription_text)
        return transcription_text
    except Exception as e:
        print(f"Error processing transcription: {e}")
        return ""

def is_user_speaking(audio_payload, threshold=0.1):
    """Detect if audio contains speech above threshold volume."""
    try:
        audio = base64.b64decode(audio_payload)
        audio = audioop.ulaw2lin(audio, 2)
        rms = audioop.rms(audio, 2) / 32768
        return rms > threshold
    except Exception:
        return False

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()

    stream_sid = None
    current_response_task = None
    responding = False
    processing_interval = 2  # seconds
    last_processed_time = 0

    async def receive_from_twilio():
        nonlocal stream_sid, current_response_task, responding, last_processed_time
        
        try:
            async for message in websocket.iter_text():
                data = json.loads(message)
                
                if data['event'] == 'start':
                    stream_sid = data['start']['streamSid']
                    audio_buffer.clear()
                    print(f"Stream started: {stream_sid}")
                
                elif data['event'] == 'media':
                    audio_payload = data['media']['payload']
                    audio_buffer.append(audio_payload)

                    # Immediate interruption handling
                    if responding and is_user_speaking(audio_payload):
                        print("User interruption detected - canceling current speech")
                        if current_response_task:
                            current_response_task.cancel()
                            try:
                                await current_response_task
                            except asyncio.CancelledError:
                                print("Successfully interrupted AI speech")
                        responding = False
                        audio_buffer.clear()
                    
                    # Process user speech when not responding
                    if not responding and audio_buffer:
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_processed_time >= processing_interval:
                            payloads_to_process = list(audio_buffer)
                            audio_buffer.clear()
                            
                            transcription = await process_transcription(payloads_to_process)
                            if transcription:
                                last_processed_time = current_time
                                response = await send_to_agent(transcription)
                                
                                # Cancel any existing task
                                if current_response_task:
                                    current_response_task.cancel()
                                    await current_response_task
                                
                                # Start new response
                                current_response_task = asyncio.create_task(send_to_twilio(response))
                
                elif data['event'] == 'stop':
                    print("Stream stopped")
                    if current_response_task:
                        current_response_task.cancel()
                        await current_response_task
                    break

        except WebSocketDisconnect:
            print("Client disconnected")
        except Exception as e:
            print(f"WebSocket Error: {e}")

    async def send_to_twilio(response):
        """Send AI-generated response back to Twilio."""
        nonlocal responding
        if not response:
            return

        responding = True
        print(f"Preparing response: {response}")

        try:
            audio_data = await text_to_audio(response)
            if not audio_data:
                return

            await websocket.send_text(json.dumps({
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": audio_data}
            }))
            print("Response sent!")
        except asyncio.CancelledError:
            print("Response was cancelled mid-speech")
            raise
        except Exception as e:
            print(f"Error in send_to_twilio: {e}")
        finally:
            responding = False

    await receive_from_twilio()

async def make_call(phone_number_to_call: str, text: str):
    """Make an outgoing call with Twilio."""
    if not phone_number_to_call:
        raise ValueError("Please provide a phone number to call.")

    is_allowed = await check_number_allowed(phone_number_to_call)
    if not is_allowed:
        raise ValueError(f"The number {phone_number_to_call} is not allowed.")

    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Say>{text}</Say><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect></Response>'
    )

    call = client.calls.create(
        from_=PHONE_NUMBER_FROM,
        to=phone_number_to_call,
        twiml=outbound_twiml
    )

    print(f"Call started with SID: {call.sid}")

async def check_number_allowed(to):
    """Check if a number is allowed to be called."""
    try:
        incoming_numbers = client.incoming_phone_numbers.list(phone_number=to)
        if incoming_numbers:
            return True

        outgoing_caller_ids = client.outgoing_caller_ids.list(phone_number=to)
        if outgoing_caller_ids:
            return True

        return False
    except Exception as e:
        print(f"Error checking phone number: {e}")
        return False

def parse_arguments():
    """Parse command line arguments."""
    import argparse
    parser = argparse.ArgumentParser(description="Run the Twilio AI voice assistant server.")
    parser.add_argument('--call', help="The phone number to call, e.g., '--call=+18005551212'")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    if args.call:
        text = "Hello! This is an AI-powered call reminder. Please follow up on your pending tasks today."
        print("Starting an outbound call...")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(make_call(args.call, text))

    uvicorn.run(app, host="0.0.0.0", port=PORT)