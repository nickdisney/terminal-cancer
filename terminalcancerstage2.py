from flask import Flask, request, render_template
import logging
from transformers import GPTJForCausalLM, AutoTokenizer
import torch
import subprocess
import shlex

app = Flask(__name__)

logging.basicConfig(filename='terminal_cancer.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TerminalCancerApp:
    def __init__(self):
        self.setup_model()

    def setup_model(self):
        model_name = "EleutherAI/gpt-j-6B"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = GPTJForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16).half().cuda()

    def model_predict(self, input_text):
        input_ids = self.tokenizer(input_text, return_tensors="pt").input_ids.cuda()
        gen_tokens = self.model.generate(input_ids, do_sample=True, temperature=0.9, max_length=100)
        gen_text = self.tokenizer.batch_decode(gen_tokens)[0]
        return gen_text

    def execute_command(self, command):
        allowed_commands = {
            "list_directory": {"cmd": "ls", "parameters": ["-l"]},
            "show_current_directory": {"cmd": "pwd"},
        }
        if command not in allowed_commands:
            return "Error: Command not allowed."
        command_info = allowed_commands[command]
        cmd = command_info["cmd"]
        cmd_params = command_info.get("parameters", [])
        safe_params = [shlex.quote(param) for param in cmd_params]
        full_command = [cmd] + safe_params
        try:
            result = subprocess.run(full_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error executing command: {e}"

    def interpret_response(self, response):
        if response.startswith("execute:"):
            command = response[len("execute:"):].strip()
            return self.execute_command(command)
        else:
            return response

terminal_cancer_app = TerminalCancerApp()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    user_input = request.form['command']
    response = terminal_cancer_app.model_predict(user_input)
    final_response = terminal_cancer_app.interpret_response(response)
    return render_template('index.html', response=final_response)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
