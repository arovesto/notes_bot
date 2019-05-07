from collections import Counter, defaultdict
from defaults import ask_lobby_action, LOBBY, max_data_in_list
from data import data_base
from telegram import InlineKeyboardButton
import matplotlib.pyplot as plt
import datetime
import random
import math
import re


def handler_wrapper(text='What do you want to do next?', reply_keyboard=ask_lobby_action, on_exit=(LOBBY,)):
    def upper(func):
        def wrapper(bot, update, **args):
            a = func(bot, update, **args)
            if a in on_exit:
                update.message.reply_text(text, reply_markup=reply_keyboard, one_time_keyboard=True)
            return a
        return wrapper
    return upper


def write_note(id, text, date, mode="w"):
    if mode == 'w':
        data_base.execute('''INSERT INTO Notes VALUES(?, ?, ?)''', [id, date, text])
    else:
        data_base.execute('''UPDATE Notes SET data = data || ? WHERE id = ? and date = ?''', [text, id, date])
    data_base.commit()


def length_of_file(id, date):
    return len(list(data_base.execute('''SELECT data FROM Notes WHERE id = ? and date = ?''', [id, date]))[0][0])


def count_word_occurrences(id, most_common=10):
    count = Counter()
    for f in data_base.execute('''SELECT data FROM Notes WHERE id = ?''', [id]):
        for l in list(f)[0].split('\n'):
            count.update(filter(lambda x: x != "", (re.compile('[^a-zA-ZÐ°-ÑÐ-Ð¯Ñ‘Ð]').sub("", a) for a in l.split())))
    return count.most_common(most_common)


def delete_file(id, username, current_note_data):
    data_base.execute('''DELETE FROM Notes WHERE id = ? and date = ?''', [id, current_note_data[id]])
    return "User {} removed his {} note".format(username, current_note_data[id])


def create_keyboard(data, page):
    raw_keyboard = [
        [InlineKeyboardButton(datetime.datetime.strptime(a, '%b %d %Y %H %M %S').strftime('%B %d, %Y %H:%M:%S'),
                              callback_data=a)] for a in data]
    if len(data) > max_data_in_list:
        keyboard = list(reversed(raw_keyboard[-max_data_in_list * (page + 1):
                                              len(data) - max_data_in_list * ((page + 1) - 1)]))
        if page == 0:
            keyboard.append([InlineKeyboardButton("More", callback_data="more")])
        elif len(keyboard) < max_data_in_list:
            keyboard.append([InlineKeyboardButton("Back", callback_data="back")])
        else:
            keyboard.append([InlineKeyboardButton("More", callback_data="more"),
                             InlineKeyboardButton("Back", callback_data="back")])
    else:
        keyboard = list(reversed(raw_keyboard))
    return keyboard


def delete_tmp_data(id, data):
    if id in data:
        del data[id]


def send_sizes_graph(data, id, bot):
    data = tuple((datetime.datetime.strptime(a, '%b %d %Y %H %M %S'), length_of_file(id, a))
                 for a in data)
    plt.clf()
    plt.figure(figsize=(15, 7))
    plt.plot(*zip(*data))
    plt.savefig(str(id) + "tmp.png")
    bot.send_photo(chat_id=id, photo=open(str(id) + "tmp.png", "rb"))


def get_statistics(dates, id):
    data = tuple(length_of_file(id, a) for a in dates)
    mean = 0 if len(data) == 0 else sum(data) / len(data)
    return "There are {} your notes. With longest one is {} symbols and shortest is {}. " \
           "The mean length of your notes is {:.2f}".format(len(data), max(data, default=0), min(data, default=0), mean)


def send_max_words_graph(id, bot):
    words, count = zip(*sorted(count_word_occurrences(id), key=lambda x: -x[1]))
    plt.clf()
    plt.figure(figsize=(15, 7))
    plt.yticks(range(min(count), int(math.ceil(max(count))) + 1))
    plt.bar(words, count, width=0.5)
    plt.savefig(str(id) + "tmp.png")
    bot.send_photo(chat_id=id, photo=open(str(id) + "tmp.png", "rb"))


def add_text_reply(name, data):
    return "Thank you, {}. I'm added more text to your note on {}"\
        .format(name, datetime.datetime.strptime(data, '%b %d %Y %H %M %S').strftime('%B %d, %Y %H:%M:%S'))


def write_text_reply(name, mark):
    return 'Thank you, {}. I created your new note on {}'.format(name, mark.strftime('%B %d, %Y %H:%M:%S'))


def get_text_from_note(id, name):
    return list(data_base.execute('''SELECT data FROM Notes WHERE id = ? and date = ?''', [id, name]))[0][0]


def delete_all_files(id):
    data_base.execute("DELETE FROM Notes WHERE id = ?", [(id)])


def generate_message(id, length, seed):
    frequencies = defaultdict(Counter)
    data = ' '.join(a[0] for a in data_base.execute("""SELECT data FROM Notes WHERE id = ?""", [id]))
    regex = re.compile('[^a-zA-ZÐ°-ÑÐ-Ð¯]')
    words = list(filter(lambda x: x != "", (regex.sub("", a) for a in data.replace('\n', ' ').split())))
    for (word1, word2) in zip(words[:-1], words[1:]):
        frequencies[word1].update([word2])
    result_sequence = ""
    if seed and seed in frequencies:
        prev_word = seed
    else:
        prev_word = random.choice(list(frequencies.keys()))
        result_sequence += ' (Word {} not found in texts. Random seed used) '.format(seed)
    for _ in range(length):
        result_sequence += prev_word + " "
        if prev_word in frequencies:
            prev_word = random.choices(*zip(*frequencies[prev_word].items()))[0]
        else:
            prev_word = random.choice(list(frequencies.keys()))
    return result_sequence
