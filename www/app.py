from flask import Flask, render_template, request, session
from flask_session import Session
from linkedin_scraper import *
from linkedin_scraper import OUTPUT_FILENAME as SCRAPER_OUT
from query_ai import *
from query_ai import OUTPUT_FILENAME as AI_OUT

APP_SHOW_BROWSER = True

# for maintaining persistant selenium driver
selenium_driver = None

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def scrape():
    # use global selenium driver
    global selenium_driver

    # Get the user input from the form
    user_input = request.form.get('user_input')

    firstname = user_input.split()[0]
    lastname = user_input.split()[1]

    # do first search for that name on LinkedIn
    username, password = get_credentials(CONF_FILENAME)
    selenium_driver = get_driver(username, password, APP_SHOW_BROWSER)
    profile_choice_list = get_profile_choice_list(selenium_driver, firstname, lastname)
    # save profile choice list to session so can be accessed later once the user makes a choice
    session['profile_choice_list'] = profile_choice_list
    choice_list_printout = get_string_profile_choice_list(profile_choice_list)
    
    return render_template('linkedin_choice.html', file_contents=choice_list_printout)


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
        query_with_file('linkedin_scraper.out', query_string)

        # we know it goes to 'query.out'
        with open('query.out', 'r') as f:
            query_output = f.read()
        
        return render_template('display_query_out.html', file_contents=query_output)



if __name__ == '__main__':
    app.run(debug=True)