# Phase Research Brief

Research schema: 3
Phase: business-requirements

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
## Business Requirements — Next.js Commerce (Shopify variant)

### Product intentThe repository is a **server-rendered ecommerce storefront template** built on Next.js App Router, marketed as a starter that one can "Deploy with Vercel." The README explicitly positions it as the **Shopify variant** in a provider-swappable family (BigCommerce, Ecwid, Geins forks cited), with Vercel maintaining only the Shopify branch. The implied business goal is to give merchants a high-performance, SEO-friendly, easy-to-deploy storefront shell that they can customize and that delegates commerce back-office concerns (checkout, orders, accounts) to Shopify.

Evidence: `README.md`; `lib/shopify/index.ts`; `components/cart/actions.ts` (exports `redirectToCheckout`).

### Actors and their goals

1. **Shopper (unauthenticated)** — Browse a home page, collections, and product detail pages; search; manage a cart; submit to checkout. No customer accounts, no order history are represented in code; checkout is delegated to Shopify-hosted pages. Evidence: `app/page.tsx`, `app/product/[handle]/page.tsx`, `app/search/[collection]/page.tsx`, `components/cart/cart-context.tsx` (`CartProvider`, `useCart`), `components/cart/actions.ts` (`redirectToCheckout`).
2. **Merchant (Store operator)** — Owns the Shopify catalog and configures the storefront via environment variables (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_REVALIDATION_SECRET`, `SITE_NAME`). Their goals implied by the codebase: surface products, collections, CMS pages, and navigation; control merchandising visibility via tags (`HIDDEN_PRODUCT_TAG`, `TAGS` in `lib/constants.ts`); receive revalidation webhooks to keep caches fresh. Evidence: `lib/constants.ts`; `app/api/revalidate/route.ts`.
3. **Platform / deploy operator (Vercel)** — Provides runtime, deploys via the one-click button; the codebase does not include explicit CI beyond `prettier --check` (aliased as `pnpm test`). Evidence: README deploy button; `VERCEL_PROJECT_PRODUCTION_URL` env.

### Core capabilities

- **Product browsing**: Home (`app/page.tsx`) composes featured products into a carousel and a three-item hero grid using `getCollectionProducts`. Collection pages (`app/search/[collection]/page.tsx`) list products with sort and tag-based filtering. Sort titles and defaults are centralized in `lib/constants.ts` (`SortFilterItem`, `defaultSort`, `sorting`, `TAGS`).
- **Product detail** (`app/product/[handle]/page.tsx`): gallery, price, variant selector (`components/product/variant-selector.tsx`) bound to URL search params, add-to-cart, and related products via `getProductRecommendations`.
- **CMS-like pages** (`app/[page]/page.tsx` with `lib/shopify/queries/page.ts`): distinct from products.
- **Search** (`app/search/page.tsx`) and navigation menu (`lib/shopify/queries/menu.ts`).
- **Cart lifecycle**: server actions in `components/cart/actions.ts` (`addItem`, `removeItem`, `updateItemQuantity`, `createCartAndSetCookie`) call Shopify mutations; client state is held in `components/cart/cart-context.tsx` (`cartReducer`, `useCart`, optimistic updates). The cart ID is persisted as a cookie.
- **Cache invalidation**: webhook endpoint `app/api/revalidate/route.ts` secured by `SHOPIFY_REVALIDATION_SECRET` triggers tag-based revalidation (`next/cache` `revalidateTag`) when Shopify content changes.
- **SEO**: dynamic OG image generators (`app/opengraph-image.tsx`, `app/[page]/opengraph-image.tsx`, `app/search/[collection]/opengraph-image.tsx`), `app/sitemap.ts`, `app/robots.ts`.

### Workflows (end-to-end behaviors)

- **Browse-to-cart-to-checkout**: shopper lands on home → navigates collection → opens product → selects variant via URL search params → `AddToCart` calls `addItem` server action → `createCartAndSetCookie` issues cart cookie → cart mutations round-trip to Shopify → modal opens via `OpenCart` → `redirectToCheckout` hands off to Shopify checkout. Evidence chain: `components/cart/add-to-cart.tsx` → `components/cart/actions.ts` → `lib/shopify/index.ts` (`addToCart`) → `lib/shopify/mutations/cart.ts`; UI in `components/cart/modal.tsx`.
- **Merchandising filter/sort**: shopper selects sort/filter items in `components/layout/search/filter/*`; these update URL search params via `createUrl`/`ensureStartsWith` (`lib/utils.ts`), and the page re-fetches products via `getCollectionProducts` using `revalidateTag`.
- **Catalog freshness**: merchant triggers a Shopify webhook → POST to `/api/revalidate` with secret → `revalidate` (`lib/shopify/index.ts`) maps payload to tag purges (`collections`, `products`, `pages`).
- **SEO share**: any rendered route can produce an OG image and sitemap entry; metadata is generated per page via helpers (`generateMetadata`).

### Business rules and validation

- **Environment contract**: `validateEnvironmentVariables` (`lib/utils.ts`) runs at startup and throws if Shopify credentials or `SITE_NAME` are missing. This is the de facto env schema — an implicit business requirement that the storefront cannot boot without valid Shopify Storefront credentials.
- **Merchandising tags**: `HIDDEN_PRODUCT_TAG` and `TAGS` in `lib/constants.ts` encode the convention that hidden SKUs and grouping tags are used to filter or omit products from listing — a catalog-presentation rule.
- **Variant identity**: `Combination` in `components/product/variant-selector.tsx` ties selected options to URL search params, which is the rule for what constitutes "the same product configuration."
- **Cart identity rule**: the cart cookie (`createCartAndSetCookie`) is the key linking client state to the server-side Shopify cart; deletion/update operations round-trip through server actions rather than mutating locally only.
- **Revalidation authorization**: webhook calls must include `SHOPIFY_REVALIDATION_SECRET`; `ShopifyErrorLike` type guard (`lib/type-guards.ts`) plus `lib/utils.ts` validators guard error handling around `shopifyFetch`.

### State changes of business interest

- **Catalog reads** (products, collections, pages, menus, recommendations) — read-through cache via `revalidateTag`; invalidated by webhook.
- **Cart mutations** (create/add/remove/update) — durable on Shopify side, mirrored optimistically in `CartContext`.
- **URL state** — sort/filter and selected variant reflected in search params, making shareable URLs a first-class business outcome.
- **Welcome toast** (`components/welcome-toast.tsx`) — demo-store UX, not a persistent requirement.

### Notable exclusions and uncertainties

- **No authentication, customer accounts, or order history** — checkout is delegated to Shopify-hosted pages via `redirectToCheckout`, so post-purchase flows are explicitly out of scope by design.
- **No formal CI or test runner**: `pnpm test` only runs Prettier formatting; there is no unit/integration test harness in the supplied intelligence. This is a gap if "tested software" is a business requirement.
- **No `vercel.json` or `.github/` workflows** in the supplied evidence — deploy automation beyond the README button is unconfirmed.
- **No explicit requirements document** beyond the README; business rules are inferred from code (env validation, hidden product tag, cookie-based cart identity, webhook secret). Any downstream agent evolving behavior must treat the README and the `lib/shopify` boundary as the authoritative source of intent.
- **Provider abstraction is a stated business goal** — the README and the isolation of all commerce logic under `lib/shopify/*` indicate that re-targeting another platform (BigCommerce/Ecwid/Geins) is intended to require rewriting only that subtree; whether the rest of the template is truly provider-agnostic is an inference, not a verified fact.
- **Symbol extraction was incomplete** (Tree-sitter unavailable for TS/TSX), so the precise GraphQL field selections and minor helpers are not visible in the deterministic intelligence; behavioral claims above are based on imports/exports and file roles, not parsed bodies.
