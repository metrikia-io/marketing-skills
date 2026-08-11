#!/usr/bin/env python3
"""
HTML shell for the report: styles, header, figures, tables, caveats.

Two rules shape everything here.

The document is built to print. A media buyer forwards this to a client or a boss,
so it has to survive Save-as-PDF without reflowing into nonsense: figures never
split across a page, tables repeat their headers, nothing relies on hover.

Every figure carries the question it answers, and every figure has a table twin.
A chart nobody can restate in words is decoration, and a number a reader cannot
copy out of the document cannot be checked. Both of those cost more credibility
than the chart buys.
"""

from safe_html import esc, narrative_to_html

STYLES = """
:root{--ink:#0b0b0b;--ink2:#3d3c39;--muted:#8a8880;--grid:#e6e5de;
--surface:#ffffff;--panel:#f7f6f2;--blue:#2a78d6;--orange:#eb6834;
--orange-ink:#b8430f;--rule:rgba(11,11,11,.12)}
*{box-sizing:border-box}
body{margin:0 auto;padding:40px 32px 56px;background:var(--surface);color:var(--ink);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;
max-width:820px;-webkit-font-smoothing:antialiased}
h1{font-size:22px;line-height:1.25;margin:0 0 4px;letter-spacing:-.01em;font-weight:600}
h2{margin:42px 0 14px;font-size:11.5px;font-weight:600;letter-spacing:.07em;
text-transform:uppercase;color:var(--muted)}
h3{font-size:16px;margin:0 0 3px;font-weight:600;letter-spacing:-.005em;color:var(--ink)}
p{margin:0 0 18px;color:var(--ink2);max-width:65ch}
/* A narrative claim opens with its bold sentence on its own line: the claim
   is the finding and the lines under it are only support. */
p>strong:first-child{display:block;color:var(--ink);font-size:15.5px;
margin-bottom:2px}
.meta{color:var(--muted);font-size:13px;margin-bottom:26px}
.hero{border:1px solid var(--rule);border-radius:12px;padding:24px 26px;
background:var(--panel);margin:0 0 10px}
.hero .top{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.hero .n{font-size:50px;font-weight:600;line-height:1;letter-spacing:-.025em}
.hero .lede{color:var(--muted);font-size:15px;max-width:34ch}
.hero .cap{color:var(--ink2);font-size:15px;margin-top:16px;max-width:62ch}
.hero .cap b{color:var(--ink);font-weight:600}
.hero .est{color:var(--muted);font-size:12px;margin-top:10px;max-width:62ch}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0 4px}
.tile{border:1px solid var(--rule);border-radius:9px;padding:13px 14px}
.tile .k{font-size:10.5px;color:var(--muted);text-transform:uppercase;
letter-spacing:.05em;line-height:1.35;min-height:28px}
.tile .v{font-size:22px;font-weight:600;margin-top:4px;letter-spacing:-.015em}
.tile .s{font-size:11.5px;color:var(--muted);margin-top:2px}
.tile.contested .v{color:var(--orange-ink)}
figure{margin:0 0 38px;break-inside:avoid;page-break-inside:avoid}
figcaption{color:var(--muted);font-size:12.5px;margin:0 0 16px;max-width:64ch}
.legend{display:flex;gap:16px;font-size:12px;color:var(--ink2);margin:0 0 14px;flex-wrap:wrap}
.legend span{display:flex;align-items:center;gap:6px}
.sw{width:9px;height:9px;border-radius:50%;display:inline-block}
.sw.sq{border-radius:2px}
.strip{display:grid;grid-template-columns:1fr auto 1fr;gap:18px;align-items:start;
border:1px solid var(--rule);border-radius:10px;padding:18px 24px;margin:0 0 38px}
.strip .n{font-size:28px;font-weight:600;letter-spacing:-.02em;line-height:1.15}
.strip .l{font-size:12.5px;color:var(--muted);margin-top:4px;line-height:1.4}
.strip .mid{font-size:12px;color:var(--muted);text-align:center;padding-top:12px}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0 0;
font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:5px 9px;border-bottom:1px solid var(--grid)}
th{color:var(--muted);font-weight:500;font-size:10.5px;text-transform:uppercase;
letter-spacing:.04em}
td:not(:first-child),th:not(:first-child){text-align:right}
details{margin-top:12px}
summary{font-size:11.5px;color:var(--muted);cursor:pointer}
.note{border-left:2px solid var(--grid);padding-left:14px;margin:16px 0;
color:var(--ink2);font-size:13.5px;max-width:65ch}
.warn{border-left-color:var(--orange)}
ul{padding-left:0;margin:0;list-style:none;max-width:65ch}
li{margin-bottom:10px;font-size:14.5px;color:var(--ink2);padding-left:16px;position:relative}
li::before{content:"";position:absolute;left:0;top:9px;width:5px;height:5px;
border-radius:50%;background:var(--muted)}
.foot{margin-top:34px;padding-top:18px;border-top:1px solid var(--grid);
font-size:13.5px;color:var(--ink2);max-width:65ch}
.foot .cta{display:inline-block;margin-top:10px;font-weight:600}
a{color:var(--blue)}
@media print{
  body{padding:0;max-width:none;font-size:10.5pt}
  @page{size:letter;margin:15mm}
  h2{margin-top:26px} details{display:none}
  thead{display:table-header-group}
  figure,.hero,.tile,.strip{break-inside:avoid}
}
"""

