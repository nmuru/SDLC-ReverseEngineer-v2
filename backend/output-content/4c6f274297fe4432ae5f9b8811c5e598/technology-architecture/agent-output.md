# Technology Architecture Analysis

## System Boundaries

The repository contains a single deployable unit: a Next.js web application that integrates with Shopify as a headless CMS. The system consists of:

- **Client-side**: Web browser rendering React components
- **Server-side**: Next.js application running on Node.js
- **External system**: Shopify platform providing product data, cart functionality, and webhooks

No separate backend services, workers, or additional deployable units are evident. The architecture follows a monolithic frontend pattern where the Next.js application handles both presentation and data fetching from Shopify.

## Entry Points

Primary runtime entry points identified:

1. **Application entry**: `app/layout.tsx` (root layout) and `app/page.tsx` (home page)
2. **API route**: `app/api/revalidate/route.ts` (handles Shopify webhooks for cache revalidation)
3. **Dynamic routes**: 
   - `app/[page]/page.tsx` (static pages)
   - `app/search/[collection]/page.tsx` (collection search)
   - `app/product/[handle]/page.tsx` (product details)
4. **Client-side navigation**: Next.js router handles client-side transitions between routes

## Component Architecture

### 1. Next.js Frontend Application
- **Responsibility**: Render UI, handle routing, fetch data from Shopify, manage cart state
- **Technology**: Next.js 13+ (App Router), React 18, TypeScript, Tailwind CSS
- **Runtime**: Node.js server (for SSR/SSG) and browser (for client-side rendering)
- **Inputs**: 
  - HTTP requests (GET/POST)
  - Shopify API responses
  - URL parameters
- **Outputs**: 
  - HTML responses
  - JSON API responses (revalidate endpoint)
  - Client-side UI updates
- **Key files**: 
  - `app/layout.tsx` (root layout with providers)
  - `app/page.tsx` and dynamic route files
  - `components/` directory (UI components)
  - `lib/shopify/` (Shopify integration layer)

### 2. Shopify Integration Layer
- **Responsibility**: Abstract Shopify API interactions, handle data fetching/mutations
- **Technology**: Shopify Storefront API (via `@shopify/hydrogen` or custom fetch)
- **Runtime**: Within Next.js application (both server and client components)
- **Inputs**: 
  - Shopify store credentials (via environment variables)
  - Query parameters/mutations from components
- **Outputs**: 
  - Product data, collections, pages
  - Cart operations (add/remove/update items)
- **Key files**:
  - `lib/shopify/index.ts` (client initialization)
  - `lib/shopify/queries/` (data fetching)
  - `lib/shopify/mutations/` (cart operations)
  - `lib/shopify/fragments/` (GraphQL fragments)

### 3. Cart State Management
- **Responsibility**: Manage shopping cart state across components
- **Technology**: React Context API
- **Runtime**: Browser (client-side)
- **Inputs**: 
  - Cart mutation responses from Shopify
  - User interactions (add/remove items)
- **Outputs**: 
  - Cart state to dependent components
  - Updated cart data to Shopify via mutations
- **Key files**:
  - `components/cart/cart-context.tsx` (context provider)
  - `components/cart/actions.ts` (action creators)
  - `components/cart/add-to-cart.tsx`, `components/cart/modal.tsx` (consumers)

### 4. Webhook Handler
- **Responsibility**: Receive Shopify webhooks to trigger cache revalidation
- **Technology**: Next.js API Route
- **Runtime**: Node.js server
- **Inputs**: 
  - HTTP POST requests from Shopify webhooks
  - Webhook payload (product/collection updates)
- **Outputs**: 
  - Revalidation of affected Next.js pages
  - HTTP 200 response to Shopify
- **Key file**: `app/api/revalidate/route.ts`

## Data Stores

No internal persistent data stores are present in the repository:

- **Ephemeral state**: 
  - React component state (UI toggles, form inputs)
  - React Context (cart state)
  - Next.js request-scoped data (fetches during rendering)
