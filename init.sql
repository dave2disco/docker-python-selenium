CREATE TABLE IF NOT EXISTS scraped_data (
    id SERIAL PRIMARY KEY,
    title TEXT,
    price TEXT,
    availability TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);