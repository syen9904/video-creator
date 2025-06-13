from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import pickle
import logging
import configparser
from llmcaller import LLMCaller
from clipscraper import ClipScraper
from pydantic import BaseModel
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip, ColorClip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OVERLAY_STYLES = {
    "topic": {
        "text_alignment": "center",   # 'left'/'center'/'right'
        "image_alignment": ("center", "center"),  # (x, y)
        "image_coordinates": (120, 300, 1800, 780),  # left_margin, up_margin, right_margin, bottom_margin
        "fade": True
    },
    "toc": {
        "text_alignment": "left",   # 'left'/'center'/'right'
        "image_alignment": ("left", "bottom"),  # (x, y)
        "image_coordinates": (50, 840, 1920, 1030),  # left_margin, up_margin, right_margin, bottom_margin
        "fade": False
    },
    "number_component": {
        "text_alignment": "center",   # 'left'/'center'/'right'
        "image_alignment": ("center", "bottom"),  # (x, y)
        "image_coordinates": (120, 300, 1800, 600),  # left_margin, up_margin, right_margin, bottom_margin
        "fade": True
    },
    "label_component": {
        "text_alignment": "center",   # 'left'/'center'/'right'
        "image_alignment": ("center", "top"),  # (x, y)
        "image_coordinates": (480, 660, 1440, 780),  # left_margin, up_margin, right_margin, bottom_margin
        "fade": False
    },
    "key_phrase": {
        "text_alignment": "center",   # 'left'/'center'/'right'
        "image_alignment": ("center", "center"),  # (x, y)
        "image_coordinates": (120, 300, 1800, 780),  # left_margin, up_margin, right_margin, bottom_margin
        "fade": True
    }
}

