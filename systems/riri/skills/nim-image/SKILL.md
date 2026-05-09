# Skill: NIM Image Generation — FLUX Models

Fast, high-quality image generation via NIM FLUX without OpenDesign overhead.

## When to Use

Use `nim_generate_image()` for:

- **Simple standalone images:** Logos, icons, banners, thumbnails
- **Quick asset generation:** Social avatars, product shots, illustrations
- **Fast iteration:** Prototype assets, placeholder images
- **Minimal latency:** Need images fast (4 or 20 steps, not multi-step design)

**When NOT to use:**
- Complex multi-element layouts → use `opendesign_run()` instead
- Designs needing reasoning/architecture → use OpenDesign
- Multiple variations at once → batch calls or use OpenDesign

## MCP Tool: nim_generate_image()

### Signature

```python
nim_generate_image(
    prompt: str,                # Image description (detailed for quality)
    model: str = "flux.1-dev",  # or "flux.1-schnell"
    width: int = 1024,          # 768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344
    height: int = 1024,         # Same valid dimensions
    steps: int = None,          # Auto-selected per model (4 or 20)
    output_path: str = "",      # Auto-saves to ~/projects/riri/output/images/
) → dict
```

### Parameters

**prompt** (required)
- Detailed image description
- More specific → better quality
- Example: "Professional logo for a fintech startup: modern geometric design, gradient blue to purple, clean sans-serif typography, 3D depth, transparent background"

**model** (default: `"flux.1-dev"`)
- `"flux.1-schnell"` — 4 steps, fast (4–8 seconds)
- `"flux.1-dev"` — 20 steps, quality (15–30 seconds)
- `"flux.1-kontext-dev"` — 20 steps, image editing/inpainting

**width & height** (default: 1024x1024)
- Valid: 768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344 (pixels)
- Examples: 1024x1024, 1280x1024, 768x768
- Invalid values → clamped to nearest valid

**steps** (optional, auto)
- Schnell: 4 steps
- Dev: 20 steps
- Leave blank to auto-select per model

**output_path** (optional)
- Where to save PNG file
- Default: `~/projects/riri/output/images/<timestamp>.png`
- Can specify custom path: `~/projects/my-assets/logo.png`

### Return Value

```python
{
    "success": True,
    "path": "/home/ahmed/projects/riri/output/images/1715291234_flux.png",
    "model": "black-forest-labs/flux.1-dev",
    "width": 1024,
    "height": 1024,
    "bytes": 245678,  # File size
}

# On error:
{
    "success": False,
    "error": "NVIDIA_API_KEY not configured",
}
```

## Usage Examples

### Example 1: Generate a Logo

```python
nim_generate_image(
    prompt="""
    Professional logo for an AI code assistant startup.
    Design: Geometric neural network pattern forming a stylized 'C' shape.
    Colors: Gradient from electric blue (#0066ff) to cyan (#00d9ff).
    Style: Modern, minimalist, clean lines, high contrast.
    Background: Transparent.
    Format: Square, suitable for favicon and social profiles.
    """,
    model="flux.1-dev",
    width=1024, height=1024,
    output_path="~/projects/my-startup/logo.png"
)
```

### Example 2: Quick Social Avatar

```python
nim_generate_image(
    prompt="Professional headshot of a tech entrepreneur, casual business attire, warm lighting, neutral background",
    model="flux.1-schnell",  # Fast!
    width=512, height=512,
    output_path="~/projects/riri/output/images/avatar.png"
)
```

### Example 3: Product Shot

```python
nim_generate_image(
    prompt="""
    Sleek SaaS dashboard UI displayed on a 16-inch MacBook Pro.
    Dashboard shows: analytics charts, dark theme with blue accents (#2563eb),
    modern glassmorphism cards. MacBook positioned 3/4 angle, studio lighting,
    white background, professional photography style.
    """,
    model="flux.1-dev",
    width=1280, height=1024,
)
```

### Example 4: Icon Grid

```python
# Generate 4 different icons (batch)
icons = [
    "Minimalist airplane icon, blue, line art, 256x256, transparent background",
    "Minimalist hotel icon, blue, line art, 256x256, transparent background",
    "Minimalist calendar icon, blue, line art, 256x256, transparent background",
    "Minimalist map icon, blue, line art, 256x256, transparent background",
]

for i, prompt in enumerate(icons):
    nim_generate_image(
        prompt=prompt,
        model="flux.1-schnell",
        width=256, height=256,
        output_path=f"~/projects/riri/output/images/icon_{i+1}.png"
    )
```

## Model Selection

### When to Use Schnell (Fast)

✅ Do use:
- Quick previews / iteration
- Thumbnails, small assets
- When you need result in <10 seconds
- Placeholder images

❌ Don't use:
- Final production assets (quality is acceptable but lower)
- Complex scenes with many details
- When quality matters more than speed

**Latency:** 4–8 seconds
**Steps:** 4
**Quality:** Good (70% of Dev)

### When to Use Dev (Quality)

