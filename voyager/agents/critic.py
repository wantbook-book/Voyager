from voyager.prompts import load_prompt
from voyager.utils.json_utils import fix_and_parse_json
# from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
import os
from typing import Union
from voyager.utils.logger import Timer
class CriticAgent:
    def __init__(
        self,
        model_name="gpt-3.5-turbo",
        temperature=0,
        request_timout=120,
        mode="auto",
        system_prompt_cut_to=1800
    ):
        self.system_prompt_cut_to = system_prompt_cut_to
        # self.llm = ChatOpenAI(
        #     model_name=model_name,
        #     temperature=temperature,
        #     request_timeout=request_timout,
        # )
        self.llm = AzureChatOpenAI(
            # model_name=model_name,
            azure_endpoint=os.environ["AZURE_MODEL_ENDPOINT"],
            azure_deployment=model_name,
            openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            temperature=temperature,
            request_timeout=request_timout,
        )
        assert mode in ["auto", "manual"]
        self.mode = mode

    def render_system_message(self):
        system_message = SystemMessage(content=load_prompt("critic"))
        content_split = system_message.content.split()
        content_split_len = len(content_split)
        # TODO: 2000大概值，这样肯定效果会很不好
        if content_split_len > self.system_prompt_cut_to:
            system_message.content = ' '.join(content_split[content_split_len-self.system_prompt_cut_to:])
        return system_message

    # def render_human_message(self, *, events, task, context, chest_observation):
    #     assert events[-1][0] == "observe", "Last event must be observe"
    #     biome = events[-1][1]["status"]["biome"]
    #     time_of_day = events[-1][1]["status"]["timeOfDay"]
    #     voxels = events[-1][1]["voxels"]
    #     health = events[-1][1]["status"]["health"]
    #     hunger = events[-1][1]["status"]["food"]
    #     position = events[-1][1]["status"]["position"]
    #     equipment = events[-1][1]["status"]["equipment"]
    #     inventory_used = events[-1][1]["status"]["inventoryUsed"]
    #     inventory = events[-1][1]["inventory"]

    #     for i, (event_type, event) in enumerate(events):
    #         if event_type == "onError":
    #             print(f"\033[31mCritic Agent: Error occurs {event['onError']}\033[0m")
    #             return None

    #     observation = ""

    #     observation += f"Biome: {biome}\n\n"

    #     observation += f"Time: {time_of_day}\n\n"

    #     if voxels:
    #         observation += f"Nearby blocks: {', '.join(voxels)}\n\n"
    #     else:
    #         observation += f"Nearby blocks: None\n\n"

    #     observation += f"Health: {health:.1f}/20\n\n"
    #     observation += f"Hunger: {hunger:.1f}/20\n\n"

    #     observation += f"Position: x={position['x']:.1f}, y={position['y']:.1f}, z={position['z']:.1f}\n\n"

    #     observation += f"Equipment: {equipment}\n\n"

    #     if inventory:
    #         observation += f"Inventory ({inventory_used}/36): {inventory}\n\n"
    #     else:
    #         observation += f"Inventory ({inventory_used}/36): Empty\n\n"

    #     observation += chest_observation

    #     observation += f"Task: {task}\n\n"

    #     if context:
    #         observation += f"Context: {context}\n\n"
    #     else:
    #         observation += f"Context: None\n\n"

    #     print(f"\033[31m****Critic Agent human message****\n{observation}\033[0m")
    #     return HumanMessage(content=observation)
    
    def render_human_message(self, *, events, task, context, chest_observation):
        assert events[-1][0] == "observe", "Last event must be observe"
        biome = events[-1][1]["status"]["biome"]
        time_of_day = events[-1][1]["status"]["timeOfDay"]
        voxels = events[-1][1]["voxels"]
        health = events[-1][1]["status"]["health"]
        hunger = events[-1][1]["status"]["food"]
        position = events[-1][1]["status"]["position"]
        equipment = events[-1][1]["status"]["equipment"]
        inventory_used = events[-1][1]["status"]["inventoryUsed"]
        inventory = events[-1][1]["inventory"]

        for i, (event_type, event) in enumerate(events):
            if event_type == "onError":
                print(f"\033[31mCritic Agent: Error occurs {event['onError']}\033[0m")
                return None

        observation = ""

        # observation += f"Biome: {biome}\n\n"

        # observation += f"Time: {time_of_day}\n\n"

        if voxels:
            observation += f"Nearby blocks: {', '.join(voxels)}\n\n"
        else:
            observation += f"Nearby blocks: None\n\n"

        # observation += f"Health: {health:.1f}/20\n\n"
        # observation += f"Hunger: {hunger:.1f}/20\n\n"

        # observation += f"Position: x={position['x']:.1f}, y={position['y']:.1f}, z={position['z']:.1f}\n\n"
        observation += f"Task: {task}\n\n"
        observation += chest_observation

        observation += f"Equipment: {equipment}\n\n"

        if inventory:
            observation += f"Current Inventory ({inventory_used}/36): {inventory}\n\n"
        else:
            observation += f"Current Inventory ({inventory_used}/36): Empty\n\n"

        observation += f"Last inventory ({self.last_inventory_used}/36): {self.last_inventory}\n"

        self.last_inventory_used = inventory_used
        self.last_inventory = inventory

        chatlog = None
        for event_type, event in events:
            if event_type == 'onChat':
                chatlog = event['onChat']
                
        if chatlog:
            observation += f"Chat log: {chatlog}"
    
        # if context:
        #     observation += f"Context: {context}\n\n"
        # else:
        #     observation += f"Context: None\n\n"

        return HumanMessage(content=observation)
    def human_check_task_success(self):
        confirmed = False
        success = False
        critique = ""
        while not confirmed:
            success = input("Success? (y/n)")
            success = success.lower() == "y"
            critique = input("Enter your critique:")
            print(f"Success: {success}\nCritique: {critique}")
            confirmed = input("Confirm? (y/n)") in ["y", ""]
        return success, critique

    def ai_check_task_success(self, messages, max_retries=5):
        if max_retries == 0:
            print(
                "\033[31mFailed to parse Critic Agent response. Consider updating your prompt.\033[0m"
            )
            return False, ""

        if messages[1] is None:
            return False, ""

        critic = self.llm(messages).content
        # print(f"\033[31m****Critic Agent ai message****\n{critic}\033[0m")
        try:
            response = fix_and_parse_json(critic)
            assert response["success"] in [True, False]
            if "critique" not in response:
                response["critique"] = ""
            return response["success"], response["critique"]
        except Exception as e:
            print(f"\033[31mError parsing critic response: {e} Trying again!\033[0m")
            return self.ai_check_task_success(
                messages=messages,
                max_retries=max_retries - 1,
            )

    # def check_task_success(
    #     self, *, events, task, context, chest_observation, max_retries=5
    # ):
    #     res = self.render_human_message(
    #         events=events,
    #         task=task, 
    #         context=context,
    #         chest_observation=chest_observation,
    #     )
    #     if res is None:
    #         human_message = None
    #         result = 'failed'
    #     else:
    #         human_message, result = res

    #     messages = [
    #         self.render_system_message(),
    #         human_message,
    #     ]

    #     if self.mode == "manual":
    #         return self.human_check_task_success()
    #     elif self.mode == "auto":
    #         # return self.ai_check_task_success(
    #         #     messages=messages, max_retries=max_retries
    #         # )
    #         if "won" in result:
    #             health = events[-1][1]["status"]["health"]
    #             critique = "You should streamline the task plan. For example, **reduce the quantity or quality** of crafting equipment in last task list to reduce time of collecting items."
    #         else:
    #         # elif "lost" in result:
    #             health = 0
    #             critique = "You need to improve the task plan. For example, **improve the quantity or quality** of crafting equipment in last task list to win the combat."
    #         return health, critique, result, events[-1][1]["status"]["equipment"]
    #     else:
    #         raise ValueError(f"Invalid critic agent mode: {self.mode}")
        
    def check_task_success(
        self, *, events, task, context, chest_observation, max_retries=5
    ):
        
        with Timer('Check Task Success render_human_message'):
            human_message = self.render_human_message(
                events=events,
                task=task,
                context=context,
                chest_observation=chest_observation,
            )
            print(f'\033[35mhuman message: {human_message}\033[0m')

        messages = [
            self.render_system_message(),
            human_message,
        ]

        if self.mode == "manual":
            return self.human_check_task_success()
        elif self.mode == "auto":
            return self.ai_check_task_success(
                messages=messages, max_retries=max_retries
            )
        # elif self.mode == 'pragram':
        #     return self.program_check_task_success(
        #         events=events, task=task
        #     )
        else:
            raise ValueError(f"Invalid critic agent mode: {self.mode}")

    def check_subgoal_success(self, events, task)->bool:
        inventory = self.get_inventory(events=events)
        if task == 'craft crafting table':
            return 'crafting_table' in inventory
        if task == 'craft wooden pickaxe':
            return 'wooden_pickaxe' in inventory
        if task == 'craft stone pickaxe':
            return 'stone_pickaxe' in inventory
        if task == 'craft iron pickaxe':
            return 'iron_pickaxe' in inventory
        if task == 'mine diamond':
            return 'diamond' in inventory