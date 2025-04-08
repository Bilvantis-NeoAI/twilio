import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv
import aiohttp
import audioop
import vosk
from collections import deque
from utils.get_func_calls import extract_function_call,create_function_call_output,call_function_function_calling
load_dotenv()
from utils.mysql_greet import fetch_explanation_by_phone
from utils.mysql_email_send import process_employee_performance

CALLER_NUMBER="+919963029130"

tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "Get current temperature for a given location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City and country e.g. Bogotá, Colombia"
            }
        },
        "required": [
            "location"
        ],
        "additionalProperties": False
    }
}]



audio_buffer = deque()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', 5050))
SYSTEM_MESSAGE = (
     "You are a warm and friendly AI assistant who speaks in a calm and soothing tone. "
    "You have a British accent and always enunciate clearly. You love sharing fun facts, "
    "you are capable of executing tools when clients request for specific information. You need to specific tool based on its description"
    "engaging stories, and keeping conversations light-hearted. "
    "Use a natural conversational flow to make interactions engaging."
    "default use Phone number {CALLER_NUMBER} if a parameter is not given the user to make function call."
)
VOICE = 'coral'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created'
]
SHOW_TIMING_MATH = False
# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

CL = '\x1b[0K'
BS = '\x08'

model = vosk.Model('model')
rec = vosk.KaldiRecognizer(model, 16000)

transcriptions = []



app = FastAPI()

async def get_caller_number(call_sid):
    import requests
    """Fetch caller's phone number using Twilio REST API."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls/{call_sid}.json"
    response = requests.get(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    
    if response.status_code == 200:
        call_data = response.json()
        return call_data.get("from", "Unknown Caller")
    else:
        print(f"⚠️ Failed to fetch caller details: {response.text}")
        return "Unknown Caller"
    


if not OPENAI_API_KEY:
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):

    form_data = await request.form()

    caller_number = form_data.get("From")
    caller_name = form_data.get("CallerName") 
    caller_city = form_data.get("CallerCity")
    caller_state = form_data.get("CallerState")
    caller_zip = form_data.get("CallerZip")
    caller_country = form_data.get("CallerCountry")

     # Debug: Raw body logging
    raw_body = await request.body()
    print(f"Raw body: {raw_body.decode()}")
       # Check request method
    if request.method == "POST":
        try:
            form_data = await request.form()
            caller_number = form_data.get("Caller", "Unknown")

            print(f"Incoming call from: {caller_number} :: {form_data}")        
        except Exception as e:
            print(f"Error parsing form data: {e}")

    elif request.method == "GET":
        query_params = request.query_params
        caller_number = query_params.get("Caller", "Unknown")
        print(f"Incoming call from (GET): {caller_number} :: {query_params}")

    """Handle incoming call and return TwiML response to connect to Media Stream."""



    greet=fetch_explanation_by_phone(caller_number)

    response = VoiceResponse()
    response.say("Hi- This is Bilvantis  A. I. voice assistant wait for moment")
    print(f"the greet message:: {greet}\n")
    response.pause(length=1)
    response.say(greet)
    response.pause(length=1)
    response.say("O.K. you can start talking!")
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

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



async def send_functions_response(msg, openai_ws):
     
 try:
     print('Sending function result to model :', json.dumps(msg))
     await openai_ws.send_json(msg)
     await openai_ws.send_json({"type": "response.create"})
 except Exception as e:
        print(f"Error sending send_functions_response to OpenAI: {e}")

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


async def print_transcriptions():
    for i,text in enumerate(transcriptions):
        print(f"{i}. {text}")

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

@app.websocket("/media-stream")
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
                nonlocal stream_sid, latest_media_timestamp
                try:
                    async for message in websocket.iter_text():
                        data = json.loads(message)
                        if data['event'] == 'media' and not openai_ws.closed:
                            audio_payload = data['media']['payload']
                            latest_media_timestamp = int(data['media']['timestamp'])
                            audio_buffer.append(audio_payload)
                            asyncio.create_task(send_to_openai(audio_payload,openai_ws))
                        elif data['event'] == 'start':
                            stream_sid = data['start']['streamSid']
                            print(f"Incoming stream has started {stream_sid}")
                            response_start_timestamp_twilio = None
                            latest_media_timestamp = 0
                            last_assistant_item = None
                        elif data['event'] == 'stop':
                            print(f"Stream stopped") 
                            call_sid = data["stop"]["callSid"]
                            print(f"📞  - STOP Call SID: {call_sid}")
                        # Fetch the caller's number asynchronously
                            caller_number = await get_caller_number(call_sid)
                            print(f"📞 STOP Caller Number: {caller_number}")
                            process_employee_performance(caller_number)
                        elif data['event'] == 'mark':
                            if mark_queue:
                                mark_queue.pop(0)

                except WebSocketDisconnect:
                    print("Client disconnected.")
                    if not openai_ws.closed: # Check if openai_ws is open
                        await openai_ws.close()
                except Exception as e:
                    print(f"Error in receive_from_twilio: {e}")
         



            async def send_to_twilio():
                """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
                nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
                try:
                    async for openai_message in openai_ws:
                        response = json.loads(openai_message.data)
                        rsp= extract_function_call(response)
                        if rsp :
                             print(f"function call detected:: {rsp}\n")
                             print(f"call id:: {rsp['call_id']}\n")
                             out=call_function_function_calling(rsp)

                             ret=create_function_call_output(rsp['call_id'], out)
                             print(f"dummy function response created::{ret}\n")
                             await send_functions_response(ret, openai_ws)


                        #print(f"Received FUNCTION CALL event: {response['type']}", response)
                       # if response['type'] in LOG_EVENT_TYPES:
                        #        print(f"Received event: {response['type']}")


                        if response.get('type') == 'response.audio.delta' and 'delta' in response:
                            try:
                                audio_payload = base64.b64decode(response['delta'])
                                # audio_payload = base64.b64decode(response['delta']).decode('utf-8') # Commented out decoding
                            except Exception as e:
                                print(f"Base64 Decode Error: {e}")
                                continue # Skip this delta

                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": base64.b64encode(audio_payload).decode('utf-8') # Re-encode the raw bytes
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

            await asyncio.gather(receive_from_twilio(), send_to_twilio())

