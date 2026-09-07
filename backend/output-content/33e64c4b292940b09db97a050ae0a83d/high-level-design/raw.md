---
model: openrouter/free
---

# High-Level Design Documentation

## System Overview

The repository implements a **production-grade, server-rendered ecommerce storefront** built on the Next.js App Router with Shopify as the commerce provider. The architecture follows Vercel's "Next.js Commerce" pattern, combining **React Server Components (RSC)**, **Server Actions**, **Suspense boundaries**, and `useOptimistic` to deliver a high-performance shopping experience with minimal client-side JavaScript.

The system is fundamentally a **content-and-commerce delivery platform** that translates Shopify GraphQL data into an SEO-optimized, type-safe storefront with a full-featured shopping cart.

---

## Logical Component Map

### 1. Shopify Integration Layer (`lib/shopify/`)

**Responsibility**: The sole abstraction boundary for all external commerce data — every piece of catalog, cart, content, and navigation data flows through this layer to Shopify's Storefront API.

**Key files**: `lib/shopify/index.ts`, `lib/shopify/types.ts`, `lib/shopify/fragments/`, `lib/shopify/queries/`, `lib/shopify/mutations/`

**Inputs**: HTTP requests from server components; Shopify GraphQL endpoint (`SHOPIFY_GRAPHQL_API_ENDPOINT`) authenticated via `SHOPIFY_STOREFRONT_ACCESS_TOKEN`.

**Outputs**: Typed domain objects (`Product`, `Cart`, `Collection`, `Menu`, `Page`, `Image`) conforming to the shape defined in `lib/shopify/types.ts`.

**Internal structure**:

- `index.ts` — Composes query and mutation modules; exposes the public API surface (`getProduct`, `getProducts`, `getCollections`, `getCart`, `addToCart`, `removeFromCart`, `updateCart`, `createCart`, `getMenu`, `getPage`, `revalidate`). Also implements the `revalidate()` function called by the API route.
- `queries/` — Individual GraphQL query builders (`cart.ts`, `collection.ts`, `menu.ts`, `page.ts`, `product.ts`) using reusable fragments.
- `mutations/` — GraphQL mutation builders (`cart.ts`) for cart operations.
- `fragments/` — Reusable GraphQL selection sets (`cart.ts`, `product.ts`, `image.ts`, `seo.ts`) ensuring consistent data shapes across queries and mutations.
- `types.ts` — Canonical TypeScript interfaces defining the domain model shared across server and client code.

**Data transformation**: Raw Shopify GraphQL responses are reshaped via `reshapeProduct()`, `reshapeProducts()`, `reshapeCart()`, `reshapeCollection()`, `reshapeCollections()`, and `reshapeImages()` functions — normalizing Shopify's connection-based pagination edges/nodes into flat arrays, deriving computed paths, filtering hidden products, and filling default tax amounts.

**Caching strategy**:

- **Private cache** (`"use cache: private"`) with `cacheTag(TAGS.cart)` and `cacheLife("seconds")` for `getCart()` — per-user, short-lived.
- **Public cache** (`"use cache"`) with `cacheTag(TAGS.collections, TAGS.products)` and `cacheLife("days")` for product/collection data — shared, longer-lived.

---

### 2. Cart Management System (`components/cart/`)

**Responsibility**: Manages the complete shopping cart lifecycle — creation, item manipulation, quantity updates, removal, and checkout redirection — with optimistic UI updates and server-side persistence via Shopify.

**Key files**: `components/cart/cart-context.tsx`, `components/cart/actions.ts`, `components/cart/modal.tsx`, `components/cart/add-to-cart.tsx`, `components/cart/delete-item-button.tsx`, `components/cart/edit-item-quantity-button.tsx`, `components/cart/open-cart.tsx`

**Architecture**: Hybrid server/client pattern.

- **Server side** (`actions.ts`): All cart mutations are Server Actions that invoke `lib/shopify` functions (`addToCart`, `removeFromCart`, `updateCart`, `createCart`) and trigger Next.js cache revalidation via `updateTag(TAGS.cart)`.
- **Client side** (`cart-context.tsx`): A React Context + `useOptimistic` hook provides an immediately responsive cart UI. The initial cart state is a `Promise<Cart | undefined>` passed from the server-side `getCart()` call in `app/layout.tsx`. User interactions dispatch optimistic updates to the context reducer before the server Action confirms.

