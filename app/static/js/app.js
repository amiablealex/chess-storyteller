/* ============================================
   Chess Storyteller — Client JS
   ============================================ */

// ---- State ----
let currentStory = '';
let currentMeta = null;
let currentPgn = '';
let currentParams = {};
let currentFilename = '';  // Set when loaded from saved story
let isEditing = false;
let teleprompterActive = false;
let teleprompterScrolling = false;
let teleprompterAnimationId = null;
let scrollPosition = 0;

// ---- Init: Check for ?load= parameter ----
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const loadFile = params.get('load');
    if (loadFile) {
        loadSavedStory(loadFile);
    }
});

// ---- Control Buttons ----
document.querySelectorAll('.control-options').forEach(group => {
    group.querySelectorAll('.control-option').forEach(btn => {
        btn.addEventListener('click', () => {
            group.querySelectorAll('.control-option').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
});

// ---- File Upload ----
document.getElementById('pgnFile').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        document.getElementById('fileName').textContent = file.name;
        const reader = new FileReader();
        reader.onload = (ev) => {
            document.getElementById('pgnInput').value = ev.target.result;
        };
        reader.readAsText(file);
    }
});

// ---- Generate Story ----
async function generateStory() {
    const btn = document.getElementById('generateBtn');
    const pgnText = document.getElementById('pgnInput').value.trim();

    if (!pgnText) {
        showError('Paste a PGN or upload a .pgn file first.');
        return;
    }

    const verbosity = getActiveValue('verbosity');
    const length = getActiveValue('length');
    const mood = getActiveValue('mood');
    const perspective = getActiveValue('perspective');

    const formData = new FormData();
    formData.append('pgn_text', pgnText);
    formData.append('verbosity', verbosity);
    formData.append('length', length);
    formData.append('mood', mood);
    formData.append('perspective', perspective);

    btn.classList.add('loading');
    btn.disabled = true;

    try {
        const response = await fetch('/analyse', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            showError(data.error || 'Something went wrong.');
            return;
        }

        currentStory = data.story;
        currentMeta = data.meta;
        currentPgn = data.pgn || pgnText;
        currentParams = data.params || { verbosity, length, mood };
        currentFilename = '';  // New generation, no saved filename yet

        displayStory(data.story, data.meta);

    } catch (err) {
        showError('Could not connect to the server. Is it running?');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// ---- Load Saved Story ----
async function loadSavedStory(filename) {
    try {
        const response = await fetch(`/stories/${filename}`);
        const data = await response.json();

        if (!response.ok) {
            showError(data.error || 'Could not load story.');
            return;
        }

        currentStory = data.story;
        currentMeta = data.meta;
        currentPgn = data.pgn || '';
        currentParams = data.params || {};
        currentFilename = filename;

        // Populate PGN input
        if (data.pgn) {
            document.getElementById('pgnInput').value = data.pgn;
        }

        displayStory(data.story, data.meta);

    } catch (err) {
        showError('Could not load saved story.');
    }
}

// ---- Nav State ----
function updateNav(hasStory) {
    const storiesBtn = document.getElementById('navStoriesBtn');
    const newBtn = document.getElementById('navNewBtn');
    if (hasStory) {
        storiesBtn.style.display = 'none';
        newBtn.style.display = 'inline-flex';
    } else {
        storiesBtn.style.display = 'inline-flex';
        newBtn.style.display = 'none';
    }
}

function requestNewStory() {
    // If there's an unsaved story, prompt
    if (currentStory && !currentFilename) {
        document.getElementById('newStoryModal').style.display = 'flex';
        return;
    }
    // If story is saved or no story, just reset
    resetToNew();
}

async function saveAndNew() {
    document.getElementById('newStoryModal').style.display = 'none';
    await doSave('');
    resetToNew();
}

function discardAndNew() {
    document.getElementById('newStoryModal').style.display = 'none';
    resetToNew();
}

function cancelNew() {
    document.getElementById('newStoryModal').style.display = 'none';
}

function resetToNew() {
    currentStory = '';
    currentMeta = null;
    currentPgn = '';
    currentParams = {};
    currentFilename = '';
    isEditing = false;

    // Reset UI
    document.getElementById('pgnInput').value = '';
    document.getElementById('fileName').textContent = '';
    document.getElementById('gameMeta').style.display = 'none';
    document.getElementById('storyText').style.display = 'none';
    document.getElementById('storyText').innerHTML = '';
    document.getElementById('storyEdit').style.display = 'none';
    document.querySelector('.story-placeholder').style.display = 'flex';
    document.getElementById('actionBar').style.display = 'none';
    document.getElementById('providerInfo').style.display = 'none';

    // Reset controls to defaults
    document.querySelectorAll('.control-options').forEach(group => {
        group.querySelectorAll('.control-option').forEach((btn, i) => {
            // Second option is default for verbosity/length, first for mood/perspective
            btn.classList.remove('active');
        });
    });
    // Set defaults
    setControlDefault('perspective', 'auto');
    setControlDefault('verbosity', 'balanced');
    setControlDefault('length', 'medium');
    setControlDefault('mood', 'calm');

    updateNav(false);

    // Clear URL params
    window.history.replaceState({}, '', '/');
}

function setControlDefault(param, value) {
    const group = document.querySelector(`[data-param="${param}"]`);
    if (!group) return;
    group.querySelectorAll('.control-option').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.value === value);
    });
}

