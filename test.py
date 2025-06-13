import os
import pickle
import logging
from featuredecider import Overlay
from textprocessor import TextProcessor
from paragraph import Paragraph
from clipscraper import ClipScraper
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip, ColorClip
import configparser
#logging.disable()
config = configparser.ConfigParser()
config.read('config.conf')
os.environ['OPENAI_API_KEY'] = config['settings']['root']
root = '/Users/apple/Desktop/sd/repo'
working_dir = '/data/tests'
model = 'gpt-4o-mini'
script_file_name = "script.txt"
transcription_file_name = "transcription.pkl"
for r, d, fs in os.walk(f"{root}{working_dir}"):
    for f in fs:
        if f == script_file_name:
            if (f"{r.replace(f'{root}{working_dir}', '')}") != '/perpetual-contracts': continue
            with open(f"{r}/{script_file_name}", 'r') as f:
                script = f.read()
            with open(f"{r}/{transcription_file_name}", 'rb') as f:
                transcription = pickle.load(f)
            output_dir = r.replace(root, '')
            print(output_dir, len(script), len(transcription.words))
            cs = ClipScraper(output_dir, script)
            cs.transcription = transcription
            cs.getTimestamps()
            cs.createSentences()
            cs.combineSentences()
            """
            print(len(cs.sentences))
            for sentence in cs.sentences:
                print(sentence)
            import time
            time.sleep(2000)
            """

            timestamps = cs.timestamps
            o = Overlay(output_dir, script, timestamps)
            o.sentences = cs.sentences
            o.getCalculation()
            #o.getStats()
            #o.getKeyPhrases()
            #print(len(o.overlays))
            #for overlay in o.overlays: o.add_photo(overlay)
            #print(len(o.dimming_clips), len(o.overlay_clips))
            #CompositeVideoClip([o.base_clip]+o.dimming_clips+o.overlay_clips).write_videofile(o.video_output_path, codec='libx264', audio_codec='aac')
            #CompositeVideoClip([o.base_clip]+o.overlay_clips).write_videofile(o.video_output_path, codec='libx264', audio_codec='aac')
