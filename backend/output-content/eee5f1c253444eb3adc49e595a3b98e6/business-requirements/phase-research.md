# Phase Research Brief

Research schema: 3
Phase: business-requirements

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
**Business‑Requirements Summary – Next.js Commerce v2**

The repository implements a server‑rendered ecommerce storefront that supports the classic retail customer journey: discovery, evaluation, cart management, and checkout. The primary external actor is the **shopper**, who browses products, applies search and filter criteria, manipulates a persistent cart, and proceeds to checkout. A secondary actor is the **Shopify integration** (or an equivalent commerce backend), which supplies product catalogs, inventory, and triggers content updates via webhooks.

**Actor Goals and Workflows**  
- **Discovery**: Shoppers navigate collections and product grids (`components/grid/three-items.tsx`, `app/search/[collection]/page.tsx`) and use a faceted search interface (`components/layout/search/filter/index.tsx`, `app/search/page.tsx`). The filter system is driven by constants (`lib/constants.ts`) that define sortable items, tag filters, price ranges, and hidden product tags, shaping how results are presented.  
- **Cart Management**: The cart is a stateful entity stored in a React context (`components/cart/cart-context.tsx`). Server actions (`components/cart/actions.ts`) provide `addItem`, `removeItem`, `updateItemQuantity`, and `redirectToCheckout`. The modal component (`components/cart/modal.tsx`) surfaces cart contents, enables quantity edits, and renders a checkout button that triggers the checkout redirection.  
- **Checkout**: The checkout workflow culminates in a server‑side redirect (`redirectToCheckout`) to the external payment provider, indicating that the repository delegates payment processing to Shopify’s checkout flow.  
- **Content Freshness**: A revalidation endpoint (`app/api/revalidate/route.ts`) accepts POST requests, likely from Shopify webhooks, to invalidate cached pages and trigger incremental static regeneration, ensuring that product updates are reflected without a full rebuild.  

**Capabilities and Business Rules**  
- **Product Browsing**: Grid and list views, collection pages, and featured carousels (`components/carousel.tsx`) provide multiple discovery modes.  
- **Search & Filtering**: The search page (`app/search/page.tsx`) combines a query input with a filter UI that respects `SortFilterItem` and tag constants, enforcing business rules such as default sorting (`defaultSort`) and exclusion of hidden products (`HIDDEN_PRODUCT_TAG`).  
- **SEO & Discoverability**: Each page type generates metadata via `generateMetadata` functions, using fragment‑sewed SEO data (`lib/shopify/fragments/seo.ts`). Open Graph images and sitemaps are produced, indicating that marketing visibility is a first‑class concern.  
- **Cart Totals & Validation**: The cart reducer (`components/cart/cart-context.tsx`) updates totals and validates line‑item changes, while type guards (`lib/type-guards.ts`) and utility validation (`lib/utils.ts`) ensure that Shopify responses conform to expected shapes before UI rendering.  

**State Changes and Dependencies**  
- **Cart State**: Changes propagate from UI interactions (add/remove/update buttons) through client‑side context reducers and server actions, ultimately updating the cart in Shopify via mutations (`lib/shopify/mutations/cart.ts`). The cart’s persistence is managed through cookies (`createCartAndSetCookie`).  
- **Page Cache**: Revalidation triggers a cache invalidation flow that depends on the `revalidate` secret (`SHOPIFY_REVALIDATION_SECRET`) and the `next/cache` import in cart actions, suggesting optimistic caching strategies.  
- **External Integration**: All commerce data is abstracted behind `lib/shopify/index.ts`, which exports `shopifyFetch` and operation functions (`getProduct`, `getCollection`, `addToCart`, etc.). Environment variables (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`) gate access to the backend, defining the system’s integration boundary.  

**Permissions and Validation**  
- **Access Control**: The repository relies on environment‑variable‑driven secrets to authenticate with Shopify, implying that only authorized deployments can mutate cart state or trigger revalidation.  
- **Data Validation**: Type guards and utility functions (`lib/type-guards.ts`, `lib/utils.ts`) enforce schema compliance for Shopify GraphQL responses, reducing runtime errors in the UI.  

**Notable Exceptions and Uncertainties**  
- **Alternative Commerce Providers**: The README states that other providers can fork the repo and replace `lib/shopify` with their own implementation, but the exact interface contracts are not enumerated in the supplied intelligence, leaving downstream integration points ambiguous.  
- **Checkout Flow Detail**: Evidence shows a `redirectToCheckout` server action, yet the precise steps between cart finalization and the external payment redirect are not fully visible, creating uncertainty about payment‑method handling or order‑creation logic.  
- **Shopify API Version & Rate Limiting**: The repository does not expose the specific Storefront API version or rate‑limit handling, making it difficult to assess versioning strategy or throttling behavior.  
- **Testing Coverage**: Only a `prettier:check` script appears in the package scripts; the absence of a comprehensive test suite suggests limited automated validation of business rules beyond linting.  

**Business Outcome**  
The system delivers a performant, SEO‑optimized storefront that balances server‑side rendering with dynamic cart interactions. By abstracting commerce logic into a pluggable `lib/shopify` layer, it supports multiple backend providers while maintaining a consistent user experience. The revalidation mechanism ensures that product catalog changes are promptly reflected, aligning operational agility with performance goals. However, gaps in interface documentation, checkout detail, and testing coverage represent areas where additional specification would reduce integration risk for alternative providers.
