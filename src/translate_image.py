from duckduckgo_search import DDGS
import requests
import os

def download_best_image(query, save_dir="downloaded_images", file_name="image.jpg"):
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, file_name)

    # Search for image URLs
    with DDGS() as ddgs:
        results = ddgs.images(query, max_results=1)
        for result in results:
            image_url = result["image"]
            print(f"Downloading from: {image_url}")
            response = requests.get(image_url)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"Image saved to {file_path}")
                return file_path
            else:
                print("Failed to download the image.")
                return None

# Example usage
download_best_image("full outer join")