**State ownership**:

| Scope | Owner | Mechanism |
|-------|-------|-----------|
| Server | Shopify-hosted cart | `cartId` cookie identified and read by `lib/shopify` on each mutation |
| Client | Optimistic cart snapshot | `useOptimistic` inside `CartProvider`; local-first, server reconciliation on next render |

**Key operations flow**:

1. User clicks "Add to Cart" → `addCartItem()` dispatches optimistic `ADD_ITEM` action
2. Server Action `addItem()` calls `lib/shopify.addToCart()` → Shopify → `updateTag(TAGS.cart)` invalidates cache
3. Next server render fetches fresh cart via `getCart()` and hydrates context

**Checkout**: `redirectToCheckout()` Server Action fetches the cart's `checkoutUrl` and performs a redirect to Shopify's hosted checkout — no custom payment flow exists in the repository.

---

### 3. Product Catalog & Display

**Responsibility**: Renders product information across multiple contexts — home page feature grids, product detail pages, related products, and collection browsing — with SEO-optimized metadata and structured data.

**Key display components**:

| File | Purpose |
|------|---------|
| `components/grid/three-items.tsx` | Featured 3-product layout (one large + two smaller tiles) |
| `components/grid/tile.tsx` | Layout primitives for product tile grids |
| `components/layout/product-grid-items.tsx` | Generic product grid rendering |
| `components/product/product-description.tsx` | Product detail information panel |
| `components/product/variant-selector.tsx` | Product variant selection UI |
| `components/carousel.tsx` | Rotating featured products on homepage |

**Key route pages**:

| File | Route | Function |
|------|-------|----------|
| `app/product/[handle]/page.tsx` | `/product/[handle]` | Product detail page |
| `app/[page]/page.tsx` | `/[page]` | Dynamic CMS pages |
| `app/search/[collection]/page.tsx` | `/search/[collection]` | Collection browsing |

**Product detail page** (`app/product/[handle]/page.tsx`):

- Server Component fetching product data via `getProduct(handle)` and `getProductRecommendations(id)`
- Generates JSON-LD structured data (`Product` schema with `AggregateOffer`)
- Uses `Suspense` boundaries around `Gallery` and `ProductDescription` for progressive rendering
- Renders a responsive layout: gallery (60%) on large screens, product details (40%) alongside
- Related products section fetched at component level (nested async)

**Metadata generation**: Each product page implements `generateMetadata()` to produce SEO-optimized `<title>`, `<meta name="description">`, `<meta name="robots">`, and OpenGraph image data.

---

### 4. Search & Filtering (`components/layout/search/`, `app/search/`)

**Responsibility**: Provides faceted product search with collection-based filtering, sorting, and pagination — enabling users to navigate the catalog efficiently.

**Key files**: `app/search/page.tsx`, `app/search/[collection]/page.tsx`, `components/layout/search/filter/index.tsx`, `components/layout/search/collections.tsx`, `components/layout/search/filter/dropdown.tsx`, `components/layout/search/filter/item.tsx`

**Data flow**:

- `app/search/page.tsx` → Server Component calls `lib/shopify.getCollections()` and `lib/shopify.getProducts()` to populate the page
- `app/search/[collection]/page.tsx` → Dynamic route for SEO-friendly category pages; calls `getCollection(handle)` and `getCollectionProducts({ collection })`
- Filter components (`collections.tsx`, `filter/index.tsx`) render available collections and filter controls
- All filtering/sorting parameters flow through URL search params → server re-renders with filtered data

---

### 5. Navigation & Layout (`components/layout/navbar/`, `app/layout.tsx`)

**Responsibility**: Provides the persistent site shell — header navigation, mobile menu, footer, and global providers — shared across all pages.

**Key files**: `app/layout.tsx`, `components/layout/navbar/index.tsx`, `components/layout/navbar/mobile-menu.tsx`, `components/layout/navbar/search.tsx`, `components/layout/footer.tsx`, `components/layout/footer-menu.tsx`

