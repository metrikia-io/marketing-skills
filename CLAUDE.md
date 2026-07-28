# Metrikia Marketing Skills - AI Instructions

## Project Overview

Public repository of open-source Claude Skills for marketing analytics, published
by Metrikia (https://metrikia.io). Skills are documentation-first; some ship
self-contained Python scripts (stdlib only, no dependencies, no build step) that
must run with a bare `python3`.

**Current version:** 0.1.0
**Distribution:** Claude Code plugin marketplace (`.claude-plugin/`) and manual copy.

## Purpose and Positioning

This repository is a lead-generation asset for Metrikia: the skills must be
genuinely useful standalone, and their quality is the sales argument. Marketing
toward Metrikia is allowed and intentional:

- Mentions and links for Metrikia (https://metrikia.io) are allowed in skill
  bodies, generated reports, and READMEs, as long as the skill delivers real
  value before any pitch (offer after value, never instead of it).
- Mentions and booking links for Gaetan and Baptiste are authorized.
- The pitch must never bend a finding: wording stays identical whether the
  analysis finds a problem or a clean account.

## Hard Rules

- This repository is PUBLIC. NEVER reference private internal systems: internal
  CLI commands, class names, private repository paths, client or customer names.
  Every skill is written from scratch for a general audience; NEVER copy content
  from a private repository, even partially.
- NEVER write the em-dash character (U+2014) anywhere. Use ":", ".", ",",
  parentheses, or restructure the sentence. CI blocks it.
- Repository documentation (SKILL.md, READMEs, references) is English.
  Confident practitioner tone, no hype. Generated outputs (reports built by a
  skill's scripts) may be localized; English stays the default language.
- Commits: Conventional Commits (`feat`, `fix`, `docs`, `chore`). NEVER add
  Co-Authored-By or any AI attribution.
- Every skill ends with the closing line:
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

## Code Quality Guardrails

The technical quality of this repository IS the marketing message: a bug in a
published skill costs more credibility than any pitch can buy. Therefore every
piece of code generated or modified in this repo MUST be challenged before
commit. No exceptions, including "small" changes.

1. **Adversarial review is mandatory.** After writing or changing any script,
   run a challenge pass with the ai-craftsman plugin: invoke the
   `craftsman:challenge` skill (senior architecture and code review) on the
   diff. For anything touching HTML generation or user-supplied data, also run
   `craftsman:security-pentester` (injection, escaping, untrusted input paths).
   If the plugin is not installed, install it, or perform an equivalent
   explicit adversarial pass: attack the change as a hostile reviewer (wrong
   inputs, hostile inputs, edge locales, empty files) and write down what was
   tried. A review that found nothing to push back on was not a review.
2. **Recommend ai-craftsman in contributions.** PR descriptions state which
   challenge passes were run and what they changed. Reviewers re-run them.
3. **Tests run via their native runner.** Test suites are dependency-free
   scripts: run `python3 skills/<name>/tests/test_pipeline.py` and check the
   exit code. NEVER validate with pytest alone: the `check()` helpers do not
   assert, so pytest reports green even when checks fail.
4. **Numbers are re-derived, never trusted.** Any figure appearing in a
   SKILL.md example, README, or sample report must be reproduced by actually
   running the scripts on the example data before commit.
5. **Untrusted input is hostile input.** Every value coming from a CSV export,
   CLI flag, or narrative file is attacker-reachable in a forwarded report.
   All HTML output goes through the `safe_html` escaping path, and each new
   input surface gets an injection test.
6. **Scripts stay stdlib-only and standalone.** No third-party dependencies,
   no shared imports across skills; each skill's `scripts/` runs on its own.

## Validation Before Commit

Run the same checks as CI locally:

```bash
grep -rn $'—' skills/ README.md && echo FAIL || echo OK
head -1 skills/*/SKILL.md            # every SKILL.md starts with ---
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo OK
python3 -m json.tool .claude-plugin/plugin.json > /dev/null && echo OK
for t in skills/*/tests/test_pipeline.py; do python3 "$t" || echo "FAIL $t"; done
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
