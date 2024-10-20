from flask import Flask, render_template, request, session, jsonify
from flask_session import Session
from linkedin_scraper import *
from linkedin_scraper import OUTPUT_FILENAME as SCRAPER_OUT
from query_ai import *
from query_ai import OUTPUT_FILENAME as AI_OUT
import re

APP_SHOW_BROWSER = True
LINKEDIN_SCRAPER_OUTPUT_FILE = 'linkedin_scraper.out'

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
    ai_choice_string = query(query_string)
    ai_choice_num = find_first_number(ai_choice_string)

    print(choice_list_printout)
    print(ai_choice_string)

    profile_link = get_profile_link(profile_choice_list, ai_choice_num)
    profile_text = get_profile(selenium_driver, profile_link)
    save_to_file(LINKEDIN_SCRAPER_OUTPUT_FILE, profile_text)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    # do first search for that name on LinkedIn
    scrape_linkedin()

    # TODO
    # scrape_instagram()
    # scrape_twitter()
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
    # get query output form the AI's output file
    with open(AI_OUT, 'r') as f:
        query_output = f.read()

    session['query_output'] = query_output
    
    return jsonify({'redirect_url': '/display_summary'})


@app.route('/display_summary', methods=['GET'])
def display_summary():
    summary = session.get('query_output')
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
    app.run(debug=True)

    