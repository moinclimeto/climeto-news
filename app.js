document.addEventListener('DOMContentLoaded', () => {
    init();
    setupEventListeners();
});

async function init() {
    await fetchPosts();
    await loadSettings();
}

let allPosts = [];
const activeFilters = {
    twitter: new Set(),
    linkedin: new Set(),
    youtube: new Set(),
    news: new Set(),
    reddit: new Set(),
    facebook: new Set()
};

async function fetchPosts() {
    try {
        const response = await fetch('/api/posts');
        const data = await response.json();
        
        allPosts = data.data;
        updateUI();
    } catch (error) {
        console.error("Error fetching posts", error);
        showToast("Error loading posts from database");
    }
}

function getPrefix(plat) {
    if (plat === 'twitter') return 'tw';
    if (plat === 'linkedin') return 'li';
    if (plat === 'youtube') return 'yt';
    if (plat === 'reddit') return 'rdt';
    if (plat === 'facebook') return 'fb';
    return 'news';
}

function updateUI() {
    const platforms = ['twitter', 'linkedin', 'youtube', 'news', 'reddit', 'facebook'];
    platforms.forEach(plat => {
        let platformPosts = allPosts.filter(p => p.platform === plat);
        setupFilterBar(plat, platformPosts);
        
        const selected = activeFilters[plat];
        if (selected.size > 0) {
            platformPosts = platformPosts.filter(p => p.keyword && selected.has(p.keyword));
        }
        
        // Ensure posts are strictly sorted by newest first
        platformPosts.sort((a, b) => new Date(b.createdAtISO || 0) - new Date(a.createdAtISO || 0));
        
        document.getElementById(`${getPrefix(plat)}-count`).textContent = platformPosts.length;
        
        if (plat === 'twitter') renderTwitter(platformPosts);
        else if (plat === 'linkedin') renderLinkedin(platformPosts);
        else if (plat === 'youtube') renderYoutube(platformPosts);
        else if (plat === 'news') renderNews(platformPosts);
        else if (plat === 'reddit') renderReddit(platformPosts);
        else if (plat === 'facebook') renderFacebook(platformPosts);
    });
}

function updatePlatformFeed(platform) {
    let platformPosts = allPosts.filter(p => p.platform === platform);
    const selected = activeFilters[platform];
    if (selected.size > 0) {
        platformPosts = platformPosts.filter(p => p.keyword && selected.has(p.keyword));
    }
    
    // Ensure posts are strictly sorted by newest first
    platformPosts.sort((a, b) => new Date(b.createdAtISO || 0) - new Date(a.createdAtISO || 0));
    
    document.getElementById(`${getPrefix(platform)}-count`).textContent = platformPosts.length;
    
    if (platform === 'twitter') renderTwitter(platformPosts);
    else if (platform === 'linkedin') renderLinkedin(platformPosts);
    else if (platform === 'youtube') renderYoutube(platformPosts);
    else if (platform === 'news') renderNews(platformPosts);
    else if (platform === 'reddit') renderReddit(platformPosts);
    else if (platform === 'facebook') renderFacebook(platformPosts);
}

function setupFilterBar(platform, posts) {
    const filterBar = document.getElementById(`${platform}-filter-bar`);
    if (!filterBar) return;
    
    const keywords = new Set();
    posts.forEach(p => { if (p.keyword) keywords.add(p.keyword); });
    
    if (keywords.size === 0) {
        filterBar.innerHTML = '';
        return;
    }
    
    filterBar.innerHTML = '';
    const selected = activeFilters[platform];
    
    keywords.forEach(kw => {
        const chip = document.createElement('div');
        chip.className = 'filter-chip';
        if (selected.has(kw)) chip.classList.add('active');
        chip.textContent = kw;
        
        chip.addEventListener('click', () => {
            if (selected.has(kw)) {
                selected.delete(kw);
                chip.classList.remove('active');
            } else {
                selected.add(kw);
                chip.classList.add('active');
            }
            updatePlatformFeed(platform);
        });
        
        filterBar.appendChild(chip);
    });
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        document.getElementById('tw-token').value = settings.twitter_auth_token || '';
        document.getElementById('tw-ct0').value = settings.twitter_ct0 || '';
        document.getElementById('li-at').value = settings.linkedin_li_at || '';
        document.getElementById('li-jsession').value = settings.linkedin_jsessionid || '';
        document.getElementById('fb-c-user').value = settings.fb_c_user || '';
        document.getElementById('fb-xs').value = settings.fb_xs || '';
    } catch (e) {
        console.error("Could not load settings", e);
    }
}

function setupEventListeners() {
    const modal = document.getElementById('settings-modal');
    
    // Tab switching logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const columns = document.querySelectorAll('.column');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            columns.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const target = btn.getAttribute('data-target');
            document.querySelector('.' + target).classList.add('active');
        });
    });
    
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
            { key: 'linkedin_jsessionid', value: document.getElementById('li-jsession').value },
            { key: 'fb_c_user', value: document.getElementById('fb-c-user').value },
            { key: 'fb_xs', value: document.getElementById('fb-xs').value }
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
        triggerFetch(e.currentTarget, null);
    });

    const singleBtns = document.querySelectorAll('.fetch-single-btn');
    singleBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const platform = e.currentTarget.getAttribute('data-platform');
            triggerFetch(e.currentTarget, platform);
        });
    });
}

