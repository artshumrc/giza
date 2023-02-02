from datetime import datetime
from cursor_FSS import file_save
import pytz

# TODO get rid of this, why reimplement logging
class Logger:
    
    def __init__(self, module_type):
        self.tasks = {}
        self.tz = pytz.timezone('US/Eastern')
        self.time_start = datetime.now(self.tz)
        self.module_type = module_type

    def save_log(self, results, module):
        for filename, data in results.items():
            file_save('logs', filename, data, module)

    def log(self, message, module=None, results=None, end=False):
        if message and message not in self.tasks.values():
            message = f"{datetime.now(self.tz)}: {message}"
            self.tasks[datetime.now(self.tz)] = message
            print(message, end="\r", flush=True) if end else print(message)
            if module and results:
                self.save_log(results, module)
    
    def end(self):
        self.log(f'>>> ALL DONE (TOTAL RUNTIME {datetime.now(self.tz)-self.time_start})')