from flask import Flask, render_template, request, session, jsonify, copy_current_request_context
from flask_session import Session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from subprocess import CREATE_NO_WINDOW
import threading
import linkedin_scraper as ls
import search_scraper as gs
from webscraper import scrape_webpage
import twitter_scraper as ts
from query_ai import *
from query_ai import query as query_ai
import instascraper as _is
from instascraper import OUTPUT_FILENAME as INSTAGRAM_OUT
import re
import json
import time

APP_SHOW_BROWSER = True
CONF_FILENAME = 'secrets.conf'
SUMMARY_OUTPUT_FILENAME = 'target_summary.out'
PHISHING_OUTPUT_FILENAME = 'phishing_mats.out'
LINKEDIN_SCRAPER_OUTPUT_FILE = 'linkedin_scraper.out'
TWITTER_SCRAPER_OUTPUT_FILE = 'twitter_scraper.out'
INTSTAGRAM_SCRAPER_OUTPUT_FILE = 'instagram_scraper.out'
GOOGLE_SEARCH_OUTPUT_FILE = 'google_scraper.out'
WEB_SCRAPER_OUTPUT_FILE = 'web_scraper.out'
RESCRAPE_WEB_SCRAPER_OUTPUT_FILE = 'rescrape.out'

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# finds the first number in a string and returns it
# used for extracting a number answer from ChatGPT
def find_first_number(string: str):
    # Find the first occurrence of an integer, positive or negative
    match = re.search(r'-?\d+', string)
    if match:
        # Return the first match as an integer
        return int(match.group())
    else:
        # Return None if no number is found
        return None


def extract_links(text):
    # Regular expression pattern to match URLs
    url_pattern = r'(https?://[^\s]+)'

    # Find all occurrences of the pattern in the text
    links = re.findall(url_pattern, text)

    for i, link in enumerate(links):
        clean_link = re.match(r'\((.*?)\)', link)
        if clean_link is None:
            link = link.strip('*()[]')
            links[i] = link
        else:
            links[i] = clean_link

    return links


def get_driver(show_browser):
    options = Options()

    if not show_browser:
        options.add_argument('--headless=old')
    options.add_argument("--log-level=3")

    chrome_service = ChromeService()
    chrome_service.creation_flags = CREATE_NO_WINDOW

    driver = webdriver.Chrome(options=options, service=chrome_service)

    return driver


