# Repository Research Brief

Research schema: 3
Phase: repository-wide

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
## Repository Summary

This is **Next.js Commerce**, a high-performance, server-rendered ecommerce application template built by Vercel using the Next.js App Router. It is currently maintained for **Shopify** as the primary commerce provider, though the architecture is designed to allow swapping the `lib/shopify` layer for alternative providers (BigCommerce, Ecwid, Geins) with minimal changes to the rest of the template.

### Technology Stack
The application uses **Next.js 15.6.0-canary**, **React 19.0.0**, **TypeScript**, **Tailwind CSS**, and **Node.js**. It leverages modern React patterns including React Server Components, Server Actions, `Suspense`, and `useOptimistic`. Styling relies on Tailwind CSS with container queries and typography plugins. Key UI dependencies include `@headlessui/react`, `@heroicons/react`, `clsx`, `geist` font, and `sonner` for toasts.

### Architecture and Key Capabilities

**Shopify Integration Layer** (`lib/shopify/`): The core commerce backend is a Shopify GraphQL client exposing functions for cart CRUD (`createCart`, `addToCart`, `removeFromCart`, `updateCart`, `getCart`), product/collection queries (`getProduct`, `getProducts`, `getCollection`, `getCollections`, `getCollectionProducts`), menu/page retrieval (`getMenu`, `getPage`, `getPages`), and product recommendations. It uses typed GraphQL fragments (product, image, SEO, cart) and mutations organized in separate files.

**Cart System**: A full client-side cart is implemented via `CartProvider`/`useCart` context with reducer-based state management, supporting add/remove/update quantity operations, cost calculations, and a modal UI with checkout redirection. Cart actions are Server Actions that interact with Shopify and invalidate caches.

**Pages and Routes**: The app includes a home page with carousel and product grids, product detail pages (`/product/[handle]`), collection/category pages (`/search/[collection]`), a general search page (`/search`), static CMS pages (`/[page]`), and an API route for revalidation (`/api/revalidate`). Each page generates SEO metadata and OpenGraph images.

**Search and Filtering**: A search interface with collection filtering, sort options, and path-based filter items is integrated into the navbar and search layout.

### External Systems and Integrations
- **Shopify** (GraphQL API): The sole commerce backend, accessed via storefront access token and store domain configured through environment variables (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_REVALIDATION_SECRET`).
- **Vercel**: Deployment platform, with `VERCEL_PROJECT_PRODUCTION_URL` used for canonical URLs and sitemap generation.
- **Sitemaps and Robots**: Generated server-side using Shopify data.

### Implementation Characteristics
The codebase is heavily TypeScript-typed with Shopify-specific types (`ShopifyProduct`, `ShopifyCart`, `Collection`, `Product`, etc.) defined in `lib/shopify/types.ts`. It uses React Server Components throughout, with Server Actions for cart mutations and revalidation. The project follows a clean separation between the Shopify data layer, shared UI components, and page-level components.

### Ambiguities
The parse summary indicates all 66 source files were marked as "unavailable," meaning the actual file contents were not inspected — only symbol-level metadata was extracted. Specific implementation details (e.g., how revalidation webhooks work, exact caching strategies, error handling patterns) cannot be confirmed from the supplied intelligence alone.
