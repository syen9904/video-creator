import os
import pickle
import logging
import configparser
from pydantic import BaseModel
from textprocessor import TextProcessor
from llmcaller import LLMCaller
from openai import OpenAI
from moviepy.editor import AudioFileClip

class Paragraph():
    def __init__(self, output_dir, outline, topic, paragraph) -> None:
        config = configparser.ConfigParser()
        config.read('config.conf')
        self.root = config['settings']['root']
        self.model = config['settings']['model']
        self.sentence_length = config.getint('settings', 'sentence_length')
        self.output_dir, self.outline, self.topic, self.paragraph = output_dir, outline, topic, paragraph
        self.timestamps, self.sentences, self.durations = [], [], []
        self.audio_path = f"{self.output_dir}/speech.mp3"
        self.output_path = f"{self.root}{self.output_dir}/paragraph.pkl"
        if not os.path.exists(f"{self.root}{self.output_dir}"):
            os.makedirs(f"{self.root}{self.output_dir}", exist_ok=True)
        with open(self.output_path, "wb") as f:
            pickle.dump(self, f)
        logging.info(f"Generated text with length = {len(paragraph)} saved to '{self.output_path}'.")
    
    # [PROD] Humanize Paragraph
    class HumanizeParagraph(BaseModel):
        paragraph: str    
    def __humanize(self) -> None:
        llmcaller = LLMCaller(self.root, self.model)
        llmcaller.output_json['paragraph'] = ''
        while len(llmcaller.output_json['paragraph']) < len(self.paragraph) * 0.75:
            user_message = self.paragraph
            llmcaller.message_to_json('humanize', user_message, self.HumanizeParagraph)
            self.paragraph = llmcaller.output_json['paragraph']

    # [PROD] get crude timestamps
    def __getSpeechAndTranscription(self, model="tts-1", voice="alloy"):
        client = OpenAI()
        with client.audio.speech.with_streaming_response.create(model=model, voice=voice, input=self.paragraph) as response:
            response.stream_to_file(f"{self.root}{self.audio_path}")
            logging.info(f"{self.root}{self.audio_path} retrieved")
        transcription = client.audio.transcriptions.create(file=open(self.root+self.audio_path, "rb"), model="whisper-1", response_format="verbose_json", timestamp_granularities=["word"])
        self.transcription = []
        for timestamp in transcription.words:
            self.transcription.append({'word': timestamp.word, 'start': timestamp.start, 'end': timestamp.end})

    # [PROD] match timestamps to script
    def __getTimestamps(self):
        # store time stamps
        self.paragraph = self.paragraph.replace("’", "'").replace("!", ".").replace("?", ".").replace('\n', '')
        index = 0
        lag = 0
        self.timestamps = []
        for timestamp in self.transcription:
            new_index = self.paragraph.lower().find(timestamp['word'].lower(), index)
            #print(new_index, '\t', timestamp['word'].lower(), '\t', self.paragraph.lower()[index:index+40])
            if new_index >= 0 and (new_index-index) < lag:
                self.timestamps.append({'index': new_index, 
                                        'start': timestamp['start'], 
                                        'end': timestamp['end'], 
                                        'word': timestamp['word']})
                index = new_index + 1
                lag = len(timestamp['word']) + 5
            else: lag += len(timestamp['word']) + 5
        
    # [PROD] split text into raw sentences with timestamp
    def __createSentences(self):
        self.sentences = self.paragraph.split('. ')
        self.durations = [-1] * len(self.sentences)
        for i in range(len(self.sentences)):
            index = self.paragraph.find(self.sentences[i])
            for timestamp in self.timestamps:
                if timestamp['index'] >= index:
                    # start time
                    self.durations[i] = timestamp['start']   
                    # ∆ start times
                    if i > 0:
                        self.durations[i-1] = timestamp['start'] - self.durations[i-1] 
                    break

        # Create a slightly longer duration for [-1] for trimming
        audio_clip = AudioFileClip(self.root+self.audio_path)
        self.durations[-1] = audio_clip.duration - self.durations[-1] + 1 
        audio_clip.close()
        
    # [PROD] merge raw sentences that are too short
    def __combineSentences(self):
        # Combine short sentences            
        too_short = True
        while too_short and len(self.sentences) > 1:
            too_short = False
            for i in range(len(self.sentences)-1):
                if self.durations[i] < self.sentence_length:
                    self.sentences = self.sentences[:i] + ['. '.join(self.sentences[i:i+2])] + self.sentences[i+2:]
                    self.durations = self.durations[:i] + [self.durations[i]+self.durations[i+1]] + self.durations[i+2:]
                    break
            for duration in self.durations[:-1]:
                if duration < self.sentence_length:
                    too_short = True
                    break

        # Edge case for combining short sentences
        if self.durations[-1] < self.sentence_length and len(self.durations) > 1:
            self.sentences = self.sentences[:-2] + [self.sentences[-2]+self.sentences[-1]]
            self.durations = self.durations[:-2] + [self.durations[-2]+self.durations[-1]]
        
    # [PROD] from raw text to sentences with duration
    def production(self) -> None:
        self.__humanize()
        self.__getSpeechAndTranscription()
        self.__getTimestamps()
        self.__createSentences()
        self.__combineSentences()
        with open(self.output_path, 'wb') as f:
            pickle.dump(self, f)

if __name__ == '__main__':
    root = '/Users/apple/Desktop/sd/repo'
    output_dir = '/data/tests/1'
    obj_path = f"{root}{output_dir}/paragraph.pkl"

    #with open(f"{root}/data/tests/outline.pkl", 'rb') as f:
    #    outline = pickle.load(f)
    #outline.outlineToParagraphs()

    with open(obj_path, 'rb') as f:
        p = pickle.load(f)
    print(len(p.paragraph))
    #p.production()
    print(len(p.paragraph))