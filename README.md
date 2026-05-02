# 🎮 BYTIL - Discord Entertainment Bot

BYTIL, Discord sunucunuz için gelişmiş bir eğlence botudur. Üç farklı oyun (Kelime Türetme, Sayı Sayma, BOM) ve rekabeti canlı tutan bir puanlama/sıralama sistemi sunar.

## 🚀 Özellikler

- **🔡 Kelime Türetme:** Bir önceki kelimenin son harfiyle başlayan yeni kelimeler türetin. Kelime dağarcığınızı yarıştırın!
- **🔢 Sayı Sayma:** Sunucu üyeleriyle sırayla sayıları sayın. Hata yapan oyunu sıfırlar.
- **💣 BOM Oyunu:** 5 ve katlarında "BOM" yazarak dikkat seviyenizi test edin.
- **📊 Puanlama Sistemi:** Oyun kazandıkça puan toplayın ve sunucu sıralamasında (Aylık/Genel) zirveye oynayın.
- **🛠️ Kolay Kurulum:** Tek bir komutla tüm oyun kanallarını ve kategorileri otomatik oluşturun.

## 🛠️ Kurulum

1. **Gereksinimler:**
   - Python 3.8 veya üzeri
   - `discord.py`, `python-dotenv` kütüphaneleri

2. **Kurulum Adımları:**
   ```bash
   # Depoyu klonlayın
   git clone https://github.com/kullaniciadi/BYTIL.git
   cd BYTIL

   # Gerekli paketleri yükleyin
   pip install -r requirements.txt
   ```

3. **Yapılandırma:**
   - `.env` dosyası oluşturun ve Discord bot tokeninizi ekleyin:
     ```env
     TOKEN=YOUR_DISCORD_BOT_TOKEN
     ```

4. **Veritabanı Hazırlığı:**
   ```bash
   python database.py
   ```

5. **Botu Başlatın:**
   ```bash
   python main.py
   ```

## 🎮 Komutlar

- `/kurulum`: Oyun kanallarını otomatik oluşturur (Sadece Sunucu Sahibi).
- `/sıralama`: Aylık en yüksek puanlı oyuncuları listeler.
- `/reboot`: Oyun kanallarını silip yeniden oluşturur ve botu yeniler.
- `/istatistikleri-sıfırla`: Tüm puanları ve oyun durumlarını sıfırlar.

## 📝 Oyun Kuralları

- **Kelime Türetme:**
  - Kelimeler `words.txt` içinde tanımlı olmalıdır.
  - Aynı kullanıcı üst üste kelime yazamaz.
  - Oyunun kazanılması için en az 4 kelime türetilmiş olmalı ve yeni kelime türetilecek harf kalmamalıdır.
- **Sayı Sayma & BOM:**
  - Sırayı bozmak veya hatalı sayı yazmak oyunu sıfırlar.
  - Üst üste yazmak yasaktır.

## 📄 Lisans

Bu proje MIT lisansı ile lisanslanmıştır.
