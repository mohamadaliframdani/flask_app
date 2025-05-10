import os
import pandas as pd
import logging
import re
import html
from flask import Flask, request, render_template, redirect, url_for
from datetime import datetime

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = Flask(__name__)

# Konfigurasi logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def count_errors_from_csv(file_path):
    """ Membaca file CSV dan menghitung error transaction berdasarkan pola regex """
    error_counts = {}

    try:
        df = pd.read_csv(file_path, delimiter="|", usecols=["message"], dtype=str)

        for log_message in df["message"].dropna():
            match = re.search(r'.\w* (?:/api/|/notif/).*? HTTP/\d\.\d" \d{3}', log_message)
            if match:
                transaction = html.unescape(match.group().strip())  # Bersihkan encoding HTML
                error_counts[transaction] = error_counts.get(transaction, 0) + 1

    except Exception as e:
        logging.error(f"Error membaca file CSV: {e}")
        return {}

    return error_counts

def format_results(error_counts):
    """ Format hasil analisis dan kembalikan top errors serta total errors """
    sorted_errors = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    total_displayed_errors = sum(count for _, count in sorted_errors)

    return sorted_errors, total_displayed_errors

@app.route("/", methods=["GET", "POST"])
def index():
    """ Halaman utama untuk mengunggah file CSV dan melihat hasil analisis """
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join(UPLOADS_DIR, file.filename)
            file.save(file_path)

            return redirect(url_for("results", filename=file.filename))

    return render_template("index.html")

@app.route("/results/<filename>")
def results(filename):
    """ Menampilkan hasil analisis dari file CSV yang diunggah lalu menghapusnya """
    file_path = os.path.join(UPLOADS_DIR, filename)

    if not os.path.exists(file_path):
        logging.error(f"File {filename} tidak ditemukan!")
        return "Error: File tidak ditemukan!", 404

    error_counts = count_errors_from_csv(file_path)
    top_errors, total_displayed_errors = format_results(error_counts)

    current_date = datetime.now().strftime("%d-%b-%Y")

    # Hapus file setelah selesai diproses
    if os.path.exists(file_path):
        os.remove(file_path)
        logging.info(f"File {filename} berhasil dihapus setelah proses selesai.")

    return render_template("results.html", 
                           top_errors=top_errors, 
                           total_displayed_errors=total_displayed_errors, 
                           filename=filename, 
                           current_date=current_date)

if __name__ == "__main__":
    app.run(port=5000, debug=True)