import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import subprocess
import logging
import os
import anthropic
import re
import threading
import shutil
import winreg  # Only for Windows systems
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Initialize logging
logging.basicConfig(filename='ai_commands.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set your Anthropic API key
anthropic.api_key = 'YOUR_ANTHROPIC_API_KEY'

def list_available_commands():
    available_commands = set()

    # Search in PATH directories
    path_dirs = os.getenv("PATH").split(os.pathsep)
    for directory in path_dirs:
        available_commands.update(find_executables(directory))

    # Search in common directories
    common_dirs = [
        "/usr/bin",  # Common directory on Unix-like systems
        "/usr/local/bin",  # Common directory on Unix-like systems
        "/opt",  # Common directory on Unix-like systems
        os.path.join(os.path.expanduser("~"), "bin"),  # User's bin directory
    ]

    # Add Windows-specific directories (if running on Windows)
    if os.name == "nt":
        common_dirs.extend(get_windows_program_dirs())

    for directory in common_dirs:
        available_commands.update(find_executables(directory))

    return available_commands

def find_executables(directory):
    executables = set()
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                executables.add(item)
    except (FileNotFoundError, PermissionError):
        pass
    return executables

def get_windows_program_dirs():
    program_dirs = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion", 0, winreg.KEY_READ) as key:
            program_dir_value, _ = winreg.QueryValueEx(key, "ProgramFilesDir")
            program_dirs.append(program_dir_value)

            program_dir_x86_value, _ = winreg.QueryValueEx(key, "ProgramFilesDir (x86)")
            program_dirs.append(program_dir_x86_value)
    except FileNotFoundError:
        pass
    return program_dirs

def retrieve_documents(directory):
    documents = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.txt', '.pdf', '.docx')):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                documents.append({'path': file_path, 'content': content})
    return documents

def rank_documents(prompt, documents):
    vectorizer = TfidfVectorizer()
    prompt_vector = vectorizer.fit_transform([prompt])
    document_vectors = vectorizer.transform([doc['content'] for doc in documents])
    similarities = cosine_similarity(prompt_vector, document_vectors).flatten()
    ranked_documents = sorted([(doc, sim) for doc, sim in zip(documents, similarities)], key=lambda x: x[1], reverse=True)
    return ranked_documents

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

def generate_follow_up_with_chat_model(prompt, available_commands, document_directory):
    command_list = ', '.join(sorted(available_commands))
    prompt_text = f"{prompt}. Available commands include: {command_list}."
    try:
        documents = retrieve_documents(document_directory)
        ranked_documents = rank_documents(prompt, documents)
        relevant_documents = [doc['content'] for doc, sim in ranked_documents[:5]]  # Consider top 5 relevant documents
        context = '\n'.join(relevant_documents)
        client = anthropic.Client(anthropic.api_key)
        response = client.completion(
            prompt=prompt_text + '\n\nRelevant Documents:\n' + context,
            model="claude-v1",
            max_tokens_to_sample=1000,
            stop_sequences=[],
            headers={"X-InstructionPrompt": "You are an AI trained to generate safe and useful bash commands based on available tools, the user's prompt, and relevant documents. Your responses should be properly crafted programs and nothing else. Omit any explanations, respond only in executable code."}
        )
        return response.completion
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""

class AITerminalGUI:
    def __init__(self, master):
        self.master = master
        master.title("Terminal Cancer")
        master.configure(bg='black')
        self.document_directory = None
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
        self.select_directory_button = tk.Button(self.master, text="Select Document Directory", command=self.select_directory, bg='light gray')
        self.select_directory_button.pack()

    def select_directory(self):
        self.document_directory = filedialog.askdirectory()

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
        if self.document_directory:
            available_commands = list_available_commands()
            follow_up_response = generate_follow_up_with_chat_model(prompt, available_commands, self.document_directory)
            self.ai_response_text.insert(tk.END, follow_up_response)
        else:
            self.ai_response_text.insert(tk.END, "Please select a document directory first.")

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
