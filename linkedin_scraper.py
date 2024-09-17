from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

CONF_FILENAME = 'secrets.conf'
OUTPUT_FILENAME = 'scraper.out'
PROFILE_LINK = 'https://www.linkedin.com/in/williamhgates/'
SHOW_BROWSER = True

def extract_text(html_content):
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract the text from the parsed HTML
    # Remove script and style elements
    for script_or_style in soup(['script', 'style', 'code']):
        script_or_style.decompose()

    # Get the human-readable text
    text = soup.get_text(separator=' ')

    clean_text = ''
    for line in text.strip().split('\n'):
        if line == '' or line == '\n' or all(c == ' ' for c in line):
            continue
        clean_text += (line + '\n')
        
    return clean_text


def remove_invisible(soup):
    # Find and extract all elements with class="visually-hidden"
    for hidden in soup.find_all(class_='visually-hidden'):
        hidden.decompose()  # Remove the element from the soup

    # Return the modified content as a string
    return soup


def get_credentials(filename):
    username = ''
    password = ''
    with open(filename, 'r') as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue
            if line.startswith('username='):
                username = line.split('=')[1].strip()
            if line.startswith('password='):
                password = line.split('=')[1].strip()
    
    return username, password


def get_profile(link, username, password):
    # Initialize WebDriver and Chrome options
    options = Options()

    # only need to show browser if the user must complete a CAPTCHA
    if not SHOW_BROWSER:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)

    # Open LinkedIn login page
    driver.get("https://www.linkedin.com/login")

    # Allow the page to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))

    # Locate the username and password input fields and enter the credentials
    username_input = driver.find_element(By.ID, "username")
    password_input = driver.find_element(By.ID, "password")

    username_input.send_keys(username)
    password_input.send_keys(password)

    # Find and click the login button
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()

    # Wait for the profile page to load and navigate to the desired profile
    WebDriverWait(driver, 30).until(EC.url_contains("feed"))
    
    # Navigate to the profile
    driver.get(link)

    # Wait for the profile content to load by waiting for a specific element
    time.sleep(3)

    # Scroll to the bottom of the page to load all dynamic content
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)  # Wait a bit for any lazy-loaded content to load

    # Extract the full page source
    html_content = driver.execute_script("return document.documentElement.innerHTML;")
    soup = BeautifulSoup(html_content, 'html.parser')
    profile_content = soup.find('main')
    profile_content = remove_invisible(profile_content)

    # page_text = extract_text(html_content)
    profile_text = extract_text(profile_content.get_text())
   
    # Close the browser
    driver.quit()

    return profile_text


def scrape():
    username, password = get_credentials(CONF_FILENAME)
    profile_text = get_profile(PROFILE_LINK, username, password)

    # Save the extracted text to a file
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        f.write(profile_text)


if __name__ == '__main__':
    scrape()

