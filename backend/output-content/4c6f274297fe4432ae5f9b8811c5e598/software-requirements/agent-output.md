Now I have a comprehensive understanding of the repository. Let me write the requirements analysis.

# Software Requirements Analysis
## Next.js Commerce (Shopify Edition)

---

### Executive Summary

This repository implements **Next.js Commerce**—a high-performance, server-rendered ecommerce storefront template built on Next.js 15 (App Router), React 19, TypeScript, and Tailwind CSS 4. It integrates with **Shopify** as a headless commerce backend via the Shopify Storefront GraphQL API. The system is designed for deployment on Vercel with support for incremental static regeneration, React Server Components, Server Actions, and optimistic UI updates.

---

## 1. Functional Requirements

### 1.1 Product Discovery & Browsing

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| FR-1.1 | The system shall display a homepage featuring a configurable hero grid of featured products and a horizontally scrolling carousel of products. | `app/page.tsx` renders `ThreeItemGrid` (fetches from `hidden-homepage-featured-items` collection) and `Carousel` (fetches from `hidden-homepage-carousel` collection) | Verified |
| FR-1.2 | The system shall provide a search interface allowing users to search products by keyword with real-time results. | `app/search/page.tsx` accepts `q` query param, calls `getProducts({ query: searchValue })` | Verified |
| FR-1.3 | The system shall display products in a paginated grid with configurable sort order (Relevance, Trending, Latest, Price Low-High, Price High-Low). | `app/search/page.tsx` and `app/search/[collection]/page.tsx` use `sorting` constants; `ProductGridItems` renders grid | Verified |
| FR-1.4 | The system shall allow browsing products by collection with collection-specific product listings. | `app/search/[collection]/page.tsx` calls `getCollectionProducts({ collection, sortKey, reverse })` | Verified |
| FR-1.5 | The system shall display individual product detail pages with title, description, price range, image gallery, variant selection, and add-to-cart action. | `app/product/[handle]/page.tsx` fetches product via `getProduct(handle)`, renders `Gallery`, `VariantSelector`, `AddToCart` | Verified |
| FR-1.6 | The system shall display related product recommendations on product detail pages. | `RelatedProducts` component in `app/product/[handle]/page.tsx` calls `getProductRecommendations(id)` | Verified |
| FR-1.7 | The system shall support filtering products by collection via a sidebar navigation. | `components/layout/search/collections.tsx` fetches collections via `getCollections()`, renders `FilterList` with collection paths | Verified |
| FR-1.8 | The system shall render static content pages (e.g., About, Contact) fetched from Shopify Pages. | `app/[page]/page.tsx` calls `getPage(handle)` and renders body HTML via `Prose` component | Verified |

### 1.2 Shopping Cart Management

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| FR-2.1 | The system shall maintain a persistent shopping cart associated with an anonymous session via a `cartId` cookie. | `lib/shopify/index.ts`: `createCart()`, `getCart()` reads `cartId` from cookies; `CartProvider` passes cart promise | Verified |
| FR-2.2 | The system shall allow adding a product variant to the cart with quantity 1 via an "Add to Cart" action. | `components/cart/add-to-cart.tsx` calls `addCartItem` (optimistic) and `addItem` server action; `lib/shopify/index.ts` `addToCart()` mutation | Verified |
| FR-2.3 | The system shall allow incrementing, decrementing, and removing line items from the cart. | `components/cart/edit-item-quantity-button.tsx` and `delete-item-button.tsx` call `updateItemQuantity` / `removeItem` server actions with optimistic updates | Verified |
| FR-2.4 | The system shall display the cart in a slide-over modal showing line items, quantities, per-line pricing, subtotal, tax (placeholder), shipping notice, and total. | `components/cart/modal.tsx` renders cart lines with `Price`, `EditItemQuantityButton`, `DeleteItemButton`, and totals | Verified |
| FR-2.5 | The system shall optimistically update the cart UI before server confirmation, with rollback on error. | `components/cart/cart-context.tsx` uses `useOptimistic` with `cartReducer` for `ADD_ITEM`/`UPDATE_ITEM` actions | Verified |
| FR-2.6 | The system shall redirect the user to Shopify's hosted checkout when proceeding to checkout. | `components/cart/actions.ts` `redirectToCheckout()` calls `getCart()` then `redirect(cart.checkoutUrl)` | Verified |
| FR-2.7 | The system shall automatically create a cart and set the `cartId` cookie when the cart modal opens and no cart exists. | `components/cart/modal.tsx` `useEffect` calls `createCartAndSetCookie()` when `!cart` | Verified |
| FR-2.8 | The system shall auto-open the cart modal when an item is successfully added. | `components/cart/modal.tsx` `useEffect` watches `cart.totalQuantity` and opens modal when it increases | Verified |

