## Note: Downgrade #gradio~=4.44.0 to gradio==3.50.2
## App setup automatically create Service Principal e.g. app-pl90j1 ai-kitchen
# This Service Principal need permission to use token. Can be setup from 
# Settings -> Advance -> Personal Access Tokens
## Use WorkspaceClient it atomatically use Client ID and Secret from Environment variables
# us WorkspaceClient to Generate token for the LLM Calls.
### Bug Fix:
# history.append({"role": "user", "content": user_input})
# history.append({"role": "assistant", "content": response})
#Fix:  history.append([user_input, response])

from databricks import sql
from databricks.sdk.core import Config
import gradio as gr
import pandas as pd
import base64, io, os
from PIL import Image
from openai import OpenAI

# Ensure environment variable is set correctly
warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")

print(
    f"Warehouse ID: {warehouse_id}"
)

# Initialize WorkspaceClient using default authentication (credentials from environment/config)
from databricks.sdk import WorkspaceClient

# Get Client and Current user name
ws_client = WorkspaceClient()
print("CLIENT ID")
print(ws_client.config.client_id)

print("SERVICE PRINCIPAL ENV CLIENT ID")
print(os.environ.get("DATABRICKS_CLIENT_ID"))

print("HOST")
print(ws_client.config.host)

token_response = ws_client.tokens.create(
    comment="AIKitchenToken",
    lifetime_seconds=86400
)

token = token_response.token_value

print("TOKEN CREATED")

print(f"Step#1: Received Client Host: {ws_client.config.host}")

try:
    me = ws_client.current_user.me()
    print(f"Step#2: Received Users: {me.display_name}, {me.user_name}")
except Exception as e:
    print("CURRENT USER ERROR")
    print(str(e))

### Test the OpenAI client
# chat_completion = client.chat.completions.create(
#   messages=[
#     {"role": "user", "content": "Hello!"},
#     {"role": "assistant", "content": "Hello! How can I assist you today?"},
#     {"role": "user", "content": "What is Databricks?"},
#   ],
#   model="databricks-meta-llama-3-1-8b-instruct",
#   max_tokens=1024
# )
# print(chat_completion.choices[0].message.content)


#################################################################################
TEXT_MODEL   = "databricks-meta-llama-3-3-70b-instruct"
VISION_MODEL = "databricks-llama-4-maverick"

def get_llm_client():

    print("Creating OpenAI Client")

    return OpenAI(
        api_key=token,
        base_url="https://7474652142269878.ai-gateway.cloud.databricks.com/mlflow/v1"
    )
    
# -------------------------------------------------------------------------------
# IMAGE SCANNER
# -------------------------------------------------------------------------------
def scan_image_for_ingredients(image_bytes: bytes) -> str:
    try:
        img_b64  = base64.b64encode(image_bytes).decode("utf-8")
        print(f"Base64 Length: {len(img_b64)}")
        print(img_b64[:100])
        client = get_llm_client()
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    },
                    {
                        "type": "text",
                        "text": "List all visible food items as comma-separated."
                    }
                ]
            }],
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error detecting ingredients: {str(e)}"

# -------------------------------------------------------------------------------
# MODE 1 - Dish name or cuisine interest + optional fridge scan
# -------------------------------------------------------------------------------
def mode1_get_recipe(user_input, diet_filter="none", chat_history=None, image_bytes=None):
    
    if chat_history is None:
        chat_history = []
    fridge_contents = None
    if image_bytes:
        fridge_contents = scan_image_for_ingredients(image_bytes)
        if fridge_contents.startswith("Error"):
            fridge_contents = None

    system_prompt = (
        "You are AI Kitchen, a friendly and expert chef assistant. "
        "Always structure your responses with clear markdown sections. "
        "For a specific dish provide: ## Recipe: [Dish Name], then Ingredients "
        "with exact quantities, Instructions as numbered steps, Nutrition per "
        "serving (calories, protein, carbs, fat), Cooking time (prep + cook). "
        "For a cuisine interest suggest 3-4 popular dishes with a 2-line "
        "description each, then ask which one they want the full recipe for. "
        "Keep tone warm and encouraging."
    )

    if fridge_contents:
        user_message = f"Request: {user_input}\n"
        if diet_filter != "none":
            user_message += f"Dietary requirement: {diet_filter}\n"
        user_message += (
            f"\nI scanned my fridge and found: {fridge_contents}\n\n"
            "Please provide:\n"
            "1. The full recipe\n"
            "2. A Your Fridge Check section with:\n"
            "   - Available: ingredients I HAVE\n"
            "   - Missing: ingredients I need to buy\n"
            "3. Nutrition information"
        )
    else:
        user_message = user_input
        if diet_filter != "none":
            user_message += f"\nDietary requirement: {diet_filter}"

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_message})

    client = get_llm_client()
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=messages,
            max_tokens=800
        )
        recipe_text = response.choices[0].message.content
    except Exception as e:
        recipe_text = f"Error generating recipe: {str(e)}"

    return {
        "recipe": recipe_text,
        "fridge_scanned": fridge_contents is not None,
        "detected_ingredients": fridge_contents or "No image provided"
    }

