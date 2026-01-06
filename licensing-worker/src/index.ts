// Prism Licensing Worker
// Cloudflare Workers script for managing license keys
// 
// Endpoints:
// - GET  /validate?key=XXXX     - Validate a license key
// - POST /admin/create          - Create a new license (requires API_SECRET)
// - POST /admin/revoke          - Revoke a license (requires API_SECRET)
// - GET  /admin/list            - List all licenses (requires API_SECRET)

interface Env {
    LICENSES: KVNamespace;
    API_SECRET: string;
}

interface License {
    tier: 'free' | 'pro' | 'enterprise';
    email: string;
    created_at: string;
    expires_at: string;
    revoked: boolean;
    machine_ids?: string[];
    metadata?: Record<string, string>;
}

interface CreateLicenseRequest {
    email: string;
    tier: 'pro' | 'enterprise';
    months: number;
    metadata?: Record<string, string>;
}

// CORS headers for cross-origin requests
const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

// --- CRYPTO SIGNING ---
// Private Key for signing licenses (Generated offline)
const PRIVATE_KEY_PEM = `
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDgIT2d5n5+6h0p
njnvQ/UgaNOlgE3i1UHE5uaQJiO7up9tn+i9Y1HNsh45cn9gw1SVruJFTlGoaFgo
9Oaoy4uPIPyibx/3DoV9Fvg4j3z9+bZOC//aUQe8poVRQBPlqHolrgs6Ccq05XCM
n/gSMocCOl6AE4MXVNdOHKARiRvsqvwISf/A0VhO0/kPdUT/VtFd0SmayN7GUEmq
8rpHnC1QDNjWL+E+qa2/HUt/YcEnRuTqZmKxzzYSQaniRWLXf4WrAJaJ4PiNTeB7
fK3L01QCByIjRuun9KVNUQMn+gwQax5nc3uAQn5EHcaTIrUprMML/T2SeqfN4sXo
SSKOHGOXAgMBAAECggEAArbGZOjsebg9f+dJlgwmpeJeCdmNE8LD9vPePcNiRecf
zqO7CM9Hny0FAkllUxRHVWEPXEwxOiqpjRQe/88G6GbxLV34FFBTgg8hsX7uJUcY
MrbWjDCB5rwHqS3rKpl/kexEV4Czj5O4UE2tZRk1iFcE7C6/yYbUJstgVC3Fp8qm
5SEpMBUDKq6OOPVKz8B/80ea6gOCbDNpPYp0U1js9+dCQ4/Wor/cbjeRZRVuLjdW
3JlhYe4bjswD/+zyVNWd9zXh8BNrvp6Klwifq0CD5MWM/eZbvjPisCzN87+FObqu
F1skUNIkvlh1pNZeIw6/ISkUXD1FGWJg166qVOmVyQKBgQD3NgG1sWnHyP1CDwdW
fGQ2jm4FLbXTWdbyI5gqMjOS1AZxepl9bU5B49SfHIIjNfUeVK2KLeL1QMKBnh/r
a9LpbU1yi5plCUXQBHoc0CT55g8ChQ1iAzTQSH8WFbXy11vch1lB6Gdk+0ziy2Jd
mAAZZQ0bwbPVzi2gY0buD6OpvQKBgQDoGSk1QLzVv8FB1Hl+icnAumgFzI8psd+t
vOCFkzMTp/AvUQCvzPjT/GAuWH4Zfly9SpBnOmw0f0KA30Qs2TGvcZ9/hItLIOTo
Ue05yf67zXp+jZZBsRtTjDNGip2xZ3WmDbMU7Hxt8lafKRNevKXD+m5wieqCDnHW
9x/WSef14wKBgD08aYwCWHues+1rH5wyz/gbq/Eoc4PZGz97xbOeH9xdHQN7JQ5G
xz3XG9IWE755HTDYNOynlTK/Se8lpi6A1QvxgV/AaQxiEaMHmOAORzqH3Gv5XWlL
9gcqDiEAW8O9yQmFlXyX/xSqk08Splkcz9l6iJa5kryBiBfUv7s0sIvZAoGAfTr+
OgaJHQfO3ZcoSrdLzZqGgAKEiGm6F8MendPzrjph5RXeufxtkevNdZQ3zceZgGUY
Dyq9sYGsv144Kb6zCUfUWHiKs+m2uQdjaVftAyX2XwxEM4O9C9JM5FXsigkZuJQR
uUt0Q9qLFGuUUPyWsGySZFR13OCwWd2TJwtPhiMCgYEA0/QvZgBj/SMpZTf5B0RI
owEz1T/lCqJdC4ZdNrjde8liYwGtAX7ogE9ByIhK3qK4npsm50kU89Ko9+6VGDkO
SoiOHYXMpUPDOJLgMvD7v/ZzShPZkQnCfBFYLVvGxh+WrCDfooxHItbdg0gVMOwE
HR+fUWhywVHptRDjwFztqHU=
-----END PRIVATE KEY-----
`;

