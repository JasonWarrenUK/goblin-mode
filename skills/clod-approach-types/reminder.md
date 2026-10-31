Types carry domain intent (clod-approach-types). When writing or changing a type definition:

- An identifier is never a bare `string` or `str`. TypeScript: a branded type (`type UserId = string & { readonly __brand: 'UserId' }`). Python: `UserId = NewType('UserId', str)`. Go: `type UserID string`.
- A lifecycle or status is a closed set, never a bare string and never a cluster of booleans. TypeScript: a string-literal union, or a discriminated union when each state carries its own data. Python: `Enum` or `Literal`. Go: a defined type with a `const` block.
- A data shape is declared: TypeScript `interface`; Python `@dataclass` or pydantic `BaseModel`, never a plain class or a dict; Go `struct`.
- Parse at the boundary: raw input becomes the branded or narrowed type once, where it enters (Zod `.brand()`, a pydantic validator or a constructor) and stays typed from there.
- Exception: UI component props (Svelte or React) keep booleans such as `isOpen`; a wire-format shape may stay bare until it is parsed.

After each `.ts` or `.py` write, ast-grep checks for a bare-string identifier or status field and exits 2 with the lines; fix them before moving on.
