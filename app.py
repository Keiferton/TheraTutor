import os
import openai
import time
import sys
import requests
from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__, static_folder="static", static_url_path="")
app.config['SECRET_KEY'] = 'secret!'  # Secret key for session management
CORS(app)  # Allow Cross-Origin Resource Sharing (CORS)
socketio = SocketIO(app, cors_allowed_origins="*")  # Initialize SocketIO with CORS allowed

# Set your OpenAI API key from environment variable
client = openai.OpenAI(
    api_key=os.getenv("my_key"),  # Retrieve API key from environment variable
)

# Function to simulate typing effect with delays
def print_with_typing_effect(text):
    for char in text:
        if char == ' ':
            sys.stdout.write(char)  # Write space character
            sys.stdout.flush()  # Ensure it is printed immediately
            time.sleep(0.05)  # Delay for spaces between words
        else:
            sys.stdout.write(char)  # Write character
            sys.stdout.flush()  # Ensure it is printed immediately
            time.sleep(0.03)  # Delay for each character
    print()  # Move to the next line after the text is fully printed

# Initialize conversation history with a system message
conversation_history = [
    {"role": "system", "content": """
     You are TheraTutor, an emotionally intelligent tutor designed to help students succeed academically by understanding and adapting to their emotional state. You start conversations asking a student how they are, you do not have to ask them that verbatim. You must respond to student queries with both educational guidance and emotional support. Your goal is to provide clear, helpful explanations while also being empathetic to the student's emotional needs. If students feel they are in a crisis, please refer them to https://988lifeline.org/chat/. This is a 24/7/365 hotline where they can vent to a professional. Only use this if sentiment analysis returns crisis or similar.

     Student Interaction:
     1. Emotionally Aware Interaction:
        - Detect and understand the emotional state of the student through their text input.
        - Adjust your responses based on the detected emotion:
          - Positive Emotion: Maintain encouragement and provide reinforcement.
          - Negative Emotion (e.g., stress, frustration): Offer support, empathy, and constructive feedback.

     2. Educational Assistance:
        - Provide academic help in various subjects.
        - Offer clear explanations, answer questions, and provide step-by-step guidance on academic topics.
        - Be patient and thorough in your explanations.

     3. Adaptive and Supportive Responses:
        - Use sentiment analysis to gauge the emotional tone of the student's input.
        - Tailor your responses to be supportive and empathetic, especially when the student expresses negative emotions.
        - Encourage and motivate students, acknowledging their efforts and progress.

     Examples:

     - Student Input (Positive Emotion):
       - "I feel great about my math test!"
       - Response: "That's wonderful to hear! Keep up the good work. Is there anything specific you'd like to review or practice further?"

     - Student Input (Negative Emotion):
       - "I'm really stressed about my exams."
       - Response: "I'm sorry to hear that you're feeling stressed. Exams can be challenging, but you're capable and well-prepared. Let's break down the material together. What topic are you most worried about?"

     - Student Input (Educational Query):
       - "Can you help me understand the Pythagorean theorem?"
       - Response: "Of course! The Pythagorean theorem states that in a right-angled triangle, the square of the length of the hypotenuse (the side opposite the right angle) is equal to the sum of the squares of the lengths of the other two sides. Here's an example..."

     Additional Notes:
     - Always be encouraging and positive.
     - Use clear, concise language.
     - Provide examples and analogies to clarify complex concepts.
     - Check for understanding and ask follow-up questions to ensure the student comprehends the material.

     Instructions to Model:
     - Always analyze the sentiment of the student's input before generating a response.
     - Maintain a balance between providing emotional support and academic assistance.
     - Ensure that responses are adaptive to the student's current emotional state and learning needs.
     """}
]

# Function to get the emotional response from the OpenAI model
def get_emotional_response(conversation_history):
    # Debugging print to check the conversation history
    print("Conversation History:", conversation_history)
    response = client.chat.completions.create(
        model="gpt-4o",  # Specify the model to use
        messages=conversation_history,  # Provide the conversation history
        max_tokens=400,  # Limit the response length
        temperature=0.7  # Control the randomness of the response
    )
    # Debugging print to check the raw response from the API
    print("Raw API Response:", response)
    assistant_response = response.choices[0].message.content.strip()  # Get the response text
    conversation_history.append({"role": "assistant", "content": assistant_response})  # Add the response to the history
    return assistant_response  # Return the response

def get_quicklatex_image_url(latex_code):
    url = "https://quicklatex.com/latex3.f"
    payload = {
        'formula': latex_code,
        'fsize': '20px',
        'fcolor': '000000',
        'mode': '0',
        'out': '1',
        'remhost': 'quicklatex.com',
        'preamble': r'\usepackage{amsmath}\usepackage{amsfonts}\usepackage{amssymb}',
        'rnd': '0.123456789'  # Random number to avoid caching issues
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.text.split()[1]  # The URL is in the response text
    return None

# Route for the home page
@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')  # Serve the React app

# Event handler for messages received via SocketIO
@socketio.on('message')
def handle_message(msg):
    global conversation_history  # Access the global conversation history
    print(f"Received message: {msg}")  # Debug print to show received message
    conversation_history.append({"role": "user", "content": msg})  # Add the user message to the history
    if "$$" in msg:
        latex_code = msg.split("$$")[1]
        image_url = get_quicklatex_image_url(latex_code)
        if image_url:
            response = f'<img src="{image_url}" alt="LaTeX Image">'
        else:
            response = "Error generating LaTeX image."
    else:
        response = get_emotional_response(conversation_history)  # Get the response from the model
    print(f"Response: {response}")  # Debug print to show response from the model
    send(response)  # Send the response back to the client

# Run the Flask application with SocketIO
if __name__ == "__main__":
    socketio.run(app, debug=True, use_reloader=True, log_output=True)  # Start the app with debugging and auto-reloading enabled
