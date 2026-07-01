/**
 * Cloudflare Pages Function: /api/callback
 *
 * Receives the GitHub OAuth code, exchanges it for an access token,
 * and posts the result back to the Decap CMS admin window.
 *
 * This follows the Decap CMS external OAuth provider protocol:
 * https://decapcms.org/docs/external-oauth-clients/
 */

export async function onRequestGet(context) {
  const { GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET } = context.env;
  const url = new URL(context.request.url);
  const code = url.searchParams.get('code');
  const errorParam = url.searchParams.get('error');
  const errorDesc = url.searchParams.get('error_description');

  if (errorParam) {
    return renderPage(false, null, errorDesc || errorParam);
  }

  if (!code) {
    return renderPage(false, null, 'No authorisation code received from GitHub.');
  }

  try {
    const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: GITHUB_CLIENT_ID,
        client_secret: GITHUB_CLIENT_SECRET,
        code,
      }),
    });

    const tokenData = await tokenRes.json();

    if (tokenData.error || !tokenData.access_token) {
      return renderPage(false, null, tokenData.error_description || 'GitHub did not return an access token.');
    }

    return renderPage(true, tokenData.access_token, null);

  } catch (err) {
    return renderPage(false, null, err.message || 'An unexpected error occurred during authentication.');
  }
}

function renderPage(success, token, errorMessage) {
  const provider = 'github';

  let payload;
  let messageType;

  if (success) {
    payload = JSON.stringify({ token, provider });
    messageType = 'success';
  } else {
    payload = JSON.stringify({ error: errorMessage });
    messageType = 'error';
  }

  // Double-encode payload so it can be safely embedded in a JS string literal
  const safePayload = JSON.stringify(payload);

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>${success ? 'Authenticating…' : 'Authentication Error'}</title>
  <style>
    body { font-family: -apple-system, sans-serif; display: flex; align-items: center;
           justify-content: center; height: 100vh; margin: 0; color: #374151; }
    p { font-size: 15px; }
  </style>
</head>
<body>
  <p>${success ? 'Authenticating with GitHub, please wait…' : 'Authentication failed. Close this window and try again.'}</p>
  <script>
  (function () {
    var payload = ${safePayload};
    var message = 'authorization:${provider}:${messageType}:' + payload;
    function onMessage(e) {
      window.opener.postMessage(message, e.origin);
    }
    window.addEventListener('message', onMessage, false);
    window.opener.postMessage('authorizing:${provider}', '*');
  })();
  </script>
</body>
</html>`;

  return new Response(html, {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  });
}
