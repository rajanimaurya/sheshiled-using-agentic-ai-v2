![GitHub Repo stars](https://img.shields.io/github/stars/rajanimaurya/sheshild-major-project?style=social)
![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)
![LangGraph](https://img.shields.io/badge/AI-LangGraph%20Multi--Agent-blueviolet.svg)
![Twilio](https://img.shields.io/badge/Alerts-Twilio%20SMS%2FCall-red.svg)
![Android](https://img.shields.io/badge/Mobile-Capacitor%20Android-3DDC84.svg)
![Railway](https://img.shields.io/badge/Deployed-Railway-black.svg)

<div align="center">

<img src="https://github.com/rajanimaurya/SheShield-Predictive-Women-Safety-LLM-Location-Intelligence/blob/main/images/Safety%20for%20Girls%20Logo%20Design.png?raw=true" width="200">

**AI-Powered Women Safety Application**
*Real-Time SOS · Voice Chatbot · Safe Route Map · Secret Distress Code*

</div>

---

## 🚀 Project Overview

**SheShield** is an **AI-powered women safety platform** that combines **LangGraph multi-agent intelligence, real-time GPS tracking, and multi-channel emergency alerts** to protect women in unsafe situations.

It is not just an SOS button — it is a **complete intelligent safety companion**. Whether you speak, type, or press a button, SheShield understands and acts instantly. It alerts your trusted contacts with your live location, suggests nearby safe places, and even lets you silently trigger SOS using a **secret distress code** — without the attacker ever knowing.

Built as a **B.Tech Major Project** at KMCLU, Lucknow — deployed live on Railway with an Android APK.

---

## 🔑 Key Features

### 🆘 1. SOS Emergency Alert System
- One button press **or** a voice command instantly triggers the alert
- App fetches your **live GPS coordinates** automatically
- Sends alerts through **three channels simultaneously:**
  - 📧 **Email** — via Gmail SMTP with Google Maps link
  - 📱 **SMS** — via Twilio
  - 📞 **Voice Call** — via Twilio
- Runs completely in the **background** — UI never freezes

### 🤫 2. Secret Distress Code
- Set a personal secret phrase in Settings (e.g. *"I'm feeling sleepy"*)
- In an unsafe situation, **type that phrase in the chat**
- The screen shows a completely **normal-looking reply**
- Behind the scenes, **SOS triggers silently** — the attacker sees nothing

### 🎙️ 3. AI Voice Chatbot
- **Speak** in Hindi, English, or Hinglish
- **OpenAI Whisper** converts your voice to text
- **DeepSeek-V3 via LangGraph** generates a smart, context-aware response
- **gTTS** speaks the reply back to you
- Supports **barge-in** — interrupt the bot mid-speech anytime
- Persistent **mic toggle** — keep it on or off as you prefer

### 🗺️ 4. Safe Route Map
- Detects your **current GPS location** automatically
- Finds nearby safe places using **Google Places API:**
  - 🏥 Hospitals
  - 👮 Police Stations
  - 🏬 Malls & Crowded Areas
  - 🍽️ Restaurants
- Shows them as **interactive map markers** with name and distance

### 🎤 5. Voice Trigger — "Help Me"
- App **listens in the background** using Vosk (fully offline — no internet needed)
- Just say **"Help Me"** clearly
- SOS triggers **automatically** — without touching the screen
- You can also set a **custom trigger word** in settings

### 🤖 6. LangGraph Multi-Agent AI
- **5 LLM workers run in parallel:** LLaMA, Mistral, Qwen, Gemma, GPT-OSS
- All run simultaneously using **asyncio** — fast response
- **DeepSeek-V3 acts as a Judge** — picks the most accurate and safe reply
- Built using **LangGraph StateGraph** pattern for structured agent flow

---

## 🏗️ System Architecture

### How It All Works Together

```
  ┌─────────────────────────────────────────────────────┐
  │               User (Android App / Browser)           │
  │   [ SOS Button ]  [ Chat ]  [ Map ]  [ Mic ]        │
  └───────────────────────┬─────────────────────────────┘
                          │  HTTP / REST API
                          ▼
  ┌─────────────────────────────────────────────────────┐
  │              FastAPI Backend (Railway)               │
  │                                                     │
  │  sos_endpoint.py      →   Receives SOS trigger      │
  │  alert_dispatcher.py  →   Coordinates all alerts    │
  │  email_service.py     →   Sends Gmail SMTP email    │
  │  voice_chat.py        →   Whisper + LLM + gTTS      │
  │  voice_trigger.py     →   "Help Me" background mic  │
  │  safe_route.py        →   Google Places API         │
  │  langgraph_agent/     →   Multi-agent AI system     │
  └──────────┬──────────────────┬────────────────┬──────┘
             │                  │                │
             ▼                  ▼                ▼
      ┌────────────┐   ┌──────────────┐  ┌────────────────┐
      │ PostgreSQL │   │    Twilio    │  │  Together.ai   │
      │ (Database) │   │ SMS + Call   │  │  LLM Workers   │
      └────────────┘   └──────────────┘  └────────────────┘
```

---

### Multi-Agent AI Workflow

```
  Your Message
       │
       ▼
  ┌────────────────────────────────────────────┐
  │             Parallel LLM Workers           │
  │                                            │
  │   LLaMA   Mistral   Qwen   Gemma   GPT    │
  │     │        │        │      │       │     │
  │     └────────┴────────┴──────┴───────┘     │
  │          (All run at the same time)         │
  └────────────────────┬───────────────────────┘
                       │  5 responses generated
                       ▼
             ┌──────────────────┐
             │  DeepSeek Judge  │
             │                  │
             │  Picks the best  │
             │  response        │
             └────────┬─────────┘
                      │
                      ▼
               Final Answer ✅
```

---

### SOS Alert Flow

```
  User presses SOS / says "Help Me" / types secret code
                        │
                        ▼
              GPS Location Fetched
                        │
                        ▼
            alert_dispatcher.py
           /           |           \
          ▼            ▼            ▼
      Gmail         Twilio        Twilio
      Email          SMS        Voice Call
          \           |           /
           ▼          ▼          ▼
        Trusted Contacts Notified
        with Location + Maps Link ✅
```

---

### Voice Chatbot Flow

```
  You Speak
      │
      ▼
  Whisper STT        →   Converts audio to text
      │
      ▼
  LangGraph Agent    →   5 workers + DeepSeek judge
      │
      ▼
  gTTS               →   Converts reply to speech
      │
      ▼
  You Hear the Reply ✅
```

---

## 📁 Project Structure

```
sheshield-major-project/
│
├── backend/
│   ├── src/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── sos_endpoint.py          # SOS trigger route
│   │   ├── alert_dispatcher.py      # Email + SMS + Call coordinator
│   │   ├── email_service.py         # Gmail SMTP sender
│   │   ├── voice_chat.py            # Whisper + LLM + gTTS pipeline
│   │   ├── voice_trigger.py         # Background "Help Me" listener (Vosk)
│   │   ├── safe_route.py            # Google Places nearby search
│   │   ├── auth.py                  # JWT authentication
│   │   ├── models.py                # PostgreSQL models (SQLAlchemy)
│   │   └── langgraph_agent/
│   │       ├── graph.py             # LangGraph StateGraph definition
│   │       ├── workers.py           # Parallel LLM worker nodes
│   │       └── judge.py             # DeepSeek-V3 judge node
│   ├── requirements.txt
│   └── Procfile                     # Railway deployment command
│
├── frontend/
│   ├── index.html                   # Main UI
│   └── js/
│       ├── app.js                   # Main controller
│       ├── voice-commands.js        # Mic input, STT, barge-in
│       ├── sos-handler.js           # SOS button + secret code
│       └── safe-route-map.js        # Map display + nearby places
│
└── android/                         # Capacitor Android project
    └── app/
```

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/rajanimaurya/sheshild-major-project.git
cd sheshild-major-project/backend
```

### 2. Install Dependencies

```bash
conda create -n sheshield python=3.10
conda activate sheshield
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file inside `backend/`:

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require

# Auth
SECRET_KEY=your-secret-key
ALGORITHM=HS256

# Gmail (Email Alerts)
GMAIL_USER=yourapp@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Twilio (SMS + Voice Call)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# Together.ai (LLM Workers)
TOGETHER_API_KEY=your-together-api-key

# Google Maps & Places
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# OpenAI (Whisper STT)
OPENAI_API_KEY=your-openai-key
```

> **How to get Gmail App Password:**
> Google Account → Security → 2-Step Verification ON → App Passwords → Select "Mail" → Generate

### 4. Run the Backend

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend is live at: `http://localhost:8000`
Interactive API docs: `http://localhost:8000/docs`

### 5. Run the Frontend

Open `frontend/index.html` in your browser.

> For testing on your phone, update the API URL in `frontend/js/app.js`:
> ```js
> const API_BASE = "http://<your-laptop-LAN-IP>:8000";
> ```

### 6. Build Android APK

```bash
cd frontend/
npx cap sync android

cd ../android/
echo "sdk.dir=/home/<your-username>/Android/Sdk" > local.properties
./gradlew assembleDebug
```

APK will be at:
```
android/app/build/outputs/apk/debug/app-debug.apk
```

Install on phone:
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

---

## 🔄 Detailed Workflow

1. **User Registration & Setup**
   - Register account, add trusted contacts, grant GPS and microphone permissions

2. **Real-Time Monitoring**
   - App listens for voice trigger ("Help Me") in the background
   - Chat monitors every message for the secret distress code

3. **AI & LLM Processing**
   - LangGraph sends the user's message to 5 parallel LLM workers
   - DeepSeek-V3 judge evaluates all responses and picks the best one

4. **Alert Dispatching**
   - GPS coordinates are fetched
   - Email, SMS, and voice call sent simultaneously to trusted contacts

5. **Safe Route Suggestion**
   - Google Places API finds nearby safe locations
   - Displayed on interactive map for immediate navigation

**Example Alert Message:**
```
🚨 EMERGENCY ALERT — SheShield

Name: Rajani Maurya
Time: 2025-11-25 22:34:10

📍 Location: 26.8467° N, 80.9462° E
🗺️  Google Maps: https://maps.google.com/?q=26.8467,80.9462

Please contact her immediately or reach her location.
This alert was sent automatically by SheShield.
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sos/trigger` | Trigger SOS emergency alert |
| `POST` | `/api/chat/voice` | Send voice message (audio file) |
| `POST` | `/api/chat/text` | Send text message |
| `GET`  | `/api/safe-route/nearby` | Get nearby safe places |
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Login and receive JWT token |
| `POST` | `/api/contacts/add` | Add emergency contact |
| `GET`  | `/api/contacts/list` | List all emergency contacts |
| `POST` | `/api/settings/secret-code` | Set secret distress code |

Full interactive docs available at: `https://<your-railway-url>/docs`

---

## ☁️ Deployment on Railway

```bash
# Railway Settings:
# Root Directory  →  backend
# Start Command   →  uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

The `Procfile` is already configured:
```
web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

Add all environment variables in the Railway dashboard.

> **Important:** Make sure `DATABASE_URL` ends with `?sslmode=require` for Railway PostgreSQL.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.10+) |
| AI Agents | LangGraph, DeepSeek-V3, LLaMA, Mistral, Qwen, Gemma |
| LLM Provider | Together.ai |
| Speech-to-Text | OpenAI Whisper |
| Text-to-Speech | gTTS |
| Voice Trigger | Vosk (Offline) |
| SMS & Voice Call | Twilio |
| Email Alerts | Gmail SMTP |
| Database | PostgreSQL (SQLAlchemy) |
| Frontend | Vanilla JS (4 modules), HTML5, CSS3 |
| Mobile App | Capacitor (Android APK) |
| Maps | Google Places API + Google Maps JS API |
| Deployment | Railway |
| Authentication | JWT |

---

## 📈 Future Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| iOS App (Capacitor) | ⭐⭐⭐⭐ | Native iOS build |
| Multi-Language Alerts | ⭐⭐⭐ | Hindi, Tamil, Telugu alert messages |
| Crime Heatmap | ⭐⭐⭐⭐ | ML-based area risk visualization |
| Law Enforcement API | ⭐⭐⭐ | Real-time alerts to authorities |
| Wearable Integration | ⭐⭐⭐⭐⭐ | Smartwatch SOS trigger |
| Offline SOS Mode | ⭐⭐⭐⭐ | Works without internet |

---

## 🛠️ Contribution

- Fork 🍴 → create a feature branch `git checkout -b feature-name`
- Keep backend and frontend code modular and clean
- Commit with clear messages: `git commit -m "feat: description"`
- Submit a Pull Request 🚀

---

## 📧 Contact

- **Author:** Rajani Maurya
- **University:** KMCLU, Lucknow (B.Tech CSE)
- **Supervisor:** Dr. Bably Dolly
- **GitHub:** [rajanimaurya](https://github.com/rajanimaurya)
- **Email:** [rajanimauryalu09@gmail.com](mailto:rajanimauryalu09@gmail.com)

---

## ⚠️ Disclaimer

For **educational & research purposes only** (B.Tech Major Project). Real-world deployment must comply with privacy laws and safety regulations. In any emergency, always contact official services: **112**

---