# -------------------------------------------------------------------------------
# MODE 2 - Fridge scan -> suggest recipes from available ingredients
# -------------------------------------------------------------------------------
def mode2_suggest_from_fridge(image_bytes, diet_filter="none"):

    detected = scan_image_for_ingredients(image_bytes)
    diet_line = (
    f"Dietary requirement: {diet_filter}"
    if diet_filter != "none"
    else ""
    )

    if detected.startswith("Error"):
        return {
            "detected_ingredients": detected,
            "full_suggestions": "Ingredient detection failed."
        }

    prompt = (
        f"I found these ingredients in my fridge: {detected}\n{diet_line}\n\n"
        "Please provide:\n\n"
        "## Ready to Cook\n"
        "Best recipe using only what I have. "
        "Include: ingredients, numbered instructions, cooking time.\n\n"
        "## Almost Ready (needs 1-3 more items)\n"
        "One great recipe needing just a few more ingredients. "
        "Include: full recipe + clearly labelled Missing Ingredients list.\n\n"
        "## Nutrition (for Ready to Cook)\n"
        "Calories, protein, carbs, fat per serving."
    )

    client = get_llm_client()
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        suggestions = response.choices[0].message.content
    except Exception as e:
        suggestions = f"Error generating suggestions: {str(e)}"

    return {
        "detected_ingredients": detected,
        "full_suggestions": suggestions
    }

# -------------------------------------------------------------------------------
# GRADIO HANDLERS
# -------------------------------------------------------------------------------
def handle_mode1(user_input, diet_filter, fridge_image, history):
    
    print(
    f"Mode1 Input: {user_input}"
    )
    
    if not user_input.strip():
        return history, history, ""

    image_bytes = None
    if fridge_image is not None:
        img = Image.fromarray(fridge_image)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()

    result = mode1_get_recipe(
        user_input=user_input,
        diet_filter=diet_filter,
        chat_history=history,
        image_bytes=image_bytes
    )
    
    response = result["recipe"]
    if image_bytes and result["detected_ingredients"] != "No image provided":
        response = f"**Fridge scan detected:** {result['detected_ingredients'][:100]}...\n\n---\n\n" + response

    # Using the Gradio 5+ required dictionary format
    # history.append({"role": "user", "content": user_input})
    # history.append({"role": "assistant", "content": response})
    history.append([user_input, response])

    print(
    "Mode1 Success"
    )

    return history, history, ""


def handle_mode2(fridge_image, diet_filter):
    
    print(
    "Mode2 Started"
    )
    
    if fridge_image is None:
        return "Please upload a fridge or pantry photo first."
    
    img = Image.fromarray(fridge_image)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()
    
    result = mode2_suggest_from_fridge(image_bytes, diet_filter)
    
    print(
    "Mode2 Success"
    )
    
    return (
        f"## Ingredients Detected\n"
        f"{result['detected_ingredients']}\n\n---\n\n"
        f"{result['full_suggestions']}"
    )