**Root layout** (`app/layout.tsx`):

- Async Server Component
- Calls `getCart()` (unawaited, passed as `cartPromise` to `CartProvider`)
- Wraps entire application with `CartProvider` and `Toaster` (sonner notifications)
- Renders `Navbar`, `<main>{children}</main>`, `WelcomeToast`
- Configures metadata with `metadataBase`, title template, robots policy, and font class

**Navbar** (`components/layout/navbar/index.tsx`):

- Fetches site menu via `lib/shopify.getMenu()`
- Contains responsive mobile menu (`mobile-menu.tsx`) and inline search (`search.tsx`)
- Menu items have `/collections` → `/search` path rewriting applied by `lib/shopify/getMenu()`

**Footer** (`components/layout/footer.tsx`):

- Renders footer menu links (also fetched via Shopify)
- Contains copyright and site information

---

### 6. Dynamic Content Pages (`app/[page]/page.tsx`, `lib/shopify/queries/page.ts`)

**Responsibility**: Provides a catch-all route for CMS-driven static pages (About, Contact, Terms, etc.) using Shopify's Online Store pages API.

**Key files**: `app/[page]/page.tsx`, `lib/shopify/queries/page.ts`, `lib/shopify/fragments/seo.ts`

**Behavior**:

- Dynamic route `app/[page]/page.tsx` catches arbitrary page handles
- Calls `getPage(handle)` which fetches from Shopify's `pagesByHandle` query
- Generates SEO metadata via `generateMetadata()` using Shopify's `seo` field
- Renders OpenGraph images (`app/[page]/opengraph-image.tsx`) for social sharing

---

### 7. Revalidation & Cache Management (`app/api/revalidate/route.ts`)

**Responsibility**: Secured webhook endpoint that invalidates Next.js cache when Shopify content changes — maintaining data consistency after product/collection updates.

**Key file**: `app/api/revalidate/route.ts`, `lib/shopify/index.ts` (revalidate function)

**Flow**:

```
Shopify publishes webhook (products/update, collections/create, etc.)
    ↓
POST to /api/revalidate
    ↓
app/api/revalidate/route.ts → lib/shopify.revalidate(req)
    ↓ validates SHOPIFY_REVALIDATION_SECRET
    ↓ reads x-shopify-topic header
    ↓ calls revalidateTag(TAGS.products) or revalidateTag(TAGS.collections)
    ↓
Next.js invalidates matching cached server components
    ↓
Next request re-fetches fresh data from Shopify
    ↓
User sees updated content
```

---

### 8. Site Configuration & Infrastructure (`app/sitemap.ts`, `lib/constants.ts`, `lib/utils.ts`)

**Responsibility**: Provides global configuration including environment variable bindings, URL construction utilities, cache tag constants, and search engine sitemap generation.

**Key files**: `app/sitemap.ts`, `lib/constants.ts`, `lib/utils.ts`, `next.config.ts`

---

## Major Data and Control Flows

### Flow 1: Initial Page Load (Server-Rendered)

```
Browser Request
    ↓
Next.js App Router matches route
    ↓
app/layout.tsx (RootLayout) — async Server Component
    ↓ calls getCart() (unawaited Promise)
    ↓
lib/shopify/index.ts → getCart()
    ↓ reads cartId cookie → shopifyFetch() → Shopify GraphQL
    ↓
CartProvider receives cartPromise → useOptimistic hydrates
    ↓
Navbar fetches menu via lib/shopify.getMenu()
    ↓
Page-specific Server Component fetches its data
    ↓
React renders HTML with data embedded in server-rendered markup
    ↓
Browser receives HTML, hydrates client components
```

**Evidence**: `app/layout.tsx` passes `cartPromise={getCart()}` without awaiting; `app/product/[handle]/page.tsx` calls `getProduct()` and `getProductRecommendations()` directly; `components/grid/three-items.tsx` calls `getCollectionProducts()` server-side.

---

### Flow 2: Add-to-Cart with Optimistic Update

