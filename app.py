import os
import time
import requests
import pandas as pd
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename

# Flask app setup
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
RESULTS_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Variables pour suivre les transactions
start_time = time.time()
transaction_count = 0

# Utility functions
def simple_processing(data):
    """Apply a simple processing to the dataset."""
    for col in data.select_dtypes(include=["object"]).columns:
        # Incrémenter le compteur de transactions
        transaction_count += len(data[col])
        data[col] = data[col].str.upper()
    return data

def process_file(filepath):
    """Process the uploaded file and generate results."""
    data = pd.read_csv(filepath)

    # Processed data
    processed_data = simple_processing(data.copy())
    processed_path = os.path.join(RESULTS_FOLDER, "processed_data.csv")
    processed_data.to_csv(processed_path, index=False)

    # Selected data (example: non-null values in the first column)
    filter_column = data.columns[0]
    selected_data = data[data[filter_column].notnull()]
    selected_path = os.path.join(RESULTS_FOLDER, "selected_data.csv")
    selected_data.to_csv(selected_path, index=False)

    return processed_path, selected_path

# Fonction pour calculer les TPS 
def get_tps():
    global start_time, transaction_count
    elapsed_time = time.time() - start_time  # Temps écoulé depuis le début
    tps = transaction_count / elapsed_time if elapsed_time > 0 else 0
    return tps

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    global start_time, transaction_count

    # Vérifier si un fichier ou une URL a été envoyé
    file = request.files.get("file")
    google_sheet_url = request.form.get("googleSheetUrl")

    if file:
        # Traitement de l'upload de fichier
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        processed_path, selected_path = process_file(filepath)
    elif google_sheet_url:
        # Télécharger le fichier CSV depuis l'URL Google Sheets
        response = requests.get(google_sheet_url)
        if response.status_code == 200:
            filepath = os.path.join(UPLOAD_FOLDER, "google_sheet.csv")
            with open(filepath, "wb") as f:
                f.write(response.content)

            processed_path, selected_path = process_file(filepath)
        else:
            return jsonify({"error": "Failed to fetch the CSV from the Google Sheets URL"}), 400
    else:
        return jsonify({"error": "No file or Google Sheets URL provided"}), 400

    # Incrémenter le compteur de transactions
    transaction_count += 1

    # Calculer le TPS
    tps = get_tps()

    return jsonify({
        "processed_file": "/download/processed",
        "selected_file": "/download/selected",
        "tps": f"{tps:.2f}"  # Afficher le TPS avec 2 décimales
    })

@app.route("/download/<file_type>", methods=["GET"])
def download_file(file_type):
    if file_type == "processed":
        filepath = os.path.join(RESULTS_FOLDER, "processed_data.csv")
    elif file_type == "selected":
        filepath = os.path.join(RESULTS_FOLDER, "selected_data.csv")
    else:
        return jsonify({"error": "Invalid file type"}), 400

    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
