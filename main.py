import gradio as gr
import requests
import json
from flask import Flask, render_template_string
import threading
import time
from bs4 import BeautifulSoup
import logging
import random
from langchain_core.documents import Document
import os
from huggingface_hub import login
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama.llms import OllamaLLM
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document
from readability import Document as ReadabilityDocument
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("transformers").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Obter o token da variável de ambiente
huggingface_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Verificar se o token foi carregado
if huggingface_token:
    # Use seu token para se autenticar
    login(token=huggingface_token)
    os.environ["HUGGINGFACE_TOKEN"] = huggingface_token
else:
    raise ValueError("HUGGINGFACEHUB_API_TOKEN não encontrado no arquivo .env")

# Inicializar o Flask
app = Flask(__name__)

# Variável global para armazenar o HTML do mapa
map_html_content = ""

# Configurar embeddings e inicializar vector_db como None
embedding_model = 'sentence-transformers/all-MiniLM-L6-v2'
embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
vector_db = None  # Inicialmente vazio
retriever = None  # Inicialmente vazio

# Inicializar o LLM do Ollama usando langchain-ollama
llm_model = "llama3.2"  # Certifique-se de que este modelo está disponível no Ollama
llm = OllamaLLM(model=llm_model)

# Configurar memória e cadeia de conversação (inicialmente vazia)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
conversation_chain = None  # Será inicializada após a ingestão dos documentos

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

# Função para atualizar o mapa e a descrição turística
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

    # Extrair contexto e salvar no VectorStore (realizando buscas turísticas)
    extrair_contexto_e_salvar(location_name + " turismo")

    # Recuperar contexto
    contexto_turistico = get_context("Brasil "+ location_name + " Turismo")
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

def gerar_descricao_turistica(contexto, temperature=0.3, top_p=0.9, max_tokens=150):
    prompt = PromptTemplate(
        input_variables=["context"],
        template="""
        Você é um especialista em turismo brasileiro.
        Por favor, escreva uma descrição turística **concisa e direta** com base nas informações abaixo (lembrando que as infromações podem estar bagunçadas e você deve responder só para localizções brasileiras):

        {context}

        A descrição deve ser em português e destacar as principais atrações turísticas, pontos de interesse e aspectos culturais do local, em um texto curto e objetivo.
        """
    )

    # Criar uma instância do LLM com os parâmetros desejados
    llm_custom = OllamaLLM(
        model=llm_model,
        request_params={
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }
    )

    # Encadear o prompt com o LLM usando o operador '|'
    chain = prompt | llm_custom

    # Invocar a cadeia com o contexto
    resposta = chain.invoke({"context": contexto})
    return resposta.strip()


def get_context(localizacao):
    global retriever
    logger.debug(f"Buscando contexto no VectorStore para a localização: {localizacao}")
    if retriever is None:
        logger.debug("Retriever não está disponível.")
        return ""
    documentos = retriever.get_relevant_documents(localizacao)
    if documentos:
        logger.debug(f"Contexto encontrado para a localização: {localizacao}")
        conteudo_relevante = []
        for doc in documentos:
            conteudo_relevante.append(doc.page_content)
        conteudo = ' '.join(conteudo_relevante)
        # Limitar o contexto a um número adequado de caracteres
        conteudo = conteudo[:2000]
        return conteudo
    else:
        logger.debug(f"Nenhum contexto encontrado para a localização: {localizacao}")
        return ""

def prepare_and_split_docs(documentos):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=256,
        separators=["\n\n", "\n", " "]
    )
    split_docs = splitter.split_documents(documentos)
    print(f"Documentos foram divididos em {len(split_docs)} partes")
    return split_docs

def ingest_into_vectordb(split_docs):
    global vector_db, retriever
    vector_db = FAISS.from_documents(split_docs, embeddings)
    retriever = vector_db.as_retriever(search_kwargs={"k": 2})
    print("Documentos foram inseridos no banco de dados vetorial (FAISS)")