```
User clicks "Add to Cart" on product page
    ↓
add-to-cart.tsx triggers addCartItem(variant, product)
    ↓
cart-context.tsx: useOptimistic dispatch → ADD_ITEM action
    ↓
cartReducer updates local optimisticCart state instantly
    ↓
UI immediately shows updated cart count/modal
    ↓
Server Action addItem() invoked (components/cart/actions.ts)
    ↓
lib/shopify.addToCart([{merchandiseId, quantity}])
    ↓ reads cartId cookie → POST to Shopify GraphQL
    ↓
Shopify returns updated cart
    ↓ updateTag(TAGS.cart) invalidates cache
    ↓
Next.js re-fetches getCart() on next server render
    ↓
CartProvider rehydrates with fresh server data
```

**Evidence**: `components/cart/add-to-cart.tsx` → `components/cart/cart-context.tsx` `addCartItem()` → `components/cart/actions.ts` `addItem()` → `lib/shopify/index.ts` `addToCart()` + `updateTag(TAGS.cart)`.

---

### Flow 3: Cart Quantity Update

```
User changes item quantity in cart modal
    ↓
edit-item-quantity-button.tsx triggers updateCartItem(merchandiseId, updateType)
    ↓
cart-context.tsx: useOptimistic dispatch → UPDATE_ITEM action
    ↓
cartReducer updates line item quantity optimistically
    ↓
Server Action updateItemQuantity() invoked
    ↓
lib/shopify.updateCart() or removeFromCart() called
    ↓ updateTag(TAGS.cart) invalidates cache
    ↓
Next.js re-fetches fresh cart
```

---

### Flow 4: Content Revalidation via Shopify Webhooks

```
Shopify publishes webhook (products/update, collections/create, etc.)
    ↓
POST to /api/revalidate
    ↓
app/api/revalidate/route.ts → lib/shopify.revalidate(req)
    ↓ validates SHOPIFY_REVALIDATION_SECRET
    ↓ reads x-shopify-topic header
    ↓ calls revalidateTag(TAGS.products) or revalidateTag(TAGS.collections)
    ↓
Next.js invalidates matching cached server components
    ↓
Next request re-fetches fresh data from Shopify
    ↓
User sees updated content
```

---

## Dependency Direction and Component Relationships

```
app/layout.tsx ──→ components/cart/cart-context.tsx (CartProvider)
app/layout.tsx ──→ components/layout/navbar/index.tsx
app/layout.tsx ──→ lib/shopify/index.ts (getCart)

app/product/[handle]/page.tsx ──→ lib/shopify/index.ts (getProduct, getProductRecommendations)
app/product/[handle]/page.tsx ──→ components/product/product-description.tsx
app/product/[handle]/page.tsx ──→ components/product/variant-selector.tsx
app/product/[handle]/page.tsx ──→ components/grid/tile.tsx (related products)

app/search/page.tsx ──→ lib/shopify/index.ts (getCollections, getProducts)
app/search/page.tsx ──→ components/layout/search/collections.tsx
app/search/page.tsx ──→ components/layout/search/filter/index.tsx

components/cart/actions.ts ──→ lib/shopify/index.ts (addToCart, removeFromCart, updateCart, getCart)
components/cart/cart-context.tsx ──→ components/cart/actions.ts (indirect via Server Actions)
components/cart/modal.tsx ──→ components/cart/actions.ts, components/cart/cart-context.tsx

lib/shopify/index.ts ──→ lib/shopify/mutations/cart.ts
lib/shopify/index.ts ──→ lib/shopify/queries/{cart,collection,menu,page,product}.ts
lib/shopify/queries/*.ts ──→ lib/shopify/fragments/*.ts
lib/shopify/fragments/*.ts ──→ lib/shopify/fragments/*.ts (product → image, seo; cart → product)

app/api/revalidate/route.ts ──→ lib/shopify/index.ts (revalidate)
components/grid/three-items.tsx ──→ lib/shopify/index.ts (getCollectionProducts)
```

**Dependency direction**:

| Direction | Description |
|-----------|-------------|
| Outward dependency | `app/` → `components/` → `lib/shopify/` → Shopify API |
| Inward dependency | `lib/shopify/` has no dependencies on `app/` or `components/` — it is the pure data layer |
| Circular dependency | None detected. `components/cart/` depends on `lib/shopify/`, and `lib/shopify/` is a leaf dependency |
| Shared state | Cart state flows via React Context (`CartProvider`); cart persistence relies on Shopify server-side carts identified by `cartId` cookie |

