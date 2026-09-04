I now have comprehensive evidence of the features. Let me produce the Features dossier.

# Features Analysis

This analysis reconstructs the implemented functional capabilities of the **Next.js Commerce (Vercel) — Shopify edition** storefront. The application is a server-rendered ecommerce front end that proxies product, collection, cart, page, and menu data from a Shopify Storefront GraphQL API and exposes them through a public shopping site plus a single internal webhook endpoint.

The inventory below groups implementation evidence into coherent user-facing workflows, operator-facing capabilities, and supporting internal behaviors. Features are described as capabilities, not as raw endpoints or files.

---

## 1. Storefront Browsing and Discovery

### 1.1 Home Page Curation
**Capability.** The home page (`/`) presents a hand-curated showcase of the catalog rather than an exhaustive listing. The composition depends on two named Shopify collections whose handles are reserved by the application.

**Workflow.** When a shopper opens the root URL:
1. The home page renders the `ThreeItemGrid` component, which calls `getCollectionProducts({ collection: "hidden-homepage-featured-items" })`.
2. If that collection contains at least three products, the first three are placed in a hero grid: a large featured product on the left and two secondary products stacked on the right.
3. The `Carousel` component then calls `getCollectionProducts({ collection: "hidden-homepage-carousel" })` and renders a horizontally scrolling strip. The product list is intentionally triplicated so the carousel can loop visually on wide screens.
4. The site footer is rendered at the bottom of the page.

**Outcome.** Visitors see a curated landing experience that exposes only products the merchant has placed in two specifically named Shopify collections. If either collection is empty or missing, the affected section is silently omitted; the page still renders.

**Status.** Implemented.

**Evidence.**
- `app/page.tsx` (composition of the page).
- `components/grid/three-items.tsx` (hero grid; reads `hidden-homepage-featured-items`).
- `components/carousel.tsx` (reads `hidden-homepage-carousel`).
- `lib/shopify/index.ts` — `getCollectionProducts` and the convention that "Collections that start with `hidden-*` are hidden from the search page."

### 1.2 Search and Free-Text Querying
**Capability.** Shoppers can search the entire catalog by free-text query and refine the result set with a sort selector.

**Workflow.** A search bar is rendered in the navbar. When a shopper submits a query:
1. The form posts to `/search` with the `q` parameter (`components/layout/navbar/search.tsx`).
2. The `SearchPage` (`app/search/page.tsx`) reads `q` and `sort` from the URL, maps `sort` to a Shopify `ProductSortKeys` + reverse flag using the `sorting` table in `lib/constants.ts`, and calls `getProducts({ sortKey, reverse, query })`.
3. The page reports the result count ("Showing N results for `query`") or a "no products match" message.
4. A `SearchLayout` (`app/search/layout.tsx`) wraps the page with a left-side collections facet, a right-side sort filter, and a footer.

The five available sort options are: Relevance, Trending (best-selling), Latest arrivals, Price low-to-high, Price high-to-low.

**Outcome.** Shoppers can locate products by text and reorder the result list by recency, popularity, or price.

**Status.** Implemented.

**Evidence.**
- `app/search/page.tsx`.
- `app/search/layout.tsx` (faceted layout).
- `components/layout/navbar/search.tsx`.
- `components/layout/search/filter/index.tsx` and `dropdown.tsx` (sort UI).
- `lib/shopify/index.ts` — `getProducts`.
- `lib/constants.ts` — `sorting` and `defaultSort`.

### 1.3 Collection-Based Browsing
**Capability.** Shoppers can browse a category of products, identified by its Shopify collection handle, and optionally sort the result list.

**Workflow.** When a shopper opens `/search/[collection]`:
1. The page calls `getCollection(params.collection)` for metadata and SEO data.
2. It calls `getCollectionProducts({ collection, sortKey, reverse })` to retrieve the product list.
3. The page renders the products in a responsive grid; if the collection has no products, it displays "No products found in this collection".
4. `generateMetadata` produces per-collection title, description, and OpenGraph data sourced from Shopify SEO fields.

