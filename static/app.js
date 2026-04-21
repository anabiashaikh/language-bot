document.addEventListener('DOMContentLoaded', async () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const typingIndicator = document.getElementById('typing-indicator');
    const welcomeMessage = document.getElementById('welcome-message');
    
    // Sidebar elements
    const sessionList = document.getElementById('session-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const sidebar = document.getElementById('sidebar');
    const openSidebarBtn = document.getElementById('open-sidebar-btn');
    const closeSidebarBtn = document.getElementById('close-sidebar-btn');
    const overlay = document.getElementById('mobile-sidebar-overlay');

    let currentSessionId = null;

    // --- Sidebar Mobile Toggle Logic ---
    function toggleSidebar() {
        const isClosed = sidebar.classList.contains('-translate-x-full');
        if(isClosed) {
            sidebar.classList.remove('-translate-x-full');
            overlay.classList.remove('hidden');
        } else {
            sidebar.classList.add('-translate-x-full');
            overlay.classList.add('hidden');
        }
    }
    openSidebarBtn.addEventListener('click', toggleSidebar);
    closeSidebarBtn.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', toggleSidebar);

    // --- Initialization ---
    await loadSessions();

    async function loadSessions() {
        const res = await fetch('/api/sessions');
        const sessions = await res.json();
        
        sessionList.innerHTML = '';
        if (sessions.length === 0) {
            await startNewChat();
        } else {
            sessions.forEach(s => appendSessionToList(s.id, s.title));
            // Default to first chat on load
            if(!currentSessionId) {
                await loadChatHistory(sessions[0].id);
            }
        }
    }

    async function startNewChat() {
        const res = await fetch('/api/sessions', { method: 'POST' });
        const data = await res.json();
        currentSessionId = data.id;
        
        appendSessionToList(data.id, data.title, true);
        chatHistory.innerHTML = '';
        welcomeMessage.classList.remove('hidden');
        updateActiveSessionStyling();
    }

    newChatBtn.addEventListener('click', () => {
        startNewChat();
        if(window.innerWidth < 768) { toggleSidebar(); }
    });

    function appendSessionToList(id, title, prepend = false) {
        const li = document.createElement('li');
        li.className = 'group rounded-md flex items-center p-2 text-sm cursor-pointer transition-colors hover:bg-white/10 text-gray-300';
        li.dataset.sessionId = id;
        li.innerHTML = `
            <span class="material-symbols-outlined text-[18px] mr-2 text-gray-500 group-hover:text-gray-300">chat_bubble</span>
            <span class="truncate sidebar-title flex-grow">${escapeHtml(title)}</span>
        `;
        
        li.addEventListener('click', () => {
            loadChatHistory(id);
            if(window.innerWidth < 768) { toggleSidebar(); }
        });

        if(prepend) {
            sessionList.prepend(li);
        } else {
            sessionList.appendChild(li);
        }
    }

    function updateActiveSessionStyling() {
        document.querySelectorAll('#session-list li').forEach(li => {
            if (li.dataset.sessionId === currentSessionId) {
                li.classList.add('bg-white/10', 'text-white', 'font-medium');
                li.querySelector('.material-symbols-outlined').classList.replace('text-gray-500', 'text-white');
            } else {
                li.classList.remove('bg-white/10', 'text-white', 'font-medium');
                li.querySelector('.material-symbols-outlined').classList.replace('text-white', 'text-gray-500');
            }
        });
    }

    async function loadChatHistory(id) {
        currentSessionId = id;
        updateActiveSessionStyling();
        chatHistory.innerHTML = '';
        welcomeMessage.classList.add('hidden');
        
        const res = await fetch(`/api/sessions/${id}`);
        const messages = await res.json();
        
        if(messages.length === 0) {
            welcomeMessage.classList.remove('hidden');
        } else {
            messages.forEach(msg => {
                if(msg.role === 'user') appendUserMessage(msg.content);
                else appendBotMessage(msg.content);
            });
            scrollToBottom();
        }
    }

    // --- Chat Form Handling ---
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const text = chatInput.value.trim();
        if(!text) return;

        if(!currentSessionId) {
            await startNewChat();
        }

        welcomeMessage.classList.add('hidden');
        chatInput.value = '';
        appendUserMessage(text);
        showTypingIndicator();
        scrollToBottom();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text, session_id: currentSessionId })
            });

            if (!response.ok) throw new Error('Server error');

            const data = await response.json();
            
            // If the backend generated a new title, refresh the sidebar
            if(data.title_updated) {
                loadSessions(); // Re-fetches sidebar to get the new Gemini title
            }

            hideTypingIndicator();
            appendBotMessage(data.answer);
            scrollToBottom();

        } catch (error) {
            hideTypingIndicator();
            appendBotMessage("Connection issue: " + error.message);
            scrollToBottom();
        }
    });

    // --- Message Rendering ---
    function appendUserMessage(message) {
        const messageHtml = `
            <div class="flex flex-col gap-1 max-w-[85%] md:max-w-[70%] self-end">
                <div class="signature-sea-gradient px-5 py-4 rounded-2xl rounded-br-sm shadow-md">
                    <p class="text-white leading-relaxed whitespace-pre-wrap">${escapeHtml(message)}</p>
                </div>
            </div>
        `;
        chatHistory.insertAdjacentHTML('beforeend', messageHtml);
    }

    function appendBotMessage(message) {
        const messageHtml = `
            <div class="flex flex-col gap-1 max-w-[90%] md:max-w-[80%] self-start">
                <div class="glass-bubble px-5 py-4 rounded-2xl rounded-bl-sm border border-black/5 shadow-sm">
                    <p class="text-on-surface leading-relaxed whitespace-pre-wrap">${escapeHtml(message)}</p>
                </div>
            </div>
        `;
        chatHistory.insertAdjacentHTML('beforeend', messageHtml);
    }

    // --- Utilities ---
    function showTypingIndicator() { typingIndicator.classList.remove('hidden'); }
    function hideTypingIndicator() { typingIndicator.classList.add('hidden'); }
    
    function scrollToBottom() {
        const container = document.getElementById('chat-container');
        container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }

    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
});
