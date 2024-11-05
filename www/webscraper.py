import requests
from bs4 import BeautifulSoup
import json

# Function to scrape the text content from a webpage
def scrape_webpage(url):
    try:
        # Send an HTTP request to the webpage
        # Set headers with a User-Agent to simulate a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
        }

        # Send an HTTP request with the headers
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the text from the webpage
        text = soup.get_text(separator=' ', strip=True)

        # Return the extracted text
        return text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return None

# Function to store the text in a JSON file
def save_to_json(text, filename='webpage_text.json'):
    data = {
        "url_text": text
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

    print(f"Text saved to {filename}")

# Main function to execute the scraper
def main():
    # Example URL to scrape
    url = input("Enter the URL of the webpage to scrape: ")

    # Scrape the text from the webpage
    text = scrape_webpage(url)

    # If text is successfully scraped, save it to JSON
    if text:
        save_to_json(text)

if __name__ == '__main__':
    main()