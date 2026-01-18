# Syntra Frontend - Folder Structure

## Overview
Struktur folder untuk website RAG Chatbot dengan React TypeScript, TanStack Query, dan Zustand.

```
src/
├── assets/                     # Static assets (images, fonts, icons)
│
├── components/                 # Shared/Reusable Components
│   ├── ui/                     # Base UI components (Button, Input, Modal, Card, etc.)
│   ├── layouts/                # Layout components (AdminLayout, UserLayout, AuthLayout)
│   └── common/                 # Common shared components (Loading, ErrorBoundary, etc.)
│
├── config/                     # Configuration files
│   └── (api.ts, env.ts)        # API config, environment variables
│
├── constants/                  # Application constants
│   └── (routes.ts, roles.ts)   # Route paths, role definitions
│
├── context/                    # React Context Providers
│   └── (AuthContext.tsx)       # Authentication context
│
├── features/                   # Feature-based modules (Domain-specific code)
│   ├── admin/                  # Admin-specific features
│   │   ├── components/         # Admin-only components (Sidebar, StatCard, etc.)
│   │   └── hooks/              # Admin-specific hooks
│   │
│   ├── auth/                   # Authentication feature
│   │   ├── components/         # LoginForm, RegisterForm, etc.
│   │   └── hooks/              # useAuth, useLogin, useLogout
│   │
│   └── chat/                   # Chat/Chatbot feature (for user role)
│       ├── components/         # ChatBubble, ChatInput, MessageList
│       └── hooks/              # useChat, useSendMessage
│
├── hooks/                      # Global/shared custom hooks
│   └── (useDebounce.ts, etc.)  # Utility hooks
│
├── lib/                        # Library configurations
│   ├── axios.ts                # Axios instance setup
│   └── queryClient.ts          # TanStack Query client
│
├── middleware/                 # Route middleware/guards
│   └── (AuthGuard.tsx)         # ProtectedRoute, AdminRoute, GuestRoute
│   └── (RoleGuard.tsx)         # Role-based access control
│
├── pages/                      # Page components (Route endpoints)
│   ├── admin/                  # Admin pages
│   │   ├── login/              # Admin login page
│   │   ├── dashboard/          # Admin dashboard
│   │   ├── documents/          # Document management (CRUD)
│   │   └── users/              # User management (CRUD)
│   │
│   ├── user/                   # User pages (Chatbot interface)
│   │   └── (chat/, profile/)   # Chat page, profile settings
│   │
│   └── auth/                   # Shared auth pages
│       └── (login/, register/) # If shared authentication
│
├── routes/                     # Route definitions
│   └── (index.tsx)             # React Router configuration
│   └── (adminRoutes.tsx)       # Admin route definitions
│   └── (userRoutes.tsx)        # User route definitions
│
├── services/                   # API service layer
│   └── (authService.ts)        # Authentication API calls
│   └── (documentService.ts)    # Document CRUD API
│   └── (userService.ts)        # User management API
│
├── store/                      # Zustand stores (Client state)
│   └── (authStore.ts)          # Authentication state
│   └── (uiStore.ts)            # UI state (sidebar, theme, etc.)
│
├── types/                      # TypeScript type definitions
│   └── (auth.types.ts)         # Auth-related types
│   └── (document.types.ts)     # Document types
│   └── (user.types.ts)         # User types
│   └── (api.types.ts)          # API response types
│
├── utils/                      # Utility functions
│   └── (formatters.ts)         # Date, currency formatters
│   └── (validators.ts)         # Form validation helpers
│   └── (storage.ts)            # LocalStorage helpers
│
├── App.tsx                     # Main App component
├── App.css                     # Global app styles
├── main.tsx                    # Entry point
└── index.css                   # Global CSS reset/base
```

## Key Architecture Decisions

### 1. Feature-Based Structure
Kode yang spesifik untuk fitur tertentu dikelompokkan dalam `features/`. Ini memudahkan maintenance dan memisahkan concern antara admin dan user.

### 2. Pages vs Features
- **pages/**: Hanya berisi komponen halaman yang di-render oleh router
- **features/**: Berisi logic bisnis, komponen spesifik fitur, dan hooks

### 3. Middleware Pattern
Route guards ditempatkan di `middleware/` untuk proteksi rute berdasarkan authentication dan role.

### 4. State Management
- **TanStack Query** (lib/queryClient.ts): Server state (API data)
- **Zustand** (store/): Client state (UI state, auth state)

### 5. Role Separation
- Admin routes: `/admin/*`
- User routes: `/*` (root level)

## File Naming Conventions
- Components: `PascalCase.tsx` (e.g., `LoginForm.tsx`)
- Hooks: `camelCase.ts` with `use` prefix (e.g., `useAuth.ts`)
- Types: `kebab-case.types.ts` (e.g., `auth.types.ts`)
- Services: `camelCase.ts` with `Service` suffix (e.g., `authService.ts`)
- Stores: `camelCase.ts` with `Store` suffix (e.g., `authStore.ts`)
