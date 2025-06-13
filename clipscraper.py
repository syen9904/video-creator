import os
import pickle
import time
import logging
import subprocess
import configparser
from openai import OpenAI
from browser import Browser
from llmcaller import LLMCaller
from pydantic import BaseModel
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ClipScraper():
    def __init__(self, output_dir, script, isSameScript=False, isThumbnail=False):
        config = configparser.ConfigParser()
        config.read('config.conf')
        self.root = config['settings']['root']
        self.model = config['settings']['model']
        self.email = config['settings']['email']
        self.pwd = config['settings']['password']
        self.sentence_length = config.getint('settings', 'sentence_length')
        self.output_dir = output_dir
        self.audio_path = self.output_dir + config['settings']['audio_file_name']
        self.script = script
        self.isThumbnail = isThumbnail
        self.isSameScript = isSameScript
        self.title = ''
        self.main_visual_style = ''
        self.raw_clips_dir = config['settings']['raw_clips_dir']
        self.download_root = config['settings']['download_root']
        self.raw_clip_paths = []
        self.used_url = {}
        self.fps = 25
        if not os.path.exists(f"{self.root}{self.output_dir}"):
            os.mkdir(f"{self.root}{self.output_dir}")
        if not os.path.exists(f"{self.root}{self.output_dir}{self.raw_clips_dir}"):
            os.mkdir(f"{self.root}{self.output_dir}{self.raw_clips_dir}")

    # [PROD] get crude timestamps
    def getSpeechAndTranscription(self, model="tts-1", voice="ash", transcription_model="whisper-1"):
        client = OpenAI()
        if self.isSameScript == False or os.path.exists(f"{self.root}{self.audio_path}") == False:
            with client.audio.speech.with_streaming_response.create(model=model, voice=voice, input=self.script) as response:
                response.stream_to_file(f"{self.root}{self.audio_path}")
                logging.info(f"{self.root}{self.audio_path} retrieved")
            self.transcription = client.audio.transcriptions.create(file=open(f"{self.root}{self.audio_path}", "rb"), 
                                                                model=transcription_model, 
                                                                response_format="verbose_json", 
                                                                timestamp_granularities=["word"])
            with open(f"{self.root}{self.output_dir}/transcription.pkl", "wb") as f:
                pickle.dump(self.transcription, f)
        else:
            with open(f"{self.root}{self.output_dir}/transcription.pkl", "rb") as f:
                self.transcription = pickle.load(f)
    
    # [PROD] store time stamps
    def getTimestamps(self):
        self.script = self.script.replace("’", "'").replace("!", ".").replace("?", ".").replace('\n', '')
        index, lag = 0, 0
        self.timestamps = []
        for word in self.transcription.words:
            new_index = self.script.lower().find(word.word.lower(), index)
            if new_index >= 0 and (new_index-index) < lag:
                self.timestamps.append({'index': new_index, 
                                        'start': word.start, 
                                        'end': word.end, 
                                        'word': word.word})
                index = new_index + 1
                lag = len(word.word) + 5
            else: lag += len(word.word) + 5
        
    # [PROD] split text into raw sentences with timestamp
    def createSentences(self):
        self.sentences = self.script.split('. ')
        self.durations = [-1] * len(self.sentences)
        for i in range(len(self.sentences)):
            index = self.script.find(self.sentences[i])
            #print(i, index, f"[{self.sentences[i]}]")
            for timestamp in self.timestamps:
                if timestamp['index'] >= index:
                    # start time
                    self.durations[i] = timestamp['start']   
                    # ∆ start times
                    if i > 0:
                        self.durations[i-1] = timestamp['start'] - self.durations[i-1] 
                    break
        # Create a slightly longer duration for [-1] for trimming
        audio_clip = AudioFileClip(f"{self.root}{self.audio_path}")
        self.durations[-1] = audio_clip.duration - self.durations[-1] + 1 
        print(self.durations)
        audio_clip.close()
        
    # [PROD] merge raw sentences that are too short
    def combineSentences(self):
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

    # [PROD] open browser
    def login(self) -> None:
        self.browser = Browser("https://elements.envato.com/sign-in", 3)
        email_xpath = "/html/body/*/main//form/div[1]/div[2]/input"
        pwd_xpath = "/html/body/*/main//form/div[2]/div[2]/input"
        enter_xpath = "/html/body/*/main//form/button"
        self.browser.scroll_find(email_xpath).send_keys(self.email)        
        self.browser.scroll_find(pwd_xpath).send_keys(self.pwd)
        while self.browser.scroll_find(enter_xpath).get_attribute("disabled"):
            time.sleep(1)
        self.browser.driver.execute_script("arguments[0].click();", self.browser.scroll_find(enter_xpath))

    # [Housekeeping] base message for __getKeyword() and __getDescriptions()
    def __getClipPrompt(self, sentence) -> str:
        user_message = ''
        if self.title != '': user_message = f"{user_message}[VIDEO TITLE]\n{self.title}\n"
        if self.main_visual_style != '': user_message = f"{user_message}\n[MAIN VISUAL STYLE]\n{self.main_visual_style}\n"
        user_message = f"{user_message}\n[SENTENCE]\n{sentence}\n"
        return user_message

    # [PROD] produce stock footage keyword
    class Keyword(BaseModel):
        keyword: str
    def getKeyword(self) -> str:
        user_message = self.__getClipPrompt(self.sentences[self.i])
        llmcaller = LLMCaller(self.root, self.model)
        llmcaller.message_to_json('keywordForClip', user_message, self.Keyword)
        keyword = llmcaller.output_json['keyword']
        logging.info(f"[SENTENCE]: {self.sentences[self.i]}")
        return keyword

    # [PROD] Returns a dict with two list: URL and description(str)
    def getDescriptions(self, keyword) -> dict:
        descriptions = []
        description_xpath =["/html/body/*/div/main/div/div[2]/div[2]/div/div/div/div/div/div[2]/div/div/div[1]/div[", "]/div/div[2]/a[1]"]
        if self.durations[self.i] == 0:
            self.browser.driver.get(f"https://elements.envato.com/photos/{keyword}/orientation-landscape")
        else:
            self.browser.driver.get(f"https://elements.envato.com/stock-video/stock-footage/{keyword}/orientation-horizontal/resolution-1080p-(full-hd)/min-length-00:{str(self.durations[self.i])}")
        for j in range(100):
            span = self.browser.scroll_find(str(j+1).join(description_xpath))
            if span is None:
                break
            description = span.get_attribute('innerText')
            url = span.get_attribute('href')
            if url in self.used_url: continue
            descriptions.append({'url': url, 'description': description})
        logging.info(f"keyword: [{keyword.upper()}], secs needed: {round(self.durations[self.i], 3)}, number of results: {len(descriptions)}")
        return descriptions
    
    # [PROD] get URL based on descriptions
    class VideoClip(BaseModel): 
        video_number: int
        video_description: str
    def getURL(self, descriptions):
        user_message = self.__getClipPrompt(self.sentences[self.i])
        video_desciptions = []
        selected_number = -1
        for i, d in enumerate(descriptions): 
            video_desciptions.append(f"{i+1}. {d['description']}\n")
        video_desciptions = ''.join(video_desciptions)
        user_message = f"{user_message}\n[LIST OF VIDEO DESCIPRITONS]\n{video_desciptions}\n"
        while selected_number < 1 or selected_number > len(descriptions):
            llmcaller = LLMCaller(self.root, self.model)
            llmcaller.message_to_json('videoclip', user_message, self.VideoClip)
            selected_number = llmcaller.output_json['video_number']
        logging.info(f"selected_number: {selected_number}, len(descriptions): {len(descriptions)}")
        url = descriptions[selected_number-1]['url']
        logging.info(f"url: {url}")
        self.used_url[url] = True
        return url

    # [PROD] download according to URL
    def download(self, url,
                 init_download_xpath = "/html/body/*/div/main/div/div/div[1]/div[1]/div/div/div/div/div/div[2]/div/div[2]/div/div/div[1]/div[2]/button[1]/span[2]",
                 project_select_box_xpath = f"/html/body/*/div/div/div/div/div/div/fieldset/div/div/div/label/div/div[1]/input",
                 add_and_download_xpath = f"/html/body/*/div/div/div/footer/div[1]/div/div/div[1]/button"):
        initial_files = set(os.listdir(self.download_root))
        self.browser.driver.get(url)
        try:
            self.browser.driver.execute_script("arguments[0].click();", self.browser.scroll_find(init_download_xpath))
            self.browser.driver.execute_script("arguments[0].click();", self.browser.scroll_find(project_select_box_xpath))
            self.browser.driver.execute_script("arguments[0].click();", self.browser.scroll_find(add_and_download_xpath))
        except Exception as e:
            logging.info(f"download error: {e}")
        while True:
            time.sleep(1) 
            current_files = set(os.listdir(self.download_root))
            file_names = current_files - initial_files  # Find new files
            if file_names:
                file_name = file_names.pop()
                if file_name.endswith(".crdownload") or file_name.startswith("."):
                    continue
                return f"/{file_name}"

    # [PROD] move file to output_dir
    def move(self, file_name) -> str:
        file_path = f"{self.download_root}{file_name}"
        destination_path = f"{self.root}{self.output_dir}{self.raw_clips_dir}{file_name}"
        while not os.path.exists(file_path):
            time.sleep(1)
        try:
            time.sleep(0.5)
            subprocess.run(["mv", file_path, destination_path])
        except Exception as e:
            logging.info(f"Error occurred: {e}")
        while not os.path.exists(destination_path):
            time.sleep(1)
        time.sleep(0.5)
        return destination_path

    # [PROD] check is clip is usable
    def isClipUsable(self):
        try:
            clip = VideoFileClip(self.raw_clip_paths[-1])
            clip.close()
            return True
        except Exception as e:
            logging.info(f"[DOWNLOAD ERROR]: {e}")
            self.raw_clip_paths.pop()
            return False

    # [PROD] turn it into 1080p
    def fitRatio(self, duration, target_width=1920, target_height=1080) -> VideoFileClip:
        video_clip = VideoFileClip(self.raw_clip_paths[-1]).subclip(0, self.durations[self.i])
        logging.info(f"original size: {video_clip.size}")
        original_aspect = video_clip.w / video_clip.h
        target_aspect = target_width / target_height
        if original_aspect > target_aspect:
            # Wider than 16:9 -> Crop sides
            new_width = int(video_clip.h * target_aspect)  # Calculate new width to match target aspect
            crop_margin = (video_clip.w - new_width) // 2
            video_clip = video_clip.crop(x1=crop_margin, x2=video_clip.w - crop_margin)
        elif original_aspect < target_aspect:
            # Taller than 16:9 -> Crop top and bottom
            new_height = int(video_clip.w / target_aspect)  # Calculate new height to match target aspect
            crop_margin = (video_clip.h - new_height) // 2
            video_clip = video_clip.crop(y1=crop_margin, y2=video_clip.h - crop_margin)
        video_clip = video_clip.resize((target_width, target_height))
        self.raw_clip_paths[-1] = self.raw_clip_paths[-1][:-4] + '-resized.mp4'
        video_clip.write_videofile(self.raw_clip_paths[-1], codec="libx264", audio_codec="aac")
        video_clip.close()

    # [PROD] combine all clips
    def patch(self):
        raw_clips = [VideoFileClip(raw_clip_path) for raw_clip_path in self.raw_clip_paths]
        final_video = concatenate_videoclips(raw_clips, method="compose")
        logging.info(f"final video size: {final_video.size}")
        audio_clip = AudioFileClip(f"{self.root}{self.audio_path}")
        final_video = final_video.set_audio(audio_clip).subclip(0, audio_clip.duration)  # Trim audio to video length
        final_video.write_videofile(f"{self.root}{self.output_dir}/base.mp4", codec="libx264", audio_codec="aac")
        final_video.close()
        audio_clip.close()
        logging.info(f"{self.output_dir}/base.mp4 rendered.")
    
    def production(self):
        if not self.isThumbnail:
            self.getSpeechAndTranscription()
            self.getTimestamps()
            self.createSentences()
            self.combineSentences()
        else:
            self.sentences = [self.script]
            self.durations = [0]
        self.login()
        for self.i in range(len(self.sentences)):
            descriptions = {}
            while len(descriptions) == 0:
                keyword = self.getKeyword()
                descriptions = self.getDescriptions(keyword)
                if len(descriptions) == 0: continue
                url = self.getURL(descriptions)
                file_name = self.download(url)
                file_root_path = self.move(file_name)
                self.raw_clip_paths.append(file_root_path)
                if self.isThumbnail: return
                if not self.isClipUsable(): descriptions = {}
            self.fitRatio(self.durations[self.i])
        self.browser.driver.quit()
        self.patch()
        
if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.conf')
    os.environ['OPENAI_API_KEY'] = config['settings']['root']
    output_dir = '/data/tests/11'
    isSameScript = True     ##
    cs = ClipScraper(output_dir, '', isSameScript=isSameScript)
    with open(f"{cs.root}/data/tests/short/script.txt", 'r') as f:
        script = f.read()
    cs.script = script
    cs.production()
    with open(f"{cs.root}{cs.output_dir}/clipscraper.pkl", 'wb') as f:
        pickle.dump(cs, f)