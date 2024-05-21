from dotenv import load_dotenv
from openai import OpenAI
from openai import AssistantEventHandler
from st_weaviate_connection import WeaviateConnection
from typing_extensions import override

import streamlit as st
import os

# Load environment variables
load_dotenv()
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
OPENAI_API_KEY = os.getenv('OPENAI_APIKEY', '')

# Initialize OpenAI and Weaviate connections
openai_client = OpenAI(api_key=OPENAI_API_KEY)
conn = WeaviateConnection("local_weaviate_connection", url=WEAVIATE_URL, additional_headers={})

# how we want to handle the events in the response stream
class Eventhandler(AssistantEventHandler):
    def __init__(self, placeholder, thread_id, assistant_id):
       super().__init__()
       self.output = None
       self.tool_id = None
       self.thread_id = thread_id
       self.assistant_id = assistant_id
       self.run_id = None
       self.run_step = None
       self.function_name = ""
       self.arguments = ""
       self.placeholder = placeholder
       self.full_text = ""

    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        if delta.value:
            self.full_text += delta.value
            self.placeholder.markdown(self.full_text)

    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "code_interpreter":
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)


st.title("🕵🏻 UPFree")
st.caption("🔍 Ontdek meer over ultrabewerkte voedingsmiddelen (UPF) en additieven in de voeding van Albert Heijn en maak gezondere voedingskeuzes.")

with st.expander("Wat is UPF (Ultra Processed Food)?"):
    st.write('''
        Ultrabewerkt voedsel is eten en drinken dat met meerdere industriële processen wordt geproduceerd. 
        Bovendien bevat het ingrediënten die je niet in je keuken thuis aantreft. 
        Voorbeelden van ultrabewerkt voedsel zijn supermarktbrood, zaadoliën, melkvervangers, ontbijtgranen, vleesvervangers en light-dranken.
             
        De GPT Assistant moet producten beoordelen op basis van de NOVA-richtlijn, die voedingsmiddelen indeelt in vier groepen:

        Groep 1: Onbewerkte of minimaal bewerkte voedingsmiddelen
        Groep 2: Verwerkte culinaire ingrediënten
        Groep 3: Bewerkte voedingsmiddelen
        Groep 4: Ultra bewerkte voedings- en drankproducten (meer dan 4 ingrediënten en/of ingrediënt wat niet in keukenkastje voorkomt)

        Om te bepalen of een product ultrabewerkt is, hanteert de Assistant de volgende criteria:

        Bevat het product vier of meer ingrediënten?
        Bevat het product een ingrediënt dat je niet herkent in je keukenkastje?.
    ''')
    st.link_button("Meer informatie over UPF", "https://www3.paho.org/hq/dmdocuments/2014/ultra-processed-foods-paho-e-obesity-latin-america-2014.pdf")

assistant_id = "asst_tAvsX37P7IO5uOPlhUHghwm5"

if "thread_id" not in st.session_state:
    thread = openai_client.beta.threads.create()
    st.session_state.thread_id = thread.id

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Goedendag! Hoe kan ik je helpen met informatie over voeding vandaag?"})

for messages in st.session_state.messages:
    with st.chat_message(messages["role"]):
        st.markdown(messages["content"])

# Example prompts
example_prompts = [
    "Welke plantaardige yoghurt is ultrabewerkt?",
    "Wat is maltodextrine en in welke producten zit het?",
    "Hoe bewerkt zijn proteïnerepen?",
]

example_prompts_help = [
    "Bekijk hoe plantaardige yoghurt scoort volgens de NOVA richtlijn",
    "Bekijk in welke producten deze toevoeging zit",
    "Bekijk een lijst aan proteïnerepen en zie de score volgens de NOVA richtlijn",
]

button_cols = st.columns(3)

button_pressed = ""

if button_cols[0].button(example_prompts[0], help=example_prompts_help[0]):
    button_pressed = example_prompts[0]
elif button_cols[1].button(example_prompts[1], help=example_prompts_help[1]):
    button_pressed = example_prompts[1]
elif button_cols[2].button(example_prompts[2], help=example_prompts_help[2]):
    button_pressed = example_prompts[2]

if prompt := (st.chat_input("Waar ben je naar op zoek?") or button_pressed):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)


    # GraphQL query setup
    query = prompt.strip().lower()
    results = conn.client().query.get(
        'Products',
        ['product_name',
         'product_description',
         'complete_ingredienten_text',
         'fat',
         'fat_saturated',
         'fat_unsaturated',
         'carbs',
         'sugars',
         'fibres',
         'kcal',
         'protein',
        ]
    ).with_hybrid(
        query=query
    ).with_additional(
        ["score", "explainScore"]
    ).with_limit(
        10
    ).do()

    if results and results.get('data', {}).get('Get', {}).get('Products'):
        product_list = [
            f"{product['product_name']} contains: {product['complete_ingredienten_text']}"
            for product in results['data']['Get']['Products']
        ]
        context_message = '\n'.join(product_list)
        instructions = f"""This the user prompt: {prompt}\n Use these results from the vector database for your answer: {context_message}.""" 
                        # Only answer when the retrieved information aligns with the question."""
        print(instructions)

    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id, 
        role="user", 
        content=prompt
    )

    with st.chat_message("assistant"):
        placeholder = st.empty()  # Placeholder to update the message
        event_handler = Eventhandler(placeholder, st.session_state.thread_id, assistant_id)

        with openai_client.beta.threads.runs.stream(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
            additional_instructions=instructions,
            event_handler=event_handler
        ) as stream:
            for _ in stream:
                pass

        # with openai_client.beta.threads.runs.stream(
        #     thread_id=st.session_state.thread_id,
        #     assistant_id=assistant_id,
        #     additional_instructions=instructions,
        # ) as stream:
        #         print(stream)
        #         response = st.write_stream(stream.text_deltas)
        #         stream.until_done()
        #         print(f"get_final_messages: {stream.get_final_messages()}")
        #         print(f"get_final_run_steps: {stream.get_final_run_steps}")
        #         print(f"get_final_run: {stream.get_final_run}")

    thread_messages = openai_client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
    message_value = thread_messages.data[0].content[0].text.value
    # message_value = thread_messages.data[0].content.text
    print(message_value)
        
    # Once the stream is over, update chat history
    st.session_state.messages.append({"role": "assistant", "content": event_handler.full_text})

    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id, 
        role="assistant", 
        content=event_handler.full_text
    )

        # for event in stream:
        #     if event.status == 'in_progress':
        #         delta = event['data']['delta']
        #         if 'content' in delta and delta['content']:
        #             for content in delta['content']:
        #                 if content['type'] == 'text':
        #                     event_handler.on_text_delta(content['text'], None)
        #     elif event.status == 'completed':
        #         st.session_state.messages.append({"role": "assistant", "content": event_handler.full_text})
        #         openai_client.beta.threads.messages.create(
        #             thread_id=st.session_state.thread_id, 
        #             role="assistant", 
        #             content=event_handler.full_text
        #         )
        #         break
        #     elif event.data == 'thread.message.created':
        #         event_handler.on_text_created(event['data']['content'])
        #     elif event.data == 'thread.run.completed':
        #         print("Run completed")