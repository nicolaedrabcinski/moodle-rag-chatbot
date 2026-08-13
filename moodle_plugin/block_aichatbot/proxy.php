<?php
/**
 * Server-side proxy for the AI chatbot API.
 * Browser → this file (same host as Moodle) → backend API (internal)
 * This avoids exposing the backend IP/port to clients.
 */
define('NO_MOODLE_COOKIES', false);
require_once('../../config.php');
require_login();   // must be authenticated

$api_url = get_config('block_aichatbot', 'api_url') ?: 'http://localhost:8010';
$api_key = get_config('block_aichatbot', 'api_key') ?: '';

$body = file_get_contents('php://input');
if (!$body) {
    http_response_code(400);
    die('Empty request');
}

// Validate JSON
$decoded = json_decode($body, true);
if (!$decoded) {
    http_response_code(400);
    die('Invalid JSON');
}

// SSE headers
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');   // disable nginx buffering
header('Connection: keep-alive');

// Flush any existing output buffers
while (ob_get_level()) ob_end_flush();
flush();

$request_headers = ['Content-Type: application/json'];
if ($api_key) {
    $request_headers[] = 'Authorization: Bearer ' . $api_key;
}

$ch = curl_init($api_url . '/api/chat/stream');
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
curl_setopt($ch, CURLOPT_HTTPHEADER, $request_headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, false);
curl_setopt($ch, CURLOPT_TIMEOUT, 120);
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
curl_setopt($ch, CURLOPT_WRITEFUNCTION, function($ch, $data) {
    echo $data;
    flush();
    return strlen($data);
});

$ok = curl_exec($ch);
if (!$ok) {
    $err = curl_error($ch);
    echo "data: " . json_encode(['type' => 'error', 'message' => 'Backend unavailable: ' . $err]) . "\n\n";
    flush();
}
curl_close($ch);
