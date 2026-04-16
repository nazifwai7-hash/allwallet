import csv
import random
import os
import psycopg2
from psycopg2.extras import Json
from eth_account import Account
from datetime import datetime
from urllib.parse import urlparse

def load_words(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def generate_random_mnemonic_no_repeat(word_list, length=12):
    return random.sample(word_list, length)

def mnemonic_to_eth_address(mnemonic_phrase):
    Account.enable_unaudited_hdwallet_features()
    acct = Account.from_mnemonic(mnemonic_phrase)
    return acct.address.lower()

def get_db_connection():
    """PostgreSQL veritabanına bağlan"""
    # Önce ortam değişkenini kontrol et (Railway, Heroku, vs.)
    database_url = os.environ.get('postgresql://postgres:yFuJterVtBVLBprWOcCSqvnnzeLKyYHJ@postgres.railway.internal:5432/railway')
    
    if database_url:
        # Railway/Heroku formatı: postgresql://user:pass@host:port/dbname
        return psycopg2.connect(database_url)
    else:
        # Local PostgreSQL bağlantısı (varsayılan)
        return psycopg2.connect(
            host=os.environ.get('DB_HOST', 'postgresql://postgres:yFuJterVtBVLBprWOcCSqvnnzeLKyYHJ@postgres.railway.internal:5432/railway'),
            database=os.environ.get('DB_NAME', 'railway'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', 'yFuJterVtBVLBprWOcCSqvnnzeLKyYHJ'),
            port=os.environ.get('DB_PORT', '5432')
        )

def init_database(conn):
    """Veritabanı tablosunu oluştur"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mnemonic_results (
                id SERIAL PRIMARY KEY,
                seed TEXT NOT NULL,
                address TEXT NOT NULL UNIQUE,
                attempt_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # İndeksler
        cur.execute("CREATE INDEX IF NOT EXISTS idx_address ON mnemonic_results(address)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON mnemonic_results(created_at)")
        
        conn.commit()
        print("✓ Veritabanı tablosu hazır.")

def save_to_database(conn, mnemonic, address, attempt_number):
    """Mnemonic ve address'i veritabanına kaydet"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO mnemonic_results (seed, address, attempt_number)
                VALUES (%s, %s, %s)
                ON CONFLICT (address) DO NOTHING
                RETURNING id
            """, (mnemonic, address, attempt_number))
            
            result = cur.fetchone()
            conn.commit()
            return result is not None
    except Exception as e:
        print(f"Veritabanı hatası: {e}")
        conn.rollback()
        return False

def main():
    # Veritabanına bağlan
    try:
        conn = get_db_connection()
        init_database(conn)
        print(f"✅ PostgreSQL'e bağlanıldı.")
    except Exception as e:
        print(f"❌ Veritabanı bağlantı hatası: {e}")
        print("Devam etmek için ENTER tuşuna bas...")
        input()
        return
    
    # Kelimeleri yükle
    words = load_words("words.txt")
    if len(words) < 12:
        print(f"Hata: En az 12 kelime gerekli. words.txt'te {len(words)} kelime var.")
        return
    
    seen_addresses = set()
    total_attempts = 0
    saved_count = 0
    
    print(f"\n📚 Toplam {len(words)} kelime yüklendi.")
    print(f"🎲 Rastgele TEKRARSIZ 12 kelimelik mnemonic'ler üretiliyor...")
    print(f"💾 PostgreSQL veritabanına kaydediliyor...")
    print("Çıkmak için Ctrl+C tuşlayın.\n")

    # CSV'ye de yedekle (opsiyonel)
    with open("output.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["seed", "address", "timestamp"])

        try:
            while True:
                total_attempts += 1
                
                # Rastgele TEKRARSIZ 12 kelime seç
                random_words = generate_random_mnemonic_no_repeat(words, 12)
                mnemonic = " ".join(random_words)
                
                try:
                    address = mnemonic_to_eth_address(mnemonic)
                except Exception as e:
                    continue
                
                if address in seen_addresses:
                    continue
                
                seen_addresses.add(address)
                
                # PostgreSQL'e kaydet
                if save_to_database(conn, mnemonic, address, total_attempts):
                    saved_count += 1
                    
                    # CSV'ye de yedekle
                    writer.writerow([mnemonic, address, datetime.now().isoformat()])
                    f.flush()
                    
                    print(f"✓ #{total_attempts}: {mnemonic[:50]}... -> {address} (DB'ye kaydedildi, toplam: {saved_count})")
                else:
                    print(f"⚠️ #{total_attempts}: {mnemonic[:50]}... -> {address} (Zaten kayıtlı veya hata)")
                
                # Her 10 kayıtta bir rapor
                if saved_count % 10 == 0 and saved_count > 0:
                    print(f"\n📊 RAPOR: {saved_count} adres veritabanına kaydedildi. ({total_attempts} deneme)\n")
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 DURDURULDU")
            print(f"   Toplam deneme: {total_attempts}")
            print(f"   Benzersiz adres: {len(seen_addresses)}")
            print(f"   Veritabanına kaydedilen: {saved_count}")
            print(f"   Çıktılar output.csv dosyasına yedeklendi.")
            conn.close()
            print("   Veritabanı bağlantısı kapatıldı.")

if __name__ == "__main__":
    main()
