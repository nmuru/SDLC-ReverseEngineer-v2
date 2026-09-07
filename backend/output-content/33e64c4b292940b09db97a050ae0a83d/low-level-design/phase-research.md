# Phase Research Brief

Research schema: 3
Phase: low-level-design

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
## Low-Level Design Summary

The application implements a Shopify-first ecommerce storefront using Next.js App Router with React Server Components, Server Actions, and a centralized cart context. The architecture separates server-side data fetching and mutations from client-side interactivity.

### Core Shopify Integration

The `lib/shopify/index.ts` module serves as the primary abstraction layer, exposing operations for cart management (`createCart`, `addToCart`, `removeFromCart`, `updateCart`, `getCart`), catalog retrieval (`getProducts`, `getCollections`, `getMenu`, `getPage`, `getProduct`, `getProductRecommendations`), and cache revalidation (`revalidate`). These functions wrap GraphQL queries and mutations defined in `lib/shopify/queries/` and `lib/shopify/mutations/`, which import shared fragments from `lib/shopify/fragments/` (cart, product, image, seo). The `shopifyFetch` function handles authenticated requests to the Shopify GraphQL endpoint using environment variables (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`). All external operations are typed via extensive TypeScript interfaces in `lib/shopify/types.ts`, defining domain entities (Product, Cart, CartItem, Collection, Menu, Page, Image, Money) and operation-specific types.

### Cart Management Architecture

Cart state is managed through a React context provider (`components/cart/cart-context.tsx`) that maintains a local representation of the Shopify cart. The context exposes a `useCart` hook and uses a reducer (`cartReducer`) to handle actions defined in `components/cart/actions.ts`: `addItem`, `removeItem`, `updateItemQuantity`, `redirectToCheckout`, and `createCartAndSetCookie`. The actions layer calls the Shopify operations directly, enabling server-side mutations while updating local state optimistically. The cart modal (`components/cart/modal.tsx`) composes interactive elements (add-to-cart buttons, delete-item buttons, quantity editors) that dispatch these actions. The context also includes utility functions for cost calculation and cart total updates, ensuring consistent state transformations.

### Product and Catalog Data Flow

Product data originates from GraphQL queries (`lib/shopify/queries/product.ts`, `lib/shopify/queries/collection.ts`) and flows through server components. Product detail pages (`app/product/[handle]/page.tsx`) fetch product data and render galleries, descriptions, and variant selectors. The variant selector (`components/product/variant-selector.tsx`) manages product option combinations, feeding into the add-to-cart flow. Catalog pages use grid components (`components/grid/`) and three-item featured grids (`components/grid/three-items.tsx`) to display products, leveraging shared tile components that render images and labels.

### Search and Filtering

The search system (`app/search/`) integrates a filter sidebar (`components/layout/search/filter/`) with collection facets (`components/layout/search/collections.tsx`). Filter items are typed as `PathFilterItem` and `SortFilterItem`, enabling dynamic query construction. The search layout (`app/search/layout.tsx`) wraps results with a children wrapper for Suspense boundaries, while the search page (`app/search/page.tsx`) orchestrates data fetching and filtering logic.

### State Management and Validation

Client state is primarily confined to the cart context, with server state managed through Next.js caching and revalidation. The revalidation endpoint (`app/api/revalidate/route.ts`) uses `SHOPIFY_REVALIDATION_SECRET` to securely trigger cache updates after mutations. Validation is centralized in `lib/type-guards.ts` (e.g., `findError`) and `lib/utils.ts`, with error handling embedded in Shopify operations. The architecture relies on TypeScript for compile-time contract enforcement, minimizing runtime validation needs.

### Key Dependencies

Critical import chains include: cart actions importing Shopify operations; cart modal depending on cart context and action helpers; product detail pages depending on variant selectors; and layout components (navbar, footer) consuming menu data from Shopify queries. The separation of queries, mutations, and fragments ensures single-source data transformation, while the context API provides a unified client-side state boundary.

### Uncertainties

The design does not expose payment processing logic, order management, or admin interfaces—these are assumed to be handled by Shopify's native checkout. The revalidation strategy's granularity (e.g., tag-based vs. path-based) is not detailed in the evidence, and the fallback behavior for GraphQL errors remains inferred from type guards rather than explicit error boundaries.
