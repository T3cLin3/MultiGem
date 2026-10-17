// Konfiguracja Supabase
const SUPABASE_URL = 'https://wgxzotfgqwfcpsddgcys.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndneHpvdGZncXdmY3BzZGRnY3lzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIyMzg1MzksImV4cCI6MjEwNzgxNDUzOX0.Tm_sSfDiHGlx4Nor2xEMLkchAOfxWy2EQ4BppTZUeZo';

let supabaseClient = null;
try {
    supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
} catch (e) {
    console.error("Błąd inicjalizacji Supabase:", e);
}

const BACKEND_URL = '';

// Sesja aktualnego pokoju
let currentRoomId = 'main-chat';
let currentRoomName = 'Główny czat';
let username = 'Użytkownik';

// Zmienne do obsługi załącznika pliku/zdjęcia
let selectedFile = null;
let selectedFileBase64 = null;
let selectedFileMime = null;

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

// Załączniki DOM
const fileInput = document.getElementById('file-input');
const attachBtn = document.getElementById('attach-btn');
const filePreview = document.getElementById('file-preview');
const fileNameEl = document.getElementById('file-name');
const removeFileBtn = document.getElementById('remove-file-btn');

if (usernameInput) {
    usernameInput.addEventListener('input', (e) => {
        username = e.target.value;
    });
}

// Obsługa wyboru pliku
if (attachBtn && fileInput) {
    attachBtn.onclick = () => fileInput.click();
    fileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        selectedFile = file;
        if (fileNameEl) fileNameEl.textContent = `📎 ${file.name}`;
        if (filePreview) filePreview.style.display = 'flex';

        const reader = new FileReader();
        reader.onload = function(uploadEvent) {
            selectedFileBase64 = uploadEvent.target.result.split(',')[1];
            selectedFileMime = file.type;
        };
        reader.readAsDataURL(file);
    };
}

if (removeFileBtn) {
    removeFileBtn.onclick = () => {
        selectedFile = null;
        selectedFileBase64 = null;
        selectedFileMime = null;
        if (fileInput) fileInput.value = '';
        if (filePreview) filePreview.style.display = 'none';
    };
}

async function init() {
    if (!supabaseClient) {
        console.error("Brak klienta Supabase!");
        return;
    }
    await loadRooms();
    await loadMessages();
    setupRealtime();
}

// Pobieranie listy pokoi
async function loadRooms() {
    if (!supabaseClient) return;
    const { data, error } = await supabaseClient.from('messages').select('room_id, content').order('id', { ascending: true });
    if (error) {
        console.error('Błąd pobierania pokoi:', error);
        return;
    }

    const roomMap = new Map();
    // Domyślny pokój zawsze na liście
    roomMap.set('main-chat', 'Główny czat');

    (data || []).forEach(m => {
        const rId = m.room_id || 'main-chat';
        if (!roomMap.has(rId)) {
            roomMap.set(rId, rId === 'main-chat' ? 'Główny czat' : `Rozmowa (${rId.slice(-4)})`);
        }
    });

    if (!roomMap.has(currentRoomId)) {
        roomMap.set(currentRoomId, currentRoomName);
    }

    if (roomsListEl) {
        roomsListEl.innerHTML = '';
        roomMap.forEach((roomName, rId) => {
            const wrapperDiv = document.createElement('div');
            wrapperDiv.className = `room-item-wrapper ${rId === currentRoomId ? 'active' : ''}`;

            const div = document.createElement('div');
            div.className = `room-item`;
            div.textContent = roomName;
            div.onclick = () => {
                currentRoomId = rId;
                currentRoomName = roomName;
                if (renameInput) renameInput.value = roomName;
                loadRooms();
                loadMessages();
            };

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'delete-room-btn';
            deleteBtn.innerHTML = '🗑️';
            deleteBtn.title = 'Usuń rozmowę';
            deleteBtn.onclick = async (e) => {
                e.stopPropagation();
                await deleteRoom(rId);
            };

            wrapperDiv.appendChild(div);
            wrapperDiv.appendChild(deleteBtn);
            roomsListEl.appendChild(wrapperDiv);
        });
    }

    if (currentRoomTitle) currentRoomTitle.textContent = currentRoomName;
    if (renameInput && document.activeElement !== renameInput) {
        renameInput.value = currentRoomName;
    }
}

// Kliknięcie "Nowa rozmowa" tworzy unikalny pokój
if (newChatBtn) {
    newChatBtn.onclick = () => {
        currentRoomId = 'room_' + Date.now();
        currentRoomName = 'Nowa rozmowa';
        
        if (renameInput) renameInput.value = currentRoomName;
        if (chatMessagesEl) chatMessagesEl.innerHTML = '';
        
        loadRooms();
        loadMessages();
    };
}