def get_conversation_chain():
    global conversation_chain, retriever, memory
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
        Você é um especialista em turismo brasileiro. Use o contexto abaixo para responder à pergunta de forma detalhada, em português, e de maneira envolvente.

        Contexto:
        {context}

        Pergunta:
        {question}

        Resposta:
        """
    )
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={'prompt': prompt},
        verbose=True
    )
    print("Cadeia de conversação criada")


def extrair_contexto_e_salvar(localizacao):
    logger.debug(f"Extraindo contexto para a localização: {localizacao}")
    search_results = search_duckduckgo_html(localizacao, num_results=15)
    if search_results and isinstance(search_results, list):
        documentos = []
        for link in search_results:
            content = extract_content_bs4(link)
            if content:
                documentos.append(Document(page_content=content))
        
        if documentos:
            # Preparar e dividir documentos
            split_documentos = prepare_and_split_docs(documentos)
            # Ingerir no FAISS
            ingest_into_vectordb(split_documentos)
            # Atualizar a cadeia de conversação
            get_conversation_chain()
            logger.debug(f"Contexto salvo no VectorStore para a localização: {localizacao}")
        else:
            logger.debug(f"Nenhum conteúdo encontrado para salvar para a localização: {localizacao}")
    else:
        logger.debug(f"Nenhum link encontrado para salvar para a localização: {localizacao}")

def responder_chatbot(pergunta, localizacao):
    logger.debug(f"Gerando resposta para a pergunta: '{pergunta}' e localização: '{localizacao}'")

    if conversation_chain is None:
        logger.debug("Cadeia de conversação não está disponível.")
        return "Desculpe, não tenho informações suficientes para responder a essa pergunta no momento."

    # Atualizar a pergunta com a localização
    pergunta_com_localizacao = f"{pergunta} em {localizacao}"

    # Gerar resposta usando a cadeia
    response = conversation_chain({"question": pergunta_com_localizacao})

    logger.debug(f"Resposta gerada: {response['answer']}")
    return response['answer'].strip()

# Função para realizar a busca no DuckDuckGo diretamente pelo HTML da página
def search_duckduckgo_html(query, max_retries=5, num_results=15):
    """
    Realiza uma busca no DuckDuckGo diretamente pelo HTML da página e extrai os links dos resultados,
    retornando no máximo 10 URLs únicas e relevantes.
    """
    base_url = 'https://html.duckduckgo.com/html/'
    params = {
        'q': query,
    }

    headers = {
        'User-Agent': get_random_user_agent(),
    }

    attempt = 0
    while attempt < max_retries:
        try:
            logger.debug(f"Iniciando conexão: {base_url}")
            response = requests.post(base_url, data=params, headers=headers, timeout=10)
            response.raise_for_status()  # Verificar se a resposta é 200

            # Usando BeautifulSoup para analisar o HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            result_links = []

            # Procurando por todos os links dentro das tags de resultados da pesquisa
            for link in soup.find_all('a', href=True):
                url = link['href']
                if url.startswith('https://') or url.startswith('http://'):
                    result_links.append(url)

            # Filtrar URLs únicas e manter apenas os top 10 resultados
            unique_links = list(dict.fromkeys(result_links))  # Remove URLs duplicadas mantendo a ordem
            top_links = unique_links[:num_results]  # Pega apenas os 10 primeiros links

            if top_links:
                logger.debug(f"Top 10 links encontrados: {top_links}")
                return top_links
            else:
                logger.debug(f"Nenhum link encontrado para a query: '{query}'")
                return []

        except requests.exceptions.RequestException as e:
            if "Ratelimit" in str(e) or "202" in str(e):
                wait_time = random.uniform(5, 15)
                logger.warning(f"Rate limit excedido. Tentativa {attempt + 1} de {max_retries}. Esperando {wait_time:.2f} segundos antes de tentar novamente.")
                time.sleep(wait_time)
                attempt += 1
            else:
                logger.error(f"Erro ao realizar a busca no DuckDuckGo. Erro: {e}")
                return []

    logger.error(f"Todas as tentativas falharam ao tentar buscar no DuckDuckGo após {max_retries} tentativas.")
    return []

# Função para extrair o conteúdo usando BeautifulSoup
def extract_content_bs4(url, max_chars=None):
    """
    Extrai o conteúdo principal de uma página utilizando Readability e BeautifulSoup.
    """
    logger.debug(f"Iniciando extração de conteúdo da URL: {url}")
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://duckduckgo.com/',
            'Connection': 'keep-alive'
        }
        resposta = requests.get(url, headers=headers, timeout=10)
        resposta.raise_for_status()
        doc = ReadabilityDocument(resposta.text)
        html = doc.summary()
        soup = BeautifulSoup(html, 'html.parser')
        conteudo = soup.get_text(separator=' ', strip=True)
        if max_chars:
            conteudo = conteudo[:max_chars] + "..." if len(conteudo) > max_chars else conteudo
        logger.debug(f"Conteúdo extraído com sucesso da URL: {url}")
        return conteudo
    except Exception as e:
        logger.error(f"Erro ao extrair conteúdo da URL: {url}. Erro: {e}")
        return ""

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

    # Função para lidar com a entrada do usuário
    def user(user_message, history):
        return "", history + [[user_message, None]]

    # Função para gerar a resposta do bot
    def bot(history, location):
        user_message = history[-1][0]
        bot_message = responder_chatbot(user_message, location)
        history[-1][1] = bot_message
        return history
    
    def reset_memory():
        global memory
        memory.clear()
        return None

    # Conectar as funções aos componentes Gradio
    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, [chatbot, location_state], [chatbot]
    )
    clear.click(fn=reset_memory, inputs=None, outputs=chatbot, queue=False)

    # Conectar a função de processamento ao botão de busca
    def update_map(location_name):
        iframe_html, description = process_location(location_name)
        return iframe_html, description, location_name  # Retorna a localização para atualizar o estado

    search_button.click(
        fn=update_map,
        inputs=location_input,
        outputs=[map_output, description_output, location_state]
    )


# Função para iniciar o servidor Flask em uma thread separada
def start_flask_app():
    app.run(port=5000)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.start()
    demo.launch()