/**
 * Sign a message string using the RSA private key.
 * Returns the signature as a Base64 string.
 */
async function signData(message: string): Promise<string> {
    try {
        const pemContents = PRIVATE_KEY_PEM
            .replace("-----BEGIN PRIVATE KEY-----", "")
            .replace("-----END PRIVATE KEY-----", "")
            .replace(/\s/g, "");

        // Base64 decode
        const binaryDerString = atob(pemContents);
        const binaryDer = new Uint8Array(binaryDerString.length);
        for (let i = 0; i < binaryDerString.length; i++) {
            binaryDer[i] = binaryDerString.charCodeAt(i);
        }

        const key = await crypto.subtle.importKey(
            "pkcs8",
            binaryDer.buffer,
            {
                name: "RSASSA-PKCS1-v1_5",
                hash: "SHA-256",
            },
            false,
            ["sign"]
        );

        const signature = await crypto.subtle.sign(
            "RSASSA-PKCS1-v1_5",
            key,
            new TextEncoder().encode(message)
        );

        // Convert ArrayBuffer to Base64
        let binary = '';
        const bytes = new Uint8Array(signature);
        const len = bytes.byteLength;
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    } catch (e) {
        console.error("Signing failed:", e);
        return "";
    }
}


// Generate a random license key in format: PRISM-{TIER}-XXXX-XXXX-XXXX-XXXX
function generateLicenseKey(tier: string): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    const segments: string[] = [];

    for (let i = 0; i < 4; i++) {
        let segment = '';
        for (let j = 0; j < 4; j++) {
            segment += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        segments.push(segment);
    }

    return `PRISM-${tier.toUpperCase()}-${segments.join('-')}`;
}

// Add months to a date
function addMonths(date: Date, months: number): Date {
    const result = new Date(date);
    result.setMonth(result.getMonth() + months);
    return result;
}

// Authenticate admin requests
function isAuthorized(request: Request, env: Env): boolean {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return false;
    }
    const token = authHeader.substring(7);
    return token === env.API_SECRET;
}

// Handle OPTIONS (CORS preflight)
function handleOptions(): Response {
    return new Response(null, { headers: corsHeaders });
}

