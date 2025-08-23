import os
import subprocess
from flask import Flask, request, jsonify, render_template
from mnemonic import Mnemonic

# Initialize the Flask application
app = Flask(__name__)
app.json.ensure_ascii = False

# --- 1. Authentication: Define your valid invite codes ---
VALID_INVITE_CODES = {
    "SECRET123",
    "MAGIC_KEY",
    "COWBOY_CODE"
}

# --- 2. Themes: Create different prompt templates ---
PROMPT_TEMPLATES = {
    "Карты Tarot (T)": (
        "предскажи будущее для '{user_name}' на '{prediction_date}', "
        "он(она) является '{relationship}' для CH aka meta.c0wb0y. "
        "Используй следующие слова словно эти слова выпали при раскладе карт Таро: '{magic_words}'"
    ),
    "Скандинавские руны (SK)": (
        "Дайте мистическое предсказание для '{user_name}' на дату '{prediction_date}'."
        "Они имеют '{relationship}' к CH, также известному как meta.c0wb0y. "
        "Интерпретируйте эти слова как древние скандинавские руны, высеченные на камне: '{magic_words}'"
),
    "Научная фантастика (SF)": (
        "Из центральных банков данных ИИ создайте системную проекцию для человека, известного как '{user_name}', на звёздную дату '{prediction_date}'."
        "Его связь с системным оператором 'meta.c0wb0y' зарегистрирована как '{relationship}'."
        "Обработайте следующие фрагменты данных из повреждённого файла журнала в качестве основы для проекции: '{magic_words}'"
)
}

# Initialize the Mnemonic library
mnemo = Mnemonic("russian")
#mnemo = Mnemonic("english")

def generate_mnemonic_words():
    """Generates 12 random mnemonic words."""
    entropy = os.urandom(32)
    return mnemo.to_mnemonic(entropy)

@app.route("/")
def home():
    """Serves the main HTML page."""
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def get_prediction():
    """
    API endpoint to generate a prediction.
    Now requires an 'invite_code' and accepts a 'theme'.
    """
    try:
        data = request.get_json()
        invite_code = data.get('invite_code')
        user_name = data['name']
        theme = data.get('theme', 'Карты Tarot (T)')
    except (TypeError, KeyError):
        return jsonify({"error": "Invalid request format."}), 400

    if not invite_code or invite_code not in VALID_INVITE_CODES:
        return jsonify({"error": "A valid invite_code is required."}), 403

    prompt_template = PROMPT_TEMPLATES.get(theme, PROMPT_TEMPLATES['Карты Tarot (T)'])
    magic_words = generate_mnemonic_words()
    prediction_date = "ближайшее будущее"
    relationship = "является"
    prompt = prompt_template.format(
        user_name=user_name,
        prediction_date=prediction_date,
        relationship=relationship,
        magic_words=magic_words
    )

    try:
        # --- THE ONLY CHANGE IS ON THIS LINE ---
        command = ["tgpt", "-s", "-w", prompt] # Added the "-w" flag
        result = subprocess.run(
            command,
            capture_output=True, text=True, check=True, timeout=120
        )
        prediction_text = result.stdout.strip()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to generate prediction from the external tool."}), 500

    return jsonify({
        "prediction_for": user_name,
        "prediction": prediction_text,
        "seed_words": magic_words,
        "theme": theme
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
