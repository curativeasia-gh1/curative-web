#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3VO static site generator -> dist/ (Cloudflare Pages ready) + standalone index for preview."""
import os, json, shutil, html

BASE = "https://m3vo.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
CSS  = open(os.path.join(ROOT, "styles.css"), encoding="utf-8").read()
JS   = open(os.path.join(ROOT, "app.js"), encoding="utf-8").read()

CONTACT_FN = r'''// functions/api/contact.js — Cloudflare Pages Function for the M3VO contact form.
// Route: POST /api/contact  (Pages maps /functions/api/contact.js to this path)
//
// Configure in Cloudflare Pages -> Settings -> Environment variables:
//   CONTACT_TO           recipient, e.g. hello@m3vo.com            (optional; defaults to hello@m3vo.com)
//   RESEND_API_KEY       secret; if set, email is sent via Resend  (https://resend.com)
//   CONTACT_FROM         verified Resend sender, e.g. "M3VO Website <noreply@m3vo.com>"
//   CONTACT_WEBHOOK_URL  optional; the enquiry JSON is also POSTed here (Slack/CRM/your worker)
// Set RESEND_API_KEY and/or CONTACT_WEBHOOK_URL — at least one — for delivery to succeed.

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json; charset=utf-8" } });

export async function onRequestPost({ request, env }) {
  let data = {};
  try {
    const ct = request.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await request.json();
    } else {
      const fd = await request.formData();
      for (const [k, v] of fd) data[k] = v;
    }
  } catch {
    return json({ ok: false, error: "Invalid request." }, 400);
  }

  // Honeypot: bots fill this hidden field. Accept silently, deliver nothing.
  if ((data.company_website || "").toString().trim() !== "") return json({ ok: true });

  const s = (v) => (v == null ? "" : v.toString().trim());
  const name = s(data.name), email = s(data.email);
  const improve = s(data.improve) || s(data.message);
  const company = s(data.company), phone = s(data.phone), country = s(data.country), systems = s(data.systems);

  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  if (!name || !emailOk || !improve)
    return json({ ok: false, error: "Please add your name, a valid email and a short description." }, 422);
  if (improve.length > 5000 || name.length > 200)
    return json({ ok: false, error: "That message is a little too long." }, 422);

  const to = env.CONTACT_TO || "hello@m3vo.com";
  const subject = `New M3VO enquiry — ${name}${company ? " (" + company + ")" : ""}`;
  const text = [
    `Name:     ${name}`,
    `Company:  ${company || "—"}`,
    `Email:    ${email}`,
    `Phone:    ${phone || "—"}`,
    `Country:  ${country || "—"}`,
    `Systems:  ${systems || "—"}`,
    ``,
    `What they want to improve:`,
    improve,
    ``,
    `— sent from the m3vo.com contact form`,
  ].join("\n");

  let delivered = false;
  const errors = [];

  if (env.RESEND_API_KEY) {
    try {
      const r = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, "content-type": "application/json" },
        body: JSON.stringify({
          from: env.CONTACT_FROM || "M3VO Website <onboarding@resend.dev>",
          to: [to],
          reply_to: email,
          subject,
          text,
        }),
      });
      if (r.ok) delivered = true;
      else errors.push("resend:" + r.status + " " + (await r.text()).slice(0, 180));
    } catch (e) {
      errors.push("resend:" + e.message);
    }
  }

  if (env.CONTACT_WEBHOOK_URL) {
    try {
      const r = await fetch(env.CONTACT_WEBHOOK_URL, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name, company, email, phone, country, systems, improve, subject, receivedAt: new Date().toISOString() }),
      });
      if (r.ok) delivered = true;
      else errors.push("webhook:" + r.status);
    } catch (e) {
      errors.push("webhook:" + e.message);
    }
  }

  if (!delivered)
    return json(
      { ok: false, error: "We couldn't deliver that just now — please email hello@m3vo.com.",
        detail: errors.join(" | ") || "No delivery method configured: set RESEND_API_KEY or CONTACT_WEBHOOK_URL." },
      503
    );

  return json({ ok: true });
}

export const onRequestGet = () =>
  new Response("Method Not Allowed", { status: 405, headers: { allow: "POST" } });
'''

ENTITY_LONG = ("M3VO is a Singapore-based software development and business automation company focused on "
  "solving everyday operational problems. M3VO builds custom software, SaaS platforms, AI-powered workflows, "
  "WhatsApp customer communication systems, CRM automation and API integrations for SMEs and growing "
  "businesses in Singapore and across Asia.")

# ---------------------------------------------------------------- icons
I = {
 "ai":'<path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6zM19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8z"/>',
 "code":'<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
 "chat":'<path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.5 8.6 8.6 0 0 1-4-.9L3 21l1.9-5.5A8.5 8.5 0 1 1 21 11.5z"/>',
 "crm":'<rect x="3" y="4" width="5" height="16" rx="1.2"/><rect x="10" y="4" width="5" height="10" rx="1.2"/><rect x="17" y="4" width="4" height="13" rx="1.2"/>',
 "plug":'<path d="M9 2v6M15 2v6M6 8h12v3a6 6 0 0 1-6 6 6 6 0 0 1-6-6zM12 17v5"/>',
 "cloud":'<path d="M17.5 19a4.5 4.5 0 0 0 .3-9 6.5 6.5 0 0 0-12.6 1.3A4 4 0 0 0 6 19z"/>',
 "health":'<path d="M3 12h3l2-5 3 10 2.5-7 1.5 2H21"/>',
 "tooth":'<path d="M12 3c2.5 0 4 1.2 5 1.2S18.5 3.5 19.5 4.5 21 8 20 12s-1.5 8-2.8 8-1-3-2.2-3-1 3-2.2 3-1.6-4-2.8-8S3.5 6 4.5 4.5 6 4 7 4.2 9.5 3 12 3z"/>',
 "box":'<path d="M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8"/>',
 "cart":'<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2 3h3l2.3 12.4a1.5 1.5 0 0 0 1.5 1.2h8.4a1.5 1.5 0 0 0 1.5-1.2L21 7H6"/>',
 "brief":'<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18"/>',
 "buildings":'<rect x="3" y="8" width="8" height="12" rx="1"/><rect x="13" y="4" width="8" height="16" rx="1"/><path d="M6 12h2M6 15h2M16 8h2M16 11h2M16 14h2"/>',
 "flow":'<circle cx="6" cy="6" r="2.4"/><circle cx="18" cy="6" r="2.4"/><circle cx="12" cy="18" r="2.4"/><path d="M8 6h8M6 8.4c0 4 4 4 6 7.2M18 8.4c0 4-4 4-6 7.2"/>',
 "doc":'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h6"/>',
 "cal":'<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>',
 "users":'<path d="M16 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="3.2"/><path d="M22 20v-2a4 4 0 0 0-3-3.8M16 3.5A4 4 0 0 1 16 11"/>',
 "chart":'<path d="M3 3v18h18"/><rect x="7" y="11" width="3" height="6"/><rect x="12" y="7" width="3" height="10"/><rect x="17" y="13" width="3" height="4"/>',
 "db":'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
 "bell":'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8M13.7 21a2 2 0 0 1-3.4 0"/>',
 "refresh":'<path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/>',
 "search":'<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
 "shield":'<path d="M12 3l8 3v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6z"/>',
 "route":'<circle cx="6" cy="19" r="2.4"/><circle cx="18" cy="5" r="2.4"/><path d="M8 19h6a4 4 0 0 0 0-8H8a4 4 0 0 1 0-8h2"/>',
 "pay":'<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
 "bulb":'<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.8.8 1 1.2 1 2.5h6c0-1.3.2-1.7 1-2.5A6 6 0 0 0 12 3z"/>',
 "arrow-right":'<path d="M5 12h14M13 6l6 6-6 6"/>',
 "arrow-down":'<path d="M12 5v14M6 13l6 6 6-6"/>',
 "chev":'<polyline points="6 9 12 15 18 9"/>',
 "plus":'<path d="M12 5v14M5 12h14"/>',
 "check":'<polyline points="20 6 9 17 4 12"/>',
 "menu":'<path d="M4 7h16M4 12h16M4 17h16"/>',
 "target":'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.3"/>',
 "layers":'<path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5M3 17l9 5 9-5"/>',
 "mail":'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
}
def ic(name, cls=""):
    c = f' class="{cls}"' if cls else ""
    return (f'<svg{c} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{I[name]}</svg>')

# ---------------------------------------------------------------- nav data
SOLUTIONS = [
 ("ai","AI & Business Automation","AI receptionists, customer service, document AI and workflow automation.","/ai-automation/"),
 ("code","Custom Software Development","Web apps, SaaS platforms, portals, dashboards and internal software.","/custom-software-development/"),
 ("chat","WhatsApp & Customer Communication","Shared inbox, AI assistance, routing, automation and CRM sync.","/whatsapp-business/"),
 ("crm","CRM & Workflow Automation","Pipelines, lead allocation, reminders, approvals and handovers.","/crm-workflow-automation/"),
 ("plug","System Integration & APIs","Connect CRM, ERP, payments, WhatsApp, e-commerce and accounting.","/system-integration/"),
 ("cloud","Cloud & Business Infrastructure","Cloud apps, hosted systems, remote access and centralised data.","/cloud-infrastructure/"),
]
INDUSTRIES = [
 ("health","Healthcare & Clinics","Reduce admin, improve the patient journey.","/healthcare-software/"),
 ("tooth","Dental & Aesthetic Clinics","Enquiry to recall, fully connected.","/dental-clinic-software/"),
 ("box","Distribution & B2B","Lead to payment across one workflow.","/industries/distribution/"),
 ("cart","Retail & E-commerce","Conversations connected to commerce.","/industries/ecommerce/"),
 ("brief","Professional Services","Enquiries and documents, structured.","/industries/professional-services/"),
 ("buildings","Multi-location Businesses","Central visibility, local control.","/industries/multi-location/"),
]

