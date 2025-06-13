import os
import time
import logging
from openai import OpenAI
import math
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip, ColorClip
from moviepy.video.fx.margin import margin
import configparser

class VideoProcessor():
    def __init__(self, root):
        self.root = root
    
    def fit_ratio(self, video_clip, target_width=1920, target_height=1080) -> VideoFileClip:
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
        return video_clip.resize((target_width, target_height))

    def add_video(self, output_dir, video_path, audio_path, output_path) -> None:
        audio_clip = AudioFileClip(f"{self.root}{output_dir}{audio_path}")
        if video_path.endswith('.png'):
            video_clip = self.fit_ratio(ImageClip(f"{self.root}{output_dir}{video_path}").set_duration(1).set_fps(24))
        else:
            video_clip = self.fit_ratio(VideoFileClip(f"{self.root}{output_dir}{video_path}"))
        video_clip = concatenate_videoclips([video_clip]*math.ceil(audio_clip.duration/video_clip.duration))
        video_clip = video_clip.subclip(0, audio_clip.duration).set_audio(audio_clip)
        video_clip.write_videofile(f"{self.root}{output_dir}{output_path}", codec='libx264', audio_codec='aac')
        logging.info(f"{video_clip.w}:{video_clip.h}, {video_clip.duration} sec")
        audio_clip.close()
        video_clip.close()

    def add_photo(self, output_dir, image_path, video_path, output_path, start_time, end_time, box,
    align="center",  # Alignment: "center", "top_left", "top_right", "bottom_left", "bottom_right"
    fade_time=0,
    duration=None,  # Duration to show the image (None = full video duration)
    fps=30,  # Output video FPS
    ) -> None:
        video_clip = VideoFileClip(f"{self.root}{output_dir}{video_path}")
        image_clip = ImageClip(f"{self.root}{output_dir}{image_path}")

        # 计算视频框的宽高
        box_left, box_right, box_top, box_bottom = box
        box_width = box_right - box_left
        box_height = box_bottom - box_top

        # 加载图片并等比例缩放以适应框
        image_aspect_ratio = image_clip.w / image_clip.h
        box_aspect_ratio = box_width / box_height

        print(image_clip.size, video_clip.size)
        if image_aspect_ratio > box_aspect_ratio:
            image_clip = image_clip.resize(width=box_width)
        else:
            image_clip = image_clip.resize(height=box_height)
        print(image_clip.size, video_clip.size)

            # 计算图片在框内的位置（根据对齐方式）
        image_x, image_y = 0, 0
        if align == "center":
            image_x = box_left + (box_width - image_clip.w) / 2
            image_y = box_top + (box_height - image_clip.h) / 2
        elif align == "top_left":
            image_x = box_left
            image_y = box_top
        elif align == "top_right":
            image_x = box_right - image_clip.w
            image_y = box_top
        elif align == "bottom_left":
            image_x = box_left
            image_y = box_bottom - image_clip.h
        elif align == "bottom_right":
            image_x = box_right - image_clip.w
            image_y = box_bottom - image_clip.h
        else:
            raise ValueError(f"Unsupported alignment: {align}")

        image_clip = (image_clip.set_start(start_time+fade_time).set_end(end_time-fade_time).set_position((image_x, image_y)))
        if fade_time > 0:
            dimming_overlay = (
                ColorClip(size=video_clip.size, color=(0, 0, 0), ismask=False)
                .set_opacity(0.5)
                .set_start(start_time)
                .set_end(end_time)
                .crossfadein(fade_time)  
                .crossfadeout(fade_time)  
            )
            final_clip = CompositeVideoClip([video_clip, dimming_overlay, image_clip])    
        else:
            final_clip = CompositeVideoClip([video_clip, image_clip])    
        final_clip.write_videofile(f"{self.root}{output_dir}{output_path}", codec='libx264', audio_codec='aac')
    
        video_clip.close()
        image_clip.close()
        final_clip.close()

    def merge(self, working_dir, start, end, clip_names = ['/output_clip.mp4'], output_name = '/output.mp4') -> float:
        video_clips = []
        for i in range(start, end):
            clip_path = ''
            for clip_name in clip_names:
                clip_path = f"{self.root}{working_dir}/{i}{clip_name}"
                if os.path.exists(clip_path): break
            video_clips.append(VideoFileClip(f"{self.root}{working_dir}/{i}{clip_name}"))
        final_video = concatenate_videoclips(video_clips, method="compose")
        final_video.write_videofile(f"{self.root}{working_dir}{output_name}", codec='libx264', audio_codec='aac')
        duration = final_video.duration

        for video_clip in video_clips: video_clip.close()
        final_video.close()
        return duration
    
