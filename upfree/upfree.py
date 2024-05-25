from openai import OpenAI, AssistantEventHandler, APIConnectionError, APIError
from openai.types.beta.threads import Text, TextDelta
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from st_weaviate_connection import WeaviateConnection
from typing_extensions import override

import streamlit as st
import os
import sys
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'http://weaviate:8080')
OPENAI_API_KEY = os.getenv('OPENAI_APIKEY')
version_number = "0.2.0"

# Ensure the API key is set
if not OPENAI_API_KEY:
    print("Error: OPENAI_APIKEY environment variable is not set.")
    sys.exit(1)

# Initialize OpenAI and Weaviate connections
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    conn = WeaviateConnection("local_weaviate_connection", url=WEAVIATE_URL, additional_headers={})
except APIConnectionError as e:
    print(f"API Connection Error: {e}")
    sys.exit(1)

# Function to perform Weaviate query
def query_weaviate(prompt):
    query = prompt.strip().lower()
    results = conn.client().query.get(
        'Products',
        [
            'product_name',
            'product_description',
            'complete_ingredienten_text',
            'breadcrumb_5',
            'breadcrumb_6',
            'fat',
            'fat_saturated',
            'fat_unsaturated',
            'carbs',
            'sugars',
            'fibres',
            'kcal',
            'protein',
        ]
    ).with_hybrid(query=query).with_additional(["score", "explainScore"]).with_limit(6).do()
    
    if results and results.get('data', {}).get('Get', {}).get('Products'):
        product_list = [
            f"**{product['product_name']}**\n"
            f"Description: {product.get('product_description', 'N/A')}\n"
            f"Ingredients: {product.get('complete_ingredienten_text', 'N/A')}\n"
            f"Category: {product.get('breadcrumb_5', 'N/A')} - {product.get('breadcrumb_6', 'N/A')}\n"
            f"Fat: {product.get('fat', 'N/A')}g\n"
            f"Saturated Fat: {product.get('fat_saturated', 'N/A')}g\n"
            f"Unsaturated Fat: {product.get('fat_unsaturated', 'N/A')}g\n"
            f"Carbs: {product.get('carbs', 'N/A')}g\n"
            f"Sugars: {product.get('sugars', 'N/A')}g\n"
            f"Fibres: {product.get('fibres', 'N/A')}g\n"
            f"Calories: {product.get('kcal', 'N/A')} kcal\n"
            f"Protein: {product.get('protein', 'N/A')}g\n"
            for product in results['data']['Get']['Products']
        ]
        return '\n'.join(product_list)
    return "No products found."

# Define the EventHandler class to handle the events in the response stream
class EventHandler(AssistantEventHandler):
    def __init__(self, placeholder, thread_id, assistant_id):
        super().__init__()
        self.output = None
        self.thread_id = thread_id
        self.assistant_id = assistant_id
        self.run_id = None
        self.placeholder = placeholder
        self.full_text = ""

    @override
    def on_text_created(self, text: Text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta: TextDelta, snapshot: Text):
        print(delta.value, end="", flush=True)
        if delta.value:
            self.full_text += delta.value
            self.placeholder.markdown(self.full_text)

    @override
    def on_tool_call_created(self, tool_call: ToolCall):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    @override
    def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall):
        if delta.type == "function_call" and delta.function_call:
            if delta.function_call.input:
                print(delta.function_call.input, end="", flush=True)
            if delta.function_call.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.function_call.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)
                        self.tool_output += output.logs  # Store tool output separately
                        # self.full_text += output.logs  # Update full_text with tool output

    @override
    def on_event(self, event):
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id  # Retrieve the run ID from the event data
            self.handle_requires_action(event.data, run_id)

    def handle_requires_action(self, data, run_id):
        tool_outputs = []
        
        for tool in data.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "query_weaviate":
                arguments = json.loads(tool.function.arguments)
                result = query_weaviate(arguments["prompt"])
                tool_outputs.append({"tool_call_id": tool.id, "output": result})
                # self.full_text += result  # Update full_text with tool output
                print(result)
        
        self.submit_tool_outputs(tool_outputs, run_id)
        
    def submit_tool_outputs(self, tool_outputs, run_id):
        with openai_client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(self.placeholder, self.thread_id, self.assistant_id),
        ) as stream:
            for text in stream.text_deltas:
                # print(text, end="", flush=True)
                if text:
                    self.full_text += text
            # print()

# Streamlit UI
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


with st.sidebar:
    st.title("🕵🏻 UPFree")
    st.markdown("""
        UPFree is gebouwd met [Streamlit](https://streamlit.io/) en [Weaviate](https://weaviate.io/) om te zoeken in ingrediëntenlijsten van [Albert Heijn](https://ah.nl/) producten.

        ⚠️ Disclaimer ⚠️ Het is nog in beta testing, wat inhoudt dat er foutjes kunnen optreden. Zo is bekend dat door de hoeveelheid informatie die de bot gepresenteerd krijgt ervoor kan zorgen
        dat deze 'hallicuneert' (i.c. antwoorden bedenkt of vergeet). Dubbel-check daarom altijd de informatie die je krijgt."""
    )
    st.title("Over de maker")
    st.markdown(    
        """ Hallo! 👋🏻 Ik ben Thomas, Data-Engineer bij [D-Data](https://d-data.nl/). Benieuwd naar hoe ik deze app heb gemaakt? Stuur me gerust een berichtje via LinkedIn."""
    )
    st.markdown(f'<a href="{"https://www.linkedin.com/in/thomas-benard/"}" target="_blank"><img src="{"https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Bug.svg.original.svg"}" width="50" /></a>', unsafe_allow_html=True)
    
    st.write(f"📱 Version: :grey[{version_number}]")

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

    # Add message to thread
    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )

    # Initiate the run
    try:
        with st.spinner('UPFree is aan het antwoorden...'):
            with st.chat_message("assistant"):
                placeholder = st.empty()  # Placeholder to update the message
                event_handler = EventHandler(placeholder, st.session_state.thread_id, assistant_id)

                with openai_client.beta.threads.runs.stream(
                    thread_id=st.session_state.thread_id,
                    assistant_id=assistant_id,
                    event_handler=event_handler
                ) as stream:
                    for _ in stream:
                        pass

        # Ensure `event_handler.full_text` is not empty before creating the assistant message
        if event_handler.full_text:
            st.session_state.messages.append({"role": "assistant", "content": event_handler.full_text})

            openai_client.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="assistant",
                content=event_handler.full_text
            )
        else:
            st.write("Error: De chatbot is even sprakeloos. Ververs de pagina of probeer het later nog een keer.")
    except APIError as e:
        st.write("Error: De chatbot heeft het even te druk! Ververs de pagina of probeer het later nog een keer.")
        print(f"APIError: {e}")
