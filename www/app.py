from flask import Flask, render_template, request, session, jsonify
from flask_session import Session
from linkedin_scraper import *
from linkedin_scraper import OUTPUT_FILENAME as SCRAPER_OUT
import twitter_scraper as ts
from query_ai import *
from query_ai import OUTPUT_FILENAME as AI_OUT
from query_ai import query as query_ai
from instascraper import *
from instascraper import OUTPUT_FILENAME as INSTAGRAM_OUT
from instascraper import query as instaquery
import re

APP_SHOW_BROWSER = True
LINKEDIN_SCRAPER_OUTPUT_FILE = 'linkedin_scraper.out'
TWITTER_SCRAPER_OUTPUT_FILE = 'twitter_scraper.out'

# for maintaining persistant selenium driver
selenium_driver = None

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# finds the first number in a string and returns it
# used for extracting a number answer from ChatGPT
def find_first_number(string: str):
    # Find all groups of digits in the string
    match = re.search(r'\d+', string)
    if match:
        # Return the first match as an integer
        return int(match.group())
    else:
        # Return None if no number is found
        return None


def scrape_instagram():
    # Get user input CHANGE THIS
    username, password = get_username(CONF_FILENAME)
    usernames = tuple(session.get('target_name').split()) + session.get('more_info')
    num_posts = 10
    
    # Set up the WebDriver CHANGE THIS
    global selenium_driver

    try:
        selenium_driver.get(f"https://www.google.com/search?q={usernames}+instagram")
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
        # print(usernames2)
        # Log into Instagram
        login_to_instagram(selenium_driver, username, password)
        canidates = []

        for username in usernames2:
            profiledata = scrape_user_profile(selenium_driver, username, 1)
            canidates.append(profiledata)
        
        canidates.append(usernames)

        with open("candidates.json", "w", encoding="utf-8") as f:
            json.dump(canidates, f, indent=2, ensure_ascii=False)
            
            

        instaquery("candidates.json", 2)
        with open('insta.out', 'r') as file:
            contents = file.read()
            print(contents)

        result = re.search(r'\d+', contents)

        awesomenumber = result.group()
        usernames_input = canidates[int(awesomenumber) - 1]['username']
        print(usernames_input)
        usernames = [username.strip() for username in usernames_input.split(',')]
        # Scrape profiles
        all_profiles = []
        for username in usernames:
            print(f"Scraping profile: {username}")
            profile_data = scrape_user_profile(selenium_driver, username, num_posts)
            all_profiles.append(profile_data)

        # Save to JSON
        with open("instagram_profiles_posts.json", "w", encoding="utf-8") as f:
            json.dump(all_profiles, f, indent=2, ensure_ascii=False)

        print("Scraping complete. Data saved to instagram_profiles_posts.json")
    finally:
        print("haiii")
    


def scrape_linkedin():
    global selenium_driver
    firstname, lastname = tuple(session.get('target_name').split())
    more_info = session.get('more_info')

    username, password = get_credentials(CONF_FILENAME)
    selenium_driver = get_driver(username, password, APP_SHOW_BROWSER)
    profile_choice_list = get_profile_choice_list(selenium_driver, firstname, lastname)
    # save profile choice list to session so can be accessed later once the user makes a choice
    session['profile_choice_list'] = profile_choice_list
    
    choice_list_printout = get_string_profile_choice_list(profile_choice_list)
    query_string = f'{choice_list_printout}\n\nHere are some people with their name, title, and location. They are numbered starting from 0 and going up. \
        Use the following provided information to select the person from this list that most matches this added information. Your answer should come in the form \
        of just ONE number followed by the word "bananas". Here is the added information\n{more_info}'
    
    # get the number from the AI for its choice
    ai_choice_string = query_ai(query_string)
    ai_choice_num = find_first_number(ai_choice_string)
    

    print(choice_list_printout)
    print(ai_choice_string)

    profile_link = get_profile_link(profile_choice_list, ai_choice_num)
    profile_text = get_profile(selenium_driver, profile_link)
    save_to_file(LINKEDIN_SCRAPER_OUTPUT_FILE, profile_text)


def scrape_twitter():
    global selenium_driver
    firstname, lastname = tuple(session.get('target_name').split())
    more_info = session.get('more_info')

    username, password = ts.get_credentials(CONF_FILENAME)
    selenium_driver = ts.initialize_webdriver(username, password, APP_SHOW_BROWSER)
    profile_choice_list = ts.search_profiles(selenium_driver, firstname, lastname)
    # save profile choice list to session so can be accessed later once the user makes a choice
    session['profile_choice_list'] = profile_choice_list
    
    choice_list_printout = ts.select_profile(profile_choice_list)
    query_string = f'{choice_list_printout}\n\nHere are some people with their name, title, and location. They are numbered starting from 0 and going up. \
        Use the following provided information to select the person from this list that most matches this added information. Your answer should come in the form \
        of just ONE number followed by the word "bananas". Here is the added information\n{more_info}'
    
    # get the number from the AI for its choice
    ai_choice_string = query_ai(query_string)
    ai_choice_num = find_first_number(ai_choice_string)

    profile_link = ts.get_profile_link(profile_choice_list, ai_choice_num)
    tweets = ts.get_tweets_and_save(selenium_driver, profile_link, 10, TWITTER_SCRAPER_OUTPUT_FILE)

    tweets_str = ''
    for tweet in tweets:
        tweets_str += (tweet + '\n')

    save_to_file(TWITTER_SCRAPER_OUTPUT_FILE, tweets_str)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    # do first search for that name on LinkedIn
    # scrape_linkedin()
    scrape_twitter()

    # TODO
    # scrape_instagram()
    # scrape_google()

    return jsonify({'redirect_url': '/display_generating_report'})


@app.route('/process', methods=['POST'])
def process():
    # use global selenium driver
    global selenium_driver

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
    
    query_string = 'This is the raw data from the LinkedIn profile of a person. Summarize all the information, \
        and make sure to give specific detail on work experience, education, and interests.' 
    query_with_file(LINKEDIN_SCRAPER_OUTPUT_FILE, query_string) 
    # get query output form the AI's output for LinkedIn
    with open(AI_OUT, 'r') as f:
        linkedin_query_output = f.read()
    session['linkedin_query_output'] = linkedin_query_output

    # TODO
    # get and save output for other scrapers

    
    return jsonify({'redirect_url': '/display_summary'})


@app.route('/display_summary', methods=['GET'])
def display_summary():
    summary = session.get('linkedin_query_output')
    return render_template('/display_query_out.html', file_contents=summary)


@app.route('/linkedin_profile_choice', methods=['POST'])
def scrape_linkedin_profile():
    if (profile_choice_list := session.get('profile_choice_list')) is None:
        return render_template('something_went_wrong.html')
    else:
        # this can only be an int, right?
        profile_choice_num = int(request.form.get('profile_choice'))
        profile_link = get_profile_link(profile_choice_list, profile_choice_num)
        profile_text = get_profile(selenium_driver, profile_link)

        save_to_file('linkedin_scraper.out', profile_text)

        # probably have to change this part later, but just do it here for now
        query_string = 'This is the raw data from the LinkedIn profile of a person. Summarize all the information, and make sure to give specific detail on work experience, education, and interests.' 
        query_with_file(LINKEDIN_SCRAPER_OUTPUT_FILE, query_string)

        # we know it goes to 'query.out'
        with open(AI_OUT, 'r') as f:
            query_output = f.read()
        
        return render_template('display_query_out.html', file_contents=query_output)



if __name__ == '__main__':
    app.run(debug=True, port=5007)

    
