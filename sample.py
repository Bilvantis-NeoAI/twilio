import os
import json
import base64
import asyncio
import argparse
import re
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv
from twilio.rest import Client
import uvicorn
import aiohttp
import audioop
import whisper
import numpy as np
from openai import OpenAI
from collections import deque

load_dotenv()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
text=""" """

PORT = int(os.getenv('PORT', 5050))
SHOW_TIMING_MATH = False
SYSTEM_MESSAGE = (
    "You are a warm and friendly AI assistant who speaks in a calm and soothing tone. "
    "You have a British accent and always enunciate clearly. You love sharing fun facts, "
    "engaging stories, and keeping conversations light-hearted. "
    "Use a natural conversational flow to make interactions engaging."
)
VOICE = 'coral'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created'
]

# Initialize Whisper model
whisper_model = whisper.load_model("base")
transcriptions = []
audio_buffer = deque()

app = FastAPI()

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
    # Log caller information
    caller_number = form_data.get("From")
    caller_name = form_data.get("CallerName") 
    caller_city = form_data.get("CallerCity")
    caller_state = form_data.get("CallerState")
    caller_zip = form_data.get("CallerZip")
    caller_country = form_data.get("CallerCountry")

    print(f"Caller Number: {caller_number}")
    print(f"Caller Name: {caller_name}")
    print(f"Caller Location: {caller_city}, {caller_state}, {caller_zip}, {caller_country}")
    
    response = VoiceResponse()
    response.say("Please wait while we connect your call to the A. I. voice assistant, powered by Twilio and the Open-A.I. Realtime API")
    response.pause(length=1)
    response.say("O.K. you can start talking!")
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

async def send_to_agent(transcription_list):
    if not transcription_list:
        return "I didn't catch that. Could you please repeat?"
    
    # Get the most recent transcription
    last_transcription = transcription_list[-1]
    
    # This is where you would typically call an LLM or your business logic
    # For now, we'll just echo back the last transcription
    return f"I heard you say: {last_transcription}"

async def text_to_audio(text):
    """Convert text to audio using OpenAI's TTS API"""
    if not text.strip():
        return None
        
    try:
        # Call OpenAI TTS API
        response = await openai_client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            response_format="pcm"  # We'll convert to ulaw
        )
        
        # Read the audio data
        audio_data = await response.read()
        
        # Convert WAV to linear PCM (16-bit, mono, 22.05kHz)
        # Skip WAV header (first 44 bytes) and convert to 8kHz μ-law
        audio = audioop.lin2lin(audio_data[44:], 2, 2)  # Convert to 16-bit PCM
        audio = audioop.ratecv(audio, 2, 1, 22050, 8000, None)[0]  # Resample to 8kHz
        ulaw_audio = audioop.lin2ulaw(audio, 2)  # Convert to μ-law
        
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

        result = whisper_model.transcribe(audio_np, language='en')
        transcription_text = result["text"].strip()
        print(transcription_text)
        transcriptions.append(transcription_text)
        return transcriptions
    except Exception as e:
        print(f"Error processing transcription: {e}")

async def print_transcriptions():
    """Print all transcriptions collected so far."""
    for i, text in enumerate(transcriptions):
        print(f"{i}. {text}")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()
    
    async with aiohttp.ClientSession() as session:
            stream_sid = None
            latest_media_timestamp = 0
            last_assistant_item = None
            mark_queue = []
            response_start_timestamp_twilio = None
            response = ""

            async def receive_from_twilio():
                """Receive audio data from Twilio, buffer it, and process periodically."""
                nonlocal stream_sid, latest_media_timestamp, response
                last_processed_time = asyncio.get_event_loop().time()
                processing_interval = 2  # seconds
                
                try:
                    async for message in websocket.iter_text():
                        current_time = asyncio.get_event_loop().time()
                        data = json.loads(message)
                        
                        if data['event'] == 'media':
                            audio_payload = data['media']['payload']
                            latest_media_timestamp = int(data['media']['timestamp'])
                            audio_buffer.append(audio_payload)
                            
                            # Check if it's time to process the buffer
                            if current_time - last_processed_time >= processing_interval:
                                if audio_buffer:
                                    payloads_to_process = list(audio_buffer)
                                    audio_buffer.clear()
                                    transcriptions_list = await process_transcription(payloads_to_process)
                                last_processed_time = current_time
                                
                                response = await  send_to_agent(transcriptions_list)
                            print("the response is ",response)
                            
                        elif data['event'] == 'start':
                            stream_sid = data['start']['streamSid']
                            print(f"Incoming stream has started {stream_sid}")
                            response_start_timestamp_twilio = None
                            latest_media_timestamp = 0
                            last_assistant_item = None
                            
                        elif data['event'] == 'mark':
                            if mark_queue:
                                mark_queue.pop(0)

                except WebSocketDisconnect:
                    print("Client disconnected.")
                except Exception as e:
                    print(f"Error in receive_from_twilio: {e}")
            async def send_to_twilio():
                """Send transcribed response back to Twilio using TwiML instructions."""
                try:
                    print("===================================")
                    print(response)
                    if response:
                        print("++++++++++++++++++++++++++")
                        print(response)
                        audio_data = await text_to_audio(response)
                        await websocket.send_text(json.dumps({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_data
                            }
                        }))
                        print(f"Sent response to Twilio: {response}")
                except Exception as e:
                    print(f"Error in send_to_twilio: {e}")


            await asyncio.gather(receive_from_twilio(), send_to_twilio())


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

async def make_call(phone_number_to_call: str, text: str):
    if not phone_number_to_call:
        raise ValueError("Please provide a phone number to call.")

    is_allowed = await check_number_allowed(phone_number_to_call)
    if not is_allowed:
        raise ValueError(f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")
    
    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Say>{text}</Say><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect></Response>'
    )

    call = client.calls.create(
        from_=PHONE_NUMBER_FROM,
        to=phone_number_to_call,
        twiml=outbound_twiml
    )
    
    await log_call_sid(call.sid)

async def log_call_sid(call_sid):
    """Log the call SID."""
    call_sid = call_sid
    print(f"Call started with SID: {call_sid}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the Twilio AI voice assistant server.")
    parser.add_argument('--call', help="The phone number to call, e.g., '--call=+18005551212'")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    if args.call:
        text =  """LENDINGKART AI BOT about your collection targets and pending tasks for today.
                         Task Reminders:
                            1. You have scheduled collections today. Please ensure timely follow-ups."""
        
        print(
            'Our recommendation is to always disclose the use of AI for outbound or inbound calls.\n'
            'Reminder: All of the rules of TCPA apply even if a call is made by AI.\n'
            'Check with your counsel for legal and compliance advice.'
        )
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(make_call(args.call,text))
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)