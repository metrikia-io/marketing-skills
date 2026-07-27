# Contributing

We welcome contributions to Metrikia Marketing Skills. This guide explains how to propose new skills or improve existing ones.

## Skill Quality Bar

Every skill in this repository must meet these standards:

1. **Valid SKILL.md frontmatter**: The file must begin with YAML frontmatter containing:
   - `name`: the skill's canonical name (kebab-case)
   - `description`: one-line summary of what the skill does
   - Any other metadata fields you choose to include

2. **Clear methodology**: The skill document must outline:
   - A trigger description: what problem or task the skill solves
   - Step-by-step workflow: numbered instructions for the user
   - Expected inputs and outputs
   - No vendor lock-in: skills work with user data, not proprietary tools

3. **Real examples**: At least one worked example showing input, process, and output.

4. **No proprietary references**: Skills are open source and should work for any marketer.
   Avoid naming specific client companies, products, or internal systems.

5. **Clear language**: Assume the reader is familiar with marketing concepts but may not know the Metrikia platform.

## How to Contribute

### For a new skill:

1. Fork this repository.
2. Create a feature branch: `git checkout -b feature/your-skill-name`.
3. Create a folder under `skills/` with your skill name.
4. Write a `SKILL.md` file following the quality bar above.
5. Include example data or templates if helpful.
6. Commit: `git commit -m "feat(skills): add your-skill-name"`.
7. Push and open a pull request to `main`.

### For improvements to existing skills:

1. Fork and branch: `git checkout -b fix/skill-name-improvement`.
2. Update the skill's `SKILL.md` or supporting files.
3. Commit: `git commit -m "fix(skills): improve your-skill-name"` or `git commit -m "docs(skills): clarify instructions"`.
4. Push and open a pull request.

## Pull Request Checklist

Before submitting, verify:

- [ ] SKILL.md frontmatter is valid YAML with `name` and `description` fields
- [ ] No em-dash character (use ":", ".", ",", parentheses, or restructure sentences)
- [ ] No proprietary references (internal commands, client names, internal class names, file paths)
- [ ] Examples work end-to-end (test the skill in Claude Code if possible)
- [ ] Skill solves a real marketing problem
- [ ] Writing is clear and concise

## PR Review Process

A maintainer will:

1. Run automated checks (frontmatter, forbidden characters, internal reference sweep).
2. Review the skill for clarity, completeness, and value to marketers.
3. Suggest improvements or approve the PR.

## Reporting Issues

For bugs or feature requests:

1. Search existing issues to avoid duplicates.
2. Open an issue with a clear title and description.
3. For skill bugs: include the skill name and the step where the issue occurred.
4. For feature requests: explain the marketing problem you're trying to solve.

## Code of Conduct

By contributing, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions?

Open a GitHub discussion or issue. We are here to help.

Thank you for contributing to better marketing analytics.
