import os
import json
import requests
import sys

# Configuration
API_URL = "https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL"
STATE_FILE = "last_run.json"

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

def fetch_rates():
    """Fetches current exchange rates from AwesomeAPI."""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching rates: {e}")
        sys.exit(1)

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
         print("Warning: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set. Notifications will store state but not send messages.")

    current_rates_data = fetch_rates()
    last_run_state = load_state()
    
    # Process USD
    usd_data = current_rates_data.get("USDBRL")
    if usd_data:
        process_currency("USD", usd_data, last_run_state)
        
    # Process EUR
    eur_data = current_rates_data.get("EURBRL")
    if eur_data:
        process_currency("EUR", eur_data, last_run_state)

    # Save the new state with current values
    # We update the state object with the current values so it's ready for next run
    # Note: process_currency updates the state object in place if needed, 
    # but strictly speaking we want to save the *current* rates as the "last run" for the *next* execution.
    # The requirement says: "comparar o preço atual com o preço da última execução."
    # So we should save the current rates now.
    
    new_state = {
        "USD": float(usd_data["bid"]) if usd_data else last_run_state.get("USD"),
        "EUR": float(eur_data["bid"]) if eur_data else last_run_state.get("EUR")
    }
    
    # Remove None values
    new_state = {k: v for k, v in new_state.items() if v is not None}
    
    save_state(new_state)
    print("Agent finished successfully.")

def process_currency(currency_code, data, last_state):
    """Processes a single currency: compares, notifies."""
    try:
        current_price = float(data["bid"])
    except ValueError:
        print(f"Error parsing price for {currency_code}")
        return

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
