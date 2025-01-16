from flask import Flask, request, jsonify, send_file, render_template
import pandas as pd
import os
from werkzeug.utils import secure_filename

# Flask app setup
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
RESULTS_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Utility functions
def simple_processing(data):
    """Apply a simple processing to the dataset."""
    for col in data.select_dtypes(include=["object"]).columns:
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

# Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Process the file
        processed_path, selected_path = process_file(filepath)

        return jsonify({
            "processed_file": "/download/processed",
            "selected_file": "/download/selected"
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

# Run the app
if __name__ == "__main__":
    #app.run(debug=True)
    app.run(debug=True, host="0.0.0.0", port=os.environ.get("PORT", 5000))

