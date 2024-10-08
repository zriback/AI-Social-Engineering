from openai import OpenAI
import base64

CONF_FILENAME = 'secrets.conf'
OUTPUT_FILENAME = 'query.out'

def get_apikey(filename):
    with open(filename, 'r') as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue
            if line.startswith('api_key'):
                api_key = line.split('=')[1].strip()
    return api_key


def query_with_file(filename: str, question: str):
    my_key = get_apikey(CONF_FILENAME)

    client = OpenAI(
        api_key=my_key
    )

    # Load and encode the content of the text file
    with open(filename, 'r', encoding='utf-8') as f:
        file_content = f.read()

    # Prepare the request payload
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Here is information from the file: {file_content}"},
                {"type": "text", "text": question}
            ]
        }
    ]

    # Send the request to the GPT-4o API
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7
    )

    # Print the model's response
    answer = response.choices[0].message.content
    
    with open(OUTPUT_FILENAME, 'w') as f:
        f.write(answer)


if __name__ == '__main__':
    query_string = 'This is the raw data from the LinkedIn profile of a person. Summarize all the information, and make sure to give specific detail on work experience, education, and interests.'
    query_with_file('scraper.out', query_string)