# Prism Landing Page Content

> This document contains all copy, features, pricing, and content for the Prism marketing website.

---

## 🎯 Hero Section

### Headline
**Find anything in your data.**  
*Semantic search for local image datasets. No cloud. No limits.*

### Subheadline
Prism is an AI-powered search engine that runs entirely on your machine. Query millions of images with natural language—like "red car turning left at night"—and get results in seconds.

### CTA Buttons
- **Primary:** `Download Free` → GitHub Releases
- **Secondary:** `View on GitHub` → Repository
- **Tertiary:** `Watch Demo` → YouTube/Loom video

### Hero Image
*Full-width screenshot of Prism TUI with search results displayed*

---

## ✨ Features Section

### Section Header
**Everything you need. Nothing you don't.**

### Feature Grid

| Icon | Feature | Description |
|------|---------|-------------|
| 🔍 | **Natural Language Search** | Search your images like you'd search Google. "Pedestrian with umbrella", "truck on highway at sunset", "empty parking lot". |
| 🏠 | **100% Local** | Your data never leaves your machine. No cloud uploads, no API calls, no privacy concerns. |
| ⚡ | **GPU Accelerated** | Blazing fast on Apple Silicon (MPS), NVIDIA GPUs (CUDA), or CPU fallback. |
| 🎯 | **Object Detection** | YOLOv8 automatically detects cars, people, traffic lights, and more—making every object searchable. |
| 🖥️ | **Beautiful Terminal UI** | A stunning, keyboard-driven interface that feels like the future of data tools. |
| 📂 | **Native File Picker** | Open a real folder dialog right from your terminal. Yes, really. |
| 🔌 | **gRPC API** | Integrate Prism into your pipelines with a full-featured API. |
| 📦 | **SQLite Storage** | Simple, portable, zero-config database. Just a single file. |

---

## 🎬 How It Works Section

### Section Header
**From folder to searchable in minutes.**

### Steps

**Step 1: Point**  
Select any folder containing images. Prism handles JPG, PNG, WebP, and more.

**Step 2: Index**  
Prism analyzes every image using state-of-the-art AI models (YOLOv8 + Google SigLIP). Each frame and detected object gets a semantic embedding.

**Step 3: Search**  
Type natural language queries. Prism finds visually similar images using cosine similarity over high-dimensional vectors.

**Step 4: Explore**  
Browse results, open images in your default viewer, and export matches for further analysis.

---

## 🏢 Use Cases Section

### Section Header
**Built for engineers who work with visual data.**

### Use Case Cards

#### 🚗 Autonomous Vehicles
"Find all frames where a pedestrian is crossing in front of the ego vehicle."  
Index terabytes of sensor data and find edge cases that would take days to grep manually.

#### 🤖 Robotics
"Show me scenes with cluttered tables."  
Train manipulation models by quickly curating relevant training data from hours of recordings.

#### 🏥 Medical Imaging
"Find X-rays with visible fractures."  
Search through patient archives with semantic queries instead of metadata tags.

#### 📹 Security & Surveillance
"Person carrying a large bag near the entrance."  
Quickly locate specific events in days of security footage.

#### 🎨 Digital Asset Management
"Sunset landscape with mountains."  
Photographers and designers can finally search their archives by content, not filename.

---

## 💰 Pricing Section

### Section Header
**Simple pricing. Start free forever.**

### Pricing Table