Collection discovery is also exposed as a left-hand facet on every search page. The list of visible collections is the result of `getCollections()`, which:
- Always prepends a synthetic "All" entry pointing to `/search`.
- Filters out any Shopify collection whose handle starts with `hidden`, allowing merchants to keep curation-only collections out of the public facet while still using them for the homepage.

**Outcome.** Shoppers can navigate the store by category with the same sort options as global search, and the UI ensures the curation collections do not leak into the public navigation.

**Status.** Implemented.

**Evidence.**
- `app/search/[collection]/page.tsx`.
- `app/search/layout.tsx`.
- `components/layout/search/collections.tsx`.
- `lib/shopify/index.ts` — `getCollections`, `getCollection`, `getCollectionProducts`, and the `hidden` handle convention.
- `app/search/[collection]/opengraph-image.tsx` for social-card generation.

### 1.4 Content Pages
**Capability.** The application serves generic content pages authored in Shopify (handles ending up at `/{handle}`) as part of the storefront, with metadata, OpenGraph tags, and a "last updated" stamp.

**Workflow.** When a shopper visits `/{handle}`:
1. The dynamic route `app/[page]/page.tsx` calls `getPage(params.page)`.
2. If the page is not found, the route calls `notFound()` (404).
3. Otherwise the title, HTML body (rendered through the `Prose` component), and a localized last-updated date are shown.
4. `generateMetadata` populates title, description, `article` OpenGraph type, and publication/modification timestamps.

The `sitemap` route calls `getPages()` so all content pages are submitted to search engines.

**Outcome.** Merchants can publish and update editorial pages (about, terms, etc.) from Shopify and have them appear at the storefront root, with correct SEO metadata.

**Status.** Implemented.

**Evidence.**
- `app/[page]/page.tsx`.
- `app/[page]/opengraph-image.tsx`.
- `lib/shopify/index.ts` — `getPage`, `getPages`.
- `lib/shopify/queries/page.ts`.

### 1.5 Menu-Driven Site Navigation
**Capability.** The header and footer render navigation menus driven by Shopify Online Store menus, so merchants can change site navigation without redeploying.

**Workflow.** On every page render that includes the navbar or footer:
1. The `Navbar` calls `getMenu("next-js-frontend-header-menu")` and renders each item as a link.
2. The `Footer` calls `getMenu("next-js-frontend-footer-menu")` and renders the same shape in the footer.
3. The `lib/shopify` `getMenu` function rewrites Shopify URLs so that `/collections/...` becomes `/search/...` and `/pages/...` is stripped, presenting consistent local routes to shoppers.
4. The `MobileMenu` component renders the same data in a headless-ui dialog for narrow viewports.

**Outcome.** Navigation links reflect the merchant's Shopify menu configuration; clicking a link routes the shopper to the appropriate local page.

**Status.** Implemented.

**Evidence.**
- `components/layout/navbar/index.tsx`.
- `components/layout/navbar/mobile-menu.tsx`.
- `components/layout/footer.tsx` and `components/layout/footer-menu.tsx`.
- `lib/shopify/index.ts` — `getMenu` and its URL rewriting.
- `lib/shopify/queries/menu.ts`.

---

## 2. Product Detail Experience

### 2.1 Product Detail Page
**Capability.** Each product has a public detail page at `/product/[handle]` that presents media, copy, price, and stock signals with rich SEO markup.

**Workflow.** When a shopper opens a product URL:
1. The route handler calls `getProduct(params.handle)`. If the result is `undefined`, the route calls `notFound()` (404).
2. The product is rendered as a two-column layout: a `Gallery` (up to 5 images) on the left, and a `ProductDescription` on the right.
3. The page emits a `Product` JSON-LD block (`schema.org/Product` with `AggregateOffer`) including price range and `InStock`/`OutOfStock` availability.
4. `generateMetadata` writes per-product title, description, OpenGraph image, and conditional `robots` directives. If the product carries the `nextjs-frontend-hidden` tag, search engines are instructed not to index or follow the page.
5. A `RelatedProducts` section is rendered below, calling `getProductRecommendations(product.id)`. If Shopify returns no recommendations, the section is omitted.