---

## State Ownership and Lifecycle

| State | Owner | Lifecycle | Evidence |
|-------|-------|-----------|----------|
| **Cart items (server)** | Shopify (via `cartId` cookie) | Persistent until checkout; revalidated via `updateTag(TAGS.cart)` | `lib/shopify/index.ts` `getCart()`, `addToCart()` |
| **Cart items (client)** | `CartProvider` + `useOptimistic` | Transient; resets on full page reload; synced to server on next render | `components/cart/cart-context.tsx` `useOptimistic(initialCart, cartReducer)` |
| **Product data** | Next.js cache (public) | `cacheLife("days")`; invalidated via `revalidateTag(TAGS.products)` | `lib/shopify/index.ts` `"use cache"`, `cacheTag(TAGS.products)` |
| **Collection data** | Next.js cache (public) | `cacheLife("days")`; invalidated via `revalidateTag(TAGS.collections)` | `lib/shopify/index.ts` `"use cache"`, `cacheTag(TAGS.collections)` |
| **Menu data** | Next.js cache (public) | `cacheLife("days")` | `lib/shopify/index.ts` `getMenu()` `"use cache"` |
| **cartId** | Browser cookie | Persists across sessions; read by `lib/shopify` on each cart operation | `components/cart/actions.ts` `cookies().get("cartId")` |
| **Page content** | Shopify (Online Store pages) | Fetched on each request for `getPage()` (no cache tag); fetched for `getPages()` | `lib/shopify/index.ts` `getPage()`, `getPages()` |

---

## External System Boundaries

### Shopify Storefront API

| Aspect | Detail |
|--------|--------|
| Interface | GraphQL POST endpoint at `{SHOPIFY_STORE_DOMAIN}{SHOPIFY_GRAPHQL_API_ENDPOINT}` |
| Authentication | `X-Shopify-Storefront-Access-Token` header using `SHOPIFY_STOREFRONT_ACCESS_TOKEN` |
| Scope | All product, collection, cart, menu, and page data; all cart mutations |
| Error handling | `shopifyFetch()` catches errors, detects Shopify-specific errors via `isShopifyError()`, and re-throws structured errors with `cause`, `status`, `message`, and `query` metadata |
| Failure propagation | Server components will propagate errors to Next.js error handling; client actions return error strings for UI display |

### Shopify Admin API (Webhooks)

| Aspect | Detail |
|--------|--------|
| Interface | `POST /api/revalidate` endpoint receiving `x-shopify-topic` headers and `secret` query parameter |
| Purpose | Cache invalidation notifications for content changes |
| Authentication | Validates `SHOPIFY_REVALIDATION_SECRET` query parameter |
| Topics handled | `collections/create\|delete\|update`, `products/create\|delete\|update` |
| All other topics | Returns `{ status: 200 }` without revalidation |

### Vercel/Deployment Platform

| Aspect | Detail |
|--------|--------|
| Configuration | `VERCEL_PROJECT_PRODUCTION_URL`, `SITE_NAME` env vars configure canonical URLs and metadata |
| Build | `next build` with `turbopack` in dev mode (`next dev --turbopack`) |
| Deployment | Vercel-optimized with server components running on the edge/Vercel infrastructure |

### Browser (Client)

| Aspect | Detail |
|--------|--------|
| Hydration boundary | `app/layout.tsx` is the server component root; client components are limited to interactive islands (`CartProvider`, `Navbar`, `modal.tsx`, `variant-selector.tsx`, `mobile-menu.tsx`) |
| Client-side state | `useOptimistic` for cart, `useContext` for cart access, `sonner` for toast notifications |

---

## Synchronous and Asynchronous Design

### Synchronous workflows

- **Server component data fetching**: `getProduct()`, `getCollection()`, `getMenu()`, `getCart()` — all execute synchronously within the server component render (the data fetch happens during render, not via client-side fetch)
- **Cart reducer**: `cartReducer()` is a pure synchronous function mapping `CartAction` to `Cart` state
- **Metadata generation**: `generateMetadata()` in page components runs synchronously at build/render time

