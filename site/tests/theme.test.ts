// Colour comes from the goblin theme's tokens and nowhere else: no component,
// stylesheet or route in src/ may carry a colour value of its own.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SITE = fileURLToPath(new URL('..', import.meta.url));
const SRC = join(SITE, 'src');

const walk = (dir: string): string[] =>
	readdirSync(dir).flatMap((entry) => {
		const path = join(dir, entry);
		if (entry === 'generated') return [];
		return statSync(path).isDirectory() ? walk(path) : [path];
	});

const COLOUR = /#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(/;
/** CSS's named colours, in any property that takes a colour: `color: silver` is a colour value too. */
const NAMED = new RegExp(
	`(?:^|[;{\\s])(?:color|background(?:-color)?|border(?:-[a-z]+)*|outline(?:-color)?|fill|stroke|box-shadow|text-decoration(?:-color)?|caret-color|accent-color|column-rule(?:-color)?)\\s*:[^;}]*\\b(?:${'aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen'.split(' ').join('|')})\\b`,
	'i',
);

describe('theme tokens', () => {
	const files = walk(SRC).filter((path) => /\.(svelte|css|ts|html)$/.test(path));

	it('finds the site source', () => {
		expect(files.length).toBeGreaterThan(5);
	});

	for (const file of files) {
		it(`${relative(SITE, file)} holds no colour value of its own`, () => {
			const hits = readFileSync(file, 'utf8')
				.split('\n')
				.map((line, index) => ({ line: index + 1, text: line }))
				.filter(({ text }) => (COLOUR.test(text) && !/href="#|id="|#\{/.test(text)) || NAMED.test(text));
			expect(hits).toEqual([]);
		});
	}
});
