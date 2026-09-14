// functions/api/contact.js — Cloudflare Pages Function for the M3VO contact form.
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
