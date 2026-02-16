FROM python:3.10-slim

# Installazione dipendenze minime di sistema
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    curl \
    unzip \
    --no-install-recommends

# Aggiunta repository Google Chrome usando il metodo moderno (GPG keyring)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia dei requisiti e installazione
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia di tutto il codice sorgente
COPY . .

EXPOSE 5000

# Avvio dell'app Flask
CMD ["python", "app.py"]