def _legend(*pairs):
    """Identity is never carried by color alone, so every multi-series figure
    names its own series rather than sharing one generic key."""
    spans = "".join(f'<span><i class="sw" style="background:{color}"></i>{label}</span>'
                    for color, label in pairs)
    return f'<div class="legend">{spans}</div>'


def _legends(strings):
    return {
        "composition": _legend(("#2a78d6", strings["leg_click"]),
                               ("#eb6834", strings["leg_view"])),
        "bracket": _bracket_legend(strings),
    }


def _fmt(value, prefix="", digits=0, strings=None):
    """Format a number in the report's own locale.

    A French report printing "37,378 $" reads as a bug to a French client and
    quietly costs the document its authority, so the separators travel with the
    language rather than with Python's default.
    """
    if value is None:
        return "n/a"
    rendered = f"{prefix}{value:,.{digits}f}"
    if not strings:
        return rendered
    return (rendered.replace(",", "\x00").replace(".", strings["dec"])
            .replace("\x00", strings["thou"]))


def _pct(value, strings):
    """Percentages carry a space before the sign in French and none in English."""
    return f"{value:.0%}".replace("%", strings["pct_space"] + "%")


def _hero(data, strings):
    """One number, in money, stated only as strongly as the data supports.

    A share tells a buyer nothing they can act on. The amount of claimed revenue
    that nothing in their own data can confirm is the figure that moves a budget,
    so it leads whenever the click/view split makes it computable, with the
    ROAS consequence stated immediately underneath.
    """
    economics = data.get("economics") or {}
    contested = economics.get("contested_revenue")
    if not contested:
        return _hero_fallback(data, strings)
    currency = data["actual"].get("currency") or ""
    cap = strings["hero_cap"].format(
        share=_pct(economics["contested_share_of_claimed_revenue"], strings),
        claimed=_money(data["claimed"].get("revenue"), currency, strings),
        consequence=_breakeven_sentence(economics, strings))
    return (f'<div class="hero"><div class="top">'
            f'<div class="n">{_money(contested, currency, strings)}</div>'
            f'<div class="lede">{strings["hero_lede"]}</div></div>'
            f'<div class="cap">{cap}</div>'
            f'<div class="est">{strings["hero_estimate"]}</div></div>')


def _hero_fallback(data, strings):
    """Without the click/view split there is no contested amount, so lead on the gap."""
    gap = data["gap"]
    return (f'<div class="hero"><div class="n">{_fmt(gap["units"], strings=strings)}</div>'
            f'<div class="lede">{strings["hero_gap"]}</div></div>')


def _breakeven_sentence(economics, strings):
    """The consequence, phrased by where the bracket sits against break-even."""
    breakeven, click_only = economics.get("breakeven_roas"), economics.get("click_only_roas")
    claimed = economics.get("claimed_roas")
    if not (breakeven and click_only and claimed):
        return strings["cons_no_margin"].format(claimed=_roas(claimed, strings),
                                                clicks=_roas(click_only, strings))
    key = "cons_straddles" if economics.get("straddles_breakeven") else (
        "cons_below" if click_only < breakeven else "cons_above")
    return strings[key].format(breakeven=_roas(breakeven, strings),
                               claimed=_roas(claimed, strings),
                               clicks=_roas(click_only, strings))


