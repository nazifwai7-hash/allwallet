import csv
import random
from eth_account import Account

def load_words(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def generate_random_mnemonic_no_repeat(word_list, length=12):
    return random.sample(word_list, length)

def mnemonic_to_eth_address(mnemonic_phrase):
    Account.enable_unaudited_hdwallet_features()
    acct = Account.from_mnemonic(mnemonic_phrase)
    return acct.address.lower()

def main():
    words = load_words("words.txt")
    if len(words) < 12:
        print(f"Hata: En az 12 kelime gerekli. words.txt'te {len(words)} kelime var.")
        return
    
    seen_addresses = set()
    total_attempts = 0
    
    print(f"Toplam {len(words)} kelime yüklendi.")
    print(f"Rastgele TEKRARSIZ 12 kelimelik mnemonic'ler üretiliyor...")
    print("Çıkmak için Ctrl+C tuşlayın.\n")

    with open("output.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["seed", "address"])

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

                writer.writerow([mnemonic, address])
                f.flush() 

                print(f"#{total_attempts}: {mnemonic} -> {address}")
                
        except KeyboardInterrupt:
            print(f"\n\nDurduruldu. Toplam {total_attempts} deneme yapıldı.")
            print(f"{len(seen_addresses)} benzersiz adres bulundu.")
            print(f"Çıktılar output.csv dosyasına kaydedildi.")

if __name__ == "__main__":
    main()