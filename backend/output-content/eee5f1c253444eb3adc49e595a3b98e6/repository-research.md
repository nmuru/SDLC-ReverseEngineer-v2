# Repository Research Brief

Research schema: 3
Phase: repository-wide

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
# Next.js Commerce Repository Summary

This repository implements **Next.js Commerce v2**, a high-performance, server-rendered ecommerce application built on the Next.js App Router framework. The project is maintained by Vercel and serves as the reference Shopify template for the Next.js Commerce ecosystem. The domain is clearly ecommerce: a online storefront with product catalog browsing, shopping cart functionality, search and filtering, and checkout integration. The repository provides a complete template that can be forked and adapted for alternative commerce providers by swapping the `lib/shopify` implementation, indicating its role as a reusable foundation rather than a standalone product.

## Business and Domain Concepts

The core business domain centers on a typical retail ecommerce customer journey. Products are organized into collections and categories, browsable through grid and list interfaces. A shopping cart manages line items with quantity adjustments, removals, and checkout progression. Search functionality supports filtering by tags, price ranges, and other attributes defined through a constants-driven filter system (`lib/constants.ts`). The presence of SEO metadata generation, Open Graph image rendering, and sitemap generation indicates that discoverability and marketing integration are first-class concerns. The revalidation endpoint (`app/api/revalidate/route.ts`) suggests a workflow where content changes in the connected backend (Shopify) trigger incremental site regeneration, balancing freshness with performance.

## Users, Actors, and System Boundaries

The primary external actor is a shopper interacting with the storefront: browsing products, searching, managing a cart, and checking out. On the operational side, an administrator or system integration with Shopify supplies product data, inventory, and orders. The system boundary is defined by the Next.js App Router layer, which renders React Server Components on the server and hydrates client-side interactivity where needed. The `lib/shopify` module abstracts the backend commerce API, currently configured for Shopify Storefront API access via environment variables (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`). The repository’s architecture separates concerns into navigation, product display, cart management, and search layers, with clear import boundaries (e.g., `components/layout/navbar/index.tsx` importing from `components/layout/navbar/mobile-menu.tsx` and `components/layout/navbar/search.tsx`).

## Major Capabilities and Representative Workflows

Key capabilities visible in the evidence include:

- **Product browsing and discovery**: Grid-based product grids (`components/grid/three-items.tsx`, `components/product/product-description.tsx`), collection pages (`app/search/[collection]/page.tsx`), and featured carousels (`components/carousel.tsx`).
- **Search and filtering**: A dedicated search page (`app/search/page.tsx`) with filter UI (`components/layout/search/filter/index.tsx`, `components/layout/search/filter/item.tsx`) that queries collections and products via Shopify GraphQL operations.
- **Cart management**: Cart state stored in a React context (`components/cart/cart-context.tsx`), with actions for adding, removing, and updating line items (`components/cart/actions.ts`). The cart modal (`components/cart/modal.tsx`) orchestrates item deletion, quantity edits, and checkout button rendering. Server actions in `components/cart/actions.ts` handle cart creation and checkout redirection.
- **SEO and metadata**: Each page type (product, collection, search) generates metadata via `generateMetadata` functions, using fragment-sewed SEO data (`lib/shopify/fragments/seo.ts`).
- **Revalidation**: The `app/api/revalidate/route.ts` endpoint accepts POST requests to invalidate cached pages, likely triggered by webhooks from the Shopify backend.

These workflows follow a consistent pattern: UI components import from `lib/shopify` for data fetching (`lib/shopify/queries/product.ts`, `lib/shopify/queries/collection.ts`) and mutations (`lib/shopify/mutations/cart.ts`), with types defined in `lib/shopify/types.ts`.

## Important Entities, State, and Relationships

The entity model maps directly to Shopify’s GraphQL schema. Key types include `Product`, `ProductVariant`, `ProductOption`, `Collection`, `Image`, `Cart`, `CartItem`, and `Money`. Relationships are explicit: a `Product` belongs to a `Collection` and has multiple `Variant`s; a `Cart` contains multiple `CartItem`s, each referencing a `CartProduct`. Navigation menus are represented as `Menu` items queried through `lib/shopify/queries/menu.ts`. The filter system in `lib/constants.ts` defines `SortFilterItem`, `defaultSort`, and tag constants (`TAGS`, `HIDDEN_PRODUCT_TAG`, `DEFAULT_OPTION`), shaping how products are sorted and filtered. State flow moves from Shopify API responses through query fragments into React state (via `useCart` hook) and finally into UI rendering.

## External Systems and Integrations

The primary external system is **Shopify**, accessed via the Storefront API. Integration is configured through environment variables and encapsulated in `lib/shopify/index.ts`, which exports a `shopifyFetch` utility and operation-specific functions. The repository references Vercel as the deployment platform, with a "Deploy with Vercel" badge in the README and environment variables named accordingly (`VERCEL_PROJECT_PRODUCTION_URL`). UI dependencies include `@headlessui/react` for accessible modal and navigation patterns, `@heroicons/react` for iconography, and `sonner` for toast notifications. Tailwind CSS v4 provides the styling system, with configuration in `postcss.config.mjs` and `tailwindcss` v4.0.14. The `geist` font utility is imported in `app/layout.tsx` for custom font loading.

## Important Implementation Characteristics

The repository is built on **Next.js 15** (canary channel `15.6.0-canary.60`) with the **App Router** enabled. The codebase is entirely **TypeScript**, including type guards (`lib/type-guards.ts`) that narrow Shopify error types. The component hierarchy blends Server Components (pages, layouts) with client-side interactivity (modals, cart operations), using `Suspense` boundaries where appropriate. Tailwind CSS v4’s utility-first approach replaces traditional CSS files, with `clsx` for conditional class joining. The `next/cache` import in `components/cart/actions.ts` hints at optimistic caching or revalidation strategies. The `lib/utils.ts` module exports URL manipulation helpers (`createUrl`, `ensureStartsWith`) and environment variable validation. The dependency graph is relatively flat: Next.js and React form the core framework, with targeted integrations for UI primitives, icons, and analytics.

## Ambiguities and Insufficient Evidence

Several areas lack sufficient detail for definitive interpretation. The exact Shopify API version, GraphQL query depth, and rate-limit handling are not exposed in the extracted symbols. The precise checkout flow beyond the `redirectToCheckout` server action is not fully visible. Test files or test configuration beyond `test: pnpm prettier:check` are absent from the intelligence, leaving test coverage and CI pipeline details unclear. The `lib/constants.ts` file defines sorting and filter constants whose business rules (e.g., what `HIDDEN_PRODUCT_TAG` signifies) are not documented in the provided excerpts. Additionally, while the repository claims support for alternative commerce providers, the specific interfaces that must be implemented (beyond `lib/shopify`) are not enumerated. These gaps do not undermine the overall architectural understanding but should be noted for downstream phases requiring granular API or testing details.
