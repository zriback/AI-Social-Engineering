from linkedin_scraper import scrape
from query_ai import query_with_file
import sys

# main function for everything
def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} [firstname] [lastname]\n')
        exit()
    else:
        firstname = sys.argv[1]
        lastname = sys.argv[2]

    scrape(firstname, lastname)

    scraper_output_file = 'scraper.out'
    query = '''The included information is from a person's LinkedIn profile. Briefly list for me all the information including
    current and past work jobs, education background, interests, and more.
    '''
    query_with_file(scraper_output_file, query)


if __name__ == '__main__':
    main()