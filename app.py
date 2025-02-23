from flask import Flask, render_template, request, send_file
import requests
import time
from flask import send_from_directory
from dotenv import load_dotenv
import os

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv()

app = Flask(__name__,
           template_folder=os.path.join(current_dir, '../backend/templates'),
           static_folder=os.path.join(current_dir, '../backend/static'))

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188/")
print(f"ComfyUI URL is set to: {COMFYUI_URL}")
OUTPUT_DIR = "outputs"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def generate_workflow(prompt, negative_prompt, steps=20, cfg=8):
    workflow = {
        "prompt": {
            "3": {
                "inputs": {
                    "seed": 156970749859315,  # Set a specific seed
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
                "class_type": "KSampler",
            },
            "4": {
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"},
                "class_type": "CheckpointLoaderSimple",
            },
            "5": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1,
                },
                "class_type": "EmptyLatentImage",
            },
            "6": {
                "inputs": {"text": prompt, "clip": ["4", 1]},
                "class_type": "CLIPTextEncode",
            },
            "7": {
                "inputs": {"text": negative_prompt, "clip": ["4", 1]},
                "class_type": "CLIPTextEncode",
            },
            "8": {
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
                "class_type": "VAEDecode",
            },
            "9": {
                "inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]},
                "class_type": "SaveImage",
            },
        }
    }
    return workflow

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory('../backend/static', path)

@app.route("/generate", methods=["POST"])
def generate_image():
    try:
        print("Received generate request")
        data = request.json
        #print(f"Request data: {data}")
        
        # First, check if ComfyUI is running
        try:
            health_check = requests.get(COMFYUI_URL)
            if not health_check.ok:
                return {"error": "ComfyUI server is not responding properly"}, 500
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to ComfyUI server. Is it running?"}, 500

        if not data or "prompt" not in data:
            return {"error": "Missing prompt in request"}, 400

        workflow = generate_workflow(
            data["prompt"],
            data.get("negative_prompt", ""),
            data.get("steps", 20),
            data.get("cfg", 8)
        )
        
       # print(f"Generated workflow: {workflow}")
        
        # Run workflow
        try:
            response = requests.post(f"{COMFYUI_URL}/prompt", json=workflow)
            if not response.ok:
                error_text = response.text
                print(f"ComfyUI error response: {error_text}")
                return {"error": f"ComfyUI server error: {response.status_code}. Details: {error_text}"}, 500
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            return {"error": f"Failed to communicate with ComfyUI: {str(e)}"}, 500

        prompt_id = response.json()["prompt_id"]

        # Wait for completion
        while True:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
            if not response.ok:
                return {"error": "Failed to check generation status"}, 500
                
            history = response.json()
            if history[prompt_id]["status"]["completed"]:
                break
            time.sleep(1)

        # Get generated image
        output = history[prompt_id]["outputs"]
        image_path = next(iter(output.values()))["images"][0]["filename"]
        image_url = f"{COMFYUI_URL}/view?filename={image_path}&type=output"

        # Save image locally
        image_response = requests.get(image_url)
        if not image_response.ok:
            return {"error": "Failed to download generated image"}, 500
            
        local_path = os.path.join(OUTPUT_DIR, image_path)
        with open(local_path, "wb") as f:
            f.write(image_response.content)

        return {"image_url": f"/download/{image_path}"}
        
    except requests.exceptions.ConnectionError:
        return {"error": "Could not connect to ComfyUI server. Is it running?"}, 500
    except Exception as e:
        print(f"Error generating image: {str(e)}")  # Log the error
        return {"error": "Internal server error"}, 500

@app.route("/download/<filename>")
def download_image(filename):
    return send_file(os.path.join(OUTPUT_DIR, filename), as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)