### Asynchronous boundaries

- **Server Actions**: Cart mutations (`addItem`, `removeItem`, `updateItemQuantity`, `redirectToCheckout`, `createCartAndSetCookie`) are Server Actions — invoked from client components, execute on the server, and return promises
- **`useOptimistic`**: Client-side state updates are applied immediately (synchronously) while the server Action completes asynchronously; reconciliation occurs on next server render
- **`getCart()` in layout**: The `cartPromise` is intentionally unawaited in `app/layout.tsx` — React Suspense handles the Promise asynchronously while the shell renders
- **Nested async components**: `RelatedProducts` in `app/product/[handle]/page.tsx` is an async component called inside the default export, fetching recommendations independently

### Cache timing

| Cache type | TTL | Purpose |
|------------|-----|---------|
| Private cache | `cacheLife("seconds")` | Cart — very short TTL ensuring cart data freshness |
| Public cache | `cacheLife("days")` | Products, collections, menus — longer TTL for catalog performance |

| Tag | Usage |
|-----|-------|
| `TAGS.cart` | Cart-specific cache entries |
| `TAGS.products` | Product catalog cache entries |
| `TAGS.collections` | Collection cache entries |

---

## Important Design Patterns

### React Server Components Pattern

All page components and layouts are async Server Components by default (`"use client"` not present). Data fetching occurs directly in components using `async/await` without needing `useEffect` or client-side fetching libraries. This eliminates waterfall client-side data fetching and produces SEO-optimized HTML.

### Optimistic Updates Pattern

The cart uses `useOptimistic` to provide instant UI feedback. The client maintains an optimistic state that mirrors the server state, and updates are applied locally before server confirmation. This pattern is evidenced by `useOptimistic(initialCart, cartReducer)` in `cart-context.tsx`.

### Provider Pattern for Global State

`CartProvider` wraps the entire application via `app/layout.tsx`, providing cart state to all descendant components via React Context. This avoids prop drilling and enables any client component to access cart functions via `useCart()`.

### Fragment Composition Pattern

GraphQL queries are composed from reusable fragments. `queries/cart.ts` imports `fragments/cart.ts`, `fragments/product.ts`; `fragments/product.ts` imports `fragments/image.ts`, `fragments/seo.ts`. This ensures consistent field selection and DRY query construction.

### Data Reshaping / Normalization Pattern

All Shopify GraphQL responses pass through reshape functions (`reshapeProduct`, `reshapeCart`, `reshapeCollections`) before being returned. This normalizes Shopify's connection-based pagination into flat arrays, adds computed properties (like `path` for collections), and fills default values — creating a stable domain model independent of Shopify's API shape changes.

### Route-Based Rendering Pattern

Dynamic routes use Next.js App Router conventions:

| File | Route | Purpose |
|------|-------|---------|
| `app/product/[handle]/page.tsx` | `/product/[handle]` | Product detail with `generateMetadata()` for SEO |
| `app/search/[collection]/page.tsx` | `/search/[collection]` | Collection browsing pages |
| `app/[page]/page.tsx` | `/[page]` | Catch-all route for CMS pages |
| `app/api/revalidate/route.ts` | `/api/revalidate` | API route for webhook handling |

---

## Coupling, Cohesion, and Boundary Analysis

### Strong Cohesion

- `lib/shopify/` forms a tightly cohesive module — all Shopify interaction is encapsulated here
- `components/cart/` forms a cohesive subsystem — all cart logic (state, actions, UI) is isolated
- `lib/shopify/fragments/` and `queries/` are tightly coupled — queries import fragments directly

### Loose Coupling

- `lib/shopify/index.ts` has zero dependencies on `app/` or `components/` — it is a pure data layer
- Page components depend on `lib/shopify/index.ts` but not on each other
- Display components (`Grid`, `GridTileImage`) are generic and do not depend on Shopify-specific logic

### Potential Coupling Concerns

1. **No abstraction over Shopify**: The entire `lib/shopify/` namespace is Shopify-specific. There is no `lib/commerce/` abstraction layer despite the README referencing alternative providers (BigCommerce, Ecwid). Swapping providers would require replacing the entire module.