### 1.3 Product Variant Selection

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| FR-3.1 | The system shall present product options (e.g., Size, Color) as selectable buttons, preserving other option selections in the URL. | `components/product/variant-selector.tsx` reads/writes option values via `useSearchParams` and `router.replace()` | Verified |
| FR-3.2 | The system shall disable unavailable variant combinations and visually indicate out-of-stock options. | `VariantSelector` computes `isAvailableForSale` by matching current option combination against `combinations` array; renders disabled with strikethrough style | Verified |
| FR-3.3 | The system shall pre-select the default variant when only one variant exists or no options are defined. | `VariantSelector` returns `null` for `hasNoOptionsOrJustOneOption`; `AddToCart` falls back to `defaultVariantId` | Verified |
| FR-3.4 | The system shall update the "Add to Cart" button state (enabled/disabled/label) based on selected variant availability. | `components/cart/add-to-cart.tsx` `SubmitButton` shows "Out Of Stock", "Add To Cart", or "Please select an option" based on `availableForSale` and `selectedVariantId` | Verified |

### 1.4 Navigation & Menus

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| FR-4.1 | The system shall render a responsive header with logo, navigation menu (desktop), search input (desktop), and cart button. | `components/layout/navbar/index.tsx` renders `LogoSquare`, menu links from `getMenu('next-js-frontend-header-menu')`, `Search`, `CartModal` | Verified |
| FR-4.2 | The system shall provide a mobile-responsive drawer menu with search and navigation links. | `components/layout/navbar/mobile-menu.tsx` uses `@headlessui/react` `Dialog`/`Transition` for slide-in panel | Verified |
| FR-4.3 | The system shall render a footer with menu links, copyright notice, and Vercel deployment link. | `components/layout/footer.tsx` fetches `getMenu('next-js-frontend-footer-menu')`, renders `FooterMenu` | Verified |
| FR-4.4 | The system shall highlight the active menu item in the footer based on current route. | `components/layout/footer-menu.tsx` `FooterMenuItem` uses `usePathname()` to set `active` state | Verified |

### 1.5 SEO & Metadata

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| FR-5.1 | The system shall generate dynamic page metadata (title, description, Open Graph) for product, collection, search, and content pages. | `generateMetadata` exports in `app/product/[handle]/page.tsx`, `app/search/[collection]/page.tsx`, `app/[page]/page.tsx` | Verified |
| FR-5.2 | The system shall include JSON-LD structured data (Product schema) on product detail pages. | `app/product/[handle]/page.tsx` renders `<script type="application/ld+json">` with `@type: Product` and `AggregateOffer` | Verified |
| FR-5.3 | The system shall generate a sitemap.xml including homepage, all collections, all products, and all pages with last-modified dates. | `app/sitemap.ts` calls `getCollections()`, `getProducts()`, `getPages()` and returns `MetadataRoute.Sitemap` | Verified |
| FR-5.4 | The system shall generate a robots.txt allowing all crawlers and referencing the sitemap. | `app/robots.ts` returns rules with `sitemap: ${baseUrl}/sitemap.xml` | Verified |
| FR-5.5 | The system shall generate dynamic Open Graph images for product, collection, and content pages using Next.js ImageResponse. | `app/product/[handle]/opengraph-image.tsx`, `app/search/[collection]/opengraph-image.tsx`, `app/[page]/opengraph-image.tsx` | Verified |
| FR-5.6 | The system shall respect the `nextjs-frontend-hidden` product tag to exclude products from search/indexing while allowing direct access. | `lib/shopify/index.ts` `reshapeProduct()` filters by `HIDDEN_PRODUCT_TAG`; `generateMetadata` sets `robots.index/follow` to false for hidden products | Verified |

### 1.6 Content Revalidation

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| FR-6.1 | The system shall accept Shopify webhook callbacks to trigger on-demand revalidation of product and collection cache tags. | `app/api/revalidate/route.ts` POST handler calls `lib/shopify/index.ts` `revalidate()` function | Verified |
| FR-6.2 | The system shall verify a shared secret (`SHOPIFY_REVALIDATION_SECRET`) before performing revalidation. | `revalidate()` checks `secret` query param against `process.env.SHOPIFY_REVALIDATION_SECRET` | Verified |
| FR-6.3 | The system shall revalidate the `collections` cache tag for collection create/delete/update webhooks and `products` tag for product webhooks. | `revalidate()` inspects `x-shopify-topic` header and calls `revalidateTag(TAGS.collections)` or `revalidateTag(TAGS.products)` | Verified |

