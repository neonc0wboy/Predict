import os
import subprocess
import requests
import base64
import urllib.parse
from flask import Flask, request, jsonify, render_template
from mnemonic import Mnemonic
from dotenv import load_dotenv
from google import genai
from google.genai import types
import datetime
# Load environment variables from the .env file first
load_dotenv()

# --- 1. Configuration ---
# Initialize the Flask application
app = Flask(__name__)
app.json.ensure_ascii = False

# Get the API Key from the environment. The app will fail to start if it's not set.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY set in the .env file or environment variables")

# Initialize the Google GenAI client with the key
client = genai.Client(api_key=GOOGLE_API_KEY)

# Configured Models
GEMINI_MODEL = "gemini-3.1-flash-lite"# Используем :generateContent вместо :streamGenerateContent для корректного парсинга JSON

# Настройки безопасности и лимиты
VALID_INVITE_CODES = {"SECRET123", "MAGIC_KEY", "COWBOY_CODE"}

PROMPT_TEMPLATES = {
    "Tarot": (
        "предскажи будущее для '{user_name}' на '{prediction_date}', "
        "Используй следующие слова словно эти слова выпали при раскладе карт Таро: '{magic_words}'. "
        "С обязательным переводом этих слов на русский язык и интерпретацией их, согласно контексту."
    ),
    "Runes": (
        "Дайте мистическое предсказание для '{user_name}' на дату '{prediction_date}'."
        "Интерпретируйте эти слова, с обязательным переводом на русский язык, так, как если бы они были древними норвежскими рунами, вырезанными на камне: '{magic_words}'"
    ),
    "Sci-Fi": (
        "Из центральных баз данных ИИ, сгенерировать системную проекцию для человека, известного как '{user_name}', на дату '{prediction_date}'."
        "Обработать следующие фрагменты данных из поврежденного файла журнала в качестве основы для проекции: '{magic_words}', с обязательным переводом на русский язык."
    ),
    "Stars": (
        "Составь астрологический прогноз для '{user_name}' на '{prediction_date}'. "
        "Интерпретируй эти символы как cosmic знамения и положения звезд: '{magic_words}'. "
        "С обязательным переводом на русский язык и астрологической трактовкой."
    ),
    "Numbers": (
        "Сделай нумерологическое предсказание для '{user_name}' на '{prediction_date}'. "
        "Проанализируй эти слова как сакральные числовые вибрации и нумерологические коды: '{magic_words}'. "
        "С обязательным переводом на русский язык и нумерологической расшифровкой."
    )
}

mnemo = Mnemonic("russian")
mnemo1 = Mnemonic("english")

def generate_mnemonic_words():
    entropy = os.urandom(16)
    return str(f"{mnemo.to_mnemonic(entropy)}{' '}{mnemo1.to_mnemonic(entropy)}")

def call_gemini_api(prompt: str) -> str:
    """
    Отправляет POST запрос к Gemini API с использованием библиотеки requests.
    """
    try:
        interaction = client.interactions.create(
            model=GEMINI_MODEL,
            input=prompt
        )
        
        # Grab the text response using the output_text helper
        if hasattr(interaction, 'output_text') and interaction.output_text:
            return interaction.output_text
        elif hasattr(interaction, 'steps') and interaction.steps:
            return interaction.steps[-1].content[0].text
        else:
            raise RuntimeError("Received an empty response from the Gemini API.")
            
    except Exception as e:
        print(f"Gemini API request failed: {e}")
        raise RuntimeError(f"Failed to connect to the Gemini API: {e}")


