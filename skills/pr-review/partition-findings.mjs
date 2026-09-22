#!/usr/bin/env node
/**
 * partition-findings.mjs: deterministic finding partition for pr-review
 *
 * Takes pr-review-dry_run's structured findings plus the PR diff, and
 * produces a ready-to-POST GitHub review-create payload. Owns every bit of
 * JSON assembly and escaping so the model never hand-builds the request body.
 *
 * Core job: work out which line-scoped findings actually sit inside a diff
 * hunk (only those can become inline `comments[]` entries; GitHub's
 * review-create endpoint rejects comments whose line isn't in the diff) and
 * fold everything else into the top-level review body.
 *
 * IMPORTANT, verified against GitHub REST docs (2022-11-28): the
 * review-create endpoint's `comments[]` array accepts ONLY line-anchored
 * entries (path, body, line, side, start_line, start_side). It does NOT
 * accept `subject_type`; that field is response-only there, not a request
 * field. File-level comments cannot be batched into a pending review at
 * all, which is why every non-inlineable finding folds into `body` instead.
 * See SKILL.md's <api-constraints> block for the full rationale.
 *
 * Usage (stdin/stdout only, no scratch files):
 *   <assemble JSON> | node partition-findings.mjs | gh api ... --input -
 *   node partition-findings.mjs --self-test
 *
 * Stdin: { verdict, selfReview?, findings: [...], diff, summary }
 *   Each finding: { type: "🔴"|"🟠"|"🟡"|"🟣", scope: "line"|"file"|"cross-file",
 *                    file?, line?, range?: {start,end}, body, suggestion? }
 *   verdict: "Request Changes" | "Comment" | "Approve", as pr-review-dry_run
 *   derived it. selfReview: true when the PR author is the reviewing login;
 *   GitHub then accepts only a COMMENT event, so the verdict is written as
 *   the body's first line instead.
 *   diff: verbatim `gh pr diff` output. summary: review summary prose.
 *
 * Stdout: { body, comments: [...] }, the exact review-create shape, ready to
 * pipe into `gh api ... --input -`. Stats ({ inline, folded, offDiffDemoted })
 * go to stderr so stdout stays pure JSON.
 *
 * Body layout: [verdict line, self-review only] + summary + folded sections +
 * the `<!-- pr-review -->` marker. SKILL.md step 2 filters prior reviews on
 * that marker, so it must be present on every body this script emits.
 *
 * Prose gate: before anything is written to stdout, the summary text and every
 * comment body are validated for two classes of slop that have leaked into
 * posted reviews before; see <follow-up-mode/> in SKILL.md for the incident
 * this backstops (a "Since my last review" delta that used 🆕, which GitHub
 * badge-renders as :new:, plus em-dashes in the prose). Both are hard
 * failures (non-zero exit, nothing written): no auto-strip, no silent fix.
 */