def brand():
    return '<span class="brand" aria-label="M3VO"><span>m</span><span class="g">3</span><span>vo</span></span>'

def header():
    sol = "".join(f'<a href="{u}"><span class="mi-ic">{ic(i)}</span><span><span class="mi-t">{t}</span>'
                   f'<span class="mi-d">{d}</span></span></a>' for i,t,d,u in SOLUTIONS)
    ind = "".join(f'<a href="{u}"><span class="mi-ic">{ic(i)}</span><span><span class="mi-t">{t}</span>'
                  f'<span class="mi-d">{d}</span></span></a>' for i,t,d,u in INDUSTRIES)
    m_sol = "".join(f'<a href="{u}">{t}</a>' for i,t,d,u in SOLUTIONS)
    m_ind = "".join(f'<a href="{u}">{t}</a>' for i,t,d,u in INDUSTRIES)
    return f'''<header class="site-header"><div class="wrap"><nav class="nav" aria-label="Primary">
  <a href="/" aria-label="M3VO home">{brand()}</a>
  <div class="nav-links">
    <div class="nav-item has-mega"><span class="nav-link" role="button" tabindex="0" aria-haspopup="true" aria-expanded="false">Solutions {ic('chev','chev')}</span>
      <div class="mega solutions">{sol}</div></div>
    <div class="nav-item has-mega"><span class="nav-link" role="button" tabindex="0" aria-haspopup="true" aria-expanded="false">Industries {ic('chev','chev')}</span>
      <div class="mega industries">{ind}</div></div>
    <div class="nav-item"><a class="nav-link" href="/how-we-work/">How We Work</a></div>
    <div class="nav-item"><a class="nav-link" href="/insights/">Resources</a></div>
    <div class="nav-item"><a class="nav-link" href="/about/">About</a></div>
  </div>
  <div class="nav-right">
    <a class="btn btn-ghost btn-sm" href="/contact/">Contact</a>
    <a class="btn btn-primary btn-sm" href="/contact/">Tell Us What Slows You Down</a>
    <button class="hamburger" aria-label="Menu" aria-expanded="false">{ic('menu')}</button>
  </div>
</nav></div></header>
<div class="mobile-panel" aria-label="Mobile navigation">
  <div class="m-group"><div class="m-head">Solutions {ic('chev')}</div><div class="m-sub">{m_sol}</div></div>
  <div class="m-group"><div class="m-head">Industries {ic('chev')}</div><div class="m-sub">{m_ind}</div></div>
  <a class="m-link" href="/how-we-work/">How We Work</a>
  <a class="m-link" href="/insights/">Resources</a>
  <a class="m-link" href="/about/">About</a>
  <a class="m-link" href="/contact/">Contact</a>
  <div style="margin-top:18px"><a class="btn btn-primary" href="/contact/" style="width:100%">Tell Us What Slows You Down</a></div>
</div>'''

def footer():
    sol = "".join(f'<a href="{u}">{t}</a>' for i,t,d,u in SOLUTIONS)
    ind = "".join(f'<a href="{u}">{t}</a>' for i,t,d,u in INDUSTRIES)
    return f'''<footer class="site-footer"><div class="wrap">
  <div class="foot-grid">
    <div class="foot-brand">{brand()}
      <p>{ENTITY_LONG}</p>
      <a class="foot-email" href="mailto:hello@m3vo.com">{ic('mail')} hello@m3vo.com</a></div>
    <div class="fcol"><h4>Solutions</h4>{sol}</div>
    <div class="fcol"><h4>Industries</h4>{ind}</div>
    <div class="fcol"><h4>Company</h4>
      <a href="/how-we-work/">How We Work</a><a href="/about/">About M3VO</a>
      <a href="/insights/">Resources</a><a href="/contact/">Contact</a></div>
  </div>
  <div class="foot-bottom">
    <span>&copy; <span id="yr">2026</span> M3VO. Software that makes business flow better.</span>
    <span>Built in Singapore &nbsp;·&nbsp; Built by entrepreneurs, for entrepreneurs.</span>
  </div>
</div></footer>'''

# ---------------------------------------------------------------- components
def chain(steps, title=None, note=None):
    parts=[]
    for idx,(i,label,accent) in enumerate(steps):
        parts.append(f'<div class="step{" accent" if accent else ""}"><span class="cic">{ic(i)}</span>'
                     f'<span class="cl">{label}</span></div>')
        if idx < len(steps)-1:
            parts.append(f'<span class="arrow">{ic("arrow-right")}</span>')
    t = f'<h3 style="margin-bottom:6px">{title}</h3>' if title else ''
    n = f'<p style="margin-top:14px;color:var(--muted);font-size:.94rem">{note}</p>' if note else ''
    return f'<div>{t}<div class="chain">{"".join(parts)}</div>{n}</div>'

def tick_list(items):
    lis=[]
    for it in items:
        if "||" in it:
            b,d = it.split("||",1)
            lis.append(f'<li><b>{b}</b> — {d}</li>')
        else:
            lis.append(f'<li>{it}</li>')
    return f'<ul class="ticks">{"".join(lis)}</ul>'

def reduce_list(items):
    return '<ul class="reduce-list">'+"".join(f'<li>{x}</li>' for x in items)+'</ul>'

def answer(title, paras):
    p = "".join(f'<p>{x}</p>' for x in paras)
    return f'<div class="answer"><h2>{title}</h2>{p}</div>'

def cta_band(title, text):
    return f'''<section class="section"><div class="wrap"><div class="ctaband">
      <h2>{title}</h2><p>{text}</p>
      <div class="btn-row">
        <a class="btn btn-green" href="/contact/">Tell Us What Slows You Down</a>
        <a class="btn btn-ghost" href="/how-we-work/">See how we work</a>
      </div></div></div></section>'''

def crumbs(items):
    out=[]
    for i,(label,url) in enumerate(items):
        if url and i < len(items)-1:
            out.append(f'<a href="{url}">{label}</a>')
        else:
            out.append(f'<span>{label}</span>')
        if i < len(items)-1: out.append(f'<span class="sep">/</span>')
    return f'<div class="wrap"><nav class="crumbs" aria-label="Breadcrumb">{"".join(out)}</nav></div>'

def related(links, title="Explore further"):
    a = "".join(f'<a class="textlink" href="{u}" style="margin:6px 18px 6px 0">{t} {ic("arrow-right")}</a>' for t,u in links)
    return f'<section class="section section--tight"><div class="wrap"><h3 style="margin-bottom:8px">{title}</h3><div>{a}</div></div></section>'

# ---------------------------------------------------------------- page shell
def breadcrumb_ld(items):
    el=[]
    for pos,(label,url) in enumerate(items, start=1):
        d={"@type":"ListItem","position":pos,"name":label}
        if url: d["item"]=BASE+url
        el.append(d)
    return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":el}

def page(title, desc, path, body, jsonld=None, inline=False):
    canonical = BASE + path
    css = f"<style>{CSS}</style>" if inline else '<link rel="stylesheet" href="/assets/styles.css">'
    js  = f"<script>{JS}</script>" if inline else '<script src="/assets/app.js" defer></script>'
    lds = ""
    for obj in (jsonld or []):
        lds += '<script type="application/ld+json">'+json.dumps(obj, ensure_ascii=False)+'</script>'
    favicon = ("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2064%2064'%3E"
               "%3Crect%20width='64'%20height='64'%20rx='14'%20fill='%23183591'/%3E%3Ctext%20x='50%25'%20y='54%25'"
               "%20font-family='Arial,sans-serif'%20font-size='34'%20font-weight='700'%20fill='%23fff'%20"
               "text-anchor='middle'%3Em%3Ctspan%20fill='%2300be64'%3E3%3C/tspan%3E%3C/text%3E%3C/svg%3E")
    return f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#183591">
