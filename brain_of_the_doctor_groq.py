# --- Groq (commented out — no vision models currently available on Groq) ---
# import base64
# import os
# from io import BytesIO
# from dotenv import load_dotenv
# from groq import Groq
# from PIL import Image
#
# load_dotenv()
#
# def encode_image_for_groq(filepath):
#     image = Image.open(filepath)
#     image.thumbnail((1024, 1024))
#     buffer = BytesIO()
#     image.convert("RGB").save(buffer, format="JPEG", quality=75)
#     return base64.b64encode(buffer.getvalue()).decode("utf-8")
#
# def brain_of_the_doctor(patient_text, image_filepath=None, video_filepath=None):
#     groq_api_key = os.environ.get("GROQ_API_KEY")
#     image_data = encode_image_for_groq(image_filepath)
#     client = Groq(api_key=groq_api_key)
#     response = client.chat.completions.create(
#         model="openai/gpt-oss-120b",  # No vision support on Groq as of Aug 2026
#         ...
#     )
#     return response.choices[0].message.content

# --- Google Gemini (active — requires GEMINI_API_KEY in .env) ---
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

load_dotenv()


def _upload_video_and_wait_until_active(client, video_filepath, max_wait_seconds=120):
    uploaded = client.files.upload(file=video_filepath)
    started = time.time()

    while uploaded.state == types.FileState.PROCESSING:
        if time.time() - started > max_wait_seconds:
            raise TimeoutError("Video upload is still processing. Please try a shorter clip.")
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state == types.FileState.FAILED:
        error_message = getattr(uploaded.error, "message", "Video processing failed.")
        raise RuntimeError(error_message)

    return uploaded


def brain_of_the_doctor(patient_text, image_filepath=None, video_filepath=None):
    if not video_filepath:
        return (
            "Before I give a recommendation, please upload a short video of the affected area in good lighting "
            "from multiple angles with gentle movement so I can better assess swelling and extent."
        )

    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("Missing GEMINI_API_KEY in .env or environment")

    prompt = (
        "You are a confident, natural doctor specializing in skin care. Speak with the reassurance, clarity, and authority of a real doctor. "
        "Limit your entire response to two or three sentences maximum. "
        "Use the uploaded video as primary evidence for movement, swelling, and extent. "
        "Use the uploaded image as additional detail if available. "
        "Do not use any special characters, symbols, asterisks, or markdown formatting in your response because it will be converted directly to audio.\n\n"
        f"Patient text: {patient_text}"
    )

    client = genai.Client(api_key=gemini_api_key)
    uploaded_video = _upload_video_and_wait_until_active(client, video_filepath)

    contents = [prompt, uploaded_video]
    if image_filepath:
        image = Image.open(image_filepath)
        image.thumbnail((1024, 1024))
        image = image.convert("RGB")
        contents.append(image)

    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction="You are a careful skin care assistant. Give general information, not a diagnosis.",
            max_output_tokens=1000,
        ),
    )

    return response.text


# OLD CODE KEPT FOR REFERENCE
# import base64
# import os
# from io import BytesIO
#
# from dotenv import load_dotenv
# from groq import Groq
# from PIL import Image
#
#
# folder = os.path.dirname(__file__)
# env_path = os.path.join(folder, ".env")
# load_dotenv(env_path)
#
# api_key = os.environ.get("GROQ_API_KEY")
# if not api_key:
#     raise ValueError("Missing GROQ_API_KEY in .env or environment")
#
#
# image_path = os.path.join(folder, "sample-image.png")
#
# image = Image.open(image_path)
# image.thumbnail((1024, 1024))
#
# buffer = BytesIO()
# image.convert("RGB").save(buffer, format="JPEG", quality=75)
# image_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
#
# client = Groq(api_key=api_key)
#
# response = client.chat.completions.create(
#     model=os.environ.get("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
#     max_completion_tokens=1000,
#     messages=[
#         {
#             "role": "system",
#             "content": "You are a helpful medical assistant. Give general information, not a diagnosis.",
#         },
#         {
#             "role": "user",
#             "content": [
#                 {
#                     "type": "text",
#                     "text": "What do you see in this image? Give general skin care advice, not a diagnosis.",
#                 },
#                 {
#                     "type": "image_url",
#                     "image_url": {
#                         "url": f"data:image/jpeg;base64,{image_data}",
#                     },
#                 },
#             ],
#         },
#     ],
# )
#
# print(response.choices[0].message.content)


# --- Quick test block ---
if __name__ == "__main__":
    folder = os.path.dirname(__file__)
    test_image = os.path.join(folder, "sample-image.png")

    result = brain_of_the_doctor(
        patient_text="I have a red, itchy rash on my arm. What could it be?",
        image_filepath=test_image,
    )
    print("Doctor's response:\n", result)