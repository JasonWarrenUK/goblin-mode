#!/usr/bin/env node
/**
 * partition-findings.mjs — deterministic finding partition for pr-review-comment
 *
 * Takes pr-review's structured findings plus the PR diff, and produces a
 * ready-to-POST GitHub review-create payload. Owns every bit of JSON
 * assembly and escaping so the model never hand-builds the request body.
 *
 * Core job: work out which line-scoped findings actually sit inside a diff
 * hunk (only those can become inline `comments[]` entries — GitHub's
 * review-create endpoint rejects comments whose line isn't in the diff) and
 * fold everything else into the top-level review body.
 *
 * IMPORTANT — verified against GitHub REST docs (2022-11-28): the
 * review-create endpoint's `comments[]` array accepts ONLY line-anchored
 * entries (path, body, line, side, start_line, start_side). It does NOT
 * accept `subject_type` — that field is response-only there, not a request
 * field. File-level comments cannot be batched into a pending review at
 * all, which is why every non-inlineable finding folds into `body` instead.
 * See SKILL.md's <api-constraints> block for the full rationale.
 *
 * Usage:
 *   node partition-findings.mjs \
 *     --findings <path>.json --diff <path>.diff \
 *     --summary-file <path>.md --out <path>.json
 *   node partition-findings.mjs --self-test
 *
 * Input (--findings): { verdict, findings: [...] }
 *   Each finding: { type: "🔴"|"🟠"|"🟡"|"🟣", scope: "line"|"file"|"cross-file",
 *                    file?, line?, range?: {start,end}, body, suggestion? }
 *
 * Output (--out): { body, comments: [...] } — exact review-create shape.
 * Stdout: { inline, folded, offDiffDemoted } stats.
 */

import { readFileSync, writeFileSync, realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const VALID_TYPES = ['🔴', '🟠', '🟡', '🟣'];

/**
 * Parses unified diff text into Map<filePath, Set<postableLineNumber>>.
 * A line is "postable" (can be inline-commented) if it's a context or
 * added line on the RIGHT (new-file) side of a hunk — deleted lines have
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
    // Diffs against /dev/null (deleted files) — no RIGHT side, skip.
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
      // Deleted line — no new-file line number, don't advance newLine.
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

/** Renders a finding as a single body bullet, e.g. "- 🟡 `path` — text". */
function renderBullet(finding) {
  const location = finding.file ? `\`${finding.file}\` — ` : '';
  return `- ${finding.type} ${location}${finding.body}`;
}

/** Composes the full markdown review body from the summary + folded sections. */
function composeBody(summary, sections) {
  const parts = [summary.trim()];

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
    // Each accolade is individually prefixed with 🟣 — no umbrella header
    // absorbing the emoji. renderBullet already does this per-item.
    parts.push(['### Accolades', ...sections.accolades.map(renderBullet)].join('\n'));
  }

  return parts.join('\n\n');
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--self-test') { args.selfTest = true; continue; }
    const m = arg.match(/^--([a-z-]+)$/);
    if (m) { args[m[1]] = argv[++i]; }
  }
  return args;
}

function run({ findings: findingsPath, diff: diffPath, 'summary-file': summaryPath, out: outPath }) {
  if (!findingsPath || !diffPath || !summaryPath || !outPath) {
    process.stderr.write(
      'Usage: node partition-findings.mjs --findings <path> --diff <path> ' +
      '--summary-file <path> --out <path>\n',
    );
    process.exit(1);
  }

  let input;
  try {
    input = JSON.parse(readFileSync(findingsPath, 'utf-8'));
  } catch (err) {
    process.stderr.write(`Error: partition-findings: unreadable/invalid --findings JSON at ${findingsPath}: ${err.message}\n`);
    process.exit(1);
  }

  let diffText, summaryText;
  try {
    diffText = readFileSync(diffPath, 'utf-8');
    summaryText = readFileSync(summaryPath, 'utf-8');
  } catch (err) {
    process.stderr.write(`Error: partition-findings: unreadable input file: ${err.message}\n`);
    process.exit(1);
  }

  const postableByFile = parseDiffHunks(diffText);

  let result;
  try {
    result = partition(input.findings || [], postableByFile);
  } catch (err) {
    process.stderr.write(`Error: partition-findings: ${err.message}\n`);
    process.exit(1);
  }

  const body = composeBody(summaryText, result.sections);
  const payload = { body, comments: result.comments };

  writeFileSync(outPath, JSON.stringify(payload, null, 2), 'utf-8');
  process.stdout.write(JSON.stringify(result.stats) + '\n');
}

// ---------------------------------------------------------------------------
// Self-test — no vitest/package.json in ~/.claude/skills, so this uses
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

  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      fn();
      process.stdout.write(`ok — ${name}\n`);
    } catch (err) {
      failed++;
      process.stdout.write(`FAIL — ${name}\n  ${err.message}\n`);
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
      run(args);
    }
  } catch (err) {
    process.stderr.write(`partition-findings.mjs failed: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  }
}
