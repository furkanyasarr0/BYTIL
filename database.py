import sqlite3

def init_db():
    conn = sqlite3.connect('entertainment_bot.db')
    cursor = conn.cursor()

    # Sunucu ayarları (Hangi oyun hangi kanalda?)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id INTEGER PRIMARY KEY,
        word_game_channel INTEGER,
        counting_game_channel INTEGER,
        bom_game_channel INTEGER
    )
    ''')

    # Kullanıcı puanları (Sıralama için)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_scores (
        guild_id INTEGER,
        user_id INTEGER,
        score INTEGER DEFAULT 0,
        monthly_score INTEGER DEFAULT 0,
        last_reset TEXT,
        PRIMARY KEY (guild_id, user_id)
    )
    ''')

    # Kelime oyunu durumu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS word_game_state (
        guild_id INTEGER PRIMARY KEY,
        last_word TEXT,
        last_user_id INTEGER,
        used_words TEXT DEFAULT ''
    )
    ''')

    # Sayı sayma durumu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS counting_game_state (
        guild_id INTEGER PRIMARY KEY,
        current_number INTEGER DEFAULT 0,
        last_user_id INTEGER
    )
    ''')

    # BOM oyunu durumu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bom_game_state (
        guild_id INTEGER PRIMARY KEY,
        current_number INTEGER DEFAULT 0,
        last_user_id INTEGER
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Veritabanı başarıyla oluşturuldu.")
