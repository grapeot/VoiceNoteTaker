# Voice Note Taker

# Motivation

This project aims to provide a seamless integration of voice input with OpenAI's Whisper API and ChatGPT. By utilizing state-of-the-art voice recognition and natural language processing technologies, users can effortlessly interact with the application using speech, which will be transcribed and processed to provide accurate and useful responses.

# Usage

To use the application, simply start the development server, open the web app in your browser, and start speaking. The application will capture your voice, transcribe it using OpenAI's Whisper API, and send the transcribed text to ChatGPT for further processing. The corrected and processed text will then be displayed on the screen.
Configuration & Environment Setup

Follow these steps to set up the project environment:

1. Clone the repository
2. cd yourrepository
3. [Optional] Create a virtual environment: `python -m venv venv`
4. [Optional] Activate the virtual environment: `venv\Scripts\activate` for Windows or `source venv/bin/activate` for Linux/Mac.
5. Install the required dependencies: `pip install -r requirements.txt`
6.  Set up your OpenAI API key as an environment variable: `set OPENAI_API_KEY=your_api_key_here` for Windows and `export OPENAI_API_KEY=your_api_key_here` for Linux/Mac.
7. Run the development server: `python app.py`

Open your browser and navigate to http://localhost:5000 to access the web app.

⚠️ Warning

This project is set up to use a development server, which is not suitable for production use. Please ensure that you do not deploy the application with the development server for production purposes. Instead, use a production-ready web server, such as Gunicorn or uWSGI, in conjunction with a reverse proxy like Nginx or Apache.