**Outcome.** Shoppers can examine a single product in depth, including variant selection and stock state, while search engines and social platforms receive structured metadata.

**Status.** Implemented.

**Evidence.**
- `app/product/[handle]/page.tsx`.
- `components/product/gallery.tsx`.
- `components/product/product-description.tsx`.
- `lib/shopify/index.ts` — `getProduct`, `getProductRecommendations`.
- `lib/constants.ts` — `HIDDEN_PRODUCT_TAG = "nextjs-frontend-hidden"`.
- `lib/shopify/fragments/product.ts` (GraphQL shape for the product detail payload).

### 2.2 Product Image Gallery
**Capability.** The product detail page supports a navigable image gallery with prev/next controls and a thumbnail strip, all driven by URL state.

**Workflow.** The `Gallery` component reads the current `image` index from `useSearchParams`. The shopper can:
- Click a thumbnail to set the active image, which calls `router.replace` with the new `?image=N` parameter (no scroll).
- Click the prev/next overlay arrows to cycle through images, wrapping at both ends.

The visible set is the first five images of the product (`product.images.slice(0, 5)`).

**Outcome.** Shoppers can browse all product imagery without losing the current page state, and the active image is shareable via URL.

**Status.** Implemented.

**Evidence.** `components/product/gallery.tsx`; image slicing in `app/product/[handle]/page.tsx`.

### 2.3 Variant Selection
**Capability.** For products with more than one option, shoppers can choose combinations (e.g. size/color) and see availability reflected in the UI.

**Workflow.** The `VariantSelector`:
1. Reads the current selection from `useSearchParams` (one URL parameter per option name, lower-cased).
2. Builds a `combinations` table of `availableForSale` for every Shopify variant.
3. For each option value, determines whether a fully-matching variant exists in stock. Out-of-stock values are rendered with a strikethrough and disabled. The active value is outlined.
4. When the shopper clicks a value, `router.replace` updates the URL parameter, keeping the rest of the page state intact.

The `AddToCart` button then derives the `selectedVariantId` by matching the URL parameters to `variant.selectedOptions`. Products with zero or exactly one option/value skip the selector entirely.

**Outcome.** Shoppers select product variants through deep-linkable URL state, and unavailable combinations are visibly disabled, preventing broken add-to-cart attempts.

**Status.** Implemented.

**Evidence.**
- `components/product/variant-selector.tsx`.
- `components/cart/add-to-cart.tsx` (selectedVariantId derivation).
- `lib/shopify/fragments/product.ts` (variant data shape, including `availableForSale`).

---

## 3. Shopping Cart and Checkout Handoff

### 3.1 Cart Lifecycle
**Capability.** The application maintains a per-visitor shopping cart backed by the Shopify Storefront API, with a persistent `cartId` cookie and a React `CartProvider` context that streams the cart to client components.

**Workflow.**
- On first interaction (the cart modal mounts), `CartModal` invokes the server action `createCartAndSetCookie`, which calls `createCart()` in `lib/shopify` (the `cartCreate` mutation) and writes the returned `cart.id` to a `cartId` cookie.
- On every page load, `app/layout.tsx` calls `getCart()` without awaiting it, passing the resulting `Promise<Cart | undefined>` to `CartProvider`. Server components receive a stable promise reference, while client components use the React `use` hook to unwrap it.
- The cart is tagged with the `cart` cache tag and a private cache directive, so per-user cart state is not shared between visitors.
- A cookie that no longer resolves to a valid Shopify cart is treated as missing (the cart is `null` after checkout completion).

**Outcome.** Each visitor has a continuously available cart object during their session without a full page reload, and stale cookies are gracefully handled.

**Status.** Implemented.

