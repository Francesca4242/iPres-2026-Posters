/* ==========================================================================
   Themed trails - "tourist walks" through the poster hall.

   Each trail is declarative. To add, remove or retune one, edit the TRAILS
   table below; no other file needs to change. A poster joins a trail when it
   matches ANY of:
     themes    - theme ids from data/posters.json
     keywords  - a case-insensitive substring of any of its keywords/topics
     text      - a case-insensitive substring of its title/abstract/keywords
   ...and is then excluded if it matches `not`. Stops are ordered by map slot,
   so following a trail really is a walk round the room.
   ========================================================================== */

const TRAILS = [
  {
    id: 'workflows',
    name: 'The Workflow Wander',
    emoji: '\u{1F501}',
    color: '#0b82c6',
    blurb: 'Pipelines, packagers and process diagrams. Start here if you want to steal a good workflow and take it home.',
    keywords: ['workflow'],
    text: ['workflow', 'pipeline', 'packager'],
  },
  {
    id: 'infrastructure',
    name: 'Bits, Boxes and Tape',
    emoji: '\u{1F5C4}️',
    color: '#0769a3',
    blurb: 'The unglamorous machinery underneath everything: storage media, containers, autoscaling and bit-level care.',
    themes: ['infrastructure'],
    not: { text: ['advocacy'] },
  },
  {
    id: 'letting-go',
    name: 'The Art of Letting Go',
    emoji: '\u{1F342}',
    color: '#eab308',
    blurb: 'Appraisal, triage, retention and deletion. Nobody can keep everything, and these posters say so out loud.',
    themes: ['ingest'],
    keywords: ['appraisal', 'retention', 'selection', 'collection assessment'],
    text: ['deletion', 'deaccession', 'triag', 'redundan', 'retention', 'backlog'],
  },
  {
    id: 'access',
    name: 'Access All Areas',
    emoji: '\u{1F50D}',
    color: '#06b6d4',
    blurb: 'Getting things back out again: discovery, delivery, emulation, captions and reading rooms of the future.',
    themes: ['access'],
  },
  {
    id: 'metadata',
    name: 'Describe It Properly',
    emoji: '\u{1F3F7}️',
    color: '#10b981',
    blurb: 'Schemas, standards, provenance and the quiet heroism of good description.',
    themes: ['metadata'],
  },
  {
    id: 'people',
    name: 'People Power',
    emoji: '\u{1F91D}',
    color: '#ef4444',
    blurb: 'Networks, national initiatives, training and advocacy. Preservation is a team sport.',
    themes: ['community'],
    keywords: ['people', 'community', 'collaboration', 'engagement'],
  },
  {
    id: 'money',
    name: 'Show Me the Evidence',
    emoji: '\u{1F4CA}',
    color: '#f97316',
    blurb: 'Maturity models, surveys, audits and costs. For anyone who has to justify the budget on Monday.',
    themes: ['management'],
    keywords: ['assessment', 'audit', 'costs', 'risk'],
  },
  {
    id: 'ethics',
    name: 'Do the Right Thing',
    emoji: '⚖️',
    color: '#d946ef',
    blurb: 'Law, ethics, sensitive material and the environmental bill for keeping everything forever.',
    themes: ['policy'],
    keywords: ['sustainability', 'governance', 'ethical'],
  },
  {
    id: 'formats',
    name: 'Format Frontier',
    emoji: '\u{1F9EC}',
    color: '#8b5cf6',
    blurb: 'Fixity, characterisation, migration and the long tail of awkward file formats.',
    themes: ['formats'],
    keywords: ['fixity', 'validation', 'characterisation', 'migration'],
  },
  {
    id: 'robots',
    name: 'Rise of the Machines',
    emoji: '\u{1F916}',
    color: '#111827',
    blurb: 'Where automation, speech recognition and AI are quietly turning up in preservation practice.',
    text: ['artificial intelligence', 'machine learning', ' ai ', 'ai-', 'automated', 'automatic', 'speech recognition', 'llm'],
  },
  {
    id: 'worldwide',
    name: 'Postcards from Everywhere',
    emoji: '\u{1F30D}',
    color: '#0ea5e9',
    blurb: 'A lap of the globe: posters from outside Europe, from Vancouver to Beijing to Rio and back.',
    orgMatch: ['brazil', 'canada', 'china', 'united states', 'america', 'australia', 'new zealand', 'japan', 'egypt'],
  },
  {
    id: 'quick',
    name: 'The Coffee-Break Quickie',
    emoji: '☕',
    color: '#b45309',
    blurb: 'Only fifteen minutes? One poster from each theme, in the order you will walk past them.',
    oneFromEachTheme: true,
  },
];

