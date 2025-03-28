from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from dataclasses import dataclass
import time
import sys
import re

CONF_FILENAME = 'secrets.conf'
OUTPUT_FILENAME = 'scraper.out'
SHOW_BROWSER = True

@dataclass
class LinkedIn_Person:
    name: str
    title: str
    location: str
    link: str

    def __str__(self):
        return f'''Name: {self.name}
Title: {self.title}
Location: {self.location}
'''

def save_to_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)


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
            if line.startswith('linkedin_username='):
                username = line.split('=')[1].strip()
            if line.startswith('linkedin_password='):
                password = line.split('=')[1].strip()
    
    return username, password


# get a Selenium driver for browsing web pages
# also login so that only has to happen once
def linkedin_login(driver, username, password):
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


def get_profile(driver, link):
    # Navigate to the profile
    driver.get(link)

    # Wait for the profile content to load by waiting for a specific element
    time.sleep(3)

    # Scroll to the bottom of the page to load all dynamic content
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)  # Wait a bit for any lazy-loaded content to load

    # Extract the full page html content
    html_content = driver.execute_script("return document.documentElement.innerHTML;")
    soup = BeautifulSoup(html_content, 'html.parser')
    profile_content = soup.find('main')
    profile_content = remove_invisible(profile_content)

    # page_text = extract_text(html_content)
    profile_text = extract_text(profile_content.get_text())

    return profile_text


def get_string_profile_choice_list(people: list['LinkedIn_Person']):
    result = f''
    for i, person in enumerate(people):
        result += f'{i}: \n{person}\n'
    return result


# get the proper profile with user input
# if choice is not passed, get command line input from user
def get_profile_link(people: list['LinkedIn_Person'], selection: int = None):
    if selection is None:
        # Now we have a list of all potential people it could be
        # Ask the user to pick one of them
        print(get_string_profile_choice_list(people))
        print('Linkedin - Which one of the above listed options is the person you are targetting? If none of the options are correct, \
              enter "None" as your answer')
        # selection = input('Enter number: ')
        selection = 'None'

        if selection == 'None':
            return None
        else:
            return people[int(selection)].link
    else:  # a selection was passed, just use that
        return people[selection].link


# Get a list of potential profiles for the user to choose from
def get_profile_choice_list(driver, firstname, lastname):
    search_link = f'https://www.linkedin.com/search/results/people/?keywords={firstname}%20{lastname}&origin=CLUSTER_EXPANSION'

    driver.get(search_link)
    time.sleep(3)

    # Extract the full page html content
    html_content = driver.execute_script("return document.documentElement.innerHTML;")
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content = soup.find('main').find('ul', class_=re.compile(r'^[A-Za-z0-9_-]+ list-style-none$'))

    if main_content is None:
        print('LinkedIn - something went wrong with scraping the search page...')

    # got the container for the misspelled name thing
    # need to get the next ul instead
    if 'Showing results for' in main_content.text and 'Search instead for' in main_content.text:
        main_content = main_content.find_next('ul', class_=re.compile(r'^[A-Za-z0-9_-]+ list-style-none$'))

    result_containers = main_content.find_all('li')

    people = []

    for result in result_containers:
        # if critical information is missing, will cause error and we can skip this result container
        try:
            primary_info = result.find('div', class_=re.compile(r'^[A-Za-z0-9_-]+ [A-Za-z0-9_-]+ pt3 pb3 t-12 t-black--light$'))
            name = primary_info.find('span', dir='ltr').find_next('span').text.strip()
            link = primary_info.find_next('a')['href']
            title = primary_info.find('div', class_=re.compile(r'^[A-Za-z0-9_-]+ t-14 t-black t-normal$')).text.strip()  
            location = result.find('div', class_=re.compile(r'^[A-Za-z0-9_-]+ t-14 t-normal$')).text.strip()
        except AttributeError as e:
            print('Could not get the linkedin info from this profile', e)
            continue

        people.append(LinkedIn_Person(name, title, location, link))
    
    return people


# main scraping function
# not used in Flask app workflow
def scrape(firstname, lastname):
    # get user credentials from secret file
    username, password = get_credentials(CONF_FILENAME)

    # get reusable selenium driver
    driver = get_driver(username, password, SHOW_BROWSER)

    # get link to profile by searching and asking user
    profile_choice_list = get_profile_choice_list(driver, firstname, lastname)

    # get the user's choice
    profile_link = get_profile_link(profile_choice_list, None)

    # get text of profile to save to file
    print('Viewing profile...')
    profile_text = get_profile(driver, profile_link)

    # Save the extracted text to a file
    save_to_file(OUTPUT_FILENAME, profile_text)

    driver.quit()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} [firstname] [lastname]\n')
        exit()
    else:
        firstname = sys.argv[1]
        lastname = sys.argv[2]
        scrape(firstname, lastname)

