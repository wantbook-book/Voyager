import os

import voyager.utils as U
# from langchain.chat_models import ChatOpenAI
# from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from langchain.vectorstores import Chroma

from voyager.prompts import load_prompt
from voyager.control_primitives import load_control_primitives
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
import os

class SkillManager:
    def __init__(
        self,
        model_name="gpt-3.5-turbo",
        temperature=0,
        retrieval_top_k=5,
        request_timout=120,
        ckpt_dir="ckpt",
        resume=False,
        re_embed_skill=False
    ):
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

        embeddings_model = AzureOpenAIEmbeddings(
            azure_endpoint=os.environ["AZURE_EMBEDDING_ENDPOINT"],
            azure_deployment='text-embedding-3-large',
            openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            openai_api_key=os.environ['OPENAI_EMBEDDING_API_KEY']
        )


        U.f_mkdir(f"{ckpt_dir}/skill/code")
        U.f_mkdir(f"{ckpt_dir}/skill/description")
        U.f_mkdir(f"{ckpt_dir}/skill/vectordb")
        # programs for env execution
        self.control_primitives = load_control_primitives()
        self.skill_primitives = self.load_skill_primitives()
        if resume:
            print(f"\033[33mLoading Skill Manager from {ckpt_dir}/skill\033[0m")
            self.skills = U.load_json(f"{ckpt_dir}/skill/skills.json")
        else:
            self.skills = {}
        self.retrieval_top_k = retrieval_top_k
        self.ckpt_dir = ckpt_dir
        # self.vectordb = Chroma(
        #     collection_name="skill_vectordb",
        #     embedding_function=OpenAIEmbeddings(),
        #     persist_directory=f"{ckpt_dir}/skill/vectordb",
        # )
        self.vectordb = Chroma(
            collection_name="skill_vectordb",
            embedding_function=embeddings_model,
            persist_directory=f"{ckpt_dir}/skill/vectordb",
        )
        if re_embed_skill:
            for key, value in self.skills.items():
                self.vectordb.add_texts(
                    texts=[value['description']],
                    ids=[key],
                    metadatas=[{"name": key}],
                )
            
            self.vectordb.persist()
        assert self.vectordb._collection.count() == len(self.skills), (
            f"Skill Manager's vectordb is not synced with skills.json.\n"
            f"There are {self.vectordb._collection.count()} skills in vectordb but {len(self.skills)} skills in skills.json.\n"
            f"Did you set resume=False when initializing the manager?\n"
            f"You may need to manually delete the vectordb directory for running from scratch."
        )

    @property
    def programs(self):
        # programs = ""
        # for skill_name, entry in self.skills.items():
        #     programs += f"{entry['code']}\n\n"
        # for primitives in self.control_primitives:
        #     programs += f"{primitives}\n\n"
        # return programs
    
        programs = ""
        for skill_name, entry in self.skills.items():
            programs += f"{entry['code']}\n\n"
        for primitives in self.control_primitives:
            programs += f"{primitives}\n\n"
        for skill_primitive in self.skill_primitives:
            programs += f"{skill_primitive}\n\n"
        return programs

    def add_new_skill(self, info):
        if info["task"].startswith("Deposit useless items into the chest at"):
            # No need to reuse the deposit skill
            return
        program_name = info["program_name"]
        program_code = info["program_code"]
        skill_description = self.generate_skill_description(program_name, program_code)
        print(
            f"\033[33mSkill Manager generated description for {program_name}:\n{skill_description}\033[0m"
        )
        if program_name in self.skills:
            print(f"\033[33mSkill {program_name} already exists. Rewriting!\033[0m")
            self.vectordb._collection.delete(ids=[program_name])
            i = 2
            while f"{program_name}V{i}.js" in os.listdir(f"{self.ckpt_dir}/skill/code"):
                i += 1
            dumped_program_name = f"{program_name}V{i}"
        else:
            dumped_program_name = program_name
        self.vectordb.add_texts(
            texts=[skill_description],
            ids=[program_name],
            metadatas=[{"name": program_name}],
        )
        self.skills[program_name] = {
            "code": program_code,
            "description": skill_description,
        }
        assert self.vectordb._collection.count() == len(
            self.skills
        ), "vectordb is not synced with skills.json"
        U.dump_text(
            program_code, f"{self.ckpt_dir}/skill/code/{dumped_program_name}.js"
        )
        U.dump_text(
            skill_description,
            f"{self.ckpt_dir}/skill/description/{dumped_program_name}.txt",
        )
        U.dump_json(self.skills, f"{self.ckpt_dir}/skill/skills.json")
        self.vectordb.persist()

    def generate_skill_description(self, program_name, program_code):
        messages = [
            SystemMessage(content=load_prompt("skill")),
            HumanMessage(
                content=program_code
                + "\n\n"
                + f"The main function is `{program_name}`."
            ),
        ]
        skill_description = f"    // { self.llm(messages).content}"
        return f"async function {program_name}(bot) {{\n{skill_description}\n}}"

    def retrieve_skills(self, query):
        # import ipdb; ipdb.set_trace()
        k = min(self.vectordb._collection.count(), self.retrieval_top_k)
        if k == 0:
            return []
        print(f"\033[32mSkill Manager retrieving for {k} skills\033[0m")
        docs_and_scores = self.vectordb.similarity_search_with_score(query, k=k)
        print(
            f"\033[32mSkill Manager retrieved skills: "
            f"{', '.join([doc.metadata['name'] for doc, _ in docs_and_scores])}\033[0m"
        )
        skills = []
        for doc, _ in docs_and_scores:
            skills.append(self.skills[doc.metadata["name"]]["code"])
        return skills

    def load_skill_primitives(self, primitive_names=None):
        package_path = "skill_library/skill"
        if primitive_names is None:
            primitive_names = [
                primitives[:-3]
                for primitives in os.listdir(f"{package_path}/primitive")
                if primitives.endswith(".js")
            ]
        primitives = [
            U.load_text(f"{package_path}/primitive/{primitive_name}.js")
            for primitive_name in primitive_names
        ]
        return primitives