const haystack = (poster) => [
  poster.title, poster.abstract, (poster.keywords || []).join(' '), (poster.topics || []).join(' '),
].join(' ').toLowerCase();

const orgText = (poster) => (poster.organisations || []).join(' ').toLowerCase();

function matchesRule(poster, rule) {
  if (!rule) return false;
  if (rule.themes && rule.themes.some((t) => (poster.themes || []).includes(t))) return true;
  if (rule.keywords) {
    const fields = [...(poster.keywords || []), ...(poster.topics || [])].map((k) => k.toLowerCase());
    if (rule.keywords.some((needle) => fields.some((field) => field.includes(needle)))) return true;
  }
  if (rule.text) {
    const text = haystack(poster);
    if (rule.text.some((needle) => text.includes(needle))) return true;
  }
  if (rule.orgMatch) {
    const orgs = orgText(poster);
    if (rule.orgMatch.some((needle) => orgs.includes(needle))) return true;
  }
  return false;
}

/* Build every trail's ordered stop list from the current poster set. */
function buildTrails(posters) {
  /* Ordered by board so a trail is a real walk. A poster with no board - one
     presented online, or simply not placed yet - falls to the end and is then
     ordered by title, so the list is stable rather than arbitrary. */
  const bySlot = (a, b) =>
    (a.slot?.number || 9999) - (b.slot?.number || 9999)
    || a.title.localeCompare(b.title);
  return TRAILS.map((trail) => {
    let stops;
    if (trail.oneFromEachTheme) {
      const picked = new Map();
      [...posters].sort(bySlot).forEach((poster) => {
        const theme = (poster.themes || [])[0];
        if (theme && !picked.has(theme)) picked.set(theme, poster);
      });
      stops = [...picked.values()].sort(bySlot);
    } else {
      stops = posters
        .filter((poster) => matchesRule(poster, trail) && !matchesRule(poster, trail.not))
        .sort(bySlot);
    }
    return { ...trail, stops };
  }).filter((trail) => trail.stops.length >= 3);
}

/* ---------- "Which trail is for me?" quiz ---------- */

const QUIZ = [
  {
    id: 'role',
    question: 'What brought you to iPRES this year?',
    options: [
      { label: 'I build and run the systems', weights: { infrastructure: 3, formats: 2, workflows: 2 } },
      { label: 'I look after collections', weights: { 'letting-go': 3, metadata: 2, access: 2 } },
      { label: 'I have to make the case upstairs', weights: { money: 3, ethics: 2, people: 2 } },
      { label: 'I am here for the people', weights: { people: 3, worldwide: 2, quick: 1 } },
    ],
  },
  {
    id: 'itch',
    question: 'Which problem is nagging at you right now?',
    options: [
      { label: 'Our process is held together with string', weights: { workflows: 3, formats: 1 } },
      { label: 'We are drowning in stuff we may not need', weights: { 'letting-go': 3, money: 1 } },
      { label: 'Nobody can find anything', weights: { access: 3, metadata: 2 } },
      { label: 'Everyone keeps saying "just use AI"', weights: { robots: 3, ethics: 1 } },
    ],
  },
  {
    id: 'time',
    question: 'How long have you got?',
    options: [
      { label: 'Fifteen minutes, tops', weights: { quick: 4 } },
      { label: 'A full coffee break', weights: { workflows: 1, access: 1, metadata: 1 } },
      { label: 'I am doing the whole hall', weights: { infrastructure: 1, people: 1, worldwide: 1, formats: 1 } },
    ],
  },
  {
    id: 'mood',
    question: 'Pick a mood.',
    options: [
      { label: 'Practical: show me the tools', weights: { workflows: 2, infrastructure: 2, formats: 1 } },
      { label: 'Philosophical: ask me hard questions', weights: { ethics: 3, 'letting-go': 2 } },
      { label: 'Curious: surprise me', weights: { worldwide: 2, robots: 2, quick: 1 } },
      { label: 'Evidence-driven: show me the numbers', weights: { money: 3, metadata: 1 } },
    ],
  },
];

function scoreQuiz(answers, trails) {
  const scores = {};
  answers.forEach(({ questionId, optionIndex }) => {
    const question = QUIZ.find((q) => q.id === questionId);
    const option = question && question.options[optionIndex];
    if (!option) return;
    Object.entries(option.weights).forEach(([trailId, weight]) => {
      scores[trailId] = (scores[trailId] || 0) + weight;
    });
  });
  return trails
    .map((trail) => ({ trail, score: scores[trail.id] || 0 }))
    .sort((a, b) => b.score - a.score || b.trail.stops.length - a.trail.stops.length)
    .filter((entry) => entry.score > 0);
}
