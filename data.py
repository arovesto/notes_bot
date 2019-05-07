import sqlite3

data_base = sqlite3.connect("notes.db", check_same_thread=False)

if __name__ == '__main__':
    data_base.execute('''CREATE TABLE Notes (id int, date text, data text)''')
