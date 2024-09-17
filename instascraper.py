import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def setup_driver(proxy_address=None, proxy_port=None):
    """Set up Selenium WebDriver with proxy if provided using Firefox"""
    firefox_options = Options()

    # Uncomment this line to enable headless mode (no browser UI)
    # firefox_options.add_argument('--headless')

    # Use a proxy if provided
    if proxy_address and proxy_port:
        firefox_options.set_preference("network.proxy.type", 1)
        firefox_options.set_preference("network.proxy.http", proxy_address)
        firefox_options.set_preference("network.proxy.http_port", int(proxy_port))
        firefox_options.set_preference("network.proxy.ssl", proxy_address)
        firefox_options.set_preference("network.proxy.ssl_port", int(proxy_port))

    # Disable bot detection flags
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("useAutomationExtension", False)

    # Set up Firefox WebDriver
    driver = webdriver.Firefox(options=firefox_options)
    return driver

def login_to_instagram(driver, username, password):
    """Login to Instagram with provided credentials"""
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(3)

    # Accept Cookies (if applicable)
    try:
        accept_cookies_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[text()='Accept']"))
        )
        accept_cookies_button.click()
    except:
        pass

    # Enter username
    username_input = driver.find_element(By.NAME, "username")
    username_input.send_keys(username)

    # Enter password
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys(password)

    # Submit the form
    password_input.send_keys(Keys.RETURN)

    # Wait for login to complete
    time.sleep(5)

    try:
        not_now_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
        )
        not_now_button.click()
    except Exception as e:
        print("Push notification not found or already dismissed:", e)

def scrape_user_profile(driver, username, num_posts):
    """Scrape a user's profile information and posts"""
    profile_url = f"https://www.instagram.com/{username}/"
    driver.get(profile_url)
    time.sleep(3)

    profile_data = {
        "username": username,
        "followers_count": 0,
        "following_count": 0,
        "biography": "",
        "posts": []
    }

    try:
        # Scrape biography, followers, and following count
        meta_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//meta[@name='description']"))
        )
        description_content = meta_element.get_attribute("content")
        bio = description_content.split("on Instagram: ")[-1]
        profile_data["biography"] = bio

        profile_data["followers_count"] = driver.find_element(By.XPATH, "//a[contains(@href, '/followers')]/span").get_attribute("title").replace(',', '')
        profile_data["following_count"] = driver.find_element(By.XPATH, "//a[contains(@href, '/following')]/span").text

        # Use ActionChains to move to the bottom left corner to click the first post
        
        # Scrape multiple posts
        for i in range(num_posts):
            action = ActionChains(driver)
            action.move_by_offset(150, driver.execute_script("return window.innerHeight") - 50).click().perform()
            time.sleep(2)  # Pause to allow manual adjustments or troubleshooting


            i2 = i
            while i2 != 0:
                action.send_keys(Keys.ARROW_RIGHT).perform()
                time.sleep(2)
                i2 = i2 -1
            driver.refresh()
            post_data = scrape_post(driver)
            if post_data:
                profile_data["posts"].append(post_data)
            driver.get(profile_url)
            time.sleep(2)
            # Move the mouse to the middle right of the window to click "Next"
    except Exception as e:
        print(f"Error scraping profile {username}: {e}")

    return profile_data

def scrape_post(driver):
    """Scrape individual post data using metadata from the page"""
    post_data = {
        "description": "",
        "likes": 0,
        "comments": 0
    }

    try:
        # Wait for the URL to contain either '/p/' (posts) or '/reel/' (reels)
        WebDriverWait(driver, 10).until(
            lambda driver: '/p/' in driver.current_url or '/reel/' in driver.current_url
        )

        # After navigating to the post page, ensure it fully loads
        time.sleep(2)  # Adjust this delay if necessary

        # Check if the metadata is updated for the current post by comparing it with the previous metadata
        meta_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//meta[@name='description']"))
            )
        meta_content = meta_element.get_attribute("content")
        # Now that we have the new metadata, extract the relevant details
        if meta_content:
            meta_parts = meta_content.split(" - ")
            if len(meta_parts) < 2:
                raise ValueError("Invalid meta content format, possibly scraping the wrong page")

            interaction_data = meta_parts[0]
            post_description = meta_parts[-1].split(":")[-1].strip().strip('"')

            # Extract likes
            likes_part = interaction_data.split(" likes")[0]
            post_data["likes"] = parse_number(likes_part)

            # Extract comments
            comments_part = interaction_data.split(", ")[-1].split(" comments")[0]
            post_data["comments"] = parse_number(comments_part)

            # Set the description
            post_data["description"] = post_description
        else:
            raise ValueError("Meta content is empty or not found")

    except Exception as e:
        print(f"Error scraping post: {e}")

    return post_data

def parse_number(text):
    """Helper function to convert likes/comments (e.g., '87K', '1.2M') into integer values"""
    text = text.replace(",", "").strip().upper()
    if "K" in text:
        return int(float(text.replace("K", "")) * 1000)
    elif "M" in text:
        return int(float(text.replace("M", "")) * 1000000)
    return int(text)

def main():
    # Get user input
    usernames_input = input("Enter Instagram usernames separated by commas: ")
    usernames = [username.strip() for username in usernames_input.split(',')]
    num_posts = int(input("Enter the number of posts to scrape per profile: "))
    insta_username = input("Enter your Instagram username: ")
    insta_password = input("Enter your Instagram password: ")
    proxy_address = input("Enter proxy address (or leave blank): ")
    proxy_port = input("Enter proxy port (or leave blank): ")

    # Set up the WebDriver
    driver = setup_driver(proxy_address, proxy_port)

    try:
        # Log into Instagram
        login_to_instagram(driver, insta_username, insta_password)

        # Scrape profiles
        all_profiles = []
        for username in usernames:
            print(f"Scraping profile: {username}")
            profile_data = scrape_user_profile(driver, username, num_posts)
            all_profiles.append(profile_data)

        # Save to JSON
        with open("instagram_profiles_posts.json", "w", encoding="utf-8") as f:
            json.dump(all_profiles, f, indent=2, ensure_ascii=False)

        print("Scraping complete. Data saved to instagram_profiles_posts.json")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
