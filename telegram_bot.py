import os
import tempfile
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, CallbackContext, Application
import telegram.ext.filters as filters

import core
from core import paraphrase_text, convert_audio_file_to_format

OUTPUT_FORMAT = "mp3"

telegram_api_token = os.environ.get('TELEGRAM_BOT_TOKEN')
print(telegram_api_token)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Send me a voice message, and I will transcribe it for you.')

async def transcribe_voice_message(update: Update, context: CallbackContext):
    file_id = update.message.voice.file_id
    voice_file = await context.bot.get_file(file_id)
    
    # Download the voice message
    voice_data = await voice_file.download_as_bytearray()
    
    # Call the Whisper ASR API
    with tempfile.NamedTemporaryFile('wb+', suffix=f'.ogg') as temp_audio_file:
        temp_audio_file.write(voice_data)
        temp_audio_file.seek(0)
        with tempfile.NamedTemporaryFile(suffix=f'.{OUTPUT_FORMAT}') as temp_output_file:
            convert_audio_file_to_format(temp_audio_file.name, temp_output_file.name, OUTPUT_FORMAT)
            transcribed_text = core.transcribe_voice_message(temp_output_file.name)
    print(transcribed_text)
    # await update.message.reply_text(transcribed_text)

    # TODO: change to GPT-4 for whitelisted users
    paraphrased_text = paraphrase_text(transcribed_text, 'gpt-3.5-turbo')
    print(paraphrased_text)
    await update.message.reply_text(paraphrased_text)

def main():
    application = Application.builder().token(telegram_api_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, transcribe_voice_message))

    # Run the bot until the user presses Ctrl-C
    print('Bot is running...')
    application.run_polling()

if __name__ == '__main__':
    main()
