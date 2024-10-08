# utils.py

import random
import requests
import json
import logging

logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) '
    'Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 '
    '(KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

def get_random_user_agent():
    """Retorna um user agent aleatório."""
    return random.choice(USER_AGENTS)

def geocode_location(location_name):
    """Realiza geocodificação de um local para obter latitude, longitude e geojson.

    Args:
        location_name (str): Nome do local.

    Returns:
        tuple: (latitude, longitude, geojson) ou (None, None, None) se não encontrado.
    """
    url = 'https://nominatim.openstreetmap.org/search'
    params = {
        'q': location_name,
        'format': 'json',
        'countrycodes': 'BR',
        'limit': 1,
        'polygon_geojson': 1,
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
    """Cria o HTML para exibir um mapa com Leaflet.js.

    Args:
        latitude (float): Latitude do centro do mapa.
        longitude (float): Longitude do centro do mapa.
        location_name (str): Nome do local.
        geojson (dict): Dados geojson do local.

    Returns:
        str: HTML do mapa.
    """
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
