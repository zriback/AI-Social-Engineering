"""
Description: This script automates the process of logging into Twitter (X), searching for profiles based on a first and 
last name, selecting a profile, and scraping tweets from it. The scraped tweets are saved in JSON format.
Author: Owen Joslin
Requirements: json, time, dataclasses, BeautifulSoup, selenium
"""

import json
import time
from dataclasses import dataclass
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

"""
This script automates the process of:
1) Logging into Twitter (X) using credentials from a configuration file.
2) Searching for profiles based on a first and last name.
3) Prompting the user (or using a selection parameter) to choose the correct profile.
4) Scraping a specified number of tweets from the chosen profile.
5) Saving those tweets in JSON format.

Major Steps:
- Load credentials from a configuration file.
- Initialize a Selenium-driven Firefox session to log into Twitter.
- Execute a profile search query.
- Retrieve a list of possible profiles and select one profile.
- Scrape tweets from the selected profile, scrolling as needed until the desired count is reached or no more tweets load.
- Save the collected tweets in a JSON file.
"""

CREDENTIALS_FILE = "secrets.conf"
DISPLAY_BROWSER = True
LOGIN_URL = "https://x.com/i/flow/login"

@dataclass
class TwitterProfile:
    name: str
    username: str
    bio: str
    profile_link: str

    def __str__(self):
        return f"TwitterProfile(name='{self.name}', username='@{self.username}', bio='{self.bio}', profile_link='{self.profile_link}')"


"""
Loads Twitter credentials (username and password) from a configuration file.
Only lines matching 'twitter_username=' or 'twitter_password=' are considered.
"""
def load_credentials(credentials_file):
    twitter_username = twitter_password = ''
    with open(credentials_file, 'r') as file:
        for line in file:
            if line.startswith('#'):
                continue
            if line.startswith('twitter_username='):
                twitter_username = line.split('=', 1)[1].strip()
            elif line.startswith('twitter_password='):
                twitter_password = line.split('=', 1)[1].strip()
    return twitter_username, twitter_password


"""
Initializes a Selenium-controlled Firefox session and logs into Twitter using the provided credentials.
Waits for login fields to appear, inputs credentials, and proceeds to the Twitter homepage.
"""
def init_twitter_session(twitter_username, twitter_password, display_browser):
    options = Options()
    if not display_browser:
        options.add_argument('--headless')
    options.add_argument("--log-level=3")
    driver = webdriver.Firefox(options=options, service=FirefoxService())
    driver.get(LOGIN_URL)

    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
    )
    username_input.send_keys(twitter_username)
    next_button = driver.find_element(By.XPATH, "//span[contains(text(), 'Next')]")
    next_button.click()

    password_input = WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
    )
    password_input.send_keys(twitter_password)
    login_button = driver.find_element(By.XPATH, "//span[contains(text(), 'Log in')]")
    login_button.click()

    WebDriverWait(driver, 30).until(EC.url_contains("home"))
    return driver


"""
Uses the provided driver to search Twitter (X) for profiles matching a given first and last name.
Extracts candidate profiles, their bios, and links. Returns a list of TwitterProfile objects.
"""
def search_twitter_profiles(selenium_driver, first_name, last_name):
    search_url = f'https://x.com/search?q={first_name}%20{last_name}&src=recent_search_click&f=user'
    selenium_driver.get(search_url)
    time.sleep(3)
    page_source = selenium_driver.execute_script("return document.documentElement.innerHTML;")
    soup = BeautifulSoup(page_source, 'html.parser')
    section = soup.find('section', attrs={'aria-labelledby': True, 'role': 'region'})
    profiles_found = []
    if section:
        for user_cell in section.find_all('button', attrs={'data-testid': 'UserCell'}):
            if 'Followed by' in user_cell.get_text():
                continue
            dir_divs = user_cell.find_all('div', attrs={'dir': True})
            dir_texts = [div.get_text(strip=True) for div in dir_divs if div.get_text(strip=True)]
            if len(dir_texts) < 2:
                continue
            name = dir_texts[0]
            username = dir_texts[1].lstrip('@')
            a_tag = user_cell.find('a', href=True)
            profile_link = 'https://x.com' + a_tag['href'] if a_tag else f'https://x.com/{username}'
            bio_divs = [
                div for div in user_cell.find_all('div', attrs={'dir': 'auto'})
                if 'Click to Follow' not in div.get_text() and 'Click to Follow' not in div.get('id', '')
            ]
            bio_texts = [div.get_text(strip=True) for div in bio_divs if div.get_text(strip=True)]
            filtered_bio_texts = [text for text in bio_texts if text not in [name, f"@{username}"]]
            bio = filtered_bio_texts[-1] if filtered_bio_texts else ''
            profile = TwitterProfile(name=name, username=username, bio=bio, profile_link=profile_link)
            profiles_found.append(profile)
    return profiles_found


