// "Some Assembly Required", the five-level skills tutorial, one Level per page
// at /skills/tutorial/<n>/. Converted from site/design/content/tutorial-draft.md;
// every sentence of prose is the approved copy, word for word. The only
// additions are <mark data-c> wraps that tie a phrase to its callout.
//
// Level 5's Real Thing quotes goblin-scout from origin/feat/goblin-scout-rename
// at 82719bd, which has not merged. Recheck those three excerpts against main
// after the final rebase (site/design/pre-pr-checks.md).

import type { Level } from '#lib/content/tutorial.types.ts';

export const TUTORIAL: Level[] = [
	{
		n: 1,
		title: 'One File, One Job',
		intro: 'In this level, you\'ll create a skill called <code>tidy-imports</code>: a single-file skill that takes some basic arguments.',
		steps: [
			{
				id: '1.1',
				title: 'A Folder and a SKILL.md',
				prose: [
					'Each skill lives in its own folder, as a file called <code>SKILL.md</code>. Make the folder inside your project, at <code>.claude/skills/tidy-imports/</code>; anyone who clones the repository then gets the skill too. The file starts with YAML frontmatter between two <code>---</code> lines; <mark data-c="1.1c">everything after that is the instructions Claude follows</mark> when the skill runs.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
---

Sort the import statements at the top of the file
alphabetically, one per line. Leave everything below
the imports exactly as it was.`,
						added: [1, 2, 3, 4, 5, 6, 7, 8],
					},
					{
						path: 'Terminal',
						lang: 'bash',
						text: 'mkdir -p .claude/skills/tidy-imports',
					},
				],
				callouts: [
					{
						label: '1.1a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 2,
						html: 'The folder name is the command you\'ll type, <code>/tidy-imports</code>, and <code>name</code> is what the <code>/</code> menu shows. Keep the two the same. A different <code>name</code> still works from the menu, but typed out it\'s an unknown command.',
					},
					{
						label: '1.1b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 3,
						html: '<code>description:</code> is the line Claude reads to decide whether this skill fits what you asked for, so it says what the skill does in plain words.',
					},
					{
						label: '1.1c',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 6,
						to: 8,
						html: 'Everything under the frontmatter is what Claude follows: here, three lines on how to sort the imports.',
					},
				],
			},
			{
				id: '1.2',
				title: 'An Argument',
				prose: [
					'Next, tell the skill which file to tidy. <mark data-c="1.2a"><code>arguments: [path]</code> gives the first word after the command a name</mark>, <code>path</code>; <mark data-c="1.2c">wherever <code>$path</code> appears in the body, Claude Code swaps in that word</mark> before Claude reads it. <mark data-c="1.2b"><code>argument-hint</code> is the reminder you see while typing the command</mark>.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
---

Tidy the imports in $path.

Sort the import statements at the top of the file
alphabetically, one per line. Leave everything below
the imports exactly as it was.`,
						added: [4, 5, 8],
					},
				],
				callouts: [
					{
						label: '1.2a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 4,
						html: '<code>arguments: [path]</code> maps names to positions in order, so <code>path</code> is the first argument and a second name would be the second.',
					},
					{
						label: '1.2b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 5,
						html: '<code>argument-hint: "[file]"</code> appears beside the command in autocomplete and changes nothing about how the skill runs.',
					},
					{
						label: '1.2c',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 8,
						html: '<code>$path</code> in <code>Tidy the imports in $path.</code> is swapped for the file you typed, and becomes an empty string when you type none.',
					},
				],
			},
			{
				id: '1.3',
				title: 'Run It',
				prose: [
					'Start Claude Code in your project and run the command with a file. If <code>.claude/skills/</code> didn\'t exist when the session started, run <code>/reload-skills</code> first, because Claude Code only watches skill folders it found at startup. You can also just ask Claude to sort a file\'s imports: the description sits in its context, so it can load the skill without the command.',
				],
				files: [
					{
						path: 'src/app.ts',
						lang: 'ts',
						text: `import express from 'express';
import { readFileSync } from 'node:fs';
import { serve } from './server';

const app = express();`,
					},
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
---

Tidy the imports in $path.

Sort the import statements at the top of the file
alphabetically, one per line. Leave everything below
the imports exactly as it was.`,
					},
					{
						path: 'Claude Code',
						lang: 'text',
						text: '/tidy-imports src/app.ts',
					},
				],
				callouts: [
					{
						label: '1.3a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 8,
						html: '<code>/tidy-imports src/app.ts</code> puts <code>src/app.ts</code> in place of <code>$path</code>, so the body\'s first line reaches Claude as <code>Tidy the imports in src/app.ts.</code>',
					},
					{
						label: '1.3b',
						file: 'src/app.ts',
						line: 5,
						html: '<code>const app = express();</code> stays where it was: that\'s what <code>Leave everything below the imports exactly as it was</code> is for.',
					},
				],
				output: {
					label: 'src/app.ts before the run',
					text: `import { serve } from './server';
import { readFileSync } from 'node:fs';
import express from 'express';

const app = express();`,
				},
			},
		],
		exercise: {
			title: 'Try it: handle a missing file',
			prompt: [
				'Run <code>/tidy-imports</code> with no file. <code>$path</code> becomes empty and Claude reads <code>Tidy the imports in .</code> Add one line to the body so Claude asks for a file instead of guessing.',
			],
			answer: [
				{
					prose: 'Under <code>Tidy the imports in $path.</code>, add:',
				},
				{
					code: 'If no path follows "in" above, ask which file to tidy and stop.',
					lang: 'markdown',
				},
				{
					prose: 'With nothing typed, a named argument expands to an empty string, so the body has to say what to do in that case.',
				},
			],
		},
	},
	{
		n: 2,
		title: 'Give It a Script and a Ledger',
		intro: 'In this level, you\'ll move the sorting into a script that Claude Code runs without asking each time. The script also keeps a ledger of every file it tidies.',
		opening: {
			title: 'Where Level 1 Left It',
			prose: [
				'Here\'s <code>SKILL.md</code> at the end of level 1. Claude still does the sorting itself, from the three lines at the bottom; step 2.1 replaces those with a script.',
			],
			files: [
				{
					path: '.claude/skills/tidy-imports/SKILL.md',
					lang: 'markdown',
					text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
---

Tidy the imports in $path.

Sort the import statements at the top of the file
alphabetically, one per line. Leave everything below
the imports exactly as it was.`,
				},
			],
		},
		steps: [
			{
				id: '2.1',
				title: 'Give It a Script',
				prose: [
					'Asked to reorder lines, Claude will now and then reflow one it was told to leave alone. A script sorts the same way every time, so move the sorting into <code>scripts/sort-imports.sh</code> inside the skill\'s folder and make it executable with <code>chmod +x</code>. In <code>SKILL.md</code>, <mark data-c="2.1a">call the script as <code>${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh</code></mark>. Claude Code fills in the skill\'s own folder, so the call works whichever folder the session is in.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
---

Tidy the imports in $path.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.`,
						added: [10, 11, 12, 13, 14, 15, 16, 17, 18],
						removed: [
							{
								before: 10,
								text: 'Sort the import statements at the top of the file',
							},
							{
								before: 10,
								text: 'alphabetically, one per line. Leave everything below',
							},
							{
								before: 10,
								text: 'the imports exactly as it was.',
							},
						],
					},
					{
						path: '.claude/skills/tidy-imports/scripts/sort-imports.sh',
						lang: 'bash',
						text: `#!/usr/bin/env bash
# Sort the import lines at the top of a file, in place.
set -euo pipefail
export LC_ALL=C # byte order, so every machine sorts the same way

file="$1"

# How many lines from the top start with "import "?
count=$(awk '/^import /{n++; next} {exit} END{print n+0}' "$file")
if [ "$count" -eq 0 ]; then
	echo "no imports at the top of $file"
	exit 0
fi

{ head -n "$count" "$file" | sort; tail -n +"$((count + 1))" "$file"; } > "$file.tmp"
mv "$file.tmp" "$file"
echo "sorted $count imports in $file"`,
						added: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
					},
				],
				callouts: [
					{
						label: '2.1a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 13,
						html: 'The script call takes the place of the three lines that told Claude how to sort.',
					},
					{
						label: '2.1b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 16,
						to: 18,
						html: '<code>Do not reorder any lines yourself</code> keeps Claude\'s hands off the sorting: it leaves the file alone after the script runs, and a non-zero exit ends the run with the script\'s message.',
					},
				],
			},
			{
				id: '2.2',
				title: 'Scope the Tool',
				prose: [
					'Claude Code asks before every Bash call unless something has approved it. <mark data-c="2.2a"><code>allowed-tools</code> approves the calls it names</mark>, for the rest of the turn that started the skill. Give it the same <code>${CLAUDE_SKILL_DIR}</code> path as the body (with <code>:*</code> for whatever arguments follow) and it approves that one script and nothing else. Claude Code fills the variable in, in both places, so the rule and the command always match. Every other tool works as it did, under your usual permission settings.',
					'The rule matches the start of the command, so the script call from 2.1a has to use exactly that path, with no <code>bash</code> or <code>./</code> in front.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.`,
						added: [6],
					},
				],
				callouts: [
					{
						label: '2.2a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 6,
						html: '<code>allowed-tools</code> approves Bash calls that start with this path until you send your next message, and the <code>:*</code> covers whatever arguments follow.',
					},
				],
			},
			{
				id: '2.3',
				title: 'Keep a Ledger',
				prose: [
					'Next, add a ledger so <mark data-c="2.3a">a later run can tell what an earlier one touched</mark>. <mark data-c="2.3b">The script appends one line per file</mark> to <code>.claude/tidy-imports.log</code>, with the path and the number of imports it sorted. The script is already approved, so writing the ledger needs no extra permission.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
						added: [11, 12, 24, 25],
					},
					{
						path: '.claude/skills/tidy-imports/scripts/sort-imports.sh',
						lang: 'bash',
						text: `#!/usr/bin/env bash
# Sort the import lines at the top of a file, in place.
set -euo pipefail
export LC_ALL=C # byte order, so every machine sorts the same way

file="$1"
ledger=".claude/tidy-imports.log"

# How many lines from the top start with "import "?
count=$(awk '/^import /{n++; next} {exit} END{print n+0}' "$file")
if [ "$count" -eq 0 ]; then
	echo "no imports at the top of $file"
	exit 0
fi

{ head -n "$count" "$file" | sort; tail -n +"$((count + 1))" "$file"; } > "$file.tmp"
mv "$file.tmp" "$file"
printf '%s\\t%s\\n' "$file" "$count" >> "$ledger"
echo "sorted $count imports in $file"`,
						added: [7, 18],
					},
				],
				callouts: [
					{
						label: '2.3a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 11,
						to: 12,
						html: '<code>Read .claude/tidy-imports.log if it exists</code> makes a second run on the same file say so before it starts.',
					},
					{
						label: '2.3b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 24,
						to: 25,
						html: '<code>The script also writes the ledger line</code> keeps the ledger\'s format the same on every run and needs no permission beyond 2.2a.',
					},
				],
				output: {
					label: '.claude/tidy-imports.log after two runs',
					text: `src/app.ts	3
src/routes/home.ts	2`,
				},
			},
		],
		realThing: {
			name: 'project-tag_version',
			intro: '<code>project-tag_version</code> is a real skill in this repository: it tags a release after a merge to main. Two of its marked lines do what you just did in steps 2.1 and 2.2; <mark data-c="R.a">the first is something <code>tidy-imports</code> gets in level 3</mark>.',
			files: [
				{
					path: 'skills/project-tag_version/SKILL.md',
					lang: 'markdown',
					text: `---
name: "Project: Tag Version"
description: "Tag the release after a merge to main, computing the next semver tag with svu"
...
disable-model-invocation: true
allowed-tools: ["Bash(svu:*)", "Bash(git:*)", "Bash(~/.claude/library/scripts/safe-version-next.sh:*)"]
...
---

# Tag the release with \`svu\`

...

\`\`\`bash
TAG="$("$HOME"/.claude/library/scripts/safe-version-next.sh)" && git tag "$TAG" && git push origin "$TAG"
\`\`\`
...`,
				},
			],
			callouts: [
				{
					label: 'R.a',
					file: 'skills/project-tag_version/SKILL.md',
					line: 5,
					html: '<code>disable-model-invocation: true</code> means only a person can start this skill, by typing its name; Claude never starts it on its own. Level 3 covers when you\'d want that.',
				},
				{
					label: 'R.b',
					file: 'skills/project-tag_version/SKILL.md',
					line: 6,
					html: '<code>allowed-tools</code> names <code>safe-version-next.sh</code> by its full path, as you did in step 2.2, alongside <code>svu</code> and <code>git</code>, which it uses to read the history and push the tag.',
				},
				{
					label: 'R.c',
					file: 'skills/project-tag_version/SKILL.md',
					line: 15,
					html: 'The <code>TAG=</code> line runs the script and tags whatever it prints, so Claude never works out the version number itself: the same idea as step 2.1.',
				},
			],
		},
		exercise: {
			title: 'Try it: put the date in the ledger',
			prompt: [
				'Change the script so each ledger line starts with the day it was written. Then change the ledger paragraph in <code>SKILL.md</code> so Claude says when a file was last tidied.',
			],
			answer: [
				{
					prose: 'In <code>sort-imports.sh</code>, put the date in front of the path:',
				},
				{
					code: 'printf \'%s\\t%s\\t%s\\n\' "$(date +%F)" "$file" "$count" >> "$ledger"',
					lang: 'bash',
				},
				{
					prose: '<code>date +%F</code> prints the date as <code>2026-11-19</code>, which sorts in date order as plain text. In <code>SKILL.md</code>, the second ledger line becomes: <code>already listed there, say on which date it was last tidied.</code>',
				},
			],
		},
	},
	{
		n: 3,
		title: 'Say Who Runs It, and How',
		intro: 'In this level, you\'ll add frontmatter that controls who can start <code>tidy-imports</code>, which model it runs on and which tools it may never use.',
		opening: {
			title: 'Where Level 2 Left It',
			prose: [
				'Here\'s <code>SKILL.md</code> at the end of level 2. Its frontmatter says nothing yet about who may start it or which model it runs on.',
			],
			files: [
				{
					path: '.claude/skills/tidy-imports/SKILL.md',
					lang: 'markdown',
					text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
arguments: [path]
argument-hint: "[file]"
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
				},
			],
		},
		steps: [
			{
				id: '3.1',
				title: 'Who May Start It',
				prose: [
					'By default, both you and Claude can start a skill. Setting <code>disable-model-invocation: true</code> makes it yours alone; <code>user-invocable: false</code> makes it Claude\'s alone. Leave <code>tidy-imports</code> open to both, <mark data-c="3.1b">write the line out anyway</mark> <mark data-c="3.1c">with a comment saying why</mark>, and <mark data-c="3.1a">add <code>when_to_use</code> to tell Claude when to reach for it</mark>.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
						added: [4, 7],
						fold: [[17, 21]],
					},
				],
				callouts: [
					{
						label: '3.1a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 4,
						html: 'Claude sees <code>when_to_use</code> alongside the description, so use it to name the moment: just after Claude has changed a file\'s imports.',
					},
					{
						label: '3.1b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 7,
						html: '<code>disable-model-invocation: false</code> is already the default; writing it out gives the comment somewhere to say why Claude may start this skill unasked.',
					},
					{
						label: '3.1c',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 7,
						html: 'The comment names the only safeguard so far: the script touches nothing but import lines. That doesn\'t cover a file with uncommitted changes, which git can\'t restore; step 4.3 adds a gate for it.',
					},
					{
						label: '3.1d',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 7,
						html: 'If this line were <code>true</code>, the description and <code>when_to_use</code> would drop out of Claude\'s context entirely. <code>when_to_use</code> only matters on a skill Claude is allowed to start.',
					},
				],
			},
			{
				id: '3.2',
				title: 'Pin the Model and Effort',
				prose: [
					'Reading a ledger and running one script doesn\'t need your most capable model, so pin a mid-sized one at low effort. <mark data-c="3.2c"><code>model</code> and <code>effort</code> override the session for the rest of the turn the skill runs in</mark>; your next message brings the session\'s own settings back.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
						added: [7, 8],
						fold: [[19, 23]],
					},
				],
				callouts: [
					{
						label: '3.2a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 7,
						html: '<code>model</code> takes the same aliases as <code>/model</code>. If your organisation\'s allowed list or auto mode rules the model out, the skill falls back to the session\'s model.',
					},
					{
						label: '3.2b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 8,
						html: '<code>effort</code> takes <code>low</code>, <code>medium</code>, <code>high</code>, <code>xhigh</code> or <code>max</code>; which of those are available depends on the model.',
					},
					{
						label: '3.2c',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 7,
						to: 8,
						html: 'Both settings hold until your next message. If Claude starts the skill partway through other work, the rest of that turn drops to low effort and stays on the session\'s model. In Claude Code 2.1.329, <code>model</code> only switches when your own message starts the skill.',
					},
				],
			},
			{
				id: '3.3',
				title: 'Promises the Frontmatter Enforces',
				prose: [
					'Since step 2.1, the body has told Claude never to edit the file itself. <mark data-c="3.3a"><code>disallowed-tools</code> enforces that</mark>: while the skill is active, the tools it lists are out of Claude\'s reach. Where <code>allowed-tools</code> approves tools, <code>disallowed-tools</code> takes them away. <mark data-c="3.3c">Keep the sentence in the body too, because the removal only lasts until your next message</mark>.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
						added: [11],
						fold: [[20, 24]],
					},
				],
				callouts: [
					{
						label: '3.3a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 11,
						html: '<code>disallowed-tools: [Edit, Write, NotebookEdit]</code> removes the three file-writing tools, so Claude cannot fix up the file after the script runs even if it decides to.',
					},
					{
						label: '3.3b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 11,
						html: 'The comment <code>the script changes the file; Claude never does</code> restates the promise from 2.1b, so a reader of the frontmatter alone sees why the list exists.',
					},
					{
						label: '3.3c',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 25,
						to: 26,
						html: '<code>Do not reorder any lines yourself</code> stays in the body, because the tool removal clears at your next message and the instruction does not.',
					},
					{
						label: '3.3d',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 11,
						html: 'The removal also lasts for the rest of the turn the skill started in, so if Claude runs the tidy partway through a task, it cannot edit any file again until you send your next message.',
					},
				],
			},
		],
		realThing: {
			name: 'pr-update',
			intro: '<code>pr-update</code> rewrites a pull request\'s description after new commits land. Claude can start it, and <mark data-c="R.c">a comment in its frontmatter names the gate that makes that safe</mark>.',
			files: [
				{
					path: 'skills/pr-update/SKILL.md',
					lang: 'markdown',
					text: `---
name: "PR: Update"
description: "Update a PR description to account for commits made since it was last written"
when_to_use: "When commits have been pushed to a branch after its PR was opened or last described; offer it whenever new work lands on a branch with an open PR rather than leaving the description stale."
model: sonnet
effort: medium
...
disable-model-invocation: false # invocable by Claude so it can offer a refresh when new commits leave the description stale; its approval step still gates the write
...
---
...
### 5. Show me the diff

Display the updated body in full and a brief summary of what changed vs the previous description. **Wait for my approval.**
...`,
				},
			],
			callouts: [
				{
					label: 'R.a',
					file: 'skills/pr-update/SKILL.md',
					line: 4,
					html: '<code>when_to_use</code> names a moment Claude sees first, new commits on a branch whose description has gone stale, as in step 3.1.',
				},
				{
					label: 'R.b',
					file: 'skills/pr-update/SKILL.md',
					line: 5,
					to: 6,
					html: '<code>model: sonnet</code> and <code>effort: medium</code> pin the run the same way 3.2 does, one notch higher on effort.',
				},
				{
					label: 'R.c',
					file: 'skills/pr-update/SKILL.md',
					line: 8,
					html: 'The comment on <code>disable-model-invocation: false</code> names the gate that makes it safe to leave open, as in step 3.1.',
				},
				{
					label: 'R.d',
					file: 'skills/pr-update/SKILL.md',
					line: 14,
					html: '<code>**Wait for my approval.**</code> is that gate, and step 4.3 gives <code>tidy-imports</code> one of its own.',
				},
			],
			after: [
				'<code>pr-update</code> has no <code>disallowed-tools</code> line. For a real one, see line 13 of <code>skills/project-tag_version/SKILL.md</code>, which removes <code>git push --tags</code> because it would publish every stray local tag.',
			],
		},
		exercise: {
			title: 'Try it: make it yours alone',
			prompt: [
				'tam wants <code>tidy-imports</code> to run only when someone types it. Change the frontmatter.',
			],
			answer: [
				{
					prose: 'Set the line to <code>disable-model-invocation: true</code> with a new comment, and delete <code>when_to_use</code>:',
				},
				{
					code: 'disable-model-invocation: true # runs only when typed',
					lang: 'yaml',
				},
				{
					prose: 'A skill with <code>disable-model-invocation: true</code> has its description taken out of Claude\'s context, so <code>when_to_use</code> would never be read. Typing <code>/tidy-imports src/app.ts</code> still works.',
				},
			],
		},
	},
	{
		n: 4,
		title: 'Skills That Call Skills',
		intro: 'In this level, you\'ll split a read-only check out of <code>tidy-imports</code> into a skill of its own, call it from <code>tidy-imports</code> and add a gate before the one change git can\'t undo.',
		opening: {
			title: 'Where Level 3 Left It',
			prose: [
				'Here\'s <code>SKILL.md</code> at the end of level 3. It does all its work on its own; step 4.1 starts a second skill beside it.',
			],
			files: [
				{
					path: '.claude/skills/tidy-imports/SKILL.md',
					lang: 'markdown',
					text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
					fold: [[20, 24]],
				},
			],
		},
		steps: [
			{
				id: '4.1',
				title: 'Split Out a Read-Only Check',
				prose: [
					'Checking whether a file\'s imports are already sorted is useful on its own, before a commit or to decide whether a tidy is needed at all. Because the check never writes, any skill can share it. Make it a skill called <code>tidy-imports-check</code>, with <mark data-c="4.1a">its own script that reports and changes nothing</mark>.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports-check/scripts/check-imports.sh',
						lang: 'bash',
						text: `#!/usr/bin/env bash
# Report whether the import lines at the top of a file are sorted. Never writes.
set -euo pipefail
export LC_ALL=C # the same order sort-imports.sh uses

file="$1"

count=$(awk '/^import /{n++; next} {exit} END{print n+0}' "$file")
if [ "$count" -eq 0 ]; then
	echo "no imports at the top of $file"
	exit 0
fi

if head -n "$count" "$file" | sort -c 2>/dev/null; then
	echo "sorted: $count imports in $file"
else
	echo "unsorted: $count imports in $file; sorted, they would read:"
	head -n "$count" "$file" | sort
fi`,
						added: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
					},
					{
						path: '.claude/skills/tidy-imports-check/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports-check
description: Report whether the import statements at the top of a file are sorted, without changing the file
when_to_use: "Before tidy-imports rewrites a file, or when the user asks whether a file's imports are in order."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # tidy-imports calls this skill, so Claude must be able to invoke it
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/check-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # reads, never writes
---

Check the imports in $path.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/check-imports.sh "$path"
\`\`\`

Report its output as it stands. Do not sort, fix or change
anything, even when the imports are out of order.`,
						added: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
					},
				],
				callouts: [
					{
						label: '4.1a',
						file: '.claude/skills/tidy-imports-check/scripts/check-imports.sh',
						line: 14,
						html: '<code>sort -c</code> only checks the order and exits non-zero on the first line out of place, so the script never opens the file for writing.',
					},
					{
						label: '4.1b',
						file: '.claude/skills/tidy-imports-check/scripts/check-imports.sh',
						line: 4,
						html: '<code>export LC_ALL=C</code> matches the line in <code>sort-imports.sh</code>, so the check and the tidy agree on what sorted means.',
					},
					{
						label: '4.1c',
						file: '.claude/skills/tidy-imports-check/SKILL.md',
						line: 9,
						html: '<code>disable-model-invocation: false</code> is already the default, and its comment records that another skill calls this one, so nobody flips it to <code>true</code> without seeing what 4.2 depends on.',
					},
					{
						label: '4.1d',
						file: '.claude/skills/tidy-imports-check/SKILL.md',
						line: 11,
						html: '<code>disallowed-tools</code> lists only the file-writing tools and leaves Bash alone, because the check runs its own script.',
					},
				],
				output: {
					label: 'On src/app.ts from 1.3, before tidying, the script prints',
					text: `unsorted: 3 imports in src/app.ts; sorted, they would read:
import express from 'express';
import { readFileSync } from 'node:fs';
import { serve } from './server';`,
				},
			},
			{
				id: '4.2',
				title: 'Call It From tidy-imports',
				prose: [
					'Have <code>tidy-imports</code> run the check first and stop when there\'s nothing to do. To call another skill, <mark data-c="4.2a">the body just tells Claude to load it by name</mark>, and Claude uses its Skill tool, as it would for any skill. <mark data-c="4.2b">That tool refuses a skill marked <code>disable-model-invocation: true</code> unless your own message names that skill\'s command</mark>, so a skill that another skill calls has to stay open to Claude.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; the script only reorders import lines
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Load the tidy-imports-check skill on $path. If it reports
the imports already sorted, say so and stop. If the check
cannot run, say why and stop.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
						added: [19, 20, 21],
						fold: [[24, 34]],
					},
				],
				callouts: [
					{
						label: '4.2a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 19,
						html: '<code>Load the tidy-imports-check skill on $path</code> names the skill and its argument, which is all one skill needs to call another.',
					},
					{
						label: '4.2b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 20,
						to: 21,
						html: '<code>If the check cannot run, say why and stop</code> covers the day someone marks the check <code>disable-model-invocation: true</code> and the call is refused.',
					},
					{
						label: '4.2c',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 7,
						to: 8,
						html: 'Both files pin <code>model: sonnet</code> and <code>effort: low</code>. The check\'s <code>effort</code> carries on into the rest of the tidy, so a different effort there would change the tidy\'s too. Its <code>model</code> doesn\'t carry, so the tidy keeps the model it started on.',
					},
				],
			},
			{
				id: '4.3',
				title: 'A Gate Before Anything Irreversible',
				prose: [
					'The script rewrites the file in place and keeps no copy. If the file is committed, git still has the old order; if it has uncommitted changes, or git has never seen it, nothing does. For that case, have <code>tidy-imports</code> stop and wait for a yes before the script runs.',
				],
				files: [
					{
						path: '.claude/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; it stops for a yes before rewriting a file git has no copy of
allowed-tools: ["Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)", "Bash(git status:*)"]
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Load the tidy-imports-check skill on $path. If it reports
the imports already sorted, say so and stop. If the check
cannot run, say why and stop.

Run \`git status --porcelain -- "$path"\`. If it prints
anything, the file has changes git holds no copy of, and
the rewrite cannot be undone from git. Show the check's
report, say this and stop. Run the script only after the
user replies yes.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
						added: [9, 10, 23, 24, 25, 26, 27],
						fold: [[16, 21], [30, 40]],
					},
				],
				callouts: [
					{
						label: '4.3a',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 23,
						html: '<code>git status --porcelain -- "$path"</code> prints nothing for a file git already holds as it is, so a clean file goes straight to the script with no question asked.',
					},
					{
						label: '4.3b',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 25,
						to: 26,
						html: '<code>Show the check\'s report, say this and stop</code> puts the planned order in front of you before you answer.',
					},
					{
						label: '4.3c',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 27,
						html: 'The yes arrives as a new message, which clears both the <code>allowed-tools</code> grant and the <code>disallowed-tools</code> removal, so Claude Code asks before the script runs unless your permission settings already allow it.',
					},
					{
						label: '4.3d',
						file: '.claude/skills/tidy-imports/SKILL.md',
						line: 9,
						html: 'The comment on <code>disable-model-invocation</code> now names the gate, which is what makes it reasonable to leave a file-rewriting skill open to Claude.',
					},
				],
			},
		],
		realThing: {
			name: 'pr-review-dry_run, pr-review and branch-qa_review',
			intro: 'Three skills in this repository share one review method. <code>pr-review-dry_run</code> holds it and prints findings; <code>pr-review</code> and <code>branch-qa_review</code> both call it.',
			files: [
				{
					path: 'skills/pr-review-dry_run/SKILL.md',
					lang: 'markdown',
					text: `---
name: "PR: Review (Dry Run)"
...
model: opus
effort: high
...
disable-model-invocation: false # required so pr-review can call it
...
disallowed-tools: ["Edit", "Write", "NotebookEdit"] # reviews, never fixes
...
---
...
Canonical review methodology. Produces structured findings only; **never posts to GitHub**. \`pr-review\` loads this skill and handles posting; keep all methodology here to avoid divergence.
...`,
				},
				{
					path: 'skills/pr-review/SKILL.md',
					lang: 'markdown',
					text: `...
model: opus
effort: high
...
disable-model-invocation: false # invocable so next-task-ship's Step 7 self-review can call it; it posts to GitHub, so never invoke without an explicit ask or that orchestration
...
    <step num="3">Load the pr-review-dry_run skill and run it against the resolved PR identifier, ...
...`,
				},
				{
					path: 'skills/branch-qa_review/SKILL.md',
					lang: 'markdown',
					text: `...
disable-model-invocation: true
...
Load the \`pr-review-dry_run\` skill and run its full methodology against this branch: ...
...
If the verdict is **Ready**, offer to run the \`pr-create\` skill immediately, ...`,
				},
			],
			callouts: [
				{
					label: 'R.a',
					file: 'skills/pr-review-dry_run/SKILL.md',
					line: 7,
					html: '<code>disable-model-invocation: false # required so pr-review can call it</code> does what you did in step 4.1, with the reason written beside it.',
				},
				{
					label: 'R.b',
					file: 'skills/pr-review/SKILL.md',
					line: 5,
					html: '<code>pr-review</code> posts to GitHub with no approval step, so its gate lives in the comment on its <code>disable-model-invocation</code> line, which limits when Claude may start it.',
				},
				{
					label: 'R.c',
					file: 'skills/pr-review/SKILL.md',
					line: 7,
					html: '<code>Load the pr-review-dry_run skill</code> appears in both callers, the same plain instruction as 4.2a.',
				},
				{
					label: 'R.d',
					file: 'skills/branch-qa_review/SKILL.md',
					line: 2,
					html: '<code>branch-qa_review</code> is itself <code>disable-model-invocation: true</code>. The rule only runs one way: a caller can be yours alone, but the skill it calls can\'t. It also ends by offering <code>pr-create</code> and leaves the yes to you.',
				},
			],
			after: [
				'Caller and callee pin the same <code>model: opus</code> and <code>effort: high</code>, for the reason in step 4.2.',
			],
		},
		exercise: {
			title: 'Try it: predict the refusal',
			prompt: [
				'ravi sets <code>tidy-imports-check</code> to <code>disable-model-invocation: true</code>, then types <code>/tidy-imports src/app.ts</code>. What happens?',
			],
			answer: [
				{
					prose: '<code>tidy-imports</code> starts, because ravi typed its command. When it tries to load <code>tidy-imports-check</code>, Claude Code refuses, because ravi\'s message named only <code>/tidy-imports</code>. The line from 4.2b applies, so Claude says the check could not run and stops before the script.',
				},
			],
		},
	},
	{
		n: 5,
		title: 'Pack It as a Plugin',
		intro: 'In this level, you\'ll move <code>tidy-imports</code> and <code>tidy-imports-check</code> into a plugin, so any project can install them with one command.',
		opening: {
			title: 'Where Level 4 Left It',
			prose: [
				'Here are both skills at the end of level 4, still in the project\'s <code>.claude/skills/</code> folder; step 5.1 moves them into a plugin.',
			],
			files: [
				{
					path: '.claude/skills/tidy-imports/SKILL.md',
					lang: 'markdown',
					text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; it stops for a yes before rewriting a file git has no copy of
allowed-tools: ["Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)", "Bash(git status:*)"]
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Load the tidy-imports-check skill on $path. If it reports
the imports already sorted, say so and stop. If the check
cannot run, say why and stop.

Run \`git status --porcelain -- "$path"\`. If it prints
anything, the file has changes git holds no copy of, and
the rewrite cannot be undone from git. Show the check's
report, say this and stop. Run the script only after the
user replies yes.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
					fold: [[16, 21], [30, 40]],
				},
				{
					path: '.claude/skills/tidy-imports-check/SKILL.md',
					lang: 'markdown',
					text: `---
name: tidy-imports-check
description: Report whether the import statements at the top of a file are sorted, without changing the file
when_to_use: "Before tidy-imports rewrites a file, or when the user asks whether a file's imports are in order."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # tidy-imports calls this skill, so Claude must be able to invoke it
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/check-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # reads, never writes
---

Check the imports in $path.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/check-imports.sh "$path"
\`\`\`

Report its output as it stands. Do not sort, fix or change
anything, even when the imports are out of order.`,
				},
			],
		},
		steps: [
			{
				id: '5.1',
				title: 'A Plugin Folder and plugin.json',
				prose: [
					'A plugin is a folder with <mark data-c="5.1c">a manifest at <code>.claude-plugin/plugin.json</code> and its parts beside it</mark>. Skills go in <code>skills/</code>, one folder each, exactly as they were in <code>.claude/skills/</code>. <mark data-c="5.1a">Call the plugin <code>tidy</code></mark>; its two skills then run as <code>/tidy:tidy-imports</code> and <code>/tidy:tidy-imports-check</code>.',
					'Before anything else, test it with <code>claude --plugin-dir ./tidy</code>, which loads the plugin for that one session without installing it.',
				],
				files: [
					{
						path: 'tidy/.claude-plugin/plugin.json',
						lang: 'json',
						text: `{
	"name": "tidy",
	"version": "0.1.0",
	"description": "Sort the import statements at the top of a file, with a read-only check first",
	"author": {
		"name": "noor"
	},
	"license": "MIT"
}`,
						added: [1, 2, 3, 4, 5, 6, 7, 8, 9],
					},
					{
						path: 'tidy',
						lang: 'text',
						text: `tidy/
	.claude-plugin/
		plugin.json
	skills/
		tidy-imports/
			SKILL.md
			scripts/sort-imports.sh
		tidy-imports-check/
			SKILL.md
			scripts/check-imports.sh`,
						added: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
					},
				],
				callouts: [
					{
						label: '5.1a',
						file: 'tidy/.claude-plugin/plugin.json',
						line: 2,
						html: '<code>"name": "tidy"</code> is the only required field. Write it in kebab-case: it becomes the prefix on every skill the plugin holds.',
					},
					{
						label: '5.1b',
						file: 'tidy/.claude-plugin/plugin.json',
						line: 3,
						html: '<code>"version": "0.1.0"</code> keeps people who install the plugin from a hosted marketplace on this version until you change the number.',
					},
					{
						label: '5.1c',
						file: 'tidy',
						line: 2,
						to: 4,
						html: '<code>.claude-plugin/</code> holds the manifest and nothing else, while <code>skills/</code> sits at the plugin root beside it.',
					},
				],
			},
			{
				id: '5.2',
				title: 'Paths That Travel',
				prose: [
					'On someone else\'s machine, a path into <code>.claude/skills/</code> points at a folder that isn\'t there. <mark data-c="5.2a"><code>${CLAUDE_SKILL_DIR}</code> already avoids that</mark>: inside a plugin it fills in the skill\'s own folder, wherever Claude Code installed the plugin (a new folder in its cache for each version), so both scripts work as they are. For a file several skills share, use <code>${CLAUDE_PLUGIN_ROOT}</code>, the plugin\'s own folder. The one change <code>tidy-imports</code> needs is <mark data-c="5.2b">the call to the check, which now uses its plugin name</mark>.',
					'Both scripts are unchanged from 4.1 and 2.3.',
				],
				files: [
					{
						path: 'tidy/skills/tidy-imports/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports
description: Sort the import statements at the top of a file
when_to_use: "After you add or remove imports in a file, or when the user asks to sort or tidy a file's imports."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # Claude may start it after changing a file's imports; it stops for a yes before rewriting a file git has no copy of
allowed-tools: ["Bash(\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh:*)", "Bash(git status:*)"]
disallowed-tools: [Edit, Write, NotebookEdit] # the script changes the file; Claude never does
---

Tidy the imports in $path.

Read .claude/tidy-imports.log if it exists. If $path is
already listed there, say so before going on.

Load the tidy:tidy-imports-check skill on $path. If it
reports the imports already sorted, say so and stop. If the
check cannot run, say why and stop.

Run \`git status --porcelain -- "$path"\`. If it prints
anything, the file has changes git holds no copy of, and
the rewrite cannot be undone from git. Show the check's
report, say this and stop. Run the script only after the
user replies yes.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/sort-imports.sh "$path"
\`\`\`

It sorts the import block in place. Do not reorder any
lines yourself or edit the file after it runs. If the
script exits non-zero, report its message and stop.

The script also writes the ledger line. Never write to
.claude/tidy-imports.log yourself.`,
						added: [19, 20, 21],
						fold: [[22, 30], [34, 40]],
					},
					{
						path: 'tidy/skills/tidy-imports-check/SKILL.md',
						lang: 'markdown',
						text: `---
name: tidy-imports-check
description: Report whether the import statements at the top of a file are sorted, without changing the file
when_to_use: "Before tidy:tidy-imports rewrites a file, or when the user asks whether a file's imports are in order."
arguments: [path]
argument-hint: "[file]"
model: sonnet
effort: low
disable-model-invocation: false # tidy:tidy-imports calls this skill, so Claude must be able to invoke it
allowed-tools: Bash(\${CLAUDE_SKILL_DIR}/scripts/check-imports.sh:*)
disallowed-tools: [Edit, Write, NotebookEdit] # reads, never writes
---

Check the imports in $path.

Run the script on the file, by exactly this path:

\`\`\`bash
\${CLAUDE_SKILL_DIR}/scripts/check-imports.sh "$path"
\`\`\`

Report its output as it stands. Do not sort, fix or change
anything, even when the imports are out of order.`,
						added: [4, 9],
					},
				],
				callouts: [
					{
						label: '5.2a',
						file: 'tidy/skills/tidy-imports/SKILL.md',
						line: 10,
						html: '<code>${CLAUDE_SKILL_DIR}</code> needs no change in a plugin: it fills in the skill\'s own folder there too, so the rule and the command still match.',
					},
					{
						label: '5.2b',
						file: 'tidy/skills/tidy-imports/SKILL.md',
						line: 19,
						html: '<code>Load the tidy:tidy-imports-check skill</code> uses the full plugin name, the form every plugin skill carries.',
					},
					{
						label: '5.2c',
						file: 'tidy/skills/tidy-imports/SKILL.md',
						line: 16,
						html: '<code>.claude/tidy-imports.log</code> stays a project path, because the plugin\'s own folder changes with every version and is no place to keep state.',
					},
				],
			},
			{
				id: '5.3',
				title: 'Install From a Marketplace',
				prose: [
					'A marketplace is a folder or repository with <code>.claude-plugin/marketplace.json</code>, listing plugins and where each one lives. Say noor keeps one called <code>noor-tools</code>, with <code>tidy</code> under <code>plugins/</code>: anyone can add that marketplace once and install from it.',
					'Delete the old <code>.claude/skills/tidy-imports/</code> and <code>.claude/skills/tidy-imports-check/</code> folders from the project once the plugin works. While they stay, <code>/tidy-imports</code> still runs the project copy.',
				],
				files: [
					{
						path: 'noor-tools/.claude-plugin/marketplace.json',
						lang: 'json',
						text: `{
	"name": "noor-tools",
	"owner": {
		"name": "noor"
	},
	"plugins": [
		{
			"name": "tidy",
			"source": "./plugins/tidy",
			"description": "Sort the import statements at the top of a file, with a read-only check first"
		}
	]
}`,
						added: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
					},
					{
						path: 'Install it in a session',
						lang: 'text',
						text: `/plugin marketplace add ./noor-tools
/plugin install tidy@noor-tools`,
					},
					{
						path: 'Or from your shell',
						lang: 'bash',
						text: `claude plugin marketplace add ./noor-tools
claude plugin install tidy@noor-tools`,
					},
					{
						path: 'Then, in any project',
						lang: 'text',
						text: '/tidy:tidy-imports src/app.ts',
					},
				],
				callouts: [
					{
						label: '5.3a',
						file: 'noor-tools/.claude-plugin/marketplace.json',
						line: 8,
						html: 'The entry\'s <code>"name": "tidy"</code> matches the plugin\'s own <code>name</code>. Installs use the entry name and skill prefixes use the manifest name, so if they differ, the install breaks.',
					},
					{
						label: '5.3b',
						file: 'noor-tools/.claude-plugin/marketplace.json',
						line: 9,
						html: '<code>"source": "./plugins/tidy"</code> is written from the marketplace root, the folder that holds <code>.claude-plugin/</code>.',
					},
					{
						label: '5.3c',
						file: 'Install it in a session',
						line: 2,
						html: '<code>tidy@noor-tools</code> is the plugin\'s entry name, an <code>@</code> and the marketplace name.',
					},
					{
						label: '5.3d',
						file: 'Install it in a session',
						line: 1,
						html: '<code>/plugin marketplace add</code> also takes a GitHub <code>owner/repo</code>, so once <code>noor-tools</code> is pushed, <code>/plugin marketplace add noor/noor-tools</code> adds it on any machine.',
					},
				],
			},
		],
		realThing: {
			name: 'goblin-scout',
			intro: '<code>goblin-scout</code> is a plugin in this repository that keeps a project plan, the roadbook, as a map of what waits on what. Its skills run as <code>/goblin-scout:&lt;skill&gt;</code>.',
			files: [
				{
					path: 'marketplace/goblin-scout/.claude-plugin/plugin.json',
					lang: 'json',
					text: `{
    "name": "goblin-scout",
    "version": "3.0.0",
    ...
    "license": "Zlib",
    ...
    "types": "./types/index.d.ts"
}`,
				},
				{
					path: 'marketplace/goblin-scout/skills/start-roadbook/SKILL.md',
					lang: 'markdown',
					text: `---
...
when_to_use: "When a project has no roadbook yet, or an existing simple-style one needs superseding with a new phase built from scratch (for converting an old single-file roadmap, use goblin-scout:rebind-roadbook instead)."
model: fable
effort: high
...
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Bash(python3:*)"]
arguments: ["phase"]
argument-hint: "[phase name (optional, e.g. PHASE_1)]"
---
...
Shared conventions (status vocabulary, colour table, graph rules, formatting) live in \`\${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md\`; read it before writing anything. The CLI is \`python3 "\${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py\`.`,
				},
				{
					path: '.claude-plugin/marketplace.json',
					lang: 'json',
					text: `{
	"name": "goblin-mode",
	...
	"plugins": [
		{
			"name": "goblin-scout",
			"source": "./marketplace/goblin-scout",
			...`,
				},
			],
			callouts: [
				{
					label: 'R.a',
					file: 'marketplace/goblin-scout/.claude-plugin/plugin.json',
					line: 2,
					html: '<code>"name": "goblin-scout"</code> is the prefix every skill in the plugin carries, so <code>start-roadbook</code> runs as <code>/goblin-scout:start-roadbook</code>, as in step 5.1.',
				},
				{
					label: 'R.b',
					file: 'marketplace/goblin-scout/skills/start-roadbook/SKILL.md',
					line: 3,
					html: '<code>use goblin-scout:rebind-roadbook instead</code> names a sibling skill by its full plugin name, as in step 5.2.',
				},
				{
					label: 'R.c',
					file: 'marketplace/goblin-scout/skills/start-roadbook/SKILL.md',
					line: 13,
					html: '<code>${CLAUDE_PLUGIN_ROOT}/references/</code> and <code>${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py</code> reach files the whole plugin shares, wherever it was installed: the job step 5.2 gives <code>${CLAUDE_PLUGIN_ROOT}</code>.',
				},
				{
					label: 'R.d',
					file: '.claude-plugin/marketplace.json',
					line: 6,
					html: 'The marketplace entry\'s <code>"name": "goblin-scout"</code> matches the manifest\'s, so it installs as <code>goblin-scout@goblin-mode</code> after <code>/plugin marketplace add JasonWarrenUK/goblin-mode</code>.',
				},
			],
			after: [
				'The manifest\'s <code>"types"</code> line belongs to the plugin\'s mod: a hooks module that ships beside the skills and runs inside Claude Code, where it can draw panes. Mods, and plugins in general, get an article of their own later.',
			],
		},
		exercise: {
			title: 'Try it: which one runs?',
			prompt: [
				'tam installs <code>tidy@noor-tools</code> in a project that still has <code>.claude/skills/tidy-imports/</code>, then types <code>/tidy-imports src/app.ts</code>. Which skill runs, and what should tam type to be sure of the plugin\'s?',
			],
			answer: [
				{
					prose: 'The project copy runs. Both skills load, since the plugin\'s is namespaced, but a plugin skill only answers to its bare name when no other command already has it. <code>/tidy:tidy-imports src/app.ts</code> always reaches the plugin\'s skill; delete the project folder and the bare name reaches it too.',
				},
			],
		},
	},
];