**Evidence.**
- `app/layout.tsx` (Promise-based cart fetching).
- `components/cart/cart-context.tsx` (`CartProvider`, `useCart`, optimistic reducer).
- `components/cart/actions.ts` — `createCartAndSetCookie`.
- `lib/shopify/index.ts` — `createCart`, `getCart` (private cache, `TAGS.cart`).
- `lib/shopify/fragments/cart.ts`.

### 3.2 Add to Cart with Optimistic Update
**Capability.** Shoppers can add a product variant to the cart from a product detail page with immediate visual feedback, while the authoritative mutation completes in the background.

**Workflow.** When a shopper clicks "Add To Cart":
1. The `AddToCart` component derives the `selectedVariantId` from URL parameters (or, for single-variant products, falls back to the only variant).
2. It synchronously dispatches an optimistic `addCartItem` action through the client `CartProvider` reducer, so the cart modal opens and the line item appears immediately.
3. In parallel, it invokes the server action `addItem`, which calls `addToCart([{ merchandiseId, quantity: 1 }])` (the `cartLinesAdd` mutation) and then calls `updateTag(TAGS.cart)` to invalidate the cart cache.
4. The cart modal's open state is bound to a `useEffect` that watches `cart.totalQuantity`; any increase (e.g. a successful add) auto-opens the modal.
5. If the product is unavailable, the button renders "Out Of Stock" and is disabled. If a required variant is not yet selected, the button renders "Please select an option" and is disabled.

**Outcome.** Shoppers experience a near-instant add-to-cart interaction that is resilient to slow networks, and the UI prevents invalid submissions.

**Status.** Implemented.

**Evidence.**
- `components/cart/add-to-cart.tsx` (variant resolution, form action, disabled states).
- `components/cart/cart-context.tsx` (`createOrUpdateCartItem`, optimistic reducer, `updateCartTotals`).
- `components/cart/modal.tsx` (auto-open on quantity change).
- `components/cart/actions.ts` — `addItem`.
- `lib/shopify/index.ts` — `addToCart`.
- `lib/shopify/mutations/cart.ts` — `addToCartMutation`.

### 3.3 Edit Line Item Quantity
**Capability.** From the cart modal, shoppers can change the quantity of any line item, including removing it by setting quantity to zero.

**Workflow.** Each line in the cart modal renders `EditItemQuantityButton` controls:
1. The plus/minus button triggers the `updateItemQuantity` server action with `{ merchandiseId, quantity }`.
2. The server action reads the current cart, finds the matching line, and either:
   - Calls `removeFromCart([lineItem.id])` (the `cartLinesRemove` mutation) if the new quantity is zero.
   - Calls `updateCart([...])` (the `cartLinesUpdate` mutation) otherwise.
   - Calls `addToCart([...])` (the `cartLinesAdd` mutation) if the line does not yet exist and quantity is positive (defensive create-on-update).
3. The server action then calls `updateTag(TAGS.cart)` to invalidate the cache.
4. The client `CartProvider` reducer also performs the equivalent transformation locally for instant feedback (`updateCartItem` with `updateType: "plus" | "minus"`).

**Outcome.** Shoppers adjust their cart contents in real time with consistent server-side persistence.

**Status.** Implemented.

**Evidence.**
- `components/cart/edit-item-quantity-button.tsx`.
- `components/cart/cart-context.tsx` — `updateCartItem`.
- `components/cart/actions.ts` — `updateItemQuantity`.
- `lib/shopify/index.ts` — `removeFromCart`, `updateCart`, `addToCart`.
- `lib/shopify/mutations/cart.ts`.

### 3.4 Remove Line Item
**Capability.** Shoppers can remove a line from the cart via a dedicated delete control.

**Workflow.** The `DeleteItemButton` invokes the `removeItem` server action:
1. The action loads the cart and locates the line by `merchandiseId`.
2. It calls `removeFromCart([lineItem.id])` and then `updateTag(TAGS.cart)`.
3. The client reducer also drops the line via `updateCartItem(item, "delete")` for immediate UI feedback.

