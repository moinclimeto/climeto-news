document.addEventListener('DOMContentLoaded', () => {
    init();
    setupEventListeners();
});

async function init() {
    await fetchPosts();
    await loadSettings();
}

async function fetchPosts() {
    try {
        const response = await fetch('/api/posts');
        const data = await response.json();
        
        const twitterPosts = data.data.filter(p => p.platform === 'twitter');
        const linkedinPosts = data.data.filter(p => p.platform === 'linkedin');
        const youtubePosts = data.data.filter(p => p.platform === 'youtube');
        
        document.getElementById('tw-count').textContent = twitterPosts.length;
        document.getElementById('li-count').textContent = linkedinPosts.length;
        document.getElementById('yt-count').textContent = youtubePosts.length;
        
        renderTwitter(twitterPosts);
        renderLinkedin(linkedinPosts);
        renderYoutube(youtubePosts);
    } catch (error) {
        console.error("Error fetching posts", error);
        showToast("Error loading posts from database");
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        document.getElementById('tw-token').value = settings.twitter_auth_token || '';
        document.getElementById('tw-ct0').value = settings.twitter_ct0 || '';
        document.getElementById('li-at').value = settings.linkedin_li_at || '';
        document.getElementById('li-jsession').value = settings.linkedin_jsessionid || '';
    } catch (e) {
        console.error("Could not load settings", e);
    }
}

function setupEventListeners() {
    const modal = document.getElementById('settings-modal');
    
    document.getElementById('settings-btn').addEventListener('click', () => {
        modal.classList.add('active');
    });
    
    document.getElementById('close-modal-btn').addEventListener('click', () => {
        modal.classList.remove('active');
    });
    
    document.getElementById('save-settings-btn').addEventListener('click', async () => {
        const settings = [
            { key: 'twitter_auth_token', value: document.getElementById('tw-token').value },
            { key: 'twitter_ct0', value: document.getElementById('tw-ct0').value },
            { key: 'linkedin_li_at', value: document.getElementById('li-at').value },
            { key: 'linkedin_jsessionid', value: document.getElementById('li-jsession').value }
        ];
        
        try {
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ settings })
            });
            modal.classList.remove('active');
            showToast("Settings saved successfully!");
        } catch (e) {
            showToast("Failed to save settings");
        }
    });

    document.getElementById('fetch-btn').addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Fetching... (Takes time)';
        btn.disabled = true;
        
        try {
            await fetch('/api/fetch', { method: 'POST' });
            showToast("Fetch started in background! Data will update soon.");
            
            // Poll for updates every 10 seconds
            const interval = setInterval(async () => {
                await fetchPosts();
            }, 10000);
            
            // Re-enable button after 2 minutes assuming it finishes
            setTimeout(() => {
                clearInterval(interval);
                btn.innerHTML = originalText;
                btn.disabled = false;
                showToast("Fetch process likely completed.");
                fetchPosts();
            }, 120000);
            
        } catch (e) {
            showToast("Failed to trigger fetch");
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });
}

function renderTwitter(posts) {
    const container = document.getElementById('twitter-feed');
    if (posts.length === 0) {
        container.innerHTML = '<div class="no-data">No Twitter posts found in database.</div>';
        return;
    }

    container.innerHTML = posts.map(post => {
        const author = post.author || {};
        
        let mediaHtml = '';
        if (post.media && post.media.length > 0) {
            mediaHtml = `<div class="card-media"><img src="${post.media[0].url}" alt="Post media" loading="lazy"></div>`;
        }

        const date = new Date(post.createdAtISO).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        return `
            <div class="card">
                <div class="card-header">
                    <img src="${author.profileImageUrl || ''}" class="avatar" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 24 24\\' fill=\\'%2394a3b8\\'%3E%3Cpath d=\\'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z\\'/%3E%3C/svg%3E'">
                    <div class="author-info">
                        <div class="author-name">${author.name || 'Unknown'}</div>
                        <div class="author-meta">@${author.screenName || 'unknown'} • ${date !== 'Invalid Date' ? date : ''}</div>
                    </div>
                </div>
                <div class="card-content">
                    ${linkify(post.text || '')}
                </div>
                ${mediaHtml}
                <div class="card-footer">
                    <div class="stat"><span>♡</span> ${post.metrics?.likes || 0}</div>
                    <div class="stat"><span>↻</span> ${post.metrics?.retweets || 0}</div>
                </div>
            </div>
        `;
    }).join('');
}

function renderLinkedin(posts) {
    const container = document.getElementById('linkedin-feed');
    if (posts.length === 0) {
        container.innerHTML = '<div class="no-data">No LinkedIn posts found in database.</div>';
        return;
    }

    container.innerHTML = posts.map(post => {
        const initial = post.companyName.charAt(0).toUpperCase();
        
        return `
            <div class="card">
                <div class="card-header">
                    <div class="avatar-fallback">${initial}</div>
                    <div class="author-info">
                        <div class="author-name">${post.companyName}</div>
                        <div class="author-meta">${post.bio}</div>
                    </div>
                </div>
                <div class="card-content">
                    ${linkify(post.text)}
                </div>
            </div>
        `;
    }).join('');
}

function renderYoutube(posts) {
    const container = document.getElementById('youtube-feed');
    if (posts.length === 0) {
        container.innerHTML = '<div class="no-data">No YouTube videos found in database.</div>';
        return;
    }

    container.innerHTML = posts.map(post => {
        const author = post.author || {};
        
        let mediaHtml = '';
        if (post.media && post.media.length > 0) {
            mediaHtml = `<div class="card-media"><img src="${post.media[0].url}" alt="Video thumbnail" loading="lazy"></div>`;
        }

        const date = new Date(post.createdAtISO).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        return `
            <div class="card">
                <div class="card-header">
                    <img src="${author.profileImageUrl || ''}" class="avatar" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 24 24\\' fill=\\'%2394a3b8\\'%3E%3Cpath d=\\'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z\\'/%3E%3C/svg%3E'">
                    <div class="author-info">
                        <div class="author-name">${author.name || 'Unknown Channel'}</div>
                        <div class="author-meta">${date !== 'Invalid Date' ? date : ''}</div>
                    </div>
                </div>
                <div class="card-content">
                    ${linkify(post.text || '')}
                </div>
                ${mediaHtml}
                <div class="card-footer">
                    <div class="stat"><span>👁</span> ${post.metrics?.views || '0 views'}</div>
                </div>
            </div>
        `;
    }).join('');
}

function linkify(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, '<a href="$1" target="_blank" style="color: var(--accent); text-decoration: none;">$1</a>');
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}
