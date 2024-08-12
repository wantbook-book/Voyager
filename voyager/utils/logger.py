import time
class Timer:
    def __init__(self, description):
        self.description = description
    
    def __enter__(self):
        self.start = time.time()
        print('')
        print("\033[33m"+'='*15+f"{self.description} starts."+'='*15+"\033[0m")
        # f"\033[33mRender Action Agent system message with {len(skills)} skills\033[0m"
        return self
    
    def __exit__(self, type, value, traceback):
        self.end = time.time()
        # self.logger.info('='*10+f"{self.description} ends. Cost {self.end - self.start} seconds"+'='*10)
        print("\033[33m"+'='*15+f"{self.description} ends. Cost {self.end - self.start} seconds"+'='*15+"\033[0m")
        print('')