import openai
import subprocess
import re
import platform
import logging
import os

# Initialize logging
logging.basicConfig(filename='ai_commands.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Replace with your actual OpenAI API key
openai.api_key = 'YOUR_API_KEY_HERE_'

def extract_command(generated_text):
    pattern = r"```(.*?)```"
    match = re.search(pattern, generated_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return generated_text

def log_command(command, output):
    """
    Logs the executed command and its output to a log file.
    """
    logging.info(f"Command executed: {command}\nOutput: {output}")

def get_desktop_path():
    if platform.system() == "Windows":
        return os.path.join(os.environ['USERPROFILE'], 'Desktop')
    else:
        return os.path.join(os.environ['HOME'], 'Desktop')

def execute_shell_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        output = result.stdout
        success = True
    except subprocess.CalledProcessError as e:
        output = e.stderr
        success = False
    return output, success

def generate_follow_up_with_chat_model(prompt, follow_up):
    """
    Generates a follow-up command or response from the AI model based on the prompt and previous output.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-0613",  # Update as necessary
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": follow_up},
            ]
        )
        return response.choices[0].message['content']
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""

def main():
    print("AI Terminal (type 'exit' to quit)")
    while True:
        prompt = input("Enter your prompt: ")
        if prompt.lower() == 'exit':
            break

        # Attempt to directly handle the action without executing a command
        if "create a blank 'helloworld.txt' file on my desktop" in prompt:
            desktop_path = get_desktop_path()
            file_path = os.path.join(desktop_path, 'helloworld.txt')
            try:
                with open(file_path, 'w') as file:
                    pass  # Just create the file
                print(f"Created blank file at: {file_path}")
                follow_up_info = f"Successfully created 'helloworld.txt' at {desktop_path}."
            except Exception as e:
                print(f"Error creating file: {e}")
                follow_up_info = "Failed to create 'helloworld.txt'."
        else:
            # Use AI to generate a command
            follow_up_response = generate_follow_up_with_chat_model(prompt, "")
            print(f"AI Generated Command or Response: {follow_up_response}")

            # Check if the response seems to be a command and not a conversational reply
            if follow_up_response.strip() and not follow_up_response.startswith("Hello"):
                command_output, success = execute_shell_command(follow_up_response)
                print("Command Output:\n", command_output)
                log_command(follow_up_response, command_output)
            else:
                print("AI Response: ", follow_up_response)

if __name__ == "__main__":
    main()

