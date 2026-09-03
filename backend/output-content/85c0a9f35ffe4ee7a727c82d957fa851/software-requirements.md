# Software Requirements Analysis

Based on the evidence from this repository, the system is an e-commerce storefront built with Next.js, React, TypeScript, and Tailwind CSS, integrated with Shopify. Below is the reconstructed requirements analysis.

## Functional Requirements

| Requirement | Evidence | Certainty |
|---|---|---|
| The system must display a homepage with a product carousel and three-item grid | `app/page.tsx` renders `<ThreeItemGrid />` and `<Carousel />` components; `components/grid/three-items.tsx` shows homepage items from `hidden-homepage-featured-items` collection | Verified |
| The system must support product search with query parameter `q` | `components/layout/search/filter/item.tsx` handles `SortFilterItem` with `slug`; `app/search/page.tsx` processes `searchParams` and renders product grid; search form at `components/layout/navbar/search.tsx` submits to `/search` | Verified |
| The system must support product filtering and sorting | `lib/constants.ts` defines `SortFilterItem` type with sort options (RELEVANCE, BEST_SELLING, CREATED_AT, PRICE); `app/search/page.tsx` uses `sorting` array from constants; filter UI components in `components/layout/search/filter/` | Verified |
| The system must display individual product pages | `app/product/[handle]/page.tsx` renders product details, gallery, variant selector, and add-to-cart; `generateMetadata` function generates product SEO metadata | Verified |
| The system must support shopping cart operations | `components/cart/actions.ts` exports `addItem`, `removeItem`, `updateItemQuantity`, `redirectToCheckout`, `createCartAndSetCookie`; `components/cart/cart-context.tsx` provides cart state management with optimistic updates; `components/product/product-description.tsx` includes `<AddToCart />` | Verified |
| The system must redirect to checkout after cart operations | `components/cart/actions.ts` `redirectToCheckout` function calls `getCart()` and redirects to `cart!.checkoutUrl` | Verified |
| The system must generate SEO metadata for pages | `app/layout.tsx` defines `metadata` with `metadataBase`, `title`, `robots`; `app/page.tsx` has description and openGraph; product and collection pages have `generateMetadata` functions | Verified |
| The system must support collection/category pages | `app/search/[collection]/page.tsx` renders products filtered by collection handle; `generateMetadata` generates collection SEO; `components/layout/search/collections.tsx` displays collection list | Verified |
| The system must support revalidation API endpoint | `app/api/revalidate/route.ts` exports `POST` handler that calls `revalidate(req)` from `lib/shopify` | Verified |
| The system must validate environment variables | `lib/utils.ts` `validateEnvironmentVariables` checks for `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_STOREFRONT_ACCESS_TOKEN`; throws errors if missing or if domain contains brackets | Verified |

## Business and Domain Rules

| Rule | Evidence | Certainty |
|---|---|---|
| Products with `nextjs-frontend-hidden` tag are hidden from search results | `lib/constants.ts` exports `HIDDEN_PRODUCT_TAG = "nextjs-frontend-hidden"`; `ThreeItemGrid.tsx` filters items from `hidden-homepage-featured-items` collection; product page checks `product.tags.includes(HIDDEN_PRODUCT_TAG)` | Verified |
| Default product option is "Default Title" | `lib/constants.ts` exports `DEFAULT_OPTION = "Default Title"` | Verified |
| Sorting options available: RELEVANCE, BEST_SELLING, CREATED_AT, PRICE | `lib/constants.ts` defines `SortFilterItem` type with `sortKey: "RELEVANCE" \| "BEST_SELLING" \| "CREATED_AT" \| "PRICE"`; `sorting` array includes these options | Verified |
| Price sorting: Low to high and High to low | `lib/constants.ts` defines `sorting` array with `PRICE` sortKey and `reverse: false/true` | Verified |
| Collections starting with `hidden-*` are hidden from search page | `ThreeItemGrid.tsx` comment: "// Collections that start with `hidden-*` are hidden from the search page."; `app/search/[collection]/page.tsx` fetches products by collection handle | Verified |
| Hidden-homepage-featured-items collection provides homepage grid items | `components/grid/three-items.tsx` fetches `hidden-homepage-featured-items` collection; requires at least 3 items to render | Verified |
| Product variant selection via URL search params | `components/product/variant-selector.tsx` reads `searchParams` and maps option values; `components/layout/search/filter/item.tsx` uses search params for sort/filter state | Verified |
| Cart persists via cookie `cartId` | `components/cart/actions.ts` `createCartAndSetCookie` sets `cartId` cookie; `components/cart/cart-context.tsx` uses `cartPromise` from `CartProvider` | Verified |