if __name__ == '__main__':
    root = '/Users/apple/Desktop/sd/repo'
    output_dir = '/data/tests'
    vp = VideoProcessor(root)
    raw_clip = '/crypto-currency-bitcoins-and-american-investment-2023-11-27-05-18-31-utc.mov'
    image_path = '/black.png'
    video_path = '/output.mp4'
    audio_path = '/speech.mp3'
    output_path = '/with_img.mp4'
    start_time = 1
    end_time = 10
    x = 1
    image_size = None
    position=(200, 100)
    #vp.add_video(output_dir+'/1', video_path='/black.png', audio_path=audio_path, output_path='/with_black.mp4')
    
    # html2image 純網頁截圖
    """
    from html2image import Html2Image
    def capture_webpage_content_with_html2image(url, output_path, width = 600, height = 700):
        hti = Html2Image()
        hti.browser_width = 200
        hti.browser_height = 1200
        print(hti.size)
        output_dir = "/".join(output_path.split("/")[:-1])  # Extract directory
        output_filename = output_path.split("/")[-1]  # Extract filename
        print(output_dir, output_filename)
        hti.output_path = output_dir
        hti.screenshot(url=url, save_as=output_filename, size=(width, height))
        print(f"截图已保存为 {output_path}")
    # 调用函数
    desti = f"{root}{output_dir}/screenshot.png"
    print(desti)
    capture_webpage_content_with_html2image("https://github.com/harry0703/MoneyPrinterTurbo/tree/main", desti)
    """
    
    # 測試碟圖功能
    """
    vp.add_photo(output_dir+'/1', image_path='/sst.png', video_path='/output.mp4', output_path='/with_thumbnail.mp4',
                  start_time=start_time, end_time=end_time,     box=(100, 1820, 216, 1080-216),  # 框的范围
    align="center",  # 图片居中对齐
    duration=5,  # 图片持续时间 5 秒
    fps=30  # 输出视频帧率
    )
    """
    
    # 標題打上去
    config = configparser.ConfigParser()
    config.read('config.conf')
    os.environ['OPENAI_API_KEY'] = config['settings']['root']
    from textprocessor import TextProcessor, LLMCaller
    from imagecreator import ImageCreator
    import json
    model = 'gpt-4o-mini'
    user_message = "why it bitcoin so popular?"
    font_path = "/arial-mt-extra-bold.ttf"
    font_size = 360
    bg_color = (0,0,0,0)
    tp = TextProcessor(root, '/data/tests', model, user_message)
    tp.content = json.loads(LLMCaller(root, model).read_text("/data/tests/content.json"))
    tp.getSentences()
    ip = ImageCreator(root, output_dir, font_path)
    core_num = 0
    outro = tp.content['script']['outro']
    output_end = 6
    for i, sentence in enumerate(tp.sentences[:output_end]):
        if i==0:continue
        
        text_and_settings = []
        box_align = 'bottom_left' 
        photo_alignment = 'left'
        fade_time = 0
        box = (50, 1920, 840, 1080-50)
        fade_time=0

        is_topic = False
        if i==1: 
            text = [tp.content['title']]
            photo_alignment = 'center'
            is_topic = True
        if i == 2:
            text = []
            for j, core_concept in enumerate(tp.content['script']['core_concepts']):
                text.append(f"{j+1}. {core_concept['descriptive_title']}")
            is_topic = True
        try:
            if sentence.find(tp.content['script']['core_concepts'][core_num]['full_declarative_sentence'].split('. ')[0])>=0:
                text =[f"{core_num+1}. {tp.content['script']['core_concepts'][core_num]['descriptive_title']}"]
                photo_alignment = 'center'
                core_num += 1
                is_topic = True
        except:
            if sentence.find(outro.split('. ')[0]) >= 0: core_num += 1
        if is_topic:
            text_color = (255, 255, 255, 255)
            for line in text:
                text_and_settings.append({'text': line, 'font_size': font_size, 'text_color': text_color})
            box_align = 'center' 
            box = (100, 1920-100, 100, 1080-100)
            fade_time=0.5
        else:
            for j, core_concept in enumerate(tp.content['script']['core_concepts']):
                text_color = (255, 255, 255, 64)
                if j + 1 == core_num:
                    text_color = (255, 255, 255, 255)
                text_and_settings.append({'text': f"{j+1}. {core_concept['descriptive_title']}", 'font_size': font_size, 'text_color': text_color})
        ip.create_image_with_text(text_and_settings, f"/{i}/menu.png", bg_color, font_size // 6, font_size // 2, photo_alignment)
        temp = VideoFileClip(f'{root}{output_dir}/{i}/output.mp4')
        end = temp.duration
        temp.close()
        vp.add_photo(f"{output_dir}/{i}", "/menu.png", "/output.mp4", "/with_menu.mp4", 0, end, box, box_align, fade_time)
    
    vp.merge(output_dir, 1, output_end, ['/with_menu.mp4', '/output.mp4'])
    """
    """