"""
Scrapes tweets from a given Twitter profile link. Continues scrolling until the desired number of tweets 
is reached or no more tweets can be loaded. Saves the tweets in a JSON file and returns them as a list.
Uses global TWEET_COUNT and OUTPUT_FILENAME variables for configuration.
"""
def scrape_tweets_from_profile(selenium_driver, profile_url):
    global TWEET_COUNT, OUTPUT_FILENAME
    selenium_driver.get(profile_url)
    time.sleep(3)
    tweets = []
    last_height = selenium_driver.execute_script("return document.body.scrollHeight")

    while len(tweets) < TWEET_COUNT:
        soup = BeautifulSoup(selenium_driver.page_source, 'html.parser')
        tweet_articles = soup.find_all('article')
        for article in tweet_articles:
            if len(tweets) >= TWEET_COUNT:
                break
            tweet_text = None
            for descendant in article.descendants:
                if descendant.name in ['span', 'div']:
                    if 'tweetText' in (descendant.get('data-testid') or ''):
                        tweet_text = descendant.get_text(strip=True)
                        break
            if tweet_text and tweet_text not in tweets:
                tweets.append(tweet_text)

        selenium_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = selenium_driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        json.dump(tweets[:TWEET_COUNT], f, ensure_ascii=False, indent=4)

    return tweets[:TWEET_COUNT]


"""
Allows the user (or a provided selection parameter) to choose the correct profile from a list of TwitterProfile objects.
If no valid profile is selected, returns None.
"""
def select_profile_url(profiles: list[TwitterProfile], selection=None):
    if selection is None:
        for i, profile in enumerate(profiles):
            print(f"{i}: {profile}")
        print('If none of the above options are correct, enter "None"')
        selection_input = input('Enter number of the correct profile or "None": ')
        if selection_input.strip().lower() == 'none':
            return None
        else:
            try:
                selection_index = int(selection_input.strip())
                if selection_index < 0 or selection_index >= len(profiles):
                    print("Invalid selection. No profile selected.")
                    return None
                return profiles[selection_index].profile_link
            except ValueError:
                print("Invalid input. No profile selected.")
                return None
    else:
        if selection == 'None':
            return None
        else:
            try:
                selection_index = int(selection)
                if selection_index < 0 or selection_index >= len(profiles):
                    print("Invalid selection index passed in. No profile selected.")
                    return None
                return profiles[selection_index].profile_link
            except ValueError:
                print("Invalid selection parameter passed in. No profile selected.")
                return None


"""
Main function that:
1) Defines TWEET_COUNT and OUTPUT_FILENAME as global variables.
2) Loads credentials.
3) Logs into Twitter (X).
4) Searches for profiles using the provided first and last name.
5) Prompts for profile selection (or uses a given index).
6) Scrapes the specified number of tweets from the selected profile.
7) Saves the tweets and prints a sample to the console.
"""
def main_scrape_tweets(first_name, last_name, selection=None):
    global TWEET_COUNT, OUTPUT_FILENAME
    TWEET_COUNT = 100
    OUTPUT_FILENAME = "tweets.json"

    twitter_username, twitter_password = load_credentials(CREDENTIALS_FILE)
    selenium_driver = init_twitter_session(twitter_username, twitter_password, DISPLAY_BROWSER)
    profiles_list = search_twitter_profiles(selenium_driver, first_name, last_name)
    profile_link = select_profile_url(profiles_list, selection=selection)
    if profile_link is None:
        print("No valid profile selected. Exiting...")
        selenium_driver.quit()
        return
    print('Getting tweets...')
    tweets = scrape_tweets_from_profile(selenium_driver, profile_link)
    selenium_driver.quit()
    print("Saved tweets to:", OUTPUT_FILENAME)
    print("Sample tweets:", tweets[:5])


if __name__ == "__main__":
    first_name = "Jonathan"
    last_name = "Weissman"
    main_scrape_tweets(first_name, last_name)
