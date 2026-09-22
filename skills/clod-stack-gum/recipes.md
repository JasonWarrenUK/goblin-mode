# Gum recipes

Complete scripts, adapted for zsh from the upstream `examples/` directory and the README. Each one is a pattern to copy into a script.

## Conventional commit

Upstream `examples/commit.sh`, tightened so an abandoned prompt aborts the script before anything is committed.

```zsh
#!/usr/bin/env zsh
set -eu

type=$(gum choose --header "Type" fix feat docs style refactor test chore revert)
scope=$(gum input --placeholder "scope (optional)")
[[ -n $scope ]] && scope="($scope)"

summary=$(gum input --width 72 --value "$type$scope: " --placeholder "Summary of this change")
[[ -n $summary ]]

body=$(gum write --width 80 --placeholder "Details (ctrl+j for a newline, enter to finish)")

gum style --border rounded --padding "0 1" --border-foreground 212 "$summary" "" "$body"
gum confirm "Commit?" && git commit -m "$summary" -m "$body"
```

`set -e` turns every `esc` (exit 1) into a script abort. The dotfiles one-liner from upstream is `alias gcm='git commit -m "$(gum input)" -m "$(gum write)"'`.

## Branch manager

Upstream `examples/git-branch-manager.sh` with a shared colour, a guard for non-repos and zsh array splitting.

```zsh
#!/usr/bin/env zsh
set -u
accent="#f14e32"
export GUM_CHOOSE_CURSOR_FOREGROUND=$accent GUM_CHOOSE_SELECTED_FOREGROUND=$accent

git rev-parse --git-dir >/dev/null 2>&1 || {
	gum log --level error "Must be run inside a git repo"
	exit 1
}

gum style --border normal --margin 1 --padding "1 2" --border-foreground $accent \
	"$(gum style --foreground $accent 'Git') Branch Manager"

branches=("${(@f)$(git branch --format='%(refname:short)' | gum choose --no-limit --header "Branches")}")
(( ${#branches} )) || exit 1

action=$(gum choose --header "Action" rebase delete update) || exit 1

for branch in "${branches[@]}"; do
	case $action in
		rebase)
			base=$(git branch --format='%(refname:short)' | gum choose --header "Rebase onto") || exit 1
			gum spin --title "Fetching..." -- git fetch origin
			git checkout "$branch" && git rebase "origin/$base"
			;;
		delete)
			gum confirm --default=false "Delete $branch?" && git branch -D "$branch"
			;;
		update)
			git checkout "$branch" && git pull --ff-only
			;;
	esac
done
```

## Stage or restore files

Upstream `examples/git-stage.sh`.

```zsh
action=$(gum choose Add Reset) || exit 1
files=$(git status --short | cut -c 4- | gum choose --no-limit) || exit 1
if [[ $action == Add ]]; then
	print -l -- "${(f)files}" | xargs git add
else
	print -l -- "${(f)files}" | xargs git restore
fi
```

## Key-value lists with `--label-delimiter`

Show a label, get back a value. Upstream `examples/filter-key-value.sh` does this with `cut` and `grep`; `choose` can do it natively.

```zsh
sound=$(gum choose --label-delimiter ':' "Cow:Moo" "Cat:Meow" "Dog:Woof")
echo "It goes $sound"
```

`filter` has no label delimiter, so for fuzzy search over labels keep the upstream shape:

```zsh
list=$'Cow:Moo\nCat:Meow\nDog:Woof'
animal=$(print -- "$list" | cut -d: -f1 | gum filter) || exit 1
sound=$(print -- "$list" | grep "^$animal:" | cut -d: -f2)
```

## Table-driven menu

```zsh
menu=$(cat <<'CSV'
Command,Description
build,Compile the project
test,Run the test suite
deploy,Ship to production
CSV
)
cmd=$(print -- "$menu" | gum table --return-column 1 --height 5) || exit 1
case $cmd in
	build)  bun run build ;;
	test)   bun test ;;
	deploy) gum confirm --default=false "Deploy to production?" && ./deploy.sh ;;
esac
```

## Long task with a spinner and honest failure

```zsh
if ! out=$(gum spin --spinner minidot --title "Running tests..." --show-error -- bun test 2>&1); then
	gum log --level error "Tests failed"
	print -- "$out" | gum pager
	exit 1
fi
gum log --level info "Tests passed"
```

`--show-error` prints the captured output only on failure; the explicit `print | gum pager` makes long output scrollable.

## Pick a tmux session

```zsh
session=$(tmux list-sessions -F '#S' | gum filter --placeholder "Session...") || exit 1
tmux switch-client -t "$session" 2>/dev/null || tmux attach -t "$session"
```

## Pick a commit, PR or package

```zsh
git log --oneline | gum filter | cut -d' ' -f1
gh pr list | cut -f1,2 | gum choose | cut -f1 | xargs gh pr checkout
brew list | gum choose --no-limit | xargs brew uninstall
gum filter < "$HISTFILE" --height 20
```

## Password prompt as a sudo helper

```zsh
alias please='gum input --password --prompt "Password: " | sudo -nS'
```

## Layout: boxes side by side

Upstream README "I LOVE Bubble Gum".

```zsh
i=$(gum style --padding "1 5" --border double --border-foreground 212 "I")
love=$(gum style --padding "1 4" --border double --border-foreground 57 "LOVE")
bubble=$(gum style --padding "1 8" --border double --border-foreground 255 "Bubble")
gum_=$(gum style --padding "1 5" --border double --border-foreground 240 "Gum")

top=$(gum join "$i" "$love")
bottom=$(gum join "$bubble" "$gum_")
gum join --align center --vertical "$top" "$bottom"
```

## Playing card (nested style and join)

From upstream `examples/magic.sh`. Shows `--width`/`--height` with `--align` to position text inside a fixed box.

```zsh
rank=A; suit=♠
tl=$(gum style --width 10 --height 5 --align left "$(gum join --vertical "$rank" "$suit")")
br=$(gum style --width 10 --align right "$(gum join --vertical "$suit" "$rank")")
gum style --border rounded --padding "0 1" --margin 2 --border-foreground 7 \
	"$(gum join --vertical "$tl" "$br")"
```

## Script-wide theme and non-interactive mode

```zsh
#!/usr/bin/env zsh
export GUM_CHOOSE_CURSOR_FOREGROUND=99 GUM_CONFIRM_SELECTED_BACKGROUND=99 GUM_INPUT_CURSOR_FOREGROUND=99
export GUM_LOG_LEVEL=${LOG_LEVEL:-info}

interactive=false
[[ -t 0 && -t 2 ]] && interactive=true

ask() {  # ask "Prompt" default
	if $interactive; then
		gum confirm --default=false "$1"
	else
		[[ ${2:-no} == yes ]]
	fi
}

ask "Run migrations?" "${RUN_MIGRATIONS:-no}" && ./migrate.sh
gum log --level debug "interactive=$interactive"
```

`gum log --level debug` is hidden by the `GUM_LOG_LEVEL=info` export unless the caller sets `LOG_LEVEL=debug`.

## Markdown help screen

```zsh
gum format -- "# $0" "" "Usage: $0 [build|test|deploy]" "" "- \`build\` compiles" "- \`test\` runs tests"
```

The `--` stops `#` and `-` lines from being parsed as flags.
