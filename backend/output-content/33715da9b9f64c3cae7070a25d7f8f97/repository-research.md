# Repository Research Brief

Research schema: 3
Phase: repository-wide

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
**Repository Summary**

The repository is a **Next.js Commerce** template—a high‑performance, server‑rendered e‑commerce application built with the Next.js App Router. It is a TypeScript‑first project that leverages React Server Components, Server Actions, Suspense, and optimistic UI patterns to deliver a fast, SEO‑friendly storefront. The template is currently focused on **Shopify** as the commerce provider, though the README notes that alternative providers (BigCommerce, Ecwid, Geins) can be swapped in by forking and replacing the `lib/shopify` layer. The project is configured for deployment on Vercel (environment variables include `VERCEL_PROJECT_PRODUCTION_URL` and a Vercel deployment button in the README) and uses Tailwind CSS with PostCSS, container queries, and a comprehensive design system based on Headless UI and Heroicons.

**Business/Domain Concepts**

The core domain revolves around a product catalog, shopping cart, checkout flow, and content pages. Strongly supported concepts include:

- **Product management** – individual product details, variants, images, pricing, and SEO metadata.
- **Collections / categories** – grouped product listings accessible via `/search/[collection]` and navigation menus.
- **Cart & checkout** – add/remove items, adjust quantities, view cart in a modal, and proceed to checkout (the checkout itself is likely external to this repo).
- **Search & filtering** – a faceted search interface (`/search`) with collection filters, sorting, and pagination.
- **Static content** – dynamic pages (`/page/[slug]`) for marketing or informational content.
- **Navigation & footer** – hierarchical menu system (`lib/shopify/queries/menu.ts`) and footer links.
- **Cache revalidation** – an `/api/revalidate` endpoint (`app/api/revalidate/route.ts`) to invalidate Shopify data caches after mutations.

**Users, Actors, and System Boundaries**

Primary actors are **shoppers** who browse products, add items to cart, and view content. The system boundary is defined by the client‑side React components (`components/`) and the server‑side Shopify integration (`lib/shopify/`). The cart state is managed locally via `components/cart/cart-context.tsx`, while product data, collections, and pages are fetched server‑side through `lib/shopify/index.ts`. The revalidation API (`app/api/revalidate/route.ts`) sits at the edge of the Next.js runtime, exposing a mutation endpoint for cache updates.

**Major Capabilities and Representative Workflows**

- **Home page** (`app/page.tsx`) renders a carousel and a three‑item grid (`components/grid/three-items.tsx`) pulling products from Shopify.
- **Product detail** (`app/product/[handle]/page.tsx`) combines a gallery (`components/product/gallery.tsx`) with a description and variant selector (`components/product/variant-selector.tsx`), and includes an “Add to Cart” button (`components/cart/add-to-cart.tsx`).
- **Search & filtering** (`app/search/page.tsx`, `components/layout/search/filter/index.tsx`) presents a list of collections (`components/layout/search/collections.tsx`) and interactive filter items (`components/layout/search/filter/item.tsx`), enabling faceted navigation.
- **Cart management** – items can be added/removed/updated via `components/cart/actions.ts` (which calls `lib/shopify` mutations), displayed in a modal (`components/cart/modal.tsx`), and persisted across sessions using cookies (`createCartAndSetCookie`).
- **Static pages** (`app/[page]/page.tsx`) are fetched via `lib/shopify/queries/page.ts` and rendered with prose components (`components/prose.tsx`).
- **SEO & sharing** – metadata is generated per page (`generateMetadata` functions), OpenGraph images are built (`components/opengraph-image.tsx`), and a sitemap (`app/sitemap.ts`) is statically generated.
- **Performance & caching** – `next/cache` is used for data fetching, and `app/api/revalidate/route.ts` triggers cache invalidation after cart mutations.

**Important Entities, State, and Relationships**