**Outcome.** Items can be removed with a single click; the cart is persisted to Shopify and the cache is invalidated for the next read.

**Status.** Implemented.

**Evidence.**
- `components/cart/delete-item-button.tsx`.
- `components/cart/cart-context.tsx` (delete handling).
- `components/cart/actions.ts` — `removeItem`.
- `lib/shopify/index.ts` — `removeFromCart`.

### 3.5 Checkout Handoff
**Capability.** Shoppers proceed to Shopify-hosted checkout from the cart modal with a single click.

**Workflow.** The cart modal's "Proceed to Checkout" button calls the `redirectToCheckout` server action, which:
1. Reads the current cart through `getCart()`.
2. Calls Next.js `redirect(cart.checkoutUrl)`, sending the browser to the Shopify-hosted checkout for the active cart.

**Outcome.** The shopper is handed off to Shopify's checkout, with cart state preserved through the Storefront API's `checkoutUrl`.

**Status.** Implemented.

**Evidence.**
- `components/cart/modal.tsx` (call site for `redirectToCheckout`).
- `components/cart/actions.ts` — `redirectToCheckout`.
- `lib/shopify/fragments/cart.ts` (exposes `checkoutUrl` on the cart).

---

## 4. Site Information Architecture and SEO

### 4.1 Sitemap Generation
**Capability.** A dynamically generated sitemap is exposed at `/sitemap.xml` covering the home page, all visible collections, all products, and all Shopify pages.

**Workflow.** `app/sitemap.ts` declares `dynamic = "force-dynamic"` (so the response is regenerated on each request):
1. The home page is added with the current timestamp.
2. `getCollections()` produces a route per collection, using each collection's `updatedAt`.
3. `getProducts({})` produces a route per product handle.
4. `getPages()` produces a route per Shopify page handle.
5. If any of the three calls fail, the error is logged via `JSON.stringify(error, null, 2)` and rethrown.
6. `validateEnvironmentVariables()` is called first; in a non-configured environment, this throws before any fetch attempt, so a missing `SHOPIFY_STORE_DOMAIN` would fail the sitemap route.

**Outcome.** Search engines can discover every product, collection, and content page via a single canonical document.

**Status.** Implemented.

**Evidence.** `app/sitemap.ts`; `lib/utils.ts` for `validateEnvironmentVariables` and `baseUrl`.

### 4.2 Robots Configuration
**Capability.** The site exposes a `/robots.txt` that points crawlers to the sitemap and the canonical host.

**Workflow.** `app/robots.ts` returns a ruleset allowing all user agents and declaring the sitemap URL and host derived from `baseUrl`.

**Outcome.** Web crawlers receive authoritative directives for crawling and discovery.

**Status.** Implemented.

**Evidence.** `app/robots.ts`.

### 4.3 OpenGraph Image Generation
**Capability.** The application generates OpenGraph images on demand for marketing-style previews of the home, generic content pages, and collection pages.

**Workflow.** Each route pair that needs social previews uses Next.js's opengraph-image conventions:
- `app/opengraph-image.tsx` and `app/[page]/opengraph-image.tsx` produce a per-handle image for the home and content routes.
- `app/search/[collection]/opengraph-image.tsx` produces one for collection pages.

**Outcome.** Sharing routes to the site (home, page, or collection) yields rich previews in social platforms.

**Status.** Implemented.

**Evidence.** `app/opengraph-image.tsx`, `app/[page]/opengraph-image.tsx`, `app/search/[collection]/opengraph-image.tsx`, and the shared `components/opengraph-image.tsx`.

---

## 5. Operator-Facing and Integration Capabilities

### 5.1 Shopify Webhook Revalidation
**Capability.** The application exposes a single HTTP endpoint that accepts Shopify webhooks for collection and product lifecycle events and triggers on-demand revalidation of the corresponding cache tags.

