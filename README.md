# Aegis: Real Time Fact Checker (Chrome Extension)
<img width="383" height="467" alt="image" src="https://github.com/user-attachments/assets/98bca86f-3396-4946-a3b5-de5f16787e4b" />

Aegis is a real-time AI-detection and fact-checking Chrome Extension designed for the "casual scroller." By integrating directly into the browser, Aegis reduces the friction of digital literacy, allowing users to verify text, images, and full articles with a simple right-click.

## The Vision
In an era of generative AI and lies, the barrier to creating misinformation has collapsed. Aegis addresses this by providing a multi-model dashboard that lives right in your browser's Side Panel, verifying content in seconds without interrupting your workflow.

## Key Features
* **Right-Click Context Menus:** Instantly scan highlighted text, images, or full-page articles directly from the browser.
* **Native Chrome Side Panel:** Results slide in seamlessly via Chrome's native Side Panel API.
* **Dual Scanning Modes:** Choose between a fast "Quick Scan" for immediate verdicts or a comprehensive "Deep Dive" for thorough research.
* **Local History:** Keeps track of your recent scans locally in your browser so you never lose a source.

## Tech Stack
* **Frontend / Client:** React (Vite) built as a Manifest V3 Chrome Extension.
* **Backend / Orchestration:** FastAPI (Python) using `httpx` and `asyncio` for high-speed, concurrent API processing.
* **Analysis Engines:** * **Google Gemini API:** Powers the complex fact-checking reasoning, claim extraction, and bias reporting.
* **Winston AI:** For high-accuracy AI text detection.

## Project Structure
```text
/rt-fact-checker
├── .env                      # Private API keys (not tracked in Git)
├── backend/                  # FastAPI Server
│   ├── main.py               # API logic & orchestration
│   └── requirements.txt
└── frontend/                 # React Chrome Extension
    ├── public/
    │   ├── manifest.json     # Extension configuration
    │   ├── background.js     # Service worker (Context menus & panel triggers)
    │   ├── content.js
    │   └── icons/             # Extension logo
    │       ├── icon16.png        
    │       ├── icon48.png
    │       └── icon128.png
    ├── src/
    │   ├── App.jsx           # Main UI logic (Side Panel)
    │   ├── index.css
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
WINSTONAI_API_KEY=your_winston_token_here
GEMINI_API_KEY=your_gemini_api_key_here
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

Install packages and build the extension:

```Bash
npm install
npm run build
```

3. Load into Chrome
Open Google Chrome and navigate to chrome://extensions/.

Toggle Developer mode ON in the top right corner.

Click Load unpacked in the top left.

Select the aegis/frontend/dist folder.

Pin the Aegis shield icon to your toolbar!



## Architecture: "Stateless by Design"
Aegis prioritizes user privacy. Aside from local browser history tracking (stored entirely on the user's machine), the backend utilizes a stateless design.

Trigger: User right-clicks web content or pastes it into the React Side Panel.

Orchestration: The Chrome Extension sends the data to FastAPI, which triggers concurrent calls to Gemini and the AI Detector.

Synthesis: The backend normalizes the data into a unified "Trust Report" JSON object.

Response: The extension renders the AI score, claims, and bias reports dynamically.
