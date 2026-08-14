/**
 * AI Chatbot block — FCIM ELSE Platform
 * Streaming SSE version
 */
define(['jquery'], function($) {
    'use strict';

    var cfg = {};

    // ── DOM helpers ──────────────────────────────────────────────────────────

    function el(id) { return document.getElementById(id); }

    function scrollBottom() {
        var msgs = el('aichatbot-messages');
        if (msgs) msgs.scrollTop = msgs.scrollHeight;
    }

    function setLoading(on) {
        var btn   = el('aichatbot-send');
        var input = el('aichatbot-input');
        var ind   = el('aichatbot-thinking');
        if (btn)   { btn.disabled = on; btn.textContent = on ? '...' : ((cfg.strings && cfg.strings.send) || 'Send'); }
        if (input) input.disabled = on;
        if (ind)   ind.style.display = on ? 'flex' : 'none';
    }

    // ── Text rendering ───────────────────────────────────────────────────────

    function renderMarkdown(text) {
        return text
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\[(\d+)\]/g, '<sup class="acb-cite">[$1]</sup>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
    }

    function formatTopic(topic) {
        if (!topic) return '';
        // Strip leading number prefix like "09_"
        var t = topic.replace(/^\d+_/, '');
        // Replace underscores/hyphens with spaces and title-case
        return t.replace(/[_-]/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
    }

    function buildSourcesHtml(sources) {
        if (!sources || !sources.length) return '';
        // Deduplicate by topic (or file_path), keep first occurrence per unique topic
        var seen = {};
        var unique = [];
        sources.forEach(function(s) {
            var key = (s.topic || s.file_path || s.document || '') + '_' + (s.index || '');
            if (!seen[key]) {
                seen[key] = true;
                unique.push(s);
            }
        });
        var items = unique.map(function(s) {
            var label = formatTopic(s.topic || s.file_path) || s.document || '';
            return '<span class="acb-source-item">' +
                '<span class="acb-source-num">[' + (s.index || '?') + ']</span> ' +
                '<span class="acb-source-label">' + label + '</span>' +
                '</span>';
        });
        return '<div class="acb-sources">📄 ' + items.join('') + '</div>';
    }

    // ── Static message (used for user + welcome) ─────────────────────────────

    function addMessage(role, text, sources) {
        var msgs = el('aichatbot-messages');
        if (!msgs) return;

        var wrap = document.createElement('div');
        wrap.className = 'acb-msg acb-msg--' + role;

        var bubble = document.createElement('div');
        bubble.className = 'acb-bubble';
        bubble.innerHTML = '<p>' + renderMarkdown(text) + '</p>';
        wrap.appendChild(bubble);

        if (sources && sources.length) {
            var srcHtml = buildSourcesHtml(sources);
            if (srcHtml) {
                var srcNode = document.createElement('div');
                srcNode.innerHTML = srcHtml;
                wrap.appendChild(srcNode.firstChild);
            }
        }

        msgs.appendChild(wrap);
        scrollBottom();
    }

    function addError(text) {
        var msgs = el('aichatbot-messages');
        if (!msgs) return;
        var wrap = document.createElement('div');
        wrap.className = 'acb-msg acb-msg--error';
        wrap.innerHTML = '<div class="acb-bubble">⚠️ ' + text + '</div>';
        msgs.appendChild(wrap);
        scrollBottom();
    }

    // ── Streaming bubble ─────────────────────────────────────────────────────

    function createStreamBubble() {
        var msgs = el('aichatbot-messages');
        if (!msgs) return null;
        var wrap = document.createElement('div');
        wrap.className = 'acb-msg acb-msg--bot';
        var bubble = document.createElement('div');
        bubble.className = 'acb-bubble acb-bubble--streaming';
        var p = document.createElement('p');
        bubble.appendChild(p);
        wrap.appendChild(bubble);
        msgs.appendChild(wrap);
        scrollBottom();
        return {wrap: wrap, bubble: bubble, p: p};
    }

    // ── Main send (streaming) ────────────────────────────────────────────────

    function send(question) {
        question = question.trim();
        if (!question) return;

        var input = el('aichatbot-input');
        if (input) input.value = '';

        addMessage('user', question, null);
        setLoading(true);

        var headers = {'Content-Type': 'application/json'};
        if (cfg.apiKey) headers['Authorization'] = 'Bearer ' + cfg.apiKey;

        var body = JSON.stringify({
            question:  question,
            course_id: cfg.courseId || 'general',
            language:  cfg.lang || 'ro',
        });

        var streamEl  = createStreamBubble();
        var fullText  = '';
        var metaSources = [];

        fetch(cfg.apiUrl, {method: 'POST', headers: headers, body: body})
            .then(function(res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);

                var reader  = res.body.getReader();
                var decoder = new TextDecoder();
                var buffer  = '';

                function finish() {
                    if (streamEl) {
                        streamEl.bubble.classList.remove('acb-bubble--streaming');
                        // Append sources node
                        if (metaSources.length) {
                            var srcHtml = buildSourcesHtml(metaSources);
                            if (srcHtml) {
                                var srcNode = document.createElement('div');
                                srcNode.innerHTML = srcHtml;
                                streamEl.wrap.appendChild(srcNode.firstChild);
                            }
                        }
                        // If no text was received, remove empty bubble
                        if (!fullText && streamEl.wrap.parentNode) {
                            streamEl.wrap.parentNode.removeChild(streamEl.wrap);
                        }
                    }
                    setLoading(false);
                    if (input) input.focus();
                }

                function processChunks() {
                    return reader.read().then(function(result) {
                        if (result.done) {
                            finish();
                            return;
                        }

                        buffer += decoder.decode(result.value, {stream: true});
                        var lines = buffer.split('\n');
                        buffer = lines.pop(); // keep incomplete last line

                        for (var i = 0; i < lines.length; i++) {
                            var line = lines[i];
                            if (!line.startsWith('data: ')) continue;
                            var data = line.slice(6).trim();
                            if (!data || data === '[DONE]') {
                                if (data === '[DONE]') { finish(); return; }
                                continue;
                            }

                            try {
                                var parsed = JSON.parse(data);
                                if (parsed.type === 'token' && parsed.text) {
                                    fullText += parsed.text;
                                    if (streamEl && streamEl.p) {
                                        streamEl.p.innerHTML = renderMarkdown(fullText);
                                        scrollBottom();
                                    }
                                } else if (parsed.type === 'meta' && parsed.sources) {
                                    metaSources = parsed.sources;
                                }
                            } catch (e) {
                                // Plain text fallback (non-JSON chunk)
                                fullText += data;
                                if (streamEl && streamEl.p) {
                                    streamEl.p.textContent = fullText;
                                    scrollBottom();
                                }
                            }
                        }

                        return processChunks();
                    });
                }

                return processChunks();
            })
            .catch(function(err) {
                console.error('[aichatbot]', err);
                if (streamEl && streamEl.wrap && streamEl.wrap.parentNode) {
                    streamEl.wrap.parentNode.removeChild(streamEl.wrap);
                }
                addError((cfg.strings && cfg.strings.error) || 'Eroare de conexiune. Încearcă din nou.');
                setLoading(false);
                if (input) input.focus();
            });
    }

    // ── Init ─────────────────────────────────────────────────────────────────

    return {
        init: function(config) {
            cfg = config || {};

            var input = el('aichatbot-input');
            var btn   = el('aichatbot-send');

            if (btn) {
                btn.addEventListener('click', function() {
                    if (input) send(input.value);
                });
            }

            if (input) {
                input.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        send(input.value);
                    }
                });
                input.focus();
            }

            if (cfg.strings && cfg.strings.welcome) {
                addMessage('bot', cfg.strings.welcome, null);
            }
        }
    };
});
