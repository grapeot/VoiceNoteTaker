import os
import tempfile
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, CallbackContext, Application, PicklePersistence
import telegram.ext.filters as filters

import core
from core import gpt_process_text, convert_audio_file_to_format, preprocess_text, gpt_iterate_on_thoughts
from prompts import PROMPTS, CHOICE_TO_PROMPT

OUTPUT_FORMAT = "mp3"

telegram_api_token = os.environ.get('TELEGRAM_BOT_TOKEN')
print(f'Bot token: {telegram_api_token}')

reply_keyboard = [
    list(CHOICE_TO_PROMPT.keys())
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Send me a voice message, and I will transcribe it for you. Note I am not a QA bot, and will not answer your questions. I will only listen to you and transcribe your voice message, with paraphrasing from GPT-4. Type /help for more information.', reply_markup=markup)

async def help(update: Update, context: CallbackContext):
    await update.message.reply_text("""*YaGe Voice Note Taker Bot*

*Usage*: Send me a voice message, and I will transcribe it for you\. Note I am not a QA bot, and will not answer your questions\. I will only listen to you and transcribe your voice message, with paraphrasing from GPT\-4\.

*Data and privacy*: I log your transcriptions and paraphrased texts, to support a future service of sending summary of your voice messages\. I will not share your data with any third party\. I will not use your data for any purposes other than to provide you with a better service\. You can always check what data are logged by sending /data command, and clear your data \(on our end\) by sending /clear command\.

*Commands*: 
/help: Display this help message\.
/data: Display any information we had about you from our end\.
/clear: Clear any information we had about you from our end\.""", parse_mode='MarkdownV2')

async def data(update: Update, context: CallbackContext):
    """
    Display any information we had about the user from our end.
    """
    chat_id = context._chat_id
    user_id = context._user_id
    member = await context.bot.get_chat_member(chat_id, user_id)
    user_full_name = member.user.full_name
    print(f'[{user_full_name}] /data')
    to_send = str(context.user_data)
    if len(to_send) > 4096:
        await update.message.reply_text(f"Your data is too long to be displayed. It contains {len(context.user_data['history'])} entries. The last message is {context.user_data['history'][-1]}. It records across the time period from {context.user_data['history'][0]['date']} to {context.user_data['history'][-1]['date']}.")
    else:
        await update.message.reply_text(to_send)

async def clear(update: Update, context: CallbackContext):
    """
    Clear any information we had about the user from our end.
    """
    chat_id = context._chat_id
    user_id = context._user_id
    member = await context.bot.get_chat_member(chat_id, user_id)
    user_full_name = member.user.full_name
    print(f'[{user_full_name}] /clear')
    context.user_data.clear()
    await update.message.reply_text("Your data has been cleared.")

# TODO: send out daily summaries to users.

async def warn_if_not_voice_message(update: Update, context: CallbackContext):
    if not update.message.voice:
        await update.message.reply_text("Please send me a voice message. I will transcribe it and paraphrase for you.")

async def process_thoughts(update: Update, context: CallbackContext):
    if len(context.user_data['history']) == 0:
        await update.message.reply_text("You need to send me a text message first before we can work on yoru thought.")
        return
    print(context.user_data['history'][-1])
    last_thought = context.user_data['history'][-1]
    last_text_field = last_thought['last_text_field']
    last_thought_text = last_thought[last_text_field]
    target_usage = update.message.text
    result = gpt_iterate_on_thoughts(last_thought_text, target_usage)
    new_text_field = last_text_field + '_' + target_usage
    # When the target usage is 思考, we don't update the last_text_field because it's not a continuation or processed version of the previous thought, but a detour with inspirations.
    if target_usage != '思考':
        context.user_data['history'][-1]['last_text_field'] = new_text_field
    context.user_data['history'][-1]['history'].append(target_usage)
    context.user_data['history'][-1][new_text_field] = result
    print(context.user_data['history'][-1])
    await update.message.reply_text(result)
    

async def transcribe_voice_message(update: Update, context: CallbackContext):
    chat_id = context._chat_id
    user_id = context._user_id
    member = await context.bot.get_chat_member(chat_id, user_id)
    user_full_name = member.user.full_name
    # We need to log the user info and histories in the user_data so we can send out daily summaries.
    # Check the help message for more details.
    if 'user_full_name' not in context.user_data:
        context.user_data['user_full_name'] = user_full_name
    if 'user_id' not in context.user_data:
        context.user_data['user_id'] = user_id
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    
    file_id = update.message.voice.file_id
    voice_file = await context.bot.get_file(file_id)
    
    # Download the voice message
    voice_data = await voice_file.download_as_bytearray()
    
    # Call the Whisper ASR API
    try:
        with tempfile.NamedTemporaryFile('wb+', suffix=f'.ogg') as temp_audio_file:
            temp_audio_file.write(voice_data)
            temp_audio_file.seek(0)
            with tempfile.NamedTemporaryFile(suffix=f'.{OUTPUT_FORMAT}') as temp_output_file:
                convert_audio_file_to_format(temp_audio_file.name, temp_output_file.name, OUTPUT_FORMAT)
                transcribed_text = core.transcribe_voice_message(temp_output_file.name)
        print(f'[{user_full_name}] {transcribed_text}')
        await update.message.reply_text("Transcribed text:")
        await update.message.reply_text(transcribed_text)
    except Exception as e:
        print(f'[{user_full_name}] Error: {e}')
        await update.message.reply_text(f"Error: {e}")
        return

    preprocessed_text = preprocess_text(transcribed_text)
    print(f'[{user_full_name}] {preprocessed_text}')
    # Some more info on the history and last_text_field:
    # The history records the order of the fields being calculated, from which how the idea got transformed could be reproduced.
    # The last_text_field records the last field that was calculated, which is used to determine which field to use as the input for the next step.
    result_obj = json.loads(preprocessed_text)
    result_obj['history'] = ['tag']
    result_obj['last_text_field'] = 'content'
    model = 'gpt-3.5-turbo' if result_obj['tag'] == '聊天' else 'gpt-4'
    result_obj['model'] = model
    result_obj['history'].append('model')
    result_obj['transcribed'] = transcribed_text
    result_obj['history'].append('transcribed')
    result_obj['last_text_field'] = 'transcribed'
    print(f'[{user_full_name}] {result_obj}')
    try:
        paraphrased_text = gpt_process_text(result_obj['content'], PROMPTS['paraphrase'], model)
        result_obj['paraphrased'] = paraphrased_text
        result_obj['history'].append('paraphrased')
        result_obj['date'] = update.message.date
        result_obj['last_text_field'] = 'paraphrased'
        print(f'[{user_full_name}] {paraphrased_text}')
        context.user_data['history'].append(result_obj)
        await update.message.reply_text(f"Paraphrased using {model.upper()}:")
        await update.message.reply_text(paraphrased_text)
    except Exception as e:
        print(f'[{user_full_name}] Error: {e}')
        await update.message.reply_text(f"Error: {e}")
        return

def main():
    persistence = PicklePersistence(filepath="gpt_archive.pickle")
    application = Application.builder().token(telegram_api_token).persistence(persistence).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("data", data))

    # We don't use ConversationHandler here because we don't need to keep track of the state.
    application.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, transcribe_voice_message))
    for target_usage in CHOICE_TO_PROMPT.keys():
        application.add_handler(MessageHandler(filters.Regex('^' + target_usage + '$'), process_thoughts))
    application.add_handler(MessageHandler(~filters.VOICE & ~filters.COMMAND, warn_if_not_voice_message))

    # Run the bot until the user presses Ctrl-C
    print('Bot is running...')
    application.run_polling()

if __name__ == '__main__':
    main()