// ---- Display Story ----
function displayStory(story, meta) {
    const metaEl = document.getElementById('gameMeta');
    document.getElementById('metaWhite').textContent = meta.white;
    document.getElementById('metaBlack').textContent = meta.black;
    document.getElementById('metaResult').textContent = meta.result;
    metaEl.style.display = 'flex';

    const placeholder = document.querySelector('.story-placeholder');
    const storyText = document.getElementById('storyText');
    placeholder.style.display = 'none';
    storyText.style.display = 'block';

    const paragraphs = story.split(/\n\n+/).filter(p => p.trim());
    storyText.innerHTML = paragraphs.map(p => `<p>${escapeHtml(p.trim())}</p>`).join('');

    // Reset edit mode
    if (isEditing) toggleEdit();

    document.getElementById('actionBar').style.display = 'flex';

    const providerInfo = document.getElementById('providerInfo');
    if (meta.provider && meta.model) {
        document.getElementById('providerText').textContent = `Generated by ${meta.model} via ${meta.provider}`;
        providerInfo.style.display = 'block';
    }

    document.getElementById('outputPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });

    updateNav(true);
}

// ---- Edit ----
function toggleEdit() {
    const storyText = document.getElementById('storyText');
    const storyEdit = document.getElementById('storyEdit');
    const editBtn = document.getElementById('editBtn');

    if (isEditing) {
        // Save edits back to state
        currentStory = storyEdit.value;
        storyEdit.style.display = 'none';
        storyText.style.display = 'block';

        // Re-render the display
        const paragraphs = currentStory.split(/\n\n+/).filter(p => p.trim());
        storyText.innerHTML = paragraphs.map(p => `<p>${escapeHtml(p.trim())}</p>`).join('');

        editBtn.classList.remove('editing');
        editBtn.innerHTML = editBtn.innerHTML.replace('Done', 'Edit');
        isEditing = false;
    } else {
        // Enter edit mode
        storyEdit.value = currentStory;
        storyText.style.display = 'none';
        storyEdit.style.display = 'block';
        storyEdit.focus();

        editBtn.classList.add('editing');
        editBtn.innerHTML = editBtn.innerHTML.replace('Edit', 'Done');
        isEditing = true;
    }
}

// ---- Save ----
async function saveStory() {
    // If editing, grab latest text
    if (isEditing) {
        currentStory = document.getElementById('storyEdit').value;
    }

    if (!currentStory) {
        showError('No story to save.');
        return;
    }

    // If already saved, show overwrite modal
    if (currentFilename) {
        document.getElementById('overwriteModal').style.display = 'flex';
        return;
    }

    // First save — just save
    await doSave('');
}

async function confirmSave(overwrite) {
    document.getElementById('overwriteModal').style.display = 'none';
    await doSave(overwrite ? currentFilename : '');
}

function cancelSave() {
    document.getElementById('overwriteModal').style.display = 'none';
}

async function doSave(filename) {
    const saveBtn = document.getElementById('saveBtn');

    try {
        const response = await fetch('/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                story: currentStory,
                meta: currentMeta,
                pgn: currentPgn,
                params: currentParams,
                filename: filename,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            showError(data.error || 'Could not save.');
            return;
        }

        currentFilename = data.filename;
        saveBtn.classList.add('saved');
        const origHTML = saveBtn.innerHTML;
        saveBtn.innerHTML = saveBtn.innerHTML.replace('Save', 'Saved');
        setTimeout(() => {
            saveBtn.classList.remove('saved');
            saveBtn.innerHTML = saveBtn.innerHTML.replace('Saved', 'Save');
        }, 2000);

    } catch (err) {
        showError('Could not save story.');
    }
}

// ---- Copy ----
async function copyStory() {
    if (isEditing) {
        currentStory = document.getElementById('storyEdit').value;
    }
    if (!currentStory) return;

    try {
        await navigator.clipboard.writeText(currentStory);
        const btn = document.getElementById('copyBtn');
        btn.classList.add('copied');
        btn.innerHTML = btn.innerHTML.replace('Copy', 'Copied');
        setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = btn.innerHTML.replace('Copied', 'Copy');
        }, 2000);
    } catch {
        showError('Could not copy to clipboard.');
    }
}