✅ Do use:
- Final LinkedIn/social posts (need polish)
- Product images, branding assets
- When quality > speed
- Complex detailed prompts

❌ Don't use:
- Time-critical tasks
- When you need <5 second turnaround

**Latency:** 15–30 seconds
**Steps:** 20
**Quality:** Excellent (100%)

### When to Use Kontext (Editing)

✅ Do use:
- Edit existing images (inpainting)
- Remove/add elements to existing PNG
- Refine previously generated images

**Latency:** 15–30 seconds
**Steps:** 20
**Quality:** Excellent (for edits)

## Architecture

```
nim_generate_image(prompt, model, ...)
    ↓
Check NVIDIA_API_KEY in env
    ↓
POST http://localhost:7457/v1/images/generations
(NIM image proxy)
    ↓
Proxy translates OpenAI format → NIM format
    ↓
POST https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev
    ↓
NIM FLUX model generates image
    ↓
Returns base64-encoded PNG
    ↓
Proxy decodes & returns OpenAI-compatible response
    ↓
Save PNG to output_path
    ↓
Return {success, path, model, ...}
```

## Valid Dimensions

FLUX supports these widths and heights independently (multiples of 64):

```
768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344 (pixels)
```

**Common combinations:**
- `1024x1024` — Square (avatar, logo)
- `1280x1024` — Landscape (banner)
- `1024x1280` — Portrait (phone mockup)
- `768x768` — Smaller (quick preview)
- `1344x1344` — Maximum size
- `512x512` — Small (icon)

**Invalid → Clamped:**
- `1200x1200` → `1216x1216`
- `1000x1000` → `1024x1024`
- `2000x2000` → `1344x1344` (clamped to max)

## Tips & Best Practices

### 1. Write Detailed Prompts

❌ Bad:
```
"Make a logo"
```

✅ Good:
```
"Geometric logo for a blockchain analytics platform. Design: overlapping circles
forming a network node pattern, gradient colors (purple to cyan), 3D effect,
modern minimalist. Background: transparent. High resolution, suitable for
256px to 1024px scaling."
```

### 2. Specify Style & Mood

```
"Professional photography style", "cinematic lighting", "high contrast",
"minimalist line art", "watercolor illustration", "3D render", etc.
```

### 3. Include Format Details

```
"Transparent background", "square composition", "landscape orientation",
"suitable for print" — helps model understand intent
```

### 4. Mention Use Case

```
"For LinkedIn social post", "For favicon", "For product landing page",
"For email header" — models adjust style accordingly
```

### 5. Iteration Strategy

```python
# Round 1: Quick preview with schnell
result = nim_generate_image(prompt="...", model="flux.1-schnell")

# Like it? Refine with dev
nim_generate_image(
    prompt="Same as above but with more [detail A] and less [detail B]",
    model="flux.1-dev"
)
```

## Troubleshooting

### "NVIDIA_API_KEY not configured"

```bash
# Check env
echo $NVIDIA_API_KEY

# Load from secrets
export $(grep NVIDIA_API_KEY ~/.nanobot/secrets.env | xargs)

# Or check files
grep NVIDIA_API_KEY ~/.nanobot/secrets.env
grep NVIDIA_API_KEY ~/.hermes/.env
```

### "Proxy not responding (localhost:7457)"

```bash
# Start proxy manually
python3 ~/projects/riri/tools/nim_image_proxy.py &

# Or via launcher
bash ~/.local/bin/opendesign-start.sh

# Check health
curl -s http://localhost:7457/health
```

### "Image generation timeout"

1. Check NIM service (usually temporary)
2. Try with `flux.1-schnell` (faster)
3. Check rate limits: console.nvidia.com

### "Output file not saving"

```bash
# Ensure output dir exists
mkdir -p ~/projects/riri/output/images/

# Check permissions
ls -la ~/projects/riri/output/images/
chmod 755 ~/projects/riri/output/images/
```

## Comparison: NIM Image vs OpenDesign

| Aspect | NIM Image | OpenDesign |
|---|---|---|
| **Use for** | Simple standalone images | Complex multi-element designs |
| **Speed** | 4–30 seconds | 30s–5 minutes |
| **Learning curve** | Simple prompt | Structured prompts + iterative |
| **Image quality** | Excellent | Excellent |
| **Layout control** | None (FLUX decides) | Full control (HTML/CSS) |
| **Interactivity** | No | Yes (clickable, hover) |
| **Video integration** | Direct feed to HyperFrames | Via HTML export |
| **Batch processing** | Easy (loop calls) | Single task at a time |
| **Cost** | Lower token usage | Higher (Hermes + OD) |

---

**Related Documentation:**
- `/home/ahmed/projects/riri/docs/nim.md` — NIM API reference, model details
- `/home/ahmed/projects/riri/skills/opendesign/SKILL.md` — When to use OpenDesign instead
- `/home/ahmed/projects/riri/tools/nim_image_proxy.py` — Proxy source code

**Last updated:** 2026-05-09
