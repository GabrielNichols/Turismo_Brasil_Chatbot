# 🗺️ Turismo Brasil Chatbot

Bem-vindo ao **Turismo Brasil Chatbot**, uma aplicação interativa que fornece informações personalizadas sobre destinos turísticos, gastronomia e cultura de diferentes regiões do Brasil. Utilizando modelos avançados de linguagem natural e várias tecnologias, este chatbot permite que os usuários explorem o Brasil de forma dinâmica e envolvente.

## 📖 Descrição do Projeto

### Objetivo

O objetivo deste projeto é desenvolver um chatbot capaz de interagir com os usuários e fornecer dicas personalizadas de viagens sobre diferentes regiões do Brasil. A aplicação visa auxiliar turistas e entusiastas a descobrir destinos, compreender aspectos culturais e conhecer a gastronomia brasileira, tudo através de uma interface web intuitiva.

### Funcionalidades

- **Interação Conversacional**: O chatbot responde a perguntas dos usuários sobre destinos turísticos, gastronomia e cultura.
- **Mapas Interativos**: Integração com o Leaflet.js para exibir mapas interativos dos locais pesquisados.
- **Geração de Descrições Turísticas**: Utiliza modelos de linguagem natural para gerar descrições concisas e informativas sobre os locais.
- **Busca e Processamento de Conteúdo**: Extrai informações relevantes da internet para enriquecer as respostas.

### Tecnologias Utilizadas

- **Python**: Linguagem principal de desenvolvimento.
- **Gradio**: Framework para criação de interfaces web interativas.
- **Flask**: Utilizado para servir o mapa interativo.
- **LangChain**: Biblioteca para trabalhar com modelos de linguagem natural.
- **OllamaLLM**: Integração com o modelo de linguagem **Llama3.2-3B**.
- **Hugging Face Hub**: Plataforma para modelos de inteligência artificial.
- **BeautifulSoup e Readability**: Para extração e processamento de conteúdo web.
- **Leaflet.js**: Biblioteca JavaScript para mapas interativos.
- **Docker**: Para containerização da aplicação (opcional).
- **Variáveis de Ambiente (.env)**: Gerenciamento seguro de tokens e credenciais.

---

## 🛠️ Instruções de Instalação

### Pré-requisitos