// Funkcja usuwania pokoju po ID
async function deleteRoom(rId) {
    if (!confirm(`Czy na pewno chcesz trwale usunąć tę rozmowę?`)) return;

    const { error } = await supabaseClient
        .from('messages')
        .delete()
        .eq('room_id', rId);

    if (error) {
        alert('Błąd podczas usuwania pokoju: ' + error.message);
        return;
    }

    if (currentRoomId === rId) {
        currentRoomId = 'main-chat';
        currentRoomName = 'Główny czat';
    }

    await loadRooms();
    await loadMessages();
}

async function loadMessages() {
    if (!supabaseClient) return;
    const { data, error } = await supabaseClient
        .from('messages')
        .select('*')
        .eq('room_id', currentRoomId)
        .order('id', { ascending: true });

    if (error) {
        console.error('Błąd pobierania wiadomości:', error);
        return;
    }

    renderMessages(data || []);
}

function renderMessages(messages) {
    if (!chatMessagesEl) return;
    chatMessagesEl.innerHTML = '';
    messages.forEach(msg => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${msg.role === 'model' ? 'assistant' : 'user'}`;

        const authorDiv = document.createElement('div');
        authorDiv.className = 'message-author';
        authorDiv.textContent = msg.role === 'model' ? 'Gemini' : (msg.author || 'Użytkownik');

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = msg.content;

        if (msg.file_data && msg.file_mime && msg.file_mime.startsWith('image/')) {
            const img = document.createElement('img');
            img.className = 'message-image';
            img.src = `data:${msg.file_mime};base64,${msg.file_data}`;
            contentDiv.appendChild(img);
        }

        msgDiv.appendChild(authorDiv);
        msgDiv.appendChild(contentDiv);
        chatMessagesEl.appendChild(msgDiv);
    });
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

function setupRealtime() {
    if (!supabaseClient) return;
    supabaseClient
        .channel('public:messages')
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages' }, payload => {
            if (payload.new.room_id === currentRoomId) {
                loadMessages();
            }
            loadRooms();
        })
        .subscribe();
}

// Wysyłanie wiadomości z załącznikiem
async function sendMessage() {
    if (!messageInput) return;
    const text = messageInput.value.trim();
    if (!text && !selectedFileBase64) return;

    messageInput.value = '';
    messageInput.style.height = 'auto';

    if (!supabaseClient) return;

    const messagePayload = {
        author: username,
        content: text || (selectedFile ? `[Załącznik: ${selectedFile.name}]` : ''),
        role: 'user',
        room_id: currentRoomId
    };

    if (selectedFileBase64) {
        messagePayload.file_data = selectedFileBase64;
        messagePayload.file_mime = selectedFileMime;
    }

    const { error: userErr } = await supabaseClient.from('messages').insert(messagePayload);

    if (userErr) {
        alert('Błąd zapisu wiadomości: ' + userErr.message);
        return;
    }

    if (removeFileBtn) removeFileBtn.click();
    await loadMessages();

    const { data: allMsgs } = await supabaseClient
        .from('messages')
        .select('*')
        .eq('room_id', currentRoomId)
        .order('id', { ascending: true });

    try {
        const res = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: allMsgs || [] })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Błąd serwera');

        await supabaseClient.from('messages').insert({
            author: 'Gemini',
            content: data.response,
            role: 'model',
            room_id: currentRoomId
        });

        await loadMessages();

    } catch (err) {
        console.error(err);
        await supabaseClient.from('messages').insert({
            author: 'System',
            content: `⚠️ Błąd: ${err.message}`,
            role: 'model',
            room_id: currentRoomId
        });
        await loadMessages();
    }
}

// Event Listeners i automatyczne rozszerzanie pola tekstowego
if (sendBtn) sendBtn.onclick = sendMessage;

if (messageInput) {
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    messageInput.onkeydown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
            messageInput.style.height = 'auto';
        }
    };
    
    // Obsługa wklejania ze schowka (Ctrl + V)
    messageInput.addEventListener('paste', (e) => {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let item of items) {
            if (item.kind === 'file') {
                const file = item.getAsFile();
                if (!file) continue;

                selectedFile = file;
                if (fileNameEl) fileNameEl.textContent = `📎 ${file.name || 'screenshot.png'} (ze schowka)`;
                if (filePreview) filePreview.style.display = 'flex';

                const reader = new FileReader();
                reader.onload = function(uploadEvent) {
                    selectedFileBase64 = uploadEvent.target.result.split(',')[1];
                    selectedFileMime = file.type;
                };
                reader.readAsDataURL(file);
                
                e.preventDefault();
                break;
            }
        }
    });
}

if (toggleSidebarBtn && sidebar) {
    toggleSidebarBtn.onclick = () => {
        sidebar.classList.toggle('hidden');
    };
}

if (renameBtn) {
    renameBtn.onclick = async () => {
        if (!renameInput || !supabaseClient) return;
        const newName = renameInput.value.trim();
        if (!newName || newName === currentRoomName) return;

        currentRoomName = newName;
        if (currentRoomTitle) currentRoomTitle.textContent = currentRoomName;
        loadRooms();
    };
}

init();