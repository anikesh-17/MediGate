document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const themeToggle = document.getElementById('theme-toggle');

    let context = { state: 'START' }; // Initial context

    // Theme Toggle
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        themeToggle.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
    });

    // Start Chat
    window.startChat = function () {
        const startBtn = document.querySelector('.start-btn');
        if (startBtn) startBtn.remove();

        // Trigger the first interaction
        sendMessage("", true);
    };

    // Send Message Function
    async function sendMessage(message, isSystemTrigger = false) {
        if (!message && !isSystemTrigger) return;

        if (!isSystemTrigger) {
            addMessage(message, 'user');
            userInput.value = '';
        }

        const loadingId = showTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    context: context
                })
            });

            const data = await response.json();
            context = data.context; // Update context

            removeTypingIndicator(loadingId);
            addMessage(data.response, 'bot');

        } catch (error) {
            console.error('Error:', error);
            removeTypingIndicator(loadingId);
            addMessage("Sorry, I encountered an error. Please try again.", 'bot');
        }
    }

    // Add Message to UI
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);

        const avatar = document.createElement('div');
        avatar.classList.add('avatar');
        avatar.textContent = sender === 'user' ? '👤' : '🤖';

        const content = document.createElement('div');
        content.classList.add('content');

        // Simple Markdown parsing (Bold and Newlines)
        let formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\n/g, '<br>'); // Newlines

        content.innerHTML = formattedText;

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);

        chatWindow.appendChild(messageDiv);
        scrollToBottom();
    }

    // Typing Indicator
    function showTypingIndicator() {
        const id = 'typing-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'bot-message', 'typing-indicator-msg');
        messageDiv.id = id;

        const avatar = document.createElement('div');
        avatar.classList.add('avatar');
        avatar.textContent = '🤖';

        const content = document.createElement('div');
        content.classList.add('content', 'typing-indicator');
        content.innerHTML = '<span></span><span></span><span></span>';

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        chatWindow.appendChild(messageDiv);
        scrollToBottom();

        return id;
    }

    function removeTypingIndicator(id) {
        const element = document.getElementById(id);
        if (element) element.remove();
    }

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Event Listeners
    sendBtn.addEventListener('click', () => sendMessage(userInput.value));

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage(userInput.value);
        }
    });
});
