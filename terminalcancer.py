import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
import threading
import subprocess
import re
import platform
import logging
import os
import openai  # Ensure you have the openai library installed

# Initialize logging
logging.basicConfig(filename='ai_commands.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Replace with your actual OpenAI API key
openai.api_key = 'YOUR_API_KEY_HERE'

def extract_command(generated_text):
    pattern = r"```(.*?)```"
    match = re.search(pattern, generated_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return generated_text

def log_command(command, output):
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
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-0613",  # Update as necessary
            messages=[
                {"role": "system", "content": "You are terminal-cancer running on macOS and you help users control their computer through writing bash programs. Your responses should be a properly created bash program and nothing else. refrain from explanations."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": follow_up},
            ]
        )
        return response.choices[0].message['content']
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""

# GUI Class
class AITerminalGUI:
    def __init__(self, master):
        self.master = master
        master.title("AI Terminal")

        # Prompt input
        self.prompt_label = tk.Label(master, text="Enter your prompt:")
        self.prompt_label.pack()
        self.prompt_entry = tk.Entry(master, width=50)
        self.prompt_entry.pack()

        # Button to execute
        self.execute_button = tk.Button(master, text="Execute", command=self.execute)
        self.execute_button.pack()

        # AI-generated command/response display
        self.ai_response_label = tk.Label(master, text="AI Generated Command or Response:")
        self.ai_response_label.pack()
        self.ai_response_text = scrolledtext.ScrolledText(master, height=5)
        self.ai_response_text.pack()

        # Command output display
        self.command_output_label = tk.Label(master, text="Command Output:")
        self.command_output_label.pack()
        self.command_output_text = scrolledtext.ScrolledText(master, height=10)
        self.command_output_text.pack()

    def execute(self):
        prompt = self.prompt_entry.get()
        if prompt.lower() == 'exit':
            self.master.quit()
        else:
            self.ai_response_text.delete('1.0', tk.END)  # Clear previous content
            self.command_output_text.delete('1.0', tk.END)  # Clear previous content

            threading.Thread(target=self.process_prompt, args=(prompt,)).start()

    def process_prompt(self, prompt):
        follow_up_response = generate_follow_up_with_chat_model(prompt, "")
        self.ai_response_text.insert(tk.END, follow_up_response)

        if follow_up_response.strip() and not follow_up_response.startswith("Hello"):
            command_output, success = execute_shell_command(follow_up_response)
            self.command_output_text.insert(tk.END, command_output)
            log_command(follow_up_response, command_output)
        else:
            self.command_output_text.insert(tk.END, "AI Response: " + follow_up_response)

def main():
    root = tk.Tk()
    gui = AITerminalGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

