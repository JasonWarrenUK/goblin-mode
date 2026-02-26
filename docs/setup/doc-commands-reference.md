# Documentation Slash Commands

> Quick reference for `/doc/*` commands that integrate with documentation workflow

---

## Available Commands

### `/doc/adr [decision title]`
**Purpose**: Create an Architecture Decision Record  
**When to use**: Making significant technical decisions  
**Output**: ADR in `docs/dev/architecture/`

**Example**:
```
/doc/adr "Database Choice: PostgreSQL vs MongoDB"
```

### `/doc/sync [doc-name]`
**Purpose**: Update existing documentation based on code changes  
**When to use**: After commits that affect documented features  
**Output**: Updated documentation file

**Example**:
```
/doc/sync Technical-Overview
```

### `/doc/generate-readme`
**Purpose**: Auto-generate comprehensive README from project analysis  
**When to use**: New projects or major README overhauls  
**Output**: README.md in project root

**Example**:
```
/doc/generate-readme
```

### `/doc/work-record`
**Purpose**: Generate work session summary from today's commits  
**When to use**: End of coding session  
**Output**: Work record in `docs/archives/work-records/`

**Example**:
```
/doc/work-record
```

---

## Integration with Workflow

### Post-Commit Hook Integration
```
1. Make code changes
2. git commit
3. Hook detects doc changes needed
4. Run /doc/sync to update
```

### End-of-Session Flow
```
1. Finish coding for the day
2. Run /doc/work-record
3. Claude analyzes commits + asks context questions
4. Work record saved automatically
```

### Decision Documentation
```
1. Making architecture decision
2. Run /doc/adr "Decision Title"
3. Answer questions interactively
4. ADR generated and saved
```

---

## Tips

- Commands use templates from `~/.claude/doc-templates/`
- All commands follow your existing command patterns
- Output locations follow your Rhea documentation structure
- Commands integrate with `doc-reminders.txt` system
- Work records are valuable for AM2 portfolio evidence

---

## Related Files

- Templates: `~/.claude/doc-templates/`
- Commands: `~/.claude/commands/doc/`
- Reminders: `~/.claude/doc-reminders.txt`
- Strategy doc: `~/.claude/documentation-workflow-strategy.md`
