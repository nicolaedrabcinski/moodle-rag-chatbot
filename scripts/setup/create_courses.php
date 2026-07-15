<?php
/**
 * Creates two FCIM courses: Filosofie and Etica, Comunicare si Drept
 * Run inside the Moodle container:
 *   php /scripts/create_courses.php
 */

define('CLI_SCRIPT', true);
require('/var/www/html/config.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/lib/blocklib.php');
require_once($CFG->dirroot . '/blocks/moodleblock.class.php');
require_once($CFG->dirroot . '/enrol/manual/externallib.php');

// ─── Helpers ─────────────────────────────────────────────────────────────────

function create_fcim_category(string $name, string $idnumber): int {
    global $DB;

    if ($existing = $DB->get_record('course_categories', ['idnumber' => $idnumber])) {
        echo "  Category exists: {$existing->name} (id={$existing->id})\n";
        return (int)$existing->id;
    }

    $cat = new stdClass();
    $cat->name      = $name;
    $cat->idnumber  = $idnumber;
    $cat->parent    = 0;
    $cat->visible   = 1;
    $cat->sortorder = 0;

    $category = core_course_category::create($cat);
    echo "  Created category: {$name} (id={$category->id})\n";
    return (int)$category->id;
}

function create_moodle_course(array $data): stdClass {
    global $DB;

    if ($existing = $DB->get_record('course', ['shortname' => $data['shortname']])) {
        echo "  Course already exists: {$existing->fullname} (id={$existing->id})\n";
        return $existing;
    }

    $course_data = (object)[
        'fullname'        => $data['fullname'],
        'shortname'       => $data['shortname'],
        'category'        => $data['category'],
        'idnumber'        => $data['idnumber'],
        'summary'         => $data['summary'],
        'summaryformat'   => FORMAT_HTML,
        'format'          => 'topics',
        'numsections'     => count($data['sections']),
        'lang'            => 'ro',
        'enablecompletion'=> 1,
        'startdate'       => mktime(0, 0, 0, 9, 1, 2026),
        'enddate'         => mktime(0, 0, 0, 6, 30, 2027),
        'visible'         => 1,
        'showgrades'      => 1,
        'newsitems'       => 3,
        'groupmode'       => 0,
    ];

    $course = create_course($course_data);
    echo "  Created course: {$course->fullname} (id={$course->id})\n";
    return $course;
}

function set_section_name(int $courseid, int $section_num, string $name, string $summary = ''): void {
    global $DB;
    $section = $DB->get_record('course_sections', [
        'course'  => $courseid,
        'section' => $section_num,
    ]);
    if ($section) {
        $section->name    = $name;
        $section->summary = $summary;
        $section->summaryformat = FORMAT_HTML;
        $section->visible = 1;
        $DB->update_record('course_sections', $section);
    }
}

function add_forum(stdClass $course, int $section, string $name, string $intro): void {
    global $DB, $CFG;
    require_once($CFG->dirroot . '/mod/forum/lib.php');

    if ($DB->record_exists('forum', ['course' => $course->id, 'name' => $name])) {
        return;
    }

    $forum = (object)[
        'course'        => $course->id,
        'type'          => 'news',
        'name'          => $name,
        'intro'         => $intro,
        'introformat'   => FORMAT_HTML,
        'assessed'      => 0,
        'timemodified'  => time(),
        'warnafter'     => 0,
        'blockafter'    => 0,
        'blockperiod'   => 0,
        'completiondiscussions' => 0,
    ];

    $forum->id = forum_add_instance($forum, null);
    $cm = add_moduleinfo((object)[
        'modulename' => 'forum',
        'module'     => $DB->get_field('modules', 'id', ['name' => 'forum']),
        'instance'   => $forum->id,
        'course'     => $course->id,
        'section'    => $section,
        'visible'    => 1,
    ], $course, null);
}

function add_ai_block(stdClass $course): void {
    global $DB, $CFG;

    $context = context_course::instance($course->id);

    // Check if block already exists
    if ($DB->record_exists('block_instances', [
        'blockname'     => 'aichatbot',
        'parentcontextid' => $context->id,
    ])) {
        echo "    AI block already exists in course {$course->shortname}\n";
        return;
    }

    $block = (object)[
        'blockname'         => 'aichatbot',
        'parentcontextid'   => $context->id,
        'showinsubcontexts' => 1,
        'requiredbytheme'   => 0,
        'pagetypepattern'   => 'course-view-*',
        'subpagepattern'    => null,
        'defaultregion'     => 'side-pre',
        'defaultweight'     => -10,
        'configdata'        => '',
        'timecreated'       => time(),
        'timemodified'      => time(),
    ];

    $DB->insert_record('block_instances', $block);
    echo "    AI block added to course {$course->shortname}\n";
}

