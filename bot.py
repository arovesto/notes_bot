
import logging
import datetime
from collections import defaultdict
from support_functions import data_base, create_keyboard, delete_tmp_data, handler_wrapper, add_text_reply,\
    write_text_reply, write_note, get_text_from_note, get_statistics, send_max_words_graph, send_sizes_graph, \
    generate_message, delete_all_files, delete_file
from defaults import ask_lobby_action, ask_note_action, ask_stats_action, LOBBY, WRITE, READ, STATS, FOUND, ADD
from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup
from telegram.ext import \
    Updater, CommandHandler, MessageHandler, Filters, RegexHandler, ConversationHandler, CallbackQueryHandler



logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


current_note_data = {}
page = defaultdict(int)


def start(bot, update):
    update.message.reply_text(
        'Hi! My name is Notes Bot. You can write your notes for me or look your previous notes.\n'
        'Now choose what do yuo want to do? You could find your old notes, write new one or look statistics\n'
        'And you always can delete all of your notes with /delete \n'
        "Write /cancel if you don't want to talk with me :(\n"
        "Write /generate <seed> <length> to generate sequence based on your text",
        reply_markup=ask_lobby_action, one_time_keyboard=True)
    return LOBBY


def list_all_dirs(message, id):
    data = list(a[0] for a in data_base.execute('''SELECT date FROM Notes WHERE id = ?''', [id]))
    if not data:
        message.reply_text("There aren't any your notes. Maybe you wish to create one at first?",
                           reply_markup=ask_lobby_action)
        return LOBBY
    keyboard = create_keyboard(data, page[id])
    message.reply_text('What note do you want to read?:', reply_markup=InlineKeyboardMarkup(keyboard))
    return READ


def lobby(bot, update):
    logger.info("New soul {} chose {}".format(update.message.from_user.first_name, update.message.text))
    if update.message.text == "Find":
        update.message.reply_text("Okay then.",reply_markup=ReplyKeyboardRemove())
        return list_all_dirs(update.message, update.message.chat_id)
    if update.message.text == "New":
        update.message.reply_text('Okay then. Type what you want', reply_markup=ReplyKeyboardRemove())
        return WRITE
    if update.message.text == "Statistics":
        update.message.reply_text("What kind of statistics do you want?", reply_markup=ask_stats_action)
        return STATS
    else:
        update.message.reply_text("Goodbye! Write /start to talk again", reply_markup=ReplyKeyboardRemove())
        delete_tmp_data(update.message.chat_id, current_note_data)
        return ConversationHandler.END


@handler_wrapper()
def add(bot, update):
    id = update.message.chat_id
    logger.info("new note editing of {} on {}".format(update.message.from_user.first_name, current_note_data[id]))
    update.message.reply_text(add_text_reply(update.message.from_user.first_name, current_note_data[id]))
    write_note(id, '\n' + update.message.text, current_note_data[id], mode="a")
    return LOBBY


@handler_wrapper()
def write(bot, update):
    id = update.message.chat_id
    mark = datetime.datetime.now()
    logger.info("new note of {} on {}".format(update.message.from_user.first_name, mark.strftime('%H:%M:%S')))
    update.message.reply_text(write_text_reply(update.message.from_user.first_name, mark))
    write_note(id, update.message.text, mark.strftime('%b %d %Y %H %M %S'))
    return LOBBY


def read(bot, update):
    id = update.callback_query.message.chat_id
    if update.callback_query.data == "back":
        page[id] -= 1
        return list_all_dirs(update.callback_query.message, id)
    if update.callback_query.data == "more":
        page[id] += 1
        return list_all_dirs(update.callback_query.message, id)
    page[id] = 0
    logger.info("new read call {} on {}".format(update.callback_query.from_user.first_name, update.callback_query.data))
    text = get_text_from_note(id, update.callback_query.data)
    update.callback_query.message.reply_text("You wrote this: \n{}".format(text))
    update.callback_query.message.reply_text('What do you want to do now with your note?', reply_markup=ask_note_action)
    current_note_data[id] = update.callback_query.data
    return FOUND


@handler_wrapper()
def stats(bot, update):
    logger.info("new stats call of {} on {}".format(update.message.from_user.first_name, update.message.text))
    data = list(a[0] for a in data_base.execute('''SELECT date FROM Notes WHERE id = ?''', [update.message.chat_id]))
    if update.message.text == "Back":
        return LOBBY
    if not data:
        update.message.reply_text("There aren't any your notes. Maybe you wish to create one at first?",
                                  reply_markup=ask_lobby_action)
        return LOBBY
    if update.message.text == "Info":
        update.message.reply_text(get_statistics(data, update.message.chat_id))
        return LOBBY
    if update.message.text == "Sizes of notes":
        send_sizes_graph(data, update.message.chat_id, bot)
        return LOBBY
    if update.message.text == "Most common words":
        send_max_words_graph(update.message.chat_id, bot)
        return LOBBY


@handler_wrapper()
def found(bot, update):
    logger.info("new stats call of {} on {}".format(update.message.from_user.first_name, update.message.text))
    if update.message.text == "Add":
        update.message.reply_text("Okay, now write anything you want to add to your note",
                                  reply_markup=ReplyKeyboardRemove())
        return ADD
    if update.message.text == "Delete":
        logger.info(delete_file(update.message.chat_id, update.message.from_user.first_name, current_note_data))
        return LOBBY
    else:
        return LOBBY


@handler_wrapper()
def delete_all(bot, update):
    logger.info("User {} deleted all his files".format(update.message.from_user.first_name))
    delete_all_files(update.message.chat_id)
    update.message.reply_text("All your files was removed")
    return LOBBY


def cancel(bot, update):
    id = update.message.chat_id
    logger.info("User {} canceled the conversation.".format(update.message.from_user.first_name))
    update.message.reply_text('Bye! See your later. Write /start to start conversation again',
                              reply_markup=ReplyKeyboardRemove())
    delete_tmp_data(id, current_note_data)
    return ConversationHandler.END


def error(bot, update, error):
    logger.warning('Update {} caused error {}'.format(update, error))


@handler_wrapper()
def message_gen(bot, update, args):
    if len(args) != 2 or not args[1].isdigit():
        update.message.reply_text("You entered wrong arguments. Try again")
        return LOBBY
    update.message.reply_text("Message, generated on your data: {}"
                              .format(generate_message(update.message.chat_id, int(args[1]), args[0])))
    return LOBBY


def main():
    updater = Updater("542333278:AAH4sv5rvwq-zv1ZTygBO2Nu0EQoVrkIEZE")
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LOBBY: [RegexHandler('^(Find|New|Statistics|Exit)$', lobby)],
            READ: [CallbackQueryHandler(read)],
            WRITE: [MessageHandler(Filters.text, write)],
            STATS: [RegexHandler('^(Info|Sizes of notes|Most common words|Back)$', stats)],
            FOUND: [RegexHandler('^(Add|Delete|Back)$', found)],
            ADD: [MessageHandler(Filters.text, add)],
        },

        fallbacks=[CommandHandler('cancel', cancel),
                   CommandHandler('delete', delete_all)]
    )
    dp.add_handler(CommandHandler('generate', message_gen, pass_args=True))
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)
    updater.start_polling()
    logger.info("Bot has start his work")
    updater.idle()


if __name__ == '__main__':
    main()
