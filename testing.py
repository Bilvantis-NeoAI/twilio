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
import time
import aiohttp
import audioop
import whisper
import numpy as np
from openai import OpenAI
from collections import deque
from enum import Enum

# Load environment variables
load_dotenv()

SHOW_TIMING_MATH = False

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

class CallStatus(Enum):
    IDLE = 0
    IN_PROGRESS = 1
    COMPLETED = 2

openai_client = OpenAI(api_key=OPENAI_API_KEY)

if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

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
    """Simulate AI processing for now."""
    if  transcription_list is None or transcription_list == "":
        return ""

    last_transcription = str(transcription_list)
    return f"I heard you say, {last_transcription}"

async def text_to_audio(text):
    """Convert text to audio using OpenAI's TTS API."""
    if not text.strip():
        return None

    try:
        response = openai_client.audio.speech.create(
            model="gpt-4o-mini-tts",
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

def is_user_speaking(audio_payload, threshold=0.1):
    """Detect if audio contains speech above threshold volume."""
    try:
        audio = base64.b64decode(audio_payload)
        audio = audioop.ulaw2lin(audio, 2)
        rms = audioop.rms(audio, 2) / 32768
        return rms > threshold
    except Exception:
        return False

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

        result = whisper_model.transcribe(audio_np, language='en')
        transcription_text = result["text"].strip()
        print("===========")
        print(transcription_text)
        transcriptions.append(transcription_text)
        return transcription_text
    except Exception as e:
        print(f"Error processing transcription: {e}")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()
    
    stream_sid = None
    transcriptions_list = ""
    last_response_sent = False
    response = ""
    twilio_playing  = False
    latest_media_timestamp = 0
    last_assistant_item = None
    mark_queue = []
    response_start_timestamp_twilio = None
    current_response_task = None
    prev_stream_id = None

    async def receive_from_twilio():
        """Receive audio data from Twilio and process periodically."""
        global current_call_status
        nonlocal stream_sid, transcriptions_list,response,last_response_sent,twilio_playing,prev_stream_id,current_response_task
        last_processed_time = asyncio.get_event_loop().time()
        processing_interval = 4  # seconds

        try:
            async for message in websocket.iter_text():
                
                current_time = asyncio.get_event_loop().time()
                data = json.loads(message)
                if data['event'] == 'media':
                    if not stream_sid: 
                        continue
                    audio_payload = data['media']['payload']
                    if is_user_speaking(audio_payload) and twilio_playing:
                        print("Speach detected")
                        twilio_playing = False
                        await websocket.send_text(json.dumps({
                            "event": "clear",
                            "streamSid": stream_sid
                        }))

                        if current_response_task and not current_response_task.done():
                            print("interrupted!!!")
                            current_response_task.cancel()
                            try:
                                await current_response_task
                            except asyncio.CancelledError:
                                print("Successfully interrupted AI speech")
                            current_response_task = None

                     
                        audio_buffer.clear()
                    else:   
                        audio_buffer.append(audio_payload)

                    prev_stream_id = stream_sid
                    if current_time - last_processed_time >= processing_interval:
                            if audio_buffer:
                                payloads_to_process = list(audio_buffer)
                                audio_buffer.clear()
                                if not last_response_sent:
                                    transcriptions_list = await process_transcription(payloads_to_process)
                                    last_processed_time = current_time
                                    response = await (send_to_agent(transcriptions_list))
                                    twilio_playing = True
                                    current_response_task = asyncio.create_task(send_to_twilio(response))
                                    last_response_sent = False
                                    audio_buffer.clear()
                                    transcriptions_list = ""
                                    

                elif data['event'] == 'start':
                    # SYS_STATE == 'started'
                    stream_sid = data['start']['streamSid']
                    twilio_playing = False
                    audio_buffer.clear()
                    print(f"Stream started: {stream_sid}")

                elif data['event'] == 'mark':  # Twilio playback markers
                    if data['mark']['name'] == 'end_of_audio':
                        twilio_playing = False
                        print("Twilio finished playing audio")
                
                elif data['event'] == 'stop':
                    print(f"Stream stopped") 
                    current_call_status = CallStatus.COMPLETED
                    
                    complete_transcriptions = " ".join([i for i in transcriptions])
                    print(complete_transcriptions)
                    await process_call_queue()
                    if current_response_task and not current_response_task.done():
                        current_response_task.cancel()
                        try:
                            await current_response_task
                        except asyncio.CancelledError:
                            print("Cancelled response task on stream stop")
                        

        except WebSocketDisconnect:
            print("Client disconnected.")
            if current_call_status == CallStatus.IN_PROGRESS:
                current_call_status = CallStatus.COMPLETED
                await process_call_queue()
        except Exception as e:
            print(f"Error in receive_from_twilio: {e}")

        finally:
        # Ensure status is updated if connection closes
            if current_call_status == CallStatus.IN_PROGRESS:
                current_call_status = CallStatus.COMPLETED
                await process_call_queue()

    async def send_to_twilio(response):
        """Send AI-generated response back to Twilio."""
        nonlocal twilio_playing 
        if not response:
            return

        twilio_playing  = True
        print(f"Sending response: {response}")
        print(f"Sending responding: {twilio_playing }")

        audio_data = await text_to_audio(response)
        if not audio_data:
            print("TTS failed.")
            return

        try:
            await websocket.send_text(json.dumps({
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": audio_data
                }
            }))

            await websocket.send_text(json.dumps({
                "event": "mark",
                "streamSid": stream_sid,
                "mark": {"name": "end_of_audio"}
            }))

            print("Response sent!")
            print(f" after sending is {twilio_playing }")
            
        except Exception as e:
            print(f"Error in send_to_twilio: {e}")
        finally:
            pass
    # await receive_from_twilio()

    await asyncio.gather(receive_from_twilio(),send_to_twilio(response))



async def make_call_with_status(phone_number: str, text: str):
    global current_call_status
    current_call_status = CallStatus.IN_PROGRESS

    """Make an outgoing call with Twilio."""
    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Say>{text}</Say><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect></Response>'
    )

    call = client.calls.create(
        from_=PHONE_NUMBER_FROM,
        to=phone_number,
        twiml=outbound_twiml
    )

    print(f"Call started with SID: {call.sid}") 

async def process_call_queue():
    """Process the next call in the queue if available."""
    global current_call_status
    if call_queue and current_call_status != CallStatus.IN_PROGRESS:
        phone_number, text = call_queue.pop(0)
        await make_call_with_status(phone_number, text)

async def make_call(phone_number_to_call: str, text: str):

    if not phone_number_to_call:
        raise ValueError("Please provide a phone number to call.")

    is_allowed = await check_number_allowed(phone_number_to_call)
    if not is_allowed:
        raise ValueError(f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")
    
    call_queue.append((phone_number_to_call, text))

    if current_call_status != CallStatus.IN_PROGRESS:
        await process_call_queue()

   

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
    # args = parse_arguments()
    SYS_STATE = 'stopped'

    nums = ["+17043693803","+17043693803"]
    current_call_status = CallStatus.IDLE
    call_queue = []

    for i in nums:
        text = "Hello! This is an AI-powered call reminder. Please follow up on your pending tasks today."
        print("Starting an outbound call...")
        print("The number is ",i)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(make_call(i, text))

    uvicorn.run(app, host="0.0.0.0", port=PORT)