- **External persistence**: 
  - Shopify platform stores all persistent data:
    - Product catalog, collections, pages
    - Customer data, orders
    - Cart contents (temporarily)
- **Caching**: 
  - Next.js Incremental Static Regeneration (ISR) for pages
  - HTTP caching headers on API responses
  - No evidence of Redis or other caching layers

## External Systems

### Shopify Platform
- **Role**: Headless CMS/ecommerce backend providing:
  - Product data via Storefront API
  - Cart and checkout functionality
  - Webhook notifications for data changes
- **Integration**: 
  - Server-side: GraphQL queries via `lib/shopify/queries/`
  - Server-side: Cart mutations via `lib/shopify/mutations/`
  - Client-side: Same APIs used in client components
  - Webhooks: `app/api/revalidate/route.ts` receives update notifications
- **Evidence**: 
  - Multiple files in `lib/shopify/` directory
  - GraphQL query/mutation patterns
  - Webhook handler route
  - Shopify-related constants and types

## Runtime and Deployment Boundaries

### Build-Time
- **Process**: `next build` (produces optimized static assets)
- **Output**: 
  - Statically generated pages (SSG) for routes with `getStaticProps`
  - Serverless functions for API routes and SSR pages
  - Client-side JavaScript bundles

### Runtime
- **Server**: 
  - Node.js process handling:
    - API routes (`app/api/`)
    - Server-side rendered pages
    - Static asset serving
    - Webhook endpoint
- **Client**: 
  - Browser executing:
    - React component tree
    - Cart context logic
    - Client-side navigation
    - User interaction handlers

### Deployment Evidence
- No Dockerfiles, Kubernetes manifests, or platform-specific configs found
- Standard Next.js deployment model:
  - Vercel (implied by Turbopack in dev script)
  - Node.js hosting platforms (AWS, Heroku, etc.)
  - Static hosting (if fully SSG)
- Environment variables expected (`.env.example` exists) but values not in repo

## Configuration Boundaries

### Environment Variables
- **Evidence**: 
  - `.env.example` file exists (referenced in intelligence)
  - No actual `.env` file in repository (security best practice)
- **Likely variables** (inferred from Shopify integration):
  - `SHOPIFY_STORE_DOMAIN`: Shopify store URL
  - `SHOPIFY_STOREFRONT_TOKEN`: Storefront API access token
- **Impact**: 
  - Affects which Shopify store the application connects to
  - Missing values cause runtime errors in Shopify API calls

### Runtime Configuration
- **Next.js configuration**: 
  - `next.config.ts` (referenced in intelligence)
  - Likely contains:
    - React Strict Mode
    - Image optimization domains
    - Base path configuration
    - Experimental features
- **Shopify API versioning**: 
  - Likely configured in `lib/shopify/index.ts` (API version)

## Communication Flows

### 1. Initial Page Load (SSG/SSR)
```
User Browser → Next.js Server → Shopify Storefront API → Next.js Server → User Browser
```
- Next.js fetches data from Shopify during build (SSG) or request (SSR)
- HTML generated and sent to browser
- Browser hydrates React components

### 2. Client-Side Navigation
```
User Browser → Next.js Client Router → Next.js Client Components → (Optional: Shopify API) → UI Update
```
- Navigation handled by Next.js client-side router
- Data fetched via `useSWR` or similar (inferred from patterns)
- Cart state updated via React Context

### 3. Cart Operations
```
User Browser → Cart Component → Cart Context → Shopify Mutations API → Shopify Store → Cart Context → UI Update
```
- User clicks "Add to Cart"
- Cart context sends mutation to Shopify
- Shopify updates cart and returns new state
- Context updates, triggering re-render of cart-dependent components

### 4. Webhook-Driven Revalidation
```
Shopify Store → Webhook (HTTP POST) → Next.js API Route → Next.js Cache Purge → Subsequent Requests → Updated Content
```
- Shopify sends webhook on product/collection change
- Next.js API route receives POST
- Triggers revalidation of affected ISR paths
- Next request gets fresh data from Shopify

