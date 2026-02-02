# Aegis: Disinformation Dashboard

Aegis is a real-time fact-checking and AI-detection tool designed to empower the "casual scroller." By consolidating multiple verification signals—AI likelihood and known fact-checks—into a single "Trust Report," Aegis reduces the friction of digital literacy.

## The Vision
In an era of generative AI, the barrier to creating misinformation has collapsed. Aegis addresses this by providing a stateless, multi-model dashboard that verifies content in seconds.

## Tech Stack
* **Frontend:** React (Vite)
* **Backend:** FastAPI (Python)
* **Async Orchestration:** `httpx` and `asyncio` for parallel API processing.
* **Analysis Engines:** 
    * **Winston AI:** For high-accuracy AI text detection.
    * **Google Fact Check Tools:** For identifying existing debunks from authoritative sources.

## Project Structure
```text
/aegis
├── backend/            # FastAPI Server
│   ├── main.py         # API logic & orchestration
│   ├── .env            # Private API keys (not tracked in Git)
│   └── requirements.txt
└── frontend/           # React Dashboard
    ├── src/
    │   ├── App.jsx     # Main UI logic
    │   └── main.jsx
    └── package.json
```
## Setup & Installation
1. Backend Setup
Navigate to the backend directory:

```Bash
cd backend
```

Create and activate a virtual environment:

```Bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```Bash
pip install -r requirements.txt
```

Create a .env file and add your credentials:

```Code snippet
WINSTONAI_API_KEY=your_token_here
FACT_CHECK_API_KEY=your_google_cloud_key_here
```

Start the server:

```Bash
python main.py
```

2. Frontend Setup
Navigate to the frontend directory:

```Bash
cd frontend
```

Install packages:

```Bash
npm install
```

Launch the development server:

```Bash
npm run dev
```

Architecture: "Stateless by Design"
Aegis does not use a database. This design choice minimizes complexity and maximizes privacy.

Request: User pastes text into the React frontend.

Orchestration: FastAPI receives the text and triggers concurrent calls to Winston AI and Google Fact Check.

Synthesis: The backend normalizes the data into a unified "Trust Report" JSON object.

Response: The frontend renders the results dynamically.


License
This project is part of a Senior Capstone Project. See the proposal for full academic context.