Key data models (defined in `lib/shopify/types.ts`) include `Product`, `ProductVariant`, `Cart`, `CartItem`, `Collection`, `Menu`, `Page`, `Image`, and `Money`. Relationships are:

- **Cart ↔ CartItem** – a cart contains multiple items, each referencing a product variant.
- **Product ↔ Collection** – products are associated with one or more collections.
- **Menu ↔ Collection/Page** – navigation menus link to collections or static pages.
- **Cart ↔ Shopify API** – cart operations (create, add, remove, update) are performed via GraphQL mutations defined in `lib/shopify/mutations/cart.ts` and `lib/shopify/queries/cart.ts`.

State is managed through React Context (`CartProvider` in `components/cart/cart-context.tsx`), which holds the cart items, totals, and actions to update the cart locally and sync with Shopify via server actions.

**External Systems/Integrations**

- **Shopify GraphQL API** – the primary data source for products, collections, carts, and content. Integration is encapsulated in `lib/shopify/index.ts` and its supporting query/mutation files.
- **Vercel hosting** – indicated by environment variables (`VERCEL_PROJECT_PRODUCTION_URL`) and the Vercel deployment button in the README. The project uses Vercel‑specific caching and revalidation patterns.
- **Potential alternative providers** – the README lists BigCommerce, Ecwid, and Geins as possible forks, suggesting the template is designed for easy substitution of the `lib/shopify` layer.

**Implementation Characteristics**

- **Architecture** – Next.js App Router with Server Components and Server Actions (e.g., `addToCart` in `components/cart/actions.ts`). Client‑side interactivity is limited to UI state and optimistic updates.
- **Styling** – Tailwind CSS v4 with PostCSS, container queries (`@tailwindcss/container-queries`), and a typography plugin. Global styles are in `app/globals.css`.
- **Type safety** – Full TypeScript support (`tsconfig.json`), strict typing for Shopify GraphQL responses, and type guards (`lib/type-guards.ts`).
- **Accessibility & UX** – Headless UI for modals (`@headlessui/react`), Heroicons for iconography, toast notifications (`sonner`), and loading states (`components/loading-dots.tsx`).
- **CI/CD** – Scripts for `dev`, `build`, `start`, and `prettier` linting. No unit‑test framework is configured; the `test` script merely runs `prettier:check`.
- **Environment configuration** – Sensitive Shopify credentials (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_REVALIDATION_SECRET`) and deployment metadata (`SITE_NAME`) are injected via environment variables.
- **SEO & discoverability** – Automatic metadata generation, OpenGraph images, a static sitemap (`app/sitemap.ts`), and a `robots.txt` (`app/robots.ts`).

**Ambiguities and Insufficient Evidence**

- The README mentions alternative commerce providers but the repository contains only Shopify‑specific code (`lib/shopify`). It is unclear whether any generic “provider abstraction” exists for easy swapping.
- The `test` script only runs `prettier:check`, indicating a lack of automated unit or integration tests. It is uncertain if testing is performed elsewhere (e.g., manually or via CI on Vercel).
- The `package.json` and `pnpm-lock.yaml` suggest a minimal dev dependency set; the absence of testing libraries or linting tools beyond Prettier may limit code quality assurance visibility.
- The `lib/shopify` folder includes many fragments and queries, but the exact GraphQL schema version or endpoint URL (`SHOPIFY_GRAPHQL_API_ENDPOINT` from `lib/constants.ts`) is not detailed in the supplied intelligence.
- The repository’s README includes a note about Next.js Commerce v1, but the current codebase appears to be v2 (based on App Router usage). The relationship between the two versions is not clarified.

Overall, the repository is a production‑ready, server‑side rendered e‑commerce template centered on Shopify, built with modern Next.js patterns, TypeScript, and a component‑driven UI. It provides a full storefront experience with cart management, search, product details, and content pages, while leaving checkout and order management to external services. The architecture emphasizes performance, SEO, and developer experience, with clear separation between client‑side UI and server‑side data fetching.