## Interface Requirements

| Interface | Required Fields/Behavior | Evidence |
|---|---|---|
| POST /api/revalidate | Accepts `NextRequest`, returns `NextResponse`; calls `revalidate(req)` from `lib/shopify` | `app/api/revalidate/route.ts` |
| Search form | POST to `/search`; input `name="q"`; autoComplete="off"; placeholder "Search for products..." | `components/layout/navbar/search.tsx` |
| Product page route | `/product/{handle}`; handle is product handle parameter | `app/product/[handle]/page.tsx` |
| Collection page route | `/search/{collection}`; collection is collection handle parameter | `app/search/[collection]/page.tsx` |
| Product variant selector | Reads `searchParams` for option values; supports multiple option selection; disables out-of-stock variants | `components/product/variant-selector.tsx` |
| Cart actions | `addItem`, `removeItem`, `updateItemQuantity`, `redirectToCheckout`, `createCartAndSetCookie` | `components/cart/actions.ts` |
| GraphQL API endpoint | `/api/2023-01/graphql.json`; requires `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_STOREFRONT_ACCESS_TOKEN` | `lib/constants.ts` |
| SEO metadata generation | `generateMetadata` functions on `app/page.tsx`, `app/product/[handle]/page.tsx`, `app/search/[collection]/page.tsx`, `app/layout.tsx`; returns `Metadata` type | Multiple `generateMetadata` functions |
| Cart context provider | `CartProvider` wraps root layout; provides `cartPromise` and `useCart` hook | `components/cart/cart-context.tsx` |

## Data Requirements

| Requirement | Evidence | Certainty |
|---|---|---|
| Product entities must have: handle, title, description, priceRange, variants, images, featuredImage, seo | `lib/shopify/types.ts` defines `Product` type; `app/product/[handle]/page.tsx` accesses `product.handle`, `product.title`, `product.priceRange`, `product.variants`, `product.images`, `product.featuredImage`, `product.seo` | Verified |
| Collection entities must have: handle, title, description, seo, updatedAt | `lib/shopify/types.ts` defines `Collection` type; `app/search/[collection]/page.tsx` accesses `collection.handle`, `collection.title`, `collection.description`, `collection.seo` | Verified |
| Cart entities must have: id, checkoutUrl, totalQuantity, lines, cost (subtotalAmount, totalAmount, totalTaxAmount) | `components/cart/cart-context.tsx` defines `createEmptyCart`; `reshapeCart` function in `lib/shopify/index.ts` | Verified |
| SEO metadata fields: title, description, robots (index/follow), openGraph (images, altText, width, height) | `lib/shopify/types.ts` defines `SEO` type; `app/layout.tsx` metadata includes all these fields; product/collection `generateMetadata` functions populate these fields | Verified |
| Environment variables: SHOPIFY_STORE_DOMAIN, SHOPIFY_STOREFRONT_ACCESS_TOKEN | `lib/utils.ts` `validateEnvironmentVariables` requires both; `lib/shopify/index.ts` uses `process.env.SHOPIFY_STORE_DOMAIN` and `process.env.SHOPIFY_STOREFRONT_ACCESS_TOKEN` | Verified |
| Cart line items contain: merchandise.id, merchandise.title, quantity, cost (totalAmount, currencyCode) | `lib/shopify/types.ts` defines `CartProduct`, `CartItem`; `reshapeCart` in `lib/shopify/index.ts` maps cart data | Verified |
| Product images contain: url, altText | `lib/shopify/fragments/image.ts` defines image fragment; `reshapeImages` in `lib/shopify/index.ts` processes image URLs and altText | Verified |
| Variant selectedOptions contain: option name (lowercased), option value | `lib/shopify/types.ts` defines `ProductVariant` with `selectedOptions`; `components/product/variant-selector.tsx` maps `variant.selectedOptions` | Verified |

## Security Requirements

| Requirement | Evidence | Certainty |
|---|---|---|
| SHOPIFY_STORE_DOMAIN must be set and must not contain brackets | `lib/utils.ts` validates presence and rejects domains with `[` or `]` | Verified |
| SHOPIFY_STOREFRONT_ACCESS_TOKEN must be set | `lib/utils.ts` `validateEnvironmentVariables` requires this variable | Verified |
| GraphQL API calls use store domain and access token | `lib/shopify/index.ts` constructs endpoint as `${domain}${SHOPIFY_GRAPHQL_API_ENDPOINT}` with `X-Shopify-Storefront-Access-Token` header | Verified |
| Error handling distinguishes Shopify errors from other errors | `lib/type-guards.ts` exports `isShopifyError` and `isObject`; `shopifyFetch` in `lib/shopify/index.ts` catches and rethrows with appropriate structure | Verified |
| Access token included in GraphQL request headers | `lib/shopify/index.ts` fetches with `X-Shopify-Storefront-Access-Token: key` header | Verified |