### 1.7 User Experience Enhancements

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| FR-7.1 | The system shall display a dismissible welcome toast on first visit (persisted via cookie for 1 year). | `components/welcome-toast.tsx` checks `document.cookie` for `welcome-toast=2`, shows `sonner` toast with deploy link | Verified |
| FR-7.2 | The system shall support dark mode via CSS media query with Tailwind `dark:` variants throughout. | `app/globals.css` `@media (prefers-color-scheme: dark)` sets `color-scheme: dark`; all components use `dark:` classes | Verified |
| FR-7.3 | The system shall provide loading skeletons for async content (search, collections, product grid, cart). | `app/search/loading.tsx`, `components/layout/search/collections.tsx` skeleton, `components/layout/navbar/search.tsx` `SearchSkeleton` | Verified |
| FR-7.4 | The system shall display a user-friendly error boundary with retry action. | `app/error.tsx` renders "Oh no!" message with "Try Again" button calling `reset()` | Verified |

---

## 2. Business & Domain Rules

| ID | Rule | Evidence | Certainty |
|----|------|----------|-----------|
| BR-1 | Products tagged with `nextjs-frontend-hidden` in Shopify are excluded from search results, collection listings, and sitemap, but remain accessible via direct URL. | `lib/constants.ts` `HIDDEN_PRODUCT_TAG`; `lib/shopify/index.ts` `reshapeProduct(filterHiddenProducts=true)`; `getCollections()` filters collections with handle starting with `hidden-` | Verified |
| BR-2 | Collections with handles starting with `hidden-` are excluded from the search page navigation but used for homepage content (featured items, carousel). | `lib/shopify/index.ts` `getCollections()` filters `!collection.handle.startsWith('hidden')`; `ThreeItemGrid` and `Carousel` explicitly query `hidden-homepage-featured-items` and `hidden-homepage-carousel` | Verified |
| BR-3 | A cart is created lazily on first interaction (opening cart modal or adding first item) and persisted via `cartId` cookie. | `components/cart/modal.tsx` `useEffect` calls `createCartAndSetCookie()`; `lib/shopify/index.ts` `createCart()` mutation | Verified |
| BR-4 | Cart line quantities cannot go below 1; decrementing to 0 removes the line item. | `lib/shopify/index.ts` `updateCartItem()` returns `null` when `newQuantity === 0`; `actions.ts` `updateItemQuantity` calls `removeFromCart` when quantity === 0 | Verified |
| BR-5 | Product variant selection is constrained to valid, available-for-sale combinations only. | `VariantSelector` computes `combinations` from variants and checks `filtered.every(...combination.availableForSale)` | Verified |
| BR-6 | The "All" collection (handle="") is a synthetic collection representing all products, always listed first in the collection filter. | `lib/shopify/index.ts` `getCollections()` prepends `{ handle: '', title: 'All', path: '/search', ... }` | Verified |
| BR-7 | Price display uses the store's currency code with narrow symbol formatting via `Intl.NumberFormat`. | `components/price.tsx` uses `new Intl.NumberFormat(undefined, { style: 'currency', currency: currencyCode, currencyDisplay: 'narrowSymbol' })` | Verified |
| BR-8 | Tax amount is not calculated client-side; the system displays a placeholder "Calculated at checkout" for shipping and relies on Shopify checkout for final totals. | `components/cart/modal.tsx` renders "Shipping: Calculated at checkout"; `reshapeCart` ensures `totalTaxAmount` exists (defaults to 0) | Verified |
| BR-9 | Product images are sourced from Shopify CDN (`cdn.shopify.com`) with AVIF/WebP format optimization. | `next.config.ts` `images.remotePatterns` allows `cdn.shopify.com/s/files/**`; `formats: ['image/avif', 'image/webp']` | Verified |

---

## 3. Interface Requirements

### 3.1 HTTP API (Server Actions & Route Handlers)

