# 🚀 Quick Start Guide - RAGAS Evaluation

## ⚡ Langkah Cepat (3 Langkah)

### 1️⃣ Edit file `.env`
Buka file `.env` di folder ini dan ganti `your_openai_api_key_here` dengan API key Anda:

```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxx
```

💡 **Cara mendapatkan API key:**
- Buka https://platform.openai.com/api-keys
- Login atau buat akun OpenAI
- Klik "Create new secret key"
- Copy API key yang digenerate

### 2️⃣ Aktifkan Virtual Environment
```bash
.\venv\Scripts\activate
```

### 3️⃣ Jalankan Evaluasi
```bash
python app.py
```

## 📊 Output yang Dihasilkan

Script akan:
1. ✅ Mengevaluasi 3 sample data dari sistem RAG Anda
2. 📈 Mengukur 2 metrik utama:
   - **Faithfulness**: Konsistensi jawaban dengan context (0-1)
   - **Answer Correctness**: Kebenaran jawaban vs ground truth (0-1)
3. 💾 Menyimpan hasil ke file `score.csv`
4. 🖥️ Menampilkan hasil di terminal

## 📝 Sample Data yang Dievaluasi

Data yang digunakan adalah dari penelitian produktivitas padi di Kecamatan Kesesi:
- ✅ 3 pertanyaan tentang produktivitas padi
- ✅ 3 jawaban yang dihasilkan sistem RAG
- ✅ Dokumen-dokumen yang di-retrieve dari knowledge base
- ✅ Ground truth untuk pembanding

## 🔧 Troubleshooting

### Error: "OPENAI_API_KEY tidak ditemukan"
➡️ **Solusi**: Edit file `.env` dan masukkan API key Anda

### Error: "Module not found"
➡️ **Solusi**: Install ulang dependencies
```bash
pip install ragas python-dotenv datasets
```

### Script berjalan lama
➡️ **Normal!** RAGAS menggunakan LLM untuk evaluasi, bisa memakan waktu 2-5 menit

## 📖 Dokumentasi Lengkap

Lihat `README.md` untuk dokumentasi lengkap dan cara menggunakan data Anda sendiri.

## 💰 Biaya

⚠️ **Penting**: RAGAS menggunakan OpenAI API yang berbayar!
- Untuk 3 sample ini: ~$0.01 - $0.05 per run
- Pastikan Anda memiliki credit di akun OpenAI

## 🎯 Next Steps

Setelah berhasil menjalankan evaluasi:
1. Lihat hasil di file `score.csv`
2. Analisis metrik Faithfulness dan Answer Correctness
3. Modifikasi `data_samples` di `app.py` untuk menggunakan data Anda sendiri
4. Tambahkan lebih banyak metrik jika diperlukan
