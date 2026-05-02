import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import os
import random
from datetime import datetime
from dotenv import load_dotenv

import sys

load_dotenv()
TOKEN = os.getenv('TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DB_PATH = 'entertainment_bot.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn, conn.cursor()

def update_score(guild_id, user_id, points):
    conn, cursor = get_db()
    now = datetime.now().strftime('%Y-%m')
    
    # Reset monthly score if month changed
    cursor.execute('SELECT last_reset FROM user_scores WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
    row = cursor.fetchone()
    if row and row[0] != now:
        cursor.execute('''
        UPDATE user_scores SET monthly_score = 0, last_reset = ? 
        WHERE guild_id = ? AND user_id = ?
        ''', (now, guild_id, user_id))

    cursor.execute('''
    INSERT INTO user_scores (guild_id, user_id, score, monthly_score, last_reset)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(guild_id, user_id) DO UPDATE SET 
        score = score + ?, 
        monthly_score = monthly_score + ?,
        last_reset = ?
    ''', (guild_id, user_id, points, points, now, points, points, now))
    conn.commit()
    conn.close()

def load_words():
    try:
        with open('words.txt', 'r', encoding='utf-8') as f:
            return [line.strip().lower() for line in f if line.strip()]
    except Exception as e:
        print(f"Kelime listesi yüklenemedi: {e}")
        return []

WORDS_LIST = load_words()

def get_possible_words(last_char):
    # Türkçede kelime ğ ile başlamaz. Eğer last_char 'ğ' ise, bu harfle başlayan kelime yoktur.
    if last_char == 'ğ':
        return []
    return [w for w in WORDS_LIST if w.startswith(last_char)]

@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"Slash komutları senkronize edilemedi: {e}")
        
    if not monthly_reset_check.is_running():
        monthly_reset_check.start()

@tasks.loop(hours=24)
async def monthly_reset_check():
    now = datetime.now()
    if now.day == 1:
        conn, cursor = get_db()
        # Bu basitleştirilmiş bir sıfırlama, on_message içinde de kontrol ediliyor
        # Ancak toplu sıfırlama için burada da durabilir.
        # Aslında her ayın 1'inde tabloyu temizlemek daha mantıklı olabilir 
        # ama 'score' (toplam puan) kalmalı, sadece monthly_score sıfırlanmalı.
        cursor.execute('UPDATE user_scores SET monthly_score = 0, last_reset = ?', (now.strftime('%Y-%m'),))
        conn.commit()
        conn.close()
        print("Aylık puanlar sıfırlandı.")

@bot.tree.command(name="kurulum", description="Oyun kanallarını otomatik olarak oluşturur.")
@app_commands.checks.has_permissions(administrator=True)
async def kurulum(interaction: discord.Interaction):
    """Oyun kanallarını bot tarafından oluşturur."""
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("Bu komutu sadece sunucu sahibi kullanabilir!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

    # Kategori oluştur (isteğe bağlı ama düzen için iyi)
    try:
        category = await guild.create_category("🎮 OYUNLAR", overwrites=overwrites)
    except discord.Forbidden:
        await interaction.followup.send("Botun kanal/kategori oluşturma yetkisi yok!", ephemeral=True)
        return
    
    # Kanalları oluştur
    word_channel = await guild.create_text_channel("🔡-kelime-türetme", category=category)
    count_channel = await guild.create_text_channel("🔢-sayı-sayma", category=category)
    bom_channel = await guild.create_text_channel("💣-bom-oyunu", category=category)

    conn, cursor = get_db()
    cursor.execute('''
    INSERT INTO guild_settings (guild_id, word_game_channel, counting_game_channel, bom_game_channel)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(guild_id) DO UPDATE SET 
        word_game_channel = ?, 
        counting_game_channel = ?, 
        bom_game_channel = ?
    ''', (guild.id, word_channel.id, count_channel.id, bom_channel.id, word_channel.id, count_channel.id, bom_channel.id))
    
    # Kelime oyunu için başlangıç kelimesi ayarla
    if WORDS_LIST:
        start_word = random.choice(WORDS_LIST)
    else:
        start_word = "elma" # Varsayılan kelime
        
    cursor.execute('''
    INSERT INTO word_game_state (guild_id, last_word, last_user_id, used_words)
    VALUES (?, ?, NULL, ?)
    ON CONFLICT(guild_id) DO UPDATE SET last_word = ?, last_user_id = NULL, used_words = ?
    ''', (guild.id, start_word, start_word, start_word, start_word))
    
    conn.commit()
    conn.close()

    await word_channel.send(f"🎮 Kelime türetme oyunu başladı! İlk kelimemiz: **{start_word}**")
    await count_channel.send("🔢 Sayı sayma oyunu başladı! `1` yazarak başlayın.")
    await bom_channel.send("💣 BOM oyunu başladı! `1` yazarak başlayın. 5 ve katlarında `BOM` yazmayı unutmayın!")

    await interaction.followup.send(f"Oyun kanalları başarıyla oluşturuldu: {category.mention}", ephemeral=True)

@bot.tree.command(name="sıralama", description="Sunucudaki aylık en yüksek puanlı oyuncuları gösterir.")
async def sıralama(interaction: discord.Interaction):
    """Sunucudaki aylık en yüksek puanlı oyuncuları gösterir."""
    await interaction.response.defer()
    conn, cursor = get_db()
    
    cursor.execute('''
    SELECT user_id, monthly_score FROM user_scores 
    WHERE guild_id = ? AND monthly_score > 0
    ORDER BY monthly_score DESC LIMIT 10
    ''', (interaction.guild.id,))
    
    results = cursor.fetchall()
    conn.close()

    if not results:
        await interaction.followup.send("Bu ay henüz kimse puan kazanmamış!", ephemeral=True)
        return

    embed = discord.Embed(
        title="📅 Aylık Sunucu Sıralaması", 
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    leaderboard_text = ""
    for i, (user_id, score) in enumerate(results, 1):
        try:
            member = interaction.guild.get_member(user_id)
            if member is None:
                member = await interaction.guild.fetch_member(user_id)
            
            name = member.display_name
        except:
            user = await bot.fetch_user(user_id)
            name = user.name if user else f"Bilinmeyen Kullanıcı ({user_id})"

        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{medal} **{name}** — `{score}` puan\n"
    
    embed.description = leaderboard_text
    embed.set_footer(text=f"{interaction.guild.name} Sıralaması", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="reboot", description="Oyun kanallarını silip tekrar oluşturur ve botu yeniden başlatır.")
@app_commands.checks.has_permissions(administrator=True)
async def reboot(interaction: discord.Interaction):
    """Oyun kanallarını silip tekrar oluşturur ve botu yeniden başlatır."""
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("Bu komutu sadece sunucu sahibi kullanabilir!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    conn, cursor = get_db()
    
    # Mevcut kanal ayarlarını al
    cursor.execute('SELECT word_game_channel, counting_game_channel, bom_game_channel FROM guild_settings WHERE guild_id = ?', (guild.id,))
    settings = cursor.fetchone()
    
    if settings:
        word_ch_id, count_ch_id, bom_ch_id = settings
        channels_to_delete = [word_ch_id, count_ch_id, bom_ch_id]
        
        # Kanalları ve kategoriyi bulup silmeye çalış
        category_to_delete = None
        for ch_id in channels_to_delete:
            if ch_id:
                channel = guild.get_channel(ch_id)
                if channel:
                    if not category_to_delete and channel.category:
                        category_to_delete = channel.category
                    try:
                        await channel.delete()
                    except Exception as e:
                        print(f"Kanal silinemedi ({ch_id}): {e}")
        
        if category_to_delete and category_to_delete.name == "🎮 OYUNLAR":
            try:
                await category_to_delete.delete()
            except Exception as e:
                print(f"Kategori silinemedi: {e}")

    # Yeni kurulum yap
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

    try:
        category = await guild.create_category("🎮 OYUNLAR", overwrites=overwrites)
    except discord.Forbidden:
        await interaction.followup.send("Botun yetkisi yetersiz!", ephemeral=True)
        return

    word_channel = await guild.create_text_channel("🔡-kelime-türetme", category=category)
    count_channel = await guild.create_text_channel("🔢-sayı-sayma", category=category)
    bom_channel = await guild.create_text_channel("💣-bom-oyunu", category=category)

    cursor.execute('''
    INSERT INTO guild_settings (guild_id, word_game_channel, counting_game_channel, bom_game_channel)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(guild_id) DO UPDATE SET 
        word_game_channel = ?, 
        counting_game_channel = ?, 
        bom_game_channel = ?
    ''', (guild.id, word_channel.id, count_channel.id, bom_channel.id, word_channel.id, count_channel.id, bom_channel.id))
    
    if WORDS_LIST:
        start_word = random.choice(WORDS_LIST)
    else:
        start_word = "elma"

    cursor.execute('''
    INSERT INTO word_game_state (guild_id, last_word, last_user_id, used_words)
    VALUES (?, ?, NULL, ?)
    ON CONFLICT(guild_id) DO UPDATE SET last_word = ?, last_user_id = NULL, used_words = ?
    ''', (guild.id, start_word, start_word, start_word, start_word))
    
    # Diğer oyun durumlarını da sıfırla
    cursor.execute('INSERT INTO counting_game_state (guild_id, current_number, last_user_id) VALUES (?, 0, NULL) ON CONFLICT(guild_id) DO UPDATE SET current_number = 0, last_user_id = NULL', (guild.id,))
    cursor.execute('INSERT INTO bom_game_state (guild_id, current_number, last_user_id) VALUES (?, 0, NULL) ON CONFLICT(guild_id) DO UPDATE SET current_number = 0, last_user_id = NULL', (guild.id,))

    # Kullanıcı puanlarını sıfırla
    cursor.execute('DELETE FROM user_scores WHERE guild_id = ?', (guild.id,))

    conn.commit()
    conn.close()

    await word_channel.send(f"🎮 Kelime türetme oyunu yeniden başlatıldı! İlk kelimemiz: **{start_word}**")
    await count_channel.send("🔢 Sayı sayma oyunu yeniden başlatıldı! `1` yazarak başlayın.")
    await bom_channel.send("💣 BOM oyunu yeniden başlatıldı! `1` yazarak başlayın. 5 ve katlarında `BOM` yazmayı unutmayın!")

    try:
        await interaction.followup.send("Oyun kanalları sıfırlandı ve yeniden oluşturuldu. Bot yeniden başlatılıyor...", ephemeral=True)
    except discord.NotFound:
        print("Interaction timed out before followup could be sent.")
    
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.tree.command(name="istatistikleri-sıfırla", description="Tüm sunucu istatistiklerini sıfırlar. (Sadece Bot Sahibi)")
async def reset_stats(interaction: discord.Interaction):
    """Tüm sunucu istatistiklerini sıfırlar."""
    if await bot.is_owner(interaction.user):
        conn, cursor = get_db()
        cursor.execute('DELETE FROM user_scores')
        cursor.execute('UPDATE word_game_state SET used_words = last_word, last_user_id = NULL')
        cursor.execute('UPDATE counting_game_state SET current_number = 0, last_user_id = NULL')
        cursor.execute('UPDATE bom_game_state SET current_number = 0, last_user_id = NULL')
        conn.commit()
        conn.close()
        await interaction.response.send_message("Tüm istatistikler ve oyun durumları başarıyla sıfırlandı.", ephemeral=True)
    else:
        await interaction.response.send_message("Bu komutu sadece bot sahibi kullanabilir!", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    conn, cursor = get_db()
    
    # Sunucu ayarlarını al
    cursor.execute('SELECT word_game_channel, counting_game_channel, bom_game_channel FROM guild_settings WHERE guild_id = ?', (message.guild.id,))
    settings = cursor.fetchone()
    
    if not settings:
        await bot.process_commands(message)
        return

    word_ch, count_ch, bom_ch = settings

    # --- KELİME TÜRETME OYUNU ---
    if message.channel.id == word_ch:
        cursor.execute('SELECT last_word, last_user_id, used_words FROM word_game_state WHERE guild_id = ?', (message.guild.id,))
        state = cursor.fetchone()
        
        word = message.content.lower().strip()
        
        if word not in WORDS_LIST:
            await message.add_reaction('❓')
            return

        used_words = []
        if state:
            last_word, last_user_id, used_words_str = state
            used_words = used_words_str.split(',') if used_words_str else []
            
            if last_user_id == message.author.id:
                try:
                    await message.delete()
                except:
                    pass
                await message.channel.send(f"{message.author.mention}, Üst üste kelime yazamazsın!", delete_after=5)
                return
            
            if not word.startswith(last_word[-1]):
                try:
                    await message.delete()
                except:
                    pass
                await message.channel.send(f"{message.author.mention}, Kelime `{last_word[-1]}` harfi ile başlamalı!", delete_after=5)
                return
            
            if word in used_words:
                try:
                    await message.delete()
                except:
                    pass
                await message.channel.send(f"{message.author.mention}, Bu kelime daha önce kullanıldı!", delete_after=5)
                return
        
        # Kelime kabul edildi, türetilemeyecek harf kontrolü
        last_char = word[-1]
        possible_words = get_possible_words(last_char)
        
        # Kullanılan kelimeleri filtrele
        new_used_words = used_words + [word]
        remaining_words = [w for w in possible_words if w not in new_used_words]

        # Oyunun kazanılması için en az 4 kelime geçmiş olmalı (yeni yazılan dahil)
        if not remaining_words:
            if len(new_used_words) >= 4:
                # OYUN KAZANILDI
                update_score(message.guild.id, message.author.id, 10)
                await message.add_reaction('🏆')
                
                embed = discord.Embed(
                    title="🎉 OYUN KAZANILDI! 🎉",
                    description=f"**{message.author.mention}**, `{word}` kelimesiyle oyunu bitirdi! `{last_char}` harfi ile başlayan başka kelime kalmadı.\n\n**+10 Puan Kazandın!**",
                    color=discord.Color.gold()
                )
                await message.channel.send(embed=embed)
                
                # Yeni oyun başlat
                if WORDS_LIST:
                    new_start_word = random.choice(WORDS_LIST)
                else:
                    new_start_word = "elma"
                cursor.execute('''
                UPDATE word_game_state SET last_word = ?, last_user_id = NULL, used_words = ?
                WHERE guild_id = ?
                ''', (new_start_word, new_start_word, message.guild.id))
                conn.commit()
                
                await message.channel.send(f"Yeni oyun başlıyor! Başlangıç kelimesi: **{new_start_word}**")
                
                conn.close()
                await bot.process_commands(message)
                return
            else:
                # 'ğ' ile bitti ama 4 kelime dolmadı, kelimeyi kabul etme
                try:
                    await message.delete()
                except:
                    pass
                await message.channel.send(f"{message.author.mention}, Oyunu şu an bitiremezsin! En az 4 kelime yazıldıktan sonra oyunu sonlandırabilirsin.", delete_after=5)
                return
        else:
            # Normal devam
            cursor.execute('''
            INSERT INTO word_game_state (guild_id, last_word, last_user_id, used_words)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET last_word = ?, last_user_id = ?, used_words = ?
            ''', (message.guild.id, word, message.author.id, ",".join(new_used_words), word, message.author.id, ",".join(new_used_words)))
            conn.commit()
            try:
                await message.add_reaction('✅')
            except discord.NotFound:
                pass

    # --- SAYI SAYMA OYUNU ---
    elif message.channel.id == count_ch:
        if not message.content.isdigit():
            return

        cursor.execute('SELECT current_number, last_user_id FROM counting_game_state WHERE guild_id = ?', (message.guild.id,))
        state = cursor.fetchone()
        
        number = int(message.content)
        current_num = state[0] if state else 0
        last_user_id = state[1] if state else None

        if last_user_id == message.author.id:
            try:
                await message.delete()
            except:
                pass
            await message.channel.send(f"{message.author.mention}, Üst üste sayı sayamazsın!", delete_after=5)
            return

        if number == current_num + 1:
            cursor.execute('''
            INSERT INTO counting_game_state (guild_id, current_number, last_user_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET current_number = ?, last_user_id = ?
            ''', (message.guild.id, number, message.author.id, number, message.author.id))
            conn.commit()
            try:
                await message.add_reaction('✅')
            except discord.NotFound:
                pass
        else:
            try:
                await message.delete()
            except:
                pass
            await message.channel.send(f"{message.author.mention}, Hatalı sayı! `{current_num + 1}` yazman gerekiyordu. Oyun sıfırlandı!", delete_after=5)
            cursor.execute('UPDATE counting_game_state SET current_number = 0, last_user_id = NULL WHERE guild_id = ?', (message.guild.id,))
            conn.commit()

    # --- BOM OYUNU ---
    elif message.channel.id == bom_ch:
        cursor.execute('SELECT current_number, last_user_id FROM bom_game_state WHERE guild_id = ?', (message.guild.id,))
        state = cursor.fetchone()
        
        current_num = state[0] if state else 0
        last_user_id = state[1] if state else None
        next_num = current_num + 1

        if last_user_id == message.author.id:
            try:
                await message.delete()
            except:
                pass
            await message.channel.send(f"{message.author.mention}, Üst üste yazamazsın!", delete_after=5)
            return

        is_bom = (next_num % 5 == 0)
        content = message.content.lower().strip()

        if (is_bom and content == "bom") or (not is_bom and content == str(next_num)):
            cursor.execute('''
            INSERT INTO bom_game_state (guild_id, current_number, last_user_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET current_number = ?, last_user_id = ?
            ''', (message.guild.id, next_num, message.author.id, next_num, message.author.id))
            conn.commit()
            try:
                await message.add_reaction('✅')
            except discord.NotFound:
                pass
        else:
            try:
                await message.delete()
            except:
                pass
            correct_answer = "BOM" if is_bom else str(next_num)
            await message.channel.send(f"{message.author.mention}, Hatalı! `{correct_answer}` yazman gerekiyordu. Oyun sıfırlandı!", delete_after=5)
            cursor.execute('UPDATE bom_game_state SET current_number = 0, last_user_id = NULL WHERE guild_id = ?', (message.guild.id,))
            conn.commit()

    conn.close()
    await bot.process_commands(message)

bot.run(TOKEN)
