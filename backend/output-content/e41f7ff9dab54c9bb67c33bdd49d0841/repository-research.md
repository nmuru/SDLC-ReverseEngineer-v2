# Repository Research Brief

Research schema: 3
Phase: repository-wide

> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.
## Repository Summary

**Next.js Commerce** is a high-performance, server-rendered e-commerce storefront template built by Vercel. It targets the Shopify commerce provider as its primary integration, using the Next.js App Router with React Server Components, Server Actions, `Suspense`, and `useOptimistic`. The template is designed for Vercel deployment and serves as a reference implementation for commerce providers to fork and adapt (swapping `lib/shopify` for their own backend).

**Domain & Actors**: Online retail storefront serving shoppers browsing products, collections, and managing a shopping cart. The system boundary spans the Next.js frontend, Shopify's GraphQL API, and Vercel's deployment infrastructure.

**Architecture**: The application follows a server-first pattern. `lib/shopify/index.ts` acts as the central data-fetching facade, exposing functions like `getProduct`, `getCollection`, `getCart`, `createCart`, `addToCart`, and `revalidate`. GraphQL operations are organized into fragments (`fragments/`), queries (`queries/`), and mutations (`mutations/`). Client-side cart state is managed through `components/cart/cart-context.tsx` with a reducer pattern, while cart mutations use Server Actions via `components/cart/actions.ts`.

**Key Capabilities**: Product browsing with variant selection, collection/category pages with filtering and sorting, search with collection autocomplete, a slide-out cart modal with item quantity editing and deletion, server-rendered homepage with carousel and product grids, SEO metadata generation, and OpenGraph image generation for social sharing. The cart supports optimistic updates and revalidation via a webhook-triggered API route (`app/api/revalidate/route.ts`).

**External Integrations**: Shopify (GraphQL storefront API, configured via `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, and `SHOPIFY_REVALIDATION_SECRET` environment variables), Vercel (deployment and preview URLs), and optional providers like BigCommerce, Ecwid, and Geins as documented alternatives.

**Implementation Notes**: The project uses pnpm, Prettier with Tailwind plugin, Tailwind CSS 4 with container queries and typography plugins, and TypeScript strict mode. The `test` script runs Prettier checks rather than unit tests, suggesting limited automated testing coverage in this template.
