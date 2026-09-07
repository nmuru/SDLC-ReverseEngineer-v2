# Phase Research Brief

Research schema: 3
Phase: business-requirements

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
# Business Requirements Summary — Next.js Commerce

## Actors and Goals

The primary actor is the **end customer** browsing and purchasing products. Their goals include discovering products via home and collection pages, browsing detailed product information with variant selection, filtering and sorting within collections, managing a persistent shopping cart, and completing checkout. The system explicitly excludes any account management, authentication, or login workflows — this is a guest-only storefront.

A secondary actor is the **system operator** managing product content and configuration through Shopify's admin interface, with the Next.js application serving as a read-only frontend mirror of that content.

## Core Capabilities and Workflows

**Product Discovery:** The application surfaces products through a home page carousel and featured product grid, followed by full collection browsing at `/search/[collection]` with URL-driven filtering and sort controls defined in `lib/constants.ts`. Product detail pages at `/product/[handle]` display variant options, image galleries, pricing, and related product recommendations. `lib/shopify/queries/product.ts` and `lib/shopify/queries/collection.ts` drive all catalog queries via the Shopify Storefront API.

**Search and Filtering:** The search surface at `app/search/page.tsx` provides a sidebar with collection navigation and filter controls. Filtering uses `next/navigation` query parameters, enabling shareable, bookmarkable filter states. Sorting definitions are centralized in `lib/constants.ts` as `SortFilterItem` structures.

**Cart Lifecycle:** Cart management is the most explicitly modeled workflow. The full lifecycle includes: cart creation (`createCart`), adding items (`addToCart` / `addItem` in `components/cart/actions.ts`), quantity editing (`updateCart` / `updateItemQuantity`), item removal (`removeFromCart` / `removeItem`), and checkout redirection. Cart state is maintained client-side via React context (`components/cart/cart-context.tsx`) with a reducer pattern, while all mutations invoke server actions that call the Shopify GraphQL API and trigger cache revalidation.

**Content and SEO:** Static content pages are managed via Shopify and rendered at `app/[page]/page.tsx` with dynamic OpenGraph image generation. A sitemap at `app/sitemap.ts` aggregates Shopify pages and collections for crawler discovery.

## Validation and Business Rules

Environment validation at `lib/utils.ts` ensures required variables (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SITE_NAME`) are present at build time, preventing misconfigured deployments. The revalidation endpoint at `app/api/revalidate/route.ts` is secured by `SHOPIFY_REVALIDATION_SECRET`, validating that webhook calls originate from Shopify.

Type guards in `lib/type-guards.ts` suggest defensive handling of Shopify API responses, though the full error recovery strategy is not fully articulated in the supplied intelligence.

## State Management and Dependencies

The cart is the primary client-side state entity, managed through `CartContextType` with actions for item updates and cart creation. Product and collection data flow server-side from Shopify through `lib/shopify/index.ts`, the single integration gateway. All external data dependency routes through Shopify's Storefront API; the application does not implement its own product catalog, inventory, or order management.

## Notable Exceptions and Gaps

No authentication or user account system exists — all sessions are anonymous. The `test` script only runs Prettier formatting checks, leaving no automated verification of business logic. Payment processing is limited to redirecting to Shopify Checkout, with no in-app payment handling. The error recovery strategy for Shopify API failures is referenced but not fully evidenced. No analytics, tracking, or A/B testing capabilities are visible in the codebase.
