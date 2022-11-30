from datetime import datetime
from cursor_FSS import file_save

class Logger:
    
    def __init__(self, module_type):
        self.tasks = {}
        self.time_start = datetime.now()
        self.module_type = module_type

    def save_log(self, results, module):
        for filename, data in results.items():
            file_save('logs', filename, data, module)

    def log(self, message, module=None, results=None, end=False):
        if message and message not in self.tasks.values():
            message = f"{datetime.now()}: {message}"
            self.tasks[datetime.now()] = message
            print(message, end="\r", flush=True) if end else print(message)
            if module and results:
                self.save_log(results, module)
    
    def end(self):
        self.log(f'>>> ALL DONE (TOTAL RUNTIME {datetime.now()-self.start})')