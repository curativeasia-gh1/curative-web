# M3VO — website

Static, multi-page site for **m3vo.com**. Repositions M3VO from "WhatsApp inbox only" to a
Singapore-based **AI software, automation & custom software** company — while keeping the WhatsApp
inbox as the flagship product (with its real per-seat, fees-itemised pricing story intact).
Brand line: *Software that makes business flow better.*

Real, separate HTML pages (one folder per URL) — deliberate, and important for the SEO/AEO/GEO
goals. Not a single-page app.

> **Heads-up:** the repo's `main` currently holds the *old* single-page site
> ("The WhatsApp inbox that shows its receipts"). This build **replaces** it. See
> "Replace the old site" below. The old site's real facts were carried forward:
> `hello@m3vo.com`, the OG image (`/assets/og-image.png`), and the per-seat/$19 pricing story
> now live on `/whatsapp-business/`.

## Deploy (Cloudflare Pages — zero config)
Repo root **is** the site. In your Pages project:
- **Build command:** *(empty)*
- **Build output directory:** `/` (root)

## Replace the old site on `main`
The old site and this one don't share filenames cleanly (old `styles.css`/`about.html` at root vs
new `assets/...` and `about/`), so do a clean replace rather than copy-over:
```bash
git clone https://github.com/curativeasia-gh1/m3vo-web.git
cd m3vo-web
git rm -r --quiet .                       # clears old tracked files (keeps .git)
cp -r /path/to/this/m3vo-web/. .          # drop this build in (note the trailing /. )
git add -A
git commit -m "Redesign: multi-page site + broadened positioning; keep WhatsApp product & pricing"
git push origin main
```
(Prefer a review step? `git checkout -b redesign` before commit, then open a PR.)

## Structure
```
index.html                     Home
ai-automation/                 Solution pages ...
custom-software-development/
whatsapp-business/             <- flagship: shared inbox + per-seat pricing + comparison
crm-workflow-automation/
system-integration/
cloud-infrastructure/
healthcare-software/           Industry pages ...
dental-clinic-software/
industries/distribution/  industries/ecommerce/
industries/professional-services/  industries/multi-location/
how-we-work/  about/  insights/  contact/
404.html  sitemap.xml  robots.txt
assets/                        styles.css, app.js, m3vo-logo.png, og-image.png
_generator/                    source to regenerate (build.py + css/js/logo/og-image)
```

## Regenerate
```bash
cd _generator && python3 build.py     # writes ./dist ; copy dist/* to repo root to publish
```

## What's built in
- Per-page title, meta description, canonical, Open Graph + Twitter (real OG image wired)
- JSON-LD: Organization (+ real email, alternateName Mevo Tech) + WebSite + FAQPage (home);
  Service + BreadcrumbList (solution/industry); SoftwareApplication with an Offer on the
  WhatsApp page; AboutPage / ContactPage where relevant
- AEO "answer" block on every page; internal linking across solutions <-> industries
- Light + dark mode, mobile nav, reduced-motion respected; sitemap.xml + robots.txt

## Contact form — now wired (Cloudflare Pages Function)
The form POSTs to `/api/contact`, handled by `functions/api/contact.js` (Pages auto-detects the
`functions/` folder — no build step). It validates input, has a bot honeypot, and delivers via
**Resend** email and/or a **webhook**. Set at least one in Pages -> Settings -> Environment variables:

| Variable | Purpose |
|---|---|
| `CONTACT_TO` | recipient (defaults to `hello@m3vo.com`) |
| `RESEND_API_KEY` | secret; enables email via resend.com |
| `CONTACT_FROM` | verified Resend sender, e.g. `M3VO Website <noreply@m3vo.com>` |
| `CONTACT_WEBHOOK_URL` | optional; also POSTs the enquiry JSON here (Slack / HubSpot / Airtable / your wa-api worker) |

With none set, the form returns a friendly "email us" error (503) — so it never silently drops a lead.
The submitter's address is set as `reply_to`, so you can reply straight from the notification.

**Test locally:** `npx wrangler pages dev .` then open the contact page and submit.

## Before you go live — confirm
1. Set the contact env vars above (Resend key and/or a webhook), and verify your Resend sender domain.
2. Confirm WhatsApp pricing. Tiers (Starter/Growth/Scale) and "from $19/seat/mo" are carried from
   your current site. The SoftwareApplication offer uses price 19 / priceCurrency USD — check the
   currency (USD vs SGD) and exact numbers in _generator/build.py (WA_LD, WA_TIERS).
3. Add socials + phone. I did not invent sameAs URLs or a phone number. Add real
   LinkedIn/Facebook/Instagram and phone to the Organization JSON-LD in home().
4. Per-page OG images (optional) — all pages currently share /assets/og-image.png.

## Next
- Wire the contact form (Pages Function).
- Fill /insights/ with real articles (the question lists are the content roadmap).
- Add Cloudflare Web Analytics for traffic data.
