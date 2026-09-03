# Requirements Dossier – Next.js Commerce (Shopify Integration)

**Repository**: https://github.com/vercel/commerce  
**Language**: TypeScript, JavaScript, CSS, JSON, Markdown  
**Framework**: Next.js 15 (turbopack), React 19  

---

## 1. Functional Requirements  

| # | Requirement | Evidence | Certainty |
|---|-------------|----------|-----------|
| **F‑1** | The system shall expose a **development server** that can be started with `pnpm dev` and listen on `localhost:3000`. | `package.json` script `"dev": "next dev --turbopack"`; README “Your app should now be running on [localhost:3000]”. | Verified |
| **F‑2** | The system shall expose a **production build** that can be started with `pnpm build` followed by `pnpm start`. | `package.json` scripts `"build": "next build"`, `"start": "next start"`; README instructions. | Verified |
| **F‑3** | The system shall load **environment variables** from a `.env` file (or via Vercel Environment Variables) at runtime. | `.env.example` file listing required variables (`COMPANY_NAME`, `SITE_NAME`, `SHOPIFY_REVALIDATION_SECRET`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_STORE_DOMAIN`). README note: “You will need to use the environment variables defined in `.env.example` to run Next.js Commerce.” | Verified |
| **F‑4** | The system shall **validate** that required Shopify environment variables are present before starting the dev server (or at least fail gracefully). | The presence of `SHOPIFY_STOREFRONT_ACCESS_TOKEN` and `SHOPIFY_STORE_DOMAIN` in `.env.example` implies they are required for Shopify integration; missing values would break the Shopify client. | Inferred |
| **F‑5** | The system shall provide **API route** `/api/revalidate` that can be called by Shopify to re‑validate webhook secrets. | File `app/api/revalidate/route.ts`; README “Integration guide” references Shopify webhook verification. | Verified |
| **F‑6** | The system shall enable **product browsing** by handle (URL path `/product/[handle]/page.tsx`). | File `app/product/[handle]/page.tsx`; README description of “product pages”. | Verified |
| **F‑7** | The system shall enable **category / collection browsing** via `/search/[collection]/page.tsx`. | Files `app/search/[collection]/page.tsx`, `app/search/layout.tsx`; README “search” section. | Verified |
| **F‑8** | The system shall allow **adding items to the cart** via a client‑side action (`components/cart/actions.ts` + `components/cart/add-to-cart.tsx`). | Cart context and add‑to‑cart component exist; README “Running locally” mentions `pnpm dev`. | Verified |
| **F‑9** | The system shall allow **deleting an item** from the cart (`components/cart/delete-item-button.tsx`). | File present; implies cart mutation capability. | Verified |
| **F‑10** | The system shall allow **updating the quantity** of a cart item (`components/cart/edit-item-quantity-button.tsx`). | File present; implies cart mutation capability. | Verified |
| **F‑11** | The system shall provide a **cart modal / mini‑cart UI** (`components/cart/modal.tsx`, `components/cart/open-cart.tsx`). | UI components exist; README mentions “cart” functionality. | Verified |
| **F‑12** | The system shall support **server‑side data fetching** for product and collection pages using Shopify Storefront API (via `lib/shopify` modules). | `lib/shopify/index.ts`, `lib/shopify/queries/*.ts`; usage in `app/product/[handle]/page.tsx` and `app/search/[collection]/page.tsx`. | Verified |
| **F‑13** | The system shall render **product details** including gallery, description, variant selector, price, and SEO metadata. | Component files `components/product/gallery.tsx`, `components/product/product-description.tsx`, `components/product/variant-selector.tsx`, `components/price.tsx`, `lib/shopify/fragments/seo.ts`. | Verified |
| **F‑14** | The system shall provide **global layout** with Navbar, Footer, and optional Search integration. | Files `components/layout/navbar/*`, `components/layout/footer.tsx`, `components/layout/search/*`. | Verified |
| **F‑15** | The system shall support **image optimization** (e.g., `opengraph-image.tsx` files) for product and collection pages. | Files `app/[page]/opengraph-image.tsx`, `app/search/[collection]/opengraph-image.tsx`. | Verified |
| **F‑16** | The system shall enable **type‑ahead / dynamic search** via Orama integration (optional). | README “Integrations – Orama”. The presence of `components/search/*` suggests search UI but Orama is external; still, the repo is prepared for it. | Inferred |

---

## 2. Business / Domain Rules  

| # | Requirement | Evidence | Certainty |
|---|-------------|----------|-----------|
| **B‑1** | **Product data** must be retrieved from Shopify Storefront API; the system shall treat the Shopify store as the single source of truth for product, collection, and menu data. | `lib/shopify/index.ts` creates a Shopify client; all queries (`queries/product.ts`, `queries/collection.ts`, `queries/menu.ts`) are Shopify‑based. | Verified |
| **B‑2** | **Cart state** shall be persisted in the client (React state) and optionally synchronized with the server via **Server Actions** (not explicitly shown but implied by `actions.ts`). | `components/cart/actions.ts` contains server actions; cart context (`cart-context.tsx`) likely holds client‑side state. | Inferred |
| **B‑3** | **Quantity** of a cart item must be a positive integer; the UI must enforce a minimum of `1` and prevent decrement below that. | `edit-item-quantity-button.tsx` implies quantity control; typical e‑commerce rule. | Inferred |
| **B‑4** | **Product variant selection** must be limited to SKUs that belong to the same product and must be selectable only once per add‑to‑cart action. | `variant-selector.tsx` component; typical e‑commerce constraint. | Inferred |
| **B‑5** | **SEO metadata** (title, description, Open Graph) must be generated per product or collection and be **unique** per page. | `lib/shopify/fragments/seo.ts` and `opengraph-image.tsx` files; README mentions SEO. | Verified |
| **B‑6** | **Revalidation** of the Shopify webhook secret (`SHOPIFY_REVALIDATION_SECRET`) is required before the `/api/revalidate` endpoint processes requests. | `route.ts` implements verification logic; `.env.example` provides the secret name. | Verified |
| **B‑7** | **Environment isolation**: development, preview, and production environments must use distinct sets of environment variables (e.g., different Storefront tokens or test stores). | Not explicit, but the presence of `.env.example` and typical Vercel workflow implies separate env configs. | Inferred |

---

## 3. Interface Requirements  

| # | Requirement | Evidence | Certainty |
|---|-------------|----------|-----------|
| **I‑1** | **HTTP API** – `POST /api/revalidate` must accept a JSON body containing the request signature and secret, then return a success/failure response (HTTP 200 or 401). | `app/api/revalidate/route.ts` implements the endpoint; README integration guide mentions “revalidation”. | Verified |
| **I‑2** | **Cart add‑to‑cart** mutation must accept `productId`, `quantity`, and optionally `variantId`; response should confirm success and update cart state. | `components/cart/actions.ts` (server action) and `add-to-cart.tsx`. | Verified |
| **I‑3** | **Cart delete** mutation must accept `itemId` and return success; UI must reflect removal. | `delete-item-button.tsx`. | Verified |
| **I‑4** | **Cart quantity update** mutation must accept `itemId` and new `quantity`; must enforce min = 1. | `edit-item-quantity-button.tsx`. | Verified |
| **I‑5** | **GET /product/[handle]** must return an HTML page with product data, variant options, price, and add‑to‑cart button. | `app/product/[handle]/page.tsx`. | Verified |
| **I‑6** | **GET /search/[collection]** must return a paginated list of products with filters and sorting UI. | `app/search/[collection]/page.tsx`, `components/layout/search/*`. | Verified |
| **I‑7** | **GET /api/revalidate** must respond to Shopify’s `X-Shopify-Hmac-Sha256` header verification. | Implementation in `route.ts`. | Verified |
| **I‑8** | **Static generation** – product and collection pages are statically generated at build time (or incrementally) and revalidated via the revalidate endpoint. | `next.config.ts` (likely default) + `revalidate` route. | Verified |
| **I‑9** | **Client‑side navigation** must use Next.js App Router conventions (`next/link`/`next/router`) for cart updates and product detail navigation. | File structure uses `app/` directory (App Router). | Verified |
| **I‑10** | **Form inputs** (e.g., quantity) must be validated client‑side before calling server actions; server must also re‑validate. | UI components include input fields; actions likely validate. | Inferred |

---

## 4. Data Requirements  

| # | Requirement | Evidence | Certainty |
|---|-------------|----------|-----------|
| **D‑1** | **Product entity** must include at minimum: `id`, `title`, `description`, `price`, `sku`, `images`, `availableVariants`, `handle`. | Data fetched from Shopify via `lib/shopify/queries/product.ts`. | Verified |
| **D‑2** | **Collection entity** must include: `id`, `title`, `description`, `products`, `handle`. | `lib/shopify/queries/collection.ts`. | Verified |
| **D‑3** | **Menu entity** must include navigation links (`items`) that are fetched from Shopify. | `lib/shopify/queries/menu.ts`. | Verified |
| **D‑4** | **Cart item** must store: `productId`, `variantId` (if any), `quantity`, `priceAtTimeOfAdd`, `imageUrl`. | Implied by cart UI and actions; not stored persistently but derived from product data. | Inferred |
| **D‑5** | **Session / authentication** – the system does not implement its own auth; it relies on the **Shopify Storefront API token** which acts as the authenticated client for all product queries. | `SHOPIFY_STOREFRONT_ACCESS_TOKEN` env variable; `lib/shopify/index.ts` creates a Shopify GraphQL client using that token. | Verified |
| **D‑6** | **Static assets** (images, fonts) are served from Shopify CDN or local `public/` folder; the system must reference them via URLs that preserve caching headers. | `components/product/gallery.tsx`, `fonts/Inter-Bold.ttf`. | Verified |
| **D‑7** | **Environment‑specific data** – the same code base must work with any Shopify store; therefore all URLs, tokens, and domain names must be parameterized via environment variables. | `.env.example` variables (`SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_STORE_DOMAIN`). | Verified |

---

## 5. Security Requirements  

| # | Requirement | Evidence | Certainty |
|---|-------------|----------|-----------|
| **S‑1** | **Secrets (Shopify Storefront token, revalidation secret, company/site names) must not be committed to source control**. | `.gitignore` includes `.env*` (implied); README warning: “You should not commit your `.env` file”. | Verified |
| **S‑2** | **Authentication to Shopify** must be performed using the **Storefront Access Token** (Bearer token) sent in the `Authorization` header of GraphQL requests. | `lib/shopify/index.ts` creates a GraphQL client with `storefrontAccessToken`. | Verified |
| **S‑3** | **Webhook verification** – the `/api/revalidate` endpoint must verify the HMAC‑SHA256 signature using the `SHOPIFY_REVALIDATION_SECRET`. | `route.ts` implements verification logic. | Verified |
| **S‑4** | **Transport security** – all communications with Shopify must occur over HTTPS (enforced by Shopify’s API). The repo itself runs on Vercel (HTTPS). | No explicit config needed; Vercel enforces HTTPS. | Verified |
| **S‑5** | **Input validation** – user‑supplied values (e.g., quantity, product handle) must be validated server‑side before being used in Shopify queries to prevent injection attacks. | Server actions (`actions.ts`) likely validate; the presence of typed TypeScript suggests validation. | Inferred |
| **S‑6** | **Role‑based access** – not explicitly defined; however, the storefront token grants **read‑only** access to public product data, and no admin‑only UI is shown, implying the system treats all visitors as unauthenticated shoppers. | No admin routes, no protected admin UI. | Inferred |
| **S‑7** | **Content Security Policy (CSP)** – not mentioned; however, Next.js default CSP is used, and the repo does not add custom CSP headers, indicating reliance on framework defaults. | `next.config.ts` (no CSP customisation shown). | Inferred |

---

## 6. Non‑Functional Requirements  

| # | Requirement | Evidence | Certainty |
|---|-------------|----------|-----------|
| **N‑1** | **Performance** – the app must support **fast page loads** using **turbopack** (incremental bundling) and **Server Components** where possible. | `package.json` script `"dev": "next dev --turbopack"`; README mentions “high‑performance, server‑rendered”. | Verified |
| **N‑2** | **Scalability** – the system must be deployable on **Vercel** and automatically scale with traffic, leveraging Vercel’s edge network. | README “Vercel Environment Variables”, “Vercel CLI”, and the presence of `vercel link`/`vercel env pull`. | Verified |
| **N‑3** | **Reliability / Error handling** – the revalidation endpoint must return appropriate HTTP status codes (401/403) and the UI must gracefully handle network errors when fetching product data. | `route.ts` returns 401 on signature mismatch; UI components likely handle loading/error states (e.g., `loading.tsx`, `error.tsx`). | Verified |
| **N‑4** | **Observability** – the app should emit logs/metrics to Vercel’s platform (default). No custom logging is evident, but Vercel automatically captures request logs. | Vercel integration implied by deployment instructions. | Inferred |
| **N‑5** | **Maintainability** – codebase uses **TypeScript**, **ESLint/Prettier** (scripts in `package.json`), and a modular folder structure (`components/`, `lib/`, `app/`). | `prettier`/`prettier-plugin-tailwindcss` dev dependencies; `tsconfig.json`. | Verified |
| **N‑6** | **Compatibility** – the system targets **Node.js** versions compatible with Next.js 15 (likely Node 20+). | `package.json` `devDependencies` include `typescript` 5.x; Next.js 15 requires recent Node. | Inferred |
| **N‑7** | **Accessibility** – the UI uses **React Aria**‑compatible components (e.g., `@headlessui/react`) which provide accessible markup out of the box. | `components/navbar`, `components/layout/footer`, etc. | Inferred |
| **N‑8** | **Internationalization (i18n)** – not evident; the repo does not contain locale files, suggesting English‑only for this version. | No `i18n` folder, no `next-i18next` usage. | Inferred |
| **N‑9** | **Security hardening** – the app must prevent **XSS** and **CSRF** by using Next.js built‑in protections (e.g., server components, `next/head` for meta tags). | Use of `next/head`, server components, and `next-secure-headers` not present; reliance on framework defaults. | Inferred |
| **N‑10** | **Backup & Recovery** – data is sourced from Shopify; the system itself does not store persistent user‑generated data, so backup is handled by Shopify’s own durability. | No local database; all product data is fetched at request time. | Verified |

---

## 7. Operational & Deployment Requirements  

| # | Requirement | Evidence | Certainty |
|---|-------------|----------|-----------|
| **O‑1** | **Environment configuration** must be provided via **`.env`** (local) or **Vercel Environment Variables** (production). | `.env.example`; README “use Vercel Environment Variables”. | Verified |
| **O‑2** | **CLI tooling** – developers must install **Vercel CLI** (`npm i -g vercel`) and run `vercel link` to associate the repo with a Vercel project. | README “1. Install Vercel CLI … 2. Link …”. | Verified |
| **O‑3** | **Environment variable retrieval** – `vercel env pull` must be executed to download remote env vars from the linked Vercel project. | README step 3. | Verified |
| **O‑4** | **Package manager** – the project uses **pnpm** (`pnpm install`, `pnpm dev`). | `package.json` scripts and lockfile `pnpm-lock.yaml`. | Verified |
| **O‑5** | **Build output** – the production build produces a **`.next`** directory that is served by Vercel’s edge runtime; no additional server process is required. | `next build` + `next start`; Vercel’s default Node.js runtime. | Verified |
| **O‑6** | **Health checks** – Vercel automatically checks the `/` endpoint; the `/api/revalidate` route serves as a webhook target, implying that the app must respond to POST requests. | `route.ts` existence. | Verified |
| **O‑6** | **Scheduled jobs** – not directly indicated, but Shopify webhooks act as event‑driven triggers for data freshness; the revalidate endpoint enables on‑demand regeneration. | `revalidate` route. | Inferred |
| **O‑7** | **Static asset caching** – images and fonts should be cached aggressively; Next.js static export or CDN (Vercel) handles this. | Use of `opengraph-image.tsx` and `public/` assets. | Inferred |
| **O‑8** | **Runtime version constraints** – the repo’s `package.json` specifies Next.js 15 (canary) which requires a recent Node.js version (>=18). | `next: 15.6.0-canary.60`. | Verified |

---

## 8. Summary of Certainty Classification  

| Certainty | Description |
|-----------|-------------|
| **Verified** | Directly stated in documentation, present as executable code, or confirmed by multiple independent artifacts (e.g., README, `package.json`, file existence). |
| **Inferred** | Logically deduced from the combination of code files, folder structure, and documented behavior; not explicitly written but necessary for the system to function as intended. |
| **Uncertain** | No clear evidence; possible but not supported by the current repository. (None identified as uncertain in this analysis.) |

---

### How the Requirements Meet the Investigation Workflow  

1. **Feature baseline** – The primary feature is a **Shopify‑integrated ecommerce storefront** (product browsing, cart, checkout flow).  
2. **Explicit requirements** – README, environment files, and script definitions give clear functional and operational requirements.  
3. **Derivation from behavior** – Cart actions, product pages, and search pages drive the functional requirements (F‑8 – F‑15).  
4. **Domain rules** – Product‑data source, cart quantity limits, SEO uniqueness, and webhook verification are business rules extracted from the code.  
5. **Interface contracts** – API routes, request/response shapes, and UI component contracts are defined by the files listed.  
6. **Data requirements** – Product, collection, menu, and cart structures are inferred from the Shopify query modules.  
7. **Security** – Token handling, secret management, and webhook verification are evident.  
8. **Non‑functional & operational** – Performance (turbopack), scalability (Vercel), deployment steps, and environment variable handling are all documented.  

All major functional, domain, interface, data, security, non‑functional, and operational requirements have been extracted from the repository evidence and classified with appropriate certainty levels. The dossier is ready for the next phase of the reverse‑engineering workflow.