import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import os
import threading
import json
from datetime import datetime
from urllib.parse import urlparse

IGNORED_EXTENSIONS = {'.zip', '.svg', '.jpg', '.jpeg', '.png', '.gif'}

class GitHubRepoFetcherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub Repository Fetcher")
        self.root.geometry("600x700")
        self.history_file = "repo_history.json"
        self.max_history = 10
        
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(main_frame, text="GitHub Token (optional):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.token_var = tk.StringVar()
        self.token_entry = ttk.Entry(main_frame, textvariable=self.token_var, width=50, show='*')
        self.token_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(main_frame, text="Repository URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar()
        self.url_combo = ttk.Combobox(main_frame, textvariable=self.url_var, width=47)
        self.url_combo.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.load_history()
        
        ttk.Label(main_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar(value="downloaded_files")
        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_var, width=50)
        self.output_entry.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate', variable=self.progress_var)
        self.progress.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.log_text = scrolledtext.ScrolledText(main_frame, width=60, height=20)
        self.log_text.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.download_btn = ttk.Button(main_frame, text="Download Files", command=self.start_download)
        self.download_btn.grid(row=5, column=0, columnspan=3, pady=10)
        
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                self.url_combo['values'] = history
        except Exception:
            self.url_combo['values'] = []

    def save_history(self, url):
        try:
            history = list(self.url_combo['values'])
            if url in history:
                history.remove(url)
            history.insert(0, url)
            history = history[:self.max_history]
            with open(self.history_file, 'w') as f:
                json.dump(history, f)
            self.url_combo['values'] = history
        except Exception as e:
            self.log_message(f"Error saving history: {str(e)}")

    def parse_github_url(self, url):
        url = url.strip().rstrip('.git')
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) < 2:
                raise ValueError("Invalid GitHub URL format")
            return path_parts[0], path_parts[1]
        except Exception:
            raise ValueError("Invalid GitHub URL format")

    def should_download_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        return ext not in IGNORED_EXTENSIONS

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def download_repository(self):
        try:
            token = self.token_var.get().strip()
            url = self.url_var.get().strip()
            output_dir = self.output_var.get().strip()
            
            self.save_history(url)
            owner, repo = self.parse_github_url(url)
            self.log_message(f"Parsed repository: {owner}/{repo}")
            
            headers = {'Authorization': f'token {token}'} if token else {}
            self.log_message(f"Starting download of {owner}/{repo}")
            os.makedirs(output_dir, exist_ok=True)
            
            def get_files(path=''):
                url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                contents = response.json()
                
                if not isinstance(contents, list):
                    contents = [contents]
                
                files = []
                for item in contents:
                    if item['type'] == 'file' and self.should_download_file(item['path']):
                        files.append(item)
                    elif item['type'] == 'dir':
                        try:
                            files.extend(get_files(item['path']))
                        except Exception as e:
                            self.log_message(f"Error accessing directory {item['path']}: {str(e)}")
                return files
            
            try:
                files = get_files()
                total_files = len(files)
                self.log_message(f"Found {total_files} files to download")

                for i, item in enumerate(files, 1):
                    try:
                        response = requests.get(item['download_url'], headers=headers)
                        response.raise_for_status()
                        
                        file_name = os.path.basename(item['path'])
                        file_path = os.path.join(output_dir, file_name)
                        
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        
                        progress = (i / total_files) * 100
                        self.progress_var.set(progress)
                        
                        self.log_message(f"Downloaded ({i}/{total_files}): {item['path']}")
                        
                    except Exception as e:
                        self.log_message(f"Error downloading {item['path']}: {str(e)}")
                
            except Exception as e:
                self.log_message(f"Error fetching repository contents: {str(e)}")
                return
            
            self.log_message("Download completed successfully!")
            messagebox.showinfo("Success", "Files downloaded successfully!")
            
        except Exception as e:
            error_message = str(e)
            self.log_message(f"Error: {error_message}")
            messagebox.showerror("Error", error_message)
        
        finally:
            self.download_btn.config(state='normal')
            self.progress_var.set(0)

    def start_download(self):
        self.download_btn.config(state='disabled')
        self.log_text.delete(1.0, tk.END)
        thread = threading.Thread(target=self.download_repository)
        thread.daemon = True
        thread.start()

def main():
    root = tk.Tk()
    app = GitHubRepoFetcherGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()