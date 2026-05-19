---
description: template for slash commands
argument-hint: [message]
allowed-tools:
model: claude-sonnet-4-5-20250929
disable-model-invocation: true
---

<command-frontmatter>
    <description>
        - **Purpose:** Brief description of the command
        - **Example:** `description: [commit changes to git]`
        - **Default Behaviour:** Uses the first line from the prompt
    <description>
    <argument-hint>
        - **Purpose:** This hint is shown to the user when auto-completing the slash command
        - **Example:** `argument-hint: [commitId]`
        - **Default Behaviour:** None
    </argument-hint>
    <allowed-tools>
        - **Purpose:** List of tools the command can use
        - **Example:** `allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)`
        - **Default Behaviour:** Inherits from the conversation
    </allowed-tools>
    <model>
        - **Purpose:** Specify a model to use.
        - **Example:** `model: claude-sonnet-4-5-20250929`
        <model-options>
            - **Recommended**
                - `claude-sonnet-4-5-20250929`
            - **"Max" Subscription Only**
                - `claude-opus-4-1-20250805`
            - **Deprecated**
                - `claude-opus-4-20250514`
                - `claude-sonnet-4-20250514`
        </model-options>
        - **Default Behaviour:** Inherits from the conversation
    </model>
    <disable-model-invocation>
        - **Purpose:** Whether to prevent SlashCommand tool (see below) from calling this command
        - **Example:** `disable-model-invocation: true`
        - **Default Behaviour:** false
    </disable-model-invocation>
</command-frontmatter>
<command-body>
    <command-arguments>
        <command-argument-basics>
            The $ARGUMENTS placeholder captures all arguments passed to the command
        </command-argument-basics>
        <positional-command-arguments>
            # Command definition
            echo 'Review PR #$1 with priority $2 and assign to $3' > .claude/commands/review-pr.md
            # Usage
            > /review-pr 456 high alice
            # $1 becomes "456", $2 becomes "high", $3 becomes "alice"
        </positional-command-arguments>
    </command-arguments>
    <referencing-files>
        <referencing-specific-file>
            "Review the implementation in @src/utils/helpers.js"
        </referencing-specific-file>
        <referencing-multiple-files>
            "Compare @src/old-version.js with @src/new-version.js"
        </referencing-multiple-files>
        <referencing-mcp-resources>
            "Show me the data from @github:repos/owner/repo/issues"
        </referencing-mcp-resources>
    </referencing-files>
    <bash-commands>
        <bash-commands-intro>
            - Execute bash commands before the slash command runs using the ! prefix.
            - The output is included in the command context.
            - You must include allowed-tools with the Bash tool...
            - ...but you can choose the specific bash commands to allow.
        </bash-commands-intro>
        <bash-commands-example>
            ---
            allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
            description: Create a git commit
            ---
            ## Context
            - Current git status: !`git status`
            - Current git diff (staged and unstaged changes): !`git diff HEAD`
            - Current branch: !`git branch --show-current`
            - Recent commits: !`git log --oneline -10`
            ## Your task
            Based on the above changes, create a single git commit.
        </bash-commands-example>
    </bash-commands>
    <slash-commands-tool>
        <slash-commands-tool-basics>
            - There is a SlashCommand tool
            - It allows Claude to execute custom slash commands programmatically during a conversation.
            - This gives Claude the ability to invoke custom commands on your behalf when appropriate.
            - Your instructions (prompts, CLAUDE.md, etc.) need to reference the command by name with its slash.
        <slash-commands-tool-basics>
        <slash-commands-tool-claude-md-example>
            "Run /write-unit-test when you are about to start writing tests."
            This tool puts each available custom slash command’s metadata into context up to the character budget limit. You can use /context to monitor token usage and follow the operations below to manage context.
        </slash-commands-tool-claude-md-example>
    </slash-commands-tool>
    <extended-thinking>
        <extended-thinking-basics>
            - Extended thinking is disabled by default in Claude Code. You can enable it on-demand by...
                1. using Tab to toggle Thinking on
                2. using prompts like “think” or “think hard”.
            - You can enable it permanently; set the MAX_THINKING_TOKENS environment variable in your settings
            - Claude will display its thinking process as italic gray text above the response
        </extended-thinking-basics>
        <extended-thinking-examples>
            <extended-thinking-via-prompt>
                1. "I need to implement a new authentication system using OAuth2 for our API. Think deeply about the best approach for implementing this in our codebase."
            </extended-thinking-via-prompt>
            <extended-thinking-refinement>
                1. "think about potential security vulnerabilities in this approach"
                2. "think hard about edge cases we should handle"
            </extended-thinking-refinement>
        </extended-thinking-examples>
        <extended-thinking-tips>
            1. Extended thinking is most valuable for complex tasks such as:
                - Planning complex architectural changes
                - Debugging intricate issues
                - Creating implementation plans for new features
                - Understanding complex codebases
                - Evaluating tradeoffs between different approaches
            2. Use Tab to toggle Thinking on and off during a session.
            3. “Think” triggers basic extended thinking
            4. Intensifying phrases triggers deeper thinking. Examples include:
                - “think hard”
                - “think more”
                - “think a lot”
                - “think longer”
        </extended-thinking-tips>
    </extended-thinking>
</command-body>
<command-organisation>
    <project-commands>
        Stored in `project-root/.claude/commands/`
    </project-commands>
    <personal-commands>
        Stored in `~/.claude/commands/`
    </personal-commands>
    <command-organisation-tips>
        - Command names are derived from the filename
            - e.g. `optimize.md` becomes `/optimize`
        - You can organize commands in subdirectories
            - File: `.claude/commands/frontend/component.md`
            - Command: `/component` with `(project:frontend)` shown in the description
        - Project commands are available to everyone who clones the repository
        - The Markdown file content becomes the prompt sent to Claude when the command is invoked
    </command-organisation-tips>
</command-organisation>
<overview>
    Follow the instructions in `<steps>`
</overview>
<role>
    You are...
</role>
<steps>
    <step-1>
    </step-1>
    <step-2>
    </step-2>
    <step-3>
    </step-3>
    </steps>
<rules>
    1.
</rules>
<guidance>
    1.
</guidance>
<template>
</template>