**Workflow.** `app/api/revalidate/route.ts` (POST) delegates to `revalidate(req)` in `lib/shopify`:
1. The handler reads the `x-shopify-topic` header and a `secret` query parameter.
2. If `secret` is missing or does not match `SHOPIFY_REVALIDATION_SECRET`, the endpoint returns `401`.
3. The supported topics are `collections/create`, `collections/delete`, `collections/update`, `products/create`, `products/delete`, `products/update`. Any other topic short-circuits with `200` (Shopify requires 2xx or it retries).
4. On a collection topic, `revalidateTag(TAGS.collections, "seconds")` is called.
5. On a product topic, `revalidateTag(TAGS.products, "seconds")` is called.
6. The response is always `200` with `{ revalidated: true, now: Date.now() }`.

**Outcome.** When the merchant updates products or collections in Shopify, the next storefront render reads fresh data; no full redeploy is required. The endpoint is explicitly internal and protected by a shared secret.

**Status.** Implemented.

**Evidence.**
- `app/api/revalidate/route.ts`.
- `lib/shopify/index.ts` — `revalidate`.
- `lib/constants.ts` — `TAGS.collections`, `TAGS.products`.

### 5.2 Cache Management
**Capability.** All read paths in the Shopify client use Next.js's `unstable_cacheLife` / `unstable_cacheTag` primitives, with per-resource lifetimes and tags. Cart state uses private cache; everything else uses shared cache.

**Workflow.** Each function in `lib/shopify/index.ts` declares its caching policy:
- `getCart`: `"use cache: private"`, tagged `cart`, lifetime `seconds`.
- `getCollection`, `getCollections`, `getMenu`: shared cache, tagged `collections`, lifetime `days`.
- `getCollectionProducts`, `getProduct`, `getProductRecommendations`, `getProducts`: shared cache, tagged `products` (and `collections` where appropriate), lifetime `days`.
- Server actions that mutate cart state call `updateTag(TAGS.cart)` so the next read re-fetches.
- The revalidation webhook calls `revalidateTag(...)` for `collections` and `products` with a `seconds` lifetime override.

**Outcome.** The storefront benefits from aggressive edge caching for catalog data while still allowing merchants to push near-real-time updates and keeping per-user cart state isolated.

**Status.** Implemented.

**Evidence.** All function bodies in `lib/shopify/index.ts`; `components/cart/actions.ts` for `updateTag` calls; `lib/constants.ts` for the `TAGS` registry.

### 5.3 Graceful Operation When Shopify Is Not Configured
**Capability.** When `SHOPIFY_STORE_DOMAIN` is missing, the application does not crash; instead, certain data fetchers return safe fallbacks so the surrounding UI can render.

**Workflow.** The `lib/shopify` functions check for the presence of the configured endpoint:
- `getCollections` returns a single synthetic "All" collection entry pointing to `/search`.
- `getCollectionProducts` and `getProduct` log a skip message and return an empty array / `undefined`.
- `getMenu` returns an empty array.

Several UI affordances rely on these fallbacks: the navbar omits its menu block, the homepage `ThreeItemGrid` and `Carousel` return `null`, and the cart modal will create a cart on first interaction.

**Outcome.** The codebase can be deployed in a non-configured state without throwing, although the corresponding features are not usable. The `validateEnvironmentVariables` utility is also available to surface misconfiguration explicitly when desired (used by the sitemap route).

**Status.** Partially implemented — defensive fallbacks exist, but meaningful functionality (products, collections, menus) is not available without Shopify credentials.

**Evidence.** Empty-endpoint guards in `lib/shopify/index.ts` (`getCollections`, `getCollectionProducts`, `getProduct`, `getMenu`); `lib/utils.ts` for `validateEnvironmentVariables`; consumers such as `components/grid/three-items.tsx` and `components/carousel.tsx` that early-return `null` on empty data.

---

## 6. Cross-Cutting and Presentation Behaviors

These capabilities are not user goals on their own, but they materially affect how the storefront presents itself and how features are reached.

