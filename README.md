# 💌 Dekat di Hati — LDR Couple Website

Website romantis untuk pasangan LDR. Dibangun dengan Flask + Supabase, deploy ke Vercel.

## ✨ Fitur

- 🗓️ **Countdown Timer** — Hitung mundur ke tanggal ketemu, bisa diatur sendiri
- 🌸 **Mood Check-in** — Kirim mood harian, lihat mood pasangan
- 💬 **Status "Lagi Ngapain"** — Real-time status mini
- ✉️ **Love Letter Box** — Surat dengan time-lock (buka di tanggal tertentu)
- 📖 **Shared Diary** — Diary berdua + love reactions
- 📸 **Memory Board** — Koleksi foto kenangan
- 🕐 **Dual Clock** — Jam dua kota + jarak dalam km

---

## 🚀 Cara Deploy ke Vercel

### Langkah 1 — Setup Supabase

1. Buka [supabase.com](https://supabase.com) → masuk ke project kamu
2. Pergi ke **SQL Editor**
3. Copy semua isi file `supabase_schema.sql` → paste → **Run**
4. Semua tabel otomatis terbuat ✅

### Langkah 2 — Deploy ke Vercel

**Cara A: Via GitHub (Rekomendasi)**
1. Upload folder ini ke GitHub repository
2. Masuk ke [vercel.com](https://vercel.com) → **New Project**
3. Import repo tersebut
4. Tambah **Environment Variables**:
   ```
   SUPABASE_URL = https://mafnnqttvkdgqqxczqyt.supabase.co
   SUPABASE_ANON_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   SUPABASE_SERVICE_KEY = (dari Supabase → Settings → API → service_role)
   SECRET_KEY = (string random panjang, misal: abc123xyz456random)
   ```
5. Klik **Deploy** 🎉

**Cara B: Via Vercel CLI**
```bash
npm i -g vercel
cd ldr-app
vercel
# Ikuti instruksinya, lalu set env vars di dashboard Vercel
```

### Langkah 3 — Cara Pakai

1. Buka website → **Daftar** akun (kamu & pasangan daftar masing-masing)
2. Masuk ke **Pengaturan**:
   - Isi nama, kota, timezone kamu
   - Isi email pasangan
   - Set jarak & timezone dia
   - Isi tanggal ketemu berikutnya
3. Selesai! Kalian bisa pakai semua fitur 💕

---

## 📁 Struktur File

```
ldr-app/
├── app.py                  # Backend Flask utama
├── requirements.txt        # Dependencies Python
├── vercel.json             # Konfigurasi Vercel
├── supabase_schema.sql     # SQL buat semua tabel
├── .env.example            # Contoh env vars
└── templates/
    ├── base.html           # Template dasar (nav, style global)
    ├── login.html          # Halaman login
    ├── register.html       # Halaman daftar
    ├── dashboard.html      # Beranda (countdown, mood, jam, status)
    ├── letters.html        # Love letter box
    ├── journal.html        # Diary berdua
    ├── memories.html       # Memory board
    └── settings.html       # Pengaturan
```

---

## 🔐 Catatan Keamanan

- Ganti `SECRET_KEY` dengan string random yang panjang
- Jangan upload file `.env` ke GitHub (sudah ada di `.gitignore`)
- `SUPABASE_SERVICE_KEY` jangan diekspos ke frontend

---

Made with 💕 for LDR couples everywhere
