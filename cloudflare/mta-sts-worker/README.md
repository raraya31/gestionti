# MTA-STS worker (gestionti.info)

Small Cloudflare Worker that serves the MTA-STS policy for `gestionti.info`. It is not part of the public site. GitHub Pages ignores this folder (see the root `_config.yml`).

The policy is in **testing** mode. Mail servers that support MTA-STS will fetch it and report failures, but they will not reject mail that fails the policy.

```
version: STSv1
mode: testing
mx: gestionti-info.mail.protection.outlook.com
max_age: 86400
```

That host is the current Microsoft 365 MX for `gestionti.info`. Each line ends with a single `\n`.

## Deploy from the Cloudflare dashboard

No Wrangler and no CLI. `wrangler.toml` is only a template for later, and it has no account id and no secrets.

1. Open the [Cloudflare dashboard](https://dash.cloudflare.com) and select the **gestionti.info** zone.
2. Go to **Workers & Pages** → **Create** → **Workers** → **Create Worker** (or **Start with Hello World**). Name it `gestionti-mta-sts`.
3. In the code editor, replace the sample with the full contents of `index.js` from this folder. The editor should already be in the module format (`export default { async fetch... }`). Deploy / Save.
4. Open the worker → **Settings** → **Domains & Routes** → **Add**:
   - **Custom domain:** `mta-sts.gestionti.info`, or
   - **Route:** `mta-sts.gestionti.info/*` on the zone `gestionti.info`.
5. Check DNS for that host. In the zone’s **DNS** tab, `mta-sts` must exist and be **proxied** (orange cloud). A custom domain creates or updates that record for you. A route does not: if the record is missing, add an `A` record for `mta-sts` pointing at `192.0.2.1` (Cloudflare ignores the address while proxied) and turn the proxy on. A grey-cloud (DNS only) record never runs the Worker. As of this change, `mta-sts.gestionti.info` already resolves to Cloudflare and answers **HTTP 525**, which means the proxy is on but nothing healthy is attached yet. Attaching this worker is what replaces that error.
6. Leave the existing TXT record `_mta-sts.gestionti.info` (`v=STSv1; id=1688221506`) as it is for this first testing publish. The next time the policy text changes, update that `id` to a new value so receivers fetch the new file. This worker does not publish DNS.

## Test

```bash
curl -sS -D- https://mta-sts.gestionti.info/.well-known/mta-sts.txt
```

Expect `HTTP/2 200` and `content-type: text/plain; charset=utf-8`, then exactly the four policy lines above.

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://mta-sts.gestionti.info/
```

Expect `404`. Any path other than `GET /.well-known/mta-sts.txt` is a 404.
