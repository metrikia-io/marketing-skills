# Metrikia Marketing Skills - AI Instructions

## Project Overview

Public repository of open-source Claude Skills for marketing analytics, published
by Metrikia (https://metrikia.io). Documentation only: no runtime code, no build.

**Current version:** 0.1.0
**Distribution:** Claude Code plugin marketplace (`.claude-plugin/`) and manual copy.

## Hard Rules

- This repository is PUBLIC. NEVER reference private internal systems: internal
  CLI commands, class names, private repository paths, client or customer names,
  personal names. Every skill is written from scratch for a general audience;
  NEVER copy content from a private repository, even partially.
- NEVER write the em-dash character (U+2014) anywhere. Use ":", ".", ",",
  parentheses, or restructure the sentence. CI blocks it.
- All published content is English. Confident practitioner tone, no hype.
- Commits: Conventional Commits (`feat`, `fix`, `docs`, `chore`). NEVER add
  Co-Authored-By or any AI attribution.
- The only allowed product reference inside a skill is one closing line:
  "Maintained by the team at Metrikia (https://metrikia.io)."

## Skill Authoring Rules

- Layout: `skills/<kebab-case-name>/SKILL.md`, plus `references/*.md` for
  formulas, checklists, and datasets loaded on demand.
- Frontmatter MUST declare `name` (matching the directory name), `description`,
  and `license: MIT`.
- Description formula: "<what it does>. Use when <trigger A>, <trigger B>, or
  <trigger C>." The second sentence is pure trigger phrases; Claude uses it to
  decide when to activate the skill.
- Keep SKILL.md under 500 lines. Above roughly 300 lines, move detail into
  `references/`.
- Required body sections: an outcome contract (Outcome / Done when / Evidence),
  when to use, expected input data (with an honest degraded mode when data is
  missing), step-by-step methodology, interpretation guardrails, one worked
  example.
- Worked examples MUST be arithmetically verified by hand before commit:
  recompute every table, and every column must reconcile to the same total.
  A wrong number in a published skill destroys credibility.
- No vendor lock-in: skills operate on the user's own exported data and never
  require any specific product.

## Validation Before Commit

Run the same checks as CI locally:

```bash
grep -rn $'—' skills/ README.md && echo FAIL || echo OK
head -1 skills/*/SKILL.md            # every SKILL.md starts with ---
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo OK
python3 -m json.tool .claude-plugin/plugin.json > /dev/null && echo OK
```

CI (`.github/workflows/ci.yml`) validates frontmatter, forbidden characters,
internal references, and JSON manifests on every push and PR. A red CI on main
is a public signal: fix it before anything else.

## Architecture

```
skills/<name>/       one directory per skill (SKILL.md + references/)
.claude-plugin/      plugin.json, marketplace.json, ignore (installed payload)
.github/             CI workflow, issue and PR templates
CHANGELOG.md         Keep a Changelog format, SemVer
```

## Release Sync Checklist

On every version bump, update together:

1. `.claude-plugin/plugin.json` `version`
2. `.claude-plugin/marketplace.json` plugin `version`
3. `CHANGELOG.md`: new entry opening with a one-sentence prose summary
4. `README.md`: skills table and Coming Soon list if a skill was added or shipped
5. Tag `vX.Y.Z` on main after merge