def _money(value, currency="", strings=None):
    if value is None:
        return "n/a"
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, "")
    rendered = _fmt(value, digits=0, strings=strings)
    return f"{rendered} {symbol}".strip() if symbol else rendered


def _roas(value, strings):
    return f"{value:.2f}x".replace(".", strings["dec"]) if value is not None else "n/a"


def _tiles(data, strings):
    """Four figures a buyer needs before reading anything: what went out, what was
    claimed for it, how much of that is contestable, and the line it has to clear."""
    claimed, economics = data["claimed"], data.get("economics") or {}
    currency = data["actual"].get("currency") or ""
    breakeven = economics.get("breakeven_roas")
    cells = [
        (strings["tile_spend"], _money(claimed.get("spend"), currency, strings),
         strings["tile_spend_sub"].format(days=data["window"]["days"]), ""),
        (strings["tile_revenue"], _money(claimed.get("revenue"), currency, strings),
         strings["tile_revenue_sub"], ""),
        (strings["tile_contested"], _money(economics.get("contested_revenue"), currency, strings),
         _contested_sub(economics, strings), "contested"),
        (strings["tile_breakeven"], _roas(breakeven, strings) if breakeven else "n/a",
         strings["tile_breakeven_sub"].format(margin=_pct(economics["gross_margin"], strings))
         if breakeven else strings["tile_breakeven_missing"], ""),
    ]
    tiles = "".join(f'<div class="tile {extra}"><div class="k">{key}</div>'
                    f'<div class="v">{value}</div><div class="s">{sub}</div></div>'
                    for key, value, sub, extra in cells)
    return f'<div class="tiles">{tiles}</div>'


def _contested_sub(economics, strings):
    share = economics.get("contested_share_of_claimed_revenue")
    return strings["tile_contested_sub"].format(share=_pct(share, strings)) if share else ""


def _corroboration(data, strings):
    """The reassuring half of the finding, and the one that makes the rest credible.

    A report that only reports what is broken reads as a sales pitch. Showing that
    the click side survives the confrontation with the store is what earns the
    reader's belief in the part that does not.
    """
    claimed, actual = data["claimed"], data["actual"]
    click = claimed.get("purchases_click")
    referred = (data.get("data_quality") or {}).get("has_referrer_data")
    matched = actual.get("referrer_paid_social")
    if not click or not referred or matched is None:
        return ""
    return (f'<h3>{strings["corr_title"]}</h3>'
            f'<figcaption>{strings["corr_question"]}</figcaption>'
            f'<div class="strip">'
            f'<div><div class="n">{_fmt(click, strings=strings)}</div>'
            f'<div class="l">{strings["corr_left"]}</div></div>'
            f'<div class="mid">{strings["corr_vs"]}</div>'
            f'<div><div class="n">{_fmt(matched, strings=strings)}</div>'
            f'<div class="l">{strings["corr_right"]}</div></div></div>')


def _claim_basis(data, strings):
    """Where the headline number came from. Everything downstream depends on it."""
    source = data.get("claim_source", {})
    # Keyed on whether the figure is reliable, not on which route produced it: a
    # campaign-level export is a sound basis too, and printing the alarm banner over
    # it told the reader to distrust a number that was fine.
    if source.get("reliable"):
        row_sum = source.get("row_sum_for_reference")
        inflation = (row_sum or 0) - source.get("value", 0)
        if inflation <= 0:
            return ""
        return (f'<div class="note">'
                f'{strings["basis_ok"].format(rows=_fmt(row_sum, strings=strings), inflation=_fmt(inflation, strings=strings))}'
                f'</div>')
    return f'<div class="note warn">{strings["basis_warn"]}</div>' 


def _figure(figure, strings):
    return (f'<figure><h3>{figure["title"]}</h3>'
            f'<figcaption>{figure["question"]}</figcaption>'
            f'{_legends(strings).get(figure["id"], "")}{figure["svg"]}'
            f'<details><summary>{strings["show_numbers"]}</summary>'
            f'<table>{figure["table"]}</table></details></figure>')


def _bracket_legend(strings):
    """The bracket carries three marks, and the wash needs naming as much as the dots."""
    return ('<div class="legend">'
            f'<span><i class="sw" style="background:#eb6834"></i>{strings["leg_low"]}</span>'
            f'<span><i class="sw" style="background:#2a78d6"></i>{strings["leg_high"]}</span>'
            f'<span><i class="sw sq" style="background:#f7ded2"></i>'
            f'{strings["leg_loss"]}</span></div>')