function showConfirm(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm-modal');
        const msgEl = document.getElementById('confirm-msg');
        const proceedBtn = document.getElementById('confirm-proceed-btn');
        const cancelBtn = document.getElementById('confirm-cancel-btn');

        msgEl.textContent = message;
        modal.classList.add('active');

        const handleProceed = () => {
            cleanup();
            resolve(true);
        };

        const handleCancel = () => {
            cleanup();
            resolve(false);
        };

        const cleanup = () => {
            proceedBtn.removeEventListener('click', handleProceed);
            cancelBtn.removeEventListener('click', handleCancel);
            modal.classList.remove('active');
        };

        proceedBtn.addEventListener('click', handleProceed);
        cancelBtn.addEventListener('click', handleCancel);
    });
}

async function triggerFetch(btn, platform) {
    let confirmMsg = "";
    if (platform === 'twitter') {
        confirmMsg = "Twitter: Have you saved the latest auth_token and ct0 in settings?";
    } else if (platform === 'linkedin') {
        confirmMsg = "LinkedIn: Have you saved the latest li_at and JSESSIONID in settings?";
    } else if (platform === 'facebook') {
        confirmMsg = "Facebook: Have you saved the latest c_user and xs in settings?";
    } else if (!platform) {
        confirmMsg = "Fetch All: Have you saved the latest cookies for Twitter, LinkedIn, and Facebook in settings?";
    }

    if (confirmMsg) {
        const isConfirmed = await showConfirm(confirmMsg);
        if (!isConfirmed) {
            return;
        }
    }

    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ Fetching...';
    btn.disabled = true;
    
    try {
        const url = platform ? `/api/fetch?platform=${platform}` : '/api/fetch';
        await fetch(url, { method: 'POST' });
        showToast(`Fetch started for ${platform || 'all platforms'}!`);
        
        // Poll for updates every 10 seconds
        const interval = setInterval(async () => {
            await fetchPosts();
        }, 10000);
        
        // Re-enable button after 2 minutes assuming it finishes
        setTimeout(() => {
            clearInterval(interval);
            btn.innerHTML = originalText;
            btn.disabled = false;
            showToast(`Fetch process for ${platform || 'all'} likely completed.`);
            fetchPosts();
        }, 120000);
        
    } catch (e) {
        showToast("Failed to trigger fetch");
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
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

function renderNews(posts) {
    const container = document.getElementById('news-feed');
    if (posts.length === 0) {
        container.innerHTML = '<div class="no-data">No News found in database.</div>';
        return;
    }
    container.innerHTML = posts.map(post => {
        const date = new Date(post.createdAtISO).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        return `
            <div class="card">
                <div class="card-header">
                    <div class="avatar-fallback" style="background: var(--news-color)">📰</div>
                    <div class="author-info">
                        <div class="author-name">${post.author.name || 'News Source'}</div>
                        <div class="author-meta">${date !== 'Invalid Date' ? date : ''}</div>
                    </div>
                </div>
                <div class="card-content">
                    ${linkify(post.text || '')}
                </div>
            </div>
        `;
    }).join('');
}

function renderReddit(posts) {
    const container = document.getElementById('reddit-feed');
    if (posts.length === 0) {
        container.innerHTML = '<div class="no-data">No Reddit posts found (Check API credentials).</div>';
        return;
    }
    container.innerHTML = posts.map(post => {
        let mediaHtml = '';
        if (post.media && post.media.length > 0) {
            mediaHtml = `<div class="card-media"><img src="${post.media[0].url}" alt="Reddit media" loading="lazy"></div>`;
        }
        const date = new Date(post.createdAtISO).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        return `
            <div class="card">
                <div class="card-header">
                    <div class="avatar-fallback" style="background: var(--reddit-color)">🤖</div>
                    <div class="author-info">
                        <div class="author-name">${post.author.name || 'u/deleted'}</div>
                        <div class="author-meta">${date !== 'Invalid Date' ? date : ''}</div>
                    </div>
                </div>
                <div class="card-content">
                    ${linkify(post.text || '')}
                </div>
                ${mediaHtml}
                <div class="card-footer">
                    <div class="stat"><span>⬆️</span> ${post.metrics?.score || 0}</div>
                    <div class="stat"><span>💬</span> ${post.metrics?.comments || 0}</div>
                </div>
            </div>
        `;
    }).join('');
}

function renderFacebook(posts) {
    const container = document.getElementById('facebook-feed');
    if (posts.length === 0) {
        container.innerHTML = '<div class="no-data">No Facebook posts found (Check cookies).</div>';
        return;
    }
    container.innerHTML = posts.map(post => {
        let mediaHtml = '';
        if (post.media && post.media.length > 0) {
            mediaHtml = `<div class="card-media"><img src="${post.media[0].url}" alt="FB media" loading="lazy"></div>`;
        }
        const date = new Date(post.createdAtISO).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        return `
            <div class="card">
                <div class="card-header">
                    <img src="${post.author.profileImageUrl || ''}" class="avatar" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 24 24\\' fill=\\'%2394a3b8\\'%3E%3Cpath d=\\'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z\\'/%3E%3C/svg%3E'">
                    <div class="author-info">
                        <div class="author-name">${post.author.name || 'Facebook User'}</div>
                        <div class="author-meta">${date !== 'Invalid Date' ? date : ''}</div>
                    </div>
                </div>
                <div class="card-content">
                    ${linkify(post.text || '')}
                </div>
                ${mediaHtml}
                <div class="card-footer">
                    <div class="stat"><span>👍</span> ${post.metrics?.likes || 0}</div>
                    <div class="stat"><span>💬</span> ${post.metrics?.comments || 0}</div>
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