// GET /validate?key=XXXX
async function handleValidate(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const key = url.searchParams.get('key');

    // Rate limiting: max 20 requests per minute per IP
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    const rateLimitKey = `ratelimit:validate:${ip}`;
    const currentCount = await env.LICENSES.get(rateLimitKey);
    const count = currentCount ? parseInt(currentCount) : 0;

    if (count >= 20) {
        return new Response(JSON.stringify({
            valid: false,
            error: 'Rate limited. Try again later.'
        }), {
            status: 429,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Increment rate limit counter (expires in 60 seconds)
    await env.LICENSES.put(rateLimitKey, (count + 1).toString(), { expirationTtl: 60 });

    if (!key) {
        return new Response(JSON.stringify({
            valid: false,
            error: 'Missing license key parameter'
        }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Validate key format
    if (!key.startsWith('PRISM-')) {
        return new Response(JSON.stringify({
            valid: false,
            error: 'Invalid license key format'
        }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    const license = await env.LICENSES.get<License>(key, 'json');

    if (!license) {
        return new Response(JSON.stringify({
            valid: false,
            error: 'Invalid license key'
        }), {
            status: 404,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Check if revoked
    if (license.revoked) {
        return new Response(JSON.stringify({
            valid: false,
            error: 'License has been revoked'
        }), {
            status: 403,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Check expiration
    const now = new Date();
    const expiresAt = new Date(license.expires_at);

    if (now > expiresAt) {
        return new Response(JSON.stringify({
            valid: false,
            error: 'License has expired',
            expired_at: license.expires_at
        }), {
            status: 403,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Calculate days remaining
    const daysRemaining = Math.ceil((expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    // Sign the response data
    // Message format must match backend: "{key}|{expires_at}|{tier}"
    const message = `${key}|${license.expires_at}|${license.tier}`;
    const signature = await signData(message);

    return new Response(JSON.stringify({
        valid: true,
        tier: license.tier,
        email: license.email,
        expires_at: license.expires_at,
        days_remaining: daysRemaining,
        signature: signature // Include signature in response
    }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
}


// POST /admin/create
async function handleCreate(request: Request, env: Env): Promise<Response> {
    if (!isAuthorized(request, env)) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    let body: CreateLicenseRequest;
    try {
        body = await request.json() as CreateLicenseRequest;
    } catch (e) {
        return new Response(JSON.stringify({ error: 'Invalid JSON body' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Validate required fields
    if (!body.email || !body.tier || !body.months) {
        return new Response(JSON.stringify({
            error: 'Missing required fields: email, tier, months'
        }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Validate tier
    if (!['pro', 'enterprise'].includes(body.tier)) {
        return new Response(JSON.stringify({
            error: 'Invalid tier. Must be "pro" or "enterprise"'
        }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Generate key
    const key = generateLicenseKey(body.tier);
    const now = new Date();

    const license: License = {
        tier: body.tier,
        email: body.email,
        created_at: now.toISOString(),
        expires_at: addMonths(now, body.months).toISOString(),
        revoked: false,
        metadata: body.metadata
    };

    // Store in KV
    await env.LICENSES.put(key, JSON.stringify(license));

    // Also add to an index for listing (store email -> keys mapping)
    const emailIndexKey = `email:${body.email}`;
    const existingKeys = await env.LICENSES.get<string[]>(emailIndexKey, 'json') || [];
    existingKeys.push(key);
    await env.LICENSES.put(emailIndexKey, JSON.stringify(existingKeys));

    return new Response(JSON.stringify({
        success: true,
        key: key,
        license: license
    }), {
        status: 201,
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
}

// POST /admin/revoke
async function handleRevoke(request: Request, env: Env): Promise<Response> {
    if (!isAuthorized(request, env)) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    let body: { key: string };
    try {
        body = await request.json() as { key: string };
    } catch (e) {
        return new Response(JSON.stringify({ error: 'Invalid JSON body' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    if (!body.key) {
        return new Response(JSON.stringify({ error: 'Missing key field' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    const license = await env.LICENSES.get<License>(body.key, 'json');

    if (!license) {
        return new Response(JSON.stringify({ error: 'License not found' }), {
            status: 404,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    // Mark as revoked
    license.revoked = true;
    await env.LICENSES.put(body.key, JSON.stringify(license));

    return new Response(JSON.stringify({
        success: true,
        message: 'License revoked'
    }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
}

// GET /admin/list
async function handleList(request: Request, env: Env): Promise<Response> {
    if (!isAuthorized(request, env)) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    const url = new URL(request.url);
    const cursor = url.searchParams.get('cursor') || undefined;
    const limit = parseInt(url.searchParams.get('limit') || '50');

    // List all license keys (excluding email indexes)
    const list = await env.LICENSES.list({ prefix: 'PRISM-', cursor, limit });

    const licenses: { key: string; license: License }[] = [];

    for (const item of list.keys) {
        const license = await env.LICENSES.get<License>(item.name, 'json');
        if (license) {
            licenses.push({ key: item.name, license });
        }
    }

    return new Response(JSON.stringify({
        licenses: licenses,
        cursor: list.cursor,
        complete: list.list_complete
    }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
}

// GET /admin/lookup?email=XXX
async function handleLookup(request: Request, env: Env): Promise<Response> {
    if (!isAuthorized(request, env)) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    const url = new URL(request.url);
    const email = url.searchParams.get('email');

    if (!email) {
        return new Response(JSON.stringify({ error: 'Missing email parameter' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }

    const emailIndexKey = `email:${email}`;
    const keys = await env.LICENSES.get<string[]>(emailIndexKey, 'json') || [];

    const licenses: { key: string; license: License }[] = [];

    for (const key of keys) {
        const license = await env.LICENSES.get<License>(key, 'json');
        if (license) {
            licenses.push({ key, license });
        }
    }

    return new Response(JSON.stringify({ licenses }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
}

// Main request handler
export default {
    async fetch(request: Request, env: Env): Promise<Response> {
        const url = new URL(request.url);
        const path = url.pathname;
        const method = request.method;

        // CORS preflight
        if (method === 'OPTIONS') {
            return handleOptions();
        }

        // Route requests
        if (path === '/validate' && method === 'GET') {
            return handleValidate(request, env);
        }

        if (path === '/admin/create' && method === 'POST') {
            return handleCreate(request, env);
        }

        if (path === '/admin/revoke' && method === 'POST') {
            return handleRevoke(request, env);
        }

        if (path === '/admin/list' && method === 'GET') {
            return handleList(request, env);
        }

        if (path === '/admin/lookup' && method === 'GET') {
            return handleLookup(request, env);
        }

        // Health check
        if (path === '/' || path === '/health') {
            return new Response(JSON.stringify({
                status: 'ok',
                service: 'prism-licensing',
                version: '1.0.0'
            }), {
                headers: { 'Content-Type': 'application/json', ...corsHeaders }
            });
        }

        // 404 for unknown routes
        return new Response(JSON.stringify({ error: 'Not found' }), {
            status: 404,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }
};
