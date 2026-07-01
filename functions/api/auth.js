/**
 * Cloudflare Pages Function: /api/auth
 *
 * Redirects the CMS admin to GitHub's OAuth authorisation page.
 * Requires environment variables set in Cloudflare Pages → Settings → Variables:
 *   GITHUB_CLIENT_ID     — from your GitHub OAuth App
 *   GITHUB_CLIENT_SECRET — from your GitHub OAuth App (keep secret)
 *
 * GitHub OAuth App callback URL must be set to:
 *   https://curative.asia/api/callback
 */

export async function onRequestGet(context) {
  const { GITHUB_CLIENT_ID } = context.env;

  if (!GITHUB_CLIENT_ID) {
    return new Response(
      'CMS is not configured. Set GITHUB_CLIENT_ID in Cloudflare Pages environment variables.',
      { status: 500, headers: { 'Content-Type': 'text/plain' } }
    );
  }

  const origin = new URL(context.request.url).origin;
  const redirectUri = `${origin}/api/callback`;

  const authUrl = new URL('https://github.com/login/oauth/authorize');
  authUrl.searchParams.set('client_id', GITHUB_CLIENT_ID);
  authUrl.searchParams.set('redirect_uri', redirectUri);
  authUrl.searchParams.set('scope', 'repo');

  return Response.redirect(authUrl.toString(), 302);
}
