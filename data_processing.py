# data_processing.py

import logging
import random
import time
import requests
from bs4 import BeautifulSoup
from readability import Document as ReadabilityDocument
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from config import embeddings
from utils import get_random_user_agent

logger = logging.getLogger(__name__)

vector_db = None
retriever = None

def search_duckduckgo_html(query, max_retries=5, num_results=15):
    """Realiza uma busca no DuckDuckGo e retorna os links dos resultados.

    Args:
        query (str): Termo de busca.
        max_retries (int): Número máximo de tentativas.
        num_results (int): Número de resultados a serem retornados.

    Returns:
        list: Lista de URLs encontradas.
    """
    base_url = 'https://html.duckduckgo.com/html/'
    params = {'q': query}
    headers = {'User-Agent': get_random_user_agent()}

    attempt = 0
    while attempt < max_retries:
        try:
            logger.debug(f"Iniciando conexão: {base_url}")
            response = requests.post(base_url, data=params, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            result_links = []

            for link in soup.find_all('a', href=True):
                url = link['href']
                if url.startswith('https://') or url.startswith('http://'):
                    result_links.append(url)

            unique_links = list(dict.fromkeys(result_links))
            top_links = unique_links[:num_results]

            if top_links:
                logger.debug(f"Links encontrados: {top_links}")
                return top_links
            else:
                logger.debug(f"Nenhum link encontrado para a query: '{query}'")
                return []
        except requests.exceptions.RequestException as e:
            wait_time = random.uniform(5, 15)
            logger.warning(f"Erro na conexão. Tentativa {attempt + 1} de {max_retries}. Esperando {wait_time:.2f} segundos.")
            time.sleep(wait_time)
            attempt += 1

    logger.error(f"Todas as tentativas falharam ao tentar buscar no DuckDuckGo após {max_retries} tentativas.")
    return []

def extract_content_bs4(url, max_chars=None):
    """Extrai o conteúdo principal de uma página web.

    Args:
        url (str): URL da página.
        max_chars (int, optional): Número máximo de caracteres a serem extraídos.

    Returns:
        str: Conteúdo extraído.
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

def prepare_and_split_docs(documentos):
    """Divide os documentos em chunks menores para processamento.

    Args:
        documentos (list): Lista de objetos Document.

    Returns:
        list: Lista de documentos divididos.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=256,
        separators=["\n\n", "\n", " "]
    )
    split_docs = splitter.split_documents(documentos)
    logger.info(f"Documentos foram divididos em {len(split_docs)} partes")
    return split_docs

def ingest_into_vectordb(split_docs):
    """Insere os documentos no banco de dados vetorial.

    Args:
        split_docs (list): Lista de documentos divididos.
    """
    global vector_db, retriever
    vector_db = FAISS.from_documents(split_docs, embeddings)
    retriever = vector_db.as_retriever(search_kwargs={"k": 2})
    logger.info("Documentos foram inseridos no banco de dados vetorial (FAISS)")

def get_context(localizacao):
    """Obtém o contexto para uma localização específica."""
    global retriever
    logger.debug(f"Buscando contexto no VectorStore para a localização: {localizacao}")
    if retriever is None:
        logger.debug("Retriever não está disponível.")
        return ""
    try:
        documentos = retriever.get_relevant_documents(localizacao)
        if documentos:
            logger.debug(f"Contexto encontrado para a localização: {localizacao}")
            conteudo_relevante = [doc.page_content for doc in documentos]
            conteudo = ' '.join(conteudo_relevante)
            conteudo = conteudo[:2000]
            return conteudo
        else:
            logger.debug(f"Nenhum contexto encontrado para a localização: {localizacao}")
            return ""
    except Exception as e:
        logger.error(f"Erro ao obter contexto: {e}")
        return ""

def extrair_contexto_e_salvar(localizacao):
    """Extrai contexto de uma localização e salva no banco vetorial.

    Args:
        localizacao (str): Nome da localização.
    """
    logger.debug(f"Extraindo contexto para a localização: {localizacao}")
    search_results = search_duckduckgo_html(localizacao, num_results=15)
    if search_results and isinstance(search_results, list):
        documentos = []
        for link in search_results:
            content = extract_content_bs4(link)
            if content:
                documentos.append(Document(page_content=content))
    
        if documentos:
            split_documentos = prepare_and_split_docs(documentos)
            ingest_into_vectordb(split_documentos)
            logger.debug(f"Contexto salvo no VectorStore para a localização: {localizacao}")
        else:
            logger.debug(f"Nenhum conteúdo encontrado para salvar para a localização: {localizacao}")
    else:
        logger.debug(f"Nenhum link encontrado para salvar para a localização: {localizacao}")
