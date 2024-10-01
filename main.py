import gradio as gr
import requests
import json
from flask import Flask, render_template_string
import threading
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Inicializar o Flask
app = Flask(__name__)

# Variável global para armazenar o HTML do mapa
map_html_content = ""

# Carregar o modelo de linguagem da Hugging Face
model_name = "distilgpt2"  # Modelo leve para demonstração, pode ser substituído por outro mais apropriado
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Funções auxiliares
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
                    return {{color: "#0000FF", weight: 2, fillOpacity: 0.2}};
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

# Função para gerar a resposta do chatbot usando o modelo de linguagem
def chatbot_response(user_input):
    input_ids = tokenizer.encode(user_input, return_tensors='pt')
    output = model.generate(input_ids, max_length=150, temperature=0.7, do_sample=True)
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    return response

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
        fn=chatbot_response,
        inputs=user_question,
        outputs=response_output
    )

# Função para iniciar o servidor Flask em uma thread separada
def start_flask_app():
    app.run(port=5000)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.start()
    demo.launch()
