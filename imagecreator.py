from PIL import Image, ImageDraw, ImageFont
from featuredecider import Overlay

class ImageCreator():
    def __init__(self, root, output_dir, font_path, overlay):
        self.root = root
        self.output_dir = output_dir
        self.overlay = overlay
        self.font_path = root + font_path
        self.font_size = 360
        self.outer_margin = self.font_size // 2
        self.line_spacing = self.font_size // 6
    """
    def create_plain_color_image(self, output_path, color, size):
        image = Image.new('RGBA', size, color)
        image.save(f'{self.root}{self.output_dir}{output_path}')
        print(f"Image created and saved to {self.root}{self.output_dir}{output_path}")
    """

    def __getDimension(self, text_and_colors):
        temp_image = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp_image)
        max_text_width = 0
        font_heights = []
        for line in text_and_colors:
            bbox = draw.textbbox((0, 0), line['text'], font=ImageFont.truetype(self.font_path, self.font_size))  # Get bounding box of the text
            font_heights.append(bbox[3] - bbox[1])  # Height of the current line
            max_text_width = max(max_text_width, bbox[2] - bbox[0])
        image_width = max_text_width + 2 * self.outer_margin
        image_height = (len(text_and_colors) * max(font_heights) + (len(text_and_colors) - 1) * self.line_spacing) + 2 * self.outer_margin
        return image_width, image_height, max(font_heights)
    
    def create_image_with_text(self, text_and_colors, output_path, bg_color, alignment='left', stroke_width=0, stroke_color=(0, 0, 0, 255)):
        output_path = self.root + self.output_dir + output_path
        image_width, image_height, max_font_height = self.__getDimension(text_and_colors)
        image = Image.new('RGBA', (image_width, image_height), bg_color)
        draw = ImageDraw.Draw(image)
        current_y = self.outer_margin

        # Draw each line of text with stroke
        for line in text_and_colors:
            font_size = line['color']
            text_color = line['color']
            font = ImageFont.truetype(self.font_path, font_size)
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
        print(f"Image with size {image.size} saved to {output_path}")


    def __splitSentence(self, words, number_of_lines):
        if number_of_lines <= 1 : return len(' '.join(words)), [' '.join(words)]
        last_line = ['']
        remaining_lines = [''] * (number_of_lines-1)
        for i, word in enumerate(words):
            last_line = ' '.join(words[-i-1:])
            max_len, remaining_lines = self.__splitSentence(words[:-i-1], number_of_lines-1)
            if max_len <= len(last_line):
                return len(last_line), remaining_lines+[last_line]
    def __getThumbnailText(self, ratio, words, font_size, thumbnail_color, outer_margin, line_spacing):
        text = words
        for i in range(1, len(words)):
            text = (self.__splitSentence(words, i))[1]
            text_and_colors = []
            for t in text:
                text_and_colors.append({'text': t, 'font_size': font_size, 'text_color': thumbnail_color})
            w, h, f = self.__getDimension(text_and_colors, outer_margin, line_spacing)
            if h/w >= (9/16)*ratio: break
        text_and_colors = []
        for t in text:
            text_and_colors.append({'text': t, 'font_size': font_size, 'text_color': thumbnail_color})
        return text_and_colors
    def __cropAndResize(self, base_image, cropped_width, cropped_height):
        target_aspect_ratio = cropped_width / cropped_height
        base_width, base_height = base_image.size
        if base_width / base_height > target_aspect_ratio:
            new_width = int(base_height * target_aspect_ratio)
            left = (base_width - new_width) // 2
            right = left + new_width
            top, bottom = 0, base_height
        else:
            new_height = int(base_width / target_aspect_ratio)
            left, right = 0, base_width
            top = (base_height - new_height) // 2
            bottom = top + new_height
        base_image = base_image.crop((left, top, right, bottom))
        base_image = base_image.resize((cropped_width, cropped_height), Image.ANTIALIAS)
        return base_image
    def __transparentize(self, base_image, transparency):
        base_pixels = base_image.load()
        for x in range(base_image.width):
            for y in range(base_image.height):
                r, g, b, a = base_pixels[x, y]
                base_pixels[x, y] = (int(r*transparency), int(g*transparency), int(b*transparency), a)  # Apply transparency to the alpha channel
        return base_image
    def createThumbnail(self, base_image_path, overlay_image_path, output_path, font_size, ratio, words, thumbnail_color, transparency=0.8, stroke_width=20, total_w = 1280, total_h = 720, border_size=20, bg_color=(0,0,0,0), alignment='left'):
        outer_margin = font_size // 2
        line_spacing = font_size // 6
        output_path = f"{self.root}{self.output_dir}{output_path}"
        
        text_and_colors = self.__getThumbnailText(ratio, words, font_size, thumbnail_color, outer_margin, line_spacing)
        self.create_image_with_text(text_and_colors, overlay_image_path, bg_color, outer_margin, line_spacing, alignment, stroke_width)
    
        base_image = Image.open(f"{self.root}{self.output_dir}{base_image_path}").convert("RGBA")
        cropped_width, cropped_height = total_w - 2 * border_size, total_h - 2 * border_size
        # for outer border
        base_image = self.__cropAndResize(base_image, cropped_width, cropped_height)    
        # for add contrast to thumbnail text
        base_image = self.__transparentize(base_image, transparency)
   
        overlay_image = Image.open(f"{self.root}{self.output_dir}{overlay_image_path}").convert("RGBA")
        overlay_image = overlay_image.resize((cropped_width, int(overlay_image.height * cropped_width / overlay_image.width)), Image.ANTIALIAS)
        base_image.paste(overlay_image, (0, (cropped_height - overlay_image.height) // 2), overlay_image)
    
        canvas = Image.new("RGBA", (total_w, total_h), thumbnail_color)
        canvas.paste(base_image, (border_size, border_size), base_image)
        canvas.save(output_path)
        print(f"Image with size {canvas.size} saved to {output_path}")

if __name__ == '__main__':
    text = ['Why Is Bitcoin So Popular?']
    root = '/Users/apple/Desktop/sd/repo'
    output_dir = '/data/tests/0'
    base_image_path = "/young-man-showing-bitcoin-coin-to-his-intrigued-gr-2023-11-27-04-49-25-utc (1).jpg"
    stroke_path = '/stroke.png'
    output_path = "/stroke_overlay.png"         
    font_path = "/arial-mt-extra-bold.ttf"
    font_size = 360
    ratio = 0.6
    words = (text[0].split())
    for i in range(len(words)):
        try: words[i] = words[i][0].upper() + words[i][1:]
        except: pass
            
    thumbnail_color = (255, 255, 0, 255)
    transparency = 0.8
    ic = ImageCreator(root, output_dir, font_path)
    ic.createThumbnail(base_image_path, stroke_path, output_path, font_size, ratio, words, thumbnail_color, transparency, stroke_width=20)