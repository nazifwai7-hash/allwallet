import csv
import random
import os
import psycopg2
from eth_account import Account
from datetime import datetime

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
    """Railway PostgreSQL veritabanına bağlan"""
    # Railway'in verdiği DATABASE_URL'i kullan
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        # Fallback: DATABASE_PUBLIC_URL dene
        database_url = os.environ.get('DATABASE_PUBLIC_URL')
    
    if not database_url:
        raise Exception("DATABASE_URL veya DATABASE_PUBLIC_URL bulunamadı!")
    
    print(f"✅ Veritabanına bağlanılıyor...")
    return psycopg2.connect(database_url)

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
        print("✅ Veritabanı tablosu hazır.")

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
        print(f"❌ Veritabanı hatası: {e}")
        conn.rollback()
        return False

def main():
    print("🚀 Mnemonic Generator Başlatılıyor...")
    print(f"⏰ Zaman: {datetime.now().isoformat()}")
    
    # Veritabanına bağlan
    try:
        conn = get_db_connection()
        init_database(conn)
        print("✅ PostgreSQL'e bağlanıldı.")
    except Exception as e:
        print(f"❌ Veritabanı bağlantı hatası: {e}")
        print("5 saniye içinde yeniden başlatılacak...")
        import time
        time.sleep(5)
        return
    
    # Kelimeleri yükle
    try:
        words = load_words("words.txt")
        if len(words) < 12:
            print(f"❌ Hata: En az 12 kelime gerekli. words.txt'te {len(words)} kelime var.")
            return
        print(f"✅ {len(words)} kelime yüklendi.")
    except FileNotFoundError:
        print("❌ Hata: words.txt dosyası bulunamadı!")
        return
    
    seen_addresses = set()
    total_attempts = 0
    saved_count = 0
    
    print(f"\n🎲 Rastgele 12 kelimelik mnemonic'ler üretiliyor...")
    print(f"💾 PostgreSQL veritabanına kaydediliyor...")
    print("Çıkmak için Ctrl+C tuşlayın.\n")

    # CSV yedekleme (opsiyonel)
    with open("output.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["seed", "address", "timestamp"])

        try:
            while True:
                total_attempts += 1
                
                # Rastgele 12 kelime seç (tekrarsız)
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
                    
                    # CSV'ye yedekle
                    writer.writerow([mnemonic, address, datetime.now().isoformat()])
                    f.flush()
                    
                    print(f"✅ #{total_attempts}: {address}")
                    print(f"   Seed: {mnemonic}\n")
                else:
                    print(f"⚠️ #{total_attempts}: {address} (zaten kayıtlı)")
                
                # Her 10 kayıtta rapor
                if saved_count % 10 == 0 and saved_count > 0:
                    print(f"📊 RAPOR: {saved_count} adres kaydedildi. ({total_attempts} deneme)\n")
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 DURDURULDU")
            print(f"   Toplam deneme: {total_attempts}")
            print(f"   Benzersiz adres: {len(seen_addresses)}")
            print(f"   Veritabanına kaydedilen: {saved_count}")
            print(f"   Çıktılar output.csv dosyasına yedeklendi.")
            conn.close()
            print("   Veritabanı bağlantısı kapatıldı.")
        except Exception as e:
            print(f"\n❌ Beklenmeyen hata: {e}")
            conn.close()

if __name__ == "__main__":
    main()