# -------------------------------------------------------------------------------
# UI
# -------------------------------------------------------------------------------
with gr.Blocks(title="AI Kitchen") as app:

    gr.HTML(
        "<div style='text-align:center;padding:24px 0 8px'>"
        "<h1 style='font-size:2rem;margin:0'>AI Kitchen</h1>"
        "<h3 style='font-size:1rem;margin:0'>What's in your Refrigerator?</h3>"
        "<p style='color:#888;margin:4px 0 0'>Powered By IgnAite</p>"
        "</div>"
    )
    print(f"Step#7: Setting up stylesheet and page layout..." )

    diet_filter = gr.Dropdown(
        choices=["none", "vegetarian", "vegan", "keto", "gluten-free", "dairy-free"],
        value="none",
        label="Choose Your Dietary Preference!"
    )
    
    print(f"Step#8: Display and Select Dietary Preference" )

    with gr.Tabs():

        # MODE 1 TAB
        with gr.Tab("Mode 1 - Dish or Cuisine"):
            gr.Markdown(
                "Enter a **dish name** or **cuisine interest**. "
                "Optionally upload a **fridge photo** to see which "
                "ingredients you have and what is missing."
            )
            print(f"Step#9: Display Mode 1 - Dish or Cuisine" )

            with gr.Row():
                with gr.Column(scale=2):
                    # type="messages" parameter completely removed for Gradio 5+ compatibility
                    chatbot = gr.Chatbot(
                        label="AI Kitchen Chef",
                        height=420,
                        avatar_images=(None, "https://em-content.zobj.net/source/apple/354/cooking_1f373.png")
                    )
                    chat_state = gr.State([])
                    with gr.Row():
                        user_input = gr.Textbox(
                            placeholder="e.g. Biryani  |  I love Thai food  |  Quick vegan dinner",
                            label="Your request",
                            scale=4
                        )
                        send_btn1 = gr.Button("Ask Chef", variant="primary", scale=1)
                        
                with gr.Column(scale=1):
                    gr.Markdown("#### Fridge Scan (optional)")
                    gr.Markdown("Upload your fridge photo to check which ingredients you have for this dish.")
                    fridge_img_m1 = gr.Image(label="Fridge / pantry photo", type="numpy", height=260)
                    gr.Markdown("_Leave empty to skip fridge check_")
            
                print(f"Step#10: Display Chat and Textbox{[user_input, diet_filter, fridge_img_m1, chat_state]}" )
                print(f"Step#11: Display Chat and Textbox{[chatbot, chat_state, user_input]}" )

            send_btn1.click(
                fn=handle_mode1,
                inputs=[user_input, diet_filter, fridge_img_m1, chat_state],
                outputs=[chatbot, chat_state, user_input]
            )
            print(f"Step#11: Sent after Button Click to Handle Model1" )

            user_input.submit(
                fn=handle_mode1,
                inputs=[user_input, diet_filter, fridge_img_m1, chat_state],
                outputs=[chatbot, chat_state, user_input]
            )
            print(f"Step#12: Submit to Handle Model1" )

        # MODE 2 TAB
        with gr.Tab("Mode 2 - What Can I Cook?"):
            print(f"Step#20: Mode 2 - What Can I Cook" )
            gr.Markdown(
                "Upload a photo of your fridge or pantry. "
                "AI detects your ingredients and suggests the best "
                "recipes you can make **right now** - plus one that "
                "needs just a few extra items."
            )
            print(f"Step#21: Mode 2 -Markdown" )
            with gr.Row():
                with gr.Column(scale=1):
                    fridge_img_m2 = gr.Image(label="Upload fridge / pantry photo", type="numpy", height=320)
                    scan_btn2 = gr.Button("Scan and Suggest Recipes", variant="primary", size="lg")
                with gr.Column(scale=1):
                    scan_output = gr.Markdown()
    print(f"Step#22: Mode 2 - Setup Row Image", diet_filter )                
    
    scan_btn2.click(
        fn=handle_mode2,
        inputs=[fridge_img_m2, diet_filter],
        outputs=[scan_output])
    
    print(f"Step#23: Mode 2 - Get Button Click", scan_output )
    
    gr.HTML(
        "<div style='text-align:center;padding:16px;color:#aaa;font-size:12px'>"
        "IgnAite | AI Powered by Databricks | Made with ❤️ Kitchen"
        "</div>"
    )

print(f"Step#6: Starting AI Kitchen App" )
app.launch(
    show_api=False, 
    show_error=True
)
print(f"Step#50: Stoppong AI Kitchen App" )