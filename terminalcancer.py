import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import logging
import os
import openai  # Ensure you have the openai library installed
import re
import threading

# Initialize logging
logging.basicConfig(filename='ai_commands.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# IMPORTANT: Replace 'xxxx' with your actual OpenAI API key and ensure it's kept secure
openai.api_key = 'xxxx'

def list_available_commands():
    path_dirs = os.getenv("PATH").split(os.pathsep)
    available_commands = set()
    for directory in path_dirs:
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                    available_commands.add(item)
        except FileNotFoundError:
            continue
    return available_commands

def extract_command(generated_text):
    pattern = r"```(.*?)```"
    match = re.search(pattern, generated_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return generated_text

def log_command_with_details(prompt, command, output, success):
    logging.info(f"Prompt: {prompt}, Command executed: {command}, Success: {success}, Output: {output}")

def execute_shell_command(command):
    command = re.sub(r'^```bash|```$', '', command).strip()
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, error = process.communicate()
        success = process.returncode == 0
        return output + error, success
    except subprocess.CalledProcessError as e:
        return e.stderr, False

def generate_follow_up_with_chat_model(prompt, available_commands):
    command_list = ', '.join(sorted(available_commands))
    prompt_text = f"{prompt}. Available commands include: {command_list}."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-0613",
            messages=[
                {"role": "system", "content": "You are an AI trained to generate bash commands based on available tools. Your responses should be properly crafted programs and nothing else. Omit any explanations, respond only in executable code."},
                {"role": "user", "content": prompt_text},
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
        master.configure(bg='black')  # Set background color to black
        self.setup_gui_components()

    def setup_gui_components(self):
        self.master.configure(bg='black')
        self.prompt_label = tk.Label(self.master, text="Enter your prompt:", bg='black', fg='white')
        self.prompt_label.pack()
        self.prompt_entry = tk.Entry(self.master, width=50, bg='light gray')
        self.prompt_entry.pack()
        self.execute_button = tk.Button(self.master, text="Submit", command=self.execute, bg='light gray')
        self.execute_button.pack()
        self.ai_response_label = tk.Label(self.master, text="AI Generated Command or Response:", bg='black', fg='white')
        self.ai_response_label.pack()
        self.ai_response_text = scrolledtext.ScrolledText(self.master, height=5, bg='light gray')
        self.ai_response_text.pack()
        self.execute_approved_button = tk.Button(self.master, text="Execute Approved Command", command=self.execute_approved_command, bg='light gray')
        self.execute_approved_button.pack()
        self.command_output_label = tk.Label(self.master, text="Command Output:", bg='black', fg='white')
        self.command_output_label.pack()
        self.command_output_text = scrolledtext.ScrolledText(self.master, height=10, bg='light gray')
        self.command_output_text.pack()

    def execute(self):
        self.execute_button.config(text="Processing...", bg='yellow')
        prompt = self.prompt_entry.get()
        if prompt.lower() == 'exit':
            self.master.quit()
        else:
            self.ai_response_text.delete('1.0', tk.END)
            self.command_output_text.delete('1.0', tk.END)
            threading.Thread(target=self.process_prompt, args=(prompt,)).start()
            self.check_thread(threading.current_thread())

    def check_thread(self, thread):
        if thread.is_alive():
            self.master.after(100, lambda: self.check_thread(thread))
        else:
            self.execute_button.config(text="Submit", bg='light gray')

    def process_prompt(self, prompt):
        available_commands = list_available_commands()
        follow_up_response = generate_follow_up_with_chat_model(prompt, available_commands)
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

