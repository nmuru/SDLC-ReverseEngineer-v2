# Design Pattern Analysis

## Overview

The repository is a Next.js Commerce storefront targeting Shopify as its primary provider. The implementation demonstrates a coherent set of recurring design patterns that organize data fetching, state management, external integration, and UI composition. Four significant patterns are evidenced: **Provider/Context with Reducer**, **Adapter Layer**, **Server Actions**, and **Fragment Composition**. A fifth pattern, **Component Composition Hierarchy**, is structural but less formally defined. The patterns work together to isolate the Shopify dependency, keep secrets server-side, and provide optimistic client-side state updates.

---

## 1. Provider/Context with Reducer — Cart State Management

**Problem:** Cart state must be shared across the application (navbar badge, modal, product pages) while staying synchronized with a server-side Shopify cart. Direct client-side fetching would expose the storefront access token and bypass Next.js caching.

**Participants:**

- `components/cart/cart-context.tsx` — defines `CartContext`, `CartProvider`, `useCart`, and `cartReducer`
- `components/cart/add-to-cart.tsx` — consumes `useCart().addCartItem` for optimistic updates
- `components/cart/modal.tsx` — consumes `useCart().cart` and `updateCartItem` for quantity editing
- `components/cart/delete-item-button.tsx`, `components/cart/edit-item-quantity-button.tsx` — dispatch reducer actions
- `app/layout.tsx` — wraps the application in `CartProvider`, passing a `cartPromise` from `getCart()`

**How the pattern is demonstrated:**

`CartProvider` receives a `cartPromise` (not resolved data) and passes it through context. `useCart` consumes the promise via React's `use` hook, then pairs it with `useOptimistic` and `cartReducer`. The reducer manages a local `Cart` state machine with actions `ADD_ITEM` and `UPDATE_ITEM`, computing costs and totals locally. The context exposes `addCartItem` and `updateCartItem` — these dispatch to the optimistic reducer immediately, providing instant UI feedback before the server mutation completes. The server-side mutation is then triggered by the form action in `add-to-cart.tsx`, which calls both `addCartItem` (optimistic) and `addItem` (Server Action).

**Role in the system:** This pattern bridges server-managed cart data with client-side interactivity. It separates the data-fetching boundary (`getCart` in layout) from the state-transition logic (reducer), and from the mutation boundary (Server Actions).

**Confidence:** Verified. The implementation clearly demonstrates the Provider/Context with Reducer pattern: a central context, a reducer function, optimistic state updates via `useOptimistic`, and a clean separation between server data and client state transitions.

---

## 2. Adapter Layer — Commerce Provider Abstraction

**Problem:** The application must integrate with Shopify's GraphQL API, but the codebase is structured so that swapping to BigCommerce, Ecwid, or Geins requires minimal changes. Direct Shopify imports throughout the codebase would create tight coupling.

**Participants:**

- `lib/shopify/index.ts` — the adapter module, exporting `shopifyFetch`, `createCart`, `addToCart`, `removeFromCart`, `updateCart`, `getCart`, `getCollection`, `getCollectionProducts`, `getCollections`, `getMenu`, `getPage`, `getPages`, `getProduct`, `getProductRecommendations`, `getProducts`, `revalidate`
- `lib/shopify/types.ts` — application-facing domain types (`Cart`, `Product`, `Collection`, `Page`, etc.) and Shopify-specific operation types
- `lib/shopify/queries/*.ts` — GraphQL query documents
- `lib/shopify/mutations/cart.ts` — GraphQL mutation documents
- `lib/shopify/fragments/*.ts` — reusable GraphQL fragments
- `lib/constants.ts` — configuration (API endpoint, tags, hidden product tag)
- `lib/type-guards.ts` — `isShopifyError` for Shopify-specific error parsing

**How the pattern is demonstrated:**

`lib/shopify/index.ts` is the sole import point for Shopify logic. No route or component imports query/mutation modules directly. The adapter exposes provider-agnostic function names (`getProduct`, `getProducts`, `createCart`, `addToCart`, etc.) that accept and return application-level types from `lib/shopify/types.ts`. Internally, `shopifyFetch` handles the HTTP call to Shopify's GraphQL endpoint, authenticates with the storefront token, and parses errors. Each exported function composes a specific query or mutation, passes variables, and reshapes the Shopify response into the application type (e.g., `reshapeCart`, `reshapeProduct`, `reshapeCollection`).

**Role in the system:** This adapter is the central integration boundary. It isolates Shopify's GraphQL schema, endpoint URL, authentication header, and response shapes from the rest of the application. The README confirms the intended use: swap this module to change providers.

