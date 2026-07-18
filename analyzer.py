import os
import json
import base64
import mimetypes
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.5-flash:generateContent"
)

# We ask Gemini to return strict JSON so the app can render color-coded
# cards and a chart, instead of one long block of text.
PROMPT = """
أنت مساعد طبي متخصص في تبسيط التقارير المخبرية للمرضى العاديين.
هذه صورة تقرير مخبري (نتائج تحاليل طبية). اقرأ محتواها بعناية جدًا.

أعد الإجابة بصيغة JSON فقط (بدون أي نص إضافي قبله أو بعده، وبدون علامات
markdown)، مطابقة تمامًا لهذا الشكل:

{
  "title": "عنوان قصير جدًا (3-5 كلمات) يصف نوع التقرير، مثال: صورة الدم الكاملة، فحص السكر والكوليسترول",
  "is_valid_report": true,
  "summary": "جملة أو جملتين تلخّص الحالة العامة بلغة بسيطة جدًا",
  "items": [
    {
      "name": "اسم التحليل بالعربي (مثال: السكر التراكمي)",
      "value": "القيمة كما وردت في التقرير",
      "unit": "وحدة القياس إن وجدت",
      "status": "normal او high او low",
      "explanation": "جملة واحدة بسيطة جدًا تشرح معنى هذه القيمة لشخص عادي"
    }
  ],
  "tips": ["نصيحة عملية 1", "نصيحة عملية 2", "نصيحة عملية 3"],
  "disclaimer": "تنويه بأن هذا التحليل لا يغني عن استشارة الطبيب"
}

قواعد مهمة:
- "status" يجب أن تكون بالضبط واحدة من: normal, high, low (بالإنجليزية وبأحرف صغيرة).
- استخدم لغة عربية بسيطة جدًا في "summary" و"explanation" و"tips"، بدون مصطلحات معقدة.
- إذا كانت الصورة غير واضحة أو لا تحتوي على تقرير طبي، اجعل "is_valid_report": false،
  واشرح ذلك بلطف داخل "summary"، واترك "items" مصفوفة فارغة [].
- لا تكتب أي شيء خارج كائن JSON.
"""


def _extract_json(raw_text):
    """Gemini sometimes wraps JSON in ```json fences even when asked not
    to — strip those before parsing."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()


def analyze_report_image(image_path):
    """Send the report image directly to Gemini via the plain REST API
    and return a parsed structured result (dict) for rendering as
    color-coded cards + a chart. Falls back to a plain-text dict on
    any error so the UI always has something safe to render."""
    if not GEMINI_API_KEY:
        return {
            "error": (
                "⚠️ لم يتم إعداد مفتاح Gemini API بعد.\n\n"
                "أضف GEMINI_API_KEY في ملف .env لتفعيل التحليل الذكي."
            )
        }

    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/jpeg"

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                    {"text": PROMPT},
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "maxOutputTokens": 8192,
            "thinkingConfig": {"thinkingLevel": "low"},
        },
    }

    response = requests.post(
        GEMINI_URL,
        headers={
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    if not response.ok:
        return {
            "error": (
                f"⚠️ حدث خطأ أثناء الاتصال بـ Gemini API: "
                f"{response.status_code} — {response.text[:300]}"
            )
        }

    data = response.json()
    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return {"error": "⚠️ لم يتمكن Gemini من تحليل هذه الصورة. جرّب صورة أوضح لتقرير طبي."}

    try:
        parsed = json.loads(_extract_json(raw_text))
    except json.JSONDecodeError:
        return {
            "error": (
                "⚠️ انقطع الرد قبل ما يكتمل التحليل. جرّبي رفع الصورة مرة ثانية "
                "(أحيانًا يصير هذا مع تقارير فيها عدد كبير جدًا من القيم)."
            )
        }

    # Basic shape safety
    parsed.setdefault("items", [])
    parsed.setdefault("tips", [])
    parsed.setdefault("summary", "")
    parsed.setdefault("title", "")
    parsed.setdefault("disclaimer", "هذا التحليل لا يغني عن استشارة الطبيب.")
    valid_statuses = {"normal", "high", "low"}
    for item in parsed["items"]:
        if item.get("status") not in valid_statuses:
            item["status"] = "normal"

    return parsed
