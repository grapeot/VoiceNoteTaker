import os
import tempfile
import json
import re 
import asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,

)
from telegram.error import BadRequest
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackContext,
    Application,
    PicklePersistence,
    CallbackQueryHandler,
)
import telegram.ext.filters as filters

import core
from core import (
    gpt_process_text,
    gpt_process_text_async,
    convert_audio_file_to_format,
    classify_outline_intent_mode,
    gpt_iterate_on_thoughts,
    classify_outline_content,
)
from prompts import PROMPTS, CHOICE_TO_PROMPT

OUTPUT_FORMAT = "mp3"

telegram_api_token = os.environ.get('TELEGRAM_BOT_TOKEN')
print(f'Bot token: {telegram_api_token}')

target_usage_markup = ReplyKeyboardMarkup([list(CHOICE_TO_PROMPT.keys())], resize_keyboard=True)
outline_markup = ReplyKeyboardMarkup([['End outline mode.']], resize_keyboard=True)

REGULAR, OUTLINE = range(2)

async def initialize_user_data(context: CallbackContext):
    """
    Initialize the user data.
    """
    chat_id = context._chat_id
    user_id = context._user_id
    member = await context.bot.get_chat_member(chat_id, user_id)
    user_full_name = member.user.full_name
    if 'user_full_name' not in context.user_data:
        context.user_data['user_full_name'] = user_full_name
    if 'user_id' not in context.user_data:
        context.user_data['user_id'] = user_id
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    if 'active_model' not in context.user_data:
        context.user_data['active_model'] = 'gpt-4'

async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Send me a voice message, and I will transcribe it for you. Note I am not a QA bot, and will not answer your questions. I will only listen to you and transcribe your voice message, with paraphrasing from GPT-4. Type /help for more information.', reply_markup=target_usage_markup)
    return REGULAR

