import requests
import time

def get_crypto_price(coin_id):
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data[coin_id]['usd']
    else:
        print("Error fetching data from API")
        return None

def main():
    # Define two main cryptocurrencies
    main_coins = ['bitcoin', 'ethereum']

    # Display prices for main cryptocurrencies
    print("Main Cryptocurrencies:")
    for coin in main_coins:
        price = get_crypto_price(coin)
        if price is not None:
            print(f"The current price of {coin.capitalize()} is: ${price}")

    # Allow user to input a cryptocurrency for instant view
    while True:
        user_input = input("\nEnter the cryptocurrency ID to view its price instantly (or type 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        
        price = get_crypto_price(user_input)
        if price is not None:
            print(f"The current price of {user_input.capitalize()} is: ${price}")
        else:
            print("Invalid cryptocurrency ID. Please try again.")

        time.sleep(1)  # Optional: Sleep for a moment before allowing another input

if __name__ == "__main__":
    main()
