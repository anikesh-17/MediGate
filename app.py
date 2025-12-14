from flask import Flask, render_template, request, jsonify
from chatbot_logic import HealthChatBotService

app = Flask(__name__)

# Initialize the chatbot service (trains model on startup)
print("Initializing Chatbot Service...")
bot_service = HealthChatBotService()
print("Chatbot Service Ready!")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    context = data.get('context', {})
    
    response, new_context = bot_service.process_message(message, context)
    
    return jsonify({
        'response': response,
        'context': new_context
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
