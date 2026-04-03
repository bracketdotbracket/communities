# Communities

A modern community platform where users can create, join, and engage with interest-based communities — built with React, TypeScript, and Lovable Cloud.

(https://communities.ws/)
## ✨ Features

- **Communities** — Create and manage topic-based communities with custom avatars, banners, and categories
- **Posts & Feeds** — Share text and image posts within communities
- **Polls** — Create interactive polls with up to 4 options and real-time vote tracking
- **Comments & Likes** — Engage with posts through comments, likes, and reposts
- **Direct Messages** — Real-time private conversations between users
- **Notifications** — Stay updated on likes, comments, and mentions
- **User Profiles** — Customizable profiles with bio, avatar, and post history
- **Explore** — Discover communities by category
- **Moderation** — Community creators can manage members, pin posts, and ban users
- **Admin Dashboard** — Platform-wide administration tools
- **Responsive Design** — Full mobile and desktop support with PWA capabilities

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript 5, Vite 5 |
| Styling | Tailwind CSS 3, shadcn/ui |
| State | TanStack React Query |
| Routing | React Router v6 |
| Backend | AWS Amplify |
| Auth | Email/password, Twitter/X OAuth |

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- npm or bun

### Installation

```bash
# Clone the repository
git clone <communities>
cd communities

# Install dependencies
npm install

# Start the development server
npm run dev
```

The app will be available at `http://localhost:5173`.


## 📁 Project Structure

```
src/
├── components/       # Reusable UI components
│   ├── ui/           # shadcn/ui primitives
│   ├── Layout.tsx    # App shell with sidebar navigation
│   ├── PostCard.tsx  # Post display with interactions
│   ├── PollDisplay.tsx
│   └── ...
├── core/            # Custom React hooks (auth, notifications, etc.)
├── pages/            # Route-level page components
├── integrations/     # AWS Amplify client & types
└── lib/              # Utility functions
```

## 📄 License

This project is private. All rights reserved.
