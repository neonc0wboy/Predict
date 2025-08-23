import os
import subprocess
from flask import Flask, request, jsonify
from mnemonic import Mnemonic

# Initialize the Flask application
app = Flask(__name__)
app.json.ensure_ascii = False
# Initialize the Mnemonic library for English words
#mnemo = Mnemonic("english")
mnemo = Mnemonic("russian")
# --- Helper Function to Generate Words ---
# This part replaces predict.py, prediction.py, and the complex shell commands
def generate_mnemonic_words():
    """
    Generates 12 random mnemonic words.
    """
    # Generate 16 bytes of random data for a 12-word mnemonic
    # os.urandom(16) is more standard for 12 words than 32 bytes.
    entropy = os.urandom(16) 
    
    # Generate the words from the random data
    words = mnemo.to_mnemonic(entropy)
    return words

# --- API Endpoint Definition ---
@app.route("/predict", methods=["POST"])
def get_prediction():
    """
    API endpoint to generate a prediction.
    Expects a JSON payload with 'name', 'date', and 'relationship'.
    """
    # 1. Get data from the incoming request
    try:
        data = request.get_json()
        user_name = data['name']
        prediction_date = data['date']
        relationship = data['relationship']
    except (TypeError, KeyError):
        # If data is not JSON or keys are missing, return an error
        return jsonify({"error": "Invalid request. Please provide 'name', 'date', and 'relationship' in the JSON body."}), 400

    # 2. Generate the "magic" words for the prediction
    try:
        # Here we call the function that encapsulates your word generation
        magic_words = generate_mnemonic_words()
        
        # If you still want to use your VANGA.sh script which might format these words:
        # Note: Ensure .shortcuts/VANGA.sh is executable (chmod +x .shortcuts/VANGA.sh)
        # and that it just prints the words to standard output.
        # For simplicity, we'll use the Python-generated words directly.
        
    except Exception as e:
        # Log the internal error for debugging
        print(f"Error generating words: {e}")
        return jsonify({"error": "Internal error during word generation."}), 500

    # 3. Construct the prompt for the tgpt command
    prompt = (
        f"предскажи будущее для '{user_name}' на '{prediction_date}', "
        f"он(она) является '{relationship}' для CH aka meta.c0wb0y, "
        f"используй следующие слова словно эти слова выпали при раскладе карт Тарро: '{magic_words}'"
    )

    # 4. Execute the tgpt command securely
    try:
        # IMPORTANT: We pass arguments as a list to prevent command injection.
        # This is much safer than building a single string to run in a shell.
        command = ["tgpt", prompt]
        
        # Run the command and capture the output
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,        # Decodes stdout/stderr as text
            check=True,       # Raises an exception if tgpt returns a non-zero exit code
            timeout=120       # Add a timeout of 2 minutes
        )
        
        prediction_text = result.stdout.strip()
        
    except FileNotFoundError:
        print("Error: 'tgpt' command not found. Is it installed and in your PATH?")
        return jsonify({"error": "The 'tgpt' command is not available on the server."}), 500
    except subprocess.CalledProcessError as e:
        # This catches errors from the tgpt command itself
        print(f"Error executing tgpt: {e.stderr}")
        return jsonify({"error": f"The tgpt command failed: {e.stderr}"}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "The prediction request timed out."}), 500


    # 5. Return the successful prediction
    return jsonify({
        "prediction_for": user_name,
        "date": prediction_date,
        "prediction": prediction_text,
        "seed_words": magic_words 
    })

if __name__ == "__main__":
    # Run the app. For development, debug=True is fine.
    # For production, use a proper WSGI server like Gunicorn.
    app.run(host="0.0.0.0", port=5000, debug=True)