| ID | Interface | Contract | Evidence |
|----|-----------|----------|----------|
| IF-1 | `POST /api/revalidate` | **Headers:** `x-shopify-topic` (required), `x-shopify-hmac-sha256` (ignored)<br>**Query:** `secret` (required, must match `SHOPIFY_REVALIDATION_SECRET`)<br>**Response:** `200 { status: 200 }` or `200 { status: 200, revalidated: true, now: timestamp }` or `401 { status: 401 }` | `app/api/revalidate/route.ts`, `lib/shopify/index.ts` `revalidate()` |
| IF-2 | Server Action `addItem(selectedVariantId: string)` | **Input:** `selectedVariantId` (required)<br>**Output:** `string` error message or `void` (success)<br>**Side effect:** Calls Shopify `cartLinesAdd`, updates `cart` cache tag | `components/cart/actions.ts` `addItem()` |
| IF-3 | Server Action `removeItem(merchandiseId: string)` | **Input:** `merchandiseId` (required)<br>**Output:** `string` error message or `void` | `components/cart/actions.ts` `removeItem()` |
| IF-4 | Server Action `updateItemQuantity({ merchandiseId, quantity })` | **Input:** `merchandiseId` (string), `quantity` (number ≥ 0)<br>**Output:** `string` error message or `void`<br>**Behavior:** quantity=0 → remove; item not in cart + quantity>0 → add | `components/cart/actions.ts` `updateItemQuantity()` |
| IF-5 | Server Action `redirectToCheckout()` | **Output:** `never` (redirects to `cart.checkoutUrl`) | `components/cart/actions.ts` `redirectToCheckout()` |
| IF-6 | Server Action `createCartAndSetCookie()` | **Side effect:** Creates Shopify cart, sets `cartId` cookie<br>**Output:** `void` | `components/cart/actions.ts` `createCartAndSetCookie()` |

### 3.2 Shopify Storefront GraphQL API (External Dependency)

| ID | Operation | Purpose | Evidence |
|----|-----------|---------|----------|
| IF-7 | `cartCreate` | Create new cart | `lib/shopify/mutations/cart.ts` |
| IF-8 | `cartLinesAdd` | Add line items to cart | `lib/shopify/mutations/cart.ts` |
| IF-9 | `cartLinesUpdate` | Update line item quantities | `lib/shopify/mutations/cart.ts` |
| IF-10 | `cartLinesRemove` | Remove line items from cart | `lib/shopify/mutations/cart.ts` |
| IF-11 | `cart(id: ID!)` | Fetch cart by ID | `lib/shopify/queries/cart.ts` |
| IF-12 | `product(handle: String!)` | Fetch single product by handle | `lib/shopify/queries/product.ts` |
| IF-13 | `products(sortKey, reverse, query, first: 100)` | Search/list products | `lib/shopify/queries/product.ts` |
| IF-14 | `productRecommendations(productId: ID!)` | Fetch related products | `lib/shopify/queries/product.ts` |
| IF-15 | `collection(handle: String!)` | Fetch collection by handle | `lib/shopify/queries/collection.ts` |
| IF-16 | `collections(first: 100, sortKey: TITLE)` | List all collections | `lib/shopify/queries/collection.ts` |
| IF-17 | `collection.products(sortKey, reverse, first: 100)` | Fetch products in collection | `lib/shopify/queries/collection.ts` |
| IF-18 | `menu(handle: String!)` | Fetch navigation menu by handle | `lib/shopify/queries/menu.ts` |
| IF-19 | `pageByHandle(handle: String!)` | Fetch page by handle | `lib/shopify/queries/page.ts` |
| IF-20 | `pages(first: 100)` | List all pages | `lib/shopify/queries/page.ts` |

### 3.3 Client-Side URL Conventions

| ID | Route Pattern | Parameters | Evidence |
|----|---------------|------------|----------|
| IF-21 | `/` | — | `app/page.tsx` |
| IF-22 | `/search` | `q` (search query), `sort` (sort slug) | `app/search/page.tsx` |
| IF-23 | `/search/[collection]` | `collection` (handle), `sort` (sort slug) | `app/search/[collection]/page.tsx` |
| IF-24 | `/product/[handle]` | `handle` (product handle), option query params (e.g., `?size=M&color=Red`) | `app/product/[handle]/page.tsx`, `VariantSelector` |
| IF-25 | `/[page]` | `page` (page handle) | `app/[page]/page.tsx` |
| IF-26 | `/api/revalidate` | `secret` (query) | `app/api/revalidate/route.ts` |

### 3.4 Environment Configuration Interface