- **Python 3.12**
- **Git** (para clonar o repositório)
- **Virtualenv** (recomendado)
- **Ollama**: Certifique-se de que o Ollama está instalado em seu sistema. Instruções em [Ollama.ai](https://ollama.ai/).

### Passos de Instalação

1. **Clone o Repositório**

   ```bash
   git clone https://github.com/GabrielNichols/projeto_turismo
   cd turismo-brasil-chatbot
   ```

2. **Crie um Ambiente Virtual**

   ```bash
   python -m venv venv
   ```

3. **Ative o Ambiente Virtual**

   - No Windows:

     ```bash
     venv\Scripts\activate
     ```

   - No macOS/Linux:

     ```bash
     source venv/bin/activate
     ```

4. **Instale as Dependências**

   ```bash
   pip install -r requirements.txt
   ```

5. **Configure o Arquivo `.env`**

   Crie um arquivo `.env` na raiz do projeto e adicione o seu token do Hugging Face:

   ```env
   HUGGINGFACEHUB_API_TOKEN=seu_token_aqui
   ```

   **Nota**: O token é necessário para autenticar e utilizar os modelos do Hugging Face.

6. **Verifique a Instalação do Ollama**

   Certifique-se de que o modelo `llama3.2` está instalado no Ollama:

   ```bash
   ollama pull llama3.2
   ```

---

## 🚀 Como Executar o Chatbot

1. **Inicie a Aplicação**

   Com o ambiente virtual ativado e no diretório do projeto, execute:

   ```bash
   python main.py
   ```

2. **Acesse a Interface Web**

   Após iniciar a aplicação, abra o navegador e acesse:

   ```
   http://127.0.0.1:7860/
   ```

3. **Interaja com o Chatbot**

   - **Pesquisar um Local**: Digite o nome de um local brasileiro no campo "Digite o nome de um local" e clique em "Buscar".
   - **Visualizar o Mapa**: O mapa interativo será atualizado para o local pesquisado.
   - **Descrição Turística**: Uma descrição sobre o local será gerada e exibida.
   - **Conversar com o Chatbot**: Faça perguntas sobre o local, gastronomia ou cultura no campo "Sua pergunta" e receba respostas personalizadas.
   - **Limpar Conversa**: Use o botão "Limpar conversa" para reiniciar o diálogo.

---

## 🧠 Explicação Técnica

### Escolha do Modelo **Llama3.2-3B**

**Por que Llama3.2-3B?**

- **Desempenho e Eficiência**: Escolhi o modelo Llama3.2-3B por oferecer um bom equilíbrio entre desempenho e recursos computacionais necessários, tornando-o adequado para execução local.
- **Suporte ao Português**: Embora muitos modelos sejam treinados predominantemente em inglês, o Llama3.2-3B possui capacidade de compreensão e geração de texto em múltiplos idiomas, incluindo o português.
- **Disponibilidade Open-Source**: Disponível no Hugging Face, permitindo integração fácil e customização conforme necessário.
- **Flexibilidade**: Adequado para tarefas de geração de texto, respostas contextuais e manutenção de conversação.

### Implementação e Integração do Modelo

- **Integração com LangChain**: Utilizei o `OllamaLLM` do `langchain-ollama` para integrar o modelo Llama3.2-3B, permitindo chamadas simplificadas ao modelo dentro da estrutura do LangChain.
- **Configuração de Parâmetros**: Configurei parâmetros como temperatura, top_p e max_tokens para controlar o comportamento do modelo.
- **Encadeamento com Prompts Personalizados**: Usei `PromptTemplate` para criar prompts que orientam o modelo a gerar respostas relevantes e coerentes.

### Ajustes Finos (Temperatura, Max Tokens, etc.)

- **Temperatura**:

  - **Descrição**: Controla a aleatoriedade das respostas. Valores mais baixos resultam em respostas mais previsíveis.
  - **Aplicação**: Utilizei valores entre 0.3 e 0.7 para equilibrar a criatividade e a coerência das respostas.

- **Top_p**:

  - **Descrição**: Nucleus sampling; considera a probabilidade cumulativa dos tokens.
  - **Aplicação**: Defini valores como 0.9 para garantir que as respostas sejam relevantes sem sacrificar a diversidade.

- **Max_tokens**:

  - **Descrição**: Limita o número máximo de tokens na resposta gerada.
  - **Aplicação**: Estabeleci limites para evitar respostas muito longas e garantir tempos de resposta razoáveis.

**Como Melhoram a Relevância das Respostas?**

- **Controle de Coerência**: Ajustes na temperatura e top_p ajudam a manter as respostas focadas e relevantes ao contexto.
- **Limitação de Comprimento**: max_tokens garante que as respostas sejam concisas, melhorando a experiência do usuário.
- **Personalização**: Permite afinar o modelo para atender às necessidades específicas da aplicação, como estilo de linguagem e nível de detalhe.

### Limitações Atuais e Melhorias Futuras

**Limitações**:

- **Compreensão Limitada do Contexto Cultural Específico**: O modelo pode não capturar nuances culturais ou informações atualizadas sobre todos os destinos.
- **Dependência de Dados da Internet**: A extração de conteúdo da web pode trazer informações desatualizadas ou irrelevantes.
- **Capacidade Computacional**: Modelos grandes podem exigir recursos significativos, afetando a escalabilidade.

**Melhorias Futuras**:

- **Treinamento Personalizado**: Treinar o modelo com um conjunto de dados específico sobre turismo brasileiro para melhorar a precisão.
- **Atualização de Dados**: Implementar mecanismos para garantir que as informações estejam sempre atualizadas.
- **Integração com APIs Oficiais**: Utilizar dados oficiais de turismo para enriquecer as respostas.
- **Otimização de Performance**: Explorar técnicas de compressão ou modelos mais leves para melhorar a eficiência.

---

## 💡 Possíveis Melhorias Futuras

1. **Suporte Multilíngue**: Expandir o suporte para outros idiomas, atendendo a turistas estrangeiros.

2. **Integração com Redes Sociais**: Permitir interações via plataformas como WhatsApp, Telegram ou Facebook Messenger.

3. **Recomendações Personalizadas**: Implementar algoritmos que ofereçam sugestões baseadas nas preferências do usuário.

4. **Análise de Sentimento**: Utilizar modelos para compreender o humor do usuário e adaptar as respostas.

5. **Modo Offline**: Desenvolver uma versão que funcione sem conexão à internet, útil para áreas com conectividade limitada.

6. **Interface Mobile**: Criar aplicativos para dispositivos móveis, oferecendo maior acessibilidade.

---

## 📝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests no repositório do projeto.

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

Obrigado por utilizar o **Turismo Brasil Chatbot**! Espero que esta ferramenta enriqueça suas experiências e conhecimentos sobre as maravilhas do Brasil.