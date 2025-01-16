from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_data():
    data = request.json.get("data")
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Exemple de traitement simple (vous pouvez adapter)
    processed = {k: v.upper() if isinstance(v, str) else v for k, v in data.items()}
    return jsonify({"processed_data": processed})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
