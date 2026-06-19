#!/usr/bin/env python3
"""Atlas programmatic SEO generator.

Reads pseo/{sectors,functions,usecases}.json and emits ~20k differentiated
pages under /secteurs, /fonctions, /villes, /cas-usage plus a /solutions hub,
multi-file sitemaps + sitemap_index.xml, and updates robots.txt.

Usage:
  python3 pseo/generate.py            # full build
  python3 pseo/generate.py --sample   # tiny build to validate template
"""
import json, os, re, sys, html, hashlib, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSEO = os.path.join(ROOT, "pseo")
BASE = "https://atlasconseil.netlify.app"
ORG_ID = f"{BASE}/#organization"
LASTMOD = "2026-06-17"
SAMPLE = "--sample" in sys.argv

def load(name):
    with open(os.path.join(PSEO, name), encoding="utf-8") as f:
        return json.load(f)

SECTORS = load("sectors.json")
FUNCTIONS = load("functions.json")
USECASES = load("usecases.json")

SERVICES = [
    {"slug": "transformation-ia", "title": "Conseil en transformation IA", "short": "Transformation IA", "name": "le conseil en transformation IA"},
    {"slug": "strategie-ia", "title": "Conseil en stratégie IA", "short": "Stratégie IA", "name": "la stratégie IA"},
    {"slug": "audit-ia", "title": "Audit IA & conformité AI Act", "short": "Audit IA", "name": "l'audit IA"},
    {"slug": "automatisation-agentique", "title": "Automatisation & agents IA", "short": "Automatisation & Agentique", "name": "l'automatisation et les agents IA"},
    {"slug": "process-ia", "title": "Conseil en process IA", "short": "Process IA", "name": "le conseil en process IA"},
]
SVC = {s["slug"]: s for s in SERVICES}

CITIES = [
    ("paris","Paris","Île-de-France"),("lyon","Lyon","Auvergne-Rhône-Alpes"),("marseille","Marseille","Provence-Alpes-Côte d'Azur"),
    ("toulouse","Toulouse","Occitanie"),("nice","Nice","Provence-Alpes-Côte d'Azur"),("nantes","Nantes","Pays de la Loire"),
    ("montpellier","Montpellier","Occitanie"),("strasbourg","Strasbourg","Grand Est"),("bordeaux","Bordeaux","Nouvelle-Aquitaine"),
    ("lille","Lille","Hauts-de-France"),("rennes","Rennes","Bretagne"),("reims","Reims","Grand Est"),("le-havre","Le Havre","Normandie"),
    ("saint-etienne","Saint-Étienne","Auvergne-Rhône-Alpes"),("toulon","Toulon","Provence-Alpes-Côte d'Azur"),("grenoble","Grenoble","Auvergne-Rhône-Alpes"),
    ("dijon","Dijon","Bourgogne-Franche-Comté"),("angers","Angers","Pays de la Loire"),("nimes","Nîmes","Occitanie"),
    ("clermont-ferrand","Clermont-Ferrand","Auvergne-Rhône-Alpes"),("le-mans","Le Mans","Pays de la Loire"),("aix-en-provence","Aix-en-Provence","Provence-Alpes-Côte d'Azur"),
    ("brest","Brest","Bretagne"),("tours","Tours","Centre-Val de Loire"),("amiens","Amiens","Hauts-de-France"),("limoges","Limoges","Nouvelle-Aquitaine"),
    ("annecy","Annecy","Auvergne-Rhône-Alpes"),("perpignan","Perpignan","Occitanie"),("metz","Metz","Grand Est"),("besancon","Besançon","Bourgogne-Franche-Comté"),
    ("orleans","Orléans","Centre-Val de Loire"),("rouen","Rouen","Normandie"),("mulhouse","Mulhouse","Grand Est"),("caen","Caen","Normandie"),
    ("nancy","Nancy","Grand Est"),("avignon","Avignon","Provence-Alpes-Côte d'Azur"),("poitiers","Poitiers","Nouvelle-Aquitaine"),
    ("dunkerque","Dunkerque","Hauts-de-France"),("versailles","Versailles","Île-de-France"),("la-rochelle","La Rochelle","Nouvelle-Aquitaine"),
    ("saint-nazaire","Saint-Nazaire","Pays de la Loire"),("pau","Pau","Nouvelle-Aquitaine"),("cannes","Cannes","Provence-Alpes-Côte d'Azur"),
    ("antibes","Antibes","Provence-Alpes-Côte d'Azur"),("beziers","Béziers","Occitanie"),("calais","Calais","Hauts-de-France"),
    ("bourges","Bourges","Centre-Val de Loire"),("colmar","Colmar","Grand Est"),("valence","Valence","Auvergne-Rhône-Alpes"),
    ("quimper","Quimper","Bretagne"),("la-roche-sur-yon","La Roche-sur-Yon","Pays de la Loire"),("chambery","Chambéry","Auvergne-Rhône-Alpes"),
    ("niort","Niort","Nouvelle-Aquitaine"),("lorient","Lorient","Bretagne"),("montauban","Montauban","Occitanie"),
    ("troyes","Troyes","Grand Est"),("angouleme","Angoulême","Nouvelle-Aquitaine"),("vannes","Vannes","Bretagne"),
    ("chartres","Chartres","Centre-Val de Loire"),("beauvais","Beauvais","Hauts-de-France"),
]
CITIES = [{"slug": s, "title": t, "name": t, "region": r} for s, t, r in CITIES]
import os as _os
if _os.path.exists(_os.path.join(PSEO, "cities.json")):
    CITIES = load("cities.json")
    for _c in CITIES:
        _c.setdefault("name", _c["title"])

if SAMPLE:
    SECTORS, FUNCTIONS, USECASES, CITIES = SECTORS[:3], FUNCTIONS[:3], USECASES[:5], CITIES[:3]

# Guard: no slug collisions between use-cases and services within a folder
svc_slugs = set(SVC)
uc_slugs = {u["slug"] for u in USECASES}
assert not (svc_slugs & uc_slugs), f"slug collision uc/service: {svc_slugs & uc_slugs}"

URLS = []  # (loc, priority)

def esc(s):
    return html.escape(s, quote=True)

def jsonld(obj):
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + '</script>')

def pick(variants, *seed):
    h = int(hashlib.md5("|".join(map(str, seed)).encode()).hexdigest(), 16)
    return variants[h % len(variants)]

def pick_n(pool, n, *seed):
    """Deterministic n distinct items from pool, order varied by seed."""
    h = int(hashlib.md5(("n|" + "|".join(map(str, seed))).encode()).hexdigest(), 16)
    order = sorted(range(len(pool)), key=lambda i: hashlib.md5(f"{h}|{i}".encode()).hexdigest())
    return [pool[i] for i in order[:n]]

_MINIFY = re.compile(r">\n\s*<")
def write(relpath, content, priority="0.5"):
    content = _MINIFY.sub("><", content)  # strip inter-tag whitespace/newlines (safe: never touches >text<)
    full = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    loc = BASE + "/" + relpath
    if relpath.endswith("index.html"):
        loc = BASE + "/" + relpath[:-len("index.html")]
    URLS.append((loc, priority))

