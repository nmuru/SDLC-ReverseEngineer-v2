# Phase Research Brief

Research schema: 3
Phase: business-purpose

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
# Business Purpose Summary

## Product and Intended UseThis repository is **Next.js Commerce**, a Vercel-maintained, open-source ecommerce storefront template specifically wired to **Shopify** as its commerce backend. The README explicitly positions it as "a high-performance, server-rendered Next.js App Router ecommerce application," and states that Vercel will "only be actively maintaining a Shopify version." The deployment button in the README preconfigures the `integration=shopify` product slug, reinforcing that Shopify is the first-class target rather than one option among many. The repository summary likewise treats this fork as a "specific focus on Shopify integration."

The product is a **reference template**, not a finished store. Its purpose is to give a developer a runnable, deployable foundation that demonstrates modern patterns — React Server Components, Server Actions, `Suspense`, `useOptimistic` — and that can be cloned, rebranded via environment configuration (`SITE_NAME`, `VERCEL_PROJECT_PRODUCTION_URL`), and pointed at a real Shopify domain (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`).

## Likely Users
Three user classes are implied by the evidence:

1. **End shoppers** — anonymous visitors who browse the homepage (`app/page.tsx`), browse collections (`app/search/[collection]/page.tsx`), search (`app/search/page.tsx`), view product details (`app/product/[handle]/page.tsx`), build a cookie-backed cart, and are redirected to Shopify-hosted checkout (`redirectToCheckout` in `components/cart/actions.ts`). No authentication or account system is present.
2. **Merchants / store operators** — Shopify admins whose product, collection, menu, and page content drives the storefront. Their edits propagate via a webhook-driven revalidation endpoint (`app/api/revalidate/route.ts`, secured by `SHOPIFY_REVALIDATION_SECRET`).
3. **Developers** — the primary adopter persona. The README explicitly invites forks where "alternative providers should be able to fork this repository and swap out the `lib/shopify` file with their own implementation." The modular Shopify layer (`lib/shopify/index.ts`, `lib/shopify/queries/*`, `lib/shopify/mutations/*`, `lib/shopify/fragments/*`) is engineered for swap-out, not just for use.

## Value Delivered
- A **production-shape storefront** covering the full browse → cart → checkout hand-off, without rebuilding catalogue, cart, or SEO plumbing from scratch.
- **Server-first performance**: ISR/revalidation through `app/api/revalidate/route.ts`, dynamic `app/sitemap.ts`, `app/robots.ts`, per-route `generateMetadata` (`app/product/[handle]/page.tsx`, `app/search/[collection]/page.tsx`, `app/[page]/page.tsx`), and Next.js Image optimisation.
- **Provider isolation**: all Shopify GraphQL lives under `lib/shopify`, so a non-Shopify fork can replace one module without touching UI components.

## Major Capabilities (evidence-supported)
- **Catalogue and navigation**: homepage carousel and three-item grid (`app/page.tsx`, `components/carousel.tsx`, `components/grid/three-items.tsx`); collection browsing with filtering/sorting (`components/layout/search/filter/index.tsx`, `components/layout/search/filter/dropdown.tsx`, `components/layout/search/filter/item.tsx`); product detail pages with gallery, variant selector (`components/product/variant-selector.tsx`), description (`components/product/product-description.tsx`), and recommendations (`getProductRecommendations`).
- **Search and filtering**: navbar search via `components/layout/navbar/search.tsx`; collection sidebar via `components/layout/search/collections.tsx`; dedicated search layout with `loading.tsx` (`app/search/layout.tsx`, `app/search/loading.tsx`).
- **Cart**: React Context + reducer (`components/cart/cart-context.tsx`), Server Actions for mutation (`components/cart/actions.ts: addItem`, `removeItem`, `updateItemQuantity`, `createCartAndSetCookie`, `redirectToCheckout`), slide-in cart UI (`components/cart/modal.tsx`, `components/cart/open-cart.tsx`, `components/cart/add-to-cart.tsx`, `components/cart/delete-item-button.tsx`, `components/cart/edit-item-quantity-button.tsx`).
- **Content surfaces**: dynamic Shopify pages (`app/[page]/page.tsx`, `lib/shopify/queries/page.ts`), menu-driven navigation (`lib/shopify/queries/menu.ts`, `components/layout/navbar/index.tsx`, `components/layout/footer.tsx`, `components/layout/footer-menu.tsx`, `components/layout/navbar/mobile-menu.tsx`).
- **SEO infrastructure**: `app/sitemap.ts`, `app/robots.ts`, Open Graph image generation (`components/opengraph-image.tsx`, per-route `opengraph-image.tsx` files), typed fragments for SEO (`lib/shopify/fragments/seo.ts`).
- **Webhook-driven freshness**: `app/api/revalidate/route.ts` plus the `revalidate` export in `lib/shopify/index.ts` keep statically generated routes consistent with Shopify-side edits.

## System Boundaries
- **External boundary**: the **Shopify Storefront API** is the sole commerce data source (queries in `lib/shopify/queries/*`, mutations in `lib/shopify/mutations/cart.ts`); no other commerce backend is wired.
- **Deployment boundary**: Vercel-flavoured (`VERCEL_PROJECT_PRODUCTION_URL`, the Vercel deploy button), with `next dev --turbopack` and `next build` scripts in `package.json`.
- **Trust boundary**: anonymous shoppers only; the cart is cookie-scoped and there is no user account concept in the supplied symbols.
- **Provider-swap boundary**: the `lib/shopify` directory is deliberately the only Shopify-coupled layer; UI components depend on shared types (`lib/shopify/types.ts`) rather than on Shopify directly.

## Inferences vs. Verified Facts
Verified: Shopify-only positioning, server-rendered App Router architecture, cookie-backed cart with hosted checkout, webhook revalidation, full sitemap/robots/OG coverage, no tests beyond `prettier:check` (`package.json` `test` script), and a swap-friendly provider abstraction. Inferred (consistent with evidence but not explicitly stated): that the primary commercial intent is to be cloned as a starting point rather than deployed unchanged, and that merchants are second-class users served indirectly through Shopify's admin and the revalidation webhook.

## Important Uncertainties
- The exact **revalidation webhook payload contract** handled by `app/api/revalidate/route.ts` is not shown.
- The **cart cookie name, lifetime, and rotation rules** are not visible in the supplied symbols.
- The **search query semantics** (whether it uses Shopify's text search, `productRecommendations`, or a query parameter pattern) are not detailed.
- **UI-level error fallbacks** for Shopify API failures are not evident beyond `lib/type-guards.ts`.