def _caveats(data, strings):
    caveats = data.get("caveats") or []
    if not caveats:
        return ""
    translations = strings.get("caveats") or {}
    items = "".join(f"<li>{translations.get(item['id'], item['text'])}</li>"
                    for item in caveats)
    return f'<h2>{strings["could_not_see"]}</h2><ul>{items}</ul>'


def _narrative_html(narrative):
    """Render the narrative through the escaping renderer (untrusted: quotes data)."""
    return narrative_to_html(narrative, heading_tag="h2")


CALL_URL = "https://cal.com/gaetanhamel/metrikia?overlayCalendar=true"
PRODUCT_URL = "https://metrikia.io/"

# The tool ships in English because the market is US. French is here so the
# report can be read and signed off internally, and so it works for a French
# client without rewriting the generator.
STRINGS = {
    "en": {
        "dec": ".", "thou": ",", "pct_space": "", "share_label": "view-through",
        "title": "Ad Conversion Reconciliation",
        "figures": "The figures",
        "could_not_see": "What this analysis could not see",
        "show_numbers": "Show the numbers",
        "to": "to", "days": "days",
        "tile_spend": "Spend", "tile_spend_sub": "{days} days",
        "tile_revenue": "Revenue claimed", "tile_revenue_sub": "by the platform",
        "tile_contested": "Of which unverifiable", "tile_contested_sub": "{share} of the claim",
        "tile_breakeven": "Break-even ROAS", "tile_breakeven_sub": "at {margin} gross margin",
        "tile_breakeven_missing": "gross margin not supplied",
        "hero_lede": ("of revenue claimed by the platform that nothing in your own data "
                      "can confirm"),
        "hero_cap": ("That is <b>{share} of the {claimed} it claims for itself.</b> These are "
                     "view-through conversions: the ad was shown, never clicked, and the sale "
                     "happened. {consequence}"),
        "hero_estimate": ("Estimate: the contested amount applies each campaign's average order "
                          "value, because platforms do not export purchase value split by click "
                          "and by view."),
        "cons_straddles": ("Your break-even sits at <b>{breakeven}</b>. The platform reports "
                           "{claimed}. Without the view-through it is {clicks}. <b>You are on "
                           "both sides of the line depending on which figure you read.</b>"),
        "cons_below": ("Your break-even sits at <b>{breakeven}</b>. Even the reported {claimed} "
                       "does not clear it, and on clicks alone you are at {clicks}."),
        "cons_above": ("Your break-even sits at <b>{breakeven}</b>. Reported {claimed}, and "
                       "{clicks} on clicks alone: it clears the line either way."),
        "cons_no_margin": ("Reported ROAS is {claimed} and {clicks} on clicks alone. Supply "
                           "your gross margin and this report will say which side of break-even "
                           "that puts you on."),
        "corr_title": "The click side does pass the test",
        "corr_question": ("What the platform claims on clicks, against the orders your store "
                          "actually recorded with a paid social referrer."),
        "corr_left": "claims on clicks, platform side",
        "corr_right": "store orders carrying a paid social referrer",
        "corr_vs": "against",
        "fig_bracket": "On the dashboard these campaigns look alike. They are not.",
        "q_bracket": ("Each campaign is a segment: the declared figure at one end, what is left "
                      "if no view-through were worth anything at the other. The truth is "
                      "somewhere on the segment. What matters is which side of break-even it "
                      "sits on."),
        "spend_sub": "{spend} spent", "th_spend": "Spend",
        "cta_product_tail": ("answers, by reconciling orders one by one."),
        "tile_claimed": "Claimed purchases", "tile_orders": "Recorded orders",
        "tile_roas": "Reported ROAS", "tile_mer": "Blended MER",
        "hero_view": ("of the {total} claimed purchases are view-through: credited to people "
                      "who were served an ad and never clicked it. Nothing in the store data "
                      "can confirm or refute them."),
        "hero_gap": ("gap between claimed purchases and recorded orders. See the breakdown "
                     "below before acting on it."),
        "fig_composition": "What the claimed number is made of",
        "q_composition": ("How much of each campaign's claim rests on conversions the store "
                          "cannot corroborate?"),
        "fig_roas": "The same return, measured three ways",
        "q_roas": "What happens to reported ROAS once the contested part is removed?",
        "fig_daily": "Claimed purchases against recorded orders, by day",
        "q_daily": "Is the gap steady, or does it spike on particular days?",
        "leg_click": "Click-attributed", "leg_view": "View-through (contested)",
        "leg_low": "On clicks alone, low case", "leg_high": "Declared by the platform",
        "leg_loss": "Below break-even",
        "leg_orders": "Orders recorded by the store",
        "leg_claimed": "Purchases claimed by the platform",
        "th_campaign": "Campaign", "th_share": "Share", "th_measure": "Measure",
        "th_value": "Value", "th_date": "Date", "th_claimed": "Claimed",
        "th_orders": "Recorded orders",
        "basis_ok": ("The claimed figure is the account-level deduplicated total. Adding up "
                     "the campaign-by-day export instead gives {rows}, which is {inflation} "
                     "higher. That difference is a reporting artifact rather than "
                     "over-attribution: one conversion can appear in several breakdown rows."),
        "basis_warn": ("<strong>Read this before quoting any figure.</strong> The claimed "
                       "number here is the sum of campaign-by-day rows, which overstates the "
                       "platform's own deduplicated total. Every gap below is an upper bound, "
                       "and no over-attribution claim can be made until the account-level "
                       "total is supplied."),
        "cta_limit": ("There is one question this report cannot answer: which order came "
                      "from which ad. A standard export carries no order IDs, so it stops there."),
        "cta_pitch": ("It is also the question that makes everything else easy. When you know "
                      "which ad produced which sale, you stop arguing about attribution windows. "
                      "A client asks where the number comes from and you just show them. Meta and "
                      "Google get fed real sales instead of pixel events, and start optimising on "
                      "the right thing. And you can ask, in plain English from Claude, what "
                      "actually made money last week."),
        "cta_product_lead": "That is what we built",
        "cta_offer_head": "<strong>Book a call with our media buying expert.</strong>",
        "cta_offer": ("Gaetan goes through this report with you line by line: where your gap "
                      "actually comes from, what it costs you every month, and the plan to close "
                      "it. Which campaigns to rebalance, at what thresholds, in what order. You "
                      "leave with a written action plan built on your own numbers, not with "
                      "general advice."),
        "cta_offer_why": ("This is the work an attribution consultant bills several thousand for. "
                          "We do it at no charge because it is how we meet the accounts we want "
                          "to work with. Half of them turn out not to need us, and Gaetan will "
                          "say so."),
        "cta_call_link": "Book the call with Gaetan",
        "cta_product_link": "Metrikia",
        "bar_reported": "Reported|by the platform",
        "bar_click": "Click-attributed|only",
        "bar_mer": "Blended MER|no attribution model",
        "caveats": {},
    },
    "fr": {
        "dec": ",", "thou": "\u202f", "pct_space": "\u202f",
        "share_label": "view-through",
        "title": "Réconciliation des conversions publicitaires",
        "figures": "Les chiffres",
        "could_not_see": "Ce que cette analyse n'a pas pu voir",
        "show_numbers": "Afficher les valeurs",
        "to": "au", "days": "jours",
        "tile_spend": "Dépense", "tile_spend_sub": "{days} jours",
        "tile_revenue": "CA revendiqué", "tile_revenue_sub": "par la plateforme",
        "tile_contested": "Dont invérifiable", "tile_contested_sub": "{share} du revendiqué",
        "tile_breakeven": "Seuil de rentabilité", "tile_breakeven_sub": "à {margin} de marge",
        "tile_breakeven_missing": "marge brute non fournie",
        "hero_lede": ("de chiffre d'affaires revendiqué par la plateforme que rien, dans vos "
                      "données, ne peut confirmer"),
        "hero_cap": ("Soit <b>{share} des {claimed} qu'elle s'attribue.</b> Ce sont des "
                     "view-through : la publicité a été montrée, jamais cliquée, et la vente a "
                     "eu lieu. {consequence}"),
        "hero_estimate": ("Estimation : la valeur contestée applique le panier moyen de chaque "
                          "campagne, les plateformes n'exportant pas séparément la valeur au "
                          "clic et à la vue."),
        "cons_straddles": ("Votre seuil de rentabilité est à <b>{breakeven}</b>. La plateforme "
                           "vous annonce {claimed}. Sans les view-through, vous êtes à "
                           "{clicks}. <b>Vous êtes des deux côtés du seuil selon le chiffre "
                           "que vous regardez.</b>"),
        "cons_below": ("Votre seuil de rentabilité est à <b>{breakeven}</b>. Même le {claimed} "
                       "déclaré ne le franchit pas, et au clic seul vous êtes à {clicks}."),
        "cons_above": ("Votre seuil de rentabilité est à <b>{breakeven}</b>. {claimed} déclaré, "
                       "{clicks} au clic seul : il est franchi dans les deux cas."),
        "cons_no_margin": ("Le ROAS déclaré est de {claimed}, et de {clicks} au clic seul. "
                           "Donnez votre marge brute et ce rapport dira de quel côté du seuil "
                           "de rentabilité cela vous place."),
        "corr_title": "La partie au clic, elle, passe le test",
        "corr_question": ("Ce que la plateforme revendique au clic, comparé aux commandes que "
                          "la boutique a réellement enregistrées avec une provenance paid social."),
        "corr_left": "revendications au clic, côté plateforme",
        "corr_right": "commandes boutique avec une provenance paid social",
        "corr_vs": "contre",
        "fig_bracket": "Sur le tableau de bord, ces campagnes se ressemblent. Dans les faits, non.",
        "q_bracket": ("Chaque campagne est un segment : à une extrémité ce que la plateforme "
                      "déclare, à l'autre ce qu'il reste si aucun view-through ne valait rien. "
                      "La vérité est quelque part sur le segment. Ce qui compte, c'est de quel "
                      "côté du seuil de rentabilité il se trouve."),
        "spend_sub": "{spend} dépensés", "th_spend": "Dépense",
        "cta_product_tail": ("répond, en rapprochant les commandes une par une."),
        "tile_claimed": "Achats déclarés", "tile_orders": "Commandes enregistrées",
        "tile_roas": "ROAS déclaré", "tile_mer": "MER blended",
        "hero_view": ("des {total} achats déclarés sont des view-through : attribués à des "
                      "personnes exposées à la publicité sans jamais avoir cliqué. Rien dans "
                      "les données de la boutique ne peut les confirmer ni les infirmer."),
        "hero_gap": ("d'écart entre les achats déclarés et les commandes enregistrées. Lisez "
                     "la décomposition ci-dessous avant d'en tirer une conclusion."),
        "fig_composition": "De quoi le chiffre déclaré est fait",
        "q_composition": ("Quelle part de la revendication de chaque campagne repose sur des "
                          "conversions que la boutique ne peut pas corroborer ?"),
        "fig_roas": "Le même retour, mesuré de trois façons",
        "q_roas": "Que devient le ROAS déclaré une fois la part contestée retirée ?",
        "fig_daily": "Achats déclarés contre commandes enregistrées, par jour",
        "q_daily": "L'écart est-il stable, ou fait-il des pics certains jours ?",
        "leg_click": "Attribué au clic", "leg_view": "View-through (contesté)",
        "leg_low": "Au clic seul, hypothèse basse", "leg_high": "Déclaré par la plateforme",
        "leg_loss": "Sous le seuil de rentabilité",
        "leg_orders": "Commandes enregistrées par la boutique",
        "leg_claimed": "Achats déclarés par la plateforme",
        "th_campaign": "Campagne", "th_share": "Part", "th_measure": "Mesure",
        "th_value": "Valeur", "th_date": "Date", "th_claimed": "Déclarés",
        "th_orders": "Commandes enregistrées",
        "basis_ok": ("Le chiffre déclaré retenu est le total dédupliqué au niveau du compte. "
                     "L'addition de l'export campagne par jour donne {rows}, soit {inflation} "
                     "de plus. Cette différence est un artefact de reporting et non de la "
                     "sur-attribution : une même conversion peut apparaître dans plusieurs "
                     "lignes ventilées."),
        "basis_warn": ("<strong>À lire avant de citer le moindre chiffre.</strong> Le chiffre "
                       "déclaré ici est la somme des lignes campagne par jour, qui surestime le "
                       "total dédupliqué de la plateforme elle-même. Tous les écarts ci-dessous "
                       "sont des bornes hautes, et aucune conclusion de sur-attribution n'est "
                       "possible tant que le total au niveau du compte n'est pas fourni."),
        "cta_limit": ("Il reste une question à laquelle ce rapport ne peut pas répondre : "
                      "quelle commande vient de quelle publicité. Un export standard ne contient "
                      "aucun identifiant de commande, il s'arrête là."),
        "cta_pitch": ("C'est aussi la question qui rend tout le reste simple. Quand vous savez "
                      "quelle publicité a produit quelle vente, vous arrêtez de débattre de "
                      "fenêtres d'attribution. Un client demande d'où sort le chiffre, vous lui "
                      "montrez. Meta et Google reçoivent vos vraies ventes au lieu d'événements "
                      "pixel, et se mettent à optimiser sur la bonne chose. Et vous pouvez "
                      "demander, en français depuis Claude, ce qui a réellement rapporté la "
                      "semaine dernière."),
        "cta_product_lead": "C'est pour ça qu'on a construit",
        "cta_offer_head": "<strong>Réservez un call avec notre expert en media buying.</strong>",
        "cta_offer": ("Gaetan reprend ce rapport avec vous, ligne par ligne : d'où vient "
                      "exactement votre écart, ce qu'il vous coûte chaque mois, et le plan pour "
                      "le refermer. Quelles campagnes rebasculer, sur quels seuils, dans quel "
                      "ordre. Vous ressortez avec un plan d'action écrit sur vos chiffres, pas "
                      "avec des généralités."),
        "cta_offer_why": ("C'est le travail qu'un consultant en attribution facture plusieurs "
                          "milliers d'euros. On le fait sans frais parce que c'est comme ça qu'on "
                          "rencontre les comptes avec qui on a envie de travailler. La moitié "
                          "n'ont pas besoin de nous, et Gaetan vous le dira."),
        "cta_call_link": "Réserver le call avec Gaetan",
        "cta_product_link": "Metrikia",
        "bar_reported": "Déclaré|par la plateforme",
        "bar_click": "Attribué au clic|seulement",
        "bar_mer": "MER blended|sans modèle d'attribution",
        "caveats": {
            "unverified_claim_basis": (
                "Aucun total dédupliqué au niveau du compte n'a été fourni : le chiffre "
                "déclaré est donc une somme de lignes surestimée. Aucune conclusion de "
                "sur-attribution n'est possible."),
            "store_may_not_cover_all_revenue": (
                "L'export de la boutique est supposé contenir tout le chiffre d'affaires. Si "
                "des ventes passent aussi par Amazon, du retail, une seconde boutique ou des "
                "abonnements facturés ailleurs, le dénominateur est sous-estimé et l'écart "
                "surestimé. À confirmer avant publication."),
            "refunds_invisible": (
                "Aucune donnée de remboursement dans l'export de la boutique : les "
                "remboursements n'ont pas pu être retirés."),
            "timezone_assumed_identical": (
                "Le compte publicitaire et la boutique ont été supposés partager le même "
                "fuseau horaire. Significatif sur une fenêtre courte, négligeable sur une "
                "fenêtre longue."),
        },
    },
}

