import os
import json
import pickle
import logging
from llmcaller import LLMCaller
from pydantic import BaseModel
from openai import OpenAI
import configparser
from youtube_transcript_api import YouTubeTranscriptApi
import time

class Scripter:
    def __init__(self, video_id='lcBNWiCn1Uo') -> None:
        config = configparser.ConfigParser()
        config.read('config.conf')
        self.root = config['settings']['root']
        self.model = config['settings']['model']
        self.video_id = video_id
        self.script = ''
    def getRawTranscript(self, language = 'en'):
        # retrieve the available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(self.video_id)
        for transcript in transcript_list:
            print(
                transcript.video_id,
                transcript.language_code,
                transcript.is_generated,
                transcript.is_translatable,
            )
            if transcript.language_code == language:
                for sentence in transcript.fetch():
                    self.script = f"{self.script} {sentence['text']}"
                return True
        return False
    def getStructure(self):
        user_message = ""
        user_message = f""
    def production(self):
        # english transcript
        ### summary
        ### rewrite summary
        # for paragraph in paragraphs:
        ### get single pure text
        # return text
        return

def add_message(history, role, message):
    return history + [{'role': role, 'content': message}]

def chat(history, model, user_message, response_format=None):
    history = add_message(history, "user", user_message)
    if response_format is not None:
        response = client.beta.chat.completions.parse(model=model,messages=history, response_format=response_format)
    else:
        response = client.beta.chat.completions.parse(model=model,messages=history)
    assistant_message = response.choices[0].message.content.strip()
    print(f'\n============================\n{assistant_message}\n\n')
    return add_message(history, "assistant", assistant_message)

class Number(BaseModel):
    number_of_paragraphs: int
class Paragraph(BaseModel):
    script_for_youtube: str

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.conf')
    os.environ['OPENAI_API_KEY'] = config['settings']['root']
    root = '/Users/apple/Desktop/sd/repo'
    script = ''
    with open(f"{root}/scripts/zh-script.txt", 'r') as f:
        script = f.read()
    """
    s = Scripter()
    if s.getRawTranscript():
        print(len(s.script))
    """
    article_provided = False

    client = OpenAI()
    model = 'gpt-4o-mini'
    history = []
    history = add_message(history, "system", "You are an assistant who writes scripts for a youtuber.")
    
    user_message = f"Write a detailed structured summary about this youtube script, including the examples and supporting facts. Because the script is from another youtuber's creation and the goal is to rewrite it, so ignore the youtuber-specific parts (like ask for the name of the youtuber, parts that involve that youtubers' other creation that is not mentioned in the youtube script input, subscribe, like, etc.)\n\n"
    user_message = f"{user_message}[Youtube Script that we are going to reference from]\n{script}\n\n"
    history = chat(history, model, user_message)

    user_message = "How many paragraphs are there in this new structured summary?"
    history = chat(history, model, user_message, Number)
    
    user_message = "What are the target audiences for this article?"    
    history = chat(history, model, user_message)

    user_message = "according to the target audience, what would be missing or redudant?"
    history = chat(history, model, user_message)

    user_message = "please recreate a detailed structured summary according to the target audience and feedback given."
    history = chat(history, model, user_message)
    
    user_message = "How many paragraphs are there in this new structured summary?"
    history = chat(history, model, user_message, Number)
    number_of_paragraphs = json.loads(history[-1]['content'])['number_of_paragraphs']
    
    user_message = f"From now on, you are going to write a youtube script for me. And because the script will go directly into an AI-generated voice funciton, only return pure text and do not add anything that would not be spoken out like directions of tone. However, there is a way to control the emotions of the script without explicitly saying out. That is to use capitalization or grammar if needed, which the voice generator would then understand. Because the script would be too long for one output, when I type '1', then produce the script for paragraph 1, when '2' then paragraph 2, etc. For each paragraph, come up with in-depth facts or examples to make the content more attractive rather than just being a superficial introduction of some knowledge."
    history = chat(history, model, user_message)
    
    script_for_youtube = []
    for i in range(number_of_paragraphs):
        history = chat(history, model, str(i+1), Paragraph)
        script_for_youtube.append(json.loads(history[-1]['content'])['script_for_youtube'])
        print(f"{i+1}\t{len(script_for_youtube[-1])}")

    for script in script_for_youtube:
        print(f"\n=======\n{script}")


    

    # summary
    # add spice
    # iterate through script

        