2. **Cookie dependency for cart**: The `cartId` cookie is read server-side in `lib/shopify/index.ts` and `components/cart/actions.ts`. This creates a tight coupling between cart functionality and cookie-based session management.

3. **Direct `next/cache` usage**: The `cacheTag` and `revalidateTag` usage is deeply integrated into the business logic layer, creating a dependency on Next.js-specific caching APIs.

### Boundary Violations (Minor)

- `app/layout.tsx` calls `getCart()` server-side, but the returned Promise is passed directly to `CartProvider` — this means the layout component acts as both a data consumer and a data provider, blurring the data-fetching boundary slightly
- `lib/shopify/index.ts` imports `next/headers` and `next/cache` directly, mixing business logic with framework-specific APIs

---

## Failure Propagation

### External API Failures

- `shopifyFetch()` catches errors and re-throws structured `{ error, query }` or `{ cause, status, message, query }` objects
- Server components will propagate these to Next.js error boundaries (if present) or crash the render
- Server Actions return error strings (e.g., `"Error adding item to cart"`) for client-side display

### Cart-Specific Failures

| Scenario | Behavior |
|----------|----------|
| No `cartId` cookie | `getCart()` returns `undefined` (graceful degradation, not an error) |
| Add/remove/update errors | Server Actions catch errors and return error strings |
| Redirect to checkout with undefined cart | Will throw — `redirectToCheckout()` assumes cart exists (`cart!.checkoutUrl`) |

### Revalidation Failures

| Scenario | Response |
|----------|----------|
| Invalid secret | `{ status: 401 }` |
| Non-matching topic | `{ status: 200 }` without action |
| Valid request | Invalidates tags and returns `{ status: 200, revalidated: true }` |

---

## Summary of Key Architectural Decisions

| Decision | Rationale | Evidence |
|----------|-----------|----------|
| Server Components for all pages | SEO optimization, reduced client bundle, direct data access | `app/layout.tsx`, `app/product/[handle]/page.tsx`, `app/search/page.tsx` |
| React Context + useOptimistic for cart | Instant UI feedback, global accessibility without prop drilling | `components/cart/cart-context.tsx` |
| Shopify as sole commerce provider | Template is Shopify-specific with no abstraction layer | `lib/shopify/` namespace, env variables |
| Cookie-based cart identification | Server-side cart persistence tied to browser session | `cookies().get("cartId")` in `lib/shopify/index.ts` |
| Next.js App Router cache tags | Granular cache invalidation on content changes | `cacheTag(TAGS.products)`, `revalidateTag(TAGS.collections)` |
| Fragment composition for GraphQL | DRY query construction, consistent data shapes | `fragments/` directory imported by `queries/` and `mutations/` |
| Data reshaping layer | Stable domain model decoupled from Shopify API changes | `reshapeProduct`, `reshapeCart`, `reshapeCollections` in `lib/shopify/index.ts` |

---

## Uncertainties and Gaps

- **Error boundary placement**: No explicit `error.tsx` or `loading.tsx` files were identified in the tracked topology. Suspense boundaries exist inline (`<Suspense>` in product page) but their completeness across all routes is unclear.

- **Cache tag granularity**: The `revalidateTag()` calls use coarse tags (`TAGS.products`, `TAGS.collections`). It is uncertain whether more granular per-product or per-collection tags are used.

- **Order/Checkout flow**: The checkout redirects entirely to Shopify's hosted checkout (`cart!.checkoutUrl`). No order confirmation, order history, or post-purchase logic exists in the repository.

- **Provider abstraction**: While the README references alternative commerce providers, the `lib/shopify/` namespace is Shopify-specific with no `lib/commerce/` abstraction layer or adapter pattern visible in the current codebase.

- **Inventory and pricing logic**: Complex variant pricing, inventory checks, discount codes, and tax calculation are all delegated to Shopify — the repository only reshapes and displays Shopify-computed values.

- **66 files unparsed**: Tree-sitter parsing was unavailable for 66 files, meaning some business rules, configuration details, or component behaviors may exist that are not reflected in this analysis.