**Confidence:** Verified. The implementation clearly demonstrates an Adapter pattern: a single module wrapping an external system (Shopify GraphQL API) behind a provider-agnostic interface, with response reshaping and error handling encapsulated internally.

---

## 3. Server Actions — Mutation Boundary

**Problem:** Cart mutations (add, remove, update quantity, create cart, redirect to checkout) must execute on the server to protect the Shopify storefront access token and leverage Next.js caching and revalidation. A client-side fetch pattern would expose secrets and bypass server-side cache control.

**Participants:**

- `components/cart/actions.ts` — all Server Actions: `addItem`, `removeItem`, `updateItemQuantity`, `redirectToCheckout`, `createCartAndSetCookie`
- `lib/shopify/index.ts` — adapter functions called by the actions
- `components/cart/modal.tsx` — imports and invokes `createCartAndSetCookie` and `redirectToCheckout` directly
- `components/cart/add-to-cart.tsx` — uses `useActionState` with `addItem` for form submission

**How the pattern is demonstrated:**

Every function in `actions.ts` is marked `"use server"`. They call the adapter (`addToCart`, `removeFromCart`, `updateCart`, `createCart`, `getCart`) and use `updateTag` from `next/cache` for cache invalidation. `createCartAndSetCookie` sets the `cartId` cookie after cart creation. `redirectToCheckout` reads the cart and redirects to Shopify's checkout URL. The modal invokes `createCartAndSetCookie` and `redirectToCheckout` as form actions. The `AddToCart` component uses `useActionState` with `addItem` for the form submission, while also calling `addCartItem` from context for optimistic UI.

**Role in the system:** Server Actions serve as the mutation boundary between the client UI and the Shopify API. They ensure secrets stay server-side, enable Next.js cache tag invalidation after mutations, and provide a clean server-side entry point for all state-changing operations.

**Confidence:** Verified. The implementation clearly demonstrates the Server Actions pattern: all mutations are defined in a dedicated module with `"use server"`, consume the adapter, and are invoked from client components via form actions or `useActionState`.

---

## 4. Fragment Composition — GraphQL Data Shape Management

**Problem:** Shopify's GraphQL API returns nested connections (edges/nodes). The application needs consistent, flattened data shapes across queries and mutations. Duplicating field selections across multiple GraphQL operations would create maintenance burden and inconsistency.

**Participants:**

- `lib/shopify/fragments/product.ts` — `productFragment`, imports `imageFragment` and `seoFragment`
- `lib/shopify/fragments/image.ts` — `imageFragment`
- `lib/shopify/fragments/seo.ts` — `seoFragment`
- `lib/shopify/fragments/cart.ts` — `cartFragment`, imports `productFragment`
- `lib/shopify/queries/product.ts`, `queries/collection.ts`, `queries/cart.ts`, `queries/page.ts`, `queries/menu.ts`
- `lib/shopify/mutations/cart.ts`

**How the pattern is demonstrated:**

Fragments are composed through file-level imports. `cartFragment` imports `productFragment`, which imports `imageFragment` and `seoFragment`. Queries and mutations import the fragments they need rather than duplicating field selections. The `reshapeProduct`, `reshapeCart`, `reshapeCollection`, and `reshapeImages` functions in `lib/shopify/index.ts` further normalize the GraphQL response by flattening `Connection<T>` structures (removing `edges`/`nodes` wrapping), filtering hidden products, and adding computed fields like `path` for collections.

**Role in the system:** Fragment composition ensures a single source of truth for Shopify schema field selections. When the schema changes or the application needs different fields, only the fragment is updated. The reshape functions provide a consistent output shape regardless of which query or mutation produced the data.

**Confidence:** Verified. The implementation clearly demonstrates a composition pattern for GraphQL data shapes. While this is a domain-specific variant rather than a textbook GoF pattern, it is a significant, intentional recurring design approach that improves maintainability and consistency.

---

## 5. Component Composition Hierarchy — UI Structure

**Problem:** The UI must be built from reusable, single-responsibility components that compose into larger structures without tight coupling. Each component should receive data via props, with context reserved for truly shared state.

**Participants (evidenced by dependency relationships):**

- `components/layout/navbar/index.tsx` → `MobileMenu`, `Search`
- `components/layout/navbar/mobile-menu.tsx` → `Search`
- `components/cart/modal.tsx` → `DeleteItemButton`, `EditItemQuantityButton`, `OpenCart`
- `components/product/product-description.tsx` → `VariantSelector`
- `components/grid/three-items.tsx` → `ThreeItemGridItem`
- `components/carousel.tsx` → `Tile` → `Label` → `Price`
- `components/layout/search/collections.tsx` → `CollectionList`, `Collections`
- `components/layout/search/filter/index.tsx` → `Dropdown`, `Item`

