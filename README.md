# Coins - Kenya Grocery Price Comparison

Compare grocery prices across **Naivas**, **Carrefour**, and **Quickmart** in one place. Search for products, compare prices side-by-side, and build optimized shopping lists.

**Tech stack:** Python (FastAPI) backend, Next.js (React + TypeScript) frontend, MySQL database, Playwright web scrapers.

---

## Prerequisites

You need to install the following tools before setting up the project. If you already have any of these, skip that step.

### 1. Install Git

Git is used to download and manage the project code.

1. Download Git from https://git-scm.com/downloads
2. Run the installer — use all the default options
3. Verify it worked by opening a terminal and running:
   ```
   git --version
   ```
   You should see something like `git version 2.x.x`

### 2. Install Python (3.10 or higher)

Python runs the backend API and web scrapers.

1. Download Python from https://www.python.org/downloads/
2. **Important:** During installation, check the box that says **"Add Python to PATH"**
3. Use all other default options and finish the install
4. Verify it worked:
   ```
   python --version
   ```
   You should see `Python 3.10.x` or higher

### 3. Install Node.js (18 or higher)

Node.js runs the frontend application.

1. Download the **LTS** version from https://nodejs.org/
2. Run the installer — use all the default options
3. Verify it worked:
   ```
   node --version
   npm --version
   ```
   You should see version numbers for both

### 4. Install Laragon (includes MySQL)

Laragon is a local development environment that bundles MySQL (MariaDB), which is the database for this project.

1. Download Laragon Full from https://laragon.org/download/
2. Run the installer — use all the default options
3. Open Laragon and click **"Start All"** to start MySQL
4. Verify MySQL is running — the Laragon panel should show a green indicator next to MySQL/MariaDB

> **Already have MySQL installed another way?** That works too — just make sure it's running on port `3306`.

---

## Project Setup

### Step 1: Clone the repository

Open a terminal and run:

```bash
git clone <your-repo-url> coins
cd coins
```

> Replace `<your-repo-url>` with the actual GitHub/GitLab URL for this project.

### Step 2: Create the database

1. Make sure MySQL is running (start Laragon if using it)
2. Open a terminal and run:
   ```bash
   mysql -u root -e "CREATE DATABASE IF NOT EXISTS coins_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   ```
   > If your MySQL has a password, add `-p` and enter it when prompted:
   > ```bash
   > mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS coins_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   > ```

### Step 3: Set up the backend

```bash
# Navigate to the backend folder
cd backend

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (needed for web scraping)
playwright install chromium
```

Now create your environment file:

```bash
# Copy the example env file
cp .env.example .env
```

Open `backend/.env` in a text editor and fill in your values:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=coins_db
```

> **Note:** Laragon's default MySQL user is `root` with no password (leave `DB_PASSWORD` empty). If you set a password, enter it here.

### Step 4: Set up the frontend

Open a **new terminal** (keep the backend terminal open):

```bash
# Navigate to the frontend folder
cd frontend

# Install Node.js dependencies
npm install
```

Create the frontend environment file:

```bash
cp .env.local.example .env.local
```

If the example file doesn't exist, create `frontend/.env.local` manually with this content:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Running the Application

You need **two terminals** running at the same time — one for the backend and one for the frontend.

### Terminal 1: Start the backend

```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

### Terminal 2: Start the frontend

```bash
cd frontend
npm run dev
```

You should see output like:
```
▲ Next.js 16.x.x
- Local: http://localhost:3000
```

### Open the app

Go to **http://localhost:3000** in your browser. The app is ready to use!

The backend API is available at **http://localhost:8000** (API docs at http://localhost:8000/docs).

---

## Seeding the Database (Optional)

To pre-load product data from all stores, run the populate script:

```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Full scrape (all stores, takes a while — uses Playwright)
python populate_db.py

# Fast mode (Carrefour only, no Playwright needed)
python populate_db.py --fast

# Specific store only
python populate_db.py --store naivas
```

> **Tip:** Start with `--fast` to quickly get some data, then run the full scrape later.

---

## Project Structure

```
coins/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── main.py          # API entry point
│   │   ├── database.py      # Database connection
│   │   ├── models.py        # Database tables
│   │   ├── auth.py          # Authentication (JWT)
│   │   ├── matcher.py       # Product matching across stores
│   │   ├── scrape_service.py
│   │   ├── routers/         # API route handlers
│   │   └── scrapers/        # Store-specific web scrapers
│   ├── requirements.txt     # Python dependencies
│   ├── populate_db.py       # Database seeding script
│   └── .env.example         # Environment variables template
├── frontend/                # Next.js React frontend
│   ├── src/
│   │   ├── app/             # Pages (home, compare, login, etc.)
│   │   ├── components/      # Reusable UI components
│   │   ├── context/         # React context (auth state)
│   │   └── lib/             # API client & utilities
│   └── package.json         # Node.js dependencies
├── start-backend.bat        # Quick-start script (Windows)
├── start-frontend.bat       # Quick-start script (Windows)
└── README.md                # This file
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create a new account |
| `POST` | `/auth/login` | Log in and get a token |
| `GET` | `/auth/me` | Get current user info |
| `GET` | `/products/search?q=milk` | Search products |
| `GET` | `/products/compare?q=milk` | Compare prices across stores |
| `GET` | `/products/{id}/history` | Price history for a product |
| `GET` | `/stores/` | List all stores |
| `GET` | `/stores/stats` | Scraping statistics |
| `POST` | `/lists/` | Create a shopping list |
| `GET` | `/lists/` | Get your shopping lists |
| `GET` | `/lists/{id}/optimize` | Find cheapest options for a list |

Full interactive API docs available at http://localhost:8000/docs when the backend is running.

---

## Troubleshooting

### "python" is not recognized

Python wasn't added to your PATH. Reinstall Python and make sure to check **"Add Python to PATH"** during installation. Restart your terminal after reinstalling.

### "npm" is not recognized

Node.js wasn't added to your PATH. Reinstall Node.js and restart your terminal.

### MySQL connection refused

Make sure MySQL is running. If using Laragon, open it and click **"Start All"**. Check that `DB_HOST`, `DB_PORT`, `DB_USER`, and `DB_PASSWORD` in `backend/.env` match your MySQL setup.

### Playwright errors / browsers not found

Run this command inside your activated virtual environment:

```bash
playwright install chromium
```

### Port already in use

If port 8000 or 3000 is already taken, you can change them:

```bash
# Backend on a different port
uvicorn app.main:app --reload --port 8001

# Frontend on a different port
npm run dev -- --port 3001
```

If you change the backend port, update `NEXT_PUBLIC_API_URL` in `frontend/.env.local` to match.

### CORS errors in the browser

Make sure the backend is running on port 8000 and the frontend on port 3000. The backend is configured to allow requests from `http://localhost:3000`.
