<div align="center">

# 🚀 TECH CLEVORA

### **Next-Gen AI-Powered Career Readiness, Resume Analytics & Interview Intelligence Platform**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.2-black?style=for-the-badge&logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-3.1.1-red?style=for-the-badge&logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6%2B-yellow?style=for-the-badge&logo=javascript&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

[Explore Features](#-key-features) • [Getting Started](#-getting-started) • [API Architecture](#-api-architecture) • [Admin Panel](#-admin-panel)

---

</div>

## 🌟 Overview

**TECH CLEVORA** is an end-to-end, AI-driven career development platform designed to empower job seekers, developers, and recruiters. By combining modern resume parsing, real-time Applicant Tracking System (ATS) optimization, custom AI mock interview simulations, and actionable skill gap analytics, Tech Clevora bridges the gap between candidates and high-growth technology roles.

---

## ✨ Key Features

### 📄 1. Smart Resume Analyzer & ATS Optimizer
* **Multi-Format Extraction**: Instant parsing for PDF and DOCX resume formats.
* **ATS Compatibility Scoring**: Calculates a dynamic compatibility percentage based on keyword density, formatting checks, and structural completeness.
* **Skill & Missing Keyword Detection**: Automatically identifies core technical competencies and highlights critical missing skills required for target roles.

### 🎙️ 2. AI Mock Interview Simulator & Console
* **Customizable Sessions**: Configure interviews by job role, experience level (Junior, Mid, Senior, Lead), difficulty, and domain (Behavioral, Technical, System Design, HR).
* **Voice & Text Interaction**: Integrated Web Speech API for real-time speech-to-text answer dictation.
* **Instant AI Feedback & Scoring**: Comprehensive performance breakdown with detailed feedback, overall score, and printable PDF report downloads.

### 📦 3. Recruiter Bulk Resume Scanner
* **Batch Processing**: Upload dozens of candidate resumes simultaneously.
* **Automated Candidate Ranking**: Rank candidates by ATS score and export summarized candidate candidate cards.

### 🗺️ 4. Personal Career Roadmap & Skill Gap Analyzer
* **Interactive Skill Trees**: Visualize progress across core technical concepts.
* **Personalized Recommendations**: Dynamic action steps to improve ATS readiness and target weak areas.

### 🏢 5. Company-Specific Prep Hub
* Dedicated interview preparation guides and question databases tailored for major tech firms (Google, Meta, Amazon, Microsoft, etc.).

### 📊 6. Interactive Analytics & Performance Hub
* Real-time charts, activity heatmaps, trendlines for ATS score growth over time, and AI Career Coach insights.

### 🛡️ 7. Enterprise Admin Control Panel
* System analytics monitoring user registrations, uploaded resumes, completed mock sessions, feedback collection, and live application logs.

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Backend Framework** | Python 3.10+, Flask, Flask-CORS |
| **Database & ORM** | SQLite3, Flask-SQLAlchemy |
| **Authentication & Security** | JWT (PyJWT), Werkzeug Security (`scrypt` password hashing) |
| **AI & NLP Engine** | Google Gemini AI (`google.genai`), Custom Heuristic Rule Engines |
| **Document Processing** | PyPDF2, python-docx |
| **Frontend UI/UX** | HTML5, Modern Vanilla CSS (Glassmorphism design system), JavaScript (ES6 SPA Router) |
| **UI Components & Icons** | FontAwesome 6 Pro, Chart.js, DiceBear Avatar API |

---

## 🚀 Getting Started

Follow these instructions to get a local copy of Tech Clevora up and running.

### Prerequisites
* **Python 3.10** or higher
* **pip** package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jenil-eng/TechClevora.git
   cd TechClevora
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables (Optional):**
   Create a `.env` file in the project root if you want to use live Gemini API calls:
   ```env
   GEMINI_API_KEY=your_google_gemini_api_key
   JWT_SECRET_KEY=your_custom_jwt_secret
   PORT=5001
   ```
   *(Note: If no API key is provided, the platform automatically utilizes a robust fallback mock AI engine).*

5. **Run the Application:**
   ```bash
   python app.py
   ```
   Open your browser and navigate to: **`http://127.0.0.1:5001`**

---

## 🔑 Default Credentials

For quick testing and evaluation, you can log in using the pre-configured admin account:

* **Admin Email**: `admin@meetai.com` or `vekariyameet674@gmail.com`
* **Admin Password**: `admin123`

---

## 📁 Repository Structure

```
TechClevora/
├── app.py                  # Main Flask application initialization & SPA routing
├── models.py               # SQLAlchemy database models & schema migration logic
├── requirements.txt        # Project dependencies
├── routes/
│   ├── admin.py            # Admin Panel REST API routes
│   ├── api.py              # Resume, Interview, Roadmap & Analytics REST API endpoints
│   └── auth.py             # User Authentication & JWT management routes
├── services/
│   ├── ai_service.py       # Gemini AI integration & fallback service
│   ├── parser_service.py   # Document parsing helpers
│   ├── report_service.py   # Performance report generator
│   ├── resume_parser.py    # PDF/DOCX text & skill extraction service
│   └── resume_scorer.py    # ATS scoring heuristics engine
├── static/
│   ├── css/
│   │   └── style.css       # Complete CSS design system & dynamic UI styles
│   └── js/
│       ├── api.js          # REST API wrapper & token storage controller
│       └── app.js          # Single-Page Application (SPA) client router & UI rendering
└── templates/
    └── index.html          # Main SPA HTML structure
```

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.

<div align="center">
  <sub>Built with ❤️ for tech career excellence. Made by <b>Jenil Eng</b></sub>
</div>
