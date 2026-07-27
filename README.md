# Metrikia Marketing Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Open-source Claude Skills for marketing analytics, attribution, and ad performance, by the team at Metrikia.

## What is this?

Claude Skills are reusable expert workflows packaged as folders containing a `SKILL.md` file. Each skill teaches Claude a methodology for a specific marketing task. You can install them in Claude Code or the Claude apps and invoke them with `/skill-name` to get expert guidance on your own campaign data.

Skills include:
- Step-by-step workflow instructions
- Real-world examples and templates
- Best practices for interpreting results
- No vendor lock-in: works with your own data

## Install

### Option A: Claude Code Plugin Marketplace

If you have Claude Code installed:

```bash
/plugin marketplace add metrikia-io/marketing-skills
/plugin install marketing-skills@metrikia-marketing-skills
```

### Option B: Manual Installation

Clone this repository and copy a skill folder into your local skills directory:

```bash
cp -r skills/attribution-model-analysis ~/.claude/skills/
```

Then use it in Claude Code or the Claude web app with `/attribution-model-analysis`.

## Skills

| Skill | Description |
|-------|-------------|
| `attribution-model-analysis` | Compare and interpret multi-touch attribution models (first-touch, last-touch, linear, time-decay, U-shaped, W-shaped) on your own campaign data. Understand which touchpoints drive revenue and optimize your media mix. |

### Coming Soon

We are working on:
- `roas-mer-audit`: Audit return on ad spend (ROAS) and marketing efficiency ratio (MER) across campaigns and channels
- `utm-taxonomy-audit`: Validate and standardize UTM parameters across your marketing stack
- `closing-funnel-metrics`: Analyze deal velocity, pipeline conversion, and revenue attribution through your closing funnel

## Why Metrikia built this

Metrikia builds an ad tracking and revenue attribution platform for agencies and businesses focused on closing-funnel metrics. We work with marketing teams every day on how to interpret their campaign data, model customer journeys, and tie ad spend to actual revenue.

These skills share the methodology underlying the Metrikia product. We believe attribution and analytics are better when they're transparent, explainable, and accessible. Open-sourcing these workflows lets marketers and developers understand our approach and apply it to their own data.

Learn more at [metrikia.io](https://metrikia.io).

## Contributing

We welcome contributions: new skills, improvements to existing ones, and bug reports.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the skill quality bar and how to submit a pull request.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Code of Conduct

Please review our [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

If you discover a security concern, please see [SECURITY.md](SECURITY.md).