**How the pattern is demonstrated:**

Each parent component imports and renders its children, passing data via props. The cart modal is the only component that imports context (`useCart`) and actions — all other composition is purely prop-based. The filter subsystem uses a local component loop (`index.tsx` ↔ `dropdown.tsx` ↔ `item.tsx`) for mutual reference, which is a composition pattern for interactive dropdowns.

**Role in the system:** Component composition separates concerns: the navbar handles navigation layout, the cart modal handles cart UI, the variant selector handles product variant UI. This makes components reusable and testable in isolation.

**Confidence:** Verified for composition structure. The pattern is evident in the dependency graph but is less formally defined than the four patterns above — it represents a general architectural convention rather than a specific named pattern.

---

## 6. Webhook Revalidation Endpoint — On-Demand ISR

**Problem:** Shopify content changes (product updates, collection changes) must propagate to the Next.js cache without polling or waiting for revalidation intervals. The application needs to purge stale data when Shopify fires webhook events.

**Participants:**

- `app/api/revalidate/route.ts` — `POST` handler, delegates to `revalidate`
- `lib/shopify/index.ts` — `revalidate` function (the adapter's export)
- Environment variable `SHOPIFY_REVALIDATION_SECRET`

**How the pattern is demonstrated:**

The API route receives a Shopify webhook POST, validates the `secret` query parameter against `SHOPIFY_REVALIDATION_SECRET`, inspects the `x-shopify-topic` header to determine the change type (collection or product), and calls `revalidateTag` with the appropriate cache tag (`TAGS.collections` or `TAGS.products`). Unknown topics receive a 200 without revalidation. The `revalidate` function is deliberately placed in the adapter module so providers can control revalidation logic.

**Role in the system:** This endpoint implements on-demand Incremental Static Regeneration. It connects Shopify's webhook system to Next.js's cache invalidation, ensuring the storefront reflects content changes without a full rebuild or fixed revalidation interval.

**Confidence:** Verified. The implementation demonstrates a Webhook Receiver / On-Demand Revalidation pattern — a recurring architectural approach in SSR/ISR applications, though not one of the classic GoF design patterns.

---

## Patterns Not Evidenced

The following pattern candidates were investigated but not substantiated by the implementation:

- **Repository Pattern:** No data-access abstraction layer exists that mediates between domain and data mapping layers. The adapter (`lib/shopify/index.ts`) functions more as an API client than a repository.
- **Factory Pattern:** No centralized object creation mechanism with interchangeable product types was found.
- **Observer Pattern:** No pub/sub event system with decoupled publishers and subscribers exists. React's context update mechanism is not an Observer pattern in the traditional sense.
- **Strategy Pattern:** No interchangeable algorithm selection mechanism was found.
- **Facade Pattern:** While `lib/shopify/index.ts` simplifies Shopify's API, it does not provide a unified interface to a subsystem of interfaces — it is a direct API client adapter.

---

## Pattern Interactions

The patterns work together in a layered architecture:

1. **App routes** call the **Adapter** for data fetching (Server Components).
2. **Cart UI components** consume the **Provider/Context** for optimistic state, and invoke **Server Actions** for mutations.
3. **Server Actions** call the **Adapter** to persist changes to Shopify.
4. **GraphQL Fragments** are composed by the Adapter's queries and mutations.
5. The **Webhook Endpoint** calls the Adapter's `revalidate` to purge caches after Shopify changes.

This layering ensures that secrets stay server-side, the Shopify dependency is isolated, and the client UI remains responsive through optimistic updates.

---

## Summary Table

| Pattern | Evidence | Location | Role |
|---|---|---|---|
| Provider/Context with Reducer | `cartReducer`, `CartProvider`, `useCart`, `useOptimistic` | `components/cart/cart-context.tsx` | Client-side cart state with server sync |
| Adapter Layer | `shopifyFetch`, `reshapeCart`, provider-agnostic exports | `lib/shopify/index.ts` | Isolate Shopify dependency |
| Server Actions | `"use server"`, `addItem`, `removeItem`, `updateItemQuantity` | `components/cart/actions.ts` | Server-side mutation boundary |
| Fragment Composition | Nested fragment imports, `productFragment` → `imageFragment` + `seoFragment` | `lib/shopify/fragments/` | Consistent GraphQL data shapes |
| Component Composition | Prop-based parent-child rendering hierarchy | `components/layout/`, `components/cart/` | UI separation of concerns |
| Webhook Revalidation | `POST` handler, `revalidateTag`, secret validation | `app/api/revalidate/route.ts` | On-demand cache invalidation |