NAV = """<nav class="nav">
  <a class="brand" href="/index.html"><span class="brand-dot"></span>Atlas</a>
  <div class="nav-links">
    <div class="has-drop">
      <button class="drop-toggle nav-link">Expertises <span class="chev">▾</span></button>
      <div class="drop">
        <a href="/transformation-ia.html"><span class="di-num">01</span><span><span class="di-t">Transformation IA</span><span class="di-d">Piloter votre transformation de bout en bout</span></span></a>
        <a href="/strategie-ia.html"><span class="di-num">02</span><span><span class="di-t">Stratégie IA</span><span class="di-d">Vision, feuille de route & cas d'usage</span></span></a>
        <a href="/audit-ia.html"><span class="di-num">03</span><span><span class="di-t">Audit IA</span><span class="di-d">Maturité, conformité AI Act & data readiness</span></span></a>
        <a href="/automatisation-agentique.html"><span class="di-num">04</span><span><span class="di-t">Automatisation & Agentique</span><span class="di-d">Agents IA & copilotes en production</span></span></a>
        <a href="/process-ia.html"><span class="di-num">05</span><span><span class="di-t">Process IA</span><span class="di-d">Réinventer vos processus métier</span></span></a>
      </div>
    </div>
    <a class="nav-link" href="/solutions/">Solutions</a>
    <a class="nav-link" href="/index.html#methode">Méthode</a>
    <a class="nav-link" href="/contact.html">Contact</a>
  </div>
  <a class="btn btn-primary btn-sm" href="/contact.html">Prendre rendez-vous</a>
  <button class="nav-burger" aria-label="Ouvrir le menu"><span></span><span></span><span></span></button>
</nav>
<div class="mobile-menu">
  <button class="mm-close" aria-label="Fermer le menu">&times;</button>
  <div class="mm-kicker">Expertises</div>
  <div class="mm-sub">
    <a href="/transformation-ia.html">Transformation IA</a>
    <a href="/strategie-ia.html">Stratégie IA</a>
    <a href="/audit-ia.html">Audit IA</a>
    <a href="/automatisation-agentique.html">Automatisation & Agentique</a>
    <a href="/process-ia.html">Process IA</a>
  </div>
  <div class="mm-kicker">Explorer</div>
  <a href="/solutions/">Solutions IA</a>
  <a href="/secteurs/">Par secteur</a>
  <a href="/fonctions/">Par fonction</a>
  <a href="/villes/">Par ville</a>
  <a href="/contact.html">Contact</a>
</div>"""

def footer(related_title="Explorer", related=None):
    rel = ""
    if related:
        rel = "".join(f'<a href="{h}">{esc(t)}</a>' for h, t in related)
    return f"""<footer class="footer">
  <div class="f-glow"></div>
  <div class="footer-grid">
    <div>
      <div class="brand" style="font-size:18px;"><span class="brand-dot"></span>Atlas</div>
      <p class="muted" style="font-size:14px;line-height:1.6;max-width:34ch;margin:16px 0 0;">Cabinet indépendant de conseil en transformation IA. De la vision à la production.</p>
      <a href="/contact.html" class="btn btn-primary btn-sm" style="margin-top:22px;">Prendre rendez-vous →</a>
    </div>
    <div>
      <div class="f-col-title">Expertises</div>
      <div class="f-links">
        <a href="/transformation-ia.html">Transformation IA</a>
        <a href="/strategie-ia.html">Stratégie IA</a>
        <a href="/audit-ia.html">Audit IA</a>
        <a href="/automatisation-agentique.html">Automatisation & Agentique</a>
        <a href="/process-ia.html">Process IA</a>
      </div>
    </div>
    <div>
      <div class="f-col-title">Explorer</div>
      <div class="f-links">
        <a href="/solutions/">Toutes les solutions IA</a>
        <a href="/secteurs/">IA par secteur</a>
        <a href="/fonctions/">IA par fonction</a>
        <a href="/villes/">IA par ville</a>
      </div>
    </div>
    <div>
      <div class="f-col-title">{esc(related_title)}</div>
      <div class="f-links">{rel}</div>
    </div>
  </div>
  <div class="footer-bottom">
    <div>© 2026 Atlas · Conseil en transformation IA</div>
    <div class="fb-links"><a href="/index.html">Accueil</a><a href="/contact.html">Contact</a><a href="https://www.linkedin.com/company/atlas-conseil-ia">LinkedIn</a></div>
  </div>
</footer>"""

def head(title, desc, canonical, schemas, robots="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"):
    s = "".join(jsonld(x) for x in schemas)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="author" content="Atlas">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="fr-FR" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta name="geo.region" content="FR">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="Atlas">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE}/project/assets/atlas-src.jpg">
<meta property="og:image:width" content="980">
<meta property="og:image:height" content="980">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{BASE}/project/assets/atlas-src.jpg">
<meta name="theme-color" content="#06060c">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/atlas.css">
{s}
</head>
<body>
<div id="atlas-root">
{NAV}"""

TAIL = '</div>\n<script src="/assets/atlas.js" defer></script>\n</body>\n</html>\n'

def breadcrumb_schema(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                for i, (n, u) in enumerate(items)]}

def faq_schema(canonical, qa):
    return {"@context": "https://schema.org", "@type": "FAQPage", "@id": canonical + "#faq",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}

def service_schema(canonical, name, service_type, desc, about=None):
    o = {"@context": "https://schema.org", "@type": "Service", "@id": canonical + "#service",
         "name": name, "serviceType": service_type, "url": canonical, "description": desc,
         "image": f"{BASE}/project/assets/atlas-src.jpg", "category": "Conseil en intelligence artificielle",
         "areaServed": {"@type": "Country", "name": "France"}, "availableLanguage": "fr",
         "provider": {"@type": "ProfessionalService", "@id": ORG_ID, "name": "Atlas", "url": f"{BASE}/"}}
    if about:
        o["about"] = about
    return o

def crumbs_html(items):
    parts = []
    for i, (n, u) in enumerate(items):
        if i < len(items) - 1:
            parts.append(f'<a href="{u}">{esc(n)}</a><span class="sep">/</span>')
        else:
            parts.append(f'<span>{esc(n)}</span>')
    return f'<nav class="crumbs" aria-label="Fil d\'Ariane" style="justify-content:center;margin-bottom:20px;">{"".join(parts)}</nav>'

def hero(eyebrow, h1, lead, crumbs):
    return f"""<header class="hero" data-glowzone>
