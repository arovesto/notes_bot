from telegram import ReplyKeyboardMarkup


LOBBY, FOUND, WRITE, STATS, READ, ADD = range(6)
ask_lobby_action = ReplyKeyboardMarkup([['Find', 'New', 'Statistics'], ['Exit']])
ask_stats_action = ReplyKeyboardMarkup([['Info', 'Sizes of notes', "Most common words"], ["Back"]])
ask_note_action = ReplyKeyboardMarkup([['Add', 'Delete', 'Back']])
max_data_in_list = 5