def generate_image_prompt_from_prediction(prediction_text: str, theme: str) -> str:
    """
    Просит Gemini составить визуальный английский промпт на основе предсказания под стиль выбранной темы.
    """
    style_guidelines = {
        "Tarot": (
            "The output must describe a mystical tarot card. "
            "Incorporate detailed, ornate gold and silver borders, celestial bodies (moons, stars), "
            "occult symbols, and a hand-drawn dark fantasy illustration style."
        ),
        "Runes": (
            "The output must describe a weathered ancient stone slab with glowing Norse runes carved into it. "
            "Incorporate ethereal blue or orange runic magic, mossy stone textures, dark foggy forest backgrounds, "
            "and a cinematic, realistic fantasy style."
        ),
        "Sci-Fi": (
            "The output must describe a high-tech sci-fi holographic interface. "
            "Incorporate glowing grid terminals, neon green or cyan system logs, complex HUD overlay elements, "
            "and a futuristic cyberpunk digital art style."
        ),
        "Stars": (
            "The output must describe a celestial star chart or cosmic map. "
            "Incorporate glowing constellations, zodiac alignments, deep cosmic nebulas, "
            "and a magical space fantasy aesthetic."
        ),
        "Numbers": (
            "The output must describe sacred geometry combined with numerical codes. "
            "Incorporate neon-glowing mathematical formulas, glowing digital grids, abstract golden ratio shapes, "
            "and a mysterious dark esoteric style."
        )
    }
    
    selected_style = style_guidelines.get(theme, style_guidelines["Tarot"])
    
    instruction = (
        f"Write a highly detailed, concise visual prompt (in English) for an AI image generator "
        f"based on the following {theme} prediction.\n\n"
        f"STRICT STYLE GUIDELINES:\n{selected_style}\n\n"
        f"Describe only key visual elements, the medium, and the lighting. Keep the prompt short (under 40 words). "
        f"Do not write any introductory or explanatory text. Output ONLY the prompt itself.\n\n"
        f"Prediction text:\n{prediction_text}"
    )
    
    try:
        # Получаем визуальный промпт через Gemini
        generated_prompt = call_gemini_api(instruction)
        return generated_prompt.strip().strip('"`\'')
    except Exception as e:
        print(f"Failed to generate prompt for image generator: {e}")
        fallbacks = {
            "Tarot": "A beautiful detailed mystical tarot card, ornate golden borders, glowing symbols, dark magic aesthetic, hand-drawn digital art",
            "Runes": "Ancient nordic runes glowing with blue light carved on a dark weathered stone slab, mystical fog, epic fantasy painting",
            "Sci-Fi": "Futuristic cyberpunk terminal screen with glowing green matrix code, holographic digital interface, sci-fi HUD",
            "Stars": "Celestial star chart, glowing gold constellations, deep dark blue space background, cosmic fantasy nebula",
            "Numbers": "Sacred geometry, glowing golden numerology codes, digital grid matrix, mysterious esoteric background"
        }
        return fallbacks.get(theme, fallbacks["Tarot"])


def generate_image_from_prompt(image_prompt: str) -> str:
    """
    Генерирует изображение через API Pollinations.ai и возвращает его в формате Base64.
    """
    try:
        encoded_prompt = urllib.parse.quote(image_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            return image_base64
        else:
            print(f"Pollinations returned status code: {response.status_code}")
            return ""
    except Exception as e:
        print(f"Image generation failed: {e}")
        return ""


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def get_prediction():
    data = request.get_json()
    
    # Валидация входных данных
    if not all(k in data for k in ['name', 'theme', 'date_for', 'invite_code']):
        return jsonify({"error": "Missing required fields."}), 400
    if data['invite_code'] not in VALID_INVITE_CODES:
        return jsonify({"error": "A valid invite_code is required."}), 403
        
    theme = data.get('theme')
    prompt_template = PROMPT_TEMPLATES.get(theme, PROMPT_TEMPLATES["Tarot"])
    magic_words = generate_mnemonic_words()
    today = datetime.date.today()
    
    # Форматирование промпта
    prompt = prompt_template.format(
        user_name=data['name'],
        prediction_date=f"Сегодня {today.day}/{today.month}/{today.year} предсказываем на {data['date_for']}",
        magic_words=magic_words
    )
    
    # 1. Текстовое предсказание через Gemini
    try:
        prediction_text = call_gemini_api(prompt)
        print("Successfully generated prediction using Gemini API.")
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    # 2. Формирование визуального промпта под стиль выбранной темы
    visual_prompt = generate_image_prompt_from_prediction(prediction_text, theme)
    print(f"Visual prompt generated: {visual_prompt}")

    # 3. Генерация картинки на Pollinations.ai
    image_base64 = generate_image_from_prompt(visual_prompt)
    if image_base64:
        print("Successfully generated prediction image using Pollinations.ai.")
    else:
        print("Image generation failed (continuing without image).")

    # Формирование итогового ответа
    return jsonify({
        "prediction_for": data['name'],
        "prediction": prediction_text,
        "seed_words": magic_words,
        "theme": theme,
        "image_data": f"data:image/jpeg;base64,{image_base64}" if image_base64 else None
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)