# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-27

First public release: one deeply worked skill rather than many shallow ones.

### Added

- **`attribution-model-analysis` skill**: compares six multi-touch attribution
  models (first-touch, last-touch, linear, time-decay, U-shaped, W-shaped) on
  the user's own touchpoint data, with computation-ready formulas, a data
  preparation checklist, and an arithmetically verified worked example.
- **Plugin marketplace support**: installable in Claude Code via
  `/plugin marketplace add metrikia-io/marketing-skills`.
- **CI validation**: SKILL.md frontmatter checks, forbidden character sweep,
  and proprietary reference sweep on every push and pull request.
