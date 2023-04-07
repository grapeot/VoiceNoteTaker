import openai
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from pydub import AudioSegment
import json
from datetime import datetime
from core import transcribe_voice_message, gpt_process_text, convert_audio_file_to_format
from prompts import PROMPTS

app = Flask(__name__)

# Configs
# TODO: move to a config file
OUTPUT_FORMAT = "mp3"
# For my use case, I want to log all the content to a file, so I can later use it for GPT analysis and dispatching.
# Change it to an actual file name will enable this logging.
PERSONAL_LOG_FILE = None

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400

    audio_file = request.files['audio']
    file_type = audio_file.content_type
    ext_name = file_type.split('/')[-1]
    temp_audio_file = tempfile.NamedTemporaryFile(suffix=f'.{ext_name}')
    with tempfile.NamedTemporaryFile(suffix=f'.{ext_name}') as temp_audio_file:
        print(temp_audio_file.name)
        audio_file.save(temp_audio_file.name)
        # Default is AAC, we need to convert it to mp3.
        with tempfile.NamedTemporaryFile(suffix=f'.{OUTPUT_FORMAT}') as temp_output_file:
            convert_audio_file_to_format(temp_audio_file.name, temp_output_file.name, OUTPUT_FORMAT)

            # Send audio file to Whisper ASR API
            transcribed_text = transcribe_voice_message(temp_output_file.name)

    print(transcribed_text)
    return jsonify(transcribed_text)

# Replace with your OpenAI API key
@app.route('/process', methods=['POST'])
def process_audio():
    if request.method == 'POST':
        data = request.get_json(force=True)
        text = data['text']

        # Send transcribed text to ChatGPT with the provided system prompt
        processed_text = gpt_process_text(text, PROMPTS['paraphrase'], 'gpt-4')
        print(processed_text)
        if PERSONAL_LOG_FILE:
            log_content_to_file(processed_text, PERSONAL_LOG_FILE)
        return jsonify(processed_text)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

def log_content_to_file(content: str, file_name: str):
    """This function helps log each content to a file, which can be later used for GPT analysis and dispatching.
    TODO: add user management so all the users can have their own log files or database.

    Args:
        content (str): Content to be logged.
        file_name (str): Logging filename.
    """
    content_json = json.dumps({'content': content, 'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, ensure_ascii=False)
    with open(file_name, 'a', encoding='UTF-8') as f:
        f.write(content_json + '\n')

if __name__ == '__main__':
    app.run(debug=True)
