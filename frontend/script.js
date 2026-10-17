// Konfiguracja Supabase (uzupełnij swoimi danymi z Supabase)
const SUPABASE_URL = 'https://wgxzotfgqwfcpsddgcys.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndneHpvdGZncXdmY3BzZGRnY3lzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIyMzg1MzksImV4cCI6MjEwNzgxNDUzOX0.Tm_sSfDiHGlx4Nor2xEMLkchAOfxWy2EQ4BppTZUeZo';
const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// Backend URL (lokalnie lub adres z deploymentu FastAPI)
const BACKEND_URL = '';

let currentRoom = 'Główny czat';
let username = 'Użytkownik';

// Elementy DOM
const roomsListEl = document.getElementById('rooms-list');
const chatMessagesEl = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
const sidebar = document.getElementById('sidebar');
const currentRoomTitle = document.getElementById('current-room-title');
const usernameInput = document.getElementById('username-input');
const renameInput = document.getElementById('rename-input');
const renameBtn = document.getElementById('rename-btn');

usernameInput.addEventListener('input', (e) => {
    username = e.target.value;
});

// Inicjalizacja
async function init() {
    await loadRooms();
    await loadMessages();
    setupRealtime();
}

// Pobieranie listy pokoi
async function loadRooms() {
    const { data, error } = await supabase.from('messages').select('room_id');
    if (error) {
        console.error('Błąd pobierania pokoi:', error);
        return;
    }

    const rooms = [...new Set(data.map(m => m.room_id || 'Główny czat'))].sort();
    if (!rooms.includes(currentRoom)) rooms.push(currentRoom);

    roomsListEl.innerHTML = '';
    rooms.forEach(room => {
        const div = document.createElement('div');
        div.className = `room-item ${room === currentRoom ? 'active' : ''}`;
        div.textContent = room;
        div.onclick = () => {
            currentRoom = room;
            renameInput.value = room;
            loadRooms();
            loadMessages();
        };
        roomsListEl.appendChild(div);
    });

    currentRoomTitle.textContent = currentRoom;
    renameInput.value = currentRoom;
}

// Pobieranie wiadomości dla aktywnego pokoju
async function loadMessages() {
    const { data, error } = await supabase
        .from('messages')
        .select('*')
        .eq('room_id', currentRoom)
        .order('id', { ascending: true });

    if (error) {
        console.error('Błąd pobierania wiadomości:', error);
        return;
    }

    renderMessages(data || []);
}

// Renderowanie wiadomości w oknie czatu
function renderMessages(messages) {
    chatMessagesEl.innerHTML = '';
    messages.forEach(msg => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${msg.role === 'model' ? 'assistant' : 'user'}`;

        const authorDiv = document.createElement('div');
        authorDiv.className = 'message-author';
        authorDiv.textContent = msg.role === 'model' ? 'Gemini' : msg.author;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = msg.content;

        msgDiv.appendChild(authorDiv);
        msgDiv.appendChild(contentDiv);
        chatMessagesEl.appendChild(msgDiv);
    });
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

// Nasłuchiwanie zmian w bazie danych w Czasie Rzeczywistym (WebSocket od Supabase)
function setupRealtime() {
    supabase
        .channel('public:messages')
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages' }, payload => {
            if (payload.new.room_id === currentRoom) {
                loadMessages();
            }
            loadRooms();
        })
        .subscribe();
}

// Wysyłanie wiadomości
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    messageInput.value = '';
    messageInput.style.height = 'auto';

    // 1. Zapis wiadomości użytkownika w Supabase
    const { error: userErr } = await supabase.from('messages').insert({
        author: username,
        content: text,
        role: 'user',
        room_id: currentRoom
    });

    if (userErr) {
        alert('Błąd zapisu wiadomości: ' + userErr.message);
        return;
    }

    // 2. Pobranie całej historii dla Gemini
    const { data: allMsgs } = await supabase
        .from('messages')
        .select('*')
        .eq('room_id', currentRoom)
        .order('id', { ascending: true });

    // 3. Wywołanie backendu FastAPI
    try {
        const res = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: allMsgs })
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Błąd serwera');

        // 4. Zapis odpowiedzi Gemini w Supabase
        await supabase.from('messages').insert({
            author: 'Gemini',
            content: data.response,
            role: 'model',
            room_id: currentRoom
        });

    } catch (err) {
        console.error(err);
        await supabase.from('messages').insert({
            author: 'System',
            content: `⚠️ Błąd: ${err.message}`,
            role: 'model',
            room_id: currentRoom
        });
    }
}

// Event Listeners
sendBtn.onclick = sendMessage;
messageInput.onkeydown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
};

newChatBtn.onclick = () => {
    const roomCount = roomsListEl.children.length + 1;
    currentRoom = `Rozmowa ${roomCount}`;
    loadRooms();
    loadMessages();
};

toggleSidebarBtn.onclick = () => {
    sidebar.classList.toggle('hidden');
};

renameBtn.onclick = async () => {
    const newName = renameInput.value.trim();
    if (!newName || newName === currentRoom) return;

    const oldRoom = currentRoom;
    const { error } = await supabase
        .from('messages')
        .update({ room_id: newName })
        .eq('room_id', oldRoom);

    if (!error) {
        currentRoom = newName;
        loadRooms();
        loadMessages();
    } else {
        alert('Błąd zmiany nazwy: ' + error.message);
    }
};

// Start aplikacji
init();