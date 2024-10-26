import json
import time
from subprocess import CREATE_NO_WINDOW

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Configuration constants
CONF_FILENAME = "secrets.conf"
SHOW_BROWSER = True
X_LOGIN_URL = "https://x.com/i/flow/login"

class TwitterPerson:
    """Class to store Twitter profile information."""

    def __init__(self, name, username, bio, profile_link):
        self.name = name
        self.username = username
        self.bio = bio
        self.profile_link = profile_link

    def __str__(self):
        return (
            f"TwitterPerson(name='{self.name}', username='@{self.username}', "
            f"bio='{self.bio}', profile_link='{self.profile_link}')"
        )

def get_credentials(filename):
    """Retrieve Twitter credentials from a configuration file."""
    username = password = ''
    with open(filename, 'r') as file:
        for line in file:
            if line.startswith('#'):
                continue
            if line.startswith('twitter_username='):
                username = line.split('=', 1)[1].strip()
            elif line.startswith('twitter_password='):
                password = line.split('=', 1)[1].strip()
    return username, password

def initialize_webdriver(username, password, show_browser):
    options = Options()
    if not show_browser:
        options.add_argument('--headless=old')
    options.add_argument("--log-level=3")
    chrome_service = ChromeService()
    chrome_service.creation_flags = CREATE_NO_WINDOW
    driver = webdriver.Chrome(options=options, service=chrome_service)

    # Log into Twitter
    driver.get(X_LOGIN_URL)
    # Wait for username input and enter username
    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
    )
    username_input.send_keys(username)
    # Click 'Next' button
    next_button = driver.find_element(By.XPATH, "//span[contains(text(), 'Next')]")
    next_button.click()
    # Wait for password input and enter password
    password_input = WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
    )
    password_input.send_keys(password)
    # Click 'Log in' button
    login_button = driver.find_element(By.XPATH, "//span[contains(text(), 'Log in')]")
    login_button.click()
    # Wait until logged in
    WebDriverWait(driver, 30).until(EC.url_contains("home"))
    return driver

def search_profiles(driver, first_name, last_name):
    """
    Search for profiles matching the given first and last name.
    """
    search_url = (
        f'https://x.com/search?q={first_name}%20{last_name}'
        '&src=recent_search_click&f=user'
    )
    driver.get(search_url)
    time.sleep(3)  # Wait for the page to load

    # Parse the page source with BeautifulSoup
    page_source = driver.execute_script("return document.documentElement.innerHTML;")
    soup = BeautifulSoup(page_source, 'html.parser')

    # Find the section containing user profiles
    section = soup.find('section', attrs={'aria-labelledby': True, 'role': 'region'})
    twitter_profiles = []

    if section:
        # Iterate over user profiles found in the search results
        for user_cell in section.find_all('button', attrs={'data-testid': 'UserCell'}):
            if 'Followed by' in user_cell.get_text():
                continue  # Skip this result

            # Extract name and username
            dir_divs = user_cell.find_all('div', attrs={'dir': True})
            dir_texts = [
                div.get_text(strip=True)
                for div in dir_divs
                if div.get_text(strip=True)
            ]
            if len(dir_texts) >= 2:
                name = dir_texts[0]
                username = dir_texts[1].lstrip('@')
            else:
                continue  # Skip if name and username not found

            # Extract profile link
            a_tag = user_cell.find('a', href=True)
            profile_link = 'https://x.com' + a_tag['href'] if a_tag else f'https://x.com/{username}'

            # Extract bio
            bio_divs = [
                div for div in user_cell.find_all('div', attrs={'dir': 'auto'})
                if 'Click to Follow' not in div.get_text()
                and 'Click to Follow' not in div.get('id', '')
            ]
            bio_texts = [
                div.get_text(strip=True) for div in bio_divs if div.get_text(strip=True)
            ]
            bio_texts_filtered = [
                text for text in bio_texts if text not in [name, f"@{username}"]
            ]
            bio = bio_texts_filtered[-1] if bio_texts_filtered else ''

            # Create TwitterPerson object and add to the list
            person = TwitterPerson(name, username, bio, profile_link)
            twitter_profiles.append(person)

    return twitter_profiles

def format_profile_choices(profiles):
    """
    Format the list of profiles for display.
    """
    result = ''
    for i, profile in enumerate(profiles):
        result += f'{i}: \n{profile}\n\n'
    return result

def select_profile(profiles, selection=None):
    """
    Let the user select a profile from the list of profiles.
    """
    if selection is None:
        print(format_profile_choices(profiles))
        print('Which one of the above listed options is the person you are targeting?')
        selection = int(input('Enter number: '))
    return profiles[selection].profile_link

def get_tweets_and_save(driver, profile_link, num_tweets, output_filename):
    """
    Extract tweets from the profile and save them to a JSON file.
    """
    driver.get(profile_link)
    time.sleep(3)  # Allow time for the page to load fully

    tweets = []
    last_height = driver.execute_script("return document.body.scrollHeight")

    while len(tweets) < num_tweets:
        # Parse page source with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all tweet articles
        tweet_articles = soup.find_all('article')

        # Extract text from each article
        for article in tweet_articles:
            if len(tweets) >= num_tweets:
                break

            # Locate the tweet content
            tweet_text = None
            for descendant in article.descendants:
                if descendant.name in ['span', 'div']:
                    if 'tweetText' in descendant.get('data-testid', ''):
                        tweet_text = descendant.get_text(strip=True)
                        break

            # Append tweet text if found and not duplicate
            if tweet_text and tweet_text not in tweets:
                tweets.append(tweet_text)

        # Scroll down to load more tweets
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for new tweets to load

        # Check if we've reached the bottom of the page
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  # No more content to load
        last_height = new_height

    return tweets[:num_tweets]

def scrape_tweets(first_name, last_name, tweet_count, output_filename):
    """
    Main function to scrape tweets from a user's profile.
    """
    # Get user credentials from the config file
    username, password = get_credentials(CONF_FILENAME)

    # Initialize Selenium WebDriver and log in to Twitter
    driver = initialize_webdriver(username, password, SHOW_BROWSER)

    # Search for profiles matching the name
    profiles = search_profiles(driver, first_name, last_name)

    # Let the user select a profile from the search results
    profile_link = select_profile(profiles)

    # Extract tweets from the profile and save to JSON file
    print('Getting tweets...')
    get_tweets_and_save(driver, profile_link, tweet_count, output_filename)

    driver.quit()

if __name__ == "__main__":
    # Example usage
    first_name = "Jonathan"
    last_name = "Weissman"
    tweet_count = 100
    output_filename = "tweets.json"

    scrape_tweets(first_name, last_name, tweet_count, output_filename)
