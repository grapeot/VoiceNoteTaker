import openai
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from pydub import AudioSegment

app = Flask(__name__)

def convert_file_to_format(input_file, output_file, output_format):
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format=output_format)

output_format = "mp3"

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
        with tempfile.NamedTemporaryFile(suffix=f'.{output_format}') as temp_output_file:
            convert_file_to_format(temp_audio_file.name, temp_output_file.name, output_format)

            # Send audio file to Whisper ASR API
            with open(temp_output_file.name, 'rb') as file:
                whisper_response = openai.Audio.transcribe('whisper-1', file)

    transcribed_text = whisper_response['text']
    print(transcribed_text)
    return jsonify(transcribed_text)

# Replace with your OpenAI API key
@app.route('/process', methods=['POST'])
def process_audio():
    if request.method == 'POST':
        data = request.get_json(force=True)
        text = data['text']

        # Send transcribed text to ChatGPT with the provided system prompt
        chat_gpt_prompt = f"Read the following text, correct any errors from automatic speech recognition, and rephrase the text in an organized way, in the same language: {text}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                # {"role": "system", "content": chat_gpt_prompt},
                {"role": "user", "content": chat_gpt_prompt},
            ],
            temperature=0,
        )

        return jsonify(response.choices[0].message.content.strip())

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
