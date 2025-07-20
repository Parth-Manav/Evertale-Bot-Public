
import os
import json
from PIL import Image

def generate_button_json(buttons_dir, output_file):
    images_data = []
    categories_data = []
    annotations_data = []

    image_id_counter = 0
    category_id_counter = 0
    annotation_id_counter = 0

    for filename in os.listdir(buttons_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            filepath = os.path.join(buttons_dir, filename)
            try:
                with Image.open(filepath) as img:
                    width, height = img.size

                # Add to images_data
                images_data.append({
                    "width": width,
                    "height": height,
                    "id": image_id_counter,
                    "file_name": f"buttons/{filename}"
                })

                # Add to categories_data (using filename without extension as category name)
                category_name = os.path.splitext(filename)[0]
                categories_data.append({
                    "id": category_id_counter,
                    "name": category_name
                })

                # Add to annotations_data
                annotations_data.append({
                    "id": annotation_id_counter,
                    "image_id": image_id_counter,
                    "category_id": category_id_counter,
                    "segmentation": [],
                    "bbox": [0.0, 0.0, float(width), float(height)],
                    "ignore": 0,
                    "iscrowd": 0,
                    "area": float(width * height)
                })

                image_id_counter += 1
                category_id_counter += 1
                annotation_id_counter += 1

            except Exception as e:
                print(f"Could not process {filename}: {e}")
                continue

    result_json = {
        "images": images_data,
        "categories": categories_data,
        "annotations": annotations_data
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_json, f, indent=4)

    print(f"Generated {len(images_data)} entries and saved to {output_file}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    buttons_directory = os.path.join(script_dir, "assets", "buttons")
    output_json_file = os.path.join(script_dir, "assets", "buttons_data.json")
    generate_button_json(buttons_directory, output_json_file)
