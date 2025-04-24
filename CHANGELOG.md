# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

````

## CONTRIBUTING.md with commit guidelines

```markdown:CONTRIBUTING.md
# Contributing to grpy-rest-client

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for our commit messages. This leads to more readable messages that are easy to follow when looking through the project history and enables automatic versioning and changelog generation.

### Commit Message Format

Each commit message consists of a **header**, a **body**, and a **footer**:

````

<type>(<scope>): <subject>
<BLANK LINE>

<body>
<BLANK LINE>
<footer>
```

The **header** is mandatory and must conform to the following format:

#### Type

Must be one of the following:

-   **feat**: A new feature
-   **fix**: A bug fix
-   **docs**: Documentation only changes
-   **style**: Changes that do not affect the meaning of the code
-   **refactor**: A code change that neither fixes a bug nor adds a feature
-   **perf**: A code change that improves performance
-   **test**: Adding missing tests or correcting existing tests
-   **build**: Changes that affect the build system or external dependencies
-   **ci**: Changes to our CI configuration files and scripts
-   **chore**: Other changes that don't modify src or test files
-   **revert**: Reverts a previous commit

#### Scope

The scope should be the name of the module affected (as perceived by the person reading the changelog).

#### Subject

The subject contains a succinct description of the change:

-   use the imperative, present tense: "change" not "changed" nor "changes"
-   don't capitalize the first letter
-   no dot (.) at the end

#### Body

The body should include the motivation for the change and contrast this with previous behavior.

#### Footer

The footer should contain any information about **Breaking Changes** and is also the place to reference GitHub issues that this commit **Closes**.

**Breaking Changes** should start with the word `BREAKING CHANGE:` with a space or two newlines. The rest of the commit message is then used for this.

### Examples

```
feat(auth): add ability to authenticate with API key

This adds support for API key authentication in addition to the existing OAuth flow.

Closes #123
```

```
fix(client): correct timeout handling in requests

The timeout was not being properly applied to all requests, which could lead to hanging connections.

Closes #456
```

```
feat!: completely refactor client API

BREAKING CHANGE: The client API has been completely redesigned to be more intuitive and flexible.
Old methods are no longer available and should be migrated to the new API.

Closes #789
```
