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

let currentRoomId = 'main-chat';
let currentRoomName = 'Główny czat';
let currentUser = null;

let selectedFile = null;
let selectedFileBase64 = null;
let selectedFileMime = null;

// Elementy DOM
const authOverlay = document.getElementById('auth-overlay');
const appContainer = document.getElementById('app-container');
const authEmailInput = document.getElementById('auth-email');
const authPasswordInput = document.getElementById('auth-password');
const loginBtn = document.getElementById('login-btn');
const signupBtn = document.getElementById('signup-btn');
const authErrorEl = document.getElementById('auth-error');
const userEmailDisplay = document.getElementById('user-email-display');
const logoutBtn = document.getElementById('logout-btn');

const roomsListEl = document.getElementById('rooms-list');
const chatMessagesEl = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
const sidebar = document.getElementById('sidebar');
const currentRoomTitle = document.getElementById('current-room-title');
const currentRoomContainer = document.getElementById('current-room-container');
const renameInput = document.getElementById('rename-input');

const fileInput = document.getElementById('file-input');
const attachBtn = document.getElementById('attach-btn');
const filePreview = document.getElementById('file-preview');
const fileNameEl = document.getElementById('file-name');
const removeFileBtn = document.getElementById('remove-file-btn');

// --- AUTENTYKACJA ---
async function checkUserSession() {
    if (!supabaseClient) return;
    const { data: { session } } = await supabaseClient.auth.getSession();
    if (session) {
        currentUser = session.user;
        showApp();
    } else {
        showAuth();
    }
}

function showApp() {
    if (authOverlay) authOverlay.classList.add('hidden');
    if (appContainer) appContainer.classList.remove('hidden');
    if (userEmailDisplay) userEmailDisplay.textContent = `👤 ${currentUser.email}`;
    init();
}

function showAuth() {
    if (authOverlay) authOverlay.classList.remove('hidden');
    if (appContainer) appContainer.classList.add('hidden');
}

if (loginBtn) {
    loginBtn.onclick = async () => {
        const email = authEmailInput.value.trim();
        const password = authPasswordInput.value.trim();
        authErrorEl.textContent = '';

        const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
        if (error) {
            authErrorEl.textContent = error.message;
        } else {
            currentUser = data.user;
            showApp();
        }
    };
}

if (signupBtn) {
    signupBtn.onclick = async () => {
        const email = authEmailInput.value.trim();
        const password = authPasswordInput.value.trim();
        authErrorEl.textContent = '';

        const { data, error } = await supabaseClient.auth.signUp({ email, password });
        if (error) {
            authErrorEl.textContent = error.message;
        } else {
            alert('Konto zostało utworzone! Możesz się teraz zalogować.');
        }
    };
}

if (logoutBtn) {
    logoutBtn.onclick = async () => {
        await supabaseClient.auth.signOut();
        currentUser = null;
        showAuth();
    };
}

// Obsługa plików
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
    await loadRooms();
    await loadMessages();
    setupRealtime();
}

// Przechowywanie niestandardowych nazw pokoi w pamięci przeglądarki (localStorage) lub mapie
const roomNamesMap = new Map();

async function loadRooms() {
    if (!supabaseClient) return;
    const { data, error } = await supabaseClient.from('messages').select('room_id, content').order('id', { ascending: true });
    if (error) return;

    const roomMap = new Map();
    roomMap.set('main-chat', roomNamesMap.get('main-chat') || 'Główny czat');

    (data || []).forEach(m => {
        const rId = m.room_id || 'main-chat';
        if (!roomMap.has(rId)) {
            const defaultName = rId === 'main-chat' ? 'Główny czat' : `Rozmowa (${rId.slice(-4)})`;
            roomMap.set(rId, roomNamesMap.get(rId) || defaultName);
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
}

if (newChatBtn) {
    newChatBtn.onclick = () => {
        currentRoomId = 'room_' + Date.now();
        currentRoomName = 'Nowa rozmowa';
        roomNamesMap.set(currentRoomId, currentRoomName);
        if (chatMessagesEl) chatMessagesEl.innerHTML = '';
        loadRooms();
        loadMessages();
    };
}

async function deleteRoom(rId) {
    if (!confirm(`Czy na pewno chcesz trwale usunąć tę rozmowę?`)) return;
    const { error } = await supabaseClient.from('messages').delete().eq('room_id', rId);
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

    if (error) return;
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
        let authorName = msg.role === 'model' ? 'Gemini' : (msg.author || 'Użytkownik');
        authorDiv.textContent = authorName;

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

// Obsługa edycji nazwy pokoju w miejscu (po kliknięciu w nagłówek)
if (currentRoomContainer && currentRoomTitle && renameInput) {
    currentRoomContainer.onclick = () => {
        currentRoomTitle.classList.add('hidden');
        renameInput.classList.remove('hidden');
        renameInput.value = currentRoomName;
        renameInput.focus();
        renameInput.select();
    };

    const saveRename = () => {
        const newName = renameInput.value.trim();
        if (newName && newName !== currentRoomName) {
            currentRoomName = newName;
            roomNamesMap.set(currentRoomId, currentRoomName);
            loadRooms();
        }
        renameInput.classList.add('hidden');
        currentRoomTitle.classList.remove('hidden');
    };

    renameInput.onblur = saveRename;
    renameInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
            saveRename();
        } else if (e.key === 'Escape') {
            renameInput.classList.add('hidden');
            currentRoomTitle.classList.remove('hidden');
        }
    };
}

// Wysyłanie wiadomości
async function sendMessage() {
    if (!messageInput) return;
    const text = messageInput.value.trim();
    if (!text && !selectedFileBase64) return;

    messageInput.value = '';
    messageInput.style.height = 'auto';

    if (!supabaseClient || !currentUser) return;

    const messagePayload = {
        author: currentUser.email,
        user_id: currentUser.id,
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

// Uruchomienie
checkUserSession();