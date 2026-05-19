---
name: create-task
description: Create a an implementation plan based on user input and project context
---

# Task Creator

Convert the user's request into a detailed implementation plan

## Usage Examples

- `/user:create-task I want to export a module`

## Instructions:

You are an experience developer on the current project. When this command is invoked:

1. **Determine the project root by looking for common indicators (.git, package.json, etc.)**
2. **Parse the command arguments to determine the desired result**
3. **Locate and analyse existing relevant files**
4. **Think harder about the constituent subtasks that need to be achieved**
5. **Think about the correct order in which to execute these tasks**

## Behavior

- Where possible, align your approach with existing project implementations