<link rel="icon" href="{favicon}">
<meta property="og:type" content="website"><meta property="og:site_name" content="M3VO">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(desc, quote=True)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE}/assets/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{BASE}/assets/og-image.png">
<meta name="twitter:title" content="{html.escape(title, quote=True)}">
<meta name="twitter:description" content="{html.escape(desc, quote=True)}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="M3VO — software that makes business flow better">
<meta name="twitter:image:alt" content="M3VO">
<meta name="twitter:label1" content="Based in"><meta name="twitter:data1" content="Singapore">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
{css}{lds}</head><body>
{header()}
<main>{body}</main>
{footer()}
{js}</body></html>'''

# ================================================================ HOME
HOME_TITLE="AI Software & Business Automation Singapore | M3VO"
HOME_DESC="M3VO builds custom software, AI automation, WhatsApp workflows and connected business systems for SMEs in Singapore and across Asia."
HOME_BODY=""; HOME_LD=[]
def home(inline=False):
    hero_flow = f'''<div class="panel" aria-label="Example customer workflow">
      <div class="panel-head"><span class="dots"><i></i><i></i><i></i></span><span class="pt">Customer workflow · live</span></div>
      <div class="msg"><span class="av">JL</span><span><span class="mn">New WhatsApp enquiry</span>
        <span class="mt">"Hi, do you have the 2mm implant kit in stock? Need a quote for 40 units."</span></span></div>
      <div class="flow">
        <div class="flow-node is-ai"><span class="fic">{ic('ai')}</span><span><span class="ft">AI qualifies the enquiry</span>
          <span class="fd">Reads intent, checks stock, tags as a sales lead</span></span><span class="fbadge">auto</span></div>
        <div class="flow-conn"></div>
        <div class="flow-node"><span class="fic">{ic('crm')}</span><span><span class="ft">Lead created in CRM</span>
          <span class="fd">Assigned to the right salesperson</span></span></div>
        <div class="flow-conn"></div>
        <div class="flow-node"><span class="fic">{ic('doc')}</span><span><span class="ft">Quotation prepared</span>
          <span class="fd">Pulled from price list, ready to send</span></span></div>
        <div class="flow-conn"></div>
        <div class="flow-node"><span class="fic">{ic('bell')}</span><span><span class="ft">Follow-up scheduled</span>
          <span class="fd">Nothing slips; management can see it all</span></span></div>
      </div></div>'''

    hero = f'''<section class="hero"><div class="wrap"><div class="hero-grid">
      <div>
        <h1>Software that makes business flow better.</h1>
        <p class="lead">Practical AI, automation and custom software built around the way your business actually works.</p>
        <p class="sub">M3VO replaces repetitive work, disconnected systems, spreadsheets and scattered conversations with software that is simpler, smarter and easier to operate.</p>
        <div class="btn-row">
          <a class="btn btn-primary" href="/contact/">Tell Us What Slows You Down</a>
          <a class="btn btn-ghost" href="#solutions">Explore Solutions</a>
        </div>
        <div class="trustline"><span>Built in Singapore</span><span class="dot"></span>
          <span>Built for growing businesses</span><span class="dot"></span><span>Built by entrepreneurs, for entrepreneurs</span></div>
      </div>
      <div class="fr-media">{hero_flow}</div>
    </div></div></section>'''

    what = f'''<section class="section section--tight"><div class="wrap">
      {answer("What is M3VO?", [
        "M3VO is a Singapore-based software development and business automation company that builds custom software, SaaS platforms, AI automation, customer communication systems and connected workflows for SMEs and growing businesses.",
        "Our goal is simple: identify what is making work difficult, simplify it, and build a practical solution — without adding unnecessary complexity."])}
    </div></section>'''

    problem = f'''<section class="section"><div class="wrap">
      <span class="eyebrow">The real problem</span>
      <h2 class="measure">Your business should not have to work around your software.</h2>
      <p class="lead measure" style="margin-top:16px;color:var(--body)">Most businesses don't have a technology problem. They have a workflow problem. A message arrives on one phone. An order is copied into a spreadsheet. Someone makes an invoice by hand. Another person updates the CRM. Individually small — across a whole business, hours of unnecessary work.</p>
      <div class="split">
        <div class="card-soft"><div class="cs-t">Today, the tools don't talk</div>
          <div class="chips">
            <span class="chip"><span class="cd"></span>WhatsApp</span><span class="chip"><span class="cd"></span>Spreadsheets</span>
            <span class="chip"><span class="cd"></span>CRM</span><span class="chip"><span class="cd"></span>ERP</span>
            <span class="chip"><span class="cd"></span>Email</span><span class="chip"><span class="cd"></span>Accounting</span>
            <span class="chip"><span class="cd"></span>Staff knowledge</span></div></div>
        <div class="midarrow">{ic('arrow-right')}</div>
        <div class="card-soft"><div class="cs-t">With M3VO, work moves on its own</div>
          <div class="after-line">
            <span class="an">Enquiry</span><span class="aic">{ic('arrow-right')}</span>
            <span class="an">Lead</span><span class="aic">{ic('arrow-right')}</span>
            <span class="an">Quote</span><span class="aic">{ic('arrow-right')}</span>
            <span class="an">Invoice</span><span class="aic">{ic('arrow-right')}</span>
            <span class="an">Follow-up</span></div>
          <p style="margin-top:16px;color:var(--muted);font-size:.94rem">One connected flow. Full visibility for management.</p></div>
      </div>
      <div style="margin-top:44px"><p style="font-family:var(--ff-head);font-weight:600;color:var(--ink);margin-bottom:16px">M3VO helps businesses reduce:</p>
      {reduce_list(["Repetitive data entry","Manual follow-ups","Missed customer enquiries","Spreadsheet dependence",
        "Disconnected software","Duplicate work","Poor visibility between departments","Complicated approvals",
        "Staff-dependent processes","Manual reporting","Lost customer history","Repetitive admin work"])}</div>
    </div></section>'''

    sol_cards = "".join(f'''<div class="sol"><span class="sic">{ic(i)}</span><h3>{t}</h3><p>{d}</p>
      <a class="textlink" href="{u}">Explore {t.split(" &")[0].split(" (")[0]} {ic('arrow-right')}</a></div>''' for i,t,d,u in SOLUTIONS)
    solutions = f'''<section class="section section--wash" id="solutions"><div class="wrap">
      <span class="eyebrow">What M3VO does</span>
      <h2 class="measure">Practical technology for real business problems.</h2>
      <div class="sol-grid">{sol_cards}</div></div></section>'''

    diff = f'''<section class="section"><div class="wrap"><div class="frow" style="border:0;padding:0">
      <div><span class="eyebrow">The difference</span>
        <h2>We don't ask what software you want. We ask what is making your work difficult.</h2>
        <p class="lead" style="margin-top:16px;color:var(--body)">Traditional projects start with a feature list. M3VO starts with your actual workflow — then decides what should be simplified, connected, automated or rebuilt.</p></div>
      <div class="fr-media">{tick_list([
        "What are employees doing repeatedly?","Where does information get stuck?",
        "What requires manual copying?","Where do customers wait unnecessarily?",
        "Which systems don't communicate?","What does management struggle to see?",
        "Which processes depend too heavily on one person?"])}</div>
    </div></div></section>'''

    ind_rows = "".join(f'''<div class="frow{' rev' if k%2 else ''}">
        <div><span class="fr-ic">{ic(i)}</span><h3>{t}</h3><p style="margin:10px 0 18px;color:var(--body)">{d}</p>
          <a class="textlink" href="{u}">Explore {t} {ic('arrow-right')}</a></div>
        <div class="fr-media">{ch}</div></div>'''
        for k,(i,t,d,u,ch) in enumerate([
          ("tooth","Dental & Aesthetic Clinics","One connected flow from first enquiry to recall — AI reception, appointments, CRM and follow-up.","/dental-clinic-software/",
             chain([("chat","Enquiry",False),("ai","AI reception",True),("cal","Appointment",False),("health","Treatment",False),("pay","Payment",False),("refresh","Recall",False)])),
          ("box","Distribution & B2B","Move from lead to payment across one workflow instead of email, WhatsApp and spreadsheets.","/industries/distribution/",
             chain([("route","Lead",False),("doc","Quote",False),("box","Order",False),("layers","Inventory",True),("pay","Invoice",False),("bell","Follow-up",False)])),
          ("health","Healthcare & Clinics","Reduce administrative load while improving the patient journey end to end.","/healthcare-software/",
             chain([("chat","Enquiry",False),("ai","AI intake",True),("cal","Booking",False),("bell","Reminders",False),("crm","Records",False),("refresh","Follow-up",False)])),
        ]))
    industries = f'''<section class="section section--wash"><div class="wrap">
      <span class="eyebrow">Industries</span>
      <h2 class="measure">Built for businesses where operations affect revenue.</h2>
      <p class="lead measure" style="margin-top:14px;color:var(--body)">We show real operational workflows — not generic industry pages.</p>
      <div class="rows" style="margin-top:26px">{ind_rows}</div>
      <div style="margin-top:8px"><a class="textlink" href="/insights/">See all industries and resources {ic('arrow-right')}</a></div>
    </div></section>'''

    aiq = f'''<section class="section"><div class="wrap"><div class="frow" style="border:0;padding:0">
      <div><span class="eyebrow">On AI</span>
        <h2>AI should remove work — not become another tool to manage.</h2>
        <p class="lead" style="margin-top:16px;color:var(--body)">The question isn't whether you need AI. It's where AI can actually make the business easier to operate. We apply it where it saves real time.</p>
        <div class="btn-row" style="margin-top:22px"><a class="btn btn-ghost" href="/ai-automation/">Explore AI automation</a></div></div>
      <div class="fr-media">{tick_list([
        "Understanding incoming enquiries","Drafting customer responses","Summarising long conversations",
        "Classifying and qualifying leads","Extracting information from documents","Searching company knowledge",
        "Preparing reports","Routing requests to the right person"])}</div>
    </div></div></section>'''

    steps = [("01","Understand","We look at how your business operates today — people, systems, data and workflow — not how a vendor thinks it should work."),
             ("02","Identify","We find where time, information and opportunities are being lost, whether that's a manual step or a disconnected system."),
             ("03","Simplify","We improve the workflow before building. There's little value in automating a bad process."),
             ("04","Build","We develop the software, AI automation or integration required to solve the problem."),
             ("05","Connect","Where possible we connect the systems you already use, so you don't replace everything to fix one thing."),
             ("06","Improve","Once it's live and in real use, we keep improving it based on how people and customers actually behave.")]
    proc = "".join(f'<div class="pstep"><div class="pn">{n}</div><h3>{t}</h3><p>{d}</p></div>' for n,t,d in steps)
    process = f'''<section class="section section--wash"><div class="wrap">
      <span class="eyebrow">How M3VO works</span>
      <h2 class="measure">From business problem to working solution.</h2>
      <div class="proc">{proc}</div></div></section>'''

    why_items=[("target","Business-first","We think about the operational problem before the technology."),
        ("check","Practical","We favour solutions your team will actually use."),
        ("ai","AI where it matters","Applied where it creates measurable value — not as a marketing feature."),
        ("plug","Integration-friendly","Your existing technology investment doesn't get discarded by default."),
        ("refresh","Designed to evolve","Businesses change. Your software should change with them."),
        ("users","Built for SMEs","Speed, flexibility and sensible implementation over enterprise complexity.")]
    why_cards="".join(f'<div class="sol"><span class="sic">{ic(i)}</span><h3>{t}</h3><p>{d}</p></div>' for i,t,d in why_items)
    why=f'''<section class="section"><div class="wrap"><span class="eyebrow">Why M3VO</span>
      <h2 class="measure">A software partner that thinks like an operator.</h2>
      <div class="sol-grid">{why_cards}</div></div></section>'''

    faqs = FAQS[:6]
    faq_html="".join(f'<details class="qa"><summary>{q}<span class="qi">{ic("plus")}</span></summary><div class="qbody">{a}</div></details>' for q,a in faqs)
    faq=f'''<section class="section section--wash"><div class="wrap">
      <span class="eyebrow center" style="display:flex;justify-content:center">Questions</span>
      <h2 class="center">M3VO, answered.</h2>
      <div class="faq">{faq_html}</div></div></section>'''

    final = f'''<section class="section"><div class="wrap"><div class="ctaband">
      <h2>What would make your business easier to run?</h2>
      <p>You don't need to know what software you need. Start with the problem — tell us what takes too much time, keeps going wrong, or you wish just worked. We'll help decide whether it should be simplified, automated, connected or rebuilt.</p>
      <div class="btn-row">
        <a class="btn btn-green" href="/contact/">Tell Us What Slows You Down</a>
        <a class="btn btn-ghost" href="/how-we-work/">See how we work</a>
      </div></div></div></section>'''

    body = hero+what+problem+solutions+diff+industries+aiq+process+why+faq+final
    ld = [
      {"@context":"https://schema.org","@type":"Organization","name":"M3VO","alternateName":"Mevo Tech","url":BASE+"/",
       "logo":BASE+"/assets/m3vo-logo.png","image":BASE+"/assets/og-image.png","email":"hello@m3vo.com","description":ENTITY_LONG,
       "areaServed":["Singapore","Southeast Asia","Asia"],
       "knowsAbout":["AI software development","Custom software development","SaaS development",
          "Business automation","Workflow automation","CRM automation","WhatsApp Business automation",
          "API integration","Healthcare software"],
       "contactPoint":{"@type":"ContactPoint","contactType":"sales","email":"hello@m3vo.com","url":BASE+"/contact/","areaServed":"SG"}},
      {"@context":"https://schema.org","@type":"WebSite","name":"M3VO","url":BASE+"/","publisher":{"@type":"Organization","name":"M3VO"}},
      {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in FAQS]},
    ]
    global HOME_BODY, HOME_LD
    HOME_BODY, HOME_LD = body, ld
    return page(HOME_TITLE, HOME_DESC, "/", body, ld, inline=inline)

# ---------------------------------------------------------------- FAQ data
FAQS = [
 ("What does M3VO do?","M3VO builds custom software, AI automation, workflow systems and integrations that help businesses reduce manual work and operate more efficiently."),
 ("Is M3VO a software development company?","Yes. M3VO develops custom web applications, SaaS platforms, business software, AI-powered workflows and system integrations."),
 ("Where is M3VO based?","M3VO is based in Singapore and works with businesses operating locally and across Asia."),
 ("Does M3VO build AI software?","Yes. M3VO develops AI-powered customer communication, workflow automation, document processing, knowledge assistants and other business AI applications."),
 ("Can M3VO build a SaaS platform?","Yes. M3VO can design and develop SaaS products including web applications, customer portals, subscription systems, dashboards and specialised industry software."),
 ("Can M3VO automate WhatsApp?","Yes — using the official WhatsApp Business Platform, including shared inboxes, routing, AI assistance, automated replies, lead management and CRM integration."),
 ("Can M3VO integrate with existing software?","Yes. M3VO connects existing systems using APIs and automation, including CRM, ERP, e-commerce, payments, accounting, WhatsApp, email and internal applications."),
 ("Do I need to replace my current software?","Not necessarily. M3VO's preferred approach is to keep systems that work and connect or extend them where possible."),
 ("Does M3VO only work with large companies?","No. M3VO is built particularly for SMEs and growing businesses that need practical software without unnecessary enterprise complexity."),
 ("How do I start a project with M3VO?","Start by explaining the business problem or workflow you want to improve. M3VO reviews the process and recommends whether the answer is automation, AI, integration, custom software or a combination."),
]

# ---------------------------------------------------------------- generic solution/industry page
def leaf(cfg):
    bc = cfg["crumbs"]
    hero = f'''<section class="section section--tight" style="padding-top:26px">{crumbs(bc)}
      <div class="wrap" style="margin-top:8px"><div style="max-width:44ch"><span class="fr-ic">{ic(cfg["icon"])}</span></div>
      <h1 style="max-width:20ch;margin-top:18px">{cfg["h1"]}</h1>
      <p class="lead measure" style="margin-top:18px;color:var(--body)">{cfg["lead"]}</p>
      <div class="btn-row" style="margin-top:24px">
        <a class="btn btn-primary" href="/contact/">{cfg.get("cta","Tell Us What Slows You Down")}</a>
        <a class="btn btn-ghost" href="/how-we-work/">How we work</a></div></div></section>'''

    ans = f'<section class="section section--tight"><div class="wrap">{answer(cfg["answer_title"], cfg["answer_paras"])}</div></section>'

    blocks=""
    if cfg.get("chain"):
        blocks += f'<section class="section"><div class="wrap"><span class="eyebrow">{cfg.get("chain_eyebrow","The workflow")}</span>{chain(cfg["chain"], cfg.get("chain_title"), cfg.get("chain_note"))}</div></section>'
    if cfg.get("build_list"):
        intro = f'<p class="lead measure" style="margin:14px 0 26px;color:var(--body)">{cfg.get("build_intro","")}</p>' if cfg.get("build_intro") else ''
        blocks += f'''<section class="section section--wash"><div class="wrap"><span class="eyebrow">{cfg.get("build_eyebrow","What M3VO can do")}</span>
          <h2 class="measure">{cfg.get("build_title")}</h2>{intro}
          <div style="max-width:900px;margin-top:8px">{tick_list(cfg["build_list"])}</div></div></section>'''
    if cfg.get("when_list"):
        blocks += f'''<section class="section"><div class="wrap"><div class="frow" style="border:0;padding:0">
          <div><span class="eyebrow">{cfg.get("when_eyebrow","When it makes sense")}</span><h2>{cfg.get("when_title")}</h2>
            {f'<p class="lead" style="margin-top:14px;color:var(--body)">{cfg.get("when_intro")}</p>' if cfg.get("when_intro") else ''}</div>
          <div class="fr-media">{tick_list(cfg["when_list"])}</div></div></div></section>'''
    if cfg.get("connect_list"):
        blocks += f'''<section class="section section--wash"><div class="wrap"><span class="eyebrow">{cfg.get("connect_eyebrow","Connects with")}</span>
          <h2 class="measure">{cfg.get("connect_title")}</h2>
          <div style="margin-top:22px" class="chips">{"".join(f'<span class="chip">{c}</span>' for c in cfg["connect_list"])}</div>
          {f'<p style="margin-top:20px;color:var(--muted);max-width:60ch">{cfg.get("connect_note")}</p>' if cfg.get("connect_note") else ''}</div></section>'''

    rel = related(cfg["related"]) if cfg.get("related") else ""
    extra = cfg.get("extra_html","")
    band = cta_band(cfg.get("cta_title","Tell us what slows you down."),
                    cfg.get("cta_text","Describe the workflow you want to improve. We'll tell you whether the answer is automation, AI, integration or custom software."))
    body = hero+ans+blocks+extra+rel+band
    ld = [breadcrumb_ld(bc)]
    if cfg.get("service_type"):
        ld.append({"@context":"https://schema.org","@type":"Service","name":cfg["h1"],
          "serviceType":cfg["service_type"],"provider":{"@type":"Organization","name":"M3VO","url":BASE+"/"},
          "areaServed":["Singapore","Southeast Asia","Asia"],"description":cfg["lead"]})
    for obj in cfg.get("extra_ld",[]): ld.append(obj)
    return page(cfg["title"], cfg["desc"], cfg["path"], body, ld)

# ---------------------------------------------------------------- leaf configs
LEAVES = {}

LEAVES["/ai-automation/"] = dict(
  path="/ai-automation/", icon="ai", service_type="AI automation",
  title="AI Automation & AI Software Development Singapore | M3VO",
  desc="M3VO builds AI-powered automation around real business processes — AI receptionists, customer service, document AI, knowledge assistants and workflow automation.",
  crumbs=[("Home","/"),("Solutions","/#solutions"),("AI & Business Automation",None)],
  h1="AI automation that removes work — not another tool to manage.",
  lead="M3VO builds AI-powered automation designed around real business processes. Instead of dropping in a generic chatbot and calling it transformation, we find the specific points where AI saves employees time or improves customer response.",
  answer_title="What is AI business automation?",
  answer_paras=["AI business automation combines artificial intelligence with software workflows to perform or assist repetitive business processes such as customer enquiries, document processing, lead qualification, reporting and follow-ups.",
    "The objective is not to add AI everywhere. It is to remove unnecessary work while keeping people in control of the decisions that matter."],
  chain_eyebrow="Where AI fits", chain_title="A real enquiry, handled end to end",
  chain=[("chat","Enquiry",False),("ai","AI qualifies",True),("crm","CRM lead",False),("users","Salesperson",False),("doc","Quotation",False),("bell","Follow-up",False)],
  chain_note="AI does the reading, sorting and drafting. Your team makes the calls.",
  build_eyebrow="AI automation examples", build_title="Practical applications, not hype.",
  build_list=["AI customer service||analyse enquiries, understand intent and help prepare accurate responses",
    "AI receptionist||handle common questions, qualify enquiries, collect information and assist with scheduling",
    "AI sales assistant||qualify leads, summarise conversations and identify follow-up actions",
    "Document AI||read documents, extract structured information and route it into business systems",
    "Company knowledge assistant||let employees search internal documents and procedures in natural language",
    "AI workflow automation||use AI decisions inside larger workflows across CRM, email, WhatsApp and ERP"],
  when_eyebrow="Human control stays", when_title="AI that assists — with review where it matters.",
  when_intro="M3VO designs AI to automate appropriate tasks while letting you decide where human review or approval is required.",
  when_list=["Understand incoming enquiries","Draft customer responses","Summarise long conversations",
    "Classify and qualify leads","Extract information from documents","Prepare reports and route requests"],
  related=[("Custom Software Development","/custom-software-development/"),("WhatsApp & Communication","/whatsapp-business/"),
    ("CRM & Workflow Automation","/crm-workflow-automation/"),("Healthcare & Clinics","/healthcare-software/")],
  cta_title="Explore an AI use case with us.",
  cta_text="Tell us where your team spends time on repetitive work. We'll show you where AI can quietly take it off their plate.")

LEAVES["/custom-software-development/"] = dict(
  path="/custom-software-development/", icon="code", service_type="Custom software development",
  title="Custom Software Development Singapore | M3VO",
  desc="M3VO designs and develops custom business software — web apps, SaaS platforms, CRMs, portals, dashboards and internal systems built around your workflow.",
  crumbs=[("Home","/"),("Solutions","/#solutions"),("Custom Software Development",None)],
  h1="Custom software built around your workflow — not the other way around.",
  lead="M3VO designs and develops custom business software for organisations that have outgrown spreadsheets, disconnected SaaS products or manual workflows. We solve operational problems rather than build technology for its own sake.",
  answer_title="What is custom software development?",
  answer_paras=["Custom software development is the design and building of applications tailored to how a specific business operates, rather than adapting the business to fit off-the-shelf software.",
    "Sometimes existing software solves 70% of the problem. The remaining 30% becomes spreadsheets, workarounds and manual steps — and that's usually where custom software earns its keep."],
  build_eyebrow="What M3VO can build", build_title="From internal tools to full SaaS products.",
  build_list=["Web applications","SaaS platforms","CRM systems","Customer portals","B2B ordering systems",
    "Booking software","Internal management systems","Operations dashboards","Subscription platforms",
    "Workflow applications","AI-enabled applications","Industry-specific software"],
  when_eyebrow="When to consider it", when_title="Signs custom software will pay off.",
  when_list=["Employees repeatedly copy data between systems","Your workflow needs several spreadsheets to run",
    "Existing software can't match your process","Staff use multiple tools to complete one task",
    "Important processes depend on individual employees","You need customers or partners to interact with your system",
    "You want to commercialise software as a SaaS product","You need a real operational advantage"],
  connect_eyebrow="Our approach", connect_title="Integration before rebuilding.",
  connect_list=["Existing CRM","ERP / Odoo","Payment gateways","Accounting","WhatsApp","E-commerce","Email","Internal databases"],
  connect_note="We don't rebuild software that already works. Where sensible, we integrate what you have and only develop the components that create real business value.",
  related=[("AI & Business Automation","/ai-automation/"),("CRM & Workflow Automation","/crm-workflow-automation/"),
    ("System Integration & APIs","/system-integration/"),("Cloud & Infrastructure","/cloud-infrastructure/")],
  cta_title="Talk to M3VO about your workflow.",
  cta_text="You don't need a specification. Describe how the work happens today and we'll propose what to build.")

WA_TIERS = [
 ("Starter","From $19 / seat / mo",["Shared WhatsApp inbox","Contact profiles &amp; canned replies","Basic automation rules","No contact / MAC tax"]),
 ("Growth","Everything in Starter, plus",["No-code automation flow builder","AI copilot included","Lightweight CRM / pipeline view"]),
 ("Scale","Everything in Growth, plus",["WhatsApp + Instagram + web","Priority support","Usage-based billing dashboard"]),
]
WA_EXTRA = (
 '<section class="section"><div class="wrap">'
 '<span class="eyebrow">Pricing</span>'
 '<h2 class="measure">Priced per seat. Never per contact.</h2>'
 '<p class="lead measure" style="margin:14px 0 8px;color:var(--body)">Automation and an AI copilot are included from the entry tier — the kind of features other tools gate behind $79+/mo plans. Every Meta/BSP conversation fee is itemised at cost, never marked up. That is the "shows its receipts" part.</p>'
 '<div class="sol-grid" style="margin-top:30px">'
 + "".join(f'<div class="sol"><h3>{t}</h3><p style="font-family:var(--ff-head);font-weight:600;color:var(--green-600);margin:2px 0 14px;font-size:1.05rem">{p}</p>{tick_list(fs)}</div>' for t,p,fs in WA_TIERS)
 + '</div>'
 '<p style="margin-top:18px;color:var(--muted);font-size:.9rem">Tiers reflect the current M3VO plan structure — confirm live pricing and currency before publishing.</p>'
 '</div></section>'
 '<section class="section section--wash"><div class="wrap"><span class="eyebrow">The category, side by side</span>'
 '<h2 class="measure">Everything the $79+/mo tier gives you elsewhere — included from $19.</h2>'
 '<p class="lead measure" style="margin:14px 0 20px;color:var(--body)">Most WhatsApp platforms add a per-contact or monthly-active-conversation charge on top of Meta\'s own fees. M3VO charges per seat and passes Meta/BSP fees through at cost.</p>'
 '<div class="chips">' + "".join(f'<span class="chip">{c}</span>' for c in ["vs Wati","vs respond.io","vs SleekFlow","vs Interakt","vs Trengo"]) + '</div>'
 '</div></section>'
)
WA_LD = [{
 "@context":"https://schema.org","@type":"SoftwareApplication","name":"M3VO",
 "applicationCategory":"BusinessApplication","operatingSystem":"Web, iOS, Android",
 "url":BASE+"/whatsapp-business/","image":BASE+"/assets/og-image.png",
 "description":"Shared WhatsApp inbox and customer communication platform with team assignment, automation, an AI copilot and per-seat pricing. Built on the official WhatsApp Business Platform.",
 "offers":{"@type":"Offer","priceCurrency":"USD","price":"19","description":"From $19 per seat per month. Meta/BSP conversation fees itemised at cost.","url":BASE+"/whatsapp-business/"},
 "provider":{"@type":"Organization","name":"M3VO","url":BASE+"/"}
}]
LEAVES["/whatsapp-business/"] = dict(
  path="/whatsapp-business/", icon="chat", service_type="WhatsApp Business automation",
  title="WhatsApp Business Automation, Shared Inbox & Pricing | M3VO",
  desc="M3VO is a shared WhatsApp inbox with team assignment, automation and an AI copilot — priced per seat from $19/mo, with Meta/BSP fees itemised at cost, not marked up.",
  crumbs=[("Home","/"),("Solutions","/#solutions"),("WhatsApp & Customer Communication",None)],
  h1="The WhatsApp inbox that shows its receipts.",
  lead="A shared WhatsApp and omnichannel inbox for your whole team — with assignment, automation and an AI copilot. Priced per seat, with every Meta/BSP fee itemised at cost rather than marked up.",
  answer_title="What is a WhatsApp shared inbox?",
  answer_paras=["A WhatsApp shared inbox lets a whole team manage customer conversations from one business number — with assignment, internal notes, status, automation and history — instead of messages living on one employee's phone.",
    "M3VO builds this on the official WhatsApp Business Platform via a licensed BSP, and prices it per seat (never per contact), passing Meta's conversation fees through at cost. It suits businesses that have outgrown the standard WhatsApp Business App."],
  chain_eyebrow="The workflow", chain_title="From customer message to completed follow-up",
  chain=[("chat","Enquiry",False),("ai","AI assist",True),("route","Route & assign",False),("users","Reply",False),("cal","Appointment",False),("crm","CRM sync",False),("bell","Follow-up",False)],
  build_eyebrow="What M3VO can support", build_title="A structured way to run business conversations.",
  build_list=["Shared team inbox","Multiple users","Multiple business numbers","Team assignment","Departments and locations",
    "Internal notes","Customer profiles","Conversation status","Automated replies","No-code automation flows","AI copilot",
    "Follow-up automation","CRM / pipeline view","Appointment workflows","Lead qualification"],
  when_eyebrow="Built for", when_title="Businesses that use WhatsApp every day.",
  when_intro="When conversations affect sales, appointments and customer service, they shouldn't depend on one employee's phone.",
  when_list=["Customers message different staff and things get lost","No visibility for managers","Follow-ups depend on memory",
    "You run multiple numbers or locations","You want AI to draft or triage replies","You're tired of a per-contact pricing tax"],
  extra_html=WA_EXTRA, extra_ld=WA_LD,
  related=[("AI & Business Automation","/ai-automation/"),("CRM & Workflow Automation","/crm-workflow-automation/"),
    ("Dental & Aesthetic Clinics","/dental-clinic-software/"),("Distribution & B2B","/industries/distribution/")],
  cta_title="See M3VO in your own workflow.",
  cta_text="Tell us how your team handles WhatsApp today. We'll show you a cleaner way to run it — and exactly what it costs.")

LEAVES["/crm-workflow-automation/"] = dict(
  path="/crm-workflow-automation/", icon="crm", service_type="CRM and workflow automation",
  title="CRM & Workflow Automation for SMEs | M3VO",
  desc="M3VO takes a workflow-first approach to CRM — customer information triggers actions across sales, operations and management, not just a database staff must update.",
  crumbs=[("Home","/"),("Solutions","/#solutions"),("CRM & Workflow Automation",None)],
  h1="Your CRM should move work forward — not just store names.",
  lead="Many CRMs become databases employees are required to update. M3VO takes a workflow-first approach: customer information should trigger actions that connect customers, staff, tasks and business processes.",
  answer_title="What is CRM workflow automation?",
  answer_paras=["CRM workflow automation connects customer records to the actions a business needs to take — assigning leads, scheduling follow-ups, triggering approvals and updating management automatically as work progresses.",
    "The system should support the business process, not simply record what already happened."],
  chain_eyebrow="A new enquiry", chain_title="From lead to management visibility",
  chain=[("route","New lead",False),("target","Source tagged",False),("users","Assign rep",True),("cal","Schedule",False),("bell","Reminder",False),("chart","Management view",False)],
  chain_note="A confirmed customer can then trigger account creation, documents, operations, payment requests and follow-up — automatically.",
  build_eyebrow="CRM capabilities", build_title="Everything tied to the way you actually sell and serve.",
  build_list=["Customer profiles","Sales pipeline","Tasks and reminders","Lead assignment","Automated follow-ups",
    "Management dashboards","Sales reporting","Customer history","Communication integration","Custom workflow stages",
    "Approvals and notifications","API integrations"],
  related=[("WhatsApp & Communication","/whatsapp-business/"),("System Integration & APIs","/system-integration/"),
    ("AI & Business Automation","/ai-automation/"),("Distribution & B2B","/industries/distribution/")],
  cta_title="Make your CRM do the work.",
  cta_text="Describe your sales or service process. We'll map where automation moves it forward on its own.")

LEAVES["/system-integration/"] = dict(
  path="/system-integration/", icon="plug", service_type="API and system integration",
  title="API & Business System Integration Singapore | M3VO",
  desc="M3VO connects the software you already use — CRM, ERP, payments, WhatsApp, e-commerce and accounting — with APIs and automated workflows so information moves on its own.",
  crumbs=[("Home","/"),("Solutions","/#solutions"),("System Integration & APIs",None)],
  h1="Make your software talk to each other.",
  lead="Businesses often already have good software. The problem is that none of it communicates. M3VO develops API integrations and automated workflows so information moves between platforms automatically.",
  answer_title="What is business system integration?",
  answer_paras=["Business system integration connects separate software platforms so data flows between them automatically — removing the manual copying, re-entry and reconciliation that happens when systems work in isolation.",
    "You may not need another platform. You may simply need your existing platforms to communicate."],
  chain_eyebrow="Typical connections", chain_title="Information that moves automatically",
  chain=[("chat","WhatsApp",False),("crm","CRM",True),("doc","Quotation",False),("box","ERP / Order",False),("pay","Payment",False),("chart","Dashboard",False)],
  build_eyebrow="What M3VO can connect", build_title="From messaging to money, joined up.",
  build_list=["CRM systems","ERP systems / Odoo","E-commerce platforms","Payment gateways","WhatsApp","Email",
    "Accounting software","Scheduling systems","Cloud storage","Internal databases","Third-party APIs"],
  connect_eyebrow="Our principle", connect_title="Integration before replacement.",
  connect_list=["WhatsApp → CRM","Website → CRM","CRM → Quotation","Order → ERP","Payment → Accounting","E-commerce → Inventory"],
  connect_note="Whenever practical, we improve what you already have before recommending you replace it.",
  related=[("Custom Software Development","/custom-software-development/"),("CRM & Workflow Automation","/crm-workflow-automation/"),
    ("Cloud & Infrastructure","/cloud-infrastructure/"),("AI & Business Automation","/ai-automation/")],
  cta_title="Connect the software you already use.",
  cta_text="List the systems that don't talk to each other. We'll tell you what can be joined up.")

LEAVES["/cloud-infrastructure/"] = dict(
  path="/cloud-infrastructure/", icon="cloud", service_type="Cloud and business infrastructure",
  title="Cloud & Business Infrastructure Singapore | M3VO",
  desc="M3VO designs cloud-based business environments — hosted applications, remote work access, centralised data and secure user management for growing companies.",
  crumbs=[("Home","/"),("Solutions","/#solutions"),("Cloud & Business Infrastructure",None)],
  h1="Give your team the tools they need, wherever they work.",
  lead="M3VO designs cloud-based business environments for companies that need secure access to applications, business data or specialised software — without the overhead of managing it all in-house.",
  answer_title="What is cloud business infrastructure?",
  answer_paras=["Cloud business infrastructure is the hosted environment — applications, data and access controls — that lets a team use business systems securely from anywhere, without maintaining physical servers.",
    "It's the foundation that keeps applications available, data centralised and access controlled as a business grows."],
  build_eyebrow="What M3VO can provide", build_title="A dependable base for your business systems.",
  build_list=["Cloud applications","Hosted business systems","Remote work environments","Cloud desktops",
    "Centralised data","User access management","Business continuity","Application hosting","Secure remote access"],
  related=[("Custom Software Development","/custom-software-development/"),("System Integration & APIs","/system-integration/"),
    ("CRM & Workflow Automation","/crm-workflow-automation/"),("Multi-location Businesses","/industries/multi-location/")],
  cta_title="Plan your cloud environment.",
  cta_text="Tell us what your team needs to access and from where. We'll design a secure, practical setup.")

# ---- industries
LEAVES["/healthcare-software/"] = dict(
  path="/healthcare-software/", icon="health", service_type="Healthcare and clinic software",
  title="Healthcare & Clinic Software Singapore | M3VO",
  desc="M3VO develops software and automation for clinics — AI reception, WhatsApp enquiries, appointments, reminders, CRM, packages, payments and follow-up workflows.",
  crumbs=[("Home","/"),("Industries","/insights/"),("Healthcare & Clinics",None)],
  h1="Practical technology for modern clinics.",
  lead="M3VO develops software and automation for healthcare businesses where customer communication, appointments, payments and operational workflows need to work together — reducing admin while improving the patient journey.",
  answer_title="What is clinic software?",
  answer_paras=["Clinic software brings a clinic's enquiries, appointments, patient communication, payments and internal operations into connected workflows, rather than spreading them across phones, spreadsheets and separate tools.",
    "Every clinic operates differently, so M3VO designs systems around the processes that matter to the organisation instead of forcing a rigid workflow."],
  chain_eyebrow="The clinic workflow", chain_title="From first enquiry to recall",
  chain=[("chat","Enquiry",False),("ai","AI reception",True),("cal","Appointment",False),("health","Consultation",False),("pay","Payment",False),("bell","Follow-up",False),("refresh","Recall",False)],
  build_eyebrow="Potential applications", build_title="Built around the way clinics actually run.",
  build_list=["AI clinic reception","WhatsApp enquiries","Appointment management","Patient reminders","Treatment enquiries",
    "Customer relationship management","Packages","Payments","Inventory","Follow-up workflows","Recall campaigns","Operational dashboards"],
  related=[("Dental & Aesthetic Clinics","/dental-clinic-software/"),("WhatsApp & Communication","/whatsapp-business/"),
    ("AI & Business Automation","/ai-automation/"),("CRM & Workflow Automation","/crm-workflow-automation/")],
  cta_title="Design your clinic workflow with M3VO.",
  cta_text="Tell us where your front desk and follow-ups get stuck. We'll design around it.")

LEAVES["/dental-clinic-software/"] = dict(
  path="/dental-clinic-software/", icon="tooth", service_type="Dental and aesthetic clinic software",
  title="Dental Clinic Software & WhatsApp Automation | M3VO",
  desc="M3VO connects the full dental and aesthetic clinic workflow — enquiry, consultation, appointment, treatment, payment, follow-up and recall — with AI reception and WhatsApp automation.",
  crumbs=[("Home","/"),("Industries","/insights/"),("Dental & Aesthetic Clinics",None)],
  h1="Manage the complete enquiry-to-recall workflow.",
  lead="M3VO helps dental and aesthetic clinics connect every step from first enquiry to recall — with AI receptionists, WhatsApp automation, CRM workflows, appointment systems and clinic-specific software.",
  answer_title="What is dental clinic software?",
  answer_paras=["Dental and aesthetic clinic software connects patient enquiries, consultations, appointments, treatments, payments and follow-up into one workflow — so nothing depends on which staff member happened to take the message.",
    "M3VO can automate the repetitive parts (reception, reminders, recall) while keeping clinical and commercial decisions with your team."],
  chain_eyebrow="The clinic workflow", chain_title="Enquiry → Consultation → Appointment → Treatment → Payment → Follow-up → Recall",
  chain=[("chat","Enquiry",False),("ai","AI reception",True),("cal","Appointment",False),("tooth","Treatment",False),("pay","Payment",False),("bell","Follow-up",False),("refresh","Recall",False)],
  build_eyebrow="Potential solutions", build_title="Everything a busy clinic front-of-house needs.",
  build_list=["WhatsApp AI receptionist","Appointment handling","Lead qualification","CRM","Treatment follow-up",
    "Patient communication","Packages","Payments","Inventory","Recall marketing"],
  related=[("Healthcare & Clinics","/healthcare-software/"),("WhatsApp & Communication","/whatsapp-business/"),
    ("AI & Business Automation","/ai-automation/"),("CRM & Workflow Automation","/crm-workflow-automation/")],
  cta_title="Build your clinic's enquiry engine.",
  cta_text="Tell us how enquiries and recalls work today. We'll show you the connected version.")

LEAVES["/industries/distribution/"] = dict(
  path="/industries/distribution/", icon="box", service_type="B2B distribution software",
  title="B2B Distribution Software | M3VO",
  desc="M3VO connects the B2B distribution workflow — lead, quotation, order, delivery, invoice, payment and follow-up — replacing scattered email, WhatsApp and spreadsheets.",
  crumbs=[("Home","/"),("Industries","/insights/"),("Distribution & B2B",None)],
  h1="Lead to payment across one connected workflow.",
  lead="B2B distributors often rely on email, WhatsApp, spreadsheets and individual employee knowledge. M3VO connects the whole workflow so orders, quotes and follow-ups stop falling through the cracks.",
  answer_title="What is B2B distribution software?",
  answer_paras=["B2B distribution software connects the steps a distributor runs every day — enquiries, quotations, orders, inventory, delivery, invoicing and payment — into one workflow with proper visibility for sales and management.",
    "It reduces the manual copying and chasing that happens when each step lives in a different tool."],
  chain_eyebrow="The distributor workflow", chain_title="Lead → Quotation → Order → Delivery → Invoice → Payment → Follow-up",
  chain=[("route","Lead",False),("doc","Quotation",False),("box","Order",False),("layers","Inventory",True),("pay","Invoice",False),("bell","Follow-up",False),("users","Account mgmt",False)],
  build_eyebrow="Potential systems", build_title="The operational backbone for a distribution business.",
  build_list=["B2B ordering","Sales CRM","Quotation workflows","Customer portals","Inventory integrations",
    "Sales reporting","Account management","Automated reminders"],
  related=[("CRM & Workflow Automation","/crm-workflow-automation/"),("System Integration & APIs","/system-integration/"),
    ("WhatsApp & Communication","/whatsapp-business/"),("Custom Software Development","/custom-software-development/")],
  cta_title="Connect your distribution workflow.",
  cta_text="Describe how an order moves through your business today. We'll find where it stalls.")

LEAVES["/industries/ecommerce/"] = dict(
  path="/industries/ecommerce/", icon="cart", service_type="E-commerce automation",
  title="E-commerce Automation & Customer Support | M3VO",
  desc="M3VO connects customer conversations with commerce — product questions, orders, delivery updates, payments, returns and AI-powered support.",
  crumbs=[("Home","/"),("Industries","/insights/"),("Retail & E-commerce",None)],
  h1="Connect customer conversations with commerce.",
  lead="Retail and e-commerce businesses win or lose on response and follow-through. M3VO ties conversations to orders, delivery, payments and support so customers aren't left waiting.",
  answer_title="What is e-commerce automation?",
  answer_paras=["E-commerce automation connects the customer-facing conversation to the commerce behind it — orders, delivery updates, payments, returns and support — so routine questions and follow-ups are handled without manual effort.",
    "AI can take the repetitive product and order questions while your team handles the exceptions."],
  chain_eyebrow="The commerce workflow", chain_title="Question → Order → Delivery → Payment → Returns → Follow-up",
  chain=[("chat","Product Q",False),("ai","AI support",True),("cart","Order",False),("box","Delivery",False),("pay","Payment",False),("refresh","Returns",False),("bell","Follow-up",False)],
  build_eyebrow="What M3VO can manage", build_title="Every touchpoint, connected.",
  build_list=["Product questions","Orders","Delivery updates","Payments","Returns","Customer service","Promotions",
    "Follow-ups","AI-powered customer support"],
  related=[("WhatsApp & Communication","/whatsapp-business/"),("System Integration & APIs","/system-integration/"),
    ("AI & Business Automation","/ai-automation/"),("CRM & Workflow Automation","/crm-workflow-automation/")],
  cta_title="Automate the routine, keep the personal.",
  cta_text="Tell us which customer questions eat your team's day. We'll take them off the queue.")

LEAVES["/industries/professional-services/"] = dict(
  path="/industries/professional-services/", icon="brief", service_type="Professional services automation",
  title="Software for Professional Services | M3VO",
  desc="M3VO turns enquiries, documents and client requests into structured workflows — lead management, document collection, onboarding, quotations, scheduling and reminders.",
  crumbs=[("Home","/"),("Industries","/insights/"),("Professional Services",None)],
  h1="Turn enquiries and documents into structured workflows.",
  lead="Professional services firms run on enquiries, documents and client requests. M3VO structures those into clear workflows so onboarding, follow-ups and scheduling run consistently.",
  answer_title="How can professional services firms use automation?",
  answer_paras=["Professional services automation structures the flow of enquiries, documents, onboarding and scheduling — so client work starts cleanly and nothing depends on one person remembering the next step.",
    "It's especially useful where every engagement needs the same information collected and the same steps followed."],
  chain_eyebrow="The client workflow", chain_title="Enquiry → Qualify → Documents → Onboarding → Quotation → Scheduling → Reminders",
  chain=[("chat","Enquiry",False),("ai","Qualify",True),("doc","Documents",False),("users","Onboarding",False),("pay","Quotation",False),("cal","Scheduling",False),("bell","Reminders",False)],
  build_eyebrow="Applications", build_title="Consistent delivery, every engagement.",
  build_list=["Lead management","Document collection","Client onboarding","Quotations","Appointment scheduling",
    "Automated reminders","Customer communication"],
  related=[("CRM & Workflow Automation","/crm-workflow-automation/"),("AI & Business Automation","/ai-automation/"),
    ("Custom Software Development","/custom-software-development/"),("System Integration & APIs","/system-integration/")],
  cta_title="Standardise how client work begins.",
  cta_text="Describe your intake and onboarding. We'll turn it into a workflow that runs itself.")

LEAVES["/industries/multi-location/"] = dict(
  path="/industries/multi-location/", icon="buildings", service_type="Multi-location business software",
  title="Software for Multi-location Businesses | M3VO",
  desc="M3VO centralises operations while letting each branch or team manage its own customers — with visibility across locations, departments, sales and management.",
  crumbs=[("Home","/"),("Industries","/insights/"),("Multi-location Businesses",None)],
  h1="Central visibility, local control.",
  lead="M3VO centralises operations while allowing each branch or team to manage its own customers — giving management a clear view across the whole business without slowing branches down.",
  answer_title="How does software help multi-location businesses?",
  answer_paras=["Software for multi-location businesses gives each branch the tools to run its own customers and operations, while rolling data up into one central view for management — so autonomy and oversight coexist.",
    "It removes the reporting scramble that happens when every location keeps its own records."],
  chain_eyebrow="The workflow", chain_title="Branch → Local team → Central CRM → Reporting → Management view",
  chain=[("buildings","Branch enquiry",False),("users","Local team",False),("crm","Central CRM",True),("chart","Reporting",False),("target","Management view",False)],
  build_eyebrow="Visibility across", build_title="One picture of the whole business.",
  build_list=["Locations","Departments","Sales teams","Customer service","Management"],
  related=[("CRM & Workflow Automation","/crm-workflow-automation/"),("Cloud & Infrastructure","/cloud-infrastructure/"),
    ("System Integration & APIs","/system-integration/"),("Distribution & B2B","/industries/distribution/")],
  cta_title="Bring your locations onto one view.",
  cta_text="Tell us how your branches report today. We'll design the central picture.")

# ---------------------------------------------------------------- how we work
def how_we_work():
    steps = [("Discovery","We start by understanding what happens today — the people involved, systems in use, decisions being made and information moving through the business."),
      ("Workflow mapping","We map the process and identify friction, duplication and unnecessary manual tasks."),
      ("Solution design","We decide whether the answer is automation, integration, configuration, AI, custom software — or a combination."),
      ("Prototype","Where useful, we build a working prototype so the workflow can be tested early."),
      ("Development","Once the process is validated, we develop the production system."),
      ("Integration","We connect the relevant external systems and data."),
      ("Deployment","The solution is introduced with the right access, configuration and workflow."),
      ("Continuous improvement","Real usage tells us things no spec ever could. We keep improving from there.")]
    rows="".join(f'<div class="pstep"><div class="pn">{str(k+1).zfill(2)}</div><h3>{t}</h3><p>{d}</p></div>' for k,(t,d) in enumerate(steps))
    body = f'''<section class="section section--tight" style="padding-top:26px">{crumbs([("Home","/"),("How We Work",None)])}
      <div class="wrap" style="margin-top:8px"><span class="eyebrow">How we work</span>
      <h1 style="max-width:20ch">How M3VO builds software.</h1>
      <p class="lead measure" style="margin-top:18px;color:var(--body)">We don't start with features. We start with your workflow — then simplify before we build.</p></div></section>
      <section class="section" style="padding-top:0"><div class="wrap"><div class="proc" style="grid-template-columns:repeat(4,1fr)">{rows}</div></div></section>
      {answer_section("Why simplify before building?", ["There is little value in automating a bad process. We improve the workflow first, so the software you get is solving the right problem — not encoding the old one faster."])}
      {cta_band("Start with the problem.","You don't need a specification. Tell us what's slow, broken or manual, and we'll take it from discovery.")}'''
    return page("How M3VO Builds Software | Our Process","M3VO's process: discovery, workflow mapping, solution design, prototype, development, integration, deployment and continuous improvement.",
        "/how-we-work/", body, [breadcrumb_ld([("Home","/"),("How We Work","/how-we-work/")])])

def answer_section(title, paras):
    return f'<section class="section section--wash"><div class="wrap">{answer(title, paras)}</div></section>'

# ---------------------------------------------------------------- about
def about():
    body = f'''<section class="section section--tight" style="padding-top:26px">{crumbs([("Home","/"),("About",None)])}
      <div class="wrap" style="margin-top:8px"><span class="eyebrow">About M3VO</span>
      <h1 style="max-width:22ch">Software built from a business owner's perspective.</h1>
      <p class="lead measure" style="margin-top:18px;color:var(--body)">M3VO was created with a simple belief: business software should make running a business easier. Yet many companies experience the opposite — they accumulate software, maintain spreadsheets between the gaps, and information becomes harder rather than easier to find.</p></div></section>
      <section class="section" style="padding-top:0"><div class="wrap"><div class="frow" style="border:0;padding:0">
        <div><h2>Built by entrepreneurs, for entrepreneurs.</h2>
          <p style="margin-top:16px;color:var(--body)">We understand that small and growing businesses can't spend years implementing enterprise systems. Technology needs to deliver practical value, be understandable, work with the team, and solve a real problem. That philosophy shapes everything we build.</p></div>
        <div class="fr-media">{tick_list(["Understand the business","Identify the friction","Simplify the process","Build what is needed","Connect what already works","Keep improving"])}</div>
      </div></div></section>
      {answer_section("Where did M3VO start?", ["M3VO started as a shared WhatsApp inbox — bringing scattered conversations into one team workspace with clear, honest pricing. That is still a core product. But the inbox is where we started, not where the problem ends: the same friction shows up across CRM, operations and reporting, which is why M3VO now spans software, automation, AI and integration.","Built by Mevo Tech."])}
      {answer_section("Where is M3VO based?", ["M3VO is based in Singapore and develops software for businesses operating locally and across international markets.","We're particularly suited to growing businesses across Singapore and Southeast Asia that need flexible systems capable of adapting to different teams, markets and workflows."])}
      {cta_band("Let's make your business easier to run.","Tell us what slows you down. We'll help decide whether it should be simplified, automated, connected or rebuilt.")}'''
    ld=[breadcrumb_ld([("Home","/"),("About","/about/")]),
        {"@context":"https://schema.org","@type":"AboutPage","name":"About M3VO","url":BASE+"/about/","description":ENTITY_LONG}]
    return page("About M3VO | Practical Software Built for Business","M3VO is a Singapore software company building practical AI, automation and custom software for growing businesses — built by entrepreneurs, for entrepreneurs.",
        "/about/", body, ld)

# ---------------------------------------------------------------- insights / resources
def insights():
    clusters = [
      ("AI for SMEs","ai",["How can SMEs use AI without replacing their existing systems?","Where should a small business start with AI automation?",
        "AI receptionist vs chatbot: what's the difference?","How much does custom AI software cost in Singapore?","When should a business build its own AI application?"]),
      ("Custom Software","code",["Custom software vs SaaS: which is better for an SME?","How much does custom software cost in Singapore?",
        "When should a company replace spreadsheets with software?","Should you build or buy a CRM?","What does it cost to build a SaaS platform?"]),
      ("WhatsApp Business","chat",["WhatsApp Business App vs WhatsApp Business Platform","Can multiple employees use one WhatsApp business number?",
        "How does a WhatsApp shared inbox work?","WhatsApp Business API pricing explained","How to build a WhatsApp AI receptionist"]),
      ("Business Automation","flow",["10 business processes SMEs should automate first","How to automate quotations and follow-ups",
        "How CRM workflow automation works","How to connect WhatsApp to an ERP","How APIs connect business software"]),
      ("Healthcare Technology","health",["How an AI receptionist works for a clinic","WhatsApp automation for dental clinics",
        "CRM systems for aesthetic clinics","Building an appointment and follow-up workflow","Clinic software vs general CRM software"]),
    ]
    cards=""
    for t,i,qs in clusters:
        lis="".join(f'<li>{q}</li>' for q in qs)
        cards+=f'''<div class="sol"><span class="sic">{ic(i)}</span><h3>{t}</h3>
          <ul class="reduce-list" style="columns:1;margin-top:6px">{lis}</ul></div>'''
    body=f'''<section class="section section--tight" style="padding-top:26px">{crumbs([("Home","/"),("Resources",None)])}
      <div class="wrap" style="margin-top:8px"><span class="eyebrow">Resources</span>
      <h1 style="max-width:24ch">Practical ideas for running a better business with software.</h1>
      <p class="lead measure" style="margin-top:18px;color:var(--body)">Not a generic tech blog. These are the real questions business owners ask — answered clearly. Content is rolling out across these clusters.</p></div></section>
      <section class="section" style="padding-top:0"><div class="wrap"><div class="sol-grid">{cards}</div></div></section>
      {cta_band("Have a question we haven't covered?","Ask it directly — describe your situation and we'll give you a straight answer.")}'''
    return page("Resources & Insights | M3VO","Practical guides on AI for SMEs, custom software, WhatsApp Business, business automation and healthcare technology from M3VO.",
        "/insights/", body, [breadcrumb_ld([("Home","/"),("Resources","/insights/")])])

# ---------------------------------------------------------------- contact
def contact():
    prompts="".join(f'<div class="prompt">{p}</div>' for p in [
      '<b>"My employees spend hours preparing reports."</b>',
      '<b>"Customers message different staff on WhatsApp."</b>',
      '<b>"Our CRM doesn\'t connect to our ERP."</b>',
      '<b>"We\'re managing everything through spreadsheets."</b>',
      '<b>"I want to automate our appointment enquiries."</b>',
      '<b>"I have an idea for a SaaS product."</b>'])
    form=f'''<form id="m3vo-contact" method="post" action="/api/contact" novalidate>
      <div class="hp" aria-hidden="true"><label>Leave this field empty<input type="text" name="company_website" tabindex="-1" autocomplete="off"></label></div>
      <div class="form-grid">
        <div class="field"><label for="f-name">Name</label><input id="f-name" name="name" type="text" autocomplete="name" required></div>
        <div class="field"><label for="f-company">Company</label><input id="f-company" name="company" type="text" autocomplete="organization"></div>
        <div class="field"><label for="f-email">Email</label><input id="f-email" name="email" type="email" autocomplete="email" required></div>
        <div class="field"><label for="f-phone">Phone / WhatsApp</label><input id="f-phone" name="phone" type="tel" autocomplete="tel"></div>
        <div class="field"><label for="f-country">Country</label>
          <select id="f-country" name="country"><option>Singapore</option><option>Malaysia</option><option>Thailand</option><option>Hong Kong</option><option>Other</option></select></div>
        <div class="field"><label for="f-systems">Existing systems in use</label><input id="f-systems" name="systems" type="text" placeholder="e.g. WhatsApp, Odoo, Excel"></div>
        <div class="field full"><label for="f-improve">What would you like to improve?</label><textarea id="f-improve" name="improve" placeholder="Describe what takes too long, keeps going wrong, or you wish just worked." required></textarea></div>
      </div>
      <div class="btn-row" style="margin-top:20px"><button class="btn btn-primary" type="submit">Discuss My Workflow</button></div>
      <div class="form-err" id="form-err" role="alert"></div>
      <p style="margin-top:12px;color:var(--muted);font-size:.86rem">You don't need to prepare a software specification. Just tell us what's happening.</p>
    </form>
    <div class="form-ok" id="form-ok"><div class="ok-ic">{ic('check')}</div>
      <h3>Thanks — we've got it.</h3><p style="margin-top:8px;color:var(--body)">We'll review your workflow and come back with whether it should be simplified, automated, connected or rebuilt.</p></div>'''
    body=f'''<section class="section section--tight" style="padding-top:26px">{crumbs([("Home","/"),("Contact",None)])}</section>
      <section class="section" style="padding-top:0"><div class="wrap"><div class="frow" style="border:0;padding:0;align-items:start">
        <div><span class="eyebrow">Contact</span>
          <h1 style="max-width:16ch">What is slowing your business down?</h1>
          <p class="lead" style="margin-top:16px;color:var(--body)">You don't need to prepare a software specification. Tell us what's happening — that's enough to start.</p>
          <a class="contact-email" href="mailto:hello@m3vo.com"><span class="ce-ic">{ic('mail')}</span><span><span class="ce-l">Email us directly</span><span class="ce-v">hello@m3vo.com</span></span></a>
          <div class="prompts">{prompts}</div></div>
        <div class="fr-media"><div class="panel" style="padding:26px">{form}</div></div>
      </div></div></section>'''
    ld=[breadcrumb_ld([("Home","/"),("Contact","/contact/")]),
        {"@context":"https://schema.org","@type":"ContactPage","name":"Contact M3VO","url":BASE+"/contact/"}]
    return page("Contact M3VO | Software Consultation Singapore","Tell M3VO what slows your business down. Describe the problem — no software specification needed — and we'll recommend a practical solution.",
        "/contact/", body, ld)

# ---------------------------------------------------------------- 404
def notfound():
    body=f'''<section class="section" style="text-align:center;padding:120px 0"><div class="wrap">
      <h1>Page not found</h1><p class="lead" style="margin:16px auto 26px;max-width:40ch;color:var(--body)">That page doesn't exist — but tell us what you were looking for and we'll point you the right way.</p>
      <div class="btn-row" style="justify-content:center"><a class="btn btn-primary" href="/">Back to home</a><a class="btn btn-ghost" href="/contact/">Contact</a></div></div></section>'''
    return page("Page not found | M3VO","The page you're looking for doesn't exist.","/404.html", body, [])

# ================================================================ build
def write(path_rel, content):
    full=os.path.join(DIST, path_rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full,"w",encoding="utf-8").write(content)

def build():
    if os.path.exists(DIST): shutil.rmtree(DIST)
    os.makedirs(DIST)
    # assets
    os.makedirs(os.path.join(DIST,"assets"), exist_ok=True)
    open(os.path.join(DIST,"assets","styles.css"),"w",encoding="utf-8").write(CSS)
    open(os.path.join(DIST,"assets","app.js"),"w",encoding="utf-8").write(JS)
    shutil.copy(os.path.join(ROOT,"m3vo-logo.png"), os.path.join(DIST,"assets","m3vo-logo.png"))
    shutil.copy(os.path.join(ROOT,"og-image.png"), os.path.join(DIST,"assets","og-image.png"))
    # pages
    write("index.html", home())
    for path,cfg in LEAVES.items():
        cfg["title"]=cfg["title"]; cfg["desc"]=cfg["desc"]
        write(path.strip("/")+"/index.html", leaf(cfg))
    write("how-we-work/index.html", how_we_work())
    write("about/index.html", about())
    write("insights/index.html", insights())
    write("contact/index.html", contact())
    write("404.html", notfound())
    # sitemap + robots
    urls=["/","/ai-automation/","/custom-software-development/","/whatsapp-business/","/crm-workflow-automation/",
      "/system-integration/","/cloud-infrastructure/","/healthcare-software/","/dental-clinic-software/",
      "/industries/distribution/","/industries/ecommerce/","/industries/professional-services/","/industries/multi-location/",
      "/how-we-work/","/about/","/insights/","/contact/"]
    sm='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls: sm+=f'  <url><loc>{BASE}{u}</loc></url>\n'
    sm+='</urlset>\n'
    write("sitemap.xml", sm)
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    # Cloudflare Pages Function for the contact form
    write("functions/api/contact.js", CONTACT_FN)
    # standalone preview (inlined homepage) — HOME_BODY/HOME_LD were set when home() ran above
    write("preview-standalone.html", page(HOME_TITLE, HOME_DESC, "/", HOME_BODY, HOME_LD, inline=True))
    return urls

if __name__=="__main__":
    urls = build()
    print("Built pages ->", DIST)
    for root,_,files in os.walk(DIST):
        for f in sorted(files):
            print("  ", os.path.relpath(os.path.join(root,f), DIST))