## Verification Summary

| Component | Status | Evidence |
|----------|--------|----------|
| Next.js Frontend | Verified | `package.json`, `next.config.ts`, `app/` directory structure, React/TypeScript files |
| Shopify Integration | Verified | `lib/shopify/` directory with queries/mutations, GraphQL patterns, API route |
| React Context Cart | Verified | `components/cart/cart-context.tsx`, related action and UI files |
| Next.js API Routes | Verified | `app/api/revalidate/route.ts`, standard Next.js file-system routing |
| Shopify as External Data Store | Verified | Consistent API calls to Shopify endpoints, no internal DB evidence |
| Environment Variables | Strongly Inferred | `.env.example` file, Shopify integration requires credentials |
| Client-Side Rendering | Verified | Next.js App Router, React components, client-side navigation patterns |
| Server-Side Rendering/SSG | Verified | Next.js build scripts, dynamic routes with data fetching patterns |

## Architecture Diagram

```mermaid
flowchart TD
    %% External Systems
    Shopify[Shopify Platform]:::external
    
    %% Client
    Browser[User Browser]:::client
    
    %% Next.js Application
    subgraph NextJSApp[Next.js Application]:::component
        direction TB
        
        %% Entry Points
        RootLayout[Root Layout<br/>app/layout.tsx]:::entry
        HomePage[Home Page<br/>app/page.tsx]:::entry
        DynamicRoutes[Dynamic Pages<br/>app/[page]/page.tsx etc]:::entry
        APIRoute[Revalidate API<br/>app/api/revalidate/route.ts]:::entry
        
        %% Core Layers
        ShopifyLayer[Shopify Integration Layer<br/>lib/shopify/]:::layer
        CartContext[Cart State Management<br/>components/cart/]:::layer
        UIComponents[UI Components<br/>components/]:::layer
        
        %% Connections
        RootLayout --> UIComponents
        HomePage --> UIComponents
        DynamicRoutes --> UIComponents
        APIRoute --> ShopifyLayer
        UIComponents --> ShopifyLayer
        UIComponents --> CartContext
        CartContext --> ShopifyLayer
    end
    
    %% Data Flows
    Browser -->|HTTP Requests| NextJSApp
    NextJSApp -->|HTML/JSON| Browser
    NextJSApp -->|GraphQL API| Shopify
    Shopify -->|Webhook| APIRoute
    Shopify -->|Product/Cart Data| NextJSApp
    
    %% Styling
    classDef component fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef layer fill:#e6f3ff,stroke:#0066cc,stroke-width:1px;
    classDef entry fill:#d4edda,stroke:#155724,stroke-width:1px;
    classDef external fill:#fff3cd,stroke:#856404,stroke-width:1px;
    classDef client fill:#f8d7da,stroke:#721c24,stroke-width:1px;
```

## Key Architectural Notes

1. **Headless CMS Pattern**: The application follows the Jamstack/headless CMS pattern where Next.js handles presentation and Shopify manages commerce data.

2. **Isolated Concerns**: 
   - Data access layer cleanly separated in `lib/shopify/`
   - State management isolated to cart context
   - UI components focused on presentation

3. **Rendering Flexibility**: 
   - Pages can be statically generated (SSG) or server-rendered (SSR) based on data fetching methods
   - API route enables dynamic revalidation without full rebuilds

4. **Client-Server Boundary**: 
   - Shopify API calls occur on server-side (during rendering) 
   - Client-side only handles UI interactions and cart updates via the same API layer
   - No direct browser-to-Shopify calls (security best practice)

5. **Scalability Characteristics**:
   - Horizontal scaling possible via standard Node.js deployment
   - Cacheability through Next.js ISR and HTTP caching
   - Bottleneck primarily at Shopify API rate limits

This architecture represents a modern, maintainable ecommerce frontend that leverages Next.js capabilities while relying on Shopify for robust commerce functionality. The repository shows evidence of following Next.js best practices with clear separation between data fetching, state management, and presentation layers.