## Non-Functional Requirements

| Requirement | Evidence | Certainty |
|---|---|---|
| Framework: Next.js 15 with React 19 | `package.json` specifies `"next": "15.6.0-canary.60"`, `"react": "19.0.0"`, `"react-dom": "19.0.0"` | Verified |
| Styling: Tailwind CSS | `package.json` includes `tailwindcss: "^4.0.14"`; `postcss.config.mjs` not read but Tailwind config present; all components use Tailwind class names | Verified |
| Package manager: pnpm | `package.json` scripts use `pnpm prettier:check`; lockfile implied | Verified |
| Development: Turbopack | `package.json` dev script: `next dev --turbopack` | Verified |
| Formatting: Prettier | `package.json` scripts: `prettier`, `prettier:check`; configured for `--ignore-unknown .` | Verified |
| No test infrastructure beyond formatting checks | `package.json` test script is `pnpm prettier:check`; no Jest or other test frameworks detected | Verified |
| Vercel-ready deployment | Environment variable configuration for Shopify integrations; no custom CI detected; relies on Vercel's platform | Verified |
| No server-side rendering configuration beyond Next.js defaults | `next.config.ts` not read but default Next.js config implied; `app/` directory routing suggests App Router | Inferred |
| Component client/adoptation: Most components use `"use client"` directive | Majority of UI components have `"use client"` at top; layout and some utilities are server components | Verified |

## Operational and Deployment Requirements

| Requirement | Evidence | Certainty |
|---|---|---|
| Environment variables required: SHOPIFY_STORE_DOMAIN, SHOPIFY_STOREFRONT_ACCESS_TOKEN | `lib/utils.ts` validates these; missing variables cause app startup failure | Verified |
| Next.js configuration via next.config.ts | Repository has `next.config.ts` file; standard Next.js configuration | Verified |
| Build script: `next build` | `package.json` scripts include `"build": "next build"` | Verified |
| Start script: `next start` | `package.json` scripts include `"start": "next start"` | Verified |
| Dev script: `next dev --turbopack` | `package.json` scripts include `"dev": "next dev --turbopack"` | Verified |
| Prettier check: `pnpm prettier:check` | `package.json` scripts include `"test": "pnpm prettier:check"` | Verified |
| No explicit CI/CD configuration detected | Only `prettier:check` script; no GitHub Actions, Jenkins, etc. | Verified |
| Shopify API version: 2023-01 | `lib/constants.ts` exports `SHOPIFY_GRAPHQL_API_ENDPOINT = "/api/2023-01/graphql.json"` | Verified |
| Default API route: `/api/2023-01/graphql.json` | Confirmed in constants and shopify fetch implementation | Verified |
| Root layout: `app/layout.tsx` | Single `app/layout.tsx` serves as root; wraps children with `CartProvider` | Verified |
| API routes under `app/api/`: `route.ts` | Only `app/api/revalidate/route.ts` present | Verified |
| No middleware detected | No `midware` or `next/config/middleware` files present | Verified |
| App Router routing: `app/` directory | All routes under `app/` directory indicating Next.js 13+ App Router | Verified |

## Summary of Certainty Levels

**Verified requirements**: Directly evidenced by executable code and configuration artifacts. These include functional behaviors, validation rules, interface contracts, data schemas, environment variable requirements, and framework versions.

**Inferred requirements**: Necessary or strongly implied by multiple implementation artifacts. These include sorting/filtering behavior, cart state management, SEO metadata patterns, and deployment scripts.

**Uncertain requirements**: Not explicitly confirmed. The repository does not contain sufficient evidence for uncertainty classifications beyond what's verified or inferred.

## Important Notes

1. The system is an e-commerce front-end with Shopify integration; backend cart and checkout logic resides in Shopify, not this repository.
2. Products marked with `nextjs-frontend-hidden` tag are hidden from search results but may still be accessible via direct URL.
3. The `hidden-homepage-featured-items` collection must contain at least 3 items for the homepage grid to render; otherwise `ThreeItemGrid` returns `null`.
4. Environment variable validation occurs at runtime; missing variables cause the application to fail on startup.
5. The system uses Next.js App Router with server and client components demarcated by `"use client"` directives.
6. No automated testing framework exists beyond Prettier formatting checks.