function enroll_admin_as_teacher(stdClass $course): void {
    global $DB;

    $admin    = get_admin();
    $context  = context_course::instance($course->id);
    $role_id  = $DB->get_field('role', 'id', ['shortname' => 'editingteacher']);
    $enrol    = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual']);

    if (!$enrol) {
        echo "    Warning: manual enrol plugin not found for course {$course->id}\n";
        return;
    }

    $enrol_plugin = enrol_get_plugin('manual');
    $enrol_plugin->enrol_user($enrol, $admin->id, $role_id);
    echo "    Admin enrolled as teacher\n";
}

// ─── Main ────────────────────────────────────────────────────────────────────

echo "\n=== Creating FCIM courses ===\n\n";

// 1. Category
echo "[1] Category\n";
$cat_id = create_fcim_category('FCIM — Discipline generale', 'FCIM-GEN');

// ─── Course 1: Filosofie ──────────────────────────────────────────────────────

echo "\n[2] Course: Filosofie\n";

$filosofie_sections = [
    1 => 'Introducere în filosofie',
    2 => 'Filosofia antică',
    3 => 'Filosofia medievală',
    4 => 'Filosofia modernă',
    5 => 'Filosofia contemporană',
    6 => 'Ontologie și metafizică',
    7 => 'Gnoseologie și epistemologie',
    8 => 'Logică și argumentare',
    9 => 'Etica filosofică',
    10 => 'Filosofia minții și conștiinței',
    11 => 'Lucrări practice și seminare',
    12 => 'Evaluare și recapitulare',
];

$filosofie = create_moodle_course([
    'fullname'  => 'Filosofie',
    'shortname' => 'FILOS-2026',
    'idnumber'  => 'FCIM-FILOS-2026',
    'category'  => $cat_id,
    'sections'  => $filosofie_sections,
    'summary'   => '<p>Cursul de Filosofie oferă o introducere cuprinzătoare în gândirea filosofică de la Antichitate până în prezent. Studenții vor explora marile întrebări despre existență, cunoaștere, etică și logică, prin analiza operelor marilor filosofi ai omenirii.</p>
<p><strong>Obiective:</strong></p>
<ul>
  <li>Înțelegerea principalelor curente și școli filosofice</li>
  <li>Dezvoltarea gândirii critice și analitice</li>
  <li>Aplicarea metodelor filosofice la probleme contemporane</li>
  <li>Formarea abilităților de argumentare logică</li>
</ul>
<p><em>Limbă de predare: Română</em></p>',
]);

// Set section names
foreach ($filosofie_sections as $num => $name) {
    set_section_name($filosofie->id, $num, $name);
}
echo "  Sections configured\n";

add_ai_block($filosofie);
enroll_admin_as_teacher($filosofie);

// ─── Course 2: Etica, Comunicare si Drept ─────────────────────────────────────

echo "\n[3] Course: Etica, Comunicare si Drept\n";

$etica_sections = [
    1  => 'Etica: noțiuni fundamentale',
    2  => 'Teorii etice clasice',
    3  => 'Etica profesională în IT',
    4  => 'Comunicare și retorică',
    5  => 'Comunicare profesională și academică',
    6  => 'Comunicare digitală și social media',
    7  => 'Introducere în drept',
    8  => 'Dreptul proprietății intelectuale',
    9  => 'Legislația în domeniul IT',
    10 => 'Protecția datelor personale (GDPR)',
    11 => 'Dreptul contractelor și muncii',
    12 => 'Evaluare finală',
];

$etica = create_moodle_course([
    'fullname'  => 'Etica, Comunicare si Drept',
    'shortname' => 'ECD-2026',
    'idnumber'  => 'FCIM-ECD-2026',
    'category'  => $cat_id,
    'sections'  => $etica_sections,
    'summary'   => '<p>Cursul integrează trei domenii esențiale pentru formarea unui specialist IT complet: etica profesională, comunicarea eficientă și cunoștințele juridice de bază. Studenții vor dobândi abilități practice necesare pentru activitatea profesională în mediul digital.</p>
<p><strong>Obiective:</strong></p>
<ul>
  <li>Înțelegerea principiilor etice în contextul profesional IT</li>
  <li>Dezvoltarea abilităților de comunicare orală și scrisă</li>
  <li>Cunoașterea cadrului legal aplicabil activității IT</li>
  <li>Aplicarea normelor GDPR și protecției datelor</li>
</ul>
<p><em>Limbă de predare: Română</em></p>',
]);

foreach ($etica_sections as $num => $name) {
    set_section_name($etica->id, $num, $name);
}
echo "  Sections configured\n";

add_ai_block($etica);
enroll_admin_as_teacher($etica);

// ─── Summary ─────────────────────────────────────────────────────────────────

echo "\n=== Done! ===\n";
echo "Filosofie:              http://10.202.40.130/course/view.php?id={$filosofie->id}\n";
echo "Etica, Comunicare...:  http://10.202.40.130/course/view.php?id={$etica->id}\n\n";