// ---- Teleprompter ----
function toggleTeleprompter() {
    const overlay = document.getElementById('teleprompterOverlay');

    if (teleprompterActive) {
        overlay.classList.remove('active');
        teleprompterActive = false;
        teleprompterScrolling = false;
        cancelAnimationFrame(teleprompterAnimationId);
        document.removeEventListener('keydown', handleTeleprompterKeys);
    } else {
        // Use latest text (including edits)
        if (isEditing) {
            currentStory = document.getElementById('storyEdit').value;
        }
        if (!currentStory) return;

        document.getElementById('teleprompterText').textContent = currentStory;
        overlay.classList.add('active');
        teleprompterActive = true;
        scrollPosition = 0;
        document.getElementById('teleprompterText').style.transform = 'translateX(-50%) translateY(0px)';

        document.addEventListener('keydown', handleTeleprompterKeys);

        setTimeout(() => {
            teleprompterScrolling = true;
            scrollTeleprompter();
        }, 1500);
    }
}

function scrollTeleprompter() {
    if (!teleprompterActive || !teleprompterScrolling) return;

    const speed = parseFloat(document.getElementById('tpSpeed').value);
    scrollPosition -= speed;

    const textEl = document.getElementById('teleprompterText');
    textEl.style.transform = `translateX(-50%) translateY(${scrollPosition}px)`;

    const scrollContainer = document.getElementById('teleprompterScroll');
    const maxScroll = textEl.offsetHeight - scrollContainer.offsetHeight * 0.4;
    if (Math.abs(scrollPosition) < maxScroll) {
        teleprompterAnimationId = requestAnimationFrame(scrollTeleprompter);
    } else {
        teleprompterScrolling = false;
    }
}

function handleTeleprompterKeys(e) {
    if (e.key === 'Escape') {
        toggleTeleprompter();
    } else if (e.key === ' ') {
        e.preventDefault();
        teleprompterScrolling = !teleprompterScrolling;
        if (teleprompterScrolling) {
            scrollTeleprompter();
        }
    }
}

// ---- Helpers ----
function getActiveValue(param) {
    const group = document.querySelector(`[data-param="${param}"]`);
    const active = group.querySelector('.control-option.active');
    return active ? active.dataset.value : '';
}

function showError(message) {
    const toast = document.getElementById('errorToast');
    toast.textContent = message;
    toast.classList.add('visible');
    setTimeout(() => toast.classList.remove('visible'), 4000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
