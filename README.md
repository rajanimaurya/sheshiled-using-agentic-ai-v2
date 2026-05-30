# SheShield – AI-Powered Women Safety & Crime Prediction App

![GitHub Repo stars](https://img.shields.io/github/stars/rajanimaurya/SheShield-Predictive-Women-Safety-LLM-Location-Intelligence?style=social) ![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg) ![LLM](https://img.shields.io/badge/LLM-GPT4%2FLlama-brightgreen.svg) ![Location](https://img.shields.io/badge/Location_Intelligence-Here%20Maps%2FGoogle%20Maps-yellow.svg) ![Predictive](https://img.shields.io/badge/Predictive_Analytics-ML%20Models-red.svg)

<div align="center">

<img src="https://github.com/rajanimaurya/SheShield-Predictive-Women-Safety-LLM-Location-Intelligence/blob/main/images/Safety%20for%20Girls%20Logo%20Design.png?raw=true" width="200">

**AI-Powered Women Safety**  
*Predictive Analytics & Real-time Protection*

</div>

## 📌 Table of Contents

- [Problem Statement](#-problem-statement)
- [Objective](#-objective)
- [Solution](#-solution)
- [Key Features](#-key-features)
- [How It Works](#-how-it-works)
- [System Architecture](#-system-architecture)
- [App Screenshots](#-app-screenshots)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Installation & Setup](#-installation--setup)
- [API Endpoints](#-api-endpoints)
- [Deployment on Railway](#-deployment-on-railway)
- [Future Enhancements](#-future-enhancements)
- [Author](#-author)

---

## ❗ Problem Statement

Women's safety remains a critical concern across India, especially during late-night travel, isolated situations, or emergencies where help cannot be called openly. Existing safety apps are limited — they either require manual intervention, depend on a single alert channel, or fail to respond intelligently in real-time situations.

Key problems identified:

- No way to silently trigger SOS without alerting an attacker
- Emergency alerts often limited to SMS only — no email or voice call backup
- No AI-powered understanding of the user's situation or surroundings
- No real-time nearby safe place suggestions during emergencies
- Voice-based help not possible when typing is unsafe

---

## 🎯 Objective

To build an **AI-powered, multi-channel women safety application** that:

1. Allows women to trigger SOS through multiple methods — button, voice, or secret code
2. Instantly notifies trusted contacts via Email, SMS, and Voice Call simultaneously
3. Uses **Agentic AI (LangGraph)** to provide smart, context-aware safety responses
4. Suggests nearby safe locations (hospitals, police stations) in real time
5. Works silently in unsafe situations without revealing the user's intent

---

## ✅ Solution

**SheShield** is a complete AI-powered safety companion that solves every identified problem:

| Problem | SheShield Solution |
|---------|-------------------|
| Cannot call for help openly | Secret distress code triggers SOS silently |
| Single alert channel fails | Email + SMS + Voice Call sent simultaneously |
| No AI understanding of situation | LangGraph multi-agent AI processes every query |
| No nearby safe place info | Google Places API shows hospitals, police stations live |
| Cannot speak or type safely | Voice trigger "Help Me" works in background offline |

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

### 📰 7. Live Crime News Intelligence
- Fetches **real-time crime news** from online sources using a live News API
- AI automatically extracts **location, time, and type of crime** from news articles
- LangGraph agent analyzes this data and **updates risk assessment** for nearby areas
- User receives proactive alerts like:
  > *"3 incidents reported near MG Road in last 24 hours — avoid this area after 9 PM"*
- Helps women make **informed decisions** before stepping out

---

## ⚡ How It Works

When a user triggers SOS (by button, voice, or secret code), SheShield:

1. **Captures live GPS location** from the device
2. **Dispatches alerts** simultaneously via Email, SMS, and Voice Call to all trusted contacts
3. **AI processes** any chat or voice query using 5 parallel LLM workers judged by DeepSeek-V3
4. **Safe places** are fetched from Google Places API and shown on the map
5. **Voice trigger** listens in background — saying "Help Me" fires SOS instantly without screen touch
6. 6. **Live Crime News Analysis**
   - News API fetches latest crime reports from online sources in real time
   - LLM reads and extracts location, type of crime, and time from each article
   - LangGraph agent maps this to the user's current or searched location
   - Risk level for that area is updated and shown to the user instantly

**Example Alert sent to trusted contacts:**
```
🚨 EMERGENCY ALERT — SheShield

Name  : Rajani Maurya
Time  : 2025-11-25 22:34:10

📍 Location : 26.8467° N, 80.9462° E
🗺️  Maps Link : https://maps.google.com/?q=26.8467,80.9462

Please contact her immediately or reach her location.
This alert was sent automatically by SheShield.
```

---

## 🏗️ System Architecture

### Overall System Flow
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/system_architecture.png" width="800">

### Multi-Agent AI Workflow
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/multi_agent_ai.png" width="800">

### SOS Alert Flow
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/sos_alert_flow.png" width="800">

### Voice Chatbot Flow
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/voice_chatbot_flow.png" width="600">

---
## 📱 App Screenshots

<!-- Registration -->
<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/registration.png" width="300">
</p>

<!-- Login -->
<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/login.png" width="300">
</p>

<!-- Home -->
<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/home.png" width="300">
</p>

<!-- Chatbot -->
<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/chatbot.png" width="300">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/chatbot2.png" width="300">
</p>

<!-- Map / Location -->
<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/location.png" width="300">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/location-detect.png" width="300">
</p>

<!-- Emergency Contact -->
<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/emergency-contact.png" width="300">
</p>

<!-- Profile -->
<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/profile.png" width="300">
</p>

<!-- Mail Output -->
<p align="center">
<img src="https://raw.githubusercontent.com/rajanimaurya/sheshiled-using-agentic-ai-v2/main/image/mail-output.png" width="300">
</p>

---

## 📁 Project Structure

```
sheshiled-using-agentic-ai-v2/
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
├── android/                         # Capacitor Android project
│   └── app/
│
└── image/                           # All diagrams and screenshots
```

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
| News Intelligence | News API + LLM extraction |

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/rajanimaurya/sheshiled-using-agentic-ai-v2.git
cd sheshiled-using-agentic-ai-v2/backend
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

> For phone testing, update the API URL in `frontend/js/app.js`:
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

APK at: `android/app/build/outputs/apk/debug/app-debug.apk`

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
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

Full interactive docs: `https://<your-railway-url>/docs`

---

## ☁️ Deployment on Railway

```bash
# Railway Settings:
# Root Directory  →  backend
# Start Command   →  uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

Procfile (already configured):
```
web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

> **Important:** `DATABASE_URL` must end with `?sslmode=require` for Railway PostgreSQL.

---

## 📈 Future Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| iOS App (Capacitor) | ⭐⭐⭐⭐ | Native iOS build |
| Multi-Language Alerts | ⭐⭐⭐ | Tamil, Telugu alert messages |
| Crime Heatmap | ⭐⭐⭐⭐ | ML-based area risk visualization |
| Wearable Integration | ⭐⭐⭐⭐⭐ | Smartwatch SOS trigger |
| Offline SOS Mode | ⭐⭐⭐⭐ | Works without internet |

---

## 👩‍💻 Author

- **Name:** Rajani Maurya
- **University:** KMCLU, Lucknow (B.Tech CSE)
- **Supervisor:** Dr. Bably Dolly
- **GitHub:** [rajanimaurya](https://github.com/rajanimaurya)
- **Email:** [rajanimauryalu09@gmail.com](mailto:rajanimauryalu09@gmail.com)

---

## ⚠️ Disclaimer

For **educational & research purposes only** (B.Tech Major Project). Real-world deployment must comply with privacy laws and safety regulations. In any emergency, always contact official services: **112**

---

<div align="center">

*Made with ❤️ for women's safety*

**SheShield — Kyunki har ladki surakshit rehne ki haqdar hai**

</div>
