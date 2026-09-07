# Business Requirements — Next.js Commerce v2

## Business Context

The repository is a reference ecommerce storefront template maintained by Vercel as the Shopify implementation of the Next.js Commerce family. It exists to give merchants a server‑rendered, search‑engine‑discoverable shopping experience that delegates product, inventory, cart, and checkout logic to a commerce platform and can be re‑skinned by replacing a single integration layer.

The repository is supplied as a starting template ("Next.js Commerce") that merchants can fork and deploy to operate an online storefront. Its business purpose is therefore not to ship a finished retail product but to satisfy the recurring needs of an online merchant: presenting a catalog, helping shoppers find products, letting shoppers build and edit a cart, and handing them off to a checkout flow owned by the commerce platform.

## Stakeholders and Actors

| Actor | Role in the business need | Evidence |
|---|---|---|
| Shopper (visitor/customer) | Discovers products, evaluates them, assembles a cart, and proceeds to checkout. | Cart modal, product page, search page, navigation |
| Merchant / store operator | Operates the storefront; relies on the commerce platform to author products, collections, inventory, and pricing. | Product/collection queries, revalidation endpoint |
| Commerce platform (Shopify or alternative provider) | Source of truth for catalog, cart, checkout, and content‑change notifications. | `lib/shopify`, revalidate webhook |
| Search engines and external linkers | Consume page metadata and previews so that the storefront is discoverable and shareable. | SEO fragments, Open Graph images, sitemap |

The repository does not explicitly model roles such as "administrator login" or "customer account"; those needs are not evidenced.

## Principal Business Capabilities

- **Storefront browsing** — Visitors must be able to navigate collections and product detail pages.
- **Product discovery through search and filtering** — Visitors must be able to query the catalog and narrow results using defined filter dimensions.
- **Persistent shopping cart** — Visitors must be able to add, remove, and adjust line items and have their selections retained across the session.
- **Checkout handoff** — When a shopper is ready to pay, the storefront must hand the cart off to a checkout flow provided by the commerce platform.
- **Discoverability and sharing** — The storefront must expose the metadata, social previews, and sitemap entries that search engines and social platforms require.
- **Catalog freshness without redeploy** — When the commerce platform reports that content has changed, the storefront must reflect those changes promptly.

## Representative Business Workflows

### Browse and evaluate products
1. A shopper lands on a marketing or collection page.
2. The shopper opens a collection page or a featured product grid.
3. The shopper selects a product to view its detail page, where variants, options, pricing, imagery, and related products are presented.
4. From the product page, the shopper can change variant and option selections before deciding to add the item to the cart.

### Search and filter the catalog
1. The shopper enters a query from the site navigation.
2. Results are returned together with a set of filter dimensions (for example, tags and price) and a sort selector.
3. The shopper refines the result set by applying one or more filters; the result set updates accordingly.
4. The shopper can move from a filtered result set directly into a product detail page or a collection page.

### Build and edit a cart
1. From a product page the shopper selects a variant and adds the item to the cart.
2. The cart is opened as a side panel showing each line item, its quantity, and a running total.
3. The shopper can change the quantity of a line item or remove it entirely.
4. The cart's contents remain available as the shopper continues browsing other pages.

### Proceed to checkout
1. From the cart, the shopper chooses to check out.
2. The storefront hands the active cart off to the commerce platform's hosted checkout.
3. Payment, tax, shipping, and order creation are completed on the commerce platform side.

### Keep the storefront in sync with the commerce platform
1. The commerce platform signals that catalog or other content has changed.
2. The storefront refreshes the affected pages so that visitors see current information.

## Business Requirements

### Storefront browsing
- Shoppers must be able to reach the storefront's home page and view curated collections and featured product highlights.
- Shoppers must be able to open a collection page that lists the products belonging to that collection.
- Shoppers must be able to open a product detail page that shows imagery, description, pricing, available variants and options, and related products.
- Shoppers must be able to navigate between products, collections, and the home page using the site's main navigation, including a mobile‑friendly form of that navigation.

### Product discovery and search
- Shoppers must be able to search the catalog from a global entry point available in the main navigation.
- The storefront must present search results together with a defined set of filter dimensions and a sort selector.
- Shoppers must be able to apply filters to narrow the result set and to remove filters to broaden it.
- Shoppers must be able to move directly from a search result into a product or collection page.

### Shopping cart
- Shoppers must be able to add a selected variant of a product to the cart from the product page.
- Shoppers must be able to open a cart view that lists current line items, quantities, line totals, and the cart total.
- Shoppers must be able to change the quantity of a line item, including increasing, decreasing, and removing the item.
- The cart's contents must persist for the shopper across page views within a session.
- The storefront must communicate any failure to update the cart (for example, an unavailable variant) back to the shopper rather than silently losing the change.

### Checkout
- Shoppers must be able to proceed to checkout from the cart.
- The storefront must delegate payment, tax, shipping selection, and order creation to the commerce platform's checkout.
- The storefront must not store or process payment details itself.

### Discoverability and marketing integration
- Each product, collection, search result, and content page must expose the metadata that search engines and social platforms consume (title, description, canonical URL, and social preview image).
- The storefront must publish a sitemap that enumerates the pages available for indexing.
- Open Graph preview images must be available for the main page types so that shared links render correctly.

### Catalog freshness
- The storefront must support an external signal that a piece of content on the commerce platform has changed.
- When such a signal is received and authenticated, the storefront must refresh the affected pages so that visitors see current information without a full redeploy.
- The signal endpoint must reject unauthenticated callers.

