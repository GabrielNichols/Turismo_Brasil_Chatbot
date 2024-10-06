import gradio as gr
import requests
import json
from flask import Flask, render_template_string
import threading
import time
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from vllm import LLM, SamplingParams
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import random

# Configuração do logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inicializar Elasticsearch
es = Elasticsearch("http://localhost:9200")

# Inicializar o Flask
app = Flask(__name__)

# Variável global para armazenar o HTML do mapa
map_html_content = ""

# Funções auxiliares

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def geocode_location(location_name):
    url = 'https://nominatim.openstreetmap.org/search'
    params = {
        'q': location_name,
        'format': 'json',
        'countrycodes': 'BR',  # Filtrar para mostrar somente no Brasil
        'limit': 1,  # Limitar o número de resultados a 1
        'polygon_geojson': 1,  # Incluir dados de polígono (GeoJSON)
    }
    response = requests.get(url, params=params, headers={'User-Agent': 'gradio-app'})
    if response.status_code == 200 and response.json():
        data = response.json()[0]
        latitude = float(data['lat'])
        longitude = float(data['lon'])
        geojson = data.get('geojson')
        return latitude, longitude, geojson
    else:
        return None, None, None


def create_leaflet_map_html(latitude, longitude, location_name="Brasil", geojson=None):
    # Criar um HTML que usa Leaflet.js para exibir o mapa
    geojson_layer = ""
    if geojson:
        geojson_layer = f"""
            var geojson = {json.dumps(geojson)};
            var geoLayer = L.geoJSON(geojson, {{
                style: function (feature) {{
                    return {{color: \"#0000FF\", weight: 2, fillOpacity: 0.2}};
                }}
            }}).addTo(map);
            map.fitBounds(geoLayer.getBounds());
        """

    map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mapa com Leaflet</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <style>
            #map {{
                height: 500px;
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([{latitude}, {longitude}], 6);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                maxZoom: 19,
                attribution: '© OpenStreetMap'
            }}).addTo(map);
            
            {geojson_layer}
        </script>
    </body>
    </html>
    """
    return map_html


@app.route("/map")
def serve_map():
    return render_template_string(map_html_content)

# Função para atualizar o mapa e a descrição
def process_location(location_name):
    global map_html_content
    # Geocodificação
    latitude, longitude, geojson = geocode_location(location_name)
    if latitude is None or longitude is None:
        return None, "Local não encontrado. Por favor, tente novamente."
    
    # Criação do mapa usando Leaflet e incluindo o polígono
    map_html_content = create_leaflet_map_html(latitude, longitude, location_name, geojson)
    
    # Gera a URL do iframe apontando para o Flask, adicionando um timestamp para evitar cache
    timestamp = int(time.time())
    iframe_html = f'<iframe src="http://127.0.0.1:5000/map?t={timestamp}" width="100%" height="500"></iframe>'
    
    return iframe_html, f"Principais atrações turísticas de {location_name} no Brasil."

# Função para recuperar contexto do Elasticsearch
def get_context(localizacao):
    logger.debug(f"Buscando contexto no Elasticsearch para a localização: {localizacao}")
    try:
        resultados_pesquisa = es.search(index="dados_turismo", query={"match": {"localizacao": localizacao}})
        if resultados_pesquisa['hits']['total']['value'] > 0:
            logger.debug(f"Contexto encontrado para a localização: {localizacao}")
            return ' '.join(hit["_source"]["conteudo"] for hit in resultados_pesquisa['hits']['hits'])
        else:
            logger.debug(f"Nenhum contexto encontrado para a localização: {localizacao}")
    except Exception as e:
        logger.error(f"Erro ao buscar contexto para a localização: {localizacao}. Erro: {e}")
    return ""

# Função do chatbot que utiliza vLLM ou Transformers para responder
def responder_chatbot(pergunta, localizacao):
    logger.debug(f"Gerando resposta para a pergunta: '{pergunta}' e localização: '{localizacao}'")
    contexto = get_context(localizacao)
    if not contexto:
        logger.warning("Contexto insuficiente para gerar resposta.")
        return "Desculpe, não consegui encontrar informações suficientes sobre esse local."

    # Tentativa de usar vLLM para gerar resposta com base no contexto recuperado
    try:
        model_name = "mistralai/Pixtral-12B-2409"
        sampling_params = SamplingParams(max_tokens=150, temperature=0.7)
        llm = LLM(model=model_name, tokenizer_mode="mistral", limit_mm_per_prompt={"image": 5}, max_model_len=32768)
        prompt = f"Você é um especialista em turismo. Responda a pergunta do usuário com base no contexto abaixo.\n\nContexto: {contexto}\n\nPergunta: {pergunta}\nResposta:"
        resposta = llm.chat(messages=[{"role": "user", "content": prompt}], sampling_params=sampling_params)[0].outputs[0].text
        logger.debug("Resposta gerada com sucesso usando vLLM.")
        return resposta
    except Exception as e:
        logger.error(f"Erro ao gerar resposta com vLLM. Erro: {e}")
        logger.info("Tentando usar modelo Transformers como fallback.")
    
    # Fallback para usar o modelo Transformers se vLLM falhar
    try:
        model_name = "pixtral-12b-2409"  # Usar o mesmo modelo
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        prompt = f"Você é um especialista em turismo. Responda a pergunta do usuário com base no contexto abaixo.\n\nContexto: {contexto}\n\nPergunta: {pergunta}\nResposta:"
        input_ids = tokenizer.encode(prompt, return_tensors='pt')
        output = model.generate(input_ids, max_length=150, temperature=0.7, do_sample=True)
        resposta = tokenizer.decode(output[0], skip_special_tokens=True)
        logger.debug("Resposta gerada com sucesso usando Transformers.")
        return resposta
    except Exception as e:
        logger.error(f"Erro ao gerar resposta com o modelo Transformers. Erro: {e}")
        return "Erro ao gerar resposta. Por favor, tente novamente mais tarde."

# Função para criar agentes usando LangGraph e realizar buscas paralelas
def criar_agentes_busca(localizacao, num_agentes=3):
    logger.debug(f"Criando {num_agentes} agentes para realizar buscas no SearXNG para a localização: '{localizacao}'")
    memory = MemorySaver()
    # Aqui substituímos o modelo vLLM pelo Transformers se necessário
    try:
        model = LLM(model="mistralai/Pixtral-12B-2409", tokenizer_mode="mistral", limit_mm_per_prompt={"image": 5}, max_model_len=32768)
    except Exception as e:
        logger.error(f"Erro ao inicializar vLLM. Usando Transformers como fallback. Erro: {e}")
        model_name = "pixtral-12b-2409"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
    # Aqui substituímos o TavilySearchResults por uma função de busca personalizada
    agentes = []
    for _ in range(num_agentes):
        agente = create_react_agent(model, [buscar_searx], checkpointer=memory)
        agentes.append(agente)
    return agentes

# Função para realizar busca no SearXNG
def buscar_searx(query):
    logger.debug(f"Iniciando busca no SearXNG para a query: '{query}'")
    url_instancia = 'https://searx.org/search'
    params = {
        'q': query,
        'format': 'json',
        'categories': 'general',
        'safesearch': 1
    }
    headers = {
        'User-Agent': get_random_user_agent()
    }
    resposta = requests.get(url_instancia, params=params, headers=headers)
    if resposta.status_code == 200:
        logger.debug("Busca realizada com sucesso.")
    else:
        logger.error(f"Erro na busca SearXNG. Status code: {resposta.status_code}")
    resultados = resposta.json().get('results', []) if resposta.status_code == 200 else []
    conteudos_extraidos = []
    for resultado in resultados:
        url = resultado.get('url')
        if url:
            conteudo = extrair_conteudo(url)
            if conteudo:
                conteudos_extraidos.append(conteudo)
    return conteudos_extraidos

# Função para realizar scraping dos resultados com BeautifulSoup
def extrair_conteudo(url):
    logger.debug(f"Iniciando extração de conteúdo da URL: {url}")
    try:
        resposta = requests.get(url, headers={'User-Agent': get_random_user_agent()}, timeout=10)
        soup = BeautifulSoup(resposta.content, 'html.parser')
        paragrafos = soup.find_all('p')
        conteudo = ' '.join(p.text for p in paragrafos)
        logger.debug(f"Conteúdo extraído com sucesso da URL: {url}")
        return conteudo
    except Exception as e:
        logger.error(f"Erro ao extrair conteúdo da URL: {url}. Erro: {e}")
        return ""

# Construção da interface
with gr.Blocks() as demo:
    gr.Markdown("# 🗺️ Aplicação de Turismo com Gradio, Leaflet e LLM")
    
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
        user_question = gr.Textbox(label="Faça uma pergunta sobre a região", placeholder="Ex: Quais são as melhores atrações no Rio de Janeiro?")
        response_output = gr.Textbox(label="Resposta do Chatbot", lines=5)
        ask_button = gr.Button("Perguntar")
    
    # Conectar a função de processamento ao botão de busca
    def update_map(location_name):
        iframe_html, description = process_location(location_name)
        return iframe_html, description

    search_button.click(
        fn=update_map,
        inputs=location_input,
        outputs=[map_output, description_output]
    )

    # Conectar a função do chatbot ao botão de perguntar
    ask_button.click(
        fn=responder_chatbot,
        inputs=[user_question, location_input],
        outputs=response_output
    )

# Função para iniciar o servidor Flask em uma thread separada
def start_flask_app():
    app.run