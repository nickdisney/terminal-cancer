import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import subprocess
import shlex
import logging
import os
import openai  # Ensure you have the openai library installed
import re
import platform

# Initialize logging
logging.basicConfig(filename='ai_commands.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# IMPORTANT: Reset your OpenAI API key since it was shared
openai.api_key = 'YOUR_API_KEY_HERE'

def extract_command(generated_text):
    pattern = r"```(.*?)```"
    match = re.search(pattern, generated_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return generated_text

def log_command_with_details(prompt, command, output, success):
    logging.info(f"Prompt: {prompt}, Command executed: {command}, Success: {success}, Output: {output}")

def get_desktop_path():
    if platform.system() == "Windows":
        return os.path.join(os.environ['USERPROFILE'], 'Desktop')
    else:
        return os.path.join(os.environ['HOME'], 'Desktop')

def execute_shell_command(command):
    command = re.sub(r'^```bash|```$', '', command).strip()  # Strip markdown formatting if present
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = process.communicate()
        success = process.returncode == 0
        return output + error, success
    except subprocess.CalledProcessError as e:
        return e.stderr, False

def generate_follow_up_with_chat_model(prompt, follow_up):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-0613",
            messages=[
                {"role": "system", "content": "You are terminal-cancer running on macOS and you help users control their computer through writing bash programs. Your responses should be a properly created bash program and nothing else. Refrain from explanations."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": follow_up},
            ]
        )
        return response.choices[0].message['content']
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""

class AITerminalGUI:
    def __init__(self, master):
        self.master = master
        master.title("Terminal Cancer")
        self.setup_gui_components()

    def setup_gui_components(self):
        self.prompt_label = tk.Label(self.master, text="Enter your prompt:")
        self.prompt_label.pack()
        self.prompt_entry = tk.Entry(self.master, width=50)
        self.prompt_entry.pack()
        self.execute_button = tk.Button(self.master, text="Execute", command=self.execute)
        self.execute_button.pack()
        self.ai_response_label = tk.Label(self.master, text="AI Generated Command or Response:")
        self.ai_response_label.pack()
        self.ai_response_text = scrolledtext.ScrolledText(self.master, height=5)
        self.ai_response_text.pack()
        self.command_output_label = tk.Label(self.master, text="Command Output:")
        self.command_output_label.pack()
        self.command_output_text = scrolledtext.ScrolledText(self.master, height=10)
        self.command_output_text.pack()
        self.execute_approved_button = tk.Button(self.master, text="Execute Approved Command", command=self.execute_approved_command)
        self.execute_approved_button.pack()

    def execute(self):
        prompt = self.prompt_entry.get()
        if prompt.lower() == 'exit':
            self.master.quit()
        else:
            self.ai_response_text.delete('1.0', tk.END)
            self.command_output_text.delete('1.0', tk.END)
            threading.Thread(target=self.process_prompt, args=(prompt,)).start()

    def process_prompt(self, prompt):
        follow_up_response = generate_follow_up_with_chat_model(prompt, "")
        self.ai_response_text.insert(tk.END, follow_up_response)

    def execute_approved_command(self):
        command = self.ai_response_text.get('1.0', tk.END).strip()
        command = extract_command(command)
        output, success = execute_shell_command(command)
        self.command_output_text.insert(tk.END, output)
        log_command_with_details(prompt="User approved command", command=command, output=output, success=success)
        self.request_feedback(command)

    def request_feedback(self, command):
        feedback = messagebox.askyesno("Feedback", "Did the command work as expected?")
        log_command_with_details("User feedback", command, "N/A", feedback)

def main():
    root = tk.Tk()
    gui = AITerminalGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

