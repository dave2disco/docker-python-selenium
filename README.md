# 📚 Selenium Book Scraper

Un'applicazione Python completa per lo scraping automatizzato, la memorizzazione su database relazionale e la visualizzazione in tempo reale tramite interfaccia web. Il progetto è interamente containerizzato con Docker.

## 🚀 Funzionalità

* **Scraping Dinamico**: Utilizza **Selenium** in modalità *headless* per navigare tra le pagine del sito [Books to Scrape](https://books.toscrape.com/).
* **Real-time Monitoring**: Dashboard web locale (localhost) con aggiornamento automatico dei dati tramite AJAX/Polling (non serve ricaricare la pagina).
* **Contatore Progressivo**: Visualizzazione in tempo reale dei libri salvati rispetto al totale (X / 1000) con barra di avanzamento.
* **Persistenza Dati**: Integrazione con un database **PostgreSQL** per la memorizzazione sicura dei dati estratti.
* **Gestione Task**: Lo scraping gira in un thread separato per non bloccare l'interfaccia utente.
* **Pulizia Dati**: Funzionalità integrata per svuotare il database direttamente dalla dashboard.

## 🛠️ Stack Tecnologico

* **Linguaggio:** Python 3.10
* **Scraping:** Selenium (Chrome Driver)
* **Web Framework:** Flask
* **Database:** PostgreSQL 15
* **Infrastruttura:** Docker & Docker Compose
* **Frontend:** Bootstrap 5 (CSS) & Vanilla JavaScript
