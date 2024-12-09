import requests
from bs4 import BeautifulSoup
import json
from io import BytesIO
from pdfminer.high_level import extract_text

# Function to scrape the text content from a webpage
# Function to scrape the text content from a webpage
def scrape_webpage(url: str):
    try:
        print('Trying to get webpage:', url)
        # Send an HTTP request to the webpage
        # Set headers with a User-Agent to simulate a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
        }

        # sometimes need to get rid of ** characters in the link
        url = url.replace('**', '')

        text = ''
        # Send an HTTP request with the headers
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        print('url is', url)
        if not url.endswith('.pdf'):
            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract the text from the webpage
            text = soup.get_text(separator=' ', strip=True)
        else:
            print('this ends with a pdf')
            # Step 2: Read PDF content from bytes
            pdf_file = BytesIO(response.content)

            # Step 3: Extract text from the PDF
            text = extract_text(pdf_file)

        # Return the extracted text
        return text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        print('Continuing scraping...')
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
