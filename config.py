# config.py

import os
import logging
from dotenv import load_dotenv
from huggingface_hub import login
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain_ollama.llms import OllamaLLM

# Configurar o logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Obter o token da variável de ambiente
huggingface_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

if huggingface_token:
    # Use seu token para se autenticar
    login(token=huggingface_token)
    os.environ["HUGGINGFACE_TOKEN"] = huggingface_token
else:
    raise ValueError("HUGGINGFACEHUB_API_TOKEN não encontrado no arquivo .env")

# Configurar embeddings
embedding_model = 'sentence-transformers/all-MiniLM-L6-v2'
embeddings = HuggingFaceEmbeddings(model_name=embedding_model)

# Inicializar o LLM do Ollama
llm_model = "llama3.2"  # Certifique-se de que este modelo está disponível no Ollama
llm = OllamaLLM(model=llm_model)

# Configurar memória de conversação
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
