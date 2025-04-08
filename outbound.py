import os
import json
import base64
import asyncio
import argparse
from fastapi import FastAPI, WebSocket, BackgroundTasks,Request
from fastapi.responses import JSONResponse,HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
import websockets
from dotenv import load_dotenv
from twilio.rest import Client
import uvicorn
import re
import aiohttp
import audioop
import vosk
import whisper
from collections import deque

load_dotenv()

transcriptions = []
CL = '\x1b[0K'
BS = '\x08'

model = vosk.Model('model')
rec = vosk.KaldiRecognizer(model, 16000)

audio_buffer = deque()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

PORT = int(os.getenv('PORT', 5050))
SHOW_TIMING_MATH = False
SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to chat about "
    "anything the user is interested in and is prepared to offer them facts. "
    "You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. "
    "Always stay positive, but work in a joke when appropriate."
)
VOICE = 'alloy'

LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

app = FastAPI()

if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')


@app.get('/', response_class=JSONResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

async def send_to_openai(audio_payload,openai_ws):
    """Send audio data to the OpenAI Realtime API."""
    try:
        audio_append = {
            "type": "input_audio_buffer.append",
            "audio": audio_payload
        }
        await openai_ws.send_json(audio_append)
    except Exception as e:
        print(f"Error sending audio to OpenAI: {e}")


async def process_transcription(audio_payload,rec):
    """Process audio for live transcription using Vosk."""
    try:
        combinedBytes = b""
        for i in audio_payload:
            audio = base64.b64decode(i)
            audio = audioop.ulaw2lin(audio, 2)
            audio = audioop.ratecv(audio, 2, 1, 8000, 16000, None)[0]
            combinedBytes += audio

        if rec.AcceptWaveform(combinedBytes):
            r = json.loads(rec.Result())
            transcription_text = r['text']
            print(CL + transcription_text + ' ', end='', flush=True)
            transcriptions.append(transcription_text)

        else:
            r = json.loads(rec.PartialResult())
            partial_text  = r['partial']
            print(CL + partial_text + BS * len(partial_text), end='', flush=True)
            transcriptions.append(partial_text)
    except Exception as e:
        print(f"Error processing transcription: {e}")


async def handler_buffer_wait():
    global audio_buffer
    while True:
        if audio_buffer:
            await asyncio.sleep(10)
            payloads_to_process  = list(audio_buffer)
            audio_buffer.clear()
            await process_transcription(payloads_to_process,rec)
            print("=================================================================")
            await print_transcriptions()
            print("=================================================================")
        else:
            await asyncio.sleep(1)


async def print_transcriptions():
    for i,text in enumerate(transcriptions):
        print(f"{i}. {text}")




@app.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()
    openai_url = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(openai_url, headers=headers) as openai_ws:
            await initialize_session(openai_ws)
            stream_sid = None
            latest_media_timestamp = 0
            last_assistant_item = None
            mark_queue = []
            response_start_timestamp_twilio = None
            asyncio.create_task(handler_buffer_wait())

            async def receive_from_twilio():
                """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
                nonlocal stream_sid,latest_media_timestamp,response_start_timestamp_twilio
                try:
                    async for message in websocket.iter_text():
                        data = json.loads(message)
                        if data['event'] == 'media' and not openai_ws.closed:
                            audio_payload = data['media']['payload']
                            audio_buffer.append(audio_payload)
                            asyncio.create_task(send_to_openai(audio_payload,openai_ws))
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
                    if openai_ws.open:
                        await openai_ws.close()

            async def send_to_twilio():
                """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
                nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
                try:
                    async for openai_message in openai_ws:
                        response = json.loads(openai_message.data)
                        
                        
                        ##### NEED TO VERIFY THE FUNCTION CALLS AND CHANGES #####
                        if response.get("type") == "function_call" and response.get("name") == "get_my_report_mysql":
                            # Extract parameters (if any)
                            question = response["parameters"].get("question", "")
                            # Call our handler to query the database
                            result = await get_my_report_mysql_handler(question)
                            # Create a function response message and send it back to OpenAI
                            function_response = {
                                "type": "tool_response",
                                "name": "get_my_report_mysql",
                                "result": result
                            }
                            await openai_ws.send_json(function_response)
                            continue  # Skip further processing of this message
                        
                        if response['type'] in LOG_EVENT_TYPES:
                            print(f"Received event: {response['type']}", response)
                        if response['type'] == 'session.updated':
                            print("Session updated successfully:", response)
                        if response['type'] == 'response.audio.delta' and response.get('delta'):
                            try:
                                audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                            except Exception as e:
                                print(f"Base64 Decode Error: {e}")
                                continue # Skip this delta
                            audio_delta = {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {
                                        "payload": audio_payload
                                    }
                                }
                            await websocket.send_json(audio_delta)
                            if response_start_timestamp_twilio is None:
                                response_start_timestamp_twilio = latest_media_timestamp
                                if SHOW_TIMING_MATH:
                                        print(f"Setting start timestamp for new response: {response_start_timestamp_twilio}ms")

                                if response.get('item_id'):
                                    last_assistant_item = response['item_id']

                                await send_mark(websocket, stream_sid)

                            if response.get('type') == 'input_audio_buffer.speech_started':
                                print("Speech started detected.")
                                if last_assistant_item:
                                    print(f"Interrupting response with id: {last_assistant_item}")
                                    await handle_speech_started_event()
                            
                except Exception as e:
                    print(f"Error in send_to_twilio: {e}")
            
            async def handle_speech_started_event():
                    """Handle interruption when the caller's speech starts."""
                    nonlocal response_start_timestamp_twilio, last_assistant_item
                    print("Handling speech started event.")
                    if mark_queue and response_start_timestamp_twilio is not None:
                        elapsed_time = latest_media_timestamp - response_start_timestamp_twilio
                        if SHOW_TIMING_MATH:
                            print(f"Calculating elapsed time for truncation: {latest_media_timestamp} - {response_start_timestamp_twilio} = {elapsed_time}ms")

                        if last_assistant_item:
                            if SHOW_TIMING_MATH:
                                print(f"Truncating item with ID: {last_assistant_item}, Truncated at: {elapsed_time}ms")

                            truncate_event = {
                                "type": "conversation.item.truncate",
                                "item_id": last_assistant_item,
                                "content_index": 0,
                                "audio_end_ms": elapsed_time
                            }
                            await openai_ws.send_json(truncate_event)

                        await websocket.send_json({
                            "event": "clear",
                            "streamSid": stream_sid
                        })

                        mark_queue.clear()
                        last_assistant_item = None
                        response_start_timestamp_twilio = None
            
            async def send_mark(connection, stream_sid):
                    if stream_sid:
                        mark_event = {
                            "event": "mark",
                            "streamSid": stream_sid,
                            "mark": {"name": "responsePart"}
                        }
                        await connection.send_json(mark_event)
                        mark_queue.append('responsePart')

                
            await asyncio.gather(receive_from_twilio(), send_to_twilio(),handler_buffer_wait())

async def send_initial_conversation_item(openai_ws):
    """Send initial conversation so AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Greet the user with 'Hello there! I am an AI voice assistant powered by "
                        "Twilio and the OpenAI Realtime API. You can ask me for facts, jokes, or "
                        "anything you can imagine. How can I help you?'"
                    )
                }
            ]
        }
    }
    await openai_ws.send_json(initial_conversation_item)
    await openai_ws.send_json({"type": "response.create"})

async def initialize_session(openai_ws):
    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE + " Please verify the customer's outstanding credit using the `get_my_report_mysql` function, and mention that if the balance is not cleared by the due date, extra penalty charges will be applied.",
            "modalities": ["text", "audio"],
            "temperature": 0.8,
            "tools": [
                
                {
                    "type": "function",
                    "name": "incentive_details",
                    "description": "Get incentive details for a given phone number, including additional benefits for exceeding the target.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": { "type": "string" }
                        },
                        "required": ["phone_number"]
                    }
                },
                {
                    "type": "function",
                    "name": "penalty_details",
                    "description": "Fetch details of penalty charges applicable after the due date.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": { "type": "string" }
                        },
                        "required": ["phone_number"]
                    }
                },
                {
                    "type": "function",
                    "name": "collection_improvements",
                    "description": "Provide guidelines for improving collections, including strategies for top customers and defaulters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": { "type": "string" }
                        },
                        "required": ["phone_number"]
                    }
                },
                {
                    "type": "function",
                    "name": "top_defaulters",
                    "description": "Retrieve a list of top defaulters along with their outstanding amounts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": { "type": "string" }
                        },
                        "required": ["phone_number"]
                    }
                },
                {
                "type": "function",
                "name": "get_my_report_mysql",
                "description": "Gets the information from the database of the enterprise...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": { "type": "string" }
                    },
                    "required": ["question"]
                }
                },
                {
                "type": "function",
                "name": "get_insurance_details",
                "description": "Gets the information on insurance of the caller from the insurance table of the database regarding the policcy, claim, dues etc of the caller. The prompt has default phone number...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": { "type": "string" }
                    },
                    "required": ["question"]
                }
                },
            ],
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send_json(session_update)

    await send_initial_conversation_item(openai_ws)


async def check_number_allowed(to):
    """Check if a number is allowed to be called."""
    try:
        # Uncomment these lines to test numbers. Only add numbers you have permission to call
        # OVERRIDE_NUMBERS = ['+18005551212'] 
        # if to in OVERRIDE_NUMBERS:             
          # return True

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
    
async def make_call(phone_number_to_call: str):
    """Make an outbound call."""
    if not phone_number_to_call:
        raise ValueError("Please provide a phone number to call.")

    is_allowed = await check_number_allowed(phone_number_to_call)
    if not is_allowed:
        raise ValueError(f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")

    # Ensure compliance with applicable laws and regulations
    # All of the rules of TCPA apply even if a call is made by AI.
    # Do your own diligence for compliance.

    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect></Response>'
    )

    call = client.calls.create(
        from_=PHONE_NUMBER_FROM,
        to=phone_number_to_call,
        twiml=outbound_twiml
    )

    await log_call_sid(call.sid)

async def log_call_sid(call_sid):
    """Log the call SID."""
    print(f"Call started with SID: {call_sid}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Twilio AI voice assistant server.")
    parser.add_argument('--call', required=True, help="The phone number to call, e.g., '--call=+18005551212'")
    args = parser.parse_args()

    phone_number = args.call
    print(
        'Our recommendation is to always disclose the use of AI for outbound or inbound calls.\n'
        'Reminder: All of the rules of TCPA apply even if a call is made by AI.\n'
        'Check with your counsel for legal and compliance advice.'
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(make_call(phone_number))
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)