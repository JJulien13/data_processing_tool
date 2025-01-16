import os
import time
import hashlib
import requests
import pandas as pd
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from threading import Thread

# Flask app setup
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
RESULTS_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Variables pour suivre les transactions
start_time = time.time()
transaction_count = 0

# Variable pour stocker l'empreinte (hash) du fichier téléchargé
last_file_hash = None

# Utility functions
def simple_processing(data):
    global start_time, transaction_count
    """Apply a simple processing to the dataset."""
    for col in data.select_dtypes(include=["object"]).columns:
        data[col] = data[col].str.upper()
        # Incrémenter le compteur de transactions
        transaction_count += len(data[col])
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

def download_and_check_google_sheet(google_sheet_url):
    """Télécharger le fichier Google Sheets et vérifier les changements"""
    global last_file_hash
    response = requests.get(google_sheet_url)
    
    if response.status_code == 200:
        # Calculer le hash du fichier téléchargé
        file_hash = hashlib.md5(response.content).hexdigest()

        # Comparer l'empreinte du fichier avec la précédente
        if file_hash != last_file_hash:
            # Si le fichier a changé, traiter les données
            filepath = os.path.join(UPLOAD_FOLDER, "google_sheet.csv")
            with open(filepath, "wb") as f:
                f.write(response.content)

            processed_path, selected_path = process_file(filepath)
            # Mettre à jour l'empreinte du fichier
            last_file_hash = file_hash
            return processed_path, selected_path
        else:
            print("No changes detected in the Google Sheets file.")
            return None, None
    else:
        print(f"Failed to fetch the CSV from the Google Sheets URL. Status code: {response.status_code}")
        return None, None

# Fonction pour vérifier le Google Sheet à intervalle régulier
def check_for_updates(google_sheet_url):
    """Vérifier périodiquement les mises à jour du fichier Google Sheets"""
    while True:
        download_and_check_google_sheet(google_sheet_url)
        time.sleep(60)  # Attendre 60 secondes avant de vérifier à nouveau

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
        processed_path, selected_path = download_and_check_google_sheet(google_sheet_url)

        if processed_path is None:
            return jsonify({"error": "No changes detected in the Google Sheets file"}), 400
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
    # Lancer la vérification périodique dans un thread séparé
    google_sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQVbfMxx1JbwNdxjwUmnaxdfkk_sdiWaJ6bhugmPpRvI_dqSoEJK2KcFqYoYAhVbZnJz9qCngZX_fs/pub?output=csv"
    update_thread = Thread(target=check_for_updates, args=(google_sheet_url,))
    update_thread.daemon = True
    update_thread.start()

    app.run(debug=True, host='0.0.0.0', port=5000)