class Overlay():
    def __init__(self, output_dir, script, timestamps=[]):
        config = configparser.ConfigParser()
        config.read('config.conf')
        self.root = config['settings']['root']
        self.model = config['settings']['model']
        self.base_path = config['settings']['base_path']
        self.overlay_path = config['settings']['overlay_path']
        self.fps = config.getint('settings', 'fps')
        self.opacity = config.getfloat('settings', 'opacity')
        self.fade_time = config.getfloat('settings', 'fade_time')
        self.font_path = config['settings']['font_path']
        self.font_size = config.getint('settings', 'font_size')
        self.outer_margin = config.getint('settings', 'outer_margin')
        self.line_spacing_factor = config.getint('settings', 'line_spacing_factor')

        self.line_spacing = self.font_size // self.font_size
        self.output_dir = output_dir
        self.script = script
        self.timestamps = timestamps
        self.font_path = self.root + self.font_path
        self.overlays = []
        self.base_clip = VideoFileClip(f"{self.root}{self.output_dir}{self.base_path}")
        self.dimming_clips = []
        self.overlay_clips = []
        self.overlay_photots_dir = f"{self.root}{self.output_dir}/overlay-photos"
        if not os.path.exists(self.overlay_photots_dir): os.mkdir(self.overlay_photots_dir)
        self.video_output_path = f"{self.root}{self.output_dir}{self.overlay_path}"

    def __synchronizeText(self, text):
        return text.replace("’", "'").replace("!", ".").replace("?", ".").replace(',', '.').lower()

    def __extract(self, prompt_file, user_message, response_format, output_key='n/a') -> list:
        quoteMatches = False
        while not quoteMatches:
            quoteMatches = True
            llmcaller = LLMCaller(self.root, self.model)
            llmcaller.message_to_json(prompt_file, user_message, response_format)
            if output_key == 'n/a': llmcaller.output_json = {output_key: [llmcaller.output_json]}
            for output in llmcaller.output_json[output_key]:
                quote = self.__synchronizeText(output['quote_component'])[:-1]
                output['start_index'] = self.__synchronizeText(self.script).find(quote)
                if output['start_index'] == -1:
                    print(f"\n\n{quote}\n{self.script[self.script.find(quote[:10]):self.script.find(quote[:10])+len(quote)]}")
                    import time
                    time.sleep(10)
                    quoteMatches = False
                    break
                output['end_index'] = output['start_index'] + len(output[ 'quote_component'])
        return llmcaller.output_json[output_key]
    
    def __getOverlayTime(self, raw_overlay, key_name):
        self.overlays.append({"category": key_name,
                              "start_time": -1,
                              "end_time": -1,
                              "content": raw_overlay[key_name]})
        for timestamp in self.timestamps:
            if self.overlays[-1]['start_time'] == -1 and timestamp['index'] >= raw_overlay['start_index']:
                self.overlays[-1]['start_time'] = round(timestamp['start'], 3)
            if timestamp['index'] >= raw_overlay['end_index']:
                self.overlays[-1]['end_time'] = round(timestamp['start'], 3)
                break
        print(round(self.overlays[-1]['end_time']-self.overlays[-1]['start_time'], 1), raw_overlay)

    """ 單一變數extraction = total failure
    class Variables(BaseModel):
        variables: list["Overlay.Variable"]
    class VariableExistence(BaseModel):
        does_variable_exist: bool
    class VariableRepetition(BaseModel):
        was_variable_mentioned: bool
    def getVariables(self):
        logging.disable()
        llmcaller = LLMCaller(self.root, self.model)
        for sentence in self.sentences:
            user_message = ""
            user_message = f"{user_message}[Article]\n{sentence}\n\n"
            llmcaller.message_to_json('getVariables', user_message, self.Variables)
            vs = llmcaller.output_json['variables'].copy()
            for v in vs:
                mentioned = False
                if len(vs) == 1:
                    user_message = f"[Variable]\nvalue: {v['value']}, unit: {v['unit']}\n\n[Sentence]\n{sentence}"
                    llmcaller.message_to_json('doesVariableExist', user_message, self.VariableExistence)
                    if not llmcaller.output_json['does_variable_exist']: 
                        print(f"==========={sentence}", end="\n")
                        print(user_message)
                elif self.script.find(sentence) > 0:
                    user_message = f"[Variable]\nvalue: {v['value']}, unit: {v['unit']}\n\n[Sentence]\n{self.script[:self.script.find(sentence)]}"
                    llmcaller.message_to_json('wasVariableMentioned', user_message, self.VariableRepetition)
                    if llmcaller.output_json['was_variable_mentioned']:
                        print('&& ', end="")
                        llmcaller.message_to_json('wasVariableMentioned', user_message, self.VariableRepetition)
                        mentioned = llmcaller.output_json['was_variable_mentioned']
                print(f"{v['name']:<{40}}\t{v['value']} {v['unit']}", end='\t')
                if mentioned: print(f"MENTIONED", end="")
                print('')
            print(f"\n======{sentence}\n")
"""

    class CalculationExistence(BaseModel):
        doesTextContainArithemticCalculation: bool
        quote_component: str
    def isThereCalculation(self) -> None:
        llmcaller = LLMCaller(self.root, self.model)
        llmcaller.message_to_json('isThereCalculation', self.script, self.CalculationExistence)
        if llmcaller.output_json['doesTextContainArithemticCalculation']:
            llmcaller.message_to_json('isThereCalculation', llmcaller.output_json['quote_component'], self.CalculationExistence)
        if llmcaller.output_json['doesTextContainArithemticCalculation']:
            self.getCalculation()
    # answer with the json format

    class Variable(BaseModel):
        name: str
        value: float
        unit: str
        full_context_of_variable: str
    class Calculation(BaseModel):
        general_equation: str
        numerical_expression: str
        input_variables: list["Overlay.Variable"]
        output_variable: "Overlay.Variable"
    class CalculationList(BaseModel):
        calculationList: list["Overlay.Calculation"]
    class CalculationCheck(BaseModel):
        calculation: str
        arithmetic_or_contextual_error: bool
        explanation: str
    class CalculationCheckList(BaseModel):
        calculationList: list["Overlay.CalculationCheck"]
    def getCalculation(self) -> None:
        llmcaller = LLMCaller(self.root, self.model)
        llmcaller.message_to_json('getCalculations', self.script, self.CalculationList)
        calculationList = llmcaller.output_json['calculationList']
        user_message = ""
        user_message = f"{user_message}[Calculation]\n"
        for calculationGroup in calculationList:
            print(calculationGroup['numerical_expression'])
            #calculationGroup['quote_component'] = self.getCalculationQuote(calculationGroup)
            user_message = f"{user_message}{calculationGroup['numerical_expression']}\n"
        user_message = f"{user_message}\n[Article]\n{self.script}\n\n"
        print(user_message)
        llmcaller.message_to_json('checkCalculation', self.script, self.CalculationCheckList)
        for c in llmcaller.output_json['calculationList']:
            print(f"{c['arithmetic_or_contextual_error']}\t{c['calculation']}\t{c['explanation']}")
        for i, calculationGroup in enumerate(llmcaller.output_json['calculationList'][:0]):
            #calculationGroup['quote_component'] = self.getCalculationQuote(calculationGroup)
            #calculationGroup['output_variable']['full_context_of_variable'] = calculationGroup['quote_component']
            calculationGroup['parent'] = -1
            j = i - 1
            while j >= 0 and False:
                random_variable = llmcaller.output_json['calculationList'][j]['output_variable']
                if self.isFormulaDependent(random_variable, calculationGroup, ['general_equation', 'input_variables', 'numerical_expression', 'quote_component']):
                    calculationGroup['parent'] = j
                    break
                j -= 1
                if j == -1 and False:
                    print(f"\n{calculationGroup['input_variables']}\n {calculationGroup['quote_component']}")
                    self.reSearchCalculation(calculationGroup)
            for key in list(calculationGroup.keys())[1:2]:
                if type(calculationGroup[key]) == str: 
                    #print(f"{llmcaller.output_json['calculationList'][calculationGroup['parent']]['output_variable']['value']}\t{calculationGroup[key]}")
                    print(f"{calculationGroup[key]}")
                elif type(calculationGroup[key]) == list:
                    for item in calculationGroup[key]: print(list(item.values()))
                else: print(list(calculationGroup[key].values()))
        for i in range(0):
            user_message = ""
            user_message = f"{user_message}[orinigally extracted calculations]\n{llmcaller.output_json}\n\n"
            user_message = f"{user_message}[article]\n{self.script}\n\n"
            llmcaller.message_to_json('reGetCalculations', user_message, self.CalculationList)
            for i, calculationGroup in enumerate(llmcaller.output_json['calculationList']):
                for key in list(calculationGroup.keys())[1:2]:
                    print(f"{calculationGroup[key]}", end='\t')
                print('')
    class FormulaDependency(BaseModel):
        is_the_random_variable_an_input_variable_for_the_given_formula: bool
    def isFormulaDependent(self, random_variable, calculationGroup, keys) -> None:
        logging.disable()
        user_message = ""
        user_message = f"{user_message}[random variable extracted from article]\n{random_variable}\n\n"
        for key in keys:
            user_message = f"{user_message}[{key} of the calculation]\n{calculationGroup[key]}\n\n"
        llmcaller = LLMCaller(self.root, self.model)
        llmcaller.message_to_json('isFormulaDependent', user_message, self.FormulaDependency)
        return llmcaller.output_json['is_the_random_variable_an_input_variable_for_the_given_formula']

    class CalculationQuote(BaseModel):
        quote_component: str
    def getCalculationQuote(self, calculation):
        logging.disable()
        user_message = ""
        user_message = f"{user_message}[Calculation]\n{calculation}\n\n"
        user_message = f"{user_message}[Article]\n{self.script}\n\n"
        return self.__extract('getCalculationQuote', user_message, self.CalculationQuote)[0]['quote_component']

    class VariableMentioned(BaseModel):
        was_variable_mentioned: bool
        quote_component: str
    class VariableCalculated(BaseModel):
        was_variable_obtained_through_arithmetic_computation: bool
        quote_component: str
    class CalculationWithQuote(BaseModel):
        calculation: "Overlay.Calculation"
        quote_component: str
    def reSearchCalculation(self, calculationGroup):
        llmcaller = LLMCaller(self.root, self.model)
        for variable in calculationGroup['input_variables']:
            user_message = ""
            user_message = f"{user_message}[Variable]\n{variable}\n\n"
            user_message = f"{user_message}[Article]\n{self.script[:self.__synchronizeText(self.script).find(self.__synchronizeText(calculationGroup['quote_component'])[:-1])]}\n\n"
            llmcaller.message_to_json('wasVariableMentioned', user_message, self.VariableMentioned)
            mentioned = llmcaller.output_json['was_variable_mentioned']
            if mentioned: 
                print(f"[MENTIONED] {llmcaller.output_json['quote_component']}")
                #llmcaller.model = 'o3-mini'
                llmcaller.message_to_json('wasVariableCalculated', user_message, self.VariableCalculated)
                calculated = llmcaller.output_json['was_variable_obtained_through_arithmetic_computation']
                if calculated:
                    print(f"[CACULATED] {llmcaller.output_json}")
                    llmcaller.message_to_json('getSingleCalculation', user_message, self.CalculationWithQuote)
                    print(llmcaller.output_json)
                else: 
                    print(user_message)


    class Statistic(BaseModel):
        number_component: str
        label_component: str
        quote_component: str
    class Statistics(BaseModel):
        statistics: list["Overlay.Statistic"]
    def getStats(self) -> None:
        self.statistics = self.__extract('getStats', self.script, self.Statistics, 'statistics')
        for statistic in self.statistics:
            #print(f"key_statistic: {statistic['key_statistic']}, key_statistic_name: {statistic['key_statistic_name']}")
            self.__getOverlayTime(statistic, 'number_component')
            self.overlays.append(self.overlays[-1].copy())
            self.overlays[-1]["category"] = "label_component"
            self.overlays[-1]["content"] = statistic["label_component"]

    class KeyPhrase(BaseModel):
        key_phrase: str
        quote_component: str
    class KeyPhrases(BaseModel):
        key_phrases: list["Overlay.KeyPhrase"]
    def getKeyPhrases(self) -> None:
        self.keyPhrases = self.__extract('getKeyphrase', self.script, self.KeyPhrases, 'key_phrases')
        for keyPhrase in self.keyPhrases:
            #print(f"quote: {keyPhrase['quote']}, key_phrase: {keyPhrase['key_phrase']}")
            self.__getOverlayTime(keyPhrase, "key_phrase")
            for overlay in self.overlays[:-1]:
                if overlay['category'] == 'toc': continue
                if not (self.overlays[-1]['end_time'] <= overlay['start_time'] or self.overlays[-1]['start_time'] >= overlay['end_time']):
                    print(f"conflict: {overlay}. {self.overlays[-1]}")
                    self.overlays.pop()
                    break

    """
    def toc(self):
        toc = f"{self.topic}"
        for i, core_concept in enumerate(self.core_concepts):
            toc = f"{toc}\n{i+1}. {core_concept['descriptive_title']}"
        self.overlays.append({"category": "toc",
                              "start_time": self.durations[0],
                              "end_time": self.base_clip.duration,
                              "content": toc})
        self.overlays.append({"category": "topic",
                              "start_time": self.fade_time,
                              "end_time": self.durations[0],
                              "content": self.topic})

    class CoreAndItsQuote(BaseModel): 
        core_concept: str
        quote: str
    class CoresAndTheirQuotes(BaseModel):
        core_concepts: list["Overlay.CoreAndItsQuote"]
    def introSplit(self) -> None:
        user_message = ''
        user_message = f"{user_message}[CORE CONCEPTS]\n"
        for i, core_concept in enumerate(self.core_concepts):
            user_message = f"{user_message}{i+1}. {core_concept['descriptive_title']}\n"
        user_message = f"{user_message}\n[YOUTUBE INTRO]\n{self.script}"
        
        # make sure output in correct core_concept sequence
        rightSequence = False
        while not rightSequence:
            self.core_concepts = self.__extract('introSplit', user_message, self.CoresAndTheirQuotes, 'core_concepts')
            rightSequence = True
            for i, core_concept in enumerate(self.core_concepts):
                if i > 0 and core_concept['start_index'] < self.core_concepts[i-1]['start_index']:
                    rightSequence = False
                    break
        toc = '\n'.join([f"{i+1}.{core_concept['core_concept']}" for i, core_concept in enumerate(self.core_concepts)])
        for i, core_concept in enumerate(self.core_concepts):
            self.overlays.append({"category": "toc",
                                  "start_time": -1,
                                  "end_time": -1,
                                  "content": f"{i+1}.{core_concept['core_concept']}\n{toc}"})
            for timestamp in self.timestamps:
                if self.overlays[-1]['start_time'] == -1 and timestamp['index'] >= core_concept['start_index']:
                    self.overlays[-1]['start_time'] = round(timestamp['start'], 3)
                if self.overlays[-1]['start_time'] > 0:
                    if i == 0: break
                    self.overlays[-2]['end_time'] = self.overlays[-1]['start_time'] - 0.001
                    break
        for timestamp in self.timestamps:
            if timestamp['index'] >= self.core_concepts[-1]['end_index']:
                self.overlays[-1]['end_time'] = round(timestamp['start'], 3)
                break
    """

    def getDimension(self, texts_and_colors):
        temp_image = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp_image)
        max_text_width = 0
        font_heights = []
        for line in texts_and_colors:
            bbox = draw.textbbox((0, 0), line['text'], font=ImageFont.truetype(self.font_path, self.font_size))  # Get bounding box of the text
            font_heights.append(bbox[3] - bbox[1])  # Height of the current line
            max_text_width = max(max_text_width, bbox[2] - bbox[0])
        image_width = max_text_width + 2 * self.outer_margin
        image_height = (len(texts_and_colors) * max(font_heights) + (len(texts_and_colors) - 1) * self.line_spacing) + 2 * self.outer_margin
        return image_width, image_height, max(font_heights)
    def create_image_with_text(self, texts_and_colors, output_path, bg_color=(255, 255, 255, 0), alignment='left', stroke_width=0, stroke_color=(0, 0, 0, 255)):
        output_path = f"{self.overlay_photots_dir}{output_path}"
        image_width, image_height, max_font_height = self.getDimension(texts_and_colors)
        image = Image.new('RGBA', (image_width, image_height), bg_color)
        draw = ImageDraw.Draw(image)
        current_y = self.outer_margin

        # Draw each line of text with stroke
        for i, line in enumerate(texts_and_colors):
            text_color = texts_and_colors[i]['color']
            font = ImageFont.truetype(self.font_path, self.font_size)
            bbox = draw.textbbox((0, 0), line['text'], font=font)  # Get bounding box
            text_width = bbox[2] - bbox[0]

            # get x
            if alignment == 'center': text_position_x = (image_width - text_width) // 2
            elif alignment == 'left': text_position_x = self.outer_margin
            elif alignment == 'right': text_position_x = image_width - text_width - self.outer_margin
            else: raise ValueError("Invalid alignment. Choose 'center', 'left', or 'right'.")
            text_position = (text_position_x, current_y)

            # Draw the stroke and TRUE text
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx != 0 or dy != 0:  # Skip the center position
                        draw.text((text_position[0] + dx, text_position[1] + dy), line['text'], font=font, fill=stroke_color)
            draw.text(text_position, line['text'], font=font, fill=text_color)
            
            current_y += max_font_height + self.line_spacing
        
        image.save(output_path)
        return image
    def add_photo(self, overlay):
        texts_and_colors = []
        lines = overlay["content"].split('\n')
        for i, line in enumerate(lines):
            texts_and_colors.append({"text": line, "color": (255, 255, 255, 63)})
            for char in texts_and_colors[-1]['text']: 
                if ord(char) > 127: texts_and_colors[-1]['text'] = texts_and_colors[-1]['text'].replace(char, "—")
            if len(lines) == 1:
                texts_and_colors[-1]["color"] = (255, 255, 255, 255)
            elif (i > 0 and line.find(lines[0]) >= 0):
                texts_and_colors[-1]["color"] = (255, 255, 255, 127)
                texts_and_colors.pop(0)
        image_clip = ImageClip(np.array(self.create_image_with_text(texts_and_colors, f"/{overlay['category']}-{str(overlay['start_time']).replace('.', '-')}.png")))
        
        # 计算视频框的宽高
        box_left, box_top, box_right, box_bottom = OVERLAY_STYLES[overlay['category']]['image_coordinates']
        box_width = box_right - box_left
        box_height = box_bottom - box_top
        # 加载图片并等比例缩放以适应框
        image_aspect_ratio = image_clip.w / image_clip.h
        box_aspect_ratio = box_width / box_height        
        if image_aspect_ratio > box_aspect_ratio:
            image_clip = image_clip.resize(width=box_width)
        else:
            image_clip = image_clip.resize(height=box_height)
        
        # 计算图片在框内的位置（根据对齐方式）
        image_x = 0
        if OVERLAY_STYLES[overlay['category']]['image_alignment'][0] == "left": image_x = box_left
        elif OVERLAY_STYLES[overlay['category']]['image_alignment'][0] == "right": image_x = box_right - image_clip.w
        else: image_x = box_left + (box_width - image_clip.w) / 2
        image_y = 0
        if OVERLAY_STYLES[overlay['category']]['image_alignment'][1] == "top": image_y = box_top
        elif OVERLAY_STYLES[overlay['category']]['image_alignment'][1] == "bottom": image_y = box_bottom - image_clip.h
        else: image_y = box_top + (box_height - image_clip.h) / 2
        
        start_time = overlay['start_time']
        end_time = overlay['end_time']
        image_clip = (image_clip
                      .set_position((image_x, image_y))
                      .set_start(start_time)
                      .set_end(end_time)
                      .fadein((end_time-start_time)/8)
                      .fadeout((end_time-start_time)/8))
        
        if OVERLAY_STYLES[overlay['category']]['fade']:
            dimming_overlay = (ColorClip(size=self.base_clip.size, color=(0, 0, 0), ismask=False)
                               .set_opacity(self.opacity)
                               .set_start(max(0, start_time-self.fade_time))
                               .set_end(min(self.base_clip.duration, end_time+self.fade_time))
                               .crossfadein(self.fade_time)
                               .crossfadeout(self.fade_time))
            self.dimming_clips.append(dimming_overlay)
            dimming_overlay.close()
        
        self.overlay_clips.append(image_clip)
        image_clip.close()

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.conf')
    os.environ['OPENAI_API_KEY'] = config['settings']['root']
    root = '/Users/apple/Desktop/sd/repo'
    output_dir = '/data/tests/11'
    with open(f"{root}/data/tests/script.txt", 'r') as f:
        script = f.read()
    cs = ClipScraper(output_dir, script, isSameScript=True)
    cs.getSpeechAndTranscription()
    cs.getTimestamps()
    """
    with open(f"{root}/data/tests/11/clipscraper.pkl", "rb") as f:
        cs = pickle.load(f)
    """
    timestamps = cs.timestamps

    print(script)
    o = Overlay(output_dir, script, timestamps)
    o.getStats() #key_statistic, key_statistic_name
    o.getKeyPhrases() #key_phrases
    print(len(o.overlays))
    #o.introSplit()
    for overlay in o.overlays:
        o.add_photo(overlay)
    print(len(o.dimming_clips), len(o.overlay_clips))
    #CompositeVideoClip([o.base_clip]+o.dimming_clips+o.overlay_clips).write_videofile(o.video_output_path, codec='libx264', audio_codec='aac')
    CompositeVideoClip([o.base_clip]+o.overlay_clips).write_videofile(o.video_output_path, codec='libx264', audio_codec='aac')