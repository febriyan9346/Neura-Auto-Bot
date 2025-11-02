# Neura Auto Bot

Bot otomatis untuk melakukan swap token pada Neura Protocol Testnet secara berkala.

## 📸 Bot in Action

![image](https://github.com/user-attachments/assets/29cf2c79-3b48-461f-b29e-410589b2570f)

## Fitur

- ✅ Multi-wallet support
- ✅ Auto swap token dengan retry mechanism
- ✅ Swap bolak-balik otomatis (A → B → A)
- ✅ Loop 24 jam otomatis
- ✅ Logging berwarna dan informatif
- ✅ Manajemen gas fee otomatis
- ✅ Auto approval token ERC20

## Persyaratan

- Python 3.8 atau lebih tinggi
- Private key wallet yang sudah memiliki ANKR token di Neura Testnet

## Instalasi

1. Clone repository ini:
```bash
git clone https://github.com/febriyan9346/Neura-Auto-Bot.git
cd Neura-Auto-Bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Buat file `.env` dan tambahkan private key Anda:
```bash
cp .env.example .env
```

4. Edit file `.env` dan masukkan private key Anda:
```env
PRIVATE_KEY_1=your_private_key_here
PRIVATE_KEY_2=your_private_key_here
PRIVATE_KEY_3=your_private_key_here
```

## Cara Menggunakan

1. Jalankan bot:
```bash
python bot.py
```

2. Pilih token yang ingin di-swap:
   - Masukkan nomor token DARI (misalnya: 1 untuk ANKR)
   - Masukkan nomor token KE (misalnya: 2 untuk USDC)
   - Masukkan jumlah token yang ingin di-swap
   - Masukkan berapa kali swap per wallet (default: 1)

3. Bot akan:
   - Melakukan swap dari Token A ke Token B
   - Menunggu 10 detik
   - Melakukan swap kembali dari Token B ke Token A
   - Mengulangi proses sesuai jumlah yang ditentukan
   - Loop setiap 24 jam

## Konfigurasi

### Multi-Wallet Setup

Anda dapat menambahkan multiple wallet dengan menambahkan private key di file `.env`:

```env
PRIVATE_KEY_1=0x...
PRIVATE_KEY_2=0x...
PRIVATE_KEY_3=0x...
# Tambahkan sebanyak yang Anda butuhkan
```

### Network Configuration

Bot menggunakan Neura Protocol Testnet:
- RPC: `https://testnet.rpc.neuraprotocol.io/`
- Explorer: `https://testnet.neuraprotocol.io/`

## Struktur File

```
Neura-Auto-Bot/
├── bot.py              # Script utama bot
├── .env                # File konfigurasi (private keys)
├── .env.example        # Template file .env
├── requirements.txt    # Dependencies Python
└── README.md          # Dokumentasi
```

## Keamanan

⚠️ **PENTING:**
- Jangan pernah share file `.env` Anda
- Jangan commit private key ke GitHub
- File `.env` sudah ditambahkan ke `.gitignore`
- Gunakan wallet testnet, jangan gunakan wallet mainnet

## Troubleshooting

### Error: Tidak ada PRIVATE_KEY ditemukan
- Pastikan file `.env` ada dan berisi private key
- Pastikan format: `PRIVATE_KEY_1=0x...`

### Error: Swap gagal
- Pastikan wallet memiliki cukup ANKR untuk gas fee
- Periksa koneksi internet Anda
- Bot akan otomatis retry hingga 3 kali

### Error: Allowance sudah mencukupi
- Ini bukan error, artinya token sudah di-approve sebelumnya
- Bot akan lanjut ke proses swap

## Kontribusi

Kontribusi selalu diterima! Silakan buat Pull Request atau Issue untuk perbaikan dan saran.

## Disclaimer

Bot ini dibuat untuk tujuan edukasi dan testing di Neura Protocol Testnet. Gunakan dengan risiko Anda sendiri. Developer tidak bertanggung jawab atas kehilangan dana atau masalah lainnya.

## Lisensi

MIT License

## Kontak

GitHub: [@febriyan9346](https://github.com/febriyan9346)

---

⭐ Jangan lupa berikan star jika bot ini membantu Anda!