| Variable | Required | Purpose | Evidence |
|----------|----------|---------|----------|
| `SHOPIFY_STORE_DOMAIN` | Yes | Shopify store subdomain (e.g., `myshop.myshopify.com`) | `.env.example`, `lib/utils.ts` `validateEnvironmentVariables()` |
| `SHOPIFY_STOREFRONT_ACCESS_TOKEN` | Yes | Storefront API access token (public) | `.env.example`, `lib/utils.ts` |
| `SHOPIFY_REVALIDATION_SECRET` | Yes | Shared secret for webhook revalidation | `.env.example`, `lib/shopify/index.ts` `revalidate()` |
| `COMPANY_NAME` | No | Copyright holder name in footer | `.env.example`, `components/layout/footer.tsx` |
| `SITE_NAME` | Yes | Site title for metadata, logo, OG | `.env.example`, `app/layout.tsx`, `components/opengraph-image.tsx` |
| `VERCEL_PROJECT_PRODUCTION_URL` | No (Vercel-injected) | Base URL for sitemap, robots, OG images | `lib/utils.ts` `baseUrl` |

---

## 4. Data Requirements

### 4.1 Core Domain Entities

| Entity | Key Attributes | Source | Persistence |
|--------|----------------|--------|-------------|
| **Product** | `id`, `handle`, `title`, `description`, `descriptionHtml`, `availableForSale`, `priceRange` (min/max), `options[]`, `variants[]`, `images[]`, `featuredImage`, `seo`, `tags[]`, `updatedAt` | Shopify GraphQL `product` fragment | Shopify (external); cached via Next.js `cacheTag(TAGS.products)` with `cacheLife('days')` |
| **ProductVariant** | `id`, `title`, `availableForSale`, `selectedOptions[]`, `price` | Shopify GraphQL `product` fragment | Shopify |
| **ProductOption** | `id`, `name`, `values[]` | Shopify GraphQL `product` fragment | Shopify |
| **Collection** | `handle`, `title`, `description`, `seo`, `updatedAt`, `path` (derived: `/search/{handle}`) | Shopify GraphQL `collection` fragment | Shopify; cached `cacheTag(TAGS.collections)` `days` |
| **Cart** | `id`, `checkoutUrl`, `cost` (subtotal, total, tax), `lines[]`, `totalQuantity` | Shopify GraphQL `cart` fragment | Shopify (server-side); client cookie `cartId`; cached `cacheTag(TAGS.cart)` `seconds` (private) |
| **CartItem** | `id`, `quantity`, `cost.totalAmount`, `merchandise` (variant + product ref) | Shopify GraphQL `cart` fragment | Shopify |
| **Menu** | `title`, `path` (derived from Shopify URL) | Shopify GraphQL `menu` query | Shopify; cached `days` |
| **Page** | `id`, `title`, `handle`, `body`, `bodySummary`, `seo`, `createdAt`, `updatedAt` | Shopify GraphQL `page` fragment | Shopify |
| **Image** | `url`, `altText`, `width`, `height` | Shopify GraphQL `image` fragment | Shopify CDN |

### 4.2 Data Transformation Rules

| Rule | Description | Evidence |
|------|-------------|----------|
| DR-1 | Shopify `Connection<T>` (edges/nodes) → flat `T[]` | `lib/shopify/index.ts` `removeEdgesAndNodes()` |
| DR-2 | Shopify `Cart` → local `Cart` with flattened `lines` and guaranteed `totalTaxAmount` | `reshapeCart()` |
| DR-3 | Shopify `Collection` → local `Collection` with added `path` | `reshapeCollection()` |
| DR-4 | Shopify `Product` → local `Product` with flattened `variants`, `images`, filtered by `HIDDEN_PRODUCT_TAG` | `reshapeProduct()` |
| DR-5 | Shopify `Image` → local `Image` with fallback `altText` (`${productTitle} - ${filename}`) | `reshapeImages()` |
| DR-6 | Shopify menu URLs → local paths (strip domain, `/collections`→`/search`, `/pages`→``) | `getMenu()` in `lib/shopify/index.ts` |

### 4.3 Caching Strategy

| Data Type | Cache Tag | Cache Life | Scope | Evidence |
|-----------|-----------|------------|-------|----------|
| Products | `products` | `days` | Shared (public) | `getProduct`, `getProducts`, `getProductRecommendations`, `getCollectionProducts` |
| Collections | `collections` | `days` | Shared | `getCollection`, `getCollections`, `getCollectionProducts` |
| Cart | `cart` | `seconds` | Private (per-user) | `getCart` uses `"use cache: private"` |
| Menus | `collections` | `days` | Shared | `getMenu` |

---

