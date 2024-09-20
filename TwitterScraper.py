import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_twitter(username, tweet_count=10):
    # Initialize the Playwright browser
    async with async_playwright() as p:
        # Launch a browser instance
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to the Twitter user's timeline page
        url = f"https://x.com/{username}"
        await page.goto(url)

        # Wait for the page to load the tweets
        await page.wait_for_selector('article', timeout=10000)

        # Scroll down to load more tweets, if necessary
        for _ in range(5):  # Adjust this to scroll and load more tweets
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(2000)  # Wait for more tweets to load

        # Extract tweets from the page
        tweets = await page.query_selector_all('article')
        print(tweets)

        # List to store tweet data
        tweet_data = []

        # Loop through and collect the tweet text
        for i, tweet in enumerate(tweets):
            if i >= tweet_count:
                break
            # Extract tweet text
            tweet_text = await tweet.inner_text()
            tweet_data.append(tweet_text)

        # Print the collected tweets to the CLI
        for i, tweet in enumerate(tweet_data, 1):
            print(f"Tweet {i}:\n{tweet}\n{'-' * 40}")

        # Close the browser
        await browser.close()

# Updated function to export tweets to a JSON file
async def scrape_twitter_to_json(username, tweet_count=10, output_file="tweets.json"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to the Twitter user's timeline page
        url = f"https://x.com/{username}"
        await page.goto(url)

        # Wait for the page to load the tweets
        await page.wait_for_selector('article', timeout=10000)

        # Scroll down to load more tweets, if necessary
        for _ in range(5):  # Adjust this to scroll and load more tweets
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(2000)  # Wait for more tweets to load

        # Extract tweets from the page
        tweets = await page.query_selector_all('article')

        # List to store tweet data
        tweet_data = []

        # Loop through and collect the tweet text
        for i, tweet in enumerate(tweets):
            if i >= tweet_count:
                break
            # Extract tweet text
            tweet_text = await tweet.inner_text()
            tweet_data.append({"tweet_number": i + 1, "content": tweet_text})

        # Export the collected tweets to a JSON file
        with open(output_file, "w") as f:
            json.dump(tweet_data, f, indent=4)

        # Close the browser
        await browser.close()

# Entry point to run the script
if __name__ == "__main__":
    username = "elonmusk"
    tweet_count = 10

    # asyncio.run(scrape_twitter(username, tweet_count))
    asyncio.run(scrape_twitter_to_json(username, tweet_count, "tweets.json"))