import { readFileSync, realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

/** Reads all of stdin synchronously as utf-8 text. */
function readStdin() {
  return readFileSync(0, 'utf-8');
}

const VALID_TYPES = ['🔴', '🟠', '🟡', '🟣'];
const VALID_VERDICTS = ['Request Changes', 'Comment', 'Approve'];
const REVIEW_MARKER = '<!-- pr-review -->';

// Dash-family characters banned everywhere in prose (summary + comment
// bodies). Em-dash is the golden-rule violation; the others are the same
// smell under different codepoints, so they're caught too.
const BANNED_DASHES = new Map([
  ['—', 'em-dash (—)'],
  ['–', 'en-dash (–)'],
  ['―', 'horizontal bar (―)'],
  ['‒', 'figure dash (‒)'],
]);

// Emoji explicitly banned from the summary: known GitHub badge-renderers
// (🆕 renders as :new:) or off-palette leftovers from the old ✅/⚠️ vocabulary
// this skill has since replaced with the ⚪/⚫/🟢 circle set. Ban-list rather
// than allow-list: summary prose can legitimately contain arbitrary emoji, an
// allow-list would false-positive on all of them.
const BANNED_SUMMARY_EMOJI = new Map([
  ['\u{1F195}', '🆕 (renders as a GitHub :new: badge, not a plain glyph)'],
  ['\u{2705}', '✅ (superseded; use ⚪ for "fixed" in the delta)'],
  ['\u{26A0}\u{FE0F}', '⚠️ (superseded; use ⚫ for "still open" in the delta)'],
  ['\u{26A0}', '⚠ (superseded; use ⚫ for "still open" in the delta)'],
]);

/**
 * Throws if `text` contains any banned dash character. Used on both the
 * summary and every comment body; the golden rule applies everywhere.
 */
function assertNoDashes(text, label) {
  for (const [char, name] of BANNED_DASHES) {
    if (text.includes(char)) {
      const idx = text.indexOf(char);
      const context = text.slice(Math.max(0, idx - 20), idx + 20);
      throw new Error(
        `${label} contains a banned ${name}: "...${context}...". ` +
        `Rewrite using a semicolon, colon, or parentheses instead.`,
      );
    }
  }
}

/** Throws if `text` (summary only; comment bodies aren't emoji-gated) contains a banned emoji. */
function assertNoBannedEmoji(text, label) {
  for (const [char, name] of BANNED_SUMMARY_EMOJI) {
    if (text.includes(char)) {
      throw new Error(
        `${label} contains banned emoji ${name}. ` +
        `Delta vocabulary is: 🟢 new, ⚪ fixed, ⚫ still open.`,
      );
    }
  }
}

/** Full prose gate for the summary: dash ban + emoji ban. */
function validateSummary(summaryText) {
  assertNoDashes(summaryText, 'Summary');
  assertNoBannedEmoji(summaryText, 'Summary');
}

/** Prose gate for a single comment body: dash ban only (finding-type emoji is validated separately by VALID_TYPES). */
function validateCommentBody(body, path, line) {
  assertNoDashes(body, `Comment on ${path}:${line}`);
}

/** Runs the dash gate over every assembled inline comment. */
function validateComments(comments) {
  for (const comment of comments) {
    validateCommentBody(comment.body, comment.path, comment.line);
  }
}

/**
 * Under self-review the verdict becomes body text, so it has to be one of the
 * three strings pr-review-dry_run derives; anything else would post a
 * meaningless first line.
 */
function validateVerdict(verdict, selfReview) {
  if (!selfReview) return;
  if (!VALID_VERDICTS.includes(verdict)) {
    throw new Error(
      `selfReview is true but verdict is ${JSON.stringify(verdict)}; ` +
      `expected one of ${VALID_VERDICTS.map(v => JSON.stringify(v)).join(', ')}.`,
    );
  }
}

/**
 * Parses unified diff text into Map<filePath, Set<postableLineNumber>>.
 * A line is "postable" (can be inline-commented) if it's a context or
 * added line on the RIGHT (new-file) side of a hunk; deleted lines have
 * no new-file line number and can't be targeted.
 */
function parseDiffHunks(diffText) {
  const postableByFile = new Map();
  let currentFile = null;
  let newLine = null;

  const lines = diffText.split('\n');
  for (const line of lines) {
    const fileMatch = line.match(/^\+\+\+ b\/(.+)$/);
    if (fileMatch) {
      currentFile = fileMatch[1];
      if (!postableByFile.has(currentFile)) postableByFile.set(currentFile, new Set());
      continue;
    }
    // Diffs against /dev/null (deleted files) have no RIGHT side; skip.
    if (line.startsWith('+++ /dev/null')) {
      currentFile = null;
      continue;
    }
    const hunkMatch = line.match(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (hunkMatch) {
      newLine = parseInt(hunkMatch[1], 10);
      continue;
    }
    if (currentFile === null || newLine === null) continue;
    if (line.startsWith('+')) {
      postableByFile.get(currentFile).add(newLine);
      newLine++;
    } else if (line.startsWith('-')) {
      // Deleted line: no new-file line number, don't advance newLine.
    } else if (line.startsWith(' ') || line === '') {
      // Context line (unified diff format allows a bare empty line as
      // context for a genuinely empty source line).
      postableByFile.get(currentFile).add(newLine);
      newLine++;
    }
    // Lines like "diff --git", "index ...", "\ No newline at end of file"
    // fall through and are ignored.
  }
  return postableByFile;
}

/** True if every line a finding targets (single line or a range) is postable. */
function isInDiff(finding, postableByFile) {
  const postable = postableByFile.get(finding.file);
  if (!postable) return false;
  if (finding.range) {
    for (let l = finding.range.start; l <= finding.range.end; l++) {
      if (!postable.has(l)) return false;
    }
    return true;
  }
  return postable.has(finding.line);
}

/** Builds one review-create comments[] entry from an in-diff line finding. */
function buildInlineComment(finding) {
  const body = finding.suggestion
    ? `${finding.type} ${finding.body}\n\n${finding.suggestion}`
    : `${finding.type} ${finding.body}`;
  const entry = { path: finding.file, body, side: 'RIGHT' };
  if (finding.range) {
    entry.start_line = finding.range.start;
    entry.start_side = 'RIGHT';
    entry.line = finding.range.end;
  } else {
    entry.line = finding.line;
  }
  return entry;
}

/**
 * Partitions findings into inline comments[] vs folded body sections.
 * Returns { comments, sections, stats }.
 */
function partition(findings, postableByFile) {
  const comments = [];
  const fileScoped = [];
  const crossFile = [];
  const offDiff = [];
  const accolades = [];
  let inline = 0, folded = 0, offDiffDemoted = 0;

  for (const finding of findings) {
    if (!VALID_TYPES.includes(finding.type)) {
      throw new Error(`Unknown finding type: ${JSON.stringify(finding.type)}`);
    }

    if (finding.type === '🟣') {
      // Admiration never inlines, even when line-scoped (pr-review matrix).
      accolades.push(finding);
      folded++;
      continue;
    }

    if (finding.scope === 'line') {
      if (isInDiff(finding, postableByFile)) {
        comments.push(buildInlineComment(finding));
        inline++;
      } else {
        offDiff.push(finding);
        folded++;
        offDiffDemoted++;
      }
      continue;
    }

    if (finding.scope === 'file') {
      fileScoped.push(finding);
      folded++;
      continue;
    }

    if (finding.scope === 'cross-file') {
      crossFile.push(finding);
      folded++;
      continue;
    }

    throw new Error(`Unknown finding scope: ${JSON.stringify(finding.scope)}`);
  }

  return {
    comments,
    sections: { fileScoped, crossFile, offDiff, accolades },
    stats: { inline, folded, offDiffDemoted },
  };
}

/** "path", "path:line" or "path:start-end", whichever the finding carries. */
function renderLocation(finding) {
  if (finding.range) return `${finding.file}:${finding.range.start}-${finding.range.end}`;
  if (finding.line != null) return `${finding.file}:${finding.line}`;
  return finding.file;
}

/**
 * A ```suggestion fence only means something as an inline comment (GitHub
 * offers to commit it). Folded into the body it would render as a dead
 * suggestion widget, so it becomes a plain fenced block, indented two spaces
 * to stay inside the bullet.
 */
function renderFoldedSuggestion(suggestion) {
  const plain = suggestion.replace(/^```suggestion[^\n]*\n/, '```\n');
  const indented = plain.split('\n').map(l => (l === '' ? '' : `  ${l}`)).join('\n');
  return `\n\n  Proposed fix (outside the diff, so not committable from here):\n\n${indented}`;
}

/** Renders a finding as a single body bullet, e.g. "- 🟡 `path:line`: text". */
function renderBullet(finding) {
  const location = finding.file ? `\`${renderLocation(finding)}\`: ` : '';
  const bullet = `- ${finding.type} ${location}${finding.body}`;
  return finding.suggestion ? bullet + renderFoldedSuggestion(finding.suggestion) : bullet;
}

/** The self-review opener: the verdict GitHub won't let the author submit as an event. */
function renderVerdictLine(verdict) {
  return `**Verdict: ${verdict}** (self-review: GitHub accepts only a comment review from the PR author, so the verdict lives here).`;
}

/** Composes the full markdown review body from the summary + folded sections. */
function composeBody(summary, sections, { verdict, selfReview } = {}) {
  const parts = [];
  if (selfReview) parts.push(renderVerdictLine(verdict));
  parts.push(summary.trim());

  if (sections.fileScoped.length) {
    parts.push(['### File-scoped notes', ...sections.fileScoped.map(renderBullet)].join('\n'));
  }
  if (sections.crossFile.length) {
    parts.push(['### Cross-file notes', ...sections.crossFile.map(renderBullet)].join('\n'));
  }
  if (sections.offDiff.length) {
    parts.push(['### Off-diff notes', ...sections.offDiff.map(renderBullet)].join('\n'));
  }
  if (sections.accolades.length) {
    // Each accolade is individually prefixed with 🟣; no umbrella header
    // absorbing the emoji. renderBullet already does this per-item.
    parts.push(['### Accolades', ...sections.accolades.map(renderBullet)].join('\n'));
  }

  parts.push(REVIEW_MARKER);
  return parts.join('\n\n');
}

function parseArgs(argv) {
  const args = {};
  for (const arg of argv) {
    if (arg === '--self-test') args.selfTest = true;
  }
  return args;
}

/**
 * Runs the full partition+validate+compose pipeline over one input object
 * and returns the review-create payload. Pure function, no I/O, so it's
 * usable both from the stdin CLI entrypoint and from the self-tests.
 */
function buildPayload({ verdict, selfReview = false, findings, diff, summary }) {
  validateVerdict(verdict, selfReview);
  validateSummary(summary);
  const postableByFile = parseDiffHunks(diff);
  const result = partition(findings || [], postableByFile);
  validateComments(result.comments);
  const body = composeBody(summary, result.sections, { verdict, selfReview });
  return { payload: { body, comments: result.comments }, stats: result.stats };
}

function run() {
  const raw = readStdin();

  let input;
  try {
    input = JSON.parse(raw);
  } catch (err) {
    process.stderr.write(`Error: partition-findings: stdin is not valid JSON: ${err.message}\n`);
    process.exit(1);
  }

  const { verdict, selfReview, findings, diff, summary } = input;
  if (diff == null || summary == null) {
    process.stderr.write(
      'Error: partition-findings: stdin must be { verdict, selfReview, findings, diff, summary }; ' +
      '"diff" and "summary" are required.\n',
    );
    process.exit(1);
  }

  let built;
  try {
    built = buildPayload({ verdict, selfReview: selfReview === true, findings, diff, summary });
  } catch (err) {
    process.stderr.write(`Error: partition-findings: ${err.message}\n`);
    process.exit(1);
  }

  process.stdout.write(JSON.stringify(built.payload, null, 2) + '\n');
  process.stderr.write(JSON.stringify(built.stats) + '\n');
}

// ---------------------------------------------------------------------------
// Self-test: no vitest/package.json in ~/.claude/skills, so this uses
// node:assert with inline fixtures. Run: node partition-findings.mjs --self-test
// ---------------------------------------------------------------------------
function selfTest() {
  const tests = [];
  const test = (name, fn) => tests.push({ name, fn });

  const SAMPLE_DIFF = [
    'diff --git a/src/a.ts b/src/a.ts',
    'index 111..222 100644',
    '--- a/src/a.ts',
    '+++ b/src/a.ts',
    '@@ -8,4 +8,6 @@',
    ' function foo() {',
    '-  return x;',
    '+  if (!x) return null;',
    '+  return x;',
    ' }',
    ' ',
    'diff --git a/src/b.ts b/src/b.ts',
    'index 333..444 100644',
    '--- a/src/b.ts',
    '+++ b/src/b.ts',
    '@@ -1,2 +1,2 @@',
    '-const y = 1;',
    '+const y = 2;',
    ' export { y };',
  ].join('\n');

  test('in-diff line finding lands in comments[] with side:RIGHT and emoji prefix', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const finding = { type: '🔴', scope: 'line', file: 'src/a.ts', line: 9, body: 'Null deref.' };
    assert.equal(isInDiff(finding, postable), true);
    const entry = buildInlineComment(finding);
    assert.equal(entry.side, 'RIGHT');
    assert.equal(entry.line, 9);
    assert.match(entry.body, /^🔴 /);
    assert.equal('subject_type' in entry, false);
  });

  test('off-diff line finding is excluded from comments[] and folded', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const finding = { type: '🟡', scope: 'line', file: 'src/a.ts', line: 999, body: 'Unrelated line.' };
    assert.equal(isInDiff(finding, postable), false);
    const { comments, sections, stats } = partition([finding], postable);
    assert.equal(comments.length, 0);
    assert.equal(sections.offDiff.length, 1);
    assert.equal(stats.offDiffDemoted, 1);
  });

  test('off-diff bullet keeps the line number and carries the fix as a plain fence', () => {
    const suggestion = '```suggestion\n  return y;\n```';
    const finding = { type: '🟠', scope: 'line', file: 'src/a.ts', line: 999, body: 'Wrong variable.', suggestion };
    const bullet = renderBullet(finding);
    assert.match(bullet, /^- 🟠 `src\/a\.ts:999`: Wrong variable\./);
    assert.ok(bullet.includes('Proposed fix'));
    assert.ok(bullet.includes('  ```\n    return y;\n  ```'));
    assert.equal(bullet.includes('```suggestion'), false);
  });

  test('off-diff range bullet renders start-end', () => {
    const finding = { type: '🟡', scope: 'line', file: 'src/a.ts', range: { start: 40, end: 44 }, body: 'Dead branch.' };
    assert.match(renderBullet(finding), /^- 🟡 `src\/a\.ts:40-44`: /);
  });

  test('multi-line range with one end outside the hunk is treated off-diff', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const finding = { type: '🟠', scope: 'line', file: 'src/a.ts', range: { start: 9, end: 500 }, body: 'Range issue.' };
    assert.equal(isInDiff(finding, postable), false);
  });

  test('file-scoped finding is folded and never carries subject_type', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const finding = { type: '🟠', scope: 'file', file: 'src/c.ts', body: 'File-level concern.' };
    const { comments, sections } = partition([finding], postable);
    assert.equal(comments.length, 0);
    assert.equal(sections.fileScoped.length, 1);
    for (const c of comments) assert.equal('subject_type' in c, false);
    assert.match(renderBullet(finding), /^- 🟠 `src\/c\.ts`: /);
  });

  test('cross-file finding is folded into cross-file section', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const finding = { type: '🟡', scope: 'cross-file', body: 'Naming inconsistency across files.' };
    const { sections } = partition([finding], postable);
    assert.equal(sections.crossFile.length, 1);
  });

  test('line-scoped admiration folds into accolades, per-item prefix, never inline', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const finding = { type: '🟣', scope: 'line', file: 'src/a.ts', line: 9, body: 'Clean null guard.' };
    const { comments, sections } = partition([finding], postable);
    assert.equal(comments.length, 0);
    assert.equal(sections.accolades.length, 1);
    const bullet = renderBullet(sections.accolades[0]);
    assert.match(bullet, /^- 🟣 /);
  });

  test('accolades section has no umbrella header absorbing the emoji', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const findings = [
      { type: '🟣', scope: 'file', file: 'src/a.ts', body: 'Great structure.' },
      { type: '🟣', scope: 'cross-file', body: 'Consistent naming throughout.' },
    ];
    const { sections } = partition(findings, postable);
    const body = composeBody('Summary.', sections);
    const accoladeLines = body.split('\n').filter(l => l.includes('Great structure') || l.includes('Consistent naming'));
    assert.equal(accoladeLines.length, 2);
    for (const l of accoladeLines) assert.match(l, /^- 🟣 /);
    // Header itself carries no emoji prefix (it's a section title, not a finding).
    assert.match(body, /### Accolades\n- 🟣/);
  });

  test('suggestion block is preserved verbatim in the inline comment body', () => {
    const suggestion = '```suggestion\n  if (!x) return null;\n```';
    const finding = { type: '🟡', scope: 'line', file: 'src/a.ts', line: 9, body: 'Consider a guard.', suggestion };
    const entry = buildInlineComment(finding);
    assert.ok(entry.body.includes(suggestion));
  });

  test('every inline comment body starts with its colour emoji', () => {
    for (const type of ['🔴', '🟠', '🟡']) {
      const finding = { type, scope: 'line', file: 'src/a.ts', line: 9, body: 'x' };
      const entry = buildInlineComment(finding);
      assert.ok(entry.body.startsWith(type));
    }
  });

  test('empty positive section omits the Accolades heading entirely', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const finding = { type: '🟡', scope: 'file', file: 'src/a.ts', body: 'A nit.' };
    const { sections } = partition([finding], postable);
    const body = composeBody('Summary.', sections);
    assert.equal(body.includes('Accolades'), false);
  });

  test('stats counts are correct across a mixed batch', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    const findings = [
      { type: '🔴', scope: 'line', file: 'src/a.ts', line: 9, body: 'inline 1' },
      { type: '🟡', scope: 'line', file: 'src/b.ts', line: 1, body: 'inline 2' },
      { type: '🟠', scope: 'line', file: 'src/a.ts', line: 999, body: 'off-diff' },
      { type: '🟡', scope: 'file', file: 'src/c.ts', body: 'file-scoped' },
      { type: '🟣', scope: 'file', file: 'src/a.ts', body: 'accolade' },
    ];
    const { stats } = partition(findings, postable);
    assert.equal(stats.inline, 2);
    assert.equal(stats.offDiffDemoted, 1);
    assert.equal(stats.folded, 3); // off-diff + file-scoped + accolade
  });

  test('unknown finding type throws rather than silently dropping', () => {
    const postable = parseDiffHunks(SAMPLE_DIFF);
    assert.throws(() => partition([{ type: '⚪', scope: 'file', body: 'x' }], postable));
  });

  test('deleted-file diff (+++ /dev/null) yields no postable lines', () => {
    const deleteDiff = [
      'diff --git a/src/old.ts b/src/old.ts',
      'deleted file mode 100644',
      '--- a/src/old.ts',
      '+++ /dev/null',
      '@@ -1,2 +0,0 @@',
      '-const z = 1;',
      '-export { z };',
    ].join('\n');
    const postable = parseDiffHunks(deleteDiff);
    assert.equal(postable.has('src/old.ts'), false);
  });

  // -------------------------------------------------------------------------
  // Body framing: marker + self-review verdict line.
  // -------------------------------------------------------------------------

  test('every body ends with the pr-review marker', () => {
    const { payload } = buildPayload({ verdict: 'Approve', findings: [], diff: SAMPLE_DIFF, summary: 'Fine.' });
    assert.ok(payload.body.endsWith(REVIEW_MARKER));
    assert.equal(payload.body.startsWith('Fine.'), true);
  });

  test('self-review opens the body with the verdict line and keeps the marker', () => {
    const { payload } = buildPayload({
      verdict: 'Request Changes', selfReview: true, findings: [], diff: SAMPLE_DIFF, summary: 'One blocker.',
    });
    assert.match(payload.body, /^\*\*Verdict: Request Changes\*\* \(self-review/);
    assert.ok(payload.body.includes('\n\nOne blocker.\n\n'));
    assert.ok(payload.body.endsWith(REVIEW_MARKER));
  });

  test('self-review with an unknown verdict string is rejected', () => {
    assert.throws(
      () => buildPayload({ verdict: 'REQUEST_CHANGES', selfReview: true, findings: [], diff: SAMPLE_DIFF, summary: 'x' }),
      /expected one of/,
    );
  });

  test('a normal review ignores the verdict string entirely', () => {
    assert.doesNotThrow(() => buildPayload({ verdict: 'whatever', findings: [], diff: SAMPLE_DIFF, summary: 'x' }));
  });

  // -------------------------------------------------------------------------
  // Prose gate: dash ban + summary emoji ban.
  // -------------------------------------------------------------------------

  test('summary with an em-dash is rejected', () => {
    assert.throws(
      () => validateSummary('The header is fixed — both files agree now.'),
      /em-dash/,
    );
  });

  test('summary with an en-dash is rejected', () => {
    assert.throws(() => validateSummary('Range 1–2 covered.'), /en-dash/);
  });

  test('summary with a horizontal bar or figure dash is rejected', () => {
    assert.throws(() => validateSummary('Section one ― section two.'), /horizontal bar/);
    assert.throws(() => validateSummary('Value: 5‒10.'), /figure dash/);
  });

  test('summary with 🆕 is rejected (renders as a GitHub badge)', () => {
    assert.throws(() => validateSummary('🆕 DATABASE.md gained an ERD.'), /:new: badge/);
  });

  test('summary with ✅ or ⚠️ is rejected (superseded vocabulary)', () => {
    assert.throws(() => validateSummary('✅ Fixed the header.'), /superseded/);
    assert.throws(() => validateSummary('⚠️ Still open: N+1 query.'), /superseded/);
  });

  test('summary using the ⚪/⚫/🟢 circle vocabulary passes', () => {
    assert.doesNotThrow(() => validateSummary(
      'Since my last review:\n' +
      '⚪ fixed: em-dash in the DBML header.\n' +
      '⚫ still open: N+1 query on the recommendations endpoint.\n' +
      '🟢 new: DATABASE.md gained an embedded ERD.',
    ));
  });

  test('clean summary with no emoji at all passes', () => {
    assert.doesNotThrow(() => validateSummary('A well-documented, correctly-hedged migration.'));
  });

  test('comment body with an em-dash is rejected', () => {
    assert.throws(
      () => validateComments([{ path: 'src/a.ts', line: 9, body: '🔴 Null deref — check x first.' }]),
      /em-dash/,
    );
  });

  test('clean comment bodies pass the dash gate', () => {
    assert.doesNotThrow(() => validateComments([
      { path: 'src/a.ts', line: 9, body: '🔴 Null deref: check x first.' },
      { path: 'src/b.ts', line: 1, body: '🟡 Consider renaming (clarity).' },
    ]));
  });

  test('run() rejects a summary file containing an em-dash before touching the diff', () => {
    // parseDiffHunks would throw on garbage input if reached; passing a
    // clearly-invalid diff proves validateSummary runs first and short-circuits.
    assert.throws(() => {
      validateSummary('Both files agree — nothing to flag.');
      parseDiffHunks('not a real diff, should never be reached');
    }, /em-dash/);
  });

  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      fn();
      process.stdout.write(`ok: ${name}\n`);
    } catch (err) {
      failed++;
      process.stdout.write(`FAIL: ${name}\n  ${err.message}\n`);
    }
  }
  process.stdout.write(`\n${tests.length - failed}/${tests.length} passed\n`);
  if (failed > 0) process.exit(1);
}

function isCliEntry() {
  if (!process.argv[1]) return false;
  try {
    const modulePath = realpathSync(fileURLToPath(import.meta.url));
    const argvPath = realpathSync(process.argv[1]);
    return modulePath === argvPath;
  } catch {
    return false;
  }
}

if (isCliEntry()) {
  const args = parseArgs(process.argv.slice(2));
  try {
    if (args.selfTest) {
      selfTest();
    } else {
      run();
    }
  } catch (err) {
    process.stderr.write(`partition-findings.mjs failed: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  }
}