## 5. Security Requirements

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| SR-1 | The system shall authenticate Shopify Storefront API requests using a `X-Shopify-Storefront-Access-Token` header (public token). | `lib/shopify/index.ts` `shopifyFetch()` includes header with `key = process.env.SHOPIFY_STOREFRONT_ACCESS_TOKEN` | Verified |
| SR-2 | The system shall validate the `SHOPIFY_REVALIDATION_SECRET` query parameter on the revalidation endpoint before invalidating caches. | `lib/shopify/index.ts` `revalidate()` returns 401 if secret missing or mismatch | Verified |
| SR-3 | The system shall store the cart identifier in an HTTP-only cookie (implied by Next.js `cookies()` API usage). | `lib/shopify/index.ts` reads/writes via `(await cookies()).get('cartId')` / `.set('cartId', ...)` | Verified |
| SR-4 | The system shall not expose the Storefront Access Token or Revalidation Secret to the client bundle. | Both variables used only in server-side code (`lib/shopify/index.ts`, `app/api/revalidate/route.ts`, `app/sitemap.ts`) | Verified |
| SR-5 | The system shall validate required environment variables at build/startup and fail fast with actionable error messages. | `lib/utils.ts` `validateEnvironmentVariables()` throws if `SHOPIFY_STORE_DOMAIN` or `SHOPIFY_STOREFRONT_ACCESS_TOKEN` missing | Verified |
| SR-6 | The system shall sanitize Shopify-provided HTML content before rendering (via `dangerouslySetInnerHTML` with trusted source assumption). | `components/prose.tsx` and `app/[page]/page.tsx` use `dangerouslySetInnerHTML={{ __html: product.descriptionHtml }}` — trusted Shopify content | Inferred |
| SR-7 | The system shall always respond 200 to Shopify webhook retries (per Shopify requirement) even on validation failure. | `revalidate()` returns `NextResponse.json({ status: 401 })` with 200 HTTP status | Verified |

> **Gap/Note:** No authentication/authorization for storefront visitors (anonymous shopping only). No user accounts, login, or role-based access control evidenced. This is consistent with a headless Shopify storefront where authentication is handled at checkout by Shopify.

---

## 6. Non-Functional Requirements

### 6.1 Performance & Scalability

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| NFR-1 | The system shall leverage React Server Components and server-side rendering for initial page loads to minimize client bundle size and improve TTFB. | `app/` routes are async server components; `app/layout.tsx` fetches cart server-side; no client hydration for static content | Verified |
| NFR-2 | The system shall use Next.js caching with tag-based invalidation (`products`, `collections`, `cart`) for GraphQL responses. | `lib/shopify/index.ts` uses `cacheTag()`, `cacheLife()`, `revalidateTag()`; `"use cache: private"` for cart | Verified |
| NFR-3 | The system shall implement optimistic UI updates for cart mutations to eliminate perceived latency. | `components/cart/cart-context.tsx` `useOptimistic` with `cartReducer` | Verified |
| NFR-4 | The system shall prefetch navigation links on hover/viewport entry via Next.js `prefetch={true}`. | `Link` components throughout use `prefetch={true}` (default) or explicit | Verified |
| NFR-5 | The system shall optimize images via Next.js Image component with automatic format selection (AVIF/WebP) and responsive sizing. | `next.config.ts` image formats; `GridTileImage`, `Gallery` use `fill`/`sizes` props | Verified |
| NFR-6 | The system shall support partial pre-rendering (PPR) and inline CSS for critical path optimization. | `next.config.ts` `experimental: { ppr: true, inlineCss: true, useCache: true }` | Verified |
| NFR-7 | The system shall stream product recommendations and gallery images via `Suspense` boundaries. | `app/product/[handle]/page.tsx` wraps `ProductDescription` and `Gallery` in `Suspense` | Verified |

### 6.2 Reliability & Resilience

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| NFR-8 | The system shall gracefully handle missing Shopify configuration by returning empty data instead of crashing (development fallback). | `getCollections()`, `getProducts()`, `getProduct()`, `getCollectionProducts()` return `[]`/`undefined` with console log when `!endpoint` | Verified |
| NFR-9 | The system shall handle Shopify GraphQL errors with structured error objects containing status, message, cause, and query. | `shopifyFetch()` catches errors, normalizes to `{ status, message, cause, query }` | Verified |
| NFR-10 | The system shall provide a client-side error boundary with retry capability for runtime errors. | `app/error.tsx` renders friendly message with `reset()` button | Verified |
| NFR-11 | The system shall ensure webhook revalidation endpoint always returns 200 to prevent Shopify retry storms. | `revalidate()` returns `NextResponse.json({ status: 401 })` (still 200 HTTP) | Verified |

