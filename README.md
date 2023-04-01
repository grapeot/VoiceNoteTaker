# Voice Note Taker

# Motivation

I often find that my writing speed is constrained by my typing abilities. One solution is to use automatic speech recognition, but it has three main disadvantages. Firstly, its accuracy can be limited. Secondly, it tends to be quite literal, requiring significant time for editing and revising. Lastly, it is difficult to go back and make changes if we change our thoughts midway. To address these issues, I developed this project using OpenAI's Whisper API for transcription, followed by the GPT-4 API to paraphrase the text in a more organized and logical manner by considering the entire content.

# Usage

To use the application, simply start the development server, open the web app in your browser, and start speaking. The application will capture your voice, transcribe it using OpenAI's Whisper API, and send the transcribed text to ChatGPT for further processing. The corrected and processed text will then be displayed on the screen.
Configuration & Environment Setup

Follow these steps to set up the project environment:

1. Clone the repository
2. `cd VoiceNoteTaker`
3. [Optional] Create a virtual environment: `python -m venv venv`
4. [Optional] Activate the virtual environment: `venv\Scripts\activate` for Windows or `source venv/bin/activate` for Linux/Mac.
5. Install the required dependencies: `pip install -r requirements.txt`
6.  Set up your OpenAI API key as an environment variable: `set OPENAI_API_KEY=your_api_key_here` for Windows and `export OPENAI_API_KEY=your_api_key_here` for Linux/Mac.
7. Run the development server: `python main.py`

Open your browser and navigate to http://localhost:5000 to access the web app.

⚠️ Warning

This project is set up to use a development server, which is not suitable for production use. Please ensure that you do not deploy the application with the development server for production purposes. Instead, use a production-ready web server, such as Gunicorn or uWSGI, in conjunction with a reverse proxy like Nginx or Apache.

## Docker usage
One click deploy via Railway:
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/JINxPn?referralCode=GfxT3U)