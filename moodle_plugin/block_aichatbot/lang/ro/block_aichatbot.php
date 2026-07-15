<?php
defined('MOODLE_INTERNAL') || die();

$string['pluginname']              = 'Asistent AI';
$string['aichatbot:addinstance']   = 'Adaugă blocul Asistent AI';
$string['aichatbot:myaddinstance'] = 'Adaugă blocul Asistent AI pe Moodle';

$string['placeholder']   = 'Pune o întrebare despre curs...';
$string['send']          = 'Trimite';
$string['thinking']      = 'Se gândește...';
$string['error']         = 'Eroare la conectarea cu serviciul AI. Încearcă din nou.';
$string['welcome']       = 'Bună! Sunt asistentul tău AI. Întreabă-mă orice despre materialele cursului.';
$string['notconfigured'] = 'Asistentul AI nu este configurat. Setează URL-ul API în setările blocului.';
$string['sources']       = 'Surse: ';

$string['settings_general']           = 'Setări conexiune';
$string['settings_api_url']           = 'URL API Chatbot';
$string['settings_api_url_desc']      = 'URL-ul backend-ului FastAPI (ex: http://10.202.40.130:8010)';
$string['settings_api_key']           = 'Cheie API';
$string['settings_api_key_desc']      = 'Cheia de autorizare pentru API (lasă gol dacă nu e necesar)';
$string['settings_default_lang']      = 'Limbă implicită';
$string['settings_default_lang_desc'] = 'Limba implicită pentru răspunsurile AI când limba utilizatorului este necunoscută';
