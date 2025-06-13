import os
import json
import logging
from pydantic import BaseModel
from openai import OpenAI
import configparser

class LLMCaller:
    def __init__(self, root, model, prompt_folder="/scripts/graph/edges"):
        self.root = root
        self.model = model
        self.prompt_folder = prompt_folder
        config = configparser.ConfigParser()
        config.read('config.conf')
        os.environ['OPENAI_API_KEY'] = config['settings']['root']    
        self.client = OpenAI()
        self.output_json = {}
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def __read_text(self, file_path):
        with open(self.root+file_path, 'r') as file:
            return file.read()

    def insert_message(self, user_message, prompt):
        for message in prompt['messages'][::-1]:
            if message['role'] == 'user':
                message['content'] = user_message
                break
        return prompt

    def message_to_json(self, prompt_file_name, user_message, response_format):
        prompt_path = f"{self.prompt_folder}/{prompt_file_name}.json"
        prompt = json.loads(self.__read_text(prompt_path))
        prompt = self.insert_message(user_message, prompt)
        response = self.client.beta.chat.completions.parse(model=self.model, messages=prompt["messages"], response_format=response_format)
        assistant_message = response.choices[0].message.content.strip()
        self.output_json = json.loads(assistant_message)
        logging.info(f"[{prompt_file_name.upper()}] Response length: {len(assistant_message)}")

    # for unit test
    class test_SupportingStatement(BaseModel):
        topic_sentence: str
        documented_fact_or_example: str

    class test_CoreConcept(BaseModel):
        descriptive_title: str
        transition_sentence: str
        full_declarative_sentence: str
        supporting_statements: list["LLMCaller.test_SupportingStatement"]
    
    class test_Script(BaseModel):    
        intro: str
        core_concepts: list["LLMCaller.test_CoreConcept"]
        outro: str

    class test_OutlineStructure(BaseModel):
        title: str
        main_visual_style: str
        script: "LLMCaller.test_Script"

if __name__ == '__main__':
    root = '/Users/apple/Desktop/sd/repo'
    model = 'gpt-4o-mini'
    llmcaller = LLMCaller(root, model)
    prompt_file_name = "sketch"
    user_message = "How did Mao defeated the Kou Min Tang in 1940s?"
    llmcaller.message_to_json(prompt_file_name, user_message, LLMCaller.test_OutlineStructure)
    print(llmcaller.output_json)