### 6.1 Global Cart Context and Toaster
**Capability.** A global `CartProvider` wraps every page in `app/layout.tsx`, alongside a `Toaster` (from `sonner`) and a `WelcomeToast` that surfaces a one-time welcome message to first-time visitors.

**Workflow.** The root layout:
1. Initiates a non-awaited `getCart()` Promise and passes it to `CartProvider`, so children can read cart state without blocking the page.
2. Renders the navbar, page content, the global `Toaster`, and the `WelcomeToast`.
3. The `WelcomeToast` reads a `welcome-toast` cookie; if it is not set to `2` and the viewport is at least 650px tall, it shows a one-time `sonner` toast pointing to the Vercel template. Dismissing the toast sets a year-long cookie so it never appears again.

**Outcome.** Cart state, transient notifications, and onboarding messaging are available site-wide without per-page plumbing.

**Status.** Implemented.

**Evidence:** `app/layout.tsx`, `components/welcome-toast.tsx`, `components/cart/cart-context.tsx`.

### 6.2 Responsive Navigation and Footer
**Capability.** The storefront renders a header and footer that adapt to viewport size, with a mobile menu on narrow screens and a desktop navbar with logo, primary navigation, search bar, and cart trigger on wider screens.

**Workflow.** The `Navbar` composes a `LogoSquare` and `SITE_NAME`, a list of menu items, a centered `Search` input (with a `SearchSkeleton` fallback during Suspense), and a `CartModal` trigger. On viewports below the `md` breakpoint, the desktop menu is replaced by a `MobileMenu` headless-ui dialog. The `Footer` mirrors the brand mark and renders the footer menu plus a "Deploy on Vercel" badge.

**Outcome.** Shoppers can navigate the site on both desktop and mobile, with cart and search consistently available.

**Status.** Implemented.

**Evidence:** `components/layout/navbar/index.tsx`, `components/layout/navbar/mobile-menu.tsx`, `components/layout/navbar/search.tsx`, `components/layout/footer.tsx`, `components/layout/footer-menu.tsx`.

### 6.3 Home Page, Search, and Product Pages Share a Common Visual Vocabulary
**Capability.** Product tiles, grids, and pricing are factored into shared components so that the homepage, search results, collection pages, and related-products strip render consistently.

**Workflow:** Reusable presentation primitives include:
- `Grid` and `GridTileImage` for tile layouts.
- `ProductGridItems` to map product arrays to tile rows.
- `Price` for localized money formatting.
- `Prose` for rendering trusted HTML (used on product descriptions and Shopify pages).
- `LoadingDots` and the `SearchSkeleton` for Suspense fallbacks.

**Outcome:** The site presents a uniform visual language without duplicating layout logic across pages.

**Status:** Implemented.

**Evidence:** `components/grid/index.tsx`, `components/grid/tile.tsx`, `components/layout/product-grid-items.tsx`, `components/price.tsx`, `components/prose.tsx`, `components/loading-dots.tsx`.

---

## 7. Implementation Status Summary

