import requests
from bs4 import BeautifulSoup
import json


def google_search(query, num_results=10):
    # Construct the search URL
    search_url = f"https://www.google.com/search?q={query}&num={num_results}"

    # Set a user-agent to avoid bot detection by Google
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
    }

    # Send the request to Google
    response = requests.get(search_url, headers=headers)

    # Parse the response content with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract the search results
    results = []
    for g in soup.find_all('div', class_='tF2Cxc')[:num_results]:
        title = g.find('h3').text if g.find('h3') else 'No title available'
        link = g.find('a')['href'] if g.find('a') else 'No link available'
        description = g.find('div', class_='VwiC3b').text if g.find('div',
                                                                    class_='VwiC3b') else 'No description available'
        results.append({'Title': title, 'Link': link, 'Description': description})

    return results


def save_to_json(data, filename="search_results.json"):
    """Save the search results to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    # Prompt the user to enter search terms
    query = input("Enter your Google search query: ")

    # Perform the search and get the results
    search_results = google_search(query)

    # Save the results to a JSON file
    if search_results:
        save_to_json(search_results)
        print(f"Search results saved to 'search_results.json'")
    else:
        print("No results found.")
