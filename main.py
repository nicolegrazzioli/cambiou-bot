import os
import json
import time
import requests

# Configuration
STATE_FILE = "last_run.json"
MAX_RETRIES = 3
INITIAL_BACKOFF = 5  # seconds

# API URLs (primary + fallback)
AWESOME_API_URL = "https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL"
FALLBACK_API_URL = "https://open.er-api.com/v6/latest/BRL"

# Load environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """Sends a message to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not found in environment variables.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("Message sent to Telegram successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Telegram: {e}")

def load_state():
    """Loads the last run state from JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error reading state file, starting fresh.")
    return {}

def save_state(state):
    """Saves the current state to JSON file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
        print(f"State saved to {STATE_FILE}.")
    except IOError as e:
        print(f"Error saving state file: {e}")

def _request_with_retry(url, headers=None):
    """Makes a GET request with retry logic for transient errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Attempt {attempt}/{MAX_RETRIES} -> {url[:60]}...")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429 and attempt < MAX_RETRIES:
                wait_time = INITIAL_BACKOFF * (2 ** (attempt - 1))
                print(f"  Rate limited (429). Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  HTTP error: {e}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
            if attempt < MAX_RETRIES:
                wait_time = INITIAL_BACKOFF * (2 ** (attempt - 1))
                print(f"  Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return None
    return None

def fetch_rates_awesome():
    """Fetches rates from AwesomeAPI and returns normalized dict."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    data = _request_with_retry(AWESOME_API_URL, headers=headers)
    if data is None:
        return None
    
    result = {}
    usd = data.get("USDBRL")
    eur = data.get("EURBRL")
    if usd:
        result["USD"] = float(usd["bid"])
    if eur:
        result["EUR"] = float(eur["bid"])
    return result if result else None

def fetch_rates_fallback():
    """Fetches rates from open.er-api.com (free, no key needed).
    
    This API returns rates FROM BRL, so we invert to get the price
    of 1 USD/EUR in BRL.
    """
    data = _request_with_retry(FALLBACK_API_URL)
    if data is None or data.get("result") != "success":
        return None
    
    rates = data.get("rates", {})
    result = {}
    
    # API gives BRL -> X, we need X -> BRL (i.e., 1/rate)
    usd_rate = rates.get("USD")
    eur_rate = rates.get("EUR")
    
    if usd_rate and usd_rate > 0:
        result["USD"] = round(1.0 / usd_rate, 4)
    if eur_rate and eur_rate > 0:
        result["EUR"] = round(1.0 / eur_rate, 4)
    
    return result if result else None

def fetch_rates():
    """Fetches rates trying AwesomeAPI first, then fallback."""
    print("Trying primary API (AwesomeAPI)...")
    rates = fetch_rates_awesome()
    if rates:
        print(f"Got rates from AwesomeAPI: {rates}")
        return rates
    
    print("Primary API failed. Trying fallback (open.er-api.com)...")
    rates = fetch_rates_fallback()
    if rates:
        print(f"Got rates from fallback API: {rates}")
        return rates
    
    print("All APIs failed.")
    return None

def format_currency(value):
    """Formats float to currency string with 2 decimal places."""
    return f"{value:.2f}"

def calculate_wise_price(price):
    """Calculates Wise simulation price: price + (price * 0.02)."""
    return price + (price * 0.02)

def main():
    print("Starting Currency Monitoring Agent...")
    
    # Check for secrets early
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
         print("Warning: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set.")

    rates = fetch_rates()
    
    if rates is None:
        print("Could not fetch rates from any source. Exiting gracefully.")
        return
    
    last_run_state = load_state()
    
    # Process each currency
    for currency_code, current_price in rates.items():
        process_currency(currency_code, current_price, last_run_state)

    # Save current rates for next run comparison
    save_state(rates)
    print("Agent finished successfully.")

def process_currency(currency_code, current_price, last_state):
    """Processes a single currency: compares, notifies."""
    last_price = last_state.get(currency_code)
    
    print(f"Checking {currency_code}: Current={current_price}, Last={last_price}")

    if last_price is None:
        print(f"First run for {currency_code}. Saving value without notification.")
        return

    if current_price != last_price:
        trend = "SUBIU 📈" if current_price > last_price else "CAIU 📉"
        wise_value = calculate_wise_price(current_price)
        
        message = (
            f"[{currency_code}] {trend} para R$ {format_currency(current_price)}. "
            f"Wise: R$ {format_currency(wise_value)}"
        )
        
        print(f"Sending notification: {message}")
        send_telegram_message(message)
    else:
        print(f"No change in {currency_code} value.")

if __name__ == "__main__":
    main()