async def help(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("""*YaGe Voice Note Taker Bot*

*Usage*: Send me a voice message, and I will transcribe it for you\. Note I am not a QA bot, and will not answer your questions\. I will only listen to you and transcribe your voice message, with paraphrasing from GPT\-4\.

*Data and privacy*: I log your transcriptions and paraphrased texts, to support a future service of sending summary of your voice messages\. I will not share your data with any third party\. I will not use your data for any purposes other than to provide you with a better service\. You can always check what data are logged by sending /data command, and clear your data \(on our end\) by sending /clear command\.

*Commands*: 
/help: Display this help message\.
/data: Display any information we had about you from our end\.
/clear: Clear any information we had about you from our end\.""", parse_mode='MarkdownV2')
    return REGULAR

async def data(update: Update, context: CallbackContext) -> int:
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
    return REGULAR

async def clear(update: Update, context: CallbackContext) -> int:
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
    return REGULAR

# TODO: send out daily summaries to users.

async def set_last_message(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    await initialize_user_data(context)
    context.user_data['history'].append({
        'date': update.message.date,
        'set_content': text,
        'last_text_field': 'set_content',
        'history': ['set_content']
    })
    await update.message.reply_text("Your message has been set as the last message. Now you can use the buttons to transform it.")
    return REGULAR

async def warn_if_not_voice_message(update: Update, context: CallbackContext) -> int:
    if not update.message.voice:
        await update.message.reply_text("Please send me a voice message. I will transcribe it and paraphrase for you.")
    return REGULAR

async def process_thoughts(update: Update, context: CallbackContext) -> int:
    await initialize_user_data(context)
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
    # TODO: make it part of the usage definition
    if target_usage != '思考':
        context.user_data['history'][-1]['last_text_field'] = new_text_field
    context.user_data['history'][-1]['history'].append(target_usage)
    context.user_data['history'][-1][new_text_field] = result
    print(context.user_data['history'][-1])
    await update.message.reply_text(result)
    return REGULAR

async def transcribe_message(user_full_name: str, update: Update, context: CallbackContext) -> str:
    """A utility function to transcribe a voice message.

    Args:
        user_full_name (str): full name of the user
        update (Update): from the telegram bot API
        context (CallbackContext): from the telegram bot API

    Returns:
        str: transcribed text
    """
    file_id = update.message.voice.file_id
    voice_file = await context.bot.get_file(file_id)
    
    # Download the voice message
    voice_data = await voice_file.download_as_bytearray()

    with tempfile.NamedTemporaryFile('wb+', suffix=f'.ogg') as temp_audio_file:
        temp_audio_file.write(voice_data)
        temp_audio_file.seek(0)
        with tempfile.NamedTemporaryFile(suffix=f'.{OUTPUT_FORMAT}') as temp_output_file:
            convert_audio_file_to_format(temp_audio_file.name, temp_output_file.name, OUTPUT_FORMAT)
            transcribed_text = core.transcribe_voice_message(temp_output_file.name)
    print(f'[{user_full_name}] {transcribed_text}')
    return transcribed_text

async def get_user_full_name(update: Update, context: CallbackContext) -> str:
    """A utility function to get the full name of the user.

    Args:
        update (Update): from the telegram bot API
        context (CallbackContext): from the telegram bot API

    Returns:
        str: full name of the user
    """
    chat_id = context._chat_id
    user_id = context._user_id
    member = await context.bot.get_chat_member(chat_id, user_id)
    user_full_name = member.user.full_name
    return user_full_name

async def transcribe_voice_message(update: Update, context: CallbackContext) -> int:
    user_full_name = await get_user_full_name(update, context)
    # We need to log the user info and histories in the user_data so we can send out daily summaries.
    # Check the help message for more details.
    await initialize_user_data(context)
    
    # Call the Whisper ASR API
    try:
        transcribed_text = await transcribe_message(user_full_name, update, context)
        await update.message.reply_text("Transcribed text:")
        await update.message.reply_text(transcribed_text, reply_markup=target_usage_markup)
    except Exception as e:
        print(f'[{user_full_name}] Error: {e}')
        await update.message.reply_text(f"Error: {e}", reply_markup=target_usage_markup)
        return REGULAR

    # Disable the preprocessing for now due to the poor performance of GPT-3.5.
    # We may resume this design when we have more thoughts on the prompts, ideas and chains.
    # preprocessed_text = preprocess_text(transcribed_text)
    # print(f'[{user_full_name}] {preprocessed_text}')
    # Sometimes due to the token limit of GPT-3.5, the preprocessed_text is truncated. We need to do some error handling here, defaulting to the original text.
    # try:
        # result_obj = json.loads(preprocessed_text)
    # except Exception as e:
        # print(f'[{user_full_name}] Error: {e}')
        # result_obj = {'tag': '思考', 'content': transcribed_text}

    result_obj = {'tag': '思考', 'content': transcribed_text}
    # Model switch
    if classify_outline_intent_mode(result_obj['content']):
        await update.message.reply_text("Entering outline mode. Now you can use natural language to edit the outline.")
        context.user_data['outline_text'] = []
        print(f'[{user_full_name}] Entering outline mode.')
        return OUTLINE
    
    # Some more info on the history and last_text_field:
    # The history records the order of the fields being calculated, from which how the idea got transformed could be reproduced.
    # The last_text_field records the last field that was calculated, which is used to determine which field to use as the input for the next step.
    result_obj['history'] = ['tag']
    result_obj['last_text_field'] = 'content'
    # model = 'gpt-3.5-turbo' if result_obj['tag'] == '草稿' else 'gpt-4'
    model = context.user_data['active_model']
    result_obj['model'] = model
    result_obj['history'].append('model')
    result_obj['transcribed'] = transcribed_text
    result_obj['history'].append('transcribed')
    result_obj['last_text_field'] = 'transcribed'
    print(f'[{user_full_name}] {result_obj}')
    try:
        # Uncomment to use synchronous API
        # paraphrased_text = gpt_process_text(result_obj['content'], PROMPTS['paraphrase'], model)
        
        # Uncomment to use asynchronous API
        await update.message.reply_text(f"Paraphrased using {model.upper()}:")
        placeholder_message = await update.message.reply_text("...")
        await update.message.chat.send_action(action="typing")
        previous_text = ''
        message_count = 0
        async for status, paraphrased_text in gpt_process_text_async(result_obj['content'], PROMPTS['paraphrase'], model):
            paraphrased_text = paraphrased_text[message_count * 4096:]
            if len(paraphrased_text) > 4096:
                # send out the current message
                await context.bot.edit_message_text(paraphrased_text[message_count * 4096: (message_count + 1) * 4096],
                    chat_id=placeholder_message.chat_id,
                    message_id=placeholder_message.message_id,
                    reply_markup=target_usage_markup)
                # maintain variables
                message_count += 1
                placeholder_message = await update.message.reply_text("...")
            if status != 'finished' and abs(len(paraphrased_text) - len(previous_text)) < 50:
                continue
            if status == 'finished' and abs(len(paraphrased_text) - len(previous_text)) == 0:
                continue
            try:
                await context.bot.edit_message_text(paraphrased_text,
                    chat_id=placeholder_message.chat_id,
                    message_id=placeholder_message.message_id,
                    reply_markup=target_usage_markup)
            except BadRequest as e:
                if str(e).startswith("Message is not modified"):
                    continue
                else:
                    await context.bot.edit_message_text(paraphrased_text,
                        chat_id=placeholder_message.chat_id,
                        message_id=placeholder_message.message_id)
            await asyncio.sleep(0.01)
            previous_text = paraphrased_text 
                 
        result_obj['paraphrased'] = paraphrased_text
        result_obj['history'].append('paraphrased')
        result_obj['date'] = update.message.date
        result_obj['last_text_field'] = 'paraphrased'
        print(f'[{user_full_name}] {paraphrased_text}')
        context.user_data['history'].append(result_obj)
        # await update.message.reply_text(paraphrased_text, reply_markup=target_usage_markup)
    except Exception as e:
        print(f'[{user_full_name}] Error: {e}')
        await update.message.reply_text(f"Error: {e}", reply_markup=target_usage_markup)
        return REGULAR

    return REGULAR

async def end_outline_mode(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "End outline mode. Back to regular mode.",
        reply_markup=target_usage_markup,
    )
    print(f'[{get_user_full_name(update, context)}] Exiting outline mode.')
    return REGULAR

async def outline_transcribe_voice_message(update: Update, context: CallbackContext) -> int:
    # Transcribe the voice message, without GPT paraphrasing.
    user_full_name = await get_user_full_name(update, context)
    transcribed_text = await transcribe_message(user_full_name, update, context)

    # Implementation V1: use JSON as the intermediate format.
    # Identify the intent and content of the transcribed text.
    parsed_text = classify_outline_content(transcribed_text)
    if parsed_text['intent'] == 'exit':
        await update.message.reply_text('Exiting outline mode.')
        return REGULAR
    if parsed_text['intent'] == 'append':
        if parsed_text['line'] == -1:
            context.user_data['outline_text'].append('* ' + parsed_text['content'])
        else:
            # note the python index starts from 0, but the line number starts from 1.
            context.user_data['outline_text'].insert(parsed_text['line'], '* ' + parsed_text['content'])
    if parsed_text['intent'] == 'modify':
        # note the python index starts from 0, but the line number starts from 1.
        context.user_data['outline_text'][parsed_text['line'] - 1] = '* ' + parsed_text['content']
    await update.message.reply_text('\n'.join(context.user_data['outline_text']))

    # Implementation V2: directly use GPT to get the new text
    # text = '\n'.join(context.user_data['outline_text'])
    # new_text = gpt_process_text(PROMPTS['language-text-editor-user-template'].format(text=text, instruction=transcribed_text), 
    #                             PROMPTS['language-text-editor-system'], 'gpt-4')
    # if new_text == 'exit':
    #     await update.message.reply_text('Exiting outline mode.')
    #     return REGULAR
    # text = new_text.split('\n')
    # # For some reason, GPT-3.5 or 4 will sometimes return "TEXT:", we need to remove it
    # text = [x.strip() for x in text if re.search(r'^\s*TEXT:\s*$', x) is None]
    # context.user_data['outline_text'] = text
    # await update.message.reply_text('\n'.join(['* ' + x for x in context.user_data['outline_text']]))
    
    return OUTLINE

async def model_selection(update: Update, context: CallbackContext):
    await initialize_user_data(context)
    buttons = []
    for model in ['gpt-3.5-turbo', 'gpt-4']:
        if model == context.user_data['active_model']:
            buttons.append(InlineKeyboardButton(text='✅ ' + model, callback_data=model))
        else:
            buttons.append(InlineKeyboardButton(text=model, callback_data=model))
    model_keyboard = InlineKeyboardMarkup.from_column(buttons)
    await update.message.reply_text('Please select a model for transcribing:', reply_markup=model_keyboard)

async def model_selection_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    model = query.data
    context.user_data['active_model'] = model
    await update.callback_query.edit_message_text('Model selected: ' + model)

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand(command="/start", description="Start the bot."),
        BotCommand(command="/help", description="View more detailed help messages."),
        BotCommand(command="/data", description="Check what data we store about you."),
        BotCommand(command="/clear", description="Clear all the data we stored about you."),
        BotCommand(command="/model", description="Select the model for transcribing."),
    ])