### Integration boundaries
- All commerce data access (catalog, cart, checkout, menus) must be performed through a single integration layer so that the storefront can be retargeted at a different commerce provider without rewriting the user‑facing application.
- Integration with the commerce platform must be configured through deployment‑level settings (store identifier and access credentials), not hard‑coded into the storefront.

## Business Rules and Constraints

- **Hidden products are excluded from the shopper‑facing catalog.** The constants layer defines a tag that marks products as not for public display; such products must not appear in browsing, search, or recommendation results served to shoppers.
- **A default sort order governs unfiltered search results.** When the shopper has not chosen a sort, the storefront must apply a defined default.
- **Filter dimensions are fixed by configuration.** The set of available filters (for example, tag categories and price bands) is defined centrally and is not user‑configurable at runtime.
- **Cart mutations are validated against the commerce platform.** Adding, removing, or updating a line item must succeed against the platform before the shopper's view of the cart is updated; failures must be surfaced to the shopper.
- **Cart checkout is delegated to the commerce platform.** The storefront must redirect the shopper to the platform's hosted checkout rather than attempt to complete payment in‑process.
- **Content revalidation is restricted to authorized callers.** The endpoint that refreshes cached content must authenticate the request and ignore requests that cannot be authenticated.
- **Storefront identity is configurable.** The store's display name is a deployment‑level setting and not a hard‑coded constant.

## Scope Boundaries and Exclusions

The following needs are **outside** the scope of this repository based on the evidence available:

- Customer accounts, login, and order history. No authentication, profile, or order‑tracking flows are implemented for shoppers.
- Native checkout, payment capture, tax calculation, and shipping rate negotiation. These are delegated to the commerce platform.
- Administrative product authoring, inventory management, and merchandising. Catalog authoring is the merchant's responsibility in the commerce platform.
- Multi‑currency, multi‑locale, and multi‑storefront logic beyond the configurable site name. The repository exposes a single site name; richer localization needs are not evidenced.
- Native analytics, advertising pixels, and conversion attribution beyond what a deployment may add.
- Automated functional testing of business rules. The only test script supplied is a formatting check; there is no test suite that exercises the business workflows above.

## External Dependencies

- **Commerce platform** — Supplies products, collections, menus, cart operations, and the hosted checkout. All commerce data flows through a single, swappable integration layer. Access requires a store identifier and a storefront credential supplied at deployment time.
- **Deployment platform** — The storefront is intended to be deployed to a hosting platform that supports on‑demand page regeneration in response to the platform's content‑change signals.
- **Search engines and social platforms** — Consume the metadata, Open Graph previews, and sitemap published by the storefront to index and preview the site.

## Requirements That Remain Uncertain

- The precise set of business rules implemented by the commerce platform (for example, inventory thresholds that block add‑to‑cart) cannot be reconstructed from the repository and is governed by the platform.
- The exact contract that an alternative commerce provider must implement to replace the integration layer is referenced in the project description but is not enumerated in the repository's documentation.
- Whether the storefront supports any customer‑recognition need beyond a session‑persistent cart is unclear; no login or account surfaces are evidenced.
- The handling of edge cases such as abandoned carts, expired cart identifiers, or unavailable variants during checkout is governed by the commerce platform and is not specified in the repository.

## Evidence and Traceability Summary

| Business need | Primary repository evidence |
|---|---|
| Browse collections and products | `app/[page]/page.tsx`, `app/search/[collection]/page.tsx`, `app/product/[handle]/page.tsx`, `components/grid/three-items.tsx`, `components/layout/product-grid-items.tsx`, `components/carousel.tsx` |
| Search and filter | `app/search/page.tsx`, `app/search/layout.tsx`, `components/layout/navbar/search.tsx`, `components/layout/search/filter/index.tsx`, `components/layout/search/filter/dropdown.tsx`, `components/layout/search/filter/item.tsx`, `components/layout/search/collections.tsx`, `lib/constants.ts` |
| Product detail and variants | `app/product/[handle]/page.tsx`, `components/product/product-description.tsx`, `components/product/variant-selector.tsx` |
| Cart management | `components/cart/cart-context.tsx`, `components/cart/actions.ts`, `components/cart/modal.tsx`, `components/cart/add-to-cart.tsx`, `components/cart/delete-item-button.tsx`, `components/cart/edit-item-quantity-button.tsx`, `components/cart/open-cart.tsx` |
| Checkout handoff | `components/cart/actions.ts` (`redirectToCheckout`), `components/cart/modal.tsx` (`CheckoutButton`), `lib/shopify/mutations/cart.ts` |
| Discoverability | `lib/shopify/fragments/seo.ts`, `app/sitemap.ts`, `app/[page]/opengraph-image.tsx`, `app/product/[handle]/page.tsx`, `app/search/[collection]/opengraph-image.tsx` (page metadata via `generateMetadata`) |
| Catalog freshness | `app/api/revalidate/route.ts`, `lib/shopify/index.ts` (`revalidate`), environment setting `SHOPIFY_REVALIDATION_SECRET` |
| Pluggable commerce integration | `lib/shopify/index.ts`, `lib/shopify/types.ts`, `lib/shopify/queries/*`, `lib/shopify/mutations/*`, `lib/shopify/fragments/*`; deployment settings `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SITE_NAME` |
| Hidden‑product rule and default sort | `lib/constants.ts` (`HIDDEN_PRODUCT_TAG`, `defaultSort`, `SortFilterItem`) |