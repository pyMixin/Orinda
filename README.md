![Alt text](https://github.com/pyMixin/Orinda/blob/main/ORINDA.png)

# Orinda Installation Guide

## Step # 1: Download Ollama (Local LLM)
- https://ollama.com/download
- Once install open terminal or command line on your OS and type
```
ollama pull llama3:latest
ollama pull llama3.2:latest
ollama pull nomic-embed-text:latest
```
- Now, ollama is ready to be used by Orinda application.

## Step # 2: 

### Instructions for Mac OSX

**Prerequisite**
- Ensures Python 3.8+ is installed
- Ollama is installed, models have been download and Ollama is started.

**Steps**
- Download all the files in the GitHub Repository
- Create a new folder in Downloads > Folder: Orinda
- Open terminal
- Change Directory to Orinda in Downloads. 
- Create virtual environment
```
python3 -m venv orinda
source orinda/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```
- Launch Orinda: python main.py 

### Instructions for Windows
**Automatic Installation (Windows)**
- Download this repository
- Run install_orinda.bat as administrator
- Follow the on-screen instructions
- After installation, run run_orinda.bat to start the application

# Solution Design for Orinda

## Architecture Overview

The application follows a modular design with two main components:
1. **LLM Chat Tab** - Direct interaction with local LLMs via Ollama
2. **RAG Tab** - Enhanced document-based responses using vector databases

### Core Technologies and Libraries

- **UI Framework**: Tkinter for cross-platform GUI
- **LLM Interface**: Ollama for local model hosting and inference
- **Vector Database**: ChromaDB for efficient document embedding storage
- **Document Processing**: LangChain for document loading and chunking
- **Embedding Generation**: Ollama for generating document embeddings
- **Local Storage**: SQLite for chat history persistence
  
## How LLM Chat Works

The LLM Chat functionality is handled primarily by the `ChatFrame` class:

1. **Model Selection**
   - Users select from available models in a dropdown (`AVAILABLE_MODELS`)
   - The application connects to Ollama to retrieve model information
   - Default model is set to "llama3.2:latest"

2. **Message Processing Flow**
   - User inputs text via an Entry widget
   - Input is captured and displayed in the chat UI
   - A background thread is spawned to prevent UI freezing
   - The input is sent to Ollama via the `llm_chat()` function
   - Response is received and displayed with a copy button

3. **Chat History**
   - Conversations can be saved with titles
   - History is stored in SQLite database
   - Users can load and delete previous conversations

## How RAG Works

The RAG functionality is implemented in the `VectorsLLMFrame` class using a sophisticated pipeline:

1. **Document Processing**
   - Users upload documents (PDF, DOCX, XLSX, MDX) via a file dialog
   - Documents are loaded using appropriate LangChain loaders
   - Text is split into chunks using `RecursiveCharacterTextSplitter`
   - Chunks are processed with metadata including source information

2. **Embedding and Storage**
   - Document chunks are embedded using Ollama's embedding model
   - Embeddings are stored in ChromaDB with corresponding text and metadata
   - ChromaDB provides persistent storage in a local directory

3. **Query Flow**
   - User enters a query text
   - Query is embedded using the same embedding model
   - Similar documents are retrieved using vector similarity search
   - Results are filtered based on relevance scores
   - A prompt is constructed with retrieved contextual information
   - The selected LLM generates a response based on the provided context

## Data Flow
1. **Document Upload Flow**:
![Alt text](https://github.com/pyMixin/Orinda/blob/main/ORINDA.png)

2. **RAG Query Flow**:
![Alt text](https://github.com/pyMixin/Orinda/blob/main/ORINDA.png)

3. **Direct Chat Flow**:
![Alt text](https://github.com/pyMixin/Orinda/blob/main/ORINDA.png)