| | **Free** | **Pro** | **Enterprise** |
|---|:---:|:---:|:---:|
| **Price** | $0 | $49 one-time | Contact us |
| | *Forever free* | *Lifetime license* | *Custom pricing* |
| **Local Indexing** | 5,000 images | **Unlimited** | **Unlimited** |
| **Semantic Search** | ✅ | ✅ | ✅ |
| **Object Detection** | ✅ | ✅ | ✅ |
| **GPU Acceleration** | ✅ | ✅ | ✅ |
| **Native File Picker** | ✅ | ✅ | ✅ |
| **Cloud Ingestion (S3)** | ❌ | ✅ | ✅ |
| **Remote GPU Core** | ❌ | ✅ | ✅ |
| **YOLO/COCO Export** | ❌ | ✅ | ✅ |
| **Priority Support** | ❌ | ✅ | ✅ |
| **Custom Models** | ❌ | ❌ | ✅ |
| **On-Prem Deployment** | ❌ | ❌ | ✅ |
| **SSO & Team Management** | ❌ | ❌ | ✅ |
| | [Download Free](#) | [Buy Pro - $49](#) | [Contact Sales](#) |

### Pricing FAQ

**Is the Free version really free forever?**  
Yes. No trials, no credit card required. The free version includes full local search capabilities with a 5,000 image limit per database.

**Why a one-time payment instead of subscription?**  
We believe in tools that respect your time and wallet. Pay once, own it forever. All minor updates included.

**What payment methods do you accept?**  
Credit card, debit card, PayPal, and Apple Pay via our secure payment partner.

**Can I get a refund?**  
Yes, within 14 days of purchase if Prism Pro doesn't work for your use case.

**Do I need to be online to use Prism?**  
No. After initial model download, Prism works completely offline.

---

## 🛠️ Tech Stack Section

### Section Header
**Built on proven, open-source foundations.**

### Tech Logos & Descriptions

| Technology | Role |
|------------|------|
| **PyTorch** | Neural network inference |
| **YOLOv8** | Real-time object detection |
| **Google SigLIP** | State-of-the-art visual-semantic embeddings |
| **Go + Bubbletea** | High-performance terminal UI |
| **gRPC** | Efficient client-server communication |
| **SQLite** | Zero-config embedded database |

---

## 📊 Stats Section (Social Proof)

### Section Header
**Trusted by engineers worldwide.**

### Stats (Update with real numbers)

| Stat | Value |
|------|-------|
| GitHub Stars | ⭐ 500+ |
| Images Indexed | 🖼️ 10M+ |
| Active Users | 👥 1,000+ |
| Avg. Search Time | ⚡ <100ms |

---

## 💬 Testimonials Section

### Section Header
**What engineers are saying.**

### Testimonial Cards

> "Prism saved us weeks of manual data curation. We found the exact edge cases we needed in minutes."  
> — **Alex Chen**, ML Engineer at Autonomous Startup

> "Finally, a search tool that doesn't require uploading my sensitive data to the cloud."  
> — **Sarah Kim**, Robotics Researcher

> "The TUI is gorgeous. It feels like using a tool from the future."  
> — **Marcus Johnson**, Staff Engineer

---

## ❓ FAQ Section

### General

**What is Prism?**  
Prism is a semantic search engine for image datasets. It uses AI to understand the visual content of your images, letting you search with natural language queries like "car at red light" instead of relying on filenames or tags.

**How is this different from keyword search?**  
Traditional search requires images to be manually tagged. Prism understands visual content directly—even objects, scenes, and activities that were never explicitly labeled.

**What image formats are supported?**  
JPEG, PNG, WebP, BMP, and GIF.

### Technical

**What are the system requirements?**  
- macOS 12+, Ubuntu 20.04+, or Windows 10+
- Python 3.9+
- Go 1.21+
- 8GB RAM minimum (16GB recommended)
- GPU optional but recommended (Apple M1+, NVIDIA GTX 1080+)

**How much disk space do models require?**  
Approximately 1.5GB for SigLIP and 50MB for YOLOv8. Models are downloaded once on first run.

**Can I use my own custom models?**  
Enterprise customers can deploy custom detection and embedding models. Contact us for details.

**Is my data sent anywhere?**  
No. Prism runs 100% locally. No network requests, no telemetry, no cloud dependencies.

### Pricing & Licensing

**What happens when I hit the 5,000 image limit?**  
Indexing stops at 5,000 images on the free version. You can still search everything already indexed. Upgrade to Pro for unlimited indexing.

**Can I use Prism Pro on multiple machines?**  
Yes, your license key works on up to 3 machines you personally own.

**Is there a student or open-source discount?**  
Yes! Email us at hello@prism.dev with your .edu email or project link for 50% off.

---

## 📧 Newsletter Section

### Section Header
**Stay in the loop.**

### Copy
Get updates on new features, tutorials, and AI tips for visual data engineers.

### Form Fields
- Email input
- Subscribe button

### Fine Print
No spam. Unsubscribe anytime. We respect your inbox.

---

## 🦶 Footer Section

### Links

**Product**
- Features
- Pricing
- Download
- Changelog

**Resources**
- Documentation
- Getting Started
- API Reference
- Error Codes

**Company**
- About
- Blog
- Contact
- Twitter

**Legal**
- Privacy Policy
- Terms of Service
- License

### Copyright
© 2026 Prism. Built by Shane Janney.

---

## 🎨 Design Notes

### Color Palette (from TUI)
- **Primary:** Electric Indigo `#7D00FF`
- **Secondary:** Cyan `#00E5FF`
- **Accent:** Neon Magenta `#FF00FF`
- **Background:** Dark `#0D0D0D`
- **Text:** Light `#EEEEEE`

### Typography Suggestions
- **Headlines:** Inter, Outfit, or Space Grotesk
- **Body:** Inter or System UI
- **Code:** JetBrains Mono or Fira Code

### Visual Assets Needed
1. Hero screenshot (TUI with results)
2. Demo GIF or video (30-60 seconds)
3. Step-by-step illustrations
4. Favicon and social share image
5. Company logo (if not just text)

---

## 📝 Meta Tags for SEO

```html
<title>Prism - Semantic Search for Local Image Datasets</title>
<meta name="description" content="AI-powered visual search that runs 100% locally. Find anything in your image datasets with natural language. No cloud, no limits.">
<meta name="keywords" content="semantic search, image search, local AI, computer vision, YOLOv8, autonomous vehicles, machine learning, terminal UI">

<!-- Open Graph -->
<meta property="og:title" content="Prism - Find anything in your data">
<meta property="og:description" content="Semantic search for local image datasets. No cloud. No limits.">
<meta property="og:image" content="https://prism.dev/og-image.png">
<meta property="og:url" content="https://prism.dev">

<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Prism - Semantic Search for Images">
<meta name="twitter:description" content="Query millions of images with natural language. 100% local.">
<meta name="twitter:image" content="https://prism.dev/twitter-card.png">
```

---

## 🚀 Launch Announcement Template

### Twitter/X Thread

**Tweet 1:**
I just launched Prism 🌈

A semantic search engine for image datasets that runs 100% locally.

Type "red car at night" → get results in seconds.

No cloud. No API keys. No privacy concerns.

[Screenshot]

🧵👇

**Tweet 2:**
The problem:

AV/robotics engineers have terabytes of sensor data.

Finding specific frames ("pedestrian crossing in rain") means:
- Manual tagging (weeks)
- Grepping logs (painful)
- Uploading to cloud (privacy nightmare)

Prism fixes this.

**Tweet 3:**
How it works:

1. Point to a folder
2. YOLOv8 detects objects
3. SigLIP generates semantic embeddings
4. Search in natural language

Built with Go + Python + gRPC.
Runs on Mac, Linux, Windows.
GPU optional (Apple MPS, NVIDIA CUDA).

**Tweet 4:**
It's free for up to 5,000 images.

Pro ($49 one-time) unlocks:
- Unlimited indexing
- S3 ingestion
- Remote GPU core
- Export to YOLO/COCO

Open source: github.com/sjanney/prism

Try it now 👇

---

*End of Landing Page Content Document*
