import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from llm import LlmClient
# from llm_with_func_calling import LlmClient
# from twilio_server import TwilioClient
# from twilio.twiml.voice_response import VoiceResponse
import asyncio
import retellclient
from retellclient.models import operations
import uuid
from datetime import datetime

load_dotenv()

app = FastAPI()
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, adjust this for production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
llm_client = LlmClient()
retell = retellclient.RetellClient(
    api_key=os.environ['RETELL_API_KEY'],
)
conversation = None
model = None
@app.post("/register-call")
async def register_call(request: Request):
    data = await request.json()
    agent_id = data.get("agentId")

    register_call_response = retell.register_call(operations.RegisterCallRequestBody(
        agent_id=agent_id,
        audio_websocket_protocol='web',
        audio_encoding='s16le',
        sample_rate=44000
    ))
    response = {
        "agentId": register_call_response.call_detail.agent_id,
        "callId": register_call_response.call_detail.call_id,
        "sampleRate": register_call_response.call_detail.sample_rate,
    }
    return response
@app.post("/update-model")
async def update_model(request: Request):
    global model
    data = await request.json()
    model = data.get("model")
    print(f'Model updated to {model}')
@app.websocket("/llm-websocket/{call_id}")
async def websocket_handler(websocket: WebSocket, call_id: str):
    global conversation
    global model
    await websocket.accept()
    # file_name = str(uuid.uuid4()) + ".txt"
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_name = f"{timestamp}.txt"

    print(f"Handle llm ws for: {call_id}")

    # send first message to signal ready of server
    response_id = 0
    first_event = llm_client.draft_begin_messsage()
    await websocket.send_text(json.dumps(first_event))

    async def stream_response(request):
        nonlocal response_id
        print(f"Getting stream response from {model}")
        for event in llm_client.draft_response(request, model, file_name):
            await websocket.send_text(json.dumps(event))
            if request['response_id'] < response_id:
                return # new response needed, abondon this one
    try:
        while True:
            message = await websocket.receive_text()
            request = json.loads(message)
            request['transcript']
            with open('conversation.txt','w') as file:
                file.write(json.dumps(request['transcript'], indent= 4))
            # print out transcript
            os.system('cls' if os.name == 'nt' else 'clear')
            print(json.dumps(request, indent=4))
            
            if 'response_id' not in request:
                continue # no response needed, process live transcript update if needed
            response_id = request['response_id']
            asyncio.create_task(stream_response(request))
            # print('I wanna print conversation', conversation)
    except WebSocketDisconnect:
        print(f"LLM WebSocket disconnected for {call_id}")
    except Exception as e:
        print(f'LLM WebSocket error for {call_id}: {e}')
    finally:
        print(f"LLM WebSocket connection closed for {call_id}")