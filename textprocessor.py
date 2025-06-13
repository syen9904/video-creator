import os
import pickle
import logging
from llmcaller import LLMCaller
from pydantic import BaseModel
import configparser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TextProcessor():
    class SupportingStatement(BaseModel):
        topic_sentence: str
        documented_fact_or_example: str

    class CoreConcept(BaseModel):
        descriptive_title: str
        transition_sentence: str
        full_declarative_sentence: str
        supporting_statements: list["TextProcessor.SupportingStatement"]
    
    class Script(BaseModel):    
        intro: str
        core_concepts: list["TextProcessor.CoreConcept"]
        outro: str

    class OutlineStructure(BaseModel):
        title: str
        main_visual_style: str
        script: "TextProcessor.Script"

    class CoreConceptTopicSentences(BaseModel):
        supporting_sentences: list[str]
    
    def __init__(self, root, model, output_dir, title, sentence_length=5) -> None:
        self.root, self.output_dir, self.model = root, output_dir, model
        self.original_title = title
        self.sentence_length = sentence_length
        self.outline = {}
        self.keywords_to_avoid = set()
        self.used_clips = set()

    # [Housekeeping] get current script and length
    def __getScripts(self, item = None) -> list[str]:
        scripts = []
        if item is None: item = self.outline['script']
        if isinstance(item, str): return [item]
        elif isinstance(item, list) or isinstance(item, tuple):
            for element in item: scripts.extend(self.__getScripts(element))
        elif isinstance(item, dict):
            for key in item.keys():
                if key.find('title') >= 0: continue
                else: scripts.extend(self.__getScripts(item[key]))
        return scripts

    # [PROD] Create v1 outline
    def __sketch(self) -> None:
        llmcaller = LLMCaller(self.root, self.model)
        llmcaller.output_json['script'] = {'core_concepts': []}
        while len(llmcaller.output_json['script']['core_concepts']) != 5: 
            logging.info(f"{len(llmcaller.output_json['script']['core_concepts'])} core concepts. Call LLM.")
            try: llmcaller.message_to_json('sketch', self.original_title, self.OutlineStructure)
            except Exception as e: print(e)
            self.outline = llmcaller.output_json
        logging.info(f"[CURRENT CONTENT SIZE]: {len(self.__getScripts())}, {len(''.join(self.__getScripts()))}")

    # [PROD] Expand v1 outline with examples
    def __expand(self) -> None:
        structure = f"{self.outline['title']}\n"
        structure = f"{structure}\n{self.outline['script']['intro']}\n"
        for i, core_concept in enumerate(self.outline['script']['core_concepts']):
            structure = f"{structure}\n{i+1}. {core_concept['descriptive_title']}\n"
            structure = f"{structure}   {core_concept['transition_sentence']}\n"
            structure = f"{structure}   {core_concept['full_declarative_sentence']}\n"
            for j, supporting_statement in enumerate(core_concept['supporting_statements']):
                structure = f"{structure}  ({j+1}) {supporting_statement['topic_sentence']}\n"
                structure = f"{structure}      - {supporting_statement['documented_fact_or_example']}\n" #
        structure = f"{structure}\n{self.outline['script']['outro']}\n"
        for i, core_concept in enumerate(self.outline['script']['core_concepts']):
            user_message = ''
            user_message = f"{user_message}\n[The Concept To Be Expanded]\n"
            user_message = f"{user_message}descriptive_title: {core_concept['descriptive_title']}\n"
            user_message = f"{user_message}full_declarative_sentence: {core_concept['full_declarative_sentence']}\n"
            for j, supporting_statement in enumerate(core_concept['supporting_statements']):
                user_message = f"{user_message}\n[SUPPORTING STATEMENT {j+1}]\n"
                user_message = f"{user_message}topic_sentence: {supporting_statement['topic_sentence']}\n"
                user_message = f"{user_message}documented_fact_or_example: {supporting_statement['documented_fact_or_example']}\n"
            user_message = f"{user_message}\n[Overall Structure]\n{structure}\n"
            llmcaller = LLMCaller(self.root, self.model)
            llmcaller.message_to_json('expand', user_message, self.CoreConcept)
            self.outline['script']['core_concepts'][i] = llmcaller.output_json
        self.outline['script']['core_concepts'][0].pop('transition_sentence')
        logging.info(f"[CURRENT CONTENT SIZE]: {len(self.__getScripts())}, {len(''.join(self.__getScripts()))}")

    # [PROD] Create connectivity in outline after expand
    def __cohere(self) -> None:
        for core_concept in self.outline['script']['core_concepts']:
            user_message = ''
            user_message = f"{user_message}[TOPIC]\n{core_concept['full_declarative_sentence']}\n\n[SUPPORT SENTENCES]\n"
            for supporting_statement in core_concept['supporting_statements']:
                user_message = f"{user_message}{supporting_statement['topic_sentence']}\n"
            llmcaller = LLMCaller(self.root, self.model)
            llmcaller.output_json['supporting_sentences'] = []
            while len(llmcaller.output_json['supporting_sentences']) != len(core_concept['supporting_statements']): 
                logging.info(f"{len(llmcaller.output_json['supporting_sentences'])} sentences (need {len(core_concept['supporting_statements'])}). Call LLM.")
                try: llmcaller.message_to_json('cohere', user_message, self.CoreConceptTopicSentences)
                except Exception as e: print(e)
            for i, supporting_statement in enumerate(core_concept['supporting_statements']):
                supporting_statement['topic_sentence'] = llmcaller.output_json['supporting_sentences'][i]
        logging.info(f"[CURRENT CONTENT SIZE]: {len(self.__getScripts())}, {len(''.join(self.__getScripts()))}")
    
    # [PROD] Create list of Paragraph obj from outline
    def outlineToParagraphs(self) -> None:
        from paragraph import Paragraph
        self.paragraphs = []
        core_concepts = self.outline['script']['core_concepts']
        for i, core_concept in enumerate(core_concepts):
            paragraph = f"{core_concept['full_declarative_sentence']} "
            for supporting_statement in core_concept["supporting_statements"]:
                paragraph = f"{paragraph} {supporting_statement['topic_sentence']} {supporting_statement['documented_fact_or_example']} "
            self.paragraphs.append(Paragraph(f"{self.output_dir}/{i+1}", self, f"{i+1}. {core_concept['descriptive_title']}", paragraph))
        self.paragraphs = [Paragraph(f"{self.output_dir}/0", self, "intro", self.outline['script']['intro'])] + self.paragraphs
        self.paragraphs = self.paragraphs + [Paragraph(f"{self.output_dir}/{len(core_concepts)+1}", self, "outro", self.outline['script']['outro'])]

    # [I/O] outline O/I, paragraphs O/I
    def production(self) -> None:
        self.__sketch()
        self.__expand()
        self.__cohere()
        self.outlineToParagraphs()
        self.title = self.outline['title']
        self.main_visual_style = self.outline['main_visual_style']
        output_path = f"{self.root}{self.output_dir}/outline.pkl"
        with open(output_path, 'wb') as f:
            pickle.dump(self, f)

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.conf')
    os.environ['OPENAI_API_KEY'] = config['settings']['root']
    root = '/Users/apple/Desktop/sd/repo'
    output_dir = '/data/tests'
    model = 'gpt-4o-mini'
    user_message = "Why is bitcoin so popular?"
    logging.info(f"[TITLE] {user_message}")
    tp = TextProcessor(root, model, output_dir, user_message)
    tp.production()
    with open(f"{root}{output_dir}/outline.pkl", "rb") as f:
        new_tp = pickle.load(f)
    print(new_tp.outline['main_visual_style'])
    
    """
    #tp.introSplit()
    gemini_key = config['settings']['gemini_key']
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    result = model.generate_content(
        user_message,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json", response_schema=New
        ),
    )
    print(json.loads(result.text))
    """