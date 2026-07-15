<?php
defined('MOODLE_INTERNAL') || die();

if ($ADMIN->fulltree) {
    $settings->add(new admin_setting_heading(
        'block_aichatbot/general',
        get_string('settings_general', 'block_aichatbot'),
        ''
    ));

    $settings->add(new admin_setting_configtext(
        'block_aichatbot/api_url',
        get_string('settings_api_url', 'block_aichatbot'),
        get_string('settings_api_url_desc', 'block_aichatbot'),
        'http://10.202.40.130:8010',
        PARAM_URL
    ));

    $settings->add(new admin_setting_configpasswordunmask(
        'block_aichatbot/api_key',
        get_string('settings_api_key', 'block_aichatbot'),
        get_string('settings_api_key_desc', 'block_aichatbot'),
        ''
    ));

    $settings->add(new admin_setting_configselect(
        'block_aichatbot/default_lang',
        get_string('settings_default_lang', 'block_aichatbot'),
        get_string('settings_default_lang_desc', 'block_aichatbot'),
        'ro',
        ['en' => 'English', 'ro' => 'Română', 'ru' => 'Русский']
    ));
}
