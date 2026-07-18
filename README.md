# 🩺 SmartLab

**تطبيق ويب يحوّل تقريرك المخبري المعقّد إلى شرح بسيط بلغة تفهمينها — بالذكاء الاصطناعي.**

![Python](https://img.shields.io/badge/Python-3.10+-1F5C4E?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-3.0-1F5C4E?style=flat-square)
![Gemini API](https://img.shields.io/badge/Gemini%20API-3.5%20Flash-E8B84B?style=flat-square)
![License](https://img.shields.io/badge/License-Educational-lightgrey?style=flat-square)

مشروع تخرّج — قسم علوم الحاسب.

## ✨ المزايا

- 📸 رفع صورة تقرير مخبري — يقرأها الذكاء الاصطناعي (Gemini) مباشرة بدون أي برنامج OCR منفصل
- 🟢🔴🟠 عرض النتائج ككروت ملوّنة (طبيعي / مرتفع / منخفض) مع رسم بياني تفاعلي يلخّص الحالة
- 👤 دخول كزائر للتجربة السريعة، أو حساب دائم لحفظ التقارير ومتابعة السجل الطبي عبر الوقت
- 💾 قاعدة بيانات SQLite تحفظ كل تقرير مرتبط بصاحبه
- 📧 إرسال نتيجة التحليل عبر البريد الإلكتروني
- 🌐 جاهز للنشر على الإنترنت عبر Google Cloud Run

---

## 📖 دليل التشغيل الكامل

## 1. المتطلبات قبل البدء

1. **Python 3.10 أو أحدث** — تحقق بكتابة في الطرفية (Terminal / CMD):
   ```
   python3 --version
   ```
   إن لم يكن مثبتًا، حمّله من https://www.python.org/downloads/

2. **مفتاح Gemini API** (مجاني للتجربة) من:
   https://aistudio.google.com/app/apikey
   انسخ المفتاح، ستحتاجه في الخطوة القادمة.

---

## 2. تشغيل المشروع محليًا على اللابتوب

### أ. فك ضغط المشروع وفتحه
فك ضغط الملف المضغوط في أي مجلد، ثم افتح الطرفية داخل مجلد المشروع `smartlab-webapp`.

### ب. إنشاء بيئة افتراضية (اختياري لكن مستحسن)
```bash
python3 -m venv venv

# تفعيلها:
# على Windows:
venv\Scripts\activate
# على Mac / Linux:
source venv/bin/activate
```

### ج. تثبيت المكتبات المطلوبة
```bash
pip install -r requirements.txt
```

### د. إعداد ملف المتغيرات البيئية
انسخ الملف `.env.example` وأعد تسميته إلى `.env`، ثم افتحه وعبّئ:
```
SECRET_KEY=اكتب-نصًا-عشوائيًا-طويلًا-هنا
GEMINI_API_KEY=المفتاح-الذي-حصلت-عليه-من-Google-AI-Studio
```
(حقول SMTP اختيارية، فقط إن أردت تفعيل إرسال البريد الإلكتروني — راجع القسم 5 بالأسفل)

### هـ. تشغيل التطبيق
```bash
python3 app.py
```
سترى رسالة تفيد أن الخادم يعمل على:
```
http://127.0.0.1:5000
```
افتح هذا الرابط في المتصفح — تطبيقك يعمل الآن محليًا على جهازك 🎉

### و. تجربة التطبيق
- اضغط **"المتابعة كزائر"** لتجربة رفع تقرير وتحليله فورًا بدون حساب (لن يُحفظ).
- أو اضغط **"إنشاء حساب"** لتسجيل بريد وكلمة مرور، وبعدها كل تقرير ترفعه يُحفظ تلقائيًا في **قاعدة بيانات SQLite** (ملف `smartlab.db` يُنشأ تلقائيًا بجانب المشروع) ويظهر في صفحة **"سجلّي"**.

---

## 3. رفع المشروع على Google (Google Cloud Run)

هذه الخطوات تجعل تطبيقك متاحًا على رابط عام على الإنترنت، مستضافًا على خوادم Google.

### أ. تجهيز حساب Google Cloud
1. اذهب إلى https://console.cloud.google.com وسجّل الدخول بحساب Google.
2. أنشئ مشروعًا جديدًا (New Project) وسمّه مثلاً `smartlab-app`.
3. فعّل الفوترة (Billing) — Google تمنح رصيدًا مجانيًا للحسابات الجديدة، و Cloud Run له طبقة مجانية سخية شهريًا.

### ب. تثبيت أداة gcloud CLI
حمّلها من: https://cloud.google.com/sdk/docs/install
بعد التثبيت، في الطرفية:
```bash
gcloud init
```
واتبع الخطوات لتسجيل الدخول وربط المشروع الذي أنشأته.

### ج. تفعيل الخدمات المطلوبة
```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

### د. النشر (Deploy)
من داخل مجلد المشروع `smartlab-webapp` (نفس المجلد الذي فيه `Dockerfile`):
```bash
gcloud run deploy smartlab-app \
  --source . \
  --region me-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY="نص-عشوائي-طويل",GEMINI_API_KEY="مفتاحك"
```
بعد انتهاء الأمر (قد يأخذ دقيقتين إلى خمس)، ستحصل على رابط مثل:
```
https://smartlab-app-xxxxxxx.a.run.app
```
هذا هو رابط موقعك العام، شاركه مع أي شخص.

### هـ. تحديث المشروع لاحقًا
```bash
gcloud run deploy smartlab-app --source .
```

> ⚠️ **ملاحظة مهمة عن قاعدة البيانات على Cloud Run**: خدمة Cloud Run لا تحتفظ بالملفات (مثل `smartlab.db`) بشكل دائم بين إعادة تشغيل الحاويات. للاستخدام التجريبي والعرض هذا لا يمثل مشكلة، لكن لتخزين دائم وحقيقي للمستخدمين لاحقًا، ستحتاج للانتقال إلى قاعدة بيانات سحابية مثل **Cloud SQL** أو **Firestore**.

---

## 4. هيكل المشروع

```
smartlab-webapp/
├── app.py              # نقطة التشغيل الرئيسية + كل المسارات (routes)
├── database.py         # التعامل مع قاعدة بيانات SQLite
├── analyzer.py          # إرسال صورة التقرير مباشرة إلى Gemini وتحليلها
├── requirements.txt     # قائمة المكتبات المطلوبة
├── Dockerfile           # لتشغيل المشروع على Google Cloud Run
├── .env.example         # نموذج للمتغيرات السرية (انسخه إلى .env)
├── templates/           # صفحات الموقع (HTML)
├── static/css/          # التنسيق (CSS)
└── uploads/             # الصور المرفوعة من المستخدمين
```

---

## 5. تفعيل إرسال البريد الإلكتروني (اختياري)

1. فعّل "التحقق بخطوتين" على حساب Gmail الذي ستستخدمه للإرسال.
2. أنشئ "App Password" من: https://myaccount.google.com/apppasswords
3. ضع في ملف `.env`:
   ```
   SMTP_USER=youremail@gmail.com
   SMTP_PASS=كلمة-المرور-المؤقتة-16-حرفًا
   ```
4. أعد تشغيل التطبيق.

---

## 6. تنويه

هذا تطبيق تخرّج تعليمي. التحليل الذي يقدّمه الذكاء الاصطناعي **لا يغني عن استشارة طبيب مختص**، وهذا موضح للمستخدم في كل نتيجة تحليل.
