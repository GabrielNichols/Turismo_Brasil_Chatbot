# chatbot.py

import logging
from langchain.prompts import PromptTemplate
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from config import llm, memory
from langchain_ollama.llms import OllamaLLM

logger = logging.getLogger(__name__)

conversation_chain = None  # Será inicializada após a ingestão dos documentos

def get_conversation_chain(retriever):
    """Cria a cadeia de conversação utilizando o retriever fornecido."""
    global conversation_chain
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
        Você é um especialista em turismo brasileiro com profundo conhecimento sobre destinos, gastronomia e cultura. Utilize o contexto fornecido para responder de forma detalhada, precisa e envolvente às perguntas dos usuários.

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
    logger.info("Cadeia de conversação criada")

def responder_chatbot(pergunta, localizacao):
    """Gera uma resposta para a pergunta do usuário."""
    logger.debug(f"Gerando resposta para a pergunta: '{pergunta}' e localização: '{localizacao}'")

    if conversation_chain is None:
        logger.debug("Cadeia de conversação não está disponível.")
        return "Desculpe, não tenho informações suficientes para responder a essa pergunta no momento."

    # Atualizar a pergunta com a localização
    pergunta_com_localizacao = f"{pergunta} em {localizacao}"

    try:
        # Gerar resposta usando a cadeia
        response = conversation_chain({"question": pergunta_com_localizacao})
        resposta = response.get("answer", "Desculpe, não consegui gerar uma resposta adequada.")
        logger.debug(f"Resposta gerada: {resposta}")
        return resposta.strip()
    except Exception as e:
        logger.error(f"Erro ao gerar resposta do chatbot: {e}")
        return "Desculpe, ocorreu um erro ao processar sua pergunta."

def gerar_descricao_turistica(contexto, temperature=0.3, top_p=0.9, max_tokens=150):
    """Gera uma descrição turística baseada no contexto fornecido."""
    prompt = PromptTemplate(
        input_variables=["context"],
        template="""
        Você é um especialista em turismo brasileiro com amplo conhecimento sobre destinos, gastronomia e cultura. Utilize as informações fornecidas abaixo para escrever uma descrição turística concisa e direta.

        {context}

        Instruções:
        - Mantenha a descrição em português.
        - Destaque as principais atrações turísticas, pontos de interesse, aspectos culturais e opções gastronômicas.
        - Seja claro, objetivo e evite jargões técnicos.
        - Limite a descrição a um texto curto e objetivo, sem perder a riqueza das informações.

        Resposta:
        """
    )

    # Criar uma nova instância do LLM com os parâmetros desejados
    llm_custom = OllamaLLM(
        model=llm.model,  # Acessa o modelo da instância original
        request_params={
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }
    )

    # Encadear o prompt com o LLM usando o operador '|'
    chain = prompt | llm_custom

    try:
        # Invocar a cadeia com o contexto
        resposta = chain.invoke({"context": contexto})
        logger.debug(f"Descrição turística gerada: {resposta}")
        return resposta.strip()
    except Exception as e:
        logger.error(f"Erro ao gerar descrição turística: {e}")
        return "Desculpe, ocorreu um erro ao gerar a descrição turística."