| Capability | Status | Notes |
|---|---|---|
| Home page curation (featured grid + carousel) | Implemented | Depends on `hidden-homepage-featured-items` and `hidden-homepage-carousel` Shopify collections. |
| Search and free-text querying | Implemented | Five sort options, layout-driven facet sidebar. |
| Collection browsing | Implemented | Hidden-prefixed collections filtered out of the public facet. |
| Shopify content pages | Implemented | Reachable at `/{handle}`; 404 via `notFound()`. |
| Menu-driven navigation | Implemented | Header and footer menus; URL rewriting for `/collections` and `/pages`. |
| Product detail page | Implemented | JSON-LD, conditional `robots`, related products, hidden-tag handling. |
| Product image gallery | Implemented | URL-state based, up to 5 images. |
| Variant selection | Implemented | URL-state based, disabled out-of-stock values. |
| Cart lifecycle (create, get, cookie) | Implemented | Private cache per user; stale cookies tolerated. |
| Add to cart with optimistic update | Implemented | Server action + client reducer. |
| Edit line item quantity | Implemented | Quantity zero falls through to remove. |
| Remove line item | Implemented | Optimistic and authoritative. |
| Checkout handoff | Implemented | Redirects to Shopify `checkoutUrl`. |
| Sitemap generation | Implemented | Aggregates collections, products, pages. |
| Robots configuration | Implemented | All user agents, references sitemap. |
| OpenGraph image generation | Implemented | Home, content, and collection routes. |
| Shopify webhook revalidation | Implemented | `collections/*` and `products/*` topics, shared secret. |
| Cache management | Implemented | Per-resource tags and lifetimes; revalidation hooks. |
| Defensive fallbacks when Shopify is not configured | Partially implemented | Lists fall back to "All"; no product detail, recommendations, or menu. |
| Authentication, accounts, wishlists, order history | Apparently not implemented | Not present in the codebase. |
| Customer login / account area | Apparently not implemented | Not present in the codebase. |
| Internationalization / multi-currency selection | Apparently not implemented | No locale routing; prices and copy come from Shopify directly. |
| Inventory display beyond availability flag | Apparently not implemented | The `availableForSale` flag is surfaced; no quantity-based inventory UI. |
| Coupon / discount entry | Apparently not implemented | Not present in the codebase. |
| Tax/shipping estimation in cart | Apparently not implemented | The cart fragment requests `totalTaxAmount`; no estimator UI is wired. |
| Real user-side persistent profile (login) | Apparently not implemented | Cart is per-cookie and unauthenticated. |

## 8. Documentation vs. Implementation Discrepancies

The README positions the project as a multi-provider template (Shopify, BigCommerce, Medusa, Saleor, etc.). In this repository, only the Shopify integration is actually implemented:

- The `lib/shopify` module is the only data source wired into the app. There is no provider abstraction layer, no environment-driven provider selection, and no alternative back ends in the codebase.
- The integrations listed in the README (Orama search, React Bricks CMS) are referenced only in the README; no code in this repository implements them.
- The README's "Vercel, Next.js Commerce, and Shopify Integration Guide" reference is external documentation, not a feature of this repository.

A few in-code features are not described in the README:

- The webhook revalidation endpoint and its secret-based authentication (`/api/revalidate`).
- The defensive empty-endpoint behavior that keeps the site renderable without Shopify credentials.
- The use of private caching for cart state and the `updateTag` invalidation pattern in cart server actions.
- The "hidden" handle convention that separates curation collections from the public facet.

These are real, implemented behaviors that complement but are not advertised in the README.

## 9. Cross-Surface Verification

The feature inventory above was cross-checked against multiple evidence surfaces:

- **Pages and routes:** `app/page.tsx`, `app/[page]/page.tsx`, `app/product/[handle]/page.tsx`, `app/search/page.tsx`, `app/search/[collection]/page.tsx`, `app/search/layout.tsx`, `app/sitemap.ts`, `app/robots.ts`, `app/api/revalidate/route.ts`.
- **Components:** `components/grid/*`, `components/layout/*`, `components/cart/*`, `components/product/*`, `components/welcome-toast.tsx`, `components/carousel.tsx`, `components/price.tsx`, `components/prose.tsx`.
- **Data layer:** `lib/shopify/index.ts`, `lib/shopify/queries/*`, `lib/shopify/mutations/cart.ts`, `lib/shopify/fragments/*`, `lib/constants.ts`, `lib/utils.ts`, `lib/type-guards.ts`.
- **Configuration:** `.env.example` (lists `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_REVALIDATION_SECRET`, `COMPANY_NAME`, `SITE_NAME`), `package.json` (Next.js 15, React 19, Tailwind v4, sonner, headlessui, heroicons), `next.config.ts`, `tsconfig.json`.
- **Documentation:** `README.md`, `license.md`.

Each feature is supported by at least one route or component plus a corresponding server function or GraphQL operation, and most are corroborated by both UI and API evidence. The "apparently not implemented" items were checked for in the file tree, the dependency list, and the GraphQL operation set, and no evidence of their presence was found.