from PIL import Image, ImageDraw, ImageFont
import os

# SETTINGS
TEMPLATE_PATH = "TREASURE.png"  # <-- make sure your base treasure icon is named this
OUTPUT_FOLDER = "generated_markers"

# Make sure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load base image
base_icon = Image.open(TEMPLATE_PATH).convert("RGBA")

# Font settings
try:
    top_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)    # Big font for top
    bottom_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 10) # Smaller font for bottom
except IOError:
    print("⚠️ Couldn't load TTF font, falling back to default.")
    top_font = ImageFont.load_default()
    bottom_font = ImageFont.load_default()

# Define batches
batch_definitions = {
    "N": 75,
    "E": 58,
    "S": 27,
    "W": 108,
    "CC": 19,
    "X": 75,
}

def create_marker(top_text, bottom_text, filename):
    canvas = base_icon.copy()
    draw = ImageDraw.Draw(canvas)

    try:
        # Smaller top font (prefix), larger bottom font (number)
        top_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 12)
        bottom_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except IOError:
        top_font = ImageFont.load_default()
        bottom_font = ImageFont.load_default()

    # Top text (prefix)
    top_bbox = draw.textbbox((0, 0), top_text, font=top_font)
    top_width, top_height = top_bbox[2] - top_bbox[0], top_bbox[3] - top_bbox[1]
    top_y = 1  # tighter to top
    top_x = (canvas.width - top_width) // 2

    # Bottom text (number)
    bottom_bbox = draw.textbbox((0, 0), bottom_text, font=bottom_font)
    bottom_width, bottom_height = bottom_bbox[2] - bottom_bbox[0], bottom_bbox[3] - bottom_bbox[1]
    bottom_y = canvas.height - bottom_height - 5
    bottom_x = (canvas.width - bottom_width) // 2

    # Draw outlines
    for x_off in [-1, 0, 1]:
        for y_off in [-1, 0, 1]:
            if x_off or y_off:
                draw.text((top_x + x_off, top_y + y_off), top_text, font=top_font, fill="black")
                draw.text((bottom_x + x_off, bottom_y + y_off), bottom_text, font=bottom_font, fill="black")

    # Draw main text (purple)
    draw.text((top_x, top_y), top_text, font=top_font, fill="purple")
    draw.text((bottom_x, bottom_y), bottom_text, font=bottom_font, fill="purple")

    canvas.save(os.path.join(OUTPUT_FOLDER, filename))


# Generate all files
for prefix, count in batch_definitions.items():
    for i in range(1, count + 1):
        top_text = prefix
        bottom_text = str(i)
        filename = f"{prefix}{i}.png"
        create_marker(top_text, bottom_text, filename)

print("✅ All markers generated!")
