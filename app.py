import os
import psycopg2
import threading
from flask import Flask, render_template_string, jsonify, request
from scraper import GenericScraper

app = Flask(__name__)

# Stato globale dello scraper
SCRAPER_STATUS = {
    "is_running": False, 
    "last_result": "", 
    "total_target": 1000
}

def get_db_connection():
    """Connessione unificata con supporto SSL per Render."""
    db_url = os.environ.get('DATABASE_URL')
    try:
        if db_url:
            # Render richiede sslmode=require per connessioni sicure
            if "sslmode=" not in db_url:
                db_url += ("?" if "?" not in db_url else "&") + "sslmode=require"
            return psycopg2.connect(db_url)
        else:
            return psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'library_db'),
                user=os.getenv('DB_USER', 'user'),
                password=os.getenv('DB_PASS', 'password'),
                port=os.getenv('DB_PORT', '5432')
            )
    except Exception as e:
        print(f"Errore connessione DB: {e}")
        raise e

def init_db():
    """Crea la tabella se non esiste all'avvio."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraped_data (
                id SERIAL PRIMARY KEY,
                title TEXT,
                price TEXT,
                availability TEXT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Database inizializzato correttamente.")
    except Exception as e:
        print(f"Errore inizializzazione database: {e}")

# Inizializza il DB all'avvio dell'app
init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Selenium Books Scraper</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        .status-running { color: #0d6efd; font-weight: bold; animation: blink 1.5s infinite; }
        .status-finished { color: #198754; font-weight: bold; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body class="bg-light">
    <div class="container py-5">
        <div class="card shadow p-4 mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h1>Live Book Scraper</h1>
                <div>
                    <button onclick="startScraping()" id="scrapBtn" class="btn btn-primary me-2">Avvia Scraping</button>
                    <button onclick="clearData()" class="btn btn-danger">Pulisci Database</button>
                </div>
            </div>
            <div id="statusAlert" class="alert d-none mb-3"></div>
            <div class="row align-items-center">
                <div class="col-md-3"><strong>Libri: <span id="countText">0</span> / 1000</strong></div>
                <div class="col-md-9">
                    <div class="progress"><div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" style="width: 0%"></div></div>
                </div>
            </div>
        </div>
        <div class="card shadow p-4">
            <table class="table">
                <thead><tr><th>Titolo</th><th>Prezzo</th><th>Disponibilità</th></tr></thead>
                <tbody id="tableBody"></tbody>
            </table>
            <nav class="d-flex justify-content-between mt-3">
                <button id="prevBtn" class="btn btn-sm btn-outline-secondary" onclick="changePage(-1)">←</button>
                <span>Pagina <span id="currentPageDisplay">1</span></span>
                <button id="nextBtn" class="btn btn-sm btn-outline-secondary" onclick="changePage(1)">→</button>
            </nav>
        </div>
    </div>
    <script>
        let currentPage = 1;
        async function updateUI() {
            try {
                const dataRes = await fetch(`/api/data?page=${currentPage}`);
                const books = await dataRes.json();
                document.getElementById('tableBody').innerHTML = books.map(b => `
                    <tr><td>${b.title}</td><td>${b.price}</td><td><span class="badge bg-info">${b.availability}</span></td></tr>
                `).join('');
                
                const statusRes = await fetch('/api/status');
                const status = await statusRes.json();
                document.getElementById('countText').innerText = status.current_count;
                document.getElementById('progressBar').style.width = (status.current_count / 10) + '%';
                
                const alert = document.getElementById('statusAlert');
                if (status.is_running) {
                    alert.className = "alert alert-info d-block";
                    alert.innerHTML = "Scraping in corso...";
                } else if (status.last_result === "finished") {
                    alert.className = "alert alert-success d-block";
                    alert.innerHTML = "Completato!";
                } else { alert.classList.add('d-none'); }
            } catch (err) {}
        }
        function changePage(s) { currentPage += s; updateUI(); }
        function startScraping() { fetch('/start'); }
        async function clearData() { if(confirm("Pulisci?")) await fetch('/clear', {method:'POST'}); updateUI(); }
        setInterval(updateUI, 3000);
        updateUI();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    page = int(request.args.get('page', 1))
    offset = (page - 1) * 20
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT title, price, availability FROM scraped_data ORDER BY id ASC LIMIT 20 OFFSET %s", (offset,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{"title": r[0], "price": r[1], "availability": r[2]} for r in rows])
    except:
        return jsonify([]), 500

@app.route('/api/status')
def get_status():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM scraped_data")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify({**SCRAPER_STATUS, "current_count": count})
    except:
        return jsonify({**SCRAPER_STATUS, "current_count": 0})

@app.route('/start')
def start():
    if not SCRAPER_STATUS["is_running"]:
        def run_scraper():
            SCRAPER_STATUS["is_running"] = True
            try:
                # Passiamo la stringa DATABASE_URL direttamente se esiste
                db_url = os.environ.get('DATABASE_URL')
                if db_url and "sslmode=" not in db_url:
                    db_url += ("?" if "?" not in db_url else "&") + "sslmode=require"
                
                config = db_url if db_url else {
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'database': os.getenv('DB_NAME', 'library_db'),
                    'user': os.getenv('DB_USER', 'user'),
                    'password': os.getenv('DB_PASS', 'password')
                }
                scraper = GenericScraper(config)
                scraper.scrape("https://books.toscrape.com/index.html")
                SCRAPER_STATUS["last_result"] = "finished"
            except Exception as e:
                SCRAPER_STATUS["last_result"] = f"error: {str(e)}"
            finally:
                SCRAPER_STATUS["is_running"] = False
        threading.Thread(target=run_scraper).start()
    return jsonify({"status": "started"})

@app.route('/clear', methods=['POST'])
def clear():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM scraped_data")
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "cleared"})
    except:
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
