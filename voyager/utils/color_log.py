# Description: Color log for the console output
# red error
print(f"\033[31m****Critic Agent ai message****\n{critic}\033[0m")
# green success
print(f"\033[32m****Action Agent human message****\n{human_message.content}\033[0m")
# dark green  log timer
f"\033[33mRender Action Agent system message with {len(skills)} skills\033[0m"
# blue ai message response
print(f"\033[34m****Action Agent ai message****\n{ai_message.content}\033[0m")
# purpure failed
print(f"\033[35mFailed tasks: {', '.join(self.curriculum_agent.failed_tasks)}\033[0m")
# cyan recorder message
f"\033[96m****Recorder message: {self.elapsed_time} ticks have elapsed****\033[0m\n"