### 6.3 Observability

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| NFR-12 | The system shall log revalidation events (topic, revalidated flag, timestamp) for debugging. | `revalidate()` returns `{ revalidated: true, now: Date.now() }` and logs invalid secret | Verified |
| NFR-13 | The system shall log skipped GraphQL calls when Shopify is not configured. | `console.log('Skipping getX - Shopify not configured')` in multiple functions | Verified |

### 6.4 Maintainability & Developer Experience

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| NFR-14 | The system shall enforce strict TypeScript with `strict: true`, `noUncheckedIndexedAccess`, and isolated modules. | `tsconfig.json` | Verified |
| NFR-15 | The system shall enforce consistent code formatting via Prettier with Tailwind CSS plugin. | `package.json` scripts `prettier`, `prettier:check`, `test`; `prettier-plugin-tailwindcss` in devDependencies | Verified |
| NFR-16 | The system shall separate Shopify-specific logic into a swappable `lib/shopify` module to support other commerce providers. | README "Providers" section; `lib/shopify` contains all Shopify queries/mutations/fragments/types | Verified |
| NFR-17 | The system shall use GraphQL fragments to avoid duplication and ensure consistent data shapes. | `lib/shopify/fragments/` — `cart.ts`, `product.ts`, `image.ts`, `seo.ts` imported by queries/mutations | Verified |

### 6.5 Compatibility

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| NFR-18 | The system shall target modern browsers (ES2015+) with React 19 and Next.js 15. | `package.json` dependencies; `tsconfig.json` `target: "es2015"`, `lib: ["dom", "dom.iterable", "esnext"]` | Verified |
| NFR-19 | The system shall support Node.js 22+ (per `@types/node: 22.13.10`). | `package.json` devDependencies | Verified |

---

## 7. Operational & Deployment Requirements