<canvas class="bg-canvas" data-constellation aria-hidden="true"></canvas>
<div class="blob blob-a" aria-hidden="true"></div><div class="blob blob-b" aria-hidden="true"></div>
<div class="orbit-motif" data-parallax="-0.05" aria-hidden="true"><div class="ring"></div><div class="ring b"></div><div class="ring c"></div><div class="core"></div></div>
<div class="hero-inner hero-sub">
<div style="position:relative;z-index:2;max-width:900px;">
{crumbs}
<span class="eyebrow"><span class="dot"></span>{esc(eyebrow)}</span>
<h1 class="h1" style="font-size:clamp(32px,4.4vw,60px);">{h1}</h1>
<p class="lead">{esc(lead)}</p>
<div class="hero-actions"><a class="btn btn-primary" href="/contact.html">Prendre rendez-vous</a><a class="btn btn-outline" href="#contenu">En savoir plus</a></div>
</div></div></header>"""

def bullets_ul(items):
    return '<ul class="checks">' + "".join(f"<li>{esc(b)}</li>" for b in items) + "</ul>"

def features_grid(items):
    cells = ""
    for i, (t, p) in enumerate(items):
        d = f' data-delay="{(i%3)*60}"' if i % 3 else ""
        cells += f'<div class="feature" data-reveal="up"{d}><h3>{esc(t)}</h3><p>{esc(p)}</p></div>'
    return f'<div class="grid grid-3">{cells}</div>'

def metric_band(metrics):
    cells = ""
    for i, (v, l) in enumerate(metrics):
        d = f' data-delay="{(i%4)*80}"' if i % 4 else ""
        cells += f'<div data-reveal="up"{d}><div class="stat-num grad-soft">{esc(v)}</div><div class="stat-lbl">{esc(l)}</div></div>'
    return f'<section class="section"><div class="container"><div class="stats">{cells}</div></div></section>'

def faq_html(qa):
    items = ""
    for i, (q, a) in enumerate(qa):
        d = f' data-delay="{i*70}"' if i else ""
        items += (f'<div class="faq-item" data-reveal="up"{d} data-faq>'
                  f'<button class="faq-q" data-faq-q>{esc(q)}<span class="faq-icon" data-faq-icon>+</span></button>'
                  f'<div class="faq-a" data-faq-a><p>{esc(a)}</p></div></div>')
    return (f'<section class="section"><div class="container narrow">'
            f'<div data-reveal="up" style="text-align:center;margin-bottom:34px;"><div class="kicker">Questions fréquentes</div>'
            f'<h2 class="h2" style="margin-top:12px;">Vos questions, nos réponses.</h2></div>'
            f'<div class="faq-list">{items}</div></div></section>')

def related_html(title, links):
    chips = "".join(f'<a class="nav-link" href="{h}" style="font-family:var(--font-mono);font-size:13px;">{esc(t)} →</a>' for h, t in links)
    return (f'<section class="section section-tight"><div class="container">'
            f'<div class="kicker" data-reveal="up" style="margin-bottom:20px;">{esc(title)}</div>'
            f'<div data-reveal="up" style="display:flex;flex-wrap:wrap;gap:14px 26px;">{chips}</div></div></section>')

def cta(title, lead):
    return (f'<section class="cta"><div class="cta-glow"></div>'
            f'<h2 class="h2" data-reveal="up" style="position:relative;font-size:clamp(28px,3.6vw,48px);margin:0 auto;max-width:20ch;">{esc(title)}</h2>'
            f'<p class="lead" data-reveal="up" data-delay="100" style="position:relative;margin:20px auto 0;max-width:48ch;">{esc(lead)}</p>'
            f'<div data-reveal="up" data-delay="180" style="position:relative;margin-top:30px;"><a class="btn btn-primary" href="/contact.html">Prendre rendez-vous →</a></div></section>')

def approach_section(ctx):
    steps = pick(METHOD_VARIANTS, ctx)
    cells = "".join(f'<div class="method-cell" data-reveal="up" data-delay="{i*80}"><div class="m-step">{esc(s)}</div><p>{esc(p.format(ctx=ctx))}</p></div>'
                    for i, (s, p) in enumerate(steps))
    h2 = pick(["Du cadrage à la valeur en production.", "Notre méthode, du diagnostic à l'échelle.",
               "Une trajectoire claire, mesurable à chaque étape."], ctx)
    return (f'<section class="section"><div class="container"><div data-reveal="up" style="margin-bottom:30px;">'
            f'<div class="kicker">Notre méthode</div><h2 class="h2" style="margin-top:14px;max-width:24ch;">{esc(h2)}</h2></div>'
            f'<div class="method">{cells}</div></div></section>')

INTRO_VARIANTS = [
    "{uc_cap} : {dim_low} fait face à des enjeux spécifiques que l'IA permet d'adresser concrètement. Atlas conçoit et industrialise la solution, de la preuve de valeur à la production.",
    "Pour {dim_low}, {uc_low} n'a de valeur que si elle passe en production. C'est la promesse d'Atlas : méthode, indépendance et exigence d'exécution.",
    "Atlas accompagne {dim_low} sur {uc_low} : cadrage, prototype évaluable en quelques semaines, puis industrialisation conforme et durable — sans dépendance technologique.",
    "Dans {dim_low}, {uc_low} change la donne quand elle est bien cadrée et ancrée dans vos données. Atlas la mène du diagnostic à l'échelle.",
    "{uc_cap} appliquée à {dim_low} : Atlas part de vos cas réels, prouve la valeur, puis industrialise avec les garde-fous nécessaires.",
    "Réussir {uc_low} dans {dim_low} suppose plus qu'un modèle performant : des données, une gouvernance et l'adhésion des équipes. Atlas adresse les quatre.",
    "Atlas aide {dim_low} à transformer {uc_low} en avantage durable — mesuré en production, pas en slide.",
    "De la vision à l'exécution, Atlas déploie {uc_low} pour {dim_low} avec une exigence simple : une valeur métier prouvée et conforme.",
    "{uc_cap} : un levier concret pour {dim_low}, à condition de le mener jusqu'à la production. C'est précisément le métier d'Atlas.",
    "Pour {dim_low}, Atlas conçoit {uc_low} comme une capacité durable — évaluée, sécurisée, et transmise à vos équipes.",
    "{uc_cap} dans {dim_low} : Atlas relie l'ambition de la direction aux contraintes du terrain, du prototype au passage à l'échelle.",
    "L'IA ne vaut que par la décision qu'elle sert. Pour {dim_low}, Atlas met {uc_low} au service de résultats clairs et mesurables.",
    "Atlas industrialise {uc_low} pour {dim_low} : évaluation rigoureuse, conformité AI Act intégrée, et autonomie des équipes en sortie de mission.",
    "Dans {dim_low}, beaucoup de POC, peu de valeur réelle. Atlas fait de {uc_low} un cas d'usage en production, pas une démonstration.",
    "{uc_cap} pour {dim_low}, menée par un cabinet indépendant : le bon niveau de technologie pour votre contexte, jamais l'inverse.",
    "Atlas cadre, prototype et met à l'échelle {uc_low} dans {dim_low} — avec des jalons mesurables à chaque étape.",
]

CROSS_VARIANTS = [
    "Concrètement, {uc_low} ne se résume pas à un outil : dans {dim_low}, elle doit s'intégrer à vos processus, vos données et vos contraintes de conformité.",
    "Ce qui distingue notre approche de {uc_low} dans {dim_low}, c'est l'exigence d'exécution : un prototype évalué sur vos données réelles avant toute industrialisation.",
    "Dans {dim_low}, la difficulté n'est pas le modèle mais l'intégration : qualité des données, gouvernance et adoption. Atlas traite ces trois fronts pour {uc_low}.",
    "Nous ancrons {uc_low} dans la réalité de {dim_low} : vos systèmes, vos référentiels et vos obligations réglementaires, sans dépendance à un éditeur.",
    "Pour {dim_low}, {uc_low} n'est un succès que si les équipes se l'approprient. Atlas conçoit la solution avec elles et leur en transmet la maîtrise.",
    "Atlas mesure {uc_low} à sa valeur captée en production dans {dim_low} — gain de temps, qualité, coûts — pas au nombre de démonstrateurs.",
    "Dans {dim_low}, {uc_low} touche des données sensibles : nous intégrons sécurité, traçabilité et conformité AI Act dès le cadrage.",
    "De la preuve de valeur au passage à l'échelle, nous séquençons {uc_low} pour {dim_low} de façon à financer chaque étape par la précédente.",
]

SOLUTION_H2 = ["{uc_title} — concrètement", "Notre dispositif pour {uc_low}", "Comment Atlas déploie {uc_low}",
               "{uc_title} : de la donnée à la production", "Mettre {uc_low} en production", "Ce que nous livrons"]

ENJEUX_VARIANTS = [("Enjeux IA · {t}", "L'IA appliquée à {n}"), ("Contexte · {t}", "Pourquoi l'IA pour {n}"),
                   ("Le contexte {t}", "{t} face à l'IA"), ("Enjeux · {t}", "Ce que l'IA change pour {n}")]

CTA_VARIANTS = [
    ("Parlons de {uc_low}.", "Un échange de 30 minutes pour cadrer {ctx} et chiffrer la valeur atteignable."),
    ("Un projet sur {uc_low} ?", "Échangeons 30 minutes pour qualifier {ctx} et les premiers gains."),
    ("Avançons sur {uc_low}.", "30 minutes pour identifier le meilleur point de départ sur {ctx}."),
    ("Passons de l'idée à la production.", "Cadrons ensemble {ctx} lors d'un premier échange de 30 minutes."),
    ("Prêt pour {uc_low} ?", "Un premier échange pour transformer {ctx} en résultats mesurables."),
    ("Donnons de la valeur à votre IA.", "30 minutes pour cadrer {ctx} et définir un premier jalon."),
]

FEATURE_FRAMES = [
    "Conçu, évalué sur vos données, puis industrialisé par Atlas.",
    "Mis en œuvre avec vos équipes et mesuré en production.",
    "Intégré à vos systèmes, avec garde-fous et supervision humaine.",
    "Déployé progressivement, du prototype au passage à l'échelle.",
    "Avec évaluation qualité systématique avant toute mise en production.",
    "Adapté à {dim_low} et à vos contraintes de conformité.",
    "Documenté et transféré à vos équipes pour gagner en autonomie.",
    "Sous contrôle humain pour les décisions sensibles.",
    "Avec des métriques de valeur suivies dès le premier jalon.",
    "Sans dépendance à un éditeur ou à un cloud particulier.",
    "Sécurisé, traçable et conforme à l'AI Act dès la conception.",
    "Branché sur vos données réelles, pas sur un jeu de démonstration.",
]

EXTRA_METRICS = [
    ("×3,5", "ROI médian à 12 mois"), ("4-6 sem.", "jusqu'au 1ᵉʳ prototype"), ("−40%", "de temps de traitement"),
    ("100%", "conforme AI Act"), ("+30%", "de productivité"), ("2-4 mois", "jusqu'à la production"),
    ("−25%", "de coûts opérationnels"), ("×2", "de capacité traitée"), ("+20 pts", "de satisfaction"),
    ("−50%", "de tâches manuelles"), ("J+90", "premiers gains mesurés"), ("98%", "de fiabilité visée"),
]

METHOD_VARIANTS = [
    [("01 — Cadrer", "Qualifier le besoin autour de {ctx}, fixer la cible de valeur et les garde-fous."),
     ("02 — Prototyper", "Prouver la valeur sur données réelles, évaluation rigoureuse, décision go / no-go factuelle."),
     ("03 — Industrialiser", "Mise en production : MLOps / LLMOps, sécurité, conformité AI Act, monitoring et qualité."),
     ("04 — Mettre à l'échelle", "Diffuser les usages, mesurer l'impact, former les équipes et transmettre l'autonomie.")],
    [("01 — Diagnostiquer", "Comprendre {ctx}, cartographier données et processus, identifier la valeur réelle."),
     ("02 — Expérimenter", "Construire un prototype sur vos données, l'évaluer sans complaisance, décider sur des faits."),
     ("03 — Déployer", "Industrialiser avec sécurité, observabilité et conformité ; maîtriser les coûts."),
     ("04 — Diffuser", "Étendre les usages, suivre l'impact et rendre vos équipes autonomes.")],
    [("01 — Aligner", "Relier {ctx} aux objectifs de la direction et aux contraintes du terrain."),
     ("02 — Prouver", "Un cas pilote évalué sur données réelles, avec critères de succès définis d'avance."),
     ("03 — Sécuriser & industrialiser", "Passage en production robuste : qualité, sécurité, conformité AI Act, monitoring."),
     ("04 — Pérenniser", "Mesure de la valeur, amélioration continue et transfert de compétences.")],
]

def section_block(kicker, h2, body_html):
    return (f'<section class="section section-tight"><div class="container">'
            f'<div class="kicker" data-reveal="up">{esc(kicker)}</div>'
            f'<h2 class="h2" data-reveal="up" data-delay="60" style="margin:14px 0 22px;max-width:26ch;">{esc(h2)}</h2>'
            f'<div data-reveal="up" data-delay="120">{body_html}</div></div></section>')

# ---------------- leaf pages: usecase × dimension ----------------
def gen_usecase_dim(uc, kind, dim):
    svc = SVC[uc["service"]]
    if kind == "sector":
        seg, hub, dim_low, dim_kicker = f"/secteurs/{dim['slug']}/{uc['slug']}.html", f"/secteurs/{dim['slug']}/", dim["name"], "Secteur"
        h1 = f"{esc(uc['h1'])} <span class=\"grad\">· {esc(dim['title'])}</span>"
        title = f"{uc['title']} pour {dim['title']} | Atlas"
        desc = f"{uc['title']} dans {dim['name']} : {uc['desc']} Conseil IA indépendant, de la preuve de valeur à la production."
        enj_k, enj_h = f"Enjeux IA · {dim['title']}", f"L'IA appliquée à {dim['name']}"
        enj_body = f'<p class="lead" style="font-size:16.5px;color:var(--muted);">{esc(dim["angle"])}</p>' + bullets_ul(dim["bullets"])
        crumbs_items = [("Accueil", "/index.html"), ("Secteurs", "/secteurs/"), (dim["title"], hub), (uc["title"], BASE + seg)]
        ctx = f"{uc['name']} pour {dim['name']}"
        about = {"@type": "Thing", "name": dim["title"]}
        contextual_q = (f"Pourquoi Atlas pour {uc['name']} dans {dim['name']} ?",
                        f"Atlas combine une connaissance des enjeux de {dim['name']} et une exécution IA indépendante : {uc['desc']} Chaque mission est mesurée à sa valeur en production.")
        related_title = f"Autres cas d'usage IA · {dim['title']}"
        rel = [(f"/secteurs/{dim['slug']}/{u['slug']}.html", u["title"]) for u in nearby(USECASES, uc, 6)]
        rel += [(f"/secteurs/{s['slug']}/{uc['slug']}.html", f"{uc['title']} · {s['title']}") for s in nearby(SECTORS, dim, 3)]
    elif kind == "function":
        seg, hub, dim_low = f"/fonctions/{dim['slug']}/{uc['slug']}.html", f"/fonctions/{dim['slug']}/", dim["name"]
        h1 = f"{esc(uc['h1'])} <span class=\"grad\">· {esc(dim['title'])}</span>"
        title = f"{uc['title']} pour {dim['title']} | Atlas"
        desc = f"{uc['title']} pour {dim['name']} : {uc['desc']} Conseil IA indépendant, de la stratégie à la mise en production."
        enj_k, enj_h = f"Enjeux IA · {dim['title']}", f"L'IA au service de {dim['name']}"
        enj_body = f'<p class="lead" style="font-size:16.5px;color:var(--muted);">{esc(dim["angle"])}</p>' + bullets_ul(dim["bullets"])
        crumbs_items = [("Accueil", "/index.html"), ("Fonctions", "/fonctions/"), (dim["title"], hub), (uc["title"], BASE + seg)]
        ctx = f"{uc['name']} pour {dim['name']}"
        about = {"@type": "Thing", "name": dim["title"]}
        contextual_q = (f"Comment l'IA transforme-t-elle {dim['name']} ?",
                        f"{dim['angle']} Sur {uc['name']}, Atlas livre une solution évaluée et industrialisée, pas une démonstration.")
        related_title = f"Autres cas d'usage IA · {dim['title']}"
        rel = [(f"/fonctions/{dim['slug']}/{u['slug']}.html", u["title"]) for u in nearby(USECASES, uc, 6)]
        rel += [(f"/fonctions/{f['slug']}/{uc['slug']}.html", f"{uc['title']} · {f['title']}") for f in nearby(FUNCTIONS, dim, 3)]
    else:  # city
        seg, hub, dim_low = f"/villes/{dim['slug']}/{uc['slug']}.html", f"/villes/{dim['slug']}/", dim["name"]
        h1 = f"{esc(uc['h1'])} <span class=\"grad\">· {esc(dim['title'])}</span>"
        title = f"{uc['title']} à {dim['title']} | Atlas"
        desc = f"{uc['title']} à {dim['title']} ({dim['region']}) : {uc['desc']} Atlas accompagne les organisations de la région."
        enj_k, enj_h = f"À {dim['title']} et en {dim['region']}", f"L'IA pour les organisations de {dim['title']}"
        enj_body = (f'<p class="lead" style="font-size:16.5px;color:var(--muted);">Atlas accompagne les entreprises, ETI et acteurs publics de {dim["title"]} '
                    f'et de la région {dim["region"]} sur leurs projets d\'intelligence artificielle, à distance comme sur site.</p>'
                    + bullets_ul(uc["bullets"]))
        crumbs_items = [("Accueil", "/index.html"), ("Villes", "/villes/"), (dim["title"], hub), (uc["title"], BASE + seg)]
        ctx = f"{uc['name']} à {dim['title']}"
        about = {"@type": "City", "name": dim["title"]}
        contextual_q = (f"Atlas intervient-il à {dim['title']} ?",
                        f"Oui. Atlas accompagne les organisations de {dim['title']} et de la région {dim['region']} sur {uc['name']}, en présentiel comme à distance.")
        related_title = f"Autres expertises IA à {dim['title']}"
        rel = [(f"/villes/{dim['slug']}/{u['slug']}.html", u["title"]) for u in nearby(USECASES, uc, 6)]
        rel += [(f"/villes/{c['slug']}/{uc['slug']}.html", f"{uc['title']} · {c['title']}") for c in nearby(CITIES, dim, 3)]

    canonical = BASE + seg
    if dim.get("stat"):
        enj_body += f'<p class="mono" style="color:var(--accent);font-size:13.5px;margin:10px 0 0;">{esc(dim["stat"])}</p>'
    intro = pick(INTRO_VARIANTS, uc["slug"], dim["slug"]).format(uc_cap=uc["title"], uc_low=uc["name"], dim_low=dim["name"], dim_title=dim["title"])
    cross = pick(CROSS_VARIANTS, dim["slug"], uc["slug"]).format(uc_low=uc["name"], dim_low=dim["name"], dim_title=dim["title"], uc_title=uc["title"])
    sol_h2 = pick(SOLUTION_H2, uc["slug"], dim["slug"]).format(uc_title=uc["title"], uc_low=uc["name"])
    feats = [(b, pick(FEATURE_FRAMES, uc["slug"], dim["slug"], i).format(dim_low=dim["name"])) for i, b in enumerate(uc["bullets"])]
    metrics = [tuple(uc["metric"])] + pick_n([m for m in EXTRA_METRICS if m[1] != uc["metric"][1]], 3, uc["slug"], dim["slug"])
    cta_t, cta_l = pick(CTA_VARIANTS, uc["slug"], dim["slug"])
    qa = [(uc["faq"][0][0], uc["faq"][0][1]), (uc["faq"][1][0], uc["faq"][1][1]), contextual_q]
    rel += [(f"/{svc['slug']}.html", f"Notre expertise : {svc['short']}")]

    schemas = [service_schema(canonical, f"{uc['title']} — {dim['title']}", uc["title"], uc["desc"], about),
               faq_schema(canonical, qa), breadcrumb_schema(crumbs_items)]
    body = (hero(f"{svc['short']} · {dim['title']}", h1, intro, crumbs_html(crumbs_items))
            + '<a id="contenu"></a>'
            + section_block(enj_k, enj_h, enj_body)
            + section_block(pick(["Notre réponse", "En pratique", "Notre dispositif", "Concrètement"], uc["slug"], dim["slug"]), sol_h2,
                            f'<p class="lead" style="font-size:16.5px;color:var(--muted);">{esc(cross)}</p>'
                            + features_grid(feats))
            + approach_section(ctx)
            + metric_band(metrics)
            + faq_html(qa)
            + related_html(related_title, rel)
            + cta(cta_t.format(uc_low=uc["name"], ctx=ctx), cta_l.format(uc_low=uc["name"], ctx=ctx)))
    page = head(title, desc, canonical, schemas) + body + footer(related_title, rel[:5]) + TAIL
    write(seg.lstrip("/"), page, "0.6" if kind == "sector" else "0.5")

def nearby(lst, item, n):
    """Deterministic neighbours of item within lst (excluding item)."""
    slugs = [x for x in lst if x["slug"] != item["slug"]]
    if not slugs:
        return []
    start = int(hashlib.md5(item["slug"].encode()).hexdigest(), 16) % len(slugs)
    out = []
    i = start
    while len(out) < min(n, len(slugs)):
        out.append(slugs[i % len(slugs)])
        i += 1
    return out

# ---------------- service × dimension ----------------
def gen_service_dim(svc, kind, dim):
    if kind == "sector":
        seg, hub = f"/secteurs/{dim['slug']}/{svc['slug']}.html", f"/secteurs/{dim['slug']}/"
        title = f"{svc['title']} · {dim['title']} | Atlas"
        prep = f"pour {dim['name']}"
        crumbs_items = [("Accueil", "/index.html"), ("Secteurs", "/secteurs/"), (dim["title"], hub), (svc["short"], BASE + seg)]
        about = {"@type": "Thing", "name": dim["title"]}
    elif kind == "function":
        seg, hub = f"/fonctions/{dim['slug']}/{svc['slug']}.html", f"/fonctions/{dim['slug']}/"
        title = f"{svc['title']} · {dim['title']} | Atlas"
        prep = f"pour {dim['name']}"
        crumbs_items = [("Accueil", "/index.html"), ("Fonctions", "/fonctions/"), (dim["title"], hub), (svc["short"], BASE + seg)]
        about = {"@type": "Thing", "name": dim["title"]}
    else:
        seg, hub = f"/villes/{dim['slug']}/{svc['slug']}.html", f"/villes/{dim['slug']}/"
        title = f"{svc['title']} à {dim['title']} | Atlas"
        prep = f"à {dim['title']} et en {dim['region']}"
        crumbs_items = [("Accueil", "/index.html"), ("Villes", "/villes/"), (dim["title"], hub), (svc["short"], BASE + seg)]
        about = {"@type": "City", "name": dim["title"]}
    canonical = BASE + seg
    h1 = f"{esc(svc['title'])} <span class=\"grad\">{esc(prep)}</span>"
    desc = f"{svc['title']} {prep} : Atlas, cabinet indépendant, accompagne vos projets d'IA de la vision à la production."
    lead = f"Atlas mobilise son expertise — {svc['name']} — au service de votre contexte, {prep}, avec méthode, indépendance et exigence d'exécution."
    qa = [
        (f"En quoi consiste {svc['name']} {prep} ?", f"Atlas adapte {svc['name']} à votre contexte : diagnostic, cadrage, prototype évaluable puis industrialisation conforme et durable."),
        ("Êtes-vous indépendants des éditeurs ?", "Oui, strictement. Nos recommandations ne servent que votre intérêt : le choix des modèles et plateformes se fait sur vos contraintes, jamais sur une commission."),
    ]
    metrics = pick_n(EXTRA_METRICS, 4, svc["slug"], dim["slug"])
    rel = [(f"/{svc['slug']}.html", f"Notre offre {svc['short']}")]
    if kind == "sector":
        rel += [(f"/secteurs/{dim['slug']}/{u['slug']}.html", u["title"]) for u in nearby(USECASES, {"slug": svc["slug"]}, 6)]
    elif kind == "function":
        rel += [(f"/fonctions/{dim['slug']}/{u['slug']}.html", u["title"]) for u in nearby(USECASES, {"slug": svc["slug"]}, 6)]
    else:
        rel += [(f"/villes/{dim['slug']}/{u['slug']}.html", u["title"]) for u in nearby(USECASES, {"slug": svc["slug"]}, 6)]
    schemas = [service_schema(canonical, f"{svc['title']} — {dim['title']}", svc["title"], desc, about),
               faq_schema(canonical, qa), breadcrumb_schema(crumbs_items)]
    body = (hero(f"{svc['short']} · {dim['title']}", h1, lead, crumbs_html(crumbs_items))
            + '<a id="contenu"></a>'
            + approach_section(f"{svc['name']} {prep}")
            + metric_band(metrics)
            + faq_html(qa)
            + related_html("Cas d'usage associés", rel)
            + cta(pick(["Avançons ensemble.", "Donnons un cap à votre IA.", "Passons à l'action."], svc["slug"], dim["slug"]),
                  f"Un échange de 30 minutes pour cadrer {svc['name']} {prep}."))
    write(seg.lstrip("/"), head(title, desc, canonical, schemas) + body + footer("Cas d'usage", rel[:5]) + TAIL, "0.5")

# ---------------- dimension × city (local + vertical) ----------------
def gen_dim_city(kind, dim, city):
    pref = "secteur-" if kind == "sector" else "fonction-"
    dimhub = f"/secteurs/{dim['slug']}/" if kind == "sector" else f"/fonctions/{dim['slug']}/"
    rootname = "Secteurs" if kind == "sector" else "Fonctions"
    seg = f"/villes/{city['slug']}/{pref}{dim['slug']}.html"
    canonical = BASE + seg
    title = f"IA pour {dim['title']} à {city['title']} | Atlas"
    h1 = f"L'IA pour {esc(dim['title'])} <span class=\"grad\">à {esc(city['title'])}</span>"
    desc = f"L'intelligence artificielle pour {dim['name']} à {city['title']} ({city['region']}). {dim['angle']} Conseil IA indépendant par Atlas."
    lead = f"Atlas accompagne les organisations de {city['title']} et de la région {city['region']} sur l'IA appliquée à {dim['name']}, en présentiel comme à distance."
    crumbs_items = [("Accueil", "/index.html"), ("Villes", "/villes/"), (city["title"], f"/villes/{city['slug']}/"), (dim["title"], canonical)]
    enj_body = f'<p class="lead" style="font-size:16.5px;color:var(--muted);">{esc(dim["angle"])}</p>' + bullets_ul(dim["bullets"])
    qa = [
        (f"Atlas intervient-il à {city['title']} pour {dim['name']} ?",
         f"Oui. Atlas accompagne les organisations de {city['title']} et de la région {city['region']} sur l'IA appliquée à {dim['name']}, en présentiel comme à distance."),
        (f"Par où commencer sur l'IA pour {dim['name']} ?",
         "Par un cadrage court qui identifie les cas d'usage à plus forte valeur, puis un prototype évaluable avant toute industrialisation."),
    ]
    metrics = [("×3,5", "ROI médian à 12 mois"), ("4-6 sem.", "jusqu'au 1ᵉʳ prototype"), ("120+", "cas d'usage déployés"), ("100%", "conforme AI Act")]
    rel = [(dimhub, f"Tous les cas d'usage · {dim['title']}"), (f"/villes/{city['slug']}/", f"Atlas à {city['title']}")]
    rel += [(f"/villes/{city['slug']}/{u['slug']}.html", u["title"]) for u in nearby(USECASES, dim, 6)]
    rel += [(f"/villes/{c['slug']}/{pref}{dim['slug']}.html", f"{dim['title']} · {c['title']}") for c in nearby(CITIES, city, 3)]
    about = {"@type": "City", "name": city["title"]}
    schemas = [service_schema(canonical, f"IA pour {dim['title']} — {city['title']}", "Conseil en intelligence artificielle", desc, about),
               faq_schema(canonical, qa), breadcrumb_schema(crumbs_items)]
    body = (hero(f"{dim['title']} · {city['title']}", h1, lead, crumbs_html(crumbs_items))
            + '<a id="contenu"></a>'
            + section_block(f"Enjeux IA · {dim['title']}", f"L'IA appliquée à {dim['name']}", enj_body)
            + approach_section(f"l'IA pour {dim['name']} à {city['title']}")
            + metric_band(metrics)
            + faq_html(qa)
            + related_html("Aller plus loin", rel)
            + cta(f"Un projet IA à {city['title']} ?", f"Parlons-en : 30 minutes pour cadrer l'IA appliquée à {dim['name']}."))
    write(seg.lstrip("/"), head(title, desc, canonical, schemas) + body + footer("Aller plus loin", rel[:5]) + TAIL, "0.5")

# ---------------- hub pages ----------------
def link_card(href, title, sub):
    return (f'<a href="{href}" class="card expertise-card" data-reveal="up" style="text-decoration:none;">'
            f'<div class="c-title" style="font-size:18px;">{esc(title)}</div>'
            f'<p style="margin-top:8px;">{esc(sub)}</p><span class="c-link">Découvrir →</span></a>')

def gen_dim_hub(kind, dim):
    extra_html = ""
    if kind == "sector":
        seg = f"/secteurs/{dim['slug']}/index.html"; root = "/secteurs/"; rootname = "Secteurs"
        title = f"IA pour {dim['title']} : cas d'usage & conseil | Atlas"
        desc = f"Tous les cas d'usage de l'IA pour {dim['name']} : {', '.join(dim['bullets'][:3]).lower()}… Conseil indépendant par Atlas."
        h1 = f"L'intelligence artificielle pour <span class=\"grad\">{esc(dim['title'])}</span>"
        intro = dim["angle"]
        children = [(f"/secteurs/{dim['slug']}/{u['slug']}.html", u["title"], u["desc"]) for u in USECASES]
        svc_children = [(f"/secteurs/{dim['slug']}/{s['slug']}.html", s["title"]) for s in SERVICES]
    elif kind == "function":
        seg = f"/fonctions/{dim['slug']}/index.html"; root = "/fonctions/"; rootname = "Fonctions"
        title = f"IA pour {dim['title']} : cas d'usage & conseil | Atlas"
        desc = f"Tous les cas d'usage de l'IA pour {dim['name']} : {', '.join(dim['bullets'][:3]).lower()}… Conseil indépendant par Atlas."
        h1 = f"L'intelligence artificielle pour <span class=\"grad\">{esc(dim['title'])}</span>"
        intro = dim["angle"]
        children = [(f"/fonctions/{dim['slug']}/{u['slug']}.html", u["title"], u["desc"]) for u in USECASES]
        svc_children = [(f"/fonctions/{dim['slug']}/{s['slug']}.html", s["title"]) for s in SERVICES]
    else:
        seg = f"/villes/{dim['slug']}/index.html"; root = "/villes/"; rootname = "Villes"
        ls = ", ".join(dim.get("local_sectors", []))
        title = f"Conseil en intelligence artificielle à {dim['title']} | Atlas"
        desc = f"Cabinet indépendant de conseil en IA à {dim['title']} ({dim['region']}) : {dim.get('economy','')[:118]}"
        h1 = f"Conseil en transformation IA à <span class=\"grad\">{esc(dim['title'])}</span>"
        intro = f"{dim.get('economy','')} Filières clés : {ls}. {dim.get('angle','')}"
        children = [(f"/cas-usage/{u['slug']}.html", u["title"], u["desc"]) for u in pick_n(USECASES, 24, dim["slug"])]
        svc_children = [(f"/{s['slug']}.html", s["title"]) for s in SERVICES]
        extra_html = (related_html("Explorer par secteur", [(f"/secteurs/{s['slug']}/", s["title"]) for s in SECTORS])
                      + related_html("Explorer par fonction", [(f"/fonctions/{f['slug']}/", f["title"]) for f in FUNCTIONS]))
    canonical = BASE + seg.replace("index.html", "")
    crumbs_items = [("Accueil", "/index.html"), (rootname, root), (dim["title"], canonical)]
    cards = "".join(link_card(h, t, s) for h, t, s in children)
    svc_links = related_html("Nos expertises appliquées", svc_children)
    schemas = [breadcrumb_schema(crumbs_items),
               {"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "url": canonical, "inLanguage": "fr-FR"}]
    body = (hero(rootname[:-1] if rootname.endswith("s") else rootname, h1, intro, crumbs_html(crumbs_items))
            + '<a id="contenu"></a>'
            + f'<section class="section section-tight"><div class="container"><div class="section-head" data-reveal="up"><h2 class="h2">Cas d\'usage de l\'IA</h2><span class="mono muted">{len(children)} cas d\'usage</span></div><div class="grid grid-3">{cards}</div></div></section>'
            + svc_links
            + extra_html
            + cta("Un projet en tête ?", "Parlons-en : 30 minutes pour cadrer votre enjeu et identifier vos premiers cas d'usage."))
    write(seg.lstrip("/"), head(title, desc, canonical, schemas) + body + footer("Nos expertises", svc_children) + TAIL, "0.6")

def gen_index_hub(kind):
    if kind == "sector":
        seg, root, name = "/secteurs/index.html", "/secteurs/", "Secteurs"
        items = SECTORS; child = lambda d: (f"/secteurs/{d['slug']}/", d["title"], d["angle"])
        title = "IA par secteur d'activité — 44 secteurs | Atlas"
        desc = "L'intelligence artificielle appliquée à votre secteur : banque, santé, industrie, retail, secteur public… Conseil IA indépendant par Atlas."
        h1 = "L'IA pour <span class=\"grad\">votre secteur</span>"
    elif kind == "function":
        seg, root, name = "/fonctions/index.html", "/fonctions/", "Fonctions"
        items = FUNCTIONS; child = lambda d: (f"/fonctions/{d['slug']}/", d["title"], d["angle"])
        title = "IA par fonction métier — finance, RH, marketing… | Atlas"
        desc = "L'intelligence artificielle pour chaque fonction de l'entreprise : finance, RH, juridique, supply chain, service client… Conseil IA indépendant."
        h1 = "L'IA pour <span class=\"grad\">chaque fonction</span>"
    elif kind == "city":
        seg, root, name = "/villes/index.html", "/villes/", "Villes"
        items = CITIES; child = lambda d: (f"/villes/{d['slug']}/", d["title"], f"Conseil en IA à {d['title']} ({d['region']}).")
        title = "Cabinet de conseil en IA en France — par ville | Atlas"
        desc = "Atlas, cabinet de conseil en transformation IA présent partout en France : Paris, Lyon, Marseille, Toulouse, Bordeaux, Lille…"
        h1 = "Conseil en IA <span class=\"grad\">partout en France</span>"
    else:  # usecases
        seg, root, name = "/cas-usage/index.html", "/cas-usage/", "Cas d'usage"
        items = USECASES; child = lambda d: (f"/cas-usage/{d['slug']}.html", d["title"], d["desc"])
        title = "Cas d'usage de l'IA en entreprise — 115 demandes | Atlas"
        desc = "Tous les cas d'usage de l'intelligence artificielle en entreprise : automatisation, agents, copilotes, audit, conformité AI Act… par Atlas."
        h1 = "Cas d'usage <span class=\"grad\">de l'IA</span>"
    canonical = BASE + root
    crumbs_items = [("Accueil", "/index.html"), (name, canonical)]
    cards = "".join(link_card(*child(d)) for d in items)
    schemas = [breadcrumb_schema(crumbs_items),
               {"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "url": canonical, "inLanguage": "fr-FR"}]
    body = (hero("Explorer", h1, desc, crumbs_html(crumbs_items)) + '<a id="contenu"></a>'
            + f'<section class="section section-tight"><div class="container"><div class="section-head" data-reveal="up"><h2 class="h2">{esc(name)}</h2><span class="mono muted">{len(items)} pages</span></div><div class="grid grid-3">{cards}</div></div></section>'
            + cta("Votre besoin n'est pas listé ?", "Parlons-en : Atlas conçoit des solutions IA sur mesure, de la stratégie à la production."))
    write(seg.lstrip("/"), head(title, desc, canonical, schemas) + body + footer() + TAIL, "0.7")

def gen_usecase_hub(uc):
    svc = SVC[uc["service"]]
    seg = f"/cas-usage/{uc['slug']}.html"; canonical = BASE + seg
    title = f"{uc['title']} : par secteur, fonction & ville | Atlas"
    desc = f"{uc['desc']} Découvrez {uc['name']} par secteur, par fonction métier et par ville. Conseil IA indépendant par Atlas."
    h1 = f"{esc(uc['h1'])}"
    crumbs_items = [("Accueil", "/index.html"), ("Cas d'usage", "/cas-usage/"), (uc["title"], canonical)]
    sec_links = [(f"/secteurs/{s['slug']}/{uc['slug']}.html", s["title"]) for s in SECTORS]
    fn_links = [(f"/fonctions/{f['slug']}/{uc['slug']}.html", f["title"]) for f in FUNCTIONS]
    city_links = [(f"/villes/{c['slug']}/{uc['slug']}.html", c["title"]) for c in CITIES]
    qa = [(uc["faq"][0][0], uc["faq"][0][1]), (uc["faq"][1][0], uc["faq"][1][1])]
    schemas = [service_schema(canonical, uc["title"], uc["title"], uc["desc"]), faq_schema(canonical, qa), breadcrumb_schema(crumbs_items)]
    body = (hero(f"Cas d'usage · {svc['short']}", h1, uc["desc"], crumbs_html(crumbs_items)) + '<a id="contenu"></a>'
            + section_block("Ce que nous mettons en place", f"{uc['title']} — concrètement",
                            features_grid([(b, "Conçu, évalué puis industrialisé par Atlas.") for b in uc["bullets"]]))
            + related_html("Par secteur", sec_links)
            + related_html("Par fonction métier", fn_links)
            + related_html("Atlas partout en France", [("/villes/", "Conseil en IA par ville →")])
            + faq_html(qa)
            + cta(f"Parlons de {uc['name']}.", "Un échange de 30 minutes pour cadrer votre besoin et la valeur atteignable."))
    write(seg.lstrip("/"), head(title, desc, canonical, schemas) + body + footer("Nos expertises", [(f"/{svc['slug']}.html", svc["short"])]) + TAIL, "0.6")

def gen_solutions_master():
    seg = "/solutions/index.html"; canonical = BASE + "/solutions/"
    title = "Solutions IA par secteur, fonction, cas d'usage & ville | Atlas"
    desc = "Explorez toutes les solutions d'intelligence artificielle d'Atlas : 44 secteurs, 30 fonctions métier, 115 cas d'usage et 60 villes. Conseil IA indépendant."
    h1 = "Toutes nos <span class=\"grad\">solutions IA</span>"
    crumbs_items = [("Accueil", "/index.html"), ("Solutions", canonical)]
    blocks = related_html("Par secteur d'activité", [(f"/secteurs/{s['slug']}/", s["title"]) for s in SECTORS])
    blocks += related_html("Par fonction métier", [(f"/fonctions/{f['slug']}/", f["title"]) for f in FUNCTIONS])
    blocks += related_html("Par cas d'usage", [(f"/cas-usage/{u['slug']}.html", u["title"]) for u in USECASES])
    blocks += related_html("Par ville", [(f"/villes/{c['slug']}/", c["title"]) for c in CITIES])
    schemas = [breadcrumb_schema(crumbs_items),
               {"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "url": canonical, "inLanguage": "fr-FR"}]
    cards = "".join(link_card(h, t, s) for h, t, s in [
        ("/secteurs/", "Par secteur", "44 secteurs d'activité, de la banque au secteur public."),
        ("/fonctions/", "Par fonction", "30 fonctions métier, de la finance au service client."),
        ("/cas-usage/", "Par cas d'usage", "115 demandes concrètes adressées par l'IA."),
        ("/villes/", "Par ville", "60 villes : Atlas partout en France."),
    ])
    body = (hero("Solutions IA", h1, desc, crumbs_html(crumbs_items)) + '<a id="contenu"></a>'
            + f'<section class="section section-tight"><div class="container"><div class="grid grid-4">{cards}</div></div></section>'
            + blocks
            + cta("Un besoin précis ?", "Parlons-en : 30 minutes pour cadrer votre enjeu IA."))
    write(seg.lstrip("/"), head(title, desc, canonical, schemas) + body + footer() + TAIL, "0.8")

# ---------------- run ----------------
def main():
    for d in ("secteurs", "fonctions", "villes", "cas-usage", "solutions"):
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
    # leaves (city-leaf families removed: near-duplicate -> consolidated into rich city hubs)
    for uc in USECASES:
        for s in SECTORS:
            gen_usecase_dim(uc, "sector", s)
        for fn in FUNCTIONS:
            gen_usecase_dim(uc, "function", fn)
    for svc in SERVICES:
        for s in SECTORS:
            gen_service_dim(svc, "sector", s)
        for fn in FUNCTIONS:
            gen_service_dim(svc, "function", fn)
    # hubs
    for s in SECTORS:
        gen_dim_hub("sector", s)
    for fn in FUNCTIONS:
        gen_dim_hub("function", fn)
    for c in CITIES:
        gen_dim_hub("city", c)
    for uc in USECASES:
        gen_usecase_hub(uc)
    for k in ("sector", "function", "city", "usecase"):
        gen_index_hub(k)
    gen_solutions_master()
    write_sitemaps()
    print(f"TOTAL PAGES: {len(URLS)}")

def write_sitemaps():
    core = [f"{BASE}/", f"{BASE}/transformation-ia.html", f"{BASE}/strategie-ia.html", f"{BASE}/audit-ia.html",
            f"{BASE}/automatisation-agentique.html", f"{BASE}/process-ia.html", f"{BASE}/contact.html"]
    chunks = []
    CHUNK = 40000
    allurls = [(u, p) for u, p in URLS]
    for i in range(0, len(allurls), CHUNK):
        chunks.append(allurls[i:i + CHUNK])
    sitemap_files = []
    for idx, ch in enumerate(chunks, 1):
        fn = f"sitemap-pseo-{idx}.xml"
        rows = "".join(f'<url><loc>{u}</loc><lastmod>{LASTMOD}</lastmod><changefreq>monthly</changefreq><priority>{p}</priority></url>' for u, p in ch)
        with open(os.path.join(ROOT, fn), "w", encoding="utf-8") as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>\n')
        sitemap_files.append(fn)
    smaps = ["sitemap.xml"] + sitemap_files
    idx_rows = "".join(f'<sitemap><loc>{BASE}/{fn}</loc><lastmod>{LASTMOD}</lastmod></sitemap>' for fn in smaps)
    index_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{idx_rows}</sitemapindex>\n'
    # emit the index under both common spellings so any GSC submission resolves
    for name in ("sitemap_index.xml", "sitemap-index.xml"):
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
            f.write(index_xml)
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: " + BASE + "/sitemap_index.xml\nSitemap: " + BASE + "/sitemap-index.xml\n")
    total = sum(len(ch) for ch in chunks)
    print(f"sitemaps: {len(sitemap_files)} pseo file(s), {total} programmatic URLs; index references {len(smaps)} sitemaps")

if __name__ == "__main__":
    main()
