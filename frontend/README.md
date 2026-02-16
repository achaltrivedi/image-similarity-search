# Visual Search Frontend

Modern React frontend for the Image Similarity Service.

## 🚀 Quick Start

### Install Dependencies

```bash
cd frontend
npm install
```

### Run Development Server

```bash
npm run dev
```

The app will run at: `http://localhost:5173`

**Important:** Make sure your FastAPI backend is running on `http://localhost:8000`

```bash
# In the parent directory
uvicorn app:app --reload
```

### Build for Production

```bash
npm run build
```

This creates a `dist/` folder ready for deployment.

---

## ✨ Features

- **Drag & Drop Upload** - Drop images directly or click to browse
- **Real-time Search** - Instant results from the image similarity API
- **Beautiful Results Grid** - Responsive card layout with similarity scores
- **Download Buttons** - Direct S3 downloads for all results
- **Loading States** - Smooth animations during search
- **Error Handling** - User-friendly error messages

---

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── SearchBox.jsx       # Drag & drop upload
│   │   ├── ResultsGrid.jsx     # Results display
│   │   ├── ResultCard.jsx      # Individual result
│   │   └── LoadingSpinner.jsx  # Loading animation
│   ├── api/
│   │   └── searchService.js    # API calls
│   ├── App.jsx                 # Main component
│   ├── main.jsx                # React entry point
│   └── index.css               # Tailwind styles
├── vite.config.js              # Vite + proxy config
└── package.json
```

---

## 🔧 API Proxy

The Vite dev server proxies `/api/*` requests to `http://localhost:8000`:

```javascript
// This call in React:
fetch('/api/search', { method: 'POST', body: formData })

// Gets proxied to:
http://localhost:8000/search
```

---

## 🌐 Deployment

### Option 1: Static Hosting (Recommended)

1. Build the app:
   ```bash
   npm run build
   ```

2. Deploy `dist/` folder to your web server:
   ```bash
   cp -r dist /var/www/visual-search/
   ```

3. Configure Nginx:
   ```nginx
   location /visual-search/ {
     alias /var/www/visual-search/;
     try_files $uri /index.html;
   }
   
   location /api/ {
     proxy_pass http://localhost:8000/;
   }
   ```

### Option 2: Docker

Add to your `docker-compose.yml`:

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - app
```

---

## 🎨 Customization

### Change API URL

Edit `src/api/searchService.js`:

```javascript
const API_BASE_URL = 'http://your-server:8000'
```

### Modify Styles

Colors and spacing use Tailwind classes. Edit directly in components:

```jsx
className="bg-purple-600 text-white"
```

Or extend in `tailwind.config.js`.

---

## 📝 Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool (fast dev server)
- **Tailwind CSS** - Styling
- **Fetch API** - HTTP requests

---

## 🐛 Troubleshooting

**Problem:** "Failed to fetch"
- **Fix:** Ensure FastAPI is running on port 8000

**Problem:** CORS errors
- **Fix:** Vite proxy should handle it, but if deploying separately, add CORS middleware to FastAPI

**Problem:** Upload doesn't work
- **Fix:** Check file size limits and supported file types

---

## 📞 Support

For issues, check the parent project README or contact the backend team.
