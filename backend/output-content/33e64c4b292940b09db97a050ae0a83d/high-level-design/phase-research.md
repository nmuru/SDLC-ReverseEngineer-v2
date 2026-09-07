# Phase Research Brief

Research schema: 3
Phase: high-level-design

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
## High-Level Design Summary

### Logical Subsystems and Responsibilities

**1. Shopify Integration Layer (`lib/shopify/`)**  
The central abstraction for all Shopify GraphQL communication. `lib/shopify/index.ts` composes query and mutation modules (`queries/cart.ts`, `queries/product.ts`, `queries/collection.ts`, `queries/menu.ts`, `queries/page.ts`, `mutations/cart.ts`) and exposes a typed client interface. Fragments (`fragments/cart.ts`, `fragments/product.ts`, `fragments/image.ts`, `fragments/seo.ts`) define reusable GraphQL selection sets, ensuring consistent data shapes. Types in `lib/shopify/types.ts` (Product, Cart, CartItem, Collection, Menu, Page, Image, Money) form the domain model shared across server and client.

**2. Cart Management System (`components/cart/`)**  
A hybrid server/client architecture. Server Actions in `components/cart/actions.ts` invoke `lib/shopify` mutations (add, update, delete) and trigger revalidation. The React Context in `components/cart/cart-context.tsx` holds a client-side cart snapshot, hydrated from server-fetched data and updated optimistically via `useOptimistic`. UI components (`modal.tsx`, `add-to-cart.tsx`, `delete-item-button.tsx`, `edit-item-quantity-button.tsx`) consume this context, keeping the cart accessible globally without prop drilling.

**3. Product Catalog & Display**  
Product browsing splits across reusable display components (`components/grid/three-items.tsx`, `components/grid/tile.tsx`, `components/layout/product-grid-items.tsx`) and feature-specific pages. The product detail route (`app/product/[handle]/page.tsx`) composes a gallery, description (`components/product/product-description.tsx`), variant selector (`components/product/variant-selector.tsx`), and add-to-cart button. The home page (`app/page.tsx`) uses a carousel (`components/carousel.tsx`) and three-item grid for featured products.

**4. Search & Filtering (`components/layout/search/`, `app/search/`)**  
The search page (`app/search/page.tsx`) integrates a filter list (`components/layout/search/filter/index.tsx` with dropdown/item subcomponents) and collection facets (`components/layout/search/collections.tsx`). Dynamic collection routes (`app/search/[collection]/page.tsx`) provide SEO-friendly category pages. All search data flows through `lib/shopify/queries/collection.ts` and `product.ts`.

**5. Navigation & Layout (`components/layout/navbar/`, `components/layout/footer.tsx`, `app/layout.tsx`)**  
The navbar (`components/layout/navbar/index.tsx`) includes a mobile menu (`mobile-menu.tsx`) and embedded search (`search.tsx`). Menus are fetched via `lib/shopify/queries/menu.ts`. The root layout (`app/layout.tsx`) provides global providers (cart context, fonts) and loads global styles.

**6. Dynamic Content Pages (`app/[page]/page.tsx`, `lib/shopify/queries/page.ts`)**  
Catch-all route renders CMS-driven pages (About, Contact, etc.) using Shopify's Online Store pages. OpenGraph images (`app/[page]/opengraph-image.tsx`, `app/search/[collection]/opengraph-image.tsx`) generate social cards dynamically.

**7. Revalidation & Cache Management (`app/api/revalidate/route.ts`)**  
A secured webhook endpoint (`SHOPIFY_REVALIDATION_SECRET`) that invalidates Next.js cache on demand. Called after cart mutations or content changes to keep server-rendered data fresh.

### Major Data and Control Flows

1. **Initial Page Load (Server)**: RSC fetches data via `lib/shopify/index.ts` → specific query module → Shopify GraphQL → typed fragments → rendered HTML. Cart hydrated from `getCart` query into context.
2. **Cart Mutation (Client → Server)**: User action → context optimistic update → Server Action (`actions.ts`) → `lib/shopify/mutations/cart.ts` → Shopify → revalidation trigger → fresh `getCart` on next render.
3. **Navigation/Menu**: `lib/shopify/queries/menu.ts` populates navbar links and footer menus at build/render time.
4. **Search/Filter**: Client interactions update URL/search params → server re-renders `app/search/page.tsx` with filtered collection data from `queries/collection.ts`.

### External Boundaries

- **Shopify Storefront API**: GraphQL endpoint (`SHOPIFY_GRAPHQL_API_ENDPOINT` from `lib/constants.ts`) authenticated via `SHOPIFY_STOREFRONT_ACCESS_TOKEN`. All catalog, cart, and content data originates here.
- **Vercel/Deployment**: `VERCEL_PROJECT_PRODUCTION_URL` and `SITE_NAME` configure canonical URLs and metadata. Turbopack used in dev (`next dev --turbopack`).
- **Client Browser**: Hydration boundary at `app/layout.tsx`; client components limited to interactive islands (cart modal, variant selector, mobile menu, search dropdown).

### Important Uncertainties

- **Cache Strategy Details**: The revalidation endpoint exists, but the exact cache tags/keys used in `lib/shopify/index.ts` and query modules are not visible. Unclear whether `next/cache` tags are granular (per product, per collection) or coarse.
- **Error/Loading Boundaries**: No explicit `error.tsx` or `loading.tsx` files appear in the tracked topology; Suspense boundaries likely exist inline but their placement and fallback UIs are not documented.
- **Provider Swappability**: The README references BigCommerce/Ecwid/Geins forks, but the current codebase hardcodes Shopify-specific fragments, mutations, and env vars. The `lib/shopify` namespace suggests a provider interface was intended, but no abstraction layer (e.g., `lib/commerce/`) is present.
- **Order/Checkout Flow**: Checkout redirects to Shopify's hosted checkout; no custom order confirmation or post-purchase logic is visible in the repository.
- **Parsing Gaps**: 66 files unavailable to tree-sitter; some business rules (e.g., variant pricing logic, inventory checks, discount codes) may reside in unparsed files.
