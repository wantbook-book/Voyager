import copy
import json
import os
import time
from typing import Dict
from javascript import require
import voyager.utils as U
from .env import VoyagerEnv

from .agents import ActionAgent
from .agents import CriticAgent
from .agents import CurriculumAgent
from .agents import SkillManager
from .agents import CommentAgent
from voyager.utils.logger import Timer
import traceback
# TODO: remove event memory
class Voyager:
    def __init__(
        self,
        mc_port: int = None,
        mc_host: str = None,
        azure_login: Dict[str, str] = None,
        server_port: int = 3000,
        environment: str = None,
        openai_api_key: str = None,
        env_wait_ticks: int = 20,
        env_request_timeout: int = 600,
        max_iterations: int = 80,
        reset_placed_if_failed: bool = False,
        action_agent_model_name: str = "gpt-4",
        action_agent_temperature: float = 0,
        action_agent_task_max_retries: int = 4,
        action_agent_show_chat_log: bool = True,
        action_agent_show_execution_error: bool = True,
        curriculum_agent_model_name: str = "gpt-4",
        curriculum_agent_temperature: float = 0,
        curriculum_agent_qa_model_name: str = "gpt-3.5-turbo",
        curriculum_agent_qa_temperature: float = 0,
        curriculum_agent_warm_up: Dict[str, int] = None,
        curriculum_agent_core_inventory_items: str = r".*_log|.*_planks|stick|crafting_table|furnace"
        r"|cobblestone|dirt|coal|.*_pickaxe|.*_sword|.*_axe",
        curriculum_agent_mode: str = "auto",
        critic_agent_model_name: str = "gpt-4",
        critic_agent_temperature: float = 0,
        critic_agent_mode: str = "auto",
        comment_agent_model_name: str="gpt-3.5-turbo",
        skill_manager_model_name: str = "gpt-3.5-turbo",
        skill_manager_temperature: float = 0,
        skill_manager_retrieval_top_k: int = 5,
        openai_api_request_timeout: int = 240,
        ckpt_dir: str = "ckpt",
        skill_library_dir: str = None,
        resume: bool = False,
        username: str = "bot",
        re_embed_skill: bool = False,
        system_prompt_cut_to: int = 1800,
    ):
        """
        The main class for Voyager.
        Action agent is the iterative prompting mechanism in paper.
        Curriculum agent is the automatic curriculum in paper.
        Critic agent is the self-verification in paper.
        Skill manager is the skill library in paper.
        :param mc_port: minecraft in-game port
        :param azure_login: minecraft login config
        :param server_port: mineflayer port
        :param openai_api_key: openai api key
        :param env_wait_ticks: how many ticks at the end each step will wait, if you found some chat log missing,
        you should increase this value
        :param env_request_timeout: how many seconds to wait for each step, if the code execution exceeds this time,
        python side will terminate the connection and need to be resumed
        :param reset_placed_if_failed: whether to reset placed blocks if failed, useful for building task
        :param action_agent_model_name: action agent model name
        :param action_agent_temperature: action agent temperature
        :param action_agent_task_max_retries: how many times to retry if failed
        :param curriculum_agent_model_name: curriculum agent model name
        :param curriculum_agent_temperature: curriculum agent temperature
        :param curriculum_agent_qa_model_name: curriculum agent qa model name
        :param curriculum_agent_qa_temperature: curriculum agent qa temperature
        :param curriculum_agent_warm_up: info will show in curriculum human message
        if completed task larger than the value in dict, available keys are:
        {
            "context": int,
            "biome": int,
            "time": int,
            "other_blocks": int,
            "nearby_entities": int,
            "health": int,
            "hunger": int,
            "position": int,
            "equipment": int,
            "chests": int,
            "optional_inventory_items": int,
        }
        :param curriculum_agent_core_inventory_items: only show these items in inventory before optional_inventory_items
        reached in warm up
        :param curriculum_agent_mode: "auto" for automatic curriculum, "manual" for human curriculum
        :param critic_agent_model_name: critic agent model name
        :param critic_agent_temperature: critic agent temperature
        :param critic_agent_mode: "auto" for automatic critic ,"manual" for human critic
        :param skill_manager_model_name: skill manager model name
        :param skill_manager_temperature: skill manager temperature
        :param skill_manager_retrieval_top_k: how many skills to retrieve for each task
        :param openai_api_request_timeout: how many seconds to wait for openai api
        :param ckpt_dir: checkpoint dir
        :param skill_library_dir: skill library dir
        :param resume: whether to resume from checkpoint
        """
        # init env
        self.environment = environment
        self.username = username
        self.env = VoyagerEnv(
            mc_host=mc_host,
            mc_port=mc_port,
            azure_login=azure_login,
            server_port=server_port,
            request_timeout=env_request_timeout,
        )
        self.env_wait_ticks = env_wait_ticks
        self.reset_placed_if_failed = reset_placed_if_failed
        self.max_iterations = max_iterations

        # set openai api key
        os.environ["OPENAI_API_KEY"] = openai_api_key
        self.total_time = 0 
        self.total_iter = 0 
        self.step_time = []
        # init agents
        self.action_agent_model_name = action_agent_model_name
        self.action_agent = ActionAgent(
            model_name=action_agent_model_name,
            temperature=action_agent_temperature,
            request_timout=openai_api_request_timeout,
            ckpt_dir=ckpt_dir,
            resume=resume,
            chat_log=action_agent_show_chat_log,
            execution_error=action_agent_show_execution_error,
            system_prompt_cut_to=system_prompt_cut_to,
        )
        self.action_agent_task_max_retries = action_agent_task_max_retries
        self.curriculum_agent = CurriculumAgent(
            model_name=curriculum_agent_model_name,
            temperature=curriculum_agent_temperature,
            qa_model_name=curriculum_agent_qa_model_name,
            qa_temperature=curriculum_agent_qa_temperature,
            request_timout=openai_api_request_timeout,
            ckpt_dir=ckpt_dir,
            resume=resume,
            mode=curriculum_agent_mode,
            warm_up=curriculum_agent_warm_up,
            core_inventory_items=curriculum_agent_core_inventory_items,
            system_prompt_cut_to=system_prompt_cut_to,
        )
        self.comment_agent = CommentAgent(
            environment=environment,
            model_name=comment_agent_model_name
        )
        self.critic_agent = CriticAgent(
            model_name=critic_agent_model_name,
            temperature=critic_agent_temperature,
            request_timout=openai_api_request_timeout,
            mode=critic_agent_mode,
            system_prompt_cut_to=system_prompt_cut_to,
        )
        self.skill_manager = SkillManager(
            model_name=skill_manager_model_name,
            temperature=skill_manager_temperature,
            retrieval_top_k=skill_manager_retrieval_top_k,
            request_timout=openai_api_request_timeout,
            ckpt_dir=skill_library_dir if skill_library_dir else ckpt_dir,
            resume=True if resume or skill_library_dir else False,
            re_embed_skill=re_embed_skill,
        )
        self.recorder = U.EventRecorder(ckpt_dir=ckpt_dir, resume=resume)
        self.resume = resume

        # init variables for rollout
        self.action_agent_rollout_num_iter = -1
        self.task = None
        self.context = ""
        self.messages = None
        self.conversations = []
        self.last_events = None

    def reset(self, task, context="", reset_env=True):
        self.action_agent_rollout_num_iter = 0
        self.task = task
        self.context = context
        if reset_env:
            self.env.reset(
                options={
                    "mode": "soft",
                    "wait_ticks": self.env_wait_ticks,
                    "username": self.username,
                }
            )
        difficulty = (
            "easy" if len(self.curriculum_agent.completed_tasks) > 15 else "peaceful"
        )
        # step to peek an observation
        events = self.env.step(
            "bot.chat(`/time set ${getNextTime()}`);\n"
            + f"bot.chat('/difficulty {difficulty}');"
        )
        with Timer("voyager reset: retrieve skills"):
            skills = self.skill_manager.retrieve_skills(query=self.context)
        print(
            f"\033[32mRender Action Agent system message with {len(skills)} skills\033[0m"
        )
        system_message = self.action_agent.render_system_message(skills=skills)
        human_message = self.action_agent.render_human_message(
            events=events, code="", task=self.task, context=context, critique=""
        )
        self.messages = [system_message, human_message]
        # print(
        #     f"\033[32m****Action Agent human message****\n{human_message.content}\033[0m"
        # )
        assert len(self.messages) == 2
        self.conversations = []
        return self.messages

    def close(self):
        self.env.close()

    def step(self):
        if self.action_agent_rollout_num_iter < 0:
            raise ValueError("Agent must be reset before stepping")
        with Timer("step: llm select skill"):
            ai_message = self.action_agent.llm(self.messages)
            print(f"\033[34m****Action Agent ai message**** {ai_message.content}\033[0m")
        self.conversations.append(
            (self.messages[0].content, self.messages[1].content, ai_message.content)
        )
        with Timer("step: action agent process select skill response"):
            parsed_result = self.action_agent.process_ai_message(message=ai_message)
        success = False
        if isinstance(parsed_result, dict):
            code = parsed_result["program_code"] + "\n" + parsed_result["exec_code"]
            with Timer("step: env step"):
                events = self.env.step(
                    code,
                    programs=self.skill_manager.programs,
                )
            self.total_time, self.total_iter = self.recorder.record(events, self.task)
            self.action_agent.update_chest_memory(events[-1][1]["nearbyChests"])
            if self.environment == 'subgoal':
                with Timer('Check Subgoal Success'):
                    success = self.critic_agent.check_subgoal_success(
                        events=events,
                        task=self.task,
                    )
                    critique = ''
                    print(f'\033[35msuccess: {success}\033[0m')
            else:
                with Timer("step: critic agent check task success"):
                    success, critique = self.critic_agent.check_task_success(
                        events=events,
                        task=self.task,
                        context=self.context,
                        chest_observation=self.action_agent.render_chest_observation(),
                        max_retries=5,
                    )

            if self.reset_placed_if_failed and not success:
                # revert all the placing event in the last step
                blocks = []
                positions = []
                for event_type, event in events:
                    if event_type == "onSave" and event["onSave"].endswith("_placed"):
                        block = event["onSave"].split("_placed")[0]
                        position = event["status"]["position"]
                        blocks.append(block)
                        positions.append(position)
                new_events = self.env.step(
                    f"await givePlacedItemBack(bot, {U.json_dumps(blocks)}, {U.json_dumps(positions)})",
                    programs=self.skill_manager.programs,
                )
                events[-1][1]["inventory"] = new_events[-1][1]["inventory"]
                events[-1][1]["voxels"] = new_events[-1][1]["voxels"]
            with Timer("step: skill manager retrieve skills"):
                new_skills = self.skill_manager.retrieve_skills(
                    query=self.context
                    + "\n\n"
                    + self.action_agent.summarize_chatlog(events)
                )
            system_message = self.action_agent.render_system_message(skills=new_skills)
            human_message = self.action_agent.render_human_message(
                events=events,
                code=parsed_result["program_code"],
                task=self.task,
                context=self.context,
                critique=critique,
            )
            # human_message = self.action_agent.render_human_message(
            #     events=events,
            #     code=parsed_result["program_name"],
            #     task=self.task,
            #     critique=critique,
            #     skills=self.skills[1]
            # )
            self.last_events = copy.deepcopy(events)
            self.messages = [system_message, human_message]
        else:
            assert isinstance(parsed_result, str)
            # self.recorder.record([], self.task)
            self.total_time, self.total_iter = self.recorder.record([], self.task)
            print(f"\033[34m{parsed_result} Trying again!\033[0m")
        assert len(self.messages) == 2
        self.step_time.append(self.total_time)
        self.action_agent_rollout_num_iter += 1
        done = (
            self.action_agent_rollout_num_iter >= self.action_agent_task_max_retries
            or success
        )
        info = {
            "task": self.task,
            "success": success,
            "conversations": self.conversations,
        }
        if success:
            assert (
                "program_code" in parsed_result and "program_name" in parsed_result
            ), "program and program_name must be returned when success"
            info["program_code"] = parsed_result["program_code"]
            info["program_name"] = parsed_result["program_name"]
        else:
            print(f"\033[35m****step fails, Failed task: {self.task}****\033[0m")
            pass
            # print(
            #     f"\033[32m****Action Agent human message****\n{self.messages[-1].content}\033[0m"
            # )
        print(f"\033[35mstep inventory: {self.last_events[-1][1]['inventory']}\033[0m")
        print(f"\033[35mrollout step done: {done}\033[0m")
        return self.messages, self.last_events[-1][1]['inventory'], done, info

    def rollout(self, *, task, context, reset_env=True):
        with Timer("rollout: reset"):
            self.reset(task=task, context=context, reset_env=reset_env)
        while True:
            with Timer("rollout: step"):
                messages, reward, done, info = self.step()
            if done:
                break
        return messages, reward, done, info

    def learn(self, reset_env=True):
        self.inventory = []
        with Timer("env reset"):
            if self.resume:
                # keep the inventory
                self.env.reset(
                    options={
                        "mode": "soft",
                        "wait_ticks": self.env_wait_ticks,
                        "username": self.username
                    }
                )
            else:
                # clear the inventory
                self.env.reset(
                    options={
                        "mode": "hard",
                        "wait_ticks": self.env_wait_ticks,
                        "username": self.username
                    }
                )
                self.resume = True
        with Timer('env step with empty string'):
            self.last_events = self.env.step("")    

        while True:
            if self.recorder.iteration > self.max_iterations:
                print("Iteration limit reached")
                break
            with Timer("curriculum agent propose next task"):
                task, context = self.curriculum_agent.propose_next_task(
                    events=self.last_events,
                    chest_observation=self.action_agent.render_chest_observation(),
                    max_retries=5,
                )
            print(
                f'\033[35mStarting task "{task}" for at most {self.action_agent_task_max_retries} times\033[0m'
            )
            try:
                # messages, reward, done, info = self.rollout(
                with Timer("learn: rollout"):
                    messages, inventory, done, info = self.rollout(
                        task=task,
                        context=context,
                        reset_env=reset_env,
                    )
            except Exception as e:
                time.sleep(3)  # wait for mineflayer to exit
                info = {
                    "task": task,
                    "success": False,
                }
                # reset bot status here
                self.last_events = self.env.reset(
                    options={
                        "mode": "hard",
                        "wait_ticks": self.env_wait_ticks,
                        "inventory": self.last_events[-1][1]["inventory"],
                        "equipment": self.last_events[-1][1]["status"]["equipment"],
                        "position": self.last_events[-1][1]["status"]["position"],
                        "username": self.username
                    }
                )
                # use red color background to print the error
                print("Your last round rollout terminated due to error:")
                print(f"\033[41m{e}\033[0m")
                import traceback; traceback.print_exc()
                continue

            if info["success"]:
                self.skill_manager.add_new_skill(info)

            new_inventory = [key for key in inventory if key not in self.inventory]
            self.inventory += new_inventory
            U.f_mkdir(f"./results/explore")
            U.dump_text(f"Iteration: {self.recorder.iteration}, Inventory obtained: {new_inventory}, Total inventory: {self.inventory}, Num: {len(self.inventory)}\n", f"./results/explore/{self.action_agent_model_name.replace(' ', '_')}.txt")
            with Timer("curriculum agent update exploration progress"):
                self.curriculum_agent.update_exploration_progress(info)
            print(
                f"\033[35mCompleted tasks: {', '.join(self.curriculum_agent.completed_tasks)}\033[0m"
            )
            print(
                f"\033[35mFailed tasks: {', '.join(self.curriculum_agent.failed_tasks)}\033[0m"
            )
        U.f_mkdir(f"./results/{self.environment}")
        completed = None
        print(f"\033[32m\n\nTicks on each step: {self.step_time}, LLM iters: {self.total_iter}, Completed: {completed}\033[0m")
        U.dump_text(f"\n\nTicks on each step: {self.step_time}; LLM iters: {self.total_iter}; Completed: {completed}", f"./results/{self.environment}/explore_{self.action_agent_model_name.replace(' ', '_')}.txt")
        return {
            "completed_tasks": self.curriculum_agent.completed_tasks,
            "failed_tasks": self.curriculum_agent.failed_tasks,
            "skills": self.skill_manager.skills,
        }

    # def decompose_task(self, task):
    #     if not self.last_events:
    #         self.last_events = self.env.reset(
    #             options={
    #                 "mode": "hard",
    #                 "wait_ticks": self.env_wait_ticks,
    #                 "username": self.username
    #             }
    #         )
    #     return self.curriculum_agent.decompose_task(task, self.last_events)
    
    def decompose_task(self, task, last_tasklist=None, critique=None, health=None):
        if not self.last_events:
            self.last_events = self.env.reset(
                options={
                    "mode": "hard",
                    "wait_ticks": self.env_wait_ticks,
                    "username": self.username
                }
            )
        return self.curriculum_agent.decompose_task(self.environment, task, last_tasklist, critique, health)

    def inference(self, task=None, sub_goals=[], reset_mode="hard", reset_env=True):
        if not task and not sub_goals:
            raise ValueError("Either task or sub_goals must be provided")
        if not sub_goals:
            sub_goals = self.decompose_task(task)
        self.env.reset(
            options={
                "mode": reset_mode,
                "wait_ticks": self.env_wait_ticks,
                "username": self.username
            }
        )
        self.curriculum_agent.completed_tasks = []
        self.curriculum_agent.failed_tasks = []
        self.last_events = self.env.step("")
        while self.curriculum_agent.progress < len(sub_goals):
            next_task = sub_goals[self.curriculum_agent.progress]
            context = self.curriculum_agent.get_task_context(next_task)
            print(
                f"\033[35mStarting task {next_task} for at most {self.action_agent_task_max_retries} times\033[0m"
            )
            messages, reward, done, info = self.rollout(
                task=next_task,
                context=context,
                reset_env=reset_env,
            )
            self.curriculum_agent.update_exploration_progress(info)
            print(
                f"\033[35mCompleted tasks: {', '.join(self.curriculum_agent.completed_tasks)}\033[0m"
            )
            print(
                f"\033[35mFailed tasks: {', '.join(self.curriculum_agent.failed_tasks)}\033[0m"
            )

    def inference_combat(self, task:str=None, sub_goals=[], reset_mode="hard", reset_env=True, feedback_rounds:int=1):
        if not task and not sub_goals:
            raise ValueError("Either task or sub_goals must be provided")
        print(f'\033[35mStarting inference for task: {task}\033[0m')
        with Timer('env reset'):
            self.last_events = self.env.reset(
                options={
                    "mode": reset_mode,
                    "wait_ticks": self.env_wait_ticks,
                    "username": self.username
                }
            )
        if not sub_goals:
            with Timer('decompose task'):
                sub_goals = self.decompose_task(task)
                print(f'\033[35mDecomposed sub_goals: {sub_goals}\033[0m')
        
        self.curriculum_agent.completed_tasks = []
        self.curriculum_agent.failed_tasks = []
        self.last_events = self.env.step("")
        for i in range(feedback_rounds):
            try:
                self.recorder.elapsed_time = 0
                self.recorder.iteration = 0
                self.step_time = []
                self.critic_agent.last_inventory = "Empty"
                self.critic_agent.last_inventory_used = 0
                while self.curriculum_agent.progress < len(sub_goals):
                    next_task = sub_goals[self.curriculum_agent.progress]
                    print(f'\033[35mNext subgoal: {next_task}, All subgoals: {sub_goals}\033[0m')
                    with Timer('get task context'):
                        context = self.curriculum_agent.get_task_context(next_task)
                        print(f'\033[35mGot task context: {context}\033[0m')
                    with Timer('rollout'):
                        messages, reward, done, info = self.rollout(
                            task=next_task,
                            context=context,
                            reset_env=reset_env,
                        )
                    with Timer('Update Exploration Progress'):
                        self.curriculum_agent.update_exploration_progress(info)
                        print(f"\033[35mCompleted tasks: {', '.join(self.curriculum_agent.completed_tasks)}\033[0m")
                        print(f"\033[31mFailed tasks: {', '.join(self.curriculum_agent.failed_tasks)}\033[0m")
                    print(f'\033[35mself.step_time[-1]: {self.step_time[-1]}\033[0m')
                    if (self.step_time[-1] >= 24000):
                        print(f"\033[31mInference Time limit reached >=24000\033[0m")
                        break
                # str_list = task.split()
                # TODO: hard coding
                self.run_raw_skill("./test_env/combatEnv.js", [10, 15, 100])
                with Timer('rerank monsters'):
                    combat_order = self.curriculum_agent.rerank_monster(task=task)
                    print(f'\033[35mCombat order: {combat_order}\033[0m')

                for task_item in task.split(','):
                    summon_para = task_item.split()
                    summon_para.insert(1, 5)  # idx =1, r=5
                    self.run_raw_skill("./test_env/summonMob.js", summon_para)

                monster_origin = task.split(',')
                try:
                    for monster in combat_order:
                        para = monster.split(' ')
                        combat_para2 = int(para[0])
                        combat_para1 = para[1].lower() # ensure no uppercase
                except:
                    # if error happens, use the origin order to kill monster
                    combat_order = monster_origin
                finally:
                    for monster in combat_order:
                        para = monster.split(' ')
                        combat_para2 = int(para[0])
                        combat_para1 = para[1].lower() # ensure no uppercase
                        with Timer('kill monsters'):
                            print(f'\033[35mKill monster skill parameter: {combat_para1}, {combat_para2}\033[0m')
                            kill_res = self.run_raw_skill("skill_library/skill/primitive/killMonsters.js", [combat_para1, combat_para2])
                        if 'lost' in kill_res:
                            break
                with Timer('Comment Check Task Success'):
                    health, cirtiques, result, equipment = \
                        self.comment_agent.check_task_success(events=self.last_events, task=sub_goals, time=self.total_time, iter=self.total_iter)
                U.f_mkdir(f"./results/combat")
                U.dump_text(f"Route {i}; Plan list: {sub_goals}; Equipments obtained: {equipment}; Ticks on each step: {self.step_time}; LLM iters: {self.total_iter}; Health: {health:.1f}; Combat result: {result}\n\n", f"./results/combat/{task.replace(' ', '_')}{self.action_agent_model_name.replace(' ', '_')}.txt")

                with Timer('decompose task again based on feedback'):
                    sub_goals = self.decompose_task(task, last_tasklist=equipment, critique=cirtiques, health=health)
                    print(f'\033[35mDecomposed sub_goals based on feedback: {sub_goals}\033[0m')
                
            except Exception as e:
                traceback.print_exc()
                U.f_mkdir(f"./results/{self.environment}")
                U.dump_text(f"Route {i}; Plan list: {sub_goals}; Ticks on each step: {self.step_time}; LLM iters: {self.total_iter}; failed; caused by {e}\n\n", f"./results/combat/{task.replace(' ', '_')}{self.action_agent_model_name.replace(' ', '_')}.txt")
            finally:
                self.run_raw_skill("./test_env/respawnAndClear.js")
                self.env.reset(
                    options={
                        "mode": "hard",
                        "wait_ticks": self.env_wait_ticks,
                        "username": self.username
                    }
                )
                self.curriculum_agent.completed_tasks = []
                self.curriculum_agent.failed_tasks = []
        
    def run_raw_skill(self, skill_path, parameters = [], reset = False):
        # reset here only used for skill test
        if (reset):
            self.env.reset(
                options={
                    "mode": "soft",
                    "wait_ticks": self.env_wait_ticks,
                    "username": self.username
                }
            )
        retry = 3
        while retry > 0:
            try:
                babel = require("@babel/core")
                babel_generator = require("@babel/generator").default

                with open(f"{skill_path}", 'r') as file:
                    code = file.read()

                parsed = babel.parse(code)
                functions = []
                assert len(list(parsed.program.body)) > 0, "No functions found"
                for i, node in enumerate(parsed.program.body):
                    if node.type != "FunctionDeclaration":
                        continue
                    node_type = (
                        "AsyncFunctionDeclaration"
                        if node["async"]
                        else "FunctionDeclaration"
                    )
                    functions.append(
                        {
                            "name": node.id.name,
                            "type": node_type,
                            "body": babel_generator(node).code,
                            "params": list(node["params"]),
                        }
                    )
                # find the last async function
                main_function = None
                for function in reversed(functions):
                    if function["type"] == "AsyncFunctionDeclaration":
                        main_function = function
                        break
                assert (
                    main_function is not None
                ), "No async function found. Your main function must be async."
                assert (
                    main_function["params"][0].name == "bot"
                ), f"Main function {main_function['name']} must take a single argument named 'bot'"
                
                program_code = "\n\n".join(function["body"] for function in functions)
                para_list = "(bot"
                for i in range(len(parameters)):
                    if isinstance(parameters[i], str):
                        para_list += ", " + "\"" + parameters[i] + "\""
                    else:
                        para_list += ", " + str(parameters[i])
                para_list += ");"
                exec_code = f"await {main_function['name']}{para_list}"
                parsed_result = {
                    "program_code": program_code,
                    "program_name": main_function["name"],
                    "exec_code": exec_code,
                }
                break
            except Exception as e:
                retry -= 1
                parsed_result = f"Error parsing action response (before program execution): {e}"

        result = ''
        if isinstance(parsed_result, dict):
            code = parsed_result["program_code"] + "\n" + parsed_result["exec_code"]
            events = self.env.step(
                code,
                programs=self.skill_manager.programs,
            )
            for event in reversed(events):
                if event[0] == 'onChat':
                    result = event[1]['onChat']
                    break
            self.last_events = copy.deepcopy(events)
        else:
            print(f"\033[31m{parsed_result} Code executes error!\033[0m")
        
        return result