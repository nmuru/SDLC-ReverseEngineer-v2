# Repository Research Brief

Research schema: 3
Phase: repository-wide

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
# Next.js Commerce — Repository Summary

## Repository Identity and Domain

This is **Next.js Commerce**, a high-performance, server-rendered e-commerce template built on the Next.js App Router. It is the official Vercel-maintained Shopify version of the commerce template, designed as a starter kit that can be forked and adapted for alternative commerce providers by swapping the `lib/shopify` implementation. The application is a React 19 + Next.js 15 (Canary) project using TypeScript, Tailwind CSS, and the Geist font system, with a strong emphasis on React Server Components, Suspense, and server-side data fetching.

## Business and Domain Concepts

The application models a standard e-commerce domain with the following core concepts:

- **Products** with variants, options, images, pricing, and SEO metadata
- **Collections** (product categories) with filtering and sorting capabilities
- **Carts** supporting creation, item addition, quantity editing, and removal
- **Pages** (static content pages managed via Shopify)
- **Menus** (navigation structures)
- **Search** with collection-based browsing and filter/sort controls

The domain model is defined in `lib/shopify/types.ts`, which exports typed interfaces for `Cart`, `CartItem`, `Product`, `ProductVariant`, `ProductOption`, `Collection`, `Image`, `Money`, `Menu`, `Page`, and `SEO`, along with corresponding Shopify GraphQL operation result types.

## Users, Actors, and System Boundaries

**Actors:** End customers browsing and purchasing products online.

**System boundaries:** The application is a frontend storefront that integrates with Shopify's Storefront API as its backend commerce engine. It does not implement its own product catalog, inventory, or order management — these are delegated to Shopify. The application also integrates with Vercel's platform (deployment, revalidation) and uses cookies for cart persistence.

## Major Capabilities and Workflows

### Product Browsing
- Home page (`app/page.tsx`) renders a carousel and a three-item grid of featured products
- Collection browsing via `app/search/[collection]/page.tsx` with filter and sort controls
- Product detail pages at `app/product/[handle]/page.tsx` with image galleries, variant selectors, and related products
- Static page rendering for content pages at `app/[page]/page.tsx`

### Search and Filtering
- Search page (`app/search/page.tsx`) with a sidebar layout containing collection navigation and filter controls
- Filter dropdowns and sort options driven by `lib/constants.ts` (sorting definitions, hidden product tags)
- URL-based filtering using `next/navigation` for query parameter management

### Cart Management
- Full cart lifecycle: create, add items, edit quantities, remove items, and redirect to checkout
- Cart state managed client-side via React context (`components/cart/cart-context.tsx`) with a reducer pattern
- Cart modal in the navbar showing real-time updates with optimistic UI patterns
- Server actions in `components/cart/actions.ts` handle all cart mutations with cache revalidation

### Content Management
- Dynamic sitemap generation (`app/sitemap.ts`) pulling from Shopify pages and collections
- OpenGraph image generation for social sharing across pages, collections, and products
- Footer menus dynamically populated from Shopify menu data

## Key Entities, State, and Relationships

The central entity is the **Cart**, which maintains client-side state through a React context provider with actions for adding, removing, and updating items. Cart operations trigger server-side mutations via Server Actions, which in turn call Shopify's GraphQL API and revalidate cached data.

**Product** entities are fetched server-side and rendered through Server Components, with variant selection handled client-side via URL parameter updates. **Collections** serve as category groupings with associated filtering and sorting metadata.

The **Shopify integration layer** (`lib/shopify/index.ts`) acts as the single gateway for all data operations, exporting functions like `getCart`, `getCollection`, `getProducts`, `getPage`, `getMenu`, and cart mutation functions (`addToCart`, `removeFromCart`, `updateCart`, `createCart`).

## External Integrations

- **Shopify Storefront API**: Primary backend for all product, cart, collection, page, and menu data. Configured via `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, and `SHOPIFY_GRAPHQL_API_ENDPOINT` environment variables.
- **Vercel Platform**: Deployment target with `VERCEL_PROJECT_PRODUCTION_URL` for absolute URL generation. Includes a revalidation webhook at `app/api/revalidate/route.ts` secured by `SHOPIFY_REVALIDATION_SECRET`.
- **Next.js Image Optimization**: Used throughout for product and gallery images.

## Implementation Characteristics

- **App Router architecture** with React Server Components as the default, client components used selectively for interactivity
- **Server Actions** for all cart mutations, leveraging `next/cache` for revalidation
- **TypeScript** with strict typing throughout, including generated Shopify operation types
- **Tailwind CSS v4** with container queries and typography plugins
- **Geist font** for typography
- **Headless UI** and **Heroicons** for accessible UI components and icons
- **Sonner** for toast notifications
- **Environment validation** via `lib/utils.ts` ensuring required variables are present at build time
- **Error boundaries** at the app level (`app/error.tsx`)

## Ambiguities and Gaps

- The `test` script only runs Prettier formatting checks — there are no unit, integration, or E2E tests in the repository
- The parse summary indicates all 66 source files failed to parse, suggesting the static analysis tooling may have limitations with the Next.js 15 Canary + React 19 toolchain
- No authentication or user account management is present — this is a guest-only storefront
- No payment processing integration beyond redirecting to Shopify Checkout
- The `lib/type-guards.ts` file suggests error handling for Shopify API responses, but the full error recovery strategy is not evident from the supplied intelligence
- No analytics, tracking, or A/B testing integrations are visible
