from openai import OpenAI
import base64

CONF_FILENAME = 'secrets.conf'

def get_apikey(filename):
    with open(filename, 'r') as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue
            if line.startswith('api_key'):
                api_key = line.split('=')[1].strip()
    return api_key


# just ask the AI a question and return the response in a string
def query(question: str):
    my_key = get_apikey(CONF_FILENAME)
    client = OpenAI(
        api_key=my_key
    )

    # Prepare the request payload
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": [
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
    
    return answer


# ask AI question with all given file contents
# output is put into OUTPUT_FILE
def query_with_files(out_filename: str, in_filenames: list['str'], question: str):
    # max size for a request
    max_request_size = 1048576 - 20000

    my_key = get_apikey(CONF_FILENAME)

    client = OpenAI(
        api_key=my_key
    )

    all_file_info = ''
    for filename in in_filenames:
        with open(filename, 'r', encoding='utf-8') as f:
            all_file_info += f.read() + '\n\n'
    
    if len(all_file_info) > max_request_size:
        all_file_info = all_file_info[:max_request_size]

    # Prepare the request payload
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Here is information from the files: {all_file_info}"},
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
    
    with open(out_filename, 'w') as f:
        f.write(answer)



# ask AI question with given file contents
# output is put into the OUTPUT_FILE 
def query_with_file(out_filename: str, in_filename: str, question: str):
    my_key = get_apikey(CONF_FILENAME)

    client = OpenAI(
        api_key=my_key
    )

    # Load and encode the content of the text file
    with open(in_filename, 'r') as f:
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
    
    with open(out_filename, 'w') as f:
        f.write(answer)


if __name__ == '__main__':
    query_string = 'This is the raw data from the LinkedIn profile of a person. Summarize all the information, and make sure to give specific detail on work experience, education, and interests.'
    query_with_file('scraper.out', query_string)