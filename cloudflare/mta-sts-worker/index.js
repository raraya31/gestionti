/**
 * MTA-STS policy for gestionti.info.
 * Served only at https://mta-sts.gestionti.info/.well-known/mta-sts.txt
 *
 * The body is intentional. Do not reformat it: receivers compare the
 * policy text, and mode stays "testing" until the owner promotes it.
 */
const POLICY =
  "version: STSv1\n" +
  "mode: testing\n" +
  "mx: gestionti-info.mail.protection.outlook.com\n" +
  "max_age: 86400\n";

const POLICY_PATH = "/.well-known/mta-sts.txt";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === POLICY_PATH) {
      return new Response(POLICY, {
        status: 200,
        headers: {
          "content-type": "text/plain; charset=utf-8",
        },
      });
    }
    return new Response("Not found\n", {
      status: 404,
      headers: {
        "content-type": "text/plain; charset=utf-8",
      },
    });
  },
};
