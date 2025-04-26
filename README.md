![Alt text](https://github.com/pyMixin/Orinda/blob/main/ORINDA.png)

# Orinda Installation Guide

## Step # 1: Download Ollama (Local LLM)
- https://ollama.com/download
- Once install open terminal or command line on your OS and type
```
ollama pull llama3.2:latest
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








