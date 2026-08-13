<?php
defined('MOODLE_INTERNAL') || die();

class block_aichatbot extends block_base {

    public function init() {
        $this->title = get_string('pluginname', 'block_aichatbot');
    }

    public function applicable_formats() {
        return ['all' => false, 'site' => true, 'course' => true, 'mod' => true, 'my' => true];
    }

    public function has_config() { return true; }
    public function instance_allow_multiple() { return false; }

    public function get_content() {
        global $USER, $COURSE;

        if ($this->content !== null) return $this->content;
        $this->content         = new stdClass();
        $this->content->footer = '';

        $api_url = get_config('block_aichatbot', 'api_url');
        $api_key = get_config('block_aichatbot', 'api_key') ?: '';

        if (empty($api_url)) {
            if (has_capability('moodle/site:config', context_system::instance())) {
                $this->content->text = '<p class="alert alert-warning">' .
                    get_string('notconfigured', 'block_aichatbot') . '</p>';
            }
            return $this->content;
        }

        $course_id  = $COURSE->shortname ?? 'general';
        $user_lang  = current_language();

        // Relative URL so it works regardless of which IP/domain the user accesses Moodle through.
        $proxy_url = '/blocks/aichatbot/proxy.php';

        $this->page->requires->js_call_amd('block_aichatbot/chatbot', 'init', [[
            'apiUrl'   => $proxy_url,
            'apiKey'   => '',   // key stays server-side in proxy.php
            'courseId' => $course_id,
            'lang'     => $user_lang,
            'strings'  => [
                'send'    => get_string('send',    'block_aichatbot'),
                'error'   => get_string('error',   'block_aichatbot'),
                'welcome' => get_string('welcome', 'block_aichatbot'),
            ],
        ]]);

        $placeholder = get_string('placeholder', 'block_aichatbot');
        $send_label  = get_string('send', 'block_aichatbot');

        $this->content->text = <<<HTML
<div class="acb-wrap">
  <div id="aichatbot-messages" class="acb-messages" role="log" aria-live="polite"></div>
  <div id="aichatbot-thinking" class="acb-thinking" style="display:none">
    <span class="acb-dot"></span><span class="acb-dot"></span><span class="acb-dot"></span>
  </div>
  <div class="acb-footer">
    <textarea id="aichatbot-input" class="acb-input" rows="2"
      placeholder="{$placeholder}" aria-label="{$placeholder}"></textarea>
    <button id="aichatbot-send" class="acb-send-btn">{$send_label}</button>
  </div>
</div>

<style>
/* ── Container ── */
.acb-wrap {
  display: flex; flex-direction: column;
  height: 420px; font-size: 0.88rem;
  border: 1px solid #dee2e6; border-radius: 8px;
  overflow: hidden; background: #fff;
}

/* ── Messages area ── */
.acb-messages {
  flex: 1; overflow-y: auto; padding: 12px 10px 4px;
  background: #f7f8fc;
  scroll-behavior: smooth;
}
.acb-messages::-webkit-scrollbar { width: 4px; }
.acb-messages::-webkit-scrollbar-thumb { background: #c5cae9; border-radius: 4px; }

/* ── Single message ── */
.acb-msg { display: flex; margin-bottom: 10px; animation: acb-in .18s ease; }
@keyframes acb-in { from { opacity:0; transform:translateY(6px); } to { opacity:1; } }

.acb-msg--user  { justify-content: flex-end; }
.acb-msg--bot   { justify-content: flex-start; flex-direction: column; }
.acb-msg--error { justify-content: flex-start; }

/* ── Bubbles ── */
.acb-bubble {
  max-width: 88%; padding: 8px 12px;
  border-radius: 16px; line-height: 1.5; word-break: break-word;
}
.acb-bubble p { margin: 0 0 4px; }
.acb-bubble p:last-child { margin-bottom: 0; }

.acb-msg--user  .acb-bubble { background:#1a73e8; color:#fff; border-radius:16px 16px 4px 16px; }
.acb-msg--bot   .acb-bubble { background:#fff; color:#202124; border:1px solid #e0e0e0; border-radius:4px 16px 16px 16px; }
.acb-msg--error .acb-bubble { background:#fff3e0; color:#e65100; border:1px solid #ffcc02; border-radius:8px; font-size:.84rem; }

/* ── Sources ── */
.acb-sources { font-size: .75rem; color: #888; margin: 3px 0 0 4px; }

/* ── Streaming cursor ── */
.acb-bubble--streaming p:last-child::after {
  content: '▋'; color: #1a73e8; margin-left: 2px;
  animation: acb-blink .7s step-end infinite;
}
@keyframes acb-blink { 0%,100%{opacity:1} 50%{opacity:0} }

/* ── Thinking dots ── */
.acb-thinking { display: flex; align-items: center; gap: 4px; padding: 6px 14px; }
.acb-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #bbb;
  animation: acb-bounce 1.2s ease-in-out infinite;
}
.acb-dot:nth-child(2) { animation-delay: .2s; }
.acb-dot:nth-child(3) { animation-delay: .4s; }
@keyframes acb-bounce { 0%,80%,100%{transform:scale(0.7)} 40%{transform:scale(1); background:#1a73e8;} }

/* ── Input area ── */
.acb-footer {
  display: flex; gap: 6px; padding: 8px;
  border-top: 1px solid #e8eaf6; background: #fff;
}
.acb-input {
  flex: 1; resize: none; border: 1px solid #c5cae9; border-radius: 8px;
  padding: 7px 10px; font-size: .88rem; font-family: inherit;
  outline: none; transition: border .15s;
}
.acb-input:focus { border-color: #1a73e8; box-shadow: 0 0 0 2px rgba(26,115,232,.15); }
.acb-send-btn {
  align-self: flex-end; padding: 8px 16px;
  background: #1a73e8; color: #fff; border: none; border-radius: 8px;
  cursor: pointer; font-size: .88rem; font-weight: 600;
  transition: background .15s, opacity .15s;
}
.acb-send-btn:hover:not(:disabled) { background: #1557b0; }
.acb-send-btn:disabled { opacity: .5; cursor: default; }
</style>
HTML;

        return $this->content;
    }
}
