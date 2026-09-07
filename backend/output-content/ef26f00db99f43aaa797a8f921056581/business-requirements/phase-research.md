# Phase Research Brief

Research schema: 3
Phase: business-requirements

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
## Business Requirements Phase Summary

### Core Product Intent

Next.js Commerce is a **reference ecommerce template** built by Vercel, designed for **Shopify** as the primary commerce provider. The architecture explicitly supports provider swapping by isolating Shopify-specific logic in `lib/shopify/`, allowing alternative providers (BigCommerce, Ecwid, Geins) to fork and replace only that layer. The template demonstrates modern Next.js App Router patterns: React Server Components, Server Actions, Suspense, and optimistic UI updates.

### Primary Actors and Goals

| Actor | Goals |
|-------|-------|
| **Shopper** | Browse products/collections, search with filters, view product details, manage a cart, proceed to checkout |
| **Merchant/Content Editor** | Manage products, collections, menus, and static pages in Shopify; see changes reflected via revalidation |
| **Developer/Integrator** | Deploy a performant, typed storefront; customize UI; swap commerce provider with minimal friction |

### Core Capabilities and Workflows

**Product Discovery**
- Home page with carousel and curated product grids (`app/page.tsx`)
- Collection/category browsing with server-rendered grids (`app/search/[collection]/page.tsx`)
- Full-text search with collection filtering, sort options, and path-based filter items (`app/search/page.tsx`, `components/layout/navbar/search.tsx`, `components/layout/search/filter/`)
- Static CMS pages for content (About, FAQ, etc.) (`app/[page]/page.tsx`)

**Product Detail**
- Product page with variant selection, description, SEO metadata, and related product recommendations (`app/product/[handle]/page.tsx`, `components/product/variant-selector.tsx`, `components/product/product-description.tsx`)

**Cart Management** (full client-side state with server-backed persistence)
- Add/remove/update line items via Server Actions (`components/cart/actions.ts`: `addItem`, `removeItem`, `updateItemQuantity`)
- Cart context with reducer-based state (`components/cart/cart-context.tsx`: `cartReducer`, `CartProvider`, `useCart`)
- Modal UI with quantity editing, line-item deletion, cost summary, and checkout redirect (`components/cart/modal.tsx`, `components/cart/delete-item-button.tsx`, `components/cart/edit-item-quantity-button.tsx`)
- Cart creation and cookie persistence (`createCartAndSetCookie`)

**Checkout**
- Redirect to Shopify checkout via `redirectToCheckout` Server Action; no local order/payment processing

**Content & Navigation**
- Menu and page retrieval from Shopify (`lib/shopify/queries/menu.ts`, `lib/shopify/queries/page.ts`)
- Footer and navbar built from Shopify menus (`components/layout/navbar/`, `components/layout/footer-menu.tsx`)

**Revalidation**
- API route `/api/revalidate` accepts webhook payloads (secured by `SHOPIFY_REVALIDATION_SECRET`) to invalidate Next.js cache on Shopify data changes (`app/api/revalidate/route.ts`, `lib/shopify/index.ts`: `revalidate`)

**SEO & Discovery**
- Per-page `generateMetadata` and OpenGraph image generation (`app/product/[handle]/opengraph-image.tsx`, `app/search/[collection]/opengraph-image.tsx`, `app/[page]/opengraph-image.tsx`)
- Sitemap and robots.txt generated server-side from Shopify data (`app/sitemap.ts`)

### Business Rules and Validation Signals

- **Cart invariants**: Quantity updates and line-item operations go through a reducer (`cartReducer`) with explicit action types (`UpdateType`, `CartAction`), suggesting guarded state transitions.
- **Type guards**: `lib/type-guards.ts` and typed GraphQL fragments (`lib/shopify/fragments/`) enforce shape safety at the Shopify boundary.
- **Revalidation secret**: Webhook endpoint validates `SHOPIFY_REVALIDATION_SECRET` before cache invalidation.
- **Provider isolation**: The `lib/shopify/` boundary is the contract; swapping providers means implementing the same exported functions (`createCart`, `getProduct`, `getCollections`, etc.) and types (`Cart`, `Product`, `Collection`).

### State Changes and Side Effects

| Operation | State Change | Side Effect |
|-----------|--------------|-------------|
| Add to cart | Cart lines + totals updated optimistically | Server Action → Shopify `cartLinesAdd` mutation → cache revalidation |
| Update quantity | Line quantity + totals updated optimistically | Server Action → Shopify `cartLinesUpdate` |
| Remove item | Line removed, totals recalculated | Server Action → Shopify `cartLinesRemove` |
| Create cart | Empty cart initialized, cookie set | Shopify `cartCreate` |
| Checkout redirect | No local state change | Navigation to Shopify checkout URL |
| Revalidate webhook | Next.js data cache purged | Subsequent requests fetch fresh Shopify data |

### External Dependencies

- **Shopify Storefront API** (GraphQL): All product, collection, cart, menu, and page data; mutations for cart operations.
- **Vercel**: Deployment, `VERCEL_PROJECT_PRODUCTION_URL` for canonical URLs/sitemaps.
- **Environment configuration**: `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_REVALIDATION_SECRET`, `SITE_NAME`.

### Notable Uncertainties (from supplied intelligence)

1. **Revalidation granularity**: The webhook handler exists but the exact cache tags/paths invalidated per event type (product update, collection change, menu edit) are not visible.
2. **Error handling and fallback UX**: How cart mutations surface errors to the shopper (toast, inline, modal) is not explicit in the symbol list; `sonner` is present but usage sites unconfirmed.
3. **Inventory/availability rules**: Whether variant selection enforces stock checks before add-to-cart, or if overselling is handled at Shopify checkout only.
4. **Authentication/accounts**: No customer account flows (login, order history, saved addresses) appear in the route map; the template appears guest-checkout only.
5. **Internationalization/multi-currency**: No locale or currency routing detected in the provided routes.
6. **Analytics/events**: No explicit tracking layer (e.g., `view_item`, `add_to_cart`, `begin_checkout`) visible in the extracted symbols.

### Representative Evidence Paths

- Cart workflow: `components/cart/actions.ts` → `components/cart/cart-context.tsx` → `components/cart/modal.tsx`
- Shopify data layer: `lib/shopify/index.ts` (exports) → `lib/shopify/queries/*.ts`, `lib/shopify/mutations/cart.ts`
- Discovery flows: `app/search/page.tsx`, `app/search/[collection]/page.tsx`, `app/product/[handle]/page.tsx`
- Revalidation: `app/api/revalidate/route.ts`, `lib/shopify/index.ts` (`revalidate`)
- Provider boundary: `lib/shopify/types.ts` (shared types), `lib/shopify/index.ts` (function contract)

---

**Summary**: The template implements a complete **guest shopper journey** (discover → detail → cart → checkout) backed by Shopify, with a clean provider abstraction, server-rendered SEO-friendly pages, and optimistic cart UX. Merchant-facing capabilities are limited to content management via Shopify admin with webhook-driven revalidation. Account management, multi-currency, and advanced merchandising rules are out of scope for this template.
