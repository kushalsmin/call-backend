from openai import OpenAI
import retellclient
import os, json
from groq import Groq
from prompts import PROMPT, START
from dotenv import load_dotenv
load_dotenv()
beginSentence = START
import uuid
class LlmClient:
    def __init__(self):
        self.retell = retellclient.RetellClient(
            api_key=os.environ['RETELL_API_KEY'],
        )
        self.model = 'gpt-4-1106-preview'
        self.persona = 'Product Manager'
        self.persona_name = 'Taha'
        self.conversation_tone = 'Witty and Cheerful'
        self.big_five_traits = 'To the point, Competent, Empathetic'
        self.organization_name = 'Hersheys'
        self.organization_facts = ""
        self.objective_context = f'As a {self.persona} you want to know various things about how the user is using or not using the product to improve it.'
        self.objective = '''-Understand from user their consumption habits and patterns of sugar and sugar based products
-Probe further to understand comfort, satisfaction, guilt and other emotions the user associates with sweet consumption.
-Ask if the user had a magic wand, what features would they like in a sweet based product. 
-Ask for examples in followup to the user’s answers associated with habits and emotions. '''
        self.task = 'get actionable advice'
        self.customer_name = 'Kushal'
        self.additional_info = '''Supporting Campaign Documents:
-Sweet revolution is a confectionary brand which sells low calorie savouries, chocolates and cakes. (Stevia based)

• Collect feedback on taste, usability, and overall satisfaction.
•If the user prefers low carb saviouries, provide a clear call-to-action to visit the website for for placing the order.(abc.xyz)'''
        self.section_separator = '=='*5
        self.heading_separator = '--'*5
    def draft_begin_messsage(self):
        return {
            "response_id": 0,
            "content": beginSentence,
            "content_complete": True,
            "end_call": False,
        }
    
    def convert_transcript_to_openai_messages(self, transcript):
        messages = []
        for utterance in transcript:
            if utterance["role"] == "agent":
                messages.append({
                    "role": "assistant",
                    "content": utterance['content']
                })
            else:
                messages.append({
                    "role": "user",
                    "content": utterance['content']
                })
        return messages

    def get_single_prompt(self, messages , length):
        return PROMPT.format(
            persona = self.persona,
            persona_name = self.persona_name,
            customer_name = self.customer_name,
            organization_name = self.organization_name,
            section_separator = self.section_separator,
            heading_separator = self.heading_separator,
            objective = self.objective,
            organization_facts = self.organization_facts,
            information_n_instructions = "",
            conversation = messages,
            conversation_tone = self.conversation_tone,
            total_messages_exchanged = length,
            big_five_traits = self.big_five_traits,
            additional_info = self.additional_info,
        )

    def save_conversation(self, conversation, file_name):
        conversation_json = json.dumps(conversation, indent=4)
        
        # Write conversation JSON to file
        with open(file_name, 'w') as file:
            file.write(conversation_json)

        print(f"Conversation saved to {file_name}")
    def prepare_prompt(self, request, file_name):
        transcript_messages = self.convert_transcript_to_openai_messages(request['transcript'])
        prompt = [{
            "role": "system",
            "content": self.get_single_prompt(messages=transcript_messages, length=len(transcript_messages))
        }]
        prompt += transcript_messages
        # for message in transcript_messages:
        #     prompt.append(message)
        self.save_conversation(transcript_messages, file_name)
        if request['interaction_type'] == "reminder_required":
            prompt.append({
                "role": "user",
                "content": "(Now the user has not responded in a while, you would say:)",
            })
        return prompt

    def draft_response(self, request, model, file_name):      
        prompt = self.prepare_prompt(request, file_name)
        if model == 'gpt-4-1106-preview':
            self.client = OpenAI()
            stream = self.client.chat.completions.create(
            model=model,
            messages=prompt,
            stream=True,
        )
        elif model == 'gpt-3.5-turbo-0125':
            self.client = OpenAI()
            stream = self.client.chat.completions.create(
            model=model,
            messages=prompt,
            stream=True,
        )
        elif model == 'mixtral-8x7b-32768':
            self.client = Groq(api_key=os.environ['GROQ_API_KEY'])
            stream = self.client.chat.completions.create(
                model=model,
                messages=prompt,
                stream=True,
            )
        
        else:
            print(f'Incorrect model given {model}')

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield {
                    "response_id": request['response_id'],
                    "content": chunk.choices[0].delta.content,
                    "content_complete": False,
                    "end_call": False,
                }
        
        yield {
            "response_id": request['response_id'],
            "content": "",
            "content_complete": True,
            "end_call": False,
        }
