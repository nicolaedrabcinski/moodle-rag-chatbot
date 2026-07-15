<?php
defined('MOODLE_INTERNAL') || die();

$string['pluginname']              = 'AI Assistant';
$string['aichatbot:addinstance']   = 'Add AI Assistant block';
$string['aichatbot:myaddinstance'] = 'Add AI Assistant block to My Moodle';

$string['placeholder']   = 'Ask a question about the course...';
$string['send']          = 'Send';
$string['thinking']      = 'Thinking...';
$string['error']         = 'Error connecting to AI service. Please try again.';
$string['welcome']       = 'Hello! I\'m your AI assistant. Ask me anything about your course materials.';
$string['notconfigured'] = 'AI Assistant is not configured. Please set the API URL in block settings.';
$string['sources']       = 'Sources: ';

$string['settings_general']          = 'Connection settings';
$string['settings_api_url']          = 'Chatbot API URL';
$string['settings_api_url_desc']     = 'URL of the FastAPI chatbot backend (e.g. http://10.202.40.130:8010)';
$string['settings_api_key']          = 'API Key';
$string['settings_api_key_desc']     = 'Authorization key for the chatbot API (leave empty if not required)';
$string['settings_default_lang']     = 'Default language';
$string['settings_default_lang_desc'] = 'Default language for AI responses when user language is unknown';