| ID | Requirement | Evidence | Certainty |
|----|-------------|----------|-----------|
| OR-1 | The system shall be deployable to Vercel with zero-config (framework detection) and support Vercel Environment Variables for secrets. | README "Running locally" uses `vercel link`, `vercel env pull`; `.env.example` documents required vars | Verified |
| OR-2 | The system shall require `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, and `SHOPIFY_REVALIDATION_SECRET` to be configured in the deployment environment. | `.env.example`, `lib/utils.ts` `validateEnvironmentVariables()` | Verified |
| OR-3 | The system shall support local development via `pnpm dev` (Turbopack) and production build via `pnpm build` / `pnpm start`. | `package.json` scripts | Verified |
| OR-4 | The system shall configure Next.js to allow Shopify CDN images (`cdn.shopify.com/s/files/**`) with AVIF/WebP optimization. | `next.config.ts` `images.remotePatterns` and `formats` | Verified |
| OR-5 | The system shall generate a production sitemap dynamically at request time (`force-dynamic`) using live Shopify data. | `app/sitemap.ts` `export const dynamic = 'force-dynamic'` | Verified |
| OR-6 | The system shall support Shopify webhook registration for `collections/create|delete|update` and `products/create|delete|update` topics pointing to `/api/revalidate`. | `lib/shopify/index.ts` `revalidate()` handles these topics; README references Vercel/Shopify integration guide | Verified |
| OR-7 | The system shall not commit `.env` files (secrets) to version control. | `.gitignore` includes `.env*` but not `.env.example` | Verified |
| OR-8 | The system shall use pnpm as package manager (lockfile `pnpm-lock.yaml`). | `package.json`, `pnpm-lock.yaml` | Verified |
| OR-9 | The system shall use Geist font (Vercel's font) with `next/font` for optimal loading. | `app/layout.tsx` imports `GeistSans` from `geist/font/sans` | Verified |

---

## 8. Discrepancies & Uncertainties

| ID | Observation | Classification |
|----|-------------|----------------|
| UNC-1 | **Cart tax calculation**: `reshapeCart()` synthesizes `totalTaxAmount: { amount: "0.0", ... }` if missing from Shopify response. The cart modal displays this as a line item "Taxes: $0.00" but also shows "Shipping: Calculated at checkout". It is unclear whether Shopify Storefront API returns real tax estimates pre-checkout or if this is a known placeholder. | Uncertain — implementation synthesizes zero; requirement for real-time tax estimate not evidenced |
| UNC-2 | **Inventory checking**: `VariantSelector` disables unavailable combinations based on `availableForSale` from Shopify, but no real-time inventory quantity is displayed or enforced (e.g., "Only 3 left"). | Inferred — only boolean availability evidenced |
| UNC-3 | **Cart persistence across sessions**: The `cartId` cookie has no explicit `maxAge`/`expires` set in `createCartAndSetCookie()`. Reliance on browser session cookie behavior. | Uncertain — cookie options not specified in `cookies().set('cartId', cart.id!)` |
| UNC-4 | **Rate limiting / abuse protection**: No evidenced rate limiting on `addItem`, `updateItemQuantity`, or search endpoints. | Unknown — not implemented in repository |
| UNC-5 | **Analytics / tracking**: No evidenced integration (Google Analytics, Vercel Analytics, etc.) beyond the welcome toast's deploy link. | Unknown |
| UNC-6 | **Accessibility (a11y) completeness**: ARIA labels present on key controls (cart, buttons, search), but no comprehensive a11y audit evidenced. Focus management in modals uses `@headlessui/react`. | Inferred — partial evidence |
| UNC-7 | **Internationalization (i18n)**: No evidenced multi-language or multi-currency support beyond single `currencyCode` from Shopify. Price formatting uses `Intl.NumberFormat(undefined, ...)` (browser locale). | Unknown — not implemented |
| UNC-8 | **Testing**: No test files found in repository. `package.json` `test` script only runs `prettier:check`. | Verified absence — no unit/integration/e2e tests |

---

## 9. Requirements Traceability Matrix

| Feature Area | Functional | Business Rules | Interface | Data | Security | Non-Functional | Operational |
|--------------|------------|----------------|-----------|------|----------|----------------|-------------|
| Homepage | FR-1.1 | BR-2 | — | DR-1, DR-4 | — | NFR-1, NFR-2, NFR-5 | — |
| Search | FR-1.2, FR-1.3 | BR-1 | IF-21, IF-22 | DR-1 | — | NFR-1, NFR-2, NFR-4, NFR-7 | — |
| Collections | FR-1.4, FR-1.7 | BR-1, BR-2, BR-6 | IF-23 | DR-1, DR-3 | — | NFR-1, NFR-2 | — |
| Product Detail | FR-1.5, FR-1.6 | BR-1, BR-5, BR-7 | IF-24 | DR-1, DR-4, DR-5 | — | NFR-1, NFR-2, NFR-5, NFR-7 | — |
| Cart | FR-2.1–2.8 | BR-3, BR-4, BR-8 | IF-2–6 | DR-2 | SR-3 | NFR-3, NFR-8 | — |
| Variant Selection | FR-3.1–3.4 | BR-5 | — | DR-1 | — | NFR-4 | — |
| Navigation | FR-4.1–4.4 | — | IF-21 | DR-5 (Menu) | — | NFR-4 | — |
| Content Pages | FR-1.8 | — | IF-25 | DR-1 (Page) | — | NFR-1 | — |
| SEO | FR-5.1–5.6 | BR-1 | IF-21–25 | — | — | — | OR-5 |
| Revalidation | FR-6.1–6.3 | — | IF-1 | — | SR-2, SR-7 | NFR-11, NFR-12 | OR-6 |
| UX Enhancements | FR-7.1–7.4 | — | — | — | — | NFR-9, NFR-10 | — |

---

## 10. Conclusion

The repository evidences a **production-ready, modern headless commerce storefront** with the following characteristics:

**Strongly Evidenced Requirements:**
- Complete anonymous shopping flow: browse → search → product detail → variant selection → cart → Shopify checkout
- Server-first architecture with RSC, streaming, caching, and optimistic UI
- Clean separation of Shopify integration (`lib/shopify`) enabling provider portability
- Comprehensive SEO/metadata/sitemap generation
- Webhook-driven cache revalidation
- Responsive, accessible UI with dark mode

**Not Evidenced (Gaps for Consideration):**
- User authentication / account management (deferred to Shopify checkout)
- Real-time inventory display
- Tax estimation pre-checkout
- Analytics / conversion tracking
- Automated testing
- Multi-currency / multi-language
- Rate limiting / bot protection
- Cookie security attributes (SameSite, Secure, HttpOnly) explicitly set

**Architectural Decisions as Constraints:**
- Shopify Storefront API as sole data source (no local database)
- Vercel/Next.js platform dependencies (Image Optimization, ImageResponse, Server Actions, `next/cache` tags)
- pnpm + TypeScript strict mode + Prettier enforced

This requirements reconstruction reflects **what the system demonstrably does and requires to operate**, not aspirational features. All verified requirements are traceable to specific implementation artifacts.