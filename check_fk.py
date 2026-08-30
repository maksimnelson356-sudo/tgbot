import sqlite3

conn = sqlite3.connect('data/tgbot.db')
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tables:', tables)
for t in tables:
    fks = conn.execute(f'PRAGMA foreign_key_list({t})').fetchall()
    if fks:
        print(f'{t}: {fks}')
conn.close()