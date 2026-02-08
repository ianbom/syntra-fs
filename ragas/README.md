# RAGAS Evaluation untuk RAG System

Script ini menggunakan [RAGAS](https://github.com/explodinggradients/ragas) untuk mengevaluasi kualitas sistem RAG (Retrieval-Augmented Generation).

## 📋 Prerequisites

1. Python 3.11+
2. Virtual environment sudah aktif
3. OpenAI API Key

## 🚀 Cara Menggunakan

### 1. Setup API Key

Edit file `.env` dan masukkan OpenAI API key Anda:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 2. Jalankan Script

```bash
# Aktifkan virtual environment (jika belum)
.\venv\Scripts\activate

# Jalankan evaluasi
python app.py
```

## 📊 Metrik yang Dievaluasi

Script ini mengevaluasi 5 metrik utama:

| Metrik | Deskripsi | Range |
|--------|-----------|-------|
| **Faithfulness** | Konsistensi jawaban dengan context yang diberikan | 0-1 |
| **Answer Relevancy** | Relevansi jawaban terhadap pertanyaan | 0-1 |
| **Context Precision** | Ketepatan context yang di-retrieve | 0-1 |
| **Context Recall** | Kelengkapan informasi penting yang ter-retrieve | 0-1 |
| **Answer Correctness** | Kebenaran jawaban dibanding ground truth | 0-1 |

**Semakin tinggi skor (mendekati 1), semakin baik!**

## 📝 Format Data

### Format Input dari API Anda:

```python
{
    'query': ['pertanyaan1', 'pertanyaan2', ...],
    'generated_response': ['jawaban1', 'jawaban2', ...],
    'retrieved_documents': [
        [['dokumen1_q1'], ['dokumen2_q1']],
        [['dokumen1_q2'], ['dokumen2_q2']],
        ...
    ],
    'ground_truths': ['truth1', 'truth2', ...]
}
```

### Format RAGAS (otomatis dikonversi):

```python
{
    'question': [...],
    'answer': [...],
    'contexts': [...],
    'ground_truth': [...]
}
```

## 💡 Contoh Penggunaan

### Opsi 1: Menggunakan Sample Data Built-in

Script sudah menyertakan sample data dan akan otomatis menjalankan evaluasi dengan data tersebut.

### Opsi 2: Menggunakan Data Anda Sendiri

```python
from app import evaluate_from_api_format

# Data dalam format API Anda
your_data = {
    'query': ['Apa faktor yang mempengaruhi produktivitas padi'],
    'generated_response': ['Faktor-faktor yang mempengaruhi adalah...'],
    'retrieved_documents': [[
        'Document 1 content...',
        'Document 2 content...'
    ]],
    'ground_truths': ['Ground truth answer...']
}

# Jalankan evaluasi
results = evaluate_from_api_format(your_data)
```

## 📈 Interpretasi Hasil

- **≥ 0.8**: Excellent ⭐⭐⭐
- **0.6 - 0.8**: Good ⭐⭐
- **0.4 - 0.6**: Fair ⭐
- **< 0.4**: Needs Improvement ⚠️

## 🔧 Troubleshooting

### Error: OPENAI_API_KEY tidak ditemukan

Pastikan file `.env` sudah dibuat dan berisi API key yang valid:

```bash
OPENAI_API_KEY=sk-your-actual-key
```

### Error: Module not found

Install ulang dependencies:

```bash
pip install ragas python-dotenv
```

## 📚 Dokumentasi RAGAS

Untuk informasi lebih lanjut tentang RAGAS: https://docs.ragas.io/

## 🎯 Next Steps

1. Ganti `your_openai_api_key_here` di file `.env` dengan API key Anda yang sebenarnya
2. Jalankan `python app.py` untuk melihat evaluasi dengan sample data
3. Uncomment baris terakhir di `app.py` untuk evaluasi dengan data Anda sendiri
4. Integrasikan fungsi `evaluate_from_api_format()` ke dalam sistem RAG Anda
