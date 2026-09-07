# Phase Research Brief

Research schema: 3
Phase: design-pattern

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
## Design Pattern Summary

### Core Architectural Patterns

**Provider/Context with Reducer (Cart State)**
The cart system uses a React Context (`components/cart/cart-context.tsx`) with a reducer (`cartReducer`) managing server-synced state. The context exposes `useCart` hook and actions (`createOrUpdateCartItem`, `updateCartItem`, `updateCartTotals`) that bridge client UI with Server Actions. This pattern isolates Shopify cart mutations behind a client-side state machine while keeping mutations on the server via `components/cart/actions.ts` (`addItem`, `removeItem`, `updateItemQuantity`, `createCartAndSetCookie`).

**Adapter Layer for Commerce Provider**
`lib/shopify/index.ts` acts as a clean adapter exposing a provider-agnostic API (`getProduct`, `getProducts`, `getCollection`, `createCart`, `addToCart`, `removeFromCart`, `updateCart`, `revalidate`). Internally it composes GraphQL fragments (`lib/shopify/fragments/cart.ts`, `product.ts`, `image.ts`, `seo.ts`) and delegates to query/mutation modules (`lib/shopify/queries/*.ts`, `lib/shopify/mutations/cart.ts`). This enables swapping Shopify for BigCommerce/Ecwid/Geins by replacing only this module.

**Server Actions for Mutations**
All cart mutations are Server Actions in `components/cart/actions.ts` — no client-side fetch to Shopify. The actions call the adapter (`lib/shopify/index.ts`) and return updated cart state. The modal (`components/cart/modal.tsx`) consumes these actions directly, while `AddToCart` (`components/cart/add-to-cart.tsx`) uses the context which internally invokes them. This keeps secrets server-side and leverages Next.js caching/revalidation.

**Fragment Composition for GraphQL**
Reusable GraphQL fragments live in `lib/shopify/fragments/` and are composed into queries/mutations: `cart.ts` imports `product.ts`, which imports `image.ts` and `seo.ts`. Queries (`lib/shopify/queries/product.ts`, `collection.ts`, `cart.ts`) and mutations (`lib/shopify/mutations/cart.ts`) import fragments rather than duplicating fields. This ensures consistent data shapes across the app and single-source-of-truth for Shopify schema.

**Component Composition Hierarchy**
UI follows strict composition: `Navbar` → `MobileMenu` + `Search`; `CartModal` → `DeleteItemButton` + `EditItemQuantityButton` + `OpenCart`; `ProductDescription` → `VariantSelector`; `ThreeItemGrid` → `ThreeItemGridItem`; `Carousel` → `Tile` → `Label` → `Price`. Each component has a single responsibility and receives data via props, not context (except cart).

**Revalidation via Webhook Endpoint**
`app/api/revalidate/route.ts` (`POST` handler) validates `SHOPIFY_REVALIDATION_SECRET` and calls `revalidate()` from the adapter to purge Next.js cache on Shopify webhook events. This implements on-demand ISR without polling.

### Dependency Direction

- **App routes** → **Components** → **Cart Context/Actions** → **Shopify Adapter** → **GraphQL Fragments/Queries/Mutations**
- **Components** import only downward (e.g., `modal.tsx` imports `actions.ts`, `cart-context.tsx`, `delete-item-button.tsx`); no cycles detected in supplied symbols.
- **Adapter** (`lib/shopify/index.ts`) is the sole import point for Shopify logic; no route or component imports query/mutation modules directly.

### Integration Mechanisms

1. **Environment-driven config**: `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_REVALIDATION_SECRET` injected at build/runtime.
2. **Server Actions + Cookies**: `createCartAndSetCookie` establishes cart identity; subsequent actions read cookie for cart ID.
3. **Optimistic UI**: README references `useOptimistic`; likely used in `AddToCart`/`EditItemQuantityButton` for immediate feedback before server response (exact locations not enumerated in symbols).
4. **Metadata Generation**: Each page exports `generateMetadata` (e.g., `app/product/[handle]/page.tsx`, `app/search/[collection]/page.tsx`) consuming adapter data for SEO/OpenGraph.

### Uncertainties

- **`useOptimistic` usage sites**: Not visible in supplied symbols; inferred only from README.
- **Checkout flow**: `redirectToCheckout` exists in actions but implementation details absent.
- **Webhook configuration**: `SHOPIFY_REVALIDATION_SECRET` validation exists but Shopify webhook setup not documented in repo.
- **Error handling strategy**: `lib/type-guards.ts` exports `findError` for Shopify error parsing, but propagation to UI not traced.
