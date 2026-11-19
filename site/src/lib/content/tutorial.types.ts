// The shape of the skills tutorial, "Some Assembly Required"
// (src/lib/content/tutorial.ts). One Level per page at /skills/tutorial/<n>/.
//
// Prose fields are HTML strings that may hold only <code>…</code> and
// <mark data-c="2.1a">…</mark>. A mark colour-matches a phrase to the callout
// of the same label. Code is plain text, never HTML.

/** One file as it stands at a given moment, shown on a tab of the specimen. */
export interface FileView {
	/** Shown on the file's tab, e.g. ".claude/skills/tidy-imports/SKILL.md". */
	path: string;
	/** For the code panel's label and any highlighting: "markdown", "bash", "json", "text". */
	lang: string;
	/** The whole file as it stands, lines separated by "\n". */
	text: string;
	/** 1-based line numbers this step added or changed (marked as new). */
	added?: number[];
	/** Lines this step removed, shown struck through above where they were (live stage only). */
	removed?: { before: number; text: string }[];
	/**
	 * 1-based inclusive line ranges folded to a single "..." line, so a long file
	 * shows its changed region and fits the stage (scope T3). Never fold a line
	 * a callout points at.
	 */
	fold?: [number, number][];
}

export interface Callout {
	/** "2.1a" for a step, "R.a" for The Real Thing. */
	label: string;
	/** The path of the FileView it points into. */
	file: string;
	/** 1-based line it points at; with `to`, the block from `line` to `to`. */
	line: number;
	to?: number;
	/** One sentence, HTML (code and marks only). */
	html: string;
}

export interface Step {
	/** "2.1" */
	id: string;
	title: string;
	/** Paragraphs of the write-up, HTML (code and marks only). */
	prose: string[];
	/** Every file the step shows, as it stands after the step. The first opens on the specimen. */
	files: FileView[];
	callouts: Callout[];
	/** Optional short output shown under the write-up, such as a script's printout or a ledger sample. */
	output?: { label: string; text: string };
}

export interface Level {
	n: 1 | 2 | 3 | 4 | 5;
	title: string;
	/** The level's one- or two-sentence intro, HTML. */
	intro: string;
	/** Where the previous level left the files: the stage's opening state. Absent on level 1. */
	opening?: { title: string; prose: string[]; files: FileView[] };
	steps: Step[];
	/** Absent on level 1. */
	realThing?: {
		/** The real skill or plugin's name, e.g. "project-tag_version". */
		name: string;
		intro: string;
		files: FileView[];
		callouts: Callout[];
		/** Prose after the callouts, HTML. */
		after?: string[];
	};
	exercise: {
		title: string;
		prompt: string[];
		/** The answer: prose and code, in order. */
		answer: ({ prose: string } | { code: string; lang: string })[];
	};
}
