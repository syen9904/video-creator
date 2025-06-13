import json
from browser import Browser
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from read_text import read_text
from selenium.webdriver.common.by import By

class TranscriptParser:
    def __init__(self, detailed_config, raw_data, length=10, root_url = 'https://www.youtube.com'):
        self.title = raw_data['original_title']
        self.length = length
        self.root_url = root_url
        self.output = []
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.parse()
        
    def url_to_transcript(self, video_id):
        raw_transcript = YouTubeTranscriptApi.get_transcript(video_id, languages = ['en'])
        transcript = ''
        for t in raw_transcript:
            transcript = f"{transcript} {t['text']}"
        return transcript

    def parse(self):
        browser = Browser(self.root_url)
        input_xpath = "/html/body/ytd-app/div[1]/div[2]/ytd-masthead/div[4]/div[2]/yt-searchbox/div[1]/form/input"
        text_area = browser.driver.find_element(By.XPATH, input_xpath)
        text_area.send_keys(f"{self.title}\n")
        i = 0
        while i < self.length:
            i += 1
            video_xpath = f"/html/body/ytd-app/div[1]/ytd-page-manager/ytd-search/div[1]/ytd-two-column-search-results-renderer/div/ytd-section-list-renderer/div[2]/ytd-item-section-renderer/div[3]/ytd-video-renderer[{i}]/div[1]/div/div[1]/div/h3/a"
            title = browser.scroll_find(video_xpath).text
            url = browser.scroll_find(video_xpath).get_attribute("href")
            if url.find('https://www.youtube.com/shorts') == 0 or self.title == title:
                logging.info(f"skipped: {url.replace('https://www.youtube.com', '')}")
                self.length += 1
                continue
            video_id = url.replace('https://www.youtube.com/watch?v=', '')[:11]
            try:
                YouTubeTranscriptApi.list_transcripts(video_id).find_transcript(['en'])
            except:
                logging.info(f"skipped: {video_id} because no transcript")
                self.length += 1
                continue
            self.output.append({'title': title, 'script': self.url_to_transcript(video_id)})
            logging.info(f"appended: {video_id}")

        
        browser.driver.quit()

if __name__ == '__main__':
    root = '/Users/apple/Desktop/sd/repo'
    dir = '/scripts/graph'
    original_title = '好機車 黑人'
    length = 5
    detailed_config = {
        'root': root,
        'model': 'model',
        'output_type': 'material',
        'message_sequence': ['original_title']
    }
    raw_data = {'original_title': original_title}
    
    material = TranscriptParser(detailed_config, raw_data, length)

    #with open(root+dir+'/examples/material.json', 'w', encoding='utf-8') as f:
    #    json.dump(material.output, f, ensure_ascii=False, indent=2)
    
    print(len(json.dumps(material.output)), len(material.output))