def _footer(strings):
    """Name the structural limit, tie it to the number the reader just saw, then offer.

    This used to run four paragraphs and read as a sales page grafted onto an
    analysis. It survives at three sentences because the limit is the pitch: the
    contested amount is undecidable for one concrete reason, and that reason is
    exactly what the product removes. Stating it once is more persuasive than
    describing the benefit at length.
    """
    return (f'<div class="foot"><p>{strings["cta_limit"]} '
            f'<a href="{PRODUCT_URL}">{strings["cta_product_link"]}</a> '
            f'{strings["cta_product_tail"]}</p>'
            f'<a class="cta" href="{CALL_URL}">{strings["cta_call_link"]}</a></div>')


def render_page(data, figures, account, narrative="", lang="en"):
    strings = STRINGS.get(lang, STRINGS["en"])
    window = data["window"]
    title = strings["title"] + (" - " + esc(account) if account else "")
    body = "".join(_figure(figure, strings) for figure in figures) + _corroboration(data, strings)
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>{STYLES}</style></head><body>'
            f'<h1>{title}</h1>'
            f'<div class="meta">{window["start"]} {strings["to"]} {window["end"]} '
            f'({window["days"]} {strings["days"]})</div>'
            f'{_hero(data, strings)}{_tiles(data, strings)}{_claim_basis(data, strings)}'
            f'<h2>{strings["figures"]}</h2>{body}'
            f'{_narrative_html(narrative)}{_caveats(data, strings)}{_footer(strings)}'
            f'</body></html>')
