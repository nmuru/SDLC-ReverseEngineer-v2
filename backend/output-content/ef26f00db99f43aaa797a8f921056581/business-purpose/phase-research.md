# Phase Research Brief

Research schema: 3
Phase: business-purpose

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
Next.js Commerce is a high-performance, server-rendered ecommerce application template built on the Next.js App Router with Shopify as the primary commerce provider. The repository is designed as a production-ready starting point for developers and teams seeking to launch a modern, SEO-optimized online store quickly while leveraging React 19's latest patterns (Server Components, Server Actions, Suspense, useOptimistic). Vercel maintains the Shopify version actively, but the architecture explicitly supports swapping the `lib/shopify` data layer for alternative providers (BigCommerce, Ecwid, Geins) with minimal changes to the rest of the codebase.

**Target Users and Value Proposition**

The template serves multiple audiences: Vercel customers deploying ecommerce sites, merchants/brands adopting a headless commerce architecture, and commerce platform providers who want to offer Next.js-based storefronts. The core value is delivering a complete, type-safe ecommerce foundation—handling product catalogs, cart state, search, and SEO—without requiring developers to build these capabilities from scratch. By combining Next.js's rendering optimizations with Shopify's GraphQL API, it aims to provide excellent Core Web Vitals and a smooth developer experience.

**Major Capabilities**

The application implements a full shopping cart system via `CartProvider`/`useCart` context with reducer-based state management (`components/cart/cart-context.tsx`), supporting add, remove, and quantity update operations. Cart mutations are Server Actions (`components/cart/actions.ts`) that interact with Shopify and invalidate caches, ensuring data consistency. The Shopify integration layer (`lib/shopify/`) exposes typed GraphQL fragments and operations for products, collections, carts, menus, and pages, with functions like `getProduct`, `getProducts`, `getCollection`, `getCollections`, `getMenu`, and `getPages` (`lib/shopify/index.ts`). Pages are generated with SEO metadata and OpenGraph images (`app/[page]/opengraph-image.tsx`, `app/product/[handle]/page.tsx`), and sitemaps are built server-side using Shopify data (`app/sitemap.ts`). Search and filtering are handled through a unified interface with collection filtering, sort options, and path-based filter items (`components/layout/search/filter/`). The system also includes a revalidation API route (`app/api/revalidate/route.ts`) for incremental static regeneration triggered by Shopify webhooks.

**System Boundaries**

The application is bounded by: (1) the Next.js frontend using React Server Components and file-based routing (`app/`); (2) the Shopify GraphQL backend accessed via storefront access tokens (`lib/shopify/`); (3) Vercel as the deployment platform, using environment variables like `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_STOREFRONT_ACCESS_TOKEN`; and (4) Tailwind CSS for styling. The cart system is client-side, while product and page data are fetched server-side. The architecture enforces a clean separation between the commerce data layer, shared UI components, and page-level logic.

**Uncertainties**

The supplied repository summary notes that 66 source files were marked as "unavailable," meaning only symbol-level metadata was extracted. Consequently, specific implementation details—such as exact caching strategies, error handling patterns, revalidation webhook mechanics, and UI/UX design nuances—cannot be confirmed from the provided intelligence alone. The README mentions a v1 version with different architecture, but the current template's relationship to that legacy codebase is not detailed. Performance benchmarks or real-world usage metrics are also absent.
