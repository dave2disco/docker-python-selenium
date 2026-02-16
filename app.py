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

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'database': os.getenv('DB_NAME', 'library_db'),
    'user': os.getenv('DB_USER', 'user'),
    'password': os.getenv('DB_PASS', 'password')
}

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
        .table-responsive { min-height: 400px; }
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
                <div class="col-md-3">
                    <strong>Libri salvati: <span id="countText">0</span> / 1000</strong>
                </div>
                <div class="col-md-9">
                    <div class="progress" style="height: 15px;">
                        <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow p-4">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Titolo</th>
                            <th>Prezzo</th>
                            <th>Disponibilità</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
            
            <nav class="d-flex justify-content-between align-items-center mt-3">
                <button id="prevBtn" class="btn btn-sm btn-outline-secondary" onclick="changePage(-1)">← Precedente</button>
                <span class="text-muted">Pagina <span id="currentPageDisplay" class="fw-bold">1</span></span>
                <button id="nextBtn" class="btn btn-sm btn-outline-secondary" onclick="changePage(1)">Successiva →</button>
            </nav>
        </div>
    </div>

    <script>
        let currentPage = 1;
        const perPage = 20;

        async function updateUI() {
            try {
                // 1. Recupero dati tabella
                const dataRes = await fetch(`/api/data?page=${currentPage}&per_page=${perPage}`);
                const books = await dataRes.json();
                const tbody = document.getElementById('tableBody');
                
                if (books.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="3" class="text-center py-4 text-muted">Nessun dato trovato per questa pagina.</td></tr>';
                } else {
                    tbody.innerHTML = books.map(b => `
                        <tr>
                            <td>${b.title}</td>
                            <td>${b.price}</td>
                            <td><span class="badge bg-info text-dark">${b.availability}</span></td>
                        </tr>
                    `).join('');
                }

                // 2. Recupero stato globale
                const statusRes = await fetch('/api/status');
                const status = await statusRes.json();
                
                const alert = document.getElementById('statusAlert');
                const btn = document.getElementById('scrapBtn');
                const countText = document.getElementById('countText');
                const bar = document.getElementById('progressBar');

                // Aggiorna contatori
                countText.innerText = status.current_count;
                bar.style.width = (status.current_count / 1000 * 100) + '%';

                // Gestione Messaggi Alert
                if (status.is_running) {
                    alert.className = "alert alert-info d-block";
                    alert.innerHTML = '<span class="status-running">● Scraping in corso... i dati appariranno gradualmente nelle pagine.</span>';
                    btn.disabled = true;
                } else if (status.last_result === "finished") {
                    alert.className = "alert alert-success d-block";
                    alert.innerHTML = '<span class="status-finished">✓ Scraping Completato! Tutti i 1000 libri sono nel database.</span>';
                    btn.disabled = false;
                    bar.classList.remove('progress-bar-animated');
                } else {
                    alert.classList.add('d-none');
                    btn.disabled = false;
                }

                // Gestione bottoni paginazione
                document.getElementById('prevBtn').disabled = (currentPage === 1);
                document.getElementById('nextBtn').disabled = (books.length < perPage);
                document.getElementById('currentPageDisplay').innerText = currentPage;

            } catch (err) { console.error("Errore polling:", err); }
        }

        function changePage(step) {
            currentPage += step;
            updateUI();
        }

        function startScraping() { fetch('/start'); }
        
        async function clearData() { 
            if(confirm("Sei sicuro di voler svuotare tutto?")) {
                await fetch('/clear', {method: 'POST'});
                currentPage = 1;
                updateUI();
            }
        }

        setInterval(updateUI, 2000);
        updateUI();
    </script>
</body>
</html>
"""

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT title, price, availability FROM scraped_data ORDER BY id ASC LIMIT %s OFFSET %s", (per_page, offset))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"title": r[0], "price": r[1], "availability": r[2]} for r in rows])

@app.route('/api/status')
def get_status():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM scraped_data")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify({**SCRAPER_STATUS, "current_count": count})

@app.route('/start')
def start():
    if not SCRAPER_STATUS["is_running"]:
        def run_scraper():
            SCRAPER_STATUS["is_running"] = True
            SCRAPER_STATUS["last_result"] = ""
            try:
                scraper = GenericScraper(DB_CONFIG)
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
    SCRAPER_STATUS["last_result"] = ""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM scraped_data")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)