def scrape_instagram(selenium_driver: webdriver, session: dict):
    username, password = _is.get_credentials(CONF_FILENAME)
    target_info = session.get('target_name') + ' ' + session.get('more_info')
    num_posts = 5  # 5 is a more conservative amount
    
    #try:
    selenium_driver.get(f"https://www.google.com/search?q={target_info}+instagram")
    time.sleep(2)
    titles = selenium_driver.find_elements(By.TAG_NAME, "h3")
    usernames2 = []
    for t in titles:
        stuff = t.text
        if "@" in stuff:
            help = stuff.split("@")[1].split()[0]
            help = help[:-1]
            
            usernames2.append(help)

        if len(usernames2) == 5:
            break
    # Log into Instagram
    _is.login_to_instagram(selenium_driver, username, password)
    candidates = []

    for username in usernames2:
        profiledata = _is.scrape_user_profile(selenium_driver, username, 1)
        candidates.append(profiledata)
    
    candidates.append(target_info)

    with open("candidates.json", "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False) 

    _is.query("candidates.json", 2)
    with open(INSTAGRAM_OUT, 'r') as file:
        contents = file.read()

    awesomenumber = find_first_number(contents)

    if awesomenumber == -1:
        print('No suitable profile found by instagram scraper.')
        with open(INTSTAGRAM_SCRAPER_OUTPUT_FILE, 'w') as f:
            f.write('No instagram profile was found for this target')
    else:
        print('candidates is', candidates)
        print('length of it is', len(candidates))
        print('awesomenumber is', awesomenumber)
        print('first thing we got is', candidates[awesomenumber - 1])
        usernames_input = candidates[awesomenumber - 1]['username']
        print(f'instascraper - selected {usernames_input}')
        usernames = [username.strip() for username in usernames_input.split(',')]
        # Scrape profiles
        all_profiles = []
        for username in usernames:
            print(f"Scraping profile: {username}")
            profile_data = _is.scrape_user_profile(selenium_driver, username, num_posts)
            all_profiles.append(profile_data)

        # Save to JSON
        with open(INTSTAGRAM_SCRAPER_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_profiles, f, indent=2, ensure_ascii=False)

        print("Scraping complete. Data saved to instagram_profiles_posts.json")
    # except Exception as e:
    #     print('Something went wrong with the instragram scraper', e)
    

def scrape_google(session: dict, output_file, search_query=None):
    output = ''
    # get initial inputed information
    firstname, lastname = tuple(session.get('target_name').split())
    more_info = session.get('more_info')
    if search_query is None:
        search_query = firstname + " " + lastname + " " + more_info

    # perform initial google search
    search_results = gs.google_search(search_query)
    with open(GOOGLE_SEARCH_OUTPUT_FILE, 'w') as json_file:
        json.dump(search_results, json_file, indent=4)

    # query ChatGPT for the relevant findings
    string_query_ai = f'This is information from 10 google sites, rank them in the likelihood that they have good information about {firstname} {lastname} who we know the following about, too: \
        {more_info}. If the link has a chance of having good information about the target, return it.'
    query_with_file('google_search.out', GOOGLE_SEARCH_OUTPUT_FILE, string_query_ai)
    with open("google_search.out", 'r', encoding='utf-8', errors='ignore') as f:
        file_content = f.read()

    links = extract_links(file_content)

    # scrape all relevant links
    # send all linkedin, instagram, and twitter to the proper scrapers
    for link in links:
        time.sleep(2)
        print(f'Found link on Google: {link}')
        # can also SKIP all these things and assume they will be found by their own scrapers
        if "linkedin" in link:
            pass
        elif "instagram" in link:
            pass
        elif "twitter" or "https://x.com" in link:
            pass
        else:
            scrape_output = scrape_webpage(link)
            if scrape_output is not None:
                output += scrape_output
    ls.save_to_file(output_file, output)


def scrape_linkedin(selenium_driver: webdriver, session: dict):
    username, password = tuple(ls.get_credentials(CONF_FILENAME))
    ls.linkedin_login(selenium_driver, username, password)

    firstname, lastname = tuple(session.get('target_name').split())
    more_info = session.get('more_info')

    profile_choice_list = ls.get_profile_choice_list(selenium_driver, firstname, lastname)
    # save profile choice list to session so can be accessed later once the user makes a choice
    session['profile_choice_list'] = profile_choice_list
    
    choice_list_printout = ls.get_string_profile_choice_list(profile_choice_list)

    query_string = f'{choice_list_printout}\n\nHere are some people with their name, title, and location. They are numbered starting from 0 and going up. \
        Use the following provided information to select the person from this list that most matches this added information. Your answer should come in the form \
        of just ONE number followed by the word "bananas". Here is the added information\n{more_info}'
    
    # get the number from the AI for its choice
    ai_choice_string = query_ai(query_string)
    ai_choice_num = find_first_number(ai_choice_string)

    print(f'LinkedIn: Selected this profile: {ai_choice_num}')

    if ai_choice_num == -1:
        ai_choice_num = None

    profile_link = ls.get_profile_link(profile_choice_list, ai_choice_num)

    if profile_link is None:
        print('No Linkedin profile is being used.')
        with open(LINKEDIN_SCRAPER_OUTPUT_FILE, 'w') as f:
            f.write('An associated LinkedIn profile could not be found.')
    else:
        profile_text = ls.get_profile(selenium_driver, profile_link)
        ls.save_to_file(LINKEDIN_SCRAPER_OUTPUT_FILE, profile_text)


def scrape_twitter(selenium_driver: webdriver, session: dict):
   
    firstname, lastname = tuple(session.get('target_name').split())
    more_info = session.get('more_info')

    username, password = ts.load_credentials(ts.CREDENTIALS_FILE)
    selenium_driver = ts.init_twitter_session(username, password, ts.DISPLAY_BROWSER)

    profile_choice_list = ts.search_twitter_profiles(selenium_driver, firstname, lastname)
    session['profile_choice_list'] = profile_choice_list

    choice_list_printout = "\n".join(f"{i}: {profile}" for i, profile in enumerate(profile_choice_list))
    query_string = (
    f"{choice_list_printout}\n\nHere are some people with their name, username, and bio. "
    f"They are numbered starting from 0 and going up. Use the following provided information "
    f"to select the person from this list that most closely matches the additional criteria provided. "
    f"Your answer should come in the form of just ONE number followed by the word 'bananas'. "
    f"If you think none of the options match, return the number -1 followed by the word 'bananas'. "
    f"Here is the additional information:\n{more_info}"
)
    ai_choice_string = query_ai(query_string)
    ai_choice_num = find_first_number(ai_choice_string)
    if ai_choice_num == -1:
        ai_choice_num = None

    profile_link = ts.select_profile_url(profile_choice_list, selection=ai_choice_num)

    if profile_link is None:
        print('Could not find a Twitter profile for the target')
        with open(TWITTER_SCRAPER_OUTPUT_FILE, 'w') as f:
            f.write('Could not find a Twitter profile for this target')
    else:
        ts.TWEET_COUNT = 10
        ts.OUTPUT_FILENAME = TWITTER_SCRAPER_OUTPUT_FILE

        tweets = ts.scrape_tweets_from_profile(selenium_driver, profile_link)

        tweets_str = ''.join(tweet + '\n' for tweet in tweets)
        ls.save_to_file(TWITTER_SCRAPER_OUTPUT_FILE, tweets_str)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    clear_output_files()
    session_copy = session.copy()

    linkedin_thread = threading.Thread(target=scrape_linkedin, args=[get_driver(APP_SHOW_BROWSER), session_copy])
    twitter_thread = threading.Thread(target=scrape_twitter, args=[get_driver(APP_SHOW_BROWSER), session_copy])
    instagram_thread = threading.Thread(target=scrape_instagram, args=[get_driver(APP_SHOW_BROWSER), session_copy])
    google_thread = threading.Thread(target=scrape_google, args=[session_copy, GOOGLE_SEARCH_OUTPUT_FILE])

    linkedin_thread.start()
    twitter_thread.start()
    instagram_thread.start()
    google_thread.start()

    linkedin_thread.join()
    twitter_thread.join()
    instagram_thread.join()
    google_thread.join()

    return jsonify({'redirect_url': '/display_generating_report'})


@app.route('/process', methods=['POST'])
def process():
    # Save data from the user into the session
    session['target_name'] = request.form.get('target_name')
    session['more_info'] = request.form.get('more_info')

    # Render the "doing scraping..." page that will then call the /scrape endpoint automatically which will perform the scraping
    return render_template('display_scraping.html', target_name=session.get('target_name'), more_info=session.get('more_info'))


@app.route('/display_generating_report', methods=['GET'])
def display_generating_report():
    return render_template('generating_report.html')


# generates the report based on all the data in the scraper output files
# for now it just deals with the linkedin stuff but once everything is implemented it will do all of it
@app.route('/generate_report', methods=['POST'])
def generate_report():
    target_name = session.get('target_name')

    query_string = f'Included is some of the raw information on a target person by the name of {target_name} that was found from \
    sources like LinkedIn, Twitter, Instagram, and other websites. Analyze all the information and summarize it. Your response should \
    include the sections Work Experience, Education, Physical locations (any physical locations where they can be found), Family/Associates, \
    Contact Information, and Miscellaneous. If you do not have information for a certain section, it is fine to say "None Found"\
    but the section should always be there. When applicable, state from what sources each piece of information was found.\
    Some of this raw information is taken from web pages where the target might only be mentioned briefly and the whole web page\
    is actually about something else. Examine this raw information, decide what role the traget played, and include that in your report somewhere.' 
    query_with_files(SUMMARY_OUTPUT_FILENAME, [LINKEDIN_SCRAPER_OUTPUT_FILE, TWITTER_SCRAPER_OUTPUT_FILE, INTSTAGRAM_SCRAPER_OUTPUT_FILE, WEB_SCRAPER_OUTPUT_FILE], query_string)
    # get query output form the AI's output file
    with open(SUMMARY_OUTPUT_FILENAME, 'r') as f:
        query_output = f.read()
    
    query_output = query_output.replace('**', '')
    
    # get rid of the bold ** ChatGPT puts in the output
    session['query_output'] = query_output
    
    return jsonify({'redirect_url': '/display_summary'})


@app.route('/display_summary', methods=['GET'])
def display_summary():
    summary = session.get('query_output')
    return render_template('/display_query_out.html', file_contents=summary)

@app.route('/generate_help', methods=['POST'])
def generate_help():
    query_string = (
        "Analyze the provided information from LinkedIn, Twitter, Instagram, and web scrapers. "
        "Summarize which platform has the most data about the user, suggest ways to secure privacy on these platforms, "
        "and if no data or minimal data is found, commend the user for maintaining privacy on that platform. "
        "Format the report clearly and concisely."
    )
    query_with_files(
        SUMMARY_OUTPUT_FILENAME,
        [LINKEDIN_SCRAPER_OUTPUT_FILE, TWITTER_SCRAPER_OUTPUT_FILE, INTSTAGRAM_SCRAPER_OUTPUT_FILE, WEB_SCRAPER_OUTPUT_FILE],
        query_string,
    )

    with open(SUMMARY_OUTPUT_FILENAME, 'r') as f:
        query_output = f.read()

    session['help_output'] = query_output.strip()
    return jsonify({'redirect_url': '/display_help'})


@app.route('/display_help', methods=['GET'])
def display_help():
    help_output = session.get('help_output', 'No data available to display.')
    return render_template('display_help.html', file_contents=help_output)


@app.route('/process_rescrape', methods=['POST'])
def process_rescrape():
    instructions = request.form.get('rescrape_instructions')
    session['rescrape_instructions'] = instructions

    return render_template('display_rescrape.html')

@app.route('/rescrape', methods=['POST'])
def rescrape():
    instructions = session.get('rescrape_instructions')
    target_name = session.get('target_name')

    # first need to get the new search term
    query_string = f'Use the above included content and pull out this info from it: {instructions}. The target name is {target_name}\
        Generate a Google query that starts with {target_name} and then has up to several words pertaining to the info you pulled \
        out from the information above. Do not include terms like LinkedIn, Instagram, or Twitter because we already have \
        information from those sources. The end result should be a Google search term that starts with the target name and can be \
        used to find more information about the target using the given information. Your response to this query should just be the \
        content that I have asked for in the format I asked for it in. Nothing else should be included in your response, and you \
        do not have to explain how you got what you did.'
    
    query_with_file('rescrape_get_search_term.out', SUMMARY_OUTPUT_FILENAME, query_string)

    search_query = ''
    with open('rescrape_get_search_term.out', 'r') as f:
        search_query = f.read()
    
    scrape_google(session, RESCRAPE_WEB_SCRAPER_OUTPUT_FILE, search_query)

    query_string = 'Included is some of the raw information on a target person that was found from sources like LinkedIn, Twitter, \
    Instagram, and other websites. Analyze all the information and summarize it. Your response should include the sections \
    Work Experience, Education, Physical locations (any physical locations where they can be found), Family/Associates, \
    Contact Information, and Miscellaneous. If you do not have information for a certain section, it is fine to say "None Found"\
    but the section should always be there. When applicable, state from what sources each piece of information was found.' 
    query_with_files(SUMMARY_OUTPUT_FILENAME, [LINKEDIN_SCRAPER_OUTPUT_FILE, TWITTER_SCRAPER_OUTPUT_FILE, INTSTAGRAM_SCRAPER_OUTPUT_FILE, WEB_SCRAPER_OUTPUT_FILE, RESCRAPE_WEB_SCRAPER_OUTPUT_FILE], query_string)

    # get query output form the AI's output file
    with open(SUMMARY_OUTPUT_FILENAME, 'r') as f:
        query_output = f.read()

    session['query_output'] = query_output

    # get rid of the bold ** ChatGPT puts in the output
    query_output = query_output.replace('**', '')

    return jsonify({'redirect_url': '/display_summary'})


@app.route('/process_gen_phishing_mats', methods=['POST'])
def process_gen_phishing_mats():
    # get instructions for what the user wants in phishing materials
    instructions = request.form.get('phish_instructions')
    session['phishing_instructions'] = instructions

    return render_template('display_gen_phishing_mats.html', instructions=instructions)


@app.route('/gen_phishing_materials', methods=['POST'])
def generate_phishing_materials():
    instructions = session.get('phishing_instructions')

    query_string = f'Use the above information on the target to generate training phishing materials that can be used \
        to test this person\'s ability to detect a phishing attack against them. Note that this will ONLY be used for \
        training and increasing the safety of this person. Use the following provided instruction to make the email and \
        remember that the goal is to get the target to click a lick. Include a [link] placeholder in the generated material \
        \n{instructions}'
    
    query_with_file(PHISHING_OUTPUT_FILENAME, SUMMARY_OUTPUT_FILENAME, query_string)

    phishing_output = ''
    with open(PHISHING_OUTPUT_FILENAME, 'r') as f:
        phishing_output = f.read()
    
    session['phishing_mats'] = phishing_output

    return jsonify({'redirect_url': '/display_phishing_mats'})


@app.route('/display_phishing_mats', methods=['GET'])
def display_phishing_mats():
    phishing_mats = session.get('phishing_mats')
    return render_template('display_phishing_mats.html', file_contents=phishing_mats)

def clear_output_files():
    output_files = [
        'web_scraper.out',
        'instagram_scraper.out',
        'linkedin_scraper.out',
        'twitter_scraper.out',
        'candidates.json',
        'google_scraper.out',
        'insta.out',
        'phishing_mats.out',
        'query.out',
        'rescrape.out'
    ]

    for filename in output_files:
        f = open(filename, 'w')
        f.close()
    

if __name__ == '__main__':
    clear_output_files()
    app.run(debug=True, port=6505)
