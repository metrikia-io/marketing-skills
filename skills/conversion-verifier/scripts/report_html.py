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
:root{--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--surface:#fcfcfb;--blue:#2a78d6;--orange:#eb6834;--rule:rgba(11,11,11,.10)}
*{box-sizing:border-box}
body{margin:0;padding:32px;background:var(--surface);color:var(--ink);
font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;
max-width:840px;margin-inline:auto;-webkit-font-smoothing:antialiased}
h1{font-size:26px;line-height:1.25;margin:0 0 6px;letter-spacing:-.01em}
h2{font-size:17px;margin:38px 0 10px;letter-spacing:-.005em}
h3{font-size:14px;margin:0 0 2px;font-weight:600}
p{margin:0 0 12px;color:var(--ink2)}
.meta{color:var(--muted);font-size:13px;margin-bottom:26px}
.hero{border:1px solid var(--rule);border-radius:10px;padding:20px 22px;margin:22px 0}
.hero .n{font-size:40px;font-weight:600;line-height:1.05;letter-spacing:-.02em}
.hero .cap{color:var(--ink2);font-size:14px;margin-top:6px}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0 4px}
.tile{border:1px solid var(--rule);border-radius:8px;padding:12px 13px}
.tile .k{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.tile .v{font-size:20px;font-weight:600;margin-top:3px}
figure{margin:0 0 26px;break-inside:avoid;page-break-inside:avoid}
figcaption{color:var(--muted);font-size:12px;margin:0 0 12px}
.legend{display:flex;gap:18px;font-size:12px;color:var(--ink2);margin:0 0 8px}
.legend span{display:flex;align-items:center;gap:6px}
.sw{width:9px;height:9px;border-radius:2px;display:inline-block}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0 0;
font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--grid)}
th{color:var(--muted);font-weight:500;font-size:11px;text-transform:uppercase;
letter-spacing:.04em}
td:not(:first-child),th:not(:first-child){text-align:right}
details{margin-top:8px}
summary{font-size:12px;color:var(--muted);cursor:pointer}
.note{border-left:2px solid var(--grid);padding-left:14px;margin:14px 0;
color:var(--ink2);font-size:14px}
.warn{border-left-color:var(--orange)}
ul{padding-left:18px;color:var(--ink2)} li{margin-bottom:7px}
.foot{margin-top:34px;padding-top:16px;border-top:1px solid var(--grid);
font-size:13px;color:var(--ink2)}
a{color:var(--blue)}
@media print{
  body{padding:0;max-width:none;font-size:11pt}
  @page{size:letter;margin:16mm}
  h2{margin-top:22px} details{display:none}
  thead{display:table-header-group}
  figure,.hero,.tile{break-inside:avoid}
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
        "daily": _legend(("#2a78d6", strings["leg_orders"]),
                         ("#eb6834", strings["leg_claimed"])),
    }


def _fmt(value, prefix="", digits=0):
    if value is None:
        return "n/a"
    return f"{prefix}{value:,.{digits}f}"


def _hero(data, strings):
    """One number, stated only as strongly as the data supports."""
    claimed = data["claimed"]
    view = claimed.get("purchases_view")
    total = claimed.get("purchases")
    if view and total:
        return (f'<div class="hero"><div class="n">{view / total:.0%}</div>'
                f'<div class="cap">{strings["hero_view"].format(total=_fmt(total))}'
                f'</div></div>')
    gap = data["gap"]
    return (f'<div class="hero"><div class="n">{_fmt(gap["units"])}</div>'
            f'<div class="cap">{strings["hero_gap"]}</div></div>')


def _tiles(data, strings):
    claimed, actual, blended = data["claimed"], data["actual"], data["blended"]
    cells = [
        (strings["tile_claimed"], _fmt(claimed["purchases"])),
        (strings["tile_orders"], _fmt(actual["orders_all_sources"])),
        (strings["tile_roas"], f'{claimed["roas"]:.2f}x' if claimed.get("roas") else "n/a"),
        (strings["tile_mer"], f'{blended["mer_true_revenue_over_spend"]:.2f}x'
         if blended.get("mer_true_revenue_over_spend") else "n/a"),
    ]
    tiles = "".join(f'<div class="tile"><div class="k">{key}</div>'
                    f'<div class="v">{value}</div></div>' for key, value in cells)
    return f'<div class="tiles">{tiles}</div>'


def _claim_basis(data, strings):
    """Where the headline number came from. Everything downstream depends on it."""
    source = data.get("claim_source", {})
    if source.get("basis") == "account_level_deduplicated":
        row_sum = source.get("row_sum_for_reference")
        inflation = (row_sum or 0) - source.get("value", 0)
        if inflation <= 0:
            return ""
        return (f'<div class="note">'
                f'{strings["basis_ok"].format(rows=_fmt(row_sum), inflation=_fmt(inflation))}'
                f'</div>')
    return f'<div class="note warn">{strings["basis_warn"]}</div>' 


def _figure(figure, strings):
    return (f'<figure><h3>{figure["title"]}</h3>'
            f'<figcaption>{figure["question"]}</figcaption>'
            f'{_legends(strings).get(figure["id"], "")}{figure["svg"]}'
            f'<details><summary>{strings["show_numbers"]}</summary>'
            f'<table>{figure["table"]}</table></details></figure>')


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
        "title": "Ad Conversion Reconciliation",
        "figures": "The figures",
        "could_not_see": "What this analysis could not see",
        "show_numbers": "Show the numbers",
        "to": "to", "days": "days",
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
        "title": "Réconciliation des conversions publicitaires",
        "figures": "Les chiffres",
        "could_not_see": "Ce que cette analyse n'a pas pu voir",
        "show_numbers": "Afficher les valeurs",
        "to": "au", "days": "jours",
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
    """Name the open question, show what answering it feels like, then offer a read.

    Written as continuous prose rather than a benefit list, because a bullet stack
    reads as a sales page and this arrives at the end of an honest analysis. What
    creates want here is a scene the reader recognises from their own week, not a
    feature they have to imagine.
    """
    return (f'<div class="foot">{strings["cta_limit"]}<br><br>'
            f'{strings["cta_pitch"]}<br><br>'
            f'{strings["cta_product_lead"]} '
            f'<a href="{PRODUCT_URL}">{strings["cta_product_link"]}</a>.<br><br>'
            f'{strings["cta_offer_head"]}<br>'
            f'{strings["cta_offer"]}<br><br>'
            f'{strings["cta_offer_why"]} '
            f'<a href="{CALL_URL}">{strings["cta_call_link"]}</a></div>')


def render_page(data, figures, account, narrative="", lang="en"):
    strings = STRINGS.get(lang, STRINGS["en"])
    window = data["window"]
    title = strings["title"] + (" - " + esc(account) if account else "")
    body = "".join(_figure(figure, strings) for figure in figures)
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>{STYLES}</style></head><body>'
            f'<h1>{title}</h1>'
            f'<div class="meta">{esc(window["start"])} {strings["to"]} {esc(window["end"])} '
            f'({esc(window["days"])} {strings["days"]})</div>'
            f'{_hero(data, strings)}{_tiles(data, strings)}{_claim_basis(data, strings)}'
            f'<h2>{strings["figures"]}</h2>{body}'
            f'{_narrative_html(narrative)}{_caveats(data, strings)}{_footer(strings)}'
            f'</body></html>')
