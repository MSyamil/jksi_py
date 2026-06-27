import io
import json
import logging
from PIL import Image
import google.generativeai as genai
from openai import OpenAI
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIClient")

class AIClient:
    @staticmethod
    def _get_gemini_client(api_key: str):
        genai.configure(api_key=api_key)
        return genai

    @staticmethod
    def _get_openai_client(api_key: str):
        return OpenAI(api_key=api_key)

    @classmethod
    def analyze_page_state(cls, dom_structure: str, screenshot_bytes: bytes, goal: str, history: list, provider: str = None, model: str = None, api_key: str = None) -> dict:
        """
        Send DOM + Screenshot + Goal + History to AI and get the next action.
        Returns a dict: {thought, action, selector, value, reason}
        """
        provider = provider or Config.DEFAULT_PROVIDER
        model = model or Config.DEFAULT_MODEL
        if not api_key:
            api_key = Config.GEMINI_API_KEY if provider == "gemini" else Config.OPENAI_API_KEY

        if not api_key:
            return {
                "thought": "API Key is missing.",
                "action": "fail",
                "selector": "",
                "value": "",
                "reason": f"API Key untuk {provider.upper()} belum diatur. Silakan masukkan API Key di sidebar."
            }

        # Convert screenshot bytes to PIL Image
        try:
            image = Image.open(io.BytesIO(screenshot_bytes))
        except Exception as e:
            logger.error(f"Failed to open screenshot image: {e}")
            image = None

        prompt = f"""
Anda adalah AI Agen Penguji Black Box (QA Automation Agent) yang bertugas menguji aplikasi web SauceDemo (https://www.saucedemo.com/).
Tujuan akhir pengujian Anda adalah: "{goal}"

Berikut adalah daftar elemen interaktif (HTML DOM ringkas) pada halaman saat ini:
```html
{dom_structure}
```

Berikut adalah riwayat aksi yang telah Anda lakukan sebelumnya (urut dari terlama ke terbaru):
{json.dumps(history, indent=2) if history else "Belum ada aksi yang dilakukan."}

Tugas Anda:
1. Analisis tangkapan layar (screenshot) halaman saat ini dan struktur DOM di atas.
2. Tentukan aksi berikutnya untuk mencapai tujuan pengujian.
3. Hindari pengulangan aksi yang sama secara terus-menerus (looping). Jika Anda mendeteksi kegagalan berulang, laporkan "fail".
4. Kembalikan tanggapan dalam format JSON yang valid dengan skema berikut:
{{
  "thought": "Penjelasan detail pemikiran Anda mengapa memilih aksi ini berdasarkan tampilan visual dan DOM",
  "action": "click | type | select | navigate | verify | finish | fail",
  "selector": "CSS Selector elemen target (harus ada dari DOM di atas jika tindakannya click/type/select)",
  "value": "Teks yang akan diketik jika action=type, opsi yang akan dipilih jika action=select, ekspektasi teks jika action=verify, kosongkan jika lainnya",
  "reason": "Penjelasan singkat dalam bahasa Indonesia untuk ditampilkan ke pengguna tentang aksi ini"
}}

Aturan Aksi:
- "click": Klik elemen target yang ditunjuk oleh "selector".
- "type": Ketik string di "value" ke dalam input yang ditunjuk oleh "selector".
- "select": Pilih opsi "value" pada elemen `<select>` yang ditunjuk oleh "selector".
- "navigate": Arahkan browser ke URL di "value" (biasanya hanya untuk kembali ke menu utama jika perlu).
- "verify": Verifikasi apakah suatu teks/elemen ada di layar untuk memastikan status sukses.
- "finish": Nyatakan bahwa tujuan pengujian ("{goal}") TELAH BERHASIL DICAPAI.
- "fail": Nyatakan bahwa pengujian GAGAL atau menemui jalan buntu (bug ditemukan, error terjadi, atau API key salah).

PENTING:
- Pilihlah selector CSS yang sangat spesifik dan akurat (misal: `#login-button`, `input#user-name`, `button#add-to-cart-sauce-labs-backpack`).
- Hasilkan hanya JSON yang valid, tanpa tambahan teks markdown di luar format JSON.
"""

        try:
            if provider == "gemini":
                genai_client = cls._get_gemini_client(api_key)
                # Use Gemini multimodal
                gemini_model = genai_client.GenerativeModel(model)
                
                content = []
                if image:
                    content.append(image)
                content.append(prompt)

                # Set generation config to force JSON
                generation_config = genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
                
                response = gemini_model.generate_content(content, generation_config=generation_config)
                response_text = response.text.strip()
                logger.info(f"Gemini raw response: {response_text}")
                return json.loads(response_text)
                
            elif provider == "openai":
                openai_client = cls._get_openai_client(api_key)
                
                # Encode screenshot to base64 if available
                messages = []
                system_message = {
                    "role": "system",
                    "content": "You are a web automation QA assistant that outputs structured JSON responses."
                }
                messages.append(system_message)
                
                user_content = [{"type": "text", "text": prompt}]
                if image:
                    import base64
                    buffered = io.BytesIO()
                    image.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_str}"
                        }
                    })
                
                messages.append({"role": "user", "content": user_content})
                
                response = openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                response_text = response.choices[0].message.content.strip()
                logger.info(f"OpenAI raw response: {response_text}")
                return json.loads(response_text)
                
        except Exception as e:
            logger.error(f"Error calling {provider} API: {e}")
            return {
                "thought": f"Terjadi kesalahan saat memanggil API {provider}: {str(e)}",
                "action": "fail",
                "selector": "",
                "value": "",
                "reason": f"API Error: {str(e)}"
            }

    @classmethod
    def heal_locator(cls, broken_locator: str, dom_structure: str, error_message: str, provider: str = None, model: str = None, api_key: str = None) -> dict:
        """
        Use AI to suggest a replacement CSS selector for a broken locator based on the current DOM.
        Returns a dict: {healed: bool, new_selector: str, confidence: float, explanation: str}
        """
        provider = provider or Config.DEFAULT_PROVIDER
        model = model or Config.DEFAULT_MODEL
        if not api_key:
            api_key = Config.GEMINI_API_KEY if provider == "gemini" else Config.OPENAI_API_KEY

        if not api_key:
            return {"healed": False, "new_selector": "", "confidence": 0.0, "explanation": "API Key not set."}

        prompt = f"""
Anda adalah modul Self-Healing Pengujian Otomatis. 
Sebuah pengujian mengalami kegagalan karena selector CSS lama berikut tidak dapat ditemukan di halaman:
Selector Rusak: `{broken_locator}`

Pesan Kesalahan: `{error_message}`

Berikut adalah HTML DOM ringkas dari halaman saat ini yang berisi elemen-elemen interaktif yang tersedia:
```html
{dom_structure}
```

Tugas Anda:
1. Analisis DOM di atas dan cari tahu elemen mana yang paling mungkin menjadi tujuan selector rusak tersebut (biasanya memiliki kesamaan ID, class, nama, teks, atau perannya).
2. Tentukan selector CSS baru yang valid dari DOM saat ini untuk menggantikan selector yang rusak.
3. Kembalikan tanggapan dalam format JSON yang valid dengan skema berikut:
{{
  "healed": true | false,
  "new_selector": "CSS Selector baru yang valid (misal: 'button#checkout' atau '.btn_action')",
  "confidence": 0.0 sampai 1.0 (tingkat keyakinan Anda),
  "explanation": "Penjelasan singkat dalam bahasa Indonesia mengapa Anda memilih selector baru ini"
}}
"""

        try:
            if provider == "gemini":
                genai_client = cls._get_gemini_client(api_key)
                gemini_model = genai_client.GenerativeModel(model)
                
                generation_config = genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
                response = gemini_model.generate_content(prompt, generation_config=generation_config)
                return json.loads(response.text.strip())
                
            elif provider == "openai":
                openai_client = cls._get_openai_client(api_key)
                response = openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a QA self-healing helper. Output JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"Error in heal_locator: {e}")
            return {"healed": False, "new_selector": "", "confidence": 0.0, "explanation": str(e)}

    @classmethod
    def generate_test_steps(cls, user_prompt: str, provider: str = None, model: str = None, api_key: str = None) -> list:
        """
        Translate a natural language goal into a structured list of test steps.
        Returns a list of dicts: [{"step": 1, "description": "...", "action": "...", "selector": "...", "value": "..."}]
        """
        provider = provider or Config.DEFAULT_PROVIDER
        model = model or Config.DEFAULT_MODEL
        if not api_key:
            api_key = Config.GEMINI_API_KEY if provider == "gemini" else Config.OPENAI_API_KEY

        if not api_key:
            return []

        prompt = f"""
Anda adalah AI Test Scenario Generator. Tugas Anda adalah menerjemahkan instruksi pengujian bahasa alami berikut menjadi serangkaian langkah pengujian Playwright terstruktur untuk situs web SauceDemo (https://www.saucedemo.com/).

Instruksi Pengujian: "{user_prompt}"

Kembalikan daftar langkah terstruktur dalam format JSON dengan skema berikut:
{{
  "steps": [
    {{
      "step": 1,
      "description": "Keterangan singkat langkah ini dalam Bahasa Indonesia (misal: 'Masukkan username standard_user')",
      "action": "type | click | select | verify | navigate",
      "selector": "CSS Selector elemen target (misal: '#user-name', '#login-button', '.inventory_item button')",
      "value": "Teks untuk diketik jika action=type, nilai pilihan jika action=select, URL jika action=navigate, teks ekspektasi jika action=verify, kosongkan jika lainnya"
    }}
  ]
}}

Gunakan pengetahuan Anda tentang SauceDemo untuk memilih selector yang tepat:
- Halaman Login: Username (`#user-name`), Password (`#password`), Tombol Login (`#login-button`)
- Kredensial standard: Username `standard_user`, Password `secret_sauce`
- Halaman Produk: Keranjang (`.shopping_cart_link`), Tombol tambah ke keranjang (`button[name^="add-to-cart"]` atau id seperti `#add-to-cart-sauce-labs-backpack`)
- Halaman Keranjang: Tombol Checkout (`#checkout`), Tombol Continue Shopping (`#continue-shopping`)
- Halaman Checkout Step One: First Name (`#first-name`), Last Name (`#last-name`), Zip Code (`#postal-code`), Tombol Continue (`#continue`)
- Halaman Checkout Step Two: Tombol Finish (`#finish`)
- PENTING: Hasilkan hanya JSON yang valid tanpa tanda petik markdown tambahan di luar JSON.
"""

        try:
            if provider == "gemini":
                genai_client = cls._get_gemini_client(api_key)
                gemini_model = genai_client.GenerativeModel(model)
                generation_config = genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
                response = gemini_model.generate_content(prompt, generation_config=generation_config)
                data = json.loads(response.text.strip())
                return data.get("steps", [])
                
            elif provider == "openai":
                openai_client = cls._get_openai_client(api_key)
                response = openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a test step generator. Output JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                data = json.loads(response.choices[0].message.content.strip())
                return data.get("steps", [])
        except Exception as e:
            logger.error(f"Error generating test steps: {e}")
            return []