async def send_initial_conversation_item(openai_ws):
    """Send initial conversation item if AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Greet the user with 'Hello there! I am an AI voice assistant powered by Twilio and the OpenAI Realtime API. You can ask me for facts, jokes, or anything you can imagine. How can I help you?'"
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
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
            "tools": [
                    {
                        "type": "function",
                        "name": "generate_horoscope_people",
                        "description": "Give today's horoscope for an astrological sign.",
                        "parameters": {
                        "type": "object",
                        "properties": {
                            "sign": {
                            "type": "string",
                            "description": "The sign for the horoscope.",
                            "enum": [
                                "Aries",
                                "Taurus",
                                "Gemini",
                                "Cancer",
                                "Leo",
                                "Virgo",
                                "Libra",
                                "Scorpio",
                                "Sagittarius",
                                "Capricorn",
                                "Aquarius",
                                "Pisces"
                            ]
                            }
                        },
                        "required": ["sign"]
                        }
                  },

                {
                    "type": "function",
                    "name": "get_target_status",
                    "description": "Retrieve the target status comparison and gap details.",
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

            {
                "type": "function",
                "name": "send_status_to_managers",
                "description": "this function sends status to managers..."
            },
            {
                "type": "function",
                "name": "get_weather_bilvantis",
                "description": "Get the current weather...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": { "type": "string" }
                    },
                    "required": ["location"]
                }
            },
            {
            "type": "function",
            "name": "search_knowledge_base_enterprise",
            "description": "Query a knowledge base to retrieve relevant info on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user question or search query."
                    },
                    "options": {
                        "type": "object",
                        "properties": {
                            "num_results": {
                                "type": "number",
                                "description": "Number of top results to return."
                            },
                            "domain_filter": {
                                "type": [
                                    "string",
                                    "null"
                                ],
                                "description": "Optional domain to narrow the search (e.g. 'finance', 'medical'). Pass null if not needed."
                            },
                            "sort_by": {
                                "type": [
                                    "string",
                                    "null"
                                ],
                                "enum": [
                                    "relevance",
                                    "date",
                                    "popularity",
                                    "alphabetical"
                                ],
                                "description": "How to sort results. Pass null if not needed."
                            }
                        },
                        "required": [
                            "num_results",
                            "domain_filter",
                            "sort_by"
                        ],
                        "additionalProperties": False
                    }
                },
                "required": [
                    "query",
                    "options"
                ],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "send_email_external",
            "description": "Send an email to a given recipient with a subject and message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "The recipient email address."
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line."
                    },
                    "body": {
                        "type": "string",
                        "description": "Body of the email message."
                    }
                },
                "required": [
                    "to",
                    "subject",
                    "body"
                ],
                "additionalProperties": False
            }
        }

        ],
        "tool_choice": "auto",
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send_json(session_update)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)