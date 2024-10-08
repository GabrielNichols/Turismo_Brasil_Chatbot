# app.py

import threading
import time
import gradio as gr
from flask import Flask, render_template_string
from config import memory
from utils import geocode_location, create_leaflet_map_html
from data_processing import extrair_contexto_e_salvar, get_context
import data_processing
from chatbot import responder_chatbot, gerar_descricao_turistica, get_conversation_chain

app = Flask(__name__)
map_html_content = ""

# Rota Flask para servir o mapa
@app.route("/map")
def serve_map():
    return render_template_string(map_html_content)

# Funções para o Gradio
def process_location(location_name):
    """Processa a localização fornecida, atualiza o mapa e gera a descrição turística."""
    global map_html_content
    latitude, longitude, geojson = geocode_location(location_name)
    if latitude is None or longitude is None:
        return None, "Local não encontrado. Por favor, tente novamente."

    map_html_content = create_leaflet_map_html(latitude, longitude, location_name, geojson)
    timestamp = int(time.time())
    iframe_html = f'<iframe src="http://127.0.0.1:5000/map?t={timestamp}" width="100%" height="500"></iframe>'

    # Extrair contexto e salvar no VectorStore (realizando buscas turísticas)
    extrair_contexto_e_salvar(location_name + " turismo")

    # Chamar a cadeia de conversação com o retriever atualizado
    get_conversation_chain(data_processing.retriever)

    # Recuperar contexto
    contexto_turistico = get_context("Brasil " + location_name + " Turismo")
    if not contexto_turistico:
        description = f"Principais atrações turísticas de {location_name} no Brasil. (Informações detalhadas não disponíveis)"
    else:
        # Gerar a descrição turística usando o LLM
        description = gerar_descricao_turistica(
            contexto_turistico,
            temperature=0.5,
            top_p=0.9,
            max_tokens=150
        )

    return iframe_html, description

def update_map(location_name):
    """Atualiza o mapa e a descrição com base na localização."""
    iframe_html, description = process_location(location_name)
    return iframe_html, description, location_name

def user(user_message, history):
    """Lida com a entrada do usuário no chat."""
    return "", history + [[user_message, None]]

def bot(history, location):
    """Gera a resposta do bot."""
    user_message = history[-1][0]
    bot_message = responder_chatbot(user_message, location)
    history[-1][1] = bot_message
    return history

def reset_memory():
    """Reseta a memória de conversação."""
    memory.clear()
    return None

# Interface Gradio
with gr.Blocks() as demo:
    gr.Markdown("# 🗺️ Aplicação de Turismo com Gradio, Leaflet e LLM")
    
    location_state = gr.State(value="")  # Estado para armazenar a localização atual

    with gr.Row():
        location_input = gr.Textbox(label="Digite o nome de um local", placeholder="Ex: Rio de Janeiro")
        search_button = gr.Button("Buscar")

    with gr.Row():
        # Inicializar o mapa com o contorno e ajuste de zoom do Brasil
        _, _, brasil_geojson = geocode_location("Brasil")
        map_html_content = create_leaflet_map_html(-14.2350, -51.9253, "Brasil", brasil_geojson)
        timestamp = int(time.time())
        iframe_html = f'<iframe src="http://127.0.0.1:5000/map?t={timestamp}" width="100%" height="500"></iframe>'
        map_output = gr.HTML(value=iframe_html)

    with gr.Row():
        description_output = gr.Textbox(label="Descrição Turística", lines=10)

    with gr.Row():
        chatbot = gr.Chatbot()
        msg = gr.Textbox(label="Sua pergunta", placeholder="Faça uma pergunta sobre a região")
        clear = gr.Button("Limpar conversa")

    # Conectar as funções aos componentes Gradio
    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, [chatbot, location_state], [chatbot]
    )
    clear.click(fn=reset_memory, inputs=None, outputs=chatbot, queue=False)

    # Conectar a função de processamento ao botão de busca
    search_button.click(
        fn=update_map,
        inputs=location_input,
        outputs=[map_output, description_output, location_state]
    )

# Iniciar o servidor Flask em uma thread separada
def start_flask_app():
    app.run(port=5000)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.start()
    demo.launch()
