// Two responsibilities, both handled at the edge via Cloudflare Pages
// Functions since this site has no build step / shared template file:
//
// 1. Redirect www.curative.asia -> curative.asia (301, path + query preserved).
//    curative.asia (apex) is the canonical host everywhere - sitemap.xml,
//    every canonical tag, robots.txt, and all internal links assume it.
//    This must run FIRST and short-circuit before anything else, so a
//    request to the wrong host never reaches page content at all.
//
// 2. Inject the Klaviyo onsite tracking snippet before </body> on every
//    HTML page served by this site. Single source of truth - do not paste
//    this snippet into individual HTML files, edit it here instead.

const KLAVIYO_SNIPPET = `
<script async type='text/javascript' src='https://static.klaviyo.com/onsite/js/U4G4mP/klaviyo.js?company_id=U4G4mP'></script>
<script type="text/javascript">
//Initialize Klaviyo object on page load
!function(){if(!window.klaviyo){window._klOnsite=window._klOnsite||[];try{window.klaviyo=new Proxy({},{get:function(n,i){return"push"===i?function(){var n;(n=window._klOnsite).push.apply(n,arguments)}:function(){for(var n=arguments.length,o=new Array(n),w=0;w<n;w++)o[w]=arguments[w];var t="function"==typeof o[o.length-1]?o.pop():void 0,e=new Promise((function(n){window._klOnsite.push([i].concat(o,[function(i){t&&t(i),n(i)}]))}));return e}}})}catch(n){window.klaviyo=window.klaviyo||[],window.klaviyo.push=function(){var n;(n=window._klOnsite).push.apply(n,arguments)}}}}();
</script>
`;

class BodyEndInjector {
  element(element) {
    // Inserts raw HTML immediately before the element's closing tag,
    // i.e. right before </body>.
    element.append(KLAVIYO_SNIPPET, { html: true });
  }
}

export async function onRequest(context) {
  const url = new URL(context.request.url);

  if (url.hostname === "www.curative.asia") {
    url.hostname = "curative.asia";
    return Response.redirect(url.toString(), 301);
  }

  const response = await context.next();

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("text/html")) {
    return response;
  }

  return new HTMLRewriter().on("body", new BodyEndInjector()).transform(response);
}