def main():
    persistence = PicklePersistence(filepath="gpt_archive.pickle")
    application = Application.builder() \
        .token(telegram_api_token) \
        .persistence(persistence) \
        .arbitrary_callback_data(True) \
        .post_init(post_init) \
        .build()

    regular_handlers =  [
            # target usage
            MessageHandler(filters.Regex('^' + target_usage + '$'), process_thoughts) 
                for target_usage in CHOICE_TO_PROMPT.keys()
        ] + [
            MessageHandler(filters.VOICE & ~filters.COMMAND, transcribe_voice_message),
            MessageHandler(filters.TEXT & ~filters.COMMAND, set_last_message),
        ]

    conversation_handler = ConversationHandler(
        entry_points=regular_handlers,
        states={
            REGULAR: regular_handlers,
            OUTLINE: [
                MessageHandler(filters.VOICE & ~filters.COMMAND, outline_transcribe_voice_message),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', end_outline_mode),
            MessageHandler(filters.TEXT & ~filters.COMMAND, end_outline_mode),
        ],
    )
    application.add_handler(conversation_handler)

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("data", data))
    application.add_handler(CommandHandler("model", model_selection))
    application.add_handler(CallbackQueryHandler(model_selection_callback, pattern='^gpt-'))

    # Fallback of the ConversationHandler because without a /start, the message won't be handled by the ConversationHandler.
    application.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, transcribe_voice_message))
    for target_usage in CHOICE_TO_PROMPT.keys():
        application.add_handler(MessageHandler(filters.Regex('^' + target_usage + '$'), process_thoughts))
    application.add_handler(MessageHandler(~filters.VOICE & ~filters.COMMAND, set_last_message))

    # Run the bot until the user presses Ctrl-C
    print('Bot is running...')
    application.run_polling()

if __name__ == '__main__':
    main()
